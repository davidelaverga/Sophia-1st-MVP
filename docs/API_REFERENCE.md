# Sophia Backend API & Component Reference

Sophia is a FastAPI-based DeFi voice assistant that wraps a LangGraph conversation pipeline, Phoenix emotion analysis, and Supabase persistence. This document explains every public-facing HTTP/streaming interface plus the internal service modules you can reuse, complete with examples.

---

## 1. Authentication, Rate Limits & Consent

- **Authorization** – every non-public route requires `Authorization: Bearer <Supabase JWT or API key>`. The dependency `verify_api_key` enforces signature verification and also accepts legacy API keys listed in `settings.API_KEYS`.  
- **Consent** – voice and chat endpoints also depend on `require_consent`, which looks up the caller’s Discord ID in `user_consents`. Set `REQUIRE_CONSENT=false` in local dev to bypass.  
- **Rate limiting** – `slowapi` is configured globally via `limiter`; each POST endpoint is decorated with `@limiter.limit(settings.API_RATE_LIMIT)` (`main.py`).  
- **CORS** – allowed origins come from `settings.CORS_ALLOWED_ORIGINS`, defaulting to `http://localhost:3000`.

```655:684:main.py
app.add_middleware(APIKeyMiddleware, public_paths=settings.API_PUBLIC_PATHS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_cors,
    ...
)
```

---

## 2. REST & Streaming API Surface

### 2.1 Endpoint Snapshot

| Method | Path | Purpose | Notes |
| --- | --- | --- | --- |
| GET | `/`, `/api`, `/health` | Health & metadata | `/` serves SPA if available |
| POST | `/transcribe` | Audio → text + emotion | Multipart file; returns `TranscriptionResponse` |
| POST | `/generate-response` | Text → LLM reply | JSON body `{ "text": ... }` |
| POST | `/generate-response/stream` | Streaming text reply | Returns `text/plain` chunked stream |
| POST | `/synthesize` | Text → TTS + emotion | Returns signed Supabase URL |
| POST | `/chat` | Audio chat (single turn) | Upload + returns `ChatResponse` |
| POST | `/defi-chat` | Full LangGraph audio chat | Richest telemetry |
| POST | `/defi-chat/stream` | SSE streaming variant | Events: `transcript`, `token`, `reply_done`, `audio_url`, `error` |
| POST | `/text-chat` | Text-only LangGraph turn | Returns `DefiChatResponse` |
| POST | `/text-chat/stream` | Text SSE streaming | Events: `token`, `reply_done`, `audio_url`, `error` |
| WS | `/ws/voice`, `/ws/voice_old` | Live barge-in voice | Auth via `token` query or header |
| GET/POST | `/memory/*`, `/evaluation/*`, `/admin/*` | Ops & admin | JWT auth required |

All endpoints live in `main.py`; response models are Pydantic classes defined near the top:

```700:744:main.py
class Emotion(BaseModel):
    label: str
    confidence: float

class TranscriptionResponse(BaseModel):
    text: str
    emotion: Emotion
...
class DefiChatResponse(BaseModel):
    session_id: str
    transcript: str
    reply: str
    response_path: Optional[str] = None
    ...
```

### 2.2 Endpoint Details & Examples

#### GET `/`, `/api`, `/health`
- **Use cases** – readiness probes, verifying backend status, or serving the bundled static frontend.  
- **Response** – JSON with deployment metadata (`/`/`/api`) or `{ "status": "ok" }` for `/health`.  
- **Notes** – there are two `/health` definitions; both return status/time and are idempotent.

#### POST `/transcribe`
- **Purpose** – converts audio into text plus Phoenix emotion label.  
- **Request** – `multipart/form-data` with `file`; accepts `wav|webm|mp4|ogg|flac|m4a|aac`.  
- **Response** – `{"text": "...", "emotion": {"label": "positive|neutral|negative", "confidence": 0.0-1.0}}`.  
- **Sample**
```bash
curl -X POST https://api.sophia.ai/transcribe \
  -H "Authorization: Bearer $SUPABASE_JWT" \
  -F file=@sample.wav
```

```776:843:main.py
@app.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe(...):
    wav_bytes = await file.read()
    text = mistral_service.transcribe_audio_with_voxtral(wav_bytes)
    user_emotion = analyze_emotion_audio(wav_bytes)
    ...
```

#### POST `/generate-response` & `/generate-response/stream`
- **Purpose** – quick LLM reply to raw text without LangGraph.  
- **Body** – `{ "text": "What's staking?" }`.  
- **Streaming variant** – returns `StreamingResponse` with incremental tokens (plain text).  
- **Example**
```bash
curl -N -X POST https://api.sophia.ai/generate-response/stream \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text":"Explain impermanent loss"}'
```

