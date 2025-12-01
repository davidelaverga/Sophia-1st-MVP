'use client'

import { createContext, useContext, useState, useEffect } from 'react'
import { SessionContextProvider, useSessionContext } from '@supabase/auth-helpers-react'
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs'
import type { SupabaseClient, User } from '@supabase/supabase-js'

// Use environment variables for Supabase configuration
// These MUST be set in .env.local for the app to work
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || ''
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''

// Only create client if we have the required env vars (avoid build-time errors)
const supabaseClient = supabaseUrl && supabaseKey 
  ? createClientComponentClient({
      supabaseUrl,
      supabaseKey,
    })
  : null

// Context for when Supabase is not available
const NoSupabaseContext = createContext<boolean>(false)

export function Providers({ children }: { children: React.ReactNode }) {
  // During build or if env vars missing, render children without Supabase context
  if (!supabaseClient) {
    console.warn('Supabase client not initialized - missing environment variables')
    return (
      <NoSupabaseContext.Provider value={true}>
        {children}
      </NoSupabaseContext.Provider>
    )
  }
  
  return (
    <NoSupabaseContext.Provider value={false}>
      <SessionContextProvider supabaseClient={supabaseClient}>
        {children}
      </SessionContextProvider>
    </NoSupabaseContext.Provider>
  )
}

type SupabaseHookResult = {
  supabase: SupabaseClient
  user: User | null
  loading: boolean
  accessToken: string | null
}

// Create a mock supabase client for when env vars are missing
const createMockClient = (): SupabaseClient => {
  return {
    auth: {
      getSession: async () => ({ data: { session: null }, error: null }),
      signOut: async () => ({ error: null }),
      signInWithOAuth: async () => ({ data: { url: null, provider: '' as any }, error: null }),
      onAuthStateChange: () => ({ data: { subscription: { unsubscribe: () => {} } } }),
    },
  } as unknown as SupabaseClient
}

export const useSupabase = (): SupabaseHookResult => {
  const noSupabase = useContext(NoSupabaseContext)
  
  // If no Supabase context, return mock values
  if (noSupabase || !supabaseClient) {
    return {
      supabase: createMockClient(),
      user: null,
      loading: false,
      accessToken: null,
    }
  }
  
  // eslint-disable-next-line react-hooks/rules-of-hooks
  const { supabaseClient: client, session, isLoading } = useSessionContext()
  return {
    supabase: client,
    user: session?.user ?? null,
    loading: isLoading,
    accessToken: session?.access_token ?? null,
  }
}
