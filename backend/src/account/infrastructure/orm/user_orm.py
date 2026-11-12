import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, ClassVar

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from uuid6 import uuid7

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
        default=uuid7,
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

    # Class-level ledger to preserve free vs paid credit breakdown across sessions
    _credit_ledger_by_user: ClassVar[dict[uuid.UUID, tuple[int, int]]] = {}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid7,
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
    cycle_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    cycle_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC) + timedelta(days=30),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    def __init__(self, **kwargs: Any) -> None:
        free_credits = kwargs.pop("free_credits_remaining", None)
        paid_credits = kwargs.pop("paid_credits_remaining", None)
        now = datetime.now(UTC)
        kwargs.setdefault("id", uuid7())
        kwargs.setdefault("used_calls", 0)
        kwargs.setdefault("reserved_calls", 0)
        kwargs.setdefault("tokens_consumed", 0)
        kwargs.setdefault("cycle_start", now)
        kwargs.setdefault("cycle_end", now + timedelta(days=30))

        if free_credits is not None or paid_credits is not None:
            fc = int(free_credits if free_credits is not None else 3)
            pc = int(paid_credits if paid_credits is not None else 0)
            used = int(kwargs.get("used_calls", 0) or 0)
            reserved = int(kwargs.get("reserved_calls", 0) or 0)
            kwargs["monthly_limit"] = max(1, used + reserved + fc + pc)
            super().__init__(**kwargs)
            self._set_credit_pool(fc, pc)
        else:
            kwargs.setdefault("monthly_limit", 30)
            super().__init__(**kwargs)

    def _get_credit_pool(self) -> tuple[int, int]:
        fc_attr = self.__dict__.get("_free_credits_remaining")
        pc_attr = self.__dict__.get("_paid_credits_remaining")
        if fc_attr is not None and pc_attr is not None:
            return int(fc_attr), int(pc_attr)
        if self.user_id and self.user_id in self._credit_ledger_by_user:
            fc, pc = self._credit_ledger_by_user[self.user_id]
            self.__dict__["_free_credits_remaining"] = fc
            self.__dict__["_paid_credits_remaining"] = pc
            return fc, pc
        remaining_total = max(
            0,
            (self.monthly_limit or 0) - (self.used_calls or 0) - (self.reserved_calls or 0),
        )
        return remaining_total, 0

    def _set_credit_pool(self, free_credits: int, paid_credits: int) -> None:
        fc = max(0, int(free_credits))
        pc = max(0, int(paid_credits))
        self.__dict__["_free_credits_remaining"] = fc
        self.__dict__["_paid_credits_remaining"] = pc
        if self.user_id is not None:
            self._credit_ledger_by_user[self.user_id] = (fc, pc)
        used = int(self.used_calls or 0)
        reserved = int(self.reserved_calls or 0)
        self.monthly_limit = max(1, used + reserved + fc + pc)

    @property
    def free_credits_remaining(self) -> int:
        fc, _ = self._get_credit_pool()
        return fc

    @free_credits_remaining.setter
    def free_credits_remaining(self, value: int) -> None:
        _, pc = self._get_credit_pool()
        self._set_credit_pool(value, pc)

    @property
    def paid_credits_remaining(self) -> int:
        _, pc = self._get_credit_pool()
        return pc

    @paid_credits_remaining.setter
    def paid_credits_remaining(self, value: int) -> None:
        fc, _ = self._get_credit_pool()
        self._set_credit_pool(fc, value)


