# PROJECT STATUS REPORT
## (BÁO CÁO TÌNH TRẠNG DỰ ÁN)

**Dự Án:** FocusFlow — Hệ thống hỗ trợ lập kế hoạch và thực thi lộ trình tự học thích ứng tích hợp AI  
**Kỳ Báo Cáo:** Tuần 5 - Từ ngày 25/09/2026 đến ngày 01/10/2026  
**Người Lập Báo Cáo:** Vũ Toàn Thắng (Project Manager)  
**Gửi Đến:** ThS. Vũ Đình Bảo (Giảng viên Hướng dẫn — Khoa Công nghệ Thông tin, HCMUTE)  
**Ngày Gửi:** 01/10/2026  

---

### 1. EXECUTIVE SUMMARY

Đánh giá tổng quan về "sức khỏe" dự án thông qua hệ thống đèn tín hiệu (RAG Status).

| Hạng mục | Trạng thái | Diễn giải ngắn gọn |
|---|---|---|
| Tiến độ (Schedule) | <span style="color:#2e7d32">●</span> **Green** | Hoàn thành 100% các biểu đồ tương tác & trạng thái UML (Sequence, State Machine); các bản thiết kế Kiến trúc và CSDL đạt 80–85%, bám sát đúng kế hoạch hướng tới mốc Milestone 2 (08/10/2026). |
| Phạm vi (Scope) | <span style="color:#2e7d32">●</span> **Green** | Toàn bộ thiết kế kiến trúc Hexagonal và mô hình quan hệ CSDL bám sát đúng 8 nhóm yêu cầu chức năng (FRs) trong hồ sơ SRS v1.0, không phát sinh Scope Creep. |
| Chất lượng (Quality) | <span style="color:#2e7d32">●</span> **Green** | Hệ thống được mô hình hóa theo chuẩn UML 2.5.1, kiến trúc Hexagonal phân tách Ports & Adapters rõ ràng, CSDL đạt chuẩn hóa 3NF/BCNF với ma trận Index và Constraint toàn vẹn. |
| Rủi ro (Risk) | <span style="color:#2e7d32">●</span> **Green** | Các bài toán kỹ thuật phức tạp (nguy cơ quá tải I/O nhịp tim phiên học và kiểm soát vòng đời quota khi đứt kết nối streaming SSE) đều đã được giải quyết triệt để ở tầng thiết kế. |

**Chú thích:**
- <span style="color:#2e7d32">●</span> **Green (Xanh):** Ổn định, không có vấn đề lớn.
- <span style="color:#f57c00">●</span> **Amber (Vàng):** Có rủi ro tiềm ẩn hoặc chậm trễ nhẹ, cần chú ý.
- <span style="color:#c62828">●</span> **Red (Đỏ):** Vấn đề nghiêm trọng, cần sự can thiệp ngay lập tức từ cấp trên.

---

### 2. HOẠT ĐỘNG ĐÃ HOÀN THÀNH TRONG KỲ (ACCOMPLISHMENTS)

Liệt kê các công việc đã làm được trong tuần qua so với kế hoạch ban đầu.

| ID | Công việc / Hạng mục | Người phụ trách | Kết quả | Ghi chú |
|---|---|---|---|---|
| 3.2 | Hoàn thiện toàn bộ các biểu đồ hoạt động (Activity Diagrams) | Phan Đình Duẩn | Hoàn thành 100% | Bổ sung đầy đủ kịch bản gián đoạn phiên học, dừng học sớm và cơ chế hoàn trả task dở dang về Backlog. |
| 3.3 | Thiết kế Sequence Diagrams (Workflow M2, Deterministic Overdue Shift, WebCal Feed) | Vũ Toàn Thắng | Hoàn thành 100% | Đặc tả chi tiết 4 kịch bản tương tác UML 2.5.1 giữa Frontend, Backend Service Layer, Redis, PostgreSQL và LLM Provider. |
| 3.4 | Thiết kế State Machine Diagrams (Vòng đời Roadmap, Task, Study Session, Schedule Proposal) | Vũ Toàn Thắng | Hoàn thành 100% | Định nghĩa tường minh các trạng thái nghiệp vụ, guard conditions và hành vi chuyển đổi trạng thái của hệ thống. |
| 4.1 | Thiết kế kiến trúc phần mềm tổng thể (Hexagonal Architecture / C4 Container & Component) | Vũ Toàn Thắng | Hoàn thành 85% | Phân định rạch ròi Domain Layer, Application Use Cases, Ports và Inbound/Outbound Adapters; xây dựng dự thảo 6 bản ghi ADR. |
| 4.2 | Thiết kế sơ đồ cơ sở dữ liệu quan hệ (Database Diagram / Relational Schema) & DDL PostgreSQL 16 | Vũ Toàn Thắng | Hoàn thành 85% | Hoàn thiện mô hình vật lý 10 bảng cốt lõi, chuẩn hóa kiểu dữ liệu, khóa chính UUIDv7 và khóa ngoại ON DELETE CASCADE. |

