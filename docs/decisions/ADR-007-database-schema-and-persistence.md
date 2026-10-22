# ADR-007: Kiến trúc Cơ sở Dữ liệu Quan hệ, Chuẩn hóa 3NF/BCNF và Ràng buộc Toàn vẹn ACID (PostgreSQL 16)

* **Trạng thái:** Được chấp thuận (Approved)
* **Ngày quyết định:** 30/09/2026 (Cập nhật Kiến trúc & Hardening: 16/10/2026)
* **Người quyết định:** Vũ Toàn Thắng, Phan Đình Duẩn
* **Căn cứ đánh giá:** Khung Rubric Đồ án Tốt nghiệp CNTT — Tiêu chí TC2.1 & TC2.3 (Mức 5)
* **Yêu cầu liên quan:** FR-AUTH-001, FR-PLAN-001..003, FR-SESSION-001..003, FR-TASK-001, FR-ADAPT-001, FR-REPORT-001, BUSR-02, BUSR-06, BUSR-07, BUSR-09, OS-01, OS-03, NFR-PERF-002, NFR-SEC-001
* **Tài liệu đối chiếu:** [`docs/database/database-schema-design.md`](file:///Users/vuthang/Documents/FocusFlow/docs/database/database-schema-design.md), [`docs/database/data-dictionary.md`](file:///Users/vuthang/Documents/FocusFlow/docs/database/data-dictionary.md), [`docs/database/schema.sql`](file:///Users/vuthang/Documents/FocusFlow/docs/database/schema.sql), [`docs/architecture/system-architecture.md`](file:///Users/vuthang/Documents/FocusFlow/docs/architecture/system-architecture.md)

---

## 1. Ngữ cảnh & Đặt vấn đề (Context)
FocusFlow là hệ thống lập kế hoạch và thực thi lộ trình tự học thích ứng (Adaptive Learning Roadmap System), đòi hỏi tính toàn vẹn dữ liệu, kiểm toán và bảo mật đa người dùng (Multi-tenant) cực kỳ khắt khe:
1. **Ràng buộc nghiệp vụ nghiêm ngặt & Tính nhất quán phân cấp:** 
   - Một lộ trình tại một thời điểm chỉ có tối đa 1 Lịch chính thức đang hoạt động (`official_schedules`).
   - Một người dùng tại một thời điểm chỉ có tối đa 1 phiên học đang diễn ra (`study_sessions.status = 'IN_PROGRESS'`).
   - Các thực thể con (Milestones, Tasks, Sessions, Proposals, Reviews) phải trực thuộc chính xác Lộ trình và Mục tiêu của cùng một Người dùng, tuyệt đối không được xảy ra tình trạng rò rỉ dữ liệu chéo (Cross-tenant Data Leakage / IDOR) ở mức lưu trữ.
2. **Bảo tồn Dữ liệu Lịch sử Học tập (Audit Trail & Data Preservation):**
   - Trong quá trình thích ứng và điều chỉnh kế hoạch, người dùng có thể xóa hoặc hủy Task, nhưng dữ liệu lịch sử các phiên học (`study_sessions`, `session_tasks`) đã thực hiện trong quá khứ là tài sản dữ liệu quý giá của người học, không được phép bị xóa liên hoàn (`CASCADE`) mất dấu tích.
3. **Quản trị Giao dịch & Hạn ngạch AI (Concurrency & Quota Integrity):**
   - Các thao tác kích hoạt lịch (Strict Apply - `OS-03`), tịnh tiến dời lịch (Domino Shift - `BUSR-07`) và cơ chế trừ hạn ngạch AI Quota hai pha (Reserve / Commit / Release) đòi hỏi tính nguyên tử (Atomicity) và cô lập (Isolation). Nếu tiến trình xử lý nền (Celery Worker) hoặc luồng SSE bị gián đoạn/crash, hạn ngạch đã giữ chỗ (Reserved) phải có cơ chế hoàn trả (Release/Reclaim) tự động, không được thất thoát.
4. **Hiệu năng truy vấn & Tránh bẫy khóa CASCADE:**
   - Hệ thống cần duy trì độ trễ phản hồi API $\le 200$ms cho 20 người dùng đồng thời (`NFR-PERF-002`), đồng thời cơ chế khóa ngoại khi xóa tài khoản người dùng (`DELETE FROM users`) không được gây xung đột khóa tức thời (`RESTRICT` check) giữa các bảng phụ thuộc lẫn nhau.

---

## 2. Các phương án xem xét (Alternatives Considered)

### Phương án A: Cơ sở dữ liệu NoSQL Tài liệu (MongoDB)
* *Ưu điểm:* Linh hoạt trong việc lưu trữ toàn bộ cây lộ trình (Roadmap $\rightarrow$ Milestones $\rightarrow$ Tasks) dưới dạng 1 document JSON lồng nhau.
* *Nhược điểm:* Rất khó bảo đảm tính toàn vẹn tham chiếu quan hệ phức tạp; thiếu các ràng buộc `CHECK`, `FOREIGN KEY CASCADE` mạnh mẽ; quản trị giao dịch đa tài liệu phức tạp và tốn tài nguyên; không phù hợp để bảo vệ trước Hội đồng chấm thi chuyên ngành Công nghệ Phần mềm.

### Phương án B: Cơ sở dữ liệu Quan hệ MySQL 8.0
* *Ưu điểm:* Rất phổ biến, dễ cài đặt.
* *Nhược điểm:* Khả năng hỗ trợ chỉ mục bộ phận (Partial Index / Filtered Index) kém hơn PostgreSQL; kiểu dữ liệu `JSONB` xử lý chậm hơn; hàm sinh UUID tích hợp sẵn không tối ưu bằng `gen_random_uuid()` của PostgreSQL 16; thiếu hỗ trợ `DEFERRABLE INITIALLY DEFERRED` cho các ràng buộc duy nhất phức hợp.

### Phương án C: PostgreSQL 16 Quan hệ kết hợp JSONB Tài liệu & Defense-in-Depth Constraints (Được chọn)
* Sử dụng hệ quản trị CSDL quan hệ PostgreSQL 16 làm nguồn chân lý dữ liệu bền vững duy nhất (Single Source of Truth).
* Chuẩn hóa toàn bộ 16 bảng dữ liệu đạt Dạng Chuẩn 3 (3NF) và Chuẩn Boyce-Codd (BCNF).
* Tận dụng kiểu `JSONB` cho các tài liệu cấu trúc động (`proposal_data`, `weekly_schedule`, `quantitative_summary`), kết hợp hệ thống khóa chính UUIDv7 tuần tự theo thời gian (RFC 9562), khóa ngoại phức hợp cô lập Tenant, sổ cái giữ chỗ AI Quota 2 pha và các chỉ mục bộ phận (Partial Indexes).

---

## 3. Quyết định (Decision)
**Chấp thuận Phương án C với 8 trụ cột kỹ thuật chi tiết:**

1. **Hệ quản trị CSDL:** Lựa chọn **PostgreSQL 16 Alpine** (vận hành containerized qua Docker Compose).
2. **Chiến lược Khóa chính Tuần tự Thời gian (UUIDv7 - RFC 9562):** 
   - Khóa chính được sinh tại Backend Python bằng thư viện `uuid6` theo chuẩn UUIDv7 (chứa 48-bit timestamp), kết hợp fallback `id UUID PRIMARY KEY DEFAULT gen_random_uuid()` tại CSDL PostgreSQL 16.
   - Đảm bảo tính đơn điệu tăng dần (Time-Ordered Monotonic), triệt tiêu phân mảnh trang chỉ mục B-Tree (Page Splitting) và tối ưu hóa bộ đệm Buffer Cache.
3. **Kiến trúc Cô lập Dữ liệu Đa người dùng Đa tầng (Cross-Tenant Multi-Entity Isolation):**
   - Thiết lập các Siêu khóa Ứng viên (Candidate Superkeys):
     - `goals`: `CONSTRAINT uq_goals_id_user UNIQUE (id, user_id)`
     - `roadmaps`: `CONSTRAINT uq_roadmaps_id_user UNIQUE (id, user_id)`
   - Ràng buộc Khóa ngoại phức hợp kết nối User:
     - `roadmaps`: `FOREIGN KEY (goal_id, user_id) REFERENCES goals(id, user_id) ON DELETE NO ACTION`
     - `schedule_proposals`: `FOREIGN KEY (roadmap_id, user_id) REFERENCES roadmaps(id, user_id) ON DELETE CASCADE`
     - `study_sessions`: `FOREIGN KEY (roadmap_id, user_id) REFERENCES roadmaps(id, user_id) ON DELETE CASCADE`
     - `ai_reviews`: `FOREIGN KEY (roadmap_id, user_id) REFERENCES roadmaps(id, user_id) ON DELETE CASCADE`
   - *Hệ quả:* Ngăn chặn 100% rủi ro lỗ hổng IDOR ở mức CSDL, bảo đảm người dùng A không bao giờ có thể tạo lộ trình, phiên học hay bản đề xuất trỏ vào mục tiêu của người dùng B.
4. **Hiệu chỉnh Hành vi Xóa Tham chiếu (Referential Integrity Actions Tuning):**
   - **`roadmaps.goal_id` sử dụng `ON DELETE NO ACTION`:** Thay thế `ON DELETE RESTRICT` để tránh lỗi câu lệnh khi xóa Người dùng (`DELETE FROM users`). Khi cascade xóa `users`, cả `goals` và `roadmaps` đều nhận lệnh xóa; `NO ACTION` chỉ kiểm tra tính hợp lệ ở cuối câu lệnh (End-of-Statement), do đó không gây lỗi nếu `goals` bị xóa trước `roadmaps`, đồng thời vẫn chặn hoàn toàn hành vi người dùng cố tình xóa lẻ Goal khi Roadmap đang hoạt động.
   - **`session_tasks.task_id` sử dụng `ON DELETE RESTRICT`:** Ngăn chặn việc xóa cứng Task khi task đó đã từng được học trong một Phiên học (`study_sessions`). Để duy trì lịch sử học tập chuẩn xác, ứng dụng bắt buộc phải chuyển trạng thái task sang `CANCELLED` thay vì xóa vật lý.
5. **Cơ chế Hạn ngạch AI Hai Pha & Sổ cái Giữ chỗ (`ai_quota_reservations`):**
   - Bổ sung bảng thứ 16: `ai_quota_reservations` đóng vai trò Transaction Ledger cho việc trừ hạn ngạch AI:
     - Trạng thái: `RESERVED` $\rightarrow$ `COMMITTED` (khi AI gọi thành công) hoặc `RELEASED` / `EXPIRED` (khi thất bại/quá hạn).
     - Lưu trữ `expires_at` (thời hạn 5 phút) cho phép Celery Beat Sweeper Job tự động quét và hoàn trả số lượt `reserved_calls` bị treo khi worker crash hoặc client ngắt kết nối SSE.
   - Cột `ai_quotas.tokens_consumed` nâng cấp lên `BIGINT` để tránh tràn số nguyên 32-bit ($> 2.14$ tỷ tokens).
6. **Tự động hóa Đồng bộ Thời gian Kiểm toán (Automated Auditing via Triggers):**
   - Định nghĩa hàm trigger dùng chung: `set_updated_at()`.
   - Gắn 12 Triggers `BEFORE UPDATE` trên tất cả 12 bảng có cột `updated_at`, đảm bảo thời gian cập nhật luôn được ghi nhận chính xác ở cấp độ hệ quản trị CSDL ngay cả khi truy vấn qua Raw SQL.
7. **Toàn vẹn Nghiệp vụ & Ràng buộc Hoãn lại (Domain Invariants & Deferrable Constraints):**
   - Hoán đổi vị trí Milestones: `CONSTRAINT uq_milestone_roadmap_sequence UNIQUE (roadmap_id, sequence_order) DEFERRABLE INITIALLY DEFERRED` cho phép cập nhật thứ tự các chặng học trong cùng một giao dịch mà không bị xung đột khóa tạm thời.
   - Chuẩn hóa Email không phân biệt hoa thường: `CREATE UNIQUE INDEX uq_users_lower_email ON users (LOWER(email))`.
   - Kiểm định cấu trúc JSON: Ràng buộc `jsonb_typeof(...) = 'object'` trên `availabilities.weekly_schedule` (lưu trữ đồng thời cả Mode A preferences và Mode B cross-midnight offset slots theo D-05, D-10), `schedule_proposals.proposal_data`, và `ai_reviews.quantitative_summary`.
   - Phân tách cấu hình tích hợp lịch: Cột `availabilities.calendar_integration_mode` (`NONE`, `EXPORT_ICS`, `CONNECTED`) độc lập với `mode` (D-06).
   - Kiểm toán đồng thời Optimistic Locking: Tận dụng trigger `trg_availabilities_updated_at` để bảo vệ cổng kích hoạt lịch (Apply Gate), trả về HTTP 409 nếu phiên bản cấu hình rảnh bị thay đổi ở phiên khác (D-09).
   - Tính toán chính xác ngày lùi lịch: `CONSTRAINT chk_pause_duration CHECK (shifted_days = (pause_end_date - pause_start_date + 1))`.
   - Kiểm soát chu kỳ Đánh giá AI: `milestone_id` bắt buộc khi `review_cycle = 'MILESTONE'`, `(period_start, period_end)` bắt buộc khi `review_cycle = 'WEEKLY'`.
   - Ảnh chụp Kế hoạch cơ sở: Cột `official_schedules.total_planned_minutes INTEGER` đóng băng tổng thời gian dự kiến (Frozen Baseline) theo đơn vị phút thống nhất.
8. **Chiến lược 24 Chỉ mục Tối ưu Hóa Truy vấn (23 Optimized Indexes):**
   - Đảm bảo 100% cột Khóa ngoại đều có Index tương ứng để triệt tiêu Table Scan khi JOIN.
   - Chỉ mục bộ phận kiểm soát đơn phiên hoạt động: `uq_user_single_active_session` trên `study_sessions(user_id) WHERE status = 'IN_PROGRESS'`.
   - Chỉ mục bộ phận đơn bản nháp đề xuất: `uq_one_draft_per_roadmap` trên `schedule_proposals(roadmap_id) WHERE status = 'DRAFT'`.
   - Chỉ mục chống trùng lặp đánh giá AI: `uq_ai_reviews_weekly` và `uq_ai_reviews_milestone`.
   - Chỉ mục tối ưu truy vấn quét Task quá hạn và phục hồi phiên học gián đoạn của Celery Worker.

---

## 4. Lý do & Đánh đổi (Rationale & Trade-Offs)

| Tiêu chí | Quyết định Lựa chọn | Đánh đổi / Chi phí Chấp nhận |
| :--- | :--- | :--- |
| **Bảo vệ Tính toàn vẹn (Integrity)** | Cài đặt toàn bộ Invariants ở CSDL (`CHECK`, Composite FK, Triggers, Deferrable Unique). | CSDL có cấu trúc chặt chẽ, câu lệnh INSERT/UPDATE phải tuân thủ nghiêm ngặt schema. |
| **Bảo mật Multi-tenant** | Khóa ngoại phức hợp `(goal_id, user_id)` và `(roadmap_id, user_id)`. | Phải tạo thêm Unique index phức hợp trên bảng cha để làm mục tiêu tham chiếu (tốn thêm một phần nhỏ dung lượng index). |
| **Độ tin cậy Quota AI** | Bảng sổ cái `ai_quota_reservations` + Sweeper Job. | Tăng thêm 1 bảng và 1 thao tác ghi bản ghi reservation khi bắt đầu gọi LLM. Đổi lại: triệt tiêu 100% thất thoát hạn ngạch. |
| **Bảo tồn Lịch sử Học** | `ON DELETE RESTRICT` trên `session_tasks.task_id`. | Ứng dụng không thể gọi lệnh DELETE bừa bãi trên Task đã học mà phải Soft Delete / Đổi status `CANCELLED`. Đổi lại: Báo cáo học tập lịch sử không bao giờ bị mồ côi hoặc sai lệch. |

---

## 5. Hệ quả & Rủi ro (Consequences)

### Tích cực (Positive Consequences)
- **Đạt điểm tối đa đồ án tốt nghiệp (TC2.1 & TC2.3 Mức 5):** Thiết kế mô hình CSDL hoàn chỉnh, chuẩn hóa 3NF/BCNF, kiểm soát toàn diện ACID, bảo mật đa người dùng và kiểm toán tự động.
- **Triệt tiêu lỗi logic nghiệp vụ:** Không còn rủi ro người dùng mở nhiều phiên học cùng lúc, tạo nhiều bản nháp đè nhau, hoặc sinh trùng lặp báo cáo tuần khi Celery retry.
- **Hiệu năng cao & Khả năng mở rộng:** Nhờ UUIDv7 và 24 chỉ mục tối ưu được tối ưu có chủ đích, hệ thống sẵn sàng xử lý hàng triệu bản ghi mà không lo phân mảnh đĩa.

### Giảm thiểu Rủi ro (Risk Mitigation)
- **Đồng bộ Schema mã nguồn:** Sử dụng SQLAlchemy 2.0 Async (`asyncpg`) và Alembic để sinh và kiểm soát các tập lệnh Migration tương thích 100% với `schema.sql`.
- **Sao lưu & Phục hồi:** Sử dụng Docker Volume `pg_data` bền vững và tệp kiểm thử khởi tạo tự động `schema.sql` (gắn vào `/docker-entrypoint-initdb.d/01-init.sql`).

---

## 6. Yêu cầu & Tài liệu liên quan
- **Yêu cầu SRS:** `FR-AUTH-001`, `FR-PLAN-001..003`, `FR-SESSION-001..003`, `FR-TASK-001`, `FR-ADAPT-001`, `FR-REPORT-001`, `BUSR-02`, `BUSR-06`, `BUSR-07`, `OS-01`, `OS-03`.
- **ADR liên quan:** `ADR-001` (Kiến trúc Lục giác), `ADR-002` (Backend Tech Stack), `ADR-004` (Celery & Background Jobs).
- **Hồ sơ thiết kế chi tiết:**
  - [`docs/database/database-schema-design.md`](file:///Users/vuthang/Documents/FocusFlow/docs/database/database-schema-design.md) (Mô hình ERD, DBML, 16 Bảng, 24 Index)
  - [`docs/database/data-dictionary.md`](file:///Users/vuthang/Documents/FocusFlow/docs/database/data-dictionary.md) (Từ điển Dữ liệu, Constraint Matrix, Index Matrix)
  - [`docs/database/schema.sql`](file:///Users/vuthang/Documents/FocusFlow/docs/database/schema.sql) (Tập lệnh DDL thực thi PostgreSQL 16)
