from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

import pytest
from uuid6 import uuid7

from src.account.public_api import (
    AvailabilitySnapshotDTO,
    CalendarBusyIntervalDTO,
    CalendarConnectionSnapshotDTO,
)
from src.execution.public_api import (
    ExistingScheduledTaskDTO,
    ScheduleSyncResultDTO,
)
from src.planning.application.services.effective_availability_service import (
    GetEffectiveAvailabilityUseCase,
)
from src.planning.application.use_cases.proposal_management_use_cases import (
    ApplyScheduleProposalUseCase,
)
from src.planning.domain.models.milestone import Milestone, MilestoneStatus
from src.planning.domain.models.roadmap import Roadmap, RoadmapStatus
from src.planning.domain.models.schedule import (
    OfficialSchedule,
    ScheduleProposal,
    ScheduleProposalStatus,
)
from src.planning.domain.models.schedule_block import ScheduleBlock
from src.planning.domain.services.milestone_effort_allocator import (
    DEFAULT_ALPHA_BY_LEVEL,
    MilestoneEffortAllocator,
)
from src.planning.domain.services.spatio_temporal_engine import (
    NonSplittableTaskClassifier,
    SpatioTemporalRuleEngine,
    _choose_slot_chunk,
)
from src.planning.domain.services.validation_types import (
    AvailabilityConfigurationDTO,
    AvailabilitySlotDTO,
    parse_iso_datetime,
)
from src.shared_kernel.config import get_settings

# =============================================================================
# DEF-07: Mode A Chronological task_end_anchor
# =============================================================================


@pytest.mark.parametrize("soft_pacing", [False, True])
def test_def07_mode_a_chronological_task_end_anchor_prevents_dag_inversion(
    soft_pacing: bool,
) -> None:
    """Mode A places evening (19:00-20:00) before daytime (09:00-09:30); anchor must be 20:00, not 09:30."""
    avail = AvailabilityConfigurationDTO(
        mode="MODE_A",
        default_daily_quota_minutes=390,
        daily_quota_minutes={"monday": 390, "tuesday": 120},
        timezone="UTC",
    )
    # Existing task occupies 20:00-24:00 (240m) on Monday 2026-11-16, leaving:
    # - 60m in evening (19:00-20:00)
    # - 600m in daytime (09:00-19:00)
    # - 150m remaining daily quota on Monday (390 - 240 = 150m)
    existing = [
        ExistingScheduledTaskDTO(
            task_id=uuid7(),
            roadmap_id=uuid7(),
            milestone_id=uuid7(),
            title="Existing Evening Block",
            scheduled_date=date(2026, 11, 16),
            scheduled_start=datetime(2026, 11, 16, 20, 0, tzinfo=UTC),
            scheduled_end=datetime(2026, 11, 17, 0, 0, tzinfo=UTC),
            estimated_minutes=240,
            status="TODO",
            roadmap_target_date=date(2026, 11, 17),
        )
    ]
    tasks = [
        {
            "task_id": "T1",
            "milestone_id": "M1",
            "title": "Predecessor Splittable",
            "estimated_minutes": 90,
            "task_order": 0,
        },
        {
            "task_id": "T2",
            "milestone_id": "M1",
            "title": "Successor",
            "estimated_minutes": 60,
            "task_order": 1,
        },
    ]
    deps = [{"predecessor_id": "T1", "successor_id": "T2", "is_mandatory": True}]

    res = SpatioTemporalRuleEngine.allocate_task_sessions_with_diagnostics(
        tasks,
        avail,
        start_date=date(2026, 11, 16),
        target_date=date(2026, 11, 17),
        dependencies=deps,
        existing_tasks=existing,
        preferred_session_minutes=60,
        soft_pacing_v2_enabled=soft_pacing,
    )
    assert res.feasibility_verdict == "VERIFIED_FEASIBLE"
    by_id = {t["task_id"]: t for t in res.tasks}
    t1_end = parse_iso_datetime(by_id["T1"]["scheduled_end"])
    t2_start = parse_iso_datetime(by_id["T2"]["scheduled_start"])
    assert t1_end is not None and t2_start is not None
    assert t1_end <= t2_start, f"DAG violated: T1 ends {t1_end} > T2 starts {t2_start}"


# =============================================================================
# DEF-08: _choose_slot_chunk Tail Check, Phase 2 eff_w vs w, & NC-1 min_unit
# =============================================================================


