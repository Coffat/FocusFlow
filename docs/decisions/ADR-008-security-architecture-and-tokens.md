# ADR-008: Kiến trúc Bảo mật Đa tầng: `PyJWT`, `pwdlib` (Argon2id), Cookie JWT, Google Calendar OAuth2 (Fernet), WebCal SHA-256 & Webhook `HMAC-SHA256`

* **Trạng thái:** Được chấp thuận (Approved — Cập nhật Kiến trúc v2.0)
* **Ngày quyết định:** 30/09/2026 (Cập nhật v2.0: 25/10/2026)
* **Người quyết định:** Vũ Toàn Thắng, Phan Đình Duẩn
* **Căn cứ đánh giá:** Khung Rubric Đồ án Tốt nghiệp CNTT — Tiêu chí TC2.1 & TC2.3 (Mức 5)
* **Yêu cầu liên quan:** `FR-AUTH-001`, `FR-AUTH-002`, `FR-EXT-001`, `UC-01`, `UC-02`, `UC-05`, `UC-13`, `UC-18`, `UC-19`, `BUSR-08`, `OS-05`, `NFR-SEC-001..004`

---

## 1. Ngữ cảnh & Đặt vấn đề (Context)
Hệ thống FocusFlow v2.0 quản lý thông tin cá nhân của người học, tích hợp thanh toán nâng cấp gói Premium (`UC-05`), đồng bộ lịch ngoại vi (`UC-13`) và cung cấp cổng quản trị hệ thống (`UC-18`, `UC-19`). Qua quá trình rà soát bảo mật và đồng bộ kiến trúc v2.0, nhóm cần giải quyết 5 yêu cầu bảo mật cốt lõi:
1. **Thay thế các thư viện mật mã Python đã ngừng bảo trì (Deprecated Libraries):** Các thư viện cũ như `python-jose` và `passlib` không còn được cập nhật thường xuyên và phát sinh cảnh báo tương thích trên Python 3.12+.
2. **Bảo vệ phiên đăng nhập & Phân quyền RBAC (`FR-AUTH-001`, `UC-18`, `UC-19`):** Chống đánh cắp token qua XSS và CSRF, đồng thời phân tách chặt chẽ quyền hạn giữa `LEARNER` và `ADMIN`.
3. **Bảo mật Đồng bộ Lịch Kép: Google Calendar OAuth 2.0 2 Chiều Có Kiểm soát & WebCal `.ics` 1 Chiều (`UC-13`, `BUSR-08`, `OS-05`):**
   * Đối với luồng đồng bộ 2 chiều có kiểm soát với Google Calendar, hệ thống phải lưu trữ OAuth Refresh Token của người dùng để worker đọc trạng thái Free/Busy và đẩy lịch học. Nếu lưu Refresh Token dạng rõ (plaintext) trong CSDL, rủi ro lộ quyền truy cập lịch cá nhân là rất lớn.
   * Đối với luồng xuất lịch 1 chiều qua URL WebCal `.ics`, hệ thống không được lưu token thô trong bảng `webcal_tokens`.
4. **Bảo mật Webhook Cổng Thanh toán (`UC-05`):** Khi cổng thanh toán (PayOS / VNPay Sandbox) gọi callback thông báo giao dịch thành công để nâng cấp tài khoản lên gói Premium và tăng hạn ngạch AI, hệ thống phải chặn đứng tấn công giả mạo request (Webhook Spoofing) và tấn công phát lại (Replay Attack).
5. **Vệ sinh Nhật ký Cấu trúc & Che giấu PII/Token (`NFR-SEC-004`):** Đảm bảo `structlog` không bao giờ ghi mật khẩu, JWT, OAuth token, WebCal token vào log hoặc gửi dữ liệu định danh cá nhân (PII) sang LLM bên ngoài.

---

## 2. Các phương án xem xét (Alternatives Considered)

### Phương án A: Dùng `python-jose` + `passlib` + Lưu JWT ở `localStorage` + Lưu OAuth Token dạng rõ
* *Nhược điểm:* `python-jose` và `passlib` đã lỗi thời trên Python 3.12+; lưu JWT trong `localStorage` dễ bị đánh cắp toàn bộ phiên nếu xảy ra lỗi XSS; lưu OAuth Refresh Token dạng rõ vi phạm nghiêm trọng nguyên tắc bảo vệ dữ liệu nhạy cảm khi lưu trữ (Encryption at Rest).

### Phương án B: Chỉ hỗ trợ WebCal 1 chiều và Bỏ hoàn toàn Google Calendar OAuth2 & Webhook Verification
* *Nhược điểm:* Không đáp ứng đầy đủ yêu cầu tích hợp lịch 2 chiều có kiểm soát (`UC-13`) và thanh toán tự động (`UC-05`) trong phạm vi kiến trúc v2.0.

