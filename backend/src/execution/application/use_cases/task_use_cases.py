from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from src.account.public_api import UserQueryPort
from src.evaluation.public_api import ScheduleChangeLogPort
from src.execution.application.dtos.execution_dtos import (
    TaskViewDTO,
    WeeklyScheduleItemDTO,
    WeeklyScheduleViewDTO,
)
from src.execution.application.ports.task_repository_port import TaskRepositoryPort
from src.execution.domain.exceptions.execution_exceptions import (
    ExecutionDomainError,
    InvalidTaskStateError,
    RoadmapReadOnlyError,
    ScheduleSlotConflictError,
    TaskBlockedError,
    TaskHasActiveSuccessorsError,
    TaskNotFoundError,
)
from src.execution.domain.models.study_session import (
    AlignmentFlag,
    NoteType,
    StudyNote,
    VerificationStatus,
)
from src.execution.domain.models.task import Task, TaskDependency, TaskStatus
from src.execution.domain.services.backlog_priority_ranker import BacklogPriorityRanker
from src.execution.domain.services.dag_cycle_validator import (
    DagCycleValidator,
    DagDependencyEdge,
    DagTaskNode,
)
from src.execution.domain.services.takeaway_guard import TakeawayGuard
from src.planning.public_api import MilestoneExecutionContextDTO, PlanningExecutionBridgePort
from src.shared_kernel.application.uow import AsyncUnitOfWork
from src.shared_kernel.domain.base import generate_uuid7
from src.shared_kernel.domain.exceptions import DomainError


def _resolve_tz(tz_name: str | None) -> ZoneInfo:
    raw = (tz_name or "").strip()
    if not raw:
        return ZoneInfo("Asia/Ho_Chi_Minh")
    try:
        return ZoneInfo(raw)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


async def _resolve_user_today(
    user_query_port: UserQueryPort | None,
    user_id: UUID,
    now: datetime,
) -> date:
    tz_name = "Asia/Ho_Chi_Minh"
    if user_query_port is not None:
        user_snap = await user_query_port.get_user_by_id(user_id)
        if user_snap is not None and user_snap.timezone:
            tz_name = user_snap.timezone
    user_tz = _resolve_tz(tz_name)
    ref_now = now if now.tzinfo is not None else now.replace(tzinfo=UTC)
    return ref_now.astimezone(user_tz).date()


def _build_task_views(
    tasks: Sequence[Task],
    dependencies: Sequence[TaskDependency],
    *,
    today: date,
    roadmap_titles: dict[UUID, str] | None = None,
    all_roadmap_tasks: Sequence[Task] | None = None,
    milestones_context: Mapping[UUID, MilestoneExecutionContextDTO] | None = None,
) -> list[TaskViewDTO]:
    status_source = all_roadmap_tasks if all_roadmap_tasks is not None else tasks
    status_by_id: dict[UUID, TaskStatus] = {t.id: t.status for t in status_source}
    preds_by_succ: dict[UUID, list[TaskDependency]] = {}
    for dep in dependencies:
        preds_by_succ.setdefault(dep.successor_id, []).append(dep)

    views: list[TaskViewDTO] = []
    for task in tasks:
        deps = preds_by_succ.get(task.id, [])
        pred_ids = tuple(d.predecessor_id for d in deps)
        is_blocked = any(
            status_by_id.get(d.predecessor_id) != TaskStatus.COMPLETED
            for d in deps
            if d.is_mandatory and d.predecessor_id in status_by_id
        )
        ms_ctx = milestones_context.get(task.milestone_id) if milestones_context else None
        views.append(
            TaskViewDTO(
                task=task,
                is_overdue=task.is_overdue(today),
                is_blocked=is_blocked,
                is_stalled=task.is_stalled(),
                predecessor_ids=pred_ids,
                milestone_sequence=ms_ctx.sequence_order if ms_ctx else None,
                roadmap_title=roadmap_titles.get(task.roadmap_id) if roadmap_titles else None,
                milestone_title=ms_ctx.title if ms_ctx else None,
                learning_outcomes=ms_ctx.learning_outcomes if ms_ctx else (),
                completion_criteria=ms_ctx.completion_criteria if ms_ctx else None,
            )
        )
    return views


async def _verify_writable_for_task(
    bridge: PlanningExecutionBridgePort,
    user_id: UUID,
    roadmap_id: UUID,
) -> date | None:
    try:
        return await bridge.verify_roadmap_writable(user_id, roadmap_id)
    except DomainError as exc:
        if exc.code == "ROADMAP_NOT_FOUND":
            raise TaskNotFoundError() from exc
        if exc.code == "ROADMAP_READ_ONLY":
            raise RoadmapReadOnlyError(exc.message) from exc
        raise


