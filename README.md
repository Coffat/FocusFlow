# FocusFlow — Hệ thống Lập kế hoạch & Quản lý Học tập Cá nhân hóa Ứng dụng AI

![Angular 21+](https://img.shields.io/badge/Frontend-Angular_21%2B_(Zoneless_Signals)-DD0031?logo=angular)
![PrimeNG v21](https://img.shields.io/badge/UI-PrimeNG_v21_%2B_Tailwind_v4-06B6D4?logo=tailwindcss)
![FastAPI](https://img.shields.io/badge/Backend-FastAPI_%2B_Python_3.12-009688?logo=fastapi)
![SQLAlchemy 2.0](https://img.shields.io/badge/ORM-SQLAlchemy_2.0_Async-D71F00)
![Taskiq](https://img.shields.io/badge/Worker-Taskiq_%2B_Redis_Streams-DC382D?logo=redis)
![PostgreSQL 16](https://img.shields.io/badge/Database-PostgreSQL_16_(24_Tables_3NF%2FBCNF)-4169E1?logo=postgresql)
![LiteLLM](https://img.shields.io/badge/AI-Provider--Agnostic_(LiteLLM)-8A2BE2)
![Architecture](https://img.shields.io/badge/Architecture-Context--First_Modular_Monolith_%2B_Hexagonal-2E8B57)

Đồ án Tốt nghiệp Đại học ngành Công nghệ Thông tin — Khoa CNTT, Trường Đại học Sư phạm Kỹ thuật TP.HCM (HCMUTE).

* **Sinh viên thực hiện:**
  * Vũ Toàn Thắng
  * Phan Đình Duẩn
* **Giảng viên Hướng dẫn:** ThS. Vũ Đình Bảo

---

## 1. Tổng quan Hệ thống & Điểm nhấn Kiến trúc (Architecture Highlights v2.0)

**FocusFlow** là hệ thống Lập kế hoạch & Quản lý Học tập Cá nhân hóa ứng dụng AI (AI-Powered Personalized Study Planning & Execution System), kết hợp **Lý thuyết Học tập Tự điều chỉnh của Zimmerman (SRL)** (*Forethought → Performance → Self-Reflection*) với **Giải thuật Lập lịch Tất định (Deterministic Scheduling)** và **Mô hình Ngôn ngữ Lớn Đa nhà cung cấp (Provider-Agnostic LLM)**.

### Điểm nhấn Kiến trúc & Kỹ thuật Phần mềm:
1. **Context-First Modular Monolith + Hexagonal Architecture (Ports & Adapters):**
   - Phân rã thành **4 Bounded Contexts độc lập** (`account`, `planning`, `execution`, `evaluation`) và **`shared_kernel`**.
   - Mỗi Context tự đóng gói 4 tầng (`domain`, `application`, `infrastructure`, `presentation`) và chỉ giao tiếp qua `public_api.py` (Read-only Query Ports) hoặc **Transactional Outbox (`outbox_events` & `processed_events`)**.
   - Kiểm soát ranh giới tự động bằng **`import-linter`** trong CI/CD.
2. **3-Tier Hybrid Validation Gate & Provider-Agnostic AI:**
   - Trừu tượng hóa qua `LLMProviderPort` (`LiteLLM` / OpenAI-compatible SDK + `MockLLMAdapter`), hỗ trợ chuyển đổi giữa **Google Gemini, OpenAI, Anthropic Claude, Local Ollama** chỉ qua `.env`.
   - Cổng kiểm duyệt 3 tầng: `Pydantic v2 Schema` $\to$ Pure Domain Rule Engines (`HybridAvailabilityRuleEngine`, `DagCycleValidator`) $\to$ `PedagogicalJudgeAdapter` (kèm tối đa 2 vòng tự sửa lỗi).
3. **2-Phase ACID Quota Reservation & Uniform 2-Stage SSE Streaming:**
   - Giữ chỗ hạn ngạch 2 pha ACID (`ai_quotas` + `ai_quota_reservations`) kết hợp giao thức SSE 2 chặng (`POST` khởi tạo $\to$ `GET` `EventSource` stream), chống mất lượt gọi AI khi gián đoạn mạng.
4. **Taskiq + Redis 7 Streams & Transactional Outbox:**
   - Xử lý tác vụ nền thuần `async/await` với `RedisStreamBroker` (`XREADGROUP`/`XACK`), `TaskiqScheduler` (`replicas: 1`) và `taskiq-fastapi`.
5. **PostgreSQL 16 — 24 Bảng Chuẩn hóa 3NF/BCNF:**
   - Thiết kế **24 bảng vật lý chuẩn 3NF/BCNF** với khóa chính **UUIDv7**, bảo toàn khóa ngoại đơn ở mức DB nhưng cấm ORM JOIN chéo Context.

---

## 2. Ngăn xếp Công nghệ (Tech Stack)

| Phân tầng | Công nghệ & Thư viện Chủ đạo | Vai trò trong Hệ thống |
| :--- | :--- | :--- |
| **Frontend SPA** | **Angular 21+** (Zoneless, Standalone, `OnPush`, Signals / `rxResource`), **Tailwind CSS v4**, **PrimeNG v21**, **Lucide Icons**, `openapi-typescript`, Vitest, Playwright | Giao diện phản ứng tức thời không cần `zone.js`, đồng bộ kiểu 100% với OpenAPI 3.1. |
| **Backend API** | **Python 3.12**, **FastAPI**, **Pydantic v2**, **SQLAlchemy 2.0 Async (`asyncpg`)**, **Alembic**, `structlog`, **`import-linter`** | Modular Monolith 4 Bounded Contexts + Hexagonal Architecture, kiểm soát ranh giới tự động. |
| **Async Worker & Scheduler** | **Taskiq**, **`taskiq-redis` (`RedisStreamBroker`)**, **`TaskiqScheduler` (`replicas: 1`)**, **`taskiq-fastapi`** | Thực thi Outbox Relay, quét phiên treo 60s, thu hồi Quota treo, tổng hợp hồ sơ SRL và đồng bộ lịch. |
| **Database & Broker** | **PostgreSQL 16** (24 bảng 3NF/BCNF, UUIDv7), **Redis 7 Alpine** (`appendonly yes` AOF + Streams) | Lưu trữ giao dịch ACID, Transactional Outbox, Message Broker và Refresh Token Rotation. |
| **AI & External Adapters** | **`LiteLLM`** / OpenAI SDK (`LLMProviderPort`), **PayOS / VNPay Sandbox** (`PaymentGatewayPort` + `HMAC-SHA256`), **Google Calendar OAuth2 & WebCal RFC 5545** (`CalendarSyncPort`) | Đa nhà cung cấp AI, thanh toán QR/Webhook và đồng bộ lịch 2 chiều / 1 chiều (kèm Mock Adapters chạy offline). |
| **Security** | **`PyJWT`** (`HttpOnly` Cookie), **`pwdlib[argon2]`** (Argon2id), **Fernet** (`cryptography`), **SHA-256**, **HMAC-SHA256** | Bảo mật xác thực, mã hóa OAuth token, chống giả mạo Webhook và lọc sạch PII khỏi log/prompt. |

---

## 3. Cấu trúc Dự án (Project Structure)

```text
FocusFlow/
├── backend/                              # Backend FastAPI (Python 3.12, Context-First Modular Monolith, uv)
│   ├── src/
│   │   ├── main.py                       # FastAPI Entrypoint, Middlewares, Routers & Taskiq Wiring
│   │   ├── shared_kernel/                # Shared Kernel (AsyncUnitOfWork, Outbox, Taskiq Broker, LLMProviderPort)
│   │   ├── account/                      # BC 1: Auth, LearnerProfile, Hybrid Availability, ACID Quota, Billing (9 bảng)
│   │   │   ├── domain/                   # Rich Models & HybridAvailabilityRuleEngine
│   │   │   ├── application/              # Use Cases (UC-01..UC-05, UC-18) & Ports
│   │   │   ├── infrastructure/           # Repositories (availabilities + availability_slots), PayOS, Security Adapters
│   │   │   ├── presentation/             # FastAPI Routers & Taskiq Tasks
│   │   │   └── public_api.py             # Cross-Context Read Query Facade
│   │   ├── planning/                     # BC 2: Goal, Roadmap, Milestone, Task DAG & 3-Tier Validation Gate (7 bảng)
│   │   │   ├── domain/                   # Rich Models & DagCycleValidator
│   │   │   ├── application/              # Use Cases (UC-06..UC-09) & ValidationGateOrchestrator
│   │   │   ├── infrastructure/           # Repositories & PedagogicalJudgeAdapter
│   │   │   ├── presentation/             # FastAPI Routers
│   │   │   └── public_api.py             # Roadmap/Task Query Facade
│   │   ├── execution/                    # BC 3: Study Session, Pomodoro Heartbeat & Calendar Sync (4 bảng)
│   │   │   ├── domain/                   # StudySession, SessionTask, StudyNote, PauseRecord
│   │   │   ├── application/              # Use Cases (UC-10..UC-13) & CalendarSyncPort
│   │   │   ├── infrastructure/           # Repositories, GoogleCalendarOAuthAdapter & IcsFeedGenerator
│   │   │   ├── presentation/             # FastAPI Routers & Taskiq Tasks
│   │   │   └── public_api.py             # Execution Query Facade
│   │   └── evaluation/                   # BC 4: SRL Analytics, AI Review & Domino Shift Adaptation (2 bảng)
│   │       ├── domain/                   # AIReview, ScheduleChangeLog & DominoShiftEngine
│   │       ├── application/              # Use Cases (UC-14..UC-17, UC-19)
│   │       ├── infrastructure/           # Repositories
│   │       ├── presentation/             # FastAPI Routers & Taskiq Tasks
│   │       └── public_api.py             # Evaluation Metrics Query Facade
│   ├── tests/                            # Unit, Integration & Architectural Fitness Tests
│   ├── pyproject.toml                    # Cấu hình uv, pytest, ruff & import-linter contracts
│   └── Dockerfile                        # Multi-stage build với Astral uv
│
├── frontend/                             # Frontend Angular 21+ (Zoneless Signals, Tailwind v4, PrimeNG v21, pnpm)
│   ├── src/app/
│   │   ├── core/                         # AuthService, WorkspaceSessionService, AiSseStreamingService, OpenAPI Types
│   │   ├── shared/                       # PrimeNG v21 + Tailwind v4 + Lucide UI Components
│   │   └── features/                     # 9 Feature Modules (auth, dashboard, roadmaps, workspace, schedule, tasks, analytics, settings, admin)
│   ├── package.json                      # Quản lý phụ thuộc với pnpm
│   └── Dockerfile                        # Multi-stage build (Node build -> Nginx Alpine)
│
├── docs/                                 # Hồ sơ Thiết kế & Kỹ thuật chuẩn mực (ISO 29148, UML 2.5.1, arc42, C4)
│   ├── requirements/                     # Bài toán thực tế, Chân dung người dùng & 5 KPIs
│   ├── srs/                              # Đặc tả yêu cầu phần mềm SRS v1.1 & 19 Use Cases
│   ├── uml/                              # Use Case, Activity, Sequence, State Machine & Class Diagrams v4.2
│   ├── architecture/                     # Kiến trúc Hệ thống arc42 v2.0, C4 Model v2.0 & Technical Specs
│   ├── database/                         # Thiết kế CSDL 24 bảng 3NF/BCNF, PostgreSQL 16 DDL & Từ điển dữ liệu
│   ├── decisions/                        # Bộ 10 Architecture Decision Records (ADR-001 đến ADR-010) chuẩn MADR
│   └── engineering/                      # Báo cáo kiểm toán tính nhất quán chéo
│
├── docs_ute/                             # Hồ sơ Báo cáo tiến độ tuần & Tài liệu môn học nộp GVHD
├── docker-compose.yml                    # Khởi chạy 6 Containers (frontend, backend, worker, scheduler, postgres, redis)
├── .env.example                          # Biến môi trường mẫu (Provider-Agnostic LLM, DB, Redis, Security)
└── AGENTS.md                             # Quy chuẩn công nghệ và triết lý kỹ thuật hệ thống
```

---

## 4. Danh mục Tài liệu Kiến trúc & 10 Quyết định Kiến trúc (ADRs)

### Tài liệu Kiến trúc & Thiết kế Cốt lõi:
- [Tài liệu Kiến trúc Hệ thống (arc42 v2.0)](file:///Users/vuthang/Documents/FocusFlow/docs/architecture/system-architecture.md)
- [Mô hình Kiến trúc C4 & Biểu đồ Thành phần (C4 Model v2.0)](file:///Users/vuthang/Documents/FocusFlow/docs/architecture/c4-model-components.md)
- [Đặc tả Kỹ thuật Phân hệ Thời gian Rảnh Lai (`FR-AVAIL`)](file:///Users/vuthang/Documents/FocusFlow/docs/architecture/technical-spec-fr-avail-hybrid-availability.md)
- [Thiết kế Cơ sở Dữ liệu Quan hệ 24 Bảng 3NF/BCNF](file:///Users/vuthang/Documents/FocusFlow/docs/database/database-schema-design.md) & [DDL `schema.sql`](file:///Users/vuthang/Documents/FocusFlow/docs/database/schema.sql)

### Bộ 10 Bản ghi Quyết định Kiến trúc (`docs/decisions/`):
1. [**ADR-001**](file:///Users/vuthang/Documents/FocusFlow/docs/decisions/ADR-001-architectural-style.md): Phong cách Kiến trúc — Context-First Modular Monolith & Hexagonal Architecture
2. [**ADR-002**](file:///Users/vuthang/Documents/FocusFlow/docs/decisions/ADR-002-backend-tech-stack.md): Ngăn xếp Công nghệ Backend & Provider-Agnostic AI (`LiteLLM` / `LLMProviderPort`)
3. [**ADR-003**](file:///Users/vuthang/Documents/FocusFlow/docs/decisions/ADR-003-frontend-tech-stack.md): Ngăn xếp Công nghệ Frontend — Angular 21+ Zoneless Signals, PrimeNG v21 & Tailwind CSS v4
4. [**ADR-004**](file:///Users/vuthang/Documents/FocusFlow/docs/decisions/ADR-004-worker-and-scheduled-jobs.md): Xử lý Tác vụ Nền & Lập lịch — Taskiq, Redis 7 Streams & Transactional Outbox
5. [**ADR-005**](file:///Users/vuthang/Documents/FocusFlow/docs/decisions/ADR-005-ai-streaming-protocol.md): Giao thức Streaming AI (Uniform 2-Stage SSE) & Quản trị Hạn ngạch ACID 2 Pha
6. [**ADR-006**](file:///Users/vuthang/Documents/FocusFlow/docs/decisions/ADR-006-deployment-strategy.md): Chiến lược Triển khai Hybrid 6 Containers (Local Docker Compose & Cloud PaaS)
7. [**ADR-007**](file:///Users/vuthang/Documents/FocusFlow/docs/decisions/ADR-007-database-schema-and-persistence.md): Thiết kế CSDL Quan hệ 24 Bảng 3NF/BCNF, UUIDv7 & Toàn vẹn ACID trên PostgreSQL 16
8. [**ADR-008**](file:///Users/vuthang/Documents/FocusFlow/docs/decisions/ADR-008-security-architecture-and-tokens.md): Kiến trúc Bảo mật Đa tầng (`PyJWT`, Argon2id, Fernet, `HMAC-SHA256`, SHA-256 WebCal, PII Sanitizer)
9. [**ADR-009**](file:///Users/vuthang/Documents/FocusFlow/docs/decisions/ADR-009-ai-constraint-validation-and-evaluation-harness.md): Cổng Kiểm duyệt Ràng buộc AI 3 Tầng (3-Tier Hybrid Validation Gate)
10. [**ADR-010**](file:///Users/vuthang/Documents/FocusFlow/docs/decisions/ADR-010-learner-profile-memory-and-anti-loop.md): Bộ nhớ Hồ sơ Người học Zimmerman SRL & Cơ chế Chống lặp Quá hạn (Anti-Loop Escalation)

---

## 5. Khởi chạy Nhanh với Docker Compose (Quickstart)

```bash
# 1. Sao chép cấu hình môi trường
cp .env.example .env

# 2. Khởi động toàn bộ 6 vùng chứa dịch vụ (frontend, backend, worker, scheduler, postgres, redis)
docker compose up -d --build

# 3. Truy cập các cổng dịch vụ:
# - Giao diện người dùng (Angular 21+ SPA): http://localhost:3000
# - Tài liệu OpenAPI 3.1 (FastAPI Backend): http://localhost:8000/docs
# - Kiểm tra Health Check API:              http://localhost:8000/api/health
```
