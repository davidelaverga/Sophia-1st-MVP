"use client"

import { copy, t } from "../../copy"
import { getPresenceCopyKey, usePresenceStore } from "../stores/presence-store"

type HeaderProps = {
  onOpenSettings?: () => void
}

export function Header({ onOpenSettings }: HeaderProps) {
  const status = usePresenceStore((state) => state.status)
  const detail = usePresenceStore((state) => state.detail)

  return (
    <header className="safe-px flex h-14 items-center justify-between">
      <div className="flex items-center gap-3">
        <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-sophia-purple text-lg font-semibold text-white">
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
        <span aria-live="polite" className="text-sm text-sophia-text2">
          {detail ?? t(getPresenceCopyKey(status))}
        </span>
        <button
          type="button"
          onClick={onOpenSettings}
          className="rounded-2xl border border-sophia-text/15 bg-sophia-button px-4 py-1.5 text-sm font-medium text-sophia-text shadow-soft/20 transition hover:bg-sophia-button-hover"
        >
          {t("settings.title")}
        </button>
      </div>
    </header>
  )
}
