# 08 — Prioritized Remediation Backlog

> **Lưu ý**: Theo quy tắc kiểm toán độc lập (read-only), tài liệu này chỉ đề xuất lộ trình khắc phục theo thứ tự ưu tiên; **chưa thực hiện chỉnh sửa mã nguồn**.

---

## P0 — Mandatory Release Blockers (Phải xử lý trước khi mở cho bất kỳ người dùng thực nào)

| Priority | Finding ID | Title | Target Files | Status |
|---|---|---|---|---|
| **P0-1** *(P0A)* | `AUD-CRIT-01` | Vá Google SSO Confused Deputy & `email_verified` fail-open | `google_auth_service.py`, `google_auth_use_case.py` | **COMPLETED (P0A)** — Xem `09-p0a-security-remediation-report.md` |
| **P0-2** *(P0A)* | `AUD-CRIT-02` | Hardening Billing Webhook & tách khỏi JWT `secret_key` | `billing_router.py`, `billing.py`, `config.py`, `payment_transaction_repository.py` | **COMPLETED (P0A)** — Xem `09-p0a-security-remediation-report.md` |
| **P0-3** *(P0A)* | `AUD-CRIT-03` | Vá DNS Rebinding SSRF trong `SafeUrlFetcher` | `safe_url_fetcher.py`, `knowledge_source_use_cases.py` | **COMPLETED (P0A)** — Xem `09-p0a-security-remediation-report.md` |
| **P0-4** *(P0A)* | `AUD-CRIT-04` | Bắt buộc AI Quota (`RESERVE → COMMIT/RELEASE`) & `ai_usage_logs` cho Evaluation | `evaluation/presentation/deps.py`, `evaluation/presentation/routers.py`, `quota_facade_adapter.py` | **COMPLETED (P0A)** — Xem `09-p0a-security-remediation-report.md` |
| **P0-5** *(P0A)* | `AUD-HIGH-10` | Vá Cross-User Sticky Note IDOR & Task UUID Existence Oracles | `session_use_cases.py`, `task_use_cases.py`, `execution/presentation/deps.py` | **COMPLETED (P0A)** — Xem `09-p0a-security-remediation-report.md` |
| **P0-6** *(P0A)* | `AUD-HIGH-03` | Thu hồi toàn bộ Refresh Token khi Password Reset | `password_reset_otp_use_case.py`, `refresh_token_use_case.py`, `redis_client.py`, `account/presentation/deps.py` | **COMPLETED (P0A)** — Xem `09-p0a-security-remediation-report.md` |
| **P0-7** *(P0A)* | `AUD-HIGH-04` | Chặn Direct Register không OTP ngoài môi trường dev/test | `auth_router.py` | **COMPLETED (P0A)** — Xem `09-p0a-security-remediation-report.md` |
| **P0-8** *(P0B)* | `AUD-HIGH-01` | Bổ sung CSRF Protection & thu hẹp `refresh_token` Cookie Path | `csrf_middleware.py`, `main.py`, `config.py`, `auth_router.py` | **COMPLETED (P0B)** — Xem `10-p0b-auth-security-remediation-report.md` |
| **P0-9** *(P0B)* | `AUD-HIGH-02` | Sửa Refresh Token Rotation (Atomic Lua + Reuse Detection + FE single-flight) | `refresh_token_use_case.py`, `redis_client.py`, `auth_ports.py`, `auth.interceptor.ts` | **COMPLETED (P0B)** — Xem `10-p0b-auth-security-remediation-report.md` |
| **P0-10** *(P0B)* | `AUD-HIGH-05` | Triển khai Redis Rate Limiting & gỡ in-memory WebCal bucket | `rate_limiter.py`, `main.py`, `auth_router.py`, `routers.py`, `calendar_router.py`, `billing_router.py`, `webhook_router.py`, `planning/routers.py` | **COMPLETED (P0B)** — Xem `10-p0b-auth-security-remediation-report.md` |

---

## P1 — Production Reliability, File Safety & Core UX Blockers

