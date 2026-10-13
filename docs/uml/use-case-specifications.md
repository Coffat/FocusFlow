# FocusFlow — Tài liệu Đặc tả Ca sử dụng Chi tiết (Use Case Specifications)

**Dự án:** FocusFlow — Hệ thống hỗ trợ lập kế hoạch và thực thi lộ trình tự học thích ứng tích hợp AI  
**Tiêu chuẩn kỹ thuật:** ISO/IEC/IEEE 29148:2018 (Requirements Engineering), OMG UML 2.5.1 Superstructure  
**Căn cứ đánh giá học thuật:** Khung Rubric Đồ án Tốt nghiệp CNTT — Tiêu chí TC1 & TC2.1 & TC2.3 (Mức 5)  
**Tài liệu liên kết:**
- Đặc tả yêu cầu phần mềm (SRS): [`docs/srs/srs-v1.0.md`](file:///Users/vuthang/Documents/FocusFlow/docs/srs/srs-v1.0.md)
- Sơ đồ Ca sử dụng: [`docs/uml/use-cases/use-case-diagram.puml`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/use-cases/use-case-diagram.puml) | File Draw.io: [`docs/uml/UC_Dia.drawio`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/UC_Dia.drawio)
- Sơ đồ Tuần tự chi tiết: [`docs/uml/sequence-diagrams.md`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/sequence-diagrams.md)
- Máy trạng thái các thực thể: [`docs/uml/state-machines.md`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/state-machines.md)

---

## MỤC LỤC
1. [Quy chuẩn Cấu trúc Đặc tả Ca sử dụng](#1-quy-chuẩn-cấu-trúc-đặc-tả-ca-sử-dụng)
2. [Phân hệ 1: Xác thực & Quản lý Tài khoản](#2-phân-hệ-1-xác-thực--quản-lý-tài-khoản)
   - [UC-AUTH-01: Đăng ký tài khoản mới](#uc-auth-01-đăng-ký-tài-khoản-mới)
   - [UC-AUTH-02: Đăng nhập hệ thống](#uc-auth-02-đăng-nhập-hệ-thống)
   - [UC-AUTH-03: Đăng xuất hệ thống](#uc-auth-03-đăng-xuất-hệ-thống)
   - [UC-QUOTA-01: Thử nghiệm nâng cấp gói học tập (Mock Sandbox)](#uc-quota-01-thử-nghiệm-nâng-cấp-gói-học-tập-mock-sandbox)
3. [Phân hệ 2: Khởi tạo Lộ trình (AI & Fallback)](#3-phân-hệ-2-khởi-tạo-lộ-trình-ai--fallback)
   - [UC-PLAN-01: Khởi tạo mục tiêu & Làm rõ ngữ cảnh](#uc-plan-01-khởi-tạo-mục-tiêu--làm-rõ-ngữ-cảnh)
   - [UC-AVAIL-01: Cấu hình thời gian rảnh khả dụng](#uc-avail-01-cấu-hình-thời-gian-rảnh-khả-dụng)
   - [UC-PLAN-02: Phê duyệt các cột mốc học tập](#uc-plan-02-phê-duyệt-các-cột-mốc-học-tập)
   - [UC-PLAN-03: Tạo đề xuất & Áp dụng lịch trình](#uc-plan-03-tạo-đề-xuất--áp-dụng-lịch-trình)
   - [UC-PLAN-04: Tự lập kế hoạch học tập thủ công](#uc-plan-04-tự-lập-kế-hoạch-học-tập-thủ-công)
4. [Phân hệ 3: Quản lý Lộ trình & Lịch trình](#4-phân-hệ-3-quản-lý-lộ-trình--lịch-trình)
   - [UC-ROADMAP-01: Điều phối & Chuyển đổi lộ trình](#uc-roadmap-01-điều-phối--chuyển-đổi-lộ-trình)
   - [UC-SCHED-01: Theo dõi & Điều hướng lịch trình](#uc-sched-01-theo-dõi--điều-hướng-lịch-trình)
   - [UC-TASK-02: Tái xếp lịch nhiệm vụ từ Backlog](#uc-task-02-tái-xếp-lịch-nhiệm-vụ-từ-backlog)
5. [Phân hệ 4: Không gian Thực thi (Study Workspace) & Quản lý Task](#5-phân-hệ-4-không-gian-thực-thi-study-workspace--quản-lý-task)
   - [UC-SESS-01: Thực hiện phiên học tập trung](#uc-sess-01-thực-hiện-phiên-học-tập-trung)
   - [UC-SESS-02: Xử lý gián đoạn phiên học](#uc-sess-02-xử-lý-gián-đoạn-phiên-học)
   - [UC-TASK-01: Đánh dấu hoàn thành nhiệm vụ](#uc-task-01-đánh-dấu-hoàn-thành-nhiệm-vụ)
6. [Phân hệ 5: Thích ứng Biến cố & Báo cáo Tiến độ](#6-phân-hệ-5-thích-ứng-biến-cố--báo-cáo-tiến-độ)
   - [UC-PAUSE-01: Thiết lập tạm dừng lộ trình](#uc-pause-01-thiết-lập-tạm-dừng-lộ-trình)
   - [UC-ADAPT-01: Quét phát hiện nhiệm vụ quá hạn](#uc-adapt-01-quét-phát-hiện-nhiệm-vụ-quá-hạn)
   - [UC-ADAPT-02: Yêu cầu AI tái cấu trúc nhiệm vụ](#uc-adapt-02-yêu-cầu-ai-tái-cấu-trúc-nhiệm-vụ)
   - [UC-REP-01: Theo dõi báo cáo tiến độ định lượng](#uc-rep-01-theo-dõi-báo-cáo-tiến-độ-định-lượng)
   - [UC-REP-02: Yêu cầu nhận xét từ AI Review](#uc-rep-02-yêu-cầu-nhận-xét-từ-ai-review)
7. [Phân hệ 6: Tích hợp Lịch Ngoại vi](#7-phân-hệ-6-tích-hợp-lịch-ngoại-vi)
   - [UC-CAL-01: Xuất tệp lịch tĩnh .ics](#uc-cal-01-xuất-tệp-lịch-tĩnh-ics)
   - [UC-CAL-02: Đăng ký & Quản lý WebCal feed](#uc-cal-02-đăng-ký--quản-lý-webcal-feed)
8. [Phân hệ 7: Phân hệ Quản trị viên (Admin Portal)](#8-phân-hệ-7-phân-hệ-quản-trị-viên-admin-portal)
   - [UC-ADM-01: Đăng nhập cổng quản trị RBAC](#uc-adm-01-đăng-nhập-cổng-quản-trị-rbac)
   - [UC-ADM-02: Quản lý người dùng & Hạn ngạch AI](#uc-adm-02-quản-lý-người-dùng--hạn-ngạch-ai)
   - [UC-ADM-03: Giám sát chỉ số vận hành hệ thống](#uc-adm-03-giám-sát-chỉ-số-vận-hành-hệ-thống)

---

## 1. Quy chuẩn Cấu trúc Đặc tả Ca sử dụng
Mỗi Use Case trong tài liệu này tuân thủ cấu trúc chuẩn ISO/IEC/IEEE 29148:
- **Mã & Tên Use Case:** Định danh duy nhất và tên hành động có ý nghĩa.
- **Tác nhân:** Phân định rõ Tác nhân chính (Primary Actor) và Tác nhân hỗ trợ (Secondary / Supporting Actor).
- **Mục tiêu & Tóm tắt:** Ý định của tác nhân khi tương tác với hệ thống.
- **Tiền điều kiện (Preconditions):** Trạng thái bắt buộc của hệ thống và người dùng trước khi ca sử dụng bắt đầu.
- **Hậu điều kiện (Postconditions):** Đảm bảo thành công (Success Guarantees) và đảm bảo tối thiểu khi lỗi (Minimal Guarantees).
- **Luồng sự kiện chính (Main Flow):** Kịch bản tương tác từng bước tối ưu.
- **Luồng sự kiện phụ / Thay thế (Alternative Flows):** Các nhánh rẽ nghiệp vụ hợp lệ.
- **Luồng ngoại lệ (Exception Flows):** Xử lý lỗi kết nối, hết hạn mức, dữ liệu không hợp lệ.
- **Truy vết kỹ thuật (Traceability):** Liên kết tới Quy tắc nghiệp vụ (BUSR), Yêu cầu chức năng (FR), Sơ đồ Tuần tự ([`docs/uml/sequence-diagrams.md`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/sequence-diagrams.md)), và Máy trạng thái ([`docs/uml/state-machines.md`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/state-machines.md)).

---

## 2. Phân hệ 1: Xác thực & Quản lý Tài khoản

### UC-AUTH-01: Đăng ký tài khoản mới
* **Tác nhân chính:** Learner (Người học).
* **Tác nhân hỗ trợ:** Hệ thống FocusFlow.
* **Mục tiêu:** Tạo tài khoản định danh mới để lưu trữ lộ trình và dữ liệu tự học.
* **Tiền điều kiện:** Người dùng chưa đăng nhập; email đăng ký chưa tồn tại trong cơ sở dữ liệu.
* **Hậu điều kiện thành công:** Bản ghi người dùng được tạo mới với vai trò mặc định `ROLE_LEARNER`, hạn ngạch AI khởi tạo gói Free (`monthly_limit = 50`), mật khẩu được băm an toàn bằng Argon2id.
* **Luồng sự kiện chính:**
  1. Người học truy cập trang Đăng ký và nhập Họ tên, Email, Mật khẩu.
  2. Người học gửi biểu mẫu đăng ký.
  3. Hệ thống kiểm tra tính hợp lệ của định dạng email, độ phức tạp mật khẩu ($\ge 8$ ký tự, chữ hoa, số).
  4. Hệ thống kiểm tra tính duy nhất của email trong bảng `users`.
  5. Hệ thống băm mật khẩu bằng Argon2id, khởi tạo tài khoản ở trạng thái `ACTIVE`.
  6. Hệ thống khởi tạo bản ghi `ai_quotas` cho người dùng với `tier = FREE`.
  7. Hệ thống cấp phát cặp JWT token (Access Token qua HttpOnly Cookie, Refresh Token lưu trong DB) và chuyển hướng người học vào màn hình Onboarding.
* **Luồng phụ / Ngoại lệ:**
  - *E1 - Email đã tồn tại:* Hệ thống thông báo lỗi `EMAIL_ALREADY_EXISTS` và gợi ý đăng nhập.
  - *E2 - Mật khẩu yếu:* Hệ thống từ chối và yêu cầu nhập lại theo chuẩn bảo mật.
* **Truy vết:** `FR-AUTH-001`, `BUSR-11`, `NFR-SEC-001`.

---

### UC-AUTH-02: Đăng nhập hệ thống
* **Tác nhân chính:** Learner (Người học).
* **Tác nhân hỗ trợ:** Hệ thống FocusFlow.
* **Mục tiêu:** Xác thực danh tính và mở phiên làm việc an toàn.
* **Tiền điều kiện:** Người học đã có tài khoản trong hệ thống.
* **Hậu điều kiện thành công:** Phiên làm việc được thiết lập, cookie HttpOnly `access_token` được gửi về trình duyệt.
* **Luồng sự kiện chính:**
  1. Người học nhập Email và Mật khẩu tại màn hình Đăng nhập.
  2. Hệ thống truy vấn bản ghi tài khoản và kiểm tra trạng thái `status = ACTIVE`.
  3. Hệ thống đối chiếu hash mật khẩu Argon2id qua `PasswordHasher`.
  4. Hệ thống kiểm tra trạng thái tài khoản không bị khóa (`is_locked() == false`).
  5. Hệ thống sinh JWT Access Token (hạn 15 phút) và Refresh Token (hạn 7 ngày).
  6. Hệ thống thiết lập HttpOnly SameSite Cookie an toàn và chuyển người học vào Dashboard.
* **Luồng phụ / Ngoại lệ:**
  - *E1 - Sai thông tin xác thực:* Hệ thống trả về `401 Unauthorized {"error": "INVALID_CREDENTIALS"}`.
  - *E2 - Tài khoản bị khóa:* Trả về `403 Forbidden {"error": "ACCOUNT_LOCKED"}` theo quy tắc `BUSR-11`.
* **Truy vết:** `FR-AUTH-002`, `NFR-SEC-001`, `NFR-SEC-002`, Sơ đồ Tuần tự: `SD1 (seq-01)`.

---

### UC-AUTH-03: Đăng xuất hệ thống
* **Tác nhân chính:** Learner, System Administrator.
* **Tác nhân hỗ trợ:** Hệ thống FocusFlow.
* **Mục tiêu:** Chấm dứt phiên làm việc an toàn, xóa thông tin xác thực tại Client và thu hồi Refresh Token trên máy chủ.
* **Tiền điều kiện:** Người dùng đang đăng nhập (có cookie `access_token` hoặc `refresh_token` hợp lệ).
* **Hậu điều kiện thành công:** Refresh Token bị vô hiệu hóa; HttpOnly cookies bị xóa; người dùng được chuyển hướng về trang Đăng nhập.
* **Luồng sự kiện chính:**
  1. Người dùng bấm nút [Đăng xuất] tại thanh điều hướng hoặc menu tài khoản.
  2. Trình duyệt gửi `POST /api/v1/auth/logout` kèm HttpOnly cookie.
  3. Hệ thống thu hồi Refresh Token tương ứng (xóa hoặc đánh dấu revoked trong database / Redis token blacklist).
  4. Hệ thống gửi header `Set-Cookie` xóa bỏ các cookie xác thực (`Max-Age=0`).
  5. Trình duyệt chuyển hướng người dùng về trang Đăng nhập.
* **Truy vết:** `FR-AUTH-002`, `NFR-SEC-001`, `NFR-SEC-002`.

---

### UC-QUOTA-01: Thử nghiệm nâng cấp gói học tập (Mock Sandbox)
* **Tác nhân chính:** Learner.
* **Tác nhân hỗ trợ:** Hệ thống FocusFlow.
* **Mục tiêu:** Trải nghiệm chuyển đổi gói tài khoản Free $\rightarrow$ Pro trong môi trường mô phỏng không phát sinh giao dịch tài chính thực tế.
* **Tiền điều kiện:** Learner đã đăng nhập; đang ở gói `FREE`.
* **Hậu điều kiện:** Hạn ngạch `monthly_limit` tăng lên mức Pro (ví dụ: 300 lượt) trong phiên thử nghiệm.
* **Luồng chính:**
  1. Người học xem thông tin hạn ngạch AI hiện tại tại mục Cài đặt Tài khoản.
  2. Người học chọn gói "Pro Sandbox" và bấm [Kích hoạt Giả lập].
  3. Hệ thống hiển thị modal giải thích: "Đây là tính năng mô phỏng thử nghiệm học thuật, không trừ phí thực tế".
  4. Người học bấm [Xác nhận Nâng cấp].
  5. Hệ thống cập nhật trường `tier = PRO` và điều chỉnh trần hạn ngạch trong bảng `ai_quotas`.
  6. Giao diện hiển thị trạng thái mới thành công.
* **Truy vết:** `FR-QUOTA-002`, `OS-02`.

---

## 3. Phân hệ 2: Khởi tạo Lộ trình (AI & Fallback)

### UC-PLAN-01: Khởi tạo mục tiêu & Làm rõ ngữ cảnh
* **Tác nhân chính:** Learner.
* **Tác nhân hỗ trợ:** Hệ thống FocusFlow.
* **Mục tiêu:** Khởi tạo mục tiêu học tập và thiết lập thực thể Roadmap ở trạng thái `INITIALIZED`.
* **Tiền điều kiện:** Learner đã đăng nhập.
* **Hậu điều kiện:** Thực thể `Goal` và `Roadmap` được khởi tạo độc lập trong CSDL ở trạng thái `INITIALIZED`, chuẩn bị cho giai đoạn phân rã kế hoạch.
* **Luồng sự kiện chính:**
  1. Người học nhập Tiêu đề Mục tiêu, Ngày hoàn thành (`target_date`), và Ngữ cảnh cá nhân.
  2. Người học bấm [Bắt đầu Lộ trình].
  3. Hệ thống kiểm tra quy tắc nghiệp vụ ngày hoàn thành: `target_date > CURRENT_DATE`.
  4. Hệ thống khởi tạo `Goal` và `Roadmap` liên kết, lưu vào PostgreSQL với `status = 'INITIALIZED'`.
  5. Hệ thống mở giao diện thiết lập kế hoạch (cho phép chọn AI hoặc Lập thủ công).
* **Luồng phụ / Ngoại lệ:**
  - *E1 - Ngày hoàn thành không hợp lệ:* Hệ thống trả về `422 Unprocessable Entity {"error": "INVALID_TARGET_DATE"}` nếu ngày chọn $\le$ ngày hiện tại.
* **Truy vết:** `FR-PLAN-001`, Sơ đồ Tuần tự: `SD2 (seq-02)`.

---

### UC-AVAIL-01: Cấu hình thời gian rảnh khả dụng
* **Tác nhân chính:** Learner.
* **Tác nhân hỗ trợ:** Hệ thống FocusFlow.
* **Mục tiêu:** Thiết lập khung thời gian học tập khả dụng theo tuần cố định hoặc lịch linh hoạt.
* **Tiền điều kiện:** Người học đã đăng nhập.
* **Hậu điều kiện:** Cấu hình thời gian rảnh được lưu vào bảng `user_availability`.
* **Luồng sự kiện chính:**
  1. Người học truy cập màn hình Cấu hình Thời gian rảnh.
  2. Người học lựa chọn chế độ:
     - **Mode A (Weekly Recurring Template):** Chọn các ngày trong tuần và khung giờ cố định (ví dụ: Thứ 2, 4, 6 từ 19:30 — 21:30).
     - **Mode B (Dynamic Slot Matrix):** Thiết lập chi tiết từng khung giờ theo ngày cụ thể.
  3. Người học tùy chỉnh thời lượng tối đa mỗi phiên và thời gian nghỉ.
  4. Hệ thống kiểm tra ràng buộc: Tổng thời lượng $\ge 1$ giờ/tuần và không xung đột khung giờ (`OS-06`).
  5. Hệ thống lưu cấu hình và xác nhận thành công.
* **Truy vết:** `FR-AVAIL-001`, `FR-AVAIL-002`, `BUSR-01`, `OS-06`.

---

### UC-PLAN-02: Phê duyệt các cột mốc học tập & Sinh đề xuất kế hoạch AI
* **Tác nhân chính:** Learner.
* **Tác nhân hỗ trợ:** External LLM (Google Gemini API), Redis.
* **Mục tiêu:** Người học thẩm định cột mốc và yêu cầu AI sinh đề xuất lịch học chi tiết thông qua SSE Streaming và Two-Phase Quota.
* **Tiền điều kiện:** Roadmap ở trạng thái `INITIALIZED`, tài khoản còn hạn ngạch AI (`available_quota > 0`).
* **Hậu điều kiện:** Bản ghi `ScheduleProposal` được lưu ở trạng thái `DRAFT`, hạn ngạch AI được trừ thành công (`committed`).
* **Luồng sự kiện chính:**
  1. Người học cấu hình thời gian rảnh và bấm [Sinh Đề xuất Lịch học bằng AI].
  2. Hệ thống kiểm tra và tạm giữ hạn ngạch AI (`reserve_quota`) qua Redis Lua script (`OS-02`).
  3. Hệ thống khử khuẩn dữ liệu (Prompt Sanitization) chống Prompt Injection (`FR-PLAN-001`).
  4. Hệ thống mở kênh SSE stream (`text/event-stream`) gửi prompt sang Google Gemini API (timeout 55s, `ADR-005`).
  5. Gemini stream các khối nội dung, hệ thống cập nhật tiến độ phần trăm % về client theo thời gian thực.
  6. Khi kết thúc stream, hệ thống thẩm định schema JSON Pydantic (thời lượng task 30–120 phút), lưu đề xuất vào `schedule_proposals` với `status = 'DRAFT'`.
  7. Hệ thống chính thức trừ hạn ngạch (`commit_quota`) và hiển thị bản xem trước cho người học duyệt.
* **Luồng phụ / Ngoại lệ:**
  - *E1 - Hết hạn ngạch AI:* Hệ thống trả về `429 Too Many Requests {"error": "AI_QUOTA_EXCEEDED"}`, gợi ý lập thủ công (`UC-PLAN-04`).
  - *E2 - LLM Timeout (> 55s) hoặc lỗi API:* Hệ thống hoàn lại hạn ngạch (`release_quota` qua Lua script), trả về `504 Gateway Timeout {"error": "AI_TIMEOUT"}`.
* **Truy vết:** `FR-PLAN-002`, `FR-QUOTA-001`, `BUSR-02`, `OS-02`, `ADR-005`, Sơ đồ Tuần tự: `SD3 (seq-03)`.

---

### UC-PLAN-03: Tạo đề xuất & Áp dụng lịch trình
* **Tác nhân chính:** Learner.
* **Tác nhân hỗ trợ:** Hệ thống FocusFlow.
* **Mục tiêu:** Áp dụng đề xuất lịch trình thành Lịch chính thức (Official Schedule) sau khi vượt qua Hard Ceiling Gate.
* **Tiền điều kiện:** Có bản ghi `ScheduleProposal` ở trạng thái `DRAFT` (`UC-PLAN-02`); Thời gian rảnh đã cấu hình (`UC-AVAIL-01`).
* **Hậu điều kiện:** `Roadmap` chuyển sang trạng thái `ACTIVE`; Lịch chính thức được lưu với tính toàn vẹn ACID qua Unit of Work; các task được tạo với trạng thái `TODO`.
* **Luồng sự kiện chính:**
  1. Người học xem xét Bản xem trước Đề xuất (Preview Proposal) và bấm [Áp dụng Lịch].
  2. Domain Service `AvailabilityValidator` kiểm tra nghiêm ngặt trần giờ rảnh trong ngày (Hard Ceiling, `BUSR-02`).
  3. Thực thể Domain thực thi nghiệp vụ: `Proposal.apply()` chuyển sang `APPLIED`, `Roadmap.activate()` chuyển sang `ACTIVE`.
  4. Unit of Work thực thi giao dịch ACID:
     - Hủy các task cũ còn dang dở (`UPDATE tasks SET status = 'CANCELLED'`).
     - Chèn hàng loạt task mới với trạng thái `TODO` (`INSERT INTO tasks ... status = 'TODO'`).
     - Cập nhật `roadmaps.status = 'ACTIVE'` và `schedule_proposals.status = 'APPLIED'`.
  5. Hệ thống hiển thị thông báo kích hoạt thành công và chuyển người học vào Màn hình Lịch làm việc.
* **Luồng phụ / Ngoại lệ:**
  - *E1 - Vi phạm trần giờ rảnh (Hard Ceiling Violated):* Hệ thống ném lỗi `422 Unprocessable Entity {"error": "HARD_CEILING_VIOLATED"}`, giao dịch bị hủy bỏ.
* **Truy vết:** `FR-PLAN-003`, `FR-PLAN-004`, `BUSR-02`, `BUSR-03`, `OS-03`, Sơ đồ Tuần tự: `SD4 (seq-04)`.

---

### UC-PLAN-04: Tự lập kế hoạch học tập thủ công
* **Tác nhân chính:** Learner.
* **Tác nhân hỗ trợ:** Hệ thống FocusFlow.
* **Mục tiêu:** Cho phép người học tự nhập toàn bộ cột mốc và nhiệm vụ không cần thông qua AI (chủ động hoặc khi hết quota AI).
* **Tiền điều kiện:** Người học đã đăng nhập.
* **Hậu điều kiện:** `Roadmap` được kích hoạt ở trạng thái `ACTIVE` mà không tiêu tốn hạn ngạch AI.
* **Luồng sự kiện chính:**
  1. Người học chọn tùy chọn "Tự tạo lộ trình thủ công" tại bước khởi tạo mục tiêu.
  2. Người học tự thêm từng Cột mốc, đặt tên và thời hạn.
  3. Người học tự thêm các Nhiệm vụ con và gán vào khung giờ rảnh.
  4. Người học bấm [Lưu và Kích hoạt Lộ trình].
  5. Hệ thống kiểm tra tính hợp lệ dữ liệu và chuyển Roadmap sang `ACTIVE`.
* **Truy vết:** `FR-PLAN-004`, `BUSR-01`.

---

## 4. Phân hệ 3: Quản lý Lộ trình & Lịch trình

### UC-ROADMAP-01: Điều phối & Chuyển đổi lộ trình
* **Tác nhân chính:** Learner.
* **Tác nhân hỗ trợ:** Hệ thống FocusFlow.
* **Mục tiêu:** Xem danh sách các lộ trình học tập song song, chuyển đổi lộ trình đang thực hiện, đổi tên hoặc lưu trữ (Archive) lộ trình đã hoàn tất.
* **Tiền điều kiện:** Người học đã đăng nhập.
* **Hậu điều kiện:** Lộ trình được chuyển đổi ngữ cảnh hoặc trạng thái vòng đời cập nhật (`COMPLETED`, `ARCHIVED`).
* **Luồng sự kiện chính:**
  1. Người học mở danh sách Lộ trình học tập cá nhân.
  2. Hệ thống hiển thị danh sách các Roadmap kèm trạng thái (`ACTIVE`, `PAUSED`, `COMPLETED`, `ARCHIVED`) và tiến độ hoàn thành.
  3. Người học chọn một Roadmap để đặt làm Lộ trình làm việc hiện tại (Active Context).
  4. Người học có thể chọn Lưu trữ (Archive) lộ trình không còn theo đuổi, hoặc đổi tên/mục tiêu.
  5. Hệ thống cập nhật cơ sở dữ liệu và tải lại ngữ cảnh làm việc tương ứng.
* **Truy vết:** `FR-AVAIL-003`, `BR-003`.

---

### UC-SCHED-01: Theo dõi & Điều hướng lịch trình
* **Tác nhân chính:** Learner.
* **Tác nhân hỗ trợ:** Hệ thống FocusFlow.
* **Mục tiêu:** Xem lịch học tập chính thức theo các chế độ xem Ngày, Tuần, Tháng; lọc nhiệm vụ theo trạng thái và kiểm tra khối lượng học tập.
* **Tiền điều kiện:** Người học đã đăng nhập; có ít nhất một Roadmap đang `ACTIVE`.
* **Hậu điều kiện:** Lịch trình được hiển thị trực quan và đồng bộ với cơ sở dữ liệu.
* **Luồng sự kiện chính:**
  1. Người học truy cập trang [Lịch học (Schedule)].
  2. Hệ thống tải danh sách các task có `scheduled_date` trong phạm vi hiển thị (Tuần hiện tại / Tháng hiện tại).
  3. Người học chuyển đổi giữa các chế độ xem: Chế độ Ngày (Daily view), Chế độ Tuần (Weekly view), hoặc Danh sách (Agenda list).
  4. Người học có thể lọc task theo trạng thái (`TODO`, `COMPLETED`, `OVERDUE`).
  5. Người học click vào từng task để xem chi tiết mô tả, thời lượng ước tính và cột mốc tương ứng.
* **Truy vết:** `FR-SCHEDULE-001`, `BUSR-02`, `NFR-UX-001`.

---

### UC-TASK-02: Tái xếp lịch nhiệm vụ từ Backlog
* **Tác nhân chính:** Learner.
* **Tác nhân hỗ trợ:** Hệ thống FocusFlow.
* **Mục tiêu:** Quản lý các task dở dang hoặc bị dời lịch (`scheduled_date = NULL`), thực hiện kéo thả hoặc gán ngày thủ công để đưa task trở lại Lịch chính thức.
* **Tiền điều kiện:** Người học đã đăng nhập.
* **Hậu điều kiện:** Task trong Backlog được gán `scheduled_date` mới hợp lệ và xuất hiện lại trên Lịch chính thức.
* **Luồng sự kiện chính:**
  1. Người học mở ngăn kéo Hàng đợi Backlog (Backlog Drawer).
  2. Hệ thống hiển thị danh sách các nhiệm vụ chưa lên lịch hoặc bị trôi dạt do gián đoạn phiên học (`scheduled_date IS NULL`).
  3. Người học chọn một task và thực hiện:
     - Kéo thả vào một ngày trống trên Time Grid; hoặc
     - Bấm [Lên lịch lại] và chọn ngày/giờ cụ thể.
  4. Hệ thống kiểm tra quỹ thời gian rảnh của ngày được chọn (`AvailabilityValidator`).
  5. Hệ thống cập nhật `scheduled_date` cho task và hiển thị task trên Lịch chính thức.
* **Truy vết:** `FR-TASK-002`, `BUSR-03`, `OS-01`.

---

## 5. Phân hệ 4: Không gian Thực thi (Study Workspace) & Quản lý Task

### UC-SESS-01: Thực hiện phiên học tập trung
* **Tác nhân chính:** Learner.
* **Tác nhân hỗ trợ:** Hệ thống FocusFlow.
* **Mục tiêu:** Tập trung học tập theo kỹ thuật Pomodoro/Time-boxing có đồng hồ đếm ngược và kiểm soát tập trung.
* **Tiền điều kiện:** Người học có ít nhất một Task cần thực hiện ở trạng thái `TODO`.
* **Hậu điều kiện:** Bản ghi `StudySession` được hoàn tất (`status = COMPLETED`), thời gian học thực tế được cộng dồn, task hoàn thành chuyển sang `COMPLETED`.
* **Luồng sự kiện chính:**
  1. Người học chọn một Task từ lịch học hôm nay và bấm [Bắt đầu Phiên học].
  2. Hệ thống kiểm tra: Người dùng chưa có phiên học nào khác đang mở (`IN_PROGRESS`).
  3. Hệ thống khởi tạo `StudySession` ở trạng thái `IN_PROGRESS`, ghi nhận `started_at = NOW()`.
  4. Màn hình Study Workspace kích hoạt chế độ tập trung, bắt đầu đếm ngược đồng hồ Pomodoro (mặc định 25 hoặc 50 phút).
  5. Trong suốt phiên học, client định kỳ gửi nhịp tim `heartbeat` mỗi 60 giây lên server để duy trì trạng thái phiên sống (`OS-07`).
  6. Khi hết giờ hoặc hoàn thành bài học, người học bấm [Kết thúc Phiên học], nhập ghi chú thu hoạch (Key Takeaways).
  7. Hệ thống thực thi giao dịch Unit of Work:
     - Cập nhật `StudySession` sang `COMPLETED`.
     - Cập nhật các Task được chọn sang `COMPLETED` (`completed_at = NOW()`).
  8. Hệ thống hiển thị màn hình tổng kết thành tựu.
* **Luồng phụ / Ngoại lệ:**
  - *E1 - Xung đột phiên hoạt động (Active Session Conflict):* Nếu đã có phiên `IN_PROGRESS`, hệ thống ném lỗi `409 Conflict {"error": "ACTIVE_SESSION_EXISTS"}`.
* **Quan hệ mở rộng:** Có điểm mở rộng `Session Interrupted` dẫn tới `UC-SESS-02`.
* **Truy vết:** `FR-SESS-001`, `FR-SESS-002`, `BUSR-07`, `OS-07`, Sơ đồ Tuần tự: `SD5 (seq-05)`.

---

### UC-SESS-02: Xử lý gián đoạn phiên học
* **Tác nhân chính:** Time / Celery Beat (Tác vụ nền định kỳ) hoặc Learner (khi bấm dừng sớm).
* **Tác nhân hỗ trợ:** Hệ thống FocusFlow.
* **Mục tiêu:** Tự động hoặc chủ động chốt phiên học gián đoạn theo công thức bảo toàn công sức `OS-01`.
* **Tiền điều kiện:** `StudySession` đang ở trạng thái `IN_PROGRESS`.
* **Hậu điều kiện:** Phiên học được chốt an toàn ở trạng thái `PARTIAL_COMPLETED` hoặc `CANCELLED`, bảo toàn thời gian học hợp lệ tính đến `last_heartbeat_at`.
* **Luồng sự kiện chính (Tác vụ nền Celery Beat quét định kỳ mỗi 5 phút):**
  1. Celery Beat đẩy task `sweep_abandoned_sessions` bất đồng bộ vào Redis Broker.
  2. Worker nhận task và truy vấn các phiên mất heartbeat quá 5 phút (`CURRENT_TIMESTAMP - last_heartbeat_at > 5 minutes`).
  3. Domain Service `AbandonmentEvaluator` áp dụng quy tắc toán học `OS-01`:
     $$\text{status} = \begin{cases} \text{PARTIAL\_COMPLETED} & \text{nếu } (\text{completed\_tasks} \ge 1) \lor (\text{actual\_minutes} \ge 0.5 \times \text{planned\_minutes}) \\ \text{CANCELLED} & \text{ngược lại} \end{cases}$$
  4. Thực thể Domain chốt phiên: `StudySession.mark_abandoned(status, last_heartbeat_at)`.
  5. Hệ thống thực thi giao dịch cơ sở dữ liệu:
     - Nhánh `PARTIAL_COMPLETED`: Chốt session, công nhận thời gian thực học, chuyển các task chưa xong về Backlog (`status = 'TODO'`, `scheduled_date = NULL`).
     - Nhánh `CANCELLED`: Hủy phiên, trả toàn bộ task dở dang về `TODO`.
  6. Worker ghi nhận log kiểm toán và số liệu đo lường.
* **Luồng phụ (Người học chủ động bấm Dừng sớm):**
  - Người học bấm [Dừng phiên sớm]. Hệ thống áp dụng cùng công thức `OS-01` để chốt `PARTIAL_COMPLETED` hoặc `CANCELLED`.
* **Quan hệ mở rộng:** `<<extend>>` từ `UC-SESS-01` tại điểm mở rộng `Session Interrupted`.
* **Truy vết:** `FR-SESS-003`, `OS-01`, `OS-07`, Sơ đồ Tuần tự: `SD8 (seq-08)`.

---

### UC-TASK-01: Đánh dấu hoàn thành nhiệm vụ
* **Tác nhân chính:** Learner.
* **Tác nhân hỗ trợ:** Hệ thống FocusFlow.
* **Mục tiêu:** Đánh dấu hoàn thành một nhiệm vụ học tập.
* **Tiền điều kiện:** Task thuộc sở hữu của người học; Task chưa bị hủy (`CANCELLED`).
* **Hậu điều kiện:** Task chuyển sang trạng thái `COMPLETED`; tỷ lệ hoàn thành Milestone và Roadmap được tính toán lại.
* **Luồng sự kiện chính:**
  1. Người học tick chọn hoàn thành Task trên giao diện Lịch học hoặc Workspace.
  2. Hệ thống cập nhật trường `status = COMPLETED` và `completed_at = NOW()`.
  3. Hệ thống kiểm tra: Nếu tất cả các task thuộc Milestone đã hoàn thành, tự động đánh dấu Milestone đó hoàn thành.
  4. Nếu 100% task của Roadmap hoàn thành, hệ thống kích hoạt trạng thái Roadmap `COMPLETED`.
* **Truy vết:** `FR-TASK-001`, `BUSR-08`.

---

## 6. Phân hệ 5: Thích ứng Biến cố & Báo cáo Tiến độ

### UC-PAUSE-01: Thiết lập tạm dừng lộ trình
* **Tác nhân chính:** Learner.
* **Tác nhân hỗ trợ:** Hệ thống FocusFlow.
* **Mục tiêu:** Tạm dừng lộ trình khi bận việc đột xuất và tịnh tiến lịch học tự động bằng giải thuật Domino Shift.
* **Tiền điều kiện:** Roadmap đang ở trạng thái `ACTIVE`.
* **Hậu điều kiện:** Roadmap chuyển sang `PAUSED`; toàn bộ task `TODO` từ ngày bắt đầu tạm dừng được tịnh tiến tất định sang sau ngày kết thúc tạm dừng; tạo bản ghi `pause_records`.
* **Luồng sự kiện chính:**
  1. Người học truy cập phần Tạm dừng Lộ trình, chọn Ngày bắt đầu nghỉ, Ngày học lại dự kiến và lý do.
  2. Hệ thống kiểm tra: `start_date < resume_date` và Roadmap đang `ACTIVE`.
  3. Domain Service `DominoShiftCalculator` tính toán ngày học mới cho toàn bộ các task `TODO` còn dang dở (< 50ms, bảo toàn quan hệ tiên quyết).
  4. Thực thể Domain thực thi nghiệp vụ: `Roadmap.pause()`, `Task.reschedule()`, `PauseRecord.create()`.
  5. Hệ thống thực thi giao dịch ACID lưu bản ghi tạm dừng, chuyển Roadmap sang `PAUSED` và batch update ngày mới cho các task.
  6. Hệ thống hiển thị thông báo lộ trình đã tạm dừng và các task đã được dời an toàn.
* **Luồng phụ / Ngoại lệ:**
  - *E1 - Khoảng ngày không hợp lệ:* Trả về `422 Unprocessable Entity {"error": "INVALID_DATE_RANGE"}`.
  - *E2 - Lộ trình không ACTIVE:* Trả về `409 Conflict {"error": "ROADMAP_NOT_ACTIVE"}`.
* **Truy vết:** `FR-ADAPT-001`, `BUSR-01`, Sơ đồ Tuần tự: `SD6 (seq-06)`.

---

### UC-ADAPT-01: Quét phát hiện nhiệm vụ quá hạn
* **Tác nhân chính:** Time / Celery Beat (Bộ lập lịch định kỳ).
* **Tác nhân hỗ trợ:** Hệ thống FocusFlow.
* **Mục tiêu:** Định kỳ tự động quét để nhận diện các nhiệm vụ đã quá thời hạn học mà chưa hoàn thành (`OverdueScheduled`).
* **Tiền điều kiện:** Sự kiện thời gian kích hoạt định kỳ (mỗi ngày lúc 00:05 AM theo múi giờ người dùng).
* **Hậu điều kiện:** Các task có `scheduled_date < CURRENT_DATE` và `status = 'TODO'` được hệ thống tính toán trạng thái phái sinh `OverdueScheduled <<derived>>` và hiển thị cờ cảnh báo trên Dashboard.
* **Luồng sự kiện chính:**
  1. Celery Beat phát tín hiệu kích hoạt tác vụ quét quá hạn hàng ngày.
  2. Hệ thống thực thi truy vấn tối ưu với partial index `idx_tasks_todo_overdue`:
     `SELECT id FROM tasks WHERE scheduled_date < CURRENT_DATE AND status = 'TODO';`
  3. Hệ thống tạo các thông báo nhắc nhở gửi tới người học để gợi ý đưa task về Backlog (`UC-TASK-02`) hoặc dùng AI tái cấu trúc (`UC-ADAPT-02`).
* **Ghi chú kiến trúc:** Tuân thủ chuẩn UML 2.5.1 với Tác nhân thời gian (Temporal Actor) kích hoạt tự động ở hậu trường.
* **Truy vết:** `FR-ADAPT-001`, `BUSR-05`.

---

### UC-ADAPT-02: Yêu cầu AI tái cấu trúc nhiệm vụ
* **Tác nhân chính:** Learner.
* **Tác nhân hỗ trợ:** External LLM.
* **Mục tiêu:** Người học yêu cầu AI hỗ trợ tái sắp xếp các nhiệm vụ bị trôi lịch/tồn đọng vào khung thời gian khả dụng tới.
* **Tiền điều kiện:** Người học có các task quá hạn trong Backlog; tài khoản còn hạn ngạch AI.
* **Hậu điều kiện:** Đề xuất tái cấu trúc lịch học được tạo để người học phê duyệt.
* **Luồng sự kiện chính:**
  1. Người học bấm nút [Tái cấu trúc lịch học tồn đọng] từ danh sách cảnh báo.
  2. Hệ thống tổng hợp danh sách task quá hạn và khung giờ rảnh trống trong 14 ngày tới.
  3. Hệ thống gửi yêu cầu sang Google Gemini API.
  4. Gemini phân tích mức độ ưu tiên và đề xuất phân bổ lại task vào các slot trống thích hợp.
  5. Người học xem xét bản đề xuất điều chỉnh lịch và bấm [Áp dụng].
  6. Hệ thống cập nhật lại ngày học mới cho các task tồn đọng.
* **Truy vết:** `FR-ADAPT-002`, `BUSR-05`.

---

### UC-REP-01: Theo dõi báo cáo tiến độ định lượng
* **Tác nhân chính:** Learner.
* **Tác nhân hỗ trợ:** Hệ thống FocusFlow.
* **Mục tiêu:** Theo dõi trực quan các chỉ số hiệu suất học tập: Tỷ lệ tuân thủ lịch (Plan Adherence), Chuỗi ngày học liên tục (Streak), Tổng giờ học tích lũy.
* **Tiền điều kiện:** Người học đã đăng nhập.
* **Hậu điều kiện:** Dữ liệu biểu đồ định lượng được kết xuất và hiển thị.
* **Luồng sự kiện chính:**
  1. Người học truy cập tab [Báo cáo & Phân tích].
  2. Hệ thống tổng hợp dữ liệu từ các bảng `study_sessions`, `tasks`, và `roadmaps`.
  3. Hệ thống tính toán chỉ số Plan Adherence:
     $$\text{Adherence Rate} = \frac{\text{Số Task hoàn thành đúng hạn}}{\text{Tổng Task dự kiến}} \times 100\%$$
     *(loại trừ các ngày Roadmap bị `PAUSED` theo quy tắc `BUSR-06`)*.
  4. Hiển thị biểu đồ nhiệt (Heatmap) chuỗi ngày học và biểu đồ phân bổ thời gian.
* **Truy vết:** `FR-REPORT-001`, `BR-002`, `BR-003`.

---

### UC-REP-02: Yêu cầu nhận xét từ AI Review
* **Tác nhân chính:** Learner.
* **Tác nhân hỗ trợ:** External LLM (Google Gemini API).
* **Mục tiêu:** Nhận phân tích nhận xét điểm mạnh, điểm yếu và lời khuyên điều chỉnh phương pháp học tập theo mô hình Tự học có điều tiết (SRL).
* **Tiền điều kiện:** Người học đang ở màn hình Báo cáo tiến độ (`UC-REP-01`); còn hạn ngạch AI.
* **Hậu điều kiện:** Báo cáo đánh giá định tính của AI được lưu vào hệ thống và hiển thị cho người học.
* **Luồng sự kiện chính:**
  1. Tại màn hình Báo cáo tiến độ, người học bấm nút [Yêu cầu Đánh giá AI].
  2. Hệ thống kiểm tra hạn ngạch (`reserve_quota`).
  3. Hệ thống trích xuất dữ liệu định lượng 7 ngày qua (tỷ lệ hoàn thành, số phút tập trung, số lần gián đoạn) làm ngữ cảnh context.
  4. Hệ thống gọi Gemini API tạo nhận xét sư phạm định tính.
  5. Gemini trả về văn bản nhận xét chia làm 3 phần: (1) Đánh giá nỗ lực, (2) Phát hiện nút thắt cổ chai, (3) Lời khuyên hành động cụ thể tuần tới.
  6. Hệ thống hiển thị nhận xét và trừ hạn ngạch (`commit_quota`).
* **Quan hệ mở rộng:** `<<extend>>` từ `UC-REP-01` tại điểm mở rộng `Weekly Evaluation Request`.
* **Truy vết:** `FR-REPORT-002`, `OS-02`.

---

## 7. Phân hệ 6: Tích hợp Lịch Ngoại vi

### UC-CAL-01: Xuất tệp lịch tĩnh .ics
* **Tác nhân chính:** Learner.
* **Tác nhân hỗ trợ:** Hệ thống FocusFlow.
* **Mục tiêu:** Tải về tệp lịch tiêu chuẩn RFC 5545 `.ics` chứa các phiên học để nhập thủ công vào ứng dụng lịch cá nhân.
* **Tiền điều kiện:** Roadmap đang `ACTIVE` và có ít nhất 1 task đã lên lịch.
* **Hậu điều kiện:** Trình duyệt tải về tệp tin `focusflow-schedule.ics`.
* **Luồng sự kiện chính:**
  1. Người học bấm nút [Xuất file Lịch .ics] tại màn hình Lịch học.
  2. Hệ thống kết xuất dữ liệu các task thành định dạng chuẩn VEVENT RFC 5545 (bao gồm `SUMMARY`, `DTSTART`, `DTEND`, `UID`, `DESCRIPTION`).
  3. Trả về HTTP Response với `Content-Type: text/calendar; charset=utf-8` và tải về máy người học.
* **Truy vết:** `FR-CALENDAR-001`, RFC 5545.

---

### UC-CAL-02: Đăng ký & Quản lý WebCal feed
* **Tác nhân chính:** External Calendar Application (Google Calendar, Apple Calendar, Outlook) qua HTTP Polling, Learner (khi tạo/thu hồi token).
* **Tác nhân hỗ trợ:** Hệ thống FocusFlow.
* **Mục tiêu:** Cấp phát URL đăng ký lịch động 1 chiều; Calendar App bên ngoài tự động kéo dữ liệu cập nhật theo chu kỳ; bảo vệ token bằng SHA-256 hash và kiểm duyệt server log.
* **Tiền điều kiện:** Người học đã đăng nhập; có token WebCal hợp lệ.
* **Hậu điều kiện:** Token WebCal ngẫu nhiên bảo mật cao được cấp phát (`OS-05`); Calendar App truy cập feed được kiểm duyệt qua `LogSanitizerMiddleware`; khi bấm Reset token cũ bị hủy ngay lập tức.
* **Luồng sự kiện chính:**
  1. Calendar App gửi `GET /api/v1/calendar/feed/{raw_token}.ics` định kỳ.
  2. `LogSanitizerMiddleware` che giấu token nhạy cảm trong server access log (`REDACTED`, `NFR-SEC-004`).
  3. Use Case băm SHA-256 token thô và kiểm tra trong bảng `webcal_tokens`.
  4. Hệ thống cập nhật timestamp `last_accessed_at`.
  5. Hệ thống truy vấn các nhiệm vụ `TODO` có lịch của người học.
  6. `IcalGeneratorAdapter` kết xuất nội dung iCalendar RFC 5545 (`text/calendar`).
  7. Hệ thống trả về `200 OK` kèm luồng dữ liệu lịch cho Calendar App.
* **Luồng ngoại lệ:**
  - *E1 - Token không hợp lệ hoặc bị vô hiệu hóa:* Hệ thống trả về `401 Unauthorized {"error": "INVALID_CALENDAR_TOKEN"}`.
* **Truy vết:** `FR-CALENDAR-002`, `FR-CALENDAR-003`, `NFR-SEC-004`, `OS-05`, RFC 5545, Sơ đồ Tuần tự: `SD7 (seq-07)`.

---

## 8. Phân hệ 7: Phân hệ Quản trị viên (Admin Portal)

### UC-ADM-01: Đăng nhập cổng quản trị RBAC
* **Tác nhân chính:** System Administrator (Quản trị viên).
* **Tác nhân hỗ trợ:** Hệ thống FocusFlow.
* **Mục tiêu:** Xác thực quyền quản trị qua cổng riêng và thiết lập phiên làm việc đặc quyền.
* **Tiền điều kiện:** Tài khoản tồn tại và có trường `role = 'ROLE_ADMIN'`.
* **Hậu điều kiện:** Cấp phát Admin Session Token, mở giao diện Quản trị viên (Web Admin Portal).
* **Luồng sự kiện chính:**
  1. Quản trị viên truy cập cổng quản trị `/admin/login`.
  2. Quản trị viên nhập thông tin tài khoản và mật khẩu.
  3. Hệ thống kiểm tra mật khẩu qua Argon2id và kiểm tra nghiêm ngặt `user.role == 'ROLE_ADMIN'`.
  4. Hệ thống cấp Admin JWT Token đặc quyền với claim RBAC rõ ràng.
  5. Chuyển hướng vào trang Tổng quan Quản trị.
* **Luồng ngoại lệ:**
  - *E1 - Tài khoản không có quyền Admin:* Dù mật khẩu đúng nhưng `role != 'ROLE_ADMIN'`, hệ thống từ chối truy cập `403 Forbidden` (`INSUFFICIENT_PRIVILEGES`), ghi log bảo mật.
* **Truy vết:** `FR-ADM-001`, `BUSR-11`, `NFR-SEC-002`, Sequence: `seq-08`.

---

### UC-ADM-02: Quản lý người dùng & Hạn ngạch AI
* **Tác nhân chính:** System Administrator.
* **Tác nhân hỗ trợ:** Hệ thống FocusFlow.
* **Mục tiêu:** Tìm kiếm, xem chi tiết người dùng, khóa/mở khóa tài khoản, hoặc nâng/hạ trần hạn ngạch AI.
* **Tiền điều kiện:** Quản trị viên đã đăng nhập và được xác thực RBAC (`UC-ADM-01`).
* **Hậu điều kiện:** Trạng thái tài khoản người dùng hoặc hạn ngạch được cập nhật; token hiện hành bị thu hồi nếu khóa tài khoản.
* **Luồng sự kiện chính:**
  1. Quản trị viên xem danh sách người dùng, lọc theo Email, Trạng thái, hoặc Gói tài khoản.
  2. Quản trị viên chọn một tài khoản cụ thể để xem chi tiết.
  3. **Trường hợp Khóa tài khoản:** Quản trị viên bấm [Khóa tài khoản (Lock Account)], nhập lý do vi phạm. Hệ thống cập nhật `status = LOCKED` trong PostgreSQL và phát lệnh vô hiệu hóa toàn bộ Refresh Token của tài khoản đó trong Redis blacklist.
  4. **Trường hợp Điều chỉnh Hạn ngạch:** Quản trị viên điều chỉnh `monthly_limit` hoặc chuyển đổi `tier` (Free $\leftrightarrow$ Pro). Hệ thống cập nhật bảng `ai_quotas` và ghi log kiểm toán (Audit Log).
* **Truy vết:** `FR-ADM-002`, `BUSR-10`, `BUSR-11`, `OS-02`, Sequence: `seq-08`.

---

### UC-ADM-03: Giám sát chỉ số vận hành hệ thống
* **Tác nhân chính:** System Administrator.
* **Tác nhân hỗ trợ:** Hệ thống FocusFlow.
* **Mục tiêu:** Giám sát thời gian thực tổng số người dùng, số lượt gọi LLM, chi phí API ước tính, và tỷ lệ lỗi hệ thống.
* **Tiền điều kiện:** Quản trị viên đã đăng nhập RBAC.
* **Hậu điều kiện:** Dashboard vận hành hiển thị dữ liệu giám sát mới nhất.
* **Luồng sự kiện chính:**
  1. Quản trị viên mở trang Giám sát Vận hành (System Metrics Dashboard).
  2. Hệ thống tổng hợp số liệu từ các bảng `ai_quotas`, `study_sessions`, và logs Redis:
     - Tổng số lượt gọi Gemini API thành công / thất bại trong 24h qua.
     - Số phiên học đang diễn ra đồng thời (Active Concurrent Sessions).
     - Thời gian phản hồi trung bình (P95 Response Time) của các endpoint AI.
  3. Hiển thị cảnh báo nếu tỷ lệ lỗi vượt ngưỡng cho phép ($\ge 5\%$).
* **Truy vết:** `FR-ADM-003`, `NFR-PERF-002`, `NFR-AVAIL-001`.
