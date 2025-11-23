"use client"

import { create } from "zustand"
import { streamConversation } from "../lib/stream-conversation"
import { usePresenceStore } from "./presence-store"
import { useUsageLimitStore } from "./usage-limit-store"
import { copy } from "../../copy"

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
  setComposerValue: (value: string) => void
  sendMessage: (override?: string) => Promise<void>
  applyQuickPrompt: (prompt: string) => void
  clearError: () => void
  setFeedbackGate: (gate?: FeedbackGate) => void
  acknowledgeFeedback: (turnId: string) => void
  openSessionFeedback: (turnId: string) => void
  closeSessionFeedback: () => void
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
  setComposerValue: (value) => set({ composerValue: value }),
  applyQuickPrompt: (prompt) => set({ composerValue: prompt }),
  clearError: () => set({ lastError: undefined }),
  setFeedbackGate: (gate) => set({ feedbackGate: gate }),
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

    const userMessage = createMessage("user", text)
    const replyId = createMessageId()

    set((state) => ({
      messages: [...state.messages, userMessage, {
        id: replyId,
        role: "sophia",
        content: "",
        createdAt: Date.now(),
        status: "streaming",
        turnId: replyId,
      }],
      composerValue: "",
      isLocked: true,
      activeReplyId: replyId,
      lastError: undefined,
      feedbackGate: undefined,
    }))

    usePresenceStore.getState().setListening(true)
    let sawFeedbackGate = false

    try {
      await streamConversation({
        body: {
          message: text,
          conversationId: get().conversationId,
        },
      }, {
        onUsageLimit: (error) => {
          // Show usage limit modal
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
        },
        onToken: (token) => {
          usePresenceStore.getState().setListening(false)
          usePresenceStore.getState().setMetaStage("thinking")
          set((state) => ({
            messages: state.messages.map((message) =>
              message.id === replyId
                ? { ...message, content: `${message.content}${token}` }
                : message
            ),
          }))
        },
        onDone: (payload) => {
          set((state) => ({
            messages: state.messages.map((message) =>
              message.id === replyId
                ? {
                    ...message,
                    status: "complete",
                    content: payload?.message ?? message.content,
                    audioUrl: payload?.audioUrl ?? payload?.audio_url,
                  }
                : message
            ),
            isLocked: false,
            activeReplyId: undefined,
            conversationId: payload?.conversationId ?? payload?.conversation_id ?? state.conversationId,
            feedbackGate: state.feedbackGate?.turnId === replyId ? undefined : state.feedbackGate,
            lastCompletedTurnId: replyId,
          }))
          if (!sawFeedbackGate) {
            get().openSessionFeedback(replyId)
          }
          usePresenceStore.getState().setListening(false)
          usePresenceStore.getState().settleToRestingSoon()
        },
        onError: (payload) => {
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
            lastError: payload?.message ?? copy.chat.error,
            feedbackGate: undefined,
          }))
          usePresenceStore.getState().setListening(false)
          usePresenceStore.getState().settleToRestingSoon()
        },
      })
    } catch (error) {
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
        lastError: copy.chat.error,
        feedbackGate: undefined,
      }))
      usePresenceStore.getState().setListening(false)
      usePresenceStore.getState().settleToRestingSoon()
    }
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
