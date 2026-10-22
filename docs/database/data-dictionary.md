# FocusFlow — Từ điển Dữ liệu, Ma trận Ràng buộc & Ma trận Chỉ mục (Database Schema Governance)

## Thông tin Hồ sơ Kỹ thuật
* **Dự án:** FocusFlow — Hệ thống hỗ trợ lập kế hoạch và thực thi lộ trình tự học thích ứng tích hợp AI
* **Phiên bản:** v1.0 — Chuẩn Quản trị Lược đồ Cơ sở Dữ liệu (Database Schema Governance Baseline)
* **Hệ quản trị CSDL:** PostgreSQL 16+
* **Tiêu chuẩn kỹ thuật:** ISO/IEC 9075:2023 (SQL Standard), ISO/IEC/IEEE 29148:2018 (Requirements Engineering)
* **Căn cứ đánh giá học thuật:** Khung Rubric Đồ án Tốt nghiệp CNTT — Tiêu chí TC2.1 & TC2.3 (Mức 5)
* **Tài liệu nguồn chân lý liên kết:**
  * Tập lệnh DDL: [`docs/database/schema.sql`](file:///Users/vuthang/Documents/FocusFlow/docs/database/schema.sql)
  * Thiết kế CSDL Chi tiết: [`docs/database/database-schema-design.md`](file:///Users/vuthang/Documents/FocusFlow/docs/database/database-schema-design.md)
  * Đặc tả Yêu cầu SRS v1.1: [`docs/srs/srs-v1.0.md`](file:///Users/vuthang/Documents/FocusFlow/docs/srs/srs-v1.0.md)
  * Đặc tả Máy trạng thái: [`docs/uml/state-machines.md`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/state-machines.md)
  * Biểu đồ Tuần tự: [`docs/uml/sequence-diagrams.md`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/sequence-diagrams.md)

---

## 1. Từ điển Dữ liệu Toàn diện (Data Dictionary - 16 Bảng)

> [!IMPORTANT]
> **Quy ước Khóa chính Toàn hệ thống (Primary Key Strategy — UUIDv7):**
> * Toàn bộ các bảng trong hệ thống FocusFlow sử dụng kiểu dữ liệu `UUID` cho khóa chính.
> * Giá trị khóa chính được **sinh trực tiếp tại tầng Backend Application (Python FastAPI sử dụng thư viện `uuid6`/`uuid_utils` theo chuẩn RFC 9562 - UUIDv7 Time-Ordered)** trước khi ghi xuống CSDL.
> * **Lợi ích kỹ thuật:** Giữ nguyên tính bảo mật chống tấn công đoán ID (ID Enumeration), đồng thời đảm bảo các khóa chính được sắp xếp tăng dần theo thời gian (Time-Ordered Sequential), loại bỏ hoàn toàn hiện tượng phân mảnh trang (B-Tree Page Splitting) của chỉ mục B-Tree PK trong PostgreSQL 16 khi hệ thống mở rộng dữ liệu lớn.
> * CSDL PostgreSQL 16 khai báo `DEFAULT gen_random_uuid()` đóng vai trò Fallback an toàn khi thao tác chèn trực tiếp không qua Application.
> * Cơ chế Trigger dùng chung `set_updated_at()` tự động cập nhật dấu thời gian `updated_at = NOW()` trước mọi thao tác `UPDATE` trên tất cả các bảng có trường này.

### 1.1. Bảng `users` (Tài khoản & Phân quyền)
| Cột (Column) | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ (BUSR) & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 (RFC 9562) | Định danh duy nhất của người dùng; sinh theo chuẩn UUIDv7 tuần tự theo thời gian, chống phân mảnh B-Tree và chống tấn công đoán ID. |
| `email` | `VARCHAR(255)` | No | None | No | No | Yes* | No | Định dạng RFC 5322 | `FR-AUTH-001`. Tên đăng nhập duy nhất toàn hệ thống (không phân biệt hoa thường qua `uq_users_lower_email`). |
| `password_hash` | `VARCHAR(255)` | No | None | No | No | No | No | Chuỗi băm Argon2id | `NFR-SEC-001`. Mật khẩu đã băm an toàn, không lưu text thô. |
| `full_name` | `VARCHAR(100)` | No | None | No | No | No | No | 1–100 ký tự | Tên hiển thị người dùng trên giao diện. |
| `timezone` | `VARCHAR(50)` | No | `'Asia/Ho_Chi_Minh'` | No | No | No | No | Chuỗi IANA Timezone | `FR-PLAN-002`, `ADR-004`. Căn cứ tính ngày chuyển giao và Celery Beat. |
| `role` | `VARCHAR(20)` | No | `'LEARNER'` | No | No | No | Yes | `'LEARNER'`, `'ADMIN'` | `BUSR-11`. Phân quyền truy cập hệ thống; chặn route `/admin/*`. |
| `tier` | `VARCHAR(20)` | No | `'FREE'` | No | No | No | Yes | `'FREE'`, `'PREMIUM'` | `OS-02`. Phân tầng tài khoản chi phối định mức hạn ngạch AI. |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm đăng ký tài khoản. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm cập nhật thông tin gần nhất (Trigger `trg_users_updated_at`). |

*\*Ràng buộc duy nhất:* Unique Index `uq_users_lower_email` trên `LOWER(email)`.

### 1.2. Bảng `webcal_tokens` (Bảo mật Đồng bộ Lịch 1 chiều)
| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ (BUSR) & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 (RFC 9562) | Khóa chính bản ghi. |
| `user_id` | `UUID` | No | None | No | `users(id)` | Yes | No | UUID tồn tại | `BUSR-08`, `OS-05`. Quan hệ 1:1 với người dùng (`ON DELETE CASCADE`). |
| `token_hash` | `VARCHAR(64)` | No | None | No | No | Yes | Yes* | 64 ký tự Hex | `OS-05`. Bản băm SHA-256 của CSPRN 32-byte hex; không lưu token thô. Ràng buộc regex 64 ký tự hex. |
| `is_active` | `BOOLEAN` | No | `TRUE` | No | No | No | No | `TRUE`, `FALSE` | Trạng thái hiệu lực; bị chuyển sang `FALSE` khi người học bấm Reset. |
| `last_used_at` | `TIMESTAMPTZ` | Yes | None | No | No | No | No | Dấu thời gian | Thời điểm ứng dụng lịch ngoại vi (Google Cal) đồng bộ feed gần nhất. |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian | Thời điểm kích hoạt token lần đầu. |
| `rotated_at` | `TIMESTAMPTZ` | Yes | None | No | No | No | No | Dấu thời gian | Thời điểm làm mới/thu hồi token gần nhất (`FR-CALENDAR-003`). `NULL` khi mới khởi tạo. |

*\*Ràng buộc regex:* `CONSTRAINT chk_webcal_token_hash CHECK (token_hash ~ '^[0-9a-f]{64}$')`.

### 1.3. Bảng `ai_quotas` (Kiểm soát Hạn ngạch & Chi phí AI)
| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ (BUSR) & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 (RFC 9562) | Khóa chính bản ghi. |
| `user_id` | `UUID` | No | None | No | `users(id)` | Yes | No | UUID tồn tại | `BUSR-10`. Quan hệ 1:1 với User (`ON DELETE CASCADE`). |
| `monthly_limit` | `INTEGER` | No | `30` | No | No | No | Yes | `> 0` (Free: 30, Prem: 300) | `OS-02`. Số lượt gọi AI tối đa được phép trong một chu kỳ tháng. |
| `used_calls` | `INTEGER` | No | `0` | No | No | No | Yes | `>= 0` | Số lượt gọi AI đã xác nhận thành công (Commit). |
| `reserved_calls` | `INTEGER` | No | `0` | No | No | No | Yes | `>= 0` | Số lượt gọi đang tạm giữ 2 pha trước khi gọi LLM (Reserve). |
| `tokens_consumed` | `BIGINT` | No | `0` | No | No | No | Yes | `>= 0` | Tổng số token Gemini thực tế tiêu thụ (dùng `BIGINT` loại bỏ nguy cơ tràn số integer). |
| `cycle_start` | `TIMESTAMPTZ` | No | None | No | No | No | No | Dấu thời gian | Ngày đầu chu kỳ (00:00:00 ngày 01 hàng tháng). |
| `cycle_end` | `TIMESTAMPTZ` | No | None | No | No | No | Yes | `cycle_end > cycle_start` | Ngày cuối chu kỳ (23:59:59 ngày cuối tháng). |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian | Thời điểm khởi tạo chu kỳ hạn ngạch. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian | Thời điểm biến động hạn ngạch gần nhất (Trigger `trg_ai_quotas_updated_at`). |

### 1.4. Bảng `ai_quota_reservations` (Nhật ký Giữ chỗ Hạn ngạch AI 2 pha)
| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ (BUSR) & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 (RFC 9562) | Khóa chính phiên giữ chỗ hạn ngạch. |
| `user_id` | `UUID` | No | None | No | `users(id)` | No | No | UUID tồn tại | Người dùng giữ chỗ quota (`ON DELETE CASCADE`). |
| `status` | `VARCHAR(20)` | No | `'RESERVED'` | No | No | No | Yes | `'RESERVED'`, `'COMMITTED'`, `'RELEASED'`, `'EXPIRED'` | Vòng đời giữ chỗ 2-pha chống rò rỉ quota khi đứt kết nối stream/worker lỗi. |
| `estimated_tokens` | `INTEGER` | No | `0` | No | No | No | Yes | `>= 0` | Số token ước tính giữ chỗ ban đầu. |
| `tokens_consumed` | `INTEGER` | No | `0` | No | No | No | Yes | `>= 0` | Số token thực tế tiêu thụ sau khi stream hoàn tất. |
| `expires_at` | `TIMESTAMPTZ` | No | None | No | No | No | No | Dấu thời gian | Thời điểm hết hạn giữ chỗ (55s timeout theo `NFR-PERF-001`). Quét bởi Background Sweeper. |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian | Thời điểm tạo lệnh giữ chỗ. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian | Thời điểm cập nhật trạng thái gần nhất (Trigger `trg_ai_quota_reservations_updated_at`). |

### 1.5. Bảng `availabilities` (Hồ sơ Quỹ thời gian rảnh)
| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ (BUSR) & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 (RFC 9562) | Khóa chính bản ghi. |
| `user_id` | `UUID` | No | None | No | `users(id)` | Yes | No | UUID tồn tại | `BUSR-03..04`. Mỗi User có đúng 1 hồ sơ thời gian rảnh (1:1). |
| `mode` | `VARCHAR(10)` | No | `'MODE_A'` | No | No | No | Yes | `'MODE_A'`, `'MODE_B'` | Phân loại chế độ rảnh: Mode A (Quỹ giờ), Mode B (Khung giờ cố định). |
| `calendar_integration_mode` | `VARCHAR(20)` | No | `'NONE'` | No | No | No | Yes | `'NONE'`, `'EXPORT_ICS'`, `'CONNECTED'` | Trạng thái tích hợp lịch ngoài (D-06): NONE (nội bộ), EXPORT_ICS (WebCal/ICS 1 chiều), CONNECTED (Google Calendar). |
| `weekly_schedule` | `JSONB` | No | None | No | No | No | Yes* | JSON Object Schema | `OS-06`, `D-05`, `D-10`. Cấu hình 7 ngày. Mode A gồm `quota_hours` (0.5h-14h), `allowed_window` ({start, end}), `preferred_period`, `min_session_minutes`. Mode B gồm mảng `time_slots` ({start, end, end_day_offset}). `enabled` dùng chung bảo toàn dữ liệu cả 2 mode. |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian | Thời điểm khởi tạo cấu hình thời gian rảnh. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian | Thời điểm cập nhật lịch rảnh gần nhất (Trigger `trg_availabilities_updated_at`, phục vụ Optimistic Locking D-09). |

*\*Ràng buộc kiểu JSON:* `CONSTRAINT chk_availabilities_schedule_json CHECK (jsonb_typeof(weekly_schedule) = 'object')`.
*\*Ràng buộc chế độ lịch:* `CONSTRAINT chk_availabilities_calendar_mode CHECK (calendar_integration_mode IN ('NONE', 'EXPORT_ICS', 'CONNECTED'))`.

### 1.6. Bảng `goals` (Mục tiêu học tập gốc)
| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ (BUSR) & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 (RFC 9562) | Khóa chính mục tiêu. |
| `user_id` | `UUID` | No | None | No | `users(id)` | No | No | UUID tồn tại | Người sở hữu mục tiêu (`ON DELETE CASCADE`). |
| `title` | `TEXT` | No | None | No | No | No | No | Chuỗi không rỗng | `FR-GOAL-001`. Tên mục tiêu học tập (ví dụ: "Học Go Backend"). |
| `raw_description` | `TEXT` | No | None | No | No | No | No | Văn bản | Ngữ cảnh, kinh nghiệm hiện tại và nguyện vọng chi tiết của người học. |
| `target_date` | `DATE` | Yes | None | No | No | No | No | YYYY-MM-DD tương lai | Hạn chót kỳ vọng hoàn thành mục tiêu (kiểu `DATE` khớp `roadmaps`). |
| `status` | `VARCHAR(20)` | No | `'ACTIVE'` | No | No | No | Yes | `'ACTIVE'`, `'ARCHIVED'` | Trạng thái mục tiêu; `ARCHIVED` sẽ ẩn toàn bộ lộ trình liên thuộc. |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian | Thời điểm nhập mục tiêu. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian | Thời điểm cập nhật mục tiêu gần nhất (Trigger `trg_goals_updated_at`). |

*\*Siêu khóa duy nhất:* `CONSTRAINT uq_goals_id_user UNIQUE (id, user_id)` bảo vệ toàn vẹn cùng chủ sở hữu khi liên kết từ `roadmaps`.

### 1.7. Bảng `roadmaps` (Lộ trình học tập tổng thể)
| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ (BUSR) & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 (RFC 9562) | Khóa chính lộ trình. |
| `user_id` | `UUID` | No | None | No | `users(id)` | No | No | UUID tồn tại | Người sở hữu lộ trình (`ON DELETE CASCADE`). |
| `goal_id` | `UUID` | No | None | No | `goals(id, user_id)`* | No | No | UUID tồn tại | Khóa ngoại phức hợp `(goal_id, user_id)` với `ON DELETE NO ACTION`. |
| `title` | `VARCHAR(255)` | No | None | No | No | No | No | Chuỗi văn bản | Tên định danh của lộ trình học tập. |
| `description` | `TEXT` | Yes | None | No | No | No | No | Văn bản | Mô tả tóm lược phạm vi kiến thức lộ trình bao phủ. |
| `status` | `VARCHAR(20)` | No | `'INITIALIZED'` | No | No | No | Yes | `'INITIALIZED'`, `'ACTIVE'`, `'PAUSED'`, `'COMPLETED'`, `'ARCHIVED'` | `BUSR-01`, SRS Mục 6.1. Vòng đời máy trạng thái Roadmap. |
| `start_date` | `DATE` | Yes | None | No | No | No | No | Định dạng YYYY-MM-DD | Ngày bắt đầu học chính thức. |
| `target_date` | `DATE` | Yes | None | No | No | No | Yes** | Định dạng YYYY-MM-DD | Ngày dự kiến hoàn thành toàn bộ lộ trình. |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian | Thời điểm khởi tạo lộ trình. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian | Thời điểm cập nhật trạng thái (Trigger `trg_roadmaps_updated_at`). |

*\*Khóa ngoại phức hợp & Siêu khóa:* `CONSTRAINT uq_roadmaps_id_user UNIQUE (id, user_id)` và `CONSTRAINT fk_roadmaps_goal_user FOREIGN KEY (goal_id, user_id) REFERENCES goals(id, user_id) ON DELETE NO ACTION`.  
*\*\*Ràng buộc thời gian:* `CONSTRAINT chk_roadmap_dates CHECK (target_date IS NULL OR start_date IS NULL OR target_date >= start_date)`.

### 1.8. Bảng `milestones` (Mốc kiến thức Cấp 1)
| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ (BUSR) & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 (RFC 9562) | Khóa chính mốc kiến thức. |
| `roadmap_id` | `UUID` | No | None | No | `roadmaps(id)` | No | No | UUID tồn tại | Lộ trình chứa mốc này (`ON DELETE CASCADE`). |
| `sequence_order`| `INTEGER` | No | None | No | No | Yes* | Yes | `>= 1` | `BUSR-02`. Thứ tự tuần tự mốc kiến thức; duy nhất trong Roadmap. |
| `title` | `VARCHAR(255)` | No | None | No | No | No | No | Chuỗi văn bản | `FR-PLAN-001`. Tên mốc kiến thức (ví dụ: "Cơ bản cú pháp Go"). |
| `description` | `TEXT` | Yes | None | No | No | No | No | Văn bản | Tóm tắt các chủ đề trọng tâm trong mốc. |
| `status` | `VARCHAR(20)` | No | `'PENDING'` | No | No | No | Yes | `'PENDING'`, `'APPROVED'` | `FR-PLAN-001`. Phải được duyệt (`APPROVED`) trước khi sinh task Cấp 2. |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian | Thời điểm AI sinh hoặc người dùng thêm mốc. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian | Thời điểm cập nhật thông tin mốc (Trigger `trg_milestones_updated_at`). |

*\*Ràng buộc duy nhất hoán đổi được & siêu khóa:* `CONSTRAINT uq_milestone_roadmap_sequence UNIQUE (roadmap_id, sequence_order) DEFERRABLE INITIALLY DEFERRED` và `CONSTRAINT uq_milestone_id_roadmap UNIQUE (id, roadmap_id)`.

### 1.9. Bảng `schedule_proposals` (Đề xuất Lịch trình Cấp 2)
| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ (BUSR) & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 (RFC 9562) | Khóa chính bản đề xuất. |
| `roadmap_id` | `UUID` | No | None | No | `roadmaps(id, user_id)`* | No | No | UUID tồn tại | Khóa ngoại phức hợp `(roadmap_id, user_id)` bảo đảm cùng chủ sở hữu. |
| `user_id` | `UUID` | No | None | No | `users(id)` | No | No | UUID tồn tại | Người sở hữu đề xuất (`ON DELETE CASCADE`). |
| `proposal_data` | `JSONB` | No | None | No | No | No | Yes** | Valid JSON Object Schema | `FR-PLAN-002`, `BUSR-02`. Mảng task dự thảo chưa qua Validation Gate. |
| `status` | `VARCHAR(20)` | No | `'DRAFT'` | No | No | Yes*** | Yes | `'DRAFT'`, `'APPLIED'`, `'DISCARDED'` | SRS Mục 6.4. Vòng đời đề xuất lịch. |
| `applied_at` | `TIMESTAMPTZ` | Yes | None | No | No | No | No | Dấu thời gian hoặc `NULL` | Thời điểm người dùng chấp nhận áp dụng đề xuất vào lịch chính thức. |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian | Thời điểm AI sinh đề xuất. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian | Thời điểm cập nhật đề xuất gần nhất (Trigger `trg_schedule_proposals_updated_at`). |

*\*Khóa ngoại phức hợp:* `CONSTRAINT fk_schedule_proposals_roadmap_user FOREIGN KEY (roadmap_id, user_id) REFERENCES roadmaps(id, user_id) ON DELETE CASCADE`.  
*\*\*Ràng buộc JSON:* `CONSTRAINT chk_proposal_data_json CHECK (jsonb_typeof(proposal_data) = 'object')`.  
*\*\*\*Ràng buộc duy nhất 1 bản nháp:* Partial Unique Index `uq_one_draft_per_roadmap` trên `(roadmap_id) WHERE status = 'DRAFT'`.

### 1.10. Bảng `official_schedules` (Lịch học Chính thức - Frozen Baseline)
| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ (BUSR) & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 (RFC 9562) | Khóa chính lịch chính thức. |
| `roadmap_id` | `UUID` | No | None | No | `roadmaps(id)` | Yes | No | UUID tồn tại | `BUSR-02`. Quan hệ 1:1 với Roadmap; đại diện lịch duy nhất có hiệu lực. |
| `total_sessions`| `INTEGER` | No | `0` | No | No | No | Yes | `>= 0` | Tổng số buổi học kế hoạch đóng băng (Frozen Baseline Planned Sessions). |
| `total_planned_minutes` | `INTEGER` | No | `0` | No | No | No | Yes | `>= 0` | Tổng số phút học kế hoạch đóng băng (Frozen Baseline Planned Minutes - loại bỏ sai số giờ nguyên). |
| `activated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian | Thời điểm vượt qua Validation Gate và bấm Apply (`FR-PLAN-003`). |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian | Thời điểm cập nhật lịch (Trigger `trg_official_schedules_updated_at`). |

### 1.11. Bảng `tasks` (Nhiệm vụ học tập chi tiết)
| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ (BUSR) & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 (RFC 9562) | Khóa chính bài học. |
| `roadmap_id` | `UUID` | No | None | No | `roadmaps(id)` | No | No | UUID tồn tại | Lộ trình chứa task (`ON DELETE CASCADE`). |
| `milestone_id` | `UUID` | No | None | No | `milestones(id, roadmap_id)` | No | No | UUID tồn tại | Khóa ngoại phức hợp đảm bảo task thuộc đúng Milestone của Roadmap. |
| `title` | `VARCHAR(255)` | No | None | No | No | No | No | Chuỗi văn bản | `FR-TASK-001`. Tên nhiệm vụ cụ thể. |
| `description` | `TEXT` | Yes | None | No | No | No | No | Văn bản | Hướng dẫn thực hiện, bài tập, checklist hoặc link tài liệu học. |
| `estimated_minutes` | `INTEGER` | No | None | No | No | No | Yes | `BETWEEN 15 AND 240` | `BUSR-03`. Thời lượng ước tính từ 15 đến 240 phút (chuẩn Pomodoro). |
| `scheduled_date`| `DATE` | Yes | None | No | No | No | No | YYYY-MM-DD hoặc `NULL` | Ngày học cụ thể. `NULL` đại diện task nằm trong **Backlog** (`BUSR-09`). |
| `start_time` | `TIME` | Yes | None | No | No | No | Yes* | HH:MM:SS | Giờ bắt đầu học (chỉ bắt buộc khi User dùng Mode B). |
| `end_time` | `TIME` | Yes | None | No | No | No | Yes* | HH:MM:SS | Giờ kết thúc học (chỉ bắt buộc khi User dùng Mode B). |
| `status` | `VARCHAR(20)` | No | `'TODO'` | No | No | No | Yes | `'PENDING'`, `'TODO'`, `'IN_PROGRESS'`, `'COMPLETED'`, `'CANCELLED'` | `BUSR-06`. Trạng thái thực hiện bền vững (PENDING: chờ duyệt; TODO: đã lên lịch; IN_PROGRESS; COMPLETED; CANCELLED). |
| `completed_at` | `TIMESTAMPTZ` | Yes | None | No | No | No | Yes** | Dấu thời gian hoặc `NULL` | Bắt buộc `NOT NULL` khi `COMPLETED`; bắt buộc `NULL` khi khác `COMPLETED`. |
| `reschedule_count`| `INTEGER` | No | `0` | No | No | No | Yes | `>= 0` | `FR-ADAPT-003`. Đếm số lần dời lịch liên tiếp; khi $\ge 3$ kích hoạt ngắt mạch Overdue Anti-Loop (STALLED). |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian | Thời điểm tạo task. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian | Thời điểm cập nhật task gần nhất (Trigger `trg_tasks_updated_at`). |

*\*Ràng buộc khung giờ & ngày học:* `CONSTRAINT chk_task_schedule_dates CHECK (scheduled_date IS NOT NULL OR (start_time IS NULL AND end_time IS NULL))` và `CONSTRAINT chk_task_time_window CHECK (start_time IS NULL OR end_time IS NULL OR start_time < end_time)`.  
*\*\*Ràng buộc logic hoàn thành:* `CHECK ((status = 'COMPLETED' AND completed_at IS NOT NULL) OR (status != 'COMPLETED' AND completed_at IS NULL))`.  
*\*\*\*Khóa duy nhất kết hợp:* `CONSTRAINT uq_tasks_id_roadmap UNIQUE (id, roadmap_id)` phục vụ khóa ngoại bảo vệ lộ trình cho `session_tasks`.

### 1.12. Bảng `study_sessions` (Phiên học tập trung)
| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ (BUSR) & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 (RFC 9562) | Khóa chính phiên học. |
| `user_id` | `UUID` | No | None | No | `users(id)` | Yes* | No | UUID tồn tại | Người tham gia học (`ON DELETE CASCADE`). |
| `roadmap_id` | `UUID` | No | None | No | `roadmaps(id, user_id)`* | No | No | UUID tồn tại | Khóa ngoại phức hợp `(roadmap_id, user_id)` bảo đảm cùng chủ sở hữu. |
| `started_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian | Thời điểm người học bấm Start Session (`FR-SESSION-001`). |
| `ended_at` | `TIMESTAMPTZ` | Yes | None | No | No | No | Yes** | Dấu thời gian hoặc `NULL` | Bắt buộc `NULL` khi đang học; bắt buộc có giá trị $\ge started\_at$ khi kết thúc. |
| `planned_minutes`| `INTEGER` | No | None | No | No | No | Yes | `> 0` | Thời lượng dự kiến của buổi học (tổng phút các task đã chọn). |
| `actual_minutes`| `INTEGER` | No | `0` | No | No | No | Yes | `>= 0` | `BUSR-09`. Thời gian thực học thực tế tích lũy qua các gói tin Heartbeat ping (phút). |
| `status` | `VARCHAR(20)` | No | `'IN_PROGRESS'` | No | No | No | Yes | `'IN_PROGRESS'`, `'COMPLETED'`, `'PARTIAL_COMPLETED'`, `'CANCELLED'` | `OS-01`, `BUSR-09`. Trạng thái phiên học. |
| `last_heartbeat_at`| `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian | `OS-07`. Thời điểm Client gửi tín hiệu Heartbeat ping gần nhất (chu kỳ 60s). |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian | Thời điểm khởi tạo bản ghi session. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian | Thời điểm cập nhật bản ghi session (Trigger `trg_study_sessions_updated_at`). |

*\*Khóa ngoại phức hợp & Bất biến đồng thời:* `CONSTRAINT fk_study_sessions_roadmap_user FOREIGN KEY (roadmap_id, user_id) REFERENCES roadmaps(id, user_id) ON DELETE CASCADE` và Partial Unique Index `uq_user_single_active_session` trên `(user_id) WHERE status = 'IN_PROGRESS'`.  
*\*\*Ràng buộc thời gian & trạng thái:* `CHECK (ended_at IS NULL OR ended_at >= started_at)` và `CHECK ((status = 'IN_PROGRESS' AND ended_at IS NULL) OR (status != 'IN_PROGRESS' AND ended_at IS NOT NULL))`.  
*\*\*\*Khóa duy nhất kết hợp:* `CONSTRAINT uq_study_sessions_id_roadmap UNIQUE (id, roadmap_id)` phục vụ khóa ngoại bảo vệ lộ trình cho `session_tasks`.

### 1.13. Bảng `session_tasks` (Liên kết N:M Phiên học - Nhiệm vụ)
| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ (BUSR) & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 (RFC 9562) | Khóa chính liên kết. |
| `session_id` | `UUID` | No | None | No | `study_sessions(id, roadmap_id)`*| Yes* | No | UUID tồn tại | Phiên học chứa task (`ON DELETE CASCADE`). |
| `task_id` | `UUID` | No | None | No | `tasks(id, roadmap_id)`* | Yes* | No | UUID tồn tại | Nhiệm vụ được học (`ON DELETE RESTRICT` - bảo toàn lịch sử học tập). |
| `roadmap_id` | `UUID` | No | None | No | `roadmaps(id)` | No | No | UUID tồn tại | Khóa ngoại liên kết lộ trình phục vụ kiểm soát toàn vẹn chéo. |
| `allocated_minutes` | `INTEGER` | No | `0` | No | No | No | Yes | `>= 0` | Thời lượng dự kiến phân bổ cho task này trong phiên học. |
| `is_completed_in_session` | `BOOLEAN` | No | `FALSE` | No | No | No | No | `TRUE`, `FALSE` | `BUSR-09`. Đánh dấu task đã được hoàn thành ngay trong phiên học này. |
| `time_spent_minutes` | `INTEGER` | No | `0` | No | No | No | Yes | `>= 0` | Số phút thực học thực tế phân bổ cho task này trong phiên. |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian | Thời điểm thêm task vào phiên. |

*\*Ràng buộc toàn vẹn tham chiếu kép:* `CONSTRAINT fk_session_tasks_session FOREIGN KEY (session_id, roadmap_id) REFERENCES study_sessions(id, roadmap_id) ON DELETE CASCADE` và `CONSTRAINT fk_session_tasks_task FOREIGN KEY (task_id, roadmap_id) REFERENCES tasks(id, roadmap_id) ON DELETE RESTRICT`. Ràng buộc `CONSTRAINT uq_session_task UNIQUE (session_id, task_id)` chặn gán trùng 1 task vào cùng 1 phiên.

### 1.14. Bảng `study_notes` (Ghi chép trong phiên học)
| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ (BUSR) & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 (RFC 9562) | Khóa chính ghi chép. |
| `session_id` | `UUID` | No | None | No | `study_sessions(id)`| Yes* | No | UUID tồn tại | Phiên học liên kết (`ON DELETE CASCADE`). |
| `note_type` | `VARCHAR(20)` | No | None | No | No | Yes* | Yes | `'SCRATCHPAD'`, `'TAKEAWAY'` | `FR-SESSION-002`. Phân loại: Nháp tự do hoặc Đúc kết trọng tâm. |
| `content` | `TEXT` | No | `''` | No | No | No | No | Văn bản | Nội dung ghi chép của người học trong Study Workspace. |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian | Thời điểm tạo ghi chú. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian | Thời điểm lưu nội dung gần nhất (Trigger `trg_study_notes_updated_at`). |

*\*Ràng buộc duy nhất phức hợp:* `CONSTRAINT uq_session_note_type UNIQUE (session_id, note_type)` giới hạn đúng 1 Scratchpad và 1 Takeaway/phiên.

### 1.15. Bảng `pause_records` (Lịch sử Tạm dừng & Dời lịch)
| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ (BUSR) & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 (RFC 9562) | Khóa chính bản ghi pause. |
| `roadmap_id` | `UUID` | No | None | No | `roadmaps(id)` | No | No | UUID tồn tại | Lộ trình được tạm dừng (`ON DELETE CASCADE`). |
| `pause_start_date`| `DATE` | No | None | No | No | No | No | YYYY-MM-DD | Ngày bắt đầu tạm dừng lộ trình. |
| `pause_end_date` | `DATE` | No | None | No | No | No | Yes* | YYYY-MM-DD | Ngày kết thúc tạm dừng. |
| `shifted_days` | `INTEGER` | No | None | No | No | No | Yes* | `> 0` | `FR-PAUSE-002`, `BUSR-07`. Số ngày lịch trình đã tịnh tiến lùi về sau. |
| `reason` | `TEXT` | Yes | None | No | No | No | No | Văn bản | Lý do tạm dừng (ví dụ: "Bận thi tốt nghiệp", "Ốm"). |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian | Thời điểm ghi nhận lệnh tạm dừng. |

*\*Ràng buộc thời gian & số ngày dời:* `CONSTRAINT chk_pause_dates CHECK (pause_end_date >= pause_start_date)` và `CONSTRAINT chk_pause_duration CHECK (shifted_days = (pause_end_date - pause_start_date + 1))`.

### 1.16. Bảng `ai_reviews` (Báo cáo & Phản tư từ AI)
| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ (BUSR) & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 (RFC 9562) | Khóa chính bản ghi review. |
| `roadmap_id` | `UUID` | No | None | No | `roadmaps(id, user_id)`* | No | No | UUID tồn tại | Khóa ngoại phức hợp `(roadmap_id, user_id)` bảo đảm cùng chủ sở hữu. |
| `user_id` | `UUID` | No | None | No | `users(id)` | No | No | UUID tồn tại | Người học nhận đánh giá (`ON DELETE CASCADE`). |
| `milestone_id` | `UUID` | Yes | None | No | `milestones(id)` | No | No | UUID tồn tại | Mốc kiến thức đánh giá (`ON DELETE CASCADE`, bắt buộc khi chu kỳ `MILESTONE`). |
| `review_cycle` | `VARCHAR(20)` | No | None | No | No | No | Yes | `'WEEKLY'`, `'MILESTONE'` | Chu kỳ đánh giá: Hàng tuần hoặc Sau mỗi cột mốc. |
| `period_start` | `DATE` | Yes | None | No | No | No | Yes** | YYYY-MM-DD | Ngày bắt đầu kỳ báo cáo (bắt buộc khi chu kỳ `WEEKLY`). |
| `period_end` | `DATE` | Yes | None | No | No | No | Yes** | YYYY-MM-DD | Ngày kết thúc kỳ báo cáo (bắt buộc khi chu kỳ `WEEKLY`). |
| `quantitative_summary`| `JSONB` | No | None | No | No | No | Yes*** | Valid JSON Summary | Dữ liệu thống kê toán học đã được làm sạch (Sanitized). |
| `strengths_feedback` | `TEXT` | No | None | No | No | No | No | Văn bản | Nhận xét định tính điểm mạnh và thành tựu đã đạt được. |
| `bottlenecks_feedback` | `TEXT` | No | None | No | No | No | No | Văn bản | Cảnh báo điểm nghẽn, các task trễ hạn hoặc học dở dang. |
| `action_recommendations`| `TEXT` | No | None | No | No | No | No | Văn bản | Đề xuất hành động điều chỉnh cụ thể cho chu kỳ tiếp theo. |
| `generated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian | `BUSR-12`. Thời điểm AI sinh nhận xét (Write-Once Snapshot). |

*\*Khóa ngoại phức hợp:* `CONSTRAINT fk_ai_reviews_roadmap_user FOREIGN KEY (roadmap_id, user_id) REFERENCES roadmaps(id, user_id) ON DELETE CASCADE`.  
*\*\*Ràng buộc chu kỳ:* `CONSTRAINT chk_ai_review_period CHECK ((review_cycle = 'MILESTONE' AND milestone_id IS NOT NULL AND period_start IS NULL AND period_end IS NULL) OR (review_cycle = 'WEEKLY' AND milestone_id IS NULL AND period_start IS NOT NULL AND period_end IS NOT NULL AND period_end >= period_start))`.  
*\*\*\*Ràng buộc JSON:* `CONSTRAINT chk_quantitative_summary_json CHECK (jsonb_typeof(quantitative_summary) = 'object')`.  
*\*\*\*\*Chống trùng lặp định kỳ:* Partial Unique Index `uq_ai_reviews_weekly` trên `(roadmap_id, period_start, period_end) WHERE review_cycle = 'WEEKLY'` và `uq_ai_reviews_milestone` trên `(roadmap_id, milestone_id) WHERE review_cycle = 'MILESTONE'`.

---

### 1.17. Bảng `task_dependencies` (Quan hệ Tiên quyết Nhiệm vụ)
| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ (BUSR) & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `predecessor_id` | `UUID` | No | None | Yes | `tasks(id, roadmap_id)` | No | Yes* | UUID tồn tại | Nhiệm vụ tiên quyết bắt buộc phải hoàn thành trước. |
| `successor_id` | `UUID` | No | None | Yes | `tasks(id, roadmap_id)` | No | Yes* | UUID tồn tại | Nhiệm vụ phụ thuộc, bị chặn Start Session nếu task trước chưa xong. |
| `roadmap_id` | `UUID` | No | None | No | `roadmaps(id)` | No | No | UUID tồn tại | Lộ trình chung chứa cả 2 task (đảm bảo không phụ thuộc chéo lộ trình). |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian | Thời điểm thiết lập quan hệ phụ thuộc. |

*\*Ràng buộc chống tự phụ thuộc:* `CONSTRAINT chk_no_self_dependency CHECK (predecessor_id <> successor_id)`. Chu trình đồ thị ($A \to B \to A$) được kiểm soát ở Domain Service (DFS Algorithm).

### 1.18. Bảng `learner_profiles` (Hồ sơ Thói quen Người học)
| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ (BUSR) & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `user_id` | `UUID` | No | None | Yes | `users(id)` | Yes | No | UUID tồn tại | Khóa chính và khóa ngoại quan hệ 1-1 với tài khoản người học. |
| `optimal_focus_duration_mins` | `INTEGER` | No | `25` | No | No | No | Yes | `BETWEEN 15 AND 120` | `FR-PROFILE-001`. Trung vị thời lượng Pomodoro thực tế (phút) hoàn thành tốt nhất. |
| `peak_productivity_slots` | `JSONB` | No | `'["MORNING", "EVENING"]'` | No | No | No | No | JSON Array of Strings | Khung giờ vàng có tỷ lệ hoàn thành cao nhất ($\ge 70\%$). |
| `estimation_bias_factor` | `NUMERIC(4,2)` | No | `1.00` | No | No | No | Yes | `BETWEEN 0.50 AND 2.00` | Hệ số chệch giữa thời gian thực tế và ước lượng ($T_{actual}/T_{estimated}$). |
| `weekly_completion_rate` | `NUMERIC(5,2)` | No | `0.00` | No | No | No | Yes | `BETWEEN 0.00 AND 100.00` | Tỷ lệ hoàn thành nhiệm vụ theo lịch trong tuần gần nhất. |
| `total_completed_sessions` | `INTEGER` | No | `0` | No | No | No | Yes | `>= 0` | Tổng số phiên Pomodoro hoàn thành thành công. |
| `is_cold_start` | `BOOLEAN` | No | `TRUE` | No | No | No | No | Boolean | Đánh dấu tài khoản chưa đủ dữ liệu tối thiểu ($< 5$ phiên học). |
| `last_aggregated_at` | `TIMESTAMPTZ` | Yes | `NOW()` | No | No | No | No | Dấu thời gian | Thời điểm Celery Worker chạy tổng hợp chỉ số gần nhất. |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian | Thời điểm khởi tạo hồ sơ. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian | Thời điểm cập nhật hồ sơ gần nhất. |

### 1.19. Bảng `schedule_change_logs` (Nhật ký Biến động Lịch trình)
| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ (BUSR) & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 (RFC 9562) | Khóa chính bản ghi audit log. |
| `roadmap_id` | `UUID` | No | None | No | `roadmaps(id)` | No | No | UUID tồn tại | Lộ trình chịu biến động lịch trình (`ON DELETE CASCADE`). |
| `task_id` | `UUID` | Yes | None | No | `tasks(id)` | No | No | UUID tồn tại hoặc `NULL` | Nhiệm vụ cụ thể bị tác động (`ON DELETE SET NULL`). |
| `actor_type` | `VARCHAR(20)` | No | None | No | No | No | Yes | `'USER'`, `'SYSTEM_ADAPT'`, `'SYSTEM_DOMINO'`, `'AI_PROPOSAL'` | Tác nhân gây biến động lịch. |
| `action` | `VARCHAR(50)` | No | None | No | No | No | No | Chuỗi hành động | Loại biến động: `'RESCHEDULE'`, `'DOMINO_SHIFT'`, `'STALL_TRIGGERED'`, v.v. |
| `old_value` | `JSONB` | Yes | None | No | No | No | No | JSON | Giá trị ngày/giờ trước khi thay đổi. |
| `new_value` | `JSONB` | Yes | None | No | No | No | No | JSON | Giá trị ngày/giờ sau khi thay đổi. |
| `reason` | `TEXT` | Yes | None | No | No | No | No | Văn bản | Lý do thay đổi hoặc ghi chú hệ thống. |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian | Thời điểm phát sinh sự kiện thay đổi. |

---

## 2. Ma trận Ràng buộc Toàn vẹn (Constraint Matrix)

Ma trận dưới đây tổng hợp toàn bộ 48 ràng buộc toàn vẹn có tên (Named Constraints) và ràng buộc khóa trong PostgreSQL 16 của FocusFlow, giải thích rõ Bất biến Nghiệp vụ (Business Invariant) được bảo vệ:

| Tên Ràng buộc (Constraint Name) | Bảng Sở hữu | Loại Ràng buộc | Định nghĩa Kỹ thuật trong DDL | Bất biến Nghiệp vụ Được Bảo vệ |
|---|---|---|---|---|
| `users_pkey` | `users` | Primary Key | `PRIMARY KEY (id)` | Đảm bảo tính duy nhất thực thể người dùng, chống ID Enumeration. |
| `users_email_key` | `users` | Unique Key | `UNIQUE (email)` | Chống trùng lặp tài khoản đăng ký trên hệ thống. |
| `uq_users_lower_email` | `users` | Unique Index | `CREATE UNIQUE INDEX ON users (LOWER(email))` | Đảm bảo email duy nhất không phân biệt hoa thường. |
| `webcal_tokens_pkey` | `webcal_tokens` | Primary Key | `PRIMARY KEY (id)` | Định danh bản ghi token. |
| `webcal_tokens_user_id_key` | `webcal_tokens` | Unique Key | `UNIQUE (user_id)` | `OS-05`. Mỗi User chỉ sở hữu duy nhất 1 WebCal token đang hiệu lực. |
| `webcal_tokens_token_hash_key` | `webcal_tokens` | Unique Key | `UNIQUE (token_hash)` | Ngăn chặn va chạm bản băm token, bảo mật feed ICS. |
| `chk_webcal_token_hash` | `webcal_tokens` | Check | `CHECK (token_hash ~ '^[0-9a-f]{64}$')` | Kiểm tra định dạng bản băm SHA-256 đúng chuẩn 64 ký tự hex. |
| `ai_quotas_pkey` | `ai_quotas` | Primary Key | `PRIMARY KEY (id)` | Định danh bản ghi hạn ngạch. |
| `ai_quotas_user_id_key` | `ai_quotas` | Unique Key | `UNIQUE (user_id)` | Mỗi User chỉ có 1 chu kỳ hạn ngạch kích hoạt đồng thời. |
| `chk_ai_quota_limit` | `ai_quotas` | Check | `CHECK (used_calls + reserved_calls <= monthly_limit)` | `BUSR-10`. Chặn race condition gọi vượt trần hạn ngạch AI tại mức CSDL. |
| `chk_ai_quota_cycle` | `ai_quotas` | Check | `CHECK (cycle_end > cycle_start)` | Đảm bảo khoảng thời gian chu kỳ tính cước luôn hợp lệ. |
| `ai_quota_reservations_pkey` | `ai_quota_reservations` | Primary Key | `PRIMARY KEY (id)` | Định danh bản ghi giữ chỗ hạn ngạch AI. |
| `fk_quota_reservations_user` | `ai_quota_reservations` | Foreign Key | `FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE` | Toàn vẹn người dùng giữ chỗ quota. |
| `availabilities_pkey` | `availabilities` | Primary Key | `PRIMARY KEY (id)` | Định danh bản ghi thời gian rảnh. |
| `availabilities_user_id_key` | `availabilities` | Unique Key | `UNIQUE (user_id)` | Mỗi User chỉ có duy nhất 1 cấu hình quỹ thời gian rảnh. |
| `chk_availabilities_schedule_json` | `availabilities` | Check | `CHECK (jsonb_typeof(weekly_schedule) = 'object')` | Kiểm tra lịch rảnh tuần phải là JSON Object hợp lệ. |
| `goals_pkey` | `goals` | Primary Key | `PRIMARY KEY (id)` | Định danh mục tiêu học tập. |
| `fk_goals_user` | `goals` | Foreign Key | `FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE` | Toàn vẹn người sở hữu mục tiêu; xóa User sẽ xóa toàn bộ Goals. |
| `uq_goals_id_user` | `goals` | Unique Key | `UNIQUE (id, user_id)` | Siêu khóa bảo đảm tính toàn vẹn đa thực thể cùng chủ sở hữu. |
| `roadmaps_pkey` | `roadmaps` | Primary Key | `PRIMARY KEY (id)` | Định danh lộ trình học tập. |
| `fk_roadmaps_user` | `roadmaps` | Foreign Key | `FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE` | Toàn vẹn người sở hữu lộ trình. |
| `uq_roadmaps_id_user` | `roadmaps` | Unique Key | `UNIQUE (id, user_id)` | Siêu khóa bảo vệ toàn vẹn đa thực thể cùng chủ sở hữu. |
| `fk_roadmaps_goal_user` | `roadmaps` | Foreign Key (Composite) | `FOREIGN KEY (goal_id, user_id) REFERENCES goals(id, user_id) ON DELETE NO ACTION` | Ngăn chặn việc xóa Goal gốc khi đang có các lộ trình phụ thuộc mà không làm đứt chuỗi Cascade xóa User. |
| `chk_roadmap_dates` | `roadmaps` | Check | `CHECK (target_date IS NULL OR start_date IS NULL OR target_date >= start_date)` | Đảm bảo ngày đích của lộ trình không sớm hơn ngày bắt đầu. |
| `milestones_pkey` | `milestones` | Primary Key | `PRIMARY KEY (id)` | Định danh mốc kiến thức Cấp 1. |
| `fk_milestones_roadmap` | `milestones` | Foreign Key | `FOREIGN KEY (roadmap_id) REFERENCES roadmaps(id) ON DELETE CASCADE` | Xóa lộ trình sẽ tự động dọn dẹp các mốc tương ứng. |
| `uq_milestone_roadmap_sequence` | `milestones` | Unique Key (Deferrable) | `UNIQUE (roadmap_id, sequence_order) DEFERRABLE INITIALLY DEFERRED` | `BUSR-02`. Thứ tự mốc kiến thức không trùng nhau; cho phép swap thứ tự trong transaction. |
| `uq_milestone_id_roadmap` | `milestones` | Unique Key | `UNIQUE (id, roadmap_id)` | Tạo siêu khóa phục vụ khóa ngoại phức hợp từ `tasks`. |
| `schedule_proposals_pkey` | `schedule_proposals`| Primary Key | `PRIMARY KEY (id)` | Định danh bản đề xuất lịch Cấp 2. |
| `fk_schedule_proposals_roadmap_user` | `schedule_proposals`| Foreign Key (Composite) | `FOREIGN KEY (roadmap_id, user_id) REFERENCES roadmaps(id, user_id) ON DELETE CASCADE` | Tự động xóa các bản dự thảo khi lộ trình bị xóa; bảo đảm cùng chủ sở hữu. |
| `uq_one_draft_per_roadmap` | `schedule_proposals` | Unique Partial Index | `UNIQUE (roadmap_id) WHERE status = 'DRAFT'` | Mỗi lộ trình tại một thời điểm chỉ có tối đa 1 bản nháp đề xuất chưa duyệt. |
| `chk_proposal_data_json` | `schedule_proposals` | Check | `CHECK (jsonb_typeof(proposal_data) = 'object')` | Kiểm tra dữ liệu đề xuất lịch phải là JSON Object. |
| `official_schedules_pkey` | `official_schedules`| Primary Key | `PRIMARY KEY (id)` | Định danh bản ghi lịch chính thức. |
| `official_schedules_roadmap_id_key` | `official_schedules`| Unique Key | `UNIQUE (roadmap_id)` | `BUSR-02`. Mỗi Roadmap chỉ có duy nhất 1 bộ lịch chính thức hiệu lực. |
| `fk_official_schedules_roadmap` | `official_schedules`| Foreign Key | `FOREIGN KEY (roadmap_id) REFERENCES roadmaps(id) ON DELETE CASCADE` | Xóa lộ trình sẽ xóa lịch chính thức tương ứng. |
| `tasks_pkey` | `tasks` | Primary Key | `PRIMARY KEY (id)` | Định danh nhiệm vụ học tập Cấp 2. |
| `uq_tasks_id_roadmap` | `tasks` | Unique Key | `UNIQUE (id, roadmap_id)` | Khóa kết hợp duy nhất phục vụ liên kết bảo vệ lộ trình cho `session_tasks`. |
| `fk_tasks_roadmap` | `tasks` | Foreign Key | `FOREIGN KEY (roadmap_id) REFERENCES roadmaps(id) ON DELETE CASCADE` | Xóa lộ trình sẽ dọn dẹp toàn bộ các task liên thuộc. |
| `fk_tasks_milestone_roadmap` | `tasks` | Foreign Key (Composite) | `FOREIGN KEY (milestone_id, roadmap_id) REFERENCES milestones(id, roadmap_id) ON DELETE CASCADE` | **Chặn đứng 100% nguy cơ gán task vào milestone của Roadmap khác**. |
| `chk_task_schedule_dates` | `tasks` | Check | `CHECK (scheduled_date IS NOT NULL OR (start_time IS NULL AND end_time IS NULL))` | Không cho phép có khung giờ bắt đầu/kết thúc khi task chưa xếp ngày. |
| `chk_task_time_window` | `tasks` | Check | `CHECK (start_time IS NULL OR end_time IS NULL OR start_time < end_time)` | Đảm bảo giờ bắt đầu luôn trước giờ kết thúc khi xếp lịch Mode B. |
| `chk_task_completed_at` | `tasks` | Check | `CHECK ((status = 'COMPLETED' AND completed_at IS NOT NULL) OR (status != 'COMPLETED' AND completed_at IS NULL))` | `INV_TK_01`. Cưỡng chế dấu thời gian hoàn thành logic đồng bộ với status. |
| `study_sessions_pkey` | `study_sessions` | Primary Key | `PRIMARY KEY (id)` | Định danh phiên học tập trung. |
| `uq_study_sessions_id_roadmap` | `study_sessions` | Unique Key | `UNIQUE (id, roadmap_id)` | Khóa kết hợp duy nhất phục vụ liên kết bảo vệ lộ trình cho `session_tasks`. |
| `fk_study_sessions_roadmap_user` | `study_sessions` | Foreign Key (Composite) | `FOREIGN KEY (roadmap_id, user_id) REFERENCES roadmaps(id, user_id) ON DELETE CASCADE` | Bảo đảm phiên học và lộ trình cùng thuộc một chủ sở hữu. |
| `uq_user_single_active_session` | `study_sessions` | Unique Partial Index | `UNIQUE (user_id) WHERE status = 'IN_PROGRESS'` | `INV_SS_01`. Mỗi User chỉ có tối đa 1 session IN_PROGRESS cùng lúc. |
| `chk_session_times` | `study_sessions` | Check | `CHECK (ended_at IS NULL OR ended_at >= started_at)` | Thời điểm kết thúc phiên không được sớm hơn thời điểm bắt đầu. |
| `chk_session_status_ended` | `study_sessions` | Check | `CHECK ((status = 'IN_PROGRESS' AND ended_at IS NULL) OR (status != 'IN_PROGRESS' AND ended_at IS NOT NULL))` | `INV_SS_03`. Phiên đóng bắt buộc có `ended_at`; phiên mở bắt buộc `NULL`. |
| `session_tasks_pkey` | `session_tasks` | Primary Key | `PRIMARY KEY (id)` | Định danh liên kết giữa phiên học và task. |
| `fk_session_tasks_session` | `session_tasks` | Foreign Key (Composite) | `FOREIGN KEY (session_id, roadmap_id) REFERENCES study_sessions(id, roadmap_id) ON DELETE CASCADE` | Chặn đứng 100% nguy cơ gán nhầm sang session khác roadmap. |
| `fk_session_tasks_task` | `session_tasks` | Foreign Key (Composite) | `FOREIGN KEY (task_id, roadmap_id) REFERENCES tasks(id, roadmap_id) ON DELETE RESTRICT` | **Bảo toàn lịch sử học tập** — ngăn chặn việc xóa cứng các task đã có phiên học ghi nhận. |
| `uq_session_task` | `session_tasks` | Unique Key | `UNIQUE (session_id, task_id)` | Ngăn chặn việc đưa 1 task 2 lần vào cùng 1 phiên học. |
| `study_notes_pkey` | `study_notes` | Primary Key | `PRIMARY KEY (id)` | Định danh ghi chép học tập. |
| `uq_session_note_type` | `study_notes` | Unique Key | `UNIQUE (session_id, note_type)` | Giới hạn 1 Scratchpad và 1 Takeaway duy nhất cho mỗi phiên học. |
| `pause_records_pkey` | `pause_records` | Primary Key | `PRIMARY KEY (id)` | Định danh bản ghi tạm dừng. |
| `chk_pause_dates` | `pause_records` | Check | `CHECK (pause_end_date >= pause_start_date)` | Ngày kết thúc tạm dừng phải $\ge$ ngày bắt đầu tạm dừng. |
| `chk_pause_duration` | `pause_records` | Check | `CHECK (shifted_days = (pause_end_date - pause_start_date + 1))` | Ràng buộc toán học đảm bảo số ngày dời lịch khớp chính xác độ dài khoảng ngày tạm dừng. |
| `ai_reviews_pkey` | `ai_reviews` | Primary Key | `PRIMARY KEY (id)` | Định danh bản ghi báo cáo AI Review. |
| `fk_ai_reviews_roadmap_user` | `ai_reviews` | Foreign Key (Composite) | `FOREIGN KEY (roadmap_id, user_id) REFERENCES roadmaps(id, user_id) ON DELETE CASCADE` | Bảo đảm báo cáo AI và lộ trình cùng thuộc một chủ sở hữu. |
| `chk_ai_review_period` | `ai_reviews` | Check | `CHECK ((review_cycle = 'MILESTONE' AND milestone_id IS NOT NULL AND period_start IS NULL AND period_end IS NULL) OR (review_cycle = 'WEEKLY' AND milestone_id IS NULL AND period_start IS NOT NULL AND period_end IS NOT NULL AND period_end >= period_start))` | Ràng buộc logic phân định chu kỳ đánh giá MILESTONE vs WEEKLY. |
| `chk_quantitative_summary_json` | `ai_reviews` | Check | `CHECK (jsonb_typeof(quantitative_summary) = 'object')` | Kiểm tra tóm tắt định lượng phải là JSON Object. |
| `uq_ai_reviews_weekly` | `ai_reviews` | Unique Partial Index | `UNIQUE (roadmap_id, period_start, period_end) WHERE review_cycle = 'WEEKLY'` | Chống tạo trùng báo cáo tuần khi Celery retry. |
| `uq_ai_reviews_milestone` | `ai_reviews` | Unique Partial Index | `UNIQUE (roadmap_id, milestone_id) WHERE review_cycle = 'MILESTONE'` | Chống tạo trùng báo cáo mốc khi Celery retry. |

---

## 3. Ma trận Chỉ mục Hiệu năng (Index Matrix - Access Pattern Traceability)

Tất cả 24 chỉ mục tối ưu trong hệ thống được thiết kế dựa trên các **Mẫu truy vấn (Access Patterns)** thực tế của Use Case và Repository, loại bỏ hoàn toàn các chỉ mục dư thừa hoặc trùng lặp tiền tố:

| Tên Chỉ mục (Index Name) | Bảng Sở hữu | Cột được Đánh chỉ mục | Loại Chỉ mục | Duy nhất (UQ) | Mẫu Truy vấn & Use Case Hỗ trợ | Phân tích Tính Chọn lọc (Selectivity) & Overhead |
|---|---|---|---|---|---|---|
| `users_pkey` | `users` | `(id)` | B-Tree | Yes | Tra cứu người dùng theo JWT claims (`user_id`). | Selectivity: 1.0 (Tuyệt đối). Overhead: Chuẩn PK. |
| `users_email_key` | `users` | `(email)` | B-Tree | Yes | `FR-AUTH-001`. Đăng nhập hệ thống (`WHERE email = :email`). | Selectivity: 1.0. Tần suất đọc cao khi xác thực. |
| `uq_users_lower_email` | `users` | `(lower(email))` | B-Tree Expression | Yes | Đăng nhập và đăng ký không phân biệt hoa thường (`WHERE lower(email) = lower(:email)`). | Selectivity: 1.0. Chống tạo tài khoản trùng biến thể hoa thường. |
| `webcal_tokens_token_hash_key` | `webcal_tokens` | `(token_hash)` | B-Tree | Yes | `FR-CALENDAR-002`. Xuất WebCal Feed 1 chiều từ ứng dụng lịch ngoại vi. | Selectivity: 1.0. Truy vấn trực tiếp từ URL không qua Cookie. |
| `uq_user_single_active_session` | `study_sessions` | `(user_id)` | B-Tree Partial | Yes | `FR-SESSION-001`. Kiểm tra người dùng có session nào đang chạy không (`WHERE user_id = :uid AND status = 'IN_PROGRESS'`). | Kích thước cực nhỏ (chỉ chứa các dòng `IN_PROGRESS`). Write Overhead tối thiểu. |
| `uq_one_draft_per_roadmap` | `schedule_proposals` | `(roadmap_id)` | B-Tree Partial | Yes | `FR-PLAN-002`. Bất biến duy nhất 1 bản nháp đề xuất cho mỗi lộ trình (`WHERE roadmap_id = :rid AND status = 'DRAFT'`). | Selectivity cao. Kích thước cực nhỏ (chỉ chứa các dòng DRAFT). |
| `uq_ai_reviews_weekly` | `ai_reviews` | `(roadmap_id, period_start, period_end)` | B-Tree Partial | Yes | `FR-REPORT-002`. Chống tạo trùng báo cáo đánh giá tuần khi Celery Worker retry thất bại mạng. | Idempotency tuyệt đối cho background job. |
| `uq_ai_reviews_milestone` | `ai_reviews` | `(roadmap_id, milestone_id)` | B-Tree Partial | Yes | `FR-REPORT-002`. Chống tạo trùng báo cáo đánh giá mốc khi Celery Worker retry. | Idempotency tuyệt đối cho background job. |
| `idx_study_sessions_user_started` | `study_sessions` | `(user_id, started_at DESC)` | B-Tree Composite | No | `FR-SESSION-002`, `FR-REPORT-001`. Tải lịch sử phiên học và vẽ biểu đồ học tập trên Dashboard theo thứ tự mới nhất. | Tối ưu hóa tuyệt đối phép sắp xếp (`ORDER BY started_at DESC LIMIT 20`), loại bỏ thao tác Sort trên RAM. |
| `idx_roadmaps_user_status` | `roadmaps` | `(user_id, status)` | B-Tree Composite | No | `FR-PLAN-001`, `FR-AVAIL-003`. Lọc nhanh các lộ trình đang hoạt động (`WHERE user_id = :uid AND status IN ('ACTIVE', 'PAUSED')`). | Giúp kiểm tra hạn ngạch Roadmap đồng thời (Free=3, Premium=15) theo `OS-02`. |
| `idx_tasks_roadmap_scheduled_date` | `tasks` | `(roadmap_id, scheduled_date)` | B-Tree Composite | No | `FR-TASK-001`, `FR-PAUSE-002`. Hiển thị lịch học trong tháng và thực thi giải thuật Domino Shift (`WHERE roadmap_id = :rid AND scheduled_date >= :date`). | Tần suất truy vấn cao nhất hệ thống; loại bỏ thao tác Filter tuần tự. |
| `idx_tasks_overdue` | `tasks` | `(scheduled_date)` | B-Tree Partial | No | `FR-ADAPT-001`, `ADR-004`. Celery Beat quét lúc 00:01 gắn cờ task quá hạn (`WHERE status IN ('PENDING', 'TODO') AND scheduled_date IS NOT NULL`). | Chỉ lập chỉ mục task chưa hoàn thành có ngày lên lịch. Rất nhẹ và tốc độ quét $\le 5$ms. |
| `idx_study_sessions_in_progress` | `study_sessions` | `(last_heartbeat_at)` | B-Tree Partial | No | `OS-07`, `ADR-004`. Celery Beat quét mỗi 5 phút chốt phiên mất mạng (`WHERE status = 'IN_PROGRESS' AND last_heartbeat_at < NOW() - 5m`). | Chỉ quét các phiên học đang mở; không bao giờ quét các phiên đã đóng. |
| `idx_quota_reservations_cleanup` | `ai_quota_reservations` | `(expires_at)` | B-Tree Partial | No | `BUSR-10`, `OS-02`. Background Sweeper định kỳ quét và hoàn trả các phiên giữ chỗ quota bị hết hạn. | Kích thước cực nhỏ (chỉ chứa các dòng RESERVED). Quét cực nhanh. |
| `idx_quota_reservations_user_id` | `ai_quota_reservations` | `(user_id)` | B-Tree | No | `FR-QUOTA-001`. Bảo vệ Cascade Delete khi xóa User và tra cứu lịch sử reservation của người dùng. | Hỗ trợ xóa User không bị Sequential Scan. |
| `idx_schedule_proposals_roadmap_status` | `schedule_proposals` | `(roadmap_id, status)` | B-Tree Composite | No | `FR-PLAN-003`. Tìm bản dự thảo lịch trình gần nhất để người học bấm Apply (`WHERE roadmap_id = :rid AND status = 'DRAFT'`). | Tăng tốc độ hiển thị Preview Proposal màn hình M2. |
| `idx_ai_reviews_roadmap_cycle` | `ai_reviews` | `(roadmap_id, review_cycle, generated_at DESC)` | B-Tree Composite | No | `FR-REPORT-002`. Lấy nhận xét phản tư mới nhất của tuần hoặc mốc (`ORDER BY generated_at DESC LIMIT 1`). | Tối ưu hóa tải báo cáo tuần mà không cần quét toàn bảng. |
| `idx_study_sessions_roadmap_started` | `study_sessions` | `(roadmap_id, started_at DESC)` | B-Tree Composite | No | `FR-REPORT-001`. Tính tổng thời gian thực học tích lũy theo từng Roadmap sắp xếp theo thời gian và bảo vệ Cascade Delete. | Ngăn chặn Sequential Scan khi Roadmap có hàng trăm phiên học. |
| `idx_session_tasks_task_id` | `session_tasks` | `(task_id)` | B-Tree | No | `FR-TASK-001`, `BUSR-09`. Kiểm tra task đã được học trong các phiên nào và hỗ trợ Cascade Delete khi người dùng xóa task. | Giải quyết điểm nghẽn khóa ngoại chiều ngược trong quan hệ N:M. |
| `idx_session_tasks_roadmap_id` | `session_tasks` | `(roadmap_id)` | B-Tree | No | `FR-SESSION-002`, Cascade Delete. Tra cứu task theo roadmap và tối ưu các phép JOIN composite. | Bảo vệ Cascade Delete và tối ưu hóa truy vấn lọc theo lộ trình. |
| `idx_tasks_milestone_roadmap` | `tasks` | `(milestone_id, roadmap_id)` | B-Tree Composite | No | `FR-PLAN-001`. Tối ưu truy vấn task theo mốc và lộ trình; bảo vệ Cascade Delete khi xóa mốc. | Che phủ chính xác composite FK `(milestone_id, roadmap_id)`. |
| `idx_goals_user_id` | `goals` | `(user_id)` | B-Tree | No | `FR-GOAL-001`, Cascade Delete. Tra cứu danh sách mục tiêu của người học. | Bảo vệ Cascade Delete khi xóa User. |
| `idx_roadmaps_goal_id` | `roadmaps` | `(goal_id)` | B-Tree | No | `FR-PLAN-001`. Tối ưu kiểm tra khóa ngoại khi truy vấn lộ trình theo mục tiêu. | Che phủ FK goal_id. |
| `idx_schedule_proposals_user_id` | `schedule_proposals`| `(user_id)` | B-Tree | No | `FR-PLAN-002`, Cascade Delete. Tra cứu các bản đề xuất theo người dùng. | Bảo vệ Cascade Delete khi xóa User. |
| `idx_pause_records_roadmap_id` | `pause_records` | `(roadmap_id)` | B-Tree | No | `FR-PAUSE-002`, Cascade Delete. Lấy lịch sử các lần tạm dừng của lộ trình. | Bảo vệ Cascade Delete khi xóa Roadmap. |
| `idx_ai_reviews_user_id` | `ai_reviews` | `(user_id)` | B-Tree | No | `FR-REPORT-002`, Cascade Delete. Tra cứu danh sách báo cáo AI của người dùng. | Bảo vệ Cascade Delete khi xóa User. |
| `idx_ai_reviews_milestone_id` | `ai_reviews` | `(milestone_id)` | B-Tree | No | `FR-REPORT-002`, Cascade Delete. Tra cứu báo cáo AI gắn với milestone và bảo vệ Cascade Delete. | Bảo vệ Cascade Delete khi xóa Milestone. |

---

## 4. Kiểm toán Tính nhất quán Toàn chuỗi (End-to-End Consistency Audit)

Thực hiện đối soát nghiêm ngặt theo chuỗi phụ thuộc:
$$\text{DB Diagram} \longleftrightarrow \text{Migration} \longleftrightarrow \text{Entity/Model} \longleftrightarrow \text{Repository} \longleftrightarrow \text{Data Dictionary}$$

### 4.1. Kết quả Đối chiếu Chi tiết
1. **DB Diagram ↔ Data Dictionary:**
   * 16/16 bảng và toàn bộ các cột, kiểu dữ liệu, khóa chính, khóa ngoại, ràng buộc CHECK và UNIQUE hoàn toàn khớp nhau $100\%$.
   * Không còn bất kỳ trường thừa hay bảng mồ côi nào.
2. **Data Dictionary ↔ Database Schema DDL (`schema.sql`):**
   * Các kiểu dữ liệu vật lý (`UUID`, `VARCHAR`, `TIMESTAMPTZ`, `JSONB`, `DATE`, `TIME`, `BIGINT`) khớp chính xác $100\%$.
   * Cú pháp sinh khóa chính ANSI `gen_random_uuid()` đã đồng bộ đồng nhất trên toàn bộ 16 bảng.
   * Toàn bộ 12 trigger `set_updated_at()` và các composite foreign keys `(goal_id, user_id)`, `(roadmap_id, user_id)`, `(milestone_id, roadmap_id)` đã được ghi nhận đầy đủ.
3. **Chỉ mục Hiệu năng (Indexes) ↔ Use Case / Access Patterns:**
   * Toàn bộ 24 chỉ mục tối ưu có tên đều có lý do nghiệp vụ thực chứng gắn trực tiếp với mã yêu cầu `FR` và quyết định mở `OS`.
   * Đã loại bỏ chỉ mục dư thừa `idx_ai_quotas_user_cycle` do `user_id` đã có Unique constraint.
   * Tối ưu hóa `idx_tasks_milestone_roadmap` che phủ composite FK kép và `idx_study_sessions_roadmap_started` che phủ sorting dashboard.
4. **Hiện trạng Mã nguồn Thực thi (`src/`):**
   * Do dự án đang ở giai đoạn đóng băng thiết kế kiến trúc và mô hình dữ liệu (Milestone M2), thư mục `src/` hiện chưa khởi tạo file vật lý (chưa có file Alembic migration hay SQLAlchemy model code).
   * **Đánh giá rủi ro:** Không có hiện tượng Lệch pha Mã nguồn (Code Drift). Toàn bộ hồ sơ CSDL tại `docs/database/` và `docs/uml/` đã sẵn sàng làm chuẩn đầu vào tuyệt đối chính xác cho giai đoạn sinh mã nguồn ORM và Migrations tiếp theo.
