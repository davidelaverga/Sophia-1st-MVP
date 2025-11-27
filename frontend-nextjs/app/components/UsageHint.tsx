"use client"

import { useRouter } from "next/navigation"
import { useUsageLimitStore } from "../stores/usage-limit-store"
import { copy } from "../../copy"
import { Sparkles } from "lucide-react"

/**
 * Subtle, non-intrusive usage hint that appears in the footer
 * Only shows when user is approaching their limit (50-79%)
 * Designed to be calm, informative, and never threatening
 */
export function UsageHint() {
  const router = useRouter()
  const hintInfo = useUsageLimitStore((state) => state.hintInfo)

  if (!hintInfo) return null

  const getHintText = () => {
    const remaining = hintInfo.limit - hintInfo.used
    
    switch (hintInfo.reason) {
      case "voice":
        return copy.usageLimit.hintVoice.replace("{remaining}", Math.round(remaining / 60).toString())
      case "text":
        return copy.usageLimit.hintText.replace("{remaining}", remaining.toString())
      case "reflections":
        return copy.usageLimit.hintReflections.replace("{remaining}", remaining.toString())
      default:
        return null
    }
  }

  const hintText = getHintText()
  if (!hintText) return null

  return (
    <div className="flex items-start gap-2 rounded-2xl bg-sophia-purple/5 px-4 py-2.5 text-xs text-sophia-text2 animate-fadeIn">
      <Sparkles className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-sophia-purple/60" />
      <div className="flex-1">
        <p className="leading-relaxed">{hintText}</p>
        {/* 💜 Subtle link to Founding Supporter - Contextual, non-intrusive */}
        <button
          type="button"
          onClick={() => router.push("/founding-supporter")}
          className="mt-1.5 text-xs font-semibold text-sophia-purple hover:text-sophia-glow transition-colors duration-200"
        >
          Learn about unlimited plans →
        </button>
      </div>
    </div>
  )
}
