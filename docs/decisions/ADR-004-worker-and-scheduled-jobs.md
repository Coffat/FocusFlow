# ADR-004: Lựa chọn Giải pháp Hàng đợi Tác vụ Nền & Tác vụ Định kỳ: Celery, Redis & Celery Beat

* **Trạng thái:** Được chấp thuận (Approved)
* **Ngày quyết định:** 29/09/2026
* **Người quyết định:** Vũ Toàn Thắng (Lead BA / System Architect), Phan Đình Duẩn (Senior BA / Quality Lead)
* **Căn cứ đánh giá:** Khung Rubric Đồ án Tốt nghiệp CNTT — Tiêu chí TC2.1 & TC2.3 (Mức 5)
* **Yêu cầu liên quan:** FR-SESSION-003, FR-ADAPT-001, FR-REPORT-001, OS-07

---

## 1. Ngữ cảnh & Đặt vấn đề (Context)
Hệ thống FocusFlow có các nghiệp vụ không thể hoặc không nên xử lý đồng bộ trong chu kỳ Request-Response của HTTP API:
1. **Quét và chốt các phiên học bị gián đoạn/mất mạng (`OS-07`):** Định kỳ mỗi 5 phút, hệ thống cần quét các phiên học không nhận được Heartbeat để áp dụng quy tắc `OS-01` (chuyển sang `PARTIAL_COMPLETED` hoặc `CANCELLED`).
2. **Quét tác vụ quá hạn tất định (`FR-ADAPT-001`):** Chạy vào 00:01 hàng ngày để gắn cờ các task có `scheduled_date < TODAY`.
3. **Tổng hợp báo cáo học tập định kỳ tuần (`FR-REPORT-001`):** Thực hiện tính toán thống kê số học cho toàn bộ người dùng vào tối Chủ Nhật hàng tuần.

---

## 2. Các phương án xem xét (Alternatives)

### Phương án A: FastAPI In-Process BackgroundTasks
* Tận dụng `BackgroundTasks` có sẵn của FastAPI và chạy vòng lặp vô tận `asyncio.sleep` trong ứng dụng.
* *Ưu điểm:* Không cần cài thêm thư viện hay dựng thêm container worker.
* *Nhược điểm:* Tác vụ chạy chung process với API; nếu API bị khởi động lại (restart) thì các tác vụ nền đang chạy sẽ bị mất; không có cơ chế quản trị hàng đợi bền vững hay retry tự động.

### Phương án B: ARQ / Taskiq + Redis
* Thư viện hàng đợi bất đồng bộ hiện đại thuần asyncio cho Python.
* *Ưu điểm:* Nhẹ, tích hợp trực tiếp với async event loop của FastAPI.
* *Nhược điểm:* Cộng đồng nhỏ hơn, ít tài liệu hơn; thiếu các công cụ giám sát trực quan chuyên nghiệp.

### Phương án C: Celery + Redis + Celery Beat (Được chọn)
* Sử dụng Celery làm Worker Queue xử lý tác vụ, Redis làm Message Broker và Result Backend, Celery Beat đóng vai trò bộ lập lịch định kỳ (Periodic Scheduler).
* *Ưu điểm:*
  * **Tiêu chuẩn công nghiệp:** Thư viện hàng đầu, tài liệu đầy đủ và độ tin cậy tuyệt đối trong môi trường Python.
  * **Celery Beat:** Cơ chế lập lịch cron-like chuẩn xác, cấu hình linh hoạt.
  * **Giám sát trực quan (Flower Dashboard):** Cung cấp giao diện web theo dõi tình trạng worker, danh sách task và thống kê hiệu năng để trình chiếu thực chứng ấn tượng trước Hội đồng bảo vệ đồ án tốt nghiệp.

---

## 3. Quyết định (Decision)
**Chấp thuận Phương án C: Sử dụng Celery, Redis và Celery Beat cho toàn bộ Hàng đợi Tác vụ Nền và Tác vụ Định kỳ.**

---

## 4. Lý do & Đánh đổi (Rationale & Trade-Offs)
* **Cô lập Rủi ro và Tách biệt Trách nhiệm:** Quá trình quét timeout hàng ngàn phiên học hoặc tính toán báo cáo tuần được đẩy hoàn toàn sang tiến trình worker độc lập, bảo đảm Backend API chính luôn nhẹ nhàng và giữ vững cam kết phản hồi $\le 200$ms (`NFR-PERF-002`).
* **Tính Bền vững (Durability & Retries):** Hỗ trợ cơ chế retry tự động với exponential backoff khi gặp sự cố CSDL tạm thời.

---

## 5. Hệ quả (Consequences)
* **Tích cực:** Hệ thống vận hành ổn định, có công cụ giám sát chuyên nghiệp, tự động hóa 100% các công việc bảo trì hệ thống.
* **Chi phí Vận hành:** Trong môi trường Docker Compose cần thêm 2 container (`worker` và `beat`). Đổi lại, tài nguyên tiêu thụ của mỗi container Celery là rất nhỏ (~50MB RAM).
