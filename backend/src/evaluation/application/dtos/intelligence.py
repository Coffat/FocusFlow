from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ProveQuestionItemSchema(BaseModel):
    """Single open-ended recall question generated for Prove Mode (UC-20)."""

    id: str = Field(..., min_length=1, max_length=16, description="Mã câu hỏi: q1, q2, hoặc q3.")
    prompt: str = Field(
        ...,
        min_length=5,
        max_length=500,
        description="Nội dung câu hỏi tự luận tiếng Việt gắn với cột mốc, nhiệm vụ hoặc khái niệm.",
    )


class ProveQuestionsLLMOutput(BaseModel):
    """LLM output schema for Prove Mode question generation (3 pedagogical objectives)."""

    questions: list[ProveQuestionItemSchema] = Field(
        ...,
        min_length=3,
        max_length=3,
        description="Đúng 3 câu hỏi: q1 (hiểu bản chất), q2 (ví dụ cụ thể/lỗi sai), q3 (vận dụng thực tế).",
    )


class ProveAnswerFeedbackSchema(BaseModel):
    """Per-question evidence extracted by the Prove Mode rubric grader."""

    question_id: str = Field(..., min_length=1, max_length=32, description="Mã câu hỏi (q1..q3).")
    evidence: str = Field(
        ...,
        min_length=3,
        max_length=400,
        description="Bằng chứng khách quan trích từ câu trả lời và điểm cần cải thiện nếu có.",
    )
    is_addressed: bool = Field(
        default=False,
        description="True nếu câu trả lời thực sự giải quyết đúng trọng tâm câu hỏi.",
    )


class ProveGradingLLMOutput(BaseModel):
    """Rubric-only Prove grader output; server owns total score, threshold status & calibration."""

    conceptual_understanding_score: int = Field(
        ...,
        ge=0,
        le=40,
        description="Mức độ hiểu bản chất khái niệm và cơ chế cốt lõi (0..40 điểm).",
    )
    example_grounding_score: int = Field(
        ...,
        ge=0,
        le=30,
        description="Ví dụ minh họa cụ thể / phát hiện lỗi sai thường gặp (0..30 điểm).",
    )
    practical_application_score: int = Field(
        ...,
        ge=0,
        le=30,
        description="Khả năng vận dụng vào tình huống thực tế mới (0..30 điểm).",
    )
    answer_evidence: list[ProveAnswerFeedbackSchema] = Field(
        default_factory=list,
        description="Nhận xét và bằng chứng cụ thể cho từng câu trả lời (q1, q2, q3).",
    )
    corrective_action: str | None = Field(
        default=None,
        max_length=500,
        description="Hành động ôn tập ngắn gọn bằng tiếng Việt nếu người học còn lỗ hổng.",
    )


class WeeklyReviewLLMOutput(BaseModel):
    """LLM output schema for supportive SRL Weekly Review feedback (UC-21)."""

    strengths_feedback: str = Field(
        ...,
        min_length=5,
        max_length=1000,
        description="Nhận xét điểm tích cực theo giọng khích lệ, chỉ dùng số liệu từ quantitative_summary.",
    )
    bottlenecks_feedback: str = Field(
        ...,
        min_length=5,
        max_length=1000,
        description="Nhận xét điểm nghẽn/khó khăn mang tính xây dựng, không phán xét, đúng số liệu nguồn.",
    )
    action_recommendations: str = Field(
        ...,
        min_length=5,
        max_length=1000,
        description="Từ 1 đến 3 hành động cụ thể, khả thi cho tuần tới.",
    )


class GenerateProofResponseDTO(BaseModel):
    proof_id: UUID
    status: str
    questions: list[dict[str, Any]]


class SubmitProofRequestDTO(BaseModel):
    answers: list[dict[str, Any]] = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)


class MilestoneProofResponseDTO(BaseModel):
    id: UUID
    milestone_id: UUID
    status: str
    score: int
    confidence: float
    corrective_action: str | None
    is_verified: bool = True
    calibration_error: float | None = None
    answer_evidence: list[dict[str, Any]] = Field(default_factory=list)


class GenerateWeeklyReviewRequestDTO(BaseModel):
    roadmap_id: UUID
    period_start: date
    period_end: date
    reflection: dict[str, Any] = Field(default_factory=dict)


class WeeklyReviewResponseDTO(BaseModel):
    id: UUID
    roadmap_id: UUID
    period_start: date
    period_end: date
    quantitative_summary: dict[str, Any]
    strengths_feedback: str
    bottlenecks_feedback: str
    action_recommendations: str
    user_reflection_payload: dict[str, Any]
    generated_at: datetime
