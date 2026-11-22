# 01 — Independent System Inventory (FocusFlow)

- **Audit Type**: Independent Product Reality Audit (Read-Only)
- **Baseline**: Branch `fix/p0-audit-remediation` @ `347066b` (working tree có thay đổi chưa commit từ các đợt remediation P0–P2B2B)
- **Verification Scope**: Tự quét độc lập toàn bộ `frontend/src/app`, `backend/src`, `backend/alembic`, `docs/database/`, `docs/srs/`, `docs/decisions/`, `docs/audits/fullstack-integration/`

---

## 1. Executive Inventory Summary (Code Reality vs Prior Docs)

| Hạng mục | `01-system-inventory.md` (cũ) | SRS v1.3 / `AGENTS.md` | **Thực tế mã nguồn (Independent)** | Trạng thái đồng bộ |
|---|---|---|---|---|
| **Frontend Route Files** | Không tách orphan | N/A | **11** file (9 active + **2 orphan** chưa mount) | Lệch (còn 2 file orphan) |
| **Frontend Components** | Không ghi rõ | N/A | **74** component (loại trừ `.spec.ts`) | Đã kiểm kê độc lập |
| **Frontend Services / Stores** | Không ghi rõ | N/A | **23** services (`12` core, `11` feature) + **3** Signal stores | Đã kiểm kê độc lập |
| **Backend FastAPI Routers** | 12+ | N/A | **14** routers trong **8** file + `main.py` | Đã kiểm kê độc lập |
| **Backend HTTP Endpoints** | **89** (lỗi thời) | N/A | **103 routes** trên **92 unique paths** (gồm `GET /api/v1/account/billing/config`) | **VERIFIED** (cập nhật hậu P1C) |
| **OpenAPI ↔ `schema.d.ts`** | Có drift trước P1B | Phải 0 drift | **92/92 paths khớp 100%** (`check-api-contract.sh` PASS) | **VERIFIED** |
| **SQLAlchemy ORM Tables** | 35 (mâu thuẫn nội bộ 36) | **35** bảng (12 account) | **36** bảng ứng dụng (13 `account` gồm `notifications`) | Đã đồng bộ vào `database-schema-design.md` v3.4 (SRS v1.3 chưa cập nhật) |
| **Alembic Migrations** | 0001..0015 | N/A | **15** migrations (`0015_add_notifications_table`), khớp 36/36 ORM | Khớp Postgres clean-migrate (36 + `alembic_version` = 37) |
| **`docs/database/schema.sql`** | Ghi nhận là blocker | Khớp Alembic | **36** bảng ứng dụng + `alembic_version` (37) + **26** triggers (`0014`/`0015`) | **SYNCED — 0 DRIFT** (`AUD-MED-10` RESOLVED) |
| **Taskiq Workers / Crons** | Không đủ chi tiết | N/A | **18** `@broker.task` (7 cron, 11 on-demand; gồm 1 no-op + 2 duplicate) | Còn nợ dọn dẹp P3 |
| **Backend Use Case Files** | Không liệt kê đủ | N/A | **39** file (`26` account, `8` planning, `2` execution, `3` evaluation) | Đã kiểm kê độc lập |
| **External Adapters** | Không phân biệt live/mock | Có mock offline | **21** file (Gemini live via Cobhub; Google Calendar live; **Payment chỉ có Mock**; **không có Mock LLM/Calendar**) | **DRIFT** với `AGENTS.md` (`AUD-MED-11`) |

---

## 2. Frontend Routes, Pages & Orphan Inventory

### 2.1 Active Routes (`frontend/src/app/app.routes.ts`)
- **Public**: `/`, `/how-it-works`, `/features`, `/pricing`, `/faq`
- **Auth (`AuthLayoutComponent`)**: `/sign-in`, `/sign-up`, `/forgot-password`, `/verify-otp` (kèm redirect `/otp-validation`, `/login`, `/register`, `/forgot-pass`, nhóm `/auth/*`, wildcard `**` → `/sign-in`)
- **Protected (`MainLayoutComponent`, `authGuard`)**:
  - `/dashboard`
  - `/roadmaps`, `/roadmaps/new`, `/roadmaps/:id`
  - `/workspace`
  - `/schedule`
  - `/availability`
  - `/tasks`
  - `/analytics`
  - `/profile`
  - `/settings` (`/settings/availability` → `/availability`)
  - `/admin` (`canActivate: [adminGuard]`)

