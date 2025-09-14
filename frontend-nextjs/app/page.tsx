'use client'

import Image from "next/image";
import LiveCall from "./components/LiveCall";
import { useState, useEffect } from 'react'
import { createBrowserClient } from '@supabase/ssr'
import { User, LogOut, Mic } from 'lucide-react'
import ChatInterface from './components/ChatInterface'
import VoiceRecorder from './components/VoiceRecorder'
import ConsentModal from './components/ConsentModal'

interface Message {
  id: string
  type: 'user' | 'sophia'
  content: string
  sender: 'user' | 'ai'
  timestamp: Date
  audioUrl?: string
  emotion?: any
  intent?: string
}

export default function Home() {
  const [user, setUser] = useState<any>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [hasConsent, setHasConsent] = useState(false)
  const [showConsent, setShowConsent] = useState(false)
  const supabase = createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  )

  useEffect(() => {
    const getUser = async () => {
      const { data: { user } } = await supabase.auth.getUser()
      setUser(user)
      
      if (user) {
        checkConsent(user.id)
      }
    }
    getUser()
  }, [])

  const checkConsent = async (userId: string) => {
    try {
      const response = await fetch('/api/consent/check', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ userId }),
      })
      
      if (!response.ok) {
        console.error('Consent check failed:', response.status, response.statusText)
        setShowConsent(true)
        return
      }
      
      const text = await response.text()
      if (!text) {
        console.error('Empty response from consent check')
        setShowConsent(true)
        return
      }
      
      const data = JSON.parse(text)
      setHasConsent(data.hasConsent)
      
      if (!data.hasConsent) {
        setShowConsent(true)
      }
    } catch (error) {
      console.error('Error checking consent:', error)
      setShowConsent(true)
    }
  }

  const handleConsentAccepted = () => {
    setHasConsent(true)
    setShowConsent(false)
  }

  const signOut = async () => {
    await supabase.auth.signOut()
    setUser(null)
    setMessages([])
    setHasConsent(false)
  }

  const signInWithDiscord = async () => {
    try {
      setIsLoading(true)
      console.log('🔐 Starting Discord sign-in...')
      const { data, error } = await supabase.auth.signInWithOAuth({
        provider: 'discord',
        options: {
          redirectTo: `${window.location.origin}/auth/callback`,
        }
      })

      if (error) {
        console.error('❌ Discord sign-in error:', error)
        alert(`Discord sign-in failed: ${error.message}`)
        return
      }

      // Some environments may not auto-redirect. Manually navigate if URL is returned.
      if (data?.url) {
        console.log('🔀 Redirecting to:', data.url)
        window.location.href = data.url
      } else {
        console.warn('⚠️ No redirect URL returned from signInWithOAuth')
      }
    } catch (e: any) {
      console.error('❌ Unexpected error during Discord sign-in:', e)
      alert(`Unexpected sign-in error: ${e?.message || e}`)
    } finally {
      setIsLoading(false)
    }
  }

  if (!user) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center">
        <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-8 shadow-2xl max-w-md w-full mx-4">
          <div className="text-center mb-8">
            <div className="w-20 h-20 bg-gradient-to-br from-purple-500 to-cyan-500 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <span className="text-3xl font-bold text-white">S</span>
            </div>
            <h1 className="text-3xl font-bold text-white mb-2">Sophia</h1>
            <p className="text-gray-300 text-lg">DeFi AI Assistant</p>
          </div>
          
          <button
            onClick={signInWithDiscord}
            disabled={isLoading}
            className="w-full bg-gradient-to-r from-indigo-600 to-indigo-700 hover:from-indigo-700 hover:to-indigo-800 disabled:opacity-60 disabled:cursor-not-allowed text-white font-semibold py-4 px-6 rounded-xl transition-all duration-300 flex items-center justify-center gap-3"
          >
            {isLoading ? 'Redirecting…' : 'Continue with Discord'}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      <header className="bg-white/5 backdrop-blur-xl border-b border-white/10">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-gradient-to-br from-purple-500 to-cyan-500 rounded-xl flex items-center justify-center">
                <span className="text-xl font-bold text-white">S</span>
              </div>
              <div>
                <h1 className="text-xl font-bold text-white">Sophia</h1>
                <p className="text-sm text-gray-300">DeFi AI Assistant</p>
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              <span className="text-sm text-gray-300">{user.user_metadata?.full_name || user.email}</span>
              <button
                onClick={signOut}
                className="p-2 text-gray-400 hover:text-white transition-colors"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {hasConsent ? (
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
            <div className="lg:col-span-1 space-y-6">
              <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-6">
                <h3 className="text-xl font-bold text-white mb-6">Quick Actions</h3>
                <div className="space-y-4">
                  <button className="w-full bg-gradient-to-r from-purple-500/20 to-purple-600/20 hover:from-purple-500/30 hover:to-purple-600/30 border border-purple-500/30 rounded-xl p-4 transition-all duration-300 text-left">
                    <div className="flex items-center gap-4">
                      <div className="w-12 h-12 bg-gradient-to-br from-purple-500 to-purple-600 rounded-xl flex items-center justify-center">
                        <span className="text-xl">🌾</span>
                      </div>
                      <div>
                        <p className="font-semibold text-white text-sm">Yield Farming</p>
                        <p className="text-gray-300 text-xs">Learn strategies</p>
                      </div>
                    </div>
                  </button>
                  
                  <button className="w-full bg-gradient-to-r from-green-500/20 to-emerald-600/20 hover:from-green-500/30 hover:to-emerald-600/30 border border-green-500/30 rounded-xl p-4 transition-all duration-300 text-left">
                    <div className="flex items-center gap-4">
                      <div className="w-12 h-12 bg-gradient-to-br from-green-500 to-emerald-600 rounded-xl flex items-center justify-center">
                        <span className="text-xl">🛡️</span>
                      </div>
                      <div>
                        <p className="font-semibold text-white text-sm">Risk Analysis</p>
                        <p className="text-gray-300 text-xs">Safety first</p>
                      </div>
                    </div>
                  </button>
                </div>
              </div>
              
              <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-6">
                <h3 className="text-xl font-bold text-white mb-6">AI Status</h3>
                <div className="space-y-4">
                  <div className="flex justify-between items-center">
                    <span className="text-gray-300 text-sm">Response Time</span>
                    <span className="bg-green-500/20 text-green-400 px-3 py-1 rounded-lg text-sm font-semibold">~2.3s</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-300 text-sm">Accuracy</span>
                    <span className="bg-blue-500/20 text-blue-400 px-3 py-1 rounded-lg text-sm font-semibold">98.7%</span>
                  </div>
                </div>
              </div>
            </div>
            
            <div className="lg:col-span-3 space-y-8">
              <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-8">
                <div className="flex items-center gap-6 mb-8">
                  <div className="w-24 h-24 bg-gradient-to-br from-purple-500 to-cyan-500 rounded-3xl flex items-center justify-center">
                    <span className="text-4xl font-bold text-white">S</span>
                  </div>
                  <div>
                    <h1 className="text-4xl font-bold text-white mb-2">Welcome to Sophia DeFi</h1>
                    <div className="flex items-center gap-3">
                      <div className="w-3 h-3 bg-green-400 rounded-full animate-pulse"></div>
                      <span className="text-xl text-green-400 font-semibold">✨ AI Ready</span>
                    </div>
                  </div>
                </div>
                
                <p className="text-gray-300 text-xl mb-8">
                  Your intelligent DeFi companion is ready to help you navigate decentralized finance.
                </p>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="bg-gradient-to-r from-purple-500/20 to-purple-600/20 border border-purple-500/30 rounded-xl p-6 cursor-pointer">
                    <h3 className="text-xl font-bold text-white mb-2">Yield Farming Guide</h3>
                    <p className="text-gray-300">Learn about maximizing DeFi returns safely</p>
                  </div>
                  
                  <div className="bg-gradient-to-r from-green-500/20 to-emerald-600/20 border border-green-500/30 rounded-xl p-6 cursor-pointer">
                    <h3 className="text-xl font-bold text-white mb-2">DeFi Safety Tips</h3>
                    <p className="text-gray-300">Essential security practices for beginners</p>
                  </div>
                </div>
              </div>
              
              {/* Live, phone-call style interface */}
              <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-6">
                <h3 className="text-xl font-bold text-white mb-4">Live Voice Call</h3>
                <p className="text-gray-300 mb-4">Talk to Sophia in real-time. Click Start Call and begin speaking. You’ll see partial transcripts and hear responses as they stream.</p>
                <LiveCall />
              </div>

              {/* Text chat remains available below */}
              <ChatInterface 
                messages={messages}
                setMessages={setMessages}
                isLoading={isLoading}
                setIsLoading={setIsLoading}
              />

              {/* Legacy upload-based voice recorder (hidden by default)
              <VoiceRecorder 
                onMessage={(message) => setMessages(prev => [...prev, message])}
                setIsLoading={setIsLoading}
              />
              */}
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center min-h-screen">
            <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-8 max-w-md mx-auto">
              <h3 className="text-2xl font-bold text-white mb-4 text-center">Consent Required</h3>
              <p className="text-gray-300 mb-6 text-center">
                Please accept our data processing consent to start using Sophia's voice features.
              </p>
              <button
                onClick={() => setShowConsent(true)}
                className="w-full bg-gradient-to-r from-purple-500 to-purple-600 hover:from-purple-600 hover:to-purple-700 text-white px-6 py-3 rounded-xl transition-all duration-300 font-semibold"
              >
                Review Consent
              </button>
            </div>
          </div>
        )}
      </main>

      {showConsent && (
        <ConsentModal
          onAccept={handleConsentAccepted}
          onClose={() => setShowConsent(false)}
        />
      )}
    </div>
  )
}
