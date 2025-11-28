"use client"

import { useEffect } from "react"

const STORAGE_KEY = "sophia-theme"

const DEFAULT_THEME = "light"

/**
 * Small client-only component that:
 * - Reads the saved theme from localStorage (if any)
 * - Applies it to <html data-sophia-theme="...">
 * This ensures the chosen theme persists outside of Settings.
 */
export function ThemeBootstrap() {
  useEffect(() => {
    if (typeof window === "undefined") return

    try {
      const stored = window.localStorage.getItem(STORAGE_KEY)
      const theme = stored || DEFAULT_THEME
      document.documentElement.dataset.sophiaTheme = theme
    } catch (err) {
      console.warn("[theme] Failed to read stored theme", err)
    }
  }, [])

  return null
}

/**
 * Helper to update theme from anywhere in the client.
 */
export function setSophiaTheme(theme: string) {
  if (typeof window === "undefined") return
  document.documentElement.dataset.sophiaTheme = theme
  try {
    window.localStorage.setItem(STORAGE_KEY, theme)
  } catch (err) {
    console.warn("[theme] Failed to persist theme", err)
  }
}




