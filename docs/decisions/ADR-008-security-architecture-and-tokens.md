# ADR-008: Kiến trúc Bảo mật Đa tầng: Xác thực Cookie JWT SameSite, Băm Mật khẩu Argon2id và Bảo mật WebCal Token SHA-256

* **Trạng thái:** Được chấp thuận (Approved)
* **Ngày quyết định:** 30/09/2026 (Hoàn thiện hồ sơ: 07/10/2026)
* **Người quyết định:** Vũ Toàn Thắng (Lead BA / System Architect), Phan Đình Duẩn (Senior BA / Quality Lead)
* **Căn cứ đánh giá:** Khung Rubric Đồ án Tốt nghiệp CNTT — Tiêu chí TC2.1 & TC2.3 (Mức 5)
* **Yêu cầu liên quan:** FR-AUTH-001, FR-AUTH-002, FR-CALENDAR-001, FR-CALENDAR-002, BUSR-08, OS-05, NFR-SEC-001..004
* **Tài liệu đối chiếu:** `docs/srs/srs-v1.0.md`, `docs/architecture/system-architecture.md`, `docs/uml/sequence-diagrams.md`

---

## 1. Ngữ cảnh & Đặt vấn đề (Context)
FocusFlow là nền tảng web phục vụ việc học tập cá nhân, đòi hỏi các ranh giới bảo mật nghiêm ngặt nhằm bảo vệ dữ liệu người dùng và bí mật hệ thống:
1. **Rủi ro XSS & CSRF khi quản lý phiên:** Nếu lưu Access Token trong LocalStorage trình duyệt, mã độc XSS có thể đánh cắp phiên. Nếu lưu trong Cookie đơn thuần qua các domain khác nhau (Vercel vs Render), chính sách trình duyệt bên thứ ba (Third-Party Cookies) sẽ chặn truyền cookie.
2. **Bảo vệ mật khẩu người dùng (`NFR-SEC-002`):** Thuật toán băm mật khẩu cũ (như MD5, SHA-1, SHA-256 thuần) dễ bị tấn công vét cạn hoặc tấn công từ điển qua GPU/ASIC.
3. **Bảo mật luồng lịch ngoại vi WebCal RFC 5545 (`BUSR-08`, `OS-05`):** Người dùng tích hợp lịch học FocusFlow vào Google Calendar hoặc Apple Calendar qua URL HTTP GET công khai. Nếu để lộ token hoặc nếu cơ sở dữ liệu bị lộ, kẻ xấu có thể theo dõi toàn bộ lịch trình học tập cá nhân của người dùng.
4. **Bảo mật bí mật và nhật ký máy chủ (`NFR-SEC-001`, `NFR-SEC-004`):** Tuyệt đối không để lộ khóa API LLM ra client (*Zero Secret Leak*) và không ghi chuỗi token nhạy cảm ra access logs máy chủ.

---

## 2. Các phương án xem xét (Alternatives Considered)

### Phương án A: Token Bearer lưu LocalStorage + MD5/Bcrypt + Plaintext WebCal Token
* *Nhược điểm:* Dễ bị đánh cắp qua tấn công XSS; Bcrypt không có khả năng chống tấn công bộ nhớ bằng ASIC/FPGA tốt như Argon2id; nếu lưu token WebCal dạng văn bản thô (Plaintext) trong DB, sự cố lộ CSDL sẽ làm lộ toàn bộ URL lịch của mọi người dùng.

### Phương án B: OAuth 2.0 Google Calendar Two-Way Sync
* *Nhược điểm:* Đòi hỏi phải xin quyền truy cập Google Account (quyền đọc/ghi lịch), quy trình kiểm duyệt của Google rất phức tạp; vi phạm quy tắc `BUSR-08` (FocusFlow chỉ hỗ trợ đồng bộ 1 chiều bảo mật, không yêu cầu quyền tài khoản người dùng).

### Phương án C: Kiến trúc Bảo mật Đa tầng Defense-in-Depth (Được chọn)
* Áp dụng mô hình Cookie JWT chia sẻ Subdomain (`.focusflow.vn`) với các cờ bảo mật cao nhất (`HttpOnly`, `Secure`, `SameSite=Lax`).
* Băm mật khẩu bằng thuật toán đoạt giải PHC: **Argon2id**.
* Sinh token WebCal bằng CSPRN 32-byte hex (`secrets.token_hex(32)`), chỉ lưu bản băm **SHA-256** vào cơ sở dữ liệu (`OS-05`).
* Sử dụng `LogSanitizerMiddleware` che giấu token thành `[REDACTED]` trước khi ghi access logs (`NFR-SEC-004`).

---

