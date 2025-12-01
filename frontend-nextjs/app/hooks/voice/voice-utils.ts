/**
 * Utility functions for voice processing
 */

export const PREBUFFER_CHUNKS = 3
export const FIRST_AUDIO_TARGET_MS = 200

export type VoiceStage = "idle" | "connecting" | "listening" | "thinking" | "speaking" | "error"
export type RouterPath = "direct" | "light" | "agentic"

export type QueuedChunk = {
  url: string
  revokeOnUse: boolean
}

/**
 * Convert HTTP/HTTPS URL to WebSocket URL
 */
export const httpToWs = (url: string): string => {
  if (url.startsWith("https://")) return url.replace("https://", "wss://")
  if (url.startsWith("http://")) return url.replace("http://", "ws://")
  return url
}

/**
 * Convert base64 string to Uint8Array
 */
export const base64ToUint8Array = (b64: string): Uint8Array => {
  const raw = atob(b64)
  const bytes = new Uint8Array(raw.length)
  for (let i = 0; i < raw.length; i += 1) {
    bytes[i] = raw.charCodeAt(i)
  }
  return bytes
}

/**
 * Get AudioContext constructor (with webkit fallback)
 */
export const getAudioContextClass = (): typeof AudioContext => {
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

/**
 * Downsample audio to 16kHz PCM16
 */
export function downsampleTo16kPCM(input: Float32Array, inputSampleRate: number): ArrayBuffer {
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
