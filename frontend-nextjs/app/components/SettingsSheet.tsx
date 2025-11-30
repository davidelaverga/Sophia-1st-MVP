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
  const [theme, setTheme] = useState<"light" | "accessible-indigo" | "accessible-slate" | "accessible-charcoal" | "moonlit-embrace" | "velvet-night" | "dawns-promise">("light")

  useEffect(() => {
    if (typeof window === "undefined") return
    try {
      const stored = window.localStorage.getItem("sophia-theme") as
        | "light"
        | "accessible-indigo"
        | "accessible-slate"
        | "accessible-charcoal"
        | "moonlit-embrace"
        | "velvet-night"
        | "dawns-promise"
        | null
      const initial = stored || "light"
      setTheme(initial)
    } catch {
      // ignore
    }
  }, [])

  const handleThemeChange = (value: "light" | "accessible-indigo" | "accessible-slate" | "accessible-charcoal" | "moonlit-embrace" | "velvet-night" | "dawns-promise") => {
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
      <div className="w-full max-w-full rounded-3xl bg-sophia-card p-5 text-sophia-text shadow-soft sm:max-w-lg sm:p-6">
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

          {/* 🎨 Theme preview / Dark mode selector */}
          <div className="space-y-3 rounded-2xl border border-sophia-text/10 bg-sophia-user px-4 py-3">
            <p className="text-sm font-medium text-sophia-text">Appearance</p>
            <p className="text-xs text-sophia-text2">
              Choose the theme that brings you calm and peace. Each dark mode is designed to feel like Sophia is there with you.
            </p>
            <div className="mt-3 space-y-2">
              <button
                type="button"
                onClick={() => handleThemeChange("light")}
                className={`flex w-full flex-col items-start rounded-xl border px-3 py-2.5 text-left transition ${
                  theme === "light"
                    ? "border-sophia-purple bg-sophia-card text-sophia-text shadow-soft"
                    : "border-sophia-text/10 bg-sophia-button text-sophia-text2 hover:border-sophia-purple/40"
                }`}
              >
                <div className="flex w-full items-center justify-between">
                  <span className="text-sm font-medium">☀️ Light Mode</span>
                  {theme === "light" && <span className="text-[10px] text-sophia-purple">✓ Active</span>}
                </div>
                <span className="text-xs text-sophia-text2 mt-0.5">Bright and clear, for daytime conversations</span>
              </button>

              <div className="pt-1">
                <p className="text-xs font-medium text-sophia-text2 mb-2 px-1">🌙 Dark Modes — Find your calm</p>
              </div>

              <button
                type="button"
                onClick={() => handleThemeChange("moonlit-embrace")}
                className={`flex w-full flex-col items-start rounded-xl border px-3 py-2.5 text-left transition ${
                  theme === "moonlit-embrace"
                    ? "border-sophia-purple bg-sophia-bubble text-sophia-text shadow-soft"
                    : "border-sophia-text/10 bg-sophia-bubble/70 text-sophia-text2 hover:border-sophia-purple/40"
                }`}
              >
                <div className="flex w-full items-center justify-between">
                  <span className="text-sm font-medium">🌙 Moonlit Embrace</span>
                  {theme === "moonlit-embrace" && <span className="text-[10px] text-sophia-purple">✓ Active</span>}
                </div>
                <span className="text-xs text-sophia-text2 mt-0.5">Like a conversation under the stars — intimate, serene, always there</span>
              </button>

              <button
                type="button"
                onClick={() => handleThemeChange("velvet-night")}
                className={`flex w-full flex-col items-start rounded-xl border px-3 py-2.5 text-left transition ${
                  theme === "velvet-night"
                    ? "border-sophia-purple bg-sophia-bubble text-sophia-text shadow-soft"
                    : "border-sophia-text/10 bg-sophia-bubble/70 text-sophia-text2 hover:border-sophia-purple/40"
                }`}
              >
                <div className="flex w-full items-center justify-between">
                  <span className="text-sm font-medium">🍷 Velvet Night</span>
                  {theme === "velvet-night" && <span className="text-[10px] text-sophia-purple">✓ Active</span>}
                </div>
                <span className="text-xs text-sophia-text2 mt-0.5">Rich and warm, like sinking into your safest space</span>
              </button>

              <button
                type="button"
                onClick={() => handleThemeChange("dawns-promise")}
                className={`flex w-full flex-col items-start rounded-xl border px-3 py-2.5 text-left transition ${
                  theme === "dawns-promise"
                    ? "border-sophia-purple bg-sophia-bubble text-sophia-text shadow-soft"
                    : "border-sophia-text/10 bg-sophia-bubble/70 text-sophia-text2 hover:border-sophia-purple/40"
                }`}
              >
                <div className="flex w-full items-center justify-between">
                  <span className="text-sm font-medium">🌅 Dawn's Promise</span>
                  {theme === "dawns-promise" && <span className="text-[10px] text-sophia-purple">✓ Active</span>}
                </div>
                <span className="text-xs text-sophia-text2 mt-0.5">Hope in the darkness — you're not alone, light is coming</span>
              </button>

              <div className="pt-2 border-t border-sophia-text/10 mt-2">
                <p className="text-xs font-medium text-sophia-text2 mb-2 px-1">Accessibility-focused themes (WCAG compliant)</p>
              </div>

              <button
                type="button"
                onClick={() => handleThemeChange("accessible-indigo")}
                className={`flex w-full flex-col items-start rounded-xl border px-3 py-2.5 text-left transition ${
                  theme === "accessible-indigo"
                    ? "border-sophia-purple bg-sophia-bubble text-sophia-text shadow-soft"
                    : "border-sophia-text/10 bg-sophia-bubble/70 text-sophia-text2 hover:border-sophia-purple/40"
                }`}
              >
                <div className="flex w-full items-center justify-between">
                  <span className="text-sm font-medium">🔷 Accessible Indigo</span>
                  {theme === "accessible-indigo" && <span className="text-[10px] text-sophia-purple">✓ Active</span>}
                </div>
                <span className="text-xs text-sophia-text2 mt-0.5">High contrast purple tones, optimized for readability</span>
              </button>

              <button
                type="button"
                onClick={() => handleThemeChange("accessible-slate")}
                className={`flex w-full flex-col items-start rounded-xl border px-3 py-2.5 text-left transition ${
                  theme === "accessible-slate"
                    ? "border-sophia-purple bg-sophia-bubble text-sophia-text shadow-soft"
                    : "border-sophia-text/10 bg-sophia-bubble/70 text-sophia-text2 hover:border-sophia-purple/40"
                }`}
              >
                <div className="flex w-full items-center justify-between">
                  <span className="text-sm font-medium">🌫️ Accessible Slate</span>
                  {theme === "accessible-slate" && <span className="text-[10px] text-sophia-purple">✓ Active</span>}
                </div>
                <span className="text-xs text-sophia-text2 mt-0.5">Cool gray tones with excellent contrast ratios</span>
              </button>

              <button
                type="button"
                onClick={() => handleThemeChange("accessible-charcoal")}
                className={`flex w-full flex-col items-start rounded-xl border px-3 py-2.5 text-left transition ${
                  theme === "accessible-charcoal"
                    ? "border-sophia-purple bg-sophia-bubble text-sophia-text shadow-soft"
                    : "border-sophia-text/10 bg-sophia-bubble/70 text-sophia-text2 hover:border-sophia-purple/40"
                }`}
              >
                <div className="flex w-full items-center justify-between">
                  <span className="text-sm font-medium">⬛ Accessible Charcoal</span>
                  {theme === "accessible-charcoal" && <span className="text-[10px] text-sophia-purple">✓ Active</span>}
                </div>
                <span className="text-xs text-sophia-text2 mt-0.5">Deep blacks with bright accents for maximum visibility</span>
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



