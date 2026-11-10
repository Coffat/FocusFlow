import json
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from src.execution.public_api import ExistingScheduledTaskDTO
from src.planning.domain.models.goal import Goal
from src.planning.domain.models.milestone import Milestone
from src.planning.domain.models.roadmap import Roadmap
from src.planning.domain.models.schedule import OfficialSchedule, ScheduleProposal

VALID_DIAGNOSTIC_DIMENSIONS: frozenset[str] = frozenset(
    {
        "KNOWLEDGE_BASELINE",
        "PRACTICAL_EXPERIENCE",
        "LEARNING_CONSTRAINTS",
    }
)


class ClarificationQuestion(BaseModel):
    question_id: str = Field(
        default="q1", description="Mã định danh duy nhất của câu hỏi (q1, q2, q3)."
    )
    id: str = Field(default="q1", description="Mã định danh câu hỏi, đồng bộ với question_id.")
    text: str = Field(
        default="", description="Nội dung câu hỏi ngắn gọn bằng tiếng Việt, đồng bộ với question."
    )
    question: str = Field(default="", description="Nội dung câu hỏi ngắn gọn bằng tiếng Việt.")
    placeholder: str = Field(
        default="Nhập câu trả lời của bạn...",
        description="Văn bản gợi ý placeholder cho người học.",
    )
    question_type: str = Field(
        default="single_choice",
        description="Loại câu hỏi: 'single_choice' (trắc nghiệm chọn 1 đáp án nhanh bằng 1 click) hoặc 'text' (tự luận ngắn).",
    )
    options: list[str] = Field(
        default_factory=list,
        description="Danh sách BẮT BUỘC gồm 3 đến 4 phương án lựa chọn thực tế, ngắn gọn khi question_type='single_choice' để người học chọn nhanh bằng 1 click. Để mảng rỗng [] khi question_type='text'.",
    )
    question_purpose: str = Field(
        default="Làm rõ bối cảnh và nhu cầu cá nhân hóa lộ trình học tập.",
        description="Mục đích sư phạm của câu hỏi nhằm thu thập thông tin gì cho việc lập lộ trình.",
    )
    expected_answer_format: str = Field(
        default="short_text",
        description="Định dạng câu trả lời mong đợi.",
    )
    diagnostic_dimension: str = Field(
        default="KNOWLEDGE_BASELINE",
        description="Chiều chẩn đoán: KNOWLEDGE_BASELINE | PRACTICAL_EXPERIENCE | LEARNING_CONSTRAINTS | GENERAL",
    )

    @model_validator(mode="before")
    @classmethod
    def _sync_id_and_question_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            copied = dict(data)
            qid = copied.get("question_id") or copied.get("id") or "q1"
            qtext = copied.get("text") or copied.get("question") or ""
            copied["question_id"] = str(qid)
            copied["id"] = str(qid)
            copied["text"] = str(qtext)
            copied["question"] = str(qtext)
            if copied.get("options") is None:
                copied["options"] = []
            return copied
        return data


# Alias requested by design spec while preserving ClarificationQuestion compatibility
ClarificationQuestionItem = ClarificationQuestion


class ClarificationQuestionsResponse(BaseModel):
    questions: list[ClarificationQuestion] = Field(default_factory=list)
    questions_version: str = "v1.0"


class ClarificationAnswerItem(BaseModel):
    question_id: str
    question_text: str | None = None
    answer: str


class ClarificationContextPayload(BaseModel):
    """Structured diagnostic context stored in Goal.clarification_context (FR-GOAL-002)."""

    status: str = "ANSWERED"  # "ANSWERED" | "PARTIAL" | "SKIPPED"
    questions_version: str = "v1.0"
    answers: list[dict[str, str]] = Field(default_factory=list)
    skipped_questions: list[str] = Field(default_factory=list)
    unresolved_assumptions: list[str] = Field(default_factory=list)
    synthesized_text: str = ""
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_json_string(self) -> str:
        return json.dumps(self.model_dump(mode="json"), ensure_ascii=False)

    def to_json_str(self) -> str:
        return self.to_json_string()


