# 03 — Independent Security & Cross-User Data Isolation Audit

- **Scope**: Phases 3 & 6 — Code-level forensic security review + Live two-user (`User A` vs `User B`) cross-tenant verification on Docker staging (`http://127.0.0.1:3000`).
- **Rule**: Mọi phát hiện đều gắn file/line cụ thể; các mục tái hiện được ở runtime đều ghi rõ HTTP status thực tế.

---

## 1. Cross-User Data Isolation Matrix (Live Test: User B → User A Resources)

| Resource / Endpoint | Expected (SRS / IDOR Rule) | Live Actual (User B) | Code Location | Verdict |
|---|---|---|---|---|
| `GET /api/v1/roadmaps/{user_a_roadmap_id}` | `404` | **404** (`ROADMAP_NOT_FOUND`) | `planning/infrastructure/repositories/` | **PASS** |
| `PATCH /api/v1/tasks/{user_a_task_id}` | `404` | **404** (`TASK_NOT_FOUND`) | `execution/application/use_cases/task_use_cases.py` | **PASS** |
| `POST /api/v1/sessions/notes` (`task_id = user_a_task_id`) | `404` | **201 Created** (tạo note `01a1fd95-...` gắn vào task User A!) | `execution/application/use_cases/session_use_cases.py:748-791` | **FAIL (`AUD-HIGH-10`)** |
| `GET /api/v1/evaluation/milestones/{user_a_mid}/proofs/latest` | `404` | **404** | `evaluation/application/use_cases/intelligence.py` | **PASS** |
| `GET /api/v1/roadmaps/jobs/{user_a_job_id}/stream` | `404` | **404** (`SSE_JOB_NOT_FOUND`) | `planning/presentation/routers.py:590` | **PASS** |
| `GET /api/v1/account/admin/status` (non-admin) | `403` | **403** (`Admin privileges required`) | `account/presentation/deps.py:311-320` | **PASS** |
| `GET /api/v1/feeds/{revoked_token}.ics` | `404` | **404** | `account/presentation/calendar_router.py:246` | **PASS** |
| `GET /api/v1/account/export` | Chỉ dữ liệu User A | **200** (12 khóa chỉ thuộc User A) | `account/presentation/routers.py:141` | **PASS** |
| `POST /api/v1/tasks/dependencies` / `sessions/start` (trộn foreign `task_id`) | `404` | Code trả `409` (UUID existence oracle) | `task_use_cases.py:962-970`, `session_use_cases.py:274-286` | **FAIL (`AUD-HIGH-10`)** |

---

## 2. Critical Security Findings

### `AUD-CRIT-01` — Google SSO Confused Deputy / Access Token Substitution
- **Files**: `backend/src/account/infrastructure/security/google_auth_service.py:53-77`, `backend/src/account/application/use_cases/auth/google_auth_use_case.py:49-65`
- **Evidence**: `verify_access_token()` chỉ gọi `oauth2/v3/userinfo` và **không kiểm tra audience (`aud`/`azp == settings.google_client_id`)** qua `tokeninfo`. Ngoài ra `google_auth_use_case.py:58` đặt `email_verified = payload.get("email_verified", True)` (fail-open) rồi tự động đăng nhập theo `email`.
- **Impact**: Kẻ tấn công lấy được Google `access_token` của nạn nhân từ bất kỳ app bên thứ ba nào (có scope `email`) có thể đăng nhập chiếm quyền tài khoản FocusFlow của nạn nhân.

### `AUD-CRIT-02` — Billing Webhook Blindly Marks Any Signed Payload as `PAID` & Reuses JWT Secret
- **Files**: `backend/src/account/presentation/billing_router.py:42-54,95-140`, `backend/src/account/application/use_cases/billing.py:178-227`
- **Evidence**:
  - `receive_billing_webhook()` chỉ kiểm tra chữ ký HMAC rồi gọi `SettlePaymentTransactionUseCase.execute()` mà **không kiểm tra `status == "PAID"`**, **không đối chiếu `amount_vnd == record.amount_vnd`**, **không kiểm tra `currency`**, và **không có cửa sổ chống replay (`X-Webhook-Timestamp`)**.
  - `_verify_webhook_hmac_signature()` (dòng 52) **dùng chung `settings.secret_key`** (chính là khóa ký JWT!).
