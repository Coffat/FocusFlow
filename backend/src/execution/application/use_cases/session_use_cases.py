from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from src.account.public_api import UserQueryPort
from src.execution.application.dtos.execution_dtos import (
    StudySessionViewDTO,
    TaskViewDTO,
    TodayFocusViewDTO,
)
from src.execution.application.ports.study_session_repository_port import (
    StudySessionRepositoryPort,
)
from src.execution.application.ports.task_repository_port import TaskRepositoryPort
from src.execution.application.use_cases.task_use_cases import (
    _build_task_views,
    _resolve_user_today,
    _verify_writable_for_task,
)
from src.execution.domain.exceptions.execution_exceptions import (
    ActiveSessionExistsError,
    ExecutionDomainError,
    InvalidSessionStateError,
    PendingTakeawayRequiredError,
    SessionNotFoundError,
    TaskBlockedError,
    TaskNotFoundError,
)
from src.execution.domain.models.study_session import (
    MVS_MIN_QUALIFYING_MINUTES,
    AlignmentFlag,
    DailyCheckin,
    NoteType,
    SessionMode,
    SessionStatus,
    SessionTask,
    StudyNote,
    StudySession,
    TimeSufficiency,
    VerificationStatus,
)
from src.execution.domain.models.task import TaskStatus
from src.execution.domain.services.takeaway_guard import TakeawayGuard
from src.planning.public_api import PlanningExecutionBridgePort
from src.shared_kernel.application.uow import AsyncUnitOfWork
from src.shared_kernel.domain.base import generate_uuid7


async def _build_session_view(
    session_repo: StudySessionRepositoryPort,
    session: StudySession,
) -> StudySessionViewDTO:
    session_tasks = await session_repo.list_session_tasks(session.id)
    notes = await session_repo.list_study_notes_for_session(session.id)
    scratchpad = ""
    takeaway: str | None = None
    takeaway_conf: int | None = None
    for n in notes:
        if n.note_type == NoteType.SCRATCHPAD:
            scratchpad = n.content
        elif n.note_type == NoteType.TAKEAWAY:
            takeaway = n.content
            takeaway_conf = n.self_confidence
    return StudySessionViewDTO(
        session=session,
        session_tasks=tuple(session_tasks),
        notes=tuple(notes),
        scratchpad_content=scratchpad,
        takeaway_content=takeaway,
        takeaway_self_confidence=takeaway_conf,
    )


class GetTodayFocusUseCase:
    """Return active session, pending_takeaway debt, today's focus task & queue in user's timezone."""

    def __init__(
        self,
        *,
        session_repo: StudySessionRepositoryPort,
        task_repo: TaskRepositoryPort,
        planning_bridge: PlanningExecutionBridgePort,
        user_query_port: UserQueryPort | None = None,
    ) -> None:
        self._session_repo = session_repo
        self._task_repo = task_repo
        self._bridge = planning_bridge
        self._user_query_port = user_query_port

    async def execute(
        self,
        *,
        user_id: UUID,
        now: datetime | None = None,
    ) -> TodayFocusViewDTO:
        effective_now = now or datetime.now(UTC)
        local_today = await _resolve_user_today(self._user_query_port, user_id, effective_now)

        active = await self._session_repo.get_active_for_user(user_id)
        active_view = (
            await _build_session_view(self._session_repo, active) if active is not None else None
        )

        pending = await self._session_repo.get_latest_pending_takeaway_for_user(user_id)
        pending_view = (
            await _build_session_view(self._session_repo, pending) if pending is not None else None
        )

        roadmaps = await self._bridge.get_user_roadmaps_context(user_id)
        active_roadmaps = [r for r in roadmaps if r.status == "ACTIVE"]
        if not active_roadmaps:
            return TodayFocusViewDTO(
                local_date=local_today,
                active_session=active_view,
                pending_takeaway_session=pending_view,
                focus_task=None,
                today_queue=(),
                overdue_tasks_count=0,
            )

        rids = [r.roadmap_id for r in active_roadmaps]
        title_map = {r.roadmap_id: r.title for r in active_roadmaps}
        all_tasks = await self._task_repo.list_by_roadmap_ids(rids)
        deps = await self._task_repo.list_dependencies_by_roadmap_ids(rids)

        all_views = _build_task_views(
            all_tasks,
            deps,
            today=local_today,
            roadmap_titles=title_map,
            all_roadmap_tasks=all_tasks,
        )
        today_queue = [
            v
            for v in all_views
            if v.task.scheduled_date == local_today and v.task.status != TaskStatus.CANCELLED
        ]
        overdue_count = sum(1 for v in all_views if v.is_overdue)

        focus_task: TaskViewDTO | None = None
        for v in today_queue:
            if v.task.status in (TaskStatus.TODO, TaskStatus.IN_PROGRESS) and not v.is_blocked:
                focus_task = v
                break
        if focus_task is None and today_queue:
            for v in today_queue:
                if v.task.status in (TaskStatus.TODO, TaskStatus.IN_PROGRESS):
                    focus_task = v
                    break

        return TodayFocusViewDTO(
            local_date=local_today,
            active_session=active_view,
            pending_takeaway_session=pending_view,
            focus_task=focus_task,
            today_queue=tuple(today_queue),
            overdue_tasks_count=overdue_count,
        )


