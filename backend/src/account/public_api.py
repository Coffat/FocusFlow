from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from src.shared_kernel.domain.events import DomainEvent


@dataclass(frozen=True, kw_only=True)
class UserUpgradedToPremiumEvent(DomainEvent):
    """Published when a learner completes a Pro subscription payment (UC-05)."""

    user_id: UUID
    plan_tier: str = "PRO"


@dataclass(frozen=True, kw_only=True)
class AvailabilityUpdatedEvent(DomainEvent):
    """Published when a learner updates their Mode A/B availability profile (UC-04)."""

    user_id: UUID
    availability_mode: str


@dataclass(frozen=True)
class AvailabilitySnapshotDTO:
    """Read-only DTO exposed to Planning & Evaluation contexts."""

    user_id: UUID
    mode: str
    daily_cap_minutes: int
    weekly_capacity_minutes: int


class AvailabilityQueryPort(Protocol):
    """Cross-context read-only query port for learner availability & Mode A/B caps."""

    async def get_active_availability(self, user_id: UUID) -> AvailabilitySnapshotDTO | None: ...


class QuotaFacadePort(Protocol):
    """Cross-context port for 2-Phase ACID AI Quota Reservation (ADR-003)."""

    async def reserve_quota(self, user_id: UUID, operation_type: str, cost: int = 1) -> UUID: ...

    async def commit_reservation(
        self, reservation_id: UUID, prompt_tokens: int, completion_tokens: int
    ) -> None: ...

    async def release_reservation(self, reservation_id: UUID, reason: str) -> None: ...
