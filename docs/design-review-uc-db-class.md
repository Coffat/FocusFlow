# BÁO CÁO RÀ SOÁT ĐỘC LẬP & CHUYÊN SÂU THIẾT KẾ HỆ THỐNG — FOCUSFLOW (v2.1)
## Use Case Analysis (`/usecase-analyst`) · Class Diagram Design (`/class-diagram-designer`) · Database Schema Mapping · 36 Findings & 09 Confirmed Decisions

| Thông tin Báo cáo | Chi tiết |
| :--- | :--- |
| **Dự án** | FocusFlow — Hệ thống lập kế hoạch và thực thi lộ trình tự học thích ứng tích hợp AI (Zimmerman SRL) |
| **Vai trò thực hiện** | Senior Business Analyst / Software Architect / Database Designer |
| **Kỹ năng chuyên sâu áp dụng** | Skill `/usecase-analyst` (Cockburn Size Test & UML 2.5 Use Cases), Skill `/class-diagram-designer` (IBM UML 2 Class Modeling & DDD Tactical Design), Chuẩn PostgreSQL 16 Relational/Temporal Integrity |
| **Chế độ rà soát** | `REVIEW-ONLY` — Độc lập 100%, dựa trên minh chứng trực tiếp (`E1`/`E2`), đối chiếu chuẩn lý thuyết quốc tế (IBM Rhapsody UML 2.5.1, IBM Enterprise DDD + Hexagonal GenAI Governance, PostgreSQL 16) |
| **Ngày cập nhật** | 04/11/2026 (Bản v2.1 — Tích hợp rà soát chuyên sâu theo 2 Skill & 09 Quyết định Thiết kế đã chốt qua `/grill-me`) |
| **Phạm vi** | Toàn bộ 28 Use Cases (`UC-01..UC-28`), 28 Bảng PostgreSQL 16 (`schema.sql` v3.1 & các biến thể), 69 Classifiers (`class-diagram.puml` v7.0 & `class-diagrams.md`), đối chiếu với `SRS v1.3`, `ADR-001..010` và ORM/Alembic thực tế |

---

## 1. Executive Summary

### 1.1. Kết luận tổng thể
Qua 3 vòng kiểm toán độc lập:
1. **Vòng 1 — Kiểm kê định lượng & đối chiếu chéo 3 artifact**: Xác lập danh mục 28 Use Cases, 28 bảng PostgreSQL 16 (`10/7/5/4/2`), 69 classifiers và phát hiện sự phân mảnh tài liệu sau đợt mở rộng hệ thống.
2. **Vòng 2 — Rà soát khắt khe theo lý thuyết quốc tế**: Đối chiếu với chuẩn **IBM Engineering Systems Design Rhapsody UML 2.5.1**, **IBM Enterprise DDD + Hexagonal GenAI Governance**, và **PostgreSQL 16 Temporal Integrity**, phát hiện các lỗ hổng ẩn trong vòng đời khoảng thời gian mở (`pause_records`), neo ngữ cảnh ghi chú (`study_notes`), và truy vết retry/quota (`ai_usage_logs`).
3. **Vòng 3 — Đánh giá chuyên sâu theo skill `/usecase-analyst` & `/class-diagram-designer`**:
   - Theo `/usecase-analyst`: Khẳng định **số lượng 28 Use Cases hiện tại là hoàn toàn hợp lý về mặt độ hạt (Cockburn Size Test)**: gồm 24 User/Admin-Goal, 3 System-Goal cho Sweeper/Scheduler, và 1 Subfunction cho Cổng kiểm định 3 tầng dùng chung (`UC-12`).
   - Theo `/class-diagram-designer`: Khẳng định mô hình hiện tại là **Specification/Design Model** tuân thủ chặt chẽ ranh giới DDD Bounded Context (25 đường `..> <<ref>>` qua định danh ID).
   - Rà soát ánh xạ Class Diagram $\leftrightarrow$ Database: Phát hiện thêm điểm bất cập khi chẻ đôi mảng JSONB của `RecallExchange` trên bảng `milestone_proofs` (`[DB-11]`), thiếu trường kiểm soát phiên bản `version_number` trên `official_schedules` (`[DB-12]`/`[CLS-08]`), và lệch tên thuộc tính/thiếu `isMandatory` trên `TaskDependency` (`[CLS-07]`).

Tổng cộng có **36 Findings độc lập (đã gộp theo root cause)**, trong đó có **05 Blocker** và **10 Critical**. Toàn bộ **09 quyết định thiết kế then chốt (`DEC-01..DEC-09`)** đã được thống nhất với Stakeholder qua chuỗi phỏng vấn `/grill-me` (chi tiết tại Mục 10) để sẵn sàng chuyển sang pha Fix.

### 1.2. Thống kê số lượng Finding theo Severity & Loại (Bản v2.1)

| Mức độ (Severity) | Defect | Risk | Suggestion | Question (Đã chốt) | Tổng cộng | Mã Finding |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Blocker** | 5 | 0 | 0 | 0 | **5** | `UC-01`, `UC-02`, `DB-01`, `DB-02`, `X-01` |
| **Critical** | 10 | 0 | 0 | 0 | **10** | `UC-03`, `DB-03`, `DB-04`, `DB-08`, `DB-09`, `CLS-01`, `CLS-05`, `CLS-06`, `X-02`, `X-03` |
| **Major** | 15 | 1 | 0 | 0 | **16** | `UC-04`, `UC-05`, `UC-07`, `UC-08`, `DB-05`, `DB-06`, `DB-10`, `DB-11`, `DB-12`, `CLS-02`, `CLS-03`, `CLS-07`, `CLS-08`, `X-04`, `X-05`, `X-06`, `X-10` |
| **Minor** | 2 | 0 | 2 | 0 | **4** | `UC-06`, `DB-07`, `CLS-04`, `X-08` |
| **Info** | 0 | 0 | 1 | 0 | **1** | `X-09` |
| **Tổng cộng** | **32** | **1** | **3** | **0 (Đã chốt 9/9)** | **36** | **36 Findings độc lập (E1: 35, E2: 1)** |

### 1.3. Top 10 Vấn đề Nghiêm trọng Nhất (Blocker & Critical)
1. **`[UC-01]` (Blocker)**: 16/28 Use Cases (`UC-13..UC-28`) trong `use-case-specifications.md` bị cắt cụt cấu trúc đặc tả; 8 UC cuối chỉ có duy nhất `Luồng chính`, mất sạch `Exception Flows`, `Business Rules`, `Inputs/Outputs`.
2. **`[UC-02]` (Blocker)**: Mâu thuẫn trực diện ngay trong `SRS v1.3` (§2.5 Out-of-Scope vs §7.1 `FR-AUTH-001/002`) và `UC-01/UC-02` về Email OTP, Quên mật khẩu OTP và Google OAuth2 SSO.
3. **`[DB-01]` (Blocker)**: Bảng `payment_transactions` trong `schema.sql` thiếu cột `expires_at` và sai constraint trạng thái (`'REFUNDED'` thay vì `'EXPIRED'`), làm gãy trực tiếp `UC-04` và `UC-06`.
4. **`[DB-02]` (Blocker)**: Lệch cấu trúc trên 9 bảng giữa `schema.sql` (292 cột, 46 FKs) với `schema.dbml` / `database-schema.puml` / `database-schema-design.md` (284 cột, 45 FKs) và lỗi copy-paste nguyên bảng `outbox_events` vào mục `2.28 processed_events` của `data-dictionary.md`.
5. **`[X-01]` (Blocker)**: Đứt gãy 4 chiều mô hình `LearningConcept` & `ConceptPrerequisite` giữa `schema.sql` (Global Knowledge Base), `class-diagram.puml` (`Roadmap *-- LearningConcept`), `class-diagrams.md` (§5.2.7 lưu tiến độ cá nhân) và `schema.dbml` (PK `UUID` + `roadmap_id`).
6. **`[DB-08]` (Critical)**: Bảng `pause_records` trong `schema.sql` ép `pause_end_date NOT NULL` và `CHECK (shifted_days = pause_end_date - pause_start_date + 1 > 0)` ngay lúc `INSERT`, khiến hệ thống không thể lưu trạng thái bắt đầu tạm dừng (`status = 'ACTIVE'`) khi người học chưa Resume, và cộng lệch `+1` ngày nếu Pause/Resume trong cùng ngày.
7. **`[DB-09]` (Critical)**: Bảng `study_notes` trong `schema.sql` thiếu `CHECK (session_id IS NOT NULL OR task_id IS NOT NULL)` (cho phép note mồ côi cả 2 đầu) và đặt `UNIQUE (session_id, note_type)` chặn việc ghi nhiều `SCRATCHPAD` hoặc ghi `TAKEAWAY` cho từng `task_id` trong phiên học nhiều bài (`session_tasks` N-N).
8. **`[CLS-05]` (Critical)**: Lệch cấu trúc thực thi Package 3 giữa `class-diagram.puml` và `schema.sql`: `StudySession` trong `.puml` có `timerMode` nhưng thiếu `roadmapId`, còn `study_sessions` trong `schema.sql` có `roadmap_id` nhưng thiếu cột `timer_mode`; `Task` trong `.puml` khai báo `actualMinutes` và `isOverdue` như cột vật lý và thiếu `scheduledEnd`; `SessionTask` thiếu `actualMinutes`.
9. **`[CLS-06]` (Critical)**: Lệch cấu trúc đánh giá Package 4: `RecallExchange` trong `class-diagram.puml` thiếu thuộc tính `selfConfidence` (làm mất đầu vào tính `avgSelfConfidence` và `calibrationGap` của Prove Mode `UC-20`); `ScheduleChangeLog` mô hình hóa theo 1 task thay vì cả đợt dời lịch; `AIReview` thiếu `milestoneId` và `modelUsed`.
10. **`[X-02]` & `[X-03]` (Critical)**: Lệch toàn bộ thuộc tính của `LearnerProfile` (thiếu `resetToColdStart()`, lệch default 25p vs 45p) và mâu thuẫn kiến trúc tại `ADR-004` Dòng 67 (ghi AI Reschedule bỏ qua Cổng Kiểm duyệt 3 Tầng trái ngược với `SRS v1.3`, `UC-23`, `ADR-009/010`).

---

## 2. Rà Soát Chuyên Sâu theo 2 Skill Chuyên Ngành & Chuẩn Lý Thuyết

