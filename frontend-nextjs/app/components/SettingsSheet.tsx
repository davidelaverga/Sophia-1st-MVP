"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { X, LogOut } from "lucide-react"
import { t } from "../../copy"
import { useSupabase } from "../providers"
import { PrivacyPanel } from "./settings/PrivacyPanel"
import { setSophiaTheme } from "../ThemeBootstrap"

type SettingsSheetProps = {
  onClose: () => void
}

export function SettingsSheet({ onClose }: SettingsSheetProps) {
  const { supabase } = useSupabase()
  const router = useRouter()
  const [isSigningOut, setIsSigningOut] = useState(false)
  const [theme, setTheme] = useState<"light" | "midnight" | "twilight" | "deep-space">("light")

  useEffect(() => {
    if (typeof window === "undefined") return
    try {
      const stored = window.localStorage.getItem("sophia-theme") as
        | "light"
        | "midnight"
        | "twilight"
        | "deep-space"
        | null
      const initial = stored || "light"
      setTheme(initial)
    } catch {
      // ignore
    }
  }, [])

  const handleThemeChange = (value: "light" | "midnight" | "twilight" | "deep-space") => {
    setTheme(value)
    setSophiaTheme(value)
  }

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

          {/* 🎨 Theme preview / Dark mode selector for client demo */}
          <div className="space-y-3 rounded-2xl border border-sophia-text/10 bg-sophia-user px-4 py-3">
            <p className="text-sm font-medium text-sophia-text">Appearance (demo)</p>
            <p className="text-xs text-sophia-text2">
              Switch between the three proposed dark modes to see how Sophia feels in each one.
            </p>
            <div className="mt-2 grid gap-2 text-xs sm:grid-cols-2">
              <button
                type="button"
                onClick={() => handleThemeChange("light")}
                className={`flex items-center justify-between rounded-xl border px-3 py-2 transition ${
                  theme === "light"
                    ? "border-sophia-purple bg-white text-sophia-text shadow-soft"
                    : "border-sophia-text/10 bg-white/70 text-sophia-text2 hover:border-sophia-purple/40"
                }`}
              >
                <span className="font-medium">Light (actual)</span>
                {theme === "light" && <span className="text-[10px] text-sophia-purple">Selected</span>}
              </button>

              <button
                type="button"
                onClick={() => handleThemeChange("midnight")}
                className={`flex items-center justify-between rounded-xl border px-3 py-2 transition ${
                  theme === "midnight"
                    ? "border-sophia-purple bg-sophia-bubble text-sophia-text shadow-soft"
                    : "border-sophia-text/10 bg-sophia-bubble/70 text-sophia-text2 hover:border-sophia-purple/40"
                }`}
              >
                <span className="font-medium">Midnight Serenity</span>
                {theme === "midnight" && <span className="text-[10px] text-sophia-purple">Selected</span>}
              </button>

              <button
                type="button"
                onClick={() => handleThemeChange("twilight")}
                className={`flex items-center justify-between rounded-xl border px-3 py-2 transition ${
                  theme === "twilight"
                    ? "border-sophia-purple bg-sophia-bubble text-sophia-text shadow-soft"
                    : "border-sophia-text/10 bg-sophia-bubble/70 text-sophia-text2 hover:border-sophia-purple/40"
                }`}
              >
                <span className="font-medium">Twilight Calm</span>
                {theme === "twilight" && <span className="text-[10px] text-sophia-purple">Selected</span>}
              </button>

              <button
                type="button"
                onClick={() => handleThemeChange("deep-space")}
                className={`flex items-center justify-between rounded-xl border px-3 py-2 transition ${
                  theme === "deep-space"
                    ? "border-sophia-purple bg-sophia-bubble text-sophia-text shadow-soft"
                    : "border-sophia-text/10 bg-sophia-bubble/70 text-sophia-text2 hover:border-sophia-purple/40"
                }`}
              >
                <span className="font-medium">Deep Space</span>
                {theme === "deep-space" && <span className="text-[10px] text-sophia-purple">Selected</span>}
              </button>
            </div>
          </div>

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



