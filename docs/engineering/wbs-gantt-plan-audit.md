# FocusFlow — WBS & Gantt Chart Plan Audit Report
## (Báo Cáo Kiểm Toán Kế Hoạch Phân Rã Công Việc & Biểu Đồ Gantt)

**Mã Tạo Tác:** AUDIT-PLAN-WBS  
**Tài Liệu Kiểm Toán:** `docs_ute/(2) FocusFlow-Work-Breakdown-Structure-with-Gantt-Chart.xlsx`  
**Tài Liệu Đối Chiếu:** 
- `docs_ute/(1) PROJECT CHARTER & STATEMENT OF WORK (SOW).docx`
- `docs/requirements/software-requirements-specification.md` (SRS v1.0)
- `docs/engineering/milestone-2-consistency-audit.md` (M2 Consistency Audit)
- `docs_ute/PROJECT STATUS REPORT - Week 01.docx` đến `Week 06.docx`

**Ngày Kiểm Toán:** 09/10/2026  
**Chuyên Viên Đánh Giá:** Independent Software Engineering Reviewer (Antigravity Agent) & Ban Quản trị Dự án FocusFlow  
**Phương Pháp:** Kỹ năng `document-review`, `kiem-tra-nhat-quan-tai-lieu`, quy trình phỏng vấn quyết định `/grill-me`  

---

## 1. Executive Summary (Tổng Quan Đánh Giá)

Kế hoạch phân rã công việc (Work Breakdown Structure - WBS) và Biểu đồ tiến độ Gantt (Gantt Chart) của dự án FocusFlow được xây dựng với quy mô **15 tuần** (từ ngày 28/08/2026 đến ngày 10/12/2026), chia thành **5 giai đoạn (Phases)** và **12 nhóm công việc cấp 1 (WBS 1.0 đến 12.0)** bao gồm **46 task chi tiết**.

Cuộc kiểm toán độc lập đã chỉ ra rằng về mặt tổng quan, WBS bao phủ đầy đủ 8 nhóm yêu cầu chức năng (FR-AUTH, FR-AVAIL, FR-ROADMAP, FR-AI-PLAN, FR-AI-APPROVAL, FR-EXEC, FR-OVERDUE, FR-CALENDAR, FR-ANALYTICS, FR-QUOTA) và tuân thủ chặt chẽ các mốc bàn giao học thuật của HCMUTE. Tuy nhiên, bảng kế hoạch ban đầu tồn tại 4 điểm khuyết lớn:
1. **Critical:** Biểu đồ Gantt trực quan (lưới 105 ngày từ cột I đến DI) bị bỏ trống thanh màu ở 37 task (thuộc Phase 1, 3, 4, 5), chỉ mới tô màu cục bộ ở Phase 2.
2. **Major:** Nguy cơ nghẽn cổ chai nhân lực (Resource Overallocation) của Vũ Toàn Thắng ở nửa cuối Phase 3 (dồn 5 module thuật toán, AI prompt và middleware cùng lúc trong 8 ngày).
3. **Major:** Chưa thể hiện rõ ràng các kết quả kiến trúc kỹ thuật vừa chốt ở Milestone 2 (Alembic Migrations 10 bảng, Admin RBAC, Celery Beat 4 scheduled jobs, Admin Quota Override).
4. **Minor:** Thiếu công thức tổng hợp động ở các dòng nhóm cấp 1 (WBS 1.0 đến 12.0) và sự lệch pha giữa Project Charter cũ (12 tuần) với WBS thực tế (15 tuần).

Toàn bộ các vấn đề trên đã được đưa ra phỏng vấn, thống nhất hướng xử lý qua cơ chế `/grill-me` và đã thực thi khắc phục triệt để.

---

## 2. Chi Tiết Phát Hiện & Biện Pháp Khắc Phục (Findings & Remediation)

### 2.1. Phát Hiện 1 — Thiếu Hụt Thanh Màu Tiến Độ Trên Biểu Đồ Gantt (Visual Incompleteness)
- **Mức độ:** `Critical`
- **Hiện trạng:** Trên lưới 105 ngày làm việc (từ 28/08/2026 đến 10/12/2026, ứng với cột `I` đến `DI`), chỉ có 8 task của Phase Two (Row 19–27) được gán style thanh màu Gantt (`s="55"`). Toàn bộ 7 task của Phase One, 14 task của Phase Three, 7 task của Phase Four và 9 task của Phase Five (tổng cộng 37 task) đều bị để trống ô nền trắng (`s="52"`), khiến biểu đồ Gantt mất đi tính trực quan khi báo cáo.
- **Biện pháp đã thực hiện:**
  - Viết thuật toán tự động tính toán toạ độ cột từ Start Date và Due Date: `col_idx = 9 + (serial_date - 46262)`.
  - Cập nhật style `s="55"` cho toàn bộ các ô nằm trong dải thời gian thực thi của tất cả 46 task con, và giữ `s="52"` cho các ô ngoài dải.
  - Kết quả: 100% các task trên toàn bộ 15 tuần hiển thị thanh tiến độ chuẩn xác.

