from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from src.execution.domain.exceptions.execution_exceptions import (
    ExecutionDomainError,
    InvalidTaskDurationError,
    InvalidTaskStateError,
    TaskStalledInterventionRequiredError,
)
from src.shared_kernel.domain.base import AggregateRoot, generate_uuid7

MANUAL_TASK_MIN_MINUTES: int = 15
MANUAL_TASK_MAX_MINUTES: int = 240
STALLED_RESCHEDULE_THRESHOLD: int = 3


class TaskStatus(StrEnum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True, slots=True)
class TaskDependency:
    """Directed prerequisite edge between two tasks within the same roadmap (DAG)."""

    id: UUID = field(default_factory=generate_uuid7)
    predecessor_id: UUID = field(default_factory=generate_uuid7)
    successor_id: UUID = field(default_factory=generate_uuid7)
    roadmap_id: UUID = field(default_factory=generate_uuid7)
    is_mandatory: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.min)

    def __post_init__(self) -> None:
        if self.predecessor_id == self.successor_id:
            raise ExecutionDomainError(
                message="Nhiệm vụ không thể tự phụ thuộc vào chính nó.",
                code="DEPENDENCY_CYCLE_DETECTED",
            )


@dataclass
class Task(AggregateRoot):
    """Execution Task aggregate root enforcing SRS 6.2 lifecycle & derived flags."""

    roadmap_id: UUID = field(default_factory=generate_uuid7)
    milestone_id: UUID = field(default_factory=generate_uuid7)
    official_schedule_id: UUID | None = None
    parent_task_id: UUID | None = None
    concept_id: str | None = None
    title: str = ""
    description: str | None = None
    estimated_minutes: int = 30
    learning_resources: list[dict[str, object]] = field(default_factory=list)
    scheduled_date: date | None = None
    scheduled_start: datetime | None = None
    scheduled_end: datetime | None = None
    status: TaskStatus = TaskStatus.TODO
    completed_at: datetime | None = None
    reschedule_count: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.min)
    updated_at: datetime = field(default_factory=lambda: datetime.min)

    def __post_init__(self) -> None:
        if isinstance(self.status, str):
            self.status = TaskStatus(self.status)
        if not self.title or not self.title.strip():
            raise ExecutionDomainError(
                message="Tiêu đề nhiệm vụ (title) không được để trống.",
                code="INVALID_TASK_TITLE",
            )
        self.title = self.title.strip()
        self._validate_duration(self.estimated_minutes)
        self._validate_time_bounds(self.scheduled_start, self.scheduled_end)
        if self.reschedule_count < 0:
            raise ExecutionDomainError(
                message="Số lần dời lịch không được âm.",
                code="INVALID_RESCHEDULE_COUNT",
            )

    @staticmethod
    def _validate_duration(minutes: int) -> None:
        if not (MANUAL_TASK_MIN_MINUTES <= int(minutes) <= MANUAL_TASK_MAX_MINUTES):
            raise InvalidTaskDurationError()

    @staticmethod
    def _validate_time_bounds(
        start: datetime | None,
        end: datetime | None,
    ) -> None:
        if (start is None) != (end is None):
            raise ExecutionDomainError(
                message="Cần cung cấp đồng thời cả giờ bắt đầu và giờ kết thúc.",
                code="INVALID_TASK_TIME_BOUNDS",
            )
        if start is not None and end is not None and end <= start:
            raise ExecutionDomainError(
                message="Giờ kết thúc (scheduled_end) phải sau giờ bắt đầu (scheduled_start).",
                code="INVALID_TASK_TIME_BOUNDS",
            )

    def is_overdue(self, today: date) -> bool:
        """Derived OVERDUE flag evaluated in learner's local timezone (BUSR-06)."""
        return (
            self.status in (TaskStatus.TODO, TaskStatus.IN_PROGRESS)
            and self.scheduled_date is not None
            and self.scheduled_date < today
        )

    def is_stalled(self) -> bool:
        """Derived STALLED flag when reschedule_count >= 3 (FR-ADAPT-003)."""
        return self.reschedule_count >= STALLED_RESCHEDULE_THRESHOLD

    def update_details(
        self,
        *,
        title: str | None = None,
        description: str | None = None,
        estimated_minutes: int | None = None,
        now: datetime,
    ) -> None:
        if self.status == TaskStatus.CANCELLED:
            raise InvalidTaskStateError("Không thể chỉnh sửa nhiệm vụ đã hủy.")
        if title is not None:
            cleaned = title.strip()
            if not cleaned:
                raise ExecutionDomainError(
                    message="Tiêu đề nhiệm vụ (title) không được để trống.",
                    code="INVALID_TASK_TITLE",
                )
            self.title = cleaned
        if description is not None:
            self.description = description
        if estimated_minutes is not None:
            self._validate_duration(estimated_minutes)
            self.estimated_minutes = int(estimated_minutes)
        self.updated_at = now

    def mark_in_progress(self, now: datetime) -> None:
        if self.status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED):
            raise InvalidTaskStateError(
                f"Không thể bắt đầu phiên học cho nhiệm vụ ở trạng thái '{self.status.value}'."
            )
        self.status = TaskStatus.IN_PROGRESS
        self.updated_at = now

    def complete(self, now: datetime) -> None:
        if self.status == TaskStatus.CANCELLED:
            raise InvalidTaskStateError("Không thể hoàn thành nhiệm vụ đã bị hủy.")
        self.status = TaskStatus.COMPLETED
        self.completed_at = now
        self.reschedule_count = 0
        self.updated_at = now

    def reopen(self, now: datetime) -> None:
        if self.status != TaskStatus.COMPLETED:
            raise InvalidTaskStateError("Chỉ có thể mở lại nhiệm vụ đang ở trạng thái COMPLETED.")
        self.status = TaskStatus.TODO
        self.completed_at = None
        self.updated_at = now

    def return_to_backlog(self, now: datetime) -> None:
        if self.status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED):
            raise InvalidTaskStateError(
                f"Không thể đưa nhiệm vụ trạng thái '{self.status.value}' về Backlog."
            )
        self.status = TaskStatus.TODO
        self.scheduled_date = None
        self.scheduled_start = None
        self.scheduled_end = None
        self.updated_at = now

    def reschedule(
        self,
        *,
        scheduled_date: date | None,
        scheduled_start: datetime | None,
        scheduled_end: datetime | None,
        today: date,
        now: datetime,
        allow_stalled_commitment: bool = False,
    ) -> bool:
        """Reschedule task to a new date/slot or move to backlog (`scheduled_date=None`).

        Returns `True` if the reschedule counted as an overdue reschedule (so caller
        can deduct weekly reschedule budget).
        """
        if self.status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED):
            raise InvalidTaskStateError(
                f"Không thể dời lịch nhiệm vụ ở trạng thái '{self.status.value}'."
            )
        if self.is_stalled() and not allow_stalled_commitment:
            raise TaskStalledInterventionRequiredError()

        was_overdue = self.is_overdue(today)

        if scheduled_date is None:
            self.return_to_backlog(now)
            return False

        self._validate_time_bounds(scheduled_start, scheduled_end)
        self.scheduled_date = scheduled_date
        self.scheduled_start = scheduled_start
        self.scheduled_end = scheduled_end
        if allow_stalled_commitment:
            self.reschedule_count = 0
            counted_overdue = False
        elif was_overdue:
            self.reschedule_count += 1
            counted_overdue = True
        else:
            counted_overdue = False

        if self.status == TaskStatus.IN_PROGRESS:
            self.status = TaskStatus.TODO
        self.updated_at = now
        return counted_overdue

    def cancel(self, now: datetime) -> None:
        if self.status == TaskStatus.COMPLETED:
            raise InvalidTaskStateError("Không thể hủy nhiệm vụ đã hoàn thành.")
        self.status = TaskStatus.CANCELLED
        self.scheduled_date = None
        self.scheduled_start = None
        self.scheduled_end = None
        self.official_schedule_id = None
        self.updated_at = now
