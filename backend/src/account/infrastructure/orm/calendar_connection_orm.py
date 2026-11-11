import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from uuid6 import uuid7

from src.shared_kernel.infrastructure.database.session import Base


class CalendarConnectionORM(Base):
    """SQLAlchemy ORM model for calendar_connections table (UC-17, 3NF/BCNF)."""

    __tablename__ = "calendar_connections"
    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uq_calendar_connections_user_provider"),
        CheckConstraint(
            "provider IN ('GOOGLE', 'OUTLOOK', 'LOCAL_MOCK')",
            name="chk_calendar_connections_provider",
        ),
        CheckConstraint(
            "sync_status IN ('ACTIVE', 'REVOKED', 'ERROR')",
            name="chk_calendar_connections_status",
        ),
        Index("idx_calendar_connections_user_status", "user_id", "sync_status"),
        Index("idx_calendar_connections_channel", "channel_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid7,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(String(30), nullable=False, default="GOOGLE")
    external_calendar_id: Mapped[str] = mapped_column(
        String(255), nullable=False, default="primary"
    )
    oauth_refresh_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    sync_status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
    sync_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    channel_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    channel_token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    channel_expiration: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    source_calendars_json: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, default=lambda: ["primary"]
    )
    sync_metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
