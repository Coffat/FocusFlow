# 10 — P0B Auth Security Remediation Report (FocusFlow)

- **Branch**: `fix/p0b-auth-security-remediation` (tạo từ `fix/p0a-security-remediation`, bảo toàn toàn bộ thay đổi P0A)
- **Scope**: P0A QA Regression Closure + `AUD-HIGH-01` (CSRF Protection) + `AUD-HIGH-02` (Atomic Refresh Token Rotation & Reuse Detection) + `AUD-HIGH-05` (Distributed Redis Rate Limiting). Không mở rộng sang P1/P2.

---

## 1. P0A QA Closure Verdict — **PASS**

- **Root cause confirmed**: 100% trong số 9 Playwright E2E failures sau P0A đến từ các setup helper gọi trực tiếp `POST /api/v1/auth/register` (đã bị chặn `403 REGISTRATION_OTP_REQUIRED` trên `staging` theo `AUD-HIGH-04`).
- **Resolution**: Tạo helper dùng chung `frontend/e2e/helpers/otp-auth.helper.ts` thực thi luồng đăng ký OTP thật (`POST /auth/register/request-otp` → poll Mailpit `/api/v1/messages` → `POST /auth/register/verify-otp`, xóa email OTP đã tiêu thụ theo ID để không va chạm với forgot-password) và gửi `Origin` hợp lệ cho `APIRequestContext` setup calls (không chỉnh sửa browser `page` requests để giữ nguyên kiểm thử CSRF trình duyệt thật).
- **Evidence**: Toàn bộ **34/34 tests** thuộc 8 spec hiện đại/lõi PASS trên Docker staging sau P0A QA Closure (không thêm bypass backend, không xóa/skip test, không làm yếu assertion).

---

## 2. Findings Resolved / Partial / Blocked

| Finding ID | Scope | Status | Verification Evidence |
|---|---|---|---|
| **P0A QA Closure** | `frontend/e2e/*` | **RESOLVED** | 34/34 core E2E tests PASS trên staging với OTP Mailpit thật (0 lời gọi `/auth/register` còn lại). |
| **`AUD-HIGH-01`** | CSRF Protection & Cookie Path | **RESOLVED** | 15/15 CSRF unit+integration tests PASS + Live staging: missing/evil `Origin` → `403 CSRF_VALIDATION_FAILED`, trusted `Origin` → `200`, webhook không cookie → `503` (không bị chặn CSRF), `refresh_token` đặt `Path=/api/v1/auth`. |
| **`AUD-HIGH-02`** | Atomic Refresh Token Rotation & Reuse Detection | **RESOLVED** | 17/17 BE unit+real-Redis integration tests + 7/7 FE `authInterceptor` tests PASS + Live staging: rotate `200`, replay token cũ → `401` + thu hồi toàn bộ family (token xoay vòng mới `refresh_token_2` cũng trả `401`), Session B độc lập vẫn rotate `200`. |
| **`AUD-HIGH-05`** | Distributed Redis Rate Limiting | **RESOLVED** | 24/24 core unit+Redis integration tests + 6/6 endpoint integration tests PASS + Live staging: lần đăng nhập sai thứ 11 → `429 RATE_LIMIT_EXCEEDED` (`Retry-After: 300`), tài khoản khác cùng IP vẫn trả `401` (không bị khóa oan); dict in-memory WebCal đã bị xóa hoàn toàn. |

---

## 3. CSRF Threat Model (`AUD-HIGH-01`)

