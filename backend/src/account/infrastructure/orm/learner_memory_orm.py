import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from uuid6 import uuid7

from src.shared_kernel.infrastructure.database.session import Base


class LearnerMemoryItemORM(Base):
    __tablename__ = "learner_memory_items"
    __table_args__ = (
        UniqueConstraint("user_id", "memory_key", name="uq_learner_memory_user_key"),
        CheckConstraint(
            "epistemic_level IN ('EXPLICIT', 'OBSERVED', 'INFERRED')",
            name="chk_learner_memory_epistemic",
        ),
        CheckConstraint(
            "status IN ('PENDING', 'CONFIRMED', 'REJECTED')",
            name="chk_learner_memory_status",
        ),
        CheckConstraint("confidence BETWEEN 0 AND 1", name="chk_learner_memory_confidence"),
        CheckConstraint("sample_size >= 0", name="chk_learner_memory_sample_size"),
        Index("idx_learner_memory_context", "user_id", "status", "category"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    memory_key: Mapped[str] = mapped_column(String(160), nullable=False)
    value: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    epistemic_level: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    evidence: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    observation_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    observation_ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )


class LearnerConceptMasteryORM(Base):
    __tablename__ = "learner_concept_masteries"
    __table_args__ = (
        UniqueConstraint("user_id", "concept_key", name="uq_learner_mastery_user_concept"),
        CheckConstraint("mastery_score BETWEEN 0 AND 1", name="chk_learner_mastery_score"),
        CheckConstraint("evidence_count > 0", name="chk_learner_mastery_evidence"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    concept_key: Mapped[str] = mapped_column(String(160), nullable=False)
    mastery_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    evidence_count: Mapped[int] = mapped_column(Integer, nullable=False)
    last_evidence_type: Mapped[str] = mapped_column(String(40), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
