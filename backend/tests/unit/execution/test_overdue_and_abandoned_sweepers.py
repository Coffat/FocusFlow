from collections import namedtuple
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

import pytest
from uuid6 import uuid7

from src.evaluation.presentation.tasks import (
    sweep_overdue_tasks_and_anti_loop as evaluation_sweep_overdue_tasks,
)
from src.execution.infrastructure.orm.session_orm import SessionTaskORM, StudySessionORM
from src.execution.infrastructure.orm.task_orm import TaskORM
from src.execution.presentation.tasks import (
    DefaultNotificationService,
    deduct_overdue_reschedule_budget,
    sweep_abandoned_study_sessions,
    sweep_overdue_tasks_and_anti_loop,
)
from src.shared_kernel.infrastructure.outbox.models import OutboxEventORM

RoadmapRow = namedtuple(
    "RoadmapRow",
    [
        "id",
        "user_id",
        "title",
        "weekly_reschedule_budget",
        "weekly_reschedule_used",
        "budget_week_start",
    ],
)
UserRow = namedtuple("UserRow", ["id", "email"])


class MockQueryResult:
    def __init__(self, items: list[Any]) -> None:
        self._items = items

    def scalars(self) -> "MockQueryResult":
        return self

    def all(self) -> list[Any]:
        return list(self._items)

    def scalar_one_or_none(self) -> Any | None:
        return self._items[0] if self._items else None

    def one_or_none(self) -> Any | None:
        return self._items[0] if self._items else None


class MockAsyncSession:
    def __init__(
        self,
        study_sessions: list[StudySessionORM] | None = None,
        session_tasks: list[SessionTaskORM] | None = None,
        tasks: list[TaskORM] | None = None,
        roadmaps: list[Any] | None = None,
        users: list[Any] | None = None,
    ) -> None:
        self.study_sessions = study_sessions or []
        self.session_tasks = session_tasks or []
        self.tasks = tasks or []
        self.roadmaps = {r.id: r for r in (roadmaps or [])}
        self.users = {u.id: u for u in (users or [])}
        self.added: list[Any] = []
        self.executed_statements: list[Any] = []
        self.bind = None

    async def __aenter__(self) -> "MockAsyncSession":
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass

    def begin(self) -> "MockAsyncSession":
        return self

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def execute(self, stmt: Any, params: dict[str, Any] | None = None) -> MockQueryResult:
        self.executed_statements.append((stmt, params))
        stmt_str = str(stmt).upper()

        # 1. StudySessionORM query
        if "STUDY_SESSIONS" in stmt_str and "SELECT" in stmt_str:
            # Check for abandoned query
            matching = [s for s in self.study_sessions if s.status == "IN_PROGRESS"]
            return MockQueryResult(matching)

        # 2. session_tasks check
        if "SESSION_TASKS" in stmt_str:
            compiled_params = stmt.compile().params if hasattr(stmt, "compile") else {}
            sid_filter = next(
                (v for k, v in compiled_params.items() if "session_id" in k),
                None,
            )
            if sid_filter is not None:
                return MockQueryResult(
                    [st for st in self.session_tasks if st.session_id == sid_filter]
                )
            return MockQueryResult(self.session_tasks)

        # 3. TaskORM query
        if "TASKS" in stmt_str and "SELECT" in stmt_str:
            compiled_params = stmt.compile().params if hasattr(stmt, "compile") else {}
            id_filter = next(
                (
                    v
                    for k, v in compiled_params.items()
                    if "id" in k and isinstance(v, (list, tuple, set))
                ),
                None,
            )
            if id_filter is not None:
                id_set = set(id_filter)
                return MockQueryResult([t for t in self.tasks if t.id in id_set])
            return MockQueryResult(self.tasks)

        # 4. Roadmaps select
        if "ROADMAPS" in stmt_str and "SELECT" in stmt_str:
            if params and "rid" in params:
                r = self.roadmaps.get(params["rid"])
                return MockQueryResult([r] if r else [])
            return MockQueryResult(list(self.roadmaps.values()))

        # 5. Roadmaps update
        if "ROADMAPS" in stmt_str and "UPDATE" in stmt_str:
            if params and "rid" in params and "new_used" in params:
                rid = params["rid"]
                if rid in self.roadmaps:
                    old = self.roadmaps[rid]
                    self.roadmaps[rid] = old._replace(weekly_reschedule_used=params["new_used"])
            return MockQueryResult([])

        # 6. Users select
        if "USERS" in stmt_str and "SELECT" in stmt_str:
            return MockQueryResult(list(self.users.values()))

        # 7. Outbox events select (for deduplication check)
        if "OUTBOX_EVENTS" in stmt_str and "SELECT" in stmt_str:
            matching_alerts = [
                (e.aggregate_id,)
                for e in self.added
                if isinstance(e, OutboxEventORM) and e.event_type == "OverdueTaskAlertEvent"
            ]
            return MockQueryResult(matching_alerts)

        return MockQueryResult([])