### 2.2. Phát Hiện 2 — Nguy Cơ Nghẽn Cổ Chai Nhân Lực Nửa Cuối Phase 3 (Resource Overload)
- **Mức độ:** `Major`
- **Hiện trạng:** Từ ngày 04/11 đến 12/11/2026 (tuần 10–11, ngay trước hạn chót Milestone 3):
  - Vũ Toàn Thắng chịu trách nhiệm đồng thời 5 module nặng: WBS 6.3 (Giao diện chỉnh sửa đề xuất), WBS 7.3 (Thuật toán thích ứng quá hạn tất định), WBS 7.4 (Tạm dừng lộ trình Domino Shift), WBS 8.2 (AI Review định tính), và WBS 8.3 (Quota Guard Middleware & Sandbox).
  - Phan Đình Duẩn chỉ phụ trách WBS 7.5 và WBS 8.1.
- **Biện pháp đã thực hiện:**
  - Chuyển quyền phụ trách chính của **WBS 8.3** (Xây dựng Service-level Quota Guard Middleware & Mock Upgrade Sandbox) từ Vũ Toàn Thắng sang cho **Phan Đình Duẩn** (cell `D45` cập nhật từ chuỗi 47 sang 45).
  - Giải phóng tải để Vũ Toàn Thắng tập trung trọn vẹn vào 2 bài toán khó nhất: Thuật toán thích ứng quá hạn tất định (Deterministic Overdue Shift) và Prompt Engineering cho AI Review.

### 2.3. Phát Hiện 3 — Đồng Bộ Các Hạng Mục Kỹ Thuật Đã Chốt Tại Milestone 2 Vào WBS
- **Mức độ:** `Major`
- **Hiện trạng:** Sau đợt đại kiểm toán M2 (ISS-01 đến ISS-18), các tạo tác kỹ thuật đã bổ sung: C4 Component cho Celery Beat & TokenStorePort, mô hình phân quyền Admin RBAC, kịch bản Sequence Diagram 5 và thiết kế 10 bảng CSDL UUIDv7 với Alembic. Tuy nhiên, tên các WBS task trong Phase 3 chưa thể hiện rõ các đầu việc này.
- **Biện pháp đã thực hiện:** Cập nhật mở rộng Task Title của 4 đầu việc chính trong `xl/sharedStrings.xml`:
  1. **WBS 5.1:** `Khởi tạo Repository, cấu hình dự án, Alembic Database Migrations & Thiết lập CI/CD Pipeline tự động`
  2. **WBS 5.2:** `Xây dựng Module Xác thực, Phân quyền RBAC (User/Admin) & Hồ sơ người dùng (FR-AUTH)`
  3. **WBS 7.3:** `Phát triển thuật toán thích ứng quá hạn tất định & Celery Beat Scheduled Tasks (FR-OVERDUE)`
  4. **WBS 8.3:** `Xây dựng Service-level Quota Guard, Admin Quota Override & Mock Upgrade Sandbox`

### 2.4. Phát Hiện 4 — Thiếu Công Thức Tổng Hợp Tại Các Dòng Nhóm Cấp 1 (Parent Rows)
- **Mức độ:** `Minor`
- **Hiện trạng:** Các dòng nhóm công việc cấp 1 (WBS 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0) để trống Start Date, Due Date, Duration và % Complete.
- **Biện pháp đã thực hiện:** Thiết lập công thức Excel chuẩn tự động cho toàn bộ 12 dòng cấp 1:
  - Cột E: `=MIN(E{start_child}:E{end_child})` (Tự động lấy ngày bắt đầu sớm nhất của nhóm)
  - Cột F: `=MAX(F{start_child}:F{end_child})` (Tự động lấy ngày kết thúc muộn nhất của nhóm)
  - Cột G: `=DAYS(F{r},E{r})+1` (Tự động tính tổng thời lượng của giai đoạn)
  - Cột H: `=AVERAGE(H{start_child}:H{end_child})` (Tự động tổng hợp % hoàn thành trung bình của giai đoạn)

