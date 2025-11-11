# Observability Guide

## Overview
Sophia exposes traces, metrics, and logs to help diagnose latency, consent enforcement, and AI-provider behavior. This guide explains how to enable telemetry locally and in production.

## Tracing (OpenTelemetry)
- **Instrumentation:** `main.py` configures `opentelemetry-sdk` and adds spans for STT, LLM generation, TTS, emotion analysis, and Supabase persistence. The FastAPI instrumentation automatically records HTTP request spans.
- **Supabase spans:** `app/services/supabase.py` wraps storage uploads, consent lookups, and row inserts with spans (`supabase.*`), recording session IDs and error metadata without exposing raw Discord IDs.
- **Export:** Set `OTEL_EXPORTER_OTLP_ENDPOINT` and (optionally) `OTEL_EXPORTER_OTLP_HEADERS` in `.env` to stream traces to Grafana Cloud, Honeycomb, or any OTLP collector. Without these values, traces remain in-process for debugging via logs.
- **Key spans:** `chat`, `defi_chat`, `llm_generation`, `tts_synthesis_upload`, `emotion_analysis_user`, `emotion_analysis_sophia`.

### Local Jaeger Setup
```bash
docker run --rm -it -e COLLECTOR_OTLP_ENABLED=true -p 16686:16686 -p 4317:4317 jaegertracing/all-in-one:latest
# Then set OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317 in .env
```
Open http://localhost:16686 to inspect request traces.

## Metrics
Although native metrics are not yet exported, the following can be derived from spans or logged counters:
- Total request latency by endpoint.
- STT/LLM/TTS component timings (span attributes).
- Consent enforcement failures (403 responses in logs).
- Redis cache hit/miss ratios (planned for Phase 1).
- Startup duration: `main.py` logs the import-to-ready latency (`Startup initialization completed …`), helping confirm the ≤12 s cold-start target.

Integrate Prometheus or Grafana Agent in Phase 1 to emit explicit counters and histograms.

## Logging
- Structured via Python’s `logging` with `INFO` level by default (override via `LOG_LEVEL`).
- Important log categories:
  - `sophia-backend`: startup config, CORS list, API middleware decisions.
  - `emotion`: Phoenix and fallback sentiment analysis.
  - `supabase`: insert failures, consent lookups, UUID sanitization warnings.
  - `tts`, `mistral`: external AI provider calls and fallbacks.

## Dashboards
- Grafana dashboards (stored under `grafana-dashboards/`) track latency, fallback usage, emotion confidence, and error rates. Import the JSON into your Grafana instance after configuring OTLP export.

## Troubleshooting Playbook
| Symptom | Likely Cause | Actions |
| --- | --- | --- |
| HTTP 401 on protected endpoints | Missing API key | Verify `Authorization` header and `API_KEYS` list in `.env`. |
| HTTP 403 on chat endpoints | Consent missing | Confirm `X-Discord-Id` header, ensure Supabase consent row exists. |
| High STT latency | Voxtral outage | Check `mistral` logs, fallbacks to Gemini; consider rate limiting adjustments. |
| No traces in collector | OTLP misconfigured | Ensure endpoint/headers set; confirm collector reachable; check startup logs for validation errors. |
| Cold start >12 s | Lazy initialization missing | Profile startup spans; move non-critical setup to runtime; ensure Supabase client preloads. |

## Next Steps
Phase 1 tasks include:
- Enabling Row-Level Security in Supabase and logging policy denials.
- Adding automated dependency vulnerability scans (Dependabot/Snyk).
- Emitting structured metrics for rate limiting, TTS fallback rates, and LangGraph evaluation status.
