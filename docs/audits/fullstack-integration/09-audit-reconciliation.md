# Audit Reconciliation Report — FocusFlow

> **Role**: Principal Software Architect & Lead Remediation Engineer  
> **Date**: 2026-11-21  
> **Scope**: Verification of all findings across `01-system-inventory.md` .. `08-verification-report.md` against actual source code, SRS v1.3, ADR-001..ADR-010, and `AGENTS.md`.  
> **Outcome**: Full Finding Registry reconciled, 7 critical audit inaccuracies/omissions corrected, 100% of verified findings mapped to dependency-ordered tasks in [07-remediation-plan.md](file:///Users/vuthang/Documents/FocusFlow/docs/audits/fullstack-integration/07-remediation-plan.md).

---

> **Last Status Update**: 2026-11-21 — **ALL P0 (7), P1A (3), P1B (8), P2A (6), P2B1 (7), P2B2A (4), and P2B2B (4: `FE-MOCK-03`, `FE-MOCK-08`, `FE-API-05`, `BE-API-02` Billing — live provider `NOT VERIFIED`) are RESOLVED** with full unit/integration/Playwright E2E evidence ([10](file:///Users/vuthang/Documents/FocusFlow/docs/audits/fullstack-integration/10-p0-implementation-report.md), [11](file:///Users/vuthang/Documents/FocusFlow/docs/audits/fullstack-integration/11-p0-closure-and-p1a-report.md), [12](file:///Users/vuthang/Documents/FocusFlow/docs/audits/fullstack-integration/12-p1b-implementation-report.md), [13](file:///Users/vuthang/Documents/FocusFlow/docs/audits/fullstack-integration/13-p2a-data-consistency-report.md), [14](file:///Users/vuthang/Documents/FocusFlow/docs/audits/fullstack-integration/14-p2b1-data-integrity-report.md), [15](file:///Users/vuthang/Documents/FocusFlow/docs/audits/fullstack-integration/15-p2b2a-functional-completeness-report.md), [16](file:///Users/vuthang/Documents/FocusFlow/docs/audits/fullstack-integration/16-p2b2b-functional-integration-report.md)). **Only P3 (`TASK-34`..`TASK-42`) remains OPEN.**

## 1. Executive Summary of Reconciliation Corrections

Direct source-code verification of all 39 distinct finding IDs across frontend, backend, database, and QA reports uncovered **7 critical inaccuracies, traps, or missed sibling bugs** in the initial audit reports. Correcting these before coding prevented regressions on cold reloads, stylesheet overwrites, and incomplete security fixes:

1. **`FE-DUP-02` / `FE-SYNC-06` (Cold-Reload Trap Caught)**: The initial audit claimed `frontend/src/app/core/guards/auth.guard.ts` verified sessions via `checkSession()`. **Actual code** (`core/guards/auth.guard.ts#L5-L15`) only checks `authService.isAuthenticated()` synchronously and redirects to `'/login'` (instead of `'/sign-in'`). Blindly switching `app.routes.ts` to it would break cold page reloads on all protected routes because `app.config.ts` does not await `checkSession()`. Furthermore, `AuthService.checkSession()` lacks `shareReplay(1)` (causing duplicate `GET /api/v1/auth/me` calls) and `core/interceptors/auth.interceptor.ts` hangs queued 401 requests forever when `refreshToken()` fails.
2. **`BE-SEC-01` (Two Missed Vulnerabilities Caught)**: Beyond the unsigned OAuth `state` and unauthenticated `GET /google/callback`, source inspection uncovered:
   - **Open Redirect**: `calendar_router.py#L75` checks `if not return_to.startswith("/")` which allows protocol-relative URLs like `return_to="//evil.com"`.
   - **Silent Validation Bypass**: `HandleGoogleCalendarOAuthCallbackUseCase#L63-L64` catches `(ValueError, json.JSONDecodeError, UnicodeDecodeError)` and executes `pass`, ignoring malformed `state`.
3. **Backend Cookie & Logout Gaps Discovered During Auth Readiness Check**:
   - `auth_router.py` sets `access_token` and `refresh_token` cookies without `secure=True` in non-dev/test environments (violating ADR-008 §3.2 over HTTPS).
   - `POST /api/v1/auth/logout` deletes cookies but does not revoke the `refresh_token` in Redis.
   - `evaluation/presentation/deps.py#L146-L162` does not verify `payload.get("type") == "access"` (unlike `account`, `planning`, `execution`).
4. **`FE-API-03` (Two Missed Sibling Bugs Caught)**: In `roadmaps-hub.component.ts`, `executePause()` (`#L245-L254`) has the **exact same inverted error bug** as `executeResume()` (mutates status to `'PAUSED'` and fires toast on HTTP error), and `onArchiveRoadmap()` (`#L322-L329`) fires `'Đã lưu trữ'` toast synchronously before HTTP completes.
5. **`FE-MOCK-01` (Double Fallback Caught)**: Even after removing the `catch` fallback in `settings.service.ts#L64-L74`, `settings-page.component.ts` (`#L477-L511, #L949-L958`) still renders hardcoded fallbacks (`2`, `10`, `3450`, `defaultCycleEnd`) whenever `quota()` is `null`, with zero loading/error/empty/retry UI states.
6. **`QA-VERIF-01` (File Overwrite Trap Caught)**: `frontend/src/styles.css` **already exists** and is imported by `styles.scss#L44`. Blindly renaming `styles.scss` to `styles.css` as originally recommended would overwrite existing styles.
7. **`BE-DUP-01` (Partial Inaccuracy Corrected)** & **`BE-ARCH-01` (Wider Scope)**: Taskiq keys tasks by `module:func_name` so duplicate `@broker.task` names do not overwrite each other (downgraded to LOW/MEDIUM cleanup). Conversely, raw SQL cross-context queries in `execution/presentation/tasks.py` span 5 blocks (`#L204-L224, #L258-L265, #L281-L297, #L328-L335, #L408-L427`).

---

## 2. Reconciled Finding Registry

### Root-Cause Groupings
Findings sharing the same underlying cause are grouped so fixes eliminate root causes rather than symptoms:
- **RC-AUTH-COOKIE**: `FE-API-04`, `FE-SYNC-06`, `FE-DUP-01`, `FE-DUP-02` (Legacy localStorage Bearer token + duplicate guard/interceptor)
- **RC-OAUTH-STATE**: `BE-SEC-01` (Unsigned OAuth state, unauthenticated GET callback, open redirect, silent decode error)
- **RC-ROADMAP-OPTIMISTIC**: `FE-API-03` (Inverted error callbacks in `executeResume` & `executePause`, synchronous toast in `onArchiveRoadmap`)
- **RC-QUOTA-FALLBACK**: `FE-MOCK-01` (Silent catch mock in `SettingsService` + template fallbacks in `SettingsPageComponent`)
- **RC-API-CONSTANTS**: `FE-API-01`, `FE-API-02`, `BE-API-01` (Stale `api-endpoints.ts` diverging from OpenAPI 3.1)
- **RC-PAUSE-ORPHAN**: `BE-INT-01`, `DB-CONSIST-01`, `DB-SCHEMA-01` (`pause_records` table unmapped in ORM and unused by pause/resume use cases)
- **RC-ROADMAP-STATE-SILO**: `FE-SYNC-01`, `FE-DUP-07` (4 independent `roadmaps` signals & `loadRoadmaps()` fetchers)
- **RC-WEBCAL-BILLING-UNWIRED**: `FE-MOCK-02`, `FE-API-05`, `BE-API-02` (ORM tables exist for `webcal_tokens` & `payment_transactions` without routers/use cases/UI)
- **RC-SRL-UNWIRED**: `FE-MOCK-05`, `BE-MOCK-02` (Hardcoded frontend SRL metrics + stubbed backend SRL aggregator)
- **RC-DEAD-FE-CODE**: `FE-DUP-03`, `FE-DUP-04`, `FE-DUP-05`, `FE-DUP-06` (Orphaned legacy components and 1-line re-export facades)

### Master Registry Table

| Finding ID | Reconciled Severity | Verification Status | Root-Cause Group | Exact Source Evidence | Affected Components | Remediation Task | Test Requirements |
|---|---|---|---|---|---|---|---|
| **BE-SEC-01** | **CRITICAL** | **VERIFIED** *(+2 nuances)* | `RC-OAUTH-STATE` | `calendar_router.py:53-95`, `initiate_google_calendar_auth_use_case.py:49-60`, `handle_google_calendar_oauth_callback_use_case.py:51-65` | Account Calendar OAuth | **TASK-02** (P0) | Negative tests: tampered/unsigned/expired/replayed state, mismatched user, unauthenticated GET, `//evil.com` redirect; positive valid callback |
| **FE-API-04** | **CRITICAL** | **VERIFIED** | `RC-AUTH-COOKIE` | `auth.service.ts:60-67,74,363`, `core/interceptors/auth.interceptor.ts:20-25,53-80` | AuthService, Interceptor, Guards | **TASK-01** (P0) | Unit + E2E: login/refresh/logout/expired session/guard/SSE with `localStorage.access_token === null` |
| **FE-SYNC-06** | **CRITICAL** *(elevated)* | **VERIFIED** *(trap caught)* | `RC-AUTH-COOKIE` | `guards/auth.guard.ts:6-32`, `core/guards/auth.guard.ts:5-15`, `app.routes.ts:4` | Route Guard, Cold Reload | **TASK-01** (P0) | Unit: guard denies when cookie invalid even if `localStorage` polluted; allows on cold reload when `checkSession()` succeeds |
| **FE-API-03** | **HIGH** | **VERIFIED** *(+2 siblings)* | `RC-ROADMAP-OPTIMISTIC` | `roadmaps-hub.component.ts:235-256, 289-310, 312-334` | RoadmapsHubComponent, RoadmapService | **TASK-03** (P0) | Unit: error path for `executeResume`, `executePause`, `onArchiveRoadmap` preserves status & shows error toast |
| **FE-MOCK-01** | **HIGH** | **VERIFIED** *(double fallback)* | `RC-QUOTA-FALLBACK` | `settings.service.ts:55-78`, `settings-page.component.ts:477-511, 949-958` | SettingsService, SettingsPageComponent | **TASK-04** (P0) | Unit: HTTP error sets `quota=null`, `quotaError!=null`; template renders loading/error/empty/retry without `3450`/`10`/`2` |
| **BE-INT-02** | **HIGH** | **VERIFIED** | Standalone | `shared_kernel/infrastructure/outbox/relay.py:10-29` | Outbox Relay, Overdue Email Alerts | **TASK-11** (P1) | Integration: pending outbox event dispatches consumer before `PUBLISHED`; failed dispatch stays retryable |
| **BE-MOCK-01** | **HIGH** | **VERIFIED** | Standalone | `account/presentation/tasks.py:10-13`, `quota_facade_adapter.py:435-458` | AI Quota Sweeper | **TASK-12** (P1) | Unit/Integration: expired `RESERVED` row transitions to `EXPIRED` and refunds credit |
| **BE-ARCH-01** | **HIGH** | **VERIFIED** *(wider scope)* | Standalone | `execution/presentation/tasks.py:204-224,258-265,281-297,328-335,408-427` | Execution Sweeper, Planning/Account Boundaries | **TASK-13** (P1) | Unit + `lint-imports`: zero raw SQL on `roadmaps`/`users` in `execution` |
| **BE-API-03** | **HIGH** *(elevated from MED)* | **VERIFIED** | Standalone | `planning/presentation/routers.py:464-516` | Knowledge Upload / URL Endpoints | **TASK-14** (P1) | Integration: invalid file ext/size & SSRF URL return HTTP 400/422, not 500 |
| **FE-SYNC-02** | **HIGH** | **VERIFIED** | Standalone | `dashboard.component.html:66-73`, `roadmaps-hub.component.html:284-291` | Dashboard, RoadmapsHub, WizardHost | **TASK-15** (P1) | Unit: emitting `roadmapApplied` triggers `loadSummary()` / `loadRoadmaps()` |
| **FE-MOCK-04** | **HIGH** | **VERIFIED** | Standalone | `settings-page.component.ts:1277-1305` | Settings Privacy Tab, Account Deletion | **TASK-16** (P1) | Unit + Backend Integration: GDPR delete calls backend endpoint or disables misleading claim until API exists |
| **FE-FUNC-01** | **HIGH** | **VERIFIED** | Standalone | `core/api/schema.d.ts:1278,1295` (0 FE usages) | Roadmaps / Evaluation Prove Mode (UC-12) | **TASK-21** (P2) | Unit + E2E: generate milestone proof, submit answer, render evaluation score |
| **FE-SYNC-01** | **HIGH** | **VERIFIED** *(line fix)* | `RC-ROADMAP-STATE-SILO` | `roadmap.service.ts:207`, `task.service.ts:56`, `schedule.service.ts:132`, `analytics.service.ts:63` | 4 Feature Services | **TASK-22** (P2) | Unit: single shared roadmap signal updates across slices on pause/resume/create |
| **FE-API-01** | **MEDIUM** *(reclassified)* | **VERIFIED** *(line fix)* | `RC-API-CONSTANTS` | `api-endpoints.ts:85-89` | `api-endpoints.ts`, Profile/Settings Services | **TASK-17** (P1) | Unit + Contract test: `API_ENDPOINTS` paths match OpenAPI `schema.d.ts` |
| **FE-API-02** | **MEDIUM** | **VERIFIED** *(line fix)* | `RC-API-CONSTANTS` | `api-endpoints.ts:9-12, 28-31, 90-94` | `api-endpoints.ts` | **TASK-17** (P1) | Static check: no ghost endpoints in active constants |
| **BE-API-01** | **MEDIUM** | **VERIFIED** | `RC-API-CONSTANTS` | `api-endpoints.ts:9-12, 30-31, 85-94` | Frontend/Backend Contract Map | **TASK-17** (P1) | Merged with `FE-API-01`/`FE-API-02` |
| **FE-MOCK-02** | **HIGH** | **VERIFIED** | `RC-WEBCAL-BILLING-UNWIRED` | `settings-page.component.ts:941-943`, `settings.service.ts:94-99` | Settings Calendar Tab, Account Context | **TASK-23** (P2) | Integration: backend SHA-256 WebCal token create/rotate + frontend binding |
| **BE-API-02** | **MEDIUM** | **VERIFIED** | `RC-WEBCAL-BILLING-UNWIRED` | `account/infrastructure/orm/user_orm.py:435-505` | WebCal & Billing Routers/Use Cases | **TASK-23** & **TASK-28** (P2) | Integration tests for WebCal & Payment checkout/webhook |
| **FE-API-05** | **MEDIUM** | **VERIFIED** | `RC-WEBCAL-BILLING-UNWIRED` | `pricing.component.ts:209-214`, `api-endpoints.ts:9-12` | Pricing / Billing Checkout | **TASK-28** (P2) | Unit + Integration: checkout modal with `PAYMENT_PROVIDER=local_mock` |
| **FE-MOCK-06** | **MEDIUM** *(reclassified)* | **VERIFIED** | Standalone | `admin-dashboard-page.component.ts:117-134` | `/admin` Route | **TASK-24** (P2) | Route guard / admin role check + real telemetry API or feature-flag gate |
| **BE-INT-01** | **MEDIUM** *(reclassified)* | **VERIFIED** | `RC-PAUSE-ORPHAN` | `alembic/versions/0002:1018-1065`, `roadmap_management_use_cases.py:292-396` | Planning/Evaluation Pause Lifecycle | **TASK-25** (P2) | Integration: pause/resume writes `pause_records` row; `Base.metadata` has 35 tables |
| **DB-CONSIST-01** | **MEDIUM** | **VERIFIED** | `RC-PAUSE-ORPHAN` | `evaluation/infrastructure/orm/` (34/35 tables) | SQLAlchemy ORM Metadata | **TASK-25** (P2) | Merged with `BE-INT-01` |
| **DB-SCHEMA-01** | **LOW** | **VERIFIED** | `RC-PAUSE-ORPHAN` | `roadmap_management_use_cases.py:320-336` | `pause_records` vs `schedule_change_logs` | **TASK-25** (P2) | Merged with `BE-INT-01` |
| **DB-CONSIST-02** | **MEDIUM** | **VERIFIED** | Standalone | `alembic/versions/0004,0007,0008,0010` | 5 PostgreSQL Tables | **TASK-26** (P2) | Migration test: 25 `updated_at` triggers verified in `information_schema.triggers` |
| **FE-SYNC-03** | **MEDIUM** | **VERIFIED** | Standalone | `workspace-session.service.ts:700-732`, `task.service.ts:198-220` | Workspace ↔ Tasks | **TASK-27** (P2) | Unit: completing task in Workspace updates `TaskService.tasks()` |
| **FE-SYNC-04** | **LOW** *(reclassified)* | **PARTIALLY ACCURATE** | Standalone | `schedule-page.component.ts:909-933`, `dashboard.component.ts:93-97` | Schedule ↔ Dashboard | **TASK-27** (P2) | Note: Dashboard already refetches on `ngOnInit`; invalidate cached summary to avoid flash |
| **FE-SYNC-05** | **MEDIUM** | **VERIFIED** | Standalone | `dashboard.component.html:76-80` | Dashboard Adaptation Modal | **TASK-29** (P2) | Unit: `(confirmAdaptation)` dispatches re-optimization API & reloads summary |
| **FE-MOCK-07** | **LOW** | **VERIFIED** | Standalone | `adaptation-modal-dialog.component.ts:29-33`, `dashboard.component.html:76-80` | Adaptation Modal Defaults | **TASK-29** (P2) | Unit: Dashboard binds real active roadmap data; defaults are empty/neutral |
| **FE-MOCK-03** | **MEDIUM** | **VERIFIED** | Standalone | `settings-page.component.ts:1198-1218` | Settings GDPR Export | **TASK-30** (P2) | Integration: backend export endpoint or accurate UI copy until implemented |
| **FE-MOCK-05** | **MEDIUM** | **VERIFIED** | `RC-SRL-UNWIRED` | `profile.service.ts:28-32` | Profile SRL Metrics | **TASK-31** (P2) | Unit + Backend: derive SRL metrics from `learner_profiles` / `analytics/summary` |
| **BE-MOCK-02** | **MEDIUM** | **VERIFIED** | `RC-SRL-UNWIRED` | `account/presentation/tasks.py:16-19` | SRL Profile Aggregator Task | **TASK-31** (P2) | Unit: `StudySessionCompletedEvent` updates `learner_profiles` metrics |
| **FE-MOCK-08** | **MEDIUM** | **VERIFIED** | Standalone | `app-navbar.component.html:64-71` | Main Navbar Bell Button | **TASK-32** (P2) | Unit: clicking bell opens alerts popover (or hide until backend alert feed exists) |
| **FE-MOCK-09** | **MEDIUM** | **VERIFIED** | Standalone | `workspace-session.service.ts:929-984` | Workspace Pomodoro Counter | **TASK-33** (P2) | Unit: prefer server `today_focus.pomodoros_completed_today`, remove localStorage source of truth |
| **BE-API-04** | **MEDIUM** | **VERIFIED** | Standalone | `execution/presentation/routers.py:210,264,575`, `planning:519,779`, `account:135` | Collection Listing Endpoints | **TASK-34** (P3) | Integration: default `limit`/`offset` backward-compatible with existing clients |
| **QA-GATE-01** | **MEDIUM** | **VERIFIED** | Standalone | `backend/.env:24-26` | Local Host Pytest Execution | **TASK-18** (P1) | Verify host `pytest tests/test_auth.py` passes without env overrides |
| **BE-SEC-02** | **LOW** | **VERIFIED** | Standalone | `account/infrastructure/email/email_service.py:122` | Email Service SMTP Fallback | **TASK-19** (P1) | Unit: SMTP error logs redacted failure without printing plaintext OTP |
| **FE-DUP-01** | **MEDIUM** | **VERIFIED** | `RC-AUTH-COOKIE` | `app/interceptors/auth.interceptor.ts` | Legacy Interceptor | **TASK-01** (P0) | Delete unused duplicate file + spec safely during Auth P0 |
| **FE-DUP-02** | **HIGH** | **PARTIALLY ACCURATE** | `RC-AUTH-COOKIE` | `app/guards/auth.guard.ts` vs `core/guards/auth.guard.ts` | Legacy Guard | **TASK-01** (P0) | Rewrite `core/guards/auth.guard.ts` with `checkSession()` + `/sign-in`, then delete legacy |
| **BE-DUP-01** | **LOW** *(downgraded)* | **PARTIALLY ACCURATE** | Standalone | `account/tasks.py:43`, `execution/tasks.py:162,437`, `evaluation/tasks.py:10` | Taskiq Registrations | **TASK-35** (P3) | Remove duplicate task registrations + dead `sync_external_google_calendar` (`BE-MOCK-03`) |
| **BE-MOCK-03** | **LOW** *(downgraded)* | **VERIFIED** | Standalone | `execution/presentation/tasks.py:431-434` | Dead Calendar Stub Task | **TASK-35** (P3) | Merged into `TASK-35` |
| **FE-DUP-03..06** | **LOW** | **VERIFIED** | `RC-DEAD-FE-CODE` | Orphaned footer/header, `LoginPageComponent`, `DashboardPageComponent`, 3 facades | Frontend Cleanup | **TASK-36** (P3) | Verify 0 consumers via grep, delete files, pass `ng build` + `ng test` |
| **FE-DUP-07** | **MEDIUM** | **VERIFIED** | `RC-ROADMAP-STATE-SILO` | 4 services' `loadRoadmaps()` | Frontend Services | **TASK-22** (P2) | Merged with `FE-SYNC-01` |
| **FE-DUP-08** | **LOW** | **VERIFIED** | Standalone | `task.service.ts:244` vs `schedule.service.ts:218` | Task Reschedule | **TASK-37** (P3) | Delegate `ScheduleService.rescheduleTask` to `TaskService` |
| **FE-DUP-09** | **LOW** | **VERIFIED** *(+2 locations)* | Standalone | `schedule.service.ts:34`, `analytics.service.ts:25`, `dashboard-weekly-grid:24`, `schedule-proposal-dialog:64` | Date Utilities | **TASK-37** (P3) | Extract `core/utils/date.util.ts` |
| **BE-DUP-02** | **LOW** | **VERIFIED** | Standalone | `hybrid_availability_rule_engine.py:163,184`, `spatio_temporal_engine.py:406,422,672,689` | Interval Overlap Logic | **TASK-38** (P3) | Extract helper only if domain boundaries stay clean |
| **BE-API-05** | **LOW** | **VERIFIED** | Standalone | `execution/presentation/routers.py` | Missing `GET /api/v1/tasks/{task_id}` | **TASK-39** (P3) | Add endpoint only when a consumer needs it (no speculative API) |
| **FE-FUNC-03** | **LOW** | **VERIFIED** | Standalone | `schedule-page.component.ts` | Schedule Drag-and-Drop | **TASK-40** (P3) | Optional UX enhancement (click reschedule already works) |
| **DB-SCHEMA-02** | **LOW** | **VERIFIED** | Standalone | `docs/database/database-schema-design.md:65,838-841` | Schema Documentation | **TASK-41** (P3) | Sync markdown doc with `concept_key VARCHAR(160)` & `milestone_proofs` DDL |
| **QA-VERIF-01** | **LOW** | **PARTIALLY ACCURATE** *(trap caught)* | Standalone | `frontend/src/styles.scss:1,43-44` + existing `frontend/src/styles.css` | Frontend Stylesheet | **TASK-42** (P3) | Merge `styles.scss` into `styles.css` carefully without overwriting; verify `ng build` |

---

## 3. Gaps Found in Original `07-remediation-plan.md`

1. **7 Mermaid Tasks Had Zero Implementation Sections**: `TASK-23`, `TASK-26`, `TASK-32`, `TASK-33`, `TASK-34`, `TASK-36`, `TASK-37` appeared in the diagram but had no text specification, acceptance criteria, or validation plan.
2. **17 Verified Findings Were Unmapped**: `FE-MOCK-05`, `FE-MOCK-06`, `FE-MOCK-07`, `FE-MOCK-09`, `FE-SYNC-04`, `FE-API-02`, `FE-API-05`, `FE-DUP-06`, `FE-DUP-08`, `FE-DUP-09`, `FE-FUNC-03`, `BE-MOCK-03`, `BE-API-02`, `BE-API-03`, `BE-API-05`, `BE-DUP-02`, `DB-SCHEMA-02` had no assigned tasks.
3. **2 Non-Existent IDs Referenced**: `FE-FUNC-02` and `FE-FUNC-04` were mentioned in scratch notes/summary but not defined in `06-additional-findings.md` (already covered by `FE-MOCK-08` and `FE-API-05`).
4. **No Rollback Plans & No Backward-Compatibility Risk Assessment**: Original plan lacked rollback steps and risk gates for auth/cookie changes, pagination, and DB migrations.

---

## 4. High-Risk Tasks (Backward Compatibility, Data Integrity, Security)

| Task | Risk Type | Potential Failure Mode | Mandatory Mitigation |
|---|---|---|---|
| **TASK-01** (Cookie-Only Auth) | Security + Backward Compatibility | Cold reload redirect loop if `authGuard` doesn't await `checkSession()`; concurrent 401 hang; E2E tests relying on `localStorage` fail; HTTPS prod cookies without `Secure` | Keep backend JSON `access_token` field for non-browser API tests; rewrite `core/guards/auth.guard.ts` with `shareReplay(1)` `checkSession()`; fix 401 queue subject; add `secure` cookie flag in non-dev/test |
| **TASK-02** (OAuth State Signing) | Security + Functional Regression | Breaking legitimate Google Calendar OAuth redirect if `SameSite` cookie is dropped or existing unit tests construct unsigned base64 state | Verify `SameSite=Lax` sends cookie on top-level GET redirect; use `OAuthStateStorePort` with Redis TTL + atomic consume; update unit tests & add negative security tests |
| **TASK-11** (Outbox Relay) | Data Integrity + Side-Effect Storm | Re-dispatching historical `PENDING` rows en masse on first deploy | Limit batch size, verify idempotency via `processed_events`, and handle unknown event types safely without infinite retry loops |
| **TASK-25** (`pause_records` ORM) | Data Integrity | Diverging from `schedule_change_logs` history for already-paused roadmaps | Keep `schedule_change_logs` write intact; add `pause_records` insert/update alongside it; handle resume when no `pause_records` row exists (legacy fallback) |
| **TASK-34** (Pagination) | Backward Compatibility | Changing `list[T]` response shape to `{ items, total }` breaks frontend OpenAPI clients | Add optional `limit`/`offset` query params with safe defaults while preserving array response shape (or version/migrate FE + BE together) |
| **TASK-42** (`styles.scss` -> `.css`) | Build / Visual Regression | Overwriting existing `frontend/src/styles.css` | Merge `styles.scss` and `styles.css` deliberately, placing all `@import` statements before `@theme` |

---

## 5. Re-Prioritization Framework Applied to `07-remediation-plan.md`

Tasks were re-ordered strictly by engineering risk hierarchy:
1. **P0 — Critical Security & Immediate Business Correctness** (`TASK-01`..`TASK-04`): Cookie-only auth & guard, Google Calendar OAuth state integrity/binding, RoadmapsHub false-success errors, Settings AI quota mock fallback. *(Scope of current implementation batch.)*
2. **P1 — High-Impact Reliability, Architecture & Contract Integrity** (`TASK-11`..`TASK-19`): Outbox relay dispatch, AI quota sweeper, raw SQL boundary refactor, knowledge upload 500→400, Wizard `(roadmapApplied)` sync, GDPR delete honesty, `api-endpoints.ts` cleanup, `REDIS_HOST` dev ergonomics, OTP stdout leak.
3. **P2 — Functional Completeness & Cross-Page State Consistency** (`TASK-21`..`TASK-33`): Prove Mode UI (UC-12), shared `RoadmapStore`, WebCal/Billing wiring, Admin gating, `pause_records` ORM, 5 missing `updated_at` triggers, Workspace↔Tasks sync, Dashboard adaptation modal, GDPR export, SRL aggregation, Notification bell, Workspace Pomodoro count.
4. **P3 — Performance, Scalability & Dead Code Cleanup** (`TASK-34`..`TASK-42`): Pagination, Taskiq duplicate cleanup, orphaned FE file deletion, rescheduling/date/interval deduplication, optional `GET /tasks/{id}`, drag-and-drop, schema doc sync, Sass warning cleanup.
