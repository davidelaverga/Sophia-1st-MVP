import { NextRequest, NextResponse } from "next/server"
import { cookies } from "next/headers"
import { createServerClient, type CookieOptions } from "@supabase/ssr"

const encoder = new TextEncoder()
const decoder = new TextDecoder()

type BackendEvent = "token" | "reply_done" | "audio_url" | "error"

type TextChatRequest = {
  message: string
  conversationId?: string
}

type ReplyDonePayload = {
  reply?: string
}

type AudioPayload = {
  audio_url?: string
  sophia_emotion?: unknown
  mock_audio?: boolean
}

const formatEvent = (event: string, data: unknown) => {
  const payload = typeof data === "string" ? data : JSON.stringify(data)
  return `event: ${event}\ndata: ${payload}\n\n`
}

const sendMetaEvent = (controller: ReadableStreamDefaultController, conversationId: string, status: string, detail?: string) => {
  try {
    // Check if controller is still open before enqueuing
    if (controller.desiredSize !== null) {
      controller.enqueue(
        encoder.encode(
          formatEvent("meta", {
            conversationId,
            presence: { status, detail },
          })
        )
      )
    }
  } catch (error) {
    // Silently ignore errors when stream is closed
    console.warn("[conversation] Stream already closed, skipping meta event:", status)
  }
}

export async function POST(request: NextRequest) {
  const apiBase = process.env.BACKEND_API_URL
  const apiKey = process.env.BACKEND_API_KEY

  if (!apiBase || !apiKey) {
    return NextResponse.json({ error: "Server configuration incomplete" }, { status: 500 })
  }

  // 💜 Get authenticated user for rate limiting (optional)
  let userId: string | undefined
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
            cookieStore.set({ name, value: "", ...options })
          },
        },
      }
    )

    const { data: { user } } = await supabase.auth.getUser()
    userId = user?.id
    console.log("[conversation] User ID for rate limiting:", userId)
  } catch (error) {
    // If auth fails, continue without user_id (no rate limiting)
    console.warn("[conversation] Failed to get user for rate limiting:", error)
  }

  let body: TextChatRequest
  try {
    body = await request.json()
  } catch (error) {
    return NextResponse.json({ error: "Invalid JSON payload" }, { status: 400 })
  }

  if (!body.message || typeof body.message !== "string") {
    return NextResponse.json({ error: "Missing message" }, { status: 400 })
  }

  // 💜 Use user_id from request body if provided (from client-side)
  // Fallback to server-side auth if not provided
  if (body.user_id) {
    userId = body.user_id
    console.log("[conversation] Using user_id from request body:", userId)
  } else if (!userId) {
    console.warn("[conversation] No user_id provided in request body and server-side auth failed")
  }

  const conversationId = body.conversationId || crypto.randomUUID()

  const backendResponse = await fetch(`${apiBase}/text-chat/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      message: body.message,
      session_id: conversationId,
      user_id: userId, // 💜 Pass user_id for rate limiting (optional)
    }),
  })

  if (!backendResponse.ok || !backendResponse.body) {
    const detail = `${backendResponse.status} ${backendResponse.statusText}`
    return NextResponse.json({ error: `Conversation stream failed: ${detail}` }, { status: backendResponse.status })
  }

  const stream = new ReadableStream({
    start(controller) {
      let buffer = ""
      let currentEvent: BackendEvent | null = null
      let currentData: string[] = []
      let finalReply = ""
      let doneSent = false
      let thinkingSent = false
      let lastAudio: AudioPayload | undefined

      const reader = backendResponse.body!.getReader()

      const queueEvent = (event: string, data: unknown) => {
        try {
          // Check if controller is still open before enqueuing
          if (controller.desiredSize !== null) {
            controller.enqueue(encoder.encode(formatEvent(event, data)))
          }
        } catch (error) {
          // Silently ignore errors when stream is closed
          console.warn("[conversation] Stream already closed, skipping event:", event)
        }
      }

      const dispatchDone = () => {
        if (doneSent) return
        queueEvent("done", {
          conversationId,
          message: finalReply.trim(),
          audioUrl: lastAudio?.audio_url,
          sophiaEmotion: lastAudio?.sophia_emotion,
          mockAudio: lastAudio?.mock_audio,
        })
        doneSent = true
        sendMetaEvent(controller, conversationId, "resting")
      }

      const handleEvent = (eventName: BackendEvent, payload: string) => {
        switch (eventName) {
          case "token": {
            if (!thinkingSent) {
              sendMetaEvent(controller, conversationId, "thinking")
              thinkingSent = true
            }
            finalReply += payload
            queueEvent("token", payload)
            break
          }
          case "reply_done": {
            try {
              const data = JSON.parse(payload) as ReplyDonePayload
              if (data.reply) {
                finalReply = data.reply
              }
            } catch (error) {
              console.warn("[conversation] Failed to parse reply_done payload", error)
            }
            sendMetaEvent(controller, conversationId, "reflecting")
            break
          }
          case "audio_url": {
            try {
              const data = JSON.parse(payload) as AudioPayload
              lastAudio = data
              queueEvent("meta", {
                conversationId,
                presence: { status: "speaking" },
                audio: data,
              })
            } catch (error) {
              console.warn("[conversation] Failed to parse audio payload", error)
            }
            dispatchDone()
            break
          }
          case "error": {
            queueEvent("error", payload)
            dispatchDone()
            break
          }
          default:
            break
        }
      }

      sendMetaEvent(controller, conversationId, "listening")

      const read = (): Promise<void> => {
        return reader.read().then(({ value, done }) => {
          if (done) {
            if (currentEvent) {
              handleEvent(currentEvent, currentData.join("\n"))
              currentEvent = null
              currentData = []
            }
            if (!doneSent) {
              dispatchDone()
            }
            controller.close()
            return
          }
          buffer += decoder.decode(value, { stream: true })
          let newlineIndex: number
          while ((newlineIndex = buffer.indexOf("\n")) !== -1) {
            const rawLine = buffer.slice(0, newlineIndex)
            buffer = buffer.slice(newlineIndex + 1)
            const line = rawLine.replace(/\r$/, "")
            if (line.startsWith("event:")) {
              if (currentEvent) {
                handleEvent(currentEvent, currentData.join("\n"))
                currentData = []
              }
              currentEvent = line.slice(6).trim() as BackendEvent
            } else if (line.startsWith("data:")) {
              currentData.push(line.slice(5).trim())
            } else if (line === "") {
              if (currentEvent) {
                handleEvent(currentEvent, currentData.join("\n"))
                currentEvent = null
                currentData = []
              }
            } else {
              currentData.push(line)
            }
          }
          return read()
        }).catch((error) => {
          console.error("[conversation] Stream read failed", error)
          queueEvent("error", { message: "Streaming interrupted" })
          dispatchDone()
          controller.close()
        })
      }

      read()
    },
    cancel() {
      backendResponse.body?.cancel().catch(() => {
        // ignore cancellation errors
      })
    },
  })

  return new NextResponse(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    },
  })
}
