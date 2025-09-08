import base64
import io
import time
import uuid
import logging
from typing import Optional

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Header, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import get_settings
from app.deps import verify_api_key, limiter
from app.services.mistral import transcribe_audio_with_voxtral, generate_llm_reply
from app.services.emotion import analyze_emotion_text, analyze_emotion_audio
from app.services.tts import synthesize_inworld
from app.services.supabase import (
    get_supabase,
    upload_audio_and_get_url,
    insert_emotion_score,
    insert_conversation_session,
)
from app.services.langgraph_service import langgraph_service
from dotenv import load_dotenv
load_dotenv()

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

settings = get_settings()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("sophia-backend")

app = FastAPI(title=settings.APP_NAME)

# OpenTelemetry setup
resource = Resource.create({"service.name": "sophia-backend"})
provider = TracerProvider(resource=resource)
otlp_exporter = OTLPSpanExporter()
provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("sophia")
FastAPIInstrumentor.instrument_app(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.state.limiter = limiter
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Mount static files for frontend
app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")


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
    intent: Optional[str] = None
    context_memory: Optional[dict] = None
    evaluation_report: Optional[dict] = None

class DefiChatResponse(BaseModel):
    session_id: str
    transcript: str
    reply: str
    user_emotion: Emotion
    sophia_emotion: Emotion
    audio_url: str
    intent: str
    context_memory: dict
    fallbacks_used: dict
    evaluation_logs: list
    evaluation_report: Optional[dict] = None

class TextChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


@app.get("/")
def root():
    """Serve the frontend interface"""
    return FileResponse("frontend/index.html")

@app.get("/api")
def api_root():
    """API status endpoint"""
    return {"message": "Sophia AI Backend with DeFi Agent is running."}


@app.post("/transcribe", response_model=TranscriptionResponse)
@limiter.limit(settings.API_RATE_LIMIT)
async def transcribe(
    request: Request,
    file: UploadFile = File(...),
    api_key_ok: None = Depends(verify_api_key),
):
    # Accept common audio formats
    allowed_extensions = ['.wav', '.webm', '.mp3', '.mp4', '.ogg', '.flac', '.m4a', '.aac']
    if not any(file.filename.lower().endswith(ext) for ext in allowed_extensions):
        raise HTTPException(status_code=400, detail=f"File must be an audio file. Supported formats: {', '.join(allowed_extensions)}")

    session_id = uuid.uuid4()

    try:
        wav_bytes = await file.read()
        text = transcribe_audio_with_voxtral(wav_bytes)
    except Exception as e:
        logger.exception("Transcription failed")
        raise HTTPException(status_code=500, detail="Transcription failed")

    user_emotion = analyze_emotion_audio(wav_bytes)

    try:
        insert_emotion_score(session_id, role="user", emotion=user_emotion)
    except Exception:
        logger.warning("Failed to persist user emotion score; continuing")

    return TranscriptionResponse(text=text, emotion=user_emotion.model_dump())


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
    try:
        audio_bytes = synthesize_inworld(body.text)
    except Exception:
        logger.exception("TTS synthesis failed")
        raise HTTPException(status_code=500, detail="Synthesis failed")

    try:
        file_name = f"sophia_{int(time.time()*1000)}.mp3"
        # Fix argument order: first bytes, then optional file_name
        audio_url = upload_audio_and_get_url(audio_bytes, file_name)
    except Exception:
        logger.exception("Audio upload failed")
        raise HTTPException(status_code=500, detail="Audio upload failed")

    sophia_emotion = analyze_emotion_audio(audio_bytes)

    try:
        session_id = uuid.uuid4()
        insert_emotion_score(session_id, role="sophia", emotion=sophia_emotion)
    except Exception:
        logger.warning("Failed to persist sophia emotion score; continuing")

    return SynthesizeResponse(audio_url=audio_url, emotion=sophia_emotion.model_dump())


@app.post("/chat", response_model=ChatResponse)
@limiter.limit(settings.API_RATE_LIMIT)
async def chat(
    request: Request,
    file: UploadFile = File(...),
    api_key_ok: None = Depends(verify_api_key),
):
    # Accept common audio formats
    allowed_extensions = ['.wav', '.webm', '.mp3', '.mp4', '.ogg', '.flac', '.m4a', '.aac']
    if not any(file.filename.lower().endswith(ext) for ext in allowed_extensions):
        raise HTTPException(status_code=400, detail=f"File must be an audio file. Supported formats: {', '.join(allowed_extensions)}")

    session_id = uuid.uuid4()

    with tracer.start_as_current_span("chat") as chat_span:
        chat_span.set_attribute("session.id", str(session_id))
        t0 = time.time()
        try:
            wav_bytes = await file.read()
            with tracer.start_as_current_span("stt_transcription") as stt_span:
                transcript = transcribe_audio_with_voxtral(wav_bytes)
                stt_span.set_attribute("transcript.length", len(transcript))
        except Exception:
            logger.exception("Transcription failed in chat")
            raise HTTPException(status_code=500, detail="Transcription failed")

        user_emotion = analyze_emotion_audio(wav_bytes)
        chat_span.set_attribute("phoenix_user_emotion.label", user_emotion.label)
        chat_span.set_attribute("phoenix_user_emotion.confidence", float(user_emotion.confidence))
        try:
            insert_emotion_score(session_id, role="user", emotion=user_emotion)
        except Exception:
            logger.warning("Persist user emotion failed; continuing")

        try:
            with tracer.start_as_current_span("llm_generation") as llm_span:
                reply = generate_llm_reply(transcript)
                llm_span.set_attribute("reply.length", len(reply))
        except Exception:
            logger.exception("LLM generation failed in chat")
            raise HTTPException(status_code=500, detail="Response generation failed")

        try:
            with tracer.start_as_current_span("tts_synthesis_upload"):
                audio_bytes = synthesize_inworld(reply)
                file_name = f"sophia_{int(time.time()*1000)}.mp3"
                # Fix argument order: first bytes, then optional file_name
                audio_url = upload_audio_and_get_url(audio_bytes, file_name)
        except Exception:
            logger.exception("Synthesis or upload failed in chat")
            raise HTTPException(status_code=500, detail="Synthesis failed")

        sophia_emotion = analyze_emotion_audio(audio_bytes)
        chat_span.set_attribute("phoenix_sophia_emotion.label", sophia_emotion.label)
        chat_span.set_attribute("phoenix_sophia_emotion.confidence", float(sophia_emotion.confidence))
        try:
            insert_emotion_score(session_id, role="sophia", emotion=sophia_emotion)
        except Exception:
            logger.warning("Persist sophia emotion failed; continuing")

        total_ms = int((time.time() - t0) * 1000)
        chat_span.set_attribute("total_roundtrip_time.ms", total_ms)

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
        user_emotion=user_emotion.model_dump(),
        sophia_emotion=sophia_emotion.model_dump(),
        audio_url=audio_url,
    )


