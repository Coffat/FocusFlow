import logging
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.account.public_api import create_user_query_port
from src.execution.infrastructure.orm.session_orm import SessionTaskORM, StudySessionORM
from src.execution.infrastructure.orm.task_orm import TaskORM
from src.execution.public_api import (
    NotificationServicePort,
    OverdueTaskAlertEvent,
    StudySessionAbandonedEvent,
)
from src.planning.public_api import (
    TaskStalledThresholdReachedEvent,
    create_planning_execution_bridge,
)
from src.shared_kernel.infrastructure.database.session import async_session_factory
from src.shared_kernel.infrastructure.outbox.models import OutboxEventORM
from src.shared_kernel.infrastructure.worker.broker import broker
from src.shared_kernel.logging import correlation_id_ctx

logger = logging.getLogger("focusflow.execution.tasks")


class DefaultNotificationService:
    """Default adapter logging overdue alerts (asynchronous email dispatch handled via Outbox)."""

    async def send_overdue_alert(
        self,
        *,
        user_id: UUID,
        email: str,
        overdue_task_titles: list[str],
        remaining_reschedule_budget: int,
    ) -> None:
        if not email:
            logger.info("No email registered for user %s; skipping overdue alert email", user_id)
            return
        logger.info(
            "Overdue alert for user %s (%s): %d tasks, budget remaining %d",
            user_id,
            email,
            len(overdue_task_titles),
            remaining_reschedule_budget,
        )


@broker.task(schedule=[{"cron": "* * * * *"}])
async def sweep_abandoned_study_sessions(
    *,
    session_factory: Any = None,
    now: datetime | None = None,
) -> int:
    """Sweep IN_PROGRESS study sessions without heartbeat for >5 minutes (ASR-05, OS-01)."""
    current_time = now or datetime.now(UTC)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=UTC)
    cutoff = current_time - timedelta(minutes=5)

    session_maker = session_factory or async_session_factory
    async with session_maker() as session:
        async with session.begin():
            stmt = select(StudySessionORM).where(
                StudySessionORM.status == "IN_PROGRESS",
                StudySessionORM.last_heartbeat_at < cutoff,
            )
            bind = session.bind
            if bind is not None and getattr(bind.dialect, "name", "") == "postgresql":
                stmt = stmt.with_for_update(skip_locked=True)

            result = await session.execute(stmt)
            abandoned_sessions = list(result.scalars().all())
            swept_count = 0

            for s in abandoned_sessions:
                # Rule OS-01:
                # 1. Minimum Viable Session (MVS): actual_minutes >= 10
                # 2. Standard Session: actual_minutes >= 0.5 * planned_minutes
                # 3. Or at least one session task completed
                st_rows: list[SessionTaskORM] = []
                try:
                    st_stmt = select(SessionTaskORM).where(SessionTaskORM.session_id == s.id)
                    st_rows = list((await session.execute(st_stmt)).scalars().all())
                except Exception:
                    st_rows = []

                has_completed_task = any(st.status_after_session == "COMPLETED" for st in st_rows)

                is_partial = False
                if s.session_mode == "MVS" and s.actual_minutes >= 10:
                    is_partial = True
                elif s.actual_minutes >= (0.5 * s.planned_minutes):
                    is_partial = True
                elif has_completed_task:
                    is_partial = True

                new_status = "PARTIAL_COMPLETED" if is_partial else "CANCELLED"
                end_time = (
                    s.last_heartbeat_at if s.last_heartbeat_at >= s.started_at else s.started_at
                )

                s.status = new_status
                s.ended_at = end_time
                s.pending_takeaway = True
                s.updated_at = current_time

                incomplete_task_ids: list[UUID] = []
                for st in st_rows:
                    if st.status_after_session != "COMPLETED":
                        st.status_after_session = "TODO"
                        st.updated_at = current_time
                        incomplete_task_ids.append(st.task_id)

                if incomplete_task_ids:
                    task_stmt = select(TaskORM).where(TaskORM.id.in_(incomplete_task_ids))
                    if bind is not None and getattr(bind.dialect, "name", "") == "postgresql":
                        task_stmt = task_stmt.with_for_update(skip_locked=True)
                    task_rows = list((await session.execute(task_stmt)).scalars().all())
                    for task_row in task_rows:
                        if task_row.status != "COMPLETED":
                            task_row.status = "TODO"
                            task_row.scheduled_date = None
                            task_row.scheduled_start = None
                            task_row.scheduled_end = None
                            task_row.official_schedule_id = None
                            task_row.updated_at = current_time

                recovered_seconds = int(s.actual_minutes) * 60
                event = StudySessionAbandonedEvent(
                    aggregate_id=s.id,
                    aggregate_type="StudySession",
                    user_id=s.user_id,
                    session_id=s.id,
                    recovered_duration_seconds=recovered_seconds,
                )
                corr_id = correlation_id_ctx.get()
                outbox_entry = OutboxEventORM(
                    id=event.event_id,
                    aggregate_type=event.aggregate_type,
                    aggregate_id=event.aggregate_id,
                    event_type=event.event_type,
                    payload=event.to_payload(),
                    correlation_id=corr_id,
                )
                session.add(outbox_entry)
                swept_count += 1
                logger.info(
                    "Swept abandoned study session %s (user=%s) -> %s, actual_minutes=%d",
                    s.id,
                    s.user_id,
                    new_status,
                    s.actual_minutes,
                )

            return swept_count


