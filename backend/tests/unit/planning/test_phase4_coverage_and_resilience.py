from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from types import SimpleNamespace
from typing import Any
from uuid import NAMESPACE_DNS, UUID, uuid4, uuid5

import pytest

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
    _merge_contiguous_slot_ranges,
)
from src.evaluation.domain.services import QuantitativeFaithfulnessValidator
from src.execution.public_api import (
    DagCycleValidator,
    DagDependencyEdge,
    DagTaskNode,
    ExistingScheduledTaskDTO,
    create_execution_dashboard_query_port,
    create_execution_schedule_sync_port,
)
from src.planning.application.dtos.planning_dtos import SseJobTicketDTO
from src.planning.application.use_cases.proposal_management_use_cases import (
    InitiateOverdueRecoveryUseCase,
    ReoptimizeScheduleProposalUseCase,
)
from src.planning.application.use_cases.roadmap_management_use_cases import (
    PauseRoadmapUseCase,
    ResumeRoadmapUseCase,
)
from src.planning.domain.models import (
    Goal,
    GoalStatus,
    Milestone,
    MilestoneStatus,
    OfficialSchedule,
    Roadmap,
    RoadmapStatus,
    ScheduleProposal,
)
from src.planning.domain.models.schedule import ScheduleProposalType
from src.planning.domain.services.spatio_temporal_engine import (
    SpatioTemporalRuleEngine,
    _in_user_timezone,
    _slot_minute_range,
    _task_minute_range_on_base_date,
    _to_int,
)
from src.planning.domain.services.validation_types import (
    AvailabilityConfigurationDTO,
    AvailabilitySlotDTO,
)

# ---------------------------------------------------------------------------
# 1. Hybrid AvailabilityRuleEngine branch coverage
# ---------------------------------------------------------------------------


def _build_profile(mode: AvailabilityMode, days: dict[str, DaySchedule]) -> AvailabilityProfile:
    return AvailabilityProfile(
        id=uuid4(),
        user_id=uuid4(),
        mode=mode,
        weekly_schedule=WeeklySchedule(days=days),
    )


