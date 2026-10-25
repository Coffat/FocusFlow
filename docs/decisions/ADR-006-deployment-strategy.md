# ADR-006: Chiến lược Triển khai 6-Container Docker Compose, Chế độ Bảo vệ Offline (Offline Defense Mode) & Cloud PaaS UAT

* **Trạng thái:** Được chấp thuận (Approved — Cập nhật Kiến trúc v2.0)
* **Ngày quyết định:** 29/09/2026 (Cập nhật v2.0: 25/10/2026)
* **Người quyết định:** Vũ Toàn Thắng, Phan Đình Duẩn
* **Căn cứ đánh giá:** Khung Rubric Đồ án Tốt nghiệp CNTT — Tiêu chí TC2.1, TC2.3 & TC2.7 (Mức 5)
* **Yêu cầu liên quan:** `ASR-05`, `ASR-06`, `NFR-AVAIL-001`, `NFR-SEC-001`, `EVAL-04`, `EVAL-05`, Ràng buộc Kiến trúc `CON-04`

---

## 1. Ngữ cảnh & Đặt vấn đề (Context)
Đồ án tốt nghiệp đại học chuyên ngành Kỹ thuật Phần mềm của FocusFlow phải thỏa mãn đồng thời 2 kịch bản vận hành đối lập nhau:
1. **Kịch bản Bảo vệ Khóa luận trước Hội đồng (Offline / Local Defense Mode - `ASR-06`):**
   * Phòng bảo vệ khóa luận thường có kết nối Wi-Fi chập chờn hoặc bị chặn tường lửa ra các dịch vụ đám mây ngoại vi (LLM API, cổng thanh toán PayOS/VNPay, Google Calendar API).
   * Hệ thống bắt buộc phải khởi chạy độc lập 100% trên máy tính cá nhân của sinh viên bằng một lệnh duy nhất (`docker compose up --build`), đồng thời cho phép trình diễn trọn vẹn mọi luồng nghiệp vụ (tạo lộ trình AI, thanh toán nâng cấp gói Premium, đồng bộ lịch) ngay cả khi **ngắt hoàn toàn kết nối Internet** mà không cần sửa đổi mã nguồn.
2. **Kịch bản Đánh giá Thử nghiệm Người dùng Thật trên Đám mây (Cloud UAT Protocol - `TC2.7`):**
   * Hệ thống cần được triển khai công khai trên Internet với tên miền hợp nhất (`.focusflow.vn`) để $U = 10 \sim 15$ sinh viên dùng thử thực tế trong 7–14 ngày, thu thập số liệu chứng minh các chỉ số KPI (`TSR >= 90%`, `SUS >= 80`) và đảm bảo không bị trùng lặp các tác vụ lập lịch định kỳ.

---

## 2. Các phương án xem xét (Alternatives Considered)

### Phương án A: Chỉ chạy Trực tiếp trên Máy chủ Vật lý / Localhost Không Đóng gói Container
* *Ưu điểm:* Không cần cài đặt Docker.
* *Nhược điểm:* Xung đột phiên bản Python 3.12, Node.js, PostgreSQL 16 và Redis 7 giữa các máy phát triển; khó tái lập môi trường đồng nhất khi demo trước Hội đồng.

### Phương án B: Hạ tầng Kubernetes (K8s / Helm) Đa Cụm trên AWS/GCP
* *Ưu điểm:* Khả năng mở rộng quy mô doanh nghiệp lớn.
* *Nhược điểm:* Quá tải vận hành (Over-engineering) cho đồ án tốt nghiệp 2 sinh viên; chi phí hạ tầng cao và không giải quyết được bài toán rớt mạng Wi-Fi tại phòng bảo vệ nếu vẫn phụ thuộc cứng vào API bên ngoài.

### Phương án C: Kiến trúc 6-Container Docker Compose Chuẩn hóa + Chế độ Bảo vệ Offline qua Hexagonal Adapters + Cloud PaaS UAT (Được chọn)
* Chuẩn hóa cấu trúc **Docker Compose 6 containers** đồng nhất giữa môi trường phát triển và nghiệm thu: `postgres`, `redis`, `backend`, `worker`, `scheduler` (`replicas: 1`), và `frontend`.
* Trang bị **Chế độ Bảo vệ Offline (Offline / Local Defense Mode)** thông qua việc hoán đổi các Hexagonal Output Adapters (`MockLLMAdapter`, `LocalMockPaymentAdapter`, `LocalCalendarAdapter`) chỉ bằng cấu hình biến môi trường `.env`.
* Kết hợp triển khai Cloud PaaS trên tên miền `.focusflow.vn` cho giai đoạn thử nghiệm UAT thực tế.

---

## 3. Quyết định (Decision)
**Chấp thuận Phương án C với 3 trụ cột triển khai và vận hành chi tiết:**

### 3.1. Topology 6-Container Docker Compose Chuẩn hóa
Toàn bộ hệ thống FocusFlow v2.0 được đóng gói gọn nhẹ, tường minh trong 6 containers giao tiếp qua mạng nội bộ `focusflow_net`:

