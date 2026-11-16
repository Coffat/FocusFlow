import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from src.execution.public_api import ExistingScheduledTaskDTO
from src.planning.domain.models.goal import Goal
from src.planning.domain.models.milestone import Milestone
from src.planning.domain.models.roadmap import Roadmap
from src.planning.domain.models.schedule import OfficialSchedule, ScheduleProposal
from src.planning.domain.services.validation_types import (
    AI_BLOCK_MAX_MINUTES,
    AI_BLOCK_MIN_MINUTES,
)


class DiagnosticDimension(StrEnum):
    """Canonical 7 diagnostic dimensions for FocusFlow Goal Clarification (T2.4 / B5)."""

    TARGET_OUTCOME = "TARGET_OUTCOME"
    PRIOR_KNOWLEDGE = "PRIOR_KNOWLEDGE"
    PRACTICAL_EXPERIENCE = "PRACTICAL_EXPERIENCE"
    TIME_COMMITMENT = "TIME_COMMITMENT"
    TIMELINE = "TIMELINE"
    DESIRED_DEPTH = "DESIRED_DEPTH"
    LEARNING_PREFERENCE = "LEARNING_PREFERENCE"

    # Canonical aliases so both naming conventions resolve to the 7 enum members
    PROJECT_CONTEXT = "TARGET_OUTCOME"
    TARGET_DEPTH = "DESIRED_DEPTH"
    TIME_BUDGET = "TIME_COMMITMENT"
    DEADLINE_CONSTRAINTS = "TIMELINE"
    LEARNING_STYLE = "LEARNING_PREFERENCE"
    ASSESSMENT_PREFERENCE = "PRACTICAL_EXPERIENCE"

    @classmethod
    def _missing_(cls, value: object) -> "DiagnosticDimension | None":
        if isinstance(value, str):
            cleaned = value.strip().upper()
            mapped = LEGACY_DIAGNOSTIC_DIMENSION_ALIASES.get(cleaned)
            if mapped is not None:
                return cls(mapped)
        return None


LEGACY_DIAGNOSTIC_DIMENSION_ALIASES: dict[str, str] = {
    "KNOWLEDGE_BASELINE": DiagnosticDimension.PRIOR_KNOWLEDGE.value,
    "PRIOR_EXPOSURE": DiagnosticDimension.PRIOR_KNOWLEDGE.value,
    "TECH_STACK_DEPTH": DiagnosticDimension.DESIRED_DEPTH.value,
    "TARGET_DEPTH": DiagnosticDimension.DESIRED_DEPTH.value,
    "LEARNING_STYLE": DiagnosticDimension.LEARNING_PREFERENCE.value,
    "LEARNING_CONSTRAINTS": DiagnosticDimension.TIME_COMMITMENT.value,
    "TIME_BUDGET": DiagnosticDimension.TIME_COMMITMENT.value,
    "TIMELINE_URGENCY": DiagnosticDimension.TIMELINE.value,
    "DEADLINE_CONSTRAINTS": DiagnosticDimension.TIMELINE.value,
    "PROJECT_CONTEXT": DiagnosticDimension.TARGET_OUTCOME.value,
    "ASSESSMENT_PREFERENCE": DiagnosticDimension.PRACTICAL_EXPERIENCE.value,
    "GENERAL": DiagnosticDimension.PRIOR_KNOWLEDGE.value,
}

VALID_DIAGNOSTIC_DIMENSIONS: frozenset[str] = frozenset(
    member.value for member in DiagnosticDimension
)


def normalize_diagnostic_dimension(raw: str | DiagnosticDimension | None) -> str:
    """Normalize any raw or legacy diagnostic dimension string into one of the 7 canonical values."""
    if isinstance(raw, DiagnosticDimension):
        return raw.value
    cleaned = str(raw or "").strip().upper()
    if not cleaned:
        return DiagnosticDimension.PRIOR_KNOWLEDGE.value
    try:
        return DiagnosticDimension(cleaned).value
    except ValueError:
        return LEGACY_DIAGNOSTIC_DIMENSION_ALIASES.get(
            cleaned,
            DiagnosticDimension.PRIOR_KNOWLEDGE.value,
        )