def test_def08_choose_slot_chunk_checks_slot_tail_and_phase2_cap() -> None:
    # Whole-fit 90m in a 110m window leaves a 20m sliver (<30m) when allow_slot_sliver=False
    chunk_110 = _choose_slot_chunk(
        rem_effort=90,
        window_width=110,
        preferred_session_minutes=60,
        allow_slot_sliver=False,
    )
    assert chunk_110 == 60, f"Expected 60 (no 20m tail), got {chunk_110}"

    # Whole-fit 60m in an 80m window leaves a 20m sliver (<30m)
    chunk_80 = _choose_slot_chunk(
        rem_effort=60,
        window_width=80,
        preferred_session_minutes=60,
        allow_slot_sliver=False,
    )
    assert chunk_80 == 30, f"Expected 30 (no 20m tail), got {chunk_80}"


def test_def08_phase2_soft_pass_respects_physical_slot_tail_and_multi_task_chunking() -> None:
    avail = AvailabilityConfigurationDTO(
        mode="MODE_B",
        availability_slots=(
            AvailabilitySlotDTO("monday", "19:00", "21:20"),  # 140m physical slot
            AvailabilitySlotDTO("tuesday", "19:00", "21:20"),
            AvailabilitySlotDTO("wednesday", "19:00", "21:20"),
            AvailabilitySlotDTO("thursday", "19:00", "21:20"),
        ),
        timezone="UTC",
    )
    ctx = SpatioTemporalRuleEngine._build_calendar_context(avail)
    tasks = [
        {"task_id": "T1", "milestone_id": "M1", "title": "Task 1", "estimated_minutes": 180},
        {"task_id": "T2", "milestone_id": "M1", "title": "Task 2", "estimated_minutes": 180},
    ]
    effs = [180, 180]
    cls_list = [(False, "DEFAULT_SPLITTABLE"), (False, "DEFAULT_SPLITTABLE")]
    study_days = [
        date(2026, 11, 16),
        date(2026, 11, 17),
        date(2026, 11, 18),
        date(2026, 11, 19),
    ]
    # day_soft_cap will be ~120m (raw_avg=90 -> paced_cap=90, max(pref=90,90)=90 or 120)
    # With pref=120, day_soft_cap=120m while physical slot width w=140m.
    # If eff_w=120 was passed to _choose_slot_chunk, chunk=120 leaves a 20m physical sliver (140-120=20m)!
    _, blocks, unplaced = SpatioTemporalRuleEngine._run_phase2_soft_pass(
        tasks,
        ctx,
        study_days=study_days,
        dependencies=[],
        milestone_order_map={"M1": 1},
        preferred_session_minutes=120,
        effective_efforts=effs,
        classifications=cls_list,
        use_daily_soft_cap=True,
        use_even_spread=False,
        avoid_partial_day_split=False,
        allow_slot_sliver=False,
    )
    assert not unplaced
    # Verify no physical 20m sliver was stranded on any 140m slot if another block couldn't use it
    # With w=140 and max_chunk=120, valid tail on 140m slot is <= 110m (140-110=30m) or 140m (tail=0)
    first_day_blocks = [b for b in blocks if b["block_date"] == "2026-11-16"]
    assert all(b["scheduled_duration_minutes"] <= 110 for b in first_day_blocks)


def test_def08_nc1_manual_15m_task_does_not_lower_min_unit_for_large_tasks() -> None:
    # 10 days with ONLY a 20m slot each (200m total, ZERO >=30m slots).
    # Tasks: one 15m manual task + two 60m tasks (135m total).
    # 60m tasks cannot use 20m slots! NC-1 must fail instead of counting 200m as packable.
    avail = AvailabilityConfigurationDTO(
        mode="MODE_B",
        availability_slots=tuple(
            AvailabilitySlotDTO(day, "19:00", "19:20")
            for day in (
                "monday",
                "tuesday",
                "wednesday",
                "thursday",
                "friday",
                "saturday",
                "sunday",
            )
        ),
        timezone="UTC",
    )
    tasks = [
        {"task_id": "T_small", "title": "15m review", "estimated_minutes": 15},
        {"task_id": "T_big1", "title": "Big 1", "estimated_minutes": 60},
        {"task_id": "T_big2", "title": "Big 2", "estimated_minutes": 60},
    ]
    nc = SpatioTemporalRuleEngine.verify_necessary_conditions(
        tasks,
        avail,
        start_date=date(2026, 11, 16),
        target_date=date(2026, 11, 25),
    )
    assert nc.nc1_passed is False
    assert nc.verdict == "EXPLICIT_UNSCHEDULABLE"


