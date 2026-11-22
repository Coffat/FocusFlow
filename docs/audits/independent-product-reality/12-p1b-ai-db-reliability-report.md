# 12 — P1B AI Harness, DB Pool & Prove Mode Reliability Report (FocusFlow)

- **Branch**: `fix/p1b-ai-db-reliability` (tạo từ `fix/p1a-reliability-remediation`, bảo toàn toàn bộ P0A + P0B + P1A)
- **Scope**: `AUD-HIGH-08` (AI Circuit Breaker & Redis Failure Policy), `AUD-HIGH-09` (PostgreSQL Connection Pooling & Timeouts), `AUD-MED-12` (Prove Mode Live Grading Correctness), Phase 4 (`MilestoneApprovedEvent` Disposition), Phase 5 (`AI_GATEWAY_TIMEOUT` 1-Wave Concurrency & Checkpoint Recovery). Không mở rộng sang Billing/P1C/P2.

---

## 1. Verified Root Causes & Resolution Status

| Finding / Item | Verified Root Cause | Status | Verification Evidence |
|---|---|---|---|
| **`AUD-HIGH-08`** AI Circuit Breaker & Redis Failure | `ai_harness_v2_enabled=False` vô hiệu hóa CB ở Planning; Evaluation không bọc CB; `RedisCircuitStateStore` không bắt `RedisError` & `INCR`+`EXPIRE` không nguyên tử; `AIExecutionManager` retry cả `AIServiceUnavailableError` khi circuit đang OPEN; `main.py` thiếu handler `503`. | **RESOLVED (P1B VERIFIED)** | `test_ai_circuit_breaker_resilience.py` + `test_ai_harness_runtime.py` (42/42 PASS): CLOSED→OPEN→HALF_OPEN→CLOSED, fail-fast không retry, fallback in-memory khi mất Redis. |
| **`AUD-HIGH-09`** PostgreSQL Pool & Timeouts | `session.py` dùng `NullPool` cho mọi môi trường (không chỉ `test`), thiếu `pool_pre_ping`/`statement_timeout`/`lock_timeout`/`command_timeout` & `engine.dispose()` ở lifespan; 4 use case giữ read transaction mở xuyên suốt LLM call. | **RESOLVED (P1B VERIFIED)** | `test_db_pool_reliability.py` (7/7 PG16 PASS + benchmark ~2x nhanh hơn `NullPool`), `pool.checkedout()==0` sau cancellation/timeout/exhaustion; **Live Staging** `pg_stat_activity`: `7 idle`, **`0 idle in transaction`**. |
| **`AUD-MED-12`** Prove Mode Live Grading | `ai_prove_grader_timeout_seconds=7.5s` quá ngắn cho live Gemini chấm 3 câu tiếng Việt; mọi lỗi kỹ thuật bị nuốt và ghi đè `score=0`, `status=NEEDS_REVIEW`, `submitted_at=now()` (HTTP `200`, làm hỏng `avg_proof_score`); `GetLatestMilestoneProofUseCase` suy diễn `is_verified = score > 0`; thiếu guard chống nộp trùng. | **RESOLVED (P1B VERIFIED)** | `test_prove_mode_grading_correctness.py` (21/21 BE PASS) + `prove-mode-dialog.component.spec.ts` (6/6 FE PASS) + **Live Staging Gemini**: `score=23, is_verified=True, answer_evidence=3`, reload khớp, nộp trùng `409 PROOF_ALREADY_GRADED`. |
| **Phase 4** `MilestoneApprovedEvent` | Được phát tại 3 điểm vào `outbox_events` nhưng không có consumer nào; SRS v1.3 (`FR-PLAN-001` / `UC-07`) không quy định bất kỳ cross-context side effect nào. | **RESOLVED (P1B VERIFIED)** | Dừng phát ra outbox (giữ class deprecated & không xóa lịch sử DB, không tạo no-op handler). `test_milestone_approved_event_disposition.py` + `test_roadmaps_and_ai_planning_api.py` (8/8 PASS) + **Live Staging**: `0` bản ghi `MilestoneApprovedEvent` mới. |
| **Phase 5** `AI_GATEWAY_TIMEOUT` (Milestone #4) | `calculate_dynamic_subjob_concurrency(4, 4)` ép chạy 2 wave tuần tự (2×2) thay vì 1 wave 4 song song; `_prefetch_resources_for_milestones()` chạy tuần tự trong 55s deadline; `finalization_reserve=14.0s` bóp nghẹt Wave 2; SSE `failed` thiếu metadata checkpoint. | **RESOLVED (P1B VERIFIED)** | `test_milestone_timeout_and_recovery.py` (40/40 PASS) + **Live Full Playwright E2E**: **37/37 PASS** (`e2e_full_workflow.spec.ts` chạy 1.1m không còn timeout). |

---

## 2. AI Execution Matrix (Post-P1B)

| Workflow | Provider & Circuit Breaker | Timeout | Retry Policy | Quota Lifecycle | Usage Logging | SSE / Recovery |
|---|---|---|---|---|---|---|
| **Clarification (Init / Follow-up)** | `wrap_with_circuit_breaker(LiteLLMAdapter)` (**ON**) | `15.0s` / `7.5s` | `max_retries=2` (fail-fast on CB OPEN) | Outer UC RESERVE/COMMIT/RELEASE | Yes | Sync HTTP + fallback |
| **Milestone Generation** | Shared CB (**ON**) | `min(50s, rem)` in `55s` | Outer validation loop; fail-fast on CB OPEN | Outer UC; read TX closed pre-LLM | Yes + `workflow_runs` | 2-Stage SSE |
| **Schedule Proposal (Milestone-Scoped)** | Shared CB (**ON**) | `min(36s, rem - 6.0s)` in `55s`, **1-wave concurrency** | Up to 1 local retry if `rem >= 12s`; fail-fast on CB OPEN | Outer UC (`AI_GATEWAY_TIMEOUT` releases) | Yes + CACHE logs | 2-Stage SSE + Redis checkpoint (`completed_milestones`, `resumable`) |
| **Dual Critics / Tier-3 Judge** | Shared CB (**ON**) | `15.0s` / `12.0s` (soft-skip `< 6s` / `< 3s`) | `max_retries=0` | Piggybacks parent | Yes | Soft-skip |
| **Prove Mode Question Gen** | Shared CB (**ON**) | **`20.0s`** | `max_retries=1` (fail-fast on CB OPEN) | Autonomous quota facade; read TX closed pre-LLM | Yes (`AI_REVIEW_MILESTONE`) | Sync HTTP `202` |
| **Prove Mode Grading** | Shared CB (**ON**) | **`25.0s`** | `max_retries=1` (fail-fast on CB OPEN) | Autonomous quota facade (release on `503`); read TX closed pre-LLM | Yes (`AI_REVIEW_MILESTONE`) | Sync HTTP; `503 AI_GRADING_UNAVAILABLE` giữ bài làm & cho `"Thử chấm lại"`; `409 PROOF_ALREADY_GRADED` |
| **Weekly Review SRL** | Shared CB (**ON**) | `10.5s` | `max_retries=1` (fail-fast on CB OPEN) | Autonomous quota facade; read TX closed pre-LLM | Yes (`AI_REVIEW_WEEKLY`) | Sync HTTP `202` |

---

## 3. Circuit Breaker Behavior & Redis Failure Policy

- **Circuit Breaker (`circuit_breaker.py`)**: Bật mặc định (`ai_circuit_breaker_enabled=True`, `ai_harness_v2_enabled=True`) qua `wrap_with_circuit_breaker()` dùng chung cho cả `planning` và `evaluation`. Trạng thái `CLOSED` → `OPEN` (ngưỡng `3` lỗi transient trong `60s`, mở `60s`) → `HALF_OPEN` (single-probe lock). Phân biệt lỗi transient (timeout, 429, 5xx, network) với lỗi validation/client (`ValidationError`, 400/401/403/404/422). `AIExecutionManager` fail-fast ngay trên `AIServiceUnavailableError` (không retry) và `main.py` trả HTTP `503`. Telemetry (`get_telemetry()`) theo dõi `rejected_calls`, `recorded_failures`, `opened_count`, `half_open_probes`, `recovery_count`, `redis_fallback_count`.
- **Redis Failure Policy theo chức năng**:
  - **AI Circuit Breaker**: Fallback tự động sang `InMemoryCircuitStateStore` (log cảnh báo `ai_circuit_breaker_redis_fallback`) — không làm sập AI call khi Redis chập chờn.
  - **AI Quota**: Lưu trên PostgreSQL (`SELECT ... FOR UPDATE`), **không bao giờ bypass** khi Redis unavailable.
  - **Auth / RTR / High-Risk Rate Limits (OTP/Login-Account/Password-Reset)**: **Fail-closed (`503`)** (giữ nguyên chuẩn P0B).
  - **SSE Job Store**: Fallback in-memory có sẵn cho stream tạm thời; không báo thành công giả.

---

## 4. Database Pool Sizing Rationale & Before/After Benchmark (`AUD-HIGH-09`)

- **Topology**: Direct PostgreSQL 16 (`max_connections=100`, không dùng PgBouncer). `supervisord.conf` chạy 1 Uvicorn API + 2 Taskiq workers + 1 scheduler (3 process tải DB chính).
- **Sizing**:
  - `ENVIRONMENT=test`: Giữ `NullPool` (bắt buộc do pytest function-scoped asyncio event loop).
  - `dev`/`staging`/`production`: `AsyncAdaptedQueuePool` với `db_pool_size=10`, `db_max_overflow=10`, `db_pool_timeout=30s`, `db_pool_recycle=1800s`, `db_pool_pre_ping=True`. Worst-case `3 × 20 = 60` connections < `100` (còn 40 slot dự phòng cho scheduler/alembic/admin).
  - `connect_args`: `timeout=10s`, `command_timeout=30s`, `server_settings={"statement_timeout": "30000", "lock_timeout": "10000"}`. `main.py` gọi `await engine.dispose()` khi shutdown.
  - Đóng read transaction trước mọi LLM call dài (`GenerateMilestoneProofUseCase`, `SubmitMilestoneProofUseCase`, `ExecuteMilestoneGenerationUseCase`, `GenerateWeeklyReviewUseCase`).
- **Before vs After Benchmark (PostgreSQL 16 thực, 40 concurrent `SELECT 1`)**:
  - **Before (`NullPool`)**: `p50 = 54.37ms` | `p95 = 60.78ms` | `p99 = 61.55ms` | `wall = 67.91ms`
  - **After (`AsyncAdaptedQueuePool`, 10+10)**: `p50 = 27.53ms` | `p95 = 33.27ms` | `p99 = 33.92ms` | `wall = 40.72ms` (**~2.0x nhanh hơn**)
  - **Leak Verification**: `pool.checkedout() == 0` sau 20 concurrent queries, `statement_timeout`, rollback, mid-query `CancelledError` và pool exhaustion; **Live Staging** `pg_stat_activity`: `7 idle`, `1 active`, **`0 idle in transaction`**.

---

## 5. Prove Mode Live Grading & `MilestoneApprovedEvent` Disposition

- **Prove Mode Live Smoke Test (Real Gemini via Cobhub trên staging)**:
  - `POST /proofs/generate-jobs`: `202` (`5.95s`, 3 câu hỏi PostgreSQL 16 tiếng Việt).
  - `POST /proofs/{id}/submit`: `200` (`6.36s`, `status=NEEDS_REVIEW`, `score=23`, `is_verified=True`, `answer_evidence=3`).
  - `GET /proofs/latest`: khôi phục chính xác `score=23, is_verified=True`.
  - Nộp trùng `POST /proofs/{id}/submit`: **`409 PROOF_ALREADY_GRADED`** (0 credit bị trừ thêm).
  - Quota & `ai_usage_logs`: `used_calls` tăng chính xác `1 → 3` (`+2`), 5 bản ghi `ai_usage_logs` khớp tổng `17,034` tokens.
- **`MilestoneApprovedEvent` Disposition**: Deprecated tại `planning_events.py`, dừng phát ra `outbox_events` ở cả 3 điểm (`ApproveMilestonesUseCase` ×2, `SaveManualRoadmapPlanUseCase`), giữ nguyên lịch sử DB, không thêm no-op handler. Live staging xác nhận `0` bản ghi `MilestoneApprovedEvent` mới.

---

## 6. Files Changed & Verification Summary

- **Backend**: `config.py`, `circuit_breaker.py`, `execution_manager.py`, `database/session.py`, `main.py`, `planning/presentation/deps.py`, `evaluation/presentation/deps.py`, `evaluation/domain/exceptions/prove_exceptions.py` *(new)*, `evaluation/application/use_cases/intelligence.py`, `evaluation/presentation/routers.py`, `planning/domain/events/planning_events.py`, `planning/application/use_cases/{milestone,proposal_management,proposal_generation}_use_cases.py`, `planning/application/services/milestone_scoped_decomposer.py`.
- **Frontend**: `prove-mode-dialog.component.ts` & `.spec.ts`.
- **Tests**: New `test_ai_circuit_breaker_resilience.py`, `test_db_pool_reliability.py`, `test_prove_mode_grading_correctness.py`, `test_milestone_approved_event_disposition.py`, `test_milestone_timeout_and_recovery.py`; updated `test_intelligence_hardening.py`, `test_roadmaps_and_ai_planning_api.py`, `test_dynamic_milestone_subjobs.py`, `test_hardening_phase1_3.py`.
- **All Quality Gates**:
  - `ruff check` & `ruff format --check` (476 files): **PASS**
  - `mypy --strict src` (326 files): **PASS**
  - `lint-imports` (5/5 contracts): **PASS**
  - `pytest` unit/eval: **897 passed, 1 skipped** | integration (PG16 + Redis 7): **138 passed, 2 deselected**
  - `scripts/check-api-contract.sh`: **PASS (0 drift)**
  - Frontend `ng lint` / `ng test` (**654/654**) / `ng build`: **PASS**
  - Full Playwright E2E on Live Docker Staging: **37/37 PASS (4.4m)** (`e2e_full_workflow.spec.ts`: **1.1m**, Prove Mode E2E: **11.2s**).

---

## 7. Residual Risks & P1C / P2 Recommendations

- **Residual Risks**:
  - Khi scale nhiều API/worker replicas lên >5 process trên cùng 1 instance PG16 (`max_connections=100`), cần hạ `DB_POOL_SIZE` theo công thức hoặc đặt PgBouncer phía trước.
  - `InMemorySseJobStore` fallback vẫn chưa có TTL eviction (`AUD-MED-08`, thuộc P2).
  - Live external LLM vẫn có thể chậm bất thường nếu upstream gateway quá tải; checkpoint Redis cho phép bấm thử lại mà không mất tiến độ đã sinh.
- **Next Recommendations (Chưa triển khai trong lượt này)**:
  - **P1C**: `AUD-HIGH-11` (chính thức feature-gate Billing cho MVP Beta hoặc tích hợp live payment gateway + sửa route `/billing/mock-checkout`).
  - **P2**: `AUD-MED-01..11` (chống enumeration password reset, atomic OTP, bỏ `access_token` khỏi JSON body, `/api/health` ping DB/Redis, dọn 2 raw SQL cross-context sót, đồng bộ `docs/database/schema.sql` 36 bảng).
