from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.planning.application.ports.schedule_block_repository_port import (
    ScheduleBlockRepositoryPort,
)
from src.planning.domain.models.schedule_block import ScheduleBlock
from src.planning.infrastructure.orm.planning_orm import ScheduleBlockORM


class SqlAlchemyScheduleBlockRepository(ScheduleBlockRepositoryPort):
    """SQLAlchemy repository for ScheduleBlock entity (UC-17 / UC-18)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _to_domain(self, orm: ScheduleBlockORM) -> ScheduleBlock:
        return ScheduleBlock(
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
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    async def get_by_id(self, block_id: UUID) -> ScheduleBlock | None:
        stmt = select(ScheduleBlockORM).where(ScheduleBlockORM.id == block_id)
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm is not None else None

    async def get_by_schedule_id(
        self,
        official_schedule_id: UUID,
        sync_status_in: list[str] | None = None,
    ) -> list[ScheduleBlock]:
        stmt = select(ScheduleBlockORM).where(
            ScheduleBlockORM.official_schedule_id == official_schedule_id
        )
        if sync_status_in:
            stmt = stmt.where(ScheduleBlockORM.sync_status.in_(sync_status_in))
        stmt = stmt.order_by(ScheduleBlockORM.start_time.asc())
        result = await self.session.execute(stmt)
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def get_by_external_event_id(self, external_event_id: str) -> ScheduleBlock | None:
        stmt = select(ScheduleBlockORM).where(
            ScheduleBlockORM.external_calendar_event_id == external_event_id
        )
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm is not None else None

    async def list_by_roadmap_ids(self, roadmap_ids: Sequence[UUID]) -> list[ScheduleBlock]:
        if not roadmap_ids:
            return []
        stmt = (
            select(ScheduleBlockORM)
            .where(ScheduleBlockORM.roadmap_id.in_(list(roadmap_ids)))
            .order_by(ScheduleBlockORM.start_time.asc())
        )
        result = await self.session.execute(stmt)
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def save(self, block: ScheduleBlock) -> ScheduleBlock:
        stmt = select(ScheduleBlockORM).where(ScheduleBlockORM.id == block.id)
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()

        if orm is None:
            orm = ScheduleBlockORM(
                id=block.id,
                roadmap_id=block.roadmap_id,
                official_schedule_id=block.official_schedule_id,
                task_id=block.task_id,
                sequence_in_task=block.sequence_in_task,
                block_type=block.block_type,
                block_date=block.block_date,
                start_time=block.start_time,
                end_time=block.end_time,
                scheduled_duration_minutes=block.scheduled_duration_minutes,
                is_protected=block.is_protected,
                status=block.status,
                external_calendar_event_id=block.external_calendar_event_id,
                etag=block.etag,
                sync_status=block.sync_status,
                last_synced_at=block.last_synced_at,
                placement_rationale=block.placement_rationale,
                created_at=block.created_at,
                updated_at=block.updated_at,
            )
            self.session.add(orm)
        else:
            orm.roadmap_id = block.roadmap_id
            orm.official_schedule_id = block.official_schedule_id
            orm.task_id = block.task_id
            orm.sequence_in_task = block.sequence_in_task
            orm.block_type = block.block_type
            orm.block_date = block.block_date
            orm.start_time = block.start_time
            orm.end_time = block.end_time
            orm.scheduled_duration_minutes = block.scheduled_duration_minutes
            orm.is_protected = block.is_protected
            orm.status = block.status
            orm.external_calendar_event_id = block.external_calendar_event_id
            orm.etag = block.etag
            orm.sync_status = block.sync_status
            orm.last_synced_at = block.last_synced_at
            orm.placement_rationale = block.placement_rationale
            orm.updated_at = block.updated_at

        await self.session.flush()
        return self._to_domain(orm)

    async def save_all(self, blocks: list[ScheduleBlock]) -> list[ScheduleBlock]:
        saved: list[ScheduleBlock] = []
        for b in blocks:
            saved.append(await self.save(b))
        return saved
