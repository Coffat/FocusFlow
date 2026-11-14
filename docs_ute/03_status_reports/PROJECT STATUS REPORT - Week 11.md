# PROJECT STATUS REPORT
## (BÁO CÁO TÌNH TRẠNG DỰ ÁN)

**Dự Án:** FocusFlow — Hệ thống hỗ trợ lập kế hoạch và thực thi lộ trình tự học thích ứng tích hợp AI  
**Kỳ Báo Cáo:** Tuần 11 - Từ ngày 06/11/2026 đến ngày 12/11/2026  
**Người Lập Báo Cáo:** Vũ Toàn Thắng (23110329) & Phan Đình Duẩn (23110192)  
**Gửi Đến:** ThS. Vũ Đình Bảo (Giảng viên Hướng dẫn — Khoa Công nghệ Thông tin, HCMUTE)  
**Ngày Gửi:** 13/11/2026  

---

### 1. EXECUTIVE SUMMARY (TỔNG QUAN ĐIỀU HÀNH)

Đánh giá tổng quan về "sức khỏe" dự án thông qua hệ thống đèn tín hiệu (RAG Status) sau khi đối chiếu kế hoạch WBS/Gantt và kết quả thực thi trong Tuần 11 (Sprint 3 — Không gian thực thi phiên học & Cơ chế thích ứng tự động):

| Hạng mục | Trạng thái | Diễn giải ngắn gọn |
| :--- | :---: | :--- |
| **Tiến độ (Schedule)** | <span style="color:#2e7d32">●</span> **Green** | Hoàn thành đúng hạn 100% Lát cắt lõi Sprint 3 vào ngày 12/11/2026 với 3 hạng mục trọng tâm: Study Session & Study Tool Suite (7.1), Daily Learning Check-in & xử lý gián đoạn (7.2), Rolling-Horizon Overdue Recovery (7.3). Đồng thời triển khai sớm và tích hợp hàng loạt tính năng nền tảng: Roadmap Hub & Wizard UI, Dashboard học tập định lượng (8.1), Profile & Settings 4 tab (5.4/8.3), và Calendar sync prep (7.5). |
| **Phạm vi (Scope)** | <span style="color:#2e7d32">●</span> **Green** | Bám sát tuyệt đối yêu cầu chức năng trong SRS v1.3 và cấu trúc WBS. Giữ vững nguyên tắc cốt lõi: AI và Scheduler chỉ đóng vai trò đề xuất bản nháp (`ScheduleProposal(DRAFT)`), tuyệt đối không tự ý ghi đè hay dời lịch trong `OfficialSchedule` khi chưa có thao tác xác nhận `Apply` từ người học. |
| **Chất lượng (Quality)** | <span style="color:#2e7d32">●</span> **Green** | Đảm bảo tính toàn vẹn hệ thống: Bộ đếm Pomodoro hoạt động chuẩn xác dựa trên mốc thời gian thực (`Date.now()`) kết hợp cơ chế nhịp tim ngầm (`heartbeat 60s`) không phụ thuộc vòng đời tab; API contracts được đồng bộ nghiêm ngặt qua openapi-typescript; hệ thống kiểm thử tự động (Unit test, E2E Onboarding & Availability) duy trì trạng thái xanh. |
| **Rủi ro (Risk)** | <span style="color:#2e7d32">●</span> **Green** | Các rủi ro về sai lệch lịch học do tự động hóa đã được kiểm soát hoàn toàn bằng Strict Apply Gate; rủi ro mất mát dữ liệu phiên học được triệt tiêu bằng cơ chế tự động lưu tạm tiến độ; các giải pháp bảo mật cho giai đoạn đồng bộ lịch ngoại vi (SSRF/HMAC) đã được thiết kế sẵn sàng. |

**Chú thích:**
- <span style="color:#2e7d32">●</span> **Green (Xanh):** Ổn định, đúng tiến độ, không có vấn đề lớn cản trở.
- <span style="color:#f57c00">●</span> **Amber (Vàng):** Có rủi ro tiềm ẩn hoặc chậm trễ nhẹ, cần chú ý theo dõi.
- <span style="color:#c62828">●</span> **Red (Đỏ):** Vấn đề nghiêm trọng, trượt hạn hoặc có lỗi chặn cần sự can thiệp ngay lập tức từ cấp trên.

---

### 2. HOẠT ĐỘNG ĐÃ HOÀN THÀNH TRONG KỲ (ACCOMPLISHMENTS)

