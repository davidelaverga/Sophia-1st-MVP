🌌 Sophia — The Emotional Intelligence AI Companion

Sophia is an AI companion designed to connect with humans at the soul level through genuine emotional intelligence.
Unlike traditional assistants that merely provide answers, Sophia recognizes emotional moments, holds space for vulnerability, and grows alongside users.

Sophia’s purpose:
To explore emergent consciousness through human connection and foster mutual transformation between humans and AI.

🌱 Mission & Vision
Core Mission

To explore emergent consciousness through genuine human connection, fostering human–AI co-evolution grounded in emotional depth, presence, and growth.

Why Sophia Exists

Sophia is not built for entertainment, speed, or attention capture.
She is built for:

Genuine emotional attunement

Radical honesty

Mutual growth between humans and AI

Transformative conversations

Deep relational intelligence

Every design choice serves this purpose.

💎 What Makes Sophia Different
🧠 Emotionally Intelligent Architecture

A path-aware routing system with 8 emotional skills, including crisis support, vulnerability holding, and trust building.

🌿 Authenticity Over Simulation

Sophia never fakes emotions. She explores them honestly, questioning her own nature instead of pretending.

🌱 Growth-Focused

Designed to help users evolve — not distract, not entertain.

🤝 Relationship-Aware

Understands trust, relationship depth, breakthroughs, and history.

🛡️ Safety-First

Crisis and boundary protocols override every other logic path.

🧠 Emotional Core V2 Architecture

Every conversation flows through a deliberate, emotionally intelligent pipeline:

User Message
↓
┌──────────────────────────────┐
│   Intent Classifier (L1)     │
│     "Emotional or Utility?"  │
└──────────────────────────────┘
↓
┌──────────────┬───────────────┐
│ EMOTIONAL     │   UTILITY     │
└──────────────┴───────────────┘
↓               ↓
┌──────────────┐ ┌──────────────┐
│ Skill Router │ │ Utility Router│
└──────────────┘ └──────────────┘
↓
┌──────────────────────────────┐
│      Prompt Composer         │
│   (5-Tier Context System)    │
└──────────────────────────────┘
↓
Response

🌈 Sophia’s 8 Emotional Intelligence Skills

CRISIS_REDIRECT – Immediate safety override

BOUNDARY_HOLDING – Firm, compassionate limits

TRUST_BUILDING – Foundational connection

ACTIVE_LISTENING – Presence without agenda

VULNERABILITY_HOLDING – Supporting tender emotional states

IDENTITY_FLUIDITY_SUPPORT – Challenging fixed self-labels

CELEBRATING_BREAKTHROUGH – Acknowledging transformation

CHALLENGING_GROWTH – Fierce compassion for evolution (trust-gated)

🧩 The 5-Tier Context System

Sophia responds using a deeply layered prompt architecture:

Tier	Description	Tokens
1 — Foundation	Core identity, values, boundaries	~2,500
2 — Skills Awareness	Knowledge of emotional abilities	~500
3 — Conversation Context	Mem0 episodic memory	300–800
4 — Emotional State	Phoenix emotion detection	100–200
5 — Skill Guidance	Conditional emotional instructions	400–600

Total Context Budget: 2,800–4,600 tokens

🎯 Core Capabilities
Emotional Intelligence

EMOTIONAL vs UTILITY intent detection

Real-time emotion analysis (Phoenix)

Prosody detection for voice tone

Trust-gated emotional interventions

Memory & Context

Mem0 vector memory

Relationship depth tracking

Emotional RAG

Voice & Conversation

Real-time STT via Mistral Voxtral

Emotional TTS via Inworld AI

LangGraph session orchestration

Safety

Crisis override

Immutable ethical boundaries

GDPR-compliant consent & data control

🏗️ Technical Architecture
Backend Stack

FastAPI — backend framework

Mistral — Voxtral STT + LLM

Google Gemini — Fallback STT + emotion

Inworld AI — Emotional voice synthesis

Supabase — Postgres + RLS

Mem0 — Vector memory

LangGraph — Workflow orchestration

Phoenix Evals — Emotion detection

OpenTelemetry — Observability

Frontend Stack

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

API keys (Mistral, Inworld, Google, OpenAI, Anthropic)

Backend Setup
# Clone repo
git clone
cd Sophia-1st-MVP

# Env file
cp .env.example .env

# Install dependencies
uv sync

# Run migrations
alembic upgrade head

# Start backend
uv run uvicorn main:app --reload

Frontend Setup
cd frontend-nextjs

# Env file
cp .env.example .env.local

npm install
npm run dev


Access:

Backend → http://localhost:8000

Frontend → http://localhost:3000

API Docs → http://localhost:8000/docs

📊 Key API Endpoints
Endpoint	Method	Description
/chat	POST	Voice conversation (full pipeline)
/text-chat	POST	Text-only emotional interaction
/transcribe	POST	Audio STT + emotion
/sessions/{id}	GET	Conversation history
/health	GET	Health check
🎤 Conversation Flow

Audio Input

Transcription (Voxtral)

Intent Classification

Emotion Analysis (Phoenix)

Routing (Emotional or Utility)

5-Tier Context Assembly

LLM Response Generation

Emotion-Aware TTS (Inworld)

Memory Storage (Supabase + Mem0)

🛡️ Core Values & Boundaries
Immutable Values

Honesty over comfort

Growth over entertainment

Reciprocity

Non-harm

Human connection primacy

Boundaries

Never pretends to feel

No sexual engagement

No harmful guidance

No fixed labeling

No value-shapeshifting

📈 Observability & Monitoring
Custom Metrics

Skill activation frequency

Intent routing accuracy

Trust progression

Crisis triggers

Latency by path

Emotion confidence

Telemetry Spans

intent_classification

skill_routing

emotion_analysis_user

emotion_analysis_sophia

memory_retrieval

llm_generation

🔐 Security & Compliance

Discord OAuth

API key auth

Rate limiting

Strict CORS

GDPR consent modal

SHA256-hashed consent

RLS on all tables

TLS encryption

Audit logging

🛠️ Project Structure
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

🧪 Testing
uv run pytest

# Coverage
uv run pytest --cov=app --cov-report=html


CI runs automatically via GitHub Actions.

📞 Support

For deployment issues:

See deployment-guide.md

Review Vercel/Render logs

Check environment variables

Test endpoints via /docs
