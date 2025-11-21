'use client'

import { SessionContextProvider, useSessionContext } from '@supabase/auth-helpers-react'
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs'
import type { SupabaseClient, User } from '@supabase/supabase-js'

const supabaseClient = createClientComponentClient()

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
