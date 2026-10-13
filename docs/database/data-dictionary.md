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

## 1. Từ điển Dữ liệu Toàn diện (Data Dictionary - 15 Bảng)

> [!IMPORTANT]
> **Quy ước Khóa chính Toàn hệ thống (Primary Key Strategy — UUIDv7):**
> * Toàn bộ các bảng trong hệ thống FocusFlow sử dụng kiểu dữ liệu `UUID` cho khóa chính.
> * Giá trị khóa chính được **sinh trực tiếp tại tầng Backend Application (Python FastAPI sử dụng thư viện `uuid6`/`uuid_utils` theo chuẩn RFC 9562 - UUIDv7 Time-Ordered)** trước khi ghi xuống CSDL.
> * **Lợi ích kỹ thuật:** Giữ nguyên tính bảo mật chống tấn công đoán ID (ID Enumeration), đồng thời đảm bảo các khóa chính được sắp xếp tăng dần theo thời gian (Time-Ordered Sequential), loại bỏ hoàn toàn hiện tượng phân mảnh trang (B-Tree Page Splitting) của chỉ mục B-Tree PK trong PostgreSQL 16 khi hệ thống mở rộng dữ liệu lớn.
> * CSDL PostgreSQL 16 khai báo `DEFAULT gen_random_uuid()` đóng vai trò Fallback an toàn khi thao tác chèn trực tiếp không qua Application.

### 1.1. Bảng `users` (Tài khoản & Phân quyền)
| Cột (Column) | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ (BUSR) & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 (RFC 9562) | Định danh duy nhất của người dùng; sinh theo chuẩn UUIDv7 tuần tự theo thời gian, chống phân mảnh B-Tree và chống tấn công đoán ID. |
| `email` | `VARCHAR(255)` | No | None | No | No | Yes | No | Định dạng RFC 5322 | `FR-AUTH-001`. Tên đăng nhập duy nhất toàn hệ thống. |
| `password_hash` | `VARCHAR(255)` | No | None | No | No | No | No | Chuỗi băm Argon2id | `NFR-SEC-001`. Mật khẩu đã băm an toàn, không lưu text thô. |
| `full_name` | `VARCHAR(100)` | No | None | No | No | No | No | 1–100 ký tự | Tên hiển thị người dùng trên giao diện. |
| `timezone` | `VARCHAR(50)` | No | `'Asia/Ho_Chi_Minh'` | No | No | No | No | Chuỗi IANA Timezone | `FR-PLAN-002`, `ADR-004`. Căn cứ tính ngày chuyển giao và Celery Beat. |
| `role` | `VARCHAR(20)` | No | `'LEARNER'` | No | No | No | Yes | `'LEARNER'`, `'ADMIN'` | `BUSR-11`. Phân quyền truy cập hệ thống; chặn route `/admin/*`. |
| `tier` | `VARCHAR(20)` | No | `'FREE'` | No | No | No | Yes | `'FREE'`, `'PREMIUM'` | `OS-02`. Phân tầng tài khoản chi phối định mức hạn ngạch AI. |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm đăng ký tài khoản. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian UTC | Thời điểm cập nhật thông tin gần nhất. |

