# PROJECT STATUS REPORT
## (BÁO CÁO TÌNH TRẠNG DỰ ÁN)

**Dự Án:** FocusFlow — Hệ thống hỗ trợ lập kế hoạch và thực thi lộ trình tự học thích ứng tích hợp AI  
**Kỳ Báo Cáo:** Tuần 8 - Từ ngày 16/10/2026 đến ngày 22/10/2026  
**Người Lập Báo Cáo:** Vũ Toàn Thắng
**Gửi Đến:** ThS. Vũ Đình Bảo (Giảng viên Hướng dẫn — Khoa Công nghệ Thông tin, HCMUTE)  
**Ngày Gửi:** 23/10/2026  

---

### 1. EXECUTIVE SUMMARY (TỔNG QUAN ĐIỀU HÀNH)

Đánh giá tổng quan về "sức khỏe" dự án thông qua hệ thống đèn tín hiệu (RAG Status).

| Hạng mục | Trạng thái | Diễn giải ngắn gọn |
| :--- | :---: | :--- |
| **Tiến độ (Schedule)** | <span style="color:#2e7d32">●</span> **Green** | Hoàn thành 100% mục tiêu Sprint 1, nghiệm thu thành công **Milestone 2.5 (Nền tảng hệ thống, Xác thực & Cấu hình thời gian rảnh)** đúng hạn chót 22/10/2026; đưa đèn tiến độ từ Amber (Tuần 7) trở lại Green. Toàn bộ hạ tầng monorepo gồm backend FastAPI (Python 3.12+ / Kiến trúc Lục giác), frontend Angular 21 (Signals & Standalone Components), PostgreSQL 16 (Alembic Migrations 10 bảng UUIDv7) và Docker Compose 5 dịch vụ đã tích hợp thông suốt, sẵn sàng kích hoạt Sprint 2. |
| **Phạm vi (Scope)** | <span style="color:#2e7d32">●</span> **Green** | Giữ vững và bảo toàn 8 nhóm yêu cầu chức năng cốt lõi (FR-01 đến FR-08); bám sát bộ 10 bản ghi quyết định kiến trúc (ADR-001 đến ADR-010). Toàn bộ các module Sprint 1 (FR-AUTH, FR-AVAIL) bám sát chặt chẽ đặc tả SRS v1.1 và cơ sở dữ liệu vật lý. Hoàn toàn không phát sinh Scope Creep. |
| **Chất lượng (Quality)** | <span style="color:#2e7d32">●</span> **Green** | Tích hợp thành công pipeline CI/CD GitHub Actions kiểm thử tự động; nghiệm thu trọn vẹn 10 bảng cơ sở dữ liệu với Alembic Migrations tự động và khóa chính UUIDv7 RFC 9562; hoàn tất 100% bộ Interactive High-fidelity Prototype trên Figma (bao gồm cả phân hệ Analytics và Admin Portal); thiết lập hoàn chỉnh bộ 5 bài toán kiểm thử vàng (Golden Dataset) và Mock LLM Adapter theo ADR-009 cho Sprint 2. |
| **Rủi ro (Risk)** | <span style="color:#2e7d32">●</span> **Green** | Đóng dứt điểm rủi ro xung đột UUIDv7 & Alembic migration nhờ kịch bản migration có kiểm soát dependency graph; kiểm soát tốt rủi ro UI Jank của đồng hồ Pomodoro qua kiểm chứng PoC Web Worker và Signals trên Angular 21; thiết lập phương án kiểm soát rủi ro độ trễ sinh phản hồi từ LLM bằng giao thức Server-Sent Events (SSE - ADR-005) kết hợp Pydantic Schema Retry Loop. |

**Chú thích:**
- <span style="color:#2e7d32">●</span> **Green (Xanh):** Ổn định, đúng tiến độ, không có vấn đề lớn cản trở.
- <span style="color:#f57c00">●</span> **Amber (Vàng):** Có rủi ro tiềm ẩn hoặc chậm trễ nhẹ, cần chú ý theo dõi.
- <span style="color:#c62828">●</span> **Red (Đỏ):** Vấn đề nghiêm trọng, trượt hạn hoặc có lỗi chặn cần sự can thiệp ngay lập tức từ cấp trên.

---

