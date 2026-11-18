# FocusFlow — Staging UAT Remediation Report

- **Ngày hoàn tất:** 2026-11-18
- **Môi trường kiểm chứng:** Docker Staging Stack (`docker-compose.yml` + `docker-compose.staging.yml`, `ENVIRONMENT=staging`, `DEBUG=False`, PostgreSQL 16 + pgvector, Redis 7, Mailpit `:1025/:8025`, Backend FastAPI + Taskiq `:8000`, Frontend Angular 21 `:3000`)
- **Model AI & Gateway:** Gemini 3.8 Flash (`gemini-3.8-flash-low` / `medium` / `high`) qua CofHub Gateway (`http://host.docker.internal:8045`) — không thay đổi production prompts, `prompts.lock`, hay routing.
- **Tài liệu đầu vào:** [`docs/reports/staging-uat-report.md`](staging-uat-report.md)
- **Kết luận phát hành (Verdict):** **CONDITIONAL GO cho Closed Beta** / **NO-GO cho Public Production** *(chi tiết điều kiện bắt buộc tại Mục 8)*.

---

## 1. Tóm tắt điều hành (Executive Summary)

Toàn bộ 4 gói khắc phục (**PR-1 .. PR-4**) cho các lỗi đã tái hiện trong Staging UAT (`BUG-01..BUG-13` và lỗ hổng Execution Context MVP) đã được triển khai, kiểm chứng bằng unit/integration tests và xác nhận lại trực tiếp trên môi trường Staging Docker thật (từ trình duyệt Playwright → Angular SPA → FastAPI/Taskiq → PostgreSQL 16 / Redis 7 / Mailpit / CofHub).

### Kết quả chính sau khắc phục

| Chỉ số / Hạng mục | Trước Remediation (`staging-uat-report.md`) | Sau Remediation (Live Staging) | Trạng thái |
|---|---|---|---|
| **Step 3 First-Attempt Completion Rate** (5 kịch bản live CofHub) | 2 / 5 (40%) | **5 / 5 (100%)** (`UAT-05R`, `UAT-06R` x2, `UAT-07R`, `UAT-08R`) | PASS |
| **CofHub Single-Call Latency** (`llm_latency_telemetry`, n=96 calls) | Không có pool / aiohttp hidden sleep | `min=1.58s`, **`p50=7.51s`**, **`p95=16.13s`**, `max=35.06s`, `retries>0: 0` | PASS |
| **Learning Resources Coverage & Live URL Reachability** | 0% ngoài 26 concept, fallback sai Python | **100% tasks có nguồn học đúng domain**, **12/12 URL trả HTTP `200 OK`** | PASS |
| **Execution End-to-End MVP** (`/workspace`, `/tasks`, `/schedule`, `/analytics`, `/dashboard`) | Không có router/UI thật (`session-demo-01`) | **17 endpoint mới**, OpenAPI sync `0 drift`, persistence qua reload + DB | PASS |
| **Transaction & Error Safety** (`BUG-02..05`, `BUG-07`) | Double quota, empty SSE error, stale apply 200 | Atomic Redis Lua idempotency, `409 PROPOSAL_SUPERSEDED`, non-negative quota, pre-LLM weekly review dedup | PASS |
| **Staging Isolation & UI Polish** (`BUG-09..13`) | `DEBUG=True`, `/docs` mở, 375px tràn, footer `fixed` | `ENVIRONMENT=staging`, `DEBUG=False`, `/docs=404`, `360 <= 375px`, footer static `Gemini 3.8 Flash via SSE` | PASS |
| **Phát hiện hạ tầng mới (`PG-COLL-01`)** | Chưa phát hiện | Phát hiện **PostgreSQL glibc collation drift** (`en_US.utf8` làm hỏng `learning_concepts_pkey` & `uq_users_email`) | Đã reindex 35/36 bảng; yêu cầu DB sạch trước Beta |

---

## 2. Chi tiết Remediation theo từng PR (PR-1 .. PR-4)

### PR-1 — Transaction Correctness & SSE Error Reporting (`BUG-02`, `BUG-03`, `BUG-04`, `BUG-05`, `BUG-07`)

- **Lỗi tái hiện:**
  - `BUG-02`: Khi Step 3 timeout, SSE trả payload lỗi rỗng/mơ hồ hoặc bắn `failed` trùng, UI nuốt message lỗi và không có CTA thử lại.
  - `BUG-03`: Hai request song song cùng `Idempotency-Key` vượt qua check-then-act, tạo 2 job và giữ 2 quota reservation.
  - `BUG-04`: `POST /proposals/{id}/apply` trên proposal `APPLIED` cũ đã bị superseded vẫn trả `200 OK` thay vì `409`.
  - `BUG-05`: `remaining_calls` bị trừ trùng `reserved_calls`, khiến thông báo hết hạn ngạch hiển thị số âm hoặc lệch `monthly_limit`.
  - `BUG-07`: Gọi song song `POST /evaluation/weekly-reviews` tạo bản ghi trùng hoặc lãng phí LLM call trước khi phát hiện trùng kỳ.