### 2.2 Orphan / Dead Frontend Files (Confirmed Still Present)
- `frontend/src/app/features/auth/auth.routes.ts` (0 references) → import `LoginPageComponent` (`frontend/src/app/features/auth/components/login-page.component.ts`, orphan).
- `frontend/src/app/features/dashboard/dashboard.routes.ts` (0 references) & `frontend/src/app/features/dashboard/components/dashboard-page.component.ts` (0 references).
- 1-line re-export facades: `frontend/src/app/features/roadmaps/roadmap.service.ts:1`, `frontend/src/app/features/roadmaps/components/roadmap-page.component.ts:1`.
- **Broken Mock Billing Route**: `backend/src/account/infrastructure/adapters/payment_provider_adapter.py:48-51` trả về `checkout_url = "{frontend_base}/billing/mock-checkout?..."`, nhưng route `/billing/mock-checkout` **không tồn tại** trong `app.routes.ts` (rơi vào `**` → `/sign-in`).

---

## 3. Page–API–Service–Database Matrix (Independent)

| Feature / Page | Route | Frontend Service / Store | Backend Router & Endpoints | Database Tables |
|---|---|---|---|---|
| **Auth / Onboarding** | `/sign-in`, `/sign-up`, `/verify-otp`, `/forgot-password` | `AuthService` (`api.constant.ts`) | `auth_router.py` (12): `/auth/login`, `/google`, `/register`, `/register/{request,resend,verify}-otp`, `/password-reset/{request-otp,verify-otp,confirm}`, `/refresh`, `/me`, `/logout` | `users`, `user_profiles`, `learner_profiles`, `ai_quotas` (+ Redis OTP/refresh) |
| **Dashboard** | `/dashboard` | `DashboardService`, `RoadmapStore`, `NotificationService` | `evaluation/routers.py`: `GET /evaluation/dashboard-summary`; `execution/routers.py`: `GET /sessions/today-focus`; `account/routers.py`: `GET /account/notifications` | `tasks`, `study_sessions`, `roadmaps`, `notifications`, `learner_profiles` |
| **Roadmaps & AI Planning** | `/roadmaps`, `/roadmaps/new`, `/roadmaps/:id` | `RoadmapService`, `RoadmapStore`, `RoadmapPlanningStore`, `AiSseService` | `planning/routers.py` (27): `POST/GET/PATCH /roadmaps*`, `archive/pause/resume`, `clarify-*`, `milestones/{generate-jobs,PUT,approve}`, `proposals/{generate-jobs,current,PUT,manual,apply}`, `reoptimize-schedule`, `overdue-revise-jobs`, `jobs/{id}/stream`, `knowledge-sources/{files,urls}` | `learning_goals`, `roadmaps`, `milestones`, `learning_concepts`, `schedule_proposals`, `schedule_blocks`, `knowledge_sources`, `knowledge_chunks`, `workflow_runs`, `workflow_step_executions`, `ai_quota_reservations`, `ai_usage_logs`, `outbox_events` |
| **Study Workspace** | `/workspace` | `WorkspaceSessionService`, `WorkspaceStudioStore`, `AmbientAudioService` | `execution/routers.py` (13 session endpoints): `/sessions/{today-focus,active,start,heartbeat,finalize,resolve-takeaway,studio-config,notes*}`, `POST /tasks/{id}/complete` | `study_sessions`, `study_notes`, `tasks`, `schedule_blocks`, `outbox_events` |
| **Tasks & Backlog** | `/tasks` | `TasksService`, `EntityInvalidationService` | `execution/routers.py` (11 task endpoints): `GET/POST /tasks`, `GET /tasks/backlog`, `PATCH/DELETE /tasks/{id}`, `complete`, `reopen`, `reschedule`, `dependencies` | `tasks`, `task_dependencies`, `schedule_blocks`, `pause_records` |
| **Schedule & Calendar** | `/schedule`, `/availability` | `ScheduleService`, `AvailabilityService`, `CalendarIntegrationService` | `execution/routers.py`: `GET /tasks/schedule/week`; `account/routers.py`: `GET/PUT /availabilities/me`; `calendar_router.py` (9): `/account/calendar/*`, `/feeds/{token}.ics`; `webhook_router.py`: `POST /calendar/webhooks/google` | `user_availabilities`, `schedule_blocks`, `tasks`, `calendar_connections`, `webcal_tokens`, `outbox_events` |
| **Prove Mode & Analytics** | `/roadmaps/:id` (dialog), `/analytics` | `ProveModeService`, `AnalyticsService` | `evaluation/routers.py` (9): `/milestones/{id}/proofs/{latest,generate-jobs,submit}`, `/weekly-reviews/{generate-jobs,latest}`, `/analytics/{summary,weekly}` | `milestone_proofs`, `weekly_reviews`, `learner_memory_items`, `learner_concept_masteries`, `study_sessions`, `tasks` |
| **Profile & Learner Memory** | `/profile` | `ProfileService` | `account/routers.py`: `GET/PATCH /account/profile`, `GET /account/learner-memory`, `PATCH /learner-memory/{id}`, `POST /learner-memory/reset` | `users`, `user_profiles`, `learner_profiles`, `learner_memory_items`, `learner_concept_masteries` |
| **Settings & Billing** | `/settings`, `/pricing` | `SettingsService`, `BillingService`, `NotificationService` | `account/routers.py`: `/account/{export,quota,change-password,notifications*}`; `billing_router.py` (5): `/account/billing/{config,checkout,transactions,webhook,mock-confirm/{id}}` | `users`, `ai_quotas`, `payment_transactions`, `notifications` |
| **Admin** | `/admin` | `AdminService` (`adminGuard`) | `account/routers.py`: `GET /account/admin/status` | `users` (role=`ADMIN`) |