### 2. HOẠT ĐỘNG ĐÃ HOÀN THÀNH TRONG KỲ (ACCOMPLISHMENTS)

Liệt kê các công việc đã làm được trong tuần qua so với kế hoạch ban đầu (bám sát Mục 3 của Báo cáo Tuần 7).

| ID | Công việc / Hạng mục | Người phụ trách | Kết quả | Ghi chú |
| :---: | :--- | :---: | :---: | :--- |
| **5.1** | Hoàn tất cấu hình Repository, hoàn thiện Docker Compose (FastAPI, Angular 21, PostgreSQL 16, Redis 7, Celery Worker/Beat) & CI/CD Actions | Phan Đình Duẩn | Hoàn thành 100% | Thiết lập cấu trúc Monorepo chuẩn; tích hợp thành công kịch bản Alembic Database Migrations cho toàn bộ 10 bảng CSDL với khóa chính UUIDv7 RFC 9562; cấu hình mạng và volume đồng bộ giữa 5 dịch vụ Docker. |
| **5.2** | Xây dựng hoàn chỉnh Module Xác thực, Phân quyền RBAC (User/Admin) & Hồ sơ người dùng (FR-AUTH: Đăng ký/Đăng nhập, JWT HttpOnly Cookie, Redis RTR & Blacklist, Argon2id) | Phan Đình Duẩn | Hoàn thành 100% | Hiện thực hóa trọn vẹn luồng Đăng ký/Đăng nhập, JWT HttpOnly Cookie bảo mật, Redis Token Store RTR (Refresh Token Rotation) & Revocation Blacklist, mã hóa mật khẩu Argon2id và Middleware kiểm tra RBAC Gate. |
| **5.3** | Xây dựng hoàn chỉnh Module Cấu hình thời gian rảnh lai (FR-AVAIL: Mode A Hạn ngạch tuần & Mode B Khung giờ cố định tuần, validation logic) | Vũ Toàn Thắng | Hoàn thành 100% | Cài đặt nghiệp vụ xác thực khung giờ không chồng lấn, kiểm tra trần giờ học tối đa theo tuần; định nghĩa các Value Objects và Domain Services bám sát SRS v1.1; kiểm thử unit test thuật toán xác thực thời gian rảnh đạt 100% pass. |
| **6.1** | Thiết lập nền tảng tích hợp AI với Mock LLM Adapter và bộ khung kiểm thử Evaluation Harness (theo ADR-009) chuẩn bị cho Sprint 2 | Vũ Toàn Thắng | Hoàn thành 100% | Xây dựng Driven Port LLMPort và Mock Adapter; nạp bộ 5 bài toán chuẩn hóa vàng (Golden Dataset) bao quát các kịch bản học tập; thiết lập cơ chế 3 lớp Strict Constraint Validation kiểm định giờ học thực tế sẵn sàng cho Sprint 2. |
| **5.0** | Hoàn thiện 100% High-fidelity Interactive Prototype trên Figma & Xây dựng Design System Spartan UI + Tailwind CSS | Vũ Toàn Thắng & Phan Đình Duẩn | Hoàn thành 100% | Hoàn tất 10% còn lại của phân hệ Analytics và Admin Portal (Quản trị người dùng & Override Quota AI); toàn bộ tương tác động của 5 phân hệ cốt lõi đã được nghiệm thu và chuyển giao cho lập trình UI Angular 21. |

---

### 3. KẾ HOẠCH THỰC HIỆN KỲ TỚI (PLANNED ACTIVITIES)

Danh sách các công việc dự kiến làm trong tuần tiếp theo (Tuần 9: từ 23/10/2026 đến 29/10/2026) — Tập trung toàn lực vào **Phase Three: Lập trình chức năng cốt lõi MVP & Tích hợp AI (Sprint 2 - AI Roadmap Generation & Approval Flow)**:

