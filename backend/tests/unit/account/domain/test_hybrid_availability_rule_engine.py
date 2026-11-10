from datetime import time

from src.account.domain.models.availability import (
    AvailabilityMode,
    AvailabilityProfile,
    DaySchedule,
    ProposedTaskSlot,
    TimeSlot,
    WeeklySchedule,
)
from src.account.domain.services.hybrid_availability_rule_engine import (
    HybridAvailabilityRuleEngine,
)
from src.shared_kernel.domain.base import generate_uuid7


def _build_test_profile(
    mode: AvailabilityMode,
    monday_quota: float = 2.0,
    monday_slots: tuple[TimeSlot, ...] = (TimeSlot.from_str("19:00", "21:00"),),
) -> AvailabilityProfile:
    days = {
        "monday": DaySchedule(
            enabled=True,
            quota_hours=monday_quota,
            time_slots=monday_slots,
        ),
        "tuesday": DaySchedule(enabled=False, quota_hours=0.0, time_slots=()),
        "wednesday": DaySchedule(enabled=False, quota_hours=0.0, time_slots=()),
        "thursday": DaySchedule(enabled=False, quota_hours=0.0, time_slots=()),
        "friday": DaySchedule(enabled=False, quota_hours=0.0, time_slots=()),
        "saturday": DaySchedule(enabled=False, quota_hours=0.0, time_slots=()),
        "sunday": DaySchedule(enabled=False, quota_hours=0.0, time_slots=()),
    }
    return AvailabilityProfile(
        user_id=generate_uuid7(),
        mode=mode,
        weekly_schedule=WeeklySchedule(days=days),
    )


def test_tc_re_01_mode_a_hard_ceiling() -> None:
    profile = _build_test_profile(AvailabilityMode.MODE_A, monday_quota=2.0)  # 120m
    # 130m > 120m -> is_valid = False, overflow = 10m
    res = HybridAvailabilityRuleEngine.validate_daily_ceiling(profile, "monday", 130)
    assert not res.is_valid
    assert res.overflow_minutes == 10

    # 120m <= 120m -> is_valid = True
    res_valid = HybridAvailabilityRuleEngine.validate_daily_ceiling(profile, "monday", 120)
    assert res_valid.is_valid
    assert res_valid.overflow_minutes == 0


def test_tc_re_02_mode_b_soft_overflow_within_30m() -> None:
    # Slot 19:00 - 21:00 (120m). Proposed task 19:00 - 21:20 (140m, overflows 20m <= 30m)
    profile = _build_test_profile(
        AvailabilityMode.MODE_B,
        monday_slots=(TimeSlot.from_str("19:00", "21:00"),),
    )
    task = ProposedTaskSlot(
        task_id=generate_uuid7(),
        title="Python Async",
        day_of_week="monday",
        start_time=time(19, 0),
        end_time=time(21, 20),
        duration_minutes=140,
    )
    res = HybridAvailabilityRuleEngine.validate_proposal_against_slots(profile, "monday", [task])
    assert res.is_valid
    assert res.has_soft_overflow
    assert res.overflow_minutes == 20


def test_tc_re_03_mode_b_hard_block_over_30m() -> None:
    # Slot 19:00 - 21:00 (120m). Proposed task 19:00 - 21:40 (160m, overflows 40m > 30m)
    profile = _build_test_profile(
        AvailabilityMode.MODE_B,
        monday_slots=(TimeSlot.from_str("19:00", "21:00"),),
    )
    task = ProposedTaskSlot(
        task_id=generate_uuid7(),
        title="Deep Learning",
        day_of_week="monday",
        start_time=time(19, 0),
        end_time=time(21, 40),
        duration_minutes=160,
    )
    res = HybridAvailabilityRuleEngine.validate_proposal_against_slots(profile, "monday", [task])
    assert not res.is_valid
    assert res.overflow_minutes == 40


def test_tc_re_04_calculate_remaining_capacity() -> None:
    # Mode A: 2.0h (120m) - 45m = 75m
    profile_a = _build_test_profile(AvailabilityMode.MODE_A, monday_quota=2.0)
    rem_a = HybridAvailabilityRuleEngine.calculate_remaining_capacity(
        profile_a, "monday", allocated_minutes=45
    )
    assert rem_a == 75

    # Mode B: Slot [19:00 - 22:00] (180m). Occupied [20:00 - 20:30]
    # Expected remaining: [19:00 - 20:00] (60m) and [20:30 - 22:00] (90m)
    profile_b = _build_test_profile(
        AvailabilityMode.MODE_B,
        monday_slots=(TimeSlot.from_str("19:00", "22:00"),),
    )
    rem_b = HybridAvailabilityRuleEngine.calculate_remaining_capacity(
        profile_b,
        "monday",
        occupied_intervals=[(time(20, 0), time(20, 30))],
    )
    assert isinstance(rem_b, list)
    assert len(rem_b) == 2
    assert rem_b[0].start_time == time(19, 0) and rem_b[0].end_time == time(20, 0)
    assert rem_b[1].start_time == time(20, 30) and rem_b[1].end_time == time(22, 0)


def test_tc_re_05_validate_proposal_collision_with_occupied() -> None:
    profile = _build_test_profile(
        AvailabilityMode.MODE_B,
        monday_slots=(TimeSlot.from_str("19:00", "22:00"),),
    )
    # Task 19:30 - 20:30 collides with occupied 20:00 - 21:00
    task = ProposedTaskSlot(
        task_id=generate_uuid7(),
        title="Database Indexing",
        day_of_week="monday",
        start_time=time(19, 30),
        end_time=time(20, 30),
        duration_minutes=60,
    )
    res = HybridAvailabilityRuleEngine.validate_proposal_against_slots(
        profile,
        "monday",
        [task],
        occupied_intervals=[(time(20, 0), time(21, 0))],
    )
    assert not res.is_valid
    assert any("va chạm" in reason for reason in res.violation_reasons)