@app.post("/defi-chat", response_model=DefiChatResponse)
@limiter.limit(settings.API_RATE_LIMIT)
async def defi_chat(
    request: Request,
    file: UploadFile = File(...),
    session_id: Optional[str] = None,
    api_key_ok: None = Depends(verify_api_key),
):
    """Enhanced chat endpoint using LangGraph for DeFi conversations"""
    
    # Accept common audio formats
    allowed_extensions = ['.wav', '.webm', '.mp3', '.mp4', '.ogg', '.flac', '.m4a', '.aac']
    if not any(file.filename.lower().endswith(ext) for ext in allowed_extensions):
        raise HTTPException(status_code=400, detail=f"File must be an audio file. Supported formats: {', '.join(allowed_extensions)}")

    try:
        wav_bytes = await file.read()
        
        # Process through LangGraph pipeline
        result = langgraph_service.process_conversation(
            audio_bytes=wav_bytes,
            session_id=session_id,
            run_evaluation=True
        )
        
        # Store in Supabase
        try:
            insert_conversation_session({
                "id": result["session_id"],
                "transcript": result["transcript"],
                "reply": result["reply"],
                "user_emotion_label": result["user_emotion"]["label"],
                "user_emotion_confidence": result["user_emotion"]["confidence"],
                "sophia_emotion_label": result["sophia_emotion"]["label"],
                "sophia_emotion_confidence": result["sophia_emotion"]["confidence"],
                "audio_url": result["audio_url"],
                "created_at": int(time.time()),
                "intent": result["intent"],
                "context_memory": str(result["context_memory"]),
            })
        except Exception as e:
            logger.warning(f"Failed to persist conversation session: {e}")
        
        return DefiChatResponse(**result)
        
    except Exception as e:
        logger.exception("DeFi chat processing failed")
        raise HTTPException(status_code=500, detail=f"DeFi chat processing failed: {str(e)}")


@app.post("/text-chat", response_model=DefiChatResponse)
@limiter.limit(settings.API_RATE_LIMIT)
async def text_chat(
    request: Request,
    body: TextChatRequest,
    api_key_ok: None = Depends(verify_api_key),
):
    """Text-only chat endpoint for DeFi conversations"""
    
    try:
        # Create a minimal audio representation for text input
        # This allows reuse of the LangGraph pipeline
        fake_audio = b""  # Empty audio bytes for text-only input
        
        # Process through LangGraph, but override transcript
        result = langgraph_service.process_conversation(
            audio_bytes=fake_audio,
            session_id=body.session_id,
            run_evaluation=True
        )
        
        # Override transcript with the actual text message
        result["transcript"] = body.message
        
        # For text-only, set neutral emotions initially
        result["user_emotion"] = {"label": "neutral", "confidence": 0.7}
        
        # Store in Supabase
        try:
            insert_conversation_session({
                "id": result["session_id"],
                "transcript": result["transcript"],
                "reply": result["reply"],
                "user_emotion_label": result["user_emotion"]["label"],
                "user_emotion_confidence": result["user_emotion"]["confidence"],
                "sophia_emotion_label": result["sophia_emotion"]["label"],
                "sophia_emotion_confidence": result["sophia_emotion"]["confidence"],
                "audio_url": result["audio_url"],
                "created_at": int(time.time()),
                "intent": result["intent"],
                "context_memory": str(result["context_memory"]),
            })
        except Exception as e:
            logger.warning(f"Failed to persist text conversation session: {e}")
        
        return DefiChatResponse(**result)
        
    except Exception as e:
        logger.exception("Text chat processing failed")
        raise HTTPException(status_code=500, detail=f"Text chat processing failed: {str(e)}")


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": int(time.time())}


@app.get("/sessions/{session_id}")
async def get_session_memory(
    session_id: str,
    api_key_ok: None = Depends(verify_api_key),
):
    """Get conversation memory for a session"""
    try:
        from app.services.memory import memory_manager
        context = memory_manager.get_context_for_llm(session_id)
        return {"session_id": session_id, "context": context}
    except Exception as e:
        logger.exception("Failed to retrieve session memory")
        raise HTTPException(status_code=500, detail="Failed to retrieve session memory")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0", 
        port=8000, 
        reload=True
    )