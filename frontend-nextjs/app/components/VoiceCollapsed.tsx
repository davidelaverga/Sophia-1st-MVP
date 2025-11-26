"use client"

import { Mic } from "lucide-react"
import { useFocusModeStore } from "../stores/focus-mode-store"

/**
 * VoiceCollapsed
 * 
 * Minimal indicator shown when user is in text mode.
 * Simple click to switch to voice focus mode.
 */

export function VoiceCollapsed() {
  const setMode = useFocusModeStore((state) => state.setMode)
  const setManualOverride = useFocusModeStore((state) => state.setManualOverride)

  const handleClick = () => {
    setMode("voice")
    setManualOverride(true)
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      onMouseDown={(e) => e.preventDefault()} // Prevent focus loss from composer
      className="w-full group rounded-3xl bg-white p-4 shadow-soft hover:shadow-md transition-all duration-300 animate-fadeIn"
    >
      <div className="flex items-center gap-4">
        {/* Minimal mic icon */}
        <div className="relative flex-shrink-0">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-sophia-purple/10 to-sophia-purple/5 flex items-center justify-center group-hover:from-sophia-purple/20 group-hover:to-sophia-purple/10 transition-all duration-300">
            <Mic className="h-5 w-5 text-sophia-purple" />
          </div>
        </div>

        {/* Text */}
        <div className="flex-1 text-left">
          <p className="text-sm font-semibold text-sophia-text group-hover:text-sophia-purple transition-colors duration-300">
            Switch to voice mode
          </p>
          <p className="text-xs text-sophia-text2">
            Talk with Sophia naturally
          </p>
        </div>

        {/* Arrow indicator */}
        <div className="flex-shrink-0 text-sophia-purple/40 group-hover:text-sophia-purple group-hover:translate-x-1 transition-all duration-300">
          <svg
            className="h-5 w-5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 5l7 7-7 7"
            />
          </svg>
        </div>
      </div>
    </button>
  )
}




