from datetime import UTC, date, datetime
from uuid import UUID

from src.account.public_api import UserQueryPort
from src.planning.application.dtos.planning_dtos import CreateGoalAndRoadmapResultDTO
from src.planning.application.ports.planning_repository_ports import (
    GoalRepositoryPort,
    RoadmapRepositoryPort,
)
from src.planning.domain.models.goal import Goal, GoalStatus
from src.planning.domain.models.roadmap import Roadmap, RoadmapStatus
from src.shared_kernel.application.uow import AsyncUnitOfWork
from src.shared_kernel.domain.base import generate_uuid7


class CreateGoalAndRoadmapUseCase:
    """Create a Learner Goal and an INITIALIZED Roadmap enforcing OS-02 active roadmap cap (UC-07)."""

    def __init__(
        self,
        *,
        goal_repo: GoalRepositoryPort,
        roadmap_repo: RoadmapRepositoryPort,
        uow: AsyncUnitOfWork,
        user_query_port: UserQueryPort | None = None,
    ) -> None:
        self._goal_repo = goal_repo
        self._roadmap_repo = roadmap_repo
        self._uow = uow
        self._user_query_port = user_query_port

    async def execute(
        self,
        *,
        user_id: UUID,
        title: str,
        description: str | None = None,
        goal_title: str | None = None,
        goal_description: str | None = None,
        start_date: date | None = None,
        target_date: date | None = None,
        tier: str | None = None,
        now: datetime | None = None,
    ) -> CreateGoalAndRoadmapResultDTO:
        effective_now = now or datetime.now(UTC)
        effective_tier = tier or "FREE"
        if tier is None and self._user_query_port is not None:
            user_snap = await self._user_query_port.get_user_by_id(user_id)
            if user_snap is not None:
                effective_tier = user_snap.tier

        active_count = await self._roadmap_repo.count_active_by_user_id(user_id)
        Roadmap.validate_active_limit(
            tier=effective_tier,
            current_active_count=active_count,
        )

        effective_goal_title = (goal_title or title).strip()
        effective_goal_desc = (
            goal_description
            if goal_description is not None
            else (description if description is not None else effective_goal_title)
        )
        effective_start_date = start_date or effective_now.date()

        goal = Goal(
            id=generate_uuid7(),
            user_id=user_id,
            title=effective_goal_title,
            raw_description=effective_goal_desc,
            target_date=target_date,
            status=GoalStatus.ACTIVE,
            created_at=effective_now,
            updated_at=effective_now,
        )
        roadmap = Roadmap(
            id=generate_uuid7(),
            user_id=user_id,
            goal_id=goal.id,
            title=title.strip(),
            description=description,
            status=RoadmapStatus.INITIALIZED,
            start_date=effective_start_date,
            target_date=target_date,
            created_at=effective_now,
            updated_at=effective_now,
        )

        async with self._uow:
            saved_goal = await self._goal_repo.save(goal)
            saved_roadmap = await self._roadmap_repo.save(roadmap)
            await self._uow.commit()

        return CreateGoalAndRoadmapResultDTO(
            goal=saved_goal,
            roadmap=saved_roadmap,
        )
