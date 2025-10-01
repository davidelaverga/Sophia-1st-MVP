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

    # Enhanced payload with Deborah voice, latest model, and playground parameters
    payload = {
        "text": clean_text,
        "voiceId": "Deborah",          # Updated from Ashley
        "modelId": "inworld-tts-1-max", # Updated to latest model
        "format": "mp3",
        "sampleRate": 22050,
        "temperature": 1.1,            # From playground settings
        "talking_speed": 1.0,          # From playground settings (normal speed)
    }
    try:
        logger.info("TTS: calling Inworld TTS with Deborah voice and inworld-tts-1-max model")
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
    """Yield accumulated LINEAR16 PCM bytes from Inworld streaming TTS.

    Following Inworld docs pattern: accumulate audio data before yielding larger chunks
    for smoother playback. Yields complete audio segments instead of tiny fragments.
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
        # Enhanced payload with Deborah voice, latest model, and playground parameters
        payload = {
            "text": clean_text,
            "voiceId": "Deborah",          # Updated from Ashley
            "modelId": "inworld-tts-1-max", # Updated to latest model
            "temperature": 1.1,            # From playground settings
            "talking_speed": 1.0,          # From playground settings (normal speed)
            "audio_config": {
                "audio_encoding": "LINEAR16",
                "sample_rate_hertz": sample_rate_hz,
            },
        }
        logger.info("TTS stream: POST :stream with Deborah voice and inworld-tts-1-max model")
        r = requests.post(url, json=payload, headers=headers, stream=True, timeout=60)
        r.raise_for_status()
        
        # Accumulate audio data like in Inworld docs
        all_audio_data = []
        wav_header = None
        chunk_count = 0
        
        for line in r.iter_lines():
            if not line:
                continue
            try:
                chunk = json.loads(line)
                audio_b64 = chunk.get("result", {}).get("audioContent")
                if not audio_b64:
                    continue
                    
                bs = base64.b64decode(audio_b64)
                chunk_count += 1
                
                if wav_header is None and len(bs) > 44:
                    # Extract WAV header from first chunk
                    wav_header = bs[:44]
                    all_audio_data.extend(bs[44:])
                else:
                    # Strip WAV header from subsequent chunks
                    audio_data = bs[44:] if len(bs) > 44 else bs
                    all_audio_data.extend(audio_data)
                
                # Yield accumulated chunks every ~0.5 seconds worth of audio
                # At 48kHz 16-bit mono: ~48000 samples/sec * 2 bytes = 96000 bytes/sec
                # So ~48000 bytes = ~0.5 seconds
                if len(all_audio_data) >= 48000:
                    if wav_header:
                        # Create complete WAV with header + accumulated data
                        complete_audio = bytearray(wav_header)
                        complete_audio.extend(all_audio_data)
                        yield bytes(complete_audio)
                        wav_header = None  # Only include header in first yield
                    else:
                        yield bytes(all_audio_data)
                    all_audio_data = []
                    
            except Exception as e:
                logger.warning(f"TTS stream: failed parsing chunk: {e}")
                continue
        
        # Yield any remaining audio data
        if all_audio_data:
            if wav_header:
                complete_audio = bytearray(wav_header)
                complete_audio.extend(all_audio_data)
                yield bytes(complete_audio)
            else:
                yield bytes(all_audio_data)
                
        logger.info(f"TTS stream: completed, processed {chunk_count} chunks")
        
    except Exception as e:
        logger.exception(f"TTS stream: request failed: {e}")
        return