- **Protected Surface**: Mọi request thay đổi trạng thái (`POST`, `PUT`, `PATCH`, `DELETE`) mang cookie `access_token` hoặc `refresh_token`, cùng các endpoint phát cookie phiên (`/api/v1/auth/{login,google,register,register/verify-otp,refresh,logout}` chống Login CSRF).
- **Enforcement (`CSRFProtectionMiddleware`, pure ASGI, zero body-buffering)**:
  1. Chặn cứng `Sec-Fetch-Site: cross-site` → `403 CSRF_VALIDATION_FAILED`.
  2. Kiểm tra `Origin` (hoặc `Referer` khi thiếu `Origin`) đối chiếu với allowlist chuẩn hóa từ cấu hình server (`settings.cors_origins` + `settings.frontend_url` + `settings.csrf_trusted_origins`); từ chối nhiều header trùng, `Origin: null`, hoặc thiếu cả `Origin` lẫn `Referer`.
  3. **Bỏ qua hoàn toàn** `Host`, `X-Forwarded-Host`, `X-Forwarded-Proto` do client gửi.
  4. CORS hardening (`main.py`): cấm `*` cùng `allow_credentials=True`; liệt kê tường minh `allow_methods`, `allow_headers`, `expose_headers`.
  5. Thu hẹp `refresh_token` cookie về `Path=/api/v1/auth` (bao phủ `/auth/refresh` & `/auth/logout`), đồng thời `/logout` xóa cả cookie legacy `Path=/`.
- **Exemptions (tối thiểu & có kiểm soát)**:
  - Safe methods (`GET`/`HEAD`/`OPTIONS`/`TRACE`): bảo toàn SSE stream, WebCal `.ics`, và Google OAuth `GET /callback` (dùng HMAC+Redis `GETDEL` state).
  - Bearer-only requests không mang auth cookie.
  - Provider webhooks xác thực bằng chữ ký riêng: `POST /api/v1/account/billing/webhook`, `POST /api/v1/calendar/webhooks/google`.

---

## 4. Refresh Token Lifecycle & Reuse Detection Evidence (`AUD-HIGH-02`)

- **Redis Data Model**:
  - `refresh_token:{sha256}` → `{user_id, family_id}` với `EX remaining_ttl`.
  - `used_refresh_token:{sha256}` → `{family_id, user_id, rotated_at, replacement_hash}` với `EX remaining_ttl` (bằng thời gian sống còn lại của family, không vượt quá `refresh_token_expire_days * 86400`, đảm bảo phát hiện reuse suốt vòng đời phiên mà không rò rỉ bộ nhớ).
  - `token_family:{family_id}` → Set các hash trong phiên, `EX remaining_ttl` (không kéo dài thời hạn phiên ngoài policy).
  - `user_families:{user_id}` → Set các `family_id` đang hoạt động.
- **Atomic Lua Scripts (`redis_client.py`)**:
  - `_INSPECT_OR_REVOKE_REUSED_LUA`: kiểm tra active + `SISMEMBER user_families`; nếu token nằm trong `used_refresh_token:*` → lập tức thu hồi toàn bộ `token_family:{fam}` và trả `REUSE_DETECTED`.
  - `_ROTATE_REFRESH_TOKEN_ATOMIC_LUA`: chạy sau khi kiểm tra DB user/lock; kiểm tra lại `refresh_token:{old_hash}` & `SISMEMBER` nguyên tử (chống revive sau logout/password reset), tính `remaining_ttl = min(TTL(token), TTL(family), max_ttl)`, xóa `old_hash`, ghi `used_refresh_token:{old_hash}`, ghi `refresh_token:{new_hash}` trong cùng 1 bước nguyên tử.
  - `_REVOKE_TOKEN_AND_FAMILY_LUA`: logout thu hồi nguyên tử toàn bộ family phiên hiện tại mà không ảnh hưởng các phiên khác của cùng user.
- **Concurrency & Grace-Window Trade-off**:
  - Chọn **strict single-use (`grace_seconds = 0`)**: không lưu plaintext refresh token trong Redis (nếu cấp lại token cũ trong grace window sẽ bắt buộc lưu plaintext hoặc mã hóa thuận nghịch, làm tăng rủi ro).
  - Chống false-positive trên trình duyệt: Angular `authInterceptor` serialize các lỗi 401 đồng thời qua single-flight (`isRefreshing` + `refreshResultSubject`), bổ sung `AUTH_RETRY_ATTEMPTED` retry-once guard và `finalize()` cleanup.
