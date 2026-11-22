from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class NotificationItemDTO(BaseModel):
    """API representation of a single persistent notification."""

    id: UUID
    notification_type: str
    title: str
    content: str
    resource_url: str | None = None
    is_read: bool
    read_at: datetime | None = None
    created_at: datetime


class NotificationListResponseDTO(BaseModel):
    """Paginated notification list with unread counter."""

    items: list[NotificationItemDTO] = Field(default_factory=list)
    total: int
    unread_count: int


class MarkAllNotificationsReadResponseDTO(BaseModel):
    """Response payload for marking all user notifications as read."""

    updated_count: int
