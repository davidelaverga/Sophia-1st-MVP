'use client'

import { useState, useRef, useEffect } from 'react'
import { Send, Loader2 } from 'lucide-react'
import EmotionDisplay from './EmotionDisplay'

interface Message {
  id: string
  type: 'user' | 'sophia'
  content: string
  sender: 'user' | 'ai'
  emotion?: any
  audioUrl?: string
  intent?: string
  timestamp: Date
}

interface ChatInterfaceProps {
  messages: Message[]
  setMessages: (messages: Message[] | ((prev: Message[]) => Message[])) => void
  isLoading: boolean
  setIsLoading: (loading: boolean) => void
}

export default function ChatInterface({ messages, setMessages, isLoading, setIsLoading }: ChatInterfaceProps) {
  const [inputText, setInputText] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const sendTextMessage = async () => {
    if (!inputText.trim() || isLoading) return

    const userMessage: Message = {
      id: generateSessionId(),
      type: 'user',
      content: inputText.trim(),
      sender: 'user',
      timestamp: new Date()
    }

    setMessages([...messages, userMessage])
    setInputText('')
    setIsLoading(true)

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'}/text-chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${process.env.NEXT_PUBLIC_API_KEY || 'dev-key'}`
        },
        body: JSON.stringify({
          message: userMessage.content,
          session_id: generateSessionId()
        })
      })

      if (!response.ok || !response.body) {
        const detail = !response.ok ? `${response.status} ${response.statusText}` : 'No response body'
        throw new Error(`Streaming request failed: ${detail}`)
      }

      // Initialize a Sophia message for incremental updates
      const sophiaId = generateSessionId()
      setMessages(prev => [...prev, {
        id: sophiaId,
        type: 'sophia',
        content: '',
        sender: 'ai',
        timestamp: new Date()
      }])

      const reader = response.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let buffer = ''
      let accumulated = ''

      const updateSophia = (content: string, extra?: { audioUrl?: string; emotion?: any }) => {
        setMessages(prev => prev.map(m => m.id === sophiaId ? ({ ...m, content, audioUrl: extra?.audioUrl, emotion: extra?.emotion }) : m))
      }

      let currentEvent: string | null = null
      let currentData: string[] = []

      const handleEvent = (event: string, data: string) => {
        try {
          if (event === 'token') {
            const chunk = data
            accumulated += chunk
            updateSophia(accumulated)
          } else if (event === 'reply_done') {
            const payload = JSON.parse(data)
            accumulated = payload.reply || accumulated
            updateSophia(accumulated)
          } else if (event === 'audio_url') {
            const payload = JSON.parse(data)
            updateSophia(accumulated, { audioUrl: payload.audio_url, emotion: payload.sophia_emotion })
            const mock = !!payload.mock_audio
            if (payload.audio_url && !mock && /^https?:\/\//.test(payload.audio_url)) {
              setTimeout(() => playAudio(payload.audio_url), 300)
            }
          }
        } catch (err) {
          console.warn('Failed to handle SSE event', event, err)
        }
      }

      const flushIfEventComplete = () => {
        if (currentEvent) {
          const data = currentData.join('\n')
          handleEvent(currentEvent, data)
          currentEvent = null
          currentData = []
        }
      }

      while (true) {
        const { done, value } = await reader.read()
        if (done) {
          flushIfEventComplete()
          break
        }
        buffer += decoder.decode(value, { stream: true })
        let idx: number
        while ((idx = buffer.indexOf('\n')) !== -1) {
          const line = buffer.slice(0, idx)
          buffer = buffer.slice(idx + 1)
          if (line.startsWith('event:')) {
            flushIfEventComplete()
            currentEvent = line.slice('event:'.length).trim()
          } else if (line.startsWith('data:')) {
            currentData.push(line.slice('data:'.length).trim())
          } else if (line.trim() === '') {
            flushIfEventComplete()
          } else {
            currentData.push(line)
          }
        }
      }

    } catch (error) {
      console.error('Text message failed:', error)
      const errorMessage: Message = {
        id: generateSessionId(),
        type: 'sophia',
        content: `Sorry, I encountered an error: ${error.message}`,
        sender: 'ai',
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const playAudio = async (audioUrl: string) => {
    try {
      const audio = new Audio(audioUrl)
      await audio.play()
    } catch (error) {
      console.error('Audio playback failed:', error)
    }
  }

  const generateSessionId = () => {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
      const r = Math.random() * 16 | 0
      const v = c == 'x' ? r : (r & 0x3 | 0x8)
      return v.toString(16)
    })
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendTextMessage()
    }
  }

  const handleQuickMessage = (message: string) => {
    setInputText(message)
    inputRef.current?.focus()
  }

  return (
    <div className="space-y-4">
      {/* Messages */}
      <div className="bg-gradient-to-br from-dark-card via-gray-800/30 to-dark-card border border-dark-border rounded-2xl p-6 min-h-[500px] max-h-[700px] overflow-y-auto custom-scrollbar relative">
        {/* Background decoration */}
        <div className="absolute top-0 right-0 w-20 h-20 bg-gradient-to-br from-purple-500/5 to-transparent rounded-full blur-xl"></div>
        <div className="absolute bottom-0 left-0 w-16 h-16 bg-gradient-to-tr from-blue-500/5 to-transparent rounded-full blur-xl"></div>
        
        <div className="space-y-6 relative z-10">
          {messages.map((message, index) => (
            <div
              key={index}
              className={`flex gap-4 ${message.type === 'user' ? 'justify-end' : 'justify-start'} group`}
            >
              {message.type === 'sophia' && (
                <div className="w-12 h-12 bg-gradient-to-br from-purple-500 via-blue-500 to-cyan-500 rounded-2xl flex items-center justify-center flex-shrink-0 shadow-lg group-hover:scale-105 transition-transform">
                  <span className="text-lg font-bold text-white">S</span>
                </div>
              )}
              
              <div className={`max-w-[75%] ${message.type === 'user' ? 'order-first' : ''}`}>
                <div
                  className={`rounded-2xl p-5 shadow-lg backdrop-blur-sm border ${
                    message.type === 'user'
                      ? 'bg-gradient-to-r from-purple-500 to-blue-500 text-white ml-auto border-purple-400/30'
                      : 'bg-gradient-to-br from-gray-800/80 to-gray-900/80 text-gray-100 border-gray-700/50'
                  } group-hover:shadow-xl transition-all duration-300`}
                >
                  <p className="text-sm leading-relaxed font-medium">{message.content}</p>
                  
                  {message.audioUrl && (
                    <button
                      onClick={() => playAudio(message.audioUrl!)}
                      className="mt-3 px-4 py-2 bg-white/10 hover:bg-white/20 rounded-xl text-xs transition-all flex items-center gap-2 font-medium border border-white/10 hover:border-white/20"
                    >
                      <span className="text-sm">🔊</span>
                      Play Audio Response
                    </button>
                  )}
                </div>
                
                <div className="flex items-center gap-3 mt-3 px-2">
                  <span className="text-xs text-gray-400 font-medium">
                    {message.timestamp.toLocaleTimeString()}
                  </span>
                  
                  {message.emotion && (
                    <div className="flex items-center gap-1">
                      <EmotionDisplay emotion={message.emotion} size="sm" />
                    </div>
                  )}
                  
                  {message.intent && (
                    <span className="px-3 py-1 bg-gradient-to-r from-cyan-500/20 to-blue-500/20 text-cyan-300 text-xs rounded-full border border-cyan-500/30 font-medium">
                      {message.intent.replace('_', ' ')}
                    </span>
                  )}
                </div>
              </div>
              
              {message.type === 'user' && (
                <div className="w-12 h-12 bg-gradient-to-br from-gray-600 to-gray-700 rounded-2xl flex items-center justify-center flex-shrink-0 shadow-lg group-hover:scale-105 transition-transform border border-gray-500/30">
                  <span className="text-lg">👤</span>
                </div>
              )}
            </div>
          ))}
          
          {isLoading && (
            <div className="flex gap-4 justify-start group">
              <div className="w-12 h-12 bg-gradient-to-br from-purple-500 via-blue-500 to-cyan-500 rounded-2xl flex items-center justify-center flex-shrink-0 shadow-lg animate-pulse">
                <span className="text-lg font-bold text-white">S</span>
              </div>
              <div className="bg-gradient-to-br from-gray-800/80 to-gray-900/80 rounded-2xl p-5 shadow-lg backdrop-blur-sm border border-gray-700/50">
                <div className="flex items-center gap-3">
                  <Loader2 className="w-5 h-5 animate-spin text-purple-400" />
                  <span className="text-sm text-gray-300 font-medium">Sophia is analyzing your question...</span>
                  <div className="flex gap-1">
                    <div className="w-1 h-1 bg-purple-400 rounded-full animate-bounce"></div>
                    <div className="w-1 h-1 bg-blue-400 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                    <div className="w-1 h-1 bg-cyan-400 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
        <div ref={messagesEndRef} />
      </div>

      {/* Enhanced Input */}
      <div className="bg-gradient-to-br from-dark-card via-gray-800/50 to-dark-card border border-dark-border rounded-2xl p-6 relative overflow-hidden">
        {/* Background decoration */}
        <div className="absolute top-0 right-0 w-16 h-16 bg-gradient-to-br from-purple-500/5 to-transparent rounded-full blur-xl"></div>
        
        <div className="relative z-10">
          <div className="flex gap-4">
            <div className="flex-1 relative">
              <input
                ref={inputRef}
                type="text"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask Sophia about DeFi strategies, risks, or market insights..."
                className="w-full bg-gradient-to-r from-gray-800/80 to-gray-900/80 border border-gray-600/50 rounded-xl px-6 py-4 text-white placeholder-gray-400 focus:outline-none focus:border-purple-400/50 focus:ring-2 focus:ring-purple-400/20 transition-all backdrop-blur-sm shadow-lg"
                disabled={isLoading}
              />
              {inputText && (
                <div className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-gray-400 bg-gray-800/80 px-2 py-1 rounded">
                  {inputText.length}/500
                </div>
              )}
            </div>
            <button
              onClick={sendTextMessage}
              disabled={!inputText.trim() || isLoading}
              className="px-6 py-4 bg-gradient-to-r from-purple-500 to-blue-500 hover:from-purple-600 hover:to-blue-600 disabled:from-gray-600 disabled:to-gray-700 disabled:cursor-not-allowed text-white rounded-xl transition-all flex items-center gap-3 shadow-lg hover:shadow-xl hover:scale-105 font-medium"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span className="hidden sm:inline">Sending...</span>
                </>
              ) : (
                <>
                  <Send className="w-5 h-5" />
                  <span className="hidden sm:inline">Send</span>
                </>
              )}
            </button>
          </div>
        </div>
        
        {messages.length === 0 && (
          <div className="mt-6 pt-4 border-t border-gray-700/50">
            <p className="text-xs text-gray-400 mb-3 font-medium">💡 Quick start suggestions:</p>
            <div className="flex flex-wrap gap-3">
              <button
                onClick={() => handleQuickMessage('What is yield farming?')}
                className="px-4 py-2 bg-gradient-to-r from-purple-500/20 to-blue-500/20 text-purple-300 rounded-xl text-sm hover:from-purple-500/30 hover:to-blue-500/30 transition-all border border-purple-500/30 hover:border-purple-400/50 font-medium"
              >
                🌾 What is yield farming?
              </button>
              <button
                onClick={() => handleQuickMessage('How do I start with DeFi safely?')}
                className="px-4 py-2 bg-gradient-to-r from-green-500/20 to-emerald-500/20 text-green-300 rounded-xl text-sm hover:from-green-500/30 hover:to-emerald-500/30 transition-all border border-green-500/30 hover:border-green-400/50 font-medium"
              >
                🛡️ How do I start with DeFi safely?
              </button>
              <button
                onClick={() => handleQuickMessage('What are current DeFi trends?')}
                className="px-4 py-2 bg-gradient-to-r from-blue-500/20 to-cyan-500/20 text-blue-300 rounded-xl text-sm hover:from-blue-500/30 hover:to-cyan-500/30 transition-all border border-blue-500/30 hover:border-blue-400/50 font-medium"
              >
                📈 What are current DeFi trends?
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
