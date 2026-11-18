from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from src.execution.domain.events.session_events import (
    StudySessionAbandonedEvent,
    StudySessionCompletedEvent,
)
from src.execution.domain.exceptions.execution_exceptions import (
    ExecutionDomainError,
    InvalidSessionStateError,
)
from src.shared_kernel.domain.base import AggregateRoot, generate_uuid7

MVS_MIN_QUALIFYING_MINUTES: int = 10
STANDARD_PARTIAL_RATIO: float = 0.5
SCRATCHPAD_MAX_CHARS: int = 10_000


class SessionMode(StrEnum):
    STANDARD = "STANDARD"
    MVS = "MVS"


class SessionStatus(StrEnum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    PARTIAL_COMPLETED = "PARTIAL_COMPLETED"
    CANCELLED = "CANCELLED"


class NoteType(StrEnum):
    SCRATCHPAD = "SCRATCHPAD"
    TAKEAWAY = "TAKEAWAY"
    GENERAL = "GENERAL"


class AlignmentFlag(StrEnum):
    UNCHECKED = "UNCHECKED"
    ALIGNED = "ALIGNED"
    SUPERFICIAL = "SUPERFICIAL"
    OFF_TOPIC = "OFF_TOPIC"
    CONTRADICTORY = "CONTRADICTORY"


class VerificationStatus(StrEnum):
    PENDING_PROVE = "PENDING_PROVE"
    VERIFIED = "VERIFIED"
    FLAGGED_SHALLOW = "FLAGGED_SHALLOW"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class TimeSufficiency(StrEnum):
    TOO_SHORT = "TOO_SHORT"
    JUST_RIGHT = "JUST_RIGHT"
    TOO_LONG = "TOO_LONG"


@dataclass(frozen=True, slots=True)
class DailyCheckin:
    """3 quantitative Daily Learning Check-in signals (SRS FR-SESSION-002)."""

    time_sufficiency: TimeSufficiency | None = None
    perceived_difficulty: int | None = None
    focus_level: int | None = None

    def __post_init__(self) -> None:
        if self.perceived_difficulty is not None and not (1 <= self.perceived_difficulty <= 5):
            raise ExecutionDomainError(
                message="Độ khó cảm nhận (perceived_difficulty) phải từ 1 đến 5.",
                code="INVALID_CHECKIN_VALUE",
            )
        if self.focus_level is not None and not (1 <= self.focus_level <= 5):
            raise ExecutionDomainError(
                message="Mức độ tập trung (focus_level) phải từ 1 đến 5.",
                code="INVALID_CHECKIN_VALUE",
            )


@dataclass
class SessionTask:
    """Association entity linking a StudySession to one or more Tasks."""

    id: UUID = field(default_factory=generate_uuid7)
    session_id: UUID = field(default_factory=generate_uuid7)
    task_id: UUID = field(default_factory=generate_uuid7)
    allocated_minutes: int = 0
    actual_minutes: int = 0
    status_after_session: str = "IN_PROGRESS"  # TODO | IN_PROGRESS | COMPLETED
    notes: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.min)
    updated_at: datetime = field(default_factory=lambda: datetime.min)


@dataclass
class StudyNote:
    """Scratchpad, Key Takeaway, or General study note attached to session/task."""

    id: UUID = field(default_factory=generate_uuid7)
    user_id: UUID = field(default_factory=generate_uuid7)
    session_id: UUID | None = None
    task_id: UUID | None = None
    note_type: NoteType = NoteType.SCRATCHPAD
    content: str = ""
    self_confidence: int | None = None
    ai_evidence_score: float | None = None
    alignment_flag: AlignmentFlag = AlignmentFlag.UNCHECKED
    verification_status: VerificationStatus = VerificationStatus.PENDING_PROVE
    created_at: datetime = field(default_factory=lambda: datetime.min)
    updated_at: datetime = field(default_factory=lambda: datetime.min)

    def __post_init__(self) -> None:
        if isinstance(self.note_type, str):
            self.note_type = NoteType(self.note_type)
        if isinstance(self.alignment_flag, str):
            self.alignment_flag = AlignmentFlag(self.alignment_flag)
        if isinstance(self.verification_status, str):
            self.verification_status = VerificationStatus(self.verification_status)
        if self.self_confidence is not None and not (1 <= self.self_confidence <= 5):
            raise ExecutionDomainError(
                message="Mức tự tin (self_confidence) phải từ 1 đến 5.",
                code="INVALID_SELF_CONFIDENCE",
            )
        if self.note_type == NoteType.SCRATCHPAD and len(self.content) > SCRATCHPAD_MAX_CHARS:
            raise ExecutionDomainError(
                message=f"Nội dung Scratchpad tối đa {SCRATCHPAD_MAX_CHARS} ký tự.",
                code="SCRATCHPAD_TOO_LONG",
            )


