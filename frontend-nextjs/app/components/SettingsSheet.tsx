"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { X, LogOut } from "lucide-react"
import { t } from "../../copy"
import { useSupabase } from "../providers"
import { PrivacyPanel } from "./settings/PrivacyPanel"

type SettingsSheetProps = {
  onClose: () => void
}

export function SettingsSheet({ onClose }: SettingsSheetProps) {
  const { supabase } = useSupabase()
  const router = useRouter()
  const [isSigningOut, setIsSigningOut] = useState(false)

  const handleSignOut = async () => {
    setIsSigningOut(true)
    try {
      await supabase.auth.signOut()
      router.push("/login")
      onClose()
    } catch (error) {
      console.error("Error signing out:", error)
    } finally {
      setIsSigningOut(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-sophia-text/30 px-3 backdrop-blur-sm">
      <div className="w-full max-w-full rounded-3xl bg-white p-5 text-sophia-text shadow-soft sm:max-w-lg sm:p-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-lg font-semibold text-sophia-text">{t("settings.title")}</p>
            <p className="text-sm text-sophia-text2">Customize Sophia's presence and privacy.</p>
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

          {/* 💜 Founding Supporter Link - Non-intrusive, in expected location */}
          <div className="rounded-2xl border border-sophia-purple/20 bg-gradient-to-br from-sophia-purple/5 to-transparent px-4 py-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-sophia-text">Founding Supporter</p>
                <p className="text-xs text-sophia-text2 mt-0.5">Unlock unlimited conversations</p>
              </div>
              <button
                type="button"
                onClick={() => {
                  router.push("/founding-supporter")
                  onClose()
                }}
                className="rounded-xl bg-sophia-purple px-4 py-1.5 text-xs font-semibold text-white transition hover:bg-sophia-glow hover:scale-[1.02] active:scale-[0.98]"
              >
                Learn more
              </button>
            </div>
          </div>

          <div className="rounded-2xl border border-sophia-text/10 bg-sophia-user px-4 py-3 text-sm text-sophia-text2">
            More settings (voice presets, data saver, etc.) arrive in the polishing layer.
          </div>

          <button
            type="button"
            onClick={handleSignOut}
            disabled={isSigningOut}
            className="flex w-full items-center justify-center gap-2 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700 transition hover:bg-red-100 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <LogOut className="h-4 w-4" />
            {isSigningOut ? "Signing out..." : "Sign out"}
          </button>
        </div>
      </div>
    </div>
  )
}



