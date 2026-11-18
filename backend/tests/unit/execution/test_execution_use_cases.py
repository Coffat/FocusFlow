from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta
from types import TracebackType
from typing import Any, Self
from uuid import UUID

import pytest
from uuid6 import uuid7

from src.account.public_api import UserSnapshotDTO
from src.evaluation.public_api import ScheduleChangeLogEntryDTO
from src.execution.application.use_cases.session_use_cases import (
    CreateStickyNoteUseCase,
    DeleteStickyNoteUseCase,
    FinalizeStudySessionUseCase,
    GetStudioConfigUseCase,
    GetTodayFocusUseCase,
    ListStickyNotesUseCase,
    StartStudySessionUseCase,
    UpdateStickyNoteUseCase,
    UpsertStudioConfigUseCase,
)
from src.execution.application.use_cases.task_use_cases import (
    CompleteTaskUseCase,
    DeleteTaskUseCase,
    ListTasksUseCase,
    RescheduleTaskUseCase,
)
from src.execution.domain.exceptions.execution_exceptions import (
    ActiveSessionExistsError,
    ExecutionDomainError,
    PendingTakeawayRequiredError,
    ScheduleSlotConflictError,
    TaskBlockedError,
    TaskHasActiveSuccessorsError,
    TaskStalledInterventionRequiredError,
)
from src.execution.domain.models.study_session import (
    NoteType,
    SessionMode,
    SessionStatus,
    SessionTask,
    StudyNote,
    StudySession,
)
from src.execution.domain.models.task import Task, TaskDependency, TaskStatus
from src.execution.presentation.routers import _handle_execution_error
from src.planning.public_api import (
    ExecutionWeekScheduleBlockDTO,
    ManualSlotValidationResultDTO,
    MilestoneExecutionContextDTO,
    RoadmapExecutionContextDTO,
)
from src.shared_kernel.domain.base import AggregateRoot


class FakeUow:
    def __init__(self) -> None:
        self.committed = False
        self.events: list[Any] = []

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        return None

    def collect_events_from(self, aggregate: AggregateRoot) -> None:
        self.events.extend(aggregate.pull_domain_events())

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        pass


class FakeTaskRepo:
    def __init__(self, tasks: list[Task] | None = None, deps: list[TaskDependency] | None = None):
        self.tasks: dict[UUID, Task] = {t.id: t for t in (tasks or [])}
        self.deps: list[TaskDependency] = list(deps or [])

    async def get_by_id(self, task_id: UUID) -> Task | None:
        return self.tasks.get(task_id)

    async def get_by_id_for_update(self, task_id: UUID) -> Task | None:
        return self.tasks.get(task_id)

    async def list_by_ids(self, task_ids: Sequence[UUID]) -> list[Task]:
        return [self.tasks[tid] for tid in task_ids if tid in self.tasks]

    async def list_by_roadmap_ids(
        self, roadmap_ids: Sequence[UUID], *, status: str | None = None
    ) -> list[Task]:
        rset = set(roadmap_ids)
        return [
            t
            for t in self.tasks.values()
            if t.roadmap_id in rset and (status is None or t.status.value == status)
        ]

    async def list_backlog_by_roadmap_ids(self, roadmap_ids: Sequence[UUID]) -> list[Task]:
        rset = set(roadmap_ids)
        return [
            t
            for t in self.tasks.values()
            if t.roadmap_id in rset and t.status == TaskStatus.TODO and t.scheduled_date is None
        ]

    async def list_dependencies_by_roadmap_ids(
        self, roadmap_ids: Sequence[UUID]
    ) -> list[TaskDependency]:
        rset = set(roadmap_ids)
        return [d for d in self.deps if d.roadmap_id in rset]

    async def get_dependency(
        self, predecessor_id: UUID, successor_id: UUID
    ) -> TaskDependency | None:
        for d in self.deps:
            if d.predecessor_id == predecessor_id and d.successor_id == successor_id:
                return d
        return None

    async def save(self, task: Task) -> Task:
        self.tasks[task.id] = task
        return task

    async def add_dependency(self, dependency: TaskDependency) -> TaskDependency:
        self.deps.append(dependency)
        return dependency

    async def delete_dependency(self, predecessor_id: UUID, successor_id: UUID) -> bool:
        before = len(self.deps)
        self.deps = [
            d
            for d in self.deps
            if not (d.predecessor_id == predecessor_id and d.successor_id == successor_id)
        ]
        return len(self.deps) < before

    async def count_incomplete_non_cancelled_in_roadmap(self, roadmap_id: UUID) -> int:
        return sum(
            1
            for t in self.tasks.values()
            if t.roadmap_id == roadmap_id and t.status in (TaskStatus.TODO, TaskStatus.IN_PROGRESS)
        )

    async def count_completed_in_roadmap(self, roadmap_id: UUID) -> int:
        return sum(
            1
            for t in self.tasks.values()
            if t.roadmap_id == roadmap_id and t.status == TaskStatus.COMPLETED
        )


