import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  const backendUrl = process.env.BACKEND_API_URL;
  const apiKey = process.env.BACKEND_API_KEY;

  if (!backendUrl || !apiKey) {
    return NextResponse.json({ error: "Server configuration incomplete" }, { status: 500 });
  }

  try {
    const response = await fetch(`${backendUrl}/api/privacy/status`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        Accept: "application/json",
      },
    });

    if (!response.ok) {
      if (response.status === 404) {
        return NextResponse.json({ error: "Privacy status endpoint not available yet" }, { status: 404 });
      }
      const errorData = await response.json().catch(() => ({ error: "Unknown error" }));
      return NextResponse.json(errorData, { status: response.status });
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("[privacy/status] Proxy error:", error);
    return NextResponse.json({ error: "Failed to fetch privacy status" }, { status: 500 });
  }
}

