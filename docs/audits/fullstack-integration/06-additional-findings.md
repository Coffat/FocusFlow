# Additional System Quality Audit — FocusFlow

> **Audit Target**: FocusFlow Architecture, Security, Data Integrity, Performance & Completeness  
> **Auditor**: Principal Fullstack Engineer & Software Architecture Auditor  
> **Date**: 2026-11-20  
> **Scope**: Functional Completeness, Data Integrity, Security, Performance & Scalability, Architectural Boundaries

---

## 1. Executive Summary

Beyond standard route mapping and mock data checks, this audit evaluated systemic cross-cutting concerns: security boundaries, transaction and referential integrity, architectural invariants, and performance scalability.

### Key Quality Baseline
- **Foreign Key Indexing**: **100% coverage** (All 58 foreign key constraints in PostgreSQL are indexed with B-Tree indexes, preventing table locks during cascaded updates/deletes).
- **Defense-in-Depth Constraints**: 124 check constraints enforce domain bounds (Mode A/B bounds, session times, status enums, JSONB types).
- **Import Boundary Linter**: `lint-imports` passed with 5 kept and 0 broken contracts.
- **RAG SSRF Protection**: `SafeUrlFetcher` rigorously validates schemes and resolves DNS to prevent connections to private/link-local/loopback IP addresses.

### Critical Quality Issues Identified
1. **OAuth Account Link Hijacking (`BE-SEC-01` — CRITICAL)**: Unsigned OAuth state parameter allows account takeover in Google Calendar integration.
2. **Modular Monolith Boundary Breach via Raw SQL (`BE-ARCH-01` — HIGH)**: Execution sweeper executes raw SQL against Planning (`roadmaps`) and Account (`users`) tables, evading AST import linter contracts.
3. **Missing Prove Mode UI (`FE-FUNC-01` — HIGH)**: Core Zimmerman SRL milestone proof feature (SRS UC-12) is absent from the frontend despite complete backend endpoints.
4. **Missing Database Update Triggers (`DB-CONSIST-02` — MEDIUM)**: 5 PostgreSQL tables with `updated_at` lack the `fn_set_updated_at()` trigger.
5. **Orphaned Dead Table `pause_records` (`DB-CONSIST-01`, `DB-SCHEMA-01` — MEDIUM)**: Physical database table has no ORM mapping and is ignored by use cases.
6. **Unpaginated Collection Queries (`BE-API-04` — MEDIUM)**: Large collections return unbounded JSON arrays.
7. **Host Workstation Redis Config Discrepancy (`QA-GATE-01` — MEDIUM)**: `backend/.env` has `REDIS_HOST=redis`, breaking host `pytest` execution unless overridden.

---

## 2. Additional Findings Catalog

| Finding ID | Severity | Category | Affected File & Lines | Description / Summary |
|---|---|---|---|---|
| **BE-SEC-01** | **CRITICAL** | Security / OAuth & CSRF | `calendar_router.py#L53-L95` | Unsigned OAuth `state` parameter & unauthenticated callback allows calendar account hijacking. |
| **BE-ARCH-01** | **HIGH** | Architecture Boundary | `execution/presentation/tasks.py#L185-L245` | Raw SQL cross-context queries & mutations bypassing `lint-imports` contracts. |
| **FE-FUNC-01** | **HIGH** | Functional Completeness | `frontend/src/app/features/roadmaps/` | Prove Mode / Milestone Knowledge Proofs (SRS UC-12) completely absent from frontend UI. |
| **DB-CONSIST-01**| **MEDIUM** | Data Integrity / ORM | `backend/src/evaluation/infrastructure/orm/` | Table `pause_records` lacks an SQLAlchemy ORM model (Base.metadata has 34/35 tables). |
| **DB-CONSIST-02**| **MEDIUM** | Data Integrity / Triggers | `backend/alembic/versions/` (0004, 0007, 0008, 0010) | 5 tables with `updated_at` lack `fn_set_updated_at()` trigger. |
| **QA-GATE-01** | **MEDIUM** | Environment & Test Portability | `backend/.env#L24-L26` | `REDIS_HOST=redis` causes test connection failures when running pytest directly on host macOS. |
| **DB-SCHEMA-01** | **LOW** | Architectural Smell | `roadmap_management_use_cases.py#L320` | `pause_records` is an unintegrated orphan table; pause events are written to `schedule_change_logs`. |
| **DB-SCHEMA-02** | **LOW** | Documentation Drift | `docs/database/database-schema-design.md` | Doc states physical FK to `learning_concepts`; implementation uses `concept_key VARCHAR(160)`. |
| **BE-SEC-02** | **LOW** | Security / Log Exposure | `email_service.py#L122` | Plaintext OTP code printed to stdout via `print()` on SMTP fallback. |
| **FE-FUNC-03** | **LOW** | UX Completeness | `frontend/.../schedule-page.component.ts` | Schedule grid lacks Angular CDK drag-and-drop task rescheduling. |
| **QA-VERIF-01** | **LOW** | Frontend Build Warning | `frontend/src/styles.scss#L1` | Dart Sass `@import "tailwindcss"` deprecation warning during production build. |

