# FocusFlow — Staging User Acceptance Testing (UAT) Report

**Date:** 2026-11-18  
**Environment:** Docker Compose Staging Stack (`http://localhost:3000` Angular FE, `http://localhost:8000` FastAPI + Uvicorn + Taskiq worker-0/worker-1/scheduler, PostgreSQL 16 `pgvector`, Redis 7, CofHub Gateway `http://host.docker.internal:8045` -> `gemini-3.8-flash-*`)  
**Code Baseline:** PR-1..PR-4, PR-A..PR-E, DEF-17  
**Release Recommendation:** **NO-GO (for Closed Beta)**

---

## 1. Executive Summary & Release Decision

**Recommendation: NO-GO for Closed Beta**

While FocusFlow's planning domain invariants (**PR-A/B/C/D** safety gates, **FIT_CAPACITY** deferred-scope enforcement, **DEF-17** per-attempt AI usage/cost ledger, **Redis Milestone Checkpointing**, and **Overdue Sweeper** non-mutation guarantees) held up cleanly under live Staging verification, Staging UAT uncovered **2 P0 blockers** and **7 P1 defects** that directly prevent real learners from completing the core end-to-end learning loop:

1. **P0 — Execution & Progress Persistence Missing (`Journey 8` FAIL):** `backend/src/execution/presentation/routers.py` only exposes `GET /api/v1/execution/status`; `backend/src/execution/application/use_cases/` is empty. Frontend `/workspace` (`WorkspaceComponent`) starts a hardcoded `'session-demo-01'` / `'task-demo-01'` Pomodoro timer whose 60s heartbeat hits `POST /api/v1/sessions/session-demo-01/heartbeat` (`404 Not Found`), while `/tasks`, `/schedule`, and `/analytics` remain disconnected empty stubs even after an `OfficialSchedule` is applied.
2. **P0 — Live Task Decomposition Reliability & Silent UI Failure (`Journey 3 & 11` FAIL):** Across 6 live CofHub-backed `PROPOSALS_GENERATE_JOBS` runs, only **2 / 6 (33.3%)** completed end-to-end (`UAT-07` after M4 retry, `UAT-08`); **4 / 6 (66.7%)** failed with `TimeoutError` (`>26s` + `>29s` on retry in 1 of 4–5 parallel milestones). Worse, `proposal_generation_use_cases.py` emits SSE `failed` with `"error": ""` (`str(TimeoutError()) == ""`), and `RoadmapService.handleSseChunk` evaluates `"" ?? evt.message ?? ...` -> `""`, hiding the error banner so the learner is left staring at an empty Step 3 screen with no failure feedback.

---

## 2. Phase 1 — Staging Readiness Audit

| Check | Target / Command | Observed Result | Status / Risk |
|---|---|---|---|
| Containers | `docker ps` | `focusflow-postgres` (healthy `:5432`), `focusflow-redis` (healthy `:6379`), `focusflow-backend` (restarted `:8000`), `focusflow-frontend` (`:3000`) | **PASS** |
| DB Schema & Head | `docker exec focusflow-backend alembic current` | `0013_ai_usage_audit_jsonb (head)`; all 35 tables present | **PASS** |
| Redis & Checkpoints | `RedisMilestoneCheckpointStore` + `redis-cli INFO keyspace` | `ping=True`, `redis_rw=ok`, `PONG`, `db0:keys=895,expires=894` (pre-UAT) | **PASS** |
| Taskiq Worker & Scheduler | `docker logs focusflow-backend` | `worker-0`, `worker-1`, `scheduler` executing `relay_pending_outbox_events`, `sweep_expired_ai_quota_reservations`, `poll_planning_outbox_events`, `sweep_abandoned_study_sessions` | **PASS** |
| CofHub Gateway & Routing | `GET /api/health?probe_ai=true` via `:8000` & `:3000` | `HTTP 200`; `actual_model_id: "gemini-3.8-flash-low"`, `low_model_thinking_tokens: 0`, `mismatches: []`; configured `llm_model_{low,medium,high}` verified *(Note: startup background probe at `03:52:17Z` logged transient `cobhub_capability_probe_failed` `TimeoutError` before on-demand probe passed)* | **PASS (with startup probe warning)** |
| Feature Flags & Env Isolation | Runtime settings inside `focusflow-backend` | `DECOMPOSER_ARCHITECTURE_MODE=milestone_scoped`, `LLM_PROVIDER=gemini`, `LLM_THINKING_CONTROL=model_suffix`, `CALENDAR_PROVIDER=google`, `PAYMENT_PROVIDER=mock`, `GOOGLE_CLIENT_ID/SECRET` set, `CALENDAR_ENCRYPTION_KEY` set | **RISK (P1/P2):** `ENVIRONMENT=development`, `DEBUG=True`, `FERNET_KEY` unset, `EMBEDDING_API_KEY` unset (`False`), `CALENDAR_WEBHOOK_BASE_URL=http://localhost:3000` |
| Mail & Personal Data Safety | DB audit & `docker-compose.yml` | Mailpit (`:8025`) not deployed in Compose; 426 synthetic test users untouched; 2 existing `calendar_connections` (`vut210225@gmail.com`, `hukhe23@gmail.com`) treated as personal and **never modified** | **PASS (Safe Isolation)** |