def test_availability_rule_engine_edge_branches() -> None:
    assert _merge_contiguous_slot_ranges([]) == []
    merged = _merge_contiguous_slot_ranges(
        [
            TimeSlot(time(18, 0), time(19, 0)),
            TimeSlot(time(18, 30), time(20, 0)),
            TimeSlot(time(21, 0), time(22, 0)),
        ]
    )
    assert merged == [(18 * 60, 20 * 60), (21 * 60, 22 * 60)]

    days_a = {
        "monday": DaySchedule(enabled=True, quota_hours=2.0),
        "sunday": DaySchedule(enabled=False, quota_hours=0.0),
    }
    profile_a = _build_profile(AvailabilityMode.MODE_A, days_a)

    # Daily ceiling disabled day
    assert (
        HybridAvailabilityRuleEngine.validate_daily_ceiling(profile_a, "sunday", 30).is_valid
        is False
    )
    assert (
        HybridAvailabilityRuleEngine.validate_daily_ceiling(profile_a, "sunday", 0).is_valid is True
    )

    # Remaining capacity (disabled Mode A & Mode B + non-overlapping/splitting occupied intervals)
    assert HybridAvailabilityRuleEngine.calculate_remaining_capacity(profile_a, "sunday") == 0

    days_b = {
        "monday": DaySchedule(
            enabled=True,
            quota_hours=3.0,
            time_slots=(TimeSlot(time(18, 0), time(19, 0)), TimeSlot(time(19, 10), time(21, 0))),
        ),
        "tuesday": DaySchedule(
            enabled=True,
            quota_hours=3.0,
            time_slots=(TimeSlot(time(18, 0), time(19, 0)), TimeSlot(time(20, 0), time(21, 0))),
        ),
        "sunday": DaySchedule(enabled=False, quota_hours=0.0, time_slots=()),
    }
    profile_b = _build_profile(AvailabilityMode.MODE_B, days_b)

    assert HybridAvailabilityRuleEngine.calculate_remaining_capacity(profile_b, "sunday") == []
    rem_slots = HybridAvailabilityRuleEngine.calculate_remaining_capacity(
        profile_b,
        "monday",
        occupied_intervals=[(time(17, 0), time(17, 30), 0), (time(19, 50), time(20, 20), 0)],
    )
    assert isinstance(rem_slots, list) and len(rem_slots) >= 2

    # validate_proposal_against_slots: disabled day, self overlap, occupied collision, soft overflow
    p_mon = ProposedTaskSlot(
        uuid4(), "T1", "monday", time(18, 0), time(18, 45), duration_minutes=45
    )
    assert (
        HybridAvailabilityRuleEngine.validate_proposal_against_slots(
            profile_b, "sunday", [p_mon]
        ).is_valid
        is False
    )
    assert (
        HybridAvailabilityRuleEngine.validate_proposal_against_slots(
            profile_b, "sunday", []
        ).is_valid
        is True
    )

    # Self-overlapping proposed tasks
    assert (
        HybridAvailabilityRuleEngine.validate_proposal_against_slots(
            profile_b,
            "tuesday",
            [
                ProposedTaskSlot(
                    uuid4(), "O1", "tuesday", time(18, 0), time(18, 50), duration_minutes=50
                ),
                ProposedTaskSlot(
                    uuid4(), "O2", "tuesday", time(18, 30), time(19, 0), duration_minutes=30
                ),
            ],
        ).is_valid
        is False
    )

    # Occupied 3-tuple collision
    assert (
        HybridAvailabilityRuleEngine.validate_proposal_against_slots(
            profile_b,
            "tuesday",
            [
                ProposedTaskSlot(
                    uuid4(), "Coll", "tuesday", time(18, 0), time(18, 50), duration_minutes=50
                )
            ],
            occupied_intervals=[(time(18, 30), time(19, 0), 0)],
        ).is_valid
        is False
    )

    # Soft overflow colliding with subsequent slot (monday slots: 18-19 and 19:10-21)
    assert (
        HybridAvailabilityRuleEngine.validate_proposal_against_slots(
            profile_b,
            "monday",
            [
                ProposedTaskSlot(
                    uuid4(), "HitNext", "monday", time(18, 15), time(19, 15), duration_minutes=60
                )
            ],
        ).is_valid
        is False
    )

    # Soft overflow valid (<=30 min and not colliding with 20:00-21:00)
    soft_ok = HybridAvailabilityRuleEngine.validate_proposal_against_slots(
        profile_b,
        "tuesday",
        [
            ProposedTaskSlot(
                uuid4(), "SoftOk", "tuesday", time(18, 15), time(19, 20), duration_minutes=65
            )
        ],
    )
    assert soft_ok.is_valid is True
    assert soft_ok.has_soft_overflow is True

    # Hard overflow > 30 min and completely outside any slot
    assert (
        HybridAvailabilityRuleEngine.validate_proposal_against_slots(
            profile_b,
            "tuesday",
            [
                ProposedTaskSlot(
                    uuid4(), "Hard", "tuesday", time(18, 15), time(19, 45), duration_minutes=90
                )
            ],
        ).is_valid
        is False
    )
    assert (
        HybridAvailabilityRuleEngine.validate_proposal_against_slots(
            profile_b,
            "tuesday",
            [
                ProposedTaskSlot(
                    uuid4(), "Outside", "tuesday", time(22, 0), time(22, 45), duration_minutes=45
                )
            ],
        ).is_valid
        is False
    )


# ---------------------------------------------------------------------------
# 2. Execution Public API & DAG Validator branch coverage
# ---------------------------------------------------------------------------


def test_execution_public_api_branches() -> None:
    d1 = date(2026, 11, 10)
    d2 = date(2026, 11, 8)
    n1 = DagTaskNode(task_id="n1", title="T1", scheduled_date=d1)
    n2 = DagTaskNode(task_id="n2", title="T2", scheduled_date=d2)
    n3 = DagTaskNode(task_id="n3", title="T3", scheduled_date=d2)

    result = DagCycleValidator.validate(
        [n1, n2, n3],
        [
            DagDependencyEdge(predecessor_id="n1", successor_id="n2", is_mandatory=False),
            DagDependencyEdge(predecessor_id="n1", successor_id="missing", is_mandatory=True),
            DagDependencyEdge(predecessor_id="n1", successor_id="n3", is_mandatory=True),
        ],
    )
    assert result.is_valid is False
    assert len(result.temporal_violations) == 1

    sync_port = create_execution_schedule_sync_port(None)  # type: ignore[arg-type]
    dash_port = create_execution_dashboard_query_port(None)  # type: ignore[arg-type]
    assert sync_port is not None
    assert dash_port is not None


# ---------------------------------------------------------------------------
# 3. SpatioTemporalRuleEngine comprehensive branch coverage
# ---------------------------------------------------------------------------


