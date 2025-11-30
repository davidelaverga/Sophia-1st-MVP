"use client"

import { useRef, useEffect } from "react"
import { Mic } from "lucide-react"
import { useChatStore } from "../stores/chat-store"
import type { ChatMessage } from "../stores/chat-store"

type VoiceTranscriptProps = {
  partialReply?: string
  finalReply?: string
}

export function VoiceTranscript({ partialReply, finalReply }: VoiceTranscriptProps) {
  // Use unified chat store for seamless context
  const allMessages = useChatStore((state) => state.messages)
  const scrollRef = useRef<HTMLDivElement>(null)
  
  // Filter to show only Sophia's messages (voice or text)
  const sophiaMessages = allMessages.filter((msg) => msg.role === "sophia")

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [sophiaMessages.length, partialReply])

  // Only show partialReply as "active" (streaming)
  // finalReply is already saved in history, so don't show it separately
  const activeReply = partialReply

  // Don't show anything if no history and no current reply
  if (sophiaMessages.length === 0 && !activeReply) {
    return null
  }

  return (
    <div className="rounded-2xl bg-sophia-card p-4 shadow-sm border border-sophia-card-border animate-fadeIn">
      <div className="flex items-center gap-2 mb-3">
        <div className="h-2 w-2 rounded-full bg-sophia-purple animate-breathe" />
        <p className="text-xs font-medium text-sophia-purple uppercase tracking-wide">
          Conversation
        </p>
      </div>

      <div
        ref={scrollRef}
        className="space-y-3 max-h-[200px] overflow-y-auto pr-2 scrollbar-thin scrollbar-thumb-sophia-purple/20 scrollbar-track-transparent"
      >
        {/* Unified conversation history - all Sophia's messages */}
        {sophiaMessages.map((message: ChatMessage) => (
          <div
            key={message.id}
            className={`rounded-xl backdrop-blur-sm px-4 py-3 text-sm text-sophia-text shadow-sm border animate-fadeIn ${
              message.source === "voice"
                ? "bg-sophia-bubble/80 border-sophia-purple/20"
                : "bg-sophia-bubble/60 border-sophia-purple/10"
            }`}
          >
            <div className="flex items-start gap-2">
              {message.source === "voice" && (
                <Mic className="h-3.5 w-3.5 text-sophia-purple mt-0.5 flex-shrink-0" />
              )}
              <p className="flex-1">{message.content}</p>
            </div>
          </div>
        ))}

        {/* Current streaming reply (only while streaming, not final) */}
        {activeReply && (
          <div className="rounded-xl bg-sophia-bubble/80 backdrop-blur-sm px-4 py-3 text-sm text-sophia-text shadow-sm border border-sophia-purple/20 animate-fadeIn">
            <div className="flex items-start gap-2">
              <Mic className="h-3.5 w-3.5 text-sophia-purple mt-0.5 flex-shrink-0" />
              <p className="flex-1">{activeReply}</p>
              <span className="inline-block ml-1 w-1.5 h-4 bg-sophia-purple animate-pulse" />
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

