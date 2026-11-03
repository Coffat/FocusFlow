from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession

from src.shared_kernel.application.uow import AsyncUnitOfWork
from src.shared_kernel.domain.base import AggregateRoot
from src.shared_kernel.infrastructure.outbox.models import OutboxEventORM
from src.shared_kernel.logging import correlation_id_ctx


class SqlAlchemyUnitOfWork(AsyncUnitOfWork):
    """Concrete SQLAlchemy Unit of Work with Transactional Outbox event collection."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()

    def collect_events_from(self, aggregate: AggregateRoot) -> None:
        """Extract domain events from an aggregate root to persist into outbox_events on commit."""
        events = aggregate.pull_domain_events()
        corr_id = correlation_id_ctx.get()
        for event in events:
            outbox_entry = OutboxEventORM(
                id=event.event_id,
                aggregate_type=event.aggregate_type,
                aggregate_id=event.aggregate_id,
                event_type=event.event_type,
                payload=event.to_payload(),
                correlation_id=corr_id,
            )
            self.session.add(outbox_entry)

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
