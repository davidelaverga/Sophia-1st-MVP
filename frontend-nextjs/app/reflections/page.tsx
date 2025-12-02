"use client"

/* eslint-disable i18next/no-literal-string */
/* eslint-disable react/no-unescaped-entities */

import { useState, useMemo, useEffect } from "react"
import { Sparkles, Heart, Send, Calendar, Filter, Search, ArrowLeft, Quote, Users, TrendingUp, Star, Loader2 } from "lucide-react"
import Link from "next/link"
import { useSupabase } from "../providers"

// Types for API responses
type CommunityInsight = {
  title: string
  insight: string
  sophia_emotion: { label: string; confidence: number }
  reflection_id: string | null
}

type UserImpact = {
  user_id: string
  session_count: number
  reflections_created: number
  reflections_shared: number
  last_session_at: string | null
}

// Mock data for reflections - will be replaced with real API calls later
const MOCK_REFLECTIONS = [
  {
    id: "1",
    text: "The key to understanding DeFi isn't the technology—it's recognizing that every protocol is designed around human behavior and trust.",
    reason: "breakthrough",
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 2), // 2 hours ago
    shared: true,
    likes: 12,
  },
  {
    id: "2", 
    text: "I realized that my fear of losing money in crypto was actually fear of admitting I made a mistake. Once I separated those, I could think more clearly.",
    reason: "insight",
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24), // 1 day ago
    shared: false,
    likes: 0,
  },
  {
    id: "3",
    text: "Diversification isn't just about spreading risk—it's about staying curious and learning from multiple ecosystems.",
    reason: "reflection",
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 3), // 3 days ago
    shared: true,
    likes: 28,
  },
  {
    id: "4",
    text: "The best time to learn about smart contract security is before you need it, not after you've lost funds.",
    reason: "wisdom",
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 5), // 5 days ago
    shared: true,
    likes: 45,
  },
  {
    id: "5",
    text: "I've been treating yield farming like a video game, chasing numbers. But real wealth comes from understanding what I'm actually investing in.",
    reason: "breakthrough",
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 7), // 1 week ago
    shared: false,
    likes: 0,
  },
]

// Fallback community insights when API fails
const FALLBACK_COMMUNITY_INSIGHTS: CommunityInsight[] = [
  {
    title: "Today Sophia learned",
    insight: "The importance of meaningful conversations and active listening.",
    sophia_emotion: { label: "curious", confidence: 0.85 },
    reflection_id: null,
  },
]

type FilterType = "all" | "shared" | "private"

function formatTimeAgo(date: Date): string {
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000)
  
  if (seconds < 60) return "just now"
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`
  if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`
  return date.toLocaleDateString()
}

