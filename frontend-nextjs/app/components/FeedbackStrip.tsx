"use client"

import { useEffect, useState } from "react"
import { postFeedback } from "../lib/api/feedback"
import { useChatStore } from "../stores/chat-store"
import { emitTelemetry } from "../lib/telemetry"

const TAGS = [
  { id: "clarity", label: "Clarity" },
  { id: "empathy", label: "Care" },
  { id: "grounding", label: "Grounding" },
  { id: "confusing", label: "Confusing" },
  { id: "slow", label: "Too slow" },
] as const

type FeedbackStripProps = {
  turnId: string
}

export function FeedbackStrip({ turnId }: FeedbackStripProps) {
  const gate = useChatStore((state) => state.feedbackGate)
  const acknowledge = useChatStore((state) => state.acknowledgeFeedback)
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState<boolean | null>(null)
  const [error, setError] = useState<string>()
  const [selectedTag, setSelectedTag] = useState<string>()

  const visible = gate?.allowed && gate.turnId === turnId

  useEffect(() => {
    if (visible) {
      emitTelemetry("feedback.shown", { gated: true, turn_id: turnId })
    }
  }, [visible, turnId])

  if (!visible) return null

  const handleSubmit = async (helpful: boolean, tag?: string) => {
    setSubmitting(true)
    setError(undefined)
    try {
      await postFeedback({ turnId, helpful, tag: tag as any })
      emitTelemetry("feedback.submit", { helpful, tag, turn_id: turnId })
      setSubmitted(helpful)
      acknowledge(turnId)
    } catch (err) {
      setError((err as Error).message ?? "Unable to send feedback. Please try again.")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="mt-3 rounded-2xl border border-sophia-text/10 bg-sophia-card/80 px-3 py-2 text-sm text-sophia-text">
      {!submitted ? (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs text-sophia-text2">Did this help?</span>
          <button
            type="button"
            className="rounded-xl bg-sophia-user px-3 py-1 text-xs font-medium text-sophia-text transition hover:bg-sophia-user/70 disabled:opacity-50"
            disabled={submitting}
            onClick={() => handleSubmit(true)}
          >
            👍 Yes
          </button>
          <button
            type="button"
            className="rounded-xl bg-sophia-user px-3 py-1 text-xs font-medium text-sophia-text transition hover:bg-sophia-user/70 disabled:opacity-50"
            disabled={submitting}
            onClick={() => handleSubmit(false)}
          >
            👎 Not quite
          </button>
          {error && (
            <span className="text-xs text-sophia-error">
              {error} —{" "}
              <button
                type="button"
                className="underline"
                onClick={() => acknowledge(turnId)}
              >
                Skip feedback
              </button>
            </span>
          )}
        </div>
      ) : (
        <div className="space-y-2">
          <p className="text-xs text-sophia-text2">Thanks — I’m learning.</p>
          <div className="flex flex-wrap gap-2">
            {TAGS.map((tag) => (
              <button
                key={tag.id}
                type="button"
                className={`rounded-full border px-3 py-1 text-xs transition ${
                  selectedTag === tag.id
                    ? "border-sophia-purple bg-sophia-purple text-white"
                    : "border-sophia-text/20 bg-sophia-button text-sophia-text"
                }`}
                disabled={submitting}
                onClick={() => {
                  setSelectedTag(tag.id)
                  handleSubmit(submitted, tag.id)
                }}
              >
                {tag.label}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}


