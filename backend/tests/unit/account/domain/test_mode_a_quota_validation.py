import pytest

from src.account.domain.exceptions.availability import InvalidQuotaBoundException
from src.account.domain.models.availability import AvailabilityMode, DaySchedule


def test_tc_ma_01_boundary_values_valid() -> None:
    day_min = DaySchedule(enabled=True, quota_hours=0.5)
    day_max = DaySchedule(enabled=True, quota_hours=14.0)

    # Should not raise
    day_min.validate_invariants("monday", AvailabilityMode.MODE_A)
    day_max.validate_invariants("tuesday", AvailabilityMode.MODE_A)


def test_tc_ma_02_below_min_raises() -> None:
    day = DaySchedule(enabled=True, quota_hours=0.4)
    with pytest.raises(InvalidQuotaBoundException) as exc_info:
        day.validate_invariants("monday", AvailabilityMode.MODE_A)
    assert exc_info.value.code == "INVALID_QUOTA_BOUNDS"
    assert exc_info.value.details["quota_hours"] == 0.4
    assert exc_info.value.details["min_allowed"] == 0.5


def test_tc_ma_03_above_max_raises() -> None:
    day = DaySchedule(enabled=True, quota_hours=14.5)
    with pytest.raises(InvalidQuotaBoundException) as exc_info:
        day.validate_invariants("friday", AvailabilityMode.MODE_A)
    assert exc_info.value.code == "INVALID_QUOTA_BOUNDS"
    assert exc_info.value.details["quota_hours"] == 14.5
    assert exc_info.value.details["max_allowed"] == 14.0


def test_tc_ma_04_disabled_day_preserves_state() -> None:
    day = DaySchedule(enabled=False, quota_hours=0.0)
    # When disabled, invariants pass without raising
    day.validate_invariants("sunday", AvailabilityMode.MODE_A)
