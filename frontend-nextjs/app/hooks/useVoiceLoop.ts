"use client"

import { useEffect, useRef, useState } from "react"
import { usePresenceStore } from "../stores/presence-store"
import { useUsageLimitStore } from "../stores/usage-limit-store"
import { emitTelemetry } from "../lib/telemetry"
import type { UsageLimitError } from "../types/rate-limits"

const PREBUFFER_CHUNKS = 3
const FIRST_AUDIO_TARGET_MS = 200

type VoiceStage = "idle" | "connecting" | "listening" | "thinking" | "speaking" | "error"
type RouterPath = "direct" | "light" | "agentic"

type QueuedChunk = {
  url: string
  revokeOnUse: boolean
}

const httpToWs = (url: string) => {
  if (url.startsWith("https://")) return url.replace("https://", "wss://")
  if (url.startsWith("http://")) return url.replace("http://", "ws://")
  return url
}

const base64ToUint8Array = (b64: string): Uint8Array => {
  const raw = atob(b64)
  const bytes = new Uint8Array(raw.length)
  for (let i = 0; i < raw.length; i += 1) {
    bytes[i] = raw.charCodeAt(i)
  }
  return bytes
}

const getAudioContextClass = () => {
  if (typeof window === "undefined") {
    throw new Error("AudioContext unavailable")
  }
  const AudioContextClass =
    window.AudioContext ||
    (window as typeof window & {
      webkitAudioContext?: typeof AudioContext
    }).webkitAudioContext
  if (!AudioContextClass) {
    throw new Error("AudioContext not supported")
  }
  return AudioContextClass
}

function downsampleTo16kPCM(input: Float32Array, inputSampleRate: number): ArrayBuffer {
  const targetRate = 16000
  if (inputSampleRate === targetRate) {
    const pcm = new Int16Array(input.length)
    for (let i = 0; i < input.length; i += 1) {
      const s = Math.max(-1, Math.min(1, input[i]))
      pcm[i] = s < 0 ? s * 0x8000 : s * 0x7fff
    }
    return pcm.buffer
  }
  const ratio = inputSampleRate / targetRate
  const newLength = Math.floor(input.length / ratio)
  const result = new Float32Array(newLength)
  let pos = 0
  let idx = 0
  while (pos < newLength) {
    const nextIdx = Math.floor((pos + 1) * ratio)
    let sum = 0
    let count = 0
    for (let i = idx; i < nextIdx && i < input.length; i += 1) {
      sum += input[i]
      count += 1
    }
    result[pos] = sum / (count || 1)
    pos += 1
    idx = nextIdx
  }
  const pcm = new Int16Array(result.length)
  for (let i = 0; i < result.length; i += 1) {
    const s = Math.max(-1, Math.min(1, result[i]))
    pcm[i] = s < 0 ? s * 0x8000 : s * 0x7fff
  }
  return pcm.buffer
}