---

## 3. Phase 2 & 3 — Executed UAT Matrix & Evidence

All UAT runs used disposable `uat.*@focusflow.vn` accounts against the live Docker staging stack (`http://localhost:3000`, `http://localhost:8000`, PostgreSQL 16, Redis 7, CofHub). Screenshots are saved under `docs/evidence/staging_uat_screenshots/` (relative links below).

| Scenario ID | Area & Persona | Steps Performed | Expected vs Actual | HTTP / Trace / Latency / DB Checks | Visual / DOM Evidence | Status |
|---|---|---|---|---|---|---|
| **UAT-01** | Auth & `MODE_A` Availability (Beginner) | Register (`201`), UI `/sign-in` -> `/dashboard` -> `/availability` `MODE_A` preset (`13.5h/wk`), save, F5 reload (`availability.spec.ts` + live UI suite) | Persists across PostgreSQL reload and `/schedule` quick drawer isolation | `POST /api/v1/auth/register` `201`, `PUT /api/v1/availabilities/me` `200`; existing `availability.spec.ts` `2/2 PASS` | [01_dashboard_empty.png](../evidence/staging_uat_screenshots/01_dashboard_empty.png), [02_availability_mode_a.png](../evidence/staging_uat_screenshots/02_availability_mode_a.png) | **PASS** |
| **UAT-02** | Onboarding Modal & Clarify Skip | Navigate `/roadmaps/new` without availability -> modal Busy Pro -> Goal create -> `clarify-skip` | Modal auto-saves `MODE_A`; Skip unlocks Step 2 with `unresolved_assumptions` | `e2e_full_workflow.spec.ts` Test 2: `1/1 PASS` (`15.5s`) | Verified via Playwright | **PASS** |
| **UAT-03** | Goal Intake & Multi-turn Clarification (Beginner Python/FastAPI) | Create Goal (`BEGINNER`, 28 days) -> `clarify-questions` -> `clarify-answers` (Round 1 -> Round 2 `WAITING_FOLLOW_UP` or Step 2) | **Actual:** Multi-turn Round 1->2 works at API level, **but** UI button label unconditionally reads `"Xác nhận câu trả lời & Sang bước Cột mốc"` even when Round 2 stays on Step 1 (broke `e2e_full_workflow.spec.ts` Test 1) | `clarify_questions` `1360 in / 817 out`; UI flow advanced after 1 round in `staging_uat_ui` | [03_goal_intake_form.png](../evidence/staging_uat_screenshots/03_goal_intake_form.png), [04_clarification_round_1.png](../evidence/staging_uat_screenshots/04_clarification_round_1.png) | **PASS (with P2 UX defect)** |
| **UAT-03B** | Knowledge RAG Ingestion Probe | `POST /api/v1/planning/goals/{goal_id}/knowledge-sources/files` (`notes.txt`) | Accepted (`202`), worker failed cleanly with `AI_EMBEDDING_PROVIDER_NOT_CONFIGURED: Missing valid EMBEDDING_API_KEY` | `202` -> `ingestion_status="FAILED"`, `chunk_count=0` | DB/API verified | **BLOCKED** (Missing `EMBEDDING_API_KEY`) |
| **UAT-04** | Milestone Gen SSE, Edit & Approval (`UC-07`) | Trigger `milestones/generate-jobs` SSE -> approve `POST /milestones/approve` | Generates 4–5 milestones via SSE; approval unlocks Step 3 & updates DB `APPROVED` | `16.9s` (UI Run 1), `41.6s` (UI Run 2), `14.6s` (`UAT-07` corr `01a1ecd2-3eb5-7199-b880-7a03d7e638ac`) | [05_step2_ready_for_milestones.png](../evidence/staging_uat_screenshots/05_step2_ready_for_milestones.png), [06_milestones_generated.png](../evidence/staging_uat_screenshots/06_milestones_generated.png), [07_milestones_approved.png](../evidence/staging_uat_screenshots/07_milestones_approved.png) | **PASS** |
| **UAT-05** | Task Decomposition SSE + Resources + Apply UI (`UC-08/12`) | Click `Sinh Nhiệm Vụ bằng AI` on Step 3 in Beginner UI run (2 live runs) | **FAIL:** Both UI runs timed out (`M1` timed out twice at `26s+29s`) AND UI showed blank screen (`error: ""` swallowed by `??`) | Run 1 `res_id=01a1eccd-d36d-79b9-af54-51397e231012` (`RELEASED`); Run 2 `res_id=01a1ecdc-7bb1-70a2-949d-26a5e6a78cdf` (`M1:1, M1:2 TIMEOUT`); `error: ""` in Redis `sse:job:*:events` | `error-context.md` snapshot confirmed blank Step 3 | **FAIL (P0)** |
| **UAT-06** | Intermediate Persona E2E (`Apache Kafka Microservices`, 12h/wk, 28d) | Run 1 & Run 2 full API/SSE pipeline against live CofHub | **FAIL (2/2):** Milestones succeeded, Proposal SSE failed both times (`TimeoutError` on 1 of 5 parallel milestones twice in a row) | SSE terminal `failed`, `error_code: "SCHEDULE_PROPOSAL_GEN_FAILED"`, `error: ""` | `uat_backend_results.json` + container logs | **FAIL (P0)** |
| **UAT-07** | Advanced Persona E2E (`Kubernetes Operators & eBPF in Go`, 14h/wk, 28d) | Full API/SSE + `Apply` (`Idempotency-Key`) + post-Apply UI inspection across `/dashboard`, `/roadmaps/:id`, `/schedule`, `/tasks`, `/analytics`, `/workspace` | Backend E2E **PASSED** (`M4:1 TIMEOUT -> M4:2 RETRY SUCCESS`, 10 tasks / 840m, `FULL` schedule); **however** `learning_resources=[]` for all 10 tasks, `mobile 375px` overflowed horizontally, and `/dashboard` displayed UTC hours (`12:00-13:30`) | `clarify=9.4s`, `milestone_sse=14.6s`, `proposal_sse=39.2s`; `apply` `200` (`corr=01a1ecd3-1185-72fb-8fc7-c9f712a2410f`); DB `10 tasks` | [08_dashboard_active_roadmap.png](../evidence/staging_uat_screenshots/08_dashboard_active_roadmap.png), [09_roadmap_active_step4_timeline.png](../evidence/staging_uat_screenshots/09_roadmap_active_step4_timeline.png), [11_roadmap_mobile_375.png](../evidence/staging_uat_screenshots/11_roadmap_mobile_375.png) | **PASS (API) / UX & KB Gaps** |
| **UAT-08** | `FIT_CAPACITY` Explicit Approval & Deferred Scope (`PR-B`) | Tight capacity (`3h/wk`, 14d, Rust/Wasm/Raft) -> `FIT_CAPACITY` milestones -> try approve unconfirmed -> try stale version -> confirm valid version -> Proposal SSE | Kept 2 milestones (`Rust Ownership`, `Tokio+PG`), deferred 2 (`Wasm`, `Raft`); unconfirmed & stale both rejected `409 SCOPE_APPROVAL_REQUIRED`; deferred milestones stayed `PENDING` with `0` leaked tasks (`4 tasks` in Step 3); Playwright `fit_capacity_scope_approval.spec.ts` `1/1 PASS` | `roadmap_id=01a1ecd3-12f0-702d-b6bf-4c64e4fccb9c`, `scope_proposal_hash=sha256:efa9baaab...` | Playwright mocked UI verified (`2.4s`) | **PASS** |
| **UAT-09** | `MODE_B` Scheduling & Google Calendar Boundaries (`UC-17`) | 1) `POST /calendar/google/authorize`, `GET /status`, forged `/webhooks/google`; 2) `MODE_B` Tue/Thu 19-21h `proposals/manual` + Apply + Monday conflict test; 3) `availability.spec.ts` | Authorize `200` (`authorization_url` returned); invalid webhook rejected `403`; `MODE_B` applied (`200`, 0 slot violations); outside-slot Monday conflict rejected `422`. **Live Google OAuth consent & Cloud push webhook blocked** (`CALENDAR_WEBHOOK_BASE_URL=http://localhost:3000`, no staging test Google OAuth credentials) | `authorize=200`, `status=200`, `webhook=403`, `apply=200`, `conflict=422`; `availability.spec.ts` `2/2 PASS` | API & Playwright verified | **PASS (API/UI) / BLOCKED (Live Google OAuth & Webhook)** |
| **UAT-10** | Negative Apply Safety Gates (`PR-A`, `UC-12`) | Apply `2 x 60m` baseline -> shrink availability to `1.0h` Monday in 4d window -> `reoptimize-schedule` (`PARTIAL`, `1 unscheduled`) -> Apply without `confirm_partial_schedule` -> Apply with `true`; plus `SaveManualPlan` probe | Unconfirmed Apply rejected `409 PARTIAL_SCHEDULE_CONFIRMATION_REQUIRED`; confirmed Apply succeeded `200`. **Side-catch P1:** `SaveManualRoadmapPlanUseCase` drops `estimated_effort_minutes` (hardcodes default `60m`), breaking subsequent Apply (`422 MILESTONE_TASK_EFFORT_MISMATCH`) for manual plans >120m/milestone | `reoptimize=201` (`unscheduled_tasks_count=1`), `apply(false)=409`, `apply(true)=200` | API/DB verified | **PASS (Gates) / P1 Bug on Manual Save** |
| **UAT-11** | Study Sessions & Task Completion (`UC-11`, `/workspace`, `/tasks`, `/schedule`, `/analytics`) | Log in as active `UAT-07` learner -> inspect `/schedule`, `/tasks`, `/analytics`, `/workspace` -> click `Bắt đầu / Tiếp tục` | **FAIL (P0):** `/schedule`, `/tasks`, `/analytics` all render empty states despite active 10-task `OfficialSchedule` in Postgres; `/workspace` uses hardcoded `'session-demo-01'` and heartbeat targets missing `POST /api/v1/sessions/session-demo-01/heartbeat` (`404`); `execution/presentation/routers.py` has only `/status` | `GET /api/v1/execution/status` only; `UAT_SCHEDULE_HAS_EMPTY_STATE=true`, `UAT_TASKS_HAS_EMPTY_STATE=true`, `UAT_ANALYTICS_HAS_EMPTY_STATE=true` | [12_schedule_page_after_apply.png](../evidence/staging_uat_screenshots/12_schedule_page_after_apply.png), [13_tasks_page_after_apply.png](../evidence/staging_uat_screenshots/13_tasks_page_after_apply.png), [15_workspace_pomodoro_running.png](../evidence/staging_uat_screenshots/15_workspace_pomodoro_running.png) | **FAIL (P0)** |
| **UAT-12** | Overdue Recovery & Reoptimization (`UC-23/25`) | Backdate `UAT-07` task `01a1ecd3-111d-7791-906a-e21deee47015` in Postgres -> run `sweep_overdue_tasks_and_anti_loop` -> check DB & Outbox -> `POST /reoptimize-schedule` -> `Apply` -> `POST /overdue-revise-jobs` SSE | Task `scheduled_date` **preserved** (never auto-shifted); `OverdueTaskAlertEvent` written & `PUBLISHED` in `outbox_events`; `reoptimize-schedule` (`201`) & `Apply` (`200`) succeeded; `overdue-revise-jobs` SSE `completed` (`202`). *(Note: no FE UI button wired to trigger Overdue Recovery)* | `SWEPT:58`, `scheduled_date_not_auto_shifted=true`, `reoptimize=201`, `apply=200`, `overdue_revise=202 -> completed` | DB + SSE verified | **PASS (Backend) / FE UI Unwired** |
| **UAT-13** | Weekly Review & Evaluation Feedback (`UC-14..16/19`) | `GET /evaluation/dashboard-summary`, `POST /evaluation/weekly-reviews/generate-jobs`, `GET /evaluation/weekly-reviews/latest` | First generation `202` + `latest` `200` returned quantitative metrics (`overdue_tasks_count=1`) + Vietnamese qualitative feedback & action recommendations. **Side-catch P1:** calling `generate-jobs` a 2nd time for same `(roadmap_id, period_start, period_end)` crashes `500 IntegrityError (uq_ai_reviews_weekly)` | `dashboard-summary=200`, `weekly-review=202`, `latest=200`; duplicate period call -> unhandled `500` | API/DB/Logs verified | **PASS (1st call) / P1 Bug on Repeat Call** |
| **UAT-14** | SSE Interruption & Redis Checkpoint Resume | Disconnect Proposal/Milestone SSE after 1 event -> reconnect with `Last-Event-ID`; probe `RedisMilestoneCheckpointStore` live in container; run PostgreSQL fault-injection integration suite | SSE reconnected cleanly (`1 + 3` events -> `completed`); Redis probe `ping=True, loaded_ok=True, stale_is_none=True`; PG fault-injection suite proved M1–M3 skipped & zero duplicate tasks/quota on M4 timeout resume | `sse_reconnected_terminal="completed"`; `test_checkpoint_and_resume_fault_injection.py` + `test_durable_checkpoint_and_fault_injection.py`: `10 passed in 0.81s` | Live SSE + Redis + Pytest PG | **PASS** |
| **UAT-15** | Concurrency, Stale Proposal, Duplicates & Quota Safety | Concurrent `POST /apply` x2; concurrent `POST /milestones/generate-jobs` with identical `Idempotency-Key`; stale `Apply` on superseded `APPLIED` proposal; cross-user IDOR (`404`); wrong password (`401`); quota exhaustion (`429`) | IDOR `404`, wrong password `401`, no duplicate `official_schedules` (`1`) or `tasks` (`2`), `429 QUOTA_EXHAUSTED` blocked generation. **FAIL on 3 P1 safety checks:** (1) simultaneous `generate-jobs` with same `Idempotency-Key` bypassed lookup & created **2 distinct jobs** (`duplicate_generate_same_job_id=false`); (2) stale `Apply` on old `APPLIED` proposal without prior idempotency key returned **`200`** instead of `409`; (3) `QUOTA_EXHAUSTED` message printed **`"hiện còn -2 credit"`** | `idor=404`, `bad_login=401`, `concurrent_apply=[200, 200]`, `stale_apply=200`, `duplicate_same_job=false`, `quota_exhausted=429` | API + Postgres verified | **FAIL (3 P1 Defects)** |
| **UAT-16** | Existing Auth Playwright Suite (`auth.spec.ts`) | Run `auth.spec.ts` against `:3000` | **FAIL:** `/sign-up` rendered `<img alt="FocusFlow">` instead of `.brand-logo` (selector drift) AND Mailpit `:8025` is not deployed in Compose | `1 failed, 7 did not run` (`auth.spec.ts:75`) | Playwright trace (`auth-.../error-context.md`) | **FAIL (Suite Drift / Env)** |