# =============================================================================
# DEF-09: Cross-Midnight Split, Carryover, Mode A Overlap, Google Recurring
# =============================================================================


def test_def09_cross_midnight_occupied_split_and_mode_b_carryover() -> None:
    # Monday has 23:00-01:00 (+1d), Tuesday has 00:00-02:00.
    # Existing task occupies Monday 23:00 -> Tuesday 01:00 (120m).
    # New 60m task on Tuesday MUST be placed at 01:00-02:00, NOT 00:00-01:00!
    avail = AvailabilityConfigurationDTO(
        mode="MODE_B",
        availability_slots=(
            AvailabilitySlotDTO("monday", "23:00", "01:00", end_day_offset=1),
            AvailabilitySlotDTO("tuesday", "00:00", "02:00", end_day_offset=0),
        ),
        timezone="UTC",
    )
    existing = [
        ExistingScheduledTaskDTO(
            task_id=uuid7(),
            roadmap_id=uuid7(),
            milestone_id=uuid7(),
            title="Overnight Existing",
            scheduled_date=date(2026, 11, 16),
            scheduled_start=datetime(2026, 11, 16, 23, 0, tzinfo=UTC),
            scheduled_end=datetime(2026, 11, 17, 1, 0, tzinfo=UTC),
            estimated_minutes=120,
            status="TODO",
            roadmap_target_date=date(2026, 11, 20),
        )
    ]
    tasks = [
        {"task_id": "T1", "milestone_id": "M1", "title": "Morning Task", "estimated_minutes": 60}
    ]
    res = SpatioTemporalRuleEngine.allocate_task_sessions_with_diagnostics(
        tasks,
        avail,
        start_date=date(2026, 11, 16),
        target_date=date(2026, 11, 17),
        existing_tasks=existing,
    )
    assert res.feasibility_verdict == "VERIFIED_FEASIBLE"
    placed_start = parse_iso_datetime(res.tasks[0]["scheduled_start"])
    assert placed_start == datetime(2026, 11, 17, 1, 0, tzinfo=UTC)

    # Also test carryover slot when Tuesday has NO own slots, only Monday 23:00-01:00 (+1d),
    # and Monday 23:00-24:00 is occupied so Tuesday 00:00-01:00 is free via carryover!
    avail_carry = AvailabilityConfigurationDTO(
        mode="MODE_B",
        availability_slots=(AvailabilitySlotDTO("monday", "23:00", "01:00", end_day_offset=1),),
        timezone="UTC",
    )
    existing_mon = [
        ExistingScheduledTaskDTO(
            task_id=uuid7(),
            roadmap_id=uuid7(),
            milestone_id=uuid7(),
            title="Mon 23-24",
            scheduled_date=date(2026, 11, 16),
            scheduled_start=datetime(2026, 11, 16, 23, 0, tzinfo=UTC),
            scheduled_end=datetime(2026, 11, 17, 0, 0, tzinfo=UTC),
            estimated_minutes=60,
            status="TODO",
            roadmap_target_date=date(2026, 11, 20),
        )
    ]
    res_carry = SpatioTemporalRuleEngine.allocate_task_sessions_with_diagnostics(
        [
            {
                "task_id": "T_carry",
                "milestone_id": "M1",
                "title": "Carryover",
                "estimated_minutes": 60,
            }
        ],
        avail_carry,
        start_date=date(2026, 11, 17),
        target_date=date(2026, 11, 17),
        existing_tasks=existing_mon,
    )
    assert res_carry.feasibility_verdict == "VERIFIED_FEASIBLE"
    assert parse_iso_datetime(res_carry.tasks[0]["scheduled_start"]) == datetime(
        2026, 11, 17, 0, 0, tzinfo=UTC
    )


