"use client"

type TelemetryEvent = {
  name: string
  payload?: Record<string, any>
  timestamp: number
}

const TELEMETRY_ENDPOINT =
  typeof window !== "undefined" ? process.env.NEXT_PUBLIC_TELEMETRY_URL ?? "" : ""

const queue: TelemetryEvent[] = []
const BATCH_DELAY_MS = 5000
let flushTimer: number | null = null

const flushQueue = (opts?: { sync?: boolean }) => {
  if (!queue.length) return
  if (!TELEMETRY_ENDPOINT) {
    if (process.env.NODE_ENV !== "production") {
      console.debug("[telemetry]", queue)
    }
    queue.length = 0
    return
  }
  const batch = queue.splice(0, queue.length)
  const body = JSON.stringify({ events: batch })

  if (opts?.sync && typeof navigator !== "undefined" && typeof navigator.sendBeacon === "function") {
    try {
      navigator.sendBeacon(TELEMETRY_ENDPOINT, body)
      return
    } catch {
      // fallthrough to fetch
    }
  }

  fetch(TELEMETRY_ENDPOINT, {
    method: "POST",
    body,
    headers: {
      "Content-Type": "application/json",
    },
    keepalive: true,
  }).catch((error) => {
    console.warn("[telemetry] send failed", error)
  })
}

const scheduleFlush = () => {
  if (flushTimer !== null) return
  if (typeof window === "undefined") return
  flushTimer = window.setTimeout(() => {
    flushTimer = null
    flushQueue()
    if (queue.length > 0) {
      scheduleFlush()
    }
  }, BATCH_DELAY_MS)
}

if (typeof window !== "undefined") {
  window.addEventListener(
    "visibilitychange",
    () => {
      if (document.visibilityState === "hidden") {
        flushQueue({ sync: true })
      }
    },
    { passive: true },
  )
  window.addEventListener(
    "pagehide",
    () => {
      flushQueue({ sync: true })
    },
    { passive: true },
  )
}

export const emitTelemetry = (name: string, payload?: Record<string, any>) => {
  if (typeof window === "undefined") return
  queue.push({
    name,
    payload,
    timestamp: Date.now(),
  })
  scheduleFlush()
}

