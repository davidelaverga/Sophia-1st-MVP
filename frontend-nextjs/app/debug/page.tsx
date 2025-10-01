'use client'

import { useEffect, useState } from 'react'
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs'

export default function DebugPage() {
  const [debugInfo, setDebugInfo] = useState<any>({})
  const [logs, setLogs] = useState<string[]>([])
  const supabase = createClientComponentClient()

  const addLog = (message: string) => {
    console.log(message)
    setLogs(prev => [...prev, `${new Date().toISOString()}: ${message}`])
  }

  useEffect(() => {
    const collectDebugInfo = async () => {
      addLog('🔍 Starting comprehensive debug analysis...')
      
      // Get current URL info
      const currentUrl = window.location.href
      const origin = window.location.origin
      const hostname = window.location.hostname
      
      addLog(`📍 Current URL: ${currentUrl}`)
      addLog(`🌐 Origin: ${origin}`)
      
      // Get environment variables
      const apiUrl = process.env.NEXT_PUBLIC_API_URL
      const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
      const apiKey = process.env.NEXT_PUBLIC_API_KEY
      
      addLog(`🔗 API URL from env: ${apiUrl}`)
      addLog(`🗄️ Supabase URL from env: ${supabaseUrl}`)
      
      // Check if we're somehow running on the wrong domain
      const isOnVercel = hostname.includes('vercel.app')
      const isOnRender = hostname.includes('onrender.com')
      
      addLog(`✅ Running on Vercel: ${isOnVercel}`)
      addLog(`❌ Running on Render: ${isOnRender}`)
      
      // Get user session
      const { data: session } = await supabase.auth.getSession()
      addLog(`👤 Has session: ${!!session?.session}`)
      
      // Test API connectivity
      let apiTest = 'Not tested'
      try {
        addLog(`🔄 Testing API connectivity to: ${apiUrl}`)
        const response = await fetch(`${apiUrl}/health`)
        const data = await response.json()
        apiTest = `Success: ${JSON.stringify(data)}`
        addLog(`✅ API test successful`)
      } catch (error) {
        apiTest = `Error: ${error.message}`
        addLog(`❌ API test failed: ${error.message}`)
      }

      setDebugInfo({
        currentUrl,
        origin,
        hostname,
        isOnVercel,
        isOnRender,
        apiUrl,
        supabaseUrl,
        apiKey: apiKey ? `${apiKey.substring(0, 10)}...` : 'Not set',
        hasSession: !!session?.session,
        sessionUser: session?.session?.user?.email || 'No user',
        apiTest,
        redirectUrl: `${origin}/auth/callback`,
        nodeEnv: process.env.NODE_ENV,
        timestamp: new Date().toISOString()
      })
      
      addLog('🏁 Debug analysis complete')
    }

    collectDebugInfo()
  }, [])

  const testOAuth = async () => {
    addLog('🔄 Testing OAuth flow...')
    try {
      const { data, error } = await supabase.auth.signInWithOAuth({
        provider: 'discord',
        options: {
          redirectTo: `${window.location.origin}/auth/callback`,
        }
      })
      
      if (error) {
        addLog(`❌ OAuth test failed: ${error.message}`)
      } else {
        addLog(`✅ OAuth initiated successfully`)
      }
    } catch (error) {
      addLog(`❌ OAuth test exception: ${error.message}`)
    }
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white p-8">
      <h1 className="text-3xl font-bold mb-8">🔍 OAuth Issue Investigation</h1>
      
      <div className="bg-red-800 p-6 rounded-lg mb-8">
        <h2 className="text-xl font-semibold mb-4">🚨 CRITICAL: Check Supabase Site URL</h2>
        <p className="mb-4">The most likely cause of your issue is Supabase configuration:</p>
        <ol className="list-decimal list-inside space-y-2 text-sm">
          <li><strong>Go to:</strong> https://supabase.com/dashboard/project/qitsfiaphigmkzfdyejp/settings/api</li>
          <li><strong>Find "Site URL" setting</strong></li>
          <li><strong>Check if it shows:</strong> https://sophia-1st-mvp-xjml.onrender.com (WRONG!)</li>
          <li><strong>Change it to:</strong> https://sophia-1st-mvp-git-main-davidelavergas-projects.vercel.app</li>
          <li><strong>Save changes</strong></li>
        </ol>
        <div className="mt-4 p-4 bg-yellow-800 rounded">
          <strong>Why this matters:</strong> Supabase redirects users to the Site URL after OAuth, overriding our callback route redirects!
        </div>
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="bg-gray-800 p-6 rounded-lg">
          <h2 className="text-xl font-semibold mb-4">📊 System Information</h2>
          <pre className="text-sm overflow-auto max-h-96">
            {JSON.stringify(debugInfo, null, 2)}
          </pre>
        </div>

        <div className="bg-gray-800 p-6 rounded-lg">
          <h2 className="text-xl font-semibant mb-4">📝 Debug Logs</h2>
          <div className="text-sm max-h-96 overflow-auto bg-black p-4 rounded">
            {logs.map((log, index) => (
              <div key={index} className="mb-1 font-mono">{log}</div>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-4 flex space-x-4">
        <button 
          onClick={testOAuth}
          className="bg-green-600 px-4 py-2 rounded hover:bg-green-700"
        >
          🧪 Test OAuth Flow
        </button>
        <button 
          onClick={() => window.location.href = '/'}
          className="bg-purple-600 px-4 py-2 rounded hover:bg-purple-700"
        >
          ← Back to Main App
        </button>
      </div>
    </div>
  )
}