from datetime import UTC, date, datetime
from typing import Any
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
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from uuid6 import uuid7

from src.shared_kernel.infrastructure.database.session import Base


class GoalORM(Base):
    """Planning Goals table (`goals`) matching 0002_complete_24_tables_schema.py."""

    __tablename__ = "goals"
    __table_args__ = (
        CheckConstraint(
            "status IN ('ACTIVE', 'COMPLETED', 'ARCHIVED')",
            name="chk_goals_status",
        ),
        Index("idx_goals_user_id", "user_id"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid7)
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE", name="fk_goals_user"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    raw_description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
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


class RoadmapORM(Base):
    """Planning Roadmaps table (`roadmaps`) matching 0002_complete_24_tables_schema.py."""

    __tablename__ = "roadmaps"
    __table_args__ = (
        CheckConstraint(
            "status IN ('INITIALIZED', 'ACTIVE', 'PAUSED', 'COMPLETED', 'ARCHIVED')",
            name="chk_roadmaps_status",
        ),
        CheckConstraint(
            "target_date IS NULL OR start_date IS NULL OR target_date >= start_date",
            name="chk_roadmaps_dates",
        ),
        Index("idx_roadmaps_user_status", "user_id", "status"),
        Index("idx_roadmaps_goal_id", "goal_id"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid7)
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE", name="fk_roadmaps_user"),
        nullable=False,
    )
    goal_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("goals.id", ondelete="CASCADE", name="fk_roadmaps_goal"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="INITIALIZED")
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class MilestoneORM(Base):
    """Planning Milestones table (`milestones`) matching 0002_complete_24_tables_schema.py."""

    __tablename__ = "milestones"
    __table_args__ = (
        UniqueConstraint(
            "roadmap_id",
            "sequence_order",
            name="uq_milestones_roadmap_seq",
            deferrable=True,
            initially="DEFERRED",
        ),
        CheckConstraint("sequence_order >= 1", name="chk_milestones_seq"),
        CheckConstraint(
            "status IN ('PENDING', 'APPROVED', 'IN_PROGRESS', 'COMPLETED')",
            name="chk_milestones_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid7)
    roadmap_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("roadmaps.id", ondelete="CASCADE", name="fk_milestones_roadmap"),
        nullable=False,
    )
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class OfficialScheduleORM(Base):
    """Planning Official Schedules table (`official_schedules`) matching 0002_complete_24_tables_schema.py."""

    __tablename__ = "official_schedules"
    __table_args__ = (
        UniqueConstraint("roadmap_id", name="uq_official_schedules_roadmap"),
        CheckConstraint("total_sessions >= 0", name="chk_official_schedules_sessions"),
        CheckConstraint(
            "total_planned_minutes >= 0",
            name="chk_official_schedules_minutes",
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid7)
    roadmap_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("roadmaps.id", ondelete="CASCADE", name="fk_official_schedules_roadmap"),
        unique=True,
        nullable=False,
    )
    total_sessions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_planned_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    activated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
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


class ScheduleProposalORM(Base):
    """Planning Schedule Proposals table (`schedule_proposals`) matching 0002_complete_24_tables_schema.py."""

    __tablename__ = "schedule_proposals"
    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT', 'APPLIED', 'DISCARDED')",
            name="chk_schedule_proposals_status",
        ),
        CheckConstraint(
            "jsonb_typeof(proposal_data) = 'object'",
            name="chk_schedule_proposals_data",
        ),
        Index(
            "uq_schedule_proposals_roadmap_draft",
            "roadmap_id",
            unique=True,
            postgresql_where="status = 'DRAFT'",
        ),
        Index("idx_schedule_proposals_roadmap_status", "roadmap_id", "status"),
        Index("idx_schedule_proposals_user_id", "user_id"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid7)
    roadmap_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("roadmaps.id", ondelete="CASCADE", name="fk_schedule_proposals_roadmap"),
        nullable=False,
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE", name="fk_schedule_proposals_user"),
        nullable=False,
    )
    proposal_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