def audit_clarification_dimensions(
    records: Sequence[str | dict[str, Any]],
) -> dict[str, Any]:
    """Read-only audit helper inspecting stored clarification JSON payloads for dimension drift."""
    canonical_counts: dict[str, int] = {dim.value: 0 for dim in DiagnosticDimension}
    alias_counts: dict[str, int] = {}
    unknown_counts: dict[str, int] = {}
    total_records = 0

    for item in records:
        total_records += 1
        payload: dict[str, Any] = {}
        if isinstance(item, str):
            try:
                parsed = json.loads(item)
                if isinstance(parsed, dict):
                    payload = parsed
            except Exception:
                continue
        elif isinstance(item, dict):
            payload = item

        dims_found: list[str] = []
        for gap in payload.get("information_gaps", []) or []:
            if isinstance(gap, dict) and gap.get("dimension"):
                dims_found.append(str(gap["dimension"]))
        for fact in payload.get("facts", []) or []:
            if isinstance(fact, dict) and fact.get("dimension"):
                dims_found.append(str(fact["dimension"]))
        for q in payload.get("questions", []) or []:
            if isinstance(q, dict) and q.get("diagnostic_dimension"):
                dims_found.append(str(q["diagnostic_dimension"]))

        for raw_dim in dims_found:
            clean_dim = raw_dim.strip().upper()
            if clean_dim in canonical_counts:
                canonical_counts[clean_dim] += 1
            elif clean_dim in LEGACY_DIAGNOSTIC_DIMENSION_ALIASES:
                alias_counts[clean_dim] = alias_counts.get(clean_dim, 0) + 1
            else:
                unknown_counts[clean_dim] = unknown_counts.get(clean_dim, 0) + 1

    return {
        "total_records": total_records,
        "canonical_counts": canonical_counts,
        "legacy_alias_counts": alias_counts,
        "unknown_counts": unknown_counts,
        "is_clean": len(unknown_counts) == 0,
    }


class ClarificationQuestionLLMOutput(BaseModel):
    """Pure LLM output schema for a single clarification question (excludes server/session fields)."""

    text: str = Field(..., min_length=1, description="Nội dung câu hỏi chẩn đoán bằng tiếng Việt.")
    question_type: Literal["single_choice", "multiple_choice", "text"] = Field(
        default="single_choice",
        description="Loại câu hỏi: single_choice | multiple_choice | text.",
    )
    options: list[str] = Field(
        default_factory=list,
        description="Tối đa 4 phương án chuyên môn cho câu hỏi trắc nghiệm; mảng rỗng [] cho câu hỏi text.",
    )
    question_purpose: str = Field(
        default="Làm rõ bối cảnh và nhu cầu cá nhân hóa lộ trình học tập.",
        description="Mục đích sư phạm của câu hỏi.",
    )
    expected_answer_format: str = Field(
        default="Chọn 1 đáp án phù hợp nhất.",
        description="Định dạng câu trả lời mong đợi.",
    )
    diagnostic_dimension: DiagnosticDimension = Field(
        default=DiagnosticDimension.PRIOR_KNOWLEDGE,
        description="Chiều chẩn đoán chuẩn thuộc 7 giá trị canonical.",
    )

    @model_validator(mode="before")
    @classmethod
    def _coerce_llm_question_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        copied = dict(data)
        if not copied.get("text") and copied.get("question"):
            copied["text"] = str(copied["question"]).strip()
        if not copied.get("question_type") and copied.get("type"):
            copied["question_type"] = str(copied["type"]).strip().lower()
        if not copied.get("question_purpose") and copied.get("purpose"):
            copied["question_purpose"] = str(copied["purpose"]).strip()
        raw_qtype = str(copied.get("question_type") or "single_choice").strip().lower()
        if raw_qtype not in ("single_choice", "multiple_choice", "text"):
            raw_opts = copied.get("options")
            copied["question_type"] = (
                "single_choice" if isinstance(raw_opts, list) and len(raw_opts) >= 2 else "text"
            )
        else:
            copied["question_type"] = raw_qtype

        raw_opts = copied.get("options")
        if isinstance(raw_opts, list):
            clean_opts: list[str] = []
            for opt in raw_opts:
                if isinstance(opt, dict):
                    label = str(opt.get("label", "")).strip()
                else:
                    label = str(getattr(opt, "label", opt)).strip()
                if label:
                    clean_opts.append(label)
            copied["options"] = clean_opts
        else:
            copied["options"] = []

        copied["diagnostic_dimension"] = DiagnosticDimension(
            normalize_diagnostic_dimension(copied.get("diagnostic_dimension"))
        )
        return copied


