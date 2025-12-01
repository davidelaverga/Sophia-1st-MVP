/**
 * Hook for managing audio playback queue
 * Handles enqueueing, playback, and cleanup of audio chunks
 */

import { useRef, useCallback } from "react"
import { logger } from "../../lib/error-logger"
import { emitTelemetry } from "../../lib/telemetry"
import type { QueuedChunk, RouterPath } from "./voice-utils"
import { PREBUFFER_CHUNKS, FIRST_AUDIO_TARGET_MS, base64ToUint8Array } from "./voice-utils"

type UseAudioPlaybackProps = {
  path?: RouterPath
  onPlaybackComplete?: () => void
}

export function useAudioPlayback({ path, onPlaybackComplete }: UseAudioPlaybackProps = {}) {
  const playbackQueueRef = useRef<QueuedChunk[]>([])
  const currentAudioRef = useRef<HTMLAudioElement | null>(null)
  const isPlayingRef = useRef(false)
  const hasStartedPlaybackRef = useRef(false)
  const prebufferOverrideRef = useRef(false)
  const streamEndedRef = useRef(false)
  const firstChunkAtRef = useRef<number | null>(null)

  /**
   * Stop current audio playback and revoke blob URL
   */
  const stopCurrentAudio = useCallback(() => {
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
      } catch (err) {
        logger.warn("Failed to revoke blob URL in stopCurrentAudio", {
          context: "useAudioPlayback.stopCurrentAudio",
          error: err instanceof Error ? err.message : String(err),
        })
      }
    }
    
    currentAudioRef.current = null
    isPlayingRef.current = false
  }, [])

  /**
   * Flush entire playback queue and stop current audio
   */
  const flushPlaybackQueue = useCallback(() => {
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
    hasStartedPlaybackRef.current = false
    prebufferOverrideRef.current = false
    streamEndedRef.current = false
    firstChunkAtRef.current = null
  }, [stopCurrentAudio])

  /**
   * Reset playback tracking without flushing queue
   */
  const resetPlaybackTracking = useCallback(() => {
    hasStartedPlaybackRef.current = false
    prebufferOverrideRef.current = false
    streamEndedRef.current = false
    firstChunkAtRef.current = null
  }, [])

  /**
   * Start playing next chunk if ready (prebuffered or override)
   */
  const startNextChunkIfReady = useCallback(() => {
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
        if (latency < FIRST_AUDIO_TARGET_MS) {
          emitTelemetry("voice.prebuffer_success", { latency_ms: Math.round(latency), path })
        }
      }
    }

    const audio = new Audio(nextChunk.url)
    audio.preload = "auto"
    currentAudioRef.current = audio
    isPlayingRef.current = true

    const finalize = () => {
      // Revoke blob URL immediately after playback
      if (nextChunk.revokeOnUse && nextChunk.url.startsWith("blob:")) {
        try {
          URL.revokeObjectURL(nextChunk.url)
        } catch (err) {
          logger.warn("Failed to revoke blob URL after playback", {
            context: "useAudioPlayback.finalize",
            error: err instanceof Error ? err.message : String(err),
          })
        }
      }

      stopCurrentAudio()
      
      if (playbackQueueRef.current.length > 0) {
        startNextChunkIfReady()
      } else if (streamEndedRef.current) {
        resetPlaybackTracking()
        onPlaybackComplete?.()
      }
    }

    audio.onended = finalize
    audio.onerror = finalize
    audio.onabort = finalize

    audio
      .play()
      .then(() => {
        // Playback started successfully
      })
      .catch(() => {
        finalize()
      })
  }, [path, stopCurrentAudio, resetPlaybackTracking, onPlaybackComplete])

  /**
   * Enqueue audio chunk for playback
   */
  const enqueueChunk = useCallback((chunk: QueuedChunk) => {
    playbackQueueRef.current.push(chunk)
    if (!firstChunkAtRef.current) {
      firstChunkAtRef.current = performance.now()
    }
    startNextChunkIfReady()
  }, [startNextChunkIfReady])

  /**
   * Enqueue base64 audio chunk
   */
  const enqueueBase64Chunk = useCallback((b64: string, mime?: string) => {
    try {
      const bytes = base64ToUint8Array(b64)
      const blob = new Blob([bytes as BlobPart], { type: mime || "audio/wav" })
      const url = URL.createObjectURL(blob)
      enqueueChunk({ url, revokeOnUse: true })
    } catch (err) {
      console.warn("[useAudioPlayback] failed to enqueue base64 chunk", err)
    }
  }, [enqueueChunk])

  /**
   * Enqueue remote URL chunk
   */
  const enqueueRemoteChunk = useCallback((url?: string) => {
    if (!url || !/^https?:\/\//.test(url)) return
    enqueueChunk({ url, revokeOnUse: false })
  }, [enqueueChunk])

  /**
   * Mark stream as ended (will complete playback after queue drains)
   */
  const markStreamEnded = useCallback(() => {
    streamEndedRef.current = true
    prebufferOverrideRef.current = true
    
    if (!isPlayingRef.current) {
      resetPlaybackTracking()
      onPlaybackComplete?.()
    }
  }, [resetPlaybackTracking, onPlaybackComplete])

  /**
   * Force start playback immediately (skip prebuffering)
   */
  const forcePrebufferOverride = useCallback(() => {
    prebufferOverrideRef.current = true
    startNextChunkIfReady()
  }, [startNextChunkIfReady])

  return {
    enqueueBase64Chunk,
    enqueueRemoteChunk,
    flushPlaybackQueue,
    markStreamEnded,
    forcePrebufferOverride,
    isPlaying: isPlayingRef.current,
  }
}