class GetActiveSessionUseCase:
    """Return currently active IN_PROGRESS study session for user or None."""

    def __init__(self, *, session_repo: StudySessionRepositoryPort) -> None:
        self._session_repo = session_repo

    async def execute(self, *, user_id: UUID) -> StudySessionViewDTO | None:
        active = await self._session_repo.get_active_for_user(user_id)
        if active is None:
            return None
        return await _build_session_view(self._session_repo, active)


class StartStudySessionUseCase:
    """Start a STANDARD or MVS study session enforcing single-active, pending_takeaway, and DAG guards."""

    def __init__(
        self,
        *,
        session_repo: StudySessionRepositoryPort,
        task_repo: TaskRepositoryPort,
        planning_bridge: PlanningExecutionBridgePort,
        uow: AsyncUnitOfWork,
    ) -> None:
        self._session_repo = session_repo
        self._task_repo = task_repo
        self._bridge = planning_bridge
        self._uow = uow

    async def execute(
        self,
        *,
        user_id: UUID,
        task_ids: Sequence[UUID],
        session_mode: str = "STANDARD",
        planned_minutes: int | None = None,
        now: datetime | None = None,
    ) -> StudySessionViewDTO:
        effective_now = now or datetime.now(UTC)
        unique_ids = list(dict.fromkeys(task_ids))
        if not unique_ids:
            raise ExecutionDomainError(
                message="Cần chọn ít nhất một nhiệm vụ để bắt đầu phiên học.",
                code="EMPTY_SESSION_TASKS",
            )

        mode_enum = SessionMode(session_mode.strip().upper())

        async with self._uow:
            existing_active = await self._session_repo.get_active_for_user(user_id)
            if existing_active is not None:
                raise ActiveSessionExistsError()

            pending = await self._session_repo.get_latest_pending_takeaway_for_user(user_id)
            if pending is not None:
                raise PendingTakeawayRequiredError(pending_session_id=str(pending.id))

            tasks = await self._task_repo.list_by_ids(unique_ids)
            task_map = {t.id: t for t in tasks}
            if len(task_map) != len(unique_ids):
                raise TaskNotFoundError()

            ordered_tasks = [task_map[tid] for tid in unique_ids]
            roadmap_ids = {t.roadmap_id for t in ordered_tasks}
            if len(roadmap_ids) != 1:
                raise InvalidSessionStateError(
                    "Các nhiệm vụ trong cùng một phiên học phải thuộc cùng một lộ trình."
                )
            roadmap_id = next(iter(roadmap_ids))
            await _verify_writable_for_task(self._bridge, user_id, roadmap_id)

            for t in ordered_tasks:
                if t.status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED):
                    raise InvalidSessionStateError(
                        f"Nhiệm vụ '{t.title}' đang ở trạng thái '{t.status.value}' nên không thể bắt đầu phiên."
                    )

            all_roadmap_tasks = await self._task_repo.list_by_roadmap_ids([roadmap_id])
            deps = await self._task_repo.list_dependencies_by_roadmap_ids([roadmap_id])
            status_by_id = {t.id: t.status for t in all_roadmap_tasks}

            blocking_preds: list[str] = []
            for t in ordered_tasks:
                for d in deps:
                    if (
                        d.successor_id == t.id
                        and d.is_mandatory
                        and d.predecessor_id in status_by_id
                        and status_by_id[d.predecessor_id] != TaskStatus.COMPLETED
                    ):
                        blocking_preds.append(str(d.predecessor_id))
            if blocking_preds:
                raise TaskBlockedError(blocking_predecessor_ids=blocking_preds)

            if mode_enum == SessionMode.MVS:
                eff_planned = (
                    int(planned_minutes)
                    if planned_minutes is not None
                    else MVS_MIN_QUALIFYING_MINUTES
                )
                if not (10 <= eff_planned <= 15):
                    raise ExecutionDomainError(
                        message="Phiên MVS Mode phải có thời lượng dự kiến từ 10 đến 15 phút.",
                        code="INVALID_SESSION_DURATION",
                    )
            else:
                eff_planned = (
                    int(planned_minutes)
                    if planned_minutes is not None
                    else sum(t.estimated_minutes for t in ordered_tasks)
                )
                if eff_planned <= 0:
                    raise ExecutionDomainError(
                        message="Thời lượng dự kiến của phiên học phải lớn hơn 0.",
                        code="INVALID_SESSION_DURATION",
                    )

            new_session = StudySession(
                id=generate_uuid7(),
                user_id=user_id,
                roadmap_id=roadmap_id,
                started_at=effective_now,
                ended_at=None,
                planned_minutes=eff_planned,
                actual_minutes=0,
                status=SessionStatus.IN_PROGRESS,
                last_heartbeat_at=effective_now,
                session_mode=mode_enum,
                pending_takeaway=False,
                created_at=effective_now,
                updated_at=effective_now,
            )
            saved_session = await self._session_repo.save(new_session)

            session_tasks: list[SessionTask] = []
            for t in ordered_tasks:
                t.mark_in_progress(effective_now)
                await self._task_repo.save(t)
                st = SessionTask(
                    id=generate_uuid7(),
                    session_id=saved_session.id,
                    task_id=t.id,
                    allocated_minutes=(
                        eff_planned
                        if len(ordered_tasks) == 1 and mode_enum == SessionMode.MVS
                        else t.estimated_minutes
                    ),
                    actual_minutes=0,
                    status_after_session="IN_PROGRESS",
                    created_at=effective_now,
                    updated_at=effective_now,
                )
                saved_st = await self._session_repo.upsert_session_task(st)
                session_tasks.append(saved_st)

            await self._uow.commit()

        return StudySessionViewDTO(
            session=saved_session,
            session_tasks=tuple(session_tasks),
        )


