# P2B2B Functional Integration, GDPR Export, Notification Center & Billing Readiness Report — FocusFlow

> **Role**: Principal Fullstack Engineer, Product Architect & Security QA Lead  
> **Branch**: `fix/p0-audit-remediation`  
> **Date**: 2026-11-21  
> **Scope**: P2B2B — Phase 0 (Pomodoro Semantics & WebCal Security Hardening), Phase 1 (`FE-MOCK-03` GDPR Data Export), Phase 2 (`FE-MOCK-08` Persistent Notification Center — Table #36), Phase 3 (`FE-API-05` / `BE-API-02` Billing Readiness), Phase 4 (Cross-Feature Integration & Playwright E2E)

---

## 1. Findings Resolved / Deferred / Blocked

| Finding ID | Severity | Status | Evidence & Scope Note |
|---|---|---|---|
| **FE-MOCK-03** | **MEDIUM** | **RESOLVED** | Replaced fake client-side JSON export with real `GET /api/v1/account/export` (authenticated, ownership-filtered, `schema_version: "1.0"`, strictly scrubbed of `password_hash`/tokens/secrets, bounded sessions/tasks) and wired `SettingsService.exportAccountData()` + `SettingsPageComponent`. *(Note: Exporting user data does NOT by itself constitute full legal GDPR compliance; GDPR Art. 17 automated deletion `FR-PROFILE-002` remains gated.)* |
| **FE-MOCK-08** | **MEDIUM** | **RESOLVED** | Created table #36 `public.notifications` (user-approved via `/grill-me`, migration `0015_add_notifications_table`), wired idempotent Outbox consumers (`OverdueTaskAlertEvent`, `OfficialScheduleAppliedEvent`, `StudySessionCompletedEvent` with `ON CONFLICT DO NOTHING` on `(user_id, event_id, notification_type)`), exposed `GET/POST read/read-all` APIs, and connected Navbar bell popover with live unread badge, navigation, and error/empty states. |
| **FE-API-05 / BE-API-02 (Billing)** | **MEDIUM** | **RESOLVED (Dev/Mock) / LIVE PROVIDER NOT VERIFIED** | Implemented full Checkout (`PENDING` 15m TTL reuse), `GET /transactions`, HMAC-SHA256 idempotent Webhook (`PENDING → PAID → User.tier='PREMIUM' + AIQuota`), and fail-closed `LocalMockPaymentAdapter` (`503` in production / non-mock without merchant credentials; `403` on `mock-confirm`). Connected `/pricing` Checkout modal. **Live external payment gateway (SePay/VietQR) is `NOT VERIFIED`** until real merchant credentials are provisioned. |
| **Phase 0 — Pomodoro KPI Semantics** | **MEDIUM** | **RESOLVED** | Replaced `sum(max(1, actual_minutes // 25))` with exact `len(monthly_sessions)` in `execution_dashboard_adapter.py` and updated Dashboard KPI Card 4 label from `"Pomodoro hoàn tất / 25m/phiên"` to `"Phiên học hoàn tất / Trong tháng"`. |
| **Phase 0 — WebCal Security Hardening** | **MEDIUM** | **RESOLVED** | Added `Cache-Control: no-store, private`, `Referrer-Policy: no-referrer`, `X-Content-Type-Options: nosniff`, per-token-hash rate limiting (`429` at >60 req/60s), and RFC 5545 §3.1 75-octet UTF-8 line folding (`_fold_ics_line`) preserving multi-byte Vietnamese characters. |

---

## 2. Data Export Contract & Security Review (`FE-MOCK-03`)

- **Endpoint**: `GET /api/v1/account/export` (authenticated via `CurrentLearnerIdDep`, `account/presentation/routers.py`).
- **Contract (`AccountDataExportDTO`)**:
  - `schema_version: "1.0"`, `exported_at` (UTC ISO-8601).
  - `user` (`id`, `email`, `full_name`, `timezone`, `role`, `tier`, `created_at`), `learner_profile`, `learner_memory`, `availability`, `roadmaps`, `analytics_summary`, `study_sessions_count` + `study_sessions` (bounded `<= 500`), `tasks_count` + `tasks` (bounded `<= 1000`).
- **Security Guarantees**:
  - Strictly excludes `password_hash`, `token_hash`, `oauth_refresh_token_encrypted`, JWTs, and API keys (asserted in `test_gdpr_export_integration.py` and Playwright E2E).
  - Strict `user_id` ownership filtering across `account`, `planning`, and `execution` via `public_api` ports (IDOR verified: User A export contains zero User B data).
  - Zero PII logged; frontend never emits a success toast or fake file download on HTTP failure.

---

## 3. Notification Architecture (`FE-MOCK-08`)

- **Schema (Migration `0015_add_notifications_table`, Table #36)**:
  - `public.notifications` (`id`, `user_id` FK→`users.id` CASCADE, `event_id`, `notification_type`, `title`, `content`, `resource_url`, `is_read`, `read_at`, `created_at`, `updated_at`).
  - Partial unique index `uq_notifications_user_event_type (user_id, event_id, notification_type) WHERE event_id IS NOT NULL` guarantees duplicate Outbox deliveries never create duplicate inbox rows.
  - Composite index `idx_notifications_user_unread (user_id, is_read, created_at DESC)` + `trg_notifications_updated_at` trigger.
  - Migration round-trip verified: `upgrade head` → `downgrade -1` → `upgrade head` (single head `0015_add_notifications_table`, 36 tables, 26 `updated_at` triggers).
- **Outbox → Inbox Pipeline**:
  - `OverdueTaskAlertEvent` → `OVERDUE_TASK` (`/tasks`)
  - `OfficialScheduleAppliedEvent` → `SCHEDULE_APPLIED` (`/schedule`)
  - `StudySessionCompletedEvent` → `SESSION_COMPLETED` (`/analytics`)
- **REST & UI**: `GET /api/v1/account/notifications`, `POST .../{id}/read` (IDOR `404`), `POST .../read-all`; `NotificationService` + `AppNavbarComponent` popover with live unread badge, loading/error/empty states, click-to-read + navigate.

---

## 4. Billing Scope Decision (`FE-API-05` / `BE-API-02`)

- **Decision (User-Approved via `/grill-me`)**: Implemented full backend Checkout + HMAC-SHA256 idempotent Webhook + `LocalMockPaymentAdapter` (dev/test only) and wired `/pricing` Checkout modal.
- **Production Safety**: `LocalMockPaymentAdapter` fails closed with HTTP `503 Service Unavailable` outside `development`/`dev`/`test`/`local` or whenever live merchant credentials are absent; `POST /api/v1/account/billing/mock-confirm/{id}` returns `403 Forbidden` outside dev/test `local_mock`.
- **External Gateway Status**: **NOT VERIFIED** — live SePay/VietQR production adapter & real webhook delivery remain pending merchant credentials.

---

## 5. Pomodoro & WebCal Phase 0 Verification

- **Pomodoro**: `execution_dashboard_adapter.py` now returns `len(monthly_sessions)` (exact count of `COMPLETED`/`PARTIAL_COMPLETED` `StudySession` rows) and `DashboardKpiGridComponent` renders `"Phiên học hoàn tất / Trong tháng"`, matching Workspace's `"phiên"` terminology.
- **WebCal Privacy**: `GET /api/v1/feeds/{token}.ics` emits `Cache-Control: no-store, private`, `Referrer-Policy: no-referrer`, `X-Content-Type-Options: nosniff`, enforces 60 req/60s per-token-hash rate limit (`429`), and folds lines at `<= 75` UTF-8 octets per RFC 5545 §3.1.

---

## 6. Files Changed

### Backend
- **Created**:
  - [0015_add_notifications_table.py](file:///Users/vuthang/Documents/FocusFlow/backend/alembic/versions/0015_add_notifications_table.py)
  - [notification_orm.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/account/infrastructure/orm/notification_orm.py), [notification_repository_port.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/account/application/ports/notification_repository_port.py), [notification_repository.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/account/infrastructure/repositories/notification_repository.py), [notifications.py (dtos)](file:///Users/vuthang/Documents/FocusFlow/backend/src/account/application/dtos/notifications.py), [notifications.py (use cases)](file:///Users/vuthang/Documents/FocusFlow/backend/src/account/application/use_cases/notifications.py)
  - [export.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/account/application/dtos/export.py), [export_account_data_use_case.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/account/application/use_cases/profile/export_account_data_use_case.py)
  - [billing.py (exceptions)](file:///Users/vuthang/Documents/FocusFlow/backend/src/account/domain/exceptions/billing.py), [payment_ports.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/account/application/ports/payment_ports.py), [billing.py (dtos)](file:///Users/vuthang/Documents/FocusFlow/backend/src/account/application/dtos/billing.py), [billing.py (use cases)](file:///Users/vuthang/Documents/FocusFlow/backend/src/account/application/use_cases/billing.py), [payment_transaction_repository.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/account/infrastructure/repositories/payment_transaction_repository.py), [payment_provider_adapter.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/account/infrastructure/adapters/payment_provider_adapter.py), [billing_router.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/account/presentation/billing_router.py)
  - [test_gdpr_export_integration.py](file:///Users/vuthang/Documents/FocusFlow/backend/tests/integration/account/test_gdpr_export_integration.py), [test_notifications_integration.py](file:///Users/vuthang/Documents/FocusFlow/backend/tests/integration/account/test_notifications_integration.py), [test_billing_integration.py](file:///Users/vuthang/Documents/FocusFlow/backend/tests/integration/account/test_billing_integration.py)
- **Modified**: `execution_dashboard_adapter.py`, `execution/public_api.py`, `ics_builder.py`, `calendar_router.py`, `account/presentation/routers.py`, `account/presentation/deps.py`, `account/presentation/tasks.py`, `account/infrastructure/orm/__init__.py`, `user_repository_port.py`, `user_repository.py`, `main.py`, `test_webcal_integration.py`, `test_pause_records_integration.py`, `test_updated_at_triggers_integration.py`.

### Frontend
- **Created**:
  - [notification.service.ts](file:///Users/vuthang/Documents/FocusFlow/frontend/src/app/core/services/notification.service.ts) & [notification.service.spec.ts](file:///Users/vuthang/Documents/FocusFlow/frontend/src/app/core/services/notification.service.spec.ts)
  - [billing.service.ts](file:///Users/vuthang/Documents/FocusFlow/frontend/src/app/core/services/billing.service.ts) & [billing.service.spec.ts](file:///Users/vuthang/Documents/FocusFlow/frontend/src/app/core/services/billing.service.spec.ts)
  - [p2b2b-functional-integration.spec.ts](file:///Users/vuthang/Documents/FocusFlow/frontend/e2e/p2b2b-functional-integration.spec.ts)
- **Modified**: `schema.d.ts`, `api-endpoints.ts`, `dashboard-kpi-grid.component.ts`, `settings.model.ts`, `settings.service.ts` (+ spec), `settings-page.component.ts` (+ spec), `app-navbar.component.ts/.html/.spec.ts`, `pricing.component.ts/.html/.spec.ts`.

---

## 7. Quality Gates & Runtime Evidence

| Quality Gate | Command | Result |
|---|---|---|
| **Backend Lint & Format** | `ruff check .` & `ruff format --check .` | **PASS** (0 errors, 451 files formatted) |
| **Backend Strict Types** | `mypy --strict src` | **PASS** (323 files, 0 issues) |
| **Architecture Contracts** | `lint-imports` | **PASS** (5 kept, 0 broken; 314 files, 1033 deps) |
| **Alembic Migration Round-Trip** | `upgrade head` → `downgrade -1` → `upgrade head` | **PASS** (single head `0015_add_notifications_table`, 36 tables, 26 triggers) |
| **Full Backend Suite** | `cd backend && uv run --extra dev pytest -q` | **PASS** (**788 passed, 3 skipped, 0 failed**) |
| **API Contract Check** | `bash scripts/check-api-contract.sh` | **PASS** (0 schema drift) |
| **Frontend Lint** | `cd frontend && pnpm exec ng lint` | **PASS** (0 errors) |
| **Frontend Unit Tests** | `cd frontend && pnpm exec ng test --watch=false` | **PASS** (**85/85 suites, 649/649 tests passed**) |
| **Frontend Production Build** | `cd frontend && pnpm exec ng build --configuration production` | **PASS** (0 errors) |
| **Playwright E2E (Real Backend + Outbox + PG)** | `cd frontend && pnpm exec playwright test e2e/p2b2b-functional-integration.spec.ts` | **PASS** (**4/4 passed in 43.8s**: GDPR export + 500 error, Notification Center + F5 persist, Billing checkout readiness, Dashboard KPI `"Phiên học hoàn tất"`) |

---

## 8. Remaining Findings & Release Readiness Blockers

### Remaining Open Findings (P3 Only — Performance, Deduplication & Cleanup)
- `BE-API-04` (`TASK-34`): Pagination on remaining list endpoints (`/tasks`, `/roadmaps`, `/notes`, `/learner-memory`).
- `BE-DUP-01` / `BE-MOCK-03` (`TASK-35`): Consolidate duplicate Taskiq task wrappers & dead stub.
- `FE-DUP-03..06` (`TASK-36`): Delete confirmed orphaned components & 1-line re-export facades.
- `FE-DUP-08` / `FE-DUP-09` / `BE-DUP-02` (`TASK-37`, `TASK-38`): Deduplicate reschedule/date/interval helpers.
- `BE-API-05` (`TASK-39`), `FE-FUNC-03` (`TASK-40`), `DB-SCHEMA-02` (`TASK-41`), `QA-VERIF-01` (`TASK-42`).

### Release Readiness Blockers (Before Production Go-Live)
1. **Live Payment Gateway (`NOT VERIFIED`)**: Provision real SePay/VietQR merchant credentials and verify live signed webhook delivery end-to-end.
2. **GDPR Article 17 Automated Account Deletion (`FR-PROFILE-002`)**: Backend soft-delete + PII scrubbing + pending-payment check endpoint is still gated/unimplemented.
3. **Admin Telemetry Backend (`FE-MOCK-06`)**: `/admin` is safely gated (`403` + `adminGuard`), but full admin user/quota/telemetry management APIs are not yet implemented.
4. **In-Memory WebCal Rate Limiter**: Current 60 req/60s rate limiter is per-process in-memory; migrate to Redis-backed rate limiting if scaling to multiple backend replicas.
5. **Static `docs/database/schema.sql` Snapshot**: Refresh via `pg_dump --schema-only` to include migrations `0014` and `0015` (36 tables, 26 triggers).