@dataclass
class StudySession(AggregateRoot):
    """StudySession aggregate root enforcing SRS 6.3, OS-01, and OS-07."""

    user_id: UUID = field(default_factory=generate_uuid7)
    roadmap_id: UUID = field(default_factory=generate_uuid7)
    started_at: datetime = field(default_factory=lambda: datetime.min)
    ended_at: datetime | None = None
    planned_minutes: int = 25
    actual_minutes: int = 0
    status: SessionStatus = SessionStatus.IN_PROGRESS
    last_heartbeat_at: datetime = field(default_factory=lambda: datetime.min)
    session_mode: SessionMode = SessionMode.STANDARD
    pending_takeaway: bool = False
    checkin_time_sufficiency: TimeSufficiency | None = None
    checkin_perceived_difficulty: int | None = None
    checkin_focus_level: int | None = None
    created_at: datetime = field(default_factory=lambda: datetime.min)
    updated_at: datetime = field(default_factory=lambda: datetime.min)

    def __post_init__(self) -> None:
        if isinstance(self.status, str):
            self.status = SessionStatus(self.status)
        if isinstance(self.session_mode, str):
            self.session_mode = SessionMode(self.session_mode)
        if isinstance(self.checkin_time_sufficiency, str):
            self.checkin_time_sufficiency = TimeSufficiency(self.checkin_time_sufficiency)
        if self.planned_minutes <= 0:
            raise ExecutionDomainError(
                message="Thời lượng dự kiến của phiên học phải lớn hơn 0.",
                code="INVALID_SESSION_DURATION",
            )

    def record_heartbeat(
        self,
        *,
        now: datetime,
        actual_minutes: int | None = None,
    ) -> None:
        if self.status != SessionStatus.IN_PROGRESS:
            raise InvalidSessionStateError(
                f"Không thể ghi nhận heartbeat cho phiên ở trạng thái '{self.status.value}'."
            )
        elapsed_minutes = max(0, int((now - self.started_at).total_seconds() // 60))
        candidate = max(0, int(actual_minutes)) if actual_minutes is not None else elapsed_minutes
        # Monotonic progression of actual_minutes & last_heartbeat_at
        self.actual_minutes = max(self.actual_minutes, candidate)
        if now > self.last_heartbeat_at:
            self.last_heartbeat_at = now
        self.updated_at = now

    def evaluate_early_stop_status(
        self,
        *,
        has_completed_task: bool,
        has_valid_takeaway: bool,
    ) -> SessionStatus:
        """Apply SRS v1.3 OS-01 rules for early-stopped / interrupted sessions."""
        if has_completed_task:
            return SessionStatus.PARTIAL_COMPLETED
        if self.session_mode == SessionMode.STANDARD:
            if self.actual_minutes >= (STANDARD_PARTIAL_RATIO * self.planned_minutes):
                return SessionStatus.PARTIAL_COMPLETED
            return SessionStatus.CANCELLED
        # MVS mode (OS-01 exception): >= 10 minutes AND valid Key Takeaway
        if self.actual_minutes >= MVS_MIN_QUALIFYING_MINUTES and has_valid_takeaway:
            return SessionStatus.PARTIAL_COMPLETED
        return SessionStatus.CANCELLED

    def finalize(
        self,
        *,
        now: datetime,
        early_stop: bool = False,
        has_completed_task: bool = False,
        has_valid_takeaway: bool = False,
        checkin: DailyCheckin | None = None,
        actual_minutes_override: int | None = None,
    ) -> SessionStatus:
        """Close an IN_PROGRESS session, evaluate OS-01, and emit domain event."""
        if self.status != SessionStatus.IN_PROGRESS:
            raise InvalidSessionStateError(
                f"Phiên học đã kết thúc ({self.status.value}) và là bất biến."
            )

        elapsed_minutes = max(0, int((now - self.started_at).total_seconds() // 60))
        candidate_minutes = (
            max(0, int(actual_minutes_override))
            if actual_minutes_override is not None
            else elapsed_minutes
        )
        self.actual_minutes = max(self.actual_minutes, candidate_minutes)

        if not early_stop:
            new_status = SessionStatus.COMPLETED
        else:
            new_status = self.evaluate_early_stop_status(
                has_completed_task=has_completed_task,
                has_valid_takeaway=has_valid_takeaway,
            )

        self.status = new_status
        self.ended_at = now if now >= self.started_at else self.started_at
        if checkin is not None:
            self.checkin_time_sufficiency = checkin.time_sufficiency
            self.checkin_perceived_difficulty = checkin.perceived_difficulty
            self.checkin_focus_level = checkin.focus_level
        self.updated_at = now

        duration_seconds = int(self.actual_minutes) * 60
        if new_status in (SessionStatus.COMPLETED, SessionStatus.PARTIAL_COMPLETED):
            self.add_domain_event(
                StudySessionCompletedEvent(
                    aggregate_id=self.id,
                    aggregate_type="StudySession",
                    user_id=self.user_id,
                    session_id=self.id,
                    actual_duration_seconds=duration_seconds,
                )
            )
        else:
            self.add_domain_event(
                StudySessionAbandonedEvent(
                    aggregate_id=self.id,
                    aggregate_type="StudySession",
                    user_id=self.user_id,
                    session_id=self.id,
                    recovered_duration_seconds=duration_seconds,
                )
            )

        return new_status

    def resolve_pending_takeaway(self, *, now: datetime) -> None:
        if not self.pending_takeaway:
            raise InvalidSessionStateError("Phiên học này không có nghĩa vụ nợ Key Takeaway.")
        self.pending_takeaway = False
        self.updated_at = now