- **Nguyên nhân gốc (Root Cause):** Thiếu atomic slot claiming trong `SseJobStore`, thiếu đối chiếu proposal mới nhất dưới row lock trong `ApplyScheduleProposalUseCase`, trừ `reserved_calls` hai lần và cache `_credit_ledger_by_user` cũ trong `QuotaFacadeAdapter`, thiếu pre-LLM check & `ON CONFLICT DO NOTHING` trong `WeeklyReview`.
- **Thay đổi code chính:**
  - Backend:
    - [`planning_exceptions.py`](../../backend/src/planning/domain/exceptions/planning_exceptions.py), [`sse_job_port.py`](../../backend/src/planning/application/ports/sse_job_port.py), [`job_store.py`](../../backend/src/shared_kernel/infrastructure/sse/job_store.py): Atomic `claim_idempotency_slot` (`"PENDING:<token>"` qua Redis Lua `SET NX EX` & `asyncio.Lock`), CAS finalize/release, polling ngắn ~2s, mã lỗi `409 IDEMPOTENCY_REQUEST_IN_PROGRESS`.
    - [`milestone_use_cases.py`](../../backend/src/planning/application/use_cases/milestone_use_cases.py), [`proposal_generation_use_cases.py`](../../backend/src/planning/application/use_cases/proposal_generation_use_cases.py), [`tasks.py`](../../backend/src/planning/presentation/tasks.py), [`routers.py`](../../backend/src/planning/presentation/routers.py): `sanitize_sse_error_details(exc)` ánh xạ `AI_GATEWAY_TIMEOUT`, giải phóng `reservation_id` nếu lỗi trước khi vào pipeline, tránh bắn trùng event `failed`.
    - [`proposal_management_use_cases.py`](../../backend/src/planning/application/use_cases/proposal_management_use_cases.py): `_resolve_applied_proposal_idempotency` kiểm tra trước và sau `FOR UPDATE` để trả `409 PROPOSAL_SUPERSEDED` cho proposal cũ.
    - [`user_orm.py`](../../backend/src/account/infrastructure/orm/user_orm.py), [`quota_facade_adapter.py`](../../backend/src/account/infrastructure/adapters/quota_facade_adapter.py): Bỏ trừ kép `reserved_calls`, bỏ co `monthly_limit`, bỏ cache lệch khi chạy DB mode, clamp hiển thị remaining `>= 0`.
    - [`intelligence_repository.py`](../../backend/src/evaluation/infrastructure/repositories/intelligence_repository.py), [`intelligence.py`](../../backend/src/evaluation/application/use_cases/intelligence.py), [`routers.py`](../../backend/src/evaluation/presentation/routers.py): Pre-LLM `get_weekly_review_for_period` + `ON CONFLICT DO NOTHING` + xử lý `409` idempotent.
  - Frontend:
    - [`ai-sse.service.ts`](../../frontend/src/app/core/services/ai-sse.service.ts): `SseStreamError`, inactivity watchdog `90s`, giới hạn reconnect `3` lần, chuẩn hóa `pickNonEmpty`.
    - [`roadmap.service.ts`](../../frontend/src/app/features/roadmaps/services/roadmap.service.ts), [`roadmap-page.component.html`](../../frontend/src/app/features/roadmaps/components/roadmap-page/roadmap-page.component.html): Giữ `lastErrorCode`/`lastFailedStage`, nút CTA `Thử lại` (`roadmap-retry-ai-btn`), gửi `Idempotency-Key` khi apply, checkbox xác nhận `confirmWarnings` (`REVIEW_PENDING`/`NEEDS_REVIEW`) và `confirmPartialSchedule`.
- **Bằng chứng kiểm thử:**
  - Unit & PG/Redis concurrency tests: `test_pr1_transaction_and_sse_safety.py` + `test_pr1_postgres_redis_concurrency_e2e.py` (`13 passed`).
  - Live Staging API (`uat_remediation_results.json` -> `pr1_pr2_checks`):
    - `BUG-03`: 2 concurrent `POST /milestones/generate-jobs` cùng `Idempotency-Key` -> `statuses=[202, 202]`, `bug03_same_job_id=true`, `bug03_reservation_rows=1`.
    - `BUG-04`: Re-apply superseded proposal -> `status=409`, `code="PROPOSAL_SUPERSEDED"`.
    - `BUG-05`: Hết quota -> `status=429`, message `"Không đủ hạn ngạch AI: cần 1 credit, hiện còn 0 credit."` (không âm).
    - `BUG-07`: Gọi trùng Weekly Review -> `statuses=[202, 202]`, `bug07_same_review_id=true`.
    - `BUG-02` (UI live): Khi Milestone #6 timeout thực tế ở mốc 55s trong lần chạy Playwright `task-1653`, UI hiển thị rõ alert `Quá thời gian xử lý AI. Vui lòng thử lại hoặc tiếp tục từ checkpoint. (AI_GATEWAY_TIMEOUT)` kèm nút `Thử lại`.
- **Rủi ro còn lại:** Nếu 1 job đang chạy trên worker quá 2s khi client gửi lại cùng `Idempotency-Key`, client nhận `409 IDEMPOTENCY_REQUEST_IN_PROGRESS` (đúng thiết kế, client cần hiển thị trạng thái đang xử lý hoặc poll job).
- **Chiến lược Rollback:** Revert PR-1 theo từng commit (không thay đổi DB schema / migration); Redis key `PENDING:<token>` tự hết hạn theo TTL.
- **Kết quả chấp nhận:** **PASS**.

---

### PR-2 — Execution Context End-to-End MVP (`BUG-01`, Study Lifecycle, Tasks, Schedule, Analytics)

- **Lỗi tái hiện:**
  - Chưa có router FastAPI cho `/api/v1/tasks/*`, `/api/v1/sessions/*`, `/api/v1/analytics/*`.
  - Frontend `/workspace` hardcode `'session-demo-01'`, `/schedule` gọi endpoint hỏng `/api/v1/calendar/tokens/reset`, `/tasks` và `/analytics` không đồng bộ dữ liệu thật từ PostgreSQL.
  - Lỗi cột SQL trong `execution/presentation/tasks.py:86` (`status = 'COMPLETED'` thay vì `status_after_session = 'COMPLETED'`).
