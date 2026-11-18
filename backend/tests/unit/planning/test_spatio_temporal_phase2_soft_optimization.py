from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from src.planning.application.services.validation_gate.orchestrator import (
    ProposalValidationGateOrchestrator,
)
from src.planning.domain.services.spatio_temporal_engine import (
    NonSplittableTaskClassifier,
    SpatioTemporalRuleEngine,
)
from src.planning.domain.services.validation_types import (
    AvailabilityConfigurationDTO,
    AvailabilitySlotDTO,
)
from src.shared_kernel import config as shared_config
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


def _goal_constraints(goal_key: str) -> tuple[date, date, int, AvailabilityConfigurationDTO]:
    if goal_key == "G1_BEGINNER_PYTHON_FASTAPI":
        return (
            date(2026, 11, 17),
            date(2026, 12, 17),
            60,
            AvailabilityConfigurationDTO(
                mode="MODE_A",
                default_daily_quota_minutes=90,
                daily_quota_minutes={
                    "monday": 90,
                    "tuesday": 90,
                    "wednesday": 90,
                    "thursday": 90,
                    "friday": 90,
                    "saturday": 120,
                    "sunday": 120,
                },
            ),
        )
    if goal_key == "G3_ADVANCED_RUST_ASYNC_TOKIO":
        return (
            date(2026, 11, 17),
            date(2026, 12, 29),
            90,
            AvailabilityConfigurationDTO(
                mode="MODE_A",
                default_daily_quota_minutes=90,
                daily_quota_minutes={
                    "monday": 90,
                    "tuesday": 90,
                    "wednesday": 90,
                    "thursday": 90,
                    "friday": 90,
                    "saturday": 150,
                    "sunday": 150,
                },
            ),
        )
    if goal_key == "G4_BEGINNER_IELTS_WRITING":
        return (
            date(2026, 11, 17),
            date(2026, 12, 31),
            60,
            AvailabilityConfigurationDTO(
                mode="MODE_A",
                default_daily_quota_minutes=60,
                daily_quota_minutes={
                    "monday": 60,
                    "tuesday": 60,
                    "wednesday": 60,
                    "thursday": 60,
                    "friday": 60,
                    "saturday": 90,
                    "sunday": 90,
                },
            ),
        )
    if goal_key == "G2_INTERMEDIATE_SYSTEM_DESIGN_CACHE":
        return (
            date(2026, 11, 17),
            date(2026, 12, 15),
            60,
            AvailabilityConfigurationDTO(
                mode="MODE_B",
                availability_slots=(
                    AvailabilitySlotDTO("tuesday", "19:30", "21:30"),
                    AvailabilitySlotDTO("thursday", "19:30", "21:30"),
                    AvailabilitySlotDTO("saturday", "09:00", "12:00"),
                ),
            ),
        )
    if goal_key == "G5_INTERMEDIATE_DATA_ENG_AIRFLOW_DBT":
        return (
            date(2026, 11, 17),
            date(2026, 12, 22),
            60,
            AvailabilityConfigurationDTO(
                mode="MODE_B",
                availability_slots=(
                    AvailabilitySlotDTO("monday", "19:30", "21:00"),
                    AvailabilitySlotDTO("wednesday", "19:30", "21:00"),
                    AvailabilitySlotDTO("friday", "19:30", "21:00"),
                    AvailabilitySlotDTO("saturday", "09:00", "12:00"),
                ),
            ),
        )
    raise AssertionError(f"Unsupported goal_key {goal_key}")