class AIQuotaReservationORM(Base):
    """2-Phase ACID AI Quota Reservation table (`ai_quota_reservations`)."""

    __tablename__ = "ai_quota_reservations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('RESERVED', 'COMMITTED', 'RELEASED', 'EXPIRED')",
            name="chk_ai_quota_res_status",
        ),
        CheckConstraint("tokens_reserved >= 0", name="chk_ai_quota_res_tokens"),
        CheckConstraint(
            "(status = 'RESERVED' AND resolved_at IS NULL) OR (status != 'RESERVED' AND resolved_at IS NOT NULL)",
            name="chk_ai_quota_res_resolved",
        ),
        Index(
            "idx_quota_reservations_cleanup",
            "expires_at",
            postgresql_where="status = 'RESERVED'",
        ),
        Index("idx_quota_reservations_user_status", "user_id", "status", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid7,
    )
    quota_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_quotas.id", ondelete="CASCADE", name="fk_ai_quota_res_quota"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE", name="fk_ai_quota_res_user"),
        nullable=False,
    )
    operation_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="RESERVED")
    tokens_reserved: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __init__(self, **kwargs: Any) -> None:
        if "cost" in kwargs:
            cost_val = kwargs.pop("cost")
            kwargs.setdefault("tokens_reserved", cost_val)
        kwargs.setdefault("id", uuid7())
        kwargs.setdefault("status", "RESERVED")
        kwargs.setdefault("tokens_reserved", 1)
        kwargs.setdefault("created_at", datetime.now(UTC))
        super().__init__(**kwargs)

    @property
    def cost(self) -> int:
        return self.tokens_reserved if self.tokens_reserved > 0 else 1

    @cost.setter
    def cost(self, value: int) -> None:
        self.tokens_reserved = max(0, int(value))


class AIUsageLogORM(Base):
    """Provider-agnostic AI Usage Audit Log table (`ai_usage_logs`)."""

    __tablename__ = "ai_usage_logs"
    __table_args__ = (
        CheckConstraint(
            "action_type IN ('ROADMAP_GENERATION', 'SCHEDULE_PROPOSAL', 'AI_REVIEW_WEEKLY', 'AI_REVIEW_MILESTONE', 'MILESTONE_BREAKDOWN', 'CHAT_ASSISTANT', 'KNOWLEDGE_INGESTION', 'WHAT_IF_SIMULATION', 'OVERDUE_RECOVERY', 'CONTINUOUS_LEARNING')",
            name="chk_ai_usage_logs_action",
        ),
        CheckConstraint(
            "prompt_tokens >= 0 AND completion_tokens >= 0 AND total_tokens >= 0",
            name="chk_ai_usage_logs_tokens",
        ),
        CheckConstraint("latency_ms >= 0", name="chk_ai_usage_logs_latency"),
        CheckConstraint(
            "status IN ('SUCCESS', 'FAILED', 'RATE_LIMITED', 'TIMEOUT')",
            name="chk_ai_usage_logs_status",
        ),
        Index("idx_ai_usage_logs_user_action", "user_id", "action_type", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid7,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE", name="fk_ai_usage_logs_user"),
        nullable=False,
    )
    action_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="ROADMAP_GENERATION"
    )
    model_name: Mapped[str] = mapped_column(String(100), nullable=False, default="gemini-2.5-flash")
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estimated_cost_usd: Mapped[float] = mapped_column(
        Numeric(12, 6), nullable=False, default=0, server_default="0"
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="SUCCESS")
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    def __init__(self, **kwargs: Any) -> None:
        if "operation_type" in kwargs and "action_type" not in kwargs:
            kwargs["action_type"] = kwargs.pop("operation_type")
        kwargs.setdefault("id", uuid7())
        kwargs.setdefault("action_type", "ROADMAP_GENERATION")
        kwargs.setdefault("model_name", "gemini-2.5-flash")
        p_tok = int(kwargs.get("prompt_tokens", 0) or 0)
        c_tok = int(kwargs.get("completion_tokens", 0) or 0)
        kwargs.setdefault("prompt_tokens", p_tok)
        kwargs.setdefault("completion_tokens", c_tok)
        kwargs.setdefault("total_tokens", p_tok + c_tok)
        kwargs.setdefault("latency_ms", 0)
        kwargs.setdefault("estimated_cost_usd", 0)
        kwargs.setdefault("status", "SUCCESS")
        kwargs.setdefault("created_at", datetime.now(UTC))
        super().__init__(**kwargs)