---

## 4. Open Bugs Ranked P0 / P1 / P2

### P0 — Release Blockers (Must Fix Before Closed Beta)

1. **BUG-01 (P0): Execution Context Endpoints & Frontend Workspace/Tasks/Schedule/Analytics Unimplemented/Disconnected**
   - **Where:** `backend/src/execution/presentation/routers.py` (only `GET /status`), `backend/src/execution/application/use_cases/` (empty), `frontend/src/app/features/workspace/workspace.component.ts` (line 77), `frontend/src/app/core/services/workspace-session.service.ts` (line 138), `frontend/src/app/features/tasks/services/task.service.ts`, `frontend/src/app/features/schedule/services/schedule.service.ts`, `frontend/src/app/features/analytics/services/analytics.service.ts`.
   - **Evidence:** Live OpenAPI exposes zero `/api/v1/sessions/*` or `/api/v1/tasks/*` endpoints. `/workspace` hardcodes `'session-demo-01'` and `'task-demo-01'` and sends heartbeat to `404` (`/api/v1/sessions/session-demo-01/heartbeat`). Even with an applied 10-task roadmap (`UAT-07`), `/schedule`, `/tasks`, and `/analytics` show empty states (`[12]`, `[13]`, Playwright DOM assertions).
   - **Impact:** Learners cannot start/complete real Pomodoro study sessions, persist task completion, view their active schedule/task queue on dedicated pages, or see live analytics.

