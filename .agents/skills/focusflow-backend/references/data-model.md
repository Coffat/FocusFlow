# Mô hình dữ liệu (PostgreSQL 16, 24 bảng, 3NF/BCNF)

## 1. Sở hữu ghi độc quyền

| Context | Bảng |
|---|---|
| account (9) | `users`, `learner_profiles`, `webcal_tokens`, `availabilities`, `availability_slots`, `ai_quotas`, `ai_quota_reservations`, `ai_usage_logs`, `payment_transactions` |
| planning (5) | `goals`, `roadmaps`, `milestones`, `official_schedules`, `schedule_proposals` |
| execution (5) | `tasks`, `task_dependencies`, `study_sessions`, `session_tasks`, `study_notes` |
| evaluation (3) | `pause_records`, `ai_reviews`, `schedule_change_logs` |
| shared_kernel (2) | `outbox_events`, `processed_events` |

SRS v1.2 §12 còn nhắc thực thể `CalendarConnection` (OAuth, tách khỏi `WebCalToken`). 24 bảng của ADR-007 **không có bảng riêng** cho nó ⇒ đây là khoảng trống đặc tả: xem `spec-conflicts.md` mục "CalendarConnection". Đừng tự thêm bảng thứ 25 mà không hỏi người dùng; nếu cần lưu OAuth token, đề xuất bảng `calendar_connections` (context `account` hoặc `execution` — hỏi) kèm migration và cập nhật con số 24.

## 2. Quy ước

- PK `UUIDv7` sinh ở domain. FK đơn (surrogate). Timestamps `timestamptz` UTC; trigger `set_updated_at()` đã có trong schema.
- **Tenant correlation id**: `user_id` trên `schedule_proposals`, `study_sessions`, `study_notes`, `pause_records`, `ai_reviews`, `schedule_change_logs`; `roadmap_id` trên `tasks`. Dùng để kiểm sở hữu không JOIN. Khi tạo thực thể, use case phải gán đúng và đảm bảo nhất quán (vd task thuộc roadmap của chính user — kiểm qua `public_api` của planning trước khi tạo).
- FK vật lý giữ ở DDL, nhưng **không** `relationship()`/JOIN ORM giữa hai context. Trong cùng context được dùng `relationship()` + `selectinload` (tránh lazy load trong async).
- `availability_slots` (`id, availability_id, day_of_week, start_time, end_time, end_day_offset, slot_type, is_active`) là bảng con chuẩn hóa, `ON DELETE CASCADE`; repository ánh xạ sang Value Object `WeeklySchedule`/`TimeSlot`. Khe vắt qua nửa đêm dùng `end_day_offset`. Không lưu JSONB `weekly_schedule`.
- `tasks.estimated_minutes` CHECK trong `[15, 240]` (thủ công); khối AI sinh nằm trong dải hẹp hơn do Tier 1 kiểm (xem conflicts).
- Task persisted status chỉ: `TODO, IN_PROGRESS, COMPLETED, CANCELLED`. `OVERDUE`, `BLOCKED`, `STALLED` là **cờ suy diễn** tại thời điểm truy vấn (`STALLED` ⇔ `reschedule_count >= 3`), không lưu thành status.
- Roadmap: `INITIALIZED, ACTIVE, PAUSED, COMPLETED, ARCHIVED`. Proposal: `DRAFT, APPLIED, DISCARDED`. Session: `IN_PROGRESS, COMPLETED, PARTIAL_COMPLETED, CANCELLED`. Reservation: `RESERVED, COMMITTED, RELEASED, EXPIRED`. Payment: xem conflicts (có `EXPIRED`, TTL 15 phút).
- `payment_transactions.transaction_ref` UNIQUE (chống replay).
- `webcal_tokens`: chỉ `token_hash` (sha256), quan hệ 1-1 với user.
- `outbox_events`: `status` (`PENDING`/`PUBLISHED`), payload JSON nhỏ; `processed_events(event_id PK, consumer, processed_at)`.

## 3. Ràng buộc & index đáng nhớ

- `uq_milestone_roadmap_sequence UNIQUE (roadmap_id, sequence_order) DEFERRABLE INITIALLY DEFERRED` → hoán đổi thứ tự milestone trong một giao dịch.
- Partial unique: `uq_user_single_active_session` (tối đa 1 phiên `IN_PROGRESS`/user), `uq_one_draft_per_roadmap` (tối đa 1 `DRAFT`/roadmap). Tạo proposal mới ⇒ phải chuyển DRAFT cũ sang `DISCARDED` trong cùng giao dịch, trước khi insert.
- Partial index `idx_study_sessions_in_progress` phục vụ sweeper.
- `session_tasks.task_id ON DELETE RESTRICT`.

## 4. Migration (Alembic async)

- Mỗi thay đổi schema = một revision có `upgrade` + `downgrade`; revision đặt tên mô tả. `backend` container chạy `alembic upgrade head` trước `uvicorn`.
- Sau khi sửa: chạy `alembic upgrade head` trên DB trống → `scripts/dump_schema.sh` → so với `docs/database/schema.sql` (CI diff). Cập nhật `schema.sql` bằng script, không sửa tay.
- Migration dữ liệu (backfill) tách khỏi migration cấu trúc; không để migration phụ thuộc code domain (copy hằng số vào migration).
- Cột NOT NULL mới trên bảng có dữ liệu: thêm nullable → backfill → siết NOT NULL.

## 5. Mapper (Data Mapper pattern)

Repository trả **domain entity**, không trả ORM model. Mỗi repository có hàm `_to_domain(orm)` và `_apply(orm, entity)`. Tuyệt đối không để `AsyncSession`/ORM đi ra khỏi `infrastructure/`. Lưu aggregate: chỉ `session.add()` + `flush()`; commit do UoW.
