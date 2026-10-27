# ADR-004: Lựa chọn Giải pháp Hàng đợi Tác vụ Nền & Lịch Định kỳ Thuần Async: Taskiq, Redis Streams & TaskiqScheduler

* **Trạng thái:** Được chấp thuận (Approved — Cập nhật Kiến trúc v2.0, thay thế thiết kế Celery cũ)
* **Ngày quyết định:** 29/09/2026 (Cập nhật v2.0: 25/10/2026)
* **Người quyết định:** Vũ Toàn Thắng, Phan Đình Duẩn
* **Căn cứ đánh giá:** Khung Rubric Đồ án Tốt nghiệp CNTT — Tiêu chí TC2.1 & TC2.3 (Mức 5)
* **Yêu cầu liên quan:** `ASR-01`, `ASR-02`, `ASR-05`, `FR-SESSION-003`, `FR-ADAPT-001`, `FR-ADAPT-003`, `FR-REPORT-001`, `OS-01`, `OS-07`, `BUSR-06`, `BUSR-09`, `NFR-PERF-002`, `NFR-AVAIL-001`

---

## 1. Ngữ cảnh & Đặt vấn đề (Context)
Hệ thống FocusFlow v2.0 sở hữu nhiều luồng xử lý nền và công việc định kỳ quan trọng không được phép làm nghẽn chu kỳ HTTP Request-Response:
1. **Chuyển tiếp Sự kiện Liên Bounded Context (Transactional Outbox Relay - `ASR-02`):** Đọc các sự kiện miền từ bảng `outbox_events` và phát tới các trình xử lý bất đồng bộ của Context đích mà không được phép làm mất sự kiện.
2. **Ghi nhận Heartbeat 60s & Quét Phiên học Treo sau 5 phút (`ASR-05`, `OS-01`, `OS-07`):** Tự động thu hồi các phiên học `IN_PROGRESS` mất kết nối quá 5 phút, bảo toàn tiến độ của người học với độ lệch $\le 60\text{s}$.
3. **Thu hồi Giữ chỗ Hạn ngạch AI Hết hạn (`Quota Sweeper` - `ASR-02`):** Quét bảng `ai_quota_reservations` để giải phóng các lượt `RESERVED` bị quá hạn `expires_at` do sự cố mạng hoặc đứt kết nối SSE.
4. **Quét Nhiệm vụ Quá hạn, Thông báo Email & Ngắt mạch Chống lặp (`Overdue Scanner / Overdue Anti-Loop Sweeper` - `FR-ADAPT-001`, `FR-ADAPT-003`):** Chạy định kỳ lúc `00:05 UTC+7` để phát hiện các nhiệm vụ quá hạn (`scheduled_date < CURRENT_DATE` và `status != 'COMPLETED'`), gửi thông báo Email tới người học (không tự ý sửa ngầm `scheduled_date`), hiển thị cảnh báo trong mục `Needs Attention` trên Web kèm nút **"AI Reschedule (Dời lịch hợp lý)"** cho riêng lộ trình đó và kích hoạt trạng thái `STALLED` khi `reschedule_count >= 3`.
5. **Tổng hợp Hồ sơ Năng lực Người học (`Learner Profile Aggregator` - `FR-PROFILE-001`):** Cập nhật các chỉ số SRL ($D_{opt}$, $\beta_{bias}$, khung giờ đỉnh) sau khi hoàn thành phiên học.
6. **Đồng bộ Lịch Ngoại vi 2 Chiều (`Calendar Sync` - `UC-13`):** Đồng bộ các khoảng bận (Free/Busy) và sự kiện với Google Calendar OAuth2.

