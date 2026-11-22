from uuid import UUID

from src.account.application.dtos.profile import (
    LearnerSrlProfileDTO,
    ProfileResponseDTO,
    UpdateProfileRequestDTO,
)
from src.account.application.ports.learner_profile_repository_port import (
    LearnerProfileRecordDTO,
    LearnerProfileRepositoryPort,
)
from src.account.application.ports.user_repository_port import UserRepositoryPort
from src.account.application.use_cases.profile.aggregate_srl_profile_use_case import (
    COLD_START_MIN_SESSIONS,
)
from src.shared_kernel.application.uow import AsyncUnitOfWork


def _to_srl_profile_dto(record: LearnerProfileRecordDTO | None) -> LearnerSrlProfileDTO:
    if record is None or record.is_cold_start:
        return LearnerSrlProfileDTO(
            total_completed_sessions=record.total_completed_sessions if record is not None else 0,
            is_cold_start=True,
            min_sessions_required=COLD_START_MIN_SESSIONS,
            optimal_focus_duration_mins=None,
            estimation_bias_factor=None,
            weekly_completion_rate=float(record.weekly_completion_rate)
            if record is not None
            else 0.0,
            peak_productivity_slots=[],
            last_aggregated_at=record.last_aggregated_at if record is not None else None,
        )

    return LearnerSrlProfileDTO(
        total_completed_sessions=record.total_completed_sessions,
        is_cold_start=False,
        min_sessions_required=COLD_START_MIN_SESSIONS,
        optimal_focus_duration_mins=record.optimal_focus_duration_mins,
        estimation_bias_factor=float(record.estimation_bias_factor),
        weekly_completion_rate=float(record.weekly_completion_rate),
        peak_productivity_slots=list(record.peak_productivity_slots),
        last_aggregated_at=record.last_aggregated_at,
    )


class UpdateProfileUseCase:
    """Updates learner profile information (full_name and IANA timezone)."""

    def __init__(
        self,
        user_repo: UserRepositoryPort,
        uow: AsyncUnitOfWork,
        learner_profile_repo: LearnerProfileRepositoryPort | None = None,
    ) -> None:
        self.user_repo = user_repo
        self.uow = uow
        self.learner_profile_repo = learner_profile_repo

    async def _load_srl_profile(self, user_id: UUID) -> LearnerSrlProfileDTO | None:
        if self.learner_profile_repo is None:
            return None
        record = await self.learner_profile_repo.get_by_user_id(user_id)
        return _to_srl_profile_dto(record)

    async def execute(self, user_id: UUID, dto: UpdateProfileRequestDTO) -> ProfileResponseDTO:
        user = await self.user_repo.find_by_id(user_id)
        if not user:
            raise ValueError(f"User not found: {user_id}")

        async with self.uow:
            updated_user = await self.user_repo.update_profile(
                user_id=user_id,
                full_name=dto.full_name,
                timezone=dto.timezone,
            )
            await self.uow.commit()

        target_user = updated_user or user
        srl_profile = await self._load_srl_profile(user_id)
        return ProfileResponseDTO(
            id=str(target_user.id),
            email=target_user.email,
            full_name=dto.full_name,
            timezone=dto.timezone,
            role=target_user.role,
            tier=target_user.tier,
            created_at=(
                target_user.created_at.isoformat()
                if hasattr(target_user.created_at, "isoformat")
                else str(target_user.created_at)
            ),
            srl_profile=srl_profile,
        )

    async def get_profile(self, user_id: UUID) -> ProfileResponseDTO:
        user = await self.user_repo.find_by_id(user_id)
        if not user:
            raise ValueError(f"User not found: {user_id}")
        srl_profile = await self._load_srl_profile(user_id)
        return ProfileResponseDTO(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            timezone=user.timezone,
            role=user.role,
            tier=user.tier,
            created_at=(
                user.created_at.isoformat()
                if hasattr(user.created_at, "isoformat")
                else str(user.created_at)
            ),
            srl_profile=srl_profile,
        )


class GetProfileUseCase:
    """Retrieves current learner profile."""

    def __init__(
        self,
        user_repo: UserRepositoryPort,
        learner_profile_repo: LearnerProfileRepositoryPort | None = None,
    ) -> None:
        self.user_repo = user_repo
        self.learner_profile_repo = learner_profile_repo

    async def execute(self, user_id: UUID) -> ProfileResponseDTO:
        user = await self.user_repo.find_by_id(user_id)
        if not user:
            raise ValueError(f"User not found: {user_id}")
        srl_profile: LearnerSrlProfileDTO | None = None
        if self.learner_profile_repo is not None:
            record = await self.learner_profile_repo.get_by_user_id(user_id)
            srl_profile = _to_srl_profile_dto(record)
        return ProfileResponseDTO(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            timezone=user.timezone,
            role=user.role,
            tier=user.tier,
            created_at=(
                user.created_at.isoformat()
                if hasattr(user.created_at, "isoformat")
                else str(user.created_at)
            ),
            srl_profile=srl_profile,
        )
