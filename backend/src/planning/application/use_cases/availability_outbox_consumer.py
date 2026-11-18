from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from src.account.public_api import (
    AvailabilityQueryPort,
    CalendarConnectionQueryPort,
    UserQueryPort,
)
from src.execution.public_api import ExecutionScheduleSyncPort
from src.planning.application.ports.planning_repository_ports import (
    GoalRepositoryPort,
    MilestoneRepositoryPort,
    RoadmapRepositoryPort,
    ScheduleProposalRepositoryPort,
)
from src.planning.application.ports.schedule_block_repository_port import (
    ScheduleBlockRepositoryPort,
)
from src.planning.application.services.preliminary_feasibility_service import (
    refresh_roadmap_preliminary_feasibility,
)
from src.planning.domain.models.roadmap import RoadmapStatus
from src.shared_kernel.application.event_bus import OutboxRepositoryPort
from src.shared_kernel.application.uow import AsyncUnitOfWork


class HandleAvailabilityUpdatedEventUseCase:
    """Idempotent Planning Outbox consumer for `AvailabilityUpdatedEvent` (DEF-06)."""

    CONSUMER_NAME: str = "planning.availability_updated_consumer"

    def __init__(
        self,
        *,
        roadmap_repo: RoadmapRepositoryPort,
        milestone_repo: MilestoneRepositoryPort,
        proposal_repo: ScheduleProposalRepositoryPort,
        availability_query_port: AvailabilityQueryPort,
        outbox_repo: OutboxRepositoryPort,
        uow: AsyncUnitOfWork,
        goal_repo: GoalRepositoryPort | None = None,
        execution_sync_port: ExecutionScheduleSyncPort | None = None,
        block_repo: ScheduleBlockRepositoryPort | None = None,
        user_query_port: UserQueryPort | None = None,
        calendar_connection_query_port: CalendarConnectionQueryPort | None = None,
    ) -> None:
        self._roadmap_repo = roadmap_repo
        self._milestone_repo = milestone_repo
        self._proposal_repo = proposal_repo
        self._availability_port = availability_query_port
        self._outbox_repo = outbox_repo
        self._uow = uow
        self._goal_repo = goal_repo
        self._execution_sync_port = execution_sync_port
        self._block_repo = block_repo
        self._user_query_port = user_query_port
        self._calendar_connection_port = calendar_connection_query_port

    async def execute(
        self,
        *,
        event_id: UUID,
        user_id: UUID,
        now: datetime | None = None,
    ) -> int:
        effective_now = now or datetime.now(UTC)

        async with self._uow:
            if await self._outbox_repo.is_event_processed(event_id, self.CONSUMER_NAME):
                return 0

            roadmaps = await self._roadmap_repo.list_by_user_id(user_id)
            target_roadmaps = [
                r
                for r in roadmaps
                if r.status not in (RoadmapStatus.COMPLETED, RoadmapStatus.ARCHIVED)
            ]

            refreshed_count = 0
            for roadmap in target_roadmaps:
                milestones = await self._milestone_repo.list_by_roadmap_id(roadmap.id)
                if not milestones:
                    continue
                refresh_res = await refresh_roadmap_preliminary_feasibility(
                    user_id=user_id,
                    roadmap=roadmap,
                    milestones=milestones,
                    goal_repo=self._goal_repo,
                    roadmap_repo=self._roadmap_repo,
                    proposal_repo=None,
                    availability_query_port=self._availability_port,
                    execution_sync_port=self._execution_sync_port,
                    block_repo=self._block_repo,
                    user_query_port=self._user_query_port,
                    calendar_connection_query_port=self._calendar_connection_port,
                    force_recompute=False,
                    discard_drafts_on_change=False,
                    now=effective_now,
                )
                if refresh_res.drifted or refresh_res.roadmap_dirty:
                    await self._roadmap_repo.save(roadmap)
                    if refresh_res.milestones_dirty:
                        await self._milestone_repo.save_many(roadmap.id, milestones)
                    await self._proposal_repo.discard_existing_drafts(roadmap.id, effective_now)
                    refreshed_count += 1

            await self._outbox_repo.mark_event_processed(event_id, self.CONSUMER_NAME)
            await self._uow.commit()
            return refreshed_count
