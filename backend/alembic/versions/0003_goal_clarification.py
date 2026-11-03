"""Add prior_knowledge_level and clarification_context to goals table

Revision ID: 0003_goal_clarification
Revises: 0002_complete_24_tables
Create Date: 2026-11-02 16:15:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_goal_clarification"
down_revision: str | None = "0002_complete_24_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "goals",
        sa.Column(
            "prior_knowledge_level",
            sa.String(50),
            nullable=False,
            server_default="BEGINNER",
        ),
    )
    op.add_column(
        "goals",
        sa.Column(
            "clarification_context",
            sa.Text(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("goals", "clarification_context")
    op.drop_column("goals", "prior_knowledge_level")
