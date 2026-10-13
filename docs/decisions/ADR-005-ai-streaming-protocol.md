# ADR-005: Lựa chọn Giao thức Tương tác AI: Quy trình SSE Hai Chặng Đồng nhất kết hợp Cổng Duyệt Con người 2 Cấp độ (Human-in-the-Loop)

* **Trạng thái:** Được chấp thuận (Approved — Đã chuẩn hóa theo SRS v1.1)
* **Ngày quyết định:** 29/09/2026 (Cập nhật chuẩn hóa: 30/09/2026)
* **Người quyết định:** Vũ Toàn Thắng (Lead BA / System Architect), Phan Đình Duẩn (Senior BA / Quality Lead)
* **Căn cứ đánh giá:** Khung Rubric Đồ án Tốt nghiệp CNTT — Tiêu chí TC2.1 & TC2.3 (Mức 5)
* **Yêu cầu liên quan:** FR-PLAN-001, FR-PLAN-002, FR-PLAN-003, FR-QUOTA-001, NFR-PERF-001, NFR-AI-001, BUSR-02, BUSR-10

---

## 1. Ngữ cảnh & Đặt vấn đề (Context)
Theo đặc tả nghiệp vụ SRS v1.1, quá trình phân rã mục tiêu tự học bằng mô hình ngôn ngữ lớn (Google Gemini API, cấu hình qua `GEMINI_MODEL`, mặc định `gemini-1.5-flash`) bắt buộc phải tuân thủ nguyên tắc **Cổng Kiểm duyệt Con người (Human-in-the-Loop Gate - BUSR-02)** qua 2 cấp độ độc lập:
1. **Cấp 1 — Cột mốc Tổng quan (Milestones - FR-PLAN-001):** AI sinh danh sách 3–7 cột mốc kiến thức; Learner có toàn quyền xem xét, chỉnh sửa tên/thứ tự, thêm/xóa milestone và bấm **"Duyệt Milestones (Approve Milestones)"**.
2. **Cấp 2 — Đề xuất Nhiệm vụ Chi tiết (Tasks & Schedule Proposal - FR-PLAN-002):** Dựa trên danh sách Milestones đã duyệt và quỹ thời gian rảnh (Availability), AI phân rã thành các tasks chi tiết (30–120 phút) và xếp vào khung giờ trống thành bản nháp `Schedule Proposal` (trạng thái `DRAFT`) trước khi Learner bấm **"Apply"** (`FR-PLAN-003`).

Đồng thời, hệ thống đòi hỏi:
* **Chống rớt mạng & Chống trừ Quota 2 lần:** Tổng thời gian suy luận có thể kéo dài 15–35s. Nếu client mất kết nối và tự động gửi lại lệnh POST, tuyệt đối không được tạo job trùng lặp hay trừ thêm hạn ngạch của người dùng (`BUSR-10`).
* **Trải nghiệm giao diện đồng nhất:** Người dùng cần theo dõi tiến trình trực quan theo thời gian thực thay vì chờ đợi màn hình trắng (blank screen).

---

## 2. Các phương án xem xét (Alternatives)

### Phương án A: Gộp Toàn bộ 1 Mạch trong 1 SSE Stream Duy nhất
* Client gửi 1 request, AI tự động chạy liên tục từ Mục tiêu -> Milestones -> Tasks trong 1 kết nối SSE duy nhất.
* *Ưu điểm:* 1 kết nối duy nhất, hoàn thành nhanh về mặt kỹ thuật.
* *Nhược điểm:* **Vi phạm nghiêm trọng nguyên tắc Human-in-the-Loop (`BUSR-02`) và `FR-PLAN-001` trong SRS v1.1**. Người học bị tước mất quyền kiểm soát cấu trúc vĩ mô (Milestones); nếu AI hiểu sai mục tiêu, toàn bộ 40 tasks sinh ra đều vô nghĩa, gây quá tải nhận thức (Cognitive Overload) khi phải sửa một danh sách task khổng lồ.

### Phương án B: Tách 2 Bước bằng HTTP REST API Đồng bộ (Standard JSON POST)
* Bước 1 gọi POST nhận Milestones; Bước 2 gọi POST nhận Tasks.
* *Ưu điểm:* Dễ cài đặt.
* *Nhược điểm:* Bước sinh Tasks chi tiết mất từ 15–30s rất dễ bị gateway timeout (ở giây thứ 55 `NFR-PERF-001`); không hiển thị được thanh phần trăm tiến trình thời gian thực.