def test_spatio_temporal_helpers_and_edf_priority() -> None:
    assert _to_int(True) == 1
    assert _to_int("42") == 42
    assert _to_int("bad", 7) == 7
    assert _to_int(None, 5) == 5

    naive = datetime(2026, 11, 10, 18, 0)
    assert _in_user_timezone(None, "Asia/Ho_Chi_Minh") is None
    assert _in_user_timezone(naive, "Asia/Ho_Chi_Minh") is not None
    aware = datetime(2026, 11, 10, 11, 0, tzinfo=UTC)
    assert _in_user_timezone(aware, "Asia/Ho_Chi_Minh") is not None

    bad_slot = AvailabilitySlotDTO(
        day_of_week="monday",
        start_time=None,  # type: ignore[arg-type]
        end_time=time(19, 0),
        end_day_offset=0,
    )
    assert _slot_minute_range(bad_slot) == (0, 0)

    # _task_minute_range_on_base_date variations
    d0 = date(2026, 11, 10)
    cross_midnight_dt = _task_minute_range_on_base_date(
        base_date=d0,
        start_dt=datetime(2026, 11, 10, 23, 0),
        end_dt=datetime(2026, 11, 11, 1, 0),
        start_t=None,
        end_t=None,
    )
    assert cross_midnight_dt is not None and cross_midnight_dt[1] > 1440
    same_instant_dt = _task_minute_range_on_base_date(
        base_date=d0,
        start_dt=datetime(2026, 11, 10, 18, 0),
        end_dt=datetime(2026, 11, 10, 18, 0),
        start_t=None,
        end_t=None,
    )
    assert same_instant_dt == (18 * 60, 18 * 60 + 1440)

    time_only = _task_minute_range_on_base_date(
        base_date=d0,
        start_dt=None,
        end_dt=None,
        start_t=time(23, 0),
        end_t=time(0, 30),
    )
    assert time_only == (23 * 60, 24 * 60 + 30)
    assert (
        _task_minute_range_on_base_date(
            base_date=d0,
            start_dt=None,
            end_dt=None,
            start_t=None,
            end_t=None,
        )
        is None
    )

    rm1 = uuid4()
    rm2 = uuid4()
    assert SpatioTemporalRuleEngine.is_higher_or_equal_edf_priority(None, None, rm1, rm2) is True
    assert (
        SpatioTemporalRuleEngine.is_higher_or_equal_edf_priority(date(2026, 12, 1), None, rm1, rm2)
        is True
    )
    assert (
        SpatioTemporalRuleEngine.is_higher_or_equal_edf_priority(None, date(2026, 12, 1), rm1, rm2)
        is True
    )
    assert (
        SpatioTemporalRuleEngine.is_higher_or_equal_edf_priority(
            date(2026, 11, 20), date(2026, 12, 1), rm1, rm2
        )
        is True
    )
    assert (
        SpatioTemporalRuleEngine.is_higher_or_equal_edf_priority(
            date(2026, 12, 1), date(2026, 11, 20), rm1, rm2
        )
        is True
    )
    assert (
        SpatioTemporalRuleEngine.is_higher_or_equal_edf_priority(
            date(2026, 12, 1), date(2026, 12, 1), min(rm1, rm2), max(rm1, rm2)
        )
        is True
    )
    assert (
        SpatioTemporalRuleEngine.is_higher_or_equal_edf_priority(
            date(2026, 12, 1), date(2026, 12, 1), max(rm1, rm2), min(rm1, rm2)
        )
        is False
    )
    assert (
        SpatioTemporalRuleEngine.is_higher_or_equal_edf_priority(
            date(2026, 12, 1), date(2026, 12, 1), None, rm2
        )
        is True
    )


