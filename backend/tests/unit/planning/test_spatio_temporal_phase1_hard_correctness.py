from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from src.planning.application.services.validation_gate.orchestrator import (
    ProposalValidationGateOrchestrator,
)
from src.planning.application.services.validation_gate.tier1_schema import run_tier1_gate
from src.planning.domain.services.spatio_temporal_engine import (
    NonSplittableTaskClassifier,
    SpatioTemporalRuleEngine,
)
from src.planning.domain.services.validation_types import (
    AvailabilityConfigurationDTO,
    AvailabilitySlotDTO,
)
from tests.helpers.llm_stubs import StubLLMAdapter

REPO_ROOT = Path(__file__).resolve().parents[4]
EXP09_PATH = REPO_ROOT / "docs" / "experiments" / "exp_09_judge_and_quality_ab.json"
KEY10_PATH = REPO_ROOT / "docs" / "experiments" / "blind_review_10_roadmaps_key.json"


def _load_exp09_roadmap(label: str) -> tuple[dict[str, Any], dict[str, Any]]:
    exp09 = json.loads(EXP09_PATH.read_text(encoding="utf-8"))
    key_map = json.loads(KEY10_PATH.read_text(encoding="utf-8"))["mapping"]
    meta = key_map[label]
    for rm in exp09["part_3_quality_ab_low_vs_medium"]["roadmaps"]:
        if rm["goal_key"] == meta["goal_id"] and rm["arm"] == meta["arm"]:
            return rm, meta
    raise AssertionError(f"Roadmap {label} not found in exp_09")


def _strip_schedule_fields(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            k: v
            for k, v in t.items()
            if k not in ("scheduled_date", "scheduled_start", "scheduled_end")
        }
        for t in tasks
    ]


def _count_adjacent_same_day_splits(blocks: list[dict[str, Any]]) -> int:
    by_task_day: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for b in blocks:
        key = (str(b["task_id"]), str(b["block_date"])[:10])
        by_task_day.setdefault(key, []).append(b)
    count = 0
    for day_blocks in by_task_day.values():
        if len(day_blocks) <= 1:
            continue
        sorted_b = sorted(day_blocks, key=lambda x: str(x["scheduled_start"]))
        for cur, nxt in zip(sorted_b, sorted_b[1:], strict=False):
            if cur["scheduled_end"] == nxt["scheduled_start"]:
                count += 1
    return count


def _count_sensitive_cross_day_splits(
    tasks: list[dict[str, Any]], blocks: list[dict[str, Any]]
) -> int:
    dates_by_task: dict[str, set[str]] = {}
    for b in blocks:
        dates_by_task.setdefault(str(b["task_id"]), set()).add(str(b["block_date"])[:10])
    count = 0
    for t in tasks:
        tid = str(t.get("task_id") or t.get("id"))
        if (
            NonSplittableTaskClassifier.is_non_splittable(t)
            and len(dates_by_task.get(tid, set())) > 1
        ):
            count += 1
    return count


def test_non_splittable_classifier_provenance_and_no_false_positives() -> None:
    # EXPLICIT_DTO overrides deterministic rules in both directions
    assert NonSplittableTaskClassifier.classify(
        {"title": "Luyện tập hàm Python", "is_non_splittable": True}
    ) == (True, "EXPLICIT_DTO")
    assert NonSplittableTaskClassifier.classify(
        {"title": "Thi thử Mock Test 1", "is_non_splittable": False}
    ) == (False, "EXPLICIT_DTO")

    # DETERMINISTIC_RULE matches Vietnamese & English timed exams / mock / load / stress / benchmark
    for title in (
        "Thi thử Mock Test 1 trọn vẹn Task 1 & Task 2 trong 60 phút",
        "Bài thi thử IELTS Writing đầy đủ",
        "Đề thi đầy đủ mô phỏng phòng thi",
        "Timed Exam: System Design 90m",
        "Practice Exam 1",
        "Luyện viết Full Test 1",
        "Kiểm thử chịu tải mô phỏng 5000 concurrent requests",
        "API Load Test at 2000 RPS",
        "Stress Testing Redis Cluster",
        "Benchmark test điều phối workload trên Tokio",
        "Mock Exam: AWS Solutions Architect",
    ):
        assert NonSplittableTaskClassifier.classify({"title": title}) == (
            True,
            "DETERMINISTIC_RULE",
        ), f"Expected non-splittable for {title!r}"

    # DEFAULT_SPLITTABLE: normal coding/unit-test/setup practice must NOT false-positive
    for title in (
        "Kiểm thử API Endpoint với FastAPI TestClient",
        "Thiết lập Bộ kiểm thử chất lượng dữ liệu dbt Test",
        "Kiểm thử tích hợp End-to-End (Integration Testing)",
        "Thực hành xây dựng CRUD Router với FastAPI",
        "Setup benchmark environment",
        "Benchmark điều phối workload trên Tokio",
    ):
        assert NonSplittableTaskClassifier.classify({"title": title}) == (
            False,
            "DEFAULT_SPLITTABLE",
        ), f"Unexpected non-splittable false positive for {title!r}"