2. **BUG-02 (P0): High Failure Rate (66.7%) on Live Step 3 Task Decomposition SSE Due to CofHub Tail Stalls + Silent UI Error Swallowing**
   - **Where:** `backend/src/planning/application/services/milestone_scoped_decomposer.py` (line 1091, `min(..., 26.0)`), `backend/src/planning/application/use_cases/proposal_generation_use_cases.py` (lines 968–987), `frontend/src/app/features/roadmaps/services/roadmap.service.ts` (lines 1884–1888).
   - **Evidence:** **4 / 6** live Step 3 `PROPOSALS_GENERATE_JOBS` runs failed (`UAT-UI #1`, `UAT-UI #2`, `UAT-06 #1`, `UAT-06 #2`) when 1 of 4–5 parallel milestones hit `TimeoutError` on both attempt 1 (`26s`) and attempt 2 (`29s`). When that happens, `str(TimeoutError())` produces `"error": ""` in SSE event `#4` (`failed`) **before** `tasks.py` appends fallback event `#5`, closing `EventSource` early; then `roadmap.service.ts` evaluates `"" ?? evt.message ?? '...'` -> `""`, hiding `[data-testid="roadmap-error-alert"]` completely.
   - **Impact:** Users experience silent failure (blank Step 3 screen, no error or retry CTA) in two-thirds of live multi-milestone decompositions.

