import base64
import logging
import mimetypes
from typing import Optional, Tuple
from urllib.parse import urljoin

from mistralai import Mistral

from app.config import get_settings

logger = logging.getLogger("sophia-backend")
_client_base_url_logged = False


def _audio_file_payload(wav_bytes: bytes) -> Tuple[str, bytes, str]:
    """Return a tuple compatible with the Voxtral SDK's file parameter."""

    default_mime = "audio/wav"

    # Ensure we always provide some bytes, even for empty clips.
    raw_bytes = wav_bytes or b""

    # Rough magic-byte sniffing for better filenames (SDK inspects extension).
    header = raw_bytes[:4]
    if header == b"RIFF":
        ext = ".wav"
    elif header[:3] == b"ID3" or (
        raw_bytes
        and raw_bytes[0] == 0xFF
        and (raw_bytes[1] & 0xE0) == 0xE0
    ):
        ext = ".mp3"
    elif header == b"OggS":
        ext = ".ogg"
    elif header == bytes([0x1A, 0x45, 0xDF, 0xA3]):
        ext = ".webm"
    else:
        ext = ".wav"

    filename = f"audio{ext}"
    mime = mimetypes.types_map.get(ext.lower(), default_mime)

    return filename, raw_bytes, mime


_RESPONSES_AVAILABLE = True


def _extract_http_details(exc: Exception) -> Tuple[Optional[int], Optional[str]]:
    """Best-effort extraction of status code and textual response from an exception."""

    status: Optional[int] = None
    text: Optional[str] = None

    for attr in ("status_code", "status"):
        value = getattr(exc, attr, None)
        if value is not None:
            try:
                status = int(value)
                break
            except (TypeError, ValueError):
                pass

    response = getattr(exc, "response", None)
    if response is not None:
        for attr in ("status_code", "status"):
            value = getattr(response, attr, None)
            if value is not None:
                try:
                    status = int(value)
                    break
                except (TypeError, ValueError):
                    pass

        text_candidate = None
        for attr in ("text", "content", "body"):
            value = getattr(response, attr, None)
            if callable(value):
                try:
                    value = value()
                except Exception:
                    value = None
            if value is None:
                continue
            if isinstance(value, bytes):
                try:
                    value = value.decode("utf-8", "ignore")
                except Exception:
                    value = None
            if isinstance(value, str) and value.strip():
                text_candidate = value.strip()
                break
        if text_candidate:
            text = text_candidate

    if text is None:
        for attr in ("message", "detail"):
            value = getattr(exc, attr, None)
            if isinstance(value, str) and value.strip():
                text = value.strip()
                break

    if text is not None and len(text) > 500:
        text = text[:497] + "..."

    return status, text


def _client() -> Mistral:
    settings = get_settings()
    if not settings.MISTRAL_API_KEY:
        raise RuntimeError("MISTRAL_API_KEY is not set")
    client = Mistral(
        api_key=settings.MISTRAL_API_KEY,
        server_url=settings.MISTRAL_API_BASE,
    )

    global _client_base_url_logged
    if not _client_base_url_logged:
        logger.info(
            "Configured Mistral client base URL: %s",
            settings.MISTRAL_API_BASE,
        )
        _client_base_url_logged = True

    return client


