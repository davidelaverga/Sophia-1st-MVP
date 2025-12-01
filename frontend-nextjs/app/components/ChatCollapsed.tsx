"use client"

import { MessageSquare } from "lucide-react"
import { useModeSwitch } from "../hooks/useModeSwitch"
import { useUsageLimitStore } from "../stores/usage-limit-store"

/**
 * ChatCollapsed
 * 
 * Minimal indicator shown when user is in voice mode.
 * Simple click to switch to text focus mode.
 * Includes validation to prevent switching during voice operations.
 */

export function ChatCollapsed() {
  const showToast = useUsageLimitStore((state) => state.showToast)
  
  const { canSwitchToChat, switchToChat } = useModeSwitch({
    onBlocked: (message) => {
      // Show toast with the block reason
      showToast({
        reason: "voice",
        plan_tier: "FREE",
        used: 0,
        limit: 0,
      })
    },
  })
  
  const isDisabled = !canSwitchToChat.canSwitch
  const tooltipMessage = canSwitchToChat.message || "Switch to chat mode"

  return (
    <button
      type="button"
      onClick={switchToChat}
      disabled={isDisabled}
      title={tooltipMessage}
      className="w-full group rounded-3xl bg-sophia-surface p-4 shadow-soft hover:shadow-md transition-all duration-300 animate-fadeIn disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:shadow-soft"
    >
      <div className="flex items-center gap-4">
        {/* Minimal chat icon */}
        <div className="relative flex-shrink-0">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-sophia-purple/10 to-sophia-purple/5 flex items-center justify-center group-hover:from-sophia-purple/20 group-hover:to-sophia-purple/10 transition-all duration-300">
            <MessageSquare className="h-5 w-5 text-sophia-purple" />
          </div>
        </div>

        {/* Text */}
        <div className="flex-1 text-left">
          <p className="text-sm font-semibold text-sophia-text group-hover:text-sophia-purple transition-colors duration-300">
            Switch to chat mode
          </p>
          <p className="text-xs text-sophia-text2">
            Type and read your conversation
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





