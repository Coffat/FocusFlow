from typing import Any

from src.shared_kernel.domain.exceptions import DomainError


class AvailabilityDomainException(DomainError):  # noqa: N818
    """Base domain exception for availability business rule violations."""

    def __init__(
        self,
        message: str,
        code: str = "AVAILABILITY_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, code=code)
        self.details = details or {}


class InvalidTimeSlotException(AvailabilityDomainException):  # noqa: N818
    """Raised when a time slot violates invariants (start >= end or duration < 30m)."""

    def __init__(
        self,
        message: str = "Khung giờ không hợp lệ: Thời lượng tối thiểu 30 phút và kết thúc phải sau bắt đầu.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, code="INVALID_TIME_SLOT", details=details)


class OverlappingTimeSlotsException(AvailabilityDomainException):  # noqa: N818
    """Raised when two or more time slots within the same day overlap."""

    def __init__(
        self,
        day: str,
        conflicting_slots: list[str] | tuple[str, ...],
        message: str | None = None,
    ) -> None:
        conflicting_list = list(conflicting_slots)
        msg = message or f"Khung giờ vào {day} bị xung đột: {conflicting_list} chồng lấn nhau."
        super().__init__(
            msg,
            code="OVERLAPPING_TIME_SLOTS",
            details={"day": day, "conflicting_slots": conflicting_list},
        )


class InvalidQuotaBoundException(AvailabilityDomainException):  # noqa: N818
    """Raised when daily quota hours violate OS-06 bounds (0.5h to 14.0h)."""

    def __init__(
        self,
        day: str,
        quota_hours: float,
        min_allowed: float = 0.5,
        max_allowed: float = 14.0,
        message: str | None = None,
    ) -> None:
        msg = message or (
            f"Số giờ rảnh cho {day} ({quota_hours}h) không hợp lệ theo OS-06. "
            f"Phải nằm trong khoảng từ {min_allowed} giờ (30 phút) đến {max_allowed} giờ."
        )
        super().__init__(
            msg,
            code="INVALID_QUOTA_BOUNDS",
            details={
                "day": day,
                "quota_hours": quota_hours,
                "min_allowed": min_allowed,
                "max_allowed": max_allowed,
            },
        )


class InvalidAllowedWindowException(AvailabilityDomainException):  # noqa: N818
    """Raised when allowed window is invalid or duration < 30m."""

    def __init__(
        self,
        message: str = "Khung giờ cho phép (allowed_window) không hợp lệ hoặc dưới 30 phút.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, code="INVALID_ALLOWED_WINDOW", details=details)


class InsufficientWeeklyAvailabilityException(AvailabilityDomainException):  # noqa: N818
    """Raised when total weekly availability is less than 1.0 hour."""

    def __init__(
        self,
        total_hours: float,
        min_required: float = 1.0,
        message: str | None = None,
    ) -> None:
        msg = message or (
            f"Tổng thời gian rảnh trong tuần ({total_hours}h) quá thấp. "
            f"Cần tối thiểu {min_required} giờ/tuần để hệ thống có thể lập kế hoạch học tập."
        )
        super().__init__(
            msg,
            code="INSUFFICIENT_WEEKLY_AVAILABILITY",
            details={"total_hours": total_hours, "min_required": min_required},
        )


class ConcurrentAvailabilityModifiedException(AvailabilityDomainException):  # noqa: N818
    """Raised when optimistic lock verification fails (version/updated_at mismatch)."""

    def __init__(
        self,
        message: str = "Cấu hình thời gian rảnh đã bị thay đổi đồng thời bởi một phiên khác.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            code="CONCURRENT_AVAILABILITY_MODIFIED",
            details=details,
        )


class InvalidAvailabilityModeException(AvailabilityDomainException):  # noqa: N818
    """Raised when availability mode is not MODE_A or MODE_B."""

    def __init__(
        self,
        mode: str,
        message: str | None = None,
    ) -> None:
        msg = (
            message
            or f"Chế độ thời gian rảnh '{mode}' không hợp lệ. Chỉ chấp nhận MODE_A hoặc MODE_B."
        )
        super().__init__(
            msg,
            code="INVALID_AVAILABILITY_MODE",
            details={"mode": mode, "allowed": ["MODE_A", "MODE_B"]},
        )


class InvalidCalendarModeException(AvailabilityDomainException):  # noqa: N818
    """Raised when calendar integration mode is invalid."""

    def __init__(
        self,
        calendar_mode: str,
        message: str | None = None,
    ) -> None:
        msg = (
            message
            or f"Chế độ tích hợp lịch '{calendar_mode}' không hợp lệ. Chỉ chấp nhận NONE, EXPORT_ICS, CONNECTED."
        )
        super().__init__(
            msg,
            code="INVALID_CALENDAR_MODE",
            details={
                "calendar_integration_mode": calendar_mode,
                "allowed": ["NONE", "EXPORT_ICS", "CONNECTED"],
            },
        )


class InvalidPreferredPeriodException(AvailabilityDomainException):  # noqa: N818
    """Raised when preferred period is invalid."""

    def __init__(
        self,
        preferred_period: str,
        day: str | None = None,
        message: str | None = None,
    ) -> None:
        msg = (
            message
            or f"Buổi học ưu tiên '{preferred_period}' không hợp lệ. Chỉ chấp nhận MORNING, AFTERNOON, EVENING, ANY."
        )
        details: dict[str, Any] = {
            "preferred_period": preferred_period,
            "allowed": ["MORNING", "AFTERNOON", "EVENING", "ANY"],
        }
        if day is not None:
            details["day"] = day
        super().__init__(
            msg,
            code="INVALID_PREFERRED_PERIOD",
            details=details,
        )


class InvalidMinSessionMinutesException(AvailabilityDomainException):  # noqa: N818
    """Raised when min_session_minutes is outside [15, 120]."""

    def __init__(
        self,
        min_session_minutes: int,
        day: str | None = None,
        message: str | None = None,
    ) -> None:
        msg = (
            message
            or f"Thời lượng phiên học tối thiểu ({min_session_minutes} phút) phải nằm trong khoảng từ 15 đến 120 phút."
        )
        details: dict[str, Any] = {
            "min_session_minutes": min_session_minutes,
            "min_allowed": 15,
            "max_allowed": 120,
        }
        if day is not None:
            details["day"] = day
        super().__init__(
            msg,
            code="INVALID_MIN_SESSION_MINUTES",
            details=details,
        )
