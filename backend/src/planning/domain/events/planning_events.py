from dataclasses import dataclass
from uuid import UUID

from src.shared_kernel.domain.events import DomainEvent


@dataclass(frozen=True, kw_only=True)
class MilestoneApprovedEvent(DomainEvent):
    """Published when a learner approves Level-1 Milestones for a Roadmap (UC-07)."""

    user_id: UUID
    roadmap_id: UUID
    milestone_count: int = 0
    aggregate_type: str = "Roadmap"


@dataclass(frozen=True, kw_only=True)
class OfficialScheduleAppliedEvent(DomainEvent):
    """Published when a learner applies a verified ScheduleProposal as OfficialSchedule (UC-08 / UC-12)."""

    user_id: UUID
    roadmap_id: UUID
    schedule_id: UUID
    proposal_id: UUID | None = None
    total_sessions: int = 0
    total_planned_minutes: int = 0
    aggregate_type: str = "OfficialSchedule"
