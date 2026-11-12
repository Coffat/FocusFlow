from datetime import UTC, datetime, time
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Time,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from uuid6 import uuid7

from src.shared_kernel.infrastructure.database.session import Base


class AvailabilityORM(Base):
    """Availability profile table (`availabilities`) mapping to AvailabilityProfile Aggregate."""

    __tablename__ = "availabilities"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_availabilities_user_id"),
        CheckConstraint("mode IN ('MODE_A', 'MODE_B')", name="chk_availabilities_mode"),
        CheckConstraint(
            "calendar_integration_mode IN ('NONE', 'EXPORT_ICS', 'CONNECTED')",
            name="chk_availabilities_cal_mode",
        ),
        CheckConstraint(
            "min_session_minutes BETWEEN 15 AND 120",
            name="chk_availabilities_min_session",
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid7)
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    mode: Mapped[str] = mapped_column(String(20), nullable=False, default="MODE_A")
    calendar_integration_mode: Mapped[str] = mapped_column(
        String(20), nullable=False, default="NONE"
    )
    daily_quotas: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    min_session_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class AvailabilitySlotORM(Base):
    """Normalized 3NF/BCNF time slots table (`availability_slots`)."""

    __tablename__ = "availability_slots"
    __table_args__ = (
        Index("idx_avail_slots_availability_day", "availability_id", "day_of_week"),
        CheckConstraint("day_of_week BETWEEN 0 AND 6", name="chk_avail_slots_day"),
        CheckConstraint("end_day_offset IN (0, 1)", name="chk_avail_slots_offset"),
        CheckConstraint("slot_type IN ('ALLOWED', 'FIXED')", name="chk_avail_slots_type"),
        CheckConstraint(
            "end_day_offset = 1 OR end_time > start_time",
            name="chk_avail_slots_time",
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid7)
    availability_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("availabilities.id", ondelete="CASCADE"),
        nullable=False,
    )
    day_of_week: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_day_offset: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0, server_default="0"
    )
    slot_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="ALLOWED", server_default="ALLOWED"
    )
    energy_level: Mapped[str] = mapped_column(
        String(10), nullable=False, default="MEDIUM", server_default="MEDIUM"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