class FakeSessionRepo:
    def __init__(self, sessions: list[StudySession] | None = None) -> None:
        self.sessions: dict[UUID, StudySession] = {s.id: s for s in (sessions or [])}
        self.session_tasks: dict[UUID, list[SessionTask]] = {}
        self.notes: dict[UUID, list[StudyNote]] = {}
        self.general_notes: dict[UUID, StudyNote] = {}

    async def get_by_id(self, session_id: UUID) -> StudySession | None:
        return self.sessions.get(session_id)

    async def get_by_id_for_update(self, session_id: UUID) -> StudySession | None:
        return self.sessions.get(session_id)

    async def get_active_for_user(self, user_id: UUID) -> StudySession | None:
        for s in self.sessions.values():
            if s.user_id == user_id and s.status == SessionStatus.IN_PROGRESS:
                return s
        return None

    async def get_latest_pending_takeaway_for_user(self, user_id: UUID) -> StudySession | None:
        for s in self.sessions.values():
            if s.user_id == user_id and s.pending_takeaway:
                return s
        return None

    async def save(self, study_session: StudySession) -> StudySession:
        self.sessions[study_session.id] = study_session
        return study_session

    async def upsert_session_task(self, session_task: SessionTask) -> SessionTask:
        lst = self.session_tasks.setdefault(session_task.session_id, [])
        for idx, existing in enumerate(lst):
            if existing.task_id == session_task.task_id:
                lst[idx] = session_task
                return session_task
        lst.append(session_task)
        return session_task

    async def list_session_tasks(self, session_id: UUID) -> list[SessionTask]:
        return list(self.session_tasks.get(session_id, []))

    async def upsert_study_note(self, study_note: StudyNote) -> StudyNote:
        if study_note.session_id is None:
            self.general_notes[study_note.id] = study_note
            return study_note
        lst = self.notes.setdefault(study_note.session_id, [])
        for idx, existing in enumerate(lst):
            if existing.note_type == study_note.note_type:
                lst[idx] = study_note
                return study_note
        lst.append(study_note)
        return study_note

    async def get_study_note_for_session(
        self, session_id: UUID, note_type: NoteType
    ) -> StudyNote | None:
        for n in self.notes.get(session_id, []):
            if n.note_type == note_type:
                return n
        return None

    async def list_study_notes_for_session(self, session_id: UUID) -> list[StudyNote]:
        return list(self.notes.get(session_id, []))

    async def list_completed_for_user_between(
        self, user_id: UUID, start_utc: datetime, end_utc: datetime
    ) -> list[StudySession]:
        result: list[StudySession] = []
        for s in self.sessions.values():
            if (
                s.user_id == user_id
                and s.status in (SessionStatus.COMPLETED, SessionStatus.PARTIAL_COMPLETED)
                and s.ended_at is not None
                and start_utc <= s.ended_at < end_utc
            ):
                result.append(s)
        return result

    async def list_general_notes_for_user(self, user_id: UUID) -> list[StudyNote]:
        matched = [
            n
            for n in self.general_notes.values()
            if n.user_id == user_id and n.note_type == NoteType.GENERAL
        ]
        matched.sort(key=lambda n: (n.updated_at, n.created_at), reverse=True)
        return matched

    async def get_study_note_by_id(self, note_id: UUID) -> StudyNote | None:
        return self.general_notes.get(note_id)

    async def delete_study_note(self, note_id: UUID) -> None:
        self.general_notes.pop(note_id, None)


