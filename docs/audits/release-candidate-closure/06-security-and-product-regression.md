# 06 — Full Security & Product Regression Verification (Phase 6)

- **Commit Verified**: `release/free-beta-rc` @ `78ced25`
- **Verdict**: **PASS (ALL AUTOMATED, CONTRACT, E2E & 13/13 LIVE SECURITY GATES GREEN)**

---

## 1. Automated Quality Gates on `release/free-beta-rc` (`78ced25`)

| Gate | Command | Result |
|---|---|---|
| Backend Lint & Format | `uv run ruff check . && uv run ruff format --check .` | **PASS** (478 files formatted, 0 issues) |
| Backend Type Check | `uv run mypy --strict src` | **PASS** (327 source files, 0 issues) |
| Hexagonal Boundaries | `uv run lint-imports` | **PASS** (5/5 contracts kept, 0 broken) |
| Backend Unit + AI Evals | `uv run pytest tests/unit tests/ai_evals tests/evaluation tests/test_*.py --tb=short -q` | **PASS** (**916 passed, 1 skipped**, 0 failed) |
| Backend Integration (PG16 + Redis 7) | `uv run pytest tests/integration -m "not live_cobhub and not live_embedding" --tb=short -q` | **PASS** (**145 passed, 2 deselected**, 0 failed) |
| OpenAPI ↔ `schema.d.ts` | `bash scripts/check-api-contract.sh` | **PASS** (`0 drift`) |
| Database Schema Sync | `docs/database/schema.sql` vs `alembic upgrade head` (`0015`) | **PASS** (`0 drift`, 36 app tables, 26 triggers) |
| Frontend Lint & Build | `pnpm exec ng lint && pnpm exec ng build --configuration production` | **PASS** (0 errors) |
| Frontend Unit Tests | `pnpm exec ng test --watch=false` | **PASS** (**86/86 files, 666/666 passed**) |
| Full Playwright E2E (Staging) | `pnpm exec playwright test --reporter=list` (10 specs / 37 tests) | **PASS** (**37/37 passed, 0 failed, 0 flaky**) |

## 2. Independent 2-User Live Security & 17-Workflow Summary
- **13/13 Security Controls Live Verified** (`p3_independent_sec_gate.py` + `focusflow-rc` `:18080`): Google SSO (`401`), Cookie CSRF (`403`/`200`, `Path=/api/v1/auth`), RTR reuse + family revoke + cross-session isolation (`200`/`401`/`401`/`200`), Password Reset session revocation (`401`), OTP-only register (`403`), Cross-user IDOR (`404`) + Admin RBAC (`403`), RAG SSRF (`422`), RAG magic-byte (`422`), Evaluation AI Quota (`used_calls 0→1`), Billing webhook & Free Beta (`503`/`503`/`403`), WebCal rotate/revoke (`404`), Account Export isolation (`200`), Distributed Rate Limiting (`429 Retry-After: 300`, account isolation `401`).
- **17 Core Workflows**: 16/17 verified live (gồm live Gemini Clarification, Milestones SSE, Proposal SSE `DRAFT`→`Apply`, Prove Mode live grading `score=23`, Outbox→Notifications, WebCal, GDPR Export, Free Beta gate); #17 (SSE F5 recovery) verified via deterministic Vitest (`ai-sse.service.spec.ts` + `roadmap.service.spec.ts`), chưa chạy F5 live giữa stream (**UNIT VERIFIED / LIVE NOT VERIFIED**).