- **Impact**: Webhook `FAILED`/`CANCELLED`/`REFUNDED` hoặc thanh toán thiếu tiền vẫn nâng cấp user lên `PREMIUM` + 100 credit. Lộ webhook secret đồng nghĩa lộ khóa ký JWT toàn hệ thống (cho phép giả mạo token `ADMIN`).

### `AUD-CRIT-03` — DNS Rebinding SSRF Bypass in Knowledge Source URL Fetcher
- **Files**: `backend/src/planning/application/knowledge/safe_url_fetcher.py:43-76`, `backend/src/planning/application/use_cases/knowledge_source_use_cases.py:96-104`
- **Evidence**: `_validate_public_destination()` phân giải DNS bằng `socket.getaddrinfo()` để kiểm tra `ip.is_global`, sau đó dòng 68 gọi `client.stream("GET", current, ...)` theo **hostname**, khiến `httpx` phân giải DNS lần 2 không qua kiểm duyệt.
- **Impact**: Domain có TTL=0 (DNS rebinding) có thể trỏ sang `169.254.169.254`, `127.0.0.1` hoặc internal Docker services (`redis:6379`, `postgres:5432`).

---

## 3. High Security Findings

### `AUD-HIGH-01` — Complete Absence of CSRF Protection & Over-Broad `refresh_token` Cookie Path
- **Files**: `backend/src/main.py:110-129`, `backend/src/account/presentation/auth_router.py:108-125`
- **Evidence**: Toàn bộ API xác thực bằng cookie `HttpOnly; SameSite=Lax; Path=/`, không có middleware kiểm tra `Origin`/`Referer` hay CSRF token. `refresh_token` đặt `Path=/` thay vì `Path=/api/v1/auth` nên bị gửi kèm mọi request.

### `AUD-HIGH-02` — Refresh Token Rotation (RTR) Missing Reuse Detection & Atomic Consumption
- **Files**: `backend/src/account/application/use_cases/auth/refresh_token_use_case.py:42-90`, `backend/src/account/infrastructure/caching/redis_client.py:70-86`
- **Evidence**: Đọc `get_refresh_token()` rồi `revoke_refresh_token()` (`DEL`) không nguyên tử (race condition khi refresh đồng thời); token đã dùng bị xóa hẳn nên replay token cũ chỉ trả `InvalidTokenError` mà **không gọi `revoke_family(family_id)`** (vi phạm ADR-008). Lỗi Redis ở `save_refresh_token()` bị nuốt im (dòng 84-89).

### `AUD-HIGH-03` — Password Reset Does Not Revoke Active Refresh Tokens (LIVE REPRODUCED)
- **Files**: `backend/src/account/application/use_cases/auth/password_reset_otp_use_case.py:98-144`, `backend/src/account/presentation/deps.py:428-437`
- **Live Reproduction**: User B hoàn tất `password-reset/verify-otp` (200) & `confirm` (200), sau đó dùng lại `refresh_token` cũ gọi `POST /api/v1/auth/refresh` → nhận **`200 OK`** và `access_token` mới. `ConfirmPasswordResetUseCase` không được inject `RefreshTokenRepositoryPort`.

### `AUD-HIGH-04` — Direct Registration Bypasses OTP in All Environments (LIVE REPRODUCED)
- **Files**: `backend/src/account/presentation/auth_router.py:209-261`
- **Live Reproduction**: `POST /api/v1/auth/register` trả **`201 Created`** trong môi trường `staging` (`DEBUG=false`) mà không cần xác thực OTP, cho phép đăng ký hàng loạt tài khoản chiếm email hoặc khai thác free AI quota.

### `AUD-HIGH-05` — Missing Rate Limiting & Unbounded In-Memory WebCal Bucket
- **Files**: `auth_router.py:89-499`, `routers.py:135-149`, `billing_router.py:95-140`, `webhook_router.py:18-82`, `calendar_router.py:56-83`
- **Evidence**: Chỉ có cooldown 60s cho OTP request/resend và dict in-memory cho WebCal. **Không có rate limit** trên `/login` (không có account lockout), `/register`, `/google`, `/refresh`, `*/verify-otp`, `/export`, `/billing/webhook`, `/calendar/webhooks/google`. `_webcal_rate_limiter_buckets` (`calendar_router.py:58`) là dict không giới hạn kích thước → nguy cơ OOM DoS nếu gửi token ngẫu nhiên.

