from __future__ import annotations

from datetime import date, time
from typing import Any

from src.planning.domain.services.spatio_temporal_engine import (
    NonSplittableTaskClassifier,
    SpatioTemporalRuleEngine,
    _choose_slot_chunk,
    _record_occupied_interval,
    _slot_minute_range,
    _subtract_intervals,
)
from src.planning.domain.services.validation_types import (
    AvailabilityConfigurationDTO,
    AvailabilitySlotDTO,
)


class DummyTaskObj:
    def __init__(self, **kwargs: Any) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)


def test_helper_primitives_branches() -> None:
    # 1. _record_occupied_interval when end_min <= start_min (line 98)
    iv_map: dict[date, list[tuple[int, int]]] = {}
    used_map: dict[date, int] = {}
    _record_occupied_interval(iv_map, used_map, date(2026, 11, 2), 100, 50)
    assert not iv_map
    assert not used_map

    # Cross-midnight recording
    _record_occupied_interval(iv_map, used_map, date(2026, 11, 2), 1400, 1500)
    assert date(2026, 11, 2) in iv_map
    assert date(2026, 11, 3) in iv_map
    assert used_map[date(2026, 11, 2)] == 40
    assert used_map[date(2026, 11, 3)] == 60

    # 2. _subtract_intervals empty base (line 186)
    assert _subtract_intervals([], [(100, 200)]) == []

    # 3. _slot_minute_range cross midnight with time objects (line 82)
    s, e = _slot_minute_range(
        AvailabilitySlotDTO(
            day_of_week="monday",
            start_time=time(23, 0),
            end_time=time(1, 0),
            end_day_offset=0,
            is_active=True,
        )
    )
    assert s == 23 * 60
    assert e == 25 * 60

    # 4. _choose_slot_chunk boundary branches
    assert _choose_slot_chunk(rem_effort=0, window_width=60, preferred_session_minutes=60) is None
    assert _choose_slot_chunk(rem_effort=60, window_width=0, preferred_session_minutes=60) is None
    # max_chunk constraint on small effort (< 30m)
    assert (
        _choose_slot_chunk(
            rem_effort=25, window_width=60, preferred_session_minutes=60, max_chunk=15
        )
        is None
    )
    # Small effort with invalid slot tail without sliver
    assert (
        _choose_slot_chunk(
            rem_effort=20,
            window_width=35,
            preferred_session_minutes=60,
            allow_slot_sliver=False,
        )
        is None
    )
    # Small effort with allow_slot_sliver=True
    assert (
        _choose_slot_chunk(
            rem_effort=20,
            window_width=35,
            preferred_session_minutes=60,
            allow_slot_sliver=True,
        )
        == 20
    )
    # Whole-fit expand up to hard cap (lines 264-265)
    chunk = _choose_slot_chunk(
        rem_effort=120,
        window_width=120,
        preferred_session_minutes=45,
    )
    assert chunk == 120
    # Fallback allow_slot_sliver (lines 271, 273-274)
    chunk_sliver = _choose_slot_chunk(
        rem_effort=70,
        window_width=85,
        preferred_session_minutes=45,
        allow_slot_sliver=True,
    )
    assert chunk_sliver is not None


def test_classifier_all_patterns() -> None:
    # Vietnamese & English regex branches
    titles = [
        "Bài thi thử số 1",
        "Luyện đề thi đầy đủ",
        "Kiểm thử chịu tải cao hệ thống",
        "Thực hiện đối chuẩn benchmark test",
        "Đánh giá tổng hợp cuối kỳ",
        "Mô phỏng phòng thi chuẩn AWS",
        "Full test semester exam",
        "Mock exam final review",
    ]
    for t in titles:
        is_ns, _ = NonSplittableTaskClassifier.classify({"title": t})
        assert is_ns is True

    # Secondary text clean out false positive (lines 160-168)
    task_sec = {
        "title": "Buổi học bình thường",
        "description": "Thực hiện bài thi thử độc lập",
    }
    assert NonSplittableTaskClassifier.classify(task_sec)[0] is True

    task_retrospective = {
        "title": "Tổng kết tuần",
        "description": "phân tích kết quả của bài thi thử",
    }
    assert NonSplittableTaskClassifier.classify(task_retrospective)[0] is False

    # Explicit flag & task_type
    assert NonSplittableTaskClassifier.classify({"is_non_splittable": True})[0] is True
    assert NonSplittableTaskClassifier.classify({"task_type": "THEORY"})[0] is False
    assert NonSplittableTaskClassifier.classify({"title": "Đọc tài liệu bình thường"})[0] is False


def test_extract_pinned_blocks_and_anchor() -> None:
    tz = "Asia/Ho_Chi_Minh"
    # 1. Pinned blocks with start/end datetimes
    task_with_pinned = {
        "task_id": "t1",
        "pinned_schedule_blocks": [
            {
                "sequence_in_task": 1,
                "block_date": "2026-11-02",
                "scheduled_start": "2026-11-02T19:00:00+07:00",
                "scheduled_end": "2026-11-02T20:00:00+07:00",
                "scheduled_duration_minutes": 0,  # tests line 938: b_dur <= 0
                "is_protected": True,
            },
            {
                "sequence_in_task": 2,
                "block_date": "2026-11-03",
                # No scheduled_start / scheduled_end -> tests lines 945-955
                "scheduled_duration_minutes": 45,
            },
            {
                # Invalid block without date or start -> tests lines 931-932
                "block_date": None,
                "scheduled_start": None,
            },
        ],
    }
    entries, blocks, anchor = SpatioTemporalRuleEngine._extract_pinned_blocks_and_anchor(
        task_with_pinned, tid="t1", effort=105, tz_name=tz
    )
    assert len(entries) == 2
    assert len(blocks) == 2
    assert anchor[0] == date(2026, 11, 3)

    # 2. No pinned blocks, task has scheduled_date and start/end datetimes (lines 981-990)
    task_single_timed = {
        "task_id": "t2",
        "scheduled_date": "2026-11-04",
        "scheduled_start": "2026-11-04T10:00:00+07:00",
        "scheduled_end": "2026-11-04T11:30:00+07:00",
        "estimated_minutes": 90,
    }
    entries2, blocks2, anchor2 = SpatioTemporalRuleEngine._extract_pinned_blocks_and_anchor(
        task_single_timed, tid="t2", effort=90, tz_name=tz
    )
    assert len(entries2) == 1
    assert anchor2[0] == date(2026, 11, 4)
    assert anchor2[1] == 11 * 60 + 30

    # 3. No pinned blocks, task has only scheduled_date without start/end (lines 992-995)
    task_date_only = {
        "task_id": "t3",
        "scheduled_date": "2026-11-05",
        "estimated_minutes": 60,
    }
    entries3, blocks3, anchor3 = SpatioTemporalRuleEngine._extract_pinned_blocks_and_anchor(
        task_date_only, tid="t3", effort=60, tz_name=tz
    )
    assert len(entries3) == 1
    assert anchor3[0] == date(2026, 11, 5)
    assert anchor3[1] == 20 * 60