def _schedule_metrics(
    tasks: list[dict[str, Any]],
    blocks: list[dict[str, Any]],
    *,
    target_date: date,
) -> dict[str, Any]:
    dates = sorted({date.fromisoformat(str(b["block_date"])[:10]) for b in blocks})
    max_streak = SpatioTemporalRuleEngine._max_consecutive_study_days(blocks)
    cross_day_tasks, cross_day_spans = SpatioTemporalRuleEngine._count_cross_day_splits(blocks)
    adj_splits = SpatioTemporalRuleEngine._count_adjacent_same_day_splits(blocks)
    idle_before_deadline = (target_date - dates[-1]).days if dates else 0
    span_days = (dates[-1] - dates[0]).days + 1 if dates else 0
    ns_cross_day = 0
    dates_by_task: dict[str, set[str]] = {}
    for b in blocks:
        dates_by_task.setdefault(str(b["task_id"]), set()).add(str(b["block_date"])[:10])
    for t in tasks:
        tid = str(t.get("task_id") or t.get("id"))
        if (
            NonSplittableTaskClassifier.is_non_splittable(t)
            and len(dates_by_task.get(tid, set())) > 1
        ):
            ns_cross_day += 1
    return {
        "max_streak": max_streak,
        "days_idle_before_deadline": idle_before_deadline,
        "cross_day_tasks": cross_day_tasks,
        "cross_day_spans": cross_day_spans,
        "adjacent_same_day_splits": adj_splits,
        "non_splittable_cross_day": ns_cross_day,
        "active_days": len(dates),
        "calendar_span_days": span_days,
        "first_date": dates[0] if dates else None,
        "last_date": dates[-1] if dates else None,
    }


def _assert_orchestrator_hard_valid(
    tasks: list[dict[str, Any]],
    blocks: list[dict[str, Any]],
    deps: list[dict[str, Any]],
    avail: AvailabilityConfigurationDTO,
    target_date: date,
) -> None:
    proposal = {"tasks": tasks, "schedule_blocks": blocks, "dependencies": deps}
    v1 = ProposalValidationGateOrchestrator.run_tier1_gate(proposal, is_ai_generated=True)
    v2, w2 = ProposalValidationGateOrchestrator.run_tier2_gate(
        proposal,
        availability=avail,
        current_roadmap_target_date=target_date,
    )
    assert v1 == [], f"Tier 1 violations: {v1}"
    assert v2 == [], f"Tier 2 violations: {v2}"
    assert w2 == [], f"Unexpected soft overflow warnings: {w2}"


@pytest.mark.parametrize("label", ["R-01", "R-02", "R-04", "R-05", "R-07"])
def test_replay_mode_a_roadmaps_reduce_streak_and_preserve_zero_extra_splits(label: str) -> None:
    rm, meta = _load_exp09_roadmap(label)
    sd, td, pref, avail = _goal_constraints(meta["goal_id"])
    tasks_in = _strip_schedule_fields(rm["decomposer"]["proposal"]["tasks"])
    deps = rm["decomposer"]["proposal"]["dependencies"]
    orig_efforts = {t["task_id"]: t["estimated_minutes"] for t in tasks_in}

    cap = SpatioTemporalRuleEngine.calculate_available_capacity_minutes(
        avail, start_date=sd, target_date=td
    )
    req = sum(orig_efforts.values())
    assert req / cap <= 0.85

    res_hard = SpatioTemporalRuleEngine.allocate_task_sessions_with_diagnostics(
        tasks_in,
        avail,
        start_date=sd,
        target_date=td,
        dependencies=deps,
        preferred_session_minutes=pref,
        soft_pacing_v2_enabled=False,
    )
    res_soft = SpatioTemporalRuleEngine.allocate_task_sessions_with_diagnostics(
        tasks_in,
        avail,
        start_date=sd,
        target_date=td,
        dependencies=deps,
        preferred_session_minutes=pref,
        soft_pacing_v2_enabled=True,
    )
    assert res_hard.feasibility_verdict == "VERIFIED_FEASIBLE"
    assert res_soft.feasibility_verdict == "VERIFIED_FEASIBLE"

    m_hard = _schedule_metrics(res_hard.tasks, res_hard.schedule_blocks, target_date=td)
    m_soft = _schedule_metrics(res_soft.tasks, res_soft.schedule_blocks, target_date=td)

    # Streak drops from 9..29d (11..34d in exp_09) down to <= 6d (<= 5d)
    assert m_hard["max_streak"] >= 9
    assert m_soft["max_streak"] <= 6
    assert m_soft["max_streak"] <= 5

    # Zero extra cross-day splits, zero adjacent splits, zero non-splittable splits, zero <30m slivers
    assert m_soft["cross_day_tasks"] <= m_hard["cross_day_tasks"]
    assert m_soft["cross_day_spans"] <= m_hard["cross_day_spans"]
    assert m_soft["adjacent_same_day_splits"] == 0
    assert m_soft["non_splittable_cross_day"] == 0
    assert all(b["scheduled_duration_minutes"] >= 30 for b in res_soft.schedule_blocks)
    assert {t["task_id"]: t["estimated_minutes"] for t in res_soft.tasks} == orig_efforts

    # R-01 and R-05 spread evenly with end buffer instead of front-loading into days 1..11 or 1..23
    assert m_soft["days_idle_before_deadline"] >= 1
    if label in ("R-01", "R-05"):
        assert m_soft["calendar_span_days"] > m_hard["calendar_span_days"]
        assert m_soft["days_idle_before_deadline"] >= 4

    _assert_orchestrator_hard_valid(res_soft.tasks, res_soft.schedule_blocks, deps, avail, td)


