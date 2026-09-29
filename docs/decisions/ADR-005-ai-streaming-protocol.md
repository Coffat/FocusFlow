# ADR-005: Lựa chọn Giao thức Tương tác AI: Quy trình 2 Bước RESTful kết hợp Server-Sent Events (SSE) & Đường ống LLM 3 Chặng

* **Trạng thái:** Được chấp thuận (Approved)
* **Ngày quyết định:** 29/09/2026
* **Người quyết định:** Vũ Toàn Thắng (Lead BA / System Architect), Phan Đình Duẩn (Senior BA / Quality Lead)
* **Căn cứ đánh giá:** Khung Rubric Đồ án Tốt nghiệp CNTT — Tiêu chí TC2.1 & TC2.3 (Mức 5)
* **Yêu cầu liên quan:** FR-PLAN-001, FR-PLAN-002, FR-PLAN-003, NFR-PERF-001, BUSR-10

---

## 1. Ngữ cảnh & Đặt vấn đề (Context)
Quá trình phân rã mục tiêu tự học bằng mô hình ngôn ngữ lớn (Google Gemini API, mô hình cấu hình linh hoạt qua biến môi trường `GEMINI_MODEL`, mặc định `gemini-1.5-flash`) đòi hỏi AI thực hiện suy luận qua 3 chặng tuần tự:
1. Chặng 1: Làm rõ mục tiêu và ngữ cảnh kiến thức nền (Clarifying Goal Context).
2. Chặng 2: Phân tích cấu trúc môn học và sinh các mốc kiến thức Cấp 1 (Milestones).
3. Chặng 3: Phân bổ các đầu việc Cấp 2 chi tiết (Tasks) khớp với quỹ thời gian rảnh.

Tổng thời gian xử lý chuỗi tác vụ này kéo dài từ **15 đến 35 giây**. 
Nếu sử dụng giao thức HTTP POST đồng bộ hoặc POST streaming đơn lẻ:
* Dễ gặp rủi ro rớt kết nối mạng ở giây thứ 55 (`NFR-PERF-001`).
* Khi rớt mạng và kết nối lại, nếu client tự động gửi lại lệnh POST sẽ tạo thành một job mới và trừ thêm hạn ngạch AI của người dùng (vi phạm cam kết Quota trong SRS v1.0).

---

## 2. Các phương án xem xét (Alternatives)

### Phương án A: HTTP REST API Đồng bộ (Standard JSON POST / Response)
* Client gửi POST request, chờ 30s và nhận về trọn vẹn khối JSON Proposal.
* *Ưu điểm:* Hiện thực đơn giản nhất.
* *Nhược điểm:* Trải nghiệm rất kém; người dùng phải chờ lâu trong vô định; dễ bị gateway timeout.

### Phương án B: WebSocket Hai chiều (Bidirectional WebSockets)
* Mở một kết nối TCP socket hai chiều liên tục giữa Browser và Backend.
* *Ưu điểm:* Giao tiếp hai chiều tốc độ cao.
* *Nhược điểm:* Phức tạp không cần thiết; WebSocket khó quản trị qua HTTP load balancer và serverless; luồng sinh lộ trình thực chất chỉ là luồng 1 chiều (Server gửi tiến trình cho Client).

### Phương án C: Quy trình 2 Bước Chuẩn RESTful: POST Tạo Job -> GET SSE Native (Được chọn)
* **Bước 1 — Khởi tạo Job (POST):** Client gửi `POST /api/v1/roadmaps/proposals` kèm `Idempotency-Key`. Backend tạm giữ quota (`reserve_quota`), tạo bản ghi `schedule_proposals` với trạng thái `PROCESSING`, và trả về `proposal_id`.
* **Bước 2 — Stream Tiến trình (GET SSE):** Client mở kết nối native `GET /api/v1/roadmaps/proposals/{id}/stream` qua `EventSource` (với `withCredentials: true`). Trình duyệt tự động gửi cookie HttpOnly qua tên miền chung `.focusflow.vn`.
* **Bản chất Đường ống LLM (3-Stage LLM Pipeline):** Thay vì parse JSON dở dang, hệ thống gọi tuần tự 3 lệnh LLM; sau mỗi chặng, kết quả được thẩm định toàn vẹn bằng **Pydantic Schema** (`GoalClarificationSchema` -> `MilestoneListSchema` -> `ProposalPlanSchema`) trước khi phát sự kiện SSE tương ứng đến Client.

---

## 3. Quyết định (Decision)
**Chấp thuận Phương án C: Quy trình 2 bước RESTful (POST tạo job & tạm giữ Quota -> GET SSE stream tiến trình) kết hợp Đường ống LLM 3 chặng thẩm định bởi Pydantic Schema.**

---

## 4. Lý do & Đánh đổi (Rationale & Trade-Offs)
* **Tính Bất biến & Chống trừ Quota 2 lần (Idempotency):** Vì bước stream sử dụng phương thức `GET`, nếu kết nối mạng bị gián đoạn, trình duyệt có thể tự động reconnect với header `Last-Event-ID` mà hoàn toàn không kích hoạt lại lệnh gọi AI mới và không bị trừ thêm quota.
* **Chứng minh Trình độ Kỹ thuật (Rubric TC2.3 Mức 5):** Thể hiện rõ năng lực kiểm soát từng bước trạng thái của LLM, có cổng kiểm tra schema ở từng nấc, và áp dụng cơ chế Quota Hai pha (Reserve -> Commit khi thành công, Refund khi lỗi).

---

## 5. Hệ quả (Consequences)
* **Tích cực:** Giao diện Next.js hiển thị thanh tiến trình 3 chặng mượt mà, người dùng nắm rõ AI đang làm gì. Cookie HttpOnly được gửi tự nhiên qua kết nối GET native.
* **Kỹ thuật:** Phía FastAPI sử dụng `StreamingResponse` cho endpoint GET stream. Phía Next.js sử dụng `EventSource` native của trình duyệt.
