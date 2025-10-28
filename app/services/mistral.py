import base64
import io
from typing import List, Optional
from mistralai import Mistral
from app.config import get_settings
import logging
logger = logging.getLogger("sophia-backend")


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

    # Preferred: Mistral transcription endpoint (voxtral-mini-latest)
    try:
        client = _client()
        # Provide a filename; SDK inspects content
        # Detect common audio container by magic bytes to choose a helpful filename
        def _detect_ext(data: bytes) -> str:
            try:
                if not data or len(data) < 4:
                    return ".wav"
                b0 = data[:4]
                if b0 == b"RIFF":
                    return ".wav"
                if b0[:3] == b"ID3" or (data[0] == 0xFF and (data[1] & 0xE0) == 0xE0):
                    return ".mp3"
                if data[:4] == b"OggS":
                    return ".ogg"
                # WebM/Matroska EBML header
                if data[:4] == bytes([0x1A, 0x45, 0xDF, 0xA3]):
                    return ".webm"
                return ".wav"
            except Exception:
                return ".wav"
        file_name = f"audio{_detect_ext(wav_bytes)}"
        bio = io.BytesIO(wav_bytes)
        resp = client.audio.transcriptions.complete(
            model="voxtral-mini-latest",
            file={
                "content": bio,
                "file_name": file_name,
            },
        )
        # Try robust extraction from SDK response
        # Known SDK returns may have attributes like 'text' or dict-like structures
        text = None
        for key in ("text", "output_text", "transcript"):
            try:
                val = getattr(resp, key, None)
                if isinstance(val, str) and val.strip():
                    text = val.strip()
                    break
            except Exception:
                pass
        if text is None:
            try:
                # If resp is dict-like
                text = (resp.get("text") or resp.get("output_text") or resp.get("transcript") or "").strip()
            except Exception:
                text = str(resp)
        return text
    except Exception:
        # Fallback: Gemini if available; otherwise empty string
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
                gresp = model.generate_content([{"text": prompt}, audio_inline])
                return (gresp.text or "").strip()
            except Exception:
                pass
        return ""




def generate_llm_reply(text: str) -> str:
    # Quick rule fallback for empty inputs
    if not text or not str(text).strip():
        return "I didn’t catch that. Could you rephrase your question about DeFi?"
    try:
        client = _client()
        # Prefer Responses API when available; fallback to Chat API for older SDKs
        try:
            resp_iface = getattr(client, "responses", None)
            if resp_iface is not None:
                r = resp_iface.create(
                    model="mistral-small-latest",
                    input=[
                        {
                            "role": "system",
                            "content": [{"type": "text", "text": "You are Sophia, a concise and safe DeFi mentor. Keep replies under 50 words."}],
                        },
                        {
                            "role": "user",
                            "content": [{"type": "text", "text": f"Respond as a DeFi mentor to: {text}"}],
                        },
                    ],
                )
                out = getattr(r, "output_text", None)
                if isinstance(out, str) and out.strip():
                    return out.strip()
                return str(r)
        except Exception:
            pass

        # Chat API fallback
        r2 = client.chat.complete(
            model="mistral-small-latest",
            messages=[
                {
                    "role": "system",
                    "content": "You are Sophia, a concise and safe DeFi mentor. Keep replies under 50 words.",
                },
                {"role": "user", "content": f"Respond as a DeFi mentor to: {text}"},
            ],
        )
        content = getattr(r2.choices[0].message, "content", r2.choices[0].message)
        return str(content).strip()
    except Exception as e:
        # Log minimal detail for debugging
        try:
            import logging
            logging.getLogger("mistral").warning(f"Responses.create failed: {e}")
        except Exception:
            pass
        # Safe rule-based fallback
        lower = text.lower()
        if "yield" in lower:
            return "Yield farming can boost returns but carries risks like impermanent loss and smart-contract bugs. Start small and diversify."
        if "staking" in lower:
            return "Staking locks tokens to secure a network in exchange for rewards. Check lockups, slashing risk, and validator reputation."
        if "defi" in lower:
            return "DeFi lets you lend, borrow, and trade without banks. Always assess protocol audits, TVL, and team track record."
        return "Here’s a quick tip: manage risk with position sizing, avoid unaudited contracts, and never chase unsustainable APRs."


def stream_generate_llm_reply(text: str):
    """Yield tokens from Mistral in a streaming fashion.

    This uses the Mistral Python SDK streaming API and yields plain text chunks
    as they arrive so the caller can forward them to clients immediately.
    """
    # Handle empty input before attempting API
    if not text or not str(text).strip():
        yield "I didn't catch that. Could you rephrase your question about DeFi?"
        return
    
    client = _client()
    
    # Use Chat streaming with proper error handling
    try:
        logger.info(f"Starting streaming LLM reply for text: {text[:50]}...")
        
        stream = client.chat.stream(
            model="mistral-small-latest",
            messages=[
                {
                    "role": "system",
                    "content": "You are Sophia, a concise and safe DeFi mentor. Keep replies under 50 words.",
                },
                {"role": "user", "content": f"Respond as a DeFi mentor to: {text}"},
            ],
        )
        
        tokens_yielded = 0
        for chunk in stream:
            try:
                # Handle different chunk formats from Mistral SDK
                if hasattr(chunk, 'choices') and chunk.choices:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, 'content') and delta.content:
                        yield delta.content
                        tokens_yielded += 1
                elif hasattr(chunk, 'delta') and chunk.delta:
                    if hasattr(chunk.delta, 'content') and chunk.delta.content:
                        yield chunk.delta.content
                        tokens_yielded += 1
                elif hasattr(chunk, 'content') and chunk.content:
                    yield chunk.content
                    tokens_yielded += 1
            except Exception as e:
                logger.warning(f"Error processing stream chunk: {e}")
                continue
                
        logger.info(f"Streaming completed, yielded {tokens_yielded} tokens")
        
        if tokens_yielded == 0:
            logger.warning("No tokens were yielded from stream, falling back to rule-based response")
            # Fallback to rule-based response if streaming failed
            lower = text.lower()
            if "yield" in lower:
                yield "Yield farming can boost returns but carries risks like impermanent loss and smart-contract bugs. Start small and diversify."
            elif "staking" in lower:
                yield "Staking locks tokens to secure a network in exchange for rewards. Check lockups, slashing risk, and validator reputation."
            elif "defi" in lower:
                yield "DeFi lets you lend, borrow, and trade without banks. Always assess protocol audits, TVL, and team track record."
            else:
                yield "Here's a quick tip: manage risk with position sizing, avoid unaudited contracts, and never chase unsustainable APRs."
        
    except Exception as e:
        logger.error(f"Streaming LLM reply failed: {e}")
        # Final rule fallback
        lower = text.lower()
        if "yield" in lower:
            yield "Yield farming can boost returns but carries risks like impermanent loss and smart-contract bugs. Start small and diversify."
        elif "staking" in lower:
            yield "Staking locks tokens to secure a network in exchange for rewards. Check lockups, slashing risk, and validator reputation."
        elif "defi" in lower:
            yield "DeFi lets you lend, borrow, and trade without banks. Always assess protocol audits, TVL, and team track record."
        else:
            yield "Here's a quick tip: manage risk with position sizing, avoid unaudited contracts, and never chase unsustainable APRs."