def test_spatio_temporal_mode_a_and_b_validation_branches() -> None:
    d_mon = date(2026, 11, 2)  # Monday
    d_sun = date(2026, 11, 8)  # Sunday

    avail_a = AvailabilityConfigurationDTO(
        mode="MODE_A",
        daily_quota_minutes={0: 60},  # int weekday key
        default_daily_quota_minutes=60,
        availability_slots=(),
        disabled_weekdays=frozenset({"sunday"}),
        timezone="Asia/Ho_Chi_Minh",
    )
    rm_other = uuid4()
    ext_tasks = [
        SimpleNamespace(
            task_id="done",
            title="Done",
            scheduled_date=d_mon,
            estimated_minutes=60,
            status="COMPLETED",
        ),
        SimpleNamespace(
            task_id="nodate",
            title="NoDate",
            scheduled_date=None,
            estimated_minutes=60,
            status="TODO",
        ),
        SimpleNamespace(
            task_id="occupied",
            title="Occupied",
            scheduled_date=d_mon,
            estimated_minutes=45,
            status="TODO",
            roadmap_id=rm_other,
            roadmap_target_date=date(2026, 11, 15),
        ),
    ]
    violations_a = SpatioTemporalRuleEngine.validate_mode_a_quota(
        tasks=[
            {"title": "Unscheduled", "estimated_minutes": 30},
            {"title": "DisabledSun", "scheduled_date": d_sun.isoformat(), "estimated_minutes": 30},
            {"title": "EDFConflict", "scheduled_date": d_mon.isoformat(), "estimated_minutes": 30},
        ],
        availability=avail_a,
        existing_tasks=ext_tasks,
        current_roadmap_target_date=date(2026, 11, 30),
    )
    codes_a = {v.rule_code for v in violations_a}
    assert "DAY_DISABLED" in codes_a
    assert "CROSS_ROADMAP_EDF_QUOTA_CONFLICT" in codes_a

    # Mode B edge violations
    avail_b = AvailabilityConfigurationDTO(
        mode="MODE_B",
        daily_quota_minutes={"monday": 180},
        default_daily_quota_minutes=180,
        availability_slots=(
            AvailabilitySlotDTO("monday", time(18, 0), time(19, 0), is_active=False),
            AvailabilitySlotDTO("monday", time(19, 0), time(20, 0), is_active=True),
            AvailabilitySlotDTO("monday", time(21, 0), time(22, 0), is_active=True),
        ),
        disabled_weekdays=frozenset(),
        timezone="Asia/Ho_Chi_Minh",
    )
    ext_b = [
        SimpleNamespace(
            task_id="ext_done",
            title="Done",
            scheduled_date=d_mon,
            estimated_minutes=60,
            status="COMPLETED",
        ),
        SimpleNamespace(
            task_id="ext_nodate",
            title="NoDate",
            scheduled_date=None,
            estimated_minutes=60,
            status="TODO",
        ),
        SimpleNamespace(
            task_id="ext_active",
            title="ExtActive",
            scheduled_date=None,
            scheduled_start=datetime(2026, 11, 2, 19, 0),
            scheduled_end=datetime(2026, 11, 2, 19, 30),
            estimated_minutes=30,
            status="TODO",
            roadmap_id=rm_other,
            roadmap_target_date=date(2026, 11, 15),
        ),
    ]
    v_b, _ = SpatioTemporalRuleEngine.validate_mode_b_slots(
        tasks=[
            {
                "task_id": "t_missing_bounds",
                "title": "NoBounds",
                "scheduled_date": d_mon.isoformat(),
                "estimated_minutes": 45,
            },
            {
                "task_id": "t_bad_order",
                "title": "BadOrder",
                "scheduled_start": "2026-11-02T19:30:00",
                "scheduled_end": "2026-11-01T18:00:00",
                "estimated_minutes": 30,
            },
            {
                "task_id": "t_mismatch",
                "title": "Mismatch",
                "scheduled_date": d_mon.isoformat(),
                "scheduled_start": "2026-11-02T21:00:00",
                "scheduled_end": "2026-11-02T21:30:00",
                "estimated_minutes": 45,
            },
            {
                "task_id": "t_overlap_1",
                "title": "O1",
                "scheduled_date": d_mon.isoformat(),
                "scheduled_start": "2026-11-02T21:00:00",
                "scheduled_end": "2026-11-02T21:45:00",
                "estimated_minutes": 45,
            },
            {
                "task_id": "t_no_slot_tue",
                "title": "NoSlotTue",
                "scheduled_date": "2026-11-03",
                "scheduled_start": "2026-11-03T19:00:00",
                "scheduled_end": "2026-11-03T19:45:00",
                "estimated_minutes": 45,
            },
        ],
        availability=avail_b,
        existing_tasks=ext_b,
        current_roadmap_target_date=date(2026, 11, 30),
    )
    codes_b = {v.rule_code for v in v_b}
    assert "MODE_B_MISSING_TIME_BOUNDS" in codes_b
    assert "INVALID_TASK_TIME_ORDER" in codes_b
    assert "MODE_B_DURATION_MISMATCH" in codes_b
    assert "TASK_TIME_OVERLAP" in codes_b
    assert "NO_AVAILABILITY_SLOT_FOR_DAY" in codes_b


