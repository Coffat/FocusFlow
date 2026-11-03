from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from src.shared_kernel.domain.events import DomainEvent


@dataclass(frozen=True, kw_only=True)
class OfficialScheduleAppliedEvent(DomainEvent):
    """Published when a learner applies a verified ScheduleProposal as OfficialSchedule (UC-08)."""

    user_id: UUID
    roadmap_id: UUID
    schedule_id: UUID


@dataclass(frozen=True, kw_only=True)
class RoadmapPausedEvent(DomainEvent):
    """Published when an active roadmap is paused by the learner (UC-09)."""

    user_id: UUID
    roadmap_id: UUID


@dataclass(frozen=True, kw_only=True)
class TaskStalledThresholdReachedEvent(DomainEvent):
    """Published when a task exceeds the overdue/split threshold (UC-17)."""

    user_id: UUID
    task_id: UUID


@dataclass(frozen=True)
class TaskSummaryDTO:
    """Read-only DTO for Execution and Evaluation contexts."""

    task_id: UUID
    roadmap_id: UUID
    title: str
    estimated_pomodoros: int
    status: str


class RoadmapTaskQueryPort(Protocol):
    """Cross-context read-only query port for Tasks, Milestones, and OfficialSchedule."""

    async def get_task_summary(self, task_id: UUID) -> TaskSummaryDTO | None: ...
