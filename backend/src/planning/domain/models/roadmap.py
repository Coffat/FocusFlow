from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from src.planning.domain.exceptions.planning_exceptions import (
    ActiveRoadmapLimitExceededError,
    InvalidRoadmapStateTransitionError,
    PlanningDomainError,
)
from src.shared_kernel.domain.base import AggregateRoot, generate_uuid7

FREE_MAX_ACTIVE_ROADMAPS: int = 3
PREMIUM_MAX_ACTIVE_ROADMAPS: int = 15


class RoadmapStatus(StrEnum):
    INITIALIZED = "INITIALIZED"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


def get_max_active_roadmaps_for_tier(tier: str) -> int:
    normalized = (tier or "FREE").strip().upper()
    if normalized in ("PREMIUM", "PRO"):
        return PREMIUM_MAX_ACTIVE_ROADMAPS
    return FREE_MAX_ACTIVE_ROADMAPS


@dataclass
class Roadmap(AggregateRoot):
    """Roadmap aggregate root enforcing SRS state machine & OS-02 tier limits."""

    user_id: UUID = field(default_factory=generate_uuid7)
    goal_id: UUID = field(default_factory=generate_uuid7)
    title: str = ""
    description: str | None = None
    status: RoadmapStatus = RoadmapStatus.INITIALIZED
    start_date: date | None = None
    target_date: date | None = None
    created_at: datetime = field(default_factory=lambda: datetime.min)
    updated_at: datetime = field(default_factory=lambda: datetime.min)

    def __post_init__(self) -> None:
        if isinstance(self.status, str):
            self.status = RoadmapStatus(self.status)
        if not self.title or not self.title.strip():
            raise PlanningDomainError(
                message="Tiêu đề lộ trình (Roadmap.title) không được để trống.",
                code="INVALID_ROADMAP_TITLE",
            )
        self.title = self.title.strip()
        if (
            self.start_date is not None
            and self.target_date is not None
            and self.target_date < self.start_date
        ):
            raise PlanningDomainError(
                message="Ngày đích (target_date) phải lớn hơn hoặc bằng ngày bắt đầu (start_date).",
                code="INVALID_ROADMAP_DATE_RANGE",
            )

    @staticmethod
    def validate_active_limit(
        *,
        tier: str,
        current_active_count: int,
    ) -> None:
        max_allowed = get_max_active_roadmaps_for_tier(tier)
        if current_active_count >= max_allowed:
            raise ActiveRoadmapLimitExceededError(
                tier=tier,
                current_active_count=current_active_count,
                max_allowed=max_allowed,
            )

    def activate(
        self,
        now: datetime,
        *,
        tier: str = "FREE",
        current_active_count: int = 0,
    ) -> None:
        """Transition INITIALIZED or PAUSED -> ACTIVE (with OS-02 active cap check)."""
        if self.status == RoadmapStatus.ACTIVE:
            self.updated_at = now
            return

        if self.status not in (RoadmapStatus.INITIALIZED, RoadmapStatus.PAUSED):
            raise InvalidRoadmapStateTransitionError(
                current_status=self.status.value,
                target_status=RoadmapStatus.ACTIVE.value,
            )

        self.validate_active_limit(tier=tier, current_active_count=current_active_count)
        self.status = RoadmapStatus.ACTIVE
        self.updated_at = now

    def pause(self, now: datetime) -> None:
        """Transition ACTIVE -> PAUSED."""
        if self.status != RoadmapStatus.ACTIVE:
            raise InvalidRoadmapStateTransitionError(
                current_status=self.status.value,
                target_status=RoadmapStatus.PAUSED.value,
            )
        self.status = RoadmapStatus.PAUSED
        self.updated_at = now

    def complete(self, now: datetime) -> None:
        """Transition ACTIVE -> COMPLETED (immutable terminal state)."""
        if self.status != RoadmapStatus.ACTIVE:
            raise InvalidRoadmapStateTransitionError(
                current_status=self.status.value,
                target_status=RoadmapStatus.COMPLETED.value,
            )
        self.status = RoadmapStatus.COMPLETED
        self.updated_at = now

    def archive(self, now: datetime) -> None:
        """Transition INITIALIZED | ACTIVE | PAUSED -> ARCHIVED (immutable terminal state)."""
        if self.status in (RoadmapStatus.COMPLETED, RoadmapStatus.ARCHIVED):
            raise InvalidRoadmapStateTransitionError(
                current_status=self.status.value,
                target_status=RoadmapStatus.ARCHIVED.value,
            )
        self.status = RoadmapStatus.ARCHIVED
        self.updated_at = now
