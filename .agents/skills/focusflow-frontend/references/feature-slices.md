# Hành vi màn hình theo feature slice (SRS v1.2)

Nguồn: SRS v1.2 + ADR-003/005/009/010. Số UC theo SRS v1.2 (xem `spec-conflicts.md` #4). Nếu cần chi tiết luồng chính/thay thế của một UC, đọc `docs/uml/use-case-specifications.md` trong repo (nếu có) trước khi giả định.

Mục lục: 0. Quy ước chung · 1. auth · 2. dashboard · 3. planning · 4. workspace · 5. calendar · 6. tasks · 7. analytics · 8. settings · 9. admin · 10. Mã lỗi → UI

## 0. Quy ước chung cho mọi màn hình
- Mỗi trang có đủ: loading (skeleton giữ kích thước), empty (giải thích + hành động tiếp theo), error (mã lỗi → thông điệp + Thử lại), success.
- Hiển thị gói (Free/Premium) và quota AI còn lại ở nơi có nút gọi AI; hết quota ⇒ nút Nâng cấp Premium.
- Mọi nút gọi AI: disable khi đang chạy, hiển thị "còn N lượt", có lối thoát "Lập kế hoạch thủ công".
- Ngày/giờ hiển thị theo `User.timezone`; ghi rõ múi giờ ở nơi dễ nhầm (lịch rảnh, lịch học).
- Xác nhận hành động phá hủy/khó đảo ngược (lưu trữ lộ trình, reset token, hạ gói, xóa/hủy task) bằng `ConfirmPopup`/Dialog nêu hệ quả cụ thể.

## 1. `auth/` — UC-01, UC-02
- Đăng ký, đăng nhập, quên mật khẩu, Onboarding bắt buộc trước khi tạo kế hoạch (BUSR-01): chọn múi giờ (IANA, mặc định theo trình duyệt nhưng cho sửa), thiết lập lịch rảnh tối thiểu, làm quen quota.
- Phiên: cookie; không giữ token trong JS. Hết phiên ⇒ đưa về login kèm `returnUrl`. ADMIN: phiên tuyệt đối 8 giờ ⇒ báo trước khi hết hạn nếu có thể.
- Lỗi đăng nhập: thông điệp chung (không tiết lộ email tồn tại); rate limit 429 ⇒ hiển thị thời gian chờ từ `Retry-After`.
- Điểm Lighthouse a11y ≥ 90 (Onboarding là trang bắt buộc kiểm).

## 2. `dashboard/`
- Tiến độ hôm nay, task hôm nay, truy cập nhanh "Bắt đầu phiên học".
- **Needs Attention**: danh sách task `OVERDUE` nhóm theo **lộ trình** (không phải toàn cục), mỗi nhóm có nút **"Dời lịch hợp lý bằng AI"** (UC-21) và liên kết dời thủ công (UC-13). Chỉ roadmap `ACTIVE`. Nhóm có task `STALLED` hiển thị cờ riêng và nút "Can thiệp" thay vì nút AI (khóa dời tự động).
- Banner khi quota AI sắp hết/hết. Không tự gọi AI khi vào trang.

## 3. `planning/` — UC-07, 08, 09, 10 (+12 gate)
Luồng AI 2 cấp, 2 chặng SSE mỗi cấp (chi tiết mẫu code ở `angular-patterns.md` §5):
1. **Goal** (UC-07): nhập mục tiêu → câu hỏi làm rõ (FR-GOAL) → "Tạo khung lộ trình bằng AI" → stream Milestones → người học **sửa/sắp xếp/Approve Milestones** (hoán đổi thứ tự được; backend dùng ràng buộc deferrable).
2. **Schedule Proposal** (UC-08): sau Approve → stream → bản nháp `DRAFT` → **màn xem/diff/chỉnh sửa** (kéo-thả hoặc sửa ngày/thời lượng) → **Áp dụng**. Hiển thị:
   - cảnh báo advisory sư phạm (Tier 3) nếu có — nhẹ, không chặn;
   - ngày bị quá tải/vi phạm tô đỏ khi Apply bị từ chối (`VALIDATION_OVERLOAD`, `DEPENDENCY_CYCLE_DETECTED`) kèm chi tiết (ngày, số phút vượt, cặp task tạo chu trình);
   - **Soft Overflow ≤30 phút** (task cuối ngày Mode B): cảnh báo trực quan + hộp xác nhận rõ ràng trước khi gửi Apply (BUSR-04).
   - Khi bản nháp đã `APPLIED`/`DISCARDED`: chỉ đọc. "Tạo lại" ⇒ bản cũ `DISCARDED` (cảnh báo người dùng).
3. **Thủ công** (UC-09): tạo lộ trình/task/lịch không cần AI, vẫn qua gate khi lưu; là đường lui khi AI lỗi hoặc hết quota.
4. **Danh mục lộ trình** (UC-10): danh sách theo trạng thái (`INITIALIZED/ACTIVE/PAUSED/COMPLETED/ARCHIVED`), đổi tên/cập nhật, **Lưu trữ** (confirm: task chưa xong sẽ chuyển CANCELLED, giải phóng lịch và 1 suất ACTIVE; không hoàn tác). `COMPLETED/ARCHIVED` chỉ đọc. Chạm trần gói (Free 3 / Premium 15 ACTIVE) ⇒ giải thích + gợi ý Nâng cấp hoặc Pause/Archive bớt.
- Lỗi AI (timeout 55s, 429, 503, schema sau 2 retry): thông điệp theo §10, luôn có Thử lại + Lập kế hoạch thủ công; quota không bị trừ (có thể nói điều đó).
- Hiển thị `validation_retry` ("AI đang tự hiệu chỉnh…") để minh bạch.

## 4. `workspace/` — UC-14 (+15)
- Chọn ≥1 task đã có lịch trong ngày → "Start Session" (task `BLOCKED` vì tiền đề chưa xong ⇒ nút khóa kèm lý do và liên kết tới tiền đề). Chỉ 1 phiên `IN_PROGRESS`/người dùng: nếu đã có, đưa vào phiên đó (API trả 409 + id).
- Pomodoro/Stopwatch, checklist task (tick tức thời, optimistic), Scratchpad Markdown, Key Takeaways; tự lưu ghi chú (debounce) và báo trạng thái lưu.
- Heartbeat 60s (xem patterns §7). Mất kết nối: banner; không mất dữ liệu cục bộ chưa gửi (giữ ghi chú trong bộ nhớ và gửi lại).
- Kết thúc/Dừng sớm: màn tóm tắt — số phút thực học (lấy từ server), task xong giữ nguyên, task chưa xong về Backlog "không phạt". Trạng thái phiên: `COMPLETED`/`PARTIAL_COMPLETED` (≥1 task xong hoặc ≥50% thời lượng dự kiến)/`CANCELLED`. Phiên đã đóng không mở lại; "Học tiếp" = tạo phiên mới.
- a11y: phím tắt có thể truy cập, focus rõ; thông báo hết giờ bằng `aria-live`; không phát âm thanh tự động mà không có tùy chọn.

## 5. `calendar/` — UC-13, 16, 17
- Lịch chính thức (chỉ `OfficialSchedule`) dạng tuần/tháng/timeline; Proposal/Backlog **không** xuất hiện như lịch chính thức (có thể là lớp "bản nháp" tách biệt rõ).
- Dời thủ công (UC-13): kéo-thả/chọn ngày; Backlog → xếp lịch; lỗi gate hiển thị như §3. Mỗi lần dời do quá hạn tăng `reschedule_count` (hiển thị badge khi gần ngưỡng 3).
- Google Calendar (UC-16): luồng OAuth (mở cửa sổ/redirect, xử lý `state`); hiển thị trạng thái kết nối, phạm vi quyền tối thiểu (chỉ đọc bận + sự kiện do FocusFlow tạo), nút ngắt kết nối. Khoảng bận hiển thị mờ và được trừ khỏi quỹ giờ rảnh.
- WebCal/.ics (UC-17): tải `.ics`; tạo/Reset WebCal — URL **chỉ hiện một lần** kèm nút sao chép; Reset có confirm ("liên kết cũ sẽ ngừng hoạt động ngay").
- Chế độ offline demo: nhãn "Lịch giả lập" khi `CALENDAR_PROVIDER=local_mock` (backend báo qua config/health nếu có).

## 6. `tasks/` — UC-11, UC-21
- Danh sách theo roadmap/milestone, Backlog (`scheduled_date = NULL`), tạo/sửa/hủy (hủy = `CANCELLED`, không xóa cứng). Thời lượng thủ công 15–240 phút.
- Phụ thuộc (DAG): chọn tiền đề; backend từ chối chu trình (`DEPENDENCY_CYCLE_DETECTED`) — UI hiển thị cặp task gây chu trình. Task có tiền đề chưa xong hiển thị `BLOCKED`.
- **STALLED dialog** (`reschedule_count >= 3`): 3 lựa chọn — (1) Cam kết ngày cố định mới (chọn slot, qua gate); (2) AI Micro-Stepping (tách thành 2–3 task ≤30 phút, người học xem rồi mới áp dụng); (3) Đưa về Backlog / Hủy. Lý do cho người học bằng ngôn ngữ không phán xét (hỗ trợ động lực, theo Temporal Motivation Theory).

## 7. `analytics/` — UC-18, 19, 20
- Thống kê định lượng (Adherence, Velocity, tiến độ roadmap) — số liệu **do server tính**, UI không tự tính lại. Biểu đồ PrimeNG Chart/`chart.js`; mọi biểu đồ có bảng/tóm tắt văn bản thay thế (a11y) và không chỉ dựa vào màu.
- AI Review (UC-19, mở rộng UC-18): nút "Yêu cầu AI đánh giá" (tiêu hao 1 lượt quota — nói rõ trước), hiển thị nhận xét định tính. AI Review **không** có nút "áp dụng thay đổi lịch" (BUSR-12); gợi ý điều chỉnh chỉ dẫn người học tới thao tác thủ công/AI Reschedule có Apply.
- Pause/Resume (UC-20): chọn `[PauseStart, PauseEnd]` → xem trước Domino Shift (nếu API hỗ trợ preview) → xác nhận. Trong thời gian PAUSED không có cảnh báo quá hạn; tiếp tục sớm/hết hạn ⇒ ACTIVE (có thể bị chặn nếu chạm trần gói).

## 8. `settings/` — UC-03, 04 (+05 kết quả)
- Hồ sơ & múi giờ (FR-AUTH-003). **Lịch rảnh lai**: Mode A (giờ/ngày, 0.5–14h) hoặc Mode B (khung giờ; hỗ trợ vắt nửa đêm; không overlap). Giải thích Soft Overflow.
- **Learner Profile** (D_opt, β_bias, khung giờ đỉnh, tỷ lệ hoàn thành 14 ngày): chỉ đọc + nút **Reset** (về cold start: 25 phút, 1.00, MORNING/EVENING) có confirm. Hiển thị "đang ở chế độ khởi đầu" khi `is_cold_start`.
- Nâng cấp Premium (UC-04): tạo đơn → hiển thị QR/Checkout URL (PayOS/VNPay hoặc mock) với **đếm ngược hết hạn 15 phút** → poll/refresh trạng thái đơn (`PENDING/PAID/FAILED/CANCELLED/EXPIRED`) hoặc SSE nếu backend có; `PAID` ⇒ cập nhật gói/quota ngay; `EXPIRED` ⇒ cho tạo đơn mới. Chế độ `local_mock`: có nút "Giả lập thanh toán thành công" **chỉ hiện khi backend báo chế độ mock**; không bao giờ hiển thị trong production.
- Hạ gói: giải thích việc roadmap vượt 3 bị chuyển `PAUSED` (giữ 3 có `target_date` sớm nhất — EDF).

## 9. `admin/` — UC-23, 24, 25
- Chỉ ADMIN (`roleGuard`), nhưng xử lý 401/403 từ server như nguồn sự thật. Bảng PrimeNG phân trang/lọc/sắp xếp phía server.
- UC-23: tìm user, khóa/mở khóa, đổi gói, chỉnh quota — mọi hành động nhạy cảm có confirm nêu rõ hệ quả, ghi lý do (nếu API hỗ trợ), phản hồi ≤500ms.
- UC-24: đối soát giao dịch (trạng thái, `transaction_ref`, cổng, số tiền, thời điểm), so khớp với cổng thanh toán.
- UC-25: dashboard giám sát (sức khỏe dịch vụ, log AI từ `ai_usage_logs`: model, tokens, latency, lỗi; doanh thu). Không chặn UI khi một widget lỗi (mỗi widget có error/retry riêng, tải song song). Không hiển thị PII không cần thiết.

## 10. Mã lỗi → UI

| `code` | Hiển thị | Hành động |
|---|---|---|
| `QUOTA_EXHAUSTED` (429) | "Bạn đã dùng hết lượt AI của gói hiện tại" | Nút **Nâng cấp Premium**, lập kế hoạch thủ công |
| `AI_GATEWAY_TIMEOUT` (504) | "Dịch vụ AI phản hồi chậm" | Thử lại · Lập kế hoạch thủ công; nói quota đã hoàn lại |
| `AI_RATE_LIMIT_EXCEEDED` (429) | "Hệ thống AI đang bận, vui lòng đợi giây lát" | Thử lại sau (đếm lùi) · Thủ công |
| AI 503 / bảo trì (circuit breaker OPEN) | "Dịch vụ AI tạm thời gián đoạn" | Lập kế hoạch thủ công |
| `AI_SCHEMA_VALIDATION_ERROR` | "AI chưa tạo được kế hoạch hợp lệ sau 2 lần tự sửa" | Thử lại · Thủ công; gợi ý nới lỏng quỹ giờ/mục tiêu |
| `VALIDATION_OVERLOAD` | tô đỏ các ngày quá tải + số phút vượt | giảm thời lượng/dời ngày rồi Apply lại |
| `DEPENDENCY_CYCLE_DETECTED` | nêu cặp task tạo chu trình | gỡ một phụ thuộc |
| 401 | (interceptor) refresh → login | — |
| 403 | "Bạn không có quyền" | về trang chủ |
| 404 | "Không tìm thấy" (cũng là kết quả với tài nguyên không thuộc user) | quay lại |
| 409 | xung đột trạng thái (đã có phiên đang chạy, proposal đã áp dụng…) | tải lại dữ liệu |
| 422 | lỗi theo field/`details` | gắn vào form |
| 5xx/mạng | thông báo chung + `correlation_id` | Thử lại |
Không đổi thông điệp theo cách làm lộ chi tiết nội bộ. Map code ở **một** file (`core/api/error-messages.ts`) để dễ bảo trì và i18n.
