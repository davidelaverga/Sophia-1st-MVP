"use client"

import { useEffect, useRef, useState } from "react"
import { usePresenceStore } from "../stores/presence-store"
import { useUsageLimitStore } from "../stores/usage-limit-store"
import { useVoiceHistoryStore } from "../stores/voice-history-store"
import { useChatStore } from "../stores/chat-store"
import { emitTelemetry } from "../lib/telemetry"
import type { UsageLimitError, UsageLimitInfo } from "../types/rate-limits"
import { refreshUsage } from "./useUsageMonitor"
import { checkMicrophonePermission, isMicrophonePermissionDenied } from "../lib/microphone-permissions"
import { diagnoseMicrophoneAccess, logDiagnostics, isMicrophoneLikelySupported } from "../lib/microphone-debug"

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

// 💜 Accept userId for rate limiting (optional)
export function useVoiceLoop(userId?: string) {
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
  const showLimitModal = useUsageLimitStore((state) => state.showModal)
  
  const addVoiceMessage = useVoiceHistoryStore((state) => state.addMessage)
  const addVoiceToChat = useChatStore((state) => state.addVoiceMessage)

  const wsRef = useRef<WebSocket | null>(null)
  const audioCtxRef = useRef<AudioContext | null>(null)
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null)
  const processorRef = useRef<ScriptProcessorNode | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const chunkAccumulatorRef = useRef<Float32Array[]>([])
  const replyBufferRef = useRef("")
  const connectPromiseRef = useRef<Promise<WebSocket> | null>(null)
  const destroyedRef = useRef(false)
  const thinkingTimeoutRef = useRef<NodeJS.Timeout | null>(null)

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
        
        // Close WebSocket after all audio playback is complete
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.close()
          wsRef.current = null
        }
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
      // TypeScript fix: cast to ensure compatibility with BlobPart
      const blob = new Blob([bytes as BlobPart], { type: mime || "audio/wav" })
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
      
      // Close WebSocket after audio stream ends to prevent backend loop
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.close()
        wsRef.current = null
      }
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
        // Handle progressive usage alerts from backend
        if (data.usage_info) {
          const usageInfo = data.usage_info
          const usagePercent = (usageInfo.used / usageInfo.limit) * 100
          
          if (usagePercent >= 80 && usagePercent < 100) {
            // Show gentle toast at 80-99%
            useUsageLimitStore.getState().showToast({
              reason: usageInfo.reason,
              plan_tier: usageInfo.plan_tier,
              limit: usageInfo.limit,
              used: usageInfo.used,
            })
          } else if (usagePercent >= 50 && usagePercent < 80) {
            // Show subtle hint at 50-79%
            useUsageLimitStore.getState().showHint({
              reason: usageInfo.reason,
              plan_tier: usageInfo.plan_tier,
              limit: usageInfo.limit,
              used: usageInfo.used,
            })
          }
        }
        break
      case "token": {
        const text = typeof data.text === "string" ? data.text : ""
        replyBufferRef.current = `${replyBufferRef.current}${text}`
        setPartialReply(replyBufferRef.current)
        const wasListening = stage === "listening"
        if (wasListening) {
          setStage("thinking")
          setListeningPresence(false)
          setMetaPresence("thinking")
          
          // Clear any existing timeout
          if (thinkingTimeoutRef.current) {
            clearTimeout(thinkingTimeoutRef.current)
          }
          
          // Set timeout to reset if no response in 60 seconds
          thinkingTimeoutRef.current = setTimeout(() => {
            console.warn("[voice] Thinking timeout - no response from server after 60s, resetting")
            setStage("idle")
            setError("Voice session timed out. Please try again.")
            setListeningPresence(false)
            setSpeakingPresence(false)
            setMetaPresence("resting")
            settlePresence()
            
            // Close and cleanup WebSocket if stuck
            if (wsRef.current) {
              try {
                wsRef.current.close()
              } catch {
                // ignore
              }
              wsRef.current = null
            }
            cleanupRecorder()
            thinkingTimeoutRef.current = null
            emitTelemetry("voice.timeout", { path })
          }, 60000) // 60 seconds timeout
        }
        break
      }
      case "reply_done": {
        // Clear thinking timeout since we got a response
        if (thinkingTimeoutRef.current) {
          clearTimeout(thinkingTimeoutRef.current)
          thinkingTimeoutRef.current = null
        }
        
        const text = typeof data.text === "string" ? data.text : replyBufferRef.current
        
        // Save to voice history (for VoiceTranscript component)
        if (text.trim()) {
          addVoiceMessage(text)
        }
        
        // ALSO save to unified chat store for seamless context
        if (text.trim()) {
          addVoiceToChat(text)
        }
        
        // Clear finalReply after saving to history to avoid showing it separately
        setFinalReply(text)
        setTimeout(() => {
          setFinalReply("")
        }, 100)
        
        // IMPORTANT: Reset reply buffer to prevent concatenation
        replyBufferRef.current = ""
        setPartialReply("")
        
        // Refresh usage immediately after voice interaction completes
        // Backend has updated the usage, so we should see the new count
        refreshUsage()
        
        // DON'T close WebSocket here - audio chunks still need to come through
        // WebSocket will close when audio playback ends (handleStreamEos)
        
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
        // Clear thinking timeout on error
        if (thinkingTimeoutRef.current) {
          clearTimeout(thinkingTimeoutRef.current)
          thinkingTimeoutRef.current = null
        }
        
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
    
    // If WebSocket exists but is in a bad state, close and recreate
    if (wsRef.current) {
      const state = wsRef.current.readyState
      if (state === WebSocket.CLOSING || state === WebSocket.CLOSED) {
        // Clean up closed/closing WebSocket
        try {
          wsRef.current.close()
        } catch {
          // ignore
        }
        wsRef.current = null
        connectPromiseRef.current = null
      } else if (state === WebSocket.OPEN) {
        return Promise.resolve(wsRef.current)
      } else if (state === WebSocket.CONNECTING && connectPromiseRef.current) {
        return connectPromiseRef.current
      }
    }
    // Use NEXT_PUBLIC_BACKEND_WS_URL if available, otherwise construct from API URL
    const wsBase = process.env.NEXT_PUBLIC_BACKEND_WS_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
    let wsUrl = wsBase.startsWith("ws") ? `${wsBase}/ws/voice` : `${httpToWs(wsBase)}/ws/voice`
    
    // Add API key for authentication (required by backend)
    const apiKey = process.env.NEXT_PUBLIC_API_KEY || "dev-key"
    const separator = wsUrl.includes("?") ? "&" : "?"
    wsUrl += `${separator}api_key=${encodeURIComponent(apiKey)}`
    
    // 💜 Add user_id query param for rate limiting (optional)
    if (userId) {
      wsUrl += `&user_id=${encodeURIComponent(userId)}`
    }
    
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
        ws.onclose = (event) => {
          // Clear thinking timeout on close
          if (thinkingTimeoutRef.current) {
            clearTimeout(thinkingTimeoutRef.current)
            thinkingTimeoutRef.current = null
          }
          
          flushPlaybackQueue()
          wsRef.current = null
          connectPromiseRef.current = null
          if (!destroyedRef.current) {
            // Only reset to idle if we're not in an error state
            if (stage !== "error") {
              setStage("idle")
            }
            resetPresence()
          }
          
          // Log unexpected closes for debugging
          if (event.code !== 1000 && !destroyedRef.current) {
            console.warn("[voice] WebSocket closed unexpectedly", { code: event.code, reason: event.reason })
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
    // 💜 Block if user is at 100% usage limit
    const usageStore = useUsageLimitStore.getState()
    if (usageStore.isAtLimit) {
      // Show modal if not already open
      if (!usageStore.isOpen && usageStore.currentUsage) {
        const reason = usageStore.currentUsage.voicePercent >= 100 ? "voice" : "text"
        const limitInfo: UsageLimitInfo = {
          reason,
          plan_tier: "FREE", // Will be updated by usage monitor
          limit: 0,
          used: 0,
        }
        usageStore.showModal(limitInfo)
      }
      setError("You've reached your daily limit. Please upgrade or come back tomorrow.")
      setStage("error")
      return // Block the request
    }

    // Immediate visual feedback - set connecting state right away
    setError(undefined)
    setStage("connecting")
    replyBufferRef.current = ""
    setPartialReply("")
    setFinalReply("")

    try {
      // Run diagnostics on first attempt (helps debug issues)
      if (typeof window !== "undefined" && !(window as any).__sophia_mic_diagnostics_run) {
        console.log("[voice] Running microphone diagnostics...")
        const diagnostics = await diagnoseMicrophoneAccess()
        logDiagnostics(diagnostics)
        
        const supportCheck = isMicrophoneLikelySupported(diagnostics)
        if (!supportCheck.supported) {
          console.warn("[voice] Potential microphone access issues detected:", supportCheck.issues)
        }
        
        (window as any).__sophia_mic_diagnostics_run = true
      }

      // Check microphone permission before attempting access (non-blocking)
      // Only block if we're CERTAIN it's denied. Otherwise, let getUserMedia handle it.
      let permissionState: "granted" | "denied" | "prompt" | "unknown" = "unknown"
      try {
        permissionState = await checkMicrophonePermission()
        console.log("[voice] Permission check result:", permissionState)
      } catch (permError) {
        // Permission API not available or failed - this is OK, we'll try getUserMedia anyway
        console.log("[voice] Permission check failed, will try getUserMedia:", permError)
        permissionState = "unknown"
      }
      
      // Only block if we're CERTAIN permission is denied
      // If it's "unknown" or "prompt", let getUserMedia handle the permission request
      if (permissionState === "denied") {
        console.log("[voice] Permission explicitly denied, blocking access")
        setError("Microphone access is blocked. Please enable it in your browser settings and refresh the page.")
        setStage("error")
        setListeningPresence(false)
        emitTelemetry("voice.error", { message: "mic_permission_denied", permissionState })
        return
      }

      // Start connection in parallel with other operations
      const wsPromise = ensureConnection()
      
      const AudioContextClass = getAudioContextClass()
      const ctx = audioCtxRef.current ?? new AudioContextClass({ sampleRate: 48000 })
      audioCtxRef.current = ctx
      
      // Unlock audio if needed (can happen in parallel)
      let unlockPromise: Promise<boolean> | null = null
      if (ctx.state === "suspended") {
        unlockPromise = unlockAudio()
      }

      // Get user media (can happen in parallel with connection)
      // This will show the browser's permission prompt if needed
      // Support multiple browser APIs for maximum compatibility
      console.log("[voice] Requesting microphone access...")
      
      let streamPromise: Promise<MediaStream>
      
      // Try modern API first
      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        streamPromise = navigator.mediaDevices.getUserMedia({
          audio: { 
            channelCount: 1, 
            noiseSuppression: true, 
            echoCancellation: true,
            autoGainControl: true,
            sampleRate: 48000
          },
        })
      } 
      // Fallback for older browsers
      else if ((navigator as any).getUserMedia) {
        streamPromise = new Promise((resolve, reject) => {
          (navigator as any).getUserMedia(
            { audio: true },
            resolve,
            reject
          )
        })
      }
      // Fallback for webkit browsers
      else if ((navigator as any).webkitGetUserMedia) {
        streamPromise = new Promise((resolve, reject) => {
          (navigator as any).webkitGetUserMedia(
            { audio: true },
            resolve,
            reject
          )
        })
      }
      // Fallback for moz browsers
      else if ((navigator as any).mozGetUserMedia) {
        streamPromise = new Promise((resolve, reject) => {
          (navigator as any).mozGetUserMedia(
            { audio: true },
            resolve,
            reject
          )
        })
      }
      else {
        throw new Error("getUserMedia is not supported in this browser. Please use a modern browser like Chrome, Firefox, Safari, or Edge.")
      }

      // Wait for all operations in parallel
      const [ws, stream] = await Promise.all([
        wsPromise,
        streamPromise,
        unlockPromise || Promise.resolve(true),
      ])
      
      if (!ws || ws.readyState !== WebSocket.OPEN) {
        throw new Error("Voice service unavailable")
      }
      
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
      console.log("[voice] Microphone access granted, listening started")
      emitTelemetry("voice.capture_start", { path })
    } catch (err) {
      console.error("[voice] startTalking failed", err)
      
      // Better error handling - distinguish between different error types
      const error = err as Error
      const errorName = error.name || ""
      const errorMessage = error.message || ""
      
      console.log("[voice] Error details:", { errorName, errorMessage, error })
      
      let userMessage = "I couldn't access your microphone. Please check your permissions."
      
      // Check for specific permission errors
      if (
        errorName === "NotAllowedError" ||
        errorName === "PermissionDeniedError" ||
        errorMessage.toLowerCase().includes("permission") ||
        errorMessage.toLowerCase().includes("denied") ||
        errorMessage.toLowerCase().includes("not allowed") ||
        errorMessage.toLowerCase().includes("notallowed")
      ) {
        console.log("[voice] Permission error detected, checking current state...")
        // Double-check permission state after error (non-blocking)
        try {
          const currentPermission = await checkMicrophonePermission()
          console.log("[voice] Current permission state after error:", currentPermission)
          if (currentPermission === "denied") {
            userMessage = "Microphone access is blocked. Please enable it in your browser settings and refresh the page."
          } else {
            userMessage = "Microphone permission was denied. Please allow access when prompted and try again."
          }
        } catch (permCheckError) {
          // Permission check failed, use generic message
          console.warn("[voice] Permission check after error failed:", permCheckError)
          userMessage = "Microphone permission was denied. Please allow access when prompted and try again."
        }
      } else if (
        errorName === "NotFoundError" ||
        errorName === "DevicesNotFoundError" ||
        errorMessage.toLowerCase().includes("device") ||
        errorMessage.toLowerCase().includes("not found")
      ) {
        userMessage = "No microphone found. Please connect a microphone and try again."
      } else if (
        errorName === "NotReadableError" ||
        errorMessage.toLowerCase().includes("readable") ||
        errorMessage.toLowerCase().includes("in use")
      ) {
        userMessage = "Microphone is being used by another application. Please close other apps using the microphone and try again."
      } else if (errorMessage.includes("service unavailable") || errorMessage.includes("Voice service")) {
        userMessage = "Voice service is temporarily unavailable. Please try again in a moment."
      } else if (errorMessage.includes("not supported") || errorMessage.includes("getUserMedia")) {
        userMessage = "Your browser doesn't support microphone access. Please use Chrome, Firefox, Safari, or Edge (latest versions)."
      } else if (errorMessage.includes("secure context") || errorMessage.includes("HTTPS")) {
        userMessage = "Microphone access requires a secure connection (HTTPS). Please access this site using https:// or from localhost."
      }
      
      console.log("[voice] Setting error message:", userMessage)
      setError(userMessage)
      
      // Get permission state for telemetry (non-blocking)
      let finalPermissionState = "unknown"
      try {
        finalPermissionState = await checkMicrophonePermission()
      } catch {
        // Ignore
      }
      
      emitTelemetry("voice.error", { 
        message: error.message || "mic_start_failed",
        errorName,
        errorMessage,
        permissionState: finalPermissionState
      })
      setStage("error")
      setListeningPresence(false)
      cleanupRecorder()
    }
  }

  const stopTalking = () => {
    cleanupRecorder()
    
    // Clear any existing thinking timeout when stopping
    if (thinkingTimeoutRef.current) {
      clearTimeout(thinkingTimeoutRef.current)
      thinkingTimeoutRef.current = null
    }
    
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      setStage((prev) => (prev === "listening" || prev === "connecting" ? "thinking" : prev))
      setMetaPresence("thinking")
      
      // Set timeout for thinking state when stopping - if no response in 60s, reset
      thinkingTimeoutRef.current = setTimeout(() => {
        console.warn("[voice] Thinking timeout after stop - no response, resetting")
        setStage("idle")
        setError("Voice session timed out. Please try again.")
        setListeningPresence(false)
        setSpeakingPresence(false)
        setMetaPresence("resting")
        settlePresence()
        
        if (wsRef.current) {
          try {
            wsRef.current.close()
          } catch {
            // ignore
          }
          wsRef.current = null
        }
        thinkingTimeoutRef.current = null
        emitTelemetry("voice.timeout", { path, reason: "after_stop" })
      }, 60000) // 60 seconds timeout
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

  const resetVoiceState = () => {
    // Clear thinking timeout
    if (thinkingTimeoutRef.current) {
      clearTimeout(thinkingTimeoutRef.current)
      thinkingTimeoutRef.current = null
    }
    
    // Stop any active recording
    cleanupRecorder()
    
    // Flush playback queue
    flushPlaybackQueue()
    
    // Close WebSocket if open
    if (wsRef.current) {
      try {
        wsRef.current.close()
      } catch {
        // ignore
      }
      wsRef.current = null
    }
    
    // Reset all state
    setStage("idle")
    setError(undefined)
    setPartialReply("")
    setFinalReply("")
    setListeningPresence(false)
    setSpeakingPresence(false)
    setMetaPresence("resting")
    settlePresence()
    
    // Reset tracking refs
    replyBufferRef.current = ""
    speechStartAtRef.current = null
    speechEndAtRef.current = null
    firstAudioAtRef.current = null
    connectPromiseRef.current = null
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
      
      // Clear thinking timeout
      if (thinkingTimeoutRef.current) {
        clearTimeout(thinkingTimeoutRef.current)
        thinkingTimeoutRef.current = null
      }
      
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
    resetVoiceState, // Expose reset function for external use
  }
}

// Export return type for components that receive voice state as props
export type VoiceLoopReturn = ReturnType<typeof useVoiceLoop>

