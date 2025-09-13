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
resource = Resource.create({
    "service.name": "sophia-backend",
    "service.version": "1.0.0",
    "deployment.environment": "staging"
})
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

        with tracer.start_as_current_span("emotion_analysis_user") as emotion_span:
            user_emotion = analyze_emotion_audio(wav_bytes)
            emotion_span.set_attribute("phoenix_user_emotion.label", user_emotion.label)
            emotion_span.set_attribute("phoenix_user_emotion.confidence", float(user_emotion.confidence))
            emotion_span.set_attribute("emotion.type", "user")
            emotion_span.set_attribute("emotion.source", "audio")
        
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

        with tracer.start_as_current_span("emotion_analysis_sophia") as sophia_emotion_span:
            sophia_emotion = analyze_emotion_audio(audio_bytes)
            sophia_emotion_span.set_attribute("phoenix_sophia_emotion.label", sophia_emotion.label)
            sophia_emotion_span.set_attribute("phoenix_sophia_emotion.confidence", float(sophia_emotion.confidence))
            sophia_emotion_span.set_attribute("emotion.type", "sophia")
            sophia_emotion_span.set_attribute("emotion.source", "audio")
        
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
            collect_evaluation_data=True
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
        # Process text message directly through LangGraph with text input
        result = langgraph_service.process_text_conversation(
            message=body.message,
            session_id=body.session_id,
            collect_evaluation_data=True
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
            logger.warning(f"Failed to persist text conversation session: {e}")
        
        return DefiChatResponse(**result)
        
    except Exception as e:
        logger.exception("Text chat processing failed")
        raise HTTPException(status_code=500, detail=f"Text chat processing failed: {str(e)}")


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": int(time.time())}


@app.get("/memory/{session_id}")
async def get_memory(
    session_id: str,
    api_key_ok: None = Depends(verify_api_key),
):
    """Get conversation memory for a session"""
    try:
        from app.services.memory import memory_manager
        context = memory_manager.get_context_for_llm(session_id)
        
        return {
            "session_id": session_id,
            "context": context,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"Failed to get memory for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve memory")


@app.post("/evaluation/force/{session_id}")
async def force_evaluate_conversation(
    session_id: str,
    api_key_ok: None = Depends(verify_api_key),
):
    """Force evaluation of a specific conversation"""
    try:
        from app.services.evaluations import evaluation_manager
        
        report = evaluation_manager.force_evaluate_conversation(session_id)
        
        if report is None:
            raise HTTPException(status_code=404, detail=f"No active conversation found for session {session_id}")
        
        return {
            "message": "Conversation evaluation completed",
            "session_id": session_id,
            "evaluation_report": {
                "total_messages": report.total_messages,
                "conversation_duration_minutes": round(report.conversation_duration / 60, 2),
                "ragas_average": report.ragas_metrics.average_score if report.ragas_metrics else None,
                "phoenix_evaluations": len(report.phoenix_metrics),
                "drift_alert": report.drift_alert,
                "confidence_change": f"{report.baseline_confidence:.2f} -> {report.current_confidence:.2f}"
            },
            "timestamp": time.time()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to force evaluate conversation {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to evaluate conversation")


@app.get("/evaluation/status")
async def get_evaluation_status(
    api_key_ok: None = Depends(verify_api_key),
):
    """Get current evaluation system status"""
    try:
        from app.services.evaluations import evaluation_manager
        
        active_count = evaluation_manager.get_active_conversation_count()
        
        # Get status of all active conversations
        active_conversations = []
        for session_id in evaluation_manager.active_conversations.keys():
            status = evaluation_manager.get_conversation_status(session_id)
            if status:
                active_conversations.append(status)
        
        return {
            "active_conversations_count": active_count,
            "active_conversations": active_conversations,
            "conversation_timeout_minutes": evaluation_manager.conversation_timeout / 60,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"Failed to get evaluation status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get evaluation status")


@app.post("/evaluation/check-finished")
async def check_finished_conversations(
    api_key_ok: None = Depends(verify_api_key),
):
    """Manually check for and evaluate finished conversations"""
    try:
        from app.services.evaluations import evaluation_manager
        
        reports = evaluation_manager.check_and_evaluate_finished_conversations()
        
        evaluation_summaries = []
        for report in reports:
            evaluation_summaries.append({
                "session_id": report.session_id,
                "total_messages": report.total_messages,
                "conversation_duration_minutes": round(report.conversation_duration / 60, 2),
                "ragas_average": report.ragas_metrics.average_score if report.ragas_metrics else None,
                "phoenix_evaluations": len(report.phoenix_metrics),
                "drift_alert": report.drift_alert
            })
        
        return {
            "message": f"Evaluated {len(reports)} finished conversations",
            "evaluations_completed": len(reports),
            "evaluation_summaries": evaluation_summaries,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"Failed to check finished conversations: {e}")
        raise HTTPException(status_code=500, detail="Failed to check finished conversations")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0", 
        port=8000, 
        reload=True
    )