class HeartbeatStudySessionUseCase:
    """Record 60s heartbeat with FOR UPDATE lock & optional SCRATCHPAD upsert."""

    def __init__(
        self,
        *,
        session_repo: StudySessionRepositoryPort,
        uow: AsyncUnitOfWork,
    ) -> None:
        self._session_repo = session_repo
        self._uow = uow

    async def execute(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
        actual_minutes: int | None = None,
        scratchpad_content: str | None = None,
        now: datetime | None = None,
    ) -> StudySessionViewDTO:
        effective_now = now or datetime.now(UTC)

        async with self._uow:
            session = await self._session_repo.get_by_id_for_update(session_id)
            if session is None or session.user_id != user_id:
                raise SessionNotFoundError()

            session.record_heartbeat(now=effective_now, actual_minutes=actual_minutes)
            saved = await self._session_repo.save(session)
            session_tasks = await self._session_repo.list_session_tasks(saved.id)

            if scratchpad_content is not None:
                primary_task_id = session_tasks[0].task_id if session_tasks else None
                scratch_note = StudyNote(
                    id=generate_uuid7(),
                    user_id=user_id,
                    session_id=saved.id,
                    task_id=primary_task_id,
                    note_type=NoteType.SCRATCHPAD,
                    content=scratchpad_content,
                    alignment_flag=AlignmentFlag.UNCHECKED,
                    verification_status=VerificationStatus.PENDING_PROVE,
                    created_at=effective_now,
                    updated_at=effective_now,
                )
                await self._session_repo.upsert_study_note(scratch_note)

            view = await _build_session_view(self._session_repo, saved)
            await self._uow.commit()
            return view


