"use client"

import { Fragment, useEffect, useRef, useState, useCallback, memo, lazy, Suspense } from "react"
import type { KeyboardEventHandler, RefObject, UIEvent } from "react"
import { Send, Loader2, Volume2, Square, Mic } from "lucide-react"
import { AppShell } from "./AppShell"
import { FeedbackStrip } from "./FeedbackStrip"
import { SessionFeedbackToast } from "./SessionFeedbackToast"
import { UsageHint } from "./UsageHint"
import { ErrorBoundary } from "./ErrorBoundary"
import { copy, t } from "../../copy"
import { useChatStore } from "../stores/chat-store"
import type { ChatMessage } from "../stores/chat-store"
import { getPresenceCopyKey, usePresenceStore } from "../stores/presence-store"
import { useReflectionPrompt } from "../hooks/useReflectionPrompt"
import { useFocusModeStore } from "../stores/focus-mode-store"
import { useVoiceLoop } from "../hooks/useVoiceLoop"
import { useModeSwitch } from "../hooks/useModeSwitch"
import { useSupabase } from "../providers"
import { useUsageMonitor } from "../hooks/useUsageMonitor"
import { useUsageLimitStore } from "../stores/usage-limit-store"
import { diagnoseMicrophoneAccess, isMicrophoneLikelySupported } from "../lib/microphone-debug"
import { useSessionPersistence } from "../hooks/useSessionPersistence"
import { useVoiceFallbackStore } from "../stores/voice-fallback-store"
import { InputModeIndicator } from "./InputModeIndicator"

// Lazy load heavy components that aren't needed immediately
const VoicePanel = lazy(() => import("./VoicePanel").then(mod => ({ default: mod.VoicePanel })))
const VoiceFocusView = lazy(() => import("./VoiceFocusView").then(mod => ({ default: mod.VoiceFocusView })))
const VoiceCollapsed = lazy(() => import("./VoiceCollapsed").then(mod => ({ default: mod.VoiceCollapsed })))
const ReflectionModal = lazy(() => import("./reflection/ReflectionModal").then(mod => ({ default: mod.ReflectionModal })))

