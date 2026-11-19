import json
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
VALID_STICKY_NOTE_COLORS: frozenset[str] = frozenset(
    {"cream", "pink", "sage", "blue", "amber", "lavender"}
)
STUDIO_CONFIG_SENTINEL_PREFIX: str = "<!--FF_STUDIO_CONFIG_V1-->"
STICKY_NOTE_ENVELOPE_PREFIX: str = "<!--FF_STICKY_V1-->"
VALID_STUDIO_SCENES: frozenset[str] = frozenset(
    {"architectural", "lofi-night", "rain", "cafe", "library"}
)
VALID_STUDIO_CLOCK_STYLES: frozenset[str] = frozenset({"editorial", "ring", "flip", "minimal"})
VALID_STUDIO_CLOCK_SIZES: frozenset[str] = frozenset({"md", "lg"})


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
class StickyNotePayload:
    """Structured sticky-note payload encoded inside StudyNote(GENERAL).content."""

    title: str
    body: str
    color: str = "cream"
    pinned: bool = True
    pos_x: float | None = None
    pos_y: float | None = None
    z_index: int | None = None
    origin_session_id: str | None = None


def encode_sticky_note_content(payload: StickyNotePayload) -> str:
    """Validate and encode a StickyNotePayload with the versioned envelope prefix."""
    if payload.color not in VALID_STICKY_NOTE_COLORS:
        raise ExecutionDomainError(
            message=f"Màu ghi chú '{payload.color}' không hợp lệ.",
            code="INVALID_STICKY_NOTE_COLOR",
        )
    if len(payload.title) > 200:
        raise ExecutionDomainError(
            message="Tiêu đề ghi chú tối đa 200 ký tự.",
            code="INVALID_STICKY_NOTE_TITLE",
        )
    if len(payload.body) > 5000:
        raise ExecutionDomainError(
            message="Nội dung ghi chú tối đa 5000 ký tự.",
            code="INVALID_STICKY_NOTE_BODY",
        )
    meta: dict[str, object] = {
        "title": payload.title,
        "color": payload.color,
        "pinned": payload.pinned,
        "pos_x": payload.pos_x,
        "pos_y": payload.pos_y,
        "z_index": payload.z_index,
        "origin_session_id": payload.origin_session_id,
    }
    return f"{STICKY_NOTE_ENVELOPE_PREFIX}{json.dumps(meta, ensure_ascii=False)}\n{payload.body}"


def decode_sticky_note_content(raw: str) -> StickyNotePayload:
    """Decode a StickyNotePayload, falling back to plain legacy text if unprefixed."""
    if not raw.startswith(STICKY_NOTE_ENVELOPE_PREFIX):
        return StickyNotePayload(title="", body=raw, color="cream", pinned=True)

    rest = raw[len(STICKY_NOTE_ENVELOPE_PREFIX) :]
    if "\n" in rest:
        meta_raw, body = rest.split("\n", 1)
    else:
        meta_raw, body = rest, ""

    try:
        meta = json.loads(meta_raw)
    except json.JSONDecodeError:
        return StickyNotePayload(title="", body=raw, color="cream", pinned=True)

    if not isinstance(meta, dict):
        return StickyNotePayload(title="", body=raw, color="cream", pinned=True)

    color_val = str(meta.get("color") or "cream")
    if color_val not in VALID_STICKY_NOTE_COLORS:
        color_val = "cream"

    raw_pos_x = meta.get("pos_x")
    raw_pos_y = meta.get("pos_y")
    raw_z = meta.get("z_index")
    raw_origin = meta.get("origin_session_id")
    return StickyNotePayload(
        title=str(meta.get("title") or "")[:200],
        body=body,
        color=color_val,
        pinned=bool(meta.get("pinned", True)),
        pos_x=(
            float(raw_pos_x)
            if isinstance(raw_pos_x, (int, float)) and not isinstance(raw_pos_x, bool)
            else None
        ),
        pos_y=(
            float(raw_pos_y)
            if isinstance(raw_pos_y, (int, float)) and not isinstance(raw_pos_y, bool)
            else None
        ),
        z_index=(int(raw_z) if isinstance(raw_z, int) and not isinstance(raw_z, bool) else None),
        origin_session_id=str(raw_origin) if raw_origin is not None else None,
    )


