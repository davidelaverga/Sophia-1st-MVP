import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  const backendUrl = process.env.BACKEND_API_URL;
  const apiKey = process.env.BACKEND_API_KEY;

  if (!backendUrl || !apiKey) {
    return NextResponse.json({ error: "Server configuration incomplete" }, { status: 500 });
  }

  try {
    const response = await fetch(`${backendUrl}/api/privacy/export`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${apiKey}`,
      },
    });

    if (!response.ok) {
      if (response.status === 404) {
        return NextResponse.json({ error: "Export endpoint not available yet" }, { status: 404 });
      }
      const errorData = await response.json().catch(() => ({ error: "Unknown error" }));
      return NextResponse.json(errorData, { status: response.status });
    }

    const blob = await response.blob();
    return new NextResponse(blob, {
      headers: {
        "Content-Type": "application/json",
        "Content-Disposition": "attachment; filename=sophia-data.json",
      },
    });
  } catch (error) {
    console.error("[privacy/export] Proxy error:", error);
    return NextResponse.json({ error: "Failed to export data" }, { status: 500 });
  }
}

