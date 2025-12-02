import { NextRequest, NextResponse } from "next/server"
import { cookies } from "next/headers"
import { createServerClient } from "@supabase/ssr"

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export async function GET(request: NextRequest) {
  try {
    // Get user_id from query params
    const { searchParams } = new URL(request.url)
    const userId = searchParams.get("user_id")

    if (!userId) {
      return NextResponse.json(
        { error: "user_id is required" },
        { status: 400 }
      )
    }

    // Get auth token from Supabase session
    const cookieStore = cookies()
    const supabase = createServerClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
      {
        cookies: {
          get(name: string) {
            return cookieStore.get(name)?.value
          },
        },
      }
    )
    
    const { data: { session } } = await supabase.auth.getSession()
    const token = session?.access_token

    const response = await fetch(
      `${BACKEND_URL}/api/community/user-impact?user_id=${encodeURIComponent(userId)}`,
      {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { "Authorization": `Bearer ${token}` } : {}),
        },
        cache: "no-store",
      }
    )

    if (!response.ok) {
      // Return empty stats on error
      return NextResponse.json({
        user_id: userId,
        session_count: 0,
        reflections_created: 0,
        reflections_shared: 0,
        last_session_at: null,
      })
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error("[community/user-impact] Error:", error)
    return NextResponse.json({
      user_id: "unknown",
      session_count: 0,
      reflections_created: 0,
      reflections_shared: 0,
      last_session_at: null,
    })
  }
}