class ListTasksUseCase:
    """List tasks for a learner with derived OVERDUE/BLOCKED/STALLED flags & predecessors."""

    def __init__(
        self,
        *,
        task_repo: TaskRepositoryPort,
        planning_bridge: PlanningExecutionBridgePort,
        user_query_port: UserQueryPort | None = None,
    ) -> None:
        self._task_repo = task_repo
        self._bridge = planning_bridge
        self._user_query_port = user_query_port

    async def execute(
        self,
        *,
        user_id: UUID,
        roadmap_id: UUID | None = None,
        status: str | None = None,
        now: datetime | None = None,
    ) -> list[TaskViewDTO]:
        effective_now = now or datetime.now(UTC)
        roadmaps = await self._bridge.get_user_roadmaps_context(user_id, roadmap_id=roadmap_id)
        if roadmap_id is not None and not roadmaps:
            raise TaskNotFoundError("Không tìm thấy lộ trình học tập.")
        if not roadmaps:
            return []

        rids = [r.roadmap_id for r in roadmaps]
        title_map = {r.roadmap_id: r.title for r in roadmaps}
        all_tasks = await self._task_repo.list_by_roadmap_ids(rids)
        deps = await self._task_repo.list_dependencies_by_roadmap_ids(rids)
        milestones_context = await self._bridge.get_milestones_context(rids)
        today = await _resolve_user_today(self._user_query_port, user_id, effective_now)

        filtered = all_tasks
        if status is not None and status.strip():
            norm_status = status.strip().upper()
            filtered = [t for t in all_tasks if t.status.value == norm_status]

        return _build_task_views(
            filtered,
            deps,
            today=today,
            roadmap_titles=title_map,
            all_roadmap_tasks=all_tasks,
            milestones_context=milestones_context,
        )


class CreateManualTaskUseCase:
    """Create a manual task (15..240 min) with optional Tier 2 slot validation (FR-TASK-001)."""

    def __init__(
        self,
        *,
        task_repo: TaskRepositoryPort,
        planning_bridge: PlanningExecutionBridgePort,
        uow: AsyncUnitOfWork,
        user_query_port: UserQueryPort | None = None,
    ) -> None:
        self._task_repo = task_repo
        self._bridge = planning_bridge
        self._uow = uow
        self._user_query_port = user_query_port

    async def execute(
        self,
        *,
        user_id: UUID,
        roadmap_id: UUID,
        milestone_id: UUID,
        title: str,
        description: str | None = None,
        estimated_minutes: int = 30,
        scheduled_date: date | None = None,
        scheduled_start: datetime | None = None,
        scheduled_end: datetime | None = None,
        concept_id: str | None = None,
        learning_resources: list[dict[str, object]] | None = None,
        confirm_soft_overflow: bool = False,
        now: datetime | None = None,
    ) -> TaskViewDTO:
        effective_now = now or datetime.now(UTC)

        async with self._uow:
            await _verify_writable_for_task(self._bridge, user_id, roadmap_id)
            milestone_ok = await self._bridge.verify_milestone_in_roadmap(
                user_id, roadmap_id, milestone_id
            )
            if not milestone_ok:
                raise TaskNotFoundError("Không tìm thấy cột mốc thuộc lộ trình này.")

            roadmaps = await self._bridge.get_user_roadmaps_context(user_id, roadmap_id=roadmap_id)
            rm_ctx = roadmaps[0] if roadmaps else None

            if scheduled_date is not None:
                validation = await self._bridge.validate_manual_task_slot(
                    user_id=user_id,
                    roadmap_id=roadmap_id,
                    task_id=None,
                    scheduled_date=scheduled_date,
                    scheduled_start=scheduled_start,
                    scheduled_end=scheduled_end,
                    estimated_minutes=estimated_minutes,
                    confirm_soft_overflow=confirm_soft_overflow,
                )
                if not validation.is_valid:
                    raise ScheduleSlotConflictError(
                        violations=list(validation.violations),
                        calendar_conflicts=list(validation.calendar_conflicts),
                    )
                official_schedule_id = validation.official_schedule_id
            else:
                official_schedule_id = rm_ctx.official_schedule_id if rm_ctx else None

            task = Task(
                id=generate_uuid7(),
                roadmap_id=roadmap_id,
                milestone_id=milestone_id,
                official_schedule_id=official_schedule_id,
                concept_id=concept_id,
                title=title,
                description=description,
                estimated_minutes=estimated_minutes,
                learning_resources=list(learning_resources or []),
                scheduled_date=scheduled_date,
                scheduled_start=scheduled_start,
                scheduled_end=scheduled_end,
                status=TaskStatus.TODO,
                completed_at=None,
                reschedule_count=0,
                created_at=effective_now,
                updated_at=effective_now,
            )
            saved = await self._task_repo.save(task)

            if scheduled_date is not None:
                await self._bridge.sync_task_lifecycle_to_blocks(
                    task_id=saved.id,
                    roadmap_id=saved.roadmap_id,
                    new_status=saved.status.value,
                    scheduled_date=saved.scheduled_date,
                    scheduled_start=saved.scheduled_start,
                    scheduled_end=saved.scheduled_end,
                    estimated_minutes=saved.estimated_minutes,
                    now=effective_now,
                )

            await self._uow.commit()

        today = await _resolve_user_today(self._user_query_port, user_id, effective_now)
        return TaskViewDTO(
            task=saved,
            is_overdue=saved.is_overdue(today),
            is_blocked=False,
            is_stalled=saved.is_stalled(),
            predecessor_ids=(),
            roadmap_title=rm_ctx.title if rm_ctx else None,
        )


