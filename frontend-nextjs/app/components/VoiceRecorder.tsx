'use client'

import { useState, useRef, useCallback } from 'react'
import { Mic, MicOff, Square } from 'lucide-react'

interface VoiceRecorderProps {
  onMessage: (message: any) => void
  setIsLoading: (loading: boolean) => void
}

export default function VoiceRecorder({ onMessage, setIsLoading }: VoiceRecorderProps) {
  const [isRecording, setIsRecording] = useState(false)
  const [recordingTime, setRecordingTime] = useState(0)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioChunksRef = useRef<Blob[]>([])
  const timerRef = useRef<NodeJS.Timeout | null>(null)
  const streamRef = useRef<MediaStream | null>(null)

  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true
        }
      })

      streamRef.current = stream
      audioChunksRef.current = []

      // Try WAV first, fallback to WebM
      let options = { mimeType: 'audio/wav' }
      if (!MediaRecorder.isTypeSupported('audio/wav')) {
        options = { mimeType: 'audio/webm;codecs=opus' }
      }

      const mediaRecorder = new MediaRecorder(stream, options)
      mediaRecorderRef.current = mediaRecorder

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data)
        }
      }

      mediaRecorder.onstop = async () => {
        await processRecording()
      }

      // Start without a timeslice to ensure we always receive a final
      // dataavailable event with the full recording on stop. Using a very
      // short timeslice can cause empty chunks if the user stops quickly.
      mediaRecorder.start()
      setIsRecording(true)
      setRecordingTime(0)

      // Start timer
      timerRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1)
      }, 1000)

    } catch (error) {
      console.error('Failed to start recording:', error)
      alert('Microphone access denied or not available')
    }
  }, [])

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
      
      if (timerRef.current) {
        clearInterval(timerRef.current)
        timerRef.current = null
      }

      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop())
        streamRef.current = null
      }
    }
  }, [isRecording])

  const processRecording = async () => {
    if (audioChunksRef.current.length === 0) {
      alert('No audio recorded')
      return
    }

    // Accept short recordings as long as we received data

    setIsLoading(true)

    try {
      const mimeType = mediaRecorderRef.current?.mimeType || 'audio/webm;codecs=opus'
      const audioBlob = new Blob(audioChunksRef.current, { type: mimeType })

      if (audioBlob.size === 0) {
        alert('No audio captured. Please try again and allow microphone access.')
        return
      }
      
      const formData = new FormData()
      let fileName = 'recording.wav'
      if (mimeType.includes('webm')) {
        fileName = 'recording.webm'
      }
      
      formData.append('file', audioBlob, fileName)

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'}/defi-chat/stream`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${process.env.NEXT_PUBLIC_API_KEY || 'dev-key'}`
        },
        body: formData
      })

      if (!response.ok || !response.body) {
        const detail = !response.ok ? `${response.status} ${response.statusText}` : 'No response body'
        throw new Error(`Streaming request failed: ${detail}`)
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let buffer = ''
      let sophiaMessageId = Date.now().toString() + '_sophia'
      let transcriptAdded = false
      let accumulated = ''
      let audioUrl: string | null = null

      const pushSophiaMessage = (content: string) => {
        onMessage({
          id: sophiaMessageId,
          type: 'sophia',
          content,
          sender: 'ai',
          timestamp: new Date()
        })
      }

      const updateSophiaMessage = (content: string, extra?: { audioUrl?: string; emotion?: any }) => {
        onMessage({
          id: sophiaMessageId,
          type: 'sophia',
          content,
          sender: 'ai',
          audioUrl: extra?.audioUrl,
          emotion: extra?.emotion,
          timestamp: new Date()
        })
      }

      const processLine = (line: string) => {
        if (!line.trim()) return
        // Expect SSE lines like: "event: token" or "data: ..."
        // We'll collect per-event until a blank line separates events
      }

      // Simple SSE parser state
      let currentEvent: string | null = null
      let currentData: string[] = []

      const handleEvent = (event: string, data: string) => {
        try {
          if (event === 'transcript') {
            const payload = JSON.parse(data)
            // Add user message first
            if (!transcriptAdded) {
              onMessage({
                id: Date.now().toString() + '_user',
                type: 'user',
                content: payload.transcript,
                sender: 'user',
                emotion: payload.user_emotion,
                timestamp: new Date()
              })
              transcriptAdded = true
              // Initialize Sophia message as empty to start streaming
              pushSophiaMessage('')
            }
          } else if (event === 'token') {
            const chunk = data
            accumulated += chunk
            updateSophiaMessage(accumulated)
          } else if (event === 'reply_done') {
            const payload = JSON.parse(data)
            accumulated = payload.reply || accumulated
            updateSophiaMessage(accumulated)
          } else if (event === 'audio_url') {
            const payload = JSON.parse(data)
            audioUrl = payload.audio_url
            const mock = !!payload.mock_audio
            updateSophiaMessage(accumulated, { audioUrl: payload.audio_url, emotion: payload.sophia_emotion })
            if (audioUrl && !mock && /^https?:\/\//.test(audioUrl)) {
              setTimeout(() => playAudio(audioUrl!), 300)
            }
          } else if (event === 'error') {
            console.error('SSE error:', data)
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
          // flush remaining
          flushIfEventComplete()
          break
        }
        buffer += decoder.decode(value, { stream: true })
        let idx: number
        while ((idx = buffer.indexOf('\n')) !== -1) {
          const line = buffer.slice(0, idx)
          buffer = buffer.slice(idx + 1)
          if (line.startsWith('event:')) {
            // Starting new event; flush previous
            flushIfEventComplete()
            currentEvent = line.slice('event:'.length).trim()
          } else if (line.startsWith('data:')) {
            currentData.push(line.slice('data:'.length).trim())
          } else if (line.trim() === '') {
            // separator between events
            flushIfEventComplete()
          } else {
            // continuation of data or ignore
            currentData.push(line)
          }
        }
      }

    } catch (error) {
      console.error('Voice processing failed:', error)
      alert(`Voice message failed: ${error.message}`)
    } finally {
      setIsLoading(false)
      setRecordingTime(0)
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

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  return (
    <div className="bg-gradient-to-br from-dark-card via-gray-800/50 to-dark-card border border-dark-border rounded-2xl p-8 relative overflow-hidden">
      {/* Background decoration */}
      <div className="absolute top-0 right-0 w-24 h-24 bg-gradient-to-br from-purple-500/5 to-transparent rounded-full blur-2xl"></div>
      <div className="absolute bottom-0 left-0 w-20 h-20 bg-gradient-to-tr from-cyan-500/5 to-transparent rounded-full blur-2xl"></div>
      
      <div className="relative z-10">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-r from-purple-500 to-cyan-500 rounded-xl flex items-center justify-center">
              <Mic className="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 className="text-xl font-bold text-white">Voice Assistant</h3>
              <p className="text-sm text-gray-400">Speak naturally with Sophia</p>
            </div>
          </div>
          {isRecording && (
            <div className="flex items-center gap-3 px-4 py-2 bg-red-500/20 border border-red-500/30 rounded-xl">
              <div className="w-3 h-3 bg-red-400 rounded-full animate-pulse shadow-lg shadow-red-400/50"></div>
              <span className="text-sm font-mono text-red-300 font-bold">{formatTime(recordingTime)}</span>
              <span className="text-xs text-red-400">RECORDING</span>
            </div>
          )}
        </div>

        <div className="flex flex-col items-center justify-center py-8">
          {!isRecording ? (
            <div className="text-center">
              <button
                onClick={startRecording}
                className="group relative w-24 h-24 bg-gradient-to-br from-purple-500 via-blue-500 to-cyan-500 rounded-3xl flex items-center justify-center hover:scale-110 transition-all duration-300 shadow-2xl hover:shadow-purple-500/30 mb-6"
              >
                <Mic className="w-10 h-10 text-white group-hover:scale-110 transition-transform" />
                <div className="absolute inset-0 rounded-3xl bg-white/10 scale-0 group-hover:scale-110 transition-transform duration-500"></div>
                <div className="absolute -inset-2 rounded-3xl bg-gradient-to-r from-purple-500/20 to-cyan-500/20 scale-0 group-hover:scale-100 transition-transform duration-700 blur-lg"></div>
              </button>
              
              <div className="space-y-2">
                <p className="text-lg font-semibold text-white">Ready to Listen</p>
                <p className="text-sm text-gray-400 max-w-md mx-auto leading-relaxed">
                  Click the microphone and ask about DeFi strategies, yield farming, staking, or any blockchain topics
                </p>
              </div>
              
              {/* Feature highlights */}
              <div className="grid grid-cols-3 gap-4 mt-8 max-w-md mx-auto">
                <div className="text-center p-3 bg-gradient-to-br from-purple-500/10 to-blue-500/10 border border-purple-500/20 rounded-xl">
                  <div className="text-lg mb-1">🎯</div>
                  <p className="text-xs text-gray-300 font-medium">Smart Analysis</p>
                </div>
                <div className="text-center p-3 bg-gradient-to-br from-blue-500/10 to-cyan-500/10 border border-blue-500/20 rounded-xl">
                  <div className="text-lg mb-1">⚡</div>
                  <p className="text-xs text-gray-300 font-medium">Real-time</p>
                </div>
                <div className="text-center p-3 bg-gradient-to-br from-cyan-500/10 to-green-500/10 border border-cyan-500/20 rounded-xl">
                  <div className="text-lg mb-1">🔊</div>
                  <p className="text-xs text-gray-300 font-medium">Voice Reply</p>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center">
              <button
                onClick={stopRecording}
                className="relative w-24 h-24 bg-gradient-to-br from-red-500 to-red-600 rounded-3xl flex items-center justify-center hover:scale-105 transition-all duration-200 shadow-2xl shadow-red-500/30 mb-6 animate-pulse"
              >
                <Square className="w-8 h-8 text-white fill-current" />
                <div className="absolute -inset-4 rounded-3xl border-2 border-red-400/50 animate-ping"></div>
              </button>
              
              <div className="space-y-2">
                <p className="text-lg font-semibold text-white">Listening...</p>
                <p className="text-sm text-gray-400">
                  Speak clearly about your DeFi question
                </p>
              </div>
              
              {/* Audio visualization */}
              <div className="flex items-center justify-center gap-1 mt-6">
                {[...Array(5)].map((_, i) => (
                  <div
                    key={i}
                    className="w-1 bg-gradient-to-t from-purple-500 to-cyan-500 rounded-full animate-pulse"
                    style={{
                      height: `${Math.random() * 20 + 10}px`,
                      animationDelay: `${i * 0.1}s`,
                      animationDuration: '0.8s'
                    }}
                  ></div>
                ))}
              </div>
            </div>
          )}
        </div>
        
        {/* Tips section */}
        <div className="mt-8 p-4 bg-gradient-to-r from-gray-800/50 to-gray-900/50 border border-gray-700/50 rounded-xl">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 bg-gradient-to-r from-yellow-500 to-orange-500 rounded-lg flex items-center justify-center flex-shrink-0">
              <span className="text-sm">💡</span>
            </div>
            <div>
              <p className="text-sm font-semibold text-white mb-1">Pro Tips</p>
              <ul className="text-xs text-gray-400 space-y-1">
                <li>• Speak clearly and at normal pace for best transcription</li>
                <li>• Ask specific questions about DeFi protocols, risks, or strategies</li>
                <li>• Wait for the audio response to complete before asking follow-ups</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
