from uuid import UUID

from src.shared_kernel.domain.exceptions import DomainError


class PlanningDomainError(DomainError):
    """Base domain error for the Planning Bounded Context."""

    def __init__(self, message: str, code: str = "PLANNING_DOMAIN_ERROR") -> None:
        super().__init__(message=message, code=code)


class InvalidRoadmapStateTransitionError(PlanningDomainError):
    """Raised when a roadmap state transition violates SRS state machine rules."""

    def __init__(
        self,
        current_status: str,
        target_status: str,
        message: str | None = None,
    ) -> None:
        msg = message or (
            f"Không thể chuyển trạng thái Roadmap từ '{current_status}' sang '{target_status}'."
        )
        super().__init__(message=msg, code="INVALID_ROADMAP_STATE_TRANSITION")
        self.current_status = current_status
        self.target_status = target_status


class ActiveRoadmapLimitExceededError(PlanningDomainError):
    """Raised when activating a roadmap exceeds OS-02 tier limits (Free: 3, Premium: 15)."""

    def __init__(
        self,
        tier: str,
        current_active_count: int,
        max_allowed: int,
        message: str | None = None,
    ) -> None:
        msg = message or (
            f"Gói '{tier}' chỉ cho phép tối đa {max_allowed} lộ trình đang ACTIVE "
            f"(hiện đang có {current_active_count})."
        )
        super().__init__(message=msg, code="ACTIVE_ROADMAP_LIMIT_EXCEEDED")
        self.tier = tier
        self.current_active_count = current_active_count
        self.max_allowed = max_allowed


class UnapprovedMilestonesError(PlanningDomainError):
    """Raised when generating a Level-2 ScheduleProposal before Milestones are APPROVED (UC-07/UC-08)."""

    def __init__(
        self,
        message: str = "Cần phê duyệt (APPROVE) ít nhất một cột mốc (Milestone) trước khi sinh đề xuất lịch học chi tiết.",
    ) -> None:
        super().__init__(message=message, code="UNAPPROVED_MILESTONES")


class InvalidMilestoneSequenceError(PlanningDomainError):
    """Raised when milestones violate sequence order or count bounds (3..7 for AI)."""

    def __init__(
        self,
        message: str = "Danh sách cột mốc (Milestones) không hợp lệ về thứ tự hoặc số lượng.",
    ) -> None:
        super().__init__(message=message, code="INVALID_MILESTONE_SEQUENCE")


class ProposalValidationGateError(PlanningDomainError):
    """Raised when a ScheduleProposal fails Tier 1 or Tier 2 deterministic validation (UC-12 / ADR-009)."""

    def __init__(
        self,
        message: str = "Đề xuất lịch học vi phạm các ràng buộc kiểm định (Validation Gate).",
        code: str = "AI_SCHEMA_VALIDATION_ERROR",
        violations: list[dict[str, object]] | None = None,
    ) -> None:
        super().__init__(message=message, code=code)
        self.violations = violations or []


class SoftOverflowConfirmationRequiredError(PlanningDomainError):
    """Raised on Apply when Mode B has a <= 30m soft overflow on the last task of day without confirmation (BUSR-04)."""

    def __init__(
        self,
        overflow_minutes: int = 0,
        message: str | None = None,
    ) -> None:
        msg = message or (
            f"Đề xuất lịch học có nhiệm vụ cuối ngày tràn {overflow_minutes} phút (<= 30 phút). "
            "Cần xác nhận (confirm_soft_overflow=True) trước khi áp dụng."
        )
        super().__init__(message=msg, code="SOFT_OVERFLOW_CONFIRMATION_REQUIRED")
        self.overflow_minutes = overflow_minutes


class GoalNotFoundError(PlanningDomainError):
    """Raised when a goal is not found or does not belong to the current user (IDOR protection)."""

    def __init__(self, message: str | UUID = "Không tìm thấy mục tiêu học tập.") -> None:
        msg = (
            f"Không tìm thấy mục tiêu học tập ({message})."
            if isinstance(message, UUID)
            else message
        )
        super().__init__(message=msg, code="GOAL_NOT_FOUND")


class RoadmapNotFoundError(PlanningDomainError):
    """Raised when a roadmap is not found or does not belong to the current user (IDOR protection)."""

    def __init__(self, message: str | UUID = "Không tìm thấy lộ trình học tập.") -> None:
        msg = (
            f"Không tìm thấy lộ trình học tập ({message})."
            if isinstance(message, UUID)
            else message
        )
        super().__init__(message=msg, code="ROADMAP_NOT_FOUND")


class ScheduleProposalNotFoundError(PlanningDomainError):
    """Raised when a schedule proposal is not found or does not belong to the current user."""

    def __init__(self, message: str | UUID = "Không tìm thấy bản đề xuất lịch học.") -> None:
        msg = (
            f"Không tìm thấy bản đề xuất lịch học ({message})."
            if isinstance(message, UUID)
            else message
        )
        super().__init__(message=msg, code="SCHEDULE_PROPOSAL_NOT_FOUND")


class UnauthorizedToolCallError(PlanningDomainError):
    """Raised when an AI stage attempts to invoke a tool not permitted for that stage."""

    def __init__(
        self,
        tool_name: str,
        stage: str,
        message: str | None = None,
    ) -> None:
        msg = message or (f"Tool '{tool_name}' không được cấp quyền thực thi tại stage '{stage}'.")
        super().__init__(message=msg, code="UNAUTHORIZED_TOOL_CALL")
        self.tool_name = tool_name
        self.stage = stage


class ToolInputValidationError(PlanningDomainError):
    """Raised when tool arguments fail deterministic validation."""

    def __init__(
        self,
        tool_name: str,
        message: str | None = None,
        *,
        reason: str | None = None,
    ) -> None:
        msg = reason or message or "Tham số đầu vào của tool không hợp lệ."
        super().__init__(message=msg, code="TOOL_INPUT_VALIDATION_ERROR")
        self.tool_name = tool_name
        self.reason = msg


class ToolCallLimitExceededError(PlanningDomainError):
    """Raised when tool invocations exceed max_tool_calls in a single stage."""

    def __init__(
        self,
        stage: str = "",
        max_calls: int = 4,
        message: str | None = None,
    ) -> None:
        msg = message or (
            f"Đã vượt quá giới hạn số lần gọi tool tối đa ({max_calls}) tại stage '{stage}'."
        )
        super().__init__(message=msg, code="TOOL_CALL_LIMIT_EXCEEDED")
        self.stage = stage
        self.max_calls = max_calls
