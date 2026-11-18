from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from src.account.public_api import (
    AvailabilityQueryPort,
    CalendarConnectionQueryPort,
    UserQueryPort,
)
from src.evaluation.public_api import ScheduleChangeLogPort
from src.execution.public_api import ExecutionScheduleSyncPort
from src.planning.application.dtos.planning_dtos import RoadmapDetailDTO
from src.planning.application.ports.planning_repository_ports import (
    GoalRepositoryPort,
    MilestoneRepositoryPort,
    OfficialScheduleRepositoryPort,
    RoadmapRepositoryPort,
    ScheduleProposalRepositoryPort,
)
from src.planning.application.ports.schedule_block_repository_port import (
    ScheduleBlockRepositoryPort,
)
from src.planning.application.services.existing_schedule_occupancy import (
    expand_existing_schedule_occupancy,
)
from src.planning.application.services.preliminary_feasibility_service import (
    refresh_roadmap_preliminary_feasibility,
)
from src.planning.application.services.repo_lock import call_for_update
from src.planning.domain.exceptions.planning_exceptions import (
    FreshCalendarConflictDetectedError,
    RoadmapNotFoundError,
)
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
        milestone_repo: MilestoneRepositoryPort | None = None,
        proposal_repo: ScheduleProposalRepositoryPort | None = None,
        availability_query_port: AvailabilityQueryPort | None = None,
        execution_sync_port: ExecutionScheduleSyncPort | None = None,
        block_repo: ScheduleBlockRepositoryPort | None = None,
        calendar_connection_query_port: CalendarConnectionQueryPort | None = None,
    ) -> None:
        self._goal_repo = goal_repo
        self._roadmap_repo = roadmap_repo
        self._uow = uow
        self._user_query_port = user_query_port
        self._milestone_repo = milestone_repo
        self._proposal_repo = proposal_repo
        self._availability_port = availability_query_port
        self._execution_sync_port = execution_sync_port
        self._block_repo = block_repo
        self._calendar_connection_port = calendar_connection_query_port

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

        prev_title = roadmap.title
        prev_start = roadmap.start_date
        prev_target = roadmap.target_date

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

        dates_or_title_changed = (
            roadmap.title != prev_title
            or roadmap.start_date != prev_start
            or roadmap.target_date != prev_target
        )

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

        goal = await self._goal_repo.get_by_id(roadmap.goal_id)
        if goal is not None and (target_date is not None or (title is not None and title.strip())):
            if title is not None and title.strip():
                goal.title = title.strip()
            if target_date is not None:
                goal.target_date = target_date
            goal.updated_at = effective_now

        milestones = (
            await self._milestone_repo.list_by_roadmap_id(roadmap_id)
            if (dates_or_title_changed and self._milestone_repo is not None)
            else []
        )
        refresh_res = None
        if dates_or_title_changed and milestones:
            refresh_res = await refresh_roadmap_preliminary_feasibility(
                user_id=user_id,
                roadmap=roadmap,
                milestones=milestones,
                goal=goal,
                goal_repo=self._goal_repo,
                roadmap_repo=self._roadmap_repo,
                proposal_repo=None,
                availability_query_port=self._availability_port,
                execution_sync_port=self._execution_sync_port,
                block_repo=self._block_repo,
                user_query_port=self._user_query_port,
                calendar_connection_query_port=self._calendar_connection_port,
                force_recompute=(roadmap.start_date != prev_start),
                discard_drafts_on_change=False,
                now=effective_now,
            )

        async with self._uow:
            saved_roadmap = await self._roadmap_repo.save(roadmap)
            if goal is not None and (
                target_date is not None or (title is not None and title.strip())
            ):
                await self._goal_repo.save(goal)
            if (
                refresh_res is not None
                and refresh_res.milestones_dirty
                and self._milestone_repo is not None
            ):
                await self._milestone_repo.save_many(roadmap_id, milestones)
            if self._proposal_repo is not None and (
                dates_or_title_changed or (refresh_res is not None and refresh_res.drifted)
            ):
                await self._proposal_repo.discard_existing_drafts(roadmap_id, effective_now)
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


