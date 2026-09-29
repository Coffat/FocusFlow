# ADR-001: Lựa chọn Phong cách Kiến trúc Lục giác (Hexagonal / Ports & Adapters) trong Modular Monolith

* **Trạng thái:** Được chấp thuận (Approved)
* **Ngày quyết định:** 29/09/2026
* **Người quyết định:** Vũ Toàn Thắng (Lead BA / System Architect), Phan Đình Duẩn (Senior BA / Quality Lead)
* **Căn cứ đánh giá:** Khung Rubric Đồ án Tốt nghiệp CNTT — Tiêu chí TC2.1 & TC2.3 (Mức 5)
* **Yêu cầu liên quan:** Toàn bộ SRS v1.0, BUSR-01 đến BUSR-10

---

## 1. Ngữ cảnh & Đặt vấn đề (Context)
FocusFlow là hệ thống hỗ trợ lập kế hoạch và thực thi tự học thích ứng tích hợp AI. Hệ thống chứa các quy tắc nghiệp vụ cốt lõi quan trọng:
* Thuật toán tịnh tiến lịch học tất định (Domino Shift) khi tạm dừng hoặc trễ hạn.
* Cổng kiểm duyệt nghiêm ngặt (Validation Gate) chặn xếp lịch vượt quá quỹ giờ rảnh (Hard Ceiling).
* Quản trị hạn ngạch AI nguyên tử và mô hình hóa thời gian rảnh lai.

Đồng thời, hệ thống phụ thuộc vào các dịch vụ bên ngoài có độ trễ và rủi ro thay đổi cao:
* Các nhà cung cấp mô hình ngôn ngữ lớn (Google Gemini, OpenAI).
* Các ứng dụng lịch ngoại vi của người dùng (Google Calendar, Apple Calendar).

Nhóm phát triển cần một phong cách kiến trúc đảm bảo:
1. Logic nghiệp vụ cốt lõi (Domain Logic) được bảo vệ độc lập, không bị phụ thuộc vào bất kỳ framework web, cơ sở dữ liệu hay thư viện AI cụ thể nào.
2. Dễ dàng kiểm thử đơn vị (Unit Test) toàn bộ thuật toán dời lịch và kiểm tra trần giờ mà không cần kết nối mạng hay cơ sở dữ liệu thật.
3. Không làm gia tăng độ phức tạp vận hành và triển khai quá mức đối với đồ án tốt nghiệp của 2 sinh viên.

---

## 2. Các phương án xem xét (Alternatives)

### Phương án A: Full-stack Framework Monolith (Next.js duy nhất)
* Sử dụng Next.js cho toàn bộ Frontend, Backend Route Handlers, Server Actions, gọi Prisma ORM và gọi LLM API trực tiếp.
* *Ưu điểm:* 1 repository, 1 ngôn ngữ TypeScript, khởi tạo nhanh.
* *Nhược điểm:* Logic nghiệp vụ bị trộn lẫn với mã giao diện và mã truy vấn CSDL; rất khó kiểm thử độc lập; hạn chế trong việc khai thác các thư viện AI mạnh mẽ của Python.

### Phương án B: Microservices Architecture
* Phân tách thành 4–5 microservices độc lập (Auth Service, Roadmap Service, Session Service, AI Gateway Service, Calendar Service).
* *Ưu điểm:* Phân tách độc lập về mã nguồn và khả năng scale từng dịch vụ.
* *Nhược điểm:* Quá phức tạp cho đồ án tốt nghiệp (Over-engineering). Gây phát sinh các bài toán khó giải: giao dịch phân tán (Distributed Transactions), mạng chập chờn giữa các service (Network Latency), triển khai phức tạp và khó debug.

### Phương án C: Modular Monolith kết hợp Kiến trúc Lục giác (Hexagonal / Ports & Adapters) (Được chọn)
* Tách biệt Web Frontend (Next.js) và Backend API (Python/FastAPI).
* Phía Backend tổ chức theo mô hình Ports & Adapters (Lục giác):
  * **Domain Layer (Lõi):** Chứa thực thể và dịch vụ miền thuần túy Python, 0 phụ thuộc thư viện ngoài.
  * **Application Layer:** Chứa ca sử dụng (Use Cases) và khai báo các Cổng (Ports - Abstract Base Classes).
  * **Infrastructure Layer:** Chứa các Bộ điều hợp (Adapters) kết nối PostgreSQL, Redis, Gemini API, iCalendar.
  * **Presentation Layer:** FastAPI Routers tiếp nhận HTTP và kích hoạt Use Case.

---

## 3. Quyết định (Decision)
**Chấp thuận Phương án C: Modular Monolith kết hợp Kiến trúc Lục giác (Hexagonal Architecture / Clean Architecture).**

---

## 4. Lý do & Đánh đổi (Rationale & Trade-Offs)
* **Khả năng kiểm thử tối đa (Testability):** Có thể viết hàng trăm bài kiểm thử Unit Test cho thuật toán Domino Shift và Hard Ceiling Validator chạy trong vài mili-giây mà không cần dựng database hay mock API mạng phức tạp.
* **Linh hoạt thay đổi công nghệ (Maintainability & Decoupling):** Khi cần đổi từ Google Gemini sang OpenAI hoặc đổi từ PostgreSQL sang một CSDL khác, nhóm chỉ cần viết một Adapter mới mà không cần chỉnh sửa một dòng mã nào trong tầng Domain hay Use Case.
* **Phù hợp năng lực và thời gian đồ án:** Kiến trúc Modular Monolith mang lại sự sạch sẽ của Microservices nhưng không phải trả giá cho độ phức tạp vận hành phân tán.

---

## 5. Hệ quả (Consequences)
* **Tích cực:** Mã nguồn sạch, cấu trúc rõ ràng, đáp ứng xuất sắc tiêu chí chấm điểm kiến trúc phần mềm chuẩn mực (Rubric TC2.1).
* **Tiêu cực / Rủi ro:** Cần viết nhiều tầng trừu tượng (Ports, DTOs, Mappers) tạo cảm giác có nhiều file lúc ban đầu. Nhóm khắc phục bằng cách thiết lập khung mẫu (Scaffolding templates) chuẩn hóa.