class GetBacklogTasksUseCase:
    """Return Backlog Recovery Queue ranked by BacklogPriorityRanker (FR-TASK-002)."""

    def __init__(
        self,
        *,
        task_repo: TaskRepositoryPort,
        planning_bridge: PlanningExecutionBridgePort,
        user_query_port: UserQueryPort | None = None,
    ) -> None:
        self._task_repo = task_repo
        self._bridge = planning_bridge
        self._user_query_port = user_query_port

    async def execute(
        self,
        *,
        user_id: UUID,
        roadmap_id: UUID | None = None,
        now: datetime | None = None,
    ) -> list[TaskViewDTO]:
        effective_now = now or datetime.now(UTC)
        roadmaps = await self._bridge.get_user_roadmaps_context(user_id, roadmap_id=roadmap_id)
        if roadmap_id is not None and not roadmaps:
            raise TaskNotFoundError("Không tìm thấy lộ trình học tập.")
        if not roadmaps:
            return []

        active_roadmaps = [r for r in roadmaps if r.status != "ARCHIVED"]
        if not active_roadmaps:
            return []

        rids = [r.roadmap_id for r in active_roadmaps]
        title_map = {r.roadmap_id: r.title for r in active_roadmaps}
        all_tasks = await self._task_repo.list_by_roadmap_ids(rids)
        backlog_tasks = [
            t for t in all_tasks if t.status == TaskStatus.TODO and t.scheduled_date is None
        ]
        if not backlog_tasks:
            return []

        deps = await self._task_repo.list_dependencies_by_roadmap_ids(rids)
        milestone_seqs = await self._bridge.get_milestone_sequences(rids)
        status_map = {t.id: t.status for t in all_tasks}

        ranked = BacklogPriorityRanker.rank(
            backlog_tasks,
            dependencies=deps,
            milestone_sequences=milestone_seqs,
            active_task_statuses=status_map,
        )

        today = await _resolve_user_today(self._user_query_port, user_id, effective_now)
        preds_by_succ: dict[UUID, list[TaskDependency]] = {}
        for dep in deps:
            preds_by_succ.setdefault(dep.successor_id, []).append(dep)

        result: list[TaskViewDTO] = []
        for entry in ranked:
            t = entry.task
            t_deps = preds_by_succ.get(t.id, [])
            is_blocked = any(
                status_map.get(d.predecessor_id) != TaskStatus.COMPLETED
                for d in t_deps
                if d.is_mandatory and d.predecessor_id in status_map
            )
            result.append(
                TaskViewDTO(
                    task=t,
                    is_overdue=t.is_overdue(today),
                    is_blocked=is_blocked,
                    is_stalled=t.is_stalled(),
                    predecessor_ids=tuple(d.predecessor_id for d in t_deps),
                    priority_rank=entry.priority_rank,
                    out_degree=entry.out_degree,
                    milestone_sequence=entry.milestone_sequence,
                    roadmap_title=title_map.get(t.roadmap_id),
                )
            )
        return result


