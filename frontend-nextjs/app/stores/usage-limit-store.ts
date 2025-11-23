import { create } from "zustand";
import type { UsageLimitInfo } from "../types/rate-limits";

type UsageLimitStore = {
  isOpen: boolean;
  limitInfo?: UsageLimitInfo;
  showModal: (info: UsageLimitInfo) => void;
  closeModal: () => void;
};

export const useUsageLimitStore = create<UsageLimitStore>((set) => ({
  isOpen: false,
  limitInfo: undefined,
  showModal: (info) => set({ isOpen: true, limitInfo: info }),
  closeModal: () => set({ isOpen: false, limitInfo: undefined }),
}));