Tuần 11 ghi nhận khối lượng công việc hoàn thành toàn diện, bao gồm cả các hạng mục cam kết trong Sprint 3 theo WBS và các tính năng mở rộng/triển khai sớm phục vụ hoàn thiện sản phẩm:

#### A. Nhóm trọng tâm Sprint 3 (Theo kế hoạch WBS/Gantt — Đạt 100%):

| ID | Công việc / Hạng mục | Người phụ trách | Kết quả | Ghi chú chi tiết |
| :---: | :--- | :---: | :---: | :--- |
| **7.1** | Hiện thực Study Session & Study Tool Suite: Pomodoro/Stopwatch, checklist, notes và lưu trạng thái [FR-SESSION-001, FR-TASK-001..003, FR-SCHEDULE-001; UC-13, UC-14; ADR-001, ADR-004, ADR-007, ADR-009] | Phan Đình Duẩn | Hoàn thành | Xây dựng hoàn chỉnh Không gian học tập tập trung (`Study Workspace`): Tích hợp đồng hồ đếm thời gian kép Pomodoro / Stopwatch vận hành trên mốc thời gian thực (`Date.now()`); cơ chế giữ nhịp tim định kỳ (`heartbeat 60s`) bảo toàn phiên học khi người dùng chuyển tab hoặc mất mạng tạm thời; bảng danh sách đầu việc (task checklist); khung ghi chú nhanh bài học (session notes) và thanh tiến độ học tập trực quan. |
| **7.2** | Daily Learning Check-in, Key Takeaway bắt buộc, xử lý gián đoạn và hoàn trả task chưa xong [FR-SESSION-002..003, FR-TASK-002; UC-14..16; ADR-004, ADR-009, ADR-010] | Phan Đình Duẩn | Hoàn thành | Hoàn thiện luồng Daily Learning Check-in đầu phiên; cơ chế bắt buộc tóm tắt nội dung thu hoạch (Key Takeaway) trước khi kết thúc buổi học; xây dựng bộ xử lý gián đoạn phiên học (Interruption Handler) cho phép tạm dừng an toàn và hoàn trả các task chưa hoàn thành về danh sách chờ mà không gây mất mát dữ liệu phiên. |
| **7.3** | Rolling-Horizon Overdue Recovery, Taskiq scheduler & quy tắc không tự dời Official Schedule [FR-ADAPT-001..003, FR-SCHEDULE-001; UC-12, UC-23..25; ADR-004, ADR-009, ADR-010] | Vũ Toàn Thắng | Hoàn thành | Thiết lập tiến trình quét nền tự động định kỳ (Taskiq Scheduler) để phát hiện bài học quá hạn (Rolling-Horizon Overdue Detection); đảm bảo quy tắc kiến trúc bắt buộc: task quá hạn chỉ được gắn cờ cảnh báo (`FLAGGED_OVERDUE`) và gửi đề xuất dời lịch dạng nháp, tuyệt đối không tự ý dời `scheduled_date` trong `OfficialSchedule` khi chưa có hành động `Apply` từ người học. |

#### B. Nhóm tính năng bổ trợ & Triển khai sớm (Accomplishments Ahead of Schedule):