| Priority | Finding ID | Title | Target Files | Acceptance Criteria |
|---|---|---|---|---|
| **P1-1** *(P1A)* | `AUD-HIGH-06` | Kiểm tra Magic Bytes / MIME / Zip-Bomb & dọn file tạm `0700` khi upload RAG | `document_extractor.py`, `local_file_store.py`, `safe_url_fetcher.py`, `knowledge_source_use_cases.py` | **COMPLETED (P1A)** — Xem `11-p1a-reliability-remediation-report.md` |
| **P1-2** *(P1A)* | `AUD-HIGH-07` | Sửa Outbox Relay (quarantine missing handler, fresh-session rollback, `FOR NO KEY UPDATE SKIP LOCKED`, backoff & metrics) | `backend/src/shared_kernel/infrastructure/outbox/relay.py` | **COMPLETED (P1A)** — Xem `11-p1a-reliability-remediation-report.md` |
| **P1-3** *(P1B)* | `AUD-HIGH-08` | Bật AI Circuit Breaker mặc định cho Planning & Evaluation + Redis fallback + fail-fast `503` | `config.py`, `circuit_breaker.py`, `execution_manager.py`, `main.py`, `planning/deps.py`, `evaluation/deps.py` | **COMPLETED (P1B)** — Xem `12-p1b-ai-db-reliability-report.md` |
| **P1-4** *(P1B)* | `AUD-HIGH-09` | Thay `NullPool` bằng `AsyncAdaptedQueuePool` + timeouts + pre-LLM read-TX release | `database/session.py`, `config.py`, `main.py`, `intelligence.py`, `milestone_use_cases.py` | **COMPLETED (P1B)** — Xem `12-p1b-ai-db-reliability-report.md` |
| **P1-5** *(P1B)* | `AUD-MED-12` | Sửa Prove Mode Grading (`503 AI_GRADING_UNAVAILABLE`, `409 PROOF_ALREADY_GRADED`, timeout `25s`, FE `"Thử chấm lại"`) + 1-wave decomposition + `MilestoneApprovedEvent` deprecation | `intelligence.py`, `evaluation/routers.py`, `prove-mode-dialog.component.ts`, `milestone_scoped_decomposer.py`, `milestone_use_cases.py` | **COMPLETED (P1B)** — Xem `12-p1b-ai-db-reliability-report.md` |
| **P1-6** *(P1C)* | `AUD-HIGH-11` | Triển khai `BILLING_RELEASE_MODE` (`FREE_BETA` mặc định, `PAID_ENABLED` fail-closed), `GET /billing/config`, đồng bộ `monthly_limit=300` & giá `99k`/`990k`, Free Beta UI gating, sửa `checkout_url` | `config.py`, `billing_router.py`, `billing.py`, `payment_provider_adapter.py`, `billing.service.ts`, `pricing.component.*`, `settings-page.component.ts` | **COMPLETED (P1C — FREE_BETA GATED; LIVE PROVIDER NOT VERIFIED)** — Xem `13-p1c-billing-release-gating-report.md` |

---

## P2 — Security Hygiene, Resilience, Architecture & Docs Sync

| Priority | Finding ID | Title | Target Files | Status |
|---|---|---|---|---|
| **P2-1** *(P2)* | `AUD-MED-01`, `AUD-MED-02`, `AUD-MED-03` | Chống Account Enumeration & Atomic OTP (`AUD-MED-03` hoãn có lý do) | `password_reset_otp_use_case.py`, `otp_repository.py` | **COMPLETED (`01`,`02` P2)** / **DEFERRED (`03`)** — Xem `14-p2-architecture-hygiene-report.md` |
| **P2-2** *(P2)* | `AUD-MED-04`, `AUD-MED-05`, `AUD-MED-06` | Hardening `/api/health` (DB/Redis ping), Fail-Closed Calendar Webhook, PII Logging Redaction | `main.py`, `webhook_router.py`, `logging.py`, `email_service.py` | **COMPLETED (P2)** — Xem `14-p2-architecture-hygiene-report.md` |
| **P2-3** *(P2)* | `AUD-MED-07`, `AUD-MED-08` | FE HTTP Timeout, SSE 401 Refresh & F5 Recovery, `InMemorySseJobStore` TTL Eviction | `app.config.ts`, `timeout.interceptor.ts`, `ai-sse.service.ts`, `roadmap.service.ts`, `sse/job_store.py` | **COMPLETED (P2)** — Xem `14-p2-architecture-hygiene-report.md` |
| **P2-4** *(P2)* | `AUD-MED-09`, `BE-API-04` | Loại bỏ 2 Raw SQL Cross-Context còn sót + Optional Pagination (`/tasks`, `/backlog`, `/roadmaps`) | `planning/public_api.py`, `schedule_sync_adapter.py`, `weekly_execution_metrics_adapter.py`, `execution/routers.py`, `planning/routers.py` | **COMPLETED (P2)** — Xem `14-p2-architecture-hygiene-report.md` |
| **P2-5** *(P2)* | `AUD-MED-10`, `AUD-MED-11` | Đồng bộ `docs/database/schema.sql` (36 bảng, 26 triggers) & `database-schema-design.md` (`AUD-MED-11` hoãn có lý do) | `docs/database/schema.sql`, `database-schema-design.md`, `01-independent-system-inventory.md` | **COMPLETED (`10` P2)** / **DEFERRED (`11`)** — Xem `14-p2-architecture-hygiene-report.md` |
| **P2-6** *(P1A)* | `AUD-MED-13` | Cập nhật Playwright E2E specs (`e2e_full_workflow`, `signal_e2e_evidence`, `p2a-data-consistency`) | `frontend/e2e/*` | **COMPLETED (P1A)** — P2 Full Run: **37/37 PASS (0 flake)**. |

---

## P3 — Low-Severity Hardening & Codebase Cleanup

| Priority | Finding ID | Title | Status |
|---|---|---|---|
| **P3-1** *(P2)* | `AUD-LOW-01..04` | Startup Fernet key validation, ẩn raw exception OAuth redirect, đóng `httpx.AsyncClient` (`AUD-LOW-04` JTI denylist hoãn có lý do) | **COMPLETED (`01`–`03` P2)** / **DEFERRED (`04`)** |
| **P3-2** *(P2)* | `AUD-LOW-05`, `AUD-LOW-06` | Hợp nhất URL hardcode về `API_ENDPOINTS`; xóa 4 file FE orphan 0 reference & 3 Taskiq task duplicate/no-op | **COMPLETED (P2)** |
