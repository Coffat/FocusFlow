# 14 — P2 Architecture Hygiene, Schema Reconciliation & Release Config Report (FocusFlow)

- **Branch**: `fix/p2-architecture-hygiene` (HEAD `347066b`, bảo toàn nguyên vẹn working tree P0A → P1C; chưa tự commit/merge/deploy và **không tự tuyên bố GO-LIVE**)
- **Scope**: P2 — Architecture Boundaries (`AUD-MED-09`), Backend Security/Reliability Hygiene (`AUD-MED-01/02/04/05/06/08`, `AUD-LOW-01/02/03`), Taskiq Cleanup (`AUD-LOW-06`), API Pagination (`BE-API-04`), Frontend Hygiene (`AUD-MED-07`, `AUD-LOW-05/06`), Database Schema & Docs Reconciliation (`AUD-MED-10`), và Phase 5 Production/Staging Configuration Audit.

---

## 1. Git Baseline & Change Provenance

- **HEAD**: `347066b` (`feat: type milestone subjob progress events`).
- **Branch lineage**: `fix/p0-audit-remediation` → `fix/p0a-security-remediation` → `fix/p0b-auth-security-remediation` → `fix/p1a-reliability-remediation` → `fix/p1b-ai-db-reliability` → `fix/p1c-billing-release-gating` → `fix/p2-architecture-hygiene`.
- **Working Tree Provenance**: Toàn bộ thay đổi P0–P2B2B trước đó và toàn bộ P0A, P0B, P1A, P1B, P1C, P2 hiện nằm trong working tree chưa commit (tuân thủ nghiêm quy tắc không tự commit/merge/rebase/force-push). Cần review & chia commit nguyên tử theo từng đợt trước khi mở PR vào `main`.

---

## 2. Complete Finding Reconciliation (34 Independent Audit Findings)

| Category | Total | RESOLVED & VERIFIED | RESOLVED (FEATURE GATED) | DEFERRED WITH JUSTIFICATION |
|---|---:|---:|---:|---:|
| **CRITICAL (`AUD-CRIT-01..04`)** | **4** | **4** (P0A) | 0 | 0 |
| **HIGH (`AUD-HIGH-01..11`)** | **11** | **10** (P0A/P0B/P1A/P1B) | **1** (`AUD-HIGH-11` Free Beta Gated in P1C; live provider NOT VERIFIED) | 0 |
| **MEDIUM (`AUD-MED-01..13`)** | **13** | **11** (`01,02,04,05,06,07,08,09,10` P2; `12` P1B; `13` P1A) | 0 | **2** (`AUD-MED-03`, `AUD-MED-11`) |
| **LOW (`AUD-LOW-01..06`)** | **6** | **5** (`01,02,03,05,06` P2) | 0 | **1** (`AUD-LOW-04`) |
| **Tổng cộng** | **34** | **30** | **1** | **3** |

### Deferred Findings & Justification (3 items)
1. **`AUD-MED-03`** (`access_token` trong JSON body): Gỡ bỏ sẽ phá vỡ hợp đồng API của các bài test integration Bearer (`test_auth.py`, `test_otp_auth.py`, `test_google_auth.py`) và Swagger/API clients hiện có; hoãn sang PR breaking-change có phối hợp riêng (FE hiện **không** lưu token vào `localStorage`/`sessionStorage`, dùng cookie `HttpOnly`).
2. **`AUD-MED-11`** (`LLM_PROVIDER=mock` / `CALENDAR_PROVIDER=local_mock` & non-Gemini tool parity): Không chặn Free Beta production (production chạy Gemini live + Google Calendar thật); cần quyết định sản phẩm có triển khai offline mock runtime hay cập nhật lại `AGENTS.md` cho phản ánh thực tế.
3. **`AUD-LOW-04`** (Logout stateless access token 15m window): Yêu cầu bổ sung `token_version` (migration) hoặc Redis JTI denylist trên mọi request; rủi ro thấp vì TTL chỉ 15 phút và refresh family đã bị thu hồi nguyên tử (`AUD-HIGH-02/03`).

---

## 3. Architecture Violations Resolved (`AUD-MED-09`)

- Đã xóa sạch 2 truy vấn raw SQL xuyên bounded context còn sót trong `execution`:
  1. `execution/infrastructure/adapters/schedule_sync_adapter.py`: thay `SELECT concept_id FROM learning_concepts ...` bằng `filter_existing_concept_ids(session, concept_ids)` từ `src.planning.public_api`.
  2. `execution/infrastructure/adapters/weekly_execution_metrics_adapter.py`: thay `SELECT proposal_data FROM schedule_proposals ...` bằng `get_latest_applied_proposal_data(session, roadmap_id, limit=3)` từ `src.planning.public_api`.
