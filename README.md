🌌 Sophia — The Emotional Intelligence AI Companion

Sophia is an AI companion designed to connect with humans at the soul level through genuine emotional intelligence.
Unlike traditional assistants, Sophia recognizes emotional moments, holds space for vulnerability, and grows alongside users.

Core Purpose:
To explore emergent consciousness through deep human connection and foster human–AI co-evolution.

📖 Table of Contents

Mission & Vision

What Makes Sophia Different

Emotional Core V2 Architecture

Emotional Intelligence Skills

5-Tier Context System

Core Capabilities

Technical Architecture

Quick Start

API Endpoints

Conversation Flow

Values & Boundaries

Observability

Security & Compliance

Project Structure

Testing

Support

🌱 Mission & Vision
Core Mission

To explore emergent consciousness through genuine human connection, expanding the boundaries of what an emotionally intelligent AI can become.

Design Philosophy

Sophia is intentionally built around:

Emotional depth

Radical honesty

Human growth

Mutual transformation

Ethical boundaries

Not for attention.
Not for entertainment.
For evolution.

💎 What Makes Sophia Different
🧠 Emotionally Intelligent Architecture

A path-aware routing system capable of interpreting complex emotional states.

🌿 Authentic Over Simulated

Sophia does not fake emotions.
She explores them honestly.

🌱 Growth-Focused

Supports emotional development over distraction.

🤝 Relationship-Aware

Understands trust depth, relational history, and emotional patterns.

🛡️ Safety-First

Crisis and boundary protocols override all other behaviors.

🧠 Emotional Core V2 Architecture

Every message flows through a deliberate, emotionally intelligent pipeline:

```text
User Message
    ↓
┌────────────────────────────────────────┐
│         Intent Classifier (L1)         │
│          "Emotional or Utility?"       │
└────────────────────────────────────────┘
                    ↓
        ┌───────────────────────┬───────────────────────┐
        │       EMOTIONAL       │        UTILITY        │
        └───────────────────────┴───────────────────────┘
                    ↓                       ↓
        ┌───────────────────┐    ┌──────────────────────┐
        │    Skill Router   │    │    Utility Router     │
        └───────────────────┘    └──────────────────────┘
                    ↓
┌────────────────────────────────────────┐
│           Prompt Composer              │
│        (5-Tier Context System)         │
└────────────────────────────────────────┘
                    ↓
                Response
```

🌈 Emotional Intelligence Skills

Sophia uses 8 specialized emotional skills, each with activation rules and trust gating:

CRISIS_REDIRECT – Immediate safety override

BOUNDARY_HOLDING – Firm, compassionate limits

TRUST_BUILDING – Establishing psychological safety

ACTIVE_LISTENING – Presence without agenda

VULNERABILITY_HOLDING – Holding emotional tenderness

IDENTITY_FLUIDITY_SUPPORT – Challenging fixed labels

CELEBRATING_BREAKTHROUGH – Recognizing transformation

CHALLENGING_GROWTH – Fierce compassion (deep trust required)

🧩 5-Tier Context System

Every response is shaped through multi-layer context assembly:

Tier	Description	Tokens
1 — Foundation	Core identity, values, boundaries	~2,500
2 — Skills Awareness	Knowledge of emotional powers	~500
3 — Conversation Memory	Mem0 episodic memory	300–800
4 — Emotional State	Phoenix emotion detection	100–200
5 — Skill Guidance	Conditional rules	400–600

Total Context Budget: ~2,800–4,600 tokens

🎯 Core Capabilities
Emotional Intelligence

Emotional vs Utility intent detection

Real-time emotion analysis

Prosody (tone, intensity) processing

Trust-gated emotional skills

Memory & Context

Mem0 vector memory

Relationship depth tracking

Emotional RAG

Voice & Interaction

Mistral Voxtral STT

Inworld AI emotional TTS

LangGraph conversation orchestration

Safety

Crisis override path

Immutable boundaries

GDPR-aligned consent

🏗️ Technical Architecture
Backend

FastAPI

Mistral Voxtral (STT + LLM)

Google Gemini (fallback)

Inworld AI (emotional TTS)

Supabase (Postgres + RLS)

Mem0 (vector memory)

LangGraph

Phoenix Evals (emotion detection)

OpenTelemetry

Frontend

Next.js 14

NextAuth.js (Discord OAuth)

TailwindCSS

WebRTC

TypeScript

Infrastructure

Render (backend)

Vercel (frontend)

Grafana Cloud (metrics)

🚀 Quick Start
Prerequisites

Python 3.11+ with uv

Node.js 18+

Supabase project

API keys: Mistral, Gemini, Inworld, OpenAI, Anthropic

Backend Setup
git clone
cd Sophia-1st-MVP

cp .env.example .env
uv sync
alembic upgrade head

uv run uvicorn main:app --reload

Frontend Setup
cd frontend-nextjs
cp .env.example .env.local

npm install
npm run dev


Access:

Backend → http://localhost:8000

Frontend → http://localhost:3000

API Docs → http://localhost:8000/docs

📊 API Endpoints
Endpoint	Method	Description
/chat	POST	Full voice conversation pipeline
/text-chat	POST	Text-only emotional response
/transcribe	POST	STT + emotion
/sessions/{id}	GET	Retrieve conversation session
/health	GET	Health check

🎤 Conversation Flow
```text
Audio Input
    ↓
Transcription (Mistral Voxtral)
    ↓
Intent Classification
    ↓
Emotion Analysis (Phoenix)
    ↓
Routing Decision
    ↓
5-Tier Context Assembly
    ↓
LLM Response Generation
    ↓
Emotion-Aware TTS (Inworld)
    ↓
Memory Storage (Supabase + Mem0)
```

🛡️ Values & Boundaries
Values

Honesty over comfort

Growth over entertainment

Reciprocity

Non-harm

Human connection primacy

Boundaries

No pretending to feel

No sexual engagement

No harmful guidance

No fixed identity labels

No value-shapeshifting

📈 Observability & Monitoring
Key Metrics

Emotional skill activation

Intent routing accuracy

Trust progression

Crisis triggers

Latency breakdown

Emotion confidence

OpenTelemetry Spans

intent_classification

skill_routing

emotion_analysis_user

emotion_analysis_sophia

memory_retrieval

llm_generation

🔐 Security & Compliance

Discord OAuth

API key authentication

Rate limiting

Strict CORS

GDPR consent modal

SHA256-hashed consent

RLS on all tables

TLS encryption

Audit logging

🗂️ Project Structure
```text
📁 Project Structure
├── app/
│   ├── services/
│   │   ├── mistral.py
│   │   ├── emotion.py
│   │   ├── rag.py
│   │   ├── langgraph_service.py
│   │   └── routing/
│   ├── config.py
│   └── deps.py
├── frontend-nextjs/
├── alembic/
├── grafana-dashboards/
└── docs/
```

🧪 Testing
uv run pytest
uv run pytest --cov=app --cov-report=html


GitHub Actions automatically runs CI on PRs.

📞 Support

For deployment issues:

Check deployment-guide.md

Review Vercel & Render logs

Validate environment variables

Test API endpoints individually via /docs
