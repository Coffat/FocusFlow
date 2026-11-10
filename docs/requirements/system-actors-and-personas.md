# FocusFlow — System Actors & User Personas Analysis Specification

> **Dự án:** FocusFlow — Hệ thống hỗ trợ lập kế hoạch và thực thi lộ trình tự học thích ứng tích hợp AI  
> **Chuyên ngành:** Công nghệ Phần mềm — Khoa Công nghệ Thông tin  
> **Cấp độ tài liệu:** Đặc tả Tác nhân Hệ thống & Phân tích Chân dung Người dùng (System Actors & User Personas Artifact)  
> **Mã tài liệu:** `DOC-REQ-ACTOR-01`  
> **Tài liệu liên kết:** 
> - [**`problem-definition.md`**](problem-definition.md) *(Định nghĩa bài toán & Ranh giới hệ thống)*
> - [**`user-survey-and-benchmarking.md`**](user-survey-and-benchmarking.md) *(Khảo sát nhu cầu tự học & Đối sánh giải pháp)*
> - [**`business-goals-and-kpis.md`**](business-goals-and-kpis.md) *(Hệ thống Mục tiêu & 5 KPI định lượng)*
> - [**`../srs/srs-v1.3.md`**](../srs/srs-v1.3.md) *(Đặc tả Yêu cầu Phần mềm v1.4 — Mục 3.1 Tác nhân hệ thống: 8 Tác nhân Chuẩn hóa `ACT-00`..`ACT-07`)*  
> **Căn cứ đánh giá học thuật:** Khung Rubric Chấm Đồ án Tốt nghiệp CNTT:
> - **Tiêu chí TC1 (Mức 5):** "Xác định rõ người dùng mục tiêu, các bên liên quan và phân tích bối cảnh khách quan."
> - **Tiêu chí TC2.1 (Mức 5):** "Mô hình hóa tác nhân, phân quyền và ranh giới hệ thống chuẩn mực."
> - **Tiêu chí TC2.7 (Mức 5):** "Thiết kế lấy người dùng làm trung tâm (UCD); Thử nghiệm nghiêm túc trên người dùng thật."

---

## MỤC LỤC

