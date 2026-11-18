from typing import Any

from src.shared_kernel.domain.exceptions import DomainError


class ExecutionDomainError(DomainError):
    """Base domain error for the Execution Bounded Context."""

    def __init__(
        self,
        message: str,
        code: str = "EXECUTION_DOMAIN_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, code=code)
        self.details = details or {}


class TaskNotFoundError(ExecutionDomainError):
    def __init__(self, message: str = "Không tìm thấy nhiệm vụ học tập.") -> None:
        super().__init__(message=message, code="TASK_NOT_FOUND")


class TaskBlockedError(ExecutionDomainError):
    def __init__(
        self,
        message: str = "Nhiệm vụ đang bị khóa do còn nhiệm vụ tiền đề chưa hoàn thành.",
        *,
        blocking_predecessor_ids: list[str] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code="TASK_BLOCKED",
            details={"blocking_predecessor_ids": blocking_predecessor_ids or []},
        )


class TaskStalledInterventionRequiredError(ExecutionDomainError):
    def __init__(
        self,
        message: str = "Nhiệm vụ đã dời lịch quá hạn từ 3 lần trở lên (STALLED). Cần chọn phương án can thiệp.",
    ) -> None:
        super().__init__(message=message, code="TASK_STALLED_INTERVENTION_REQUIRED")


class InvalidTaskDurationError(ExecutionDomainError):
    def __init__(
        self,
        message: str = "Thời lượng nhiệm vụ thủ công phải nằm trong khoảng 15 đến 240 phút.",
    ) -> None:
        super().__init__(message=message, code="INVALID_TASK_DURATION")


class InvalidTaskStateError(ExecutionDomainError):
    def __init__(
        self,
        message: str = "Trạng thái hiện tại của nhiệm vụ không cho phép thao tác này.",
    ) -> None:
        super().__init__(message=message, code="INVALID_TASK_STATE")


class TaskHasActiveSuccessorsError(ExecutionDomainError):
    def __init__(
        self,
        message: str = "Không thể hủy nhiệm vụ vì đang là tiền đề bắt buộc của nhiệm vụ chưa hoàn thành.",
        *,
        dependent_successor_ids: list[str] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code="TASK_HAS_ACTIVE_SUCCESSORS",
            details={"dependent_successor_ids": dependent_successor_ids or []},
        )


class TakeawayValidationFailedError(ExecutionDomainError):
    def __init__(
        self,
        message: str = "Nội dung Key Takeaway chưa đạt chuẩn tối thiểu (tối thiểu 30 ký tự, 6 từ có nghĩa, không lặp/rác và không sao chép đề bài).",
        *,
        reasons: list[str] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code="TAKEAWAY_VALIDATION_FAILED",
            details={"reasons": reasons or []},
        )


class ActiveSessionExistsError(ExecutionDomainError):
    def __init__(
        self,
        message: str = "Bạn đang có một phiên học khác đang diễn ra (IN_PROGRESS).",
    ) -> None:
        super().__init__(message=message, code="ACTIVE_SESSION_EXISTS")


class PendingTakeawayRequiredError(ExecutionDomainError):
    def __init__(
        self,
        message: str = "Vui lòng bổ sung Key Takeaway cho phiên học bị gián đoạn trước đó trước khi mở phiên mới.",
        *,
        pending_session_id: str | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code="PENDING_TAKEAWAY_REQUIRED",
            details={"pending_session_id": pending_session_id} if pending_session_id else {},
        )


class SessionNotFoundError(ExecutionDomainError):
    def __init__(self, message: str = "Không tìm thấy phiên học.") -> None:
        super().__init__(message=message, code="SESSION_NOT_FOUND")


class InvalidSessionStateError(ExecutionDomainError):
    def __init__(
        self,
        message: str = "Trạng thái phiên học không hợp lệ cho thao tác này.",
    ) -> None:
        super().__init__(message=message, code="INVALID_SESSION_STATE")


class ScheduleSlotConflictError(ExecutionDomainError):
    def __init__(
        self,
        message: str = "Khung giờ học vi phạm ràng buộc thời gian rảnh hoặc xung đột lịch.",
        *,
        violations: list[dict[str, Any]] | None = None,
        calendar_conflicts: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code="SCHEDULE_SLOT_CONFLICT",
            details={
                "violations": violations or [],
                "calendar_conflicts": calendar_conflicts or [],
            },
        )


class RoadmapReadOnlyError(ExecutionDomainError):
    def __init__(
        self,
        message: str = "Lộ trình đã hoàn thành hoặc lưu trữ nên không thể chỉnh sửa nhiệm vụ.",
    ) -> None:
        super().__init__(message=message, code="ROADMAP_READ_ONLY")


class RescheduleBudgetExhaustedError(ExecutionDomainError):
    def __init__(
        self,
        message: str = "Ngân sách dời lịch quá hạn trong tuần của lộ trình đã hết.",
    ) -> None:
        super().__init__(message=message, code="RESCHEDULE_BUDGET_EXHAUSTED")