---

## 3. Detailed Structured Audit Findings

### [BE-SEC-01] Unsigned OAuth State & Missing Authentication in Calendar Callback Endpoint
- **Severity**: **CRITICAL**
- **Category**: Security / OAuth Account Linking & CSRF
- **Affected Pages/Modules**: `account` context, Google Calendar OAuth integration
- **File Path + Line Numbers**:
  - [backend/src/account/presentation/calendar_router.py#L53-L95](file:///Users/vuthang/Documents/FocusFlow/backend/src/account/presentation/calendar_router.py#L53-L95)
  - [backend/src/account/application/use_cases/calendar/initiate_google_calendar_auth_use_case.py#L49-L61](file:///Users/vuthang/Documents/FocusFlow/backend/src/account/application/use_cases/calendar/initiate_google_calendar_auth_use_case.py#L49-L61)
  - [backend/src/account/application/use_cases/calendar/handle_google_calendar_oauth_callback_use_case.py#L48-L61](file:///Users/vuthang/Documents/FocusFlow/backend/src/account/application/use_cases/calendar/handle_google_calendar_oauth_callback_use_case.py#L48-L61)
- **Expected Behavior**: The Google OAuth callback endpoint (`GET /api/v1/account/calendar/google/callback`) must verify that the user completing the flow is authenticated, and the `state` query parameter must be cryptographically signed (e.g. HMAC-SHA256 with application secret) or verified against a server-side Redis nonce to prevent CSRF and account link hijacking.
- **Actual Behavior**: `handle_google_calendar_callback_get` has NO `user_id` authentication dependency (`get_current_learner_id` is missing). It decodes `state` directly from unverified base64 JSON (`user_id = UUID(state_data["user_id"])`) and passes it to the use case. Because `state` contains an unvalidated random nonce that is never checked in Redis or signed, an attacker can craft a base64 state with any target user's UUID and trick the system into binding an external calendar to that target account.
- **Evidence**:
  ```python
  # calendar_router.py:70-73
  decoded_bytes = base64.urlsafe_b64decode(state.encode("utf-8"))
  state_data = json.loads(decoded_bytes.decode("utf-8"))
  user_id = UUID(state_data["user_id"])
  # use case executes with user_id without session verification!
  ```
- **Impact**: Arbitrary calendar account hijacking; attacker can sync foreign events into a victim's study schedule or overwrite victim's calendar connection tokens.
- **Recommended Fix**: Sign `state` payload with `hmac.new(secret_key, ...)` in `InitiateGoogleCalendarAuthUseCase` and verify signature in `HandleGoogleCalendarOAuthCallbackUseCase`, or require the user's JWT access cookie in `handle_google_calendar_callback_get`.
- **Validation Steps**: Send GET request to `/api/v1/account/calendar/google/callback?code=mock_code&state=<base64_with_other_user_id>` without auth cookies; observe that backend accepts and processes it.
- **Confidence Level**: 100%

---

### [BE-ARCH-01] Raw SQL Cross-Context Mutation and Query Bypassing Boundary Linter
- **Severity**: **HIGH**
- **Category**: Architecture Boundary / Modular Monolith Violation
- **Affected Pages/Modules**: `execution` context (`sweep_overdue_tasks_and_anti_loop`, `deduct_overdue_reschedule_budget`)
- **File Path + Line Numbers**:
  - [backend/src/execution/presentation/tasks.py#L185-L189](file:///Users/vuthang/Documents/FocusFlow/backend/src/execution/presentation/tasks.py#L185-L189)
  - [backend/src/execution/presentation/tasks.py#L220-L225](file:///Users/vuthang/Documents/FocusFlow/backend/src/execution/presentation/tasks.py#L220-L225)
  - [backend/src/execution/presentation/tasks.py#L238-L245](file:///Users/vuthang/Documents/FocusFlow/backend/src/execution/presentation/tasks.py#L238-L245)
  - [backend/src/execution/presentation/tasks.py#L414-L425](file:///Users/vuthang/Documents/FocusFlow/backend/src/execution/presentation/tasks.py#L414-L425)
- **Expected Behavior**: In FocusFlow's Context-First Modular Monolith, Bounded Contexts must communicate across boundaries strictly via `public_api.py` query ports or transactional outbox events. Execution context must not directly touch `roadmaps` (owned by Planning) or `users` (owned by Account).
- **Actual Behavior**: Background sweepers in `execution/presentation/tasks.py` execute direct SQL queries:
  - `SELECT id, user_id, title, weekly_reschedule_budget, weekly_reschedule_used, budget_week_start FROM roadmaps`
  - `UPDATE roadmaps SET weekly_reschedule_used = 0, budget_week_start = :monday ...`
  - `SELECT id, email FROM users WHERE id = ANY(:uids)`
  - `UPDATE roadmaps SET weekly_reschedule_used = :new_used WHERE id = :rid`
  This evades Python AST import inspection (`lint-imports`), violating the modular monolith boundary.
- **Root Cause**: Budget reset and user email lookup were implemented inside the execution sweeper using raw SQL rather than defining appropriate query and bridge ports.
- **Evidence**:
  ```python
  # execution/presentation/tasks.py:220-225
  await cast(Any, session).execute(
      text("UPDATE roadmaps SET weekly_reschedule_used = 0, budget_week_start = :monday WHERE id = ANY(:rids) AND ..."),
      {"rids": roadmap_ids, "monday": current_monday},
  )
  ```
- **Impact**: Violates database encapsulation between contexts; breaks if Bounded Contexts are separated into independent PostgreSQL schemas or microservices.
- **Recommended Fix**: Move weekly reschedule budget management into a domain service/use case in `planning`, exposed via `PlanningExecutionBridgePort`. Query user email via existing `UserQueryPort`.
- **Validation Steps**: Inspect SQL execution statements in `execution/presentation/tasks.py`.
- **Confidence Level**: 100%

---

### [FE-FUNC-01] Complete Absence of Prove Mode / Milestone Knowledge Verification (SRS UC-12)
- **Severity**: **HIGH**
- **Category**: Missing SRS Feature / Incomplete Functional Scope
- **Affected Requirements**: SRS v1.3 UC-12 (Evaluation Context: Milestone Proof & Knowledge Verification)
- **Backend Availability**: Fully supported in OpenAPI `schema.d.ts`:
  - `POST /api/v1/evaluation/milestones/{milestone_id}/proofs/generate-jobs`
  - `POST /api/v1/evaluation/milestones/{milestone_id}/proofs/{proof_id}/submit`
- **Frontend Status**: 0 components, 0 services, 0 dialogs exist. No UI allows a student to enter Prove Mode, generate challenge questions, or submit code/answers to verify milestone mastery.
- **Impact**: Core Zimmerman SRL evaluation capability is unavailable to users despite being advertised in marketing and pricing.
- **Recommended Fix**: Create `ProveModeDialogComponent` in `features/evaluation/` or `features/roadmaps/` to invoke the proof generation and submission endpoints.
- **Validation Steps**: Open a completed milestone; click "Chứng minh kiến thức"; verify quiz/challenge dialog renders and submits answers to backend.
- **Confidence Level**: 100%

---

### [DB-CONSIST-01] Table `pause_records` lacks an SQLAlchemy ORM Model in `backend/src/evaluation/`
- **Severity**: **MEDIUM**
- **Category**: ORM / Schema Inconsistency
- **Affected Pages/Modules**: `backend/src/evaluation/infrastructure/orm/`, `backend/src/shared_kernel/infrastructure/database/session.py`
- **File Path + Line Numbers**: [backend/src/evaluation/infrastructure/orm/](file:///Users/vuthang/Documents/FocusFlow/backend/src/evaluation/infrastructure/orm/)
- **Expected Behavior**: All 35 physical tables defined in PostgreSQL and `schema.sql` should have corresponding SQLAlchemy 2.0 ORM models registered under `Base.metadata`.
- **Actual Behavior**: `Base.metadata.tables` contains exactly 34 tables. Table `pause_records` has no ORM class anywhere in `backend/src/evaluation/infrastructure/orm/`.
- **Root Cause**: During the transition to 35 tables, `pause_records` was created in Alembic migration 0002 and included in `schema.sql`, but the corresponding `pause_record_orm.py` was never created because roadmap pausing was handled differently in the application layer.
- **Impact**: Any attempt to perform ORM queries or database reflection on `pause_records` fails.
- **Recommended Fix**: Create `backend/src/evaluation/infrastructure/orm/pause_record_orm.py` and export it in `__init__.py`.
- **Validation Steps**: Inspect `Base.metadata.tables` to confirm all 35 tables are registered.
- **Confidence Level**: 100%

---

### [DB-CONSIST-02] Five (5) PostgreSQL tables with `updated_at` columns lack the `fn_set_updated_at()` trigger
- **Severity**: **MEDIUM**
- **Category**: Database Triggers & Data Integrity
- **Affected Pages/Modules**: `backend/alembic/versions/` (migrations 0004, 0007, 0008, 0010)
- **File Path + Line Numbers**:
  - `backend/alembic/versions/0004_knowledge_base_tables.py` (`learning_concepts`)
  - `backend/alembic/versions/0007_ai_harness_workflows.py` (`workflow_runs`)
  - `backend/alembic/versions/0008_knowledge_rag.py` (`knowledge_sources`)
  - `backend/alembic/versions/0010_learner_intelligence.py` (`learner_memory_items`, `learner_concept_masteries`)
- **Expected Behavior**: All 25 tables in PostgreSQL with an `updated_at` column should have a `BEFORE UPDATE` trigger attached to execute `fn_set_updated_at()`.
- **Actual Behavior**: Exactly 5 tables are missing triggers:
  1. `knowledge_sources`
  2. `learner_concept_masteries`
  3. `learner_memory_items`
  4. `learning_concepts`
  5. `workflow_runs`
- **Root Cause**: Alembic migration scripts created tables with `updated_at` columns using `server_default=sa.func.now()`, but did not execute raw SQL `CREATE TRIGGER trg_..._updated_at BEFORE UPDATE ON ... FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at()`.
- **Impact**: If any of these 5 tables are updated via direct SQL or background scripts without ORM automatic timestamp updating, `updated_at` will remain stale, compromising data provenance and cache invalidation.
- **Recommended Fix**: Add an Alembic migration creating triggers for the 5 tables.
- **Validation Steps**: Query `information_schema.triggers` to confirm 25 triggers exist.
- **Confidence Level**: 100%

---

### [QA-GATE-01] Integration test failure when running pytest on host due to `REDIS_HOST=redis` in `.env`
- **Severity**: **MEDIUM**
- **Category**: Environment Configuration / Test Portability
- **Affected Pages/Modules**: `backend/tests/test_auth.py`, `backend/tests/test_otp_auth.py`
- **File Path + Line Numbers**: [backend/.env#L24-L26](file:///Users/vuthang/Documents/FocusFlow/backend/.env#L24-L26)
- **Expected Behavior**: Running `pytest` on the local developer workstation should seamlessly execute all integration tests against local services mapped to `localhost:6379`.
- **Actual Behavior**: When executed directly on macOS via `uv run pytest`, tests calling Redis fail with:
  ```
  redis.exceptions.ConnectionError: Error 8 connecting to redis:6379. nodename nor servname provided, or not known.
  ```
- **Root Cause**: `backend/.env` has `POSTGRES_SERVER=localhost` but `REDIS_HOST=redis` (which only resolves inside Docker network `focusflow-network`).
- **Impact**: Developers running local tests experience false-negative test failures unless they execute inside Docker or manually set `REDIS_HOST=localhost`.
- **Recommended Fix**: In `backend/.env`, set `REDIS_HOST=localhost` and `REDIS_URL=redis://localhost:6379/0`, while allowing Docker Compose to override them with `REDIS_HOST=redis` via `docker-compose.yml`.
- **Validation Steps**: Update `backend/.env`; run `uv run --extra dev pytest tests/test_auth.py tests/test_otp_auth.py -q`; verify exit code 0.
- **Confidence Level**: 100%

---

### [BE-SEC-02] Plaintext OTP Code Printed to Standard Output on SMTP Fallback
- **Severity**: **LOW**
- **Category**: Security & Observability / Secret Exposure in Console Logs
- **Affected Pages/Modules**: `account/infrastructure/email/email_service.py`
- **File Path + Line Numbers**: [backend/src/account/infrastructure/email/email_service.py#L122](file:///Users/vuthang/Documents/FocusFlow/backend/src/account/infrastructure/email/email_service.py#L122)
- **Expected Behavior**: One-time passwords (OTPs) should never be printed in plain text to standard output, where container log aggregators or terminal recordings can capture them.
- **Actual Behavior**: When an SMTP delivery error occurs, line 122 executes: `print(f"\n[SMTP ERROR FALLBACK] OTP for {to_email} is: {otp_code}\n")`.
- **Root Cause**: Debug helper left in place for local testing when SMTP is misconfigured.
- **Impact**: OTP leakage into container standard streams, violating security baseline rules.
- **Recommended Fix**: Remove the `print` statement; log an error event with redacted details instead.
- **Validation Steps**: Cause SMTP failure during registration and check process stdout for OTP code.
- **Confidence Level**: 100%

---

### [QA-VERIF-01] Dart Sass `@import` deprecation warning during Frontend production build
- **Severity**: **LOW**
- **Category**: Frontend Tooling / Deprecation Warning
- **Affected Pages/Modules**: `frontend/src/styles.scss`
- **File Path + Line Numbers**: [frontend/src/styles.scss#L1](file:///Users/vuthang/Documents/FocusFlow/frontend/src/styles.scss#L1)
- **Expected Behavior**: Production build executes with 0 warnings.
- **Actual Behavior**: `ng build --configuration production` completes successfully in 6.55s, but outputs:
  ```
  ▲ [WARNING] Deprecation [plugin angular-sass]
      src/styles.scss:1:8:
        1 │ @import "tailwindcss";
          ╵         ^
    Sass @import rules are deprecated and will be removed in Dart Sass 3.0.0.
  ```
- **Root Cause**: Angular 21 Sass compiler uses Dart Sass, which is deprecating `@import` in favor of `@use`. In Tailwind CSS v4, `@import "tailwindcss";` is standard CSS import syntax, but when processed by `styles.scss` (Sass compiler), Dart Sass intercepts it as a deprecated Sass import.
- **Impact**: Non-blocking today, but could cause a warning or error when Dart Sass 3.0.0 is released.
- **Recommended Fix**: Rename `frontend/src/styles.scss` to `frontend/src/styles.css` (since FocusFlow uses pure Tailwind CSS v4 without Sass variables) and update `angular.json` style entry from `src/styles.scss` to `src/styles.css`.
- **Validation Steps**: Build frontend: `pnpm exec ng build --configuration production`; confirm warning is eliminated.
- **Confidence Level**: 100%
