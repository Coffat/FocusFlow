from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.planning.application.dtos.planning_dtos import (
    ClarificationAnswerItem,
    ClarificationQuestion,
    ClarificationQuestionsResponse,
)

__all__ = [
    "ClarificationAnswerItem",
    "ClarificationQuestion",
    "ClarificationQuestionsResponse",
]


class GoalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    title: str
    raw_description: str | None = None
    target_date: date | None = None
    status: str
    prior_knowledge_level: str = "BEGINNER"
    clarification_context: str | None = None
    created_at: datetime
    updated_at: datetime


class CreateKnowledgeUrlRequest(BaseModel):
    title: str = Field(default="Nguồn học liệu URL", max_length=255)
    url: str = Field(..., min_length=8, max_length=2048)


class KnowledgeSourceResponse(BaseModel):
    id: UUID
    goal_id: UUID
    source_type: str
    title: str
    ingestion_status: str
    chunk_count: int
    provenance_metadata: dict[str, Any] = Field(default_factory=dict)
    error_detail: str | None = None
    created_at: datetime
    updated_at: datetime


class SubmitClarificationAnswersRequest(BaseModel):
    session_id: UUID | None = None
    round: int = Field(default=1, ge=1, le=2)
    answers: list[ClarificationAnswerItem] = Field(default_factory=list)
    skipped: bool = Field(default=False)
    skipped_question_ids: list[str] = Field(default_factory=list)
    total_questions_count: int | None = Field(default=None)


class SkipClarificationRequest(BaseModel):
    session_id: UUID | None = None
    skipped_question_ids: list[str] = Field(default_factory=list)


class SubmitClarificationAnswersResponse(BaseModel):
    goal_id: UUID
    status: str = "ANSWERED"
    clarification_context: str
    unresolved_assumptions: list[str] = Field(default_factory=list)
    session_id: UUID | None = None
    round: int = Field(default=1, ge=1, le=2)
    questions: list[ClarificationQuestion] = Field(default_factory=list)
    information_gaps: list[dict[str, Any]] = Field(default_factory=list)
    next_turn_quota_cost: int = Field(default=0, ge=0, le=1)
    message: str = "Clarification context updated successfully"


class MilestoneUpsertItemSchema(BaseModel):
    id: UUID | None = None
    milestone_id: UUID | None = None
    sequence_order: int = Field(default=1, ge=1)
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    learning_outcomes: list[str] = Field(default_factory=list)
    completion_criteria: str | None = None
    estimated_effort_minutes: int | None = Field(default=None, gt=0)
    required_concepts: list[str] = Field(default_factory=list)
    unverified_concepts: list[str] = Field(default_factory=list)
    prerequisite_milestone_ids: list[UUID] = Field(default_factory=list)


class MilestoneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    roadmap_id: UUID
    sequence_order: int
    title: str
    description: str | None = None
    learning_outcomes: list[str] = Field(default_factory=list)
    completion_criteria: str | None = None
    estimated_effort_minutes: int = 60
    required_concepts: list[str] = Field(default_factory=list)
    unverified_concepts: list[str] = Field(default_factory=list)
    prerequisite_milestone_ids: list[UUID] = Field(default_factory=list)
    status: str
    created_at: datetime
    updated_at: datetime


class MilestoneListResponse(BaseModel):
    roadmap_id: UUID
    milestones: list[MilestoneResponse]


class UpdateMilestonesRequest(BaseModel):
    milestones: list[MilestoneUpsertItemSchema] = Field(..., min_length=1)


class MilestoneGenerationRequest(BaseModel):
    generation_strategy: Literal["FULL_SCOPE", "FIT_CAPACITY"] = "FULL_SCOPE"


FactProvenanceValue = Literal[
    "USER_CONFIRMED",
    "USER_EXPLICIT",
    "SYSTEM_OBSERVED",
    "SYSTEM_DEFAULT",
    "AI_INFERRED",
]


class GoalInputProvenanceSchema(BaseModel):
    target_date: FactProvenanceValue = "SYSTEM_DEFAULT"
    prior_knowledge_level: FactProvenanceValue = "SYSTEM_DEFAULT"
    weekly_commitment_hours: FactProvenanceValue = "SYSTEM_DEFAULT"


class CreateRoadmapRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    goal_title: str | None = None
    goal_description: str | None = None
    prior_knowledge_level: str = "BEGINNER"
    start_date: date | None = None
    target_date: date | None = None
    weekly_commitment_hours: float | None = Field(default=None, ge=0.5, le=80)
    input_provenance: GoalInputProvenanceSchema = Field(default_factory=GoalInputProvenanceSchema)


class UpdateRoadmapRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    start_date: date | None = None
    target_date: date | None = None
    status: str | None = None


class RoadmapResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    goal_id: UUID
    title: str
    description: str | None = None
    status: str
    start_date: date | None = None
    target_date: date | None = None
    created_at: datetime
    updated_at: datetime
    goal: GoalResponse | None = None


class SseJobTicketResponse(BaseModel):
    job_id: UUID
    reservation_id: UUID
    roadmap_id: UUID
    job_type: str
    status: str
    stream_url: str
    jobId: str  # noqa: N815
    reservationId: str  # noqa: N815
    streamUrl: str  # noqa: N815


