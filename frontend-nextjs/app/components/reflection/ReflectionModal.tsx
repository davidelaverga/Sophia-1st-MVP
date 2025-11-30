"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import { ReflectionChunk } from "../../hooks/useReflectionPrompt"
import { createReflection, ReflectionAction } from "../../lib/api/reflections"
import { emitTelemetry } from "../../lib/telemetry"
import { t } from "../../../copy"

type ReflectionModalProps = {
  conversationId: string
  chunks: ReflectionChunk[]
  onClose: () => void
}

export function ReflectionModal({ conversationId, chunks, onClose }: ReflectionModalProps) {
  const [selected, setSelected] = useState<string | null>(chunks[0]?.id ?? null)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string>()
  const containerRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    setSelected((prev) => prev ?? chunks[0]?.id ?? null)
  }, [chunks])

  useEffect(() => {
    const node = containerRef.current
    if (!node) return
    const focusable = node.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
    )
    focusable[0]?.focus()

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault()
        onClose()
        return
      }
      if (event.key !== "Tab") return
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      if (!first || !last) return
      if (event.shiftKey) {
        if (document.activeElement === first) {
          event.preventDefault()
          last.focus()
        }
      } else if (document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }

    node.addEventListener("keydown", handleKeyDown)
    return () => {
      node.removeEventListener("keydown", handleKeyDown)
    }
  }, [onClose, chunks])

  const handleSubmit = async (action: ReflectionAction) => {
    if (!selected || submitting) return
    setSubmitting(true)
    setError(undefined)
    emitTelemetry("reflection.submit", { action, chunk_id: selected })
    try {
      await createReflection({ conversationId, chunkId: selected, action })
      emitTelemetry("reflection.submit_ok", { action, chunk_id: selected })
      onClose()
    } catch (err) {
      emitTelemetry("reflection.submit_err", { action, chunk_id: selected })
      setError((err as Error).message ?? "Something went wrong. Please try again.")
      setSubmitting(false)
    }
  }

  const sortedChunks = useMemo(() => chunks.slice(0, 3), [chunks])

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-sophia-text/40 px-3 pb-6 pt-12 backdrop-blur-sm sm:items-center"
      role="dialog"
      aria-modal="true"
      aria-labelledby="reflection-modal-title"
    >
      <div
        ref={containerRef}
        className="w-full max-w-lg rounded-3xl bg-sophia-card p-5 text-sophia-text shadow-soft sm:p-6"
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <p id="reflection-modal-title" className="text-lg font-semibold text-sophia-text">
              {t("reflection.promptTitle")}
            </p>
            <p className="mt-1 text-sm text-sophia-text2">{t("reflection.promptBody")}</p>
          </div>
          <button
            type="button"
            className="rounded-full border border-sophia-text/20 px-2 py-1 text-xs text-sophia-text2 hover:border-sophia-purple/40 hover:text-sophia-purple"
            onClick={onClose}
          >
            {t("reflection.dismiss")}
          </button>
        </div>

        <div className="mt-5 space-y-3" role="radiogroup" aria-label="Reflection choices">
          {sortedChunks.map((chunk) => {
            const isSelected = selected === chunk.id
            return (
              <label
                key={chunk.id}
                className={`flex cursor-pointer flex-col rounded-2xl border px-4 py-3 transition ${
                  isSelected ? "border-sophia-purple bg-sophia-reply" : "border-sophia-text/15 bg-sophia-button"
                }`}
              >
                <input
                  type="radio"
                  name="reflection-option"
                  className="sr-only"
                  value={chunk.id}
                  checked={isSelected}
                  onChange={() => setSelected(chunk.id)}
                />
                <span className="text-sm text-sophia-text">{chunk.text}</span>
                <span className="mt-1 text-xs text-sophia-text2">{chunk.reason}</span>
              </label>
            )
          })}
        </div>

        {error && <p className="mt-3 text-sm text-sophia-error">{error}</p>}

        <div className="mt-5 grid gap-3 sm:grid-cols-2">
          <button
            type="button"
            className="rounded-2xl border border-sophia-text/20 px-4 py-3 text-sm font-medium text-sophia-text transition hover:border-sophia-purple/40 disabled:opacity-50"
            disabled={!selected || submitting}
            onClick={() => handleSubmit("save")}
          >
            {t("reflection.savePrivate")}
          </button>
          <button
            type="button"
            className="rounded-2xl bg-sophia-purple px-4 py-3 text-sm font-semibold text-white transition hover:bg-sophia-glow disabled:opacity-60"
            disabled={!selected || submitting}
            onClick={() => handleSubmit("share_discord")}
          >
            {t("reflection.shareDiscord")}
          </button>
        </div>

        <button
          type="button"
          className="mt-4 w-full text-center text-xs font-medium text-sophia-text2 underline underline-offset-2"
          onClick={onClose}
        >
          {t("reflection.dismiss")}
        </button>
      </div>
    </div>
  )
}