### Lý do Loại bỏ Celery + Celery Beat (từ bản v1.0)
Trong bản thiết kế v1.0, nhóm từng lựa chọn **Celery 5.6 + Celery Beat**. Tuy nhiên, quá trình rà soát kiến trúc sâu cho thấy Celery có **độ lệch pha nghiêm trọng (Impedance Mismatch)** với ngăn xếp bất đồng bộ `FastAPI + SQLAlchemy 2.0 Async (asyncpg)` của FocusFlow (`ADR-002`):
* Celery được thiết kế trên nền tảng **đồng bộ (Synchronous/Threaded/Prefork)**. Để gọi các Use Case `async def` và `AsyncUnitOfWork` (`asyncpg`) bên trong Celery task, lập trình viên buộc phải bọc qua `asyncio.run(...)` hoặc tự quản lý vòng lặp sự kiện mỗi lần chạy task, đồng thời phải cấu hình `NullPool` cho SQLAlchemy để tránh lỗi *`Task attached to a different loop`*.
* Celery không thể chia sẻ trực tiếp hệ thống Dependency Injection bất đồng bộ của FastAPI, dẫn đến mã nguồn khởi tạo Use Case bị nhân bản ở hai nơi.

---

## 2. Các phương án xem xét (Alternatives Considered)

### Phương án A: FastAPI `BackgroundTasks` Nội bộ
* *Ưu điểm:* Có sẵn trong FastAPI, không cần tiến trình riêng.
* *Nhược điểm:* Chạy chung tiến trình với API server; nếu container `backend` khởi động lại, toàn bộ tác vụ đang chạy bị mất trắng; không có cơ chế lưu trữ bền vững, không có ACK hay bộ lập lịch định kỳ độc lập.

### Phương án B: Celery 5.6 + Celery Beat (Đã bác bỏ ở v2.0)
* *Ưu điểm:* Phổ biến trong các ứng dụng Python đồng bộ truyền thống (Django/Flask).
* *Nhược điểm:* Bất tương thích gốc với `asyncio` và `SQLAlchemy AsyncSession`; tốn bộ nhớ; không chia sẻ được DI với FastAPI; gây lỗi vòng lặp sự kiện khi tái sử dụng connection pool của `asyncpg`.

### Phương án C: Taskiq + Redis Streams (`RedisStreamBroker`, `TaskiqScheduler`, `taskiq-fastapi`, `taskiq-redis`) (Được chọn)
* Sử dụng **Taskiq** — bộ khung hàng đợi tác vụ phân tán **thuần `async/await` (Async-Native)** hiện đại nhất cho Python 3.12+.
* Sử dụng **Redis Streams (`RedisStreamBroker` từ `taskiq-redis`)** với cơ chế Consumer Group (`XREADGROUP`) và xác nhận hoàn tất tường minh (`XACK`).
* Tích hợp **`taskiq-fastapi`** để dùng chung 100% hệ thống Dependency Injection (`TaskiqDepends`) và `AsyncSession` pool với FastAPI.
* Sử dụng **`TaskiqScheduler`** chạy trong container độc lập (`replicas: 1`) cho toàn bộ các tác vụ định kỳ (Cron/Interval).

---

## 3. Quyết định (Decision)
**Chấp thuận Phương án C: Chuẩn hóa toàn bộ hệ thống tác vụ nền và lập lịch định kỳ sang Taskiq + Redis Streams (`taskiq`, `taskiq-fastapi`, `taskiq-redis`) với 5 Quy tắc Vận hành Production và 6 Nhóm Tác vụ Cốt lõi:**

### 3.1. Tại sao Taskiq + Redis Streams Vượt trội
1. **Thuần `async def` 100%:** Mọi task là hàm `async def` chạy trên cùng một `asyncio` event loop liên tục của worker, sử dụng trực tiếp connection pool của `SQLAlchemy 2.0 AsyncEngine` (`asyncpg`) mà không cần `asyncio.run()` hay `NullPool`.
2. **Chia sẻ Dependency Injection với FastAPI (`taskiq-fastapi`):** Cho phép tiêm `AsyncUnitOfWork` và các Use Cases vào task thông qua `TaskiqDepends` ngay tại Composition Root (`presentation/deps.py`).
3. **Độ tin cậy Chuẩn Công nghiệp với Redis Streams (`XREADGROUP` / `XACK`):** Khác với Redis Pub/Sub hay List (`LPUSH`/`BRPOP`) dễ mất message khi worker chết giữa chừng, `RedisStreamBroker` giữ message trong Pending Entries List (PEL) cho đến khi worker xử lý xong và gửi lệnh `XACK`.
4. **Dễ dàng Hoán đổi Broker:** Tuân thủ triệt để kiến trúc Hexagonal, cấu hình broker nằm gọn trong `shared_kernel/infrastructure/worker/`.

