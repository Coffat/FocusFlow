from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Protocol
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


@dataclass(frozen=True)
class ScheduleBlockSyncDTO:
    """Read-only ScheduleBlock DTO exposed for Calendar Sync (UC-17)."""

    id: UUID
    roadmap_id: UUID
    official_schedule_id: UUID
    task_id: UUID | None
    sequence_in_task: int
    block_type: str
    block_date: date
    start_time: datetime
    end_time: datetime
    scheduled_duration_minutes: int
    is_protected: bool
    status: str
    external_calendar_event_id: str | None
    etag: str | None
    sync_status: str
    last_synced_at: datetime | None
    placement_rationale: str | None


class ScheduleBlockSyncPort(Protocol):
    """Cross-context port exposed by Planning for Calendar Two-Way Sync (UC-17)."""

    async def get_blocks_for_schedule(
        self,
        official_schedule_id: UUID,
        sync_status_in: Sequence[str] | None = None,
    ) -> list[ScheduleBlockSyncDTO]: ...

    async def get_block_by_id(self, block_id: UUID) -> ScheduleBlockSyncDTO | None: ...

    async def get_block_by_external_event_id(
        self, external_event_id: str
    ) -> ScheduleBlockSyncDTO | None: ...

    async def update_block_sync_info(
        self,
        block_id: UUID,
        *,
        external_calendar_event_id: str | None = None,
        etag: str | None = None,
        sync_status: str | None = None,
        last_synced_at: datetime | None = None,
    ) -> None: ...


_schedule_block_sync_factory: Any = None


def register_schedule_block_sync_factory(factory: Any) -> None:
    global _schedule_block_sync_factory
    _schedule_block_sync_factory = factory


def create_schedule_block_sync_port(session: Any) -> ScheduleBlockSyncPort:
    global _schedule_block_sync_factory
    if _schedule_block_sync_factory is None:
        import importlib

        importlib.import_module("src.planning.infrastructure.adapters.schedule_block_sync_adapter")
    assert callable(_schedule_block_sync_factory)
    res: ScheduleBlockSyncPort = _schedule_block_sync_factory(session)
    return res
