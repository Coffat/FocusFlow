from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from src.planning.domain.exceptions.planning_exceptions import (
    InvalidMilestoneSequenceError,
)
from src.shared_kernel.domain.base import Entity, generate_uuid7


class MilestoneStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


@dataclass
class Milestone(Entity):
    """Milestone entity within a Roadmap (UC-07 / FR-PLAN-001)."""

    roadmap_id: UUID = field(default_factory=generate_uuid7)
    sequence_order: int = 1
    title: str = ""
    description: str | None = None
    learning_outcomes: tuple[str, ...] = ()
    completion_criteria: str | None = None
    estimated_effort_minutes: int = 60
    required_concepts: tuple[str, ...] = ()
    unverified_concepts: tuple[str, ...] = ()
    prerequisite_milestone_ids: tuple[UUID, ...] = ()
    status: MilestoneStatus = MilestoneStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.min)
    updated_at: datetime = field(default_factory=lambda: datetime.min)

    def __post_init__(self) -> None:
        if isinstance(self.status, str):
            self.status = MilestoneStatus(self.status)
        if self.sequence_order < 1:
            raise InvalidMilestoneSequenceError(
                message=f"Thứ tự cột mốc (sequence_order={self.sequence_order}) phải >= 1."
            )
        if not self.title or not self.title.strip():
            raise InvalidMilestoneSequenceError(
                message="Tiêu đề cột mốc (Milestone.title) không được để trống."
            )
        self.title = self.title.strip()
        self.learning_outcomes = tuple(
            outcome.strip() for outcome in self.learning_outcomes if outcome.strip()
        )
        self.required_concepts = tuple(
            concept.strip() for concept in self.required_concepts if concept.strip()
        )
        self.unverified_concepts = tuple(
            concept.strip() for concept in self.unverified_concepts if concept.strip()
        )
        if self.estimated_effort_minutes <= 0:
            raise InvalidMilestoneSequenceError(
                message="Nỗ lực ước tính của Milestone phải lớn hơn 0 phút."
            )

    def approve(self, now: datetime) -> None:
        if self.status == MilestoneStatus.PENDING:
            self.status = MilestoneStatus.APPROVED
            self.updated_at = now

    def reset_to_pending(self, now: datetime) -> None:
        if self.status == MilestoneStatus.APPROVED:
            self.status = MilestoneStatus.PENDING
            self.updated_at = now

    def mark_in_progress(self, now: datetime) -> None:
        self.status = MilestoneStatus.IN_PROGRESS
        self.updated_at = now

    def mark_completed(self, now: datetime) -> None:
        self.status = MilestoneStatus.COMPLETED
        self.updated_at = now


def validate_milestone_sequence(
    milestones: Sequence[Milestone],
    *,
    enforce_ai_bounds: bool = False,
) -> None:
    """Validate a non-empty adaptive milestone list with contiguous 1..N ordering.

    ``enforce_ai_bounds`` remains for compatibility. FR-PLAN-001 no longer
    imposes a pedagogical count bound.
    """
    count = len(milestones)
    _ = enforce_ai_bounds
    if count == 0:
        raise InvalidMilestoneSequenceError(message="Danh sách cột mốc không được rỗng.")

    orders = sorted(m.sequence_order for m in milestones)
    expected = list(range(1, count + 1))
    if orders != expected:
        raise InvalidMilestoneSequenceError(
            message=f"Thứ tự sequence_order của các cột mốc phải liên tục từ 1..{count}, nhận được {orders}."
        )
