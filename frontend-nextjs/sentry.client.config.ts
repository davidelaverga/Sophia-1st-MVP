import * as Sentry from "@sentry/nextjs"

const SENTRY_DSN = process.env.NEXT_PUBLIC_SENTRY_DSN

Sentry.init({
  dsn: SENTRY_DSN,
  
  // Set tracesSampleRate to 1.0 to capture 100% of transactions for performance monitoring.
  // We recommend adjusting this value in production
  tracesSampleRate: process.env.NODE_ENV === "production" ? 0.1 : 1.0,
  
  // Capture Replay for 10% of all sessions,
  // plus for 100% of sessions with an error
  replaysSessionSampleRate: 0.1,
  replaysOnErrorSampleRate: 1.0,
  
  // Setting this option to true will print useful information to the console while you're setting up Sentry.
  debug: false,
  
  environment: process.env.NODE_ENV,
  
  integrations: [
    Sentry.replayIntegration({
      // Mask all text content, ignore all media
      maskAllText: true,
      blockAllMedia: true,
    }),
  ],
  
  // Filter out certain errors
  ignoreErrors: [
    // Browser extension errors
    "top.GLOBALS",
    "originalCreateNotification",
    "canvas.contentDocument",
    "MyApp_RemoveAllHighlights",
    "atomicFindClose",
    // Network errors that are user-related
    "NetworkError",
    "Network request failed",
  ],
  
  beforeSend(event, hint) {
    // Don't send events in development unless explicitly enabled
    if (process.env.NODE_ENV === "development" && !process.env.NEXT_PUBLIC_SENTRY_ENABLED) {
      return null
    }
    return event
  },
})
