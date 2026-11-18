"""Structural & deterministic audit metrics for FocusFlow milestones and roadmaps.

Computes deterministic quality signals that LLM-as-a-Judge often misses:
  - `capacity_utilization` (total milestone/task effort / available minutes); warns >90% / >100%
  - `effort_equal_ratio` (modal fraction of milestones sharing identical effort)
  - `milestone_vs_tasks_gap` (|sum(task_minutes) - sum(milestone_effort)| / sum(milestone_effort))
  - `linear_dependency_ratio` (fraction of tasks with strictly [prev_task] predecessor)
  - `max_consecutive_study_days` and `days_idle_before_deadline`
  - `split_integrity` (tasks split across multiple days, esp. mock tests / load tests, plus adjacent same-day splits)
  - `project_min_minutes` (PROJECT tasks < 90 minutes)

Can audit:
  1. The 10 blind-reviewed full roadmaps (`R-01`..`R-10`) from `exp_09_judge_and_quality_ab.json`
  2. The 12 blind-reviewed Milestone Planner plans (`M-01`..`M-12`) from `exp_10_planner_tool_rounds_ab.json`
  3. Any generic milestone/proposal JSON file (`--input`).
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from src.planning.domain.services.spatio_temporal_engine import (
    AvailabilityConfigurationDTO,
    AvailabilitySlotDTO,
    SpatioTemporalRuleEngine,
)

DEFAULT_EXP09_PATH = (
    REPO_ROOT / "docs" / "experiments" / "exp_09_judge_and_quality_ab.json"
)
DEFAULT_EXP10_PATH = (
    REPO_ROOT / "docs" / "experiments" / "exp_10_planner_tool_rounds_ab.json"
)
DEFAULT_HARD_DATASET_PATH = (
    BACKEND_DIR / "tests" / "ai_evals" / "datasets" / "hard_planning_6_goals.jsonl"
)
DEFAULT_KEY_10_PATH = (
    REPO_ROOT / "docs" / "experiments" / "blind_review_10_roadmaps_key.json"
)
DEFAULT_KEY_12_PATH = (
    REPO_ROOT / "docs" / "experiments" / "blind_review_hard_6_milestones_key.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "docs" / "experiments" / "structural_audit_results.json"
)

SENSITIVE_NON_SPLITTABLE_PATTERN = re.compile(
    r"(?:thi\s*thử|mock\s*test|load\s*test|stress\s*test|kiểm\s*thử\s*(?:chịu\s*)?tải|tải\s*cao|benchmark|đối\s*chuẩn|đánh\s*giá\s*tổng\s*hợp|kiểm\s*tra\s*cuối)",
    re.IGNORECASE,
)

# Exact goal constraints matching `scripts/experiments/exp_09_judge_and_quality_ab.py` (`_build_5_diverse_goals`).
EXP09_GOAL_CONSTRAINTS: dict[str, dict[str, Any]] = {
    "G1_BEGINNER_PYTHON_FASTAPI": {
        "start_date": "2026-11-17",
        "target_date": "2026-12-17",
        "availability": {
            "mode": "MODE_A",
            "default_daily_quota_minutes": 90,
            "daily_quota_minutes": {
                "monday": 90,
                "tuesday": 90,
                "wednesday": 90,
                "thursday": 90,
                "friday": 90,
                "saturday": 120,
                "sunday": 120,
            },
            "availability_slots": [],
            "disabled_weekdays": [],
        },
    },
    "G2_INTERMEDIATE_SYSTEM_DESIGN_CACHE": {
        "start_date": "2026-11-17",
        "target_date": "2026-12-15",
        "availability": {
            "mode": "MODE_B",
            "default_daily_quota_minutes": 90,
            "daily_quota_minutes": {},
            "availability_slots": [
                {"day_of_week": "tuesday", "start_time": "19:30", "end_time": "21:30"},
                {"day_of_week": "thursday", "start_time": "19:30", "end_time": "21:30"},
                {"day_of_week": "saturday", "start_time": "09:00", "end_time": "12:00"},
            ],
            "disabled_weekdays": [],
        },
    },
    "G3_ADVANCED_RUST_ASYNC_TOKIO": {
        "start_date": "2026-11-17",
        "target_date": "2026-12-29",
        "availability": {
            "mode": "MODE_A",
            "default_daily_quota_minutes": 90,
            "daily_quota_minutes": {
                "monday": 90,
                "tuesday": 90,
                "wednesday": 90,
                "thursday": 90,
                "friday": 90,
                "saturday": 150,
                "sunday": 150,
            },
            "availability_slots": [],
            "disabled_weekdays": [],
        },
    },
    "G4_BEGINNER_IELTS_WRITING": {
        "start_date": "2026-11-17",
        "target_date": "2026-12-31",
        "availability": {
            "mode": "MODE_A",
            "default_daily_quota_minutes": 60,
            "daily_quota_minutes": {
                "monday": 60,
                "tuesday": 60,
                "wednesday": 60,
                "thursday": 60,
                "friday": 60,
                "saturday": 90,
                "sunday": 90,
            },
            "availability_slots": [],
            "disabled_weekdays": [],
        },
    },
    "G5_INTERMEDIATE_DATA_ENG_AIRFLOW_DBT": {
        "start_date": "2026-11-17",
        "target_date": "2026-12-22",
        "availability": {
            "mode": "MODE_B",
            "default_daily_quota_minutes": 90,
            "daily_quota_minutes": {},
            "availability_slots": [
                {"day_of_week": "monday", "start_time": "19:30", "end_time": "21:00"},
                {
                    "day_of_week": "wednesday",
                    "start_time": "19:30",
                    "end_time": "21:00",
                },
                {"day_of_week": "friday", "start_time": "19:30", "end_time": "21:00"},
                {"day_of_week": "saturday", "start_time": "09:00", "end_time": "12:00"},
            ],
            "disabled_weekdays": [],
        },
    },
}


def build_availability_dto(raw: dict[str, Any]) -> AvailabilityConfigurationDTO:
    """Convert raw availability dict into `AvailabilityConfigurationDTO`."""
    slots = [
        AvailabilitySlotDTO(
            day_of_week=str(s["day_of_week"]).lower(),
            start_time=str(s["start_time"]),
            end_time=str(s["end_time"]),
            end_day_offset=int(s.get("end_day_offset", 0) or 0),
            is_active=bool(s.get("is_active", True)),
        )
        for s in (raw.get("availability_slots") or [])
    ]
    return AvailabilityConfigurationDTO(
        mode=str(raw.get("mode", "MODE_A")),
        daily_quota_minutes={
            str(k).lower(): int(v)
            for k, v in (raw.get("daily_quota_minutes") or {}).items()
        },
        default_daily_quota_minutes=int(
            raw.get("default_daily_quota_minutes", 60) or 60
        ),
        availability_slots=slots,
        disabled_weekdays=[
            str(d).lower() for d in (raw.get("disabled_weekdays") or [])
        ],
    )


def calculate_available_minutes(
    availability_raw: dict[str, Any],
    *,
    start_date: date,
    target_date: date,
) -> int:
    """Compute exact available study minutes via `SpatioTemporalRuleEngine`."""
    dto = build_availability_dto(availability_raw)
    return int(
        SpatioTemporalRuleEngine.calculate_available_capacity_minutes(
            dto,
            start_date=start_date,
            target_date=target_date,
        )
    )


def audit_milestone_plan(
    milestones: list[dict[str, Any]],
    *,
    start_date: date,
    target_date: date,
    availability_raw: dict[str, Any],
    scope_summary: str | None = None,
    deferred_scope: list[str] | None = None,
) -> dict[str, Any]:
    """Compute structural audit metrics for a Milestone Planner output."""
    ordered = sorted(milestones, key=lambda m: int(m.get("sequence_order", 0)))
    efforts = [int(m.get("estimated_effort_minutes", 0) or 0) for m in ordered]
    total_effort = sum(efforts)
    avail_minutes = calculate_available_minutes(
        availability_raw, start_date=start_date, target_date=target_date
    )
    utilization = round(total_effort / avail_minutes, 4) if avail_minutes > 0 else None

    effort_counts = Counter(efforts)
    modal_count = max(effort_counts.values()) if effort_counts else 0
    effort_equal_ratio = round(modal_count / len(efforts), 4) if efforts else 0.0
    unique_efforts = len(effort_counts)
    all_equal = unique_efforts <= 1 and len(efforts) > 1
    mean_effort = (total_effort / len(efforts)) if efforts else 0.0
    stddev = (
        round(math.sqrt(sum((e - mean_effort) ** 2 for e in efforts) / len(efforts)), 2)
        if efforts
        else 0.0
    )

    hard_violations: list[str] = []
    conditional_violations: list[str] = []
    soft_quality_warnings: list[str] = []
    structural_reasons: list[str] = []
    scheduling_reasons: list[str] = []

    if utilization is not None:
        if utilization > 1.0:
            hard_violations.append("UTILIZATION_OVER_100_PCT")
            scheduling_reasons.append("UTILIZATION_OVER_100_PCT")
        elif utilization > 0.90:
            conditional_violations.append("UTILIZATION_OVER_90_PCT")
    if all_equal:
        soft_quality_warnings.append("ALL_MILESTONE_EFFORTS_EQUAL")
    elif effort_equal_ratio >= 0.75 and len(efforts) >= 4:
        soft_quality_warnings.append("HIGH_MILESTONE_EFFORT_UNIFORMITY")

    diagnostics: dict[str, Any] = {
        "unique_effort_values_count": unique_efforts,
        "effort_stddev_minutes": stddev,
        "has_deferred_scope": bool(deferred_scope),
        "scope_summary_mentions_fit": bool(
            scope_summary and "FIT_CAPACITY" in scope_summary
        ),
    }
    soft_quality_score = round(max(0.0, 1.0 - 0.15 * len(soft_quality_warnings)), 4)
    warnings = [*hard_violations, *conditional_violations, *soft_quality_warnings]

    return {
        "milestones_count": len(ordered),
        "effort_values_minutes": efforts,
        "total_milestone_effort_minutes": total_effort,
        "available_capacity_minutes": avail_minutes,
        "capacity_utilization": utilization,
        "warn_utilization_gt_90pct": bool(
            utilization is not None and utilization > 0.90
        ),
        "warn_utilization_gt_100pct": bool(
            utilization is not None and utilization > 1.00
        ),
        "effort_equal_ratio": effort_equal_ratio,
        "all_efforts_equal": all_equal,
        "unique_effort_values_count": unique_efforts,
        "effort_stddev_minutes": stddev,
        "has_deferred_scope": bool(deferred_scope),
        "scope_summary_mentions_fit": bool(
            scope_summary and "FIT_CAPACITY" in scope_summary
        ),
        "hard_violations": hard_violations,
        "conditional_violations": conditional_violations,
        "soft_quality_warnings": soft_quality_warnings,
        "diagnostics": diagnostics,
        "structural_validity": len(structural_reasons) == 0,
        "scheduling_feasibility": len(scheduling_reasons) == 0,
        "pedagogical_quality": {
            "soft_quality_score": soft_quality_score,
            "soft_quality_warnings": list(soft_quality_warnings),
        },
        "failure_reasons_by_layer": {
            "structural_validity": structural_reasons,
            "scheduling_feasibility": scheduling_reasons,
            "conditional_constraints": conditional_violations,
            "soft_quality_warnings": soft_quality_warnings,
        },
        "warnings": warnings,
    }


def _parse_iso_dt(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def audit_roadmap_proposal(
    milestones: list[dict[str, Any]],
    proposal: dict[str, Any],
    *,
    start_date: date,
    target_date: date,
    availability_raw: dict[str, Any],
    scope_summary: str | None = None,
    deferred_scope: list[str] | None = None,
) -> dict[str, Any]:
    """Compute structural audit metrics for a full Milestone + Task Decomposer roadmap."""
    ms_metrics = audit_milestone_plan(
        milestones,
        start_date=start_date,
        target_date=target_date,
        availability_raw=availability_raw,
        scope_summary=scope_summary,
        deferred_scope=deferred_scope,
    )

    tasks: list[dict[str, Any]] = list(proposal.get("tasks") or [])
    dependencies: list[dict[str, Any]] = list(proposal.get("dependencies") or [])
    schedule_blocks: list[dict[str, Any]] = list(proposal.get("schedule_blocks") or [])

    total_task_minutes = sum(int(t.get("estimated_minutes", 0) or 0) for t in tasks)
    avail_minutes = int(ms_metrics["available_capacity_minutes"])
    task_utilization = (
        round(total_task_minutes / avail_minutes, 4) if avail_minutes > 0 else None
    )

    total_ms_effort = int(ms_metrics["total_milestone_effort_minutes"])
    if total_ms_effort > 0:
        ms_tasks_gap = round(
            abs(total_task_minutes - total_ms_effort) / total_ms_effort, 4
        )
        ms_tasks_ratio = round(total_task_minutes / total_ms_effort, 4)
    else:
        ms_tasks_gap = None
        ms_tasks_ratio = None

    # Linear dependency ratio: tasks (after the first) whose predecessor set is strictly [prev_task].
    task_ids = [str(t.get("task_id", "")).strip() for t in tasks]
    preds_by_task: dict[str, list[str]] = defaultdict(list)
    for dep in dependencies:
        pred = str(dep.get("predecessor_id", "")).strip()
        succ = str(dep.get("successor_id", "")).strip()
        if pred and succ:
            preds_by_task[succ].append(pred)

    non_initial = max(0, len(task_ids) - 1)
    linear_dep_tasks = 0
    branching_nodes = 0
    for idx in range(1, len(task_ids)):
        tid = task_ids[idx]
        prev_tid = task_ids[idx - 1]
        p_set = preds_by_task.get(tid, [])
        if p_set == [prev_tid]:
            linear_dep_tasks += 1
        elif len(p_set) > 1 or (p_set and p_set != [prev_tid]):
            branching_nodes += 1
    linear_dep_ratio = (
        round(linear_dep_tasks / non_initial, 4) if non_initial > 0 else 0.0
    )

    # Schedule cadence: consecutive study days, idle days before deadline, split integrity.
    blocks_by_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
    active_dates_set: set[date] = set()
    for blk in schedule_blocks:
        tid = str(blk.get("task_id", "")).strip()
        if tid:
            blocks_by_task[tid].append(blk)
        b_date_raw = blk.get("block_date")
        if isinstance(b_date_raw, str) and b_date_raw.strip():
            active_dates_set.add(date.fromisoformat(b_date_raw.strip()[:10]))

    if not active_dates_set:
        for task in tasks:
            s_date_raw = task.get("scheduled_date")
            if isinstance(s_date_raw, str) and s_date_raw.strip():
                active_dates_set.add(date.fromisoformat(s_date_raw.strip()[:10]))

    sorted_dates = sorted(active_dates_set)
    max_consecutive = 0
    cur_streak = 0
    prev_d: date | None = None
    for d in sorted_dates:
        if prev_d is not None and d == prev_d + timedelta(days=1):
            cur_streak += 1
        else:
            cur_streak = 1
        max_consecutive = max(max_consecutive, cur_streak)
        prev_d = d

    days_idle_before_deadline = (
        (target_date - sorted_dates[-1]).days if sorted_dates else None
    )

    tasks_split_across_days: list[dict[str, Any]] = []
    sensitive_tasks_split_across_days: list[dict[str, Any]] = []
    adjacent_same_day_split_tasks: list[dict[str, Any]] = []

    for task in tasks:
        tid = str(task.get("task_id", "")).strip()
        title = str(task.get("title", "")).strip()
        blks = sorted(
            blocks_by_task.get(tid, []),
            key=lambda b: int(b.get("sequence_in_task", 0) or 0),
        )
        if len(blks) <= 1:
            continue
        blk_dates = [str(b.get("block_date", ""))[:10] for b in blks]
        distinct_dates = sorted(set(blk_dates))
        blk_durs = [int(b.get("scheduled_duration_minutes", 0) or 0) for b in blks]
        is_sensitive = bool(SENSITIVE_NON_SPLITTABLE_PATTERN.search(title))

        if len(distinct_dates) > 1:
            rec = {
                "task_id": tid,
                "title": title,
                "task_type": str(task.get("task_type", "")),
                "estimated_minutes": int(task.get("estimated_minutes", 0) or 0),
                "distinct_dates": distinct_dates,
                "block_durations_minutes": blk_durs,
                "is_sensitive_non_splittable": is_sensitive,
            }
            tasks_split_across_days.append(rec)
            if is_sensitive:
                sensitive_tasks_split_across_days.append(rec)

        # Check same-day back-to-back contiguous split (e.g. 19:30-20:15 + 20:15-21:00)
        by_day: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for b in blks:
            by_day[str(b.get("block_date", ""))[:10]].append(b)
        for day_key, day_blks in by_day.items():
            if len(day_blks) <= 1:
                continue
            day_blks_sorted = sorted(
                day_blks,
                key=lambda b: str(b.get("scheduled_start") or ""),
            )
            is_contiguous = False
            for i in range(len(day_blks_sorted) - 1):
                end_cur = _parse_iso_dt(day_blks_sorted[i].get("scheduled_end"))
                start_next = _parse_iso_dt(
                    day_blks_sorted[i + 1].get("scheduled_start")
                )
                if (
                    end_cur is not None
                    and start_next is not None
                    and end_cur == start_next
                ):
                    is_contiguous = True
                    break
            adjacent_same_day_split_tasks.append(
                {
                    "task_id": tid,
                    "title": title,
                    "block_date": day_key,
                    "block_durations_minutes": [
                        int(b.get("scheduled_duration_minutes", 0) or 0)
                        for b in day_blks_sorted
                    ],
                    "is_contiguous": is_contiguous,
                }
            )

    project_tasks = [
        t for t in tasks if str(t.get("task_type", "")).upper() == "PROJECT"
    ]
    short_projects = [
        {
            "task_id": str(t.get("task_id", "")),
            "title": str(t.get("title", "")),
            "estimated_minutes": int(t.get("estimated_minutes", 0) or 0),
        }
        for t in project_tasks
        if int(t.get("estimated_minutes", 0) or 0) < 90
    ]
    min_project_minutes = (
        min(int(t.get("estimated_minutes", 0) or 0) for t in project_tasks)
        if project_tasks
        else None
    )

    hard_violations = list(ms_metrics["hard_violations"])
    conditional_violations = list(ms_metrics["conditional_violations"])
    soft_quality_warnings = list(ms_metrics["soft_quality_warnings"])
    structural_reasons = list(
        ms_metrics["failure_reasons_by_layer"]["structural_validity"]
    )
    scheduling_reasons = list(
        ms_metrics["failure_reasons_by_layer"]["scheduling_feasibility"]
    )

    if task_utilization is not None and task_utilization > 1.0:
        hard_violations.append("TASK_UTILIZATION_OVER_100_PCT")
        scheduling_reasons.append("TASK_UTILIZATION_OVER_100_PCT")
    if sensitive_tasks_split_across_days:
        hard_violations.append("SENSITIVE_TASK_SPLIT_ACROSS_DAYS")
        scheduling_reasons.append("SENSITIVE_TASK_SPLIT_ACROSS_DAYS")

    if ms_tasks_gap is not None and ms_tasks_gap > 0.15:
        conditional_violations.append("MILESTONE_VS_TASKS_GAP_GT_15_PCT")
    if short_projects:
        conditional_violations.append("PROJECT_UNDER_90_MIN")

    if linear_dep_ratio >= 0.90 and len(tasks) >= 6:
        soft_quality_warnings.append("PURELY_LINEAR_DEPENDENCIES")
    if max_consecutive >= 14:
        soft_quality_warnings.append("NO_REST_DAY_STREAK_GE_14")

    diagnostics = {
        **ms_metrics["diagnostics"],
        "tasks_count": len(tasks),
        "branching_nodes_count": branching_nodes,
        "active_study_days": len(sorted_dates),
        "max_consecutive_study_days": max_consecutive,
        "days_idle_before_deadline": days_idle_before_deadline,
        "tasks_split_across_days_count": len(tasks_split_across_days),
        "adjacent_same_day_split_count": len(adjacent_same_day_split_tasks),
    }
    soft_quality_score = round(max(0.0, 1.0 - 0.15 * len(soft_quality_warnings)), 4)
    warnings = [*hard_violations, *conditional_violations, *soft_quality_warnings]

    return {
        **ms_metrics,
        "tasks_count": len(tasks),
        "total_task_minutes": total_task_minutes,
        "task_capacity_utilization": task_utilization,
        "milestone_vs_tasks_gap": ms_tasks_gap,
        "milestone_vs_tasks_ratio": ms_tasks_ratio,
        "milestone_vs_tasks_delta_minutes": total_task_minutes - total_ms_effort,
        "dependencies_count": len(dependencies),
        "linear_dep_tasks_count": linear_dep_tasks,
        "non_initial_tasks_count": non_initial,
        "linear_dependency_ratio": linear_dep_ratio,
        "branching_nodes_count": branching_nodes,
        "active_study_days": len(sorted_dates),
        "first_study_date": sorted_dates[0].isoformat() if sorted_dates else None,
        "last_study_date": sorted_dates[-1].isoformat() if sorted_dates else None,
        "max_consecutive_study_days": max_consecutive,
        "days_idle_before_deadline": days_idle_before_deadline,
        "split_integrity": {
            "tasks_split_across_days_count": len(tasks_split_across_days),
            "sensitive_tasks_split_across_days_count": len(
                sensitive_tasks_split_across_days
            ),
            "adjacent_same_day_split_count": len(adjacent_same_day_split_tasks),
            "tasks_split_across_days": tasks_split_across_days,
            "sensitive_tasks_split_across_days": sensitive_tasks_split_across_days,
            "adjacent_same_day_split_tasks": adjacent_same_day_split_tasks,
        },
        "project_min_minutes": {
            "project_tasks_count": len(project_tasks),
            "min_project_minutes": min_project_minutes,
            "short_project_under_90_count": len(short_projects),
            "short_project_tasks": short_projects,
        },
        "hard_violations": hard_violations,
        "conditional_violations": conditional_violations,
        "soft_quality_warnings": soft_quality_warnings,
        "diagnostics": diagnostics,
        "structural_validity": len(structural_reasons) == 0,
        "scheduling_feasibility": len(scheduling_reasons) == 0,
        "pedagogical_quality": {
            "soft_quality_score": soft_quality_score,
            "soft_quality_warnings": list(soft_quality_warnings),
        },
        "failure_reasons_by_layer": {
            "structural_validity": structural_reasons,
            "scheduling_feasibility": scheduling_reasons,
            "conditional_constraints": conditional_violations,
            "soft_quality_warnings": soft_quality_warnings,
        },
        "warnings": warnings,
    }


def audit_10_blind_roadmaps(
    *,
    exp09_path: Path = DEFAULT_EXP09_PATH,
    key_path: Path = DEFAULT_KEY_10_PATH,
) -> list[dict[str, Any]]:
    """Audit all 10 roadmaps (`R-01`..`R-10`) using exact `exp_09` payloads."""
    exp09 = json.loads(exp09_path.read_text(encoding="utf-8"))
    key_data = json.loads(key_path.read_text(encoding="utf-8"))
    roadmaps_by_pair: dict[tuple[str, str], dict[str, Any]] = {
        (str(r["goal_key"]), str(r["arm"])): r
        for r in exp09["part_3_quality_ab_low_vs_medium"]["roadmaps"]
    }

    rows: list[dict[str, Any]] = []
    for label in sorted(key_data["mapping"].keys()):
        meta = key_data["mapping"][label]
        goal_key = str(meta["goal_id"])
        arm = str(meta["arm"])
        rm = roadmaps_by_pair[(goal_key, arm)]
        constraints = EXP09_GOAL_CONSTRAINTS[goal_key]
        audit = audit_roadmap_proposal(
            rm["planner"]["milestones"],
            rm["decomposer"]["proposal"],
            start_date=date.fromisoformat(constraints["start_date"]),
            target_date=date.fromisoformat(constraints["target_date"]),
            availability_raw=constraints["availability"],
            scope_summary=rm["planner"].get("scope_summary"),
            deferred_scope=rm["planner"].get("deferred_scope"),
        )
        rows.append(
            {
                "label": label,
                "goal_id": goal_key,
                "arm": arm,
                "model_id": meta.get("model_id"),
                "attempts_used": meta.get("attempts_used"),
                "judge_low_score": meta.get("judge_low_score"),
                "judge_medium_score": meta.get("judge_medium_score"),
                **audit,
            }
        )
    return rows


def audit_12_blind_milestones(
    *,
    exp10_path: Path = DEFAULT_EXP10_PATH,
    hard_dataset_path: Path = DEFAULT_HARD_DATASET_PATH,
    key_path: Path = DEFAULT_KEY_12_PATH,
) -> list[dict[str, Any]]:
    """Audit all 12 Milestone Planner outputs (`M-01`..`M-12`) from `exp_10`."""
    exp10 = json.loads(exp10_path.read_text(encoding="utf-8"))
    key_data = json.loads(key_path.read_text(encoding="utf-8"))
    dataset_by_id: dict[str, dict[str, Any]] = {
        str(obj["scenario_id"]): obj
        for line in hard_dataset_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
        for obj in [json.loads(line)]
    }
    scenarios_by_id: dict[str, dict[str, Any]] = {
        str(s["scenario_id"]): s for s in exp10.get("scenarios") or []
    }

    rows: list[dict[str, Any]] = []
    for label in sorted(key_data["mapping"].keys()):
        meta = key_data["mapping"][label]
        sid = str(meta["scenario_id"])
        arm = str(meta["arm"])
        arm_payload = scenarios_by_id[sid][arm]
        ds_item = dataset_by_id[sid]
        audit = audit_milestone_plan(
            arm_payload["milestones"],
            start_date=date.fromisoformat(str(ds_item["start_date"])),
            target_date=date.fromisoformat(str(ds_item["target_date"])),
            availability_raw=ds_item["availability"],
            scope_summary=arm_payload.get("scope_summary"),
            deferred_scope=arm_payload.get("deferred_scope"),
        )
        rows.append(
            {
                "label": label,
                "scenario_id": sid,
                "arm": arm,
                "wall_ms": meta.get("wall_ms"),
                **audit,
            }
        )
    return rows


def print_summary_tables(
    roadmaps_10: list[dict[str, Any]],
    milestones_12: list[dict[str, Any]],
) -> None:
    """Print readable Markdown summary tables to stdout."""
    print("## Audit 10 Roadmap (R-01..R-10)\n")
    print(
        "| Mã | Arm | MS | Tasks | MS Effort / Cap (`util%`) | Task Min (`gap%`) | Eq Effort | Linear Dep | Streak / Idle Early | Split Cross-Day (Sensitive) | Same-Day Adj Split | Project `<90m` |"
    )
    print("|---|---|---:|---:|---|---:|---:|---:|---|---:|---:|---:|")
    for r in roadmaps_10:
        util_pct = f"{r['capacity_utilization'] * 100:.1f}%"
        task_util = f"{r['task_capacity_utilization'] * 100:.1f}%"
        gap_pct = f"{r['milestone_vs_tasks_gap'] * 100:.1f}%"
        si = r["split_integrity"]
        pm = r["project_min_minutes"]
        print(
            f"| {r['label']} | {r['arm']} | {r['milestones_count']} | {r['tasks_count']} | "
            f"{r['total_milestone_effort_minutes']}/{r['available_capacity_minutes']} ({util_pct}) | "
            f"{r['total_task_minutes']}m ({task_util}, gap {gap_pct}) | "
            f"{r['effort_equal_ratio'] * 100:.0f}% | "
            f"{r['linear_dependency_ratio'] * 100:.1f}% ({r['linear_dep_tasks_count']}/{r['non_initial_tasks_count']}) | "
            f"{r['max_consecutive_study_days']}d / -{r['days_idle_before_deadline']}d | "
            f"{si['tasks_split_across_days_count']} ({si['sensitive_tasks_split_across_days_count']}) | "
            f"{si['adjacent_same_day_split_count']} | "
            f"{pm['short_project_under_90_count']} (min {pm['min_project_minutes']}m) |"
        )

    print("\n## Audit 12 Milestone Plans (M-01..M-12)\n")
    print(
        "| Mã | Scenario | Arm | MS | Effort / Cap (`util%`) | Eq Ratio | All Equal? | Efforts |"
    )
    print("|---|---|---|---:|---|---:|:---:|---|")
    for m in milestones_12:
        util_pct = f"{m['capacity_utilization'] * 100:.1f}%"
        print(
            f"| {m['label']} | {m['scenario_id']} | {m['arm']} | {m['milestones_count']} | "
            f"{m['total_milestone_effort_minutes']}/{m['available_capacity_minutes']} ({util_pct}) | "
            f"{m['effort_equal_ratio'] * 100:.1f}% | {'YES' if m['all_efforts_equal'] else 'no'} | "
            f"{m['effort_values_minutes']} |"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run structural deterministic audit on FocusFlow roadmaps & milestones.",
    )
    parser.add_argument("--exp09", type=Path, default=DEFAULT_EXP09_PATH)
    parser.add_argument("--exp10", type=Path, default=DEFAULT_EXP10_PATH)
    parser.add_argument("--hard-dataset", type=Path, default=DEFAULT_HARD_DATASET_PATH)
    parser.add_argument("--key10", type=Path, default=DEFAULT_KEY_10_PATH)
    parser.add_argument("--key12", type=Path, default=DEFAULT_KEY_12_PATH)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    roadmaps_10 = audit_10_blind_roadmaps(exp09_path=args.exp09, key_path=args.key10)
    milestones_12 = audit_12_blind_milestones(
        exp10_path=args.exp10,
        hard_dataset_path=args.hard_dataset,
        key_path=args.key12,
    )
    print_summary_tables(roadmaps_10, milestones_12)

    payload = {
        "schema_version": "1.0",
        "roadmaps_10_summary": {
            "count": len(roadmaps_10),
            "warn_gt_90pct_count": sum(
                1 for r in roadmaps_10 if r["warn_utilization_gt_90pct"]
            ),
            "warn_gt_100pct_count": sum(
                1 for r in roadmaps_10 if r["warn_utilization_gt_100pct"]
            ),
            "all_efforts_equal_count": sum(
                1 for r in roadmaps_10 if r["all_efforts_equal"]
            ),
            "pure_linear_dep_count": sum(
                1 for r in roadmaps_10 if r["linear_dependency_ratio"] >= 0.90
            ),
            "sensitive_split_across_days_total": sum(
                r["split_integrity"]["sensitive_tasks_split_across_days_count"]
                for r in roadmaps_10
            ),
            "short_project_under_90_total": sum(
                r["project_min_minutes"]["short_project_under_90_count"]
                for r in roadmaps_10
            ),
        },
        "milestones_12_summary": {
            "count": len(milestones_12),
            "warn_gt_90pct_count": sum(
                1 for m in milestones_12 if m["warn_utilization_gt_90pct"]
            ),
            "warn_gt_100pct_count": sum(
                1 for m in milestones_12 if m["warn_utilization_gt_100pct"]
            ),
            "all_efforts_equal_count": sum(
                1 for m in milestones_12 if m["all_efforts_equal"]
            ),
        },
        "roadmaps_10": roadmaps_10,
        "milestones_12": milestones_12,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"\nSaved JSON audit report to {args.output_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