class PauseRoadmapUseCase:
    """Pause an ACTIVE Roadmap (`ACTIVE -> PAUSED`) and log event (`UC-22`)."""

    def __init__(
        self,
        *,
        roadmap_repo: RoadmapRepositoryPort,
        schedule_repo: OfficialScheduleRepositoryPort,
        uow: AsyncUnitOfWork,
        schedule_change_log_port: ScheduleChangeLogPort | None = None,
    ) -> None:
        self._roadmap_repo = roadmap_repo
        self._schedule_repo = schedule_repo
        self._uow = uow
        self._change_log_port = schedule_change_log_port

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

        roadmap.pause(effective_now)
        schedule = await self._schedule_repo.get_by_roadmap_id(roadmap_id)

        async with self._uow:
            saved_roadmap = await self._roadmap_repo.save(roadmap)
            if self._change_log_port is not None:
                await self._change_log_port.record_change_log(
                    roadmap_id=roadmap_id,
                    schedule_id=schedule.id if schedule is not None else None,
                    trigger_type="ROADMAP_PAUSED",
                    reason="Tạm dừng lộ trình học tập theo yêu cầu người học (UC-22)",
                    affected_tasks_count=0,
                    total_shifted_minutes=0,
                    diff_payload={"paused_at": effective_now.isoformat()},
                    now=effective_now,
                )
            await self._uow.commit()

        return saved_roadmap


