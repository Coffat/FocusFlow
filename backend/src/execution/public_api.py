from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from src.shared_kernel.domain.events import DomainEvent


@dataclass(frozen=True, kw_only=True)
class StudySessionCompletedEvent(DomainEvent):
    """Published when a learner finishes a Pomodoro or Stopwatch study session (UC-10)."""

    user_id: UUID
    session_id: UUID
    actual_duration_seconds: int


@dataclass(frozen=True, kw_only=True)
class StudySessionAbandonedEvent(DomainEvent):
    """Published when a stale session is auto-recovered after 5 minutes without heartbeat (UC-10)."""

    user_id: UUID
    session_id: UUID
    recovered_duration_seconds: int


@dataclass(frozen=True, kw_only=True)
class ExternalCalendarBusyUpdatedEvent(DomainEvent):
    """Published when Google Calendar 2-way sync detects updated busy slots (UC-13)."""

    user_id: UUID


@dataclass(frozen=True)
class StudyExecutionStatsDTO:
    """Read-only execution statistics for Evaluation and SRL profile aggregation."""

    user_id: UUID
    completed_sessions_count: int
    total_focus_seconds: int


class StudyExecutionQueryPort(Protocol):
    """Cross-context read-only query port for StudySession metrics."""

    async def get_user_execution_stats(self, user_id: UUID) -> StudyExecutionStatsDTO: ...
