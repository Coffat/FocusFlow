from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from uuid6 import uuid7

from src.shared_kernel.infrastructure.database.session import Base


class PauseRecordORM(Base):
    """Roadmap Pause Records table (`pause_records`) matching docs/database/schema.sql:504-518."""

    __tablename__ = "pause_records"
    __table_args__ = (
        CheckConstraint("pause_end_date >= pause_start_date", name="chk_pause_records_dates"),
        CheckConstraint(
            "shifted_days = ((pause_end_date - pause_start_date) + 1)",
            name="chk_pause_records_duration",
        ),
        CheckConstraint("shifted_days > 0", name="chk_pause_records_shifted"),
        CheckConstraint(
            "status IN ('ACTIVE', 'COMPLETED', 'CANCELLED')",
            name="chk_pause_records_status",
        ),
        Index("idx_pause_records_roadmap_id", "roadmap_id"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid7)
    roadmap_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("roadmaps.id", ondelete="CASCADE", name="fk_pause_records_roadmap"),
        nullable=False,
    )
    pause_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    pause_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    shifted_days: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
