from uuid import UUID

from src.account.application.dtos.calendar import CalendarConnectionResponseDTO
from src.account.application.ports.calendar_connection_repository_port import (
    CalendarConnectionRepositoryPort,
)


class GetCalendarConnectionStatusUseCase:
    """Retrieve external calendar connection status and source calendar identifiers."""

    def __init__(self, repository: CalendarConnectionRepositoryPort) -> None:
        self._repository = repository

    async def execute(
        self,
        user_id: UUID,
        provider: str = "GOOGLE",
    ) -> CalendarConnectionResponseDTO:
        conn = await self._repository.get_by_user_id_and_provider(user_id, provider)
        if conn is None:
            return CalendarConnectionResponseDTO(
                connected=False,
                provider=provider,
                sync_status="REVOKED",
                external_calendar_id=None,
                source_calendars=[],
                last_synced_at=None,
                error_detail=None,
            )

        return CalendarConnectionResponseDTO(
            connected=conn.is_active,
            provider=conn.provider,
            sync_status=conn.sync_status,
            external_calendar_id=conn.external_calendar_id,
            source_calendars=conn.source_calendars_json,
            last_synced_at=conn.last_synced_at,
            error_detail=conn.error_detail,
        )
