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
  loading: boolean
}

export const useSupabase = (): SupabaseHookResult => {
  const { supabaseClient: client, session, isLoading } = useSessionContext()
  return {
    supabase: client,
    user: session?.user ?? null,
    loading: isLoading,
  }
}
