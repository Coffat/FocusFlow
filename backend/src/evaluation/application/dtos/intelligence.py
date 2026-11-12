from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class GenerateProofResponseDTO(BaseModel):
    proof_id: UUID
    status: str
    questions: list[dict[str, Any]]


class SubmitProofRequestDTO(BaseModel):
    answers: list[dict[str, Any]] = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)


class MilestoneProofResponseDTO(BaseModel):
    id: UUID
    milestone_id: UUID
    status: str
    score: int
    confidence: float
    corrective_action: str | None


class GenerateWeeklyReviewRequestDTO(BaseModel):
    roadmap_id: UUID
    period_start: date
    period_end: date
    reflection: dict[str, Any] = Field(default_factory=dict)


class WeeklyReviewResponseDTO(BaseModel):
    id: UUID
    roadmap_id: UUID
    period_start: date
    period_end: date
    quantitative_summary: dict[str, Any]
    strengths_feedback: str
    bottlenecks_feedback: str
    action_recommendations: str
    user_reflection_payload: dict[str, Any]
    generated_at: datetime
