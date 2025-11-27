import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  const backendUrl = process.env.BACKEND_API_URL;
  const apiKey = process.env.BACKEND_API_KEY;

  if (!backendUrl || !apiKey) {
    return NextResponse.json({ error: "Server configuration incomplete" }, { status: 500 });
  }

  let body: { accept: boolean };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON payload" }, { status: 400 });
  }

  try {
    const response = await fetch(`${backendUrl}/api/privacy/consent`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      if (response.status === 404) {
        return NextResponse.json({ error: "Consent endpoint not available yet" }, { status: 404 });
      }
      const errorData = await response.json().catch(() => ({ error: "Unknown error" }));
      return NextResponse.json(errorData, { status: response.status });
    }

    return NextResponse.json({ ok: true });
  } catch (error) {
    console.error("[privacy/consent] Proxy error:", error);
    return NextResponse.json({ error: "Failed to submit consent" }, { status: 500 });
  }
}

