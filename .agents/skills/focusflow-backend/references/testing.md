# Chiến lược kiểm thử (Backend)

Nguyên tắc: kim tự tháp — nhiều unit thuần (ms), vừa phải integration (PostgreSQL thật), ít E2E. Test hành vi nghiệp vụ, không test chi tiết cài đặt.

## 1. Unit — domain (không DB/Redis/LLM, `pytest`)
- Aggregate: mỗi method đổi trạng thái có test ca hợp lệ + ca vi phạm bất biến (task CANCELLED không complete được; `reschedule_count` tăng/không tăng đúng chỗ; STALLED).
- `HybridAvailabilityRuleEngine`: Mode A chạm trần/vượt/đúng bằng; Mode B trong slot, Soft Overflow đúng 30 vs 31 phút, chỉ task cuối ngày, slot vắt nửa đêm, overlap, trừ khoảng bận. Branch coverage ≥ 95%.
- `DagCycleValidator`: tự vòng, vòng dài, đa nhánh, tiền đề xếp sau hậu kế. ≥ 95%.
- `DominoShiftEngine`: dịch đúng số ngày khả dụng, giữ thứ tự, **giữ nguyên `reschedule_count`**, biên cuối tuần/ngày không khả dụng.
- Thời gian: dùng `FakeClock`; test quá hạn quanh nửa đêm ở nhiều timezone (UTC+7, UTC-8, ranh giới DST).
- Property-based (hypothesis) rất đáng với engine lịch: "không bao giờ xuất ra lịch vi phạm ràng buộc cứng".

## 2. Unit — use case (fake port, in-memory UoW)
Dùng `FakeUnitOfWork` ghi nhận `committed`/`collected_events`. Kiểm: IDOR (người khác ⇒ NotFound), event được phát, không commit khi lỗi, quota RELEASE trên mọi nhánh lỗi của luồng AI, `Idempotency-Key` trùng không reserve hai lần, consumer trùng `event_id` không xử lý lần hai.

## 3. Integration (PostgreSQL 16 thật + `InMemoryBroker`)
- Repository ↔ DB: mapping `availability_slots` ↔ `WeeklySchedule`, constraint (CHECK, partial unique `uq_user_single_active_session`, `uq_one_draft_per_roadmap`, deferrable sequence).
- UoW: ghi nghiệp vụ + `outbox_events` trong một giao dịch; rollback khi lỗi ⇒ không có outbox mồ côi.
- Concurrency quota: 10 request song song, còn 1 lượt ⇒ 1 thành công + 9 `QUOTA_EXHAUSTED`.
- Sweeper: nhiều worker song song không xử lý trùng (`SKIP LOCKED`); phiên 5 phút không heartbeat được chốt đúng OS-01 với `ended_at = last_heartbeat_at`; reservation hết TTL chuyển `EXPIRED` và hoàn `reserved`.
- Outbox relay → consumer → `processed_events` → cập nhật `learner_profiles` (eventual consistency).
- Migration: `alembic upgrade head` trên DB trống, `downgrade` thử, diff với `schema.sql`.

## 4. API / bảo mật (`httpx.AsyncClient`)
IDOR từng endpoint `{id}`; RBAC `/admin/*`; cookie flags; refresh rotation + reuse detection; webhook (sai chữ ký, replay, trùng `transaction_ref`); SSE: reconnect không trừ quota, sự kiện đúng thứ tự `stage→chunk→completed`, lỗi → `failed`; hợp đồng OpenAPI (snapshot) để phát hiện breaking change cho frontend.

## 5. AI
Dùng `MockLLMAdapter` có kịch bản lỗi (JSON hỏng, vi phạm overbooking, chu trình DAG, timeout Tier 3, 429) để test retry/RELEASE/fail-open. Không gọi LLM thật trong CI. Eval harness chạy riêng (`tests/ai_evals/`).

## 6. Quy ước
- Tên test mô tả hành vi: `test_apply_proposal_rejects_overbooked_day`.
- Fixture/factory cho aggregate; tránh sao chép dữ liệu lớn.
- Test không phụ thuộc thứ tự, không phụ thuộc giờ hệ thống, không sleep thật (dùng fake clock / `asyncio` mock).
- Bug mới ⇒ viết test tái hiện trước khi sửa.