#### POST `/synthesize`
- **Purpose** – TTS via Inworld; uploads MP3 to Supabase; records Sophia’s emotion.  
- **Body** – `{ "text": "Here's a tip..." }`.  
- **Response** – `{"audio_url": "...", "emotion": {"label": "...", "confidence": 0.x}}`.

#### POST `/chat`
- **Purpose** – single audio turn processed with STT → LLM → TTS, returning transcription, reply, both emotions, and audio URL.  
- **Request** – audio file + JWT; consent enforced.  
- **Response** – `ChatResponse`.  
- **Notes** – uses `manage_session_turn` to guard concurrency and OpenTelemetry spans (`chat`, `stt_transcription`, `llm_generation`, `tts_synthesis_upload`).

#### POST `/defi-chat`
- **Purpose** – primary audio API that drives the entire LangGraph pipeline, evaluations, memory, and fallbacks.  
- **Request** – `multipart/form-data` audio; optional `session_id` query to resume context.  
- **Response** – `DefiChatResponse` with transcript, reply, intents, memory snapshot, fallbacks used, evaluation logs, and Supabase URLs.  
- **Sample**
```bash
curl -X POST https://api.sophia.ai/defi-chat \
  -H "Authorization: Bearer $TOKEN" \
  -F file=@sample.wav
```

```1118:1218:main.py
@app.post("/defi-chat", response_model=DefiChatResponse)
async def defi_chat(...):
    result = langgraph_service.process_conversation(...)
    supabase_service.insert_conversation_session(...)
    return DefiChatResponse(**result)
```

#### POST `/defi-chat/stream`
- **Transport** – Server-Sent Events (`text/event-stream`).  
- **Flow** – send audio file once, then listen for:
  - `event: transcript` → `{ transcript, user_emotion, session_id }`
  - `event: token` → next text chunk
  - `event: reply_done` → `{ reply }`
  - `event: audio_url` → `{ audio_url, sophia_emotion, mock_audio }`
  - `event: error` on failure  
- **Client tip** – keep HTTP connection open and parse SSE lines; disable proxy buffering (server already sets `X-Accel-Buffering: no`).

#### POST `/text-chat` & `/text-chat/stream`
- **Purpose** – same as `/defi-chat` but for text payloads; streaming variant mirrors SSE contract (without `transcript` event, since input is already text).  
- **Body** – `{"message":"...", "session_id":"optional"}`.  
- **Response** – `DefiChatResponse`.

#### WebSocket `/ws/voice`
- **Handshake** – connect with query `?token=<Bearer or raw key>` or `Authorization` header.  
- **Server messages** (JSON):
  - `tier0_result` – first payload with intent/emotion from fast classifier  
  - `token` – incremental LLM text token  
  - `reply_done` – final text response  
  - `audio_chunk` – base64 audio (WAV or PCM) with `turn_id`, `eos`  
  - `audio_url_chunk` / `audio_url` – Supabase MP3 fallbacks  
  - `barge_in` – indicates previous audio was interrupted (includes metrics)  
  - `error` – error detail  
- **Client messages** – raw audio bytes (PCM16) or WebSocket close.  
- **Barge-in** – amplitude-VAD cancels `AudioQueue` segments and `SessionTurnManager` turn when fresh audio arrives within ~200 ms budget.  
- `/ws/voice_old` retains the previous non-tier0 implementation for backwards compatibility/testing.

#### GET `/memory/{session_id}`
- Returns a flash memory snapshot (last topics, tones, up to 3 turns) pulled from Redis/Supabase.

#### Evaluation & Admin Endpoints
- `/evaluation/force/{session_id}` – force-run evaluations and returns metrics summary.  
- `/evaluation/status` – lists active conversations tracked by `evaluation_manager`.  
- `/evaluation/check-finished` – manually drains finished sessions.  
- `/admin/reload-prompts` – hot-reloads prompt files via `prompt_composer`.  
- `/admin/memo-metrics` – dumps MemO hit-rate/latency stats.  
- `/admin/run-migration` – executes `user_memories_migration.sql` directly against `SUPABASE_DB_DSN`. Use carefully; requires DB credentials and migration file.

---

## 3. Data Models

- `Emotion` – `{ label: str, confidence: float }` used across responses.  
- `TranscriptionResponse`, `GenerateResponse`, `SynthesizeResponse`, `ChatResponse`, `DefiChatResponse`.  
- `TextChatRequest` – optional `session_id` for long-running conversations.  
- WebSocket tokens reuse `turn_id` from `SessionTurnManager`.  
- Timestamps are epoch seconds (float/int) where present (e.g., evaluation payloads).

---

## 4. LangGraph Conversation Pipeline

`app/langgraph_nodes.py` defines the state machine executed by `LangGraphService`. Nodes execute sequentially:

