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
from src.planning.public_api import get_latest_applied_proposal_data

_TASK_TYPES: tuple[str, ...] = ("THEORY", "PRACTICE", "REVIEW", "PROJECT")


class WeeklyExecutionMetricsAdapter(WeeklyExecutionMetricsQueryPort):
    """Deterministic SQLAlchemy adapter reading weekly execution metrics for Evaluation."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _load_task_type_lookup(
        self,
        roadmap_id: UUID,
    ) -> tuple[dict[str, str], dict[str, str]]:
        proposals = await get_latest_applied_proposal_data(
            self._session,
            roadmap_id,
            limit=3,
        )
        by_id: dict[str, str] = {}
        by_title: dict[str, str] = {}
        for proposal_data in proposals:
            raw_tasks = proposal_data.get("tasks")
            if not isinstance(raw_tasks, list):
                continue
            for item in raw_tasks:
                if not isinstance(item, dict):
                    continue
                t_type = str(item.get("task_type") or "").strip().upper()
                if t_type not in _TASK_TYPES:
                    continue
                tid = item.get("task_id")
                if tid is not None:
                    by_id.setdefault(str(tid), t_type)
                title = str(item.get("title") or "").strip().lower()
                if title:
                    by_title.setdefault(title, t_type)
        return by_id, by_title

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

        prev_start_dt = start_dt - timedelta(days=7)
        prev_sess_stmt = select(
            func.coalesce(func.sum(StudySessionORM.actual_minutes), 0),
        ).where(
            StudySessionORM.user_id == user_id,
            StudySessionORM.roadmap_id == roadmap_id,
            StudySessionORM.started_at >= prev_start_dt,
            StudySessionORM.started_at < start_dt,
            StudySessionORM.status.in_(("COMPLETED", "PARTIAL_COMPLETED")),
        )
        previous_week_completed_minutes = int(
            (await self._session.execute(prev_sess_stmt)).scalar() or 0
        )
        week_over_week_delta_pct: float | None = None
        if previous_week_completed_minutes > 0:
            week_over_week_delta_pct = round(
                (
                    (completed_minutes - previous_week_completed_minutes)
                    / previous_week_completed_minutes
                )
                * 100.0,
                1,
            )

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

        completed_task_stmt = select(
            TaskORM.id,
            TaskORM.title,
            TaskORM.estimated_minutes,
        ).where(
            TaskORM.roadmap_id == roadmap_id,
            TaskORM.status == "COMPLETED",
            TaskORM.completed_at.is_not(None),
            TaskORM.completed_at >= start_dt,
            TaskORM.completed_at < end_dt,
        )
        completed_task_rows = (await self._session.execute(completed_task_stmt)).all()
        task_type_breakdown: dict[str, dict[str, int]] = {
            t_type: {"completed_tasks_count": 0, "completed_minutes": 0} for t_type in _TASK_TYPES
        }
        if completed_task_rows:
            type_by_id, type_by_title = await self._load_task_type_lookup(roadmap_id)
            for tid, title, est_min in completed_task_rows:
                resolved_type = type_by_id.get(str(tid)) or type_by_title.get(
                    str(title or "").strip().lower()
                )
                if resolved_type in task_type_breakdown:
                    task_type_breakdown[resolved_type]["completed_tasks_count"] += 1
                    task_type_breakdown[resolved_type]["completed_minutes"] += int(est_min or 0)

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
            task_type_breakdown=task_type_breakdown,
            previous_week_completed_minutes=previous_week_completed_minutes,
            week_over_week_delta_pct=week_over_week_delta_pct,
        )


def _weekly_execution_metrics_factory_impl(
    session: AsyncSession,
) -> WeeklyExecutionMetricsQueryPort:
    return WeeklyExecutionMetricsAdapter(session)


register_weekly_execution_metrics_factory(_weekly_execution_metrics_factory_impl)
