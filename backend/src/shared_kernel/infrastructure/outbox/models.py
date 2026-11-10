from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from uuid6 import uuid7

from src.shared_kernel.infrastructure.database.session import Base


class OutboxEventORM(Base):
    """Transactional Outbox table (`outbox_events`) ensuring zero lost domain events."""

    __tablename__ = "outbox_events"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'PUBLISHED', 'FAILED')",
            name="chk_outbox_events_status",
        ),
        CheckConstraint("retry_count >= 0", name="chk_outbox_events_retry"),
        CheckConstraint("jsonb_typeof(payload) = 'object'", name="chk_outbox_events_payload"),
        CheckConstraint(
            "(status = 'PUBLISHED' AND published_at IS NOT NULL) OR (status != 'PUBLISHED' AND published_at IS NULL)",
            name="chk_outbox_events_published",
        ),
        Index(
            "idx_outbox_events_pending",
            "created_at",
            postgresql_where=text("status = 'PENDING'"),
        ),
        Index("idx_outbox_events_aggregate", "aggregate_type", "aggregate_id"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid7)
    aggregate_type: Mapped[str] = mapped_column(String(100), nullable=False)
    aggregate_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PENDING", server_default="PENDING"
    )
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def event_id(self) -> UUID:
        return self.id

    @event_id.setter
    def event_id(self, val: UUID) -> None:
        self.id = val


class ProcessedEventORM(Base):
    """Idempotent Consumer deduplication log (`processed_events`)."""

    __tablename__ = "processed_events"

    event_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("outbox_events.id", ondelete="CASCADE"), primary_key=True
    )
    handler_name: Mapped[str] = mapped_column(String(120), primary_key=True)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    @property
    def consumer_name(self) -> str:
        return self.handler_name

    @consumer_name.setter
    def consumer_name(self, val: str) -> None:
        self.handler_name = val
