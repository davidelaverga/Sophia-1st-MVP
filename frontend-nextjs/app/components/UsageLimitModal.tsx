"use client";

import { useEffect } from "react";
import type { UsageLimitInfo } from "../types/rate-limits";
import { copy } from "../../copy";
import { useUsageLimitStore } from "../stores/usage-limit-store";
import { useFocusTrap } from "../hooks/useFocusTrap";

type UsageLimitModalProps = {
  open: boolean;
  onClose: () => void;
  info?: UsageLimitInfo;
};

export function UsageLimitModal({ open, onClose, info }: UsageLimitModalProps) {
  const isAtLimit = useUsageLimitStore((state) => state.isAtLimit)
  const { containerRef, restoreFocus } = useFocusTrap();

  // Handle Escape key to close modal (but not when at 100% limit)
  useEffect(() => {
    if (!open) return;

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !isAtLimit) {
        handleClose();
      }
    };

    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, [open, isAtLimit]);

  const handleClose = () => {
    restoreFocus();
    onClose();
  };

  if (!open) return null;

  const handleUpgrade = () => {
    const checkoutUrl = process.env.NEXT_PUBLIC_FOUNDING_CHECKOUT_URL;
    if (checkoutUrl) {
      window.location.href = checkoutUrl;
    } else {
      window.location.href = "/founding-supporter";
    }
  };

  const getUsageText = () => {
    if (!info) return null;
    
    switch (info.reason) {
      case "voice":
        return copy.usageLimit.voiceUsed
          .replace("{used}", Math.round(info.used / 60).toString())
          .replace("{limit}", Math.round(info.limit / 60).toString());
      case "text":
        return copy.usageLimit.textUsed
          .replace("{used}", info.used.toString())
          .replace("{limit}", info.limit.toString());
      case "reflections":
        return copy.usageLimit.reflectionsUsed
          .replace("{used}", info.used.toString())
          .replace("{limit}", info.limit.toString());
      default:
        return null;
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="usage-limit-title"
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/40 p-4"
      ref={containerRef}
      onClick={(e) => {
        // Prevent closing modal by clicking backdrop - user must use button
        e.stopPropagation()
      }}
    >
      <div className="w-full max-w-lg rounded-3xl bg-sophia-surface p-6 shadow-soft">
        <h2 id="usage-limit-title" className="text-xl font-semibold text-sophia-text">
          {copy.usageLimit.modalTitle}
        </h2>

        {info && (
          <p className="mt-2 text-sm text-sophia-text2">
            {getUsageText()}
          </p>
        )}

        <div className="mt-4 space-y-3 text-sm leading-relaxed text-sophia-text">
          <p>{copy.usageLimit.intro}</p>
          <p>{copy.usageLimit.ifYouFelt}</p>
          
          <ul className="space-y-1.5 pl-5">
            {copy.usageLimit.benefits.map((benefit, idx) => (
              <li key={idx} className="flex items-start gap-2">
                <span className="mt-1 text-sophia-purple">●</span>
                <span>{benefit}</span>
              </li>
            ))}
          </ul>

          <p>{copy.usageLimit.noPressure}</p>
          <p className="font-medium">{copy.usageLimit.thankYou}</p>
        </div>

        <div className="mt-6 flex flex-col gap-2 sm:flex-row sm:justify-end">
          <button
            type="button"
            onClick={() => {
              // Don't allow closing if at 100% limit - user must upgrade
              if (!isAtLimit) {
                handleClose();
              }
            }}
            disabled={isAtLimit}
            aria-label={isAtLimit ? "Cannot close - at usage limit" : "Maybe later"}
            className={`w-full rounded-2xl border border-sophia-text/15 bg-sophia-button px-4 py-2.5 text-sm font-medium text-sophia-text transition hover:bg-sophia-user sm:w-auto ${
              isAtLimit ? "opacity-50 cursor-not-allowed" : ""
            }`}
          >
            {copy.usageLimit.ctaSecondary}
          </button>
          <button
            type="button"
            onClick={handleUpgrade}
            aria-label="Explore Sophia Plus"
            className="w-full rounded-2xl bg-sophia-purple px-4 py-2.5 text-sm font-semibold text-white shadow-soft/30 transition hover:bg-sophia-glow sm:w-auto"
          >
            {copy.usageLimit.ctaPrimary}
          </button>
        </div>
      </div>
    </div>
  );
}

