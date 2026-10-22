# PROJECT STATUS REPORT
## (BÁO CÁO TÌNH TRẠNG DỰ ÁN)

**Dự Án:** FocusFlow — Hệ thống hỗ trợ lập kế hoạch và thực thi lộ trình tự học thích ứng tích hợp AI  
**Kỳ Báo Cáo:** Tuần 7 - Từ ngày 09/10/2026 đến ngày 15/10/2026  
**Người Lập Báo Cáo:** Vũ Toàn Thắng  
**Gửi Đến:** ThS. Vũ Đình Bảo (Giảng viên Hướng dẫn — Khoa Công nghệ Thông tin, HCMUTE)  
**Ngày Gửi:** 16/10/2026  

---

### 1. EXECUTIVE SUMMARY (TỔNG QUAN ĐIỀU HÀNH)

Đánh giá tổng quan về "sức khỏe" dự án thông qua hệ thống đèn tín hiệu (RAG Status).

| Hạng mục | Trạng thái | Diễn giải ngắn gọn |
| :--- | :---: | :--- |
| **Tiến độ (Schedule)** | <span style="color:#f57c00">●</span> **Amber** | Khởi động Phase Three (Sprint 1) với các module nền tảng kỹ thuật và xác thực. Do ưu tiên dành nửa đầu tuần hoàn thiện bộ Interactive UI Prototype (Figma) và ban hành khung kiểm thử AI (ADR-009, ADR-010), tiến độ lập trình các module 5.1–5.3 dời nhẹ 1 tuần để hoàn tất đồng bộ vào 22/10/2026 (Milestone 2.5). Không ảnh hưởng đến hạn chót Milestone 3 (12/11/2026). |
| **Phạm vi (Scope)** | <span style="color:#2e7d32">●</span> **Green** | Giữ vững phạm vi 8 nhóm yêu cầu chức năng cốt lõi (FR-01 đến FR-08); hoàn thiện chuẩn hóa thiết kế với 10 bản ghi ADR (bổ sung ADR-009 về AI Evaluation Harness và ADR-010 về Learner Profile Memory & Anti-Loop). Hoàn toàn không phát sinh Scope Creep. |
| **Chất lượng (Quality)** | <span style="color:#2e7d32">●</span> **Green** | Hoàn tất đợt đại kiểm toán kế hoạch WBS & Gantt Chart 15 tuần (`wbs-gantt-plan-audit.md`), phủ kín 100% thanh tiến độ trực quan trên lưới 105 ngày; đồng bộ hóa thiết kế giao diện theo bộ Design System Spartan UI và Tailwind v4. Chuẩn bị sẵn sàng bộ 5 bài toán kiểm thử vàng (Golden Dataset) cho AI. |
| **Rủi ro (Risk)** | <span style="color:#2e7d32">●</span> **Green** | Xử lý triệt để nguy cơ nghẽn cổ chai nhân lực ở nửa cuối Phase 3 bằng việc tái phân bổ WBS 8.3 cho Phan Đình Duẩn; kiểm soát tốt rủi ro re-render của đồng hồ Pomodoro thông qua cơ chế Signals của Angular 19 (ADR-003); kiểm soát an toàn Quota AI 2-phase. |

**Chú thích:**
- <span style="color:#2e7d32">●</span> **Green (Xanh):** Ổn định, đúng tiến độ, không có vấn đề lớn cản trở.
- <span style="color:#f57c00">●</span> **Amber (Vàng):** Có rủi ro tiềm ẩn hoặc chậm trễ nhẹ, cần chú ý theo dõi.
- <span style="color:#c62828">●</span> **Red (Đỏ):** Vấn đề nghiêm trọng, trượt hạn hoặc có lỗi chặn cần sự can thiệp ngay lập tức từ cấp trên.

---

### 2. HOẠT ĐỘNG ĐÃ HOÀN THÀNH TRONG KỲ (ACCOMPLISHMENTS)

Liệt kê các công việc đã làm được trong tuần qua so với kế hoạch ban đầu (bám sát Mục 3 của Báo cáo Tuần 6).

