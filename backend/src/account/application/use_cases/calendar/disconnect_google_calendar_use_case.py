from uuid import UUID

from src.account.application.dtos.calendar import CalendarConnectionResponseDTO
from src.account.application.ports.calendar_connection_repository_port import (
    CalendarConnectionRepositoryPort,
)
from src.account.domain.ports.calendar_provider_port import CalendarProviderPort
from src.shared_kernel.application.uow import AsyncUnitOfWork
from src.shared_kernel.config import Settings, get_settings
from src.shared_kernel.infrastructure.security.encryption import decrypt_token


class DisconnectGoogleCalendarUseCase:
    """Stop active push notification channel and mark connection as REVOKED (UC-17)."""

    def __init__(
        self,
        repository: CalendarConnectionRepositoryPort,
        calendar_provider: CalendarProviderPort,
        uow: AsyncUnitOfWork | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._repository = repository
        self._calendar_provider = calendar_provider
        self._uow = uow
        self._settings = settings or get_settings()

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

        # If webhook watch channel is registered, stop it gracefully
        if conn.channel_id and conn.resource_id and conn.oauth_refresh_token_encrypted:
            try:
                refresh_token = decrypt_token(
                    conn.oauth_refresh_token_encrypted,
                    key=self._settings.calendar_encryption_key or None,
                )
                await self._calendar_provider.stop_watch_channel(
                    refresh_token=refresh_token,
                    channel_id=conn.channel_id,
                    resource_id=conn.resource_id,
                )
            except Exception:
                # Do not abort disconnection on external channel stop failure
                pass

        conn.mark_revoked(reason="User disconnected calendar integration")
        if self._uow is not None:
            async with self._uow as uow:
                saved = await self._repository.save(conn)
                await uow.commit()
        else:
            saved = await self._repository.save(conn)

        return CalendarConnectionResponseDTO(
            connected=False,
            provider=saved.provider,
            sync_status=saved.sync_status,
            external_calendar_id=saved.external_calendar_id,
            source_calendars=saved.source_calendars_json,
            last_synced_at=saved.last_synced_at,
            error_detail=saved.error_detail,
        )
