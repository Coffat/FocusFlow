from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
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
    prior_knowledge_level: Mapped[str] = mapped_column(
        String(50), nullable=False, default="BEGINNER"
    )
    clarification_context: Mapped[str | None] = mapped_column(Text, nullable=True)
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
    weekly_reschedule_budget: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=3)
    weekly_reschedule_used: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    budget_week_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_study_activity_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reset_ritual_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
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
    proof_status: Mapped[str] = mapped_column(String(20), nullable=False, default="UNVERIFIED")
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
    buffer_minutes_per_week: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    recovery_window_days: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=7)
    daily_workload_cap_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=180)
    stability_weight: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False, default=0.8)
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
    proposal_type: Mapped[str] = mapped_column(
        String(35), nullable=False, default="INITIAL_SCHEDULE"
    )
    original_proposal_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    user_edit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pedagogical_warnings: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list
    )
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


class LearningConceptORM(Base):
    """Curated Knowledge Base concepts table (`learning_concepts`)."""

    __tablename__ = "learning_concepts"
    __table_args__ = (
        CheckConstraint(
            "verification_status IN ('VERIFIED', 'UNVERIFIED', 'DEPRECATED')",
            name="chk_learning_concepts_verification_status",
        ),
        CheckConstraint(
            "estimated_effort_minutes > 0",
            name="chk_learning_concepts_effort_positive",
        ),
        Index(
            "idx_learning_concepts_domain_level",
            "domain",
            "difficulty_level",
            "verification_status",
        ),
    )

    concept_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    domain: Mapped[str] = mapped_column(String(100), nullable=False)
    difficulty_level: Mapped[str] = mapped_column(String(50), nullable=False, default="BEGINNER")
    estimated_effort_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    keywords: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    learning_outcomes: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    verification_status: Mapped[str] = mapped_column(String(30), nullable=False, default="VERIFIED")
    version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0.0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class ConceptPrerequisiteORM(Base):
    """Directed prerequisite edges between curated concepts (`concept_prerequisites`)."""

    __tablename__ = "concept_prerequisites"
    __table_args__ = (
        CheckConstraint(
            "relation_type IN ('REQUIRES', 'RECOMMENDED_BEFORE')",
            name="chk_concept_prerequisites_relation_type",
        ),
        CheckConstraint(
            "source_concept_id <> prerequisite_concept_id",
            name="chk_concept_prerequisites_no_self_loop",
        ),
        Index("idx_concept_prerequisites_source", "source_concept_id"),
        Index("idx_concept_prerequisites_prereq", "prerequisite_concept_id"),
    )

    source_concept_id: Mapped[str] = mapped_column(
        String(120),
        ForeignKey(
            "learning_concepts.concept_id",
            ondelete="CASCADE",
            name="fk_concept_prerequisites_source",
        ),
        primary_key=True,
    )
    prerequisite_concept_id: Mapped[str] = mapped_column(
        String(120),
        ForeignKey(
            "learning_concepts.concept_id",
            ondelete="CASCADE",
            name="fk_concept_prerequisites_prereq",
        ),
        primary_key=True,
    )
    relation_type: Mapped[str] = mapped_column(String(30), nullable=False, default="REQUIRES")
    rationale: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )


class ScheduleBlockORM(Base):
    """Planning Schedule Blocks table (`schedule_blocks`) matching 0006_calendar_connections_and_schedule_blocks.py."""

    __tablename__ = "schedule_blocks"
    __table_args__ = (
        CheckConstraint("sequence_in_task >= 1", name="chk_schedule_blocks_seq"),
        CheckConstraint(
            "block_type IN ('STUDY', 'BUFFER', 'REVISION', 'RECOVERY')",
            name="chk_schedule_blocks_type",
        ),
        CheckConstraint(
            "scheduled_duration_minutes BETWEEN 10 AND 240",
            name="chk_schedule_blocks_duration",
        ),
        CheckConstraint(
            "status IN ('PLANNED', 'COMPLETED', 'MISSED', 'RESCHEDULED', 'CANCELLED')",
            name="chk_schedule_blocks_status",
        ),
        CheckConstraint("end_time > start_time", name="chk_schedule_blocks_time_order"),
        Index("idx_schedule_blocks_roadmap_date", "roadmap_id", "block_date", "start_time"),
        Index("idx_schedule_blocks_schedule_id", "official_schedule_id"),
        Index(
            "idx_schedule_blocks_task_id",
            "task_id",
            postgresql_where=text("task_id IS NOT NULL"),
        ),
        Index(
            "idx_schedule_blocks_external_event",
            "external_calendar_event_id",
            postgresql_where=text("external_calendar_event_id IS NOT NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid7)
    roadmap_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("roadmaps.id", ondelete="CASCADE", name="fk_schedule_blocks_roadmap"),
        nullable=False,
    )
    official_schedule_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "official_schedules.id",
            ondelete="CASCADE",
            name="fk_schedule_blocks_schedule",
        ),
        nullable=False,
    )
    task_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE", name="fk_schedule_blocks_task"),
        nullable=True,
    )
    sequence_in_task: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    block_type: Mapped[str] = mapped_column(String(20), nullable=False, default="STUDY")
    block_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    scheduled_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    is_protected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PLANNED")
    external_calendar_event_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    etag: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sync_status: Mapped[str] = mapped_column(String(30), nullable=False, default="SYNCED")
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    placement_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
