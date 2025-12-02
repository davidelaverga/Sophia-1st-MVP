import { create } from "zustand";
import type { UsageLimitInfo } from "../types/rate-limits";

type UsageLimitStore = {
  isOpen: boolean;
  limitInfo?: UsageLimitInfo;
  hintInfo?: UsageLimitInfo; // Subtle footer hint (50-79%)
  toastInfo?: UsageLimitInfo; // Gentle toast (80-99%)
  lastToastDismissedAt?: number; // Timestamp when toast was last dismissed
  lastToastPercent?: number; // Last percentage when toast was shown
  lastModalDismissedAt?: number; // Timestamp when modal was last dismissed
  isAtLimit: boolean; // True if user is at 100% usage (blocks all requests)
  currentUsage?: {
    voicePercent: number;
    textPercent: number;
    user_id?: string; // Store user_id for passing to backend
  };
  showModal: (info: UsageLimitInfo, force?: boolean) => void;
  closeModal: () => void;
  showHint: (info: UsageLimitInfo) => void;
  dismissHint: () => void;
  showToast: (info: UsageLimitInfo) => void;
  dismissToast: () => void;
  setUsageData: (voicePercent: number, textPercent: number, user_id?: string) => void;
};

export const useUsageLimitStore = create<UsageLimitStore>((set, get) => ({
  isOpen: false,
  limitInfo: undefined,
  hintInfo: undefined,
  toastInfo: undefined,
  lastToastDismissedAt: undefined,
  lastToastPercent: undefined,
  isAtLimit: false,
  currentUsage: undefined,
  showModal: (info, force = false) => {
    const state = get()
    
    // Force parameter bypasses all checks (used by demo controls)
    if (force) {
      set({ isOpen: true, limitInfo: info })
      return
    }
    
    // If user is at 100% limit, always show modal (ignore dismissal time)
    // Otherwise, only show if it wasn't just dismissed (prevent immediate re-opening)
    if (state.isAtLimit) {
      // At 100%, always show modal regardless of dismissal time
      set({ isOpen: true, limitInfo: info })
    } else {
      const timeSinceDismiss = state.lastModalDismissedAt ? Date.now() - state.lastModalDismissedAt : Infinity
      const oneMinute = 60 * 1000
      
      if (timeSinceDismiss < oneMinute && state.lastModalDismissedAt) {
        // Modal was recently dismissed, don't show again immediately
        return
      }
      
      set({ isOpen: true, limitInfo: info })
    }
  },
  closeModal: () => {
    const state = get()
    // If user is still at 100%, keep blocking even if modal is closed
    // The modal will reappear if they try to use Sophia
    set({ 
      isOpen: false, 
      limitInfo: undefined,
      lastModalDismissedAt: Date.now(),
    })
  },
  showHint: (info) => set({ hintInfo: info }),
  dismissHint: () => set({ hintInfo: undefined }),
  showToast: (info) => set({ toastInfo: info }),
  dismissToast: () => {
    const state = get()
    const percent = state.toastInfo ? (state.toastInfo.used / state.toastInfo.limit) * 100 : undefined
    set({ 
      toastInfo: undefined,
      lastToastDismissedAt: Date.now(),
      lastToastPercent: percent,
    })
  },
  setUsageData: (voicePercent: number, textPercent: number, user_id?: string) => {
    const isAtLimit = voicePercent >= 100 || textPercent >= 100
    set({ 
      isAtLimit,
      currentUsage: { voicePercent, textPercent, user_id },
    })
    
    // If user reaches 100%, show modal immediately
    if (isAtLimit && !get().isOpen) {
      const reason = voicePercent >= 100 ? "voice" : "text"
      // We need to get the limit info from the current state or from usage monitor
      // For now, we'll let useUsageMonitor handle showing the modal
    }
  },
}));

