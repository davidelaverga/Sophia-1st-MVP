import logging
import time
from typing import Callable
import uuid

from fastapi import HTTPException
from app.services import mistral, supabase
from app.services.emotion import Emotion, analyze_emotion_audio, infer_text_emotion
from app.services.emotional_guidance import get_guidance
from app.services.tts import synthesize_inworld

logger = logging.getLogger(__name__)

def transcript_audio(wav_bytes: bytes, cancel_check: Callable):
    try:
    
        transcript = mistral.transcribe_audio_with_voxtral(
            wav_bytes,
            cancel_check=cancel_check,
        )
        return transcript
    except Exception:
        logger.exception("Transcription failed in chat")
        raise HTTPException(status_code=500, detail="Transcription failed")
    
def analyze_emotion_by_audio(wav_bytes: bytes, cancel_check: Callable):
    is_mock_audio = False
    try:
        is_mock_audio = (wav_bytes.startswith(b'ID3mock') or len(wav_bytes) < 2048)
    except:
        is_mock_audio = False
    try:
        user_emotion = analyze_emotion_audio(wav_bytes)
        return user_emotion, is_mock_audio
    except Exception:
        logger.exception("Emotion analysis failed in chat")
        raise HTTPException(status_code=500, detail="Emotion analysis failed")

def analyze_emotion_by_text(text: str, cancel_check):
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

def generate_llm_reply(transcript: str, cancel_check: Callable):
    try:
        reply = mistral.generate_llm_reply(
            transcript,
            cancel_check=cancel_check,
        )
        return reply
    except Exception:
        logger.exception("LLM generation failed in chat")
        raise HTTPException(
            status_code=500, detail="Response generation failed"
        )
    
def synthesize_reply(reply: str, cancel_check: Callable):
    try:
        audio_bytes = synthesize_inworld(
            reply,
            cancel_check=cancel_check,
        )
        file_name = f"sophia_{int(time.time() * 1000)}.mp3"
        audio_url = supabase.upload_audio_and_get_url(
            audio_bytes, file_name
        )
        return audio_bytes, audio_url
    except Exception:
        logger.exception("Synthesis or upload failed in chat")
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