def test_def09_validate_mode_b_and_mode_a_cross_midnight_and_timed_overlaps() -> None:
    # Mode B cross-midnight self-overlap & EDF overlap
    avail_b = AvailabilityConfigurationDTO(
        mode="MODE_B",
        availability_slots=(
            AvailabilitySlotDTO("monday", "23:00", "01:00", end_day_offset=1),
            AvailabilitySlotDTO("tuesday", "00:30", "01:30"),
        ),
        timezone="UTC",
    )
    v_self, _ = SpatioTemporalRuleEngine.validate_mode_b_slots(
        tasks=[
            {
                "task_id": "A",
                "title": "Late Mon",
                "estimated_minutes": 120,
                "scheduled_date": "2026-11-16",
                "scheduled_start": "2026-11-16T23:00:00+00:00",
                "scheduled_end": "2026-11-17T01:00:00+00:00",
            },
            {
                "task_id": "B",
                "title": "Early Tue",
                "estimated_minutes": 60,
                "scheduled_date": "2026-11-17",
                "scheduled_start": "2026-11-17T00:30:00+00:00",
                "scheduled_end": "2026-11-17T01:30:00+00:00",
            },
        ],
        availability=avail_b,
    )
    assert any(v.rule_code == "TASK_TIME_OVERLAP" for v in v_self)

    existing_cross = [
        ExistingScheduledTaskDTO(
            task_id=uuid7(),
            roadmap_id=uuid7(),
            milestone_id=uuid7(),
            title="Existing Overnight",
            scheduled_date=date(2026, 11, 16),
            scheduled_start=datetime(2026, 11, 16, 23, 0, tzinfo=UTC),
            scheduled_end=datetime(2026, 11, 17, 1, 0, tzinfo=UTC),
            estimated_minutes=120,
            status="TODO",
            roadmap_target_date=date(2026, 11, 20),
        )
    ]
    v_edf, _ = SpatioTemporalRuleEngine.validate_mode_b_slots(
        tasks=[
            {
                "task_id": "B",
                "title": "Early Tue",
                "estimated_minutes": 60,
                "scheduled_date": "2026-11-17",
                "scheduled_start": "2026-11-17T00:30:00+00:00",
                "scheduled_end": "2026-11-17T01:30:00+00:00",
            }
        ],
        availability=avail_b,
        existing_tasks=existing_cross,
        current_roadmap_target_date=date(2026, 11, 25),
    )
    assert any(v.rule_code == "CROSS_ROADMAP_EDF_SLOT_CONFLICT" for v in v_edf)

    # Mode A timed self-overlap & EDF overlap (including cross-midnight)
    avail_a = AvailabilityConfigurationDTO(
        mode="MODE_A", default_daily_quota_minutes=240, timezone="UTC"
    )
    va_self = SpatioTemporalRuleEngine.validate_mode_a_quota(
        tasks=[
            {
                "task_id": "A1",
                "title": "Mon Night",
                "estimated_minutes": 120,
                "scheduled_date": "2026-11-16",
                "scheduled_start": "2026-11-16T23:00:00+00:00",
                "scheduled_end": "2026-11-17T01:00:00+00:00",
            },
            {
                "task_id": "A2",
                "title": "Tue Overlap",
                "estimated_minutes": 60,
                "scheduled_date": "2026-11-17",
                "scheduled_start": "2026-11-17T00:30:00+00:00",
                "scheduled_end": "2026-11-17T01:30:00+00:00",
            },
        ],
        availability=avail_a,
    )
    assert any(v.rule_code == "TASK_TIME_OVERLAP" for v in va_self)

    va_edf = SpatioTemporalRuleEngine.validate_mode_a_quota(
        tasks=[
            {
                "task_id": "A2",
                "title": "Tue Overlap",
                "estimated_minutes": 60,
                "scheduled_date": "2026-11-17",
                "scheduled_start": "2026-11-17T00:30:00+00:00",
                "scheduled_end": "2026-11-17T01:30:00+00:00",
            }
        ],
        availability=avail_a,
        existing_tasks=existing_cross,
        current_roadmap_target_date=date(2026, 11, 25),
    )
    assert any(v.rule_code == "CROSS_ROADMAP_EDF_SLOT_CONFLICT" for v in va_edf)


