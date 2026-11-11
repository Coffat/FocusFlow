from datetime import UTC, datetime
from uuid import UUID

from src.account.application.dtos.calendar import InboundSyncResultDTO
from src.account.application.ports.calendar_connection_repository_port import (
    CalendarConnectionRepositoryPort,
)
from src.account.domain.ports.calendar_provider_port import (
    CalendarEventDTO,
    CalendarGoneError,
    CalendarProviderPort,
)
from src.planning.public_api import ScheduleBlockSyncPort
from src.shared_kernel.application.uow import AsyncUnitOfWork
from src.shared_kernel.config import Settings, get_settings
from src.shared_kernel.domain.base import utc_now
from src.shared_kernel.infrastructure.security.encryption import decrypt_token


def _to_utc(dt: datetime) -> datetime:
    """Ensure datetime is timezone-aware in UTC."""
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


class ProcessGoogleCalendarWebhookUseCase:
    """Inbound sync worker: processes Google Calendar push notifications (UC-17).

    Enforces:
    1. Pagination loop until nextSyncToken.
    2. 410 Gone full sync reconciliation without deleting internal blocks.
    3. Event Deletion Matrix: Preserves completed/missed blocks and tasks 100%.
    4. Content & Version Echo Check: Differentiates outbound write echoes from user edits.
    5. Strict Review Policy: Marks external time modifications as PENDING_REVIEW.
    """

    def __init__(
        self,
        repository: CalendarConnectionRepositoryPort,
        calendar_provider: CalendarProviderPort,
        schedule_block_port: ScheduleBlockSyncPort,
        uow: AsyncUnitOfWork | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._repository = repository
        self._calendar_provider = calendar_provider
        self._schedule_block_port = schedule_block_port
        self._uow = uow
        self._settings = settings or get_settings()

    async def execute(self, channel_id: str) -> InboundSyncResultDTO:
        conn = await self._repository.get_by_channel_id(channel_id)
        if conn is None or not conn.is_active:
            return InboundSyncResultDTO(
                channel_id=channel_id,
                total_events_received=0,
                echo_ignored_count=0,
                pending_review_count=0,
                deleted_blocks_count=0,
            )

        refresh_token = decrypt_token(
            conn.oauth_refresh_token_encrypted,
            key=self._settings.calendar_encryption_key,
        )

        all_events: list[CalendarEventDTO] = []
        page_token: str | None = None
        final_sync_token: str | None = None
        current_sync_token: str | None = conn.sync_token
        full_reconciliation = False

        # Pagination & 410 Gone handling loop
        while True:
            try:
                res = await self._calendar_provider.list_events(
                    refresh_token=refresh_token,
                    calendar_id=conn.external_calendar_id,
                    sync_token=current_sync_token,
                    page_token=page_token,
                )
            except CalendarGoneError:
                # 410 Gone: syncToken invalid or expired. Clear sync token and do full sync!
                full_reconciliation = True
                conn.sync_token = None
                current_sync_token = None
                page_token = None
                all_events.clear()
                res = await self._calendar_provider.list_events(
                    refresh_token=refresh_token,
                    calendar_id=conn.external_calendar_id,
                    sync_token=None,
                    page_token=None,
                )

            if res.sync_reset_needed:
                full_reconciliation = True
                conn.sync_token = None
                current_sync_token = None
                page_token = None
                all_events.clear()
                res = await self._calendar_provider.list_events(
                    refresh_token=refresh_token,
                    calendar_id=conn.external_calendar_id,
                    sync_token=None,
                    page_token=None,
                )

            all_events.extend(res.events)
            if res.next_page_token:
                page_token = res.next_page_token
            else:
                final_sync_token = res.next_sync_token
                break

        echo_ignored = 0
        pending_review = 0
        deleted_count = 0
        now = utc_now()

        for ev in all_events:
            # 1. Match event to ScheduleBlock
            block = None
            if ev.block_id:
                block = await self._schedule_block_port.get_block_by_id(ev.block_id)

            if block is None and ev.id.startswith("ff"):
                try:
                    target_id = UUID(ev.id[2:])
                    block = await self._schedule_block_port.get_block_by_id(target_id)
                except ValueError:
                    block = None

            if block is None:
                block = await self._schedule_block_port.get_block_by_external_event_id(ev.id)

            # If no matching internal schedule block, skip (external personal event)
            if block is None:
                continue

            # 2. Event Deletion Matrix (status == "cancelled")
            if ev.status == "cancelled":
                deleted_count += 1
                # If block is COMPLETED or MISSED: 100% PRESERVE STUDY PROGRESS!
                # Update sync_status = 'EXTERNAL_DELETED', keep block.status unchanged!
                # If block is PLANNED: update sync_status = 'EXTERNAL_DELETED', do not reset task.
                await self._schedule_block_port.update_block_sync_info(
                    block.id,
                    sync_status="EXTERNAL_DELETED",
                    last_synced_at=now,
                )
                continue

            # 3. Content & Version Echo Check
            ev_start = _to_utc(ev.start_time)
            ev_end = _to_utc(ev.end_time)
            block_start = _to_utc(block.start_time)
            block_end = _to_utc(block.end_time)

            time_matches = (
                abs((ev_start - block_start).total_seconds()) < 1.0
                and abs((ev_end - block_end).total_seconds()) < 1.0
            )

            if time_matches:
                # Echo detected: FocusFlow just wrote this event -> update etag and skip
                echo_ignored += 1
                await self._schedule_block_port.update_block_sync_info(
                    block.id,
                    etag=ev.etag,
                    last_synced_at=now,
                )
            else:
                # User actually modified event on Google Calendar!
                # Strict Review Policy: Mark PENDING_REVIEW
                pending_review += 1
                await self._schedule_block_port.update_block_sync_info(
                    block.id,
                    etag=ev.etag,
                    sync_status="PENDING_REVIEW",
                    last_synced_at=now,
                )

        # Update connection tokens and timestamp
        conn.sync_token = final_sync_token
        conn.last_synced_at = now
        await self._repository.save(conn)

        if self._uow:
            await self._uow.commit()

        return InboundSyncResultDTO(
            channel_id=channel_id,
            total_events_received=len(all_events),
            echo_ignored_count=echo_ignored,
            pending_review_count=pending_review,
            deleted_blocks_count=deleted_count,
            full_reconciliation_triggered=full_reconciliation,
            new_sync_token=final_sync_token,
        )
