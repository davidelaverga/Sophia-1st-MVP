"use client"

import { useRef, useEffect } from "react"
import { Mic, Square, Zap } from "lucide-react"
import type { VoiceLoopReturn } from "../hooks/useVoiceLoop"
import { Waveform } from "./Waveform"
import { VoiceTranscript } from "./VoiceTranscript"
import { useFocusModeStore } from "../stores/focus-mode-store"
import { useUsageLimitStore } from "../stores/usage-limit-store"

const stageLabel: Record<string, string> = {
  idle: "Press and hold whenever you're ready",
  connecting: "Connecting…",
  listening: "Listening",
  thinking: "Thinking",
  speaking: "Speaking",
  error: "Something went wrong",
}

type VoicePanelProps = {
  voiceState: VoiceLoopReturn
}

export function VoicePanel({ voiceState }: VoicePanelProps) {
  const { stage, partialReply, finalReply, error, path, needsUnlock, stream, startTalking, stopTalking, bargeIn, unlockAudio } =
    voiceState
  
  // Focus mode management
  const setMode = useFocusModeStore((state) => state.setMode)
  const setManualOverride = useFocusModeStore((state) => state.setManualOverride)
  
  // Check if usage limit modal is open - block voice interaction
  const isModalOpen = useUsageLimitStore((state) => state.isOpen)
  
  // Stop recording if modal opens
  useEffect(() => {
    const isRecording = stage === "listening"
    if (isModalOpen && isRecording) {
      stopTalking()
    }
  }, [isModalOpen, stopTalking, stage])
  
  // Map voice stage to presence state for waveform
  const getWaveformState = () => {
    if (stage === "listening") return "listening"
    if (stage === "thinking") return "thinking"
    if (stage === "speaking") return "speaking"
    return "resting"
  }

  // Toggle recording on/off with each click
  const handleToggleRecording = async () => {
    // Block interaction if modal is open
    if (isModalOpen) {
      return
    }
    
    if (stage === "thinking" || stage === "speaking") {
      // Don't allow toggle while processing
      return
    }

    const isRecording = stage === "listening"
    
    if (isRecording) {
      // Stop recording - immediate feedback
      stopTalking()
    } else {
      // Start recording - immediate visual feedback
      // Switch to voice focus mode for smooth transition
      setMode("voice")
      setManualOverride(true)
      
      // Start async operations in background (don't await)
      // This allows immediate visual feedback
      startTalking().catch((error) => {
        console.error("[VoicePanel] Failed to start talking:", error)
      })
    }
  }

  const handleKeyPress = async (event: React.KeyboardEvent<HTMLButtonElement>) => {
    if (event.key === " " || event.key === "Enter") {
      event.preventDefault()
      handleToggleRecording()
    }
  }

  const activeReply = partialReply || finalReply
  const showInterrupt = stage === "speaking"

  return (
    <section 
      className={`rounded-3xl bg-sophia-surface p-5 pb-6 shadow-soft transition-all duration-500 ${
        stage === "thinking" 
          ? "animate-ringBreathe" 
          : ""
      }`}
    >
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

      {/* Voice transcript - Sophia's voice responses */}
      <div className="mt-4">
        <VoiceTranscript partialReply={partialReply} finalReply={finalReply} />
      </div>

      <div className="mt-6 flex flex-col items-center gap-4">
        {/* Waveform visualization - ABOVE the button for better visibility */}
        <div className="w-full max-w-xs">
          <Waveform
            stream={stream ?? undefined}
            presenceState={getWaveformState()}
          />
        </div>

        {/* Button with hint text below */}
        <div className="flex flex-col items-center gap-2">
          <button
            type="button"
            onClick={handleToggleRecording}
            onKeyDown={handleKeyPress}
            disabled={stage === "thinking" || stage === "speaking" || isModalOpen}
            className={`group relative flex h-16 w-16 items-center justify-center rounded-3xl text-white transition-all duration-300 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 sm:h-24 sm:w-24 ${
              isModalOpen
                ? "bg-gradient-to-br from-sophia-purple/40 to-sophia-glow/30 opacity-50 cursor-not-allowed"
                : stage === "listening"
                ? "bg-gradient-to-br from-sophia-purple to-sophia-glow shadow-lg shadow-sophia-purple/40 scale-105"
                : stage === "thinking"
                ? "bg-gradient-to-br from-sophia-purple/60 to-sophia-glow/40 opacity-60 cursor-not-allowed"
                : "bg-gradient-to-br from-sophia-purple to-sophia-glow/60 hover:scale-105"
            }`}
            aria-pressed={stage === "listening"}
            aria-busy={stage === "thinking" || isModalOpen}
            aria-label={stage === "listening" ? "Stop recording" : "Start recording"}
          >
            <Mic className="h-7 w-7 sm:h-10 sm:w-10" />
          </button>
          
          {/* Status text */}
          {stage === "listening" && (
            <span className="text-[11px] font-medium text-sophia-text2 animate-fadeIn">Click to stop & send</span>
          )}
          {stage === "thinking" && (
            <span className="text-xs font-medium text-sophia-purple animate-pulse">Sophia is thinking...</span>
          )}
        </div>

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
            className="mt-2 inline-flex items-center gap-1 rounded-full bg-sophia-button px-3 py-1 text-xs font-medium text-sophia-text"
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