def test_dag_graph_branches() -> None:
    tasks = [
        {"task_id": "t1"},
        {"task_id": "t2"},
    ]
    deps = [
        "not a dict",  # tests line 1257
        {"is_mandatory": False},  # tests line 1259
        {"predecessor_id": "t1", "successor_id": "unknown"},  # tests line 1265
        {"predecessor_id": "t1", "successor_id": "t1"},  # self loop: lines 1267-1268
        {"predecessor_id": "t1", "successor_id": "t2", "is_mandatory": True},
    ]
    id_map, preds, succs, is_acyclic = SpatioTemporalRuleEngine._build_dag_graph(tasks, deps)
    assert is_acyclic is False
    assert preds[1] == [0]
    assert succs[0] == [1]


def test_mode_a_and_mode_b_validation_branches() -> None:
    tz = "Asia/Ho_Chi_Minh"
    avail_a = AvailabilityConfigurationDTO(
        mode="MODE_A",
        timezone=tz,
        daily_quota_minutes={"0": 120, "monday": 120},  # tests string digit index (line 467)
        default_daily_quota_minutes=120,
        availability_slots=[],
        disabled_weekdays=[],
    )

    # Mode A task missing date but having scheduled_start (line 336)
    tasks_a = [
        {
            "task_id": "t1",
            "title": "Task A",
            "estimated_minutes": 60,
            "scheduled_start": "2026-11-02T19:00:00+07:00",
            "scheduled_end": "2026-11-02T20:00:00+07:00",
        }
    ]
    # Existing task missing date but having start (line 376)
    existing_ext = [
        DummyTaskObj(
            title="Existing Active",
            status="TODO",
            scheduled_date=None,
            planned_start_at="2026-11-02T20:00:00+07:00",
            planned_end_at="2026-11-02T21:00:00+07:00",
            estimated_minutes=60,
            roadmap_target_date="2026-12-01",
        )
    ]
    violations_a = SpatioTemporalRuleEngine.validate_mode_a_quota(
        tasks=tasks_a,
        availability=avail_a,
        existing_tasks=existing_ext,
        current_roadmap_target_date=date(2026, 12, 10),
    )
    assert violations_a == []

    # Over quota with EDF note
    tasks_a_over = [
        {
            "task_id": "t1",
            "title": "Task A",
            "estimated_minutes": 90,
            "scheduled_date": "2026-11-02",
        }
    ]
    violations_over = SpatioTemporalRuleEngine.validate_mode_a_quota(
        tasks=tasks_a_over,
        availability=avail_a,
        existing_tasks=existing_ext,
        current_roadmap_target_date=date(2026, 12, 10),
    )
    assert any(v.rule_code == "CROSS_ROADMAP_EDF_QUOTA_CONFLICT" for v in violations_over)

    # Mode B tests
    avail_b = AvailabilityConfigurationDTO(
        mode="MODE_B",
        timezone=tz,
        daily_quota_minutes={},
        default_daily_quota_minutes=0,
        availability_slots=[
            # Inactive slot
            AvailabilitySlotDTO(
                day_of_week="monday",
                start_time="19:00",
                end_time="20:00",
                end_day_offset=0,
                is_active=False,
            ),
            # Overlapping slots to test merging (line 552)
            AvailabilitySlotDTO(
                day_of_week="monday",
                start_time="19:00",
                end_time="21:00",
                end_day_offset=0,
                is_active=True,
            ),
            AvailabilitySlotDTO(
                day_of_week="monday",
                start_time="20:30",
                end_time="22:00",
                end_day_offset=0,
                is_active=True,
            ),
            # Cross-midnight slot on Sunday (lines 715-723)
            AvailabilitySlotDTO(
                day_of_week="sunday",
                start_time="23:00",
                end_time="02:00",
                end_day_offset=1,
                is_active=True,
            ),
        ],
        disabled_weekdays=[],
    )

    # 1. Invalid time order (line 600): start 2026-11-04, end 2026-11-01 on base_date 2026-11-02
    tasks_invalid_order = [
        {
            "task_id": "tb1",
            "title": "Invalid Order",
            "scheduled_date": "2026-11-02",
            "scheduled_start": "2026-11-04T10:00:00+07:00",
            "scheduled_end": "2026-11-01T10:00:00+07:00",
            "estimated_minutes": 60,
        }
    ]
    v_order, _ = SpatioTemporalRuleEngine.validate_mode_b_slots(
        tasks=tasks_invalid_order, availability=avail_b
    )
    assert any(v.rule_code == "INVALID_TASK_TIME_ORDER" for v in v_order)

    # 2. Duration mismatch (line 613)
    tasks_dur_mismatch = [
        {
            "task_id": "tb2",
            "title": "Mismatch",
            "scheduled_date": "2026-11-02",
            "scheduled_start": "2026-11-02T19:00:00+07:00",
            "scheduled_end": "2026-11-02T20:00:00+07:00",
            "estimated_minutes": 90,
        }
    ]
    v_mismatch, _ = SpatioTemporalRuleEngine.validate_mode_b_slots(
        tasks=tasks_dur_mismatch, availability=avail_b
    )
    assert any(v.rule_code == "MODE_B_DURATION_MISMATCH" for v in v_mismatch)

    # 3. Cross-roadmap slot conflict (lines 690-709)
    tasks_b_conflict = [
        {
            "task_id": "tb3",
            "title": "Proposed Conflicting",
            "scheduled_date": "2026-11-02",
            "scheduled_start": "2026-11-02T19:00:00+07:00",
            "scheduled_end": "2026-11-02T20:00:00+07:00",
            "estimated_minutes": 60,
        }
    ]
    ext_conflict = [
        DummyTaskObj(
            title="Existing Occupied",
            status="TODO",
            scheduled_date="2026-11-02",
            planned_start_at="2026-11-02T19:30:00+07:00",
            planned_end_at="2026-11-02T20:30:00+07:00",
            roadmap_target_date="2026-11-20",
        )
    ]
    v_conf, _ = SpatioTemporalRuleEngine.validate_mode_b_slots(
        tasks=tasks_b_conflict,
        availability=avail_b,
        existing_tasks=ext_conflict,
        current_roadmap_target_date=date(2026, 12, 1),
    )
    assert any(v.rule_code == "CROSS_ROADMAP_EDF_SLOT_CONFLICT" for v in v_conf)

    # 4. Soft overflow <= 30m warning (lines 775-789)
    # Slot on Monday is 19:00-22:00. Task runs 21:00-22:20 (20m soft overflow, last task of day)
    tasks_soft_over = [
        {
            "task_id": "tb4",
            "title": "Last Task Soft Overflow",
            "scheduled_date": "2026-11-02",
            "scheduled_start": "2026-11-02T21:00:00+07:00",
            "scheduled_end": "2026-11-02T22:20:00+07:00",
            "estimated_minutes": 80,
        }
    ]
    v_soft, w_soft = SpatioTemporalRuleEngine.validate_mode_b_slots(
        tasks=tasks_soft_over, availability=avail_b
    )
    assert not v_soft
    assert len(w_soft) == 1
    assert w_soft[0].overflow_minutes == 20

    # 5. Overflow > 30m (lines 796-812)
    tasks_hard_over = [
        {
            "task_id": "tb5",
            "title": "Hard Overflow 45m",
            "scheduled_date": "2026-11-02",
            "scheduled_start": "2026-11-02T21:00:00+07:00",
            "scheduled_end": "2026-11-02T22:45:00+07:00",
            "estimated_minutes": 105,
        }
    ]
    v_hard, _ = SpatioTemporalRuleEngine.validate_mode_b_slots(
        tasks=tasks_hard_over, availability=avail_b
    )
    assert any(v.rule_code == "OVERFLOW_EXCEEDS_30M" for v in v_hard)