class FakeUserQueryPort:
    def __init__(self, users: dict[UUID, UserSnapshotDTO] | None = None) -> None:
        self.users = users or {}

    async def get_user_by_id(self, user_id: UUID) -> UserSnapshotDTO | None:
        return self.users.get(user_id)

    async def get_user_by_email(self, email: str) -> UserSnapshotDTO | None:
        for u in self.users.values():
            if u.email == email:
                return u
        return None


class FakePlanningBridge:
    def __init__(
        self,
        *,
        user_id: UUID,
        roadmap_id: UUID,
        slot_valid: bool = True,
        milestones: dict[UUID, MilestoneExecutionContextDTO] | None = None,
    ) -> None:
        self.user_id = user_id
        self.roadmap_id = roadmap_id
        self.slot_valid = slot_valid
        self.milestones = milestones or {}
        self.synced_calls: list[dict[str, Any]] = []
        self.deducted_count = 0
        self.completed_roadmap = False

    async def get_user_roadmaps_context(
        self, user_id: UUID, roadmap_id: UUID | None = None
    ) -> list[RoadmapExecutionContextDTO]:
        if user_id != self.user_id:
            return []
        return [
            RoadmapExecutionContextDTO(
                roadmap_id=self.roadmap_id,
                user_id=self.user_id,
                title="Test Roadmap",
                status="ACTIVE",
                target_date=date(2026, 12, 31),
                official_schedule_id=uuid7(),
                weekly_reschedule_budget=3,
                weekly_reschedule_used=0,
                budget_week_start=None,
            )
        ]

    async def get_milestone_sequences(self, roadmap_ids: Sequence[UUID]) -> dict[UUID, int]:
        return {mid: ctx.sequence_order for mid, ctx in self.milestones.items()}

    async def get_milestones_context(
        self, roadmap_ids: Sequence[UUID]
    ) -> dict[UUID, MilestoneExecutionContextDTO]:
        rset = set(roadmap_ids)
        return {mid: ctx for mid, ctx in self.milestones.items() if ctx.roadmap_id in rset}

    async def verify_milestone_in_roadmap(
        self, user_id: UUID, roadmap_id: UUID, milestone_id: UUID
    ) -> bool:
        return user_id == self.user_id and roadmap_id == self.roadmap_id

    async def get_week_schedule_blocks(
        self, user_id: UUID, start_date: date, end_date: date
    ) -> list[ExecutionWeekScheduleBlockDTO]:
        return []

    async def verify_roadmap_writable(self, user_id: UUID, roadmap_id: UUID) -> date | None:
        return date(2026, 12, 31)

    async def validate_manual_task_slot(self, **kwargs: Any) -> ManualSlotValidationResultDTO:
        return ManualSlotValidationResultDTO(
            is_valid=self.slot_valid,
            violations=() if self.slot_valid else ({"rule_code": "CONFLICT"},),
        )

    async def sync_task_lifecycle_to_blocks(self, **kwargs: Any) -> None:
        self.synced_calls.append(kwargs)

    async def deduct_overdue_reschedule_budget(self, roadmap_id: UUID, now: datetime) -> int:
        self.deducted_count += 1
        return self.deducted_count

    async def record_study_activity_and_check_completion(
        self, roadmap_id: UUID, activity_at: datetime, all_tasks_completed: bool, now: datetime
    ) -> str:
        if all_tasks_completed:
            self.completed_roadmap = True
            return "COMPLETED"
        return "ACTIVE"


class FakeChangeLogPort:
    def __init__(self) -> None:
        self.logs: list[dict[str, Any]] = []

    async def log_schedule_change(self, **kwargs: Any) -> ScheduleChangeLogEntryDTO:
        self.logs.append(kwargs)
        return ScheduleChangeLogEntryDTO(
            id=uuid7(),
            roadmap_id=kwargs["roadmap_id"],
            schedule_id=kwargs.get("schedule_id"),
            task_id=kwargs.get("task_id"),
            trigger_type=kwargs.get("trigger_type", "MANUAL_EDIT"),
            reason=kwargs.get("reason"),
            affected_tasks_count=1,
            total_shifted_minutes=kwargs.get("total_shifted_minutes", 0),
        )

    async def record_change_log(self, **kwargs: Any) -> ScheduleChangeLogEntryDTO:
        return await self.log_schedule_change(**kwargs)