class MockNotificationService:
    def __init__(self) -> None:
        self.alerts: list[dict[str, Any]] = []

    async def send_overdue_alert(
        self,
        *,
        user_id: UUID,
        email: str,
        overdue_task_titles: list[str],
        remaining_reschedule_budget: int,
    ) -> None:
        self.alerts.append(
            {
                "user_id": user_id,
                "email": email,
                "titles": overdue_task_titles,
                "remaining_budget": remaining_reschedule_budget,
            }
        )


@pytest.mark.asyncio
async def test_sweep_abandoned_study_sessions_standard_partial_and_cancelled() -> None:
    now = datetime(2026, 11, 18, 12, 0, 0, tzinfo=UTC)
    user_id = uuid7()
    roadmap_id = uuid7()

    # Session 1: Standard >= 50% (actual=30m, planned=60m) -> PARTIAL_COMPLETED
    s1 = StudySessionORM(
        id=uuid7(),
        user_id=user_id,
        roadmap_id=roadmap_id,
        status="IN_PROGRESS",
        session_mode="STANDARD",
        planned_minutes=60,
        actual_minutes=30,
        started_at=now - timedelta(minutes=40),
        last_heartbeat_at=now - timedelta(minutes=10),
    )

    # Session 2: Standard < 50% (actual=15m, planned=60m) -> CANCELLED
    s2 = StudySessionORM(
        id=uuid7(),
        user_id=user_id,
        roadmap_id=roadmap_id,
        status="IN_PROGRESS",
        session_mode="STANDARD",
        planned_minutes=60,
        actual_minutes=15,
        started_at=now - timedelta(minutes=40),
        last_heartbeat_at=now - timedelta(minutes=10),
    )

    # Session 3: MVS >= 10m (actual=10m, planned=60m) -> PARTIAL_COMPLETED (OS-01 exception)
    s3 = StudySessionORM(
        id=uuid7(),
        user_id=user_id,
        roadmap_id=roadmap_id,
        status="IN_PROGRESS",
        session_mode="MVS",
        planned_minutes=60,
        actual_minutes=10,
        started_at=now - timedelta(minutes=20),
        last_heartbeat_at=now - timedelta(minutes=10),
    )

    # Session 4: MVS < 10m (actual=8m, planned=60m) -> CANCELLED
    s4 = StudySessionORM(
        id=uuid7(),
        user_id=user_id,
        roadmap_id=roadmap_id,
        status="IN_PROGRESS",
        session_mode="MVS",
        planned_minutes=60,
        actual_minutes=8,
        started_at=now - timedelta(minutes=20),
        last_heartbeat_at=now - timedelta(minutes=10),
    )

    session = MockAsyncSession(study_sessions=[s1, s2, s3, s4])

    def session_factory() -> MockAsyncSession:
        return session

    swept = await sweep_abandoned_study_sessions(session_factory=session_factory, now=now)
    assert swept == 4

    # Assert statuses and end times
    assert s1.status == "PARTIAL_COMPLETED"
    assert s1.ended_at == s1.last_heartbeat_at

    assert s2.status == "CANCELLED"
    assert s2.ended_at == s2.last_heartbeat_at

    assert s3.status == "PARTIAL_COMPLETED"
    assert s3.ended_at == s3.last_heartbeat_at

    assert s4.status == "CANCELLED"
    assert s4.ended_at == s4.last_heartbeat_at

    # Assert outbox events were emitted and pending_takeaway is set
    assert s1.pending_takeaway is True
    assert s2.pending_takeaway is True
    assert s3.pending_takeaway is True
    assert s4.pending_takeaway is True
    outbox_events = [obj for obj in session.added if isinstance(obj, OutboxEventORM)]
    assert len(outbox_events) == 4
    for ev in outbox_events:
        assert ev.event_type == "StudySessionAbandonedEvent"
        assert "recovered_duration_seconds" in ev.payload


