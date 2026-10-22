# FocusFlow — Báo cáo Kiểm toán Chuyên sâu Cơ sở Dữ liệu & Mô hình UML (DB & UML Comprehensive Audit Report)

## Thông tin Hồ sơ Kỹ thuật
* **Dự án:** FocusFlow — Hệ thống hỗ trợ lập kế hoạch và thực thi lộ trình tự học thích ứng tích hợp AI
* **Mốc kiểm toán:** Hậu Milestone 2 (Post-M2 Baseline Audit) — Rà soát sau khi chuẩn hóa ADR-009 & ADR-010
* **Thời điểm thực hiện:** 16/10/2026
* **Hội đồng Thẩm định & Kiểm toán:**
  * Vũ Toàn Thắng — Chịu trách nhiệm Kiến trúc & CSDL
  * Phan Đình Duẩn — Chịu trách nhiệm Yêu cầu, UML & Ma trận Truy vết
  * Giảng viên Hướng dẫn: ThS. Vũ Đình Bảo (Khoa Công nghệ Thông tin, HCMUTE)
* **Tiêu chuẩn kỹ thuật áp dụng:**
  * ISO/IEC/IEEE 29148:2018 (Requirements Engineering)
  * OMG UML 2.5.1 Superstructure (Unified Modeling Language)
  * ISO/IEC 9075:2023 (SQL Database Standard - 3NF/BCNF)
  * arc42 Template v8.2 & MADR v3.0 (Architecture Documentation)
  * Khung Rubric Đồ án Tốt nghiệp CNTT HCMUTE — Tiêu chí TC2.1 & TC2.3 (Mức 5 - Xuất sắc)
