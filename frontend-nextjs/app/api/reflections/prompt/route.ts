import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  const backendUrl = process.env.BACKEND_API_URL;
  const apiKey = process.env.BACKEND_API_KEY;

  if (!backendUrl || !apiKey) {
    return NextResponse.json({ error: "Server configuration incomplete" }, { status: 500 });
  }

  let body: { conversation_id: string; user_id: string };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON payload" }, { status: 400 });
  }

  if (!body.conversation_id || !body.user_id) {
    return NextResponse.json({ error: "Missing required fields" }, { status: 400 });
  }

  try {
    // Call backend /api/reflections/run to generate reflection
    const response = await fetch(`${backendUrl}/api/reflections/run`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify({
        conversation_id: body.conversation_id,
        user_id: body.user_id,
        share_to_discord: false, // Just generate, don't share yet
      }),
    });

    if (!response.ok) {
      if (response.status === 404) {
        return NextResponse.json({ allow: false, reason: "endpoint_not_available" });
      }
      // Silent fail for reflection prompt - return allow: false
      return NextResponse.json({ allow: false, reason: "backend_error" });
    }

    const data = await response.json();
    
    // Transform backend response to frontend format
    // Backend returns: { id, summary, insight_tags, ... }
    // Frontend expects: { allow: true, chunks: [{ id, text, ts, reason }] }
    
    if (!data.summary) {
      return NextResponse.json({ allow: false, reason: "no_summary" });
    }

    // Split summary into sentences (simple split by '. ')
    const sentences = data.summary
      .split('. ')
      .filter((s: string) => s.trim().length > 10)
      .slice(0, 3);

    if (sentences.length === 0) {
      return NextResponse.json({ allow: false, reason: "no_meaningful_content" });
    }

    const chunks = sentences.map((text: string, idx: number) => ({
      id: `${data.id}-chunk-${idx}`,
      text: text.trim().endsWith('.') ? text.trim() : `${text.trim()}.`,
      ts: Date.now(),
      reason: data.insight_tags?.[idx] || "reflection",
    }));

    return NextResponse.json({
      allow: true,
      chunks,
      reflection_id: data.id,
    });
  } catch (error) {
    console.error("[reflections/prompt] Proxy error:", error);
    // Silent fail for reflection prompt
    return NextResponse.json({ allow: false, reason: "fetch_error" });
  }
}