def test_replay_r08_mode_a_handles_weekend_120m_splittable_and_unschedulable_phase1() -> None:
    rm, meta = _load_exp09_roadmap("R-08")
    sd, td, pref, avail_g4 = _goal_constraints(meta["goal_id"])
    tasks_in = _strip_schedule_fields(rm["decomposer"]["proposal"]["tasks"])
    deps = rm["decomposer"]["proposal"]["dependencies"]

    # Case 1: Original G4 (90m weekend) leaves T30 (120m non-splittable) EXPLICIT_UNSCHEDULABLE in Phase 1 -> Phase 2 stays untouched
    res_unsched_hard = SpatioTemporalRuleEngine.allocate_task_sessions_with_diagnostics(
        tasks_in,
        avail_g4,
        start_date=sd,
        target_date=td,
        dependencies=deps,
        preferred_session_minutes=pref,
        soft_pacing_v2_enabled=False,
    )
    res_unsched_soft = SpatioTemporalRuleEngine.allocate_task_sessions_with_diagnostics(
        tasks_in,
        avail_g4,
        start_date=sd,
        target_date=td,
        dependencies=deps,
        preferred_session_minutes=pref,
        soft_pacing_v2_enabled=True,
    )
    assert res_unsched_soft.feasibility_verdict == "EXPLICIT_UNSCHEDULABLE"
    assert res_unsched_soft.tasks == res_unsched_hard.tasks
    assert res_unsched_soft.schedule_blocks == res_unsched_hard.schedule_blocks

    # Case 2: Weekend 120m quota (util=0.719 <= 0.85, preserves T29=90m & T30=120m non-splittable)
    avail_g4_120 = AvailabilityConfigurationDTO(
        mode="MODE_A",
        default_daily_quota_minutes=60,
        daily_quota_minutes={
            "monday": 60,
            "tuesday": 60,
            "wednesday": 60,
            "thursday": 60,
            "friday": 60,
            "saturday": 120,
            "sunday": 120,
        },
    )
    r1_120 = SpatioTemporalRuleEngine.allocate_task_sessions_with_diagnostics(
        tasks_in,
        avail_g4_120,
        start_date=sd,
        target_date=td,
        dependencies=deps,
        preferred_session_minutes=pref,
        soft_pacing_v2_enabled=False,
    )
    r2_120 = SpatioTemporalRuleEngine.allocate_task_sessions_with_diagnostics(
        tasks_in,
        avail_g4_120,
        start_date=sd,
        target_date=td,
        dependencies=deps,
        preferred_session_minutes=pref,
        soft_pacing_v2_enabled=True,
    )
    m1_120 = _schedule_metrics(r1_120.tasks, r1_120.schedule_blocks, target_date=td)
    m2_120 = _schedule_metrics(r2_120.tasks, r2_120.schedule_blocks, target_date=td)
    assert m1_120["max_streak"] >= 20
    assert m2_120["max_streak"] <= 6
    assert m2_120["cross_day_tasks"] <= m1_120["cross_day_tasks"]
    assert m2_120["non_splittable_cross_day"] == 0
    assert m2_120["days_idle_before_deadline"] >= 1
    _assert_orchestrator_hard_valid(r2_120.tasks, r2_120.schedule_blocks, deps, avail_g4_120, td)

    # Case 3: Original G4 (90m weekend) with splittable tasks (util=0.804 <= 0.85)
    g4_splittable = [{**t, "is_non_splittable": False} for t in tasks_in]
    r1_split = SpatioTemporalRuleEngine.allocate_task_sessions_with_diagnostics(
        g4_splittable,
        avail_g4,
        start_date=sd,
        target_date=td,
        dependencies=deps,
        preferred_session_minutes=pref,
        soft_pacing_v2_enabled=False,
    )
    r2_split = SpatioTemporalRuleEngine.allocate_task_sessions_with_diagnostics(
        g4_splittable,
        avail_g4,
        start_date=sd,
        target_date=td,
        dependencies=deps,
        preferred_session_minutes=pref,
        soft_pacing_v2_enabled=True,
    )
    m1_split = _schedule_metrics(r1_split.tasks, r1_split.schedule_blocks, target_date=td)
    m2_split = _schedule_metrics(r2_split.tasks, r2_split.schedule_blocks, target_date=td)
    assert m1_split["max_streak"] >= 30
    assert m2_split["max_streak"] <= 6
    assert m2_split["cross_day_tasks"] <= m1_split["cross_day_tasks"]
    assert m2_split["days_idle_before_deadline"] >= 1
    _assert_orchestrator_hard_valid(r2_split.tasks, r2_split.schedule_blocks, deps, avail_g4, td)


