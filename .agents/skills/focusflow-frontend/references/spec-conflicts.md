# Mâu thuẫn SRS v1.3, ADR và trạng thái triển khai

Nguồn nghiệp vụ hiện hành: `docs/srs/srs-v1.3.md` (03/11/2026, UC-01..UC-28, 35 bảng đích). ADR-001..010 quyết định kỹ thuật. Skill cũ từng dựa vào SRS v1.2/24 bảng; số UC và mô hình dữ liệu đó không còn là nguồn chuẩn.

## Quy tắc phân xử

1. Hành vi, BUSR/FR, state machine và số UC: theo SRS v1.3. Kiến trúc, thư viện và hạ tầng: theo ADR.
2. Nếu SRS và ADR quy định khác nhau, chọn hướng bảo toàn bất biến người học rồi báo rõ mâu thuẫn và tài liệu cần sửa. Không sửa SRS/ADR khi chưa được cho phép.
3. Đích 35 bảng không đồng nghĩa đã triển khai: Alembic hiện tạo 28 bảng. Không dùng bảng chưa có migration; không tự thêm bảng ngoài thiết kế.

## Các quyết định cần giữ

- **AI overdue recovery:** SRS `UC-23`/BUSR-02 yêu cầu `ScheduleProposal(DRAFT)` qua validation gate 3 tầng; chỉ Apply mới đổi `OfficialSchedule` và tăng `reschedule_count`. ADR-004/009/010 còn có mô tả cũ bỏ gate hoặc tăng ngay; cần cập nhật các ADR đó khi được phép.
- **Quét quá hạn:** `UC-25`, lúc 00:05 theo `User.timezone`; ADR-004/010 ghi UTC+7 cố định. Theo SRS để ngày học của người dùng đúng múi giờ.
- **Thời lượng:** SRS v1.3 quy định task/khối AI 30–120 phút, thủ công 15–240 phút; ADR-009 còn ghi 15–120 cho AI. Theo SRS; micro-step 10–15 phút của `UC-15` là luồng riêng.
- **UC mới:** `UC-13` Today Focus, `UC-14` phiên học, `UC-15` MVS, `UC-16` khôi phục phiên, `UC-17` Google Calendar, `UC-18` đồng bộ lịch, `UC-19` thống kê, `UC-20` Prove Mode, `UC-21` Weekly Review, `UC-22` Pause/Domino, `UC-23` overdue recovery, `UC-24` Reset Ritual, `UC-25` tiến trình nền, `UC-26..28` admin. Đọc tên UC trong SRS khi dùng số.
- **Payment:** SRS có `EXPIRED` và `expires_at` 15 phút; ADR-007 cũ chỉ nêu bốn trạng thái. Theo SRS.
- **CalendarConnection:** đã được tạo bởi migration `0006_calendar_connections_and_schedule_blocks.py`; ghi chú cũ nói không có bảng đã lỗi thời.
- **Hiệu năng:** API nội bộ ≤200ms ở 20 user đồng thời theo SRS, TTFT ≤2.5s và hard timeout LLM 55s theo ADR/SRS.

Khi phát hiện chênh lệch mới, ghi tài liệu A/B, lựa chọn và lý do trong báo cáo cho người dùng; đề xuất cập nhật tài liệu tương ứng.
