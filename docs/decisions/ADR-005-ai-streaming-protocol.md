# ADR-005: Lựa chọn Giao thức Tương tác AI: Server-Sent Events (SSE) với Pydantic Streaming Parser

* **Trạng thái:** Được chấp thuận (Approved)
* **Ngày quyết định:** 29/09/2026
* **Người quyết định:** Vũ Toàn Thắng (Lead BA / System Architect), Phan Đình Duẩn (Senior BA / Quality Lead)
* **Căn cứ đánh giá:** Khung Rubric Đồ án Tốt nghiệp CNTT — Tiêu chí TC2.1 & TC2.3 (Mức 5)
* **Yêu cầu liên quan:** FR-PLAN-001, FR-PLAN-002, FR-PLAN-003, NFR-PERF-001

---

## 1. Ngữ cảnh & Đặt vấn đề (Context)
Quá trình phân rã mục tiêu tự học bằng mô hình ngôn ngữ lớn (Google Gemini 1.5) đòi hỏi AI phải thực hiện suy luận qua nhiều bước:
1. Giai đoạn 1: Làm rõ mục tiêu và ngữ cảnh kiến thức nền (Clarifying Goal).
2. Giai đoạn 2: Phân tích kiến trúc môn học và sinh các mốc kiến thức Cấp 1 (Milestones).
3. Giai đoạn 3: Phân bổ các đầu việc Cấp 2 chi tiết (Tasks) khớp với quỹ thời gian rảnh.

Tổng thời gian xử lý toàn bộ quy trình này có thể kéo dài từ **15 đến 35 giây**. 
Nếu sử dụng giao thức HTTP Request/Response truyền thống (đồng bộ), người dùng phải nhìn màn hình quay vô tận trong hơn nửa phút, dễ gây tâm lý hoang mang, nghi ngờ hệ thống bị treo hoặc gặp lỗi mạng, vi phạm tiêu chuẩn trải nghiệm người dùng (`BG-04`, `EVAL-05`).

---

## 2. Các phương án xem xét (Alternatives)

### Phương án A: HTTP REST API Đồng bộ (Standard JSON POST / Response)
* Client gửi POST request, chờ 30s và nhận về trọn vẹn khối JSON Proposal.
* *Ưu điểm:* Hiện thực đơn giản nhất.
* *Nhược điểm:* Trải nghiệm rất kém; trình duyệt hoặc reverse proxy có thể tự ngắt kết nối do gateway timeout nếu mạng chậm; người dùng không biết AI đang làm gì.

### Phương án B: WebSocket Hai chiều (Bidirectional WebSockets)
* Mở một kết nối TCP socket hai chiều liên tục giữa Browser và Backend.
* *Ưu điểm:* Giao tiếp hai chiều tốc độ cao.
* *Nhược điểm:* Phức tạp không cần thiết; WebSocket khó quản trị qua HTTP load balancer và serverless; không tận dụng được cơ chế HTTP header authorization thông thường; quy trình sinh lộ trình thực chất chỉ là luồng 1 chiều (Server gửi tiến trình cho Client).

### Phương án C: Server-Sent Events (SSE) kết hợp Pydantic Streaming Parser (Được chọn)
* Client gửi HTTP POST/GET, Backend thiết lập kênh `text/event-stream` truyền tải liên tục các sự kiện tiến trình (Progress Steps) và trả về từng phần cấu trúc dữ liệu.
* *Ưu điểm:*
  * **Chuẩn HTTP Thuần túy:** Hoạt động trơn tru qua mọi tường lửa, proxy và mạng di động mà không cần nâng cấp giao thức phức tạp.
  * **Trải nghiệm Thời gian thực Minh bạch:** Client nhận các sự kiện: `event: step_clarifying` -> `event: milestones_ready` -> `event: proposal_complete`.
  * **Tự động Kết nối lại (Reconnection):** Trình duyệt tích hợp sẵn cơ chế auto-reconnect của SSE.

---

## 3. Quyết định (Decision)
**Chấp thuận Phương án C: Sử dụng Server-Sent Events (SSE) kết hợp Pydantic Streaming Parser cho toàn bộ luồng tương tác AI sinh lộ trình.**

---

## 4. Lý do & Đánh đổi (Rationale & Trade-Offs)
* **Chứng minh Trình độ Kỹ thuật (Rubric TC2.3 Mức 5):** Thể hiện năng lực kiểm soát hoàn toàn vòng đời tương tác với LLM, phân rã quy trình thành các bước trạng thái rõ ràng thay vì xem AI như một "hộp đen" chậm chạp.
* **Ngăn chặn Timeout:** Kênh SSE liên tục gửi gói tin keep-alive / progress update, triệt tiêu hoàn toàn nguy cơ rớt kết nối mạng ở giây thứ 55 (`NFR-PERF-001`).

---

## 5. Hệ quả (Consequences)
* **Tích cực:** Giao diện Next.js hiển thị thanh tiến trình trực quan (Step Wizard 3 giai đoạn), người dùng nhìn thấy các Milestone xuất hiện tuần tự, tạo cảm giác hệ thống cực kỳ nhanh và thông minh.
* **Kỹ thuật:** Phía FastAPI sử dụng `StreamingResponse(event_generator(), media_type="text/event-stream")`. Phía Next.js sử dụng API `EventSource` hoặc thư viện `fetch-event-source` để gửi kèm Access Token an toàn.