@pytest.mark.parametrize("label", ["R-03", "R-06", "R-09", "R-10"])
def test_replay_mode_b_roadmaps_and_six_day_slot_streak_break(label: str) -> None:
    rm, meta = _load_exp09_roadmap(label)
    sd, td, pref, avail = _goal_constraints(meta["goal_id"])
    tasks_in = _strip_schedule_fields(rm["decomposer"]["proposal"]["tasks"])
    deps = rm["decomposer"]["proposal"]["dependencies"]

    r_hard = SpatioTemporalRuleEngine.allocate_task_sessions_with_diagnostics(
        tasks_in,
        avail,
        start_date=sd,
        target_date=td,
        dependencies=deps,
        preferred_session_minutes=pref,
        soft_pacing_v2_enabled=False,
    )
    r_soft = SpatioTemporalRuleEngine.allocate_task_sessions_with_diagnostics(
        tasks_in,
        avail,
        start_date=sd,
        target_date=td,
        dependencies=deps,
        preferred_session_minutes=pref,
        soft_pacing_v2_enabled=True,
    )
    assert r_soft.feasibility_verdict == "VERIFIED_FEASIBLE"
    m_hard = _schedule_metrics(r_hard.tasks, r_hard.schedule_blocks, target_date=td)
    m_soft = _schedule_metrics(r_soft.tasks, r_soft.schedule_blocks, target_date=td)
    assert m_soft["cross_day_tasks"] <= m_hard["cross_day_tasks"]
    assert m_soft["non_splittable_cross_day"] == 0
    assert m_soft["max_streak"] <= 6
    _assert_orchestrator_hard_valid(r_soft.tasks, r_soft.schedule_blocks, deps, avail, td)

    # MODE_B with Mon..Sat slots (6 consecutive days) breaks streak to <= 5 when slack allows
    avail_6day = AvailabilityConfigurationDTO(
        mode="MODE_B",
        availability_slots=tuple(
            AvailabilitySlotDTO(day, "19:00", "20:00")
            for day in ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday")
        ),
    )
    tasks_6day = [
        {"task_id": f"B{i}", "title": f"Unit {i}", "estimated_minutes": 60} for i in range(1, 8)
    ]
    res_6day = SpatioTemporalRuleEngine.allocate_task_sessions_with_diagnostics(
        tasks_6day,
        avail_6day,
        start_date=date(2026, 11, 2),
        target_date=date(2026, 11, 21),
        preferred_session_minutes=60,
        soft_pacing_v2_enabled=True,
    )
    assert res_6day.feasibility_verdict == "VERIFIED_FEASIBLE"
    assert SpatioTemporalRuleEngine._max_consecutive_study_days(res_6day.schedule_blocks) <= 5
    _assert_orchestrator_hard_valid(
        res_6day.tasks, res_6day.schedule_blocks, [], avail_6day, date(2026, 11, 21)
    )