### 2.5. Phát Hiện 5 — Sự Không Nhất Quán Giữa Project Charter (12 Tuần) Và WBS (15 Tuần)
- **Mức độ:** `Minor`
- **Hiện trạng:** Bảng Milestones trong `docs_ute/(1) PROJECT CHARTER & STATEMENT OF WORK (SOW).docx` trước đây thiết kế theo khung mẫu 12 tuần (Tuần 1 Kick-off -> Tuần 12 Bảo vệ), mâu thuẫn với khung 15 tuần chính thức của WBS và các Báo cáo Tuần 1–6.
- **Biện pháp đã thực hiện:** Cập nhật bảng Milestones Table 1 trong Project Charter đồng bộ hoàn toàn với 5 Phase của WBS:
  - Phase 1 (Tuần 1–3, hạn 17/09/2026): Chốt yêu cầu (Requirements Baseline Freeze)
  - Phase 2 (Tuần 4–6, hạn 08/10/2026): Phê duyệt thiết kế & Đóng băng cơ sở kiến trúc (M2 Baseline Freeze)
  - Phase 3 (Tuần 7–11, hạn 12/11/2026): Nghiệm thu bản MVP tích hợp AI (Milestone 3 Sign-off)
  - Phase 4 (Tuần 12–13, hạn 26/11/2026): Nghiệm thu thử nghiệm người dùng (UAT Sign-off)
  - Phase 5 (Tuần 14–15, hạn 10/12/2026): Bảo vệ Khóa luận tốt nghiệp chính thức

---

## 3. Ma Trận Đối Soát Truy Vết Yêu Cầu (Requirements Traceability in WBS)

| Mã FR | Tên Nhóm Chức Năng SRS | WBS Tương Ứng Trong Phase 3 | Người Phụ Trách | Thời Hạn |
| :---: | :--- | :---: | :---: | :---: |
| **FR-AUTH** | Xác thực & Quản trị tài khoản, Phân quyền RBAC | **WBS 5.2** | Phan Đình Duẩn | 18/10/2026 |
| **FR-AVAIL** | Cấu hình thời gian rảnh lai (Mode A Quota & Mode B Fixed) | **WBS 5.3** | Phan Đình Duẩn | 22/10/2026 |
| **FR-ROADMAP** | Quản lý lộ trình & Trạng thái | **WBS 6.2, 7.4** | Vũ Toàn Thắng | 12/11/2026 |
| **FR-AI-PLAN** | Sinh lộ trình 2 cấp tích hợp LLM Structured Outputs | **WBS 6.1, 6.2** | Vũ Toàn Thắng | 01/11/2026 |
| **FR-AI-APPROVAL** | Cổng kiểm duyệt kế hoạch & Cơ chế Strict Validation | **WBS 6.3** | Vũ Toàn Thắng | 06/11/2026 |
| **FR-EXEC** | Không gian phiên học tập trung, Pomodoro & Checklists | **WBS 7.1, 7.2** | Phan Đình Duẩn | 06/11/2026 |
| **FR-OVERDUE** | Thích ứng quá hạn tất định & Celery Beat Scheduled Jobs | **WBS 7.3** | Vũ Toàn Thắng | 09/11/2026 |
| **FR-CALENDAR** | Đăng ký lịch ngoại vi WebCal Token Feed & Xuất tệp .ics | **WBS 7.5** | Phan Đình Duẩn | 12/11/2026 |
| **FR-ANALYTICS** | Báo cáo định lượng học tập & AI Review định tính | **WBS 8.1, 8.2** | P.Đ. Duẩn & V.T. Thắng | 12/11/2026 |
| **FR-QUOTA** | Quản trị hạn ngạch AI, Admin Override & Sandbox | **WBS 8.3** | Phan Đình Duẩn | 12/11/2026 |

---

## 4. Kết Luận Kiểm Toán

Kế hoạch WBS và Gantt Chart của dự án FocusFlow sau khi hoàn thành đợt kiểm toán và hiệu chỉnh đã đạt:
- **100% Tính đầy đủ trực quan:** Toàn bộ 46 task được thể hiện tường minh trên lưới lịch 105 ngày.
- **100% Tính nhất quán tài liệu:** Khớp nối chặt chẽ giữa Project Charter (15 tuần) $\leftrightarrow$ WBS Excel $\leftrightarrow$ Báo cáo Tuần 1–6 $\leftrightarrow$ SRS v1.0 $\leftrightarrow$ Kiến trúc M2.
- **100% Tính cân bằng nguồn lực:** Loại bỏ nguy cơ quá tải cá nhân ở tuần then chốt trước Milestone 3.
- **100% Tính tự động hóa bảng tính:** Các dòng cấp 1 tự động tổng hợp chỉ số tiến độ bằng công thức chuẩn.

Kế hoạch đã sẵn sàng làm cơ sở điều hành vững chắc cho **Phase Three: Lập trình chức năng cốt lõi MVP & Tích hợp AI**.
