from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from src.shared_kernel.domain.events import DomainEvent


class EventBusPort(Protocol):
    """Protocol for publishing domain events to in-process handlers or background workers."""

    async def publish(self, event: DomainEvent) -> None: ...

    async def publish_all(self, events: Sequence[DomainEvent]) -> None: ...


class OutboxRepositoryPort(Protocol):
    """Protocol for persisting and polling Transactional Outbox & Idempotent Consumer events."""

    async def add_events(self, events: Sequence[DomainEvent]) -> None: ...

    async def is_event_processed(self, event_id: UUID, consumer_name: str) -> bool: ...

    async def mark_event_processed(self, event_id: UUID, consumer_name: str) -> None: ...
