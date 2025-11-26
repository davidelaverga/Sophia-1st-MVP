import { create } from "zustand"

/**
 * Focus Mode Store
 * 
 * Manages the UI focus state to reduce distractions and provide
 * a calm, focused experience.
 * 
 * Modes:
 * - full: Both voice and text visible (default)
 * - voice: Voice panel expanded, chat minimized
 * - text: Chat expanded, voice panel minimized
 */

export type FocusMode = "full" | "voice" | "text"

interface FocusModeState {
  mode: FocusMode
  setMode: (mode: FocusMode) => void
  
  // Track if user manually overrode the mode
  isManualOverride: boolean
  setManualOverride: (override: boolean) => void
  
  // For voice focus: whether to show transcript preview
  transcriptExpanded: boolean
  toggleTranscript: () => void
}

export const useFocusModeStore = create<FocusModeState>((set) => ({
  mode: "full",
  setMode: (mode) => set({ mode }),
  
  isManualOverride: false,
  setManualOverride: (override) => set({ isManualOverride: override }),
  
  transcriptExpanded: false,
  toggleTranscript: () => set((state) => ({ 
    transcriptExpanded: !state.transcriptExpanded 
  })),
}))








