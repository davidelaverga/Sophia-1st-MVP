import type { Config } from "tailwindcss"

const config: Config = {
  darkMode: ["class"],
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  // Safelist classes that might not be detected during build
  safelist: [
    'bg-sophia-surface',
    'bg-sophia-bubble',
    'text-sophia-text',
    'text-sophia-text2',
    'border-sophia-surface-border',
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
          bubble: "var(--sophia-bubble)",
          reply: "var(--sophia-bubble)",
          btn: "var(--btn-active)",
          error: "var(--error)",
          surface: "var(--card-bg)",
          "surface-border": "var(--card-border)",
          input: "var(--input-bg)",
          "input-border": "var(--input-border)",
          button: "var(--button-bg)",
          "button-hover": "var(--button-hover)",
        },
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "sans-serif"],
      },
      borderRadius: {
        md: "var(--radius-md)",
        xl: "var(--radius-xl)",
        "2xl": "0.6rem",
        "3xl": "0.6rem",
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
        fadeInUp: {
          "0%": { opacity: "0", transform: "translateY(10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
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
        glowBreathe: {
          "0%, 100%": { 
            opacity: "0.4",
            transform: "scale(0.95)",
            boxShadow: "0 0 8px rgba(139, 92, 246, 0.3)"
          },
          "50%": { 
            opacity: "1",
            transform: "scale(1.1)",
            boxShadow: "0 0 20px rgba(139, 92, 246, 0.6), 0 0 40px rgba(167, 139, 250, 0.3)"
          },
        },
        ringBreathe: {
          "0%, 100%": { 
            boxShadow: "0 0 0 2px rgba(139, 92, 246, 0.2), 0 0 20px rgba(139, 92, 246, 0.1)"
          },
          "50%": { 
            boxShadow: "0 0 0 2px rgba(139, 92, 246, 0.4), 0 0 40px rgba(139, 92, 246, 0.3), 0 0 60px rgba(167, 139, 250, 0.2)"
          },
        },
      },
      animation: {
        pulseSoft: "pulseSoft 2s ease-in-out infinite",
        fadeIn: "fadeIn 400ms ease-out",
        fadeInUp: "fadeInUp 500ms ease-out",
        breathe: "breathe 3s ease-in-out infinite",
        breatheSlow: "breatheSlow 4s ease-in-out infinite",
        float: "float 3s ease-in-out infinite",
        shimmer: "shimmer 3s ease-in-out infinite",
        glowBreathe: "glowBreathe 2.5s ease-in-out infinite",
        ringBreathe: "ringBreathe 3s ease-in-out infinite",
      },
    },
  },
  plugins: [],
}

export default config