def test_coalesce_adjacent_blocks_merges_and_renumbers() -> None:
    raw_blocks = [
        {
            "task_id": "T1",
            "sequence_in_task": 1,
            "block_date": "2026-11-18",
            "scheduled_start": "2026-11-18T19:30:00+00:00",
            "scheduled_end": "2026-11-18T20:15:00+00:00",
            "scheduled_duration_minutes": 45,
        },
        {
            "task_id": "T1",
            "sequence_in_task": 2,
            "block_date": "2026-11-18",
            "scheduled_start": "2026-11-18T20:15:00+00:00",
            "scheduled_end": "2026-11-18T21:00:00+00:00",
            "scheduled_duration_minutes": 45,
        },
        {
            "task_id": "T1",
            "sequence_in_task": 3,
            "block_date": "2026-11-20",
            "scheduled_start": "2026-11-20T19:30:00+00:00",
            "scheduled_end": "2026-11-20T20:00:00+00:00",
            "scheduled_duration_minutes": 30,
        },
        # Sum > 120m must NOT merge
        {
            "task_id": "T2",
            "sequence_in_task": 1,
            "block_date": "2026-11-21",
            "scheduled_start": "2026-11-21T09:00:00+00:00",
            "scheduled_end": "2026-11-21T10:30:00+00:00",
            "scheduled_duration_minutes": 90,
        },
        {
            "task_id": "T2",
            "sequence_in_task": 2,
            "block_date": "2026-11-21",
            "scheduled_start": "2026-11-21T10:30:00+00:00",
            "scheduled_end": "2026-11-21T11:30:00+00:00",
            "scheduled_duration_minutes": 60,
        },
    ]
    merged = SpatioTemporalRuleEngine._coalesce_adjacent_blocks(raw_blocks)
    t1_blocks = [b for b in merged if b["task_id"] == "T1"]
    t2_blocks = [b for b in merged if b["task_id"] == "T2"]
    assert len(t1_blocks) == 2
    assert t1_blocks[0]["scheduled_duration_minutes"] == 90
    assert t1_blocks[0]["scheduled_end"] == "2026-11-18T21:00:00+00:00"
    assert [b["sequence_in_task"] for b in t1_blocks] == [1, 2]
    assert len(t2_blocks) == 2
    assert [b["scheduled_duration_minutes"] for b in t2_blocks] == [90, 60]


