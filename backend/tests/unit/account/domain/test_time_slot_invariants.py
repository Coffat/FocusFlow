from datetime import time

import pytest

from src.account.domain.exceptions.availability import InvalidTimeSlotException
from src.account.domain.models.availability import TimeSlot


def test_tc_ts_01_valid_time_slot_duration() -> None:
    slot = TimeSlot(start_time=time(19, 0), end_time=time(21, 0), end_day_offset=0)
    assert slot.duration_minutes == 120
    assert slot.minute_range() == (1140, 1260)


def test_tc_ts_02_start_after_end_same_day_raises() -> None:
    with pytest.raises(InvalidTimeSlotException):
        TimeSlot(start_time=time(21, 0), end_time=time(20, 0), end_day_offset=0)


def test_tc_ts_03_start_equal_end_raises() -> None:
    with pytest.raises(InvalidTimeSlotException):
        TimeSlot(start_time=time(20, 0), end_time=time(20, 0), end_day_offset=0)


def test_tc_ts_04_shorter_than_30_minutes_raises() -> None:
    with pytest.raises(InvalidTimeSlotException) as exc_info:
        TimeSlot(start_time=time(20, 0), end_time=time(20, 25), end_day_offset=0)
    assert "tối thiểu 30 phút" in str(exc_info.value)


def test_tc_ts_05_overlaps_touching_vs_intersecting() -> None:
    slot_a = TimeSlot.from_str("18:00", "19:30")
    slot_b = TimeSlot.from_str("19:30", "21:00")
    slot_c = TimeSlot.from_str("19:00", "20:30")

    # Touching boundaries do not overlap
    assert not slot_a.overlaps(slot_b)
    assert not slot_b.overlaps(slot_a)

    # Intersecting intervals overlap
    assert slot_a.overlaps(slot_c)
    assert slot_b.overlaps(slot_c)


def test_tc_ts_06_cross_midnight_slot() -> None:
    slot = TimeSlot(start_time=time(22, 30), end_time=time(0, 30), end_day_offset=1)
    # 22:30 is 1350; 00:30 next day is 30 + 1440 = 1470; 1470 - 1350 = 120m
    assert slot.duration_minutes == 120
    assert slot.minute_range() == (1350, 1470)


def test_tc_ts_invalid_offset() -> None:
    with pytest.raises(InvalidTimeSlotException):
        TimeSlot(start_time=time(20, 0), end_time=time(22, 0), end_day_offset=2)