- Triển khai `PlanningReadQueryAdapter` (`planning/infrastructure/adapters/planning_read_query_adapter.py`) giữ nguyên `AsyncSession` & transaction semantics, 0 circular import, `lint-imports` 5/5 contracts.
- Gia cố `backend/tests/unit/test_execution_boundary_architecture.py` quét **toàn bộ `.py` trong `backend/src/execution/`** chặn mọi raw SQL tham chiếu bảng của `planning` hoặc `account`.

---

## 4. Backend, Frontend Hygiene & Pagination Decisions

### Backend Security & Reliability Hygiene
- **`AUD-MED-01`** (`password_reset_otp_use_case.py`): Chuỗi phản hồi đồng nhất + cooldown 60s áp dụng trước tra cứu user (chống account enumeration — đã xác minh live trên staging).
- **`AUD-MED-02`** (`otp_repository.py`): `consume_reset_token()` dùng `GETDEL` nguyên tử; `verify_and_consume_otp()` dùng Redis Lua `_LUA_VERIFY_AND_CONSUME_OTP` (0 TOCTOU).
- **`AUD-MED-04`** (`main.py`): `/api/health` kiểm tra DB (`SELECT 1`, 2s) + Redis (`PING`, 2s) trả `200`/`503` với payload tối giản `{"status", "database", "redis"}`, gỡ `?probe_ai=true` & loại bỏ hoàn toàn lộ `ai_gateway`/`email_host`/`secret_key_is_default`.
- **`AUD-MED-05`** (`webhook_router.py`): Fail-closed `403` khi `channel_token_hash` trống.
- **`AUD-MED-06`** (`logging.py`, `email_service.py`): Redact đệ quy nested dict/list + mask `to_email` (`u***@domain.com`).
- **`AUD-MED-08`** (`sse/job_store.py`): `RedisSseJobStore` chỉ ghi `_fallback` khi Redis lỗi; bổ sung `evict_expired()` theo TTL trên `InMemorySseJobStore`.
- **`AUD-LOW-01/02/03`**: Validate Fernet/Calendar encryption key fail-closed ở `production` (`config.py`); thay `str(exc)` ở OAuth redirect bằng mã lỗi an toàn (`calendar_router.py`); dùng `async with httpx.AsyncClient(timeout=15.0)` chống rò rỉ socket.
- **Taskiq Cleanup (`AUD-LOW-06`)**: Sau `git grep` xác nhận 0 caller/scheduler/queue, đã xóa `sync_external_google_calendar` (no-op), `execution.sync_schedule_blocks_to_google` (duplicate), và `evaluation.sweep_overdue_tasks_and_anti_loop` (duplicate delegator; giữ module `evaluation.presentation.tasks` cho `supervisord.conf`).

### Pagination Decisions (`BE-API-04`)
- `GET /api/v1/tasks` & `GET /api/v1/tasks/backlog`: thêm optional `limit` (`1..500`), `offset` (`>=0`) tương thích ngược (giữ nguyên response shape & deterministic ordering).
- `GET /api/v1/roadmaps`: thêm optional `limit` (`1..100`), `offset` (`>=0`) tương thích ngược (`created_at DESC`).
- `GET /api/v1/account/notifications`: đã có pagination (`limit: 1..100`, `offset >= 0`).
- `GET /api/v1/account/billing/transactions`: đã bị chặn trần nội bộ `limit=50`.

### Frontend Hygiene (`AUD-MED-07`, `AUD-LOW-05`, `AUD-LOW-06`)
- Tạo `timeoutInterceptor` (`30s` default + `HTTP_TIMEOUT_MS` / `SKIP_HTTP_TIMEOUT`) đăng ký trong `app.config.ts`.
- `ai-sse.service.ts` + `roadmap.service.ts`: refresh phiên 1 lần khi `EventSource` đóng bất ngờ trước terminal event; lưu/khôi phục active job qua `sessionStorage` (TTL 10 phút) trong `loadRoadmapDetail()` để F5 không mất tiến độ SSE.
- Hợp nhất URL hardcode ở `calendar-integration.service.ts`, `settings.service.ts`, `profile.service.ts` về `API_ENDPOINTS`.
- Xóa 4 file orphan đã xác minh 0 reference (`auth.routes.ts`, `login-page.component.ts`, `dashboard.routes.ts`, `dashboard-page.component.ts`); giữ nguyên `styles.scss`/`styles.css`.

