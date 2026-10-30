from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any
from uuid import UUID

from src.execution.public_api import ExistingScheduledTaskDTO
from src.planning.domain.models.goal import Goal
from src.planning.domain.models.milestone import Milestone
from src.planning.domain.models.roadmap import Roadmap
from src.planning.domain.models.schedule import OfficialSchedule, ScheduleProposal


@dataclass(frozen=True, slots=True)
class CreateGoalAndRoadmapResultDTO:
    goal: Goal
    roadmap: Roadmap


@dataclass(frozen=True, slots=True)
class SseJobTicketDTO:
    job_id: UUID
    reservation_id: UUID
    roadmap_id: UUID
    job_type: str
    status: str
    stream_url: str


@dataclass(frozen=True, slots=True)
class MilestoneInputItemDTO:
    title: str
    description: str | None = None
    sequence_order: int = 1
    milestone_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class ProposedTaskInputItemDTO:
    milestone_id: UUID
    title: str
    description: str | None = None
    estimated_minutes: int = 45
    scheduled_date: date | str | None = None
    scheduled_start: datetime | str | None = None
    scheduled_end: datetime | str | None = None
    task_id: UUID | None = None
    prerequisite_ids: list[UUID | str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ProposedDependencyInputItemDTO:
    predecessor_id: UUID | str
    successor_id: UUID | str
    is_mandatory: bool = True


@dataclass(frozen=True, slots=True)
class ScheduleProposalViewDTO:
    proposal: ScheduleProposal
    is_valid: bool
    violations: list[dict[str, Any]] = field(default_factory=list)
    soft_overflow_warnings: list[dict[str, Any]] = field(default_factory=list)
    advisory_warnings: list[str] = field(default_factory=list)
    diff_summary: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ApplyScheduleProposalResultDTO:
    roadmap: Roadmap
    official_schedule: OfficialSchedule
    proposal: ScheduleProposal
    preserved_completed_tasks_count: int
    replaced_tasks_count: int
    inserted_tasks_count: int
    affected_tasks_count: int
    total_shifted_minutes: int
    trigger_type: str


@dataclass(frozen=True, slots=True)
class RoadmapDetailDTO:
    roadmap: Roadmap
    goal: Goal | None
    milestones: list[Milestone]
    official_schedule: OfficialSchedule | None
    current_draft_proposal: ScheduleProposal | None
    scheduled_tasks: list[ExistingScheduledTaskDTO] = field(default_factory=list)
