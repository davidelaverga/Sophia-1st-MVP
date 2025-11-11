import { createServerClient, type CookieOptions } from '@supabase/ssr'
import type { Session, SupabaseClient } from '@supabase/supabase-js'
import { cookies } from 'next/headers'
import { NextRequest, NextResponse } from 'next/server'

export async function GET(request: NextRequest) {
  const requestUrl = new URL(request.url)
  const code = requestUrl.searchParams.get('code')
  const error = requestUrl.searchParams.get('error')
    
  let session: Session;
  let supabase: SupabaseClient<any, any, any>;
  
  // CRITICAL FIX: Use correct Vercel origin instead of potentially wrong requestUrl.origin
  const origin = process.env.NEXT_PUBLIC_SITE_URL || requestUrl.origin

  console.log('🔄 Auth callback received:', { 
    code: !!code, 
    error, 
    origin,
    requestOrigin: requestUrl.origin,
    env: process.env.NODE_ENV 
  })

  if (error) {
    console.error('❌ OAuth error from Discord:', error)
    return NextResponse.redirect(`${origin}/?error=oauth_error&details=${error}`)
  }

  if (code) {
    const cookieStore = cookies()
    supabase = createServerClient(
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

    try {
      console.log('🔄 Exchanging code for session...')
      const { data, error: exchangeError } = await supabase.auth.exchangeCodeForSession(code)
      
      if (exchangeError) {
        console.error('❌ Error exchanging code:', exchangeError)
        return NextResponse.redirect(`${origin}/?error=exchange_failed&details=${exchangeError.message}`)
      }
      
      console.log('✅ Session exchange successful:', !!data.session)

      session = data.session;
    } catch (error) {
      console.error('❌ Unexpected error during exchange:', error)
      return NextResponse.redirect(`${origin}/?error=auth_failed&details=${error.message}`)
    }
  } else {
    console.log('❌ No authorization code received')
    return NextResponse.redirect(`${origin}/?error=no_code`)
  }

  const user = session.user;
  if (user?.id) {
    try {
      const metadata = user.user_metadata || {}
      const discordId =
        metadata.provider_id ||
        metadata.sub ||
        metadata.provider_token ||
        metadata.user_id ||
        null

      const payload = {
        id: user.id,
        email: user.email || `${user.id}@placeholder.sophia`,
        discord_id: discordId ? String(discordId) : null,
      }

      const { error: upsertError } = await supabase
        .from('users')
        .upsert(payload, { onConflict: 'id' })

      if (upsertError) {
        console.error('❌ Failed to upsert user during auth callback:', upsertError)
      } else {
        console.log('✅ Ensured user row exists for', user.id)
      }
    } catch (userSyncError) {
      console.error('❌ Unexpected error ensuring user row:', userSyncError)
    }
  }

  console.log('✅ Redirecting to home page')
  return NextResponse.redirect(`${origin}/`)
}
