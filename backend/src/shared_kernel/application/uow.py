from types import TracebackType
from typing import Protocol, Self

from src.shared_kernel.domain.base import AggregateRoot


class AsyncUnitOfWork(Protocol):
    """Protocol for transactional Unit of Work with Transactional Outbox event collection."""

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None: ...

    def collect_events_from(self, aggregate: AggregateRoot) -> None:
        """Extract domain events from an aggregate root to persist into outbox_events on commit."""
        ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
