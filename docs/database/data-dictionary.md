# FocusFlow — Từ điển Dữ liệu, Ma trận Ràng buộc & Ma trận Chỉ mục (Database Schema Governance)

## Thông tin Hồ sơ Kỹ thuật
* **Dự án:** FocusFlow — Hệ thống hỗ trợ lập kế hoạch và thực thi lộ trình tự học thích ứng tích hợp AI (FocusFlow Learning Intelligence Harness)
* **Phiên bản:** v3.2 — Chuẩn Quản trị Lược đồ Cơ sở Dữ liệu Đầy đủ 35 Bảng 3NF/BCNF kết hợp Controlled JSONB Value Objects + `pgvector` (35 Physical Tables Schema Governance Baseline — 4 Bounded Contexts + Shared Kernel: 12 / 10 / 5 / 4 / 4)
* **Hệ quản trị CSDL:** PostgreSQL 16+ (`pgvector` extension enabled)
* **Tiêu chuẩn kỹ thuật:** ISO/IEC 9075:2023 (SQL Standard), ISO/IEC/IEEE 29148:2018 (Requirements Engineering)
* **Căn cứ đánh giá học thuật:** Khung Rubric Đồ án Tốt nghiệp CNTT — Tiêu chí TC2.1 & TC2.3 (Mức 5)
* **Tài liệu nguồn chân lý liên kết:**
  * Tập lệnh DDL: [`docs/database/schema.sql`](schema.sql)
  * Thiết kế CSDL Chi tiết: [`docs/database/database-schema-design.md`](database-schema-design.md)
  * Quyết định Kiến trúc CSDL: [`docs/decisions/ADR-007-database-schema-and-persistence.md`](../decisions/ADR-007-database-schema-and-persistence.md)
  * Đặc tả Yêu cầu SRS v1.3: [`docs/srs/srs-v1.3.md`](../srs/srs-v1.3.md)
  * Báo cáo Căn chỉnh Mentor: [`docs/mentor-alignment-and-gap-report.md`](../mentor-alignment-and-gap-report.md)
  * Sơ đồ Lớp UML: [`docs/uml/class-diagrams/class-diagram.puml`](../uml/class-diagrams/class-diagram.puml) \| [`docs/uml/class-diagrams.md`](../uml/class-diagrams.md)
  * Sơ đồ CSDL DBML: [`docs/database/schema.dbml`](schema.dbml)

---

## 1. Nguyên tắc Cốt lõi & Quy ước Định danh Toàn hệ thống

> [!IMPORTANT]
> **20 Quyết định Kiến trúc & Quy chuẩn Cơ sở Dữ liệu FocusFlow v3.2 (35 Bảng 3NF/BCNF + `pgvector`):**
> 1. **Hệ quản trị CSDL & Extension `pgvector`:** PostgreSQL 16 vận hành tối ưu hóa trên container Docker Compose, kết nối qua `SQLAlchemy 2.0 Async + asyncpg`, kích hoạt `CREATE EXTENSION IF NOT EXISTS vector;` phục vụ Hybrid RAG (`tsvector` GIN + `vector(768)` HNSW) ngay trong cùng cụm CSDL quan hệ mà không cần thêm container Vector DB riêng.
> 2. **Chiến lược Khóa chính:** UUIDv7 (RFC 9562, 128-bit Time-Ordered Monotonic) sinh tại tầng Backend FastAPI (`uuid_utils`/`uuid6`), Fallback tại CSDL `DEFAULT gen_random_uuid()` loại bỏ phân mảnh B-Tree và chống tấn công đoán ID (riêng `processed_events` dùng khóa chính kép `(event_id, handler_name)`, `learning_concepts` dùng `concept_id VARCHAR(120)` và `concept_prerequisites` dùng `(source_concept_id, prerequisite_concept_id)`).
> 3. **Phân rã theo 4 Bounded Contexts + Shared Kernel (`12 / 10 / 5 / 4 / 4` = 35 Bảng):**
>    - **`account` (12 bảng):** `users`, `learner_profiles`, `webcal_tokens`, `calendar_connections`, `availabilities`, `availability_slots`, `ai_quotas`, `ai_quota_reservations`, `ai_usage_logs`, `payment_transactions`, `learner_memory_items` *(Mới v3.2)*, `learner_concept_masteries` *(Mới v3.2)*.
>    - **`planning` (10 bảng):** `goals`, `roadmaps`, `milestones`, `official_schedules`, `schedule_proposals`, `learning_concepts`, `concept_prerequisites`, `knowledge_sources` *(Mới v3.2)*, `knowledge_chunks` *(Mới v3.2)*, `schedule_blocks` *(Mới v3.2)*.
>    - **`execution` (5 bảng):** `tasks`, `task_dependencies`, `study_sessions`, `session_tasks`, `study_notes`.
>    - **`evaluation` (4 bảng):** `pause_records`, `ai_reviews`, `schedule_change_logs`, `milestone_proofs`.
>    - **`shared_kernel` (4 bảng):** `outbox_events`, `processed_events`, `workflow_runs` *(Mới v3.2)*, `workflow_step_executions` *(Mới v3.2)*.
> 4. **Quy tắc Modular Monolith & Controlled JSONB Value Objects:** Giữ nguyên Foreign Key vật lý ở tầng PostgreSQL 16 để đảm bảo toàn vẹn dữ liệu 3NF/BCNF kết hợp Controlled JSONB Value Objects có ràng buộc `CHECK` kiểm định miền giá trị (`daily_quotas`, `learning_resources_json`, `mistake_taxonomy_json`), nhưng cấm ORM JOIN chéo Bounded Context trong mã nguồn (chỉ giao tiếp qua `public_api.py` và `outbox_events`).
> 5. **Cô lập Đa người dùng (Multi-tenant):** Sử dụng Single Surrogate FK chuẩn, `user_id` hiện diện tại các bảng gốc, kiểm soát ủy quyền sở hữu tại Application Service Layer.
> 6. **Quản trị AI Quota 2 Pha ACID & Mặc định `gemini-2.5-flash`:** Tách biệt `ai_quotas` (hạn ngạch hiện tại kèm `reserved_calls`), `ai_quota_reservations` (sổ cái giữ chỗ 2 pha `RESERVED -> COMMITTED/RELEASED/EXPIRED` với TTL **5 phút (300 giây)**), và `ai_usage_logs` (nhật ký kiểm toán chi tiết với `model_name` mặc định `'gemini-2.5-flash'`, hỗ trợ 11 hành động bao gồm `'KNOWLEDGE_INGESTION'` và `'WHAT_IF_SIMULATION'`).
> 7. **Trí nhớ Người học Cấu trúc hóa (Structured Learner Memory 4×3) & Skill Mastery:** Bảng `learner_memory_items` chuẩn hóa 4 danh mục (`PROFILE`, `BEHAVIORAL`, `KNOWLEDGE`, `INTERACTION`) × 3 mức nhận thức (`EXPLICIT`, `OBSERVED`, `INFERRED`) kèm điểm tin cậy và xác nhận của người học; bảng `learner_concept_masteries` theo dõi điểm thành thạo (`0..100`) và lịch ôn tập thông minh (`next_review_at`).
> 8. **Knowledge Engine & Hybrid RAG:** Bảng `knowledge_sources` quản lý tài liệu (`PDF`, `DOCX`, `TXT`, `URL`) với kiểm duyệt SSRF và `content_hash` SHA-256; bảng `knowledge_chunks` lưu từng phân đoạn kèm `search_vector TSVECTOR` (GIN) và `embedding vector(768)` (HNSW).
> 9. **Tách biệt Nỗ lực Ước tính (`tasks.estimated_minutes`) và Khối Lịch Học Thực thi (`schedule_blocks`):** Cột `tasks.estimated_minutes` đại diện cho nỗ lực ước tính bởi AI (`estimated_effort`), trong khi `schedule_blocks.scheduled_duration_minutes` đại diện cho thời lượng phân bổ của từng buổi học (`STUDY`, `BUFFER`, `REVISION`, `RECOVERY`) và ánh xạ `external_calendar_event_id` với Google/Outlook Calendar.
> 10. **Chính sách Lịch Học Chống Đứt Gãy (Resilience Policy) & Mô phỏng What-If:** Bảng `official_schedules` bổ sung `buffer_minutes_per_week`, `recovery_window_days`, `daily_workload_cap_minutes`, `stability_weight`; bảng `schedule_proposals` hỗ trợ `'WHAT_IF_SIMULATION'` và `'SCHEDULE_ONLY_REOPTIMIZE'`.
> 11. **Phiên học Pomodoro, MVS, Heartbeat 60s & Daily Learning Check-in:** Bảng `study_sessions` bổ sung 3 cột khảo sát nhanh cuối phiên (`checkin_time_sufficiency`, `checkin_perceived_difficulty`, `checkin_focus_level`).
> 12. **Phản tư Tuần (Weekly Reflection) & Mistake Intelligence:** Bảng `ai_reviews` bổ sung `user_reflection_payload JSONB`; bảng `milestone_proofs` bổ sung `mistake_taxonomy_json JSONB` phân loại lỗi sai vào 4 nhóm (`MISSING_FOUNDATION`, `CONCEPT_MISCONCEPTION`, `PROCESS_ERROR`, `LACK_OF_PRACTICE`).
> 13. **Điều phối Workflow Bền vững (Durable Workflow Orchestration):** Hai bảng `workflow_runs` và `workflow_step_executions` trong `shared_kernel` lưu vết trạng thái thực thi và điểm dừng Human-in-the-Loop cho 5 Workflow cốt lõi.
> 14. **Tách biệt Nghiêm ngặt `AI Execution Run` và `Learning Event`:** Nhật ký vận hành AI (`workflow_runs`, `workflow_step_executions`, `ai_usage_logs`) tách biệt hoàn toàn khỏi sự kiện học tập của người học (`study_sessions`, `study_notes`, `milestone_proofs`, `schedule_change_logs`).
> 15. **Transactional Outbox & Idempotent Consumer:** Bảng `outbox_events` và `processed_events` đảm bảo 0% mất sự kiện và 0% xử lý trùng lặp trên **Taskiq Worker (Redis Streams)**.
> 16. **Quản lý Thời gian, Trigger & Chỉ mục:** `TIMESTAMPTZ` (UTC) cho mọi mốc thời gian; hàm trigger `fn_set_updated_at()` tự động cập nhật `updated_at` trên tất cả **26 bảng** có cột `updated_at`; **74 chỉ mục chuyên biệt** (B-Tree, Partial Unique, GIN, HNSW).

### 1.1. Bảng Ánh xạ 11 Khái niệm Logic của FocusFlow Learning Intelligence Harness sang 35 Bảng Vật lý

| STT | Khái niệm Logic (Learning Intelligence Harness) | Bảng Vật lý Ánh xạ (`schema.sql` v3.2) | Bounded Context | Lý giải Chuẩn hóa 3NF/BCNF & Tách biệt Ngữ nghĩa |
| :---: | :--- | :--- | :---: | :--- |
| **1** | **AI Execution Run** | `workflow_runs`, `ai_usage_logs`, `ai_quota_reservations` | `shared_kernel`, `account` | Lưu vết phiên chạy điều phối AI, giữ chỗ hạn ngạch 2 pha và chi phí token/độ trễ của LLM (`gemini-2.5-flash`). **Tách biệt 100% khỏi `Learning Event`** để dữ liệu vận hành AI không làm nhiễu phân tích hành vi học tập. |
| **2** | **Workflow Step Execution** | `workflow_step_executions` | `shared_kernel` | Quan hệ 1:N chuẩn 3NF với `workflow_runs`, lưu checkpoint đầu vào/đầu ra và liên kết `ai_usage_log_id` của từng bước trong Workflow. |
| **3** | **Knowledge Source** | `knowledge_sources`, `learning_concepts`, `concept_prerequisites` | `planning` | Quản lý tài liệu đầu vào (`PDF`, `DOCX`, `TXT`, `URL` kèm `content_hash` SHA-256) và đồ thị khái niệm học thuật chuẩn hóa. |
| **4** | **Knowledge Chunk** | `knowledge_chunks` | `planning` | Quan hệ 1:N chuẩn 3NF với `knowledge_sources` (`UNIQUE (source_id, chunk_index)`), tích hợp `search_vector TSVECTOR` (GIN) và `embedding vector(768)` (HNSW). |
| **5** | **Learning Event** | `study_sessions`, `session_tasks`, `study_notes`, `milestone_proofs`, `schedule_change_logs` | `execution`, `evaluation` | Ghi nhận bằng chứng học tập thực tế của người học: phiên Pomodoro + Daily Check-in, ghi chép Takeaway, bài kiểm chứng năng lực + `mistake_taxonomy_json`, và biến động lịch. **Tuyệt đối không trộn với `AI Execution Run`.** |
| **6** | **Learner Profile** | `users`, `learner_profiles`, `learner_concept_masteries` | `account` | Quản lý định danh, các chỉ số SRL tổng hợp 1:1 (`learner_profiles`), và mức độ thành thạo từng khái niệm 1:N (`learner_concept_masteries`). |
| **7** | **Learner Feature Snapshot** | `learner_memory_items` | `account` | Chuẩn hóa 3NF/BCNF cho các nhận định trí nhớ người học theo **4 Categories × 3 Epistemic Levels** (`UNIQUE (user_id, memory_category, memory_key)`). |
| **8** | **Availability Snapshot** | `availabilities`, `availability_slots` | `account` | Cấu hình quỹ thời gian rảnh Mode A (`availabilities.daily_quotas`) và các khung giờ rảnh kèm mức năng lượng Mode B chuẩn 3NF (`availability_slots`). |
| **9** | **Schedule Revision** | `official_schedules`, `schedule_proposals`, `pause_records` | `planning`, `evaluation` | Quản lý lịch chính thức đóng băng kèm chính sách chống đứt gãy (`official_schedules`), bản nháp What-If (`schedule_proposals`) và lịch sử tạm dừng (`pause_records`). |
| **10** | **Calendar Event Mapping** | `schedule_blocks`, `calendar_connections`, `webcal_tokens` | `planning`, `account` | Bảng `schedule_blocks` phân bổ các khối lịch thực thi (`STUDY`, `BUFFER`, `REVISION`, `RECOVERY`) và ánh xạ `external_calendar_event_id` sang Google/Outlook Calendar (`calendar_connections`). |
| **11** | **Weekly Review** | `ai_reviews` | `evaluation` | Báo cáo đánh giá định kỳ kết hợp chỉ số định lượng (`quantitative_summary`), phản tư chủ quan của người học (`user_reflection_payload`) và khuyến nghị thích ứng từ AI. |

---

## 2. Từ điển Dữ liệu Toàn diện (Data Dictionary - 35 Bảng Vật lý)

---

### PHẦN A — BOUNDED CONTEXT 1: `account` (12 BẢNG)

#### 2.1. Bảng `users` (Tài khoản, Phân quyền RBAC & Gói dịch vụ)
* **Mục đích:** Quản lý danh tính người dùng, phân quyền, gói dịch vụ, trạng thái khóa tài khoản và múi giờ cục bộ.
* **Ánh xạ yêu cầu:** `FR-AUTH-001`, `FR-ADM-002`, `BUSR-01`, `BUSR-11`, `OS-02`.

| Cột (Column) | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 (RFC 9562) | Định danh duy nhất người dùng. |
| `email` | `VARCHAR(255)` | No | None | No | No | Yes* | No | RFC 5322 Email Format | Tên đăng nhập duy nhất toàn hệ thống (không phân biệt hoa thường qua `uq_users_lower_email`). |
| `password_hash` | `VARCHAR(255)` | No | None | No | No | No | No | Argon2id Hash String | `NFR-SEC-001`. Mật khẩu băm an toàn, không bao giờ lưu văn bản thô. |
| `full_name` | `VARCHAR(100)` | No | None | No | No | No | No | 1–100 ký tự | Tên hiển thị người dùng trên giao diện ứng dụng. |
| `timezone` | `VARCHAR(50)` | No | `'Asia/Ho_Chi_Minh'` | No | No | No | No | Chuỗi IANA Timezone | Căn cứ tính chuyển giao ngày và lịch chạy Taskiq Scheduler. |
| `role` | `VARCHAR(20)` | No | `'LEARNER'` | No | No | No | Yes | `'LEARNER'`, `'ADMIN'` | Phân quyền vai trò hệ thống (`chk_users_role`). |
| `tier` | `VARCHAR(20)` | No | `'FREE'` | No | No | No | Yes | `'FREE'`, `'PREMIUM'` | Phân tầng tài khoản chi phối định mức hạn ngạch AI (Free: 30, Prem: 300) (`chk_users_tier`). |
| `is_locked` | `BOOLEAN` | No | `FALSE` | No | No | No | No | `TRUE`, `FALSE` | Cờ khóa tài khoản bởi Admin (`UC-26`); nếu `TRUE` thì chặn đăng nhập (`UC-02`). |
| `premium_expires_at` | `TIMESTAMPTZ` | Yes | None | No | No | No | No | Dấu thời gian UTC | Thời điểm hết hạn gói cước `PREMIUM` (NULL với gói `FREE` hoặc vĩnh viễn). |
| `last_login_at` | `TIMESTAMPTZ` | Yes | None | No | No | No | No | Dấu thời gian UTC | Thời điểm đăng nhập thành công gần nhất phục vụ phát hiện tài khoản không hoạt động. |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm đăng ký tài khoản. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm cập nhật gần nhất (Trigger `trg_users_updated_at`). |

---

#### 2.2. Bảng `learner_profiles` (Hồ sơ Năng lực Người học - Zimmerman SRL)
* **Mục đích:** Quan hệ 1:1 với `users`, lưu trữ thói quen và độ dốc nhận thức được tổng hợp bất đồng bộ qua Taskiq Worker.
* **Ánh xạ yêu cầu:** `FR-PROFILE-001` (Learner Profile Memory - Zimmerman Self-Regulated Learning).

| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 | Định danh hồ sơ năng lực. |
| `user_id` | `UUID` | No | None | No | `users(id)` | Yes | No | UUID tồn tại | Khóa ngoại 1:1 tham chiếu người dùng (`ON DELETE CASCADE`). |
| `optimal_focus_duration_mins` | `INTEGER` | No | `25` | No | No | No | Yes | 15 đến 120 phút | Trung vị thời lượng Pomodoro thực tế hoàn thành tốt nhất (`chk_learner_profiles_duration`). |
| `peak_productivity_slots` | `JSONB` | No | `'["MORNING", "EVENING"]'::jsonb` | No | No | No | No | JSON Array | Khung giờ có tỷ lệ hoàn thành cao nhất ($\ge 70\%$). |
| `estimation_bias_factor` | `NUMERIC(4,2)` | No | `1.00` | No | No | No | Yes | 0.50 đến 2.00 | Hệ số chệch giữa thời gian thực tế và ước lượng ($T_{actual}/T_{estimated}$) (`chk_learner_profiles_bias`). |
| `weekly_completion_rate` | `NUMERIC(5,2)` | No | `0.00` | No | No | No | Yes | 0.00% đến 100.00% | Tỷ lệ hoàn thành nhiệm vụ theo lịch trong tuần gần nhất (`chk_learner_profiles_rate`). |
| `total_completed_sessions` | `INTEGER` | No | `0` | No | No | No | Yes | $\ge 0$ | Tổng số phiên Pomodoro hoàn thành thành công (`chk_learner_profiles_sessions`). |
| `is_cold_start` | `BOOLEAN` | No | `TRUE` | No | No | No | No | `TRUE`, `FALSE` | Đánh dấu người học mới chưa đủ dữ liệu thống kê ($< 5$ phiên học). |
| `last_aggregated_at` | `TIMESTAMPTZ` | Yes | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm Taskiq Worker chạy tổng hợp chỉ số gần nhất. |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm khởi tạo hồ sơ. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm cập nhật gần nhất (Trigger `trg_learner_profiles_updated_at`). |

---

#### 2.3. Bảng `webcal_tokens` (Bảo mật Đồng bộ Lịch 1 Chiều WebCal Feed .ics)
* **Mục đích:** Lưu trữ bản băm SHA-256 của token đồng bộ lịch 1 chiều (`.ics`) phục vụ người học đăng ký feed lịch cá nhân vào Apple/Google/Outlook Calendar mà không cần cấp quyền OAuth.
* **Ánh xạ yêu cầu:** `FR-CALENDAR-002`, `FR-CALENDAR-003`, `BUSR-08`.

| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 | Định danh bản ghi token. |
| `user_id` | `UUID` | No | None | No | `users(id)` | Yes | No | UUID tồn tại | Quan hệ 1:1 với người dùng (`ON DELETE CASCADE`). |
| `token_hash` | `VARCHAR(64)` | No | None | No | No | Yes | Yes* | 64 ký tự Hex | Bản băm SHA-256 của CSPRN 32-byte hex; không lưu token thô (`chk_webcal_tokens_hash`). |
| `is_active` | `BOOLEAN` | No | `TRUE` | No | No | No | No | `TRUE`, `FALSE` | Trạng thái hiệu lực; chuyển sang `FALSE` khi người học thu hồi token. |
| `last_used_at` | `TIMESTAMPTZ` | Yes | None | No | No | No | No | Dấu thời gian UTC | Thời điểm ứng dụng lịch ngoại vi đồng bộ feed gần nhất. |
| `rotated_at` | `TIMESTAMPTZ` | Yes | None | No | No | No | No | Dấu thời gian UTC | Thời điểm xoay vòng/làm mới token gần nhất (`FR-CALENDAR-003`). |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm khởi tạo token lần đầu. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm cập nhật gần nhất (Trigger `trg_webcal_tokens_updated_at`). |

*\*Ràng buộc regex:* `CONSTRAINT chk_webcal_tokens_hash CHECK (token_hash ~ '^[0-9a-f]{64}$')`.

---

#### 2.4. Bảng `calendar_connections` (Kết nối Lịch Ngoại vi 2 Chiều OAuth - Chuẩn hóa 3NF/BCNF)
* **Mục đích:** Quản lý kết nối OAuth 2 chiều với Google Calendar, Outlook Calendar hoặc Local Mock (tách chuẩn BCNF khỏi `webcal_tokens` theo SRS §12). Lưu trữ Refresh Token mã hóa Fernet đối xứng.
* **Ánh xạ yêu cầu:** `SRS §12`, `FR-CALENDAR-002`, `FR-CALENDAR-003`, `OS-05`.

| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 | Định danh duy nhất kết nối lịch OAuth. |
| `user_id` | `UUID` | No | None | No | `users(id)` | Yes* | No | UUID tồn tại | Người sở hữu kết nối lịch (`ON DELETE CASCADE`). |
| `provider` | `VARCHAR(30)` | No | `'GOOGLE'` | No | No | Yes* | Yes | `'GOOGLE'`, `'OUTLOOK'`, `'LOCAL_MOCK'` | Nhà cung cấp lịch ngoại vi (`chk_calendar_connections_provider`). |
| `external_calendar_id` | `VARCHAR(255)` | No | `'primary'` | No | No | No | No | Chuỗi ID lịch | Định danh lịch đích ngoại vi (mặc định `'primary'`). |
| `oauth_refresh_token_encrypted` | `TEXT` | No | None | No | No | No | No | Chuỗi mã hóa Fernet | Refresh token OAuth2 mã hóa đối xứng bằng Fernet (`NFR-SEC-001`). |
| `sync_status` | `VARCHAR(20)` | No | `'ACTIVE'` | No | No | No | Yes | `'ACTIVE'`, `'REVOKED'`, `'ERROR'` | Trạng thái đồng bộ lịch (`chk_calendar_connections_status`). |
| `last_synced_at` | `TIMESTAMPTZ` | Yes | None | No | No | No | No | Dấu thời gian UTC | Thời điểm đồng bộ 2 chiều thành công gần nhất. |
| `error_detail` | `TEXT` | Yes | None | No | No | No | No | Văn bản | Chi tiết thông báo lỗi nếu đồng bộ thất bại. |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm liên kết tài khoản lịch. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm cập nhật gần nhất (Trigger `trg_calendar_connections_updated_at`). |

*\*Ràng buộc duy nhất:* `CONSTRAINT uq_calendar_connections_user_provider UNIQUE (user_id, provider)`.

---

#### 2.5. Bảng `availabilities` (Cấu hình Quỹ Thời gian Rảnh Tổng thể)
* **Mục đích:** Cấu hình thời gian rảnh gốc của người dùng (Mode A quỹ giờ/ngày hoặc Mode B khung giờ cố định).
* **Ánh xạ yêu cầu:** `FR-AVAIL-001..002`, `BUSR-03..04`, `OS-06`.

| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 | Khóa chính cấu hình. |
| `user_id` | `UUID` | No | None | No | `users(id)` | Yes | No | UUID tồn tại | Quan hệ 1:1 với người học (`ON DELETE CASCADE`). |
| `mode` | `VARCHAR(20)` | No | `'MODE_A'` | No | No | No | Yes | `'MODE_A'`, `'MODE_B'` | Phân loại chế độ rảnh (Mode A: Quỹ giờ, Mode B: Khung giờ). |
| `calendar_integration_mode` | `VARCHAR(20)` | No | `'NONE'` | No | No | No | Yes | `'NONE'`, `'EXPORT_ICS'`, `'CONNECTED'` | Trạng thái tích hợp lịch ngoài. |
| `daily_quotas` | `JSONB` | No | `'{}'::jsonb` | No | No | No | Yes* | Map thứ (`MON`..`SUN`) -> số giờ (`0.5`–`14.0`h) | Controlled JSONB Value Object lưu hạn mức giờ học mỗi ngày trong tuần cho chế độ `MODE_A` (ánh xạ sang `WeeklySchedule.dailyQuotas`, kiểm định bởi `chk_availabilities_quotas_json` / `fn_validate_daily_quotas(daily_quotas, mode)`). |
| `min_session_minutes` | `INTEGER` | No | `30` | No | No | No | Yes | 15 đến 120 phút | Thời lượng phiên học tối thiểu khả thi (`chk_availabilities_min_session`). |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm khởi tạo cấu hình. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm cập nhật cấu hình gần nhất (Trigger `trg_availabilities_updated_at`). |

*\*Ràng buộc miền giá trị JSONB:* `CONSTRAINT chk_availabilities_quotas_json CHECK (fn_validate_daily_quotas(daily_quotas, mode))` đảm bảo `jsonb_typeof(daily_quotas) = 'object'`, mọi khóa thuộc `('MON'..'SUN', 'MONDAY'..'SUNDAY')`, mọi giá trị là số thực trong khoảng `[0.5, 14.0]` giờ/ngày và `daily_quotas <> '{}'::jsonb` khi `mode = 'MODE_A'`.

---

#### 2.6. Bảng `availability_slots` (Khung Giờ Rảnh & Mức Năng Lượng Chi tiết - Chuẩn hóa 3NF)
* **Mục đích:** Lưu trữ chuẩn hóa từng khung giờ rảnh trong tuần kèm mức năng lượng `energy_level`, ánh xạ trực tiếp sang Value Objects `WeeklySchedule` & `TimeSlot` tại tầng Repository.
* **Ánh xạ yêu cầu:** `FR-AVAIL-002`, `BUSR-03`, `BUSR-04`, Mentor §7.2 (Energy-Aware Planning).

| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 | Khóa chính khung giờ rảnh. |
| `availability_id` | `UUID` | No | None | No | `availabilities(id)` | No | No | UUID tồn tại | Khóa ngoại trỏ về cấu hình rảnh cha (`ON DELETE CASCADE`). |
| `day_of_week` | `SMALLINT` | No | None | No | No | No | Yes | 0 đến 6 | Ngày trong tuần (0: Thứ Hai .. 6: Chủ Nhật, `chk_avail_slots_day`). |
| `start_time` | `TIME` | No | None | No | No | No | No | HH:MM:SS | Giờ bắt đầu khung thời gian rảnh. |
| `end_time` | `TIME` | No | None | No | No | No | Yes* | HH:MM:SS | Giờ kết thúc khung thời gian rảnh. |
| `end_day_offset` | `SMALLINT` | No | `0` | No | No | No | Yes | `0`, `1` | Độ lệch ngày kết thúc (`0`: cùng ngày, `1`: vắt qua nửa đêm sang ngày hôm sau). |
| `slot_type` | `VARCHAR(20)` | No | `'ALLOWED'` | No | No | No | Yes | `'ALLOWED'`, `'FIXED'` | Phân biệt khung giờ cho phép (`allowedWindows`) và khung giờ cố định (`fixedSlots`). |
| `energy_level` | `VARCHAR(10)` | No | `'MEDIUM'` | No | No | No | Yes | `'LOW'`, `'MEDIUM'`, `'HIGH'` | Mức năng lượng sinh học tự khai báo trong khung giờ (`chk_avail_slots_energy`). |
| `is_active` | `BOOLEAN` | No | `TRUE` | No | No | No | No | `TRUE`, `FALSE` | Trạng thái bật/tắt của khung giờ rảnh này. |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm thêm khung giờ. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm sửa đổi khung giờ gần nhất (Trigger `trg_availability_slots_updated_at`). |

*\*Ràng buộc thời gian:* `CONSTRAINT chk_avail_slots_time CHECK (end_day_offset = 1 OR end_time > start_time)`.  
*\*Chống xung đột trùng khung giờ rảnh đồng thời (DEC-03):* Partial Unique Index `CREATE UNIQUE INDEX uq_availability_slots_active_time ON availability_slots (availability_id, day_of_week, start_time) WHERE is_active = TRUE;`.

---

#### 2.7. Bảng `ai_quotas` (Hạn ngạch AI Chu kỳ Hiện tại - 2-Phase Quota Guard)
* **Mục đích:** Kiểm soát hạn ngạch số lượt gọi AI của người dùng trong một chu kỳ tháng kèm bộ đếm giữ chỗ 2 pha `reserved_calls`.
* **Ánh xạ yêu cầu:** `FR-QUOTA-001`, `BUSR-10`, `OS-02`, `ASR-02`.

| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 | Định danh bản ghi hạn ngạch. |
| `user_id` | `UUID` | No | None | No | `users(id)` | Yes | No | UUID tồn tại | Quan hệ 1:1 với người dùng (`ON DELETE CASCADE`). |
| `monthly_limit` | `INTEGER` | No | `30` | No | No | No | Yes | $> 0$ (Free: 30, Prem: 300) | Định mức gọi AI tối đa trong chu kỳ. |
| `used_calls` | `INTEGER` | No | `0` | No | No | No | Yes | $\ge 0$ | Số lượt gọi AI đã thực thi và commit thành công trong chu kỳ. |
| `reserved_calls` | `INTEGER` | No | `0` | No | No | No | Yes | $\ge 0$ | Số lượt gọi AI đang tạm giữ chỗ (`RESERVED`) chờ LLM phản hồi. |
| `tokens_consumed` | `BIGINT` | No | `0` | No | No | No | Yes | $\ge 0$ | Tổng token tiêu thụ trong chu kỳ (kiểu `BIGINT` chống tràn số). |
| `cycle_start` | `TIMESTAMPTZ` | No | None | No | No | No | No | Dấu thời gian UTC | Thời điểm bắt đầu chu kỳ (đầu tháng). |
| `cycle_end` | `TIMESTAMPTZ` | No | None | No | No | No | Yes | `cycle_end > cycle_start` | Thời điểm kết thúc chu kỳ (cuối tháng). |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm khởi tạo hạn ngạch. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm cập nhật gần nhất (Trigger `trg_ai_quotas_updated_at`). |

*\*Ràng buộc tổng hạn ngạch:* `CONSTRAINT chk_ai_quotas_limit CHECK (used_calls + reserved_calls <= monthly_limit)`.

---

#### 2.8. Bảng `ai_quota_reservations` (Sổ cái Giữ chỗ Hạn ngạch AI 2 Pha)
* **Mục đích:** Theo dõi từng giao dịch giữ chỗ hạn ngạch AI 2 pha (`Reserve -> Commit / Release / Expired`), giúp Taskiq `QuotaSweeper` tự động thu hồi các lượt giữ chỗ bị treo khi tiến trình gọi LLM gặp sự cố.
* **Ánh xạ yêu cầu:** `FR-QUOTA-001`, `BUSR-10`, `ASR-02`, Sequence Diagram `SD3` & `SD9`.

| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 | Định danh duy nhất của phiên giữ chỗ hạn ngạch. |
| `quota_id` | `UUID` | No | None | No | `ai_quotas(id)` | No | No | UUID tồn tại | Khóa ngoại tham chiếu bản ghi hạn ngạch gốc (`ON DELETE CASCADE`). |
| `user_id` | `UUID` | No | None | No | `users(id)` | No | No | UUID tồn tại | Người học thực hiện yêu cầu gọi AI (`ON DELETE CASCADE`). |
| `operation_type` | `VARCHAR(50)` | No | None | No | No | No | No | Tên nghiệp vụ AI | Loại thao tác yêu cầu giữ chỗ (ví dụ: `ROADMAP_GENERATION`, `SCHEDULE_PROPOSAL`, `KNOWLEDGE_INGESTION`). |
| `status` | `VARCHAR(20)` | No | `'RESERVED'` | No | No | No | Yes | `'RESERVED'`, `'COMMITTED'`, `'RELEASED'`, `'EXPIRED'` | Trạng thái vòng đời của bản ghi giữ chỗ (`chk_ai_quota_res_status`). |
| `tokens_reserved` | `INTEGER` | No | `0` | No | No | No | Yes | $\ge 0$ | Số lượng token tạm ước tính/giữ chỗ (`chk_ai_quota_res_tokens`). |
| `expires_at` | `TIMESTAMPTZ` | No | None | No | No | No | No | Dấu thời gian UTC | Thời điểm hết hạn giữ chỗ (mặc định `created_at + 5 phút (300 giây)`). |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm khởi tạo giữ chỗ Pha 1. |
| `resolved_at` | `TIMESTAMPTZ` | Yes | None | No | No | No | Yes* | Dấu thời gian UTC | Thời điểm chốt Pha 2 (`COMMITTED`, `RELEASED` hoặc `EXPIRED`). |

*\*Ràng buộc đối soát:* `CONSTRAINT chk_ai_quota_res_resolved CHECK ((status = 'RESERVED' AND resolved_at IS NULL) OR (status != 'RESERVED' AND resolved_at IS NOT NULL))`.

---

#### 2.9. Bảng `ai_usage_logs` (Nhật ký Gọi Dịch vụ AI Chi tiết)
* **Mục đích:** Lưu vết kiểm toán từng lần gọi AI qua `LLMProviderPort`: loại nghiệp vụ (bao gồm `KNOWLEDGE_INGESTION` & `WHAT_IF_SIMULATION`), số token, độ trễ, mô hình (`gemini-2.5-flash`) và trạng thái.
* **Ánh xạ yêu cầu:** `FR-QUOTA-001`, `FR-ADM-003`, `NFR-SEC-003`, `BUSR-10`.

| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 | Khóa chính bản ghi nhật ký. |
| `user_id` | `UUID` | No | None | No | `users(id)` | No | No | UUID tồn tại | Người dùng thực hiện gọi AI (`ON DELETE CASCADE`). |
| `reservation_id` | `UUID` | Yes | None | No | `ai_quota_reservations(id)` | No | No | UUID tồn tại | Khóa ngoại trỏ về phiên giữ chỗ hạn ngạch AI 2 pha (`ON DELETE SET NULL`). |
| `action_type` | `VARCHAR(50)` | No | None | No | No | No | Yes | Danh mục 11 hành động | Nghiệp vụ gọi AI: `ROADMAP_GENERATION`, `MILESTONE_BREAKDOWN`, `SCHEDULE_PROPOSAL`, `AI_RESCHEDULE`, `TASK_MICRO_STEPPING`, `MILESTONE_PROVE_CHECK`, `AI_REVIEW_WEEKLY`, `AI_REVIEW_MILESTONE`, `CHAT_ASSISTANT`, `KNOWLEDGE_INGESTION`, `WHAT_IF_SIMULATION` (`chk_ai_usage_logs_action`). |
| `model_name` | `VARCHAR(100)` | No | `'gemini-2.5-flash'` | No | No | No | No | Chuỗi tên model | Mô hình LLM tiếp nhận xử lý (mặc định `'gemini-2.5-flash'`). |
| `attempt_no` | `SMALLINT` | No | `1` | No | No | No | Yes | 1 đến 5 | Số thứ tự lần thử gọi LLM trong cùng một tác vụ (`chk_ai_usage_logs_attempt`). |
| `prompt_tokens` | `INTEGER` | No | `0` | No | No | No | Yes | $\ge 0$ | Số lượng token đầu vào (prompt). |
| `completion_tokens` | `INTEGER` | No | `0` | No | No | No | Yes | $\ge 0$ | Số lượng token đầu ra (completion). |
| `total_tokens` | `INTEGER` | No | `0` | No | No | No | Yes | $\ge 0$ | Tổng số token tiêu thụ của lượt gọi. |
| `latency_ms` | `INTEGER` | No | `0` | No | No | No | Yes | $\ge 0$ | Thời gian phản hồi tính bằng mili-giây. |
| `estimated_cost_usd` | `NUMERIC(10,6)` | No | `0.000000` | No | No | No | Yes | $\ge 0$ | Chi phí ước tính tính bằng USD dựa trên định mức giá token của model. |
| `status` | `VARCHAR(20)` | No | `'SUCCESS'` | No | No | No | Yes | 4 trạng thái | Kết quả gọi: `'SUCCESS'`, `'FAILED'`, `'RATE_LIMITED'`, `'TIMEOUT'`. |
| `error_message` | `TEXT` | Yes | None | No | No | No | No | Văn bản | Chi tiết thông báo lỗi nếu gọi thất bại. |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm ghi nhận lượt gọi AI. |