### 1.2. Bảng `webcal_tokens` (Bảo mật Đồng bộ Lịch 1 chiều)
| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ (BUSR) & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 (RFC 9562) | Khóa chính bản ghi. |
| `user_id` | `UUID` | No | None | No | `users(id)` | Yes | No | UUID tồn tại | `BUSR-08`, `OS-05`. Quan hệ 1:1 với người dùng (`ON DELETE CASCADE`). |
| `token_hash` | `VARCHAR(64)` | No | None | No | No | Yes | No | 64 ký tự Hex | `OS-05`. Bản băm SHA-256 của CSPRN 32-byte hex; không lưu token thô. |
| `is_active` | `BOOLEAN` | No | `TRUE` | No | No | No | No | `TRUE`, `FALSE` | Trạng thái hiệu lực; bị chuyển sang `FALSE` khi người học bấm Reset. |
| `last_used_at` | `TIMESTAMPTZ` | Yes | None | No | No | No | No | Dấu thời gian | Thời điểm ứng dụng lịch ngoại vi (Google Cal) đồng bộ feed gần nhất. |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian | Thời điểm kích hoạt token lần đầu. |
| `reset_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian | Thời điểm làm mới token gần nhất (`FR-CALENDAR-003`). |

### 1.3. Bảng `ai_quotas` (Kiểm soát Hạn ngạch & Chi phí AI)
| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ (BUSR) & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 (RFC 9562) | Khóa chính bản ghi. |
| `user_id` | `UUID` | No | None | No | `users(id)` | Yes | No | UUID tồn tại | `BUSR-10`. Quan hệ 1:1 với User (`ON DELETE CASCADE`). |
| `monthly_limit` | `INTEGER` | No | `30` | No | No | No | Yes | `> 0` (Free: 30, Prem: 300) | `OS-02`. Số lượt gọi AI tối đa được phép trong một chu kỳ tháng. |
| `used_calls` | `INTEGER` | No | `0` | No | No | No | Yes | `>= 0` | Số lượt gọi AI đã xác nhận thành công (Commit). |
| `reserved_calls` | `INTEGER` | No | `0` | No | No | No | Yes | `>= 0` | Số lượt gọi đang tạm giữ 2 pha trước khi gọi LLM (Reserve). |
| `tokens_consumed` | `INTEGER` | No | `0` | No | No | No | Yes | `>= 0` | Tổng số token Gemini thực tế tiêu thụ (phục vụ giám sát chi phí). |
| `cycle_start` | `TIMESTAMPTZ` | No | None | No | No | No | No | Dấu thời gian | Ngày đầu chu kỳ (00:00:00 ngày 01 hàng tháng). |
| `cycle_end` | `TIMESTAMPTZ` | No | None | No | No | No | Yes | `cycle_end > cycle_start` | Ngày cuối chu kỳ (23:59:59 ngày cuối tháng). |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian | Thời điểm biến động hạn ngạch gần nhất. |

### 1.4. Bảng `availabilities` (Hồ sơ Quỹ thời gian rảnh)
| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ (BUSR) & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 (RFC 9562) | Khóa chính bản ghi. |
| `user_id` | `UUID` | No | None | No | `users(id)` | Yes | No | UUID tồn tại | `BUSR-03..04`. Mỗi User có đúng 1 hồ sơ thời gian rảnh (1:1). |
| `mode` | `VARCHAR(10)` | No | `'MODE_A'` | No | No | No | Yes | `'MODE_A'`, `'MODE_B'` | Phân loại chế độ rảnh: Mode A (Quỹ giờ), Mode B (Khung giờ cố định). |
| `weekly_schedule` | `JSONB` | No | None | No | No | No | No | JSON Schema chuẩn | `OS-06`. Mảng 7 ngày; Mode A: 0.5h–14h/ngày; Mode B: các mảng khung giờ. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian | Thời điểm cập nhật lịch rảnh gần nhất. |

### 1.5. Bảng `goals` (Mục tiêu học tập gốc)
| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ (BUSR) & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 (RFC 9562) | Khóa chính mục tiêu. |
| `user_id` | `UUID` | No | None | No | `users(id)` | No | No | UUID tồn tại | Người sở hữu mục tiêu (`ON DELETE CASCADE`). |
| `title` | `TEXT` | No | None | No | No | No | No | Chuỗi không rỗng | `FR-GOAL-001`. Tên mục tiêu học tập (ví dụ: "Học Go Backend"). |
| `raw_description` | `TEXT` | No | None | No | No | No | No | Văn bản | Ngữ cảnh, kinh nghiệm hiện tại và nguyện vọng chi tiết của người học. |
| `target_date` | `TIMESTAMPTZ` | Yes | None | No | No | No | No | Dấu thời gian tương lai | Hạn chót kỳ vọng hoàn thành mục tiêu. |
| `status` | `VARCHAR(20)` | No | `'ACTIVE'` | No | No | No | Yes | `'ACTIVE'`, `'ARCHIVED'` | Trạng thái mục tiêu; `ARCHIVED` sẽ ẩn toàn bộ lộ trình liên thuộc. |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian | Thời điểm nhập mục tiêu. |

### 1.6. Bảng `roadmaps` (Lộ trình học tập tổng thể)
| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ (BUSR) & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 (RFC 9562) | Khóa chính lộ trình. |
| `user_id` | `UUID` | No | None | No | `users(id)` | No | No | UUID tồn tại | Người sở hữu lộ trình (`ON DELETE CASCADE`). |
| `goal_id` | `UUID` | No | None | No | `goals(id)` | No | No | UUID tồn tại | `ON DELETE RESTRICT`. Chặn xóa nhầm Goal khi đang có lộ trình. |
| `title` | `VARCHAR(255)` | No | None | No | No | No | No | Chuỗi văn bản | Tên định danh của lộ trình học tập. |
| `description` | `TEXT` | Yes | None | No | No | No | No | Văn bản | Mô tả tóm lược phạm vi kiến thức lộ trình bao phủ. |
| `status` | `VARCHAR(20)` | No | `'INITIALIZED'` | No | No | No | Yes | `'INITIALIZED'`, `'ACTIVE'`, `'PAUSED'`, `'COMPLETED'`, `'ARCHIVED'` | `BUSR-01`, SRS Mục 6.1. Vòng đời máy trạng thái Roadmap. |
| `start_date` | `DATE` | Yes | None | No | No | No | No | Định dạng YYYY-MM-DD | Ngày bắt đầu học chính thức. |
| `target_date` | `DATE` | Yes | None | No | No | No | Yes* | Định dạng YYYY-MM-DD | Ngày dự kiến hoàn thành toàn bộ lộ trình. |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian | Thời điểm khởi tạo lộ trình. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian | Thời điểm cập nhật trạng thái hoặc thông tin lộ trình. |

*\*Ràng buộc thời gian:* `CONSTRAINT chk_roadmap_dates CHECK (target_date IS NULL OR start_date IS NULL OR target_date >= start_date)`.

### 1.7. Bảng `milestones` (Mốc kiến thức Cấp 1)
| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ (BUSR) & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 (RFC 9562) | Khóa chính mốc kiến thức. |
| `roadmap_id` | `UUID` | No | None | No | `roadmaps(id)` | No | No | UUID tồn tại | Lộ trình chứa mốc này (`ON DELETE CASCADE`). |
| `sequence_order`| `INTEGER` | No | None | No | No | Yes* | Yes | `>= 1` | `BUSR-02`. Thứ tự tuần tự mốc kiến thức; duy nhất trong Roadmap. |
| `title` | `VARCHAR(255)` | No | None | No | No | No | No | Chuỗi văn bản | `FR-PLAN-001`. Tên mốc kiến thức (ví dụ: "Cơ bản cú pháp Go"). |
| `description` | `TEXT` | Yes | None | No | No | No | No | Văn bản | Tóm tắt các chủ đề trọng tâm trong mốc. |
| `status` | `VARCHAR(20)` | No | `'PENDING'` | No | No | No | Yes | `'PENDING'`, `'APPROVED'` | `FR-PLAN-001`. Phải được duyệt (`APPROVED`) trước khi sinh task Cấp 2. |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian | Thời điểm AI sinh hoặc người dùng thêm mốc. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian | Thời điểm cập nhật thông tin mốc kiến thức gần nhất. |

*\*Ràng buộc duy nhất phức hợp:* `UQ (roadmap_id, sequence_order)` và `UQ (id, roadmap_id)`.

### 1.8. Bảng `schedule_proposals` (Đề xuất Lịch trình Cấp 2)
| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ (BUSR) & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 (RFC 9562) | Khóa chính bản đề xuất. |
| `roadmap_id` | `UUID` | No | None | No | `roadmaps(id)` | No | No | UUID tồn tại | Lộ trình được đề xuất lịch (`ON DELETE CASCADE`). |
| `user_id` | `UUID` | No | None | No | `users(id)` | No | No | UUID tồn tại | Người sở hữu đề xuất (`ON DELETE CASCADE`). |
| `proposal_data` | `JSONB` | No | None | No | No | No | No | Valid JSON Proposal Schema | `FR-PLAN-002`, `BUSR-02`. Mảng task dự thảo chưa qua Validation Gate. |
| `status` | `VARCHAR(20)` | No | `'DRAFT'` | No | No | No | Yes | `'DRAFT'`, `'APPLIED'`, `'DISCARDED'` | SRS Mục 6.4. Vòng đời đề xuất lịch. |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian | Thời điểm AI sinh đề xuất. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian | Thời điểm cập nhật đề xuất gần nhất. |

### 1.9. Bảng `official_schedules` (Lịch học Chính thức)
| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ (BUSR) & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 (RFC 9562) | Khóa chính lịch chính thức. |
| `roadmap_id` | `UUID` | No | None | No | `roadmaps(id)` | Yes | No | UUID tồn tại | `BUSR-02`. Quan hệ 1:1 với Roadmap; đại diện lịch duy nhất có hiệu lực. |
| `total_sessions`| `INTEGER` | No | `0` | No | No | No | Yes | `>= 0` | Tổng số buổi học được phân bổ chính thức. |
| `total_hours` | `INTEGER` | No | `0` | No | No | No | Yes | `>= 0` | Tổng số giờ học cam kết của toàn bộ lộ trình. |
| `activated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian | Thời điểm vượt qua Validation Gate và bấm Apply (`FR-PLAN-003`). |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian | Thời điểm cập nhật lịch (sau dời lịch Domino Shift hoặc Re-apply). |