def test_replay_r03_eliminates_all_12_adjacent_same_day_splits() -> None:
    rm, _ = _load_exp09_roadmap("R-03")
    avail_g5 = AvailabilityConfigurationDTO(
        mode="MODE_B",
        availability_slots=(
            AvailabilitySlotDTO("monday", "19:30", "21:00"),
            AvailabilitySlotDTO("wednesday", "19:30", "21:00"),
            AvailabilitySlotDTO("friday", "19:30", "21:00"),
            AvailabilitySlotDTO("saturday", "09:00", "12:00"),
        ),
    )
    tasks_in = _strip_schedule_fields(rm["decomposer"]["proposal"]["tasks"])
    orig_efforts = {t["task_id"]: t["estimated_minutes"] for t in tasks_in}
    deps = rm["decomposer"]["proposal"]["dependencies"]

    res = SpatioTemporalRuleEngine.allocate_task_sessions_with_diagnostics(
        tasks_in,
        avail_g5,
        start_date=date(2026, 11, 17),
        target_date=date(2026, 12, 22),
        dependencies=deps,
        preferred_session_minutes=60,
    )
    assert res.feasibility_verdict == "VERIFIED_FEASIBLE"
    assert len(res.unscheduled_diagnostics) == 0
    assert len(res.tasks) == 12
    assert len(res.schedule_blocks) == 12
    assert _count_adjacent_same_day_splits(res.schedule_blocks) == 0
    assert all(b["scheduled_duration_minutes"] == 90 for b in res.schedule_blocks)
    assert {t["task_id"]: t["estimated_minutes"] for t in res.tasks} == orig_efforts


def test_replay_r08_and_r10_zero_sensitive_cross_day_splits() -> None:
    # R-10: T8 (100m load test) placed in a single contiguous block
    rm10, _ = _load_exp09_roadmap("R-10")
    avail_g2 = AvailabilityConfigurationDTO(
        mode="MODE_B",
        availability_slots=(
            AvailabilitySlotDTO("tuesday", "19:30", "21:30"),
            AvailabilitySlotDTO("thursday", "19:30", "21:30"),
            AvailabilitySlotDTO("saturday", "09:00", "12:00"),
        ),
    )
    r10_tasks = _strip_schedule_fields(rm10["decomposer"]["proposal"]["tasks"])
    r10_deps = rm10["decomposer"]["proposal"]["dependencies"]
    res10 = SpatioTemporalRuleEngine.allocate_task_sessions_with_diagnostics(
        r10_tasks,
        avail_g2,
        start_date=date(2026, 11, 17),
        target_date=date(2026, 12, 15),
        dependencies=r10_deps,
        preferred_session_minutes=60,
    )
    assert res10.feasibility_verdict == "VERIFIED_FEASIBLE"
    assert _count_sensitive_cross_day_splits(res10.tasks, res10.schedule_blocks) == 0
    t8_blocks = [b for b in res10.schedule_blocks if b["task_id"] == "T8"]
    assert len(t8_blocks) == 1
    assert t8_blocks[0]["scheduled_duration_minutes"] == 100

    # R-08: T29 (90m Mock Test 1) & T30 (120m Mock Test 2)
    rm08, _ = _load_exp09_roadmap("R-08")
    r08_tasks = _strip_schedule_fields(rm08["decomposer"]["proposal"]["tasks"])
    r08_deps = rm08["decomposer"]["proposal"]["dependencies"]

    # Case A: Original G4 availability (max 90m on Sat/Sun): T29 places whole, T30 fails NC-2 cleanly (never split!)
    avail_g4_90 = AvailabilityConfigurationDTO(
        mode="MODE_A",
        daily_quota_minutes={
            "monday": 60,
            "tuesday": 60,
            "wednesday": 60,
            "thursday": 60,
            "friday": 60,
            "saturday": 90,
            "sunday": 90,
        },
        default_daily_quota_minutes=60,
    )
    res08_90 = SpatioTemporalRuleEngine.allocate_task_sessions_with_diagnostics(
        r08_tasks,
        avail_g4_90,
        start_date=date(2026, 11, 17),
        target_date=date(2026, 12, 31),
        dependencies=r08_deps,
        preferred_session_minutes=60,
    )
    assert _count_sensitive_cross_day_splits(res08_90.tasks, res08_90.schedule_blocks) == 0
    assert len([b for b in res08_90.schedule_blocks if b["task_id"] == "T29"]) == 1
    assert res08_90.feasibility_verdict == "EXPLICIT_UNSCHEDULABLE"
    assert any(
        d.task_id == "T30" and d.reason_code == "TASK_EXCEEDS_CONTINUOUS_SLOT"
        for d in res08_90.unscheduled_diagnostics
    )

    # Case B: Weekend 120m quota: both T29 (90m) and T30 (120m) place whole in 1 block each
    avail_g4_120 = AvailabilityConfigurationDTO(
        mode="MODE_A",
        daily_quota_minutes={
            "monday": 60,
            "tuesday": 60,
            "wednesday": 60,
            "thursday": 60,
            "friday": 60,
            "saturday": 120,
            "sunday": 120,
        },
        default_daily_quota_minutes=60,
    )
    res08_120 = SpatioTemporalRuleEngine.allocate_task_sessions_with_diagnostics(
        r08_tasks,
        avail_g4_120,
        start_date=date(2026, 11, 17),
        target_date=date(2026, 12, 31),
        dependencies=r08_deps,
        preferred_session_minutes=60,
    )
    assert res08_120.feasibility_verdict == "VERIFIED_FEASIBLE"
    assert _count_sensitive_cross_day_splits(res08_120.tasks, res08_120.schedule_blocks) == 0
    assert len([b for b in res08_120.schedule_blocks if b["task_id"] == "T29"]) == 1
    assert len([b for b in res08_120.schedule_blocks if b["task_id"] == "T30"]) == 1


