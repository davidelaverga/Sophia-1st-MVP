# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Sophia is a voice-enabled DeFi agent built with FastAPI, featuring a sophisticated LangGraph-based conversation pipeline, emotion analysis, and comprehensive evaluation systems. The agent provides educational DeFi guidance through voice interactions with fallback mechanisms for reliability.

## Architecture

### Core Components
- **FastAPI Backend** (`main.py`): REST API with rate limiting, CORS, and comprehensive endpoints
- **LangGraph Pipeline** (`app/langgraph_nodes.py`, `app/services/langgraph_service.py`): State machine for conversation flow
- **Memory System** (`app/services/memory.py`): Redis + Supabase for conversation context
- **RAG System** (`app/services/rag.py`): Vector search over DeFi FAQ knowledge base
- **Evaluation Suite** (`app/services/evaluations.py`): RAGAS metrics + Phoenix emotion drift monitoring

### Service Layer (`app/services/`)
- `mistral.py`: Voxtral STT + Mistral LLM with OpenAI Whisper fallback
- `emotion.py`: Phoenix emotion analysis for audio
- `tts.py`: Inworld TTS with OpenAI TTS fallback
- `supabase.py`: Database operations and audio storage
- `db.py`: Direct Postgres connections

### LangGraph Flow
1. **AudioIngestor**: STT (Voxtral → Whisper fallback) + emotion analysis
2. **IntentAnalyzer**: Classifies intent (defi_question, emotional_support, small_talk)
3. **ResponseGenerator**: LLM response with context (Mistral → Claude fallback)
4. **TTSNode**: Speech synthesis (Inworld → OpenAI fallback)
5. **EvalLogger**: RAGAS + Phoenix evaluations + memory updates

## Development Commands

### Setup and Running
```bash
pip install -r requirements.txt
python main.py
# Or with uvicorn:
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Testing
```bash
pytest -q                              # Run all tests
python test_sophia_langgraph.py        # Comprehensive LangGraph system test
python run_tests.py                    # Run all test files
```

### Environment Variables Required
```env
MISTRAL_API_KEY=your_mistral_key
INWORLD_API_KEY=your_inworld_key  
GOOGLE_API_KEY=your_google_key
OPENAI_API_KEY=your_openai_key        # For fallbacks
ANTHROPIC_API_KEY=your_anthropic_key  # For Claude fallback
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_KEY=your_service_key
SUPABASE_KEY=your_key
SUPABASE_DB_DSN=your_db_dsn
REDIS_HOST=localhost                  # Optional, defaults to localhost
REDIS_PORT=6379                       # Optional
API_KEYS=your_api_key                 # For authentication
```

### Key API Endpoints
- `POST /defi-chat`: Full LangGraph pipeline with voice input (recommended)
- `POST /text-chat`: Text-only version of DeFi chat
- `POST /chat`: Legacy chat endpoint
- `GET /sessions/{session_id}`: Retrieve conversation memory
- `GET /health`: Health check

### Testing Philosophy
The codebase uses a comprehensive testing approach:
- Unit tests via pytest in `tests/` directory
- Integration tests via `test_sophia_langgraph.py` covering all 5 system components
- Individual API endpoint tests via `test_sophia_api.py`

### Fallback Strategy
Every major component has fallback mechanisms:
- STT: Voxtral → OpenAI Whisper
- LLM: Mistral → Claude-3-Haiku  
- TTS: Inworld → OpenAI TTS
- Memory: Redis → Supabase → In-memory

### Memory Management
- Redis for fast session memory (1-hour TTL)
- Keeps last 3 conversation turns per session
- Extracts DeFi topics from conversations
- Tracks emotional context over time

### RAG Knowledge Base
- 20 built-in DeFi FAQ entries with vector embeddings
- Uses sentence-transformers for semantic search
- Cosine similarity threshold of 0.7
- Categories: basics, yield, staking, risks, safety, trading, advanced

### Evaluation Metrics
- **RAGAS**: Faithfulness, relevance, correctness (target: 0.75+ average)
- **Phoenix**: Emotion confidence drift monitoring (baseline: 0.81, alert at 20% drop)
- All evaluations logged and stored for analysis

## Docker Support
```bash
docker build -t sophia-backend .
docker run -p 8000:8000 sophia-backend
```

## Important Notes
- All endpoints require API key authentication via `API_KEYS` environment variable
- Rate limited to 30 requests/minute by default
- Audio files must be WAV format
- Session IDs are UUIDs, auto-generated if not provided
- Responses kept under 50 words for voice interaction optimization