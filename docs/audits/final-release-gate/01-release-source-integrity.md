# 01 — Release Source Integrity & Change Provenance (Phase 0)

- **Audit Target**: `/Users/vuthang/Documents/FocusFlow`
- **Current Branch / HEAD**: `fix/p2-architecture-hygiene` @ `347066b` (`feat: type milestone subjob progress events`)
- **Verdict**: **CONDITIONAL PASS (WORKING TREE UNCOMMITTED — REQUIRES ATOMIC COMMITS BEFORE RELEASE TAG)**

---

## 1. Git Baseline & Provenance Findings

- **Branch Graph**: Tất cả 7 nhánh remediation (`fix/p0-audit-remediation`, `fix/p0a-security-remediation`, `fix/p0b-auth-security-remediation`, `fix/p1a-reliability-remediation`, `fix/p1b-ai-db-reliability`, `fix/p1c-billing-release-gating`, `fix/p2-architecture-hygiene`) hiện cùng trỏ về commit gốc `347066b` (tuân thủ nghiêm quy tắc không tự commit/merge/rebase).
- **Working Tree Delta**: **193** tracked files đã sửa + **235** untracked files (bao gồm toàn bộ mã nguồn, tests, migrations `0014`/`0015`, báo cáo audit `01`–`14`, và các production manifests mới tạo ở P3).
- **Secret Scan**: **PASS (0 leaks)** — quét toàn bộ file untracked và tracked cho private key headers (`-----BEGIN ... PRIVATE KEY-----`), `AIza...`, `sk-...`, `AKIA...` và file `.env*` trả về **0 phát hiện**. Chỉ có `.env.example` và `.env.prod.example` (placeholder an toàn).
- **Non-Release Artifacts Present (KHÔNG ĐƯỢC COMMIT VÀO RELEASE BRANCH)**:
  1. `artifacts/` (~70+ file dựng DOCX/PDF/PNG, nhiều MB).
  2. `docs_ute/03_status_reports/PROJECT STATUS REPORT - Week 11.docx`, `Week 12.docx`, `Week 12.md`.
  3. `docs/experiments/scheduled_eval_7d/runs/*.json` (22 file kết quả thử nghiệm) và `docs/evidence/e2e_screenshots/*` (30 ảnh chụp).
  4. `scripts/grant_unlimited_quota.py` (script hỗ trợ dev/staging — cần rà soát riêng, không ship mặc định cho production).

---

## 2. Change Provenance Matrix (P0A → P3)

Toàn bộ **18/18** file cốt lõi của P0A–P2 và **7/7** file P3 đã được xác minh tồn tại trong working tree hiện tại:

