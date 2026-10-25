from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from src.shared_kernel.domain.events import DomainEvent


@dataclass(frozen=True, kw_only=True)
class DominoShiftRequestedEvent(DomainEvent):
    """Published when DominoShiftEngine requests schedule adaptation for overdue tasks (UC-16)."""

    user_id: UUID
    roadmap_id: UUID
    shift_days: int


@dataclass(frozen=True, kw_only=True)
class AIReviewGeneratedEvent(DomainEvent):
    """Published when a weekly/monthly SRL AI Review completes (UC-15)."""

    user_id: UUID
    review_id: UUID


@dataclass(frozen=True)
class EvaluationMetricsDTO:
    """Read-only quantitative metrics DTO (Adherence Rate, Velocity, Streak)."""

    user_id: UUID
    adherence_rate: float
    streak_days: int


class EvaluationMetricsQueryPort(Protocol):
    """Cross-context read-only query port for Evaluation & Analytics."""

    async def get_latest_metrics(self, user_id: UUID) -> EvaluationMetricsDTO: ...