---

### 3. KẾ HOẠCH THỰC HIỆN KỲ TỚI (PLANNED ACTIVITIES)

Danh sách các công việc dự kiến làm trong tuần tiếp theo, bao gồm cả các thay đổi về nguồn lực hoặc lịch trình nếu có.

| ID | Công việc dự kiến | Người phụ trách | Deadline | Mức độ ưu tiên |
|---|---|---|---|---|
| 4.3 | Hoàn thiện nghiệm thu Từ điển dữ liệu (Data Dictionary), Index Matrix & Ràng buộc toàn vẹn CSDL | Vũ Toàn Thắng | 07/10/2026 | High |
| 4.4 | Chuẩn hóa và rà soát bộ 6 Architecture Decision Records (ADR-001 đến ADR-006) | Vũ Toàn Thắng | 08/10/2026 | High |
| 4.5 | Rà soát, thẩm định và đối chiếu tính nhất quán chéo SRS – UML – Architecture – Database (Audit Milestone 2) | Vũ Toàn Thắng & Phan Đình Duẩn | 08/10/2026 | High |
| 5.1 | Khởi tạo cấu trúc Repository, cấu hình dự án chuẩn & dựng khung môi trường Docker Compose mẫu chuẩn bị cho Phase 3 | Phan Đình Duẩn | 08/10/2026 | Medium |

---

### 4. QUẢN LÝ VẤN ĐỀ & RỦI RO (ISSUES & RISKS)

Phần quan trọng nhất để báo cáo các vấn đề mở (Open Issues) và kế hoạch hành động.

| Loại (Type) | Mô tả vấn đề / Rủi ro | Mức độ tác động | Kế hoạch giải quyết (Action Plan) | Người xử lý | Trạng thái |
|---|---|---|---|---|---|
| Issue | Tần suất gửi tín hiệu nhịp tim (Heartbeat 30s) trong phiên học Pomodoro có nguy cơ gây quá tải I/O ghi trực tiếp vào CSDL PostgreSQL khi số lượng phiên tăng. | Cao | Sử dụng Redis làm bộ nhớ đệm tạm thời (Session State Buffer) với cơ chế TTL 90s; backend chỉ kết xuất và ghi nhận kết quả tổng kết buổi học vào PostgreSQL khi kết thúc phiên hoặc xử lý gián đoạn. | Vũ Toàn Thắng | Closed |
| Risk | Nguy cơ thất thoát hạn ngạch hoặc trừ nhầm Quota AI của người dùng khi kết nối SSE streaming bị ngắt quãng giữa chừng hoặc LLM Provider trả lỗi kết nối. | Trung bình | Thiết kế Quota Manager theo mô hình 2 pha: Tạm giữ hạn ngạch (Reserve) trước khi gọi LLM -> Cam kết trừ thực tế (Commit) khi stream hoàn tất hoặc Hoàn trả (Release/Rollback) nếu stream đứt gãy trước khi có dữ liệu hợp lệ. | Vũ Toàn Thắng | Closed |

---

### 5. CÁC MỐC QUAN TRỌNG SẮP TỚI (UPCOMING MILESTONES)

*Theo dõi các mốc bàn giao chính (Deliverables) để đảm bảo không bị trượt deadline tổng.*

| Mốc sự kiện (Milestone) | Ngày theo kế hoạch | Ngày dự kiến thực tế | Trạng thái |
|---|---|---|---|
| Hoàn thành Thiết kế Kiến trúc & Database Diagram (Milestone 2) | 08/10/2026 | 08/10/2026 | On-track |
| Hoàn thiện Bộ chức năng cốt lõi MVP & Tích hợp AI (Milestone 3) | 12/11/2026 | 12/11/2026 | On-track |