class ClarificationQuestionsLLMOutput(BaseModel):
    """Pure LLM output schema for Goal Clarifier stage (T2.3 / B6)."""

    questions: list[ClarificationQuestionLLMOutput] = Field(
        default_factory=list,
        description="Danh sách 0..3 câu hỏi chẩn đoán tiếng Việt; 0 câu nếu không còn khoảng trống thông tin.",
    )
    initial_assumptions: list[str] = Field(
        default_factory=list,
        description="Các giả định ban đầu nếu chưa có đủ thông tin từ người học.",
    )
    missing_dimensions: list[DiagnosticDimension] = Field(
        default_factory=list,
        description="Các chiều chẩn đoán còn thiếu thuộc 7 giá trị chuẩn DiagnosticDimension.",
    )

    @model_validator(mode="before")
    @classmethod
    def _coerce_llm_questions_wrapper(cls, data: Any) -> Any:
        if isinstance(data, list):
            return {"questions": data}
        if isinstance(data, dict):
            copied = dict(data)
            if "questions" not in copied:
                for alt in ("data", "result", "items", "clarification_questions"):
                    if isinstance(copied.get(alt), list):
                        copied["questions"] = copied.pop(alt)
                        break
            if isinstance(copied.get("missing_dimensions"), list):
                copied["missing_dimensions"] = [
                    DiagnosticDimension(normalize_diagnostic_dimension(d))
                    for d in copied["missing_dimensions"]
                ]
            return copied
        return data


class ClarificationFollowupLLMOutput(BaseModel):
    """Pure LLM output schema for Goal Clarifier round-2 follow-up (strictly 1 question)."""

    questions: list[ClarificationQuestionLLMOutput] = Field(
        ...,
        min_length=1,
        max_length=1,
        description="Danh sách gồm ĐÚNG 1 câu hỏi follow-up bằng tiếng Việt.",
    )

    @model_validator(mode="before")
    @classmethod
    def _coerce_followup_wrapper(cls, data: Any) -> Any:
        if isinstance(data, list):
            return {"questions": data}
        if isinstance(data, dict):
            copied = dict(data)
            if "questions" not in copied:
                for alt in ("data", "result", "items", "clarification_questions"):
                    if isinstance(copied.get(alt), list):
                        copied["questions"] = copied.pop(alt)
                        break
            return copied
        return data


class MilestoneItemLLMOutput(BaseModel):
    """LLM output schema for a single adaptive Milestone (T2.1 / B1)."""

    sequence_order: int = Field(
        ..., ge=1, description="Thứ tự liên tục của cột mốc bắt đầu từ 1 (1, 2, ...)."
    )
    title: str = Field(
        ..., min_length=1, description="Tên cột mốc ngắn gọn, rõ ràng bằng tiếng Việt."
    )
    description: str = Field(
        default="", description="Mô tả trọng tâm kiến thức và phạm vi của cột mốc."
    )
    learning_outcomes: list[str] = Field(
        ...,
        min_length=1,
        description="Danh sách kết quả học tập đo lường được (gắn với mã M{sequence_order}-O{index} ở bước sau).",
    )
    completion_criteria: str = Field(
        ...,
        min_length=1,
        description="Tiêu chí hoàn thành cụ thể, kiểm chứng được của cột mốc.",
    )
    estimated_effort_minutes: int = Field(
        ...,
        ge=15,
        description="Tổng thời lượng ước tính thực tế cho cột mốc (phút, >= 15; thường 60..600 phút).",
    )
    required_concepts: list[str] = Field(
        default_factory=list,
        description="Chỉ gồm các concept_id xác thực có trong Knowledge Base / kết quả công cụ.",
    )
    unverified_concepts: list[str] = Field(
        default_factory=list,
        description="Các khái niệm cần học nhưng chưa có trong Knowledge Base catalog.",
    )
    dependencies: list[int] = Field(
        default_factory=list,
        description="Danh sách sequence_order của các cột mốc tiền đề bắt buộc trước cột mốc này.",
    )