class LearnerProfileORM(Base):
    """Zimmerman SRL Learner Profile table (`learner_profiles`)."""

    __tablename__ = "learner_profiles"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_learner_profiles_user_id"),
        CheckConstraint(
            "optimal_focus_duration_mins BETWEEN 15 AND 120",
            name="chk_learner_profiles_duration",
        ),
        CheckConstraint(
            "estimation_bias_factor BETWEEN 0.50 AND 2.00",
            name="chk_learner_profiles_bias",
        ),
        CheckConstraint(
            "weekly_completion_rate BETWEEN 0.00 AND 100.00",
            name="chk_learner_profiles_rate",
        ),
        CheckConstraint(
            "total_completed_sessions >= 0",
            name="chk_learner_profiles_sessions",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid7,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE", name="fk_learner_profiles_user"),
        unique=True,
        nullable=False,
    )
    optimal_focus_duration_mins: Mapped[int] = mapped_column(Integer, nullable=False, default=45)
    peak_productivity_slots: Mapped[Any] = mapped_column(JSONB, nullable=False, default=dict)
    estimation_bias_factor: Mapped[Decimal] = mapped_column(
        Numeric(4, 2), nullable=False, default=Decimal("1.00")
    )
    weekly_completion_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("0.00")
    )
    total_completed_sessions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_cold_start: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_aggregated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=lambda: datetime.now(UTC),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    def __init__(self, **kwargs: Any) -> None:
        if "opt_session_minutes" in kwargs and "optimal_focus_duration_mins" not in kwargs:
            kwargs["optimal_focus_duration_mins"] = kwargs.pop("opt_session_minutes")
        if "estimation_bias_beta" in kwargs and "estimation_bias_factor" not in kwargs:
            kwargs["estimation_bias_factor"] = Decimal(str(kwargs.pop("estimation_bias_beta")))
        kwargs.setdefault("id", uuid7())
        kwargs.setdefault("optimal_focus_duration_mins", 45)
        kwargs.setdefault("peak_productivity_slots", {})
        kwargs.setdefault("estimation_bias_factor", Decimal("1.00"))
        kwargs.setdefault("weekly_completion_rate", Decimal("0.00"))
        kwargs.setdefault("total_completed_sessions", 0)
        kwargs.setdefault("is_cold_start", True)
        super().__init__(**kwargs)

    @property
    def opt_session_minutes(self) -> int:
        return int(self.optimal_focus_duration_mins)

    @opt_session_minutes.setter
    def opt_session_minutes(self, value: int) -> None:
        self.optimal_focus_duration_mins = int(value)

    @property
    def estimation_bias_beta(self) -> float:
        return float(self.estimation_bias_factor)

    @estimation_bias_beta.setter
    def estimation_bias_beta(self, value: float) -> None:
        self.estimation_bias_factor = Decimal(f"{float(value):.2f}")


class WebCalTokenORM(Base):
    """WebCal & Calendar OAuth Sync Token table (`webcal_tokens`)."""

    __tablename__ = "webcal_tokens"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_webcal_tokens_user_id"),
        UniqueConstraint("token_hash", name="uq_webcal_tokens_token_hash"),
        CheckConstraint("token_hash ~ '^[0-9a-f]{64}$'", name="chk_webcal_tokens_hash"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE", name="fk_webcal_tokens_user"),
        unique=True,
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    oauth_refresh_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_calendar_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class PaymentTransactionORM(Base):
    """Subscription upgrade payment transactions table (`payment_transactions`)."""

    __tablename__ = "payment_transactions"
    __table_args__ = (
        UniqueConstraint("transaction_ref", name="uq_payment_transactions_ref"),
        CheckConstraint(
            "gateway_provider IN ('PAYOS', 'VNPAY', 'MOCK')",
            name="chk_payment_transactions_provider",
        ),
        CheckConstraint("amount_vnd > 0", name="chk_payment_transactions_amount"),
        CheckConstraint(
            "status IN ('PENDING', 'PAID', 'FAILED', 'CANCELLED', 'REFUNDED')",
            name="chk_payment_transactions_status",
        ),
        CheckConstraint(
            "(status IN ('PAID', 'REFUNDED') AND paid_at IS NOT NULL) OR (status NOT IN ('PAID', 'REFUNDED') AND paid_at IS NULL)",
            name="chk_payment_transactions_paid_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT", name="fk_payment_transactions_user"),
        nullable=False,
    )
    transaction_ref: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    gateway_provider: Mapped[str] = mapped_column(String(20), nullable=False, default="PAYOS")
    amount_vnd: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="VND")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    qr_code_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    webhook_signature_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


# Model aliases matching prompt naming conventions
AiQuotaModel = AIQuotaORM
AiQuotaReservationModel = AIQuotaReservationORM
AiUsageLogModel = AIUsageLogORM
LearnerProfileModel = LearnerProfileORM
UserModel = UserORM