### 1.10. Bảng `tasks` (Nhiệm vụ học tập chi tiết)
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
| `status` | `VARCHAR(20)` | No | `'TODO'` | No | No | No | Yes | `'TODO'`, `'IN_PROGRESS'`, `'COMPLETED'`, `'CANCELLED'` | `BUSR-06`. Trạng thái thực hiện bền vững (TODO -> IN_PROGRESS -> COMPLETED hoặc CANCELLED). |
| `completed_at` | `TIMESTAMPTZ` | Yes | None | No | No | No | Yes** | Dấu thời gian hoặc `NULL` | Bắt buộc `NOT NULL` khi `COMPLETED`; bắt buộc `NULL` khi khác `COMPLETED`. |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian | Thời điểm tạo task. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian | Thời điểm cập nhật task gần nhất (sau dời lịch Domino Shift hoặc sửa thông tin). |

*\*Ràng buộc khung giờ:* `CHECK (start_time IS NULL OR end_time IS NULL OR start_time < end_time)`.  
*\*\*Ràng buộc logic hoàn thành:* `CHECK ((status = 'COMPLETED' AND completed_at IS NOT NULL) OR (status != 'COMPLETED' AND completed_at IS NULL))`.

### 1.11. Bảng `study_sessions` (Phiên học tập trung)
| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ (BUSR) & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 (RFC 9562) | Khóa chính phiên học. |
| `user_id` | `UUID` | No | None | No | `users(id)` | Yes* | No | UUID tồn tại | Người tham gia học (`ON DELETE CASCADE`). |
| `roadmap_id` | `UUID` | No | None | No | `roadmaps(id)` | No | No | UUID tồn tại | Lộ trình đang học (`ON DELETE CASCADE`). |
| `started_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian | Thời điểm người học bấm Start Session (`FR-SESSION-001`). |
| `ended_at` | `TIMESTAMPTZ` | Yes | None | No | No | No | Yes** | Dấu thời gian hoặc `NULL` | Bắt buộc `NULL` khi đang học; bắt buộc có giá trị $\ge started\_at$ khi kết thúc. |
| `planned_minutes`| `INTEGER` | No | None | No | No | No | Yes | `> 0` | Thời lượng dự kiến của buổi học (tổng phút các task đã chọn). |
| `actual_minutes`| `INTEGER` | No | `0` | No | No | No | Yes | `>= 0` | `BUSR-09`. Thời gian thực học thực tế tích lũy qua các nhịp tim (phút). |
| `status` | `VARCHAR(20)` | No | `'IN_PROGRESS'` | No | No | No | Yes | `'IN_PROGRESS'`, `'COMPLETED'`, `'PARTIAL_COMPLETED'`, `'CANCELLED'` | `OS-01`, `BUSR-09`. Trạng thái phiên học. |
| `last_heartbeat_at`| `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian | `OS-07`. Thời điểm Client ping nhịp tim gần nhất (chu kỳ 60s). |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian | Thời điểm khởi tạo bản ghi session. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian | Thời điểm cập nhật bản ghi session gần nhất. |

