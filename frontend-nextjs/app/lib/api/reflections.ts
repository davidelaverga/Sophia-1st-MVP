"use client"

export type ReflectionAction = "save" | "share_discord"

export type CreateReflectionPayload = {
  conversationId: string
  chunkId: string
  action: ReflectionAction
}

export const createReflection = async ({ conversationId, chunkId, action }: CreateReflectionPayload): Promise<void> => {
  const response = await fetch("/api/reflections/create", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      conversation_id: conversationId,
      chunk_id: chunkId,
      action,
    }),
  })

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}))
    const message = (payload as { error?: string }).error ?? response.statusText
    throw new Error(message || "Unable to save reflection.")
  }
}





