"""Add 7 missing foreign key indexes for query and cascade performance

Revision ID: 0005_add_missing_fk_indexes
Revises: 0004_knowledge_base_tables
Create Date: 2026-05-10 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005_add_missing_fk_indexes"
down_revision: str | None = "0004_knowledge_base_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    # 1. ai_quota_reservations.quota_id
    if "ai_quota_reservations" in existing_tables:
        op.create_index(
            "idx_ai_quota_reservations_quota_id",
            "ai_quota_reservations",
            ["quota_id"],
            unique=False,
            if_not_exists=True,
        )

    # 2. schedule_change_logs.schedule_id (partial index WHERE schedule_id IS NOT NULL)
    if "schedule_change_logs" in existing_tables:
        op.create_index(
            "idx_sched_change_logs_schedule_id",
            "schedule_change_logs",
            ["schedule_id"],
            unique=False,
            postgresql_where=sa.text("schedule_id IS NOT NULL"),
            if_not_exists=True,
        )

    # 3. schedule_change_logs.task_id (partial index WHERE task_id IS NOT NULL)
    if "schedule_change_logs" in existing_tables:
        op.create_index(
            "idx_sched_change_logs_task_id",
            "schedule_change_logs",
            ["task_id"],
            unique=False,
            postgresql_where=sa.text("task_id IS NOT NULL"),
            if_not_exists=True,
        )

    # 4 & 5. milestone_proofs
    if "milestone_proofs" in existing_tables:
        op.create_index(
            "idx_milestone_proofs_roadmap_id",
            "milestone_proofs",
            ["roadmap_id"],
            unique=False,
            if_not_exists=True,
        )
        op.create_index(
            "idx_milestone_proofs_corrective_task_id",
            "milestone_proofs",
            ["corrective_task_id"],
            unique=False,
            postgresql_where=sa.text("corrective_task_id IS NOT NULL"),
            if_not_exists=True,
        )

    # 6. workflow_runs
    if "workflow_runs" in existing_tables:
        op.create_index(
            "idx_workflow_runs_goal_id",
            "workflow_runs",
            ["goal_id"],
            unique=False,
            postgresql_where=sa.text("goal_id IS NOT NULL"),
            if_not_exists=True,
        )

    # 7. workflow_step_executions
    if "workflow_step_executions" in existing_tables:
        op.create_index(
            "idx_workflow_step_executions_ai_log_id",
            "workflow_step_executions",
            ["ai_usage_log_id"],
            unique=False,
            postgresql_where=sa.text("ai_usage_log_id IS NOT NULL"),
            if_not_exists=True,
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if "workflow_step_executions" in existing_tables:
        op.drop_index(
            "idx_workflow_step_executions_ai_log_id",
            table_name="workflow_step_executions",
            if_exists=True,
        )
    if "workflow_runs" in existing_tables:
        op.drop_index(
            "idx_workflow_runs_goal_id",
            table_name="workflow_runs",
            if_exists=True,
        )
    if "milestone_proofs" in existing_tables:
        op.drop_index(
            "idx_milestone_proofs_corrective_task_id",
            table_name="milestone_proofs",
            if_exists=True,
        )
        op.drop_index(
            "idx_milestone_proofs_roadmap_id",
            table_name="milestone_proofs",
            if_exists=True,
        )
    if "schedule_change_logs" in existing_tables:
        op.drop_index(
            "idx_sched_change_logs_task_id",
            table_name="schedule_change_logs",
            if_exists=True,
        )
        op.drop_index(
            "idx_sched_change_logs_schedule_id",
            table_name="schedule_change_logs",
            if_exists=True,
        )
    if "ai_quota_reservations" in existing_tables:
        op.drop_index(
            "idx_ai_quota_reservations_quota_id",
            table_name="ai_quota_reservations",
            if_exists=True,
        )
