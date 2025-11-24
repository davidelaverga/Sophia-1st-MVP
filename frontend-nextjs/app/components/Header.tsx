"use client"

import { copy, t } from "../../copy"
import { PresenceIndicator } from "./PresenceIndicator"

type HeaderProps = {
  onOpenSettings?: () => void
}

export function Header({ onOpenSettings }: HeaderProps) {
  return (
    <header className="safe-px flex h-14 items-center justify-between">
      <div className="flex items-center gap-3">
        <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-sophia-purple text-lg font-semibold text-white shadow-md animate-breatheSlow">
          {copy.brand.initial}
        </span>
        <div>
          <p className="text-base font-semibold text-sophia-text">
            {copy.brand.name}
          </p>
          <p className="text-sm text-sophia-text2">{t("header.subtitle")}</p>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <PresenceIndicator />
        <button
          type="button"
          onClick={onOpenSettings}
          className="rounded-2xl border border-sophia-text/15 bg-white/60 px-4 py-1.5 text-sm font-medium text-sophia-text shadow-soft/20 transition-all duration-300 ease-out hover:scale-[1.02] hover:bg-white hover:shadow-md active:scale-[0.98]"
        >
          {t("settings.title")}
        </button>
      </div>
    </header>
  )
}
