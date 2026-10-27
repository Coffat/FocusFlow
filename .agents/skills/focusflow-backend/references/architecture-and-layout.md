# Kiến trúc & bố cục thư mục (Backend)

Mục lục: 1. Cây thư mục · 2. Hợp đồng import-linter · 3. Public API giữa context · 4. Composition Root · 5. Quyền sở hữu context · 6. Sự kiện miền liên context

## 1. Cây thư mục chuẩn

```
backend/
  pyproject.toml                  # ruff, mypy --strict, import-linter, pytest
  alembic/versions/
  scripts/dump_schema.sh          # pg_dump --schema-only --no-owner --no-privileges
  src/
    shared_kernel/
      domain/                     # DomainEvent base, Clock, errors, ids (uuid7)
      application/                # AsyncUnitOfWork (Protocol), EventBus, LLMProviderPort, EmailNotificationPort...
      infrastructure/
        db/                       # engine, session factory, SqlAlchemyUnitOfWork, OutboxEventORM, ProcessedEventORM
        external_ai/              # LiteLLMAdapter / OpenAICompatibleAdapter / MockLLMAdapter / CircuitBreaker wrapper
        worker/                   # RedisStreamBroker, TaskiqScheduler, outbox relay task
      config.py                   # pydantic-settings
      logging.py                  # structlog + sanitize_sensitive_data_processor
    account|planning|execution|evaluation/
      domain/                     # entities, aggregates, value objects, domain services, domain events
      application/
        use_cases/                # 1 file / use case; command & query
        ports/                    # repository + external Protocols
        dto.py
      infrastructure/
        orm/                      # SQLAlchemy models (không relationship() sang context khác)
        repositories/             # Data Mapper: ORM <-> domain
        adapters/                 # LLM judge, payment, calendar, smtp...
        tasks/                    # Taskiq task (mỏng, chỉ gọi use case)
      presentation/
        routers.py  schemas.py  deps.py   # deps.py = Composition Root
      public_api.py               # Query Ports + DTO bất biến xuất bản cho context khác
    main.py                       # tạo FastAPI app, gắn router, middleware (correlation_id, exception handlers)
  tests/
    unit/<context>/               # domain + use case (fake ports), không DB/Redis/LLM
    integration/<context>/        # PostgreSQL thật (testcontainers hoặc compose), InMemoryBroker cho Taskiq
    security/                     # IDOR, RBAC, webhook signature/replay
    ai_evals/                     # harness JSONL 100+ kịch bản, chạy qua LLMProviderPort
```

Nếu repo thực tế đặt tên khác (ví dụ `modules/`), **theo repo**; quy tắc không đổi.

## 2. Hợp đồng import-linter (trong `pyproject.toml`)

```toml
[tool.importlinter]
root_packages = ["src"]

[[tool.importlinter.contracts]]
name = "Context isolation"
type = "forbidden"
# Với mỗi cặp context A->B: source = A (trừ public_api), forbidden = B (trừ public_api & shared_kernel)
source_modules = ["src.account", "src.planning", "src.execution", "src.evaluation"]
forbidden_modules = ["src.account", "src.planning", "src.execution", "src.evaluation"]
allow_indirect_imports = true
# Thực tế cấu hình theo từng cặp + ignore_imports = ["src.*.*->src.*.public_api"]

[[tool.importlinter.contracts]]
name = "Hexagonal layers (per context)"
type = "layers"
layers = ["presentation", "infrastructure", "application", "domain"]
containers = ["src.account", "src.planning", "src.execution", "src.evaluation"]

[[tool.importlinter.contracts]]
name = "Domain purity"
type = "forbidden"
source_modules = ["src.account.domain", "src.planning.domain", "src.execution.domain", "src.evaluation.domain"]
forbidden_modules = ["fastapi", "starlette", "sqlalchemy", "taskiq", "redis", "litellm"]

[[tool.importlinter.contracts]]
name = "Application purity"
type = "forbidden"
source_modules = ["src.account.application", "src.planning.application", "src.execution.application", "src.evaluation.application"]
forbidden_modules = ["fastapi", "starlette", "sqlalchemy", "taskiq"]
```
Khi thêm context/package, cập nhật hợp đồng cùng commit. Đừng "sửa" lỗi lint bằng cách thêm `ignore_imports` — sửa thiết kế (thêm Query Port / event).

