import base64
import io
import time
import uuid
import logging
from typing import Optional

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Header, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import get_settings
from app.deps import verify_api_key, limiter
from app.services.mistral import transcribe_audio_with_voxtral, generate_llm_reply
from app.services.emotion import analyze_emotion_text
from app.services.tts import synthesize_inworld
from app.services.supabase import (
    get_supabase,
    upload_audio_and_get_url,
    insert_emotion_score,
    insert_conversation_session,
)
#load env file
from dotenv import load_dotenv
load_dotenv()

settings = get_settings()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("sophia-backend")

app = FastAPI(title=settings.APP_NAME)

# CORS (adjust as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Rate limiter integration
app.state.limiter = limiter
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ----- Models -----
class Emotion(BaseModel):
    label: str
    confidence: float

class TranscriptionResponse(BaseModel):
    text: str
    emotion: Emotion

class GenerateResponse(BaseModel):
    reply: str
    tone: Optional[str] = "neutral"

class SynthesizeResponse(BaseModel):
    audio_url: str
    emotion: Emotion

class ChatResponse(BaseModel):
    transcript: str
    reply: str
    user_emotion: Emotion
    sophia_emotion: Emotion
    audio_url: str


@app.get("/")
def root():
    return {"message": "Sophia AI Backend is running."}


@app.post("/transcribe", response_model=TranscriptionResponse)
@limiter.limit(settings.API_RATE_LIMIT)
async def transcribe(
    request: Request,
    file: UploadFile = File(...),
    api_key_ok: None = Depends(verify_api_key),
):
    if not file.filename.lower().endswith(".wav"):
        raise HTTPException(status_code=400, detail="File must be a WAV audio file.")

    session_id = uuid.uuid4()

    try:
        wav_bytes = await file.read()
        text = transcribe_audio_with_voxtral(wav_bytes)
    except Exception as e:
        logger.exception("Transcription failed")
        raise HTTPException(status_code=500, detail="Transcription failed")

    # Emotion from text (Phoenix), with graceful fallback inside
    user_emotion = analyze_emotion_text(text)

    # Persist emotion score
    try:
        insert_emotion_score(session_id, role="user", emotion=user_emotion)
    except Exception:
        logger.warning("Failed to persist user emotion score; continuing")

    return TranscriptionResponse(text=text, emotion=user_emotion)


class GenerateRequest(BaseModel):
    text: str

@app.post("/generate-response", response_model=GenerateResponse)
@limiter.limit(settings.API_RATE_LIMIT)
async def generate_response(
    request: Request,
    body: GenerateRequest,
    api_key_ok: None = Depends(verify_api_key),
):
    try:
        reply = generate_llm_reply(body.text)
    except Exception:
        logger.exception("LLM response generation failed")
        raise HTTPException(status_code=500, detail="Response generation failed")

    return GenerateResponse(reply=reply, tone="encouraging")


class SynthesizeRequest(BaseModel):
    text: str

@app.post("/synthesize", response_model=SynthesizeResponse)
@limiter.limit(settings.API_RATE_LIMIT)
async def synthesize(
    request: Request,
    body: SynthesizeRequest,
    api_key_ok: None = Depends(verify_api_key),
):
    # TTS
    try:
        audio_bytes = synthesize_inworld(body.text)
    except Exception:
        logger.exception("TTS synthesis failed")
        raise HTTPException(status_code=500, detail="Synthesis failed")

    # Upload to storage and get URL
    try:
        file_name = f"sophia_{int(time.time()*1000)}.mp3"
        audio_url = upload_audio_and_get_url(file_name, audio_bytes)
    except Exception:
        logger.exception("Audio upload failed")
        raise HTTPException(status_code=500, detail="Audio upload failed")

    # Emotion from synthesized text as proxy (optional). If you prefer audio-based, replace with audio model.
    sophia_emotion = analyze_emotion_text(body.text)

    # Persist emotion score (role = sophia)
    try:
        session_id = uuid.uuid4()
        insert_emotion_score(session_id, role="sophia", emotion=sophia_emotion)
    except Exception:
        logger.warning("Failed to persist sophia emotion score; continuing")

    return SynthesizeResponse(audio_url=audio_url, emotion=sophia_emotion)


@app.post("/chat", response_model=ChatResponse)
@limiter.limit(settings.API_RATE_LIMIT)
async def chat(
    request: Request,
    file: UploadFile = File(...),
    api_key_ok: None = Depends(verify_api_key),
):
    if not file.filename.lower().endswith(".wav"):
        raise HTTPException(status_code=400, detail="File must be a WAV audio file.")

    session_id = uuid.uuid4()

    try:
        wav_bytes = await file.read()
        transcript = transcribe_audio_with_voxtral(wav_bytes)
    except Exception:
        logger.exception("Transcription failed in chat")
        raise HTTPException(status_code=500, detail="Transcription failed")

    user_emotion = analyze_emotion_text(transcript)
    try:
        insert_emotion_score(session_id, role="user", emotion=user_emotion)
    except Exception:
        logger.warning("Persist user emotion failed; continuing")

    try:
        reply = generate_llm_reply(transcript)
    except Exception:
        logger.exception("LLM generation failed in chat")
        raise HTTPException(status_code=500, detail="Response generation failed")

    try:
        audio_bytes = synthesize_inworld(reply)
        file_name = f"sophia_{int(time.time()*1000)}.mp3"
        audio_url = upload_audio_and_get_url(file_name, audio_bytes)
    except Exception:
        logger.exception("Synthesis or upload failed in chat")
        raise HTTPException(status_code=500, detail="Synthesis failed")

    sophia_emotion = analyze_emotion_text(reply)
    try:
        insert_emotion_score(session_id, role="sophia", emotion=sophia_emotion)
    except Exception:
        logger.warning("Persist sophia emotion failed; continuing")

    # Persist full session
    try:
        insert_conversation_session({
            "id": str(session_id),
            "transcript": transcript,
            "reply": reply,
            "user_emotion_label": user_emotion.label,
            "user_emotion_confidence": user_emotion.confidence,
            "sophia_emotion_label": sophia_emotion.label,
            "sophia_emotion_confidence": sophia_emotion.confidence,
            "audio_url": audio_url,
            "created_at": int(time.time()),
        })
    except Exception:
        logger.warning("Persist conversation session failed; continuing")

    return ChatResponse(
        transcript=transcript,
        reply=reply,
        user_emotion=user_emotion,
        sophia_emotion=sophia_emotion,
        audio_url=audio_url,
    )