@pytest.mark.asyncio
async def test_def09_effective_availability_multiweek_no_carve_and_no_dropped_committed() -> None:
    user_id = uuid7()

    class FakeAvailPort:
        async def get_active_availability(self, uid: UUID) -> AvailabilitySnapshotDTO | None:
            del uid
            return AvailabilitySnapshotDTO(
                user_id=user_id,
                mode="MODE_A",
                daily_cap_minutes=120,
                weekly_capacity_minutes=840,
                calendar_integration_mode="CONNECTED",
                allowed_window_start="07:00",
                allowed_window_end="24:00",
                min_session_minutes=30,
            )

    class FakeCalPort:
        async def get_connection_snapshot(
            self, user_id: UUID, provider: str = "GOOGLE"
        ) -> CalendarConnectionSnapshotDTO | None:
            del provider
            return CalendarConnectionSnapshotDTO(
                user_id=user_id,
                provider="GOOGLE",
                sync_status="ACTIVE",
                external_calendar_id="primary",
                source_calendars=("primary",),
                last_synced_at="2026-11-16T00:00:00+00:00",
                is_active=True,
            )

        async def get_free_busy_intervals(
            self, user_id: UUID, time_min: datetime, time_max: datetime, provider: str = "GOOGLE"
        ) -> list[CalendarBusyIntervalDTO]:
            del user_id, time_min, time_max, provider
            # Date-specific Google meeting ONLY on 2026-11-16 (Monday Week 1)
            return [
                CalendarBusyIntervalDTO(
                    start_time=datetime(2026, 11, 16, 9, 0, tzinfo=UTC),
                    end_time=datetime(2026, 11, 16, 12, 0, tzinfo=UTC),
                )
            ]

    committed_wed = ExistingScheduledTaskDTO(
        task_id=uuid7(),
        roadmap_id=uuid7(),
        milestone_id=uuid7(),
        title="Committed Wed Task",
        scheduled_date=date(2026, 11, 18),
        scheduled_start=datetime(2026, 11, 18, 19, 0, tzinfo=UTC),
        scheduled_end=datetime(2026, 11, 18, 20, 0, tzinfo=UTC),
        estimated_minutes=60,
        status="TODO",
    )
    committed_overnight = ExistingScheduledTaskDTO(
        task_id=uuid7(),
        roadmap_id=uuid7(),
        milestone_id=uuid7(),
        title="Committed Overnight",
        scheduled_date=date(2026, 11, 20),
        scheduled_start=datetime(2026, 11, 20, 23, 0, tzinfo=UTC),
        scheduled_end=datetime(2026, 11, 21, 1, 0, tzinfo=UTC),
        estimated_minutes=120,
        status="TODO",
    )

    uc = GetEffectiveAvailabilityUseCase(
        availability_query_port=FakeAvailPort(),  # type: ignore[arg-type]
        calendar_connection_query_port=FakeCalPort(),  # type: ignore[arg-type]
    )
    # 3-week range (len(occurrences) > 1 for every weekday)
    eff = await uc.execute(
        user_id=user_id,
        start_date=date(2026, 11, 16),
        target_date=date(2026, 12, 6),
        timezone="UTC",
        existing_tasks=[committed_wed, committed_overnight],
    )
    monday_slots = [
        s for s in eff.availability_config.availability_slots if s.day_of_week == "monday"
    ]
    # Must NOT carve Nov 16 09:00-12:00 out of all future Mondays; and 24:00 must NOT truncate to 23:59
    assert len(monday_slots) == 1
    assert monday_slots[0].start_time == "07:00"
    assert monday_slots[0].end_time == "00:00"
    assert monday_slots[0].end_day_offset == 1

    # Both committed tasks AND date-specific Google busy event must be present in effective_existing_tasks
    eff_titles = {getattr(t, "title", None) for t in eff.effective_existing_tasks}
    assert "Committed Wed Task" in eff_titles
    assert "Committed Overnight" in eff_titles
    assert "Google Calendar Busy" in eff_titles


# =============================================================================
# DEF-10: MilestoneEffortAllocator Case 1B, Case 2/3, ADVANCED alpha
# =============================================================================