1. [Phân biệt Lý thuyết giữa Tác nhân Hệ thống & Chân dung Người dùng](#1-phân-biệt-lý-thuyết-giữa-tác-nhân-hệ-thống--chân-dung-người-dùng)
   - 1.1 [Cơ sở khoa học kỹ thuật phần mềm & Quy tắc Ranh giới Hệ thống](#11-cơ-sở-khoa-học-kỹ-thuật-phần-mềm--quy-tắc-ranh-giới-hệ-thống)
   - 1.2 [Mối quan hệ tương quan trong chu trình phát triển](#12-mối-quan-hệ-tương-quan-trong-chu-trình-phát-triển)
2. [Đặc tả Chi tiết 8 Tác nhân Hệ thống Chuẩn hóa (`ACT-00`..`ACT-07`)](#2-đặc-tả-chi-tiết-8-tác-nhân-hệ-thống-chuẩn-hóa-act-00act-07)
   - 2.0 [`ACT-00`: Khách vãng lai (Guest / Anonymous User - Primary Human Actor)](#20-act-00-khách-vãng-lai-guest--anonymous-user---primary-human-actor)
   - 2.1 [`ACT-01`: Người dùng đã đăng ký (Registered User - Abstract Primary Human Actor)](#21-act-01-người-dùng-đã-đăng-ký-registered-user---abstract-primary-human-actor)
   - 2.2 [`ACT-02`: Người học (Learner - Primary / Beneficiary Human Actor)](#22-act-02-người-học-learner---primary--beneficiary-human-actor)
   - 2.3 [`ACT-03`: Quản trị viên (Administrator - Platform & Operational Administrator)](#23-act-03-quản-trị-viên-administrator---platform--operational-administrator)
   - 2.4 [`ACT-04`: Nhà cung cấp AI (External LLM Provider - External System Actor)](#24-act-04-nhà-cung-cấp-ai-external-llm-provider---external-system-actor)
   - 2.5 [`ACT-05`: Cổng Thanh toán Trực tuyến (Payment Gateway - External System Actor)](#25-act-05-cổng-thanh-toán-trực-tuyến-payment-gateway---external-system-actor)
   - 2.6 [`ACT-06`: Dịch vụ Lịch Ngoại vi (External Calendar Service - External System Actor)](#26-act-06-dịch-vụ-lịch-ngoại-vi-external-calendar-service---external-system-actor)
   - 2.7 [`ACT-07`: Dịch vụ Thư điện tử (Email Notification Service - External System Actor)](#27-act-07-dịch-vụ-thư-điện-tử-email-notification-service---external-system-actor)
   - 2.8 [Ma trận Trách nhiệm & Phân quyền Tác nhân (Actor Responsibility Matrix)](#28-ma-trận-trách-nhiệm--phân-quyền-tác-nhân-actor-responsibility-matrix)
3. [Phân tích 3 Chân dung Người dùng Chuyên sâu (In-Depth User Personas)](#3-phân-tích-3-chân-dung-người-dùng-chuyên-sâu-in-depth-user-personas)
   - 3.1 [Phương pháp luận User Archetypes (Alan Cooper's Goal-Directed Design)](#31-phương-pháp-luận-user-archetypes-alan-coopers-goal-directed-design)
   - 3.2 [Persona 1: Nguyễn Văn An — Sinh viên năm cuối ngành CNTT (Primary Persona - IT Student Archetype ~60%)](#32-persona-1-nguyễn-văn-an--sinh-viên-năm-cuối-ngành-cntt-primary-persona---it-student-archetype-60)
   - 3.3 [Persona 2: Trần Minh Hùng — Kỹ sư Cơ khí tự học chuyển ngành IT (Secondary Persona - ~25%)](#33-persona-2-trần-minh-hùng--kỹ-sư-cơ-khí-tự-học-chuyển-ngành-it-secondary-persona---25)
   - 3.4 [Persona 3: Lê Thu Mai — Chuyên viên Phân tích tự học chứng chỉ AWS (Tertiary Persona - ~15%)](#34-persona-3-lê-thu-mai--chuyên-viên-phân-tích-tự-học-chứng-chỉ-aws-tertiary-persona---15)
   - 3.5 [Khung Nhu Cầu Thật & Job-to-be-done (JTBD) Cốt Lõi của Người Tự Học](#35-khung-nhu-cầu-thật--job-to-be-done-jtbd-cốt-lõi-của-người-tự-học)
4. [Ma trận Ánh xạ Persona sang Tính năng & Yêu cầu Kỹ thuật](#4-ma-trận-ánh-xạ-persona-sang-tính-năng--yêu-cầu-kỹ-thuật)
5. [Góc Nhìn Cố Vấn Khóa Luận (Defense Guidance on Actors & Personas)](#5-góc-nhìn-cố-vấn-khóa-luận-defense-guidance-on-actors--personas)

---

## 1. Phân biệt Lý thuyết giữa Tác nhân Hệ thống & Chân dung Người dùng

### 1.1 Cơ sở khoa học kỹ thuật phần mềm & Quy tắc Ranh giới Hệ thống
Trong công nghệ phần mềm và thiết kế lấy người dùng làm trung tâm (*User-Centered Design - UCD*), sinh viên thường mắc sai lầm đánh đồng giữa **Tác nhân hệ thống (System Actor)** và **Chân dung người dùng (User Persona)**, hoặc đưa các tiến trình nội bộ làm Actor. FocusFlow phân định rõ ràng các khái niệm này theo chuẩn ISO/IEC/IEEE 29148:2018 và OMG UML 2.5.1:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                 PHÂN ĐỊNH KHÁI NIỆM TRONG CÔNG NGHỆ PHẦN MỀM                │
│                                                                             │
│   USER PERSONA (Tâm lý & Con người thực) ──> SYSTEM ACTOR (Vai trò logic)  │
│   - Tên gọi, tuổi, nghề nghiệp, tâm lý      - Vai trò logic trừu tượng      │
│   - Động lực, nỗi đau, thói quen học        - Ranh giới tương tác hệ thống  │
│   - Ngữ cảnh thực tế đời sống               - Phân quyền API & Bảo mật      │
│   - Dùng để: Thiết kế trải nghiệm (UX)      - Dùng để: Mô hình hóa UML/SRS  │
└─────────────────────────────────────────────────────────────────────────────┘
```

1. **System Actor (Tác nhân Hệ thống):**
   - Là một **thực thể logic trừu tượng nằm bên ngoài Ranh giới Hệ thống (*System Boundary*)** (có thể là con người, hệ thống phần cứng, hoặc dịch vụ phần mềm bên ngoài) tương tác trực tiếp với hệ thống đang thiết kế (*System Under Design - SuD*).
   - Actor đại diện cho *vai trò* (Role) chứ không đại diện cho một cá nhân cụ thể. Actor được sử dụng trong Biểu đồ Ca sử dụng (Use Case Diagram), Biểu đồ Tuần tự (Sequence Diagram) và ma trận phân quyền bảo mật (RBAC).
   - **Quy tắc Ranh giới Kiến trúc Bắt buộc (Architectural Boundary Rule):** Toàn bộ các thành phần hạ tầng và thực thi nội bộ — bao gồm cơ sở dữ liệu **`PostgreSQL 16 + pgvector`**, bộ nhớ đệm/hàng đợi **`Redis 7`**, trình điều phối tác vụ nền **`Taskiq Worker & Taskiq Scheduler`**, và lõi **`Internal AI Harness Runtime`** — nằm hoàn toàn **bên trong Ranh giới Hệ thống (System Boundary)** và được biểu diễn trong các biểu đồ kiến trúc C4 (Container / Component Diagrams), **tuyệt đối không được mô hình hóa làm Use Case Actor hay `Time <<temporal>>` Actor**. Các ca sử dụng chạy định kỳ theo lịch (`UC-06`, `UC-16`, `UC-18`, `UC-25`) được kích hoạt bởi sự kiện thời gian nội bộ (`[Trigger: TimeEvent]`) và gắn kết trực tiếp với **Tác nhân Thụ hưởng chính (Beneficiary Actor: `Learner — ACT-02`, `Administrator — ACT-03`)** cùng các tác nhân dịch vụ ngoại vi liên quan (`ACT-06`, `ACT-07`).
2. **User Persona (Chân dung Người dùng):**
   - Là một **hình mẫu người dùng hợp thành mang tính thực chứng** (*Composite User Archetype*) theo phương pháp luận *Goal-Directed Design* của Alan Cooper (1999), đại diện cho một nhóm người dùng mục tiêu có cùng mô thức hành vi, mục tiêu, động lực và các điểm nghẽn tâm lý.
   - Persona không phải là một cá nhân được chỉ đích danh ngoài đời thực, mà là công cụ mô hình hóa nhận thức giúp đội ngũ phát triển thấu cảm sâu sắc nỗi đau của người dùng (*Empathy*) để đưa ra các quyết định thiết kế công thái học chuẩn mực.

### 1.2 Mối quan hệ tương quan trong chu trình phát triển
Nhiều Personas khác nhau ngoài đời thực (Sinh viên năm cuối, Kỹ sư chuyển ngành, Chuyên viên ôn thi chứng chỉ) khi đăng nhập vào hệ thống đều tương tác dưới cùng một vai trò kỹ thuật duy nhất là **Learner Actor (`ACT-02`, kế thừa `Registered User — ACT-01`)**. Tuy nhiên, các Persona khác nhau sẽ sử dụng các tính năng và chế độ cấu hình khác nhau (ví dụ: An dùng Mode B với khung giờ tối cố định; Hùng dùng Mode A với quỹ giờ linh hoạt; Mai dùng tính năng WebCal Feed để đồng bộ lịch công tác).

---

## 2. Đặc tả Chi tiết 8 Tác nhân Hệ thống Chuẩn hóa (`ACT-00`..`ACT-07`)

Theo chuẩn cơ sở được phê duyệt bởi Hội đồng Kiểm soát Thay đổi (CCB) trong [SRS v1.4 (Mục 3.1)](../srs/srs-v1.3.md#31-các-tác-nhân-hệ-thống-system-actors), hệ thống FocusFlow được chuẩn hóa trên **8 Tác nhân Hệ thống (`ACT-00` đến `ACT-07`)** (gồm 01 tác nhân trừu tượng, 03 tác nhân con người cụ thể, và 04 tác nhân hệ thống/dịch vụ ngoại vi):

### 2.0 `ACT-00`: Khách vãng lai (Guest / Anonymous User - Primary Human Actor)
- **Bản chất:** Người dùng chưa đăng ký hoặc chưa đăng nhập vào hệ thống.
- **Ranh giới tương tác:** Các trang giao diện Web công khai (Landing Page, Trang Đăng ký).
- **Trách nhiệm chính:** Tìm hiểu thông tin sản phẩm và khởi xướng ca sử dụng đăng ký tài khoản mới (`UC-01` / `UC-ACC-01`).

---

### 2.1 `ACT-01`: Người dùng đã đăng ký (Registered User - Abstract Primary Human Actor)
- **Bản chất:** Tác nhân trừu tượng (`<<abstract>>`) đại diện cho mọi cá nhân đã sở hữu tài khoản hợp lệ trên hệ thống, đóng vai trò lớp cha tổng quát hóa (Generalization) cho `Learner` (`ACT-02`) và `Administrator` (`ACT-03`).
- **Ranh giới tương tác:** Giao diện Xác thực & Bảo mật phiên làm việc.
- **Trách nhiệm chính:** Khởi xướng trực tiếp các ca sử dụng xác thực và bảo mật tài khoản dùng chung: Đăng nhập, làm mới phiên & đăng xuất (`UC-02` / `UC-ACC-02`), và Tự đặt lại mật khẩu an toàn qua thư điện tử (`FR-AUTH-004` / `UC-ACC-03`).

---

### 2.2 `ACT-02`: Người học (Learner - Primary / Beneficiary Human Actor)
- **Bản chất:** Con người thực tế tương tác với hệ thống qua trình duyệt Web (`Learner --|> Registered User`).
- **Ranh giới tương tác:** Giao diện Web Application (Desktop & Mobile).
- **Trách nhiệm chính & Quyền lợi thụ hưởng:**
  - Khởi tạo tài khoản cá nhân, bảo vệ thông tin mật khẩu phiên đăng nhập, hoặc thực thi quyền đóng & xóa vĩnh viễn tài khoản theo Điều 17 GDPR (`FR-PROFILE-002` / `UC-ACC-05`).
  - Cấu hình thời gian rảnh khả dụng (Mode A hoặc Mode B kèm `energy_level`) và quản lý ghi chú thói quen học tập (`Structured Learner Memory` — `UC-03` / `UC-ACC-11`).
  - Khởi tạo mục tiêu, nạp tài liệu RAG, tạo danh sách bài học bằng AI (`UC-07` / `UC-PLAN-02`), tương tác làm rõ và chủ động bấm nút "Apply" để lưu Schedule Proposal thành Official Schedule (`UC-07`, `UC-08`).
  - Vận hành các phiên học trong Study Workspace (Thực hiện phiên học tập trung (Tiêu chuẩn & Rút gọn), tick hoàn thành task, Daily Check-in, Scratchpad, Key Takeaways — `UC-14`, `UC-15` / `UC-EXEC-04`) và làm bài kiểm tra cột mốc (Prove Mode — `UC-20` / `UC-ADAPT-02`).
  - Nhận thông báo Email khi có task quá hạn (`OVERDUE`), kích hoạt **"Dời lịch hợp lý bằng AI (AI Reschedule)"** (`UC-23`), khôi phục lộ trình bị gián đoạn lâu ngày (Reset Ritual — `UC-24` / `UC-ADAPT-07`), hoặc thiết lập Tạm dừng và tiếp tục lộ trình và dời lịch bù ngày dừng (Pause Roadmap & Domino Shift — `UC-22` / `UC-ADAPT-05`) khi có biến cố.
  - Kết nối tài khoản Google Calendar (`UC-17` / `UC-EXEC-07`), tự động cập nhật thời gian bận từ Google Calendar (`UC-EXEC-08`), đồng bộ lịch học sang Google Calendar / ứng dụng lịch, quản lý mã WebCal Token và xuất tệp `.ics` (`UC-18` / `UC-EXEC-09`).
  - Chọn nâng cấp gói học tập (`PREMIUM` — `UC-04`) và thụ hưởng các tiến trình nền tự động theo sự kiện thời gian nội bộ (`[Trigger: TimeEvent]`): làm mới hạn ngạch đầu tháng & khôi phục giữ chỗ treo (`UC-06`), tự động lưu phiên học khi mất kết nối (`UC-16` / `UC-EXEC-06`), và gửi email nhắc nhở bài quá hạn và lộ trình gián đoạn (`UC-25` / `UC-ADAPT-08`) / tổng hợp bộ nhớ người học hàng ngày.
- **Cơ chế xác thực & Bảo mật:** Xác thực qua Email/Mật khẩu băm (Argon2id), cấp phiên làm việc bằng Session Token / JWT mang cờ bảo mật `HttpOnly`, `SameSite`. Mọi thao tác đều bị ràng buộc bởi `user_id`.

---

### 2.3 `ACT-03`: Quản trị viên (Administrator - Platform & Operational Administrator)
- **Bản chất:** Tác nhân người dùng nội bộ (Internal Human Actor, `Administrator --|> Registered User`) thực hiện quản trị nền tảng và vận hành hệ thống.
- **Ranh giới tương tác:** Giao diện Web Admin Portal tối giản (3 màn hình nghiệp vụ chính: Đăng nhập RBAC với giới hạn phiên tuyệt đối 8 giờ, Quản lý Người dùng/Gói cước/Hạn ngạch Quota & Đối soát Giao dịch Thanh toán, Dashboard Giám sát chỉ số vận hành, tiêu thụ AI & doanh thu), được bảo vệ nghiêm ngặt bằng cơ chế kiểm soát truy cập dựa trên vai trò (`role = 'ADMIN'`).
- **Trách nhiệm chính & Quyền lợi thụ hưởng:**
  - Xác thực phiên làm việc quản trị viên an toàn (`UC-02`), bảo vệ các endpoint và route quản trị `/admin/*`.
  - Quản trị danh sách người dùng, khóa/mở khóa tài khoản, chuyển đổi phân tầng tài khoản (`FREE` / `PREMIUM`), điều chỉnh định mức hạn ngạch gọi AI (`UC-26`), tra cứu và đối soát giao dịch thanh toán nâng cấp gói cước (`UC-27`), đồng thời thụ hưởng tác vụ nền thu hồi giữ chỗ/đơn thanh toán quá hạn (`UC-06` — `[Trigger: TimeEvent]`).
  - Giám sát trạng thái hoạt động, chỉ số độ sẵn sàng (Uptime Monitor), tỷ lệ lỗi API, tổng lượng tài nguyên AI đã tiêu thụ và thống kê doanh thu gói cước trên toàn hệ thống (`UC-28`).

---

### 2.4 `ACT-04`: Nhà cung cấp AI (External LLM Provider - External System Actor)
- **Bản chất:** Hệ thống trí tuệ nhân tạo bên thứ ba (Google Gemini API / OpenAI API / Anthropic Claude API) cung cấp qua giao diện đám mây.
- **Giao thức tương tác:** HTTPS RESTful API qua cổng bảo mật TLS 1.3; bắt buộc hỗ trợ **Structured JSON Outputs (JSON Schema)**.
- **Trách nhiệm chính:**
  - Tiếp nhận prompt chứa thông tin mục tiêu học tập và học liệu đã được làm sạch, cô lập ngữ cảnh (`<user_input>`, `<untrusted_knowledge_context>`).
  - Sinh phản hồi tạo danh sách bài học bằng AI (`UC-07` / `UC-PLAN-02`), Schedule Proposal (`UC-08`), làm bài kiểm tra cột mốc (Prove Mode — `UC-20` / `UC-ADAPT-02`), đánh giá học tập cuối tuần (`UC-21` / `UC-ADAPT-03`), dời lịch quá hạn (`UC-23`) hoặc khôi phục lộ trình bị gián đoạn lâu ngày (Reset Ritual — `UC-24` / `UC-ADAPT-07`) theo đúng định dạng JSON Schema trong thời gian quy định ($\le 55$ giây).
- **Ràng buộc an toàn:** Hệ thống FocusFlow coi External LLM (`ACT-04`) là một hệ thống không đáng tin cậy hoàn toàn; mọi payload trả về đều phải đi qua Cổng kiểm định 3 tầng (`UC-12`) của `Internal AI Harness` bên trong System Boundary trước khi tạo bản nháp.

---

### 2.5 `ACT-05`: Cổng Thanh toán Trực tuyến (Payment Gateway - External System Actor)
- **Bản chất:** Hệ thống cổng thanh toán trực tuyến bên thứ ba tích hợp chuẩn công nghiệp (**PayOS / VNPay Sandbox**).
- **Giao thức tương tác:** HTTPS RESTful API (khởi tạo đơn hàng thanh toán & đối soát) và **HTTPS POST Webhook / IPN** đính kèm chữ ký số mật mã **`HMAC-SHA256`**.
- **Trách nhiệm chính:**
  - Tiếp nhận yêu cầu tạo đơn hàng nâng cấp gói học tập `PREMIUM` từ FocusFlow Backend (`UC-04`) và trả về liên kết thanh toán (`checkout_url`) cùng mã QR chuyển khoản (`VietQR`).
  - Xử lý giao dịch thanh toán của Người học, đóng vai trò Primary Actor chủ động gửi thông báo kết quả giao dịch tức thời về FocusFlow qua Webhook/IPN (`UC-05`), và cung cấp API đối soát giao dịch cho Quản trị viên (`UC-27`).
- **Ràng buộc bảo mật & Toàn vẹn:** FocusFlow Backend bắt buộc xác thực chữ ký số `HMAC-SHA256` và kiểm tra tính bất biến (`idempotency` theo `order_code`) trước khi chuyển trạng thái giao dịch sang `PAID` và kích hoạt gói `PREMIUM` (300 lượt gọi AI/tháng, 15 lộ trình hoạt động).

---

### 2.6 `ACT-06`: Dịch vụ Lịch Ngoại vi (External Calendar Service - External System Actor)
- **Bản chất:** Các dịch vụ lịch tiêu chuẩn của bên thứ ba (Google Calendar, Apple Calendar, Microsoft Outlook Calendar).
- **Giao thức tương tác:** **Đồng bộ Lịch 2 Chiều Có Kiểm Soát (Controlled Two-Way Calendar Sync)**:
  - *Chiều Inbound (Kết nối tài khoản Google Calendar & Tự động cập nhật thời gian bận từ Google Calendar — `UC-17` / `UC-EXEC-07`, `UC-EXEC-08`)*: Giao thức OAuth 2.0 REST API đọc dữ liệu khoảng thời gian bận (`Free/Busy intervals` & `syncToken`) từ Google Calendar của người học.
  - *Chiều Outbound (Đồng bộ lịch học sang Google Calendar / ứng dụng lịch — `UC-18` / `UC-EXEC-09`)*: Đồng bộ các khối `schedule_blocks` thuộc `Official Schedule` qua kết nối API, luồng **WebCal HTTP/HTTPS GET** kèm mã bảo mật `{user_secure_token}.ics`, hoặc tệp tĩnh chuẩn iCalendar **RFC 5545 (`.ics`)**.
- **Trách nhiệm chính:**
  - Cung cấp các khoảng thời gian bận (`Free/Busy`) để FocusFlow tự động khấu trừ dung lượng thời gian rảnh khả dụng khi lập lịch hoặc dời lịch.
  - Tiếp nhận và hiển thị các sự kiện học tập thuộc Lịch học chính thức (`Official Schedule`) song song với lịch sinh hoạt cá nhân.
- **Ràng buộc bảo mật & Toàn vẹn:** Chiều Inbound chỉ đọc khoảng bận `Free/Busy`, tuyệt đối không cho phép thao tác kéo thả hay xóa sự kiện trên ứng dụng lịch ngoài tự động xóa hoặc ghi đè cấu trúc Milestone/Roadmap gốc của FocusFlow (`BUSR-08`).

---

### 2.7 `ACT-07`: Dịch vụ Thư điện tử (Email Notification Service - External System Actor)
- **Bản chất:** Hạ tầng chuyển phát thư điện tử giao dịch bên ngoài tích hợp qua giao thức SMTP bảo mật TLS hoặc REST API dịch vụ email.
- **Giao thức tương tác:** SMTP over TLS / HTTPS REST API qua cổng `EmailNotificationPort`.
- **Trách nhiệm chính:**
  - Tiếp nhận yêu cầu chuyển phát email chứa liên kết khôi phục mật khẩu ký số có hiệu lực 15 phút (`FR-AUTH-004` / `UC-ACC-03`).
  - Tiếp nhận yêu cầu từ tiến trình quét định kỳ lúc `00:05` (`UC-25` / `UC-ADAPT-08: Gửi email nhắc nhở bài quá hạn và lộ trình gián đoạn`) để gửi thư nhắc nhở bài quá hạn và lộ trình gián đoạn đến địa chỉ email đăng ký của người học.

---

### 2.8 Ma trận Trách nhiệm & Phân quyền Tác nhân (Actor Responsibility Matrix)

| Chức năng & Nghiệp vụ Hệ thống (28 Use Cases — SRS v1.4) | Guest (`ACT-00`) | Learner (`ACT-02` $\subset$ `ACT-01`) | Administrator (`ACT-03` $\subset$ `ACT-01`) | External LLM (`ACT-04`) | Payment Gateway (`ACT-05`) | External Calendar (`ACT-06`) | Email Service (`ACT-07`) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Đăng ký tài khoản mới (`UC-01`) | **Chủ trì** | - | - | - | - | - | - |
| Đăng nhập, quản lý phiên & Tự đặt lại mật khẩu (`UC-02`, `FR-AUTH-004`) | - | **Chủ trì** (`ACT-01`) | **Chủ trì** (`ACT-01`, RBAC 8h) | - | - | - | **Gửi link Reset** |
| Hồ sơ cá nhân, Thời gian rảnh Mode A/B, Bộ nhớ 4×3 & Xóa tài khoản GDPR (`UC-03`, `FR-PROFILE-002`) | - | **Chủ trì** | - | - | - | - | - |
| Nâng cấp gói Premium & Xử lý Webhook thanh toán (`UC-04`, `UC-05`) | - | **Chủ trì** (`UC-04`) | Đối soát (`UC-27`) | - | **Xử lý & Gửi Webhook (`UC-05`)** | - | - |
| Làm mới hạn ngạch định kỳ & Thu hồi giữ chỗ quá hạn (`UC-06` — `[Trigger: TimeEvent]`) | - | **Thụ hưởng** | **Thụ hưởng** | - | - | - | - |
| Khởi tạo mục tiêu, Nạp RAG & Tạo danh sách bài học bằng AI / Lập lịch (`UC-07`..`UC-12`) | - | **Chủ trì & Apply** | - | **Thực thi (`UC-07`, `UC-08`)** | - | - | - |
| Today Focus View, Phiên học Tiêu chuẩn & Rút gọn, Tự động lưu phiên (`UC-13`..`UC-16`) | - | **Chủ trì (`UC-13..15`) / Thụ hưởng (`UC-16` TimeEvent)** | - | Gợi ý tùy chọn (`UC-14`) | - | - | - |
| Kết nối Google Calendar, cập nhật thời gian bận & Đồng bộ lịch học (`UC-17`, `UC-18`) | - | **Chủ trì** | - | - | - | **Đồng bộ Free/Busy & .ics** | - |
| Báo cáo định lượng, Làm bài kiểm tra cột mốc & Đánh giá học tập cuối tuần (`UC-19`..`UC-21`) | - | **Chủ trì** | - | **Phân tích (`UC-20`, `UC-21`)** | - | - | - |
| Tạm dừng, Tiếp tục dời lịch bù ngày dừng, Khôi phục lộ trình gián đoạn (`UC-22`..`UC-24`) | - | **Chủ trì & Apply** | - | **Tái lập lịch (`UC-23`, `UC-24`)** | - | - | - |
| Gửi email nhắc nhở bài quá hạn & lộ trình gián đoạn, Tổng hợp Memory (`UC-25` — `[Trigger: TimeEvent]`) | - | **Thụ hưởng** | - | - | - | - | **Gửi Email cảnh báo** |
| Quản lý Người dùng/Quota, Đối soát Thanh toán & Giám sát Hệ thống (`UC-26`..`UC-28`) | - | Người dùng thụ hưởng | **Chủ trì toàn cục** | - | **Đối soát (`UC-27`)** | - | - |

---

## 3. Phân tích 3 Chân dung Người dùng Chuyên sâu (In-Depth User Personas)

### 3.1 Phương pháp luận User Archetypes (Alan Cooper's Goal-Directed Design)
Theo phương pháp luận Thiết kế Định hướng Mục tiêu (*Goal-Directed Design - GDD*) của Alan Cooper (1999) — công trình kinh điển đặt nền móng cho kỹ thuật Persona trong kỹ nghệ phần mềm: Persona không phải là một người dùng có thật với họ tên hay số căn cước cá nhân cụ thể, mà là một **Hình mẫu Hợp thành (Synthesized Composite Archetype)** được xây dựng từ việc trừu tượng hóa các mục tiêu, mô thức hành vi, rào cản tâm lý và môi trường kỹ thuật của người dùng.

Dựa trên nghiên cứu báo cáo ngành công nghệ (Stack Overflow Developer Survey, tỷ lệ bỏ cuộc MOOCs 85-95% trên tạp chí *Science*) kết hợp nhật ký thực nghiệm công thái học (Cognitive Walkthrough), FocusFlow thiết lập **3 User Archetypes** chủ đạo:

1. **Archetype 1 — IT Student Archetype (Minh họa: Sinh viên An, 21 tuổi):** Đại diện cho phân khúc sinh viên kỹ thuật/công nghệ (~60%), có nền tảng công nghệ tốt nhưng bị quá tải bởi khối lượng tài liệu khổng lồ và thiếu năng lực phân rã mục tiêu thành các đầu việc hàng ngày.
2. **Archetype 2 — Career Switcher Archetype (Minh họa: Kỹ sư Hùng, 26 tuổi):** Đại diện cho phân khúc người đi làm tự học chuyển nghề (~25%), có quỹ thời gian rất hạn hẹp (1.5h/tối), thường xuyên đối mặt với hiện tượng suy hao ý chí sau giờ làm và lịch trình dễ bị đứt gãy do tăng ca đột xuất.
3. **Archetype 3 — Certification Seeker Archetype (Minh họa: Chuyên viên Mai, 24 tuổi):** Đại diện cho phân khúc người đi làm ôn thi chứng chỉ quốc tế (~15%), lịch trình di chuyển linh hoạt, đòi hỏi sự đồng bộ chặt chẽ với ứng dụng lịch công tác (Google Calendar) và nhu cầu đúc kết kiến thức thi cử ngắn gọn.

---

### 3.2 Persona 1: Nguyễn Văn An — Sinh viên năm cuối ngành CNTT (Primary Persona - IT Student Archetype ~60%)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ PERSONA 1: NGUYỄN VĂN AN (PRIMARY PERSONA - SINH VIÊN CNTT NĂM CUỐI)        │
│ "Em có động lực học rất lớn nhưng luôn bị ngập trong mớ tài liệu hỗn độn."  │
├──────────────────────────────────────┬──────────────────────────────────────┤
│ THÔNG TIN CƠ BẢN                     │ MỤC TIÊU & ĐỘNG LỰC                  │
│ - Tuổi: 21                           │ - Tự học Golang, Docker & K8s trong  │
│ - Trường: ĐH Sư phạm Kỹ thuật TP.HCM │   2 tháng để làm đồ án tốt nghiệp.   │
│ - Chuyên ngành: Kỹ thuật Phần mềm    │ - Chuẩn bị kiến thức phỏng vấn thực  │
│ - Nơi ở: TP. Thủ Đức, TP.HCM         │   tập vị trí Backend Engineer.       │
│ - Trình độ công nghệ: Khá - Giỏi     │ - Xây dựng kỷ luật học tập hàng ngày.│
├──────────────────────────────────────┴──────────────────────────────────────┤
│ ĐIỂM NGHẼN & NỖI ĐAU THỰC TẾ (PAIN POINTS)                                   │
│ 1. Bế tắc phân rã: Không biết chia khối lượng kiến thức Docker/K8s khổng lồ  │
│    thành việc gì cần làm hôm nay, việc gì làm ngày mai.                      │
│ 2. Lộ trình "chết": Dùng ChatGPT tạo roadmap rất hay nhưng nằm nguyên trong  │
│    chatbox, copy sang Notion thì mất cả buổi chiều để trang trí template.    │
│ 3. Đứt gãy lịch: Gặp tuần thi cử bận 3 ngày, quay lại thấy danh sách task    │
│    quá hạn đỏ lòm, áp lực tâm lý quá lớn nên bỏ xó luôn lộ trình.            │
├─────────────────────────────────────────────────────────────────────────────┤
│ THÓI QUEN & MÔI TRƯỜNG KỸ THUẬT                                             │
│ - Thiết bị: Laptop MacBook/Ubuntu (chính), Smartphone Android.              │
│ - Khung giờ học: Thích hợp với Mode B (Cố định 20:00 – 22:30 các tối trong tuần).│
│ - Ứng dụng thường dùng: VS Code, Terminal, Google Calendar, Notion, Spotify.│
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Bản đồ Thấu cảm (Empathy Map) của Nguyễn Văn An:
- **Says (Nói):** *"Lộ trình trên mạng nhiều quá, chỗ nào cũng bảo học cái này cái kia, em không biết bắt đầu từ đâu và phân bổ thời gian thế nào cho vừa sức."*
- **Thinks (Nghĩ):** *"Mình sắp ra trường rồi mà kiến thức thực tế còn yếu quá. Nếu không có kế hoạch rõ ràng thì chắc chắn lại lướt mạng hết buổi tối."*
- **Does (Làm):** Hỏi ChatGPT xin roadmap $\rightarrow$ Lưu vào bookmark $\rightarrow$ Mở máy tính định học nhưng loay hoay tìm tài liệu và bấm giờ mất 30 phút $\rightarrow$ Mệt mỏi đóng máy đi ngủ.
- **Feels (Cảm thấy):** Lo âu về tương lai, bất lực khi nhìn kế hoạch bị vỡ nợ thời gian, nản lòng khi thấy công cụ hiện tại quá phức tạp.

#### Kịch bản Sử dụng Điển hình (User Scenario):
An đăng ký FocusFlow, nhập mục tiêu *"Tự học Backend Golang và Docker trong 6 tuần"*, chọn cấu hình Mode B rảnh từ 20h đến 22h tối thứ 2, 4, 6. AI FocusFlow đặt câu hỏi làm rõ nền tảng, sinh ra 3 Milestones. An chỉnh sửa nhẹ và bấm duyệt. Hệ thống sinh Schedule Proposal vừa khít khung giờ tối 2h/ngày. An bấm "Apply". Mỗi tối, An chỉ cần mở FocusFlow, bấm "Start Session" để học theo Pomodoro 25/5, ghi chép nhanh code snippet vào Scratchpad và lưu Takeaway đúc kết trước khi tắt máy.

---

### 3.3 Persona 2: Trần Minh Hùng — Kỹ sư Cơ khí tự học chuyển ngành IT (Secondary Persona - ~25%)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ PERSONA 2: TRẦN MINH HÙNG (SECONDARY PERSONA - NGƯỜI CHUYỂN NGÀNH)          │
│ "Đi làm về đã kiệt sức, tôi cần một công cụ xếp lịch sẵn để chỉ việc ngồi học."│
├──────────────────────────────────────┬──────────────────────────────────────┤
│ THÔNG TIN CƠ BẢN                     │ MỤC TIÊU & ĐỘNG LỰC                  │
│ - Tuổi: 26                           │ - Tự học Web Frontend (HTML/CSS/JS/  │
│ - Nghề nghiệp: Kỹ sư thiết kế Cơ khí │   React) trong vòng 6 tháng.         │
│ - Nơi ở: Quận 7, TP.HCM              │ - Chuyển sang làm Web Developer để có│
│ - Quỹ thời gian: Rất hạn hẹp         │   môi trường làm việc linh hoạt hơn. │
│ - Trình độ công nghệ: Cơ bản - Trung bình│ - Tận dụng tối đa 1.5h rảnh buổi tối.│
├──────────────────────────────────────┴──────────────────────────────────────┤
│ ĐIỂM NGHẼN & NỖI ĐAU THỰC TẾ (PAIN POINTS)                                   │
│ 1. Suy hao ý chí (Ego Depletion): Sau 9 tiếng làm việc căng thẳng tại nhà    │
│    máy, năng lượng tinh thần đã cạn kiệt, không còn sức tự lên kế hoạch học. │
│ 2. Phân mảnh công cụ: Mở quá nhiều tab (YouTube, Pomodoro, Google Docs) làm │
│    mất tập trung, rất dễ bị phân tâm sang lướt mạng xã hội.                  │
│ 3. Tăng ca đột xuất: Thường xuyên bị sếp yêu cầu OT đột xuất 1-2 hôm. Khi về │
│    đến nhà thì lỡ giờ học, không biết dời bài học hôm nay sang hôm nào.      │
├─────────────────────────────────────────────────────────────────────────────┤
│ THÓI QUEN & MÔI TRƯỜNG KỸ THUẬT                                             │
│ - Thiết bị: Laptop Windows cũ, Smartphone iPhone.                           │
│ - Khung giờ học: Thích hợp với Mode A (Quỹ giờ 1.5h/ngày, cuối tuần 3h/ngày).│
│ - Ứng dụng thường dùng: Trình duyệt Chrome, Excel, Zalo, YouTube.           │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Bản đồ Thấu cảm (Empathy Map) của Trần Minh Hùng:
- **Says (Nói):** *"Tôi chỉ có đúng 1 tiếng rưỡi mỗi tối. Tôi không muốn làm thư ký đi kéo thả lịch hay học cách dùng Notion phức tạp, tôi chỉ muốn vào là học ngay."*
- **Thinks (Nghĩ):** *"Mình bắt đầu học lập trình ở tuổi 26 là khá muộn. Nếu không kiên trì từng ngày thì sẽ mãi giậm chân tại chỗ ở công việc cũ."*
- **Does (Làm):** Đi làm về mệt $\rightarrow$ Bật máy tính $\rightarrow$ Không biết hôm nay phải học gì tiếp theo $\rightarrow$ Xem video YouTube giải trí rồi đi ngủ trong cảm giác tội lỗi.
- **Feels (Cảm thấy):** Mệt mỏi thể xác, áp lực tài chính và tuổi tác, sợ bị bỏ lại phía sau.

#### Kịch bản Sử dụng Điển hình (User Scenario):
Hùng sử dụng chế độ Mode A (Quỹ giờ rảnh: ngày thường 1.5 tiếng, thứ Bảy 3 tiếng, Chủ Nhật nghỉ). FocusFlow tự động xếp các task ngắn 30–45 phút vừa khít quỹ giờ 1.5h. Thứ Năm tuần này, Hùng phải tăng ca đến 22h, Hùng bấm nút **"Pause Roadmap"** chọn nghỉ 2 ngày. Thuật toán **Domino Shift** của FocusFlow tự động đẩy toàn bộ bài học lùi về sau đúng số ngày tương ứng, giữ nguyên logic bài học. Hùng an tâm làm việc mà không bị cảm giác "nợ bài" dằn vặt.

---

### 3.4 Persona 3: Lê Thu Mai — Chuyên viên Phân tích tự học chứng chỉ AWS (Tertiary Persona - ~15%)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ PERSONA 3: LÊ THU MAI (TERTIARY / EDGE PERSONA - ÔN THI CHỨNG CHỈ QUỐC TẾ)  │
│ "Tôi cần lịch học xuất hiện trên Google Calendar công việc để không bị quên."│
├──────────────────────────────────────┬──────────────────────────────────────┤
│ THÔNG TIN CƠ BẢN                     │ MỤC TIÊU & ĐỘNG LỰC                  │
│ - Tuổi: 24                           │ - Ôn thi đỗ chứng chỉ AWS Certified  │
│ - Nghề nghiệp: Data Analyst          │   Solutions Architect Associate (SAA)│
│ - Nơi ở: Quận Cầu Giấy, Hà Nội       │   trong vòng 8 tuần.                 │
│ - Trình độ công nghệ: Khá            │ - Đạt yêu cầu thăng tiến lên Senior. │
├──────────────────────────────────────┴──────────────────────────────────────┤
│ ĐIỂM NGHẼN & NỖI ĐAU THỰC TẾ (PAIN POINTS)                                   │
│ 1. Lịch trình công việc dày đặc: Thường xuyên họp hành, công tác đột xuất    │
│    khiến thời gian học bị xé nhỏ thành các khoảng trống 45 phút - 1 tiếng.   │
│ 2. Quên lịch học: Không có thói quen mở thêm một app riêng để xem lịch; chỉ  │
│    theo dõi duy nhất ứng dụng Google Calendar công ty trên điện thoại.       │
│ 3. Khó tổng kết kiến thức: Các bài lab thực hành AWS rất dài, học xong không │
│    đúc kết được điểm cốt lõi để ôn tập trước ngày thi.                       │
├─────────────────────────────────────────────────────────────────────────────┤
│ THÓI QUEN & MÔI TRƯỜNG KỸ THUẬT                                             │
│ - Thiết bị: MacBook Pro công ty, iPhone, iPad.                              │
│ - Khung giờ học: Linh hoạt (trưa 12:00 – 13:00 hoặc sáng sớm 6:00 – 7:00).   │
│ - Ứng dụng thường dùng: Google Calendar, Slack, Notion, Jira.               │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Bản đồ Thấu cảm (Empathy Map) của Lê Thu Mai:
- **Says (Nói):** *"Nếu lịch học không nằm trên Google Calendar của tôi, nó coi như không tồn tại."*
- **Thinks (Nghĩ):** *"Thi chứng chỉ này tốn 150$, mình bắt buộc phải thi đỗ ngay lần đầu, không thể học kiểu tài tử được."*
- **Does (Làm):** Đăng ký thi $\rightarrow$ Lên lịch rất hoành tráng $\rightarrow$ Cuộc họp công ty chèn vào giờ học $\rightarrow$ Quên bẵng lịch học.
- **Feels (Cảm thấy):** Bận rộn liên miên, căng thẳng vì hạn chót ngày thi cận kề.

#### Kịch bản Sử dụng Điển hình (User Scenario):
Mai dùng FocusFlow tạo lộ trình ôn thi AWS. Sau khi Apply lịch chính thức, Mai vào mục Tích hợp lịch, lấy đường dẫn **Secure WebCal Feed Token** và dán vào Google Calendar trên iPhone. Từ đó, các buổi học FocusFlow tự động hiển thị mượt mà trên ứng dụng lịch điện thoại của Mai. Khi kết thúc mỗi buổi học trong FocusFlow, Mai bắt buộc phải điền trường **Key Takeaway** (ví dụ: *"S3 Standard phù hợp dữ liệu truy cập thường xuyên, Glacier Deep Archive mất 12h phục hồi"*). Cuối tuần, tính năng AI Review đọc lại toàn bộ các Takeaways này để tổng hợp cho Mai một bản tóm tắt ôn tập siêu ngắn gọn.

---

### 3.5 Khung Nhu Cầu Thật & Job-to-be-done (JTBD) Cốt Lõi của Người Tự Học

Người tự học không chỉ đơn thuần cần một "AI thông minh" hay một bảng lịch đẹp mắt. Họ cần một hệ sinh thái giảm tải quyết định nhận thức, duy trì nhịp học ổn định và hỗ trợ họ quay lại sau khi lỡ nhịp.

#### 3.5.1 Core Job-to-be-done (JTBD) Cốt Lõi
Áp dụng khung lý thuyết Job-to-be-done (Clayton Christensen), toàn bộ giá trị mà FocusFlow mang lại cho người tự học được gói gọn trong tuyên ngôn JTBD:

> **"Khi tôi muốn tự học một kỹ năng dài hạn nhưng quỹ thời gian và năng lượng thường xuyên bị đời sống làm xáo trộn, tôi muốn hệ thống biến mục tiêu lớn thành từng phiên học cụ thể vừa sức, giữ tôi đi đúng nhịp học tập trung, và giúp tôi phục hồi kế hoạch có kiểm soát khi lỡ hẹn, để tôi không bị cảm giác tội lỗi đè nặng và không bỏ cuộc giữa chừng."**

#### 3.5.2 Phân Tích Hai Tầng Nhu Cầu: Chức Năng vs Tâm Lý

##### A. Tầng Nhu cầu Chức năng (Functional Needs)
1. **Phân rã mục tiêu:** Biến mục tiêu lớn, mơ hồ thành lộ trình 2 cấp (Milestones tổng quan & Tasks cụ thể).
2. **Định lượng vừa sức:** Chia nhỏ nội dung thành các task 30–60 phút khả thi, ước lượng thời lượng sát thực tế.
3. **Lập lịch theo thực tế:** Xếp lịch dựa trên thời gian rảnh thật (Mode A Quota / Mode B Fixed Slots), không dựa trên giả định lý tưởng.
4. **Không gian thực thi tập trung:** Cung cấp Study Workspace tích hợp (Checklist, Timer Pomodoro/Stopwatch, Scratchpad, Key Takeaways).
5. **Định hướng tức thì:** Biết chính xác hôm nay cần học gì ngay khi mở ứng dụng (Today Focus View) mà không phải bối rối duyệt qua dashboard phức tạp.
6. **Thích ứng khi lỡ lịch:** Có cơ chế phát hiện quá hạn tất định, dời lịch hợp lý bằng AI và tạm dừng lộ trình (Domino Shift).
7. **Đo lường trực quan:** Nhìn thấy tiến bộ thực chất bằng dữ liệu định lượng và báo cáo định tính thay vì cảm giác mơ hồ.
8. **Đồng bộ ngoại vi:** Xuất lịch ra Google/Apple Calendar qua WebCal Feed bảo mật để không bỏ lỡ buổi học.

##### B. Tầng 5 Nhu Cầu Tâm Lý Chống Bỏ Cuộc (Psychological Needs Against Giving Up)
Tự học là một hành trình đơn độc chịu áp lực tâm lý rất lớn. Để ngăn chặn tỷ lệ 85%–95% bỏ cuộc giữa chừng, FocusFlow được thiết kế đáp ứng trọn vẹn **5 nhu cầu tâm lý cốt tử**:

1. **Cảm giác "Hôm nay chỉ cần làm bước tiếp theo" (Cognitive Offloading & Micro-Actions):**
   - *Vấn đề tâm lý:* Khi nhìn vào lộ trình 3–6 tháng với hàng trăm bài học, người học bị choáng ngợp (paralysis by analysis), sinh ra cảm giác bất lực và trì hoãn.
   - *Thiết kế FocusFlow:* Giao diện **Today Focus View** ẩn đi sự đồ sộ của toàn bộ lộ trình; người học mở ứng dụng ra chỉ thấy 1–2 task của ngày hôm nay kèm nút [Bắt đầu học]. Tâm trí được giải phóng hoàn toàn khỏi nỗi lo "còn bao nhiêu bài nữa".
2. **Cảm giác "Lỡ một ngày không có nghĩa là thất bại" (Guilt-Free Recovery & Non-Judgmental Continuity):**
   - *Vấn đề tâm lý:* Khi bỏ lỡ một buổi học do tăng ca hay mệt mỏi, người học thường cảm thấy tội lỗi, tự trách và dễ buông xuôi bỏ cuộc hoàn toàn (hiệu ứng "What-the-hell effect").
   - *Thiết kế FocusFlow:* Hệ thống xem việc vỡ kế hoạch là một trạng thái bình thường tất yếu của cuộc sống. Các tính năng như **Minimum Viable Session (MVS 10–15 phút)**, **Pause Roadmap (Domino Shift)** và **Single-Roadmap AI Reschedule** mang thông điệp tích cực: *"Chỉ cần bạn quay lại, hệ thống luôn sẵn sàng xếp lại lịch một cách nhẹ nhàng, không phán xét, không phạt điểm chuyên cần vô lý."*
3. **Cảm giác "Hệ thống hiểu giới hạn thời gian thật của mình" (Empathy for Real-world Constraints):**
   - *Vấn đề tâm lý:* Các công cụ khác thường ép người học vào lịch trình lý tưởng hóa, dẫn đến tình trạng vừa bắt đầu đã quá tải và phá vỡ thời gian biểu cá nhân.
   - *Thiết kế FocusFlow:* Mô hình thời gian rảnh lai (Mode A / Mode B), tính năng đọc lịch bận Inbound Free/Busy từ Google Calendar, và cơ chế tràn biên có kiểm soát (Soft Overflow 30 phút) chứng minh hệ thống tôn trọng cuộc sống thật của người học.
4. **Cảm giác "AI hỗ trợ nhưng mình vẫn nắm quyền kiểm soát" (Sense of Agency & Human-in-the-Loop):**
   - *Vấn đề tâm lý:* Người học mất niềm tin nếu AI tự ý sửa đổi lịch trình của họ như một "hộp đen độc đoán", hoặc khi AI đưa ra kế hoạch không khả thi mà người học không thể can thiệp.
   - *Thiết kế FocusFlow:* AI chỉ sinh đề xuất (`ScheduleProposal` ở trạng thái `DRAFT`), hiển thị trực quan bản so sánh trước/sau (`Recovery Proposal Diff`). Người học có quyền chỉnh sửa và bắt buộc phải bấm **"Apply"** thì lịch chính thức mới được cập nhật. Con người luôn là người ra quyết định tối cao.
5. **Cảm giác "Mình đang tiến bộ thật, không chỉ tick task ảo" (Evidence of Learning vs Illusion of Competence):**
   - *Vấn đề tâm lý:* Đánh dấu tick hoàn thành task trên To-Do list dễ tạo ra ảo tưởng năng lực (Illusion of Competence), trong khi người học không thực sự nhớ hay hiểu kiến thức, dẫn đến chán nản khi đối mặt với bài toán thực tế.
   - *Thiết kế FocusFlow:* Bắt buộc ghi nhận **Key Takeaways** (đúc kết 1–2 câu bằng lời của mình) khi kết thúc phiên, kết hợp **Prove Mode** (AI đặt câu hỏi Recall kiểm chứng thực chất cuối Milestone). Người học nhìn thấy bằng chứng tri thức tích lũy mỗi ngày, xây dựng sự tự tin vững chắc từ bên trong.

---

## 4. Ma trận Ánh xạ Persona sang Tính năng & Yêu cầu Kỹ thuật

Bảng đối chiếu chứng minh thiết kế hệ thống FocusFlow giải quyết triệt để nỗi đau của từng Persona:

| Nhóm Persona | Nỗi đau cốt tử | Nhu cầu chức năng | Tính năng & Module FocusFlow tương ứng | Yêu cầu Kỹ thuật trong SRS v1.2 |
|---|---|---|---|---|
| **An (Sinh viên CNTT)** | Không biết chia nhỏ mục tiêu lớn; lười trang trí template | Tự động phân rã 2 cấp; xem trước và chỉnh sửa trước khi lưu | Module Lập kế hoạch AI: Đối thoại làm rõ $\rightarrow$ Duyệt Milestone $\rightarrow$ Proposal $\rightarrow$ Nút Apply | `FR-PLAN-001`, `FR-PLAN-002`, `FR-PLAN-003`, `BUSR-02` |
| **An (Sinh viên CNTT)** | Mất tập trung khi mở nhiều tab tài liệu, code | Không gian phiên học tập trung, ghi chú code nhanh | Study Workspace: Pomodoro Timer + Task Checklist + Scratchpad | `FR-SESSION-001`, `FR-SESSION-002`, `NFR-PERF-002` |
| **Hùng (Chuyển ngành)** | Quỹ thời gian phân tán, không cố định khung giờ | Xếp lịch theo tổng số giờ rảnh mỗi ngày | Chế độ Thời gian rảnh Mode A: Daily Hours Quota | `FR-AVAIL-001`, `BUSR-03` |
| **Hùng (Chuyển ngành)** | Tăng ca đột xuất, áp lực nợ task quá hạn | Tạm dừng lộ trình mà không bị phạt, hoặc dời lịch 1 lộ trình bằng AI | Tính năng Pause Roadmap (Domino Shift) & Thông báo Email quá hạn + Single-Roadmap AI Reschedule | `FR-PAUSE-001`, `FR-PAUSE-002`, `FR-ADAPT-001..003`, `BUSR-06`, `BUSR-07` |
| **Mai (Ôn chứng chỉ)** | Chỉ xem lịch trên Google Calendar điện thoại | Đồng bộ lịch 2 chiều có kiểm soát với ứng dụng lịch cá nhân | Đồng bộ lịch 2 chiều có kiểm soát (Free/Busy Inbound + Official Outbound) & WebCal Feed bảo mật token (`.ics`) | `FR-CALENDAR-001`, `FR-CALENDAR-002`, `FR-CALENDAR-003`, `BUSR-08` |
| **Mai (Ôn chứng chỉ)** | Học xong hay quên, thiếu đúc kết thi cử | Bắt buộc ghi nhận tóm tắt cốt lõi và tổng kết tuần | Trường bắt buộc Key Takeaways & Trợ lý AI Review định kỳ | `FR-SESSION-002`, `FR-REPORT-002`, `BUSR-09` |

---

## 5. Góc Nhìn Cố Vấn Khóa Luận (Defense Guidance on Actors & Personas)

### Câu hỏi Phản biện 1: "Tại sao trong tài liệu của em lại phân chia thành 'System Actors' và 'User Personas'? Sao không gộp chung lại làm một cho đơn giản?"
> **Gợi ý trả lời bảo vệ:**  
> *"Thưa Thầy/Cô, việc phân định rõ giữa System Actors và User Personas là chuẩn mực bắt buộc trong Công nghệ Phần mềm chuyên nghiệp (chuẩn ISO/IEC/IEEE 29148 và phương pháp UCD):*  
> *1. **System Actor là khái niệm kiến trúc kỹ thuật:** Dùng để trả lời câu hỏi 'Hệ thống có những vai trò logic nào tương tác qua ranh giới hệ thống (System Boundary) và cơ chế phân quyền bảo mật ra sao?'. Hệ thống của em có **8 tác nhân chuẩn hóa (`ACT-00`..`ACT-07`)**: `Guest (ACT-00)`, `Registered User (ACT-01 — abstract)`, `Learner (ACT-02)`, `Administrator (ACT-03)`, `External LLM Provider (ACT-04)`, `Payment Gateway (ACT-05)`, `External Calendar Service (ACT-06)`, và `Email Notification Service (ACT-07)`, trong khi các thành phần nội bộ (`PostgreSQL`, `Redis`, `Taskiq Worker/Scheduler`, `Internal AI Harness`) nằm hoàn toàn bên trong System Boundary.*  
> *2. **User Persona là công cụ thiết kế hành vi và tâm lý học:** Dùng để trả lời câu hỏi 'Người dùng thực tế là ai, họ có nỗi đau gì và họ sử dụng hệ thống trong ngữ cảnh nào?'. Cả 3 Persona An, Hùng và Mai ngoài đời đều đóng vai trò là `Learner Actor` khi đăng nhập, nhưng họ có quỹ thời gian khác nhau (Mode A vs Mode B) và thói quen khác nhau (WebCal vs Workspace Pomodoro). Sự phân định này giúp hệ thống vừa chặt chẽ về mặt kiến trúc phần mềm, vừa tối ưu công thái học cho người dùng thật."*

### Câu hỏi Phản biện 2: "Tại sao hệ thống chỉ thiết kế Web Admin Portal tối giản (3 màn hình) mà không xây dựng một hệ thống CMS/Admin đồ sộ? Thiết kế này có đáp ứng tiêu chuẩn đồ án không?"
> **Gợi ý trả lời bảo vệ:**  
> *"Thưa Thầy/Cô, đây là một **Quyết định Thiết kế có chủ đích (Deliberate Architectural Decision)** nhằm bảo vệ phạm vi cốt lõi của đồ án và tuân thủ nghiêm ngặt chuẩn mực Kỹ thuật Phần mềm:*  
> *1. Trọng tâm cốt lõi của FocusFlow là giải quyết bài toán tự học thích ứng cho người dùng cá nhân (End-User Value với Core Domain là Adaptive Planning & Focus Execution), không phải là hệ thống thương mại điện tử hay CMS tổng hợp.*  
> *2. Để đảm bảo tính hoàn thiện và chuẩn mực UML (tránh lỗi Orphan Actor), hệ thống đã xây dựng **Web Admin Portal tối giản với đầy đủ 3 màn hình nghiệp vụ thiết yếu**: (a) Xác thực phân quyền RBAC (`role = 'ADMIN'`), (b) Quản trị danh sách người dùng, chuyển đổi Tier và cấp phát Quota AI, và (c) Dashboard giám sát chỉ số vận hành và tổng lượng token AI tiêu thụ.*  
> *3. Quyết định giới hạn phạm vi quản trị ở mức tối giản này giúp nhóm vừa đảm bảo tính trọn vẹn của hệ thống, vừa bảo vệ tiến độ 15 tuần của đồ án, tập trung 100% nguồn lực hoàn thiện Study Workspace, thuật toán Domino Shift và tích hợp an toàn AI đạt điểm chất lượng cao nhất."*
