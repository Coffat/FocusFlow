"""Add learning_concepts and concept_prerequisites tables with VERIFIED seed data

Revision ID: 0004_knowledge_base_tables
Revises: 0003_goal_clarification
Create Date: 2026-04-20 09:00:00.000000
"""

import json
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from src.planning.infrastructure.repositories.sqlalchemy_knowledge_base_repository import (
    VERIFIED_SEED_CONCEPTS,
    VERIFIED_SEED_EDGES,
)

# revision identifiers, used by Alembic.
revision: str = "0004_knowledge_base_tables"
down_revision: str | None = "0003_goal_clarification"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "learning_concepts",
        sa.Column("concept_id", sa.String(length=120), primary_key=True, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("domain", sa.String(length=100), nullable=False),
        sa.Column(
            "difficulty_level",
            sa.String(length=50),
            nullable=False,
            server_default="BEGINNER",
        ),
        sa.Column(
            "estimated_effort_minutes",
            sa.Integer(),
            nullable=False,
            server_default="60",
        ),
        sa.Column(
            "keywords",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "learning_outcomes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "verification_status",
            sa.String(length=30),
            nullable=False,
            server_default="VERIFIED",
        ),
        sa.Column(
            "version",
            sa.String(length=20),
            nullable=False,
            server_default="1.0.0",
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
            "verification_status IN ('VERIFIED', 'UNVERIFIED', 'DEPRECATED')",
            name="chk_learning_concepts_verification_status",
        ),
        sa.CheckConstraint(
            "estimated_effort_minutes > 0",
            name="chk_learning_concepts_effort_positive",
        ),
    )
    op.create_index(
        "idx_learning_concepts_domain_level",
        "learning_concepts",
        ["domain", "difficulty_level", "verification_status"],
    )

    op.create_table(
        "concept_prerequisites",
        sa.Column(
            "source_concept_id",
            sa.String(length=120),
            sa.ForeignKey(
                "learning_concepts.concept_id",
                ondelete="CASCADE",
                name="fk_concept_prerequisites_source",
            ),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "prerequisite_concept_id",
            sa.String(length=120),
            sa.ForeignKey(
                "learning_concepts.concept_id",
                ondelete="CASCADE",
                name="fk_concept_prerequisites_prereq",
            ),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "relation_type",
            sa.String(length=30),
            nullable=False,
            server_default="REQUIRES",
        ),
        sa.Column(
            "rationale",
            sa.Text(),
            nullable=False,
            server_default="",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint(
            "relation_type IN ('REQUIRES', 'RECOMMENDED_BEFORE')",
            name="chk_concept_prerequisites_relation_type",
        ),
        sa.CheckConstraint(
            "source_concept_id <> prerequisite_concept_id",
            name="chk_concept_prerequisites_no_self_loop",
        ),
    )
    op.create_index(
        "idx_concept_prerequisites_source",
        "concept_prerequisites",
        ["source_concept_id"],
    )
    op.create_index(
        "idx_concept_prerequisites_prereq",
        "concept_prerequisites",
        ["prerequisite_concept_id"],
    )

    concepts_table = sa.table(
        "learning_concepts",
        sa.column("concept_id", sa.String),
        sa.column("title", sa.String),
        sa.column("summary", sa.Text),
        sa.column("domain", sa.String),
        sa.column("difficulty_level", sa.String),
        sa.column("estimated_effort_minutes", sa.Integer),
        sa.column("keywords", postgresql.JSONB),
        sa.column("learning_outcomes", postgresql.JSONB),
        sa.column("verification_status", sa.String),
        sa.column("version", sa.String),
    )
    op.bulk_insert(
        concepts_table,
        [
            {
                "concept_id": c.concept_id,
                "title": c.title,
                "summary": c.summary,
                "domain": c.domain,
                "difficulty_level": c.difficulty_level,
                "estimated_effort_minutes": c.estimated_effort_minutes,
                "keywords": json.loads(json.dumps(list(c.keywords), ensure_ascii=False)),
                "learning_outcomes": json.loads(
                    json.dumps(list(c.learning_outcomes), ensure_ascii=False)
                ),
                "verification_status": c.verification_status.value,
                "version": str(c.version),
            }
            for c in VERIFIED_SEED_CONCEPTS
        ],
    )

    edges_table = sa.table(
        "concept_prerequisites",
        sa.column("source_concept_id", sa.String),
        sa.column("prerequisite_concept_id", sa.String),
        sa.column("relation_type", sa.String),
        sa.column("rationale", sa.Text),
    )
    op.bulk_insert(
        edges_table,
        [
            {
                "source_concept_id": e.source_concept_id,
                "prerequisite_concept_id": e.prerequisite_concept_id,
                "relation_type": e.relation_type.value,
                "rationale": e.rationale,
            }
            for e in VERIFIED_SEED_EDGES
        ],
    )


def downgrade() -> None:
    op.drop_index("idx_concept_prerequisites_prereq", table_name="concept_prerequisites")
    op.drop_index("idx_concept_prerequisites_source", table_name="concept_prerequisites")
    op.drop_table("concept_prerequisites")
    op.drop_index("idx_learning_concepts_domain_level", table_name="learning_concepts")
    op.drop_table("learning_concepts")
