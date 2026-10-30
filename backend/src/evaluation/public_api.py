from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from src.shared_kernel.domain.events import DomainEvent

__all__ = [
    "AIReviewGeneratedEvent",
    "DominoShiftRequestedEvent",
    "EvaluationMetricsDTO",
    "EvaluationMetricsQueryPort",
    "ScheduleChangeLogEntryDTO",
    "ScheduleChangeLogPort",
]


@dataclass(frozen=True, kw_only=True)
class DominoShiftRequestedEvent(DomainEvent):
    """Published when DominoShiftEngine requests schedule adaptation for overdue tasks (UC-20)."""

    user_id: UUID
    roadmap_id: UUID
    shift_days: int


@dataclass(frozen=True, kw_only=True)
class AIReviewGeneratedEvent(DomainEvent):
    """Published when a weekly/milestone SRL AI Review completes (UC-19)."""

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


@dataclass(frozen=True, slots=True)
class ScheduleChangeLogEntryDTO:
    """Immutable DTO returned after recording a schedule change log entry."""

    id: UUID
    roadmap_id: UUID
    schedule_id: UUID | None
    task_id: UUID | None
    trigger_type: str
    reason: str | None
    affected_tasks_count: int
    total_shifted_minutes: int
    diff_payload: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None


class ScheduleChangeLogPort(Protocol):
    """Cross-context port exposed by Evaluation to Planning & Execution to log schedule changes."""

    async def log_schedule_change(
        self,
        *,
        roadmap_id: UUID,
        trigger_type: str = "AI_REPLAN",
        schedule_id: UUID | None = None,
        task_id: UUID | None = None,
        reason: str | None = None,
        affected_tasks_count: int = 1,
        total_shifted_minutes: int = 0,
        diff_payload: dict[str, Any] | None = None,
        now: datetime | None = None,
    ) -> ScheduleChangeLogEntryDTO: ...

    async def record_change_log(
        self,
        *,
        roadmap_id: UUID,
        trigger_type: str = "AI_REPLAN",
        schedule_id: UUID | None = None,
        task_id: UUID | None = None,
        reason: str | None = None,
        affected_tasks_count: int = 1,
        total_shifted_minutes: int = 0,
        diff_payload: dict[str, Any] | None = None,
        now: datetime | None = None,
    ) -> ScheduleChangeLogEntryDTO: ...
