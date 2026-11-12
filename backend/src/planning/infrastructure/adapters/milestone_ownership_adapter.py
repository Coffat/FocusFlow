from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.planning.infrastructure.orm.planning_orm import MilestoneORM, RoadmapORM
from src.planning.public_api import (
    MilestoneOwnershipDTO,
    MilestoneOwnershipQueryPort,
    register_milestone_ownership_factory,
)


class MilestoneOwnershipAdapter(MilestoneOwnershipQueryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_milestone(self, milestone_id: UUID) -> MilestoneOwnershipDTO | None:
        result = await self._session.execute(
            select(MilestoneORM, RoadmapORM.user_id)
            .join(RoadmapORM, RoadmapORM.id == MilestoneORM.roadmap_id)
            .where(MilestoneORM.id == milestone_id)
        )
        row = result.one_or_none()
        if row is None:
            return None
        milestone, user_id = row
        return MilestoneOwnershipDTO(
            milestone_id=milestone.id,
            roadmap_id=milestone.roadmap_id,
            user_id=user_id,
            title=milestone.title,
        )

    async def roadmap_belongs_to(self, roadmap_id: UUID, user_id: UUID) -> bool:
        result = await self._session.execute(
            select(RoadmapORM.id).where(
                RoadmapORM.id == roadmap_id,
                RoadmapORM.user_id == user_id,
            )
        )
        return result.scalar_one_or_none() is not None


def _factory(session: AsyncSession) -> MilestoneOwnershipQueryPort:
    return MilestoneOwnershipAdapter(session)


register_milestone_ownership_factory(_factory)