### 2.1. Đánh giá Use Case theo Skill `/usecase-analyst`
Dưới góc nhìn của Senior Business Analyst áp dụng chuẩn Alistair Cockburn và IEEE 29148:
1. **Độ hạt Use Case (Size Test)**:
   - **24 User-Goal / Admin-Goal Level Use Cases**: Đạt chuẩn Sea-Level. Mỗi Use Case hoàn thành trong 1 phiên làm việc liên tục, mang lại giá trị trọn vẹn (Actor có thể "xong việc" sau đó). Không tạo Use Case cho các thao tác UI đơn lẻ ("Nhập form", "Bấm nút") và không gộp thô bạo toàn bộ module thành một Use Case CRUD duy nhất.
   - **03 System-Goal Level Use Cases** (`UC-06`, `UC-16`, `UC-25`): Tách riêng rất hợp lý vì do tác nhân thời gian `System Scheduler` (`ACT-03`) kích hoạt định kỳ, có tiền điều kiện, luồng xử lý và hậu điều kiện hệ thống riêng biệt (thu hồi quota, chốt phiên gián đoạn, quét quá hạn/ngủ đông).
   - **01 Subfunction Level Use Case** (`UC-12: Kiểm định tính hợp lệ của lịch học`): Đây là ca sử dụng mức dưới (Fish-Level). Không có Actor nối trực tiếp mà đóng vai trò dịch vụ dùng chung được 7 Use Cases khác nhau (`UC-08, 09, 11, 13, 22, 23, 24`) gọi bắt buộc thông qua quan hệ `<<include>>`. Việc tách `UC-12` là hoàn toàn đúng đắn để tái sử dụng đặc tả logic Cổng kiểm định lai 3 tầng.
2. **Ranh giới Actor & Quan hệ**:
   - Ranh giới hệ thống (System boundary) được bao bọc chuẩn xác: 3 Actor người (`Learner`, `Admin`, `AuthUser`) và 4 Actor hệ thống ngoài (`Scheduler`, `LLM`, `Google Calendar`, `Payment Gateway`, `Email Service`) đều nằm ngoài System boundary.
   - `<<include>>` (7 đường) và `<<extend>>` (4 đường) đều hướng đúng chiều mũi tên theo chuẩn OMG UML 2.5.1.
   - **Điểm khuyết thiếu**: Các Base Use Case (`UC-14`, `UC-19`, `UC-23`) chưa khai báo ngăn `Extension Points` tường minh (`[UC-07]`); và `UC-07` thiếu bước khởi tạo/liên kết thực thể `learning_concepts` (`[UC-08]`).

