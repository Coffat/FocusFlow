from uuid import UUID

from src.account.application.dtos.calendar import OutboundSyncResultDTO
from src.account.application.ports.calendar_connection_repository_port import (
    CalendarConnectionRepositoryPort,
)
from src.account.domain.ports.calendar_provider_port import (
    CalendarConflictError,
    CalendarEventDTO,
    CalendarProviderPort,
    get_deterministic_event_id,
)
from src.planning.public_api import ScheduleBlockSyncPort
from src.shared_kernel.application.uow import AsyncUnitOfWork
from src.shared_kernel.config import Settings, get_settings
from src.shared_kernel.domain.base import utc_now
from src.shared_kernel.infrastructure.security.encryption import decrypt_token


class SyncScheduleBlocksToGoogleUseCase:
    """Outbound sync worker: syncs ScheduleBlock entities to Google Calendar using deterministic IDs (UC-17)."""

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

    async def execute(self, schedule_id: UUID, user_id: UUID) -> OutboundSyncResultDTO:
        conn = await self._repository.get_by_user_id_and_provider(user_id, "GOOGLE")
        if conn is None or not conn.is_active:
            return OutboundSyncResultDTO(
                schedule_id=str(schedule_id),
                user_id=str(user_id),
                total_blocks_scanned=0,
                synced_blocks_count=0,
                skipped=True,
                error_detail="No active Google Calendar connection found.",
            )

        refresh_token = decrypt_token(
            conn.oauth_refresh_token_encrypted,
            key=self._settings.calendar_encryption_key,
        )

        # Query blocks belonging to official_schedule_id
        blocks = await self._schedule_block_port.get_blocks_for_schedule(
            schedule_id,
            sync_status_in=("PENDING_SYNC", "SYNCED"),
        )
        if not blocks:
            # Fallback: scan all blocks for the schedule
            blocks = await self._schedule_block_port.get_blocks_for_schedule(schedule_id)

        synced_count = 0
        conflict_resolved_count = 0
        now = utc_now()

        for block in blocks:
            event_id = get_deterministic_event_id(block.id)
            title = f"FocusFlow: {block.block_type.capitalize()} Session"
            event_dto = CalendarEventDTO(
                id=event_id,
                title=title,
                start_time=block.start_time,
                end_time=block.end_time,
                description=f"FocusFlow Study Block ({block.scheduled_duration_minutes}m)",
                block_id=block.id,
                extended_properties={
                    "focusflow_block_id": str(block.id),
                    "official_schedule_id": str(schedule_id),
                },
            )

            try:
                created = await self._calendar_provider.create_event(
                    refresh_token=refresh_token,
                    calendar_id=conn.external_calendar_id,
                    event=event_dto,
                )
                await self._schedule_block_port.update_block_sync_info(
                    block.id,
                    external_calendar_event_id=created.id,
                    etag=created.etag,
                    sync_status="SYNCED",
                    last_synced_at=now,
                )
                synced_count += 1
            except CalendarConflictError:
                # 409 Conflict Recovery: Fetch existing event via get_event
                existing = await self._calendar_provider.get_event(
                    refresh_token=refresh_token,
                    calendar_id=conn.external_calendar_id,
                    event_id=event_id,
                )
                if existing is not None and (
                    existing.block_id == block.id
                    or existing.extended_properties.get("focusflow_block_id") == str(block.id)
                ):
                    # Matched! Update external event id, etag, mark SYNCED without duplicating
                    await self._schedule_block_port.update_block_sync_info(
                        block.id,
                        external_calendar_event_id=existing.id,
                        etag=existing.etag,
                        sync_status="SYNCED",
                        last_synced_at=now,
                    )
                    synced_count += 1
                    conflict_resolved_count += 1

        conn.last_synced_at = now
        await self._repository.save(conn)

        if self._uow:
            await self._uow.commit()

        return OutboundSyncResultDTO(
            schedule_id=str(schedule_id),
            user_id=str(user_id),
            total_blocks_scanned=len(blocks),
            synced_blocks_count=synced_count,
            conflict_resolved_count=conflict_resolved_count,
            skipped=False,
        )
