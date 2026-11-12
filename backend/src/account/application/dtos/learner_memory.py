from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class LearnerMemoryResponseDTO(BaseModel):
    id: UUID
    memory_key: str
    value: dict[str, Any]
    category: str
    epistemic_level: str
    confidence: float
    sample_size: int
    evidence: list[dict[str, Any]]
    status: str
    created_at: datetime
    updated_at: datetime


class UpdateLearnerMemoryRequestDTO(BaseModel):
    action: Literal["confirm", "edit", "reject"]
    value: dict[str, Any] | None = None


class ResetLearnerMemoryRequestDTO(BaseModel):
    confirm: bool = Field(description="Must be true after explicit learner confirmation")