def test_validate_candidate_schedule_all_error_branches() -> None:
    tz_name = "Asia/Ho_Chi_Minh"
    start_d = date(2026, 11, 2)
    target_d = date(2026, 11, 15)
    avail = AvailabilityConfigurationDTO(
        mode="MODE_A",
        timezone=tz_name,
        daily_quota_minutes={"monday": 120},
        default_daily_quota_minutes=120,
        availability_slots=[],
        disabled_weekdays=[],
    )

    # 1. TASK_COUNT_MISMATCH (line 2630)
    errors1 = SpatioTemporalRuleEngine._validate_phase2_candidate(
        cand_tasks=[{"task_id": "t1", "estimated_minutes": 60}],
        cand_blocks=[],
        availability=avail,
        effective_efforts=[60, 60],  # len 2 != len 1
        classifications=[(False, "DEFAULT")],
        start_date=start_d,
        target_date=target_d,
        dependencies=[],
        existing_tasks=(),
        hard_split_tasks=0,
        hard_extra_spans=0,
    )
    assert "TASK_COUNT_MISMATCH" in errors1

    # 2. EFFORT_MUTATION, UNPLACED_TASK, PAST_TARGET_DATE, BEFORE_START_DATE
    cand_tasks = [
        {
            "task_id": "t1",
            "estimated_minutes": 50,  # mutation: expected 60
            "scheduled_date": None,  # UNPLACED_TASK
            "scheduled_start": None,
            "scheduled_end": None,
        },
        {
            "task_id": "t2",
            "estimated_minutes": 60,
            "scheduled_date": "2026-11-20",  # PAST_TARGET_DATE
            "scheduled_start": "2026-11-20T19:00:00+07:00",
            "scheduled_end": "2026-11-20T20:00:00+07:00",
        },
        {
            "task_id": "t3",
            "estimated_minutes": 60,
            "scheduled_date": "2026-10-30",  # BEFORE_START_DATE
            "scheduled_start": "2026-10-30T19:00:00+07:00",
            "scheduled_end": "2026-10-30T20:00:00+07:00",
        },
        {
            "task_id": "t4",
            "estimated_minutes": 0,  # eff <= 0: line 2642
        },
    ]
    efforts = [60, 60, 60, 0]
    classifs = [(False, "DEFAULT"), (False, "DEFAULT"), (False, "DEFAULT"), (False, "DEFAULT")]
    errors2 = SpatioTemporalRuleEngine._validate_phase2_candidate(
        cand_tasks=cand_tasks,
        cand_blocks=[],
        availability=avail,
        effective_efforts=efforts,
        classifications=classifs,
        start_date=start_d,
        target_date=target_d,
        dependencies=[],
        existing_tasks=(),
        hard_split_tasks=0,
        hard_extra_spans=0,
    )
    assert any("EFFORT_MUTATION:t1" in e for e in errors2)
    assert any("UNPLACED_TASK:t1" in e for e in errors2)
    assert any("PAST_TARGET_DATE:t2" in e for e in errors2)
    assert any("BEFORE_START_DATE:t3" in e for e in errors2)

    # 3. Block validation: ORPHAN_BLOCK, INVALID_BLOCK, BLOCK_PAST_TARGET_DATE, BLOCK_IN_END_BUFFER, BLOCK_EFFORT_MISMATCH, NON_SPLITTABLE_SPLIT
    buffer_d = {date(2026, 11, 14)}
    cand_tasks3 = [
        {
            "task_id": "t1",
            "estimated_minutes": 60,
            "scheduled_date": "2026-11-02",
            "scheduled_start": "2026-11-02T19:00:00+07:00",
            "scheduled_end": "2026-11-02T20:00:00+07:00",
        },
        {
            "task_id": "t2",
            "estimated_minutes": 60,
            "scheduled_date": "2026-11-03",
            "scheduled_start": "2026-11-03T19:00:00+07:00",
            "scheduled_end": "2026-11-03T20:00:00+07:00",
        },
    ]
    cand_blocks3 = [
        # Orphan block
        {"task_id": "unknown_orphan", "sequence_in_task": 1},
        # Invalid block: duration < 10 or mismatched end-start
        {
            "task_id": "t1",
            "sequence_in_task": 1,
            "block_date": "2026-11-02",
            "scheduled_start": "2026-11-02T19:00:00+07:00",
            "scheduled_end": "2026-11-02T19:05:00+07:00",  # 5m < 10m
            "scheduled_duration_minutes": 5,
        },
        # Block past target date
        {
            "task_id": "t1",
            "sequence_in_task": 2,
            "block_date": "2026-11-16",
            "scheduled_start": "2026-11-16T19:00:00+07:00",
            "scheduled_end": "2026-11-16T19:30:00+07:00",
            "scheduled_duration_minutes": 30,
        },
        # Block in end buffer
        {
            "task_id": "t1",
            "sequence_in_task": 3,
            "block_date": "2026-11-14",
            "scheduled_start": "2026-11-14T19:00:00+07:00",
            "scheduled_end": "2026-11-14T19:30:00+07:00",
            "scheduled_duration_minutes": 30,
        },
        # Non-splittable split into two blocks for t2
        {
            "task_id": "t2",
            "sequence_in_task": 1,
            "block_date": "2026-11-03",
            "scheduled_start": "2026-11-03T19:00:00+07:00",
            "scheduled_end": "2026-11-03T19:30:00+07:00",
            "scheduled_duration_minutes": 30,
        },
        {
            "task_id": "t2",
            "sequence_in_task": 2,
            "block_date": "2026-11-04",
            "scheduled_start": "2026-11-04T19:00:00+07:00",
            "scheduled_end": "2026-11-04T19:30:00+07:00",
            "scheduled_duration_minutes": 30,
        },
    ]
    errors3 = SpatioTemporalRuleEngine._validate_phase2_candidate(
        cand_tasks=cand_tasks3,
        cand_blocks=cand_blocks3,
        availability=avail,
        effective_efforts=[60, 60],
        classifications=[(False, "DEFAULT"), (True, "EXAM_RULE")],  # t2 is non-splittable
        start_date=start_d,
        target_date=target_d,
        dependencies=[],
        buffer_days=buffer_d,
        movable_task_ids=None,
        existing_tasks=(
            {"status": "CANCELLED"},  # tests line 2745
            {
                "status": "TODO",
                "scheduled_date": "2026-11-03",
                "scheduled_start": "2026-11-03T19:00:00+07:00",
                "scheduled_end": "2026-11-03T20:00:00+07:00",
                "estimated_minutes": 60,
            },
        ),
        hard_split_tasks=0,
        hard_extra_spans=0,
    )
    assert any("ORPHAN_BLOCK:unknown_orphan" in e for e in errors3)
    assert any("INVALID_BLOCK:t1" in e for e in errors3)
    assert any("BLOCK_PAST_TARGET_DATE:t1" in e for e in errors3)
    assert any("BLOCK_IN_END_BUFFER:t1" in e for e in errors3)
    assert any("NON_SPLITTABLE_SPLIT:t2" in e for e in errors3)

    # 4. SCHEDULE_BLOCK_OVERLAP
    cand_tasks4 = [
        {
            "task_id": "t1",
            "estimated_minutes": 60,
            "scheduled_date": "2026-11-02",
            "scheduled_start": "2026-11-02T19:00:00+07:00",
            "scheduled_end": "2026-11-02T20:00:00+07:00",
        },
        {
            "task_id": "t2",
            "estimated_minutes": 60,
            "scheduled_date": "2026-11-02",
            "scheduled_start": "2026-11-02T19:30:00+07:00",
            "scheduled_end": "2026-11-02T20:30:00+07:00",
        },
    ]
    cand_blocks4 = [
        {
            "task_id": "t1",
            "sequence_in_task": 1,
            "block_date": "2026-11-02",
            "scheduled_start": "2026-11-02T19:00:00+07:00",
            "scheduled_end": "2026-11-02T20:00:00+07:00",
            "scheduled_duration_minutes": 60,
        },
        {
            "task_id": "t2",
            "sequence_in_task": 1,
            "block_date": "2026-11-02",
            "scheduled_start": "2026-11-02T19:30:00+07:00",
            "scheduled_end": "2026-11-02T20:30:00+07:00",
            "scheduled_duration_minutes": 60,
        },
    ]
    errors4 = SpatioTemporalRuleEngine._validate_phase2_candidate(
        cand_tasks=cand_tasks4,
        cand_blocks=cand_blocks4,
        availability=avail,
        effective_efforts=[60, 60],
        classifications=[(False, "DEFAULT"), (False, "DEFAULT")],
        start_date=start_d,
        target_date=target_d,
        dependencies=[],
        existing_tasks=(),
        hard_split_tasks=0,
        hard_extra_spans=0,
    )
    assert "SCHEDULE_BLOCK_OVERLAP" in errors4