## 3. Quyết định (Decision)
**Chấp thuận Phương án C:**
1. **Xác thực Phiên làm việc (Auth & JWT Lifecycle):**
   - **Access Token:** JWT thời hạn ngắn (**15 phút**), ký bằng khóa bí mật `SECRET_KEY` (chuỗi hex 64 ký tự), lưu trong Cookie:
     `Set-Cookie: access_token=...; Domain=.focusflow.vn; Path=/; HttpOnly; Secure; SameSite=Lax`
     Trình duyệt tự động đính kèm cookie trong các REST API và SSE `EventSource` (`withCredentials: true`), loại trừ 100% rủi ro XSS đánh cắp token.
   - **Refresh Token & Xoay vòng Token (RTR):** Chuỗi mật mã CSPRN 64 ký tự, thời hạn **7 ngày**, được lưu trữ và quản lý trạng thái thu hồi trong **Redis** (Key: `refresh_token:{token_hash}` kèm metadata `user_id`, `family_id` với TTL 7 ngày; kết hợp Set `token_family:{family_id}` hỗ trợ phát hiện tái sử dụng và thu hồi tức thì toàn bộ chuỗi token). Cơ chế này giữ cho CSDL quan hệ PostgreSQL 16 thuần khiết với 15 bảng nghiệp vụ lõi, không bị phân mảnh bởi dữ liệu token tạm thời có tần suất đọc/ghi và hết hạn liên tục.
2. **Băm Mật khẩu:** 100% mật khẩu được băm bằng thuật toán **Argon2id** (thư viện `argon2-cffi` trong Python).
3. **Bảo mật WebCal 1 Chiều RFC 5545:**
   - Khi người dùng kích hoạt, hệ thống sinh `raw_token = secrets.token_hex(32)`.
   - Cơ sở dữ liệu bảng `webcal_tokens` chỉ lưu `token_hash = sha256(raw_token).hexdigest()`. Tuyệt đối không lưu chuỗi thô.
   - Khi Google/Apple Calendar gửi request kéo lịch: `GET /api/v1/calendar/feed/{raw_token}.ics`, Backend băm `raw_token` và so khớp với `token_hash` trong DB.
   - Cơ chế thu hồi tức thì (Instant Revocation): Bấm [Reset Token] sẽ hủy kích hoạt token cũ ngay lập tức (`is_active = FALSE`).
4. **Vệ sinh Nhật ký & Bảo vệ Bí mật (Data Hygiene & Zero Secret Leak):**
   - `LogSanitizerMiddleware` lọc sạch chuỗi token WebCal khỏi access log máy chủ: `GET /api/v1/calendar/feed/[REDACTED].ics`.
   - `PromptSanitizer` loại bỏ định danh cá nhân (PII: Email, Họ tên thật, số điện thoại) trước khi gửi prompt sang Google Gemini API.
   - Toàn bộ `GEMINI_API_KEY`, `DATABASE_URL`, `SECRET_KEY` chỉ được truyền qua biến môi trường (.env được đưa vào .gitignore).

---

## 4. Lý do & Đánh đổi (Rationale & Trade-Offs)
* **Bảo vệ Tính Riêng tư Tối đa (Privacy by Design):** Ngay cả khi hacker có được bản sao lưu cơ sở dữ liệu PostgreSQL, họ không thể khôi phục mật khẩu (nhờ Argon2id) và không thể suy luận ra URL WebCal thực tế của người dùng (nhờ tính một chiều của SHA-256).
* **Trải nghiệm Đăng nhập Liền mạch (Seamless UX):** Cơ chế chia sẻ Root Domain `.focusflow.vn` cho phép Next.js frontend tại `app.focusflow.vn` và FastAPI backend tại `api.focusflow.vn` giao tiếp mượt mà mà không gặp lỗi CORS hay bị chặn cookie bên thứ ba.
* **Tối ưu Hóa Hiệu năng & Lưu trữ:** Việc lưu trữ Refresh Token Rotation trên Redis với TTL 7 ngày giúp giảm tải I/O trên PostgreSQL, tra cứu O(1) < 2ms, loại bỏ thao tác định kỳ dọn rác bản ghi token hết hạn trong CSDL chính.
* **Chi phí Đánh đổi:** Đòi hỏi cấu hình tên miền chung khi triển khai UAT (sử dụng tên miền phụ hoặc proxy nội bộ). Trong môi trường phát triển cục bộ (localhost), hệ thống cấu hình cookie linh hoạt để chạy thuận tiện.

---

## 5. Hệ quả (Consequences)
* **Tích cực:** Đáp ứng toàn diện các tiêu chuẩn bảo mật khắt khe nhất trong SRS (`NFR-SEC-001` đến `NFR-SEC-004`), bảo vệ người học và bảo vệ nguồn lực API của nhóm.
* **Đồng bộ Kiến trúc:** Hoàn toàn nhất quán 100% với `system-architecture.md`, `schema.sql` (15 bảng), và `sequence-diagrams.md`.

---

## 6. Yêu cầu & Tài liệu liên quan
- **Yêu cầu SRS:** `FR-AUTH-001`, `FR-AUTH-002`, `FR-CALENDAR-001`, `FR-CALENDAR-002`, `BUSR-08`, `OS-05`, `NFR-SEC-001..004`.
- **ADR liên quan:** `ADR-001` (Kiến trúc Lục giác), `ADR-002` (Backend Tech Stack), `ADR-004` (Worker & Redis), `ADR-007` (Database Persistence).
- **Hồ sơ thiết kế:** [`docs/architecture/system-architecture.md`](file:///Users/vuthang/Documents/FocusFlow/docs/architecture/system-architecture.md), [`docs/uml/sequence-diagrams.md`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/sequence-diagrams.md).
