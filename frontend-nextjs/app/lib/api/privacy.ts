"use client"

const usePrivacyMock = process.env.NEXT_PUBLIC_MOCK_PRIVACY === "true"

export type ConsentStatusResponse = {
  consent: boolean
  consent_ts?: string
}

const withJson = async <T>(response: Response): Promise<T> => {
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    const error = (data as { error?: string }).error ?? `${response.status} ${response.statusText}`
    throw new Error(error)
  }
  return data as T
}

export const getConsentStatus = async (signal?: AbortSignal): Promise<ConsentStatusResponse> => {
  if (usePrivacyMock) {
    return Promise.resolve({ consent: false })
  }
  // Use /api/consent/check which works directly with Supabase
  const response = await fetch("/api/consent/check", {
    method: "GET",
    headers: { Accept: "application/json" },
    signal,
  })
  
  // Transform response to expected format
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    const error = (data as { error?: string }).error ?? `${response.status} ${response.statusText}`
    throw new Error(error)
  }
  
  return {
    consent: (data as { hasConsent?: boolean }).hasConsent ?? false,
    consent_ts: (data as { consentDate?: string }).consentDate ?? undefined,
  }
}

export const postConsentAccept = async (): Promise<void> => {
  if (usePrivacyMock) {
    return Promise.resolve()
  }
  // Use /api/consent/accept which works directly with Supabase
  const response = await fetch("/api/consent/accept", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ 
      userId: "current", // Will be extracted from session
      timestamp: new Date().toISOString(),
    }),
  })
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}))
    const message = (payload as { error?: string }).error ?? response.statusText
    throw new Error(message)
  }
}

export const exportPrivacyData = async (): Promise<Blob> => {
  if (usePrivacyMock) {
    return new Blob([JSON.stringify({ conversations: [], exported_at: new Date().toISOString() }, null, 2)], {
      type: "application/json",
    })
  }
  const response = await fetch("/api/privacy/export", {
    method: "GET",
  })
  if (!response.ok) {
    throw new Error(`${response.status}`)
  }
  return response.blob()
}

export const deleteAccountData = async (): Promise<void> => {
  if (usePrivacyMock) {
    return Promise.resolve()
  }
  const response = await fetch("/api/privacy/delete", {
    method: "DELETE",
  })
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}))
    const message = (payload as { error?: string }).error ?? response.statusText
    throw new Error(message)
  }
}



