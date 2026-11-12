"""Add learner memory, concept mastery, and milestone proof tables.

Revision ID: 0010_learner_intelligence
Revises: 0009_learning_intel
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0010_learner_intelligence"
down_revision: str | None = "0009_learning_intel"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "learner_memory_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("memory_key", sa.String(160), nullable=False),
        sa.Column("value", postgresql.JSONB(), nullable=False),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("epistemic_level", sa.String(20), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("evidence", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("observation_started_at", sa.DateTime(timezone=True)),
        sa.Column("observation_ended_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("user_id", "memory_key", name="uq_learner_memory_user_key"),
        sa.CheckConstraint(
            "epistemic_level IN ('EXPLICIT', 'OBSERVED', 'INFERRED')",
            name="chk_learner_memory_epistemic",
        ),
        sa.CheckConstraint(
            "status IN ('PENDING', 'CONFIRMED', 'REJECTED')", name="chk_learner_memory_status"
        ),
        sa.CheckConstraint("confidence BETWEEN 0 AND 1", name="chk_learner_memory_confidence"),
        sa.CheckConstraint("sample_size >= 0", name="chk_learner_memory_sample_size"),
    )
    op.create_index(
        "idx_learner_memory_context", "learner_memory_items", ["user_id", "status", "category"]
    )

    op.create_table(
        "learner_concept_masteries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("concept_key", sa.String(160), nullable=False),
        sa.Column("mastery_score", sa.Numeric(5, 4), nullable=False),
        sa.Column("evidence_count", sa.Integer(), nullable=False),
        sa.Column("last_evidence_type", sa.String(40), nullable=False),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("user_id", "concept_key", name="uq_learner_mastery_user_concept"),
        sa.CheckConstraint("mastery_score BETWEEN 0 AND 1", name="chk_learner_mastery_score"),
        sa.CheckConstraint("evidence_count > 0", name="chk_learner_mastery_evidence"),
    )

    op.create_table(
        "milestone_proofs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "milestone_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("milestones.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(24), nullable=False, server_default="DRAFT"),
        sa.Column("questions", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("answers", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("score", sa.Integer()),
        sa.Column("confidence", sa.Numeric(5, 4)),
        sa.Column("corrective_action", sa.Text()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("submitted_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'READY', 'SUBMITTED', 'PASSED', 'NEEDS_REVIEW')",
            name="chk_milestone_proofs_status",
        ),
        sa.CheckConstraint(
            "confidence IS NULL OR confidence BETWEEN 0 AND 1",
            name="chk_milestone_proofs_confidence",
        ),
    )
    op.create_index("idx_milestone_proofs_owner", "milestone_proofs", ["user_id", "milestone_id"])


def downgrade() -> None:
    op.drop_index("idx_milestone_proofs_owner", table_name="milestone_proofs")
    op.drop_table("milestone_proofs")
    op.drop_table("learner_concept_masteries")
    op.drop_index("idx_learner_memory_context", table_name="learner_memory_items")
    op.drop_table("learner_memory_items")
