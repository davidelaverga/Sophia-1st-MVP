"use client"

import { Fragment, useEffect, useRef, useState } from "react"
import type { KeyboardEventHandler, RefObject, UIEvent } from "react"
import { Send, Loader2, Volume2 } from "lucide-react"
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
    <div className="flex h-full flex-col justify-between gap-6 rounded-2xl bg-sophia-bubble p-6 text-sophia-text">
      <div>
        <p className="text-sm font-medium uppercase tracking-wide text-sophia-text2">
          {copy.home.hero.statusIcon} {copy.home.hero.status}
        </p>
        <h2 className="mt-2 text-2xl font-semibold text-sophia-text">{copy.home.hero.heading}</h2>
        <p className="mt-2 text-base text-sophia-text2">{copy.home.hero.body}</p>
      </div>
      <div>
        <p className="text-sm font-medium text-sophia-text2">{t("chat.quickStartTitle")}</p>
        <div className="mt-3 flex flex-wrap gap-2">
          {copy.chat.quickPrompts.map((prompt) => (
            <button
              key={prompt.id}
              type="button"
              className="rounded-2xl border border-sophia-text/10 bg-white/70 px-4 py-2 text-sm font-medium text-sophia-text transition hover:border-sophia-purple/40 hover:text-sophia-purple"
              onClick={() => onPromptSelect(prompt.label)}
            >
              <span className="mr-2" aria-hidden>
                {prompt.emoji}
              </span>
              {prompt.label}
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

  const handleAudio = async () => {
    if (!message.audioUrl) return
    try {
      const audio = new Audio(message.audioUrl)
      await audio.play()
    } catch (error) {
      console.warn("[conversation] Audio playback failed", error)
    }
  }

  return (
    <div className={`flex w-full gap-3 ${alignment}`} role="article" aria-label={isUser ? "You said" : "Sophia replied"}>
      {!isUser && (
        <div className="mt-1 flex h-10 w-10 items-center justify-center rounded-2xl bg-sophia-purple text-sm font-semibold text-white">
          {copy.brand.initial}
        </div>
      )}
      <div className="max-w-[80%] space-y-2">
        <div className={`rounded-3xl px-4 py-3 text-sm leading-relaxed shadow-soft/30 ${bubbleClasses}`}>
          {message.content || <span className="text-sophia-text2">{t("chat.loading")}</span>}
        </div>
        {!isUser && message.turnId && <FeedbackStrip turnId={message.turnId} />}
        {message.audioUrl && (
          <button
            type="button"
            onClick={handleAudio}
            className="flex items-center gap-2 text-xs font-medium text-sophia-purple"
          >
            <Volume2 className="h-4 w-4" />
            {t("chat.audioButton")}
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
  return (
    <div className="flex items-center gap-2 text-sm text-sophia-text2">
      <Loader2 className="h-4 w-4 animate-spin text-sophia-purple" />
      {t("chat.loading")}
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
      <div className="rounded-2xl bg-white p-4 shadow-soft">
        <div className="flex flex-col gap-3">
          <textarea
            ref={textareaRef}
            rows={3}
            value={value}
            placeholder={t("chat.placeholder")}
            disabled={isLocked}
            onChange={(event) => setValue(event.target.value)}
            onKeyDown={onKeyDown}
            className="w-full resize-none rounded-2xl border border-sophia-text/10 bg-sophia-user px-4 py-3 text-base text-sophia-text outline-none transition focus:border-sophia-purple/60"
          />
          <div className="flex items-center justify-between">
            <p className="text-sm text-sophia-text2">
              {presenceDetail ?? t(getPresenceCopyKey(presenceStatus))}
            </p>
            <button
              type="button"
              onClick={handleSend}
              disabled={!value.trim() || isLocked}
              className="inline-flex items-center gap-2 rounded-2xl bg-sophia-purple px-5 py-2 text-sm font-medium text-white transition disabled:opacity-60"
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