def test_g4_and_g5_pack_100_percent_on_attempt_1_with_zero_slivers_or_effort_mutation() -> None:
    # G5 (90m Mon/Wed/Fri, 180m Sat, capacity=2250m, preferred=60): 1980m packability rescue
    avail_g5 = AvailabilityConfigurationDTO(
        mode="MODE_B",
        availability_slots=(
            AvailabilitySlotDTO("monday", "19:30", "21:00"),
            AvailabilitySlotDTO("wednesday", "19:30", "21:00"),
            AvailabilitySlotDTO("friday", "19:30", "21:00"),
            AvailabilitySlotDTO("saturday", "09:00", "12:00"),
        ),
    )
    g5_tasks = (
        [
            {
                "task_id": f"G5_T{i + 1}",
                "milestone_id": "m1",
                "title": f"Task {i + 1}",
                "estimated_minutes": 120,
            }
            for i in range(6)
        ]
        + [
            {
                "task_id": f"G5_T{i + 7}",
                "milestone_id": "m2",
                "title": f"Task {i + 7}",
                "estimated_minutes": 90,
            }
            for i in range(6)
        ]
        + [
            {
                "task_id": f"G5_T{i + 13}",
                "milestone_id": "m3",
                "title": f"Task {i + 13}",
                "estimated_minutes": 60,
            }
            for i in range(12)
        ]
    )
    g5_orig_efforts = {t["task_id"]: t["estimated_minutes"] for t in g5_tasks}

    # Confirm legacy fails attempt 1 due to blind divmod stranding 30m tails
    legacy_tasks, _ = SpatioTemporalRuleEngine.allocate_task_sessions(
        g5_tasks,
        avail_g5,
        start_date=date(2026, 11, 17),
        target_date=date(2026, 12, 22),
        preferred_session_minutes=60,
        hard_solver_v2_enabled=False,
    )
    assert any(t["scheduled_date"] is None for t in legacy_tasks)

    # Phase 1 hard solver places 100% with 0 <30m blocks and 0 effort mutation
    res_g5 = SpatioTemporalRuleEngine.allocate_task_sessions_with_diagnostics(
        g5_tasks,
        avail_g5,
        start_date=date(2026, 11, 17),
        target_date=date(2026, 12, 22),
        preferred_session_minutes=60,
    )
    assert res_g5.feasibility_verdict == "VERIFIED_FEASIBLE"
    assert all(t["scheduled_date"] is not None for t in res_g5.tasks)
    assert all(b["scheduled_duration_minutes"] >= 30 for b in res_g5.schedule_blocks)
    assert {t["task_id"]: t["estimated_minutes"] for t in res_g5.tasks} == g5_orig_efforts

    # G4 (60m Mon-Fri, 90m Sat-Sun, capacity=3060m, preferred=60): 2460m from R-08 with splittable tasks
    rm08, _ = _load_exp09_roadmap("R-08")
    g4_tasks = [
        {**t, "is_non_splittable": False}
        for t in _strip_schedule_fields(rm08["decomposer"]["proposal"]["tasks"])
    ]
    g4_orig_efforts = {t["task_id"]: t["estimated_minutes"] for t in g4_tasks}
    avail_g4 = AvailabilityConfigurationDTO(
        mode="MODE_A",
        daily_quota_minutes={
            "monday": 60,
            "tuesday": 60,
            "wednesday": 60,
            "thursday": 60,
            "friday": 60,
            "saturday": 90,
            "sunday": 90,
        },
        default_daily_quota_minutes=60,
    )
    res_g4 = SpatioTemporalRuleEngine.allocate_task_sessions_with_diagnostics(
        g4_tasks,
        avail_g4,
        start_date=date(2026, 11, 17),
        target_date=date(2026, 12, 31),
        dependencies=rm08["decomposer"]["proposal"]["dependencies"],
        preferred_session_minutes=60,
    )
    assert res_g4.feasibility_verdict == "VERIFIED_FEASIBLE"
    assert all(t["scheduled_date"] is not None for t in res_g4.tasks)
    assert all(b["scheduled_duration_minutes"] >= 30 for b in res_g4.schedule_blocks)
    assert {t["task_id"]: t["estimated_minutes"] for t in res_g4.tasks} == g4_orig_efforts