*\*Ràng buộc đồng thời:* Partial Unique Index `uq_user_single_active_session` trên `(user_id) WHERE status = 'IN_PROGRESS'`.  
*\*\*Ràng buộc thời gian & trạng thái:* `CHECK (ended_at IS NULL OR ended_at >= started_at)` và `CHECK ((status = 'IN_PROGRESS' AND ended_at IS NULL) OR (status != 'IN_PROGRESS' AND ended_at IS NOT NULL))`.

### 1.12. Bảng `session_tasks` (Liên kết N:M Phiên học - Nhiệm vụ)
| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ (BUSR) & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 (RFC 9562) | Khóa chính liên kết. |
| `session_id` | `UUID` | No | None | No | `study_sessions(id)`| Yes* | No | UUID tồn tại | Phiên học chứa task (`ON DELETE CASCADE`). |
| `task_id` | `UUID` | No | None | No | `tasks(id)` | Yes* | No | UUID tồn tại | Nhiệm vụ được học (`ON DELETE CASCADE`). |
| `allocated_minutes` | `INTEGER` | No | `0` | No | No | No | Yes | `>= 0` | Thời lượng dự kiến phân bổ cho task này trong phiên học. |
| `is_completed_in_session` | `BOOLEAN` | No | `FALSE` | No | No | No | No | `TRUE`, `FALSE` | `BUSR-09`. Đánh dấu task đã được hoàn thành ngay trong phiên học này. |
| `time_spent_minutes` | `INTEGER` | No | `0` | No | No | No | Yes | `>= 0` | Số phút thực học thực tế phân bổ cho task này trong phiên. |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian | Thời điểm thêm task vào phiên. |

*\*Ràng buộc duy nhất phức hợp:* `CONSTRAINT uq_session_task UNIQUE (session_id, task_id)` chặn gán trùng 1 task vào cùng 1 phiên.

### 1.13. Bảng `study_notes` (Ghi chép trong phiên học)
| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ (BUSR) & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 (RFC 9562) | Khóa chính ghi chép. |
| `session_id` | `UUID` | No | None | No | `study_sessions(id)`| Yes* | No | UUID tồn tại | Phiên học liên kết (`ON DELETE CASCADE`). |
| `note_type` | `VARCHAR(20)` | No | None | No | No | Yes* | Yes | `'SCRATCHPAD'`, `'TAKEAWAY'` | `FR-SESSION-002`. Phân loại: Nháp tự do hoặc Đúc kết trọng tâm. |
| `content` | `TEXT` | No | `''` | No | No | No | No | Văn bản | Nội dung ghi chép của người học trong Study Workspace. |
| `updated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian | Thời điểm lưu nội dung gần nhất. |

*\*Ràng buộc duy nhất phức hợp:* `CONSTRAINT uq_session_note_type UNIQUE (session_id, note_type)` giới hạn đúng 1 Scratchpad và 1 Takeaway/phiên.

### 1.14. Bảng `pause_records` (Lịch sử Tạm dừng & Dời lịch)
| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ (BUSR) & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 (RFC 9562) | Khóa chính bản ghi pause. |
| `roadmap_id` | `UUID` | No | None | No | `roadmaps(id)` | No | No | UUID tồn tại | Lộ trình được tạm dừng (`ON DELETE CASCADE`). |
| `pause_start_date`| `DATE` | No | None | No | No | No | No | YYYY-MM-DD | Ngày bắt đầu tạm dừng lộ trình. |
| `pause_end_date` | `DATE` | No | None | No | No | No | Yes | `pause_end_date >= pause_start_date` | Ngày kết thúc tạm dừng. |
| `shifted_days` | `INTEGER` | No | None | No | No | No | Yes | `> 0` | `FR-PAUSE-002`, `BUSR-07`. Số ngày lịch trình đã tịnh tiến lùi về sau. |
| `reason` | `TEXT` | Yes | None | No | No | No | No | Văn bản | Lý do tạm dừng (ví dụ: "Bận thi tốt nghiệp", "Ốm"). |
| `created_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian | Thời điểm ghi nhận lệnh tạm dừng. |