- **Live Staging Reuse Evidence**:
  - Rotate `refresh_token_1` → `200` (`refresh_token_2`).
  - Replay `refresh_token_1` → `401 ("Refresh token reuse detected. Session family has been revoked.")`.
  - Dùng `refresh_token_2` → `401` (xác nhận cả family đã bị vô hiệu).
  - Rotate `refresh_token_b` (phiên độc lập khác) → `200` (xác nhận cô lập liên phiên).

---

## 5. Distributed Rate Limit Policy Matrix & Redis Failure Semantics (`AUD-HIGH-05`)

Engine: `backend/src/shared_kernel/infrastructure/security/rate_limiter.py` (Lua `INCR` + `PEXPIRE` on hit 1 + defensive `PTTL < 0` healing; cấu hình qua `RATE_LIMIT_ENABLED`, `RATE_LIMIT_TRUSTED_PROXIES`, `RATE_LIMIT_OVERRIDES_JSON`; trích xuất IP từ `X-Forwarded-For` phải-sang-trái chỉ khi peer nằm trong `trusted_proxies`; băm SHA-256 cho email/token).

| Policy | Limit / Window | Key Scope | Failure Mode (Redis Down) | Protected Endpoints |
|---|---:|---|---|---|
| `auth_login_ip` | 60 / 60s | Client IP | Fail-open (`degraded=True`) | `POST /api/v1/auth/login` |
| `auth_login_account` | 10 / 300s | `hash_email(email)` | **Fail-closed (`503`)** | `POST /api/v1/auth/login` |
| `auth_register_otp_ip` | 60 / 300s | Client IP | **Fail-closed (`503`)** | `POST /auth/register`, `/register/request-otp`, `/register/resend-otp` |
| `auth_verify_otp_ip` | 60 / 300s | Client IP | **Fail-closed (`503`)** | `POST /api/v1/auth/register/verify-otp` |
| `auth_verify_otp_account` | 8 / 300s | `hash_email(email)` | **Fail-closed (`503`)** | `POST /api/v1/auth/register/verify-otp` |
| `auth_password_reset_ip` | 60 / 300s | Client IP | **Fail-closed (`503`)** | `POST /password-reset/{request-otp,verify-otp,confirm}` |
| `auth_password_reset_account` | 5 / 300s | `hash_email(email)` | **Fail-closed (`503`)** | `POST /password-reset/{request-otp,verify-otp,confirm}` |
| `auth_refresh_ip` | 120 / 60s | Client IP | Fail-open (`degraded=True`) | `POST /api/v1/auth/refresh` |
| `auth_google_ip` | 60 / 60s | Client IP | Fail-open (`degraded=True`) | `POST /api/v1/auth/google` |
| `account_export_user` | 5 / 3600s | `user_id` | Fail-open (`degraded=True`) | `GET /api/v1/account/export` |
| `webcal_feed_token` | 60 / 300s | `hash_token(token)` | Fail-open (`degraded=True`) | `GET /api/v1/feeds/{token}.ics` *(xóa dict in-memory)* |
| `calendar_oauth_init_user` | 15 / 300s | `user_id` | Fail-open (`degraded=True`) | `POST /api/v1/account/calendar/google/authorize` |
| `knowledge_upload_user` | 20 / 300s | `user_id` | Fail-open (`degraded=True`) | `POST /planning/goals/{id}/knowledge-sources/{files,urls}` |
| `billing_webhook_ip` | 120 / 60s | Client IP | Fail-open (`degraded=True`) | `POST /api/v1/account/billing/webhook` |
| `calendar_webhook_ip` | 120 / 60s | Client IP | Fail-open (`degraded=True`) | `POST /api/v1/calendar/webhooks/google` |

