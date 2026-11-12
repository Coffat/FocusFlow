from uuid import UUID

from src.account.application.dtos.learner_memory import (
    LearnerMemoryResponseDTO,
    UpdateLearnerMemoryRequestDTO,
)
from src.account.application.ports.learner_memory_repository_port import (
    LearnerMemoryRepositoryPort,
)
from src.account.domain.models.learner_memory import LearnerMemoryItem
from src.shared_kernel.application.uow import AsyncUnitOfWork


class LearnerMemoryNotFoundError(LookupError):
    pass


def _to_dto(item: LearnerMemoryItem) -> LearnerMemoryResponseDTO:
    return LearnerMemoryResponseDTO(
        id=item.id,
        memory_key=item.memory_key,
        value=item.value,
        category=item.category.value,
        epistemic_level=item.epistemic_level.value,
        confidence=item.confidence,
        sample_size=item.sample_size,
        evidence=list(item.evidence),
        status=item.status.value,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


class ListLearnerMemoryUseCase:
    def __init__(self, repository: LearnerMemoryRepositoryPort) -> None:
        self._repository = repository

    async def execute(self, user_id: UUID) -> list[LearnerMemoryResponseDTO]:
        return [_to_dto(item) for item in await self._repository.list_active(user_id)]


class UpdateLearnerMemoryUseCase:
    def __init__(self, repository: LearnerMemoryRepositoryPort, uow: AsyncUnitOfWork) -> None:
        self._repository = repository
        self._uow = uow

    async def execute(
        self, user_id: UUID, memory_id: UUID, request: UpdateLearnerMemoryRequestDTO
    ) -> LearnerMemoryResponseDTO:
        item = await self._repository.get_owned(memory_id, user_id)
        if item is None:
            raise LearnerMemoryNotFoundError
        if request.action == "confirm":
            updated = item.confirm()
        elif request.action == "reject":
            updated = item.reject()
        else:
            if request.value is None:
                raise ValueError("value is required for edit")
            updated = item.edit(request.value)
        await self._repository.save(updated)
        await self._uow.commit()
        return _to_dto(updated)


class ResetLearnerMemoryUseCase:
    def __init__(self, repository: LearnerMemoryRepositoryPort, uow: AsyncUnitOfWork) -> None:
        self._repository = repository
        self._uow = uow

    async def execute(self, user_id: UUID, *, confirmed: bool) -> None:
        if not confirmed:
            raise ValueError("explicit confirmation is required")
        await self._repository.reset_profile(user_id)
        await self._uow.commit()