| ID | Công việc / Hạng mục | Người phụ trách | Kết quả | Ghi chú |
| :---: | :--- | :---: | :---: | :--- |
| **5.1** | Hoàn thiện cấu hình Repository, hoàn tất Docker Compose (PostgreSQL 16, Redis 7, Celery Worker & Beat) & CI/CD Pipeline | Phan Đình Duẩn | Hoàn thành 60% | Thiết lập cấu trúc Monorepo chuẩn: Backend FastAPI theo Kiến trúc Lục giác (Hexagonal Architecture), Frontend Angular 19 SPA (Standalone Components & Signals); hoàn tất kịch bản Docker Compose 5 dịch vụ; chuẩn bị migration DDL 10 bảng PostgreSQL 16 với UUIDv7. |
| **5.2** | Xây dựng Module Xác thực & Quản trị Hồ sơ người dùng (FR-AUTH: Đăng ký/Đăng nhập, JWT Cookie HttpOnly, Redis Token Store RTR, Argon2id) | Phan Đình Duẩn | Hoàn thành 40% | Thiết kế schema bảng `users`, `user_roles`; định nghĩa Driven Port `TokenStorePort` và Adapter mã hóa mật khẩu `Argon2id`; thiết lập cấu trúc Authentication Router và Middleware kiểm tra RBAC Gate. |
| **5.3** | Xây dựng Module Cấu hình thời gian rảnh lai (FR-AVAIL: Mode A Hạn ngạch tuần & Mode B Khung giờ cố định tuần, validation logic) | Vũ Toàn Thắng | Hoàn thành 30% | Hoàn thành đặc tả chi tiết thuật toán kiểm tra trần giờ rảnh; thiết kế schema bảng `user_availability`; xây dựng Value Objects và bộ luật nghiệp vụ xác thực khung giờ không chồng lấn. |
| **6.1** | Khởi động Module Lập kế hoạch AI: Tích hợp LLMPort Adapter với Gemini API, Pydantic Structured Outputs và JSON Schema Validation Gate | Vũ Toàn Thắng | Hoàn thành 100% (Phần nghiên cứu & kiến trúc) | Hoàn thiện và phê duyệt 2 bản ghi quyết định kiến trúc cốt lõi: **ADR-009** (Evaluation Harness & 3-layer Constraint Validation) và **ADR-010** (Learner Profile Memory & Thuật toán chống lặp kế hoạch Anti-Loop). |
| **5.0** | Thiết kế High-fidelity Interactive Prototype trên Figma & Xây dựng Design System (Hạng mục bổ sung phục vụ Phase 3) | Vũ Toàn Thắng & Phan Đình Duẩn | Hoàn thành 90% | Xây dựng hoàn chỉnh bộ Design System (tokens, màu sắc, kiểu chữ) kết hợp Spartan UI và Tailwind v4; hoàn thiện prototype động trên Figma cho 4/5 phân hệ (Onboarding, Roadmap, Pomodoro Session, Calendar); phân hệ Analytics đạt 80%. |
| **Audit** | Đại kiểm toán Kế hoạch WBS & Biểu đồ tiến độ Gantt 15 tuần (`wbs-gantt-plan-audit.md`) | Vũ Toàn Thắng & Phan Đình Duẩn | Hoàn thành 100% | Phủ kín dải màu tiến độ 105 ngày trên biểu đồ Gantt; giải quyết nguy cơ nghẽn cổ chai nhân lực bằng việc chuyển WBS 8.3 sang Phan Đình Duẩn; chuẩn hóa công thức Excel tự động cho 12 dòng nhóm cấp 1. |

---

### 3. KẾ HOẠCH THỰC HIỆN KỲ TỚI (PLANNED ACTIVITIES)

Danh sách các công việc dự kiến làm trong tuần tiếp theo (Tuần 8: từ 16/10/2026 đến 22/10/2026) — Tập trung dứt điểm Sprint 1 để đạt **Milestone 2.5**:

| ID | Công việc dự kiến | Người phụ trách | Deadline | Mức độ ưu tiên |
| :---: | :--- | :---: | :---: | :---: |
| **5.1** | Hoàn thành 100% cấu hình Repository, tích hợp Alembic Migration 10 bảng PostgreSQL 16 (UUIDv7), hoàn thiện Docker Compose & CI/CD Actions | Phan Đình Duẩn | 19/10/2026 | High |
| **5.2** | Hoàn thiện 100% Module Xác thực, Phân quyền RBAC (User/Admin) & Hồ sơ người dùng (FR-AUTH: Đăng ký/Đăng nhập, JWT HttpOnly Cookie, Redis RTR & Blacklist, Argon2id) | Phan Đình Duẩn | 22/10/2026 | High |
| **5.3** | Hoàn thiện 100% Module Cấu hình thời gian rảnh lai (FR-AVAIL: Mode A Hạn ngạch tuần & Mode B Khung giờ cố định tuần, validation logic) | Vũ Toàn Thắng | 22/10/2026 | High |
| **6.1** | Thiết lập nền tảng tích hợp AI với Mock LLM Adapter và bộ khung kiểm thử Evaluation Harness (theo ADR-009) chuẩn bị cho Sprint 2 | Vũ Toàn Thắng | 22/10/2026 | High |
| **5.0** | Hoàn thiện 10% còn lại của High-fidelity Interactive Prototype trên Figma (hoàn tất phân hệ Analytics và Admin Portal) | Vũ Toàn Thắng & Phan Đình Duẩn | 18/10/2026 | Medium |

