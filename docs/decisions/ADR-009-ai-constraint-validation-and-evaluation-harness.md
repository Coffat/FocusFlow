# ADR-009: Lựa chọn Cơ chế Xác thực Đề xuất Lịch trình Đa tầng (Hybrid Validation Gate) và Bộ khung Đánh giá Thực nghiệm (AI Evaluation Harness)

* **Trạng thái:** Được chấp thuận (Approved — Đã chuẩn hóa theo SRS v1.1 & Kết quả Rà soát Kiến trúc)
* **Ngày quyết định:** 16/10/2026
* **Người quyết định:** Vũ Toàn Thắng, Phan Đình Duẩn
* **Căn cứ đánh giá:** Khung Rubric Đồ án Tốt nghiệp CNTT — Tiêu chí TC2.1 & TC2.3 (Mức 5)
* **Yêu cầu liên quan:** FR-PLAN-002, FR-PLAN-003, FR-PLAN-005, NFR-AI-001, NFR-AI-003, EVAL-06, EVAL-07, EVAL-08, BUSR-02, BUSR-03, BUSR-04, BUSR-05

---

## 1. Ngữ cảnh & Đặt vấn đề (Context)
Trong hệ thống FocusFlow, quá trình lập lịch học tập bằng External LLM (Google Gemini / OpenAI) thường đối mặt với hai thách thức kỹ thuật lớn:
1. **Ảo giác Lập lịch (Hallucinated Scheduling) & Vi phạm Ràng buộc Cứng:** LLM thường tính toán thời gian kém, có thể xếp các task vượt quá số giờ rảnh trong ngày của người học (Overbooking), xếp chồng chéo mốc giờ (Time Overlap), hoặc xếp task nâng cao trước task tiên quyết. Hệ thống bắt buộc phải đảm bảo $100\%$ không vi phạm các ràng buộc cứng này trước khi người dùng xem xét áp dụng.
2. **Thiếu Bộ khung Đo lường Thực nghiệm Khoa học cho Luận văn:** Để chứng minh tính khả thi và độ tin cậy của giải pháp AI trong Đồ án Tốt nghiệp Kỹ sư CNTT, nhóm nghiên cứu cần số liệu thực nghiệm đo đạc độc lập, có thể tái lập, so sánh được giữa các mô hình (Gemini 2.5 Flash, GPT-4o-mini, Local SLM) trên bộ kịch bản kiểm thử đa dạng.

---

## 2. Các phương án xem xét (Alternatives)

### Phương án A: Chỉ Dùng Pydantic Schema Validation Đơn thuần
* *Ưu điểm:* Cài đặt rất nhanh, độ trễ thấp.
* *Nhược điểm:* Pydantic chỉ kiểm tra cấu trúc cú pháp và kiểu dữ liệu (ngày, số phút). Nó không kiểm tra được logic nghiệp vụ như tổng thời lượng ngày vượt quỹ rảnh, xung đột khung giờ, hay chu trình phụ thuộc giữa các task. Toàn bộ gánh nặng kiểm tra dồn lên mắt người dùng khi xem giao diện Preview.

### Phương án B: Sử dụng LLM-as-a-Judge Toàn phần (Ralph-style Goal Loop như Hermes)
* Gửi toàn bộ lịch do AI sinh qua một LLM thứ hai (Judge) để thẩm định mọi khía cạnh, lặp lại cho đến khi Judge đồng ý.
* *Ưu điểm:* Linh hoạt về mặt nhận thức.
* *Nhược điểm:* Rất chậm (có thể vượt trần 55s của NFR-PERF-001), tốn kém chi phí token gấp đôi, và bản thân LLM Judge cũng tính toán toán học không đáng tin cậy bằng thuật toán tất định (Deterministic Code).

