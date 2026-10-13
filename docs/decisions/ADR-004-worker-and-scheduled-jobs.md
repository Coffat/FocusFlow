# ADR-004: Lựa chọn Giải pháp Hàng đợi Tác vụ Nền & Tác vụ Định kỳ: Celery, Redis & Celery Beat
## Phiên bản: v1.1 — Chuẩn hóa Kiến trúc Đồng bộ Bền vững (Persistence Alignment)

* **Trạng thái:** Được chấp thuận (Approved)
* **Ngày quyết định:** 29/09/2026 (Cập nhật chuẩn hóa: 07/10/2026)
* **Người quyết định:** Vũ Toàn Thắng (Lead BA / System Architect), Phan Đình Duẩn (Senior BA / Quality Lead)
* **Căn cứ đánh giá:** Khung Rubric Đồ án Tốt nghiệp CNTT — Tiêu chí TC2.1 & TC2.3 (Mức 5)
* **Yêu cầu liên quan:** FR-SESSION-003, FR-ADAPT-001, FR-REPORT-001, OS-01, OS-07, BUSR-06, BUSR-09, NFR-PERF-002, NFR-AVAIL-001
* **Tài liệu đối chiếu:** `docs/srs/srs-v1.0.md`, `docs/database/schema.sql`, `docs/architecture/system-architecture.md`, `docs/uml/sequence-diagrams.md`

---

## 1. Ngữ cảnh & Đặt vấn đề (Context)
Hệ thống FocusFlow có các nghiệp vụ không thể hoặc không nên xử lý đồng bộ trong chu kỳ Request-Response của HTTP API:
1. **Quét và chốt các phiên học bị gián đoạn/mất mạng (`OS-07`):** Định kỳ mỗi 5 phút, hệ thống cần quét các phiên học không nhận được Heartbeat để áp dụng quy tắc `OS-01` (chuyển sang `PARTIAL_COMPLETED` hoặc `CANCELLED`).
2. **Quét tác vụ quá hạn định kỳ tổng hợp báo cáo (`FR-ADAPT-001`):** Thực thi lúc 00:01 hàng ngày để tổng hợp các nhiệm vụ quá hạn phục vụ nhắc nhở (lưu ý: trạng thái `OVERDUE` trên UI là derived condition, không sửa enum trong CSDL).
3. **Tổng hợp báo cáo học tập định kỳ tuần (`FR-REPORT-001`):** Thực hiện tính toán thống kê định lượng số học và tổng hợp Key Takeaways cho toàn bộ người dùng vào tối Chủ Nhật hàng tuần.
4. **Cơ chế ghi nhận nhịp tim phiên học (`BUSR-09`, `OS-07`):** Chu kỳ gửi Heartbeat từ Study Workspace là 60 giây. Với quy mô thử nghiệm 20 người dùng đồng thời, tần suất ghi nhận chỉ đạt tối đa $\approx 0.33$ writes/giây. Việc ghi nhận trực tiếp vào bảng `study_sessions` trong PostgreSQL (cột `last_heartbeat_at`, `actual_minutes`) hoàn toàn nằm trong ngưỡng chịu tải của PostgreSQL 16 (chỉ mục B-Tree Partial Index `idx_study_sessions_in_progress`), đồng thời loại trừ triệt để nguy cơ mất mát dữ liệu số phút thực học nếu Redis gặp sự cố hoặc restart đột ngột.

---

## 2. Các phương án xem xét (Alternatives Considered)

### Phương án A: FastAPI In-Process BackgroundTasks
* Tận dụng `BackgroundTasks` có sẵn của FastAPI và chạy vòng lặp vô tận `asyncio.sleep` trong ứng dụng.
* *Ưu điểm:* Không cần cài thêm thư viện hay dựng thêm container worker.
* *Nhược điểm:* Tác vụ chạy chung process với API; nếu API bị khởi động lại (restart) thì các tác vụ nền đang chạy sẽ bị mất; không có cơ chế quản trị hàng đợi bền vững hay retry tự động.

### Phương án B: ARQ / Taskiq + Redis
* Thư viện hàng đợi bất đồng bộ hiện đại thuần asyncio cho Python.
* *Ưu điểm:* Nhẹ, tích hợp trực tiếp với async event loop của FastAPI.
* *Nhược điểm:* Cộng đồng nhỏ hơn, ít tài liệu hơn; thiếu các công cụ giám sát trực quan chuyên nghiệp.

