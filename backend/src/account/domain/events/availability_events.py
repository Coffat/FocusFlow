from dataclasses import dataclass
from uuid import UUID

from src.shared_kernel.domain.events import DomainEvent


@dataclass(frozen=True, kw_only=True)
class AvailabilityUpdatedEvent(DomainEvent):
    """Published when a learner updates their Mode A/B availability profile (UC-04)."""

    user_id: UUID
    availability_mode: str
    aggregate_type: str = "AvailabilityProfile"
