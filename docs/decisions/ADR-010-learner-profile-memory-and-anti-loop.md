# ADR-010: Lựa chọn Thiết kế Hồ sơ Người học (Learner Profile Memory) theo Mô hình Zimmerman SRL và Cơ chế Ngắt mạch Chống lặp Quá hạn (Overdue Anti-Loop)

* **Trạng thái:** Được chấp thuận (Approved — Đã chuẩn hóa theo SRS v1.1 & Kết quả Rà soát Kiến trúc)
* **Ngày quyết định:** 16/10/2026
* **Người quyết định:** Vũ Toàn Thắng, Phan Đình Duẩn
* **Căn cứ đánh giá:** Khung Rubric Đồ án Tốt nghiệp CNTT — Tiêu chí TC2.1, TC2.3 (Mức 5)
* **Yêu cầu liên quan:** FR-ADAPT-001, FR-ADAPT-003, FR-PAUSE-001, FR-PAUSE-002, FR-PROFILE-001, BUSR-06, BUSR-07, BUSR-09

---

## 1. Ngữ cảnh & Đặt vấn đề (Context)
1. **Thiếu Khả năng Cá nhân hóa Thực chứng:** Trong mô hình Self-Regulated Learning (Zimmerman 2002), giai đoạn Phản tư (Self-Reflection) đóng vai trò quyết định để tái lập kế hoạch (Forethought) hiệu quả hơn. Hiện tại, FocusFlow chỉ nhận dữ liệu đầu vào tĩnh; AI Planner không học hỏi từ lịch sử thực tế của sinh viên (thường học bao nhiêu phút thì đuối, có xu hướng ước lượng thiếu thời gian hay không).
2. **Hiện tượng Tuyết lăn Trì hoãn (Procrastination Snowball):** Khi một task bị trễ hạn, cơ chế quét quá hạn tự động dời sang ngày tiếp theo. Nếu sinh viên liên tục bỏ bê task nhiều ngày liền, việc tự động dời lịch vô hạn gây ra tình trạng dồn ứ lịch trình ảo, phá vỡ tính cam kết tâm lý của người học.

---

## 2. Các phương án xem xét (Alternatives)

### Hạng mục 1: Kiến trúc Hồ sơ Người học (Learner Profile Memory)
* **Phương án A — Tính toán Trực tiếp Đồng bộ (Online Real-time):** Tính toán lại toàn bộ chỉ số profile ngay trong request HTTP kết thúc phiên học (`FinishSession`).
  * *Nhược điểm:* Làm chậm API kết thúc phiên (tăng latency $> 500\text{ms}$); dễ xung đột khóa dữ liệu.
* **Phương án B — Tích hợp Vector DB & Agent Memory Framework ngoài (như Honcho trong Hermes):**
  * *Nhược điểm:* Quá phức tạp và cồng kềnh đối với đồ án tốt nghiệp; Honcho tập trung vào persona đàm thoại chứ không trích xuất số liệu học tập định lượng.
* **Phương án C — Tổng hợp Bất đồng bộ qua Celery vào Bảng `learner_profiles` (Được chọn):**
  * Tách biệt hoàn toàn: Tác vụ nền Celery chạy định kỳ (sau mỗi $\ge 5$ phiên hoàn thành hoặc tổng hợp hàng tuần).
  * Định nghĩa ngưỡng dữ liệu riêng biệt cho từng chỉ số để tránh kết luận vội:
    - $D_{opt}$ (thời lượng tập trung tối ưu): Cần $\ge 5$ phiên, lọc bỏ ngoại lệ $< 5$p hoặc $> 180$p trước khi tính Median.
    - $\beta_{bias}$ (hệ số chệch ước lượng): Cần $\ge 8$ task, kẹp trong khoảng an toàn $[0.50, 2.00]$.
    - Khung giờ đỉnh: Cần $\ge 10$ phiên qua 14 ngày.
  * Có cơ chế Cold Start rõ ràng (dưới ngưỡng dùng giá trị chuẩn); đóng gói System Prompt tinh gọn $\le 60$ tokens để bảo đảm prompt hygiene; người dùng có quyền xem và Reset Profile.

### Hạng mục 2: Cơ chế Chống lặp Quá hạn (Overdue Anti-Loop)
* **Phương án A — Cho phép Dời lịch Vô hạn, chỉ Tăng Priority:**
  * *Nhược điểm:* Task bị trôi dạt vĩnh viễn, người học mất cảm giác trách nhiệm với mục tiêu.
* **Phương án B — Tự động Xóa hoặc Đẩy thẳng về Backlog:**
  * *Nhược điểm:* Quá tiêu cực và gây thất lạc nhiệm vụ quan trọng mà không hỏi ý kiến người học.
* **Phương án C — Ngắt mạch tại Ngưỡng 3 lần Dời lịch (`reschedule_count >= 3`) kết hợp Phân lập Domino Shift (Được chọn):**
  * Dựa trên lý thuyết tâm lý học trì hoãn (Steel 2007): Sau 3 ngày liên tiếp trì hoãn, hành vi né tránh đã hình thành.
  * Khi `reschedule_count >= 3`: Khóa dời lịch tự động, chuyển trạng thái dẫn xuất sang `STALLED`, kích hoạt hộp thoại can thiệp với 3 lựa chọn (Cam kết ngày cố định, Chia nhỏ task bằng AI, hoặc Chuyển về Backlog).
  * **Phân lập với Domino Shift:** Khi tạm dừng toàn bộ Roadmap (`FR-PAUSE`), thuật toán Domino Shift tịnh tiến ngày **KHÔNG làm tăng `reschedule_count`** vì đây là quyết định chủ động toàn cục, không phải lỗi bỏ bê task cá nhân.
  * Chống race condition giữa các Celery worker bằng `SELECT ... FOR UPDATE SKIP LOCKED`.

---

## 3. Quyết định (Decision)
**Chấp thuận Phương án C cho cả hai hạng mục: Triển khai Bảng `learner_profiles` tổng hợp bất đồng bộ qua Celery theo chuẩn Zimmerman SRL và Cơ chế Overdue Anti-Loop Circuit Breaker tại ngưỡng 3 lần dời lịch.**

---

## 4. Lý do & Đánh đổi (Rationale & Trade-Offs)
* **Khớp 100% Cơ sở Lý thuyết Khoa học:** Gắn kết chặt chẽ với mô hình Self-Regulated Learning (Zimmerman 2002) và lý thuyết Temporal Motivation Theory (Steel 2007), tạo luận cứ học thuật đắt giá khi bảo vệ đồ án tốt nghiệp.
* **Bảo vệ Trạng thái Hệ thống:** Chặn đứng tình trạng dồn ứ lịch trình ảo; bảo đảm hiệu năng API kết thúc phiên không bị ảnh hưởng.
* **Tôn trọng Quyền Tự chủ của Người học:** Profile chỉ đóng vai trò tư vấn trong prompt, không bao giờ tự ý ghi đè quyết định của người dùng.

---

## 5. Hệ quả (Consequences)
* **Tích cực:** Kế hoạch học tập ngày càng thích ứng chính xác với sức học thực tế của sinh viên; ngăn ngừa bỏ cuộc giữa chừng.
* **Tiêu cực / Rủi ro:** Cần bổ sung bảng `learner_profiles` và cột `reschedule_count` trong CSDL PostgreSQL; cần thêm worker task trong Celery.
