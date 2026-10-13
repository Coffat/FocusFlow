# FocusFlow — Cẩm nang Hướng dẫn Sử dụng Bộ Prompts Kỹ thuật & Pipeline 8 Bước

## Thông tin Tài liệu
* **Dự án:** FocusFlow — Hệ thống hỗ trợ lập kế hoạch và thực thi lộ trình tự học thích ứng tích hợp AI
* **Phiên bản:** v1.0 — Chuẩn Thực thi Công nghệ Phần mềm (SE Execution Baseline)
* **Bộ kỹ năng tích hợp:** 8 Skills tiếng Việt tại `.agents/skills/`
* **Mục đích:** Cung cấp hướng dẫn chi tiết về **thời điểm sử dụng**, **điều kiện tiên quyết**, **prompt chuẩn để sao chép** và **kết quả kỳ vọng** cho từng giai đoạn thiết kế hệ thống.

---

## 1. Sơ đồ Pipeline 8 Bước Thực thi Chuẩn (The 8-Step Pipeline)

Để đảm bảo tính nhất quán tối đa và tránh việc phải làm lại (rework), các giai đoạn kỹ thuật trong FocusFlow bắt buộc phải tuân theo thứ tự phụ thuộc dữ liệu logic dưới đây:

```
REQUIREMENTS (SRS v1.1)
       │
       ▼
[Bước 1: STATE MACHINE] (Vòng đời Roadmap, Task, Session, Proposal)
       │
       ▼
[Bước 2: PHYSICAL DB DIAGRAM] (Physical Database Schema Diagram - Crow's Foot)
       │
       ▼
[Bước 3: DATABASE SCHEMA] (Data Dictionary, Constraint Matrix, Index Matrix)
       │
       ▼
[Bước 4: SEQUENCE DIAGRAM] (Runtime Interaction: M2, Overdue Shift, WebCal)
       │
       ▼
[Bước 5: SOFTWARE ARCHITECTURE] (arc42: 12 Sections, Quality Attributes)
       │
       ▼
[Bước 6: C4 & COMPONENT] (Context -> Container -> Component -> Ports & Adapters)
       │
       ▼
[Bước 7: ADR GOVERNANCE] (Ghi nhận các quyết định kiến trúc cốt lõi)
       │
       ▼
[Bước 8: CROSS-ARTIFACT AUDIT] (Kiểm tra chéo toàn diện 9 mắt xích)
```

### Bảng tóm tắt Thứ tự Pipeline

