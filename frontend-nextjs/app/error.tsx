"use client"

import { useEffect } from "react"
import { ErrorFallback } from "./components/ErrorFallback"
import { logger } from "./lib/error-logger"

/**
 * Global error boundary for the entire app
 * 
 * Catches unhandled errors in any component and shows a fallback UI
 * instead of crashing the entire application.
 * 
 * @see https://nextjs.org/docs/app/building-your-application/routing/error-handling
 */
export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    // Log the error to our error tracking service
    logger.fatal(error, {
      component: 'GlobalErrorBoundary',
      metadata: {
        digest: error.digest,
        name: error.name,
      },
    })
  }, [error])

  return (
    <ErrorFallback
      error={error}
      onReset={reset}
      showHomeLink={true}
    />
  )
}
