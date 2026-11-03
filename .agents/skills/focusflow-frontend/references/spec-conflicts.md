# Mâu thuẫn & khoảng trống giữa SRS v1.2 và các ADR

Tài liệu được đối chiếu: `SRS v1.2` (27/10/2026), `ADR-001..010` (cập nhật v2.0 ngày 25/10/2026).

## Nguyên tắc phân xử (dùng khi gặp mâu thuẫn mới)
1. **Yêu cầu nghiệp vụ / hành vi quan sát được** (BUSR, FR, state machine, OS-xx, số UC) → **SRS v1.2** thắng (mới hơn, và tuyên bố đã đồng bộ với ADR).
2. **Cách làm kỹ thuật** (thư viện, kiến trúc, hạ tầng, cấu trúc code) → **ADR** thắng.
3. Con số/ngưỡng bị lệch → chọn phương án **chặt hơn / an toàn hơn** cho người dùng, ghi rõ vào PR/báo cáo, hỏi người dùng xác nhận.
4. Khi áp dụng một giải pháp ở mục dưới: **nói với người dùng một câu** ("SRS và ADR lệch nhau ở X, tôi theo Y vì …; cần cập nhật tài liệu Z"). Không im lặng chọn.
5. Khoảng trống đặc tả: đề xuất tối thiểu hợp lý, đánh dấu `TODO(spec)` trong code/PR, đừng phát minh quy tắc nghiệp vụ lớn.

## #1 AI Reschedule quá hạn có đi qua cổng 3 tầng không? (QUAN TRỌNG)
- ADR-004 §3.3(4), ADR-009 §3.1.1, ADR-010 §3.2(2): **bỏ qua** cổng 3 tầng (bỏ Tier 3; chỉ JSON Schema + kiểm dung lượng/xung đột cơ bản), `reschedule_count` tăng ngay khi bấm.
- SRS v1.2 (BUSR-02, FR-ADAPT-002, §6.4, Glossary "AI Reschedule", RTM): sinh `ScheduleProposal(DRAFT)` cho 1 roadmap, **đi qua đủ cổng 3 tầng (UC-12)**, người học xem diff rồi bấm **Apply**; chỉ khi Apply mới cập nhật `OfficialSchedule` và tăng `reschedule_count` + ghi `schedule_change_logs`. Revision history v1.2 nêu rõ đây là chủ ý để bảo toàn BUSR-02/BUSR-03.
- **Giải quyết:** theo SRS v1.2. Lý do: BUSR-02 nói "mọi kết quả AI … chỉ là Proposal"; bỏ cổng sẽ cho phép AI ghi lịch vượt Mode A/B. Tier 2 tất định tuyệt đối không được bỏ; Tier 3 vẫn advisory/fail-open nên chi phí thấp.
- Cần người dùng: cập nhật ADR-004/009/010 cho khớp (nhắc ở cuối báo cáo nếu task liên quan).

## #2 Giờ quét quá hạn: UTC+7 cố định hay theo múi giờ từng người học?
- ADR-004/010: `00:05 UTC+7`. SRS FR-ADAPT-001: `00:05` **theo `User.timezone`** (IANA, FR-AUTH-003).
- **Giải quyết:** theo SRS (đúng nghiệp vụ; quá hạn cũng tính theo múi giờ người học). Cài bằng tick định kỳ + lũy đẳng `(user_id, local_date)` (xem `domain-rules.md` §4). Với người học ở UTC+7 kết quả trùng ADR.

## #3 Dải thời lượng task/khối do AI sinh
- ADR-009 Tier 1: `[15, 120]` phút. SRS v1.2 (revision history, RTM): AI **30–120**, thủ công **15–240**.
- **Giải quyết:** dùng hằng số cấu hình duy nhất `AI_BLOCK_MIN_MINUTES`/`AI_BLOCK_MAX_MINUTES`; mặc định theo SRS (30–120) cho Tier 1; thủ công & CHECK DB `[15, 240]`. Lưu ý micro-stepping (UC-21/STALLED) tạo task ≤30 phút ⇒ ngoại lệ có chủ đích với dải AI, vì đây là tách nhỏ có chủ đích (kiểm bằng validator riêng của micro-stepping, vẫn ≥15). Hỏi người dùng chốt 15 hay 30.

## #4 Đánh số Use Case
SRS v1.2: **25 UC** (UC-01..UC-25, UC-12 là hàm con kiểm định dùng chung). ADR còn dùng bộ 19 UC cũ (và đôi chỗ ADR tự lệch nhau). Dùng số của SRS trong code/commit/tài liệu mới. Ánh xạ tham khảo (chỉ mang tính gợi ý; khi nghi ngờ, đối chiếu tên UC trong SRS §3.2):

