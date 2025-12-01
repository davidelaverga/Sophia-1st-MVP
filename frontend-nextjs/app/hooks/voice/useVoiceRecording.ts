/**
 * Hook for managing voice recording and microphone access
 * Handles getUserMedia, audio processing, and PCM encoding
 */

import { useRef, useCallback } from "react"
import { logger } from "../../lib/error-logger"
import { downsampleTo16kPCM, getAudioContextClass } from "./voice-utils"

export function useVoiceRecording() {
  const streamRef = useRef<MediaStream | null>(null)
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null)
  const processorRef = useRef<ScriptProcessorNode | null>(null)
  const chunkAccumulatorRef = useRef<Float32Array[]>([])
  const audioCtxRef = useRef<AudioContext | null>(null)

  /**
   * Cleanup recording resources
   */
  const cleanupRecorder = useCallback(() => {
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
    // Stop all MediaStream tracks to release microphone
    if (streamRef.current) {
      try {
        streamRef.current.getTracks().forEach((track) => {
          track.stop()
        })
      } catch (err) {
        logger.warn("Failed to stop MediaStream tracks", {
          context: "useVoiceRecording.cleanupRecorder",
          error: err instanceof Error ? err.message : String(err),
        })
      }
      streamRef.current = null
    }
    processorRef.current = null
    sourceRef.current = null
    chunkAccumulatorRef.current = []
  }, [])

  /**
   * Unlock audio context (required for iOS/Safari)
   */
  const unlockAudio = useCallback(async (): Promise<boolean> => {
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
      return true
    } catch (err) {
      logger.error("Audio unlock failed", {
        context: "useVoiceRecording.unlockAudio",
        error: err instanceof Error ? err.message : String(err),
      })
      return false
    }
  }, [])

  /**
   * Start recording from microphone
   * @param onAudioData - Callback for when audio chunks are ready (PCM16 at 16kHz)
   */
  const startRecording = useCallback(async (
    onAudioData: (pcm16: ArrayBuffer) => void
  ): Promise<MediaStream> => {
    const AudioContextClass = getAudioContextClass()
    const ctx = audioCtxRef.current ?? new AudioContextClass({ sampleRate: 48000 })
    audioCtxRef.current = ctx

    // Get microphone access
    let stream: MediaStream
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    } else if ((navigator as any).getUserMedia) {
      stream = await new Promise((resolve, reject) => {
        (navigator as any).getUserMedia({ audio: true }, resolve, reject)
      })
    } else if ((navigator as any).webkitGetUserMedia) {
      stream = await new Promise((resolve, reject) => {
        (navigator as any).webkitGetUserMedia({ audio: true }, resolve, reject)
      })
    } else if ((navigator as any).mozGetUserMedia) {
      stream = await new Promise((resolve, reject) => {
        (navigator as any).mozGetUserMedia({ audio: true }, resolve, reject)
      })
    } else {
      throw new Error("getUserMedia is not supported in this browser. Please use a modern browser like Chrome, Firefox, Safari, or Edge.")
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
      
      // Send chunks every 200ms
      if (secs >= 0.2) {
        const merged = new Float32Array(totalSamples)
        let offset = 0
        for (const chunk of chunkAccumulatorRef.current) {
          merged.set(chunk, offset)
          offset += chunk.length
        }
        chunkAccumulatorRef.current = []
        const pcm16 = downsampleTo16kPCM(merged, ctx.sampleRate)
        onAudioData(pcm16)
      }
    }

    source.connect(processor)
    processor.connect(ctx.destination)

    return stream
  }, [])

  /**
   * Stop recording and cleanup
   */
  const stopRecording = useCallback(() => {
    cleanupRecorder()
  }, [cleanupRecorder])

  /**
   * Close audio context (for cleanup on unmount)
   */
  const closeAudioContext = useCallback(() => {
    if (audioCtxRef.current) {
      try {
        if (audioCtxRef.current.state !== "closed") {
          audioCtxRef.current.close()
        }
      } catch (err) {
        logger.warn("Failed to close AudioContext", {
          context: "useVoiceRecording.closeAudioContext",
          error: err instanceof Error ? err.message : String(err),
        })
      }
      audioCtxRef.current = null
    }
  }, [])

  return {
    stream: streamRef.current,
    unlockAudio,
    startRecording,
    stopRecording,
    cleanupRecorder,
    closeAudioContext,
  }
}