def test_def10_allocator_case1b_floor_cap_case3_and_advanced_alpha() -> None:
    # 1. ADVANCED alpha <= INTERMEDIATE
    assert DEFAULT_ALPHA_BY_LEVEL["ADVANCED"] == 0.85
    assert DEFAULT_ALPHA_BY_LEVEL["ADVANCED"] <= DEFAULT_ALPHA_BY_LEVEL["INTERMEDIATE"]
    assert get_settings().ai_milestone_alpha_advanced == 0.85

    # 2. Case 1B with sum_llm <= p_hard < sum(m_floors): MUST NOT exceed p_hard or drop < m_floor
    small_llm_milestones = [
        {
            "sequence_order": 1,
            "title": "M1",
            "learning_outcomes": ["O1"],
            "completion_criteria": "Quiz",
            "estimated_effort_minutes": 30,
            "required_concepts": ["c1"],
            "dependencies": [],
        },
        {
            "sequence_order": 2,
            "title": "M2",
            "learning_outcomes": ["O2"],
            "completion_criteria": "Quiz",
            "estimated_effort_minutes": 30,
            "required_concepts": ["c2"],
            "dependencies": [1],
        },
    ]
    res_1b = MilestoneEffortAllocator.allocate(
        small_llm_milestones,
        hard_packable_capacity_minutes=90,  # sum_llm=60 <= 90 < sum(m_floors)=120
        prior_knowledge_level="INTERMEDIATE",
    )
    assert res_1b.status != "FULL_SCOPE_FEASIBLE"
    assert res_1b.status == "FIT_CAPACITY_REQUIRES_APPROVAL"
    assert len(res_1b.kept_scope) == 1
    assert res_1b.normalized_planned_total_minutes <= 90
    assert all(item["normalized_planned_effort_minutes"] >= 60 for item in res_1b.kept_scope)

    # 3. Case 3 when e_mins[0] > p_hard even if llm_efforts[0] <= p_hard (capstone m_floor=90 > p_hard=60)
    capstone_first = [
        {
            "sequence_order": 1,
            "title": "Capstone M1",
            "learning_outcomes": ["O1", "O2"],
            "completion_criteria": "Capstone deliverable",
            "estimated_effort_minutes": 60,
            "required_concepts": ["c1", "c2"],
            "dependencies": [],
        },
        {
            "sequence_order": 2,
            "title": "M2",
            "learning_outcomes": ["O3"],
            "completion_criteria": "Lab",
            "estimated_effort_minutes": 120,
            "required_concepts": ["c3"],
            "dependencies": [1],
        },
    ]
    res_case3 = MilestoneEffortAllocator.allocate(
        capstone_first,
        hard_packable_capacity_minutes=60,
        prior_knowledge_level="BEGINNER",
    )
    assert res_case3.status == "PRELIMINARY_UNSCHEDULABLE"
    assert res_case3.kept_scope == ()


# =============================================================================
# DEF-12: NC-3b Predecessor Budget Deduction & Phase 2 daily_workload_cap_minutes
# =============================================================================


def test_def12_nc3b_predecessor_budget_deduction_and_phase2_daily_cap() -> None:
    # 2 days * 60m = 120m total capacity. Chain T1(40m)->T2(40m)->T3(40m) = 120m.
    # Because T1 leaves 20m (<30m min_unit) on day 1 and T2 leaves 20m on day 2, T3 cannot fit!
    avail = AvailabilityConfigurationDTO(
        mode="MODE_A",
        default_daily_quota_minutes=60,
        timezone="UTC",
    )
    tasks = [
        {"task_id": "T1", "title": "T1", "estimated_minutes": 40},
        {"task_id": "T2", "title": "T2", "estimated_minutes": 40},
        {"task_id": "T3", "title": "T3", "estimated_minutes": 40},
    ]
    deps = [
        {"predecessor_id": "T1", "successor_id": "T2", "is_mandatory": True},
        {"predecessor_id": "T2", "successor_id": "T3", "is_mandatory": True},
    ]
    nc = SpatioTemporalRuleEngine.verify_necessary_conditions(
        tasks,
        avail,
        start_date=date(2026, 11, 16),
        target_date=date(2026, 11, 17),
        dependencies=deps,
    )
    assert nc.nc1_passed is True
    assert nc.nc3_passed is False
    assert nc.verdict == "EXPLICIT_UNSCHEDULABLE"

    # Phase 2 validator must reject candidate exceeding daily_workload_cap_minutes inclusive of existing_tasks
    avail_cap = AvailabilityConfigurationDTO(
        mode="MODE_A", default_daily_quota_minutes=240, timezone="UTC"
    )
    existing = [
        ExistingScheduledTaskDTO(
            task_id=uuid7(),
            roadmap_id=uuid7(),
            milestone_id=uuid7(),
            title="Existing 60m",
            scheduled_date=date(2026, 11, 16),
            scheduled_start=datetime(2026, 11, 16, 19, 0, tzinfo=UTC),
            scheduled_end=datetime(2026, 11, 16, 20, 0, tzinfo=UTC),
            estimated_minutes=60,
            status="TODO",
        )
    ]
    errs = SpatioTemporalRuleEngine._validate_phase2_candidate(
        cand_tasks=[
            {
                "task_id": "T_new",
                "title": "New 90m",
                "estimated_minutes": 90,
                "scheduled_date": "2026-11-16",
                "scheduled_start": "2026-11-16T20:00:00+00:00",
                "scheduled_end": "2026-11-16T21:30:00+00:00",
            }
        ],
        cand_blocks=[
            {
                "task_id": "T_new",
                "sequence_in_task": 1,
                "block_date": "2026-11-16",
                "scheduled_start": "2026-11-16T20:00:00+00:00",
                "scheduled_end": "2026-11-16T21:30:00+00:00",
                "scheduled_duration_minutes": 90,
            }
        ],
        availability=avail_cap,
        start_date=date(2026, 11, 16),
        target_date=date(2026, 11, 20),
        dependencies=[],
        existing_tasks=existing,
        effective_efforts=[90],
        classifications=[(False, "DEFAULT_SPLITTABLE")],
        hard_split_tasks=0,
        hard_extra_spans=0,
        daily_workload_cap_minutes=120,
    )
    assert any("DAILY_WORKLOAD_CAP_EXCEEDED" in e for e in errs)


