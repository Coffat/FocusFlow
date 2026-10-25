# Hexagonal Architecture — Layer Details

## Directory Map

```
backend/src/
  domain/
    models/          # Pure Python dataclasses — business entities & value objects
    services/        # Domain services — complex business logic spanning entities
    exceptions/      # Domain-specific exceptions (BusinessRuleViolation, etc.)
  application/
    dtos/            # Command/Query DTOs — plain dataclasses, no Pydantic
    ports/
      input/         # Driving ports (use case interfaces)
      output/        # Driven ports (repository/external service protocols)
    use_cases/       # Application services — orchestrate domain + ports
  infrastructure/
    database/        # ORM models, repositories, session factory, migrations
    caching/         # Redis adapters
    calendar/        # iCalendar integration adapters
    external_ai/     # Gemini AI provider adapters
    workers/         # Celery task definitions
  presentation/
    api/
      routes/        # FastAPI routers
      schemas/       # Pydantic request/response models
    middlewares/     # CORS, auth, error handling
    main.py          # FastAPI app factory
```

## Import Rules (Strict)

| From → To | domain | application | infrastructure | presentation |
|-----------|--------|-------------|----------------|--------------|
| domain | ✅ | ❌ | ❌ | ❌ |
| application | ✅ | ✅ | ❌ | ❌ |
| infrastructure | ✅ | ✅ | ✅ | ❌ |
| presentation | ✅ | ✅ | ✅ | ✅ |

## Port Definition Pattern

```python
# application/ports/output/user_repository.py
from typing import Protocol
from src.domain.models.user import User

class UserRepository(Protocol):
    async def get_by_id(self, user_id: str) -> User | None: ...
    async def save(self, user: User) -> User: ...
    async def delete(self, user_id: str) -> None: ...
```

## Use Case Pattern

```python
# application/use_cases/create_learning_plan.py
from dataclasses import dataclass
from src.application.dtos.learning_plan import CreateLearningPlanCommand
from src.application.ports.output.learning_plan_repository import LearningPlanRepository
from src.domain.models.learning_plan import LearningPlan

@dataclass
class CreateLearningPlanUseCase:
    repository: LearningPlanRepository

    async def execute(self, command: CreateLearningPlanCommand) -> LearningPlan:
        plan = LearningPlan.create(
            user_id=command.user_id,
            title=command.title,
            goals=command.goals,
        )
        return await self.repository.save(plan)
```

## DI Wiring Pattern

```python
# presentation/api/dependencies.py
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.infrastructure.database.session import get_session
from src.infrastructure.database.repositories.learning_plan_repo import SqlLearningPlanRepository
from src.application.use_cases.create_learning_plan import CreateLearningPlanUseCase

def get_learning_plan_repo(
    session: AsyncSession = Depends(get_session),
) -> SqlLearningPlanRepository:
    return SqlLearningPlanRepository(session)

def get_create_learning_plan_use_case(
    repo: SqlLearningPlanRepository = Depends(get_learning_plan_repo),
) -> CreateLearningPlanUseCase:
    return CreateLearningPlanUseCase(repository=repo)
```

## Repository Implementation Pattern

```python
# infrastructure/database/repositories/learning_plan_repo.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.domain.models.learning_plan import LearningPlan
from src.infrastructure.database.orm.learning_plan_orm import LearningPlanORM

class SqlLearningPlanRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, plan: LearningPlan) -> LearningPlan:
        orm = self._to_orm(plan)
        self._session.add(orm)
        await self._session.flush()
        return self._to_domain(orm)

    @staticmethod
    def _to_orm(plan: LearningPlan) -> LearningPlanORM:
        return LearningPlanORM(
            id=plan.id,
            user_id=plan.user_id,
            title=plan.title,
            # ... map all fields
        )

    @staticmethod
    def _to_domain(orm: LearningPlanORM) -> LearningPlan:
        return LearningPlan(
            id=orm.id,
            user_id=orm.user_id,
            title=orm.title,
            # ... map all fields
        )
```
