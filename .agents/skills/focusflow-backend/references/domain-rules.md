# Quy tắc nghiệp vụ cô đọng (nguồn: SRS v1.2)

Mục lục: 1. BUSR · 2. Quyết định OS-01..08 · 3. State machine · 4. Quá hạn · 5. Pause/Domino · 6. Phiên học · 7. Learner profile · 8. Giới hạn số · 9. Báo cáo · 10. Admin

## 1. BUSR (mỗi dòng: điều phải đúng trong code)
- BUSR-01: phải đăng nhập mới tạo goal/plan; mọi dữ liệu gắn `user_id`.
- BUSR-02: AI chỉ sinh `ScheduleProposal(DRAFT)`; chỉ `Apply` của người học (+ validate tất định lần cuối) mới ghi `OfficialSchedule`. Áp dụng cho cả sinh lộ trình lẫn AI Reschedule.
- BUSR-03: Backend là chốt chặn cuối cho mọi tạo/sửa/dời/apply: tổng phút/ngày hoặc/khung ≤ thời gian rảnh khả dụng (đã trừ roadmap khác + khoảng bận ngoài), trừ Soft Overflow.
- BUSR-04: Soft Overflow chỉ task **cuối ngày Mode B**, ≤30 phút sau mốc kết thúc slot; cảnh báo + người dùng xác nhận trước Apply.
- BUSR-05: nhiều roadmap ACTIVE (Free 3 / Premium 15); xếp lịch mới chỉ vào khoảng trống; xung đột ưu tiên theo EDF (`target_date` gần hơn thắng).
- BUSR-06: quá hạn là điều kiện **suy diễn**: `status ∉ {COMPLETED, CANCELLED} ∧ scheduled_date < today(user.timezone)`. Scanner **không** đổi `scheduled_date`, chỉ gắn cờ + email.
- BUSR-07: Domino Shift khi Pause: dịch các buổi từ ngày A đúng số ngày khả dụng, giữ thứ tự/liên kết task, không phát cảnh báo quá hạn trong thời gian PAUSED, không tăng `reschedule_count`.
- BUSR-08: Calendar 2 chiều có kiểm soát; WebCal chỉ xuất OfficialSchedule; token reset hủy ngay; URL/token không vào log.
- BUSR-09: phiên bị dừng/gián đoạn: lưu đúng số phút thực học; task đã tick giữ `COMPLETED`; task chưa xong về Backlog (`scheduled_date = NULL`) không phạt.
- BUSR-10: kiểm quota trước khi gọi LLM; giữ chỗ/quyết toán nguyên tử; lỗi 503/429/timeout/hủy sau 2 retry không trừ quota; không đưa dữ liệu nhạy cảm vào prompt.
- BUSR-11: `/admin/*` bắt buộc RBAC ADMIN, 403/401; sự kiện an ninh/quản trị vào audit stream.
- BUSR-12: AI Review không đổi lộ trình/lịch/task.

## 2. Quyết định đã phê duyệt
- OS-01: phiên dừng sớm/mất mạng ⇒ `PARTIAL_COMPLETED` nếu có ≥1 task `COMPLETED` **hoặc** thực học ≥ **50%** thời lượng dự kiến; ngược lại `CANCELLED`.
- OS-02: Free = 3 roadmap ACTIVE + 30 lượt AI/tháng; Premium = 15 + 300. Reset quota ngày 01. Hạ cấp Premium→Free có >3 ACTIVE ⇒ giữ 3 roadmap có `target_date` sớm nhất (EDF), phần còn lại → `PAUSED` (giữ nguyên dữ liệu).
- OS-03: Apply khi đã có OfficialSchedule ⇒ **Merge / Future Shift**: giữ task & phiên `COMPLETED` quá khứ; chỉ thay các task chưa hoàn thành bằng proposal mới.
- OS-04: EDF.
- OS-05: WebCal token 32-byte hex, lưu sha256, 1-1 với user, trả một lần.
- OS-06: Mode A: **0.5h–14h/ngày**.
- OS-07: heartbeat mỗi **60s**; im lặng >**5 phút** ⇒ chốt `ended_at = last_heartbeat_at`.
- OS-08: backoff 2s, 4s (trần 10s) full jitter, tối đa 2 retry.

## 3. State machine (persisted)
- Roadmap: `INITIALIZED →(Apply thành công & chưa vượt trần) ACTIVE ⇄ PAUSED`; `ACTIVE|PAUSED → ARCHIVED` (task chưa xong → `CANCELLED`, `scheduled_date=NULL`, giải phóng slot & suất ACTIVE); `ACTIVE → COMPLETED` khi 100% task không bị hủy `COMPLETED`. `COMPLETED/ARCHIVED` bất biến (chỉ đọc; học tiếp = Goal mới). `PAUSED → ACTIVE` khi hết hạn Pause hoặc resume sớm và chưa vượt trần.
- Task: `TODO ⇄ COMPLETED` (tick/bỏ tick: bỏ tick xóa `completed_at`; tick đặt `reschedule_count=0`), `TODO|IN_PROGRESS → CANCELLED` (đặt `scheduled_date=NULL`). `TODO → IN_PROGRESS` khi bắt đầu phiên **và** mọi tiền đề `COMPLETED` (nếu không: BLOCKED, khóa Start Session). Gián đoạn phiên: task chưa tick → `TODO` Backlog.
- Session: `IN_PROGRESS → COMPLETED | PARTIAL_COMPLETED | CANCELLED`; sau đó bất biến (không mở lại; muốn học tiếp tạo phiên mới). Start cần ≥1 task có lịch trong ngày; tối đa 1 phiên `IN_PROGRESS`/user.
- Proposal: `DRAFT → APPLIED | DISCARDED`; ≤1 DRAFT/roadmap.
- Derived (không lưu): `OVERDUE`, `BLOCKED`, `STALLED (reschedule_count>=3)`.

