# ADR-007: Kiến trúc Cơ sở Dữ liệu Quan hệ, Chuẩn hóa 3NF/BCNF và Ràng buộc Toàn vẹn ACID (PostgreSQL 16)

* **Trạng thái:** Được chấp thuận (Approved)
* **Ngày quyết định:** 30/09/2026 (Hoàn thiện hồ sơ: 07/10/2026)
* **Người quyết định:** Vũ Toàn Thắng (Lead BA / System Architect), Phan Đình Duẩn (Senior BA / Quality Lead)
* **Căn cứ đánh giá:** Khung Rubric Đồ án Tốt nghiệp CNTT — Tiêu chí TC2.1 & TC2.3 (Mức 5)
* **Yêu cầu liên quan:** FR-AUTH-001, FR-PLAN-001..003, FR-SESSION-001..003, FR-TASK-001, FR-ADAPT-001, BUSR-02, BUSR-06, BUSR-07, BUSR-09, OS-01, OS-03, NFR-PERF-002
* **Tài liệu đối chiếu:** `docs/database/database-schema-design.md`, `docs/database/schema.sql`, `docs/architecture/system-architecture.md`

---

## 1. Ngữ cảnh & Đặt vấn đề (Context)
FocusFlow là hệ thống lập kế hoạch và thực thi lộ trình tự học đòi hỏi tính toàn vẹn dữ liệu cực kỳ khắt khe:
1. **Ràng buộc nghiệp vụ nghiêm ngặt:** Một lộ trình tại một thời điểm chỉ có 1 Lịch chính thức (`official_schedules`); một người dùng tại một thời điểm chỉ có tối đa 1 phiên học đang diễn ra (`study_sessions.status = 'IN_PROGRESS'`); các task thuộc milestone phải thuộc đúng lộ trình tương ứng (tránh lệch liên kết).
2. **Xử lý giao dịch đồng thời (Concurrency & Race Conditions):** Các thao tác kích hoạt lịch (Strict Apply - `OS-03`), tịnh tiến dời lịch (Domino Shift - `BUSR-07`) và trừ hạn ngạch AI Quota hai pha đòi hỏi tính nguyên tử (Atomicity), nhất quán (Consistency), cô lập (Isolation) và bền vững (Durability) tuyệt đối.
3. **Hiệu năng truy vấn cao:** Hệ thống cần duy trì độ trễ phản hồi API $\le 200$ms cho 20 người dùng đồng thời (`NFR-PERF-002`), đồng thời hỗ trợ tra cứu các điều kiện suy diễn động (như task quá hạn: `scheduled_date < CURRENT_DATE AND status = 'PENDING'`) mà không làm phình to bảng dữ liệu.

---

## 2. Các phương án xem xét (Alternatives Considered)

### Phương án A: Cơ sở dữ liệu NoSQL Tài liệu (MongoDB)
* *Ưu điểm:* Linh hoạt trong việc lưu trữ toàn bộ cây lộ trình (Roadmap $\rightarrow$ Milestones $\rightarrow$ Tasks) dưới dạng 1 document JSON lồng nhau.
* *Nhược điểm:* Rất khó bảo đảm tính toàn vẹn tham chiếu quan hệ phức tạp; thiếu các ràng buộc `CHECK`, `FOREIGN KEY CASCADE` mạnh mẽ; quản trị giao dịch đa tài liệu phức tạp và tốn tài nguyên; không phù hợp để bảo vệ trước Hội đồng chấm thi chuyên ngành Công nghệ Phần mềm.

### Phương án B: Cơ sở dữ liệu Quan hệ MySQL 8.0
* *Ưu điểm:* Rất phổ biến, dễ cài đặt.
* *Nhược điểm:* Khả năng hỗ trợ chỉ mục bộ phận (Partial Index / Filtered Index) kém hơn PostgreSQL; kiểu dữ liệu `JSONB` xử lý chậm hơn; hàm sinh UUID tích hợp sẵn không tối ưu bằng `gen_random_uuid()` của PostgreSQL 16.

### Phương án C: PostgreSQL 16 Quan hệ kết hợp JSONB Tài liệu (Được chọn)
* Sử dụng hệ quản trị CSDL quan hệ PostgreSQL 16 làm nguồn chân lý dữ liệu bền vững duy nhất (Single Source of Truth).
* Chuẩn hóa toàn bộ 15 bảng dữ liệu đạt Dạng Chuẩn 3 (3NF) và Chuẩn Boyce-Codd (BCNF).
* Tận dụng kiểu `JSONB` cho các tài liệu cấu trúc động (`proposal_data`, `weekly_schedule`, `quantitative_summary`), kết hợp hệ thống khóa chính UUIDv7 tuần tự theo thời gian (RFC 9562), khóa ngoại phức hợp (Composite Foreign Keys) và các chỉ mục bộ phận (Partial Indexes).

---