| Bước | Tên Giai đoạn / Tác vụ | Skill Tương ứng | Đầu ra Chính |
|:---:|---|---|---|
| **1** | Mô hình hóa Máy trạng thái | `thiet-ke-state-machine` | Biểu đồ State Machine + Bảng chuyển trạng thái của 4 thực thể cốt lõi |
| **2** | Thiết kế Mô hình Dữ liệu | `thiet-ke-mo-hinh-co-so-du-lieu` | Sơ đồ Physical Database Schema Diagram (DB Diagram Crow's Foot), Chuẩn hóa 3NF/BCNF |
| **3** | Quản trị Lược đồ CSDL | `quan-tri-schema-co-so-du-lieu` | Data Dictionary chi tiết, Ma trận Ràng buộc, Ma trận Chỉ mục Hiệu năng |
| **4** | Thiết kế Biểu đồ Tuần tự | `thiet-ke-sequence-diagram` | Sequence Diagrams cho Workflow M2, Overdue Shift và WebCal Feed |
| **5** | Thiết kế Kiến trúc Hệ thống | `thiet-ke-kien-truc-phan-mem` | Hồ sơ kiến trúc tổng thể theo cấu trúc 12 phần chuẩn arc42 |
| **6** | Mô hình hóa C4 & Component | `thiet-ke-c4-component` | C4 Context, C4 Container, C4 Component cho Backend Hexagonal |
| **7** | Quản trị Quyết định Kiến trúc | `architecture-decision-record` | Danh mục ADRs (ADR-001 đến ADR-NNN) giải trình đánh đổi kỹ thuật |
| **8** | Audit Tính Nhất quán Toàn diện | `kiem-tra-nhat-quan-tai-lieu` | Ma trận nhất quán 9 mắt xích, danh mục mâu thuẫn & Remediation Plan |

---

## 2. Chi tiết Từng Prompt Thực thi & Hướng dẫn Sử dụng

---

### Bước 1: Thiết kế State Machine Diagram (Vòng đời Trạng thái)

* **Skill liên kết:** `thiet-ke-state-machine`
* **Khi nào sử dụng:** 
  * Sử dụng ngay sau khi đóng băng SRS và trước khi chốt chi tiết Database Schema hoặc Sequence Diagram.
  * Khi cần chuẩn hóa vòng đời chuyển đổi trạng thái của các thực thể cốt lõi: Roadmap, Task, Study Session, Schedule Proposal.
  * Khi cần làm rõ điều kiện kích hoạt (Trigger), rào chắn (Guard) và hành động (Action) để tránh tạo ra các trạng thái "bẫy" (Trap state) hoặc trạng thái không thể chạm tới (Dead state).
* **Điều kiện tiên quyết / Đầu vào:**
  * [`docs/srs/srs-v1.0.md`](file:///Users/vuthang/Documents/FocusFlow/docs/srs/srs-v1.0.md) (Mục 6: State Transition Rules).
  * [`docs/requirements/problem-definition.md`](file:///Users/vuthang/Documents/FocusFlow/docs/requirements/problem-definition.md) (Mục 5.3, 5.4).
* **Đầu ra kỳ vọng:**
  * File biểu đồ PlantUML / Mermaid cho từng thực thể.
  * Bảng ma trận chuyển trạng thái (State Transition Table) kèm các bất biến vòng đời (Lifecycle Invariants).
  * Danh sách chuyển trạng thái hợp lệ và không hợp lệ (Invalid Transitions).

#### Prompt sao chép (Copyable Prompt):

```text
Sử dụng skill `thiet-ke-state-machine`. 

Thiết kế và kiểm tra UML 2.5.1 State Machine cho:
1. Roadmap
2. Task
3. Session
4. Proposal

Trước tiên đọc:
- Requirements
- SRS
- Use Cases
- Domain Model
- Database Schema
- Database Status/Enum
- Sequence Diagram
- Architecture
- ADR

Không tự suy đoán lifecycle. Với mỗi Entity hãy xác định:
- Initial State
- Các State
- Terminal State
- Event
- Trigger
- Guard
- Action
- Transition
- Invalid Transition

Tạo:
A. State Machine Diagram
B. Bảng State Transition
C. Valid Transitions
D. Invalid Transitions
E. Lifecycle Invariants

Sau đó kiểm tra sự phụ thuộc giữa:
Roadmap → Task → Session
và:
Proposal → Roadmap/Task/Schedule

Nếu phát hiện State Machine mâu thuẫn với Database hoặc Requirements: KHÔNG tự sửa. Báo cáo mâu thuẫn trước.
```

---

### Bước 2: Thiết kế Mô hình Cơ sở Dữ liệu (Physical Database Schema Diagram & Relational Model)

* **Skill liên kết:** `thiet-ke-mo-hinh-co-so-du-lieu`
* **Khi nào sử dụng:**
  * Sử dụng sau khi đã xác định rõ các thực thể miền và vòng đời trạng thái ở Bước 1.
  * Khi cần chuẩn hóa mô hình dữ liệu vật lý theo chuẩn của Giảng viên hướng dẫn: không dùng ERD khái niệm hình thoi (Chen notation) mà dùng **Physical Database Schema Diagram (DB Diagram)** phản ánh đúng PostgreSQL 16.
  * Khi cần xác định chính xác các quan hệ 1:1, 1:N, N:M (phân rã thành junction table), chỉ định rõ PK (`UUID`), FK, kiểu dữ liệu chuẩn và chuẩn hóa 3NF/BCNF.
* **Điều kiện tiên quyết / Đầu vào:**
  * SRS v1.1, Domain Model, State Machine Diagrams đã hoàn thành ở Bước 1.
* **Đầu ra kỳ vọng:**
  * Sơ đồ Physical Database Schema Diagram (DB Diagram) chuẩn Crow's Foot (Mermaid và DBML cho `dbdiagram.io`).
  * Báo cáo phân tích chuẩn hóa dữ liệu 3NF/BCNF (giải trình các trường hợp denormalization nếu có như JSONB).
  * Danh mục khóa chính (PK), khóa ngoại (FK), ràng buộc toàn vẹn tham chiếu.

#### Prompt sao chép (Copyable Prompt):

```text
Sử dụng skill `thiet-ke-mo-hinh-co-so-du-lieu`. 

Thiết kế và audit Database Model của FocusFlow. 

Đọc trước:
- Requirements
- SRS
- Use Cases
- Domain Model
- State Machines
- Database hiện tại
- Migration
- Entity/Model
- Repository
- API Contract nếu liên quan

Thực hiện theo thứ tự:
1. Conceptual Data Model
2. Logical ER Model
3. Relational Schema
4. Physical PostgreSQL Schema

Với mỗi Entity xác định:
- mục đích
- Primary Key
- Candidate Key nếu có
- Attribute
- Foreign Key
- Relationship
- Cardinality
- Optionality

Phân tích Normalization đến ít nhất 3NF. Tìm:
- Partial Dependency
- Transitive Dependency
- Update Anomaly
- Insert Anomaly
- Delete Anomaly
- Unnecessary Duplication

Kiểm tra:
- PK
- FK
- NOT NULL
- UNIQUE
- CHECK
- Referential Integrity

Không tự ý thay đổi Database nếu việc thay đổi có thể mâu thuẫn với Requirements hoặc ADR đã được chấp thuận. Báo cáo mâu thuẫn trước.
```

---

### Bước 3: Quản trị Lược đồ Cơ sở Dữ liệu (Data Dictionary, Indexes & Constraints)

* **Skill liên kết:** `quan-tri-schema-co-so-du-lieu`
* **Khi nào sử dụng:**
  * Sử dụng ngay sau khi mô hình quan hệ ở Bước 2 hoàn thành, trước khi viết mã migration hoặc truy vấn backend.
  * Khi cần xây dựng tài liệu Từ điển dữ liệu (Data Dictionary) chi tiết phục vụ báo cáo Đồ án tốt nghiệp và bàn giao kỹ thuật.
  * Khi cần thiết lập Ma trận Ràng buộc (Constraint Matrix) để bảo vệ toàn vẹn dữ liệu ở cấp CSDL và Ma trận Chỉ mục (Index Matrix) dựa trên mẫu truy vấn thực tế.
* **Điều kiện tiên quyết / Đầu vào:**
  * Sơ đồ Physical Database Schema Diagram (DB Diagram), Database Schema DDL (`schema.sql`), ORM Models (SQLAlchemy 2.0).
* **Đầu ra kỳ vọng:**
  * File Data Dictionary đầy đủ từng bảng/cột, kiểu dữ liệu, nullability, default, ý nghĩa và rule liên kết.
  * Ma trận Constraint (PK, FK, UK, CHECK, NOT NULL) kèm giải trình invariant được bảo vệ.
  * Ma trận Index (loại index, query pattern hỗ trợ, phân tích overhead ghi).
  * Báo cáo phát hiện Documentation Drift.

#### Prompt sao chép (Copyable Prompt):

```text
Sử dụng skill `quan-tri-schema-co-so-du-lieu`. 

Audit toàn bộ Database Schema của FocusFlow. 

Đọc Database Definition/Migration/Entity thực tế trước. 

Tạo hoặc cập nhật:
1. Data Dictionary
2. Constraint Matrix
3. Index Matrix

Với mỗi Table/Column ghi:
- ý nghĩa
- Data Type
- Nullable
- Default
- PK
- FK
- UNIQUE
- CHECK
- Allowed Values
- Business Rule

Với mỗi Index ghi:
- Table
- Columns
- Index Type
- Unique/Non-Unique
- Query Pattern được hỗ trợ
- Redundancy
- Write Overhead

Không tạo Index dựa trên lời khuyên chung chung. Hãy dựa trên:
- Repository
- Query
- API
- Use Case
- Access Pattern

Cuối cùng đối chiếu:
Physical Database Schema Diagram (DB Diagram) → Migration → Entity → Repository → Data Dictionary

Báo cáo mọi điểm không nhất quán.
```

---

### Bước 4: Thiết kế Biểu đồ Tuần tự (Runtime Interaction / Sequence Diagrams)

* **Skill liên kết:** `thiet-ke-sequence-diagram`
* **Khi nào sử dụng:**
  * Sử dụng sau khi đã có vòng đời trạng thái (Bước 1) và mô hình dữ liệu (Bước 2, 3).
  * Khi cần mô hình hóa tương tác theo dòng thời gian giữa Actor, UI, Controller, Use Case, Domain Service, Adapters, CSDL và External APIs.
  * Được chia thành 3 kịch bản trọng yếu của FocusFlow: **Workflow M2**, **Overdue Shift** và **WebCal Feed**.

---

#### Kịch bản 4A: Workflow M2 (Khởi tạo Lộ trình 2 Cấp độ & Phê duyệt Lịch)

* **Khi nào sử dụng:** Khi thiết kế hoặc rà soát luồng người dùng tạo mục tiêu, làm rõ ngữ cảnh, phê duyệt Cột mốc (Cấp 1), sinh Đề xuất Lịch trình (Cấp 2) và kích hoạt Lịch chính thức qua Backend Validation Gate.

```text
Sử dụng skill `thiet-ke-sequence-diagram`. 

Hãy thiết kế và kiểm tra UML 2.5.1 Sequence Diagram cho workflow M2 của FocusFlow. 

Trước khi chỉnh sửa:
1. Đọc Requirements hiện tại.
2. Đọc SRS.
3. Đọc Use Case liên quan đến M2.
4. Đọc kiến trúc hiện tại.
5. Đọc Database Model nếu workflow có lưu dữ liệu.
6. Đọc các Diagram hiện có để giữ nguyên thuật ngữ và quy ước.

Mô hình hóa đầy đủ:
- Actor khởi tạo
- Các Lifeline liên quan
- Luồng thành công
- Luồng thay thế
- Luồng lỗi
- Validation
- Business Logic
- Database Operation
- User Review/Confirmation nếu có
- External System nếu có
- Asynchronous Operation nếu thực sự tồn tại

Sử dụng đúng UML:
- alt
- opt
- loop
- par
- guard

Không tự tạo behavior, API, database table hoặc service chưa được định nghĩa. 

Nếu Requirements, SRS, Architecture và Database Model mâu thuẫn: KHÔNG tự sửa. Hãy báo cáo:
- mâu thuẫn nằm ở đâu
- bằng chứng
- ảnh hưởng
- tài liệu liên quan

Sau khi hoàn thành, kiểm tra Sequence Diagram với:
Requirements → SRS → Use Case → Architecture → Database Model.

Báo cáo chính xác những file đã tạo/chỉnh sửa.
```

---

#### Kịch bản 4B: Workflow Overdue Shift (Phát hiện Quá hạn & Tịnh tiến Lịch)

* **Khi nào sử dụng:** Khi thiết kế quy trình xử lý tác vụ quá hạn định kỳ, chạy qua thuật toán tất định thuần backend `task.status != COMPLETED AND task.scheduled_date < TODAY` (`BUSR-06`) và cơ chế tịnh tiến Domino Shift (`BUSR-07`).

```text
Sử dụng skill `thiet-ke-sequence-diagram`. 

Thiết kế UML 2.5.1 Sequence Diagram cho workflow Overdue Shift của FocusFlow. 

Trước tiên hãy tìm hiểu từ tài liệu hiện tại:
- Overdue được định nghĩa như thế nào?
- Task/Session nào được xem là quá hạn?
- Ai hoặc hệ thống nào phát hiện quá hạn?
- Quy tắc dịch chuyển lịch là gì?
- Có phát hiện xung đột lịch không?
- Có cần người dùng xác nhận không?
- Dữ liệu nào được cập nhật?
- Có Notification hay External Integration không?

Không tự suy đoán. 

Sequence Diagram phải thể hiện:
1. Trigger
2. Phát hiện quá hạn
3. Kiểm tra Business Rules
4. Tính toán đề xuất thay đổi
5. Phát hiện Conflict nếu có
6. Người dùng xem/xác nhận nếu yêu cầu quy định
7. Cập nhật dữ liệu
8. Notification/Integration nếu có

Sử dụng `alt`, `opt`, `loop`, `par` đúng ngữ nghĩa UML. 

Sau khi hoàn thành, kiểm tra với:
- Requirements
- State Machine
- Architecture
- Database Model

Báo cáo mọi mâu thuẫn.
```

---

#### Kịch bản 4C: Workflow WebCal Feed (Tích hợp Lịch Ngoại vi 1 Chiều)

* **Khi nào sử dụng:** Khi mô hình hóa quy trình ứng dụng lịch bên ngoài (Google Calendar, Apple Calendar, Outlook) truy vấn luồng lịch 1 chiều qua URL chứa token bảo mật (`RFC 5545`) và cơ chế reset token.

```text
Sử dụng skill `thiet-ke-sequence-diagram`. 

Thiết kế UML 2.5.1 Sequence Diagram cho WebCal Feed của FocusFlow. 

Đầu tiên đọc các Requirements và Architecture liên quan đến WebCal/iCalendar. 

Mô hình hóa:
- Client yêu cầu Calendar Feed
- Authentication/Authorization nếu có
- Lấy dữ liệu lịch
- Chuyển đổi dữ liệu sang định dạng Calendar
- Tạo iCalendar Feed
- Trả dữ liệu cho Calendar Client
- Error Handling
- Dữ liệu không hợp lệ hoặc không tồn tại nếu Requirements quy định

Phân biệt rõ trách nhiệm của:
- FocusFlow
- Calendar Client
- Database
- External System

Không tự tạo cơ chế đồng bộ hai chiều nếu Requirements không yêu cầu. 

Kiểm tra Diagram với Architecture và Requirements hiện tại.
```

---

### Bước 5: Thiết kế & Rà soát Kiến trúc Phần mềm (Software Architecture theo arc42)

* **Skill liên kết:** `thiet-ke-kien-truc-phan-mem`
* **Khi nào sử dụng:**
  * Sử dụng sau khi đã có hành vi tương tác động (Sequence) và cấu trúc dữ liệu tĩnh (Database).
  * Khi cần soạn thảo hoặc thẩm định toàn diện Tài liệu Thiết kế Kiến trúc Hệ thống (System Architecture Document) theo chuẩn quốc tế arc42 (12 sections).
  * Khi cần chứng minh tính vững chắc của các quyết định kỹ thuật trước Hội đồng bảo vệ đồ án tốt nghiệp.
* **Điều kiện tiên quyết / Đầu vào:**
  * Problem Definition, SRS v1.1, Domain Model, Sequence Diagrams, Database Schema, ADRs hiện có.
* **Đầu ra kỳ vọng:**
  * Hồ sơ tài liệu kiến trúc arc42 gồm 12 mục hoàn chỉnh.
  * Bảng ánh xạ thuộc tính chất lượng (NFR Mapping Matrix).
  * Phân tích đánh đổi (Trade-off Analysis) và danh mục rủi ro/nợ kỹ thuật.

#### Prompt sao chép (Copyable Prompt):

```text
Sử dụng skill `thiet-ke-kien-truc-phan-mem`. 

Thực hiện thiết kế và rà soát toàn bộ kiến trúc FocusFlow. 

Trước tiên đọc:
- Problem Definition
- Requirements
- SRS
- Use Cases
- Domain Model
- Sequence Diagrams
- State Machine Diagrams
- Database Model
- Database Schema
- ADR
- Source Code nếu cần

Sau đó xây dựng kiến trúc theo tư duy arc42:
1. Introduction & Goals
2. Constraints
3. Context & Scope
4. Solution Strategy
5. Building Block View
6. Runtime View
7. Deployment View
8. Cross-cutting Concepts
9. Architecture Decisions
10. Quality Requirements
11. Risks & Technical Debt
12. Glossary

Không tự ý thay đổi những quyết định mà chủ dự án đã xác nhận. Không tự tạo:
- Service
- Database
- Queue
- Cache
- External System
- Infrastructure
nếu không có bằng chứng từ Requirements, Architecture, Code hoặc ADR.

Nếu phát hiện vấn đề:
- chỉ ra bằng chứng
- chỉ ra ảnh hưởng
- đề xuất phương án
- KHÔNG tự động thay đổi quyết định đã được chấp thuận.
```

---

### Bước 6: Thiết kế Mô hình C4 & Kiến trúc Thành phần (C4 Model & Component Diagram)

* **Skill liên kết:** `thiet-ke-c4-component`
* **Khi nào sử dụng:**
  * Sử dụng để trực quan hóa kiến trúc hệ thống ở các tầng phân rã chi tiết (Context $\rightarrow$ Container $\rightarrow$ Component).
  * Khi cần làm rõ ranh giới phân lớp Kiến trúc Lục giác (Hexagonal Architecture / Ports & Adapters) bên trong Backend API Container.
  * Khi cần kiểm tra vi phạm phụ thuộc (Layer Violations, Circular Dependencies, Infrastructure Leakage).
* **Điều kiện tiên quyết / Đầu vào:**
  * Tài liệu kiến trúc ở Bước 5, cây thư mục mã nguồn (`backend/src/`), danh sách Ports & Adapters.
* **Đầu ra kỳ vọng:**
  * Sơ đồ C4 Context (Mức 1).
  * Sơ đồ C4 Container (Mức 2).
  * Sơ đồ C4 Component cho Backend API Container (Mức 3).
  * Danh mục kiểm tra vi phạm phân lớp (Coupling & Layer Invariants).

#### Prompt sao chép (Copyable Prompt):

```text
Sử dụng skill `thiet-ke-c4-component`. 

Thiết kế và kiểm tra kiến trúc FocusFlow bằng C4 Model. 

KHÔNG tạo Diagram ngay. Trước tiên đọc toàn bộ tài liệu liên quan và xác định:
- System Boundary
- Actors
- External Systems
- Applications
- Containers
- Databases
- Components
- Responsibilities
- Dependencies

Sau đó tạo hoặc rà soát:
1. System Context Diagram
2. Container Diagram
3. Component Diagram cho các Container quan trọng

Nếu hệ thống sử dụng Layered Architecture, xác định rõ:
- Presentation/API
- Application
- Domain
- Infrastructure/Persistence
- External Integration

Kiểm tra:
- Không trộn abstraction level.
- Không có dependency không giải thích được.
- Không có circular dependency.
- Không vi phạm Layer.
- Không có Component trùng trách nhiệm.
- Không tạo Component không có cơ sở.
- Không tạo technology/system không tồn tại.

So sánh Diagram với:
- Source Code
- Requirements
- Architecture
- Database
- Sequence Diagram

Báo cáo mọi mâu thuẫn.
```

---

### Bước 7: Quản trị Bản ghi Quyết định Kiến trúc (Architecture Decision Records - ADR)

* **Skill liên kết:** `architecture-decision-record`
* **Khi nào sử dụng:**
  * Sử dụng khi xuất hiện quyết định kỹ thuật mới (ví dụ: giao thức streaming SSE, chính sách merge lịch OS-03, thuật toán EDF OS-04, chiến lược cookie SameSite/Domain).
  * Khi cần rà soát lại toàn bộ cây thư mục `docs/decisions/` để chuẩn hóa trạng thái (Proposed, Accepted, Superseded).
  * Khi phát hiện quyết định trong mã nguồn hoặc tài liệu không khớp với ADR đã phê duyệt.
* **Điều kiện tiên quyết / Đầu vào:**
  * Toàn bộ tài liệu yêu cầu, kiến trúc, mã nguồn và các file ADR hiện hành trong `docs/decisions/`.
* **Đầu ra kỳ vọng:**
  * Danh sách ADRs hoàn chỉnh, không mâu thuẫn, có cấu trúc đồng bộ.
  * Các file `ADR-NNN-<slug>.md` mới được tạo với đầy đủ ma trận đánh đổi (Trade-offs).
  * Cập nhật danh mục tham chiếu trong `docs/architecture/system-architecture.md`.

#### Prompt sao chép (Copyable Prompt):

```text
Sử dụng skill `architecture-decision-record`. 

Audit toàn bộ Architecture Decision của FocusFlow. 

Đọc:
- Problem Definition
- Requirements
- SRS
- Architecture
- Database Architecture
- ADR hiện có
- Decision Files
- UML liên quan

Xác định các quyết định kiến trúc mà chủ dự án đã thực sự lựa chọn. 

QUAN TRỌNG: Những quyết định đã được chủ dự án xác nhận phải được coi là quyết định đã chấp thuận. Không được thay thế bằng phương án mà AI cho là tốt hơn. 

Với mỗi quyết định quan trọng:
Kiểm tra ADR đã tồn tại chưa. Nếu chưa có, tạo ADR gồm:
- Title
- Status
- Date
- Context
- Decision
- Alternatives Considered
- Decision Criteria
- Consequences
- Related Requirements
- Related ADRs

Không được bịa lý do. Nếu không biết rationale: Ghi rõ: "Rationale chưa được tài liệu hóa."

Kiểm tra:
- ADR mâu thuẫn
- ADR bị thay thế
- ADR trùng lặp
- ADR mâu thuẫn với Architecture hiện tại

Không thay đổi Implementation hoặc Requirements trong task này.
```

---

### Bước 8: Cuộc Audit Toàn diện Tính Nhất quán (Cross-Artifact Consistency Audit)

* **Skill liên kết:** `kiem-tra-nhat-quan-tai-lieu` (kết hợp hỗ trợ từ cả 7 skills trên)
* **Khi nào sử dụng:**
  * **ĐÂY LÀ BƯỚC QUAN TRỌNG NHẤT CỦA TOÀN BỘ DỰ ÁN.**
  * Chạy sau khi đã hoàn thành toàn bộ chuỗi 7 bước thiết kế trên, trước khi bắt tay vào giai đoạn lập trình mã nguồn (Implementation) hoặc trước mỗi đợt nộp báo cáo tiến độ đồ án.
  * Giúp rà soát toàn bộ hệ thống tài liệu kỹ thuật để đảm bảo 100% không có sự lệch pha, mâu thuẫn ngầm hay giả định không có căn cứ.
* **Điều kiện tiên quyết / Đầu vào:**
  * Toàn bộ tài liệu trong `docs/requirements/`, `docs/srs/`, `docs/uml/`, `docs/architecture/`, `docs/database/`, `docs/decisions/`.
* **Đầu ra kỳ vọng:**
  * Ma trận Truy vết Toàn diện (Comprehensive Traceability Matrix) qua 9 mắt xích.
  * Danh sách Mâu thuẫn (Contradictions) phân loại theo mức độ nghiêm trọng (Critical, High, Medium, Low).
  * Kế hoạch Khắc phục (Remediation Plan) chi tiết từng bước.
  * **Lưu ý: Không tự ý sửa file khi chưa được người dùng phê duyệt kế hoạch.**

#### Prompt sao chép (Copyable Prompt):

```text
Sử dụng các skill phù hợp:
- `thiet-ke-sequence-diagram`
- `thiet-ke-state-machine`
- `thiet-ke-kien-truc-phan-mem`
- `thiet-ke-c4-component`
- `thiet-ke-mo-hinh-co-so-du-lieu`
- `quan-tri-schema-co-so-du-lieu`
- `architecture-decision-record`
- `kiem-tra-nhat-quan-tai-lieu`

Hãy thực hiện một cuộc audit toàn diện cho mô hình kỹ thuật của FocusFlow. 

KHÔNG chỉnh sửa file ngay. 

Trước tiên đọc toàn bộ:
- Problem Definition
- Requirements
- SRS
- Use Cases
- Domain Model
- Sequence Diagrams
- State Machine Diagrams
- Architecture
- C4 Diagrams
- Database Architecture
- Physical Database Schema Diagram (DB Diagram)
- Database Schema
- Data Dictionary
- Indexes
- Constraints
- ADR

Xây dựng chuỗi Traceability:
Requirement → Use Case → Domain Entity → State Machine → Sequence Diagram → Architecture Component → Database Entity → Database Constraint → ADR

Tìm:
- Contradiction
- Missing Information
- Terminology Drift
- Unsupported Assumption
- Architecture Inconsistency
- Database Inconsistency
- UML Inconsistency
- ADR Inconsistency
- Missing Traceability

Với mỗi vấn đề ghi:
1. Artifact
2. Vấn đề
3. Bằng chứng
4. Ảnh hưởng
5. Mức độ nghiêm trọng
6. Đề xuất xử lý
7. Các Artifact bị ảnh hưởng

KHÔNG tự động sửa. Sau khi audit xong, tạo Remediation Plan theo thứ tự ưu tiên. Chỉ thực hiện Remediation khi tôi xác nhận.
```

---

## 3. Quy tắc Dùng Từ Ngữ & Thuật ngữ Chuyên ngành

Khi viết tài liệu luận văn hoặc giao tiếp kỹ thuật với Antigravity, **luôn giữ thuật ngữ chuyên ngành tiếng Anh chuẩn quốc tế trong ngoặc đơn bên cạnh tiếng Việt** để đảm bảo:
1. Giảng viên và Hội đồng đánh giá cao tính học thuật chuẩn mực.
2. AI Agent (Antigravity) nhận diện chính xác các khái niệm lập trình và mẫu thiết kế mà không bị dịch sai ngữ cảnh.

### Bảng Thuật ngữ Đối chiếu Chuẩn:

| Thuật ngữ Tiếng Việt | Thuật ngữ Tiếng Anh Chuẩn (OMG / arc42 / ISO) |
|---|---|
| Sơ đồ Trình tự / Biểu đồ Tuần tự | **Sequence Diagram** (UML 2.5.1) |
| Sơ đồ Máy trạng thái | **State Machine Diagram** (UML 2.5.1) |
| Sơ đồ Thành phần | **Component Diagram** (UML 2.5.1) |
| Sơ đồ Lược đồ CSDL Vật lý (thay thế ERD khái niệm) | **Physical Database Schema Diagram / DB Diagram** (Crow's Foot, ISO/IEC 9075) |
| Mô hình C4 | **C4 Model** (Context, Container, Component, Code) |
| Khung Tài liệu Kiến trúc Hệ thống | **arc42 Architecture Template** |
| Bản ghi Quyết định Kiến trúc | **Architecture Decision Record (ADR)** |
| Từ điển Dữ liệu | **Data Dictionary** |
| Ma trận Ràng buộc | **Constraint Matrix** |
| Ma trận Chỉ mục | **Index Matrix** |
| Bất biến Nghiệp vụ | **Business Invariant** |
| Hiện tượng Lệch pha Tài liệu | **Documentation Drift** |
| Kiến trúc Lục giác / Cổng và Bộ điều hợp | **Hexagonal Architecture / Ports & Adapters** |
| Chuẩn hóa Dữ liệu | **Database Normalization (1NF, 2NF, 3NF, BCNF)** |
| Tác nhân Con người / Hệ thống ngoài | **Human Actor / External System** |
