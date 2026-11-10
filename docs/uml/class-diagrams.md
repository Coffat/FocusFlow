# FocusFlow — Sơ đồ Lớp Miền & Thiết kế Hành vi (System Domain & Behavioral Design Class Diagram)

> **Phiên bản:** v11.1 — **Baseline v1.4 Post-CCB Approved (Hội đồng CCB Phê duyệt: 43 FR, 8 Actors ACT-00..ACT-07, Chuẩn OMG UML 2.5.1; Domain Overview được bổ sung operations cốt lõi)**.  
> **Ngôn ngữ:** Tên class/thuộc tính bằng tiếng Anh; nhãn quan hệ và chú thích bằng tiếng Việt.  
> **Nguồn PlantUML Domain Overview:** [`class-diagrams/class-diagram.puml`](class-diagrams/class-diagram.puml) | **Nguồn Mermaid tương đương:** [`class-diagrams/class-diagram.mmd`](class-diagrams/class-diagram.mmd) | **Behavioral Design views:** xem [Mục I](#i-behavioral-design-class-diagrams--operation-catalog).  
> **Ảnh kết xuất độ nét cao:** [`images/FocusFlow_Class_Diagram.png`](images/FocusFlow_Class_Diagram.png)

---

## Mục lục

- [A. Phạm vi, Profile & Giả định Thiết kế](#a-phạm-vi-profile--giả-định-thiết-kế)
- [B. Danh mục Khái niệm Miền Cốt lõi & Truy vết 35 Thực thể SRS §12](#b-danh-mục-khái-niệm-miền-cốt-lõi--truy-vết-35-thực-thể-srs-12)
- [C. Sơ đồ Lớp Tổng quan Duy nhất & Ma trận Tích hợp Ngữ cảnh](#c-sơ-đồ-lớp-tổng-quan-duy-nhất--ma-trận-tích-hợp-ngữ-cảnh)
- [D. Bảng Đăng ký Quan hệ (Relationship Register)](#d-bảng-đăng-ký-quan-hệ-relationship-register)
- [E. Chi tiết Kỹ thuật Chủ đích Lược bỏ khỏi Sơ đồ Tổng quan](#e-chi-tiết-kỹ-thuật-chủ-đích-lược-bỏ-khỏi-sơ-đồ-tổng-quan)
- [F. Danh mục Hòa giải Kiến trúc & Trả lời Câu hỏi Mở (C-01..C-06 & Q-01..Q-09)](#f-danh-mục-hòa-giải-kiến-trúc--trả-lời-câu-hỏi-mở-c-01c-06--q-01q-09)
- [G. Danh mục Kiểu Liệt kê (Enum Catalog — Đối chiếu 2 Phía SRS vs DB)](#g-danh-mục-kiểu-liệt-kê-enum-catalog--đối-chiếu-2-phía-srs-vs-db)
- [H. Kết quả Kiểm tra, Bảng Đối chiếu Chất lượng & Đóng Findings](#h-kết-quả-kiểm-tra-bảng-đối-chiếu-chất-lượng--đóng-findings)
- [I. Behavioral Design Class Diagrams & Operation Catalog](#i-behavioral-design-class-diagrams--operation-catalog)

---

## A. Phạm vi, Profile & Giả định Thiết kế

### A.1 Phạm vi và Profile

| Mục | Nội dung Chuẩn hóa |
|---|---|
| **Profile** | **Behavior-enriched Class Diagram (Profile A + các operations cốt lõi của Profile C)**: Giữ bức tranh nghiệp vụ, quan hệ và bội số của Domain Overview; bổ sung có chọn lọc operations thay đổi trạng thái/bảo vệ invariant. Không hiển thị ORM, CRUD, getter/setter, HTTP, Taskiq, adapter, LLM call hay trường khóa kỹ thuật (`id`, `*_id`, UUID, hash, token thô, timestamps kiểm toán). |
| **Thuộc tính & Kiểu dữ liệu** | **100% thuộc tính có kiểu dữ liệu tường minh** (`name : Type`). Mỗi class thể hiện 2–6 thuộc tính mang ý nghĩa nghiệp vụ tiêu biểu nhất. Kiểu thuộc tính viết hoa (như `RoadmapStatus`, `UserStatus`, `TimerMode`, `AlignmentFlag`) là enum nghiệp vụ, tra cứu chi tiết tại [Mục G](#g-danh-mục-kiểu-liệt-kê-enum-catalog--đối-chiếu-2-phía-srs-vs-db). |
| **Bố cục Không gian Tối ưu** | **Bố cục Không gian 3 Cột (Spine Architecture)**: Không sử dụng khung bao package cứng nhằm triệt tiêu hoàn toàn hiện tượng đường nối chồng chéo, đè nhãn hay cắt ngang phức tạp. Phân định Bounded Context trực quan bằng **Bảng màu Ngữ nghĩa (Semantic Color Palette)** trên từng class box (Account: `#EEF2FF`, Planning: `#ECFDF5`, Execution: `#FFFBEB`, Evaluation: `#FDF2F8`). Hiển thị tường minh DDD Stereotypes (`15 <<AggregateRoot>>`, `13 <<Entity>>`, `4 <<ValueObject>>`, `1 <<AssociationClass>>` — tổng 33 classifiers) trên 100% class. |
| **Quan hệ Liên Context** | **Unidirectional Association (`-->`) kèm Stereotype `«references»` & Snapshot Dependency (`..>`)**: Mọi tham chiếu định danh xuyên Bounded Context được chuẩn hóa thành hiệp hội đơn hướng (`--> «references»`), trong khi các bản chụp bằng chứng/trích dẫn bất biến tại thời điểm thực thi được biểu diễn bằng phụ thuộc chụp nhanh (`..> «citationSnapshot»`, `..> «evidenceSnapshot»`). Bảo vệ tuyệt đối nguyên tắc độc lập của Bounded Context trong Modular Monolith (`ADR-001`), ngăn chặn nhầm lẫn về quan hệ ORM hai chiều hay SQL JOIN chéo context. |
| **Trọng tâm Nghiệp vụ** | Thể hiện tường minh 3 trụ cột độc lập: **`Roadmap` (học gì)** $\neq$ **`Schedule` (học khi nào)** $\neq$ **`Learner Model` (học như thế nào)**; AI chỉ tạo `ScheduleProposal(DRAFT)`, chỉ hành động **Apply** của người học mới chuyển hóa thành `OfficialSchedule` sở hữu `ScheduleBlock`; phân biệt rõ Availability Mode A (`DailyHoursQuota`) và Mode B (`AvailabilitySlot`); và luồng bóc tách tri thức RAG (`KnowledgeSource` $\to$ `KnowledgeChunk` $\to$ `Task`). |
| **Mở rộng v11.0 (Post-Review)** | Khắc phục triệt để các tồn tại của v10.0: Thêm `DailyHoursQuota` (Mode A); chuyển `Task./scheduledDate` thành thuộc tính dẫn xuất; bổ sung cờ `isProtected` và `energyLevel`; khôi phục enum `AlignmentFlag` 5 giá trị; loại bỏ enum tự bịa `FLOWMODORO`; loại bỏ `WorkflowRun` khỏi mô hình khái niệm để chuyển sang tài liệu kiến trúc runtime. |

> **Operations có chủ đích:** Sơ đồ tổng hợp hiện hiển thị một tập operations cốt lõi để phục vụ software design. Mục I vẫn cung cấp các behavioral views theo từng bounded context; chúng không làm thay đổi multiplicity/ownership của mô hình miền.

### A.2 Nguồn Tài liệu & Căn cứ Xác minh

| Nguồn Tài liệu | Vai trò Căn cứ |
|---|---|
| `docs/srs/srs-v1.3.md` (SRS Baseline v1.4 CCB Phê duyệt 05/11/2026, 43 FR, 8 Actors ACT-00..ACT-07) | Nguồn căn cứ nghiệp vụ chính cho toàn bộ khái niệm miền, 43 yêu cầu chức năng, vòng đời và máy trạng thái. |
| `docs/uml/use-case-specifications.md` | Đối chiếu hành vi và ranh giới trách nhiệm của 28 Use Cases miền nghiệp vụ (`UC-01..UC-28`). |
| `docs/decisions/` (`ADR-001` đến `ADR-010`) | Ranh giới Bounded Context (`ADR-001`), bộ nhớ người học 4×3 (`ADR-010`), kiểm soát AI và quota (`ADR-009`). |
| `docs/architecture/ai-learning-intelligence-harness.md` | Phân tách 3 thực thể cốt lõi và kiến trúc Shared AI Harness Runtime. |
| `docs/database/schema.sql` v3.2 | Đối chiếu tính khả thi lưu trữ (bội số quan hệ, ràng buộc `CHECK`, `UNIQUE` của 35 bảng vật lý). |

---

## B. Danh mục Khái niệm Miền Cốt lõi & Truy vết 35 Thực thể SRS §12

Dưới đây là danh mục chính xác **33 Khái niệm Miền Nghiệp vụ** (phân bổ trong 4 Bounded Contexts) sau khi bổ sung `DailyHoursQuota` (Mode A) và lược bỏ `WorkflowRun` khỏi mô hình khái niệm:

| # | Khái niệm (Concept) | Phân loại DDD / UML | Miền (Context) | Mục đích Nghiệp vụ Cốt lõi & Thuộc tính Nổi bật | Nguồn tham chiếu | Trạng thái |
|:---:|---|---|---|---|---|:---:|
| **1** | **User** | `<<AggregateRoot>>` | `account` | Người dùng nền tảng: định danh `email : String`, vai trò `role : UserRole`, gói `tier : SubscriptionTier`, `timezone : String`, và trạng thái tài khoản `status : UserStatus`. | SRS v1.4 §12.1 #1; `FR-PROFILE-002` | **CONFIRMED** |
| **2** | **LearnerProfile** | `<<Entity>>` | `account` | Hồ sơ thói quen học tập theo mô hình SRL: thời lượng tập trung tối ưu `optimalFocusDurationMinutes : Integer`, khung giờ năng suất cao `peakProductivitySlots : TimeSlot [0..*]`, hệ số sai lệch ước lượng `estimationBiasFactor : Decimal`, tỷ lệ hoàn thành tuần `weeklyCompletionRate : Decimal`. | SRS §12.1 #2; ADR-010 §3.1 | **CONFIRMED** |
| **3** | **LearnerMemoryItem** | `<<Entity>>` | `account` | Bộ nhớ người học dài hạn: danh mục `category : MemoryCategory`, mức nhận thức `epistemicType : EpistemicType`, nội dung ghi nhớ `claim : String`, độ tin cậy `confidenceScore : Decimal`, cỡ mẫu `sampleSize : Integer [0..1]`, trạng thái xác nhận `confirmationStatus : ConfirmationStatus`. | SRS §12.1 #3; ADR-010 | **CONFIRMED** |
| **4** | **ConceptMastery** | `<<Entity>>` | `account` | Mức độ nắm vững khái niệm của người học: mức xếp hạng `masteryLevel : MasteryLevel`, điểm số chuẩn hóa `masteryScore : Decimal` (0..100), mốc ôn tập tiếp theo `nextReviewAt : Timestamp`. Ràng buộc `{unique(user, concept)}`. | SRS §12.1 #4 | **CONFIRMED** |
| **5** | **AvailabilityProfile** | `<<AggregateRoot>>` | `account` | Cấu hình thời gian rảnh khả dụng của người học: chế độ `mode : AvailabilityMode`, khung giờ ưu tiên `preferredPeriod : String [0..1]`, thời lượng phiên tối thiểu `minSessionMinutes : Integer [0..1]`. | SRS §12.1 #7; `FR-AVAIL-001/003` | **CONFIRMED** |
| **6** | **DailyHoursQuota** | `<<ValueObject>>` | `account` | **Khái niệm mới Mode A (FR-AVAIL-001)**: Quỹ thời gian học tối đa mỗi ngày trong tuần: thứ `dayOfWeek : DayOfWeek`, số giờ khả dụng `hours : Decimal` (`0.5..14.0` giờ/ngày); lưu trữ trong `availabilities.daily_quotas JSONB` được kiểm soát bởi ràng buộc `chk_availabilities_quotas_json` (`fn_validate_daily_quotas`). | SRS §12.1 #7; `FR-AVAIL-001` | **CONFIRMED** |
| **7** | **AvailabilitySlot** | `<<Entity>>` | `account` | Khung giờ rảnh chi tiết Mode B: thứ `dayOfWeek : DayOfWeek`, giờ bắt đầu `startTime : Time`, giờ kết thúc `endTime : Time`, độ lệch ngày `endDayOffset : Integer`, mức năng lượng `energyLevel : EnergyLevel`. | SRS §12.1 #8; `FR-AVAIL-002` | **CONFIRMED** |
| **8** | **CalendarConnection** | `<<Entity>>` | `account` | Liên kết OAuth 2 chiều với ứng dụng lịch bên ngoài (`provider : CalendarProvider`, `syncStatus : ConnectionStatus`) để đồng bộ Free/Busy. | SRS §12.1 #6; `FR-CALENDAR-002` | **CONFIRMED** |
| **9** | **WebCalLink** | `<<Entity>>` | `account` | Luồng cung cấp lịch học chính thức định dạng `.ics` một chiều (WebCal feed) với mã bảo mật băm SHA-256 (`active : Boolean`). | SRS §12.1 #5 | **CONFIRMED** |
| **10** | **AIQuota** | `<<AggregateRoot>>` | `account` | Hạn ngạch cuộc gọi AI theo chu kỳ tháng của người dùng: `monthlyLimit : Integer`, `usedCalls : Integer`. Invariant: `usedCalls + activeReservations <= monthlyLimit`. | SRS §12.1 #9; `FR-QUOTA-001` | **CONFIRMED** |
| **11** | **QuotaReservation** | `<<Entity>>` | `account` | Bản ghi giữ chỗ hạn ngạch 2 pha nguyên tử (`status : ReservationStatus`, `expiresAt : Timestamp`) bảo vệ tài nguyên LLM. | SRS §12.1 #10; AGENTS.md §4 | **CONFIRMED** |
| **12** | **PaymentTransaction** | `<<AggregateRoot>>` | `account` | Giao dịch thanh toán nâng cấp/gia hạn gói Premium: mã đơn `orderCode : String`, số tiền `amount : Decimal`, trạng thái `status : PaymentStatus`, thời hạn `expiresAt : Timestamp` (TTL 15'). | SRS §12.1 #12; `FR-QUOTA-002` | **CONFIRMED** |
| **13** | **PasswordResetToken** | `<<Entity>>` | `account` | Thực thể token đặt lại mật khẩu tự phục vụ qua email: thời hạn `expiresAt : Timestamp` (TTL 15 phút), cờ đã sử dụng `used : Boolean`. | SRS v1.4 §7.1; `FR-AUTH-004` | **CONFIRMED** |
| **14** | **Goal** | `<<AggregateRoot>>` | `planning` | Ý định học tập ban đầu của người học: mô tả mục tiêu `description : String`, trình độ xuất phát `currentLevel : SkillLevel`, ngày đích mong muốn `targetDate : Date`. | SRS §12.2 #13; `FR-GOAL-001` | **CONFIRMED** |
| **15** | **Roadmap** | `<<AggregateRoot>>` | `planning` | Lộ trình học tập tổng thể — xác định **học gì** và thứ tự nào (`title : String`, `status : RoadmapStatus`, `targetDate : Date`), ngân sách dời lịch tuần `weeklyRescheduleBudget : Integer`, `weeklyRescheduleUsed : Integer`, hoạt động cuối `lastStudyActivityAt : Timestamp [0..1]`, số lần reset `resetRitualCount : Integer`, trạng thái ngủ đông `/isDormant : Boolean`. | SRS §1.2, §12.2 #16; `FR-ADAPT-001` | **CONFIRMED** |
| **16** | **Milestone** | `<<Entity>>` | `planning` | Cột mốc kiến thức trung gian trong lộ trình: tên `name : String`, thứ tự `sequenceOrder : Integer`, trạng thái kiểm chứng năng lực `proofStatus : ProofStatus`. | SRS §12.2 #17; `FR-TASK-002` | **CONFIRMED** |
| **17** | **ScheduleProposal** | `<<AggregateRoot>>` | `planning` | Bản đề xuất thời gian biểu (DRAFT) do AI hoặc bộ lập lịch sinh ra: mục đích `purpose : ProposalPurpose`, trạng thái `status : ProposalStatus`, tính khả thi `feasibility : Feasibility [0..1]`. | SRS §12.2 #19, §6.4; `FR-PLAN-002` | **CONFIRMED** |
| **18** | **OfficialSchedule** | `<<AggregateRoot>>` | `planning` | Lịch học chính thức hợp lệ kèm **4 tham số Schedule Resilience**: `bufferMinutesPerWeek : Integer`, `recoveryWindowDays : Integer`, `dailyWorkloadCapMinutes : Integer`, `stabilityWeight : Decimal`. | SRS §12.2 #18, §1.2; `FR-PLAN-005` | **CONFIRMED** |
| **19** | **ScheduleBlock** | `<<Entity>>` | `planning` | Khối thời gian biểu học tập cụ thể — xác định **học khi nào**: phân loại khối `blockType : BlockType`, ngày học `blockDate : Date`, giờ bắt đầu `startTime : Time [0..1]`, thời lượng `scheduledDurationMinutes : Integer`, cờ bảo vệ `isProtected : Boolean`, trạng thái `status : BlockStatus`. | SRS §12.2 #20, §1.5; `FR-PLAN-005` | **CONFIRMED** |
| **20** | **KnowledgeSource** | `<<AggregateRoot>>` | `planning` | Nguồn học liệu người học cung cấp: định dạng `sourceType : SourceType`, trạng thái xử lý `ingestionStatus : IngestionStatus`. | SRS §12.2 #14 | **CONFIRMED** |
| **21** | **KnowledgeChunk** | `<<ValueObject>>` | `planning` | Đoạn tri thức đã chia nhỏ (300–600 tokens) lưu kèm nội dung `content : String` và siêu dữ liệu trích dẫn nguồn gốc `provenance : String`. | SRS §12.2 #15; `FR-GOAL-003` | **CONFIRMED** |
| **22** | **LearningConcept** | `<<AggregateRoot>>` | `planning` | Khái niệm học thuật toàn cục (Global Ground Truth Taxonomy): tên `name : String`, chuẩn đầu ra `learningOutcomes : String`, quan hệ DAG `{acyclic}`. | SRS §12.2 #21; `FR-REPORT-003` | **CONFIRMED** |
| **23** | **Task** | `<<AggregateRoot>>` | `execution` | Nhiệm vụ học tập chi tiết: tiêu đề `title : String`, khối lượng nỗ lực `estimatedMinutes : Integer`, nguồn gốc `origin : TaskOrigin` (`AI`, `MANUAL`), trạng thái `status : TaskStatus`, ngày hạn định dẫn xuất `/scheduledDate : Date [0..1]`, số lần dời lịch `rescheduleCount : Integer`. | SRS §12.3 #23; `FR-TASK-001..003` | **CONFIRMED** |
| **24** | **StudySession** | `<<AggregateRoot>>` | `execution` | Phiên học tập trung thực tế: chế độ `mode : SessionMode`, kiểu đếm giờ `timerMode : TimerMode` (`POMODORO`, `STOPWATCH`), trạng thái `status : SessionStatus`, thời điểm bắt đầu `startedAt : Timestamp`, kết thúc `endedAt : Timestamp [0..1]`, thời lượng thực tế `actualDurationMinutes : Integer [0..1]`, cờ nợ đúc kết `pendingTakeaway : Boolean`. | SRS §12.3 #25, §6.3; `FR-SESSION-001` | **CONFIRMED** |
| **25** | **SessionTask** | `<<AssociationClass>>` | `execution` | Bản ghi kết quả học từng Task trong một phiên (`session_tasks`): thời lượng phân bổ `allocatedMinutes : Integer`, thời lượng học thực tế `actualMinutes : Integer`, trạng thái sau phiên `statusAfterSession : SessionTaskStatus` (`TODO`, `IN_PROGRESS`, `COMPLETED`), ghi chú `notes : String [0..1]`. | SRS §12.3 #26; OMG UML §11.5 | **CONFIRMED** |
| **26** | **DailyCheckin** | `<<ValueObject>>` | `execution` | 3 tín hiệu khảo sát nhanh cuối phiên học: đủ thời gian `timeSufficiency : TimeSufficiency` (`TOO_SHORT`, `JUST_RIGHT`, `TOO_LONG`), độ khó cảm nhận `perceivedDifficulty : Integer`, mức độ tập trung `focusLevel : Integer`. | SRS §1.2, §12.3 #25; `FR-SESSION-002` | **CONFIRMED** |
| **27** | **StudyNote** | `<<Entity>>` | `execution` | Ghi chép học tập trong phiên: nội dung `content : String`. | SRS §12.3 #27 | **CONFIRMED** |
| **28** | **KeyTakeaway** | `<<Entity>>` | `execution` | Đúc kết cốt lõi chuyên biệt (`StudyNote <\|-- KeyTakeaway`): điểm tự tin `selfConfidence : Integer`, trạng thái xác thực `verificationStatus : TakeawayVerification`, cờ lệch mục tiêu chuẩn hóa `alignmentFlag : AlignmentFlag` (Enum 5 giá trị), điểm bằng chứng AI `aiEvidenceScore : Decimal (1.00..5.00)`. | SRS §12.3 #27; `FR-REPORT-003` | **CONFIRMED** |
| **29** | **MilestoneProof** | `<<AggregateRoot>>` | `evaluation` | Bản ghi kiểm chứng năng lực Prove Mode: số lần thi `attemptNo : Integer`, phán quyết `verdict : ProofVerdict`, điểm tự tin trung bình `avgSelfConfidence : Decimal`, điểm bằng chứng AI `aiEvidenceScore : Decimal`, độ lệch hiệu chỉnh `/calibrationGap : Decimal`. | SRS §12.4 #31; `FR-REPORT-003` | **CONFIRMED** |
| **30** | **MistakeTaxonomy** | `<<ValueObject>>` | `evaluation` | Phân loại sai lầm theo 4 nhóm Trí tuệ Sai lầm (`cause : MistakeCause`), liên kết Composition với `MilestoneProof`. | SRS §1.5, §12.4 #31 | **CONFIRMED** |
| **31** | **AIReview** | `<<AggregateRoot>>` | `evaluation` | Đánh giá tổng kết định kỳ: chu kỳ `cycle : ReviewCycle`, điểm mạnh `strengthsFeedback : String`, điểm nghẽn `bottlenecksFeedback : String`, đề xuất hành động `actionRecommendations : String`, phản tư người học `userReflection : String [0..1]`. | SRS §12.4 #29; `FR-REPORT-002` | **CONFIRMED** |
| **32** | **PauseRecord** | `<<AggregateRoot>>` | `evaluation` | Bản ghi tạm dừng lộ trình học tập có chủ đích: ngày bắt đầu `startDate : Date`, ngày kết thúc `endDate : Date`, trạng thái `status : PauseStatus`, số ngày dời lịch không phạt `shiftedDays : Integer`. | SRS §12.4 #28; `FR-PAUSE-001` | **CONFIRMED** |
| **33** | **ScheduleChangeLog** | `<<Entity>>` | `evaluation` | Bản ghi biến động lịch học quản lý ngân sách dời lịch: tác nhân kích hoạt `trigger : ChangeTriggerType`, phân loại gián đoạn `disruptionCategory : DisruptionCategory`, cờ trừ ngân sách `countsTowardBudget : Boolean`. | SRS §12.4 #30; `FR-ADAPT-001` | **CONFIRMED** |

> **Tổng hợp Phân loại Stereotype (33 Classifiers):** `15 <<AggregateRoot>>` + `13 <<Entity>>` + `4 <<ValueObject>>` (`DailyHoursQuota`, `KnowledgeChunk`, `DailyCheckin`, `MistakeTaxonomy`) + `1 <<AssociationClass>>` (`SessionTask`) = **33 Classifiers**.

---

## C. Sơ đồ Lớp Tổng quan Duy nhất & Ma trận Tích hợp Ngữ cảnh

### C.1 Hình ảnh Sơ đồ Lớp Tổng quan Hệ thống (System Domain Overview Class Diagram)

Sơ đồ thể hiện đầy đủ 33 khái niệm nghiệp vụ (`15 <<AggregateRoot>>`, `13 <<Entity>>`, `4 <<ValueObject>>`, `1 <<AssociationClass>>`), 23 quan hệ liên kết nội bộ ngữ cảnh (gồm 6 Composition, 1 Generalization, 1 Association Class, 3 Self-associations), 14 quan hệ chéo context (12 Unidirectional Associations `--> «references»` + 2 Snapshot Dependencies `..> «citationSnapshot»` / `«evidenceSnapshot»`) và 1 quan hệ phụ thuộc hành vi (`ScheduleProposal ..> OfficialSchedule : «materializes on Apply»`):

> ![FocusFlow System Domain Overview](images/FocusFlow_Class_Diagram.png)

*Tệp mã nguồn PlantUML chuẩn:* [`docs/uml/class-diagrams/class-diagram.puml`](class-diagrams/class-diagram.puml)

| STT | Sơ đồ | Mã nguồn PlantUML | Tệp ảnh PNG | Quy mô Classifier | Tổng số Quan hệ |
|:---:|---|---|---|:---:|:---:|
| **1** | **FocusFlow System Domain Overview v11.0** | [`class-diagram.puml`](class-diagrams/class-diagram.puml) | [`FocusFlow_Class_Diagram.png`](images/FocusFlow_Class_Diagram.png) | **33 Classifiers** | **23 Nội bộ + 14 Quan hệ Chéo Context (12 «references» + 2 Snapshot) + 1 Dependency = 38 Đường nối** |

---

### C.2 Ma trận Tích hợp Ranh giới Ngữ cảnh (Strategic Context Integration Register)

Tuân thủ nghiêm ngặt kiến trúc Context-First Modular Monolith (`ADR-001`), các Bounded Context tích hợp thông qua hai cơ chế chuẩn: **Query Port (Đọc đồng bộ nội bộ)** và **Outbox Event (Phản ứng bất đồng bộ qua Redis Streams)**:

| Ngữ cảnh Phát (Upstream) | Ngữ cảnh Nhận (Downstream) | Cơ chế Tích hợp | Nội dung Trao đổi Dữ liệu | Căn cứ Kiến trúc |
|---|---|---|---|---|
| `account` | `planning` | **Query Port** | `UnifiedAvailabilityModel` (khung giờ rảnh Mode A/B đã khấu trừ lịch ngoại vi), `LearnerMemorySummary`, yêu cầu giữ chỗ hạn ngạch AI. | `ADR-001 §3.1` (CONFIRMED) |
| `planning` | `execution` | **Query Port** | Danh sách bài học của Roadmap, thông tin Cột mốc và các khối `ScheduleBlock` đã lên lịch cho ngày hôm nay. | `UC-EXEC-01` (INFERRED) |
| `planning` | `evaluation` | **Query Port** | Cấu trúc Roadmap và thông tin Cột mốc cần kiểm chứng hoặc đánh giá. | `UC-ADAPT-02/03` (INFERRED) |
| `execution` | `evaluation` | **Query Port** | Lịch sử phiên học `StudySession`, kết quả `SessionTask` và đúc kết `KeyTakeaway` làm bằng chứng cho Prove Mode. | `UC-ADAPT-02/03` (INFERRED) |
| `account` | `execution`, `evaluation` | **Query Port** | Kiểm tra quyền hạn, trạng thái tài khoản `User.status = 'ACTIVE'` và số dư hạn ngạch AI trước khi gọi LLM. | `AGENTS.md §4`, `FR-PROFILE-002` (CONFIRMED) |
| `execution` | `evaluation` | **Outbox Event** | `StudySessionCompletedEvent`: Thông báo phiên học hoàn thành để cập nhật chuỗi ngày học liên tục (Streak). | `ADR-001 §3.2` (CONFIRMED) |
| `evaluation` | `account` | **Outbox Event** | `MilestoneProofEvaluatedEvent`: Cập nhật điểm thành thạo `ConceptMastery.masteryScore` và thăng hạng kỹ năng cho người học. | `ADR-001 §3.2` (CONFIRMED) |
| `account` | `planning` | **Outbox Event** | `UserUpgradedToPremiumEvent`: Mở khóa các tính năng lập kế hoạch nâng cao (như tải tài liệu RAG dung lượng lớn). | `ADR-001 §3.2` (CONFIRMED) |
| `planning` | `execution` | **Outbox Event** | `OfficialScheduleAppliedEvent`: Kích hoạt cập nhật thời gian biểu chính thức sang không gian thực thi học tập. | `ADR-001 §3.2` (CONFIRMED) |
| `account` | Cả 4 Context | **Outbox Event** | `UserAccountDeletedEvent`: Kích hoạt hủy bỏ các tác vụ tương lai, thu hồi token, revoke lịch kết nối khi tài khoản bị xóa theo GDPR Điều 17. | `FR-PROFILE-002` (CONFIRMED) |

---

## D. Bảng Đăng ký Quan hệ (Relationship Register)

### D.1 Quan hệ Liên kết Nội bộ Ngữ cảnh (Internal Relationships — 23 Quan hệ)

| Mã | Từ Lớp (From) | Quan hệ Nghiệp vụ | Tới Lớp (To) | Bội số (From $\to$ To) | Bội số (To $\to$ From) | Căn cứ Xác minh & Ghi chú |
|:---:|---|---|---|:---:|:---:|---|
| **R-01** | `User` | có hồ sơ thói quen | `LearnerProfile` | 0..1 | 1 | SRS §12.1 #2; `uq_learner_profiles_user_id` |
| **R-02** | `User` | có bộ nhớ cá nhân hóa | `LearnerMemoryItem` | 0..* | 1 | SRS §12.1 #3; `uq_learner_memory_items_user_cat_key` |
| **R-03** | `User` | đạt mức thành thạo | `ConceptMastery` | 0..* | 1 | SRS §12.1 #4; `uq_learner_concept_masteries_user_concept` |
| **R-04** | `User` | cấu hình thời gian rảnh | `AvailabilityProfile` | 0..1 | 1 | SRS §12.1 #7; `uq_availabilities_user_id` |
| **R-04a** | `AvailabilityProfile` | cấu hình quỹ giờ Mode A (`*--`) | `DailyHoursQuota` | 0..* | 1 | SRS §12.1 #7; `FR-AVAIL-001` (Composition Mode A) |
| **R-04b** | `AvailabilityProfile` | cấu hình khung giờ Mode B (`*--`) | `AvailabilitySlot` | 0..* | 1 | SRS §12.1 #8; `FR-AVAIL-002` (Composition Mode B) |
| **R-05** | `User` | liên kết ứng dụng lịch | `CalendarConnection` | 0..* | 1 | SRS §12.1 #6; `uq_calendar_connections_user_provider` |
| **R-06** | `User` | đăng ký luồng WebCal | `WebCalLink` | 0..1 | 1 | SRS §12.1 #5 (quan hệ 1-1 với User) |
| **R-07** | `User` | được cấp hạn mức | `AIQuota` | 1 | 1 | SRS §12.1 #9; `FR-AUTH-001` (Cấp quota ngay khi đăng ký) |
| **R-08** | `AIQuota` | giữ chỗ an toàn 2 pha | `QuotaReservation` | 0..* | 1 | SRS §12.1 #10; AGENTS.md §4 |
| **R-09** | `User` | giao dịch thanh toán | `PaymentTransaction` | 0..* | 1 | SRS §12.1 #12; `FR-QUOTA-002` |
| **R-10** | `User` | yêu cầu đặt lại mật khẩu | `PasswordResetToken` | 0..* | 1 | SRS v1.4 §7.1; `FR-AUTH-004` |
| **R-12** | `Goal` | được phân rã thành | `Roadmap` | 1 | 1 | SRS §6.1, §12.2 #13/#16 (Bội số 1:1 tuyệt đối) |
| **R-13** | `Goal` | đính kèm tài liệu học | `KnowledgeSource` | 0..* | 1 | SRS §12.2 #14 |
| **R-14** | `KnowledgeSource` | phân đoạn tri thức (`*--`) | `KnowledgeChunk` | 0..* | 1 | SRS §12.2 #15 (Composition) |
| **R-15** | `Roadmap` | gồm các cột mốc | `Milestone` | 0..* | 1 | SRS §12.2 #17 |
| **R-16** | `Roadmap` | có lịch chính thức | `OfficialSchedule` | 0..1 | 1 | `schema.sql`: `uq_official_schedules_roadmap` |
| **R-17** | `Roadmap` | có bản đề xuất lịch | `ScheduleProposal` | 0..* | 1 | SRS §12.2 #19 |
| **R-18** | `OfficialSchedule` | sở hữu khối lịch (`*--`) | `ScheduleBlock` | 0..* | 1 | SRS §12.2 #20 (Composition chính thức) |
| **R-20** | `LearningConcept` | yêu cầu tiên quyết (`-right->`) | `LearningConcept` | 0..* | 0..* | SRS §12.2 #22 (Đồ thị Tiên quyết Tri thức `{acyclic}`) |
| **R-22** | `StudySession` | học trong phiên (`--`) | `Task` | 1..* | 0..* | SRS §12.3 #26; `FR-SESSION-001` (chọn $\ge 1$ task) |
| **R-22ac**| `(StudySession, Task)`| liên kết thuộc tính (`..`) | `SessionTask` | — | — | SRS §12.3 #26; OMG UML §11.5 |
| **R-24** | `StudySession` | kết thúc với khảo sát (`*--`) | `DailyCheckin` | 0..1 | 1 | SRS §1.2, §12.3 #25 (Composition) |
| **R-25** | `StudySession` | ghi lại ghi chú | `StudyNote` | 0..* | 1 | SRS §12.3 #27 (ghi chú thuộc phiên) |
| **R-26** | `StudyNote` | kế thừa chuyên biệt (`<\|--`) | `KeyTakeaway` | — | — | SRS §12.3 #27 (`alignmentFlag` Enum 5 giá trị) |
| **R-27** | `Task` (cha) | chia nhỏ bước con (`-up->`) | `Task` (con) | 0..* | 0..1 | SRS §12.3 #23 (Micro-Stepping) |
| **R-28** | `Task` (trước) | điều kiện tiên quyết (`-down->`) | `Task` (sau) | 0..* | 0..* | SRS §12.3 #24; `FR-TASK-003` (DAG `{acyclic}`) |
| **R-29** | `MilestoneProof` | phân loại nguyên nhân lỗi (`*--`) | `MistakeTaxonomy` | 0..* | 1 | SRS §12.4 #31 (Mistake Intelligence Composition) |

---

### D.2 Quan hệ Tham chiếu & Chụp nhanh Đơn hướng Liên Bounded Context (`--> «references»` & `..> «*Snapshot»` — 14 Quan hệ)

| Mã | Thực thể Nguồn (From) | Quan hệ Tham chiếu | Thực thể Đích (To) | Bội số Tham chiếu | Căn cứ Xác minh & Ghi chú |
|:---:|---|---|---|:---:|---|
| **U-01** | `Goal` (`planning`) | `--> «references»` | `User` (`account`) | 0..* $\to$ 1 | SRS §12.2 #13; kiểm soát quyền sở hữu IDOR |
| **U-02** | `Task` (`execution`) | `--> «references»` | `Roadmap` (`planning`) | 0..* $\to$ 1 | SRS §12.3 #23; neo vào lộ trình học |
| **U-03** | `Task` (`execution`) | `--> «references»` | `Milestone` (`planning`) | 0..* $\to$ 1 | SRS §12.3 #23; thuộc cột mốc cụ thể |
| **U-04** | `Task` (`execution`) | `--> «references»` | `LearningConcept` (`planning`) | 0..* $\to$ 0..1 | SRS §12.3 #23; nhiệm vụ giảng dạy khái niệm |
| **U-05** | `Task` (`execution`) | `..> «citationSnapshot»` | `KnowledgeChunk` (`planning`) | Snapshot JSONB | Lưu bất biến danh sách trích dẫn `chunk_id` + đoạn trích trong `tasks.learning_resources_json` (`FR-GOAL-003`) |
| **U-06** | `ScheduleBlock` (`planning`) | `--> «references»` | `Task` (`execution`) | 0..* $\to$ 0..1 | SRS §12.2 #20 (khối Buffer/Recovery không gắn Task) |
| **U-07** | `StudyNote` (`execution`) | `--> «references»` | `Task` (`execution`) | 0..* $\to$ 0..1 | **Quan hệ mới M-03**: Ghi chú neo vào bài học cụ thể trong phiên |
| **U-08** | `ConceptMastery` (`account`) | `--> «references»` | `LearningConcept` (`planning`) | 0..* $\to$ 1 | SRS §12.1 #4; đo lường năng lực trên Đồ thị Tri thức |
| **U-09** | `MilestoneProof` (`evaluation`) | `--> «references»` | `Milestone` (`planning`) | 0..* $\to$ 1 | SRS §12.4 #31; kiểm chứng hoàn thành cột mốc |
| **U-10** | `MilestoneProof` (`evaluation`) | `..> «evidenceSnapshot»` | `KeyTakeaway` (`execution`) | Snapshot JSONB | Lưu bất biến bằng chứng đối chất từ `study_notes (TAKEAWAY)` vào `milestone_proofs.recall_exchanges_payload` (`FR-REPORT-003`) |
| **U-11** | `MilestoneProof` (`evaluation`) | `--> «references»` | `Task` (`execution`) | 0..* $\to$ 0..1 | SRS §12.4 #31 (`correctiveTask` bài ôn tập bổ trợ) |
| **U-12** | `AIReview` (`evaluation`) | `--> «references»` | `Roadmap` (`planning`) | 0..* $\to$ 1 | SRS §12.4 #29; đánh giá định kỳ theo lộ trình |
| **U-13** | `PauseRecord` (`evaluation`) | `--> «references»` | `Roadmap` (`planning`) | 0..* $\to$ 1 | SRS §12.4 #28; tạm dừng một lộ trình cụ thể |
| **U-14** | `ScheduleChangeLog` (`evaluation`) | `--> «references»` | `Roadmap` (`planning`) | 0..* $\to$ 1 | SRS §12.4 #30; ghi vết biến động lịch theo lộ trình |

---

### D.3 Quan hệ Phụ thuộc Hành vi (Behavioral Dependency — 1 Quan hệ)

| Mã | Thực thể Nguồn (From) | Ký hiệu | Thực thể Đích (To) | Ngữ nghĩa Hành vi |
|:---:|---|---|---|---|
| **DEP-01** | `ScheduleProposal` | `..>` | `OfficialSchedule` | `«materializes on Apply»`: Bản đề xuất nháp chỉ chuyển hóa thành khối lịch chính thức khi người học bấm Apply (`FR-PLAN-002`, `BUSR-02`). |

---

## E. Chi tiết Kỹ thuật Chủ đích Lược bỏ khỏi Sơ đồ Tổng quan

Theo đúng chuẩn **Profile A (Domain Overview)**, các bảng kỹ thuật/hạ tầng thuần túy được chủ đích tách khỏi sơ đồ lớp tổng quan để bảo vệ khả năng đọc hiểu nghiệp vụ:

### E.1 Các Bảng Cơ sở Dữ liệu Không Vẽ Thành Class Riêng trên Sơ đồ Tổng quan (7 Bảng)

| Bảng CSDL (`schema.sql` v3.2) | Context | Lý do Lược bỏ khỏi Sơ đồ Tổng quan | Nơi Thể hiện Chuẩn xác |
|---|---|---|---|
| `ai_usage_logs` | `account` | Bản ghi kỹ thuật quan sát vận hành (token, latency ms, chi phí USD, model LLM); không chứa hành vi miền cốt lõi. | ERD vật lý (`schema.sql`), Báo cáo Giám sát Admin (`UC-ADM-06`). |
| `concept_prerequisites` | `planning` | Bảng quan hệ N:N giữa các `LearningConcept`; đã được thể hiện trực quan bằng **Reflexive Association có hướng `R-20` (`{acyclic}`)** trên sơ đồ. | ERD vật lý (`schema.sql`). |
| `task_dependencies` | `execution` | Bảng quan hệ N:N đồ thị DAG giữa các `Task`; đã được thể hiện trực tiếp bằng **Reflexive Association có hướng `R-28` (`{acyclic}`)** trên sơ đồ. | ERD vật lý (`schema.sql`). |
| `workflow_runs` | `shared_kernel` | Thực thể điều phối quy trình bền vững (Durable Saga Orchestration) thuộc hạ tầng kỹ thuật (Solution Space). | Tài liệu Thiết kế Kiến trúc Runtime (`ADR-001 §3.5`). |
| `workflow_step_executions` | `shared_kernel` | Nhật ký thực thi từng bước con kỹ thuật trong một phiên quy trình `WorkflowRun`. | ERD vật lý (`schema.sql`), Đặc tả Durable Workflow State. |
| `outbox_events` | `shared_kernel` | Bảng hạ tầng phục vụ mẫu thiết kế Transactional Outbox đảm bảo phát sự kiện At-Least-Once qua Redis Streams. | ERD vật lý (`schema.sql`), Ma trận Tích hợp Ngữ cảnh (Mục C.2). |
| `processed_events` | `shared_kernel` | Bảng hạ tầng kiểm soát lũy đẳng (Idempotent Consumer) khi tiêu thụ sự kiện liên context. | ERD vật lý (`schema.sql`). |

> **Bảo toàn Số lượng 35 Bảng CSDL Vật lý & 33 Classifiers Khớp 100%:**  
> - **Phân bổ 33 Classifiers trên Sơ đồ Tổng quan**: `15 <<AggregateRoot>>` + `13 <<Entity>>` + `4 <<ValueObject>>` + `1 <<AssociationClass>>` = **33 Classifiers**.  
> - **28 Bảng CSDL** được mô hình hóa trực tiếp thành Domain Entities, Aggregate Roots, Association Class (và bảng `knowledge_chunks` cho `KnowledgeChunk`) trên Sơ đồ Tổng quan.  
> - **7 Bảng Kỹ thuật/Junction** liệt kê tại Mục E.1.  
> $\Rightarrow \mathbf{28 + 7 = 35}$ **bảng CSDL vật lý của `schema.sql` v3.2**.  
> - **Các Value Objects nhúng trực tiếp không tạo bảng riêng**: `DailyHoursQuota` lưu trong `availabilities.daily_quotas JSONB` (ràng buộc `chk_availabilities_quotas_json` / `fn_validate_daily_quotas`: `0.5..14.0` giờ/ngày); `DailyCheckin` lưu các trường trong `study_sessions`; `MistakeTaxonomy` lưu trong `milestone_proofs` (`mistake_taxonomy_json`); riêng `KnowledgeChunk` lưu trong bảng `knowledge_chunks`.  
> - **Lý do Thiết kế Phụ thuộc Chụp nhanh Bất biến (`U-05` & `U-10`) thay vì Bảng Trung gian M:N**: Hai quan hệ `U-05` (`Task ..> KnowledgeChunk : «citationSnapshot»`) và `U-10` (`MilestoneProof ..> KeyTakeaway : «evidenceSnapshot»`) được mô hình hóa là các phụ thuộc chụp nhanh lưu trong JSONB (`tasks.learning_resources_json` và `milestone_proofs.recall_exchanges_payload`) thay vì bảng nối M:N có khóa ngoại. Thiết kế này ghi nhận **bản chụp kiểm toán/nguồn gốc bất biến tại đúng thời điểm thực thi (immutable point-in-time audit/provenance snapshot)** khi AI sinh nhiệm vụ học tập hoặc tiến hành phiên vấn đáp Prove Mode, bảo đảm toàn vẹn lịch sử đối soát ngay cả khi người học về sau chỉnh sửa/xóa ghi chú hoặc tái lập chỉ mục (re-index) tài liệu RAG.

---

## F. Danh mục Hòa giải Kiến trúc & Trả lời Câu hỏi Mở (C-01..C-06 & Q-01..Q-09)

### F.1 Các Quyết định Kiến trúc Chuẩn hóa v11.0 (C-01..C-06)

1. **`C-01` — Chuẩn hóa `SessionTask` dưới dạng Association Class**:  
   - Giữ nguyên Association Class `SessionTask` nối nét đứt giữa `StudySession` và `Task` theo đúng OMG UML 2.5.1 (§11.5) để lưu kết quả thực thi của từng bài học trong phiên.
2. **`C-02` — Thay thế Dependency `«by id»` bằng Unidirectional Association `--> «references»`**:  
   - Khắc phục lỗi D-H01/F-01: Thay toàn bộ các đường nét đứt kèm multiplicity sai cú pháp bằng **Hiệp hội đơn hướng có hướng (`-->`)** kèm stereotype **`«references»`**. Vừa bảo đảm tính hợp chuẩn UML 2.5.1 (đầu đích có multiplicity), vừa giữ vững nguyên tắc tham chiếu theo định danh của Domain-Driven Design (Vaughn Vernon Rule 3).
3. **`C-03` — Cố định Bội số `Goal "1" -- "1" Roadmap`**:  
   - Đóng chính thức câu hỏi `Q-01`: Theo SRS §6.1, một lộ trình hoàn thành/lưu trữ là read-only, muốn học tiếp phải tạo Goal mới. Bội số chuẩn là **1:1 tuyệt đối**. Xóa bỏ ghi chú cũ "duy nhất 1 active".
4. **`C-04` — Loại bỏ Thuộc tính JSON Thừa trên `MilestoneProof`**:  
   - Khắc phục lỗi D-M02: Xóa bỏ thuộc tính kỹ thuật `mistakeTaxonomyJson` trên `MilestoneProof`, giữ nguyên quan hệ hợp thành (`*--`) với Value Object `MistakeTaxonomy`.
5. **`C-05` — Bổ sung Lớp `DailyHoursQuota` Biểu diễn Mode A (`FR-AVAIL-001`)**:  
   - Khắc phục lỗi F-03: Bổ sung lớp `DailyHoursQuota` (dayOfWeek, hours) hợp thành từ `AvailabilityProfile` để biểu diễn quỹ giờ học mỗi ngày (0.5..14.0 giờ/ngày).
6. **`C-06` — Chuẩn hóa Sở hữu `ScheduleBlock` & Phân định Ranh giới Proposal**:  
   - Khắc phục lỗi D-H02/F-02: Khẳng định `OfficialSchedule 1 *-- 0..* ScheduleBlock`. Bản đề xuất `ScheduleProposal` liên kết chuyển hóa khi Apply qua phụ thuộc hành vi `DEP-01`, loại bỏ ràng buộc `{xor}` lỏng lẻo.

---

### F.2 Bảng Trả lời & Đóng 9 Câu hỏi Kiến trúc Mở (Q-01..Q-09)

| Mã | Câu hỏi Mở Kiến trúc | Quyết định Chính thức cho Baseline v11.0 | Trạng thái |
|:---:|---|---|:---:|
| **Q-01** | Bội số Goal – Roadmap: 1:1 hay 1:0..*? | **Chốt 1:1 Tuyệt đối**: Theo SRS §6.1, mỗi Goal gắn với đúng 1 Roadmap. Khi hoàn thành muốn học tiếp phải tạo Goal mới. | **CLOSED** |
| **Q-02** | StudyNote có bắt buộc gắn Task không? | **Tùy chọn (`0..1`)**: Bổ sung Unidirectional Association `StudyNote --> Task` với multiplicity `0..1` (hỗ trợ ghi chú chung lẫn ghi chú bài học). | **CLOSED** |
| **Q-03** | Số lượng Milestone tối thiểu khi Roadmap `INITIALIZED`? | **Giữ `0..*`**: Khi vừa khởi tạo khung, AI chưa phân rã xong thì danh sách cột mốc có thể tạm thời rỗng trước khi chuyển sang `ACTIVE`. | **CLOSED** |
| **Q-04** | Bản chất `ScheduleChangeLog`? | **Entity Miền**: Giữ nguyên trong context `evaluation` vì tham gia trực tiếp vào logic kiểm soát Ngân sách dời lịch tuần (3 lượt/tuần). | **CLOSED** |
| **Q-05** | Có cần tách thực thể `Subscription` riêng? | **Không tách**: Quản lý gói cước trực tiếp qua `User.tier`, `User.premiumExpiresAt` và lịch sử `PaymentTransaction` để bảo toàn trần 35 thực thể. | **CLOSED** |
| **Q-06** | Khởi tạo Quota khi đăng ký? | **Eager Init (`1:1`)**: Theo `FR-AUTH-001`, `AIQuota` được cấp phát ngay lập tức khi đăng ký. Bội số sửa thành `User "1" -- "1" AIQuota`. | **CLOSED** |
| **Q-07** | Lưu trữ khối lịch của Proposal? | **OfficialSchedule sở hữu**: `OfficialSchedule *-- ScheduleBlock`. Bản đề xuất nháp lưu JSON, chuyển hóa thành block chính thức khi Apply. | **CLOSED** |
| **Q-08** | Phiên học có bắt buộc chọn Task không? | **Bắt buộc chọn $\ge 1$ Task (`1..*`)**: Theo `FR-SESSION-001`, sửa bội số thành `StudySession "0..*" -- "1..*" Task`. | **CLOSED** |
| **Q-09** | Tần suất đồng bộ Bounded Context? | **Duy trì Ma trận Mục C.2**: Đọc đồng bộ qua Query Port và phát sinh Outbox Event qua Redis Streams, kiểm thử tải bảo đảm SLA. | **CLOSED** |

---

## G. Danh mục Kiểu Liệt kê (Enum Catalog — Đối chiếu 2 Phía SRS vs DB)

### G.1 Bảng Đối chiếu 4 Kiểu Liệt kê Giữa SRS và CSDL

| # | Kiểu Enum | Ngữ cảnh | Thuộc tính Sử dụng | Giá trị theo SRS v1.4 | Giá trị theo CSDL (`schema.sql` v3.2) | Quyết định Chuẩn hóa v11.0 |
|:---:|---|---|---|---|---|---|
| **1** | `MasteryLevel` | `account` | `ConceptMastery.masteryLevel` | `NOVICE`, `DEVELOPING`, `PROFICIENT`, `MASTERED` | `NOVICE`, `DEVELOPING`, `PROFICIENT`, `MASTERED` | Đồng bộ 100% giữa SRS v1.4, Class Diagram v11.0 và PostgreSQL DDL v3.2 (không còn sai lệch). |
| **2** | `IngestionStatus` | `planning` | `KnowledgeSource.ingestionStatus` | `PENDING`, `PROCESSING`, `INDEXED`, `FAILED`, `QUARANTINED` | `PENDING`, `PROCESSING`, `INDEXED`, `FAILED`, `QUARANTINED` | Đồng bộ 100% giữa SRS v1.4, Class Diagram v11.0 và PostgreSQL DDL v3.2 (không còn sai lệch). |
| **3** | `BlockStatus` | `planning` | `ScheduleBlock.status` | `PLANNED`, `COMPLETED`, `MISSED`, `RESCHEDULED`, `CANCELLED` | `PLANNED`, `COMPLETED`, `MISSED`, `RESCHEDULED`, `CANCELLED` | Đồng bộ 100% giữa SRS v1.4, Class Diagram v11.0 và PostgreSQL DDL v3.2 (không còn sai lệch). |
| **4** | `NoteType` | `execution` | `StudyNote.noteType` | `SCRATCHPAD`, `TAKEAWAY` | `SCRATCHPAD`, `TAKEAWAY`, `GENERAL` | Giữ 3 giá trị theo CSDL để hỗ trợ ghi chú ngoài phiên. |

---

### G.2 Toàn bộ Danh mục 39 Kiểu Liệt kê Nghiệp vụ Chuẩn hóa

| # | Kiểu Enum | Ngữ cảnh | Thuộc tính Sử dụng | Danh sách Giá trị Chuẩn hóa | Ghi chú & Nguồn quy định |
|:---:|---|---|---|---|---|
| 1 | `UserRole` | `account` | `User.role` | `LEARNER`, `ADMIN` | Phân quyền truy cập nền tảng (SRS §12.1 #1) |
| 2 | `SubscriptionTier` | `account` | `User.tier` | `FREE`, `PREMIUM` | Phân tầng dịch vụ và hạn ngạch (SRS §12.1 #1) |
| 3 | `UserStatus` | `account` | `User.status` | `ACTIVE`, `LOCKED`, `DELETED` | Vòng đời tài khoản & GDPR Điều 17 (`FR-PROFILE-002`) |
| 4 | `AvailabilityMode` | `account` | `AvailabilityProfile.mode` | `MODE_A`, `MODE_B` | Chế độ giờ rảnh (Mode A: hạn ngạch, Mode B: lịch tuần) |
| 5 | `DayOfWeek` | `account` | `DailyHoursQuota.dayOfWeek`, `AvailabilitySlot.dayOfWeek` | `MONDAY`, `TUESDAY`, `WEDNESDAY`, `THURSDAY`, `FRIDAY`, `SATURDAY`, `SUNDAY` | Các ngày trong tuần (`FR-AVAIL-001/002`) |
| 6 | `EnergyLevel` | `account` | `AvailabilitySlot.energyLevel` | `LOW`, `MEDIUM`, `HIGH` | Mức năng lượng cho Energy-Aware Scheduling (`FR-AVAIL-002`) |
| 7 | `CalendarProvider` | `account` | `CalendarConnection.provider` | `GOOGLE`, `OUTLOOK`, `LOCAL_MOCK` | Nhà cung cấp lịch ngoại vi (SRS §12.1 #6) |
| 8 | `ConnectionStatus` | `account` | `CalendarConnection.syncStatus` | `ACTIVE`, `REVOKED`, `ERROR` | Trạng thái đồng bộ lịch OAuth (SRS §12.1 #6) |
| 9 | `MemoryCategory` | `account` | `LearnerMemoryItem.category` | `PROFILE`, `BEHAVIORAL`, `KNOWLEDGE`, `INTERACTION` | 4 danh mục bộ nhớ dài hạn (ADR-010 §3.2) |
| 10 | `EpistemicType` | `account` | `LearnerMemoryItem.epistemicType` | `EXPLICIT`, `OBSERVED`, `INFERRED` | 3 mức độ nhận thức dữ liệu (ADR-010) |
| 11 | `ConfirmationStatus` | `account` | `LearnerMemoryItem.confirmationStatus` | `UNCONFIRMED`, `CONFIRMED`, `REJECTED`, `EDITED` | Trạng thái xác nhận người học (ADR-010) |
| 12 | `MasteryLevel` | `account` | `ConceptMastery.masteryLevel` | `NOVICE`, `DEVELOPING`, `PROFICIENT`, `MASTERED` | Mức độ làm chủ khái niệm (SRS §12.1 #4) |
| 13 | `ReservationStatus` | `account` | `QuotaReservation.status` | `RESERVED`, `COMMITTED`, `RELEASED`, `EXPIRED` | Vòng đời 2 pha giữ chỗ Quota AI (ADR-009) |
| 14 | `PaymentStatus` | `account` | `PaymentTransaction.status` | `PENDING`, `PAID`, `FAILED`, `CANCELLED`, `EXPIRED` | Trạng thái giao dịch Premium (SRS §12.1 #12) |
| 15 | `SkillLevel` | `planning` | `Goal.currentLevel` | `BEGINNER`, `INTERMEDIATE`, `ADVANCED` | Trình độ xuất phát của mục tiêu (SRS §12.2 #13) |
| 16 | `RoadmapStatus` | `planning` | `Roadmap.status` | `INITIALIZED`, `ACTIVE`, `PAUSED`, `COMPLETED`, `ARCHIVED` | Vòng đời lộ trình học tập (SRS §6.1) |
| 17 | `ProofStatus` | `planning` | `Milestone.proofStatus` | `UNVERIFIED`, `PENDING_REVIEW`, `PROVEN`, `NEEDS_REVIEW` | Trạng thái kiểm chứng năng lực Cột mốc (SRS §6.2) |
| 18 | `ProposalPurpose` | `planning` | `ScheduleProposal.purpose` | `INITIAL_SCHEDULE`, `AI_RECOVERY`, `POST_FAILURE_RESET`, `WHAT_IF_SIMULATION`, `SCHEDULE_ONLY_REOPTIMIZE` | Mục đích sinh bản đề xuất lịch (SRS §12.2 #19) |
| 19 | `ProposalStatus` | `planning` | `ScheduleProposal.status` | `DRAFT`, `APPLIED`, `DISCARDED` | Vòng đời bản đề xuất thời gian biểu (SRS §6.4) |
| 20 | `BlockType` | `planning` | `ScheduleBlock.blockType` | `STUDY`, `BUFFER`, `REVISION`, `RECOVERY` | 4 phân loại khối thời gian biểu (SRS §12.2 #20) |
| 21 | `BlockStatus` | `planning` | `ScheduleBlock.status` | `PLANNED`, `COMPLETED`, `MISSED`, `RESCHEDULED`, `CANCELLED` | Trạng thái khối lịch học (`chk_schedule_blocks_status`) |
| 22 | `SourceType` | `planning` | `KnowledgeSource.sourceType` | `PDF`, `DOCX`, `TXT`, `URL` | Định dạng học liệu RAG (SRS §12.2 #14) |
| 23 | `IngestionStatus` | `planning` | `KnowledgeSource.ingestionStatus` | `PENDING`, `PROCESSING`, `INDEXED`, `FAILED`, `QUARANTINED` | Trạng thái nạp học liệu RAG (`chk_knowledge_sources_status`) |
| 24 | `TaskOrigin` | `execution` | `Task.origin` | `AI`, `MANUAL` | **Enum mới**: Phân định nguồn gốc task (AI: 30–120', Manual: 15–240') |
| 25 | `TaskStatus` | `execution` | `Task.status` | `TODO`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED` | Vòng đời nhiệm vụ học tập (SRS §6.3) |
| 26 | `SessionTaskStatus` | `execution` | `SessionTask.statusAfterSession` | `TODO`, `IN_PROGRESS`, `COMPLETED` | Trạng thái bài học ngay sau khi kết thúc phiên học (`chk_session_tasks_status_after`) |
| 27 | `SessionMode` | `execution` | `StudySession.mode` | `STANDARD`, `MVS` | Chế độ học tập (SRS §12.3 #25) |
| 28 | `TimerMode` | `execution` | `StudySession.timerMode` | `POMODORO`, `STOPWATCH` | **Chuẩn hóa**: Đã xóa `FLOWMODORO` tự bịa (`FR-SESSION-001`) |
| 29 | `SessionStatus` | `execution` | `StudySession.status` | `IN_PROGRESS`, `COMPLETED`, `PARTIAL_COMPLETED`, `CANCELLED` | Vòng đời phiên học thực thi (SRS §6.3) |
| 30 | `TimeSufficiency` | `execution` | `DailyCheckin.timeSufficiency` | `TOO_SHORT`, `JUST_RIGHT`, `TOO_LONG` | **Chuẩn hóa**: Sửa từ Integer sang Enum 3 giá trị (`FR-SESSION-002`) |
| 31 | `NoteType` | `execution` | `StudyNote.noteType` | `SCRATCHPAD`, `TAKEAWAY`, `GENERAL` | Phân loại ghi chép học tập |
| 32 | `TakeawayVerification`| `execution` | `KeyTakeaway.verificationStatus` | `PENDING_PROVE`, `VERIFIED`, `FLAGGED_SHALLOW`, `NEEDS_REVIEW` | Kết quả thẩm định đúc kết của AI (`FR-REPORT-003`) |
| 33 | `AlignmentFlag` | `execution` | `KeyTakeaway.alignmentFlag` | `UNCHECKED`, `ALIGNED`, `SUPERFICIAL`, `OFF_TOPIC`, `CONTRADICTORY` | **Chuẩn hóa**: Sửa từ Boolean sang Enum 5 giá trị Anti-Gaming |
| 34 | `ProofVerdict` | `evaluation` | `MilestoneProof.verdict` | `PENDING`, `PROVEN`, `NEEDS_REVIEW`, `FLAGGED_SHALLOW` | Phán quyết kiểm chứng năng lực (SRS §12.4 #31) |
| 35 | `MistakeCause` | `evaluation` | `MistakeTaxonomy.cause` | `MISSING_FOUNDATION`, `CONCEPT_MISCONCEPTION`, `PROCESS_ERROR`, `LACK_OF_PRACTICE` | 4 nhóm Trí tuệ Sai lầm sư phạm (SRS §1.5) |
| 36 | `ReviewCycle` | `evaluation` | `AIReview.cycle` | `WEEKLY`, `MILESTONE` | Chu kỳ đánh giá định kỳ của AI (SRS §12.4 #29) |
| 37 | `PauseStatus` | `evaluation` | `PauseRecord.status` | `ACTIVE`, `COMPLETED` | Trạng thái tạm dừng lộ trình học tập (SRS §12.4 #28) |
| 38 | `ChangeTriggerType`| `evaluation` | `ScheduleChangeLog.trigger` | `DOMINO_SHIFT`, `MANUAL_PROACTIVE_EDIT`, `OVERDUE_RESCHEDULE`, `AI_REPLAN`, `POST_FAILURE_RESET`, `COMMITMENT_CONTRACT`, `BACKLOG_QUEUE_MOVE` | Các nguyên nhân kích hoạt biến động lịch (`FR-ADAPT-001`) |
| 39 | `DisruptionCategory`| `evaluation` | `ScheduleChangeLog.disruptionCategory` | `UNSPECIFIED`, `LEGITIMATE_HEALTH`, `LEGITIMATE_WORK_SCHOOL`, `LEGITIMATE_EXTERNAL_CALENDAR`, `OVERLOAD_TASK_TOO_LARGE`, `PROCRASTINATION_LOW_ENERGY` | Phân loại lý do gián đoạn lịch học (`FR-ADAPT-001`) |

---

## H. Kết quả Kiểm tra, Bảng Đối chiếu Chất lượng & Đóng Findings

### H.1 Đối chiếu Định lượng Khớp 100% với File PlantUML Duy nhất

| File Mã nguồn PlantUML | Số Lớp Miền (Domain Classifiers) | Association Class | Association Nội bộ | Quan hệ Chéo Context (`--> «references»` & `..> «*Snapshot»`) | Kế thừa (`<\|--`) | Dependency (`..>`) | Thuộc tính có Kiểu tường minh | Trạng thái Kiểm chứng |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| [`class-diagram.puml`](class-diagrams/class-diagram.puml) | **33** (`15 AR + 13 E + 4 VO + 1 AC`) | **1** (`SessionTask`) | **21** (15 Assoc + 6 Comp) | **14** (12 `«references»` + 2 Snapshot) | **1** (`KeyTakeaway`) | **1** (`DEP-01 Apply`) | **118 / 118 (100%)** | **Khớp 100% Tuyệt đối** |

---

### H.2 Bảng Đối chiếu Đóng Toàn bộ Findings (Review 1 & Review 2)

| Mã Finding Review 1 | Mã Finding Review 2 | Vấn đề được Nêu | Giải pháp Đã Thực hiện trong v11.0 | Trạng thái |
|:---:|:---:|---|---|:---:|
| **D-H01** | **F-01** | 14 quan hệ `«by id»` kèm multiplicity vi phạm UML 2.5.1 | Chuyển thành **Unidirectional Association (`-->`)** kèm stereotype **`«references»`**, bảo vệ ranh giới Modular Monolith. | **RESOLVED** |
| **D-H02** | **F-02** | `ScheduleBlock` bị ràng buộc `1` ở cả Proposal lẫn OfficialSchedule | `OfficialSchedule 1 *-- 0..* ScheduleBlock`; Proposal liên kết phụ thuộc `DEP-01 «materializes on Apply»`. | **RESOLVED** |
| **D-H03** | **F-07** | `alignmentFlag : Boolean` làm mất ngữ nghĩa Anti-Gaming | Chuyển thành Enum **`AlignmentFlag` đủ 5 giá trị** (`UNCHECKED`, `ALIGNED`, `SUPERFICIAL`, `OFF_TOPIC`, `CONTRADICTORY`). | **RESOLVED** |
| — | **F-03** | Thiếu thực thể và thuộc tính cho Availability Mode A (0.5..14h) | Bổ sung lớp **`DailyHoursQuota` (dayOfWeek, hours)** hợp thành từ `AvailabilityProfile`. | **RESOLVED** |
| — | **F-04** | `Task.scheduledDate` xung đột với khối lịch và nguyên tắc Roadmap $\neq$ Schedule | Chuyển thành thuộc tính dẫn xuất **`Task./scheduledDate : Date [0..1] = max(ScheduleBlocks.blockDate)`**. | **RESOLVED** |
| **D-M01** | **F-06** | `PasswordResetToken` gắn sai stereotype `<<ValueObject>>` | Đổi stereotype sang **`<<Entity>>`**, xóa `tokenHash`, bỏ ghi chú hạ tầng Redis. | **RESOLVED** |
| **D-M02** | **F-06** | Trùng lặp `mistakeTaxonomyJson` trên `MilestoneProof` | Xóa bỏ trường `mistakeTaxonomyJson`, giữ nguyên Composition với Value Object `MistakeTaxonomy`. | **RESOLVED** |
| **D-M03** | **F-08** | Class rỗng thiếu thuộc tính nội dung (`claim`, `content`, phản tư) | Bổ sung đầy đủ: `claim` vào `LearnerMemoryItem`; `content` vào `KnowledgeChunk` & `StudyNote`; các trường phản tư vào `AIReview`. | **RESOLVED** |
| **D-M04** | **F-08** | Thiếu kiểm soát Ngân sách dời lịch tuần (3 lượt/tuần) | Thêm `weeklyRescheduleBudget`, `weeklyRescheduleUsed` vào `Roadmap`; thêm `countsTowardBudget` vào `ScheduleChangeLog`. | **RESOLVED** |
| **D-M05** | **F-08** | `ScheduleBlock` thiếu `isProtected` và thời điểm bắt đầu | Thêm `blockDate`, `startTime [0..1]`, `scheduledDurationMinutes`, `isProtected` vào `ScheduleBlock`. | **RESOLVED** |
| **D-M06** | — | `AvailabilitySlot` thiếu `energyLevel` | Thêm `energyLevel : EnergyLevel` và `endDayOffset : Integer` vào `AvailabilitySlot`. | **RESOLVED** |
| **D-M07** | — | `AIQuota` thiếu invariant tính giữ chỗ đang chờ | Cập nhật Invariant: `usedCalls + activeReservations <= monthlyLimit`. | **RESOLVED** |
| **D-M08** | **F-07** | `TimerMode` chứa enum tự bịa `FLOWMODORO` | Xóa bỏ hoàn toàn `FLOWMODORO`, chỉ giữ `POMODORO` và `STOPWATCH`. | **RESOLVED** |
| **D-M09** | **F-13** | Trích dẫn không tồn tại: `BUSR-14`, `FR-STUDY-004`, `DEC-04`, `SRS §6.5` | Xóa bỏ toàn bộ các mã không tồn tại, cập nhật trích dẫn chuẩn SRS v1.4. | **RESOLVED** |
| **D-M10** | — | 15 `<<AggregateRoot>>` nhưng thiếu aggregate boundary | Bổ sung làm rõ ranh giới Aggregate tại Mục D.1 và chú giải chi tiết. | **RESOLVED** |
| — | **F-06** | `WorkflowRun` là hạ tầng điều phối, không thuộc domain model | **Xóa bỏ `WorkflowRun`** khỏi sơ đồ lớp khái niệm, chuyển sang tài liệu kiến trúc runtime. | **RESOLVED** |
| — | **F-09** | Thiếu 3 quan hệ: Task trích dẫn Chunk, Proof dùng Takeaway, Note gắn Task | Bổ sung đầy đủ 3 quan hệ: `Task ..> KnowledgeChunk («citationSnapshot»)`, `MilestoneProof ..> KeyTakeaway («evidenceSnapshot»)`, `StudyNote --> Task («references»)`. | **RESOLVED** |
| **D-L02** | — | Tiêu đề Mục G.2 ghi nhầm số lượng enum | Đính chính tiêu đề Mục G.2 thành số lượng chính xác 39 kiểu liệt kê (gồm `SessionTaskStatus`). | **RESOLVED** |

---

### H.3 Đánh giá Tuân thủ Tiêu chuẩn Thiết kế (Review Checklist Baseline v1.4 Post-CCB Ready)

- ✅ **Operations có kiểm soát**: Chỉ hiển thị operations thay đổi trạng thái hoặc bảo vệ invariant; không chứa getter/setter, CRUD, kiểu dữ liệu framework, trường PK/FK/UUID hay I/O infrastructure.
- ✅ **Tổ chức UML Package cho Bounded Context**: Thể hiện trực quan 4 Bounded Contexts (`account`, `planning`, `execution`, `evaluation`) trong cùng 1 sơ đồ duy nhất.
- ✅ **Hiển thị Tường minh DDD Stereotypes**: 100% các class hiển thị rõ `<<AggregateRoot>>` (15), `<<Entity>>` (13), `<<ValueObject>>` (4), hoặc `<<AssociationClass>>` (1).
- ✅ **100% Thuộc tính Định kiểu Tường minh**: Toàn bộ 118 thuộc tính trong 33 classifiers đều có kiểu dữ liệu rõ ràng (`name : Type`).
- ✅ **Biểu diễn Association Class `SessionTask` Chuẩn xác**: Nối nét đứt `(StudySession, Task) .. SessionTask` lưu trữ đầy đủ 4 thuộc tính kết quả học tập trong phiên (`allocatedMinutes`, `actualMinutes`, `statusAfterSession`, `notes`).
- ✅ **Quan hệ Chéo Context Chuẩn UML & DDD**: Toàn bộ 14 quan hệ chéo miền gồm 12 Unidirectional Associations (`--> «references»`) và 2 Snapshot Dependencies (`..> «citationSnapshot»`, `..> «evidenceSnapshot»`), bảo vệ triệt để tính độc lập của Bounded Context trong Modular Monolith (`ADR-001`).
- ✅ **Bảo toàn Single Source of Truth**: Sơ đồ duy nhất [`docs/uml/class-diagrams/class-diagram.puml`](class-diagrams/class-diagram.puml) khớp số học 100% với tài liệu này và hình ảnh kết xuất [`docs/uml/images/FocusFlow_Class_Diagram.png`](images/FocusFlow_Class_Diagram.png).

---

## I. Behavioral Design Class Diagrams & Operation Catalog

### I.1 Phạm vi và quy ước

Các sơ đồ dưới đây là **Profile C — Software Design Class Diagram**, bổ sung operations cho đúng 33 classifiers đang có trong Domain Overview. Mỗi operation biểu diễn trách nhiệm thay đổi trạng thái hoặc bảo vệ invariant của chính domain concept; không đưa getter/setter, CRUD, ORM, HTTP, Taskiq, LLM invocation, email/OAuth delivery, hoặc transaction/UoW vào class.

Các chữ ký là **PROPOSED** ở mức thiết kế (tên/parameter có thể tinh chỉnh khi thiết kế API), còn trách nhiệm nghiệp vụ và chuyển trạng thái được truy vết tới SRS/UC. Các use case điều phối nhiều aggregate — ví dụ AI generation, deterministic scheduling, Apply proposal, Domino Shift và Prove evaluation — vẫn thuộc application/domain service, không bị gán sai vào một entity.

| Bounded Context | PlantUML behavioral design view | Classifiers phủ | Căn cứ chính |
|---|---|---:|---|
| `account` | [`behavioral-design-account.puml`](class-diagrams/behavioral-design-account.puml) | 13/13 | `UC-ACC-01..11`, `UC-EXEC-07..09`, `UC-ADAPT-09`, `FR-QUOTA-001`, `FR-AVAIL-001/002` |
| `planning` | [`behavioral-design-planning.puml`](class-diagrams/behavioral-design-planning.puml) | 9/9 | `UC-PLAN-01..10`, `UC-ADAPT-03..07`, `FR-PLAN-*`, `FR-ADAPT-001` |
| `execution` | [`behavioral-design-execution.puml`](class-diagrams/behavioral-design-execution.puml) | 6/6 | `UC-EXEC-02..06`, `UC-ADAPT-02`, `FR-TASK-*`, `FR-SESSION-*` |
| `evaluation` | [`behavioral-design-evaluation.puml`](class-diagrams/behavioral-design-evaluation.puml) | 5/5 | `UC-ADAPT-02..07`, `FR-REPORT-*`, `FR-PAUSE-001/002`, `FR-ADAPT-001` |

### I.2 Ranh giới trách nhiệm quan trọng

| Không gán vào entity | Lý do | Nơi thuộc về |
|---|---|---|
| Sinh đề xuất bằng AI, gọi provider và vòng đời quota | Phối hợp external adapter, quota và nhiều aggregate. | Application use case + Shared AI Harness Runtime |
| Kiểm định/optimization lịch và Domino Shift | Phối hợp `Roadmap`, `OfficialSchedule`, `ScheduleBlock`, `Task`, availability và hard constraints. | Deterministic scheduling application/domain service |
| Apply `ScheduleProposal` thành `OfficialSchedule` | Thay đổi nhiều aggregate; chỉ Learner action mới được phép Apply. | Application use case có transaction boundary |
| OAuth exchange, WebCal/ICS rendering, gửi email, scheduled jobs | I/O hoặc infrastructure. | Presentation/infrastructure/task layer |
