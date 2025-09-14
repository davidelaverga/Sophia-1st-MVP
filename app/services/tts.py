import base64
import requests
from app.config import get_settings
import logging
logger = logging.getLogger("sophia-backend")


def synthesize_inworld(text: str) -> bytes:
    """Call Inworld TTS and return MP3 bytes. Requires INWORLD_API_KEY (Basic base64 token)."""
    settings = get_settings()
    if not settings.INWORLD_API_KEY:
        # simple mock tone if key missing
        logger.warning("TTS: INWORLD_API_KEY missing; returning mock audio bytes")
        return b"ID3mock-mp3"

    url = "https://api.inworld.ai/tts/v1/voice"
    # Use Basic (base64) per provider docs
    headers_basic = {
        "Authorization": f"Basic {settings.INWORLD_API_KEY}",
        "Content-Type": "application/json",
    }
    # Sanitize text: Inworld requires at least one Unicode letter or digit
    try:
        import re as _re
        clean_text = (text or "").strip()
        if not _re.search(r"\w", clean_text, flags=_re.UNICODE):
            logger.warning("TTS: text lacks letters/digits; replacing with 'Okay.'")
            clean_text = "Okay."
    except Exception:
        clean_text = text or "Okay."

    # Provide a slightly richer payload; fields are commonly supported by TTS providers
    payload = {
        "text": clean_text,
        "voiceId": "Ashley",
        "modelId": "inworld-tts-1",
        "format": "mp3",
        "sampleRate": 22050,
    }
    try:
        logger.info("TTS: calling Inworld TTS (Basic)")
        r = requests.post(url, json=payload, headers=headers_basic, timeout=30)
        r.raise_for_status()
        data = r.json()
        audio_b64 = data.get("audioContent")
        if not audio_b64:
            # Return mock audio to avoid breaking UX
            logger.warning("TTS: no audioContent in response; returning mock audio")
            return b"ID3mock-mp3"
        audio_bytes = base64.b64decode(audio_b64)
        logger.info(f"TTS: received {len(audio_bytes)} bytes of audio")
        return audio_bytes
    except Exception as e:
        # Return mock audio so the pipeline continues and the user still gets audio feedback
        try:
            # If response exists in scope, log a short body
            body = r.text[:300] if 'r' in locals() and hasattr(r, 'text') else ''
            if body:
                logger.warning(f"TTS: last response body (truncated): {body}")
        except Exception:
            pass
        logger.exception(f"TTS: exception during synthesis, returning mock: {e}")
        return b"ID3mock-mp3"


def synthesize_inworld_stream(text: str, sample_rate_hz: int = 48000):
    """Yield LINEAR16 PCM bytes from Inworld streaming TTS (:stream).

    We keep the WAV header on the first chunk to make the concatenated Blob playable in browsers
    when the frontend assembles all chunks. Subsequent chunks are raw PCM16 data.
    On error, this generator yields nothing (caller should fall back to synthesize_inworld).
    """
    settings = get_settings()
    if not settings.INWORLD_API_KEY:
        logger.warning("TTS stream: INWORLD_API_KEY missing; aborting")
        return
    try:
        import json, re as _re
        clean_text = (text or "").strip()
        if not _re.search(r"\w", clean_text, flags=_re.UNICODE):
            clean_text = "Okay."
        url = "https://api.inworld.ai/tts/v1/voice:stream"
        headers = {
            "Authorization": f"Basic {settings.INWORLD_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "text": clean_text,
            "voiceId": "Ashley",
            "modelId": "inworld-tts-1",
            "audio_config": {
                "audio_encoding": "LINEAR16",
                "sample_rate_hertz": sample_rate_hz,
            },
        }
        logger.info("TTS stream: POST :stream")
        r = requests.post(url, json=payload, headers=headers, stream=True, timeout=60)
        r.raise_for_status()
        first = True
        for line in r.iter_lines():
            if not line:
                continue
            try:
                chunk = json.loads(line)
                audio_b64 = chunk.get("result", {}).get("audioContent")
                if not audio_b64:
                    continue
                bs = base64.b64decode(audio_b64)
                if first:
                    # Keep WAV header (first 44 bytes) so browser playback works when concatenated
                    first = False
                    yield bs
                else:
                    # Subsequent chunks contain a WAV header too; strip it if present
                    yield bs[44:] if len(bs) > 44 else bs
            except Exception as e:
                logger.warning(f"TTS stream: failed parsing chunk: {e}")
                continue
    except Exception as e:
        logger.exception(f"TTS stream: request failed: {e}")
        return