@pytest.mark.asyncio
async def test_complete_task_blocked_then_unblocked_completes_roadmap() -> None:
    now = datetime(2026, 11, 18, 10, 0, tzinfo=UTC)
    uid, rid, mid = uuid7(), uuid7(), uuid7()
    t1 = Task(
        id=uuid7(), roadmap_id=rid, milestone_id=mid, title="T1", created_at=now, updated_at=now
    )
    t2 = Task(
        id=uuid7(), roadmap_id=rid, milestone_id=mid, title="T2", created_at=now, updated_at=now
    )
    dep = TaskDependency(
        predecessor_id=t1.id, successor_id=t2.id, roadmap_id=rid, is_mandatory=True
    )

    task_repo = FakeTaskRepo([t1, t2], [dep])
    bridge = FakePlanningBridge(user_id=uid, roadmap_id=rid)
    uow = FakeUow()
    uc = CompleteTaskUseCase(task_repo=task_repo, planning_bridge=bridge, uow=uow)

    with pytest.raises(TaskBlockedError):
        await uc.execute(user_id=uid, task_id=t2.id, now=now)

    await uc.execute(user_id=uid, task_id=t1.id, now=now)
    assert bridge.completed_roadmap is False

    await uc.execute(user_id=uid, task_id=t2.id, now=now)
    assert bridge.completed_roadmap is True
    assert uow.committed is True


@pytest.mark.asyncio
async def test_reschedule_stalled_budget_and_slot_conflict() -> None:
    now = datetime(2026, 11, 18, 10, 0, tzinfo=UTC)
    uid, rid, mid = uuid7(), uuid7(), uuid7()
    overdue = Task(
        id=uuid7(),
        roadmap_id=rid,
        milestone_id=mid,
        title="Overdue",
        scheduled_date=date(2026, 11, 16),
        reschedule_count=1,
        created_at=now,
        updated_at=now,
    )
    stalled = Task(
        id=uuid7(),
        roadmap_id=rid,
        milestone_id=mid,
        title="Stalled",
        scheduled_date=date(2026, 11, 16),
        reschedule_count=3,
        created_at=now,
        updated_at=now,
    )
    task_repo = FakeTaskRepo([overdue, stalled])
    bridge = FakePlanningBridge(user_id=uid, roadmap_id=rid, slot_valid=True)
    log_port = FakeChangeLogPort()
    uow = FakeUow()

    uc = RescheduleTaskUseCase(
        task_repo=task_repo,
        planning_bridge=bridge,
        schedule_change_log_port=log_port,
        uow=uow,
    )

    with pytest.raises(TaskStalledInterventionRequiredError):
        await uc.execute(
            user_id=uid, task_id=stalled.id, scheduled_date=date(2026, 11, 20), now=now
        )

    res = await uc.execute(
        user_id=uid, task_id=overdue.id, scheduled_date=date(2026, 11, 20), now=now
    )
    assert res.task.reschedule_count == 2
    assert bridge.deducted_count == 1
    assert len(log_port.logs) == 1
    assert log_port.logs[0]["trigger_type"] == "MANUAL_EDIT"

    bridge.slot_valid = False
    with pytest.raises(ScheduleSlotConflictError):
        await uc.execute(
            user_id=uid, task_id=overdue.id, scheduled_date=date(2026, 11, 21), now=now
        )


@pytest.mark.asyncio
async def test_delete_task_rejects_active_mandatory_successor() -> None:
    now = datetime(2026, 11, 18, 10, 0, tzinfo=UTC)
    uid, rid, mid = uuid7(), uuid7(), uuid7()
    t1 = Task(
        id=uuid7(), roadmap_id=rid, milestone_id=mid, title="T1", created_at=now, updated_at=now
    )
    t2 = Task(
        id=uuid7(), roadmap_id=rid, milestone_id=mid, title="T2", created_at=now, updated_at=now
    )
    dep = TaskDependency(
        predecessor_id=t1.id, successor_id=t2.id, roadmap_id=rid, is_mandatory=True
    )

    task_repo = FakeTaskRepo([t1, t2], [dep])
    bridge = FakePlanningBridge(user_id=uid, roadmap_id=rid)
    uc = DeleteTaskUseCase(task_repo=task_repo, planning_bridge=bridge, uow=FakeUow())

    with pytest.raises(TaskHasActiveSuccessorsError):
        await uc.execute(user_id=uid, task_id=t1.id, now=now)