def test_spatio_temporal_allocation_and_capacity_branches() -> None:
    d0 = date(2026, 11, 2)
    avail_a = AvailabilityConfigurationDTO(
        mode="MODE_A",
        daily_quota_minutes={"monday": 90, "tuesday": 90},
        default_daily_quota_minutes=90,
        availability_slots=(),
        disabled_weekdays=frozenset({"sunday"}),
        timezone="Asia/Ho_Chi_Minh",
    )
    assert (
        SpatioTemporalRuleEngine.allocate_tasks_to_availability(
            [], availability=avail_a, start_date=d0, target_date=d0
        )
        == []
    )

    # All tasks already scheduled
    already = [{"task_id": "a1", "scheduled_date": d0.isoformat(), "estimated_minutes": 45}]
    assert (
        SpatioTemporalRuleEngine.allocate_tasks_to_availability(
            already, availability=avail_a, start_date=d0, target_date=d0
        )[0]["scheduled_date"]
        == d0.isoformat()
    )

    # Dict slots + cross-midnight + cycle fallback + zero duration + existing dicts + tight window
    avail_dict_b = AvailabilityConfigurationDTO(
        mode="MODE_B",
        daily_quota_minutes={"monday": 180},
        default_daily_quota_minutes=180,
        availability_slots=(
            {
                "day_of_week": "monday",
                "start_time": "23:00",
                "end_time": "00:30",
                "is_active": True,
            },  # type: ignore[arg-type]
            {
                "day_of_week": "monday",
                "start_time": "18:00",
                "end_time": "19:00",
                "is_active": False,
            },  # type: ignore[arg-type]
        ),
        disabled_weekdays=frozenset({"sunday"}),
        timezone="Asia/Ho_Chi_Minh",
    )
    ext_dicts: list[Any] = [
        {"status": "COMPLETED", "scheduled_date": d0.isoformat(), "estimated_minutes": 30},
        {
            "status": "TODO",
            "scheduled_date": d0.isoformat(),
            "scheduled_start": f"{d0.isoformat()}T23:00:00",
            "scheduled_end": f"{d0.isoformat()}T23:30:00",
            "estimated_minutes": 30,
        },
        ExistingScheduledTaskDTO(
            task_id=uuid4(),
            roadmap_id=uuid4(),
            milestone_id=uuid4(),
            title="ScheduledOnlyDate",
            scheduled_date=d0,
            scheduled_start=None,
            scheduled_end=None,
            estimated_minutes=30,
            status="TODO",
        ),
    ]
    tasks_cycle = [
        {
            "task_id": "c1",
            "estimated_minutes": 45,
            "scheduled_date": d0.isoformat(),
            "scheduled_start": f"{d0.isoformat()}T18:00:00",
        },
        {"task_id": "c2", "estimated_minutes": 0},
        {"task_id": "c3", "estimated_minutes": 45},
        {"task_id": "c4", "estimated_minutes": 120},  # cannot fit in remaining 60m on single Mon
    ]
    deps_cycle = [
        {"predecessor_id": "c3", "successor_id": "c4", "is_mandatory": True},
        {"predecessor_id": "c4", "successor_id": "c3", "is_mandatory": True},
    ]
    allocated = SpatioTemporalRuleEngine.allocate_tasks_to_availability(
        tasks_cycle,
        availability=avail_dict_b,
        start_date=d0,
        target_date=d0,
        dependencies=deps_cycle,
        existing_tasks=ext_dicts,
    )
    assert len(allocated) == 4

    # Mode A allocation with daily occupied intervals and deadline overflow
    alloc_a = SpatioTemporalRuleEngine.allocate_tasks_to_availability(
        [{"task_id": "m1", "estimated_minutes": 60}, {"task_id": "m2", "estimated_minutes": 60}],
        availability=avail_a,
        start_date=d0,
        target_date=d0,
        existing_tasks=[
            {
                "status": "TODO",
                "scheduled_date": d0.isoformat(),
                "scheduled_start": f"{d0.isoformat()}T08:00:00",
                "scheduled_end": f"{d0.isoformat()}T08:30:00",
                "estimated_minutes": 30,
            }
        ],
    )
    assert alloc_a[0]["scheduled_date"] == d0.isoformat()

    # Capacity calculation edge cases
    assert (
        SpatioTemporalRuleEngine.calculate_available_capacity_minutes(
            availability=avail_a,
            start_date=d0 + timedelta(days=2),
            target_date=d0,
        )
        == 0
    )
    cap_a = SpatioTemporalRuleEngine.calculate_available_capacity_minutes(
        availability=avail_a,
        start_date=d0,
        target_date=d0 + timedelta(days=7),
        existing_tasks=ext_dicts,
        daily_workload_cap_minutes=60,
    )
    cap_b = SpatioTemporalRuleEngine.calculate_available_capacity_minutes(
        availability=AvailabilityConfigurationDTO(
            mode="MODE_B",
            daily_quota_minutes={"monday": 180},
            default_daily_quota_minutes=180,
            availability_slots=(
                {
                    "day_of_week": "monday",
                    "start_time": "23:00",
                    "end_time": "00:30",
                    "is_active": True,
                },  # type: ignore[arg-type]
                {
                    "day_of_week": "monday",
                    "start_time": None,
                    "end_time": "19:00",
                    "is_active": True,
                },  # type: ignore[arg-type]
                {
                    "day_of_week": "tuesday",
                    "start_time": "18:00",
                    "end_time": "19:00",
                    "is_active": False,
                },  # type: ignore[arg-type]
            ),
            disabled_weekdays=frozenset({"sunday"}),
            timezone="Asia/Ho_Chi_Minh",
        ),
        start_date=d0,
        target_date=d0 + timedelta(days=7),
        existing_tasks=ext_dicts,
        daily_workload_cap_minutes=120,
    )
    assert cap_a > 0
    assert cap_b >= 0

    # allocate_task_sessions edge branches (session_limit < 10, effort <= 0, base < 10, peak slots, weekly buffer, cap)
    avail_sessions = AvailabilityConfigurationDTO(
        mode="MODE_B",
        daily_quota_minutes={"monday": 180, "tuesday": 180},
        default_daily_quota_minutes=180,
        availability_slots=(
            AvailabilitySlotDTO("monday", time(18, 0), time(21, 0), is_active=True),
            AvailabilitySlotDTO("tuesday", time(18, 0), time(21, 0), is_active=True),
        ),
        disabled_weekdays=frozenset(),
        timezone="Asia/Ho_Chi_Minh",
    )
    SpatioTemporalRuleEngine.allocate_task_sessions(
        [{"task_id": "no_cap", "milestone_id": "m1", "title": "NoCap", "estimated_minutes": 45}],
        availability=AvailabilityConfigurationDTO(mode="MODE_B", availability_slots=()),
        start_date=d0,
        target_date=d0 + timedelta(days=7),
        preferred_session_minutes=5,
    )
    SpatioTemporalRuleEngine.allocate_task_sessions(
        [{"task_id": "z0", "milestone_id": "m1", "title": "Zero", "estimated_minutes": 0}],
        availability=avail_sessions,
        start_date=d0,
        target_date=d0 + timedelta(days=7),
    )
    sessions_out, blocks_out = SpatioTemporalRuleEngine.allocate_task_sessions(
        [
            {"task_id": "s1", "milestone_id": "m1", "title": "Small", "estimated_minutes": 15},
            {"task_id": "s2", "milestone_id": "m1", "title": "Medium", "estimated_minutes": 90},
        ],
        availability=avail_sessions,
        start_date=d0,
        target_date=d0 + timedelta(days=7),
        dependencies=[{"predecessor_id": "s1", "successor_id": "s2", "is_mandatory": True}],
        estimation_bias_beta=0.5,
        preferred_session_minutes=45,
        peak_productivity_slots=["monday"],
        buffer_minutes_per_week=15,
        daily_workload_cap_minutes=90,
    )
    assert len(sessions_out) == 2
    assert len(blocks_out) >= 1


