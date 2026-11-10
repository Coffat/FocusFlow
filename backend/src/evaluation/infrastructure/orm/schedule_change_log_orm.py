from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from uuid6 import uuid7

from src.shared_kernel.infrastructure.database.session import Base


class ScheduleChangeLogORM(Base):
    """Schedule Change Audit Log table (`schedule_change_logs`) matching 0002_complete_24_tables_schema.py."""

    __tablename__ = "schedule_change_logs"
    __table_args__ = (
        CheckConstraint(
            "trigger_type IN ('DOMINO_SHIFT', 'MANUAL_EDIT', 'AI_REPLAN', 'CALENDAR_SYNC')",
            name="chk_sched_change_logs_trigger",
        ),
        CheckConstraint("affected_tasks_count >= 0", name="chk_sched_change_logs_affected"),
        CheckConstraint("total_shifted_minutes >= 0", name="chk_sched_change_logs_minutes"),
        CheckConstraint(
            "jsonb_typeof(diff_payload) = 'object'",
            name="chk_sched_change_logs_payload",
        ),
        Index("idx_sched_change_logs_roadmap_created", "roadmap_id", "created_at"),
        Index("idx_sched_change_logs_trigger", "trigger_type", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid7)
    roadmap_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "roadmaps.id",
            ondelete="CASCADE",
            name="fk_sched_change_logs_roadmap",
        ),
        nullable=False,
    )
    schedule_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "official_schedules.id",
            ondelete="SET NULL",
            name="fk_sched_change_logs_schedule",
        ),
        nullable=True,
    )
    task_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "tasks.id",
            ondelete="SET NULL",
            name="fk_sched_change_logs_task",
        ),
        nullable=True,
    )
    trigger_type: Mapped[str] = mapped_column(String(30), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    affected_tasks_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    total_shifted_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    diff_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
