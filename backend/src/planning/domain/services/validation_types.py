from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, time
from typing import Any, Literal

NonSplittableSource = Literal["EXPLICIT_DTO", "DETERMINISTIC_RULE", "DEFAULT_SPLITTABLE"]
FeasibilityVerdict = Literal[
    "VERIFIED_FEASIBLE",
    "EXPLICIT_UNSCHEDULABLE",
    "HEURISTIC_ALLOCATION_INCOMPLETE",
]
ScheduleCompletenessStatus = Literal["FULL", "PARTIAL", "UNDETERMINED", "INFEASIBLE"]
UnschedulableReasonCode = Literal[
    "TOTAL_EFFORT_EXCEEDS_HARD_CAPACITY",
    "TASK_EXCEEDS_CONTINUOUS_SLOT",
    "CRITICAL_PATH_EXCEEDS_WINDOW",
    "CALENDAR_CONFLICT_SATURATION",
    "HEURISTIC_ALLOCATION_INCOMPLETE",
]

AI_BLOCK_MIN_MINUTES: int = 30
AI_BLOCK_MAX_MINUTES: int = 120

MANUAL_BLOCK_MIN_MINUTES: int = 15
MANUAL_BLOCK_MAX_MINUTES: int = 240

MAX_DAILY_PLANNED_MINUTES: int = 720
SOFT_OVERFLOW_MAX_MINUTES: int = 30

WEEKDAY_NAMES: tuple[str, ...] = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)


@dataclass(frozen=True, slots=True)
class ConstraintViolationDTO:
    """Structured constraint violation returned by Tier 1 / Tier 2 for LLM Self-Correction & API 422."""

    task_index: int | None
    field: str
    rule_code: str
    expected_bound: str
    actual_value: str
    suggested_fix: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_index": self.task_index,
            "field": self.field,
            "rule_code": self.rule_code,
            "expected_bound": self.expected_bound,
            "actual_value": self.actual_value,
            "suggested_fix": self.suggested_fix,
        }


@dataclass(frozen=True, slots=True)
class SoftOverflowWarningDTO:
    """Warning emitted in Mode B when the last task of a slot/day overflows by <= 30m (BUSR-04)."""

    task_index: int
    task_title: str
    scheduled_date: date
    overflow_minutes: int
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_index": self.task_index,
            "task_title": self.task_title,
            "scheduled_date": self.scheduled_date.isoformat(),
            "overflow_minutes": self.overflow_minutes,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class AvailabilitySlotDTO:
    """Single availability window for a weekday in Mode B (FIXED_SLOTS)."""

    day_of_week: int | str  # 0..6 (Monday=0..Sunday=6) or "monday".."sunday"
    start_time: time | str  # time or "HH:MM"
    end_time: time | str  # time or "HH:MM"
    end_day_offset: int = 0
    is_active: bool = True


@dataclass(frozen=True, slots=True)
class AvailabilityConfigurationDTO:
    """Availability configuration passed into the Planning 3-Tier Validation Gate."""

    mode: str = "MODE_A"  # "MODE_A" / "QUOTA" or "MODE_B" / "FIXED_SLOTS"
    daily_quota_minutes: Mapping[str | int, int] = field(default_factory=dict)
    default_daily_quota_minutes: int = 120
    availability_slots: Sequence[AvailabilitySlotDTO] = ()
    disabled_weekdays: frozenset[str] = field(default_factory=frozenset)
    timezone: str = "UTC"


@dataclass(frozen=True, slots=True)
class UnscheduledTaskDiagnosticDTO:
    """Structured diagnostic explaining why a task remained unplaced after Phase 1 scheduling."""

    task_id: str
    title: str
    estimated_minutes: int
    is_non_splittable: bool
    non_splittable_source: NonSplittableSource
    verdict: FeasibilityVerdict
    reason_code: str
    message: str
    earliest_feasible_date: date | None = None
    max_contiguous_window_minutes: int = 0
    required_minutes: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "estimated_minutes": self.estimated_minutes,
            "is_non_splittable": self.is_non_splittable,
            "non_splittable_source": self.non_splittable_source,
            "verdict": self.verdict,
            "reason_code": self.reason_code,
            "message": self.message,
            "earliest_feasible_date": (
                self.earliest_feasible_date.isoformat()
                if self.earliest_feasible_date is not None
                else None
            ),
            "max_contiguous_window_minutes": self.max_contiguous_window_minutes,
            "required_minutes": self.required_minutes,
        }


