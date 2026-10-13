# FocusFlow — Thiết kế Sơ đồ Tuần tự Chi tiết (Sequence Diagrams Document)
## Phiên bản: v3.0 — Chuẩn UML 2.5.1 & Thực sự hóa Ca sử dụng (Use-Case Realization)
**Dự án:** FocusFlow — Hệ thống hỗ trợ lập kế hoạch và thực thi lộ trình tự học thích ứng tích hợp AI  
**Tiêu chuẩn kỹ thuật:** ISO/IEC 19505-2 (UML 2.5.1 Superstructure), RFC 5545 (iCalendar), Kiến trúc Lục giác (Hexagonal Architecture / Ports & Adapters)  
**Căn cứ đánh giá học thuật:** Khung Rubric Đồ án Tốt nghiệp CNTT — Tiêu chí TC1 & TC2.1 & TC2.3 (Mức 5)  
**Tài liệu liên kết:**
- Sơ đồ Ca sử dụng: [`docs/uml/use-cases/use-case-diagram.puml`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/use-cases/use-case-diagram.puml)
- Đặc tả Ca sử dụng Chi tiết: [`docs/uml/use-case-specifications.md`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/use-case-specifications.md)
- Biểu đồ Lớp (Domain Model & DCD): [`docs/uml/class-diagrams.md`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/class-diagrams.md)
- Yêu cầu phần mềm (SRS): [`docs/srs/srs-v1.0.md`](file:///Users/vuthang/Documents/FocusFlow/docs/srs/srs-v1.0.md)
- Thiết kế Kiến trúc: [`docs/architecture/system-architecture.md`](file:///Users/vuthang/Documents/FocusFlow/docs/architecture/system-architecture.md)
- Thiết kế Cơ sở Dữ liệu: [`docs/database/database-schema-design.md`](file:///Users/vuthang/Documents/FocusFlow/docs/database/database-schema-design.md)
- Thư mục nguồn PlantUML: [`docs/uml/sequence/`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/sequence) (gồm 9 sơ đồ độc lập)

---

## MỤC LỤC
1. [Nguyên tắc Thiết kế & Sơ đồ Tuần tự Hệ thống Tổng quan (SSD)](#1-nguyên-tắc-thiết-kế--sơ-đồ-tuần-tự-hệ-thống-mức-tổng-quan-ssd)
2. [Sequence Diagram 1: Đăng nhập Hệ thống (UC-AUTH-02)](#2-sequence-diagram-1-đăng-nhập-hệ-thống-uc-auth-02)
3. [Sequence Diagram 2: Khởi tạo Mục tiêu & Đăng ký Lộ trình (UC-PLAN-01)](#3-sequence-diagram-2-khởi-tạo-mục-tiêu--đăng-ký-lộ-trình-uc-plan-01)
4. [Sequence Diagram 3: Sinh Cột mốc & Phân rã Nhiệm vụ AI (UC-PLAN-02)](#4-sequence-diagram-3-sinh-cột-mốc--phân-rã-nhiệm-vụ-ai-uc-plan-02)
5. [Sequence Diagram 4: Áp dụng Lịch học Chính thức & Kiểm tra Trần Giờ rảnh (UC-PLAN-03)](#5-sequence-diagram-4-áp-dụng-lịch-học-chính-thức--kiểm-tra-trần-giờ-rảnh-uc-plan-03)
6. [Sequence Diagram 5: Thực thi Phiên học Pomodoro (UC-SESS-01)](#6-sequence-diagram-5-thực-thi-phiên-học-pomodoro-uc-sess-01)
7. [Sequence Diagram 6: Thiết lập Tạm dừng Lộ trình & Domino Shift (UC-PAUSE-01)](#7-sequence-diagram-6-thiết-lập-tạm-dừng-lộ-trình--domino-shift-uc-pause-01)
8. [Sequence Diagram 7: Đồng bộ Lịch 1 Chiều WebCal RFC 5545 (UC-CAL-01)](#8-sequence-diagram-7-đồng-bộ-lịch-1-chiều-webcal-rfc-5545-uc-cal-01)
9. [Sequence Diagram 8: Tự động Quét & Chốt Phiên Gián đoạn Celery Beat (UC-SESS-02)](#9-sequence-diagram-8-tự-động-quét--chốt-phiên-gián-đoạn-celery-beat-uc-sess-02)
10. [Ma trận Kiểm tra Tính Nhất quán (Consistency & Traceability Matrix)](#10-ma-trận-kiểm-tra-tính-nhất-quán-consistency--traceability-matrix)

---

## 1. Nguyên tắc Thiết kế & Sơ đồ Tuần tự Hệ thống Mức Tổng quan (SSD)

### 1.1 Nguyên tắc Thiết kế Use-Case Realization & Phân lớp Kiến trúc
Nhằm khắc phục triệt để lỗi thiết kế nhồi nhét nhiều kịch bản vào một sơ đồ gây rườm rà, bộ Sequence Diagram của FocusFlow tuân thủ nghiêm ngặt chuẩn mực công nghệ phần mềm:
1. **Phạm vi kịch bản đơn lẻ (Single Scenario Focus):** Mỗi sơ đồ tuần tự mức thiết kế (Design Sequence Diagram - DSD) mô hình hóa trọn vẹn sự hợp tác giữa các đối tượng để thực sự hóa **1 kịch bản cụ thể** (Use-Case Realization) của một Ca sử dụng.
2. **Tuân thủ phân lớp Kiến trúc Lục giác (Hexagonal Architecture):**
   - **Actor (Tác nhân):** Người dùng (`Learner`), tác nhân ngoại vi (`External Calendar App`) hoặc bộ lập lịch nền (`Celery Beat`).
   - **Boundary / Presentation Layer:** Giao diện `Next.js Web Client`, các bộ lọc `Middleware`, và các bộ điều hướng `FastAPI Router`.
   - **Control / Application Layer:** Các `Use Case Interactors` điều phối luồng nghiệp vụ.
   - **Domain Layer:** Các thực thể nghiệp vụ (`Goal`, `Roadmap`, `StudySession`, `Task`) và các `Domain Services` thuần Python (`DominoShiftCalculator`, `AvailabilityValidator`, `PromptSanitizer`).
   - **Infrastructure Adapters:** Các Adapter giao tiếp cơ sở dữ liệu (`SqlRoadmapRepo`, `SqlSessionRepo`, v.v.), dịch vụ token bảo mật, và bộ tích hợp AI (`GeminiLLMAdapter`).
   - **Storage / External Systems:** `PostgreSQL 16`, `Redis`, `Google Gemini API`.
3. **Quy chuẩn thông điệp (Messages & Activations):**
   - Lời gọi phương thức đồng bộ thể hiện bằng mũi tên nét liền đầu đặc (`->`).
   - Phản hồi dữ liệu / DTO thể hiện bằng mũi tên nét đứt đầu hở (`-->`).
   - Mọi tương tác dữ liệu phải thông qua phương thức hướng đối tượng của Repository, tuyệt đối không dùng câu lệnh SQL thô trên sơ đồ tuần tự.
   - Thanh kích hoạt (`Activation Bar`) thể hiện chính xác thời điểm thực thi của từng đối tượng.

---

### 1.2 Sơ đồ Tuần tự Hệ thống Tổng quan (System Sequence Diagram - SSD)
Mô hình hóa Hộp đen (**Black-box SSD**) theo chu trình Tự học có điều tiết (**Self-Regulated Learning - SRL**):
* **File nguồn PlantUML:** [`docs/uml/sequence/seq-00-system-sequence-diagram.puml`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/sequence/seq-00-system-sequence-diagram.puml)

```mermaid
sequenceDiagram
    autonumber
    actor User as Learner (Người học)
    participant System as :FocusFlow System (Hộp đen)

    Note over User,System: GIAI ĐOẠN 1: THIẾT LẬP MỤC TIÊU & LẬP KẾ HOẠCH (FORETHOUGHT PHASE)
    User->>System: createGoal(goal_title, target_date)
    alt Đủ hạn ngạch Quota AI
        System-->>User: milestonesList (3-7 Cột mốc cấp 1)
        User->>System: approveMilestonesAndSetAvailability(milestones, availability_config)
        System-->>User: scheduleProposal (Kế hoạch nhiệm vụ chi tiết cấp 2)
        User->>System: applyOfficialSchedule(proposal_id)
        alt Quỹ giờ rảnh hợp lệ (Thỏa mãn trần giờ)
            System-->>User: scheduleActivatedAck (Lịch chính thức được kích hoạt)
        else Vi phạm trần giờ rảnh (Hard Ceiling Violated)
            System-->>User: scheduleRejectedError (Cảnh báo quá tải, yêu cầu chỉnh sửa)
        end
    else Hết hạn ngạch Quota AI
        System-->>User: quotaExceededError (Cảnh báo hết hạn ngạch AI, gợi ý Mock Sandbox)
    end

    Note over User,System: GIAI ĐOẠN 2: THỰC THI PHIÊN HỌC & GIÁM SÁT (PERFORMANCE PHASE)
    User->>System: startStudySession(task_id)
    System-->>User: sessionStartedAck (Mở Study Workspace)

    opt Nhịp tim định kỳ trong lúc học (Mỗi 60s)
        User->>System: sendHeartbeat(session_id)
        System-->>User: heartbeatAck
    end

    alt Hoàn thành phiên bình thường
        User->>System: finishStudySession(session_id, completed_tasks, takeaways)
        System-->>User: sessionSummaryDTO (Cập nhật tiến độ & Chuỗi ngày học)
    else Mất kết nối / Bỏ ngang > 5 phút (OS-07)
        Note over System: Hệ thống tự động quét và chốt phiên gián đoạn (OS-01)
        User->>System: reconnectAndQuerySession(session_id)
        System-->>User: sessionFinalizedAbandonedAck (Chốt phiên gián đoạn, bảo toàn thời gian đã ghi nhận)
    end

    Note over User,System: GIAI ĐOẠN 3: TỰ SUY NGẪM & THÍCH ỨNG BIẾN CỐ (SELF-REFLECTION & ADAPTATION)
    opt Người học có biến cố cần hoãn hoặc dời lịch
        User->>System: pauseRoadmap(roadmap_id, start_date, resume_date, reason)
        System-->>User: dominoShiftResult (Lịch học tịnh tiến tất định an toàn)
    end
```

---

## 2. Sequence Diagram 1: Đăng nhập Hệ thống (UC-AUTH-02)
* **Ca sử dụng:** `UC-AUTH-02: Đăng nhập hệ thống`.
* **Yêu cầu chức năng:** `FR-AUTH-002`, `NFR-SEC-001`.
* **Mô tả kịch bản:** Người học gửi thông tin đăng nhập (email, password). Hệ thống xác thực danh tính qua băm mật khẩu bảo mật (Argon2/Bcrypt), kiểm tra trạng thái khóa tài khoản (`is_locked()`), sinh cặp JSON Web Token (Access Token & Refresh Token) và trả về HttpOnly Cookie.
* **File nguồn PlantUML:** [`docs/uml/sequence/seq-01-user-login.puml`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/sequence/seq-01-user-login.puml)

```mermaid
sequenceDiagram
    autonumber
    actor User as Learner
    participant UI as Next.js Web Client
    participant Router as AuthRouter (FastAPI)
    participant AuthUC as AuthenticateUserUC (Use Case)
    participant Hasher as PasswordHasher (Domain)
    participant UserEntity as User (Domain Entity)
    participant TokenService as JwtTokenProvider (TokenPort)
    participant Repo as SqlUserRepo (UserRepoPort)
    participant DB as PostgreSQL 16

    User->>UI: Nhập Email, Mật khẩu & Bấm [Đăng nhập]
    UI->>Router: POST /api/v1/auth/login (email, password)
    Router->>AuthUC: execute(cmd: LoginCommand)
    AuthUC->>Repo: find_by_email(email)
    Repo->>DB: query_user_by_email(email)
    DB-->>Repo: user_record

    alt Không tìm thấy User (user_record == null)
        Repo-->>AuthUC: null
        AuthUC-->>Router: throw InvalidCredentialsError
        Router-->>UI: 401 Unauthorized {"error": "INVALID_CREDENTIALS"}
        UI-->>User: Hiển thị thông báo "Email hoặc mật khẩu không chính xác"
    else Tìm thấy User
        Repo-->>AuthUC: userEntity
        AuthUC->>Hasher: verify_password(raw_password, userEntity.password_hash)
        Hasher-->>AuthUC: is_password_valid: bool

        alt Mật khẩu sai (is_password_valid == false)
            AuthUC-->>Router: throw InvalidCredentialsError
            Router-->>UI: 401 Unauthorized {"error": "INVALID_CREDENTIALS"}
            UI-->>User: Hiển thị thông báo "Email hoặc mật khẩu không chính xác"
        else Mật khẩu chính xác (is_password_valid == true)
            AuthUC->>UserEntity: is_locked()
            UserEntity-->>AuthUC: is_locked: bool

            alt Tài khoản bị khóa (is_locked == true)
                AuthUC-->>Router: throw AccountLockedError
                Router-->>UI: 403 Forbidden {"error": "ACCOUNT_LOCKED"}
                UI-->>User: Cảnh báo "Tài khoản của bạn đã bị tạm khóa"
            else Tài khoản hoạt động (ACTIVE)
                AuthUC->>TokenService: create_token_pair(userEntity.id, userEntity.role)
                TokenService-->>AuthUC: TokenPair(access_token, refresh_token)
                AuthUC-->>Router: AuthSuccessDTO(user_info, token_pair)
                Router-->>UI: 200 OK + Set-Cookie (HttpOnly JWT)
                UI-->>User: Điều hướng vào Màn hình Chính (Dashboard)
            end
        end
    end
```

---

## 3. Sequence Diagram 2: Khởi tạo Mục tiêu & Đăng ký Lộ trình (UC-PLAN-01)
* **Ca sử dụng:** `UC-PLAN-01: Khởi tạo mục tiêu & Làm rõ ngữ cảnh`.
* **Yêu cầu chức năng:** `FR-PLAN-001`.
* **Mô tả kịch bản:** Người học khởi tạo mục tiêu học tập ban đầu. Thực thể `Goal` và `Roadmap` được khởi tạo độc lập, kiểm tra quy tắc nghiệp vụ ngày hoàn thành (`targetDate > currentDate`), lưu vào cơ sở dữ liệu ở trạng thái `PLANNING` để chuẩn bị cho giai đoạn phân rã kế hoạch.
* **File nguồn PlantUML:** [`docs/uml/sequence/seq-02-create-goal-roadmap.puml`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/sequence/seq-02-create-goal-roadmap.puml)

```mermaid
sequenceDiagram
    autonumber
    actor User as Learner
    participant UI as Next.js Web Client
    participant Router as RoadmapRouter (FastAPI)
    participant CreateUC as CreateGoalAndRoadmapUC (Use Case)
    participant GoalEntity as Goal (Domain Entity)
    participant RoadmapEntity as Roadmap (Domain Entity)
    participant Repo as SqlRoadmapRepo (RepoPort)
    participant DB as PostgreSQL 16

    User->>UI: Nhập Mục tiêu, Ngày kết thúc & Bấm [Bắt đầu Lộ trình]
    UI->>Router: POST /api/v1/roadmaps/goals (title, target_date, context)
    Router->>CreateUC: execute(cmd: CreateGoalCommand)
    CreateUC->>GoalEntity: create(userId, title, targetDate, context)

    alt targetDate <= currentDate (Thời hạn không hợp lệ)
        GoalEntity-->>CreateUC: throw InvalidTargetDateException
        CreateUC-->>Router: throw ValidationException
        Router-->>UI: 422 Unprocessable Entity {"error": "INVALID_TARGET_DATE"}
        UI-->>User: Báo lỗi "Thời hạn hoàn thành mục tiêu phải lớn hơn ngày hiện tại"
    else targetDate hợp lệ
        GoalEntity-->>CreateUC: goalEntity (status=ACTIVE)
        CreateUC->>RoadmapEntity: create(goalId, userId, title, targetDate)
        RoadmapEntity-->>CreateUC: roadmapEntity (status=INITIALIZED)
        CreateUC->>Repo: save_goal_and_roadmap(goalEntity, roadmapEntity)
        Repo->>DB: insert_goal_and_roadmap_records(data)
        DB-->>Repo: (goal_id, roadmap_id)
        Repo-->>CreateUC: PersistedRoadmapDTO
        CreateUC-->>Router: RoadmapCreatedDTO(goal_id, roadmap_id, status="INITIALIZED")
        Router-->>UI: 201 Created {"roadmap_id": "road_123", "goal_id": "goal_123"}
        UI-->>User: Mở giao diện thiết lập kế hoạch (Chọn AI hoặc Lập thủ công)
    end
```

---

## 4. Sequence Diagram 3: Sinh Cột mốc & Phân rã Nhiệm vụ AI (UC-PLAN-02)
* **Ca sử dụng:** `UC-PLAN-02: Phê duyệt các cột mốc học tập & Sinh đề xuất kế hoạch`.
* **Yêu cầu chức năng:** `FR-PLAN-002`, `FR-QUOTA-001`, `OS-02` (Two-Phase Quota Lifecycle), `ADR-005` (SSE Streaming Progress).
* **Mô tả kịch bản:** Thực hiện phân rã kế hoạch học tập qua Google Gemini API với cơ chế phản hồi dòng SSE (`text/event-stream`). Quota được bảo lưu nguyên tử qua Redis Lua script (`reserve_quota`), prompt được khử khuẩn chống Prompt Injection (`PromptSanitizer`), gọi LLM kèm giới hạn thời gian Timeout 55s. Dữ liệu đề xuất được stream về Client theo từng chunk tiến trình. Khi hoàn tất, lưu bản nháp đề xuất (`status='DRAFT'`) và chính thức trừ hạn ngạch (`commit_quota`). Nếu lỗi/timeout, hạn ngạch được hoàn trả an toàn (`release_quota`).
* **File nguồn PlantUML:** [`docs/uml/sequence/seq-03-generate-milestones-tasks-ai.puml`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/sequence/seq-03-generate-milestones-tasks-ai.puml)

```mermaid
sequenceDiagram
    autonumber
    actor User as Learner
    participant UI as Next.js Web Client
    participant Router as RoadmapRouter (FastAPI)
    participant GenUC as GenerateProposalUC (Use Case)
    participant Sanitizer as PromptSanitizer (Domain)
    participant Quota as RedisQuotaAdapter (AIQuotaPort)
    participant Redis as Redis 7.2 (Cache & Quota)
    participant LLMAdapter as GeminiLLMAdapter (LLMPort)
    participant LLM as Google Gemini API
    participant Repo as SqlProposalRepo (ProposalRepoPort)
    participant DB as PostgreSQL 16

    User->>UI: Cấu hình Giờ rảnh & Bấm [Sinh Đề xuất Lịch học bằng AI]
    UI->>Router: POST /api/v1/roadmaps/{id}/proposals/generate (Stream SSE)
    Router->>GenUC: execute(cmd: GenerateProposalCommand)
    GenUC->>Quota: reserve_quota(userId)
    Quota->>Redis: EVALSHA token_bucket_reserve.lua (userId, cost=1)
    Redis-->>Quota: quota_reserved: bool

    alt Hết hạn ngạch Quota AI (quota_reserved == false)
        Quota-->>GenUC: throw QuotaExceededError
        GenUC-->>Router: throw QuotaExceededError
        Router-->>UI: 429 Too Many Requests {"error": "AI_QUOTA_EXCEEDED"}
        UI-->>User: Cảnh báo hết hạn ngạch AI hôm nay, gợi ý chuyển sang Lập kế hoạch thủ công
    else Quota hợp lệ
        Quota-->>GenUC: reservation_token
        GenUC->>Sanitizer: sanitize_prompt(rawContext)
        Sanitizer-->>GenUC: cleanPrompt (PII-stripped)
        GenUC->>LLMAdapter: generate_schedule_proposal_stream(cleanPrompt, availability) [Timeout 55s]
        LLMAdapter->>LLM: generate_content_stream(cleanPrompt)

        alt Lỗi Timeout 55s / Service Error
            LLM-->>LLMAdapter: TimeoutError (sau 55s)
            LLMAdapter-->>GenUC: throw LLMTimeoutException
            GenUC->>Quota: release_quota(userId, reservation_token)
            Quota->>Redis: EVALSHA token_bucket_release.lua (userId, token)
            Redis-->>Quota: OK
            Quota-->>GenUC: OK
            GenUC-->>Router: throw AIPlanGenerationTimeoutException
            Router-->>UI: 504 Gateway Timeout {"error": "AI_TIMEOUT"}
            UI-->>User: Thông báo AI quá tải, cho phép thử lại hoặc lập thủ công
        else Sinh đề xuất thành công (Streaming SSE Chunks)
            loop Đọc từng SSE chunk từ Gemini
                LLM-->>LLMAdapter: chunk_data
                LLMAdapter-->>GenUC: parsedChunk
                GenUC-->>Router: yield sse_event("progress", percent)
                Router-->>UI: EventSource message (Cập nhật thanh tiến độ % realtime)
            end
            LLM-->>LLMAdapter: completed_stream
            LLMAdapter-->>GenUC: completeRawProposalData
            GenUC->>GenUC: validate_schema(completeRawProposalData) [tasks 30-120m]
            GenUC->>Repo: create_draft_proposal(roadmapId, userId, rawProposalData)
            Repo->>DB: insert_schedule_proposal(record, status='DRAFT')
            DB-->>Repo: proposal_id
            Repo-->>GenUC: proposalEntity (status="DRAFT")
            GenUC->>Quota: commit_quota(userId, reservation_token)
            Quota->>Redis: EVALSHA token_bucket_commit.lua (userId, token)
            Redis-->>Quota: OK
            Quota-->>GenUC: OK
            GenUC-->>Router: yield sse_event("completed", ProposalCreatedDTO)
            Router-->>UI: SSE Complete Event {"proposal_id": "prop_456"}
            UI-->>User: Hiển thị Bản xem trước Đề xuất (Preview Proposal, chờ người học duyệt)
        end
    end
```

---

### 5. Sequence Diagram 4: Áp dụng Lịch học Chính thức & Kiểm tra Trần Giờ rảnh (UC-PLAN-03)
* **Ca sử dụng:** `UC-PLAN-03: Tạo đề xuất & Áp dụng lịch trình`.
* **Yêu cầu chức năng:** `FR-PLAN-003`, `FR-PLAN-004`.
* **Mô tả kịch bản:** Trước khi ghi nhận lịch học chính thức, Domain Service `AvailabilityValidator` kiểm tra nghiêm ngặt trần giờ rảnh trong ngày (Hard Ceiling). Nếu vi phạm, từ chối giao dịch. Nếu hợp lệ, hệ thống thực thi theo mô hình Rich Domain Model (`Proposal.apply()`, `Roadmap.activate()`) và giao dịch nguyên tử (ACID Transaction qua Unit of Work): chuyển trạng thái các Task cũ còn dang dở sang `CANCELLED`, nạp danh sách task mới từ proposal với trạng thái `TODO`, kích hoạt Roadmap sang `ACTIVE` và đánh dấu Proposal là `APPLIED`.
* **File nguồn PlantUML:** [`docs/uml/sequence/seq-04-apply-official-schedule.puml`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/sequence/seq-04-apply-official-schedule.puml)

```mermaid
sequenceDiagram
    autonumber
    actor User as Learner
    participant UI as Next.js Web Client
    participant Router as RoadmapRouter (FastAPI)
    participant ApplyUC as ApplyProposalUC (Use Case)
    participant Val as AvailabilityValidator (Domain Service)
    participant Proposal as Proposal (Domain Entity)
    participant Roadmap as Roadmap (Domain Entity)
    participant ProposalRepo as SqlProposalRepo (ProposalRepoPort)
    participant RoadmapRepo as SqlRoadmapRepo (RoadmapRepoPort)
    participant TaskRepo as SqlTaskRepo (TaskRepoPort)
    participant DB as PostgreSQL 16

    User->>UI: Xem xét Bản xem trước Đề xuất -> Bấm [Áp dụng Lịch]
    UI->>Router: POST /api/v1/roadmaps/{id}/apply {"proposal_id": "prop_456"}
    Router->>ApplyUC: execute(userId, roadmapId, proposalId)
    ApplyUC->>RoadmapRepo: get_user_availability(userId)
    RoadmapRepo->>DB: query_user_availability(userId)
    DB-->>RoadmapRepo: availabilityRecord
    RoadmapRepo-->>ApplyUC: UserAvailabilityProfile

    ApplyUC->>ProposalRepo: find_by_id(proposalId)
    ProposalRepo->>DB: query_proposal_by_id(proposalId)
    DB-->>ProposalRepo: proposalRecord
    ProposalRepo-->>ApplyUC: proposalEntity

    ApplyUC->>Val: validate_schedule_ceiling(proposalEntity.tasks, availabilityProfile)

    alt Tổng thời lượng task vượt quá Quỹ giờ rảnh (Hard Ceiling Violated)
        Val-->>ApplyUC: throw HardCeilingViolationError(exceededDate, totalMinutes, quotaMinutes)
        ApplyUC-->>Router: throw HardCeilingViolationError
        Router-->>UI: 422 Unprocessable Entity {"error": "HARD_CEILING_VIOLATED", "date": "..."}
        UI-->>User: Cảnh báo đỏ: Quá tải giờ rảnh ngày chỉ định! Vui lòng điều chỉnh trước khi lưu.
    else Thỏa mãn trần giờ rảnh
        Val-->>ApplyUC: ValidationResult(valid=true)
        ApplyUC->>RoadmapRepo: find_by_id(roadmapId)
        RoadmapRepo->>DB: query_roadmap_by_id(roadmapId)
        DB-->>RoadmapRepo: roadmapRecord
        RoadmapRepo-->>ApplyUC: roadmapEntity

        ApplyUC->>Proposal: apply()
        Proposal-->>ApplyUC: appliedProposal (status="APPLIED")

        ApplyUC->>Roadmap: activate(officialSchedule)
        Roadmap-->>ApplyUC: activeRoadmap (status="ACTIVE")

        Note over ApplyUC,DB: ACID Transaction (Unit of Work): Hủy task cũ -> Insert task mới (TODO) -> Cập nhật Roadmap & Proposal
        ApplyUC->>TaskRepo: cancel_pending_tasks(roadmapId)
        TaskRepo->>DB: UPDATE tasks SET status = 'CANCELLED' WHERE roadmap_id = ... AND status = 'TODO'
        DB-->>TaskRepo: OK
        TaskRepo-->>ApplyUC: OK

        ApplyUC->>TaskRepo: save_tasks_batch(proposalEntity.tasks)
        TaskRepo->>DB: INSERT INTO tasks (...) VALUES (...)
        DB-->>TaskRepo: OK
        TaskRepo-->>ApplyUC: OK

        ApplyUC->>RoadmapRepo: save(activeRoadmap)
        RoadmapRepo->>DB: UPDATE roadmaps SET status = 'ACTIVE' ...
        DB-->>RoadmapRepo: OK
        RoadmapRepo-->>ApplyUC: OK

        ApplyUC->>ProposalRepo: save(appliedProposal)
        ProposalRepo->>DB: UPDATE schedule_proposals SET status = 'APPLIED' ...
        DB-->>ProposalRepo: OK
        ProposalRepo-->>ApplyUC: OK

        ApplyUC-->>Router: ApplyResponseDTO(status="ACTIVE")
        Router-->>UI: 200 OK {"status": "ACTIVE"}
        UI-->>User: Thông báo kích hoạt thành công! Điều hướng vào Màn hình Lịch làm việc.
    end
```

---

## 6. Sequence Diagram 5: Thực thi Phiên học Tập trung (UC-SESS-01)
* **Ca sử dụng:** `UC-SESS-01: Thực hiện phiên học tập trung`.
* **Yêu cầu chức năng:** `FR-SESS-001`, `FR-SESS-002`, `OS-07` (Nhịp tim 60s).
* **Mô tả kịch bản:** Vòng đời trọn vẹn của phiên học tập trung gồm 3 mốc tương tác: Khởi tạo phiên (`start`) với kiểm tra xung đột phiên đang chạy (409 Conflict), đồng bộ nhịp tim định kỳ mỗi 60 giây (`record_heartbeat`) để bảo vệ thời gian tích lũy chống rớt mạng, và chốt phiên hoàn thành (`finish`), phân tách rõ ràng trách nhiệm giữa `SessionRepo` và `TaskRepo` qua Unit of Work, cập nhật trạng thái nhiệm vụ sang `COMPLETED`. (Kịch bản minh họa: Người học kích hoạt chế độ đếm ngược Pomodoro/Time-boxing 50 phút).
* **File nguồn PlantUML:** [`docs/uml/sequence/seq-05-study-session-pomodoro.puml`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/sequence/seq-05-study-session-pomodoro.puml)

```mermaid
sequenceDiagram
    autonumber
    actor User as Learner
    participant UI as Study Workspace (Next.js Client)
    participant Router as SessionRouter (FastAPI)
    participant SessionUC as StudySessionUC (Use Case)
    participant SessionEntity as StudySession (Domain Entity)
    participant TaskEntity as Task (Domain Entity)
    participant SessionRepo as SqlSessionRepo (SessionRepoPort)
    participant TaskRepo as SqlTaskRepo (TaskRepoPort)
    participant UoW as SqlUnitOfWork (UnitOfWorkPort)
    participant DB as PostgreSQL 16

    Note over User,DB: 1. Khởi tạo Phiên học (Start Session)
    User->>UI: Chọn Task & Bấm [Bắt đầu Phiên học]
    UI->>Router: POST /api/v1/sessions {"task_ids": ["task_1"], "planned_minutes": 50}
    Router->>SessionUC: start_session(cmd: StartSessionCommand)
    SessionUC->>SessionRepo: find_active_session_by_user(userId)
    SessionRepo->>DB: query_active_session(userId)
    DB-->>SessionRepo: activeSessionRecord

    alt Đang có phiên khác hoạt động (Active Session Exists)
        SessionRepo-->>SessionUC: existingActiveSession
        SessionUC-->>Router: throw ActiveSessionConflictException
        Router-->>UI: 409 Conflict {"error": "ACTIVE_SESSION_EXISTS"}
        UI-->>User: Cảnh báo: Bạn đang có phiên học khác chưa hoàn thành!
    else Không có phiên xung đột
        SessionRepo-->>SessionUC: null
        SessionUC->>SessionEntity: start(userId, taskIds, plannedMinutes)
        SessionEntity-->>SessionUC: sessionEntity (status="IN_PROGRESS")
        SessionUC->>SessionRepo: save_session(sessionEntity)
        SessionRepo->>DB: insert_study_session(sessionData)
        DB-->>SessionRepo: session_id = "sess_101"
        SessionRepo-->>SessionUC: persistedSession
        SessionUC-->>Router: SessionStartedDTO(session_id="sess_101")
        Router-->>UI: 201 Created {"session_id": "sess_101"}
        UI-->>User: Mở giao diện Pomodoro Workspace, đếm ngược thời gian
    end

    Note over User,DB: 2. Đồng bộ Nhịp tim định kỳ (Mỗi 60s)
    loop Mỗi 60 giây trong phiên (Heartbeat Sync)
        UI->>Router: POST /api/v1/sessions/sess_101/heartbeat {"actual_minutes": X}
        Router->>SessionUC: record_heartbeat(session_id="sess_101", actual_minutes=X)
        SessionUC->>SessionRepo: find_by_id("sess_101")
        SessionRepo->>DB: query_session_by_id("sess_101")
        DB-->>SessionRepo: sessionRecord
        SessionRepo-->>SessionUC: sessionEntity
        SessionUC->>SessionEntity: record_heartbeat(actual_minutes)
        SessionEntity-->>SessionUC: updatedSession
        SessionUC->>SessionRepo: update_heartbeat(sessionEntity)
        SessionRepo->>DB: update_session_heartbeat("sess_101", X, timestamp)
        DB-->>SessionRepo: OK
        SessionRepo-->>SessionUC: OK
        SessionUC-->>Router: HeartbeatAckDTO(synced_minutes=X)
        Router-->>UI: 200 OK {"ack": true, "synced_minutes": X}
    end

    Note over User,DB: 3. Hoàn tất Phiên học (Finish Session)
    User->>UI: Đánh dấu Task hoàn thành & Bấm [Kết thúc Phiên]
    UI->>Router: POST /api/v1/sessions/sess_101/finish {"completed_task_ids": ["task_1"]}
    Router->>SessionUC: finish_session(cmd: FinishSessionCommand)
    SessionUC->>SessionRepo: find_by_id("sess_101")
    SessionRepo->>DB: query_session_by_id("sess_101")
    DB-->>SessionRepo: sessionRecord
    SessionRepo-->>SessionUC: sessionEntity
    SessionUC->>SessionEntity: finish(takeaways)
    SessionEntity-->>SessionUC: sessionEntity (status="COMPLETED")

    SessionUC->>TaskRepo: find_tasks_by_ids(["task_1"])
    TaskRepo->>DB: query_tasks_by_ids(["task_1"])
    DB-->>TaskRepo: taskRecords
    TaskRepo-->>SessionUC: taskEntities
    SessionUC->>TaskEntity: mark_completed()
    TaskEntity-->>SessionUC: updatedTaskEntity

    SessionUC->>UoW: begin_transaction()
    SessionUC->>SessionRepo: update(sessionEntity)
    SessionRepo->>DB: UPDATE study_sessions SET status = 'COMPLETED' ...
    DB-->>SessionRepo: OK
    SessionRepo-->>SessionUC: OK

    SessionUC->>TaskRepo: update(taskEntity)
    TaskRepo->>DB: UPDATE tasks SET status = 'COMPLETED', completed_at = NOW() ...
    DB-->>TaskRepo: OK
    TaskRepo-->>SessionUC: OK

    SessionUC->>UoW: commit()
    UoW->>DB: COMMIT
    DB-->>UoW: OK
    UoW-->>SessionUC: OK

    SessionUC-->>Router: SessionFinishedDTO(status="COMPLETED")
    Router-->>UI: 200 OK {"status": "COMPLETED"}
    UI-->>User: Hiển thị màn hình Tổng kết thành tựu & Chúc mừng hoàn thành!
```

---

## 7. Sequence Diagram 6: Thiết lập Tạm dừng Lộ trình & Domino Shift (UC-ADAPT-02)
* **Ca sử dụng:** `UC-ADAPT-02: Thiết lập tạm dừng lộ trình`.
* **Yêu cầu chức năng:** `FR-ADAPT-001`, `BUSR-01` (Domino Shift tất định).
* **Mô tả kịch bản:** Khi người học có biến cố cần nghỉ học, hệ thống kích hoạt giải thuật toán học tất định `DominoShiftCalculator` trong tầng Domain. Thuật toán tịnh tiến toàn bộ các nhiệm vụ chưa thực hiện (`TODO`) lùi sang các ngày rảnh kế tiếp trong quỹ thời gian khả dụng mà không làm đảo lộn thứ tự tiên quyết (Prerequisites), thực thi tức thời (< 50ms) mà không phụ thuộc vào AI. Thao tác dời ngày được gói vào nghiệp vụ rich domain `Task.reschedule()`.
* **File nguồn PlantUML:** [`docs/uml/sequence/seq-06-pause-domino-shift.puml`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/sequence/seq-06-pause-domino-shift.puml)

```mermaid
sequenceDiagram
    autonumber
    actor User as Learner
    participant UI as Next.js Web Client
    participant Router as RoadmapRouter (FastAPI)
    participant PauseUC as PauseRoadmapUC (Use Case)
    participant RoadmapEntity as Roadmap (Domain Entity)
    participant Domino as DominoShiftCalculator (Domain Service)
    participant TaskEntity as Task (Domain Entity)
    participant PauseRecordEntity as PauseRecord (Domain Entity)
    participant Repo as SqlRoadmapRepo (RoadmapRepoPort)
    participant DB as PostgreSQL 16

    User->>UI: Bấm [Tạm dừng Lộ trình] -> Nhập ngày tạm dừng, ngày tiếp tục & lý do
    UI->>Router: POST /api/v1/roadmaps/{id}/pause (start_date, resume_date, reason)
    Router->>PauseUC: execute(cmd: PauseRoadmapCommand)

    alt startDate >= resumeDate (Khoảng thời gian không hợp lệ)
        PauseUC-->>Router: throw InvalidPauseDateRangeException
        Router-->>UI: 422 Unprocessable Entity {"error": "INVALID_DATE_RANGE"}
        UI-->>User: Báo lỗi: Ngày tiếp tục học phải sau ngày bắt đầu tạm dừng
    else Khoảng thời gian hợp lệ
        PauseUC->>Repo: find_roadmap_by_id(roadmapId)
        Repo->>DB: query_roadmap_by_id(roadmapId)
        DB-->>Repo: roadmapRecord
        Repo-->>PauseUC: roadmapEntity

        alt roadmapEntity.status != 'ACTIVE'
            PauseUC-->>Router: throw InvalidRoadmapStateException
            Router-->>UI: 409 Conflict {"error": "ROADMAP_NOT_ACTIVE"}
            UI-->>User: Cảnh báo: Chỉ có thể tạm dừng lộ trình đang hoạt động (ACTIVE)
        else Lộ trình ACTIVE hợp lệ
            PauseUC->>Repo: get_todo_tasks_from_date(roadmapId, startDate)
            Repo->>DB: query_todo_tasks_from_date(roadmapId, startDate)
            DB-->>Repo: todoTaskRecords
            Repo-->>PauseUC: todoTasks
            PauseUC->>Repo: get_user_availability(userId)
            Repo->>DB: query_user_availability(userId)
            DB-->>Repo: availabilityRecord
            Repo-->>PauseUC: availabilityProfile

            PauseUC->>Domino: calculate_shifted_dates(todoTasks, startDate, resumeDate, availabilityProfile)
            Note over Domino: Thuật toán tất định: Tính khoảng dời -> Tịnh tiến ngày học sang ngày rảnh -> Giữ nguyên quan hệ tiên quyết (< 50ms)
            Domino-->>PauseUC: shiftedTaskDatesMap

            loop Với mỗi task trong danh sách tịnh tiến
                PauseUC->>TaskEntity: reschedule(shiftedDate)
                TaskEntity-->>PauseUC: updatedTaskEntity
            end

            PauseUC->>RoadmapEntity: pause(startDate, resumeDate, reason)
            RoadmapEntity-->>PauseUC: updatedRoadmap (status="PAUSED")

            PauseUC->>PauseRecordEntity: create(roadmapId, startDate, resumeDate, reason)
            PauseRecordEntity-->>PauseUC: pauseRecordEntity

            PauseUC->>Repo: apply_pause_and_domino_shift(roadmapEntity, pauseRecordEntity, shiftedTasks)
            Note over Repo,DB: ACID Persistence: Lưu pause_records -> Set Roadmap PAUSED -> Batch update ngày học mới cho Tasks TODO
            Repo->>DB: execute_atomic_domino_shift_tx(roadmapData, pauseRecordData, shiftedTasksData)
            DB-->>Repo: transaction_success
            Repo-->>PauseUC: success_ack

            PauseUC-->>Router: PauseResultDTO(status="PAUSED", shifted_count=shiftedCount)
            Router-->>UI: 200 OK {"status": "PAUSED", "shifted_count": shiftedCount}
            UI-->>User: Cập nhật giao diện: Lộ trình đã TẠM DỪNG, các nhiệm vụ đã được tịnh tiến an toàn!
        end
    end
```

---

## 8. Sequence Diagram 7: Đồng bộ Lịch 1 Chiều WebCal RFC 5545 (UC-CAL-02)
* **Ca sử dụng:** `UC-CAL-02: Ngoại vi — Đồng bộ lịch 1 chiều WebCal`.
* **Yêu cầu chức năng:** `FR-CALENDAR-002`, `NFR-SEC-004` (Bảo mật token và log sanitizer).
* **Mô tả kịch bản:** Ứng dụng lịch bên ngoài (Google Calendar, Apple Calendar) gửi yêu cầu HTTP GET định kỳ lấy dữ liệu lịch. Request đi qua `LogSanitizerMiddleware` để kiểm duyệt và che giấu token bí mật khỏi log máy chủ. Use Case kiểm tra tính hợp lệ của token băm (SHA-256), truy vấn các nhiệm vụ chính thức và sử dụng `IcalGeneratorAdapter` để sinh luồng nội dung iCalendar chuẩn RFC 5545 (`text/calendar`).
* **File nguồn PlantUML:** [`docs/uml/sequence/seq-07-webcal-sync-export.puml`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/sequence/seq-07-webcal-sync-export.puml)

```mermaid
sequenceDiagram
    autonumber
    actor ExtCal as External Calendar App (Google / Apple Calendar)
    participant LogMid as LogSanitizerMiddleware (Security Filter)
    participant Router as CalendarRouter (FastAPI)
    participant CalUC as ExportCalendarFeedUC (Use Case)
    participant WebCalRepo as SqlWebCalRepo (WebCalRepoPort)
    participant TaskRepo as SqlTaskRepo (TaskRepoPort)
    participant IcalGen as IcalGeneratorAdapter (CalendarExportPort)
    participant DB as PostgreSQL 16

    ExtCal->>LogMid: GET /api/v1/calendar/feed/{raw_token}.ics (HTTP Polling định kỳ)
    Note over LogMid: Che giấu token nhạy cảm trong server access log (REDACTED)
    LogMid->>Router: forward_sanitized_request(raw_token)
    Router->>CalUC: export_feed_by_token(raw_token)

    Note over CalUC: Băm SHA-256 token thô: token_hash = hash_sha256(raw_token)
    CalUC->>WebCalRepo: find_active_subscription_by_hash(token_hash)
    WebCalRepo->>DB: query_active_webcal_token(token_hash)
    DB-->>WebCalRepo: tokenRecord

    alt Token không hợp lệ hoặc đã bị vô hiệu hóa
        WebCalRepo-->>CalUC: null
        CalUC-->>Router: throw InvalidCalendarTokenException
        Router-->>ExtCal: 401 Unauthorized {"error": "INVALID_CALENDAR_TOKEN"}
    else Token hợp lệ (ACTIVE)
        WebCalRepo-->>CalUC: webCalSubscriptionEntity
        CalUC->>WebCalRepo: record_feed_access(token_hash)
        WebCalRepo->>DB: update_last_accessed_timestamp(token_hash)
        DB-->>WebCalRepo: OK
        WebCalRepo-->>CalUC: OK

        CalUC->>TaskRepo: get_active_scheduled_tasks(userId)
        TaskRepo->>DB: query_tasks_for_calendar_feed(userId)
        DB-->>TaskRepo: taskRecords
        TaskRepo-->>CalUC: taskEntities

        CalUC->>IcalGen: generate_ical_stream(taskEntities)
        Note over IcalGen: Kết xuất chuỗi iCalendar RFC 5545 (VCALENDAR, VEVENT, DTSTART, DTEND)
        IcalGen-->>CalUC: icalContentStream (.ics)
        CalUC-->>Router: CalendarFeedDTO(content=icalContentStream, mime_type="text/calendar")
        Router-->>ExtCal: 200 OK (Content-Type: text/calendar; charset=utf-8)
        Note over ExtCal: Ứng dụng Lịch tự động nạp sự kiện và hiển thị trên Lịch cá nhân của người học
    end
```

---

## 9. Sequence Diagram 8: Tự động Quét & Chốt Phiên Gián đoạn Celery Beat (UC-SESS-02)
* **Ca sử dụng:** `UC-SESS-02: Xử lý gián đoạn phiên học`.
* **Yêu cầu chức năng:** `FR-SESS-003`, `OS-01` (Quy tắc phân định trạng thái gián đoạn).
* **Mô tả kịch bản:** Tác vụ nền định kỳ kích hoạt mỗi 5 phút bởi Celery Beat bằng cách đẩy message bất đồng bộ vào Redis Broker. Worker nhận message và gọi Use Case quét các phiên học đang ở trạng thái `IN_PROGRESS` nhưng mất kết nối heartbeat quá 5 phút. Domain Service `AbandonmentEvaluator` áp dụng quy tắc OS-01: Nếu phiên đã hoàn thành $\ge 50\%$ thời lượng dự kiến hoặc có ít nhất 1 task hoàn thành thì chốt `PARTIAL_COMPLETED` (công nhận công sức, trả task dở dang về `TODO` trong Backlog); ngược lại chốt `CANCELLED` (hủy phiên, bảo toàn task `TODO`).
* **File nguồn PlantUML:** [`docs/uml/sequence/seq-08-abandoned-session-sweep.puml`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/sequence/seq-08-abandoned-session-sweep.puml)

```mermaid
sequenceDiagram
    autonumber
    actor Beat as Celery Beat (Periodic Timer)
    participant Broker as Redis 7.2 (Message Broker)
    participant Worker as SessionSweepWorker (Celery Task)
    participant SweepUC as SweepAbandonedSessionsUC (Use Case)
    participant Evaluator as AbandonmentEvaluator (Domain Service - OS-01)
    participant SessionEntity as StudySession (Domain Entity)
    participant SessionRepo as SqlSessionRepo (SessionRepoPort)
    participant TaskRepo as SqlTaskRepo (TaskRepoPort)
    participant DB as PostgreSQL 16

    Note over Beat,DB: Tác vụ nền chạy định kỳ mỗi 5 phút quét các phiên mất heartbeat quá 5 phút
    Beat->>Broker: enqueue_task("sweep_abandoned_sessions", args=[threshold=5])
    Note over Beat: Beat gửi bất đồng bộ vào Redis rồi tiếp tục chu kỳ hẹn giờ
    Broker->>Worker: dispatch_task("sweep_abandoned_sessions", args=[threshold=5])
    Worker->>SweepUC: execute(threshold_minutes=5)
    SweepUC->>SessionRepo: find_stale_in_progress_sessions(interval_minutes=5)
    SessionRepo->>DB: query_sessions_heartbeat_older_than(interval_minutes=5)
    DB-->>SessionRepo: staleSessionRecords
    SessionRepo-->>SweepUC: List[staleSessions]

    loop Với mỗi staleSession trong danh sách
        SweepUC->>TaskRepo: get_completed_tasks_count_in_session(sessionId)
        TaskRepo->>DB: query_completed_task_count(sessionId)
        DB-->>TaskRepo: completedCount
        TaskRepo-->>SweepUC: completedCount

        SweepUC->>Evaluator: evaluate_disposition(staleSession, completedCount)
        Note over Evaluator: Áp dụng OS-01: actualMinutes >= 50% plannedMinutes HOẶC completedCount >= 1 => PARTIAL_COMPLETED; Ngược lại => CANCELLED
        Evaluator-->>SweepUC: evaluationResult (status, dispositionReason)

        SweepUC->>SessionEntity: mark_abandoned(evaluationResult.status, staleSession.lastHeartbeatAt)
        SessionEntity-->>SweepUC: finalizedSession

        SweepUC->>SessionRepo: finalize_abandoned_session(finalizedSession)
        alt Thỏa mãn ngưỡng: PARTIAL_COMPLETED
            Note over SessionRepo,DB: Transaction: Set session PARTIAL_COMPLETED & Trả task dở dang về TODO
            SessionRepo->>DB: execute_atomic_partial_finalize(sessionData)
            DB-->>SessionRepo: OK
        else Dưới ngưỡng: CANCELLED
            Note over SessionRepo,DB: Transaction: Set session CANCELLED & Trả toàn bộ task dở dang về TODO
            SessionRepo->>DB: execute_atomic_cancel_finalize(sessionData)
            DB-->>SessionRepo: OK
        end
        SessionRepo-->>SweepUC: sessionFinalizedAck
    end

    SweepUC-->>Worker: SweepSummaryDTO(processed_count, partial_count, cancelled_count)
    Worker->>Worker: log_summary_and_metrics(SweepSummaryDTO)
```

---

## 10. Ma trận Kiểm tra Tính Nhất quán (Consistency & Traceability Matrix)

| Mã Sơ đồ | Tên Kịch bản (Use-Case Realization) | Ca Sử Dụng Liên Kết | Lớp Điều Phối (Use Case) | Thực Thể & Domain Service | Adapters & Repositories | Ràng Buộc Nghiệp Vụ / Tiêu Chuẩn |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **SSD** | Sơ đồ Tuần tự Hệ thống Tổng quan | Toàn hệ thống | :FocusFlow System | SRL 3 Pha | Web Client | ISO/IEC 19505-2, SRL Framework, OS-07 (5m Timeout) |
| **SD1** | Đăng nhập Hệ thống | `UC-AUTH-02` | `AuthenticateUserUC` | `User`, `PasswordHasher` | `SqlUserRepo`, `JwtTokenProvider` | `NFR-SEC-001`, Argon2, HttpOnly JWT |
| **SD2** | Khởi tạo Mục tiêu & Đăng ký Lộ trình | `UC-PLAN-01` | `CreateGoalAndRoadmapUC` | `Goal`, `Roadmap` | `SqlRoadmapRepo` | `FR-PLAN-001`, `targetDate > today` |
| **SD3** | Sinh Cột mốc & Phân rã Nhiệm vụ AI | `UC-PLAN-02` | `GenerateProposalUC` | `PromptSanitizer` | `RedisQuotaAdapter`, `GeminiLLMAdapter`, `SqlProposalRepo` | `OS-02` (Two-Phase Quota), 55s Timeout, ADR-005 (SSE Streaming) |
| **SD4** | Áp dụng Lịch học & Kiểm tra Quỹ giờ | `UC-PLAN-03` | `ApplyProposalUC` | `AvailabilityValidator`, `Proposal`, `Roadmap` | `SqlRoadmapRepo`, `SqlProposalRepo`, `SqlTaskRepo` | `BUSR-02`, Hard Ceiling Gate, ACID Persist (Task `TODO`) |
| **SD5** | Thực thi Phiên học Tập trung | `UC-SESS-01` | `StudySessionUC` | `StudySession`, `Task` | `SqlSessionRepo`, `SqlTaskRepo`, `SqlUnitOfWork` | `OS-07` (Nhịp tim 60s), 409 Conflict, Pomodoro/Timebox Timer |
| **SD6** | Tạm dừng Lộ trình & Domino Shift | `UC-ADAPT-02` | `PauseRoadmapUC` | `DominoShiftCalculator`, `Roadmap`, `Task`, `PauseRecord` | `SqlRoadmapRepo` | `BUSR-01`, Tất định < 50ms, Giữ tiên quyết, Task `TODO` |
| **SD7** | Đồng bộ Lịch 1 Chiều WebCal | `UC-CAL-02` | `ExportCalendarFeedUC` | Token Sanitizer Logic | `SqlWebCalRepo`, `SqlTaskRepo`, `IcalGeneratorAdapter` | `RFC 5545`, SHA-256 Token, `NFR-SEC-004`, `FR-CALENDAR-002` |
| **SD8** | Tự động Quét & Chốt Phiên Gián đoạn | `UC-SESS-02` | `SweepAbandonedSessionsUC` | `AbandonmentEvaluator`, `StudySession` | `SessionSweepWorker`, `SqlSessionRepo`, `SqlTaskRepo`, `Redis` | `OS-01` (Phân định 50% / 1 task), Celery Beat async queue |

---
*Tài liệu được cập nhật và kiểm duyệt tự động theo tiêu chuẩn ISO/IEC 19505-2 và kiến trúc Lục giác FocusFlow.*