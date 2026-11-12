from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.execution.infrastructure.orm.session_orm import StudySessionORM
from src.execution.infrastructure.orm.task_orm import TaskORM
from src.execution.public_api import (
    ExecutionDashboardQueryPort,
    ExecutionDayStudyDTO,
    ExecutionKpiStatsDTO,
    ExecutionTodayTaskDTO,
    register_execution_dashboard_factory,
)

_WEEKDAY_LABELS: list[str] = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


class ExecutionDashboardAdapter(ExecutionDashboardQueryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _get_active_roadmaps(self, user_id: UUID) -> dict[UUID, str]:
        stmt = text(
            """
            SELECT id, title
            FROM roadmaps
            WHERE user_id = :u_id AND status = 'ACTIVE'
            """
        )
        res = await self._session.execute(stmt, {"u_id": user_id})
        return {row.id: row.title for row in res.fetchall()}

    async def _get_all_user_roadmap_ids(self, user_id: UUID) -> list[UUID]:
        stmt = text("SELECT id FROM roadmaps WHERE user_id = :u_id")
        res = await self._session.execute(stmt, {"u_id": user_id})
        return [row.id for row in res.fetchall()]

    async def get_today_queue(self, user_id: UUID, today: date) -> list[ExecutionTodayTaskDTO]:
        roadmap_map = await self._get_active_roadmaps(user_id)
        if not roadmap_map:
            return []

        active_roadmap_ids = list(roadmap_map.keys())
        stmt = (
            select(TaskORM)
            .where(
                TaskORM.roadmap_id.in_(active_roadmap_ids),
                TaskORM.scheduled_date == today,
                TaskORM.status.in_(("TODO", "IN_PROGRESS", "COMPLETED")),
            )
            .order_by(
                TaskORM.scheduled_start.asc().nulls_last(),
                TaskORM.created_at.asc(),
            )
        )
        result = await self._session.execute(stmt)
        tasks = list(result.scalars().all())

        queue_items: list[ExecutionTodayTaskDTO] = []
        for task in tasks:
            task_code = f"TSK-{str(task.id)[:8].upper()}"
            roadmap_title = roadmap_map.get(task.roadmap_id, "Lộ trình học tập")

            if task.scheduled_start and task.scheduled_end:
                scheduled_time = (
                    f"{task.scheduled_start.strftime('%H:%M')} - "
                    f"{task.scheduled_end.strftime('%H:%M')}"
                )
            else:
                scheduled_time = f"Dự kiến {task.estimated_minutes}p"

            pomodoro_estimate = max(1, (task.estimated_minutes + 24) // 25)

            display_status = task.status
            if task.status == "TODO":
                display_status = "READY"

            queue_items.append(
                ExecutionTodayTaskDTO(
                    id=task.id,
                    task_code=task_code,
                    title=task.title,
                    roadmap_title=roadmap_title,
                    scheduled_time=scheduled_time,
                    pomodoro_estimate=pomodoro_estimate,
                    duration_minutes=task.estimated_minutes,
                    status=display_status,
                )
            )

        return queue_items

    async def get_7day_study_distribution(
        self, user_id: UUID, today: date
    ) -> list[ExecutionDayStudyDTO]:
        monday = today - timedelta(days=today.weekday())
        week_start = datetime.combine(monday, time.min, tzinfo=UTC)
        week_end = week_start + timedelta(days=7)

        stmt = select(StudySessionORM).where(
            StudySessionORM.user_id == user_id,
            StudySessionORM.started_at >= week_start,
            StudySessionORM.started_at < week_end,
            StudySessionORM.status.in_(("COMPLETED", "PARTIAL_COMPLETED")),
        )
        res = await self._session.execute(stmt)
        sessions = list(res.scalars().all())

        daily_minutes: dict[date, int] = {monday + timedelta(days=i): 0 for i in range(7)}
        for s in sessions:
            session_date = s.started_at.date()
            if session_date in daily_minutes:
                daily_minutes[session_date] += s.actual_minutes

        distribution: list[ExecutionDayStudyDTO] = []
        for i in range(7):
            day_d = monday + timedelta(days=i)
            minutes = daily_minutes[day_d]
            distribution.append(
                ExecutionDayStudyDTO(
                    day_date=day_d,
                    day_label=_WEEKDAY_LABELS[i],
                    study_hours=round(minutes / 60.0, 1),
                    is_today=(day_d == today),
                )
            )

        return distribution

    async def get_execution_kpis(self, user_id: UUID, today: date) -> ExecutionKpiStatsDTO:
        month_start = datetime(today.year, today.month, 1, tzinfo=UTC)
        if today.month == 12:
            next_month_start = datetime(today.year + 1, 1, 1, tzinfo=UTC)
        else:
            next_month_start = datetime(today.year, today.month + 1, 1, tzinfo=UTC)

        # Monthly study sessions
        sess_stmt = select(StudySessionORM).where(
            StudySessionORM.user_id == user_id,
            StudySessionORM.started_at >= month_start,
            StudySessionORM.started_at < next_month_start,
            StudySessionORM.status.in_(("COMPLETED", "PARTIAL_COMPLETED")),
        )
        sess_res = await self._session.execute(sess_stmt)
        monthly_sessions = list(sess_res.scalars().all())

        monthly_study_seconds = sum(s.actual_minutes * 60 for s in monthly_sessions)
        deep_work_seconds = sum(
            s.actual_minutes * 60 for s in monthly_sessions if s.actual_minutes >= 45
        )
        completed_pomodoro_count = sum(max(1, s.actual_minutes // 25) for s in monthly_sessions)

        # Streak calculation
        all_roadmap_ids = await self._get_all_user_roadmap_ids(user_id)

        # Distinct study dates from completed sessions
        sess_dates_stmt = select(StudySessionORM.started_at).where(
            StudySessionORM.user_id == user_id,
            StudySessionORM.status.in_(("COMPLETED", "PARTIAL_COMPLETED")),
        )
        sess_dates_res = await self._session.execute(sess_dates_stmt)
        study_dates: set[date] = {
            row[0].date() for row in sess_dates_res.fetchall() if row[0] is not None
        }

        # Distinct dates from completed tasks
        if all_roadmap_ids:
            tasks_comp_stmt = select(TaskORM.completed_at).where(
                TaskORM.roadmap_id.in_(all_roadmap_ids),
                TaskORM.status == "COMPLETED",
                TaskORM.completed_at.is_not(None),
            )
            tasks_comp_res = await self._session.execute(tasks_comp_stmt)
            for row in tasks_comp_res.fetchall():
                if row[0] is not None:
                    study_dates.add(row[0].date())

        streak_days = 0
        check_date = today
        if check_date not in study_dates:
            check_date = today - timedelta(days=1)

        while check_date in study_dates:
            streak_days += 1
            check_date -= timedelta(days=1)

        # Personal best streak
        personal_best = streak_days
        if study_dates:
            sorted_dates = sorted(study_dates)
            curr = 0
            prev_d: date | None = None
            for d in sorted_dates:
                if prev_d is None or d == prev_d + timedelta(days=1):
                    curr += 1
                else:
                    curr = 1
                prev_d = d
                if curr > personal_best:
                    personal_best = curr

        # Streak history last 7 days (ending today)
        streak_history_last_7_days = [
            (today - timedelta(days=6 - i)) in study_dates for i in range(7)
        ]

        # Overdue tasks
        active_roadmaps = await self._get_active_roadmaps(user_id)
        active_ids = list(active_roadmaps.keys())

        overdue_tasks_count = 0
        adherence_rate_pct = 0.0
        if active_ids:
            overdue_stmt = select(func.count(TaskORM.id)).where(
                TaskORM.roadmap_id.in_(active_ids),
                TaskORM.status.in_(("TODO", "IN_PROGRESS")),
                TaskORM.scheduled_date < today,
            )
            overdue_res = await self._session.execute(overdue_stmt)
            overdue_tasks_count = overdue_res.scalar() or 0

            # Adherence calculation
            tot_stmt = select(func.count(TaskORM.id)).where(
                TaskORM.roadmap_id.in_(active_ids),
                TaskORM.scheduled_date <= today,
            )
            tot_res = await self._session.execute(tot_stmt)
            total_scheduled = tot_res.scalar() or 0

            comp_stmt = select(func.count(TaskORM.id)).where(
                TaskORM.roadmap_id.in_(active_ids),
                TaskORM.scheduled_date <= today,
                TaskORM.status == "COMPLETED",
            )
            comp_res = await self._session.execute(comp_stmt)
            completed_scheduled = comp_res.scalar() or 0

            if total_scheduled > 0:
                adherence_rate_pct = round((completed_scheduled / total_scheduled) * 100.0, 1)
            elif monthly_study_seconds > 0:
                adherence_rate_pct = 100.0

        return ExecutionKpiStatsDTO(
            monthly_study_seconds=monthly_study_seconds,
            deep_work_seconds=deep_work_seconds,
            completed_pomodoro_count=completed_pomodoro_count,
            streak_days=streak_days,
            personal_best_streak=personal_best,
            streak_history_last_7_days=streak_history_last_7_days,
            adherence_rate_pct=adherence_rate_pct,
            adherence_delta_pct=0.0,
            overdue_tasks_count=overdue_tasks_count,
        )


def _execution_dashboard_factory_impl(
    session: AsyncSession,
) -> ExecutionDashboardQueryPort:
    return ExecutionDashboardAdapter(session)


register_execution_dashboard_factory(_execution_dashboard_factory_impl)
