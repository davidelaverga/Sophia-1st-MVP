"use client"

import { useEffect } from "react"
import { RefreshCw, Home, MessageSquare } from "lucide-react"

type ErrorFallbackProps = {
  error?: Error
  errorMessage?: string
  onReset?: () => void
  showHomeLink?: boolean
}

/**
 * Fallback UI shown when a component crashes
 * 
 * Features:
 * - User-friendly error message
 * - Reset/retry action
 * - Navigation options
 * - Maintains Sophia's gentle aesthetic
 */
export function ErrorFallback({
  error,
  errorMessage,
  onReset,
  showHomeLink = true,
}: ErrorFallbackProps) {
  useEffect(() => {
    // Log error details (can be sent to monitoring service)
    console.error('[ErrorFallback] Component error:', error)
  }, [error])

  const displayMessage = errorMessage || error?.message || "Something unexpected happened"

  return (
    <div className="flex min-h-[400px] items-center justify-center px-4 py-8">
      <div className="w-full max-w-md space-y-6 rounded-3xl bg-sophia-surface p-6 text-center shadow-soft">
        {/* Icon */}
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-sophia-error/10">
          <MessageSquare className="h-8 w-8 text-sophia-error" />
        </div>

        {/* Title */}
        <div>
          <h2 className="text-xl font-semibold text-sophia-text">
            Oops! Something went wrong
          </h2>
          <p className="mt-2 text-sm text-sophia-text2">
            {displayMessage}
          </p>
        </div>

        {/* Actions */}
        <div className="flex flex-col gap-3 sm:flex-row sm:justify-center">
          {onReset && (
            <button
              type="button"
              onClick={onReset}
              className="inline-flex items-center justify-center gap-2 rounded-2xl bg-sophia-purple px-6 py-3 text-sm font-medium text-white shadow-md transition-all hover:scale-[1.02] hover:shadow-lg active:scale-[0.98]"
            >
              <RefreshCw className="h-4 w-4" />
              Try again
            </button>
          )}

          {showHomeLink && (
            <a
              href="/"
              className="inline-flex items-center justify-center gap-2 rounded-2xl border border-sophia-text/20 bg-sophia-button px-6 py-3 text-sm font-medium text-sophia-text transition-all hover:border-sophia-purple/40 hover:bg-sophia-button-hover"
            >
              <Home className="h-4 w-4" />
              Go home
            </a>
          )}
        </div>

        {/* Development info */}
        {process.env.NODE_ENV === 'development' && error?.stack && (
          <details className="mt-6 text-left">
            <summary className="cursor-pointer text-xs text-sophia-text2 hover:text-sophia-text">
              Developer info (only visible in dev mode)
            </summary>
            <pre className="mt-2 max-h-40 overflow-auto rounded-lg bg-sophia-bg p-3 text-[10px] text-sophia-text2">
              {error.stack}
            </pre>
          </details>
        )}
      </div>
    </div>
  )
}