### Phương án C: Cổng Xác thực Đa tầng Lai (Hybrid Validation Gate) kết hợp AI Evaluation Harness Độc lập (Được chọn)
* **Kiến trúc Runtime:**
  1. *Tầng 1 (Cú pháp & Schema)*: Pydantic v2 kiểm định tính toàn vẹn JSON và quan hệ khóa ngoại `milestone_id`.
  2. *Tầng 2 (Ràng buộc Cứng Tất định - 100% Python Engine)*: Kiểm tra toán học quỹ thời gian rảnh (Hard Ceiling cho Mode A), kiểm tra từng task nằm trọn trong slot rảnh thực tế qua `validate_proposal_against_slots` (Mode B với dung sai Soft Overflow $\le 30$ phút cho phần tràn ngoài biên không va chạm), chống trùng lịch (Zero Overlap), tuân thủ biên roadmap, và thứ tự prerequisite.
  3. *Tầng 3 (Kiểm định Sư phạm - Lightweight LLM Judge)*: Đánh giá độ dốc nhận thức (khối lượng kiến thức nền tảng xếp trước nâng cao).
  * *Chính sách Thử lại có Ngữ cảnh (Structured Feedback Retry)*: Nếu vi phạm Tầng 1 hoặc Tầng 2, đóng gói mã lỗi cụ thể gửi lại cho LLM tự sửa (tối đa 2 lần retry).
  * *Chính sách Fail-Open có kiểm soát cho Tầng 3*: Nếu Ràng buộc Cứng đã thỏa mãn $100\%$ nhưng Tầng 3 gặp sự cố timeout/5xx hoặc có góp ý nhẹ, hệ thống vẫn trả về Schedule Preview kèm nhãn cảnh báo/góp ý để người học tự quyết định trước khi Apply. Tuyệt đối không chặn người học nếu ràng buộc toán học đã hợp lệ.
* **Kiến trúc Offline Evaluation (`backend/tests/ai_evals/`)**:
  * Xây dựng bộ công cụ chạy batch benchmark độc lập trên 100+ kịch bản chuẩn (JSONL), đo lường 3 tầng: Pass@1 Schema thô, Tỷ lệ vi phạm ràng buộc thô, và Tỷ lệ thành công hệ thống sau retry; xuất số liệu trực tiếp phục vụ Chương 5 Luận văn.

---

## 3. Quyết định (Decision)
**Chấp thuận Phương án C: Triển khai Cổng Xác thực Đa tầng Lai (Hybrid Validation Gate) cho luồng runtime lập lịch và Xây dựng Bộ khung AI Evaluation Harness (100+ scenarios) cho công tác thử nghiệm đo lường khoa học của Đồ án.**

---

## 4. Lý do & Đánh đổi (Rationale & Trade-Offs)
* **Phân định Trách nhiệm Chuẩn mực (Separation of Concerns):** Thuật toán tất định làm việc tính toán số học (giờ rảnh, chống trùng); LLM làm việc sáng tạo ngữ nghĩa và đánh giá sư phạm.
* **Bảo vệ Trải nghiệm & Độ trễ:** Cơ chế Fail-Open có kiểm soát ở Tầng 3 bảo đảm hệ thống luôn tuân thủ ngắt cứng 55s (`NFR-PERF-001`) và không từ chối vô lý một đề xuất đã hợp lệ về mặt toán học.
* **Giá trị Thực nghiệm Xuất sắc cho Khóa luận:** Cung cấp số liệu định lượng có đối chứng (Gemini vs GPT-4o-mini vs Local Ollama) cho Tiêu chí Rubric TC2.3 Mức 5.

---

## 5. Hệ quả (Consequences)
* **Tích cực:** Độ tin cậy của đề xuất lịch trình đạt $100\%$ Zero Overbooking; loại bỏ hoàn toàn lỗi lịch trình bất khả thi; cung cấp bằng chứng thực nghiệm khoa học.
* **Tiêu cực / Rủi ro:** Cần duy trì và viết thêm mã nguồn cho `ConstraintValidationEngine` và bộ kịch bản 100+ JSONL trong thư mục test.
