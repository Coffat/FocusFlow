from uuid import UUID

from src.account.application.dtos.availability import (
    AvailabilityResponseDTO,
    UpdateAvailabilityRequestDTO,
)
from src.account.application.ports.availability_repository_port import (
    AvailabilityRepositoryPort,
)
from src.account.application.use_cases.availability.mappers import (
    from_weekly_schedule_dto,
    to_availability_response_dto,
)
from src.account.domain.events.availability_events import AvailabilityUpdatedEvent
from src.account.domain.exceptions.availability import (
    InvalidAvailabilityModeException,
    InvalidCalendarModeException,
    InvalidMinSessionMinutesException,
)
from src.account.domain.models.availability import (
    AvailabilityMode,
    AvailabilityProfile,
    CalendarIntegrationMode,
)
from src.shared_kernel.application.uow import AsyncUnitOfWork


class UpdateAvailabilityUseCase:
    """Command use case updating learner availability with 3NF persistence & Outbox event (UC-04)."""

    def __init__(
        self,
        repository: AvailabilityRepositoryPort,
        uow: AsyncUnitOfWork,
    ) -> None:
        self._repository = repository
        self._uow = uow

    async def execute(
        self, user_id: UUID, request: UpdateAvailabilityRequestDTO
    ) -> AvailabilityResponseDTO:
        try:
            target_mode = AvailabilityMode(request.mode)
        except ValueError as exc:
            raise InvalidAvailabilityModeException(mode=request.mode) from exc

        try:
            target_cal_mode = CalendarIntegrationMode(request.calendar_integration_mode)
        except ValueError as exc:
            raise InvalidCalendarModeException(
                calendar_mode=request.calendar_integration_mode
            ) from exc

        if not (15 <= request.min_session_minutes <= 120):
            raise InvalidMinSessionMinutesException(min_session_minutes=request.min_session_minutes)

        async with self._uow:
            profile = await self._repository.get_by_user_id(user_id)
            new_weekly_schedule = from_weekly_schedule_dto(
                request.weekly_schedule,
                target_mode=target_mode,
                existing_profile=profile,
                default_min_session_minutes=request.min_session_minutes,
            )

            if profile is None:
                # First time creation: validate invariants against requested mode
                new_weekly_schedule.validate_invariants(target_mode)
                profile = AvailabilityProfile(
                    user_id=user_id,
                    mode=target_mode,
                    calendar_integration_mode=target_cal_mode,
                    weekly_schedule=new_weekly_schedule,
                    min_session_minutes=request.min_session_minutes,
                )
                profile.add_domain_event(
                    AvailabilityUpdatedEvent(
                        user_id=user_id,
                        availability_mode=target_mode.value,
                        aggregate_id=profile.id,
                    )
                )
            else:
                profile.update_schedule(
                    new_schedule=new_weekly_schedule,
                    calendar_integration_mode=target_cal_mode,
                    min_session_minutes=request.min_session_minutes,
                    new_mode=target_mode,
                )

            saved = await self._repository.save(profile)
            self._uow.collect_events_from(profile)
            await self._uow.commit()

        return to_availability_response_dto(saved, is_lazy_default=False)