# ---------------------------------------------------------------------------
# 4. Resilience Use Cases (UC-22, Reoptimize, UC-23) & Faithfulness Validator
# ---------------------------------------------------------------------------


class _FakeUow:
    def __init__(self) -> None:
        self.committed = False

    async def __aenter__(self) -> _FakeUow:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        return None


class _FakeGoalRepo:
    def __init__(self, goal: Goal) -> None:
        self.goal = goal

    async def get_by_id(self, goal_id: UUID) -> Goal | None:
        return self.goal if self.goal.id == goal_id else None

    async def get_by_id_for_user(self, goal_id: UUID, user_id: UUID) -> Goal | None:
        return self.goal if self.goal.id == goal_id and self.goal.user_id == user_id else None

    async def save(self, goal: Goal) -> Goal:
        self.goal = goal
        return goal


class _FakeRoadmapRepo:
    def __init__(self, roadmap: Roadmap) -> None:
        self.roadmap = roadmap

    async def get_by_id_for_user(self, roadmap_id: UUID, user_id: UUID) -> Roadmap | None:
        return (
            self.roadmap
            if self.roadmap.id == roadmap_id and self.roadmap.user_id == user_id
            else None
        )

    async def save(self, roadmap: Roadmap) -> Roadmap:
        self.roadmap = roadmap
        return roadmap

    async def count_active_by_user_id(
        self, user_id: UUID, *, exclude_roadmap_id: UUID | None = None
    ) -> int:
        return 0

    async def list_by_user_id(self, user_id: UUID, *, status: str | None = None) -> list[Roadmap]:
        return [self.roadmap]