---

## 4. Background Workers & Scheduled Jobs (18 Tasks)

| File | Task Name | Schedule / Trigger | Reality Status |
|---|---|---|---|
| `shared_kernel/infrastructure/outbox/relay.py:47` | `relay_pending_outbox_events` | Cron `* * * * *` | **REAL** (nhưng có lỗi silent drop & aborted session — `AUD-HIGH-07`) |
| `account/presentation/tasks.py:13` | `sweep_expired_ai_quota_reservations` | Cron `* * * * *` | **REAL** |
| `account/presentation/tasks.py:36` | `aggregate_learner_srl_profile` | Outbox event | **REAL** (verified live in `processed_events`) |
| `account/presentation/tasks.py:89` | `send_otp_email_task` | On-demand | **REAL** (có fallback SMTP trực tiếp) |
| `account/presentation/tasks.py:110` | `sync_schedule_blocks_to_google` | Outbox event | **REAL** (verified live in `processed_events`) |
| `account/presentation/tasks.py:135` | `process_google_calendar_webhook` | Webhook | **REAL** |
| `account/presentation/tasks.py:160` | `renew_expiring_calendar_webhooks` | Cron `0 * * * *` | **REAL** |
| `account/presentation/tasks.py:182` | `reconcile_calendar_connections` | Cron `0 */6 * * *` | **REAL** |
| `account/presentation/tasks.py:198` | `send_overdue_task_alert_email_task` | Outbox event | **REAL** |
| `planning/presentation/tasks.py:59` | `execute_ai_roadmap_generation` | On-demand (SSE) | **REAL** (verified live với Gemini) |
| `planning/presentation/tasks.py:235` | `ingest_knowledge_source` | On-demand | **REAL** (cần `EMBEDDING_API_KEY`, hiện `false` ở staging) |
| `planning/presentation/tasks.py:317` | `consume_availability_updated_event` | Outbox event | **REAL** (verified live) |
| `planning/presentation/tasks.py:342` | `poll_planning_outbox_events` | Cron `* * * * *` | **REAL** |
| `execution/presentation/tasks.py:53` | `sweep_abandoned_study_sessions` | Cron `* * * * *` | **REAL** |
| `execution/presentation/tasks.py:165` | `sweep_overdue_tasks_and_anti_loop` | Cron `5 17 * * *` | **REAL** (không tự dời `scheduled_date`) |
| `execution/presentation/tasks.py:359` | `sync_external_google_calendar` | Unused | **NO-OP STUB** (`return None`, nợ P3) |
| `execution/presentation/tasks.py:365` | `sync_schedule_blocks_to_google` | Unused | **DUPLICATE** của task ở `account` (nợ P3) |
| `evaluation/presentation/tasks.py:10` | `sweep_overdue_tasks_and_anti_loop` | Unused | **DUPLICATE DELEGATOR** sang `execution` (nợ P3) |

