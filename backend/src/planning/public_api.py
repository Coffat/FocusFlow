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


@dataclass(frozen=True, slots=True)
class MilestoneOwnershipDTO:
    milestone_id: UUID
    roadmap_id: UUID
    user_id: UUID
    title: str


class MilestoneOwnershipQueryPort(Protocol):
    async def get_milestone(self, milestone_id: UUID) -> MilestoneOwnershipDTO | None: ...

    async def roadmap_belongs_to(self, roadmap_id: UUID, user_id: UUID) -> bool: ...


_milestone_ownership_factory: Any = None


def register_milestone_ownership_factory(factory: Any) -> None:
    global _milestone_ownership_factory
    _milestone_ownership_factory = factory


def create_milestone_ownership_port(session: Any) -> MilestoneOwnershipQueryPort:
    global _milestone_ownership_factory
    if _milestone_ownership_factory is None:
        import importlib

        importlib.import_module("src.planning.infrastructure.adapters.milestone_ownership_adapter")
    assert callable(_milestone_ownership_factory)
    result: MilestoneOwnershipQueryPort = _milestone_ownership_factory(session)
    return result


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


@dataclass(frozen=True, slots=True)
class PlanningActiveRoadmapDTO:
    id: UUID
    code: str
    title: str
    commitment_hours_per_week: float
    deadline: str | None
    completed_tasks: int
    total_tasks: int
    progress_pct: float
    next_task_code: str | None
    next_task_title: str | None


@dataclass(frozen=True, slots=True)
class PlanningDashboardScheduleBlockDTO:
    id: UUID
    day_of_week: int
    day_label: str
    start_time: str
    end_time: str
    title: str
    category: str
    status: str
    pomodoro_count: int
    duration_minutes: int
    roadmap_code: str
    description: str | None = None


class PlanningDashboardQueryPort(Protocol):
    async def get_active_roadmaps_for_user(
        self, user_id: UUID
    ) -> list[PlanningActiveRoadmapDTO]: ...

    async def get_week_schedule_blocks(
        self, user_id: UUID, start_date: date, end_date: date
    ) -> list[PlanningDashboardScheduleBlockDTO]: ...

    async def get_monthly_target_hours(self, user_id: UUID) -> float: ...


_planning_dashboard_factory: Any = None


def register_planning_dashboard_factory(factory: Any) -> None:
    global _planning_dashboard_factory
    _planning_dashboard_factory = factory


def create_planning_dashboard_query_port(session: Any) -> PlanningDashboardQueryPort:
    global _planning_dashboard_factory
    if _planning_dashboard_factory is None:
        import importlib

        importlib.import_module("src.planning.infrastructure.adapters.planning_dashboard_adapter")
    assert callable(_planning_dashboard_factory)
    res: PlanningDashboardQueryPort = _planning_dashboard_factory(session)
    return res
