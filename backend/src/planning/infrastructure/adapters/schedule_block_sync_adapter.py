from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.planning.infrastructure.orm.planning_orm import ScheduleBlockORM
from src.planning.public_api import (
    ScheduleBlockSyncDTO,
    ScheduleBlockSyncPort,
    register_schedule_block_sync_factory,
)


class ScheduleBlockSyncAdapter(ScheduleBlockSyncPort):
    """SQLAlchemy adapter for ScheduleBlockSyncPort (UC-17)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _to_dto(self, orm: ScheduleBlockORM) -> ScheduleBlockSyncDTO:
        return ScheduleBlockSyncDTO(
            id=orm.id,
            roadmap_id=orm.roadmap_id,
            official_schedule_id=orm.official_schedule_id,
            task_id=orm.task_id,
            sequence_in_task=orm.sequence_in_task,
            block_type=orm.block_type,
            block_date=orm.block_date,
            start_time=orm.start_time,
            end_time=orm.end_time,
            scheduled_duration_minutes=orm.scheduled_duration_minutes,
            is_protected=orm.is_protected,
            status=orm.status,
            external_calendar_event_id=orm.external_calendar_event_id,
            etag=orm.etag,
            sync_status=orm.sync_status,
            last_synced_at=orm.last_synced_at,
            placement_rationale=orm.placement_rationale,
        )

    async def get_blocks_for_schedule(
        self,
        official_schedule_id: UUID,
        sync_status_in: Sequence[str] | None = None,
    ) -> list[ScheduleBlockSyncDTO]:
        stmt = select(ScheduleBlockORM).where(
            ScheduleBlockORM.official_schedule_id == official_schedule_id
        )
        if sync_status_in:
            stmt = stmt.where(ScheduleBlockORM.sync_status.in_(list(sync_status_in)))
        stmt = stmt.order_by(ScheduleBlockORM.start_time.asc())
        result = await self.session.execute(stmt)
        return [self._to_dto(orm) for orm in result.scalars().all()]

    async def get_block_by_id(self, block_id: UUID) -> ScheduleBlockSyncDTO | None:
        stmt = select(ScheduleBlockORM).where(ScheduleBlockORM.id == block_id)
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_dto(orm) if orm is not None else None

    async def get_block_by_external_event_id(
        self, external_event_id: str
    ) -> ScheduleBlockSyncDTO | None:
        stmt = select(ScheduleBlockORM).where(
            ScheduleBlockORM.external_calendar_event_id == external_event_id
        )
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_dto(orm) if orm is not None else None

    async def update_block_sync_info(
        self,
        block_id: UUID,
        *,
        external_calendar_event_id: str | None = None,
        etag: str | None = None,
        sync_status: str | None = None,
        last_synced_at: datetime | None = None,
    ) -> None:
        stmt = select(ScheduleBlockORM).where(ScheduleBlockORM.id == block_id)
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is not None:
            if external_calendar_event_id is not None:
                orm.external_calendar_event_id = external_calendar_event_id
            if etag is not None:
                orm.etag = etag
            if sync_status is not None:
                orm.sync_status = sync_status
            if last_synced_at is not None:
                orm.last_synced_at = last_synced_at
            await self.session.flush()


def _schedule_block_sync_factory_fn(session: AsyncSession) -> ScheduleBlockSyncPort:
    return ScheduleBlockSyncAdapter(session)


register_schedule_block_sync_factory(_schedule_block_sync_factory_fn)