## 4. Quá hạn (UC-22 / FR-ADAPT-001)
- Chạy hằng ngày **00:05 theo `User.timezone`** (SRS). ADR-004/010 ghi "00:05 UTC+7" — xem conflicts #2. Cách cài đề xuất để đúng cả hai: scheduler tick mỗi 15–30 phút; với mỗi user lấy `local_now`; nếu `local_now ≥ 00:05` và chưa quét ngày `local_date` đó thì quét (lũy đẳng bằng bảng/khóa `(user_id, local_date)`); `SKIP LOCKED`.
- Chỉ xét roadmap `ACTIVE` (PAUSED/ARCHIVED không quét). Gửi email qua `EmailNotificationPort` (SMTP adapter + mock). Không gọi LLM. UI "Needs Attention" lấy danh sách OVERDUE kèm nút "Dời lịch hợp lý bằng AI" theo roadmap.
- Dời thủ công (UC-13) hoặc AI Reschedule (UC-21) mới đổi `scheduled_date`, tăng `reschedule_count`, ghi `schedule_change_logs`. `reschedule_count >= 3` ⇒ STALLED: khóa dời tự động, phát `TaskStalledThresholdReachedEvent`; người học chọn: Re-commit ngày mới / AI Micro-Stepping (tách thành 2–3 task ≤30 phút) / chuyển Backlog hoặc Cancel.

## 5. Pause / Resume (UC-20)
- `PauseRecord(start,end)` hợp lệ. `DominoShiftEngine` (thuần) tính dịch chuyển theo số ngày khả dụng, kiểm qua UC-12, ghi `schedule_change_logs` (trước/sau, lý do, số ngày). Không tăng `reschedule_count`. Resume sớm/hết hạn ⇒ ACTIVE nếu chưa vượt trần gói.

## 6. Phiên học (UC-14/15)
- Heartbeat `POST /api/v1/sessions/{id}/heartbeat` mỗi 60s ghi `actual_minutes` + `last_heartbeat_at`. Sweeper mỗi 60s quét `IN_PROGRESS` có `last_heartbeat_at < now()-5m`, áp OS-01, phát `StudySessionCompletedEvent` (outbox).
- Scratchpad/Key Takeaways lưu `study_notes`; ghi chú nháp bảo mật không đưa vào LLM.

## 7. Learner Profile (FR-PROFILE-001)
- Cập nhật bất đồng bộ qua `StudySessionCompletedEvent`. `D_opt` = trung vị thời lượng thực học hiệu quả khi ≥5 phiên (lọc <5 hoặc >180 phút; kẹp [15,120]); `β_bias` = thực tế/dự kiến khi ≥8 task hoàn thành, kẹp [0.50, 2.00]; `peak_productivity_slots` & `weekly_completion_rate` từ 14 ngày gần nhất.
- Cold start (`is_cold_start=TRUE`): `D_opt=25`, `β_bias=1.00`, peak = `["MORNING","EVENING"]`. Người học có thể xem và **Reset** về cold start.

## 8. Bảng giới hạn số (đừng hard-code rải rác — gom vào config/domain constants)
| Hằng | Giá trị |
|---|---|
| Heartbeat / ngưỡng treo | 60s / 5 phút |
| Quota TTL / sweeper | 120s / 60s |
| AI hard timeout | 55s (hiển thị ≤60s) |
| Retry AI | 2 lần, backoff 2s/4s, trần 10s, full jitter |
| Tier 3 timeout | ≤5s, fail-open |
| Soft Overflow | ≤30 phút, chỉ task cuối ngày Mode B |
| Mode A | 0.5–14 giờ/ngày |
| Task thủ công | 15–240 phút |
| Task/khối AI | xem conflicts #3 |
| Roadmap ACTIVE | Free 3 / Premium 15 |
| Quota AI/tháng | Free 30 / Premium 300 |
| STALLED | `reschedule_count >= 3` |
| Payment order TTL | 15 phút |
| Access / Refresh / Admin session | 15 phút / 7 ngày / 8 giờ tuyệt đối |
| WebCal token | 32 byte hex |
| REST P95 | ≤250ms (ADR-002); SRS: ≤200ms với 20 user đồng thời |
| TTFT SSE | ≤2.5s |

## 9. Báo cáo & AI Review (UC-18/19)
- Thống kê toán học tất định (Adherence = buổi tham gia / buổi đã lên lịch, loại khoảng PAUSED; Velocity...) phải chính xác 100% và độc lập LLM. AI Review (UC-19, `<<extend>>` UC-18) chỉ định tính, dùng số liệu đã tính + Key Takeaways đã sanitize.

## 10. Admin (UC-23/24/25)
- Quản lý user/tier/quota, đối soát giao dịch với Payment Gateway, dashboard giám sát (`ai_usage_logs`, sức khỏe hệ thống, doanh thu). Phản hồi ≤500ms, non-blocking; mọi thao tác nhạy cảm vào audit stream; ADMIN session 8h.