def test_legacy_solver_allocation_branches() -> None:
    tz = "Asia/Ho_Chi_Minh"
    start_d = date(2026, 11, 2)
    target_d = date(2026, 11, 20)

    # 1. No unscheduled tasks (line 3474)
    tasks_already_done = [
        {
            "task_id": "t1",
            "scheduled_date": "2026-11-02",
            "scheduled_start": "2026-11-02T19:00:00+07:00",
            "scheduled_end": "2026-11-02T20:00:00+07:00",
            "estimated_minutes": 60,
        }
    ]
    avail_legacy = AvailabilityConfigurationDTO(
        mode="MODE_B",
        timezone=tz,
        daily_quota_minutes={"monday": 120},
        default_daily_quota_minutes=120,
        availability_slots=[
            AvailabilitySlotDTO(
                day_of_week="monday",
                start_time="19:00",
                end_time="21:00",
                end_day_offset=0,
                is_active=True,
            ),
            {"day_of_week": "tuesday", "start_time": "19:00", "end_time": "21:00"},
        ],
        disabled_weekdays=["sunday", "saturday"],
    )
    res1 = SpatioTemporalRuleEngine._allocate_tasks_to_availability_legacy(
        tasks_already_done, avail_legacy, start_date=start_d, target_date=target_d
    )
    assert len(res1) == 1

    # 2. Tasks with existing tasks, dependencies, predecessor ordering (lines 3532-3743)
    tasks_to_allocate = [
        {"task_id": "t1", "estimated_minutes": 60, "milestone_id": "m1"},
        {"task_id": "t2", "estimated_minutes": 60, "milestone_id": "m1"},
        {
            "task_id": "t3_zero",
            "estimated_minutes": 0,
            "milestone_id": "m1",
        },  # duration <= 0 (line 3652)
        {"task_id": "t4_pred_unplaced", "estimated_minutes": 60, "milestone_id": "m2"},
    ]
    deps = [
        {"predecessor_id": "t1", "successor_id": "t2"},
        # t4 depends on t3_zero which is unplaced -> triggers lines 3666 & 3676-3679
        {"predecessor_id": "t3_zero", "successor_id": "t4_pred_unplaced"},
    ]
    existing = [
        {"status": "COMPLETED"},
        {
            "status": "TODO",
            "scheduled_date": "2026-11-02",
            "planned_start_at": "2026-11-02T19:00:00+07:00",
            "planned_end_at": "2026-11-02T20:00:00+07:00",
            "estimated_minutes": 60,
        },
        DummyTaskObj(
            status="TODO",
            scheduled_date="2026-11-03",
            planned_start_at="2026-11-03T19:00:00+07:00",
            planned_end_at="2026-11-03T20:00:00+07:00",
            estimated_minutes=60,
        ),
    ]
    res2 = SpatioTemporalRuleEngine._allocate_tasks_to_availability_legacy(
        tasks_to_allocate,
        avail_legacy,
        start_date=start_d,
        target_date=target_d,
        dependencies=deps,
        existing_tasks=existing,
    )
    assert res2[0]["scheduled_date"] is not None
    assert res2[2]["scheduled_date"] is None  # zero duration
    assert res2[3]["scheduled_date"] is None  # unplaced predecessor

    # 3. Mode A (Quota) branch in legacy solver (lines 3724-3743)
    avail_quota = AvailabilityConfigurationDTO(
        mode="QUOTA",
        timezone=tz,
        daily_quota_minutes={"monday": 120, "tuesday": 120},
        default_daily_quota_minutes=120,
        availability_slots=[],
        disabled_weekdays=["sunday"],
    )
    tasks_quota = [
        {"task_id": "tq1", "estimated_minutes": 60},
        {"task_id": "tq2", "estimated_minutes": 60},
    ]
    res3 = SpatioTemporalRuleEngine._allocate_tasks_to_availability_legacy(
        tasks_quota, avail_quota, start_date=start_d, target_date=target_d
    )
    assert res3[0]["scheduled_date"] is not None