@pytest.mark.asyncio
async def test_session_guards_and_early_stop_backlog_return() -> None:
    now = datetime(2026, 11, 18, 10, 0, tzinfo=UTC)
    uid, rid, mid = uuid7(), uuid7(), uuid7()
    t1 = Task(
        id=uuid7(),
        roadmap_id=rid,
        milestone_id=mid,
        title="Task 1",
        estimated_minutes=60,
        scheduled_date=date(2026, 11, 18),
        created_at=now,
        updated_at=now,
    )
    task_repo = FakeTaskRepo([t1])
    bridge = FakePlanningBridge(user_id=uid, roadmap_id=rid)

    # 1. Pending takeaway blocks start
    pending_sess = StudySession(
        id=uuid7(),
        user_id=uid,
        roadmap_id=rid,
        started_at=now,
        ended_at=now,
        planned_minutes=30,
        status=SessionStatus.PARTIAL_COMPLETED,
        pending_takeaway=True,
        last_heartbeat_at=now,
        created_at=now,
        updated_at=now,
    )
    sess_repo = FakeSessionRepo([pending_sess])
    start_uc = StartStudySessionUseCase(
        session_repo=sess_repo, task_repo=task_repo, planning_bridge=bridge, uow=FakeUow()
    )
    with pytest.raises(PendingTakeawayRequiredError):
        await start_uc.execute(user_id=uid, task_ids=[t1.id], now=now)

    # 2. Clear pending, start MVS, then second start blocked by ACTIVE_SESSION_EXISTS
    pending_sess.pending_takeaway = False
    started = await start_uc.execute(
        user_id=uid,
        task_ids=[t1.id],
        session_mode=SessionMode.MVS.value,
        planned_minutes=10,
        now=now,
    )
    assert started.session.status == SessionStatus.IN_PROGRESS
    assert task_repo.tasks[t1.id].status == TaskStatus.IN_PROGRESS

    with pytest.raises(ActiveSessionExistsError):
        await start_uc.execute(user_id=uid, task_ids=[t1.id], now=now)

    # 3. Early stop MVS >= 10m with valid takeaway -> PARTIAL_COMPLETED & incomplete task returned to backlog
    uow_fin = FakeUow()
    fin_uc = FinalizeStudySessionUseCase(
        session_repo=sess_repo, task_repo=task_repo, planning_bridge=bridge, uow=uow_fin
    )
    finalized = await fin_uc.execute(
        user_id=uid,
        session_id=started.session.id,
        early_stop=True,
        completed_task_ids=[],
        takeaway="Mình đã đọc xong phần khái niệm cốt lõi và ghi chú lại các bước thực hành tiếp theo.",
        self_confidence=4,
        now=now + timedelta(minutes=11),
    )
    assert finalized.session.status == SessionStatus.PARTIAL_COMPLETED
    assert task_repo.tasks[t1.id].status == TaskStatus.TODO
    assert task_repo.tasks[t1.id].scheduled_date is None
    assert len(uow_fin.events) == 1


