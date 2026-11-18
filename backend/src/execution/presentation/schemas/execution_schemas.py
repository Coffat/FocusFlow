from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class TaskResponse(BaseModel):
    id: UUID
    roadmap_id: UUID
    milestone_id: UUID
    official_schedule_id: UUID | None = None
    parent_task_id: UUID | None = None
    concept_id: str | None = None
    title: str
    description: str | None = None
    estimated_minutes: int
    learning_resources: list[dict[str, object]] = Field(default_factory=list)
    scheduled_date: date | None = None
    scheduled_start: datetime | None = None
    scheduled_end: datetime | None = None
    status: str
    completed_at: datetime | None = None
    reschedule_count: int
    is_overdue: bool
    is_blocked: bool
    is_stalled: bool
    predecessor_ids: list[UUID] = Field(default_factory=list)
    roadmap_title: str | None = None
    priority_rank: int | None = None
    out_degree: int | None = None
    milestone_sequence: int | None = None
    created_at: datetime
    updated_at: datetime


class CreateTaskRequest(BaseModel):
    roadmap_id: UUID
    milestone_id: UUID
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    estimated_minutes: int = 30
    scheduled_date: date | None = None
    scheduled_start: datetime | None = None
    scheduled_end: datetime | None = None
    concept_id: str | None = None
    learning_resources: list[dict[str, object]] = Field(default_factory=list)
    confirm_soft_overflow: bool = False


class UpdateTaskRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    estimated_minutes: int | None = None


class CompleteTaskRequest(BaseModel):
    takeaway: str | None = None
    self_confidence: int | None = Field(default=None, ge=1, le=5)


class RescheduleTaskRequest(BaseModel):
    scheduled_date: date | None = None
    scheduled_start: datetime | None = None
    scheduled_end: datetime | None = None
    reason: str | None = None
    allow_stalled_commitment: bool = False
    confirm_soft_overflow: bool = False


class AddTaskDependencyRequest(BaseModel):
    predecessor_id: UUID
    is_mandatory: bool = True


class TaskDependencyResponse(BaseModel):
    id: UUID
    predecessor_id: UUID
    successor_id: UUID
    roadmap_id: UUID
    is_mandatory: bool
    created_at: datetime


class WeeklyScheduleItemResponse(BaseModel):
    block_id: UUID
    roadmap_id: UUID
    roadmap_title: str
    roadmap_status: str
    official_schedule_id: UUID
    task_id: UUID | None = None
    sequence_in_task: int
    block_type: str
    block_date: date
    start_time: datetime
    end_time: datetime
    scheduled_duration_minutes: int
    block_status: str
    sync_status: str
    is_protected: bool
    placement_rationale: str | None = None
    task: TaskResponse | None = None


class WeeklyScheduleResponse(BaseModel):
    week_start: date
    week_end: date
    items: list[WeeklyScheduleItemResponse] = Field(default_factory=list)


class SessionTaskResponse(BaseModel):
    id: UUID
    session_id: UUID
    task_id: UUID
    allocated_minutes: int
    actual_minutes: int
    status_after_session: str
    notes: str | None = None


class StudyNoteResponse(BaseModel):
    id: UUID
    note_type: str
    content: str
    self_confidence: int | None = None
    alignment_flag: str
    verification_status: str
    created_at: datetime
    updated_at: datetime


class StudySessionResponse(BaseModel):
    id: UUID
    user_id: UUID
    roadmap_id: UUID
    started_at: datetime
    ended_at: datetime | None = None
    planned_minutes: int
    actual_minutes: int
    status: str
    last_heartbeat_at: datetime
    session_mode: str
    pending_takeaway: bool
    checkin_time_sufficiency: str | None = None
    checkin_perceived_difficulty: int | None = None
    checkin_focus_level: int | None = None
    scratchpad_content: str = ""
    takeaway_content: str | None = None
    takeaway_self_confidence: int | None = None
    session_tasks: list[SessionTaskResponse] = Field(default_factory=list)
    notes: list[StudyNoteResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class StartSessionRequest(BaseModel):
    task_ids: list[UUID] = Field(..., min_length=1)
    session_mode: Literal["STANDARD", "MVS"] = "STANDARD"
    planned_minutes: int | None = None


class HeartbeatSessionRequest(BaseModel):
    actual_minutes: int | None = Field(default=None, ge=0)
    scratchpad_content: str | None = None


class FinalizeSessionRequest(BaseModel):
    early_stop: bool = False
    completed_task_ids: list[UUID] = Field(default_factory=list)
    takeaway: str | None = None
    self_confidence: int | None = Field(default=None, ge=1, le=5)
    scratchpad_content: str | None = None
    actual_minutes: int | None = Field(default=None, ge=0)
    checkin_time_sufficiency: Literal["TOO_SHORT", "JUST_RIGHT", "TOO_LONG"] | None = None
    checkin_perceived_difficulty: int | None = Field(default=None, ge=1, le=5)
    checkin_focus_level: int | None = Field(default=None, ge=1, le=5)


class ResolveTakeawayRequest(BaseModel):
    takeaway: str
    self_confidence: int | None = Field(default=None, ge=1, le=5)


class TodayFocusResponse(BaseModel):
    local_date: date
    active_session: StudySessionResponse | None = None
    pending_takeaway_session: StudySessionResponse | None = None
    focus_task: TaskResponse | None = None
    today_queue: list[TaskResponse] = Field(default_factory=list)
    overdue_tasks_count: int = 0
