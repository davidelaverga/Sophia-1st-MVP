'use client'

import { useEffect, useState } from 'react'
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs'

export default function DebugPage() {
  const [debugInfo, setDebugInfo] = useState<any>({})
  const supabase = createClientComponentClient()

  useEffect(() => {
    const collectDebugInfo = async () => {
      // Get current URL info
      const currentUrl = window.location.href
      const origin = window.location.origin
      
      // Get environment variables
      const apiUrl = process.env.NEXT_PUBLIC_API_URL
      const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
      
      // Get user session
      const { data: session } = await supabase.auth.getSession()
      
      // Test API connectivity
      let apiTest = 'Not tested'
      try {
        const response = await fetch(`${apiUrl}/health`)
        const data = await response.json()
        apiTest = `Success: ${JSON.stringify(data)}`
      } catch (error) {
        apiTest = `Error: ${error.message}`
      }

      setDebugInfo({
        currentUrl,
        origin,
        apiUrl,
        supabaseUrl,
        hasSession: !!session?.session,
        sessionUser: session?.session?.user?.email || 'No user',
        apiTest,
        redirectUrl: `${origin}/auth/callback`,
        timestamp: new Date().toISOString()
      })
    }

    collectDebugInfo()
  }, [])

  return (
    <div className="min-h-screen bg-gray-900 text-white p-8">
      <h1 className="text-3xl font-bold mb-8">🔍 Sophia Debug Information</h1>
      
      <div className="bg-gray-800 p-6 rounded-lg">
        <h2 className="text-xl font-semibold mb-4">Environment & Configuration</h2>
        <pre className="text-sm overflow-auto">
          {JSON.stringify(debugInfo, null, 2)}
        </pre>
      </div>

      <div className="mt-8 bg-blue-800 p-4 rounded">
        <h3 className="font-bold mb-2">🎯 Expected Values:</h3>
        <ul className="text-sm space-y-1">
          <li><strong>apiUrl:</strong> https://sophia-1st-mvp-xjml.onrender.com</li>
          <li><strong>currentUrl:</strong> Should start with https://sophia-1st-mvp-git-main-davidelavergas-projects.vercel.app</li>
          <li><strong>apiTest:</strong> Should show success with backend JSON</li>
          <li><strong>hasSession:</strong> Should be true if logged in</li>
        </ul>
      </div>

      <div className="mt-4">
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