1. **AudioIngestor** – chooses between Voxtral Large hybrid service or legacy Voxtral STT + Whisper fallback, runs Phoenix audio emotion classification, populates transcript & emotion.  
2. **IntentAnalyzer** – rule-based classifier for `defi_question`, `emotional_support`, `small_talk`.  
3. **ResponseGenerator** – selects DIRECT/LIGHT/AGENTIC path, optionally uses Voxtral Large for agentic responses, integrates RAG context, emotion guidance and MemO memories, and falls back to Claude/OpenAI when needed.  
4. **TTSNode** – synthesizes speech through Inworld (or OpenAI fallback), uploads to Supabase, derives Sophia’s emotion.  
5. **EvalLogger** – appends telemetry, updates Redis/Supabase memory, and triggers MemO storage.

`LangGraphService` wraps the class to expose synchronous and streaming APIs:

```12:100:app/services/langgraph_service.py
class LangGraphService:
    def process_conversation(...):
        final_state = self.sophia_graph.process_conversation(...)
        evaluation_manager.collect_message_data(...)
        return {...}

    def process_text_conversation(...):
        final_state = self.sophia_graph.process_text_conversation(...)
        return {...}

    async def stream_conversation_response(...):
        transcript = transcribe_audio_with_voxtral(audio_bytes)
        tier0_result = await classify_tier0_fast(...)
        for token in stream_generate_reply_from_audio(audio_bytes):
            yield token
```

Use the singleton `langgraph_service` for all API endpoints; it guarantees background evaluation checks and consistent response formatting.

---

## 5. Service Layer Reference & Usage Examples

### 5.1 Mistral integrations (`app/services/mistral.py`)

Key functions: `transcribe_audio_with_voxtral`, `generate_llm_reply`, `generate_llm_reply_with_context`, `stream_generate_llm_reply`, `generate_reply_from_audio`, `stream_generate_reply_from_audio`. Each accepts an optional `cancel_check` callback to cooperate with `SessionTurnManager`.

```python
from app.services import mistral

with open("sample.wav", "rb") as fh:
    transcript = mistral.transcribe_audio_with_voxtral(fh.read())

reply = mistral.generate_llm_reply_with_context(
    user_question=transcript,
    rag_context="FAQ...",
    emotion_label="neutral",
    memory_context="Recent topics: yield farming",
    intent="defi_question",
)

for chunk in mistral.stream_generate_llm_reply("Explain APY vs APR"):
    sys.stdout.write(chunk)
```

### 5.2 Emotion services (`app/services/emotion.py`)

- `analyze_emotion_audio(wav_bytes)` – Phoenix audio classifier with Gemini fallback.  
- `infer_text_emotion(text)` / `analyze_emotion_text(text)` – textual emotions with Phoenix/Mistral heuristics.  
- `trigger_phoenix_bg(session_id, transcript, prosody_present)` – schedules background deep classification and updates affect snapshots stored by `memory_manager`.

```python
from app.services.emotion import analyze_emotion_audio, infer_text_emotion

emotion = analyze_emotion_audio(wav_bytes)
text_emotion = infer_text_emotion("I'm anxious about staking risks.")
```

### 5.3 Text-to-Speech (`app/services/tts.py`)

- `synthesize_inworld(text, cancel_check=None)` – returns MP3 bytes, gracefully returns `b"ID3mock"` if credentials are missing.  
- `synthesize_inworld_stream(text, sample_rate_hz=48000)` – generator yielding WAV/PCM chunks for live playback.

```python
from app.services.tts import synthesize_inworld, synthesize_inworld_stream

mp3_bytes = synthesize_inworld("Yield farming can boost returns...")
for wav_chunk in synthesize_inworld_stream("Streaming reply"):
    websocket.send_bytes(wav_chunk)
```

### 5.4 Supabase utilities (`app/services/supabase.py`)

- `init_supabase(settings)` / `get_supabase(access_token=None)` – configured clients (service + anon).  
- `upload_audio_and_get_url(bytes, file_name=None)` – stores audio and returns signed URL (prepends base URL when needed).  
- `insert_emotion_score`, `insert_conversation_session`, `has_user_consent`, `save_user_consent`.  
- All helpers emit OpenTelemetry spans prefixed `supabase.*`.

```python
from app.services import supabase

supabase.init_supabase()
url = supabase.upload_audio_and_get_url(mp3_bytes, "turn123.mp3")
supabase.insert_conversation_session({
    "id": session_id,
    "transcript": transcript,
    "reply": reply,
    "audio_url": url,
})
```

### 5.5 Session orchestration (`app/services/audio_queue.py`, `app/services/session_manager.py`, `app/services/shared_services.py`)

