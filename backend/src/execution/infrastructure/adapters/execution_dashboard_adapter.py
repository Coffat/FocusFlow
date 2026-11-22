from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.account.public_api import create_user_query_port
from src.execution.infrastructure.orm.session_orm import SessionTaskORM, StudySessionORM
from src.execution.infrastructure.orm.task_orm import TaskORM
from src.execution.public_api import (
    AnalyticsDailyMetricDTO,
    AnalyticsSummaryQueryDTO,
    AnalyticsWeeklyQueryDTO,
    ExecutionDashboardQueryPort,
    ExecutionDayStudyDTO,
    ExecutionKpiStatsDTO,
    ExecutionTodayTaskDTO,
    ExportStudySessionDTO,
    ExportTaskDTO,
    SrlSessionFactsDTO,
    register_execution_dashboard_factory,
)
from src.planning.public_api import create_planning_execution_bridge

_WEEKDAY_LABELS: list[str] = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _resolve_zoneinfo(user_timezone: str | None) -> ZoneInfo:
    raw = (user_timezone or "").strip()
    if not raw:
        return ZoneInfo("UTC")
    try:
        return ZoneInfo(raw)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def _to_user_date(dt: datetime, user_tz: ZoneInfo) -> date:
    aware = dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)
    return aware.astimezone(user_tz).date()


