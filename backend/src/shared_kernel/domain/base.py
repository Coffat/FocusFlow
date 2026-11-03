from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from uuid6 import uuid7

from src.shared_kernel.domain.events import DomainEvent


def generate_uuid7() -> UUID:
    """Generate a time-ordered UUIDv7 identifier."""
    return uuid7()


def utc_now() -> datetime:
    """Return timezone-aware UTC timestamp."""
    return datetime.now(UTC)


@dataclass(frozen=True)
class ValueObject:
    """Immutable Value Object base class compared by value."""


@dataclass
class Entity:
    """Base Domain Entity identified by UUIDv7."""

    id: UUID = field(default_factory=generate_uuid7)


@dataclass
class AggregateRoot(Entity):
    """Base Aggregate Root that records domain events for Transactional Outbox dispatch."""

    _domain_events: list[DomainEvent] = field(default_factory=list, init=False, repr=False)

    def add_domain_event(self, event: DomainEvent) -> None:
        self._domain_events.append(event)

    def pull_domain_events(self) -> list[DomainEvent]:
        events = list(self._domain_events)
        self._domain_events.clear()
        return events