---

#### 2.10. Bảng `payment_transactions` (Giao dịch Thanh toán Nâng cấp Gói)
* **Mục đích:** Lưu trữ đơn hàng và kết quả đối soát Webhook `HMAC-SHA256` khi người học nâng cấp lên gói `PREMIUM` qua `PaymentGatewayPort`.
* **Ánh xạ yêu cầu:** `FR-QUOTA-002`, `UC-04`, `UC-05`, `UC-27`, `ASR-06`.

| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 | Định danh duy nhất của giao dịch thanh toán. |
| `user_id` | `UUID` | No | None | No | `users(id)` | No | No | UUID tồn tại | Người học thực hiện thanh toán (`ON DELETE RESTRICT` bảo vệ chứng từ). |
| `transaction_ref` | `VARCHAR(100)` | No | None | No | No | Yes | No | Mã tham chiếu duy nhất | Mã đơn hàng duy nhất đối soát với cổng thanh toán (`uq_payment_transactions_ref`). |
| `gateway_provider` | `VARCHAR(20)` | No | `'PAYOS'` | No | No | No | Yes | `'PAYOS'`, `'VNPAY'`, `'MOCK'` | Nhà cung cấp cổng thanh toán xử lý giao dịch (`chk_payment_transactions_provider`). |
| `amount_vnd` | `INTEGER` | No | None | No | No | No | Yes | $> 0$ | Số tiền thanh toán tính bằng Đồng Việt Nam (`chk_payment_transactions_amount`). |
| `currency` | `VARCHAR(10)` | No | `'VND'` | No | No | No | No | `'VND'` | Đơn vị tiền tệ thanh toán. |
| `status` | `VARCHAR(20)` | No | `'PENDING'` | No | No | No | Yes | `'PENDING'`, `'PAID'`, `'FAILED'`, `'CANCELLED'`, `'EXPIRED'` | Trạng thái vòng đời của giao dịch (`chk_payment_transactions_status`). |
| `qr_code_url` | `TEXT` | Yes | None | No | No | No | No | URL hợp lệ | Đường dẫn mã QR / trang checkout trả về từ cổng thanh toán. |
| `webhook_signature_verified` | `BOOLEAN` | No | `FALSE` | No | No | No | No | `TRUE`, `FALSE` | Cờ xác nhận chữ ký số Webhook `HMAC-SHA256` đã được kiểm tra hợp lệ. |
| `paid_at` | `TIMESTAMPTZ` | Yes | None | No | No | No | Yes* | Dấu thời gian UTC | Thời điểm thanh toán thành công (`chk_payment_transactions_paid_at`). |
| `expires_at` | `TIMESTAMPTZ` | Yes | None | No | No | No | No | Dấu thời gian UTC | Thời điểm hết hạn hiệu lực của đơn hàng thanh toán (mặc định 15 phút sau khi tạo). |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm khởi tạo giao dịch. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm cập nhật gần nhất (Trigger `trg_payment_transactions_updated_at`). |

---

#### 2.11. Bảng `learner_memory_items` (Trí nhớ Người học Cấu trúc hóa 4×3 — MỚI v3.2)
* **Mục đích:** Lưu trữ chuẩn hóa 3NF/BCNF các nhận định trí nhớ người học theo ma trận **4 Danh mục (`PROFILE`, `BEHAVIORAL`, `KNOWLEDGE`, `INTERACTION`) × 3 Mức nhận thức (`EXPLICIT`, `OBSERVED`, `INFERRED`)**, kèm kích thước mẫu, độ tin cậy và trạng thái xác nhận của người học.
* **Ánh xạ yêu cầu:** `FR-PROFILE-001`, FocusFlow Learning Intelligence Harness (`Learner Feature Snapshot`).

| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 | Định danh duy nhất của mục trí nhớ người học. |
| `user_id` | `UUID` | No | None | No | `users(id)` | Yes* | No | UUID tồn tại | Người học sở hữu mục trí nhớ (`ON DELETE CASCADE`). |
| `memory_category` | `VARCHAR(30)` | No | None | No | No | Yes* | Yes | `'PROFILE'`, `'BEHAVIORAL'`, `'KNOWLEDGE'`, `'INTERACTION'` | Danh mục trí nhớ người học (`chk_learner_memory_items_category`). |
| `epistemic_type` | `VARCHAR(20)` | No | None | No | No | No | Yes | `'EXPLICIT'`, `'OBSERVED'`, `'INFERRED'` | Mức độ nhận thức: Người học tự khai báo (`EXPLICIT`), quan sát từ dữ liệu (`OBSERVED`), hoặc suy luận bởi AI (`INFERRED`). |
| `memory_key` | `VARCHAR(120)` | No | None | No | No | Yes* | No | Chuỗi khóa chuẩn | Khóa nhận định trong danh mục (ví dụ: `'preferred_explanation_style'`, `'evening_fatigue_pattern'`). |
| `claim_value` | `JSONB` | No | None | No | No | No | Yes | JSON Object | Giá trị chi tiết của nhận định (`jsonb_typeof(claim_value) = 'object'`). |
| `source_evidence` | `TEXT` | No | `''` | No | No | No | No | Văn bản | Dẫn chứng giải thích vì sao hệ thống ghi nhận mục trí nhớ này. |
| `sample_size` | `INTEGER` | No | `1` | No | No | No | Yes | $\ge 0$ | Số lượng phiên học/sự kiện làm cơ sở thống kê cho nhận định (`chk_learner_memory_items_sample_size`). |
| `observation_window_days` | `INTEGER` | Yes | None | No | No | No | Yes | `NULL` hoặc $\ge 0$ | Độ rộng cửa sổ thời gian quan sát tính bằng ngày (`chk_learner_memory_items_window`). |
| `confidence_score` | `NUMERIC(4,3)` | No | `1.000` | No | No | No | Yes | `0.000` đến `1.000` | Độ tin cậy của nhận định (`chk_learner_memory_items_confidence`). |
| `confirmation_status` | `VARCHAR(25)` | No | `'UNCONFIRMED'` | No | No | No | Yes | `'UNCONFIRMED'`, `'CONFIRMED'`, `'REJECTED'`, `'EDITED'` | Trạng thái người học duyệt/sửa/bác bỏ nhận định suy luận (`chk_learner_memory_items_confirmation`). |
| `confirmed_at` | `TIMESTAMPTZ` | Yes | None | No | No | No | No | Dấu thời gian UTC | Thời điểm người học xác nhận hoặc chỉnh sửa nhận định. |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm tạo mục trí nhớ. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm cập nhật gần nhất (Trigger `trg_learner_memory_items_updated_at`). |

*\*Ràng buộc duy nhất:* `CONSTRAINT uq_learner_memory_items_user_cat_key UNIQUE (user_id, memory_category, memory_key)`.

---

#### 2.12. Bảng `learner_concept_masteries` (Theo dõi Thành thạo Khái niệm & Ôn tập Thông minh — MỚI v3.2)
* **Mục đích:** Theo dõi mức độ nắm vững từng khái niệm học thuật (`learning_concepts`) của người học xuyên suốt các lộ trình, tổng hợp mẫu lỗi sai và lên lịch ôn tập thông minh (`next_review_at`).
* **Ánh xạ yêu cầu:** `FR-PROFILE-001`, `FR-EVAL-004`, FocusFlow Learning Intelligence Harness (`Skill Mastery & Intelligent Revision`).

| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 | Định danh bản ghi thành thạo khái niệm. |
| `user_id` | `UUID` | No | None | No | `users(id)` | Yes* | No | UUID tồn tại | Người học (`ON DELETE CASCADE`, Intra-Context FK). |
| `concept_id` | `VARCHAR(120)` | No | None | No | `learning_concepts(concept_id)` | Yes* | No | Mã concept tồn tại | Khái niệm học thuật (`ON DELETE CASCADE`, Cross-Context FK `account -> planning`). |
| `mastery_score` | `NUMERIC(5,2)` | No | `0.00` | No | No | No | Yes | `0.00` đến `100.00` | Điểm thành thạo khái niệm (`chk_learner_mastery_score`). |
| `mastery_level` | `VARCHAR(20)` | No | `'NOVICE'` | No | No | No | Yes | `'NOVICE'`, `'DEVELOPING'`, `'PROFICIENT'`, `'MASTERED'` | Cấp độ thành thạo hiện tại (`chk_learner_mastery_level`). |
| `evidence_count` | `INTEGER` | No | `0` | No | No | No | Yes | $\ge 0$ | Số lượng bằng chứng (Takeaway, Prove Mode) đã đóng góp vào điểm thành thạo (`chk_learner_mastery_evidence`). |
| `mistake_pattern_summary` | `JSONB` | No | `'[]'::jsonb` | No | No | No | Yes | JSON Array | Tóm tắt các mẫu lỗi sai thường gặp của người học trên khái niệm này (`chk_learner_mastery_mistakes_json`). |
| `last_practiced_at` | `TIMESTAMPTZ` | Yes | None | No | No | No | No | Dấu thời gian UTC | Thời điểm thực hành hoặc kiểm chứng khái niệm gần nhất. |
| `next_review_at` | `TIMESTAMPTZ` | Yes | None | No | No | No | No | Dấu thời gian UTC | Thời điểm khuyến nghị ôn tập lặp lại ngắt quãng tiếp theo. |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm tạo bản ghi. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm cập nhật gần nhất (Trigger `trg_learner_concept_masteries_updated_at`). |

*\*Ràng buộc duy nhất:* `CONSTRAINT uq_learner_concept_masteries_user_concept UNIQUE (user_id, concept_id)`.

---

### PHẦN B — BOUNDED CONTEXT 2: `planning` (10 BẢNG)

#### 2.13. Bảng `goals` (Mục tiêu Học tập)
* **Mục đích:** Lưu trữ mục tiêu học tập gốc của người học trước khi AI sinh lộ trình thích ứng.
* **Ánh xạ yêu cầu:** `FR-GOAL-001..002`, `NFR-SEC-003`.

| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 | Khóa chính mục tiêu. |
| `user_id` | `UUID` | No | None | No | `users(id)` | No | No | UUID tồn tại | Người sở hữu mục tiêu (`ON DELETE CASCADE`). |
| `title` | `TEXT` | No | None | No | No | No | No | Chuỗi không rỗng | Tên tiêu đề mục tiêu học tập. |
| `raw_description` | `TEXT` | No | None | No | No | No | No | Văn bản | Nguyện vọng, nền tảng kiến thức hiện tại và bối cảnh chi tiết. |
| `target_date` | `DATE` | Yes | None | No | No | No | No | YYYY-MM-DD | Hạn chót kỳ vọng hoàn thành mục tiêu. |
| `status` | `VARCHAR(20)` | No | `'ACTIVE'` | No | No | No | Yes | `'DRAFT'`, `'CLARIFIED'`, `'ACTIVE'`, `'PAUSED'`, `'COMPLETED'`, `'ABANDONED'` | Trạng thái mục tiêu (`chk_goals_status`). |
| `prior_knowledge_level` | `VARCHAR(50)` | No | `'BEGINNER'` | No | No | No | No | Chuỗi mức độ | Trình độ kiến thức trước đó (`BEGINNER`, `INTERMEDIATE`, `ADVANCED`). |
| `clarification_context` | `TEXT` | Yes | None | No | No | No | No | Văn bản | Bối cảnh làm rõ bổ sung qua hội thoại với AI. |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm tạo mục tiêu. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm sửa đổi mục tiêu gần nhất (Trigger `trg_goals_updated_at`). |

---

#### 2.14. Bảng `roadmaps` (Lộ trình Tự học Thích ứng)
* **Mục đích:** Kế hoạch học tập tổng thể phân rã từ Goal, quản lý trạng thái vòng đời học tập, hạn mức dời lịch tuần (`weekly_reschedule_budget`) và phát hiện lộ trình bị bỏ quên (`DORMANT >= 7 ngày`).
* **Ánh xạ yêu cầu:** `FR-PLAN-001`, `BUSR-01`, Mentor §7.1, §8.4, §8.6.

| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 | Khóa chính lộ trình. |
| `user_id` | `UUID` | No | None | No | `users(id)` | No | No | UUID tồn tại | Người sở hữu lộ trình (`ON DELETE CASCADE`). |
| `goal_id` | `UUID` | No | None | No | `goals(id)` | Yes | No | UUID tồn tại | Mục tiêu gốc sinh ra lộ trình này (`ON DELETE CASCADE`, quan hệ 1-1 qua `UNIQUE`). |
| `title` | `VARCHAR(255)` | No | None | No | No | No | No | Chuỗi văn bản | Tên định danh của lộ trình học tập. |
| `description` | `TEXT` | Yes | None | No | No | No | No | Văn bản | Diễn giải phạm vi kiến thức và chuẩn đầu ra của lộ trình. |
| `status` | `VARCHAR(20)` | No | `'INITIALIZED'` | No | No | No | Yes | `'INITIALIZED'`, `'ACTIVE'`, `'PAUSED'`, `'COMPLETED'`, `'ARCHIVED'` | Vòng đời lộ trình (`chk_roadmaps_status`). |
| `start_date` | `DATE` | Yes | None | No | No | No | No | YYYY-MM-DD | Ngày bắt đầu thực thi lộ trình. |
| `target_date` | `DATE` | Yes | None | No | No | No | Yes* | YYYY-MM-DD | Ngày dự kiến hoàn tất toàn bộ lộ trình (`target_date >= start_date`). |
| `weekly_reschedule_budget` | `SMALLINT` | No | `3` | No | No | No | Yes | 1 đến 10 | Ngân sách dời task quá hạn tối đa trong 1 tuần (`chk_roadmaps_weekly_budget`). |
| `weekly_reschedule_used` | `SMALLINT` | No | `0` | No | No | No | Yes | $\ge 0$ | Số lượt dời task quá hạn đã dùng trong tuần hiện tại (`chk_roadmaps_weekly_used`). |
| `budget_week_start` | `DATE` | No | `CURRENT_DATE` | No | No | No | No | YYYY-MM-DD | Ngày bắt đầu tuần tính ngân sách dời lịch. |
| `last_study_activity_at` | `TIMESTAMPTZ` | Yes | None | No | No | No | No | Dấu thời gian UTC | Thời điểm kết thúc phiên học hợp lệ gần nhất (để phát hiện `DORMANT >= 7 ngày`). |
| `reset_ritual_count` | `SMALLINT` | No | `0` | No | No | No | Yes | $\ge 0$ | Số lần thực hiện nghi thức làm lại lộ trình (Post-Failure Reset Ritual, `chk_roadmaps_reset_count`). |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm tạo lộ trình. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm cập nhật lộ trình gần nhất (Trigger `trg_roadmaps_updated_at`). |

---

#### 2.15. Bảng `milestones` (Mốc Kiến thức Tuần tự Cấp 1)
* **Mục đích:** Chia nhỏ lộ trình thành các chặng/mốc kiến thức tuần tự với cơ chế hoán đổi thứ tự và theo dõi trạng thái kiểm chứng Prove Mode.
* **Ánh xạ yêu cầu:** `FR-PLAN-002`, `BUSR-02`, Mentor §8.2.

| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 | Khóa chính mốc kiến thức. |
| `roadmap_id` | `UUID` | No | None | No | `roadmaps(id)` | No | No | UUID tồn tại | Lộ trình chứa mốc kiến thức này (`ON DELETE CASCADE`). |
| `sequence_order` | `INTEGER` | No | None | No | No | Yes* | Yes | $\ge 1$ | Thứ tự tuần tự mốc kiến thức trong lộ trình (`DEFERRABLE INITIALLY DEFERRED`). |
| `title` | `VARCHAR(255)` | No | None | No | No | No | No | Chuỗi văn bản | Tiêu đề mốc kiến thức. |
| `description` | `TEXT` | Yes | None | No | No | No | No | Văn bản | Mô tả chi tiết nội dung kiến thức cần lĩnh hội. |
| `status` | `VARCHAR(20)` | No | `'PENDING'` | No | No | No | Yes | `'PENDING'`, `'APPROVED'`, `'IN_PROGRESS'`, `'COMPLETED'` | Trạng thái mốc (`chk_milestones_status`). |
| `proof_status` | `VARCHAR(20)` | No | `'UNVERIFIED'` | No | No | No | Yes | `'UNVERIFIED'`, `'PENDING_REVIEW'`, `'PROVEN'`, `'NEEDS_REVIEW'` | Trạng thái kiểm chứng năng lực Prove Mode (`chk_milestones_proof_status`). |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm tạo mốc kiến thức. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm sửa đổi mốc gần nhất (Trigger `trg_milestones_updated_at`). |

---

#### 2.16. Bảng `official_schedules` (Lịch trình Học tập Chính thức — Frozen Baseline & Resilience Policy)
* **Mục đích:** Đại diện cho lịch học tập chính thức đang kích hoạt; đóng băng chỉ số kế hoạch cơ sở (`total_sessions`, `total_planned_minutes`) cho KPI 3 và lưu trữ cấu hình chống đứt gãy lịch trình (**Resilience Policy**).
* **Ánh xạ yêu cầu:** `FR-PLAN-003`, `BUSR-02`, `BUSR-08`, `OS-03`, FocusFlow Learning Intelligence Harness (`Resilient Scheduling Policy`).

| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 | Khóa chính lịch biểu chính thức. |
| `roadmap_id` | `UUID` | No | None | No | `roadmaps(id)` | Yes | No | UUID tồn tại | Mỗi lộ trình tại một thời điểm có 1 lịch chính thức (`ON DELETE CASCADE`, quan hệ 1-1 qua `UNIQUE`). |
| `version_number` | `INTEGER` | No | `1` | No | No | No | Yes | $\ge 1$ | Số thứ tự phiên bản lịch chính thức được áp dụng. |
| `strategy` | `VARCHAR(20)` | No | `'MERGE_EXISTING'` | No | No | No | Yes | `'MERGE_EXISTING'`, `'REPLACE_ALL'` | Chiến lược áp dụng lịch khi phê duyệt bản nháp đề xuất. |
| `total_sessions` | `INTEGER` | No | `0` | No | No | No | Yes | $\ge 0$ | Tổng số phiên học kế hoạch đóng băng (Frozen Baseline, `chk_official_schedules_sessions`). |
| `total_planned_minutes` | `INTEGER` | No | `0` | No | No | No | Yes | $\ge 0$ | Tổng số phút học kế hoạch đóng băng (`chk_official_schedules_minutes`). |
| `buffer_minutes_per_week` | `INTEGER` | No | `60` | No | No | No | Yes | $\ge 0$ | Quỹ phút dự phòng mỗi tuần để hấp thụ sự cố trễ lịch nhỏ mà không làm vỡ toàn bộ kế hoạch (`chk_official_schedules_buffer`). |
| `recovery_window_days` | `SMALLINT` | No | `7` | No | No | No | Yes | `1` đến `30` | Cửa sổ số ngày tối đa để tái phân bổ khối lượng quá hạn trong chế độ phục hồi cục bộ (`chk_official_schedules_recovery_window`). |
| `daily_workload_cap_minutes` | `INTEGER` | No | `180` | No | No | No | Yes | `15` đến `720` | Trần phụ tải học tập tối đa cho phép trong một ngày nhằm chống quá tải khi dồn lịch (`chk_official_schedules_daily_cap`). |
| `stability_weight` | `NUMERIC(3,2)` | No | `0.80` | No | No | No | Yes | `0.00` đến `1.00` | Trọng số ưu tiên giữ nguyên các khối lịch không bị ảnh hưởng khi tối ưu hóa lại lịch (`chk_official_schedules_stability_weight`). |
| `activated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm người học kích hoạt lịch chính thức. |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm khởi tạo bản ghi lịch. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm cập nhật lịch gần nhất (Trigger `trg_official_schedules_updated_at`). |

---

#### 2.17. Bảng `schedule_proposals` (Bản Đề xuất Lịch Xem trước & Mô phỏng What-If)
* **Mục đích:** Lưu trữ bản nháp đề xuất lịch xem trước từ AI/Scheduler sau khi vượt qua **3-Tier Hybrid Validation Gate**, hỗ trợ mô phỏng `'WHAT_IF_SIMULATION'`, tối ưu hóa lại lịch `'SCHEDULE_ONLY_REOPTIMIZE'`, và đo KPI AI Proposal Edit Rate.
* **Ánh xạ yêu cầu:** `FR-PLAN-005`, `BUSR-02` (Strict Apply Policy), `OS-03`, `ASR-04`, Mentor §7.3.

| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 | Khóa chính đề xuất lịch. |
| `roadmap_id` | `UUID` | No | None | No | `roadmaps(id)` | No | No | UUID tồn tại | Lộ trình được đề xuất lịch (`ON DELETE CASCADE`). |
| `user_id` | `UUID` | No | None | No | `users(id)` | No | No | UUID tồn tại | Người sở hữu đề xuất lịch (`ON DELETE CASCADE`). |
| `proposal_data` | `JSONB` | No | None | No | No | No | Yes* | JSON Object | Danh sách nhiệm vụ/khối lịch dự thảo và chỉ số đánh đổi (`chk_schedule_proposals_data`). |
| `status` | `VARCHAR(20)` | No | `'DRAFT'` | No | No | No | Yes | `'DRAFT'`, `'APPLIED'`, `'DISCARDED'` | Vòng đời đề xuất (`uq_schedule_proposals_roadmap_draft`). |
| `proposal_type` | `VARCHAR(30)` | No | `'INITIAL_SCHEDULE'` | No | No | No | Yes | `'INITIAL_SCHEDULE'`, `'AI_RECOVERY'`, `'POST_FAILURE_RESET'`, `'WHAT_IF_SIMULATION'`, `'SCHEDULE_ONLY_REOPTIMIZE'` | Phân loại đề xuất lịch (`chk_schedule_proposals_type`). |
| `original_proposal_data` | `JSONB` | Yes | None | No | No | No | No | JSON Object | Snapshot đề xuất gốc của AI trước khi người học chỉnh sửa tay (đo KPI `AI Proposal Edit Rate`). |
| `user_edit_count` | `INTEGER` | No | `0` | No | No | No | Yes | $\ge 0$ | Số thao tác chỉnh sửa thủ công của người học trước khi bấm Apply (`chk_schedule_proposals_edits`). |
| `applied_at` | `TIMESTAMPTZ` | Yes | None | No | No | No | No | Dấu thời gian UTC | Thời điểm người học bấm Apply để đưa vào lịch chính thức. |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm sinh bản đề xuất. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm sửa đổi đề xuất gần nhất (Trigger `trg_schedule_proposals_updated_at`). |

---

#### 2.18. Bảng `learning_concepts` (Cơ sở Tri thức Học thuật Đã Xác thực - Knowledge Base)
* **Mục đích:** Lưu trữ các khái niệm học thuật chuẩn hóa phục vụ tra cứu chỉ đọc (Read-only Tool Calling) cho AI Milestone Planner và làm Ground Truth kiểm chứng Takeaway ở Prove Mode.
* **Ánh xạ yêu cầu:** `FR-PLAN-004`, `ASR-04`, Mentor §8.2.

| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `concept_id` | `VARCHAR(120)` | No | None | Yes | No | Yes | No | Chuỗi định danh chuẩn | Định danh học thuật chuẩn (ví dụ: `'python.asyncio'`, `'sql.bcnf'`). |
| `title` | `VARCHAR(255)` | No | None | No | No | No | No | Chuỗi văn bản | Tiêu đề khái niệm kiến thức. |
| `summary` | `TEXT` | No | None | No | No | No | No | Văn bản | Tóm tắt lý thuyết cốt lõi của khái niệm. |
| `domain` | `VARCHAR(100)` | No | None | No | No | No | No | Chuỗi phân loại | Lĩnh vực chuyên môn (ví dụ: `'Backend'`, `'Database'`, `'Machine Learning'`). |
| `difficulty_level` | `VARCHAR(50)` | No | `'BEGINNER'` | No | No | No | No | Chuỗi mức độ | Mức độ khó (`BEGINNER`, `INTERMEDIATE`, `ADVANCED`). |
| `estimated_effort_minutes` | `INTEGER` | No | `60` | No | No | No | Yes | $> 0$ | Thời lượng ước tính trung bình để nắm vững khái niệm (`chk_learning_concepts_effort_positive`). |
| `keywords` | `JSONB` | No | `'[]'::jsonb` | No | No | No | No | JSON Array | Danh sách từ khóa chuyên môn liên quan. |
| `learning_outcomes` | `JSONB` | No | `'[]'::jsonb` | No | No | No | No | JSON Array | Chuẩn đầu ra nhận thức kỳ vọng (Bloom's Taxonomy). |
| `verification_status` | `VARCHAR(30)` | No | `'VERIFIED'` | No | No | No | Yes | `'VERIFIED'`, `'UNVERIFIED'`, `'DEPRECATED'` | Trạng thái thẩm định học thuật (`chk_learning_concepts_verification_status`). |
| `version` | `VARCHAR(20)` | No | `'1.0.0'` | No | No | No | No | Chuỗi phiên bản | Phiên bản định dạng tri thức. |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm đưa khái niệm vào cơ sở tri thức. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm cập nhật khái niệm gần nhất (Trigger `trg_learning_concepts_updated_at`). |

---

#### 2.19. Bảng `concept_prerequisites` (Quan hệ Tiên quyết Giữa các Khái niệm Tri thức)
* **Mục đích:** Lưu trữ đồ thị tiên quyết giữa các khái niệm học thuật, kiểm định không tự chu trình, cung cấp tri thức cho thuật toán sinh lộ trình.
* **Ánh xạ yêu cầu:** `FR-PLAN-004`, `ASR-04`.

| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `source_concept_id` | `VARCHAR(120)` | No | None | Yes* | `learning_concepts(concept_id)` | No | Yes** | Khái niệm nguồn | Khái niệm cần học (`ON DELETE CASCADE`). |
| `prerequisite_concept_id` | `VARCHAR(120)` | No | None | Yes* | `learning_concepts(concept_id)` | No | Yes** | Khái niệm tiên quyết | Khái niệm bắt buộc biết trước (`ON DELETE CASCADE`). |
| `relation_type` | `VARCHAR(30)` | No | `'REQUIRES'` | No | No | No | Yes | `'REQUIRES'`, `'RECOMMENDED_BEFORE'` | Mức độ bắt buộc của quan hệ (`chk_concept_prerequisites_relation_type`). |
| `rationale` | `TEXT` | No | `''` | No | No | No | No | Văn bản | Lý do sư phạm cần học trước. |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm thiết lập quan hệ tiên quyết. |

*\*Khóa chính kép:* `PRIMARY KEY (source_concept_id, prerequisite_concept_id)`.  
*\*\*Chống tự tham chiếu:* `CONSTRAINT chk_concept_prerequisites_no_self_loop CHECK (source_concept_id <> prerequisite_concept_id)`.

---

#### 2.20. Bảng `knowledge_sources` (Nguồn Tài liệu Học tập Đầu vào — Knowledge Engine — MỚI v3.2)
* **Mục đích:** Quản lý tài liệu (`PDF`, `DOCX`, `TXT`) và đường dẫn `URL` do người học tải lên/cung cấp cho một mục tiêu học tập, tích hợp kiểm duyệt chống SSRF, chống trùng lặp nội dung qua `content_hash` SHA-256 và lưu siêu dữ liệu nguồn gốc (`provenance_metadata`).
* **Ánh xạ yêu cầu:** `FR-PLAN-001`, `FR-PLAN-004`, FocusFlow Learning Intelligence Harness (`Knowledge Source`).

| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 | Định danh duy nhất của nguồn tài liệu học tập. |
| `user_id` | `UUID` | No | None | No | `users(id)` | No | No | UUID tồn tại | Người học sở hữu tài liệu (`ON DELETE CASCADE`, Cross-Context FK `planning -> account`). |
| `goal_id` | `UUID` | No | None | No | `goals(id)` | No | No | UUID tồn tại | Mục tiêu học tập được neo kiến thức bởi tài liệu này (`ON DELETE CASCADE`, Intra-Context FK). |
| `source_type` | `VARCHAR(20)` | No | None | No | No | No | Yes | `'PDF'`, `'DOCX'`, `'TXT'`, `'URL'` | Định dạng nguồn tài liệu (`chk_knowledge_sources_type`). |
| `title` | `VARCHAR(255)` | No | None | No | No | No | No | Chuỗi văn bản | Tên hiển thị của tài liệu hoặc trang web. |
| `source_uri` | `TEXT` | Yes | None | No | No | No | No | URI / Đường dẫn tệp | Đường dẫn lưu trữ tệp nội bộ hoặc URL nguồn đã qua kiểm duyệt SSRF. |
| `content_hash` | `VARCHAR(64)` | No | None | No | No | No | Yes | 64 ký tự Hex | Bản băm SHA-256 của nội dung gốc (`content_hash ~ '^[0-9a-f]{64}$'`). |
| `ingestion_status` | `VARCHAR(20)` | No | `'PENDING'` | No | No | No | Yes | `'PENDING'`, `'PROCESSING'`, `'INDEXED'`, `'FAILED'`, `'QUARANTINED'` | Trạng thái xử lý bóc tách và lập chỉ mục tài liệu (`chk_knowledge_sources_status`). |
| `chunk_count` | `INTEGER` | No | `0` | No | No | No | Yes | $\ge 0$ | Tổng số phân đoạn (`knowledge_chunks`) đã được bóc tách (`chk_knowledge_sources_chunks`). |
| `provenance_metadata` | `JSONB` | No | `'{}'::jsonb` | No | No | No | Yes | JSON Object | Siêu dữ liệu nguồn gốc (tác giả, số trang, kích thước tệp, miền URL) (`chk_knowledge_sources_provenance`). |
| `error_detail` | `TEXT` | Yes | None | No | No | No | No | Văn bản | Chi tiết nguyên nhân nếu bóc tách thất bại hoặc bị cách ly (`QUARANTINED`). |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm tải lên tài liệu. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm cập nhật gần nhất (Trigger `trg_knowledge_sources_updated_at`). |

---

#### 2.21. Bảng `knowledge_chunks` (Phân đoạn Tri thức RAG — `tsvector` + `pgvector` — MỚI v3.2)
* **Mục đích:** Lưu trữ từng phân đoạn văn bản bóc tách từ `knowledge_sources`, phục vụ truy xuất lai Hybrid RAG kết hợp tìm kiếm toàn văn bản (`search_vector TSVECTOR` GIN) và tìm kiếm tương đồng ngữ nghĩa (`embedding vector(768)` HNSW).
* **Ánh xạ yêu cầu:** `FR-PLAN-004`, FocusFlow Learning Intelligence Harness (`Knowledge Chunk`).

| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 | Định danh duy nhất của phân đoạn tri thức. |
| `source_id` | `UUID` | No | None | No | `knowledge_sources(id)` | Yes* | No | UUID tồn tại | Nguồn tài liệu cha (`ON DELETE CASCADE`, Intra-Context FK). |
| `goal_id` | `UUID` | No | None | No | `goals(id)` | No | No | UUID tồn tại | Mục tiêu học tập sở hữu phân đoạn (`ON DELETE CASCADE`, Intra-Context FK). |
| `chunk_index` | `INTEGER` | No | None | No | No | Yes* | Yes | $\ge 0$ | Thứ tự phân đoạn trong tài liệu nguồn (`chk_knowledge_chunks_index`). |
| `section_title` | `VARCHAR(255)` | Yes | None | No | No | No | No | Chuỗi văn bản | Tiêu đề chương/mục chứa phân đoạn văn bản. |
| `page_number` | `INTEGER` | Yes | None | No | No | No | Yes | `NULL` hoặc $\ge 1$ | Số trang trong tài liệu PDF/DOCX (`chk_knowledge_chunks_page`). |
| `content` | `TEXT` | No | None | No | No | No | No | Văn bản | Nội dung văn bản đã làm sạch của phân đoạn. |
| `token_count` | `INTEGER` | No | None | No | No | No | Yes | $> 0$ | Số lượng token của phân đoạn (`chk_knowledge_chunks_tokens`). |
| `search_vector` | `TSVECTOR` | Yes | None | No | No | No | No | PostgreSQL `tsvector` | Vector từ khóa phục vụ Full-Text Search qua chỉ mục GIN (`idx_knowledge_chunks_search_vector`). |
| `embedding` | `vector(768)` | Yes | None | No | No | No | No | Vector 768 chiều (`pgvector`) | Vector nhúng ngữ nghĩa phục vụ truy xuất tương đồng Cosine qua chỉ mục HNSW (`idx_knowledge_chunks_embedding_hnsw`). |
| `provenance_json` | `JSONB` | No | `'{}'::jsonb` | No | No | No | Yes | JSON Object | Siêu dữ liệu trích dẫn bổ sung (offset ký tự, đoạn văn) (`chk_knowledge_chunks_provenance`). |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm tạo phân đoạn. |

*\*Ràng buộc duy nhất:* `CONSTRAINT uq_knowledge_chunks_source_idx UNIQUE (source_id, chunk_index)`.

---

#### 2.22. Bảng `schedule_blocks` (Khối Lịch Học Thực thi & Ánh xạ Sự kiện Lịch Ngoại vi — MỚI v3.2)
* **Mục đích:** Tách biệt hoàn toàn nỗ lực ước tính của một nhiệm vụ (`tasks.estimated_minutes` = `estimated_effort`, ví dụ 120 phút) với các khối thời gian thực tế được Bộ lập lịch tất định phân bổ vào lịch (`scheduled_duration_minutes`, ví dụ hai khối 60 phút), hỗ trợ các khối `STUDY`, `BUFFER`, `REVISION`, `RECOVERY` và lưu `external_calendar_event_id` để đồng bộ Google/Outlook Calendar.
* **Ánh xạ yêu cầu:** `FR-PLAN-003`, `FR-CALENDAR-002`, FocusFlow Learning Intelligence Harness (`Calendar Event Mapping` & `Resilient Scheduling`).

| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 | Định danh duy nhất của khối lịch học. |
| `roadmap_id` | `UUID` | No | None | No | `roadmaps(id)` | No | No | UUID tồn tại | Lộ trình sở hữu khối lịch (`ON DELETE CASCADE`, Intra-Context FK). |
| `official_schedule_id` | `UUID` | No | None | No | `official_schedules(id)` | No | No | UUID tồn tại | Lịch chính thức chứa khối lịch này (`ON DELETE CASCADE`, Intra-Context FK). |
| `task_id` | `UUID` | Yes | None | No | `tasks(id)` | No | No | UUID tồn tại hoặc `NULL` | Nhiệm vụ học tập được phân bổ vào khối này (`ON DELETE CASCADE`, Cross-Context FK `planning -> execution`; `NULL` đối với khối `BUFFER` thuần túy). |
| `sequence_in_task` | `SMALLINT` | No | `1` | No | No | No | Yes | $\ge 1$ | Thứ tự buổi học của cùng một Task khi Task lớn được chia thành nhiều khối lịch (`chk_schedule_blocks_seq`). |
| `block_type` | `VARCHAR(20)` | No | `'STUDY'` | No | No | No | Yes | `'STUDY'`, `'BUFFER'`, `'REVISION'`, `'RECOVERY'` | Phân loại khối lịch: Học chính thức (`STUDY`), Dự phòng (`BUFFER`), Ôn tập (`REVISION`), Phục hồi (`RECOVERY`) (`chk_schedule_blocks_type`). |
| `block_date` | `DATE` | No | None | No | No | No | No | YYYY-MM-DD | Ngày diễn ra khối lịch học. |
| `start_time` | `TIMESTAMPTZ` | No | None | No | No | No | Yes* | Dấu thời gian UTC | Thời điểm bắt đầu khối lịch. |
| `end_time` | `TIMESTAMPTZ` | No | None | No | No | No | Yes* | Dấu thời gian UTC | Thời điểm kết thúc khối lịch (`end_time > start_time`). |
| `scheduled_duration_minutes` | `INTEGER` | No | None | No | No | No | Yes | `10` đến `240` | Thời lượng phân bổ của khối lịch này tính bằng phút (`chk_schedule_blocks_duration`). |
| `is_protected` | `BOOLEAN` | No | `FALSE` | No | No | No | No | `TRUE`, `FALSE` | Cờ khóa bảo vệ khối lịch không bị dời tự động khi tối ưu hóa lại lịch. |
| `status` | `VARCHAR(20)` | No | `'PLANNED'` | No | No | No | Yes | `'PLANNED'`, `'COMPLETED'`, `'MISSED'`, `'RESCHEDULED'`, `'CANCELLED'` | Trạng thái thực thi của khối lịch (`chk_schedule_blocks_status`). |
| `external_calendar_event_id` | `VARCHAR(255)` | Yes | None | No | No | No | No | Chuỗi ID sự kiện | Định danh sự kiện tương ứng trên Google/Outlook Calendar để đồng bộ 2 chiều. |
| `placement_rationale` | `TEXT` | Yes | None | No | No | No | No | Văn bản | Giải thích vì sao Bộ lập lịch đặt khối học vào khung giờ này (ví dụ: khớp khung năng lượng `HIGH`). |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm tạo khối lịch. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm cập nhật gần nhất (Trigger `trg_schedule_blocks_updated_at`). |

*\*Ràng buộc thứ tự thời gian:* `CONSTRAINT chk_schedule_blocks_time_order CHECK (end_time > start_time)`.

---

### PHẦN C — BOUNDED CONTEXT 3: `execution` (5 BẢNG)

#### 2.23. Bảng `tasks` (Nhiệm vụ Học tập Chi tiết Cấp 2)
* **Mục đích:** Đầu việc học tập cụ thể, hỗ trợ chia nhỏ nhiệm vụ Micro-Stepping (`parent_task_id`), neo tri thức học thuật (`concept_id`) và lưu danh sách trích dẫn nguồn từ Knowledge Engine (`learning_resources_json`). **Lưu ý quan trọng:** Cột `estimated_minutes` biểu diễn nỗ lực ước tính bởi AI (`estimated_effort`), trong khi thời lượng phân bổ lịch của từng buổi học được quản lý tại `schedule_blocks.scheduled_duration_minutes`.
* **Ánh xạ yêu cầu:** `FR-TASK-001`, `FR-ADAPT-003`, `BUSR-06`, `BUSR-07`, `UC-13`, `UC-14`, `UC-23`, Mentor §8.2.

| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 | Khóa chính nhiệm vụ. |
| `roadmap_id` | `UUID` | No | None | No | `roadmaps(id)` | No | No | UUID tồn tại | Lộ trình chứa nhiệm vụ (`ON DELETE CASCADE`, Cross-Context FK `execution -> planning`). |
| `milestone_id` | `UUID` | No | None | No | `milestones(id)` | No | No | UUID tồn tại | Mốc kiến thức trực thuộc (`ON DELETE CASCADE`, Cross-Context FK `execution -> planning`). |
| `official_schedule_id` | `UUID` | Yes | None | No | `official_schedules(id)` | No | No | UUID tồn tại | Lịch chính thức phân bổ nhiệm vụ này (`ON DELETE SET NULL`, Cross-Context FK `execution -> planning`). |
| `parent_task_id` | `UUID` | Yes | None | No | `tasks(id)` | No | Yes* | UUID tồn tại | Liên kết về task cha khi chia nhỏ bằng Micro-Stepping (`ON DELETE SET NULL`, `parent_task_id <> id`). |
| `concept_id` | `VARCHAR(120)` | Yes | None | No | `learning_concepts(concept_id)` | No | No | Mã concept tồn tại | Khái niệm tri thức neo giữ Ground Truth (`ON DELETE SET NULL`). |
| `title` | `VARCHAR(255)` | No | None | No | No | No | No | Chuỗi văn bản | Tên nhiệm vụ cụ thể. |
| `description` | `TEXT` | Yes | None | No | No | No | No | Văn bản | Hướng dẫn chi tiết hoặc mục tiêu đầu ra của nhiệm vụ. |
| `estimated_minutes` | `INTEGER` | No | None | No | No | No | Yes | 15 đến 240 phút | Nỗ lực ước tính tổng thể bởi AI (`estimated_effort`, `chk_tasks_estimated_minutes`); có thể được chia thành 1 hoặc nhiều `schedule_blocks`. |
| `learning_resources_json` | `JSONB` | No | `'[]'::jsonb` | No | No | No | Yes | JSON Array | Mảng trích dẫn nguồn từ Knowledge Engine (`source_id`, `chunk_id`, `section`, `page`, `relevance`) (`chk_tasks_learning_resources_json`). |
| `scheduled_date` | `DATE` | Yes | None | No | No | No | No | YYYY-MM-DD | Ngày xếp lịch chính (`NULL` = Backlog chưa xếp lịch). |
| `scheduled_start` | `TIMESTAMPTZ` | Yes | None | No | No | No | Yes** | Dấu thời gian UTC | Mốc thời gian bắt đầu xếp lịch (`chk_tasks_scheduled_time_order`). |
| `scheduled_end` | `TIMESTAMPTZ` | Yes | None | No | No | No | Yes** | Dấu thời gian UTC | Mốc thời gian kết thúc xếp lịch (`scheduled_end > scheduled_start`). |
| `status` | `VARCHAR(20)` | No | `'TODO'` | No | No | No | Yes | `'TODO'`, `'IN_PROGRESS'`, `'COMPLETED'`, `'CANCELLED'` | Trạng thái nhiệm vụ (`chk_tasks_status`). |
| `completed_at` | `TIMESTAMPTZ` | Yes | None | No | No | No | Yes*** | Dấu thời gian UTC | Thời điểm đánh dấu hoàn thành nhiệm vụ (`chk_tasks_completed_at`). |
| `reschedule_count` | `INTEGER` | No | `0` | No | No | No | Yes | $\ge 0$ | Số lần nhiệm vụ bị dời lịch tự động liên tiếp (ngưỡng chống lặp $\ge 3$). |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm tạo nhiệm vụ. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm sửa đổi nhiệm vụ gần nhất (Trigger `trg_tasks_updated_at`). |

---

#### 2.24. Bảng `task_dependencies` (Quan hệ Tiên quyết Nhiệm vụ - DAG)
* **Mục đích:** Lưu trữ quan hệ phụ thuộc có hướng giữa các nhiệm vụ trong cùng lộ trình; kiểm định không chu trình bởi `DagCycleValidator`.
* **Ánh xạ yêu cầu:** `FR-TASK-003`, `ASR-04`.

| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 | Khóa chính cạnh quan hệ phụ thuộc. |
| `predecessor_id` | `UUID` | No | None | No | `tasks(id)` | Yes* | No | UUID tồn tại | Nhiệm vụ tiên quyết bắt buộc xong trước (`ON DELETE CASCADE`, Intra-Context FK). |
| `successor_id` | `UUID` | No | None | No | `tasks(id)` | Yes* | Yes** | UUID tồn tại | Nhiệm vụ phụ thuộc (`predecessor_id <> successor_id`, `ON DELETE CASCADE`, Intra-Context FK). |
| `roadmap_id` | `UUID` | No | None | No | `roadmaps(id)` | No | No | UUID tồn tại | Lộ trình chung chứa cả 2 task (`ON DELETE CASCADE`, Cross-Context FK `execution -> planning`). |
| `is_mandatory` | `BOOLEAN` | No | `TRUE` | No | No | No | No | `TRUE`, `FALSE` | Cờ xác định điều kiện tiên quyết bắt buộc trước khi mở khóa task kế tiếp. |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm thiết lập cạnh phụ thuộc. |

---

#### 2.25. Bảng `study_sessions` (Phiên Thực thi Học tập Pomodoro / Stopwatch / MVS & Daily Check-in)
* **Mục đích:** Quản lý buổi học tập trung, hỗ trợ Minimum Viable Session (10–15 phút), ghi nhận thời gian thực học, tín hiệu duy trì Heartbeat ping 60s, quản lý nợ Takeaway và thu thập 3 chỉ số **Daily Learning Check-in** cuối phiên.
* **Ánh xạ yêu cầu:** `FR-SESSION-001..003`, `BUSR-09`, `OS-01`, `OS-07`, `ASR-05`, `UC-14`, `UC-15`, `UC-16`, Mentor §7.2.

| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 | Khóa chính phiên học. |
| `user_id` | `UUID` | No | None | No | `users(id)` | No | No | UUID tồn tại | Người học thực hiện phiên (`ON DELETE CASCADE`). |
| `roadmap_id` | `UUID` | No | None | No | `roadmaps(id)` | No | No | UUID tồn tại | Lộ trình đang học (`ON DELETE CASCADE`). |
| `session_mode` | `VARCHAR(20)` | No | `'STANDARD'` | No | No | No | Yes | `'STANDARD'`, `'MVS'` | Chế độ học chuẩn (`UC-14`) hoặc Minimum Viable Session 10–15p (`UC-15`, `chk_study_sessions_mode`). |
| `timer_mode` | `VARCHAR(20)` | No | `'POMODORO'` | No | No | No | Yes | `'POMODORO'`, `'STOPWATCH'` | Chế độ đếm thời gian: Pomodoro từng hiệp hoặc Đồng hồ bấm giờ tự do. |
| `started_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm bắt đầu bấm giờ phiên học. |
| `ended_at` | `TIMESTAMPTZ` | Yes | None | No | No | No | Yes* | Dấu thời gian UTC | Thời điểm kết thúc phiên (`ended_at >= started_at`). |
| `planned_minutes` | `INTEGER` | No | None | No | No | No | Yes | $> 0$ | Thời lượng dự kiến ban đầu (`chk_study_sessions_planned_min`). |
| `actual_minutes` | `INTEGER` | No | `0` | No | No | No | Yes | $\ge 0$ | Thời gian thực học thực tế (tính đến gói Heartbeat ping cuối, `chk_study_sessions_actual_min`). |
| `status` | `VARCHAR(20)` | No | `'IN_PROGRESS'` | No | No | No | Yes | `'IN_PROGRESS'`, `'COMPLETED'`, `'PARTIAL_COMPLETED'`, `'CANCELLED'` | Trạng thái phiên học (`chk_study_sessions_status`). |
| `pending_takeaway` | `BOOLEAN` | No | `FALSE` | No | No | No | No | `TRUE`, `FALSE` | Cờ đánh dấu phiên bị Auto-close do rớt mạng còn nợ nhập Key Takeaway (`UC-16`). |
| `checkin_time_sufficiency` | `VARCHAR(20)` | Yes | None | No | No | No | Yes | `'ENOUGH'`, `'TIGHT'`, `'INSUFFICIENT'` | **Daily Check-in:** Cảm nhận của người học về quỹ thời gian của phiên (`chk_study_sessions_checkin_time`). |
| `checkin_perceived_difficulty` | `VARCHAR(20)` | Yes | None | No | No | No | Yes | `'EASY'`, `'AS_EXPECTED'`, `'HARDER'` | **Daily Check-in:** Cảm nhận độ khó thực tế so với dự kiến (`chk_study_sessions_checkin_diff`). |
| `checkin_focus_level` | `SMALLINT` | Yes | None | No | No | No | Yes | `1` đến `5` | **Daily Check-in:** Mức độ tập trung tự đánh giá trong phiên (`chk_study_sessions_checkin_focus`). |
| `last_heartbeat_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm client gửi ping gần nhất (quét bởi Taskiq Scheduler mỗi 60s). |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm khởi tạo bản ghi phiên học. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm cập nhật phiên học gần nhất (Trigger `trg_study_sessions_updated_at`). |

---

#### 2.26. Bảng `session_tasks` (Bảng Liên kết Nhiều - Nhiều giữa Phiên học và Nhiệm vụ)
* **Mục đích:** Cho phép một phiên học chọn nhiều task, hoặc một task chia nhỏ học trong nhiều phiên; bảo vệ lịch sử học tập với `ON DELETE RESTRICT` nội bộ Context `execution`.
* **Ánh xạ yêu cầu:** `FR-SESSION-002`, `BUSR-09`, `OS-01`.

| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 | Khóa chính bản ghi liên kết. |
| `session_id` | `UUID` | No | None | No | `study_sessions(id)` | Yes* | No | UUID tồn tại | Khóa ngoại trỏ về phiên học (`ON DELETE CASCADE`, Intra-Context FK). |
| `task_id` | `UUID` | No | None | No | `tasks(id)` | Yes* | No | UUID tồn tại | Khóa ngoại trỏ về nhiệm vụ (`ON DELETE RESTRICT` bảo vệ lịch sử học, Intra-Context FK `execution -> execution`). |
| `allocated_minutes` | `INTEGER` | No | `0` | No | No | No | Yes | $\ge 0$ | Số phút dự kiến phân bổ cho nhiệm vụ này trong phiên. |
| `actual_minutes` | `INTEGER` | No | `0` | No | No | No | Yes | $\ge 0$ | Số phút thực học thực tế cho nhiệm vụ này trong phiên. |
| `status_after_session` | `VARCHAR(20)` | No | `'IN_PROGRESS'` | No | No | No | Yes | `'TODO'`, `'IN_PROGRESS'`, `'COMPLETED'` | Trạng thái nhiệm vụ sau phiên (`chk_session_tasks_status_after`). |
| `notes` | `TEXT` | Yes | None | No | No | No | No | Văn bản | Ghi chú ngắn về tiến độ thực hiện nhiệm vụ trong phiên. |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm gán nhiệm vụ vào phiên. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm cập nhật liên kết gần nhất (Trigger `trg_session_tasks_updated_at`). |

---

#### 2.27. Bảng `study_notes` (Ghi chép Không gian Học tập & Thẩm định Bằng chứng Takeaway)
* **Mục đích:** Lưu trữ bản nháp tức thời (`SCRATCHPAD`), đúc kết cốt lõi (`TAKEAWAY`) và ghi chép tổng quát (`GENERAL`). Tích hợp thang đo tự tin (Confidence Calibration), điểm bằng chứng AI chấm và cơ chế chống ghi chú đối phó (Anti-Gaming).
* **Ánh xạ yêu cầu:** `FR-SESSION-002`, `NFR-SEC-003`, Mentor §8.2 & §8.3.

| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 | Khóa chính bản ghi chép. |
| `user_id` | `UUID` | No | None | No | `users(id)` | No | No | UUID tồn tại | Người sở hữu ghi chép (`ON DELETE CASCADE`). |
| `session_id` | `UUID` | Yes | None | No | `study_sessions(id)` | Partial* | Yes** | UUID tồn tại | Phiên học liên kết (`ON DELETE CASCADE`, Intra-Context FK). |
| `task_id` | `UUID` | Yes | None | No | `tasks(id)` | Partial* | Yes** | UUID tồn tại | Nhiệm vụ liên kết (`ON DELETE SET NULL`, Intra-Context FK `execution -> execution`). |
| `note_type` | `VARCHAR(20)` | No | None | No | No | Partial* | Yes | `'SCRATCHPAD'`, `'TAKEAWAY'`, `'GENERAL'` | Phân loại ghi chú (`chk_study_notes_type`). |
| `content` | `TEXT` | No | `''` | No | No | No | Yes*** | Văn bản Markdown | Nội dung ghi chép (bắt buộc $\ge 30$ ký tự đối với `TAKEAWAY`, `chk_study_notes_takeaway_min_length`). |
| `self_confidence` | `SMALLINT` | Yes | None | No | No | No | Yes | 1 đến 5 | Điểm tự tin do người học tự đánh giá khi viết Takeaway (`chk_study_notes_confidence`). |
| `ai_evidence_score` | `NUMERIC(3,2)` | Yes | None | No | No | No | Yes | 1.00 đến 5.00 | Điểm chất lượng bằng chứng do AI chấm đối chiếu task spec (`chk_study_notes_evidence_score`). |
| `alignment_flag` | `VARCHAR(25)` | No | `'UNCHECKED'` | No | No | No | Yes | 5 cờ trạng thái | Cờ phát hiện Takeaway đối phó: `'UNCHECKED'`, `'ALIGNED'`, `'SUPERFICIAL'`, `'OFF_TOPIC'`, `'CONTRADICTORY'` (`chk_study_notes_alignment`). |
| `verification_status` | `VARCHAR(25)` | No | `'PENDING_PROVE'` | No | No | No | Yes | 4 trạng thái | Trạng thái thẩm định Takeaway: `'PENDING_PROVE'`, `'VERIFIED'`, `'FLAGGED_SHALLOW'`, `'NEEDS_REVIEW'` (`chk_study_notes_verification`). |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm tạo ghi chép. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm sửa đổi ghi chép gần nhất (Trigger `trg_study_notes_updated_at`). |

---

### PHẦN D — BOUNDED CONTEXT 4: `evaluation` (4 BẢNG)

#### 2.28. Bảng `pause_records` (Lịch sử Tạm dừng Lộ trình & Tịnh tiến Domino Shift)
* **Mục đích:** Lưu trữ các đợt tạm dừng học tập và số ngày đã tịnh tiến dời lịch tự động của toàn bộ nhiệm vụ.
* **Ánh xạ yêu cầu:** `FR-PAUSE-001..002`, `BUSR-07`, `EVAL-03`.

| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 | Khóa chính bản ghi tạm dừng. |
| `roadmap_id` | `UUID` | No | None | No | `roadmaps(id)` | No | No | UUID tồn tại | Lộ trình được tạm dừng (`ON DELETE CASCADE`, Cross-Context FK `evaluation -> planning`). |
| `pause_start_date` | `DATE` | No | None | No | No | No | No | YYYY-MM-DD | Ngày bắt đầu tạm dừng học. |
| `pause_end_date` | `DATE` | Yes | None | No | No | No | Yes* | YYYY-MM-DD | Ngày kết thúc tạm dừng (bắt buộc khi `COMPLETED`, `NULL` khi `ACTIVE`). |
| `shifted_days` | `INTEGER` | Yes | None | No | No | No | Yes* | $\ge 0$ | Số ngày lịch học bị tịnh tiến (`shifted_days = pause_end_date - pause_start_date` khi `COMPLETED`). |
| `reason` | `TEXT` | Yes | None | No | No | No | No | Văn bản | Lý do tạm dừng. |
| `status` | `VARCHAR(20)` | No | `'ACTIVE'` | No | No | No | Yes | `'ACTIVE'`, `'COMPLETED'` | Trạng thái đợt tạm dừng (`chk_pause_records_status`). |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm ghi nhận lệnh tạm dừng. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm sửa đổi gần nhất (Trigger `trg_pause_records_updated_at`). |

---

#### 2.29. Bảng `ai_reviews` (Báo cáo Đánh giá Tiến độ, Phản tư Tuần & Khuyến nghị Thích ứng)
* **Mục đích:** Lưu trữ nhận xét định tính, bản chụp số liệu `QuantitativeMetrics` và nội dung **Weekly Reflection** (2–3 câu hỏi & câu trả lời phản tư chủ quan của người học) định kỳ tuần hoặc sau mỗi mốc kiến thức.
* **Ánh xạ yêu cầu:** `FR-REPORT-001..002`, `BUSR-12`, FocusFlow Learning Intelligence Harness (`Weekly Review`).

| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 | Khóa chính báo cáo AI. |
| `roadmap_id` | `UUID` | No | None | No | `roadmaps(id)` | No | No | UUID tồn tại | Lộ trình được đánh giá (`ON DELETE CASCADE`). |
| `user_id` | `UUID` | No | None | No | `users(id)` | No | No | UUID tồn tại | Người học nhận báo cáo (`ON DELETE CASCADE`). |
| `milestone_id` | `UUID` | Yes | None | No | `milestones(id)` | No | No | UUID tồn tại | Mốc kiến thức được đánh giá (bắt buộc khi `MILESTONE`, `ON DELETE CASCADE`). |
| `review_cycle` | `VARCHAR(20)` | No | None | No | No | No | Yes | `'WEEKLY'`, `'MILESTONE'` | Chu kỳ đánh giá (`chk_ai_reviews_cycle`). |
| `period_start` | `DATE` | Yes | None | No | No | No | No | YYYY-MM-DD | Ngày bắt đầu chu kỳ tuần (bắt buộc khi `WEEKLY`). |
| `period_end` | `DATE` | Yes | None | No | No | No | Yes* | YYYY-MM-DD | Ngày kết thúc chu kỳ tuần (`period_end >= period_start`, `chk_ai_reviews_period_order`). |
| `quantitative_summary` | `JSONB` | No | `'{}'::jsonb` | No | No | No | Yes | JSON Object | Lưu 5 chỉ số của Value Object `QuantitativeMetrics`: `completion_rate`, `planned_minutes`, `actual_minutes`, `adherence_rate`, `overdue_task_count` (`chk_ai_reviews_quantitative_summary`). |
| `user_reflection_payload` | `JSONB` | No | `'{}'::jsonb` | No | No | No | Yes | JSON Object | Lưu 2–3 câu hỏi và câu trả lời phản tư chủ quan của người học trong tuần (`chk_ai_reviews_user_reflection`). |
| `strengths_feedback` | `TEXT` | No | None | No | No | No | No | Văn bản | Nhận xét định tính phân tích các điểm mạnh học tập trong chu kỳ. |
| `bottlenecks_feedback` | `TEXT` | No | None | No | No | No | No | Văn bản | Nhận xét định tính chỉ ra điểm nghẽn và nguyên nhân trễ hạn. |
| `action_recommendations` | `TEXT` | No | None | No | No | No | No | Văn bản | Đề xuất hành động điều chỉnh lộ trình cụ thể cho chu kỳ tiếp theo. |
| `model_used` | `VARCHAR(100)` | No | `'gemini-2.5-flash'` | No | No | No | No | Chuỗi tên model | Định danh mô hình LLM đã thực hiện sinh báo cáo đánh giá (mặc định `'gemini-2.5-flash'`). |
| `generated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm AI sinh nội dung đánh giá. |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm lưu bản ghi. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm cập nhật bản ghi gần nhất (Trigger `trg_ai_reviews_updated_at`). |

