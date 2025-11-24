import { create } from "zustand";
import type { UsageLimitInfo } from "../types/rate-limits";

type UsageLimitStore = {
  isOpen: boolean;
  limitInfo?: UsageLimitInfo;
  hintInfo?: UsageLimitInfo; // Subtle footer hint (50-79%)
  toastInfo?: UsageLimitInfo; // Gentle toast (80-99%)
  showModal: (info: UsageLimitInfo) => void;
  closeModal: () => void;
  showHint: (info: UsageLimitInfo) => void;
  dismissHint: () => void;
  showToast: (info: UsageLimitInfo) => void;
  dismissToast: () => void;
};

export const useUsageLimitStore = create<UsageLimitStore>((set) => ({
  isOpen: false,
  limitInfo: undefined,
  hintInfo: undefined,
  toastInfo: undefined,
  showModal: (info) => set({ isOpen: true, limitInfo: info }),
  closeModal: () => set({ isOpen: false, limitInfo: undefined }),
  showHint: (info) => set({ hintInfo: info }),
  dismissHint: () => set({ hintInfo: undefined }),
  showToast: (info) => set({ toastInfo: info }),
  dismissToast: () => set({ toastInfo: undefined }),
}));