| Wave | Findings Covered | Core Source Files Verified Present | Verification Test Suites | Current Git State |
|---|---|---|---|---|
| **Prior Baseline** | P2A–P2B2B (Notifications, WebCal, Admin Guard, Prove Mode UI, Export) | `alembic/versions/0014*`, `0015*`, `roadmap.store.ts`, `entity-invalidation.service.ts`, `notification.service.ts`, `admin.guard.ts`, `prove-mode-dialog` | `p2a-*`, `p2b1-*`, `p2b2a-*`, `p2b2b-*` | Uncommitted diff |
| **P0A** | `AUD-CRIT-01..04`, `AUD-HIGH-03/04/10` | `google_auth_service.py`, `billing_router.py`, `safe_url_fetcher.py`, `evaluation/presentation/deps.py`, `session_use_cases.py`, `password_reset_otp_use_case.py`, `auth_router.py` | `test_google_auth_security.py`, `test_billing_webhook_security.py`, `test_safe_url_fetcher_ssrf.py`, `test_evaluation_quota_enforcement.py`, `test_sticky_note_idor_isolation.py`, `test_password_reset_security.py`, `test_register_otp_enforcement.py` | Uncommitted diff |
| **P0B** | `AUD-HIGH-01/02/05`, P0A QA Closure | `csrf_middleware.py`, `redis_client.py`, `refresh_token_use_case.py`, `rate_limiter.py`, `auth.interceptor.ts`, `frontend/e2e/helpers/otp-auth.helper.ts` | `test_csrf_middleware.py`, `test_csrf_protection_integration.py`, `test_refresh_token_rotation_integration.py`, `test_distributed_rate_limiter.py`, `test_endpoint_rate_limiting_integration.py` | Uncommitted diff |
| **P1A** | `AUD-HIGH-06/07`, `AUD-MED-13` | `document_extractor.py`, `local_file_store.py`, `outbox/relay.py`, `frontend/e2e/{e2e_full_workflow,signal_e2e_evidence,p2a-data-consistency}.spec.ts` | `test_rag_ingestion_security.py`, `test_rag_knowledge_ownership.py`, `test_outbox_reliability_integration.py`, 3x Full Playwright E2E | Uncommitted diff |
| **P1B** | `AUD-HIGH-08/09`, `AUD-MED-12`, Phase 4 & 5 | `circuit_breaker.py`, `execution_manager.py`, `database/session.py`, `evaluation/application/use_cases/intelligence.py`, `milestone_scoped_decomposer.py`, `planning_events.py` | `test_ai_circuit_breaker_resilience.py`, `test_db_pool_reliability.py`, `test_prove_mode_grading_correctness.py`, `test_milestone_approved_event_disposition.py`, `test_milestone_timeout_and_recovery.py` | Uncommitted diff |
| **P1C** | `AUD-HIGH-11` (`FREE_BETA`), P1B Follow-up | `config.py` (`BILLING_RELEASE_MODE`), `billing_router.py` (`/config`), `milestone_checkpoint_port.py` (`is_durable`), `billing.service.ts`, `pricing.component.*` | `test_billing_integration.py`, `test_billing_webhook_security.py`, `pricing.component.spec.ts`, `FE-API-05` E2E | Uncommitted diff |
| **P2** | `AUD-MED-01/02/04..10`, `AUD-LOW-01..03/05/06`, `BE-API-04` | `planning_read_query_adapter.py`, `planning/public_api.py`, `otp_repository.py`, `main.py` (`/api/health`), `logging.py`, `job_store.py`, `timeout.interceptor.ts`, `docs/database/schema.sql` | `test_p2_hygiene_security.py`, `test_execution_boundary_architecture.py`, `timeout.interceptor.spec.ts`, `ai-sse.service.spec.ts` | Uncommitted diff |
| **P3** | Production Manifests, DR Scripts & Release Gate | `docker-compose.prod.yml`, `backend/supervisord.prod.conf`, `frontend/Dockerfile.prod`, `frontend/nginx.prod.conf`, `.env.prod.example`, `scripts/{backup,restore}_postgres.sh`, `docs/audits/final-release-gate/` | `docker compose config` PASS, Clean-Room DR Drill PASS, 13/13 Security Gate PASS, 120-req Perf Gate PASS | Untracked (ready to commit) |

---

## 3. Recommended Atomic Commit Plan (Chưa thực thi)

Trước khi gắn tag Release Candidate (`v0.9.0-beta.1`), xóa/loại trừ `artifacts/`, giữ `docs_ute/` và `docs/experiments/scheduled_eval_7d/runs/` ngoài nhánh release, sau đó tạo 8 commit nguyên tử:
1. `feat(baseline): land P2A-P2B2B notifications, webcal, admin guard, prove mode UI and migrations 0014-0015`
2. `fix(security): P0A remediation — Google SSO, billing webhook, DNS rebinding SSRF, eval quota, sticky note IDOR, password reset, OTP-only register`
3. `fix(auth): P0B remediation — CSRF middleware, atomic RTR reuse detection, distributed Redis rate limiting and OTP E2E helpers`
4. `fix(reliability): P1A remediation — RAG magic-byte/zip-bomb security, transactional outbox hardening and Playwright E2E stabilization`
5. `fix(reliability): P1B remediation — AI circuit breaker, PostgreSQL pooling/timeouts, Prove Mode grading correctness and 1-wave decomposition`
6. `feat(billing): P1C remediation — FREE_BETA vs PAID_ENABLED release gating, server-side billing config and SRS quota 300 alignment`
7. `refactor(architecture): P2 remediation — cross-context query ports, backend/frontend hygiene, pagination and canonical schema.sql sync`
8. `chore(release): P3 production compose/nginx/supervisord manifests, PostgreSQL DR scripts and final release gate reports`
