"use client"

import { useState, useEffect } from "react"
import { postFeedback } from "../lib/api/feedback"
import { useChatStore } from "../stores/chat-store"
import { emitTelemetry } from "../lib/telemetry"

export function SessionFeedbackToast() {
  const sessionFeedback = useChatStore((state) => state.sessionFeedback)
  const closeToast = useChatStore((state) => state.closeSessionFeedback)
  const acknowledge = useChatStore((state) => state.acknowledgeFeedback)
  const turnId = sessionFeedback?.turnId
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string>()

  useEffect(() => {
    if (sessionFeedback?.open && turnId) {
      emitTelemetry("feedback.shown", { gated: false, turn_id: turnId })
    }
  }, [sessionFeedback?.open, turnId])

  if (!sessionFeedback?.open || !turnId) return null

  const handleSubmit = async (helpful: boolean) => {
    setSubmitting(true)
    setError(undefined)
    try {
      await postFeedback({ turnId, helpful })
      emitTelemetry("feedback.submit", { helpful, turn_id: turnId })
      acknowledge(turnId)
      closeToast()
    } catch (err) {
      setError((err as Error).message ?? "Unable to send feedback.")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="pointer-events-auto fixed bottom-4 left-0 right-0 z-40 flex justify-center px-4">
      <div className="flex w-full max-w-md items-center justify-between rounded-2xl border border-sophia-text/10 bg-sophia-surface p-3 text-sm shadow-soft">
        <div>
          <p className="font-semibold text-sophia-text">How did that feel?</p>
          {error && (
            <p className="mt-1 text-xs text-sophia-error">
              {error} —{" "}
              <button type="button" className="underline" onClick={() => {
                acknowledge(turnId)
                closeToast()
              }}>
                Skip feedback
              </button>
            </p>
          )}
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            disabled={submitting}
            className="rounded-full border border-sophia-text/15 px-3 py-1 text-xs font-medium text-sophia-text transition hover:border-sophia-purple/40 disabled:opacity-50"
            onClick={() => handleSubmit(true)}
          >
            👍
          </button>
          <button
            type="button"
            disabled={submitting}
            className="rounded-full border border-sophia-text/15 px-3 py-1 text-xs font-medium text-sophia-text transition hover:border-sophia-purple/40 disabled:opacity-50"
            onClick={() => handleSubmit(false)}
          >
            👎
          </button>
          <button
            type="button"
            className="rounded-full border border-transparent px-2 py-1 text-xs underline text-sophia-text2 hover:text-sophia-text"
            onClick={() => {
              acknowledge(turnId)
              closeToast()
            }}
          >
            Skip
          </button>
        </div>
      </div>
    </div>
  )
}


