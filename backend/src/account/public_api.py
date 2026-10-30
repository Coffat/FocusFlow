from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from src.account.domain.events.availability_events import AvailabilityUpdatedEvent
from src.shared_kernel.domain.events import DomainEvent

__all__ = [
    "AvailabilityGateResultDTO",
    "AvailabilityQueryPort",
    "AvailabilitySnapshotDTO",
    "AvailabilityUpdatedEvent",
    "ProposedTaskBlockDTO",
    "QuotaFacadePort",
    "UserQueryPort",
    "UserSnapshotDTO",
    "UserUpgradedToPremiumEvent",
]


@dataclass(frozen=True, kw_only=True)
class UserUpgradedToPremiumEvent(DomainEvent):
    """Published when a learner completes a Pro subscription payment (UC-05)."""

    user_id: UUID
    plan_tier: str = "PRO"


@dataclass(frozen=True)
class AvailabilitySnapshotDTO:
    """Read-only DTO exposed to Planning & Evaluation contexts."""

    user_id: UUID
    mode: str
    daily_cap_minutes: int
    weekly_capacity_minutes: int
    updated_at: str | None = None


@dataclass(frozen=True)
class ProposedTaskBlockDTO:
    """Task block proposal submitted by Planning to be validated against learner availability."""

    task_id: UUID | None
    title: str
    day_of_week: str  # "monday" .. "sunday"
    start_time: str  # "HH:MM"
    end_time: str  # "HH:MM"
    end_day_offset: int = 0
    duration_minutes: int = 30


@dataclass(frozen=True)
class AvailabilityGateResultDTO:
    """Result of Tier-2 availability gate validation returned to Planning."""

    is_valid: bool
    has_soft_overflow: bool
    overflow_minutes: int
    violation_reasons: tuple[str, ...]
    availability_updated_at: str | None = None


class AvailabilityQueryPort(Protocol):
    """Cross-context read-only query & validation port exposed to Planning & Evaluation."""

    async def get_active_availability(self, user_id: UUID) -> AvailabilitySnapshotDTO | None: ...

    async def validate_schedule_proposal(
        self,
        user_id: UUID,
        proposed_tasks: list[ProposedTaskBlockDTO],
        occupied_tasks: list[ProposedTaskBlockDTO] | None = None,
        expected_updated_at: str | None = None,
    ) -> AvailabilityGateResultDTO: ...


class QuotaFacadePort(Protocol):
    """Cross-context port for 2-Phase ACID AI Quota Reservation (ADR-003)."""

    async def reserve_quota(self, user_id: UUID, operation_type: str, cost: int = 1) -> UUID: ...

    async def commit_reservation(
        self, reservation_id: UUID, prompt_tokens: int, completion_tokens: int
    ) -> None: ...

    async def release_reservation(self, reservation_id: UUID, reason: str) -> None: ...


@dataclass(frozen=True)
class UserSnapshotDTO:
    """Read-only user profile DTO exposed across bounded contexts."""

    id: UUID
    email: str
    full_name: str
    role: str
    tier: str
    is_locked: bool
    timezone: str = "Asia/Ho_Chi_Minh"


class UserQueryPort(Protocol):
    """Cross-context read-only query port for User information."""

    async def get_user_by_id(self, user_id: UUID) -> UserSnapshotDTO | None: ...

    async def get_user_by_email(self, email: str) -> UserSnapshotDTO | None: ...
