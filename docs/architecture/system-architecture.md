# FocusFlow — Tài liệu Kiến trúc Hệ thống (System Architecture Document - arc42)
## Phiên bản: v1.1 — Chuẩn Kiến trúc Cơ sở Hoàn chỉnh (Comprehensive Architecture Baseline)
**Dự án:** FocusFlow — Hệ thống hỗ trợ lập kế hoạch và thực thi lộ trình tự học thích ứng tích hợp AI  
**Tiêu chuẩn tài liệu:** arc42 Architecture Template (v8.2), ISO/IEC/IEEE 42010:2011, UML 2.5.1  
**Căn cứ đánh giá học thuật:** Khung Rubric Đồ án Tốt nghiệp CNTT — Tiêu chí TC1, TC2.1 & TC2.3 (Mức 5)  
**Tài liệu liên kết nguồn:**
- Định nghĩa bài toán & Yêu cầu: [`docs/requirements/problem-definition.md`](file:///Users/vuthang/Documents/FocusFlow/docs/requirements/problem-definition.md), [`docs/requirements/business-goals-and-kpis.md`](file:///Users/vuthang/Documents/FocusFlow/docs/requirements/business-goals-and-kpis.md)
- Đặc tả yêu cầu phần mềm: [`docs/srs/srs-v1.0.md`](file:///Users/vuthang/Documents/FocusFlow/docs/srs/srs-v1.0.md)
- Sơ đồ ca sử dụng & Mô hình hành vi: [`docs/uml/UC_Dia.drawio`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/UC_Dia.drawio), [`docs/uml/sequence-diagrams.md`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/sequence-diagrams.md), [`docs/uml/state-machines.md`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/state-machines.md)
- Biểu đồ Lớp (Domain Model & DCD): [`docs/uml/class-diagrams.md`](file:///Users/vuthang/Documents/FocusFlow/docs/uml/class-diagrams.md)
- Thiết kế cơ sở dữ liệu: [`docs/database/database-schema-design.md`](file:///Users/vuthang/Documents/FocusFlow/docs/database/database-schema-design.md), [`docs/database/schema.sql`](file:///Users/vuthang/Documents/FocusFlow/docs/database/schema.sql)
- Các bản ghi quyết định kiến trúc: [`docs/decisions/`](file:///Users/vuthang/Documents/FocusFlow/docs/decisions) (ADR-001 đến ADR-006)

---

## MỤC LỤC THEO CHUẨN ARC42
1. [Giới thiệu & Mục tiêu (Introduction and Goals)](#1-giới-thiệu--mục-tiêu-introduction-and-goals)
2. [Ràng buộc Kiến trúc (Architecture Constraints)](#2-ràng-buộc-kiến-trúc-architecture-constraints)
3. [Bối cảnh & Phạm vi (Context and Scope)](#3-bối-cảnh--phạm-vi-context-and-scope)
4. [Chiến lược Giải pháp (Solution Strategy)](#4-chiến-lược-giải-pháp-solution-strategy)
5. [Cấu trúc Khối tĩnh (Building Block View)](#5-cấu-trúc-khối-tĩnh-building-block-view)
6. [Động lực học & Luồng Thực thi (Runtime View)](#6-động-lực-học--luồng-thực-thi-runtime-view)
7. [Kiến trúc Triển khai (Deployment View)](#7-kiến-trúc-triển-khai-deployment-view)
8. [Các Khái niệm Xuyên suốt (Cross-cutting Concepts)](#8-các-khái-niệm-xuyên-suốt-cross-cutting-concepts)
9. [Các Quyết định Kiến trúc Cốt lõi (Architecture Decisions - ADRs)](#9-các-quyết-định-kiến-trúc-cốt-lõi-architecture-decisions---adrs)
10. [Yêu cầu Chất lượng (Quality Requirements)](#10-yêu-cầu-chất-lượng-quality-requirements)
11. [Rủi ro & Nợ Kỹ thuật (Risks and Technical Debt)](#11-rủi-ro--nợ-kỹ-thuật-risks-and-technical-debt)
12. [Thuật ngữ Chuẩn hóa (Glossary)](#12-thuật-ngữ-chuẩn-hóa-glossary)

---

## 1. Giới thiệu & Mục tiêu (Introduction and Goals)

### 1.1 Tổng quan bài toán
FocusFlow giải quyết chuỗi đứt gãy liên hoàn của người tự học công nghệ và kỹ năng số:
1. **Rào cản phân rã mục tiêu (Decomposition Barrier):** Mục tiêu lớn trừu tượng khó chuyển hóa thành đầu việc học tập khả thi hàng ngày.
2. **Phân mảnh công cụ (Tool Fragmentation):** Người học bị phân tán sự chú ý giữa Chatbot AI, Google Calendar, Notion và Pomodoro App độc lập.
3. **Đứt gãy kế hoạch khi có biến cố (Rigid Planning Failure):** Khi có việc bận đột xuất 1–2 ngày, kế hoạch bị đổ vỡ dồn ứ, dẫn đến bỏ cuộc.

### 1.2 Mục tiêu nghiệp vụ & 5 KPI định lượng
Hệ thống được thiết kế để thỏa mãn 5 chỉ số KPI định lượng đo lường được trong đợt thử nghiệm người dùng thật (UAT):

| Mã KPI | Tên chỉ số | Giá trị mục tiêu | Ý nghĩa đo lường kỹ thuật |
|---|---|---|---|
| **KPI 1** | Thời gian khởi tạo lộ trình (*Plan Creation Time*) | $\le \mathbf{5}$ phút | Tự động hóa quá trình phân rã mục tiêu thay vì mất 30–60 phút thủ công. |
| **KPI 2** | Hiệu quả thực thi buổi học (*Session Execution Efficiency*) | $\ge \mathbf{80\%}$ | Tỷ lệ hoàn thành các đầu việc được lên lịch trong mỗi phiên học. |
| **KPI 3** | Tỷ lệ duy trì lộ trình (*Plan Adherence Rate*) | $\ge \mathbf{70\%}$ | Tỷ lệ số buổi học tham gia thực tế trên tổng số buổi đã lên lịch (loại trừ thời gian PAUSED). |
| **KPI 4** | Tỷ lệ hoàn thành tác vụ (*Task Success Rate*) | $\ge \mathbf{90\%}$ | Người dùng hoàn thành luồng chính (tạo lộ trình, chạy Pomodoro, lưu ghi chú, xem báo cáo). |
| **KPI 5** | Điểm trải nghiệm người dùng (*SUS Usability Score*) | $\ge \mathbf{80/100}$ | Đánh giá độ khả dụng theo bảng câu hỏi chuẩn hóa System Usability Scale trên $\ge 10$ người dùng. |

### 1.3 Các bên liên quan (Stakeholders)
- **Learner (Người học):** Sinh viên, người chuyển ngành cần lộ trình học thích ứng và không gian học tập trung (Study Workspace).
- **Administrator (Quản trị viên hạ tầng):** Giám sát mức tiêu thụ token AI, quản trị hạn ngạch Quota phân tầng (Free/Premium).
- **External Systems:** Ứng dụng lịch cá nhân (Google Calendar/Apple Calendar qua WebCal RFC 5545), External LLM Provider (Google Gemini API).
- **Giảng viên hướng dẫn & Hội đồng đánh giá:** Đánh giá tính chuẩn mực công nghệ phần mềm, kiến trúc sạch và khả năng vận hành thực chứng.

---

## 2. Ràng buộc Kiến trúc (Architecture Constraints)

| Mã Ràng buộc | Phân loại | Nội dung chi tiết | Tác động kiến trúc |
|---|---|---|---|
| **CON-01** | Thời gian & Nhân lực | Hoàn thành toàn bộ đồ án trong 15 tuần với đội ngũ 2 sinh viên. | Tránh Microservices phức tạp; chọn Modular Monolith để tối ưu chia việc độc lập giữa Frontend và Backend. |
| **CON-02** | Ngân sách vận hành | Chi phí gọi API LLM và máy chủ hạ tầng ở mức sinh viên ($0 – $5/tháng). | Thiết kế Quota Guard hai pha (Reserve/Commit) ngăn cạn kiệt ngân sách; tích hợp Mock Upgrade Sandbox. |
| **CON-03** | Bảo mật bí mật | Tuyệt đối không rò rỉ API Key của LLM, SECRET_KEY ra client (*Zero Secret Leak*). | Backend proxy toàn bộ cuộc gọi AI; cô lập biến môi trường; lọc sạch secret khỏi access logs. |
| **CON-04** | Môi trường nghiệm thu | Hệ thống phải demo offline mượt mà trước Hội đồng (Local Docker) và deploy online cho UAT người dùng thật. | Áp dụng mô hình triển khai Hybrid: Docker Compose Local đồng nhất với Cloud PaaS (Vercel + Render + Managed PostgreSQL). |
| **CON-05** | Chuẩn công nghệ | Tuân thủ ISO/IEC 42010, UML 2.5.1, RFC 5545 iCalendar, ISO/IEC 9075 SQL. | Mọi sơ đồ, schema, API contract phải có tính truy vết 1:1, không tự tạo thực thể không có căn cứ. |

---

## 3. Bối cảnh & Phạm vi (Context and Scope)

### 3.1 Bối cảnh Nghiệp vụ (Business Context - C4 Context)

```mermaid
flowchart TD
    User["Learner / Người học<br>[Person]<br>Sinh viên, người chuyển ngành, tự ôn luyện"]
    Admin["Administrator<br>[Person - Service Role]<br>Quản trị viên cấu hình hạn ngạch & hạ tầng"]
    
    subgraph Boundary["FocusFlow System Boundary"]
        FocusFlow["FocusFlow Platform<br>[Software System]<br>Nền tảng hỗ trợ lập kế hoạch và thực thi lộ trình tự học thích ứng"]
    end
    
    LLM["External LLM Provider<br>[External SaaS]<br>Google Gemini API (GEMINI_MODEL)<br>Dự phòng OpenAI Adapter"]
    ExtCal["External Calendar Applications<br>[External System]<br>Google Calendar, Apple Calendar, Outlook<br>(Giao thức iCalendar RFC 5545)"]

    User -->|1. Đăng ký, thiết lập mục tiêu, duyệt đề xuất, học tập Workspace| FocusFlow
    Admin -->|Quản trị token quota, giám sát vận hành| FocusFlow
    FocusFlow -->|2. Gửi clean prompt, nhận cấu trúc JSON qua SSE| LLM
    ExtCal -->|3. Polling lịch học 1 chiều qua URL bảo mật /feed/{token}.ics| FocusFlow
```

### 3.2 Bối cảnh Kỹ thuật (Technical Context)
- **Kênh giao tiếp Client-Server:** Giao thức HTTPS (TLS 1.3), RESTful API cho các thao tác CRUD và lệnh điều khiển; Server-Sent Events (SSE) cho luồng dữ liệu AI thời gian thực.
- **Kênh ngoại vi Lịch (Calendar Feed):** HTTP GET 1 chiều trả về MIME type `text/calendar; charset=utf-8` theo chuẩn RFC 5545.
- **Kênh nhà cung cấp AI:** HTTPS POST tới Google Gemini endpoint với cấu trúc JSON định kiểu chặt chẽ bằng Pydantic Schema.

---

## 4. Chiến lược Giải pháp (Solution Strategy)

| Thách thức Kỹ thuật | Giải pháp Kiến trúc Lựa chọn | Căn cứ Quyết định (ADR) |
|---|---|---|
| Đảm bảo tính toàn vẹn nghiệp vụ, dễ kiểm thử độc lập mà không bị dính chặt vào framework | Áp dụng **Kiến trúc Lục giác (Hexagonal Architecture / Ports & Adapters)** trong mô hình **Modular Monolith**. Tách biệt 4 tầng: Domain, Application, Infrastructure, Presentation. | **ADR-001** |
| Phản hồi nhanh, hỗ trợ xử lý dữ liệu AI và JSON Schema an toàn cao | Backend sử dụng **Python 3.12 + FastAPI + Pydantic v2 + SQLAlchemy 2.0 Async (asyncpg)**. | **ADR-002** |
| Giao diện công thái học cao, chuẩn tiếp cận Lighthouse A11y $\ge 90$ | Frontend sử dụng **Next.js 15 (App Router) + React 19 + TypeScript + Tailwind CSS + Shadcn UI**. Quản trị trạng thái tách biệt: **TanStack Query** (Server State) và **Zustand** (Local Workspace State). | **ADR-003** |
| Chống nghẽn I/O khi gọi LLM trễ 5–40s; bảo toàn Quota khi mạng gián đoạn | Giao thức **Server-Sent Events (SSE)** hai chặng đồng nhất kết hợp **Quản trị Quota 2 pha (Reserve/Commit)** và Hard Timeout 55s. | **ADR-005** |
| Xử lý tác vụ nền nặng, quét timeout phiên mất mạng, tính toán định kỳ | Bộ đôi **Celery 5.6 + Redis 7 + Celery Beat** chạy cô lập, thực thi tác vụ idempotency. | **ADR-004** |
| Khắc phục gián đoạn đột ngột (mất mạng/tắt trình duyệt) trong phiên học | Cơ chế **Heartbeat Ping mỗi 60 giây ghi trực tiếp vào PostgreSQL**, kết hợp Celery Beat quét quá hạn 5 phút theo quy tắc phân định kết quả **OS-01**. | **BUSR-09**, **OS-07** |
| Dời lịch tức thời khi có việc bận mà không tốn chi phí AI | Thuật toán **Domino Shift** tất định thực thi trong tầng Domain, tịnh tiến các task chưa hoàn thành sang ngày rảnh kế tiếp trong < 50ms. | **BUSR-07** |

---

## 5. Cấu trúc Khối tĩnh (Building Block View)

### 5.1 Cấp độ 1: Mô hình Vùng chứa (C4 Container View)

```mermaid
flowchart TB
    UserDevice["Trình duyệt Người dùng<br>[Desktop / Mobile Browser]"]
    ExtCalApp["Ứng dụng Lịch Ngoại vi<br>[Google / Apple Calendar]"]
    LLMService["Google Gemini API<br>[External AI SaaS]"]

    subgraph ContainerBoundary["Hạ tầng Vùng chứa FocusFlow"]
        Frontend["Web Frontend Container<br>[Next.js 15, TypeScript, TailwindCSS]<br>Port: 3000"]
        Backend["Backend API Container<br>[FastAPI, Python 3.12, Uvicorn ASGI]<br>Port: 8000"]
        Worker["Worker Queue Container<br>[Celery Worker, Python 3.12]"]
        Beat["Periodic Scheduler Container<br>[Celery Beat]"]
        RedisDB["In-Memory Cache & Broker<br>[Redis 7 Alpine]<br>Port: 6379"]
        PostgresDB["Primary Relational Database<br>[PostgreSQL 16 Alpine]<br>Port: 5432"]
    end

    UserDevice -->|HTTPS / REST & SSE| Frontend
    Frontend -->|Reverse Proxy / Internal HTTP| Backend
    ExtCalApp -->|HTTP GET /api/v1/calendar/feed/{token}.ics| Backend
    
    Backend -->|Async SQLAlchemy / asyncpg| PostgresDB
    Backend -->|Atomic Token Bucket / Cache (DB 0)| RedisDB
    Backend -->|Dispatch Tasks (Broker DB 1)| RedisDB
    
    Beat -->|Schedule Periodic Crons (DB 1)| RedisDB
    RedisDB -->|Consume Task Messages| Worker
    Worker -->|Read / Write Status & Audits| PostgresDB
    
    Backend -->|HTTPS POST JSON (Prompt -> Schema)| LLMService
```

### 5.2 Cấp độ 2: Phân lớp Kiến trúc Lục giác Backend (Hexagonal Internal Decomposition)

Tuân thủ **Quy tắc Phụ thuộc (The Dependency Rule)**: Tầng bên trong không phụ thuộc vào tầng bên ngoài.

```
+─────────────────────────────────────────────────────────────────────────────+
| PRESENTATION LAYER (Driving Adapters)                                       |
| - FastAPI Routers: AuthRouter, RoadmapRouter, SessionRouter, CalendarRouter |
| - Middlewares: AuthMiddleware (JWT), QuotaGuardMiddleware, LogSanitizer     |
+──────────────────────────────────────┬──────────────────────────────────────+
                                       │ calls
+──────────────────────────────────────▼──────────────────────────────────────+
| APPLICATION LAYER (Ports & Use Cases Orchestration)                         |
| - Input Ports: GenerateProposalInputPort, ApplyScheduleInputPort, etc.      |
| - Use Cases: GenerateProposalUC, ApplyProposalUC, PauseRoadmapUC, SessionUC |
| - Output Ports: RoadmapRepoPort, SessionRepoPort, LLMProviderPort, QuotaPort|
+──────────────────────────────────────┬──────────────────────────────────────+
                                       │ orchestrates
+──────────────────────────────────────▼──────────────────────────────────────+
| DOMAIN LAYER (Core Domain Entities & Pure Services)                         |
| - Entities: Roadmap, Milestone, Task, StudySession, AvailabilityProfile     |
| - Value Objects: WebCalToken, QuotaBucket, TimeSlotWindow                   |
| - Domain Services: DominoShiftCalculator (BUSR-07), AvailabilityValidator   |
| - Domain Exceptions: HardCeilingViolationError, QuotaExceededError          |
+─────────────────────────────────────────────────────────────────────────────+
                                       ▲ implements
+──────────────────────────────────────┴──────────────────────────────────────+
| INFRASTRUCTURE LAYER (Driven Adapters)                                      |
| - Repositories: SqlRoadmapRepository, SqlSessionRepository (SQLAlchemy 2.0) |
| - AI Adapters: GeminiAdapter (google-genai SDK), PromptSanitizer            |
| - Cache Adapters: RedisQuotaAdapter (Atomic Lua), RedisCache                |
| - Calendar: IcalGeneratorAdapter (RFC 5545 VCALENDAR)                       |
| - Celery Tasks: CheckAbandonedSessionsTask, ScanDailyOverdueTasks, WeeklySummaryTask |
+─────────────────────────────────────────────────────────────────────────────+
```

### 5.3 Cấp độ 3: Kiến trúc Cơ sở Dữ liệu (Database Persistence View)
Cơ sở dữ liệu PostgreSQL 16 gồm 15 bảng vật lý chuẩn hóa 3NF/BCNF, phân nhóm chức năng:
1. **Quản trị Người dùng & Hạn ngạch:** `users`, `webcal_tokens`, `ai_quotas`, `availabilities`.
2. **Kế hoạch & Lộ trình:** `goals`, `roadmaps`, `milestones`, `tasks`, `schedule_proposals`, `official_schedules`.
3. **Thực thi Phiên học & Ghi chép:** `study_sessions`, `session_tasks`, `study_notes`.
4. **Thích ứng & Đánh giá định kỳ:** `pause_records`, `ai_reviews`.

---

## 6. Động lực học & Luồng Thực thi (Runtime View)

### 6.1 Luồng Phân rã Mục tiêu AI qua SSE & Cổng Kiểm tra Nghiêm ngặt (FR-PLAN-001..003)
- **Tác nhân:** Learner $\rightarrow$ RoadmapRouter $\rightarrow$ QuotaService $\rightarrow$ GenerateProposalUC $\rightarrow$ GeminiAdapter $\rightarrow$ PostgreSQL.
- **Đặc trưng:**
  1. *Pha 1 (Tạm giữ):* `reserve_quota()` tăng `reserved_calls` lên 1 trong `ai_quotas` (chặn race condition).
  2. *Chặng 1 (Milestones):* Sinh 3–7 Milestones qua SSE, Learner chỉnh sửa và bấm duyệt (`milestones.status = 'APPROVED'`).
  3. *Chặng 2 (Tasks & Proposal):* LLM phân rã thành các task chi tiết (30–120 phút). Hoàn tất thành công kích hoạt `commit_quota()` tăng `used_calls = used_calls + 1`. Nếu lỗi/timeout 55s, kích hoạt `refund_quota()` giải phóng `reserved_calls` mà không trừ lượt của người dùng.
  4. *Chặng 3 (Strict Apply Gate):* `AvailabilityValidator` kiểm tra trần giờ rảnh trong ngày (Mode A: Hard Ceiling; Mode B: Soft Overflow $\le 30$ phút). Nếu vi phạm, từ chối với HTTP 422. Nếu hợp lệ, thực thi Transaction lưu vào `official_schedules` và chuyển Roadmap sang `ACTIVE`.

### 6.2 Luồng Tạm dừng Lộ trình & Tịnh tiến Tất định Domino Shift (BUSR-07)
- **Tác nhân:** Learner $\rightarrow$ RoadmapRouter $\rightarrow$ PauseRoadmapUC $\rightarrow$ DominoShiftCalculator $\rightarrow$ SqlRoadmapRepo.
- **Đặc trưng:** Thuật toán tính toán số ngày tạm dừng $N = \text{resume\_date} - \text{start\_date}$, tịnh tiến toàn bộ các task chưa học (`scheduled_date >= start_date`) lùi về sau đúng bằng các ngày khả dụng tiếp theo. Đảm bảo bảo toàn nguyên vẹn thứ tự tiên quyết, hoàn tất trong < 50ms mà không tốn chi phí gọi AI.

### 6.3 Luồng Đồng bộ Phiên học Heartbeat & Quét Timeout Gián đoạn (BUSR-09, OS-01, OS-07)
- **Tác nhân:** Study Workspace $\rightarrow$ SessionRouter $\rightarrow$ PostgreSQL $\leftrightarrow$ Celery Beat $\leftrightarrow$ Celery Worker.
- **Đặc trưng:**
  1. *Heartbeat Ping:* Client gửi `actual_minutes` mỗi 60 giây, cập nhật trực tiếp `actual_minutes` và `last_heartbeat_at = NOW()` vào PostgreSQL (tải cực nhẹ ~0.33 writes/s cho 20 người dùng, bảo toàn dữ liệu khi sự cố).
  2. *Quét gián đoạn (OS-07):* Celery Beat kích hoạt task mỗi 5 phút quét các phiên có `status = 'IN_PROGRESS'` và `last_heartbeat_at < NOW() - INTERVAL '5 minutes'`.
  3. *Chốt trạng thái (OS-01):* Nếu $\text{actual\_minutes} \ge 0.5 \times \text{planned\_minutes}$ hoặc có $\ge 1$ task hoàn tất $\rightarrow$ chốt `PARTIAL_COMPLETED`. Ngược lại chốt `CANCELLED`. Chốt `ended_at = last_heartbeat_at`, bảo toàn từng phút nỗ lực của người học.

---

## 7. Kiến trúc Triển khai (Deployment View)

Hệ thống FocusFlow áp dụng **Mô hình Triển khai Hybrid (Hybrid Deployment Model)** theo **ADR-006**:

```
+─────────────────────────────────────────────────────────────────────────────+
|                         MÔ HÌNH TRIỂN KHAI HYBRID FOCUSFLOW                 |
+──────────────────────────────────────┬──────────────────────────────────────+
|   MÔI TRƯỜNG NỘI BỘ / BẢO VỆ ĐỒ ÁN   |   MÔI TRƯỜNG CLOUD UAT (PRODUCTION)  |
|   (Local Defense Environment)        |   (Public Testing Environment)       |
+──────────────────────────────────────┼──────────────────────────────────────+
| • 100% Container hóa bằng Docker     | • Tên miền hợp nhất: .focusflow.vn   |
|   Compose (6 dịch vụ logic).         | • Frontend: Vercel (app.focusflow.vn)|
| • Chạy mượt mà trên laptop sinh viên | • Backend Web: Render Paid Service   |
|   hoặc máy trạm Hội đồng chấm thi:   |   (api.focusflow.vn - không sleep)   |
|   `docker compose up --build`.       | • Worker & Beat: Render Background   |
| • Hoạt động độc lập, không phụ thuộc |   Worker (chạy liên tục 24/7)        |
|   Internet phòng bảo vệ (trừ AI API).| • Database: Managed PostgreSQL bền vững |
+──────────────────────────────────────┴──────────────────────────────────────+
```

### 7.1 Ma trận Cấu hình Mạng & Biến Môi trường
- **CORS & Cookie Domain:** Cấu hình tên miền gốc chung `.focusflow.vn` cho phép cookie `access_token` chia sẻ SameSite/Same-Origin an toàn giữa `app.focusflow.vn` và `api.focusflow.vn`.
- **Port Mapping:**
  - `frontend`: Cổng `3000`
  - `backend`: Cổng `8000` (Endpoint `/api/v1`, Docs `/docs`, Health `/api/health`)
  - `postgres`: Cổng `5432` (Cô lập trong bridge network trên production)
  - `redis`: Cổng `6379` (Bảo vệ bằng mật khẩu requirepass)

---

## 8. Các Khái niệm Xuyên suốt (Cross-cutting Concepts)

### 8.1 Kiến trúc Bảo mật & Ranh giới Tin cậy (Trust Boundaries)
1. **Xác thực Cookie JWT Hai Token & Quản lý Phiên:** Access Token (15 phút, `HttpOnly`, `Secure`, `SameSite=Lax`, chia sẻ subdomain `.focusflow.vn`) và Refresh Token (7 ngày, lưu trữ và xoay vòng trên Redis với cơ chế Refresh Token Rotation - RTR và Family Revocation; giữ sạch PostgreSQL với đúng 15 bảng nghiệp vụ lõi).
2. **Băm Mật khẩu Chuẩn Hiện đại (NFR-SEC-002):** Sử dụng thuật toán **Argon2id** kháng cự hoàn toàn tấn công GPU/ASIC.
3. **Bảo mật Lịch WebCal RFC 5545 (BUSR-08, OS-05):** Sinh mã 32-byte CSPRN ngẫu nhiên (`secrets.token_hex(32)`), chỉ lưu bản băm SHA-256 vào database.
4. **Vệ sinh Nhật ký Máy chủ (NFR-SEC-004):** `LogSanitizerMiddleware` tự động che giấu token thành `[REDACTED]` trước khi ghi access logs.
5. **Vệ sinh Dữ liệu Prompt AI (NFR-SEC-003):** `PromptSanitizer` loại bỏ định danh cá nhân nhạy cảm (PII: email, mật khẩu, tên thật) trước khi chuyển sang External LLM.

### 8.2 Quản trị Hạn ngạch AI & Mock Sandbox (BUSR-10, OS-02)
- Hạn ngạch được cấp theo chu kỳ hàng tháng (Gói Free: 30 lượt/tháng, Gói Premium: 300 lượt/tháng).
- Nguồn chân lý ACID lưu tại bảng `ai_quotas` trong PostgreSQL.
- Cung cấp **Mock Upgrade Sandbox** (`FR-QUOTA-002`) cho phép giả lập nâng cấp tài khoản nới rộng hạn ngạch để nghiệm thu đồ án mà không tích hợp cổng thanh toán tiền thật.

### 8.3 Xử lý Lỗi & Khả năng Phục hồi (Error Handling & Resilience)
- Hard Timeout 55 giây cho toàn bộ tác vụ AI (`NFR-PERF-001`).
- Chiến lược Exponential Backoff với Full Jitter (`OS-08`) cho các mã lỗi 429/503 từ nhà cung cấp LLM (tối đa 2 lần retry).
- Cơ chế Fallback sang Lập kế hoạch Thủ công (`FR-PLAN-004`) khi AI mất kết nối hoặc schema lỗi sau retry.

### 8.4 Lịch Trình Tác vụ Nền Định kỳ (Celery Beat Schedule Catalog)
Hệ thống vận hành 4 tác vụ định kỳ chính thức qua Celery Beat:
1. `check_abandoned_sessions`: Chạy định kỳ mỗi 5 phút (300s), quét các phiên học `IN_PROGRESS` ngừng gửi heartbeat > 5 phút để chốt trạng thái theo `OS-01`.
2. `scan_daily_overdue_tasks`: Chạy lúc 00:01 hàng ngày, quét thống kê tác vụ quá hạn theo công thức tất định `BUSR-06` phục vụ thông báo tổng hợp.
3. `generate_weekly_ai_reviews`: Chạy lúc 23:59 Chủ Nhật hàng tuần, tổng hợp chỉ số học tập tuần và kích hoạt AI Review lưu vào bảng `ai_reviews` (`FR-AI-004`).
4. `refresh_ai_quotas`: Chạy lúc 00:00 ngày đầu tiên mỗi tháng, làm mới chu kỳ hạn ngạch AI cho toàn bộ người dùng (`OS-02`).

---

## 9. Các Quyết định Kiến trúc Cốt lõi (Architecture Decisions - ADRs)

Dự án FocusFlow quản trị kiến trúc thông qua 8 bản ghi quyết định kiến trúc chính thức:

| Mã ADR | Tiêu đề Quyết định | Tóm tắt Quyết định & Luận cứ Kỹ thuật |
|---|---|---|
| **ADR-001** | Phong cách Kiến trúc Phân tầng | Lựa chọn **Modular Monolith kết hợp Kiến trúc Lục giác (Hexagonal Architecture)**. Bảo vệ Domain độc lập, tối ưu hóa nguồn lực 2 sinh viên, loại bỏ rủi ro vận hành phân tán của Microservices. |
| **ADR-002** | Ngăn xếp Công nghệ Backend | Lựa chọn **Python 3.12 + FastAPI + Pydantic v2 + SQLAlchemy 2.0 Async**. Tận dụng tối đa hệ sinh thái AI, xác thực schema bằng Rust core, hiệu năng I/O bất đồng bộ cao. |
| **ADR-003** | Ngăn xếp Công nghệ Frontend | Lựa chọn **Next.js 15 (App Router) + TypeScript + Tailwind CSS + Shadcn UI**. Phân tách Server/Client Components, quản trị state tách bạch bằng TanStack Query và Zustand. |
| **ADR-004** | Xử lý Tác vụ Nền & Định kỳ | Lựa chọn **Celery 5.6 + Redis 7 + Celery Beat**. Tách biệt các tác vụ quét timeout phiên học, tính toán báo cáo tuần ra khỏi vòng đời HTTP Request. |
| **ADR-005** | Giao thức Luồng Dữ liệu AI | Lựa chọn **Server-Sent Events (SSE)** hai chặng đồng nhất chuẩn RESTful. Phản hồi mượt mà không treo UI, giải quyết triệt để lỗi trừ quota lặp khi reconnect. |
| **ADR-006** | Chiến lược Triển khai Hệ thống | Lựa chọn **Mô hình Hybrid**: Docker Compose Local (phục vụ bảo vệ đồ án offline) và Cloud PaaS (Vercel + Render Paid + Managed DB phục vụ UAT). |
| **ADR-007** | Thiết kế CSDL Quan hệ & Toàn vẹn ACID | Lựa chọn **PostgreSQL 16 + Khóa chính UUIDv7 (RFC 9562)** tối ưu chỉ mục B-Tree, chuẩn hóa 3NF/BCNF, khóa ngoại kép ngăn ngừa lệch lộ trình và phòng thủ đa tầng. |
| **ADR-008** | Kiến trúc Bảo mật Đa tầng & Xác thực | Lựa chọn **Cookie JWT HttpOnly SameSite**, băm mật khẩu Argon2id, WebCal token SHA-256, che giấu log nhạy cảm và quản lý Refresh Token Rotation (RTR) trên Redis. |

---

## 10. Yêu cầu Chất lượng (Quality Requirements)

Hệ thống được ánh xạ chặt chẽ theo tiêu chuẩn chất lượng ISO/IEC 25010:

```
+─────────────────────────────────────────────────────────────────────────────+
|               MA TRẬN ÁNH XẠ THUỘC TÍNH CHẤT LƯỢNG ISO/IEC 25010            |
+──────────────────────────┬──────────────────────────┬───────────────────────+
| Thuộc tính Chất lượng     | Chỉ số Định lượng (SRS)  | Giải pháp Kiến trúc   |
+──────────────────────────┼──────────────────────────┼───────────────────────+
| Performance Efficiency   | API latency <= 200ms;    | FastAPI asyncpg,      |
|                          | AI streaming timeout 55s | B-Tree partial index, |
|                          | (NFR-PERF-001..002)      | SSE protocol          |
+──────────────────────────┼──────────────────────────┼───────────────────────+
| Security & Privacy       | 0 rò rỉ secret;          | Argon2id hashing,     |
|                          | HttpOnly SameSite cookie | SHA-256 WebCal token, |
|                          | (NFR-SEC-001..004)       | LogSanitizer, PII filter|
+──────────────────────────┼──────────────────────────┼───────────────────────+
| Reliability              | Uptime >= 95% UAT;       | Celery Heartbeat sweep|
|                          | Bảo toàn phút thực học   | (OS-07), Transaction  |
|                          | (NFR-AVAIL-001, OS-01)   | ACID trong PostgreSQL |
+──────────────────────────┼──────────────────────────┼───────────────────────+
| Usability & A11y         | Lighthouse Score >= 90;  | Shadcn UI (Radix UI), |
|                          | Responsive Desktop/Mobile| Zustand Workspace,    |
|                          | (NFR-UX-001..002)        | Dark/Light Theme      |
+──────────────────────────┼──────────────────────────┼───────────────────────+
| Maintainability          | Kiểm thử độc lập 100%    | Hexagonal Architecture|
|                          | nghiệp vụ lõi (Domain)   | Ports & Adapters,     |
|                          |                          | Strict Type Hinting   |
+──────────────────────────┴──────────────────────────┴───────────────────────+
```

---

## 11. Rủi ro & Nợ Kỹ thuật (Risks and Technical Debt)

| Mã Rủi ro / Nợ | Mô tả Vấn đề | Tác động Tiềm ẩn | Chiến lược Giảm thiểu & Khắc phục |
|---|---|---|---|
| **RSK-01** | Độ trễ biến thiên của dịch vụ AI ngoài (Google Gemini API). | Có thể vượt quá thời gian người dùng chờ đợi nếu mạng quốc tế chập chờn. | Thiết lập Hard Timeout 55s; cung cấp thanh tiến trình SSE hiển thị trạng thái sinh; hỗ trợ nút chuyển sang chế độ lập kế hoạch thủ công (`FR-PLAN-004`). |
| **RSK-02** | Giới hạn Render Free Tier (tự ngủ sau 15 phút, CSDL hết hạn). | Gây cold start 50s làm hỏng chỉ số UAT của người dùng thật. | **Đã giải quyết:** Sử dụng Render Paid Web Service hoặc máy chủ Cloud VPS Docker Compose ($5/tháng) trong 2 tuần diễn ra đợt nghiệm thu UAT. |
| **RSK-03** | Khác biệt định nghĩa giữa derived query và cron job đối với Task quá hạn. | `celery_app.py` hiện khai báo mock task `scan_overdue_tasks` hàng ngày trong khi SRS định nghĩa Overdue là derived condition. | Thống nhất: Truy vấn trạng thái hiển thị động trên UI theo công thức `scheduled_date < CURRENT_DATE`; task Celery chỉ phục vụ việc gom nhóm gửi email/báo cáo tổng kết tuần (không đổi enum status thừa trong DB). |

---

## 12. Thuật ngữ Chuẩn hóa (Glossary)

| Thuật ngữ | Khái niệm & Ranh giới Kỹ thuật trong Hệ thống FocusFlow |
|---|---|
| **Goal** | Mục tiêu học tập ban đầu do Learner nhập vào hệ thống, là đầu vào cho quy trình AI làm rõ và phân rã. |
| **Roadmap** | Lộ trình học tập tổng thể của một Goal, gồm danh sách Milestones và các nhiệm vụ tương ứng (`INITIALIZED`, `ACTIVE`, `PAUSED`, `COMPLETED`). |
| **Milestone** | Cột mốc kiến thức trung gian Cấp 1 (gồm 3–7 mốc tuần tự trong một lộ trình). |
| **Task** | Nhiệm vụ học tập cụ thể Cấp 2 có thời lượng dự tính (15–240 phút) và trạng thái vòng đời (`PENDING`, `COMPLETED`). |
| **Schedule Proposal** | Bản đề xuất lịch học dự thảo (`DRAFT`) do AI sinh ra, chưa ghi vào lịch chính thức và người học có toàn quyền chỉnh sửa. |
| **Official Schedule** | Lịch học chính thức đã vượt qua Backend Validation Gate (Hard Ceiling) sau khi người dùng chủ động bấm "Apply"; nguồn chân lý duy nhất để xuất WebCal. |
| **Study Workspace** | Không gian thực thi phiên học tập trung, tích hợp Task Checklist, Timer Pomodoro/Stopwatch, Scratchpad và Key Takeaways. |
| **Domino Shift** | Thuật toán tất định tịnh tiến toàn bộ các task chưa học lùi về sau đúng bằng số ngày khả dụng khi tạm dừng lộ trình (`BUSR-07`). |
| **Hard Ceiling** | Quy tắc chặn cứng không cho phép tổng giờ học trong ngày vượt quá quỹ thời gian rảnh đã khai báo trong Availability Mode A. |
| **Soft Overflow** | Cơ chế cảnh báo cho phép khung giờ học tràn ra ngoài biên tối đa $\le 30$ phút trong Availability Mode B. |
| **WebCal** | Giao thức đồng bộ lịch 1 chiều an toàn theo chuẩn RFC 5545 thông qua URL bí mật định dạng `.ics`. |
| **Mock Sandbox** | Môi trường giả lập nâng cấp gói tài khoản để thử nghiệm tính năng nới rộng hạn ngạch Quota mà không tích hợp cổng thanh toán thực tế. |
