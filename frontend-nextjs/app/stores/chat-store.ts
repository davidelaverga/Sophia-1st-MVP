"use client"

import { create } from "zustand"
import { streamConversation } from "../lib/stream-conversation"
import { usePresenceStore } from "./presence-store"
import { useUsageLimitStore } from "./usage-limit-store"
import { copy } from "../../copy"
import type { UsageLimitInfo } from "../types/rate-limits"
import { refreshUsage } from "../hooks/useUsageMonitor"
import { useSupabase } from "../providers"
import { logger } from "../lib/error-logger"
import { eventBus } from "../lib/events"

type ChatRole = "user" | "sophia" | "system"

type ChatStatus = "streaming" | "complete" | "error"

export type ChatMessage = {
  id: string
  role: ChatRole
  content: string
  createdAt: number
  status?: ChatStatus
  audioUrl?: string
  turnId?: string
  source?: "voice" | "text" // Track if message came from voice or text interaction
}

type FeedbackGate = {
  turnId: string
  allowed: boolean
  emotionalWeight?: number | null
}

type ChatStore = {
  messages: ChatMessage[]
  composerValue: string
  isLocked: boolean
  conversationId?: string
  activeReplyId?: string
  lastError?: string
  feedbackGate?: FeedbackGate
  sessionFeedback?: {
    open: boolean
    turnId?: string
  }
  lastCompletedTurnId?: string
  abortController?: AbortController
  setComposerValue: (value: string) => void
  sendMessage: (override?: string) => Promise<void>
  cancelStream: () => void
  applyQuickPrompt: (prompt: string) => void
  clearError: () => void
  setFeedbackGate: (gate?: FeedbackGate) => void
  acknowledgeFeedback: (turnId: string) => void
  openSessionFeedback: (turnId: string) => void
  closeSessionFeedback: () => void
  addVoiceMessage: (content: string, audioUrl?: string) => void
}

const createMessageId = () => {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID()
  }
  return Math.random().toString(36).slice(2)
}

const createMessage = (role: ChatRole, content: string, overrides: Partial<ChatMessage> = {}): ChatMessage => ({
  id: createMessageId(),
  role,
  content,
  createdAt: Date.now(),
  ...overrides,
})

