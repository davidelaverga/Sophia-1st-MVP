import base64
import io
import time
import uuid
import logging
from typing import Optional

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Header, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import get_settings
from app.deps import verify_api_key, limiter
from app.services.mistral import (
    transcribe_audio_with_voxtral,
    generate_llm_reply,
    stream_generate_llm_reply,
    generate_reply_from_audio,
)
from app.services.emotion import analyze_emotion_text, analyze_emotion_audio
from app.services.tts import synthesize_inworld, synthesize_inworld_stream
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
    "deployment.environment": "staging",
})


def _normalize_otlp_endpoint(ep: str | None) -> str | None:
    if not ep:
        return None
    ep = ep.rstrip("/")
    # If caller passed base gateway (e.g., https://otlp-gateway.grafana.net/otlp),
    # add the traces path expected by the HTTP exporter.
    if not ep.endswith("/v1/traces"):
        # Common Grafana endpoints end in "/otlp". Either way, append the traces path cleanly.
        return f"{ep}/v1/traces"
    return ep


def _parse_otlp_headers(hdrs: str | None) -> dict[str, str] | None:
    if not hdrs:
        return None
    # Support comma-separated key=value pairs, e.g. "Authorization=Bearer abc, X-Org=123"
    out: dict[str, str] = {}
    for part in hdrs.split(","):
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip()] = v.strip()
    return out or None


provider = TracerProvider(resource=resource)

# Configure OTLP HTTP exporter for Grafana Cloud (or any OTLP endpoint) via env
otlp_endpoint = _normalize_otlp_endpoint(settings.OTEL_EXPORTER_OTLP_ENDPOINT)
otlp_headers = _parse_otlp_headers(settings.OTEL_EXPORTER_OTLP_HEADERS)

# Only enable exporter if explicitly configured to avoid connection errors to localhost
if otlp_endpoint:
    otlp_exporter = OTLPSpanExporter(
        endpoint=otlp_endpoint,
        headers=otlp_headers,
    )
    provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
else:
    # No exporter configured; traces will be kept in-process only
    pass

trace.set_tracer_provider(provider)
tracer = trace.get_tracer("sophia")

# Auto-instrument FastAPI
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


@app.post("/generate-response/stream")
@limiter.limit(settings.API_RATE_LIMIT)
async def generate_response_stream(
    request: Request,
    body: GenerateRequest,
    api_key_ok: None = Depends(verify_api_key),
):
    """Stream LLM tokens as they are generated.

    Returns plain text chunks; the client should append them to display the
    streaming answer. This endpoint is ideal for chat UIs that want low-latency
    first token and incremental updates.
    """
    try:
        generator = stream_generate_llm_reply(body.text)
        return StreamingResponse(generator, media_type="text/plain")
    except Exception:
        logger.exception("Streaming response generation failed")
        raise HTTPException(status_code=500, detail="Streaming response generation failed")


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
        # Defer emotion persistence until after conversation session is created to avoid FK issues

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
        # Defer emotion persistence until after conversation session is created to avoid FK issues

        total_ms = int((time.time() - t0) * 1000)
        chat_span.set_attribute("total_roundtrip_time.ms", total_ms)

    # Insert conversation first (let DB set timestamps), then emotion scores to satisfy FK
    try:
        insert_conversation_session({
            "id": str(session_id),
            "transcript": transcript,
            "reply": reply,
            "user_emotion_label": user_emotion.label,
            "user_emotion_confidence": user_emotion.confidence,
            "sophia_emotion_label": sophia_emotion.label,
            "sophia_emotion_confidence": sophia_emotion.confidence,
            "audio_url": audio_url or None,
        })
        try:
            insert_emotion_score(session_id, role="user", emotion=user_emotion)
        except Exception:
            logger.warning("Persist user emotion failed; continuing")
        try:
            insert_emotion_score(session_id, role="sophia", emotion=sophia_emotion)
        except Exception:
            logger.warning("Persist sophia emotion failed; continuing")
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
        
        # Store in Supabase (let DB set timestamps). Insert conversation first, then emotions.
        try:
            insert_conversation_session({
                "id": result["session_id"],
                "transcript": result["transcript"],
                "reply": result["reply"],
                "user_emotion_label": result["user_emotion"]["label"],
                "user_emotion_confidence": result["user_emotion"]["confidence"],
                "sophia_emotion_label": result["sophia_emotion"]["label"],
                "sophia_emotion_confidence": result["sophia_emotion"]["confidence"],
                "audio_url": result["audio_url"] or None,
                "intent": result["intent"],
                "context_memory": str(result["context_memory"]),
            })
            try:
                insert_emotion_score(result["session_id"], role="user", emotion=type("E", (), result["user_emotion"])())
            except Exception as e:
                logger.warning(f"Failed to persist user emotion: {e}")
            try:
                insert_emotion_score(result["session_id"], role="sophia", emotion=type("E", (), result["sophia_emotion"])())
            except Exception as e:
                logger.warning(f"Failed to persist sophia emotion: {e}")
        except Exception as e:
            logger.warning(f"Failed to persist conversation session: {e}")
        
        return DefiChatResponse(**result)
        
    except Exception as e:
        logger.exception("DeFi chat processing failed")
        raise HTTPException(status_code=500, detail=f"DeFi chat processing failed: {str(e)}")