class MilestoneGenerationLLMOutput(BaseModel):
    """LLM output schema for Milestone Planner stage with required scope_summary & deferred_scope (T2.1 / B3)."""

    milestones: list[MilestoneItemLLMOutput] = Field(
        ..., min_length=1, description="Chuỗi cột mốc học tập tuần tự theo thứ tự tiên quyết."
    )
    scope_summary: str = Field(
        ...,
        min_length=1,
        description="Tóm tắt phạm vi lộ trình (FULL_SCOPE bao phủ toàn bộ; FIT_CAPACITY nêu rõ phần giữ lại và giới hạn).",
    )
    deferred_scope: list[str] = Field(
        ...,
        description="Danh sách nội dung bị hoãn lại khi strategy=FIT_CAPACITY; rỗng [] khi FULL_SCOPE.",
    )


class TaskDependencyLLMOutput(BaseModel):
    """Directed prerequisite edge between two proposed tasks."""

    predecessor_id: str = Field(
        ..., min_length=1, description="Mã task_id tiền đề (ví dụ T1) phải học trước."
    )
    successor_id: str = Field(
        ..., min_length=1, description="Mã task_id kế tiếp (ví dụ T2) học sau."
    )
    is_mandatory: bool = Field(
        default=True, description="True nếu thứ tự phụ thuộc là bắt buộc trong DAG."
    )


class TaskItemLLMOutput(BaseModel):
    """LLM output schema for a single atomic study task (T2.1 / B2 & T2.2 / B4)."""

    task_id: str = Field(
        ...,
        pattern=r"^T[1-9][0-9]*$",
        description="Mã định danh tuần tự của nhiệm vụ dạng T1, T2, T3, ...",
    )
    milestone_id: str = Field(
        ..., min_length=1, description="UUID của cột mốc APPROVED chứa nhiệm vụ này."
    )
    title: str = Field(
        ..., min_length=1, description="Tiêu đề nhiệm vụ học tập súc tích bằng tiếng Việt."
    )
    description: str = Field(
        default="", description="Mô tả nội dung cần học hoặc thực hành trong phiên."
    )
    task_type: Literal["THEORY", "PRACTICE", "REVIEW", "PROJECT"] = Field(
        default="PRACTICE",
        description="Loại nhiệm vụ theo tiến trình sư phạm THEORY -> PRACTICE -> REVIEW -> PROJECT.",
    )
    learning_objective: str = Field(
        default="", description="Mục tiêu học tập cụ thể đạt được sau nhiệm vụ."
    )
    completion_criteria: str = Field(
        default="", description="Tiêu chí hoàn thành đo lường được của nhiệm vụ."
    )
    resource_ids: list[str] = Field(
        default_factory=list,
        max_length=3,
        description="Tối đa 3 resource_id lấy trực tiếp từ kết quả tool get_learning_resources_and_guidance; [] nếu không có.",
    )
    concept_ids: list[str] = Field(
        default_factory=list,
        description="Danh sách concept_id của cột mốc được bao phủ bởi nhiệm vụ này.",
    )
    covered_outcome_ids: list[str] = Field(
        ...,
        min_length=1,
        description="Danh sách mã outcome dạng M{sequence}-O{index} mà nhiệm vụ này bao phủ.",
    )
    estimated_minutes: int = Field(
        ...,
        ge=AI_BLOCK_MIN_MINUTES,
        le=AI_BLOCK_MAX_MINUTES,
        description="Thời lượng học tập (30..120 phút), bám theo opt_session_minutes và effort từ context.",
    )


class TaskProposalLLMOutput(BaseModel):
    """LLM output schema for Task Decomposer stage (T2.1 / B2)."""

    tasks: list[TaskItemLLMOutput] = Field(
        ...,
        min_length=1,
        description="Danh sách nhiệm vụ nguyên tử bao phủ toàn bộ outcomes/concepts.",
    )
    dependencies: list[TaskDependencyLLMOutput] = Field(
        default_factory=list, description="Đồ thị phụ thuộc DAG không chu trình giữa các task_id."
    )


class JudgeIssueLLMOutput(BaseModel):
    """Single pedagogical issue reported by Tier 3 Judge (T2.1 / B1)."""

    severity: Literal["INFO", "WARNING", "CRITICAL", "ERROR", "FAIL"] = Field(
        default="WARNING",
        description="Mức độ nghiêm trọng: INFO | WARNING (khuyên sửa) | CRITICAL | ERROR | FAIL (chặn đạt).",
    )
    category: str = Field(
        ...,
        min_length=1,
        description="Nhóm lỗi sư phạm (vd: PREREQUISITE_ORDER, THEORY_PRACTICE_BALANCE, COGNITIVE_LOAD, CLARITY).",
    )
    message: str = Field(
        ..., min_length=1, description="Mô tả cụ thể vấn đề sư phạm bằng tiếng Việt."
    )
    evidence: str | None = Field(
        default=None,
        description="Bằng chứng cụ thể trích từ proposal hoặc milestone chứng minh lỗi này.",
    )
    task_ref: str | None = Field(
        default=None,
        description="Mã task_id hoặc UUID của task bị lỗi trong proposal; để null nếu là lỗi tổng thể toàn lộ trình.",
    )