@dataclass(frozen=True, slots=True)
class NecessaryConditionCheckResult:
    """Mathematical necessary-condition feasibility verification result (NC-1..NC-3)."""

    verdict: FeasibilityVerdict
    nc1_passed: bool
    nc2_passed: bool
    nc3_passed: bool
    total_required_minutes: int
    total_hard_packable_minutes: int
    raw_capacity_without_existing_minutes: int = 0
    max_contiguous_window_minutes: int = 0
    violations: tuple[ConstraintViolationDTO, ...] = ()
    unscheduled_diagnostics: tuple[UnscheduledTaskDiagnosticDTO, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "nc1_passed": self.nc1_passed,
            "nc2_passed": self.nc2_passed,
            "nc3_passed": self.nc3_passed,
            "total_required_minutes": self.total_required_minutes,
            "total_hard_packable_minutes": self.total_hard_packable_minutes,
            "raw_capacity_without_existing_minutes": self.raw_capacity_without_existing_minutes,
            "max_contiguous_window_minutes": self.max_contiguous_window_minutes,
            "violations": [v.to_dict() for v in self.violations],
            "unscheduled_diagnostics": [d.to_dict() for d in self.unscheduled_diagnostics],
        }


@dataclass(frozen=True, slots=True)
class ScheduleAllocationResult:
    """Phase 1 allocation output including feasibility verdict and per-task diagnostics."""

    tasks: list[dict[str, Any]]
    schedule_blocks: list[dict[str, Any]]
    feasibility_verdict: FeasibilityVerdict
    necessary_conditions: NecessaryConditionCheckResult
    unscheduled_diagnostics: tuple[UnscheduledTaskDiagnosticDTO, ...] = ()
    repairs_attempted: int = 0


def normalize_weekday_name(day_val: int | str | date) -> str:
    """Convert date, 0..6 integer, or string day name into lowercase 'monday'..'sunday'."""
    if isinstance(day_val, date):
        return WEEKDAY_NAMES[day_val.weekday()]
    if isinstance(day_val, int):
        idx = day_val % 7
        return WEEKDAY_NAMES[idx]
    cleaned = str(day_val).strip().lower()
    if cleaned.isdigit():
        return WEEKDAY_NAMES[int(cleaned) % 7]
    for name in WEEKDAY_NAMES:
        if cleaned == name or cleaned.startswith(name[:3]):
            return name
    return cleaned


def parse_hhmm_or_time(val: object) -> time | None:
    """Parse a time, datetime, ISO string, or 'HH:MM' string into datetime.time."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.time().replace(second=0, microsecond=0, tzinfo=None)
    if isinstance(val, time):
        return val.replace(second=0, microsecond=0, tzinfo=None)
    text = str(val).strip()
    if not text:
        return None
    if "T" in text:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return dt.time().replace(second=0, microsecond=0, tzinfo=None)
    parts = text.split(":")
    return time(hour=int(parts[0]), minute=int(parts[1]))


def parse_iso_datetime(val: object) -> datetime | None:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    text = str(val).strip()
    if not text:
        return None
    if "T" in text or " " in text:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    return None


def parse_iso_date(val: object) -> date | None:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    text = str(val).strip()
    if not text:
        return None
    if "T" in text:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    return date.fromisoformat(text[:10])


def safe_parse_iso_date(val: object) -> date | None:
    """Parse ISO date or datetime safely, returning None on invalid strings."""
    try:
        return parse_iso_date(val)
    except ValueError:
        return None


def safe_parse_iso_datetime(val: object) -> datetime | None:
    """Parse ISO datetime safely, returning None on invalid strings."""
    try:
        return parse_iso_datetime(val)
    except ValueError:
        return None


def classify_schedule_completeness(
    *,
    total_tasks: int,
    scheduled_tasks_count: int,
    unscheduled_tasks_count: int,
    available_minutes: int,
    schedulable_ratio: float,
    feasibility_verdict: str | None = None,
    has_schedule_blocks: bool = False,
    all_scheduled_have_block_times: bool = False,
    allow_partial_schedule: bool = True,
) -> ScheduleCompletenessStatus:
    """Classify deterministic schedule completeness into FULL, PARTIAL, UNDETERMINED, or INFEASIBLE."""
    if total_tasks <= 0:
        return "UNDETERMINED"
    if available_minutes <= 0:
        return "INFEASIBLE"
    if feasibility_verdict == "UNDETERMINED":
        return "UNDETERMINED"
    if (
        unscheduled_tasks_count > 0
        and not feasibility_verdict
        and not has_schedule_blocks
        and not all_scheduled_have_block_times
    ):
        return "UNDETERMINED"
    if scheduled_tasks_count == 0 and not feasibility_verdict and not has_schedule_blocks:
        return "UNDETERMINED"
    if scheduled_tasks_count == 0 or schedulable_ratio < 0.25:
        return "INFEASIBLE"
    if unscheduled_tasks_count > 0 and not allow_partial_schedule:
        return "INFEASIBLE"
    if feasibility_verdict == "EXPLICIT_UNSCHEDULABLE" and not allow_partial_schedule:
        return "INFEASIBLE"
    if unscheduled_tasks_count > 0:
        return "PARTIAL"
    if feasibility_verdict == "EXPLICIT_UNSCHEDULABLE":
        return "INFEASIBLE"
    if schedulable_ratio < 1.0 or scheduled_tasks_count < total_tasks:
        return "UNDETERMINED"
    if (
        feasibility_verdict == "VERIFIED_FEASIBLE"
        or all_scheduled_have_block_times
        or has_schedule_blocks
    ):
        return "FULL"
    return "UNDETERMINED"
