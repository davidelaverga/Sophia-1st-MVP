"use client"

import Link from "next/link"
import { Sparkles } from "lucide-react"
import { copy, t } from "../../copy"
import { getPresenceCopyKey, usePresenceStore } from "../stores/presence-store"
import { ThemeToggle } from "./ThemeToggle"
import { ActiveModeIndicator } from "./ActiveModeIndicator"

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
        <ActiveModeIndicator />
        <span aria-live="polite" className="text-sm text-sophia-text2">
          {detail ?? t(getPresenceCopyKey(status))}
        </span>
        
        {/* My Reflections link */}
        <Link
          href="/reflections"
          className="hidden items-center gap-1.5 rounded-2xl border border-sophia-purple/20 bg-sophia-purple/5 px-3 py-1.5 text-sm font-medium text-sophia-purple transition-all hover:bg-sophia-purple/10 hover:border-sophia-purple/30 sm:flex"
        >
          <Sparkles className="h-3.5 w-3.5" />
          <span>Reflections</span>
        </Link>
        
        <ThemeToggle />
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
