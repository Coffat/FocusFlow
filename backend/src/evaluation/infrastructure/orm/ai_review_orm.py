import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from uuid6 import uuid7

from src.shared_kernel.infrastructure.database.session import Base


class AIReviewORM(Base):
    __tablename__ = "ai_reviews"
    __table_args__ = (
        CheckConstraint("review_cycle IN ('WEEKLY', 'MILESTONE')", name="chk_ai_reviews_cycle"),
        Index("idx_ai_reviews_user_id", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    roadmap_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roadmaps.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    milestone_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("milestones.id", ondelete="CASCADE")
    )
    review_cycle: Mapped[str] = mapped_column(String(20), nullable=False)
    period_start: Mapped[date | None] = mapped_column(Date)
    period_end: Mapped[date | None] = mapped_column(Date)
    quantitative_summary: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    strengths_feedback: Mapped[str] = mapped_column(Text, nullable=False)
    bottlenecks_feedback: Mapped[str] = mapped_column(Text, nullable=False)
    action_recommendations: Mapped[str] = mapped_column(Text, nullable=False)
    user_reflection_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    model_used: Mapped[str] = mapped_column(
        String(100), nullable=False, default="mock-deterministic"
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
