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
    "CalendarBusyIntervalDTO",
    "CalendarConnectionQueryPort",
    "CalendarConnectionSnapshotDTO",
    "CalendarSyncFacadePort",
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
    "create_availability_query_port",
    "create_calendar_connection_query_port",
    "create_calendar_sync_facade",
    "create_learner_profile_query_port",
    "create_quota_facade",
    "create_user_query_port",
    "register_account_port_factories",
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

    async def check_quota_available(
        self,
        user_id: UUID,
        min_credits: int = 1,
    ) -> bool: ...

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


@dataclass(frozen=True)
class CalendarConnectionSnapshotDTO:
    """Read-only external calendar connection DTO exposed to Planning context (UC-17)."""

    user_id: UUID
    provider: str
    sync_status: str
    external_calendar_id: str
    source_calendars: tuple[str, ...]
    last_synced_at: str | None = None
    is_active: bool = True


@dataclass(frozen=True)
class CalendarBusyIntervalDTO:
    """External calendar busy interval passed to Planning for conflict-free scheduling."""

    start_time: datetime
    end_time: datetime


class CalendarConnectionQueryPort(Protocol):
    """Cross-context read-only query port for Google/Outlook Calendar connection state."""

    async def get_connection_snapshot(
        self,
        user_id: UUID,
        provider: str = "GOOGLE",
    ) -> CalendarConnectionSnapshotDTO | None: ...

    async def get_free_busy_intervals(
        self,
        user_id: UUID,
        time_min: datetime,
        time_max: datetime,
        provider: str = "GOOGLE",
    ) -> list[CalendarBusyIntervalDTO]: ...


class CalendarSyncFacadePort(Protocol):
    """Cross-context facade port for calendar synchronization operations (UC-17)."""

    async def sync_schedule_blocks_to_google(
        self,
        schedule_id: UUID,
        user_id: UUID,
    ) -> None: ...


_quota_factory: Any = None
_availability_factory: Any = None
_learner_profile_factory: Any = None
_user_query_factory: Any = None
_calendar_connection_query_factory: Any = None
_calendar_sync_facade_factory: Any = None


def register_account_port_factories(
    *,
    quota_factory: Any = None,
    availability_factory: Any = None,
    learner_profile_factory: Any = None,
    user_query_factory: Any = None,
    calendar_connection_query_factory: Any = None,
    calendar_sync_facade_factory: Any = None,
) -> None:
    global \
        _quota_factory, \
        _availability_factory, \
        _learner_profile_factory, \
        _user_query_factory, \
        _calendar_connection_query_factory, \
        _calendar_sync_facade_factory
    if quota_factory is not None:
        _quota_factory = quota_factory
    if availability_factory is not None:
        _availability_factory = availability_factory
    if learner_profile_factory is not None:
        _learner_profile_factory = learner_profile_factory
    if user_query_factory is not None:
        _user_query_factory = user_query_factory
    if calendar_connection_query_factory is not None:
        _calendar_connection_query_factory = calendar_connection_query_factory
    if calendar_sync_facade_factory is not None:
        _calendar_sync_facade_factory = calendar_sync_facade_factory


def _ensure_account_factories_loaded() -> None:
    if _quota_factory is None:
        import importlib

        importlib.import_module("src.account.infrastructure.adapters")


def create_quota_facade(session: Any) -> QuotaFacadePort:
    _ensure_account_factories_loaded()
    res: QuotaFacadePort = _quota_factory(session)
    return res


def create_availability_query_port(session: Any) -> AvailabilityQueryPort:
    _ensure_account_factories_loaded()
    res: AvailabilityQueryPort = _availability_factory(session)
    return res


def create_learner_profile_query_port(session: Any) -> LearnerProfileQueryPort:
    _ensure_account_factories_loaded()
    res: LearnerProfileQueryPort = _learner_profile_factory(session)
    return res


def create_user_query_port(session: Any) -> UserQueryPort:
    _ensure_account_factories_loaded()
    res: UserQueryPort = _user_query_factory(session)
    return res


def create_calendar_connection_query_port(
    session: Any,
    calendar_provider: Any = None,
) -> CalendarConnectionQueryPort:
    _ensure_account_factories_loaded()
    res: CalendarConnectionQueryPort = _calendar_connection_query_factory(
        session, calendar_provider=calendar_provider
    )
    return res


def create_calendar_sync_facade(session: Any) -> CalendarSyncFacadePort:
    _ensure_account_factories_loaded()
    if _calendar_sync_facade_factory is None:
        import importlib

        importlib.import_module("src.account.infrastructure.adapters.calendar_sync_facade_adapter")
    assert callable(_calendar_sync_facade_factory)
    res: CalendarSyncFacadePort = _calendar_sync_facade_factory(session)
    return res