export const useChatStore = create<ChatStore>((set, get) => ({
  messages: [],
  composerValue: "",
  isLocked: false,
  conversationId: undefined,
  activeReplyId: undefined,
  lastError: undefined,
  feedbackGate: undefined,
  sessionFeedback: { open: false },
  lastCompletedTurnId: undefined,
  abortController: undefined,
  setComposerValue: (value) => set({ composerValue: value }),
  applyQuickPrompt: (prompt) => set({ composerValue: prompt }),
  clearError: () => set({ lastError: undefined }),
  setFeedbackGate: (gate) => set({ feedbackGate: gate }),
  cancelStream: () => {
    const { abortController, activeReplyId, conversationId } = get()
    if (abortController) {
      // 1. Abort the frontend fetch immediately
      abortController.abort()
      
      // 2. Notify backend to stop processing (fire-and-forget)
      if (conversationId) {
        fetch(`/api/conversation/${conversationId}/cancel`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
        }).catch(() => {
          // Ignore errors - best effort cancellation
          console.debug("[chat-store] Backend cancel request failed (non-critical)")
        })
      }
      
      // 3. Clean up UI state
      set((state) => ({
        // Remove the incomplete Sophia message
        messages: state.messages.filter((m) => m.id !== activeReplyId),
        isLocked: false,
        activeReplyId: undefined,
        abortController: undefined,
        feedbackGate: undefined,
      }))
      usePresenceStore.getState().setListening(false)
      usePresenceStore.getState().settleToRestingSoon()
    }
  },
  acknowledgeFeedback: (turnId) =>
    set((state) => {
      const updates: Partial<ChatStore> = {}
      if (state.feedbackGate?.turnId === turnId) {
        updates.feedbackGate = undefined
      }
      if (state.sessionFeedback?.turnId === turnId) {
        updates.sessionFeedback = { open: false, turnId: undefined }
      }
      return updates
    }),
  openSessionFeedback: (turnId) => set({ sessionFeedback: { open: true, turnId } }),
  closeSessionFeedback: () => set({ sessionFeedback: { open: false, turnId: undefined } }),
  setLastCompletedTurn: (turnId) => set({ lastCompletedTurnId: turnId }),
  sendMessage: async (override) => {
    const text = (override ?? get().composerValue).trim()
    if (!text || get().isLocked) return

    // Add breadcrumb for message send
    logger.addBreadcrumb("User sent message", {
      messageLength: text.length,
      hasOverride: !!override,
    })

    // 💜 Block if user is at 100% usage limit
    const usageStore = useUsageLimitStore.getState()
    if (usageStore.isAtLimit) {
      // Show modal if not already open
      if (!usageStore.isOpen && usageStore.currentUsage) {
        const reason = usageStore.currentUsage.textPercent >= 100 ? "text" : "voice"
        const limitInfo: UsageLimitInfo = {
          reason,
          plan_tier: "FREE", // Will be updated by usage monitor
          limit: 0,
          used: 0,
        }
        usageStore.showModal(limitInfo)
      }
      return // Block the request
    }

    const userMessage = createMessage("user", text)
    const replyId = createMessageId()

    // 🔔 Emit message sent event
    eventBus.emit("chat:message:sent", {
      id: userMessage.id,
      content: text,
      role: "user",
      timestamp: Date.now(),
      source: "text",
    })

    // Accumulate tokens in memory but don't show them until done
    let accumulatedContent = ""

    // Create AbortController for this stream
    const abortController = new AbortController()

    set((state) => ({
      messages: [...state.messages, userMessage, {
        id: replyId,
        role: "sophia",
        content: "", // Start empty - will only show when done
        createdAt: Date.now(),
        status: "streaming",
        turnId: replyId,
      }],
      composerValue: "",
      isLocked: true,
      activeReplyId: replyId,
      lastError: undefined,
      feedbackGate: undefined,
      abortController,
    }))

    // 🔔 Emit stream start event
    eventBus.emit("chat:stream:start", {
      conversationId: get().conversationId ?? "new",
      timestamp: Date.now(),
    })

    usePresenceStore.getState().setListening(true)
    let sawFeedbackGate = false

    // 💜 Get user_id from usage store (set by useUsageMonitor)
    // The usage monitor already has access to the user, so we can get it from there
    const userId = useUsageLimitStore.getState().currentUsage?.user_id
    
    try {
      await streamConversation({
        body: {
          message: text,
          conversationId: get().conversationId,
          user_id: userId, // 💜 Pass user_id for rate limiting
        },
        signal: abortController.signal,
      }, {
        onCancel: () => {
          // Stream was cancelled by user - cleanup already done in cancelStream
          console.log("[chat-store] Stream cancelled by user")
        },
        onUsageLimit: (error) => {
          // Only show modal when limit is reached (100%)
          // Progressive alerts (hints/toasts) are handled by backend meta events
          useUsageLimitStore.getState().showModal({
            reason: error.reason,
            plan_tier: error.plan_tier,
            limit: error.limit,
            used: error.used,
          })
          // Clean up UI state
          set((state) => ({
            messages: state.messages.filter((m) => m.id !== replyId),
            isLocked: false,
            activeReplyId: undefined,
            feedbackGate: undefined,
          }))
          usePresenceStore.getState().setListening(false)
          usePresenceStore.getState().settleToRestingSoon()
        },
        onMeta: (meta) => {
          if (meta?.conversationId && meta.conversationId !== get().conversationId) {
            set({ conversationId: meta.conversationId })
          }
          if (meta?.presence) {
            const presence = typeof meta.presence === "string"
              ? { status: meta.presence }
              : meta.presence
            usePresenceStore.getState().setMetaStage(presence.status, presence.detail)
          } else if (meta?.status) {
            usePresenceStore.getState().setMetaStage(meta.status, meta.detail)
          }
          if (typeof meta?.feedback_allowed === "boolean") {
            sawFeedbackGate = sawFeedbackGate || meta.feedback_allowed
            const turnId = meta.turn_id ?? replyId
            get().setFeedbackGate({
              turnId,
              allowed: meta.feedback_allowed,
              emotionalWeight: meta.emotional_weight ?? null,
            })
          }
          // Handle progressive usage alerts from backend
          if (meta?.usage_info) {
            const usageInfo = meta.usage_info
            const usagePercent = (usageInfo.used / usageInfo.limit) * 100
            
            if (usagePercent >= 80 && usagePercent < 100) {
              // Show gentle toast at 80-99%
              useUsageLimitStore.getState().showToast({
                reason: usageInfo.reason,
                plan_tier: usageInfo.plan_tier,
                limit: usageInfo.limit,
                used: usageInfo.used,
              })
            } else if (usagePercent >= 50 && usagePercent < 80) {
              // Show subtle hint at 50-79%
              useUsageLimitStore.getState().showHint({
                reason: usageInfo.reason,
                plan_tier: usageInfo.plan_tier,
                limit: usageInfo.limit,
                used: usageInfo.used,
              })
            }
          }
        },
        onToken: (token) => {
          // Accumulate tokens but don't update UI - user won't see tokens
          accumulatedContent += token
          usePresenceStore.getState().setListening(false)
          usePresenceStore.getState().setMetaStage("thinking")
          
          // 🔔 Emit stream chunk event
          eventBus.emit("chat:stream:chunk", {
            id: replyId,
            content: token,
            timestamp: Date.now(),
          })
          // Don't update message content - wait for onDone
        },
        onDone: (payload) => {
          // Show the final reply - use accumulated content or payload message
          const finalContent = payload?.message ?? accumulatedContent.trim()
          set((state) => {
            const currentMessage = state.messages.find(m => m.id === replyId)
            const finalText = finalContent || currentMessage?.content || ""
            return {
              messages: state.messages.map((message) =>
                message.id === replyId
                  ? {
                      ...message,
                      status: "complete",
                      content: finalText,
                      audioUrl: payload?.audioUrl ?? payload?.audio_url,
                    }
                  : message
              ),
              isLocked: false,
              activeReplyId: undefined,
              abortController: undefined,
              conversationId: payload?.conversationId ?? payload?.conversation_id ?? state.conversationId,
              feedbackGate: state.feedbackGate?.turnId === replyId ? undefined : state.feedbackGate,
              lastCompletedTurnId: replyId,
            }
          })
          
          // 🔔 Emit stream complete event
          eventBus.emit("chat:stream:complete", {
            id: replyId,
            finalContent: finalContent,
            timestamp: Date.now(),
            turnId: payload?.turn_id ?? replyId,
          })
          
          // 🔔 Emit message received event
          eventBus.emit("chat:message:received", {
            id: replyId,
            content: finalContent,
            role: "sophia",
            timestamp: Date.now(),
            turnId: payload?.turn_id ?? replyId,
            audioUrl: payload?.audioUrl ?? payload?.audio_url,
          })
          
          if (!sawFeedbackGate) {
            get().openSessionFeedback(replyId)
          }
          usePresenceStore.getState().setListening(false)
          usePresenceStore.getState().settleToRestingSoon()
          
          // Refresh usage immediately after message completes
          // Backend has updated the usage, so we should see the new count
          console.log("[chat-store] Message completed, calling refreshUsage()")
          refreshUsage()
        },
        onError: (payload) => {
          // 🔔 Emit stream error event
          eventBus.emit("chat:stream:error", {
            error: payload?.message ?? copy.chat.error,
            timestamp: Date.now(),
          })
          
          set((state) => ({
            messages: state.messages.map((message) =>
              message.id === replyId
                ? {
                    ...message,
                    status: "error",
                    content: message.content || copy.chat.error,
                  }
                : message
            ),
            isLocked: false,
            activeReplyId: undefined,
            abortController: undefined,
            lastError: payload?.message ?? copy.chat.error,
            feedbackGate: undefined,
          }))
          usePresenceStore.getState().setListening(false)
          usePresenceStore.getState().settleToRestingSoon()
        },
      })
    } catch (error) {
      // Ignore abort errors - they're handled in onCancel
      if (error instanceof DOMException && error.name === "AbortError") {
        return
      }
      
      logger.error(error, {
        component: 'ChatStore',
        action: 'sendMessage',
        metadata: {
          conversationId: get().conversationId,
          messageLength: text.length,
        },
      })
      
      console.error("[conversation] Streaming request failed", error)
      set((state) => ({
        messages: state.messages.map((message) =>
          message.id === replyId
            ? {
                ...message,
                status: "error",
                content: message.content || copy.chat.error,
              }
            : message
        ),
        isLocked: false,
        activeReplyId: undefined,
        abortController: undefined,
        lastError: copy.chat.error,
        feedbackGate: undefined,
      }))
      usePresenceStore.getState().setListening(false)
      usePresenceStore.getState().settleToRestingSoon()
    }
  },
  addVoiceMessage: (content, audioUrl) => {
    const voiceMessage = createMessage("sophia", content, {
      source: "voice",
      status: "complete",
      audioUrl,
    })
    
    // 🔔 Emit message received event for voice
    eventBus.emit("chat:message:received", {
      id: voiceMessage.id,
      content: content,
      role: "sophia",
      timestamp: Date.now(),
      audioUrl: audioUrl,
    })
    
    set((state) => ({
      messages: [...state.messages, voiceMessage],
    }))
  },
}))

if (process.env.NODE_ENV !== "production") {
  useChatStore.subscribe((state, prevState) => {
    if (!prevState) return

    if (state.isLocked !== prevState.isLocked) {
      console.trace("[chat-store] isLocked", prevState.isLocked, "→", state.isLocked)
    }

    if (state.messages.length !== prevState.messages.length) {
      console.trace("[chat-store] messages", prevState.messages.length, "→", state.messages.length)
    }

    if (state.lastError !== prevState.lastError) {
      console.trace("[chat-store] lastError", prevState.lastError, "→", state.lastError)
    }
  })
}
