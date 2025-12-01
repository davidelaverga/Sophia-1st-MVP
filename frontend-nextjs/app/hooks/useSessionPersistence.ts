"use client"

import { useEffect, useRef, useCallback } from "react"
import { useChatStore } from "../stores/chat-store"
import { useFocusModeStore } from "../stores/focus-mode-store"
import { loadSession, saveSession, clearSession } from "../lib/session-persistence"
import { archiveConversation } from "../lib/conversation-history"
import { debug } from "../lib/debug"

/**
 * Hook to automatically persist and restore chat sessions
 * - Restores session on mount (if valid) - NOW DEFERRED until user chooses
 * - Saves session on every message change (including focus mode)
 * - Archives conversation before clearing
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

  // Manual restore function - called by WelcomeBack component
  const restoreSession = useCallback(() => {
    if (hasRestoredRef.current) return false
    
    const session = loadSession()
    if (!session) return false

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
    
    return true
  }, [setMode])

  // Save session whenever messages or focus mode change
  useEffect(() => {
    if (!conversationId || messages.length === 0) {
      // Don't clear immediately - let WelcomeBack handle it
      return
    }

    // Debounce saves to avoid too many writes
    const timeoutId = setTimeout(() => {
      saveSession(conversationId, messages, focusMode)
    }, 500)

    return () => clearTimeout(timeoutId)
  }, [conversationId, messages, focusMode])

  // Archive and clear session when user explicitly starts new conversation
  useEffect(() => {
    const handleClear = () => {
      // Archive current session before clearing
      const session = loadSession()
      if (session && session.messages.length >= 2) {
        archiveConversation(session.conversationId, session.messages, session.focusMode)
        debug.log("[SessionPersistence] Archived conversation before clear")
      }
      
      clearSession()
      hasRestoredRef.current = false
      debug.log("[SessionPersistence] Session cleared")
    }

    // Listen for reset events
    window.addEventListener("sophia:reset-session", handleClear)
    return () => window.removeEventListener("sophia:reset-session", handleClear)
  }, [])
  
  // Archive conversation when user leaves the page (for history)
  useEffect(() => {
    const handleBeforeUnload = () => {
      const session = loadSession()
      if (session && session.messages.length >= 2) {
        // Archive current conversation so it appears in history
        archiveConversation(session.conversationId, session.messages, session.focusMode)
      }
    }
    
    window.addEventListener("beforeunload", handleBeforeUnload)
    return () => window.removeEventListener("beforeunload", handleBeforeUnload)
  }, [])
  
  return { restoreSession }
}