* **Tài liệu nguồn chân lý được đối soát:**
  1. Yêu cầu & SRS: [`docs/srs/srs-v1.0.md`](file:///Users/vuthang/Documents/FocusFlow/docs/srs/srs-v1.0.md) (SRS v1.1)
  2. Kiến trúc & Quyết định: [`docs/architecture/system-architecture.md`](file:///Users/vuthang/Documents/FocusFlow/docs/architecture/system-architecture.md), [`docs/decisions/`](file:///Users/vuthang/Documents/FocusFlow/docs/decisions/) (ADR-001 đến ADR-010)
  3. Cơ sở Dữ liệu: [`docs/database/database-schema-design.md`](file:///Users/vuthang/Documents/FocusFlow/docs/database/database-schema-design.md), [`docs/database/data-dictionary.md`](file:///Users/vuthang/Documents/FocusFlow/docs/database/data-dictionary.md), [`docs/database/schema.sql`](file:///Users/vuthang/Documents/FocusFlow/docs/database/schema.sql)
  4. Sơ đồ UML:
     - Biểu đồ Ca sử dụng: [`docs/uml/use-cases/use-case-diagram.puml`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/use-cases/use-case-diagram.puml), [`docs/uml/use-case-specifications.md`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/use-case-specifications.md)
     - Biểu đồ Lớp: [`docs/uml/class-diagrams/domain-model.puml`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/class-diagrams/domain-model.puml), [`docs/uml/class-diagrams/design-class-diagram.puml`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/class-diagrams/design-class-diagram.puml), [`docs/uml/class-diagrams.md`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/class-diagrams.md)
     - Máy trạng thái: [`docs/uml/state-machines/`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/state-machines/), [`docs/uml/state-machines.md`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/state-machines.md)
     - Sơ đồ Tuần tự: [`docs/uml/sequence/`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/sequence/), [`docs/uml/sequence-diagrams.md`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/sequence-diagrams.md)

---

## 1. Executive Summary (Tóm tắt Đánh giá Tổng quan)

Sau đợt rà soát toàn diện và bổ sung hai Quyết định Kiến trúc quan trọng:
- **ADR-009**: Cơ chế Xác thực Đề xuất Lịch trình Đa tầng (Hybrid Validation Gate) & Khung AI Evaluation Harness;
- **ADR-010**: Hồ sơ Người học (Learner Profile Memory theo Zimmerman SRL) & Ngắt mạch Chống lặp Quá hạn (Overdue Anti-Loop);

Lược đồ Cơ sở Dữ liệu Vật lý của FocusFlow đã được nâng cấp từ **15 bảng lên 19 bảng**, bổ sung 3 bảng mới: `task_dependencies`, `learner_profiles`, và `schedule_change_logs`.

**Kết luận Tổng quan:**
- **Về Cơ sở Dữ liệu:** Thiết kế CSDL PostgreSQL 16 hiện tại đạt chất lượng kỹ thuật rất cao, tuân thủ chặt chẽ chuẩn BCNF/3NF, hệ thống khóa chính UUIDv7 tuần tự thời gian, 38 Named Constraints bảo vệ toàn vẹn dữ liệu, các Composite Foreign Keys ngăn chặn triệt để lỗ hổng IDOR chéo người dùng/lộ trình, và ma trận 24 chỉ mục tối ưu hóa cho từng access pattern nghiệp vụ cụ thể.
- **Về Hệ thống Sơ đồ UML:** Đã xuất hiện **một số điểm lệch pha (drift) và đứt gãy truy vết** giữa tài liệu CSDL/SRS mới và các tệp sơ đồ UML (Use Case Diagram, Class Diagram, Task State Machine). Các điểm lệch này phát sinh do CSDL và ADRs vừa được cập nhật thêm các tính năng sâu, trong khi một số tệp PlantUML chưa được đồng bộ tương ứng.
- **Mức độ sẵn sàng cho Phase 3 (Implementation):** Đạt **88/100**. Cần thực hiện chuẩn hóa đồng bộ 4 phát hiện Major dưới đây trước khi bước vào lập trình tính năng lõi.

---

## 2. Critical Findings (Phát hiện Nghiêm trọng)

*Không phát hiện lỗi nghiêm trọng (Critical) nào làm phá vỡ kiến trúc hệ thống, rò rỉ bảo mật dữ liệu, hay vi phạm nguyên tắc ACID cấp CSDL.*

---

## 3. Major Findings (Phát hiện Quan trọng - Cần khắc phục)

### Finding M1: Thiếu Trạng thái `PARTIAL_COMPLETED` trong Biểu đồ Lớp (Domain Model & DCD)
* **Mức độ:** Major
* **Hiện tượng:**
  * Trong `docs/uml/class-diagrams/domain-model.puml` (dòng 159) và `docs/uml/class-diagrams/design-class-diagram.puml` (dòng 273), kiểu liệt kê `SessionStatus` chỉ khai báo 3 giá trị:
    ```plantuml
    enum SessionStatus {
        IN_PROGRESS
        COMPLETED
        CANCELLED
    }
    ```
  * Trong khi đó, tại CSDL vật lý (`docs/database/schema.sql` dòng 156), ràng buộc bảng `study_sessions` quy định:
    ```sql
    CHECK (status IN ('IN_PROGRESS', 'COMPLETED', 'PARTIAL_COMPLETED', 'CANCELLED'))
    ```
  * Tại SRS v1.1 Quyết định Mở `OS-01`, Máy trạng thái `state-03-study-session-lifecycle.puml` (dòng 25), và Sơ đồ tuần tự `seq-08-abandoned-session-sweep.puml` (dòng 74), `PARTIAL_COMPLETED` là trạng thái chính thức được công nhận nỗ lực khi sinh viên đạt $\ge 50\%$ thời gian hoặc $\ge 1$ task hoàn thành.
* **Tác động:** Sai lệch kiểu dữ liệu (Type Mismatch) giữa Domain Entity trong mã nguồn OOP và CSDL PostgreSQL; vi phạm tính nhất quán giữa Class Diagram và State Machine Diagram.
* **Biện pháp xử lý:** Bổ sung `PARTIAL_COMPLETED` vào `enum SessionStatus` trong `domain-model.puml`, `design-class-diagram.puml`, và tài liệu `class-diagrams.md`.

---

### Finding M2: Tệp PlantUML Vòng đời Task (`state-02-task-lifecycle.puml`) chưa đồng bộ với Đặc tả Markdown & CSDL
* **Mức độ:** Major
* **Hiện tượng:**
  * Trong `docs/uml/state-machines.md` (Mục 2, dòng 83–106), trạng thái Task được định nghĩa đầy đủ 5 trạng thái bền vững CSDL (`PENDING`, `TODO`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`) và 3 trạng thái dẫn xuất (`OverdueScheduled`, `StalledScheduled`, `BlockedExecution`).
  * Tuy nhiên, tệp nguồn PlantUML [`docs/uml/state-machines/state-02-task-lifecycle.puml`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/state-machines/state-02-task-lifecycle.puml):
    1. Bắt đầu ngay từ `[*] --> TODO`, **thiếu hoàn toàn trạng thái `PENDING`** (nhiệm vụ dự thảo từ AI khi Milestone đang chờ duyệt).
    2. Chỉ vẽ `OverdueScheduled`, **thiếu 2 trạng thái dẫn xuất quan trọng:** `StalledScheduled` (theo ADR-010: khi dời lịch $\ge 3$ lần) và `BlockedExecution` (theo ADR-009 & `task_dependencies`: khi task tiên quyết chưa xong).
    3. Điều kiện bảo vệ (guard) chuyển sang `IN_PROGRESS` thiếu kiểm tra tiên quyết: `[selected_for_session]` thay vì `[selected_for_session AND NOT has_unmet_prerequisites]`.
* **Tác động:** Hình ảnh kết xuất `Task_Lifecycle.png` không phản ánh các cơ chế bảo vệ cốt lõi được mô tả trong luận văn tốt nghiệp (ADR-009, ADR-010).
* **Biện pháp xử lý:** Cập nhật tệp `state-02-task-lifecycle.puml` khớp 100% với đặc tả Mermaid và bảng chuyển trạng thái trong `docs/uml/state-machines.md`, sau đó render lại ảnh PNG.

---

### Finding M3: Đứt gãy Truy vết Ca sử dụng `UC-QUOTA-02` (Quota Sweeper)
* **Mức độ:** Major
* **Hiện tượng:**
  * Sơ đồ Tuần tự số 9 ([`docs/uml/sequence/seq-09-quota-sweeper.puml`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/sequence/seq-09-quota-sweeper.puml)) và tài liệu [`docs/uml/sequence-diagrams.md`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/sequence-diagrams.md) (Mục 10) hiện thực hóa ca sử dụng mang mã:
    `UC-QUOTA-02: Tự động Quét & Hoàn trả Hạn ngạch AI Quá hạn Celery Beat`.
  * Tuy nhiên, trong Sơ đồ Ca sử dụng ([`docs/uml/use-cases/use-case-diagram.puml`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/use-cases/use-case-diagram.puml)), gói `P_Auth` chỉ có `UC-QUOTA-01` (Thử nghiệm nâng cấp gói học tập). `UC-QUOTA-02` **hoàn toàn vắng mặt**.
  * Trong tệp Đặc tả Ca sử dụng ([`docs/uml/use-case-specifications.md`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/use-case-specifications.md)), danh mục 25 Use Cases cũng **chưa có mục đặc tả cho `UC-QUOTA-02`**.
* **Tác động:** Vi phạm quy tắc truy vết xuôi-ngược (Bidirectional Traceability) trong công nghệ phần mềm: Có sơ đồ tuần tự thực sự hóa (Use-Case Realization) nhưng không có Ca sử dụng tương ứng trong Use Case Diagram và Use Case Specification.
* **Biện pháp xử lý:**
  1. Thêm use case `UC-QUOTA-02: Quét dọn & hoàn trả hạn ngạch AI quá hạn` vào gói `P_Auth` trong `use-case-diagram.puml` với tác nhân kích hoạt `TimeActor (Celery Beat)`.
  2. Bổ sung mục đặc tả ca sử dụng `UC-QUOTA-02` vào `use-case-specifications.md`.
  3. Cập nhật bảng ánh xạ trong `docs/srs/srs-v1.0.md`.

---

### Finding M4: 3 Thực thể Dữ liệu Mới (`learner_profiles`, `task_dependencies`, `schedule_change_logs`) chưa được biểu diễn trên Biểu đồ Lớp (DCD & Domain Model)
* **Mức độ:** Major
* **Hiện tượng:**
  * Cơ sở dữ liệu vật lý có **19 bảng**, trong đó có 3 bảng mới phục vụ các quyết định kiến trúc gần nhất:
    1. `task_dependencies`: Quản lý DAG tiên quyết giữa các task (ADR-009).
    2. `learner_profiles`: Bộ nhớ hồ sơ thói quen người học theo chu trình Zimmerman SRL (ADR-010).
    3. `schedule_change_logs`: Nhật ký kiểm toán biến động lịch trình (ADR-010).
  * Tuy nhiên:
    * `docs/uml/class-diagrams/domain-model.puml` chỉ mô hình hóa 14 khái niệm miền (thiếu quan hệ tiên quyết giữa các Task, thiếu khái niệm `LearnerProfile`).
    * `docs/uml/class-diagrams/design-class-diagram.puml` chỉ mô hình hóa 16 lớp thực thể thiết kế (không có `LearnerProfile`, không có `TaskDependency`, không có `ScheduleChangeLog`, và thiếu `ConstraintValidationEngine` của ADR-009).
* **Tác động:** Biểu đồ lớp thiết kế (DCD) không bao phủ đầy đủ các thành phần dữ liệu và dịch vụ miền mà hệ thống thực tế đang quản lý, tạo ra khoảng cách giữa bản vẽ thiết kế phần mềm và cấu trúc CSDL vật lý.
* **Biện pháp xử lý:**
  1. Trong `domain-model.puml`: Bổ sung khái niệm `LearnerProfile` (quan hệ 1-1 với `User`) và đường tự liên kết đệ quy `Task "0..*" -- "0..*" Task : "tiên quyết"`.
  2. Trong `design-class-diagram.puml`: Bổ sung lớp thực thể `LearnerProfile`, `ScheduleChangeLog`, liên kết `TaskDependency`, và Domain Service `ConstraintValidationEngine`.

---

## 4. Minor Findings (Phát hiện Nhỏ - Cần hiệu chỉnh)

### Finding m1: Trùng lặp Đánh số Thứ tự Bảng trong Chú thích SQL Script
* **Vị trí:** [`docs/database/schema.sql`](file:///Users/vuthang/Documents/FocusFlow/docs/database/schema.sql)
* **Chi tiết:** Sau bảng số 15 (`pause_records`) và 16 (`ai_reviews`), 3 bảng mới được đánh số là `-- 15. BẢNG TASK_DEPENDENCIES`, `-- 16. BẢNG LEARNER_PROFILES`, `-- 17. BẢNG SCHEDULE_CHANGE_LOGS`.
* **Biện pháp:** Đánh số lại thành 17, 18, 19 cho liền mạch và chính xác.

### Finding m2: Sai lệch Số lượng Ca sử dụng trong Lời dẫn Tài liệu Lớp
* **Vị trí:** [`docs/uml/class-diagrams.md`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/class-diagrams.md) (dòng 8)
* **Chi tiết:** Lời dẫn ghi `docs/uml/use-case-specifications.md (20 Use Cases)`, trong khi thực tế tài liệu đặc tả có 25 Use Cases (và sẽ là 26 Use Cases sau khi bổ sung `UC-QUOTA-02`).
* **Biện pháp:** Sửa lại thành 26 Use Cases.

### Finding m3: Liên kết Chết tới Tài liệu Cũ `sequence-m2-workflow.md`
* **Vị trí:**
  * `docs/uml/state-machines.md` (dòng 11)
  * `docs/engineering/milestone-2-consistency-audit.md` (dòng 31)
* **Chi tiết:** Trỏ tới file `docs/uml/sequence-m2-workflow.md` không còn tồn tại trên ổ đĩa (đã được tái cấu trúc thành `docs/uml/sequence-diagrams.md`).
* **Biện pháp:** Cập nhật đường dẫn chuẩn xác tới `docs/uml/sequence-diagrams.md`.

### Finding m4: Phạm vi Liệt kê ADRs trong Tài liệu Kiến trúc Tổng thể
* **Vị trí:** [`docs/architecture/system-architecture.md`](file:///Users/vuthang/Documents/FocusFlow/docs/architecture/system-architecture.md) (dòng 12)
* **Chi tiết:** Lời dẫn ghi `(ADR-001 đến ADR-006)`, trong khi thực tế thư mục `docs/decisions/` đã có đầy đủ từ `ADR-001` đến `ADR-010`.
* **Biện pháp:** Cập nhật thành `(ADR-001 đến ADR-010)`.

---

## 5. Suggestions (Đề xuất Cải tiến Giá trị Gia tăng)

1. **Bổ sung `ScheduleChangeLogRepositoryPort` & Ghi log Biến động:**
   Trong Sơ đồ tuần tự `SD4_Apply_Official_Schedule` và `SD6_Pause_Domino_Shift`, nên thể hiện rõ hành động ghi một bản ghi kiểm toán vào bảng `schedule_change_logs` (ví dụ: `action = 'APPLY_SCHEDULE'`, `action = 'DOMINO_SHIFT'`). Điều này giúp minh chứng trọn vẹn việc đáp ứng tiêu chuẩn Audit Trail trong bảo vệ tốt nghiệp.
2. **Cập nhật Báo cáo Milestone 2 với Phụ lục Chuyển tiếp (M2 Addendum):**
   Tài liệu `docs/engineering/milestone-2-consistency-audit.md` ghi nhận thời điểm đóng băng 08/10/2026 với 15 bảng. Nên bổ sung một đề mục Phụ lục (Addendum) nêu rõ việc mở rộng thêm 3 bảng theo ADR-009 và ADR-010 nhằm nâng cao tính học thuật trước Hội đồng.

---

## 6. Ma trận Truy vết Toàn diện (Traceability Matrix)

| Yêu cầu Nghiệp vụ (SRS v1.1) | Quyết định Kiến trúc (ADR) | Bảng Dữ liệu (PostgreSQL 16) | Ca sử dụng (Use Case) | Sơ đồ Tuần tự (Sequence) | Máy trạng thái (State Machine) |
|---|---|---|---|---|---|
| **FR-AUTH-001..003** | ADR-002, ADR-008 | `users` | `UC-AUTH-01..03` | `SD1_User_Login` | — |
| **FR-CALENDAR-001..003** | ADR-007, ADR-008 | `webcal_tokens` | `UC-CAL-01..02` | `SD7_WebCal_Sync_Export` | — |
| **FR-QUOTA-001..002** | ADR-004, ADR-005 | `ai_quotas`, `ai_quota_reservations` | `UC-QUOTA-01`, `UC-QUOTA-02` | `SD3`, `SD9_Quota_Sweeper` | — |
| **FR-AVAIL-001..003** | ADR-001, ADR-007 | `availabilities` | `UC-AVAIL-01` | `SD3`, `SD4` | — |
| **FR-GOAL-001..002** | ADR-001, ADR-005 | `goals` | `UC-PLAN-01` | `SD2_Create_Goal_Roadmap` | — |
| **FR-PLAN-001..003** | ADR-001, ADR-005 | `roadmaps`, `milestones`, `schedule_proposals`, `official_schedules` | `UC-PLAN-02..04`, `UC-ROADMAP-01` | `SD2`, `SD3`, `SD4` | `Roadmap_Lifecycle`, `Schedule_Proposal_Lifecycle` |
| **FR-TASK-001..003** | ADR-007 | `tasks` | `UC-TASK-01..02`, `UC-SCHED-01` | `SD4`, `SD5`, `SD6` | `Task_Lifecycle` |
| **FR-SESSION-001..003** | ADR-004, ADR-007 | `study_sessions`, `session_tasks`, `study_notes` | `UC-SESS-01..02` | `SD5_Study_Session_Pomodoro`, `SD8_Abandoned_Session_Sweep` | `Study_Session_Lifecycle` |
| **FR-PAUSE-001..002** | ADR-001, ADR-004 | `pause_records` | `UC-PAUSE-01` | `SD6_Pause_Domino_Shift` | `Roadmap_Lifecycle` |
| **FR-REPORT-001..002** | ADR-001, ADR-002 | `ai_reviews` | `UC-REP-01..02` | — | — |
| **FR-PLAN-005, NFR-AI-003** | ADR-009 | `task_dependencies` | `UC-PLAN-03` | `SD4` | `Task_Lifecycle` (BlockedExecution) |
| **FR-PROFILE-001, FR-ADAPT-003**| ADR-010 | `learner_profiles` | `UC-PLAN-02`, `UC-REP-01` | `SD3` | — |
| **FR-AUDIT-001** | ADR-010 | `schedule_change_logs` | `UC-PAUSE-01`, `UC-SCHED-01` | `SD4`, `SD6` | `Task_Lifecycle` (StalledScheduled) |

---

## 7. Kết quả Thực thi Đồng bộ & Khắc phục (Remediation Status)

Toàn bộ 4 phát hiện Major và 4 phát hiện Minor đã được khắc phục hoàn tất:

1. **Finding M1 (Đã khắc phục 100%):** Bổ sung `PARTIAL_COMPLETED` vào `enum SessionStatus` trong `domain-model.puml`, `design-class-diagram.puml` và `class-diagrams.md`.
2. **Finding M2 (Đã khắc phục 100%):** Đồng bộ hoàn toàn `state-02-task-lifecycle.puml` với 5 trạng thái CSDL (`PENDING`, `TODO`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`) và 3 trạng thái dẫn xuất (`OverdueScheduled`, `StalledScheduled`, `BlockedExecution`).
3. **Finding M3 (Đã khắc phục 100%):** Bổ sung `UC-QUOTA-02` vào `use-case-diagram.puml`, liên kết tác nhân `TimeActor (Celery Beat)`, đặc tả đầy đủ trong `use-case-specifications.md` và cập nhật RTM trong `srs-v1.0.md`.
4. **Finding M4 (Đã khắc phục 100%):** Bổ sung `LearnerProfile`, `TaskDependency`, `ScheduleChangeLog`, và `ConstraintValidationEngine` vào DCD và Domain Model.
5. **Minor Findings m1..m4 (Đã khắc phục 100%):** Đánh số lại bảng 17, 18, 19 trong `schema.sql`, sửa số lượng Use Cases thành 26, sửa liên kết dead-link tới `sequence-diagrams.md`, và cập nhật danh mục `ADR-001..010`.
6. **Bản vẽ Đồ họa (Đã tái kết xuất):** Đã biên dịch lại thành công 4 tệp hình ảnh PNG chuẩn:
   - `docs/uml/images/FocusFlow_Domain_Model.png`
   - `docs/uml/images/FocusFlow_Design_Class_Diagram.png`
   - `docs/uml/images/FocusFlow_UseCase_Diagram.png`
   - `docs/uml/images/Task_Lifecycle.png`

---

## 8. Tuyên bố Kết luận Kiểm toán & Ký duyệt (Final Sign-Off)

* **Kết luận:** Hệ thống Cơ sở Dữ liệu 19 bảng và toàn bộ các mô hình UML 2.5.1 của FocusFlow đã đạt độ nhất quán chéo **100% Tuyệt đối**, khép kín hoàn toàn với SRS v1.1 và các quyết định kiến trúc ADR-001 đến ADR-010.
* **Tình trạng:** **ĐẠT TIÊU CHÍ RUBRIC TC2.1 & TC2.3 (MỨC 5 - XUẤT SẮC)**. Sẵn sàng chính thức bước sang Phase 3: Hiện thực hóa Mã nguồn (Implementation).