def test_tc_re_06_cross_midnight_slot_duration() -> None:
    slot = TimeSlot.from_str("22:30", "00:30", end_day_offset=1)
    assert slot.duration_minutes == 120


def test_e2e_dom_06_cross_midnight_interval_subtraction() -> None:
    """E2E-DOM-06: Subtracting 22:00->00:30 (+1d) from 22:00->02:00 (+1d) yields 00:30->02:00 (90m, offset=0)."""
    base_slot = TimeSlot.from_str("22:00", "02:00", end_day_offset=1)
    assert base_slot.duration_minutes == 240

    remaining = HybridAvailabilityRuleEngine.subtract_intervals(
        base_slots=[base_slot],
        occupied=[(time(22, 0), time(0, 30), 1)],
    )
    assert len(remaining) == 1
    assert remaining[0].start_time == time(0, 30)
    assert remaining[0].end_time == time(2, 0)
    assert remaining[0].end_day_offset == 0
    assert remaining[0].duration_minutes == 90


def test_e2e_dom_07_contiguous_slots_merged_for_task_fit() -> None:
    """E2E-DOM-07: Two touching slots [18:00-19:30] and [19:30-21:00] allow task [18:00-20:00] with 0 overflow."""
    profile = _build_test_profile(
        AvailabilityMode.MODE_B,
        monday_slots=(
            TimeSlot.from_str("18:00", "19:30"),
            TimeSlot.from_str("19:30", "21:00"),
        ),
    )
    task = ProposedTaskSlot(
        task_id=generate_uuid7(),
        title="System Design Deep Dive",
        day_of_week="monday",
        start_time=time(18, 0),
        end_time=time(20, 0),
        duration_minutes=120,
    )
    res = profile.validate_proposal_against_slots("monday", [task])
    assert res.is_valid is True
    assert res.has_soft_overflow is False
    assert res.overflow_minutes == 0


def test_e2e_dom_08_cumulative_soft_overflow_exceeding_30m_blocked() -> None:
    """E2E-DOM-08: Two tasks each overflowing by 20m in the same day (total 40m > 30m) are rejected."""
    profile = _build_test_profile(
        AvailabilityMode.MODE_B,
        monday_slots=(
            TimeSlot.from_str("18:00", "19:00"),
            TimeSlot.from_str("20:00", "21:00"),
        ),
    )
    task1 = ProposedTaskSlot(
        task_id=generate_uuid7(),
        title="Task 1 (+20m)",
        day_of_week="monday",
        start_time=time(18, 0),
        end_time=time(19, 20),
        duration_minutes=80,
    )
    task2 = ProposedTaskSlot(
        task_id=generate_uuid7(),
        title="Task 2 (+20m)",
        day_of_week="monday",
        start_time=time(20, 0),
        end_time=time(21, 20),
        duration_minutes=80,
    )
    res = profile.validate_proposal_against_slots("monday", [task1, task2])
    assert res.is_valid is False
    assert res.overflow_minutes == 40
    assert any("vượt quá giới hạn tối đa 30 phút" in r for r in res.violation_reasons)


def test_e2e_dom_08c_soft_overflow_colliding_with_occupied_blocked() -> None:
    """E2E-DOM-08(c): Soft overflow of 20m that collides with an occupied interval [20:40-21:00] is rejected."""
    profile = _build_test_profile(
        AvailabilityMode.MODE_B,
        monday_slots=(TimeSlot.from_str("19:00", "20:30"),),
    )
    task = ProposedTaskSlot(
        task_id=generate_uuid7(),
        title="Task Overflowing Into Busy Slot",
        day_of_week="monday",
        start_time=time(19, 0),
        end_time=time(20, 50),
        duration_minutes=110,
    )
    res = profile.validate_proposal_against_slots(
        "monday",
        [task],
        occupied_intervals=[(time(20, 40), time(21, 0))],
    )
    assert res.is_valid is False
    assert any("va chạm với khoảng bận" in r for r in res.violation_reasons)


def test_profile_delegation_methods_and_atomic_mode_update() -> None:
    """Verify AvailabilityProfile delegating methods and atomic update_schedule(new_mode=...)."""
    profile = AvailabilityProfile.create_default(generate_uuid7())
    assert profile.get_daily_ceiling("monday") == 120
    assert profile.get_daily_ceiling("saturday") == 180
    assert profile.validate_daily_ceiling("monday", 90).is_valid is True
    assert profile.calculate_remaining_capacity("monday", allocated_minutes=30) == 90

    # Atomic switch from Mode A to Mode B with new schedule
    new_days = dict(profile.weekly_schedule.days)
    new_days["monday"] = DaySchedule(
        enabled=True,
        quota_hours=2.0,
        time_slots=(TimeSlot.from_str("08:00", "10:30"),),
    )
    profile.update_schedule(
        new_schedule=WeeklySchedule(days=new_days),
        new_mode=AvailabilityMode.MODE_B,
        min_session_minutes=45,
    )
    assert profile.mode == AvailabilityMode.MODE_B
    assert profile.min_session_minutes == 45
    assert profile.get_daily_ceiling("monday") == 150