@dataclass(frozen=True, slots=True)
class StudioConfigPayload:
    """Workspace studio configuration encoded inside a sentinel StudyNote(GENERAL)."""

    scene: str = "lofi-night"
    clock_style: str = "ring"
    clock_size: str = "lg"
    show_seconds: bool = True
    show_in_tab_title: bool = True
    tab_guard_enabled: bool = True
    zen_lock_enabled: bool = False
    blocklist: tuple[str, ...] = ("facebook.com", "youtube.com", "tiktok.com")
    parking_lot: tuple[dict[str, object], ...] = ()


def encode_studio_config(payload: StudioConfigPayload) -> str:
    """Validate and encode StudioConfigPayload with the sentinel prefix."""
    if payload.scene not in VALID_STUDIO_SCENES:
        raise ExecutionDomainError(
            message=f"Chủ đề phòng học '{payload.scene}' không hợp lệ.",
            code="INVALID_STUDIO_CONFIG",
        )
    if payload.clock_style not in VALID_STUDIO_CLOCK_STYLES:
        raise ExecutionDomainError(
            message=f"Kiểu đồng hồ '{payload.clock_style}' không hợp lệ.",
            code="INVALID_STUDIO_CONFIG",
        )
    if payload.clock_size not in VALID_STUDIO_CLOCK_SIZES:
        raise ExecutionDomainError(
            message=f"Kích thước đồng hồ '{payload.clock_size}' không hợp lệ.",
            code="INVALID_STUDIO_CONFIG",
        )
    data: dict[str, object] = {
        "scene": payload.scene,
        "clock_style": payload.clock_style,
        "clock_size": payload.clock_size,
        "show_seconds": payload.show_seconds,
        "show_in_tab_title": payload.show_in_tab_title,
        "tab_guard_enabled": payload.tab_guard_enabled,
        "zen_lock_enabled": payload.zen_lock_enabled,
        "blocklist": list(payload.blocklist),
        "parking_lot": [dict(item) for item in payload.parking_lot],
    }
    return f"{STUDIO_CONFIG_SENTINEL_PREFIX}{json.dumps(data, ensure_ascii=False)}"


def decode_studio_config(raw: str) -> StudioConfigPayload:
    """Decode StudioConfigPayload from sentinel content, defaulting cleanly on invalid input."""
    if not raw.startswith(STUDIO_CONFIG_SENTINEL_PREFIX):
        return StudioConfigPayload()

    json_part = raw[len(STUDIO_CONFIG_SENTINEL_PREFIX) :].strip()
    try:
        data = json.loads(json_part)
    except json.JSONDecodeError:
        return StudioConfigPayload()

    if not isinstance(data, dict):
        return StudioConfigPayload()

    defaults = StudioConfigPayload()
    scene = str(data.get("scene") or defaults.scene)
    if scene not in VALID_STUDIO_SCENES:
        scene = defaults.scene

    clock_style = str(data.get("clock_style") or defaults.clock_style)
    if clock_style not in VALID_STUDIO_CLOCK_STYLES:
        clock_style = defaults.clock_style

    clock_size = str(data.get("clock_size") or defaults.clock_size)
    if clock_size not in VALID_STUDIO_CLOCK_SIZES:
        clock_size = defaults.clock_size

    raw_blocklist = data.get("blocklist")
    blocklist = (
        tuple(str(item) for item in raw_blocklist)
        if isinstance(raw_blocklist, list)
        else defaults.blocklist
    )

    raw_parking = data.get("parking_lot")
    parking_lot = (
        tuple(dict(item) for item in raw_parking if isinstance(item, dict))
        if isinstance(raw_parking, list)
        else defaults.parking_lot
    )

    return StudioConfigPayload(
        scene=scene,
        clock_style=clock_style,
        clock_size=clock_size,
        show_seconds=bool(data.get("show_seconds", defaults.show_seconds)),
        show_in_tab_title=bool(data.get("show_in_tab_title", defaults.show_in_tab_title)),
        tab_guard_enabled=bool(data.get("tab_guard_enabled", defaults.tab_guard_enabled)),
        zen_lock_enabled=bool(data.get("zen_lock_enabled", defaults.zen_lock_enabled)),
        blocklist=blocklist,
        parking_lot=parking_lot,
    )


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
        if self.status == SessionStatus.CANCELLED:
            qualifies_mvs = (
                self.session_mode == SessionMode.MVS
                and self.actual_minutes >= MVS_MIN_QUALIFYING_MINUTES
            )
            qualifies_standard = (
                self.planned_minutes > 0 and self.actual_minutes * 2 >= self.planned_minutes
            )
            if qualifies_mvs or qualifies_standard:
                self.status = SessionStatus.PARTIAL_COMPLETED
        self.pending_takeaway = False
        self.updated_at = now
