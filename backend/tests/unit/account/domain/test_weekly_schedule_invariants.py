import pytest

from src.account.domain.exceptions.availability import InsufficientWeeklyAvailabilityException
from src.account.domain.models.availability import (
    AvailabilityMode,
    AvailabilityProfile,
    DaySchedule,
    TimeSlot,
    WeeklySchedule,
)
from src.shared_kernel.domain.base import generate_uuid7


def test_tc_ws_01_default_schedule_16_hours_valid() -> None:
    user_id = generate_uuid7()
    profile = AvailabilityProfile.create_default(user_id)
    assert profile.mode == AvailabilityMode.MODE_A
    total_hours = profile.weekly_schedule.calculate_total_weekly_hours(AvailabilityMode.MODE_A)
    assert total_hours == 16.0
    # Invariants pass without error
    profile.weekly_schedule.validate_invariants(AvailabilityMode.MODE_A)


def test_tc_ws_02_total_below_1_hour_raises() -> None:
    days = {
        "monday": DaySchedule(enabled=True, quota_hours=0.5),
        "tuesday": DaySchedule(enabled=False, quota_hours=0.0),
        "wednesday": DaySchedule(enabled=False, quota_hours=0.0),
        "thursday": DaySchedule(enabled=False, quota_hours=0.0),
        "friday": DaySchedule(enabled=False, quota_hours=0.0),
        "saturday": DaySchedule(enabled=False, quota_hours=0.0),
        "sunday": DaySchedule(enabled=False, quota_hours=0.0),
    }
    sched = WeeklySchedule(days=days)
    with pytest.raises(InsufficientWeeklyAvailabilityException) as exc_info:
        sched.validate_invariants(AvailabilityMode.MODE_A)
    assert exc_info.value.code == "INSUFFICIENT_WEEKLY_AVAILABILITY"
    assert exc_info.value.details["total_hours"] == 0.5
    assert exc_info.value.details["min_required"] == 1.0


def test_tc_ws_03_mode_b_calculation_and_validation() -> None:
    days = {
        "monday": DaySchedule(
            enabled=True,
            quota_hours=2.0,
            time_slots=(TimeSlot.from_str("19:00", "21:00"),),
        ),
        "tuesday": DaySchedule(
            enabled=True,
            quota_hours=1.5,
            time_slots=(TimeSlot.from_str("20:00", "21:30"),),
        ),
        "wednesday": DaySchedule(enabled=False, quota_hours=0.0, time_slots=()),
        "thursday": DaySchedule(enabled=False, quota_hours=0.0, time_slots=()),
        "friday": DaySchedule(enabled=False, quota_hours=0.0, time_slots=()),
        "saturday": DaySchedule(enabled=False, quota_hours=0.0, time_slots=()),
        "sunday": DaySchedule(enabled=False, quota_hours=0.0, time_slots=()),
    }
    sched = WeeklySchedule(days=days)
    # Monday = 2.0h, Tuesday = 1.5h -> total = 3.5h
    assert sched.calculate_total_weekly_hours(AvailabilityMode.MODE_B) == 3.5
    sched.validate_invariants(AvailabilityMode.MODE_B)
