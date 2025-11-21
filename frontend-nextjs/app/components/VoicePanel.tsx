"use client"

import { useRef } from "react"
import { Mic, Square, Zap } from "lucide-react"
import { useVoiceLoop } from "../hooks/useVoiceLoop"

const stageLabel: Record<string, string> = {
  idle: "Press and hold whenever you’re ready",
  connecting: "Connecting…",
  listening: "Listening",
  thinking: "Thinking",
  speaking: "Speaking",
  error: "Something went wrong",
}

export function VoicePanel() {
  const { stage, partialReply, finalReply, error, path, needsUnlock, startTalking, stopTalking, bargeIn, unlockAudio } =
    useVoiceLoop()
  const holdRef = useRef(false)
  const pointerIdRef = useRef<number | null>(null)

  const handlePressStart = async () => {
    if (holdRef.current) return
    holdRef.current = true
    try {
      await startTalking()
    } catch {
      holdRef.current = false
    }
  }

  const handlePressEnd = () => {
    if (!holdRef.current) return
    holdRef.current = false
    stopTalking()
  }

  const handleKeyDown = async (event: React.KeyboardEvent<HTMLButtonElement>) => {
    if (event.key === " " || event.key === "Enter") {
      event.preventDefault()
      if (!holdRef.current) {
        holdRef.current = true
        try {
          await startTalking()
        } catch {
          holdRef.current = false
        }
      }
    }
  }

  const handleKeyUp = (event: React.KeyboardEvent<HTMLButtonElement>) => {
    if (event.key === " " || event.key === "Enter") {
      event.preventDefault()
      handlePressEnd()
    }
  }

  const activeReply = partialReply || finalReply
  const showInterrupt = stage === "speaking"

  return (
    <section className="rounded-3xl bg-white p-5 shadow-soft">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-semibold text-sophia-text">Live voice space</p>
          <p className="text-sm text-sophia-text2 sm:text-sm text-xs">{stageLabel[stage]}</p>
        </div>
        {path && (
          <span className="inline-flex w-fit rounded-full bg-sophia-reply px-3 py-1 text-xs font-medium text-sophia-text2 uppercase tracking-wide">
            {path}
          </span>
        )}
      </div>

      <div className="mt-6 flex flex-col items-center gap-4">
        <button
          type="button"
          onPointerDown={(event) => {
            pointerIdRef.current = event.pointerId
            handlePressStart()
          }}
          onPointerUp={(event) => {
            if (pointerIdRef.current === event.pointerId) {
              handlePressEnd()
            }
          }}
          onPointerLeave={(event) => {
            if (pointerIdRef.current === event.pointerId) {
              handlePressEnd()
            }
          }}
          onPointerCancel={(event) => {
            if (pointerIdRef.current === event.pointerId) {
              handlePressEnd()
            }
          }}
          onKeyDown={handleKeyDown}
          onKeyUp={handleKeyUp}
          className={`group relative flex h-16 w-16 items-center justify-center rounded-3xl text-white transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 sm:h-24 sm:w-24 ${
            stage === "listening"
              ? "bg-gradient-to-br from-sophia-purple to-sophia-glow shadow-lg shadow-sophia-purple/40"
              : "bg-gradient-to-br from-sophia-purple to-sophia-glow/60"
          }`}
          aria-pressed={stage === "listening"}
        >
          <Mic className="h-7 w-7 sm:h-10 sm:w-10" />
          {stage === "listening" && (
            <span className="absolute -bottom-7 text-[11px] font-medium text-sophia-text2">Release to send</span>
          )}
        </button>

        {showInterrupt && (
          <button
            type="button"
            className="flex items-center gap-2 rounded-full border border-sophia-text/15 px-3 py-1 text-xs font-medium text-sophia-text"
            onClick={bargeIn}
          >
            <Square className="h-3 w-3" />
            Interrupt
          </button>
        )}
      </div>

        {needsUnlock && (
        <div className="mt-4 w-full rounded-2xl border border-sophia-text/10 bg-sophia-reply/70 px-3 py-2 text-xs text-sophia-text">
          <p>Safari needs one extra tap to enable audio.</p>
          <button
            type="button"
            className="mt-2 inline-flex items-center gap-1 rounded-full bg-white px-3 py-1 text-xs font-medium text-sophia-text"
            onClick={unlockAudio}
          >
            <Zap className="h-3 w-3" />
            Enable voice
          </button>
        </div>
      )}

      {activeReply && (
        <div className="mt-6 rounded-2xl bg-sophia-bubble px-4 py-3 text-sm text-sophia-text">
          {activeReply}
        </div>
      )}

      {error && (
        <p className="mt-4 rounded-2xl bg-sophia-error/10 px-4 py-3 text-sm text-sophia-text" role="status">
          {error}
        </p>
      )}
    </section>
  )
}