def test_tight_deadline_95_percent_utilization_gracefully_relaxes_and_passes_gates() -> None:
    # 19 x 60m = 1140m across 20 days x 60m = 1200m (95.0% utilization).
    # Cannot fit end_buffer (2 days) or 3 recovery days without dropping tasks -> relaxes cleanly to valid schedule.
    avail_60 = AvailabilityConfigurationDTO(mode="MODE_A", default_daily_quota_minutes=60)
    sd = date(2026, 11, 2)
    td = sd + timedelta(days=19)  # 20 days -> 1200m
    tasks_95 = [
        {"task_id": f"T{i}", "milestone_id": "m1", "title": f"Task {i}", "estimated_minutes": 60}
        for i in range(1, 20)
    ]
    deps_95 = [
        {"predecessor_id": f"T{i}", "successor_id": f"T{i + 1}", "is_mandatory": True}
        for i in range(1, 19)
    ]

    res_soft = SpatioTemporalRuleEngine.allocate_task_sessions_with_diagnostics(
        tasks_95,
        avail_60,
        start_date=sd,
        target_date=td,
        dependencies=deps_95,
        preferred_session_minutes=60,
        soft_pacing_v2_enabled=True,
    )
    assert res_soft.feasibility_verdict == "VERIFIED_FEASIBLE"
    assert len(res_soft.unscheduled_diagnostics) == 0
    assert all(t["scheduled_date"] is not None for t in res_soft.tasks)
    assert sum(b["scheduled_duration_minutes"] for b in res_soft.schedule_blocks) == 1140
    _assert_orchestrator_hard_valid(res_soft.tasks, res_soft.schedule_blocks, deps_95, avail_60, td)


