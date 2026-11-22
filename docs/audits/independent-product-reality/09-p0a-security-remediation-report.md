# 09 — P0A Security Remediation Report (FocusFlow)

- **Branch**: `fix/p0a-security-remediation` (tạo từ `fix/p0-audit-remediation` @ `347066b`, bảo toàn nguyên vẹn working tree trước đó)
- **Scope**: P0A — 7 Critical Security & Confirmed Exploitable Defects (`AUD-CRIT-01`, `AUD-CRIT-02`, `AUD-CRIT-03`, `AUD-CRIT-04`, `AUD-HIGH-10`, `AUD-HIGH-03`, `AUD-HIGH-04`). Không mở rộng sang P0B/P1/P2.
- **Methodology**: Test-first (tái hiện lỗi bằng negative tests trước khi sửa), bảo toàn Hexagonal Architecture (`lint-imports` 5/5 contracts), kiểm chứng cả unit/integration lẫn live Docker staging (`http://127.0.0.1:3000`).

---

## 1. Verified Root Causes & Resolution Status

| Finding ID | Verified Root Cause | Status | Verification Evidence |
|---|---|---|---|
| **`AUD-CRIT-01`** | `GoogleAuthService.verify_access_token()` chỉ gọi `userinfo` mà không kiểm tra `aud`/`azp == google_client_id`; `verify_id_token()` nuốt `InvalidCredentialsError` dưới `except Exception`; `GoogleAuthUseCase` đặt mặc định `email_verified = payload.get("email_verified", True)`. | **RESOLVED** | `test_google_auth_security.py` + `test_google_auth.py` (PASS) + Live `POST /auth/google` từ chối fake `id_token` & `access_token` (`401`). |
| **`AUD-CRIT-02`** | `billing_router.py` dùng chung JWT `settings.secret_key` để ký HMAC webhook, không kiểm `X-Webhook-Timestamp` (replay), không kiểm `event_type`/`status == PAID`/`amount_vnd`/`currency`/`user_id`, và `SettlePaymentTransactionUseCase` không khóa hàng `FOR UPDATE`. | **RESOLVED** | `test_billing_webhook_security.py` + `test_billing_integration.py` (12/12 PASS, gồm 5x concurrent delivery) + Live `POST /billing/webhook` fail-closed `503` khi thiếu `PAYMENT_WEBHOOK_SECRET`. |
| **`AUD-CRIT-03`** | `SafeUrlFetcher` kiểm tra DNS `socket.getaddrinfo()` nhưng để `httpx` phân giải DNS lần 2 theo hostname (DNS rebinding TOCTOU), không đặt `trust_env=False`, và `create_url()` không chặn IP private/obfuscated ngay lúc intake. | **RESOLVED** | `test_safe_url_fetcher_ssrf.py` (43/43 PASS: DNS rebinding, IPv4/IPv6/IPv4-mapped, multi-hop redirects, proxy env bypass, SNI & TLS `verify=True`). |
| **`AUD-CRIT-04`** | `evaluation/presentation/deps.py` không truyền `quota_port` cho Prove Mode (`generate`/`submit`) & Weekly Review → `AIExecutionManager` dùng `_NoOpQuotaAdapter`, không trừ `ai_quotas` và không ghi `ai_usage_logs`. | **RESOLVED** | `test_evaluation_quota_enforcement.py` (5/5 PASS trên PG16) + **Live Staging**: `used_calls` tăng `0 → 1`, `tokens_consumed=1008`, xác nhận bản ghi `ai_usage_logs` (`AI_REVIEW_MILESTONE`, `reservation_id`). |
| **`AUD-HIGH-10`** | `CreateStickyNoteUseCase` ghi `task_id` / `origin_session_id` không kiểm quyền sở hữu; `StartStudySessionUseCase` và `AddTaskDependencyUseCase` kiểm `roadmap_id` trước quyền sở hữu tạo `409` UUID existence oracle. | **RESOLVED** | `test_sticky_note_idor_isolation.py` (2/2 multi-user PG16 PASS) + **Live Staging**: User B gửi `POST /sessions/notes` với `task_id` User A → **`404 TASK_NOT_FOUND`**. |
| **`AUD-HIGH-03`** | `ConfirmPasswordResetUseCase` không inject `RefreshTokenRepositoryPort` và không gọi `revoke_all_for_user()`; `RefreshTokenUseCase` xoay vòng token không kiểm tra family còn hoạt động nguyên tử. | **RESOLVED** | `test_password_reset_security.py` (PASS, gồm concurrent refresh/reset Lua race) + **Live Staging**: replay refresh token cũ sau password reset → **`401`**. |
| **`AUD-HIGH-04`** | `POST /api/v1/auth/register` mở không điều kiện ở mọi môi trường (gồm `staging`/`production`), cho phép bỏ qua xác thực OTP. | **RESOLVED** | `test_register_otp_enforcement.py` (PASS) + **Live Staging**: `POST /api/v1/auth/register` trả **`403 REGISTRATION_OTP_REQUIRED`**; luồng OTP đăng ký UI (`auth.spec.ts` #1) PASS. |

*(Ghi chú quét toàn bộ LLM entrypoints cho `AUD-CRIT-04`: đã rà soát tất cả vị trí gọi `AIExecutionManager`/`LLMProviderPort`/`generate_structured` trong `planning` — `clarification_use_cases.py`, `milestone_use_cases.py`, `validation_gate`, `milestone_scoped_decomposer.py`, `learning_quality.py` — tất cả đều chạy dưới reservation hợp lệ. Chỉ 3 use case của `evaluation` bị thiếu `quota_port`.)*

---

## 2. Security Architecture Decisions

1. **Google SSO Dual-Path Hardening (`AUD-CRIT-01`)**: Vì frontend (`google-sso.service.ts`) hỗ trợ cả GSI `id_token` và `initTokenClient` `access_token`, cả hai nhánh đều được siết chặt thay vì phá vỡ luồng hiện có: `id_token` xác minh mật mã qua `verify_oauth2_token` + kiểm `iss`/`aud`/`azp`/`exp`/`email_verified is True`; `access_token` bắt buộc xác minh qua Google `tokeninfo` (`aud`/`azp == client_id`, `exp`, `email_verified`) trước khi gọi `userinfo` đối chiếu `sub` & `email`. Fail-closed nếu `google_client_id` rỗng.
2. **Webhook Signing & Locking (`AUD-CRIT-02`)**: Chữ ký HMAC-SHA256 dùng khóa riêng `PAYMENT_WEBHOOK_SECRET` (tách hoàn toàn khỏi JWT `SECRET_KEY`), ràng buộc `f"{timestamp}." + raw_body` với cửa sổ ±300s, validate nghiệp vụ chặt trong `SettlePaymentTransactionUseCase.execute()` kết hợp `SELECT ... FOR UPDATE`, tách biệt `execute_mock_confirm()` chỉ chạy trong `dev/test/local`.
3. **IP-Pinned Transport + SNI (`AUD-CRIT-03`)**: Resolve DNS 1 lần, kiểm mọi IP trả về (IPv4/IPv6/IPv4-mapped/6to4/teredo), pin IP vào `pinned_url`, giữ nguyên `Host` header + `extensions={"sni_hostname": ascii_host}` (ASCII `str` tương thích `httpx 0.28` + `anyio`) + `verify=True` + `trust_env=False`.
4. **Autonomous Quota Transactions (`AUD-CRIT-04`)**: `_AutonomousEvaluationQuotaFacade` bọc `create_quota_facade(session)` (từ `src.account.public_api`, giữ 0 vi phạm `lint-imports`) trong giao dịch ngắn riêng biệt để không giữ khóa `FOR UPDATE` xuyên suốt lệnh gọi LLM bên ngoài và tương thích với vòng đời đọc-rồi-ghi của `GenerateWeeklyReviewUseCase`.
5. **Atomic Refresh Family Check (`AUD-HIGH-03`)**: Bổ sung Redis Lua script `save_rotated_refresh_token` kiểm tra `SISMEMBER user_families:{user_id} family_id == 1` nguyên tử trước khi ghi refresh token xoay vòng, chặn race condition giữa password reset và concurrent refresh.

---

## 3. Files Changed

### Backend Source (19 files)
- `backend/src/account/infrastructure/security/google_auth_service.py`
- `backend/src/account/application/use_cases/auth/google_auth_use_case.py`
- `backend/src/account/application/ports/auth_ports.py`
- `backend/src/account/infrastructure/caching/redis_client.py`
- `backend/src/account/application/use_cases/auth/refresh_token_use_case.py`
- `backend/src/account/application/use_cases/auth/password_reset_otp_use_case.py`
- `backend/src/account/presentation/deps.py`
- `backend/src/account/presentation/auth_router.py`
- `backend/src/shared_kernel/config.py`
- `backend/src/account/domain/exceptions/billing.py`
- `backend/src/account/application/dtos/billing.py`
- `backend/src/account/application/ports/payment_ports.py`
- `backend/src/account/application/use_cases/billing.py`
- `backend/src/account/infrastructure/adapters/payment_provider_adapter.py`
- `backend/src/account/infrastructure/repositories/payment_transaction_repository.py`
- `backend/src/account/presentation/billing_router.py`
- `backend/src/account/infrastructure/adapters/quota_facade_adapter.py`
- `backend/src/planning/application/knowledge/safe_url_fetcher.py`
- `backend/src/planning/application/use_cases/knowledge_source_use_cases.py`
- `backend/src/evaluation/presentation/deps.py`
- `backend/src/evaluation/presentation/routers.py`
- `backend/src/execution/application/use_cases/session_use_cases.py`
- `backend/src/execution/application/use_cases/task_use_cases.py`
- `backend/src/execution/presentation/deps.py`

### Frontend Generated Types (1 file)
- `frontend/src/app/core/api/schema.d.ts` (tự động sinh qua `pnpm run api:gen`, 0 drift)

### Security Regression Tests Added / Updated (11 files)
- Added: `backend/tests/unit/account/test_google_auth_security.py`
- Added: `backend/tests/unit/account/test_password_reset_security.py`
- Added: `backend/tests/unit/account/test_register_otp_enforcement.py`
- Added: `backend/tests/unit/planning/test_safe_url_fetcher_ssrf.py` (43 tests)
- Added: `backend/tests/integration/account/test_billing_webhook_security.py` (11 tests)
- Added: `backend/tests/integration/evaluation/test_evaluation_quota_enforcement.py` (5 tests)
- Added: `backend/tests/integration/execution/test_sticky_note_idor_isolation.py` (2 multi-user tests)
- Updated: `backend/tests/test_google_auth.py`, `backend/tests/test_otp_auth.py`, `backend/tests/unit/account/test_profile_use_cases.py`, `backend/tests/integration/account/test_billing_integration.py`

---

## 4. Automated Regression & Live Runtime Verification

| Gate / Suite | Result | Details |
|---|---|---|
| `ruff check .` & `ruff format --check .` | **PASS** | 0 lỗi, 458 files formatted |
| `mypy --strict src` | **PASS** | 0 lỗi trên 323 source files |
| `lint-imports` | **PASS** | 5/5 contracts kept, 0 broken |
| `scripts/check-api-contract.sh` | **PASS** | 0 drift OpenAPI ↔ `schema.d.ts` |
| Backend Unit + AI Evals + Eval + Root | **PASS** | **794 passed, 1 skipped, 0 failed** |
| Backend Integration (Real PG16 + Redis 7) | **PASS** | **93 passed, 2 deselected, 0 failed** |
| Frontend `ng lint` / `ng test` / `ng build` | **PASS** | **649/649 Vitest PASS**, prod build 0 errors |
| Live Docker Staging (`http://127.0.0.1:3000`) | **6/6 PASS** | `AUD-HIGH-04` (`403`), `AUD-HIGH-03` (`401`), `AUD-HIGH-10` (`404`), `AUD-CRIT-02` (`503`), `AUD-CRIT-01` (`401`), `AUD-CRIT-04` (`used_calls 0→1` + PG `ai_usage_logs` verified) |
| Playwright E2E on Staging (`auth`, `p2b1`, `p2b2a`, `p2b2b`) | **3 PASS / 9 FAIL (Expected Staging Break)** | `auth.spec.ts` #1–#3 (OTP UI, Login, Wrong pass) **PASS**. 9 fail còn lại **100% do helper setup E2E gọi trực tiếp `POST /api/v1/auth/register`** vốn đã bị chặn `403` đúng yêu cầu `AUD-HIGH-04` trên `staging`. |

---

## 5. Breaking Changes & Deployment Considerations

1. **Billing Webhook Contract (`AUD-CRIT-02`)**:
   - Bắt buộc cấu hình biến môi trường mới **`PAYMENT_WEBHOOK_SECRET`** trước khi kích hoạt webhook thanh toán thật (thiếu sẽ fail-closed `503`).
   - Header **`X-Webhook-Timestamp`** (Unix epoch hoặc ISO8601 có timezone, sai lệch ≤ ±300s) là bắt buộc; chữ ký HMAC ký trên `f"{timestamp}." + raw_body`.
   - Payload bắt buộc có `event_type`, `status`, `amount_vnd`, `currency` (không còn default `status="PAID"`).
2. **Direct Registration Disabled in Staging/Production (`AUD-HIGH-04`)**:
   - `POST /api/v1/auth/register` trả `403 REGISTRATION_OTP_REQUIRED` khi `ENVIRONMENT` không thuộc `{development, dev, test, local}`.
   - Các helper setup Playwright E2E chạy trên `staging` (`auth.spec.ts` #4, `p2b1`, `p2b2a`, `p2b2b`) cần cập nhật dùng luồng `/register/request-otp` + Mailpit + `/register/verify-otp`.
3. **Database Migrations**: Không cần migration mới (giữ nguyên 36 bảng / Alembic head `0015_add_notifications_table`).

---

## 6. Residual Attack Surfaces & Items Deferred to P0B

Các bề mặt tấn công còn lại ngoài phạm vi P0A (chưa xử lý trong lượt này):
- **Short-lived Access Token Window (15m)**: Sau password reset hoặc logout, stateless JWT access token cũ vẫn hợp lệ tối đa 15 phút vì schema hiện tại chưa có cột `token_version` hoặc Redis JTI denylist (`AUD-LOW-04`).
- **P0B Security Blockers (đợt tiếp theo)**:
  - **`AUD-HIGH-01`**: CSRF protection (`Origin`/`Referer` allowlist middleware) & thu hẹp `refresh_token` cookie `Path=/api/v1/auth`.
  - **`AUD-HIGH-02`**: Refresh Token Rotation reuse detection (`used_token` marker gọi `revoke_family()`) & atomic `GETDEL` khi tiêu thụ token.
  - **`AUD-HIGH-05`**: Redis sliding-window rate limiting cho `/login`, `/register*`, `*/verify-otp`, `/export`, webhooks, và thay dict in-memory WebCal.
- **P1/P2/P3**: `AUD-HIGH-06..09`, `AUD-HIGH-11`, `AUD-MED-01..13`, `AUD-LOW-01..06` (giữ nguyên cho các đợt sau).
