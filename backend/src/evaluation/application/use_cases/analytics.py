from datetime import UTC, date, datetime
from uuid import UUID

from src.account.public_api import UserQueryPort
from src.execution.public_api import (
    AnalyticsSummaryQueryDTO,
    AnalyticsWeeklyQueryDTO,
    ExecutionDashboardQueryPort,
    WeeklyExecutionMetricsQueryPort,
)


class GetAnalyticsSummaryUseCase:
    """Deterministic quantitative analytics summary (Total Focused Hours, TCR, Adherence, WRLS)."""

    def __init__(
        self,
        *,
        execution_dashboard_port: ExecutionDashboardQueryPort,
        user_query_port: UserQueryPort | None = None,
        weekly_metrics_port: WeeklyExecutionMetricsQueryPort | None = None,
    ) -> None:
        self._execution_port = execution_dashboard_port
        self._user_query_port = user_query_port
        self._weekly_metrics_port = weekly_metrics_port

    async def execute(
        self,
        user_id: UUID,
        *,
        now: datetime | None = None,
    ) -> AnalyticsSummaryQueryDTO:
        tz_name: str | None = None
        if self._user_query_port is not None:
            user_snap = await self._user_query_port.get_user_by_id(user_id)
            if user_snap is not None and user_snap.timezone:
                tz_name = user_snap.timezone
        effective_now = now or datetime.now(UTC)
        return await self._execution_port.get_analytics_summary(
            user_id,
            user_timezone=tz_name,
            now=effective_now,
        )


class GetWeeklyAnalyticsUseCase:
    """Deterministic 7-day analytics breakdown + WRLS + Adherence stats."""

    def __init__(
        self,
        *,
        execution_dashboard_port: ExecutionDashboardQueryPort,
        user_query_port: UserQueryPort | None = None,
        weekly_metrics_port: WeeklyExecutionMetricsQueryPort | None = None,
    ) -> None:
        self._execution_port = execution_dashboard_port
        self._user_query_port = user_query_port
        self._weekly_metrics_port = weekly_metrics_port

    async def execute(
        self,
        user_id: UUID,
        *,
        week_start: date | None = None,
        now: datetime | None = None,
    ) -> AnalyticsWeeklyQueryDTO:
        tz_name: str | None = None
        if self._user_query_port is not None:
            user_snap = await self._user_query_port.get_user_by_id(user_id)
            if user_snap is not None and user_snap.timezone:
                tz_name = user_snap.timezone
        effective_now = now or datetime.now(UTC)
        return await self._execution_port.get_weekly_analytics(
            user_id,
            week_start=week_start,
            user_timezone=tz_name,
            now=effective_now,
        )
