"""Add scheduling resilience, check-in and weekly intelligence columns.

Revision ID: 0009_learning_intel
Revises: 0008_knowledge_rag
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0009_learning_intel"
down_revision: str | None = "0008_knowledge_rag"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "availability_slots",
        sa.Column("energy_level", sa.String(10), nullable=False, server_default="MEDIUM"),
    )
    op.create_check_constraint(
        "chk_avail_slots_energy", "availability_slots", "energy_level IN ('LOW', 'MEDIUM', 'HIGH')"
    )

    op.add_column(
        "roadmaps",
        sa.Column("weekly_reschedule_budget", sa.SmallInteger, nullable=False, server_default="3"),
    )
    op.add_column(
        "roadmaps",
        sa.Column("weekly_reschedule_used", sa.SmallInteger, nullable=False, server_default="0"),
    )
    op.add_column("roadmaps", sa.Column("budget_week_start", sa.Date, nullable=True))
    op.add_column(
        "roadmaps", sa.Column("last_study_activity_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "roadmaps", sa.Column("reset_ritual_count", sa.Integer, nullable=False, server_default="0")
    )
    op.create_check_constraint(
        "chk_roadmaps_weekly_budget",
        "roadmaps",
        "weekly_reschedule_budget >= 0 AND weekly_reschedule_used >= 0",
    )
    op.create_check_constraint("chk_roadmaps_reset_count", "roadmaps", "reset_ritual_count >= 0")

    op.add_column(
        "milestones",
        sa.Column("proof_status", sa.String(20), nullable=False, server_default="UNVERIFIED"),
    )
    op.create_check_constraint(
        "chk_milestones_proof_status",
        "milestones",
        "proof_status IN ('UNVERIFIED', 'PENDING_REVIEW', 'PROVEN', 'NEEDS_REVIEW')",
    )

    op.add_column(
        "official_schedules",
        sa.Column("buffer_minutes_per_week", sa.Integer, nullable=False, server_default="60"),
    )
    op.add_column(
        "official_schedules",
        sa.Column("recovery_window_days", sa.SmallInteger, nullable=False, server_default="7"),
    )
    op.add_column(
        "official_schedules",
        sa.Column("daily_workload_cap_minutes", sa.Integer, nullable=False, server_default="180"),
    )
    op.add_column(
        "official_schedules",
        sa.Column("stability_weight", sa.Numeric(4, 3), nullable=False, server_default="0.800"),
    )
    op.create_check_constraint(
        "chk_official_schedules_resilience",
        "official_schedules",
        "buffer_minutes_per_week >= 0 AND recovery_window_days BETWEEN 7 AND 14 AND daily_workload_cap_minutes BETWEEN 30 AND 840 AND stability_weight BETWEEN 0 AND 1",
    )

    op.add_column(
        "schedule_proposals",
        sa.Column(
            "proposal_type", sa.String(35), nullable=False, server_default="INITIAL_SCHEDULE"
        ),
    )
    op.add_column(
        "schedule_proposals",
        sa.Column(
            "original_proposal_data",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "schedule_proposals",
        sa.Column("user_edit_count", sa.Integer, nullable=False, server_default="0"),
    )
    op.add_column(
        "schedule_proposals",
        sa.Column(
            "pedagogical_warnings",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.create_check_constraint(
        "chk_schedule_proposals_type",
        "schedule_proposals",
        "proposal_type IN ('INITIAL_SCHEDULE', 'AI_RECOVERY', 'POST_FAILURE_RESET', 'SCHEDULE_ONLY_REOPTIMIZE', 'WHAT_IF_SIMULATION')",
    )
    op.create_check_constraint(
        "chk_schedule_proposals_original",
        "schedule_proposals",
        "jsonb_typeof(original_proposal_data) = 'object'",
    )
    op.create_check_constraint(
        "chk_schedule_proposals_warnings",
        "schedule_proposals",
        "jsonb_typeof(pedagogical_warnings) = 'array'",
    )
    op.create_check_constraint(
        "chk_schedule_proposals_edit_count", "schedule_proposals", "user_edit_count >= 0"
    )

    op.add_column(
        "tasks", sa.Column("parent_task_id", postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.add_column("tasks", sa.Column("concept_id", sa.String(120), nullable=True))
    op.add_column(
        "tasks",
        sa.Column(
            "learning_resources_json",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.create_foreign_key(
        "fk_tasks_parent", "tasks", "tasks", ["parent_task_id"], ["id"], ondelete="SET NULL"
    )
    op.create_foreign_key(
        "fk_tasks_concept",
        "tasks",
        "learning_concepts",
        ["concept_id"],
        ["concept_id"],
        ondelete="SET NULL",
    )
    op.create_check_constraint(
        "chk_tasks_resources_json", "tasks", "jsonb_typeof(learning_resources_json) = 'array'"
    )
    op.create_index("idx_tasks_parent_id", "tasks", ["parent_task_id"])
    op.create_index("idx_tasks_concept_id", "tasks", ["concept_id"])

    op.add_column(
        "study_sessions",
        sa.Column("session_mode", sa.String(15), nullable=False, server_default="STANDARD"),
    )
    op.add_column(
        "study_sessions",
        sa.Column("pending_takeaway", sa.Boolean, nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "study_sessions", sa.Column("checkin_time_sufficiency", sa.String(15), nullable=True)
    )
    op.add_column(
        "study_sessions", sa.Column("checkin_perceived_difficulty", sa.SmallInteger, nullable=True)
    )
    op.add_column(
        "study_sessions", sa.Column("checkin_focus_level", sa.SmallInteger, nullable=True)
    )
    op.create_check_constraint(
        "chk_study_sessions_mode", "study_sessions", "session_mode IN ('STANDARD', 'MVS')"
    )
    op.create_check_constraint(
        "chk_study_sessions_checkin_time",
        "study_sessions",
        "checkin_time_sufficiency IS NULL OR checkin_time_sufficiency IN ('TOO_SHORT', 'JUST_RIGHT', 'TOO_LONG')",
    )
    op.create_check_constraint(
        "chk_study_sessions_checkin_scores",
        "study_sessions",
        "(checkin_perceived_difficulty IS NULL OR checkin_perceived_difficulty BETWEEN 1 AND 5) AND (checkin_focus_level IS NULL OR checkin_focus_level BETWEEN 1 AND 5)",
    )

    op.add_column("study_notes", sa.Column("self_confidence", sa.SmallInteger, nullable=True))
    op.add_column("study_notes", sa.Column("ai_evidence_score", sa.Numeric(4, 2), nullable=True))
    op.add_column(
        "study_notes",
        sa.Column("alignment_flag", sa.String(20), nullable=False, server_default="UNCHECKED"),
    )
    op.add_column(
        "study_notes",
        sa.Column(
            "verification_status", sa.String(25), nullable=False, server_default="PENDING_PROVE"
        ),
    )
    op.create_check_constraint(
        "chk_study_notes_confidence",
        "study_notes",
        "self_confidence IS NULL OR self_confidence BETWEEN 1 AND 5",
    )
    op.create_check_constraint(
        "chk_study_notes_evidence",
        "study_notes",
        "ai_evidence_score IS NULL OR ai_evidence_score BETWEEN 1 AND 5",
    )
    op.create_check_constraint(
        "chk_study_notes_alignment",
        "study_notes",
        "alignment_flag IN ('UNCHECKED', 'ALIGNED', 'SUPERFICIAL', 'OFF_TOPIC', 'CONTRADICTORY')",
    )
    op.create_check_constraint(
        "chk_study_notes_verification",
        "study_notes",
        "verification_status IN ('PENDING_PROVE', 'VERIFIED', 'FLAGGED_SHALLOW', 'NEEDS_REVIEW')",
    )

    op.add_column(
        "ai_reviews",
        sa.Column(
            "user_reflection_payload",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.create_check_constraint(
        "chk_ai_reviews_reflection",
        "ai_reviews",
        "jsonb_typeof(user_reflection_payload) = 'object'",
    )

    op.add_column(
        "schedule_change_logs", sa.Column("disruption_category", sa.String(40), nullable=True)
    )
    op.add_column(
        "schedule_change_logs",
        sa.Column("counts_toward_budget", sa.Boolean, nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column("schedule_change_logs", "counts_toward_budget")
    op.drop_column("schedule_change_logs", "disruption_category")
    op.drop_constraint("chk_ai_reviews_reflection", "ai_reviews", type_="check")
    op.drop_column("ai_reviews", "user_reflection_payload")
    for name in (
        "chk_study_notes_verification",
        "chk_study_notes_alignment",
        "chk_study_notes_evidence",
        "chk_study_notes_confidence",
    ):
        op.drop_constraint(name, "study_notes", type_="check")
    for column in ("verification_status", "alignment_flag", "ai_evidence_score", "self_confidence"):
        op.drop_column("study_notes", column)
    for name in (
        "chk_study_sessions_checkin_scores",
        "chk_study_sessions_checkin_time",
        "chk_study_sessions_mode",
    ):
        op.drop_constraint(name, "study_sessions", type_="check")
    for column in (
        "checkin_focus_level",
        "checkin_perceived_difficulty",
        "checkin_time_sufficiency",
        "pending_takeaway",
        "session_mode",
    ):
        op.drop_column("study_sessions", column)
    op.drop_index("idx_tasks_concept_id", table_name="tasks")
    op.drop_index("idx_tasks_parent_id", table_name="tasks")
    op.drop_constraint("chk_tasks_resources_json", "tasks", type_="check")
    op.drop_constraint("fk_tasks_concept", "tasks", type_="foreignkey")
    op.drop_constraint("fk_tasks_parent", "tasks", type_="foreignkey")
    for column in ("learning_resources_json", "concept_id", "parent_task_id"):
        op.drop_column("tasks", column)
    for name in (
        "chk_schedule_proposals_edit_count",
        "chk_schedule_proposals_warnings",
        "chk_schedule_proposals_original",
        "chk_schedule_proposals_type",
    ):
        op.drop_constraint(name, "schedule_proposals", type_="check")
    for column in (
        "pedagogical_warnings",
        "user_edit_count",
        "original_proposal_data",
        "proposal_type",
    ):
        op.drop_column("schedule_proposals", column)
    op.drop_constraint("chk_official_schedules_resilience", "official_schedules", type_="check")
    for column in (
        "stability_weight",
        "daily_workload_cap_minutes",
        "recovery_window_days",
        "buffer_minutes_per_week",
    ):
        op.drop_column("official_schedules", column)
    op.drop_constraint("chk_milestones_proof_status", "milestones", type_="check")
    op.drop_column("milestones", "proof_status")
    op.drop_constraint("chk_roadmaps_reset_count", "roadmaps", type_="check")
    op.drop_constraint("chk_roadmaps_weekly_budget", "roadmaps", type_="check")
    for column in (
        "reset_ritual_count",
        "last_study_activity_at",
        "budget_week_start",
        "weekly_reschedule_used",
        "weekly_reschedule_budget",
    ):
        op.drop_column("roadmaps", column)
    op.drop_constraint("chk_avail_slots_energy", "availability_slots", type_="check")
    op.drop_column("availability_slots", "energy_level")