class GetWeeklyScheduleUseCase:
    """Weekly schedule view joining Planning `schedule_blocks` with Execution `tasks`."""

    def __init__(
        self,
        *,
        task_repo: TaskRepositoryPort,
        planning_bridge: PlanningExecutionBridgePort,
        user_query_port: UserQueryPort | None = None,
    ) -> None:
        self._task_repo = task_repo
        self._bridge = planning_bridge
        self._user_query_port = user_query_port

    async def execute(
        self,
        *,
        user_id: UUID,
        week_start: date | None = None,
        now: datetime | None = None,
    ) -> WeeklyScheduleViewDTO:
        effective_now = now or datetime.now(UTC)
        today = await _resolve_user_today(self._user_query_port, user_id, effective_now)
        effective_start = (
            week_start if week_start is not None else (today - timedelta(days=today.weekday()))
        )
        effective_end = effective_start + timedelta(days=6)

        blocks = await self._bridge.get_week_schedule_blocks(
            user_id, effective_start, effective_end
        )
        if not blocks:
            return WeeklyScheduleViewDTO(
                week_start=effective_start,
                week_end=effective_end,
                items=(),
            )

        roadmap_ids = list({b.roadmap_id for b in blocks})
        title_map = {b.roadmap_id: b.roadmap_title for b in blocks}
        all_tasks = await self._task_repo.list_by_roadmap_ids(roadmap_ids)
        deps = await self._task_repo.list_dependencies_by_roadmap_ids(roadmap_ids)
        milestones_context = await self._bridge.get_milestones_context(roadmap_ids)
        task_views = _build_task_views(
            all_tasks,
            deps,
            today=today,
            roadmap_titles=title_map,
            all_roadmap_tasks=all_tasks,
            milestones_context=milestones_context,
        )
        view_by_id = {v.task.id: v for v in task_views}

        items = [
            WeeklyScheduleItemDTO(
                block_id=b.id,
                roadmap_id=b.roadmap_id,
                roadmap_title=b.roadmap_title,
                roadmap_status=b.roadmap_status,
                official_schedule_id=b.official_schedule_id,
                task_id=b.task_id,
                sequence_in_task=b.sequence_in_task,
                block_type=b.block_type,
                block_date=b.block_date,
                start_time=b.start_time,
                end_time=b.end_time,
                scheduled_duration_minutes=b.scheduled_duration_minutes,
                block_status=b.status,
                sync_status=b.sync_status,
                is_protected=b.is_protected,
                placement_rationale=b.placement_rationale,
                task=view_by_id.get(b.task_id) if b.task_id is not None else None,
            )
            for b in blocks
        ]
        return WeeklyScheduleViewDTO(
            week_start=effective_start,
            week_end=effective_end,
            items=tuple(items),
        )


class UpdateTaskUseCase:
    """Update task title, description, or estimated_minutes (15..240)."""

    def __init__(
        self,
        *,
        task_repo: TaskRepositoryPort,
        planning_bridge: PlanningExecutionBridgePort,
        uow: AsyncUnitOfWork,
        user_query_port: UserQueryPort | None = None,
    ) -> None:
        self._task_repo = task_repo
        self._bridge = planning_bridge
        self._uow = uow
        self._user_query_port = user_query_port

    async def execute(
        self,
        *,
        user_id: UUID,
        task_id: UUID,
        title: str | None = None,
        description: str | None = None,
        estimated_minutes: int | None = None,
        now: datetime | None = None,
    ) -> TaskViewDTO:
        effective_now = now or datetime.now(UTC)

        async with self._uow:
            task = await self._task_repo.get_by_id_for_update(task_id)
            if task is None:
                raise TaskNotFoundError()
            await _verify_writable_for_task(self._bridge, user_id, task.roadmap_id)

            old_minutes = task.estimated_minutes
            task.update_details(
                title=title,
                description=description,
                estimated_minutes=estimated_minutes,
                now=effective_now,
            )

            if (
                estimated_minutes is not None
                and task.estimated_minutes != old_minutes
                and task.scheduled_date is not None
            ):
                new_end = task.scheduled_end
                if task.scheduled_start is not None:
                    new_end = task.scheduled_start + timedelta(minutes=task.estimated_minutes)
                    task.scheduled_end = new_end
                validation = await self._bridge.validate_manual_task_slot(
                    user_id=user_id,
                    roadmap_id=task.roadmap_id,
                    task_id=task.id,
                    scheduled_date=task.scheduled_date,
                    scheduled_start=task.scheduled_start,
                    scheduled_end=task.scheduled_end,
                    estimated_minutes=task.estimated_minutes,
                )
                if not validation.is_valid:
                    raise ScheduleSlotConflictError(
                        violations=list(validation.violations),
                        calendar_conflicts=list(validation.calendar_conflicts),
                    )
                await self._bridge.sync_task_lifecycle_to_blocks(
                    task_id=task.id,
                    roadmap_id=task.roadmap_id,
                    new_status=task.status.value,
                    scheduled_date=task.scheduled_date,
                    scheduled_start=task.scheduled_start,
                    scheduled_end=task.scheduled_end,
                    estimated_minutes=task.estimated_minutes,
                    now=effective_now,
                )

            saved = await self._task_repo.save(task)
            all_tasks = await self._task_repo.list_by_roadmap_ids([saved.roadmap_id])
            deps = await self._task_repo.list_dependencies_by_roadmap_ids([saved.roadmap_id])
            await self._uow.commit()

        today = await _resolve_user_today(self._user_query_port, user_id, effective_now)
        return _build_task_views([saved], deps, today=today, all_roadmap_tasks=all_tasks)[0]


