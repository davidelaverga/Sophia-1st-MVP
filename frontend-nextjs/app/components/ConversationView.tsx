'use client'
import { VoicePanel } from "./VoicePanel"
import { VoiceFocusView } from "./VoiceFocusView"
import { VoiceCollapsed } from "./VoiceCollapsed"
import { FeedbackStrip } from "./FeedbackStrip"
import { SessionFeedbackToast } from "./SessionFeedbackToast"
import { ReflectionModal } from "./reflection/ReflectionModal"
import { UsageHint } from "./UsageHint"
import { copy, t } from "../../copy"
import { useChatStore } from "../stores/chat-store"
import type { ChatMessage } from "../stores/chat-store"
import { getPresenceCopyKey, usePresenceStore } from "../stores/presence-store"
import { useReflectionPrompt } from "../hooks/useReflectionPrompt"
import { useFocusModeStore } from "../stores/focus-mode-store"
import { useVoiceLoop } from "../hooks/useVoiceLoop"
import { useSupabase } from "../providers"
import { useUsageMonitor } from "../hooks/useUsageMonitor"
import { useUsageLimitStore } from "../stores/usage-limit-store"
import { diagnoseMicrophoneAccess, isMicrophoneLikelySupported } from "../lib/microphone-debug"
import { Loader2, Mic, Send, Square, Volume2 } from "lucide-react"
import { Fragment, KeyboardEventHandler, RefObject, useEffect, useRef, useState } from "react"
import { AppShell } from "./AppShell"

export function ConversationView() {
  const composerRef = useRef<HTMLTextAreaElement>(null)
  const applyPrompt = useChatStore((state) => state.applyQuickPrompt)
  const conversationId = useChatStore((state) => state.conversationId)
  const lastCompletedTurnId = useChatStore((state) => state.lastCompletedTurnId)
  const { chunks, dismiss } = useReflectionPrompt(conversationId, lastCompletedTurnId)
  const [micSupportWarning, setMicSupportWarning] = useState<string | null>(null)
  
  // Check microphone support on mount (non-blocking, just for user info)
  useEffect(() => {
    if (typeof window === "undefined") return
    
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
          }
        }
      } catch (error) {
        // Silently fail - this is just a helpful check
        console.log("[ConversationView] Microphone support check failed:", error)
      }
    }
    
    // Run check after a short delay to not block initial render
    const timer = setTimeout(checkSupport, 1000)
    return () => clearTimeout(timer)
  }, [])
  
  // Focus mode state
  const focusMode = useFocusModeStore((state) => state.mode)
  const setMode = useFocusModeStore((state) => state.setMode)
  const isManualOverride = useFocusModeStore((state) => state.isManualOverride)
  const setManualOverride = useFocusModeStore((state) => state.setManualOverride)
  
  // Voice state - SINGLE SOURCE OF TRUTH
  const { user } = useSupabase()
  const voiceState = useVoiceLoop(user?.id)
  const voiceStage = voiceState.stage
  
  // Monitor usage and trigger alerts
  useUsageMonitor()
  
  // Track composer focus and interaction
  const [composerHasFocus, setComposerHasFocus] = useState(false)
  const [userIsTyping, setUserIsTyping] = useState(false)
  const isLocked = useChatStore((state) => state.isLocked)

  const handlePromptSelect = (prompt: string) => {
    applyPrompt(prompt)
    requestAnimationFrame(() => composerRef.current?.focus())
  }

  // Auto-switch focus mode based on user interaction
  useEffect(() => {
    // Don't auto-switch if user manually overrode
    if (isManualOverride) return

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
  }, [voiceStage, composerHasFocus, userIsTyping, isLocked, focusMode, setMode, isManualOverride])

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
      {/* Microphone support warning (non-blocking, informational) */}
      {micSupportWarning && (
        <div className="mx-auto max-w-2xl rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 animate-fadeIn">
          <p className="font-medium">⚠️ Microphone Access Note</p>
          <p className="mt-1 text-xs">{micSupportWarning}</p>
          <p className="mt-2 text-xs opacity-75">You can still try using voice - the browser will prompt for permission when needed.</p>
        </div>
      )}
      <div className="space-y-4 transition-all duration-500 ease-in-out">
        {/* Voice Focus Mode */}
        {focusMode === "voice" && (
          <div className="animate-fadeIn">
            <VoiceFocusView voiceState={voiceState} />
          </div>
        )}

        {/* Text Focus Mode */}
        {focusMode === "text" && (
          <div className="space-y-4 animate-fadeIn">
            <VoiceCollapsed />
            <Transcript onPromptSelect={handlePromptSelect} />
          </div>
        )}

        {/* Full View Mode */}
        {focusMode === "full" && (
          <div className="space-y-4 animate-fadeIn">
            <VoicePanel voiceState={voiceState} />
            <Transcript onPromptSelect={handlePromptSelect} />
          </div>
        )}
      </div>
      {!chunks && <SessionFeedbackToast />}
      {chunks && conversationId && (
        <ReflectionModal conversationId={conversationId} chunks={chunks} onClose={dismiss} />
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

  const handleScroll = (event: any) => {
    const target = event.currentTarget
    const distanceFromBottom = target.scrollHeight - target.scrollTop - target.clientHeight
    setShouldStickToBottom(distanceFromBottom < 80)
  }

  const maxHeight = compact ? "40vh" : "65vh"
  const minHeight = compact ? "200px" : "360px"

  // In compact mode (Voice Focus), don't show anything if no messages yet
  if (compact && messages.length === 0) {
    return null
  }

  return (
    <div className="rounded-3xl bg-white p-4 shadow-soft">
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
              className="group rounded-2xl border border-sophia-text/10 bg-white/70 px-4 py-2.5 text-sm font-medium text-sophia-text shadow-sm transition-all duration-300 ease-out hover:scale-[1.02] hover:border-sophia-purple/40 hover:bg-white hover:text-sophia-purple hover:shadow-md active:scale-[0.98]"
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

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user"
  const alignment = isUser ? "justify-end" : "justify-start"
  const bubbleClasses = isUser
    ? "bg-sophia-user text-sophia-text"
    : message.status === "error"
      ? "bg-sophia-error/10 text-sophia-text"
      : "bg-sophia-reply text-sophia-text"

  const [isPlaying, setIsPlaying] = useState(false)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  const handleAudio = async () => {
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
  }

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
}

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

  const handleSend = () => {
    // Block sending if modal is open
    if (isModalOpen) return
    sendMessage()
  }

  const onKeyDown: KeyboardEventHandler<HTMLTextAreaElement> = (event) => {
    // Block keyboard interaction if modal is open
    if (isModalOpen) {
      event.preventDefault()
      return
    }
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault()
      handleSend()
    }
  }

  const handleFocus = () => {
    onFocusChange?.(true)
  }

  const handleBlur = (e: React.FocusEvent<HTMLTextAreaElement>) => {
    // Only blur if focus is moving outside the composer area
    // Don't blur if clicking on buttons within the chat (like play audio)
    const relatedTarget = e.relatedTarget as HTMLElement
    if (relatedTarget && relatedTarget.closest('.composer-container')) {
      return
    }
    onFocusChange?.(false)
  }

  return (
    <div className="space-y-2 composer-container">
      <div className="rounded-2xl bg-white p-4 shadow-soft transition-all duration-300">
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
            className={`w-full resize-none rounded-2xl border border-sophia-text/10 bg-sophia-user px-4 py-3 text-base text-sophia-text outline-none transition-all duration-300 ease-out focus:border-sophia-purple/60 focus:shadow-sm ${
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