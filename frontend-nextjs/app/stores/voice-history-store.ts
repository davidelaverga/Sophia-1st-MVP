"use client"

import { create } from "zustand"

export type VoiceMessage = {
  id: string
  content: string
  timestamp: number
}

type VoiceHistoryStore = {
  messages: VoiceMessage[]
  addMessage: (content: string) => void
  clearHistory: () => void
}

const createMessageId = () => {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID()
  }
  return Math.random().toString(36).slice(2)
}

export const useVoiceHistoryStore = create<VoiceHistoryStore>((set) => ({
  messages: [],
  addMessage: (content) => {
    const newMessage: VoiceMessage = {
      id: createMessageId(),
      content,
      timestamp: Date.now(),
    }
    set((state) => ({
      messages: [...state.messages, newMessage],
    }))
  },
  clearHistory: () => set({ messages: [] }),
}))