### 2.2. Đánh giá Class Diagram theo Skill `/class-diagram-designer`
Dưới góc nhìn của Senior Software Architect áp dụng chuẩn IBM Developer UML 2 Class Diagram và DDD Tactical Patterns:
1. **Góc nhìn mô hình hóa (Perspective)**:
   - Mô hình [class-diagram.puml](file:///Users/vuthang/Documents/FocusFlow/docs/uml/class-diagrams/class-diagram.puml) được xây dựng ở mức **Specification / Design Model**: định rõ tên lớp, thuộc tính, kiểu dữ liệu chung, tầm vực (`-` private, `+` public), phương thức nghiệp vụ, không chứa getter/setter thuần túy.
   - Phân chia rõ ràng 69 Classifiers: **22 Entities**, **5 Value Objects**, **3 Association Classes**, **4 Domain Services** và **35 Enumerations**.
2. **Tính đóng gói & Phân tách Bounded Context**:
   - Tuyệt đối không có quan hệ kết dính cứng (Association/Composition) xuyên qua ranh giới giữa 4 package Bounded Context. Mọi tương tác xuyên context đều sử dụng đường phụ thuộc định danh `..> : <<ref>> <id>`, tuân thủ đúng DDD Aggregate Reference by Identity.
3. **Các điểm vi phạm UML 2 cần chuẩn hóa**:
   - **Bội số Composition**: `StudySession "1" *-- "0..*" StudyNote` sai vì `StudyNote` có thể tồn tại ngoài phiên học (`sessionId : UUID [0..1]`). Cần sửa thành `0..1` ở cả đầu `StudySession` và `Task` (`[CLS-02]`).
   - **Thuộc tính dẫn xuất**: `Task.actualMinutes` và `Task.isOverdue` phải có dấu gạch chéo `/` (`/actualMinutes`, `/isOverdue`).
   - **Lặp thuộc tính FK**: Xóa hoặc gắn nhãn `{fk}` cho các thuộc tính ID nội bộ trùng lặp với Association (`[CLS-04]`).
   - **Lệch cấu trúc thực thi/đánh giá**: Chuẩn hóa `StudySession`, `Task`, `SessionTask`, `RecallExchange`, `ScheduleChangeLog`, `AIReview` (`[CLS-05]`, `[CLS-06]`).

### 2.3. Đánh giá Ánh Xạ Class Diagram $\leftrightarrow$ Database Schema (3NF/BCNF Mapping)
1. **Mức độ tương thích tổng thể**:
   - 22 `<<entity>>` $\leftrightarrow$ 22 bảng thực thể CSDL (1-1).
   - 3 `<<associationClass>>` (`ConceptPrerequisite`, `TaskDependency`, `SessionTask`) $\leftrightarrow$ 3 bảng trung gian mang thuộc tính riêng của quan hệ.
   - 4 `<<domainService>>` là logic phi trạng thái, không cần bảng.
   - 2 bảng hạ tầng Outbox Pattern (`outbox_events`, `processed_events`) được đặt đúng ở tầng `shared_kernel`.
2. **Các điểm đứt gãy ánh xạ dữ liệu phát hiện qua rà soát**:
   - `[DB-11]` (Mới): `RecallExchange` trên Class Diagram là 1 Value Object chứa đủ bộ `(câu hỏi, câu trả lời, độ tự tin, điểm AI, lời phê)`, nhưng trong `schema.sql` bảng `milestone_proofs` lại chẻ đôi thành 2 mảng JSONB `recall_questions_payload` và `learner_answers_payload`. Nếu 2 mảng lệch index sẽ làm hỏng dữ liệu.
   - `[DB-12]` & `[CLS-08]` (Mới): `OfficialSchedule` trên Class Diagram có `versionNumber` và `strategy`, nhưng bảng `official_schedules` lại thiếu; ngược lại DB có `total_sessions`, `total_planned_minutes`, `activated_at` thì Class Diagram lại thiếu.
   - `[CLS-07]` (Mới): `TaskDependency` trên Class Diagram dùng tên `prerequisiteTaskId` / `dependentTaskId` và thiếu `isMandatory`, trong khi CSDL dùng `predecessor_id`, `successor_id` và `is_mandatory`.

---

## 3. Artifact Inventory (Kiểm kê Định lượng Thực tế)

### 3.1. Kiểm kê Cụm Use Case

| Hạng mục kiểm kê | `docs/srs/srs-v1.3.md` | `docs/uml/use-case-specifications.md` | `use-case-diagram.puml` + 5 `uc-mod-*.puml` | `.drawio` (`UC_Master` vs `UC_Module_01..05`) |
| :--- | :---: | :---: | :---: | :---: |
| **Actor cụ thể (`ACT-01..07`)** | **7** (`Learner`, `Admin`, `Scheduler`, `LLM`, `Google Calendar`, `Payment Gateway`, `Email Service`) | **7** (`ACT-01..07`) | **7** (3 `actor` + 4 `rectangle <<system>>`) | `UC_Master.drawio`: **6** (thiếu `ACT-07`)<br>`UC_Module_01..05.drawio`: **7** |
| **Actor trừu tượng (Abstract Actor)** | **1** (`Authenticated User`) | **1** (`Authenticated User`) | **1** (`AuthUser` — `Learner` & `Admin` kế thừa `--|>`) | **1** (`Authenticated User`) |
| **Tổng số Use Case chuẩn hóa** | **28** (`UC-01..UC-28`) | **28** (`UC-01..UC-28`) | **28** (Mod1: `6`, Mod2: `6`, Mod3: `6`+`UC-12`, Mod4: `7`+`UC-12`, Mod5: `3`) | `UC_Master.drawio` / `UC_Dia.drawio`: **19** (bản cũ)<br>`UC_Module_01..05.drawio`: **28** |
| **Số Heading chứa chuỗi `UC-` trong file `.md`** | — | **35** (`2` heading `##` mục lớn + `5` heading `###` tiêu đề phân hệ + `28` heading `### UC-01..UC-28`) | — | — |
| **Quan hệ `<<include>>`** | **7** (`UC-08, 09, 11, 13, 22, 23, 24` $\rightarrow$ `UC-12`) | **7** (`UC-08, 09, 11, 13, 22, 23, 24` $\rightarrow$ `UC-12`) | **7** | `UC_Master.drawio`: **1** (`UC-04 -> UC-05` cũ)<br>`UC_Module_01..05.drawio`: **7** |
| **Quan hệ `<<extend>>`** | **2** ghi ở Bảng 3.2 (`UC-15->14`, `UC-24->23`; sót `UC-20, 21 -> UC-19`) | **4** (`UC-15->UC-14`, `UC-20->UC-19`, `UC-21->UC-19`, `UC-24->UC-23`) | **4** (có `[condition]`, nhưng Base UC thiếu ngăn `Extension Points`) | `UC_Module_01..05.drawio`: **4** |
| **Main Success Scenarios** | 28 mô tả tóm tắt | **28** kịch bản chính (tổng **182 bước**) | — | — |
| **Alternative Flows** | — | **36** nhánh (chỉ có ở **19/28** UC; **9/28** UC thiếu hẳn) | — | — |
| **Exception Flows** | — | **31** nhánh (chỉ có ở **15/28** UC; **13/28** UC từ `UC-16..28` bị cắt mất) | — | — |
| **Business Rules / Requirements** | `BR-001..006` (6), `BUSR-01..12` (12), `FR-*` (40), `NFR-*` (12), `OS-01..08` (8) | `BR-<DOMAIN>-*` cục bộ: **37** mã (chỉ có ở `UC-01..13`; **15/28** UC từ `UC-14..28` thiếu hẳn mục Business Rules!) | — | — |

### 3.2. Kiểm kê Cụm Database (28 Bảng theo phân bổ `10 / 7 / 5 / 4 / 2`)

| Chỉ số định lượng | `schema.sql` (v3.1) | `schema.dbml` | `database-schema.puml` | `data-dictionary.md` | `database-schema-design.md` | `backend/alembic/` (`0001..0004`) | `backend/src/**/orm/` |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Tổng số bảng** | **28** | **28** | **28** | **28** bảng duy nhất (**29** mục do lặp `processed_events` 2 lần) | **28** | **26** (thiếu `calendar_connections`, `milestone_proofs`) | **21** (thiếu 7 bảng) |
| **Tổng số cột (Columns)** | **292** | **284** | **284** | **288** (28 bảng) / **298** (kể cả mục lặp) | **284** | **261** | **214** |
| **Primary Keys (PK)** | **28** (26 PK đơn + 2 PK kép `concept_prerequisites`, `processed_events`) | **28** (26 `[pk]` + 2 composite `[pk]`) | **27** nhãn `<<PK>>` (sót `handler_name`) | **28** | **28** | **26** | **21** |
| **Foreign Keys (FK)** | **46** (`24` Intra-BC + `22` Cross-BC) | **45** (`40` `ref: >` + `5` `ref: -`) | **45** đường nối | **45** dòng ở Bảng §3.1 | **45** | **40** | **31** |
| **Ràng buộc `UNIQUE` (Inline/Table)** | **14** (+ **5** Partial Unique Indexes = **19**) | **11** | **0** nhãn `<<UQ>>` | **14** (+ 5 Partial UQ) | **11** (trong DBML) | **12** | **10** |
| **Tổng số `CREATE INDEX`** | **49** (`44` Index thường + `5` Unique Index) | **3** | **0** | **49** (Mục 5) | **49** (Mục 5.1) | **43** | — |
| **Ràng buộc `CHECK`** | **97** mệnh đề `CHECK` | **0** | **0** | **93** | — | **82** | — |
| **Triggers / Functions** | **1** function + **21** triggers `updated_at` | **0** | **0** | **1** function + **21** triggers | **1** function + **21** triggers | **1** function + **19** triggers | — |

### 3.3. Kiểm kê Cụm Class Diagram

| Chỉ số định lượng | `docs/uml/class-diagrams/class-diagram.puml` | `docs/uml/class-diagrams.md` (§2, §3.2, §4.2, §5) | `docs/uml/class-diagrams/class_diagram.drawio` |
| :--- | :---: | :---: | :---: |
| **Tổng số Classifiers** | **69** (`34` Classes + `35` Enumerations) | **69** ở §2 & Mermaid §3.2 (nhưng §5.5 lệch tên 5 Enum & giá trị 7 Enum) | **34** Classes (**0** Enumerations — thiếu cả 35 Enums!) |
| **Phân loại 34 Classes** | `22` `<<entity>>`, `5` `<<valueObject>>`, `3` `<<associationClass>>`, `4` `<<domainService>>` | `22` `<<entity>>`, `5` `<<valueObject>>`, `3` `<<associationClass>>`, `4` `<<domainService>>` | `22` `<<entity>>`, `5` `<<valueObject>>`, `3` `<<associationClass>>`, `4` `<<domainService>>` |
| **Abstract Class / Interface** | **0** / **0** | **0** / **0** | **0** / **0** |
| **Tổng số Attributes & Operations** | **249** attributes + **94** operations | Mermaid §3.2 khớp; **Bảng §5.1–5.4 lệch cấu trúc 4 lớp & thiếu 6 methods** | **249** attributes + **94** operations |
| **Composition (`*--`) / Aggregation (`o--`)** | **14** `*--` / **0** `o--` | **14** `*--` / **0** `o--` | **12** `*--` / **0** `o--` |
| **Association (`--`)** | **9** | **9** | **5** (thiếu 4 đường Association) |
| **Association Class links (`..`)** | **3** (`ConceptPrerequisite`, `TaskDependency`, `SessionTask`) | **3** | **2** (thiếu kết nối `SessionTask`) |
| **Generalization / Realization** | **0** / **0** | **0** / **0** | **0** / **0** |
| **Dependency (`..>`)** | **74** (`25` `<<ref>>`, `2` `<<use>>`, `47` tới Enum/VO) | Bảng §4.2 gộp thành 6 nhóm `..> <<ref>>` | **0** (thiếu toàn bộ 74 đường `..>`!) |

---

## 4. Review Coverage (Độ phủ Rà soát theo Danh mục Kiểm tra)

| Artifact | Hạng mục kiểm tra | Kết quả | Minh chứng & Tham chiếu Finding |
| :--- | :--- | :---: | :--- |
| **Use Case Diagram** | System Boundary, Actors (`ACT-01..07`) & Generalization (`AuthUser`) | **Pass** | Ranh giới rõ trong `.puml`; `Learner` và `Admin` kế thừa `AuthUser` đúng chuẩn UML 2.5.1. |
| **Use Case Diagram** | Ngữ nghĩa `<<include>>` (7 đường tới `UC-12`) & `<<extend>>` + `Extension Points` (IBM Rhapsody UML 2.5.1) | **Fail** | Hướng mũi tên đúng, nhưng 3 Base UC (`UC-14`, `UC-19`, `UC-23`) thiếu khai báo `Extension Points` (`UC-07`). |
| **Use Case Diagram** | Tính đồng bộ giữa `.puml`, `.drawio` và Bảng Actor phụ trong đặc tả | **Fail** | `UC_Master.drawio` kẹt ở 19 UCs (`UC-05`); `UC-14` nối `LLM` trên `.puml` nhưng bảng ghi `Actor phụ: Không có` (`UC-04`). |
| **Use Case Spec** | Độ đầy đủ cấu trúc đặc tả 28 Use Cases (Basic / Alternative / Exception / Rules / I-O) | **Fail** | 16/28 UC (`UC-13..28`) bị cắt cụt; 8 UC chỉ có đúng `Luồng chính`, mất sạch Exception & Rules (`UC-01`). |
| **Use Case Spec** | Tính nhất quán Business Rules với `SRS v1.3` (Auth OTP/SSO, EDF Downgrade, Knowledge Graph CRUD) | **Fail** | Mâu thuẫn Auth OTP/SSO (`UC-02`); `UC-26` ghi giữ 1 lộ trình thay vì 3 theo EDF (`UC-03`); thiếu bước tạo `learning_concepts` ở `UC-07` (`UC-08`). |
| **Use Case Spec** | Mức độ trừu tượng (không rò rỉ chi tiết cài đặt vật lý vào Basic Flow) | **Fail** | `UC-13..28` ghi thẳng tên bảng/cột/thuật toán (`Fernet`, `CSPRN 32-byte`, `study_sessions.status`) vào luồng chính (`UC-06`). |
| **Database Design** | Chuẩn hóa 3NF/BCNF, tách bảng `calendar_connections` & PK/FK/ON DELETE | **Pass** | 28 bảng đạt 3NF/BCNF; tách `calendar_connections` khỏi `webcal_tokens`; 46 FKs có `ON DELETE` chủ đích. |
| **Database Design** | Ràng buộc toàn vẹn trạng thái & vòng đời khoảng thời gian (`payment_transactions`, `users`, `goals`, `pause_records`) | **Fail** | Thiếu `payment_transactions.expires_at` (`DB-01`); thiếu `users.premium_expires_at` (`DB-03`); `chk_goals_status` chặn `'DRAFT'` (`DB-05`); `pause_records` ép `pause_end_date NOT NULL` ngay khi đang Pause (`DB-08`). |
| **Database Design** | Ràng buộc neo ngữ cảnh (`study_notes`), chống trùng khung giờ rảnh (`availability_slots`), đồng bộ JSONB (`milestone_proofs`) và kiểm soát phiên bản (`official_schedules`) | **Fail** | `study_notes` thiếu `CHECK` neo ngữ cảnh và sai `UNIQUE` (`DB-09`); `availability_slots` thiếu `UNIQUE` (`DB-10`); `milestone_proofs` chẻ đôi mảng JSONB (`DB-11`); `official_schedules` thiếu `version_number` (`DB-12`). |
| **Database Design** | Tính đúng đắn của giao dịch SQL mẫu & Partial Index (`database-schema-design.md`, `data-dictionary.md`) | **Fail** | SQL Domino Shift cộng nhầm `reschedule_count + 1` vi phạm `BUSR-07` (`DB-04`); lệch điều kiện index `idx_study_sessions_pending_takeaway` (`DB-06`). |
| **Database Design** | Đồng bộ giữa `schema.sql`, `schema.dbml`, `database-schema.puml`, `data-dictionary.md` | **Fail** | Lệch 8 cột, 1 FK và cấu trúc 9 bảng giữa `schema.sql` (292 cột) và `schema.dbml` (284 cột); lỗi copy-paste mục 2.28 (`DB-02`). |
| **Class Diagram** | Phân tách Bounded Contexts & Reference by Identity (`..> <<ref>>`) | **Pass** | Không có Association/Composition xuyên package; 25 đường `..> <<ref>>` tuân thủ DDD & `ADR-001`. |
| **Class Diagram** | Đồng bộ nội bộ giữa `class-diagram.puml` (Mermaid §3.2) và Đặc tả chi tiết §5 trong `class-diagrams.md` | **Fail** | Lệch tên 5 Enum, lệch giá trị 7 Enum, lệch cấu trúc 4 lớp (`LearningConcept`, `ConceptPrerequisite`, `MilestoneProof`, `RecallExchange`) (`CLS-01`). |
| **Class Diagram** | Ngữ nghĩa Composition Lifecycle & Multiplicity (`StudyNote`) | **Fail** | `StudySession "1" *-- "0..*" StudyNote` và `Task "1" -- "0..*" StudyNote` mâu thuẫn với `sessionId [0..1]`, `taskId [0..1]` (`CLS-02`). |
| **Class Diagram** | Đầy đủ thuộc tính nghiệp vụ ở Package 2, 3 & 4 (`Task`, `StudySession`, `SessionTask`, `OfficialSchedule`, `TaskDependency`, `RecallExchange`, `ScheduleChangeLog`, `AIReview`) | **Fail** | `OfficialSchedule` thiếu trường thống kê (`CLS-08`); `TaskDependency` lệch tên/thiếu `isMandatory` (`CLS-07`); `StudySession` thiếu `roadmapId` (`CLS-05`); `RecallExchange` thiếu `selfConfidence` (`CLS-06`). |
| **Cross-Artifact** | Đồng bộ Thực thể, Thuộc tính, Enum, AI Lineage & Quy tắc kiến trúc giữa UC ↔ Class ↔ DB ↔ ADR ↔ ORM | **Fail** | Đứt gãy `LearningConcept` (`X-01`), `LearnerProfile` (`X-02`), `ADR-004` vs `UC-23` (`X-03`), 11 Enum lệch (`X-04`), lệch mã UC/FR (`X-05`), ORM thiếu 7 bảng (`X-06`), thiếu AI Retry/Quota Lineage trên `ai_usage_logs` (`X-10`). |

---

## 5. Use Case Findings

### [UC-01] — 16/28 Use Cases (`UC-13..UC-28`) trong `use-case-specifications.md` bị cắt cụt cấu trúc đặc tả (thiếu Exception Flows, Business Rules, I/O)
- **Artifact:** [docs/uml/use-case-specifications.md](file:///Users/vuthang/Documents/FocusFlow/docs/uml/use-case-specifications.md) (Dòng 890–1494).
- **Loại:** Defect · **Severity:** Blocker · **Priority:** P0 · **Confidence:** E1
- **Hiện trạng:** Từ `UC-13` đến `UC-28`, cấu trúc 7 tiểu mục chuẩn bị rơi rụng dần; đặc biệt 8 Use Cases cuối (`UC-17, 21, 22, 24, 25, 26, 27, 28`) chỉ có duy nhất `Luồng sự kiện chính`, mất sạch luồng ngoại lệ, quy tắc nghiệp vụ và dữ liệu vào/ra.
- **Khuyến nghị:** Bổ sung đầy đủ 7 tiểu mục chuẩn bám sát yêu cầu nghiệp vụ tại `SRS v1.3` (§7.3–§7.5).

### [UC-02] — Mâu thuẫn trực diện ngay trong `SRS v1.3` và giữa `SRS v1.3` ↔ `UC-01/UC-02` ↔ `schema.sql` về Email OTP, Quên mật khẩu OTP & Google OAuth2 SSO
- **Artifact:** [docs/srs/srs-v1.3.md](file:///Users/vuthang/Documents/FocusFlow/docs/srs/srs-v1.3.md) (§2.5 Dòng 284 vs §7.1 `FR-AUTH-001/002` Dòng 508–715).
- **Loại:** Defect · **Severity:** Blocker · **Priority:** P0 · **Confidence:** E1
- **Hiện trạng:** Mục 2.5 Out-of-Scope và `UC-01/UC-02` loại bỏ Email OTP và Social Login (kích hoạt `ACTIVE` ngay), nhưng `FR-AUTH-001` và `FR-AUTH-002` vẫn bắt buộc Email OTP 6 số, Google SSO và Quên mật khẩu OTP 3 bước.
- **Khuyến nghị:** Cập nhật `FR-AUTH-001` và `FR-AUTH-002` loại bỏ yêu cầu OTP/SSO để khớp 100% với Mục 2.5 Out-of-Scope, `UC-01/02`, `ADR-008` và `schema.sql`.

### [UC-03] — `UC-26` quy định sai quy tắc hạ cấp gói từ `PREMIUM` xuống `FREE` (`> 1` lộ trình giữ lộ trình cập nhật gần nhất thay vì `> 3` lộ trình theo EDF)
- **Artifact:** [docs/uml/use-case-specifications.md](file:///Users/vuthang/Documents/FocusFlow/docs/uml/use-case-specifications.md) (`UC-26` Bước 3, Dòng 1391).
- **Loại:** Defect · **Severity:** Critical · **Priority:** P0 · **Confidence:** E1
- **Khuyến nghị:** Sửa Bước 3 của `UC-26` thành giữ lại tối đa **3 lộ trình `ACTIVE` có `targetDate` sớm nhất theo giải thuật EDF (`OS-02`, `BR-QUOTA-04`)**.

### [UC-04] — Lệch khai báo Actor phụ (`ACT-04 LLM`) ở `UC-14` và sót ghi chú `<<extend>>` ở Bảng 3.2 `SRS v1.3`
- **Artifact:** [docs/uml/use-cases/use-case-diagram.puml](file:///Users/vuthang/Documents/FocusFlow/docs/uml/use-cases/use-case-diagram.puml) (Dòng 156) vs [docs/uml/use-case-specifications.md](file:///Users/vuthang/Documents/FocusFlow/docs/uml/use-case-specifications.md) (Dòng 89, 954) & `srs-v1.3.md` (Bảng 3.2).
- **Loại:** Defect · **Severity:** Major · **Priority:** P2 · **Confidence:** E1
- **Khuyến nghị:** Bổ sung `ACT-04 (External LLM Provider)` vào cột Actor phụ của `UC-14`, và bổ sung ghi chú `(<<extend>> UC-19)` cho `UC-20, UC-21` trong Bảng 3.2 của `srs-v1.3.md`.

### [UC-05] — Ba file sơ đồ tổng quan `.drawio` bị tụt hậu ở phiên bản 19 Use Cases cũ
- **Artifact:** `docs/uml/UC_Master.drawio`, `docs/uml/UC_Dia.drawio`, `docs/uml/use-cases/UC_Master.drawio`.
- **Loại:** Defect · **Severity:** Major · **Priority:** P2 · **Confidence:** E1
- **Khuyến nghị:** Cập nhật `docs/uml/use-cases/UC_Master.drawio` lên 28 Use Cases và xóa 2 bản trùng lặp ở thư mục cha.

### [UC-06] — Rò rỉ chi tiết cài đặt vật lý vào kịch bản chính của `UC-13..UC-28` và bất nhất stereotype `<<subfunction>>`
- **Artifact:** [docs/uml/use-case-specifications.md](file:///Users/vuthang/Documents/FocusFlow/docs/uml/use-case-specifications.md) (Dòng 896–1458).
- **Loại:** Suggestion · **Severity:** Minor · **Priority:** P3 · **Confidence:** E1
- **Khuyến nghị:** Chuyển tên bảng/cột SQL/thuật toán mã hóa xuống mục Ghi chú kỹ thuật; đồng bộ hiển thị `UC-12`.

### [UC-07] — [Mới Vòng 2 · Chuẩn IBM Rhapsody UML 2.5.1] Thiếu khai báo tường minh `Extension Points` trong 3 Base Use Cases (`UC-14`, `UC-19`, `UC-23`)
- **Artifact:** [docs/uml/use-cases/use-case-diagram.puml](file:///Users/vuthang/Documents/FocusFlow/docs/uml/use-cases/use-case-diagram.puml) và `use-case-specifications.md` (`UC-14`, `UC-19`, `UC-23`).
- **Loại:** Defect · **Severity:** Major · **Priority:** P1 · **Confidence:** E1
- **Khuyến nghị (Đã chốt DEC-05):** Khai báo ngăn `extension points` trên hình oval `.puml` và dòng `Điểm mở rộng` trong bảng đặc tả của `UC-14`, `UC-19`, `UC-23`.

### [UC-08] — [Mới Vòng 2 · Độ phủ CRUD Nghiệp vụ] Thiếu đặc tả bước khởi tạo / liên kết Kho Khái niệm Tri thức (`learning_concepts`) trong `UC-07`
- **Artifact:** [docs/uml/use-case-specifications.md](file:///Users/vuthang/Documents/FocusFlow/docs/uml/use-case-specifications.md) (`UC-07` Dòng 499–568).
- **Loại:** Defect · **Severity:** Major · **Priority:** P1 · **Confidence:** E1
- **Khuyến nghị (Đã chốt DEC-05/06):** Đặc tả rõ ở Bước 6 của `UC-07`: Hệ thống ưu tiên ánh xạ vào khái niệm chuẩn (`VERIFIED` từ Seed Migration); nếu chủ đề mới chưa có, AI đề xuất khái niệm mới với `verification_status = 'UNVERIFIED'`.

---

## 6. Database Findings

### [DB-01] — Bảng `payment_transactions` trong `schema.sql` thiếu cột `expires_at` và sai tập trạng thái (`REFUNDED` thay vì `EXPIRED`)
- **Artifact:** [docs/database/schema.sql](file:///Users/vuthang/Documents/FocusFlow/docs/database/schema.sql) (Dòng 245–267).
- **Loại:** Defect · **Severity:** Blocker · **Priority:** P0 · **Confidence:** E1
- **Khuyến nghị:** Thêm `expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '15 minutes')`, đổi `'REFUNDED'` $\rightarrow$ `'EXPIRED'`, và thêm partial index trên `(expires_at) WHERE status = 'PENDING'`.

### [DB-02] — Độ lệch cấu trúc trên 9 bảng giữa `schema.sql` (292 cột) với `schema.dbml` / `database-schema.puml` / `database-schema-design.md` (284 cột) và lỗi Copy-Paste trong `data-dictionary.md`
- **Artifact:** [docs/database/schema.sql](file:///Users/vuthang/Documents/FocusFlow/docs/database/schema.sql) vs [docs/database/schema.dbml](file:///Users/vuthang/Documents/FocusFlow/docs/database/schema.dbml), `data-dictionary.md`.
- **Loại:** Defect · **Severity:** Blocker · **Priority:** P0 · **Confidence:** E1
- **Khuyến nghị:** Tái đồng bộ toàn bộ DBML, PUML, Design.md và sửa mục `2.26`, `2.28` (lặp `processed_events`), `3.1` của `data-dictionary.md` từ nguồn chuẩn `schema.sql`.

### [DB-03] — Bảng `users` thiếu cột `premium_expires_at` và `last_login_at`
- **Artifact:** [docs/database/schema.sql](file:///Users/vuthang/Documents/FocusFlow/docs/database/schema.sql) (Dòng 35–49).
- **Loại:** Defect · **Severity:** Critical · **Priority:** P0 · **Confidence:** E1
- **Khuyến nghị (Đã chốt DEC-06):** Thêm 2 cột `premium_expires_at TIMESTAMPTZ NULL` và `last_login_at TIMESTAMPTZ NULL` vào bảng `users`.

### [DB-04] — Giao dịch SQL mẫu của Domino Shift trong `database-schema-design.md` cộng tăng `reschedule_count + 1` vi phạm `BUSR-07`
- **Artifact:** [docs/database/database-schema-design.md](file:///Users/vuthang/Documents/FocusFlow/docs/database/database-schema-design.md) (Dòng 1175).
- **Loại:** Defect · **Severity:** Critical · **Priority:** P1 · **Confidence:** E1
- **Khuyến nghị:** Xóa dòng `reschedule_count = reschedule_count + 1` khỏi câu lệnh `UPDATE tasks` mẫu.

### [DB-05] — Ràng buộc `chk_goals_status` chặn trạng thái `'DRAFT'` / `'CLARIFIED'` và bảng `roadmaps` thiếu `UNIQUE (goal_id)`
- **Artifact:** [docs/database/schema.sql](file:///Users/vuthang/Documents/FocusFlow/docs/database/schema.sql) (Dòng 290, 300).
- **Loại:** Defect · **Severity:** Major · **Priority:** P1 · **Confidence:** E1
- **Khuyến nghị:** Sửa `chk_goals_status` mở rộng `'DRAFT', 'CLARIFIED'`, và thêm `CONSTRAINT uq_roadmaps_goal UNIQUE (goal_id)`.

### [DB-06] — Lệch điều kiện Partial Index `idx_study_sessions_pending_takeaway` và lệch TTL giữ chỗ Quota AI (`120s` vs `5 phút`)
- **Artifact:** [docs/database/data-dictionary.md](file:///Users/vuthang/Documents/FocusFlow/docs/database/data-dictionary.md) (Dòng 33, 747), `ADR-004`.
- **Loại:** Defect · **Severity:** Major · **Priority:** P2 · **Confidence:** E1
- **Khuyến nghị:** Sửa điều kiện lọc thành `WHERE pending_takeaway = TRUE`, thống nhất TTL 5 phút (300 giây).

### [DB-07] — Khoảng giá trị `chk_learner_profiles_duration` (`15..120` phút) hẹp hơn miền lọc ngoại lai của `SRS FR-PROFILE-001`
- **Artifact:** [docs/database/schema.sql](file:///Users/vuthang/Documents/FocusFlow/docs/database/schema.sql) (Dòng 66).
- **Loại:** Defect · **Severity:** Minor · **Priority:** P3 · **Confidence:** E1
- **Khuyến nghị:** Bổ sung phép kẹp `CLAMP(median, 15, 120)` vào đặc tả `FR-PROFILE-001` và `UC-25`.

### [DB-08] — [Mới Vòng 2 · Lý thuyết Khoảng Thời gian Mở] Bảng `pause_records` ép `pause_end_date NOT NULL` và `shifted_days > 0` ngay khi đang Pause
- **Artifact:** [docs/database/schema.sql](file:///Users/vuthang/Documents/FocusFlow/docs/database/schema.sql) (Dòng 596–611).
- **Loại:** Defect · **Severity:** Critical · **Priority:** P0 · **Confidence:** E1
- **Khuyến nghị (Đã chốt DEC-01):** Cho phép `pause_end_date` và `shifted_days` nhận `NULL` khi `status = 'ACTIVE'`; chỉ bắt buộc `NOT NULL` và tính `shifted_days = (pause_end_date - pause_start_date)` khi chuyển sang `'COMPLETED'` (Resume).

### [DB-09] — [Mới Vòng 2 · Toàn vẹn Neo Ngữ cảnh & Quan hệ N-N] Bảng `study_notes` thiếu `CHECK` neo ngữ cảnh và sai `UNIQUE (session_id, note_type)`
- **Artifact:** [docs/database/schema.sql](file:///Users/vuthang/Documents/FocusFlow/docs/database/schema.sql) (Dòng 550–583).
- **Loại:** Defect · **Severity:** Critical · **Priority:** P0 · **Confidence:** E1
- **Khuyến nghị (Đã chốt DEC-02):** Thêm `CONSTRAINT chk_study_notes_context_anchor CHECK (session_id IS NOT NULL OR task_id IS NOT NULL)` và đổi sang Partial Unique Index `(session_id, task_id) WHERE note_type = 'TAKEAWAY'`.

### [DB-10] — [Mới Vòng 2 · Lý thuyết PostgreSQL 16 Temporal Exclusion] Bảng `availability_slots` thiếu ràng buộc chống trùng slot
- **Artifact:** [docs/database/schema.sql](file:///Users/vuthang/Documents/FocusFlow/docs/database/schema.sql) (Dòng 139–157).
- **Loại:** Risk · **Severity:** Major · **Priority:** P2 · **Confidence:** E1
- **Khuyến nghị (Đã chốt DEC-03):** Thêm Partial Unique Index `UNIQUE (availability_id, day_of_week, start_time) WHERE is_active = TRUE`.

### [DB-11] — [Mới Vòng 3 · Ánh xạ Class Diagram $\rightarrow$ Database] Bảng `milestone_proofs` chẻ đôi mảng JSONB gây rủi ro lệch index thay vì một mảng `RecallExchange[1..*]`
- **Artifact:** [docs/database/schema.sql](file:///Users/vuthang/Documents/FocusFlow/docs/database/schema.sql) (Dòng 699–700) vs [docs/uml/class-diagrams/class-diagram.puml](file:///Users/vuthang/Documents/FocusFlow/docs/uml/class-diagrams/class-diagram.puml) (Dòng 834, 848–854).
- **Loại:** Defect · **Severity:** Major · **Priority:** P1 · **Confidence:** E1
- **Phân tích:** Trong `schema.sql`, `milestone_proofs` lưu 2 cột `recall_questions_payload JSONB` và `learner_answers_payload JSONB`. Việc chẻ đôi 1 thực thể trao đổi (`RecallExchange`) thành 2 mảng song song tạo rủi ro bất đồng bộ nếu độ dài 2 mảng lệch nhau.
- **Khuyến nghị (Đã chốt DEC-07):** Gom thành 1 mảng JSONB duy nhất: `recall_exchanges_payload JSONB NOT NULL DEFAULT '[]'::jsonb`, lưu danh sách các object `RecallExchange [{question_index, concept_code, question_text, learner_answer, self_confidence, question_score, ai_critique}]`, khớp 100% với Class Diagram.

### [DB-12] — [Mới Vòng 3 · Ánh xạ Class Diagram $\rightarrow$ Database] Bảng `official_schedules` thiếu cột `version_number` và `strategy`
- **Artifact:** [docs/database/schema.sql](file:///Users/vuthang/Documents/FocusFlow/docs/database/schema.sql) (Dòng 350–363) vs [docs/uml/class-diagrams/class-diagram.puml](file:///Users/vuthang/Documents/FocusFlow/docs/uml/class-diagrams/class-diagram.puml) (Dòng 506–507).
- **Loại:** Defect · **Severity:** Major · **Priority:** P1 · **Confidence:** E1
- **Khuyến nghị (Đã chốt DEC-08):** Thêm `version_number INTEGER NOT NULL DEFAULT 1` (phục vụ kiểm tra phiên bản đồng bộ lịch ngoại vi và optimistic locking) và `strategy VARCHAR(20) NOT NULL DEFAULT 'MERGE_EXISTING'` vào bảng `official_schedules`.

---

## 7. Class Diagram Findings

### [CLS-01] — Tự mâu thuẫn nội bộ nghiêm trọng trong `docs/uml/class-diagrams.md` giữa Sơ đồ (§2, §3.2) và Đặc tả chi tiết (§5.1–§5.5) trên 4 Lớp và 12 Enumerations
- **Artifact:** [docs/uml/class-diagrams.md](file:///Users/vuthang/Documents/FocusFlow/docs/uml/class-diagrams.md) (§5.2, §5.4, §5.5).
- **Loại:** Defect · **Severity:** Critical · **Priority:** P0 · **Confidence:** E1
- **Khuyến nghị:** Cập nhật toàn bộ Mục 5 của `class-diagrams.md` khớp 100% với `class-diagram.puml`.

### [CLS-02] — Mâu thuẫn bội số bắt buộc `"1"` tại `StudySession "1" *-- "0..*" StudyNote` và `Task "1" -- "0..*" StudyNote`
- **Artifact:** [docs/uml/class-diagrams/class-diagram.puml](file:///Users/vuthang/Documents/FocusFlow/docs/uml/class-diagrams/class-diagram.puml) (Dòng 739–740).
- **Loại:** Defect · **Severity:** Major · **Priority:** P1 · **Confidence:** E1
- **Khuyến nghị (Đã chốt DEC-02):** Đổi bội số ở cả đầu `StudySession` và `Task` thành `"0..1"`: `StudySession "0..1" *-- "0..*" StudyNote` và `Task "0..1" -- "0..*" StudyNote`.

### [CLS-03] — File `class_diagram.drawio` thiếu toàn bộ 35 `<<enumeration>>` và thiếu 81/100 đường quan hệ
- **Artifact:** [docs/uml/class-diagrams/class_diagram.drawio](file:///Users/vuthang/Documents/FocusFlow/docs/uml/class-diagrams/class_diagram.drawio).
- **Loại:** Defect · **Severity:** Major · **Priority:** P2 · **Confidence:** E1
- **Khuyến nghị:** Cập nhật lại `.drawio` hoặc xuất ảnh `.png` trực tiếp từ `class-diagram.puml`.

### [CLS-04] — Lặp lại thuộc tính khóa ngoại vật lý (`goalId`, `roadmapId`, `quotaId`) bên trong các lớp đã có đường nối Association/Composition
- **Artifact:** [docs/uml/class-diagrams/class-diagram.puml](file:///Users/vuthang/Documents/FocusFlow/docs/uml/class-diagrams/class-diagram.puml) (Dòng 249, 392, 430, 461, 504).
- **Loại:** Suggestion · **Severity:** Minor · **Priority:** P3 · **Confidence:** E1
- **Khuyến nghị:** Gắn nhãn `{fk}` hoặc ghi chú rõ quy ước trong Mục 4.1 của `class-diagrams.md`.

### [CLS-05] — [Mới Vòng 2 · Độ lệch Cấu trúc Thực thi Package 3] Lệch thuộc tính giữa `class-diagram.puml` và `schema.sql` trên `StudySession`, `Task` và `SessionTask`
- **Artifact:** [docs/uml/class-diagrams/class-diagram.puml](file:///Users/vuthang/Documents/FocusFlow/docs/uml/class-diagrams/class-diagram.puml) (Dòng 581–682) vs `schema.sql`.
- **Loại:** Defect · **Severity:** Critical · **Priority:** P0 · **Confidence:** E1
- **Khuyến nghị (Đã chốt DEC-04):** Bổ sung `timer_mode` vào bảng `study_sessions`; cập nhật `class-diagram.puml` (thêm `roadmapId` vào `StudySession`, đổi `Task./actualMinutes`, `Task./isOverdue` thành thuộc tính dẫn xuất, thêm `actualMinutes` và `statusAfterSession` vào `SessionTask`).

### [CLS-06] — [Mới Vòng 2 · Độ lệch Cấu trúc Đánh giá Package 4] `RecallExchange` thiếu `selfConfidence`, `ScheduleChangeLog` và `AIReview` lệch mô hình dữ liệu
- **Artifact:** [docs/uml/class-diagrams/class-diagram.puml](file:///Users/vuthang/Documents/FocusFlow/docs/uml/class-diagrams/class-diagram.puml) (Dòng 761–854).
- **Loại:** Defect · **Severity:** Critical · **Priority:** P0 · **Confidence:** E1
- **Khuyến nghị (Đã chốt DEC-04):** Bổ sung `selfConfidence : Integer` vào `RecallExchange`; đồng bộ `ScheduleChangeLog` và `AIReview` khớp 100% với `schema.sql`.

### [CLS-07] — [Mới Vòng 3 · Chuẩn hóa Thuật ngữ Đồ thị DAG] Lớp `TaskDependency` dùng tên `prerequisiteTaskId` / `dependentTaskId` và thiếu `isMandatory`
- **Artifact:** [docs/uml/class-diagrams/class-diagram.puml](file:///Users/vuthang/Documents/FocusFlow/docs/uml/class-diagrams/class-diagram.puml) (Dòng 616–621) vs [docs/database/schema.sql](file:///Users/vuthang/Documents/FocusFlow/docs/database/schema.sql) (Dòng 479–491).
- **Loại:** Defect · **Severity:** Major · **Priority:** P2 · **Confidence:** E1
- **Khuyến nghị (Đã chốt DEC-09):** Chuẩn hóa thuộc tính trên Class Diagram theo thuật ngữ đồ thị của CSDL: đổi thành `predecessorTaskId : UUID`, `successorTaskId : UUID` và bổ sung `isMandatory : Boolean = true`.

### [CLS-08] — [Mới Vòng 3 · Ánh xạ Class Diagram $\rightarrow$ Database] Lớp `OfficialSchedule` thiếu các thuộc tính thống kê `totalSessions`, `totalPlannedMinutes`, `activatedAt`
- **Artifact:** [docs/uml/class-diagrams/class-diagram.puml](file:///Users/vuthang/Documents/FocusFlow/docs/uml/class-diagrams/class-diagram.puml) (Dòng 502–513) vs [docs/database/schema.sql](file:///Users/vuthang/Documents/FocusFlow/docs/database/schema.sql) (Dòng 350–363).
- **Loại:** Defect · **Severity:** Major · **Priority:** P2 · **Confidence:** E1
- **Khuyến nghị (Đã chốt DEC-08):** Bổ sung `totalSessions : Integer = 0`, `totalPlannedMinutes : Integer = 0`, `activatedAt : DateTime` vào lớp `OfficialSchedule` trong `class-diagram.puml`.

---

## 8. Cross-Artifact Findings (Kiểm tra Chéo Use Case ↔ Class Diagram ↔ Database)

### [X-01] — Đứt gãy 4 chiều mô hình `LearningConcept` & `ConceptPrerequisite`
- **Artifact:** `schema.sql`, `class-diagram.puml`, `class-diagrams.md` (§5.2.7), `schema.dbml`.
- **Loại:** Defect · **Severity:** Blocker · **Priority:** P0 · **Confidence:** E1
- **Khuyến nghị (Đã chốt DEC-06):** Chốt theo mô hình Global Knowledge Base của `schema.sql` (`concept_id VARCHAR(120)`), bỏ `Roadmap *-- LearningConcept` trên Class Diagram, dùng `Task/ProposedTask ..> LearningConcept : <<ref>>`.

### [X-02] — Bất đồng bộ cấu trúc `LearnerProfile` (4 chỉ số thực chứng vs thói quen tự khai báo), thiếu `resetToColdStart()` và lệch mặc định 25p vs 45p
- **Artifact:** `schema.sql` (Dòng 55–73), `SRS FR-PROFILE-001` vs `class-diagram.puml` (Dòng 164–183).
- **Loại:** Defect · **Severity:** Critical · **Priority:** P0 · **Confidence:** E1
- **Khuyến nghị:** Đồng bộ thuộc tính theo `schema.sql`, thêm `+ resetToColdStart() : void`, đổi mặc định Cold Start thành `25` phút tại `UC-01` và `user_orm.py`.

### [X-03] — Mâu thuẫn kiến trúc giữa `ADR-004` (cho phép AI Reschedule bỏ qua Cổng Kiểm duyệt 3 Tầng) với `SRS v1.3`, `UC-23`, `ADR-009/010`
- **Artifact:** `ADR-004` (Dòng 67).
- **Loại:** Defect · **Severity:** Critical · **Priority:** P0 · **Confidence:** E1
- **Khuyến nghị:** Xóa câu "bỏ qua Cổng Kiểm duyệt 3 Tầng" tại Dòng 67 và sửa `UC-13` $\rightarrow$ `UC-17` tại Dòng 69 của `ADR-004`.

### [X-04] — 11/35 Kiểu liệt kê (`<<enumeration>>`) và thuộc tính lớp trong `class-diagram.puml` lệch với `schema.sql`
- **Artifact:** `class-diagram.puml` vs `schema.sql`.
- **Loại:** Defect · **Severity:** Major · **Priority:** P1 · **Confidence:** E1
- **Khuyến nghị:** Chuẩn hóa 1-1 cả 11 tập giá trị Enum giữa hai tài liệu.

### [X-05] — Sai lệch số hiệu Use Case (`UC-15..UC-27`) và 18 mã `FR-*`/`BUSR-*`/`NFR-*` "ma" trong `class-diagrams.md`, `use-case-specifications.md` và các `ADR`
- **Artifact:** `class-diagrams.md` (§6.1), `use-case-specifications.md`, `ADR-003, 006, 010`.
- **Loại:** Defect · **Severity:** Major · **Priority:** P1 · **Confidence:** E1
- **Khuyến nghị:** Đồng bộ toàn bộ mã Use Case và mã yêu cầu theo đúng `SRS v1.3`.

### [X-06] — Độ trễ đồng bộ giữa Tài liệu Thiết kế (28 bảng v3.1) với Alembic Migrations (26 bảng) và SQLAlchemy ORM Models (21 bảng)
- **Artifact:** `backend/alembic/versions/` và `backend/src/**/orm/*.py`.
- **Loại:** Defect · **Severity:** Major · **Priority:** P1 · **Confidence:** E1
- **Khuyến nghị:** Bổ sung migration tạo 2 bảng còn thiếu và cập nhật 7 ORM models còn thiếu.

### [X-08] — Còn sót đường dẫn tuyệt đối cục bộ (`file:///Users/vuthang/...`)
- **Artifact:** `database-schema-design.md` (Dòng 1223).
- **Loại:** Defect · **Severity:** Minor · **Priority:** P3 · **Confidence:** E1
- **Khuyến nghị:** Đổi thành đường dẫn tương đối.

### [X-09] — Kiến trúc Khóa ngoại Vật lý Xuyên Bounded Context (22 Cross-BC FKs) kết hợp Cấm ORM `relationship()` / `JOIN` Chéo Context
- **Artifact:** `schema.sql`, `ADR-007` (§3.3), `AGENTS.md` (§4).
- **Loại:** Suggestion · **Severity:** Info · **Priority:** P3 · **Confidence:** E1
- **Khuyến nghị:** Gắn comment `-- [Cross-BC FK]` cạnh 22 dòng FK liên context.

### [X-10] — [Mới Vòng 2 · Chuẩn IBM Enterprise GenAI Governance & Lineage] Bảng `ai_usage_logs` thiếu liên kết `reservation_id`, `attempt_no` và `estimated_cost_usd`
- **Artifact:** `schema.sql` (Dòng 212–238) vs `class-diagram.puml` (Dòng 268–282).
- **Loại:** Defect · **Severity:** Major · **Priority:** P1 · **Confidence:** E1
- **Khuyến nghị (Đã chốt DEC-05):** Thêm `reservation_id UUID NULL`, `attempt_no SMALLINT DEFAULT 1`, `estimated_cost_usd NUMERIC(10,6)` vào `ai_usage_logs` và `AIUsageLog`.

---

## 9. What Is Working Well (Những Điểm Thiết Kế Xuất Sắc Có Minh Chứng)

1. **Tuân thủ nghiêm ngặt Ranh giới Bounded Context & Reference by Identity trên `class-diagram.puml`**:
   - Giữa 4 package `account`, `planning`, `execution`, `evaluation` trong [class-diagram.puml](file:///Users/vuthang/Documents/FocusFlow/docs/uml/class-diagrams/class-diagram.puml) (Dòng 890–915), không có bất kỳ đường `Association (--)` hay `Composition (*--)` nào cắt ngang ranh giới gói. Toàn bộ 25 kết nối liên miền đều dùng `..> : <<ref>> <id>`, khớp hoàn hảo với chuẩn **IBM Enterprise DDD Aggregate Boundaries** và `ADR-001`.
2. **Mô hình hóa Cổng Kiểm định Lai 3 Tầng (`UC-12`) và Bất biến Bản nháp AI (`ScheduleProposal(DRAFT) -> OfficialSchedule`) rất chặt chẽ**:
   - Trên cả 6 file `.puml` Use Case, 7 luồng sinh/biến đổi lịch (`UC-08, 09, 11, 13, 22, 23, 24`) đều tái sử dụng `UC-12` qua quan hệ `<<include>>` đúng hướng chuẩn **IBM Rhapsody UML 2.5.1**. Ở tầng CSDL ([schema.sql](file:///Users/vuthang/Documents/FocusFlow/docs/database/schema.sql) Dòng 389), Partial Unique Index `uq_schedule_proposals_roadmap_draft` (`WHERE status = 'DRAFT'`) bảo đảm mỗi lộ trình chỉ có tối đa 1 bản nháp chờ duyệt.
3. **Cơ chế Giữ chỗ Hạn ngạch AI 2 Pha Nguyên tử (Two-Phase ACID Quota Reservation)**:
   - Cặp bảng `ai_quotas` và `ai_quota_reservations` ([schema.sql](file:///Users/vuthang/Documents/FocusFlow/docs/database/schema.sql) Dòng 163–210) kết hợp `CHECK (used_calls + reserved_calls <= monthly_limit)` và `CHECK ((status = 'RESERVED' AND resolved_at IS NULL) OR (status <> 'RESERVED' AND resolved_at IS NOT NULL))` cùng Partial Index `WHERE status = 'RESERVED'`, triệt tiêu hoàn toàn lỗi Race Condition khi người dùng mở nhiều tab gọi AI đồng thời.
4. **Chuẩn hóa 3NF/BCNF giữa `webcal_tokens` và `calendar_connections`**:
   - Việc tách bảng `calendar_connections` ([schema.sql](file:///Users/vuthang/Documents/FocusFlow/docs/database/schema.sql) Dòng 98–114) khỏi `webcal_tokens` (Dòng 79–93) phân tách rõ khóa băm một chiều `SHA-256` (`token_hash` cho luồng `.ics` 1 chiều `UC-18`) và khóa mã hóa đối xứng `Fernet` (`oauth_refresh_token_encrypted` cho luồng OAuth 2 chiều `UC-17`).
5. **Bảo vệ lịch sử học tập bằng `ON DELETE RESTRICT` có chủ đích trên `session_tasks.task_id` và `payment_transactions.user_id`**:
   - Trong [schema.sql](file:///Users/vuthang/Documents/FocusFlow/docs/database/schema.sql) (Dòng 247, 540), việc sử dụng `ON DELETE RESTRICT` trên `session_tasks.task_id` ngăn chặn ở tầng vật lý việc xóa nhầm một `Task` đã từng được người học thực thi trong một phiên Pomodoro, bảo toàn tính toàn vẹn của dữ liệu thực chứng SRL.

---

## 10. Confirmed Design Decisions (Toàn Bộ 09 Quyết Định Thiết Kế Đã Chốt Qua `/grill-me`)

| Mã Quyết định | Vấn đề Thiết kế & Finding Liên quan | Quyết định Đã Chốt (Confirmed Baseline) |
| :---: | :--- | :--- |
| **DEC-01** | **Vòng đời bảng `pause_records` (`[DB-08]`)**: Xử lý cột `pause_end_date` và `shifted_days` khi người học đang tạm dừng (`status = 'ACTIVE'`). | Cho phép `pause_end_date` và `shifted_days` nhận `NULL` khi `status = 'ACTIVE'`; chỉ bắt buộc `NOT NULL` và tính `shifted_days = (pause_end_date - pause_start_date)` khi chuyển sang `'COMPLETED'` (Resume). |
| **DEC-02** | **Ràng buộc bảng `study_notes` & lớp `StudyNote` (`[DB-09]`, `[CLS-02]`)**: Bội số quan hệ, neo ngữ cảnh và khóa duy nhất khi 1 phiên học nhiều bài. | (1) Sửa `class-diagram.puml` thành `0..1` ở cả đầu `StudySession` và `Task`; (2) Thêm `CHECK (session_id IS NOT NULL OR task_id IS NOT NULL)` vào `schema.sql`; (3) Thay `UNIQUE (session_id, note_type)` bằng Partial Unique Index trên `(session_id, task_id) WHERE note_type = 'TAKEAWAY'`. |
| **DEC-03** | **Chống chồng lấn khung giờ ở PostgreSQL 16 (`[DB-10]`)**: Ràng buộc tầng CSDL cho `availability_slots` và `tasks`. | Bổ sung Partial Unique Index `UNIQUE (availability_id, day_of_week, start_time) WHERE is_active = TRUE` cho `availability_slots` để chặn trùng khung giờ rảnh; giữ Index thường cho `tasks` vì lịch học cho phép Soft Overflow có xác nhận. |
| **DEC-04** | **Đồng bộ cấu trúc Package 3 & 4 (`[CLS-05]`, `[CLS-06]`)**: Độ lệch thuộc tính giữa `class-diagram.puml` và `schema.sql`. | (1) Thêm cột `timer_mode` vào bảng `study_sessions`; (2) Cập nhật `class-diagram.puml`: đổi `Task./actualMinutes` & `Task./isOverdue` thành thuộc tính dẫn xuất `/`, thêm `scheduledStart/End : DateTime`; thêm `roadmapId` vào `StudySession`; thêm `actualMinutes` & `statusAfterSession` vào `SessionTask`; thêm `selfConfidence` vào `RecallExchange`; đồng bộ `ScheduleChangeLog` & `AIReview` theo `schema.sql`. |
| **DEC-05** | **Chuẩn IBM Rhapsody UML 2.5.1 `Extension Points`, Nguồn tạo `LearningConcept` & IBM GenAI Lineage (`[UC-07]`, `[UC-08]`, `[X-10]`)**. | (1) Khai báo tường minh `Extension Points` trong ngăn oval và bảng đặc tả của `UC-14`, `UC-19`, `UC-23`; (2) Ghi rõ trong `UC-07`: `learning_concepts` khởi tạo từ Seed Migration (`VERIFIED`) + AI đề xuất (`UNVERIFIED`); (3) Bổ sung `reservation_id UUID NULL`, `attempt_no SMALLINT DEFAULT 1`, `estimated_cost_usd NUMERIC(10,6)` vào `ai_usage_logs` và `AIUsageLog`. |
| **DEC-06** | **Bản chất `LearningConcept` & Hết hạn gói `PREMIUM` (`[X-01]`, `[DB-03]`)**. | (1) Chốt `LearningConcept` là **Global Knowledge Base** dùng chung (`concept_id VARCHAR(120)`, bỏ `Roadmap *-- LearningConcept` trên Class Diagram, dùng `Task/ProposedTask ..> LearningConcept : <<ref>>`); (2) Bổ sung cột `premium_expires_at TIMESTAMPTZ NULL` và `last_login_at TIMESTAMPTZ NULL` vào bảng `users`. |
| **DEC-07** | **Chuẩn hóa cấu trúc lưu trữ `RecallExchange` trên `milestone_proofs` (`[DB-11]`)**. | Gom 2 mảng `recall_questions_payload` và `learner_answers_payload` thành **1 mảng JSONB duy nhất: `recall_exchanges_payload JSONB NOT NULL DEFAULT '[]'::jsonb`**, lưu danh sách các object `RecallExchange` đầy đủ. Khớp 100% với Class Diagram và triệt tiêu rủi ro lệch index. |
| **DEC-08** | **Đồng bộ hai chiều thực thể `OfficialSchedule` (`[DB-12]`, `[CLS-08]`)**. | (1) CSDL `official_schedules`: thêm `version_number INTEGER NOT NULL DEFAULT 1` và `strategy VARCHAR(20) NOT NULL DEFAULT 'MERGE_EXISTING'`; (2) Class Diagram `OfficialSchedule`: bổ sung `totalSessions : Integer = 0`, `totalPlannedMinutes : Integer = 0`, `activatedAt : DateTime`. |
| **DEC-09** | **Chuẩn hóa thuộc tính `TaskDependency` theo thuật ngữ đồ thị DAG (`[CLS-07]`)**. | Chuẩn hóa tên thuộc tính trên Class Diagram theo CSDL: đổi thành `predecessorTaskId : UUID`, `successorTaskId : UUID` và bổ sung `isMandatory : Boolean = true` (phân biệt ràng buộc cứng bắt buộc vs khuyến nghị). |

---

## 11. Prioritized Action Plan (Kế hoạch Hành động theo Thứ tự Ưu tiên)

| Thứ tự | Công việc cần thực hiện | Finding giải quyết | Priority | Trạng thái Thực thi | Căn cứ Hoàn thành & Kiểm chứng |
| :-: | :--- | :---: | :---: | :---: | :--- |
| **1** | Sửa `FR-AUTH-001` & `FR-AUTH-002` trong `docs/srs/srs-v1.3.md` (§7.1): bỏ yêu cầu Email OTP, Quên mật khẩu OTP & Google SSO để khớp với §2.5 Out-of-Scope và `UC-01/UC-02`; bổ sung `ACT-04` cho `UC-14` và ghi chú `(<<extend>> UC-19)` vào Bảng 3.2 cho `UC-20, UC-21`. | `UC-02`, `UC-04` | **P0** | **✅ ĐÃ HOÀN TẤT** | Đã chuẩn hóa `docs/srs/srs-v1.3.md`, xóa OTP/SSO, đồng bộ 100% với `ADR-008` và §2.5. |
| **2** | Cập nhật `docs/database/schema.sql`: (a) `payment_transactions`: thêm `expires_at`, đổi `'REFUNDED'` $\rightarrow$ `'EXPIRED'`; (b) `users`: thêm `premium_expires_at`, `last_login_at`; (c) `goals` & `roadmaps`: thêm `'DRAFT'`, `'CLARIFIED'` vào `chk_goals_status` và `UNIQUE (goal_id)`; (d) `pause_records`: cho phép `pause_end_date`, `shifted_days` là `NULL` khi `'ACTIVE'`; (e) `study_notes`: thêm `chk_study_notes_context_anchor` và đổi sang Partial Unique Index `(session_id, task_id) WHERE note_type = 'TAKEAWAY'`; (f) `study_sessions`: thêm `timer_mode`; (g) `ai_usage_logs`: thêm `reservation_id`, `attempt_no`, `estimated_cost_usd`; (h) `availability_slots`: thêm Partial Unique Index chống trùng slot; (i) `milestone_proofs`: gom 2 mảng thành `recall_exchanges_payload JSONB`; (j) `official_schedules`: thêm `version_number`, `strategy`. | `DB-01`, `DB-03`, `DB-05`, `DB-08`, `DB-09`, `DB-10`, `DB-11`, `DB-12`, `CLS-05`, `X-10` | **P0** | **✅ ĐÃ HOÀN TẤT** | Đã test 100% cú pháp DDL & ràng buộc positive/negative trên PostgreSQL 16 container. |
| **3** | Đồng bộ lại `schema.dbml`, `database-schema.puml`, `database-schema-design.md` (xóa dòng `reschedule_count + 1` ở SQL Domino Shift dòng 1175 và sửa link tuyệt đối dòng 1223) và sửa mục `2.26`, `2.28`, `3.1`, `747` trong `data-dictionary.md` từ nguồn chuẩn `schema.sql`. | `DB-02`, `DB-04`, `DB-06`, `X-08` | **P0** | **✅ ĐÃ HOÀN TẤT** | Cả 4 tài liệu CSDL phái sinh đã đồng bộ đủ 28 bảng, 52 index, 0 liên kết tuyệt đối. |
| **4** | Cập nhật `docs/uml/class-diagrams/class-diagram.puml`: (a) Chuyển `LearningConcept` sang Global Knowledge Base (`..> <<ref>>`); (b) Đồng bộ `LearnerProfile` (4 chỉ số thực chứng + `resetToColdStart()` + default 25p); (c) Sửa bội số `0..1` cho `StudyNote`; (d) Đồng bộ `Task`, `StudySession`, `SessionTask`, `RecallExchange`, `ScheduleChangeLog`, `AIReview`, `PauseRecord`, `AIUsageLog`; (e) Chuẩn hóa 11 Enum; (f) Đồng bộ `OfficialSchedule` và `TaskDependency` theo DEC-08, DEC-09. | `X-01`, `X-02`, `X-04`, `X-10`, `CLS-02`, `CLS-05`, `CLS-06`, `CLS-07`, `CLS-08` | **P0** | **✅ ĐÃ HOÀN TẤT** | File `.puml` đạt 69 Classifiers chuẩn UML 2.5.1, cân bằng ngoặc nhọn, 0 lỗi cú pháp. |
| **5** | Đồng bộ toàn bộ Mục `5.1..5.5` và Bảng truy vết `6.1` trong `docs/uml/class-diagrams.md` theo đúng `class-diagram.puml` mới và số hiệu `UC-01..UC-28` của `SRS v1.3`. | `CLS-01`, `X-05` | **P1** | **✅ ĐÃ HOÀN TẤT** | Sơ đồ Mermaid Mục 3.2, bảng đặc tả Mục 5 và ma trận truy vết Mục 6.1 (28 UCs) đã khớp 100%. |
| **6** | Hoàn thiện `docs/uml/use-case-specifications.md` và `.puml`: (a) Bổ sung đầy đủ 7 tiểu mục chuẩn cho `UC-13..UC-28`; (b) Sửa quy tắc EDF ở `UC-26` bước 3; (c) Khai báo `Extension Points` cho `UC-14`, `UC-19`, `UC-23`; (d) Bổ sung bước khởi tạo/tra cứu `learning_concepts` ở `UC-07`; (e) Sửa Actor phụ `UC-14` và các mã `FR-*`/`UC-*` tham chiếu nhầm. | `UC-01`, `UC-03`, `UC-04`, `UC-06`, `UC-07`, `UC-08`, `X-05` | **P0 / P1** | **✅ ĐÃ HOÀN TẤT** | 28/28 Use Cases đạt đủ 7 mục chuẩn ISO 29148, sửa EDF `UC-26`, khai báo Extension Points. |
| **7** | Cập nhật `ADR-004` (bỏ câu bypass cổng 3 tầng ở Dòng 67, đổi TTL 120s $\rightarrow$ 5m, sửa `UC-13` $\rightarrow$ `UC-17`), `ADR-001`, `ADR-003`, `ADR-006`, `ADR-007`, `ADR-010` (đồng bộ 28 bảng và số hiệu `UC-01..UC-28`). | `X-03`, `X-05`, `DB-06` | **P1** | **✅ ĐÃ HOÀN TẤT** | Toàn bộ 10 ADRs và `README.md` đã đồng bộ 100% với `SRS v1.3` và `schema.sql` v3.1. |
| **8** | Cập nhật `UC_Master.drawio`, `class_diagram.drawio` (hoặc xuất lại ảnh `.png` từ `.puml`) và viết Alembic migration + 7 ORM models còn thiếu trong `backend/`. | `UC-05`, `CLS-03`, `X-06` | **P2** | **⏳ Sẵn sàng thực hiện** | Phụ thuộc hoàn tất đồng bộ tài liệu (Toàn bộ 7 bước trước đã hoàn tất). |

---

## 12. Overall Readiness Assessment

| Hạng mục Đánh giá | Mức độ Sẵn sàng | Căn cứ Kết luận |
| :--- | :---: | :--- |
| **1. Use Case (Diagram & Spec)** | **✅ Fully Ready (Sẵn sàng 100%)** | Đã hoàn thành Bước 1 & Bước 6: 28/28 Use Cases đạt chuẩn Cockburn Size Test và đủ 7 mục theo ISO/IEC/IEEE 29148:2018 (`docs/uml/use-case-specifications.md`); đã xóa OTP/SSO ở `srs-v1.3.md` (§7.1); đã sửa quy tắc EDF ở `UC-26`; đã khai báo đầy đủ Extension Points cho `UC-14`, `UC-19`, `UC-23`. |
| **2. Database Design** | **✅ Fully Ready (Sẵn sàng 100%)** | Đã hoàn thành Bước 2 & Bước 3: `schema.sql` v3.1 (28 bảng, 52 index) đã vượt qua 100% bài kiểm thử cú pháp DDL & ràng buộc positive/negative trên PostgreSQL 16 container; toàn bộ 4 tài liệu CSDL phái sinh (`schema.dbml`, `database-schema.puml`, `database-schema-design.md`, `data-dictionary.md`) đã đồng bộ 100%. |
| **3. Class Diagram** | **✅ Fully Ready (Sẵn sàng 100%)** | Đã hoàn thành Bước 4 & Bước 5: `class-diagram.puml` (69 classifiers) và tài liệu `class-diagrams.md` đã đồng bộ hoàn hảo: `LearningConcept` chuyển sang Global Knowledge Base, `StudyNote` sửa bội số `0..1`, `LearnerProfile` cập nhật 4 chỉ số thực chứng, `OfficialSchedule`, `TaskDependency` DAG, và 35 Enums khớp 1-1 với CSDL. |
| **4. Cross-Artifact Consistency** | **✅ Fully Ready (Sẵn sàng 100%)** | Đã hoàn thành Bước 7: Toàn bộ 10 tài liệu ADR (`ADR-001..010`), `README.md`, `SRS v1.3`, `schema.sql` v3.1, và `use-case-specifications.md` đạt tính nhất quán tuyệt đối 1-1 (0 mâu thuẫn kiến trúc, 0 liên kết tuyệt đối, 0 mã ma). |

---

## 13. Review Limitations

1. **Giới hạn về Sơ đồ Hình ảnh (`.png`) và `.drawio`**: Đã kiểm tra cấu trúc XML của toàn bộ các file `.drawio` để phát hiện độ lệch số lượng phần tử và kết nối so với `.puml`; không đánh giá thẩm mỹ bố cục thị giác (layout/màu sắc) của file ảnh xuất ra.
2. **Giới hạn về Source Code**: Theo đúng quy tắc mục 2.4 và xác nhận của người dùng, source code trong `backend/src/` và `backend/alembic/` chỉ được đọc ở tầng ORM models và migrations để đối chiếu mức độ đồng bộ schema, không thực hiện review code logic tầng Application/Presentation hay Frontend UI.

---

## PHỤ LỤC: BẢNG ĐỐI CHIẾU TRẠNG THÁI VỚI BÁO CÁO REVIEW CŨ

*(Thực hiện sau khi hoàn tất rà soát độc lập theo đúng lựa chọn của người dùng: đối chiếu với `Báo cáo đánh giá toàn diện Use Case và Class Diagram — FocusFlow.md` và `docs/mentor-alignment-and-gap-report.md`)*

| Mã Finding Cũ | Nội dung trong Báo cáo cũ | Trạng thái Hiện tại | Đối chiếu Chi tiết trên Repo Hiện tại |
| :---: | :--- | :---: | :--- |
| **U1** | `UC-17` (nay là `UC-23`) ghi thẳng vào lịch, bỏ qua cổng kiểm duyệt 3 tầng, mâu thuẫn `BUSR-02`/`BUSR-03`. | **⚠️ Đã xử lý ở SRS/UC/ADR-009, nhưng CÒN SÓT ở `ADR-004`** | `SRS v1.3`, `UC-23` và `ADR-009`/`010` đã sửa chuẩn (`ScheduleProposal(DRAFT)` + `<<include>> UC-12`), **nhưng `ADR-004` Dòng 67 vẫn còn ghi "bỏ qua Cổng Kiểm duyệt 3 Tầng"** $\rightarrow$ Ghi nhận tại **`[X-03]`**. |
| **U2** | `<<extend>>` sai ở Lập lịch thủ công và Gián đoạn phiên học. | **✅ Đã xử lý triệt để** | `UC-09` đã thành UC độc lập; tự động chốt phiên tách thành `UC-16` do `ACT-03 (System Scheduler)` kích hoạt; thêm `UC-15 (MVS) <<extend>> UC-14` hợp lệ. |
| **U3** | `UC-04 <<include>> UC-05` sai ngữ nghĩa UML. | **✅ Đã xử lý triệt để** | Đã bỏ `<<include>>` trên `.puml`; `UC-05` tách thành UC độc lập do `ACT-06 (Payment Gateway)` khởi xướng. (Chỉ còn sót trên file cũ `UC_Master.drawio` $\rightarrow$ **`[UC-05]`**). |
| **U4** | Thiếu actor `System Scheduler` và `Email Notification Service`. | **✅ Đã xử lý triệt để** | Đã bổ sung `ACT-03` và `ACT-07` cùng 3 UC hệ thống (`UC-06`, `UC-16`, `UC-25`). |
| **U5** | UC gộp nhiều mục tiêu; cần tách thành 24–28 UC. | **✅ Đã xử lý triệt để** | Đã chuẩn hóa thành **28 Use Cases (`UC-01..UC-28`)**. Tuy nhiên quá trình tách làm phát sinh lỗi cắt cụt đặc tả ở `UC-13..UC-28` (`[UC-01]`) và lệch đánh số `UC-15..24` trong `class-diagrams.md` (`[X-05]`). |
| **U6** | Diagram thiếu association từ `Learner` tới một số UC; Đối soát thanh toán thiếu nối `Payment Gateway`. | **⚠️ Đã xử lý trên `.puml`, còn lệch nhẹ ở Bảng & `.drawio`** | `.puml` đã nối đủ `Learner` và `UC27 -- PayGateway`; còn lệch khai báo Actor phụ `LLM` của `UC-14` giữa bảng và `.puml` (`[UC-04]`) và `UC_Master.drawio` cũ (`[UC-05]`). |
| **U7** | Rò rỉ chi tiết thiết kế (`HMAC-SHA256`, `SHA-256`, `Fernet`, tên bảng/cột) vào kịch bản chính của UC spec. | **🔴 Còn mở ở `UC-13..UC-28`** | `UC-01..UC-12` đã chuyển chi tiết kỹ thuật xuống mục Ghi chú kỹ thuật, nhưng `UC-13..UC-28` vẫn viết thẳng tên bảng/cột/thuật toán vào `Luồng chính` $\rightarrow$ **`[UC-06]`**. |
| **U8** | Mâu thuẫn hành vi sau 2 lần retry AI vi phạm giữa `FR-PLAN-005`, `FR-AI-001` và `ADR-009`. | **✅ Đã xử lý triệt để** | Đã thống nhất hủy thao tác, `RELEASE` reservation và gợi ý chỉnh tay/thử lại. |
| **U9** | Lưu trữ lộ trình (`UC-10`) không có FR riêng trong SRS. | **✅ Đã xử lý triệt để** | `SRS v1.3` đã bổ sung **`FR-PLAN-006: Quản lý Danh mục Lộ trình và Lưu trữ`**. |
| **U10** | Ký tự lạ tiếng Hàn/Ả Rập (`المục`, `thời점`, `kiểm증`) và link cứng `file:///Users/vuthang/...`. | **⚠️ Đã xóa hết ký tự lạ, còn 1 link cứng** | Toàn bộ ký tự Hàn/Ả Rập đã được xóa sạch (`0` kết quả); chỉ còn sót 1 link `file:///Users/vuthang/...` ở `database-schema-design.md` Dòng 1223 $\rightarrow$ **`[X-08]`**. |
| **C1** | Lệch trạng thái thanh toán (`EXPIRED` vs `REFUNDED`), nơi lưu OAuth token, tên bảng giữa SRS, ADR, Class, DB. | **⚠️ Đã tách `calendar_connections`, nhưng CÒN MỞ lỗi `EXPIRED` vs `REFUNDED` ở `schema.sql`** | Đã tách bảng `calendar_connections` và xóa tên bảng ma; nhưng `schema.sql` vẫn giữ `'REFUNDED'` và thiếu cột `expires_at` ở `payment_transactions` $\rightarrow$ **`[DB-01]`**, cùng 10 Enum khác lệch giữa `.puml` và `schema.sql` $\rightarrow$ **`[X-04]`**. |
| **C2** | Class diagram vẽ association trực tiếp xuyên Bounded Context, vi phạm `ADR-001` và `ADR-007`. | **✅ Đã xử lý triệt để** | `class-diagram.puml` đã thay toàn bộ Association xuyên package bằng 25 đường `..> : <<ref>>`. |
| **C3** | Quan hệ dư `Goal 1..* Roadmap`, `Roadmap 1 -- * StudySession`. | **✅ Đã xử lý trên Class Diagram, còn thiếu `UNIQUE` ở DB** | Đã sửa thành `Goal "1" -- "0..1" Roadmap` trên `class-diagram.puml`, nhưng `schema.sql` còn thiếu `UNIQUE (goal_id)` trên bảng `roadmaps` $\rightarrow$ **`[DB-05]`**. |
| **C4** | Dùng sai Composition/Aggregation ở `Roadmap *-- ScheduleChangeLog` và `OfficialSchedule o-- Task`. | **✅ Đã xử lý (nhưng còn `StudySession "1" *-- StudyNote`)** | Đã sửa 2 quan hệ cũ; chỉ còn bội số `"1"` trên `StudySession "1" *-- "0..*" StudyNote` và `Task "1" -- "0..*" StudyNote` mâu thuẫn với `sessionId [0..1]`, `taskId [0..1]` $\rightarrow$ **`[CLS-02]`**. |
| **C5** | Trách nhiệm trùng lặp giữa Entity và Domain Service; thiếu lớp `ProposedTask`. | **✅ Đã xử lý triệt để** | Đã bổ sung Value Object `ProposedTask` và phân bổ rõ 4 `<<domainService>>`. |
| **C6** | Đưa `OutboxEvent` và `ProcessedEvent` (hạ tầng) vào Class Diagram miền. | **✅ Đã xử lý triệt để** | Đã loại bỏ khỏi `class-diagram.puml` và giải thích rõ tại §6.2 của `class-diagrams.md`. |
| **C7** | `User *-- LearnerProfile` có bội số `0..1` thay vì `1`; Mermaid thiếu Enum. | **✅ Đã xử lý triệt để** | Đã sửa thành `User "1" *-- "1" LearnerProfile` và cập nhật Mermaid §3.2 đủ 69 classifiers. |