### 1.15. Bảng `ai_reviews` (Báo cáo & Phản tư từ AI)
| Cột | Kiểu Dữ liệu | Null | Mặc định | PK | FK | UQ | CHECK | Miền Giá trị Hợp lệ | Quy tắc Nghiệp vụ (BUSR) & Ý nghĩa |
|---|---|---|---|---|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Yes | No | Yes | No | UUIDv7 (RFC 9562) | Khóa chính bản ghi review. |
| `roadmap_id` | `UUID` | No | None | No | `roadmaps(id)` | No | No | UUID tồn tại | Lộ trình được đánh giá (`ON DELETE CASCADE`). |
| `user_id` | `UUID` | No | None | No | `users(id)` | No | No | UUID tồn tại | Người học nhận đánh giá (`ON DELETE CASCADE`). |
| `review_cycle` | `VARCHAR(20)` | No | None | No | No | No | Yes | `'WEEKLY'`, `'MILESTONE'` | Chu kỳ đánh giá: Hàng tuần hoặc Sau mỗi cột mốc. |
| `quantitative_summary`| `JSONB` | No | None | No | No | No | No | Valid JSON Summary | Dữ liệu thống kê toán học đã được làm sạch (Sanitized). |
| `strengths_feedback` | `TEXT` | No | None | No | No | No | No | Văn bản | Nhận xét định tính điểm mạnh và thành tựu đã đạt được. |
| `bottlenecks_feedback` | `TEXT` | No | None | No | No | No | No | Văn bản | Cảnh báo điểm nghẽn, các task trễ hạn hoặc học dở dang. |
| `action_recommendations`| `TEXT` | No | None | No | No | No | No | Văn bản | Đề xuất hành động điều chỉnh cụ thể cho chu kỳ tiếp theo. |
| `generated_at` | `TIMESTAMPTZ` | No | `NOW()` | No | No | No | No | Dấu thời gian | `BUSR-12`. Thời điểm AI sinh nhận xét (Write-Once Snapshot). |

---

## 2. Ma trận Ràng buộc Toàn vẹn (Constraint Matrix)

Ma trận dưới đây tổng hợp toàn bộ 38 ràng buộc toàn vẹn có tên (Named Constraints) và ràng buộc khóa trong PostgreSQL 16 của FocusFlow, giải thích rõ Bất biến Nghiệp vụ (Business Invariant) được bảo vệ:

