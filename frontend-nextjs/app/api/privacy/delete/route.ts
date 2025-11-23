import { NextRequest, NextResponse } from "next/server";

export async function DELETE(request: NextRequest) {
  const backendUrl = process.env.BACKEND_API_URL;
  const apiKey = process.env.BACKEND_API_KEY;

  if (!backendUrl || !apiKey) {
    return NextResponse.json({ error: "Server configuration incomplete" }, { status: 500 });
  }

  try {
    const response = await fetch(`${backendUrl}/api/privacy/delete`, {
      method: "DELETE",
      headers: {
        Authorization: `Bearer ${apiKey}`,
      },
    });

    if (!response.ok) {
      if (response.status === 404) {
        return NextResponse.json({ error: "Delete endpoint not available yet" }, { status: 404 });
      }
      const errorData = await response.json().catch(() => ({ error: "Unknown error" }));
      return NextResponse.json(errorData, { status: response.status });
    }

    return NextResponse.json({ ok: true });
  } catch (error) {
    console.error("[privacy/delete] Proxy error:", error);
    return NextResponse.json({ error: "Failed to delete account" }, { status: 500 });
  }
}

