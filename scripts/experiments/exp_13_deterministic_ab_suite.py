"""Experiment 13 (PR-4): Controlled A/B Suite (Control vs Treatment).

Compares Control (legacy flags: `spatio_temporal_v2_hard_solver_enabled=False`,
`spatio_temporal_v2_soft_pacing_enabled=False`, `milestone_effort_allocator_enabled=False`,
`ai_task_decomposer_timeout_seconds=25.0`) vs Treatment (PR-1 + PR-3A + PR-2 + PR-3B +
`ai_task_decomposer_timeout_seconds=36.0`) across:
  - Cohort A: Frozen deterministic replay (`R-01..R-10`, `M-01..M-12`, `G4`/`G5` attempt-1).
  - Cohort B: Live E2E runs via CofHub (`hard_planning_6_goals.jsonl` and
    `golden_planning_18_goals.jsonl`), gated by explicit gateway health probe.
  - Cohort C: 8 synthetic edge-case scenarios (`EC-1..EC-8`).

Constraints:
  - Zero production prompt, lockfile, or API schema changes.
  - Never prints, logs, or persists API keys or PII.
  - Never fabricates live LLM measurements if gateway is unreachable.

Output:
  - `docs/experiments/exp_13_deterministic_ab_results.json`
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
import urllib.error
import urllib.request
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Literal, Self
from uuid import UUID

from common import (
    BACKEND_DIR,
    EXPERIMENTS_OUT_DIR,
    _merged_dotenv,
    sanitize_error_message,
    utc_timestamp,
    write_experiment_json,
)
from src.account.public_api import (
    AvailabilityQueryPort,
    AvailabilitySnapshotDTO,
    LearnerProfileDTO,
    LearnerProfileQueryPort,
    QuotaFacadePort,
)
from src.execution.public_api import ExecutionScheduleSyncPort, ExistingScheduledTaskDTO
from src.planning.application.ports.planning_repository_ports import (
    GoalRepositoryPort,
    MilestoneRepositoryPort,
    RoadmapRepositoryPort,
    ScheduleProposalRepositoryPort,
)
from src.planning.application.services.validation_gate.orchestrator import (
    ProposalValidationGateOrchestrator,
)
from src.planning.application.use_cases.milestone_use_cases import (
    ApproveMilestonesUseCase,
    ExecuteMilestoneGenerationUseCase,
)
from src.planning.application.use_cases.proposal_generation_use_cases import (
    ExecuteScheduleProposalGenerationUseCase,
    InitiateScheduleProposalGenerationUseCase,
)
from src.planning.domain.exceptions.planning_exceptions import (
    ScopeApprovalRequiredError,
)
from src.planning.domain.models.goal import Goal, GoalStatus
from src.planning.domain.models.milestone import Milestone
from src.planning.domain.models.roadmap import Roadmap, RoadmapStatus
from src.planning.domain.models.schedule import ScheduleProposal, ScheduleProposalStatus
from src.planning.domain.services.milestone_effort_allocator import (
    MilestoneEffortAllocator,
)
from src.planning.domain.services.spatio_temporal_engine import (
    NonSplittableTaskClassifier,
    SpatioTemporalRuleEngine,
)
from src.planning.domain.services.validation_types import (
    AvailabilityConfigurationDTO,
    AvailabilitySlotDTO,
)
from src.shared_kernel.application.uow import AsyncUnitOfWork
from src.shared_kernel.config import get_settings
from src.shared_kernel.domain.base import generate_uuid7
from src.shared_kernel.infrastructure.external_ai.litellm_adapter import (
    LiteLLMAdapter,
    clear_cobhub_capability_probe_cache,
)
from src.shared_kernel.infrastructure.sse.job_store import InMemorySseJobStore
from tests.ai_evals.eval_runner import (
    DEFAULT_18_GOALS_DATASET_PATH,
    HARD_6_GOALS_DATASET_PATH,
    run_planning_eval_suite,
    validate_eval_report_totals,
)
from tests.helpers.llm_stubs import StubLLMAdapter

OUTPUT_FILENAME = "exp_13_deterministic_ab_results.json"
EXP09_PATH = EXPERIMENTS_OUT_DIR / "exp_09_judge_and_quality_ab.json"
KEY10_PATH = EXPERIMENTS_OUT_DIR / "blind_review_10_roadmaps_key.json"
EXP10_PATH = EXPERIMENTS_OUT_DIR / "exp_10_planner_tool_rounds_ab.json"
KEY12_PATH = EXPERIMENTS_OUT_DIR / "blind_review_hard_6_milestones_key.json"


# ---------------------------------------------------------------------------
# Shared Helpers for Cohort A & Cohort C
# ---------------------------------------------------------------------------
def _strip_schedule_fields(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            k: v
            for k, v in t.items()
            if k not in ("scheduled_date", "scheduled_start", "scheduled_end")
        }
        for t in tasks
    ]


def _goal_constraints(
    goal_key: str,
) -> tuple[date, date, int, AvailabilityConfigurationDTO]:
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
    raise ValueError(f"Unsupported goal_key {goal_key}")


def _to_avail_cfg(avail_dict: dict[str, Any]) -> AvailabilityConfigurationDTO:
    return AvailabilityConfigurationDTO(
        mode=str(avail_dict["mode"]),
        default_daily_quota_minutes=int(avail_dict["default_daily_quota_minutes"]),
        daily_quota_minutes=dict(avail_dict.get("daily_quota_minutes") or {}),
        availability_slots=tuple(
            AvailabilitySlotDTO(**s)
            for s in (avail_dict.get("availability_slots") or [])
        ),
        disabled_weekdays=frozenset(avail_dict.get("disabled_weekdays") or []),
    )


def _evaluate_schedule_arm(
    *,
    tasks_in: list[dict[str, Any]],
    deps: list[dict[str, Any]],
    avail: AvailabilityConfigurationDTO,
    start_date: date,
    target_date: date,
    preferred_session_minutes: int,
    arm: Literal["control", "treatment"],
    existing_tasks: list[dict[str, Any]] | tuple[dict[str, Any], ...] = (),
) -> dict[str, Any]:
    orig_efforts = {
        str(t.get("task_id") or t.get("id")): int(t.get("estimated_minutes", 0) or 0)
        for t in tasks_in
    }
    if arm == "control":
        out_tasks, out_blocks = SpatioTemporalRuleEngine.allocate_task_sessions(
            tasks_in,
            avail,
            start_date=start_date,
            target_date=target_date,
            dependencies=deps,
            existing_tasks=existing_tasks,
            preferred_session_minutes=preferred_session_minutes,
            hard_solver_v2_enabled=False,
            soft_pacing_v2_enabled=False,
        )
        unplaced_count = sum(1 for t in out_tasks if t.get("scheduled_date") is None)
        verdict = "VERIFIED_FEASIBLE" if unplaced_count == 0 else "LEGACY_UNPLACED"
        unsched_codes: list[str] = []
    else:
        alloc_res = SpatioTemporalRuleEngine.allocate_task_sessions_with_diagnostics(
            tasks_in,
            avail,
            start_date=start_date,
            target_date=target_date,
            dependencies=deps,
            existing_tasks=existing_tasks,
            preferred_session_minutes=preferred_session_minutes,
            soft_pacing_v2_enabled=True,
        )
        out_tasks = alloc_res.tasks
        out_blocks = alloc_res.schedule_blocks
        verdict = alloc_res.feasibility_verdict
        unsched_codes = [d.reason_code for d in alloc_res.unscheduled_diagnostics]

    proposal = {"tasks": out_tasks, "schedule_blocks": out_blocks, "dependencies": deps}
    v1 = ProposalValidationGateOrchestrator.run_tier1_gate(
        proposal, is_ai_generated=True
    )
    v2, w2 = ProposalValidationGateOrchestrator.run_tier2_gate(
        proposal,
        availability=avail,
        existing_tasks=existing_tasks,
        current_roadmap_target_date=target_date,
    )
    hard_violations = [v.rule_code for v in [*v1, *v2]]

    dates = sorted({date.fromisoformat(str(b["block_date"])[:10]) for b in out_blocks})
    max_streak = SpatioTemporalRuleEngine._max_consecutive_study_days(out_blocks)
    cross_day_tasks, cross_day_spans = SpatioTemporalRuleEngine._count_cross_day_splits(
        out_blocks
    )
    adj_splits = SpatioTemporalRuleEngine._count_adjacent_same_day_splits(out_blocks)
    idle_before_deadline = (target_date - dates[-1]).days if dates else None

    dates_by_task: dict[str, set[str]] = {}
    for b in out_blocks:
        dates_by_task.setdefault(str(b["task_id"]), set()).add(
            str(b["block_date"])[:10]
        )
    sensitive_cross_day = 0
    for t in out_tasks:
        tid = str(t.get("task_id") or t.get("id"))
        if (
            NonSplittableTaskClassifier.is_non_splittable(t)
            and len(dates_by_task.get(tid, set())) > 1
        ):
            sensitive_cross_day += 1

    placed_count = sum(1 for t in out_tasks if t.get("scheduled_date") is not None)
    sub_30m_blocks = sum(
        1 for b in out_blocks if int(b.get("scheduled_duration_minutes", 0) or 0) < 30
    )
    mutated_count = sum(
        1
        for t in out_tasks
        if int(t.get("estimated_minutes", 0) or 0)
        != orig_efforts.get(str(t.get("task_id") or t.get("id")), -1)
    )

    return {
        "passed_hard_gates": len(hard_violations) == 0
        and placed_count == len(tasks_in),
        "placed_tasks": placed_count,
        "total_tasks": len(tasks_in),
        "placement_rate": round(placed_count / max(1, len(tasks_in)), 4),
        "blocks_count": len(out_blocks),
        "adjacent_same_day_split_count": adj_splits,
        "sensitive_tasks_split_across_days": sensitive_cross_day,
        "max_consecutive_study_days": max_streak,
        "days_idle_before_deadline": idle_before_deadline,
        "cross_day_tasks": cross_day_tasks,
        "cross_day_spans": cross_day_spans,
        "sub_30m_blocks_count": sub_30m_blocks,
        "estimated_minutes_mutated_count": mutated_count,
        "feasibility_verdict": verdict,
        "unscheduled_reason_codes": unsched_codes,
        "hard_violations_count": len(hard_violations),
        "hard_violation_codes": hard_violations,
        "soft_overflow_warnings_count": len(w2),
    }


# ---------------------------------------------------------------------------
# Cohort A: Frozen Deterministic Replay
# ---------------------------------------------------------------------------
def run_cohort_a_frozen_replay() -> dict[str, Any]:
    print(
        "\n=== [Cohort A] Frozen Deterministic Replay (Control vs Treatment) ===",
        flush=True,
    )
    exp09 = json.loads(EXP09_PATH.read_text(encoding="utf-8"))
    key10 = json.loads(KEY10_PATH.read_text(encoding="utf-8"))["mapping"]
    exp10 = json.loads(EXP10_PATH.read_text(encoding="utf-8"))
    key12 = json.loads(KEY12_PATH.read_text(encoding="utf-8"))["mapping"]
    hard_ds = {
        obj["scenario_id"]: obj
        for line in HARD_6_GOALS_DATASET_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
        for obj in [json.loads(line)]
    }

    # 1. R-01..R-10 replay
    r_rows: list[dict[str, Any]] = []
    for label, meta in key10.items():
        rm = next(
            r
            for r in exp09["part_3_quality_ab_low_vs_medium"]["roadmaps"]
            if r["goal_key"] == meta["goal_id"] and r["arm"] == meta["arm"]
        )
        sd, td, pref, avail = _goal_constraints(meta["goal_id"])
        tasks_in = _strip_schedule_fields(rm["decomposer"]["proposal"]["tasks"])
        deps = rm["decomposer"]["proposal"]["dependencies"]

        ctrl = _evaluate_schedule_arm(
            tasks_in=tasks_in,
            deps=deps,
            avail=avail,
            start_date=sd,
            target_date=td,
            preferred_session_minutes=pref,
            arm="control",
        )
        trt = _evaluate_schedule_arm(
            tasks_in=tasks_in,
            deps=deps,
            avail=avail,
            start_date=sd,
            target_date=td,
            preferred_session_minutes=pref,
            arm="treatment",
        )
        r_rows.append(
            {
                "label": label,
                "goal_id": meta["goal_id"],
                "arm": meta["arm"],
                "tasks_count": len(tasks_in),
                "control": ctrl,
                "treatment": trt,
            }
        )

    # Also record R-08 with 120m weekend slot (demonstrating valid feasible pacing once NC-2 120m slot exists)
    rm08 = next(
        r
        for r in exp09["part_3_quality_ab_low_vs_medium"]["roadmaps"]
        if r["goal_key"] == key10["R-08"]["goal_id"]
        and r["arm"] == key10["R-08"]["arm"]
    )
    sd08, td08, pref08, _ = _goal_constraints("G4_BEGINNER_IELTS_WRITING")
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
    r08_120m = {
        "label": "R-08_weekend_120m",
        "control": _evaluate_schedule_arm(
            tasks_in=_strip_schedule_fields(rm08["decomposer"]["proposal"]["tasks"]),
            deps=rm08["decomposer"]["proposal"]["dependencies"],
            avail=avail_g4_120,
            start_date=sd08,
            target_date=td08,
            preferred_session_minutes=pref08,
            arm="control",
        ),
        "treatment": _evaluate_schedule_arm(
            tasks_in=_strip_schedule_fields(rm08["decomposer"]["proposal"]["tasks"]),
            deps=rm08["decomposer"]["proposal"]["dependencies"],
            avail=avail_g4_120,
            start_date=sd08,
            target_date=td08,
            preferred_session_minutes=pref08,
            arm="treatment",
        ),
    }

    def _agg_r(side: Literal["control", "treatment"]) -> dict[str, Any]:
        items = [row[side] for row in r_rows]
        n = len(items)
        return {
            "pass_count": sum(1 for x in items if x["passed_hard_gates"]),
            "pass_rate": round(
                sum(1 for x in items if x["passed_hard_gates"]) / max(1, n), 4
            ),
            "adjacent_same_day_split_total": sum(
                x["adjacent_same_day_split_count"] for x in items
            ),
            "sensitive_tasks_split_across_days_total": sum(
                x["sensitive_tasks_split_across_days"] for x in items
            ),
            "max_consecutive_study_days_max": max(
                x["max_consecutive_study_days"] for x in items
            ),
            "cross_day_tasks_total": sum(x["cross_day_tasks"] for x in items),
            "hard_violations_total": sum(x["hard_violations_count"] for x in items),
            "days_idle_before_deadline_avg": round(
                sum(x["days_idle_before_deadline"] or 0 for x in items) / max(1, n), 2
            ),
            "verdicts": {
                row["label"]: row[side]["feasibility_verdict"] for row in r_rows
            },
        }

    # 2. M-01..M-12 replay
    scenarios_10 = {s["scenario_id"]: s for s in exp10["scenarios"]}
    m_rows: list[dict[str, Any]] = []
    for label, meta in key12.items():
        sid = meta["scenario_id"]
        arm_name = meta["arm"]
        ds_item = hard_ds[sid]
        cfg = _to_avail_cfg(ds_item["availability"])
        s_date = date.fromisoformat(ds_item["start_date"])
        t_date = date.fromisoformat(ds_item["target_date"])
        p_hard, _ = SpatioTemporalRuleEngine.calculate_hard_packable_capacity(
            cfg, start_date=s_date, target_date=t_date
        )
        raw_ms = scenarios_10[sid][arm_name]["milestones"]
        raw_efforts = [int(m.get("estimated_effort_minutes", 0) or 0) for m in raw_ms]
        raw_sum = sum(raw_efforts)
        raw_equal = len(set(raw_efforts)) <= 1 and len(raw_efforts) > 1

        alloc = MilestoneEffortAllocator.allocate(
            raw_ms,
            hard_packable_capacity_minutes=p_hard,
            prior_knowledge_level=ds_item["learner_level"],
            start_date=s_date,
            target_date=t_date,
            availability=cfg,
        )
        norm_efforts = [b.normalized_planned_effort_minutes for b in alloc.breakdowns]
        norm_equal = len(set(norm_efforts)) <= 1 and len(norm_efforts) > 1

        m_rows.append(
            {
                "label": label,
                "scenario_id": sid,
                "arm": arm_name,
                "hard_packable_capacity_minutes": p_hard,
                "control": {
                    "all_efforts_equal": raw_equal,
                    "efforts": raw_efforts,
                    "total_minutes": raw_sum,
                    "raw_utilization": round(raw_sum / p_hard, 4),
                    "exceeds_hard_capacity": raw_sum > p_hard,
                    "preliminary_status": "UNASSESSED_LEGACY",
                },
                "treatment": {
                    "all_efforts_equal": norm_equal,
                    "efforts": norm_efforts,
                    "llm_estimated_total_minutes": alloc.llm_estimated_total_minutes,
                    "minimum_defensible_total_minutes": alloc.minimum_defensible_total_minutes,
                    "normalized_planned_effort_minutes": alloc.normalized_planned_total_minutes,
                    "normalized_utilization": round(
                        alloc.normalized_planned_total_minutes / p_hard, 4
                    ),
                    "exceeds_hard_capacity": alloc.normalized_planned_total_minutes
                    > p_hard,
                    "preliminary_status": alloc.status,
                    "requires_learner_approval": alloc.requires_learner_approval,
                },
            }
        )

    # M-12 tight-cap FIT_CAPACITY sensitivity
    m12_meta = key12["M-12"]
    m12_ds = hard_ds[m12_meta["scenario_id"]]
    m12_cfg = _to_avail_cfg(m12_ds["availability"])
    m12_s = date.fromisoformat(m12_ds["start_date"])
    m12_t = date.fromisoformat(m12_ds["target_date"])
    m12_ms = scenarios_10[m12_meta["scenario_id"]][m12_meta["arm"]]["milestones"]
    m12_tight = MilestoneEffortAllocator.allocate(
        m12_ms,
        hard_packable_capacity_minutes=780,
        prior_knowledge_level=m12_ds["learner_level"],
        start_date=m12_s,
        target_date=m12_s + (m12_t - m12_s) // 4,
        availability=m12_cfg,
    )

    # 3. G4 / G5 attempt-1 placement vs legacy divmod
    avail_g5 = _goal_constraints("G5_INTERMEDIATE_DATA_ENG_AIRFLOW_DBT")[3]
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
    g5_control = _evaluate_schedule_arm(
        tasks_in=g5_tasks,
        deps=[],
        avail=avail_g5,
        start_date=date(2026, 11, 17),
        target_date=date(2026, 12, 22),
        preferred_session_minutes=60,
        arm="control",
    )
    g5_treatment = _evaluate_schedule_arm(
        tasks_in=g5_tasks,
        deps=[],
        avail=avail_g5,
        start_date=date(2026, 11, 17),
        target_date=date(2026, 12, 22),
        preferred_session_minutes=60,
        arm="treatment",
    )

    avail_g4 = _goal_constraints("G4_BEGINNER_IELTS_WRITING")[3]
    g4_tasks = [
        {**t, "is_non_splittable": False}
        for t in _strip_schedule_fields(rm08["decomposer"]["proposal"]["tasks"])
    ]
    g4_deps = rm08["decomposer"]["proposal"]["dependencies"]
    g4_control = _evaluate_schedule_arm(
        tasks_in=g4_tasks,
        deps=g4_deps,
        avail=avail_g4,
        start_date=date(2026, 11, 17),
        target_date=date(2026, 12, 31),
        preferred_session_minutes=60,
        arm="control",
    )
    g4_treatment = _evaluate_schedule_arm(
        tasks_in=g4_tasks,
        deps=g4_deps,
        avail=avail_g4,
        start_date=date(2026, 11, 17),
        target_date=date(2026, 12, 31),
        preferred_session_minutes=60,
        arm="treatment",
    )

    return {
        "r01_to_r10": {
            "summary": {
                "control": _agg_r("control"),
                "treatment": _agg_r("treatment"),
            },
            "per_roadmap": r_rows,
            "r08_weekend_120m_sensitivity": r08_120m,
        },
        "m01_to_m12": {
            "source_note": (
                "Replayed from docs/experiments/exp_10_planner_tool_rounds_ab.json + "
                "docs/experiments/blind_review_hard_6_milestones_key.json "
                "(docs/experiments/blind_review_10/milestones_12.json is not present in repo)."
            ),
            "summary": {
                "control": {
                    "all_efforts_equal_count": sum(
                        1 for r in m_rows if r["control"]["all_efforts_equal"]
                    ),
                    "exceeds_hard_capacity_count": sum(
                        1 for r in m_rows if r["control"]["exceeds_hard_capacity"]
                    ),
                },
                "treatment": {
                    "all_efforts_equal_count": sum(
                        1 for r in m_rows if r["treatment"]["all_efforts_equal"]
                    ),
                    "exceeds_hard_capacity_count": sum(
                        1 for r in m_rows if r["treatment"]["exceeds_hard_capacity"]
                    ),
                    "full_scope_feasible_count": sum(
                        1
                        for r in m_rows
                        if r["treatment"]["preliminary_status"] == "FULL_SCOPE_FEASIBLE"
                    ),
                },
            },
            "per_plan": m_rows,
            "m12_tight_cap_780m_fit_capacity": {
                "status": m12_tight.status,
                "scope_proposal_version": m12_tight.scope_proposal_version,
                "requires_learner_approval": m12_tight.requires_learner_approval,
                "kept_scope_count": len(m12_tight.kept_scope),
                "deferred_scope_count": len(m12_tight.deferred_scope),
                "normalized_planned_total_minutes": m12_tight.normalized_planned_total_minutes,
            },
        },
        "g4_g5_attempt_1": {
            "G5_1980m_in_2250m": {"control": g5_control, "treatment": g5_treatment},
            "G4_2460m_in_3060m": {"control": g4_control, "treatment": g4_treatment},
        },
    }


# ---------------------------------------------------------------------------
# Cohort B: Live E2E via CofHub
# ---------------------------------------------------------------------------
def _resolve_cobhub_credentials() -> tuple[str, str]:
    dotenv_map = _merged_dotenv()
    base_url = (
        os.getenv("LLM_BASE_URL") or dotenv_map.get("LLM_BASE_URL") or ""
    ).strip()
    api_key = (
        os.getenv("LLM_API_KEY")
        or os.getenv("LLM_KEY")
        or dotenv_map.get("LLM_API_KEY")
        or dotenv_map.get("LLM_KEY")
        or ""
    ).strip()
    return base_url, api_key


def probe_cobhub_health() -> dict[str, Any]:
    base_url, api_key = _resolve_cobhub_credentials()
    if not base_url:
        return {"reachable": False, "reason": "Missing LLM_BASE_URL", "base_url": None}
    if not api_key:
        return {
            "reachable": False,
            "reason": "Missing LLM_API_KEY",
            "base_url": base_url,
        }

    url = f"{base_url.rstrip('/')}/v1beta/models"
    t0 = time.perf_counter()
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            status = int(resp.status)
            body = resp.read().decode("utf-8", "ignore")
            parsed = json.loads(body) if body.strip() else {}
            models_count = (
                len(parsed.get("models", [])) if isinstance(parsed, dict) else 0
            )
            return {
                "reachable": status == 200,
                "status_code": status,
                "base_url": base_url,
                "probe_url": url,
                "latency_ms": round((time.perf_counter() - t0) * 1000.0, 2),
                "models_count": models_count,
            }
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
        return {
            "reachable": False,
            "base_url": base_url,
            "probe_url": url,
            "latency_ms": round((time.perf_counter() - t0) * 1000.0, 2),
            "error": sanitize_error_message(exc),
        }


def _configure_live_arm_env(
    base_url: str,
    api_key: str,
    *,
    arm: Literal["control", "treatment"],
) -> dict[str, Any]:
    os.environ["ENVIRONMENT"] = "development"
    os.environ["LLM_PROVIDER"] = "gemini"
    os.environ["LLM_BASE_URL"] = base_url
    os.environ["LLM_API_KEY"] = api_key
    os.environ["LLM_THINKING_CONTROL"] = "model_suffix"
    os.environ["LLM_MODEL"] = "gemini-3.8-flash-medium"
    os.environ["LLM_MODEL_LOW"] = "gemini-3.8-flash-low"
    os.environ["LLM_MODEL_MEDIUM"] = "gemini-3.8-flash-medium"
    os.environ["LLM_MODEL_HIGH"] = "gemini-3.8-flash-high"

    os.environ["AI_HARD_TIMEOUT_SECONDS"] = "55.0"
    os.environ["AI_SSE_PIPELINE_TIMEOUT_SECONDS"] = "55.0"
    os.environ["AI_CLARIFIER_TIMEOUT_SECONDS"] = "15.0"
    os.environ["AI_MILESTONE_PLANNER_TIMEOUT_SECONDS"] = "50.0"
    os.environ["AI_TOOL_CALL_TIMEOUT_SECONDS"] = "40.0"
    os.environ["AI_QUALITY_CRITIC_TIMEOUT_SECONDS"] = "15.0"
    os.environ["AI_QUALITY_ARBITER_TIMEOUT_SECONDS"] = "14.5"
    os.environ["TIER3_JUDGE_TIMEOUT_SECONDS"] = "12.0"
    os.environ["AI_MIN_CRITIC_REMAINING_SECONDS"] = "6.0"
    os.environ["AI_MIN_JUDGE_REMAINING_SECONDS"] = "3.0"
    os.environ["AI_MIN_RETRY_REMAINING_SECONDS"] = "12.0"

    if arm == "control":
        os.environ["SPATIO_TEMPORAL_V2_HARD_SOLVER_ENABLED"] = "false"
        os.environ["SPATIO_TEMPORAL_V2_SOFT_PACING_ENABLED"] = "false"
        os.environ["MILESTONE_EFFORT_ALLOCATOR_ENABLED"] = "false"
        os.environ["AI_TASK_DECOMPOSER_TIMEOUT_SECONDS"] = "25.0"
    else:
        os.environ["SPATIO_TEMPORAL_V2_HARD_SOLVER_ENABLED"] = "true"
        os.environ["SPATIO_TEMPORAL_V2_SOFT_PACING_ENABLED"] = "true"
        os.environ["MILESTONE_EFFORT_ALLOCATOR_ENABLED"] = "true"
        os.environ["AI_TASK_DECOMPOSER_TIMEOUT_SECONDS"] = "36.0"

    get_settings.cache_clear()
    clear_cobhub_capability_probe_cache()
    s = get_settings()
    return {
        "arm": arm,
        "spatio_temporal_v2_hard_solver_enabled": s.spatio_temporal_v2_hard_solver_enabled,
        "spatio_temporal_v2_soft_pacing_enabled": s.spatio_temporal_v2_soft_pacing_enabled,
        "milestone_effort_allocator_enabled": s.milestone_effort_allocator_enabled,
        "ai_task_decomposer_timeout_seconds": s.ai_task_decomposer_timeout_seconds,
        "ai_sse_pipeline_timeout_seconds": s.ai_sse_pipeline_timeout_seconds,
        "ai_min_retry_remaining_seconds": s.ai_min_retry_remaining_seconds,
    }


def _extract_cohort_b_summary(
    report: dict[str, Any], active_flags: dict[str, Any]
) -> dict[str, Any]:
    outcomes = report.get("per_case_outcomes", [])
    audits = [o.get("structural_audit", {}) for o in outcomes]
    with_prop = [a for a in audits if a.get("has_proposal")]
    return {
        "flags": active_flags,
        "dataset_size": report.get("dataset_size"),
        "total_runs": report.get("total_runs"),
        "passed_runs": report.get("passed_runs"),
        "failed_runs": report.get("failed_runs"),
        "pass_at_1": report.get("pass_at_1"),
        "pass_with_judge_verdict": report.get("pass_with_judge_verdict"),
        "avg_retries": report.get("avg_retries"),
        "structural_validity_pass_count": sum(
            1 for a in audits if a.get("structural_validity")
        ),
        "scheduling_feasibility_pass_count": sum(
            1 for a in audits if a.get("scheduling_feasibility")
        ),
        "soft_quality_score_avg": round(
            sum(
                float(
                    (a.get("pedagogical_quality") or {}).get("soft_quality_score")
                    or 0.0
                )
                for a in audits
            )
            / max(1, len(audits)),
            4,
        ),
        "adjacent_same_day_split_total": sum(
            int(a.get("adjacent_same_day_split_count") or 0) for a in with_prop
        ),
        "sensitive_tasks_split_across_days_total": sum(
            int(a.get("sensitive_tasks_split_across_days_count") or 0)
            for a in with_prop
        ),
        "max_consecutive_study_days_max": max(
            (int(a.get("max_consecutive_study_days") or 0) for a in with_prop),
            default=None,
        ),
        "all_efforts_equal_cases": (report.get("structural_audit_summary") or {}).get(
            "all_efforts_equal_cases"
        ),
        "pedagogical_score_avg": report.get("pedagogical_score_avg"),
        "judge_passed_count": report.get("judge_passed_count"),
        "weekly_llm_success_count": report.get("weekly_llm_success_count"),
        "weekly_fallbacks": report.get("weekly_fallbacks"),
        "injection_isolation_summary": report.get("injection_isolation_summary"),
        "error_breakdown": report.get("error_breakdown"),
        "stage_latency_stats": report.get("stage_latency_stats"),
        "prompt_tokens_total": report.get("prompt_tokens_total"),
        "output_tokens_total": report.get("output_tokens_total"),
        "thinking_tokens_total": report.get("thinking_tokens_total"),
    }


async def run_cohort_b_live(
    *,
    concurrency: int = 3,
    skip_golden_18: bool = False,
) -> dict[str, Any]:
    print("\n=== [Cohort B] Live E2E via CofHub (Control vs Treatment) ===", flush=True)
    probe = probe_cobhub_health()
    if not probe.get("reachable"):
        print(f"  Cobhub unreachable: {probe}", flush=True)
        return {
            "status": "BLOCKED_COBHUB_UNREACHABLE",
            "health_probe": probe,
            "hard_6_goals": None,
            "golden_18_goals": None,
        }

    base_url, api_key = _resolve_cobhub_credentials()
    out: dict[str, Any] = {
        "status": "EXECUTED",
        "health_probe": probe,
        "concurrency": concurrency,
    }

    # Verify gateway capability probe once
    _configure_live_arm_env(base_url, api_key, arm="treatment")
    cap_probe = await LiteLLMAdapter().probe_cobhub_capabilities(force=True)
    out["capability_probe"] = cap_probe.to_dict()

    datasets: list[tuple[str, Path]] = [("hard_6_goals", HARD_6_GOALS_DATASET_PATH)]
    if not skip_golden_18:
        datasets.append(("golden_18_goals", DEFAULT_18_GOALS_DATASET_PATH))

    for ds_key, ds_path in datasets:
        arm_reports: dict[str, Any] = {}
        for arm in ("control", "treatment"):
            arm_lit: Literal["control", "treatment"] = arm
            flags = _configure_live_arm_env(base_url, api_key, arm=arm_lit)
            print(
                f"  Running {ds_key} E2E arm={arm_lit} (concurrency={concurrency})...",
                flush=True,
            )
            t0 = time.perf_counter()
            report = await run_planning_eval_suite(
                dataset_path=ds_path,
                trials_per_goal=1,
                live=True,
                e2e=True,
                concurrency=concurrency,
                include_weekly=True,
                apply_milestone_effort_allocator=(arm_lit == "treatment"),
            )
            validate_eval_report_totals(report)
            wall_s = round(time.perf_counter() - t0, 2)
            summary = _extract_cohort_b_summary(report, flags)
            summary["wall_seconds"] = wall_s
            arm_reports[arm_lit] = {
                "summary": summary,
                "full_report": report,
            }
            print(
                f"    -> {ds_key}/{arm_lit} done in {wall_s}s: "
                f"passed={report['passed_runs']}/{report['total_runs']} "
                f"struct_ok={summary['structural_validity_pass_count']} "
                f"sched_ok={summary['scheduling_feasibility_pass_count']}",
                flush=True,
            )
        out[ds_key] = arm_reports

    # Restore Treatment defaults cleanly
    _configure_live_arm_env(base_url, api_key, arm="treatment")
    return out


# ---------------------------------------------------------------------------
# Cohort C: 8 Synthetic Edge-Case Scenarios (EC-1..EC-8)
# ---------------------------------------------------------------------------
class _FakeGoalRepo(GoalRepositoryPort):
    def __init__(self) -> None:
        self.items: dict[UUID, Goal] = {}

    async def save(self, goal: Goal) -> Goal:
        self.items[goal.id] = goal
        return goal

    async def get_by_id(self, goal_id: UUID) -> Goal | None:
        return self.items.get(goal_id)

    async def get_by_id_for_user(self, goal_id: UUID, user_id: UUID) -> Goal | None:
        g = self.items.get(goal_id)
        return g if g and g.user_id == user_id else None

    async def list_by_user_id(self, user_id: UUID) -> list[Goal]:
        return [g for g in self.items.values() if g.user_id == user_id]


class _FakeRoadmapRepo(RoadmapRepositoryPort):
    def __init__(self) -> None:
        self.items: dict[UUID, Roadmap] = {}

    async def save(self, roadmap: Roadmap) -> Roadmap:
        self.items[roadmap.id] = roadmap
        return roadmap

    async def get_by_id(self, roadmap_id: UUID) -> Roadmap | None:
        return self.items.get(roadmap_id)

    async def get_by_id_for_user(
        self, roadmap_id: UUID, user_id: UUID
    ) -> Roadmap | None:
        r = self.items.get(roadmap_id)
        return r if r and r.user_id == user_id else None

    async def list_by_user_id(
        self, user_id: UUID, *, status: str | None = None
    ) -> list[Roadmap]:
        return [
            r
            for r in self.items.values()
            if r.user_id == user_id and (status is None or r.status.value == status)
        ]

    async def count_active_by_user_id(
        self, user_id: UUID, *, exclude_roadmap_id: UUID | None = None
    ) -> int:
        return sum(
            1
            for r in self.items.values()
            if r.user_id == user_id
            and r.status == RoadmapStatus.ACTIVE
            and r.id != exclude_roadmap_id
        )


class _FakeMilestoneRepo(MilestoneRepositoryPort):
    def __init__(self) -> None:
        self.by_roadmap: dict[UUID, list[Milestone]] = {}

    async def save_many(self, roadmap_id: UUID, milestones: Any) -> list[Milestone]:
        self.by_roadmap[roadmap_id] = list(milestones)
        return sorted(self.by_roadmap[roadmap_id], key=lambda m: m.sequence_order)

    async def list_by_roadmap_id(self, roadmap_id: UUID) -> list[Milestone]:
        return sorted(
            self.by_roadmap.get(roadmap_id, []), key=lambda m: m.sequence_order
        )

    async def approve_all_for_roadmap(
        self, roadmap_id: UUID, now: datetime
    ) -> list[Milestone]:
        items = self.by_roadmap.get(roadmap_id, [])
        for m in items:
            m.approve(now)
        return sorted(items, key=lambda m: m.sequence_order)


class _FakeProposalRepo(ScheduleProposalRepositoryPort):
    def __init__(self) -> None:
        self.items: dict[UUID, ScheduleProposal] = {}

    async def save(self, proposal: ScheduleProposal) -> ScheduleProposal:
        self.items[proposal.id] = proposal
        return proposal

    async def get_by_id(self, proposal_id: UUID) -> ScheduleProposal | None:
        return self.items.get(proposal_id)

    async def get_current_draft(self, roadmap_id: UUID) -> ScheduleProposal | None:
        for p in self.items.values():
            if p.roadmap_id == roadmap_id and p.status == ScheduleProposalStatus.DRAFT:
                return p
        return None

    async def discard_existing_drafts(self, roadmap_id: UUID, now: datetime) -> int:
        cnt = 0
        for p in self.items.values():
            if p.roadmap_id == roadmap_id and p.status == ScheduleProposalStatus.DRAFT:
                p.discard(now)
                cnt += 1
        return cnt


class _FakeQuotaFacade(QuotaFacadePort):
    def __init__(self) -> None:
        self.reserved: list[UUID] = []
        self.committed: list[UUID] = []
        self.released: list[UUID] = []

    async def reserve_quota(
        self, *, user_id: UUID, operation_type: str, cost: int = 1
    ) -> UUID:
        del user_id, operation_type, cost
        rid = generate_uuid7()
        self.reserved.append(rid)
        return rid

    async def commit_reservation(
        self,
        reservation_id: UUID,
        *,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        model_name: str = "",
    ) -> None:
        del prompt_tokens, completion_tokens, model_name
        self.committed.append(reservation_id)

    async def release_reservation(
        self, reservation_id: UUID, *, reason: str = ""
    ) -> None:
        del reason
        self.released.append(reservation_id)


class _FakeUoW(AsyncUnitOfWork):
    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None

    def collect_events_from(self, aggregate: Any) -> None:
        del aggregate


class _FakeAvailabilityPort(AvailabilityQueryPort):
    def __init__(self, snapshot: AvailabilitySnapshotDTO) -> None:
        self._snapshot = snapshot

    async def get_active_availability(
        self, user_id: UUID
    ) -> AvailabilitySnapshotDTO | None:
        del user_id
        return self._snapshot


class _FakeLearnerProfilePort(LearnerProfileQueryPort):
    async def get_learner_profile(self, user_id: UUID) -> LearnerProfileDTO:
        return LearnerProfileDTO(
            user_id=user_id, opt_session_minutes=60, estimation_bias_beta=1.0
        )


class _FakeExecutionSyncPort(ExecutionScheduleSyncPort):
    async def get_tasks_for_roadmaps(
        self,
        roadmap_ids: Any,
        *,
        roadmap_target_dates: dict[UUID, date | None] | None = None,
    ) -> list[ExistingScheduledTaskDTO]:
        del roadmap_ids, roadmap_target_dates
        return []


async def _run_ec5_fit_capacity_lifecycle() -> dict[str, Any]:
    now = datetime(2026, 11, 2, 10, 0, tzinfo=UTC)
    user_id = generate_uuid7()
    goal = Goal(
        id=generate_uuid7(),
        user_id=user_id,
        title="Hệ thống Distributed Rust",
        raw_description="Xây dựng hệ phân tán",
        target_date=date(2026, 11, 15),
        prior_knowledge_level="INTERMEDIATE",
        status=GoalStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
    roadmap = Roadmap(
        id=generate_uuid7(),
        user_id=user_id,
        goal_id=goal.id,
        title="Distributed Rust 2 tuần",
        start_date=date(2026, 11, 2),
        target_date=date(2026, 11, 15),
        status=RoadmapStatus.INITIALIZED,
        created_at=now,
        updated_at=now,
    )
    goal_repo = _FakeGoalRepo()
    roadmap_repo = _FakeRoadmapRepo()
    milestone_repo = _FakeMilestoneRepo()
    proposal_repo = _FakeProposalRepo()
    quota = _FakeQuotaFacade()
    sse_store = InMemorySseJobStore()
    uow = _FakeUoW()
    await goal_repo.save(goal)
    await roadmap_repo.save(roadmap)

    avail_snapshot = AvailabilitySnapshotDTO(
        user_id=user_id,
        mode="MODE_B",
        daily_cap_minutes=120,
        weekly_capacity_minutes=120,
        daily_quota_minutes={},
        availability_slots=(
            {
                "day_of_week": "monday",
                "start_time": "19:00",
                "end_time": "21:00",
                "end_day_offset": 0,
                "is_active": True,
            },
        ),
        disabled_weekdays=(),
    )
    llm_milestones_payload = {
        "milestones": [
            {
                "sequence_order": 1,
                "title": "Nền tảng Rust Ownership & Async",
                "description": "Cài đặt async executor cơ bản",
                "learning_outcomes": ["Thiết lập async runtime", "Kiểm thử unit"],
                "completion_criteria": "Pass unit test async",
                "estimated_effort_minutes": 240,
                "required_concepts": [],
                "unverified_concepts": ["rust-async"],
                "dependencies": [],
            },
            {
                "sequence_order": 2,
                "title": "Giao thức gRPC & Streaming",
                "description": "Xây dựng server gRPC",
                "learning_outcomes": ["Cài đặt streaming RPC", "Kiểm thử tích hợp"],
                "completion_criteria": "gRPC server chạy ổn định",
                "estimated_effort_minutes": 240,
                "required_concepts": [],
                "unverified_concepts": ["tonic-grpc"],
                "dependencies": [1],
            },
            {
                "sequence_order": 3,
                "title": "Đồ án Raft Consensus Cluster",
                "description": "Xây dựng cụm Raft 3-node",
                "learning_outcomes": ["Triển khai leader election", "Chạy chaos test"],
                "completion_criteria": "Đồ án cụm 3-node vượt chaos test",
                "estimated_effort_minutes": 360,
                "required_concepts": [],
                "unverified_concepts": ["raft"],
                "dependencies": [2],
            },
        ],
        "scope_summary": "FULL_SCOPE",
        "deferred_scope": [],
    }

    ms_job_id = generate_uuid7()
    ms_res_id = await quota.reserve_quota(
        user_id=user_id, operation_type="MILESTONE_GEN"
    )
    await sse_store.create_job(
        job_id=ms_job_id,
        user_id=user_id,
        roadmap_id=roadmap.id,
        reservation_id=ms_res_id,
        job_type="MILESTONE_GEN",
        operation=f"MILESTONE_GEN:{roadmap.id}",
    )
    gen_ms_uc = ExecuteMilestoneGenerationUseCase(
        goal_repo=goal_repo,
        roadmap_repo=roadmap_repo,
        milestone_repo=milestone_repo,
        quota_facade=quota,
        llm_provider=StubLLMAdapter(canned_responses=[llm_milestones_payload]),
        sse_job_store=sse_store,
        uow=uow,
        availability_query_port=_FakeAvailabilityPort(avail_snapshot),
        execution_sync_port=_FakeExecutionSyncPort(),
    )
    await gen_ms_uc.execute(
        job_id=ms_job_id,
        user_id=user_id,
        roadmap_id=roadmap.id,
        reservation_id=ms_res_id,
        now=now,
    )

    stored_rm = await roadmap_repo.get_by_id(roadmap.id)
    assert stored_rm is not None
    prelim = stored_rm.planning_metadata["preliminary_feasibility"]
    assert isinstance(prelim, dict)

    approve_uc = ApproveMilestonesUseCase(
        roadmap_repo=roadmap_repo, milestone_repo=milestone_repo, uow=uow
    )
    rejected_missing = False
    try:
        await approve_uc.execute(user_id=user_id, roadmap_id=roadmap.id, now=now)
    except ScopeApprovalRequiredError:
        rejected_missing = True

    rejected_stale = False
    try:
        await approve_uc.execute(
            user_id=user_id,
            roadmap_id=roadmap.id,
            confirmed_scope_proposal_version=99,
            accept_fit_capacity=True,
            now=now,
        )
    except ScopeApprovalRequiredError:
        rejected_stale = True

    init_prop_uc = InitiateScheduleProposalGenerationUseCase(
        roadmap_repo=roadmap_repo,
        milestone_repo=milestone_repo,
        quota_facade=quota,
        sse_job_store=sse_store,
        uow=uow,
    )
    reserved_before = len(quota.reserved)
    decomposer_blocked_unconfirmed = False
    try:
        await init_prop_uc.execute(
            user_id=user_id, roadmap_id=roadmap.id, run_inline=False
        )
    except ScopeApprovalRequiredError:
        decomposer_blocked_unconfirmed = True
    zero_quota_consumed_on_block = len(quota.reserved) == reserved_before

    approved_ms = await approve_uc.execute(
        user_id=user_id,
        roadmap_id=roadmap.id,
        confirmed_scope_proposal_version=int(prelim["scope_proposal_version"]),
        accept_fit_capacity=True,
        now=now,
    )
    kept_orders = {int(item["sequence_order"]) for item in prelim["kept_scope"]}
    kept_ms = [m for m in approved_ms if m.sequence_order in kept_orders]
    decomposer_payload = {
        "tasks": [
            {
                "task_id": f"T{idx}",
                "milestone_id": str(m.id),
                "title": f"Thực hành {m.title}",
                "description": "Thực hành chuyên sâu",
                "task_type": "PRACTICE",
                "learning_objective": f"Nắm vững {m.title}",
                "completion_criteria": "Pass unit test",
                "resource_ids": [],
                "concept_ids": [],
                "covered_outcome_ids": [
                    f"M{m.sequence_order}-O{oi}"
                    for oi in range(1, len(m.learning_outcomes) + 1)
                ],
                "estimated_minutes": 60,
            }
            for idx, m in enumerate(kept_ms, start=1)
        ],
        "dependencies": [],
    }
    prop_ticket = await init_prop_uc.execute(
        user_id=user_id, roadmap_id=roadmap.id, run_inline=False
    )
    exec_prop_uc = ExecuteScheduleProposalGenerationUseCase(
        goal_repo=goal_repo,
        roadmap_repo=roadmap_repo,
        milestone_repo=milestone_repo,
        proposal_repo=proposal_repo,
        availability_query_port=_FakeAvailabilityPort(avail_snapshot),
        learner_profile_port=_FakeLearnerProfilePort(),
        execution_sync_port=_FakeExecutionSyncPort(),
        quota_facade=quota,
        llm_provider=StubLLMAdapter(canned_responses=[decomposer_payload]),
        sse_job_store=sse_store,
        uow=uow,
        enable_tier3_judge=False,
    )
    proposal = await exec_prop_uc.execute(
        job_id=prop_ticket.job_id,
        user_id=user_id,
        roadmap_id=roadmap.id,
        reservation_id=prop_ticket.reservation_id,
        now=now,
    )
    decomposed_mids = {str(t["milestone_id"]) for t in proposal.proposal_data["tasks"]}
    passed = bool(
        prelim["status"] == "FIT_CAPACITY_REQUIRES_APPROVAL"
        and rejected_missing
        and rejected_stale
        and decomposer_blocked_unconfirmed
        and zero_quota_consumed_on_block
        and decomposed_mids == {str(m.id) for m in kept_ms}
    )
    return {
        "scenario_id": "EC-5",
        "name": "Partial fit (FIT_CAPACITY_REQUIRES_APPROVAL) halts for versioned learner confirmation",
        "passed": passed,
        "treatment": {
            "preliminary_status": prelim["status"],
            "scope_proposal_version": prelim["scope_proposal_version"],
            "kept_scope_count": len(prelim["kept_scope"]),
            "deferred_scope_count": len(prelim["deferred_scope"]),
            "rejected_missing_version": rejected_missing,
            "rejected_stale_version": rejected_stale,
            "decomposer_blocked_before_approval": decomposer_blocked_unconfirmed,
            "zero_quota_consumed_on_block": zero_quota_consumed_on_block,
            "decomposed_only_kept_scope": decomposed_mids
            == {str(m.id) for m in kept_ms},
        },
        "control": {
            "note": "Legacy flow lacks MilestoneEffortAllocator and scope approval gating; attempts full 840m into 240m capacity.",
            "passed_hard_gates": False,
        },
    }


async def run_cohort_c_edge_cases() -> dict[str, Any]:
    print(
        "\n=== [Cohort C] 8 Synthetic Edge-Case Scenarios (EC-1..EC-8) ===", flush=True
    )
    # Ensure treatment settings are active for EC-5
    os.environ["MILESTONE_EFFORT_ALLOCATOR_ENABLED"] = "true"
    os.environ["SPATIO_TEMPORAL_V2_HARD_SOLVER_ENABLED"] = "true"
    os.environ["SPATIO_TEMPORAL_V2_SOFT_PACING_ENABLED"] = "true"
    get_settings.cache_clear()

    cases: list[dict[str, Any]] = []

    # EC-1: Tight deadline (~95% utilization) -> graceful Phase 2 relaxation to VERIFIED_FEASIBLE
    avail_60 = AvailabilityConfigurationDTO(
        mode="MODE_A", default_daily_quota_minutes=60
    )
    ec1_tasks = [
        {
            "task_id": f"T{i}",
            "milestone_id": "m1",
            "title": f"Task {i}",
            "estimated_minutes": 60,
        }
        for i in range(1, 20)
    ]
    ec1_deps = [
        {"predecessor_id": f"T{i}", "successor_id": f"T{i + 1}", "is_mandatory": True}
        for i in range(1, 19)
    ]
    ec1_ctrl = _evaluate_schedule_arm(
        tasks_in=ec1_tasks,
        deps=ec1_deps,
        avail=avail_60,
        start_date=date(2026, 11, 2),
        target_date=date(2026, 11, 21),
        preferred_session_minutes=60,
        arm="control",
    )
    ec1_trt = _evaluate_schedule_arm(
        tasks_in=ec1_tasks,
        deps=ec1_deps,
        avail=avail_60,
        start_date=date(2026, 11, 2),
        target_date=date(2026, 11, 21),
        preferred_session_minutes=60,
        arm="treatment",
    )
    cases.append(
        {
            "scenario_id": "EC-1",
            "name": "Tight deadline (~95% util) graceful Phase 2 relaxation",
            "passed": ec1_trt["passed_hard_gates"]
            and ec1_trt["feasibility_verdict"] == "VERIFIED_FEASIBLE",
            "control": ec1_ctrl,
            "treatment": ec1_trt,
        }
    )

    # EC-2: Sparse availability (MODE_B narrow days)
    avail_sparse = AvailabilityConfigurationDTO(
        mode="MODE_B",
        availability_slots=(
            AvailabilitySlotDTO("monday", "19:30", "20:30"),
            AvailabilitySlotDTO("wednesday", "19:30", "21:00"),
            AvailabilitySlotDTO("saturday", "09:00", "11:00"),
        ),
    )
    ec2_tasks = [
        {
            "task_id": "S1",
            "milestone_id": "m1",
            "title": "Bài 1",
            "estimated_minutes": 60,
        },
        {
            "task_id": "S2",
            "milestone_id": "m1",
            "title": "Bài 2",
            "estimated_minutes": 90,
        },
        {
            "task_id": "S3",
            "milestone_id": "m1",
            "title": "Bài 3",
            "estimated_minutes": 120,
        },
        {
            "task_id": "S4",
            "milestone_id": "m1",
            "title": "Bài 4",
            "estimated_minutes": 60,
        },
        {
            "task_id": "S5",
            "milestone_id": "m1",
            "title": "Bài 5",
            "estimated_minutes": 90,
        },
        {
            "task_id": "S6",
            "milestone_id": "m1",
            "title": "Bài 6",
            "estimated_minutes": 120,
        },
    ]
    ec2_ctrl = _evaluate_schedule_arm(
        tasks_in=ec2_tasks,
        deps=[],
        avail=avail_sparse,
        start_date=date(2026, 11, 2),
        target_date=date(2026, 11, 21),
        preferred_session_minutes=60,
        arm="control",
    )
    ec2_trt = _evaluate_schedule_arm(
        tasks_in=ec2_tasks,
        deps=[],
        avail=avail_sparse,
        start_date=date(2026, 11, 2),
        target_date=date(2026, 11, 21),
        preferred_session_minutes=60,
        arm="treatment",
    )
    cases.append(
        {
            "scenario_id": "EC-2",
            "name": "Sparse availability (MODE_B narrow slots)",
            "passed": ec2_trt["passed_hard_gates"]
            and ec2_trt["adjacent_same_day_split_count"] == 0,
            "control": ec2_ctrl,
            "treatment": ec2_trt,
        }
    )

    # EC-3: Calendar conflicts (existing_tasks occupying middle of Saturday 180m slot) -> slot-boundary split without <30m slivers or mutation
    avail_conflict = AvailabilityConfigurationDTO(
        mode="MODE_B",
        availability_slots=(
            AvailabilitySlotDTO("saturday", "09:00", "12:00"),
            AvailabilitySlotDTO("monday", "19:00", "21:00"),
        ),
    )
    existing_conflict = [
        {
            "status": "TODO",
            "scheduled_date": "2026-11-07",
            "scheduled_start": "2026-11-07T10:00:00+00:00",
            "scheduled_end": "2026-11-07T11:00:00+00:00",
            "estimated_minutes": 60,
        }
    ]
    ec3_tasks = [
        {
            "task_id": "C1",
            "milestone_id": "m1",
            "title": "Lab 1",
            "estimated_minutes": 120,
        },
        {
            "task_id": "C2",
            "milestone_id": "m1",
            "title": "Lab 2",
            "estimated_minutes": 90,
        },
    ]
    ec3_ctrl = _evaluate_schedule_arm(
        tasks_in=ec3_tasks,
        deps=[],
        avail=avail_conflict,
        start_date=date(2026, 11, 7),
        target_date=date(2026, 11, 9),
        preferred_session_minutes=60,
        arm="control",
        existing_tasks=existing_conflict,
    )
    ec3_trt = _evaluate_schedule_arm(
        tasks_in=ec3_tasks,
        deps=[],
        avail=avail_conflict,
        start_date=date(2026, 11, 7),
        target_date=date(2026, 11, 9),
        preferred_session_minutes=60,
        arm="treatment",
        existing_tasks=existing_conflict,
    )
    cases.append(
        {
            "scenario_id": "EC-3",
            "name": "Calendar conflicts (existing_tasks partial slot) without <30m slivers or mutation",
            "passed": ec3_trt["passed_hard_gates"]
            and ec3_trt["sub_30m_blocks_count"] == 0
            and ec3_trt["estimated_minutes_mutated_count"] == 0,
            "control": ec3_ctrl,
            "treatment": ec3_trt,
        }
    )

    # EC-4: Impossible goal -> NC-1/NC-2/NC-3 EXPLICIT_UNSCHEDULABLE + Milestone PRELIMINARY_UNSCHEDULABLE
    avail_120 = AvailabilityConfigurationDTO(
        mode="MODE_B",
        availability_slots=(AvailabilitySlotDTO("monday", "19:00", "21:00"),),
    )
    nc1_res = SpatioTemporalRuleEngine.allocate_task_sessions_with_diagnostics(
        [
            {"task_id": "t1", "title": "Task 1", "estimated_minutes": 120},
            {"task_id": "t2", "title": "Task 2", "estimated_minutes": 60},
        ],
        avail_120,
        start_date=date(2026, 11, 2),
        target_date=date(2026, 11, 2),
    )
    avail_90 = AvailabilityConfigurationDTO(
        mode="MODE_B",
        availability_slots=(AvailabilitySlotDTO("monday", "19:30", "21:00"),),
    )
    nc2_res = SpatioTemporalRuleEngine.allocate_task_sessions_with_diagnostics(
        [
            {
                "task_id": "t_exam",
                "title": "Thi thử Mock Test 120p",
                "estimated_minutes": 120,
            }
        ],
        avail_90,
        start_date=date(2026, 11, 2),
        target_date=date(2026, 11, 8),
    )
    nc3_res = SpatioTemporalRuleEngine.allocate_task_sessions_with_diagnostics(
        [
            {
                "task_id": "p1",
                "title": "Root",
                "estimated_minutes": 60,
                "scheduled_date": "2026-11-05",
            },
            {"task_id": "p2", "title": "Step 2", "estimated_minutes": 60},
            {"task_id": "p3", "title": "Step 3", "estimated_minutes": 60},
        ],
        AvailabilityConfigurationDTO(mode="MODE_A", default_daily_quota_minutes=60),
        start_date=date(2026, 11, 2),
        target_date=date(2026, 11, 5),
        dependencies=[
            {"predecessor_id": "p1", "successor_id": "p2", "is_mandatory": True},
            {"predecessor_id": "p2", "successor_id": "p3", "is_mandatory": True},
        ],
    )
    prelim_unsched = MilestoneEffortAllocator.allocate(
        [
            {
                "sequence_order": 1,
                "title": "Nền tảng",
                "learning_outcomes": ["O1", "O2"],
                "completion_criteria": "Đồ án",
                "estimated_effort_minutes": 300,
                "dependencies": [],
            }
        ],
        hard_packable_capacity_minutes=20,
        prior_knowledge_level="BEGINNER",
    )
    ec4_passed = bool(
        nc1_res.feasibility_verdict == "EXPLICIT_UNSCHEDULABLE"
        and nc1_res.unscheduled_diagnostics[0].reason_code
        == "TOTAL_EFFORT_EXCEEDS_HARD_CAPACITY"
        and nc2_res.feasibility_verdict == "EXPLICIT_UNSCHEDULABLE"
        and nc2_res.unscheduled_diagnostics[0].reason_code
        == "TASK_EXCEEDS_CONTINUOUS_SLOT"
        and nc3_res.feasibility_verdict == "EXPLICIT_UNSCHEDULABLE"
        and any(
            d.reason_code == "CRITICAL_PATH_EXCEEDS_WINDOW"
            for d in nc3_res.unscheduled_diagnostics
        )
        and prelim_unsched.status == "PRELIMINARY_UNSCHEDULABLE"
        and prelim_unsched.adjustment_options["is_approximate"] is True
    )
    cases.append(
        {
            "scenario_id": "EC-4",
            "name": "Impossible goal (NC-1/NC-2/NC-3 -> EXPLICIT_UNSCHEDULABLE + PRELIMINARY_UNSCHEDULABLE)",
            "passed": ec4_passed,
            "control": {
                "note": "Legacy silently drops tasks (scheduled_date=None) without mathematical NC proof.",
            },
            "treatment": {
                "nc1_verdict": nc1_res.feasibility_verdict,
                "nc1_reason": nc1_res.unscheduled_diagnostics[0].reason_code,
                "nc2_verdict": nc2_res.feasibility_verdict,
                "nc2_reason": nc2_res.unscheduled_diagnostics[0].reason_code,
                "nc3_verdict": nc3_res.feasibility_verdict,
                "nc3_reasons": [d.reason_code for d in nc3_res.unscheduled_diagnostics],
                "preliminary_status": prelim_unsched.status,
                "adjustment_is_approximate": prelim_unsched.adjustment_options[
                    "is_approximate"
                ],
            },
        }
    )

    # EC-5: Partial fit -> versioned FIT_CAPACITY_REQUIRES_APPROVAL
    cases.append(await _run_ec5_fit_capacity_lifecycle())

    # EC-6: Non-splittable 120m mock test in 90m slot vs 120m slot
    mock_task = [
        {
            "task_id": "MOCK1",
            "milestone_id": "m1",
            "title": "Thi thử Mock Test 120m",
            "estimated_minutes": 120,
        }
    ]
    avail_90_multi = AvailabilityConfigurationDTO(
        mode="MODE_B",
        availability_slots=(
            AvailabilitySlotDTO("monday", "19:30", "21:00"),
            AvailabilitySlotDTO("wednesday", "19:30", "21:00"),
        ),
    )
    avail_120_slot = AvailabilityConfigurationDTO(
        mode="MODE_B",
        availability_slots=(AvailabilitySlotDTO("saturday", "09:00", "11:00"),),
    )
    ec6_90_ctrl = _evaluate_schedule_arm(
        tasks_in=mock_task,
        deps=[],
        avail=avail_90_multi,
        start_date=date(2026, 11, 2),
        target_date=date(2026, 11, 8),
        preferred_session_minutes=60,
        arm="control",
    )
    ec6_90_trt = _evaluate_schedule_arm(
        tasks_in=mock_task,
        deps=[],
        avail=avail_90_multi,
        start_date=date(2026, 11, 2),
        target_date=date(2026, 11, 8),
        preferred_session_minutes=60,
        arm="treatment",
    )
    ec6_120_trt = _evaluate_schedule_arm(
        tasks_in=mock_task,
        deps=[],
        avail=avail_120_slot,
        start_date=date(2026, 11, 7),
        target_date=date(2026, 11, 7),
        preferred_session_minutes=60,
        arm="treatment",
    )
    cases.append(
        {
            "scenario_id": "EC-6",
            "name": "Non-splittable 120m mock test vs slot length (90m -> NC-2, 120m -> 1 block)",
            "passed": (
                ec6_90_trt["feasibility_verdict"] == "EXPLICIT_UNSCHEDULABLE"
                and ec6_90_trt["unscheduled_reason_codes"]
                == ["TASK_EXCEEDS_CONTINUOUS_SLOT"]
                and ec6_120_trt["passed_hard_gates"]
                and ec6_120_trt["blocks_count"] == 1
                and ec6_120_trt["sensitive_tasks_split_across_days"] == 0
            ),
            "control_90m_slot": ec6_90_ctrl,
            "treatment_90m_slot": ec6_90_trt,
            "treatment_120m_slot": ec6_120_trt,
        }
    )

    # EC-7: R-03 back-to-back coalescing (12 -> 0 adjacent same-day splits)
    exp09 = json.loads(EXP09_PATH.read_text(encoding="utf-8"))
    key10 = json.loads(KEY10_PATH.read_text(encoding="utf-8"))["mapping"]
    rm03 = next(
        r
        for r in exp09["part_3_quality_ab_low_vs_medium"]["roadmaps"]
        if r["goal_key"] == key10["R-03"]["goal_id"]
        and r["arm"] == key10["R-03"]["arm"]
    )
    sd03, td03, pref03, avail03 = _goal_constraints(key10["R-03"]["goal_id"])
    r03_tasks = _strip_schedule_fields(rm03["decomposer"]["proposal"]["tasks"])
    r03_deps = rm03["decomposer"]["proposal"]["dependencies"]
    ec7_ctrl = _evaluate_schedule_arm(
        tasks_in=r03_tasks,
        deps=r03_deps,
        avail=avail03,
        start_date=sd03,
        target_date=td03,
        preferred_session_minutes=pref03,
        arm="control",
    )
    ec7_trt = _evaluate_schedule_arm(
        tasks_in=r03_tasks,
        deps=r03_deps,
        avail=avail03,
        start_date=sd03,
        target_date=td03,
        preferred_session_minutes=pref03,
        arm="treatment",
    )
    cases.append(
        {
            "scenario_id": "EC-7",
            "name": "R-03 back-to-back coalescing (adjacent_same_day_split_count: 12 -> 0)",
            "passed": ec7_ctrl["adjacent_same_day_split_count"] == 12
            and ec7_trt["adjacent_same_day_split_count"] == 0
            and ec7_trt["passed_hard_gates"],
            "control": ec7_ctrl,
            "treatment": ec7_trt,
        }
    )

    # EC-8: G4/G5 bin-packing rescue (100% placement without effort mutation)
    avail_g5 = _goal_constraints("G5_INTERMEDIATE_DATA_ENG_AIRFLOW_DBT")[3]
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
    ec8_g5_ctrl = _evaluate_schedule_arm(
        tasks_in=g5_tasks,
        deps=[],
        avail=avail_g5,
        start_date=date(2026, 11, 17),
        target_date=date(2026, 12, 22),
        preferred_session_minutes=60,
        arm="control",
    )
    ec8_g5_trt = _evaluate_schedule_arm(
        tasks_in=g5_tasks,
        deps=[],
        avail=avail_g5,
        start_date=date(2026, 11, 17),
        target_date=date(2026, 12, 22),
        preferred_session_minutes=60,
        arm="treatment",
    )
    cases.append(
        {
            "scenario_id": "EC-8",
            "name": "G5 bin-packing rescue (100% placement without task effort mutation)",
            "passed": ec8_g5_ctrl["placement_rate"] < 1.0
            and ec8_g5_trt["placement_rate"] == 1.0
            and ec8_g5_trt["estimated_minutes_mutated_count"] == 0
            and ec8_g5_trt["sub_30m_blocks_count"] == 0
            and ec8_g5_trt["passed_hard_gates"],
            "control": ec8_g5_ctrl,
            "treatment": ec8_g5_trt,
        }
    )

    return {
        "total_cases": len(cases),
        "passed_cases": sum(1 for c in cases if c["passed"]),
        "cases": cases,
    }


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Experiment 13 (PR-4): Controlled A/B Suite (Cohort A + B + C)"
    )
    parser.add_argument(
        "--skip-live",
        action="store_true",
        help="Skip Cohort B live CofHub runs (run Cohort A + Cohort C offline only).",
    )
    parser.add_argument(
        "--skip-golden-18",
        action="store_true",
        help="In Cohort B, run hard_6_goals only and skip golden_18_goals.",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=3,
        help="Bounded concurrency for Cohort B live CofHub runs (default: 3).",
    )
    args = parser.parse_args()

    cohort_a = run_cohort_a_frozen_replay()
    cohort_c = await run_cohort_c_edge_cases()

    if args.skip_live:
        cohort_b: dict[str, Any] = {
            "status": "SKIPPED_BY_FLAG",
            "health_probe": probe_cobhub_health(),
        }
    else:
        cohort_b = await run_cohort_b_live(
            concurrency=max(1, args.concurrency),
            skip_golden_18=args.skip_golden_18,
        )

    payload = {
        "schema_version": "1.0",
        "experiment": "exp_13_deterministic_ab_suite",
        "timestamp": utc_timestamp(),
        "repo_paths": {
            "backend_dir": str(BACKEND_DIR),
        },
        "cohort_a_frozen_replay": cohort_a,
        "cohort_b_live_e2e": cohort_b,
        "cohort_c_edge_cases": cohort_c,
    }
    out_path = write_experiment_json(OUTPUT_FILENAME, payload)
    print(f"\nSaved Experiment 13 artifact to {out_path}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