def test_necessary_conditions_vs_heuristic_incomplete_and_repair() -> None:
    # NC-1: Total effort exceeds hard packable capacity -> EXPLICIT_UNSCHEDULABLE
    avail_120 = AvailabilityConfigurationDTO(
        mode="MODE_B",
        availability_slots=(AvailabilitySlotDTO("monday", "19:00", "21:00"),),
    )
    res_nc1 = SpatioTemporalRuleEngine.allocate_task_sessions_with_diagnostics(
        [
            {"task_id": "t1", "title": "Bài 1", "estimated_minutes": 120},
            {"task_id": "t2", "title": "Bài 2", "estimated_minutes": 60},
        ],
        avail_120,
        start_date=date(2026, 11, 2),
        target_date=date(2026, 11, 2),
    )
    assert res_nc1.feasibility_verdict == "EXPLICIT_UNSCHEDULABLE"
    assert res_nc1.necessary_conditions.nc1_passed is False
    assert res_nc1.unscheduled_diagnostics[0].reason_code == "TOTAL_EFFORT_EXCEEDS_HARD_CAPACITY"

    # NC-1 with existing_tasks causing calendar saturation -> CALENDAR_CONFLICT_SATURATION
    res_cal = SpatioTemporalRuleEngine.allocate_task_sessions_with_diagnostics(
        [{"task_id": "t1", "title": "Bài 1", "estimated_minutes": 120}],
        avail_120,
        start_date=date(2026, 11, 2),
        target_date=date(2026, 11, 2),
        existing_tasks=[
            {
                "status": "TODO",
                "scheduled_date": "2026-11-02",
                "scheduled_start": "2026-11-02T19:00:00+00:00",
                "scheduled_end": "2026-11-02T20:00:00+00:00",
                "estimated_minutes": 60,
            }
        ],
    )
    assert res_cal.feasibility_verdict == "EXPLICIT_UNSCHEDULABLE"
    assert res_cal.unscheduled_diagnostics[0].reason_code == "CALENDAR_CONFLICT_SATURATION"

    # NC-2: 120m non-splittable task in 90m max slot -> TASK_EXCEEDS_CONTINUOUS_SLOT
    avail_90 = AvailabilityConfigurationDTO(
        mode="MODE_B",
        availability_slots=(
            AvailabilitySlotDTO("monday", "19:30", "21:00"),
            AvailabilitySlotDTO("wednesday", "19:30", "21:00"),
        ),
    )
    res_nc2 = SpatioTemporalRuleEngine.allocate_task_sessions_with_diagnostics(
        [{"task_id": "t_exam", "title": "Thi thử Mock Test 120p", "estimated_minutes": 120}],
        avail_90,
        start_date=date(2026, 11, 2),
        target_date=date(2026, 11, 8),
    )
    assert res_nc2.feasibility_verdict == "EXPLICIT_UNSCHEDULABLE"
    assert res_nc2.necessary_conditions.nc2_passed is False
    assert res_nc2.unscheduled_diagnostics[0].reason_code == "TASK_EXCEEDS_CONTINUOUS_SLOT"

    # NC-3: Already-scheduled predecessor anchors chain late in horizon -> CRITICAL_PATH_EXCEEDS_WINDOW
    avail_daily_60 = AvailabilityConfigurationDTO(mode="MODE_A", default_daily_quota_minutes=60)
    res_nc3 = SpatioTemporalRuleEngine.allocate_task_sessions_with_diagnostics(
        [
            {
                "task_id": "t1",
                "title": "Root",
                "estimated_minutes": 60,
                "scheduled_date": "2026-11-05",
            },
            {"task_id": "t2", "title": "Step 2", "estimated_minutes": 60},
            {"task_id": "t3", "title": "Step 3", "estimated_minutes": 60},
        ],
        avail_daily_60,
        start_date=date(2026, 11, 2),
        target_date=date(2026, 11, 5),
        dependencies=[
            {"predecessor_id": "t1", "successor_id": "t2", "is_mandatory": True},
            {"predecessor_id": "t2", "successor_id": "t3", "is_mandatory": True},
        ],
    )
    assert res_nc3.feasibility_verdict == "EXPLICIT_UNSCHEDULABLE"
    assert res_nc3.necessary_conditions.nc1_passed is True  # 120m unplaced <= 180m free (Nov 2..4)
    assert res_nc3.necessary_conditions.nc3_passed is False
    assert any(
        d.reason_code == "CRITICAL_PATH_EXCEEDS_WINDOW" for d in res_nc3.unscheduled_diagnostics
    )

    # Bounded Repair Pass rescues order-dependent non-splittable conflict:
    # Sat (2026-11-07) has 90m, Mon (2026-11-09) has 60m. T1=60m splittable comes before T2=90m non-splittable.
    avail_sat90_mon60 = AvailabilityConfigurationDTO(
        mode="MODE_B",
        availability_slots=(
            AvailabilitySlotDTO("saturday", "09:00", "10:30"),
            AvailabilitySlotDTO("monday", "19:00", "20:00"),
        ),
    )
    res_repair = SpatioTemporalRuleEngine.allocate_task_sessions_with_diagnostics(
        [
            {"task_id": "t1", "title": "Bài tập thường", "estimated_minutes": 60},
            {"task_id": "t2", "title": "Thi thử Mock Test", "estimated_minutes": 90},
        ],
        avail_sat90_mon60,
        start_date=date(2026, 11, 7),
        target_date=date(2026, 11, 9),
    )
    assert res_repair.feasibility_verdict == "VERIFIED_FEASIBLE"
    assert res_repair.repairs_attempted >= 1
    assert all(t["scheduled_date"] is not None for t in res_repair.tasks)

    # HEURISTIC_ALLOCATION_INCOMPLETE:
    # 3 non-splittable 60m tasks (total 180m) in two 100m slots (total packable 200m >= 180m, max slot 100m >= 60m).
    # NC-1..3 all pass mathematically, yet discrete bin-packing cannot place 3 x 60m non-splittable in 2 x 100m slots.
    avail_two_100 = AvailabilityConfigurationDTO(
        mode="MODE_B",
        availability_slots=(
            AvailabilitySlotDTO("monday", "19:00", "20:40"),
            AvailabilitySlotDTO("tuesday", "19:00", "20:40"),
        ),
    )
    res_heur = SpatioTemporalRuleEngine.allocate_task_sessions_with_diagnostics(
        [
            {"task_id": "e1", "title": "Mock Test 1", "estimated_minutes": 60},
            {"task_id": "e2", "title": "Mock Test 2", "estimated_minutes": 60},
            {"task_id": "e3", "title": "Mock Test 3", "estimated_minutes": 60},
        ],
        avail_two_100,
        start_date=date(2026, 11, 2),
        target_date=date(2026, 11, 3),
    )
    assert res_heur.necessary_conditions.nc1_passed is True
    assert res_heur.necessary_conditions.nc2_passed is True
    assert res_heur.necessary_conditions.nc3_passed is True
    assert res_heur.feasibility_verdict == "HEURISTIC_ALLOCATION_INCOMPLETE"
    assert len(res_heur.unscheduled_diagnostics) == 1
    assert res_heur.unscheduled_diagnostics[0].reason_code == "HEURISTIC_ALLOCATION_INCOMPLETE"


