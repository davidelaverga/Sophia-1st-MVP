"use client"

import { useRef, useEffect } from "react"
import { Mic, Square } from "lucide-react"
import type { VoiceLoopReturn } from "../hooks/useVoiceLoop"
import { Waveform } from "./Waveform"
import { ChatCollapsed } from "./ChatCollapsed"
import { VoiceTranscript } from "./VoiceTranscript"
import { useFocusModeStore } from "../stores/focus-mode-store"
import { useUsageLimitStore } from "../stores/usage-limit-store"

/**
 * VoiceFocusView
 * 
 * Minimalist voice panel in focus mode - clean, distraction-free experience.
 * Voice interaction with full conversation transcript visible.
 * 
 * IMPORTANT: Receives voice state as props to avoid multiple useVoiceLoop instances
 */

type VoiceFocusViewProps = {
  voiceState: VoiceLoopReturn
}

export function VoiceFocusView({ voiceState }: VoiceFocusViewProps) {
  const { 
    stage, 
    partialReply, 
    finalReply, 
    error, 
    stream, 
    startTalking, 
    stopTalking, 
    bargeIn 
  } = voiceState
  
  const setManualOverride = useFocusModeStore((state) => state.setManualOverride)
  const isRecordingRef = useRef(false)
  
  // Check if usage limit modal is open - block voice interaction
  const isModalOpen = useUsageLimitStore((state) => state.isOpen)
  
  // Stop recording if modal opens
  useEffect(() => {
    if (isModalOpen && isRecordingRef.current) {
      isRecordingRef.current = false
      stopTalking()
    }
  }, [isModalOpen, stopTalking])

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

    if (isRecordingRef.current) {
      // Stop recording - immediate feedback
      isRecordingRef.current = false
      stopTalking()
    } else {
      // Start recording - immediate visual feedback
      isRecordingRef.current = true
      setManualOverride(true) // Keep user in voice mode
      
      // Start async operations in background (don't await)
      // This allows immediate visual feedback
      startTalking().catch(() => {
        isRecordingRef.current = false
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
    <div className="space-y-4">
      {/* Chat collapsed indicator - easy switch to chat mode */}
      <ChatCollapsed />
      
      <section 
        className={`rounded-3xl bg-white p-6 shadow-soft animate-fadeIn transition-all duration-500 ${
          stage === "thinking" 
            ? "animate-ringBreathe" 
            : ""
        }`}
      >
        {/* Voice transcript - Sophia's voice responses */}
        <VoiceTranscript partialReply={partialReply} finalReply={finalReply} />

        {/* Waveform visualization */}
        <div className={`flex justify-center ${partialReply || finalReply ? "mt-6 mb-6" : "mb-6"}`}>
          <div className="w-full max-w-md">
            <Waveform
              stream={stream ?? undefined}
              presenceState={getWaveformState()}
            />
          </div>
        </div>

        {/* Main button area */}
        <div className="flex flex-col items-center gap-4">
          {/* Rectangular microphone button (modern style) */}
          <div className="flex flex-col items-center gap-2">
            <button
              type="button"
              onClick={handleToggleRecording}
              onKeyDown={handleKeyPress}
              disabled={stage === "thinking" || stage === "speaking" || isModalOpen}
              className={`group relative flex h-20 w-20 items-center justify-center rounded-3xl text-white transition-all duration-300 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 sm:h-24 sm:w-24 ${
                isModalOpen
                  ? "bg-gradient-to-br from-sophia-purple/40 to-sophia-glow/30 opacity-50 cursor-not-allowed"
                  : stage === "listening"
                  ? "bg-gradient-to-br from-sophia-purple to-sophia-glow shadow-lg shadow-sophia-purple/40 scale-105"
                  : stage === "thinking"
                  ? "bg-gradient-to-br from-sophia-purple/60 to-sophia-glow/40 opacity-60 cursor-not-allowed"
                  : "bg-gradient-to-br from-sophia-purple to-sophia-glow/60 hover:shadow-md hover:scale-105"
              }`}
              aria-pressed={stage === "listening"}
              aria-busy={stage === "thinking" || isModalOpen}
              aria-label={stage === "listening" ? "Stop recording" : "Start recording"}
            >
              <Mic className="h-8 w-8 sm:h-10 sm:w-10" />
            </button>
            
            {/* Status text */}
            {stage === "listening" && (
              <span className="text-xs font-medium text-sophia-text2 animate-fadeIn">
                Click to stop & send
              </span>
            )}
            {stage === "thinking" && (
              <span className="text-xs font-medium text-sophia-purple animate-pulse">
                Sophia is thinking...
              </span>
            )}
          </div>

          {/* Interrupt button when Sophia is speaking */}
          {showInterrupt && (
            <button
              type="button"
              className="flex items-center gap-2 rounded-full border border-sophia-text/15 px-3 py-1.5 text-xs font-medium text-sophia-text hover:bg-sophia-text/5 transition-colors duration-200"
              onClick={bargeIn}
            >
              <Square className="h-3 w-3" />
              Interrupt
            </button>
          )}
        </div>

        {/* Error message */}
        {error && (
          <p className="mt-4 rounded-2xl bg-sophia-error/10 px-4 py-3 text-sm text-sophia-text" role="status">
            {error}
          </p>
        )}
      </section>
    </div>
  )
}