export function useVoiceLoop() {
  const [stage, setStage] = useState<VoiceStage>("idle")
  const [partialReply, setPartialReply] = useState("")
  const [finalReply, setFinalReply] = useState("")
  const [error, setError] = useState<string>()
  const [path, setPath] = useState<RouterPath>()
  const [needsUnlock, setNeedsUnlock] = useState(false)

  const setListeningPresence = usePresenceStore((state) => state.setListening)
  const setSpeakingPresence = usePresenceStore((state) => state.setSpeaking)
  const setMetaPresence = usePresenceStore((state) => state.setMetaStage)
  const setPresenceDetail = usePresenceStore((state) => state.setDetail)
  const settlePresence = usePresenceStore((state) => state.settleToRestingSoon)
  const resetPresence = usePresenceStore((state) => state.reset)

  const wsRef = useRef<WebSocket | null>(null)
  const audioCtxRef = useRef<AudioContext | null>(null)
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null)
  const processorRef = useRef<ScriptProcessorNode | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const chunkAccumulatorRef = useRef<Float32Array[]>([])
  const replyBufferRef = useRef("")
  const connectPromiseRef = useRef<Promise<WebSocket> | null>(null)
  const destroyedRef = useRef(false)

  const playbackQueueRef = useRef<QueuedChunk[]>([])
  const isPlayingRef = useRef(false)
  const hasStartedPlaybackRef = useRef(false)
  const streamEndedRef = useRef(false)
  const prebufferOverrideRef = useRef(false)
  const currentAudioRef = useRef<HTMLAudioElement | null>(null)
  const firstChunkAtRef = useRef<number | null>(null)
  const speechStartAtRef = useRef<number | null>(null)
  const speechEndAtRef = useRef<number | null>(null)
  const firstAudioAtRef = useRef<number | null>(null)

  const resetPlaybackTracking = () => {
    streamEndedRef.current = false
    prebufferOverrideRef.current = false
    hasStartedPlaybackRef.current = false
    firstChunkAtRef.current = null
  }

  const stopCurrentAudio = () => {
    const current = currentAudioRef.current
    if (!current) return
    try {
      current.pause()
      current.currentTime = 0
    } catch {
      // ignore
    }
    current.onended = null
    current.onerror = null
    current.onabort = null
    if (current.src?.startsWith("blob:")) {
      try {
        URL.revokeObjectURL(current.src)
      } catch {
        // ignore
      }
    }
    currentAudioRef.current = null
    isPlayingRef.current = false
  }

  const flushPlaybackQueue = () => {
    stopCurrentAudio()
    for (const chunk of playbackQueueRef.current) {
      if (chunk.revokeOnUse) {
        try {
          URL.revokeObjectURL(chunk.url)
        } catch {
          // ignore
        }
      }
    }
    playbackQueueRef.current = []
    resetPlaybackTracking()
  }

  const startNextChunkIfReady = () => {
    if (isPlayingRef.current || playbackQueueRef.current.length === 0) return

    const needsPrebuffer = !hasStartedPlaybackRef.current
    const prebufferReady =
      !needsPrebuffer || prebufferOverrideRef.current || playbackQueueRef.current.length >= PREBUFFER_CHUNKS
    if (!prebufferReady) return

    const nextChunk = playbackQueueRef.current.shift()!
    if (!hasStartedPlaybackRef.current) {
      hasStartedPlaybackRef.current = true
      prebufferOverrideRef.current = false
      if (firstChunkAtRef.current) {
        const latency = performance.now() - firstChunkAtRef.current
        if (latency > FIRST_AUDIO_TARGET_MS) {
          console.warn(
            `[voice] first audio chunk started after ${Math.round(latency)}ms (target ≤ ${FIRST_AUDIO_TARGET_MS}ms)`,
          )
        }
      }
    }

    const audio = new Audio(nextChunk.url)
    audio.preload = "auto"
    currentAudioRef.current = audio
    isPlayingRef.current = true

    const finalize = () => {
      stopCurrentAudio()
      if (playbackQueueRef.current.length > 0) {
        startNextChunkIfReady()
      } else if (streamEndedRef.current) {
        resetPlaybackTracking()
        setStage("idle")
        setSpeakingPresence(false)
        settlePresence()
      }
    }

    audio.onended = finalize
    audio.onerror = finalize
    audio.onabort = finalize

    audio
      .play()
      .then(() => {
        setStage("speaking")
        setSpeakingPresence(true)
        const now = performance.now()
        firstAudioAtRef.current = now
        if (speechEndAtRef.current) {
          emitTelemetry("voice.perceived_latency_ms", {
            ms: Math.round(now - speechEndAtRef.current),
            path,
          })
        }
      })
      .catch(() => {
        finalize()
      })
  }

  const enqueueChunk = (chunk: QueuedChunk) => {
    playbackQueueRef.current.push(chunk)
    if (!firstChunkAtRef.current) {
      firstChunkAtRef.current = performance.now()
    }
    startNextChunkIfReady()
  }

  const enqueueBase64Chunk = (b64: string, mime?: string) => {
    try {
      const bytes = base64ToUint8Array(b64)
      const blob = new Blob([bytes], { type: mime || "audio/wav" })
      const url = URL.createObjectURL(blob)
      enqueueChunk({ url, revokeOnUse: true })
    } catch (err) {
      console.warn("[voice] failed to enqueue base64 chunk", err)
    }
  }

  const enqueueRemoteChunk = (url?: string) => {
    if (!url || !/^https?:\/\//.test(url)) return
    enqueueChunk({ url, revokeOnUse: false })
  }

  const handleStreamEos = () => {
    streamEndedRef.current = true
    prebufferOverrideRef.current = true
    if (!isPlayingRef.current) {
      resetPlaybackTracking()
      setStage("idle")
      setSpeakingPresence(false)
      settlePresence()
    }
    if (speechStartAtRef.current) {
      emitTelemetry("voice.stream_complete", {
        path,
        duration_ms: Math.round(performance.now() - speechStartAtRef.current),
      })
    }
    speechStartAtRef.current = null
    speechEndAtRef.current = null
    firstAudioAtRef.current = null
  }

  const handleServerMessage = (event: MessageEvent) => {
    if (typeof event.data !== "string") return
    let data: Record<string, any>
    try {
      data = JSON.parse(event.data)
    } catch {
      return
    }

    switch (data.type) {
      case "meta":
        if (data.path) {
          setPath(data.path)
        }
        if (data.stage) {
          setMetaPresence(data.stage, data.detail)
        } else if (typeof data.detail === "string") {
          setPresenceDetail(data.detail)
        }
        break
      case "token": {
        const text = typeof data.text === "string" ? data.text : ""
        replyBufferRef.current = `${replyBufferRef.current}${text}`
        setPartialReply(replyBufferRef.current)
        setStage((prev) => (prev === "listening" ? "thinking" : prev))
        setListeningPresence(false)
        setMetaPresence("thinking")
        break
      }
      case "reply_done": {
        const text = typeof data.text === "string" ? data.text : replyBufferRef.current
        setFinalReply(text)
        break
      }
      case "audio_chunk":
        if (data.b64) {
          enqueueBase64Chunk(data.b64, data.mime)
        }
        if (data.eos) {
          handleStreamEos()
        }
        break
      case "audio_url":
      case "audio_url_chunk":
        enqueueRemoteChunk(data.audio_url)
        if (data.eos) {
          handleStreamEos()
        }
        break
      case "error": {
        // Check if it's a usage limit error
        if (data.error === "USAGE_LIMIT_REACHED") {
          const limitError: UsageLimitError = {
            error: "USAGE_LIMIT_REACHED",
            reason: data.reason || "voice",
            plan_tier: data.plan_tier || "FREE",
            limit: data.limit || 0,
            used: data.used || 0,
            message: data.message,
            body: data.body,
          }
          useUsageLimitStore.getState().showModal({
            reason: limitError.reason,
            plan_tier: limitError.plan_tier,
            limit: limitError.limit,
            used: limitError.used,
          })
          flushPlaybackQueue()
          setStage("idle")
          setListeningPresence(false)
          setSpeakingPresence(false)
          resetPresence()
          emitTelemetry("voice.usage_limit", { reason: limitError.reason, path })
        } else {
          setError(data.detail ?? data.message ?? "The voice session ended unexpectedly.")
          setStage("error")
          flushPlaybackQueue()
          setListeningPresence(false)
          setSpeakingPresence(false)
          setMetaPresence("resting")
          settlePresence()
          emitTelemetry("voice.error", { message: data.detail ?? data.message ?? "server_error", path })
        }
        break
      }
      default:
        break
    }
  }

  const ensureConnection = () => {
    if (typeof window === "undefined") {
      return Promise.reject(new Error("Voice not supported on server"))
    }
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      return Promise.resolve(wsRef.current)
    }
    if (wsRef.current && wsRef.current.readyState === WebSocket.CONNECTING && connectPromiseRef.current) {
      return connectPromiseRef.current
    }
    // Use NEXT_PUBLIC_BACKEND_WS_URL if available, otherwise construct from API URL
    const wsBase = process.env.NEXT_PUBLIC_BACKEND_WS_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
    const wsUrl = wsBase.startsWith("ws") ? `${wsBase}/ws/voice` : `${httpToWs(wsBase)}/ws/voice`
    setStage("connecting")

    const promise = new Promise<WebSocket>((resolve, reject) => {
      try {
        const ws = new WebSocket(wsUrl)
        ws.binaryType = "arraybuffer"
        ws.onopen = () => {
          wsRef.current = ws
          connectPromiseRef.current = null
          setStage("idle")
          resolve(ws)
        }
        ws.onmessage = handleServerMessage
        ws.onerror = (event) => {
          console.warn("[voice] websocket error", event)
          if (ws.readyState !== WebSocket.OPEN) {
            connectPromiseRef.current = null
            reject(new Error("WebSocket error"))
          }
        }
        ws.onclose = () => {
          flushPlaybackQueue()
          wsRef.current = null
          connectPromiseRef.current = null
          if (!destroyedRef.current) {
            setStage("idle")
            resetPresence()
          }
        }
      } catch (err) {
        connectPromiseRef.current = null
        reject(err)
      }
    })

    connectPromiseRef.current = promise
    return promise
  }

  const unlockAudio = async () => {
    const AudioContextClass = getAudioContextClass()
    const ctx = audioCtxRef.current ?? new AudioContextClass({ sampleRate: 48000 })
    audioCtxRef.current = ctx
    try {
      await ctx.resume()
      const buffer = ctx.createBuffer(1, 1, ctx.sampleRate)
      const source = ctx.createBufferSource()
      source.buffer = buffer
      source.connect(ctx.destination)
      source.start(0)
      setNeedsUnlock(false)
      return true
    } catch {
      setNeedsUnlock(true)
      return false
    }
  }

  const cleanupRecorder = () => {
    try {
      processorRef.current?.disconnect()
    } catch {
      // ignore
    }
    try {
      sourceRef.current?.disconnect()
    } catch {
      // ignore
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop())
      streamRef.current = null
    }
    processorRef.current = null
    sourceRef.current = null
    chunkAccumulatorRef.current = []
  }

  const startTalking = async () => {
    setError(undefined)
    replyBufferRef.current = ""
    setPartialReply("")
    setFinalReply("")

    try {
      const ws = await ensureConnection()
      if (!ws || ws.readyState !== WebSocket.OPEN) {
        throw new Error("Voice service unavailable")
      }
      const AudioContextClass = getAudioContextClass()
      const ctx = audioCtxRef.current ?? new AudioContextClass({ sampleRate: 48000 })
      audioCtxRef.current = ctx
      if (ctx.state === "suspended") {
        const unlocked = await unlockAudio()
        if (!unlocked) {
          throw new Error("Audio context locked")
        }
      }

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, noiseSuppression: true, echoCancellation: true },
      })
      streamRef.current = stream
      const source = ctx.createMediaStreamSource(stream)
      sourceRef.current = source
      const processor = ctx.createScriptProcessor(4096, 1, 1)
      processorRef.current = processor
      chunkAccumulatorRef.current = []

      processor.onaudioprocess = (e) => {
        const input = e.inputBuffer.getChannelData(0)
        chunkAccumulatorRef.current.push(new Float32Array(input))
        const totalSamples = chunkAccumulatorRef.current.reduce((acc, chunk) => acc + chunk.length, 0)
        const secs = totalSamples / ctx.sampleRate
        if (secs >= 0.2 && wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          const merged = new Float32Array(totalSamples)
          let offset = 0
          for (const chunk of chunkAccumulatorRef.current) {
            merged.set(chunk, offset)
            offset += chunk.length
          }
          chunkAccumulatorRef.current = []
          const pcm16 = downsampleTo16kPCM(merged, ctx.sampleRate)
          wsRef.current.send(pcm16)
        }
      }

      source.connect(processor)
      processor.connect(ctx.destination)
      setStage("listening")
      setListeningPresence(true)
      speechStartAtRef.current = performance.now()
      emitTelemetry("voice.capture_start", { path })
    } catch (err) {
      console.error("[voice] startTalking failed", err)
      setError("I couldn’t access your microphone. Please check your permissions.")
      emitTelemetry("voice.error", { message: (err as Error)?.message ?? "mic_start_failed" })
      setStage("error")
      setListeningPresence(false)
      cleanupRecorder()
    }
  }

  const stopTalking = () => {
    cleanupRecorder()
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      setStage((prev) => (prev === "listening" || prev === "connecting" ? "thinking" : prev))
      setMetaPresence("thinking")
    } else {
      setStage("idle")
      setMetaPresence("resting")
      settlePresence()
    }
    setListeningPresence(false)
    const now = performance.now()
    speechEndAtRef.current = now
    if (speechStartAtRef.current) {
      emitTelemetry("voice.capture_stop", {
        path,
        duration_ms: Math.round(now - speechStartAtRef.current),
      })
    }
  }

  const bargeIn = () => {
    const start = performance.now()
    flushPlaybackQueue()
    try {
      wsRef.current?.send(JSON.stringify({ type: "cancel", reason: "barge_in" }))
    } catch {
      // ignore
    }
    const latency = performance.now() - start
    emitTelemetry("voice.barge_in_latency_ms", {
      ms: Math.round(latency),
      path,
    })
    setStage("idle")
    setListeningPresence(false)
    setSpeakingPresence(false)
    setMetaPresence("resting")
    settlePresence()
    speechStartAtRef.current = null
    speechEndAtRef.current = null
    firstAudioAtRef.current = null
  }

  useEffect(() => {
    return () => {
      destroyedRef.current = true
      cleanupRecorder()
      flushPlaybackQueue()
      try {
        wsRef.current?.close()
      } catch {
        // ignore
      }
      wsRef.current = null
      resetPresence()
    }
  }, [])

  return {
    stage,
    partialReply,
    finalReply,
    error,
    path,
    needsUnlock,
    stream: streamRef.current,
    startTalking,
    stopTalking,
    bargeIn,
    unlockAudio,
  }
}