### P1 — High-Severity Correctness & Data Integrity Defects

3. **BUG-03 (P1): Race Condition on `Idempotency-Key` in `POST /milestones/generate-jobs` & `POST /proposals/generate-jobs`**
   - **Where:** `backend/src/planning/application/use_cases/milestone_use_cases.py` (lines 888–892) and `proposal_generation_use_cases.py` (lines 1041–1045).
   - **Evidence:** Two concurrent `POST /milestones/generate-jobs` requests with identical `Idempotency-Key` in `UAT-15` both passed `get_by_idempotency_key` (`None`), returned **different `job_id`s** (`duplicate_generate_same_job_id=false`), reserved **2 credits**, and executed **2 Taskiq jobs** concurrently.
   - **Impact:** Double-clicking or network retries can double-charge AI quota and trigger duplicate LLM pipelines.

4. **BUG-04 (P1): Stale/Superseded Proposal Apply Returns `200 OK` When Original Apply Lacked `Idempotency-Key`**
   - **Where:** `backend/src/planning/application/use_cases/proposal_management_use_cases.py` (lines 886–888, 1336–1340).
   - **Evidence:** In `UAT-15`, after applying `prop_id` (without `Idempotency-Key`) and creating a newer proposal (`M1 Safety v2`), re-calling `POST /proposals/{prop_id}/apply` returned `200 OK` instead of `409 Conflict` because `locked_applied_key is None` bypasses stale checks.

