from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.shared_kernel.infrastructure.database.session import Base


class WorkflowRunORM(Base):
    __tablename__ = "workflow_runs"
    __table_args__ = (
        CheckConstraint(
            "workflow_type IN ('PLAN_CREATION', 'SCHEDULE_GENERATION', 'OVERDUE_RECOVERY', 'WEEKLY_REVIEW', 'CONTINUOUS_LEARNING')",
            name="chk_workflow_runs_type",
        ),
        CheckConstraint(
            "status IN ('RUNNING', 'PAUSED_WAITING_USER', 'COMPLETED', 'FAILED', 'CANCELLED')",
            name="chk_workflow_runs_status",
        ),
        CheckConstraint(
            "jsonb_typeof(context_snapshot) = 'object'", name="chk_workflow_runs_snapshot"
        ),
        Index("idx_workflow_runs_user_status", "user_id", "status", "updated_at"),
        Index("idx_workflow_runs_roadmap_type", "roadmap_id", "workflow_type"),
        Index("idx_workflow_runs_goal_id", "goal_id"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    goal_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("goals.id", ondelete="CASCADE"), nullable=True
    )
    roadmap_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("roadmaps.id", ondelete="CASCADE"), nullable=True
    )
    workflow_type: Mapped[str] = mapped_column(String(40), nullable=False)
    current_step: Mapped[str] = mapped_column(String(60), nullable=False)
    status: Mapped[str] = mapped_column(String(25), nullable=False, default="RUNNING")
    context_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )


class WorkflowStepExecutionORM(Base):
    __tablename__ = "workflow_step_executions"
    __table_args__ = (
        CheckConstraint("step_order >= 1", name="chk_workflow_steps_order"),
        CheckConstraint(
            "status IN ('PENDING', 'RUNNING', 'WAITING_USER', 'COMPLETED', 'FAILED', 'SKIPPED')",
            name="chk_workflow_steps_status",
        ),
        CheckConstraint(
            "jsonb_typeof(input_summary) = 'object'", name="chk_workflow_steps_input_json"
        ),
        CheckConstraint(
            "jsonb_typeof(output_payload) = 'object'", name="chk_workflow_steps_output_json"
        ),
        CheckConstraint("retry_count >= 0", name="chk_workflow_steps_retry"),
        Index("idx_workflow_step_executions_run_order", "workflow_run_id", "step_order"),
        Index("idx_workflow_step_executions_ai_log_id", "ai_usage_log_id"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    workflow_run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workflow_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    step_name: Mapped[str] = mapped_column(String(60), nullable=False)
    step_order: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(25), nullable=False, default="RUNNING")
    input_summary: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    output_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    ai_usage_log_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ai_usage_logs.id", ondelete="SET NULL"),
        nullable=True,
    )
    retry_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
