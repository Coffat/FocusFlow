# P1B Implementation & Cross-Page E2E Report — FocusFlow

> **Role**: Principal Fullstack Engineer & Integration Architect  
> **Branch**: `fix/p0-audit-remediation`  
> **Date**: 2026-11-21  
> **Scope**: Phase 1 — P1A Reliability Verification & Hardening; Phase 2 — P1B (`BE-ARCH-01`, `BE-API-03`, `FE-SYNC-02`, `FE-API-01/02`, `QA-GATE-01`, `FE-MOCK-04`); Phase 3 — Cross-Page Playwright E2E

---

## 1. Phase 1 — P1A Reliability Verification & Hardening Results

All 5 P1A reliability questions were audited directly against source code before beginning P1B, and 3 concrete hardening fixes were applied immediately:

| # | Reliability Question | Initial Finding | Hardening Applied & Semantics Verified |
|---|---|---|---|
| 1 | **Broker publish succeeds, DB commit fails** | `relay_pending_outbox_events` committed once after the whole batch loop, so a commit failure on event `N` rolled back events `1..N-1` already published to Redis. | Refactored [relay.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/shared_kernel/infrastructure/outbox/relay.py) to lock (`limit(1).with_for_update(skip_locked=True)`) and commit **per event**. Semantics are explicitly **at-least-once** delivery (not exactly-once); broker acknowledgement, worker execution, and business side effects are distinct phases. |
| 2 | **Consumer-side idempotency** | `AvailabilityUpdatedEvent` (`HandleAvailabilityUpdatedEventUseCase`) had full `processed_events` idempotency; `OfficialScheduleAppliedEvent` had business-level idempotency (deterministic Google event ID + 409 reconcile); **`OverdueTaskAlertEvent` had NO consumer idempotency** and `send_overdue_alert_email` silently swallowed SMTP exceptions. | Passed `event_id` into `send_overdue_task_alert_email_task` ([account/presentation/tasks.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/account/presentation/tasks.py)), enforced `processed_events` (`"account.overdue_task_alert_email_worker"`) before sending, and added `raise_on_error=True` to `EmailService.send_overdue_alert_email` ([email_service.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/account/infrastructure/email/email_service.py)). Verified by integration test `test_overdue_alert_email_worker_duplicate_delivery_sends_strictly_once`. |
| 3 | **Worker failure after broker publish** | `RedisStreamBroker` had `middlewares == []` (zero retries; Taskiq XACKed failed tasks on error). | Attached `SimpleRetryMiddleware(default_retry_count=3)` in [broker.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/shared_kernel/infrastructure/worker/broker.py) so transient worker failures retry automatically after broker publish. |
| 4 | **Taskiq scheduler runtime trigger** | Verified `supervisord.conf:29` imports `src.account.presentation.tasks`, `LabelScheduleSource.startup()` registers `sweep_expired_ai_quota_reservations` with `cron="* * * * *"`, and `taskiq.receiver.params_parser.parse_params` resolves default args `(session_factory=None, now=None)` cleanly. | Confirmed working at runtime without modification. |
| 5 | **Test environment Redis isolation** | No `backend/tests/conftest.py` existed; running `pytest` without `ENVIRONMENT=test` could push jobs into live Docker Redis. | Resolved via `QA-GATE-01`: created [backend/tests/conftest.py](file:///Users/vuthang/Documents/FocusFlow/backend/tests/conftest.py) + `_is_test_runtime()` defense-in-depth in [broker.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/shared_kernel/infrastructure/worker/broker.py). |

---

## 2. Findings Resolved & Remaining Findings

### Resolved in P1B (Definition of Done Met)
| Finding ID | Severity | Status | Summary of Resolution |
|---|---|---|---|
| **BE-ARCH-01** | **HIGH** | **RESOLVED** | Eliminated ALL raw SQL cross-context queries (`roadmaps`, `users`, `outbox_events`) across `backend/src/execution/` (both `presentation/tasks.py` and `infrastructure/adapters/execution_dashboard_adapter.py`) by extending existing `PlanningExecutionBridgePort` & `UserQueryPort` (zero redundant bridge ports). Added static architecture regression test [test_execution_boundary_architecture.py](file:///Users/vuthang/Documents/FocusFlow/backend/tests/unit/test_execution_boundary_architecture.py). |
| **BE-API-03** | **HIGH** | **RESOLVED** | Added `InvalidKnowledgeSourceError(ValueError)` in `knowledge_source_use_cases.py`, mapped `(InvalidKnowledgeSourceError, UnsafeUrlError)` → HTTP `422` in `planning/presentation/routers.py` while leaving bare `ValueError`/`Exception` as HTTP `500`, and caught persisted ingestion errors in `dispatch_ingest_knowledge_source` inline fallback. |
| **FE-SYNC-02** | **HIGH** | **RESOLVED** | Bound `(roadmapApplied)="onRoadmapApplied($event)"` in both `DashboardComponent` and `RoadmapsHubComponent`. Dashboard transitions out of `'new-user'`/`'unscheduled'` and refetches `loadSummary()`; RoadmapsHub avoids duplicate `GET /api/v1/roadmaps` when `loading()` is already active. Verified by unit tests + 5 Playwright E2E workflows against real PostgreSQL. |
| **FE-API-01 / FE-API-02 / BE-API-01** | **MEDIUM** | **RESOLVED** | Fixed `SETTINGS.PROFILE` (`/api/v1/account/profile`) and `SETTINGS.QUOTA` (`/api/v1/account/quota`) in `api-endpoints.ts`; removed 8 verified 0-consumer ghost entries (`BILLING.*`, `ADMIN.*`, `ROADMAPS.GENERATE_JOB`, `ACTIVE`, `APPLY`) and duplicate `STREAM_JOB`; kept all valid OpenAPI endpoints; migrated `ProfileService`, `SettingsService`, and `DashboardService` to use `API_ENDPOINTS`. |
| **QA-GATE-01** | **MEDIUM** | **RESOLVED** | Created `backend/tests/conftest.py` forcing `ENVIRONMENT=test`, redirecting host `REDIS_HOST=redis` → `localhost` outside Docker (without editing `.env` or `docker-compose.yml`), and failing fast if `broker` is not `InMemoryBroker`. |
| **FE-MOCK-04** | **HIGH** | **RESOLVED** | Disabled fake GDPR account deletion button (`[disabled]="true"`, `aria-disabled="true"`), added honest Vietnamese `FR-PROFILE-002` unavailable notice (`data-testid="delete-account-unavailable-notice"`), and removed fake confirmation/toast from `onRequestDeleteAccount()`. |

### Remaining Findings (Out of P1B Scope — Deferred to P2/P3)
- **P2 (13 tasks, `TASK-21`..`TASK-33`)**: `FE-FUNC-01` (Prove Mode UI), `FE-SYNC-01`/`FE-DUP-07` (shared `RoadmapStore`), `FE-MOCK-02`/`BE-API-02` (WebCal), `FE-MOCK-06` (Admin gate), `BE-INT-01`/`DB-CONSIST-01`/`DB-SCHEMA-01` (`pause_records` ORM), `DB-CONSIST-02` (5 `updated_at` triggers), `FE-SYNC-03`/`04` (Workspace↔Tasks sync), `FE-API-05`/`BE-API-02` (Billing), `FE-SYNC-05`/`FE-MOCK-07` (Dashboard Adaptation modal), `FE-MOCK-03` (GDPR export), `BE-MOCK-02`/`FE-MOCK-05` (SRL aggregation), `FE-MOCK-08` (Navbar bell), `FE-MOCK-09` (Workspace Pomodoro count).
- **P3 (9 tasks, `TASK-34`..`TASK-42`)**: Pagination (`BE-API-04`), Taskiq duplicate cleanup (`BE-DUP-01`/`BE-MOCK-03`), orphaned FE cleanup (`FE-DUP-03..06`), utility dedup (`FE-DUP-08`/`09`, `BE-DUP-02`), optional `GET /tasks/{id}` (`BE-API-05`), schedule drag-and-drop (`FE-FUNC-03`), schema doc sync (`DB-SCHEMA-02`), Sass merge (`QA-VERIF-01`).

---

## 3. Key Architecture Decisions

1. **No Redundant Bridge Ports (`BE-ARCH-01`)**: Extended existing `PlanningExecutionBridgePort` (`get_roadmaps_context_by_ids`, `reset_weekly_reschedule_budgets`) and `UserQueryPort` (`get_users_by_ids`) rather than introducing new cross-context port abstractions.
2. **Narrow Exception Mapping (`BE-API-03`)**: Introduced `InvalidKnowledgeSourceError` so routers catch only explicit client validation errors (`InvalidKnowledgeSourceError`, `UnsafeUrlError`) → HTTP `422`, preserving HTTP `500` for programming/infrastructure defects.
3. **Zero `.env` / `docker-compose.yml` Mutation (`QA-GATE-01`)**: Enforced test isolation in `backend/tests/conftest.py` + `broker.py`, keeping Docker production/dev networking (`REDIS_HOST=redis`) completely untouched.
4. **Honest GDPR Gate (`FE-MOCK-04`)**: Per SRS `FR-PROFILE-002` (requires Argon2id password re-verification, pending-payment guard, soft delete, PII scrubbing, outbox event), avoided implementing unsafe physical/cascade delete and replaced the misleading toast with a disabled control + transparent status notice.

---

## 4. Files Changed

### Backend
- **Created**:
  - [backend/tests/conftest.py](file:///Users/vuthang/Documents/FocusFlow/backend/tests/conftest.py)
  - [test_execution_boundary_architecture.py](file:///Users/vuthang/Documents/FocusFlow/backend/tests/unit/test_execution_boundary_architecture.py)
  - [test_knowledge_upload_error_semantics.py](file:///Users/vuthang/Documents/FocusFlow/backend/tests/unit/planning/test_knowledge_upload_error_semantics.py)
- **Modified**:
  - [relay.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/shared_kernel/infrastructure/outbox/relay.py)
  - [broker.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/shared_kernel/infrastructure/worker/broker.py)
  - [email_service.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/account/infrastructure/email/email_service.py)
  - [account/presentation/tasks.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/account/presentation/tasks.py)
  - [account/public_api.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/account/public_api.py) & [user_query_adapter.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/account/infrastructure/adapters/user_query_adapter.py)
  - [planning/public_api.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/public_api.py) & [planning_execution_bridge.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/infrastructure/adapters/planning_execution_bridge.py)
  - [knowledge_source_use_cases.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/application/use_cases/knowledge_source_use_cases.py), [planning/presentation/routers.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/presentation/routers.py), [planning/presentation/tasks.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/presentation/tasks.py)
  - [execution/presentation/tasks.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/execution/presentation/tasks.py) & [execution_dashboard_adapter.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/execution/infrastructure/adapters/execution_dashboard_adapter.py)
  - [test_outbox_relay_integration.py](file:///Users/vuthang/Documents/FocusFlow/backend/tests/integration/shared_kernel/test_outbox_relay_integration.py) & [test_overdue_and_abandoned_sweepers.py](file:///Users/vuthang/Documents/FocusFlow/backend/tests/unit/execution/test_overdue_and_abandoned_sweepers.py)

### Frontend
- **Created**:
  - [api-endpoints.spec.ts](file:///Users/vuthang/Documents/FocusFlow/frontend/src/app/core/constants/api-endpoints.spec.ts)
  - [roadmap-dashboard-sync.spec.ts](file:///Users/vuthang/Documents/FocusFlow/frontend/e2e/roadmap-dashboard-sync.spec.ts)
- **Modified**:
  - [dashboard.component.html](file:///Users/vuthang/Documents/FocusFlow/frontend/src/app/features/dashboard/dashboard.component.html), [dashboard.component.ts](file:///Users/vuthang/Documents/FocusFlow/frontend/src/app/features/dashboard/dashboard.component.ts), [dashboard.component.spec.ts](file:///Users/vuthang/Documents/FocusFlow/frontend/src/app/features/dashboard/dashboard.component.spec.ts)
  - [roadmaps-hub.component.html](file:///Users/vuthang/Documents/FocusFlow/frontend/src/app/features/roadmaps/components/roadmaps-hub/roadmaps-hub.component.html), [roadmaps-hub.component.ts](file:///Users/vuthang/Documents/FocusFlow/frontend/src/app/features/roadmaps/components/roadmaps-hub/roadmaps-hub.component.ts), [roadmaps-hub.component.spec.ts](file:///Users/vuthang/Documents/FocusFlow/frontend/src/app/features/roadmaps/components/roadmaps-hub/roadmaps-hub.component.spec.ts)
  - [roadmap-wizard-host.component.spec.ts](file:///Users/vuthang/Documents/FocusFlow/frontend/src/app/features/roadmaps/components/dialogs/roadmap-wizard-host/roadmap-wizard-host.component.spec.ts)
  - [api-endpoints.ts](file:///Users/vuthang/Documents/FocusFlow/frontend/src/app/core/constants/api-endpoints.ts), [profile.service.ts](file:///Users/vuthang/Documents/FocusFlow/frontend/src/app/features/profile/services/profile.service.ts), [settings.service.ts](file:///Users/vuthang/Documents/FocusFlow/frontend/src/app/features/settings/services/settings.service.ts), [dashboard.service.ts](file:///Users/vuthang/Documents/FocusFlow/frontend/src/app/features/dashboard/services/dashboard.service.ts)
  - [settings-page.component.ts](file:///Users/vuthang/Documents/FocusFlow/frontend/src/app/features/settings/components/settings-page.component.ts) & [settings-page.component.spec.ts](file:///Users/vuthang/Documents/FocusFlow/frontend/src/app/features/settings/components/settings-page.component.spec.ts)

---

## 5. Unit, Integration & Playwright E2E Test Evidence

| Quality Gate | Command | Result |
|---|---|---|
| **Backend Lint** | `cd backend && uv run --extra dev ruff check .` | **PASS** (0 issues) |
| **Backend Format** | `cd backend && uv run --extra dev ruff format --check .` | **PASS** (417 files formatted) |
| **Backend Strict Types** | `cd backend && uv run --extra dev mypy --strict src` | **PASS** (300 source files, 0 issues) |
| **Architecture Contracts** | `cd backend && uv run --extra dev lint-imports` | **PASS** (5 kept, 0 broken; 291 files, 953 deps) |
| **Full Backend Suite (Zero Env Overrides)** | `cd backend && uv run --extra dev pytest -q` | **PASS** (**770 passed, 3 skipped, 0 failed** in 91.23s) |
| **API Contract Check** | `bash scripts/check-api-contract.sh` | **PASS** (0 schema drift) |
| **Frontend Lint** | `cd frontend && pnpm exec ng lint` | **PASS** (0 errors) |
| **Frontend Unit Tests** | `cd frontend && pnpm exec ng test --watch=false` | **PASS** (**78/78 suites, 597/597 tests passed** in 4.43s) |
| **Frontend Production Build** | `cd frontend && pnpm exec ng build --configuration production` | **PASS** (0 errors, 7.87s) |
| **Cross-Page Playwright E2E (Real Backend + PG)** | `cd frontend && pnpm exec playwright test e2e/roadmap-dashboard-sync.spec.ts` | **PASS** (**5/5 workflows passed** in 19.8s) |

### Phase 3 Playwright Workflows Verified Against Real PostgreSQL
1. **Create Roadmap → Apply Proposal → Dashboard updates** (`2.5s`): Verified immediate Dashboard refresh without reload + real `GET /api/v1/evaluation/dashboard-summary` & `GET /api/v1/roadmaps` readback (`status === 'ACTIVE'`).
2. **Apply Roadmap → Roadmaps Hub displays ACTIVE status** (`1.6s`): Verified `ĐANG KÍCH HOẠT` badge + filter count matching persistent DB.
3. **Pause / Resume Roadmap → UI & DB consistency** (`2.8s`): Verified Pause (`PAUSED`), `F5` reload persistence, and Resume (`ACTIVE`) against real `GET /api/v1/roadmaps`.
4. **API Apply fails (HTTP 500)** (`1.7s`): Verified wizard stays open with `[data-testid="wizard-error-banner"]`, Dashboard stays empty, and DB confirms roadmap is NOT `ACTIVE`.
5. **Reload & Route Navigation (`/dashboard` ↔ `/roadmaps`)** (`2.3s`): Verified consistent state across transitions and `F5` reloads.

---

## 6. Contract Verification

- `bash scripts/check-api-contract.sh` passed with **0 diff** between FastAPI OpenAPI 3.1 and `frontend/src/app/core/api/schema.d.ts`.
- `api-endpoints.spec.ts` enforces that `API_ENDPOINTS` contains zero `/api/v1/users/*` paths and zero removed ghost keys.

---

## 7. Residual Risks & Issues for P2

### Residual Risks
1. **Outbox At-Least-Once Delivery**: Outbox relay guarantees at-least-once delivery; any future outbox consumer added in P2 must implement `processed_events` or business-level idempotency (as `AvailabilityUpdatedEvent`, `OverdueTaskAlertEvent`, and `OfficialScheduleAppliedEvent` now do).
2. **Taskiq Dead-Letter Queue (DLQ)**: `SimpleRetryMiddleware(default_retry_count=3)` retries transient worker exceptions 3 times; after 3 consecutive worker failures, failed task results are logged/recorded in Taskiq result backend rather than moved to a dedicated DLQ table.
3. **Live Docker Containers**: Rebuild containers (`docker compose up --build`) before running live E2E against `localhost:3000`.

### Next Issues to Handle in P2
1. **Shared Roadmap State (`FE-SYNC-01`, `FE-DUP-07`)**: Unify the 4 independent `roadmaps` signals across `RoadmapService`, `TaskService`, `ScheduleService`, and `AnalyticsService`.
2. **Workspace ↔ Tasks & Dashboard Adaptation (`FE-SYNC-03`, `FE-SYNC-05`, `FE-MOCK-07`)**: Sync task completion from Study Workspace to Task Queue and wire Dashboard Adaptation Modal to real active roadmap data + `reoptimize-schedule`.
3. **Prove Mode UI (`FE-FUNC-01`, UC-12)**: Build UI for existing milestone knowledge proof endpoints.
4. **Database Completeness (`BE-INT-01`/`DB-CONSIST-01`, `DB-CONSIST-02`)**: Map `PauseRecordORM` (35/35 ORM tables) and create Alembic migration `0014` for the 5 missing `updated_at` triggers.
5. **Remaining Mock/Unwired Flows (`FE-MOCK-02`, `FE-MOCK-03`, `FE-MOCK-05`, `FE-MOCK-06`, `FE-MOCK-08`, `FE-MOCK-09`, `BE-MOCK-02`, `FE-API-05`)**.