class ResumeRoadmapUseCase:
    """Resume a PAUSED Roadmap (`PAUSED -> ACTIVE`) applying Domino Shift without increasing `reschedule_count` (`UC-22`)."""

    def __init__(
        self,
        *,
        goal_repo: GoalRepositoryPort,
        roadmap_repo: RoadmapRepositoryPort,
        schedule_repo: OfficialScheduleRepositoryPort,
        uow: AsyncUnitOfWork,
        execution_sync_port: ExecutionScheduleSyncPort | None = None,
        block_repo: ScheduleBlockRepositoryPort | None = None,
        user_query_port: UserQueryPort | None = None,
        schedule_change_log_port: ScheduleChangeLogPort | None = None,
    ) -> None:
        self._goal_repo = goal_repo
        self._roadmap_repo = roadmap_repo
        self._schedule_repo = schedule_repo
        self._uow = uow
        self._execution_sync_port = execution_sync_port
        self._block_repo = block_repo
        self._user_query_port = user_query_port
        self._change_log_port = schedule_change_log_port

    async def execute(
        self,
        *,
        user_id: UUID,
        roadmap_id: UUID,
        shift_days: int | None = None,
        now: datetime | None = None,
    ) -> Roadmap:
        effective_now = now or datetime.now(UTC)

        effective_tier = "FREE"
        if self._user_query_port is not None:
            snap = await self._user_query_port.get_user_by_id(user_id)
            if snap is not None:
                effective_tier = snap.tier

        async with self._uow:
            locked_roadmaps = await call_for_update(self._roadmap_repo.list_by_user_id, user_id)
            roadmap = next((r for r in locked_roadmaps if r.id == roadmap_id), None)
            if roadmap is None:
                roadmap = await call_for_update(
                    self._roadmap_repo.get_by_id_for_user, roadmap_id, user_id
                )
            if roadmap is None:
                raise RoadmapNotFoundError()

            paused_at = roadmap.updated_at if roadmap.updated_at != datetime.min else effective_now
            effective_shift_days = (
                max(0, int(shift_days))
                if shift_days is not None
                else max(1, (effective_now.date() - paused_at.date()).days)
            )

            if locked_roadmaps:
                other_active = [
                    r
                    for r in locked_roadmaps
                    if r.id != roadmap_id and r.status == RoadmapStatus.ACTIVE
                ]
                active_count = len(other_active)
            else:
                active_count = await self._roadmap_repo.count_active_by_user_id(
                    user_id,
                    exclude_roadmap_id=roadmap_id,
                )
                active_list = await self._roadmap_repo.list_by_user_id(user_id, status="ACTIVE")
                other_active = [r for r in active_list if r.id != roadmap_id]

            roadmap.activate(
                effective_now,
                tier=effective_tier,
                current_active_count=active_count,
            )

            schedule = await call_for_update(self._schedule_repo.get_by_roadmap_id, roadmap_id)
            delta = timedelta(days=effective_shift_days)
            planned_blocks = []
            if self._block_repo is not None and schedule is not None:
                all_blocks = await call_for_update(self._block_repo.get_by_schedule_id, schedule.id)
                planned_blocks = [b for b in all_blocks if b.status == "PLANNED"]

            if other_active and self._execution_sync_port is not None:
                candidate_intervals: list[tuple[str, datetime, datetime]] = []
                if planned_blocks:
                    for blk in planned_blocks:
                        candidate_intervals.append(
                            (
                                str(blk.task_id or blk.id),
                                blk.start_time + delta,
                                blk.end_time + delta,
                            )
                        )
                else:
                    own_tasks = await self._execution_sync_port.get_tasks_for_roadmaps([roadmap_id])
                    for t in own_tasks:
                        if (
                            t.status != "COMPLETED"
                            and t.scheduled_start is not None
                            and t.scheduled_end is not None
                        ):
                            candidate_intervals.append(
                                (
                                    str(t.task_id),
                                    t.scheduled_start + delta,
                                    t.scheduled_end + delta,
                                )
                            )

                if candidate_intervals:
                    other_ids = [r.id for r in other_active]
                    target_dates = {r.id: r.target_date for r in other_active}
                    other_tasks = await self._execution_sync_port.get_tasks_for_roadmaps(
                        other_ids,
                        roadmap_target_dates=target_dates,
                    )
                    if self._block_repo is not None:
                        other_tasks = expand_existing_schedule_occupancy(
                            other_tasks,
                            await self._block_repo.list_by_roadmap_ids(other_ids),
                        )
                    conflicts: list[dict[str, object]] = []
                    for cand_id, c_start, c_end in candidate_intervals:
                        for ot in other_tasks:
                            if ot.scheduled_start is None or ot.scheduled_end is None:
                                continue
                            if c_start < ot.scheduled_end and ot.scheduled_start < c_end:
                                conflicts.append(
                                    {
                                        "task_id": cand_id,
                                        "scheduled_start": c_start.isoformat(),
                                        "scheduled_end": c_end.isoformat(),
                                        "conflict_source": "ACTIVE_ROADMAP_SLOT_CONFLICT",
                                        "conflict_start": ot.scheduled_start.isoformat(),
                                        "conflict_end": ot.scheduled_end.isoformat(),
                                    }
                                )
                    if conflicts:
                        raise FreshCalendarConflictDetectedError(conflicts=conflicts)

            if effective_shift_days > 0 and roadmap.target_date is not None:
                roadmap.target_date = roadmap.target_date + delta

            shifted_tasks_count = 0
            saved_roadmap = await self._roadmap_repo.save(roadmap)
            if effective_shift_days > 0:
                goal = await self._goal_repo.get_by_id(roadmap.goal_id)
                if goal is not None and goal.target_date is not None:
                    goal.target_date = goal.target_date + delta
                    goal.updated_at = effective_now
                    await self._goal_repo.save(goal)

                if self._execution_sync_port is not None:
                    shifted_tasks_count = (
                        await self._execution_sync_port.shift_incomplete_tasks_for_domino(
                            roadmap_id=roadmap_id,
                            shift_days=effective_shift_days,
                            now=effective_now,
                        )
                    )

                if planned_blocks and self._block_repo is not None:
                    for blk in planned_blocks:
                        blk.block_date = blk.block_date + delta
                        blk.start_time = blk.start_time + delta
                        blk.end_time = blk.end_time + delta
                        blk.sync_status = "PENDING_SYNC"
                        blk.updated_at = effective_now
                    await self._block_repo.save_all(planned_blocks)

            if self._change_log_port is not None:
                await self._change_log_port.record_change_log(
                    roadmap_id=roadmap_id,
                    schedule_id=schedule.id if schedule is not None else None,
                    trigger_type="DOMINO_SHIFT",
                    reason=(
                        f"Kích hoạt lại lộ trình và dịch Domino {effective_shift_days} ngày "
                        "không tăng reschedule_count (UC-22)"
                    ),
                    affected_tasks_count=shifted_tasks_count,
                    total_shifted_minutes=effective_shift_days * 60,
                    diff_payload={
                        "shift_days": effective_shift_days,
                        "shifted_tasks_count": shifted_tasks_count,
                    },
                    now=effective_now,
                )
            await self._uow.commit()

        return saved_roadmap