### Phương án C: Celery 5.6 + Redis 7 Broker + Celery Beat Scheduler (Được chọn)
* Sử dụng Celery làm Worker Queue xử lý tác vụ nền nặng và tác vụ định kỳ, Redis làm Message Broker và Result Backend (DB 1 và DB 2), Celery Beat đóng vai trò bộ lập lịch định kỳ (Periodic Scheduler).
* Ghi nhận Heartbeat bền vững trực tiếp vào PostgreSQL 16 (`study_sessions.last_heartbeat_at`) để bảo toàn từng phút nỗ lực học tập của người dùng theo chuẩn ACID.
* *Ưu điểm:*
  * **Tiêu chuẩn công nghiệp:** Thư viện hàng đầu, tài liệu đầy đủ và độ tin cậy tuyệt đối trong môi trường Python.
  * **Celery Beat:** Cơ chế lập lịch cron-like chuẩn xác, cấu hình linh hoạt theo từng múi giờ.
  * **Tách biệt tải tính toán:** Các tác vụ phân tích báo cáo tuần nặng nề được đẩy hoàn toàn sang worker, không làm ảnh hưởng đến độ trễ API $\le 200$ms (`NFR-PERF-002`).
  * **Độ bền dữ liệu tối đa (ACID Durability):** Số phút thực học và mốc nhịp tim được bảo lưu trực tiếp trong PostgreSQL, không phụ thuộc vào bộ nhớ tạm TTL của Redis.

---

## 3. Quyết định (Decision)
**Chấp thuận Phương án C:**
1. **Sử dụng Celery 5.6 và Celery Beat** cho toàn bộ Hàng đợi Tác vụ Nền và Tác vụ Định kỳ của hệ thống:
   - Worker chạy tiến trình độc lập trong container `focusflow-worker`.
   - Scheduler chạy tiến trình độc lập trong container `focusflow-beat`.
2. **Sử dụng Redis 7 làm Message Broker & Result Backend:**
   - Database 1 (`redis://redis:6379/1`): Celery Task Queue.
   - Database 2 (`redis://redis:6379/2`): Celery Result Backend.
   - Database 0 (`redis://redis:6379/0`): Dành riêng cho Bộ đệm Đọc và Khóa nguyên tử Hạn ngạch AI (ADR-005).
3. **Chính sách Đồng bộ Nhịp tim & Quét Timeout:**
   - Study Workspace gửi Heartbeat định kỳ 60 giây qua `POST /api/v1/sessions/{id}/heartbeat`.
   - Backend cập nhật trực tiếp `actual_minutes = X` và `last_heartbeat_at = NOW()` vào bảng `study_sessions` trong PostgreSQL 16.
   - Celery Beat kích hoạt task `CheckAbandonedSessionsTask` định kỳ mỗi 5 phút quét các phiên có `status = 'IN_PROGRESS'` và `last_heartbeat_at < NOW() - INTERVAL '5 minutes'`.
   - Áp dụng quy tắc `OS-01`: Nếu $\text{actual\_minutes} \ge 0.5 \times \text{planned\_minutes}$ hoặc có $\ge 1$ task hoàn tất $\rightarrow$ chốt `PARTIAL_COMPLETED`; ngược lại chốt `CANCELLED`. Chốt `ended_at = last_heartbeat_at` chính xác tuyệt đối.

---

## 4. Lý do & Đánh đổi (Rationale & Trade-Offs)
* **Bảo vệ Tính Bền vững (Durability First):** Trong ứng dụng quản lý học tập, số phút thực học là tài sản nỗ lực của người dùng. Việc lưu trực tiếp vào CSDL quan hệ với tải $0.33$ writes/s là giải pháp tối ưu, loại bỏ hoàn toàn nguy cơ mất dữ liệu phiên học do Redis restart.
* **Tối ưu hóa Truy vấn bằng Partial Index:** Cơ sở dữ liệu sử dụng chỉ mục chuyên biệt `CREATE INDEX idx_study_sessions_in_progress ON study_sessions(last_heartbeat_at) WHERE status = 'IN_PROGRESS'`. Bảng chỉ mục này cực kỳ nhỏ gọn vì chỉ chứa các phiên đang mở, giúp Celery Worker quét timeout trong $< 5$ms.
* **Cô lập Rủi ro và Tách biệt Trách nhiệm:** Quá trình quét timeout định kỳ và tính toán báo cáo tuần được đẩy hoàn toàn sang tiến trình worker độc lập, bảo đảm Backend API chính luôn nhẹ nhàng.

---

## 5. Hệ quả (Consequences)
* **Tích cực:** Hệ thống vận hành ổn định, tự động hóa 100% các công việc dọn dẹp phiên rớt mạng, bảo toàn dữ liệu chuẩn ACID, có thể cắm Flower Dashboard để giám sát trực quan.
* **Chi phí Vận hành:** Trong môi trường Docker Compose cần thêm 2 container (`worker` và `beat`). Đổi lại, tài nguyên tiêu thụ của mỗi container Celery là rất nhỏ (~50MB RAM).
* **Đồng bộ Kiến trúc:** Hoàn toàn nhất quán 100% với `schema.sql`, `system-architecture.md`, và `sequence-diagrams.md`.

---

## 6. Yêu cầu & Tài liệu liên quan
- **Yêu cầu SRS:** `FR-SESSION-003`, `FR-ADAPT-001`, `FR-REPORT-001`, `OS-01`, `OS-07`, `BUSR-09`.
- **ADR liên quan:** `ADR-001` (Kiến trúc Lục giác), `ADR-002` (FastAPI Backend), `ADR-007` (Database Persistence).
