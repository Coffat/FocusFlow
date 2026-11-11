import hashlib
import secrets
from datetime import timedelta

from uuid6 import uuid7

from src.account.application.ports.calendar_connection_repository_port import (
    CalendarConnectionRepositoryPort,
)
from src.account.domain.ports.calendar_provider_port import CalendarProviderPort
from src.shared_kernel.application.uow import AsyncUnitOfWork
from src.shared_kernel.config import Settings, get_settings
from src.shared_kernel.domain.base import utc_now
from src.shared_kernel.infrastructure.security.encryption import decrypt_token


class RenewExpiringCalendarWebhooksUseCase:
    """Cron sweeper: renews webhook watch channels expiring within 24 hours (UC-17)."""

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

    async def execute(self) -> int:
        now = utc_now()
        threshold = now + timedelta(hours=24)

        expiring_connections = await self._repository.get_expiring_active_connections(
            expiration_before=threshold
        )

        renewed_count = 0
        for conn in expiring_connections:
            try:
                refresh_token = decrypt_token(
                    conn.oauth_refresh_token_encrypted,
                    key=self._settings.calendar_encryption_key,
                )

                new_channel_id = str(uuid7())
                channel_token = secrets.token_urlsafe(32)
                channel_token_hash = hashlib.sha256(channel_token.encode("utf-8")).hexdigest()
                base_url = (
                    self._settings.calendar_webhook_base_url.rstrip("/")
                    if self._settings.calendar_webhook_base_url
                    else "http://localhost:8000"
                )
                webhook_url = f"{base_url}/api/v1/calendar/webhooks/google"

                watch_result = await self._calendar_provider.watch_calendar(
                    refresh_token=refresh_token,
                    calendar_id=conn.external_calendar_id,
                    channel_id=new_channel_id,
                    webhook_url=webhook_url,
                    channel_token=channel_token,
                )

                conn.update_channel(
                    channel_id=watch_result.channel_id,
                    resource_id=watch_result.resource_id,
                    expiration=watch_result.expiration,
                    token_hash=channel_token_hash,
                )
                await self._repository.save(conn)
                renewed_count += 1
            except Exception as exc:
                conn.mark_error(f"Failed to renew watch channel: {exc}")
                await self._repository.save(conn)

        if self._uow:
            await self._uow.commit()

        return renewed_count
