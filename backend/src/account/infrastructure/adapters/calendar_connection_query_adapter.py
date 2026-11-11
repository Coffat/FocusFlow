from datetime import datetime
from uuid import UUID

from src.account.application.ports.calendar_connection_repository_port import (
    CalendarConnectionRepositoryPort,
)
from src.account.domain.ports.calendar_provider_port import CalendarProviderPort
from src.account.public_api import (
    CalendarBusyIntervalDTO,
    CalendarConnectionQueryPort,
    CalendarConnectionSnapshotDTO,
)
from src.shared_kernel.infrastructure.security.encryption import decrypt_token


class SqlAlchemyCalendarConnectionQueryAdapter(CalendarConnectionQueryPort):
    """Adapter exposing Calendar Connection queries and FreeBusy retrieval to external contexts."""

    def __init__(
        self,
        repository: CalendarConnectionRepositoryPort,
        calendar_provider: CalendarProviderPort,
    ) -> None:
        self._repository = repository
        self._calendar_provider = calendar_provider

    async def get_connection_snapshot(
        self,
        user_id: UUID,
        provider: str = "GOOGLE",
    ) -> CalendarConnectionSnapshotDTO | None:
        conn = await self._repository.get_by_user_id_and_provider(user_id, provider)
        if conn is None:
            return None

        return CalendarConnectionSnapshotDTO(
            user_id=conn.user_id,
            provider=conn.provider,
            sync_status=conn.sync_status,
            external_calendar_id=conn.external_calendar_id,
            source_calendars=tuple(conn.source_calendars_json),
            last_synced_at=conn.last_synced_at.isoformat() if conn.last_synced_at else None,
            is_active=conn.is_active,
        )

    async def get_free_busy_intervals(
        self,
        user_id: UUID,
        time_min: datetime,
        time_max: datetime,
        provider: str = "GOOGLE",
    ) -> list[CalendarBusyIntervalDTO]:
        conn = await self._repository.get_by_user_id_and_provider(user_id, provider)
        if conn is None or not conn.is_active or not conn.oauth_refresh_token_encrypted:
            return []

        try:
            refresh_token = decrypt_token(conn.oauth_refresh_token_encrypted)
            calendar_ids = conn.source_calendars_json or ["primary"]
            intervals = await self._calendar_provider.get_free_busy_intervals(
                refresh_token=refresh_token,
                calendar_ids=calendar_ids,
                time_min=time_min,
                time_max=time_max,
            )
            return [
                CalendarBusyIntervalDTO(start_time=iv.start_time, end_time=iv.end_time)
                for iv in intervals
            ]
        except Exception:
            # Degrade gracefully during scheduling if external calendar is unreachable
            return []
