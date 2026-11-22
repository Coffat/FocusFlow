from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.planning.infrastructure.orm.planning_orm import (
    LearningConceptORM,
    ScheduleProposalORM,
)
from src.planning.public_api import (
    PlanningReadQueryPort,
    register_planning_read_query_factory,
)


class PlanningReadQueryAdapter(PlanningReadQueryPort):
    """Read-only SQLAlchemy query adapter exposed by Planning via public_api."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def filter_existing_concept_ids(
        self,
        concept_ids: Sequence[str],
    ) -> set[str]:
        cleaned = [cid for cid in concept_ids if cid]
        if not cleaned:
            return set()

        stmt = select(LearningConceptORM.concept_id).where(
            LearningConceptORM.concept_id.in_(cleaned)
        )
        rows = (await self._session.execute(stmt)).fetchall()
        return {str(row[0]) for row in rows}

    async def get_latest_applied_proposal_data(
        self,
        roadmap_id: UUID,
        *,
        limit: int = 3,
    ) -> list[dict[str, Any]]:
        stmt = (
            select(ScheduleProposalORM.proposal_data)
            .where(
                ScheduleProposalORM.roadmap_id == roadmap_id,
                ScheduleProposalORM.status.in_(("APPLIED", "DRAFT")),
            )
            .order_by(
                case((ScheduleProposalORM.status == "APPLIED", 0), else_=1),
                ScheduleProposalORM.applied_at.desc().nulls_last(),
                ScheduleProposalORM.updated_at.desc(),
            )
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).fetchall()
        return [row[0] for row in rows if isinstance(row[0], dict)]


def _planning_read_query_factory_impl(session: AsyncSession) -> PlanningReadQueryPort:
    return PlanningReadQueryAdapter(session)


register_planning_read_query_factory(_planning_read_query_factory_impl)
