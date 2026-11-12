# Bảo mật (Backend)

## 1. Xác thực & phiên
- `PyJWT[crypto]` ký JWT; `pwdlib[argon2]` băm mật khẩu (Argon2id). Cấm `python-jose`, `passlib`.
- Access token 15 phút, set cookie: `access_token=...; Path=/; HttpOnly; Secure; SameSite=Lax`. Hỗ trợ cả `HttpClient` lẫn `EventSource(withCredentials)`.
- Refresh token 7 ngày, **Refresh Token Rotation** trên Redis: khoá `refresh_token:{hash}` và `token_family:{family_id}` TTL 7 ngày. Dùng lại refresh token cũ ⇒ thu hồi toàn bộ family.
- Chỉ lưu **hash** refresh token trong Redis. Logout ⇒ xóa family.
- ADMIN: phiên tuyệt đối tối đa **8 giờ** (FR-ADM-001) — refresh không được kéo dài quá 8h kể từ lúc đăng nhập (lưu `session_started_at` trong family).
- CSRF: cookie `SameSite=Lax` + với endpoint đổi trạng thái chỉ chấp nhận `POST/PUT/PATCH/DELETE`; khi API và SPA cùng root domain (`app.` / `api.focusflow.vn`) Lax là đủ; không cho phép state-changing `GET`.

## 2. Phân quyền
- `role ∈ {LEARNER, ADMIN}` trong JWT và `User`. `require_role(UserRole.ADMIN)` ở presentation cho `/api/v1/admin/*`, đồng thời use case admin kiểm lại `actor.role`.
- Mọi thao tác Roadmap/Milestone/Task/Session/Proposal/Note: `resource.user_id == actor.id` (NFR-SEC-004). Không sở hữu ⇒ **404** (tránh lộ tồn tại). Viết test IDOR cho mỗi endpoint có `{id}`.
- Sự kiện an ninh phải phát ra **Structured Audit Stream** kèm actor, thời điểm, IP: truy cập RBAC trái phép, đăng nhập thất bại, chữ ký webhook sai, khóa/mở khóa tài khoản, đổi gói, chỉnh quota (BUSR-11).

## 3. Google Calendar OAuth2
- Scope tối thiểu: `calendar.freebusy`/`calendar.readonly` (đọc bận) + `calendar.events` (chỉ sự kiện do FocusFlow tạo). Tuyệt đối không sửa/xóa sự kiện cá nhân.
- Callback OAuth chống CSRF bằng `state` ký, TTL 5 phút (Redis/cookie).
- Access/Refresh token mã hóa `Fernet` (hoặc AES-256-GCM) bằng `CALENDAR_ENCRYPTION_KEY` (tách khỏi các khóa khác) **trước khi** ghi DB. Không bao giờ log.
- Chiều Inbound: chỉ đọc Free/Busy để trừ dung lượng rảnh. Chiều Outbound/WebCal/`.ics`: **chỉ xuất `OfficialSchedule`**, không bao giờ Proposal/Backlog.
- Có `LocalCalendarAdapter` cho chế độ offline.

## 4. WebCal `.ics`
- `raw = secrets.token_hex(32)` (64 ký tự hex). DB chỉ lưu `sha256(raw).hexdigest()` trong `webcal_tokens.token_hash`. Token thô trả cho client **một lần**. Reset ⇒ vô hiệu token cũ ngay (truy cập bằng token cũ → 401/404).
- Endpoint feed không dùng cookie; xác thực bằng token; so khớp hash (constant-time). URL chứa token **không** được vào access log (che `/webcal/{token}.ics` ⇒ `[REDACTED]`, cả ở log của reverse proxy).

## 5. Webhook thanh toán (UC-05)
`POST /api/v1/billing/webhooks/payment`:
1. Đọc **raw body**; tính `HMAC-SHA256` bằng `PAYMENT_WEBHOOK_SECRET`; so với chữ ký bằng `hmac.compare_digest` ⇒ sai ⇒ 401/403 + ghi audit.
2. Kiểm timestamp (chống replay ngoài cửa sổ cho phép).
3. `SELECT … FOR UPDATE` trên `payment_transactions` theo `transaction_ref` (UNIQUE). Đã `PAID` ⇒ trả 200 không làm gì. Lần đầu ⇒ `PAID`, nâng gói + cộng quota **đúng một lần**, phát `UserUpgradedToPremiumEvent` qua outbox.
4. Đơn có TTL 15 phút (`expires_at`), trạng thái cuối `PAID/FAILED/CANCELLED/EXPIRED`. Webhook đến cho đơn đã `EXPIRED` ⇒ xử lý theo chính sách đã thống nhất (mặc định: ghi nhận để đối soát UC-27, không tự nâng gói; hỏi người dùng nếu chưa có quy tắc).
5. Có `LocalMockPaymentAdapter` (sinh QR nội bộ + nút giả lập callback ký đúng HMAC) cho demo offline.

## 6. Log & bí mật
- `structlog` JSON; `correlation_id` qua middleware ASGI và header Taskiq. Processor `sanitize_sensitive_data_processor` che: `password, access_token, refresh_token, oauth_token, api_key, authorization, cookie, signature` và URL webcal.
- Secrets chỉ từ biến môi trường: `JWT_SECRET_KEY`, `CALENDAR_ENCRYPTION_KEY`, `PAYMENT_WEBHOOK_SECRET`, `LLM_API_KEY`, DB/Redis URL. Không commit; `.env.example` chỉ chứa giá trị mẫu cho dev. Secret scanner phải 0 cảnh báo (NFR-SEC-001).
- Không đưa thông tin nhạy cảm vào response lỗi hoặc prompt LLM.

## 7. Rate limit & chống lạm dụng
Rate limit lưu Redis cho: đăng nhập/đăng ký/quên mật khẩu, endpoint khởi tạo AI (ngoài quota), webhook. Phản hồi 429 có `Retry-After`.

## 8. Test bảo mật bắt buộc
Webhook sai chữ ký bị từ chối; trùng `transaction_ref` chỉ nâng cấp một lần; LEARNER gọi `/admin/*` ⇒ 403; IDOR trên từng resource; dữ liệu `webcal_tokens`/OAuth không plaintext; reuse refresh token ⇒ thu hồi family; log không chứa token.
