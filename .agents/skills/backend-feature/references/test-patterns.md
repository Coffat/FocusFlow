# Test Patterns for Backend Features

## Unit Test — Use Case

```python
# tests/application/use_cases/test_create_learning_plan.py
import pytest
from unittest.mock import AsyncMock
from src.application.use_cases.create_learning_plan import CreateLearningPlanUseCase
from src.application.dtos.learning_plan import CreateLearningPlanCommand
from src.domain.models.learning_plan import LearningPlan

@pytest.fixture
def mock_repo():
    repo = AsyncMock()
    repo.save.return_value = LearningPlan(
        id="plan-001", user_id="user-001", title="Test Plan", goals=[]
    )
    return repo

async def test_create_learning_plan_success(mock_repo):
    use_case = CreateLearningPlanUseCase(repository=mock_repo)
    command = CreateLearningPlanCommand(
        user_id="user-001", title="Test Plan", goals=[]
    )

    result = await use_case.execute(command)

    assert result.id == "plan-001"
    mock_repo.save.assert_called_once()

async def test_create_learning_plan_validates_title(mock_repo):
    use_case = CreateLearningPlanUseCase(repository=mock_repo)
    command = CreateLearningPlanCommand(
        user_id="user-001", title="", goals=[]
    )

    with pytest.raises(ValueError):
        await use_case.execute(command)
```

## Unit Test — Domain Model

```python
# tests/domain/models/test_learning_plan.py
import pytest
from src.domain.models.learning_plan import LearningPlan

def test_create_plan_sets_defaults():
    plan = LearningPlan.create(user_id="u1", title="Math", goals=[])
    assert plan.status == "draft"
    assert plan.created_at is not None

def test_plan_cannot_exceed_max_goals():
    with pytest.raises(ValueError):
        LearningPlan.create(user_id="u1", title="T", goals=["g"] * 51)
```

## Integration Test — Repository

```python
# tests/infrastructure/database/test_learning_plan_repo.py
import pytest
from src.infrastructure.database.repositories.learning_plan_repo import SqlLearningPlanRepository
from src.domain.models.learning_plan import LearningPlan

@pytest.fixture
async def repo(test_db_session):
    return SqlLearningPlanRepository(test_db_session)

async def test_save_and_get(repo):
    plan = LearningPlan.create(user_id="u1", title="Math", goals=[])
    saved = await repo.save(plan)

    fetched = await repo.get_by_id(saved.id)
    assert fetched is not None
    assert fetched.title == "Math"

async def test_get_nonexistent_returns_none(repo):
    result = await repo.get_by_id("nonexistent-id")
    assert result is None
```

## Naming Conventions

- Test files: `test_{module_name}.py` — mirror source path in `tests/`
- Test functions: `test_{action}_{scenario}` (e.g., `test_create_plan_validates_title`)
- Fixtures: descriptive noun (e.g., `mock_repo`, `test_db_session`, `sample_user`)