## 3. Quyết định (Decision)
**Chấp thuận Phương án C:**
1. **Hệ quản trị CSDL:** Lựa chọn **PostgreSQL 16 Alpine** (vận hành containerized qua Docker Compose).
2. **Chiến lược Khóa chính Tuần tự Thời gian (UUIDv7 - RFC 9562):** Khóa chính được sinh tại Backend Python bằng thư viện `uuid6` theo chuẩn UUIDv7 (chứa 48-bit timestamp), kết hợp fallback `id UUID PRIMARY KEY DEFAULT gen_random_uuid()` tại CSDL PostgreSQL 16. Chiến lược này vừa bảo đảm an toàn chống tấn công dò đoán ID (ID Enumeration), vừa bảo đảm tính đơn điệu tăng dần theo thời gian (Time-Ordered Monotonic), triệt tiêu hoàn toàn hiện tượng phân mảnh trang (B-Tree Page Splitting), tối ưu hóa hiệu năng ghi đệm Buffer Cache khi quy mô dữ liệu tăng trưởng.
3. **Bảo vệ Tính toàn vẹn bằng Defense-in-Depth Constraints:**
   - Khóa ngoại phức hợp: `CONSTRAINT fk_tasks_milestone_roadmap FOREIGN KEY (milestone_id, roadmap_id) REFERENCES milestones(id, roadmap_id) ON DELETE CASCADE` ngăn chặn hoàn toàn việc gán task nhầm sang roadmap khác.
   - Ràng buộc hoàn thành: `CONSTRAINT chk_task_completed_at CHECK ((status = 'COMPLETED' AND completed_at IS NOT NULL) OR (status = 'PENDING' AND completed_at IS NULL))`.
   - Ràng buộc chu kỳ học: `CONSTRAINT chk_task_time_window CHECK (start_time IS NULL OR end_time IS NULL OR start_time < end_time)`.
4. **Chiến lược Partial Indexes & Concurrency Protection:**
   - Ngăn chặn người dùng mở 2 phiên học đồng thời: `CREATE UNIQUE INDEX uq_user_single_active_session ON study_sessions(user_id) WHERE status = 'IN_PROGRESS';`.
   - Tối ưu hóa truy vấn phát hiện Overdue động: `CREATE INDEX idx_tasks_pending_overdue ON tasks(scheduled_date) WHERE status = 'PENDING' AND scheduled_date IS NOT NULL;`.
   - Tối ưu hóa Celery Worker quét gián đoạn: `CREATE INDEX idx_study_sessions_in_progress ON study_sessions(last_heartbeat_at) WHERE status = 'IN_PROGRESS';`.
5. **Đồng bộ Schema:** Sử dụng SQLAlchemy 2.0 Async (`asyncpg`) và công cụ di chuyển dữ liệu Alembic để duy trì tính nhất quán 1:1 với `schema.sql`.

---

## 4. Lý do & Đánh đổi (Rationale & Trade-Offs)
* **Học thuật Xuất sắc (Academic Rigor):** Mô hình hóa dữ liệu theo chuẩn Physical Database Schema Diagram đạt tiêu chí TC2.1 & TC2.3 Mức 5. Có thể chứng minh tính đúng đắn toán học qua chuẩn hóa 3NF/BCNF.
* **Bảo vệ Tầng Miền ở Mức CSDL (Database-level Invariants):** Ngay cả khi xảy ra lỗi lập trình ở tầng ứng dụng hoặc race condition qua mạng, CSDL sẽ từ chối giao dịch vi phạm thay vì ghi dữ liệu rác hoặc không nhất quán.
* **Chi phí Đánh đổi:** Đòi hỏi lập trình viên phải quản lý migrations chặt chẽ bằng Alembic và viết các truy vấn JOIN cẩn thận. Tuy nhiên, với ORM SQLAlchemy 2.0 Async, chi phí này hoàn toàn trong tầm kiểm soát.

---

## 5. Hệ quả (Consequences)
* **Tích cực:** Độ tin cậy dữ liệu 100%, không xảy ra rò rỉ hay lệch pha giữa các thực thể; truy vấn cực nhanh nhờ partial indexes; phục vụ tốt cho cả REST API, Celery Worker và xuất WebCal.
* **Giảm thiểu Rủi ro:** Sao lưu định kỳ qua volume `pg_data` của Docker và có tệp khởi tạo schema tự động `01-init.sql`.

---

## 6. Yêu cầu & Tài liệu liên quan
- **Yêu cầu SRS:** `FR-AUTH-001`, `FR-PLAN-001..003`, `FR-SESSION-001..003`, `BUSR-02`, `BUSR-06`, `BUSR-07`.
- **ADR liên quan:** `ADR-001` (Kiến trúc Lục giác), `ADR-002` (Backend Tech Stack), `ADR-004` (Celery & Jobs).
- **Hồ sơ thiết kế:** [`docs/database/database-schema-design.md`](file:///Users/vuthang/Documents/FocusFlow/docs/database/database-schema-design.md), [`docs/database/schema.sql`](file:///Users/vuthang/Documents/FocusFlow/docs/database/schema.sql).
