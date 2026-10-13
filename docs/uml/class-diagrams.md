# FocusFlow — Tài liệu Thiết kế Biểu đồ Lớp UML (Class Diagrams Document)

**Dự án:** FocusFlow — Hệ thống hỗ trợ lập kế hoạch và thực thi lộ trình tự học thích ứng tích hợp AI  
**Tiêu chuẩn kỹ thuật:** OMG UML 2.5.1 Superstructure, Craig Larman (*Applying UML and Patterns*), Martin Fowler (*UML Distilled*)  
**Căn cứ đánh giá học thuật:** Khung Rubric Đồ án Tốt nghiệp CNTT — Tiêu chí TC1 & TC2.1 & TC2.3 (Mức 5)  
**Tài liệu liên kết nguồn:**
- Đặc tả yêu cầu phần mềm: [`docs/srs/srs-v1.0.md`](file:///Users/vuthang/Documents/FocusFlow/docs/srs/srs-v1.0.md)
- Sơ đồ Ca sử dụng: [`docs/uml/use-cases/use-case-diagram.puml`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/use-cases/use-case-diagram.puml) | [`docs/uml/use-case-specifications.md`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/use-case-specifications.md) (20 Use Cases)
- Sơ đồ Tuần tự: [`docs/uml/sequence-diagrams.md`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/sequence-diagrams.md) (9 sơ đồ chi tiết)
- Máy trạng thái thực thể: [`docs/uml/state-machines.md`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/state-machines.md) (4 máy trạng thái)
- Thiết kế Cơ sở dữ liệu: [`docs/database/database-schema-design.md`](file:///Users/vuthang/Documents/FocusFlow/docs/database/database-schema-design.md) & [`docs/database/schema.sql`](file:///Users/vuthang/Documents/FocusFlow/docs/database/schema.sql)

---

## MỤC LỤC
1. [Phân định Góc nhìn Thiết kế theo Chuẩn Craig Larman](#1-phân-định-góc-nhìn-thiết-kế-theo-chuẩn-craig-larman)
2. [Phần I: Mô hình Miền Nghiệp vụ (Domain Model / Conceptual Class Diagram)](#2-phần-i-mô-hình-miền-nghiệp-vụ-domain-model--conceptual-class-diagram)
   - [2.1. Bản vẽ Sơ đồ Miền](#21-bản-vẽ-sơ-đồ-miền)
   - [2.2. Đặc tả 13 Khái niệm Miền Cốt lõi](#22-đặc-tả-13-khái-niệm-miền-cốt-lõi)
   - [2.3. Ma trận Quan hệ Phân cấp & Bản số](#23-ma-trận-quan-hệ-phân-cấp--bản-số)
3. [Phần II: Sơ đồ Lớp Thiết kế Chi tiết (Design Class Diagram - DCD)](#3-phần-ii-sơ-đồ-lớp-thiết-kế-chi-tiết-design-class-diagram---dcd)
   - [3.1. Bản vẽ Sơ đồ Lớp Thiết kế](#31-bản-vẽ-sơ-đồ-lớp-thiết-kế)
   - [3.2. Trích xuất Phương thức từ Sequence Diagrams](#32-trích-xuất-phương-thức-từ-sequence-diagrams)
   - [3.3. Các Dịch vụ Miền (Domain Services - GRASP Pure Fabrication)](#33-các-dịch-vụ-miền-domain-services---grasp-pure-fabrication)
   - [3.4. Áp dụng Nguyên tắc Thiết kế GRASP & SOLID](#34-áp-dụng-nguyên-tắc-thiết-kế-grasp--solid)
4. [Phần III: Ma trận Truy vết Toàn diện (Traceability Matrix)](#4-phần-iii-ma-trận-truy-vết-toàn-diện-traceability-matrix)

---

## 1. Phân định Góc nhìn Thiết kế theo Chuẩn Craig Larman

Theo giáo trình kỹ thuật phần mềm kinh điển của **Craig Larman** (*Applying UML and Patterns*) và **Martin Fowler** (*UML Distilled*), để đảm bảo tính kỷ luật và mạch lạc trong đồ án tốt nghiệp CNTT, hệ thống FocusFlow phân tách rõ ràng hai góc nhìn biểu đồ lớp:

```
[Khảo sát Yêu cầu & Use Cases]
            │
            ▼
┌───────────────────────────────────────────────┐
│  Góc nhìn 1: DOMAIN MODEL (Mô hình Miền)       │
│  - Trực quan hóa khái niệm bài toán thực tế   │
│  - Chỉ gồm Tên lớp + Thuộc tính (2 ngăn)      │
│  - TUYỆT ĐỐI KHÔNG CÓ PHƯƠNG THỨC             │
└───────────────────────┬───────────────────────┘
                        │ + Phân tích Động (Sequence Diagrams)
                        │ + Nguyên tắc Trách nhiệm GRASP / SOLID
                        ▼
┌───────────────────────────────────────────────┐
│  Góc nhìn 2: DESIGN CLASS DIAGRAM (DCD)       │
│  - Mô hình hóa cấu trúc phần mềm thực tế      │
│  - Đầy đủ 3 ngăn: Tên, Thuộc tính (-), Hàm (+)│
│  - Phương thức trích xuất từ Sequence Diagram │
│  - Bổ sung Domain Services xử lý nghiệp vụ    │
└───────────────────────────────────────────────┘
```

---

## 2. Phần I: Mô hình Miền Nghiệp vụ (Domain Model / Conceptual Class Diagram)

### 2.1. Bản vẽ Sơ đồ Miền
* **File nguồn PlantUML:** [`docs/uml/class-diagrams/domain-model.puml`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/class-diagrams/domain-model.puml)
* **Bản render xuất sẵn:** [[Bản vẽ PNG]](file:///Users/vuthang/Documents/FocusFlow/docs/uml/images/FocusFlow_Domain_Model.png)

```mermaid
classDiagram
    direction TB
    title FocusFlow — Domain Model (Không phương thức, Không khóa kỹ thuật)

    class User {
        +String fullName
        +String email
        +String timezone
        +UserRole role
        +UserTier tier
    }

    class Goal {
        +String title
        +Date targetDate
        +String context
        +GoalStatus status
    }

    class Roadmap {
        +String title
        +Date startDate
        +Date targetDate
        +RoadmapStatus status
    }

    class OfficialSchedule {
        +Integer totalSessions
        +Float totalHours
        +DateTime activatedAt
    }

    class Milestone {
        +String title
        +String description
        +Integer sequenceOrder
        +Float estimatedHours
        +MilestoneStatus status
    }

    class Task {
        +String title
        +Integer estimatedMinutes
        +Date scheduledDate
        +TaskStatus status
    }

    class StudySession {
        +Integer targetDurationMinutes
        +DateTime startedAt
        +DateTime endedAt
        +SessionStatus status
    }

    class SessionTask {
        +Integer allocatedMinutes
        +Integer timeSpentMinutes
        +Boolean isCompletedInSession
    }

    class AvailabilityProfile {
        +AvailabilityMode mode
        +Object weeklySchedule
    }

    class ScheduleProposal {
        +Integer proposalVersion
        +ProposalStatus status
    }

    class PauseRecord {
        +Date pauseStartDate
        +Date resumeDate
        +Integer shiftDays
        +String reason
    }

    class StudyNote {
        +String content
        +NoteType noteType
    }

    class AIReview {
        +ReviewType reviewCycle
        +Object quantitativeSummary
        +String qualitativeFeedback
    }

    class WebCalSubscription {
        +Boolean isActive
        +DateTime lastSyncedAt
    }

    class AIQuota {
        +Integer monthlyLimit
        +Integer usedCalls
        +Integer reservedCalls
        +Date cycleStart
        +Date cycleEnd
    }

    User "1" -- "0..*" Goal : thiết lập
    User "1" -- "0..*" Roadmap : sở hữu
    User "1" *-- "1" AvailabilityProfile : cấu hình
    User "1" *-- "1" AIQuota : sở hữu
    User "1" -- "0..1" WebCalSubscription : cấp phát
    User "1" -- "0..*" StudySession : thực hiện

    Goal "1" -- "0..*" Roadmap : phân rã thành

    Roadmap "1" *-- "3..7" Milestone : gồm các mốc
    Roadmap "1" *-- "0..1" OfficialSchedule : áp dụng lịch chính thức
    Roadmap "1" o-- "0..*" ScheduleProposal : có đề xuất lịch
    Roadmap "1" *-- "0..*" PauseRecord : lưu vết tạm dừng
    Roadmap "1" -- "0..*" AIReview : nhận đánh giá

    Milestone "1" *-- "1..*" Task : chia nhỏ thành

    StudySession "0..*" -- "1..*" Task : học nhiệm vụ
    StudySession "1" *-- "0..*" StudyNote : ghi chép
```

### 2.2. Đặc tả 15 Khái niệm Miền Cốt lõi
1. **`User`:** Đại diện cho cá nhân người học hoặc quản trị viên trong hệ thống FocusFlow.
2. **`Goal`:** Mục tiêu tự học dài hạn do người dùng đặt ra trước khi có lộ trình chi tiết.
3. **`Roadmap`:** Kế hoạch học tập tổng thể hoàn chỉnh chia làm các giai đoạn có ngày bắt đầu và kết thúc.
4. **`OfficialSchedule`:** Lịch học chính thức có hiệu lực của lộ trình sau khi vượt qua Validation Gate và được áp dụng (`FR-ROADMAP-002`).
5. **`Milestone`:** Cột mốc kiến thức trọng tâm (giai đoạn cấp 1) trong lộ trình; mỗi lộ trình có từ 3 đến 7 cột mốc theo quy tắc `BUSR-02`.
6. **`Task`:** Nhiệm vụ học tập cụ thể theo từng ngày (15–240 phút); có thể nằm trên lịch chính thức hoặc trong hàng đợi Backlog (`scheduledDate` để trống).
7. **`StudySession`:** Phiên tập trung Pomodoro thực thi một hoặc nhiều task trong Study Workspace.
8. **`SessionTask`:** Thực thể liên kết giữa phiên học và task, lưu thời lượng phân bổ (`allocatedMinutes`), thời gian thực học (`timeSpentMinutes`) và cờ hoàn thành trong phiên (`BUSR-08`).
9. **`AvailabilityProfile`:** Khung thời gian rảnh cố định (Mode A) hoặc ma trận linh hoạt (Mode B) của người học.
10. **`ScheduleProposal`:** Đề xuất phân bổ nhiệm vụ vào khung giờ rảnh trước khi kích hoạt chính thức (Human-in-the-Loop Cấp 2).
11. **`PauseRecord`:** Lưu vết khoảng thời gian tạm dừng lộ trình để tính toán Domino Shift.
12. **`StudyNote`:** Ghi chép nháp (Scratchpad) hoặc đúc kết (Takeaways) sinh ra trong phiên học.
13. **`AIReview`:** Báo cáo phản hồi sư phạm định tính định kỳ từ mô hình Tự học có điều tiết (Zimmerman SRL).
14. **`WebCalSubscription`:** Đăng ký xuất lịch động 1 chiều cho ứng dụng lịch cá nhân qua feed RFC 5545 (`FR-CALENDAR-002`).
15. **`AIQuota`:** Quản lý hạn ngạch lượt gọi và chu kỳ tiêu thụ AI theo gói tài khoản.

### 2.3. Ma trận Quan hệ Phân cấp & Bản số
Điểm cải tiến học thuật cốt lõi theo chuẩn UML 2.5.1:
* **Hierarchical Composition (Sở hữu phân cấp):** `Roadmap *-- Milestone` và `Milestone *-- Task`. Bỏ đường nối trực tiếp `Roadmap *-- Task` để tránh vi phạm nguyên tắc một Part chỉ thuộc một Composite Whole duy nhất tại một thời điểm.
* **Many-to-Many giữa Session và Task qua Association Class:** Bản số `StudySession "0..*" -- "1..*" Task` kết nối qua `SessionTask` phản ánh đúng thực tế một task có thể học qua nhiều phiên và một phiên có thể học nhiều task.
* **1:1 Composition với OfficialSchedule:** `Roadmap *-- 0..1 OfficialSchedule` đại diện cho bộ lịch duy nhất đang được kích hoạt.

---

## 3. Phần II: Sơ đồ Lớp Thiết kế Chi tiết (Design Class Diagram - DCD)

### 3.1. Bản vẽ Sơ đồ Lớp Thiết kế
* **File nguồn PlantUML:** [`docs/uml/class-diagrams/design-class-diagram.puml`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/class-diagrams/design-class-diagram.puml)
* **Bản render xuất sẵn:** [[Bản vẽ PNG]](file:///Users/vuthang/Documents/FocusFlow/docs/uml/images/FocusFlow_Design_Class_Diagram.png)

```mermaid
classDiagram
    direction TB
    title FocusFlow — Design Class Diagram (DCD đầy đủ 3 ngăn)

    class User {
        -UUID id
        -String fullName
        -String email
        -String timezone
        -UserRole role
        -UserTier tier
        +canUseAI() Boolean
    }

    class Goal {
        -UUID id
        -String title
        -Date targetDate
        -String context
        -GoalStatus status
        +getDaysRemaining() Integer
        +archive() void
    }

    class Roadmap {
        -UUID id
        -String title
        -Date startDate
        -Date targetDate
        -RoadmapStatus status
        +activate() void
        +applyOfficialSchedule(schedule) void
        +pause(startDate, resumeDate, reason) void
        +resume() void
        +archive() void
    }

    class OfficialSchedule {
        -UUID id
        -UUID roadmapId
        -Integer totalSessions
        -Float totalHours
        -DateTime activatedAt
        +getSummary() String
    }

    class Milestone {
        -UUID id
        -String title
        -String description
        -Integer sequenceOrder
        -Float estimatedHours
        -MilestoneStatus status
        +approve() void
    }

    class Task {
        -UUID id
        -String title
        -Integer estimatedMinutes
        -Date scheduledDate
        -TaskStatus status
        +markCompleted() void
        +isOverdue(currentDate) Boolean
        +reschedule(newDate) void
    }

    class StudySession {
        -UUID id
        -Integer targetDurationMinutes
        -DateTime startedAt
        -DateTime endedAt
        -SessionStatus status
        -DateTime lastHeartbeatAt
        +start() void
        +finish() void
        +interrupt(reason) void
        +recordHeartbeat() void
        +markAbandoned() void
    }

    class SessionTask {
        -UUID id
        -UUID sessionId
        -UUID taskId
        -Integer allocatedMinutes
        -Integer timeSpentMinutes
        -Boolean isCompletedInSession
        +recordProgress(minutes, completed) void
    }

    class AvailabilityProfile {
        -UUID id
        -AvailabilityMode mode
        -Integer maxDailyMinutes
        -Integer preferredBreakMinutes
        +getDailyCeiling() Integer
    }

    class ScheduleProposal {
        -UUID id
        -Integer proposalVersion
        -ProposalStatus status
        +apply() void
        +reject() void
    }

    class PauseRecord {
        -UUID id
        -Date pauseStartDate
        -Date resumeDate
        -Integer shiftDays
        -String reason
        +calculateShiftDays() Integer
    }

    class StudyNote {
        -UUID id
        -String content
        -NoteType noteType
    }

    class AIReview {
        -UUID id
        -ReviewType reviewCycle
        -Object quantitativeSummary
        -String qualitativeFeedback
    }

    class WebCalSubscription {
        -UUID id
        -Boolean isActive
        -DateTime lastSyncedAt
        +resetToken() void
        +revoke() void
    }

    class AIQuota {
        -UUID id
        -Integer monthlyLimit
        -Integer usedCalls
        -Integer reservedCalls
        -Date cycleStart
        -Date cycleEnd
        +hasRemainingQuota() Boolean
        +reserve(calls) Boolean
        +commit(calls) void
        +release(calls) void
        +resetCycle() void
    }

    class DominoShiftCalculator {
        <<domain service>>
        +calculateShiftedDates(tasks, pauseDuration, profile) List~Task~
    }

    class AvailabilityValidator {
        <<domain service>>
        +validateDailyCeiling(duration, profile) Boolean
        +validateScheduleSlots(proposal, profile) Boolean
    }

    class PromptSanitizer {
        <<domain service>>
        +sanitizeInput(rawText) String
        +detectInjection(rawText) Boolean
    }

    class AbandonmentEvaluator {
        <<domain service>>
        +isAbandoned(lastHeartbeat, timeoutMinutes) Boolean
    }

    User "1" -- "0..*" Goal : thiết lập
    User "1" -- "0..*" Roadmap : sở hữu
    User "1" *-- "1" AvailabilityProfile : cấu hình
    User "1" *-- "1" AIQuota : sở hữu
    User "1" -- "0..1" WebCalSubscription : cấp phát
    User "1" -- "0..*" StudySession : thực hiện

    Goal "1" -- "0..*" Roadmap : phân rã thành

    Roadmap "1" *-- "3..7" Milestone : gồm các mốc
    Roadmap "1" *-- "0..1" OfficialSchedule : áp dụng lịch chính thức
    Roadmap "1" o-- "0..*" ScheduleProposal : có đề xuất lịch
    Roadmap "1" *-- "0..*" PauseRecord : lưu vết tạm dừng
    Roadmap "1" -- "0..*" AIReview : nhận đánh giá

    Milestone "1" *-- "1..*" Task : chia nhỏ thành

    StudySession "0..*" -- "1..*" Task : học nhiệm vụ
    StudySession "1" *-- "0..*" StudyNote : ghi chép

    Roadmap ..> DominoShiftCalculator : <<use>> (seq-06)
    ScheduleProposal ..> AvailabilityValidator : <<use>> (seq-04)
    Goal ..> PromptSanitizer : <<use>> (seq-02)
    StudySession ..> AbandonmentEvaluator : <<use>> (seq-08)
```

### 3.2. Trích xuất Phương thức từ Sequence Diagrams
Theo Tiêu chí I.3, mọi phương thức trong DCD đều có nguồn gốc từ thông điệp (Messages) trong các Sơ đồ Tuần tự chuẩn hóa:

| Lớp (Class) | Phương thức trong DCD | Thông điệp trích xuất từ Sequence Diagram | Sơ đồ Tuần tự nguồn |
|---|---|---|---|
| `User` | `canUseAI()` | `userEntity.can_use_ai()` | `seq-01-user-login.puml` |
| `AIQuota` | `hasRemainingQuota()`, `reserve()`, `commit()`, `release()` | `reserve_quota(user_id)`, `commit_quota()`, `release_quota()` | `seq-03-generate-milestones-tasks-ai.puml` |
| `Goal` | `create(...)` | `Goal.create(userId, title, targetDate, context)` | `seq-02-create-goal-roadmap.puml` |
| `Roadmap` | `create(...)`, `activate()`, `applyOfficialSchedule(...)` | `Roadmap.create(...)`, `roadmap.activate(schedule)` | `seq-02`, `seq-04` |
| `Roadmap` | `pause(...)` | `Roadmap.pause(startDate, resumeDate, reason)` | `seq-06-pause-domino-shift.puml` |
| `ScheduleProposal` | `createDraft()`, `apply()` | `create_draft_proposal()`, `proposal.mark_applied()` | `seq-03`, `seq-04` |
| `Task` | `markCompleted()` | `taskEntity.mark_completed()` | `seq-05-study-session-pomodoro.puml` |
| `Task` | `reschedule(newDate)` | `task.reschedule(newDate)` | `seq-06-pause-domino-shift.puml` |
| `StudySession` | `start()`, `recordHeartbeat()`, `finish()` | `session.start()`, `session.record_heartbeat()`, `session.finish()` | `seq-05-study-session-pomodoro.puml` |
| `StudySession` | `markAbandoned()` | `session.mark_abandoned(status, lastHeartbeatAt)` | `seq-08-abandoned-session-sweep.puml` |
| `SessionTask` | `recordProgress(...)` | `session_task.record_progress(minutes, completed)` | `seq-05-study-session-pomodoro.puml` |
| `WebCalSubscription` | `findActive()`, `recordAccess()` | `find_active_subscription_by_hash()`, `record_feed_access()` | `seq-07-webcal-sync-export.puml` |

### 3.3. Các Dịch vụ Miền (Domain Services - GRASP Pure Fabrication)
Để không làm ô nhiễm các Entity thuần túy bằng các giải thuật tính toán phức tạp, hệ thống thiết kế 4 Domain Services:
1. **`DominoShiftCalculator`:** Thực thi giải thuật dịch chuyển lịch tất định khi tạm dừng lộ trình (`seq-06`), tính toán khoảng dời $D = \text{resumeDate} - \text{startDate}$, dời lịch các task chưa hoàn thành sang ngày rảnh tiếp theo và bảo toàn quan hệ tiên quyết.
2. **`AvailabilityValidator`:** Xác thực trần học tối đa mỗi ngày (Hard Ceiling Validation Gate) đối chiếu không vượt quá quỹ giờ rảnh khả dụng (`seq-04`).
3. **`PromptSanitizer`:** Khử khuẩn đầu vào, ngăn chặn tấn công Prompt Injection trước khi chuyển tải sang External LLM (`seq-02`, `seq-03`).
4. **`AbandonmentEvaluator`:** Đánh giá động quy tắc OS-01 phân định kết quả phiên học gián đoạn sang `PARTIAL_COMPLETED` hoặc `CANCELLED` (`seq-08`).

### 3.4. Áp dụng Nguyên tắc Thiết kế GRASP & SOLID
- **Information Expert:** `Task` tự quản lý trạng thái `isOverdue(currentDate)` vì nó nắm `scheduledDate` và `status`; `AIQuota` tự kiểm tra `hasRemainingQuota()` vì nó nắm `usedCalls` và `monthlyLimit`.
- **High Cohesion (Gắn kết cao):** Mỗi Entity chỉ lưu trữ các thuộc tính bản chất; các phép tính toán lịch phức tạp được tách thành Pure Fabrication Domain Services.
- **Low Coupling (Phụ thuộc thấp):** Các Entity chỉ phụ thuộc vào các Enum trạng thái; quan hệ tới Domain Service là Dependency ngắn hạn (`..>`).

---

## 4. Phần III: Ma trận Truy vết Toàn diện (Traceability Matrix)

| Lớp Đối tượng | Phân hệ Use Case (20 UCs) | Sơ đồ Tuần tự (SD) | Bảng CSDL (PostgreSQL 16) | Ghi chú Trách nhiệm |
|---|---|---|---|---|
| `User` | `UC-AUTH-01..03`, `UC-ADM-01..02` | `seq-01` | `users` | Xác thực, phân quyền RBAC và kiểm tra trạng thái tài khoản |
| `AIQuota` | `UC-QUOTA-01`, `UC-ADM-02..03` | `seq-03` | `ai_quotas` | Quản lý hạn ngạch 2 pha (Reserve - Commit/Release) |
| `WebCalSubscription` | `UC-CAL-02` | `seq-07` | `webcal_tokens` | Cấp phát token 32-byte hex và feed lịch RFC 5545 |
| `Goal` | `UC-PLAN-01`, `FR-GOAL-001` | `seq-02` | `goals` | Quản lý mục tiêu và ngữ cảnh cá nhân |
| `Roadmap` | `UC-PLAN-01`, `UC-PAUSE-01` | `seq-02`, `seq-04`, `seq-06` | `roadmaps` | Thực thể trung tâm quản lý vòng đời kế hoạch học |
| `OfficialSchedule` | `UC-PLAN-03`, `FR-ROADMAP-002` | `seq-04` | `official_schedules` | Lịch chính thức được kích hoạt sau Validation Gate |
| `Milestone` | `UC-PLAN-01..02`, `BUSR-02` | `seq-02`, `seq-03` | `milestones` | Cột mốc kiến thức (ràng buộc 3..7 mốc/roadmap) |
| `Task` | `UC-PLAN-03`, `UC-TASK-01..02` | `seq-04`, `seq-05`, `seq-06` | `tasks` | Nhiệm vụ thực thi trong ngày hoặc trong Backlog |
| `StudySession` | `UC-SESS-01..02`, `OS-01/07` | `seq-05`, `seq-08` | `study_sessions` | Phiên học Pomodoro và cơ chế giám sát heartbeat |
| `SessionTask` | `UC-SESS-01`, `BUSR-08` | `seq-05` | `session_tasks` | Liên kết N:M phiên học và task, lưu thời lượng phân bổ |
| `AvailabilityProfile` | `UC-AVAIL-01`, `BUSR-01` | `seq-03`, `seq-04` | `availabilities` | Quỹ thời gian rảnh theo tuần (Mode A/B) |
| `ScheduleProposal` | `UC-PLAN-02..03` | `seq-03`, `seq-04` | `schedule_proposals` | Đề xuất dự thảo lịch học trước khi Apply ACID |
| `PauseRecord` | `UC-PAUSE-01`, `BUSR-01` | `seq-06` | `pause_records` | Lưu vết tạm dừng phục vụ Domino Shift |
| `StudyNote` | `UC-SESS-01..02` | `seq-05` | `study_notes` | Thu hoạch kiến thức hoặc lý do gián đoạn |
| `AIReview` | `UC-REP-02` | `seq-03` | `ai_reviews` | Nhận xét định tính định kỳ theo Zimmerman SRL |
| `DominoShiftCalculator` | `UC-PAUSE-01`, `BUSR-01` | `seq-06` | *(Domain Service)* | Thuật toán tịnh tiến tất định không gọi AI |
| `AvailabilityValidator` | `UC-PLAN-03`, `BUSR-03` | `seq-04` | *(Domain Service)* | Kiểm tra trần giờ học và hợp lệ khung giờ |
| `PromptSanitizer` | `UC-PLAN-02`, `NFR-SEC-005` | `seq-02`, `seq-03` | *(Domain Service)* | Phòng chống Prompt Injection bảo vệ LLM |
| `AbandonmentEvaluator` | `UC-SESS-02`, `OS-01` | `seq-08` | *(Domain Service)* | Phân định kết quả phiên học gián đoạn |
