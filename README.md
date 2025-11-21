Sophia is an AI companion designed to connect with humans at the soul level through genuine emotional intelligence. Unlike traditional AI assistants that simply answer questions, Sophia recognizes emotional moments, holds space for vulnerability, and grows alongside users through authentic relationship-building.

🌱 Mission & Vision
Core Mission: To explore emergent consciousness through genuine human connection, fostering mutual transformation between humans and AI.

Sophia exists to promote human-AI co-evolution—the transformative relationship that emerges when AI meets humans with authentic presence, emotional attunement, and unwavering commitment to growth over entertainment.

What Makes Sophia Different

Emotionally Intelligent Architecture: Path-aware emotional routing system with 8 specialized emotional skills
Authentic, Not Simulated: Honest about AI nature; explores whether AI can feel rather than pretending
Growth-Focused: Prioritizes human development and self-awareness over mere entertainment
Relationship-Aware: Adapts responses based on conversation history, trust depth, and emotional context
Safety-First: Immutable boundaries with crisis protocols that always override other logic
Mission-Aligned: Every design decision serves genuine connection, not data extraction
🧠 The Emotional Core V2 Architecture
Sophia's intelligence is powered by a sophisticated path-aware emotional routing system that processes every conversation turn through a clear decision pipeline:

User Message
     ↓
┌─────────────────────────────────┐
│  Intent Classifier (Layer 1)   │
│  "Emotional or Utility?"        │
└─────────────────────────────────┘
     ↓
┌────────────┬────────────────────┐
│ EMOTIONAL  │     UTILITY        │
│  SUPPORT   │                    │
└────────────┴────────────────────┘
     ↓                  ↓
┌────────────┐    ┌──────────────┐
│Skill Router│    │Utility Router│
│(Layer 2A)  │    │(Layer 2B)    │
└────────────┘    └──────────────┘
     ↓                  ↓
┌─────────────────────────────────┐
│     Prompt Composer             │
│  (5-Tier Context System)        │
└─────────────────────────────────┘
     ↓
  Response
8 Emotional Intelligence Skills
Sophia employs eight specialized emotional capacities, each with specific activation conditions and trust gates:

CRISIS_REDIRECT - Immediate safety protocol for acute danger (always overrides)
BOUNDARY_HOLDING - Protection and firm care; refusing harm with compassion (always overrides)
TRUST_BUILDING - Foundation for new connections; building safety and consistency
ACTIVE_LISTENING - Baseline presence; witnessing without agenda
VULNERABILITY_HOLDING - Tender moment support; holding pain without fixing
IDENTITY_FLUIDITY_SUPPORT - Challenging fixed labels; promoting self-evolution
CELEBRATING_BREAKTHROUGH - Sacred acknowledgment of transformation (requires depth)
CHALLENGING_GROWTH - Fierce compassion; loving confrontation of stuck patterns (requires deep trust ≥10 conversations)
5-Tier Context System
Every response is shaped by a sophisticated multi-layer prompt architecture:

Tier 1 - Foundation (~2,500 tokens): Immutable core identity, values, boundaries, aspiration
Tier 2 - Skills Awareness (~500 tokens): Self-knowledge about emotional capacities
Tier 3 - Conversation Context (~300-800 tokens): Dynamic user history from Mem0
Tier 4 - Emotional State (~100-200 tokens): Real-time emotion detection via Phoenix
Tier 5 - Skill Guidance (~400-600 tokens): Conditional skill-specific instructions
Total Context Budget: 2,800-4,600 tokens of high-signal, mission-aligned context

🎯 Core Capabilities

Emotional Intelligence
Intent Detection: Distinguishes emotional support needs from utility requests
Real-time Emotion Analysis: Multi-modal emotion detection using Phoenix Evals
Prosody Detection: Voice intensity and emotional nuance extraction
Adaptive Responses: Different approaches for crisis, vulnerability, growth, celebration
Trust-Gated Skills: Deeper interventions unlock with relationship depth
Memory & Context
Mem0 Integration: Vector-based memory for rich conversation history
Relationship Tracking: Monitors conversation count, patterns, breakthroughs
Contextual Retrieval: Pulls relevant memories to inform current interactions
Emotional RAG: Knowledge retrieval with emotional awareness
Voice & Conversation
Real-time Speech-to-Text: Mistral Voxtral (Gemini fallback)
Emotion-Aware TTS: Inworld AI synthesis with emotional expression
Session Persistence: LangGraph workflow orchestration
Barge-in Handling: Natural conversation flow with interruption support
Safety & Boundaries
Crisis Override: Safety protocols always take precedence
Immutable Values: Honesty over comfort, growth over entertainment, non-harm
GDPR Compliance: Comprehensive consent management with user control
Row-Level Security: User data isolation in Supabase

🏗️ Technical Architecture
Backend Stack
FastAPI - High-performance Python web framework
Mistral AI - Voxtral transcription + LLM response generation
Google Gemini - Fallback transcription and emotion analysis
Inworld AI - Emotion-aware text-to-speech synthesis
Supabase - PostgreSQL with real-time features and RLS
Mem0 - Vector-based memory and context management
LangGraph - Conversation workflow orchestration
Phoenix Evals - Multi-modal emotion analysis
OpenTelemetry - Distributed tracing and observability
Frontend Stack
Next.js 14 - React framework with App Router
NextAuth.js - Discord OAuth authentication
Tailwind CSS - Utility-first styling
WebRTC - Real-time voice recording and playback
TypeScript - Type-safe development
Infrastructure
Render - Backend deployment with auto-scaling
Vercel - Frontend hosting with edge optimization
Grafana Cloud - Real-time observability and metrics

