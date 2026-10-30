from uuid import UUID

from src.account.application.dtos.availability import AvailabilityResponseDTO
from src.account.application.ports.availability_repository_port import (
    AvailabilityRepositoryPort,
)
from src.account.application.use_cases.availability.mappers import (
    to_availability_response_dto,
)
from src.account.domain.models.availability import AvailabilityProfile


class GetAvailabilityUseCase:
    """Query use case retrieving learner availability with lazy initialization (UC-04)."""

    def __init__(self, repository: AvailabilityRepositoryPort) -> None:
        self._repository = repository

    async def execute(self, user_id: UUID) -> AvailabilityResponseDTO:
        profile = await self._repository.get_by_user_id(user_id)
        if profile is None:
            # Lazy initialization: Return default template with id=None without persisting
            default_profile = AvailabilityProfile.create_default(user_id)
            return to_availability_response_dto(default_profile, is_lazy_default=True)

        return to_availability_response_dto(profile, is_lazy_default=False)
