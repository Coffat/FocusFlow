# 11 — P1A Reliability & E2E Remediation Report (FocusFlow)

- **Branch**: `fix/p1a-reliability-remediation` (tạo từ `fix/p0b-auth-security-remediation`, bảo toàn toàn bộ P0A + P0B)
- **Scope**: `AUD-HIGH-06` (RAG Ingestion Security), `AUD-HIGH-07` (Transactional Outbox Reliability), `AUD-MED-13` (Playwright E2E Stabilization). Không mở rộng sang P1B/P1C/P2 (`AUD-HIGH-08`, `AUD-HIGH-09`, `AUD-MED-12`, `AUD-HIGH-11`).

---

## 1. Baseline Findings & Verified Root Causes

| Finding ID | Verified Root Cause | Status |
|---|---|---|
| **`AUD-HIGH-06`** | (1) `CreateKnowledgeSourceUseCase.create_file` chỉ kiểm tra extension, cho phép `.url` upload, không kiểm magic bytes/MIME/DOCX zip-bomb; (2) lưu tạm trong `/tmp/focusflow-knowledge` không `0700`/`0600` và không cleanup khi ingest xong/lỗi/timeout/cancel; (3) `learning_resource_discovery.py` (`verify_official_url_live`) tạo `httpx.AsyncClient` riêng bỏ qua `SafeUrlFetcher`; (4) `GET /goals/{goal_id}/knowledge-sources` chưa kiểm cross-user goal ownership. | **RESOLVED (P1A VERIFIED)** |
| **`AUD-HIGH-07`** | (1) `relay_pending_outbox_events` đánh dấu `PUBLISHED` ngay cả khi `_OUTBOX_HANDLERS` rỗng (silent event drop); (2) không có backoff, không rollback + tạo session mới khi DB transaction abort (gây `MissingGreenlet` / retry vô hạn); (3) dùng `FOR UPDATE SKIP LOCKED` gây self-deadlock với `FOR KEY SHARE` khi consumer trong session khác ghi `processed_events` (FK → `outbox_events.id`). | **RESOLVED (P1A VERIFIED)** |
| **`AUD-MED-13`** | (1) `e2e_full_workflow.spec.ts` giả định Clarification chỉ 1 vòng & hardcode `localhost:8000`; (2) `signal_e2e_evidence.spec.ts` dùng selector cũ `.trailing-toggle-button`, hardcode `localhost:8000` + Bearer token và nhiều `waitForTimeout`; (3) `p2a-data-consistency.spec.ts` Workflow 6 click `step-tab-4` trước khi `loadRoadmapDetail()` hydrate xong `activeStep(3)`. | **RESOLVED (P1A VERIFIED)** |

---

## 2. RAG Ingestion Security Changes (`AUD-HIGH-06`)

- **Magic-Byte, MIME & Decompression Bomb Protection** (`document_extractor.py`, `config.py`):
  - Kiểm tra chữ ký thật: `%PDF-` (PDF), `PK\x03\x04` + cấu trúc `word/document.xml` & `[Content_Types].xml` (DOCX), UTF-8 chặt + chặn null bytes/control chars (TXT); đối chiếu MIME consistency.
  - Pre-extraction `ZipInfo` guard cho DOCX: giới hạn số entry, tổng kích thước giải nén (50MB), tỉ lệ nén (100x), chặn zip-slip (`..`, absolute path, drive letter, null byte).
  - Giới hạn số trang PDF (`knowledge_pdf_max_pages`), số ký tự trích xuất (`knowledge_max_extracted_chars`), và chuẩn hóa lỗi tên miền (không lộ đường dẫn nội bộ/stack trace).
- **Private Temp File Lifecycle & Guaranteed Cleanup** (`local_file_store.py`, `knowledge_source_use_cases.py`):
  - Thư mục tạm riêng theo UID (`<tempdir>/focusflow-knowledge-<uid>`, quyền `0700`, từ chối symlink root); file tạm tạo qua `os.open(..., 0o600 | O_NOFOLLOW)` với tên UUID thuần (chặn path traversal).
  - `CreateKnowledgeSourceUseCase.create_file` chặn `.url`, chạy `sanitize_filename` + `validate_uploaded_document` trước khi ghi đĩa, và cleanup bằng `asyncio.shield` nếu lưu DB lỗi.
  - `IngestKnowledgeSourceUseCase.execute` bọc `try ... finally` với `asyncio.shield(self._files.delete(...))` đảm bảo dọn file trên mọi nhánh (success, failure, timeout, `asyncio.CancelledError`); không ghi raw document content vào log.