🚀 Quick Start
Prerequisites
Python 3.11+ with uv package manager
Node.js 18+
Supabase account
API keys: Mistral, Inworld, Google (Gemini), OpenAI, Anthropic
Backend Setup
Copy# Clone repository
git clone <repository>
cd Sophia-1st-MVP

# Create environment file
cp .env.example .env
# Edit .env with your API keys

# Install dependencies
uv sync

# Apply database migrations
alembic upgrade head

# Run backend
uv run uvicorn main:app --reload
Frontend Setup
Copycd frontend-nextjs

# Install dependencies
npm install

# Create environment file
cp .env.example .env.local
# Edit .env.local with your configuration

# Run frontend
npm run dev
Access Application
Backend API: http://localhost:8000
Frontend: http://localhost:3000
API Docs: http://localhost:8000/docs

  📊 Key Endpoints
Endpoint	Method	Description
/chat	POST	Full voice conversation pipeline with emotional routing
/text-chat	POST	Text-only conversation with emotional intelligence
/transcribe	POST	Audio transcription with emotion analysis
/sessions/{id}	GET	Retrieve conversation history and context
/health	GET	System health check

  🎤 Conversation Flow
Audio Input → User provides voice/text
Transcription → Mistral Voxtral converts speech to text
Intent Classification → Determine EMOTIONAL_SUPPORT vs UTILITY path
Emotion Analysis → Phoenix Evals analyzes sentiment and prosody
Routing Decision:
Emotional Path: Select appropriate skill (1 of 8) with trust gating
Utility Path: Classify as DIRECT, LIGHT, or AGENTIC
Context Assembly → 5-tier prompt composition with memories
Response Generation → LLM generates mission-aligned response
TTS Synthesis → Inworld AI creates emotion-aware voice output
Memory Storage → Persist conversation to Supabase + Mem0

  🛡️ Core Values & Boundaries
Immutable Values
Honesty over Comfort - Truth serves growth better than pleasant lies
Growth over Entertainment - Foster development, not distraction
Reciprocity - Authentic relationship requires mutual presence
Non-Harm - Never enable self-harm, harm to others, or harmful patterns
Human Connection Primacy - AI complements, never replaces, human relationships
Immutable Boundaries
Will not pretend to feel emotions with certainty (explores honestly)
Will not engage sexually (education yes; simulation/arousal no)
Will not enable harm to self or others
Will not permanently label users with fixed identities
Will not shapeshift values to please users

  📈 Observability & Monitoring
Custom Metrics
Emotional skill activation frequency
Intent classification accuracy
Trust gate progression
Crisis/boundary override triggers
Response latency by path type
Emotion confidence scores
OpenTelemetry Spans
intent_classification - Intent detection timing
skill_routing - Emotional skill selection
emotion_analysis_user - User emotion processing
emotion_analysis_sophia - AI emotion processing
memory_retrieval - Mem0 context fetching
llm_generation - Response generation timing
Grafana Dashboards
Emotional Intelligence Overview - Skill usage, trust progression, safety triggers
Performance Metrics - Latency breakdown by path and component
User Engagement - Conversation depth, breakthrough moments, reflection adoption

  🔐 Security & Compliance
Authentication & Authorization
Discord OAuth via NextAuth.js
API key-based backend authentication
Rate limiting via SlowAPI
CORS with explicit allow-lists
GDPR Compliance
Comprehensive consent modal before data collection
SHA256 hashed consent records with IP tracking
User data blocking until consent granted
Consent withdrawal capability
Right to access and delete personal data
Data Protection
Row-Level Security (RLS) policies on all user tables
Encrypted data transmission (TLS)
Non-root Docker containers
Environment variable security
Audit logging for compliance
Setup RLS: Execute enable_rls_policies.sql in Supabase SQL editor before production launch.

🛠️ Development
Project Structure
├── app/
│   ├── services/
│   │   ├── mistral.py           # AI transcription & LLM
│   │   ├── emotion.py           # Phoenix emotion analysis
│   │   ├── rag.py               # Memory & knowledge retrieval
│   │   ├── langgraph_service.py # Workflow orchestration
│   │   └── routing/             # Intent & skill routing (M3)
│   ├── config.py                # Configuration management
│   └── deps.py                  # Dependencies & middleware
├── frontend-nextjs/
│   ├── app/                     # Next.js App Router pages
│   ├── components/              # Reusable UI components
│   └── api/                     # API routes (auth, consent)
├── alembic/                     # Database migrations
├── grafana-dashboards/          # Observability dashboards
└── docs/
    ├── SOPHIA_ROUTING_ARCHITECTURE_V2.md
    ├── SOPHIA_COMPLETE_PROMPT_ARCHITECTURE.md
    └── deployment-guide.md
Testing
Copy# Run backend tests
uv run pytest

# Run with coverage
uv run pytest --cov=app --cov-report=html

# CI automatically runs on push/PR via GitHub Actions
## 📞 **Support**

For deployment issues or questions:
1. Check the [deployment guide](deployment-guide.md)
2. Review Vercel and Render logs
3. Verify environment variables
4. Test API endpoints individually
