from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from src.shared_kernel.domain.base import AggregateRoot, generate_uuid7, utc_now


@dataclass
class CalendarConnection(AggregateRoot):
    """Domain model representing a 2-way external calendar connection (UC-17, 3NF/BCNF)."""

    user_id: UUID = field(default_factory=generate_uuid7)
    provider: str = "GOOGLE"
    external_calendar_id: str = "primary"
    oauth_refresh_token_encrypted: str = ""
    sync_status: str = "ACTIVE"
    sync_token: str | None = None
    channel_id: str | None = None
    resource_id: str | None = None
    channel_token_hash: str | None = None
    channel_expiration: datetime | None = None
    source_calendars_json: list[str] = field(default_factory=lambda: ["primary"])
    sync_metadata_json: dict[str, Any] = field(default_factory=dict)
    last_synced_at: datetime | None = None
    error_detail: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    @property
    def is_active(self) -> bool:
        """Check if connection is in ACTIVE sync status."""
        return self.sync_status == "ACTIVE"

    def is_channel_expired(self, now: datetime | None = None) -> bool:
        """Check if active webhook watch channel has expired or is absent."""
        if not self.channel_id or not self.channel_expiration:
            return True
        current_time = now if now is not None else utc_now()
        return current_time >= self.channel_expiration

    def mark_active(self, sync_token: str | None = None) -> None:
        """Mark connection as ACTIVE and clear errors."""
        self.sync_status = "ACTIVE"
        self.error_detail = None
        if sync_token is not None:
            self.sync_token = sync_token
        self.updated_at = utc_now()

    def mark_revoked(self, reason: str | None = None) -> None:
        """Mark connection as REVOKED and wipe push notification channel registration."""
        self.sync_status = "REVOKED"
        self.error_detail = reason
        self.clear_channel()
        self.updated_at = utc_now()

    def mark_error(self, detail: str) -> None:
        """Mark connection in ERROR state with diagnostic details."""
        self.sync_status = "ERROR"
        self.error_detail = detail
        self.updated_at = utc_now()

    def update_channel(
        self,
        channel_id: str,
        resource_id: str,
        expiration: datetime | None,
        token_hash: str | None = None,
    ) -> None:
        """Update webhook watch channel metadata."""
        self.channel_id = channel_id
        self.resource_id = resource_id
        self.channel_expiration = expiration
        self.channel_token_hash = token_hash
        self.updated_at = utc_now()

    def clear_channel(self) -> None:
        """Clear webhook channel metadata."""
        self.channel_id = None
        self.resource_id = None
        self.channel_expiration = None
        self.channel_token_hash = None
        self.updated_at = utc_now()

    def record_sync_success(self, new_sync_token: str | None = None) -> None:
        """Record successful synchronization iteration."""
        if new_sync_token is not None:
            self.sync_token = new_sync_token
        self.last_synced_at = utc_now()
        self.error_detail = None
        self.updated_at = utc_now()