class _FakeScheduleRepo:
    def __init__(self, schedule: OfficialSchedule | None) -> None:
        self.schedule = schedule

    async def get_by_roadmap_id(self, roadmap_id: UUID) -> OfficialSchedule | None:
        return self.schedule if self.schedule and self.schedule.roadmap_id == roadmap_id else None


class _FakeMilestoneRepo:
    def __init__(self, milestones: list[Milestone]) -> None:
        self.milestones = milestones

    async def list_by_roadmap_id(self, roadmap_id: UUID) -> list[Milestone]:
        return [m for m in self.milestones if m.roadmap_id == roadmap_id]


class _FakeProposalRepo:
    def __init__(self) -> None:
        self.saved: list[ScheduleProposal] = []

    async def discard_existing_drafts(self, roadmap_id: UUID, now: datetime) -> int:
        return 0

    async def save(self, proposal: ScheduleProposal) -> ScheduleProposal:
        self.saved.append(proposal)
        return proposal


class _FakeAvailabilityPort:
    async def get_active_availability(self, user_id: UUID) -> None:
        return None


class _FakeExecutionSyncPort:
    def __init__(self, overdue_tasks: list[ExistingScheduledTaskDTO]) -> None:
        self.overdue_tasks = overdue_tasks
        self.shifted_calls: list[int] = []

    async def shift_incomplete_tasks_for_domino(
        self,
        *,
        roadmap_id: UUID,
        shift_days: int,
        now: datetime,
    ) -> int:
        self.shifted_calls.append(shift_days)
        return len(self.overdue_tasks)

    async def get_tasks_for_roadmaps(
        self,
        roadmap_ids: list[UUID],
        *,
        roadmap_target_dates: dict[UUID, date | None] | None = None,
    ) -> list[ExistingScheduledTaskDTO]:
        return [t for t in self.overdue_tasks if t.roadmap_id in roadmap_ids]

    async def list_existing_scheduled_tasks(self, **kwargs: Any) -> list[ExistingScheduledTaskDTO]:
        return list(self.overdue_tasks)


class _FakeChangeLogPort:
    def __init__(self) -> None:
        self.logs: list[dict[str, Any]] = []

    async def record_change_log(self, **kwargs: Any) -> None:
        self.logs.append(kwargs)


class _FakeSseStore:
    def __init__(self) -> None:
        self.jobs: list[SseJobTicketDTO] = []
        self.events: list[dict[str, Any]] = []

    async def create_job(self, **kwargs: Any) -> SseJobTicketDTO:
        t = SseJobTicketDTO(
            job_id=kwargs["job_id"],
            reservation_id=kwargs["reservation_id"],
            roadmap_id=kwargs["roadmap_id"],
            job_type=kwargs["job_type"],
            status="QUEUED",
            stream_url="/sse/jobs/1",
        )
        self.jobs.append(t)
        return t

    async def append_event(self, **kwargs: Any) -> None:
        self.events.append(kwargs)


