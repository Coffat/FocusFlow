from datetime import UTC, date, datetime
from uuid import UUID

from src.account.public_api import UserQueryPort
from src.execution.public_api import ExecutionScheduleSyncPort
from src.planning.application.dtos.planning_dtos import RoadmapDetailDTO
from src.planning.application.ports.planning_repository_ports import (
    GoalRepositoryPort,
    MilestoneRepositoryPort,
    OfficialScheduleRepositoryPort,
    RoadmapRepositoryPort,
    ScheduleProposalRepositoryPort,
)
from src.planning.domain.exceptions.planning_exceptions import RoadmapNotFoundError
from src.planning.domain.models.roadmap import Roadmap, RoadmapStatus
from src.shared_kernel.application.uow import AsyncUnitOfWork


class ListRoadmapsUseCase:
    """List roadmaps belonging to a learner with optional status filter (UC-10)."""

    def __init__(self, *, roadmap_repo: RoadmapRepositoryPort) -> None:
        self._roadmap_repo = roadmap_repo

    async def execute(
        self,
        *,
        user_id: UUID,
        status: str | None = None,
    ) -> list[Roadmap]:
        return await self._roadmap_repo.list_by_user_id(user_id, status=status)


class GetRoadmapDetailUseCase:
    """Retrieve full Roadmap details including Goal, Milestones, OfficialSchedule, Tasks & Draft Proposal (UC-10)."""

    def __init__(
        self,
        *,
        goal_repo: GoalRepositoryPort,
        roadmap_repo: RoadmapRepositoryPort,
        milestone_repo: MilestoneRepositoryPort,
        schedule_repo: OfficialScheduleRepositoryPort,
        proposal_repo: ScheduleProposalRepositoryPort,
        execution_sync_port: ExecutionScheduleSyncPort | None = None,
    ) -> None:
        self._goal_repo = goal_repo
        self._roadmap_repo = roadmap_repo
        self._milestone_repo = milestone_repo
        self._schedule_repo = schedule_repo
        self._proposal_repo = proposal_repo
        self._execution_sync_port = execution_sync_port

    async def execute(
        self,
        *,
        user_id: UUID,
        roadmap_id: UUID,
    ) -> RoadmapDetailDTO:
        roadmap = await self._roadmap_repo.get_by_id_for_user(roadmap_id, user_id)
        if roadmap is None:
            raise RoadmapNotFoundError()

        goal = await self._goal_repo.get_by_id(roadmap.goal_id)
        milestones = await self._milestone_repo.list_by_roadmap_id(roadmap_id)
        official_schedule = await self._schedule_repo.get_by_roadmap_id(roadmap_id)
        current_draft = await self._proposal_repo.get_current_draft(roadmap_id)
        scheduled_tasks = (
            await self._execution_sync_port.get_tasks_for_roadmaps(
                [roadmap_id],
                roadmap_target_dates={roadmap_id: roadmap.target_date},
            )
            if self._execution_sync_port is not None
            else []
        )

        return RoadmapDetailDTO(
            roadmap=roadmap,
            goal=goal,
            milestones=milestones,
            official_schedule=official_schedule,
            current_draft_proposal=current_draft,
            scheduled_tasks=scheduled_tasks,
        )


class UpdateRoadmapUseCase:
    """Update metadata or status of a learner's Roadmap enforcing state transitions & OS-02 (UC-10)."""

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
        roadmap_id: UUID,
        title: str | None = None,
        description: str | None = None,
        start_date: date | None = None,
        target_date: date | None = None,
        status: str | None = None,
        tier: str | None = None,
        now: datetime | None = None,
    ) -> Roadmap:
        effective_now = now or datetime.now(UTC)
        roadmap = await self._roadmap_repo.get_by_id_for_user(roadmap_id, user_id)
        if roadmap is None:
            raise RoadmapNotFoundError()

        if title is not None and title.strip():
            roadmap.title = title.strip()
        if description is not None:
            roadmap.description = description
        if start_date is not None:
            roadmap.start_date = start_date
        if target_date is not None:
            roadmap.target_date = target_date

        # Re-validate date range invariant
        roadmap.__post_init__()
        roadmap.updated_at = effective_now

        if status is not None:
            target_status = RoadmapStatus(status.strip().upper())
            if target_status != roadmap.status:
                if target_status == RoadmapStatus.ACTIVE:
                    effective_tier = tier or "FREE"
                    if tier is None and self._user_query_port is not None:
                        snap = await self._user_query_port.get_user_by_id(user_id)
                        if snap is not None:
                            effective_tier = snap.tier
                    active_count = await self._roadmap_repo.count_active_by_user_id(
                        user_id,
                        exclude_roadmap_id=roadmap_id,
                    )
                    roadmap.activate(
                        effective_now,
                        tier=effective_tier,
                        current_active_count=active_count,
                    )
                elif target_status == RoadmapStatus.PAUSED:
                    roadmap.pause(effective_now)
                elif target_status == RoadmapStatus.COMPLETED:
                    roadmap.complete(effective_now)
                elif target_status == RoadmapStatus.ARCHIVED:
                    roadmap.archive(effective_now)

        async with self._uow:
            saved_roadmap = await self._roadmap_repo.save(roadmap)
            if target_date is not None or title is not None:
                goal = await self._goal_repo.get_by_id(roadmap.goal_id)
                if goal is not None:
                    if title is not None and title.strip():
                        goal.title = title.strip()
                    if target_date is not None:
                        goal.target_date = target_date
                    goal.updated_at = effective_now
                    await self._goal_repo.save(goal)
            await self._uow.commit()

        return saved_roadmap


class ArchiveRoadmapUseCase:
    """Archive a Roadmap (INITIALIZED | ACTIVE | PAUSED -> ARCHIVED) (UC-10)."""

    def __init__(
        self,
        *,
        goal_repo: GoalRepositoryPort,
        roadmap_repo: RoadmapRepositoryPort,
        uow: AsyncUnitOfWork,
    ) -> None:
        self._goal_repo = goal_repo
        self._roadmap_repo = roadmap_repo
        self._uow = uow

    async def execute(
        self,
        *,
        user_id: UUID,
        roadmap_id: UUID,
        now: datetime | None = None,
    ) -> Roadmap:
        effective_now = now or datetime.now(UTC)
        roadmap = await self._roadmap_repo.get_by_id_for_user(roadmap_id, user_id)
        if roadmap is None:
            raise RoadmapNotFoundError()

        roadmap.archive(effective_now)

        async with self._uow:
            saved_roadmap = await self._roadmap_repo.save(roadmap)
            goal = await self._goal_repo.get_by_id(roadmap.goal_id)
            if goal is not None:
                goal.archive(effective_now)
                await self._goal_repo.save(goal)
            await self._uow.commit()

        return saved_roadmap
