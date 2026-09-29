# ADR-002: Lựa chọn Nền tảng Công nghệ Backend: Python 3.12, FastAPI, Pydantic v2 & SQLAlchemy 2.0 Async

* **Trạng thái:** Được chấp thuận (Approved)
* **Ngày quyết định:** 29/09/2026
* **Người quyết định:** Vũ Toàn Thắng (Lead BA / System Architect), Phan Đình Duẩn (Senior BA / Quality Lead)
* **Căn cứ đánh giá:** Khung Rubric Đồ án Tốt nghiệp CNTT — Tiêu chí TC2.1 & TC2.3 (Mức 5)
* **Yêu cầu liên quan:** NFR-PERF-001, NFR-PERF-002, NFR-AI-001

---

## 1. Ngữ cảnh & Đặt vấn đề (Context)
FocusFlow là hệ thống tích hợp sâu với trí tuệ nhân tạo (AI/LLM) để tự động hóa phân rã lộ trình học tập, sinh mốc kiến thức (Milestones), phân bổ đầu việc (Tasks) và nhận xét báo cáo định kỳ.

Hệ thống đòi hỏi:
1. Nền tảng Backend phải hỗ trợ hệ sinh thái AI/LLM mạnh mẽ và được các nhà cung cấp mô hình (Google, OpenAI) ưu tiên SDK chính thức.
2. Cơ chế xác thực dữ liệu đầu vào và đầu ra cực kỳ nghiêm ngặt nhằm đảm bảo 100% phản hồi từ AI tuân thủ đúng định dạng JSON Schema (`NFR-AI-001`).
3. Khả năng xử lý tác vụ bất đồng bộ (Asynchronous I/O) hiệu năng cao, phản hồi API $\le 200$ms (`NFR-PERF-002`).

---

## 2. Các phương án xem xét (Alternatives)

### Phương án A: Node.js / TypeScript (NestJS hoặc Express)
* Sử dụng TypeScript cho toàn bộ Backend, đồng nhất ngôn ngữ với Frontend.
* *Ưu điểm:* Chia sẻ định nghĩa kiểu dữ liệu (Types/Interfaces) giữa Frontend và Backend.
* *Nhược điểm:* Các thư viện và SDK AI trên Node.js thường đi sau Python về tính năng; việc ép kiểu JSON Schema phức tạp với AI không tự nhiên và mạnh mẽ bằng Pydantic.

### Phương án B: Python 3.12 + FastAPI + Pydantic v2 + SQLAlchemy 2.0 Async (Được chọn)
* Sử dụng FastAPI trên nền ASGI Uvicorn, kết hợp Pydantic v2 và SQLAlchemy 2.0 Async với driver `asyncpg`.
* *Ưu điểm:*
  * **Hệ sinh thái AI Tối thượng:** Python là ngôn ngữ số 1 về Trí tuệ Nhân tạo.
  * **Pydantic v2:** Nhân Rust cực nhanh, hỗ trợ xuất và thẩm định JSON Schema nguyên bản cho LLM Structured Outputs.
  * **Async I/O:** Xử lý hàng ngàn kết nối đồng thời với độ trễ thấp, tích hợp hoàn hảo với Server-Sent Events (SSE).
* *Nhược điểm:* Khác ngôn ngữ với Frontend (Next.js/TypeScript).

---

## 3. Quyết định (Decision)
**Chấp thuận Phương án B: Sử dụng Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0 Async (`asyncpg`) và Alembic.**

---

## 4. Lý do & Đánh đổi (Rationale & Trade-Offs)
* **Khả năng kiểm soát rủi ro AI (Rubric TC2.3 Mức 5):** Pydantic v2 cho phép định nghĩa các Schema nghiêm ngặt (`ProposalPlanSchema`, `MilestoneListSchema`). Khi Gemini trả về kết quả, Pydantic tự động thẩm định và bóc tách dữ liệu; nếu có sai sót cấu trúc, hệ thống kích hoạt retry tự động ngay lập tức mà không gây crash ứng dụng.
* **Tài liệu hóa API tự động:** FastAPI tự động sinh tài liệu Swagger UI / OpenAPI Spec tương tác trực quan tại `/docs`, giúp đội ngũ Frontend (Next.js) tích hợp API nhanh chóng và dễ dàng demo trước Hội đồng.

---

## 5. Hệ quả (Consequences)
* **Tích cực:** Tối ưu hóa hiệu năng, xử lý AI mượt mà, mã nguồn ngắn gọn và dễ bảo trì.
* **Khắc phục sự khác biệt ngôn ngữ:** Frontend sinh kiểu TypeScript an toàn từ OpenAPI Schema của FastAPI bằng công cụ `openapi-typescript` hoặc định nghĩa DTOs tương ứng.
