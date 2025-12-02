import { NextRequest, NextResponse } from "next/server";

// Emotional/support keywords for smarter tagging
const INSIGHT_KEYWORDS: Record<string, string[]> = {
  "encouragement": ["you've got this", "you can do", "believe in", "proud of", "amazing", "great job"],
  "self-care": ["take care", "rest", "breathe", "pause", "gentle", "kind to yourself"],
  "growth": ["learn", "grow", "progress", "step", "journey", "improve"],
  "validation": ["it's okay", "normal to feel", "valid", "understand", "makes sense"],
  "guidance": ["try", "consider", "suggest", "recommend", "start with", "focus on"],
  "empathy": ["i hear you", "sounds like", "must be", "feeling", "understand how"],
  "motivation": ["can do", "capable", "strong", "resilient", "overcome"],
  "reflection": ["noticed", "thinking about", "reflect", "moment", "insight"],
};

function detectInsightType(text: string): string {
  const lowerText = text.toLowerCase();
  
  for (const [insightType, keywords] of Object.entries(INSIGHT_KEYWORDS)) {
    for (const keyword of keywords) {
      if (lowerText.includes(keyword)) {
        return insightType;
      }
    }
  }
  
  return "reflection";
}

function extractMeaningfulSentences(text: string): string[] {
  // Split by sentence endings, but keep the punctuation
  const sentences = text
    .split(/(?<=[.!?])\s+/)
    .map(s => s.trim())
    .filter(s => s.length > 15); // Minimum meaningful length
  
  // Prioritize sentences with action words or emotional content
  const actionWords = ["start", "try", "focus", "remember", "take", "you", "your", "can", "will"];
  const emotionalWords = ["feel", "heart", "love", "care", "support", "understand", "believe"];
  
  const scored = sentences.map(sentence => {
    let score = 0;
    const lower = sentence.toLowerCase();
    
    // Boost for action words
    for (const word of actionWords) {
      if (lower.includes(word)) score += 2;
    }
    
    // Boost for emotional content
    for (const word of emotionalWords) {
      if (lower.includes(word)) score += 3;
    }
    
    // Penalty for generic openings
    if (lower.startsWith("it's completely normal") || lower.startsWith("it is completely")) {
      score -= 5;
    }
    
    // Boost for questions (engaging)
    if (sentence.includes("?")) score += 2;
    
    // Boost for personal pronouns
    if (lower.includes("you") || lower.includes("your")) score += 1;
    
    return { sentence, score };
  });
  
  // Sort by score and take top 3
  return scored
    .sort((a, b) => b.score - a.score)
    .slice(0, 3)
    .map(s => s.sentence);
}

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

    // Use smarter sentence extraction
    const sentences = extractMeaningfulSentences(data.summary);

    if (sentences.length === 0) {
      return NextResponse.json({ allow: false, reason: "no_meaningful_content" });
    }

    // Create chunks with smart insight detection
    const chunks = sentences.map((text: string, idx: number) => {
      // Detect insight type from the text itself (smarter than backend keywords)
      const detectedReason = detectInsightType(text);
      
      return {
        id: `${data.id}-chunk-${idx}`,
        text: text.trim().endsWith('.') || text.trim().endsWith('!') || text.trim().endsWith('?') 
          ? text.trim() 
          : `${text.trim()}.`,
        ts: Date.now() - (idx * 1000), // Slight time offset for variety
        reason: detectedReason,
      };
    });

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

