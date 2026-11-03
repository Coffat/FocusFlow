from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, time
from typing import Any

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