---

#### 2.30. Bảng `schedule_change_logs` (Nhật ký Kiểm toán Biến động Lịch học)
* **Mục đích:** Sổ nhật ký bất biến lưu vết toàn bộ các đợt thay đổi lịch học (Domino Shift, người học dời tay, AI Replan, đồng bộ lịch ngoài, phục hồi lộ trình).
* **Ánh xạ yêu cầu:** `FR-ADAPT-001`, `BUSR-07`, `UC-13`, `UC-22`, `UC-23`, `UC-24`.

| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 | Định danh duy nhất của bản ghi nhật ký biến động lịch. |
| `roadmap_id` | `UUID` | No | None | No | `roadmaps(id)` | No | No | UUID tồn tại | Lộ trình có lịch bị thay đổi (`ON DELETE CASCADE`). |
| `schedule_id` | `UUID` | Yes | None | No | `official_schedules(id)` | No | No | UUID tồn tại | Lịch chính thức bị tác động (`ON DELETE SET NULL`). |
| `task_id` | `UUID` | Yes | None | No | `tasks(id)` | No | No | UUID tồn tại | Nhiệm vụ cụ thể bị tác động nếu dời đơn lẻ (`ON DELETE SET NULL`). |
| `trigger_type` | `VARCHAR(30)` | No | None | No | No | No | Yes | 8 trigger types | Loại sự kiện/tác nhân: `'DOMINO_SHIFT'`, `'MANUAL_PROACTIVE_EDIT'`, `'OVERDUE_RESCHEDULE'`, `'AI_REPLAN'`, `'STALLED_COMMITMENT_CONTRACT'`, `'BACKLOG_QUEUE_MOVE'`, `'POST_FAILURE_RESET'`, `'CALENDAR_SYNC'` (`chk_sched_change_logs_trigger`). |
| `disruption_category` | `VARCHAR(30)` | No | `'UNSPECIFIED'` | No | No | No | Yes | 8 loại phân loại | Phân loại gián đoạn: `'UNSPECIFIED'`, `'LEGITIMATE_HEALTH'`, `'LEGITIMATE_WORK_SCHOOL'`, `'LEGITIMATE_EXTERNAL_CALENDAR'`, `'OVERLOAD_TASK_TOO_LARGE'`, `'OVERLOAD_PREREQUISITE_GAP'`, `'PROCRASTINATION_LOW_ENERGY'`, `'PROCRASTINATION_AVOIDANCE'` (`chk_sched_change_logs_disruption`). |
| `counts_toward_budget` | `BOOLEAN` | No | `FALSE` | No | No | No | No | Boolean | Đánh dấu sự kiện dời lịch này có tính vào ngân sách dời lịch (`weekly_reschedule_used`) hay không (`FALSE` với Domino Shift). |
| `reason` | `TEXT` | Yes | None | No | No | No | No | Văn bản | Lý do thay đổi lịch trình. |
| `affected_tasks_count` | `INTEGER` | No | `1` | No | No | No | Yes | $\ge 0$ | Tổng số nhiệm vụ bị thay đổi ngày/giờ học trong đợt này (`chk_sched_change_logs_affected`). |
| `total_shifted_minutes` | `INTEGER` | No | `0` | No | No | No | Yes | $\ge 0$ | Tổng số phút học bị dịch chuyển (`chk_sched_change_logs_minutes`). |
| `diff_payload` | `JSONB` | No | `'{}'::jsonb` | No | No | No | Yes | JSON Object | Ảnh chụp chi tiết trạng thái ngày/giờ trước và sau khi dời lịch (`chk_sched_change_logs_payload`). |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm ghi nhận biến động lịch. |

