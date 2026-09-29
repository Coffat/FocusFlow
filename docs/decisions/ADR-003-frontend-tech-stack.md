# ADR-003: Lựa chọn Nền tảng Công nghệ Frontend: Next.js 15 (App Router), TypeScript, TanStack Query & Zustand

* **Trạng thái:** Được chấp thuận (Approved)
* **Ngày quyết định:** 29/09/2026
* **Người quyết định:** Vũ Toàn Thắng (Lead BA / System Architect), Phan Đình Duẩn (Senior BA / Quality Lead)
* **Căn cứ đánh giá:** Khung Rubric Đồ án Tốt nghiệp CNTT — Tiêu chí TC2.1 & TC2.7 (Mức 5)
* **Yêu cầu liên quan:** NFR-UX-001, NFR-UX-002, BG-04, EVAL-04, EVAL-05

---

## 1. Ngữ cảnh & Đặt vấn đề (Context)
FocusFlow cung cấp 2 không gian trải nghiệm đặc thù:
1. **Không gian Quản lý & Lập kế hoạch (Roadmap Dashboard):** Cần tốc độ tải trang nhanh, hiển thị trực quan các mốc kiến thức và lịch trình dạng Kanban / Timeline.
2. **Không gian Thực thi Tập trung (Study Workspace):** Giao diện tương tác cao với đồng hồ Pomodoro/Stopwatch chạy theo thời gian thực từng giây, danh sách công việc kiểm tra (Checklist), vùng ghi chú nháp (Scratchpad) và gửi nhịp tim định kỳ (Heartbeat 60s).

Giao diện phải đạt chuẩn tiếp cận **Google Lighthouse Accessibility $\ge 90$** (`NFR-UX-002`), đồng thời tách bạch rạch ròi giữa dữ liệu đồng bộ từ máy chủ (Server State) và trạng thái tương tác tạm thời của phiên học (Client State).

---

## 2. Các phương án xem xét (Alternatives)

### Phương án A: React Single Page Application thuần (Vite + React 19)
* Xây dựng ứng dụng SPA thuần túy đóng gói tĩnh.
* *Ưu điểm:* Đơn giản, cấu hình nhẹ nhàng.
* *Nhược điểm:* Thiếu cơ chế Server Components để tối ưu hóa SEO và tải trang lần đầu; việc tổ chức routing và layout lồng nhau phải tự dựng thủ công.

### Phương án B: Next.js 15 + Redux Toolkit
* Sử dụng Next.js kết hợp Redux Toolkit làm kho trạng thái duy nhất.
* *Ưu điểm:* Mô hình Redux quen thuộc trong các dự án doanh nghiệp lớn.
* *Nhược điểm:* Quá nhiều boilerplate (actions, reducers, slices); quản lý cả dữ liệu API và trạng thái đồng hồ bấm giờ trong cùng một Redux store gây cồng kềnh và giảm hiệu năng re-render.

### Phương án C: Next.js 15 (App Router) + TanStack Query v5 + Zustand (Được chọn)
* Sử dụng Next.js 15 App Router với TypeScript, kết hợp TailwindCSS và bộ component Shadcn UI (Radix UI).
* Phân chia trạng thái thành 2 tầng độc lập:
  * **Server State:** Quản lý bởi **TanStack Query (React Query v5)** (caching, background revalidation, optimistic UI updates).
  * **Client Workspace State:** Quản lý bởi **Zustand** (lưu trữ cục bộ bộ đếm Pomodoro, trạng thái pause/play và bản nháp Scratchpad).

---

## 3. Quyết định (Decision)
**Chấp thuận Phương án C: Next.js 15 (App Router, TypeScript, TailwindCSS, Shadcn UI) + TanStack Query v5 + Zustand.**

---

## 4. Lý do & Đánh đổi (Rationale & Trade-Offs)
* **Tối ưu hóa Phân tách Trạng thái:** TanStack Query giải quyết toàn bộ bài toán đồng bộ dữ liệu với Backend (tự động cache danh sách roadmap, tự động làm mới khi người dùng chuyển tab). Zustand đóng vai trò lưu trữ nhẹ cho bộ đếm Pomodoro mà không gây kích hoạt re-render toàn bộ trang web.
* **Chuẩn Công thái học & Tiếp cận (Rubric TC2.7):** Shadcn UI xây dựng trên nền tảng Radix UI nguyên thủy, hỗ trợ đầy đủ các tiêu chuẩn ARIA, điều hướng bằng bàn phím (Keyboard Navigation) và độ tương phản màu sắc chuẩn mực, bảo đảm điểm số Lighthouse Accessibility $\ge 90$ dễ dàng.

---

## 5. Hệ quả (Consequences)
* **Tích cực:** Trải nghiệm người dùng mượt mà, cấu trúc code hiện đại, tách biệt rõ ràng giữa logic giao diện và logic gọi API.
* **Lưu ý:** Cần nắm vững ranh giới giữa Server Components (`async function Component`) và Client Components (`'use client'`) trong Next.js 15 App Router để tránh lỗi hydration mismatch.
