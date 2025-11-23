"use client";

import { useEffect, useRef } from "react";
import type { UsageLimitInfo } from "../types/rate-limits";
import { copy } from "../../copy";

type UsageLimitModalProps = {
  open: boolean;
  onClose: () => void;
  info?: UsageLimitInfo;
};

export function UsageLimitModal({ open, onClose, info }: UsageLimitModalProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open) return;

    const node = containerRef.current;
    if (!node) return;

    // Focus trap
    const focusable = node.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
    );
    focusable[0]?.focus();

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
        return;
      }
      if (event.key !== "Tab") return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (!first || !last) return;
      if (event.shiftKey) {
        if (document.activeElement === first) {
          event.preventDefault();
          last.focus();
        }
      } else if (document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };

    node.addEventListener("keydown", handleKeyDown);
    return () => {
      node.removeEventListener("keydown", handleKeyDown);
    };
  }, [open, onClose]);

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
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      ref={containerRef}
    >
      <div className="w-full max-w-lg rounded-3xl bg-white p-6 shadow-soft">
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
            onClick={onClose}
            className="w-full rounded-2xl border border-sophia-text/15 bg-white px-4 py-2.5 text-sm font-medium text-sophia-text transition hover:bg-sophia-user sm:w-auto"
          >
            {copy.usageLimit.ctaSecondary}
          </button>
          <button
            type="button"
            onClick={handleUpgrade}
            className="w-full rounded-2xl bg-sophia-purple px-4 py-2.5 text-sm font-semibold text-white shadow-soft/30 transition hover:bg-sophia-glow sm:w-auto"
          >
            {copy.usageLimit.ctaPrimary}
          </button>
        </div>
      </div>
    </div>
  );
}

