from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from src.shared_kernel.domain.base import AggregateRoot, generate_uuid7


class GoalStatus(StrEnum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


@dataclass
class Goal(AggregateRoot):
    """Learner Goal aggregate root (UC-07 / FR-GOAL-001)."""

    user_id: UUID = field(default_factory=generate_uuid7)
    title: str = ""
    raw_description: str | None = ""
    target_date: date | None = None
    status: GoalStatus = GoalStatus.ACTIVE
    created_at: datetime = field(default_factory=lambda: datetime.min)
    updated_at: datetime = field(default_factory=lambda: datetime.min)

    def __post_init__(self) -> None:
        if isinstance(self.status, str):
            self.status = GoalStatus(self.status)
        if not self.title or not self.title.strip():
            raise ValueError("Tiêu đề mục tiêu học tập (Goal.title) không được để trống.")
        self.title = self.title.strip()

    def mark_completed(self, now: datetime) -> None:
        self.status = GoalStatus.COMPLETED
        self.updated_at = now

    def archive(self, now: datetime) -> None:
        self.status = GoalStatus.ARCHIVED
        self.updated_at = now