@pytest.mark.asyncio
async def test_soft_pacing_rollback_flag_in_engine_and_orchestrator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    defaults = shared_config.Settings()
    assert defaults.spatio_temporal_v2_soft_pacing_enabled is True
    assert defaults.spatio_temporal_soft_end_buffer_ratio == 0.12
    assert defaults.spatio_temporal_soft_max_consecutive_days == 5
    # PR-4: Decomposer timeout tuned to 36.0s within 55.0s SSE pipeline cap
    assert defaults.ai_task_decomposer_timeout_seconds == 36.0
    assert defaults.ai_task_decomposer_timeout_seconds <= defaults.ai_sse_pipeline_timeout_seconds

    mid = uuid4()
    tasks_in = [
        {
            "task_id": f"T{i}",
            "milestone_id": str(mid),
            "title": f"Học bài {i}",
            "estimated_minutes": 60,
        }
        for i in range(1, 9)
    ]
    avail = AvailabilityConfigurationDTO(mode="MODE_A", default_daily_quota_minutes=60)
    sd = date(2026, 11, 2)
    td = date(2026, 11, 21)

    res_hard = SpatioTemporalRuleEngine.allocate_task_sessions_with_diagnostics(
        tasks_in,
        avail,
        start_date=sd,
        target_date=td,
        preferred_session_minutes=60,
        soft_pacing_v2_enabled=False,
    )
    res_soft = SpatioTemporalRuleEngine.allocate_task_sessions_with_diagnostics(
        tasks_in,
        avail,
        start_date=sd,
        target_date=td,
        preferred_session_minutes=60,
        soft_pacing_v2_enabled=True,
    )
    assert SpatioTemporalRuleEngine._max_consecutive_study_days(res_hard.schedule_blocks) == 8
    assert SpatioTemporalRuleEngine._max_consecutive_study_days(res_soft.schedule_blocks) <= 5

    # Direct allocate_task_sessions forwards soft_pacing_v2_enabled=False
    tasks_off, blocks_off = SpatioTemporalRuleEngine.allocate_task_sessions(
        tasks_in,
        avail,
        start_date=sd,
        target_date=td,
        preferred_session_minutes=60,
        soft_pacing_v2_enabled=False,
    )
    assert tasks_off == res_hard.tasks
    assert blocks_off == res_hard.schedule_blocks

    # Orchestrator respects Settings(spatio_temporal_v2_soft_pacing_enabled=False)
    canned = {"tasks": tasks_in, "dependencies": []}
    gate_on = ProposalValidationGateOrchestrator(
        llm_provider=StubLLMAdapter(canned_responses=[canned]),
        enable_tier3_judge=False,
    )
    out_on = await gate_on.generate_and_validate_proposal_with_retry(
        system_prompt="sys",
        user_prompt="usr",
        response_schema=None,
        availability=avail,
        valid_milestone_ids={mid},
        start_date=sd,
        current_roadmap_target_date=td,
        deterministic_allocation=True,
        preferred_session_minutes=60,
    )
    assert (
        SpatioTemporalRuleEngine._max_consecutive_study_days(
            out_on.validated_proposal_data["schedule_blocks"]
        )
        <= 5
    )

    settings_off = shared_config.Settings(spatio_temporal_v2_soft_pacing_enabled=False)
    monkeypatch.setattr(
        "src.planning.application.services.validation_gate.orchestrator.get_settings",
        lambda: settings_off,
    )
    gate_off = ProposalValidationGateOrchestrator(
        llm_provider=StubLLMAdapter(canned_responses=[canned]),
        enable_tier3_judge=False,
    )
    out_off = await gate_off.generate_and_validate_proposal_with_retry(
        system_prompt="sys",
        user_prompt="usr",
        response_schema=None,
        availability=avail,
        valid_milestone_ids={mid},
        start_date=sd,
        current_roadmap_target_date=td,
        deterministic_allocation=True,
        preferred_session_minutes=60,
    )
    assert out_off.validated_proposal_data["schedule_blocks"] == res_hard.schedule_blocks


def test_fault_injection_revalidation_failure_falls_back_atomically_to_phase1_s_hard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rm, meta = _load_exp09_roadmap("R-01")
    sd, td, pref, avail = _goal_constraints(meta["goal_id"])
    tasks_in = _strip_schedule_fields(rm["decomposer"]["proposal"]["tasks"])
    deps = rm["decomposer"]["proposal"]["dependencies"]

    res_hard = SpatioTemporalRuleEngine.allocate_task_sessions_with_diagnostics(
        tasks_in,
        avail,
        start_date=sd,
        target_date=td,
        dependencies=deps,
        preferred_session_minutes=pref,
        soft_pacing_v2_enabled=False,
    )

    calls = 0

    @classmethod  # type: ignore[misc]
    def _always_fail_revalidation(cls: type[SpatioTemporalRuleEngine], **kwargs: Any) -> list[str]:
        nonlocal calls
        del cls, kwargs
        calls += 1
        return ["INJECTED_HARD_VIOLATION"]

    monkeypatch.setattr(
        SpatioTemporalRuleEngine,
        "_validate_phase2_candidate",
        _always_fail_revalidation,
    )

    res_fallback = SpatioTemporalRuleEngine.allocate_task_sessions_with_diagnostics(
        tasks_in,
        avail,
        start_date=sd,
        target_date=td,
        dependencies=deps,
        preferred_session_minutes=pref,
        soft_pacing_v2_enabled=True,
    )
    assert calls >= 1
    assert res_fallback.feasibility_verdict == "VERIFIED_FEASIBLE"
    assert res_fallback.tasks == res_hard.tasks
    assert res_fallback.schedule_blocks == res_hard.schedule_blocks