- **Thay đổi code chính:**
  - Backend:
    - [`planning/public_api.py`](../../backend/src/planning/public_api.py) & [`planning_execution_bridge.py`](../../backend/src/planning/infrastructure/adapters/planning_execution_bridge.py): `PlanningExecutionBridgePort` đảm bảo biên giới Hexagonal (`0 broken contracts` trong `import-linter`).
    - [`execution/infrastructure/orm/session_orm.py`](../../backend/src/execution/infrastructure/orm/session_orm.py), domain entities (`Task`, `StudySession`, `SessionTask`, `StudyNote`, `DailyCheckin`, `TakeawayGuard`, `BacklogPriorityRanker`), repositories (`SqlAlchemyTaskRepository`, `SqlAlchemyStudySessionRepository`), use cases, schemas và routers (`tasks_router`, `sessions_router`), cùng `analytics_router` trong `evaluation/` qua `ExecutionDashboardQueryPort`, gắn vào [`main.py`](../../backend/src/main.py).
    - Sửa lỗi SQL `status_after_session = 'COMPLETED'` trong [`execution/presentation/tasks.py`](../../backend/src/execution/presentation/tasks.py).
    - Regenerate OpenAPI types vào [`frontend/src/app/core/api/schema.d.ts`](../../frontend/src/app/core/api/schema.d.ts) (`17` endpoint mới; `scripts/check-api-contract.sh` xanh).
  - Frontend:
    - Nối thật [`workspace-session.service.ts`](../../frontend/src/app/core/services/workspace-session.service.ts), `/workspace`, `/tasks`, `/schedule`, `/analytics`, `/dashboard` theo kiểu từ `schema.d.ts` (`withCredentials: true`, standalone OnPush Signals, đầy đủ loading/empty/error states). Xóa toàn bộ `'session-demo-01'` và `/api/v1/calendar/tokens/reset`.
    - Sửa nhãn `Điểm tập trung TB` trên [`analytics-page.component.ts`](../../frontend/src/app/features/analytics/components/analytics-page.component.ts) từ `/ 5` thành `/ 100` (khớp thang điểm 0–100 từ backend).
- **Bằng chứng kiểm thử:**
  - Backend unit + integration (`tests/unit/execution/`, `tests/integration/execution/test_execution_e2e_postgres.py`, `tests/unit/evaluation/`): pass 100% (bao gồm IDOR `404`, concurrent session `409`, takeaway guard, DAG prerequisite check, outbox event).
  - Live Staging API & DB assertions (`uat_remediation_results.json` -> `pr2_bug07_bug08`):
    - `today_focus_status=200`, `tasks_count=13`, `schedule_week_items_count=3`, `concurrent_session_start_status=409`.
    - DB assertions sau phiên học: `db_task_status="COMPLETED"`, `db_schedule_block_status="COMPLETED"`, `db_study_notes_count=2`, `db_outbox_event="StudySessionCompletedEvent"`.
    - Analytics trả dữ liệu thật: `total_focused_hours=0.42`, `task_completion_rate=7.7%`, `plan_adherence_rate=100.0%`, `completed_tasks_count=1/13`, `active_streak_days=1`, `average_focus_score=80.0`.
  - Live Staging UI E2E (Playwright): Đăng nhập → Cấu hình lịch → Tạo Roadmap → Apply → Vào `/workspace` bấm Start → Ghi Scratchpad → Finalize với Key Takeaway → **Reload trang (`F5`)** → Xác nhận persisted ở `/tasks` (`1/19` Hoàn thành), `/schedule` (`Đã hoàn thành`, giờ địa phương `19:00–19:45`), `/analytics` (`5.3%`, `100%`, `80 / 100`, tạo AI Weekly Review thành công), `/dashboard` (`5.3%`, `1 ngày streak`, `1 phiên Pomodoro`).
- **Rủi ro còn lại:** Chưa có migration mới (tận dụng đúng 35 bảng hiện có theo SRS v1.3); với phiên học dưới 30 giây trong test tự động, làm tròn giờ hiển thị `0.0 giờ` trong khi phút hiển thị `1 phút học` (hành vi làm tròn bình thường).
- **Chiến lược Rollback:** Unmount `tasks_router`, `sessions_router`, `analytics_router` trong `main.py` và revert các slice FE về bản trước PR-2; không ảnh hưởng schema DB.
- **Kết quả chấp nhận:** **PASS**.

---

### PR-3 — Step 3 CofHub Reliability, Learning Resources & Bugfixes (`BUG-06`, `BUG-08`)

- **Lỗi tái hiện:**
  - Step 3 timeout 60% trên live CofHub (chỉ 2/5 pass trước remediation); `aiohttp` ẩn sleep 1–10s, AFC bật ngầm, cắt sớm 26s, `asyncio.gather` không `return_exceptions=True` hủy checkpoint các milestone thành công khác.
  - Tài nguyên học tập ngoài 26 concept bị rỗng hoặc fallback sai sang Python; URL không kiểm tra allowlist/reachability.
  - `BUG-06`: `SaveManualRoadmapPlanUseCase` làm rơi `estimated_effort_minutes` và metadata milestone.
  - `BUG-08`: Dashboard hiển thị giờ học dạng UTC (`12:00 - 13:00`) thay vì múi giờ người học (`19:00 - 20:00` `Asia/Ho_Chi_Minh`).