---

#### 2.31. Bảng `milestone_proofs` (Bằng chứng Khảo sát Năng lực Mốc & Mistake Intelligence)
* **Mục đích:** Lưu trữ bằng chứng khảo sát năng lực (Prove Mode) khi hoàn thành mốc kiến thức, bao gồm câu hỏi truy hồi AI sinh, câu trả lời tự luận, phân loại lỗi sai (**Mistake Intelligence**: `MISSING_FOUNDATION`, `CONCEPT_MISCONCEPTION`, `PROCESS_ERROR`, `LACK_OF_PRACTICE`), điểm đánh giá độ sâu bằng chứng và phán quyết năng lực.
* **Ánh xạ yêu cầu:** `BUSR-04`, `BUSR-11`, `FR-REPORT-003`, `UC-20`, FocusFlow Learning Intelligence Harness (`Mistake Intelligence`).

| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 | Định danh duy nhất của lượt nộp bằng chứng khảo sát mốc. |
| `milestone_id` | `UUID` | No | None | No | `milestones(id)` | Yes* | No | UUID tồn tại | Mốc kiến thức được khảo sát năng lực (`ON DELETE CASCADE`, Cross-Context FK `evaluation -> planning`). |
| `roadmap_id` | `UUID` | No | None | No | `roadmaps(id)` | No | No | UUID tồn tại | Lộ trình chứa mốc kiến thức (`ON DELETE CASCADE`, Cross-Context FK `evaluation -> planning`). |
| `user_id` | `UUID` | No | None | No | `users(id)` | No | No | UUID tồn tại | Người học thực hiện khảo sát năng lực (`ON DELETE CASCADE`, Cross-Context FK `evaluation -> account`). |
| `attempt_no` | `SMALLINT` | No | `1` | No | No | Yes* | Yes | $\ge 1$ | Số thứ tự lần thử khảo sát (`chk_milestone_proofs_attempt`, `uq_milestone_proofs_attempt`). |
| `recall_exchanges_payload` | `JSONB` | No | `'[]'::jsonb` | No | No | No | Yes | JSON Array | Mảng JSON lưu danh sách đối thoại truy hồi `RecallExchange` (`chk_milestone_proofs_exchanges_json`). |
| `mistake_taxonomy_json` | `JSONB` | No | `'[]'::jsonb` | No | No | No | Yes | JSON Array | **Mistake Intelligence:** Danh sách lỗi sai được phân loại vào `MISSING_FOUNDATION`, `CONCEPT_MISCONCEPTION`, `PROCESS_ERROR`, `LACK_OF_PRACTICE` (`chk_milestone_proofs_mistake_taxonomy`). |
| `avg_self_confidence` | `NUMERIC(3,2)` | No | None | No | No | No | Yes | 1.00 đến 5.00 | Điểm tự tin trung bình của người học tự chấm qua các câu hỏi truy hồi (`chk_milestone_proofs_confidence`). |
| `ai_evidence_score` | `NUMERIC(3,2)` | No | None | No | No | No | Yes | 1.00 đến 5.00 | Điểm bằng chứng trung bình do AI thẩm định qua các câu trả lời tự luận (`chk_milestone_proofs_score`). |
| `calibration_gap` | `NUMERIC(4,2)` | Yes | Generated | No | No | No | No | -4.00 đến 4.00 | Độ lệch hiệu chỉnh nhận thức tự sinh (`GENERATED ALWAYS AS (avg_self_confidence - ai_evidence_score) STORED`). |
| `proof_verdict` | `VARCHAR(25)` | No | `'PENDING'` | No | No | No | Yes | 4 trạng thái | Phán quyết năng lực: `'PENDING'`, `'PROVEN'`, `'NEEDS_REVIEW'`, `'FLAGGED_SHALLOW'` (`chk_milestone_proofs_verdict`). |
| `feedback_summary` | `TEXT` | No | `''` | No | No | No | No | Văn bản | Nhận xét tổng hợp định tính phân tích lỗ hổng kiến thức hoặc điểm xuất sắc. |
| `corrective_task_id` | `UUID` | Yes | None | No | `tasks(id)` | No | No | UUID tồn tại | Nhiệm vụ học tập bổ trợ khắc phục lỗ hổng kiến thức (`ON DELETE SET NULL`, Cross-Context FK `evaluation -> execution`). |
| `model_used` | `VARCHAR(100)` | No | `'gemini-2.5-flash'` | No | No | No | No | Chuỗi tên model | Mô hình LLM được sử dụng để thẩm định bằng chứng (mặc định `'gemini-2.5-flash'`). |
| `evaluated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm AI hoàn thành việc chấm điểm và đưa ra phán quyết. |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm khởi tạo bản nộp bằng chứng. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm cập nhật bản ghi gần nhất (Trigger `trg_milestone_proofs_updated_at`). |

---

### PHẦN E — SHARED KERNEL: `shared_kernel` (4 BẢNG)

#### 2.32. Bảng `outbox_events` (Hàng đợi Sự kiện Giao dịch Liên Context)
* **Mục đích:** Triển khai mẫu **Transactional Outbox Pattern**, lưu sự kiện miền trong cùng giao dịch ACID với thay đổi của Aggregate Root trước khi đẩy sang **Taskiq Redis Streams**.
* **Ánh xạ yêu cầu:** `ASR-01` (Modularity), `ASR-02` (0% mất sự kiện liên Context).

| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 | Định danh duy nhất của sự kiện Outbox. |
| `aggregate_type` | `VARCHAR(100)` | No | None | No | No | No | No | Tên Aggregate Root | Loại thực thể gốc phát sinh sự kiện (ví dụ: `'User'`, `'Roadmap'`, `'StudySession'`). |
| `aggregate_id` | `UUID` | No | None | No | No | No | No | UUID thực thể gốc | Định danh của Aggregate Root phát sinh sự kiện. |
| `event_type` | `VARCHAR(120)` | No | None | No | No | No | No | Tên lớp DomainEvent | Loại sự kiện miền (ví dụ: `'StudySessionCompletedEvent'`, `'OfficialScheduleAppliedEvent'`). |
| `payload` | `JSONB` | No | None | No | No | No | Yes | JSON Object | Dữ liệu chi tiết của sự kiện miền (`chk_outbox_events_payload`). |
| `status` | `VARCHAR(20)` | No | `'PENDING'` | No | No | No | Yes | `'PENDING'`, `'PUBLISHED'`, `'FAILED'` | Trạng thái tiếp vận sự kiện sang Redis Streams (`chk_outbox_events_status`). |
| `retry_count` | `INTEGER` | No | `0` | No | No | No | Yes | $\ge 0$ | Số lần thử tiếp vận lại khi Redis gặp sự cố tạm thời (`chk_outbox_events_retry`). |
| `correlation_id` | `VARCHAR(64)` | Yes | None | No | No | No | No | Trace/Correlation ID | Mã truy vết xuyên suốt từ HTTP Request sang Taskiq Worker (`structlog`). |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm sự kiện được ghi trong giao dịch ACID. |
| `published_at` | `TIMESTAMPTZ` | Yes | None | No | No | No | Yes* | Dấu thời gian UTC | Thời điểm `OutboxRelayTask` đẩy thành công vào Redis Streams (`chk_outbox_events_published`). |

---

#### 2.33. Bảng `processed_events` (Sổ cái Chống Xử lý Trùng Sự kiện)
* **Mục đích:** Triển khai mẫu **Idempotent Consumer Pattern** cho các trình xử lý sự kiện trên **Taskiq Worker**, đảm bảo mỗi handler chỉ xử lý một `event_id` đúng một lần duy nhất.
* **Ánh xạ yêu cầu:** `ASR-01`, `ASR-02`.

| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `event_id` | `UUID` | No | None | Yes* | `outbox_events(id)` | No | No | UUID tồn tại | Định danh sự kiện Outbox đã được tiêu thụ (`ON DELETE CASCADE`). |
| `handler_name` | `VARCHAR(120)` | No | None | Yes* | No | No | No | Tên Event Handler | Tên định danh của trình xử lý sự kiện (ví dụ: `'LearnerProfileAggregatorHandler'`). |
| `processed_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm hoàn tất xử lý sự kiện thành công. |

---

#### 2.34. Bảng `workflow_runs` (Trạng thái Điều phối Workflow Bền vững — MỚI v3.2)
* **Mục đích:** Quản lý trạng thái điều phối bền vững (Durable Workflow Orchestration) cho 5 luồng nghiệp vụ trọng tâm của **FocusFlow Learning Intelligence Harness**, hỗ trợ tạm dừng chờ người dùng xác nhận (`PAUSED_WAITING_USER`) và khôi phục ngữ cảnh chính xác.
* **Ánh xạ yêu cầu:** `ASR-01`, `ASR-02`, FocusFlow Learning Intelligence Harness (`AI Execution Run`).

| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 | Định danh duy nhất của phiên chạy Workflow. |
| `user_id` | `UUID` | No | None | No | `users(id)` | No | No | UUID tồn tại | Người học khởi chạy hoặc thụ hưởng Workflow (`ON DELETE CASCADE`). |
| `goal_id` | `UUID` | Yes | None | No | `goals(id)` | No | No | UUID tồn tại hoặc `NULL` | Mục tiêu liên kết (`ON DELETE CASCADE`). |
| `roadmap_id` | `UUID` | Yes | None | No | `roadmaps(id)` | No | No | UUID tồn tại hoặc `NULL` | Lộ trình liên kết (`ON DELETE CASCADE`). |
| `workflow_type` | `VARCHAR(40)` | No | None | No | No | No | Yes | `'PLAN_CREATION'`, `'SCHEDULE_GENERATION'`, `'OVERDUE_RECOVERY'`, `'WEEKLY_REVIEW'`, `'CONTINUOUS_LEARNING'` | Loại Workflow điều phối (`chk_workflow_runs_type`). |
| `current_step` | `VARCHAR(60)` | No | None | No | No | No | No | Tên bước hiện tại | Tên bước đang thực thi hoặc đang tạm dừng chờ người học. |
| `status` | `VARCHAR(25)` | No | `'RUNNING'` | No | No | No | Yes | `'RUNNING'`, `'PAUSED_WAITING_USER'`, `'COMPLETED'`, `'FAILED'`, `'CANCELLED'` | Trạng thái vòng đời của Workflow (`chk_workflow_runs_status`). |
| `context_snapshot` | `JSONB` | No | `'{}'::jsonb` | No | No | No | Yes | JSON Object | Ảnh chụp ngữ cảnh bền vững để tiếp tục Workflow sau khi tạm dừng (`chk_workflow_runs_snapshot`). |
| `error_detail` | `TEXT` | Yes | None | No | No | No | No | Văn bản | Chi tiết lỗi nếu Workflow chuyển sang `FAILED`. |
| `started_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm bắt đầu chạy Workflow. |
| `paused_at` | `TIMESTAMPTZ` | Yes | None | No | No | No | No | Dấu thời gian UTC | Thời điểm tạm dừng tại cổng Human-in-the-Loop. |
| `completed_at` | `TIMESTAMPTZ` | Yes | None | No | No | No | No | Dấu thời gian UTC | Thời điểm hoàn tất Workflow. |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm khởi tạo bản ghi. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm cập nhật gần nhất (Trigger `trg_workflow_runs_updated_at`). |

---

#### 2.35. Bảng `workflow_step_executions` (Nhật ký Điểm dừng & Truy vết Từng Bước Workflow — MỚI v3.2)
* **Mục đích:** Ghi nhận chi tiết từng bước thực thi (step-by-step checkpoint) bên trong một `workflow_run`, liên kết trực tiếp với `ai_usage_logs` khi bước đó có gọi LLM.
* **Ánh xạ yêu cầu:** `ASR-01`, `ASR-02`, FocusFlow Learning Intelligence Harness (`Workflow Step Execution`).

| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 | Định danh duy nhất của bước thực thi Workflow. |
| `workflow_run_id` | `UUID` | No | None | No | `workflow_runs(id)` | No | No | UUID tồn tại | Phiên chạy Workflow cha (`ON DELETE CASCADE`, Intra-Context FK). |
| `step_name` | `VARCHAR(60)` | No | None | No | No | No | No | Tên định danh bước | Tên bước thực thi (ví dụ: `'INGEST_KNOWLEDGE'`, `'GENERATE_MILESTONES'`, `'SOLVE_SCHEDULE'`). |
| `step_order` | `SMALLINT` | No | None | No | No | No | Yes | $\ge 1$ | Thứ tự bước trong quy trình (`chk_workflow_steps_order`). |
| `status` | `VARCHAR(25)` | No | `'RUNNING'` | No | No | No | Yes | `'PENDING'`, `'RUNNING'`, `'WAITING_USER'`, `'COMPLETED'`, `'FAILED'`, `'SKIPPED'` | Trạng thái của bước thực thi (`chk_workflow_steps_status`). |
| `input_summary` | `JSONB` | No | `'{}'::jsonb` | No | No | No | Yes | JSON Object | Tóm tắt đầu vào của bước thực thi (`chk_workflow_steps_input_json`). |
| `output_payload` | `JSONB` | No | `'{}'::jsonb` | No | No | No | Yes | JSON Object | Kết quả đầu ra của bước thực thi (`chk_workflow_steps_output_json`). |
| `ai_usage_log_id` | `UUID` | Yes | None | No | `ai_usage_logs(id)` | No | No | UUID tồn tại hoặc `NULL` | Liên kết bản ghi kiểm toán LLM nếu bước này gọi AI (`ON DELETE SET NULL`, Cross-Context FK `shared_kernel -> account`). |
| `retry_count` | `SMALLINT` | No | `0` | No | No | No | Yes | $\ge 0$ | Số lần thử lại của bước thực thi (`chk_workflow_steps_retry`). |
| `started_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm bắt đầu bước. |
| `completed_at` | `TIMESTAMPTZ` | Yes | None | No | No | No | No | Dấu thời gian UTC | Thời điểm hoàn thành bước. |

---

## 3. Ma trận Ràng buộc Toàn vẹn Khóa ngoại & Chiến lược Xóa (Referential Actions Matrix — 35 Bảng)

### 3.1. Ma trận Phân loại Intra-Context FK vs Cross-Context FK & Hành vi `ON DELETE` (Theo Phân rã `12 / 10 / 5 / 4 / 4`)

| Bảng Nguồn (Child Table) | Bounded Context Nguồn | Cột Khóa Ngoại | Bảng Đích (Parent Table) | Bounded Context Đích | Phân loại FK | Hành vi `ON DELETE` | Mục đích Kỹ thuật & Bảo toàn Dữ liệu |
|---|---|---|---|---|---|---|---|
| `learner_profiles` | `account` | `user_id` | `users(id)` | `account` | **Intra-Context FK** | `CASCADE` | Xóa hồ sơ thói quen khi tài khoản người học bị xóa. |
| `webcal_tokens` | `account` | `user_id` | `users(id)` | `account` | **Intra-Context FK** | `CASCADE` | Xóa token đồng bộ lịch 1 chiều WebCal khi tài khoản bị xóa. |
| `calendar_connections` | `account` | `user_id` | `users(id)` | `account` | **Intra-Context FK** | `CASCADE` | Xóa kết nối đồng bộ Google/Outlook Calendar khi tài khoản bị xóa (`UC-17`). |
| `availabilities` | `account` | `user_id` | `users(id)` | `account` | **Intra-Context FK** | `CASCADE` | Xóa cấu hình thời gian rảnh khi tài khoản bị xóa. |
| `availability_slots` | `account` | `availability_id` | `availabilities(id)` | `account` | **Intra-Context FK** | `CASCADE` | Xóa toàn bộ khung giờ rảnh khi cấu hình rảnh bị xóa. |
| `ai_quotas` | `account` | `user_id` | `users(id)` | `account` | **Intra-Context FK** | `CASCADE` | Xóa hạn ngạch AI khi tài khoản bị xóa. |
| `ai_quota_reservations` | `account` | `quota_id` | `ai_quotas(id)` | `account` | **Intra-Context FK** | `CASCADE` | Xóa sổ cái giữ chỗ khi bản ghi hạn ngạch bị xóa. |
| `ai_quota_reservations` | `account` | `user_id` | `users(id)` | `account` | **Intra-Context FK** | `CASCADE` | Xóa sổ cái giữ chỗ khi tài khoản bị xóa. |
| `ai_usage_logs` | `account` | `user_id` | `users(id)` | `account` | **Intra-Context FK** | `CASCADE` | Xóa nhật ký kiểm toán AI khi tài khoản bị xóa. |
| `ai_usage_logs` | `account` | `reservation_id` | `ai_quota_reservations(id)` | `account` | **Intra-Context FK** | `SET NULL` | Giữ lại nhật ký kiểm toán AI khi bản ghi giữ chỗ hết hạn hoặc bị dọn dẹp. |
| `payment_transactions` | `account` | `user_id` | `users(id)` | `account` | **Intra-Context FK** | **`RESTRICT`** | **Bảo vệ chứng từ tài chính:** Chặn xóa cứng người dùng đã có giao dịch thanh toán. |
| `learner_memory_items` | `account` | `user_id` | `users(id)` | `account` | **Intra-Context FK** | `CASCADE` | Xóa các mục trí nhớ cấu trúc hóa khi tài khoản người học bị xóa. |
| `learner_concept_masteries` | `account` | `user_id` | `users(id)` | `account` | **Intra-Context FK** | `CASCADE` | Xóa dữ liệu thành thạo khái niệm khi tài khoản người học bị xóa. |
| `learner_concept_masteries` | `account` | `concept_id` | `learning_concepts(concept_id)` | `planning` | **Cross-Context FK** | `CASCADE` | Xóa bản ghi thành thạo nếu khái niệm gốc bị xóa khỏi Knowledge Base. |
| `goals` | `planning` | `user_id` | `users(id)` | `account` | **Cross-Context FK** | `CASCADE` | Xóa mục tiêu khi người dùng xóa tài khoản. |
| `roadmaps` | `planning` | `user_id` | `users(id)` | `account` | **Cross-Context FK** | `CASCADE` | Xóa lộ trình khi người dùng xóa tài khoản. |
| `roadmaps` | `planning` | `goal_id` | `goals(id)` | `planning` | **Intra-Context FK** | `CASCADE` | Xóa các lộ trình liên thuộc khi mục tiêu bị xóa. |
| `milestones` | `planning` | `roadmap_id` | `roadmaps(id)` | `planning` | **Intra-Context FK** | `CASCADE` | Xóa mốc kiến thức khi lộ trình bị xóa. |
| `official_schedules` | `planning` | `roadmap_id` | `roadmaps(id)` | `planning` | **Intra-Context FK** | `CASCADE` | Xóa lịch chính thức khi lộ trình bị xóa. |
| `schedule_proposals` | `planning` | `roadmap_id` | `roadmaps(id)` | `planning` | **Intra-Context FK** | `CASCADE` | Xóa đề xuất lịch khi lộ trình bị xóa. |
| `schedule_proposals` | `planning` | `user_id` | `users(id)` | `account` | **Cross-Context FK** | `CASCADE` | Xóa đề xuất lịch khi tài khoản người học bị xóa. |
| `concept_prerequisites` | `planning` | `source_concept_id` | `learning_concepts(concept_id)` | `planning` | **Intra-Context FK** | `CASCADE` | Xóa cạnh đồ thị khi khái niệm nguồn bị xóa. |
| `concept_prerequisites` | `planning` | `prerequisite_concept_id` | `learning_concepts(concept_id)` | `planning` | **Intra-Context FK** | `CASCADE` | Xóa cạnh đồ thị khi khái niệm tiên quyết bị xóa. |
| `knowledge_sources` | `planning` | `user_id` | `users(id)` | `account` | **Cross-Context FK** | `CASCADE` | Xóa nguồn tài liệu khi người học xóa tài khoản. |
| `knowledge_sources` | `planning` | `goal_id` | `goals(id)` | `planning` | **Intra-Context FK** | `CASCADE` | Xóa nguồn tài liệu khi mục tiêu học tập bị xóa. |
| `knowledge_chunks` | `planning` | `source_id` | `knowledge_sources(id)` | `planning` | **Intra-Context FK** | `CASCADE` | Xóa toàn bộ phân đoạn vector/tsvector khi tài liệu nguồn bị xóa. |
| `knowledge_chunks` | `planning` | `goal_id` | `goals(id)` | `planning` | **Intra-Context FK** | `CASCADE` | Xóa toàn bộ phân đoạn khi mục tiêu học tập bị xóa. |
| `schedule_blocks` | `planning` | `roadmap_id` | `roadmaps(id)` | `planning` | **Intra-Context FK** | `CASCADE` | Xóa khối lịch học khi lộ trình bị xóa. |
| `schedule_blocks` | `planning` | `official_schedule_id` | `official_schedules(id)` | `planning` | **Intra-Context FK** | `CASCADE` | Xóa khối lịch học khi lịch chính thức bị xóa. |
| `schedule_blocks` | `planning` | `task_id` | `tasks(id)` | `execution` | **Cross-Context FK** | `CASCADE` | Xóa khối lịch học tương ứng khi nhiệm vụ bị xóa (`planning` -> `execution`). |
| `tasks` | `execution` | `roadmap_id` | `roadmaps(id)` | `planning` | **Cross-Context FK** | `CASCADE` | Xóa nhiệm vụ khi lộ trình bị xóa (`execution` -> `planning`). |
| `tasks` | `execution` | `milestone_id` | `milestones(id)` | `planning` | **Cross-Context FK** | `CASCADE` | Xóa nhiệm vụ khi mốc kiến thức bị xóa (`execution` -> `planning`). |
| `tasks` | `execution` | `official_schedule_id` | `official_schedules(id)` | `planning` | **Cross-Context FK** | `SET NULL` | Giữ lại task nhưng ngắt liên kết lịch khi lịch chính thức được thay thế. |
| `tasks` | `execution` | `parent_task_id` | `tasks(id)` | `execution` | **Intra-Context FK** | `SET NULL` | Giữ nguyên subtask con, chỉ ngắt liên kết cha nếu task cha bị xóa. |
| `tasks` | `execution` | `concept_id` | `learning_concepts(concept_id)` | `planning` | **Cross-Context FK** | `SET NULL` | Giữ nguyên nhiệm vụ thực thi, chỉ ngắt liên kết khái niệm nếu node tri thức bị xóa. |
| `task_dependencies` | `execution` | `predecessor_id` | `tasks(id)` | `execution` | **Intra-Context FK** | `CASCADE` | Tự động dọn cạnh đồ thị khi nhiệm vụ tiên quyết bị xóa. |
| `task_dependencies` | `execution` | `successor_id` | `tasks(id)` | `execution` | **Intra-Context FK** | `CASCADE` | Tự động dọn cạnh đồ thị khi nhiệm vụ phụ thuộc bị xóa. |
| `task_dependencies` | `execution` | `roadmap_id` | `roadmaps(id)` | `planning` | **Cross-Context FK** | `CASCADE` | Dọn dẹp cạnh đồ thị khi lộ trình bị xóa. |
| `study_sessions` | `execution` | `user_id` | `users(id)` | `account` | **Cross-Context FK** | `CASCADE` | Xóa phiên học khi tài khoản người học bị xóa. |
| `study_sessions` | `execution` | `roadmap_id` | `roadmaps(id)` | `planning` | **Cross-Context FK** | `CASCADE` | Xóa phiên học khi lộ trình bị xóa. |
| `session_tasks` | `execution` | `session_id` | `study_sessions(id)` | `execution` | **Intra-Context FK** | `CASCADE` | Xóa dòng liên kết khi phiên học bị xóa. |
| `session_tasks` | `execution` | `task_id` | `tasks(id)` | `execution` | **Intra-Context FK** | **`RESTRICT`** | **Bảo vệ lịch sử học tập:** Chặn xóa cứng nhiệm vụ đã có phiên Pomodoro ghi nhận. |
| `study_notes` | `execution` | `user_id` | `users(id)` | `account` | **Cross-Context FK** | `CASCADE` | Xóa ghi chép khi tài khoản bị xóa. |
| `study_notes` | `execution` | `session_id` | `study_sessions(id)` | `execution` | **Intra-Context FK** | `CASCADE` | Xóa ghi chép gắn với phiên học khi phiên học bị xóa. |
| `study_notes` | `execution` | `task_id` | `tasks(id)` | `execution` | **Intra-Context FK** | `SET NULL` | Giữ nguyên ghi chép học tập, chỉ gỡ liên kết task nếu task bị xóa. |
| `pause_records` | `evaluation` | `roadmap_id` | `roadmaps(id)` | `planning` | **Cross-Context FK** | `CASCADE` | Xóa lịch sử tạm dừng khi lộ trình bị xóa. |
| `ai_reviews` | `evaluation` | `roadmap_id` | `roadmaps(id)` | `planning` | **Cross-Context FK** | `CASCADE` | Xóa báo cáo AI khi lộ trình bị xóa. |
| `ai_reviews` | `evaluation` | `user_id` | `users(id)` | `account` | **Cross-Context FK** | `CASCADE` | Xóa báo cáo AI khi tài khoản bị xóa. |
| `ai_reviews` | `evaluation` | `milestone_id` | `milestones(id)` | `planning` | **Cross-Context FK** | `CASCADE` | Xóa báo cáo mốc khi mốc kiến thức bị xóa. |
| `schedule_change_logs` | `evaluation` | `roadmap_id` | `roadmaps(id)` | `planning` | **Cross-Context FK** | `CASCADE` | Xóa nhật ký biến động lịch khi lộ trình bị xóa. |
| `schedule_change_logs` | `evaluation` | `schedule_id` | `official_schedules(id)` | `planning` | **Cross-Context FK** | `SET NULL` | Giữ nguyên nhật ký kiểm toán ngay cả khi lịch chính thức được tạo mới. |
| `schedule_change_logs` | `evaluation` | `task_id` | `tasks(id)` | `execution` | **Cross-Context FK** | `SET NULL` | Giữ nguyên nhật ký kiểm toán nếu nhiệm vụ chưa học bị xóa. |
| `milestone_proofs` | `evaluation` | `milestone_id` | `milestones(id)` | `planning` | **Cross-Context FK** | `CASCADE` | Xóa bằng chứng khảo sát khi mốc kiến thức bị xóa. |
| `milestone_proofs` | `evaluation` | `roadmap_id` | `roadmaps(id)` | `planning` | **Cross-Context FK** | `CASCADE` | Xóa bằng chứng khảo sát khi lộ trình bị xóa. |
| `milestone_proofs` | `evaluation` | `user_id` | `users(id)` | `account` | **Cross-Context FK** | `CASCADE` | Xóa bằng chứng khảo sát khi người học xóa tài khoản. |
| `milestone_proofs` | `evaluation` | `corrective_task_id` | `tasks(id)` | `execution` | **Cross-Context FK** | `SET NULL` | Giữ lại bằng chứng khảo sát khi nhiệm vụ bổ trợ bị xóa. |
| `processed_events` | `shared_kernel` | `event_id` | `outbox_events(id)` | `shared_kernel` | **Intra-Context FK** | `CASCADE` | Dọn dẹp bản ghi chống lặp khi sự kiện Outbox cũ được lưu trữ/xóa. |
| `workflow_runs` | `shared_kernel` | `user_id` | `users(id)` | `account` | **Cross-Context FK** | `CASCADE` | Xóa lịch sử chạy Workflow khi tài khoản người dùng bị xóa. |
| `workflow_runs` | `shared_kernel` | `goal_id` | `goals(id)` | `planning` | **Cross-Context FK** | `CASCADE` | Xóa phiên chạy Workflow gắn với mục tiêu khi mục tiêu bị xóa. |
| `workflow_runs` | `shared_kernel` | `roadmap_id` | `roadmaps(id)` | `planning` | **Cross-Context FK** | `CASCADE` | Xóa phiên chạy Workflow gắn với lộ trình khi lộ trình bị xóa. |
| `workflow_step_executions` | `shared_kernel` | `workflow_run_id` | `workflow_runs(id)` | `shared_kernel` | **Intra-Context FK** | `CASCADE` | Xóa các bước thực thi khi phiên chạy Workflow cha bị xóa. |
| `workflow_step_executions` | `shared_kernel` | `ai_usage_log_id` | `ai_usage_logs(id)` | `account` | **Cross-Context FK** | `SET NULL` | Giữ nguyên vết bước thực thi nếu nhật ký AI cũ được dọn dẹp. |

---

## 4. Ma trận Chỉ mục Hiệu năng & Ràng buộc Đồng thời (Indexes Matrix — 74 Chỉ mục)

