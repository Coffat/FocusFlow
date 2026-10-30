from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class GoalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    title: str
    raw_description: str | None = None
    target_date: date | None = None
    status: str
    created_at: datetime
    updated_at: datetime


class MilestoneUpsertItemSchema(BaseModel):
    id: UUID | None = None
    milestone_id: UUID | None = None
    sequence_order: int = Field(default=1, ge=1)
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None


class MilestoneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    roadmap_id: UUID
    sequence_order: int
    title: str
    description: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime


class MilestoneListResponse(BaseModel):
    roadmap_id: UUID
    milestones: list[MilestoneResponse]


class UpdateMilestonesRequest(BaseModel):
    milestones: list[MilestoneUpsertItemSchema] = Field(..., min_length=1)


class CreateRoadmapRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    goal_title: str | None = None
    goal_description: str | None = None
    start_date: date | None = None
    target_date: date | None = None


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


class ProposedTaskItemSchema(BaseModel):
    task_id: UUID | str | None = None
    milestone_id: UUID | str | None = None
    milestone_sequence_order: int | None = None
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    estimated_minutes: int = Field(default=45)
    scheduled_date: date | str | None = None
    scheduled_start: datetime | str | None = None
    scheduled_end: datetime | str | None = None
    prerequisite_ids: list[UUID | str] = Field(default_factory=list)


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


class ScheduleProposalResponse(BaseModel):
    id: UUID
    roadmap_id: UUID
    user_id: UUID
    status: str
    is_valid: bool = True
    has_soft_overflow: bool = False
    tasks: list[dict[str, Any]] = Field(default_factory=list)
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


class OfficialScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    roadmap_id: UUID
    total_sessions: int
    total_planned_minutes: int
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
