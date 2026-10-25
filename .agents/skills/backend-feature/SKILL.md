---
name: backend-feature
description: Step-by-step guide to implement a backend feature following Context-First Modular Monolith and Hexagonal Architecture. Use when creating new API endpoints, domain logic, use cases, Taskiq background tasks, or repository adapters in the FastAPI backend.
---

# Backend Feature Implementation (Context-First Modular Monolith + Hexagonal)

Implements a backend feature inside one of the 4 Bounded Contexts (`account`, `planning`, `execution`, `evaluation`) across all hexagonal layers. Follow this exact order.

## Pre-flight

1. Identify the FR/UC requirement being implemented (`UC-01`..`UC-19`) and determine the owning Bounded Context (`account` | `planning` | `execution` | `evaluation`).
2. Check if cross-context data is needed:
   - Synchronous read -> import Query Port / DTO from `src.<other_context>.public_api`.
   - Asynchronous side-effect -> emit a `DomainEvent` via `AggregateRoot.add_domain_event()` and persist through `AsyncUnitOfWork` (`outbox_events`).
3. Read `references/hexagonal-flow.md` for layer-specific conventions.

## Implementation Order (Inside `backend/src/{context}/`)

### 1. Domain Layer (`backend/src/{context}/domain/`)

- Create/update Aggregate Root or Entity in `domain/models/` inheriting from `src.shared_kernel.domain.base.{AggregateRoot, Entity, ValueObject}` (pure Python `@dataclass`, UUIDv7, zero framework imports).
- Add Domain Events in `domain/events/` (or `public_api.py` if consumed across contexts).
- Add Domain Exceptions in `domain/exceptions/` inheriting from `src.shared_kernel.domain.exceptions.DomainError`.
- Add pure Domain Services in `domain/services/` (e.g., `HybridAvailabilityRuleEngine`, `DagCycleValidator`, `DominoShiftEngine`).

### 2. Ports (`backend/src/{context}/application/ports/` & `public_api.py`)

- Define repository and external adapter output ports as `typing.Protocol` in `application/ports/`.
- If exposing a read-only query interface to other Bounded Contexts, define the `Protocol` and immutable DTO in `backend/src/{context}/public_api.py`.

### 3. Application Layer (`backend/src/{context}/application/`)

- Create input/output DTOs in `application/dtos/`.
- Create Use Case in `application/use_cases/`:
  - Inject `AsyncUnitOfWork` (`src.shared_kernel.application.uow`) and context ports.
  - Call `uow.collect_events_from(aggregate)` before `await uow.commit()` so Domain Events are atomically written to `outbox_events`.

### 4. Infrastructure Layer (`backend/src/{context}/infrastructure/`)

- Create/update SQLAlchemy 2.0 `Mapped[]` ORM models in `infrastructure/orm/` inheriting from `src.shared_kernel.infrastructure.database.session.Base`.
- Implement repository adapters in `infrastructure/repositories/` mapping ORM <-> Domain models.
- Implement external adapters in `infrastructure/adapters/` (e.g., `PayOSAdapter`, `GoogleCalendarOAuthAdapter`, `PedagogicalJudgeAdapter`).
- If DB schema changed -> apply skill `db-change`.

### 5. Presentation Layer (`backend/src/{context}/presentation/`)

- Define Pydantic v2 request/response schemas in `presentation/schemas/`.
- Add FastAPI route handlers in `presentation/routers.py` and register in `backend/src/main.py`.
- Wire dependencies in `presentation/deps.py`.
- Add async background tasks or cron sweepers in `presentation/tasks.py` using `@broker.task` from `src.shared_kernel.infrastructure.worker.broker`.
- If API contract changed -> apply skill `api-contract`.

### 6. Tests (`backend/tests/`)

- Unit test pure domain models & domain services (`tests/unit/{context}/`).
- Unit test use cases with mocked ports (`tests/unit/{context}/`).
- Integration test repositories and FastAPI endpoints (`tests/integration/{context}/`).

## Verification

- Run `cd backend && uv run pytest -q`
- Run `cd backend && uv run lint-imports` (skill `arch-guard`) to verify zero boundary violations.
