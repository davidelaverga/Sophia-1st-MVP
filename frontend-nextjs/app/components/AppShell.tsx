"use client"

import { type ReactNode, useState, lazy, Suspense } from "react"
import { Header } from "./Header"
import { AuthGate } from "./AuthGate"
import { ConsentGate } from "./ConsentGate"
import { GentleUsageToast } from "./GentleUsageToast"
import { UsageDemoControls } from "./UsageDemoControls"
import { useUsageLimitStore } from "../stores/usage-limit-store"
import { ErrorBoundary } from "./ErrorBoundary"

// Lazy load modals for better initial bundle size
const SettingsSheet = lazy(() => import("./SettingsSheet").then(mod => ({ default: mod.SettingsSheet })))
const UsageLimitModal = lazy(() => import("./UsageLimitModal").then(mod => ({ default: mod.UsageLimitModal })))

type AppShellProps = {
  children: ReactNode
  actionBar?: ReactNode
}

export function AppShell({ children, actionBar }: AppShellProps) {
  const [showSettings, setShowSettings] = useState(false)
  // 🔧 BYPASS: Skip auth for testing - remove this in production
  const [isAuthReady, setIsAuthReady] = useState(true) // was false
  const [isConsentReady, setIsConsentReady] = useState(true) // was false
  const limitModalOpen = useUsageLimitStore((state) => state.isOpen)
  const limitInfo = useUsageLimitStore((state) => state.limitInfo)
  const closeLimitModal = useUsageLimitStore((state) => state.closeModal)

  // Show AuthGate first, then ConsentGate after auth
  const showConsentGate = false // 🔧 BYPASS: was (isAuthReady && !isConsentReady)

  return (
    // 🔧 BYPASS: Removed AuthGate wrapper for testing
    <div className="grid min-h-[100svh] grid-rows-[auto_1fr_auto] bg-sophia-bg text-sophia-text">
        {/* Skip to main content link for keyboard navigation */}
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-[200] focus:rounded-lg focus:bg-sophia-purple focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:text-white focus:shadow-lg focus:outline-none focus:ring-2 focus:ring-sophia-purple focus:ring-offset-2"
        >
          Skip to main content
        </a>
        
        <Header onOpenSettings={() => setShowSettings(true)} />
        <div className="h-px w-full bg-sophia-text/10" />
        <main id="main-content" className="safe-px overflow-y-auto" aria-hidden={!isConsentReady}>
          <div className="mx-auto w-full max-w-2xl py-4">{children}</div>
        </main>
        <footer className="safe-px safe-b" aria-hidden={!isConsentReady}>
          <div className="mx-auto w-full max-w-2xl py-3">
            {actionBar ?? <div className="h-14" />}
            {/* 💜 Subtle footer link - Always visible but very discrete */}
            <div className="flex items-center justify-center pt-2 pb-1">
              <a
                href="/founding-supporter"
                className="text-[10px] text-sophia-text2/50 hover:text-sophia-purple/60 transition-colors duration-200"
              >
                Founding Supporter
              </a>
            </div>
          </div>
        </footer>

        {showConsentGate && <ConsentGate onReady={() => setIsConsentReady(true)} />}

        {showSettings && (
          <ErrorBoundary componentName="SettingsSheet">
            <Suspense fallback={<div className="fixed inset-0 z-50 bg-black/60" />}>
              <SettingsSheet onClose={() => setShowSettings(false)} />
            </Suspense>
          </ErrorBoundary>
        )}

        <ErrorBoundary componentName="UsageLimitModal">
          <Suspense fallback={null}>
            <UsageLimitModal open={limitModalOpen} onClose={closeLimitModal} info={limitInfo} />
          </Suspense>
        </ErrorBoundary>
        <GentleUsageToast />
        <UsageDemoControls />
      </div>
    // 🔧 BYPASS: Removed AuthGate closing tag
  )
}
