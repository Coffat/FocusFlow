from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any
from uuid import UUID

from src.shared_kernel.domain.base import generate_uuid7, utc_now


@dataclass
class MilestoneProof:
    milestone_id: UUID
    user_id: UUID
    status: str
    questions: list[dict[str, Any]]
    answers: list[dict[str, Any]] = field(default_factory=list)
    score: int | None = None
    confidence: float | None = None
    corrective_action: str | None = None
    id: UUID = field(default_factory=generate_uuid7)
    created_at: datetime = field(default_factory=utc_now)
    submitted_at: datetime | None = None


@dataclass
class WeeklyReview:
    roadmap_id: UUID
    user_id: UUID
    period_start: date
    period_end: date
    quantitative_summary: dict[str, Any]
    strengths_feedback: str
    bottlenecks_feedback: str
    action_recommendations: str
    user_reflection_payload: dict[str, Any]
    id: UUID = field(default_factory=generate_uuid7)
    generated_at: datetime = field(default_factory=utc_now)
