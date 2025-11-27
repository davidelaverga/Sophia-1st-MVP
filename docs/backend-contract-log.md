# Frontend Integration Log (Parts 0–6)

This log tracks backend dependencies and the temporary strategies we applied while the API layer is still under construction.

## Consent & Privacy (Part 5)

| Endpoint | Status | Frontend handling |
| --- | --- | --- |
| `GET /api/privacy/status` | Pending | Mockable via `NEXT_PUBLIC_MOCK_PRIVACY=true`. Consent gate shows retry + fallback continue. |
| `POST /api/privacy/consent` | Pending | Same mock flag; errors surface inline. |
| `GET /api/privacy/export` | Not implemented (404) | Button now shows “Export endpoint isn’t available yet” when 404. Mock flag downloads a dummy JSON. |
| `DELETE /api/privacy/delete` | Not implemented (404) | Two-step delete; 404 shows “endpoint isn’t available yet”. Mock flag resolves instantly. |

Next actions once backend is ready:
1. Remove `NEXT_PUBLIC_MOCK_PRIVACY` flag (or default to `false`).
2. Verify 200 responses to ensure UI hides warning messages.

## Inline Feedback (Part 6)

| Endpoint | Status | Frontend handling |
| --- | --- | --- |
| `POST /api/conversation/feedback` | Pending | Feedback strip/toast shows friendly error and stays visible until submission succeeds. Telemetry still records intent. |

## Voice personality (Part 0 follow-up)

Backend still returns DeFi-oriented replies because prompts/RAG no se han actualizado. Frontend no puede cambiarlo; se documenta aquí para el roadmap.

---

**Mock toggle:** set `NEXT_PUBLIC_MOCK_PRIVACY=true` in `.env.local` to exercise flows without backend support. Remove once APIs are deployed.