- **Thay đổi code chính:**
  - [`litellm_adapter.py`](../../backend/src/shared_kernel/infrastructure/external_ai/litellm_adapter.py), [`circuit_breaker.py`](../../backend/src/shared_kernel/infrastructure/external_ai/circuit_breaker.py), [`config.py`](../../backend/src/shared_kernel/config.py): Dùng pooled `httpx.AsyncClient(limits=Limits(max_connections=12, max_keepalive_connections=6), http2=False)`, tắt `automatic_function_calling` (`AFC`), giảm `ai_max_concurrent_llm_requests` (`8 -> 4`), thêm `ai_decomposer_max_concurrency=2` (không tăng timeout `36s`/`55s`).
  - [`milestone_scoped_decomposer.py`](../../backend/src/planning/application/services/milestone_scoped_decomposer.py), [`proposal_generation_use_cases.py`](../../backend/src/planning/application/use_cases/proposal_generation_use_cases.py): Bỏ cắt sớm `26s`, dùng `asyncio.gather(..., return_exceptions=True)` để bảo toàn Redis checkpoint của các milestone anh em, đóng owned `RedisMilestoneCheckpointStore` trong `finally:`, tăng cường fingerprint (gồm `clarification_context`, `start_date`, stage model).
  - [`sqlalchemy_knowledge_base_repository.py`](../../backend/src/planning/infrastructure/repositories/sqlalchemy_knowledge_base_repository.py), [`learning_resource_discovery.py`](../../backend/src/planning/application/services/learning_resource_discovery.py), [`harness_support.py`](../../backend/src/planning/application/services/harness_support.py), [`learning_quality.py`](../../backend/src/planning/domain/services/learning_quality.py): Sửa lệch `concept_id` Angular, bỏ fallback Python sai domain, mở rộng kho tài liệu chính thống (K8s, eBPF, Go, Rust, Kafka, Docker, AWS, System Design, ML/AI, React, Java/Spring, IELTS), ground nguồn `INDEXED` của learner, kiểm tra HTTPS allowlist + SSRF + `HEAD` check.
  - [`proposal_management_use_cases.py`](../../backend/src/planning/application/use_cases/proposal_management_use_cases.py) (`SaveManualRoadmapPlanUseCase`) + [`roadmap.service.ts`](../../frontend/src/app/features/roadmaps/services/roadmap.service.ts): Bảo toàn `estimated_effort_minutes` và milestone metadata (`BUG-06`).
  - [`execution_dashboard_adapter.py`](../../backend/src/execution/infrastructure/adapters/execution_dashboard_adapter.py), [`planning/public_api.py`](../../backend/src/planning/public_api.py), [`planning_dashboard_adapter.py`](../../backend/src/planning/infrastructure/adapters/planning_dashboard_adapter.py), [`dashboard_summary.py`](../../backend/src/evaluation/application/use_cases/dashboard_summary.py), [`roadmap-page.component.html`](../../frontend/src/app/features/roadmaps/components/roadmap-page/roadmap-page.component.html): Chuyển đổi giờ sang `user_tz` cho cả `Today Focus` VÀ lưới lịch tuần Dashboard (`BUG-08`).
- **Bằng chứng kiểm thử:**
  - Unit tests `test_pr3_reliability_resources_and_bugs.py` (`11 passed`, gồm test mới cho `PlanningDashboardAdapter.get_week_schedule_blocks`).
  - Live Staging 5 kịch bản CofHub: **5/5 pass Step 3 ngay attempt 1** (chi tiết Mục 4); **12/12 URL tài nguyên trả HTTP `200 OK`** (chi tiết Mục 5).
  - `BUG-06`: Apply manual plan 360 phút trả `200 OK`.
  - `BUG-08`: Live `dashboard-summary` trả `today_queue[0].scheduled_time = "19:00 - 20:00"` và `schedule_blocks[0].start_time = "19:00"`, `end_time = "19:45"` (xác nhận trực quan trên ảnh `09_dashboard_after_study.png`).
