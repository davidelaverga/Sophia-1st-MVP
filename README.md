# Sophia DeFi AI Assistant

> **Milestone 4 Complete**: Production-ready voice AI assistant for DeFi education with full observability and GDPR compliance.

Sophia is an intelligent voice assistant specifically designed for DeFi (Decentralized Finance) education and guidance. It combines advanced AI capabilities with a modern web interface to provide personalized, emotion-aware conversations about cryptocurrency, yield farming, staking, and DeFi protocols.

## 🎯 **Project Overview**

### **Core Capabilities**
- **Voice Conversations**: Real-time speech-to-text, AI response generation, and text-to-speech
- **Emotion Analysis**: Multi-modal emotion detection for both user input and AI responses
- **DeFi Expertise**: Specialized knowledge base with 20+ FAQ categories covering DeFi concepts
- **RAG Integration**: Vector-based knowledge retrieval for accurate, contextual responses
- **Session Memory**: Persistent conversation context using LangGraph workflows

### **Production Features**
- **Discord OAuth**: Seamless user authentication and profile management
- **GDPR Compliance**: Comprehensive consent management with hashed record storage
- **Real-time Observability**: OpenTelemetry integration with Grafana Cloud dashboards
- **Scalable Architecture**: Containerized deployment on Fly.io with auto-scaling

## 🏗️ **Architecture**

### **Backend Stack**
- **FastAPI**: High-performance Python web framework
- **Mistral AI**: Voxtral for transcription, LLM for response generation
- **Google Gemini**: Fallback transcription and emotion analysis
- **Inworld AI**: Text-to-speech synthesis with emotion
- **Supabase**: PostgreSQL database with real-time features
- **LangGraph**: Conversation workflow orchestration
- **OpenTelemetry**: Distributed tracing and metrics

### **Frontend Stack**
- **Next.js 14**: React framework with App Router
- **NextAuth.js**: Discord OAuth integration
- **Tailwind CSS**: Utility-first styling with crypto theme
- **WebRTC**: Real-time voice recording and playback
- **TypeScript**: Type-safe development

## 🚀 **Quick Start**

### **Local Development**

1. **Clone and Setup Backend**
```bash
git clone <repository>
cd Sophia-1st-MVP

# Create environment file
cp .env.template .env
# Edit .env with your API keys and service URLs

# Install dependencies
pip install -r requirements.txt

# Run backend
uvicorn main:app --reload
```

2. **Setup Frontend**
```bash
cd frontend-nextjs

# Install dependencies
npm install

# Create environment file
cp .env.example .env.local
# Edit .env.local with your configuration

# Run frontend
npm run dev
```

3. **Access Application**
- Backend API: http://localhost:8000
- Frontend: http://localhost:3000
- API Documentation: http://localhost:8000/docs

### **Environment Configuration**

All configuration lives in environment variables. Use the provided [.env.template](./.env.template) as a reference, copying it to `.env` for local development. Key sections include:

- **Core settings:** `APP_ENV`, rate limiting, logging level.
- **Supabase:** `SUPABASE_URL`, `SUPABASE_KEY`, optional `SUPABASE_DB_DSN`, and a non-zero `SUPABASE_DEFAULT_USER_ID`.
- **API security:** `API_KEYS`, `CORS_ALLOWED_ORIGINS`, and paths that should remain public (`API_PUBLIC_PATHS`).
- **AI providers:** Mistral, Inworld, Google (Gemini), OpenAI, and Anthropic keys as needed.
- **Observability:** OTLP endpoint and headers for OpenTelemetry exporters.

🚨 **Production note:** Every deployment must set `API_KEYS`, Supabase credentials, and the external AI keys the environment relies on. Missing mandatory settings will prevent the backend from starting, as enforced by the startup validator.

### **Supabase Database & Migrations**