| Ý nghĩa | UC cũ (ADR) | UC mới (SRS v1.2) |
|---|---|---|
| Đăng ký / Đăng nhập | 01 / 02 | 01 / 02 |
| Hồ sơ & lịch rảnh | 03 | 03 |
| Nâng cấp Premium / Thanh toán–webhook | 04 / 05 | 04 / 05 |
| Làm mới quota & thu hồi reservation | (sweeper) | 06 |
| Goal + Milestone AI | 06 | 07 |
| Sinh & duyệt Schedule Proposal | 07 | 08 |
| Tạo lộ trình thủ công / Quản lý danh mục | 09 / – | 09 / 10 |
| Quản lý task & DAG | 09 | 11 |
| Kiểm định lịch (gate) | (ngầm) | 12 |
| Xem lịch & dời thủ công | 10/13 | 13 |
| Phiên học & ghi chú / tự chốt phiên treo | 10–11 | 14 / 15 |
| Google Calendar sync / WebCal .ics | 13 | 16 / 17 |
| Thống kê / AI Review | 14 / 15 | 18 / 19 |
| Pause–Resume (Domino) | 16 | 20 |
| AI Reschedule / Quét quá hạn + hồ sơ + email | 17 | 21 / 22 |
| Admin: user–quota / đối soát / giám sát | 18 / – / 19 | 23 / 24 / 25 |

## #5 Trạng thái giao dịch thanh toán
ADR-007: `PENDING, PAID, FAILED, CANCELLED`. SRS v1.2: thêm `EXPIRED` + `expires_at` (TTL 15 phút). **Giải quyết:** theo SRS (5 trạng thái); cần migration CHECK/enum và cập nhật ADR-007/data dictionary.

## #6 `CalendarConnection` không có bảng
SRS §12 tách `CalendarConnection` (OAuth) khỏi `WebCalToken`; ADR-007 liệt kê đúng 24 bảng và không có bảng cho OAuth token (dù ADR-008 yêu cầu lưu token mã hóa trong DB). **Giải quyết:** hỏi người dùng trước khi thêm bảng; đề xuất `calendar_connections` (user_id, provider, encrypted_access_token, encrypted_refresh_token, scopes, expires_at, status) — cập nhật số bảng (25) ở mọi nơi.

## #7 Mục tiêu hiệu năng
ADR-002: REST P95 ≤250ms, TTFT ≤2.5s. SRS NFR-PERF-002: API nội bộ ≤200ms ở 20 user đồng thời; UI phản hồi ≤500ms; NFR-PERF-001: sinh lịch ≤60s, hard timeout 55s. **Giải quyết:** mục tiêu đồng thời — dùng số chặt hơn khi tối ưu (≤200ms @20 CCU cho API thường), và TTFT/hard timeout cho luồng AI.

## #8 Mật khẩu
SRS cho phép Argon2id **hoặc** bcrypt cost ≥10; ADR-008 chọn Argon2id (`pwdlib`). **Theo ADR** (cụ thể hơn, không mâu thuẫn).

## #9 Phiên ADMIN 8 giờ tuyệt đối
Có trong SRS FR-ADM-001, không có trong ADR-008 (access 15m/refresh 7d). **Giải quyết:** áp trần tuyệt đối 8h cho role ADMIN (lưu `session_started_at` trong token family; refresh không vượt quá).

## #10 Tham chiếu chéo cũ trong SRS
SRS trỏ `sanitizePromptContext()` và harness về `ADR-003`, trạng thái circuit breaker về `ADR-007`; thực tế nội dung ở ADR-008/009/005 (và ADR-003/007 là frontend/CSDL). Bỏ qua trỏ sai; dùng ADR đúng chủ đề. Circuit breaker (NFR-AI-002) chưa có ADR — xem `ai-and-quota.md` §1.

## #11 ADR-003 (frontend) lệch số UC
Mapping 9 feature slice → UC trong ADR-003 dùng số cũ. Xem `focusflow-frontend/references/feature-slices.md` cho mapping đã chuẩn hóa theo SRS v1.2.

## Cách xử lý mâu thuẫn mới phát hiện
Ghi nhận ngắn gọn (tài liệu A nói gì, tài liệu B nói gì, bạn chọn gì, vì sao), áp dụng nguyên tắc phân xử ở đầu file, và đề xuất người dùng cập nhật tài liệu. Có thể thêm mục vào file này khi người dùng đồng ý.