- **Unified SSRF & Ownership Enforcement** (`safe_url_fetcher.py`, `learning_resource_discovery.py`, `planning/presentation/routers.py`):
  - `SafeUrlFetcher` kiểm allowlist `Content-Type`, sanitize lỗi HTTP/socket/timeout (không lộ IP/host nội bộ), bổ sung `probe_reachable(...)` IP-pinned + `trust_env=False` + `verify=True`.
  - Định tuyến `verify_official_url_live` qua `SafeUrlFetcher.probe_reachable(...)` (không còn HTTP client riêng vượt rào).
  - Bắt buộc kiểm quyền sở hữu goal (`404`) trên `GET /goals/{goal_id}/knowledge-sources` và `GET /knowledge-sources/{source_id}`.

---

## 3. Transactional Outbox Reliability Design & Failure/Retry Semantics (`AUD-HIGH-07`)

- **Delivery Contract**: At-least-once delivery kết hợp consumer-side idempotency (`processed_events`). Không đánh đồng broker acknowledgment với business-side-effect completion.
- **No Silent Drop / Quarantine**: Khi không tìm thấy handler cho `event_type`, tuyệt đối không đánh dấu `PUBLISHED`; chuyển sang `status='FAILED'` (`published_at=None`) với `payload._outbox_meta.failure_code = "NO_HANDLER_REGISTERED"` và ghi cảnh báo/metric `unknown_handler_events`.
- **Bounded Retries & Exponential Backoff**: Lỗi tạm thời tăng `retry_count`, tính `next_retry_at` theo backoff lũy thừa (`DEFAULT_BASE_BACKOFF_SECONDS=5.0`, `DEFAULT_MAX_BACKOFF_SECONDS=300.0`) lưu trong `payload._outbox_meta`, bỏ qua bản ghi chưa đến hạn, và chuyển dứt khoát sang `status='FAILED'` (`MAX_RETRIES_EXCEEDED`) khi chạm `max_retries`.
- **Aborted Transaction Recovery**: Lưu trước `event_id` & `event_type` dưới dạng biến cục bộ (tránh `MissingGreenlet` sau rollback); mọi `SQLAlchemyError` / session hỏng đều `await session.rollback()` và ghi trạng thái retry/failure qua một session mới sạch (`_record_failure_in_fresh_session`).
- **Concurrency Locking (FK-Safe)**: Dùng `.with_for_update(skip_locked=True, key_share=True)` (`FOR NO KEY UPDATE SKIP LOCKED`) thay cho `FOR UPDATE SKIP LOCKED`, vừa chống double-claim giữa nhiều relay worker vừa tránh self-deadlock `FOR KEY SHARE` khi consumer ghi `processed_events` (có FK tới `outbox_events.id`).
- **Observability**: `collect_outbox_metrics(session)` trả về `OutboxMetricsSnapshot(pending_count, failed_count, oldest_pending_age_seconds, retry_attempts, unknown_handler_events, dispatch_failures, published_count)` kèm log đã redact credential URL.

---

## 4. Files Changed & Tests Added

### Backend Source
- `backend/src/shared_kernel/config.py`
- `backend/src/shared_kernel/infrastructure/outbox/relay.py`
- `backend/src/planning/infrastructure/knowledge/local_file_store.py`
- `backend/src/planning/application/knowledge/document_extractor.py`
- `backend/src/planning/application/knowledge/safe_url_fetcher.py`
- `backend/src/planning/application/knowledge/__init__.py`
- `backend/src/planning/application/services/learning_resource_discovery.py`
- `backend/src/planning/application/use_cases/knowledge_source_use_cases.py`
- `backend/src/planning/presentation/deps.py`
- `backend/src/planning/presentation/routers.py`

### Frontend E2E (`frontend/e2e/` only — 0 thay đổi `frontend/src/`)
- `frontend/e2e/e2e_full_workflow.spec.ts` (hỗ trợ Clarification đa vòng, bỏ `localhost:8000` và `waitForTimeout`)
- `frontend/e2e/signal_e2e_evidence.spec.ts` (selector theo role/label hiện tại, bỏ `localhost:8000`, `Bearer` token và `waitForTimeout`)
- `frontend/e2e/p2a-data-consistency.spec.ts` (đợi hydration `step-3-panel` + `ACTIVE` trước khi click `step-tab-4` ở Workflow 6)
- `frontend/e2e/helpers/otp-auth.helper.ts` + 6 spec khác chuẩn hóa `BACKEND_API_URL` fallback (`http://127.0.0.1:3000/api/v1`)

### Tests Added / Updated
- Added: `backend/tests/unit/planning/test_rag_ingestion_security.py`
- Added: `backend/tests/integration/planning/test_rag_knowledge_ownership.py`
- Added: `backend/tests/integration/shared_kernel/test_outbox_reliability_integration.py` (8 integration tests trên PostgreSQL 16 + Redis 7 / `RedisStreamBroker` thật)
- Updated: `backend/tests/unit/planning/test_pr3_reliability_resources_and_bugs.py`, `backend/tests/integration/shared_kernel/test_outbox_relay_integration.py`

---