- Export a direct Postgres connection string from Supabase (`Settings → Database → Connection string`) and set it as `SUPABASE_DB_DSN` in your environment.
- Apply the ORM-managed schema by running `alembic upgrade head`. The Alembic configuration automatically picks up `SUPABASE_DB_DSN` when invoked from the repo root.
- Use the SQLAlchemy helpers in `app/db/session.py` (`session_scope`, `get_engine`, `get_session_factory`) whenever the backend needs ORM access to Supabase.
- The declarative models in `app/db/models.py` mirror the SQL scripts in this repo (`users`, `conversation_sessions`, `emotion_scores`, `user_consents`). Regenerate migrations with `alembic revision --autogenerate -m "<message>"` after structural changes.

### **Testing & CI**

- Run `pytest` from the repository root to execute the backend test suite. Consent-dependent tests rely on the `SUPABASE_DEFAULT_USER_ID` value provided in `.env.template`.
- A GitHub Actions workflow (`.github/workflows/ci.yml`) installs dependencies and runs `pytest` automatically on pushes and pull requests. Ensure new tests are deterministic and do not require external network access.
- Automated dependency scanning is enabled via Dependabot (`.github/dependabot.yml`), generating weekly PRs for Python packages; treat security updates as high priority.

### **Production Deployment**

See [deployment-guide.md](deployment-guide.md) for complete production setup instructions, including container builds, Fly.io configuration, and frontend deployment on Vercel.

Before granting end-user access, execute [`enable_rls_policies.sql`](./enable_rls_policies.sql) in the Supabase SQL editor using the service role to enforce row-level security on `conversation_sessions` and `emotion_scores`.

## 📊 **API Endpoints**

| Endpoint | Method | Description |
|----------|---------|-------------|
| `/` | GET | Serve frontend interface |
| `/health` | GET | System health check |
| `/transcribe` | POST | Audio transcription only |
| `/chat` | POST | Full voice conversation pipeline |
| `/defi-chat` | POST | Enhanced DeFi conversation with LangGraph |
| `/text-chat` | POST | Text-only DeFi conversation |
| `/sessions/{id}` | GET | Retrieve session memory |

## 🎤 **Voice Conversation Flow**

1. **Audio Input**: User provides voice or text input
2. **Transcription**: Mistral Voxtral converts speech to text (Gemini fallback)
3. **Emotion Analysis**: Phoenix Evals analyzes user sentiment from audio
4. **Intent Recognition**: DeFi-specific intent classification
5. **RAG Retrieval**: Vector search through DeFi knowledge base
6. **Response Generation**: Context-aware AI response via Mistral LLM
7. **TTS Synthesis**: Inworld AI converts response to speech
8. **Emotion Analysis**: AI response sentiment analysis
9. **Storage**: Session data persisted to Supabase

## 🧠 **DeFi Knowledge Base**

Sophia includes a comprehensive RAG system with 20+ categories:

- **Basics**: DeFi fundamentals, stablecoins, smart contracts
- **Yield Farming**: Strategies, risks, protocol selection
- **Staking**: Mechanisms, rewards, validator selection
- **Trading**: DEXs, slippage, MEV protection
- **Risk Management**: Impermanent loss, smart contract risks
- **Advanced Topics**: Flash loans, governance tokens, vault strategies

## 🎨 **Frontend Features**

### **Voice Interface**
- Hold-to-talk recording with visual feedback
- Real-time transcription display
- Automatic audio playback of responses
- Multi-format audio support (WAV, WebM, MP3)

### **Chat Interface**
- Text and voice message support
- Session-based conversation history
- Quick-action buttons for common queries
- Real-time typing indicators

### **Emotion Visualization**
- Color-coded emotion indicators (🟢 positive, ⚪ neutral, 🔴 negative)
- Confidence percentage display
- Real-time emotion tracking for both user and AI

### **User Experience**
- Discord OAuth login
- GDPR consent management
- Responsive design for mobile/desktop
- Crypto-themed UI with floating animations