class PedagogicalJudgeLLMOutput(BaseModel):
    """LLM output schema for Tier 3 Pedagogical Judge; server derives PASS/FAIL status (T2.1 / B1)."""

    score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Điểm thẩm định sư phạm 0..100 theo rubric neo mốc 0/40/60/80/100 (< 60 tương ứng FAIL ở máy chủ).",
    )
    issues: list[JudgeIssueLLMOutput] = Field(
        default_factory=list,
        description="Danh sách các vấn đề sư phạm có bằng chứng cụ thể; rỗng [] nếu đạt xuất sắc.",
    )

    def derive_status(self) -> Literal["PASS", "FAIL"]:
        has_blocking_issue = any(
            issue.severity in ("CRITICAL", "ERROR", "FAIL") for issue in self.issues
        )
        if self.score >= 60 and not has_blocking_issue:
            return "PASS"
        return "FAIL"


class CriticIssueLLMOutput(BaseModel):
    """Single quality issue emitted by an independent critic or arbiter (T2.1)."""

    code: str = Field(..., min_length=1, description="Mã lỗi chuẩn hóa (vd: PREREQUISITE_ORDER).")
    severity: Literal["WARNING", "ERROR"] = Field(
        default="WARNING", description="Mức độ: WARNING (cảnh báo) hoặc ERROR (lỗi nặng cần sửa)."
    )
    message: str = Field(..., min_length=1, description="Mô tả ngắn gọn vấn đề kèm dẫn chứng.")
    evidence: str | None = Field(
        default=None, description="Bằng chứng cụ thể trích từ payload (tên/ID mục bị lỗi)."
    )
    task_ref: str | None = Field(
        default=None, description="Mã task_id/UUID hoặc mã cột mốc liên quan nếu có."
    )
    suggested_fix: str | None = Field(
        default=None, description="Đề xuất khắc phục cụ thể để vòng tự sửa lỗi áp dụng."
    )


class CriticQualityLLMOutput(BaseModel):
    """Pydantic schema for dual quality critics and arbiter outputs (T2.1)."""

    status: Literal["PASS", "WARN", "FAIL"] = Field(
        ..., description="Kết luận thẩm định: PASS | WARN | FAIL."
    )
    score: int | float | None = Field(
        default=None, ge=0, le=100, description="Điểm chất lượng 0..100 theo rubric."
    )
    issues: list[CriticIssueLLMOutput] = Field(
        default_factory=list, description="Danh sách lỗi/cảnh báo có bằng chứng cụ thể."
    )


