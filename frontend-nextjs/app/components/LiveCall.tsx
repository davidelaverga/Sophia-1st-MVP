"use client"

import React, { useEffect, useRef, useState } from "react"

function httpToWs(url: string) {
  if (url.startsWith("https://")) return url.replace("https://", "wss://")
  if (url.startsWith("http://")) return url.replace("http://", "ws://")
  return url
}

// Downsample Float32Array from input sampleRate to 16k, then encode PCM16 little-endian
function downsampleTo16kPCM(intput: Float32Array, inputSampleRate: number): ArrayBuffer {
  const targetRate = 16000
  if (inputSampleRate === targetRate) {
    // Encode directly to PCM16
    const pcm = new Int16Array(intput.length)
    for (let i = 0; i < intput.length; i++) {
      const s = Math.max(-1, Math.min(1, intput[i]))
      pcm[i] = s < 0 ? s * 0x8000 : s * 0x7fff
    }
    return pcm.buffer
  }
  const ratio = inputSampleRate / targetRate
  const newLength = Math.floor(intput.length / ratio)
  const result = new Float32Array(newLength)
  let pos = 0
  let idx = 0
  while (pos < newLength) {
    const nextIdx = Math.floor((pos + 1) * ratio)
    let sum = 0
    let count = 0
    for (let i = idx; i < nextIdx && i < intput.length; i++) {
      sum += intput[i]
      count++
    }
    result[pos] = sum / (count || 1)
    pos++
    idx = nextIdx
  }
  const pcm = new Int16Array(result.length)
  for (let i = 0; i < result.length; i++) {
    const s = Math.max(-1, Math.min(1, result[i]))
    pcm[i] = s < 0 ? s * 0x8000 : s * 0x7fff
  }
  return pcm.buffer
}