@pytest.mark.asyncio
async def test_sweep_abandoned_session_sets_pending_takeaway_and_returns_incomplete_tasks_to_backlog() -> (
    None
):
    now = datetime(2026, 11, 18, 12, 0, 0, tzinfo=UTC)
    user_id = uuid7()
    roadmap_id = uuid7()
    milestone_id = uuid7()
    schedule_id = uuid7()
    session_id = uuid7()

    abandoned = StudySessionORM(
        id=session_id,
        user_id=user_id,
        roadmap_id=roadmap_id,
        status="IN_PROGRESS",
        session_mode="STANDARD",
        planned_minutes=60,
        actual_minutes=15,
        started_at=now - timedelta(minutes=30),
        last_heartbeat_at=now - timedelta(minutes=10),
        pending_takeaway=False,
    )

    t_incomplete = TaskORM(
        id=uuid7(),
        roadmap_id=roadmap_id,
        milestone_id=milestone_id,
        official_schedule_id=schedule_id,
        title="Incomplete Task",
        estimated_minutes=30,
        scheduled_date=now.date(),
        scheduled_start=now - timedelta(minutes=30),
        scheduled_end=now,
        status="IN_PROGRESS",
        reschedule_count=0,
    )
    t_completed = TaskORM(
        id=uuid7(),
        roadmap_id=roadmap_id,
        milestone_id=milestone_id,
        official_schedule_id=schedule_id,
        title="Completed Task",
        estimated_minutes=30,
        scheduled_date=now.date(),
        scheduled_start=now - timedelta(minutes=60),
        scheduled_end=now - timedelta(minutes=30),
        status="COMPLETED",
        completed_at=now - timedelta(minutes=20),
        reschedule_count=0,
    )

    st_incomplete = SessionTaskORM(
        id=uuid7(),
        session_id=session_id,
        task_id=t_incomplete.id,
        allocated_minutes=30,
        actual_minutes=15,
        status_after_session="IN_PROGRESS",
    )
    st_completed = SessionTaskORM(
        id=uuid7(),
        session_id=session_id,
        task_id=t_completed.id,
        allocated_minutes=30,
        actual_minutes=30,
        status_after_session="COMPLETED",
    )

    mock_db = MockAsyncSession(
        study_sessions=[abandoned],
        session_tasks=[st_incomplete, st_completed],
        tasks=[t_incomplete, t_completed],
    )

    swept = await sweep_abandoned_study_sessions(session_factory=lambda: mock_db, now=now)
    assert swept == 1
    assert abandoned.status == "PARTIAL_COMPLETED"  # has_completed_task=True
    assert abandoned.pending_takeaway is True

    assert st_incomplete.status_after_session == "TODO"
    assert st_completed.status_after_session == "COMPLETED"

    assert t_incomplete.status == "TODO"
    assert t_incomplete.scheduled_date is None
    assert t_incomplete.scheduled_start is None
    assert t_incomplete.scheduled_end is None
    assert t_incomplete.official_schedule_id is None

    assert t_completed.status == "COMPLETED"
    assert t_completed.scheduled_date == now.date()
    assert t_completed.official_schedule_id == schedule_id


