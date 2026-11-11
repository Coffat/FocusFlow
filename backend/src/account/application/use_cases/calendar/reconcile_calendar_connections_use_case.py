from src.account.application.ports.calendar_connection_repository_port import (
    CalendarConnectionRepositoryPort,
)
from src.account.application.use_cases.calendar.process_google_calendar_webhook_use_case import (
    ProcessGoogleCalendarWebhookUseCase,
)
from src.account.application.use_cases.calendar.renew_expiring_calendar_webhooks_use_case import (
    RenewExpiringCalendarWebhooksUseCase,
)
from src.shared_kernel.application.uow import AsyncUnitOfWork
from src.shared_kernel.domain.base import utc_now


class ReconcileCalendarConnectionsUseCase:
    """Cron sweeper: runs every 6 hours to reconcile active connections and catch missed events (UC-17)."""

    def __init__(
        self,
        repository: CalendarConnectionRepositoryPort,
        process_webhook_use_case: ProcessGoogleCalendarWebhookUseCase,
        renew_webhooks_use_case: RenewExpiringCalendarWebhooksUseCase | None = None,
        uow: AsyncUnitOfWork | None = None,
    ) -> None:
        self._repository = repository
        self._process_webhook_use_case = process_webhook_use_case
        self._renew_webhooks_use_case = renew_webhooks_use_case
        self._uow = uow

    async def execute(self) -> int:
        active_connections = await self._repository.get_active_connections()
        reconciled_count = 0
        now = utc_now()

        for conn in active_connections:
            if conn.is_channel_expired(now) and self._renew_webhooks_use_case:
                await self._renew_webhooks_use_case.execute()

            if conn.channel_id:
                try:
                    await self._process_webhook_use_case.execute(channel_id=conn.channel_id)
                    reconciled_count += 1
                except Exception as exc:
                    conn.mark_error(f"Reconciliation failed: {exc}")
                    await self._repository.save(conn)

        if self._uow:
            await self._uow.commit()

        return reconciled_count
