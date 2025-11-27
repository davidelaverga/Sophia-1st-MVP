import { NextRequest, NextResponse } from 'next/server'
import { createServerClient } from '@supabase/ssr'
import { cookies } from 'next/headers'

export async function GET(request: NextRequest) {
  try {
    const cookieStore = cookies()
    const supabase = createServerClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL || "https://qtyqgvdkbhjfmnfkxyvm.supabase.co",
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF0eXFndmRrYmhqZm1uZmt4eXZtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM0Nzc3MzUsImV4cCI6MjA3OTA1MzczNX0.XqfLoS-qOd01AOnO7gAY4mRPFPGa1JbRvNMmxpudJPI",
      {
        cookies: {
          get(name: string) {
            return cookieStore.get(name)?.value
          },
          set(name: string, value: string, options: any) {
            cookieStore.set({ name, value, ...options })
          },
          remove(name: string, options: any) {
            cookieStore.set({ name, value: '', ...options })
          },
        },
      }
    )

    // Get authenticated user
    const { data: { user }, error: userError } = await supabase.auth.getUser()
    
    if (userError || !user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    // Query user_usage table
    console.log('[usage/api] Fetching usage for user:', user.id)
    const { data, error } = await supabase
      .from('user_usage')
      .select('*')
      .eq('user_id', user.id)
      .single()

    if (error) {
      if (error.code === 'PGRST116') {
        // No record found - return default values
        console.log('[usage/api] No usage record found, returning defaults')
        return NextResponse.json({
          voice_seconds_used: 0,
          text_seconds_used: 0,
          reflections_count: 0,
        })
      }
      console.error('[usage/api] Error fetching usage:', error)
      return NextResponse.json({ error: error.message }, { status: 500 })
    }

    console.log('[usage/api] Usage data:', {
      voice: data.voice_seconds_used || 0,
      text: data.text_seconds_used || 0,
      reflections: data.reflections_count || 0,
    })

    return NextResponse.json({
      voice_seconds_used: data.voice_seconds_used || 0,
      text_seconds_used: data.text_seconds_used || 0,
      reflections_count: data.reflections_count || 0,
    })
  } catch (err: any) {
    console.error('[usage] Error in usage check:', err)
    return NextResponse.json({ error: err.message || 'Internal server error' }, { status: 500 })
  }
}

