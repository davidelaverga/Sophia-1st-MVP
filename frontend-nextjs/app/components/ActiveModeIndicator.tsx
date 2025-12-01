"use client"

import { Mic, MessageSquare } from "lucide-react"
import { useFocusModeStore } from "../stores/focus-mode-store"

export function ActiveModeIndicator() {
  const focusMode = useFocusModeStore((state) => state.mode)
  
  if (focusMode === "text") return null
  
  return (
    <div className="flex items-center gap-1.5 rounded-lg border border-sophia-purple/20 bg-sophia-purple/5 px-2 py-1">
      <Mic className="h-3.5 w-3.5 text-sophia-purple" />
      <span className="text-xs font-medium text-sophia-purple">Voice</span>
    </div>
  )
}