@pytest.mark.asyncio
async def test_today_focus_and_list_tasks_include_milestone_context_and_today_stats() -> None:
    # 2026-11-18 18:00 UTC == 2026-11-19 01:00 Asia/Ho_Chi_Minh
    now_utc = datetime(2026, 11, 18, 18, 0, tzinfo=UTC)
    uid, rid, mid = uuid7(), uuid7(), uuid7()

    user_port = FakeUserQueryPort(
        {
            uid: UserSnapshotDTO(
                id=uid,
                email="learner@focusflow.test",
                full_name="Learner",
                role="LEARNER",
                tier="FREE",
                is_locked=False,
                timezone="Asia/Ho_Chi_Minh",
            )
        }
    )
    ms_ctx = MilestoneExecutionContextDTO(
        milestone_id=mid,
        roadmap_id=rid,
        sequence_order=2,
        title="Milestone 2: Async Workers",
        learning_outcomes=("Hiểu Redis Streams", "Triển khai Sweeper"),
        completion_criteria="Chạy được test integration",
    )
    bridge = FakePlanningBridge(user_id=uid, roadmap_id=rid, milestones={mid: ms_ctx})

    t_today = Task(
        id=uuid7(),
        roadmap_id=rid,
        milestone_id=mid,
        title="Task Hôm Nay",
        estimated_minutes=45,
        scheduled_date=date(2026, 11, 19),
        created_at=now_utc,
        updated_at=now_utc,
    )
    task_repo = FakeTaskRepo([t_today])

    # Local day in Asia/Ho_Chi_Minh is 2026-11-19 -> [2026-11-18 17:00 UTC, 2026-11-19 17:00 UTC)
    s_completed = StudySession(
        id=uuid7(),
        user_id=uid,
        roadmap_id=rid,
        started_at=datetime(2026, 11, 18, 17, 10, tzinfo=UTC),
        ended_at=datetime(2026, 11, 18, 17, 45, tzinfo=UTC),
        planned_minutes=45,
        actual_minutes=35,
        status=SessionStatus.COMPLETED,
        last_heartbeat_at=datetime(2026, 11, 18, 17, 45, tzinfo=UTC),
        created_at=now_utc,
        updated_at=now_utc,
    )
    s_partial = StudySession(
        id=uuid7(),
        user_id=uid,
        roadmap_id=rid,
        started_at=datetime(2026, 11, 18, 17, 50, tzinfo=UTC),
        ended_at=datetime(2026, 11, 18, 17, 59, tzinfo=UTC),
        planned_minutes=20,
        actual_minutes=12,
        status=SessionStatus.PARTIAL_COMPLETED,
        last_heartbeat_at=datetime(2026, 11, 18, 17, 59, tzinfo=UTC),
        created_at=now_utc,
        updated_at=now_utc,
    )
    # Earlier local day (2026-11-18 23:30 ICT = 16:30 UTC) -> excluded from 2026-11-19
    s_yesterday = StudySession(
        id=uuid7(),
        user_id=uid,
        roadmap_id=rid,
        started_at=datetime(2026, 11, 18, 16, 0, tzinfo=UTC),
        ended_at=datetime(2026, 11, 18, 16, 30, tzinfo=UTC),
        planned_minutes=30,
        actual_minutes=30,
        status=SessionStatus.COMPLETED,
        last_heartbeat_at=datetime(2026, 11, 18, 16, 30, tzinfo=UTC),
        created_at=now_utc,
        updated_at=now_utc,
    )
    # Cancelled today -> excluded
    s_cancelled = StudySession(
        id=uuid7(),
        user_id=uid,
        roadmap_id=rid,
        started_at=datetime(2026, 11, 18, 17, 1, tzinfo=UTC),
        ended_at=datetime(2026, 11, 18, 17, 4, tzinfo=UTC),
        planned_minutes=30,
        actual_minutes=3,
        status=SessionStatus.CANCELLED,
        last_heartbeat_at=datetime(2026, 11, 18, 17, 4, tzinfo=UTC),
        created_at=now_utc,
        updated_at=now_utc,
    )

    sess_repo = FakeSessionRepo([s_completed, s_partial, s_yesterday, s_cancelled])

    focus_uc = GetTodayFocusUseCase(
        session_repo=sess_repo,
        task_repo=task_repo,
        planning_bridge=bridge,
        user_query_port=user_port,
    )
    focus = await focus_uc.execute(user_id=uid, now=now_utc)
    assert focus.local_date == date(2026, 11, 19)
    assert focus.completed_sessions_today == 2
    assert focus.studied_minutes_today == 47
    assert focus.focus_task is not None
    assert focus.focus_task.milestone_sequence == 2
    assert focus.focus_task.milestone_title == "Milestone 2: Async Workers"
    assert focus.focus_task.learning_outcomes == ("Hiểu Redis Streams", "Triển khai Sweeper")
    assert focus.focus_task.completion_criteria == "Chạy được test integration"

    list_uc = ListTasksUseCase(
        task_repo=task_repo,
        planning_bridge=bridge,
        user_query_port=user_port,
    )
    listed = await list_uc.execute(user_id=uid, roadmap_id=rid, now=now_utc)
    assert len(listed) == 1
    assert listed[0].milestone_title == "Milestone 2: Async Workers"


