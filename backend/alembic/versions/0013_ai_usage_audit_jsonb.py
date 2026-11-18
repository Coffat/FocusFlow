"""Add idempotency_key and JSONB audit_metadata to ai_usage_logs without adding tables.

Revision ID: 0013_ai_usage_audit_jsonb
Revises: 0012_adaptive_roadmap_quality
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0013_ai_usage_audit_jsonb"
down_revision: str | None = "0012_adaptive_roadmap_quality"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ai_usage_logs",
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "ai_usage_logs",
        sa.Column(
            "audit_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.create_index(
        "uq_ai_usage_logs_idempotency_key",
        "ai_usage_logs",
        ["idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_ai_usage_logs_idempotency_key", table_name="ai_usage_logs")
    op.drop_column("ai_usage_logs", "audit_metadata")
    op.drop_column("ai_usage_logs", "idempotency_key")
