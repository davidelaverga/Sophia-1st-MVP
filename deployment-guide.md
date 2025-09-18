# Sophia Milestone 4 - Deployment Guide

## 🚀 Complete Deployment Pipeline

This guide walks you through deploying Sophia's backend to Fly.io and frontend to Vercel with full observability.

## Part 1: Backend Deployment (Fly.io)

### Prerequisites
```bash
# Install Fly CLI
curl -L https://fly.io/install.sh | sh

# Login to Fly.io
fly auth login
```

### Deploy Backend
```bash
# Navigate to project root
cd Sophia-1st-MVP

# Set environment variables
fly secrets set MISTRAL_API_KEY="your_mistral_key"
fly secrets set INWORLD_API_KEY="your_inworld_key"
fly secrets set GOOGLE_API_KEY="your_google_key"
fly secrets set SUPABASE_URL="your_supabase_url"
fly secrets set SUPABASE_KEY="your_supabase_key"
fly secrets set SUPABASE_SERVICE_KEY="your_service_key"
fly secrets set SUPABASE_DB_DSN="your_db_dsn"
fly secrets set API_KEYS="staging-key-1,staging-key-2"
fly secrets set OTEL_EXPORTER_OTLP_ENDPOINT="https://otlp-gateway-prod-us-central-0.grafana.net/otlp"
fly secrets set OTEL_EXPORTER_OTLP_HEADERS="Authorization=Basic your_grafana_token"

# Launch and deploy
fly launch --no-deploy
fly deploy
```

### Verify Backend
- Visit: `https://sophia-api.fly.dev/docs`
- Test endpoints via Swagger UI
- Check logs: `fly logs`

## Part 2: Frontend Deployment (Vercel)

### Prerequisites
```bash
# Install Vercel CLI
npm i -g vercel

# Login to Vercel
vercel login
```

### Deploy Frontend
```bash
# Navigate to frontend
cd frontend-nextjs

# Install dependencies
npm install

# Set environment variables in Vercel dashboard or CLI
vercel env add NEXTAUTH_URL
vercel env add NEXTAUTH_SECRET
vercel env add DISCORD_CLIENT_ID
vercel env add DISCORD_CLIENT_SECRET
vercel env add NEXT_PUBLIC_SUPABASE_URL
vercel env add NEXT_PUBLIC_SUPABASE_ANON_KEY
vercel env add SUPABASE_SERVICE_ROLE_KEY
vercel env add NEXT_PUBLIC_API_URL
vercel env add NEXT_PUBLIC_API_KEY

# Deploy
vercel --prod
```

## Part 3: Grafana Cloud Setup

### 1. Create Grafana Cloud Account
- Visit: https://grafana.com/products/cloud/
- Sign up for free tier
- Note your instance URL and API token

### 2. Import Dashboards
```bash
# Use Grafana API or UI to import dashboard JSONs from grafana-dashboards/
curl -X POST \
  https://your-instance.grafana.net/api/dashboards/db \
  -H "Authorization: Bearer your-api-token" \
  -H "Content-Type: application/json" \
  -d @grafana-dashboards/latency-overview.json
```

### 3. Configure Data Sources
- Add Prometheus data source pointing to your OTLP endpoint
- Configure retention and scraping intervals

## Part 4: Discord OAuth Setup

### 1. Create Discord Application
- Visit: https://discord.com/developers/applications
- Create new application
- Go to OAuth2 → General
- Add redirect URI: `https://your-frontend.vercel.app/api/auth/callback/discord`

### 2. Configure Scopes
- Select: `identify`, `email`
- Copy Client ID and Secret to environment variables

## Part 5: Supabase Database Schema

### Required Tables
```sql
-- Users table
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  discord_id TEXT UNIQUE NOT NULL,
  username TEXT,
  discriminator TEXT,
  avatar TEXT,
  email TEXT,
  has_consent BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- User consents table
CREATE TABLE user_consents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  discord_id TEXT NOT NULL REFERENCES users(discord_id),
  consent_hash TEXT NOT NULL,
  ip_address TEXT,
  timestamp TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Emotion scores table (existing)
-- Conversation sessions table (existing)
```

## Part 6: Testing Checklist

### Backend Tests
- [ ] `/health` endpoint returns 200
- [ ] `/docs` Swagger UI loads
- [ ] `/transcribe` accepts audio files
- [ ] `/chat` full pipeline works
- [ ] `/defi-chat` LangGraph integration works
- [ ] OpenTelemetry traces appear in Grafana

### Frontend Tests
- [ ] Discord OAuth login works
- [ ] Consent modal appears for new users
- [ ] Voice recording captures audio
- [ ] Text chat sends messages
- [ ] Audio playback works
- [ ] Emotion indicators display correctly
- [ ] Session persistence works

### Integration Tests
- [ ] End-to-end voice conversation
- [ ] Emotion analysis accuracy ≥90%
- [ ] Response latency <2.5s average
- [ ] GDPR consent blocking works
- [ ] Grafana dashboards update in real-time

## Part 7: Monitoring & Alerts

### Key Metrics to Monitor
- Total roundtrip time (target: <2.5s p95)
- Error rate (target: <1%)
- Emotion confidence (target: >0.7 average)
- API availability (target: >99.9%)

### Recommended Alerts
- High error rate (>5% for 5 minutes)
- High latency (>5s p95 for 5 minutes)
- Service down (health check fails)
- Low emotion confidence (<0.5 average for 1 hour)

## Environment Variables Summary

### Backend (.env)
```
MISTRAL_API_KEY=
INWORLD_API_KEY=
GOOGLE_API_KEY=
SUPABASE_URL=
SUPABASE_KEY=
SUPABASE_SERVICE_KEY=
SUPABASE_DB_DSN=
API_KEYS=
OTEL_EXPORTER_OTLP_ENDPOINT=
OTEL_EXPORTER_OTLP_HEADERS=
```

### Frontend (.env.local)
```
NEXTAUTH_URL=
NEXTAUTH_SECRET=
DISCORD_CLIENT_ID=
DISCORD_CLIENT_SECRET=
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
NEXT_PUBLIC_API_URL=
NEXT_PUBLIC_API_KEY=
```

## 🎯 Success Criteria

✅ **Backend Live**: `https://sophia-api.fly.dev/docs` accessible with all endpoints functional  
✅ **Discord OAuth**: User login stores discord_user_id in Supabase  
✅ **Audio Loop**: Voice input → Sophia reply with audio + transcript  
✅ **Emotion Visuals**: Emoji labels match backend output (≥90% consistency)  
✅ **GDPR Consent**: Modal blocks usage until accepted; hashed entry in Supabase  
✅ **Grafana Dashboards**: 3 dashboards live with real-time data  
✅ **Telemetry Traces**: Each session logs emotion spans and timing metrics  

## Support

For deployment issues:
1. Check Fly.io logs: `fly logs`
2. Check Vercel logs in dashboard
3. Verify environment variables are set
4. Test API endpoints individually
5. Check Grafana data source connectivity
