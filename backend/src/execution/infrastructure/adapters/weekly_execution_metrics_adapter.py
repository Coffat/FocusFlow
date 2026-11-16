from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.execution.infrastructure.orm.session_orm import StudySessionORM
from src.execution.infrastructure.orm.task_orm import TaskORM
from src.execution.public_api import (
    WeeklyExecutionMetricsDTO,
    WeeklyExecutionMetricsQueryPort,
    register_weekly_execution_metrics_factory,
)


class WeeklyExecutionMetricsAdapter(WeeklyExecutionMetricsQueryPort):
    """Deterministic SQLAlchemy adapter reading weekly execution metrics for Evaluation."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_roadmap_period_metrics(
        self,
        *,
        user_id: UUID,
        roadmap_id: UUID,
        period_start: date,
        period_end: date,
    ) -> WeeklyExecutionMetricsDTO:
        start_dt = datetime.combine(period_start, time.min, tzinfo=UTC)
        end_dt = datetime.combine(period_end + timedelta(days=1), time.min, tzinfo=UTC)

        sess_stmt = select(
            func.count(StudySessionORM.id),
            func.coalesce(func.sum(StudySessionORM.actual_minutes), 0),
        ).where(
            StudySessionORM.user_id == user_id,
            StudySessionORM.roadmap_id == roadmap_id,
            StudySessionORM.started_at >= start_dt,
            StudySessionORM.started_at < end_dt,
            StudySessionORM.status.in_(("COMPLETED", "PARTIAL_COMPLETED")),
        )
        sess_row = (await self._session.execute(sess_stmt)).one()
        completed_sessions_count = int(sess_row[0] or 0)
        completed_minutes = int(sess_row[1] or 0)

        task_stmt = select(TaskORM.status, TaskORM.estimated_minutes).where(
            TaskORM.roadmap_id == roadmap_id,
            TaskORM.status != "CANCELLED",
            TaskORM.scheduled_date >= period_start,
            TaskORM.scheduled_date <= period_end,
        )
        task_rows = (await self._session.execute(task_stmt)).all()
        planned_tasks_count = len(task_rows)
        completed_tasks_count = sum(1 for status_val, _ in task_rows if status_val == "COMPLETED")
        planned_minutes = sum(int(est or 0) for _, est in task_rows)

        overdue_stmt = select(func.count(TaskORM.id)).where(
            TaskORM.roadmap_id == roadmap_id,
            TaskORM.status.in_(("TODO", "IN_PROGRESS")),
            TaskORM.scheduled_date.is_not(None),
            TaskORM.scheduled_date <= period_end,
        )
        overdue_tasks_count = int((await self._session.execute(overdue_stmt)).scalar() or 0)

        adherence_rate_pct: float | None = None
        if planned_tasks_count > 0:
            adherence_rate_pct = round((completed_tasks_count / planned_tasks_count) * 100.0, 1)
        elif planned_minutes > 0:
            adherence_rate_pct = round(min(100.0, (completed_minutes / planned_minutes) * 100.0), 1)

        return WeeklyExecutionMetricsDTO(
            completed_minutes=completed_minutes,
            planned_minutes=planned_minutes,
            completed_sessions_count=completed_sessions_count,
            completed_tasks_count=completed_tasks_count,
            planned_tasks_count=planned_tasks_count,
            overdue_tasks_count=overdue_tasks_count,
            adherence_rate_pct=adherence_rate_pct,
        )


def _weekly_execution_metrics_factory_impl(
    session: AsyncSession,
) -> WeeklyExecutionMetricsQueryPort:
    return WeeklyExecutionMetricsAdapter(session)


register_weekly_execution_metrics_factory(_weekly_execution_metrics_factory_impl)