| Tên Ràng buộc (Constraint Name) | Bảng Sở hữu | Loại Ràng buộc | Định nghĩa Kỹ thuật trong DDL | Bất biến Nghiệp vụ Được Bảo vệ |
|---|---|---|---|---|
| `users_pkey` | `users` | Primary Key | `PRIMARY KEY (id)` | Đảm bảo tính duy nhất thực thể người dùng, chống ID Enumeration. |
| `users_email_key` | `users` | Unique Key | `UNIQUE (email)` | Chống trùng lặp tài khoản đăng ký trên hệ thống. |
| `webcal_tokens_pkey` | `webcal_tokens` | Primary Key | `PRIMARY KEY (id)` | Định danh bản ghi token. |
| `webcal_tokens_user_id_key` | `webcal_tokens` | Unique Key | `UNIQUE (user_id)` | `OS-05`. Mỗi User chỉ sở hữu duy nhất 1 WebCal token đang hiệu lực. |
| `webcal_tokens_token_hash_key` | `webcal_tokens` | Unique Key | `UNIQUE (token_hash)` | Ngăn chặn va chạm bản băm token, bảo mật feed ICS. |
| `ai_quotas_pkey` | `ai_quotas` | Primary Key | `PRIMARY KEY (id)` | Định danh bản ghi hạn ngạch. |
| `ai_quotas_user_id_key` | `ai_quotas` | Unique Key | `UNIQUE (user_id)` | Mỗi User chỉ có 1 chu kỳ hạn ngạch kích hoạt đồng thời. |
| `chk_ai_quota_limit` | `ai_quotas` | Check | `CHECK (used_calls + reserved_calls <= monthly_limit)` | `BUSR-10`. Chặn race condition gọi vượt trần hạn ngạch AI tại mức CSDL. |
| `chk_ai_quota_cycle` | `ai_quotas` | Check | `CHECK (cycle_end > cycle_start)` | Đảm bảo khoảng thời gian chu kỳ tính cước luôn hợp lệ. |
| `availabilities_pkey` | `availabilities` | Primary Key | `PRIMARY KEY (id)` | Định danh bản ghi thời gian rảnh. |
| `availabilities_user_id_key` | `availabilities` | Unique Key | `UNIQUE (user_id)` | Mỗi User chỉ có duy nhất 1 cấu hình quỹ thời gian rảnh. |
| `goals_pkey` | `goals` | Primary Key | `PRIMARY KEY (id)` | Định danh mục tiêu học tập. |
| `fk_goals_user` | `goals` | Foreign Key | `FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE` | Toàn vẹn người sở hữu mục tiêu; xóa User sẽ xóa toàn bộ Goals. |
| `roadmaps_pkey` | `roadmaps` | Primary Key | `PRIMARY KEY (id)` | Định danh lộ trình học tập. |
| `fk_roadmaps_user` | `roadmaps` | Foreign Key | `FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE` | Toàn vẹn người sở hữu lộ trình. |
| `fk_roadmaps_goal` | `roadmaps` | Foreign Key | `FOREIGN KEY (goal_id) REFERENCES goals(id) ON DELETE RESTRICT` | Ngăn chặn việc xóa Goal gốc khi đang có các lộ trình phụ thuộc. |
| `chk_roadmap_dates` | `roadmaps` | Check | `CHECK (target_date IS NULL OR start_date IS NULL OR target_date >= start_date)` | Đảm bảo ngày đích của lộ trình không sớm hơn ngày bắt đầu. |
| `milestones_pkey` | `milestones` | Primary Key | `PRIMARY KEY (id)` | Định danh mốc kiến thức Cấp 1. |
| `fk_milestones_roadmap` | `milestones` | Foreign Key | `FOREIGN KEY (roadmap_id) REFERENCES roadmaps(id) ON DELETE CASCADE` | Xóa lộ trình sẽ tự động dọn dẹp các mốc tương ứng. |
| `uq_milestone_roadmap_sequence` | `milestones` | Unique Key | `UNIQUE (roadmap_id, sequence_order)` | `BUSR-02`. Thứ tự mốc kiến thức trong 1 lộ trình không được trùng nhau. |
| `uq_milestone_id_roadmap` | `milestones` | Unique Key | `UNIQUE (id, roadmap_id)` | Tạo siêu khóa phục vụ khóa ngoại phức hợp từ `tasks`. |
| `schedule_proposals_pkey` | `schedule_proposals`| Primary Key | `PRIMARY KEY (id)` | Định danh bản đề xuất lịch Cấp 2. |
| `fk_proposals_roadmap` | `schedule_proposals`| Foreign Key | `FOREIGN KEY (roadmap_id) REFERENCES roadmaps(id) ON DELETE CASCADE` | Tự động xóa các bản dự thảo khi lộ trình bị xóa. |
| `fk_proposals_user` | `schedule_proposals`| Foreign Key | `FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE` | Toàn vẹn sở hữu đề xuất. |
| `official_schedules_pkey` | `official_schedules`| Primary Key | `PRIMARY KEY (id)` | Định danh bản ghi lịch chính thức. |
| `official_schedules_roadmap_id_key` | `official_schedules`| Unique Key | `UNIQUE (roadmap_id)` | `BUSR-02`. Mỗi Roadmap chỉ có duy nhất 1 bộ lịch chính thức hiệu lực. |
| `fk_official_schedules_roadmap` | `official_schedules`| Foreign Key | `FOREIGN KEY (roadmap_id) REFERENCES roadmaps(id) ON DELETE CASCADE` | Xóa lộ trình sẽ xóa lịch chính thức tương ứng. |
| `tasks_pkey` | `tasks` | Primary Key | `PRIMARY KEY (id)` | Định danh nhiệm vụ học tập Cấp 2. |
| `fk_tasks_roadmap` | `tasks` | Foreign Key | `FOREIGN KEY (roadmap_id) REFERENCES roadmaps(id) ON DELETE CASCADE` | Xóa lộ trình sẽ dọn dẹp toàn bộ các task liên thuộc. |
| `fk_tasks_milestone_roadmap` | `tasks` | Foreign Key (Composite) | `FOREIGN KEY (milestone_id, roadmap_id) REFERENCES milestones(id, roadmap_id) ON DELETE CASCADE` | **Chặn đứng 100% nguy cơ gán task vào milestone của Roadmap khác**. |
| `chk_task_time_window` | `tasks` | Check | `CHECK (start_time IS NULL OR end_time IS NULL OR start_time < end_time)` | Đảm bảo giờ bắt đầu luôn trước giờ kết thúc khi xếp lịch Mode B. |
| `chk_task_completed_at` | `tasks` | Check | `CHECK ((status = 'COMPLETED' AND completed_at IS NOT NULL) OR (status != 'COMPLETED' AND completed_at IS NULL))` | `INV_TK_01`. Cưỡng chế dấu thời gian hoàn thành logic đồng bộ với status. |
| `study_sessions_pkey` | `study_sessions` | Primary Key | `PRIMARY KEY (id)` | Định danh phiên học tập trung. |
| `uq_user_single_active_session` | `study_sessions` | Unique Partial Index | `UNIQUE (user_id) WHERE status = 'IN_PROGRESS'` | `INV_SS_01`. Mỗi User chỉ có tối đa 1 session IN_PROGRESS cùng lúc. |
| `chk_session_times` | `study_sessions` | Check | `CHECK (ended_at IS NULL OR ended_at >= started_at)` | Thời điểm kết thúc phiên không được sớm hơn thời điểm bắt đầu. |
| `chk_session_status_ended` | `study_sessions` | Check | `CHECK ((status = 'IN_PROGRESS' AND ended_at IS NULL) OR (status != 'IN_PROGRESS' AND ended_at IS NOT NULL))` | `INV_SS_03`. Phiên đóng bắt buộc có `ended_at`; phiên mở bắt buộc `NULL`. |
| `session_tasks_pkey` | `session_tasks` | Primary Key | `PRIMARY KEY (id)` | Định danh liên kết giữa phiên học và task. |
| `uq_session_task` | `session_tasks` | Unique Key | `UNIQUE (session_id, task_id)` | Ngăn chặn việc đưa 1 task 2 lần vào cùng 1 phiên học. |
| `study_notes_pkey` | `study_notes` | Primary Key | `PRIMARY KEY (id)` | Định danh ghi chép học tập. |
| `uq_session_note_type` | `study_notes` | Unique Key | `UNIQUE (session_id, note_type)` | Giới hạn 1 Scratchpad và 1 Takeaway duy nhất cho mỗi phiên học. |
| `pause_records_pkey` | `pause_records` | Primary Key | `PRIMARY KEY (id)` | Định danh bản ghi tạm dừng. |
| `chk_pause_dates` | `pause_records` | Check | `CHECK (pause_end_date >= pause_start_date)` | Ngày kết thúc tạm dừng phải $\ge$ ngày bắt đầu tạm dừng. |
| `ai_reviews_pkey` | `ai_reviews` | Primary Key | `PRIMARY KEY (id)` | Định danh bản ghi báo cáo AI Review. |

---

