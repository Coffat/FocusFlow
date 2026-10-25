from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from uuid6 import uuid7


@dataclass(frozen=True, kw_only=True)
class DomainEvent:
    """Immutable base class for all intra-context and inter-context Domain Events."""

    event_id: UUID = field(default_factory=uuid7)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    aggregate_type: str = "UnknownAggregate"
    aggregate_id: UUID = field(default_factory=uuid7)

    @property
    def event_type(self) -> str:
        return self.__class__.__name__

    def to_payload(self) -> dict[str, Any]:
        raw = asdict(self)
        return {
            key: (str(val) if isinstance(val, (UUID, datetime)) else val)
            for key, val in raw.items()
        }
