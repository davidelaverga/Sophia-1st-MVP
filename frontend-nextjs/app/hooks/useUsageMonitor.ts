"use client"

import { useEffect, useRef } from "react"
import { useSupabase } from "../providers"
import { useUsageLimitStore } from "../stores/usage-limit-store"
import { updateUsageAlerts } from "../lib/usage-tracker"
import type { UsageLimitInfo } from "../types/rate-limits"
import { logger } from "../lib/error-logger"

// Global ref to store the checkUsage function so it can be called from anywhere
let globalCheckUsage: (() => Promise<void>) | null = null

/**
 * Monitor user usage from Supabase and trigger alerts
 * This is a temporary solution until backend sends usage_info in responses
 */
export function useUsageMonitor() {
  const { user } = useSupabase()
  const intervalRef = useRef<NodeJS.Timeout | null>(null)

  useEffect(() => {
    if (!user) {
      // Clear user context when logged out
      logger.setUser(null)
      return
    }

    // Set user context for error tracking
    logger.setUser(user.id, user.email, user.user_metadata?.username)
    logger.addBreadcrumb("User authenticated", { userId: user.id })

    const checkUsage = async () => {
      if (!user) return

      try {
        // Fetch usage from backend API endpoint
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
        const apiKey = process.env.NEXT_PUBLIC_API_KEY || "dev-key"
        
        const response = await fetch(`${apiUrl}/api/usage/limits?user_id=${user.id}`, {
          headers: {
            "Authorization": `Bearer ${apiKey}`,
          },
        })
        
        if (!response.ok) {
          if (response.status === 401) {
            // User not authenticated, skip
            return
          }
          console.error("[usage] Error fetching usage:", response.statusText)
          return
        }

        const data = await response.json()
        
        if (!data) return

        console.log("[usage] Usage data received from backend:", data)

        // Check voice usage
        const voiceLimit = data.limits.daily_voice_seconds || 600
        const voiceUsed = data.daily_usage.voice_seconds || 0
        const voicePercent = data.percentage_used.voice || 0

        console.log("[usage] Voice usage:", voiceUsed, "/", voiceLimit, "=", voicePercent.toFixed(1) + "%")

        // Check text usage
        const textLimit = data.limits.daily_text_messages || 1800
        const textUsed = data.daily_usage.text_messages || 0
        const textPercent = data.percentage_used.text || 0

        console.log("[usage] Text usage:", textUsed, "/", textLimit, "=", textPercent.toFixed(1) + "%")

        // Update usage data in store (for blocking checks) - AFTER calculating both percentages
        // Also store user_id so chat-store can pass it to backend
        useUsageLimitStore.getState().setUsageData(voicePercent, textPercent, user.id)
        
        // Always check voice usage and trigger alerts
        const voiceInfo: UsageLimitInfo = {
          reason: "voice",
          plan_tier: data.plan_tier || "FREE",
          limit: voiceLimit,
          used: voiceUsed,
        }
        
        if (voicePercent >= 100) {
          // At 100%, show modal immediately and block all interaction
          useUsageLimitStore.getState().showModal(voiceInfo)
          useUsageLimitStore.getState().dismissToast()
          useUsageLimitStore.getState().dismissHint()
        } else if (voicePercent >= 50) {
          // Between 50-99%, show progressive alerts
          updateUsageAlerts(voiceInfo)
        } else {
          // Below 50%, clear all alerts
          useUsageLimitStore.getState().dismissHint()
          useUsageLimitStore.getState().dismissToast()
        }

        // Always check text usage and trigger alerts
        const textInfo: UsageLimitInfo = {
          reason: "text",
          plan_tier: data.plan_tier || "FREE",
          limit: textLimit,
          used: textUsed,
        }
        
        if (textPercent >= 100) {
          // At 100%, show modal immediately and block all interaction
          useUsageLimitStore.getState().showModal(textInfo)
          useUsageLimitStore.getState().dismissToast()
          useUsageLimitStore.getState().dismissHint()
        } else if (textPercent >= 50) {
          // Between 50-99%, show progressive alerts
          updateUsageAlerts(textInfo)
        }

        // Check reflections
        const reflectionsLimit = data.limits.monthly_reflections || 4
        const reflectionsUsed = data.monthly_reflections_used || 0
        const reflectionsPercent = data.percentage_used.reflections || 0

        if (reflectionsPercent >= 50) {
          const reflectionsInfo: UsageLimitInfo = {
            reason: "reflections",
            plan_tier: data.plan_tier || "FREE",
            limit: reflectionsLimit,
            used: reflectionsUsed,
          }
          updateUsageAlerts(reflectionsInfo)
        }
      } catch (err) {
        console.error("[usage] Error in usage monitor:", err)
      }
    }

    // Store checkUsage function globally so it can be called from anywhere
    globalCheckUsage = checkUsage

    // Check immediately
    checkUsage()

    // Then check every 5 seconds
    intervalRef.current = setInterval(checkUsage, 5000)

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
      globalCheckUsage = null
    }
  }, [user])
}

/**
 * Refresh usage data immediately (call after sending message/voice)
 * This ensures usage is updated right after user interaction
 */
export function refreshUsage() {
  if (globalCheckUsage) {
    console.log("[usage] refreshUsage() called - scheduling usage refresh...")
    // Try multiple times with increasing delays to ensure we catch the update
    // Backend updates usage after processing, so we need to wait a bit
    setTimeout(() => {
      console.log("[usage] First refresh attempt (1.5s delay)")
      globalCheckUsage?.()
    }, 1500)
    
    setTimeout(() => {
      console.log("[usage] Second refresh attempt (3s delay)")
      globalCheckUsage?.()
    }, 3000)
    
    setTimeout(() => {
      console.log("[usage] Third refresh attempt (5s delay)")
      globalCheckUsage?.()
    }, 5000)
  } else {
    console.warn("[usage] refreshUsage called but globalCheckUsage is not available")
  }
}

