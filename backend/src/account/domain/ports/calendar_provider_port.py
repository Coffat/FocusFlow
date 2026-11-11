from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.shared_kernel.domain.exceptions import DomainError


class CalendarProviderError(DomainError):
    """Base exception for external calendar provider operations (UC-17)."""

    def __init__(
        self, message: str = "Lỗi dịch vụ lịch ngoại vi.", code: str = "CALENDAR_ERROR"
    ) -> None:
        super().__init__(message=message, code=code)


def get_deterministic_event_id(block_id: UUID) -> str:
    """Generate deterministic event ID matching Google Calendar [a-v0-9]{5,1024} regex."""
    return f"ff{block_id.hex.lower()}"


class CalendarGoneError(CalendarProviderError):
    """Raised when external sync token is invalid or expired (HTTP 410 Gone)."""

    def __init__(
        self,
        message: str = "Sync token lịch ngoại vi đã hết hạn hoặc không hợp lệ (410 Gone).",
        code: str = "CALENDAR_SYNC_TOKEN_EXPIRED",
    ) -> None:
        super().__init__(message=message, code=code)


class CalendarConflictError(CalendarProviderError):
    """Raised when an event ID already exists or clashes (HTTP 409 Conflict)."""

    def __init__(
        self,
        message: str = "Sự kiện lịch đã tồn tại hoặc bị xung đột định danh (409 Conflict).",
        code: str = "CALENDAR_EVENT_CONFLICT",
    ) -> None:
        super().__init__(message=message, code=code)


class CalendarPreconditionFailedError(CalendarProviderError):
    """Raised when event etag or version mismatches (HTTP 412 Precondition Failed)."""

    def __init__(
        self,
        message: str = "Tiền điều kiện ETag không khớp, sự kiện đã bị sửa đổi ngoại vi (412 Precondition Failed).",
        code: str = "CALENDAR_PRECONDITION_FAILED",
    ) -> None:
        super().__init__(message=message, code=code)


class CalendarRateLimitError(CalendarProviderError):
    """Raised when external calendar API rate limits or quotas are exceeded (HTTP 429)."""

    def __init__(
        self,
        message: str = "Vượt quá hạn ngạch gọi Google Calendar API (429 Rate Limit).",
        code: str = "CALENDAR_RATE_LIMITED",
    ) -> None:
        super().__init__(message=message, code=code)


class CalendarAuthError(CalendarProviderError):
    """Raised when OAuth token exchange or refresh fails (HTTP 401 Unauthorized)."""

    def __init__(
        self,
        message: str = "Ủy quyền OAuth lịch ngoại vi không thành công hoặc token đã bị thu hồi.",
        code: str = "CALENDAR_AUTH_ERROR",
    ) -> None:
        super().__init__(message=message, code=code)


@dataclass(frozen=True)
class CalendarTimeInterval:
    """Time interval representing busy periods from external calendars."""

    start_time: datetime
    end_time: datetime


@dataclass
class CalendarEventDTO:
    """Representation of an external calendar event mapped to FocusFlow schedule block."""

    id: str
    title: str
    start_time: datetime
    end_time: datetime
    description: str | None = None
    location: str | None = None
    etag: str | None = None
    status: str = "confirmed"  # "confirmed", "tentative", "cancelled"
    block_id: UUID | None = None
    extended_properties: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class CalendarWatchResultDTO:
    """Metadata returned upon successful registration of Google Calendar push notifications."""

    channel_id: str
    resource_id: str
    expiration: datetime | None
    token: str | None = None


@dataclass(frozen=True)
class CalendarSyncEventsResultDTO:
    """Paginated or incremental event sync result."""

    events: list[CalendarEventDTO]
    next_sync_token: str | None = None
    next_page_token: str | None = None
    sync_reset_needed: bool = False


class CalendarProviderPort(Protocol):
    """Driven Port for external calendar integration (Google Calendar v3, Outlook, Mock)."""

    async def get_free_busy_intervals(
        self,
        refresh_token: str,
        calendar_ids: list[str],
        time_min: datetime,
        time_max: datetime,
    ) -> list[CalendarTimeInterval]:
        """Query busy intervals from external calendars for schedule optimization."""
        ...

    async def create_secondary_calendar(
        self,
        refresh_token: str,
        title: str = "FocusFlow",
    ) -> str:
        """Create a dedicated secondary calendar and return its external_calendar_id."""
        ...

    async def list_events(
        self,
        refresh_token: str,
        calendar_id: str,
        sync_token: str | None = None,
        page_token: str | None = None,
        time_min: datetime | None = None,
        time_max: datetime | None = None,
    ) -> CalendarSyncEventsResultDTO:
        """Fetch incremental changes or events with pagination and syncToken support."""
        ...

    async def get_event(
        self,
        refresh_token: str,
        calendar_id: str,
        event_id: str,
    ) -> CalendarEventDTO | None:
        """Fetch a single event by ID (events.get) for 409 conflict recovery."""
        ...

    async def create_event(
        self,
        refresh_token: str,
        calendar_id: str,
        event: CalendarEventDTO,
    ) -> CalendarEventDTO:
        """Create an event on external calendar with client-specified deterministic ID."""
        ...

    async def update_event(
        self,
        refresh_token: str,
        calendar_id: str,
        event: CalendarEventDTO,
    ) -> CalendarEventDTO:
        """Update an existing event with optimistic concurrency control (ETag)."""
        ...

    async def delete_event(
        self,
        refresh_token: str,
        calendar_id: str,
        event_id: str,
        etag: str | None = None,
    ) -> bool:
        """Delete an event from external calendar."""
        ...

    async def watch_calendar(
        self,
        refresh_token: str,
        calendar_id: str,
        channel_id: str,
        webhook_url: str,
        channel_token: str | None = None,
    ) -> CalendarWatchResultDTO:
        """Establish push notifications via webhooks for instant inbound sync."""
        ...

    async def stop_watch_channel(
        self,
        refresh_token: str,
        channel_id: str,
        resource_id: str,
    ) -> bool:
        """Stop push notifications for a registered channel."""
        ...
