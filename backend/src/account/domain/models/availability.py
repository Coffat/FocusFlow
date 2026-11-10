from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, time
from enum import StrEnum
from typing import Any
from uuid import UUID

from src.account.domain.events.availability_events import AvailabilityUpdatedEvent
from src.account.domain.exceptions.availability import (
    InsufficientWeeklyAvailabilityException,
    InvalidAllowedWindowException,
    InvalidMinSessionMinutesException,
    InvalidQuotaBoundException,
    InvalidTimeSlotException,
    OverlappingTimeSlotsException,
)
from src.shared_kernel.domain.base import (
    AggregateRoot,
    ValueObject,
    generate_uuid7,
    utc_now,
)


class AvailabilityMode(StrEnum):
    MODE_A = "MODE_A"
    MODE_B = "MODE_B"


class CalendarIntegrationMode(StrEnum):
    NONE = "NONE"
    EXPORT_ICS = "EXPORT_ICS"
    CONNECTED = "CONNECTED"


class PreferredPeriod(StrEnum):
    MORNING = "MORNING"
    AFTERNOON = "AFTERNOON"
    EVENING = "EVENING"
    ANY = "ANY"


def parse_time_str(val: str) -> time:
    """Parse HH:MM or HH:MM:SS string to datetime.time."""
    parts = val.strip().split(":")
    if len(parts) < 2:
        raise InvalidTimeSlotException(f"Định dạng thời gian không hợp lệ: '{val}'. Cần HH:MM.")
    return time(hour=int(parts[0]), minute=int(parts[1]))


@dataclass(frozen=True)
class TimeSlot(ValueObject):
    start_time: time
    end_time: time
    end_day_offset: int = 0

    def __post_init__(self) -> None:
        if self.end_day_offset not in (0, 1):
            raise InvalidTimeSlotException("end_day_offset chỉ được phép là 0 hoặc 1.")

        start_m = self.start_time.hour * 60 + self.start_time.minute
        end_m = self.end_time.hour * 60 + self.end_time.minute + (self.end_day_offset * 1440)

        if self.end_day_offset == 0 and self.start_time >= self.end_time:
            raise InvalidTimeSlotException(
                f"Thời gian bắt đầu ({self.start_time.strftime('%H:%M')}) phải trước "
                f"thời gian kết thúc ({self.end_time.strftime('%H:%M')}) khi cùng ngày."
            )

        duration = end_m - start_m
        if duration < 30:
            raise InvalidTimeSlotException(
                f"Thời lượng khung giờ ({duration} phút) phải đạt tối thiểu 30 phút."
            )

    @property
    def duration_minutes(self) -> int:
        start_m = self.start_time.hour * 60 + self.start_time.minute
        end_m = self.end_time.hour * 60 + self.end_time.minute + (self.end_day_offset * 1440)
        return end_m - start_m

    def minute_range(self) -> tuple[int, int]:
        start_m = self.start_time.hour * 60 + self.start_time.minute
        end_m = self.end_time.hour * 60 + self.end_time.minute + (self.end_day_offset * 1440)
        return start_m, end_m

    def overlaps(self, other: "TimeSlot") -> bool:
        s1, e1 = self.minute_range()
        s2, e2 = other.minute_range()
        return s1 < e2 and s2 < e1

    @classmethod
    def from_str(
        cls,
        start: str,
        end: str,
        end_day_offset: int = 0,
        day: str = "",  # noqa: ARG003
    ) -> "TimeSlot":
        return cls(
            start_time=parse_time_str(start),
            end_time=parse_time_str(end),
            end_day_offset=end_day_offset,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "start": self.start_time.strftime("%H:%M"),
            "end": self.end_time.strftime("%H:%M"),
            "end_day_offset": self.end_day_offset,
        }


@dataclass(frozen=True)
class AllowedWindow(ValueObject):
    start: str = "07:00"
    end: str = "23:00"

    def __post_init__(self) -> None:
        try:
            s_t = parse_time_str(self.start)
            e_t = parse_time_str(self.end)
        except Exception as exc:
            raise InvalidAllowedWindowException(
                f"Định dạng giờ allowed_window không hợp lệ: {exc}"
            ) from exc

        s_m = s_t.hour * 60 + s_t.minute
        e_m = e_t.hour * 60 + e_t.minute
        if e_m <= s_m:
            raise InvalidAllowedWindowException(
                f"Khung giờ cho phép không hợp lệ: start ({self.start}) phải trước end ({self.end})."
            )
        if (e_m - s_m) < 30:
            raise InvalidAllowedWindowException(
                f"Khung giờ cho phép phải có độ dài ít nhất 30 phút, hiện tại là {e_m - s_m} phút."
            )


