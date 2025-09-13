import { NextRequest, NextResponse } from 'next/server'
import { createServerClient, type CookieOptions } from '@supabase/ssr'
import { cookies } from 'next/headers'

async function handleConsentCheck(request: NextRequest) {
  try {
    const cookieStore = cookies()
    const supabase = createServerClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
      {
        cookies: {
          get(name: string) {
            return cookieStore.get(name)?.value
          },
          set(name: string, value: string, options: CookieOptions) {
            cookieStore.set({ name, value, ...options })
          },
          remove(name: string, options: CookieOptions) {
            cookieStore.set({ name, value: '', ...options })
          },
        },
      }
    )

    // Get current user session
    const { data: { session }, error: sessionError } = await supabase.auth.getSession()
    
    if (sessionError || !session?.user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    // Get user's Discord ID from auth metadata
    const discordId = session.user.user_metadata?.provider_id || session.user.user_metadata?.sub

    if (!discordId) {
      return NextResponse.json({ hasConsent: false })
    }

    // Create service role client for database operations
    const serviceSupabase = createServerClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.SUPABASE_SERVICE_ROLE_KEY!,
      {
        cookies: {
          get() { return undefined },
          set() {},
          remove() {},
        },
      }
    )

    // Check consent status
    const { data: consent } = await serviceSupabase
      .from('user_consents')
      .select('*')
      .eq('discord_id', discordId)
      .single()

    return NextResponse.json({ 
      hasConsent: !!consent,
      consentDate: consent?.created_at || null
    })

  } catch (error) {
    console.error('Consent check error:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}

export async function GET(request: NextRequest) {
  return handleConsentCheck(request)
}

export async function POST(request: NextRequest) {
  return handleConsentCheck(request)
}