@app.post("/defi-chat/stream")
@limiter.limit(settings.API_RATE_LIMIT)
async def defi_chat_stream(
    request: Request,
    file: UploadFile = File(...),
    session_id: Optional[str] = None,
    api_key_ok: None = Depends(verify_api_key),
):
    """Streaming variant of DeFi chat.

    Server-Sent Events (SSE) stream with events:
    - event: transcript, data: { transcript, user_emotion }
    - event: token, data: <text chunk>
    - event: reply_done, data: { reply }
    - event: audio_url, data: { audio_url, sophia_emotion }
    """
    # IMPORTANT: Read the uploaded file BEFORE starting the generator.
    # Starlette may close the underlying SpooledTemporaryFile once the coroutine
    # returns control, which would make subsequent reads fail within the
    # generator with "I/O operation on closed file".
    wav_bytes = await file.read()

    async def event_generator():
        nonlocal session_id
        try:
            # STT
            transcript = transcribe_audio_with_voxtral(wav_bytes)
            user_emotion = analyze_emotion_audio(wav_bytes)
            if session_id is None:
                session_id_local = str(uuid.uuid4())
                session_id = session_id_local
            else:
                session_id_local = session_id
            # Do NOT persist emotions yet; insert conversation first to satisfy FK

            # Send transcript event
            import json as _json
            yield f"event: transcript\ndata: {_json.dumps({'transcript': transcript, 'user_emotion': user_emotion.model_dump(), 'session_id': session_id_local})}\n\n"

            # Stream LLM
            reply_accum = []
            for chunk in stream_generate_llm_reply(transcript):
                if not chunk:
                    continue
                reply_accum.append(chunk)
                # stream token chunk
                safe_chunk = chunk.replace("\n", " ")
                yield f"event: token\ndata: {safe_chunk}\n\n"

            reply = "".join(reply_accum).strip()
            yield f"event: reply_done\ndata: {{\"reply\": { _json.dumps(reply) }}}\n\n"

            # Synthesize TTS and upload
            try:
                audio_bytes = synthesize_inworld(reply)
                file_name = f"sophia_{int(time.time()*1000)}.mp3"
                audio_url = upload_audio_and_get_url(audio_bytes, file_name)
            except Exception:
                logger.exception("Synthesis or upload failed in defi_chat_stream")
                audio_url = None

            # Analyze Sophia emotion (persist later after conversation insert)
            sophia_emotion = None
            mock_audio = False
            try:
                if audio_url:
                    # Detect mock audio (tiny placeholder)
                    try:
                        mock_audio = audio_bytes.startswith(b"ID3mock") or len(audio_bytes) < 2048
                    except Exception:
                        mock_audio = False
                    sophia_emotion = analyze_emotion_audio(audio_bytes)
            except Exception:
                logger.warning("Sophia emotion analysis failed; continuing")

            # Persist conversation first (no explicit created_at), then emotions to satisfy FK
            try:
                insert_conversation_session({
                    "id": session_id_local,
                    "transcript": transcript,
                    "reply": reply,
                    "user_emotion_label": user_emotion.label,
                    "user_emotion_confidence": user_emotion.confidence,
                    "sophia_emotion_label": (sophia_emotion.label if sophia_emotion else None),
                    "sophia_emotion_confidence": (sophia_emotion.confidence if sophia_emotion else None),
                    "audio_url": audio_url or None,
                })
                try:
                    insert_emotion_score(session_id_local, role="user", emotion=user_emotion)
                except Exception as e:
                    logger.warning(f"Failed to persist user emotion: {e}")
                try:
                    if sophia_emotion:
                        insert_emotion_score(session_id_local, role="sophia", emotion=sophia_emotion)
                except Exception as e:
                    logger.warning(f"Failed to persist sophia emotion: {e}")
            except Exception as e:
                logger.warning(f"Failed to persist conversation session (stream): {e}")

            # Send audio URL and sophia emotion
            payload = {"audio_url": audio_url, "sophia_emotion": (sophia_emotion.model_dump() if sophia_emotion else None), "mock_audio": mock_audio}
            yield f"event: audio_url\ndata: {_json.dumps(payload)}\n\n"

        except Exception as e:
            logger.exception("Streaming DeFi chat failed")
            # Send an error event to client
            yield f"event: error\ndata: {{\"detail\": \"{str(e)}\"}}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