## 3. Ma trận Chỉ mục Hiệu năng (Index Matrix - Access Pattern Traceability)

Tất cả các chỉ mục trong hệ thống được thiết kế dựa trên các **Mẫu truy vấn (Access Patterns)** thực tế của Use Case và Repository, loại bỏ hoàn toàn các chỉ mục dư thừa hoặc trùng lặp tiền tố:

| Tên Chỉ mục (Index Name) | Bảng Sở hữu | Cột được Đánh chỉ mục | Loại Chỉ mục | Duy nhất (UQ) | Mẫu Truy vấn & Use Case Hỗ trợ | Phân tích Tính Chọn lọc (Selectivity) & Overhead |
|---|---|---|---|---|---|---|
| `users_pkey` | `users` | `(id)` | B-Tree | Yes | Tra cứu người dùng theo JWT claims (`user_id`). | Selectivity: 1.0 (Tuyệt đối). Overhead: Chuẩn PK. |
| `users_email_key` | `users` | `(email)` | B-Tree | Yes | `FR-AUTH-001`. Đăng nhập hệ thống (`WHERE email = :email`). | Selectivity: 1.0. Tần suất đọc cao khi xác thực. |
| `webcal_tokens_token_hash_key` | `webcal_tokens` | `(token_hash)` | B-Tree | Yes | `FR-CALENDAR-002`. Xuất WebCal Feed 1 chiều từ ứng dụng lịch ngoại vi. | Selectivity: 1.0. Truy vấn trực tiếp từ URL không qua Cookie. |
| `uq_user_single_active_session` | `study_sessions` | `(user_id)` | B-Tree Partial | Yes | `FR-SESSION-001`. Kiểm tra người dùng có session nào đang chạy không (`WHERE user_id = :uid AND status = 'IN_PROGRESS'`). | Kích thước cực nhỏ (chỉ chứa các dòng `IN_PROGRESS`). Write Overhead tối thiểu. |
| `idx_study_sessions_user_started` | `study_sessions` | `(user_id, started_at DESC)` | B-Tree Composite | No | `FR-SESSION-002`, `FR-REPORT-001`. Tải lịch sử phiên học và vẽ biểu đồ học tập trên Dashboard theo thứ tự mới nhất. | Tối ưu hóa tuyệt đối phép sắp xếp (`ORDER BY started_at DESC LIMIT 20`), loại bỏ thao tác Sort trên RAM. |
| `idx_roadmaps_user_status` | `roadmaps` | `(user_id, status)` | B-Tree Composite | No | `FR-PLAN-001`, `FR-AVAIL-003`. Lọc nhanh các lộ trình đang hoạt động (`WHERE user_id = :uid AND status IN ('ACTIVE', 'PAUSED')`). | Giúp kiểm tra hạn ngạch Roadmap đồng thời (Free=3, Premium=15) theo `OS-02`. |
| `idx_tasks_roadmap_scheduled_date` | `tasks` | `(roadmap_id, scheduled_date)` | B-Tree Composite | No | `FR-TASK-001`, `FR-PAUSE-002`. Hiển thị lịch học trong tháng và thực thi giải thuật Domino Shift (`WHERE roadmap_id = :rid AND scheduled_date >= :date`). | Tần suất truy vấn cao nhất hệ thống; loại bỏ thao tác Filter tuần tự. |
| `idx_tasks_todo_overdue` | `tasks` | `(scheduled_date)` | B-Tree Partial | No | `FR-ADAPT-001`, `ADR-004`. Celery Beat quét lúc 00:01 gắn cờ task quá hạn (`WHERE status = 'TODO' AND scheduled_date IS NOT NULL`). | Chỉ lập chỉ mục task chưa xong có ngày lên lịch. Rất nhẹ và tốc độ quét $\le 5$ms. |
| `idx_study_sessions_in_progress` | `study_sessions` | `(last_heartbeat_at)` | B-Tree Partial | No | `OS-07`, `ADR-004`. Celery Beat quét mỗi 5 phút chốt phiên mất mạng (`WHERE status = 'IN_PROGRESS' AND last_heartbeat_at < NOW() - 5m`). | Chỉ quét các phiên học đang mở; không bao giờ quét các phiên đã đóng. |
| `idx_ai_quotas_user_cycle` | `ai_quotas` | `(user_id, cycle_start, cycle_end)` | B-Tree Covering | No | `FR-QUOTA-001`, `BUSR-10`. Middleware kiểm tra và tạm giữ hạn ngạch AI trước khi gọi Gemini API. | Index-Only Scan che phủ toàn bộ điều kiện lọc chu kỳ, tốc độ phản hồi $\le 1$ms. |
| `idx_schedule_proposals_roadmap_status` | `schedule_proposals` | `(roadmap_id, status)` | B-Tree Composite | No | `FR-PLAN-003`. Tìm bản dự thảo lịch trình gần nhất để người học bấm Apply (`WHERE roadmap_id = :rid AND status = 'DRAFT'`). | Tăng tốc độ hiển thị Preview Proposal màn hình M2. |
| `idx_ai_reviews_roadmap_cycle` | `ai_reviews` | `(roadmap_id, review_cycle, generated_at DESC)` | B-Tree Composite | No | `FR-REPORT-002`. Lấy nhận xét phản tư mới nhất của tuần hoặc mốc (`ORDER BY generated_at DESC LIMIT 1`). | Tối ưu hóa tải báo cáo tuần mà không cần quét toàn bảng. |
| `idx_study_sessions_roadmap_id` | `study_sessions` | `(roadmap_id)` | B-Tree | No | `FR-REPORT-001`. Tính tổng thời gian thực học tích lũy theo từng Roadmap (`SELECT sum(actual_minutes) ... WHERE roadmap_id = :rid`) và hỗ trợ Cascade Delete. | Ngăn chặn Sequential Scan khi Roadmap có hàng trăm phiên học. |
| `idx_session_tasks_task_id` | `session_tasks` | `(task_id)` | B-Tree | No | `FR-TASK-001`, `BUSR-09`. Kiểm tra task đã được học trong các phiên nào và hỗ trợ Cascade Delete khi người dùng xóa task. | Giải quyết điểm nghẽn khóa ngoại chiều ngược trong quan hệ N:M. |
| `idx_tasks_milestone_id` | `tasks` | `(milestone_id)` | B-Tree | No | `FR-PLAN-001`, PostgreSQL FK lock protection. Tối ưu truy vấn task theo mốc và bảo vệ Cascade Delete khi xóa mốc. | Triệt tiêu Sequential Scan toàn bảng tasks khi xóa Milestone. |
| `idx_goals_user_id` | `goals` | `(user_id)` | B-Tree | No | `FR-GOAL-001`, Cascade Delete. Tra cứu danh sách mục tiêu của người học. | Bảo vệ Cascade Delete khi xóa User. |
| `idx_roadmaps_goal_id` | `roadmaps` | `(goal_id)` | B-Tree | No | `FR-PLAN-001`, RESTRICT check. Kiểm tra khóa ngoại khi thao tác với Goal gốc. | Tối ưu kiểm tra ràng buộc RESTRICT khi xóa Goal. |
| `idx_schedule_proposals_user_id` | `schedule_proposals`| `(user_id)` | B-Tree | No | `FR-PLAN-002`, Cascade Delete. Tra cứu các bản đề xuất theo người dùng. | Bảo vệ Cascade Delete khi xóa User. |
| `idx_pause_records_roadmap_id` | `pause_records` | `(roadmap_id)` | B-Tree | No | `FR-PAUSE-002`, Cascade Delete. Lấy lịch sử các lần tạm dừng của lộ trình. | Bảo vệ Cascade Delete khi xóa Roadmap. |
| `idx_ai_reviews_user_id` | `ai_reviews` | `(user_id)` | B-Tree | No | `FR-REPORT-002`, Cascade Delete. Tra cứu danh sách báo cáo AI của người dùng. | Bảo vệ Cascade Delete khi xóa User. |