## 5. Quality Gates & Redis/PostgreSQL Runtime Evidence

| Gate / Verification | Result | Exact Details |
|---|---|---|
| Backend `ruff check` & `ruff format --check` | **PASS** | 470 files formatted, 0 issues |
| Backend `mypy --strict src` | **PASS** | 0 issues across 325 source files |
| Backend `lint-imports` | **PASS** | 5/5 contracts kept, 0 broken |
| Backend Unit + AI Evals + Eval + Root | **PASS** | **870 passed, 1 skipped, 0 failed** |
| Backend Integration (Real PG16 + Redis 7) | **PASS** | **125 passed, 2 deselected, 0 failed** (gồm 8/8 `test_outbox_reliability_integration.py` với `RedisStreamBroker` thật + 7/7 `test_outbox_relay_integration.py`) |
| OpenAPI Contract (`check-api-contract.sh`) | **PASS** | **0 drift** |
| Frontend `ng lint` / `ng test` / `ng build` | **PASS** | **652/652 Vitest PASS**, prod build 0 errors |
| Live Staging — RAG Security (`verify_p1a_live.py`) | **PASS** | PNG bytes giả `.pdf` → **HTTP 422** (`Tệp PDF không có chữ ký định dạng hợp lệ`); SSRF `127.0.0.1:6379` & `169.254.169.254` → **HTTP 422** (`URL trỏ đến mạng nội bộ, loopback hoặc link-local`). |
| Live Staging — Outbox Worker | **PASS** | `PUT /availabilities/me` tạo `AvailabilityUpdatedEvent` → tick 60s chuyển `PENDING → PUBLISHED`, `processed_events` ghi cả `planning.availability_updated_dispatch` & `planning.availability_updated_consumer`. Quarantine hoạt động thật trên log staging cho `MilestoneApprovedEvent` (`NO_HANDLER_REGISTERED`). |

---

## 6. Playwright Full-Suite Results (3 Consecutive Runs on Live Docker Staging)

Command: `PLAYWRIGHT_BASE_URL=http://127.0.0.1:3000 BACKEND_API_URL=http://127.0.0.1:3000/api/v1 MAILPIT_API_URL=http://127.0.0.1:8025/api/v1 pnpm exec playwright test --reporter=list`

| Run | Passed | Failed | Skipped | Duration | Notes |
|---|---:|---:|---:|---:|---|
| **Run #1** | **36** | **1** | **0** | `5.4m` | Fail duy nhất: `e2e_full_workflow.spec.ts:16` gặp **`AI_GATEWAY_TIMEOUT`** (live Gemini proxy milestone #4 vượt `AI_HARD_TIMEOUT_SECONDS=55`, TTFT 20.4s) — không phải flake UI/selector. |
| **Run #2** | **37** | **0** | **0** | `4.6m` | **37/37 PASS** |
| **Run #3** | **37** | **0** | **0** | `4.5m` | **37/37 PASS** |
| **Tổng cộng** | **110** | **1** | **0** | `14.5m` | **99,1% pass rate; 0 UI/hydration/selector flakes** (`p2a-data-consistency` 30/30, `signal_e2e_evidence` 3/3, `auth` 24/24). |

---

## 7. Residual Risks & P1B Recommendations

### Residual Risks
- **Live LLM Latency Timeout**: Khi chạy E2E trên staging nối trực tiếp tới LLM proxy thật (`AI_HARD_TIMEOUT_SECONDS=55`), biến động độ trễ mạng/model có thể gây `AI_GATEWAY_TIMEOUT` ở bước decompose milestone (xảy ra 1/3 lần ở Run #1).
- **Unregistered Event Type (`MilestoneApprovedEvent`)**: Quan sát thực tế trên staging cho thấy `MilestoneApprovedEvent` đang được ghi vào `outbox_events` nhưng chưa có consumer nào đăng ký — nay đã bị cách ly rõ ràng (`NO_HANDLER_REGISTERED`) thay vì âm thầm drop; cần quyết định ở đợt sau là đăng ký consumer hay dừng phát ra outbox nếu không cần cross-context side effect.
- **RAG Embedding Unconfigured in Staging**: `rag_embedding_configured=false` (thiếu `EMBEDDING_API_KEY`).

### P1B Recommendations (Chưa triển khai trong lượt này)
1. **`AUD-HIGH-08`**: Bật AI Circuit Breaker mặc định cho cả Planning & Evaluation và bọc fail-open an toàn khi mất Redis.
2. **`AUD-HIGH-09`**: Thay `NullPool` bằng `AsyncAdaptedQueuePool` + `pool_pre_ping` + `command_timeout`.
3. **`AUD-MED-12` & `AUD-HIGH-11`**: Điều tra Prove Mode live grader fallback (`NEEDS_REVIEW`/`score=0`) và feature-gate chính thức Billing (hoặc tích hợp live payment gateway).
