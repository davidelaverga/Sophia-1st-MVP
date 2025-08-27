import base64
from typing import List
from mistralai import Mistral
from app.config import get_settings


def _client() -> Mistral:
    settings = get_settings()
    if not settings.MISTRAL_API_KEY:
        raise RuntimeError("MISTRAL_API_KEY is not set")
    return Mistral(api_key=settings.MISTRAL_API_KEY)


def transcribe_audio_with_voxtral(wav_bytes: bytes) -> str:
    """Transcribe audio using Mistral Voxtral if available; fallback to Gemini.
    Returns plain text transcript.
    """
    settings = get_settings()

    # 1) Try Mistral Voxtral via chat with input_audio content
    try:
        client = _client()
        audio_b64 = base64.b64encode(wav_bytes).decode("utf-8")
        model = "voxtral-mini-latest"
        resp = client.chat.complete(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_audio", "input_audio": audio_b64},
                        {
                            "type": "text",
                            "text": "Please transcribe this audio and identify the main topic or intent.",
                        },
                    ],
                }
            ],
        )
        content = getattr(resp.choices[0].message, "content", resp.choices[0].message)
        if isinstance(content, list):
            # join any text parts
            text_parts: List[str] = []
            for c in content:
                if isinstance(c, dict) and c.get("type") == "text":
                    text_parts.append(c.get("text", ""))
            out = " ".join([t for t in text_parts if t]).strip()
            if out:
                return out
        return str(content).strip()
    except Exception:
        # 2) Fallback to Gemini transcription if configured
        if getattr(settings, "GOOGLE_API_KEY", None):
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.GOOGLE_API_KEY)
                model = genai.GenerativeModel("gemini-1.5-flash")
                audio_inline = {
                    "inline_data": {
                        "mime_type": "audio/wav",
                        "data": base64.b64encode(wav_bytes).decode("utf-8"),
                    }
                }
                prompt = "Transcribe this audio. Return only the transcription text, no extra words."
                resp = model.generate_content([{"text": prompt}, audio_inline])
                return (resp.text or "").strip()
            except Exception:
                pass
        # 3) Final fallback
        return ""


def generate_llm_reply(text: str) -> str:
    client = _client()
    resp = client.chat.complete(
        model="mistral-small-latest",
        messages=[
            {
                "role": "system",
                "content": "You are Sophia, a concise and safe DeFi mentor. Keep replies under 50 words.",
            },
            {"role": "user", "content": f"Respond as a DeFi mentor to: {text}"},
        ],
    )
    content = getattr(resp.choices[0].message, "content", resp.choices[0].message)
    return str(content).strip()
