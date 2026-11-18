from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared_kernel.application.event_bus import OutboxRepositoryPort
from src.shared_kernel.domain.events import DomainEvent
from src.shared_kernel.infrastructure.outbox.models import OutboxEventORM, ProcessedEventORM
from src.shared_kernel.logging import correlation_id_ctx


class SqlAlchemyOutboxRepository(OutboxRepositoryPort):
    """SQLAlchemy implementation of `OutboxRepositoryPort` & `processed_events` deduplication."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_events(self, events: Sequence[DomainEvent]) -> None:
        corr_id = correlation_id_ctx.get()
        for event in events:
            entry = OutboxEventORM(
                id=event.event_id,
                aggregate_type=event.aggregate_type,
                aggregate_id=event.aggregate_id,
                event_type=event.event_type,
                payload=event.to_payload(),
                correlation_id=corr_id,
            )
            self._session.add(entry)
        await self._session.flush()

    async def is_event_processed(self, event_id: UUID, consumer_name: str) -> bool:
        stmt = select(ProcessedEventORM.event_id).where(
            ProcessedEventORM.event_id == event_id,
            ProcessedEventORM.handler_name == consumer_name,
        )
        return (await self._session.execute(stmt)).scalar_one_or_none() is not None

    async def mark_event_processed(self, event_id: UUID, consumer_name: str) -> None:
        stmt = (
            pg_insert(ProcessedEventORM)
            .values(
                event_id=event_id,
                handler_name=consumer_name,
                processed_at=datetime.now(UTC),
            )
            .on_conflict_do_nothing(
                index_elements=["event_id", "handler_name"],
            )
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def list_unprocessed_events(
        self,
        *,
        event_type: str,
        consumer_name: str,
        limit: int = 50,
    ) -> list[OutboxEventORM]:
        processed_subq = select(ProcessedEventORM.event_id).where(
            ProcessedEventORM.handler_name == consumer_name
        )
        stmt = (
            select(OutboxEventORM)
            .where(
                OutboxEventORM.event_type == event_type,
                OutboxEventORM.id.not_in(processed_subq),
            )
            .order_by(OutboxEventORM.created_at.asc())
            .limit(limit)
        )
        return list((await self._session.execute(stmt)).scalars().all())