5. **BUG-05 (P1): Quota Calculation Double-Subtracts `reserved_calls` & Uses Process-Local Cache**
   - **Where:** `backend/src/account/infrastructure/orm/user_orm.py` (lines 136–143) and `backend/src/account/infrastructure/adapters/quota_facade_adapter.py` (lines 118–123, 144–154).
   - **Evidence:** `_get_credit_pool()` already computes `monthly_limit - used_calls - reserved_calls`, yet `reserve_quota` and `has_available_quota` subtract `reserved_calls` a second time, producing `"hiện còn -2 credit"` in `UAT-15` (`QUOTA_EXHAUSTED` `429`). Class-level `_credit_ledger_by_user` also risks stale quota reads across worker processes.

6. **BUG-06 (P1): `SaveManualRoadmapPlanUseCase` Drops `estimated_effort_minutes` on Manual Milestones**
   - **Where:** `backend/src/planning/application/use_cases/proposal_management_use_cases.py` (lines 1758–1769).
   - **Evidence:** Creating a manual plan via `POST /proposals/manual` with `"estimated_effort_minutes": 360` or `180` ignores the input and saves default `60m`; subsequent `POST /apply` fails `422 MILESTONE_TASK_EFFORT_MISMATCH` (`"25%..200% of milestone effort (60 minutes)"`).

7. **BUG-07 (P1): `POST /api/v1/evaluation/weekly-reviews/generate-jobs` Unhandled `500 IntegrityError` on Repeat Call in Same Period**
   - **Where:** `backend/src/evaluation/presentation/routers.py` / `intelligence.py` use case (`INSERT INTO ai_reviews`).
   - **Evidence:** Re-invoking `weekly-reviews/generate-jobs` for the same `(roadmap_id, period_start, period_end)` crashed ASGI with `UniqueViolationError: uq_ai_reviews_weekly` (`httpx.RemoteProtocolError` on client).

8. **BUG-08 (P1): Dashboard Calendar Displays UTC Hours (`12:00-13:30`) Instead of Local Timezone (`19:00-20:30+07:00`)**
   - **Where:** Dashboard calendar / `dashboard-summary` rendering (`[08_dashboard_active_roadmap.png](../evidence/staging_uat_screenshots/08_dashboard_active_roadmap.png)`).
   - **Evidence:** `UAT-07` scheduled blocks for `19:00-20:30+07:00` (evening preference), stored as `12:00-13:30+00` in Postgres, rendered visually as `12:00 - 13:30` in Dashboard.

9. **BUG-09 (P1): Environment & RAG/Calendar Readiness Gaps in Staging**
   - `ENVIRONMENT=development` & `DEBUG=True`; `EMBEDDING_API_KEY` unset (all uploaded RAG sources fail with `AI_EMBEDDING_PROVIDER_NOT_CONFIGURED`); `CALENDAR_WEBHOOK_BASE_URL=http://localhost:3000` (cannot receive Google Cloud push webhooks); `FERNET_KEY` unset (separate `CALENDAR_ENCRYPTION_KEY` is set).

### P2 — Medium / UX & UI Defects

10. **BUG-10 (P2): Roadmap Page Horizontal Overflow on `375px` Mobile + Narrow Hero Title Column + Fixed Footer Overlap**
    - **Evidence:** `UAT_METRIC roadmap_mobile_375_overflow=true` ([11_roadmap_mobile_375.png](../evidence/staging_uat_screenshots/11_roadmap_mobile_375.png)), Step 2/3 roadmap `h1` squeezed into ~120px column on desktop ([06_milestones_generated.png](../evidence/staging_uat_screenshots/06_milestones_generated.png), [07_milestones_approved.png](../evidence/staging_uat_screenshots/07_milestones_approved.png)), and fixed bottom footer (`app-footer.component.html`) overlaps content on scroll.