@pytest.mark.asyncio
async def test_sticky_notes_crud_idor_404_and_studio_config() -> None:
    now = datetime(2026, 11, 18, 10, 0, tzinfo=UTC)
    owner_id, other_id = uuid7(), uuid7()
    sess_repo = FakeSessionRepo()

    get_cfg_uc = GetStudioConfigUseCase(session_repo=sess_repo)
    default_cfg = await get_cfg_uc.execute(user_id=owner_id)
    assert default_cfg.scene == "lofi-night"
    assert default_cfg.updated_at is None

    upsert_cfg_uc = UpsertStudioConfigUseCase(session_repo=sess_repo, uow=FakeUow())
    saved_cfg = await upsert_cfg_uc.execute(
        user_id=owner_id,
        scene="library",
        clock_style="editorial",
        clock_size="md",
        show_seconds=False,
        show_in_tab_title=True,
        tab_guard_enabled=True,
        zen_lock_enabled=True,
        blocklist=["youtube.com"],
        parking_lot=[{"id": "p1", "text": "Đọc tài liệu ADR-006", "created_at": now.isoformat()}],
        now=now,
    )
    assert saved_cfg.scene == "library"
    assert saved_cfg.clock_style == "editorial"
    assert saved_cfg.updated_at == now

    loaded_cfg = await get_cfg_uc.execute(user_id=owner_id)
    assert loaded_cfg.scene == "library"
    assert loaded_cfg.parking_lot[0]["text"] == "Đọc tài liệu ADR-006"

    # Sentinel studio config must NOT leak into sticky notes list
    list_notes_uc = ListStickyNotesUseCase(session_repo=sess_repo)
    assert await list_notes_uc.execute(user_id=owner_id) == []

    # Create, list, update, delete sticky note
    create_note_uc = CreateStickyNoteUseCase(session_repo=sess_repo, uow=FakeUow())
    created = await create_note_uc.execute(
        user_id=owner_id,
        title="Công thức Pomodoro",
        body="25 phút học + 5 phút nghỉ",
        color="amber",
        pos_x=10.0,
        pos_y=20.0,
        z_index=2,
        now=now,
    )
    assert created.title == "Công thức Pomodoro"
    assert created.color == "amber"

    listed_notes = await list_notes_uc.execute(user_id=owner_id)
    assert len(listed_notes) == 1
    assert listed_notes[0].id == created.id

    update_note_uc = UpdateStickyNoteUseCase(session_repo=sess_repo, uow=FakeUow())
    updated = await update_note_uc.execute(
        user_id=owner_id,
        note_id=created.id,
        body="50 phút học + 10 phút nghỉ",
        pinned=False,
        now=now + timedelta(minutes=5),
    )
    assert updated.body == "50 phút học + 10 phút nghỉ"
    assert updated.pinned is False
    assert updated.title == "Công thức Pomodoro"

    # IDOR check: another user gets NOTE_NOT_FOUND -> mapped to 404
    with pytest.raises(ExecutionDomainError) as exc_idor_upd:
        await update_note_uc.execute(user_id=other_id, note_id=created.id, title="Hacked")
    assert exc_idor_upd.value.code == "NOTE_NOT_FOUND"
    assert _handle_execution_error(exc_idor_upd.value).status_code == 404

    delete_note_uc = DeleteStickyNoteUseCase(session_repo=sess_repo, uow=FakeUow())
    with pytest.raises(ExecutionDomainError) as exc_idor_del:
        await delete_note_uc.execute(user_id=other_id, note_id=created.id)
    assert exc_idor_del.value.code == "NOTE_NOT_FOUND"
    assert _handle_execution_error(exc_idor_del.value).status_code == 404

    await delete_note_uc.execute(user_id=owner_id, note_id=created.id)
    assert await list_notes_uc.execute(user_id=owner_id) == []

    # Studio config still intact after sticky note deletion
    assert (await get_cfg_uc.execute(user_id=owner_id)).scene == "library"
