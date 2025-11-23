"use client"

import { type ReactNode, useState } from "react"
import { Header } from "./Header"
import { ConsentGate } from "./ConsentGate"
import { SettingsSheet } from "./SettingsSheet"
import { UsageLimitModal } from "./UsageLimitModal"
import { useUsageLimitStore } from "../stores/usage-limit-store"

type AppShellProps = {
  children: ReactNode
  actionBar?: ReactNode
}

export function AppShell({ children, actionBar }: AppShellProps) {
  const [showSettings, setShowSettings] = useState(false)
  const [isConsentReady, setIsConsentReady] = useState(false)
  const { isOpen: limitModalOpen, limitInfo, closeModal: closeLimitModal } = useUsageLimitStore()

  return (
    <div className="grid min-h-[100svh] grid-rows-[auto_1fr_auto] bg-sophia-bg text-sophia-text">
      <Header onOpenSettings={() => setShowSettings(true)} />
      <div className="h-px w-full bg-sophia-text/10" />
      <main className="safe-px overflow-y-auto" aria-hidden={!isConsentReady}>
        <div className="mx-auto w-full max-w-2xl py-4">{children}</div>
      </main>
      <footer className="safe-px safe-b" aria-hidden={!isConsentReady}>
        <div className="mx-auto w-full max-w-2xl py-3">{actionBar ?? <div className="h-14" />}</div>
      </footer>

      {!isConsentReady && <ConsentGate onReady={() => setIsConsentReady(true)} />}

      {showSettings && <SettingsSheet onClose={() => setShowSettings(false)} />}

      <UsageLimitModal open={limitModalOpen} onClose={closeLimitModal} info={limitInfo} />
    </div>
  )
}
