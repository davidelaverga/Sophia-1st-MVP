import { NextRequest, NextResponse } from 'next/server'
import { createServerClient, type CookieOptions } from '@supabase/ssr'
import { cookies } from 'next/headers'
import { createHash } from 'crypto'

export async function POST(request: NextRequest) {
  console.log('📝 Consent accept request received')
  
  try {
    // Verify environment variables are set
    if (!process.env.NEXT_PUBLIC_SUPABASE_URL) {
      console.error('❌ NEXT_PUBLIC_SUPABASE_URL is not set')
      return NextResponse.json({ error: 'Server configuration error' }, { status: 500 })
    }
    if (!process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY) {
      console.error('❌ NEXT_PUBLIC_SUPABASE_ANON_KEY is not set')
      return NextResponse.json({ error: 'Server configuration error' }, { status: 500 })
    }
    if (!process.env.SUPABASE_SERVICE_ROLE_KEY) {
      console.error('❌ SUPABASE_SERVICE_ROLE_KEY is not set')
      return NextResponse.json({ error: 'Server configuration error' }, { status: 500 })
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

    // Get current user session
    console.log('🔍 Fetching user session...')
    const { data: { session }, error: sessionError } = await supabase.auth.getSession()
    
    if (sessionError) {
      console.error('❌ Session error:', sessionError)
      return NextResponse.json({ error: 'Unauthorized - session error' }, { status: 401 })
    }
    
    if (!session?.user) {
      console.error('❌ No user session found')
      return NextResponse.json({ error: 'Unauthorized - no session' }, { status: 401 })
    }

    console.log('✅ User session found:', session.user.id)

    const body = await request.json()
    const { userId, timestamp } = body

    // Get user's Discord ID from auth metadata
    const discordId = session.user.user_metadata?.provider_id || session.user.user_metadata?.sub

    if (!discordId) {
      console.error('❌ Discord ID not found in user metadata')
      console.log('User metadata:', JSON.stringify(session.user.user_metadata))
      return NextResponse.json({ error: 'Discord ID not found' }, { status: 404 })
    }

    console.log('✅ Discord ID found:', discordId)

    // Get client IP
    const forwarded = request.headers.get('x-forwarded-for')
    const ip = forwarded ? forwarded.split(',')[0] : request.headers.get('x-real-ip') || 'unknown'
    console.log('📍 Client IP:', ip)

    // Convert ISO timestamp to Unix timestamp (bigint)
    const unixTimestamp = Math.floor(new Date(timestamp).getTime() / 1000)

    // Create consent hash
    const consentData = `${discordId}:${timestamp}:${ip}`
    const consentHash = createHash('sha256').update(consentData).digest('hex')
    console.log('🔐 Consent hash generated:', consentHash.substring(0, 16) + '...')

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

    // Check if consent already exists
    console.log('🔍 Checking for existing consent...')
    const { data: existingConsent, error: checkError } = await serviceSupabase
      .from('user_consents')
      .select('discord_id')
      .eq('discord_id', discordId)
      .single()

    if (checkError && checkError.code !== 'PGRST116') {
      // PGRST116 = not found, which is expected for new users
      console.error('❌ Error checking existing consent:', checkError)
    }

    if (existingConsent) {
      console.log('✅ Consent already exists for user')
      return NextResponse.json({ 
        success: true,
        message: 'Consent already exists'
      })
    }

    // Store new consent record
    console.log('💾 Inserting new consent record...')
    const consentRecord = {
      discord_id: discordId,
      consent_hash: consentHash,
      ip_address: ip,
      timestamp: unixTimestamp,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    }
    console.log('📄 Consent record:', JSON.stringify(consentRecord, null, 2))

    const { data: insertedData, error: insertError } = await serviceSupabase
      .from('user_consents')
      .insert(consentRecord)
      .select()

    if (insertError) {
      console.error('❌ Database insert error:', insertError)
      console.error('Error code:', insertError.code)
      console.error('Error message:', insertError.message)
      console.error('Error details:', insertError.details)
      console.error('Error hint:', insertError.hint)
      
      // Handle duplicate key error gracefully
      if (insertError.code === '23505') {
        console.log('⚠️ Duplicate key error - consent already exists')
        return NextResponse.json({ 
          success: true,
          message: 'Consent already exists'
        })
      }
      
      return NextResponse.json({ 
        error: 'Failed to store consent',
        details: insertError.message 
      }, { status: 500 })
    }

    console.log('✅ Consent recorded successfully!')
    console.log('Inserted data:', insertedData)

    return NextResponse.json({ 
      success: true,
      message: 'Consent recorded successfully'
    })

  } catch (error) {
    console.error('Consent accept error:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
