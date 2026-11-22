from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ExportUserDTO(BaseModel):
    """Sanitized user profile snapshot for GDPR export (strictly excludes secrets/hashes)."""

    id: UUID
    email: str
    full_name: str
    timezone: str
    role: str
    tier: str
    created_at: datetime


class ExportLearnerProfileDTO(BaseModel):
    """Learner SRL profile metrics snapshot."""

    optimal_focus_duration_mins: int
    peak_productivity_slots: list[str]
    estimation_bias_factor: float
    weekly_completion_rate: float
    total_completed_sessions: int
    is_cold_start: bool
    last_aggregated_at: datetime | None = None


class ExportLearnerMemoryItemDTO(BaseModel):
    """Learner memory item snapshot."""

    id: UUID
    memory_key: str
    value: dict[str, Any]
    category: str
    epistemic_level: str
    confidence: float
    sample_size: int
    status: str
    updated_at: datetime


class ExportAvailabilitySlotDTO(BaseModel):
    """Single day availability slot snapshot."""

    day_of_week: str
    enabled: bool
    quota_hours: float
    preferred_period: str
    min_session_minutes: int
    time_slots: list[dict[str, Any]] = Field(default_factory=list)


class ExportAvailabilityDTO(BaseModel):
    """User availability settings & slots snapshot."""

    mode: str
    calendar_integration_mode: str
    min_session_minutes: int
    total_weekly_hours: float
    days: list[ExportAvailabilitySlotDTO] = Field(default_factory=list)


class ExportRoadmapDTO(BaseModel):
    """User roadmap metadata snapshot."""

    roadmap_id: UUID
    title: str
    status: str
    target_date: date | None = None
    weekly_reschedule_budget: int
    weekly_reschedule_used: int


class ExportAnalyticsSummaryDTO(BaseModel):
    """Aggregated analytics summary snapshot."""

    total_focused_hours: float
    weekly_study_hours: float
    task_completion_rate: float
    plan_adherence_rate: float
    completed_tasks_count: int
    total_tasks_count: int
    active_streak_days: int
    average_focus_score: float


class ExportStudySessionItemDTO(BaseModel):
    """Bounded study session record for GDPR export."""

    id: UUID
    roadmap_id: UUID
    session_mode: str
    status: str
    planned_minutes: int
    actual_minutes: int
    started_at: datetime
    ended_at: datetime | None = None
    created_at: datetime


class ExportTaskItemDTO(BaseModel):
    """Bounded task record for GDPR export."""

    id: UUID
    roadmap_id: UUID
    milestone_id: UUID
    title: str
    description: str | None = None
    estimated_minutes: int
    scheduled_date: date | None = None
    status: str
    completed_at: datetime | None = None
    created_at: datetime


class AccountDataExportDTO(BaseModel):
    """GDPR Article 20 portable JSON export payload for the authenticated learner (FE-MOCK-03)."""

    schema_version: str = "1.0"
    exported_at: datetime
    user: ExportUserDTO
    learner_profile: ExportLearnerProfileDTO | None = None
    learner_memory: list[ExportLearnerMemoryItemDTO] = Field(default_factory=list)
    availability: ExportAvailabilityDTO | None = None
    roadmaps: list[ExportRoadmapDTO] = Field(default_factory=list)
    analytics_summary: ExportAnalyticsSummaryDTO
    study_sessions_count: int
    study_sessions: list[ExportStudySessionItemDTO] = Field(default_factory=list)
    tasks_count: int
    tasks: list[ExportTaskItemDTO] = Field(default_factory=list)