export function ConversationView() {
  const composerRef = useRef<HTMLTextAreaElement>(null)
  const applyPrompt = useChatStore((state) => state.applyQuickPrompt)
  const conversationId = useChatStore((state) => state.conversationId)
  const lastCompletedTurnId = useChatStore((state) => state.lastCompletedTurnId)
  const { chunks, dismiss } = useReflectionPrompt(conversationId, lastCompletedTurnId)
  const [micSupportWarning, setMicSupportWarning] = useState<string | null>(null)
  
  // Session persistence - automatically save/restore conversations
  useSessionPersistence()
  
  // Focus mode state - must be declared before useEffect that uses it
  const focusMode = useFocusModeStore((state) => state.mode)
  const setMode = useFocusModeStore((state) => state.setMode)
  const setManualOverride = useFocusModeStore((state) => state.setManualOverride)
  
  // Voice fallback detection
  const shouldAutoFallback = useVoiceFallbackStore((state) => state.shouldAutoFallback)
  
  // Auto-fallback to text if voice has failed multiple times
  useEffect(() => {
    if (shouldAutoFallback() && focusMode === "voice") {
      console.log("[ConversationView] Auto-falling back to text mode due to voice failures")
      setMode("text")
      setManualOverride(true)
    }
  }, [shouldAutoFallback, focusMode, setMode, setManualOverride])
  
  // Check microphone support ONLY when user enters voice mode
  useEffect(() => {
    if (typeof window === "undefined" || focusMode !== "voice") {
      // Clear warning when leaving voice mode
      if (focusMode !== "voice") {
        setMicSupportWarning(null)
      }
      return
    }
    
    const checkSupport = async () => {
      try {
        const diagnostics = await diagnoseMicrophoneAccess()
        const supportCheck = isMicrophoneLikelySupported(diagnostics)
        
        if (!supportCheck.supported && supportCheck.issues.length > 0) {
          // Only show warning for critical issues (not just "prompt" state)
          const criticalIssues = supportCheck.issues.filter(issue => 
            !issue.includes("prompt") && 
            !issue.includes("unknown")
          )
          
          if (criticalIssues.length > 0) {
            setMicSupportWarning(criticalIssues[0])
            
            // Auto-dismiss after 4 seconds
            const dismissTimer = setTimeout(() => {
              setMicSupportWarning(null)
            }, 4000)
            
            return () => clearTimeout(dismissTimer)
          }
        }
      } catch (error) {
        // Silently fail - this is just a helpful check
        console.log("[ConversationView] Microphone support check failed:", error)
      }
    }
    
    // Run check when entering voice mode
    const timer = setTimeout(checkSupport, 300)
    return () => clearTimeout(timer)
  }, [focusMode])
  
  const isManualOverride = useFocusModeStore((state) => state.isManualOverride)
  
  // Voice state - SINGLE SOURCE OF TRUTH
  const { user } = useSupabase()
  const voiceState = useVoiceLoop(user?.id)
  const voiceStage = voiceState.stage
  
  // Reset voice state when leaving voice mode to prevent stuck states
  useEffect(() => {
    if (focusMode !== "voice") {
      // If we're leaving voice mode and voice is active, reset it
      if (voiceStage === "thinking" || voiceStage === "connecting" || voiceStage === "listening" || voiceStage === "speaking") {
        console.log("[ConversationView] Leaving voice mode, resetting voice state")
        voiceState.resetVoiceState?.()
      }
    }
    // REMOVED: Do NOT reset when entering voice mode in "thinking" state
    // "thinking" is a VALID state after user stops recording - backend is processing
    // Only reset if we're stuck (timeout handles that in useVoiceLoop)
  }, [focusMode, voiceStage, voiceState])
  
  // Monitor usage and trigger alerts
  useUsageMonitor()
  
  // Track composer focus and interaction
  const [composerHasFocus, setComposerHasFocus] = useState(false)
  const [userIsTyping, setUserIsTyping] = useState(false)
  const isLocked = useChatStore((state) => state.isLocked)

  const handlePromptSelect = useCallback((prompt: string) => {
    applyPrompt(prompt)
    requestAnimationFrame(() => composerRef.current?.focus())
  }, [applyPrompt])

  // Auto-switch focus mode based on user interaction
  // CLEAN Architecture: Uses domain logic from mode-switching.ts via useModeSwitch
  const { canAutoSwitch } = useModeSwitch()
  
  useEffect(() => {
    // Don't auto-switch if user manually overrode
    if (isManualOverride) return
    
    // Don't auto-switch if domain logic blocks it (operations in progress)
    if (!canAutoSwitch) return

    const isVoiceActive = voiceStage !== "idle" && voiceStage !== "error"

    // Priority 1: Voice is active (user is actively using voice) → Voice Focus
    if (isVoiceActive) {
      if (focusMode !== "voice") setMode("voice")
    }
    // Priority 2: User is typing or composer has focus → Text Focus
    // IMPORTANT: Stay in text focus even when Sophia is responding (isLocked)
    else if (composerHasFocus || userIsTyping) {
      if (focusMode !== "text") setMode("text")
    }
    // Priority 3: Sophia is responding in text mode → Stay in text focus
    else if (isLocked && focusMode === "text") {
      // Keep text focus when Sophia is responding
      return
    }
    // Priority 4: Nothing active → Only return to Full View if NOT in a focused mode
    // IMPORTANT: Don't auto-switch OUT of voice/text focus - user must manually switch
    else {
      // NEVER auto-switch out of voice or text focus modes
      // User must explicitly click "Switch to chat/voice mode" to change
      if (focusMode === "voice" || focusMode === "text") return
      
      // Only auto-switch TO full view if we're already in full view (no-op)
      if (focusMode === "full") return
    }
  }, [voiceStage, composerHasFocus, userIsTyping, isLocked, focusMode, setMode, isManualOverride, canAutoSwitch])

  // Track typing activity to maintain text focus
  useEffect(() => {
    if (composerHasFocus) {
      setUserIsTyping(true)
      
      // Reset typing flag after 5 seconds of no focus
      const timer = setTimeout(() => {
        if (!composerHasFocus) {
          setUserIsTyping(false)
        }
      }, 5000)
      
      return () => clearTimeout(timer)
    }
  }, [composerHasFocus])

  // Reset manual override when user explicitly switches context
  useEffect(() => {
    if (isManualOverride) {
      const timer = setTimeout(() => {
        // Only reset if nothing is active (no voice, no typing, no Sophia responding)
        if (voiceStage === "idle" && !composerHasFocus && !userIsTyping && !isLocked) {
          setManualOverride(false)
        }
      }, 30000) // Reset after 30 seconds of complete inactivity
      return () => clearTimeout(timer)
    }
  }, [isManualOverride, setManualOverride, voiceStage, composerHasFocus, userIsTyping, isLocked])

  return (
    <AppShell actionBar={focusMode !== "voice" ? <Composer textareaRef={composerRef} onFocusChange={setComposerHasFocus} /> : undefined}>
      {/* Microphone support warning - only in voice mode, elegant Sophia styling */}
      {micSupportWarning && focusMode === "voice" && (
        <div className="mx-auto max-w-2xl animate-fadeIn">
          <div className="rounded-2xl border border-sophia-purple/20 bg-sophia-surface px-4 py-3 shadow-soft">
            <div className="flex items-start gap-3">
              <div className="mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-sophia-purple/10">
                <Mic className="h-3 w-3 text-sophia-purple" />
              </div>
              <div className="flex-1 space-y-1">
                <p className="text-sm font-medium text-sophia-text">Microphone Access</p>
                <p className="text-xs leading-relaxed text-sophia-text2">{micSupportWarning}</p>
              </div>
              <button
                type="button"
                onClick={() => setMicSupportWarning(null)}
                className="flex-shrink-0 rounded-lg p-1 text-sophia-text2/60 transition-colors hover:bg-sophia-purple/10 hover:text-sophia-purple"
                aria-label="Dismiss"
              >
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      )}
      <div className="space-y-4 transition-all duration-500 ease-in-out">
        {/* Voice Focus Mode */}
        {focusMode === "voice" && (
          <div className="animate-fadeIn">
            <Suspense fallback={<div className="h-48 animate-pulse rounded-2xl bg-sophia-surface" />}>
              <VoiceFocusView voiceState={voiceState} />
            </Suspense>
          </div>
        )}

        {/* Text Focus Mode */}
        {focusMode === "text" && (
          <div className="space-y-4 animate-fadeIn">
            <Suspense fallback={<div className="h-12 animate-pulse rounded-xl bg-sophia-surface" />}>
              <VoiceCollapsed />
            </Suspense>
            <Transcript onPromptSelect={handlePromptSelect} />
          </div>
        )}

        {/* Full View Mode */}
        {focusMode === "full" && (
          <div className="space-y-4 animate-fadeIn">
            <Suspense fallback={<div className="h-32 animate-pulse rounded-2xl bg-sophia-surface" />}>
              <VoicePanel voiceState={voiceState} />
            </Suspense>
            <Transcript onPromptSelect={handlePromptSelect} />
          </div>
        )}
      </div>
      {/* Only show feedback toast in chat mode, not voice mode */}
      {!chunks && focusMode !== "voice" && <SessionFeedbackToast />}
      {chunks && conversationId && (
        <ErrorBoundary componentName="ReflectionModal">
          <Suspense fallback={null}>
            <ReflectionModal conversationId={conversationId} chunks={chunks} onClose={dismiss} />
          </Suspense>
        </ErrorBoundary>
      )}
    </AppShell>
  )
}

