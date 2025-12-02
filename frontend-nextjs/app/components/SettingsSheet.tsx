"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { X, LogOut, RotateCcw } from "lucide-react"
import { t } from "../../copy"
import { useSupabase } from "../providers"
import { PrivacyPanel } from "./settings/PrivacyPanel"
import { useFocusTrap } from "../hooks/useFocusTrap"
import { useChatStore } from "../stores/chat-store"
import { clearSession } from "../lib/session-persistence"

type SettingsSheetProps = {
  onClose: () => void
}

export function SettingsSheet({ onClose }: SettingsSheetProps) {
  const { supabase } = useSupabase()
  const router = useRouter()
  const [isSigningOut, setIsSigningOut] = useState(false)
  const messages = useChatStore((state) => state.messages)
  
  // Focus trap for accessibility
  const { containerRef, restoreFocus } = useFocusTrap()
  
  // Handle Escape key to close modal
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        handleClose()
      }
    }
    
    document.addEventListener("keydown", handleEscape)
    return () => document.removeEventListener("keydown", handleEscape)
  }, [])
  
  const handleClose = () => {
    restoreFocus()
    onClose()
  }

  const handleNewConversation = () => {
    // Clear chat store
    useChatStore.setState({
      messages: [],
      conversationId: undefined,
      composerValue: "",
      lastError: undefined,
      feedbackGate: undefined,
      sessionFeedback: { open: false },
      lastCompletedTurnId: undefined,
    })
    
    // Clear localStorage
    clearSession()
    
    // Emit event for other listeners
    window.dispatchEvent(new CustomEvent("sophia:reset-session"))
    
    handleClose()
  }

  const handleSignOut = async () => {
    setIsSigningOut(true)
    try {
      await supabase.auth.signOut()
      // Clear local session data
      clearSession()
      // Reload to show AuthGate with Discord login
      window.location.href = "/"
    } catch (error) {
      console.error("Error signing out:", error)
      setIsSigningOut(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-3">
      <div 
        ref={containerRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="settings-title"
        className="w-full max-w-full rounded-3xl bg-sophia-surface p-5 text-sophia-text shadow-2xl sm:max-w-lg sm:p-6"
      >
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <p id="settings-title" className="text-2xl font-semibold text-sophia-text">{t("settings.title")}</p>
            <p className="mt-1 text-sm text-sophia-text2">Customize Sophia&apos;s presence and privacy.</p>
          </div>
          <button
            type="button"
            onClick={handleClose}
            aria-label="Close settings"
            className="rounded-xl border border-sophia-text/10 p-2 text-sophia-text2 transition hover:border-sophia-purple/40 hover:bg-sophia-purple/5 hover:text-sophia-purple"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="mt-6 h-px bg-gradient-to-r from-transparent via-sophia-text/10 to-transparent" />

        <div className="mt-6 space-y-6">
          <PrivacyPanel />

          {/* Theme toggle moved to Header for easier access */}
          <div className="rounded-xl border border-sophia-text/15 bg-sophia-surface px-4 py-3 shadow-sm">
            <p className="text-xs text-sophia-text2 text-center">
              <span className="font-medium text-sophia-text">✨ Theme toggle:</span> Use the ☀️/🌙 buttons in the header to switch between Light Mode and Moonlit Embrace.
            </p>
          </div>

          <div className="h-px bg-gradient-to-r from-transparent via-sophia-text/10 to-transparent" />

          {/* 💜 Founding Supporter Link - Non-intrusive, in expected location */}
          <div className="group rounded-2xl border border-sophia-text/15 bg-sophia-surface px-4 py-4 shadow-sm transition-all hover:border-sophia-purple/30 hover:shadow-md">
            <div className="flex items-center justify-between gap-4">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-base">💜</span>
                  <p className="text-sm font-semibold text-sophia-text">Founding Supporter</p>
                </div>
                <p className="text-xs text-sophia-text2 mt-1">Unlock unlimited conversations and help shape Sophia&apos;s future</p>
              </div>
              <button
                type="button"
                onClick={() => {
                  router.push("/founding-supporter")
                  onClose()
                }}
                className="rounded-xl bg-sophia-purple px-4 py-2 text-xs font-semibold text-white shadow-sm transition-all hover:bg-sophia-glow hover:scale-[1.03] hover:shadow-md active:scale-[0.98]"
              >
                Learn more
              </button>
            </div>
          </div>

          <div className="rounded-xl border border-sophia-text/15 bg-sophia-surface px-4 py-3 shadow-sm">
            <p className="text-xs text-sophia-text2 text-center">
              <span className="font-medium text-sophia-text">Coming soon:</span> Voice presets, data saver, and more customization options.
            </p>
          </div>

          <div className="h-px bg-gradient-to-r from-transparent via-sophia-text/10 to-transparent" />

          {/* New Conversation button */}
          {messages.length > 0 && (
            <button
              type="button"
              onClick={handleNewConversation}
              className="flex w-full items-center justify-center gap-2 rounded-xl border-2 border-sophia-purple/20 bg-sophia-purple/5 px-4 py-2.5 text-sm font-medium text-sophia-purple transition-all hover:border-sophia-purple/40 hover:bg-sophia-purple/10 hover:scale-[1.01]"
            >
              <RotateCcw className="h-4 w-4" />
              Start New Conversation
            </button>
          )}

          <button
            type="button"
            onClick={handleSignOut}
            disabled={isSigningOut}
            className="flex w-full items-center justify-center gap-2 rounded-xl border border-sophia-text/10 bg-sophia-button px-4 py-2.5 text-sm font-medium text-sophia-text2 transition-all hover:border-red-400/40 hover:bg-red-50 hover:text-red-600 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <LogOut className="h-4 w-4" />
            {isSigningOut ? "Signing out..." : "Sign out"}
          </button>
        </div>
      </div>
    </div>
  )
}