---

### 4. QUẢN LÝ VẤN ĐỀ & RỦI RO (ISSUES & RISKS)

Phần quan trọng nhất để báo cáo các vấn đề mở (Open Issues) và kế hoạch hành động.

| Loại (Type) | Mô tả vấn đề / Rủi ro | Mức độ tác động | Kế hoạch giải quyết (Action Plan) | Người xử lý | Trạng thái |
| :---: | :--- | :---: | :--- | :---: | :---: |
| **Issue** | Nguy cơ nghẽn cổ chai nhân lực (Resource Overallocation) của Vũ Toàn Thắng ở nửa cuối Phase 3 khi phải đảm nhiệm 5 module phức tạp đồng thời. | Cao | Đã kiểm toán qua `wbs-gantt-plan-audit.md` và điều chuyển quyền phụ trách chính của **WBS 8.3** (Quota Guard Middleware & Mock Upgrade Sandbox) sang cho Phan Đình Duẩn; giải phóng tải để tập trung vào thuật toán thích ứng và AI Review. | Vũ Toàn Thắng & Phan Đình Duẩn | Closed |
| **Issue** | Thiếu hụt cơ chế đánh giá độc lập chất lượng đầu ra AI (Evaluation Harness) dẫn đến nguy cơ phụ thuộc hoàn toàn vào API Gemini khi kiểm thử tự động. | Cao | Ban hành **ADR-009**, xây dựng Mock LLM Provider Adapter với 5 bài toán chuẩn hóa vàng (Golden Dataset), thiết lập cơ chế 3 lớp Strict Constraint Validation kiểm định giờ học thực tế. | Vũ Toàn Thắng | Closed |
| **Risk** | Rủi ro rò rỉ bộ nhớ hoặc giật lag giao diện (UI Jank) trên trình duyệt khi vận hành đồng hồ đếm ngược Pomodoro 25 phút kèm phát âm thanh nền và nhịp tim Heartbeat. | Trung bình | Áp dụng triệt để cơ chế Signals của Angular 19 (Zone-less / Fine-grained Change Detection), tách biệt Web Worker xử lý đếm thời gian thực không phụ thuộc vào chu kỳ render của giao diện chính; kiểm chứng bộ nhớ qua Chrome DevTools Memory Profiler. | Phan Đình Duẩn | Open |
| **Risk** | Nguy cơ xung đột kiểu dữ liệu và thứ tự thực thi khóa ngoại UUIDv7 giữa các phiên bản PostgreSQL 16 và Alembic Migrations tự động. | Trung bình | Viết migration scripts ban đầu thủ công có kiểm soát thứ tự phụ thuộc bảng (Dependency Graph); sử dụng hàm `gen_random_uuid()` kết hợp thư viện `uuid6` chuẩn hóa theo RFC 9562; bổ sung test case migration upgrade/downgrade tự động trong pipeline CI/CD. | Phan Đình Duẩn | Open |

---

### 5. CÁC MỐC QUAN TRỌNG SẮP TỚI (UPCOMING MILESTONES)

Theo dõi các mốc bàn giao chính (Deliverables) để đảm bảo không bị trượt deadline tổng.

| Mốc sự kiện (Milestone) | Ngày theo kế hoạch | Ngày dự kiến thực tế | Trạng thái |
| :--- | :---: | :---: | :---: |
| **Hoàn thành Thiết kế Kiến trúc & Database Diagram (Milestone 2)** | 08/10/2026 | 08/10/2026 | Completed |
| **Hoàn thành Sprint 1: Nền tảng hệ thống, Xác thực & Cấu hình Thời gian rảnh (Milestone 2.5)** | 15/10/2026 | 22/10/2026 | In-progress |
| **Hoàn thiện Bộ chức năng cốt lõi MVP & Tích hợp AI (Milestone 3)** | 12/11/2026 | 12/11/2026 | On-track |
