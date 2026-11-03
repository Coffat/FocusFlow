from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
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
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from uuid6 import uuid7

from src.shared_kernel.infrastructure.database.session import Base


class TaskORM(Base):
    """Execution Tasks table (`tasks`) matching 0002_complete_24_tables_schema.py."""

    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint(
            "estimated_minutes BETWEEN 15 AND 240",
            name="chk_tasks_estimated_minutes",
        ),
        CheckConstraint(
            "status IN ('TODO', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED')",
            name="chk_tasks_status",
        ),
        CheckConstraint("reschedule_count >= 0", name="chk_tasks_reschedule_count"),
        CheckConstraint(
            "(scheduled_start IS NULL AND scheduled_end IS NULL) OR "
            "(scheduled_start IS NOT NULL AND scheduled_end IS NOT NULL AND scheduled_end > scheduled_start)",
            name="chk_tasks_scheduled_time_order",
        ),
        CheckConstraint(
            "(status = 'COMPLETED' AND completed_at IS NOT NULL) OR "
            "(status != 'COMPLETED' AND completed_at IS NULL)",
            name="chk_tasks_completed_at",
        ),
        Index("idx_tasks_roadmap_scheduled_date", "roadmap_id", "scheduled_date"),
        Index(
            "idx_tasks_scheduled_start",
            "scheduled_start",
            postgresql_where="scheduled_start IS NOT NULL",
        ),
        Index(
            "idx_tasks_overdue",
            "scheduled_date",
            postgresql_where="status IN ('TODO', 'IN_PROGRESS') AND scheduled_date IS NOT NULL",
        ),
        Index("idx_tasks_milestone_id", "milestone_id"),
        Index("idx_tasks_official_schedule_id", "official_schedule_id"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid7)
    roadmap_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("roadmaps.id", ondelete="CASCADE", name="fk_tasks_roadmap"),
        nullable=False,
    )
    milestone_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("milestones.id", ondelete="CASCADE", name="fk_tasks_milestone"),
        nullable=False,
    )
    official_schedule_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "official_schedules.id",
            ondelete="SET NULL",
            name="fk_tasks_official_schedule",
        ),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    scheduled_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    scheduled_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scheduled_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="TODO")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reschedule_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class TaskDependencyORM(Base):
    """Execution Task Dependencies DAG edges table (`task_dependencies`)."""

    __tablename__ = "task_dependencies"
    __table_args__ = (
        UniqueConstraint("predecessor_id", "successor_id", name="uq_task_deps_pair"),
        CheckConstraint("predecessor_id <> successor_id", name="chk_task_deps_not_self"),
        Index("idx_task_deps_successor", "successor_id"),
        Index("idx_task_deps_predecessor", "predecessor_id"),
        Index("idx_task_deps_roadmap", "roadmap_id"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid7)
    predecessor_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE", name="fk_task_deps_pred"),
        nullable=False,
    )
    successor_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE", name="fk_task_deps_succ"),
        nullable=False,
    )
    roadmap_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("roadmaps.id", ondelete="CASCADE", name="fk_task_deps_roadmap"),
        nullable=False,
    )
    is_mandatory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