| STT | Tên Dịch vụ (`docker-compose.yml`) | Công nghệ & Image Nền tảng | Trách nhiệm & Cấu hình Trọng yếu |
| :---: | :--- | :--- | :--- |
| **1** | **`postgres`** | `postgres:16-alpine` | Cơ sở dữ liệu quan hệ chính chứa **24 bảng 3NF/BCNF**, gắn volume bền vững `pg_data` và `healthcheck` (`pg_isready`). |
| **2** | **`redis`** | `redis:7-alpine` | Message Broker cho **Redis Streams (`Taskiq`)**, lưu trữ xoay vòng Refresh Token, Rate Limit và SSE Pub/Sub. Bắt buộc khởi chạy với **`--appendonly yes` (AOF Enabled)** để bảo toàn dữ liệu hàng đợi khi container khởi động lại. |
| **3** | **`backend`** | Python 3.12-slim (`FastAPI` + `Uvicorn`) | Phục vụ REST API, luồng 2-Stage SSE, Webhook và thực thi Alembic migrations khi khởi động. |
| **4** | **`worker`** | Python 3.12-slim (`taskiq worker`) | Thực thi bất đồng bộ các tác vụ từ Redis Streams (`XREADGROUP`/`XACK`): Outbox Relay, AI Aggregation, Calendar Sync, Sweeper tasks. Có thể mở rộng `replicas: N`. |
| **5** | **`scheduler`** | Python 3.12-slim (`taskiq scheduler`) | Kích hoạt các tác vụ định kỳ theo lịch (60s Session/Quota/Outbox Sweep, Overdue Anti-Loop). **Bắt buộc cố định `deploy.replicas: 1`** để ngăn chặn tuyệt đối việc phát trùng lịch cron. |
| **6** | **`frontend`** | Multi-stage build: Node 22 $\to$ `nginx:alpine` | Phục vụ ứng dụng **Angular 21+ Zoneless SPA** tĩnh siêu nhẹ (< 25MB), cấu hình reverse proxy `/api` về `backend` và tắt đệm (`proxy_buffering off`) cho các luồng SSE. |

### 3.2. Chế độ Bảo vệ Khóa luận Offline / Local (Offline Defense Mode — `ASR-06`)
Nhờ kiến trúc Hexagonal (`ADR-001`, `ADR-005`), mọi dịch vụ bên ngoài đều đứng sau các Output Ports. Khi bảo vệ khóa luận tại phòng thi không có Internet (hoặc khi chạy kiểm thử E2E Playwright tự động), nhóm chỉ cần chuyển cấu hình trong `.env` sang chế độ Local/Offline mà **không cần sửa bất kỳ dòng code nào**:
1. **`LLM_PROVIDER=mock` (hoặc `ollama`):** Composition Root tự động tiêm **`MockLLMAdapter`** (mô phỏng luồng stream SSE từng chunk với độ trễ chân thực 1–2s và trả về JSON chuẩn Pydantic v2) hoặc kết nối tới mô hình Local Ollama chạy ngay trên máy cá nhân.
2. **`PAYMENT_PROVIDER=local_mock`:** Tự động tiêm **`LocalMockPaymentAdapter`** sinh mã QR nội bộ và cung cấp nút giả lập callback thanh toán thành công (ký đúng chữ ký `HMAC-SHA256`) để demo luồng nâng cấp gói Premium (`UC-05`) ngay tại chỗ.
3. **`CALENDAR_PROVIDER=local_mock`:** Tự động tiêm **`LocalCalendarAdapter`** mô phỏng phản hồi OAuth2 Free/Busy và kết hợp luồng xuất file `.ics` cục bộ (`UC-13`).

### 3.3. Triển khai Cloud PaaS cho Đánh giá Thực nghiệm UAT (`TC2.7`)
Trong giai đoạn thử nghiệm người dùng thật (7–14 ngày):
* Sử dụng chung Root Domain `.focusflow.vn` (`app.focusflow.vn` cho Angular SPA và `api.focusflow.vn` cho FastAPI Backend) để Cookie JWT (`HttpOnly`, `Secure`, `SameSite=Lax`) hoạt động liền mạch.
* Duy trì đúng 1 tiến trình `taskiq scheduler` (`replicas: 1`) cùng tiến trình `taskiq worker` và Managed PostgreSQL 16 + Redis 7 (bật AOF).

---

## 4. Lý do & Đánh đổi (Rationale & Trade-Offs)
* **An toàn Tuyệt đối Ngày Bảo vệ (`ASR-06`):** Chế độ Offline Defense Mode loại bỏ 100% rủi ro rớt mạng phòng thi, hết hạn API key hay cổng thanh toán sandbox bảo trì ngay lúc Hội đồng đang chấm điểm.
* **Không Trùng lặp Tác vụ Định kỳ (`ASR-02`, `ASR-05`):** Tách riêng container `scheduler` (`replicas: 1`) khỏi `worker` giúp hệ thống vừa có thể scale worker xử lý tải, vừa đảm bảo các lệnh cron quét mỗi 60s chỉ được phát đi đúng 1 lần.
* **Chi phí Vận hành Thấp:** Toàn bộ 6 containers trên Docker Compose tiêu thụ dưới 800MB RAM trên máy cá nhân của sinh viên.

---

## 5. Hệ quả & Kiểm chứng (Consequences & Verification)
* **Tích cực:** Đáp ứng hoàn hảo cả tiêu chí đóng gói hạ tầng hiện đại (Rubric TC2.1) lẫn khả năng vận hành thực nghiệm UAT và bảo vệ tại chỗ (Rubric TC2.7).
* **Kiểm chứng Tự động:** Kịch bản kiểm thử khói (Smoke Test) khởi chạy `docker compose up -d` với cấu hình Offline Mode và chạy bộ Playwright E2E test khi ngắt mạng ngoại vi phải vượt qua 100%.
