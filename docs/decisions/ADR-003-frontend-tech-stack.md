# ADR-003: Lựa chọn Nền tảng Công nghệ Frontend: Angular 19 (Standalone & Signals), TypeScript, Tailwind CSS v4, Spartan UI & Reactive Services

* **Trạng thái:** Được chấp thuận (Approved)
* **Ngày quyết định:** 29/09/2026
* **Người quyết định:** Vũ Toàn Thắng, Phan Đình Duẩn
* **Căn cứ đánh giá:** Khung Rubric Đồ án Tốt nghiệp CNTT — Tiêu chí TC2.1 & TC2.7 (Mức 5)
* **Yêu cầu liên quan:** FR-SESSION-001, FR-SESSION-002, BR-004, NFR-UX-001, NFR-UX-002, EVAL-04, EVAL-05 (Mục tiêu BG-04)

---

## 1. Ngữ cảnh & Đặt vấn đề (Context)
FocusFlow cung cấp 2 không gian trải nghiệm đặc thù:
1. **Không gian Quản lý & Lập kế hoạch (Roadmap Dashboard):** Cần tốc độ tải trang nhanh, hiển thị trực quan các mốc kiến thức và lịch trình dạng Kanban / Timeline.
2. **Không gian Thực thi Tập trung (Study Workspace):** Giao diện tương tác cao với đồng hồ Pomodoro/Stopwatch chạy theo thời gian thực từng giây, danh sách công việc kiểm tra (Checklist), vùng ghi chú nháp (Scratchpad) và gửi tín hiệu duy trì phiên định kỳ (Heartbeat 60s).

Giao diện phải đạt chuẩn tiếp cận **Google Lighthouse Accessibility $\ge 90$** (`NFR-UX-002`), đồng thời tách bạch rạch ròi giữa dữ liệu đồng bộ từ máy chủ (Server State) và trạng thái tương tác tạm thời của phiên học (Workspace State).

---

## 2. Các phương án xem xét (Alternatives)

### Phương án A: React Single Page Application thuần (Vite + React 19)
* Xây dựng ứng dụng React SPA thuần túy đóng gói tĩnh bằng Vite.
* *Ưu điểm:* Đơn giản, cấu hình nhẹ nhàng, hệ sinh thái phong phú.
* *Nhược điểm:* Phải tự thiết lập routing, form validation, dependency injection thủ công; thiếu tính cấu trúc khuôn mẫu tiêu chuẩn hóa cao của các dự án kỹ thuật phần mềm doanh nghiệp lớn.

### Phương án B: Angular kiến trúc NgModule cũ kết hợp NgRx Store (Redux pattern)
* Sử dụng Angular theo phong cách cổ điển với `NgModule` và `NgRx Store` làm kho trạng thái duy nhất.
* *Ưu điểm:* Mô hình Redux quen thuộc trong các đề tài tốt nghiệp truyền thống.
* *Nhược điểm:* Quá nhiều boilerplate (actions, reducers, effects, selectors, module declarations); việc đưa trạng thái tick 1s của bộ đếm Pomodoro vào Redux store gây cồng kềnh và giảm hiệu năng render không cần thiết.

### Phương án C: Angular 19 (Standalone & Signals) + Tailwind CSS v4 + Spartan UI + Reactive Services (Được chọn)
* Sử dụng Angular 19 với kiến trúc **Standalone Components**, loại bỏ hoàn toàn `NgModule`.
* Áp dụng cú pháp **Control Flow** mới (`@if`, `@for`, `@switch`, `@defer`) giúp template ngắn gọn, an toàn kiểu dữ liệu và tăng tốc độ biên dịch.
* Phân chia trạng thái thành 2 tầng độc lập:
  * **Server State:** Quản lý bởi **Reactive Services kết hợp `HttpClient` & RxJS** (caching, handling HTTP requests, stream events).
  * **Client Workspace State:** Quản lý bởi **Angular Signals thuần** (`signal()`, `computed()`, `effect()`) xử lý bộ đếm Pomodoro, trạng thái pause/play và bản nháp Scratchpad với cơ chế Fine-grained Reactivity.
* Bộ giao diện: **Tailwind CSS v4** kết hợp **Spartan UI (Angular CDK)** (bộ primitives mô phỏng kiến trúc Shadcn UI trên nền Angular CDK), bảo đảm chuẩn WAI-ARIA.
* Đóng gói triển khai dạng **Single Page Application (SPA / CSR thuần)** phân phối qua Nginx Alpine container, siêu nhẹ và ổn định.

---

## 3. Quyết định (Decision)
**Chấp thuận Phương án C: Angular 19 (Standalone Components, Signals, Control Flow) + TypeScript Strict + Tailwind CSS v4 + Spartan UI (Angular CDK) + Reactive Services (RxJS).**

---

## 4. Lý do & Đánh đổi (Rationale & Trade-Offs)
* **Tối ưu hóa Phản ứng Cục bộ với Signals (Fine-grained Reactivity):** Bộ đếm Pomodoro cập nhật mỗi 1s chỉ kích hoạt cập nhật chính xác DOM node hiển thị con số thời gian mà không kích hoạt kiểm tra thay đổi (change detection) trên toàn bộ cây component, tối ưu tối đa tài nguyên CPU trình duyệt.
* **Chuẩn Công thái học & Tiếp cận (Rubric TC2.7):** Spartan UI xây dựng trên nền tảng Angular CDK primitives, hỗ trợ đầy đủ các tiêu chuẩn ARIA, bẫy tiêu điểm (focus trap), điều hướng bằng bàn phím (Keyboard Navigation) và độ tương phản màu sắc chuẩn mực, bảo đảm điểm số Lighthouse Accessibility $\ge 90$ dễ dàng.
* **Cấu trúc Kỹ nghệ Chuẩn mực (Disciplined Software Engineering):** Hệ thống Dependency Injection (DI) mạnh mẽ của Angular và mô hình Feature-based Architecture giúp mã nguồn phân tầng rõ ràng, dễ viết Unit Test với Vitest và kiểm thử E2E với Playwright.
* **Đóng gói Triển khai Siêu nhẹ:** Triển khai dạng SPA tĩnh qua container Nginx Alpine giúp kích thước image nhỏ gọn (< 25MB), thời gian khởi động tức thì, loại bỏ hoàn toàn nguy cơ lỗi Hydration Mismatch.

---

## 5. Hệ quả (Consequences)
* **Tích cực:** Trải nghiệm người dùng mượt mà, cấu trúc code hiện đại, tách biệt rõ ràng giữa logic giao diện và logic gọi API, đáp ứng xuất sắc các tiêu chí chấm điểm đồ án tốt nghiệp.
* **Lưu ý:** Đội ngũ phát triển cần nắm vững việc tích hợp giữa RxJS và Angular Signals (`toSignal()`, `toObservable()`), đồng thời sử dụng thành thạo cú pháp Control Flow (`@if`, `@for`, `@defer`) và cơ chế Functional Router Guards / Interceptors trong Angular 19.
