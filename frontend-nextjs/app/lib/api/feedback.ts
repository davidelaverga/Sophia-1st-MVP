"use client"

export type FeedbackPayload = {
  turnId: string
  helpful: boolean
  tag?: "clarity" | "empathy" | "grounding" | "confusing" | "slow"
}

export const postFeedback = async ({ turnId, helpful, tag }: FeedbackPayload): Promise<void> => {
  const response = await fetch("/api/conversation/feedback", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      turn_id: turnId,
      helpful,
      tag,
    }),
  })

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}))
    const message = (payload as { error?: string }).error ?? response.statusText
    throw new Error(message)
  }
}


