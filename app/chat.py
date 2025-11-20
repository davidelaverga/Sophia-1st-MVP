import logging
import time
import uuid
from typing import Callable, Optional

from fastapi import HTTPException
from opentelemetry import trace

from app.services import mistral, supabase
from app.services.emotion import Emotion, analyze_emotion_audio, infer_text_emotion
from app.services.emotional_guidance import get_guidance
from app.services.tts import synthesize_inworld, synthesize_inworld_stream

logger = logging.getLogger(__name__)
tracer = trace.get_tracer("sophia.chat")

def transcript_audio(wav_bytes: bytes, cancel_check: Optional[Callable] = None):
    try:
        with tracer.start_as_current_span("stt_transcription") as stt_span:
            transcript = mistral.transcribe_audio_with_voxtral(
                wav_bytes,
                cancel_check=cancel_check,
            )
            stt_span.set_attribute("transcript.length", len(transcript))
        return transcript
    except Exception:
        logger.exception("Transcription failed in chat")
        raise HTTPException(status_code=500, detail="Transcription failed")
    
def analyze_emotion_by_audio(
    wav_bytes: bytes,
    cancel_check: Optional[Callable] = None,
    role: str = "user",
):
    is_mock_audio = False
    try:
        is_mock_audio = (wav_bytes.startswith(b'ID3mock') or len(wav_bytes) < 2048)
    except Exception:
        is_mock_audio = False
    try:
        span_name = f"emotion_analysis_{role or 'unknown'}"
        with tracer.start_as_current_span(span_name) as emotion_span:
            user_emotion = analyze_emotion_audio(wav_bytes)
            emotion_span.set_attribute(
                f"phoenix_{role}_emotion.label", getattr(user_emotion, "label", "unknown")
            )
            emotion_span.set_attribute(
                f"phoenix_{role}_emotion.confidence",
                float(getattr(user_emotion, "confidence", 0.0)),
            )
            emotion_span.set_attribute("emotion.type", role or "unknown")
            emotion_span.set_attribute("emotion.source", "audio")
        return user_emotion, is_mock_audio
    except Exception:
        logger.exception("Emotion analysis failed in chat")
        raise HTTPException(status_code=500, detail="Emotion analysis failed")

def analyze_emotion_by_text(text: str, cancel_check=None):
    return infer_text_emotion(text)
        

def get_emotional_guidance(emotion: Emotion):
    emotional_guidance = []
    try:
        emotional_guidance = get_guidance(emotion.label)
    except Exception as error:
        logger.warning(
            "Text chat stream guidance lookup failed: %s", error
        )
    finally:
        return emotional_guidance

def generate_llm_reply(transcript: str, cancel_check: Optional[Callable] = None):
    cancel = cancel_check or (lambda: None)
    try:
        with tracer.start_as_current_span("llm_generation") as llm_span:
            reply = mistral.generate_llm_reply(
                transcript,
                cancel_check=cancel,
            )
            llm_span.set_attribute("reply.length", len(reply))
        return reply
    except Exception:
        logger.exception("LLM generation failed in chat")
        raise HTTPException(status_code=500, detail="Response generation failed")

def generate_streamed_llm_reply(prompt: str, cancel_check: Optional[Callable] = None):
    try:
        streamed = mistral.stream_generate_llm_reply(prompt, cancel_check=cancel_check)
        token_count = 0
        with tracer.start_as_current_span("llm_stream_generation") as stream_span:
            for chunk in streamed:
                if cancel_check:
                    cancel_check()
                if not chunk:
                    continue
                token_count += 1
                yield chunk
            stream_span.set_attribute("reply.tokens_streamed", token_count)
    except Exception:
        logger.exception("Streamed LLM generation failed in chat")
        raise HTTPException(status_code=500, detail="Response generation failed")

def synthesize_reply(reply: str, cancel_check: Optional[Callable] = None):
    try:
        with tracer.start_as_current_span("tts_synthesis_upload") as tts_span:
            audio_bytes = synthesize_inworld(
                reply,
                cancel_check=cancel_check,
            )
            file_name = f"sophia_{int(time.time() * 1000)}.mp3"
            audio_url = supabase.upload_audio_and_get_url(
                audio_bytes, file_name
            )
            tts_span.set_attribute("tts.audio_url", audio_url)
            tts_span.set_attribute("tts.audio_bytes", len(audio_bytes or b""))
        return audio_bytes, audio_url
    except Exception:
        logger.exception("Synthesis or upload failed in chat")
        raise HTTPException(status_code=500, detail="Synthesis failed")

def synthesize_streamed_reply(text: str, samplerate: int, cancel_check: Optional[Callable] = None):
    try:
        for pcm_chunk in synthesize_inworld_stream(text, sample_rate_hz=samplerate, cancel_check=cancel_check):
            if cancel_check:
                cancel_check()
            yield pcm_chunk
    except Exception:
        logger.exception("Streamed synthesis failed in chat")
        raise HTTPException(status_code=500, detail="Synthesis failed")

def persist_conversation_session(
    supabase_token: str,
    user_id: str,
    session_id: uuid.UUID=None,
    transcript: str=None,
    reply: str=None,
    user_emotion: Emotion=None,
    sophia_emotion: Emotion=None,
    reply_audio_url: str=None,
    intent=None,
    context_memory=None,
):
    try:
        supabase.insert_conversation_session(
            {
                "id": str(session_id),
                "transcript": transcript,
                "reply": reply,
                "user_emotion_label": user_emotion.label,
                "user_emotion_confidence": user_emotion.confidence,
                "sophia_emotion_label": sophia_emotion.label,
                "sophia_emotion_confidence": sophia_emotion.confidence,
                "audio_url": reply_audio_url or None,
                "intent": intent,
                "context_memory": context_memory,
                "user_id": user_id,
            },
            access_token=supabase_token,
        )
    except Exception:
        logger.warning("Persist conversation session failed; continuing")
    try:
        supabase.insert_emotion_score(
            session_id,
            role="user",
            emotion=user_emotion,
            user_id=user_id,
            access_token=supabase_token,
        )
    except Exception:
        logger.warning("Persist user emotion failed; continuing")
    try:
        supabase.insert_emotion_score(
            session_id,
            role="sophia",
            emotion=sophia_emotion,
            user_id=user_id,
            access_token=supabase_token,
        )
    except Exception:
        logger.warning("Persist sophia emotion failed; continuing")
