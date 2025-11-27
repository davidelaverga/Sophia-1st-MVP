'use client'

import { SessionContextProvider, useSessionContext } from '@supabase/auth-helpers-react'
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs'
import type { SupabaseClient, User } from '@supabase/supabase-js'

// FORCE use of CORRECT URL and KEY (temporary fix for demo)
// TODO: Fix env variable reading issue
const supabaseUrl = "https://qtyqgvdkbhjfmnfkxyvm.supabase.co"
// Force use of the correct anon key directly
const supabaseKey = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF0eXFndmRrYmhqZm1uZmt4eXZtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM0Nzc3MzUsImV4cCI6MjA3OTA1MzczNX0.XqfLoS-qOd01AOnO7gAY4mRPFPGa1JbRvNMmxpudJPI"
const supabaseClient = createClientComponentClient({
  supabaseUrl: supabaseUrl,
  supabaseKey: supabaseKey,
})

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <SessionContextProvider supabaseClient={supabaseClient}>
      {children}
    </SessionContextProvider>
  )
}

type SupabaseHookResult = {
  supabase: SupabaseClient
  user: User | null
  accessToken: string | null
  loading: boolean
}

<<<<<<< HEAD
const Context = createContext<SupabaseContext | undefined>(undefined)

export function Providers({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [accessToken, setAccessToken] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  
  // Debug environment variables
  console.log('🔧 Supabase Config:', {
    url: process.env.NEXT_PUBLIC_SUPABASE_URL,
    anonKey: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY?.substring(0, 20) + '...'
  })
  
  const supabase = createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  )

  useEffect(() => {
    const getUser = async () => {
      console.log('🔍 Checking existing session...')
      try {
        const { data: { session }, error } = await supabase.auth.getSession()
        console.log('Session data:', session)
        console.log('Session error:', error)
        setUser(session?.user ?? null)
        setAccessToken(session?.access_token ?? null)
      } catch (err) {
        console.error('❌ Error getting session:', err)
      }
      setLoading(false)
    }

    getUser()

    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      console.log('🔄 Auth state changed:', event, session?.user?.email)
      setUser(session?.user ?? null)
      setAccessToken(session?.access_token ?? null)
      setLoading(false)
    })

    return () => subscription.unsubscribe()
  }, [supabase])

  return (
    <Context.Provider value={{ supabase, user, accessToken, loading }}>
      {children}
    </Context.Provider>
  )
}

export const useSupabase = () => {
  const context = useContext(Context)
  if (context === undefined) {
    throw new Error('useSupabase must be used inside Providers')
=======
export const useSupabase = (): SupabaseHookResult => {
  const { supabaseClient: client, session, isLoading } = useSessionContext()
  return {
    supabase: client,
    user: session?.user ?? null,
    loading: isLoading,
>>>>>>> 0c5b809ac824140402012b804879965c93f57ab1
  }
}
