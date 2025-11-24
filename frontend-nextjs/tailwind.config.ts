import type { Config } from "tailwindcss"

const config: Config = {
  darkMode: ["class"],
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        sophia: {
          purple: "var(--sophia-purple)",
          glow: "var(--sophia-glow)",
          bg: "var(--bg)",
          text: "var(--text)",
          text2: "var(--text-2)",
          user: "var(--user-bubble)",
          reply: "var(--sophia-bubble)",
          btn: "var(--btn-active)",
          error: "var(--error)",
        },
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "sans-serif"],
      },
      borderRadius: {
        md: "var(--radius-md)",
        xl: "var(--radius-xl)",
        "2xl": "32px",
      },
      boxShadow: {
        soft: "var(--shadow-soft)",
      },
      spacing: {
        page: "24px",
        bubble: "16px",
      },
      keyframes: {
        pulseSoft: {
          "0%, 100%": { opacity: "0.7" },
          "50%": { opacity: "1" },
        },
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        breathe: {
          "0%, 100%": { opacity: "0.8", transform: "scale(1)" },
          "50%": { opacity: "1", transform: "scale(1.02)" },
        },
        breatheSlow: {
          "0%, 100%": { opacity: "0.7", transform: "scale(1)" },
          "50%": { opacity: "0.95", transform: "scale(1.01)" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-4px)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "200% 0" },
          "100%": { backgroundPosition: "-200% 0" },
        },
      },
      animation: {
        pulseSoft: "pulseSoft 2s ease-in-out infinite",
        fadeIn: "fadeIn 200ms ease",
        breathe: "breathe 3s ease-in-out infinite",
        breatheSlow: "breatheSlow 4s ease-in-out infinite",
        float: "float 3s ease-in-out infinite",
        shimmer: "shimmer 3s ease-in-out infinite",
      },
    },
  },
  plugins: [],
}

export default config