### 3.2. Năm Quy tắc Vận hành Bắt buộc (5 Production Rules)
1. **Quy tắc 1 — `scheduler` bắt buộc chạy Đơn bản (`replicas: 1`):** Container `scheduler` (`taskiq scheduler`) chỉ có nhiệm vụ phát lệnh kích hoạt theo lịch vào Redis Stream nên **bắt buộc cấu hình `replicas: 1`** để không bao giờ phát trùng sự kiện cron. Ngược lại, container `worker` (`taskiq worker`) có thể mở rộng nhiều bản sao (`replicas: N`) tùy theo tải.
2. **Quy tắc 2 — Tác vụ Bắt buộc có Tính Lũy đẳng (Idempotent Tasks):** Mọi task xử lý sự kiện liên Context phải kiểm tra `event_id` trong bảng `processed_events` trước khi thực thi; mọi task quét định kỳ (Sweeper) phải sử dụng khóa hàng **`SELECT ... FOR UPDATE SKIP LOCKED`** trong PostgreSQL để chống race condition tuyệt đối.
3. **Quy tắc 3 — Chỉ truyền Định danh Nguyên thủy (Pass Primitive UUIDv7 IDs Only):** Payload đẩy vào Redis Streams chỉ chứa các kiểu nguyên thủy nhẹ (chuỗi `UUIDv7` ID, mốc thời gian ISO), tuyệt đối không serialize đối tượng ORM hay dữ liệu lớn vào message broker; worker sẽ tự truy vấn trạng thái mới nhất từ PostgreSQL thông qua `AsyncUnitOfWork`.
4. **Quy tắc 4 — Kiểm soát Timeout, Exponential Backoff & Redis AOF:** Mọi task gọi dịch vụ ngoài (LLM, Google Calendar) phải gắn giới hạn thời gian chạy (timeout) và chính sách thử lại lũy thừa (Exponential Backoff + Jitter) qua `SimpleRetryMiddleware`; dịch vụ Redis 7 bắt buộc bật chế độ lưu trữ bền vững **`--appendonly yes` (AOF)**.
5. **Quy tắc 5 — Tách tải Tác vụ Nặng CPU (Offload Heavy CPU Work):** Vì Taskiq worker chạy trên `asyncio` event loop, bất kỳ bước tính toán đồng bộ nặng CPU nào (nếu có) phải được đẩy sang `asyncio.to_thread()` để không làm nghẽn vòng lặp sự kiện của các task I/O khác.

### 3.3. Danh mục 6 Nhóm Tác vụ Nền & Định kỳ Cốt lõi
1. **Outbox Relay Task (`shared_kernel`):** Quét bảng `outbox_events` (`status = 'PENDING'`) với `SELECT ... FOR UPDATE SKIP LOCKED`, phát sự kiện sang các Taskiq handlers của Context đích và đánh dấu `PUBLISHED`.
2. **60s Heartbeat & 5-Minute Abandoned Session Sweeper (`execution` - `ASR-05`, `OS-01`, `OS-07`):**
   * Client gửi Heartbeat mỗi 60s qua `POST /api/v1/sessions/{id}/heartbeat` ghi trực tiếp `actual_minutes` và `last_heartbeat_at = NOW()` xuống bảng `study_sessions` (PostgreSQL).
   * `TaskiqScheduler` kích hoạt `AbandonedSessionSweeperTask` mỗi 60 giây để quét các phiên `status = 'IN_PROGRESS'` có `last_heartbeat_at < NOW() - INTERVAL '5 minutes'` (tận dụng Partial Index `idx_study_sessions_in_progress` và `FOR UPDATE SKIP LOCKED`). Áp dụng quy tắc `OS-01` để chốt `PARTIAL_COMPLETED` hoặc `CANCELLED` và phát sự kiện ra Outbox.
