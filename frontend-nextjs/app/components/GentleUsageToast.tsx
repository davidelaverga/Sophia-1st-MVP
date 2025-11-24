"use client"

import { useEffect, useState } from "react"
import { useUsageLimitStore } from "../stores/usage-limit-store"
import { copy } from "../../copy"
import { Sparkles, X } from "lucide-react"

/**
 * Gentle, non-blocking toast that appears when user reaches 80% of their limit
 * Designed to be informative and calm, never threatening
 * Can be dismissed by the user
 */
export function GentleUsageToast() {
  const toastInfo = useUsageLimitStore((state) => state.toastInfo)
  const dismissToast = useUsageLimitStore((state) => state.dismissToast)
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    if (toastInfo) {
      setIsVisible(true)
    } else {
      setIsVisible(false)
    }
  }, [toastInfo])

  const handleDismiss = () => {
    setIsVisible(false)
    setTimeout(() => dismissToast(), 300) // Wait for fade out
  }

  if (!toastInfo || !isVisible) return null

  const getToastText = () => {
    const remaining = toastInfo.limit - toastInfo.used
    
    switch (toastInfo.reason) {
      case "voice":
        return copy.usageLimit.toastVoice.replace("{remaining}", Math.round(remaining / 60).toString())
      case "text":
        return copy.usageLimit.toastText.replace("{remaining}", remaining.toString())
      case "reflections":
        return copy.usageLimit.toastReflections.replace("{remaining}", remaining.toString())
      default:
        return null
    }
  }

  const toastText = getToastText()
  if (!toastText) return null

  return (
    <div
      className={`fixed bottom-20 left-1/2 z-40 w-full max-w-md -translate-x-1/2 px-4 transition-all duration-300 ${
        isVisible ? "translate-y-0 opacity-100" : "translate-y-4 opacity-0"
      }`}
    >
      <div className="rounded-3xl border border-sophia-purple/20 bg-white p-4 shadow-soft">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-2xl bg-sophia-purple/10">
            <Sparkles className="h-5 w-5 text-sophia-purple" />
          </div>
          <div className="flex-1 space-y-2">
            <p className="text-sm font-medium text-sophia-text">{copy.usageLimit.toastTitle}</p>
            <p className="text-xs leading-relaxed text-sophia-text2">{toastText}</p>
            <button
              type="button"
              onClick={() => {
                window.location.href = "/founding-supporter"
              }}
              className="text-xs font-medium text-sophia-purple hover:underline"
            >
              {copy.usageLimit.toastCta}
            </button>
          </div>
          <button
            type="button"
            onClick={handleDismiss}
            className="flex-shrink-0 rounded-full p-1 text-sophia-text2 transition hover:bg-sophia-user hover:text-sophia-text"
            aria-label="Dismiss"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  )
}

