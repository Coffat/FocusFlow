"""Complete 24-table relational database schema (18 remaining tables)

Revision ID: 0002_complete_24_tables
Revises: 0001_account_avail
Create Date: 2026-10-30 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_complete_24_tables"
down_revision: str | None = "0001_account_avail"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 0. Shared trigger function for updated_at
    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    # =========================================================================
    # BOUNDED CONTEXT 1: ACCOUNT (5 remaining tables of 9)
    # =========================================================================

    # 2. learner_profiles
    op.create_table(
        "learner_profiles",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE", name="fk_learner_profiles_user"),
            nullable=False,
        ),
        sa.Column("optimal_focus_duration_mins", sa.Integer(), nullable=False, server_default="25"),
        sa.Column(
            "peak_productivity_slots",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text('\'["MORNING", "EVENING"]\'::jsonb'),
        ),
        sa.Column(
            "estimation_bias_factor",
            sa.Numeric(4, 2),
            nullable=False,
            server_default="1.00",
        ),
        sa.Column(
            "weekly_completion_rate",
            sa.Numeric(5, 2),
            nullable=False,
            server_default="0.00",
        ),
        sa.Column("total_completed_sessions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "is_cold_start",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("TRUE"),
        ),
        sa.Column(
            "last_aggregated_at",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint("user_id", name="uq_learner_profiles_user_id"),
        sa.CheckConstraint(
            "optimal_focus_duration_mins BETWEEN 15 AND 120",
            name="chk_learner_profiles_duration",
        ),
        sa.CheckConstraint(
            "estimation_bias_factor BETWEEN 0.50 AND 2.00",
            name="chk_learner_profiles_bias",
        ),
        sa.CheckConstraint(
            "weekly_completion_rate BETWEEN 0.00 AND 100.00",
            name="chk_learner_profiles_rate",
        ),
        sa.CheckConstraint(
            "total_completed_sessions >= 0",
            name="chk_learner_profiles_sessions",
        ),
        if_not_exists=True,
    )

    # 3. webcal_tokens
    op.create_table(
        "webcal_tokens",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE", name="fk_webcal_tokens_user"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("oauth_refresh_token_encrypted", sa.Text(), nullable=True),
        sa.Column("external_calendar_id", sa.String(255), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("TRUE"),
        ),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint("user_id", name="uq_webcal_tokens_user_id"),
        sa.UniqueConstraint("token_hash", name="uq_webcal_tokens_token_hash"),
        sa.CheckConstraint(
            "token_hash ~ '^[0-9a-f]{64}$'",
            name="chk_webcal_tokens_hash",
        ),
        if_not_exists=True,
    )

    # 7. ai_quota_reservations
    op.create_table(
        "ai_quota_reservations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "quota_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ai_quotas.id", ondelete="CASCADE", name="fk_ai_quota_res_quota"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE", name="fk_ai_quota_res_user"),
            nullable=False,
        ),
        sa.Column("operation_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="RESERVED"),
        sa.Column("tokens_reserved", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('RESERVED', 'COMMITTED', 'RELEASED', 'EXPIRED')",
            name="chk_ai_quota_res_status",
        ),
        sa.CheckConstraint("tokens_reserved >= 0", name="chk_ai_quota_res_tokens"),
        sa.CheckConstraint(
            "(status = 'RESERVED' AND resolved_at IS NULL) OR (status != 'RESERVED' AND resolved_at IS NOT NULL)",
            name="chk_ai_quota_res_resolved",
        ),
        if_not_exists=True,
    )
    op.create_index(
        "idx_quota_reservations_cleanup",
        "ai_quota_reservations",
        ["expires_at"],
        postgresql_where=sa.text("status = 'RESERVED'"),
        if_not_exists=True,
    )
    op.create_index(
        "idx_quota_reservations_user_status",
        "ai_quota_reservations",
        ["user_id", "status", sa.text("created_at DESC")],
        if_not_exists=True,
    )

    # 8. ai_usage_logs
    op.create_table(
        "ai_usage_logs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE", name="fk_ai_usage_logs_user"),
            nullable=False,
        ),
        sa.Column("action_type", sa.String(50), nullable=False),
        sa.Column("model_name", sa.String(100), nullable=False, server_default="gpt-4o-mini"),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="SUCCESS"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint(
            "action_type IN ('ROADMAP_GENERATION', 'SCHEDULE_PROPOSAL', 'AI_REVIEW_WEEKLY', 'AI_REVIEW_MILESTONE', 'MILESTONE_BREAKDOWN', 'CHAT_ASSISTANT')",
            name="chk_ai_usage_logs_action",
        ),
        sa.CheckConstraint(
            "prompt_tokens >= 0 AND completion_tokens >= 0 AND total_tokens >= 0",
            name="chk_ai_usage_logs_tokens",
        ),
        sa.CheckConstraint("latency_ms >= 0", name="chk_ai_usage_logs_latency"),
        sa.CheckConstraint(
            "status IN ('SUCCESS', 'FAILED', 'RATE_LIMITED', 'TIMEOUT')",
            name="chk_ai_usage_logs_status",
        ),
        if_not_exists=True,
    )
    op.create_index(
        "idx_ai_usage_logs_user_action",
        "ai_usage_logs",
        ["user_id", "action_type", sa.text("created_at DESC")],
        if_not_exists=True,
    )

    # 9. payment_transactions
    op.create_table(
        "payment_transactions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT", name="fk_payment_transactions_user"),
            nullable=False,
        ),
        sa.Column("transaction_ref", sa.String(100), nullable=False),
        sa.Column("gateway_provider", sa.String(20), nullable=False, server_default="PAYOS"),
        sa.Column("amount_vnd", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False, server_default="VND"),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("qr_code_url", sa.Text(), nullable=True),
        sa.Column(
            "webhook_signature_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("FALSE"),
        ),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint("transaction_ref", name="uq_payment_transactions_ref"),
        sa.CheckConstraint(
            "gateway_provider IN ('PAYOS', 'VNPAY', 'MOCK')",
            name="chk_payment_transactions_provider",
        ),
        sa.CheckConstraint("amount_vnd > 0", name="chk_payment_transactions_amount"),
        sa.CheckConstraint(
            "status IN ('PENDING', 'PAID', 'FAILED', 'CANCELLED', 'REFUNDED')",
            name="chk_payment_transactions_status",
        ),
        sa.CheckConstraint(
            "(status IN ('PAID', 'REFUNDED') AND paid_at IS NOT NULL) OR (status NOT IN ('PAID', 'REFUNDED') AND paid_at IS NULL)",
            name="chk_payment_transactions_paid_at",
        ),
        if_not_exists=True,
    )
    op.create_index(
        "idx_payment_transactions_user_created",
        "payment_transactions",
        ["user_id", sa.text("created_at DESC")],
        if_not_exists=True,
    )
    op.create_index(
        "idx_payment_transactions_status",
        "payment_transactions",
        ["status", sa.text("created_at DESC")],
        if_not_exists=True,
    )

    # =========================================================================
    # BOUNDED CONTEXT 2: PLANNING (5 tables)
    # =========================================================================

    # 10. goals
    op.create_table(
        "goals",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE", name="fk_goals_user"),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("raw_description", sa.Text(), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'COMPLETED', 'ARCHIVED')",
            name="chk_goals_status",
        ),
        if_not_exists=True,
    )
    op.create_index(
        "idx_goals_user_id",
        "goals",
        ["user_id"],
        if_not_exists=True,
    )

    # 11. roadmaps
    op.create_table(
        "roadmaps",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE", name="fk_roadmaps_user"),
            nullable=False,
        ),
        sa.Column(
            "goal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("goals.id", ondelete="CASCADE", name="fk_roadmaps_goal"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="INITIALIZED"),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint(
            "status IN ('INITIALIZED', 'ACTIVE', 'PAUSED', 'COMPLETED', 'ARCHIVED')",
            name="chk_roadmaps_status",
        ),
        sa.CheckConstraint(
            "target_date IS NULL OR start_date IS NULL OR target_date >= start_date",
            name="chk_roadmaps_dates",
        ),
        if_not_exists=True,
    )
    op.create_index(
        "idx_roadmaps_user_status",
        "roadmaps",
        ["user_id", "status"],
        if_not_exists=True,
    )
    op.create_index(
        "idx_roadmaps_goal_id",
        "roadmaps",
        ["goal_id"],
        if_not_exists=True,
    )

    # 12. milestones
    op.create_table(
        "milestones",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "roadmap_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("roadmaps.id", ondelete="CASCADE", name="fk_milestones_roadmap"),
            nullable=False,
        ),
        sa.Column("sequence_order", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint(
            "roadmap_id",
            "sequence_order",
            name="uq_milestones_roadmap_seq",
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.CheckConstraint("sequence_order >= 1", name="chk_milestones_seq"),
        sa.CheckConstraint(
            "status IN ('PENDING', 'APPROVED', 'IN_PROGRESS', 'COMPLETED')",
            name="chk_milestones_status",
        ),
        if_not_exists=True,
    )

    # 13. official_schedules
    op.create_table(
        "official_schedules",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "roadmap_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("roadmaps.id", ondelete="CASCADE", name="fk_official_schedules_roadmap"),
            nullable=False,
        ),
        sa.Column("total_sessions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_planned_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "activated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint("roadmap_id", name="uq_official_schedules_roadmap"),
        sa.CheckConstraint("total_sessions >= 0", name="chk_official_schedules_sessions"),
        sa.CheckConstraint(
            "total_planned_minutes >= 0",
            name="chk_official_schedules_minutes",
        ),
        if_not_exists=True,
    )

    # 14. schedule_proposals
    op.create_table(
        "schedule_proposals",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "roadmap_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("roadmaps.id", ondelete="CASCADE", name="fk_schedule_proposals_roadmap"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE", name="fk_schedule_proposals_user"),
            nullable=False,
        ),
        sa.Column(
            "proposal_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="DRAFT"),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'APPLIED', 'DISCARDED')",
            name="chk_schedule_proposals_status",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(proposal_data) = 'object'",
            name="chk_schedule_proposals_data",
        ),
        if_not_exists=True,
    )
    op.create_index(
        "uq_schedule_proposals_roadmap_draft",
        "schedule_proposals",
        ["roadmap_id"],
        unique=True,
        postgresql_where=sa.text("status = 'DRAFT'"),
        if_not_exists=True,
    )
    op.create_index(
        "idx_schedule_proposals_roadmap_status",
        "schedule_proposals",
        ["roadmap_id", "status"],
        if_not_exists=True,
    )
    op.create_index(
        "idx_schedule_proposals_user_id",
        "schedule_proposals",
        ["user_id"],
        if_not_exists=True,
    )

    # =========================================================================
    # BOUNDED CONTEXT 3: EXECUTION (5 tables)
    # =========================================================================

    # 15. tasks
    op.create_table(
        "tasks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "roadmap_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("roadmaps.id", ondelete="CASCADE", name="fk_tasks_roadmap"),
            nullable=False,
        ),
        sa.Column(
            "milestone_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("milestones.id", ondelete="CASCADE", name="fk_tasks_milestone"),
            nullable=False,
        ),
        sa.Column(
            "official_schedule_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "official_schedules.id",
                ondelete="SET NULL",
                name="fk_tasks_official_schedule",
            ),
            nullable=True,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("estimated_minutes", sa.Integer(), nullable=False),
        sa.Column("scheduled_date", sa.Date(), nullable=True),
        sa.Column("scheduled_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scheduled_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="TODO"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reschedule_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint(
            "estimated_minutes BETWEEN 15 AND 240",
            name="chk_tasks_estimated_minutes",
        ),
        sa.CheckConstraint(
            "status IN ('TODO', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED')",
            name="chk_tasks_status",
        ),
        sa.CheckConstraint("reschedule_count >= 0", name="chk_tasks_reschedule_count"),
        sa.CheckConstraint(
            "(scheduled_start IS NULL AND scheduled_end IS NULL) OR (scheduled_start IS NOT NULL AND scheduled_end IS NOT NULL AND scheduled_end > scheduled_start)",
            name="chk_tasks_scheduled_time_order",
        ),
        sa.CheckConstraint(
            "(status = 'COMPLETED' AND completed_at IS NOT NULL) OR (status != 'COMPLETED' AND completed_at IS NULL)",
            name="chk_tasks_completed_at",
        ),
        if_not_exists=True,
    )
    op.create_index(
        "idx_tasks_roadmap_scheduled_date",
        "tasks",
        ["roadmap_id", "scheduled_date"],
        if_not_exists=True,
    )
    op.create_index(
        "idx_tasks_scheduled_start",
        "tasks",
        ["scheduled_start"],
        postgresql_where=sa.text("scheduled_start IS NOT NULL"),
        if_not_exists=True,
    )
    op.create_index(
        "idx_tasks_overdue",
        "tasks",
        ["scheduled_date"],
        postgresql_where=sa.text(
            "status IN ('TODO', 'IN_PROGRESS') AND scheduled_date IS NOT NULL"
        ),
        if_not_exists=True,
    )
    op.create_index(
        "idx_tasks_milestone_id",
        "tasks",
        ["milestone_id"],
        if_not_exists=True,
    )
    op.create_index(
        "idx_tasks_official_schedule_id",
        "tasks",
        ["official_schedule_id"],
        if_not_exists=True,
    )

    # 16. task_dependencies
    op.create_table(
        "task_dependencies",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "predecessor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="CASCADE", name="fk_task_deps_pred"),
            nullable=False,
        ),
        sa.Column(
            "successor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="CASCADE", name="fk_task_deps_succ"),
            nullable=False,
        ),
        sa.Column(
            "roadmap_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("roadmaps.id", ondelete="CASCADE", name="fk_task_deps_roadmap"),
            nullable=False,
        ),
        sa.Column(
            "is_mandatory",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("TRUE"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint("predecessor_id", "successor_id", name="uq_task_deps_pair"),
        sa.CheckConstraint("predecessor_id <> successor_id", name="chk_task_deps_not_self"),
        if_not_exists=True,
    )
    op.create_index(
        "idx_task_deps_successor",
        "task_dependencies",
        ["successor_id"],
        if_not_exists=True,
    )
    op.create_index(
        "idx_task_deps_predecessor",
        "task_dependencies",
        ["predecessor_id"],
        if_not_exists=True,
    )
    op.create_index(
        "idx_task_deps_roadmap",
        "task_dependencies",
        ["roadmap_id"],
        if_not_exists=True,
    )

    # 17. study_sessions
    op.create_table(
        "study_sessions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE", name="fk_study_sessions_user"),
            nullable=False,
        ),
        sa.Column(
            "roadmap_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("roadmaps.id", ondelete="CASCADE", name="fk_study_sessions_roadmap"),
            nullable=False,
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("planned_minutes", sa.Integer(), nullable=False),
        sa.Column("actual_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="IN_PROGRESS"),
        sa.Column(
            "last_heartbeat_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint("planned_minutes > 0", name="chk_study_sessions_planned_min"),
        sa.CheckConstraint("actual_minutes >= 0", name="chk_study_sessions_actual_min"),
        sa.CheckConstraint(
            "status IN ('IN_PROGRESS', 'COMPLETED', 'PARTIAL_COMPLETED', 'CANCELLED')",
            name="chk_study_sessions_status",
        ),
        sa.CheckConstraint(
            "ended_at IS NULL OR ended_at >= started_at",
            name="chk_study_sessions_times",
        ),
        sa.CheckConstraint(
            "(status = 'IN_PROGRESS' AND ended_at IS NULL) OR (status != 'IN_PROGRESS' AND ended_at IS NOT NULL)",
            name="chk_study_sessions_status_ended",
        ),
        if_not_exists=True,
    )
    op.create_index(
        "uq_study_sessions_user_active",
        "study_sessions",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'IN_PROGRESS'"),
        if_not_exists=True,
    )
    op.create_index(
        "idx_study_sessions_user_started",
        "study_sessions",
        ["user_id", sa.text("started_at DESC")],
        if_not_exists=True,
    )
    op.create_index(
        "idx_study_sessions_roadmap_started",
        "study_sessions",
        ["roadmap_id", sa.text("started_at DESC")],
        if_not_exists=True,
    )
    op.create_index(
        "idx_study_sessions_heartbeat",
        "study_sessions",
        ["last_heartbeat_at"],
        postgresql_where=sa.text("status = 'IN_PROGRESS'"),
        if_not_exists=True,
    )

    # 18. session_tasks
    op.create_table(
        "session_tasks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "study_sessions.id",
                ondelete="CASCADE",
                name="fk_session_tasks_session",
            ),
            nullable=False,
        ),
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="RESTRICT", name="fk_session_tasks_task"),
            nullable=False,
        ),
        sa.Column("allocated_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("actual_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "status_after_session",
            sa.String(20),
            nullable=False,
            server_default="IN_PROGRESS",
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint("session_id", "task_id", name="uq_session_tasks_session_task"),
        sa.CheckConstraint("allocated_minutes >= 0", name="chk_session_tasks_allocated"),
        sa.CheckConstraint("actual_minutes >= 0", name="chk_session_tasks_actual"),
        sa.CheckConstraint(
            "status_after_session IN ('TODO', 'IN_PROGRESS', 'COMPLETED')",
            name="chk_session_tasks_status_after",
        ),
        if_not_exists=True,
    )
    op.create_index(
        "idx_session_tasks_task_id",
        "session_tasks",
        ["task_id"],
        if_not_exists=True,
    )
    op.create_index(
        "idx_session_tasks_session_id",
        "session_tasks",
        ["session_id"],
        if_not_exists=True,
    )

    # 19. study_notes
    op.create_table(
        "study_notes",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE", name="fk_study_notes_user"),
            nullable=False,
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "study_sessions.id",
                ondelete="CASCADE",
                name="fk_study_notes_session",
            ),
            nullable=True,
        ),
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="SET NULL", name="fk_study_notes_task"),
            nullable=True,
        ),
        sa.Column("note_type", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint("session_id", "note_type", name="uq_study_notes_session_type"),
        sa.CheckConstraint(
            "note_type IN ('SCRATCHPAD', 'TAKEAWAY', 'GENERAL')",
            name="chk_study_notes_type",
        ),
        if_not_exists=True,
    )
    op.create_index(
        "idx_study_notes_user_session",
        "study_notes",
        ["user_id", "session_id"],
        if_not_exists=True,
    )
    op.create_index(
        "idx_study_notes_task_id",
        "study_notes",
        ["task_id"],
        if_not_exists=True,
    )

    # =========================================================================
    # BOUNDED CONTEXT 4: EVALUATION (3 tables)
    # =========================================================================

    # 20. pause_records
    op.create_table(
        "pause_records",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "roadmap_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("roadmaps.id", ondelete="CASCADE", name="fk_pause_records_roadmap"),
            nullable=False,
        ),
        sa.Column("pause_start_date", sa.Date(), nullable=False),
        sa.Column("pause_end_date", sa.Date(), nullable=False),
        sa.Column("shifted_days", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint(
            "pause_end_date >= pause_start_date",
            name="chk_pause_records_dates",
        ),
        sa.CheckConstraint("shifted_days > 0", name="chk_pause_records_shifted"),
        sa.CheckConstraint(
            "shifted_days = (pause_end_date - pause_start_date + 1)",
            name="chk_pause_records_duration",
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'COMPLETED', 'CANCELLED')",
            name="chk_pause_records_status",
        ),
        if_not_exists=True,
    )
    op.create_index(
        "idx_pause_records_roadmap_id",
        "pause_records",
        ["roadmap_id"],
        if_not_exists=True,
    )

    # 21. ai_reviews
    op.create_table(
        "ai_reviews",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "roadmap_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("roadmaps.id", ondelete="CASCADE", name="fk_ai_reviews_roadmap"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE", name="fk_ai_reviews_user"),
            nullable=False,
        ),
        sa.Column(
            "milestone_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("milestones.id", ondelete="CASCADE", name="fk_ai_reviews_milestone"),
            nullable=True,
        ),
        sa.Column("review_cycle", sa.String(20), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column(
            "quantitative_summary",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("strengths_feedback", sa.Text(), nullable=False),
        sa.Column("bottlenecks_feedback", sa.Text(), nullable=False),
        sa.Column("action_recommendations", sa.Text(), nullable=False),
        sa.Column("model_used", sa.String(100), nullable=False),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint(
            "review_cycle IN ('WEEKLY', 'MILESTONE')",
            name="chk_ai_reviews_cycle",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(quantitative_summary) = 'object'",
            name="chk_ai_reviews_quantitative_summary",
        ),
        sa.CheckConstraint(
            "(review_cycle = 'MILESTONE' AND milestone_id IS NOT NULL AND period_start IS NULL AND period_end IS NULL) OR (review_cycle = 'WEEKLY' AND milestone_id IS NULL AND period_start IS NOT NULL AND period_end IS NOT NULL AND period_end >= period_start)",
            name="chk_ai_reviews_period_order",
        ),
        if_not_exists=True,
    )
    op.create_index(
        "uq_ai_reviews_weekly",
        "ai_reviews",
        ["roadmap_id", "period_start", "period_end"],
        unique=True,
        postgresql_where=sa.text("review_cycle = 'WEEKLY'"),
        if_not_exists=True,
    )
    op.create_index(
        "uq_ai_reviews_milestone",
        "ai_reviews",
        ["roadmap_id", "milestone_id"],
        unique=True,
        postgresql_where=sa.text("review_cycle = 'MILESTONE'"),
        if_not_exists=True,
    )
    op.create_index(
        "idx_ai_reviews_roadmap_cycle",
        "ai_reviews",
        ["roadmap_id", "review_cycle", sa.text("generated_at DESC")],
        if_not_exists=True,
    )
    op.create_index(
        "idx_ai_reviews_user_id",
        "ai_reviews",
        ["user_id"],
        if_not_exists=True,
    )

    # 22. schedule_change_logs
    op.create_table(
        "schedule_change_logs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "roadmap_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "roadmaps.id",
                ondelete="CASCADE",
                name="fk_sched_change_logs_roadmap",
            ),
            nullable=False,
        ),
        sa.Column(
            "schedule_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "official_schedules.id",
                ondelete="SET NULL",
                name="fk_sched_change_logs_schedule",
            ),
            nullable=True,
        ),
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "tasks.id",
                ondelete="SET NULL",
                name="fk_sched_change_logs_task",
            ),
            nullable=True,
        ),
        sa.Column("trigger_type", sa.String(30), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("affected_tasks_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("total_shifted_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "diff_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint(
            "trigger_type IN ('DOMINO_SHIFT', 'MANUAL_EDIT', 'AI_REPLAN', 'CALENDAR_SYNC')",
            name="chk_sched_change_logs_trigger",
        ),
        sa.CheckConstraint("affected_tasks_count >= 0", name="chk_sched_change_logs_affected"),
        sa.CheckConstraint("total_shifted_minutes >= 0", name="chk_sched_change_logs_minutes"),
        sa.CheckConstraint(
            "jsonb_typeof(diff_payload) = 'object'",
            name="chk_sched_change_logs_payload",
        ),
        if_not_exists=True,
    )
    op.create_index(
        "idx_sched_change_logs_roadmap_created",
        "schedule_change_logs",
        ["roadmap_id", sa.text("created_at DESC")],
        if_not_exists=True,
    )
    op.create_index(
        "idx_sched_change_logs_trigger",
        "schedule_change_logs",
        ["trigger_type", sa.text("created_at DESC")],
        if_not_exists=True,
    )

    # Triggers for updated_at across all 18 tables that have updated_at
    tables_with_updated_at = (
        "users",
        "learner_profiles",
        "webcal_tokens",
        "availabilities",
        "availability_slots",
        "ai_quotas",
        "payment_transactions",
        "goals",
        "roadmaps",
        "milestones",
        "official_schedules",
        "schedule_proposals",
        "tasks",
        "study_sessions",
        "session_tasks",
        "study_notes",
        "pause_records",
        "ai_reviews",
    )
    for tbl in tables_with_updated_at:
        op.execute(f"DROP TRIGGER IF EXISTS trg_{tbl}_updated_at ON {tbl};")
        op.execute(
            f"CREATE TRIGGER trg_{tbl}_updated_at BEFORE UPDATE ON {tbl} "
            "FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();"
        )


def downgrade() -> None:
    # Drop triggers on the 14 newly added tables that have updated_at
    new_tables_with_updated_at = (
        "ai_reviews",
        "pause_records",
        "study_notes",
        "session_tasks",
        "study_sessions",
        "tasks",
        "schedule_proposals",
        "official_schedules",
        "milestones",
        "roadmaps",
        "goals",
        "payment_transactions",
        "webcal_tokens",
        "learner_profiles",
    )
    for tbl in new_tables_with_updated_at:
        op.execute(f"DROP TRIGGER IF EXISTS trg_{tbl}_updated_at ON {tbl};")

    # Evaluation (3 tables)
    op.drop_index(
        "idx_sched_change_logs_trigger",
        table_name="schedule_change_logs",
        if_exists=True,
    )
    op.drop_index(
        "idx_sched_change_logs_roadmap_created",
        table_name="schedule_change_logs",
        if_exists=True,
    )
    op.drop_table("schedule_change_logs", if_exists=True)

    op.drop_index("idx_ai_reviews_user_id", table_name="ai_reviews", if_exists=True)
    op.drop_index("idx_ai_reviews_roadmap_cycle", table_name="ai_reviews", if_exists=True)
    op.drop_index("uq_ai_reviews_milestone", table_name="ai_reviews", if_exists=True)
    op.drop_index("uq_ai_reviews_weekly", table_name="ai_reviews", if_exists=True)
    op.drop_table("ai_reviews", if_exists=True)

    op.drop_index("idx_pause_records_roadmap_id", table_name="pause_records", if_exists=True)
    op.drop_table("pause_records", if_exists=True)

    # Execution (5 tables in reverse dependency order)
    op.drop_index("idx_study_notes_task_id", table_name="study_notes", if_exists=True)
    op.drop_index("idx_study_notes_user_session", table_name="study_notes", if_exists=True)
    op.drop_table("study_notes", if_exists=True)

    op.drop_index("idx_session_tasks_session_id", table_name="session_tasks", if_exists=True)
    op.drop_index("idx_session_tasks_task_id", table_name="session_tasks", if_exists=True)
    op.drop_table("session_tasks", if_exists=True)

    op.drop_index("idx_study_sessions_heartbeat", table_name="study_sessions", if_exists=True)
    op.drop_index(
        "idx_study_sessions_roadmap_started",
        table_name="study_sessions",
        if_exists=True,
    )
    op.drop_index("idx_study_sessions_user_started", table_name="study_sessions", if_exists=True)
    op.drop_index("uq_study_sessions_user_active", table_name="study_sessions", if_exists=True)
    op.drop_table("study_sessions", if_exists=True)

    op.drop_index("idx_task_deps_roadmap", table_name="task_dependencies", if_exists=True)
    op.drop_index("idx_task_deps_predecessor", table_name="task_dependencies", if_exists=True)
    op.drop_index("idx_task_deps_successor", table_name="task_dependencies", if_exists=True)
    op.drop_table("task_dependencies", if_exists=True)

    op.drop_index("idx_tasks_official_schedule_id", table_name="tasks", if_exists=True)
    op.drop_index("idx_tasks_milestone_id", table_name="tasks", if_exists=True)
    op.drop_index("idx_tasks_overdue", table_name="tasks", if_exists=True)
    op.drop_index("idx_tasks_scheduled_start", table_name="tasks", if_exists=True)
    op.drop_index("idx_tasks_roadmap_scheduled_date", table_name="tasks", if_exists=True)
    op.drop_table("tasks", if_exists=True)

    # Planning (5 tables in reverse dependency order)
    op.drop_index(
        "idx_schedule_proposals_user_id",
        table_name="schedule_proposals",
        if_exists=True,
    )
    op.drop_index(
        "idx_schedule_proposals_roadmap_status",
        table_name="schedule_proposals",
        if_exists=True,
    )
    op.drop_index(
        "uq_schedule_proposals_roadmap_draft",
        table_name="schedule_proposals",
        if_exists=True,
    )
    op.drop_table("schedule_proposals", if_exists=True)

    op.drop_table("official_schedules", if_exists=True)
    op.drop_table("milestones", if_exists=True)

    op.drop_index("idx_roadmaps_goal_id", table_name="roadmaps", if_exists=True)
    op.drop_index("idx_roadmaps_user_status", table_name="roadmaps", if_exists=True)
    op.drop_table("roadmaps", if_exists=True)

    op.drop_index("idx_goals_user_id", table_name="goals", if_exists=True)
    op.drop_table("goals", if_exists=True)

    # Account (5 tables)
    op.drop_index(
        "idx_payment_transactions_status",
        table_name="payment_transactions",
        if_exists=True,
    )
    op.drop_index(
        "idx_payment_transactions_user_created",
        table_name="payment_transactions",
        if_exists=True,
    )
    op.drop_table("payment_transactions", if_exists=True)

    op.drop_index(
        "idx_ai_usage_logs_user_action",
        table_name="ai_usage_logs",
        if_exists=True,
    )
    op.drop_table("ai_usage_logs", if_exists=True)

    op.drop_index(
        "idx_quota_reservations_user_status",
        table_name="ai_quota_reservations",
        if_exists=True,
    )
    op.drop_index(
        "idx_quota_reservations_cleanup",
        table_name="ai_quota_reservations",
        if_exists=True,
    )
    op.drop_table("ai_quota_reservations", if_exists=True)

    op.drop_table("webcal_tokens", if_exists=True)
    op.drop_table("learner_profiles", if_exists=True)
