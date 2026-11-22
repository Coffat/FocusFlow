# 06 — End-to-End Product Validation (Phase 6)

- **Environment**: Live Docker staging (`http://127.0.0.1:3000` → `focusflow-backend:8000`, PG16, Redis 7, Mailpit `:8025`, Gemini live via Cobhub `host.docker.internal:8045`, `BILLING_RELEASE_MODE=FREE_BETA`).
- **Automated Gate Baseline**:
  - Backend: **916 unit/eval + 145 integration = 1,061 PASS (0 fail)**, `ruff`/`mypy --strict`/`lint-imports`/`check-api-contract.sh` (`0 drift`) PASS.
  - Frontend: `ng lint` PASS, **666/666 Vitest PASS**, `ng build --configuration production` PASS.
  - **Full Playwright E2E (10 specs / 37 tests)**: **`37 passed, 0 failed, 0 skipped (4.6m)`**.

---

## 14-Journey Validation Matrix (Distinguishing Deterministic vs Live Provider)

| # | User Journey | Verification Type | Evidence | Status |
|---|---|---|---|---|
| 1 | **Registration OTP → Login** | Live Staging (Mailpit + PG + Redis) | `auth.spec.ts` (8/8 PASS) + `p3_independent_sec_gate.py` | **PASS** |
| 2 | **Create Goal → Clarification (multi-round) → Milestones** | **Live External Gemini** | `e2e_full_workflow.spec.ts` (1.1m PASS) + `signal_e2e_evidence.spec.ts` (1.4m PASS) | **PASS** |
| 3 | **Schedule Proposal Review (`DRAFT`) → Apply (`OfficialSchedule`)** | **Live External Gemini** | `e2e_full_workflow.spec.ts` + `fit_capacity_scope_approval.spec.ts` + `roadmap-dashboard-sync.spec.ts` (5/5 PASS) | **PASS** |
| 4 | **Dashboard → Workspace → Start → Heartbeat → Finalize** | Live Staging | `p2b1-study-data-integrity.spec.ts` (PASS) + `signal_e2e_evidence.spec.ts` | **PASS** |
| 5 | **Tasks / Schedule / Analytics Synchronization** | Live Staging | `p2a-data-consistency.spec.ts` (10/10 PASS) | **PASS** |
| 6 | **Prove Mode (Real External Gemini Grading)** | **Live External Gemini** | `p2b2a-functional-completeness.spec.ts` (PASS, 11.2s) + P1B live smoke (`score=23, is_verified=True, answer_evidence=3`, reload khớp, duplicate `409`, `ai_usage_logs` khớp 100%) + P3 live quota check (`used_calls 0→1`) | **PASS** |
| 7 | **SRL Aggregation** | Live Staging + PG16 Integration | `test_srl_profile_aggregation_integration.py` + live `processed_events` (`account.aggregate_learner_srl_profile`) | **PASS** |
| 8 | **Outbox → Notifications** | Live Staging + PG16/Redis Integration | `p2b2b-functional-integration.spec.ts` + P1A live (`AvailabilityUpdatedEvent` PUBLISHED + `processed_events`) + `test_outbox_reliability_integration.py` (8/8 PASS) | **PASS** |
| 9 | **WebCal Create / Rotate / Revoke** | Live Staging | `p2b2a` + `p3_independent_sec_gate.py` (`rotate 200 → .ics 200 → delete 200 → .ics 404`) | **PASS** |
| 10 | **GDPR Data Export** | Live Staging | `p2b2b` + `p3_independent_sec_gate.py` (`200`, User A data only, 0 User B data) | **PASS** |
| 11 | **Free Beta Pricing & Disabled Checkout** | Live Staging | `p2b2b` Test #30 (`FE-API-05` PASS: banner hiển thị, nút disabled, `POST /checkout → 503`, `POST /mock-confirm → 403`) | **PASS** |
| 12 | **Logout → Re-login** | Live Staging | `auth.spec.ts` (8/8 PASS) + `p3_independent_sec_gate.py` | **PASS** |
| 13 | **Browser Refresh During AI Jobs** | Deterministic Unit Tests (`ai-sse.service.spec.ts`, `roadmap.service.spec.ts`) | `sessionStorage` F5 auto-reattachment & 401 SSE refresh verified in Vitest (666/666 PASS); **live mid-stream F5 browser test: NOT VERIFIED LIVE** | **PARTIAL (UNIT VERIFIED)** |
| 14 | **Cross-User Data Isolation (2 Users)** | Live Staging (2 Users) | `p3_independent_sec_gate.py` (13/13 PASS: Roadmaps/Tasks/StickyNotes/Export/WebCal/Admin RBAC) | **PASS** |

---

## Live Provider vs Deterministic Mock Distinction
- **Verified with Real External Model (Gemini via Cobhub)**: Goal Clarification (multi-round), Milestones SSE, Schedule Proposal SSE, Prove Mode Question Gen, Prove Mode Grading.
- **Verified Deterministically (Not Live-Verified)**: Weekly Review real-model output (unit/integration verified), RAG Embedding ingestion (`rag_embedding_configured=false` in staging), Google OAuth live consent & HTTPS Calendar webhooks (`calendar_webhook_https_ready=false`), Production transactional SMTP (staging uses Mailpit).
