# API Patterns — FocusFlow

## Pydantic Schema Templates

```python
# presentation/api/schemas/learning_plan.py
from datetime import datetime
from pydantic import BaseModel, Field

class CreateLearningPlanRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    goals: list[str] = Field(default_factory=list)

class UpdateLearningPlanRequest(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    goals: list[str] | None = None

class LearningPlanResponse(BaseModel):
    id: str
    user_id: str
    title: str
    status: str
    goals: list[str]
    created_at: datetime

    model_config = {"from_attributes": True}

class PaginatedResponse(BaseModel):
    data: list[LearningPlanResponse]
    total: int
    page: int
    per_page: int
```

## Router Template

```python
# presentation/api/routes/learning_plans.py
from fastapi import APIRouter, Depends, HTTPException, status
from src.presentation.api.schemas.learning_plan import (
    CreateLearningPlanRequest,
    LearningPlanResponse,
)
from src.application.use_cases.create_learning_plan import (
    CreateLearningPlanUseCase,
    CreateLearningPlanCommand,
)
from src.presentation.api.dependencies import get_create_learning_plan_use_case

router = APIRouter(prefix="/api/v1/learning-plans", tags=["Learning Plans"])

@router.post(
    "/",
    response_model=LearningPlanResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_learning_plan(
    request: CreateLearningPlanRequest,
    use_case: CreateLearningPlanUseCase = Depends(get_create_learning_plan_use_case),
):
    """Create a new learning plan."""
    command = CreateLearningPlanCommand(
        user_id="current-user",  # from auth dependency
        title=request.title,
        goals=request.goals,
    )
    result = await use_case.execute(command)
    return LearningPlanResponse.model_validate(result, from_attributes=True)

@router.get("/{plan_id}", response_model=LearningPlanResponse)
async def get_learning_plan(plan_id: str):
    """Get a learning plan by ID."""
    ...

@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_learning_plan(plan_id: str):
    """Delete a learning plan."""
    ...
```

## HTTP Status Code Conventions

| Action | Status Code | Description |
|--------|------------|-------------|
| GET success | `200 OK` | Resource found |
| GET not found | `404 Not Found` | Resource not found |
| POST success | `201 Created` | Resource created |
| PUT/PATCH success | `200 OK` | Resource updated |
| DELETE success | `204 No Content` | Resource deleted |
| Validation error | `422 Unprocessable Entity` | FastAPI default |
| Auth required | `401 Unauthorized` | Missing/invalid token |
| Auth forbidden | `403 Forbidden` | Insufficient permissions |

## Error Response Format

```python
# presentation/api/schemas/error.py
from pydantic import BaseModel

class ErrorDetail(BaseModel):
    field: str | None = None
    message: str

class ErrorResponse(BaseModel):
    error: str
    details: list[ErrorDetail] = []
```

## Router Registration

```python
# presentation/main.py
from src.presentation.api.routes import learning_plans, users, tasks

app.include_router(learning_plans.router)
app.include_router(users.router)
app.include_router(tasks.router)
```