function Transcript({ onPromptSelect, compact }: { onPromptSelect: (prompt: string) => void; compact?: boolean }) {
  const messages = useChatStore((state) => state.messages)
  const isLocked = useChatStore((state) => state.isLocked)
  const lastError = useChatStore((state) => state.lastError)
  const scrollAnchorRef = useRef<HTMLDivElement>(null)
  const scrollContainerRef = useRef<HTMLDivElement>(null)
  const [shouldStickToBottom, setShouldStickToBottom] = useState(true)

  useEffect(() => {
    if (shouldStickToBottom) {
      scrollAnchorRef.current?.scrollIntoView({ behavior: "smooth", block: "end" })
    }
  }, [messages.length, isLocked, shouldStickToBottom])

  const handleScroll = useCallback((event: UIEvent<HTMLDivElement>) => {
    const target = event.currentTarget
    const distanceFromBottom = target.scrollHeight - target.scrollTop - target.clientHeight
    setShouldStickToBottom(distanceFromBottom < 80)
  }, [])

  const maxHeight = compact ? "40vh" : "65vh"
  const minHeight = compact ? "200px" : "360px"

  // In compact mode (Voice Focus), don't show anything if no messages yet
  if (compact && messages.length === 0) {
    return null
  }

  return (
    <div className="rounded-3xl bg-sophia-surface p-4 shadow-soft">
      <div
        ref={scrollContainerRef}
        role="log"
        aria-label="Conversation transcript"
        aria-live="polite"
        aria-relevant="additions text"
        aria-busy={isLocked}
        onScroll={handleScroll}
        className="flex flex-col gap-4 overflow-y-auto pr-2"
        style={{ maxHeight, minHeight }}
      >
        {messages.length === 0 ? (
          <EmptyState onPromptSelect={onPromptSelect} />
        ) : (
          <Fragment>
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
            {isLocked && <StreamingIndicator />}
          </Fragment>
        )}
        <div ref={scrollAnchorRef} />
      </div>
      {lastError && (
        <p className="mt-3 rounded-2xl bg-sophia-error/10 px-4 py-3 text-sm text-sophia-text" role="status">
          {lastError}
        </p>
      )}
    </div>
  )
}

