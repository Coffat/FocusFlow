from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from src.planning.domain.models.schedule_block import ScheduleBlock


class ScheduleBlockRepositoryPort(Protocol):
    """Driven Port for persisting and querying ScheduleBlock entities (UC-17 / UC-18)."""

    async def get_by_id(self, block_id: UUID) -> ScheduleBlock | None:
        """Find schedule block by primary key."""
        ...

    async def get_by_schedule_id(
        self,
        official_schedule_id: UUID,
        sync_status_in: list[str] | None = None,
    ) -> list[ScheduleBlock]:
        """List blocks for an official schedule, optionally filtered by sync_status."""
        ...

    async def list_by_roadmap_ids(self, roadmap_ids: Sequence[UUID]) -> list[ScheduleBlock]:
        """Return blocks belonging to active roadmaps without crossing context tables."""
        ...

    async def get_by_external_event_id(self, external_event_id: str) -> ScheduleBlock | None:
        """Find block by Google/Outlook external calendar event ID."""
        ...

    async def save(self, block: ScheduleBlock) -> ScheduleBlock:
        """Persist or update schedule block."""
        ...

    async def save_all(self, blocks: list[ScheduleBlock]) -> list[ScheduleBlock]:
        """Persist multiple schedule blocks."""
        ...