class ExecutionDashboardAdapter(ExecutionDashboardQueryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _resolve_user_context(
        self,
        user_id: UUID,
        today: date | None,
        *,
        user_timezone: str | None = None,
        now: datetime | None = None,
    ) -> tuple[ZoneInfo, date]:
        tz_name = (user_timezone or "").strip() if user_timezone is not None else ""
        if user_timezone is None:
            user_snap = await create_user_query_port(self._session).get_user_by_id(user_id)
            if user_snap is not None and user_snap.timezone:
                tz_name = user_snap.timezone
        user_tz = _resolve_zoneinfo(tz_name or "UTC")
        if today is not None:
            effective_today = today
        else:
            ref_now = now if now is not None else datetime.now(UTC)
            effective_today = _to_user_date(ref_now, user_tz)
        return user_tz, effective_today

    async def _get_active_roadmaps(self, user_id: UUID) -> dict[UUID, str]:
        roadmaps = await create_planning_execution_bridge(self._session).get_user_roadmaps_context(
            user_id
        )
        return {r.roadmap_id: r.title for r in roadmaps if r.status == "ACTIVE"}

    async def _get_all_user_roadmap_ids(self, user_id: UUID) -> list[UUID]:
        roadmaps = await create_planning_execution_bridge(self._session).get_user_roadmaps_context(
            user_id
        )
        return [r.roadmap_id for r in roadmaps]

    async def get_today_queue(
        self,
        user_id: UUID,
        today: date | None = None,
        *,
        user_timezone: str | None = None,
        now: datetime | None = None,
    ) -> list[ExecutionTodayTaskDTO]:
        user_tz, effective_today = await self._resolve_user_context(
            user_id,
            today,
            user_timezone=user_timezone,
            now=now,
        )
        roadmap_map = await self._get_active_roadmaps(user_id)
        if not roadmap_map:
            return []

        active_roadmap_ids = list(roadmap_map.keys())
        stmt = (
            select(TaskORM)
            .where(
                TaskORM.roadmap_id.in_(active_roadmap_ids),
                TaskORM.scheduled_date == effective_today,
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
                start_aware = (
                    task.scheduled_start
                    if task.scheduled_start.tzinfo is not None
                    else task.scheduled_start.replace(tzinfo=UTC)
                )
                end_aware = (
                    task.scheduled_end
                    if task.scheduled_end.tzinfo is not None
                    else task.scheduled_end.replace(tzinfo=UTC)
                )
                scheduled_time = (
                    f"{start_aware.astimezone(user_tz).strftime('%H:%M')} - "
                    f"{end_aware.astimezone(user_tz).strftime('%H:%M')}"
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
        self,
        user_id: UUID,
        today: date | None = None,
        *,
        user_timezone: str | None = None,
        now: datetime | None = None,
    ) -> list[ExecutionDayStudyDTO]:
        user_tz, effective_today = await self._resolve_user_context(
            user_id,
            today,
            user_timezone=user_timezone,
            now=now,
        )
        monday = effective_today - timedelta(days=effective_today.weekday())
        week_start_local = datetime.combine(monday, time.min, tzinfo=user_tz)
        week_end_local = week_start_local + timedelta(days=7)
        week_start = week_start_local.astimezone(UTC)
        week_end = week_end_local.astimezone(UTC)

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
            session_date = _to_user_date(s.started_at, user_tz)
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
                    is_today=(day_d == effective_today),
                )
            )

        return distribution

    async def get_execution_kpis(
        self,
        user_id: UUID,
        today: date | None = None,
        *,
        user_timezone: str | None = None,
        now: datetime | None = None,
    ) -> ExecutionKpiStatsDTO:
        user_tz, effective_today = await self._resolve_user_context(
            user_id,
            today,
            user_timezone=user_timezone,
            now=now,
        )
        month_start_local = datetime(effective_today.year, effective_today.month, 1, tzinfo=user_tz)
        if effective_today.month == 12:
            next_month_start_local = datetime(effective_today.year + 1, 1, 1, tzinfo=user_tz)
        else:
            next_month_start_local = datetime(
                effective_today.year, effective_today.month + 1, 1, tzinfo=user_tz
            )
        month_start = month_start_local.astimezone(UTC)
        next_month_start = next_month_start_local.astimezone(UTC)

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
        completed_pomodoro_count = len(monthly_sessions)

        # Streak calculation
        all_roadmap_ids = await self._get_all_user_roadmap_ids(user_id)

        # Distinct study dates from completed sessions in user timezone
        sess_dates_stmt = select(StudySessionORM.started_at).where(
            StudySessionORM.user_id == user_id,
            StudySessionORM.status.in_(("COMPLETED", "PARTIAL_COMPLETED")),
        )
        sess_dates_res = await self._session.execute(sess_dates_stmt)
        study_dates: set[date] = {
            _to_user_date(row[0], user_tz)
            for row in sess_dates_res.fetchall()
            if row[0] is not None
        }

        # Distinct dates from completed tasks in user timezone
        if all_roadmap_ids:
            tasks_comp_stmt = select(TaskORM.completed_at).where(
                TaskORM.roadmap_id.in_(all_roadmap_ids),
                TaskORM.status == "COMPLETED",
                TaskORM.completed_at.is_not(None),
            )
            tasks_comp_res = await self._session.execute(tasks_comp_stmt)
            for row in tasks_comp_res.fetchall():
                if row[0] is not None:
                    study_dates.add(_to_user_date(row[0], user_tz))

        streak_days = 0
        check_date = effective_today
        if check_date not in study_dates:
            check_date = effective_today - timedelta(days=1)

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

        # Streak history last 7 days (ending effective_today)
        streak_history_last_7_days = [
            (effective_today - timedelta(days=6 - i)) in study_dates for i in range(7)
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
                TaskORM.scheduled_date < effective_today,
            )
            overdue_res = await self._session.execute(overdue_stmt)
            overdue_tasks_count = overdue_res.scalar() or 0

            # Adherence calculation
            tot_stmt = select(func.count(TaskORM.id)).where(
                TaskORM.roadmap_id.in_(active_ids),
                TaskORM.scheduled_date <= effective_today,
            )
            tot_res = await self._session.execute(tot_stmt)
            total_scheduled = tot_res.scalar() or 0

            comp_stmt = select(func.count(TaskORM.id)).where(
                TaskORM.roadmap_id.in_(active_ids),
                TaskORM.scheduled_date <= effective_today,
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

    async def _get_non_paused_user_roadmap_ids(self, user_id: UUID) -> list[UUID]:
        roadmaps = await create_planning_execution_bridge(self._session).get_user_roadmaps_context(
            user_id
        )
        return [r.roadmap_id for r in roadmaps if r.status not in ("PAUSED", "ARCHIVED")]

    async def _compute_wrls_for_sessions(
        self,
        sessions: list[StudySessionORM],
        user_tz: ZoneInfo,
    ) -> int:
        if not sessions:
            return 0
        sess_ids = [s.id for s in sessions]
        st_stmt = (
            select(
                SessionTaskORM.session_id,
                TaskORM.reschedule_count,
                TaskORM.parent_task_id,
            )
            .join(TaskORM, TaskORM.id == SessionTaskORM.task_id)
            .where(SessionTaskORM.session_id.in_(sess_ids))
        )
        st_rows = (await self._session.execute(st_stmt)).all()
        recovered_by_task_sessions: set[UUID] = set()
        for sid, resched_cnt, parent_tid in st_rows:
            if int(resched_cnt or 0) > 0 or parent_tid is not None:
                recovered_by_task_sessions.add(sid)

        wrls = 0
        mvs_dates_counted: set[date] = set()
        for s in sessions:
            local_d = _to_user_date(s.started_at, user_tz)
            if s.session_mode == "MVS":
                # BR-SESS-04: max 1 MVS session per day counts toward WRLS
                if local_d not in mvs_dates_counted:
                    mvs_dates_counted.add(local_d)
                    wrls += 1
            elif s.status == "PARTIAL_COMPLETED" or s.id in recovered_by_task_sessions:
                wrls += 1
        return wrls

    async def get_weekly_analytics(
        self,
        user_id: UUID,
        *,
        week_start: date | None = None,
        user_timezone: str | None = None,
        now: datetime | None = None,
    ) -> AnalyticsWeeklyQueryDTO:
        user_tz, effective_today = await self._resolve_user_context(
            user_id,
            None,
            user_timezone=user_timezone,
            now=now,
        )
        monday = (
            week_start
            if week_start is not None
            else (effective_today - timedelta(days=effective_today.weekday()))
        )
        sunday = monday + timedelta(days=6)
        week_start_utc = datetime.combine(monday, time.min, tzinfo=user_tz).astimezone(UTC)
        week_end_utc = (
            datetime.combine(monday, time.min, tzinfo=user_tz) + timedelta(days=7)
        ).astimezone(UTC)

        sess_stmt = (
            select(StudySessionORM)
            .where(
                StudySessionORM.user_id == user_id,
                StudySessionORM.started_at >= week_start_utc,
                StudySessionORM.started_at < week_end_utc,
                StudySessionORM.status.in_(("COMPLETED", "PARTIAL_COMPLETED")),
            )
            .order_by(StudySessionORM.started_at.asc())
        )
        sessions = list((await self._session.execute(sess_stmt)).scalars().all())

        daily_minutes: dict[date, int] = {monday + timedelta(days=i): 0 for i in range(7)}
        daily_sessions: dict[date, int] = {monday + timedelta(days=i): 0 for i in range(7)}
        attended_dates: set[date] = set()

        for s in sessions:
            s_date = _to_user_date(s.started_at, user_tz)
            attended_dates.add(s_date)
            if s_date in daily_minutes:
                daily_minutes[s_date] += int(s.actual_minutes)
                daily_sessions[s_date] += 1

        daily_breakdown: list[AnalyticsDailyMetricDTO] = []
        for i in range(7):
            day_d = monday + timedelta(days=i)
            mins = daily_minutes[day_d]
            sess_cnt = daily_sessions[day_d]
            daily_breakdown.append(
                AnalyticsDailyMetricDTO(
                    date=day_d,
                    day_label=_WEEKDAY_LABELS[i],
                    minutes_studied=mins,
                    pomodoros_completed=(mins // 25)
                    if mins >= 25
                    else (1 if sess_cnt > 0 and mins > 0 else 0),
                    sessions_count=sess_cnt,
                    is_today=(day_d == effective_today),
                )
            )

        total_week_minutes = sum(int(s.actual_minutes) for s in sessions)
        total_focused_hours = round(total_week_minutes / 60.0, 2)
        wrls = await self._compute_wrls_for_sessions(sessions, user_tz)

        roadmap_ids = await self._get_non_paused_user_roadmap_ids(user_id)
        completed_tasks_count = 0
        total_scheduled_tasks_count = 0
        scheduled_dates_in_week: set[date] = set()
        if roadmap_ids:
            t_stmt = select(TaskORM.status, TaskORM.scheduled_date).where(
                TaskORM.roadmap_id.in_(roadmap_ids),
                TaskORM.status != "CANCELLED",
                TaskORM.scheduled_date.is_not(None),
                TaskORM.scheduled_date >= monday,
                TaskORM.scheduled_date <= sunday,
            )
            t_rows = (await self._session.execute(t_stmt)).all()
            total_scheduled_tasks_count = len(t_rows)
            for st_val, task_sched_date in t_rows:
                if st_val == "COMPLETED":
                    completed_tasks_count += 1
                if task_sched_date is not None and task_sched_date <= effective_today:
                    scheduled_dates_in_week.add(task_sched_date)

        task_completion_rate = (
            round((completed_tasks_count / total_scheduled_tasks_count) * 100.0, 1)
            if total_scheduled_tasks_count > 0
            else 0.0
        )
        if scheduled_dates_in_week:
            adherence = round(
                (len(scheduled_dates_in_week & attended_dates) / len(scheduled_dates_in_week))
                * 100.0,
                1,
            )
        elif total_scheduled_tasks_count > 0:
            adherence = task_completion_rate
        elif sessions:
            adherence = 100.0
        else:
            adherence = 0.0

        return AnalyticsWeeklyQueryDTO(
            week_start=monday,
            week_end=sunday,
            total_focused_hours=total_focused_hours,
            completed_sessions_count=len(sessions),
            completed_tasks_count=completed_tasks_count,
            total_scheduled_tasks_count=total_scheduled_tasks_count,
            task_completion_rate=task_completion_rate,
            plan_adherence_rate=adherence,
            weekly_recovered_learning_sessions=wrls,
            daily_breakdown=tuple(daily_breakdown),
        )

    async def get_analytics_summary(
        self,
        user_id: UUID,
        *,
        user_timezone: str | None = None,
        now: datetime | None = None,
    ) -> AnalyticsSummaryQueryDTO:
        user_tz, effective_today = await self._resolve_user_context(
            user_id,
            None,
            user_timezone=user_timezone,
            now=now,
        )
        kpis = await self.get_execution_kpis(
            user_id,
            effective_today,
            user_timezone=user_tz.key,
            now=now,
        )
        weekly = await self.get_weekly_analytics(
            user_id,
            user_timezone=user_tz.key,
            now=now,
        )

        # Total focused hours across all completed / partial_completed sessions
        all_sess_stmt = select(
            StudySessionORM.actual_minutes,
            StudySessionORM.checkin_focus_level,
            StudySessionORM.started_at,
        ).where(
            StudySessionORM.user_id == user_id,
            StudySessionORM.status.in_(("COMPLETED", "PARTIAL_COMPLETED")),
        )
        all_sess_rows = (await self._session.execute(all_sess_stmt)).all()
        total_focused_minutes = sum(int(row[0] or 0) for row in all_sess_rows)
        total_focused_hours = round(total_focused_minutes / 60.0, 2)
        focus_scores = [int(row[1]) for row in all_sess_rows if row[1] is not None]
        average_focus_score = (
            round((sum(focus_scores) / len(focus_scores)) * 20.0, 1) if focus_scores else 0.0
        )
        attended_dates = {
            _to_user_date(row[2], user_tz) for row in all_sess_rows if row[2] is not None
        }

        all_roadmap_ids = await self._get_all_user_roadmap_ids(user_id)
        completed_tasks_count = 0
        total_tasks_count = 0
        if all_roadmap_ids:
            all_t_stmt = select(TaskORM.status).where(
                TaskORM.roadmap_id.in_(all_roadmap_ids),
                TaskORM.status != "CANCELLED",
            )
            all_t_rows = (await self._session.execute(all_t_stmt)).scalars().all()
            total_tasks_count = len(all_t_rows)
            completed_tasks_count = sum(1 for st in all_t_rows if st == "COMPLETED")

        task_completion_rate = (
            round((completed_tasks_count / total_tasks_count) * 100.0, 1)
            if total_tasks_count > 0
            else 0.0
        )

        # Overall Plan Adherence Rate across non-paused roadmaps (FR-REPORT-001)
        non_paused_ids = await self._get_non_paused_user_roadmap_ids(user_id)
        scheduled_dates_to_date: set[date] = set()
        if non_paused_ids:
            sched_d_stmt = select(TaskORM.scheduled_date).where(
                TaskORM.roadmap_id.in_(non_paused_ids),
                TaskORM.status != "CANCELLED",
                TaskORM.scheduled_date.is_not(None),
                TaskORM.scheduled_date <= effective_today,
            )
            for row_d in (await self._session.execute(sched_d_stmt)).scalars().all():
                if row_d is not None:
                    scheduled_dates_to_date.add(row_d)

        if scheduled_dates_to_date:
            plan_adherence_rate = round(
                (len(scheduled_dates_to_date & attended_dates) / len(scheduled_dates_to_date))
                * 100.0,
                1,
            )
        elif all_sess_rows:
            plan_adherence_rate = 100.0
        else:
            plan_adherence_rate = 0.0

        return AnalyticsSummaryQueryDTO(
            total_focused_hours=total_focused_hours,
            weekly_study_hours=weekly.total_focused_hours,
            task_completion_rate=task_completion_rate,
            plan_adherence_rate=plan_adherence_rate,
            weekly_recovered_learning_sessions=weekly.weekly_recovered_learning_sessions,
            completed_tasks_count=completed_tasks_count,
            total_tasks_count=total_tasks_count,
            active_streak_days=kpis.streak_days,
            average_focus_score=average_focus_score,
            daily_metrics=weekly.daily_breakdown,
        )

    async def get_srl_session_facts(self, user_id: UUID) -> SrlSessionFactsDTO:
        stmt = (
            select(
                StudySessionORM.actual_minutes,
                StudySessionORM.planned_minutes,
                StudySessionORM.started_at,
            )
            .where(
                StudySessionORM.user_id == user_id,
                StudySessionORM.status.in_(("COMPLETED", "PARTIAL_COMPLETED")),
            )
            .order_by(StudySessionORM.started_at.asc())
        )
        rows = (await self._session.execute(stmt)).all()

        completed_durations: list[int] = []
        estimation_ratios: list[float] = []
        start_datetimes_utc: list[datetime] = []

        for actual_min, planned_min, started_at in rows:
            actual_val = int(actual_min or 0)
            planned_val = int(planned_min or 0)
            if actual_val > 0:
                completed_durations.append(actual_val)
            if actual_val > 0 and planned_val > 0:
                estimation_ratios.append(float(actual_val) / float(planned_val))
            if started_at is not None:
                aware = (
                    started_at if started_at.tzinfo is not None else started_at.replace(tzinfo=UTC)
                )
                start_datetimes_utc.append(aware.astimezone(UTC))

        weekly = await self.get_weekly_analytics(user_id)
        return SrlSessionFactsDTO(
            total_completed_sessions=len(rows),
            completed_durations_mins=tuple(completed_durations),
            estimation_ratios=tuple(estimation_ratios),
            session_start_datetimes_utc=tuple(start_datetimes_utc),
            weekly_completion_rate=float(weekly.task_completion_rate),
        )

    async def get_user_export_sessions(
        self,
        user_id: UUID,
        *,
        limit: int = 500,
    ) -> tuple[int, list[ExportStudySessionDTO]]:
        count_stmt = select(func.count(StudySessionORM.id)).where(
            StudySessionORM.user_id == user_id
        )
        total_count = int((await self._session.execute(count_stmt)).scalar_one() or 0)

        stmt = (
            select(StudySessionORM)
            .where(StudySessionORM.user_id == user_id)
            .order_by(StudySessionORM.started_at.desc())
            .limit(max(1, min(limit, 500)))
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        items = [
            ExportStudySessionDTO(
                id=row.id,
                roadmap_id=row.roadmap_id,
                session_mode=row.session_mode,
                status=row.status,
                planned_minutes=row.planned_minutes,
                actual_minutes=row.actual_minutes,
                started_at=row.started_at,
                ended_at=row.ended_at,
                created_at=row.created_at,
            )
            for row in rows
        ]
        return total_count, items

    async def get_user_export_tasks(
        self,
        user_id: UUID,
        *,
        limit: int = 1000,
    ) -> tuple[int, list[ExportTaskDTO]]:
        all_roadmap_ids = await self._get_all_user_roadmap_ids(user_id)
        if not all_roadmap_ids:
            return 0, []

        count_stmt = select(func.count(TaskORM.id)).where(TaskORM.roadmap_id.in_(all_roadmap_ids))
        total_count = int((await self._session.execute(count_stmt)).scalar_one() or 0)

        stmt = (
            select(TaskORM)
            .where(TaskORM.roadmap_id.in_(all_roadmap_ids))
            .order_by(TaskORM.created_at.desc())
            .limit(max(1, min(limit, 1000)))
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        items = [
            ExportTaskDTO(
                id=row.id,
                roadmap_id=row.roadmap_id,
                milestone_id=row.milestone_id,
                title=row.title,
                description=row.description,
                estimated_minutes=row.estimated_minutes,
                scheduled_date=row.scheduled_date,
                status=row.status,
                completed_at=row.completed_at,
                created_at=row.created_at,
            )
            for row in rows
        ]
        return total_count, items


def _execution_dashboard_factory_impl(
    session: AsyncSession,
) -> ExecutionDashboardQueryPort:
    return ExecutionDashboardAdapter(session)


register_execution_dashboard_factory(_execution_dashboard_factory_impl)
