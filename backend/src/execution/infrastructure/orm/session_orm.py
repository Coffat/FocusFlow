from datetime import UTC, datetime
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
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from uuid6 import uuid7

from src.shared_kernel.infrastructure.database.session import Base


class StudySessionORM(Base):
    """Execution Study Sessions table (`study_sessions`) matching 0002 and 0009 migrations."""

    __tablename__ = "study_sessions"
    __table_args__ = (
        CheckConstraint("planned_minutes > 0", name="chk_study_sessions_planned_min"),
        CheckConstraint("actual_minutes >= 0", name="chk_study_sessions_actual_min"),
        CheckConstraint(
            "status IN ('IN_PROGRESS', 'COMPLETED', 'PARTIAL_COMPLETED', 'CANCELLED')",
            name="chk_study_sessions_status",
        ),
        CheckConstraint(
            "ended_at IS NULL OR ended_at >= started_at",
            name="chk_study_sessions_times",
        ),
        CheckConstraint(
            "(status = 'IN_PROGRESS' AND ended_at IS NULL) OR (status != 'IN_PROGRESS' AND ended_at IS NOT NULL)",
            name="chk_study_sessions_status_ended",
        ),
        CheckConstraint(
            "session_mode IN ('STANDARD', 'MVS')",
            name="chk_study_sessions_mode",
        ),
        Index(
            "uq_study_sessions_user_active",
            "user_id",
            unique=True,
            postgresql_where=text("status = 'IN_PROGRESS'"),
        ),
        Index("idx_study_sessions_user_started", "user_id", text("started_at DESC")),
        Index("idx_study_sessions_roadmap_started", "roadmap_id", text("started_at DESC")),
        Index(
            "idx_study_sessions_heartbeat",
            "last_heartbeat_at",
            postgresql_where=text("status = 'IN_PROGRESS'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid7)
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE", name="fk_study_sessions_user"),
        nullable=False,
    )
    roadmap_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("roadmaps.id", ondelete="CASCADE", name="fk_study_sessions_roadmap"),
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    planned_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    actual_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="IN_PROGRESS")
    last_heartbeat_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    session_mode: Mapped[str] = mapped_column(String(15), nullable=False, default="STANDARD")
    pending_takeaway: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    checkin_time_sufficiency: Mapped[str | None] = mapped_column(String(15), nullable=True)
    checkin_perceived_difficulty: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    checkin_focus_level: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
