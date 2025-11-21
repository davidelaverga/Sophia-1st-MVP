"use client"

import { X } from "lucide-react"
import { t } from "../../copy"
import { PrivacyPanel } from "./settings/PrivacyPanel"

type SettingsSheetProps = {
  onClose: () => void
}

export function SettingsSheet({ onClose }: SettingsSheetProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-sophia-text/30 px-3 backdrop-blur-sm">
      <div className="w-full max-w-full rounded-3xl bg-white p-5 text-sophia-text shadow-soft sm:max-w-lg sm:p-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-lg font-semibold text-sophia-text">{t("settings.title")}</p>
            <p className="text-sm text-sophia-text2">Customize Sophia’s presence and privacy.</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close settings"
            className="rounded-full border border-sophia-text/20 p-2 text-sophia-text transition hover:border-sophia-purple/40 hover:text-sophia-purple"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="mt-6 space-y-6">
          <PrivacyPanel />

          <div className="rounded-2xl border border-sophia-text/10 bg-sophia-user px-4 py-3 text-sm text-sophia-text2">
            More settings (voice presets, data saver, etc.) arrive in the polishing layer.
          </div>
        </div>
      </div>
    </div>
  )
}



