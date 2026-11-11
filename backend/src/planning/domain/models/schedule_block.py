from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from uuid import UUID

from src.shared_kernel.domain.base import AggregateRoot, generate_uuid7, utc_now


@dataclass
class ScheduleBlock(AggregateRoot):
    """Domain model representing a scheduled study time block (UC-17 / UC-18)."""

    roadmap_id: UUID = field(default_factory=generate_uuid7)
    official_schedule_id: UUID = field(default_factory=generate_uuid7)
    task_id: UUID | None = None
    sequence_in_task: int = 1
    block_type: str = "STUDY"  # STUDY, BUFFER, REVISION, RECOVERY
    block_date: date = field(default_factory=date.today)
    start_time: datetime = field(default_factory=utc_now)
    end_time: datetime = field(default_factory=utc_now)
    scheduled_duration_minutes: int = 30
    is_protected: bool = False
    status: str = "PLANNED"  # PLANNED, COMPLETED, MISSED, RESCHEDULED, CANCELLED
    external_calendar_event_id: str | None = None
    etag: str | None = None
    sync_status: str = "SYNCED"  # PENDING_SYNC, SYNCED, PENDING_REVIEW, EXTERNAL_DELETED
    last_synced_at: datetime | None = None
    placement_rationale: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def mark_synced(
        self,
        event_id: str,
        etag: str | None = None,
        synced_at: datetime | None = None,
    ) -> None:
        self.external_calendar_event_id = event_id
        if etag is not None:
            self.etag = etag
        self.sync_status = "SYNCED"
        self.last_synced_at = synced_at or utc_now()
        self.updated_at = utc_now()

    def mark_pending_review(self, etag: str | None = None) -> None:
        if etag is not None:
            self.etag = etag
        self.sync_status = "PENDING_REVIEW"
        self.last_synced_at = utc_now()
        self.updated_at = utc_now()

    def mark_external_deleted(self) -> None:
        self.sync_status = "EXTERNAL_DELETED"
        self.last_synced_at = utc_now()
        self.updated_at = utc_now()

    def is_echo(self, external_start: datetime, external_end: datetime) -> bool:
        """Content & Version Echo Check: verify if external event times match internal block times."""

        def to_utc(dt: datetime) -> datetime:
            return dt if dt.tzinfo else dt.replace(tzinfo=UTC)

        return (
            abs((to_utc(external_start) - to_utc(self.start_time)).total_seconds()) < 1.0
            and abs((to_utc(external_end) - to_utc(self.end_time)).total_seconds()) < 1.0
        )
