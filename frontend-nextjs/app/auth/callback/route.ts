import { createServerClient, type CookieOptions } from '@supabase/ssr'
import { cookies } from 'next/headers'
import { NextRequest, NextResponse } from 'next/server'

export async function GET(request: NextRequest) {
  const requestUrl = new URL(request.url)
  const code = requestUrl.searchParams.get('code')
  const error = requestUrl.searchParams.get('error')
  
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
    
    try {
      console.log('🔄 Exchanging code for session...')
      const { data, error: exchangeError } = await supabase.auth.exchangeCodeForSession(code)
      
      if (exchangeError) {
        console.error('❌ Error exchanging code:', exchangeError)
        return NextResponse.redirect(`${origin}/?error=exchange_failed&details=${exchangeError.message}`)
      }
      
      console.log('✅ Session exchange successful:', !!data.session)
    } catch (error) {
      console.error('❌ Unexpected error during exchange:', error)
      return NextResponse.redirect(`${origin}/?error=auth_failed&details=${error.message}`)
    }
  } else {
    console.log('❌ No authorization code received')
    return NextResponse.redirect(`${origin}/?error=no_code`)
  }

  console.log('✅ Redirecting to home page')
  return NextResponse.redirect(`${origin}/`)
}