def parse_clarification_context(
    raw: str | None,
    *,
    prior_knowledge_level: str = "BEGINNER",
) -> ClarificationContextPayload:
    """Parse Goal.clarification_context from JSON or legacy plain text with safe defaults."""
    if raw is None or not raw.strip():
        return ClarificationContextPayload(
            status="SKIPPED",
            questions_version="v1.0",
            answers=[],
            skipped_questions=[],
            unresolved_assumptions=[
                f"Người học chưa trả lời phỏng vấn chẩn đoán; năng lực chi tiết đang ở mức UNKNOWN "
                f"(tạm định hướng khởi đầu theo prior_knowledge_level={prior_knowledge_level}).",
                "Giả định người học cần lộ trình cân bằng giữa lý thuyết cốt lõi và bài tập thực hành có kiểm chứng.",
            ],
            synthesized_text="",
            updated_at=datetime.now(UTC).isoformat(),
        )

    cleaned = raw.strip()
    if cleaned.startswith("{") and cleaned.endswith("}"):
        try:
            parsed_dict = json.loads(cleaned)
            if isinstance(parsed_dict, dict) and "status" in parsed_dict:
                return ClarificationContextPayload.model_validate(parsed_dict)
        except (ValueError, TypeError):
            pass

    return ClarificationContextPayload(
        status="ANSWERED",
        questions_version="v1.0",
        answers=[{"question_id": "legacy", "question_text": "", "answer": cleaned}],
        skipped_questions=[],
        unresolved_assumptions=[],
        synthesized_text=cleaned,
        updated_at=datetime.now(UTC).isoformat(),
    )


@dataclass(frozen=True, slots=True)
class CreateGoalAndRoadmapResultDTO:
    goal: Goal
    roadmap: Roadmap


@dataclass(frozen=True, slots=True)
class SseJobTicketDTO:
    job_id: UUID
    reservation_id: UUID
    roadmap_id: UUID
    job_type: str
    status: str
    stream_url: str


@dataclass(frozen=True, slots=True)
class MilestoneInputItemDTO:
    title: str
    description: str | None = None
    sequence_order: int = 1
    milestone_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class ProposedTaskInputItemDTO:
    milestone_id: UUID
    title: str
    description: str | None = None
    estimated_minutes: int = 45
    scheduled_date: date | str | None = None
    scheduled_start: datetime | str | None = None
    scheduled_end: datetime | str | None = None
    task_id: UUID | None = None
    prerequisite_ids: list[UUID | str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ProposedDependencyInputItemDTO:
    predecessor_id: UUID | str
    successor_id: UUID | str
    is_mandatory: bool = True


@dataclass(frozen=True, slots=True)
class ScheduleProposalViewDTO:
    proposal: ScheduleProposal
    is_valid: bool
    violations: list[dict[str, Any]] = field(default_factory=list)
    soft_overflow_warnings: list[dict[str, Any]] = field(default_factory=list)
    advisory_warnings: list[str] = field(default_factory=list)
    diff_summary: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ApplyScheduleProposalResultDTO:
    roadmap: Roadmap
    official_schedule: OfficialSchedule
    proposal: ScheduleProposal
    preserved_completed_tasks_count: int
    replaced_tasks_count: int
    inserted_tasks_count: int
    affected_tasks_count: int
    total_shifted_minutes: int
    trigger_type: str


@dataclass(frozen=True, slots=True)
class RoadmapDetailDTO:
    roadmap: Roadmap
    goal: Goal | None
    milestones: list[Milestone]
    official_schedule: OfficialSchedule | None
    current_draft_proposal: ScheduleProposal | None
    scheduled_tasks: list[ExistingScheduledTaskDTO] = field(default_factory=list)
