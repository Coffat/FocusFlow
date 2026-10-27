# ADR-007: Kiến trúc Cơ sở Dữ liệu PostgreSQL 16 (24 Bảng 3NF/BCNF), Khóa Ngoại Đơn (Single Surrogate FK) & Cấm ORM JOIN Chéo Context

* **Trạng thái:** Được chấp thuận (Approved — Cập nhật & Đồng bộ Kiến trúc v2.0)
* **Ngày quyết định:** 30/09/2026 (Cập nhật v2.0: 25/10/2026)
* **Người quyết định:** Vũ Toàn Thắng, Phan Đình Duẩn
* **Căn cứ đánh giá:** Khung Rubric Đồ án Tốt nghiệp CNTT — Tiêu chí TC2.1 & TC2.3 (Mức 5)
* **Yêu cầu liên quan:** `ASR-01`, `ASR-02`, `FR-AUTH-001`, `FR-PLAN-001..005`, `FR-SESSION-001..003`, `FR-TASK-001`, `FR-ADAPT-001..003`, `FR-REPORT-001`, `UC-01` đến `UC-19`, `BUSR-02`, `BUSR-06`, `BUSR-07`, `OS-01`, `OS-03`
* **Tài liệu đối chiếu:** [`docs/database/database-schema-design.md`](file:///Users/vuthang/Documents/FocusFlow/docs/database/database-schema-design.md), [`docs/database/data-dictionary.md`](file:///Users/vuthang/Documents/FocusFlow/docs/database/data-dictionary.md), [`docs/database/schema.sql`](file:///Users/vuthang/Documents/FocusFlow/docs/database/schema.sql)

---

## 1. Ngữ cảnh & Đặt vấn đề (Context)
Trong quá trình đối chiếu chéo toàn diện giữa tài liệu Nghiệp vụ (`SRS v1.2`, `19 Use Cases`, `Class Diagram v5.0`) và tài liệu Thiết kế Cơ sở Dữ liệu (`schema.sql` v3.0), nhóm phát triển đã phát hiện và cần giải quyết dứt điểm **3 vấn đề thiết kế trọng tâm** từ phiên bản v1.0:
1. **Lệch số lượng bảng giữa các tài liệu (15 vs 16 vs 19 vs 24 bảng):** Các bản ghi ADR cũ chỉ nhắc tới 15 hoặc 16 bảng, thiếu các bảng quan trọng phục vụ thanh toán (`payment_transactions`), kiểm toán dời lịch (`schedule_change_logs`), nhật ký tiêu thụ AI (`ai_usage_logs`), và đặc biệt là cặp bảng đảm bảo tính nhất quán sự kiện liên module (`outbox_events`, `processed_events`).
2. **Chiến lược Khóa ngoại Đơn (Single Surrogate FK) kết hợp Định danh Tương quan Đa người thuê Liên Context (Cross-Context Tenant Correlation IDs — `user_id`, `roadmap_id`):** Trong kiến trúc **Context-First Modular Monolith** cấm tuyệt đối ORM JOIN chéo Bounded Context (`ADR-001`), nếu các bảng ở các Context hạ nguồn (`schedule_proposals`, `study_sessions`, `ai_reviews`, `tasks`) hoàn toàn không lưu định danh tương quan (`user_id` hoặc `roadmap_id` trên `tasks`), mọi thao tác kiểm tra quyền sở hữu chống tấn công IDOR (`NFR-SEC-004`) sẽ buộc phải thực hiện nhiều cuộc gọi RPC nội bộ qua `public_api.py` gây suy giảm hiệu năng. Ngược lại, nếu dùng Khóa ngoại Phức hợp (Composite FK `(roadmap_id, user_id)`) cứng nhắc ở mọi cấp, lược đồ sẽ trở nên cồng kềnh. Do đó, cần làm rõ cơ chế giữ Single Surrogate Primary/Foreign Key chuẩn 3NF/BCNF kết hợp với **Cross-Context Tenant Correlation IDs** được bảo vệ bởi bất biến tầng ứng dụng.
3. **Mâu thuẫn biểu diễn Lịch rảnh (`availability_slots` vs cột `JSONB weekly_schedule`):** Tài liệu CSDL thiết kế bảng con chuẩn hóa `availability_slots` đạt chuẩn 3NF, trong khi một số tài liệu kiến trúc cũ lại mô tả lưu mảng JSONB `weekly_schedule` trong bảng `availabilities` còn Class Diagram mô tả các Value Objects `WeeklySchedule` và `TimeSlot`.

---

## 2. Các phương án xem xét (Alternatives Considered)

### Phương án A: Tách 4 Cơ sở dữ liệu / 4 Schema Vật lý riêng biệt và Bỏ toàn bộ Foreign Keys liên Context
* *Ưu điểm:* Cô lập vật lý giống Microservices.
* *Nhược điểm:* Mất khả năng bảo vệ toàn vẹn tham chiếu (Referential Integrity) ở cấp hệ quản trị CSDL; khó chứng minh thiết kế lược đồ quan hệ chuẩn 3NF/BCNF hoàn chỉnh trước Hội đồng bảo vệ đồ án.

### Phương án B: Dùng Khóa ngoại Phức hợp (Composite FK) Cồng kềnh và Lưu toàn bộ Khung giờ Lịch rảnh bằng mảng JSONB (Bản nháp cũ)
* *Ưu điểm:* Gom toàn bộ cấu trúc tuần vào một cột JSONB.
* *Nhược điểm:* Lưu mảng lặp các khung giờ rảnh trong JSONB khiến CSDL không thể kiểm tra ràng buộc `start_time < end_time` hay `day_of_week` bằng các `CHECK` constraints quan hệ chuẩn 3NF.

### Phương án C: Đồng bộ Tuyệt đối 24 Bảng Chuẩn 3NF/BCNF trên PostgreSQL 16 (`public` schema), Single Surrogate FK + Cross-Context Tenant Correlation IDs (`user_id`, `roadmap_id`), Bảng con `availability_slots` & Cấm ORM JOIN Chéo Context (Được chọn)
* Chuẩn hóa chính thức **24 bảng trong schema `public` của PostgreSQL 16** đạt chuẩn **3NF/BCNF** nghiêm ngặt.
* Sử dụng **Khóa ngoại Đơn thay thế (Single Surrogate Foreign Keys - `UUIDv7`)** kết hợp giữ lại có chủ đích các cột **Cross-Context Tenant Correlation IDs** (`user_id` trên `schedule_proposals`, `study_sessions`, `ai_reviews`, `pause_records`... và `roadmap_id` trên `tasks`) để kiểm tra quyền sở hữu chống IDOR trong thời gian $O(1)$ không cần JOIN chéo Context (`NFR-SEC-004`).
* Giữ nguyên bảng con chuẩn hóa **`availability_slots`** trong PostgreSQL 16 và thực hiện ánh xạ (mapping) bên trong `SqlAlchemyAvailabilityRepository` sang các Domain Value Objects `WeeklySchedule` và `TimeSlot`.

---

## 3. Quyết định (Decision)
**Chấp thuận Phương án C với 5 trụ cột thiết kế CSDL v2.0:**

### 3.1. Phân bổ Chính thức 24 Bảng Chuẩn 3NF/BCNF theo 4 Bounded Contexts + `shared_kernel`
Toàn bộ 24 bảng nằm trong schema `public` của PostgreSQL 16, trong đó mỗi bảng thuộc quyền **sở hữu ghi độc quyền (Exclusive Write Ownership)** của đúng một Bounded Context (đồng bộ 100% với `Class Diagram v5.0` và `schema.sql` v3.0):

| Phân vùng (Bounded Context) | Số lượng | Danh sách các Bảng PostgreSQL 16 Sở hữu |
| :--- | :---: | :--- |
| **1. `account`** | **9 bảng** | `users`, `learner_profiles`, `webcal_tokens`, `availabilities`, `availability_slots`, `ai_quotas`, `ai_quota_reservations`, `ai_usage_logs`, `payment_transactions` |
| **2. `planning`** | **5 bảng** | `goals`, `roadmaps`, `milestones`, `official_schedules`, `schedule_proposals` |
| **3. `execution`** | **5 bảng** | `tasks`, `task_dependencies`, `study_sessions`, `session_tasks`, `study_notes` |
| **4. `evaluation`** | **3 bảng** | `pause_records`, `ai_reviews`, `schedule_change_logs` |
| **5. `shared_kernel`** | **2 bảng** | `outbox_events`, `processed_events` |
| **Tổng cộng toàn hệ thống** | **24 bảng** | **Đạt chuẩn 3NF / BCNF 100% với Khóa chính `UUIDv7` tuần tự thời gian** |

### 3.2. Khóa Ngoại Đơn (Single Surrogate FK), Định danh Tương quan Liên Context (`user_id`, `roadmap_id`) & Cấm ORM JOIN Chéo Context
1. **Ở cấp độ CSDL Vật lý (`PostgreSQL 16` — `schema.sql` v3.0):**
   * Mọi liên kết quan hệ đều sử dụng **Single Surrogate Foreign Key (`UUIDv7`)** chuẩn mực.
   * **Lý giải Kiến trúc về Cross-Context Tenant Correlation IDs (`user_id` và `roadmap_id`):** Trong kiến trúc **Context-First Modular Monolith** nơi việc thực hiện câu lệnh `JOIN` ORM chéo Bounded Context bị cấm tuyệt đối (`ADR-001`), cột `user_id` (trên `schedule_proposals`, `study_sessions`, `study_notes`, `pause_records`, `ai_reviews`, `schedule_change_logs`) và cột `roadmap_id` (trên `tasks` thuộc `execution`, trong khi `milestones`/`roadmaps` thuộc `planning`) được giữ lại có chủ đích với vai trò là **Định danh Tương quan Người thuê Liên Context (Cross-Context Tenant Correlation IDs)**. Thiết kế này cho phép từng Bounded Context thực thi kiểm tra quyền sở hữu chống tấn công **IDOR (`NFR-SEC-004`) với độ phức tạp $O(1)$ không cần JOIN (Zero-Join Ownership Check)** ngay trên bảng cục bộ của mình, đồng thời vẫn duy trì tính toàn vẹn chuẩn 3NF/BCNF thông qua các khóa ngoại đơn và bất biến ở tầng Application/Use Case khi khởi tạo thực thể.
2. **Ở cấp độ Mã nguồn Ứng dụng (`SQLAlchemy 2.0 ORM`):**
   * Giữ các ràng buộc `FOREIGN KEY` vật lý ở DDL SQL để đảm bảo tính toàn vẹn dữ liệu cấp cuối (Defense-in-Depth), nhưng **cấm tuyệt đối việc khai báo `relationship()` hoặc viết câu lệnh SQLAlchemy `JOIN` trực tiếp giữa các bảng thuộc hai Bounded Context khác nhau**.
   * Mọi nhu cầu tra cứu dữ liệu liên Context bắt buộc đi qua `public_api.py` (Read-Only Query Port) của Context sở hữu bảng đó (`ADR-001`).

### 3.3. Giải quyết Triệt để Bài toán Lịch Rảnh: Bảng `availability_slots` $\leftrightarrow$ Value Objects `WeeklySchedule` & `TimeSlot`
* **Tại tầng CSDL (`PostgreSQL 16`):** Lưu trữ các khung giờ rảnh trong bảng con chuẩn hóa **`availability_slots`** (`id`, `availability_id`, `day_of_week`, `start_time`, `end_time`, `end_day_offset`, `slot_type`, `is_active`, ...) có khóa ngoại trỏ về `availabilities(id) ON DELETE CASCADE`. Điều này cho phép kiểm tra ràng buộc toàn vẹn từng khung giờ bằng SQL `CHECK` constraints và đạt chuẩn 3NF tuyệt đối (không lưu mảng lặp các khung giờ trong cột JSONB).
* **Tại tầng Domain (`account.domain`):** Aggregate Root `AvailabilityProfile` giữ đối tượng giá trị bất biến **`WeeklySchedule`** chứa tập hợp các **`TimeSlot`** (đồng bộ 100% với `Class Diagram v5.0`) để phục vụ tính toán trong `HybridAvailabilityRuleEngine`.
* **Tại tầng Infrastructure (`SqlAlchemyAvailabilityRepository`):** Repository đảm nhận vai trò **Data Mapper** nạp bảng `availabilities` cùng danh sách `availability_slots` (qua `selectinload`) và tái cấu trúc thành `WeeklySchedule` / `TimeSlot` khi đọc lên Domain, cũng như đồng bộ ngược lại các dòng `availability_slots` khi lưu Aggregate Root.

### 3.4. Chuẩn hóa 5 Bảng Nghiệp vụ & Hạ tầng Bổ sung cùng `ai_usage_logs`
Bản thiết kế v2.0 chính thức chuẩn hóa đầy đủ các bảng phục vụ giao dịch tài chính, hạn ngạch AI, kiểm toán lịch và kiến trúc hướng sự kiện:
1. **`payment_transactions` (`account`):** Lưu trữ lịch sử giao dịch nâng cấp gói (`UC-05`), mã tham chiếu duy nhất `transaction_ref` (`UNIQUE` chống replay webhook), số tiền, cổng thanh toán (`PAYOS`/`VNPAY`/`LOCAL_MOCK`) và trạng thái (`PENDING`, `PAID`, `FAILED`, `CANCELLED`).
2. **`ai_quota_reservations` (`account`):** Sổ cái giữ chỗ hạn ngạch AI 2 pha (`RESERVED`, `COMMITTED`, `RELEASED`, `EXPIRED`) kèm cột `expires_at` phục vụ `QuotaSweeperTask` (`ADR-005`).
3. **`ai_usage_logs` (`account`):** Bảng telemetry ghi nhận từng lệnh gọi LLM (mô hình, số prompt/completion tokens, thời gian phản hồi `latency_ms`, trạng thái thành công/lỗi) phục vụ giám sát hệ thống của Admin (`UC-19`).
4. **`schedule_change_logs` (`evaluation`):** Bảng kiểm toán bất biến ghi lại mọi biến động lịch trình (do `DominoShiftEngine` khi Pause/Resume lộ trình hoặc do xử lý quá hạn `UC-16`, `UC-17`), lưu trữ trạng thái trước/sau và lý do dịch chuyển.
5. **`outbox_events` & `processed_events` (`shared_kernel`):** Cặp bảng hạ tầng đảm bảo mẫu **Transactional Outbox** và **Idempotent Consumer** giữa 4 Bounded Contexts (`ADR-001`, `ADR-004`).

### 3.5. Ràng buộc Toàn vẹn Cốt lõi, Deferrable Constraints & Partial Indexes
* **Khóa chính UUIDv7 (RFC 9562):** Sinh tại tầng Domain Python (`uuid6.uuid7()`), đảm bảo thứ tự tăng dần theo thời gian, chống phân mảnh B-Tree Index.
* **Bảo tồn lịch sử học tập:** `session_tasks.task_id` sử dụng `ON DELETE RESTRICT` để ngăn xóa cứng các Task đã từng có lịch sử phiên học; ứng dụng chuyển trạng thái Task sang `CANCELLED`.
* **Ràng buộc hoãn lại (Deferrable Unique):** `uq_milestone_roadmap_sequence UNIQUE (roadmap_id, sequence_order) DEFERRABLE INITIALLY DEFERRED` hỗ trợ hoán đổi thứ tự Milestones mượt mà trong một giao dịch.
* **Partial Unique Indexes:** Đảm bảo mỗi người học chỉ có tối đa 1 phiên `IN_PROGRESS` (`uq_user_single_active_session`) và mỗi lộ trình chỉ có tối đa 1 bản nháp đề xuất `DRAFT` (`uq_one_draft_per_roadmap`).

---

## 4. Lý do & Đánh đổi (Rationale & Trade-Offs)

| Tiêu chí | Quyết định Lựa chọn v2.0 | Lý do & Giá trị Đạt được |
| :--- | :--- | :--- |
| **Chuẩn hóa 3NF/BCNF & Chống IDOR $O(1)$** | Khóa ngoại đơn (Single Surrogate FK) + Cross-Context Tenant Correlation IDs (`user_id`, `roadmap_id`) + Bảng con `availability_slots`. | Đảm bảo kiểm tra quyền sở hữu chống IDOR (`NFR-SEC-004`) trong $O(1)$ mà không cần ORM JOIN chéo Context, đồng thời giữ cấu trúc bảng con `availability_slots` chuẩn 3NF/BCNF. |
| **Cô lập Bounded Context** | Giữ FK vật lý ở PostgreSQL nhưng cấm ORM JOIN chéo Context. | Vừa có lưới an toàn Referential Integrity ở cấp DB, vừa giữ mã nguồn các Bounded Context độc lập hoàn toàn (`ASR-01`). |
| **Đồng bộ Tài liệu 100%** | Thống nhất con số **24 bảng** trên mọi tài liệu (`ERD`, `DDL`, `Class Diagram`, `ADRs`). | Xóa bỏ hoàn toàn mâu thuẫn giữa các phiên bản tài liệu cũ. |

---

## 5. Nguồn Chân Lý của Schema & Chiến Lược Migration (Schema Source of Truth & Migration Strategy)

* **Alembic là Nguồn Chân lý khi chạy (Runtime Source of Truth):**
  - Mọi thay đổi cấu trúc CSDL vật lý đều được hiện thực hóa thông qua các phiên bản di chuyển dữ liệu (migrations) được quản lý chặt chẽ bởi **Alembic Async** (`alembic/versions/`).
  - Khi triển khai môi trường Docker Compose hoặc Cloud Production, tiến trình khởi động của dịch vụ `backend` sẽ tự động thực thi lệnh `alembic upgrade head` trước khi khởi chạy máy chủ ASGI `uvicorn`. CSDL vật lý không còn phụ thuộc vào việc gắn tệp SQL tĩnh qua thư mục `/docker-entrypoint-initdb.d/`.
* **Vai trò của `docs/database/schema.sql`:**
  - `schema.sql` (v3.0 — 24 bảng 3NF/BCNF) đóng vai trò là **tài liệu thiết kế kiến trúc chuẩn mực (Design Specification Target)** và là bản DDL phục vụ cho Hội đồng chấm đồ án tốt nghiệp.
  - Trong quá trình phát triển, tệp `schema.sql` được đồng bộ ngược (regenerate) từ CSDL thực thi đã áp dụng đủ các migration mới nhất thông qua kịch bản `backend/scripts/dump_schema.sh` (`pg_dump --schema-only --no-owner --no-privileges`).
  - Kiểm thử CI (CI Pipeline) sẽ tự động kiểm tra tính tương đồng (diff check) giữa kết quả xuất từ `alembic upgrade head` trên CSDL mới với tệp `docs/database/schema.sql` để đảm bảo không xảy ra hiện tượng trôi dạt lược đồ (schema drift).

---

## 6. Hệ quả & Kiểm chứng (Consequences & Verification)
* **Tích cực:** Lược đồ CSDL 24 bảng đạt độ chuẩn xác học thuật và kỹ thuật cao nhất (Rubric TC2.1 & TC2.3 Mức 5). Quy trình migration tự động triệt tiêu hoàn toàn rủi ro mất dữ liệu khi nâng cấp hệ thống.
* **Kiểm chứng Tự động:** Tập lệnh migration của Alembic và `schema.sql` khởi tạo thành công 24 bảng, đầy đủ Foreign Keys, Check Constraints, Triggers `set_updated_at()` và Partial Indexes trên PostgreSQL 16 mà không có bất kỳ cảnh báo nào.
