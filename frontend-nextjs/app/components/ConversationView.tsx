"use client"

import { Fragment, useEffect, useRef, useState } from "react"
import type { KeyboardEventHandler, RefObject, UIEvent } from "react"
import { Send, Loader2, Volume2, Square } from "lucide-react"
import { AppShell } from "./AppShell"
import { VoicePanel } from "./VoicePanel"
import { FeedbackStrip } from "./FeedbackStrip"
import { SessionFeedbackToast } from "./SessionFeedbackToast"
import { ReflectionModal } from "./reflection/ReflectionModal"
import { UsageHint } from "./UsageHint"
import { copy, t } from "../../copy"
import { useChatStore } from "../stores/chat-store"
import type { ChatMessage } from "../stores/chat-store"
import { getPresenceCopyKey, usePresenceStore } from "../stores/presence-store"
import { useReflectionPrompt } from "../hooks/useReflectionPrompt"

export function ConversationView() {
  const composerRef = useRef<HTMLTextAreaElement>(null)
  const applyPrompt = useChatStore((state) => state.applyQuickPrompt)
  const conversationId = useChatStore((state) => state.conversationId)
  const lastCompletedTurnId = useChatStore((state) => state.lastCompletedTurnId)
  const { chunks, dismiss } = useReflectionPrompt(conversationId, lastCompletedTurnId)

  const handlePromptSelect = (prompt: string) => {
    applyPrompt(prompt)
    requestAnimationFrame(() => composerRef.current?.focus())
  }

  return (
    <AppShell actionBar={<Composer textareaRef={composerRef} />}>
      <div className="space-y-4">
        <VoicePanel />
        <Transcript onPromptSelect={handlePromptSelect} />
      </div>
      {!chunks && <SessionFeedbackToast />}
      {chunks && conversationId && (
        <ReflectionModal conversationId={conversationId} chunks={chunks} onClose={dismiss} />
      )}
    </AppShell>
  )
}

function Transcript({ onPromptSelect }: { onPromptSelect: (prompt: string) => void }) {
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

  const handleScroll = (event: UIEvent<HTMLDivElement>) => {
    const target = event.currentTarget
    const distanceFromBottom = target.scrollHeight - target.scrollTop - target.clientHeight
    setShouldStickToBottom(distanceFromBottom < 80)
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
        style={{ maxHeight: "65vh", minHeight: "360px" }}
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
          {message.content || <span className="text-sophia-text2 animate-breathe">{t("chat.loading")}</span>}
        </div>
        {!isUser && message.turnId && <FeedbackStrip turnId={message.turnId} />}
        {message.audioUrl && (
          <button
            type="button"
            onClick={handleAudio}
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
      <div className="flex gap-1">
        <span className="inline-block h-2 w-2 rounded-full bg-sophia-purple animate-breathe" style={{ animationDelay: "0ms" }} />
        <span className="inline-block h-2 w-2 rounded-full bg-sophia-purple animate-breathe" style={{ animationDelay: "150ms" }} />
        <span className="inline-block h-2 w-2 rounded-full bg-sophia-purple animate-breathe" style={{ animationDelay: "300ms" }} />
      </div>
      <span className="animate-breathe">{message}</span>
    </div>
  )
}

function Composer({ textareaRef }: { textareaRef: RefObject<HTMLTextAreaElement> }) {
  const value = useChatStore((state) => state.composerValue)
  const setValue = useChatStore((state) => state.setComposerValue)
  const sendMessage = useChatStore((state) => state.sendMessage)
  const isLocked = useChatStore((state) => state.isLocked)
  const presenceStatus = usePresenceStore((state) => state.status)
  const presenceDetail = usePresenceStore((state) => state.detail)

  const handleSend = () => {
    sendMessage()
  }

  const onKeyDown: KeyboardEventHandler<HTMLTextAreaElement> = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="space-y-2">
      <div className="rounded-2xl bg-white p-4 shadow-soft transition-all duration-300">
        <div className="flex flex-col gap-3">
          <textarea
            ref={textareaRef}
            rows={3}
            value={value}
            placeholder={t("chat.placeholder")}
            disabled={isLocked}
            onChange={(event) => setValue(event.target.value)}
            onKeyDown={onKeyDown}
            className="w-full resize-none rounded-2xl border border-sophia-text/10 bg-sophia-user px-4 py-3 text-base text-sophia-text outline-none transition-all duration-300 ease-out focus:border-sophia-purple/60 focus:shadow-sm"
          />
          <div className="flex items-center justify-between">
            <p className="text-sm text-sophia-text2 transition-all duration-300">
              {presenceDetail ?? t(getPresenceCopyKey(presenceStatus))}
            </p>
            <button
              type="button"
              onClick={handleSend}
              disabled={!value.trim() || isLocked}
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