class LearningResourceSchema(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    url: str = Field(..., min_length=1)
    type: str = Field(default="DOCS")
    description: str | None = None


class ProposedTaskItemSchema(BaseModel):
    task_id: UUID | str | None = None
    milestone_id: UUID | str | None = None
    milestone_sequence_order: int | None = None
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    task_type: str | None = Field(default="PRACTICE")
    learning_objective: str | None = None
    completion_criteria: str | None = None
    learning_resources: list[LearningResourceSchema] = Field(default_factory=list)
    resources: list[LearningResourceSchema] = Field(default_factory=list)
    concept_ids: list[str] = Field(default_factory=list)
    covered_outcome_ids: list[str] = Field(default_factory=list)
    estimated_minutes: int = Field(default=45)
    scheduled_date: date | str | None = None
    scheduled_start: datetime | str | None = None
    scheduled_end: datetime | str | None = None
    unscheduled_reason: str | None = None
    prerequisite_ids: list[UUID | str] = Field(default_factory=list)


# Aliases for cross-module typing and test compatibility
ProposalTaskInputSchema = ProposedTaskItemSchema
ProposalTaskItemResponse = ProposedTaskItemSchema


class ProposedDependencyItemSchema(BaseModel):
    predecessor_id: UUID | str
    successor_id: UUID | str
    is_mandatory: bool = True


class ConstraintViolationSchema(BaseModel):
    task_index: int | None = None
    field: str
    rule_code: str
    expected_bound: str
    actual_value: str
    suggested_fix: str


class SoftOverflowWarningSchema(BaseModel):
    task_index: int
    task_title: str
    scheduled_date: str
    overflow_minutes: int
    message: str


class ProposedScheduleBlockSchema(BaseModel):
    task_id: UUID | str
    sequence_in_task: int = Field(..., ge=1)
    block_date: date
    scheduled_start: datetime
    scheduled_end: datetime
    scheduled_duration_minutes: int = Field(..., ge=10, le=240)


class ScheduleFeasibilitySchema(BaseModel):
    status: Literal["FEASIBLE", "PARTIAL", "INFEASIBLE"] = "FEASIBLE"
    required_minutes: int = 0
    available_minutes: int = 0
    scheduled_minutes: int = 0
    schedulable_ratio: float = 1.0
    unscheduled_minutes: int = 0
    reason_codes: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=lambda: ["APPLY"])


class ScheduleProposalResponse(BaseModel):
    id: UUID
    roadmap_id: UUID
    user_id: UUID
    status: str
    is_valid: bool = True
    has_soft_overflow: bool = False
    judge_status: str = "PASSED"
    is_partial_schedule: bool = False
    scheduled_tasks_count: int = 0
    unscheduled_tasks_count: int = 0
    unscheduled_tasks: list[dict[str, Any]] = Field(default_factory=list)
    feasibility: ScheduleFeasibilitySchema = Field(default_factory=ScheduleFeasibilitySchema)
    availability_source_metadata: dict[str, Any] = Field(default_factory=dict)
    tasks: list[dict[str, Any]] = Field(default_factory=list)
    schedule_blocks: list[ProposedScheduleBlockSchema] = Field(default_factory=list)
    dependencies: list[dict[str, Any]] = Field(default_factory=list)
    violations: list[ConstraintViolationSchema] = Field(default_factory=list)
    soft_overflow_warnings: list[SoftOverflowWarningSchema] = Field(default_factory=list)
    advisory_warnings: list[str] = Field(default_factory=list)
    diff_summary: dict[str, Any] = Field(default_factory=dict)
    proposal_data: dict[str, Any] = Field(default_factory=dict)
    applied_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class UpdateScheduleProposalRequest(BaseModel):
    tasks: list[ProposedTaskItemSchema] = Field(..., min_length=1)
    dependencies: list[ProposedDependencyItemSchema] = Field(default_factory=list)
    reject_invalid: bool = False


class CreateManualRoadmapPlanRequest(BaseModel):
    milestones: list[MilestoneUpsertItemSchema] | None = None
    tasks: list[ProposedTaskItemSchema] = Field(..., min_length=1)
    dependencies: list[ProposedDependencyItemSchema] = Field(default_factory=list)


class ApplyScheduleProposalRequest(BaseModel):
    confirm_soft_overflow: bool = False
    confirm_warnings: bool = False
    confirm_partial_schedule: bool = False


class OfficialScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    roadmap_id: UUID
    total_sessions: int
    total_planned_minutes: int
    buffer_minutes_per_week: int = 60
    recovery_window_days: int = 7
    daily_workload_cap_minutes: int = 180
    stability_weight: float = 0.8
    activated_at: datetime
    created_at: datetime
    updated_at: datetime


class ScheduledTaskResponse(BaseModel):
    task_id: UUID
    roadmap_id: UUID
    milestone_id: UUID
    title: str
    estimated_minutes: int
    scheduled_date: date | None = None
    scheduled_start: datetime | None = None
    scheduled_end: datetime | None = None
    status: str
    roadmap_target_date: date | None = None


class ApplyScheduleProposalResponse(BaseModel):
    roadmap_id: UUID
    roadmap_status: str
    official_schedule_id: UUID
    proposal_id: UUID
    proposal_status: str
    total_sessions: int
    total_planned_minutes: int
    preserved_completed_tasks_count: int
    replaced_tasks_count: int
    inserted_tasks_count: int
    affected_tasks_count: int
    total_shifted_minutes: int
    trigger_type: str
    calendar_sync_status: str = "NOT_CONNECTED"
    backlog_unscheduled_tasks_count: int = 0
    official_schedule: OfficialScheduleResponse


class RoadmapDetailResponse(BaseModel):
    id: UUID
    user_id: UUID
    goal_id: UUID
    title: str
    description: str | None = None
    status: str
    start_date: date | None = None
    target_date: date | None = None
    created_at: datetime
    updated_at: datetime
    goal: GoalResponse | None = None
    milestones: list[MilestoneResponse] = Field(default_factory=list)
    official_schedule: OfficialScheduleResponse | None = None
    scheduled_tasks: list[ScheduledTaskResponse] = Field(default_factory=list)
    current_draft_proposal: ScheduleProposalResponse | None = None