def test_tier1_gate_blocks_non_splittable_task_split_across_days() -> None:
    mid = str(uuid4())
    violations = run_tier1_gate(
        {
            "tasks": [
                {
                    "task_id": "T29",
                    "milestone_id": mid,
                    "title": "Thi thử Mock Test 1",
                    "estimated_minutes": 90,
                    "scheduled_date": "2026-12-24",
                    "scheduled_start": "2026-12-24T19:00:00+00:00",
                    "scheduled_end": "2026-12-25T19:45:00+00:00",
                }
            ],
            "schedule_blocks": [
                {
                    "task_id": "T29",
                    "sequence_in_task": 1,
                    "block_date": "2026-12-24",
                    "scheduled_start": "2026-12-24T19:00:00+00:00",
                    "scheduled_end": "2026-12-24T19:45:00+00:00",
                    "scheduled_duration_minutes": 45,
                },
                {
                    "task_id": "T29",
                    "sequence_in_task": 2,
                    "block_date": "2026-12-25",
                    "scheduled_start": "2026-12-25T19:00:00+00:00",
                    "scheduled_end": "2026-12-25T19:45:00+00:00",
                    "scheduled_duration_minutes": 45,
                },
            ],
        },
        valid_milestone_ids={mid},
    )
    assert any(v.rule_code == "NON_SPLITTABLE_TASK_SPLIT_ACROSS_DAYS" for v in violations)


