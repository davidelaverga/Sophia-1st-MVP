import { NextRequest, NextResponse } from 'next/server'
import { createServerClient, type CookieOptions } from '@supabase/ssr'
import { cookies } from 'next/headers'

async function handleConsentCheck(request: NextRequest) {
  console.log('🔍 Consent check request received')
  
  try {
    // Verify environment variables
    if (!process.env.NEXT_PUBLIC_SUPABASE_URL || !process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || !process.env.SUPABASE_SERVICE_ROLE_KEY) {
      console.error('❌ Missing Supabase environment variables')
      return NextResponse.json({ hasConsent: false, error: 'Server configuration error' }, { status: 500 })
    }

    console.log('✅ Environment variables verified')
    console.log('📍 Supabase URL:', process.env.NEXT_PUBLIC_SUPABASE_URL)

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

    // Get current user (server-side method)
    // Note: Using getUser() instead of getSession() for server-side validation
    console.log('🔍 Fetching authenticated user...')
    const { data: { user }, error: userError } = await supabase.auth.getUser()
    
    if (userError) {
      console.error('❌ User authentication error:', userError)
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }
    
    if (!user) {
      console.error('❌ No authenticated user found')
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    console.log('✅ Authenticated user found:', user.id)

    // Get user's Discord ID from auth metadata
    const discordId = user.user_metadata?.provider_id || user.user_metadata?.sub

    if (!discordId) {
      console.warn('⚠️ Discord ID not found, returning hasConsent: false')
      return NextResponse.json({ hasConsent: false })
    }

    console.log('✅ Discord ID found:', discordId)
    console.log('📋 Discord ID type:', typeof discordId)

    // Ensure discord_id is always a string
    const discordIdString = String(discordId)
    console.log('✅ Discord ID converted to string:', discordIdString)

    // Create service role client for database operations
    console.log('🔑 Creating service role client...')
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
    console.log('🔍 Checking consent status in database...')
    console.log('🔍 Querying with discord_id:', discordIdString)
    const { data: consent, error: consentError } = await serviceSupabase
      .from('user_consents')
      .select('*')
      .eq('discord_id', discordIdString)
      .single()

    if (consentError) {
      if (consentError.code === 'PGRST116') {
        // Not found - user has no consent record
        console.log('ℹ️ No consent record found for user')
        return NextResponse.json({ 
          hasConsent: false,
          consentDate: null
        })
      }
      if (consentError.code === 'PGRST205') {
        console.warn('⚠️ user_consents table missing; treating consent as granted for this environment')
        return NextResponse.json({
          hasConsent: true,
          consentDate: null,
          message: 'Consent table missing; skipping enforcement'
        })
      }
      console.error('❌ Error checking consent:', consentError)
      return NextResponse.json({ 
        hasConsent: false, 
        error: consentError.message 
      }, { status: 500 })
    }

    console.log('✅ Consent record found:', !!consent)

    return NextResponse.json({ 
      hasConsent: !!consent,
      consentDate: consent?.created_at || null
    })

  } catch (error) {
    console.error('❌ Consent check error:', error)
    return NextResponse.json({ 
      hasConsent: false,
      error: 'Internal server error' 
    }, { status: 500 })
  }
}

export async function GET(request: NextRequest) {
  return handleConsentCheck(request)
}

export async function POST(request: NextRequest) {
  return handleConsentCheck(request)
}