def transcribe_audio_with_voxtral(wav_bytes: bytes) -> str:
    """Transcribe audio using Mistral Voxtral if available; fallback to Gemini.
    Returns plain text transcript.
    """
    settings = get_settings()

    # Preferred: Mistral transcription endpoint (voxtral-large-latest for best accuracy)
    try:
        client = _client()
        endpoint = urljoin(settings.MISTRAL_API_BASE.rstrip("/") + "/", "v1/audio/transcriptions")
        logger.info(
            "Calling Mistral transcription endpoint %s with %d bytes",
            endpoint,
            len(wav_bytes),
        )

        resp = client.audio.transcriptions.complete(
            model="voxtral-large-latest",
            file=_audio_file_payload(wav_bytes),
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
    except Exception as e:
        status_code = None
        response_body = None
        resp = getattr(e, "response", None)
        if resp is not None:
            status_code = getattr(resp, "status_code", None)
            response_body = getattr(resp, "text", None) or getattr(resp, "content", None)
            if response_body is None:
                try:
                    response_body = resp.json()
                except Exception:
                    response_body = None
        if status_code is None:
            status_code = getattr(e, "status_code", None)
        if response_body is None:
            response_body = getattr(e, "body", None)
        if isinstance(response_body, (bytes, bytearray)):
            try:
                response_body = response_body.decode("utf-8", errors="replace")
            except Exception:
                response_body = repr(response_body)
        if response_body is not None and len(str(response_body)) > 1000:
            response_body = f"{str(response_body)[:1000]}…"

        logger.warning(
            "Mistral transcription failed (status=%s, body=%s): %s",
            status_code,
            response_body,
            e,
            exc_info=True,
        )
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
    global _RESPONSES_AVAILABLE
    try:
        client = _client()
        # Prefer Responses API when available; fallback to Chat API for older SDKs
        resp_iface = getattr(client, "responses", None)
        if resp_iface is not None and _RESPONSES_AVAILABLE:
            try:
                r = resp_iface.create(
                    model="mistral-large-latest",
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
            except Exception as responses_exc:
                _RESPONSES_AVAILABLE = False
                status, body = _extract_http_details(responses_exc)
                if status is not None and 400 <= status < 500:
                    consequence = "Payload may be invalid; continuing with Chat API."
                else:
                    consequence = "Disabling Responses API for this process and using Chat API."
                details = []
                if status is not None:
                    details.append(f"status={status}")
                if body:
                    details.append(f"response={body}")
                detail_str = ", ".join(details) if details else "no additional diagnostics"
                logger.warning(
                    "Mistral Responses API call failed (%s). %s",
                    detail_str,
                    consequence,
                )

        # Chat API fallback (current production path)
        r2 = client.chat.complete(
            model="mistral-large-latest",
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


def generate_llm_reply_with_context(
    user_question: str, 
    rag_context: str = "", 
    emotion_label: str = "neutral", 
    memory_context: str = "",
    intent: str = "small_talk"
) -> str:
    """Generate LLM reply with proper context separation."""
    
    # Handle empty input first - before any logging that might crash
    if not user_question or not str(user_question).strip():
        logger.warning(f"⚠️ Empty user_question received with intent={intent}")
        if intent == "defi_question":
            return "I didn't catch that. Could you rephrase your question about DeFi?"
        elif intent == "emotional_support":
            return "I'm here to listen. What's on your mind?"
        else:
            return "I didn't catch that. Could you say that again?"
    
    # Log inputs for debugging (AFTER type guard to prevent crashes)
    logger.info(f"🎯 generate_llm_reply_with_context called:")
    logger.info(f"   user_question: '{user_question[:100]}'")
    logger.info(f"   intent: {intent}")
    logger.info(f"   emotion: {emotion_label}")
    logger.info(f"   rag_context length: {len(rag_context) if rag_context else 0}")
    logger.info(f"   memory_context length: {len(memory_context) if memory_context else 0}")
    
    try:
        # Build system message with ALL context
        system_parts = []
        
        # Base personality  
        system_parts.append("You are Sophia, a knowledgeable and supportive DeFi education mentor.")
        
        # Add emotional context
        if emotion_label and emotion_label != "neutral":
            system_parts.append(f"\nUser's current emotional state: {emotion_label}. Be aware of this but prioritize factual accuracy.")
        
        # Add conversation history
        if memory_context:
            system_parts.append(f"\nConversation history: {memory_context}")
        
        # Add RAG context
        if rag_context:
            system_parts.append(f"\n\nRELEVANT KNOWLEDGE BASE:\n{rag_context}")
            system_parts.append("\n⚠️ IMPORTANT: Use the knowledge base when relevant.")
        
        # Response guidelines based on intent
        system_parts.append("\n\nResponse guidelines:")
        if intent == "defi_question":
            system_parts.append("- This is a DeFi educational question. Provide accurate answers (50-100 words).")
        elif intent == "emotional_support":
            system_parts.append("- Be empathetic while remaining educational (40-80 words).")
        else:  # small_talk
            system_parts.append("- This is casual conversation. Be friendly, warm, and conversational (20-40 words).")
            system_parts.append("- You can engage in general conversation, not just DeFi topics.")
            system_parts.append("- If asked about yourself, share that you're Sophia, an AI assistant for DeFi education.")
        
        system_message = "".join(system_parts)
        
        logger.info(f"📝 System message built: {len(system_message)} chars")
        logger.info(f"📝 System message preview: {system_message[:200]}...")
        
        # User message is JUST the question
        client = _client()
        
        logger.info(f"🚀 Calling Mistral API...")
        
        # Try Responses API first
        response_text = None
        try:
            resp_iface = getattr(client, "responses", None)
            if resp_iface is not None:
                logger.info("   Using Responses API")
                r = resp_iface.create(
                    model="mistral-large-latest",
                    input=[
                        {
                            "role": "system",
                            "content": [{"type": "text", "text": system_message}],
                        },
                        {
                            "role": "user",
                            "content": [{"type": "text", "text": user_question}],
                        },
                    ],
                )
                out = getattr(r, "output_text", None)
                logger.info(f"✅ Responses API returned: type={type(out)}, len={len(str(out)) if out else 0}")
                logger.info(f"   Response preview: {str(out)[:200] if out else 'None'}")
                
                if isinstance(out, str) and out.strip():
                    response_text = out.strip()
                else:
                    response_text = str(r)
                    logger.warning(f"⚠️ output_text not found, using str(r): {response_text[:100]}")
        except Exception as e:
            logger.warning(f"⚠️ Responses API failed: {type(e).__name__}: {str(e)}")
        
        # Chat API fallback
        if not response_text:
            logger.info("   Using Chat API (fallback)")
            r2 = client.chat.complete(
                model="mistral-large-latest",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_question},
                ],
            )
            content = getattr(r2.choices[0].message, "content", r2.choices[0].message)
            response_text = str(content).strip()
            logger.info(f"✅ Chat API returned: len={len(response_text)}")
            logger.info(f"   Response preview: {response_text[:200]}")
        
        logger.info(f"🎉 Mistral API SUCCESS - returning response: '{response_text[:100]}'")
        return response_text
        
    except Exception as e:
        # ✅ ENHANCED ERROR LOGGING
        logger.error(f"❌ LLM with context failed: {type(e).__name__}: {str(e)}")
        
        # Check API key configuration
        settings = get_settings()
        has_key = bool(getattr(settings, 'MISTRAL_API_KEY', None))
        key_length = len(settings.MISTRAL_API_KEY) if has_key else 0
        logger.error(f"🔑 MISTRAL_API_KEY status: present={has_key}, length={key_length}")
        
        # Log API response details if available
        if hasattr(e, 'response'):
            try:
                status = getattr(e.response, 'status_code', 'N/A')
                body = getattr(e.response, 'text', 'N/A')[:500]
                logger.error(f"📡 API Response Status: {status}")
                logger.error(f"📡 API Response Body: {body}")
            except:
                pass
        
        # Log the full traceback for debugging
        import traceback
        logger.error(f"📋 Full traceback:\n{traceback.format_exc()}")
        
        # Context-aware rule-based fallback
        lower = user_question.lower()
        
        # Small talk fallbacks (NEW - based on intent)
        if intent == "small_talk":
            if any(greeting in lower for greeting in ["hello", "hi", "hey", "good morning", "good evening"]):
                return "Hello! I'm Sophia, your DeFi education assistant. How can I help you today?"
            if "how are you" in lower or "how're you" in lower:
                return "I'm doing great, thanks for asking! I'm here to help you learn about DeFi. What would you like to know?"
            if "who are you" in lower or "what are you" in lower:
                return "I'm Sophia, an AI assistant specializing in DeFi education. I help people understand decentralized finance."
            if "your name" in lower or "you called" in lower:
                return "My name is Sophia. I'm here to help you navigate the world of DeFi!"
            # Generic small talk
            return "I'm here to help! Feel free to ask me about DeFi, or we can just chat."
        
        # DeFi-specific keywords
        if "yield" in lower:
            return "Yield farming can boost returns but carries risks like impermanent loss and smart-contract bugs. Start small and diversify."
        if "staking" in lower:
            return "Staking locks tokens to secure a network in exchange for rewards. Check lockups, slashing risk, and validator reputation."
        if "defi" in lower or "crypto" in lower:
            return "DeFi lets you lend, borrow, and trade without banks. Always assess protocol audits, TVL, and team track record."
        
        # Emotional support fallback
        if intent == "emotional_support":
            return "I understand you're going through something. Remember, it's okay to take a step back. I'm here for you."
        
        # Final generic fallback
        return "I'm here to help! What would you like to know?"


def stream_generate_llm_reply(text: str):
    """Yield tokens from Mistral in a streaming fashion.

    This uses the Mistral Python SDK streaming API and yields plain text chunks
    as they arrive so the caller can forward them to clients immediately.
    """
    # Handle empty input before attempting API
    if not text or not str(text).strip():
        yield "I didn't catch that. Could you say that again?"
        return
    
    client = _client()
    
    # Use Chat streaming with proper error handling
    try:
        logger.info(f"Starting streaming LLM reply for text: {text[:50]}...")
        
        stream = client.chat.stream(
            model="mistral-large-latest",
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