def test_capacity_and_allocate_task_sessions_branches() -> None:
    tz = "Asia/Ho_Chi_Minh"
    start_d = date(2026, 11, 2)
    target_d = date(2026, 11, 10)

    # 1. calculate_hard_packable_capacity: end_date < start_date (line 3903)
    avail = AvailabilityConfigurationDTO(
        mode="MODE_B",
        timezone=tz,
        daily_quota_minutes={},
        default_daily_quota_minutes=0,
        availability_slots=[
            AvailabilitySlotDTO(
                day_of_week="monday",
                start_time="19:00",
                end_time="21:00",
                end_day_offset=0,
                is_active=True,
            )
        ],
        disabled_weekdays=[],
    )
    total_cap, cap_map = SpatioTemporalRuleEngine.calculate_hard_packable_capacity(
        avail, start_date=date(2026, 11, 10), target_date=date(2026, 11, 5)
    )
    assert total_cap == 0
    assert cap_map == {}

    # Valid span
    tot_valid, map_valid = SpatioTemporalRuleEngine.calculate_hard_packable_capacity(
        avail, start_date=start_d, target_date=target_d
    )
    assert tot_valid > 0

    # 2. allocate_task_sessions with Mode A / Quota (lines 3989-4085)
    avail_a = AvailabilityConfigurationDTO(
        mode="MODE_A",
        timezone=tz,
        daily_quota_minutes={"monday": 120, "wednesday": 120},
        default_daily_quota_minutes=120,
        availability_slots=[],
        disabled_weekdays=["sunday"],
    )
    tasks_sess = [
        {"task_id": "ts1", "estimated_minutes": 60},
        {"task_id": "ts2", "estimated_minutes": 90},
        {"task_id": "ts3_zero", "estimated_minutes": 0},
    ]
    deps_sess = [{"predecessor_id": "ts1", "successor_id": "ts2"}]
    # Bias beta > 1.0 (lines 4022-4028)
    scheduled_tasks, blocks = SpatioTemporalRuleEngine.allocate_task_sessions(
        tasks_sess,
        avail_a,
        start_date=start_d,
        target_date=target_d,
        dependencies=deps_sess,
        estimation_bias_beta=1.3,
    )
    assert len(scheduled_tasks) == 3
    # Check session limit < 10 branch (line 4011): zero capacity availability
    avail_zero_cap = AvailabilityConfigurationDTO(
        mode="MODE_A",
        timezone=tz,
        daily_quota_minutes={},
        default_daily_quota_minutes=0,
        availability_slots=[],
        disabled_weekdays=[],
    )
    unplaced_tasks, _ = SpatioTemporalRuleEngine.allocate_task_sessions(
        tasks_sess,
        avail_zero_cap,
        start_date=start_d,
        target_date=target_d,
        preferred_session_minutes=30,
    )
    assert all(t.get("scheduled_date") is None for t in unplaced_tasks)


def test_v2_session_pass_edge_cases() -> None:
    tz = "Asia/Ho_Chi_Minh"
    start_d = date(2026, 11, 2)
    target_d = date(2026, 11, 5)

    # Empty study days: all days disabled (lines 2230-2234)
    avail_no_days = AvailabilityConfigurationDTO(
        mode="MODE_A",
        timezone=tz,
        daily_quota_minutes={},
        default_daily_quota_minutes=0,
        availability_slots=[],
        disabled_weekdays=[
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ],
    )
    tasks = [{"task_id": "t1", "estimated_minutes": 60}]
    ctx = SpatioTemporalRuleEngine._build_calendar_context(avail_no_days)
    cloned, blocks, unplaced = SpatioTemporalRuleEngine._run_phase1_session_pass(
        tasks,
        ctx,
        start_date=start_d,
        target_date=target_d,
        dependencies=[],
        milestone_order_map={},
        preferred_session_minutes=60,
        effective_efforts=[60],
        classifications=[(False, "DEFAULT")],
    )
    assert len(unplaced) == 1
    assert cloned[0]["scheduled_date"] is None

    # All tasks pinned (line 2228)
    tasks_pinned = [
        {
            "task_id": "t_pinned",
            "estimated_minutes": 60,
            "scheduled_date": "2026-11-02",
            "scheduled_start": "2026-11-02T19:00:00+07:00",
            "scheduled_end": "2026-11-02T20:00:00+07:00",
        }
    ]
    avail_normal = AvailabilityConfigurationDTO(
        mode="MODE_A",
        timezone=tz,
        daily_quota_minutes={"monday": 120},
        default_daily_quota_minutes=120,
        availability_slots=[],
        disabled_weekdays=[],
    )
    ctx_normal = SpatioTemporalRuleEngine._build_calendar_context(avail_normal)
    cloned_p, blocks_p, unplaced_p = SpatioTemporalRuleEngine._run_phase1_session_pass(
        tasks_pinned,
        ctx_normal,
        start_date=start_d,
        target_date=target_d,
        dependencies=[],
        milestone_order_map={},
        preferred_session_minutes=60,
        effective_efforts=[60],
        classifications=[(False, "DEFAULT")],
    )
    assert not unplaced_p
    assert len(blocks_p) == 1


def test_calendar_context_all_branches() -> None:
    tz = "Asia/Ho_Chi_Minh"
    avail = AvailabilityConfigurationDTO(
        mode="MODE_B",
        timezone=tz,
        daily_quota_minutes={"0": 120, "monday": 120},
        default_daily_quota_minutes=120,
        availability_slots=[
            # Inactive slot (line 1056)
            AvailabilitySlotDTO(
                day_of_week="monday",
                start_time="08:00",
                end_time="10:00",
                end_day_offset=0,
                is_active=False,
            ),
            # Invalid slot object (line 1069)
            12345,  # type: ignore[arg-type]
            # Slot with None start/end (line 1071)
            {"day_of_week": "monday", "start_time": None, "end_time": "10:00"},
            # Valid slots with overlap to test merging (line 1083)
            AvailabilitySlotDTO(
                day_of_week="tuesday",
                start_time="19:00",
                end_time="21:00",
                end_day_offset=0,
                is_active=True,
            ),
            AvailabilitySlotDTO(
                day_of_week="tuesday",
                start_time="20:00",
                end_time="22:00",
                end_day_offset=0,
                is_active=True,
            ),
        ],
        disabled_weekdays=["SUNDAY"],
    )
    existing = [
        # Existing task with date and mins but no start_dt/end_dt (line 1131-1132)
        {"status": "TODO", "scheduled_date": "2026-11-02", "estimated_minutes": 60},
    ]
    ctx = SpatioTemporalRuleEngine._build_calendar_context(avail, existing_tasks=existing)
    assert date(2026, 11, 2) in ctx["existing_used"]
    assert "tuesday" in ctx["slots_by_day"]
    assert ctx["slots_by_day"]["tuesday"] == [(19 * 60, 22 * 60)]


def test_necessary_conditions_ancestors_and_cross_midnight() -> None:
    tz = "Asia/Ho_Chi_Minh"
    start_d = date(2026, 11, 2)
    target_d = date(2026, 11, 10)

    # Avail with cross-midnight slot (lines 1630-1647)
    avail = AvailabilityConfigurationDTO(
        mode="MODE_B",
        timezone=tz,
        daily_quota_minutes={},
        default_daily_quota_minutes=0,
        availability_slots=[
            AvailabilitySlotDTO(
                day_of_week="monday",
                start_time="23:00",
                end_time="02:00",
                end_day_offset=1,
                is_active=True,
            ),
            AvailabilitySlotDTO(
                day_of_week="tuesday",
                start_time="19:00",
                end_time="21:00",
                end_day_offset=0,
                is_active=True,
            ),
        ],
        disabled_weekdays=[],
    )
    # Task 0 is ancestor already scheduled in past (before start_date, line 1657)
    # Task 1 is non-splittable with predecessor Task 0 (lines 1471-1476)
    tasks = [
        {
            "task_id": "t0_past",
            "estimated_minutes": 60,
            "scheduled_date": "2026-10-25",
            "scheduled_start": "2026-10-25T19:00:00+07:00",
            "scheduled_end": "2026-10-25T20:00:00+07:00",
        },
        {
            "task_id": "t1_ns",
            "title": "Bài thi thử Raft",
            "estimated_minutes": 90,
            "is_non_splittable": True,
        },
        {
            "task_id": "t2_splittable",
            "estimated_minutes": 120,
        },
    ]
    deps = [{"predecessor_id": "t0_past", "successor_id": "t1_ns", "is_mandatory": True}]
    nc_result = SpatioTemporalRuleEngine.verify_necessary_conditions(
        tasks,
        avail,
        start_date=start_d,
        target_date=target_d,
        dependencies=deps,
    )
    assert nc_result.verdict in ("VERIFIED_FEASIBLE", "NC1_FAILED", "NC2_FAILED", "NC3_FAILED")


