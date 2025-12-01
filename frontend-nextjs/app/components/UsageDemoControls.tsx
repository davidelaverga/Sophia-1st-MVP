"use client"

import { useState } from "react"
import { useUsageLimitStore } from "../stores/usage-limit-store"
import { Settings, X } from "lucide-react"

/**
 * Demo controls for testing usage alerts
 * Only visible in development or when ?demo=true is in URL
 */
export function UsageDemoControls() {
  const [isOpen, setIsOpen] = useState(false)
  const showHint = useUsageLimitStore((state) => state.showHint)
  const showToast = useUsageLimitStore((state) => state.showToast)
  const showModal = useUsageLimitStore((state) => state.showModal)
  const dismissHint = useUsageLimitStore((state) => state.dismissHint)
  const dismissToast = useUsageLimitStore((state) => state.dismissToast)

  // Only show in development or with ?demo=true
  const isDemoMode = 
    process.env.NODE_ENV === "development" || 
    (typeof window !== "undefined" && window.location.search.includes("demo=true"))

  if (!isDemoMode) return null

  const demoUsageInfo = {
    voice: {
      reason: "voice" as const,
      plan_tier: "FREE" as const,
      limit: 600, // 10 minutes
      used: 0,
    },
    text: {
      reason: "text" as const,
      plan_tier: "FREE" as const,
      limit: 1800, // 30 minutes
      used: 0,
    },
    reflections: {
      reason: "reflections" as const,
      plan_tier: "FREE" as const,
      limit: 4,
      used: 0,
    },
  }

  const triggerHint = (type: "voice" | "text" | "reflections", percent: number) => {
    const info = { ...demoUsageInfo[type] }
    info.used = Math.floor(info.limit * (percent / 100))
    showHint(info)
  }

  const triggerToast = (type: "voice" | "text" | "reflections", percent: number) => {
    const info = { ...demoUsageInfo[type] }
    info.used = Math.floor(info.limit * (percent / 100))
    showToast(info)
  }

  const triggerModal = (type: "voice" | "text" | "reflections") => {
    const info = { ...demoUsageInfo[type] }
    info.used = info.limit
    showModal(info)
  }

  const clearAll = () => {
    dismissHint()
    dismissToast()
  }

  return (
    <>
      {/* Floating button to open controls */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="fixed bottom-4 right-4 z-[100] flex h-12 w-12 items-center justify-center rounded-full bg-red-500 text-white shadow-lg transition hover:bg-red-600"
        title="Demo Controls"
      >
        {isOpen ? <X className="h-5 w-5" /> : <Settings className="h-5 w-5" />}
      </button>

      {/* Controls panel */}
      {isOpen && (
        <div className="fixed bottom-20 right-4 z-[100] w-80 rounded-2xl border border-sophia-card-border bg-sophia-surface p-4 shadow-xl">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-sm font-bold text-gray-900">Usage Demo Controls</h3>
            <button
              type="button"
              onClick={clearAll}
              className="text-xs text-red-500 hover:underline"
            >
              Clear All
            </button>
          </div>

          {/* Voice Controls */}
          <div className="mb-4 space-y-2 rounded-lg border border-purple-200 bg-purple-50 p-3">
            <p className="text-xs font-semibold text-purple-900">Voice Chat</p>
            <div className="flex flex-wrap gap-1">
              <button
                type="button"
                onClick={() => triggerHint("voice", 60)}
                className="rounded bg-yellow-100 px-2 py-1 text-xs text-yellow-900 hover:bg-yellow-200"
              >
                Hint (60%)
              </button>
              <button
                type="button"
                onClick={() => triggerToast("voice", 85)}
                className="rounded bg-orange-100 px-2 py-1 text-xs text-orange-900 hover:bg-orange-200"
              >
                Toast (85%)
              </button>
              <button
                type="button"
                onClick={() => triggerModal("voice")}
                className="rounded bg-red-100 px-2 py-1 text-xs text-red-900 hover:bg-red-200"
              >
                Modal (100%)
              </button>
            </div>
          </div>

          {/* Text Controls */}
          <div className="mb-4 space-y-2 rounded-lg border border-blue-200 bg-blue-50 p-3">
            <p className="text-xs font-semibold text-blue-900">Text Chat</p>
            <div className="flex flex-wrap gap-1">
              <button
                type="button"
                onClick={() => triggerHint("text", 65)}
                className="rounded bg-yellow-100 px-2 py-1 text-xs text-yellow-900 hover:bg-yellow-200"
              >
                Hint (65%)
              </button>
              <button
                type="button"
                onClick={() => triggerToast("text", 90)}
                className="rounded bg-orange-100 px-2 py-1 text-xs text-orange-900 hover:bg-orange-200"
              >
                Toast (90%)
              </button>
              <button
                type="button"
                onClick={() => triggerModal("text")}
                className="rounded bg-red-100 px-2 py-1 text-xs text-red-900 hover:bg-red-200"
              >
                Modal (100%)
              </button>
            </div>
          </div>

          {/* Reflections Controls */}
          <div className="space-y-2 rounded-lg border border-green-200 bg-green-50 p-3">
            <p className="text-xs font-semibold text-green-900">Reflection Cards</p>
            <div className="flex flex-wrap gap-1">
              <button
                type="button"
                onClick={() => triggerHint("reflections", 75)}
                className="rounded bg-yellow-100 px-2 py-1 text-xs text-yellow-900 hover:bg-yellow-200"
              >
                Hint (75%)
              </button>
              <button
                type="button"
                onClick={() => triggerToast("reflections", 80)}
                className="rounded bg-orange-100 px-2 py-1 text-xs text-orange-900 hover:bg-orange-200"
              >
                Toast (80%)
              </button>
              <button
                type="button"
                onClick={() => triggerModal("reflections")}
                className="rounded bg-red-100 px-2 py-1 text-xs text-red-900 hover:bg-red-200"
              >
                Modal (100%)
              </button>
            </div>
          </div>

          <div className="mt-4 rounded-lg bg-gray-100 p-2 text-xs text-gray-600">
            <p className="font-semibold">Legend:</p>
            <p>• Hint = Subtle footer (50-79%)</p>
            <p>• Toast = Gentle notification (80-99%)</p>
            <p>• Modal = Limit reached (100%)</p>
          </div>
        </div>
      )}
    </>
  )
}