# ==========================
# Live Mode: WebSocket Voice
# ==========================

def _wav_header_pcm16(num_samples: int, sample_rate: int = 16000, num_channels: int = 1) -> bytes:
    import struct
    byte_rate = sample_rate * num_channels * 2
    block_align = num_channels * 2
    data_size = num_samples * 2
    riff_chunk_size = 36 + data_size
    return b"".join([
        b"RIFF",
        struct.pack("<I", riff_chunk_size),
        b"WAVE",
        b"fmt ",
        struct.pack("<IHHIIHH", 16, 1, num_channels, sample_rate, byte_rate, block_align, 16),
        b"data",
        struct.pack("<I", data_size),
    ])

async def _ws_send_json(ws: WebSocket, obj: dict):
    import json as _json
    await ws.send_text(_json.dumps(obj))

def _avg_abs_pcm16(buf: bytes) -> float:
    if not buf:
        return 0.0
    import array
    a = array.array('h')
    a.frombytes(buf[: len(buf) - (len(buf) % 2)])
    if len(a) == 0:
        return 0.0
    s = sum(abs(x) for x in a)
    return s / len(a)

@app.websocket("/ws/voice")
async def ws_voice(websocket: WebSocket):
    # In production, protect with auth (API key/session) via headers or query.
    await websocket.accept()
    SAMPLE_RATE = 16000
    BYTES_PER_SEC = SAMPLE_RATE * 2  # pcm16 mono
    CHUNK_MS = 200
    SILENCE_THRESHOLD = 300  # avg abs amplitude heuristic (lower => more responsive)
    SILENCE_MS = 600  # shorter endpointing delay for faster replies
    SILENCE_BYTES = int(BYTES_PER_SEC * (SILENCE_MS / 1000.0))

    pcm_buffer = bytearray()
    partial_transcript = ""
    last_partial_emit = 0.0
    last_voice_activity = time.time()
    in_speech = False
    utter_start_pos = 0
    # Live-mode summary state for end-of-call persistence
    last_final_text = ""
    last_reply_text = ""
    last_audio_url: Optional[str] = None

    try:
        while True:
            msg = await websocket.receive()
            if "bytes" in msg and msg["bytes"] is not None:
                chunk: bytes = msg["bytes"]
                if not chunk:
                    continue
                pcm_buffer.extend(chunk)

                # Emit partial transcript about every ~1s (and if we have enough audio)
                now = time.time()
                if now - last_partial_emit >= 1.0 and len(pcm_buffer) >= BYTES_PER_SEC // 2:
                    tail = pcm_buffer[-(2 * BYTES_PER_SEC):]
                    wav = _wav_header_pcm16(len(tail) // 2) + tail
                    try:
                        text = transcribe_audio_with_voxtral(wav)
                        if text:
                            await _ws_send_json(websocket, {"type": "partial_transcript", "text": text})
                            partial_transcript = text
                    except Exception:
                        pass
                    last_partial_emit = now

                # Simple amplitude-based VAD
                recent = pcm_buffer[-SILENCE_BYTES:] if len(pcm_buffer) > SILENCE_BYTES else pcm_buffer
                amp = _avg_abs_pcm16(recent)
                if amp > SILENCE_THRESHOLD:
                    if not in_speech:
                        in_speech = True
                        utter_start_pos = max(0, len(pcm_buffer) - len(recent))
                        logger.info(f"WS: speech started at {utter_start_pos} bytes (amp={amp:.1f})")
                    last_voice_activity = now

                # Endpoint: long enough silence after speech and we have some text
                if in_speech and partial_transcript and (now - last_voice_activity) * 1000.0 >= SILENCE_MS:
                    final_text = partial_transcript.strip()
                    await _ws_send_json(websocket, {"type": "final_transcript", "text": final_text})
                    # Extract utterance audio segment for logs only
                    utter_bytes = bytes(pcm_buffer[utter_start_pos:])
                    wav_utter = _wav_header_pcm16(len(utter_bytes) // 2) + utter_bytes
                    logger.info(f"WS: endpoint detected; utterance bytes={len(utter_bytes)} final_text_len={len(final_text)}")

                    # TRUE streaming of tokens from Mistral (Responses or Chat fallback)
                    logger.info("WS: starting token stream from LLM")
                    reply_tokens = []
                    tokens_sent = 0
                    try:
                        for tok in stream_generate_llm_reply(final_text):
                            if not tok:
                                continue
                            reply_tokens.append(tok)
                            await _ws_send_json(websocket, {"type": "token", "text": tok})
                            tokens_sent += 1
                    except Exception as e:
                        logger.warning(f"WS: stream_generate_llm_reply failed: {e}")
                    if tokens_sent == 0:
                        # Fallback: generate full reply and emit synthetic tokens so UI still streams
                        try:
                            logger.info("WS: no tokens streamed; falling back to generate_llm_reply + synthetic chunks")
                            full = generate_llm_reply(final_text)
                        except Exception as e:
                            logger.warning(f"WS: generate_llm_reply fallback failed: {e}")
                            full = "Okay."
                        chunk_size = 16
                        for i in range(0, len(full), chunk_size):
                            await _ws_send_json(websocket, {"type": "token", "text": full[i:i+chunk_size]})
                            tokens_sent += 1
                        reply_full = full.strip() or "Okay."
                    else:
                        reply_full = "".join(reply_tokens).strip() or "Okay."
                    logger.info(f"WS: token streaming complete; tokens_sent={tokens_sent}, reply_len={len(reply_full)}")
                    await _ws_send_json(websocket, {"type": "reply_done", "text": reply_full})

                    # Streaming TTS: split reply into short sentences; for each sentence synthesize once
                    # and emit base64 audio chunks immediately. Also keep URL events for backward compat.
                    import re
                    sentences = [s.strip() for s in re.split(r"(?<=[\.!?])\s+", reply_full) if s.strip()]
                    audio_url_last = None
                    for sent in sentences:
                        try:
                            logger.info(f"WS: TTS streaming for sentence len={len(sent)}")
                            import base64 as _b64
                            streamed_any = False
                            try:
                                for pcm_chunk in synthesize_inworld_stream(sent, sample_rate_hz=48000) or []:
                                    streamed_any = True
                                    b64 = _b64.b64encode(pcm_chunk).decode('ascii')
                                    # audio/wav because first chunk includes WAV header, subsequent are PCM
                                    await _ws_send_json(websocket, {"type": "audio_chunk", "mime": "audio/wav", "b64": b64, "eos": False})
                            except Exception:
                                logger.exception("WS: inworld streaming failed; falling back to non-streaming TTS for this sentence")
                            if not streamed_any:
                                # Fallback: synthesize whole sentence and stream bytes
                                audio_bytes = synthesize_inworld(sent)
                                logger.info(f"WS: fallback TTS bytes={len(audio_bytes)} (mock={str(audio_bytes).startswith('b\'ID3mock')})")
                                CHUNK = 8192
                                for off in range(0, len(audio_bytes), CHUNK):
                                    piece = audio_bytes[off:off+CHUNK]
                                    b64 = _b64.b64encode(piece).decode('ascii')
                                    await _ws_send_json(websocket, {"type": "audio_chunk", "mime": "audio/mpeg", "b64": b64, "eos": False})
                                # Also upload the full sentence MP3 to storage (optional/back-compat)
                                try:
                                    file_name = f"sophia_{int(time.time()*1000)}.mp3"
                                    audio_url_chunk = upload_audio_and_get_url(audio_bytes, file_name)
                                    audio_url_last = audio_url_chunk
                                    logger.info(f"WS: uploaded audio chunk -> {audio_url_chunk}")
                                    await _ws_send_json(websocket, {"type": "audio_url_chunk", "audio_url": audio_url_chunk})
                                except Exception:
                                    logger.warning("WS: upload of TTS sentence failed; continuing with streamed chunks only")
                        except Exception:
                            logger.exception("WS: TTS or upload chunk failed")
                            continue
                    # Signal end-of-stream for this reply's audio
                    await _ws_send_json(websocket, {"type": "audio_chunk", "mime": "audio/wav", "b64": "", "eos": True})
                    # Also send final audio_url for compatibility
                    await _ws_send_json(websocket, {"type": "audio_url", "audio_url": audio_url_last})

                    # Update summary for end-of-call persistence
                    last_final_text = final_text
                    last_reply_text = reply_full
                    last_audio_url = audio_url_last

                    # Reset for next utterance
                    partial_transcript = ""
                    in_speech = False
                    last_partial_emit = now
                    last_voice_activity = now
            elif msg.get("type") == "websocket.disconnect":
                break
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await _ws_send_json(websocket, {"type": "error", "detail": str(e)})
        try:
            await websocket.close()
        except Exception:
            pass

    # Persist a single conversation summary at hangup (best-effort, no emotions to keep it fast)
    try:
        if last_final_text or last_reply_text:
            insert_conversation_session({
                "transcript": last_final_text,
                "reply": last_reply_text,
                "audio_url": last_audio_url or None,
            })
    except Exception:
        pass
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
        
        # Store in Supabase (let DB set timestamps). Insert conversation first, then emotions.
        try:
            insert_conversation_session({
                "id": result["session_id"],
                "transcript": result["transcript"],
                "reply": result["reply"],
                "audio_url": result["audio_url"] or None,
                "intent": result["intent"],
                "context_memory": str(result["context_memory"]),
            })
            try:
                insert_emotion_score(result["session_id"], role="user", emotion=type("E", (), result["user_emotion"])())
            except Exception as e:
                logger.warning(f"Failed to persist user emotion: {e}")
            try:
                insert_emotion_score(result["session_id"], role="sophia", emotion=type("E", (), result["sophia_emotion"])())
            except Exception as e:
                logger.warning(f"Failed to persist sophia emotion: {e}")
        except Exception as e:
            logger.warning(f"Failed to persist text conversation session: {e}")
        
        return DefiChatResponse(**result)
        
    except Exception as e:
        logger.exception("Text chat processing failed")
        raise HTTPException(status_code=500, detail=f"Text chat processing failed: {str(e)}")


@app.post("/text-chat/stream")
@limiter.limit(settings.API_RATE_LIMIT)
async def text_chat_stream(
    request: Request,
    body: TextChatRequest,
    api_key_ok: None = Depends(verify_api_key),
):
    """Streaming variant for text-only chat.

    Server-Sent Events (SSE) with:
    - event: token, data: <text chunk>
    - event: reply_done, data: { reply }
    - event: audio_url, data: { audio_url, sophia_emotion }
    """
    async def event_generator():
        try:
            import json as _json
            # Stream LLM tokens
            reply_accum = []
            for chunk in stream_generate_llm_reply(body.message):
                if not chunk:
                    continue
                reply_accum.append(chunk)
                safe_chunk = chunk.replace("\n", " ")
                yield f"event: token\ndata: {safe_chunk}\n\n"

            reply = "".join(reply_accum).strip()
            yield f"event: reply_done\ndata: {{\"reply\": { _json.dumps(reply) }}}\n\n"

            # Optional TTS synthesis and audio URL
            audio_url = ""
            sophia_emotion = None
            mock_audio = False
            try:
                audio_bytes = synthesize_inworld(reply)
                file_name = f"sophia_{int(time.time()*1000)}.mp3"
                audio_url = upload_audio_and_get_url(audio_bytes, file_name)
                try:
                    mock_audio = audio_bytes.startswith(b"ID3mock") or len(audio_bytes) < 2048
                except Exception:
                    mock_audio = False
                sophia_emotion = analyze_emotion_audio(audio_bytes)
            except Exception:
                logger.exception("Synthesis or upload failed in text_chat_stream")

            payload = {"audio_url": audio_url, "sophia_emotion": (sophia_emotion.model_dump() if sophia_emotion else None), "mock_audio": mock_audio}
            yield f"event: audio_url\ndata: {_json.dumps(payload)}\n\n"

        except Exception as e:
            logger.exception("Streaming text chat failed")
            yield f"event: error\ndata: {{\"detail\": \"{str(e)}\"}}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
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