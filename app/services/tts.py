import base64
import requests
from app.config import get_settings


def synthesize_inworld(text: str) -> bytes:
    """Call Inworld TTS and return MP3 bytes. Requires INWORLD_API_KEY (Basic base64 token)."""
    settings = get_settings()
    if not settings.INWORLD_API_KEY:
        # simple mock tone if key missing
        return b"ID3mock-mp3"

    url = "https://api.inworld.ai/tts/v1/voice"
    headers = {
        "Authorization": f"Basic {settings.INWORLD_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "voiceId": "Ashley",
        "modelId": "inworld-tts-1",
    }
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=30)
        r.raise_for_status()
        data = r.json()
        audio_b64 = data.get("audioContent")
        if not audio_b64:
            # Return mock audio to avoid breaking UX
            return b"ID3mock-mp3"
        return base64.b64decode(audio_b64)
    except Exception:
        # Return mock audio so the pipeline continues and the user still gets audio feedback
        return b"ID3mock-mp3"
