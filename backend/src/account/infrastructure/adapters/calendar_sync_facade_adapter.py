from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.account.application.use_cases.calendar.sync_schedule_blocks_use_case import (
    SyncScheduleBlocksToGoogleUseCase,
)
from src.account.domain.ports.calendar_provider_port import (
    CalendarProviderError,
    CalendarProviderPort,
)
from src.account.infrastructure.adapters.google_calendar_adapter import (
    GoogleCalendarAdapter,
)
from src.account.infrastructure.repositories.calendar_connection_repository import (
    SqlAlchemyCalendarConnectionRepository,
)
from src.account.public_api import (
    CalendarSyncFacadePort,
    register_account_port_factories,
)
from src.planning.public_api import create_schedule_block_sync_port
from src.shared_kernel.config import get_settings
from src.shared_kernel.infrastructure.database.sqlalchemy_uow import (
    SqlAlchemyUnitOfWork,
)


class CalendarSyncFacadeAdapter(CalendarSyncFacadePort):
    """Adapter providing cross-context calendar sync operations (UC-17)."""

    def __init__(
        self,
        session: AsyncSession,
        calendar_provider: CalendarProviderPort | None = None,
    ) -> None:
        self.session = session
        settings = get_settings()
        if calendar_provider is not None:
            provider = calendar_provider
        else:
            provider_name = settings.calendar_provider.strip().lower()
            if provider_name not in ("google", "google_calendar"):
                raise CalendarProviderError(
                    f"CALENDAR_PROVIDER_NOT_CONFIGURED: Unsupported calendar_provider={settings.calendar_provider!r}. Only 'google' is supported.",
                    code="CALENDAR_PROVIDER_NOT_CONFIGURED",
                )
            provider = GoogleCalendarAdapter(settings=settings)

        repo = SqlAlchemyCalendarConnectionRepository(session)
        block_port = create_schedule_block_sync_port(session)
        uow = SqlAlchemyUnitOfWork(session)
        self._sync_use_case = SyncScheduleBlocksToGoogleUseCase(
            repository=repo,
            calendar_provider=provider,
            schedule_block_port=block_port,
            uow=uow,
            settings=settings,
        )

    async def sync_schedule_blocks_to_google(
        self,
        schedule_id: UUID,
        user_id: UUID,
    ) -> str:
        res = await self._sync_use_case.execute(schedule_id=schedule_id, user_id=user_id)
        if res.skipped:
            if res.error_detail and "No active Google Calendar connection" in res.error_detail:
                return "NOT_CONNECTED"
            return "SYNC_FAILED"
        if res.error_detail:
            return "SYNC_FAILED" if res.synced_blocks_count == 0 else "PENDING_SYNC"
        return "SYNCED"


def _calendar_sync_facade_factory(session: Any) -> CalendarSyncFacadePort:
    return CalendarSyncFacadeAdapter(session)


register_account_port_factories(calendar_sync_facade_factory=_calendar_sync_facade_factory)