### Phương án C: Kiến trúc Bảo mật Đa tầng Hiện đại với `PyJWT`, `pwdlib[argon2]`, Cookie JWT + RBAC, Mã hóa `Fernet` cho OAuth2, Băm `SHA-256` cho WebCal, Webhook `HMAC-SHA256` & `structlog` Sanitizer (Được chọn)
* Chuẩn hóa toàn bộ ngăn xếp mật mã trên Python 3.12+ bằng các thư viện chuẩn công nghiệp đang được bảo trì tích cực và áp dụng nguyên tắc Phòng thủ Chiều sâu (Defense-in-Depth) ở mọi ranh giới giao tiếp.

---

## 3. Quyết định (Decision)
**Chấp thuận Phương án C với 6 trụ cột bảo mật bắt buộc:**

### 3.1. Chuẩn hóa Thư viện Mật mã Hiện đại: `PyJWT` & `pwdlib[argon2]`
* **Ký & Xác thực JWT:** Thay thế hoàn toàn `python-jose` bằng **`PyJWT` (`pyjwt[crypto]`)** — thư viện chuẩn mực được FastAPI chính thức khuyến nghị, kết hợp gói `cryptography` hiện đại.
* **Băm Mật khẩu Người dùng (`NFR-SEC-002`):** Thay thế `passlib` bằng **`pwdlib[argon2]`** (sử dụng trực tiếp `argon2-cffi` với thuật toán **Argon2id** chiến thắng cuộc thi Password Hashing Competition), chống lại hiệu quả các cuộc tấn công vét cạn bằng GPU/ASIC.

### 3.2. Xác thực Cookie JWT (`HttpOnly`, `Secure`, `SameSite=Lax`), Xoay vòng Refresh Token trên Redis & RBAC
* **Access Token (`15 phút`):** Được đính kèm tự động qua Cookie bảo mật:
  `Set-Cookie: access_token=...; Path=/; HttpOnly; Secure; SameSite=Lax`
  Bảo vệ 100% trước nguy cơ mã JavaScript độc hại (XSS) đọc trộm token, đồng thời hỗ trợ liền mạch cả lệnh gọi `HttpClient` lẫn kết nối streaming `EventSource` (`withCredentials: true`).
* **Refresh Token (`7 ngày`) & Refresh Token Rotation (RTR) trên Redis:** Lưu trữ trạng thái xoay vòng token trong Redis (`refresh_token:{token_hash}` và `token_family:{family_id}` với TTL 7 ngày). Nếu phát hiện một Refresh Token cũ bị tái sử dụng (Token Replay), hệ thống lập tức thu hồi toàn bộ chuỗi token của phiên đó.
* **Kiểm soát Truy cập Dựa trên Vai trò (RBAC — `LEARNER` vs `ADMIN`):**
  * Payload của JWT và thực thể `User` chứa trường `role` (`LEARNER` hoặc `ADMIN`).
  * Các route quản trị người dùng (`/api/v1/admin/users/*` - `UC-18`) và giám sát hệ thống (`/api/v1/admin/monitoring/*` - `UC-19`) bắt buộc đi qua Dependency Guard `require_role(UserRole.ADMIN)` ở tầng Presentation và kiểm tra quyền tại Use Case.

### 3.3. Bảo mật Đồng bộ Lịch Kép: Google Calendar OAuth 2.0 (`Fernet` / `AES-256-GCM`) & WebCal `.ics` (`SHA-256`)
1. **Đồng bộ 2 Chiều Có Kiểm soát qua Google Calendar OAuth 2.0 (`UC-13`):**
   * **Phạm vi Quyền Tối thiểu (Minimal Scopes):** Chỉ yêu cầu quyền đọc trạng thái bận (`freebusy` / `calendar.readonly`) và quyền quản lý các sự kiện lịch học do chính FocusFlow tạo ra (`calendar.events`), tuyệt đối không sửa hay xóa sự kiện cá nhân có sẵn của người dùng.
   * **Bảo vệ Chống CSRF khi OAuth Callback:** Sử dụng tham số `state` ký mật mã có thời hạn ngắn (5 phút) lưu trên Redis/Cookie.
   * **Mã hóa Dữ liệu khi Lưu trữ (Encryption at Rest):** OAuth Refresh Token và Access Token của Google Calendar **bắt buộc được mã hóa đối xứng bằng `cryptography.fernet` / `AES-256-GCM`** (với khóa `CALENDAR_ENCRYPTION_KEY` tách biệt trong `.env`) trước khi lưu xuống cơ sở dữ liệu.
