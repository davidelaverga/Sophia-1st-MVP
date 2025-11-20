# Sophia Project Roadmap — Phase 0 & Phase 1

## Overview
This roadmap captures the sequential work Codex will execute during the stabilization effort. It is organized into Phase 0 (first month) and Phase 1 (second month), including task descriptions, priorities, tags, and explicit success criteria.

## Phase 0 — Foundational Fixes (Month 1)
| Task | Tag | Priority | Description | Expected Outcome |
| --- | --- | --- | --- | --- |
| Harden CORS configuration | Security | High | Restrict accepted origins to trusted frontend domains, ensure preflight handling, and return the correct CORS headers. | Trusted clients make cross-domain requests without errors; untrusted origins are rejected. |
| Enforce API-key validation globally | Security | High | Add middleware that requires a valid API key on every protected route, with explicit handling for any public endpoints. | 100% of protected requests require a valid key; unauthorized requests receive HTTP 401. |
| Validate configuration at startup | Config | High | Check all mandatory environment variables during startup, fail fast with clear errors, provide defaults for optional values, and allow a developer mode with mock services when keys are absent. | Startup fails with descriptive errors if critical settings are missing; developer mode works without external API keys. |
| Centralize Supabase initialization | Backend | Medium | Move creation of the Supabase client into the application bootstrap to avoid per-request instantiation and reduce latency. | Supabase client created once at startup, eliminating connection churn and cold-start lag. |
| Test coverage for user consent flows | Testing | High | Write unit/integration tests covering consent-required endpoints, ensuring 403 responses when consent is absent. | ≥5 new tests verifying consent enforcement; all pass. |
| Configure CI pipeline for build and tests | DevOps | High | Add continuous integration (e.g., GitHub Actions) to install dependencies, run linters, and execute tests on every push/PR. | CI runs automatically and blocks merges when checks fail. |
| Eliminate zero UUIDs | Bugfix | Medium | Replace placeholder zero UUIDs with `NULL` or generated UUIDs, and add validation that prevents them from being stored. | No zero UUIDs remain in code or data; guards prevent future occurrences. |
| Update dependencies | Maintenance | Medium | Audit and upgrade outdated libraries, prioritizing security fixes, and run regression tests afterward. | Dependencies on supported versions; security warnings resolved. |
| Publish `.env.template` | Documentation | Medium | Document all environment variables with descriptions, defaults, and required flags. | `.env.template` added with annotated entries for every variable. |
| Refresh `README.md` | Documentation | Medium | Update project overview, setup instructions, environment configuration, testing guide, and reference new security/observability docs. | README reflects current architecture, dev workflow, and safety posture. |
| Draft ADR-001 (configuration validation & dev mode) | Architecture | Medium | Record the decision around strict configuration validation with a dev-mode exception, including context and alternatives. | `docs/architecture/ADR-001.md` created, capturing rationale and future implications. |

## Phase 1 — Security & Observability Enhancements (Month 2)
| Task | Tag | Priority | Description | Expected Outcome |
| --- | --- | --- | --- | --- |
| Enable database Row-Level Security | Security | High | Activate RLS policies in Supabase/PostgreSQL that restrict access to a user’s own records. | ✅ RLS policies and SQL script committed; backend derives per-user UUIDs (2025-01-07). |
| Expand OpenTelemetry traces & metrics | Observability | Medium | Instrument HTTP handlers, Supabase calls, and external API interactions; export OTEL data to the configured backend and document usage. | ✅ Supabase spans added, startup latency logged, observability guide updated (2025-01-07). |
| Increase automated test coverage (≥20 scenarios) | Testing | Medium | Add tests for authentication, CRUD flows, external integration mocks, and edge cases to reach at least 20 unique scenarios. | ✅ Additional Supabase identity tests push suite beyond 20 scenarios (2025-01-07). |
| Integrate dependency vulnerability scanning | Security | Medium | Introduce Dependabot/Snyk/npm audit into CI, failing builds on High/Medium vulnerabilities. | ✅ Dependabot weekly scan configured via `.github/dependabot.yml` (2025-01-07). |
| Improve cold-start performance | Performance | Low | Profile startup, apply lazy initialization or parallelization, and confirm cold-start time ≤12 seconds. | ✅ SentenceTransformer lazy load + startup telemetry reduce import work; log shows ≤12 s target (2025-01-07). |
| Address remaining Medium vulnerabilities | Security | Low | Review scanner reports, remediate or document any Medium/Low issues, and update `SECURITY.md` with disposition. | ✅ SECURITY.md documents clean state; Dependabot ensures future coverage (2025-01-07). |
| Create `SECURITY.md` policy | Documentation | Medium | Outline vulnerability disclosure process, response timelines, dependency management policy, and supported versions. | `SECURITY.md` available at repository root with up-to-date guidance. |
| Publish `observability.md` | Documentation | Medium | Document available metrics, traces, dashboards, and instructions for viewing OTEL data. | `observability.md` explains the monitoring stack and debugging workflows. |

## Acceptance Criteria Summary
- No unresolved High/Medium vulnerabilities by end of Phase 1.
- ≥20 key scenarios covered by automated tests.
- Startup configuration validation prevents misconfigured launches; dev mode supports mock operation.
- Application cold-start time ≤12 seconds.
- Consent enforcement and API-key validation apply to 100% of protected requests.
- Documentation set includes updated README, `.env.template`, ADR-001, `SECURITY.md`, and `observability.md`.

## Next Steps
Codex will progress through Phase 0 tasks first, raising follow-up ADRs or docs as decisions require. Phase 1 begins once Phase 0 acceptance criteria are satisfied and validated through CI.