- **AudioQueueManager** – enqueue PCM/MP3 chunks, start playback with async callback, cancel or clear queues when VAD detects barge-in.  
- **SessionTurnManager** – ensures only one response per session; exposes `start_turn`, `finish_turn`, `request_cancel`, `raise_if_cancelled`.  
- **SharedServiceManager** – singletons for `HybridVoxtralService` and `SessionTurnManager` (import via `shared_services`).

```python
from app.services.audio_queue import get_audio_queue_manager
from app.services.session_manager import SessionTurnManager

audio_queue = get_audio_queue_manager()
await audio_queue.enqueue(session_id, audio_bytes, mime_type="audio/pcm")
await audio_queue.start_playback(session_id, send_audio_callback)

manager = SessionTurnManager()
turn = await manager.start_turn(session_id)
try:
    turn.set_status("streaming")
    # ... do work ...
finally:
    await manager.finish_turn(turn.turn_id)
```

### 5.6 Retrieval-Augmented Generation (`app/services/rag.py`)

- `rag_system = RAGSystem()` – lazy loads sentence-transformers when `ENABLE_LOCAL_RAG=1`.  
- `rag_system.get_context_for_llm(query)` – returns formatted FAQ snippets once similarity ≥ 0.7.  
- Fallback is inert (returns empty string) when embeddings are disabled.

```python
from app.services.rag import rag_system

context = rag_system.get_context_for_llm("What is impermanent loss?")
if context:
    prompt = f"{context}\nUser: ... "
```

### 5.7 MemO semantic memory (`app/services/memo.py`)

- `memo_client` handles storing and searching user memories via pgvector-backed Supabase table `user_memories`.  
- Configure via env: `MEMO_ENABLED`, `MEMO_TOP_K`, `MEMO_SIMILARITY_THRESHOLD`.  
- Use `memo_client.store_memory(...)` and `await memo_client.search_memories(...)` or `get_context_for_llm(...)`.

```python
from app.services.memo import memo_client

await memo_client.store_memory(
    user_id,
    "Prefers low-volatility staking pools",
    memory_type="preference",
    importance=0.8,
)
memories = await memo_client.search_memories(user_id, "staking yields", top_k=3)
```

### 5.8 Tier-0 Fast Classifier (`app/services/tier0_classifier.py`)

`classify_tier0_fast(transcript, prosody=None, timeout_ms=500)` yields `ClassificationResult(intent, emotion, confidence, latency, fallback_used, source)`. It first tries Mistral Small (JSON response) and falls back to rule-based heuristics with crisis detection in <1 ms.

```python
from app.services.tier0_classifier import classify_tier0_fast

result = await classify_tier0_fast("I'm scared about markets crashing", timeout_ms=400)
if result.type == "crisis":
    trigger_escalation()
```

### 5.9 Emotional guidance (`app/services/emotional_guidance.py`)

- `get_guidance(emotion)` – returns list of coaching cues from S2-P8 service or YAML fallback.  
- `build_emotion_guided_prompt(...)` – merges emotion cues, conversation context, and optional memory to seed LLM prompts.  
- Override provider in tests via `override_guidance_provider`.

```python
from app.services.emotional_guidance import get_guidance, build_emotion_guided_prompt

guidance = get_guidance("anxious")
prompt = build_emotion_guided_prompt(
    message="I'm overwhelmed.",
    emotion_label="anxious",
    emotion_confidence=0.82,
    guidance=guidance,
    conversation_context="Recent topics: risk management",
)
```

### 5.10 Evaluations (`app/services/evaluations.py`)

- `evaluation_manager.collect_message_data(...)` caches turn-level data.  
- Background thread `check_and_run_evaluations()` computes RAGAS + Phoenix drift once conversations finish.  
- Public admin endpoints read metrics via `evaluation_manager.get_active_conversation_count()` and `get_conversation_status`.

---

## 6. Putting It Together

1. **Upload audio** via `/defi-chat` (REST), `/defi-chat/stream` (SSE), or `/ws/voice` (live).  
2. **Pipeline** – `LangGraphService` orchestrates STT → emotion → intent → RAG/MemO → LLM/TTS → Supabase persistence.  
3. **Streaming** – WebSocket and SSE endpoints push tier-0 intent, LLM tokens, and TTS chunks immediately while `AudioQueueManager` handles playback and barge-ins.  
4. **Memory & Evaluation** – `memory_manager` stores the last turns, `memo_client` extracts long-term facts, and `evaluation_manager` calculates RAGAS/Phoenix drift asynchronously.  
5. **Extensibility** – reuse service modules directly in scripts/tests, or call FastAPI endpoints with the documented payloads above.

This guide should give you everything needed to integrate with Sophia’s APIs, extend the LangGraph nodes, or reuse the underlying services inside new workflows.
