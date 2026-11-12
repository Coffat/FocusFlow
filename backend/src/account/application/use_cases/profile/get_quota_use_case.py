from uuid import UUID

from src.account.application.dtos.profile import AIQuotaResponseDTO
from src.account.application.ports.user_repository_port import UserRepositoryPort
from src.shared_kernel.application.uow import AsyncUnitOfWork


class GetQuotaUseCase:
    """Retrieves or initializes the learner's AI Quota status."""

    def __init__(self, user_repo: UserRepositoryPort, uow: AsyncUnitOfWork) -> None:
        self.user_repo = user_repo
        self.uow = uow

    async def execute(self, user_id: UUID) -> AIQuotaResponseDTO:
        user = await self.user_repo.find_by_id(user_id)
        if not user:
            raise ValueError(f"User not found: {user_id}")

        quota = await self.user_repo.get_quota_by_user_id(user_id)
        if quota is None:
            tier = getattr(user, "tier", "FREE")
            async with self.uow:
                quota = await self.user_repo.create_or_init_quota(user_id, tier=tier)
                await self.uow.commit()

        remaining_calls = max(0, quota.monthly_limit - quota.used_calls - quota.reserved_calls)
        cycle_start_str = (
            quota.cycle_start.isoformat()
            if hasattr(quota.cycle_start, "isoformat")
            else str(quota.cycle_start)
        )
        cycle_end_str = (
            quota.cycle_end.isoformat()
            if hasattr(quota.cycle_end, "isoformat")
            else str(quota.cycle_end)
        )

        return AIQuotaResponseDTO(
            monthly_limit=quota.monthly_limit,
            used_calls=quota.used_calls,
            reserved_calls=quota.reserved_calls,
            remaining_calls=remaining_calls,
            tokens_consumed=quota.tokens_consumed,
            cycle_start=cycle_start_str,
            cycle_end=cycle_end_str,
        )
