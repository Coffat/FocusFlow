from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class NotificationRecordDTO:
    """Immutable persistence record for a learner notification."""

    id: UUID
    user_id: UUID
    event_id: UUID | None
    notification_type: str
    title: str
    content: str
    resource_url: str | None
    is_read: bool
    read_at: datetime | None
    created_at: datetime
    updated_at: datetime


class NotificationRepositoryPort(Protocol):
    """Repository port for persistent notifications in Account context (FE-MOCK-08)."""

    async def create_idempotent(
        self,
        *,
        user_id: UUID,
        notification_type: str,
        title: str,
        content: str,
        event_id: UUID | None = None,
        resource_url: str | None = None,
    ) -> NotificationRecordDTO | None: ...

    async def list_for_user(
        self,
        user_id: UUID,
        *,
        limit: int = 20,
        offset: int = 0,
        unread_only: bool = False,
    ) -> tuple[list[NotificationRecordDTO], int, int]: ...

    async def mark_read(
        self,
        notification_id: UUID,
        user_id: UUID,
        *,
        now: datetime,
    ) -> NotificationRecordDTO | None: ...

    async def mark_all_read(
        self,
        user_id: UUID,
        *,
        now: datetime,
    ) -> int: ...
