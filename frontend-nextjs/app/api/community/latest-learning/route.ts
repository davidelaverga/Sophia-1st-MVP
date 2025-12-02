import { NextRequest, NextResponse } from "next/server"
import { cookies } from "next/headers"
import { createServerClient } from "@supabase/ssr"

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export async function GET(request: NextRequest) {
  try {
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

    const response = await fetch(`${BACKEND_URL}/api/community/latest-learning`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { "Authorization": `Bearer ${token}` } : {}),
      },
      cache: "no-store",
    })

    if (!response.ok) {
      // Return fallback data on error
      return NextResponse.json({
        title: "Today Sophia learned",
        insight: "The importance of meaningful conversations.",
        sophia_emotion: { label: "curious", confidence: 0.85 },
        reflection_id: null,
      })
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error("[community/latest-learning] Error:", error)
    // Return fallback on error
    return NextResponse.json({
      title: "Today Sophia learned",
      insight: "The importance of meaningful conversations.",
      sophia_emotion: { label: "curious", confidence: 0.85 },
      reflection_id: null,
    })
  }
}