- **Redis Failure Semantics**:
  - `RateLimitExceededError` → HTTP `429` (`code: "RATE_LIMIT_EXCEEDED"`, kèm `Retry-After`, `X-RateLimit-Limit`, `X-RateLimit-Remaining`), không lộ email có tồn tại hay không.
  - `RateLimiterUnavailableError` (khi `fail_closed=True`) → HTTP `503` (`code: "RATE_LIMITER_UNAVAILABLE"`).
  - `SessionStoreUnavailableError` (RTR / auth session Redis lỗi) → HTTP `503` (`code: "SESSION_STORE_UNAVAILABLE"`), tách biệt hoàn toàn khỏi lỗi xác thực `401`.

---

## 6. Files Changed

- **Backend Core & Security**:
  - `backend/src/shared_kernel/config.py`
  - `backend/src/shared_kernel/infrastructure/security/csrf_middleware.py` *(new)*
  - `backend/src/shared_kernel/infrastructure/security/rate_limiter.py` *(new)*
  - `backend/src/main.py`
  - `backend/src/account/domain/exceptions/auth_exceptions.py`
  - `backend/src/account/application/ports/auth_ports.py`
  - `backend/src/account/infrastructure/caching/redis_client.py`
  - `backend/src/account/application/use_cases/auth/refresh_token_use_case.py`
  - `backend/src/account/presentation/auth_router.py`
  - `backend/src/account/presentation/routers.py`
  - `backend/src/account/presentation/calendar_router.py`
  - `backend/src/account/presentation/billing_router.py`
  - `backend/src/account/presentation/webhook_router.py`
  - `backend/src/planning/presentation/routers.py`
- **Frontend**:
  - `frontend/src/app/core/interceptors/auth.interceptor.ts` & `auth.interceptor.spec.ts`
  - `frontend/e2e/helpers/otp-auth.helper.ts` *(new)* + 9 spec files trong `frontend/e2e/` (migrated setup sang OTP thật + CSRF `Origin` cho `APIRequestContext`).
- **Backend Tests**:
  - New: `test_csrf_middleware.py`, `test_csrf_protection_integration.py`, `test_refresh_token_rotation.py`, `test_refresh_token_rotation_integration.py`, `test_rate_limiter_unit.py`, `test_distributed_rate_limiter.py`, `test_endpoint_rate_limiting_integration.py`.
  - Updated: `test_auth.py`, `test_otp_auth.py`, `test_google_auth.py`, `test_auth_cookie_and_jwt_hardening.py`, `test_calendar_two_way_sync.py`, `test_webcal_integration.py`.

---

## 7. Security Regression & Full E2E Results

| Gate / Suite | Result | Details |
|---|---|---|
| Backend `ruff check` / `ruff format --check` | **PASS** | 467 files formatted, 0 issues |
| Backend `mypy --strict src` | **PASS** | 0 issues across 325 source files |
| Backend `lint-imports` | **PASS** | 5/5 contracts kept, 0 broken |
| Backend Unit + AI Evals + Eval + Root | **PASS** | **831 passed, 1 skipped, 0 failed** |
| Backend Integration (Real PG16 + Redis 7) | **PASS** | **116 passed, 2 deselected, 0 failed** |
| OpenAPI Contract (`check-api-contract.sh`) | **PASS** | **0 drift** |
| Frontend `ng lint` / `ng test` / `ng build` | **PASS** | **652/652 Vitest PASS**, prod build 0 errors |
| Live Docker Staging (`verify_p0b_live.py`) | **12/12 PASS** | P0A non-regression, CSRF 403/200/webhook, RTR reuse + family revoke + cross-session isolation, Rate Limit 429 + `Retry-After` + account isolation |
| Full Playwright E2E (10 specs / 37 tests) | **34/34 Core PASS** (+1 transient flake re-run PASS) | `auth` (8/8), `availability` (2/2), `fit_capacity_scope_approval` (1/1), `p2b1` (1/1), `p2b2a` (3/3), `p2b2b` (4/4), `roadmap-dashboard-sync` (5/5) PASS; `p2a-data-consistency` 9/10 + Workflow 6 re-run PASS (1/1, 2.3s). **2 pre-existing P2 legacy failures (`AUD-MED-13`)**: `e2e_full_workflow.spec.ts` Test #1 (clarification vòng 2) & `signal_e2e_evidence.spec.ts` (selector cũ `.trailing-toggle-button`). |

