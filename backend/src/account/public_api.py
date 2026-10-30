from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from src.shared_kernel.domain.events import DomainEvent
from src.shared_kernel.domain.exceptions import DomainError

__all__ = [
    "AvailabilityGateResultDTO",
    "AvailabilityQueryPort",
    "AvailabilitySnapshotDTO",
    "AvailabilityUpdatedEvent",
    "InsufficientQuotaError",
    "LearnerProfileDTO",
    "LearnerProfileQueryPort",
    "ProposedTaskBlockDTO",
    "QuotaExceededError",
    "QuotaExceededException",
    "QuotaExhaustedError",
    "QuotaFacadePort",
    "QuotaReservationNotFoundError",
    "UserQueryPort",
    "UserSnapshotDTO",
    "UserUpgradedToPremiumEvent",
]


@dataclass(frozen=True, kw_only=True)
class AvailabilityUpdatedEvent(DomainEvent):
    """Published when a learner updates their Mode A/B availability profile (UC-03)."""

    user_id: UUID
    availability_mode: str
    aggregate_type: str = "AvailabilityProfile"


@dataclass(frozen=True, kw_only=True)
class UserUpgradedToPremiumEvent(DomainEvent):
    """Published when a learner completes a Pro subscription payment (UC-05)."""

    user_id: UUID
    plan_tier: str = "PRO"


class QuotaExceededError(DomainError):
    """Raised when a user does not have sufficient AI credits/quota for an operation (BUSR-10)."""

    def __init__(
        self,
        message: str = "Hạn ngạch AI của bạn không đủ để thực hiện thao tác này.",
        code: str = "QUOTA_EXHAUSTED",
    ) -> None:
        super().__init__(message=message, code=code)


class QuotaReservationNotFoundError(DomainError):
    """Raised when an AI quota reservation cannot be found."""

    def __init__(
        self,
        message: str = "Không tìm thấy bản ghi giữ chỗ hạn ngạch AI.",
        code: str = "QUOTA_RESERVATION_NOT_FOUND",
    ) -> None:
        super().__init__(message=message, code=code)


QuotaExceededException = QuotaExceededError
QuotaExhaustedError = QuotaExceededError
InsufficientQuotaError = QuotaExceededError


@dataclass(frozen=True)
class AvailabilitySnapshotDTO:
    """Read-only DTO exposed to Planning & Evaluation contexts."""

    user_id: UUID
    mode: str
    daily_cap_minutes: int
    weekly_capacity_minutes: int
    updated_at: str | None = None
    daily_quota_minutes: dict[str, int] = field(default_factory=dict)
    availability_slots: tuple[dict[str, Any], ...] = ()
    disabled_weekdays: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProposedTaskBlockDTO:
    """Task block proposal submitted by Planning to be validated against learner availability."""

    task_id: UUID | None
    title: str
    day_of_week: str  # "monday" .. "sunday"
    start_time: str  # "HH:MM"
    end_time: str  # "HH:MM"
    end_day_offset: int = 0
    duration_minutes: int = 30


@dataclass(frozen=True)
class AvailabilityGateResultDTO:
    """Result of Tier-2 availability gate validation returned to Planning."""

    is_valid: bool
    has_soft_overflow: bool
    overflow_minutes: int
    violation_reasons: tuple[str, ...]
    availability_updated_at: str | None = None


class AvailabilityQueryPort(Protocol):
    """Cross-context read-only query & validation port exposed to Planning & Evaluation."""

    async def get_active_availability(self, user_id: UUID) -> AvailabilitySnapshotDTO | None: ...

    async def validate_schedule_proposal(
        self,
        user_id: UUID,
        proposed_tasks: list[ProposedTaskBlockDTO],
        occupied_tasks: list[ProposedTaskBlockDTO] | None = None,
        expected_updated_at: str | None = None,
    ) -> AvailabilityGateResultDTO: ...


class QuotaFacadePort(Protocol):
    """Cross-context port for 2-Phase ACID AI Quota Reservation (ADR-005 / BUSR-10)."""

    async def reserve_quota(
        self,
        user_id: UUID,
        operation_type: str = "ROADMAP_GEN",
        cost: int = 1,
        ttl_seconds: int = 120,
    ) -> UUID: ...

    async def commit_reservation(
        self,
        reservation_id: UUID,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        model_name: str = "gemini-2.5-flash",
    ) -> None: ...

    async def release_reservation(
        self,
        reservation_id: UUID,
        reason: str = "RELEASED",
    ) -> None: ...

    async def expire_stale_reservations(self, now: datetime | None = None) -> int: ...


@dataclass(frozen=True)
class LearnerProfileDTO:
    """Read-only Learner Profile DTO exposed to Planning & Evaluation contexts (ADR-010)."""

    user_id: UUID
    opt_session_minutes: int = 45
    estimation_bias_beta: float = 1.0
    peak_productivity_slots: dict[str, Any] = field(default_factory=dict)
    is_cold_start: bool = True

    @property
    def optimal_focus_duration_mins(self) -> int:
        return self.opt_session_minutes

    @property
    def estimation_bias_factor(self) -> float:
        return self.estimation_bias_beta


class LearnerProfileQueryPort(Protocol):
    """Cross-context read-only query port for Zimmerman SRL Learner Profile (UC-07/08, ADR-010)."""

    async def get_learner_profile(self, user_id: UUID) -> LearnerProfileDTO: ...


@dataclass(frozen=True)
class UserSnapshotDTO:
    """Read-only user profile DTO exposed across bounded contexts."""

    id: UUID
    email: str
    full_name: str
    role: str
    tier: str
    is_locked: bool
    timezone: str = "Asia/Ho_Chi_Minh"


class UserQueryPort(Protocol):
    """Cross-context read-only query port for User information."""

    async def get_user_by_id(self, user_id: UUID) -> UserSnapshotDTO | None: ...

    async def get_user_by_email(self, email: str) -> UserSnapshotDTO | None: ...
