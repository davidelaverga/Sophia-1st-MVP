"use client"

import { useEffect, useState } from "react"
import { emitTelemetry } from "../lib/telemetry"
import { useChatStore } from "../stores/chat-store"

export type ReflectionChunk = {
  id: string
  text: string
  ts: number
  reason: string
}

type ReflectionResponse = {
  allow?: boolean
  chunks?: ReflectionChunk[]
  reason?: string
}

export function useReflectionPrompt(conversationId?: string, turnId?: string) {
  const [chunks, setChunks] = useState<ReflectionChunk[] | null>(null)

  useEffect(() => {
    if (!conversationId || !turnId) return

    let cancelled = false
    const controller = new AbortController()

    const fetchPrompt = async () => {
      try {
        const response = await fetch(`/api/conversations/${conversationId}/reflection-prompt`, {
          signal: controller.signal,
          headers: { Accept: "application/json" },
        })
        if (!response.ok) {
          return
        }
        const payload = (await response.json()) as ReflectionResponse
        if (cancelled || !payload) return
        if (payload.allow && payload.chunks && payload.chunks.length > 0) {
          const trimmed = payload.chunks.slice(0, 3)
          useChatStore.getState().closeSessionFeedback()
          setChunks(trimmed)
          emitTelemetry("reflection.prompt_shown", { turn_id: turnId })
        } else if (payload.allow === false && payload.reason) {
          emitTelemetry("reflection.prompt_denied", { reason: payload.reason })
        }
      } catch {
        // silent fail
      }
    }

    fetchPrompt()

    return () => {
      cancelled = true
      controller.abort()
    }
  }, [conversationId, turnId])

  const dismiss = () => {
    setChunks(null)
  }

  return { chunks, dismiss }
}





