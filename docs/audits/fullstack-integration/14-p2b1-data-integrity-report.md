# P2B1 Database Integrity, Background Processing & Real Study Data Report — FocusFlow

> **Role**: Principal Backend Architect, Data Engineer & Reliability Engineer  
> **Branch**: `fix/p0-audit-remediation`  
> **Date**: 2026-11-21  
> **Scope**: P2B1 — `BE-INT-01` / `DB-CONSIST-01` / `DB-SCHEMA-01` (`pause_records`), `DB-CONSIST-02` (`updated_at` triggers), `BE-MOCK-02` / `FE-MOCK-05` (SRL Profile Aggregation), `FE-MOCK-09` (Server-Side Canonical Pomodoro Metrics)

---

## 1. Findings Resolved (Definition of Done Met)

| Finding ID | Severity | Status | Root Cause Resolved |
|---|---|---|---|
| **BE-INT-01 / DB-CONSIST-01 / DB-SCHEMA-01** | **MEDIUM / LOW** | **RESOLVED** | Created `PauseRecordORM` in `evaluation/infrastructure/orm/pause_record_orm.py` (bringing SQLAlchemy `Base.metadata` to **35/35** application tables), added Hexagonal `PauseRecordPort` + `PauseRecordAdapter` (sharing caller's `AsyncSession` with `FOR UPDATE` locking), and wired atomic pause/resume persistence into `PauseRoadmapUseCase` (now locking roadmap inside `async with self._uow:`) and `ResumeRoadmapUseCase`. |
| **DB-CONSIST-02** | **MEDIUM** | **RESOLVED** | Created Alembic migration `0014_add_updated_at_triggers` (`backend/alembic/versions/0014_add_missing_updated_at_triggers.py`, `down_revision="0013_ai_usage_audit_jsonb"`) attaching `fn_set_updated_at()` to all 5 missing tables (`knowledge_sources`, `learner_concept_masteries`, `learner_memory_items`, `learning_concepts`, `workflow_runs`). Verified `upgrade head` → `downgrade -1` → `upgrade head` and real PostgreSQL `UPDATE` trigger advancement across all 5 tables. |
| **BE-MOCK-02** | **MEDIUM** | **RESOLVED** | Built full SRL aggregation pipeline: `StudySession.finalize()` → `StudySessionCompletedEvent` in `outbox_events` → `relay_pending_outbox_events` → `aggregate_learner_srl_profile` (Taskiq worker with `processed_events` idempotency) → `AggregateSrlProfileUseCase` → `learner_profiles` → `ProfileResponseDTO.srl_profile` (`GET /api/v1/account/profile`). |
| **FE-MOCK-05** | **MEDIUM** | **RESOLVED** | Deleted hardcoded `45`, `1.05`, and `'Sequential Deep Work'` from `ProfileService` & `ProfilePageComponent`; derived `srlProfile` & `isSrlColdStart` from regenerated OpenAPI `LearnerSrlProfileDTO`; added explicit `"Chưa đủ dữ liệu học tập"` cold-start banner (`< 3` sessions) displaying `—` instead of fabricated metrics. |
| **FE-MOCK-09** | **MEDIUM** | **RESOLVED** | Deleted all `localStorage['focusflow_pomodoros_today_v1']` reads/writes from `WorkspaceSessionService`; bound `completedPomodorosToday` strictly to server-persisted `TodayFocusResponse.completed_sessions_today` (+ optimistic delta ONLY after successful `COMPLETED`/`PARTIAL_COMPLETED` `finalizeSession()`, never on timer hitting `0` before finalize or on `CANCELLED`/HTTP error). |

---

## 2. Database Design Decisions

1. **Keeping & Integrating `pause_records` (35-Table Invariant Preserved)**:
   - Per SRS v1.3 UC-22 (`FR-PAUSE-001`, `FR-PAUSE-002`) and `AGENTS.md` §8 (35-table architecture), `pause_records` is owned by the `evaluation` context and stores discrete pause windows (`pause_start_date`, `pause_end_date`, `shifted_days`, `status`), whereas `schedule_change_logs` records broader schedule diff audit logs.
   - `PauseRecordORM` enforces PostgreSQL's `chk_pause_records_duration` (`shifted_days = (pause_end_date - pause_start_date) + 1`, `shifted_days > 0`). When resumed with `shift_days=0`, the active pause record transitions to `CANCELLED` rather than violating `shifted_days > 0`.
   - `PauseRoadmapUseCase` now acquires `FOR UPDATE` on the roadmap row inside `async with self._uow:`, and `PauseRecordAdapter.create_active_pause` locks existing `ACTIVE` rows (`FOR UPDATE`) and cancels any stale `ACTIVE` rows before inserting, guaranteeing zero duplicate `ACTIVE` pause records under concurrent requests.
2. **Alembic Revision Length Constraint (`VARCHAR(32)`)**:
   - PostgreSQL's `alembic_version.version_num` column is `VARCHAR(32)`. The migration revision ID was set to `"0014_add_updated_at_triggers"` (28 chars) so upgrade/downgrade executes cleanly without truncation.
3. **No Invented SRL Composite Scores**:
   - Aggregation computes ONLY fields backed by `learner_profiles` columns & `study_sessions` rows: `total_completed_sessions`, `is_cold_start` (`< 3` sessions threshold), `optimal_focus_duration_mins` (median clamped `[15, 120]`), `estimation_bias_factor` (mean `actual/planned` clamped `[0.50, 2.00]`), `peak_productivity_slots` (top-2 user-timezone time-of-day buckets), `weekly_completion_rate` (clamped `[0.00, 100.00]`), and `last_aggregated_at`. No arbitrary 0–100 score or fabricated learning style label is computed.

---

## 3. Migration Evidence (`DB-CONSIST-02`)

```
alembic upgrade head  -> 0013_ai_usage_audit_jsonb -> 0014_add_updated_at_triggers (OK)
alembic downgrade -1  -> 0014_add_updated_at_triggers -> 0013_ai_usage_audit_jsonb (OK)
alembic upgrade head  -> 0013_ai_usage_audit_jsonb -> 0014_add_updated_at_triggers (OK)
alembic heads         -> 0014_add_updated_at_triggers (head)
```

Verified via `test_updated_at_triggers_integration.py` against live PostgreSQL:
- All **25/25** tables containing `updated_at` now have `BEFORE UPDATE` triggers executing `public.fn_set_updated_at()` in `information_schema.triggers`.
- Raw SQL `UPDATE` statements on `knowledge_sources`, `learner_concept_masteries`, `learner_memory_items`, `learning_concepts`, and `workflow_runs` automatically advance `updated_at`.

---

## 4. SRL Aggregation Pipeline & Pomodoro Canonical Data Flow

### SRL Pipeline (`BE-MOCK-02` + `FE-MOCK-05`)
```
StudySession.finalize()
  → StudySessionCompletedEvent persisted atomically in outbox_events
  → relay_pending_outbox_events (FOR UPDATE SKIP LOCKED + per-event commit)
  → _handle_study_session_completed_event → aggregate_learner_srl_profile.kiq(user_id, event_id)
  → Idempotency check (processed_events: "account.aggregate_learner_srl_profile_worker")
  → ExecutionDashboardQueryPort.get_srl_session_facts(user_id)
  → AggregateSrlProfileUseCase → upsert learner_profiles
  → GET /api/v1/account/profile (ProfileResponseDTO.srl_profile)
  → ProfileService.srlProfile → ProfilePageComponent (Cold-Start Banner vs Real Metrics)
```

### Pomodoro Canonical Data Flow (`FE-MOCK-09`)
```
POST /api/v1/sessions/{id}/finalize (status = COMPLETED | PARTIAL_COMPLETED)
  → StudySession persisted in PostgreSQL with ended_at (UTC)
  → GET /api/v1/sessions/today-focus resolves user local day window in user IANA timezone
  → Returns TodayFocusResponse.completed_sessions_today (excludes IN_PROGRESS & CANCELLED)
  → WorkspaceSessionService.completedPomodorosToday = todayFocus.completed_sessions_today + _localPomodoroDelta
    (delta incremented ONLY on confirmed COMPLETED/PARTIAL_COMPLETED finalize, reset to 0 on loadWorkspace())
  → Zero localStorage usage; identical across reloads, tabs, and independent devices.
```

---

## 5. Idempotency Guarantees & Limitations

- **`aggregate_learner_srl_profile`**: Checks `processed_events` (`account.aggregate_learner_srl_profile_worker`) before running and marks processed ONLY after aggregation commits. If the worker raises an exception, `processed_events` is NOT marked, enabling clean retry recovery (verified by integration test). Furthermore, aggregation itself is a deterministic full recomputation from persisted `study_sessions`, making it naturally idempotent even across multiple events.
- **`pause_records`**: Protected by `FOR UPDATE` locking on both `roadmaps` and active `pause_records` rows inside a single `AsyncUnitOfWork` transaction; transaction rollback leaves zero orphan rows.
- **Pomodoro counter**: Backend `GET /sessions/today-focus` counts distinct persisted `study_sessions` rows; `FinalizeStudySessionUseCase` rejects double-finalization (`InvalidSessionStateError`), preventing double-counting on retries or refreshes.
- **Limitation**: If a live Docker container (`focusflow-backend` on `localhost:8000`) is running an older image built before P2B1, `docker compose up --build` is required for the live container to serve `srl_profile` on `/api/v1/account/profile` (frontend safely handles `srl_profile === undefined` as cold-start).

---

## 6. Files Changed

### Backend
- **Created**:
  - [pause_record_orm.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/evaluation/infrastructure/orm/pause_record_orm.py)
  - [pause_record_adapter.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/evaluation/infrastructure/adapters/pause_record_adapter.py)
  - [0014_add_missing_updated_at_triggers.py](file:///Users/vuthang/Documents/FocusFlow/backend/alembic/versions/0014_add_missing_updated_at_triggers.py)
  - [learner_profile_repository_port.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/account/application/ports/learner_profile_repository_port.py)
  - [learner_profile_repository.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/account/infrastructure/repositories/learner_profile_repository.py)
  - [aggregate_srl_profile_use_case.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/account/application/use_cases/profile/aggregate_srl_profile_use_case.py)
  - [test_pause_records_integration.py](file:///Users/vuthang/Documents/FocusFlow/backend/tests/integration/planning/test_pause_records_integration.py)
  - [test_updated_at_triggers_integration.py](file:///Users/vuthang/Documents/FocusFlow/backend/tests/integration/shared_kernel/test_updated_at_triggers_integration.py)
  - [test_srl_profile_aggregation_integration.py](file:///Users/vuthang/Documents/FocusFlow/backend/tests/integration/account/test_srl_profile_aggregation_integration.py)
- **Modified**:
  - [evaluation/infrastructure/orm/__init__.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/evaluation/infrastructure/orm/__init__.py), [evaluation/public_api.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/evaluation/public_api.py), [evaluation/infrastructure/adapters/__init__.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/evaluation/infrastructure/adapters/__init__.py)
  - [roadmap_management_use_cases.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/application/use_cases/roadmap_management_use_cases.py), [planning/presentation/deps.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/planning/presentation/deps.py)
  - [execution/public_api.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/execution/public_api.py), [execution_dashboard_adapter.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/execution/infrastructure/adapters/execution_dashboard_adapter.py)
  - [account/presentation/tasks.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/account/presentation/tasks.py), [account/application/dtos/profile.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/account/application/dtos/profile.py), [update_profile_use_case.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/account/application/use_cases/profile/update_profile_use_case.py), [account/presentation/deps.py](file:///Users/vuthang/Documents/FocusFlow/backend/src/account/presentation/deps.py)

### Frontend
- **Created**:
  - [p2b1-study-data-integrity.spec.ts](file:///Users/vuthang/Documents/FocusFlow/frontend/e2e/p2b1-study-data-integrity.spec.ts)
- **Modified**:
  - [schema.d.ts](file:///Users/vuthang/Documents/FocusFlow/frontend/src/app/core/api/schema.d.ts) (regenerated from OpenAPI 3.1)
  - [profile.model.ts](file:///Users/vuthang/Documents/FocusFlow/frontend/src/app/features/profile/models/profile.model.ts), [profile.service.ts](file:///Users/vuthang/Documents/FocusFlow/frontend/src/app/features/profile/services/profile.service.ts), [profile.service.spec.ts](file:///Users/vuthang/Documents/FocusFlow/frontend/src/app/features/profile/services/profile.service.spec.ts)
  - [profile-page.component.ts](file:///Users/vuthang/Documents/FocusFlow/frontend/src/app/features/profile/components/profile-page.component.ts), [profile-page.component.spec.ts](file:///Users/vuthang/Documents/FocusFlow/frontend/src/app/features/profile/components/profile-page.component.spec.ts)
  - [workspace-session.service.ts](file:///Users/vuthang/Documents/FocusFlow/frontend/src/app/core/services/workspace-session.service.ts), [workspace-session.service.spec.ts](file:///Users/vuthang/Documents/FocusFlow/frontend/src/app/core/services/workspace-session.service.spec.ts)

---

## 7. Quality Gate Evidence

| Quality Gate | Command | Result |
|---|---|---|
| **Backend Lint & Format** | `ruff check .` & `ruff format --check .` | **PASS** (0 errors, 426 files formatted) |
| **Backend Strict Types** | `mypy --strict src` | **PASS** (305 files, 0 issues) |
| **Architecture Contracts** | `lint-imports` | **PASS** (5 kept, 0 broken) |
| **Full Backend Suite (incl. 9 new PG integration tests)** | `cd backend && uv run --extra dev pytest -q` | **PASS** (**779 passed, 3 skipped, 0 failed**) |
| **Alembic Migration Round-Trip** | `upgrade head` → `downgrade -1` → `upgrade head` | **PASS** (single head `0014_add_updated_at_triggers`) |
| **API Contract Check** | `bash scripts/check-api-contract.sh` | **PASS** (0 schema drift) |
| **Frontend Lint** | `cd frontend && pnpm exec ng lint` | **PASS** (0 errors) |
| **Frontend Unit Tests** | `cd frontend && pnpm exec ng test --watch=false` | **PASS** (**80/80 suites, 617/617 tests passed**) |
| **Frontend Production Build** | `cd frontend && pnpm exec ng build --configuration production` | **PASS** (0 errors, 6.96s) |
| **Playwright E2E (Real Backend + PG + Multi-Device)** | `cd frontend && pnpm exec playwright test e2e/p2b1-study-data-integrity.spec.ts` | **PASS** (**14.8s**, Pomodoro persistence + `localStorage` spoof ignored + `CANCELLED` excluded + Client B multi-device consistency + Profile cold-start banner) |

---

## 8. Remaining Risks & Recommendations for P2B2

### Residual Risks
1. **Live Docker Image Rebuild**: Rebuild `docker compose up --build` so running containers serve migration `0014` and the new `srl_profile` API field.
2. **`docs/database/schema.sql` Dump Refresh**: Regenerate `docs/database/schema.sql` via `pg_dump --schema-only` when cutting a release so the 5 new triggers appear in the static SQL snapshot (per `AGENTS.md`, never hand-edit `schema.sql`).
3. **SRL Cold-Start Threshold (`3` sessions)**: Currently `COLD_START_MIN_SESSIONS = 3`; confirm with product if a higher threshold (e.g. `5`) is preferred.

### Recommended Next Batch: **P2B2 — Functional Completeness**
1. **TASK-21 (`FE-FUNC-01`)**: Implement Prove Mode UI (UC-12) for existing milestone proof endpoints.
2. **TASK-23 (`FE-MOCK-02`, `BE-API-02`)**: Implement backend WebCal token endpoints (SHA-256 hashed) & bind Settings Calendar tab.
3. **TASK-24 (`FE-MOCK-06`)**: Gate `/admin` route behind admin role guard / feature flag until backend telemetry APIs exist.
4. **TASK-28 (`FE-API-05`, `BE-API-02`)**: Billing checkout & webhook integration (`PAYMENT_PROVIDER=local_mock`).
5. **TASK-30 (`FE-MOCK-03`)** & **TASK-32 (`FE-MOCK-08`)**: GDPR data export label/endpoint & Navbar notification bell.