class CompleteTaskUseCase:
    """Complete a task after checking ownership, mandatory predecessors, and optional TakeawayGuard."""

    def __init__(
        self,
        *,
        task_repo: TaskRepositoryPort,
        planning_bridge: PlanningExecutionBridgePort,
        uow: AsyncUnitOfWork,
        note_saver: Any = None,
        user_query_port: UserQueryPort | None = None,
    ) -> None:
        self._task_repo = task_repo
        self._bridge = planning_bridge
        self._uow = uow
        self._note_saver = note_saver
        self._user_query_port = user_query_port

    async def execute(
        self,
        *,
        user_id: UUID,
        task_id: UUID,
        takeaway: str | None = None,
        self_confidence: int | None = None,
        now: datetime | None = None,
    ) -> TaskViewDTO:
        effective_now = now or datetime.now(UTC)

        async with self._uow:
            task = await self._task_repo.get_by_id_for_update(task_id)
            if task is None:
                raise TaskNotFoundError()
            await _verify_writable_for_task(self._bridge, user_id, task.roadmap_id)

            all_tasks = await self._task_repo.list_by_roadmap_ids([task.roadmap_id])
            deps = await self._task_repo.list_dependencies_by_roadmap_ids([task.roadmap_id])
            status_by_id = {t.id: t.status for t in all_tasks}
            blocking_ids = [
                str(d.predecessor_id)
                for d in deps
                if d.successor_id == task.id
                and d.is_mandatory
                and d.predecessor_id in status_by_id
                and status_by_id[d.predecessor_id] != TaskStatus.COMPLETED
            ]
            if blocking_ids:
                raise TaskBlockedError(blocking_predecessor_ids=blocking_ids)

            if takeaway is not None:
                TakeawayGuard.validate(
                    takeaway,
                    task_title=task.title,
                    task_description=task.description,
                )
                if self._note_saver is not None:
                    note = StudyNote(
                        id=generate_uuid7(),
                        user_id=user_id,
                        session_id=None,
                        task_id=task.id,
                        note_type=NoteType.TAKEAWAY,
                        content=takeaway.strip(),
                        self_confidence=self_confidence,
                        alignment_flag=AlignmentFlag.UNCHECKED,
                        verification_status=VerificationStatus.PENDING_PROVE,
                        created_at=effective_now,
                        updated_at=effective_now,
                    )
                    await self._note_saver(note)

            task.complete(effective_now)
            saved = await self._task_repo.save(task)

            await self._bridge.sync_task_lifecycle_to_blocks(
                task_id=saved.id,
                roadmap_id=saved.roadmap_id,
                new_status="COMPLETED",
                scheduled_date=saved.scheduled_date,
                scheduled_start=saved.scheduled_start,
                scheduled_end=saved.scheduled_end,
                estimated_minutes=saved.estimated_minutes,
                now=effective_now,
            )

            incomplete_count = await self._task_repo.count_incomplete_non_cancelled_in_roadmap(
                saved.roadmap_id
            )
            await self._bridge.record_study_activity_and_check_completion(
                saved.roadmap_id,
                effective_now,
                incomplete_count == 0,
                effective_now,
            )
            await self._uow.commit()

        today = await _resolve_user_today(self._user_query_port, user_id, effective_now)
        refreshed_tasks = [saved if t.id == saved.id else t for t in all_tasks]
        return _build_task_views([saved], deps, today=today, all_roadmap_tasks=refreshed_tasks)[0]


