"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"

export function ThemeToggle() {
  const [theme, setTheme] = useState<string>("light")
  const router = useRouter()

  useEffect(() => {
    const storedTheme = localStorage.getItem("sophia-theme") || "light"
    setTheme(storedTheme)
  }, [])

  const toggleTheme = () => {
    const newTheme = theme === "light" ? "moonlit-embrace" : "light"
    setTheme(newTheme)
    localStorage.setItem("sophia-theme", newTheme)
    document.documentElement.dataset.sophiaTheme = newTheme
    router.refresh()
  }

  const isLight = theme === "light"

  return (
    <button
      type="button"
      onClick={toggleTheme}
      className="group relative flex h-9 w-9 items-center justify-center rounded-xl border-2 border-sophia-text/20 bg-sophia-button hover:border-sophia-purple/40 hover:scale-105 shadow-sm transition-all duration-200"
      aria-label={isLight ? "Switch to Moonlit Embrace" : "Switch to Light Mode"}
    >
      <span className={`text-lg transition-all duration-500 ${
        isLight 
          ? "rotate-0 group-hover:rotate-[15deg]" 
          : "rotate-0 group-hover:rotate-[-15deg] group-hover:scale-110 animate-[pulse_2s_ease-in-out_infinite]"
      }`}>
        {isLight ? "☀️" : "🌙"}
      </span>
      
      {/* Tooltip on hover */}
      <div className="absolute -bottom-16 left-1/2 -translate-x-1/2 px-3 py-2 text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-50 bg-sophia-surface text-sophia-text shadow-lg border border-sophia-text/10">
        <div className="text-center">
          {isLight ? "Moments of clarity and focus" : "Like a conversation under the stars"}
        </div>
        <div className="absolute -top-1 left-1/2 -translate-x-1/2 w-2 h-2 rotate-45 bg-sophia-surface border-l border-t border-sophia-text/10"></div>
      </div>
    </button>
  )
}