| ID | Công việc dự kiến | Người phụ trách | Deadline | Mức độ ưu tiên |
| :---: | :--- | :---: | :---: | :---: |
| **6.1** | Tích hợp Gemini 2.5 Flash API với Pydantic Structured Outputs & JSON Schema Validation Gate (FR-AI-PLAN) | Vũ Toàn Thắng | 27/10/2026 | High |
| **6.2** | Xây dựng luồng sinh Milestones Cấp 1 & Nhiệm vụ Cấp 2 thích ứng kết hợp Learner Profile Memory & Anti-Loop (ADR-010) | Vũ Toàn Thắng | 29/10/2026 | High |
| **6.3** | Phát triển giao diện Angular 21 cho Cổng kiểm duyệt kế hoạch & chỉnh sửa đề xuất lộ trình học tập (FR-AI-APPROVAL) | Vũ Toàn Thắng & Phan Đình Duẩn | 29/10/2026 | High |
| **7.1** | Khởi động phát triển Không gian phiên học & Study Tool Suite (Pomodoro Timer, Web Worker, Ambient Sound) (FR-EXEC) | Phan Đình Duẩn | 29/10/2026 | Medium |
| **6.0** | Tổ chức kiểm thử đánh giá độ chính xác của AI sinh lộ trình bằng Evaluation Harness trên 5 Golden Datasets | Vũ Toàn Thắng | 29/10/2026 | High |

---

### 4. QUẢN LÝ VẤN ĐỀ & RỦI RO (ISSUES & RISKS)

Phần quan trọng nhất để báo cáo các vấn đề mở (Open Issues) và kế hoạch hành động.

| Loại (Type) | Mô tả vấn đề / Rủi ro | Mức độ tác động | Kế hoạch giải quyết (Action Plan) | Người xử lý | Trạng thái |
| :---: | :--- | :---: | :--- | :---: | :---: |
| **Risk** | Nguy cơ xung đột kiểu dữ liệu và thứ tự thực thi khóa ngoại UUIDv7 giữa các phiên bản PostgreSQL 16 và Alembic Migrations tự động. | Trung bình | Viết migration scripts ban đầu thủ công có kiểm soát thứ tự bảng; kết hợp thư viện `uuid6` chuẩn RFC 9562; đã kiểm thử upgrade/downgrade tự động thành công 100% trong Docker. | Phan Đình Duẩn | Closed |
| **Risk** | Rủi ro rò rỉ bộ nhớ hoặc giật lag giao diện (UI Jank) trên trình duyệt khi vận hành đồng hồ đếm ngược Pomodoro 25 phút kèm phát âm thanh nền và nhịp tim Heartbeat. | Thấp | Áp dụng Signals trên Angular 21 (Fine-grained Change Detection), xây dựng PoC Web Worker xử lý đếm giây độc lập với chu kỳ render của main thread; đã kiểm chứng sơ bộ qua Chrome DevTools Memory Profiler không có rò rỉ bộ nhớ. | Phan Đình Duẩn | Open |
| **Risk** | Độ trễ phản hồi từ LLM API khi sinh chi tiết Lộ trình 2 cấp (ước tính 3–7 giây) có thể gây trải nghiệm chờ đợi không tối ưu cho người dùng và nguy cơ timeout kết nối HTTP thông thường. | Trung bình | Triển khai giao thức streaming SSE (Server-Sent Events) theo ADR-005 để hiển thị tiến độ phân rã lộ trình theo thời gian thực (Milestone -> Task); áp dụng cơ chế Retry tối đa 3 lần với Pydantic schema validation gate; cung cấp Skeleton UI và thanh trạng thái tiến trình sinh động. | Vũ Toàn Thắng | Open |

---

### 5. CÁC MỐC QUAN TRỌNG SẮP TỚI (UPCOMING MILESTONES)

Theo dõi các mốc bàn giao chính (Deliverables) để đảm bảo không bị trượt deadline tổng.

| Mốc sự kiện (Milestone) | Ngày theo kế hoạch | Ngày dự kiến thực tế | Trạng thái |
| :--- | :---: | :---: | :---: |
| **Hoàn thành Thiết kế Kiến trúc & Database Diagram (Milestone 2)** | 08/10/2026 | 08/10/2026 | Completed |
| **Hoàn thành Sprint 1: Nền tảng hệ thống, Xác thực & Cấu hình Thời gian rảnh (Milestone 2.5)** | 22/10/2026 | 22/10/2026 | Completed |
| **Hoàn thành Sprint 2: Lập kế hoạch AI & Cổng phê duyệt lộ trình thích ứng** | 29/10/2026 | 29/10/2026 | On-track |
| **Hoàn thiện Bộ chức năng cốt lõi MVP & Tích hợp AI (Milestone 3)** | 12/11/2026 | 12/11/2026 | On-track |
