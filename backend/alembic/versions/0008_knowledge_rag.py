"""Add secure knowledge ingestion and hybrid RAG tables.

Revision ID: 0008_knowledge_rag
Revises: 0007_ai_harness_workflows
"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0008_knowledge_rag"
down_revision: str | None = "0007_ai_harness_workflows"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "knowledge_sources",
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
            nullable=False,
        ),
        sa.Column("source_type", sa.String(20), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("source_uri", sa.Text, nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("ingestion_status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("chunk_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "provenance_metadata",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("error_detail", sa.Text, nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint(
            "user_id", "goal_id", "content_hash", name="uq_knowledge_sources_owner_hash"
        ),
        sa.CheckConstraint(
            "source_type IN ('PDF', 'DOCX', 'TXT', 'URL')", name="chk_knowledge_sources_type"
        ),
        sa.CheckConstraint("content_hash ~ '^[0-9a-f]{64}$'", name="chk_knowledge_sources_hash"),
        sa.CheckConstraint(
            "ingestion_status IN ('PENDING', 'PROCESSING', 'INDEXED', 'FAILED', 'QUARANTINED')",
            name="chk_knowledge_sources_status",
        ),
        sa.CheckConstraint("chunk_count >= 0", name="chk_knowledge_sources_chunks"),
        sa.CheckConstraint(
            "jsonb_typeof(provenance_metadata) = 'object'", name="chk_knowledge_sources_provenance"
        ),
    )
    op.create_index(
        "idx_knowledge_sources_goal_status", "knowledge_sources", ["goal_id", "ingestion_status"]
    )

    op.create_table(
        "knowledge_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("knowledge_sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "goal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("goals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("section_title", sa.String(255), nullable=True),
        sa.Column("page_number", sa.Integer, nullable=True),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("token_count", sa.Integer, nullable=False),
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR,
            sa.Computed("to_tsvector('simple', content)", persisted=True),
            nullable=False,
        ),
        sa.Column("embedding", Vector(768), nullable=True),
        sa.Column(
            "provenance_json",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("source_id", "chunk_index", name="uq_knowledge_chunks_source_idx"),
        sa.CheckConstraint("chunk_index >= 0", name="chk_knowledge_chunks_index"),
        sa.CheckConstraint(
            "page_number IS NULL OR page_number >= 1", name="chk_knowledge_chunks_page"
        ),
        sa.CheckConstraint("token_count > 0", name="chk_knowledge_chunks_tokens"),
        sa.CheckConstraint(
            "jsonb_typeof(provenance_json) = 'object'", name="chk_knowledge_chunks_provenance"
        ),
    )
    op.create_index("idx_knowledge_chunks_goal_id", "knowledge_chunks", ["goal_id"])
    op.execute(
        "CREATE INDEX idx_knowledge_chunks_search_vector ON knowledge_chunks USING GIN (search_vector)"
    )
    op.execute(
        "CREATE INDEX idx_knowledge_chunks_embedding_hnsw ON knowledge_chunks USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.drop_table("knowledge_chunks")
    op.drop_table("knowledge_sources")