@pytest.mark.asyncio
async def test_resilience_use_cases_pause_resume_reoptimize_and_overdue() -> None:
    uid = uuid5(NAMESPACE_DNS, "u-res")
    gid = uuid5(NAMESPACE_DNS, "g-res")
    rid = uuid5(NAMESPACE_DNS, "r-res")
    mid = uuid5(NAMESPACE_DNS, "m-res")
    now = datetime(2026, 11, 10, 9, 0, tzinfo=UTC)

    goal = Goal(
        id=gid,
        user_id=uid,
        title="Backend Mastery",
        status=GoalStatus.ACTIVE,
        target_date=date(2026, 12, 10),
        created_at=now,
        updated_at=now,
    )
    roadmap = Roadmap(
        id=rid,
        user_id=uid,
        goal_id=gid,
        title="Roadmap 1",
        status=RoadmapStatus.ACTIVE,
        start_date=date(2026, 11, 2),
        target_date=date(2026, 12, 10),
        created_at=now,
        updated_at=now,
    )
    schedule = OfficialSchedule(
        id=uuid4(),
        roadmap_id=rid,
        total_sessions=2,
        total_planned_minutes=90,
        buffer_minutes_per_week=60,
        recovery_window_days=5,
        daily_workload_cap_minutes=120,
        stability_weight=0.75,
        activated_at=now,
        created_at=now,
        updated_at=now,
    )
    change_log = _FakeChangeLogPort()
    uow = _FakeUow()

    paused = await PauseRoadmapUseCase(
        roadmap_repo=_FakeRoadmapRepo(roadmap),
        schedule_repo=_FakeScheduleRepo(schedule),
        uow=uow,  # type: ignore[arg-type]
        schedule_change_log_port=change_log,  # type: ignore[arg-type]
    ).execute(user_id=uid, roadmap_id=rid, now=now)
    assert paused.status == RoadmapStatus.PAUSED
    assert change_log.logs[-1]["trigger_type"] == "ROADMAP_PAUSED"

    ext_task = ExistingScheduledTaskDTO(
        task_id=uuid4(),
        roadmap_id=rid,
        milestone_id=mid,
        title="Overdue Drill",
        scheduled_date=date(2026, 11, 4),
        scheduled_start=datetime(2026, 11, 4, 19, 0),
        scheduled_end=datetime(2026, 11, 4, 19, 45),
        estimated_minutes=45,
        status="TODO",
    )
    exec_port = _FakeExecutionSyncPort([ext_task])
    resumed = await ResumeRoadmapUseCase(
        goal_repo=_FakeGoalRepo(goal),  # type: ignore[arg-type]
        roadmap_repo=_FakeRoadmapRepo(paused),
        schedule_repo=_FakeScheduleRepo(schedule),
        uow=uow,  # type: ignore[arg-type]
        execution_sync_port=exec_port,  # type: ignore[arg-type]
        schedule_change_log_port=change_log,  # type: ignore[arg-type]
    ).execute(user_id=uid, roadmap_id=rid, shift_days=3, now=now + timedelta(days=3))
    assert resumed.status == RoadmapStatus.ACTIVE
    assert exec_port.shifted_calls == [3]

    milestone = Milestone(
        id=mid,
        roadmap_id=rid,
        title="Milestone 1",
        sequence_order=1,
        status=MilestoneStatus.PENDING,
        created_at=now,
        updated_at=now,
    )
    proposal_repo = _FakeProposalRepo()
    reopt_view = await ReoptimizeScheduleProposalUseCase(
        roadmap_repo=_FakeRoadmapRepo(resumed),
        milestone_repo=_FakeMilestoneRepo([milestone]),  # type: ignore[arg-type]
        proposal_repo=proposal_repo,  # type: ignore[arg-type]
        availability_query_port=_FakeAvailabilityPort(),  # type: ignore[arg-type]
        execution_sync_port=exec_port,  # type: ignore[arg-type]
        uow=uow,  # type: ignore[arg-type]
    ).execute(user_id=uid, roadmap_id=rid, now=now)
    assert reopt_view.proposal.proposal_type == ScheduleProposalType.SCHEDULE_ONLY_REOPTIMIZE

    sse_store = _FakeSseStore()
    ticket = await InitiateOverdueRecoveryUseCase(
        roadmap_repo=_FakeRoadmapRepo(resumed),
        milestone_repo=_FakeMilestoneRepo([milestone]),  # type: ignore[arg-type]
        proposal_repo=proposal_repo,  # type: ignore[arg-type]
        availability_query_port=_FakeAvailabilityPort(),  # type: ignore[arg-type]
        execution_sync_port=exec_port,  # type: ignore[arg-type]
        sse_job_store=sse_store,  # type: ignore[arg-type]
        uow=uow,  # type: ignore[arg-type]
    ).execute(user_id=uid, roadmap_id=rid, now=now)
    assert ticket.status == "COMPLETED"
    assert len(proposal_repo.saved) == 2

    sanitized, score = QuantitativeFaithfulnessValidator.validate_or_sanitize(
        "Bạn hoàn thành 120 phút trên tổng 180 phút.",
        [120, 180],
        "Fallback",
    )
    assert score == 1.0
    assert "120" in sanitized