class FinalizeStudySessionUseCase:
    """Finalize a study session with FOR UPDATE lock, TakeawayGuard, OS-01, DailyCheckin & Outbox."""

    def __init__(
        self,
        *,
        session_repo: StudySessionRepositoryPort,
        task_repo: TaskRepositoryPort,
        planning_bridge: PlanningExecutionBridgePort,
        uow: AsyncUnitOfWork,
    ) -> None:
        self._session_repo = session_repo
        self._task_repo = task_repo
        self._bridge = planning_bridge
        self._uow = uow

    async def execute(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
        early_stop: bool = False,
        completed_task_ids: Sequence[UUID] = (),
        takeaway: str | None = None,
        self_confidence: int | None = None,
        scratchpad_content: str | None = None,
        actual_minutes: int | None = None,
        checkin_time_sufficiency: str | None = None,
        checkin_perceived_difficulty: int | None = None,
        checkin_focus_level: int | None = None,
        now: datetime | None = None,
    ) -> StudySessionViewDTO:
        effective_now = now or datetime.now(UTC)

        async with self._uow:
            session = await self._session_repo.get_by_id_for_update(session_id)
            if session is None or session.user_id != user_id:
                raise SessionNotFoundError()
            if session.status != SessionStatus.IN_PROGRESS:
                raise InvalidSessionStateError(
                    f"Phiên học đã kết thúc ({session.status.value}) và không thể chốt lại."
                )

            session_tasks = await self._session_repo.list_session_tasks(session.id)
            tasks = await self._task_repo.list_by_ids([st.task_id for st in session_tasks])
            task_map = {t.id: t for t in tasks}

            combined_title = " ".join(t.title for t in tasks)
            combined_desc = " ".join(t.description for t in tasks if t.description)

            has_valid_takeaway = False
            if not early_stop:
                TakeawayGuard.validate(
                    takeaway,
                    task_title=combined_title,
                    task_description=combined_desc or None,
                )
                has_valid_takeaway = True
            elif takeaway is not None and takeaway.strip():
                TakeawayGuard.validate(
                    takeaway,
                    task_title=combined_title,
                    task_description=combined_desc or None,
                )
                has_valid_takeaway = True

            checkin = DailyCheckin(
                time_sufficiency=(
                    TimeSufficiency(checkin_time_sufficiency.strip().upper())
                    if checkin_time_sufficiency is not None
                    else None
                ),
                perceived_difficulty=checkin_perceived_difficulty,
                focus_level=checkin_focus_level,
            )

            session_task_id_set = {st.task_id for st in session_tasks}
            completed_set = {tid for tid in completed_task_ids if tid in session_task_id_set}

            new_status = session.finalize(
                now=effective_now,
                early_stop=early_stop,
                has_completed_task=bool(completed_set),
                has_valid_takeaway=has_valid_takeaway,
                checkin=checkin,
                actual_minutes_override=actual_minutes,
            )

            for st in session_tasks:
                task = task_map.get(st.task_id)
                if task is None:
                    continue
                if task.id in completed_set:
                    task.complete(effective_now)
                    st.status_after_session = "COMPLETED"
                    st.actual_minutes = session.actual_minutes
                    await self._task_repo.save(task)
                    await self._bridge.sync_task_lifecycle_to_blocks(
                        task_id=task.id,
                        roadmap_id=task.roadmap_id,
                        new_status="COMPLETED",
                        scheduled_date=task.scheduled_date,
                        scheduled_start=task.scheduled_start,
                        scheduled_end=task.scheduled_end,
                        estimated_minutes=task.estimated_minutes,
                        now=effective_now,
                    )
                else:
                    if early_stop or new_status in (
                        SessionStatus.PARTIAL_COMPLETED,
                        SessionStatus.CANCELLED,
                    ):
                        task.return_to_backlog(effective_now)
                        await self._bridge.sync_task_lifecycle_to_blocks(
                            task_id=task.id,
                            roadmap_id=task.roadmap_id,
                            new_status="TODO",
                            scheduled_date=None,
                            scheduled_start=None,
                            scheduled_end=None,
                            estimated_minutes=task.estimated_minutes,
                            now=effective_now,
                        )
                    elif task.status == TaskStatus.IN_PROGRESS:
                        task.status = TaskStatus.TODO
                        task.updated_at = effective_now
                    st.status_after_session = "TODO"
                    await self._task_repo.save(task)

                st.updated_at = effective_now
                await self._session_repo.upsert_session_task(st)

            primary_task_id = session_tasks[0].task_id if session_tasks else None
            if scratchpad_content is not None:
                await self._session_repo.upsert_study_note(
                    StudyNote(
                        id=generate_uuid7(),
                        user_id=user_id,
                        session_id=session.id,
                        task_id=primary_task_id,
                        note_type=NoteType.SCRATCHPAD,
                        content=scratchpad_content,
                        alignment_flag=AlignmentFlag.UNCHECKED,
                        verification_status=VerificationStatus.PENDING_PROVE,
                        created_at=effective_now,
                        updated_at=effective_now,
                    )
                )

            if has_valid_takeaway and takeaway is not None:
                await self._session_repo.upsert_study_note(
                    StudyNote(
                        id=generate_uuid7(),
                        user_id=user_id,
                        session_id=session.id,
                        task_id=primary_task_id,
                        note_type=NoteType.TAKEAWAY,
                        content=takeaway.strip(),
                        self_confidence=self_confidence,
                        alignment_flag=AlignmentFlag.UNCHECKED,
                        verification_status=VerificationStatus.PENDING_PROVE,
                        created_at=effective_now,
                        updated_at=effective_now,
                    )
                )

            saved_session = await self._session_repo.save(session)

            incomplete_count = await self._task_repo.count_incomplete_non_cancelled_in_roadmap(
                saved_session.roadmap_id
            )
            await self._bridge.record_study_activity_and_check_completion(
                saved_session.roadmap_id,
                effective_now,
                incomplete_count == 0,
                effective_now,
            )

            self._uow.collect_events_from(session)
            view = await _build_session_view(self._session_repo, saved_session)
            await self._uow.commit()
            return view