11. **BUG-11 (P2): Stale Footer Copy (`"Gemini 1.5 Pro via SSE"`)**
    - **Where:** `frontend/src/app/layout/main-layout/app-footer/app-footer.component.html:6`. System actually uses `gemini-3.8-flash-*`.
12. **BUG-12 (P2): Multi-Turn Clarification Button & Banner Copy Misleads Learner**
    - **Where:** `roadmap-page.component.html:605`, `roadmap.service.ts:1164`. When `status === 'WAITING_FOLLOW_UP'`, success banner says `"Đã lưu chẩn đoán mục tiêu thành công!"` and button still reads `"Xác nhận câu trả lời & Sang bước Cột mốc"` despite remaining on Step 1 for Round 2.
13. **BUG-13 (P2): Low Button Contrast on `/workspace` `"Tạm dừng"` + Unwired Overdue/Weekly-Review Triggers in FE + `auth.spec.ts` Selector Drift**
    - `[15_workspace_pomodoro_running.png](../evidence/staging_uat_screenshots/15_workspace_pomodoro_running.png)` shows dark text on medium grey `"Tạm dừng"` button; `WeeklyReview` (`evaluation`) and `Overdue Recovery` (`overdue-revise-jobs`) have no UI triggers; `auth.spec.ts` fails on `.brand-logo` & missing Mailpit.

---

## 5. Reliability, Latency & Token Telemetry Summary

Measured across the entire live UAT session (`2026-11-18T03:55:00Z+`) from `docker logs focusflow-backend` (`llm_latency_telemetry`) and PostgreSQL `ai_usage_logs`:

| Metric | Observed Value |
|---|---|
| CofHub Single-Call Latency (`n=74` completed calls logged) | `min = 1947.1 ms`, **`p50 = 6600.5 ms`**, **`p95 = 14955.9 ms`**, `max = 34108.2 ms` |
| End-to-End Stage Latency (Successful Personas) | Clarification: `9.4s` (`UAT-07`); Milestones SSE: `14.6s` (`UAT-07`), `16.9s` (`UI #1`), `41.6s` (`UI #2`); Task Decomp SSE (`UAT-07`): `39.2s` |
| Live Step 3 Proposal SSE Completion Rate | **2 / 6 (33.3%)** (`UAT-07`, `UAT-08` PASS; `UAT-UI #1`, `UAT-UI #2`, `UAT-06 #1`, `UAT-06 #2` FAIL due to double `TimeoutError`) |
| `ai_usage_logs` Totals During UAT | `GOAL_CLARIFICATION`: 8 `SUCCESS` (`10,609` in / `5,972` out, est. `$0.030353`); `MILESTONE_BREAKDOWN`: 38 `SUCCESS` (`149,806` in / `45,881` out, est. `$0.284413`) + **9 `TIMEOUT` (`UNKNOWN` usage)**; `ROADMAP_GENERATION`: 36 `SUCCESS` (`150,578` in / `7,078` out, est. `$0.139481`) + **5 `TIMEOUT` + 1 `FAILED` (`UNKNOWN` usage)** |
| Cost Accounting Completeness | Observed partial Google API reference est.: `$0.454247` (`actual_gateway_cost_usd`: **`UNVERIFIED`**; incomplete due to **15** `TIMEOUT`/`FAILED` attempts marked `UNKNOWN`) |

*Important DEF-17 Note:* Because 15 failed/timed-out attempts lacked upstream usage telemetry (`usage_completeness='UNKNOWN'`), total UAT spend is explicitly **partial**, never claimed as exact billed CofHub cost.

---

## 6. Phase 4 — Product & Pedagogical Quality Assessment

1. **Roadmap Relevance, Prerequisites & Task Actionability (`UAT-04`, `UAT-07`, `UAT-08`):**
   - **Strengths:** AI-generated milestones and tasks are domain-accurate, well-sequenced, and appropriately tailored to learner persona. For `UAT-07` (`ADVANCED` K8s Operators + eBPF in Go), tasks cover concrete topics (`client-go` Informers/WorkQueue, Kubebuilder OpenAPI validation markers, level-triggered idempotent Reconcile, OwnerReferences, Finalizers, `cilium/ebpf` `bpf2go`, BPF Ring Buffer, Chaos Capstone) with clear, measurable `completion_criteria` (e.g., Kind cluster CRD apply, log assertions, Prometheus `/metrics` verification). For `UAT-08` (`FIT_CAPACITY` 3h/wk Rust), scope reduction cleanly retained foundational Ownership & Tokio/SQLx and deferred WebAssembly & Raft.
