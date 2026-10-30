import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.shared_kernel.infrastructure.database.session import Base


class UserORM(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        CheckConstraint("role IN ('LEARNER', 'ADMIN')", name="chk_users_role"),
        CheckConstraint("tier IN ('FREE', 'PREMIUM')", name="chk_users_tier"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, default="Asia/Ho_Chi_Minh")
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="LEARNER")
    tier: Mapped[str] = mapped_column(String(20), nullable=False, default="FREE")
    is_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class AIQuotaORM(Base):
    __tablename__ = "ai_quotas"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_ai_quotas_user_id"),
        CheckConstraint("monthly_limit > 0", name="chk_ai_quotas_monthly_limit"),
        CheckConstraint("used_calls >= 0", name="chk_ai_quotas_used_calls"),
        CheckConstraint("reserved_calls >= 0", name="chk_ai_quotas_reserved_calls"),
        CheckConstraint("tokens_consumed >= 0", name="chk_ai_quotas_tokens"),
        CheckConstraint("used_calls + reserved_calls <= monthly_limit", name="chk_ai_quotas_limit"),
        CheckConstraint("cycle_end > cycle_start", name="chk_ai_quotas_cycle"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    monthly_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    used_calls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reserved_calls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_consumed: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    cycle_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cycle_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