function EmptyState({ onPromptSelect }: { onPromptSelect: (prompt: string) => void }) {
  return (
    <div className="flex h-full flex-col justify-between gap-8 rounded-2xl bg-sophia-bubble p-8 text-sophia-text">
      <div className="space-y-4">
        {/* Presence indicator with breathing animation */}
        <p className="inline-flex items-center gap-2 text-sm font-medium uppercase tracking-wide text-sophia-purple animate-breathe">
          <span className="text-base">{copy.home.hero.statusIcon}</span>
          <span>{copy.home.hero.status}</span>
        </p>
        
        {/* Welcome message with improved hierarchy */}
        <div className="space-y-3">
          <h2 className="text-3xl font-semibold text-sophia-text sm:text-4xl">
            {copy.home.hero.heading}
          </h2>
          <p className="text-base leading-relaxed text-sophia-text2 sm:text-lg">
            {copy.home.hero.body}
          </p>
        </div>
      </div>
      
      {/* Quick prompts with enhanced styling */}
      <div className="space-y-4">
        <p className="text-sm font-medium text-sophia-text2">{t("chat.quickStartTitle")}</p>
        <div className="flex flex-wrap gap-2.5">
          {copy.chat.quickPrompts.map((prompt, index) => (
            <button
              key={prompt.id}
              type="button"
              className="group rounded-xl border border-sophia-purple/15 bg-sophia-button/70 px-4 py-2.5 text-sm font-medium text-sophia-text shadow-sm transition-all duration-300 ease-out hover:scale-[1.02] hover:border-sophia-purple/40 hover:bg-sophia-button-hover hover:text-sophia-purple hover:shadow-md active:scale-[0.98]"
              onClick={() => onPromptSelect(prompt.label)}
              style={{ animationDelay: `${index * 50}ms` }}
            >
              <span className="mr-2 inline-block text-base transition-transform duration-300 group-hover:scale-110" aria-hidden>
                {prompt.emoji}
              </span>
              <span>{prompt.label}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

const MessageBubble = memo(function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user"
  const alignment = isUser ? "justify-end" : "justify-start"
  const bubbleClasses = isUser
    ? "bg-sophia-user text-sophia-text"
    : message.status === "error"
      ? "bg-sophia-error/10 text-sophia-text"
      : "bg-sophia-reply text-sophia-text"

  const [isPlaying, setIsPlaying] = useState(false)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  const handleAudio = useCallback(async () => {
    if (!message.audioUrl) return
    
    // If already playing, stop it
    if (isPlaying && audioRef.current) {
      audioRef.current.pause()
      audioRef.current.currentTime = 0
      setIsPlaying(false)
      return
    }

    try {
      // Stop any other audio that might be playing
      if (audioRef.current) {
        audioRef.current.pause()
        audioRef.current.currentTime = 0
      }

      const audio = new Audio(message.audioUrl)
      audioRef.current = audio
      
      audio.onplay = () => setIsPlaying(true)
      audio.onended = () => {
        setIsPlaying(false)
        audioRef.current = null
      }
      audio.onerror = () => {
        setIsPlaying(false)
        audioRef.current = null
        console.warn("[conversation] Audio playback failed")
      }
      audio.onpause = () => {
        if (audio.currentTime === 0) {
          setIsPlaying(false)
        }
      }

      await audio.play()
    } catch (error) {
      console.warn("[conversation] Audio playback failed", error)
      setIsPlaying(false)
      audioRef.current = null
    }
  }, [message.audioUrl, isPlaying])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause()
        audioRef.current = null
      }
    }
  }, [])

  return (
    <div className={`flex w-full gap-3 ${alignment} animate-fadeIn`} role="article" aria-label={isUser ? "You said" : "Sophia replied"}>
      {!isUser && (
        <div className="mt-1 flex h-10 w-10 items-center justify-center rounded-2xl bg-sophia-purple text-sm font-semibold text-white shadow-md animate-breatheSlow">
          {copy.brand.initial}
        </div>
      )}
      <div className="max-w-[80%] space-y-2">
        <div className={`rounded-3xl px-4 py-3 text-sm leading-relaxed shadow-soft/30 transition-all duration-300 ease-out ${bubbleClasses}`}>
          <div className="flex items-start gap-2">
            {!isUser && message.source === "voice" && (
              <Mic className="h-3.5 w-3.5 text-sophia-purple/70 mt-0.5 flex-shrink-0" />
            )}
            <span className="flex-1">
              {message.content || <span className="text-sophia-text2 animate-breathe">{t("chat.loading")}</span>}
            </span>
          </div>
        </div>
        {!isUser && message.turnId && <FeedbackStrip turnId={message.turnId} />}
        {message.audioUrl && (
          <button
            type="button"
            onClick={handleAudio}
            onMouseDown={(e) => e.preventDefault()} // Prevent focus loss
            className="flex items-center gap-2 text-xs font-medium text-sophia-purple transition-all duration-300 hover:scale-105 hover:text-sophia-purple/80 active:scale-95"
          >
            {isPlaying ? (
              <>
                <Square className="h-4 w-4 fill-current" />
                <span>Stop audio</span>
              </>
            ) : (
              <>
                <Volume2 className="h-4 w-4" />
                {t("chat.audioButton")}
              </>
            )}
          </button>
        )}
      </div>
      {isUser && (
        <div className="mt-1 flex h-10 w-10 items-center justify-center rounded-2xl border border-sophia-text/10 text-base">
          👤
        </div>
      )}
    </div>
  )
})