@dataclass(frozen=True)
class DaySchedule(ValueObject):
    enabled: bool
    quota_hours: float
    time_slots: tuple[TimeSlot, ...] = ()
    allowed_window: AllowedWindow = field(default_factory=AllowedWindow)
    preferred_period: PreferredPeriod = PreferredPeriod.ANY
    min_session_minutes: int = 30

    @property
    def total_slot_minutes(self) -> int:
        return sum(slot.duration_minutes for slot in self.time_slots)

    def validate_invariants(self, day_name: str, active_mode: AvailabilityMode) -> None:
        if not self.enabled:
            return

        if active_mode == AvailabilityMode.MODE_A:
            if not (0.5 <= self.quota_hours <= 14.0):
                raise InvalidQuotaBoundException(day=day_name, quota_hours=self.quota_hours)
            if not (15 <= self.min_session_minutes <= 120):
                raise InvalidMinSessionMinutesException(
                    min_session_minutes=self.min_session_minutes,
                    day=day_name,
                )
        elif active_mode == AvailabilityMode.MODE_B:
            if len(self.time_slots) == 0:
                raise InvalidTimeSlotException(
                    f"Ngày {day_name} đang bật (enabled=True) nhưng chưa có khung giờ rảnh nào."
                )
            sorted_slots = sorted(self.time_slots, key=lambda s: s.minute_range()[0])
            for i in range(len(sorted_slots) - 1):
                if sorted_slots[i].overlaps(sorted_slots[i + 1]):
                    s1_str = (
                        f"{sorted_slots[i].start_time.strftime('%H:%M')} - "
                        f"{sorted_slots[i].end_time.strftime('%H:%M')}"
                    )
                    s2_str = (
                        f"{sorted_slots[i + 1].start_time.strftime('%H:%M')} - "
                        f"{sorted_slots[i + 1].end_time.strftime('%H:%M')}"
                    )
                    raise OverlappingTimeSlotsException(
                        day=day_name,
                        conflicting_slots=[s1_str, s2_str],
                    )


@dataclass(frozen=True)
class WeeklySchedule(ValueObject):
    days: Mapping[str, DaySchedule]

    def calculate_total_weekly_hours(self, mode: AvailabilityMode) -> float:
        if mode == AvailabilityMode.MODE_A:
            total = sum(d.quota_hours for d in self.days.values() if d.enabled)
            return round(total, 1)
        total = sum(d.total_slot_minutes for d in self.days.values() if d.enabled) / 60.0
        return round(total, 1)

    def validate_invariants(self, mode: AvailabilityMode) -> None:
        for day_name, day_schedule in self.days.items():
            day_schedule.validate_invariants(day_name, mode)

        total_hours = self.calculate_total_weekly_hours(mode)
        if total_hours < 1.0:
            raise InsufficientWeeklyAvailabilityException(
                total_hours=total_hours,
                min_required=1.0,
            )


@dataclass(frozen=True)
class ProposedTaskSlot(ValueObject):
    task_id: UUID | None
    title: str
    day_of_week: str
    start_time: time
    end_time: time
    end_day_offset: int = 0
    duration_minutes: int = 30

    def minute_range(self) -> tuple[int, int]:
        start_m = self.start_time.hour * 60 + self.start_time.minute
        end_m = self.end_time.hour * 60 + self.end_time.minute + (self.end_day_offset * 1440)
        return start_m, end_m


@dataclass(frozen=True)
class AvailabilityValidationResult(ValueObject):
    is_valid: bool
    overflow_minutes: int = 0
    has_soft_overflow: bool = False
    violation_reasons: tuple[str, ...] = ()