3. **AI Quota Reservation Sweeper (`account` - `ASR-02`):** Định kỳ mỗi 60 giây quét bảng `ai_quota_reservations` có `status = 'RESERVED'` và `expires_at < NOW()` (quá hạn TTL **120 giây / 2 phút**), tự động hoàn trả số lượt giữ chỗ (`reserved_calls`) về bảng `ai_quotas` và chuyển trạng thái sang `'EXPIRED'`.
4. **Overdue Scanner & Anti-Loop Sweeper (`evaluation` - `00:05 UTC+7`, `FR-ADAPT-001`, `FR-ADAPT-003`):** Quét các nhiệm vụ quá hạn (`scheduled_date < CURRENT_DATE` và `status != 'COMPLETED'`) định kỳ lúc `00:05 UTC+7`. Tác vụ **tuyệt đối KHÔNG tự động thay đổi ngầm `scheduled_date` (does NOT silently mutate `scheduled_date`)**; thay vào đó, hệ thống gửi **Email Notification** tới địa chỉ email đăng ký của người dùng (qua `EmailNotificationPort` / SMTP Adapter) và đưa các task quá hạn vào khu vực **`Needs Attention`** kèm nút **"AI Reschedule (Dời lịch hợp lý)"** khi người học đăng nhập ứng dụng Web. Khi người học bấm **"AI Reschedule"** trên một lộ trình quá hạn, AI quét các task chưa hoàn thành của **riêng Lộ trình đó** cùng lịch học tương lai của người dùng (trừ đi các khung giờ đã bị chiếm dụng bởi các lộ trình khác hoặc lịch ngoại vi) để sắp xếp lại **chỉ các task của Lộ trình đó** (không bao giờ chạm vào các lộ trình/công việc khác), **bỏ qua Cổng Kiểm duyệt 3 Tầng (bypassing the 3-Tier Hybrid Validation Gate — bỏ qua Tier 3 Pedagogical Judge**, chỉ kiểm tra định dạng JSON Schema & ràng buộc dung lượng/tránh xung đột cơ bản cho lộ trình đó), và tăng `reschedule_count` thêm 1 (nếu chạm ngưỡng `reschedule_count >= 3` thì kích hoạt cơ chế leo thang chống lặp `STALLED`).
5. **Learner Profile Aggregator (`account` - `FR-PROFILE-001`):** Lắng nghe sự kiện `StudySessionCompletedEvent` từ Outbox / chạy tổng hợp định kỳ để tính toán lại các tham số năng lực SRL ($D_{opt}$, $\beta_{bias}$, khung giờ tập trung đỉnh) lưu vào bảng `learner_profiles`.
6. **External Calendar Sync Task (`execution` - `UC-13`):** Thực thi đồng bộ bất đồng bộ 2 chiều có kiểm soát với Google Calendar OAuth2 API (đọc khung giờ bận Free/Busy và đẩy lịch học mới khi `OfficialScheduleAppliedEvent` được phát ra).

---

## 4. Lý do & Đánh đổi (Rationale & Trade-Offs)
* **Đồng nhất Kiến trúc 100% (`ASR-01`, `ASR-02`):** Loại bỏ hoàn toàn sự chắp vá giữa Sync (Celery) và Async (FastAPI/SQLAlchemy 2.0), giúp toàn bộ codebase dùng chung một mô hình lập trình `async/await` và `AsyncUnitOfWork`.
* **Bảo vệ Nỗ lực Người học (`ASR-05`):** Ghi nhận Heartbeat 60s trực tiếp xuống PostgreSQL kết hợp quét `FOR UPDATE SKIP LOCKED` qua Taskiq đảm bảo không mất quá 60s tiến độ học tập ngay cả khi mất mạng hoặc sập trình duyệt.
* **Đánh đổi:** Taskiq là thư viện hiện đại hơn Celery nên tài liệu tiếng Việt ít hơn; tuy nhiên API của Taskiq cực kỳ giống FastAPI nên rất trực quan đối với nhóm phát triển.

---

## 5. Hệ quả & Kiểm chứng (Consequences & Verification)
* **Tích cực:** Hệ thống xử lý tác vụ nền nhẹ nhàng, tiêu thụ ít RAM hơn Celery, hỗ trợ đầy đủ Transactional Outbox và Idempotent Consumer.
* **Kiểm chứng Tự động:** Các task của Taskiq được kiểm thử trực tiếp trong `pytest-asyncio` bằng `InMemoryBroker` mà không cần chạy tiến trình worker ngoài.