class ReopenTaskUseCase:
    """Reopen a COMPLETED task back to TODO and re-sync schedule blocks."""

    def __init__(
        self,
        *,
        task_repo: TaskRepositoryPort,
        planning_bridge: PlanningExecutionBridgePort,
        uow: AsyncUnitOfWork,
        user_query_port: UserQueryPort | None = None,
    ) -> None:
        self._task_repo = task_repo
        self._bridge = planning_bridge
        self._uow = uow
        self._user_query_port = user_query_port

    async def execute(
        self,
        *,
        user_id: UUID,
        task_id: UUID,
        now: datetime | None = None,
    ) -> TaskViewDTO:
        effective_now = now or datetime.now(UTC)

        async with self._uow:
            task = await self._task_repo.get_by_id_for_update(task_id)
            if task is None:
                raise TaskNotFoundError()
            await _verify_writable_for_task(self._bridge, user_id, task.roadmap_id)

            task.reopen(effective_now)
            saved = await self._task_repo.save(task)

            await self._bridge.sync_task_lifecycle_to_blocks(
                task_id=saved.id,
                roadmap_id=saved.roadmap_id,
                new_status=saved.status.value,
                scheduled_date=saved.scheduled_date,
                scheduled_start=saved.scheduled_start,
                scheduled_end=saved.scheduled_end,
                estimated_minutes=saved.estimated_minutes,
                now=effective_now,
            )

            all_tasks = await self._task_repo.list_by_roadmap_ids([saved.roadmap_id])
            deps = await self._task_repo.list_dependencies_by_roadmap_ids([saved.roadmap_id])
            await self._uow.commit()

        today = await _resolve_user_today(self._user_query_port, user_id, effective_now)
        return _build_task_views([saved], deps, today=today, all_roadmap_tasks=all_tasks)[0]


class RescheduleTaskUseCase:
    """Reschedule a task or move it to backlog (`scheduled_date=None`) via UC-12 + DAG checks."""

    def __init__(
        self,
        *,
        task_repo: TaskRepositoryPort,
        planning_bridge: PlanningExecutionBridgePort,
        schedule_change_log_port: ScheduleChangeLogPort,
        uow: AsyncUnitOfWork,
        user_query_port: UserQueryPort | None = None,
    ) -> None:
        self._task_repo = task_repo
        self._bridge = planning_bridge
        self._change_log_port = schedule_change_log_port
        self._uow = uow
        self._user_query_port = user_query_port

    async def execute(
        self,
        *,
        user_id: UUID,
        task_id: UUID,
        scheduled_date: date | None = None,
        scheduled_start: datetime | None = None,
        scheduled_end: datetime | None = None,
        reason: str | None = None,
        allow_stalled_commitment: bool = False,
        confirm_soft_overflow: bool = False,
        now: datetime | None = None,
    ) -> TaskViewDTO:
        effective_now = now or datetime.now(UTC)

        async with self._uow:
            task = await self._task_repo.get_by_id_for_update(task_id)
            if task is None:
                raise TaskNotFoundError()
            await _verify_writable_for_task(self._bridge, user_id, task.roadmap_id)

            today = await _resolve_user_today(self._user_query_port, user_id, effective_now)
            old_date = task.scheduled_date
            old_start = task.scheduled_start
            old_end = task.scheduled_end

            if scheduled_date is not None:
                validation = await self._bridge.validate_manual_task_slot(
                    user_id=user_id,
                    roadmap_id=task.roadmap_id,
                    task_id=task.id,
                    scheduled_date=scheduled_date,
                    scheduled_start=scheduled_start,
                    scheduled_end=scheduled_end,
                    estimated_minutes=task.estimated_minutes,
                    confirm_soft_overflow=confirm_soft_overflow,
                )
                if not validation.is_valid:
                    raise ScheduleSlotConflictError(
                        violations=list(validation.violations),
                        calendar_conflicts=list(validation.calendar_conflicts),
                    )

            all_tasks = await self._task_repo.list_by_roadmap_ids([task.roadmap_id])
            deps = await self._task_repo.list_dependencies_by_roadmap_ids([task.roadmap_id])

            if scheduled_date is not None and deps:
                dag_nodes: list[DagTaskNode] = []
                node_dates: dict[UUID, date | None] = {}
                for t in all_tasks:
                    if t.status == TaskStatus.CANCELLED:
                        continue
                    eff_date = scheduled_date if t.id == task.id else t.scheduled_date
                    eff_start = scheduled_start if t.id == task.id else t.scheduled_start
                    eff_end = scheduled_end if t.id == task.id else t.scheduled_end
                    node_dates[t.id] = eff_date
                    dag_nodes.append(
                        DagTaskNode(
                            task_id=t.id,
                            title=t.title,
                            scheduled_date=eff_date,
                            scheduled_start=eff_start,
                            scheduled_end=eff_end,
                        )
                    )
                dag_edges = [
                    DagDependencyEdge(
                        predecessor_id=d.predecessor_id,
                        successor_id=d.successor_id,
                        is_mandatory=d.is_mandatory,
                    )
                    for d in deps
                ]
                DagCycleValidator.assert_valid(dag_nodes, dag_edges)

                for d in deps:
                    if not d.is_mandatory:
                        continue
                    if (
                        d.successor_id == task.id
                        and d.predecessor_id in node_dates
                        and node_dates[d.predecessor_id] is None
                    ):
                        raise ExecutionDomainError(
                            message="Không thể xếp lịch nhiệm vụ khi nhiệm vụ tiền đề bắt buộc vẫn đang ở Backlog.",
                            code="DEPENDENCY_TEMPORAL_ORDER_VIOLATION",
                        )

            counted_overdue = task.reschedule(
                scheduled_date=scheduled_date,
                scheduled_start=scheduled_start,
                scheduled_end=scheduled_end,
                today=today,
                now=effective_now,
                allow_stalled_commitment=allow_stalled_commitment,
            )

            if counted_overdue:
                try:
                    await self._bridge.deduct_overdue_reschedule_budget(
                        task.roadmap_id, effective_now
                    )
                except DomainError as exc:
                    raise ExecutionDomainError(exc.message, code=exc.code) from exc

            saved = await self._task_repo.save(task)

            await self._bridge.sync_task_lifecycle_to_blocks(
                task_id=saved.id,
                roadmap_id=saved.roadmap_id,
                new_status=saved.status.value,
                scheduled_date=saved.scheduled_date,
                scheduled_start=saved.scheduled_start,
                scheduled_end=saved.scheduled_end,
                estimated_minutes=saved.estimated_minutes,
                now=effective_now,
            )

            await self._change_log_port.log_schedule_change(
                roadmap_id=saved.roadmap_id,
                schedule_id=saved.official_schedule_id,
                task_id=saved.id,
                trigger_type="MANUAL_EDIT",
                reason=reason
                or (
                    "Chuyển nhiệm vụ về Backlog" if scheduled_date is None else "Dời lịch thủ công"
                ),
                affected_tasks_count=1,
                total_shifted_minutes=saved.estimated_minutes,
                diff_payload={
                    "old_scheduled_date": old_date.isoformat() if old_date else None,
                    "new_scheduled_date": scheduled_date.isoformat() if scheduled_date else None,
                    "old_scheduled_start": old_start.isoformat() if old_start else None,
                    "new_scheduled_start": scheduled_start.isoformat() if scheduled_start else None,
                    "old_scheduled_end": old_end.isoformat() if old_end else None,
                    "new_scheduled_end": scheduled_end.isoformat() if scheduled_end else None,
                    "counted_overdue_budget": counted_overdue,
                },
                now=effective_now,
            )
            await self._uow.commit()

        refreshed = [saved if t.id == saved.id else t for t in all_tasks]
        return _build_task_views([saved], deps, today=today, all_roadmap_tasks=refreshed)[0]