2. **Learning Resources & URL Validity (Product Gap):**
   - **KB Seeded Concepts (`26` concepts):** FocusFlow's seeded Knowledge Base (`sqlalchemy_knowledge_base_repository.py`) maps Python/FastAPI/HTTP/SQL/DSA topics to valid external docs (`8/8` sampled URLs returned `HTTP 200`, e.g. `docs.python.org`, `fastapi.tiangolo.com`, `docs.sqlalchemy.org`, `owasp.org`).
   - **Out-of-Seed Domains (`UAT-07`, `UAT-08`):** Because `learning_quality.py` strips unverified URLs and returns `[]` whenever `learning_concepts` lacks a domain match, **10 / 10 tasks in `UAT-07` (`K8s/eBPF`) and the sampled `UAT-08` (`Rust`) tasks had `learning_resources = []`** (`"Chưa đính kèm tài liệu học tập"`). Unless the KB catalog is expanded or learners can ingest RAG sources (`EMBEDDING_API_KEY` currently unset), advanced/non-Python learners receive **zero curated study links**.
3. **Weekly Review Quality (`UAT-13`):**
   - Quantitative metrics (`adherence_rate_pct`, `overdue_tasks_count`, `completed_minutes`) aligned accurately with DB state, and qualitative feedback (`strengths`, `bottlenecks`, `actions`) was actionable and grounded without hallucinated metrics.
4. **UI/UX Friction Summary (Separated from Backend Bugs):**
   - Broken goal title wrapping on Step 2/3 (`[07_milestones_approved.png](../evidence/staging_uat_screenshots/07_milestones_approved.png)`), fixed footer overlap, stale `"Gemini 1.5 Pro via SSE"` label, `375px` mobile overflow, low-contrast `"Tạm dừng"` button, and misleading Round-2 clarification button text.

---

## 7. Required Corrections Before Closed Beta

1. **[P0] Implement & Wire Execution Bounded Context & Frontend Pages:** Expose `/api/v1/execution` (or `/sessions/start`, `/heartbeat`, `/finalize`, `/tasks/{id}/complete`) and connect `/workspace`, `/tasks`, `/schedule`, and `/analytics` to live backend APIs instead of local demo stubs.
2. **[P0] Fix Step 3 Proposal Reliability & Silent Error UI:** Investigate why CofHub parallel 4–5 milestone bursts hit double `TimeoutError` (`>26s`/`>29s`) 66.7% of the time (evaluate bounded gateway concurrency/client connection pooling or non-blocking checkpoint resume UX), ensure `proposal_generation_use_cases.py` / `tasks.py` never emit `error: ""` on `TimeoutError`, and change `roadmap.service.ts` to use `evt.error?.trim() || evt.message?.trim() || ...` so failures always surface in the UI with a Retry CTA.
3. **[P1] Fix Planning/Account Correctness Bugs:**
   - Make `Idempotency-Key` job deduplication atomic (`SET NX` / unique DB constraint) in `InitiateMilestoneGenUseCase` and `InitiateProposalGenUseCase`.
   - Reject stale `Apply` on superseded `APPLIED` proposals with `409` even when `applied_idempotency_key` is `None`.
   - Remove double subtraction of `reserved_calls` and process-local `_credit_ledger_by_user` cache in `quota_facade_adapter.py` / `user_orm.py`.
   - Preserve `estimated_effort_minutes` in `SaveManualRoadmapPlanUseCase`.
   - Handle duplicate-period `uq_ai_reviews_weekly` gracefully (`409` or idempotent return) in `GenerateWeeklyReviewUseCase`.
   - Convert `scheduled_start` / `scheduled_end` to learner local timezone (`UTC+7`) on Dashboard calendar cards.
4. **[P1] Staging Config & Content Readiness:** Set `ENVIRONMENT=staging`, `DEBUG=False`, configure valid `EMBEDDING_API_KEY` (unblocking RAG upload ingestion) and public HTTPS `CALENDAR_WEBHOOK_BASE_URL` (with dedicated staging Google test account), deploy Mailpit (or staging SMTP) for auth OTP E2E, and expand `learning_concepts` or safe resource discovery beyond the initial 26 Python/DSA concepts.
5. **[P2] UI Polish:** Fix Roadmap hero title wrapping, `375px` horizontal overflow, fixed footer overlap, `"Gemini 1.5 Pro"` footer copy, Round-2 clarification button copy, and wire Overdue Recovery + Weekly Review into UI.