@pytest.mark.asyncio
async def test_sweep_overdue_tasks_anti_loop_and_notifications() -> None:
    now = datetime(2026, 11, 18, 12, 0, 0, tzinfo=UTC)
    effective_today = now.date()
    yesterday = effective_today - timedelta(days=1)

    user_id = uuid7()
    roadmap_id = uuid7()
    milestone_id = uuid7()

    # Task 1: Normal overdue task (reschedule_count=1)
    t1 = TaskORM(
        id=uuid7(),
        roadmap_id=roadmap_id,
        milestone_id=milestone_id,
        title="Overdue Task 1",
        estimated_minutes=60,
        scheduled_date=yesterday,
        status="TODO",
        reschedule_count=1,
    )

    # Task 2: Stalled overdue task (reschedule_count=3 -> triggers anti-loop breaker)
    t2 = TaskORM(
        id=uuid7(),
        roadmap_id=roadmap_id,
        milestone_id=milestone_id,
        title="Stalled Overdue Task 2",
        estimated_minutes=45,
        scheduled_date=yesterday,
        status="IN_PROGRESS",
        reschedule_count=3,
    )

    roadmap_row = RoadmapRow(
        id=roadmap_id,
        user_id=user_id,
        title="Test Roadmap",
        weekly_reschedule_budget=3,
        weekly_reschedule_used=1,
        budget_week_start=effective_today - timedelta(days=2),
    )
    user_row = UserRow(id=user_id, email="learner@focusflow.test")

    session = MockAsyncSession(
        tasks=[t1, t2],
        roadmaps=[roadmap_row],
        users=[user_row],
    )

    def session_factory() -> MockAsyncSession:
        return session

    notifier = MockNotificationService()
    swept = await sweep_overdue_tasks_and_anti_loop(
        session_factory=session_factory,
        now=now,
        notification_service=notifier,
    )
    assert swept == 2

    # Invariant: scheduled_date must NEVER be mutated silently
    assert t1.scheduled_date == yesterday
    assert t2.scheduled_date == yesterday

    # Verify anti-loop breaker event emitted for t2 (reschedule_count >= 3)
    outbox_events = [obj for obj in session.added if isinstance(obj, OutboxEventORM)]
    stalled_events = [
        e for e in outbox_events if e.event_type == "TaskStalledThresholdReachedEvent"
    ]
    assert len(stalled_events) == 1
    assert stalled_events[0].aggregate_id == t2.id

    # Verify overdue alert notification was dispatched via Transactional Outbox (OverdueTaskAlertEvent)
    alert_events = [e for e in outbox_events if e.event_type == "OverdueTaskAlertEvent"]
    assert len(alert_events) == 1
    alert = alert_events[0]
    assert alert.aggregate_id == user_id
    assert alert.payload["user_id"] == str(user_id)
    assert alert.payload["email"] == "learner@focusflow.test"
    assert "Overdue Task 1" in alert.payload["overdue_task_titles"]
    assert "Stalled Overdue Task 2" in alert.payload["overdue_task_titles"]
    assert alert.payload["remaining_reschedule_budget"] == 2  # 3 - 1 = 2
    assert alert.payload["alert_date"] == effective_today.isoformat()

    # Verify notification deduplication: running sweeper a second time on the same day does not emit duplicate alert
    swept_second_run = await sweep_overdue_tasks_and_anti_loop(
        session_factory=session_factory,
        now=now,
    )
    assert swept_second_run == 2
    all_alert_events = [
        e
        for e in session.added
        if isinstance(e, OutboxEventORM) and e.event_type == "OverdueTaskAlertEvent"
    ]
    assert len(all_alert_events) == 1  # Still exactly 1, no duplicate emitted!


@pytest.mark.asyncio
async def test_deduct_overdue_reschedule_budget() -> None:
    roadmap_id = uuid7()
    user_id = uuid7()

    roadmap_row = RoadmapRow(
        id=roadmap_id,
        user_id=user_id,
        title="Test Roadmap",
        weekly_reschedule_budget=3,
        weekly_reschedule_used=1,
        budget_week_start=date(2026, 11, 16),
    )

    session = MockAsyncSession(roadmaps=[roadmap_row])

    # 1. Normal deduction: used 1 -> 2
    new_used = await deduct_overdue_reschedule_budget(roadmap_id, session=session)  # type: ignore[arg-type]
    assert new_used == 2

    # 2. Another deduction: used 2 -> 3
    new_used = await deduct_overdue_reschedule_budget(roadmap_id, session=session)  # type: ignore[arg-type]
    assert new_used == 3

    # 3. Exhausted budget: used 3 >= 3 -> raises ValueError
    with pytest.raises(ValueError, match="Weekly reschedule budget exhausted"):
        await deduct_overdue_reschedule_budget(roadmap_id, session=session)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_evaluation_sweeper_delegation() -> None:
    now = datetime(2026, 11, 18, 12, 0, 0, tzinfo=UTC)
    session = MockAsyncSession(tasks=[])

    def session_factory() -> MockAsyncSession:
        return session

    res = await evaluation_sweep_overdue_tasks(session_factory=session_factory, now=now)
    assert res == 0


@pytest.mark.asyncio
async def test_default_notification_service_handles_missing_email() -> None:
    svc = DefaultNotificationService()
    # Should not raise when email is empty string
    await svc.send_overdue_alert(
        user_id=uuid7(),
        email="",
        overdue_task_titles=["Task A"],
        remaining_reschedule_budget=2,
    )


@pytest.mark.asyncio
async def test_no_duplicate_taskiq_cron_registrations() -> None:
    from src.evaluation.presentation.tasks import (
        sweep_overdue_tasks_and_anti_loop as evaluation_task,
    )
    from src.execution.presentation.tasks import (
        sweep_overdue_tasks_and_anti_loop as execution_task,
    )

    exec_labels = getattr(execution_task, "labels", {})
    eval_labels = getattr(evaluation_task, "labels", {})

    # Execution sweeper holds the single scheduled daily cron at 17:05 UTC (00:05 UTC+7)
    assert "schedule" in exec_labels
    assert exec_labels["schedule"] == [{"cron": "5 17 * * *"}]

    # Evaluation sweeper delegates without duplicate cron schedule registration
    assert "schedule" not in eval_labels or eval_labels["schedule"] == []