function StreamingIndicator() {
  const presenceStatus = usePresenceStore((state) => state.status)
  const messages = [
    "Taking a moment to reflect...",
    "Considering your words...",
    "Gathering my thoughts...",
  ]
  const message = presenceStatus === "reflecting" ? messages[2] : presenceStatus === "thinking" ? messages[1] : messages[0]
  
  return (
    <div className="flex items-center gap-3 text-sm text-sophia-text2 animate-fadeIn">
      <div className="flex gap-2">
        <span 
          className="inline-block h-3 w-3 rounded-full bg-gradient-to-br from-sophia-purple to-sophia-glow animate-glowBreathe" 
          style={{ animationDelay: "0ms" }} 
        />
        <span 
          className="inline-block h-3 w-3 rounded-full bg-gradient-to-br from-sophia-purple to-sophia-glow animate-glowBreathe" 
          style={{ animationDelay: "400ms" }} 
        />
        <span 
          className="inline-block h-3 w-3 rounded-full bg-gradient-to-br from-sophia-purple to-sophia-glow animate-glowBreathe" 
          style={{ animationDelay: "800ms" }} 
        />
      </div>
      <span className="animate-pulse">{message}</span>
    </div>
  )
}

function Composer({ 
  textareaRef, 
  onFocusChange 
}: { 
  textareaRef: RefObject<HTMLTextAreaElement>
  onFocusChange?: (hasFocus: boolean) => void
}) {
  const value = useChatStore((state) => state.composerValue)
  const setValue = useChatStore((state) => state.setComposerValue)
  const sendMessage = useChatStore((state) => state.sendMessage)
  const isLocked = useChatStore((state) => state.isLocked)
  const presenceStatus = usePresenceStore((state) => state.status)
  const presenceDetail = usePresenceStore((state) => state.detail)
  
  // Block interaction if usage limit modal is open
  const isModalOpen = useUsageLimitStore((state) => state.isOpen)

  const handleSend = useCallback(() => {
    // Block sending if modal is open
    if (isModalOpen) return
    sendMessage()
  }, [isModalOpen, sendMessage])

  const onKeyDown: KeyboardEventHandler<HTMLTextAreaElement> = useCallback((event) => {
    // Block keyboard interaction if modal is open
    if (isModalOpen) {
      event.preventDefault()
      return
    }
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault()
      handleSend()
    }
  }, [isModalOpen, handleSend])

  const handleFocus = useCallback(() => {
    onFocusChange?.(true)
  }, [onFocusChange])

  const handleBlur = useCallback((e: React.FocusEvent<HTMLTextAreaElement>) => {
    // Only blur if focus is moving outside the composer area
    // Don't blur if clicking on buttons within the chat (like play audio)
    const relatedTarget = e.relatedTarget as HTMLElement
    if (relatedTarget && relatedTarget.closest('.composer-container')) {
      return
    }
    onFocusChange?.(false)
  }, [onFocusChange])

  return (
    <div className="space-y-2 composer-container">
      {/* Voice fallback indicator */}
      <InputModeIndicator />
      
      <div className="rounded-2xl bg-sophia-surface p-4 shadow-soft transition-all duration-300">
        <div className="flex flex-col gap-3">
          <textarea
            ref={textareaRef}
            rows={3}
            value={value}
            placeholder={isModalOpen ? "Please close the limit modal to continue" : t("chat.placeholder")}
            disabled={isLocked || isModalOpen}
            onChange={(event) => {
              if (isModalOpen) return
              setValue(event.target.value)
            }}
            onKeyDown={onKeyDown}
            onFocus={handleFocus}
            onBlur={handleBlur}
            style={{ backgroundColor: 'var(--input-bg)' }}
            className={`w-full resize-none rounded-2xl border border-sophia-input-border px-4 py-3 text-base text-sophia-text placeholder:text-sophia-text2 outline-none transition-all duration-300 ease-out focus:border-sophia-purple/60 focus:shadow-sm ${
              isModalOpen ? "opacity-50 cursor-not-allowed" : ""
            }`}
          />
          <div className="flex items-center justify-between">
            <p className="text-sm text-sophia-text2 transition-all duration-300">
              {isModalOpen ? "Usage limit reached" : (presenceDetail ?? t(getPresenceCopyKey(presenceStatus)))}
            </p>
            <button
              type="button"
              onClick={handleSend}
              disabled={!value.trim() || isLocked || isModalOpen}
              className="inline-flex items-center gap-2 rounded-2xl bg-sophia-purple px-5 py-2 text-sm font-medium text-white shadow-md transition-all duration-300 ease-out hover:scale-[1.02] hover:shadow-lg active:scale-[0.98] disabled:opacity-60 disabled:hover:scale-100"
            >
              {isLocked ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              <span>{isLocked ? t("chat.sending") : t("chat.send")}</span>
            </button>
          </div>
        </div>
      </div>
      <UsageHint />
    </div>
  )
}

