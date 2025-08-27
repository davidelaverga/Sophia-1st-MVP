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
    """Transcribe using Mistral Voxtral via chat.complete with input_audio.
    Returns plain text transcript (string).
    """
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
                        "text": "Transcribe this audio. Return only the transcription text, no extra words.",
                    },
                ],
            }
        ],
    )
    # Response content may be a string; normalize to str
    content = resp.choices[0].message.content
    if isinstance(content, list):
        # join any text parts
        text_parts: List[str] = []
        for c in content:
            if isinstance(c, dict) and c.get("type") == "text":
                text_parts.append(c.get("text", ""))
        return " ".join([t for t in text_parts if t]).strip()
    return str(content).strip()


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
    return str(resp.choices[0].message.content).strip()