class DeleteTaskUseCase:
    """Soft-cancel a task (`CANCELLED`), verify no active mandatory successors, free blocks."""

    def __init__(
        self,
        *,
        task_repo: TaskRepositoryPort,
        planning_bridge: PlanningExecutionBridgePort,
        uow: AsyncUnitOfWork,
        user_query_port: UserQueryPort | None = None,
    ) -> None:
        self._task_repo = task_repo
        self._bridge = planning_bridge
        self._uow = uow
        self._user_query_port = user_query_port

    async def execute(
        self,
        *,
        user_id: UUID,
        task_id: UUID,
        now: datetime | None = None,
    ) -> TaskViewDTO:
        effective_now = now or datetime.now(UTC)

        async with self._uow:
            task = await self._task_repo.get_by_id_for_update(task_id)
            if task is None:
                raise TaskNotFoundError()
            await _verify_writable_for_task(self._bridge, user_id, task.roadmap_id)

            all_tasks = await self._task_repo.list_by_roadmap_ids([task.roadmap_id])
            deps = await self._task_repo.list_dependencies_by_roadmap_ids([task.roadmap_id])
            status_by_id = {t.id: t.status for t in all_tasks}

            active_successors = [
                str(d.successor_id)
                for d in deps
                if d.predecessor_id == task.id
                and d.is_mandatory
                and status_by_id.get(d.successor_id) in (TaskStatus.TODO, TaskStatus.IN_PROGRESS)
            ]
            if active_successors:
                raise TaskHasActiveSuccessorsError(dependent_successor_ids=active_successors)

            task.cancel(effective_now)
            saved = await self._task_repo.save(task)

            await self._bridge.sync_task_lifecycle_to_blocks(
                task_id=saved.id,
                roadmap_id=saved.roadmap_id,
                new_status="CANCELLED",
                scheduled_date=None,
                scheduled_start=None,
                scheduled_end=None,
                estimated_minutes=saved.estimated_minutes,
                now=effective_now,
            )

            completed_count = await self._task_repo.count_completed_in_roadmap(saved.roadmap_id)
            incomplete_count = await self._task_repo.count_incomplete_non_cancelled_in_roadmap(
                saved.roadmap_id
            )
            if completed_count > 0 and incomplete_count == 0:
                await self._bridge.record_study_activity_and_check_completion(
                    saved.roadmap_id,
                    effective_now,
                    True,
                    effective_now,
                )

            await self._uow.commit()

        today = await _resolve_user_today(self._user_query_port, user_id, effective_now)
        refreshed = [saved if t.id == saved.id else t for t in all_tasks]
        return _build_task_views([saved], deps, today=today, all_roadmap_tasks=refreshed)[0]


