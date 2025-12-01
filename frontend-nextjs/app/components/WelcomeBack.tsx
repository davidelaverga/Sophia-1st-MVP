"use client"

import { useState, useEffect, useCallback } from "react"
import { MessageSquare, Plus, Clock, ChevronRight, Trash2, History } from "lucide-react"
import { copy } from "../../copy"
import { useChatStore } from "../stores/chat-store"
import { useFocusModeStore } from "../stores/focus-mode-store"
import { 
  hasRestorableSession, 
  getCurrentSessionPreview, 
  getConversationSummaries,
  loadConversationFromHistory,
  deleteConversationFromHistory,
  archiveConversation,
  formatRelativeTime,
  type ConversationSummary 
} from "../lib/conversation-history"
import { loadSession, clearSession } from "../lib/session-persistence"

type WelcomeBackProps = {
  onContinue: () => void
  onStartNew: () => void
  onPromptSelect: (prompt: string) => void
}

export function WelcomeBack({ onContinue, onStartNew, onPromptSelect }: WelcomeBackProps) {
  const [showHistory, setShowHistory] = useState(false)
  const [currentSession, setCurrentSession] = useState<ConversationSummary | null>(null)
  const [history, setHistory] = useState<ConversationSummary[]>([])
  const [mounted, setMounted] = useState(false)
  
  const setMode = useFocusModeStore((state) => state.setMode)
  
  useEffect(() => {
    setMounted(true)
    setCurrentSession(getCurrentSessionPreview())
    setHistory(getConversationSummaries())
  }, [])
  
  const handleContinue = useCallback(() => {
    // Load the session - useSessionPersistence will handle restoration
    onContinue()
  }, [onContinue])
  
  const handleStartNew = useCallback(() => {
    // Archive current session before starting new
    const session = loadSession()
    if (session && session.messages.length >= 2) {
      archiveConversation(session.conversationId, session.messages, session.focusMode)
    }
    
    // Clear current session
    clearSession()
    useChatStore.setState({ 
      messages: [], 
      conversationId: undefined,
      lastError: undefined 
    })
    
    // Refresh history
    setHistory(getConversationSummaries())
    setCurrentSession(null)
    
    onStartNew()
  }, [onStartNew])
  
  const handleLoadConversation = useCallback((conversationId: string) => {
    const archived = loadConversationFromHistory(conversationId)
    if (!archived) return
    
    // Archive current session first
    const currentSessionData = loadSession()
    if (currentSessionData && currentSessionData.messages.length >= 2) {
      archiveConversation(
        currentSessionData.conversationId, 
        currentSessionData.messages, 
        currentSessionData.focusMode
      )
    }
    
    // Load archived conversation
    useChatStore.setState({
      messages: archived.messages,
      conversationId: archived.id,
      lastError: undefined,
    })
    
    if (archived.focusMode) {
      const restoredMode = archived.focusMode === "voice" ? "text" : archived.focusMode
      setMode(restoredMode)
    }
    
    setShowHistory(false)
    onContinue()
  }, [onContinue, setMode])
  
  const handleDeleteConversation = useCallback((e: React.MouseEvent, conversationId: string) => {
    e.stopPropagation()
    deleteConversationFromHistory(conversationId)
    setHistory(getConversationSummaries())
  }, [])
  
  if (!mounted) return null
  
  // Show history panel
  if (showHistory) {
    return (
      <div className="flex h-full flex-col rounded-2xl bg-sophia-bubble p-6 text-sophia-text animate-in fade-in duration-300">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <History className="w-5 h-5 text-sophia-purple" />
            <h2 className="text-xl font-semibold">Conversation History</h2>
          </div>
          <button
            onClick={() => setShowHistory(false)}
            className="px-3 py-1.5 text-sm text-sophia-text2 hover:text-sophia-text transition-colors"
          >
            Back
          </button>
        </div>
        
        {/* History list */}
        <div className="flex-1 overflow-y-auto space-y-2 scrollbar-thin">
          {history.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-sophia-text2">
              <MessageSquare className="w-12 h-12 mb-4 opacity-30" />
              <p className="text-center">No saved conversations yet.</p>
              <p className="text-sm text-center mt-1 opacity-70">
                Your conversations will appear here.
              </p>
            </div>
          ) : (
            history.map((conv) => (
              <button
                key={conv.id}
                onClick={() => handleLoadConversation(conv.id)}
                className="group w-full flex items-start gap-3 p-4 rounded-xl bg-sophia-surface/50 hover:bg-sophia-surface border border-transparent hover:border-sophia-purple/20 transition-all duration-200 text-left"
              >
                <MessageSquare className="w-5 h-5 mt-0.5 text-sophia-purple/60 group-hover:text-sophia-purple transition-colors flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <h3 className="font-medium text-sophia-text truncate">
                      {conv.title}
                    </h3>
                    <button
                      onClick={(e) => handleDeleteConversation(e, conv.id)}
                      className="opacity-0 group-hover:opacity-100 p-1 hover:bg-sophia-error/10 rounded transition-all"
                      title="Delete conversation"
                    >
                      <Trash2 className="w-4 h-4 text-sophia-error/70 hover:text-sophia-error" />
                    </button>
                  </div>
                  <p className="text-sm text-sophia-text2 truncate mt-1">
                    {conv.preview}
                  </p>
                  <div className="flex items-center gap-2 mt-2 text-xs text-sophia-text2/70">
                    <Clock className="w-3 h-3" />
                    <span>{formatRelativeTime(conv.updatedAt)}</span>
                    <span className="opacity-50">•</span>
                    <span>{conv.messageCount} messages</span>
                  </div>
                </div>
                <ChevronRight className="w-4 h-4 text-sophia-text2/50 group-hover:text-sophia-purple transition-colors flex-shrink-0 mt-1" />
              </button>
            ))
          )}
        </div>
        
        {/* Start new button */}
        <div className="mt-4 pt-4 border-t border-sophia-purple/10">
          <button
            onClick={handleStartNew}
            className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-sophia-purple/10 hover:bg-sophia-purple/20 text-sophia-purple font-medium transition-colors"
          >
            <Plus className="w-5 h-5" />
            Start New Conversation
          </button>
        </div>
      </div>
    )
  }
  
  // Welcome Back view with current session
  if (currentSession) {
    return (
      <div className="flex h-full flex-col justify-between gap-6 rounded-2xl bg-sophia-bubble p-8 text-sophia-text animate-in fade-in duration-300">
        {/* Header */}
        <div className="space-y-4">
          <p className="inline-flex items-center gap-2 text-sm font-medium uppercase tracking-wide text-sophia-purple animate-breathe">
            <span className="text-base">💜</span>
            <span>Welcome back</span>
          </p>
          
          <div className="space-y-3">
            <h2 className="text-3xl font-semibold text-sophia-text sm:text-4xl">
              Continue our conversation?
            </h2>
            <p className="text-base leading-relaxed text-sophia-text2 sm:text-lg">
              You have an unfinished conversation from {formatRelativeTime(currentSession.updatedAt).toLowerCase()}.
            </p>
          </div>
        </div>
        
        {/* Current session card */}
        <div 
          onClick={handleContinue}
          className="group cursor-pointer p-5 rounded-xl bg-sophia-surface/60 border border-sophia-purple/20 hover:border-sophia-purple/40 hover:bg-sophia-surface transition-all duration-200"
        >
          <div className="flex items-start gap-4">
            <div className="p-3 rounded-xl bg-sophia-purple/10 text-sophia-purple">
              <MessageSquare className="w-6 h-6" />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="font-semibold text-sophia-text text-lg truncate group-hover:text-sophia-purple transition-colors">
                {currentSession.title}
              </h3>
              <p className="text-sm text-sophia-text2 mt-1 line-clamp-2">
                {currentSession.preview}
              </p>
              <div className="flex items-center gap-2 mt-3 text-xs text-sophia-text2/70">
                <Clock className="w-3.5 h-3.5" />
                <span>{formatRelativeTime(currentSession.updatedAt)}</span>
                <span className="opacity-50">•</span>
                <span>{currentSession.messageCount} messages</span>
              </div>
            </div>
            <ChevronRight className="w-5 h-5 text-sophia-text2/50 group-hover:text-sophia-purple transition-colors mt-1" />
          </div>
        </div>
        
        {/* Action buttons */}
        <div className="space-y-3">
          <button
            onClick={handleContinue}
            className="w-full py-4 rounded-xl bg-sophia-purple text-white font-semibold text-lg shadow-lg shadow-sophia-purple/20 hover:shadow-sophia-purple/30 hover:brightness-110 transition-all duration-200 active:scale-[0.98]"
          >
            Continue Conversation
          </button>
          
          <div className="flex gap-3">
            <button
              onClick={handleStartNew}
              className="flex-1 py-3 rounded-xl border border-sophia-purple/30 text-sophia-purple font-medium hover:bg-sophia-purple/10 transition-colors"
            >
              <Plus className="w-4 h-4 inline-block mr-2" />
              Start New
            </button>
            
            {history.length > 0 && (
              <button
                onClick={() => setShowHistory(true)}
                className="flex-1 py-3 rounded-xl border border-sophia-purple/30 text-sophia-purple font-medium hover:bg-sophia-purple/10 transition-colors"
              >
                <History className="w-4 h-4 inline-block mr-2" />
                View History
              </button>
            )}
          </div>
        </div>
      </div>
    )
  }
  
  // No current session - show regular empty state with history access
  return (
    <div className="flex h-full flex-col justify-between gap-8 rounded-2xl bg-sophia-bubble p-8 text-sophia-text">
      <div className="space-y-4">
        {/* Presence indicator with breathing animation */}
        <p className="inline-flex items-center gap-2 text-sm font-medium uppercase tracking-wide text-sophia-purple animate-breathe">
          <span className="text-base">{copy.home.hero.statusIcon}</span>
          <span>{copy.home.hero.status}</span>
        </p>
        
        {/* Welcome message */}
        <div className="space-y-3">
          <h2 className="text-3xl font-semibold text-sophia-text sm:text-4xl">
            {copy.home.hero.heading}
          </h2>
          <p className="text-base leading-relaxed text-sophia-text2 sm:text-lg">
            {copy.home.hero.body}
          </p>
        </div>
      </div>
      
      {/* Quick prompts */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <p className="text-sm font-medium text-sophia-text2">Try asking...</p>
          {history.length > 0 && (
            <button
              onClick={() => setShowHistory(true)}
              className="flex items-center gap-1.5 text-sm text-sophia-purple hover:text-sophia-purple/80 transition-colors"
            >
              <History className="w-4 h-4" />
              View History
            </button>
          )}
        </div>
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
