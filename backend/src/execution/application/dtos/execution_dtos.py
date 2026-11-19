from dataclasses import dataclass, field
from datetime import date, datetime
from uuid import UUID

from src.execution.domain.models.study_session import (
    SessionTask,
    StudyNote,
    StudySession,
)
from src.execution.domain.models.task import Task


@dataclass(frozen=True, slots=True)
class TaskViewDTO:
    """Read model for a Task enriched with derived OVERDUE/BLOCKED/STALLED flags & predecessors."""

    task: Task
    is_overdue: bool
    is_blocked: bool
    is_stalled: bool
    predecessor_ids: tuple[UUID, ...] = ()
    priority_rank: int | None = None
    out_degree: int | None = None
    milestone_sequence: int | None = None
    roadmap_title: str | None = None
    milestone_title: str | None = None
    learning_outcomes: tuple[str, ...] = ()
    completion_criteria: str | None = None


@dataclass(frozen=True, slots=True)
class WeeklyScheduleItemDTO:
    """Single block in `/api/v1/tasks/schedule/week` combining Planning block & Execution task."""

    block_id: UUID
    roadmap_id: UUID
    roadmap_title: str
    roadmap_status: str
    official_schedule_id: UUID
    task_id: UUID | None
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
    task: TaskViewDTO | None = None


@dataclass(frozen=True, slots=True)
class WeeklyScheduleViewDTO:
    week_start: date
    week_end: date
    items: tuple[WeeklyScheduleItemDTO, ...] = ()


@dataclass(frozen=True, slots=True)
class StudySessionViewDTO:
    session: StudySession
    session_tasks: tuple[SessionTask, ...] = ()
    notes: tuple[StudyNote, ...] = ()
    scratchpad_content: str = ""
    takeaway_content: str | None = None
    takeaway_self_confidence: int | None = None


@dataclass(frozen=True, slots=True)
class TodayFocusViewDTO:
    local_date: date
    active_session: StudySessionViewDTO | None
    pending_takeaway_session: StudySessionViewDTO | None
    focus_task: TaskViewDTO | None
    today_queue: tuple[TaskViewDTO, ...] = field(default_factory=tuple)
    overdue_tasks_count: int = 0
    completed_sessions_today: int = 0
    studied_minutes_today: int = 0


@dataclass(frozen=True, slots=True)
class StickyNoteViewDTO:
    id: UUID
    user_id: UUID
    task_id: UUID | None
    title: str
    body: str
    color: str
    pinned: bool
    pos_x: float | None
    pos_y: float | None
    z_index: int | None
    origin_session_id: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class StudioConfigViewDTO:
    scene: str
    clock_style: str
    clock_size: str
    show_seconds: bool
    show_in_tab_title: bool
    tab_guard_enabled: bool
    zen_lock_enabled: bool
    blocklist: tuple[str, ...] = ()
    parking_lot: tuple[dict[str, object], ...] = ()
    updated_at: datetime | None = None
