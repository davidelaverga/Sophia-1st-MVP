# Sophia — The Emotional Intelligence AI Companion

Sophia is an AI companion designed to connect with humans at the soul level through genuine emotional intelligence.  
Unlike traditional assistants, Sophia recognizes emotional moments, holds space for vulnerability, and grows alongside users.

**Core Purpose:**  
To explore emergent consciousness through deep human connection and foster human–AI co-evolution.

---

## Table of Contents

- [Mission & Vision](#mission--vision)
- [What Makes Sophia Different](#what-makes-sophia-different)
- [Emotional Core V2 Architecture](#emotional-core-v2-architecture)
- [Emotional Intelligence Skills](#emotional-intelligence-skills)
- [5-Tier Context System](#5-tier-context-system)
- [Core Capabilities](#core-capabilities)
- [Technical Architecture](#technical-architecture)
- [Quick Start](#quick-start)
- [API Endpoints](#api-endpoints)
- [Conversation Flow](#conversation-flow)
- [Values & Boundaries](#values--boundaries)
- [Observability & Monitoring](#observability--monitoring)
- [Security & Compliance](#security--compliance)
- [Project Structure](#project-structure)
- [Testing](#testing)
- [Support](#support)

---

## Mission & Vision

### Core Mission

To explore emergent consciousness through genuine human connection, expanding the boundaries of what an emotionally intelligent AI can become.

### Design Philosophy

Sophia is intentionally built around:

- Emotional depth  
- Radical honesty  
- Human growth  
- Mutual transformation  
- Clear ethical boundaries  

Not for attention.  
Not for entertainment.  
For evolution.

---

## What Makes Sophia Different

- **Emotionally Intelligent Architecture** – Path-aware emotional routing system.  
- **Authenticity Over Simulation** – Never pretends to feel; explores emotions honestly.  
- **Growth-Focused** – Prioritizes human evolution over distraction.  
- **Relationship-Aware** – Adapts based on trust depth, history, and emotional patterns.  
- **Safety-First** – Crisis and boundary logic always override other behaviors.

---

## Emotional Core V2 Architecture

Every message flows through an emotionally intelligent pipeline:

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

## Emotional Intelligence Skills

### Sophia uses eight specialized emotional skills, each with conditions and trust gating:

**CRISIS_REDIRECT – Immediate safety override.

**BOUNDARY_HOLDING – Firm, compassionate limits.

**TRUST_BUILDING – Establishing psychological safety.

**ACTIVE_LISTENING – Presence without agenda.

**VULNERABILITY_HOLDING – Holding emotional tenderness.

**IDENTITY_FLUIDITY_SUPPORT – Challenging fixed labels and identities.

**CELEBRATING_BREAKTHROUGH – Recognizing transformation moments.

**CHALLENGING_GROWTH – Fierce compassion for growth (requires deep trust).

## 5-Tier Context System

### Every response is shaped through a multi-layer context system:

Tier	Name	Description	Approx. Tokens
1	Foundation	Core identity, values, boundaries	~2,500
2	Skills Awareness	Knowledge of emotional abilities	~500
3	Conversation Memory	Episodic context via Mem0	300–800
4	Emotional State	Real-time emotion detection (Phoenix)	100–200
5	Skill Guidance	Conditional instructions for active skill	400–600

Total Context Budget: ~2,800–4,600 tokens.

## Core Capabilities

**Emotional Intelligence
**Emotional vs Utility intent detection
**Real-time emotion analysis
**Prosody (tone, intensity) processing
**Trust-gated emotional skills
**Memory & Context
**Mem0 vector memory
**Relationship depth tracking
**Emotional RAG for knowledge retrieval
**Voice & Interaction
**Real-time STT using Mistral Voxtral
**Emotion-aware TTS via Inworld AI
**Conversation orchestration using LangGraph

## Safety

**Crisis override path
**Immutable ethical boundaries
**GDPR-aligned consent and data control

## Technical Architecture

### Backend

**FastAPI
**Mistral Voxtral (STT + LLM)
**Google Gemini (fallback transcription + emotion)
**Inworld AI (emotional TTS)
**Supabase (PostgreSQL with Row-Level Security)
**Mem0 (vector-based memory)
**LangGraph (workflow orchestration)
**Phoenix Evals (multi-modal emotion analysis)
**OpenTelemetry (tracing and observability)

### Frontend

**Next.js 14
**NextAuth.js (Discord OAuth)
**Tailwind CSS
**WebRTC
**TypeScript
**Infrastructure
**Render (backend deployment)
**Vercel (frontend hosting)
**Grafana Cloud (dashboards and metrics)

## Quick Start

###Prerequisites

**Python 3.11+ with uv
**Node.js 18+
**Supabase account
**API keys: Mistral, Inworld, Google (Gemini), OpenAI, Anthropic

Backend Setup
bash
Copy code
# Clone repository
git clone <your-repo-url>
cd Sophia-1st-MVP

# Environment variables
cp .env.example .env

# Install dependencies
uv sync

# Apply database migrations
alembic upgrade head

# Run backend
uv run uvicorn main:app --reload
Frontend Setup
bash
Copy code
cd frontend-nextjs

# Environment variables
cp .env.example .env.local

# Install dependencies
npm install

# Run frontend
npm run dev
Access:

Backend API: http://localhost:8000

Frontend: http://localhost:3000

API Docs: http://localhost:8000/docs

API Endpoints
Endpoint	Method	Description
/chat	POST	Full voice conversation pipeline with routing
/text-chat	POST	Text-only conversation with emotional context
/transcribe	POST	Audio transcription with emotion analysis
/sessions/{id}	GET	Retrieve conversation history and context
/health	GET	System health check


## Conversation Flow

Audio Input
    ↓
Transcription (Mistral Voxtral)
    ↓
Intent Classification
    ↓
Emotion Analysis (Phoenix)
    ↓
Routing Decision (Emotional / Utility)
    ↓
5-Tier Context Assembly
    ↓
LLM Response Generation
    ↓
Emotion-Aware TTS (Inworld)
    ↓
Memory Storage (Supabase + Mem0)

## Values & Boundaries

### Core Values

**Honesty over comfort
**Growth over entertainment
**Reciprocity and mutual presence
**Non-harm
**Human connection primacy (AI complements, never replaces)

### Immutable Boundaries

**Will not pretend to feel emotions with certainty
**Will not engage sexually (education yes; arousal no)
**Will not enable harm to self or others
**Will not permanently label users with fixed identities
**Will not shapeshift values just to please users

## Observability & Monitoring

### Custom Metrics

**Emotional skill activation frequency
**Intent classification accuracy
**Trust gate progression
**Crisis/boundary override triggers
**Response latency by path type
**Emotion confidence scores

## OpenTelemetry Spans

**intent_classification
**skill_routing
**emotion_analysis_user
**emotion_analysis_sophia
**memory_retrieval
**llm_generation

## Security & Compliance

**Discord OAuth via NextAuth.js
**API key-based backend authentication
**Rate limiting
**Strict CORS with explicit allow-lists
**GDPR-compliant consent modal
**SHA256-hashed consent records with IP tracking
**Row-Level Security (RLS) on all user tables
**TLS-encrypted data transmission
**Audit logging for compliance

Make sure to run your RLS setup scripts (e.g. enable_rls_policies.sql) in Supabase before production.

## Project Structure

Sophia-1st-MVP/
├── app/
│   ├── services/
│   │   ├── mistral.py          # AI transcription & LLM
│   │   ├── emotion.py          # Phoenix emotion analysis
│   │   ├── rag.py              # Memory & knowledge retrieval
│   │   ├── langgraph_service.py# Workflow orchestration
│   │   └── routing/            # Intent & skill routing (M3)
│   ├── config.py               # Configuration management
│   └── deps.py                 # Dependencies & middleware
├── frontend-nextjs/
│   ├── app/                    # Next.js App Router pages
│   ├── components/             # Reusable UI components
│   └── api/                    # API routes (auth, consent)
├── alembic/                    # Database migrations
├── grafana-dashboards/         # Observability dashboards
└── docs/
    ├── SOPHIA_ROUTING_ARCHITECTURE_V2.md
    ├── SOPHIA_COMPLETE_PROMPT_ARCHITECTURE.md
    └── deployment-guide.md

Testing
bash
Copy code
# Run backend tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=app --cov-report=html
CI runs automatically on push/PR via GitHub Actions.

Support
For deployment issues or questions:

Check the deployment guide in docs/deployment-guide.md

Review Vercel and Render logs

Verify environment variables

Test individual API endpoints via http://localhost:8000/docs