### `AUD-HIGH-06` — File Upload Extension-Only Validation & Uncleaned `/tmp` Storage
- **Files**: `backend/src/planning/application/use_cases/knowledge_source_use_cases.py:62-94,146-225`, `backend/src/shared_kernel/config.py:130`
- **Evidence**: Chỉ kiểm tra đuôi file (`pdf`, `docx`, `txt`), không kiểm tra magic bytes / MIME; lưu tại `/tmp/focusflow-knowledge` (world-writable) và không xóa file sau khi ingest hoặc lỗi.

### `AUD-HIGH-10` — Cross-User `task_id` IDOR on Sticky Note Creation (LIVE REPRODUCED)
- **Files**: `backend/src/execution/application/use_cases/session_use_cases.py:748-791`
- **Live Reproduction**: User B gọi `POST /api/v1/sessions/notes` với `task_id` thuộc User A → **`201 Created`**. Ngoài ra `AddTaskDependencyUseCase` (`task_use_cases.py:967`) và `StartStudySessionUseCase` (`session_use_cases.py:281`) trả `409` thay vì `404` khi trộn foreign `task_id`.

---

## 4. Medium & Low Security Findings

- **`AUD-MED-01` (Account Enumeration — LIVE REPRODUCED)**: `POST /api/v1/auth/password-reset/request-otp` (`password_reset_otp_use_case.py:39-59`) trả 2 chuỗi thông báo tiếng Việt khác nhau và chỉ áp dụng 429 cooldown cho email tồn tại.
- **`AUD-MED-02` (Non-Atomic OTP/Reset Token)**: `otp_repository.py:84-130` kiểm tra/tăng `attempts` và `consume_reset_token()` không nguyên tử (`GET` rồi `DELETE` thay vì `GETDEL`/Lua).
- **`AUD-MED-03` (Access Token in JSON Body — LIVE REPRODUCED)**: `auth_router.py:127-494` trả `access_token` trong JSON body bên cạnh cookie `HttpOnly`, làm giảm hiệu quả cô lập XSS.
- **`AUD-MED-04` (Unauthenticated `/api/health` Info Leak — LIVE REPRODUCED)**: `main.py:146-183` công khai `environment`, `email_host`, `secret_key_is_default`, `ai_gateway.base_url` (`http://host.docker.internal:8045`), danh sách model, và cho phép `?probe_ai=true` không xác thực.
- **`AUD-MED-05` (Google Calendar Webhook Null Token)**: `webhook_router.py:50-61` bỏ qua xác thực `X-Goog-Channel-Token` nếu `channel_token_hash` là `None`.
- **`AUD-MED-06` (PII/Secret Logging Gaps)**: `shared_kernel/logging.py:9-35` chỉ áp dụng cho `structlog` top-level; `email_service.py:126-189` dùng stdlib `logging` và ghi `to_email` ở mức INFO/ERROR.
- **`AUD-LOW-01..04`**: Cho phép default `secret_key` ở `staging` & không validate Fernet key lúc startup (`config.py:213-225`); phản chiếu raw exception vào OAuth redirect URL (`calendar_router.py:138-142`); rò rỉ `httpx.AsyncClient` chưa đóng (`handle_google_calendar_oauth_callback_use_case.py:89-120`); logout không có JTI denylist cho access token 15m (`auth_router.py:521-545`).

---

## 5. Verified Strong Security Controls

- **Password Hashing**: Argon2id qua `pwdlib` (`password_hasher.py:1-17`).
- **Google Calendar OAuth State**: HMAC-SHA256 + user binding + TTL + Redis `GETDEL` one-time nonce + `sanitize_return_to()` + Fernet encryption cho refresh token.
- **WebCal Token Security**: Chỉ lưu SHA-256 hash; revoke trả `404`; header `Cache-Control: no-store, private`, `Referrer-Policy: no-referrer`, `X-Content-Type-Options: nosniff`.
- **Frontend Hygiene**: Không lưu token trong `localStorage`/`sessionStorage`; `withCredentials: true` trên `HttpClient` và `EventSource`; whitelist chặt YouTube/Spotify trước `bypassSecurityTrustResourceUrl`.
