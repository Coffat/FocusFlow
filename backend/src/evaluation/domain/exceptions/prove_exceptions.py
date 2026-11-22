"""Domain exceptions for Prove Mode assessment lifecycle."""

from __future__ import annotations


class ProofAlreadyGradedError(Exception):
    """Raised when attempting to grade a MilestoneProof that is already graded."""

    code: str = "PROOF_ALREADY_GRADED"

    def __init__(
        self,
        message: str = (
            "Bài kiểm tra kiến thức này đã được chấm điểm trước đó. "
            "Vui lòng tạo bộ câu hỏi mới nếu bạn muốn làm lại."
        ),
    ) -> None:
        super().__init__(message)
        self.message = message


class ProveGradingUnavailableError(RuntimeError):
    """Raised when AI grading fails due to a technical, provider, or schema error."""

    code: str = "AI_GRADING_UNAVAILABLE"

    def __init__(
        self,
        message: str = (
            "Hệ thống chấm điểm AI tạm thời gián đoạn. "
            "Câu trả lời của bạn vẫn được giữ nguyên, vui lòng bấm thử chấm lại."
        ),
        *,
        reason_code: str = "PROVE_GRADER_UNAVAILABLE",
    ) -> None:
        super().__init__(message)
        self.message = message
        self.reason_code = reason_code