| Tên Chỉ mục (Index Name) | Bảng Áp dụng | Các Cột Chỉ mục | Loại Index | Điều kiện (WHERE Clause / Partial) | Mục đích Kỹ thuật & Nghiệp vụ |
|---|---|---|---|---|---|
| `uq_users_lower_email` | `users` | `(LOWER(email))` | B-Tree Unique | Không | Chống trùng email không phân biệt hoa thường (`FR-AUTH-001`). |
| `uq_availability_slots_active_time` | `availability_slots` | `(availability_id, day_of_week, start_time)` | B-Tree Unique Partial | `WHERE is_active = TRUE` | Chống trùng lặp/chồng lấn khung giờ rảnh hoạt động trong cùng một cấu hình rảnh. |
| `uq_study_sessions_user_active` | `study_sessions` | `(user_id)` | B-Tree Unique Partial | `WHERE status = 'IN_PROGRESS'` | **Bất biến đồng thời:** Một user tại một thời điểm chỉ có tối đa 1 phiên học đang chạy (`OS-01`). |
| `uq_study_notes_takeaway` | `study_notes` | `(session_id, task_id)` | B-Tree Unique Partial | `WHERE note_type = 'TAKEAWAY'` | **Bất biến phiên học:** Mỗi cặp phiên học và nhiệm vụ chỉ có tối đa 1 ghi chép đúc kết Takeaway (`DEC-02`). |
| `uq_schedule_proposals_roadmap_draft` | `schedule_proposals` | `(roadmap_id)` | B-Tree Unique Partial | `WHERE status = 'DRAFT'` | **Bất biến đề xuất:** Mỗi lộ trình tại một thời điểm chỉ có tối đa 1 bản nháp đề xuất chưa duyệt. |
| `uq_ai_reviews_weekly` | `ai_reviews` | `(roadmap_id, period_start, period_end)` | B-Tree Unique Partial | `WHERE review_cycle = 'WEEKLY'` | Chống sinh trùng báo cáo tuần khi Taskiq Worker Retry (Idempotency). |
| `uq_ai_reviews_milestone` | `ai_reviews` | `(roadmap_id, milestone_id)` | B-Tree Unique Partial | `WHERE review_cycle = 'MILESTONE'` | Chống sinh trùng báo cáo mốc khi Taskiq Worker Retry (Idempotency). |
| `idx_quota_reservations_cleanup` | `ai_quota_reservations` | `(expires_at)` | B-Tree Partial | `WHERE status = 'RESERVED'` | Taskiq `QuotaSweeper` quét và thu hồi nhanh các giữ chỗ AI bị treo quá hạn (`ASR-02`). |
| `idx_quota_reservations_user_status` | `ai_quota_reservations` | `(user_id, status, created_at DESC)` | B-Tree | Không | Tra cứu lịch sử giữ chỗ hạn ngạch AI theo người dùng. |
| `idx_payment_transactions_user_created` | `payment_transactions` | `(user_id, created_at DESC)` | B-Tree | Không | Truy vấn lịch sử thanh toán nâng cấp gói cước của người học (`UC-04`, `UC-27`). |
| `idx_payment_transactions_status` | `payment_transactions` | `(status, created_at DESC)` | B-Tree | Không | Đối soát và thống kê doanh thu theo trạng thái giao dịch (`UC-27`). |
| `idx_payment_transactions_pending_expires` | `payment_transactions` | `(expires_at)` | B-Tree Partial | `WHERE status = 'PENDING'` | Taskiq Sweeper quét định kỳ các giao dịch thanh toán chờ quá hạn để cập nhật trạng thái `EXPIRED` (`ASR-06`). |
| `idx_study_sessions_user_started` | `study_sessions` | `(user_id, started_at DESC)` | B-Tree | Không | Tối ưu hóa truy vấn lịch sử học tập & biểu đồ Dashboard của người dùng. |
| `idx_study_sessions_roadmap_started` | `study_sessions` | `(roadmap_id, started_at DESC)` | B-Tree | Không | Thống kê số giờ học thực tế theo lộ trình. |
| `idx_study_sessions_heartbeat` | `study_sessions` | `(last_heartbeat_at)` | B-Tree Partial | `WHERE status = 'IN_PROGRESS'` | Taskiq `AbandonedSessionSweeper` quét định kỳ phát hiện phiên mất kết nối quá 5 phút (`OS-07`). |
| `idx_roadmaps_user_status` | `roadmaps` | `(user_id, status)` | B-Tree | Không | Lọc nhanh danh sách lộ trình của người học theo trạng thái (`ACTIVE`, `PAUSED`). |
| `idx_roadmaps_goal_id` | `roadmaps` | `(goal_id)` | B-Tree | Không | Tối ưu hóa truy vấn các lộ trình thuộc một mục tiêu cụ thể. |
| `idx_tasks_roadmap_scheduled_date` | `tasks` | `(roadmap_id, scheduled_date)` | B-Tree | Không | Truy vấn danh sách nhiệm vụ của lộ trình theo từng ngày học. |
| `idx_tasks_scheduled_start` | `tasks` | `(scheduled_start)` | B-Tree Partial | `WHERE scheduled_start IS NOT NULL` | Tối ưu hóa Calendar View và feed xuất lịch iCal/WebCal. |
| `idx_tasks_overdue` | `tasks` | `(scheduled_date)` | B-Tree Partial | `WHERE status IN ('TODO', 'IN_PROGRESS') AND scheduled_date IS NOT NULL` | **Phát hiện nhiệm vụ quá hạn tất định:** Truy vấn nhanh các task trễ hạn cần cảnh báo (`BUSR-06`). |
| `idx_tasks_milestone_id` | `tasks` | `(milestone_id)` | B-Tree | Không | Lấy toàn bộ nhiệm vụ của một mốc kiến thức cụ thể. |
| `idx_tasks_official_schedule_id` | `tasks` | `(official_schedule_id)` | B-Tree | Không | Tối ưu hóa tra cứu task thuộc lịch chính thức và dọn dẹp khóa ngoại. |
| `idx_task_deps_successor` | `task_dependencies` | `(successor_id)` | B-Tree | Không | Kiểm tra điều kiện tiên quyết khi người học bấm Start Session. |
| `idx_task_deps_predecessor` | `task_dependencies` | `(predecessor_id)` | B-Tree | Không | Mở khóa các task phía sau khi task trước hoàn thành. |
| `idx_task_deps_roadmap` | `task_dependencies` | `(roadmap_id)` | B-Tree | Không | Truy vấn toàn bộ đồ thị DAG của lộ trình để dựng giao diện và kiểm tra chu trình. |
| `idx_session_tasks_task_id` | `session_tasks` | `(task_id)` | B-Tree | Không | Tra cứu lịch sử phiên học của một nhiệm vụ; bảo vệ khóa ngoại `RESTRICT`. |
| `idx_session_tasks_session_id` | `session_tasks` | `(session_id)` | B-Tree | Không | Lấy toàn bộ nhiệm vụ thực hiện trong một phiên học cụ thể. |
| `idx_ai_usage_logs_user_action` | `ai_usage_logs` | `(user_id, action_type, created_at DESC)` | B-Tree | Không | Thống kê số lượng gọi AI và chi phí token theo từng loại nghiệp vụ. |
| `idx_avail_slots_availability_day` | `availability_slots` | `(availability_id, day_of_week)` | B-Tree | Không | `HybridAvailabilityRuleEngine` nạp khung giờ rảnh của người học theo từng ngày trong tuần. |
| `idx_goals_user_id` | `goals` | `(user_id)` | B-Tree | Không | Lấy danh sách mục tiêu học tập của người dùng. |
| `idx_schedule_proposals_roadmap_status` | `schedule_proposals` | `(roadmap_id, status)` | B-Tree | Không | Lọc đề xuất lịch theo trạng thái để thực hiện phê duyệt (Strict Apply). |
| `idx_schedule_proposals_user_id` | `schedule_proposals` | `(user_id)` | B-Tree | Không | Bảo vệ khóa ngoại và tra cứu đề xuất của người dùng. |
| `idx_pause_records_roadmap_id` | `pause_records` | `(roadmap_id)` | B-Tree | Không | Lấy lịch sử tạm dừng và số ngày tịnh tiến của lộ trình. |
| `idx_ai_reviews_roadmap_cycle` | `ai_reviews` | `(roadmap_id, review_cycle, generated_at DESC)` | B-Tree | Không | Tải báo cáo AI gần nhất của lộ trình theo chu kỳ tuần hoặc mốc. |
| `idx_ai_reviews_user_id` | `ai_reviews` | `(user_id)` | B-Tree | Không | Lấy toàn bộ báo cáo AI của người dùng. |
| `idx_study_notes_user_session` | `study_notes` | `(user_id, session_id)` | B-Tree | Không | Tải bản nháp Scratchpad và đúc kết Takeaways trong phiên học. |
| `idx_study_notes_task_id` | `study_notes` | `(task_id)` | B-Tree | Không | Tra cứu ghi chú đính kèm theo nhiệm vụ cụ thể. |
| `idx_sched_change_logs_roadmap_created` | `schedule_change_logs` | `(roadmap_id, created_at DESC)` | B-Tree | Không | Truy vấn dòng thời gian lịch sử biến động lịch học của một lộ trình. |
| `idx_sched_change_logs_trigger` | `schedule_change_logs` | `(trigger_type, created_at DESC)` | B-Tree | Không | Thống kê tần suất biến động lịch theo nguyên nhân (`DOMINO_SHIFT`, `AI_REPLAN`, v.v.). |
| `idx_outbox_events_pending` | `outbox_events` | `(created_at ASC)` | B-Tree Partial | `WHERE status = 'PENDING'` | Taskiq `OutboxRelayTask` quét nhanh các sự kiện chờ phát sang Redis Streams (`ASR-02`). |
| `idx_outbox_events_aggregate` | `outbox_events` | `(aggregate_type, aggregate_id)` | B-Tree | Không | Tra cứu nhanh lịch sử sự kiện theo Aggregate Root. |
| `idx_learning_concepts_domain_level` | `learning_concepts` | `(domain, difficulty_level, verification_status)` | B-Tree | Không | Tra cứu cây khái niệm tri thức theo lĩnh vực, độ khó và trạng thái thẩm định. |
| `idx_concept_prerequisites_source` | `concept_prerequisites` | `(source_concept_id)` | B-Tree | Không | Kiểm tra điều kiện tiên quyết giữa các khái niệm tri thức. |
| `idx_concept_prerequisites_prereq` | `concept_prerequisites` | `(prerequisite_concept_id)` | B-Tree | Không | Tìm các khái niệm phụ thuộc khi một khái niệm được xác minh. |
| `idx_calendar_connections_user_status` | `calendar_connections` | `(user_id, sync_status)` | B-Tree | Không | Lọc kết nối Google/Outlook Calendar đang hoạt động của người học để đồng bộ 2 chiều (`UC-17`). |
| `idx_tasks_parent_task_id` | `tasks` | `(parent_task_id)` | B-Tree Partial | `WHERE parent_task_id IS NOT NULL` | Tối ưu hóa truy vấn cây nhiệm vụ cha - con (Subtask hierarchy, `FR-EXEC-005`). |
| `idx_tasks_concept_id` | `tasks` | `(concept_id)` | B-Tree Partial | `WHERE concept_id IS NOT NULL` | Liên kết và tổng hợp tiến độ hoàn thành các khái niệm tri thức. |
| `idx_tasks_backlog_queue` | `tasks` | `(roadmap_id, milestone_id, reschedule_count DESC)` | B-Tree Partial | `WHERE scheduled_date IS NULL AND status IN ('TODO', 'IN_PROGRESS')` | Ưu tiên xếp lịch các task trôi dạt vào hàng đợi sắp tới dựa trên số lần bị hoãn (`BUSR-06`). |
| `idx_roadmaps_dormant_scan` | `roadmaps` | `(status, last_study_activity_at)` | B-Tree Partial | `WHERE status = 'ACTIVE'` | Taskiq Sweeper quét nhanh các lộ trình bị bỏ quên $\ge 7$ ngày để kích hoạt quy trình Phục hồi Ngủ đông (`UC-24`, `UC-25`). |
| `idx_study_sessions_pending_takeaway` | `study_sessions` | `(user_id, ended_at DESC)` | B-Tree Partial | `WHERE pending_takeaway = TRUE` | Chặn mở phiên mới khi người học nợ đúc kết Takeaways của phiên trước (`BUSR-04`). |
| `idx_milestone_proofs_milestone` | `milestone_proofs` | `(milestone_id, attempt_no DESC)` | B-Tree | Không | Tra cứu lịch sử các lượt nộp bài khảo sát năng lực của một mốc học tập. |
| `idx_milestone_proofs_user_verdict` | `milestone_proofs` | `(user_id, proof_verdict, evaluated_at DESC)` | B-Tree | Không | Thống kê kết quả thẩm định năng lực Prove Mode của người học. |
| `idx_learner_memory_items_user_cat` | `learner_memory_items` | `(user_id, memory_category, confirmation_status)` | B-Tree | Không | Truy vấn nhanh các nhận định trí nhớ người học theo danh mục và trạng thái xác nhận. |
| `idx_learner_concept_masteries_user_review` | `learner_concept_masteries` | `(user_id, next_review_at)` | B-Tree Partial | `WHERE next_review_at IS NOT NULL` | Quét nhanh các khái niệm đến hạn cần ôn tập lặp lại ngắt quãng của người học. |
| `idx_learner_concept_masteries_concept` | `learner_concept_masteries` | `(concept_id)` | B-Tree | Không | Tra cứu và bảo vệ khóa ngoại theo mã khái niệm `concept_id`. |
| `idx_knowledge_sources_goal_status` | `knowledge_sources` | `(goal_id, ingestion_status)` | B-Tree | Không | Kiểm tra trạng thái bóc tách tài liệu học tập của một mục tiêu. |
| `idx_knowledge_sources_user_created` | `knowledge_sources` | `(user_id, created_at DESC)` | B-Tree | Không | Liệt kê danh sách tài liệu học tập người học đã tải lên. |
| `idx_knowledge_chunks_goal_id` | `knowledge_chunks` | `(goal_id)` | B-Tree | Không | Lọc phạm vi các phân đoạn tri thức thuộc mục tiêu học tập hiện tại trước khi truy xuất RAG. |
| `idx_knowledge_chunks_search_vector` | `knowledge_chunks` | `(search_vector)` | **GIN** | Không | Tìm kiếm toàn văn bản tốc độ cao theo từ khóa chuyên ngành (Hybrid RAG Lexical Search). |
| `idx_knowledge_chunks_embedding_hnsw` | `knowledge_chunks` | `(embedding vector_cosine_ops)` | **HNSW (`pgvector`)** | Không | Tìm kiếm láng giềng gần nhất theo độ tương đồng Cosine trên vector 768 chiều (Hybrid RAG Semantic Search). |
| `idx_schedule_blocks_roadmap_date` | `schedule_blocks` | `(roadmap_id, block_date, start_time)` | B-Tree | Không | Hiển thị lịch học theo ngày/tuần trên giao diện Calendar View. |
| `idx_schedule_blocks_schedule_id` | `schedule_blocks` | `(official_schedule_id)` | B-Tree | Không | Truy vấn toàn bộ khối lịch thuộc phiên bản lịch chính thức hiện tại. |
| `idx_schedule_blocks_task_id` | `schedule_blocks` | `(task_id)` | B-Tree Partial | `WHERE task_id IS NOT NULL` | Lấy danh sách các khối lịch đã phân bổ cho một nhiệm vụ học tập cụ thể. |
| `idx_schedule_blocks_external_event` | `schedule_blocks` | `(external_calendar_event_id)` | B-Tree Partial | `WHERE external_calendar_event_id IS NOT NULL` | Đối soát nhanh sự kiện đồng bộ 2 chiều với Google/Outlook Calendar. |
| `idx_workflow_runs_user_status` | `workflow_runs` | `(user_id, status, updated_at DESC)` | B-Tree | Không | Truy vấn các phiên chạy Workflow đang hoạt động hoặc tạm dừng chờ người học (`PAUSED_WAITING_USER`). |
| `idx_workflow_runs_roadmap_type` | `workflow_runs` | `(roadmap_id, workflow_type)` | B-Tree Partial | `WHERE roadmap_id IS NOT NULL` | Kiểm tra tiến trình Workflow theo lộ trình và loại luồng điều phối. |
| `idx_workflow_step_executions_run_order` | `workflow_step_executions` | `(workflow_run_id, step_order)` | B-Tree | Không | Truy xuất tuần tự lịch sử từng bước thực thi (checkpoint trace) của một Workflow. |
| `idx_ai_quota_reservations_quota_id` | `ai_quota_reservations` | `(quota_id)` | B-Tree | Không | Tối ưu hóa hiệu năng CASCADE DELETE và kiểm tra hạn ngạch giữ chỗ theo `quota_id`. |
| `idx_sched_change_logs_schedule_id` | `schedule_change_logs` | `(schedule_id)` | B-Tree Partial | `WHERE schedule_id IS NOT NULL` | Tối ưu hóa hiệu năng tra cứu và cascade SET NULL theo phiên bản lịch chính thức. |
| `idx_sched_change_logs_task_id` | `schedule_change_logs` | `(task_id)` | B-Tree Partial | `WHERE task_id IS NOT NULL` | Tối ưu hóa tra cứu lịch sử biến động dời lịch của một bài học cụ thể. |
| `idx_milestone_proofs_roadmap_id` | `milestone_proofs` | `(roadmap_id)` | B-Tree | Không | Tối ưu hóa truy vấn lịch sử kiểm chứng Prove Mode theo lộ trình và CASCADE DELETE. |
| `idx_milestone_proofs_corrective_task_id` | `milestone_proofs` | `(corrective_task_id)` | B-Tree Partial | `WHERE corrective_task_id IS NOT NULL` | Tra cứu và bảo vệ khóa ngoại tới bài học bổ trợ được chỉ định sau kiểm chứng. |
| `idx_workflow_runs_goal_id` | `workflow_runs` | `(goal_id)` | B-Tree Partial | `WHERE goal_id IS NOT NULL` | Truy vấn các luồng workflow phân tán gắn với một mục tiêu học tập cụ thể. |
| `idx_workflow_step_executions_ai_log_id` | `workflow_step_executions` | `(ai_usage_log_id)` | B-Tree Partial | `WHERE ai_usage_log_id IS NOT NULL` | Tra cứu liên kết giữa bước thực thi workflow và bản ghi kiểm toán cuộc gọi LLM. |
