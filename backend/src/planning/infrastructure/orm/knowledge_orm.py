from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    CheckConstraint,
    Computed,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.shared_kernel.infrastructure.database.session import Base


class KnowledgeSourceORM(Base):
    __tablename__ = "knowledge_sources"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "goal_id", "content_hash", name="uq_knowledge_sources_owner_hash"
        ),
        CheckConstraint(
            "source_type IN ('PDF', 'DOCX', 'TXT', 'URL')", name="chk_knowledge_sources_type"
        ),
        CheckConstraint(
            "ingestion_status IN ('PENDING', 'PROCESSING', 'INDEXED', 'FAILED', 'QUARANTINED')",
            name="chk_knowledge_sources_status",
        ),
        CheckConstraint("content_hash ~ '^[0-9a-f]{64}$'", name="chk_knowledge_sources_hash"),
        CheckConstraint("chunk_count >= 0", name="chk_knowledge_sources_chunks"),
        CheckConstraint(
            "jsonb_typeof(provenance_metadata) = 'object'",
            name="chk_knowledge_sources_provenance",
        ),
        Index("idx_knowledge_sources_goal_status", "goal_id", "ingestion_status"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    goal_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("goals.id", ondelete="CASCADE"), nullable=False
    )
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    source_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    ingestion_status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    provenance_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )


class KnowledgeChunkORM(Base):
    __tablename__ = "knowledge_chunks"
    __table_args__ = (
        UniqueConstraint("source_id", "chunk_index", name="uq_knowledge_chunks_source_idx"),
        CheckConstraint("chunk_index >= 0", name="chk_knowledge_chunks_index"),
        CheckConstraint(
            "page_number IS NULL OR page_number >= 1", name="chk_knowledge_chunks_page"
        ),
        CheckConstraint("token_count > 0", name="chk_knowledge_chunks_tokens"),
        CheckConstraint(
            "jsonb_typeof(provenance_json) = 'object'", name="chk_knowledge_chunks_provenance"
        ),
        Index("idx_knowledge_chunks_goal_id", "goal_id"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    source_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("knowledge_sources.id", ondelete="CASCADE"),
        nullable=False,
    )
    goal_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("goals.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    section_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    search_vector: Mapped[Any] = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('simple', content)", persisted=True),
        nullable=False,
    )
    embedding: Mapped[list[float] | None] = mapped_column(Vector(768), nullable=True)
    provenance_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
