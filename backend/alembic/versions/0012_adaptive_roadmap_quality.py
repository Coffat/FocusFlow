"""Persist adaptive roadmap quality inputs without adding tables.

Revision ID: 0012_adaptive_roadmap_quality
Revises: 0011_goal_clarification_action
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0012_adaptive_roadmap_quality"
down_revision: str | None = "0011_goal_clarification_action"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "roadmaps",
        sa.Column(
            "planning_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "milestones",
        sa.Column(
            "learning_outcomes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column("milestones", sa.Column("completion_criteria", sa.Text(), nullable=True))
    op.add_column(
        "milestones",
        sa.Column("estimated_effort_minutes", sa.Integer(), nullable=False, server_default="60"),
    )
    op.add_column(
        "milestones",
        sa.Column(
            "required_concepts",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "milestones",
        sa.Column(
            "unverified_concepts",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "milestones",
        sa.Column(
            "prerequisite_milestone_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("milestones", "prerequisite_milestone_ids")
    op.drop_column("milestones", "unverified_concepts")
    op.drop_column("milestones", "required_concepts")
    op.drop_column("milestones", "estimated_effort_minutes")
    op.drop_column("milestones", "completion_criteria")
    op.drop_column("milestones", "learning_outcomes")
    op.drop_column("roadmaps", "planning_metadata")
