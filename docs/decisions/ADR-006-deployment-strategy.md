# ADR-006: Chiến lược Triển khai & Vận hành Hybrid: Docker Compose Local & Cloud PaaS (Vercel / Render)

* **Trạng thái:** Được chấp thuận (Approved)
* **Ngày quyết định:** 29/09/2026
* **Người quyết định:** Vũ Toàn Thắng (Lead BA / System Architect), Phan Đình Duẩn (Senior BA / Quality Lead)
* **Căn cứ đánh giá:** Khung Rubric Đồ án Tốt nghiệp CNTT — Tiêu chí TC2.1 & TC2.7 (Mức 5)
* **Yêu cầu liên quan:** NFR-AVAIL-001, NFR-SEC-001, CON-04

---

## 1. Ngữ cảnh & Đặt vấn đề (Context)
Đồ án tốt nghiệp đại học có 2 nhu cầu triển khai mang tính chất đối nghịch:
1. **Nhu cầu Nghiệm thu & Bảo vệ trước Hội đồng:** Yêu cầu hệ thống phải khởi chạy độc lập và ổn định tuyệt đối trên máy tính trạm của sinh viên hoặc máy của giám khảo tại phòng bảo vệ, không được phụ thuộc vào chất lượng sóng wifi hay sự cố nghẽn mạng của phòng thi.
2. **Nhu cầu Đánh giá Thử nghiệm Người dùng Thật (UAT Protocol - `TC2.7`):** Yêu cầu hệ thống phải có tên miền công khai trên Internet để $U = 10 \sim 15$ người dùng thật có thể đăng ký tài khoản, dùng thử trong 7 đến 14 ngày, phục vụ việc đo lường 5 chỉ số KPI định lượng (`TSR \ge 90\%`, `SUS \ge 80`).

---

## 2. Các phương án xem xét (Alternatives)

### Phương án A: Chỉ Triển khai Cục bộ (Local Only - Docker Compose)
* Toàn bộ hệ thống chỉ chạy trên localhost qua Docker.
* *Ưu điểm:* Dễ kiểm soát, 0 chi phí hosting.
* *Nhược điểm:* Không thể gửi link cho người dùng bên ngoài vào dùng thử UAT để thu thập số liệu thực tế; không thỏa mãn tiêu chí TC2.7 Mức 5 của Rubric.

### Phương án B: Tự dựng Hạ tầng Cloud Phức tạp (AWS / GCP Kubernetes / Terraform)
* Triển khai cụm Kubernetes (EKS/GKE), Load Balancers, RDS và ElastiCache trên AWS.
* *Ưu điểm:* Tiêu chuẩn doanh nghiệp quy mô lớn.
* *Nhược điểm:* Chi phí đám mây đắt đỏ vượt quá ngân sách sinh viên; tốn hàng tuần lễ cấu hình hạ tầng mạng thay vì tập trung vào nghiệp vụ cốt lõi; rủi ro sự cố hạ tầng ngày bảo vệ.

### Phương án C: Chiến lược Hybrid: Docker Compose Local + Cloud PaaS Production-Ready (Được chọn)
* **Môi trường Cục bộ:** Sử dụng Docker Compose đóng gói toàn bộ 6 dịch vụ (`web`, `api`, `worker`, `beat`, `db`, `redis`) trong một lệnh duy nhất (`docker compose up --build`), bảo vệ mật khẩu qua file `.env`, phục vụ phát triển hàng ngày và demo trực tiếp trước Hội đồng.
* **Môi trường Cloud UAT (Thực chiến 7–14 ngày):**
  * **Tên miền Gốc Hợp nhất:** Cấu hình tên miền `.focusflow.vn` để giải quyết triệt để rào cản Cross-Site Cookie: Frontend đặt tại `app.focusflow.vn` và Backend đặt tại `api.focusflow.vn`.
  * **Frontend:** Triển khai trên **Vercel** (Global Edge CDN, auto CI/CD từ GitHub).
  * **Backend & Workers:** Triển khai trên **Render Paid Web Service** (để loại bỏ hiện tượng ngủ sau 15 phút, không bị cold start 60s làm méo mó KPI UAT) kết hợp **Render Background Worker** (đảm bảo Celery worker và Celery beat chạy liên tục 24/7).
  * **Database & Cache:** Sử dụng Managed PostgreSQL bền vững (không bị xóa sau 30 ngày) và Managed Upstash Redis.

---

## 3. Quyết định (Decision)
**Chấp thuận Phương án C: Áp dụng Chiến lược Triển khai Hybrid (Docker Compose cho Hội đồng & Cloud Production-Ready trên Tên miền Hợp nhất .focusflow.vn cho UAT).**

---

## 4. Lý do & Đánh đổi (Rationale & Trade-Offs)
* **Bảo đảm An toàn Tuyệt đối Ngày Bảo vệ:** Không có bất kỳ rủi ro nào về mạng chập chờn hay server cloud bảo trì vào đúng giờ bảo vệ khóa luận; sinh viên hoàn toàn làm chủ hệ thống trên máy cá nhân với Docker Compose.
* **Khắc phục Giới hạn Gói Miễn phí:** Việc đầu tư tên miền và gói tài nguyên Render có trả phí cho giai đoạn UAT (7–14 ngày) đảm bảo hệ thống không bị cold start, duy trì Uptime $\ge 95\%$ (`NFR-AVAIL-001`), và cho phép HttpOnly Cookie hoạt động trơn tru giữa Frontend và API.
* **Thỏa mãn 100% Rubric:** Vừa có quy chuẩn đóng gói Docker chuyên nghiệp (TC2.1), vừa có sản phẩm thực chiến trên Internet thu thập số liệu UAT thực chứng (TC2.7).

---

## 5. Hệ quả (Consequences)
* **Tích cực:** Môi trường phát triển và môi trường nghiệm thu tách bạch, đồng nhất và đáng tin cậy. Bảo vệ trọn vẹn điểm số trải nghiệm người dùng (SUS $\ge 80$).
* **Tài liệu hóa:** Nhóm bổ sung tệp `docker-compose.yml` hoàn chỉnh trong mã nguồn và tài liệu hướng dẫn triển khai `DEPLOYMENT.md` từng bước.