@dataclass
class AvailabilityProfile(AggregateRoot):
    user_id: UUID = field(default_factory=generate_uuid7)
    mode: AvailabilityMode = AvailabilityMode.MODE_A
    calendar_integration_mode: CalendarIntegrationMode = CalendarIntegrationMode.NONE
    weekly_schedule: WeeklySchedule = field(default_factory=lambda: WeeklySchedule(days={}))
    min_session_minutes: int = 30
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    @classmethod
    def create_default(cls, user_id: UUID) -> "AvailabilityProfile":
        weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday"]
        weekends = ["saturday", "sunday"]
        days: dict[str, DaySchedule] = {}

        for day in weekdays:
            days[day] = DaySchedule(
                enabled=True,
                quota_hours=2.0,
                time_slots=(TimeSlot.from_str("19:30", "21:30"),),
                allowed_window=AllowedWindow(start="07:00", end="23:00"),
                preferred_period=PreferredPeriod.EVENING,
                min_session_minutes=30,
            )
        for day in weekends:
            days[day] = DaySchedule(
                enabled=True,
                quota_hours=3.0,
                time_slots=(TimeSlot.from_str("14:00", "17:00"),),
                allowed_window=AllowedWindow(start="07:00", end="23:00"),
                preferred_period=PreferredPeriod.AFTERNOON,
                min_session_minutes=30,
            )
        schedule = WeeklySchedule(days=days)
        schedule.validate_invariants(AvailabilityMode.MODE_A)
        return cls(
            user_id=user_id,
            mode=AvailabilityMode.MODE_A,
            calendar_integration_mode=CalendarIntegrationMode.NONE,
            weekly_schedule=schedule,
            min_session_minutes=30,
            created_at=utc_now(),
            updated_at=utc_now(),
        )

    def switch_mode(self, new_mode: AvailabilityMode) -> None:
        self.weekly_schedule.validate_invariants(new_mode)
        self.mode = new_mode
        self.updated_at = utc_now()

    def update_schedule(
        self,
        new_schedule: WeeklySchedule,
        calendar_integration_mode: CalendarIntegrationMode | None = None,
        min_session_minutes: int | None = None,
        new_mode: AvailabilityMode | None = None,
    ) -> None:
        target_mode = new_mode if new_mode is not None else self.mode
        target_min_session = (
            min_session_minutes if min_session_minutes is not None else self.min_session_minutes
        )
        if not (15 <= target_min_session <= 120):
            raise InvalidMinSessionMinutesException(min_session_minutes=target_min_session)

        new_schedule.validate_invariants(target_mode)
        self.mode = target_mode
        self.weekly_schedule = new_schedule
        if calendar_integration_mode is not None:
            self.calendar_integration_mode = calendar_integration_mode
        if min_session_minutes is not None:
            self.min_session_minutes = min_session_minutes
        self.updated_at = utc_now()
        self.add_domain_event(
            AvailabilityUpdatedEvent(
                user_id=self.user_id,
                availability_mode=self.mode.value,
                aggregate_id=self.id,
            )
        )

    def get_daily_ceiling(self, day_of_week: str) -> int:
        day_schedule = self.weekly_schedule.days.get(day_of_week.lower())
        if not day_schedule or not day_schedule.enabled:
            return 0
        if self.mode == AvailabilityMode.MODE_A:
            return int(day_schedule.quota_hours * 60)
        return day_schedule.total_slot_minutes

    def validate_daily_ceiling(
        self, day_of_week: str, total_minutes: int
    ) -> AvailabilityValidationResult:
        from src.account.domain.services.hybrid_availability_rule_engine import (
            HybridAvailabilityRuleEngine,
        )

        return HybridAvailabilityRuleEngine.validate_daily_ceiling(self, day_of_week, total_minutes)

    def validate_proposal_against_slots(
        self,
        day_of_week: str,
        proposed_tasks: Sequence[ProposedTaskSlot],
        occupied_intervals: Sequence[tuple[time, time, int] | tuple[time, time]] = (),
    ) -> AvailabilityValidationResult:
        from src.account.domain.services.hybrid_availability_rule_engine import (
            HybridAvailabilityRuleEngine,
        )

        return HybridAvailabilityRuleEngine.validate_proposal_against_slots(
            self, day_of_week, proposed_tasks, occupied_intervals
        )

    def calculate_remaining_capacity(
        self,
        day_of_week: str,
        occupied_intervals: Sequence[tuple[time, time, int] | tuple[time, time]] = (),
        allocated_minutes: int = 0,
    ) -> int | list[TimeSlot]:
        from src.account.domain.services.hybrid_availability_rule_engine import (
            HybridAvailabilityRuleEngine,
        )

        return HybridAvailabilityRuleEngine.calculate_remaining_capacity(
            self, day_of_week, occupied_intervals, allocated_minutes
        )