class AddTaskDependencyUseCase:
    """Add a prerequisite dependency edge validated by DagCycleValidator."""

    def __init__(
        self,
        *,
        task_repo: TaskRepositoryPort,
        planning_bridge: PlanningExecutionBridgePort,
        uow: AsyncUnitOfWork,
    ) -> None:
        self._task_repo = task_repo
        self._bridge = planning_bridge
        self._uow = uow

    async def execute(
        self,
        *,
        user_id: UUID,
        successor_id: UUID,
        predecessor_id: UUID,
        is_mandatory: bool = True,
        now: datetime | None = None,
    ) -> TaskDependency:
        effective_now = now or datetime.now(UTC)

        async with self._uow:
            successor = await self._task_repo.get_by_id(successor_id)
            predecessor = await self._task_repo.get_by_id(predecessor_id)
            if successor is None or predecessor is None:
                raise TaskNotFoundError()
            await _verify_writable_for_task(self._bridge, user_id, successor.roadmap_id)
            if predecessor.roadmap_id != successor.roadmap_id:
                raise InvalidTaskStateError(
                    "Hai nhiệm vụ phụ thuộc phải thuộc cùng một lộ trình học tập."
                )

            existing = await self._task_repo.get_dependency(predecessor_id, successor_id)
            if existing is not None:
                return existing

            new_dep = TaskDependency(
                id=generate_uuid7(),
                predecessor_id=predecessor_id,
                successor_id=successor_id,
                roadmap_id=successor.roadmap_id,
                is_mandatory=is_mandatory,
                created_at=effective_now,
            )

            all_tasks = await self._task_repo.list_by_roadmap_ids([successor.roadmap_id])
            deps = await self._task_repo.list_dependencies_by_roadmap_ids([successor.roadmap_id])

            dag_nodes = [
                DagTaskNode(
                    task_id=t.id,
                    title=t.title,
                    scheduled_date=t.scheduled_date,
                    scheduled_start=t.scheduled_start,
                    scheduled_end=t.scheduled_end,
                )
                for t in all_tasks
                if t.status != TaskStatus.CANCELLED
            ]
            dag_edges = [
                *[
                    DagDependencyEdge(
                        predecessor_id=d.predecessor_id,
                        successor_id=d.successor_id,
                        is_mandatory=d.is_mandatory,
                    )
                    for d in deps
                ],
                DagDependencyEdge(
                    predecessor_id=predecessor_id,
                    successor_id=successor_id,
                    is_mandatory=is_mandatory,
                ),
            ]
            DagCycleValidator.assert_valid(dag_nodes, dag_edges)

            saved = await self._task_repo.add_dependency(new_dep)
            await self._uow.commit()
            return saved


class DeleteTaskDependencyUseCase:
    """Remove a prerequisite dependency edge."""

    def __init__(
        self,
        *,
        task_repo: TaskRepositoryPort,
        planning_bridge: PlanningExecutionBridgePort,
        uow: AsyncUnitOfWork,
    ) -> None:
        self._task_repo = task_repo
        self._bridge = planning_bridge
        self._uow = uow

    async def execute(
        self,
        *,
        user_id: UUID,
        successor_id: UUID,
        predecessor_id: UUID,
    ) -> None:
        async with self._uow:
            successor = await self._task_repo.get_by_id(successor_id)
            if successor is None:
                raise TaskNotFoundError()
            await _verify_writable_for_task(self._bridge, user_id, successor.roadmap_id)

            deleted = await self._task_repo.delete_dependency(predecessor_id, successor_id)
            if not deleted:
                raise TaskNotFoundError("Không tìm thấy liên kết phụ thuộc.")
            await self._uow.commit()
