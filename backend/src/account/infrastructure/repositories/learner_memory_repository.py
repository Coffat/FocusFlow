from decimal import Decimal
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.account.application.ports.learner_memory_repository_port import (
    LearnerMemoryRepositoryPort,
)
from src.account.domain.models.learner_memory import (
    LearnerMemoryItem,
    MemoryCategory,
    MemoryEpistemicLevel,
    MemoryStatus,
)
from src.account.infrastructure.orm.learner_memory_orm import (
    LearnerConceptMasteryORM,
    LearnerMemoryItemORM,
)
from src.account.infrastructure.orm.user_orm import LearnerProfileORM


def _to_domain(row: LearnerMemoryItemORM) -> LearnerMemoryItem:
    return LearnerMemoryItem(
        id=row.id,
        user_id=row.user_id,
        memory_key=row.memory_key,
        value=row.value,
        category=MemoryCategory(row.category),
        epistemic_level=MemoryEpistemicLevel(row.epistemic_level),
        confidence=row.confidence,
        sample_size=row.sample_size,
        evidence=tuple(row.evidence),
        observation_started_at=row.observation_started_at,
        observation_ended_at=row.observation_ended_at,
        status=MemoryStatus(row.status),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlAlchemyLearnerMemoryRepository(LearnerMemoryRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_active(self, user_id: UUID) -> list[LearnerMemoryItem]:
        result = await self._session.execute(
            select(LearnerMemoryItemORM)
            .where(
                LearnerMemoryItemORM.user_id == user_id,
                LearnerMemoryItemORM.status != MemoryStatus.REJECTED.value,
            )
            .order_by(LearnerMemoryItemORM.category, LearnerMemoryItemORM.memory_key)
        )
        return [_to_domain(row) for row in result.scalars()]

    async def get_owned(self, memory_id: UUID, user_id: UUID) -> LearnerMemoryItem | None:
        result = await self._session.execute(
            select(LearnerMemoryItemORM).where(
                LearnerMemoryItemORM.id == memory_id,
                LearnerMemoryItemORM.user_id == user_id,
            )
        )
        row = result.scalar_one_or_none()
        return _to_domain(row) if row else None

    async def save(self, item: LearnerMemoryItem) -> LearnerMemoryItem:
        row = await self._session.get(LearnerMemoryItemORM, item.id)
        if row is None:
            row = LearnerMemoryItemORM(id=item.id, user_id=item.user_id, memory_key=item.memory_key)
            self._session.add(row)
        row.value = item.value
        row.category = item.category.value
        row.epistemic_level = item.epistemic_level.value
        row.confidence = item.confidence
        row.sample_size = item.sample_size
        row.evidence = list(item.evidence)
        row.observation_started_at = item.observation_started_at
        row.observation_ended_at = item.observation_ended_at
        row.status = item.status.value
        row.created_at = item.created_at
        row.updated_at = item.updated_at
        await self._session.flush()
        return item

    async def has_rejected_key(self, user_id: UUID, memory_key: str) -> bool:
        result = await self._session.execute(
            select(LearnerMemoryItemORM.id).where(
                LearnerMemoryItemORM.user_id == user_id,
                LearnerMemoryItemORM.memory_key == memory_key,
                LearnerMemoryItemORM.status == MemoryStatus.REJECTED.value,
            )
        )
        return result.scalar_one_or_none() is not None

    async def reset_profile(self, user_id: UUID) -> None:
        await self._session.execute(
            delete(LearnerMemoryItemORM).where(LearnerMemoryItemORM.user_id == user_id)
        )
        await self._session.execute(
            delete(LearnerConceptMasteryORM).where(LearnerConceptMasteryORM.user_id == user_id)
        )
        result = await self._session.execute(
            select(LearnerProfileORM).where(LearnerProfileORM.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        if profile is not None:
            profile.optimal_focus_duration_mins = 45
            profile.peak_productivity_slots = {}
            profile.estimation_bias_factor = Decimal("1.00")
            profile.weekly_completion_rate = Decimal("0.00")
            profile.total_completed_sessions = 0
            profile.is_cold_start = True
            profile.last_aggregated_at = None
        await self._session.flush()
