from typing import Protocol
from uuid import UUID

from src.account.domain.models.availability import AvailabilityProfile


class AvailabilityRepositoryPort(Protocol):
    """Driven Port for persisting and retrieving AvailabilityProfile Aggregate."""

    async def get_by_user_id(self, user_id: UUID) -> AvailabilityProfile | None:
        """Retrieve availability profile by learner's UUID."""
        ...

    async def save(self, profile: AvailabilityProfile) -> AvailabilityProfile:
        """Persist availability profile and synchronize 3NF/BCNF slots."""
        ...