# =============================================================================
# DEF-13: NonSplittableTaskClassifier & Manual >120m Block Preservation
# =============================================================================


def test_def13_classifier_rules_and_metadata_fields() -> None:
    assert NonSplittableTaskClassifier.classify({"title": "Mock Exam: AWS SAA"}) == (
        True,
        "DETERMINISTIC_RULE",
    )
    assert NonSplittableTaskClassifier.classify({"title": "Setup benchmark environment"}) == (
        False,
        "DEFAULT_SPLITTABLE",
    )
    assert NonSplittableTaskClassifier.classify({"title": "Benchmark test for latency"}) == (
        True,
        "DETERMINISTIC_RULE",
    )
    assert NonSplittableTaskClassifier.classify(
        {
            "title": "Luyện tập tổng hợp",
            "completion_criteria": "Hoàn thành bài kiểm tra dạng Mock Exam 120 phút",
        }
    ) == (True, "DETERMINISTIC_RULE")
    assert NonSplittableTaskClassifier.classify(
        {
            "title": "Thực hành kiến trúc",
            "learning_objective": "Vượt qua timed exam dưới áp lực thời gian",
        }
    ) == (True, "DETERMINISTIC_RULE")


@pytest.mark.asyncio
async def test_def13_apply_fallback_preserves_single_contiguous_block_up_to_240m() -> None:
    now = datetime(2026, 11, 16, 8, 0, tzinfo=UTC)
    user_id = uuid7()
    roadmap_id = uuid7()
    milestone_id = uuid7()
    proposal_id = uuid7()
    task_id = uuid7()

    roadmap = Roadmap(
        id=roadmap_id,
        user_id=user_id,
        goal_id=uuid7(),
        title="Mock Exam Prep",
        start_date=date(2026, 11, 16),
        target_date=date(2026, 11, 20),
        status=RoadmapStatus.INITIALIZED,
        created_at=now,
        updated_at=now,
    )
    milestone = Milestone(
        id=milestone_id,
        roadmap_id=roadmap_id,
        sequence_order=1,
        title="M1",
        estimated_effort_minutes=180,
        status=MilestoneStatus.APPROVED,
        created_at=now,
        updated_at=now,
    )
    # Proposal WITHOUT schedule_blocks (e.g. manual/edit plan) containing a 180m Mock Exam
    proposal = ScheduleProposal(
        id=proposal_id,
        roadmap_id=roadmap_id,
        user_id=user_id,
        proposal_data={
            "source": "MANUAL",
            "tasks": [
                {
                    "task_id": str(task_id),
                    "milestone_id": str(milestone_id),
                    "title": "Mock Exam: Full 3-Hour Simulation",
                    "learning_objective": "Complete full mock exam",
                    "completion_criteria": "Score >= 80%",
                    "estimated_minutes": 180,
                    "scheduled_date": "2026-11-16",
                    "scheduled_start": "2026-11-16T18:00:00+00:00",
                    "scheduled_end": "2026-11-16T21:00:00+00:00",
                }
            ],
            "dependencies": [],
        },
        status=ScheduleProposalStatus.DRAFT,
        created_at=now,
        updated_at=now,
    )

    class RRepo:
        def __init__(self) -> None:
            self.r = roadmap

        async def get_by_id_for_user(self, rid: UUID, uid: UUID) -> Roadmap | None:
            return self.r if rid == roadmap_id and uid == user_id else None

        async def list_by_user_id(self, uid: UUID, status: str | None = None) -> list[Roadmap]:
            del uid, status
            return []

        async def count_active_by_user_id(
            self, uid: UUID, exclude_roadmap_id: UUID | None = None
        ) -> int:
            del uid, exclude_roadmap_id
            return 0

        async def save(self, r: Roadmap) -> Roadmap:
            self.r = r
            return r

    class MRepo:
        async def list_by_roadmap_id(self, rid: UUID) -> list[Milestone]:
            del rid
            return [milestone]

    class PRepo:
        def __init__(self) -> None:
            self.p = proposal

        async def get_by_id(self, pid: UUID) -> ScheduleProposal | None:
            return self.p if pid == proposal_id else None

        async def save(self, p: ScheduleProposal) -> ScheduleProposal:
            self.p = p
            return p

    class SRepo:
        def __init__(self) -> None:
            self.s: OfficialSchedule | None = None

        async def get_by_roadmap_id(self, rid: UUID) -> OfficialSchedule | None:
            del rid
            return self.s

        async def save(self, s: OfficialSchedule) -> OfficialSchedule:
            self.s = s
            return s

    class BRepo:
        def __init__(self) -> None:
            self.blocks: list[ScheduleBlock] = []

        async def get_by_schedule_id(self, sid: UUID) -> list[ScheduleBlock]:
            del sid
            return list(self.blocks)

        async def list_by_roadmap_ids(self, rids: list[UUID]) -> list[ScheduleBlock]:
            del rids
            return []

        async def save_all(self, blocks: list[ScheduleBlock]) -> list[ScheduleBlock]:
            self.blocks = list(blocks)
            return self.blocks

    class AvailPort:
        async def get_active_availability(self, uid: UUID) -> AvailabilitySnapshotDTO | None:
            del uid
            return AvailabilitySnapshotDTO(
                user_id=user_id,
                mode="MODE_A",
                daily_cap_minutes=240,
                weekly_capacity_minutes=1680,
                calendar_integration_mode="NONE",
            )

    class ExecPort:
        async def get_tasks_for_roadmaps(self, *args: Any, **kwargs: Any) -> list[Any]:
            del args, kwargs
            return []

        async def sync_official_schedule_tasks(self, **kwargs: Any) -> ScheduleSyncResultDTO:
            tasks_in = kwargs["proposed_tasks"]
            return ScheduleSyncResultDTO(
                roadmap_id=roadmap_id,
                official_schedule_id=kwargs["official_schedule_id"],
                preserved_completed_tasks_count=0,
                replaced_tasks_count=0,
                inserted_tasks_count=len(tasks_in),
                affected_tasks_count=len(tasks_in),
                total_shifted_minutes=0,
                total_active_sessions=len(tasks_in),
                total_planned_minutes=180,
            )

    class LogPort:
        async def record_change_log(self, **kwargs: Any) -> None:
            del kwargs

    class UoW:
        async def __aenter__(self) -> UoW:
            return self

        async def __aexit__(self, *args: Any) -> None:
            del args

        async def commit(self) -> None:
            pass

        async def rollback(self) -> None:
            pass

        def collect_events_from(self, *args: Any) -> None:
            del args

    b_repo = BRepo()
    uc = ApplyScheduleProposalUseCase(
        roadmap_repo=RRepo(),  # type: ignore[arg-type]
        milestone_repo=MRepo(),  # type: ignore[arg-type]
        proposal_repo=PRepo(),  # type: ignore[arg-type]
        schedule_repo=SRepo(),  # type: ignore[arg-type]
        block_repo=b_repo,  # type: ignore[arg-type]
        availability_query_port=AvailPort(),  # type: ignore[arg-type]
        execution_sync_port=ExecPort(),  # type: ignore[arg-type]
        schedule_change_log_port=LogPort(),  # type: ignore[arg-type]
        uow=UoW(),  # type: ignore[arg-type]
    )
    await uc.execute(user_id=user_id, roadmap_id=roadmap_id, proposal_id=proposal_id, now=now)
    assert len(b_repo.blocks) == 1
    assert b_repo.blocks[0].scheduled_duration_minutes == 180