def test_validate_phase2_candidate_edge_invariants() -> None:
    tz_name = "Asia/Ho_Chi_Minh"
    start_d = date(2026, 11, 2)
    target_d = date(2026, 11, 15)
    avail = AvailabilityConfigurationDTO(
        mode="MODE_B",
        timezone=tz_name,
        daily_quota_minutes={},
        default_daily_quota_minutes=0,
        availability_slots=[
            AvailabilitySlotDTO(
                day_of_week="monday",
                start_time="19:00",
                end_time="21:00",
                end_day_offset=0,
                is_active=True,
            )
        ],
        disabled_weekdays=[],
    )
    # 1. 720m daily cap exceeded (line 2791)
    cand_tasks = [
        {
            "task_id": "t_huge",
            "estimated_minutes": 750,
            "scheduled_date": "2026-11-02",
            "scheduled_start": "2026-11-02T08:00:00+07:00",
            "scheduled_end": "2026-11-02T20:30:00+07:00",
        }
    ]
    cand_blocks = [
        {
            "task_id": "t_huge",
            "sequence_in_task": 1,
            "block_date": "2026-11-02",
            "scheduled_start": "2026-11-02T08:00:00+07:00",
            "scheduled_end": "2026-11-02T20:30:00+07:00",
            "scheduled_duration_minutes": 750,
            "is_protected": True,
        }
    ]
    errors_huge = SpatioTemporalRuleEngine._validate_phase2_candidate(
        cand_tasks=cand_tasks,
        cand_blocks=cand_blocks,
        availability=avail,
        start_date=start_d,
        target_date=target_d,
        dependencies=[],
        existing_tasks=[
            {"status": "TODO", "scheduled_date": "2026-11-02", "estimated_minutes": 60}
        ],
        effective_efforts=[750],
        classifications=[(True, "EXPLICIT_DTO")],
        hard_split_tasks=0,
        hard_extra_spans=0,
        daily_workload_cap_minutes=400,  # line 2793: daily workload cap exceeded
    )
    assert any("DAILY_MAX_720M_EXCEEDED" in e for e in errors_huge)
    assert any("DAILY_WORKLOAD_CAP_EXCEEDED" in e for e in errors_huge)

    # 2. DAG order violation: p_end > s_start (line 2841)
    cand_tasks_dag = [
        {
            "task_id": "tp",
            "estimated_minutes": 60,
            "scheduled_date": "2026-11-02",
            "scheduled_start": "2026-11-02T19:00:00+07:00",
            "scheduled_end": "2026-11-02T20:00:00+07:00",
        },
        {
            "task_id": "ts",
            "estimated_minutes": 60,
            "scheduled_date": "2026-11-02",
            "scheduled_start": "2026-11-02T18:00:00+07:00",  # starts BEFORE predecessor ends!
            "scheduled_end": "2026-11-02T19:00:00+07:00",
        },
    ]
    cand_blocks_dag = [
        {
            "task_id": "tp",
            "sequence_in_task": 1,
            "block_date": "2026-11-02",
            "scheduled_start": "2026-11-02T19:00:00+07:00",
            "scheduled_end": "2026-11-02T20:00:00+07:00",
            "scheduled_duration_minutes": 60,
        },
        {
            "task_id": "ts",
            "sequence_in_task": 1,
            "block_date": "2026-11-02",
            "scheduled_start": "2026-11-02T18:00:00+07:00",
            "scheduled_end": "2026-11-02T19:00:00+07:00",
            "scheduled_duration_minutes": 60,
        },
    ]
    deps_violation = [
        {"predecessor_id": "tp", "successor_id": "ts"},
        {"predecessor_id": "unknown_task", "successor_id": "ts"},  # line 2837: p_task is None
    ]
    errors_dag = SpatioTemporalRuleEngine._validate_phase2_candidate(
        cand_tasks=cand_tasks_dag,
        cand_blocks=cand_blocks_dag,
        availability=avail,
        start_date=start_d,
        target_date=target_d,
        dependencies=deps_violation,
        existing_tasks=(),
        effective_efforts=[60, 60],
        classifications=[(False, "DEFAULT"), (False, "DEFAULT")],
        hard_split_tasks=0,
        hard_extra_spans=0,
    )
    assert any("DAG_ORDER_VIOLATION:tp->ts" in e for e in errors_dag)

    # 3. Extra cross-day splits, adjacent same-day splits, streak exceeds max (lines 2846, 2848, 2855)
    cand_blocks_splits = [
        {
            "task_id": "tp",
            "sequence_in_task": 1,
            "block_date": "2026-11-02",
            "scheduled_start": "2026-11-02T19:00:00+07:00",
            "scheduled_end": "2026-11-02T19:30:00+07:00",
            "scheduled_duration_minutes": 30,
        },
        {
            "task_id": "tp",
            "sequence_in_task": 2,
            "block_date": "2026-11-02",
            "scheduled_start": "2026-11-02T19:30:00+07:00",  # adjacent same-day! (line 2848)
            "scheduled_end": "2026-11-02T20:00:00+07:00",
            "scheduled_duration_minutes": 30,
        },
        {
            "task_id": "ts",
            "sequence_in_task": 1,
            "block_date": "2026-11-03",
            "scheduled_start": "2026-11-03T19:00:00+07:00",
            "scheduled_end": "2026-11-03T19:30:00+07:00",
            "scheduled_duration_minutes": 30,
        },
        {
            "task_id": "ts",
            "sequence_in_task": 2,
            "block_date": "2026-11-04",  # cross day split!
            "scheduled_start": "2026-11-04T19:00:00+07:00",
            "scheduled_end": "2026-11-04T19:30:00+07:00",
            "scheduled_duration_minutes": 30,
        },
    ]
    errors_splits = SpatioTemporalRuleEngine._validate_phase2_candidate(
        cand_tasks=cand_tasks_dag,
        cand_blocks=cand_blocks_splits,
        availability=avail,
        start_date=start_d,
        target_date=target_d,
        dependencies=[],
        existing_tasks=(),
        effective_efforts=[60, 60],
        classifications=[(False, "DEFAULT"), (False, "DEFAULT")],
        hard_split_tasks=0,  # 0 expected cross-day split
        hard_extra_spans=0,
        max_allowed_streak=1,  # 3 consecutive days > max 1! (line 2855)
    )
    assert "EXTRA_CROSS_DAY_SPLITS" in errors_splits
    assert "ADJACENT_SAME_DAY_SPLITS" in errors_splits
    assert "STREAK_EXCEEDS_MAX" in errors_splits


