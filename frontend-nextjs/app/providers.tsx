'use client'

import { SessionContextProvider, useSessionContext } from '@supabase/auth-helpers-react'
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs'
import type { SupabaseClient, User } from '@supabase/supabase-js'

// Use environment variables for Supabase configuration
// These MUST be set in .env.local for the app to work
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

if (!supabaseUrl || !supabaseKey) {
  throw new Error(
    'Missing Supabase environment variables. Please set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY in .env.local'
  )
}

const supabaseClient = createClientComponentClient({
  supabaseUrl,
  supabaseKey,
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