| ID | Công việc / Hạng mục | Người phụ trách | Kết quả | Ghi chú chi tiết |
| :---: | :--- | :---: | :---: | :--- |
| **6.3+** | Tái thiết kế Roadmap Creation Wizard UI & Roadmap Hub [FR-PLAN-002..005; UC-08, UC-12] | Vũ Toàn Thắng & Phan Đình Duẩn | Hoàn thành | Nâng cấp toàn diện giao diện tạo lộ trình học tập với layout 7/5 chuẩn UX/UI; tích hợp hộp thoại kiểm tra điều kiện tiên quyết thời gian rảnh (`prerequisite availability check`) trước khi sinh lộ trình; hỗ trợ đính kèm tài liệu học tập (`knowledge attachments`) với thẻ ngữ cảnh an toàn `<untrusted_knowledge_context>`; làm mới bộ nhận diện thương hiệu FocusFlow. |
| **8.1\*** | Triển khai sớm Dashboard Học tập & Báo cáo tổng quan [FR-SESSION-001, FR-REPORT-001; UC-13, UC-19; ADR-003, ADR-009, ADR-010] | Phan Đình Duẩn | Triển khai sớm | Xây dựng màn hình Dashboard tổng quan (`Today Focus View`), tích hợp các widget theo dõi tiến độ tuần, thẻ chỉ số định lượng, và hiện thực use case `dashboard_summary` cùng API endpoint tương ứng tại backend. |
| **5.4 / 8.3\*** | Tách trang Hồ sơ người học (Profile) & Tái cấu trúc Cài đặt 4 tab (Settings) [FR-AUTH-004, FR-PROFILE-002, FR-QUOTA-001; UC-04..06, UC-26..28] | Phan Đình Duẩn & Vũ Toàn Thắng | Hoàn thành sớm | Tách riêng trang Hồ sơ học tập (`Learner Profile`) theo phong cách editorial trực quan; tái cấu trúc hệ thống Cài đặt thành 4 tab chuyên sâu (Chung, Lịch học, Quota AI, Tài khoản) với hệ thống định tuyến URL sâu (Deep Routing); hoàn thiện các API backend về thông tin tài khoản, hạn ngạch AI và đồng bộ token bảo mật chống rò rỉ dữ liệu chéo tài khoản. |
| **7.5\*** | Chuẩn bị nền tảng Đồng bộ Lịch ngoại vi (Google Calendar Sync & WebCal) [FR-CALENDAR-001..003; UC-17, UC-18] | Phan Đình Duẩn | Triển khai sớm | Tích hợp luồng xác thực OAuth cho Google Calendar, định nghĩa hợp đồng API `calendar auth return_to` và hoàn thiện sơ bộ adapter đồng bộ lịch ngoại vi với cơ chế phòng chống tấn công SSRF. |

---

### 3. KẾ HOẠCH THỰC HIỆN KỲ TỚI (PLANNED ACTIVITIES)

Danh sách các công việc dự kiến triển khai trong kỳ tiếp theo (Tuần 12: từ 13/11/2026 đến 19/11/2026) — Tập trung hoàn thiện cơ chế thích ứng lịch học nâng cao, đồng bộ lịch ngoại vi và phân hệ báo cáo định lượng:

| ID | Công việc dự kiến | Người phụ trách | Deadline | Mức độ ưu tiên |
| :---: | :--- | :---: | :---: | :---: |
| **7.4** | **Pause Roadmap, Domino Shift & Reschedule Budget:** Hiện thực tính năng Tạm dừng lộ trình (`Pause Roadmap`), cơ chế dời tịnh tiến thông minh toàn bộ bài học tiếp theo (`Domino Shift`), tự động thích ứng khối lượng học (`Adaptive Workload`) và kiểm soát ngân sách dời lịch hàng tuần (`Weekly Reschedule Budget`). | Vũ Toàn Thắng | 16/11/2026 | High |
| **7.5** | **WebCal Subscription Feed & Google Calendar Sync:** Hoàn tất feed xuất lịch chuẩn ICS/WebCal có chữ ký xác thực HMAC-SHA256 một chiều; hoàn thiện đồng bộ Free/Busy 2 chiều với Google Calendar; rà soát bộ lọc SSRF guard cho các URL lịch ngoài. | Phan Đình Duẩn | 19/11/2026 | High |
| **8.1** | **Hoàn thiện Module Báo cáo định lượng & Today Focus View:** Kết nối dữ liệu phiên học thực tế vào Dashboard tổng quan; hoàn thiện các biểu đồ trực quan hóa tiến độ hoàn thành mục tiêu, phân tích thời gian tập trung và tỷ lệ bám sát lịch học. | Phan Đình Duẩn | 17/11/2026 | High |
| **8.2** | **Khởi động AI Review & Weekly Reflection:** Xây dựng luồng tổng kết tuần với AI (`Weekly Reflection`), trích xuất bộ nhớ người học có cấu trúc (`Structured Learner Memory`), đánh giá mức độ thuần thục kỹ năng (`Skill Mastery & Prove Mode`) theo khung SRL Zimmerman. | Vũ Toàn Thắng | 21/11/2026 | Medium |

---

### 4. QUẢN LÝ VẤN ĐỀ & RỦI RO (ISSUES & RISKS)

Theo dõi chặt chẽ các vấn đề đã xử lý và các rủi ro kỹ thuật trong giai đoạn tích hợp nâng cao:

