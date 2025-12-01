"use client"

import { useEffect, useRef } from "react"
import { useChatStore } from "../stores/chat-store"
import { useFocusModeStore } from "../stores/focus-mode-store"
import { loadSession, saveSession, clearSession } from "../lib/session-persistence"
import { debug } from "../lib/debug"

/**
 * Hook to automatically persist and restore chat sessions
 * - Restores session on mount (if valid)
 * - Saves session on every message change (including focus mode)
 * - Clears session when conversation is reset
 * 
 * Note: When restoring, 'voice' mode is converted to 'text' because
 * the WebSocket connection doesn't persist between page loads.
 */
export function useSessionPersistence() {
  const messages = useChatStore((state) => state.messages)
  const conversationId = useChatStore((state) => state.conversationId)
  const focusMode = useFocusModeStore((state) => state.mode)
  const setMode = useFocusModeStore((state) => state.setMode)
  const hasRestoredRef = useRef(false)

  // Restore session on mount (only once)
  useEffect(() => {
    if (hasRestoredRef.current) return
    if (messages.length > 0) return // Don't restore if already has messages

    const session = loadSession()
    if (!session) return

    // Restore messages to store
    useChatStore.setState({
      messages: session.messages,
      conversationId: session.conversationId,
    })

    // Restore focus mode (but convert 'voice' to 'text' since WebSocket doesn't persist)
    if (session.focusMode) {
      const restoredMode = session.focusMode === "voice" ? "text" : session.focusMode
      setMode(restoredMode)
    }

    hasRestoredRef.current = true
    debug.log("[SessionPersistence] Restored session:", {
      conversationId: session.conversationId,
      messageCount: session.messages.length,
      originalMode: session.focusMode,
      restoredMode: session.focusMode === "voice" ? "text" : session.focusMode,
    })
  }, [messages.length, setMode])

  // Save session whenever messages or focus mode change
  useEffect(() => {
    if (!conversationId || messages.length === 0) {
      clearSession()
      return
    }

    // Debounce saves to avoid too many writes
    const timeoutId = setTimeout(() => {
      saveSession(conversationId, messages, focusMode)
    }, 500)

    return () => clearTimeout(timeoutId)
  }, [conversationId, messages, focusMode])

  // Clear session when user explicitly starts new conversation
  useEffect(() => {
    const handleClear = () => {
      clearSession()
      debug.log("[SessionPersistence] Session cleared")
    }

    // Listen for reset events
    window.addEventListener("sophia:reset-session", handleClear)
    return () => window.removeEventListener("sophia:reset-session", handleClear)
  }, [])
}
