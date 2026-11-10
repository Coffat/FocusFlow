from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from src.planning.domain.exceptions.planning_exceptions import (
    InvalidMilestoneSequenceError,
)
from src.shared_kernel.domain.base import Entity, generate_uuid7

AI_MILESTONE_MIN_COUNT: int = 3
AI_MILESTONE_MAX_COUNT: int = 7


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

    def approve(self, now: datetime) -> None:
        if self.status == MilestoneStatus.PENDING:
            self.status = MilestoneStatus.APPROVED
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
    """Validate that milestones have contiguous 1..N sequence_order and optional AI 3..7 count."""
    count = len(milestones)
    if enforce_ai_bounds and not (AI_MILESTONE_MIN_COUNT <= count <= AI_MILESTONE_MAX_COUNT):
        raise InvalidMilestoneSequenceError(
            message=(
                f"Số lượng cột mốc do AI sinh phải nằm trong khoảng "
                f"[{AI_MILESTONE_MIN_COUNT}, {AI_MILESTONE_MAX_COUNT}], nhận được {count}."
            )
        )
    if count == 0:
        raise InvalidMilestoneSequenceError(message="Danh sách cột mốc không được rỗng.")

    orders = sorted(m.sequence_order for m in milestones)
    expected = list(range(1, count + 1))
    if orders != expected:
        raise InvalidMilestoneSequenceError(
            message=f"Thứ tự sequence_order của các cột mốc phải liên tục từ 1..{count}, nhận được {orders}."
        )