# Taskiq scheduler operates in UTC: 17:05 UTC = 00:05 UTC+7 (Indochina Time / ICT).
# Daily sweeper runs 5 minutes past midnight user local time (UC-25, BUSR-23).
@broker.task(schedule=[{"cron": "5 17 * * *"}])  # 17:05 UTC = 00:05 UTC+7 (ICT)
async def sweep_overdue_tasks_and_anti_loop(
    *,
    session_factory: Any = None,
    now: datetime | None = None,
    notification_service: NotificationServicePort | None = None,
) -> int:
    """Sweep overdue tasks, enforce anti-loop circuit breaker (reschedule_count >= 3 -> /isStalled),
    and emit OverdueTaskAlertEvent via Transactional Outbox without mutating scheduled_date
    (UC-25, BUSR-23, FR-ADAPT-001, FR-ADAPT-003)."""
    current_time = now or datetime.now(UTC)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=UTC)
    effective_today = current_time.date()

    _ = notification_service
    session_maker = session_factory or async_session_factory

    async with session_maker() as session:
        async with session.begin():
            stmt = (
                select(TaskORM)
                .where(
                    TaskORM.scheduled_date < effective_today,
                    TaskORM.status.in_(("TODO", "IN_PROGRESS")),
                )
                .order_by(TaskORM.scheduled_date.asc(), TaskORM.id.asc())
            )
            bind = session.bind
            if bind is not None and getattr(bind.dialect, "name", "") == "postgresql":
                stmt = stmt.with_for_update(skip_locked=True)

            res = await session.execute(stmt)
            overdue_tasks = list(res.scalars().all())
            if not overdue_tasks:
                return 0

            # INVARIANT: NEVER mutate t.scheduled_date!
            # Group tasks by roadmap to check roadmap metadata and user mapping via Planning port.
            roadmap_ids = list({t.roadmap_id for t in overdue_tasks})
            planning_bridge = create_planning_execution_bridge(session)
            roadmaps_by_id = await planning_bridge.get_roadmaps_context_by_ids(roadmap_ids)

            # 1. Anti-loop circuit-breaker:
            # When reschedule_count >= 3, derive or mark /isStalled = true
            corr_id = correlation_id_ctx.get()
            for t in overdue_tasks:
                if t.reschedule_count >= 3:
                    rm = roadmaps_by_id.get(t.roadmap_id)
                    user_id = rm.user_id if rm else None
                    if user_id:
                        stalled_event = TaskStalledThresholdReachedEvent(
                            aggregate_id=t.id,
                            aggregate_type="Task",
                            user_id=user_id,
                            task_id=t.id,
                        )
                        outbox_entry = OutboxEventORM(
                            id=stalled_event.event_id,
                            aggregate_type=stalled_event.aggregate_type,
                            aggregate_id=stalled_event.aggregate_id,
                            event_type=stalled_event.event_type,
                            payload=stalled_event.to_payload(),
                            correlation_id=corr_id,
                        )
                        session.add(outbox_entry)
                        logger.warning(
                            "Anti-loop circuit breaker: task %s has reached STALLED threshold (reschedule_count=%d)",
                            t.id,
                            t.reschedule_count,
                        )

            # 2. Reset weekly reschedule budget if new week (SRS v1.3 UC-25 Reset Budget)
            current_monday = effective_today - timedelta(days=effective_today.weekday())
            reset_count = await planning_bridge.reset_weekly_reschedule_budgets(
                roadmap_ids=roadmap_ids,
                current_monday=current_monday,
                now=current_time,
            )
            if reset_count > 0:
                roadmaps_by_id = await planning_bridge.get_roadmaps_context_by_ids(roadmap_ids)

            # 3. Dispatch overdue alert notification via Transactional Outbox (UC-25, BUSR-23)
            # Notification deduplication: check if an overdue alert for this user and date has already been emitted today
            user_tasks: dict[UUID, list[TaskORM]] = defaultdict(list)
            for t in overdue_tasks:
                rm = roadmaps_by_id.get(t.roadmap_id)
                if rm:
                    user_tasks[rm.user_id].append(t)

            user_ids = list(user_tasks.keys())
            users_by_id: dict[UUID, str] = {}
            if user_ids:
                user_query = create_user_query_port(session)
                user_snapshots = await user_query.get_users_by_ids(user_ids)
                users_by_id = {uid: (snap.email or "") for uid, snap in user_snapshots.items()}

            today_start = datetime(
                effective_today.year,
                effective_today.month,
                effective_today.day,
                0,
                0,
                0,
                tzinfo=UTC,
            )
            already_notified_user_ids: set[UUID] = set()
            if user_ids:
                alert_rows = await session.execute(
                    select(OutboxEventORM.aggregate_id).where(
                        OutboxEventORM.aggregate_type == "User",
                        OutboxEventORM.event_type == "OverdueTaskAlertEvent",
                        OutboxEventORM.aggregate_id.in_(user_ids),
                        OutboxEventORM.created_at >= today_start,
                    )
                )
                for row in alert_rows.all():
                    uid = (
                        row[0]
                        if isinstance(row, (tuple, list))
                        else getattr(row, "aggregate_id", row)
                    )
                    if isinstance(uid, UUID):
                        already_notified_user_ids.add(uid)

            for user_id, tasks in user_tasks.items():
                if user_id in already_notified_user_ids:
                    logger.info(
                        "Overdue alert already emitted today for user %s; skipping duplicate alert",
                        user_id,
                    )
                    continue

                email = users_by_id.get(user_id, "")
                # Find minimum remaining reschedule budget among user's active roadmaps
                min_remaining = 3
                for t in tasks:
                    rm = roadmaps_by_id.get(t.roadmap_id)
                    if rm:
                        budget_val = getattr(rm, "weekly_reschedule_budget", 3)
                        used_val = getattr(rm, "weekly_reschedule_used", 0)
                        rem = max(0, int(budget_val) - int(used_val))
                        min_remaining = min(min_remaining, rem)

                titles = [t.title for t in tasks]
                # INVARIANT: Do NOT send email synchronously before DB commit!
                # Emit OverdueTaskAlertEvent into outbox_events in the same transactional unit of work.
                alert_event = OverdueTaskAlertEvent(
                    aggregate_type="User",
                    aggregate_id=user_id,
                    user_id=user_id,
                    email=email,
                    overdue_task_titles=titles,
                    remaining_reschedule_budget=min_remaining,
                    alert_date=effective_today.isoformat(),
                )
                outbox_entry = OutboxEventORM(
                    id=alert_event.event_id,
                    aggregate_type=alert_event.aggregate_type,
                    aggregate_id=alert_event.aggregate_id,
                    event_type=alert_event.event_type,
                    payload=alert_event.to_payload(),
                    correlation_id=corr_id,
                    created_at=current_time,
                )
                session.add(outbox_entry)
                already_notified_user_ids.add(user_id)
                logger.info(
                    "Emitted OverdueTaskAlertEvent to outbox for user %s (%d overdue tasks)",
                    user_id,
                    len(titles),
                )

            return len(overdue_tasks)


async def deduct_overdue_reschedule_budget(
    roadmap_id: UUID,
    *,
    session: AsyncSession,
    now: datetime | None = None,
) -> int:
    """Deduct 1 from weekly_reschedule_budget when overdue reschedule is initiated (UC-23, ADR-010).

    Delegates to PlanningExecutionBridgePort to preserve bounded context isolation.
    """
    current_time = now or datetime.now(UTC)
    bridge = create_planning_execution_bridge(session)
    return await bridge.deduct_overdue_reschedule_budget(
        roadmap_id=roadmap_id,
        now=current_time,
    )