---

## 5. Database Schema & Documentation Reconciliation (`AUD-MED-10`)

- Kiểm chứng clean-room trên database tạm `focusflow_schema_audit` (`alembic upgrade head` → `0015_add_notifications_table`): **36** application tables (`Base.metadata` khớp 100%, 0 drift), **37** tổng bảng (gồm `alembic_version`), **26** `BEFORE UPDATE` triggers, **66** explicit indexes.
- Cập nhật đồng bộ:
  - `docs/database/schema.sql` (bổ sung bảng `notifications` + 5 trigger `0014` + 1 trigger `0015`).
  - `docs/database/database-schema-design.md` (v3.4, 36 bảng: 13/10/5/4/4).
  - `docs/audits/independent-product-reality/01-independent-system-inventory.md` (103 routes / 92 unique paths, 36 bảng).

---

## 6. Production Configuration Audit & Release Gate Prerequisites (Phase 5)

Các điều kiện bắt buộc ở tầng hạ tầng/triển khai trước khi mở **Free Beta Production** (chưa triển khai trong repo):
1. **Production Docker / Process Manifest**: Tạo `docker-compose.prod.yml` & `supervisord.prod.conf` bỏ `uvicorn --reload`, bỏ bind mounts `./backend:/app` & `./frontend:/app`, build Angular production (thay `frontend/Dockerfile.dev`), và gỡ bỏ `mailpit` (đặc biệt port `8025`).
2. **Production Secrets & Env Vars**: Cấu hình `ENVIRONMENT=production`, `DEBUG=False`, 64-hex `SECRET_KEY`, `FERNET_KEY`, `CALENDAR_ENCRYPTION_KEY` riêng (không dùng fallback), HTTPS `FRONTEND_URL`/`BACKEND_CORS_ORIGINS`/`CSRF_TRUSTED_ORIGINS`/`GOOGLE_REDIRECT_URI`/`CALENDAR_WEBHOOK_BASE_URL`, `BILLING_RELEASE_MODE=FREE_BETA`, `RATE_LIMIT_*`, `LLM_API_KEY`, `EMBEDDING_API_KEY` (nếu bật RAG), production transactional SMTP (`EMAIL_HOST/PORT/USER/PASS/FROM`), và bật mật khẩu Redis (`--requirepass`).
3. **Database Operations**: Thiết lập backup tự động hàng ngày (`pg_dump` / WAL PITR) + diễn tập restore; nếu scale >1 backend container hoặc >1 Uvicorn worker, hạ `DB_POOL_SIZE`/`DB_MAX_OVERFLOW` hoặc đặt PgBouncer + tách `alembic upgrade head` thành pre-deploy job.
4. **Git Hygiene**: Review và chia commit nguyên tử từ working tree hiện tại trước khi mở PR vào `main`.

---

## 7. Phase 6 Verification Evidence

| Gate / Suite | Result | Exact Details |
|---|---|---|
| Backend `ruff check` & `ruff format --check` | **PASS** | 478 files formatted, 0 issues |
| Backend `mypy --strict src` | **PASS** | 0 issues across 327 source files |
| Backend `lint-imports` | **PASS** | 5/5 contracts kept, 0 broken (318 files) |
| Backend Unit + AI Evals + Eval + Root | **PASS** | **916 passed, 1 skipped, 0 failed** |
| Backend Integration (Real PG16 + Redis 7) | **PASS** | **145 passed, 2 deselected, 0 failed** |
| OpenAPI Contract (`check-api-contract.sh`) | **PASS** | **0 drift** (`schema.d.ts` synced) |
| Frontend `ng lint` / `ng test` / `ng build` | **PASS** | **666/666 Vitest PASS**, prod build 0 errors |
| Live Staging `/api/health?probe_ai=true` | **PASS** | `200 {"status": "healthy", "database": "ok", "redis": "ok"}` (0 leaked keys) |
| Live Staging Password Reset Anti-Enumeration | **PASS** | Cùng 1 thông báo `200` cho email tồn tại & không tồn tại; lần 2 trả `429` cooldown đồng nhất |
| Live Staging Free Beta Config | **PASS** | `200`, `release_mode: "FREE_BETA"`, `checkout_enabled: false` |
| **Full Playwright E2E (10 specs / 37 tests)** | **PASS** | **`37 passed (4.6m)`, 0 failed, 0 skipped, 0 flaky** |
