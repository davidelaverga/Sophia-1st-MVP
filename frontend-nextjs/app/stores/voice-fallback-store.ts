"use client"

import { create } from "zustand"

type VoiceFallbackState = {
  hasVoiceFailed: boolean
  failureReason?: string
  failureCount: number
  lastFailureTime?: number
  isVoiceAvailable: boolean
  setVoiceFailed: (reason: string) => void
  setVoiceAvailable: () => void
  resetFailures: () => void
  shouldAutoFallback: () => boolean
}

const MAX_FAILURES_BEFORE_FALLBACK = 2
const FAILURE_RESET_TIME_MS = 5 * 60 * 1000 // 5 minutes

export const useVoiceFallbackStore = create<VoiceFallbackState>((set, get) => ({
  hasVoiceFailed: false,
  failureReason: undefined,
  failureCount: 0,
  lastFailureTime: undefined,
  isVoiceAvailable: true,

  setVoiceFailed: (reason: string) => {
    const now = Date.now()
    const state = get()
    
    // Reset count if last failure was too long ago
    const shouldReset = state.lastFailureTime && (now - state.lastFailureTime) > FAILURE_RESET_TIME_MS
    const newCount = shouldReset ? 1 : state.failureCount + 1
    
    set({
      hasVoiceFailed: true,
      failureReason: reason,
      failureCount: newCount,
      lastFailureTime: now,
      isVoiceAvailable: newCount < MAX_FAILURES_BEFORE_FALLBACK,
    })
    
    console.log("[VoiceFallback] Voice failed:", {
      reason,
      failureCount: newCount,
      isVoiceAvailable: newCount < MAX_FAILURES_BEFORE_FALLBACK,
    })
  },

  setVoiceAvailable: () => {
    set({
      hasVoiceFailed: false,
      failureReason: undefined,
      isVoiceAvailable: true,
    })
  },

  resetFailures: () => {
    set({
      hasVoiceFailed: false,
      failureReason: undefined,
      failureCount: 0,
      lastFailureTime: undefined,
      isVoiceAvailable: true,
    })
  },

  shouldAutoFallback: () => {
    const state = get()
    return !state.isVoiceAvailable && state.failureCount >= MAX_FAILURES_BEFORE_FALLBACK
  },
}))