def test_phase2_soft_optimization_fallbacks() -> None:
    tz = "Asia/Ho_Chi_Minh"
    start_d = date(2026, 11, 2)
    avail = AvailabilityConfigurationDTO(
        mode="MODE_A",
        timezone=tz,
        daily_quota_minutes={"monday": 120},
        default_daily_quota_minutes=120,
        availability_slots=[],
        disabled_weekdays=[],
    )
    tasks = [{"task_id": "t1", "estimated_minutes": 60}]
    blocks = [
        {
            "task_id": "t1",
            "sequence_in_task": 1,
            "block_date": "2026-11-02",
            "scheduled_start": "2026-11-02T19:00:00+07:00",
            "scheduled_end": "2026-11-02T20:00:00+07:00",
            "scheduled_duration_minutes": 60,
        }
    ]
    # 1. Infeasible NC result (line 2887)
    from src.planning.domain.services.validation_types import NecessaryConditionCheckResult

    nc_fail = NecessaryConditionCheckResult(
        verdict="NC1_FAILED",
        nc1_passed=False,
        nc2_passed=True,
        nc3_passed=True,
        total_required_minutes=100,
        total_hard_packable_minutes=50,
    )
    ctx = SpatioTemporalRuleEngine._build_calendar_context(avail)
    res_tasks, res_blocks = SpatioTemporalRuleEngine._optimize_schedule_phase2(
        tasks=tasks,
        hard_tasks=tasks,
        hard_blocks=blocks,
        availability=avail,
        ctx=ctx,
        start_date=start_d,
        target_date=date(2026, 11, 10),
        dependencies=[],
        existing_tasks=(),
        milestone_order_map={},
        preferred_session_minutes=60,
        effective_efforts=[60],
        classifications=[(False, "DEFAULT")],
        nc_result=nc_fail,
        soft_pacing_v2_enabled=True,
        end_buffer_ratio=0.1,
        max_consecutive_study_days=3,
    )
    assert res_tasks == tasks
    assert res_blocks == blocks

    # 2. No movable indices (line 2895)
    tasks_all_scheduled = [
        {
            "task_id": "t1",
            "estimated_minutes": 60,
            "scheduled_date": "2026-11-02",
            "scheduled_start": "2026-11-02T19:00:00+07:00",
            "scheduled_end": "2026-11-02T20:00:00+07:00",
        }
    ]
    nc_ok = NecessaryConditionCheckResult(
        verdict="VERIFIED_FEASIBLE",
        nc1_passed=True,
        nc2_passed=True,
        nc3_passed=True,
        total_required_minutes=60,
        total_hard_packable_minutes=120,
    )
    res_tasks2, res_blocks2 = SpatioTemporalRuleEngine._optimize_schedule_phase2(
        tasks=tasks_all_scheduled,
        hard_tasks=tasks_all_scheduled,
        hard_blocks=blocks,
        availability=avail,
        ctx=ctx,
        start_date=start_d,
        target_date=date(2026, 11, 10),
        dependencies=[],
        existing_tasks=(),
        milestone_order_map={},
        preferred_session_minutes=60,
        effective_efforts=[60],
        classifications=[(False, "DEFAULT")],
        nc_result=nc_ok,
        soft_pacing_v2_enabled=True,
        end_buffer_ratio=0.1,
        max_consecutive_study_days=3,
    )
    assert res_tasks2 == tasks_all_scheduled
    assert res_blocks2 == blocks

    # 3. target_date is None and streak exceeds max_consecutive_study_days (lines 2908-2913)
    # Blocks span 3 consecutive days
    streak_blocks = [
        {
            "task_id": "t1",
            "sequence_in_task": 1,
            "block_date": "2026-11-02",
            "scheduled_start": "2026-11-02T19:00:00+07:00",
            "scheduled_end": "2026-11-02T20:00:00+07:00",
            "scheduled_duration_minutes": 60,
        },
        {
            "task_id": "t2",
            "sequence_in_task": 1,
            "block_date": "2026-11-03",
            "scheduled_start": "2026-11-03T19:00:00+07:00",
            "scheduled_end": "2026-11-03T20:00:00+07:00",
            "scheduled_duration_minutes": 60,
        },
        {
            "task_id": "t3",
            "sequence_in_task": 1,
            "block_date": "2026-11-04",
            "scheduled_start": "2026-11-04T19:00:00+07:00",
            "scheduled_end": "2026-11-04T20:00:00+07:00",
            "scheduled_duration_minutes": 60,
        },
    ]
    tasks_unscheduled = [
        {"task_id": "t1", "estimated_minutes": 60},
        {"task_id": "t2", "estimated_minutes": 60},
        {"task_id": "t3", "estimated_minutes": 60},
    ]
    res_tasks3, res_blocks3 = SpatioTemporalRuleEngine._optimize_schedule_phase2(
        tasks=tasks_unscheduled,
        hard_tasks=tasks_unscheduled,
        hard_blocks=streak_blocks,
        availability=avail,
        ctx=ctx,
        start_date=start_d,
        target_date=None,  # target_date is None!
        dependencies=[],
        existing_tasks=(),
        milestone_order_map={},
        preferred_session_minutes=60,
        effective_efforts=[60, 60, 60],
        classifications=[(False, "DEFAULT"), (False, "DEFAULT"), (False, "DEFAULT")],
        nc_result=nc_ok,
        soft_pacing_v2_enabled=True,
        end_buffer_ratio=0.1,
        max_consecutive_study_days=1,  # max 1 day < 3 days streak!
    )
    assert len(res_blocks3) >= 1


def test_largest_non_splittable_first_solver_fallback() -> None:
    tz = "Asia/Ho_Chi_Minh"
    start_d = date(2026, 11, 2)  # Monday
    target_d = date(2026, 11, 3)  # Tuesday

    # Monday has 120m slot (19:00-21:00)
    # Tuesday has 90m slot (19:00-20:30)
    avail = AvailabilityConfigurationDTO(
        mode="MODE_B",
        timezone=tz,
        daily_quota_minutes={},
        default_daily_quota_minutes=0,
        availability_slots=[
            AvailabilitySlotDTO(
                day_of_week="monday",
                start_time="19:00",
                end_time="21:00",
                end_day_offset=0,
                is_active=True,
            ),
            AvailabilitySlotDTO(
                day_of_week="tuesday",
                start_time="19:00",
                end_time="20:30",
                end_day_offset=0,
                is_active=True,
            ),
        ],
        disabled_weekdays=[],
    )
    # Task 1 (60m splittable), Task 2 (120m non-splittable)
    # Under TOPOLOGICAL_DEFAULT: Task 1 places on Monday 19:00-20:00. Remaining Monday is 60m.
    # Task 2 (120m) cannot fit in Monday (60m) or Tuesday (90m). Thus best_unplaced is not empty!
    # NC check verifies total 180m <= 210m packable, so LARGEST_NON_SPLITTABLE_FIRST triggers!
    # Under LARGEST_NON_SPLITTABLE_FIRST: Task 2 (120m) places on Monday 19:00-21:00, Task 1 on Tuesday!
    # (Lines 3431-3448)
    tasks = [
        {"task_id": "t1_small", "estimated_minutes": 60, "is_non_splittable": False},
        {
            "task_id": "t2_big_ns",
            "title": "Bài thi thử 120 phút",
            "estimated_minutes": 120,
            "is_non_splittable": True,
        },
    ]
    allocated = SpatioTemporalRuleEngine.allocate_tasks_to_availability(
        tasks,
        avail,
        start_date=start_d,
        target_date=target_d,
        hard_solver_v2_enabled=True,
    )
    assert all(t["scheduled_date"] is not None for t in allocated)
    t2 = next(t for t in allocated if t["task_id"] == "t2_big_ns")
    assert t2["scheduled_date"] == "2026-11-02"


