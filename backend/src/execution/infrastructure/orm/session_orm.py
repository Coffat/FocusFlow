from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
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


class SessionTaskORM(Base):
    """Execution Session Tasks join table (`session_tasks`) matching schema.sql."""

    __tablename__ = "session_tasks"
    __table_args__ = (
        UniqueConstraint("session_id", "task_id", name="uq_session_tasks_session_task"),
        CheckConstraint("actual_minutes >= 0", name="chk_session_tasks_actual"),
        CheckConstraint("allocated_minutes >= 0", name="chk_session_tasks_allocated"),
        CheckConstraint(
            "status_after_session IN ('TODO', 'IN_PROGRESS', 'COMPLETED')",
            name="chk_session_tasks_status_after",
        ),
        Index("idx_session_tasks_session_id", "session_id"),
        Index("idx_session_tasks_task_id", "task_id"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid7)
    session_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("study_sessions.id", ondelete="CASCADE", name="fk_session_tasks_session"),
        nullable=False,
    )
    task_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="RESTRICT", name="fk_session_tasks_task"),
        nullable=False,
    )
    allocated_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    actual_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status_after_session: Mapped[str] = mapped_column(
        String(20), nullable=False, default="IN_PROGRESS"
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class StudyNoteORM(Base):
    """Execution Study Notes table (`study_notes`) matching schema.sql."""

    __tablename__ = "study_notes"
    __table_args__ = (
        UniqueConstraint("session_id", "note_type", name="uq_study_notes_session_type"),
        CheckConstraint(
            "note_type IN ('SCRATCHPAD', 'TAKEAWAY', 'GENERAL')",
            name="chk_study_notes_type",
        ),
        CheckConstraint(
            "self_confidence IS NULL OR (self_confidence >= 1 AND self_confidence <= 5)",
            name="chk_study_notes_confidence",
        ),
        CheckConstraint(
            "ai_evidence_score IS NULL OR (ai_evidence_score >= 1 AND ai_evidence_score <= 5)",
            name="chk_study_notes_evidence",
        ),
        CheckConstraint(
            "alignment_flag IN ('UNCHECKED', 'ALIGNED', 'SUPERFICIAL', 'OFF_TOPIC', 'CONTRADICTORY')",
            name="chk_study_notes_alignment",
        ),
        CheckConstraint(
            "verification_status IN ('PENDING_PROVE', 'VERIFIED', 'FLAGGED_SHALLOW', 'NEEDS_REVIEW')",
            name="chk_study_notes_verification",
        ),
        Index("idx_study_notes_task_id", "task_id"),
        Index("idx_study_notes_user_session", "user_id", "session_id"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid7)
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE", name="fk_study_notes_user"),
        nullable=False,
    )
    session_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("study_sessions.id", ondelete="CASCADE", name="fk_study_notes_session"),
        nullable=True,
    )
    task_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="SET NULL", name="fk_study_notes_task"),
        nullable=True,
    )
    note_type: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    self_confidence: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    ai_evidence_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    alignment_flag: Mapped[str] = mapped_column(String(20), nullable=False, default="UNCHECKED")
    verification_status: Mapped[str] = mapped_column(
        String(25), nullable=False, default="PENDING_PROVE"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