## 3. Public API giữa các context

`src/<ctx>/public_api.py` chỉ chứa: `Protocol` truy vấn **chỉ đọc** + DTO bất biến (`@dataclass(frozen=True)`), và (nếu cần) factory trả về implementation đã nối dây ở composition root.

Luồng đọc liên context hiện có (không thêm ngoại lệ):
- `planning` → `account`: `AvailabilityQueryPort` (cấu hình Mode A/B, slot), `QuotaPort` (reserve/commit/release).
- `planning` → `execution`: `StudyExecutionQueryPort` (đồ thị task/dependency để `DagCycleValidator` kiểm).
- `account` → `execution`: `StudyExecutionQueryPort` (thống kê phiên cho Learner Profile Aggregator).
- `evaluation` → `execution`/`planning`: truy vấn task quá hạn, lịch hiện hành qua public_api tương ứng.

Nguyên tắc: public_api nhỏ, ổn định, trả DTO (không trả entity/ORM). Thêm method mới ⇒ thêm DTO + test.

Chú ý domain service nằm ở context sở hữu dữ liệu nhưng được `planning` gọi trong gate: `planning` **không** import `account.domain`; nó gọi qua port do `account.public_api` xuất bản (port nhận DTO lịch đề xuất, trả `list[ConstraintViolationDTO]`) hoặc nhận một implementation tiêm vào ở composition root.

## 4. Composition Root (`presentation/deps.py`)

- Đây là nơi duy nhất dùng `Depends`/`TaskiqDepends`, đọc `settings`, chọn adapter theo env (`LLM_PROVIDER`, `PAYMENT_PROVIDER`, `CALENDAR_PROVIDER`), tạo `SqlAlchemyUnitOfWork`, lắp use case.
- Một hàm factory cho mỗi use case: `def get_apply_proposal_uc(uow=Depends(get_uow), ...) -> ApplyScheduleProposalUseCase`.
- Task Taskiq dùng cùng factory (qua `TaskiqDepends`) ⇒ không nhân bản logic lắp ráp.
- Chọn adapter: `match settings.llm_provider: case "mock": MockLLMAdapter() ...`. Thêm nhà cung cấp mới = thêm nhánh ở đây + adapter, **không** sửa application.

## 5. Quyền sở hữu context (tóm tắt)

| Context | Aggregate Root | Domain Service thuần |
|---|---|---|
| account | `User`, `AvailabilityProfile`, `AIQuota` (+ `LearnerProfile`, `PaymentTransaction`, `WebCalToken`) | `HybridAvailabilityRuleEngine` |
| planning | `Roadmap` (+ Goal, Milestone), `OfficialSchedule`, `ScheduleProposal` | `ProposalValidationGateOrchestrator` ở tầng application (điều phối 3 tier) |
| execution | `Task`, `StudySession` | `DagCycleValidator` |
| evaluation | `PauseRecord`, `AIReview` | `DominoShiftEngine` |

## 6. Sự kiện miền liên context (đã định nghĩa)

| Event | Phát bởi | Tiêu thụ bởi | Mục đích |
|---|---|---|---|
| `StudySessionCompletedEvent` | execution (kể cả sweeper chốt phiên `PARTIAL_COMPLETED`) | account (`UpdateLearnerProfileOnSessionCompletedHandler`) | cập nhật `learner_profiles` (D_opt, β_bias, peak slots) |
| `UserUpgradedToPremiumEvent` | account (webhook thanh toán) | account/others | nâng quota, mở trần lộ trình |
| `OfficialScheduleAppliedEvent` | planning | execution (đồng bộ lịch ngoại vi), evaluation | outbound calendar sync, ghi `schedule_change_logs` |
| `TaskStalledThresholdReachedEvent` | execution/evaluation | UI/notification | kích hoạt dialog can thiệp `STALLED` |

Event mới: định nghĩa ở `domain/events.py` của context phát; payload chỉ chứa ID + dữ liệu tối thiểu (consumer tự truy vấn trạng thái mới nhất); có `event_id` (uuid7), `occurred_at`, `schema_version`.
