import pytest

from src.account.domain.exceptions.availability import (
    InvalidTimeSlotException,
    OverlappingTimeSlotsException,
)
from src.account.domain.models.availability import AvailabilityMode, DaySchedule, TimeSlot


def test_tc_mb_01_independent_slots_valid() -> None:
    slots = (
        TimeSlot.from_str("08:00", "10:00"),
        TimeSlot.from_str("14:00", "16:00"),
    )
    day = DaySchedule(enabled=True, quota_hours=4.0, time_slots=slots)
    day.validate_invariants("monday", AvailabilityMode.MODE_B)


def test_tc_mb_02_touching_slots_valid() -> None:
    slots = (
        TimeSlot.from_str("18:00", "19:30"),
        TimeSlot.from_str("19:30", "21:00"),
    )
    day = DaySchedule(enabled=True, quota_hours=3.0, time_slots=slots)
    day.validate_invariants("tuesday", AvailabilityMode.MODE_B)


def test_tc_mb_03_overlapping_slots_raises() -> None:
    slots = (
        TimeSlot.from_str("19:00", "21:00"),
        TimeSlot.from_str("20:00", "22:00"),
    )
    day = DaySchedule(enabled=True, quota_hours=4.0, time_slots=slots)
    with pytest.raises(OverlappingTimeSlotsException) as exc_info:
        day.validate_invariants("wednesday", AvailabilityMode.MODE_B)
    assert exc_info.value.code == "OVERLAPPING_TIME_SLOTS"
    assert exc_info.value.details["day"] == "wednesday"
    assert len(exc_info.value.details["conflicting_slots"]) == 2


def test_tc_mb_enabled_without_slots_raises() -> None:
    day = DaySchedule(enabled=True, quota_hours=2.0, time_slots=())
    with pytest.raises(InvalidTimeSlotException):
        day.validate_invariants("thursday", AvailabilityMode.MODE_B)