@pytest.mark.asyncio
async def test_orchestrator_propagates_verdict_and_supports_v2_rollback_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mid = uuid4()
    canned = {
        "tasks": [
            {
                "task_id": "T1",
                "milestone_id": str(mid),
                "title": "Lập trình DAG với Airflow",
                "estimated_minutes": 90,
            }
        ],
        "dependencies": [],
    }
    avail = AvailabilityConfigurationDTO(
        mode="MODE_B",
        availability_slots=(AvailabilitySlotDTO("monday", "19:30", "21:00"),),
    )

    gate = ProposalValidationGateOrchestrator(
        llm_provider=StubLLMAdapter(canned_responses=[canned]),
        enable_tier3_judge=False,
    )
    res_v2 = await gate.generate_and_validate_proposal_with_retry(
        system_prompt="sys",
        user_prompt="usr",
        response_schema=None,
        availability=avail,
        valid_milestone_ids={mid},
        start_date=date(2026, 11, 2),
        current_roadmap_target_date=date(2026, 11, 2),
        deterministic_allocation=True,
        preferred_session_minutes=60,
    )
    assert res_v2.feasibility_verdict == "VERIFIED_FEASIBLE"
    assert len(res_v2.validated_proposal_data["schedule_blocks"]) == 1
    assert res_v2.validated_proposal_data["schedule_blocks"][0]["scheduled_duration_minutes"] == 90

    # Rollback flag=False falls back to legacy pre-splitting (45+45)
    from src.shared_kernel import config as shared_config

    settings_off = shared_config.Settings(spatio_temporal_v2_hard_solver_enabled=False)
    monkeypatch.setattr(
        "src.planning.application.services.validation_gate.orchestrator.get_settings",
        lambda: settings_off,
    )
    gate_off = ProposalValidationGateOrchestrator(
        llm_provider=StubLLMAdapter(canned_responses=[canned]),
        enable_tier3_judge=False,
    )
    res_legacy = await gate_off.generate_and_validate_proposal_with_retry(
        system_prompt="sys",
        user_prompt="usr",
        response_schema=None,
        availability=avail,
        valid_milestone_ids={mid},
        start_date=date(2026, 11, 2),
        current_roadmap_target_date=date(2026, 11, 2),
        deterministic_allocation=True,
        preferred_session_minutes=60,
    )
    assert [
        b["scheduled_duration_minutes"]
        for b in res_legacy.validated_proposal_data["schedule_blocks"]
    ] == [45, 45]