class ResolvePendingTakeawayUseCase:
    """Resolve `pending_takeaway=True` debt for an interrupted session via TakeawayGuard."""

    def __init__(
        self,
        *,
        session_repo: StudySessionRepositoryPort,
        task_repo: TaskRepositoryPort,
        uow: AsyncUnitOfWork,
    ) -> None:
        self._session_repo = session_repo
        self._task_repo = task_repo
        self._uow = uow

    async def execute(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
        takeaway: str,
        self_confidence: int | None = None,
        now: datetime | None = None,
    ) -> StudySessionViewDTO:
        effective_now = now or datetime.now(UTC)

        async with self._uow:
            session = await self._session_repo.get_by_id_for_update(session_id)
            if session is None or session.user_id != user_id:
                raise SessionNotFoundError()
            if not session.pending_takeaway:
                raise InvalidSessionStateError("Phiên học này không có nghĩa vụ nợ Key Takeaway.")

            session_tasks = await self._session_repo.list_session_tasks(session.id)
            tasks = await self._task_repo.list_by_ids([st.task_id for st in session_tasks])
            combined_title = " ".join(t.title for t in tasks)
            combined_desc = " ".join(t.description for t in tasks if t.description)

            TakeawayGuard.validate(
                takeaway,
                task_title=combined_title,
                task_description=combined_desc or None,
            )

            primary_task_id = session_tasks[0].task_id if session_tasks else None
            await self._session_repo.upsert_study_note(
                StudyNote(
                    id=generate_uuid7(),
                    user_id=user_id,
                    session_id=session.id,
                    task_id=primary_task_id,
                    note_type=NoteType.TAKEAWAY,
                    content=takeaway.strip(),
                    self_confidence=self_confidence,
                    alignment_flag=AlignmentFlag.UNCHECKED,
                    verification_status=VerificationStatus.PENDING_PROVE,
                    created_at=effective_now,
                    updated_at=effective_now,
                )
            )

            session.resolve_pending_takeaway(now=effective_now)
            saved = await self._session_repo.save(session)
            view = await _build_session_view(self._session_repo, saved)
            await self._uow.commit()
            return view
