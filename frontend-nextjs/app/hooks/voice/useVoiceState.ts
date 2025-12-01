/**
 * Voice state machine hook
 * Manages voice interaction stages and transitions
 */

import { useState, useCallback } from "react"
import type { VoiceStage, RouterPath } from "./voice-utils"

export function useVoiceState() {
  const [stage, setStage] = useState<VoiceStage>("idle")
  const [partialReply, setPartialReply] = useState("")
  const [finalReply, setFinalReply] = useState("")
  const [error, setError] = useState<string>()
  const [path, setPath] = useState<RouterPath>()
  const [needsUnlock, setNeedsUnlock] = useState(false)

  const resetState = useCallback(() => {
    setStage("idle")
    setPartialReply("")
    setFinalReply("")
    setError(undefined)
    setPath(undefined)
  }, [])

  const updatePartialReply = useCallback((text: string) => {
    setPartialReply(text)
  }, [])

  const updateFinalReply = useCallback((text: string) => {
    setFinalReply(text)
    setPartialReply("")
  }, [])

  const setErrorMessage = useCallback((message: string) => {
    setError(message)
    setStage("error")
  }, [])

  const clearError = useCallback(() => {
    setError(undefined)
    if (stage === "error") {
      setStage("idle")
    }
  }, [stage])

  return {
    // State
    stage,
    partialReply,
    finalReply,
    error,
    path,
    needsUnlock,
    
    // Actions
    setStage,
    setPath,
    setNeedsUnlock,
    resetState,
    updatePartialReply,
    updateFinalReply,
    setErrorMessage,
    clearError,
  }
}
