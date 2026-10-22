# FocusFlow — Tài liệu Thiết kế Biểu đồ Lớp UML (Class Diagrams Document)

**Dự án:** FocusFlow — Hệ thống hỗ trợ lập kế hoạch và thực thi lộ trình tự học thích ứng tích hợp AI  
**Tiêu chuẩn kỹ thuật:** OMG UML 2.5.1 Superstructure, Craig Larman (*Applying UML and Patterns*), Martin Fowler (*UML Distilled*)  
**Căn cứ đánh giá học thuật:** Khung Rubric Đồ án Tốt nghiệp CNTT — Tiêu chí TC1 & TC2.1 & TC2.3 (Mức 5)  
**Tài liệu liên kết nguồn:**
- Đặc tả yêu cầu phần mềm: [`docs/srs/srs-v1.0.md`](file:///Users/vuthang/Documents/FocusFlow/docs/srs/srs-v1.0.md)
- Sơ đồ Ca sử dụng: [`docs/uml/use-cases/use-case-diagram.puml`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/use-cases/use-case-diagram.puml) | [`docs/uml/use-case-specifications.md`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/use-case-specifications.md) (26 Use Cases)
- Sơ đồ Tuần tự: [`docs/uml/sequence-diagrams.md`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/sequence-diagrams.md) (9 sơ đồ chi tiết)
- Máy trạng thái thực thể: [`docs/uml/state-machines.md`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/state-machines.md) (4 máy trạng thái)
- Thiết kế Cơ sở dữ liệu: [`docs/database/database-schema-design.md`](file:///Users/vuthang/Documents/FocusFlow/docs/database/database-schema-design.md), [`docs/database/data-dictionary.md`](file:///Users/vuthang/Documents/FocusFlow/docs/database/data-dictionary.md) & [`docs/database/schema.sql`](file:///Users/vuthang/Documents/FocusFlow/docs/database/schema.sql)

---

## MỤC LỤC
1. [Phân định Góc nhìn Thiết kế theo Chuẩn Craig Larman](#1-phân-định-góc-nhìn-thiết-kế-theo-chuẩn-craig-larman)
2. [Phần I: Mô hình Miền Nghiệp vụ (Domain Model / Conceptual Class Diagram)](#2-phần-i-mô-hình-miền-nghiệp-vụ-domain-model--conceptual-class-diagram)
   - [2.1. Bản vẽ Sơ đồ Miền](#21-bản-vẽ-sơ-đồ-miền)
   - [2.2. Đặc tả 14 Khái niệm Miền Cốt lõi](#22-đặc-tả-14-khái-niệm-miền-cốt-lõi)
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
┌───────────────────────────────────────────────────────────────┐
│  Góc nhìn 1: DOMAIN MODEL (Mô hình Miền Nghiệp vụ)            │
│  - Trực quan hóa 15 khái niệm nghiệp vụ bài toán người học   │
│  - Chỉ gồm Tên lớp + Thuộc tính (2 ngăn)                     │
│  - TUYỆT ĐỐI KHÔNG CÓ PHƯƠNG THỨC & KHÔNG KHÓA KỸ THUẬT       │
│  - Bổ sung LearnerProfile (Zimmerman SRL) & Quan hệ tiên quyết│
│  - Loại bỏ các cơ chế kỹ thuật hạ tầng (Reservation, Tokens)  │
└───────────────────────────────┬───────────────────────────────┘
                                │ + Phân tích Động (Sequence Diagrams SD1..SD9)
                                │ + Nguyên tắc Trách nhiệm GRASP / SOLID
                                │ + Kiến trúc Lục giác (Ports & Adapters)
                                ▼
┌───────────────────────────────────────────────────────────────┐
│  Góc nhìn 2: DESIGN CLASS DIAGRAM (DCD - Thiết kế Phần mềm)   │
│  - Mô hình hóa 19 lớp thực thể thiết kế (Rich Domain Model)   │
│  - 100% Lớp là Danh từ thuần túy, phương thức theo Information│
│    Expert, loại bỏ Domain Service theo chuẩn OOP học thuật   │
│  - Đầy đủ 3 ngăn: Tên, Thuộc tính (-), Phương thức (+)        │
│  - Bổ sung AIQuotaReservation, WebCalToken, LearnerProfile,   │
│    TaskDependency, ScheduleChangeLog                          │
│  - Thuần OOP: Quan hệ liên kết bản số, không trùng lặp FK     │
└───────────────────────────────────────────────────────────────┘
```

---

## 2. Phần I: Mô hình Miền Nghiệp vụ (Domain Model / Conceptual Class Diagram)

### 2.1. Bản vẽ Sơ đồ Miền
* **File nguồn PlantUML:** [`docs/uml/class-diagrams/domain-model.puml`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/class-diagrams/domain-model.puml)
* **Bản render xuất sẵn:** [[Bản vẽ PNG]](file:///Users/vuthang/Documents/FocusFlow/docs/uml/images/FocusFlow_Domain_Model.png)

```mermaid
classDiagram
    direction TB
    title FocusFlow — Domain Model (14 Khái niệm Miền Cốt lõi, Chuẩn Craig Larman)

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
        +Integer totalPlannedMinutes
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
        +Date pauseEndDate
        +Integer shiftedDays
        +String reason
    }

    class StudyNote {
        +String content
        +NoteType noteType
    }

    class AIReview {
        +ReviewCycle reviewCycle
        +Object quantitativeSummary
        +String qualitativeFeedback
    }

    class AIQuota {
        +Integer monthlyLimit
        +Integer usedCalls
        +Integer reservedCalls
        +DateTime cycleStart
        +DateTime cycleEnd
    }

    class LearnerProfile {
        +Integer optimalFocusDurationMins
        +Object peakProductivitySlots
        +Float estimationBiasFactor
        +Float weeklyCompletionRate
        +Integer totalCompletedSessions
        +Boolean isColdStart
    }

    User "1" -- "0..*" Goal : thiết lập
    User "1" -- "0..*" Roadmap : sở hữu
    User "1" *-- "1" AvailabilityProfile : cấu hình
    User "1" *-- "1" AIQuota : sở hữu
    User "1" *-- "1" LearnerProfile : khắc họa hồ sơ
    User "1" -- "0..*" StudySession : thực hiện

    Goal "1" -- "0..*" Roadmap : phân rã thành

    Roadmap "1" *-- "3..7" Milestone : gồm các mốc
    Roadmap "1" *-- "0..1" OfficialSchedule : áp dụng lịch chính thức
    Roadmap "1" o-- "0..*" ScheduleProposal : có đề xuất lịch
    Roadmap "1" *-- "0..*" PauseRecord : lưu vết tạm dừng
    Roadmap "1" -- "0..*" AIReview : nhận đánh giá

    Milestone "1" *-- "1..*" Task : chia nhỏ thành
    Task "0..*" -- "0..*" Task : tiên quyết (DAG)

    StudySession "1" *-- "1..*" SessionTask : gồm các task trong phiên
    SessionTask "0..*" -- "1" Task : học nhiệm vụ
    StudySession "1" *-- "0..*" StudyNote : ghi chép
```

### 2.2. Đặc tả 15 Khái niệm Miền Cốt lõi
Theo chuẩn Craig Larman, Mô hình Miền chỉ ghi nhận các khái niệm nghiệp vụ có ý nghĩa đối với người học và chuyên gia miền:
1. **`User`:** Đại diện cho cá nhân người học hoặc quản trị viên trong hệ thống FocusFlow.
2. **`Goal`:** Mục tiêu tự học dài hạn do người dùng đặt ra trước khi có lộ trình chi tiết.
3. **`Roadmap`:** Kế hoạch học tập tổng thể hoàn chỉnh chia làm các giai đoạn có ngày bắt đầu và kết thúc.
4. **`OfficialSchedule`:** Lịch học chính thức có hiệu lực của lộ trình sau khi vượt qua Validation Gate và được kích hoạt (`FR-ROADMAP-002`). Lưu trữ ảnh chụp kế hoạch cơ sở đóng băng (`totalPlannedMinutes`).
5. **`Milestone`:** Cột mốc kiến thức trọng tâm (giai đoạn cấp 1) trong lộ trình; mỗi lộ trình có từ 3 đến 7 cột mốc theo quy tắc `BUSR-02`.
6. **`Task`:** Nhiệm vụ học tập cụ thể theo từng ngày (15–240 phút); có thể nằm trên lịch chính thức hoặc trong hàng đợi Backlog (`scheduledDate` để trống). Trạng thái hỗ trợ `PENDING, TODO, IN_PROGRESS, COMPLETED, CANCELLED`.
7. **`StudySession`:** Phiên tập trung Pomodoro thực thi một hoặc nhiều task trong Study Workspace. Trạng thái hỗ trợ `IN_PROGRESS, COMPLETED, PARTIAL_COMPLETED, CANCELLED` (theo `OS-01`).
8. **`SessionTask`:** Thực thể liên kết giữa phiên học và task, lưu thời lượng phân bổ (`allocatedMinutes`), thời gian thực học (`timeSpentMinutes`) và cờ hoàn thành trong phiên (`BUSR-08`).
9. **`AvailabilityProfile`:** Khung thời gian rảnh cố định (Mode A) hoặc ma trận linh hoạt (Mode B) của người học.
10. **`ScheduleProposal`:** Đề xuất phân bổ nhiệm vụ vào khung giờ rảnh trước khi kích hoạt chính thức (Human-in-the-Loop Cấp 2).
11. **`PauseRecord`:** Lưu vết khoảng thời gian tạm dừng lộ trình để tính toán Domino Shift tất định: $\text{shiftedDays} = \text{pauseEndDate} - \text{pauseStartDate} + 1$.
12. **`StudyNote`:** Ghi chép nháp (Scratchpad) hoặc đúc kết (Takeaways) sinh ra trong phiên học.
13. **`AIReview`:** Báo cáo phản hồi sư phạm định kỳ (chu kỳ tuần `WEEKLY` hoặc theo mốc `MILESTONE`) từ mô hình Tự học có điều tiết (Zimmerman SRL).
14. **`AIQuota`:** Quản lý hạn ngạch lượt gọi và chu kỳ tiêu thụ AI theo gói tài khoản người dùng (`OS-02`).
15. **`LearnerProfile`:** Hồ sơ thói quen tự học cá nhân hóa theo chu trình Zimmerman SRL (thời lượng tập trung tối ưu, khung giờ vàng, hệ số chệch ước lượng thời gian) được tổng hợp bất đồng bộ qua Celery định kỳ (`ADR-010`).

> [!NOTE]
> **Giải trình Học thuật Loại trừ Thực thể Kỹ thuật:** Các bảng vật lý như `ai_quota_reservations` (sổ cái 2 pha phòng ngừa sự cố mạng) và `webcal_tokens` (mã băm bảo mật SHA-256 đồng bộ feed) là các chi tiết kỹ thuật/hạ tầng (Infrastructure / Persistence Mechanics), do đó được tách bạch hoàn toàn khỏi Domain Model theo đúng chuẩn Craig Larman và xuất hiện đầy đủ trong Sơ đồ Lớp Thiết kế (DCD).

### 2.3. Ma trận Quan hệ Phân cấp & Bản số
Điểm cải tiến học thuật cốt lõi theo chuẩn UML 2.5.1:
* **Hierarchical Composition (Sở hữu phân cấp):** `Roadmap *-- Milestone` và `Milestone *-- Task`. Bỏ đường nối trực tiếp `Roadmap *-- Task` để tránh vi phạm nguyên tắc một Part chỉ thuộc một Composite Whole duy nhất tại một thời điểm.
* **Phân rã liên kết N:M giữa StudySession và Task:** Thay vì dùng Association Class gây nhầm lẫn hiển thị, quan hệ nhiều-nhiều được phân rã tường minh thành 2 liên kết nhị phân theo chuẩn OOP và CSDL:
  - `StudySession "1" *-- "1..*" SessionTask` (Composition: vòng đời của lượt học phụ thuộc hoàn toàn vào phiên học).
  - `SessionTask "0..*" -- "1" Task` (Association: tham chiếu nhiệm vụ học tập, với ràng buộc `ON DELETE RESTRICT` để bảo toàn lịch sử học tập).
* **1:1 Composition với OfficialSchedule:** `Roadmap *-- 0..1 OfficialSchedule` đại diện cho bộ lịch duy nhất đang được kích hoạt.

---

## 3. Phần II: Sơ đồ Lớp Thiết kế Chi tiết (Design Class Diagram - DCD)

### 3.1. Bản vẽ Sơ đồ Lớp Thiết kế
* **File nguồn PlantUML:** [`docs/uml/class-diagrams/design-class-diagram.puml`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/class-diagrams/design-class-diagram.puml)
* **Bản render xuất sẵn:** [[Bản vẽ PNG]](file:///Users/vuthang/Documents/FocusFlow/docs/uml/images/FocusFlow_Design_Class_Diagram.png)

```mermaid
classDiagram
    direction TB
    title FocusFlow — Design Class Diagram (DCD 19 Lớp Thực thể Thiết kế — Chuẩn Rich Domain Model & Information Expert)

    class User {
        -UUID id
        -String fullName
        -String email
        -String timezone
        -UserRole role
        -UserTier tier
        +canUseAI() Boolean
        +isFreeTier() Boolean
        +upgradeTier(newTier) void
    }

    class Goal {
        -UUID id
        -String title
        -Date targetDate
        -String context
        -GoalStatus status
        +getDaysRemaining() Integer
        +sanitizeContext() void
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
        +pause(startDate, endDate, reason) void
        +resume() void
        +calculateDominoShift(pauseRecord) void
        +archive() void
    }

    class OfficialSchedule {
        -UUID id
        -Integer totalSessions
        -Integer totalPlannedMinutes
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
        -Time startTime
        -Time endTime
        -TaskStatus status
        -DateTime completedAt
        +markCompleted() void
        +cancel() void
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
        +recordHeartbeat() void
        +markAbandoned() void
        +evaluateAbandonmentStatus(timeoutMinutes) SessionStatus
        +isTimedOut(timeoutMinutes) Boolean
    }

    class SessionTask {
        -UUID id
        -Integer allocatedMinutes
        -Integer timeSpentMinutes
        -Boolean isCompletedInSession
        +recordProgress(minutes, completed) void
    }

    class AvailabilityProfile {
        -UUID id
        -AvailabilityMode mode
        -Object weeklySchedule
        +getDailyCeiling(dayOfWeek) Integer
        +validateDailyCeiling(durationMinutes) Boolean
        +validateScheduleSlots(proposal) Boolean
    }

    class ScheduleProposal {
        -UUID id
        -Integer proposalVersion
        -ProposalStatus status
        -DateTime appliedAt
        +apply() void
        +reject() void
        +validateConstraints(profile) Boolean
    }

    class PauseRecord {
        -UUID id
        -Date pauseStartDate
        -Date pauseEndDate
        -Integer shiftedDays
        -String reason
        +calculateShiftedDays() Integer
    }

    class StudyNote {
        -UUID id
        -String content
        -NoteType noteType
    }

    class AIReview {
        -UUID id
        -UUID milestoneId
        -Date periodStart
        -Date periodEnd
        -ReviewCycle reviewCycle
        -String qualitativeFeedback
        -Object quantitativeSummary
    }

    class WebCalToken {
        -UUID id
        -String tokenHash
        -Boolean isActive
        -DateTime lastUsedAt
        -DateTime rotatedAt
        +rotate(newHash) void
        +deactivate() void
        +recordAccess() void
    }

    class AIQuota {
        -UUID id
        -Integer monthlyLimit
        -Integer usedCalls
        -Integer reservedCalls
        -Long tokensConsumed
        -DateTime cycleStart
        -DateTime cycleEnd
        +hasRemainingQuota() Boolean
        +reserve() Boolean
        +commit(tokens) void
        +release() void
        +resetCycle() void
    }

    class AIQuotaReservation {
        -UUID id
        -QuotaReservationStatus status
        -Integer estimatedTokens
        -Integer tokensConsumed
        -DateTime expiresAt
        -DateTime createdAt
        +commit(tokens) void
        +release() void
        +markExpired() void
        +isExpired(now) Boolean
    }

    class LearnerProfile {
        -UUID userId
        -Integer optimalFocusDurationMins
        -Object peakProductivitySlots
        -Float estimationBiasFactor
        -Float weeklyCompletionRate
        -Integer totalCompletedSessions
        -Boolean isColdStart
        -DateTime lastAggregatedAt
        +recalculateProfile(sessions) void
        +resetProfile() void
        +isEligibleForAdjustment() Boolean
    }

    class TaskDependency {
        -UUID predecessorId
        -UUID successorId
        -UUID roadmapId
        -DateTime createdAt
        +isValid() Boolean
        +detectCycle(dependencies) Boolean
    }

    class ScheduleChangeLog {
        -UUID id
        -UUID roadmapId
        -UUID taskId
        -ScheduleActorType actorType
        -String action
        -Object oldValue
        -Object newValue
        -String reason
        -DateTime createdAt
    }

    User "1" -- "0..*" Goal : thiết lập
    User "1" -- "0..*" Roadmap : sở hữu
    User "1" *-- "1" AvailabilityProfile : cấu hình
    User "1" *-- "1" AIQuota : sở hữu
    User "1" *-- "1" LearnerProfile : khắc họa hồ sơ
    User "1" -- "0..1" WebCalToken : cấp phát
    User "1" -- "0..*" StudySession : thực hiện

    Goal "1" -- "0..*" Roadmap : phân rã thành

    Roadmap "1" *-- "3..7" Milestone : gồm các mốc
    Roadmap "1" *-- "0..1" OfficialSchedule : áp dụng lịch chính thức
    Roadmap "1" o-- "0..*" ScheduleProposal : có đề xuất lịch
    Roadmap "1" *-- "0..*" PauseRecord : lưu vết tạm dừng
    Roadmap "1" -- "0..*" AIReview : nhận đánh giá
    Roadmap "1" *-- "0..*" ScheduleChangeLog : lưu vết biến động

    Milestone "1" *-- "1..*" Task : chia nhỏ thành

    Task "1" *-- "0..*" TaskDependency : predecessor
    Task "1" *-- "0..*" TaskDependency : successor

    StudySession "1" *-- "1..*" SessionTask : gồm các task trong phiên
    SessionTask "0..*" -- "1" Task : học nhiệm vụ
    StudySession "1" *-- "0..*" StudyNote : ghi chép

    AIQuota "1" *-- "0..*" AIQuotaReservation : ghi nhật ký giữ chỗ
```

### 3.2. Trích xuất Phương thức từ Sequence Diagrams
Theo Tiêu chí I.3, mọi phương thức trong DCD đều có nguồn gốc từ thông điệp (Messages) trong các Sơ đồ Tuần tự chuẩn hóa (SD1 đến SD9):

| Lớp Thiết kế (Class) | Phương thức trong DCD | Thông điệp trích xuất từ Sequence Diagram | Sơ đồ Tuần tự nguồn |
|---|---|---|---|
| `User` | `canUseAI()`, `isFreeTier()`, `upgradeTier(newTier)` | `userEntity.can_use_ai()`, `upgrade_tier(...)` | `seq-01-user-login.puml` |
| `AIQuota` | `hasRemainingQuota()`, `reserve()`, `commit()`, `release()`, `resetCycle()` | `reserve_quota(user_id)`, `commit_quota()`, `release_quota()` | `seq-03-generate-milestones-tasks-ai.puml` |
| `AIQuotaReservation` | `commit()`, `release()`, `markExpired()`, `isExpired()` | `create_reservation()`, `mark_expired()`, `release_reservation()` | `seq-03`, `seq-09-quota-sweeper.puml` |
| `Goal` | `getDaysRemaining()`, `sanitizeContext()`, `archive()` | `Goal.create(...)`, `goal.archive()` | `seq-02-create-goal-roadmap.puml` |
| `Roadmap` | `activate()`, `applyOfficialSchedule(...)`, `pause(...)`, `resume()`, `calculateDominoShift(pauseRecord)`, `archive()` | `Roadmap.create(...)`, `roadmap.activate(schedule)`, `roadmap.pause(...)`, `roadmap.calculate_domino_shift(...)` | `seq-02`, `seq-04`, `seq-06-pause-domino-shift.puml` |
| `ScheduleProposal` | `apply()`, `reject()`, `validateConstraints(profile)` | `create_draft_proposal()`, `proposal.apply()`, `proposal.validate_constraints(...)` | `seq-03`, `seq-04-apply-official-schedule.puml` |
| `AvailabilityProfile` | `getDailyCeiling(...)`, `validateDailyCeiling(...)`, `validateScheduleSlots(...)` | `profile.get_daily_ceiling()`, `profile.validate_ceiling(...)` | `seq-03`, `seq-04-apply-official-schedule.puml` |
| `Task` | `markCompleted()`, `cancel()`, `reschedule(newDate)`, `isOverdue(...)` | `task.mark_completed()`, `task.cancel()`, `task.reschedule(newDate)` | `seq-05`, `seq-06-pause-domino-shift.puml` |
| `StudySession` | `start()`, `recordHeartbeat()`, `finish()`, `markAbandoned()`, `evaluateAbandonmentStatus(...)`, `isTimedOut(...)` | `session.start()`, `session.record_heartbeat()`, `session.finish()`, `session.evaluate_abandonment()` | `seq-05`, `seq-08-abandoned-session-sweep.puml` |
| `SessionTask` | `recordProgress(...)` | `session_task.record_progress(minutes, completed)` | `seq-05-study-session-pomodoro.puml` |
| `WebCalToken` | `rotate()`, `deactivate()`, `recordAccess()` | `rotate_token()`, `find_active_by_hash()`, `record_access()` | `seq-07-webcal-sync-export.puml` |
| `LearnerProfile` | `recalculateProfile()`, `resetProfile()`, `isEligibleForAdjustment()` | `profile.recalculate()`, `profile.reset()` | `ADR-010`, `seq-03` |
| `TaskDependency` | `isValid()`, `detectCycle(dependencies)` | `task_deps.validate()`, `task_deps.detect_cycle()` | `ADR-009`, `seq-04` |
| `ScheduleChangeLog` | `—` | `schedule_change_logs.create()` | `ADR-010`, `seq-04`, `seq-06` |

### 3.3. Mô hình Miền Giàu Bản Thể (Rich Domain Model) & Nguyên lý GRASP Information Expert

Nhằm khắc phục triệt để các hạn chế của **Mô hình Miền Thiếu Máu (Anemic Domain Model)** và hiện tượng "Động từ hóa thành Lớp" (Function-as-a-Class) thường bị hội đồng phản biện học thuật đánh giá là phong cách lập trình thủ tục trá hình trong OOP, hệ thống FocusFlow áp dụng triệt để mô hình **Rich Domain Model** kết hợp nguyên lý **GRASP Information Expert**:

1. **Loại bỏ Domain Services khỏi Sơ đồ Lớp Thực thể:**
   - Các lớp dịch vụ phi trạng thái (stateless) trước đây (`DominoShiftCalculator`, `AvailabilityValidator`, `ConstraintValidationEngine`, `PromptSanitizer`, `AbandonmentEvaluator`) được loại bỏ hoàn toàn khỏi DCD.
   - 100% các lớp trong DCD đều là **Danh từ thuần túy (19 Entity Classes)** đại diện cho các thực thể đối tượng có trạng thái, dữ liệu và định danh (Identity).

2. **Chuyển giao trách nhiệm theo GRASP Information Expert:**
   - **`Roadmap.calculateDominoShift(pauseRecord: PauseRecord)`:** `Roadmap` là Aggregate Root quản lý cấu trúc các cột mốc và nhiệm vụ, nắm giữ thông tin ngày tháng toàn diện. Do đó, `Roadmap` đóng vai trò Information Expert tự thực thi thuật toán tịnh tiến các Task chưa hoàn thành khi nhận bản ghi tạm dừng `PauseRecord`, bảo toàn tính đóng gói mà không cần gọi External Service.
   - **`AvailabilityProfile.validateDailyCeiling(durationMinutes)` & `validateScheduleSlots(proposal)`:** `AvailabilityProfile` nắm giữ cấu hình lịch rảnh tuần (Mode A/B) của người học, do đó chính thực thể này tự kiểm định các slot học và trần thời gian hàng ngày trước khi cấp phép phân bổ.
   - **`ScheduleProposal.validateConstraints(profile)`:** Thực thể đề xuất lịch tự kiểm tra tính hợp lệ về mặt ràng buộc đối chiếu với hồ sơ thời gian rảnh trước khi kích hoạt sang trạng thái `APPLIED`.
   - **`StudySession.evaluateAbandonmentStatus(timeoutMinutes)` & `isTimedOut(timeoutMinutes)`:** `StudySession` nắm giữ `startedAt`, `endedAt`, `targetDurationMinutes` và `lastHeartbeatAt`, nên là Information Expert trực tiếp đánh giá trạng thái gián đoạn và phân định kết quả phiên học theo quy tắc `OS-01`.
   - **`TaskDependency.detectCycle(dependencies)`:** Thực thể phụ thuộc nhiệm vụ tự cung cấp phương thức giải thuật phát hiện chu trình đồ thị có hướng (DAG), ngăn chặn phụ thuộc vòng lặp giữa các nhiệm vụ.
   - **`Goal.sanitizeContext()`:** Thực thể mục tiêu tự làm sạch và chuẩn hóa ngữ cảnh đầu vào của người học; các cơ chế kiểm duyệt chuyên sâu trước khi gọi external LLM được giữ ở tầng Application/Port Adapter theo đúng ranh giới kiến trúc Hexagonal.

3. **Phân định Ranh giới Kiến trúc Phần mềm:**
   - Class Diagram chỉ biểu diễn cấu trúc dữ liệu và phương thức nghiệp vụ nội tại của các Entity.
   - Các dịch vụ điều phối luồng Use Case (Application Services, Use Case Interactors) thuộc về Tầng Ứng dụng trong Kiến trúc Lục giác, được trực quan hóa đầy đủ trong **Sơ đồ Thành phần (C4 Component Diagram)** và **Sơ đồ Tuần tự (Sequence Diagrams)**, đảm bảo sự tách bạch rõ ràng giữa Cấu trúc Dữ liệu Miền (Static Structure) và Điều phối Quy trình Động (Dynamic Orchestration).

### 3.4. Áp dụng Nguyên tắc Thiết kế GRASP & SOLID
- **Information Expert:** Trách nhiệm xử lý logic được giao cho lớp nắm giữ đầy đủ dữ liệu nhất (`Roadmap` tính Domino Shift, `StudySession` đánh giá bỏ ngang, `Task` tự quản lý quá hạn `isOverdue`).
- **Encapsulation & High Cohesion (Đóng gói & Gắn kết cao):** Thuộc tính luôn ở mức `private (-)`, phương thức cung cấp giao diện `public (+)`, loại bỏ các getter/setter vô nghĩa, ngăn chặn dữ liệu bị sửa đổi tùy tiện từ bên ngoài.
- **Low Coupling (Phụ thuộc thấp):** Các Entity liên kết qua quan hệ kết hợp (Association/Composition) có ngữ nghĩa bản số rõ ràng; không phụ thuộc lẫn nhau qua khóa ngoại kỹ thuật thô.

---

## 4. Phần III: Ma trận Truy vết Toàn diện (Traceability Matrix)

| Lớp Đối tượng (19 Classes) | Phân hệ Use Case (26 UCs) | Sơ đồ Tuần tự (SD) | Bảng CSDL (PostgreSQL 16) | Ghi chú Trách nhiệm & Phương thức Rich Domain |
|---|---|---|---|---|
| `User` | `UC-AUTH-01..03`, `UC-ADM-01..02` | `seq-01` | `users` | Xác thực, phân quyền RBAC và kiểm tra trạng thái tài khoản (`canUseAI`, `upgradeTier`). |
| `AIQuota` | `UC-QUOTA-01`, `UC-ADM-02..03` | `seq-03`, `seq-09` | `ai_quotas` | Quản lý hạn ngạch 2 pha (`hasRemainingQuota`, `reserve`, `commit`, `release`). |
| `AIQuotaReservation` | `UC-QUOTA-01..02`, `BUSR-10`, `OS-02` | `seq-03`, `seq-09` | `ai_quota_reservations` | Sổ cái giữ chỗ 2 pha, lưu vết trạng thái và kiểm tra hết hạn (`isExpired`, `markExpired`). |
| `WebCalToken` | `UC-CAL-01..02`, `BUSR-08` | `seq-07` | `webcal_tokens` | Cấp phát token 32-byte hex và feed lịch RFC 5545 1 chiều (`rotate`, `deactivate`, `recordAccess`). |
| `Goal` | `UC-PLAN-01`, `FR-GOAL-001` | `seq-02` | `goals` | Quản lý mục tiêu cá nhân của người học (`getDaysRemaining`, `sanitizeContext`, `archive`). |
| `Roadmap` | `UC-PLAN-01`, `UC-PAUSE-01` | `seq-02`, `seq-04`, `seq-06` | `roadmaps` | Thực thể trung tâm quản lý vòng đời và tự tịnh tiến Domino (`calculateDominoShift`, `pause`, `activate`). |
| `OfficialSchedule` | `UC-PLAN-03`, `FR-ROADMAP-002` | `seq-04` | `official_schedules` | Lịch chính thức đóng băng (`totalPlannedMinutes`) sau Validation Gate (`getSummary`). |
| `Milestone` | `UC-PLAN-01..02`, `BUSR-02` | `seq-02`, `seq-03` | `milestones` | Cột mốc kiến thức (ràng buộc 3..7 mốc/roadmap, phương thức `approve`). |
| `Task` | `UC-PLAN-03`, `UC-TASK-01..02` | `seq-04`, `seq-05`, `seq-06` | `tasks` | Nhiệm vụ thực thi (`markCompleted`, `cancel`, `reschedule`, `isOverdue`). |
| `StudySession` | `UC-SESS-01..02`, `OS-01/07` | `seq-05`, `seq-08` | `study_sessions` | Phiên học Pomodoro và tự thẩm định bỏ ngang (`evaluateAbandonmentStatus`, `isTimedOut`, `recordHeartbeat`). |
| `SessionTask` | `UC-SESS-01`, `BUSR-08` | `seq-05` | `session_tasks` | Liên kết N:M phiên học và task, ON DELETE RESTRICT bảo toàn lịch sử (`recordProgress`). |
| `AvailabilityProfile` | `UC-AVAIL-01`, `BUSR-01` | `seq-03`, `seq-04` | `availabilities` | Quỹ giờ rảnh theo tuần và tự kiểm định trần giờ (`validateDailyCeiling`, `validateScheduleSlots`). |
| `ScheduleProposal` | `UC-PLAN-02..03` | `seq-03`, `seq-04` | `schedule_proposals` | Đề xuất dự thảo lịch học và tự kiểm tra ràng buộc (`validateConstraints`, `apply`, `reject`). |
| `PauseRecord` | `UC-PAUSE-01`, `BUSR-01` | `seq-06` | `pause_records` | Lưu vết tạm dừng và tự tính số ngày dời (`calculateShiftedDays`). |
| `StudyNote` | `UC-SESS-01..02` | `seq-05` | `study_notes` | Thu hoạch kiến thức hoặc ghi chú nháp trong phiên học. |
| `AIReview` | `UC-REP-02` | `seq-03` | `ai_reviews` | Nhận xét sư phạm định kỳ theo Zimmerman SRL (WEEKLY / MILESTONE). |
| `LearnerProfile` | `UC-PLAN-02`, `UC-REP-01` | `seq-03` | `learner_profiles` | Hồ sơ thói quen tự học cá nhân hóa (`recalculateProfile`, `resetProfile`, `isEligibleForAdjustment`). |
| `TaskDependency` | `UC-PLAN-03`, `FR-PLAN-005` | `seq-04` | `task_dependencies` | Bảng quan hệ phụ thuộc tiên quyết có hướng DAG và phát hiện chu trình (`detectCycle`, `isValid`). |
| `ScheduleChangeLog` | `UC-PAUSE-01`, `UC-SCHED-01` | `seq-04`, `seq-06` | `schedule_change_logs` | Nhật ký kiểm toán lưu vết mọi biến động lịch trình (`ADR-010`). |