---

## 8. Breaking Changes & Deployment Configuration Requirements

1. **CSRF Enforcement**: Mọi client trình duyệt hoặc script dùng cookie xác thực khi gọi `POST`/`PUT`/`PATCH`/`DELETE` bắt buộc có `Origin` hoặc `Referer` nằm trong `BACKEND_CORS_ORIGINS` / `FRONTEND_URL` / `CSRF_TRUSTED_ORIGINS`. Không chấp nhận `*` trong CORS/CSRF khi bật credentials.
2. **Refresh Cookie Path**: `refresh_token` chỉ gửi tới `/api/v1/auth/*` (`Path=/api/v1/auth`).
3. **Environment Variables mới cho Deployment**:
   - `CSRF_TRUSTED_ORIGINS` (tuỳ chọn, bổ sung origin tin cậy ngoài `BACKEND_CORS_ORIGINS` & `FRONTEND_URL`).
   - `RATE_LIMIT_ENABLED` (mặc định `true`).
   - `RATE_LIMIT_TRUSTED_PROXIES` (CIDR của reverse proxy/ingress tin cậy để đọc `X-Forwarded-For` an toàn).
   - `RATE_LIMIT_OVERRIDES_JSON` (tuỳ chọn JSON ghi đè ngưỡng limit/window theo môi trường).
4. **Redis Dependency**: Redis là bắt buộc cho RTR và rate-limit fail-closed; khi Redis gián đoạn, các endpoint OTP/login-account/password-reset/refresh trả `503` thay vì fail-open hoặc cấp cookie không lưu được.

---

## 9. Residual Risks & P1 Recommendations

### Residual Risks (Trung thực sau P0A + P0B)
- **Stateless Access Token 15m window (`AUD-LOW-04`)**: Chưa có `token_version` / JTI denylist cho access token ngắn hạn sau logout/password reset.
- **2-Tab Simultaneous Refresh Trade-off**: Nếu 2 tab khác nhau của cùng 1 trình duyệt hết hạn access token cùng thời điểm mili-giây và đồng thời gọi `/auth/refresh` với cùng 1 `refresh_token`, strict single-use sẽ phát hiện reuse và buộc đăng nhập lại (an toàn hơn nhưng có thể gây bất tiện hiếm gặp nếu không có `BroadcastChannel` đồng bộ giữa các tab).
- **Account Enumeration trên `password-reset/request-otp` (`AUD-MED-01`)**: Đã có rate limit đồng nhất, nhưng chuỗi thông báo vẫn còn khác nhau (xử lý ở P2).

### Next Steps — P1 Recommendations (Chưa triển khai trong lượt này)
1. `AUD-HIGH-06`: Magic-byte/MIME validation & dọn `/tmp` cho RAG upload.
2. `AUD-HIGH-07`: Sửa Outbox Relay (không silent-drop khi thiếu handler, rollback trước khi tăng `retry_count`, thêm `next_retry_at`).
3. `AUD-HIGH-08`: Bật AI Circuit Breaker mặc định cho cả Planning & Evaluation + fail-open an toàn khi mất Redis.
4. `AUD-HIGH-09`: Thay `NullPool` bằng `AsyncAdaptedQueuePool` + `command_timeout`.
5. `AUD-MED-12` & `AUD-HIGH-11`: Điều tra Prove Mode live grader fallback & chính thức feature-gate Billing (hoặc tích hợp live payment gateway) trước khi mở MVP Beta.