export default function LiveCall() {
  const [connected, setConnected] = useState(false)
  const [listening, setListening] = useState(false)
  const [partial, setPartial] = useState("")
  const [reply, setReply] = useState("")
  const wsRef = useRef<WebSocket | null>(null)
  const acRef = useRef<AudioContext | null>(null)
  const procRef = useRef<ScriptProcessorNode | null>(null)
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null)
  // Simple playback queue for streaming TTS chunk URLs
  const ttsQueueRef = useRef<string[]>([])
  const playingRef = useRef(false)
  const audioChunkBuffersRef = useRef<Uint8Array[]>([])

  const playNextInQueue = () => {
    if (playingRef.current) return
    const url = ttsQueueRef.current.shift()
    if (!url) return
    playingRef.current = true
    const audio = new Audio(url)
    audio.onended = () => {
      playingRef.current = false
      playNextInQueue()
    }
    audio.onerror = () => {
      playingRef.current = false
      playNextInQueue()
    }
    audio.play().catch(() => {
      playingRef.current = false
      playNextInQueue()
    })
  }

  // Messages UI state
  const [tokens, setTokens] = useState<string>("")

  const startCall = async () => {
    if (connected) return
    const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"
    const wsUrl = httpToWs(base) + "/ws/voice"
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => setConnected(true)
    ws.onclose = () => {
      setConnected(false)
      setListening(false)
    }
    ws.onerror = () => {}
    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data)
        if (data.type === "partial_transcript") {
          setPartial(data.text || "")
        } else if (data.type === "final_transcript") {
          setPartial(data.text || "")
          setTokens("")
          setReply("")
        } else if (data.type === "token") {
          setTokens((prev) => prev + (data.text || ""))
        } else if (data.type === "reply_done") {
          setReply(data.text || "")
        } else if (data.type === "audio_url_chunk") {
          const u = data.audio_url as string
          if (u && /^https?:\/\//.test(u)) {
            ttsQueueRef.current.push(u)
            playNextInQueue()
          }
        } else if (data.type === "audio_chunk") {
          // Streaming base64 audio chunks. We accumulate per reply until eos, then play.
          try {
            const eos = !!data.eos
            const b64 = data.b64 as string
            if (b64 && !eos) {
              const bin = Uint8Array.from(atob(b64), c => c.charCodeAt(0))
              audioChunkBuffersRef.current.push(bin)
            }
            if (eos) {
              const total = audioChunkBuffersRef.current.reduce((acc, u) => acc + u.byteLength, 0)
              if (total > 0) {
                const merged = new Uint8Array(total)
                let off = 0
                for (const u of audioChunkBuffersRef.current) { merged.set(u, off); off += u.byteLength }
                audioChunkBuffersRef.current = []
                const blob = new Blob([merged], { type: data.mime || 'audio/mpeg' })
                const url = URL.createObjectURL(blob)
                ttsQueueRef.current.push(url)
                playNextInQueue()
                // Revoke URL after some time
                setTimeout(() => URL.revokeObjectURL(url), 30000)
              }
            }
          } catch {}
        } else if (data.type === "audio_url") {
          if (data.audio_url && /^https?:\/\//.test(data.audio_url)) {
            // If we didn't stream chunks, play the single URL
            ttsQueueRef.current.push(data.audio_url)
            playNextInQueue()
          }
        }
      } catch {
        // ignore
      }
    }

    // Start mic capture after WS connects
    ws.addEventListener("open", async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, noiseSuppression: true, echoCancellation: true } })
        const ac = new AudioContext({ sampleRate: 48000 })
        acRef.current = ac
        const source = ac.createMediaStreamSource(stream)
        sourceRef.current = source
        const proc = ac.createScriptProcessor(4096, 1, 1)
        procRef.current = proc
        let lastSend = performance.now()
        let chunk: Float32Array[] = []

        proc.onaudioprocess = (e) => {
          const input = e.inputBuffer.getChannelData(0)
          // accumulate until ~200ms at 48kHz → 9600 samples
          chunk.push(new Float32Array(input))
          const now = performance.now()
          const need = 0.2 // seconds
          const totalSamples = chunk.reduce((acc, c) => acc + c.length, 0)
          const secs = totalSamples / ac.sampleRate
          if (secs >= need && wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            // merge
            const merged = new Float32Array(totalSamples)
            let off = 0
            for (const c of chunk) { merged.set(c, off); off += c.length }
            chunk = []
            const pcm16 = downsampleTo16kPCM(merged, ac.sampleRate)
            wsRef.current.send(pcm16)
            lastSend = now
          }
        }

        source.connect(proc)
        proc.connect(ac.destination)
        setListening(true)
      } catch (err) {
        console.error("Mic error", err)
        ws.close()
      }
    })
  }

  const endCall = () => {
    try { procRef.current?.disconnect(); } catch {}
    try { sourceRef.current?.disconnect(); } catch {}
    try { acRef.current?.close(); } catch {}
    procRef.current = null
    sourceRef.current = null
    acRef.current = null
    setListening(false)
    try { wsRef.current?.close(); } catch {}
    wsRef.current = null
  }

  useEffect(() => {
    return () => { endCall() }
  }, [])

  return (
    <div className="bg-gradient-to-br from-dark-card via-gray-800/50 to-dark-card border border-dark-border rounded-2xl p-6 space-y-4">
      <div className="flex items-center gap-3">
        <button onClick={startCall} disabled={connected} className="px-4 py-2 rounded-xl bg-green-600 text-white disabled:bg-gray-600">Start Call</button>
        <button onClick={endCall} disabled={!connected} className="px-4 py-2 rounded-xl bg-red-600 text-white disabled:bg-gray-600">End</button>
        <span className="text-sm text-gray-300">{connected ? (listening ? "Live (mic on)" : "Connected") : "Disconnected"}</span>
      </div>
      <div className="text-sm text-gray-300"><span className="font-semibold text-gray-100">You (partial):</span> {partial || ""}</div>
      <div className="text-sm text-gray-300"><span className="font-semibold text-gray-100">Sophia (stream):</span> {tokens}</div>
      {reply && (
        <div className="text-sm text-gray-100 font-medium">Final reply: {reply}</div>
      )}
      <div className="text-xs text-gray-500">Tip: keep sentences short for fastest replies.</div>
    </div>
  )
}