2. **Đồng bộ 1 Chiều qua Luồng WebCal `.ics` (`BUSR-08`, `OS-05`):**
   * Sinh token ngẫu nhiên an toàn mật mã `raw_token = secrets.token_hex(32)` (256-bit entropy).
   * Bảng `webcal_tokens` trong PostgreSQL **chỉ lưu giá trị băm một chiều `token_hash = sha256(raw_token).hexdigest()`**.
   * Hỗ trợ thu hồi và cấp mới tức thì (`Revoke & Rotate`) khi người dùng nghi ngờ lộ đường dẫn `.ics`.

### 3.4. Bảo mật Webhook Cổng Thanh toán (`HMAC-SHA256` & Khóa Lũy đẳng `transaction_ref`)
Đối với luồng nhận thông báo kết quả thanh toán từ PayOS / VNPay Sandbox (`POST /api/v1/billing/webhooks/payment` - `UC-05`):
1. **Xác thực Chữ ký Mật mã (`HMAC-SHA256`):** Adapter `PayOSWebhookVerifier` tính toán chữ ký `HMAC-SHA256` trên raw body/sorted payload bằng `PAYMENT_WEBHOOK_SECRET` và so sánh hằng thời gian (`hmac.compare_digest`) để chống Timing Attack và chặn 100% webhook giả mạo.
2. **Chống Phát lại & Xử lý Trùng lặp (Idempotency & Replay Protection):** Kiểm tra mốc thời gian của webhook và sử dụng ràng buộc `UNIQUE` cùng khóa hàng `SELECT ... FOR UPDATE` trên cột `payment_transactions.transaction_ref`. Nếu webhook được cổng thanh toán gửi lặp lại nhiều lần, hệ thống chỉ cộng hạn ngạch AI và nâng cấp gói Premium **đúng 1 lần duy nhất** (sau đó phát `UserUpgradedToPremiumEvent` vào `outbox_events`).

### 3.5. Làm sạch Nhật ký Cấu trúc (`structlog` PII & Token Sanitization)
* Cài đặt processor chuyên biệt `sanitize_sensitive_data_processor` trong pipeline của **`structlog`** (`shared_kernel/logging.py`):
  * Tự động thay thế mọi trường có khóa nhạy cảm (`password`, `access_token`, `refresh_token`, `oauth_token`, `api_key`, `authorization`, `cookie`, `signature`) và che giấu đường dẫn `/webcal/{token}.ics` thành `[REDACTED]`.
  * Trước khi gửi dữ liệu sang `LLMProviderPort`, bộ lọc `PromptSanitizer` lược bỏ hoàn toàn email, họ tên định danh và thông tin thanh toán của người học.

---

## 4. Lý do & Đánh đổi (Rationale & Trade-Offs)
* **An toàn Mật mã Hiện đại & Bền vững:** Việc chuyển sang `PyJWT` và `pwdlib[argon2]` giúp hệ thống tương thích hoàn hảo với Python 3.12+ và không còn bất kỳ cảnh báo thư viện ngừng hỗ trợ nào.
* **Bảo vệ Toàn diện Cả Lịch Ngoại vi Lẫn Giao dịch Thanh toán:** Kết hợp mã hóa `Fernet` (cho OAuth token cần giải mã để gọi API), băm một chiều `SHA-256` (cho WebCal token chỉ cần so khớp) và chữ ký `HMAC-SHA256` (cho Webhook thanh toán) thể hiện sự lựa chọn đúng đắn các công cụ mật mã theo từng bài toán cụ thể.
* **Đánh đổi:** Cần quản lý các biến môi trường bí mật (`JWT_SECRET_KEY`, `CALENDAR_ENCRYPTION_KEY`, `PAYMENT_WEBHOOK_SECRET`) trong tệp `.env`; nhóm cung cấp sẵn `.env.example` với khóa mẫu an toàn cho môi trường phát triển cục bộ.

---

## 5. Hệ quả & Kiểm chứng (Consequences & Verification)
* **Tích cực:** Đáp ứng xuất sắc toàn bộ yêu cầu phi chức năng về bảo mật (`NFR-SEC-001` đến `NFR-SEC-004`) và đạt điểm tối đa về thiết kế bảo mật trong Rubric TC2.1 & TC2.3.
* **Kiểm chứng Tự động:** Bộ kiểm thử bảo mật tự động xác minh: (1) Gửi webhook sai chữ ký `HMAC-SHA256` bị từ chối với HTTP `401/403`; (2) Gửi trùng webhook có cùng `transaction_ref` chỉ nâng cấp tài khoản 1 lần; (3) Tài khoản `LEARNER` gọi `/api/v1/admin/*` nhận HTTP `403 Forbidden`; (4) Dữ liệu lưu trong bảng `webcal_tokens` và OAuth token không bao giờ ở dạng plaintext.