---

## 5. Inventory Discrepancies & Uncaught Structural Gaps

1. **Cross-Context Raw SQL Violations Still Present (`AUD-MED-09`)**:
   - `backend/src/execution/infrastructure/adapters/schedule_sync_adapter.py:205` truy vấn trực tiếp bảng `learning_concepts` của `planning`.
   - `backend/src/execution/infrastructure/adapters/weekly_execution_metrics_adapter.py:30-42` truy vấn trực tiếp bảng `schedule_proposals` của `planning`.
   - Báo cáo P1B (`BE-ARCH-01` / `TASK-13`) đánh dấu `RESOLVED` nhưng chỉ dọn `execution/presentation/tasks.py`.
2. **Incomplete API Constants Consolidation (`AUD-LOW-05`)**:
   - Tồn tại song song `frontend/src/app/constant/api.constant.ts` (còn hardcode `GOOGLE_CLIENT_ID` tại dòng 19) và `frontend/src/app/core/constants/api-endpoints.ts` (10 hằng số không được gọi); 3 service (`calendar-integration`, `settings`, `profile`) vẫn hardcode đường dẫn `/api/v1/account/*`.
3. **Unused Knowledge-Source Read Endpoints (`AUD-LOW-05`)**:
   - `GET /api/v1/planning/goals/{goal_id}/knowledge-sources` (`planning/presentation/routers.py:537`) và `GET /api/v1/planning/knowledge-sources/{source_id}` (`:550`) chưa có caller phía frontend (`roadmap.service.ts` chỉ gọi upload/add URL).
4. **Gated / Unimplemented Features**:
   - **Account Deletion (GDPR Art. 17 / `FR-PROFILE-002`)**: `settings-page.component.ts:1533-1537` chủ động trả `return;` (honest gate); backend chưa có `DELETE /api/v1/account`.
   - **Live Payment Gateway**: Không có adapter cho SePay/VNPay/MoMo/Stripe; chỉ có `LocalMockPaymentAdapter` và mặc định `PAYMENT_PROVIDER=sepay` trả `503`.
5. **Documentation & Schema Drift (`AUD-MED-10` — RESOLVED for Schema/Design Docs)**:
   - `docs/database/schema.sql` đã được đồng bộ 0-drift từ `alembic upgrade head` (`0001`..`0015`): 36 bảng ứng dụng + `alembic_version` (37) + 26 triggers (`0014`/`0015`) + 66 explicit indexes.
   - `docs/database/database-schema-design.md` đã được nâng lên v3.4 (36 bảng, bổ sung bảng `notifications` vào `account`).
   - Ghi chú còn lại: `docs/decisions/` là thư mục chứa ADR (không phải `docs/adr/` như ghi trong `AGENTS.md`), và SRS v1.3 / `AGENTS.md` vẫn ghi 35 bảng (cần phê duyệt người dùng trước khi sửa SRS/AGENTS).