class ClarificationOption(BaseModel):
    id: str
    label: str


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
        description="Loại câu hỏi: 'single_choice' (trắc nghiệm chọn 1 đáp án), 'multiple_choice' (trắc nghiệm chọn nhiều đáp án) hoặc 'text' (tự luận ngắn).",
    )
    options: list[ClarificationOption] = Field(
        default_factory=list,
        description="Danh sách gồm 3 đến 5 phương án lựa chọn thực tế, chuyên môn khi question_type='single_choice' hoặc 'multiple_choice'. Để mảng rỗng [] khi question_type='text'.",
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
            elif isinstance(copied.get("options"), list):
                copied["options"] = [
                    option
                    if isinstance(option, (ClarificationOption, dict))
                    else {"id": f"{qid}-opt-{index + 1}", "label": str(option)}
                    for index, option in enumerate(copied["options"])
                ]
            return copied
        return data


# Alias requested by design spec while preserving ClarificationQuestion compatibility
ClarificationQuestionItem = ClarificationQuestion


class ClarificationQuestionsResponse(BaseModel):
    questions: list[ClarificationQuestion] = Field(default_factory=list)
    questions_version: str = "v2.0"
    session_id: UUID | None = None
    round: int = Field(default=1, ge=1, le=2)
    status: str = "WAITING_ANSWER"
    information_gaps: list[dict[str, Any]] = Field(default_factory=list)
    next_turn_quota_cost: int = Field(default=0, ge=0, le=1)

    @model_validator(mode="before")
    @classmethod
    def _coerce_input(cls, data: Any) -> Any:
        if isinstance(data, list):
            return {"questions": data}
        if isinstance(data, dict):
            if "questions" not in data:
                for k in ("data", "result", "items", "clarification_questions"):
                    if isinstance(data.get(k), list):
                        copied = dict(data)
                        copied["questions"] = copied.pop(k)
                        return copied
        return data


class ClarificationAnswerItem(BaseModel):
    question_id: str
    question_text: str | None = None
    answer: str = ""
    selected_option_ids: list[str] = Field(default_factory=list)
    free_text: str | None = None

    @field_validator("answer", mode="before")
    @classmethod
    def normalize_answer(cls, v: Any) -> str:
        if isinstance(v, list):
            return ", ".join(str(item).strip() for item in v if str(item).strip())
        if isinstance(v, str):
            trimmed = v.strip()
            if trimmed.startswith("[") and trimmed.endswith("]"):
                try:
                    parsed = json.loads(trimmed)
                    if isinstance(parsed, list):
                        return ", ".join(str(item).strip() for item in parsed if str(item).strip())
                except Exception:
                    pass
            return trimmed
        return str(v) if v is not None else ""

    @model_validator(mode="after")
    def populate_legacy_answer(self) -> "ClarificationAnswerItem":
        if not self.answer.strip() and self.free_text:
            self.answer = self.free_text.strip()
        return self


class ClarificationContextPayload(BaseModel):
    """Structured diagnostic context stored in Goal.clarification_context (FR-GOAL-002)."""

    schema_version: int = 2
    session_id: str | None = None
    status: Literal["NOT_REQUIRED", "ANSWERED", "PARTIAL", "SKIPPED"] = "ANSWERED"
    questions_version: str = "v2.0"
    answers: list[dict[str, Any]] = Field(default_factory=list)
    skipped_questions: list[str] = Field(default_factory=list)
    unresolved_assumptions: list[str] = Field(default_factory=list)
    facts: list[dict[str, Any]] = Field(default_factory=list)
    information_gaps: list[dict[str, Any]] = Field(default_factory=list)
    contradictions: list[dict[str, Any]] = Field(default_factory=list)
    input_provenance: dict[str, str] = Field(default_factory=dict)
    weekly_commitment_hours: float | None = None
    rounds_completed: int = 0
    synthesized_text: str = ""
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_json_string(self) -> str:
        return json.dumps(self.model_dump(mode="json"), ensure_ascii=False)

    def to_json_str(self) -> str:
        return self.to_json_string()


@dataclass(frozen=True, slots=True)
class ClarificationTurnResultDTO:
    goal: Goal
    session_id: UUID | None
    round: int
    status: str
    questions: tuple[ClarificationQuestion, ...] = ()
    information_gaps: tuple[dict[str, Any], ...] = ()
    next_turn_quota_cost: int = 0


def parse_clarification_context(
    raw: str | None,
    *,
    prior_knowledge_level: str = "BEGINNER",
) -> ClarificationContextPayload:
    """Parse Goal.clarification_context from JSON or legacy plain text with safe defaults."""
    if raw is None or not raw.strip():
        return ClarificationContextPayload(
            status="SKIPPED",
            schema_version=1,
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
        schema_version=1,
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
    is_existing: bool = False


@dataclass(frozen=True, slots=True)
class MilestoneInputItemDTO:
    title: str
    description: str | None = None
    sequence_order: int = 1
    milestone_id: UUID | None = None
    learning_outcomes: tuple[str, ...] = ()
    completion_criteria: str | None = None
    estimated_effort_minutes: int | None = None
    required_concepts: tuple[str, ...] = ()
    unverified_concepts: tuple[str, ...] = ()
    prerequisite_milestone_ids: tuple[UUID, ...] = ()


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
    calendar_sync_status: str = "NOT_CONNECTED"
    backlog_unscheduled_tasks_count: int = 0


@dataclass(frozen=True, slots=True)
class RoadmapDetailDTO:
    roadmap: Roadmap
    goal: Goal | None
    milestones: list[Milestone]
    official_schedule: OfficialSchedule | None
    current_draft_proposal: ScheduleProposal | None
    scheduled_tasks: list[ExistingScheduledTaskDTO] = field(default_factory=list)
