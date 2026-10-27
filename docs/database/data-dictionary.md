# FocusFlow — Từ điển Dữ liệu, Ma trận Ràng buộc & Ma trận Chỉ mục (Database Schema Governance)

## Thông tin Hồ sơ Kỹ thuật
* **Dự án:** FocusFlow — Hệ thống hỗ trợ lập kế hoạch và thực thi lộ trình tự học thích ứng tích hợp AI
* **Phiên bản:** v3.0 — Chuẩn Quản trị Lược đồ Cơ sở Dữ liệu Đầy đủ 24 Bảng (24 Physical Tables Schema Governance Baseline — 4 Bounded Contexts + Shared Kernel)
* **Hệ quản trị CSDL:** PostgreSQL 16+
* **Tiêu chuẩn kỹ thuật:** ISO/IEC 9075:2023 (SQL Standard), ISO/IEC/IEEE 29148:2018 (Requirements Engineering)
* **Căn cứ đánh giá học thuật:** Khung Rubric Đồ án Tốt nghiệp CNTT — Tiêu chí TC2.1 & TC2.3 (Mức 5)
* **Tài liệu nguồn chân lý liên kết:**
  * Tập lệnh DDL: [`docs/database/schema.sql`](file:///Users/vuthang/Documents/FocusFlow/docs/database/schema.sql)
  * Thiết kế CSDL Chi tiết: [`docs/database/database-schema-design.md`](file:///Users/vuthang/Documents/FocusFlow/docs/database/database-schema-design.md)
  * Đặc tả Yêu cầu SRS v1.2: [`docs/srs/srs-v1.0.md`](file:///Users/vuthang/Documents/FocusFlow/docs/srs/srs-v1.0.md)
  * Sơ đồ Lớp UML v5.0: [`docs/uml/class-diagrams/class_diagram.drawio`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/class-diagrams/class_diagram.drawio) \| [`docs/uml/class-diagrams.md`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/class-diagrams.md)
  * Sơ đồ CSDL DBML: [`docs/database/schema.dbml`](file:///Users/vuthang/Documents/FocusFlow/docs/database/schema.dbml)

---

## 1. Nguyên tắc Cốt lõi & Quy ước Định danh Toàn hệ thống

> [!IMPORTANT]
> **16 Quyết định Kiến trúc & Quy chuẩn Cơ sở Dữ liệu FocusFlow v3.0 (24 Bảng):**
> 1. **Hệ quản trị CSDL:** PostgreSQL 16 vận hành tối ưu hóa trên container Docker Compose, kết nối qua `SQLAlchemy 2.0 Async + asyncpg`.
> 2. **Chiến lược Khóa chính:** UUIDv7 (RFC 9562, 128-bit Time-Ordered Monotonic) sinh tại tầng Backend FastAPI (`uuid_utils`/`uuid6`), Fallback tại CSDL `DEFAULT gen_random_uuid()` loại bỏ phân mảnh B-Tree và chống tấn công đoán ID (riêng `processed_events` dùng khóa chính kép `(event_id, handler_name)`).
> 3. **Phân rã theo 4 Bounded Contexts + Shared Kernel (`9 / 5 / 5 / 3 / 2`):**
>    - **`account` (9 bảng):** `users`, `learner_profiles`, `webcal_tokens`, `availabilities`, `availability_slots`, `ai_quotas`, `ai_quota_reservations`, `ai_usage_logs`, `payment_transactions`.
>    - **`planning` (5 bảng):** `goals`, `roadmaps`, `milestones`, `official_schedules`, `schedule_proposals`.
>    - **`execution` (5 bảng):** `tasks`, `task_dependencies`, `study_sessions`, `session_tasks`, `study_notes`.
>    - **`evaluation` (3 bảng):** `pause_records`, `ai_reviews`, `schedule_change_logs`.
>    - **`shared_kernel` (2 bảng):** `outbox_events`, `processed_events`.
> 4. **Quy tắc Modular Monolith:** Giữ nguyên Foreign Key vật lý ở tầng PostgreSQL 16 để đảm bảo toàn vẹn dữ liệu 3NF/BCNF, nhưng cấm ORM JOIN chéo Bounded Context trong mã nguồn (chỉ giao tiếp qua `public_api.py` và `outbox_events`).
> 5. **Cô lập Đa người dùng (Multi-tenant):** Sử dụng Single Surrogate FK chuẩn, `user_id` hiện diện tại các bảng gốc, kiểm soát ủy quyền sở hữu tại Application Service Layer.
> 6. **Quản trị AI Quota 2 Pha ACID:** Tách biệt `ai_quotas` (hạn ngạch hiện tại kèm `reserved_calls`), `ai_quota_reservations` (sổ cái giữ chỗ 2 pha `RESERVED -> COMMITTED/RELEASED/EXPIRED` với TTL **120s (2 phút)**), và `ai_usage_logs` (nhật ký kiểm toán chi tiết).
> 7. **Thanh toán Đa Cổng (`PaymentGatewayPort`):** Bảng `payment_transactions` lưu trữ giao dịch nâng cấp gói `PREMIUM` qua PayOS, VNPay Sandbox hoặc `MOCK`, xác thực chữ ký số `HMAC-SHA256`.
> 8. **Thời gian rảnh Chuẩn hóa 100% 3NF:** Bảng cha `availabilities` và bảng con `availability_slots` (`day_of_week` 0–6, `start_time`, `end_time`, `end_day_offset`, `slot_type`, `is_active`) ánh xạ trực tiếp sang Value Objects `WeeklySchedule` & `TimeSlot`.
> 9. **Quản lý Lịch & Tiên quyết DAG:** Lên lịch trực tiếp trên bảng `tasks` (`scheduled_date`, `scheduled_start`, `scheduled_end`, `official_schedule_id`); đồ thị tiên quyết `task_dependencies` kiểm định không chu trình bởi `DagCycleValidator` (thuộc Context `execution`).
> 10. **Đề xuất Lịch 3-Tier Validation Gate:** Bảng `schedule_proposals` lưu `proposal_data` `JSONB` xem trước, chỉ lưu sau khi vượt qua cổng kiểm định 3 tầng và không tự động ghi đè lịch chính thức.
> 11. **Phiên học Pomodoro & Heartbeat 60s:** Quan hệ Nhiều - Nhiều nội bộ `execution` qua `session_tasks`; `study_sessions` duy trì `last_heartbeat_at` mỗi 60s và được quét tự động bởi **Taskiq Scheduler**.
> 12. **Tạm dừng, Domino Shift & Kiểm toán Biến động Lịch:** Bảng `pause_records` ghi nhận khoảng nghỉ và bảng `schedule_change_logs` lưu vết kiểm toán bất biến mọi biến động lịch (`DOMINO_SHIFT`, `MANUAL_EDIT`, `AI_REPLAN`, `CALENDAR_SYNC`) (thuộc Context `evaluation`).
> 13. **Transactional Outbox & Idempotent Consumer:** Bảng `outbox_events` và `processed_events` đảm bảo 0% mất sự kiện và 0% xử lý trùng lặp trên **Taskiq Worker (Redis Streams)**.
> 14. **Chiến lược Xóa Lai (Hybrid Deletion):** `CASCADE` cho các nhánh phụ thuộc vòng đời; `ON DELETE RESTRICT` trên `session_tasks.task_id` và `payment_transactions.user_id` bảo vệ lịch sử học tập và chứng từ tài chính.
> 15. **Trạng thái & Enum:** `VARCHAR` kết hợp ràng buộc `CHECK (... IN (...))` thân thiện với Alembic migration, tránh khóa bảng.
> 16. **Quản lý Thời gian:** `TIMESTAMPTZ` (UTC) cho mọi mốc thời gian; `timezone` mặc định `'Asia/Ho_Chi_Minh'` trong bảng `users`; hàm trigger `fn_set_updated_at()` tự động cập nhật `updated_at` trên cả 18 bảng có cột `updated_at`.

---

## 2. Từ điển Dữ liệu Toàn diện (Data Dictionary - 24 Bảng Vật lý)

---

### PHẦN A — BOUNDED CONTEXT 1: `account` (9 BẢNG)

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
| `is_locked` | `BOOLEAN` | No | `FALSE` | No | No | No | No | `TRUE`, `FALSE` | Cờ khóa tài khoản bởi Admin (`UC-18`); nếu `TRUE` thì chặn đăng nhập (`UC-02`). |
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

#### 2.3. Bảng `webcal_tokens` (Bảo mật Đồng bộ Lịch WebCal & OAuth Sync Metadata)
* **Mục đích:** Lưu trữ bản băm SHA-256 của token đồng bộ lịch 1 chiều (`.ics`) và thông tin kết nối OAuth2 lịch 2 chiều được mã hóa Fernet.
* **Ánh xạ yêu cầu:** `FR-CALENDAR-002`, `FR-CALENDAR-003`, `BUSR-08`, `OS-05`.

| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 | Định danh bản ghi token. |
| `user_id` | `UUID` | No | None | No | `users(id)` | Yes | No | UUID tồn tại | Quan hệ 1:1 với người dùng (`ON DELETE CASCADE`). |
| `token_hash` | `VARCHAR(64)` | No | None | No | No | Yes | Yes* | 64 ký tự Hex | Bản băm SHA-256 của CSPRN 32-byte hex; không lưu token thô (`chk_webcal_tokens_hash`). |
| `oauth_refresh_token_encrypted` | `TEXT` | Yes | None | No | No | No | No | Chuỗi mã hóa Fernet | Refresh token Google Calendar OAuth2 đã mã hóa đối xứng Fernet (nếu bật đồng bộ 2 chiều). |
| `external_calendar_id` | `VARCHAR(255)` | Yes | None | No | No | No | No | Chuỗi ID lịch | Định danh lịch ngoại vi đích khi đồng bộ OAuth2. |
| `is_active` | `BOOLEAN` | No | `TRUE` | No | No | No | No | `TRUE`, `FALSE` | Trạng thái hiệu lực; chuyển sang `FALSE` khi người học thu hồi token. |
| `last_used_at` | `TIMESTAMPTZ` | Yes | None | No | No | No | No | Dấu thời gian UTC | Thời điểm ứng dụng lịch ngoại vi đồng bộ feed gần nhất. |
| `rotated_at` | `TIMESTAMPTZ` | Yes | None | No | No | No | No | Dấu thời gian UTC | Thời điểm xoay vòng/làm mới token gần nhất (`FR-CALENDAR-003`). |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm khởi tạo token lần đầu. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm cập nhật gần nhất (Trigger `trg_webcal_tokens_updated_at`). |

*\*Ràng buộc regex:* `CONSTRAINT chk_webcal_tokens_hash CHECK (token_hash ~ '^[0-9a-f]{64}$')`.

---

#### 2.4. Bảng `availabilities` (Cấu hình Quỹ Thời gian Rảnh Tổng thể)
* **Mục đích:** Cấu hình thời gian rảnh gốc của người dùng (Mode A quỹ giờ/ngày hoặc Mode B khung giờ cố định).
* **Ánh xạ yêu cầu:** `FR-AVAIL-001..002`, `BUSR-03..04`, `OS-06`.

| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 | Khóa chính cấu hình. |
| `user_id` | `UUID` | No | None | No | `users(id)` | Yes | No | UUID tồn tại | Quan hệ 1:1 với người học (`ON DELETE CASCADE`). |
| `mode` | `VARCHAR(20)` | No | `'MODE_A'` | No | No | No | Yes | `'MODE_A'`, `'MODE_B'` | Phân loại chế độ rảnh (Mode A: Quỹ giờ, Mode B: Khung giờ). |
| `calendar_integration_mode` | `VARCHAR(20)` | No | `'NONE'` | No | No | No | Yes | `'NONE'`, `'EXPORT_ICS'`, `'CONNECTED'` | Trạng thái tích hợp lịch ngoài. |
| `daily_quotas` | `JSONB` | No | `'{}'::jsonb` | No | No | No | No | Map thứ -> số giờ (0.5–14.0h) | Hạn mức giờ học mỗi ngày trong tuần cho chế độ `MODE_A` (ánh xạ sang `WeeklySchedule.dailyQuotas`). |
| `min_session_minutes` | `INTEGER` | No | `30` | No | No | No | Yes | 15 đến 120 phút | Thời lượng phiên học tối thiểu khả thi (`chk_availabilities_min_session`). |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm khởi tạo cấu hình. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm cập nhật cấu hình gần nhất (Trigger `trg_availabilities_updated_at`). |

---

#### 2.5. Bảng `availability_slots` (Khung Giờ Rảnh Chi tiết - Chuẩn hóa 100% 3NF)
* **Mục đích:** Lưu trữ chuẩn hóa từng khung giờ rảnh trong tuần, ánh xạ trực tiếp sang Value Objects `WeeklySchedule` & `TimeSlot` tại tầng Repository.
* **Ánh xạ yêu cầu:** `FR-AVAIL-002`, `BUSR-03`, `BUSR-04`.

| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 | Khóa chính khung giờ rảnh. |
| `availability_id` | `UUID` | No | None | No | `availabilities(id)` | No | No | UUID tồn tại | Khóa ngoại trỏ về cấu hình rảnh cha (`ON DELETE CASCADE`). |
| `day_of_week` | `SMALLINT` | No | None | No | No | No | Yes | 0 đến 6 | Ngày trong tuần (0: Chủ Nhật / Thứ Hai tùy quy ước, `chk_avail_slots_day`). |
| `start_time` | `TIME` | No | None | No | No | No | No | HH:MM:SS | Giờ bắt đầu khung thời gian rảnh. |
| `end_time` | `TIME` | No | None | No | No | No | Yes* | HH:MM:SS | Giờ kết thúc khung thời gian rảnh. |
| `end_day_offset` | `SMALLINT` | No | `0` | No | No | No | Yes | `0`, `1` | Độ lệch ngày kết thúc (`0`: cùng ngày, `1`: vắt qua nửa đêm sang ngày hôm sau). |
| `slot_type` | `VARCHAR(20)` | No | `'ALLOWED'` | No | No | No | Yes | `'ALLOWED'`, `'FIXED'` | Phân biệt khung giờ cho phép (`allowedWindows`) và khung giờ cố định (`fixedSlots`). |
| `is_active` | `BOOLEAN` | No | `TRUE` | No | No | No | No | `TRUE`, `FALSE` | Trạng thái bật/tắt của khung giờ rảnh này. |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm thêm khung giờ. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm sửa đổi khung giờ gần nhất (Trigger `trg_availability_slots_updated_at`). |

*\*Ràng buộc thời gian:* `CONSTRAINT chk_avail_slots_time CHECK (end_day_offset = 1 OR end_time > start_time)`.

---

#### 2.6. Bảng `ai_quotas` (Hạn ngạch AI Chu kỳ Hiện tại - 2-Phase Quota Guard)
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

#### 2.7. Bảng `ai_quota_reservations` (Sổ cái Giữ chỗ Hạn ngạch AI 2 Pha - MỚI v3.0)
* **Mục đích:** Theo dõi từng giao dịch giữ chỗ hạn ngạch AI 2 pha (`Reserve -> Commit / Release / Expired`), giúp Taskiq `QuotaSweeper` tự động thu hồi các lượt giữ chỗ bị treo khi tiến trình gọi LLM gặp sự cố.
* **Ánh xạ yêu cầu:** `FR-QUOTA-001`, `BUSR-10`, `ASR-02`, Sequence Diagram `SD3` & `SD9`.

| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 | Định danh duy nhất của phiên giữ chỗ hạn ngạch. |
| `quota_id` | `UUID` | No | None | No | `ai_quotas(id)` | No | No | UUID tồn tại | Khóa ngoại tham chiếu bản ghi hạn ngạch gốc (`ON DELETE CASCADE`). |
| `user_id` | `UUID` | No | None | No | `users(id)` | No | No | UUID tồn tại | Người học thực hiện yêu cầu gọi AI (`ON DELETE CASCADE`). |
| `operation_type` | `VARCHAR(50)` | No | None | No | No | No | No | Tên nghiệp vụ AI | Loại thao tác yêu cầu giữ chỗ (ví dụ: `ROADMAP_GENERATION`, `SCHEDULE_PROPOSAL`, `AI_REVIEW`). |
| `status` | `VARCHAR(20)` | No | `'RESERVED'` | No | No | No | Yes | `'RESERVED'`, `'COMMITTED'`, `'RELEASED'`, `'EXPIRED'` | Trạng thái vòng đời của bản ghi giữ chỗ (`chk_ai_quota_res_status`). |
| `tokens_reserved` | `INTEGER` | No | `0` | No | No | No | Yes | $\ge 0$ | Số lượng token tạm ước tính/giữ chỗ (`chk_ai_quota_res_tokens`). |
| `expires_at` | `TIMESTAMPTZ` | No | None | No | No | No | No | Dấu thời gian UTC | Thời điểm hết hạn giữ chỗ (mặc định `created_at + 120s (2 phút)`). |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm khởi tạo giữ chỗ Pha 1. |
| `resolved_at` | `TIMESTAMPTZ` | Yes | None | No | No | No | Yes* | Dấu thời gian UTC | Thời điểm chốt Pha 2 (`COMMITTED`, `RELEASED` hoặc `EXPIRED`). |

*\*Ràng buộc đối soát:* `CONSTRAINT chk_ai_quota_res_resolved CHECK ((status = 'RESERVED' AND resolved_at IS NULL) OR (status != 'RESERVED' AND resolved_at IS NOT NULL))`.

---

#### 2.8. Bảng `ai_usage_logs` (Nhật ký Gọi Dịch vụ AI Chi tiết)
* **Mục đích:** Lưu vết kiểm toán từng lần gọi AI qua `LLMProviderPort`: loại nghiệp vụ, số token, độ trễ, mô hình và trạng thái.
* **Ánh xạ yêu cầu:** `FR-QUOTA-001`, `FR-ADM-003`, `NFR-SEC-003`, `BUSR-10`.

| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 | Khóa chính bản ghi nhật ký. |
| `user_id` | `UUID` | No | None | No | `users(id)` | No | No | UUID tồn tại | Người dùng thực hiện gọi AI (`ON DELETE CASCADE`). |
| `action_type` | `VARCHAR(50)` | No | None | No | No | No | Yes | Danh mục 6 hành động | Nghiệp vụ gọi AI: `ROADMAP_GENERATION`, `SCHEDULE_PROPOSAL`, `AI_REVIEW_WEEKLY`, `AI_REVIEW_MILESTONE`, `MILESTONE_BREAKDOWN`, `CHAT_ASSISTANT`. |
| `model_name` | `VARCHAR(100)` | No | `'gpt-4o-mini'` | No | No | No | No | Chuỗi tên model | Mô hình LLM tiếp nhận xử lý (Gemini / OpenAI / Claude / Ollama / Mock). |
| `prompt_tokens` | `INTEGER` | No | `0` | No | No | No | Yes | $\ge 0$ | Số lượng token đầu vào (prompt). |
| `completion_tokens` | `INTEGER` | No | `0` | No | No | No | Yes | $\ge 0$ | Số lượng token đầu ra (completion). |
| `total_tokens` | `INTEGER` | No | `0` | No | No | No | Yes | $\ge 0$ | Tổng số token tiêu thụ của lượt gọi. |
| `latency_ms` | `INTEGER` | No | `0` | No | No | No | Yes | $\ge 0$ | Thời gian phản hồi tính bằng mili-giây. |
| `status` | `VARCHAR(20)` | No | `'SUCCESS'` | No | No | No | Yes | 4 trạng thái | Kết quả gọi: `'SUCCESS'`, `'FAILED'`, `'RATE_LIMITED'`, `'TIMEOUT'`. |
| `error_message` | `TEXT` | Yes | None | No | No | No | No | Văn bản | Chi tiết thông báo lỗi nếu gọi thất bại. |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm ghi nhận lượt gọi AI. |

---

#### 2.9. Bảng `payment_transactions` (Giao dịch Thanh toán Nâng cấp Gói - MỚI v3.0)
* **Mục đích:** Lưu trữ đơn hàng và kết quả đối soát Webhook `HMAC-SHA256` khi người học nâng cấp lên gói `PREMIUM` qua `PaymentGatewayPort`.
* **Ánh xạ yêu cầu:** `FR-QUOTA-002`, `UC-04`, `UC-05`, `UC-18`, `UC-19`, `ASR-06`.

| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 | Định danh duy nhất của giao dịch thanh toán. |
| `user_id` | `UUID` | No | None | No | `users(id)` | No | No | UUID tồn tại | Người học thực hiện thanh toán (`ON DELETE RESTRICT` bảo vệ chứng từ). |
| `transaction_ref` | `VARCHAR(100)` | No | None | No | No | Yes | No | Mã tham chiếu duy nhất | Mã đơn hàng duy nhất đối soát với cổng thanh toán (`uq_payment_transactions_ref`). |
| `gateway_provider` | `VARCHAR(20)` | No | `'PAYOS'` | No | No | No | Yes | `'PAYOS'`, `'VNPAY'`, `'MOCK'` | Nhà cung cấp cổng thanh toán xử lý giao dịch (`chk_payment_transactions_provider`). |
| `amount_vnd` | `INTEGER` | No | None | No | No | No | Yes | $> 0$ | Số tiền thanh toán tính bằng Đồng Việt Nam (`chk_payment_transactions_amount`). |
| `currency` | `VARCHAR(10)` | No | `'VND'` | No | No | No | No | `'VND'` | Đơn vị tiền tệ thanh toán. |
| `status` | `VARCHAR(20)` | No | `'PENDING'` | No | No | No | Yes | `'PENDING'`, `'PAID'`, `'FAILED'`, `'CANCELLED'`, `'REFUNDED'` | Trạng thái vòng đời của giao dịch (`chk_payment_transactions_status`). |
| `qr_code_url` | `TEXT` | Yes | None | No | No | No | No | URL hợp lệ | Đường dẫn mã QR / trang checkout trả về từ cổng thanh toán. |
| `webhook_signature_verified` | `BOOLEAN` | No | `FALSE` | No | No | No | No | `TRUE`, `FALSE` | Cờ xác nhận chữ ký số Webhook `HMAC-SHA256` đã được kiểm tra hợp lệ. |
| `paid_at` | `TIMESTAMPTZ` | Yes | None | No | No | No | Yes* | Dấu thời gian UTC | Thời điểm thanh toán thành công (`chk_payment_transactions_paid_at`). |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm khởi tạo giao dịch. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm cập nhật gần nhất (Trigger `trg_payment_transactions_updated_at`). |

---

### PHẦN B — BOUNDED CONTEXT 2: `planning` (5 BẢNG)

#### 2.10. Bảng `goals` (Mục tiêu Học tập)
* **Mục đích:** Lưu trữ mục tiêu học tập gốc của người học trước khi AI sinh lộ trình thích ứng.
* **Ánh xạ yêu cầu:** `FR-GOAL-001..002`, `NFR-SEC-003`.

| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 | Khóa chính mục tiêu. |
| `user_id` | `UUID` | No | None | No | `users(id)` | No | No | UUID tồn tại | Người sở hữu mục tiêu (`ON DELETE CASCADE`). |
| `title` | `TEXT` | No | None | No | No | No | No | Chuỗi không rỗng | Tên tiêu đề mục tiêu học tập. |
| `raw_description` | `TEXT` | No | None | No | No | No | No | Văn bản | Nguyện vọng, nền tảng kiến thức hiện tại và bối cảnh chi tiết. |
| `target_date` | `DATE` | Yes | None | No | No | No | No | YYYY-MM-DD | Hạn chót kỳ vọng hoàn thành mục tiêu. |
| `status` | `VARCHAR(20)` | No | `'ACTIVE'` | No | No | No | Yes | `'ACTIVE'`, `'COMPLETED'`, `'ARCHIVED'` | Trạng thái mục tiêu (`chk_goals_status`). |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm tạo mục tiêu. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm sửa đổi mục tiêu gần nhất (Trigger `trg_goals_updated_at`). |

---

#### 2.11. Bảng `roadmaps` (Lộ trình Tự học Thích ứng)
* **Mục đích:** Kế hoạch học tập tổng thể phân rã từ Goal, quản lý trạng thái vòng đời học tập.
* **Ánh xạ yêu cầu:** `FR-PLAN-001`, `BUSR-01`, Máy trạng thái Lộ trình.

| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 | Khóa chính lộ trình. |
| `user_id` | `UUID` | No | None | No | `users(id)` | No | No | UUID tồn tại | Người sở hữu lộ trình (`ON DELETE CASCADE`). |
| `goal_id` | `UUID` | No | None | No | `goals(id)` | No | No | UUID tồn tại | Mục tiêu gốc sinh ra lộ trình này (`ON DELETE CASCADE`). |
| `title` | `VARCHAR(255)` | No | None | No | No | No | No | Chuỗi văn bản | Tên định danh của lộ trình học tập. |
| `description` | `TEXT` | Yes | None | No | No | No | No | Văn bản | Diễn giải phạm vi kiến thức và chuẩn đầu ra của lộ trình. |
| `status` | `VARCHAR(20)` | No | `'INITIALIZED'` | No | No | No | Yes | `'INITIALIZED'`, `'ACTIVE'`, `'PAUSED'`, `'COMPLETED'`, `'ARCHIVED'` | Vòng đời lộ trình (`chk_roadmaps_status`). |
| `start_date` | `DATE` | Yes | None | No | No | No | No | YYYY-MM-DD | Ngày bắt đầu thực thi lộ trình. |
| `target_date` | `DATE` | Yes | None | No | No | No | Yes* | YYYY-MM-DD | Ngày dự kiến hoàn tất toàn bộ lộ trình (`target_date >= start_date`). |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm tạo lộ trình. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm cập nhật lộ trình gần nhất (Trigger `trg_roadmaps_updated_at`). |

---

#### 2.12. Bảng `milestones` (Mốc Kiến thức Tuần tự Cấp 1)
* **Mục đích:** Chia nhỏ lộ trình thành các chặng/mốc kiến thức tuần tự với cơ chế hoán đổi thứ tự.
* **Ánh xạ yêu cầu:** `FR-PLAN-002`, `BUSR-02`.

| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 | Khóa chính mốc kiến thức. |
| `roadmap_id` | `UUID` | No | None | No | `roadmaps(id)` | No | No | UUID tồn tại | Lộ trình chứa mốc kiến thức này (`ON DELETE CASCADE`). |
| `sequence_order` | `INTEGER` | No | None | No | No | Yes* | Yes | $\ge 1$ | Thứ tự tuần tự mốc kiến thức trong lộ trình (`DEFERRABLE INITIALLY DEFERRED`). |
| `title` | `VARCHAR(255)` | No | None | No | No | No | No | Chuỗi văn bản | Tiêu đề mốc kiến thức. |
| `description` | `TEXT` | Yes | None | No | No | No | No | Văn bản | Mô tả chi tiết nội dung kiến thức cần lĩnh hội. |
| `status` | `VARCHAR(20)` | No | `'PENDING'` | No | No | No | Yes | `'PENDING'`, `'APPROVED'`, `'IN_PROGRESS'`, `'COMPLETED'` | Trạng thái mốc (`chk_milestones_status`). |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm tạo mốc kiến thức. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm sửa đổi mốc gần nhất (Trigger `trg_milestones_updated_at`). |

---

#### 2.13. Bảng `official_schedules` (Lịch trình Học tập Chính thức - Frozen Baseline)
* **Mục đích:** Đại diện cho lịch học tập chính thức đang kích hoạt; đóng băng chỉ số kế hoạch cơ sở (`total_sessions`, `total_planned_minutes`) phục vụ đo lường KPI 3 (Plan Adherence Rate).
* **Ánh xạ yêu cầu:** `FR-PLAN-003`, `BUSR-02`, `BUSR-08`, `OS-03`.

| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 | Khóa chính lịch biểu chính thức. |
| `roadmap_id` | `UUID` | No | None | No | `roadmaps(id)` | Yes | No | UUID tồn tại | Mỗi lộ trình tại một thời điểm có 1 lịch chính thức (`ON DELETE CASCADE`). |
| `total_sessions` | `INTEGER` | No | `0` | No | No | No | Yes | $\ge 0$ | Tổng số phiên học kế hoạch đóng băng (Frozen Baseline). |
| `total_planned_minutes` | `INTEGER` | No | `0` | No | No | No | Yes | $\ge 0$ | Tổng số phút học kế hoạch đóng băng. |
| `activated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm người học kích hoạt lịch chính thức. |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm khởi tạo bản ghi lịch. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm cập nhật lịch gần nhất (Trigger `trg_official_schedules_updated_at`). |

---

#### 2.14. Bảng `schedule_proposals` (Bản Đề xuất Lịch Xem trước từ AI - Preview Draft)
* **Mục đích:** Lưu trữ bản nháp đề xuất lịch xem trước từ AI sau khi vượt qua **3-Tier Hybrid Validation Gate**; tuyệt đối không tự động ghi đè lịch chính thức.
* **Ánh xạ yêu cầu:** `FR-PLAN-005`, `BUSR-02` (Strict Apply Policy), `OS-03`, `ASR-04`.

| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 | Khóa chính đề xuất lịch. |
| `roadmap_id` | `UUID` | No | None | No | `roadmaps(id)` | No | No | UUID tồn tại | Lộ trình được đề xuất lịch (`ON DELETE CASCADE`). |
| `user_id` | `UUID` | No | None | No | `users(id)` | No | No | UUID tồn tại | Người sở hữu đề xuất lịch (`ON DELETE CASCADE`). |
| `proposal_data` | `JSONB` | No | None | No | No | No | Yes* | JSON Object | Toàn bộ danh sách nhiệm vụ dự thảo và ngày/giờ đề xuất từ LLM (`chk_schedule_proposals_data`). |
| `status` | `VARCHAR(20)` | No | `'DRAFT'` | No | No | No | Yes | `'DRAFT'`, `'APPLIED'`, `'DISCARDED'` | Vòng đời đề xuất (`uq_schedule_proposals_roadmap_draft`). |
| `applied_at` | `TIMESTAMPTZ` | Yes | None | No | No | No | No | Dấu thời gian UTC | Thời điểm người học bấm Apply để đưa vào lịch chính thức. |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm AI sinh bản đề xuất. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm sửa đổi đề xuất gần nhất (Trigger `trg_schedule_proposals_updated_at`). |

---

### PHẦN C — BOUNDED CONTEXT 3: `execution` (5 BẢNG)

#### 2.15. Bảng `tasks` (Nhiệm vụ Học tập Chi tiết Cấp 2)
* **Mục đích:** Đầu việc học tập cụ thể, lên lịch trực tiếp qua `scheduled_date`, `scheduled_start`, `scheduled_end` và liên kết với `official_schedule_id`.
* **Ánh xạ yêu cầu:** `FR-TASK-001`, `FR-ADAPT-003`, `BUSR-06`, `BUSR-07`.

| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 | Khóa chính nhiệm vụ. |
| `roadmap_id` | `UUID` | No | None | No | `roadmaps(id)` | No | No | UUID tồn tại | Lộ trình chứa nhiệm vụ (`ON DELETE CASCADE`, Cross-Context FK `execution -> planning`). |
| `milestone_id` | `UUID` | No | None | No | `milestones(id)` | No | No | UUID tồn tại | Mốc kiến thức trực thuộc (`ON DELETE CASCADE`, Cross-Context FK `execution -> planning`). |
| `official_schedule_id` | `UUID` | Yes | None | No | `official_schedules(id)` | No | No | UUID tồn tại | Lịch chính thức phân bổ nhiệm vụ này (`ON DELETE SET NULL`, Cross-Context FK `execution -> planning`). |
| `title` | `VARCHAR(255)` | No | None | No | No | No | No | Chuỗi văn bản | Tên nhiệm vụ cụ thể. |
| `description` | `TEXT` | Yes | None | No | No | No | No | Văn bản | Hướng dẫn chi tiết hoặc tài liệu tham khảo đính kèm. |
| `estimated_minutes` | `INTEGER` | No | None | No | No | No | Yes | 15 đến 240 phút | Thời lượng ước tính hoàn thành nhiệm vụ (`chk_tasks_estimated_minutes`). |
| `scheduled_date` | `DATE` | Yes | None | No | No | No | No | YYYY-MM-DD | Ngày xếp lịch (`NULL` = Backlog chưa xếp lịch). |
| `scheduled_start` | `TIMESTAMPTZ` | Yes | None | No | No | No | Yes* | Dấu thời gian UTC | Mốc thời gian bắt đầu xếp lịch (`chk_tasks_scheduled_time_order`). |
| `scheduled_end` | `TIMESTAMPTZ` | Yes | None | No | No | No | Yes* | Dấu thời gian UTC | Mốc thời gian kết thúc xếp lịch (`(scheduled_start IS NULL AND scheduled_end IS NULL) OR (scheduled_start IS NOT NULL AND scheduled_end IS NOT NULL AND scheduled_end > scheduled_start)`). |
| `status` | `VARCHAR(20)` | No | `'TODO'` | No | No | No | Yes | `'TODO'`, `'IN_PROGRESS'`, `'COMPLETED'`, `'CANCELLED'` | Trạng thái nhiệm vụ (`chk_tasks_status`). |
| `completed_at` | `TIMESTAMPTZ` | Yes | None | No | No | No | Yes** | Dấu thời gian UTC | Thời điểm đánh dấu hoàn thành nhiệm vụ (`chk_tasks_completed_at`). |
| `reschedule_count` | `INTEGER` | No | `0` | No | No | No | Yes | $\ge 0$ | Số lần nhiệm vụ bị dời lịch tự động liên tiếp (ngưỡng chống lặp $\ge 3$). |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm tạo nhiệm vụ. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm sửa đổi nhiệm vụ gần nhất (Trigger `trg_tasks_updated_at`). |

---

#### 2.16. Bảng `task_dependencies` (Quan hệ Tiên quyết Nhiệm vụ - DAG)
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

#### 2.17. Bảng `study_sessions` (Phiên Thực thi Học tập Pomodoro / Stopwatch)
* **Mục đích:** Quản lý buổi học tập trung, ghi nhận thời gian thực học và tín hiệu duy trì Heartbeat ping 60s.
* **Ánh xạ yêu cầu:** `FR-SESSION-001..003`, `BUSR-09`, `OS-01`, `OS-07`, `ASR-05`.

| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 | Khóa chính phiên học. |
| `user_id` | `UUID` | No | None | No | `users(id)` | No | No | UUID tồn tại | Người học thực hiện phiên (`ON DELETE CASCADE`). |
| `roadmap_id` | `UUID` | No | None | No | `roadmaps(id)` | No | No | UUID tồn tại | Lộ trình đang học (`ON DELETE CASCADE`). |
| `started_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm bắt đầu bấm giờ phiên học. |
| `ended_at` | `TIMESTAMPTZ` | Yes | None | No | No | No | Yes* | Dấu thời gian UTC | Thời điểm kết thúc phiên (`ended_at >= started_at`). |
| `planned_minutes` | `INTEGER` | No | None | No | No | No | Yes | $> 0$ | Thời lượng dự kiến ban đầu. |
| `actual_minutes` | `INTEGER` | No | `0` | No | No | No | Yes | $\ge 0$ | Thời gian thực học thực tế (tính đến gói Heartbeat ping cuối). |
| `status` | `VARCHAR(20)` | No | `'IN_PROGRESS'` | No | No | No | Yes | `'IN_PROGRESS'`, `'COMPLETED'`, `'PARTIAL_COMPLETED'`, `'CANCELLED'` | Trạng thái phiên học (`chk_study_sessions_status`). |
| `last_heartbeat_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm client gửi ping gần nhất (quét bởi Taskiq Scheduler mỗi 60s). |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm khởi tạo bản ghi phiên học. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm cập nhật phiên học gần nhất (Trigger `trg_study_sessions_updated_at`). |

---

#### 2.18. Bảng `session_tasks` (Bảng Liên kết Nhiều - Nhiều giữa Phiên học và Nhiệm vụ)
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

#### 2.19. Bảng `study_notes` (Ghi chép Không gian Học tập)
* **Mục đích:** Lưu trữ bản nháp tức thời (`SCRATCHPAD`), đúc kết cốt lõi (`TAKEAWAY`) và ghi chép tổng quát (`GENERAL`).
* **Ánh xạ yêu cầu:** `FR-SESSION-002`, `NFR-SEC-003`.

| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 | Khóa chính bản ghi chép. |
| `user_id` | `UUID` | No | None | No | `users(id)` | No | No | UUID tồn tại | Người sở hữu ghi chép (`ON DELETE CASCADE`). |
| `session_id` | `UUID` | Yes | None | No | `study_sessions(id)` | Yes* | No | UUID tồn tại | Phiên học liên kết (`ON DELETE CASCADE`, Intra-Context FK). |
| `task_id` | `UUID` | Yes | None | No | `tasks(id)` | No | No | UUID tồn tại | Nhiệm vụ liên kết (`ON DELETE SET NULL`, Intra-Context FK `execution -> execution`). |
| `note_type` | `VARCHAR(20)` | No | None | No | No | Yes* | Yes | `'SCRATCHPAD'`, `'TAKEAWAY'`, `'GENERAL'` | Phân loại ghi chú (`uq_study_notes_session_type`). |
| `content` | `TEXT` | No | `''` | No | No | No | No | Văn bản Markdown | Nội dung ghi chép của người học. |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm tạo ghi chép. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm sửa đổi ghi chép gần nhất (Trigger `trg_study_notes_updated_at`). |

---

### PHẦN D — BOUNDED CONTEXT 4: `evaluation` (3 BẢNG)

#### 2.20. Bảng `pause_records` (Lịch sử Tạm dừng Lộ trình & Tịnh tiến Domino Shift)
* **Mục đích:** Lưu trữ các đợt tạm dừng học tập và số ngày đã tịnh tiến dời lịch tự động của toàn bộ nhiệm vụ.
* **Ánh xạ yêu cầu:** `FR-PAUSE-001..002`, `BUSR-07`, `EVAL-03`.

| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 | Khóa chính bản ghi tạm dừng. |
| `roadmap_id` | `UUID` | No | None | No | `roadmaps(id)` | No | No | UUID tồn tại | Lộ trình được tạm dừng (`ON DELETE CASCADE`, Cross-Context FK `evaluation -> planning`). |
| `pause_start_date` | `DATE` | No | None | No | No | No | No | YYYY-MM-DD | Ngày bắt đầu tạm dừng học. |
| `pause_end_date` | `DATE` | No | None | No | No | No | Yes* | YYYY-MM-DD | Ngày kết thúc tạm dừng (`pause_end_date >= pause_start_date`). |
| `shifted_days` | `INTEGER` | No | None | No | No | No | Yes** | $> 0$ | Số ngày lịch học bị tịnh tiến (`shifted_days = pause_end_date - pause_start_date + 1`). |
| `reason` | `TEXT` | Yes | None | No | No | No | No | Văn bản | Lý do tạm dừng. |
| `status` | `VARCHAR(20)` | No | `'ACTIVE'` | No | No | No | Yes | `'ACTIVE'`, `'COMPLETED'`, `'CANCELLED'` | Trạng thái đợt tạm dừng (`chk_pause_records_status`). |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm ghi nhận lệnh tạm dừng. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm sửa đổi gần nhất (Trigger `trg_pause_records_updated_at`). |

---

#### 2.21. Bảng `ai_reviews` (Báo cáo Đánh giá Tiến độ & Khuyến nghị Thích ứng từ AI)
* **Mục đích:** Lưu trữ nhận xét định tính và bản chụp số liệu `QuantitativeMetrics` định kỳ tuần hoặc sau mỗi mốc kiến thức hoàn thành, đồng bộ 100% với lớp `AIReview` & `QuantitativeMetrics` (`class-diagram.puml` v5.0 & `FR-REPORT-001/002`).
* **Ánh xạ yêu cầu:** `FR-REPORT-001..002`, `BUSR-12`.

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
| `strengths_feedback` | `TEXT` | No | None | No | No | No | No | Văn bản | Nhận xét định tính phân tích các điểm mạnh học tập trong chu kỳ. |
| `bottlenecks_feedback` | `TEXT` | No | None | No | No | No | No | Văn bản | Nhận xét định tính chỉ ra điểm nghẽn và nguyên nhân trễ hạn. |
| `action_recommendations` | `TEXT` | No | None | No | No | No | No | Văn bản | Đề xuất hành động điều chỉnh lộ trình cụ thể cho chu kỳ tiếp theo. |
| `model_used` | `VARCHAR(100)` | No | None | No | No | No | No | Chuỗi tên model | Định danh mô hình LLM đã thực hiện sinh báo cáo đánh giá. |
| `generated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm AI sinh nội dung đánh giá. |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm lưu bản ghi. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm cập nhật bản ghi gần nhất (Trigger `trg_ai_reviews_updated_at`). |

*\*Ràng buộc chu kỳ:* `CONSTRAINT chk_ai_reviews_period_order CHECK ((review_cycle = 'MILESTONE' AND milestone_id IS NOT NULL AND period_start IS NULL AND period_end IS NULL) OR (review_cycle = 'WEEKLY' AND milestone_id IS NULL AND period_start IS NOT NULL AND period_end IS NOT NULL AND period_end >= period_start))`.

---

#### 2.22. Bảng `schedule_change_logs` (Nhật ký Kiểm toán Biến động Lịch học - MỚI v3.0)
* **Mục đích:** Sổ nhật ký bất biến lưu vết toàn bộ các đợt thay đổi lịch học (Domino Shift, người học dời tay, AI Replan, đồng bộ lịch ngoài).
* **Ánh xạ yêu cầu:** `FR-ADAPT-001`, `BUSR-07`, `UC-10`, `UC-16`, `UC-17`.

| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 | Định danh duy nhất của bản ghi nhật ký biến động lịch. |
| `roadmap_id` | `UUID` | No | None | No | `roadmaps(id)` | No | No | UUID tồn tại | Lộ trình có lịch bị thay đổi (`ON DELETE CASCADE`). |
| `schedule_id` | `UUID` | Yes | None | No | `official_schedules(id)` | No | No | UUID tồn tại | Lịch chính thức bị tác động (`ON DELETE SET NULL`). |
| `task_id` | `UUID` | Yes | None | No | `tasks(id)` | No | No | UUID tồn tại | Nhiệm vụ cụ thể bị tác động nếu dời đơn lẻ (`ON DELETE SET NULL`). |
| `trigger_type` | `VARCHAR(30)` | No | None | No | No | No | Yes | `'DOMINO_SHIFT'`, `'MANUAL_EDIT'`, `'AI_REPLAN'`, `'CALENDAR_SYNC'` | Loại sự kiện/tác nhân kích hoạt biến động lịch (`chk_sched_change_logs_trigger`). |
| `reason` | `TEXT` | Yes | None | No | No | No | No | Văn bản | Lý do thay đổi lịch trình. |
| `affected_tasks_count` | `INTEGER` | No | `1` | No | No | No | Yes | $\ge 0$ | Tổng số nhiệm vụ bị thay đổi ngày/giờ học trong đợt này (`chk_sched_change_logs_affected`). |
| `total_shifted_minutes` | `INTEGER` | No | `0` | No | No | No | Yes | $\ge 0$ | Tổng số phút học bị dịch chuyển (`chk_sched_change_logs_minutes`). |
| `diff_payload` | `JSONB` | No | `'{}'::jsonb` | No | No | No | Yes | JSON Object | Ảnh chụp chi tiết trạng thái ngày/giờ trước và sau khi dời lịch (`chk_sched_change_logs_payload`). |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm ghi nhận biến động lịch. |

---

### PHẦN E — SHARED KERNEL: `shared_kernel` (2 BẢNG)

#### 2.23. Bảng `outbox_events` (Hàng đợi Sự kiện Giao dịch Liên Context - MỚI v3.0)
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

#### 2.24. Bảng `processed_events` (Sổ cái Chống Xử lý Trùng Sự kiện - MỚI v3.0)
* **Mục đích:** Triển khai mẫu **Idempotent Consumer Pattern** cho các trình xử lý sự kiện trên **Taskiq Worker**, đảm bảo mỗi handler chỉ xử lý một `event_id` đúng một lần duy nhất.
* **Ánh xạ yêu cầu:** `ASR-01`, `ASR-02`.

| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `event_id` | `UUID` | No | None | Yes* | `outbox_events(id)` | No | No | UUID tồn tại | Định danh sự kiện Outbox đã được tiêu thụ (`ON DELETE CASCADE`). |
| `handler_name` | `VARCHAR(120)` | No | None | Yes* | No | No | No | Tên Event Handler | Tên định danh của trình xử lý sự kiện (ví dụ: `'LearnerProfileAggregatorHandler'`). |
| `processed_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm hoàn tất xử lý sự kiện thành công. |

*\*Khóa chính kép:* `CONSTRAINT pk_processed_events PRIMARY KEY (event_id, handler_name)`.

---

## 3. Ma trận Ràng buộc Toàn vẹn Khóa ngoại & Chiến lược Xóa (Referential Actions Matrix — 24 Bảng)

### 3.1. Ma trận Phân loại Intra-Context FK vs Cross-Context FK & Hành vi `ON DELETE` (Theo Phân rã `9 / 5 / 5 / 3 / 2`)

| Bảng Nguồn (Child Table) | Bounded Context Nguồn | Cột Khóa Ngoại | Bảng Đích (Parent Table) | Bounded Context Đích | Phân loại FK | Hành vi `ON DELETE` | Mục đích Kỹ thuật & Bảo toàn Dữ liệu |
|---|---|---|---|---|---|---|---|
| `learner_profiles` | `account` | `user_id` | `users(id)` | `account` | **Intra-Context FK** | `CASCADE` | Xóa hồ sơ thói quen khi tài khoản người học bị xóa. |
| `webcal_tokens` | `account` | `user_id` | `users(id)` | `account` | **Intra-Context FK** | `CASCADE` | Xóa token đồng bộ lịch khi tài khoản bị xóa. |
| `availabilities` | `account` | `user_id` | `users(id)` | `account` | **Intra-Context FK** | `CASCADE` | Xóa cấu hình thời gian rảnh khi tài khoản bị xóa. |
| `availability_slots` | `account` | `availability_id` | `availabilities(id)` | `account` | **Intra-Context FK** | `CASCADE` | Xóa toàn bộ khung giờ rảnh khi cấu hình rảnh bị xóa. |
| `ai_quotas` | `account` | `user_id` | `users(id)` | `account` | **Intra-Context FK** | `CASCADE` | Xóa hạn ngạch AI khi tài khoản bị xóa. |
| `ai_quota_reservations` | `account` | `quota_id` | `ai_quotas(id)` | `account` | **Intra-Context FK** | `CASCADE` | Xóa sổ cái giữ chỗ khi bản ghi hạn ngạch bị xóa. |
| `ai_quota_reservations` | `account` | `user_id` | `users(id)` | `account` | **Intra-Context FK** | `CASCADE` | Xóa sổ cái giữ chỗ khi tài khoản bị xóa. |
| `ai_usage_logs` | `account` | `user_id` | `users(id)` | `account` | **Intra-Context FK** | `CASCADE` | Xóa nhật ký kiểm toán AI khi tài khoản bị xóa. |
| `payment_transactions` | `account` | `user_id` | `users(id)` | `account` | **Intra-Context FK** | **`RESTRICT`** | **Bảo vệ chứng từ tài chính:** Chặn xóa cứng người dùng đã có giao dịch thanh toán. |
| `goals` | `planning` | `user_id` | `users(id)` | `account` | **Cross-Context FK** | `CASCADE` | Xóa mục tiêu khi người dùng xóa tài khoản. |
| `roadmaps` | `planning` | `user_id` | `users(id)` | `account` | **Cross-Context FK** | `CASCADE` | Xóa lộ trình khi người dùng xóa tài khoản. |
| `roadmaps` | `planning` | `goal_id` | `goals(id)` | `planning` | **Intra-Context FK** | `CASCADE` | Xóa các lộ trình liên thuộc khi mục tiêu bị xóa. |
| `milestones` | `planning` | `roadmap_id` | `roadmaps(id)` | `planning` | **Intra-Context FK** | `CASCADE` | Xóa mốc kiến thức khi lộ trình bị xóa. |
| `official_schedules` | `planning` | `roadmap_id` | `roadmaps(id)` | `planning` | **Intra-Context FK** | `CASCADE` | Xóa lịch chính thức khi lộ trình bị xóa. |
| `schedule_proposals` | `planning` | `roadmap_id` | `roadmaps(id)` | `planning` | **Intra-Context FK** | `CASCADE` | Xóa đề xuất lịch khi lộ trình bị xóa. |
| `schedule_proposals` | `planning` | `user_id` | `users(id)` | `account` | **Cross-Context FK** | `CASCADE` | Xóa đề xuất lịch khi tài khoản người học bị xóa. |
| `tasks` | `execution` | `roadmap_id` | `roadmaps(id)` | `planning` | **Cross-Context FK** | `CASCADE` | Xóa nhiệm vụ khi lộ trình bị xóa (`execution` -> `planning`). |
| `tasks` | `execution` | `milestone_id` | `milestones(id)` | `planning` | **Cross-Context FK** | `CASCADE` | Xóa nhiệm vụ khi mốc kiến thức bị xóa (`execution` -> `planning`). |
| `tasks` | `execution` | `official_schedule_id` | `official_schedules(id)` | `planning` | **Cross-Context FK** | `SET NULL` | Giữ lại task nhưng ngắt liên kết lịch khi lịch chính thức được thay thế (`execution` -> `planning`). |
| `task_dependencies` | `execution` | `predecessor_id` | `tasks(id)` | `execution` | **Intra-Context FK** | `CASCADE` | Tự động dọn cạnh đồ thị khi nhiệm vụ tiên quyết bị xóa (`execution` -> `execution`). |
| `task_dependencies` | `execution` | `successor_id` | `tasks(id)` | `execution` | **Intra-Context FK** | `CASCADE` | Tự động dọn cạnh đồ thị khi nhiệm vụ phụ thuộc bị xóa (`execution` -> `execution`). |
| `task_dependencies` | `execution` | `roadmap_id` | `roadmaps(id)` | `planning` | **Cross-Context FK** | `CASCADE` | Dọn dẹp cạnh đồ thị khi lộ trình bị xóa (`execution` -> `planning`). |
| `study_sessions` | `execution` | `user_id` | `users(id)` | `account` | **Cross-Context FK** | `CASCADE` | Xóa phiên học khi tài khoản người học bị xóa. |
| `study_sessions` | `execution` | `roadmap_id` | `roadmaps(id)` | `planning` | **Cross-Context FK** | `CASCADE` | Xóa phiên học khi lộ trình bị xóa. |
| `session_tasks` | `execution` | `session_id` | `study_sessions(id)` | `execution` | **Intra-Context FK** | `CASCADE` | Xóa dòng liên kết khi phiên học bị xóa (`execution` -> `execution`). |
| `session_tasks` | `execution` | `task_id` | `tasks(id)` | `execution` | **Intra-Context FK** | **`RESTRICT`** | **Bảo vệ lịch sử học tập:** Chặn xóa cứng nhiệm vụ đã có phiên Pomodoro ghi nhận (`execution` -> `execution`). |
| `study_notes` | `execution` | `user_id` | `users(id)` | `account` | **Cross-Context FK** | `CASCADE` | Xóa ghi chép khi tài khoản bị xóa. |
| `study_notes` | `execution` | `session_id` | `study_sessions(id)` | `execution` | **Intra-Context FK** | `CASCADE` | Xóa ghi chép gắn với phiên học khi phiên học bị xóa (`execution` -> `execution`). |
| `study_notes` | `execution` | `task_id` | `tasks(id)` | `execution` | **Intra-Context FK** | `SET NULL` | Giữ nguyên ghi chép học tập, chỉ gỡ liên kết task nếu task bị xóa (`execution` -> `execution`). |
| `pause_records` | `evaluation` | `roadmap_id` | `roadmaps(id)` | `planning` | **Cross-Context FK** | `CASCADE` | Xóa lịch sử tạm dừng khi lộ trình bị xóa (`evaluation` -> `planning`). |
| `ai_reviews` | `evaluation` | `roadmap_id` | `roadmaps(id)` | `planning` | **Cross-Context FK** | `CASCADE` | Xóa báo cáo AI khi lộ trình bị xóa. |
| `ai_reviews` | `evaluation` | `user_id` | `users(id)` | `account` | **Cross-Context FK** | `CASCADE` | Xóa báo cáo AI khi tài khoản bị xóa. |
| `ai_reviews` | `evaluation` | `milestone_id` | `milestones(id)` | `planning` | **Cross-Context FK** | `CASCADE` | Xóa báo cáo mốc khi mốc kiến thức bị xóa. |
| `schedule_change_logs` | `evaluation` | `roadmap_id` | `roadmaps(id)` | `planning` | **Cross-Context FK** | `CASCADE` | Xóa nhật ký biến động lịch khi lộ trình bị xóa. |
| `schedule_change_logs` | `evaluation` | `schedule_id` | `official_schedules(id)` | `planning` | **Cross-Context FK** | `SET NULL` | Giữ nguyên nhật ký kiểm toán ngay cả khi lịch chính thức được tạo mới. |
| `schedule_change_logs` | `evaluation` | `task_id` | `tasks(id)` | `execution` | **Cross-Context FK** | `SET NULL` | Giữ nguyên nhật ký kiểm toán nếu nhiệm vụ chưa học bị xóa. |
| `processed_events` | `shared_kernel` | `event_id` | `outbox_events(id)` | `shared_kernel` | **Intra-Context FK** | `CASCADE` | Dọn dẹp bản ghi chống lặp khi sự kiện Outbox cũ được lưu trữ/xóa. |

---

## 4. Ma trận Chỉ mục Hiệu năng & Ràng buộc Đồng thời (Indexes Matrix — 37 Chỉ mục)

| Tên Chỉ mục (Index Name) | Bảng Áp dụng | Các Cột Chỉ mục | Loại Index | Điều kiện (WHERE Clause / Partial) | Mục đích Kỹ thuật & Nghiệp vụ |
|---|---|---|---|---|---|
| `uq_users_lower_email` | `users` | `(LOWER(email))` | B-Tree Unique | Không | Chống trùng email không phân biệt hoa thường (`FR-AUTH-001`). |
| `uq_study_sessions_user_active` | `study_sessions` | `(user_id)` | B-Tree Unique Partial | `WHERE status = 'IN_PROGRESS'` | **Bất biến đồng thời:** Một user tại một thời điểm chỉ có tối đa 1 phiên học đang chạy (`OS-01`). |
| `uq_schedule_proposals_roadmap_draft` | `schedule_proposals` | `(roadmap_id)` | B-Tree Unique Partial | `WHERE status = 'DRAFT'` | **Bất biến đề xuất:** Mỗi lộ trình tại một thời điểm chỉ có tối đa 1 bản nháp đề xuất chưa duyệt. |
| `uq_ai_reviews_weekly` | `ai_reviews` | `(roadmap_id, period_start, period_end)` | B-Tree Unique Partial | `WHERE review_cycle = 'WEEKLY'` | Chống sinh trùng báo cáo tuần khi Taskiq Worker Retry (Idempotency). |
| `uq_ai_reviews_milestone` | `ai_reviews` | `(roadmap_id, milestone_id)` | B-Tree Unique Partial | `WHERE review_cycle = 'MILESTONE'` | Chống sinh trùng báo cáo mốc khi Taskiq Worker Retry (Idempotency). |
| `idx_quota_reservations_cleanup` | `ai_quota_reservations` | `(expires_at)` | B-Tree Partial | `WHERE status = 'RESERVED'` | Taskiq `QuotaSweeper` quét và thu hồi nhanh các giữ chỗ AI bị treo quá hạn (`ASR-02`). |
| `idx_quota_reservations_user_status` | `ai_quota_reservations` | `(user_id, status, created_at DESC)` | B-Tree | Không | Tra cứu lịch sử giữ chỗ hạn ngạch AI theo người dùng. |
| `idx_payment_transactions_user_created` | `payment_transactions` | `(user_id, created_at DESC)` | B-Tree | Không | Truy vấn lịch sử thanh toán nâng cấp gói cước của người học (`UC-04`, `UC-18`). |
| `idx_payment_transactions_status` | `payment_transactions` | `(status, created_at DESC)` | B-Tree | Không | Đối soát và thống kê doanh thu theo trạng thái giao dịch (`UC-19`). |
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
