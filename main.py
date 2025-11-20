"""FastAPI entry point that wires endpoints, middleware, telemetry, and voice pipelines."""

import os
import asyncio
import time
import uuid
import logging
from contextlib import asynccontextmanager
from typing import Optional, Sequence, Any, Dict

from fastapi import (
    FastAPI,
    File,
    UploadFile,
    HTTPException,
    Depends,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from pydantic import BaseModel
from app.helpers import extract_audio, sse_event, validate_audio_upload
from app.audio_utils import avg_abs_pcm16, pcm16_to_wav, wav_header_pcm16
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from app.config import get_settings
from app.config_validation import validate_settings
from app.deps import (
    verify_api_key,
    limiter,
    require_consent,
    extract_identity_from_token,
)
from app.services.langgraph_service import langgraph_service
from app.services.tts import synthesize_inworld_stream
from app.services import supabase as supabase_service
from app.services.audio_queue import get_audio_queue_manager, AudioSegment
from app.services.shared_services import shared_services
from app.services.emotional_guidance import build_emotion_guided_prompt
from app.services.memory import memory_manager, ConversationTurn
from app.tracing import setup_tracer
from dotenv import load_dotenv
from opentelemetry import trace

load_dotenv()

_START_TIME = time.perf_counter()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("sophia-backend")


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Middleware that enforces API-key authentication on every non-public HTTP route."""

    def __init__(self, app: FastAPI, public_paths: Sequence[str]):
        super().__init__(app)
        self.public_paths = public_paths or []

    def _is_public(self, path: str) -> bool:
        """Return True when request path matches a configured public route."""
        for pattern in self.public_paths:
            if pattern == "*":
                return True
            if pattern.endswith("/*"):
                prefix = pattern[:-2]
                if path.startswith(prefix):
                    return True
            if path == pattern:
                return True
            # Allow prefix-style matches without needing explicit wildcard
            if (
                pattern
                and pattern != "/"
                and path.startswith(pattern.rstrip("/") + "/")
            ):
                return True
        return False

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        if request.method == "OPTIONS":
            return await call_next(request)
        if self._is_public(request.url.path):
            return await call_next(request)
        authorization = request.headers.get("Authorization")
        try:
            verify_api_key(request=request, authorization=authorization)
        except HTTPException as exc:
            return JSONResponse(
                status_code=exc.status_code, content={"detail": exc.detail}
            )
        return await call_next(request)


settings = get_settings()
validate_settings(settings)

app = FastAPI(title=settings.APP_NAME)

setup_tracer(app, settings)
supabase_service.init_supabase(settings)

from app import chat as chat_service

# ==========================
# Live Mode: WebSocket Voice
# ==========================


async def _ws_send_json(ws: WebSocket, obj: dict) -> None:
    import json as _json

    await ws.send_text(_json.dumps(obj))


@app.websocket("/ws/voice")
async def ws_voice(websocket: WebSocket):
    """WebSocket pipeline with VAD-driven barge-in and queued audio playback."""

    api_key = websocket.query_params.get("token") or websocket.headers.get(
        "Authorization"
    )

    if api_key and not api_key.lower().startswith("bearer "):
        api_key = f"Bearer {api_key}"

    try:
        logger.info("🔑 Attempting to verify API key...")
        supabase_token = verify_api_key(authorization=api_key)
        logger.info("✅ API key verified successfully")
    except HTTPException as exc:
        logger.error(f"❌ API key verification failed: {exc.detail}")
        await websocket.close(code=1008, reason=exc.detail)
        return

    supabase_user_id, discord_id = extract_identity_from_token(supabase_token)

    logger.info(
        f"🔌 WebSocket /ws/voice request: discord_id={discord_id}, has_token={bool(api_key)}"
    )

    try:
        require_consent(
            request=None, discord_id=discord_id, supabase_token=supabase_token
        )
    except HTTPException as exc:
        await websocket.close(code=1008, reason=exc.detail)
        return

    logger.info("🎉 WebSocket connection accepted!")
    await websocket.accept()
    SAMPLE_RATE = 16000
    BYTES_PER_SEC = SAMPLE_RATE * 2  # pcm16 mono
    SILENCE_THRESHOLD = 300
    SILENCE_MS = 600
    SILENCE_BYTES = int(BYTES_PER_SEC * (SILENCE_MS / 1000.0))

    pcm_buffer = bytearray()
    last_voice_activity = time.time()
    in_speech = False
    utter_start_pos = 0
    last_final_text = ""
    last_reply_text = ""
    last_audio_url: Optional[str] = None

    session_id = str(uuid.uuid4())
    audio_queue = get_audio_queue_manager()
    manager = shared_services.get_session_turn_manager()
    metadata: Dict[str, Any] = {"endpoint": "/ws/voice"}
    if discord_id:
        metadata["discord_id"] = discord_id



    async def send_audio_callback(segment: AudioSegment):
        import base64 as _b64

        eos = bool(segment.metadata.get("eos"))
        turn_id = segment.metadata.get("turn_id")
        payload_bytes = segment.audio_data or b""
        mime = segment.mime_type or "audio/mpeg"

        if payload_bytes:
            has_wav_header = payload_bytes[:4] == b"RIFF"
            if has_wav_header:
                mime = "audio/wav"
            elif mime in {"audio/pcm", "audio/x-raw"}:
                sample_rate = int(segment.metadata.get("sample_rate", 48000))
                payload_bytes = pcm16_to_wav(payload_bytes, sample_rate=sample_rate)
                mime = "audio/wav"

        b64_data = (
            _b64.b64encode(payload_bytes).decode("ascii") if payload_bytes else ""
        )
        await _ws_send_json(
            websocket,
            {
                "type": "audio_chunk",
                "mime": mime,
                "b64": b64_data,
                "eos": eos,
                "turn_id": turn_id,
            },
        )

    await audio_queue.start_playback(session_id, send_audio_callback)

    try:
        while True:
            msg = await websocket.receive()
            if "bytes" in msg and msg["bytes"] is not None:
                chunk: bytes = msg["bytes"]
                if not chunk:
                    continue
                pcm_buffer.extend(chunk)

                now = time.time()
                recent = (
                    pcm_buffer[-SILENCE_BYTES:]
                    if len(pcm_buffer) > SILENCE_BYTES
                    else pcm_buffer
                )
                amp = avg_abs_pcm16(recent)
                if amp > SILENCE_THRESHOLD:
                    if not in_speech:
                        in_speech = True
                        utter_start_pos = max(0, len(pcm_buffer) - len(recent))
                        barge_in_start = time.time()
                        active_turn = manager.get_active_turn(session_id)
                        interrupted_turn_id = (
                            active_turn.turn_id if active_turn else None
                        )
                        if interrupted_turn_id:
                            manager.request_cancel(turn_id=interrupted_turn_id)
                        current_cancelled, queue_cleared = audio_queue.cancel_all(
                            session_id
                        )
                        barge_in_ms = (time.time() - barge_in_start) * 1000
                        await _ws_send_json(
                            websocket,
                            {
                                "type": "barge_in",
                                "interruption_ms": barge_in_ms,
                                "cancelled": current_cancelled,
                                "cleared": queue_cleared,
                                "interrupted_turn_id": interrupted_turn_id,
                            },
                        )
                        if barge_in_ms > 200:
                            logger.warning(
                                f"WS Session {session_id}: barge-in interruption took {barge_in_ms:.2f}ms (>200ms budget)"
                            )
                    last_voice_activity = now
                    continue

                if in_speech and (now - last_voice_activity) * 1000.0 >= SILENCE_MS:
                    utter_bytes = bytes(pcm_buffer[utter_start_pos:])
                    wav_utter = wav_header_pcm16(len(utter_bytes) // 2) + utter_bytes
                    logger.info(
                        f"WS: endpoint detected; utterance bytes={len(utter_bytes)}"
                    )

                    async with manage_session_turn(
                        session_id, metadata=metadata
                    ) as turn_state:

                        def cancel_check():
                            manager.raise_if_cancelled(turn_state.turn_id)

                        reply_tokens: list[str] = []
                        tokens_sent = 0
                        turn_state.set_status("streaming")
                        try:
                            async for (
                                tok
                            ) in langgraph_service.stream_conversation_response(
                                wav_utter
                            ):
                                cancel_check()
                                if not tok:
                                    continue
                                # Check if this is tier-0 classification result
                                if isinstance(tok, dict) and tok.get("__tier0__"):
                                    await _ws_send_json(
                                        websocket, {"type": "tier0_result", **tok}
                                    )
                                    logger.info(
                                        f"📤 Sent tier-0 result to frontend: intent={tok.get('intent')}, emotion={tok.get('emotion')}"
                                    )
                                    continue
                                reply_tokens.append(tok)
                                await _ws_send_json(
                                    websocket,
                                    {
                                        "type": "token",
                                        "text": tok,
                                        "turn_id": turn_state.turn_id,
                                    },
                                )
                                tokens_sent += 1
                        except Exception as exc:
                            logger.warning(f"WS: LangGraph streaming failed: {exc}")

                        if tokens_sent == 0:
                            fallback_response = "I'm here to help with DeFi questions. Could you please repeat your question?"
                            for i in range(0, len(fallback_response), 8):
                                chunk_text = fallback_response[i : i + 8]
                                reply_tokens.append(chunk_text)
                                await _ws_send_json(
                                    websocket,
                                    {
                                        "type": "token",
                                        "text": chunk_text,
                                        "turn_id": turn_state.turn_id,
                                    },
                                )
                                tokens_sent += 1

                        reply_full = "".join(reply_tokens).strip() or "Okay."
                        await _ws_send_json(
                            websocket,
                            {
                                "type": "reply_done",
                                "text": reply_full,
                                "turn_id": turn_state.turn_id,
                            },
                        )

                        import re

                        turn_state.set_status("synthesizing")
                        sentences = [
                            s.strip()
                            for s in re.split(r"(?<=[\.!?])\s+", reply_full)
                            if s.strip()
                        ]
                        audio_url_last = None
                        for idx, sent in enumerate(sentences):
                            streamed_any = False
                            try:
                                for pcm_chunk in chat_service.synthesize_streamed_reply(sent, 48000, cancel_check):
                                    streamed_any = True
                                    await audio_queue.enqueue(
                                        session_id=session_id,
                                        audio_data=pcm_chunk,
                                        mime_type="audio/pcm",
                                        metadata={
                                            "turn_id": turn_state.turn_id,
                                            "sentence": sent,
                                            "chunk_index": idx,
                                            "eos": False,
                                            "sample_rate": 48000,
                                        },
                                    )
                            except Exception:
                                logger.exception(
                                    "WS: streaming TTS failed; falling back to full synthesis"
                                )

                            if not streamed_any:
                                try:
                                    audio_bytes, audio_url_last = chat_service.synthesize_reply(
                                        sent, cancel_check
                                    )
                                    cancel_check()
                                    await audio_queue.enqueue(
                                        session_id=session_id,
                                        audio_data=audio_bytes,
                                        mime_type="audio/mpeg",
                                        metadata={
                                            "turn_id": turn_state.turn_id,
                                            "sentence": sent,
                                            "chunk_index": idx,
                                            "eos": False,
                                        },
                                    )
                                    await _ws_send_json(
                                        websocket,
                                        {
                                            "type": "audio_url_chunk",
                                            "audio_url": audio_url_last,
                                            "turn_id": turn_state.turn_id,
                                        },
                                    )
                                except Exception:
                                    logger.exception(
                                        "WS: fallback TTS synthesis failed"
                                    )

                        await audio_queue.enqueue(
                            session_id=session_id,
                            audio_data=b"",
                            mime_type="audio/pcm",
                            metadata={
                                "turn_id": turn_state.turn_id,
                                "eos": True,
                                "sample_rate": 48000,
                            },
                        )
                        if audio_url_last is None:
                            try:
                                cancel_check()
                                audio_bytes, audio_url_last = chat_service.synthesize_reply(
                                    reply_full, cancel_check=cancel_check
                                )
                            except asyncio.CancelledError:
                                raise
                            except Exception:
                                logger.warning(
                                    "WS: failed to synthesize/upload archival audio for reply"
                                )

                        await _ws_send_json(
                            websocket,
                            {
                                "type": "audio_url",
                                "audio_url": audio_url_last,
                                "turn_id": turn_state.turn_id,
                            },
                        )

                        last_final_text = f"[Audio processed: {len(utter_bytes)} bytes]"
                        last_reply_text = reply_full
                        last_audio_url = audio_url_last
                        turn_state.set_status("completed")

                    pcm_buffer.clear()
                    in_speech = False
                    last_voice_activity = now
            elif msg.get("type") == "websocket.disconnect":
                break
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        await _ws_send_json(websocket, {"type": "error", "detail": str(exc)})
        try:
            await websocket.close()
        except Exception:
            pass
    finally:
        try:
            stats = audio_queue.get_stats(session_id)
            if stats:
                logger.info(
                    f"WS Session {session_id}: stats played={stats.segments_played}, "
                    f"cancelled={stats.segments_cancelled}, "
                    f"total_cancellations={stats.total_cancellations}, "
                    f"last_interrupt_ms={stats.last_interruption_ms}"
                )
            await audio_queue.cleanup_session(session_id)
        except Exception as exc:
            logger.warning(f"WS Session {session_id}: cleanup error: {exc}")

    try:
        if last_final_text or last_reply_text:
            supabase_service.insert_conversation_session(
                {
                    "transcript": last_final_text,
                    "reply": last_reply_text,
                    "audio_url": last_audio_url or None,
                    "user_id": supabase_user_id,
                },
                access_token=supabase_token,
            )
    except Exception:
        pass


@asynccontextmanager
async def manage_session_turn(
    session_id: str, *, metadata: Optional[Dict[str, Any]] = None
):
    """Acquire a per-session turn and ensure it is released safely."""
    manager = shared_services.get_session_turn_manager()
    state = await manager.start_turn(session_id, metadata=metadata)
    try:
        yield state
        if manager.get_turn(state.turn_id) is not None:
            await manager.finish_turn(state.turn_id, status="completed")
    except asyncio.CancelledError:
        if manager.get_turn(state.turn_id) is not None:
            await manager.finish_turn(state.turn_id, status="cancelled")
        raise
    except Exception as exc:
        if manager.get_turn(state.turn_id) is not None:
            await manager.fail_turn(state.turn_id, exc)
        raise

app.add_middleware(APIKeyMiddleware, public_paths=settings.API_PUBLIC_PATHS)

allowed_cors_origins = settings.CORS_ALLOWED_ORIGINS or ["http://localhost:3000"]
logger.info("Configuring CORS for allowed origins: %s", allowed_cors_origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "Origin",
        "X-Requested-With",
        "X-Api-Key",
    ],
    expose_headers=["Authorization"],
    max_age=86400,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Mount static files for frontend (only if frontend directory exists)
# In backend-only deployment (Render), frontend is served separately by Vercel

if os.path.exists("frontend"):
    app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")
    logger.info("Frontend static files mounted at /frontend")
else:
    logger.info(
        "Frontend directory not found - running in backend-only mode (frontend served by Vercel)"
    )

logger.info(
    "Startup initialization completed in %.2f s", time.perf_counter() - _START_TIME
)

# Simple health endpoint for Fly.io checks and container orchestration
@app.get("/health")
def health():
    return {"status": "ok"}


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
    response_path: Optional[str] = None
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
def root(request: Request):
    """Backend status with optional static frontend response."""
    accepts = request.headers.get("accept", "")
    if "text/html" in accepts.lower() and os.path.exists("frontend/index.html"):
        # Full-stack deployment: serve frontend to browser clients requesting HTML
        return FileResponse("frontend/index.html")

    # Backend-only deployment: return API info (default for API clients/tests)
    return {
        "message": "Sophia AI Backend is running",
        "frontend_url": "https://sophia-1st-mvp-git-main-davidelavergas-projects.vercel.app",
        "api_status": "ok",
        "deployment_mode": "backend+api"
        if os.path.exists("frontend/index.html")
        else "backend-only",
        "docs_url": "/docs",
    }

@app.get("/api")
def api_root():
    """API status endpoint"""
    return {"message": "Sophia AI Backend with DeFi Agent is running."}


@app.post("/transcribe", response_model=TranscriptionResponse)
@limiter.limit(settings.API_RATE_LIMIT)
async def transcribe(
    request: Request,
    file: UploadFile = File(...),
    supabase_token: str = Depends(verify_api_key),
):
    validate_audio_upload(file)
    wav_bytes = await extract_audio(file)

    session_id = uuid.uuid4()

    text = chat_service.transcript_audio(wav_bytes)
    user_emotion, _ = chat_service.analyze_emotion_by_audio(wav_bytes, role="user")
    supabase_user_id, _ = extract_identity_from_token(supabase_token)

    try:
        supabase_service.insert_emotion_score(
            session_id,
            role="user",
            emotion=user_emotion,
            user_id=supabase_user_id,
            access_token=supabase_token,
        )
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
    supabase_token: str = Depends(verify_api_key),
):
    reply = chat_service.generate_llm_reply(body.text)
    return GenerateResponse(reply=reply, tone="encouraging")


@app.post("/generate-response/stream")
@limiter.limit(settings.API_RATE_LIMIT)
async def generate_response_stream(
    request: Request,
    body: GenerateRequest,
    supabase_token: str = Depends(verify_api_key),
):
    """Stream LLM tokens as they are generated.

    Returns plain text chunks; the client should append them to display the
    streaming answer. This endpoint is ideal for chat UIs that want low-latency
    first token and incremental updates.
    """
    try:
        generator = chat_service.generate_streamed_llm_reply(body.text)
        return StreamingResponse(generator, media_type="text/plain")
    except Exception:
        logger.exception("Streaming response generation failed")
        raise HTTPException(
            status_code=500, detail="Streaming response generation failed"
        )


class SynthesizeRequest(BaseModel):
    text: str


@app.post("/synthesize", response_model=SynthesizeResponse)
@limiter.limit(settings.API_RATE_LIMIT)
async def synthesize(
    request: Request,
    body: SynthesizeRequest,
    supabase_token: str = Depends(verify_api_key),
    ):
    supabase_user_id, _ = extract_identity_from_token(supabase_token)

    audio_bytes, audio_url = chat_service.synthesize_reply(body.text)
    sophia_emotion, _ = chat_service.analyze_emotion_by_audio(
        audio_bytes, role="sophia"
    )

    try:
        session_id = uuid.uuid4()
        supabase_service.insert_emotion_score(
            session_id,
            role="sophia",
            emotion=sophia_emotion,
            user_id=supabase_user_id,
            access_token=supabase_token,
        )
    except Exception:
        logger.warning("Failed to persist sophia emotion score; continuing")

    return SynthesizeResponse(audio_url=audio_url, emotion=sophia_emotion.model_dump())


@app.post("/chat", response_model=ChatResponse)
@limiter.limit(settings.API_RATE_LIMIT)
async def chat(
    request: Request,
    file: UploadFile = File(...),
    supabase_token: str = Depends(verify_api_key),
    consent_ok: None = Depends(require_consent),
):
    validate_audio_upload(file)
    wav_bytes = await extract_audio(file)

    supabase_user_id, discord_id = extract_identity_from_token(supabase_token)
    manager = shared_services.get_session_turn_manager()

    session_uuid = uuid.uuid4()
    session_id_str = str(session_uuid)
    metadata: Dict[str, Any] = {"endpoint": "/chat"}
    if discord_id:
        metadata["discord_id"] = discord_id

    async with manage_session_turn(session_id_str, metadata=metadata) as turn_state:

        def cancel_check():
            manager.raise_if_cancelled(turn_state.turn_id)

        current_span = trace.get_current_span()
        current_span.set_attribute("session.id", session_id_str)
        t0 = time.time()

        transcript = chat_service.transcript_audio(wav_bytes, cancel_check)

        cancel_check()

        user_emotion, _ = chat_service.analyze_emotion_by_audio(
            wav_bytes, cancel_check, role="user"
        )

        turn_state.set_status("streaming")
        cancel_check()

        reply = chat_service.generate_llm_reply(transcript, cancel_check)

        turn_state.set_status("synthesizing")
        cancel_check()

        reply_audio_bytes, audio_url = chat_service.synthesize_reply(
            reply, cancel_check
        )

        sophia_emotion, _ = chat_service.analyze_emotion_by_audio(
            reply_audio_bytes, cancel_check, role="sophia"
        )

        total_ms = int((time.time() - t0) * 1000)
        current_span.set_attribute("total_roundtrip_time.ms", total_ms)
        current_span.set_attribute("phoenix_user_emotion.label", user_emotion.label)
        current_span.set_attribute(
            "phoenix_user_emotion.confidence", float(user_emotion.confidence)
        )
        current_span.set_attribute("phoenix_sophia_emotion.label", sophia_emotion.label)
        current_span.set_attribute(
            "phoenix_sophia_emotion.confidence", float(sophia_emotion.confidence)
        )

        chat_service.persist_conversation_session(
            session_id=session_uuid,
            transcript=transcript,
            reply=reply,
            user_emotion=user_emotion,
            sophia_emotion=sophia_emotion,
            reply_audio_url=audio_url,
            user_id=supabase_user_id,
            supabase_token=supabase_token
        )

        turn_state.set_status("completed")
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
    supabase_token: str = Depends(verify_api_key),
    consent_ok: None = Depends(require_consent),
):
    validate_audio_upload(file)
    wav_bytes = await extract_audio(file)

    user_id, discord_id = extract_identity_from_token(supabase_token)

    session_identifier = session_id or str(uuid.uuid4())
    metadata: Dict[str, Any] = {"endpoint": "/defi-chat"}
    if session_id:
        metadata["provided_session_id"] = session_id
    if discord_id:
        metadata["discord_id"] = discord_id
    manager = shared_services.get_session_turn_manager()

    async with manage_session_turn(session_identifier, metadata=metadata) as turn_state:

        def cancel_check():
            manager.raise_if_cancelled(turn_state.turn_id)

        try:
            cancel_check()

            turn_state.set_status("streaming")
            cancel_check()
            result = langgraph_service.process_conversation(
                audio_bytes=wav_bytes,
                session_id=session_identifier,
                collect_evaluation_data=True,
                supabase_token=supabase_token,
                cancel_check=cancel_check,
            )

            turn_state.set_status("synthesizing")
            cancel_check()

            chat_service.persist_conversation_session(
                supabase_token=supabase_token,
                user_id=user_id,
                session_id=result['session_id'],
                transcript=result['transcript'],
                reply=result['reply'],
                user_emotion=Emotion(
                    label=result['user_emotion']['label'],
                    confidence=result['user_emotion']['confidence']
                ),
                sophia_emotion=Emotion(
                    label=result['sophia_emotion']['label'],
                    confidence=result['sophia_emotion']['confidence']
                ),
                reply_audio_url=result.get('audio_url'),
                intent=result['intent'],
                context_memory=str(result['context_memory'])
            )

            turn_state.set_status("completed")
            return DefiChatResponse(**result)

        except asyncio.CancelledError:
            logger.info("DeFi chat turn %s cancelled", turn_state.turn_id)
            raise
        except Exception as e:
            logger.exception("DeFi chat processing failed")
            raise HTTPException(
                status_code=500, detail=f"DeFi chat processing failed: {str(e)}"
            )


@app.post("/defi-chat/stream")
@limiter.limit(settings.API_RATE_LIMIT)
async def defi_chat_stream(
    request: Request,
    file: UploadFile = File(...),
    session_id: Optional[str] = None,
    supabase_token: str = Depends(verify_api_key),
    consent_ok: None = Depends(require_consent),
):
    """Streaming variant of DeFi chat.

    Server-Sent Events (SSE) stream with events:
    - event: transcript, data: { transcript, user_emotion }
    - event: token, data: <text chunk>
    - event: reply_done, data: { reply }
    - event: audio_url, data: { audio_url, sophia_emotion }
    """
    validate_audio_upload(file)
    wav_bytes = await extract_audio(file)

    user_id, discord_id = extract_identity_from_token(supabase_token)
    session_identifier = session_id or str(uuid.uuid4())
    metadata: Dict[str, Any] = {"endpoint": "/defi-chat/stream"}
    if session_identifier:
        metadata["provided_session_id"] = session_identifier
    if discord_id:
        metadata["discord_id"] = discord_id
    manager = shared_services.get_session_turn_manager()
    # IMPORTANT: Read the uploaded file BEFORE starting the generator.
    # Starlette may close the underlying SpooledTemporaryFile once the coroutine
    # returns control, which would make subsequent reads fail within the
    # generator with "I/O operation on closed file".

    async def event_generator():
        nonlocal session_identifier
        async with manage_session_turn(
            session_identifier, metadata=metadata
        ) as turn_state:

            def cancel_check():
                manager.raise_if_cancelled(turn_state.turn_id)

            try:
                cancel_check()
                transcript = chat_service.transcript_audio(wav_bytes, cancel_check)
                cancel_check()
                user_emotion, _ = chat_service.analyze_emotion_by_audio(
                    wav_bytes, cancel_check, role="user"
                )

                yield sse_event(
                    'transcript',
                    {'transcript': transcript, 'user_emotion': user_emotion.model_dump(), 'session_id': session_id_local}
                )

                turn_state.set_status("streaming")
                reply_accum = []
                for chunk in chat_service.generate_streamed_llm_reply(
                    transcript,
                    cancel_check=cancel_check,
                ):
                    reply_accum.append(chunk)
                    safe_chunk = chunk.replace("\n", " ")
                    yield sse_event('token', safe_chunk)

                reply = "".join(reply_accum).strip()
                yield sse_event('reply_done', { 'reply': reply })

                turn_state.set_status("synthesizing")
                cancel_check()

                audio_bytes, audio_url = chat_service.synthesize_reply(reply, cancel_check)

                cancel_check()
                sophia_emotion, mock_audio = chat_service.analyze_emotion_by_audio(
                    audio_bytes, cancel_check, role="sophia"
                )

                cancel_check()
                chat_service.persist_conversation_session(
                    session_id=session_id,
                    transcript=transcript,
                    reply=reply,
                    user_emotion=user_emotion,
                    sophia_emotion=sophia_emotion,
                    reply_audio_url=audio_url,
                    user_id=user_id,
                    supabase_token=supabase_token
                )

                turn_state.set_status("completed")

                payload = {
                    "audio_url": audio_url,
                    "sophia_emotion": (
                        sophia_emotion.model_dump() if sophia_emotion else None
                    ),
                    "mock_audio": mock_audio,
                }
                yield sse_event('audio_url', payload)

            except asyncio.CancelledError:
                logger.info("Streaming DeFi chat turn %s cancelled", turn_state.turn_id)
                raise
            except Exception as e:
                logger.exception("Streaming DeFi chat failed")
                yield sse_event('error', {"detail": str(e)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

@app.post("/text-chat", response_model=DefiChatResponse)
@limiter.limit(settings.API_RATE_LIMIT)
async def text_chat(
    request: Request,
    body: TextChatRequest,
    supabase_token: str = Depends(verify_api_key),
    consent_ok: None = Depends(require_consent),
):
    """Text-only chat endpoint for DeFi conversations"""
    user_id, discord_id = extract_identity_from_token(supabase_token)

    session_identifier = body.session_id or str(uuid.uuid4())
    metadata: Dict[str, Any] = {"endpoint": "/text-chat"}
    if body.session_id:
        metadata["provided_session_id"] = body.session_id
    if discord_id:
        metadata["discord_id"] = discord_id

    manager = shared_services.get_session_turn_manager()

    async with manage_session_turn(session_identifier, metadata=metadata) as turn_state:

        def cancel_check():
            manager.raise_if_cancelled(turn_state.turn_id)

        try:
            turn_state.set_status("streaming")
            cancel_check()
            result = langgraph_service.process_text_conversation(
                message=body.message,
                session_id=session_identifier,
                collect_evaluation_data=True,
                supabase_token=supabase_token,
                cancel_check=cancel_check,
            )

            turn_state.set_status("synthesizing")
            cancel_check()

            chat_service.persist_conversation_session(
                supabase_token=supabase_token,
                user_id=user_id,
                session_id=result['session_id'],
                transcript=result['transcript'],
                reply=result['reply'],
                user_emotion=Emotion(
                    label=result['user_emotion']['label'],
                    confidence=result['user_emotion']['confidence']
                ),
                sophia_emotion=Emotion(
                    label=result['sophia_emotion']['label'],
                    confidence=result['sophia_emotion']['confidence']
                ),
                reply_audio_url=result.get('audio_url'),
                intent=result['intent'],
                context_memory=str(result['context_memory'])
            )

            turn_state.set_status("completed")
            return DefiChatResponse(**result)

        except asyncio.CancelledError:
            logger.info("Text chat turn %s cancelled", turn_state.turn_id)
            raise
        except Exception as e:
            logger.exception("Text chat processing failed")
            raise HTTPException(
                status_code=500, detail=f"Text chat processing failed: {str(e)}"
            )


def _format_memory_context_for_prompt(context: Optional[Dict[str, Any]]) -> str:
    if not context:
        return ""

    parts: list[str] = []
    topics = context.get("last_topics") or []
    if topics:
        parts.append(f"Recent topics: {', '.join(topics)}")

    tone = context.get("last_user_tone")
    if tone:
        parts.append(f"Previous user tone: {tone}")

    intents = context.get("recent_intents") or []
    if intents:
        parts.append(f"Recent intents: {', '.join(intents)}")

    recent_turns = context.get("recent_turns") or []
    if recent_turns:
        snippet_lines: list[str] = [
            "Conversation so far (use for context only; do not repeat lines verbatim):"
        ]
        for turn in recent_turns[-3:]:
            user_line = (turn.get("user") or "").strip()
            sophia_line = (turn.get("sophia") or "").strip()
            if user_line:
                snippet_lines.append(f"User: {user_line}")
            if sophia_line:
                snippet_lines.append(f"Sophia: {sophia_line}")
        if len(snippet_lines) > 1:
            parts.append("\n".join(snippet_lines))

    return "\n".join(parts)


def _record_text_stream_turn(
    session_id: str,
    user_text: str,
    reply: str,
    user_emotion: Dict[str, Any],
    sophia_emotion: Optional[Emotion],
    supabase_token: Optional[str],
):
    try:
        turn = ConversationTurn(
            query=user_text,
            response=reply,
            user_emotion=user_emotion.get("label") or "neutral",
            sophia_emotion=getattr(sophia_emotion, "label", "neutral"),
            intent="text_chat",
            timestamp=time.time(),
        )
        memory_manager.update_session_memory(
            session_id, turn, access_token=supabase_token
        )
    except Exception as exc:
        logger.warning("Text chat stream memory update failed: %s", exc)


@app.post("/text-chat/stream")
@limiter.limit(settings.API_RATE_LIMIT)
async def text_chat_stream(
    request: Request,
    body: TextChatRequest,
    supabase_token: str = Depends(verify_api_key),
    consent_ok: None = Depends(require_consent),
):
    """Streaming variant for text-only chat.

    Server-Sent Events (SSE) with:
    - event: token, data: <text chunk>
    - event: reply_done, data: { reply }
    - event: audio_url, data: { audio_url, sophia_emotion }
    """
    user_id, discord_id = extract_identity_from_token(supabase_token)
    session_identifier = body.session_id or str(uuid.uuid4())
    metadata: Dict[str, Any] = {"endpoint": "/text-chat/stream"}
    if body.session_id:
        metadata["provided_session_id"] = body.session_id
    if discord_id:
        metadata["discord_id"] = discord_id
    manager = shared_services.get_session_turn_manager()

    async def event_generator():
        async with manage_session_turn(
            session_identifier, metadata=metadata
        ) as turn_state:

            def cancel_check():
                manager.raise_if_cancelled(turn_state.turn_id)

            try:

                user_emotion: Emotion = chat_service.analyze_emotion_by_text(body.message)

                emotion_guidance: Sequence[str] = chat_service.get_emotional_guidance(user_emotion)
                if emotion_guidance:
                    preview = "; ".join(emotion_guidance[:2])
                    logger.info(
                        "Text chat stream guidance for %s: %s%s",
                        user_emotion.label,
                        preview,
                        "..." if len(emotion_guidance) > 2 else "",
                    )

                memory_context_text = ""
                try:
                    flash_context = memory_manager.get_context_for_llm(
                        session_identifier, access_token=supabase_token
                    )
                    memory_context_text = _format_memory_context_for_prompt(
                        flash_context
                    )
                except Exception as context_error:
                    logger.warning(
                        "Text chat stream memory lookup failed: %s", context_error
                    )
                    memory_context_text = ""

                guided_prompt = build_emotion_guided_prompt(
                    body.message,
                    user_emotion.label,
                    float(user_emotion.confidence),
                    emotion_guidance,
                    conversation_context=memory_context_text,
                )

                turn_state.set_status("streaming")
                reply_accum = []
                for chunk in chat_service.generate_streamed_llm_reply(
                    guided_prompt,
                    cancel_check=cancel_check,
                ):
                    reply_accum.append(chunk)
                    safe_chunk = chunk.replace("\n", " ")
                    yield sse_event('token', safe_chunk)

                reply = "".join(reply_accum).strip()
                reply_payload = {"reply": reply, "user_emotion": user_emotion.model_dump()}
                yield sse_event('reply_done', reply_payload)

                turn_state.set_status("synthesizing")
                cancel_check()

                audio_bytes, audio_url = chat_service.synthesize_reply(reply, cancel_check)
                cancel_check()
                sophia_emotion, mock_audio = chat_service.analyze_emotion_by_audio(
                    audio_bytes, cancel_check, role="sophia"
                )

                payload = {
                    "audio_url": audio_url,
                    "sophia_emotion": (
                        sophia_emotion.model_dump() if sophia_emotion else None
                    ),
                    "mock_audio": mock_audio,
                    "user_emotion": user_emotion.model_dump(),
                }

                _record_text_stream_turn(
                    session_identifier,
                    body.message,
                    reply,
                    user_emotion.model_dump(),
                    sophia_emotion,
                    supabase_token,
                )
                turn_state.set_status("completed")
                yield sse_event('audio_url', payload)

            except asyncio.CancelledError:
                logger.info("Streaming text chat turn %s cancelled", turn_state.turn_id)
                raise
            except Exception as e:
                logger.exception("Streaming text chat failed")
                yield sse_event('error', {"detail": str(e)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/status")
def status_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": int(time.time())}


@app.get("/memory/{session_id}")
async def get_memory(
    session_id: str,
    supabase_token: str = Depends(verify_api_key),
):
    """Get conversation memory for a session"""
    try:
        context = memory_manager.get_context_for_llm(
            session_id, access_token=supabase_token
        )

        return {"session_id": session_id, "context": context, "timestamp": time.time()}

    except Exception as e:
        logger.error(f"Failed to get memory for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve memory")


@app.post("/evaluation/force/{session_id}")
async def force_evaluate_conversation(
    session_id: str,
    supabase_token: str = Depends(verify_api_key),
):
    """Force evaluation of a specific conversation"""
    try:
        from app.services.evaluations import evaluation_manager

        report = evaluation_manager.force_evaluate_conversation(session_id)

        if report is None:
            raise HTTPException(
                status_code=404,
                detail=f"No active conversation found for session {session_id}",
            )

        return {
            "message": "Conversation evaluation completed",
            "session_id": session_id,
            "evaluation_report": {
                "total_messages": report.total_messages,
                "conversation_duration_minutes": round(
                    report.conversation_duration / 60, 2
                ),
                "ragas_average": report.ragas_metrics.average_score
                if report.ragas_metrics
                else None,
                "phoenix_evaluations": len(report.phoenix_metrics),
                "drift_alert": report.drift_alert,
                "confidence_change": f"{report.baseline_confidence:.2f} -> {report.current_confidence:.2f}",
            },
            "timestamp": time.time(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to force evaluate conversation {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to evaluate conversation")


@app.get("/evaluation/status")
async def get_evaluation_status(
    supabase_token: str = Depends(verify_api_key),
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
            "conversation_timeout_minutes": evaluation_manager.conversation_timeout
            / 60,
            "timestamp": time.time(),
        }

    except Exception as e:
        logger.error(f"Failed to get evaluation status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get evaluation status")


@app.post("/evaluation/check-finished")
async def check_finished_conversations(
    supabase_token: str = Depends(verify_api_key),
):
    """Manually check for and evaluate finished conversations"""
    try:
        from app.services.evaluations import evaluation_manager

        reports = evaluation_manager.check_and_evaluate_finished_conversations()

        evaluation_summaries = []
        for report in reports:
            evaluation_summaries.append(
                {
                    "session_id": report.session_id,
                    "total_messages": report.total_messages,
                    "conversation_duration_minutes": round(
                        report.conversation_duration / 60, 2
                    ),
                    "ragas_average": report.ragas_metrics.average_score
                    if report.ragas_metrics
                    else None,
                    "phoenix_evaluations": len(report.phoenix_metrics),
                    "drift_alert": report.drift_alert,
                }
            )

        return {
            "message": f"Evaluated {len(reports)} finished conversations",
            "evaluations_completed": len(reports),
            "evaluation_summaries": evaluation_summaries,
            "timestamp": time.time(),
        }

    except Exception as e:
        logger.error(f"Failed to check finished conversations: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to check finished conversations"
        )


@app.post("/admin/reload-prompts")
async def reload_prompts(
    supabase_token: str = Depends(verify_api_key),
):
    """Hot reload system prompts from disk (Task #42597)"""
    try:
        from app.services.prompt_composer import prompt_composer

        success = prompt_composer.reload_prompts()
        status = prompt_composer.get_reload_status()

        if success:
            return {
                "message": "Prompts reloaded successfully",
                "status": status,
                "timestamp": time.time(),
            }
        else:
            return JSONResponse(
                status_code=500,
                content={
                    "message": "Prompts reload failed or incomplete",
                    "status": status,
                    "timestamp": time.time(),
                },
            )

    except Exception as e:
        logger.error(f"Failed to reload prompts: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to reload prompts: {str(e)}"
        )


@app.get("/admin/memo-metrics")
async def get_memo_metrics(
    supabase_token: str = Depends(verify_api_key),
):
    """Get MemO performance metrics (Task #42597)"""
    try:
        from app.services.memo import memo_client

        metrics = memo_client.get_metrics()

        return {
            "memo_enabled": memo_client.enabled,
            "metrics": metrics,
            "timestamp": time.time(),
        }

    except Exception as e:
        logger.error(f"Failed to get MemO metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")


@app.post("/admin/run-migration")
async def run_migration(
    supabase_token: str = Depends(verify_api_key),
):
    """Run user_memories table migration (Task #42597)"""
    try:
        import psycopg
        from pathlib import Path

        migration_file = Path("user_memories_migration.sql")
        if not migration_file.exists():
            raise HTTPException(status_code=404, detail="Migration file not found")

        # Read migration SQL
        with open(migration_file, "r") as f:
            migration_sql = f.read()

        # Get DB connection string from settings
        settings = get_settings()
        db_dsn = settings.SUPABASE_DB_DSN

        if not db_dsn:
            raise HTTPException(
                status_code=500, detail="SUPABASE_DB_DSN not configured"
            )

        # Execute migration
        conn = psycopg.connect(db_dsn)
        cursor = conn.cursor()

        try:
            cursor.execute(migration_sql)
            conn.commit()

            # Verify table exists
            cursor.execute(
                "SELECT tablename FROM pg_tables WHERE tablename = 'user_memories'"
            )
            result = cursor.fetchone()

            if result:
                # Get table structure
                cursor.execute("""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_name = 'user_memories'
                    ORDER BY ordinal_position
                """)
                columns = cursor.fetchall()

                return {
                    "message": "Migration executed successfully",
                    "table_exists": True,
                    "columns": [{"name": col[0], "type": col[1]} for col in columns],
                    "timestamp": time.time(),
                }
            else:
                return {
                    "message": "Migration executed but table not found",
                    "table_exists": False,
                    "timestamp": time.time(),
                }

        except Exception as e:
            conn.rollback()
            error_str = str(e).lower()
            if "already exists" in error_str:
                return {
                    "message": "Migration already applied (table exists)",
                    "table_exists": True,
                    "timestamp": time.time(),
                }
            else:
                raise

        finally:
            cursor.close()
            conn.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to run migration: {e}")
        raise HTTPException(status_code=500, detail=f"Migration failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
