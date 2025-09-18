import { NextRequest, NextResponse } from 'next/server'
import { createServerClient, type CookieOptions } from '@supabase/ssr'
import { cookies } from 'next/headers'
import { createHash } from 'crypto'

export async function POST(request: NextRequest) {
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

    const body = await request.json()
    const { userId, timestamp } = body

    // Get user's Discord ID from auth metadata
    const discordId = session.user.user_metadata?.provider_id || session.user.user_metadata?.sub

    if (!discordId) {
      return NextResponse.json({ error: 'Discord ID not found' }, { status: 404 })
    }

    // Get client IP
    const forwarded = request.headers.get('x-forwarded-for')
    const ip = forwarded ? forwarded.split(',')[0] : request.headers.get('x-real-ip') || 'unknown'

    // Convert ISO timestamp to Unix timestamp (bigint)
    const unixTimestamp = Math.floor(new Date(timestamp).getTime() / 1000)

    // Create consent hash
    const consentData = `${discordId}:${timestamp}:${ip}`
    const consentHash = createHash('sha256').update(consentData).digest('hex')

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

    // Check if consent already exists
    const { data: existingConsent } = await serviceSupabase
      .from('user_consents')
      .select('discord_id')
      .eq('discord_id', discordId)
      .single()

    if (existingConsent) {
      // User already has consent, just return success
      return NextResponse.json({ 
        success: true,
        message: 'Consent already exists'
      })
    }

    // Store new consent record
    const { error } = await serviceSupabase
      .from('user_consents')
      .insert({
        discord_id: discordId,
        consent_hash: consentHash,
        ip_address: ip,
        timestamp: unixTimestamp,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      })

    if (error) {
      // Handle duplicate key error gracefully
      if (error.code === '23505') {
        return NextResponse.json({ 
          success: true,
          message: 'Consent already exists'
        })
      }
      console.error('Consent storage error:', error)
      return NextResponse.json({ error: 'Failed to store consent' }, { status: 500 })
    }

    return NextResponse.json({ 
      success: true,
      message: 'Consent recorded successfully'
    })

  } catch (error) {
    console.error('Consent accept error:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