### Phương án C: Quy trình SSE Hai Chặng Đồng nhất (Uniform 2-Stage SSE) kết hợp Cổng Duyệt 2 Cấp độ (Được chọn)
* Áp dụng thống nhất mô hình **2 bước chuẩn RESTful (POST khởi tạo job -> GET SSE stream tiến trình)** cho cả 2 cấp độ phân rã:
  * **Giai đoạn 1 — Phân rã & Duyệt Milestones (FR-PLAN-001):**
    1. Client gửi `POST /api/v1/roadmaps/milestones/generate` kèm `Idempotency-Key`. Hệ thống tạm giữ (Reserve) 1 AI Credit (`FR-QUOTA-001`) và trả về `job_id`.
    2. Client mở `GET /api/v1/roadmaps/milestones/jobs/{job_id}/stream` qua `EventSource` để nhận phản hồi stream tiến trình; LLM sinh và thẩm định cấu trúc qua `MilestoneListSchema` (Pydantic v2).
    3. Giao diện dừng lại hiển thị danh sách Milestones; Learner chỉnh sửa và bấm **"Duyệt Milestones"**.
  * **Giai đoạn 2 — Phân rã Tasks Chi tiết & Xếp Lịch (FR-PLAN-002):**
    1. Learner bấm "Tạo Đề xuất Lịch trình" -> Client gửi `POST /api/v1/roadmaps/proposals` truyền ID của Milestones đã duyệt.
    2. Client mở `GET /api/v1/roadmaps/proposals/{proposal_id}/stream` qua `EventSource`; Backend phân bổ thời gian rảnh, gọi LLM sinh tasks, thẩm định bằng `ProposalPlanSchema`.
    3. Hoàn tất thành công: Hệ thống chính thức trừ (Commit) 1 AI Credit vào CSDL, lưu bản nháp Proposal `DRAFT`, và gửi sự kiện `completed` kết thúc stream.
    4. Learner xem bảng lịch, tinh chỉnh và bấm "Apply" (`FR-PLAN-003`).

---

## 3. Quyết định (Decision)
**Chấp thuận Phương án C: Áp dụng Quy trình SSE Hai Chặng Đồng nhất (POST tạo job & Reserve Quota -> GET SSE stream) gắn liền với Cổng Phê duyệt Con người 2 cấp độ chuẩn mực theo SRS v1.1.**

---

## 4. Lý do & Đánh đổi (Rationale & Trade-Offs)
* **Khớp 100% với Mô hình Tâm lý Tự điều chỉnh Học tập (Zimmerman SRL & SRS v1.1):** Tách bạch rõ giữa giai đoạn hoạch định chiến lược vĩ mô (Milestones) và kế hoạch hành động vi mô (Tasks), giảm tải nhận thức cho sinh viên.
* **Chính sách Hạn ngạch Nhân văn & Bảo mật (Rubric TC2.3 Mức 5):** Gói trọn toàn bộ quy trình tạo lộ trình hoàn chỉnh (Cả Milestones lẫn Tasks) chỉ tính là **1 lượt gọi AI (1 AI Credit)**. Cơ chế Quota 2 Pha (Reserve tại Giai đoạn 1 -> Commit khi kết thúc Giai đoạn 2; tự động Refund nếu người dùng hủy hoặc gặp lỗi timeout 55s) bảo vệ quyền lợi tối đa cho người học.
* **Tính Bất biến Tuyệt đối (Idempotency):** Kênh truyền GET SSE native cho phép trình duyệt tự động kết nối lại (`Last-Event-ID`) khi mạng chập chờn mà không bao giờ kích hoạt gọi lại LLM hoặc trừ trùng quota.

---

## 5. Hệ quả (Consequences)
* **Tích cực:** Đáp ứng xuất sắc toàn bộ ca sử dụng `UC-PLAN-01`, `UC-PLAN-02`, `UC-PLAN-03`; bảo vệ nghiêm ngặt các quy tắc `BUSR-02`, `BUSR-10`, `NFR-AI-001` và `NFR-PERF-001`.
* **Kỹ thuật:** Frontend (Next.js) triển khai 2 màn hình/modal tương tác kế tiếp nhau, mỗi màn hình sử dụng một hook `useSSE` tái sử dụng được; Backend tổ chức 2 Router endpoints tương ứng trong `roadmap_router.py`.