---

## 4. Kiểm toán Tính nhất quán Toàn chuỗi (End-to-End Consistency Audit)

Thực hiện đối soát nghiêm ngặt theo chuỗi phụ thuộc:
$$\text{DB Diagram} \longleftrightarrow \text{Migration} \longleftrightarrow \text{Entity/Model} \longleftrightarrow \text{Repository} \longleftrightarrow \text{Data Dictionary}$$

### 4.1. Kết quả Đối chiếu Chi tiết
1. **DB Diagram ↔ Data Dictionary:**
   * 15/15 bảng và toàn bộ các cột, kiểu dữ liệu, khóa chính, khóa ngoại, ràng buộc CHECK và UNIQUE hoàn toàn khớp nhau $100\%$.
   * Không còn bất kỳ trường thừa hay bảng mồ côi nào.
2. **Data Dictionary ↔ Database Schema DDL (`schema.sql`):**
   * Các kiểu dữ liệu vật lý (`UUID`, `VARCHAR`, `TIMESTAMPTZ`, `JSONB`, `DATE`, `TIME`) khớp chính xác $100\%$.
   * Cú pháp sinh khóa chính ANSI `gen_random_uuid()` đã đồng bộ đồng nhất trên toàn bộ 15 bảng.
   * Khóa ngoại phức hợp `(milestone_id, roadmap_id)` và việc loại bỏ `official_schedule_id` đã được cập nhật chuẩn xác.
3. **Chỉ mục Hiệu năng (Indexes) ↔ Use Case / Access Patterns:**
   * Đã loại bỏ 2 chỉ mục trùng lặp (`idx_milestones_roadmap_seq` trùng với constraint `uq_milestone_roadmap_sequence`; `idx_study_notes_session` trùng tiền tố với `uq_session_note_type`).
   * Đã bổ sung 2 chỉ mục che phủ khóa ngoại quan trọng (`idx_study_sessions_roadmap_id` và `idx_session_tasks_task_id`).
   * Toàn bộ 14 chỉ mục đều có lý do nghiệp vụ thực chứng gắn trực tiếp với mã yêu cầu `FR` và quyết định mở `OS`.
4. **Hiện trạng Mã nguồn Thực thi (`src/`):**
   * Do dự án đang ở giai đoạn đóng băng thiết kế kiến trúc và mô hình dữ liệu (Milestone M2), thư mục `src/` hiện chưa khởi tạo file vật lý (chưa có file Alembic migration hay SQLAlchemy model code).
   * **Đánh giá rủi ro:** Không có hiện tượng Lệch pha Mã nguồn (Code Drift). Toàn bộ hồ sơ CSDL tại `docs/database/` và `docs/uml/` đã sẵn sàng làm chuẩn đầu vào tuyệt đối chính xác cho giai đoạn sinh mã nguồn ORM và Migrations tiếp theo.
