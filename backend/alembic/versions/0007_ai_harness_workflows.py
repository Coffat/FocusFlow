"""Add durable AI harness workflows and usage telemetry.

Revision ID: 0007_ai_harness_workflows
Revises: 0006_calendar_connections_and_schedule_blocks
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0007_ai_harness_workflows"
down_revision: str | None = "0006_calendar_and_blocks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("chk_ai_usage_logs_action", "ai_usage_logs", type_="check")
    op.create_check_constraint(
        "chk_ai_usage_logs_action",
        "ai_usage_logs",
        "action_type IN ('ROADMAP_GENERATION', 'SCHEDULE_PROPOSAL', 'AI_REVIEW_WEEKLY', 'AI_REVIEW_MILESTONE', 'MILESTONE_BREAKDOWN', 'CHAT_ASSISTANT', 'KNOWLEDGE_INGESTION', 'WHAT_IF_SIMULATION', 'OVERDUE_RECOVERY', 'CONTINUOUS_LEARNING')",
    )
    op.add_column(
        "ai_usage_logs",
        sa.Column("estimated_cost_usd", sa.Numeric(12, 6), nullable=False, server_default="0"),
    )
    op.add_column("ai_usage_logs", sa.Column("error_code", sa.String(80), nullable=True))

    op.create_table(
        "workflow_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "goal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("goals.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "roadmap_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("roadmaps.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("workflow_type", sa.String(40), nullable=False),
        sa.Column("current_step", sa.String(60), nullable=False),
        sa.Column("status", sa.String(25), nullable=False, server_default="RUNNING"),
        sa.Column(
            "context_snapshot",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("error_detail", sa.Text, nullable=True),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "workflow_type IN ('PLAN_CREATION', 'SCHEDULE_GENERATION', 'OVERDUE_RECOVERY', 'WEEKLY_REVIEW', 'CONTINUOUS_LEARNING')",
            name="chk_workflow_runs_type",
        ),
        sa.CheckConstraint(
            "status IN ('RUNNING', 'PAUSED_WAITING_USER', 'COMPLETED', 'FAILED', 'CANCELLED')",
            name="chk_workflow_runs_status",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(context_snapshot) = 'object'", name="chk_workflow_runs_snapshot"
        ),
    )
    op.create_index(
        "idx_workflow_runs_user_status", "workflow_runs", ["user_id", "status", "updated_at"]
    )
    op.create_index(
        "idx_workflow_runs_roadmap_type", "workflow_runs", ["roadmap_id", "workflow_type"]
    )
    op.create_index("idx_workflow_runs_goal_id", "workflow_runs", ["goal_id"])

    op.create_table(
        "workflow_step_executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workflow_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workflow_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("step_name", sa.String(60), nullable=False),
        sa.Column("step_order", sa.SmallInteger, nullable=False),
        sa.Column("status", sa.String(25), nullable=False, server_default="RUNNING"),
        sa.Column(
            "input_summary", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column(
            "output_payload",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "ai_usage_log_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ai_usage_logs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("retry_count", sa.SmallInteger, nullable=False, server_default="0"),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("step_order >= 1", name="chk_workflow_steps_order"),
        sa.CheckConstraint(
            "status IN ('PENDING', 'RUNNING', 'WAITING_USER', 'COMPLETED', 'FAILED', 'SKIPPED')",
            name="chk_workflow_steps_status",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(input_summary) = 'object'", name="chk_workflow_steps_input_json"
        ),
        sa.CheckConstraint(
            "jsonb_typeof(output_payload) = 'object'", name="chk_workflow_steps_output_json"
        ),
        sa.CheckConstraint("retry_count >= 0", name="chk_workflow_steps_retry"),
    )
    op.create_index(
        "idx_workflow_step_executions_run_order",
        "workflow_step_executions",
        ["workflow_run_id", "step_order"],
    )
    op.create_index(
        "idx_workflow_step_executions_ai_log_id",
        "workflow_step_executions",
        ["ai_usage_log_id"],
    )


def downgrade() -> None:
    op.drop_table("workflow_step_executions")
    op.drop_table("workflow_runs")
    op.drop_column("ai_usage_logs", "error_code")
    op.drop_column("ai_usage_logs", "estimated_cost_usd")
    op.drop_constraint("chk_ai_usage_logs_action", "ai_usage_logs", type_="check")
    op.create_check_constraint(
        "chk_ai_usage_logs_action",
        "ai_usage_logs",
        "action_type IN ('ROADMAP_GENERATION', 'SCHEDULE_PROPOSAL', 'AI_REVIEW_WEEKLY', 'AI_REVIEW_MILESTONE', 'MILESTONE_BREAKDOWN', 'CHAT_ASSISTANT')",
    )