export default function ReflectionsPage() {
  const { user } = useSupabase()
  const [filter, setFilter] = useState<FilterType>("all")
  const [searchQuery, setSearchQuery] = useState("")
  
  // Real data states
  const [communityInsight, setCommunityInsight] = useState<CommunityInsight | null>(null)
  const [userImpact, setUserImpact] = useState<UserImpact | null>(null)
  const [isLoadingCommunity, setIsLoadingCommunity] = useState(true)
  const [isLoadingImpact, setIsLoadingImpact] = useState(true)

  // Fetch community insights on mount
  useEffect(() => {
    async function fetchCommunityInsight() {
      try {
        const response = await fetch("/api/community/latest-learning")
        if (response.ok) {
          const data = await response.json()
          setCommunityInsight(data)
        }
      } catch (error) {
        console.error("Failed to fetch community insight:", error)
      } finally {
        setIsLoadingCommunity(false)
      }
    }
    fetchCommunityInsight()
  }, [])

  // Fetch user impact when user is available
  useEffect(() => {
    async function fetchUserImpact() {
      if (!user?.id) {
        setIsLoadingImpact(false)
        return
      }
      try {
        const response = await fetch(`/api/community/user-impact?user_id=${encodeURIComponent(user.id)}`)
        if (response.ok) {
          const data = await response.json()
          setUserImpact(data)
        }
      } catch (error) {
        console.error("Failed to fetch user impact:", error)
      } finally {
        setIsLoadingImpact(false)
      }
    }
    fetchUserImpact()
  }, [user?.id])

  const filteredReflections = useMemo(() => {
    let result = MOCK_REFLECTIONS

    // Filter by type
    if (filter === "shared") {
      result = result.filter(r => r.shared)
    } else if (filter === "private") {
      result = result.filter(r => !r.shared)
    }

    // Filter by search
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase()
      result = result.filter(r => 
        r.text.toLowerCase().includes(query) ||
        r.reason.toLowerCase().includes(query)
      )
    }

    return result
  }, [filter, searchQuery])

  return (
    <div className="min-h-screen bg-sophia-bg">
      {/* Header */}
      <header className="sticky top-0 z-40 border-b border-sophia-text/5 bg-sophia-bg/80 backdrop-blur-xl">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
          <div className="flex items-center gap-3">
            <Link 
              href="/"
              className="flex items-center gap-2 rounded-xl p-2 text-sophia-text2 transition-colors hover:bg-sophia-purple/10 hover:text-sophia-purple"
            >
              <ArrowLeft className="h-5 w-5" />
            </Link>
            <div>
              <h1 className="text-xl font-semibold text-sophia-text">Your Reflections</h1>
              <p className="text-sm text-sophia-text2">Wisdom collected from your journey</p>
            </div>
          </div>
          
          {/* Impact stats mini */}
          <div className="hidden items-center gap-4 sm:flex">
            {userImpact && (
              <>
                <div className="flex items-center gap-1.5 text-sm text-sophia-text2">
                  <Star className="h-4 w-4 text-amber-500" />
                  <span>{userImpact.session_count} sessions</span>
                </div>
                <div className="flex items-center gap-1.5 text-sm text-sophia-text2">
                  <Heart className="h-4 w-4 text-pink-500" />
                  <span>{userImpact.reflections_shared} shared</span>
                </div>
              </>
            )}
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-6">
        <div className="grid gap-6 lg:grid-cols-3">
          
          {/* Main content - Reflections list */}
          <div className="lg:col-span-2">
            {/* Search and filter bar */}
            <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              {/* Search */}
              <div className="relative flex-1 max-w-sm">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-sophia-text2" />
                <input
                  type="text"
                  placeholder="Search reflections..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full rounded-xl border-2 border-sophia-text/10 bg-sophia-surface py-2.5 pl-10 pr-4 text-sm text-sophia-text placeholder:text-sophia-text2/50 focus:border-sophia-purple focus:outline-none"
                />
              </div>

              {/* Filter tabs */}
              <div className="flex items-center gap-1 rounded-xl bg-sophia-surface p-1">
                {(["all", "shared", "private"] as const).map((f) => (
                  <button
                    key={f}
                    onClick={() => setFilter(f)}
                    className={`rounded-lg px-4 py-1.5 text-sm font-medium transition-all ${
                      filter === f
                        ? "bg-sophia-purple text-white shadow-sm"
                        : "text-sophia-text2 hover:text-sophia-text"
                    }`}
                  >
                    {f === "all" ? "All" : f === "shared" ? "Shared" : "Private"}
                  </button>
                ))}
              </div>
            </div>

            {/* Reflections list */}
            <div className="space-y-4">
              {filteredReflections.length === 0 ? (
                <div className="rounded-2xl border-2 border-dashed border-sophia-text/10 bg-sophia-surface/50 px-6 py-12 text-center">
                  <Sparkles className="mx-auto mb-3 h-10 w-10 text-sophia-purple/40" />
                  <p className="text-sophia-text2">No reflections found</p>
                  <p className="mt-1 text-sm text-sophia-text2/70">
                    {searchQuery ? "Try a different search term" : "Start a conversation with Sophia to collect wisdom"}
                  </p>
                </div>
              ) : (
                filteredReflections.map((reflection) => (
                  <article
                    key={reflection.id}
                    className="group relative overflow-hidden rounded-2xl bg-sophia-surface p-5 shadow-sm ring-1 ring-sophia-text/5 transition-all hover:shadow-md hover:ring-sophia-purple/20"
                  >
                    {/* Quote icon */}
                    <Quote className="absolute right-4 top-4 h-8 w-8 text-sophia-purple/10 transition-colors group-hover:text-sophia-purple/20" />
                    
                    {/* Content */}
                    <p className="pr-10 text-sophia-text leading-relaxed">
                      "{reflection.text}"
                    </p>

                    {/* Meta row */}
                    <div className="mt-4 flex flex-wrap items-center gap-3 text-xs">
                      {/* Reason tag */}
                      <span className="inline-flex items-center gap-1 rounded-full bg-sophia-purple/10 px-2.5 py-1 font-medium text-sophia-purple">
                        <Sparkles className="h-3 w-3" />
                        {reflection.reason}
                      </span>

                      {/* Shared badge - uses sophia-purple for theme consistency */}
                      {reflection.shared ? (
                        <span className="inline-flex items-center gap-1 rounded-full bg-sophia-purple/15 px-2.5 py-1 font-medium text-sophia-purple">
                          <Send className="h-3 w-3" />
                          Shared
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 rounded-full bg-sophia-text/5 px-2.5 py-1 font-medium text-sophia-text2">
                          <Heart className="h-3 w-3" />
                          Private
                        </span>
                      )}

                      {/* Likes */}
                      {reflection.shared && reflection.likes > 0 && (
                        <span className="inline-flex items-center gap-1 text-sophia-text2">
                          <Heart className="h-3 w-3 fill-pink-500 text-pink-500" />
                          {reflection.likes}
                        </span>
                      )}

                      {/* Time */}
                      <span className="ml-auto inline-flex items-center gap-1 text-sophia-text2">
                        <Calendar className="h-3 w-3" />
                        {formatTimeAgo(reflection.createdAt)}
                      </span>
                    </div>
                  </article>
                ))
              )}
            </div>
          </div>

          {/* Sidebar */}
          <aside className="space-y-6">
            {/* User Impact Card */}
            <div className="rounded-2xl bg-gradient-to-br from-sophia-purple/20 via-sophia-card to-sophia-card p-5 ring-1 ring-sophia-purple/10">
              <div className="mb-4 flex items-center gap-2">
                <TrendingUp className="h-5 w-5 text-sophia-purple" />
                <h2 className="font-semibold text-sophia-text">Your Impact</h2>
              </div>

              {isLoadingImpact ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-sophia-purple" />
                </div>
              ) : userImpact ? (
                <>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="rounded-xl bg-sophia-bg/50 p-3 text-center">
                      <p className="text-2xl font-bold text-sophia-purple">{userImpact.reflections_created}</p>
                      <p className="text-xs text-sophia-text2">Reflections</p>
                    </div>
                    <div className="rounded-xl bg-sophia-bg/50 p-3 text-center">
                      <p className="text-2xl font-bold text-sophia-purple">{userImpact.reflections_shared}</p>
                      <p className="text-xs text-sophia-text2">Shared</p>
                    </div>
                    <div className="rounded-xl bg-sophia-bg/50 p-3 text-center">
                      <p className="text-2xl font-bold text-pink-500">{userImpact.session_count}</p>
                      <p className="text-xs text-sophia-text2">Sessions</p>
                    </div>
                    <div className="rounded-xl bg-sophia-bg/50 p-3 text-center">
                      <p className="text-2xl font-bold text-amber-500">
                        {userImpact.last_session_at ? "Active" : "—"}
                      </p>
                      <p className="text-xs text-sophia-text2">Status</p>
                    </div>
                  </div>

                  {/* Rank badge */}
                  <div className="mt-4 flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-sophia-purple to-sophia-glow p-2.5">
                    <Star className="h-4 w-4 text-white" />
                    <span className="text-sm font-semibold text-white">
                      {userImpact.reflections_shared >= 5 ? "Wisdom Sharer" : 
                       userImpact.reflections_created >= 3 ? "Reflector" : "Explorer"}
                    </span>
                  </div>
                </>
              ) : (
                <p className="text-center text-sm text-sophia-text2 py-4">
                  Sign in to see your impact
                </p>
              )}
            </div>

            {/* Community Insights */}
            <div className="rounded-2xl bg-sophia-surface p-5 ring-1 ring-sophia-text/5">
              <div className="mb-4 flex items-center gap-2">
                <Users className="h-5 w-5 text-sophia-purple" />
                <h2 className="font-semibold text-sophia-text">Community Wisdom</h2>
              </div>

              {isLoadingCommunity ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-sophia-purple" />
                </div>
              ) : communityInsight ? (
                <div className="space-y-4">
                  <div className="border-b border-sophia-text/5 pb-4">
                    <p className="text-xs font-medium text-sophia-purple mb-2">
                      {communityInsight.title}
                    </p>
                    <p className="text-sm leading-relaxed text-sophia-text">
                      "{communityInsight.insight}"
                    </p>
                    <div className="mt-2 flex items-center justify-between text-xs text-sophia-text2">
                      <span>Anonymous Wisdom</span>
                      <span className="flex items-center gap-1 capitalize">
                        <Sparkles className="h-3 w-3 text-sophia-purple" />
                        {communityInsight.sophia_emotion.label}
                      </span>
                    </div>
                  </div>
                </div>
              ) : (
                <p className="text-center text-sm text-sophia-text2 py-4">
                  No community insights yet
                </p>
              )}

              <Link
                href="#"
                className="mt-4 block rounded-xl border-2 border-sophia-text/10 p-2.5 text-center text-sm font-medium text-sophia-text2 transition-all hover:border-sophia-purple/30 hover:text-sophia-purple"
              >
                View all community insights →
              </Link>
            </div>
          </aside>
        </div>
      </main>
    </div>
  )
}