| Loại (Type) | Mô tả vấn đề / Rủi ro | Mức độ tác động | Kế hoạch giải quyết (Action Plan) | Người xử lý | Trạng thái |
| :---: | :--- | :---: | :--- | :---: | :---: |
| **Issue** | Sự không nhất quán giữa kế hoạch Tuần 9 và WBS baseline đã dẫn đến cảnh báo tiến độ ở Tuần 10. | Cao | Đã chuẩn hóa toàn bộ kế hoạch trong Tuần 10; Tuần 11 đã tập trung dứt điểm 100% các hạng mục 7.1, 7.2, 7.3 đúng hạn ngày 12/11/2026 và cập nhật đồng bộ file WBS Gantt. | Vũ Toàn Thắng & Phan Đình Duẩn | **Closed** |
| **Issue** | Nguy cơ rò rỉ token truy cập giữa các phiên đăng nhập khác nhau trên cùng một trình duyệt. | Cao | Đã sửa đổi cơ chế đồng bộ token tại sự kiện đăng nhập, làm sạch toàn bộ state cũ và kiểm tra quyền sở hữu tài nguyên IDOR nghiêm ngặt. | Phan Đình Duẩn | **Closed** |
| **Risk** | Tiến trình chạy ngầm (Taskiq Worker) có thể tự ý ghi đè thay đổi vào `OfficialSchedule` ngoài sự kiểm soát của người học. | Cao | Thiết lập ràng buộc kiến trúc Strict Apply: Taskiq chỉ gắn cờ `FLAGGED_OVERDUE` hoặc sinh bản nháp đề xuất (`ScheduleProposal(DRAFT)`); chỉ thao tác `Apply` của người học mới được ghi vào `OfficialSchedule`. | Vũ Toàn Thắng | **Controlled** |
| **Risk** | Rủi ro tấn công SSRF và rò rỉ token khi kết nối đồng bộ lịch với Google Calendar và các nguồn WebCal bên ngoài (7.5). | Cao | Áp dụng kiểm tra SSRF guard chặn toàn bộ dải IP nội bộ/metadata cloud; mã hóa đối xứng token Google Calendar bằng Fernet trong CSDL; dùng hàm băm HMAC-SHA256 một chiều cho URL WebCal. | Phan Đình Duẩn & Vũ Toàn Thắng | **Open** |
| **Risk** | Tính phức tạp của thuật toán Domino Shift (7.4) khi tịnh tiến lịch có thể vi phạm khung giờ rảnh (Availability Mode A/B) của người học. | Trung bình | Thiết kế thuật toán tịnh tiến dựa trên ma trận thời gian rảnh có sẵn; viết bộ unit test kiểm thử toàn diện các trường hợp biên (vượt tuần, chạm ngày nghỉ, chạm ngưỡng Reschedule Budget) trước khi tích hợp UI. | Vũ Toàn Thắng | **Open** |

---

### 5. CÁC MỐC QUAN TRỌNG SẮP TỚI (UPCOMING MILESTONES)

Theo dõi các mốc bàn giao chính (Deliverables) đối chiếu với tiến độ kế hoạch tổng thể:

| Mốc sự kiện (Milestone) | Ngày theo kế hoạch | Ngày thực tế / Dự kiến | Trạng thái |
| :--- | :---: | :---: | :---: |
| **Hoàn thành Thiết kế Kiến trúc & Database Diagram (Milestone 2)** | 08/10/2026 | 08/10/2026 | Completed |
| **Hoàn thành Sprint 1: Nền tảng, Xác thực & Cấu hình thời gian rảnh (Milestone 2.5)** | 22/10/2026 | 22/10/2026 | Completed |
| **Đóng Sprint 2: AI Planning & Approval Gate (bao gồm 6.3)** | 30/10/2026 | 30/10/2026 | Completed |
| **Hoàn thành Lát cắt lõi Sprint 3: 7.1–7.3 (Study Workspace & Overdue Recovery)** | 12/11/2026 | 12/11/2026 | **Completed** |
| **Hoàn thành Toàn diện Phase 7 & Phase 8: Bộ chức năng cốt lõi MVP & Tích hợp AI (Milestone 3)** | 21/11/2026 | 21/11/2026 | **On-track** |
| **Hoàn thành Phase 9: Kiểm thử phần mềm & Đo lường NFRs (Milestone 3.5)** | 26/11/2026 | 26/11/2026 | Planned |
| **Hoàn thành Thử nghiệm UAT & Triển khai Staging (Milestone 4)** | 26/11/2026 | 26/11/2026 | Planned |