def test_legacy_solver_complex_occupied_and_topological_sort() -> None:
    tz = "Asia/Ho_Chi_Minh"
    start_d = date(2026, 11, 2)
    target_d = date(2026, 11, 10)

    avail_b = AvailabilityConfigurationDTO(
        mode="MODE_B",
        timezone=tz,
        daily_quota_minutes={},
        default_daily_quota_minutes=0,
        availability_slots=[
            AvailabilitySlotDTO(
                day_of_week="monday",
                start_time="19:00",
                end_time="21:00",
                end_day_offset=0,
                is_active=True,
            ),
            AvailabilitySlotDTO(
                day_of_week="tuesday",
                start_time="19:00",
                end_time="20:00",
                end_day_offset=0,
                is_active=True,
            ),
        ],
        disabled_weekdays=[],
    )
    # Existing task occupied at 19:00-19:30 on Monday -> tests cand_s < occ_e and window fit (lines 3711-3720)
    existing = [
        {
            "status": "TODO",
            "scheduled_date": "2026-11-02",
            "estimated_minutes": 30,
            "planned_start_at": "2026-11-02T19:00:00+07:00",
            "planned_end_at": "2026-11-02T19:30:00+07:00",
        },
        # Existing task with only date and mins (line 3570)
        {"status": "TODO", "scheduled_date": "2026-11-04", "estimated_minutes": 45},
    ]
    # Partially scheduled cloned task with both start/end and one without start/end (lines 3578-3596)
    tasks = [
        {
            "task_id": "tp1_pinned",
            "scheduled_date": "2026-11-02",
            "scheduled_start": "2026-11-02T19:30:00+07:00",
            "scheduled_end": "2026-11-02T20:30:00+07:00",
            "estimated_minutes": 60,
        },
        {
            "task_id": "tp2_date_only",
            "scheduled_date": "2026-11-03",
            "estimated_minutes": 60,
        },
        # Unscheduled tasks with dependencies (lines 3608-3636)
        {"task_id": "tu1", "estimated_minutes": 30},
        {
            "task_id": "tu2",
            "estimated_minutes": 90,
        },  # 90m > 60m remaining slot -> skips day (line 3702)
    ]
    deps = [
        "not a dict",  # line 3610
        {"predecessor_id": "tu1", "successor_id": "tu2"},
    ]
    res = SpatioTemporalRuleEngine._allocate_tasks_to_availability_legacy(
        tasks,
        avail_b,
        start_date=start_d,
        target_date=target_d,
        dependencies=deps,
        existing_tasks=existing,
    )
    assert len(res) == 4

    # Mode A (Quota) branch with occupied intervals (lines 3734-3742)
    avail_a = AvailabilityConfigurationDTO(
        mode="MODE_A",
        timezone=tz,
        daily_quota_minutes={"monday": 120, "tuesday": 60},
        default_daily_quota_minutes=120,
        availability_slots=[],
        disabled_weekdays=[],
    )
    existing_a = [
        {
            "status": "TODO",
            "scheduled_date": "2026-11-02",
            "estimated_minutes": 60,
            "planned_start_at": "2026-11-02T19:00:00+07:00",
            "planned_end_at": "2026-11-02T20:00:00+07:00",
        }
    ]
    tasks_a = [
        {"task_id": "ta1", "estimated_minutes": 60},
        {
            "task_id": "ta2",
            "estimated_minutes": 80,
        },  # 80 > 60 Tuesday quota -> skips Tuesday (line 3729)
    ]
    res_a = SpatioTemporalRuleEngine._allocate_tasks_to_availability_legacy(
        tasks_a,
        avail_a,
        start_date=start_d,
        target_date=target_d,
        existing_tasks=existing_a,
    )
    assert len(res_a) == 2


def test_allocate_task_sessions_dependencies_and_small_base() -> None:
    tz = "Asia/Ho_Chi_Minh"
    start_d = date(2026, 11, 2)
    target_d = date(2026, 11, 15)

    avail_a = AvailabilityConfigurationDTO(
        mode="MODE_A",
        timezone=tz,
        daily_quota_minutes={"monday": 180, "tuesday": 180, "wednesday": 180},
        default_daily_quota_minutes=180,
        availability_slots=[],
        disabled_weekdays=[],
    )
    # Task with dependencies between tasks (lines 4056-4061)
    tasks = [
        {"task_id": "t_first", "estimated_minutes": 120},
        {"task_id": "t_second", "estimated_minutes": 90},
    ]
    deps = [{"predecessor_id": "t_first", "successor_id": "t_second"}]
    scheduled, blocks = SpatioTemporalRuleEngine.allocate_task_sessions(
        tasks,
        avail_a,
        start_date=start_d,
        target_date=target_d,
        dependencies=deps,
        preferred_session_minutes=60,
    )
    assert len(scheduled) == 2
    assert len(blocks) >= 2

    # base < 10 branch (line 4038)
    # effort = 15m, session_limit = 10, count = 2, base = 15 // 2 = 7 < 10!
    tasks_small = [{"task_id": "t_small", "estimated_minutes": 15}]
    unplaced, _ = SpatioTemporalRuleEngine.allocate_task_sessions(
        tasks_small,
        avail_a,
        start_date=start_d,
        target_date=target_d,
        preferred_session_minutes=10,
        hard_solver_v2_enabled=False,
    )
    assert unplaced[0]["scheduled_date"] is None

    # session_limit < 10 branch (line 4011)
    unplaced_limit, _ = SpatioTemporalRuleEngine.allocate_task_sessions(
        tasks_small,
        AvailabilityConfigurationDTO(
            mode="MODE_A",
            timezone=tz,
            daily_quota_minutes={"monday": 5},
            default_daily_quota_minutes=5,
            availability_slots=[],
            disabled_weekdays=[],
        ),
        start_date=start_d,
        target_date=target_d,
        preferred_session_minutes=5,
        hard_solver_v2_enabled=False,
    )
    assert unplaced_limit[0]["scheduled_date"] is None

    # effort <= 0 branch (line 4033) and beta adjustment (line 4025)
    tasks_mixed = [
        {"task_id": "t_zero", "estimated_minutes": 0},
        {"task_id": "t_beta", "estimated_minutes": 60},
    ]
    scheduled_mixed, blocks_mixed = SpatioTemporalRuleEngine.allocate_task_sessions(
        tasks_mixed,
        avail_a,
        start_date=start_d,
        target_date=target_d,
        preferred_session_minutes=60,
        estimation_bias_beta=1.5,
        hard_solver_v2_enabled=False,
    )
    assert len(scheduled_mixed) == 2
