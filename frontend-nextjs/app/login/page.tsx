"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { createClientComponentClient } from "@supabase/auth-helpers-nextjs"
import { Sparkles } from "lucide-react"

export default function LoginPage() {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  // FORCE use of CORRECT URL and KEY (temporary fix for demo)
  // TODO: Fix env variable reading issue
  const supabaseUrl = "https://qtyqgvdkbhjfmnfkxyvm.supabase.co"
  // Force use of the correct anon key directly
  const supabaseKey = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF0eXFndmRrYmhqZm1uZmt4eXZtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM0Nzc3MzUsImV4cCI6MjA3OTA1MzczNX0.XqfLoS-qOd01AOnO7gAY4mRPFPGa1JbRvNMmxpudJPI"
  
  // Debug log (remove after testing)
  if (typeof window !== "undefined") {
    console.log("[login] Supabase URL (from env):", process.env.NEXT_PUBLIC_SUPABASE_URL)
    console.log("[login] Supabase URL (using FORCED):", supabaseUrl)
    console.log("[login] Supabase Key (from env):", process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ? "Set" : "Missing")
    console.log("[login] Supabase Key (using):", supabaseKey ? supabaseKey.substring(0, 20) + "..." : "Missing")
  }
  
  const supabase = createClientComponentClient({
    supabaseUrl: supabaseUrl,
    supabaseKey: supabaseKey,
  })
  const router = useRouter()

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      const { data, error: authError } = await supabase.auth.signInWithPassword({
        email,
        password,
      })

      if (authError) {
        console.error("[login] Auth error:", authError)
        setError(authError.message || "Invalid email or password")
        setLoading(false)
        return
      }

      if (data.user) {
        // Success! Redirect to home
        router.push("/")
        router.refresh()
      } else {
        setError("Login failed. Please try again.")
        setLoading(false)
      }
    } catch (err: any) {
      console.error("[login] Unexpected error:", err)
      setError(err?.message || "An unexpected error occurred. Please check your connection.")
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-sophia-purple/5 via-white to-sophia-glow/5 p-4">
      <div className="w-full max-w-md">
        {/* Logo/Header */}
        <div className="text-center mb-8 animate-fadeIn">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-sophia-purple to-sophia-glow mb-4 shadow-lg shadow-sophia-purple/20">
            <Sparkles className="h-8 w-8 text-white" />
          </div>
          <h1 className="text-3xl font-semibold text-sophia-text mb-2">Welcome back</h1>
          <p className="text-sm text-sophia-text2">Sign in to continue your conversation with Sophia</p>
        </div>

        {/* Login Form */}
        <div className="rounded-3xl bg-white p-8 shadow-soft border border-sophia-purple/10 animate-fadeIn">
          <form onSubmit={handleLogin} className="space-y-6">
            {/* Email */}
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-sophia-text mb-2">
                Email
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                disabled={loading}
                autoComplete="email"
                className="w-full rounded-2xl border border-sophia-text/15 bg-white px-4 py-3 text-sm text-sophia-text placeholder:text-sophia-text2 focus:outline-none focus:ring-2 focus:ring-sophia-purple/20 focus:border-sophia-purple/40 transition-all duration-200 disabled:opacity-60 disabled:cursor-not-allowed"
                placeholder="you@example.com"
              />
            </div>

            {/* Password */}
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-sophia-text mb-2">
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                disabled={loading}
                autoComplete="current-password"
                className="w-full rounded-2xl border border-sophia-text/15 bg-white px-4 py-3 text-sm text-sophia-text placeholder:text-sophia-text2 focus:outline-none focus:ring-2 focus:ring-sophia-purple/20 focus:border-sophia-purple/40 transition-all duration-200 disabled:opacity-60 disabled:cursor-not-allowed"
                placeholder="••••••••"
              />
            </div>

            {/* Error Message */}
            {error && (
              <div className="rounded-2xl bg-sophia-error/10 border border-sophia-error/20 px-4 py-3 text-sm text-sophia-text animate-fadeIn">
                {error}
              </div>
            )}

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-2xl bg-gradient-to-br from-sophia-purple to-sophia-glow px-6 py-3.5 text-sm font-semibold text-white shadow-lg shadow-sophia-purple/30 hover:shadow-xl hover:shadow-sophia-purple/40 transition-all duration-300 hover:scale-[1.02] active:scale-[0.98] disabled:opacity-60 disabled:cursor-not-allowed disabled:hover:scale-100"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                  Signing in...
                </span>
              ) : (
                "Sign in"
              )}
            </button>
          </form>

          {/* Demo Note */}
          <div className="mt-6 pt-6 border-t border-sophia-text/10">
            <p className="text-xs text-center text-sophia-text2">
              Demo account: Use the credentials you created in Supabase
            </p>
          </div>
        </div>

        {/* Footer */}
        <p className="text-center text-xs text-sophia-text2 mt-6">
          By signing in, you agree to our terms and privacy policy
        </p>
      </div>
    </div>
  )
}

