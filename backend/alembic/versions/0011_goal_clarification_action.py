"""Track goal clarification as a dedicated AI usage action.

Revision ID: 0011_goal_clarification_action
Revises: 0010_learner_intelligence
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0011_goal_clarification_action"
down_revision: str | None = "0010_learner_intelligence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_BASE_ACTIONS = (
    "'ROADMAP_GENERATION', 'SCHEDULE_PROPOSAL', 'AI_REVIEW_WEEKLY', "
    "'AI_REVIEW_MILESTONE', 'MILESTONE_BREAKDOWN', 'CHAT_ASSISTANT', "
    "'KNOWLEDGE_INGESTION', 'WHAT_IF_SIMULATION', 'OVERDUE_RECOVERY', "
    "'CONTINUOUS_LEARNING'"
)


def upgrade() -> None:
    op.drop_constraint("chk_ai_usage_logs_action", "ai_usage_logs", type_="check")
    op.create_check_constraint(
        "chk_ai_usage_logs_action",
        "ai_usage_logs",
        f"action_type IN ({_BASE_ACTIONS}, 'GOAL_CLARIFICATION')",
    )


def downgrade() -> None:
    op.execute(
        "UPDATE ai_usage_logs SET action_type = 'ROADMAP_GENERATION' "
        "WHERE action_type = 'GOAL_CLARIFICATION'"
    )
    op.drop_constraint("chk_ai_usage_logs_action", "ai_usage_logs", type_="check")
    op.create_check_constraint(
        "chk_ai_usage_logs_action",
        "ai_usage_logs",
        f"action_type IN ({_BASE_ACTIONS})",
    )
