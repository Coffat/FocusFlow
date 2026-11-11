from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class InitiateCalendarAuthRequestDTO:
    """Request payload to initiate Google Calendar OAuth authorization (UC-17)."""

    sync_type: str = "two_way"  # "inbound" | "two_way"
    redirect_uri: str | None = None


@dataclass(frozen=True)
class InitiateCalendarAuthResponseDTO:
    """Response containing Google OAuth authorization URL and CSRF state token."""

    authorization_url: str
    state: str


@dataclass(frozen=True)
class CalendarOAuthCallbackRequestDTO:
    """Callback payload received from Google OAuth redirection."""

    code: str
    state: str


@dataclass(frozen=True)
class CalendarConnectionResponseDTO:
    """Public representation of external calendar connection status."""

    connected: bool
    provider: str = "GOOGLE"
    sync_status: str = "REVOKED"
    external_calendar_id: str | None = None
    source_calendars: list[str] = field(default_factory=list)
    last_synced_at: datetime | None = None
    error_detail: str | None = None


@dataclass(frozen=True)
class OutboundSyncResultDTO:
    """Result of outbound synchronization of schedule blocks to external calendar."""

    schedule_id: str
    user_id: str
    total_blocks_scanned: int
    synced_blocks_count: int
    conflict_resolved_count: int = 0
    skipped: bool = False
    error_detail: str | None = None


@dataclass(frozen=True)
class InboundSyncResultDTO:
    """Result of inbound synchronization from external calendar webhook push."""

    channel_id: str
    total_events_received: int
    echo_ignored_count: int
    pending_review_count: int
    deleted_blocks_count: int
    full_reconciliation_triggered: bool = False
    new_sync_token: str | None = None