@pytest.mark.asyncio
async def test_pr4_decomposer_timeout_36s_no_retry_on_timeout_and_fast_error_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    defaults = shared_config.Settings()
    assert defaults.ai_task_decomposer_timeout_seconds == 36.0
    assert defaults.ai_sse_pipeline_timeout_seconds == 55.0
    assert defaults.ai_task_decomposer_timeout_seconds <= defaults.ai_sse_pipeline_timeout_seconds

    mid = uuid4()
    avail = AvailabilityConfigurationDTO(mode="MODE_A", default_daily_quota_minutes=90)

    # 1. TimeoutError from provider must NOT trigger a second Decomposer attempt
    class _TimeoutLLM(StubLLMAdapter):
        def __init__(self) -> None:
            super().__init__()
            self.call_count = 0

        async def generate_structured(self, **kwargs: Any) -> Any:
            del kwargs
            self.call_count += 1
            raise TimeoutError("Simulated Decomposer 36s timeout")

    timeout_llm = _TimeoutLLM()
    gate_timeout = ProposalValidationGateOrchestrator(
        llm_provider=timeout_llm,
        enable_tier3_judge=False,
    )
    with pytest.raises(TimeoutError):
        await gate_timeout.generate_and_validate_proposal_with_retry(
            system_prompt="sys",
            user_prompt="usr",
            response_schema=None,
            availability=avail,
            valid_milestone_ids={mid},
            start_date=date(2026, 11, 2),
            current_roadmap_target_date=date(2026, 11, 10),
            deterministic_allocation=True,
            max_retries=2,
        )
    assert timeout_llm.call_count == 1

    # 2. Fast validation error retries only when remaining_seconds >= min_retry_remaining
    bad_payload = {"tasks": [], "dependencies": []}
    good_payload = {
        "tasks": [
            {
                "task_id": "T1",
                "milestone_id": str(mid),
                "title": "Học cơ bản",
                "task_type": "THEORY",
                "learning_objective": "Hiểu khái niệm",
                "completion_criteria": "Hoàn thành bài tập",
                "estimated_minutes": 60,
            }
        ],
        "dependencies": [],
    }
    fast_retry_gate = ProposalValidationGateOrchestrator(
        llm_provider=StubLLMAdapter(canned_responses=[bad_payload, good_payload]),
        enable_tier3_judge=False,
    )
    res_retried = await fast_retry_gate.generate_and_validate_proposal_with_retry(
        system_prompt="sys",
        user_prompt="usr",
        response_schema=None,
        availability=avail,
        valid_milestone_ids={mid},
        start_date=date(2026, 11, 2),
        current_roadmap_target_date=date(2026, 11, 10),
        deterministic_allocation=True,
        max_retries=2,
    )
    assert res_retried.attempts_used == 2

    # When remaining_seconds < ai_min_retry_remaining_seconds, fast validation error must NOT retry
    tight_settings = shared_config.Settings(
        ai_hard_timeout_seconds=55.0,
        ai_sse_pipeline_timeout_seconds=55.0,
        ai_milestone_planner_timeout_seconds=50.0,
        ai_task_decomposer_timeout_seconds=36.0,
        ai_min_retry_remaining_seconds=55.0,
    )
    monkeypatch.setattr(
        "src.planning.application.services.validation_gate.orchestrator.get_settings",
        lambda: tight_settings,
    )
    no_budget_gate = ProposalValidationGateOrchestrator(
        llm_provider=StubLLMAdapter(canned_responses=[bad_payload, good_payload]),
        enable_tier3_judge=False,
    )
    from src.planning.domain.exceptions.planning_exceptions import ProposalValidationGateError

    with pytest.raises(ProposalValidationGateError):
        await no_budget_gate.generate_and_validate_proposal_with_retry(
            system_prompt="sys",
            user_prompt="usr",
            response_schema=None,
            availability=avail,
            valid_milestone_ids={mid},
            start_date=date(2026, 11, 2),
            current_roadmap_target_date=date(2026, 11, 10),
            deterministic_allocation=True,
            max_retries=2,
        )