- **Rủi ro còn lại:** Với roadmap có 6 milestone khi CofHub bị tail latency >20s ở 1 subcall, tổng ngân sách 55s vẫn có thể chạm timeout (đã quan sát 1 lần ở Milestone #6 trong Playwright run #2; cơ chế checkpoint Redis + nút `Thử lại` cho phép resume sạch mà không mất M1–M5).
- **Chiến lược Rollback:** Revert PR-3 hoặc điều chỉnh biến môi trường `AI_DECOMPOSER_MAX_CONCURRENCY` / `AI_MAX_CONCURRENT_LLM_REQUESTS`; không đổi prompt/schema DB.
- **Kết quả chấp nhận:** **PASS**.

---

### PR-4 — Staging Environment Isolation, UI Polish (`BUG-09..13`) & Auth E2E

- **Lỗi tái hiện:**
  - `BUG-09`: Staging chạy `ENVIRONMENT=development`, `DEBUG=True`, mở công khai `/docs` & `/redoc`, không có readiness summary an toàn.
  - `BUG-10`: Mobile `375px` bị tràn ngang (ban đầu do Roadmap hero, và phát hiện thêm 3px tràn ngang `378px > 375px` từ `app-navbar` trong live Playwright run).
  - `BUG-11`: Footer đặt `position: fixed` đè nội dung dưới và ghi sai model cũ thay vì `Gemini 3.8 Flash via SSE`.
  - `BUG-12`: Copy Round-2 clarification gây hiểu nhầm.
  - `BUG-13`: Contrast nút trên `/workspace` không đạt chuẩn WCAG do thiếu biến CSS `--secondary-foreground`.
  - Auth Playwright `auth.spec.ts` lệch selector và không gửi OTP qua Mailpit thực.
- **Thay đổi code chính:**
  - [`docker-compose.yml`](../../docker-compose.yml), [`docker-compose.staging.yml`](../../docker-compose.staging.yml), [`.env.example`](../../.env.example), [`config.py`](../../backend/src/shared_kernel/config.py), [`main.py`](../../backend/src/main.py): Thêm service `focusflow-mailpit`, cấu hình `ENVIRONMENT=staging`, `DEBUG=False`, `EMAIL_HOST=mailpit`, tắt `/docs` & `/redoc` khi `debug=False`, thêm `staging_readiness_summary()` vào `/api/health`.
  - Sửa môi trường test bị nhiễm `SECRET_KEY` từ `litellm` (`load_dotenv()`) trong [`test_staging_config_and_health.py`](../../backend/tests/unit/shared_kernel/test_staging_config_and_health.py).
  - UI fixes: [`roadmap-page.component.scss`](../../frontend/src/app/features/roadmaps/components/roadmap-page/roadmap-page.component.scss), [`styles.scss`](../../frontend/src/styles.scss), [`main-layout.component.html`](../../frontend/src/app/layout/main-layout/main-layout.component.html), [`app-navbar.component.html`](../../frontend/src/app/layout/main-layout/app-navbar/app-navbar.component.html) (thu gọn padding/gap mobile cho 375px), [`app-footer.component.html`](../../frontend/src/app/layout/main-layout/app-footer/app-footer.component.html), [`ai-grill-me-dialog.component.html`](../../frontend/src/app/features/roadmaps/components/dialogs/ai-grill-me-dialog/ai-grill-me-dialog.component.html).
  - E2E specs: [`frontend/e2e/auth.spec.ts`](../../frontend/e2e/auth.spec.ts) & [`frontend/e2e/availability.spec.ts`](../../frontend/e2e/availability.spec.ts).
- **Bằng chứng kiểm thử:**
  - Live Staging health: `GET /api/health?probe_ai=true` trả `environment="staging"`, `debug=false`, `ai_gateway.status="ok"`, `missing_gateway_models=[]`; `GET /docs` trả `404`; Mailpit `:8025` trả `200`.
  - Playwright regression (`auth.spec.ts`, `availability.spec.ts`, `fit_capacity_scope_approval.spec.ts` trên `http://localhost:3000`): **11/11 PASS** (gồm 8/8 kịch bản OTP Mailpit thật, Argon2id login, forgot password, anti-brute-force khóa OTP).
  - Live mobile audit trên Step 3 (`375x812`): `scrollWidth=360 <= innerWidth=375` (`hasHorizontalOverflow=false`), `footerPosition="static"`, `footerText` chứa `"Gemini 3.8 Flash via SSE"`, `--primary: #005234`, `--secondary: #5f5e5e`, `--secondary-foreground: #ffffff` (contrast ratio 6.48:1).
- **Chiến lược Rollback:** Chạy lại `docker compose up -d` không kèm `docker-compose.staging.yml` hoặc revert commit CSS/template; không ảnh hưởng DB.
- **Kết quả chấp nhận:** **PASS**.

---

## 3. Ma trận Hồi quy Staging UAT (Regression Matrix)

| Mã UAT | Kịch bản kiểm thử | Bằng chứng / Trace ID / Kết quả quan sát | Kết quả |
|---|---|---|---|
| **UAT-01** | Auth OTP Mailpit, Login Argon2id, Logout, Auth Guard, Brute-force OTP | `e2e/auth.spec.ts` trên live Staging `:3000` + Mailpit `:8025` (`8/8 passed`) | **PASS** |
| **UAT-02** | Availability `MODE_A` + Reload PostgreSQL + Quick Drawer | `e2e/availability.spec.ts` (`2/2 passed`) + live UI E2E | **PASS** |
| **UAT-03B** | Availability `MODE_B`, `/google/authorize`, Forged Webhook Security | `availability.spec.ts` #10 (`Mode B <-> Mode A` reload PASS); `POST /account/calendar/google/authorize` = `200`; Forged `POST /calendar/webhooks/google` = `403`. *Live Google OAuth consent & Cloud push webhook chưa có domain HTTPS & tài khoản Google staging.* | **PARTIAL / EXTERNAL BLOCKED** |
| **UAT-04** | FIT_CAPACITY explicit approval & deferred scope | `e2e/fit_capacity_scope_approval.spec.ts` PASS + live `UAT-08R` (Rust/Wasm/Raft 3h/tuần, `roadmap_id=01a1ed2a-0468-7fb4-923a-d3dd570b2f4f`, `apply=200`) | **PASS** |
| **UAT-05R** | Beginner Python FastAPI & PostgreSQL (Step 1→4 + Apply) | `roadmap_id=01a1ed36-a7e2-7456-bcd0-59bed54b1400`, `proposal_id=01a1ed37-b96e-780d-b046-116dc1474364`, `18/18` tasks có tài nguyên, `judge_status=PASSED`, `apply=200` | **PASS** |
| **UAT-06R (T1/T2)** | Intermediate Apache Kafka Microservices (2 trials) | T1: `corr_proposal=01a1ed28-1142-7236-91c7-76e80a30d0e8`, `13/13` tasks có tài nguyên, `37.7s`; T2: `corr_proposal=01a1ed28-d3c3-7af5-93f1-71716593a0f2`, `10/10` tasks có tài nguyên, `26.8s` | **PASS** |
| **UAT-07R** | Advanced K8s Operators & eBPF in Go | `corr_proposal=01a1ed29-7a8c-7de2-9f6f-3292492ebc12`, `15/15` tasks có tài nguyên (K8s + Prometheus docs), `34.8s`, `apply=200` | **PASS** |
| **UAT-08R** | Tight Capacity Rust + Wasm + Raft (3h/wk, `FIT_CAPACITY`) | `corr_proposal=01a1ed2a-a5d8-79e3-be9a-330fc770aa74`, `12/12` tasks có tài nguyên (Rust Book/Std), `27.6s`, `apply=200` | **PASS** |
| **UAT-09** | Đổi Availability không reset Roadmap / Milestones | `before_status=ACTIVE -> after_status=ACTIVE`, `milestones: 6 -> 6` | **PASS** |
| **UAT-10** | Full UI Learner Journey: Workspace Pomodoro + Scratchpad + Takeaway + Reload + `/tasks` + `/schedule` + `/analytics` + `/dashboard` | Live Playwright (`uat.ui.rem.1794981846038@focusflow.vn`), 9 ảnh chụp xác minh, DB `COMPLETED` + `StudySessionCompletedEvent`, `0` lỗi API không mong đợi | **PASS** |
| **UAT-11** | PR-1 Idempotency, Superseded Apply, Quota Non-Negative, Weekly Review Dedup, Manual 360m (`BUG-03..07`) | `bug03_reservation_rows=1`, `bug04=409 PROPOSAL_SUPERSEDED`, `bug05=429 (0 credit)`, `bug06=200`, `bug07_same_review_id=true` | **PASS** |
| **UAT-12** | Overdue Task Recovery & Reschedule Budget | Quá hạn không bị tự dời `scheduled_date`; learner dời qua `POST /api/v1/tasks/{id}/reschedule` -> `200`, `reschedule_count=1`, `weekly_reschedule_used=1` | **PASS** |
| **UAT-14** | SSE Mid-Stream Disconnect & `Last-Event-ID` Replay + Redis Checkpoint | Ngắt kết nối sau `id: 1`, reconnect với `Last-Event-ID: 1` -> replay `4` events tới `completed`; Redis lưu `ff:checkpoint:milestone:*` | **PASS** |
| **UAT-15** | Live Google AI Studio RAG Ingestion (`EMBEDDING_API_KEY`) | `readiness.rag_embedding_configured=false` (chưa có `EMBEDDING_API_KEY` trong `.env` host; fail-closed được xác minh) | **BLOCKED (External Secret)** |

---

## 4. Độ tin cậy Step 3, Latency CofHub & Kiểm toán Quota / Token

### 4.1. Kết quả 5 kịch bản Live CofHub (Step 2 & Step 3)

| Kịch bản | Milestone SSE (ms) | Proposal SSE Attempt 1 (ms) | Attempt 1 Pass | Tasks có Resources | Used / Remaining Calls | Tokens Consumed | Judge Status |
|---|---:|---:|:---:|:---:|:---:|---:|---|
| **UAT-05R** (Beginner Python/FastAPI) | 17,777.2 | 52,303.9 *(gồm UAT-14 reconnect)* | YES | 18 / 18 (100%) | — *(rerun)* | — | `PASSED` |
| **UAT-06R Trial 1** (Kafka Intermediate) | 16,138.0 | 37,721.6 | YES | 13 / 13 (100%) | 2 / 28 (`reserved=0`) | 55,766 | `PASSED` |
| **UAT-06R Trial 2** (Kafka Intermediate) | 11,505.6 | 26,812.5 | YES | 10 / 10 (100%) | 2 / 28 (`reserved=0`) | 47,585 | `PASSED` |
| **UAT-07R** (Advanced K8s/eBPF Go) | 15,261.6 | 34,799.0 | YES | 15 / 15 (100%) | 2 / 28 (`reserved=0`) | 63,810 | `PASSED` |
| **UAT-08R** (FIT_CAPACITY Rust/Wasm) | 41,253.1 | 27,602.4 | YES | 12 / 12 (100%) | 2 / 28 (`reserved=0`) | 56,853 | `PASSED` |

> **Lưu ý minh bạch về lần chạy `UAT-05R` đầu tiên (`task-1426`) và Playwright run #2 (`task-1653`):**
> - Ở lần chạy đầu `task-1426`, Step 3 của `UAT-05R` **vẫn hoàn tất attempt 1** nhưng Tier 3 Pedagogical Judge timeout ở 12s (Fail-Open ADR-009 → `REVIEW_PENDING`), và `Apply` trả đúng `409 JUDGE_REVIEW_CONFIRMATION_REQUIRED` vì script test ban đầu quên gửi `confirm_warnings=True` cho `REVIEW_PENDING` (UI thật đã có checkbox `confirm-warnings-checkbox`).
> - Trong lần chạy lại `UAT-05R`, chúng tôi phát hiện sự cố hạ tầng `PG-COLL-01` (xem Mục 7), xử lý `REINDEX TABLE`, và rerun `UAT-05R` pass 100% (`judge_status=PASSED`, `apply=200`).
> - Trong Playwright run #2 (`task-1653`), Milestone #6 của lộ trình 6 chặng gặp timeout thực tế ở 55s từ CofHub — xác nhận trực tiếp UI hiển thị đúng `AI_GATEWAY_TIMEOUT` + CTA `Thử lại` (`BUG-02`) và Redis đã bảo toàn checkpoint `ff:checkpoint:milestone:*` cho M1–M5.

### 4.2. Phân phối Single-Call CofHub Latency (`llm_latency_telemetry`, 20 phút, `n = 96` calls)

- **Tổng số lệnh gọi quan sát:** `96` (`retries > 0`: `0`)
- **Min:** `1,584.65 ms` (`1.58s`)
- **p50:** `7,514.1 ms` (`7.51s`)
- **p95:** `16,134.7 ms` (`16.13s`)
- **Max:** `35,064.54 ms` (`35.06s`)

### 4.3. Kiểm toán Quota & Telemetry (`ai_usage_logs`)

- Mọi kịch bản hoàn tất 2 bước AI (Step 2 + Step 3) tiêu thụ chính xác `used_calls=2`, `reserved_calls=0`, `remaining_calls=28 / 30` (không leak reservation).
- Mọi lời gọi LLM thành công đều ghi `usage_source="GATEWAY_TELEMETRY"` với `prompt_tokens` và `completion_tokens` đầy đủ.
- Các subcall thất bại/timeout trung gian (`UAT-07R` 1 lần `ValueError`, `UAT-08R` 1 lần `TimeoutError` trước khi tự phục hồi) đều được ghi nhận độc lập trong `ai_usage_logs` với `usage_source="UNKNOWN"` (đúng DEF-17, không coi là 0 compute).

---

## 5. Kiểm chứng Nguồn Học tập (Learning Resources URL Reachability)

Toàn bộ **12/12** URL duy nhất được hệ thống sinh ra trên cả 5 kịch bản domain khác nhau (Python/FastAPI, Kafka/Distributed Systems, Kubernetes/Prometheus, Rust) đều vượt qua kiểm tra HTTP sống (`200 OK`):

| URL | HTTP Status | Kết quả |
|---|:---:|:---:|
| `https://doc.rust-lang.org/book/` | `200` | PASS |
| `https://doc.rust-lang.org/std/` | `200` | PASS |
| `https://docs.python.org/3/library/asyncio.html` | `200` | PASS |
| `https://docs.python.org/3/tutorial/introduction.html` | `200` | PASS |
| `https://kafka.apache.org/documentation/` | `200` | PASS |
| `https://kubernetes.io/docs/concepts/overview/` | `200` | PASS |
| `https://learn.microsoft.com/en-us/azure/architecture/patterns/` | `200` | PASS |
| `https://martinfowler.com/articles/patterns-of-distributed-systems/` | `200` | PASS |
| `https://prometheus.io/docs/introduction/overview/` | `200` | PASS |
| `https://realpython.com/defining-your-own-python-function/` | `200` | PASS |
| `https://www.oreilly.com/library/view/fluent-python-2nd/9781492056348/` | `200` | PASS |
| `https://www.youtube.com/watch?v=R-HLU9Fl5ug` | `200` | PASS |

---

## 6. Bằng chứng Giao diện (Live Staging Screenshots)

Toàn bộ ảnh chụp màn hình từ phiên kiểm thử Playwright trên Staging (`http://localhost:3000`, tài khoản `uat.ui.rem.1794981846038@focusflow.vn`) được lưu tại [`docs/evidence/staging_uat_remediation_screenshots/`](../evidence/staging_uat_remediation_screenshots/) và đã được kiểm tra trực quan:

- [`01_step2_milestones.png`](../evidence/staging_uat_remediation_screenshots/01_step2_milestones.png) — Step 2 Milestones sau SSE completion.
- [`02_step3_tasks_resources.png`](../evidence/staging_uat_remediation_screenshots/02_step3_tasks_resources.png) — Step 3 phân rã nhiệm vụ (16–19 tasks) & nguồn học tập hiển thị đầy đủ (`19` panel, `26` resource items).
- [`03_mobile_375_roadmap.png`](../evidence/staging_uat_remediation_screenshots/03_mobile_375_roadmap.png) — Viewport mobile `375x812`: `scrollWidth=360 <= 375`, `0` tràn ngang (cả navbar và Roadmap).
- [`04_step4_applied_schedule.png`](../evidence/staging_uat_remediation_screenshots/04_step4_applied_schedule.png) — Step 4 Official Schedule đã Apply (`ACTIVE`), footer `Gemini 3.8 Flash via SSE` tĩnh không đè nội dung.
- [`05_workspace_finalized.png`](../evidence/staging_uat_remediation_screenshots/05_workspace_finalized.png) — `/workspace` sau khi hoàn tất phiên học với Key Takeaway và độ tương phản nút chuẩn WCAG.
- [`06_tasks_completed.png`](../evidence/staging_uat_remediation_screenshots/06_tasks_completed.png) — `/tasks` sau reload: tab `Đã hoàn thành (1)` persisted từ PostgreSQL kèm nhãn tài liệu học.
- [`07_schedule_week.png`](../evidence/staging_uat_remediation_screenshots/07_schedule_week.png) — `/schedule`: lịch tuần hiển thị đúng giờ địa phương `19:00 – 19:45` (`Đã hoàn thành`) và `19:30 – 20:30` (`PLANNED`).
- [`08_analytics_review.png`](../evidence/staging_uat_remediation_screenshots/08_analytics_review.png) — `/analytics`: `5.3%` (`1/19`), `100%` Adherence, `Điểm tập trung TB: 80 / 100`, phân bổ ngày và AI Weekly Review sinh thật.
- [`09_dashboard_after_study.png`](../evidence/staging_uat_remediation_screenshots/09_dashboard_after_study.png) — `/dashboard`: cả lưới lịch tuần (`19:00–19:45`) lẫn `Hàng đợi Trọng tâm Hôm nay` (`19:00 - 19:30`) đều khớp múi giờ `Asia/Ho_Chi_Minh`, `5.3%` tiến độ, `1 ngày` chuỗi, `1 phiên` Pomodoro.

---

## 7. Kết quả Quality Gates & Phát hiện Hạ tầng (`PG-COLL-01`)

### 7.1. Quality Gates cuối (sau mọi chỉnh sửa)

| Cổng kiểm tra | Lệnh thực thi | Kết quả |
|---|---|---|
| Backend Lint & Format | `ruff check . && ruff format --check .` | **PASS** (`405 files already formatted`) |
| Backend Type Check | `mypy --strict src` | **PASS** (`0 issues in 297 source files`) |
| Hexagonal / Context Boundaries | `lint-imports` | **PASS** (`Contracts: 5 kept, 0 broken`) |
| API Contract Sync | `bash scripts/check-api-contract.sh` | **PASS** (`0 drift`) |
| Backend Unit + Integration | `REDIS_URL=redis://localhost:6379/0 pytest -q -m "not live_cobhub and not live_embedding"` + isolated rerun `test_execution_e2e_postgres.py` & `test_auth.py`/`test_otp_auth.py` (`Redis DB 1`) | **718 passed** (chạy chung, gồm `test_auth`/`test_otp_auth`) + `test_execution_e2e_postgres.py` **`1 passed`** (in-process, tách khỏi Staging worker ở Redis DB 0) — **tổng 719/719 passed, 0 failed, 3 deselected (live markers)** |
| Frontend Lint & Unit Tests | `npx ng lint && pnpm exec ng test --watch=false` | **PASS** (`59/59` files, `446/446` tests) |
| Frontend Production Build | `npx ng build --configuration production` | **PASS** (`Initial total: 799.00 kB / 173.40 kB gzip`) |
| Playwright Staging Regression | `PLAYWRIGHT_BASE_URL=http://localhost:3000 pnpm exec playwright test e2e/auth.spec.ts e2e/availability.spec.ts e2e/fit_capacity_scope_approval.spec.ts` | **PASS** (`11/11`) |

*(Lưu ý kỹ thuật khi chạy `test_execution_e2e_postgres.py` trên máy host cùng lúc Docker Staging đang chạy: vì container `focusflow-backend` tiêu thụ Redis DB 0, chạy host pytest với `REDIS_URL=redis://localhost:6379/0` khiến worker Docker lấy mất job và gọi CofHub thật thay vì `StubLLMAdapter`; chạy test auth trên Redis DB 1 và execution test ở chế độ in-process/CI sạch pass 100%.)*

### 7.2. Phát hiện hạ tầng quan trọng — `PG-COLL-01` (PostgreSQL glibc Collation Drift)

- **Triệu chứng:** Trong lần chạy lại `UAT-05R`, `POST /apply` ném `500 ForeignKeyViolationError` cho `fk_tasks_concept` (`Key (concept_id)=(sqlalchemy-async-alembic) is not present in table "learning_concepts"`), dù dòng đó **thực sự tồn tại** khi quét tuần tự (`enable_indexscan = off` trả `1`, `indexscan = on` trả `0`).
- **Nguyên nhân:** Volume Docker PostgreSQL 16 hiện tại có `datcollate='en_US.utf8'` với `datcollversion=NULL` so với glibc thực tế `2.36` trong image `pgvector/pgvector:pg16`, làm hỏng thứ tự btree index cho cột text/varchar.
- **Xử lý hiện tại trên Staging:** Đã chạy `REINDEX TABLE` thành công cho **35/36 bảng** non-`users` (`learning_concepts_pkey` hoạt động bình thường trở lại). Riêng bảng `users` có 1 bản ghi email test trùng lịch sử (`learner_334704e9@focusflow.vn`) từng lọt qua `uq_users_email` khi index hỏng — **chưa xóa** để tuân thủ quy tắc an toàn dữ liệu.
- **Hành động bắt buộc trước Closed Beta:** Khởi tạo volume PostgreSQL mới sạch cho môi trường Beta (ưu tiên `LC_COLLATE=C.UTF-8` hoặc ICU collation) hoặc dọn bản ghi test trùng và chạy `REINDEX DATABASE` + `ALTER DATABASE ... REFRESH COLLATION VERSION`.

---

## 8. Kết luận cuối cùng — Closed Beta GO / NO-GO

### Phán quyết: **CONDITIONAL GO cho Closed Beta** | **NO-GO cho Public Production**

- **Lý do đạt CONDITIONAL GO cho Closed Beta:**
  - Toàn bộ hành trình cốt lõi của người học (Auth OTP → Availability → AI Roadmap 4 bước → Tài nguyên học tập kiểm chứng → Apply Schedule → Học tập Pomodoro/Scratchpad/Takeaway → Persistence sau Reload → `/tasks` → `/schedule` → Overdue Recovery → `/analytics` + Weekly Review → `/dashboard`) đã hoạt động thông suốt end-to-end trên Staging Docker thật với độ tin cậy Step 3 đạt **100% (5/5)** attempt 1 và **12/12** URL tài nguyên sống.
  - Toàn bộ 13 lỗi UAT (`BUG-01..BUG-13`) và các cổng chất lượng kỹ thuật (lint, strict mypy, import-linter, OpenAPI contract, unit/integration/Playwright) đều xanh.
- **Các điều kiện bắt buộc trước khi gửi lời mời Closed Beta (Pre-flight Checklist):**
  1. **PostgreSQL sạch cho Beta (`PG-COLL-01`):** Provision database volume mới (hoặc deduplicate email test `learner_334704e9@focusflow.vn` + `REINDEX DATABASE`) và xác nhận `datcollversion` khớp glibc hiện tại.
  2. **Secret Rotation:** Thiết lập `SECRET_KEY`, `FERNET_KEY` riêng cho Beta (không dùng giá trị mẫu) và xác nhận `/api/health` báo `secret_key_is_default: false`, `debug: false`.
  3. **Quyết định phạm vi 2 tích hợp ngoài đang `BLOCKED`:**
     - **RAG Ingestion (`EMBEDDING_API_KEY`):** Nếu Closed Beta cần tải PDF/URL tài liệu riêng, bắt buộc nạp `EMBEDDING_API_KEY` (Google AI Studio) và kiểm thử 1 tài liệu thật; nếu không, giữ tính năng ở trạng thái fail-closed / ẩn khỏi phạm vi Beta.
     - **Google Calendar Live Push (`CALENDAR_WEBHOOK_BASE_URL`):** Cần domain HTTPS công khai + cấu hình OAuth consent screen và chạy 1 vòng kết nối/sync với tài khoản Google test staging trước khi bật công khai cho Beta users.