## 📈 **Observability & Monitoring**

### **Grafana Dashboards**
1. **Latency Overview**: STT/LLM/TTS performance breakdown
2. **Emotion Confidence Trends**: Daily emotion analytics
3. **Errors & Fallbacks**: Service health and error monitoring

### **Custom Metrics**
- Total conversation roundtrip time
- Individual component latencies (STT, LLM, TTS)
- Emotion confidence scores
- API error rates and fallback usage
- User engagement patterns

### **OpenTelemetry Spans**
- `emotion_analysis_user` - User emotion processing
- `emotion_analysis_sophia` - AI emotion processing
- `stt_transcription` - Speech-to-text timing
- `llm_generation` - Response generation timing
- `tts_synthesis_upload` - Text-to-speech timing

## 🔐 **Security & Compliance**

### **Authentication**
- Discord OAuth via NextAuth.js
- API key-based backend authentication (enforced by middleware on every protected route)
- Rate limiting via SlowAPI (configurable through `API_RATE_LIMIT`)
- CORS configuration with explicit allow-list driven by `CORS_ALLOWED_ORIGINS`

### **GDPR Compliance**
- Comprehensive consent modal with data processing disclosure
- SHA256 hashed consent records with IP tracking
- User data blocking until consent granted (API endpoints require `X-Discord-Id` header with confirmed consent)
- Consent withdrawal capability
- Row-Level Security (RLS) policies on Supabase tables ensure users only access their own conversations; apply the SQL in [`enable_rls_policies.sql`](./enable_rls_policies.sql) when provisioning the database.

### **Security & Observability Docs**
- Review [SECURITY.md](./SECURITY.md) for responsible disclosure guidelines, dependency update cadence, and supported versions.
- Consult [observability.md](./observability.md) to enable OpenTelemetry collection, inspect metrics, and interpret Grafana dashboards.

### **Data Protection**
- Non-root Docker containers
- Environment variable security
- Encrypted data transmission
- Audit logging for compliance

## 🛠️ **Development**

### **Project Structure**
```
├── app/                          # Backend application
│   ├── services/                 # Core services (AI, emotion, RAG)
│   ├── config.py                 # Configuration management
│   └── deps.py                   # Dependencies and middleware
├── frontend-nextjs/              # Next.js frontend
│   ├── app/                      # App router pages and components
│   ├── components/               # Reusable UI components
│   └── api/                      # API routes (auth, consent)
├── grafana-dashboards/           # Observability dashboards
├── fly.toml                      # Fly.io deployment config
├── Dockerfile                    # Production container
└── deployment-guide.md           # Complete deployment instructions
```

### **Key Services**
- `mistral.py` - AI transcription and response generation
- `emotion.py` - Multi-modal emotion analysis
- `rag.py` - DeFi knowledge retrieval system
- `langgraph_service.py` - Conversation workflow orchestration
- `evaluations.py` - AI response quality assessment

## 🎯 **Performance Targets**

- **Response Latency**: <2.5s average roundtrip time
- **Emotion Accuracy**: >90% confidence consistency
- **API Availability**: >99.9% uptime
- **Error Rate**: <1% for all endpoints

## 🚀 **Deployment**

### **Production URLs**
- **Backend**: `https://sophia-1st-mvp-xjml.onrender.com`
- **Frontend**: `sophia-1st-mvp-git-main-davidelavergas-projects.vercel.app`
- **Monitoring**: Grafana Cloud dashboards

### **Environment Variables**
See `.env.staging` and `frontend-nextjs/.env.example` for complete configuration templates.

## 📝 **License**

This project is part of the Sophia DeFi AI Assistant MVP development.

## 🤝 **Contributing**

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests and documentation
5. Submit a pull request

## 📞 **Support**

For deployment issues or questions:
1. Check the [deployment guide](deployment-guide.md)
2. Review Vercel and Render logs
3. Verify environment variables
4. Test API endpoints individually
