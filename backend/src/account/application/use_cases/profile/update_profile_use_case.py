from uuid import UUID

from src.account.application.dtos.profile import (
    ProfileResponseDTO,
    UpdateProfileRequestDTO,
)
from src.account.application.ports.user_repository_port import UserRepositoryPort
from src.shared_kernel.application.uow import AsyncUnitOfWork


class UpdateProfileUseCase:
    """Updates learner profile information (full_name and IANA timezone)."""

    def __init__(self, user_repo: UserRepositoryPort, uow: AsyncUnitOfWork) -> None:
        self.user_repo = user_repo
        self.uow = uow

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
        )

    async def get_profile(self, user_id: UUID) -> ProfileResponseDTO:
        user = await self.user_repo.find_by_id(user_id)
        if not user:
            raise ValueError(f"User not found: {user_id}")
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
        )


class GetProfileUseCase:
    """Retrieves current learner profile."""

    def __init__(self, user_repo: UserRepositoryPort) -> None:
        self.user_repo = user_repo

    async def execute(self, user_id: UUID) -> ProfileResponseDTO:
        user = await self.user_repo.find_by_id(user_id)
        if not user:
            raise ValueError(f"User not found: {user_id}")
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
        )
