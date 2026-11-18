"""Experiment 11: Task Decomposer Precomputed Schedule Budget A/B.

Tests Decomposer BEFORE (`include_budget_context=False`) vs AFTER
(`include_budget_context=True`, injecting deterministic `[PRECOMPUTED_SCHEDULE_BUDGET]`)
on:
  1. `G4_BEGINNER_IELTS_WRITING` & `G5_INTERMEDIATE_DATA_ENG_AIRFLOW_DBT` using the
     exact Goal, Availability, and Planner milestones (`low` arm) from
     `docs/experiments/exp_09_judge_and_quality_ab.json` at `LOW` thinking level
     with 120s isolation budget.
  2. All 6 hard goals from `backend/tests/ai_evals/datasets/hard_planning_6_goals.jsonl`
     via `ProposalValidationGateOrchestrator` with configurable Decomposer timeout
     (`--decomposer-timeout`, default `40.0`; or `--both-timeouts` for `25.0` & `40.0`).

Constraints:
- NEVER modifies production prompts (`roadmap_skills.py`, `prompts.py`, `prompts.lock`).
- NEVER reads/prints secrets, API keys, or PII.
- Executes all cobhub calls (`http://127.0.0.1:8045`) strictly sequentially.

Output:
- `docs/experiments/exp_11_decomposer_budget_ab.json`
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
from collections import Counter
from collections.abc import Sequence
from datetime import date
from typing import Any
from uuid import UUID

from common import (
    BACKEND_DIR,
    EXPERIMENTS_OUT_DIR,
    get_cobhub_config,
    sanitize_error_message,
    summarize_numeric,
    utc_timestamp,
    write_experiment_json,
)
from exp_09_judge_and_quality_ab import (
    _build_5_diverse_goals,
    _build_decomposer_user_prompt,
    _TelemetryAdapter,
)
from src.planning.application.dtos.planning_dtos import (
    ClarificationQuestionsLLMOutput,
    TaskProposalLLMOutput,
)
from src.planning.application.services.knowledge_tool_dispatcher import (
    KnowledgeToolDispatcher,
    RoadmapPipelineStage,
)
from src.planning.application.services.roadmap_context_builder import (
    RoadmapContextBuilder,
)
from src.planning.application.services.roadmap_skills import (
    TASK_DECOMPOSER_SKILL,
    build_planning_prompt_registry,
    build_task_decomposer_prompt,
)
from src.planning.application.services.validation_gate import (
    ProposalValidationGateOrchestrator,
)
from src.planning.application.use_cases.proposal_generation_use_cases import (
    resolve_task_resources_from_tool_results,
)
from src.planning.domain.exceptions.planning_exceptions import (
    ProposalValidationGateError,
)
from src.planning.domain.models.goal import Goal
from src.planning.domain.models.milestone import Milestone, MilestoneStatus
from src.planning.domain.services.validation_types import (
    AvailabilityConfigurationDTO,
)
from src.planning.infrastructure.repositories.sqlalchemy_knowledge_base_repository import (
    InMemoryKnowledgeBaseRepository,
)
from src.shared_kernel.config import get_settings
from src.shared_kernel.domain.base import generate_uuid7
from tests.ai_evals.eval_runner import (
    _build_availability,
    _build_decomposer_inputs,
    _merge_clarification_answers_into_goal,
)

OUTPUT_FILENAME = "exp_11_decomposer_budget_ab.json"
EXP_09_PATH = EXPERIMENTS_OUT_DIR / "exp_09_judge_and_quality_ab.json"
HARD_DATASET_PATH = (
    BACKEND_DIR / "tests" / "ai_evals" / "datasets" / "hard_planning_6_goals.jsonl"
)


def _configure_env(
    base_url: str,
    api_key: str,
    *,
    decomposer_timeout_seconds: float,
    skip_critics: bool = True,
) -> None:
    os.environ["ENVIRONMENT"] = "development"
    os.environ["LLM_PROVIDER"] = "gemini"
    os.environ["LLM_BASE_URL"] = base_url
    if api_key and not os.environ.get("LLM_API_KEY"):
        os.environ["LLM_API_KEY"] = api_key
    os.environ["LLM_THINKING_CONTROL"] = "model_suffix"
    os.environ["LLM_MODEL"] = "gemini-3.8-flash-medium"
    os.environ["LLM_MODEL_LOW"] = "gemini-3.8-flash-low"
    os.environ["LLM_MODEL_MEDIUM"] = "gemini-3.8-flash-medium"
    os.environ["LLM_MODEL_HIGH"] = "gemini-3.8-flash-high"
    pipeline_timeout = max(120.0, decomposer_timeout_seconds * 2.5 + 10.0)
    hard_timeout = pipeline_timeout + 10.0
    os.environ["AI_HARD_TIMEOUT_SECONDS"] = str(hard_timeout)
    os.environ["AI_SSE_PIPELINE_TIMEOUT_SECONDS"] = str(pipeline_timeout)
    os.environ["AI_MILESTONE_PLANNER_TIMEOUT_SECONDS"] = str(
        max(50.0, decomposer_timeout_seconds)
    )
    os.environ["AI_TASK_DECOMPOSER_TIMEOUT_SECONDS"] = str(decomposer_timeout_seconds)
    os.environ["AI_TOOL_CALL_TIMEOUT_SECONDS"] = str(decomposer_timeout_seconds)
    os.environ["AI_MIN_RETRY_REMAINING_SECONDS"] = "12.0"
    os.environ["AI_MIN_JUDGE_REMAINING_SECONDS"] = "3.0"
    if skip_critics:
        os.environ["AI_MIN_CRITIC_REMAINING_SECONDS"] = str(pipeline_timeout + 5.0)
    else:
        os.environ["AI_MIN_CRITIC_REMAINING_SECONDS"] = "6.0"
    get_settings.cache_clear()


def compute_precomputed_schedule_budget(
    *,
    availability: AvailabilityConfigurationDTO,
    start_date: date,
    target_date: date | None,
    milestones: Sequence[Milestone],
    opt_session_minutes: int,
) -> dict[str, Any]:
    """Use the canonical RoadmapContextBuilder.compute_schedule_budget metrics."""
    return RoadmapContextBuilder.compute_schedule_budget(
        availability=availability,
        milestones=milestones,
        start_date=start_date,
        target_date=target_date,
        learner_profile={"opt_session_minutes": opt_session_minutes},
    )


def inject_schedule_budget_into_prompt(user_prompt: str, budget: dict[str, Any]) -> str:
    """Append canonical `precomputed_schedule_budget` JSON before final action/skill tail."""
    budget_line = (
        f"precomputed_schedule_budget: {json.dumps(budget, ensure_ascii=False)}"
    )
    for marker in ("\n\nYêu cầu hành động:", "\nskill="):
        if marker in user_prompt:
            head, tail = user_prompt.split(marker, 1)
            return f"{head}\n{budget_line}{marker}{tail}"
    return f"{user_prompt}\n{budget_line}"


def _load_g4_g5_from_exp09() -> list[dict[str, Any]]:
    exp09_data = json.loads(EXP_09_PATH.read_text(encoding="utf-8"))
    goals_by_key = {g["goal_key"]: g for g in _build_5_diverse_goals()}
    roadmaps = exp09_data["part_3_quality_ab_low_vs_medium"]["roadmaps"]

    selected: list[dict[str, Any]] = []
    for g_key in ("G4_BEGINNER_IELTS_WRITING", "G5_INTERMEDIATE_DATA_ENG_AIRFLOW_DBT"):
        goal_def = goals_by_key[g_key]
        rm_low = next(
            r for r in roadmaps if r["goal_key"] == g_key and r["arm"] == "low"
        )
        roadmap_id = generate_uuid7()
        milestone_entities: list[Milestone] = []
        for m in sorted(
            rm_low["planner"]["milestones"], key=lambda x: int(x["sequence_order"])
        ):
            outcomes = tuple(
                str(o.get("description") or o.get("id") or o)
                if isinstance(o, dict)
                else str(o)
                for o in (m.get("learning_outcomes") or [])
            )
            milestone_entities.append(
                Milestone(
                    id=UUID(str(m["milestone_id"])),
                    roadmap_id=roadmap_id,
                    sequence_order=int(m["sequence_order"]),
                    title=str(m["title"]),
                    description=str(m.get("description") or "").strip() or None,
                    learning_outcomes=outcomes,
                    completion_criteria=str(m.get("completion_criteria") or "").strip()
                    or None,
                    estimated_effort_minutes=max(
                        15, int(m.get("estimated_effort_minutes", 60) or 60)
                    ),
                    required_concepts=tuple(
                        str(c) for c in (m.get("required_concepts") or [])
                    ),
                    unverified_concepts=tuple(
                        str(c) for c in (m.get("unverified_concepts") or [])
                    ),
                    status=MilestoneStatus.APPROVED,
                )
            )
        selected.append(
            {
                "case_id": g_key,
                "goal": goal_def,
                "roadmap_id": roadmap_id,
                "milestones": milestone_entities,
                "exp09_low_retry_history": rm_low["decomposer"].get(
                    "retry_history", []
                ),
            }
        )
    return selected


def _load_hard_scenarios() -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in HARD_DATASET_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _extract_attempt1_rule_codes(
    *,
    retry_history: list[dict[str, Any]],
    gate_violations: list[dict[str, Any]],
    attempts_used: int,
) -> list[str]:
    if retry_history:
        first_viols = retry_history[0].get("violations", [])
        return [str(v.get("rule_code", "")) for v in first_viols if isinstance(v, dict)]
    if attempts_used <= 1 and gate_violations:
        return [
            str(v.get("rule_code", "")) for v in gate_violations if isinstance(v, dict)
        ]
    return []


async def _run_decomposer_arm(
    *,
    case_id: str,
    arm_name: str,
    include_budget_context: bool,
    goal_title: str,
    learner_level: str,
    availability: AvailabilityConfigurationDTO,
    start_date: date,
    target_date: date,
    opt_session_minutes: int,
    milestones: list[Milestone],
    base_user_prompt: str,
    milestone_summary_json: str,
    max_retries: int,
    roadmap_id: UUID,
    thinking_level: str,
    enable_tools: bool = True,
    max_tool_calls: int = TASK_DECOMPOSER_SKILL.max_tool_calls,
) -> dict[str, Any]:
    kb = InMemoryKnowledgeBaseRepository()
    dispatcher = KnowledgeToolDispatcher(
        kb,
        stage=RoadmapPipelineStage.TASK_DECOMPOSITION,
        max_tool_calls=TASK_DECOMPOSER_SKILL.max_tool_calls,
        timeout_seconds=10.0,
    )
    decomposer_tpl = build_planning_prompt_registry().latest(
        TASK_DECOMPOSER_SKILL.skill_id
    )
    budget_info = compute_precomputed_schedule_budget(
        availability=availability,
        start_date=start_date,
        target_date=target_date,
        milestones=milestones,
        opt_session_minutes=opt_session_minutes,
    )
    effective_prompt = (
        inject_schedule_budget_into_prompt(base_user_prompt, budget_info)
        if include_budget_context
        else base_user_prompt
    )

    adapter = _TelemetryAdapter()
    orchestrator = ProposalValidationGateOrchestrator(
        llm_provider=adapter,
        enable_tier3_judge=False,
        roadmap_id=roadmap_id,
    )

    t0 = time.perf_counter()
    final_passed = False
    attempt_1_passed = False
    attempts_used = 0
    retry_history: list[dict[str, Any]] = []
    gate_violations: list[dict[str, Any]] = []
    error: str | None = None
    tasks_count = 0
    total_estimated_minutes = 0
    soft_warnings_count = 0

    try:
        gate_res = await orchestrator.generate_and_validate_proposal_with_retry(
            system_prompt=decomposer_tpl.system_template,
            user_prompt=effective_prompt,
            response_schema=TaskProposalLLMOutput.model_json_schema(),
            availability=availability,
            valid_milestone_ids={m.id for m in milestones},
            current_roadmap_target_date=target_date,
            goal_title=goal_title,
            learner_level=learner_level,
            milestone_summary=milestone_summary_json,
            max_retries=max_retries,
            start_date=start_date,
            milestone_order_map={str(m.id): m.sequence_order for m in milestones},
            tools=dispatcher.get_allowed_tool_declarations() if enable_tools else None,
            tool_executor=dispatcher.dispatch if enable_tools else None,
            max_tool_calls=max_tool_calls if enable_tools else 0,
            thinking_level=thinking_level,
            deterministic_allocation=True,
            preferred_session_minutes=opt_session_minutes,
            milestones=milestones,
            resource_resolver=(
                lambda raw_prop: resolve_task_resources_from_tool_results(
                    raw_prop,
                    dispatcher.collected_resources,
                    strict=True,
                )
            )
            if enable_tools
            else None,
            prompt_template=decomposer_tpl,
        )
        final_passed = bool(gate_res.is_valid and len(gate_res.violations) == 0)
        attempts_used = max(1, int(gate_res.attempts_used))
        attempt_1_passed = final_passed and attempts_used == 1
        retry_history = list(gate_res.retry_history)
        soft_warnings_count = len(gate_res.soft_overflow_warnings or ())
        proposal = dict(gate_res.validated_proposal_data or {})
        tasks = (
            proposal.get("tasks", []) if isinstance(proposal.get("tasks"), list) else []
        )
        tasks_count = len(tasks)
        total_estimated_minutes = sum(
            int(t.get("estimated_minutes", 0) or 0)
            for t in tasks
            if isinstance(t, dict)
        )
    except ProposalValidationGateError as exc:
        error = f"{exc.code}: {exc.message}"
        gate_violations = list(exc.violations)
        attempts_used = max(1, len([c for c in adapter.calls if c.get("ok")]))
    except Exception as exc:  # noqa: BLE001
        error = sanitize_error_message(exc)
        attempts_used = max(1, len(adapter.calls))

    wall_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    attempt_1_rule_codes = _extract_attempt1_rule_codes(
        retry_history=retry_history,
        gate_violations=gate_violations,
        attempts_used=attempts_used,
    )
    if not attempt_1_passed and not attempt_1_rule_codes and error:
        attempt_1_rule_codes = [error.split(":", 1)[0]]

    return {
        "case_id": case_id,
        "arm": arm_name,
        "include_budget_context": include_budget_context,
        "attempt_1_passed": attempt_1_passed,
        "final_passed": final_passed,
        "retried": attempts_used > 1,
        "attempts_used": attempts_used,
        "attempt_1_failure_rule_codes": attempt_1_rule_codes,
        "wall_ms": wall_ms,
        "model_id": next(
            (c.get("model_id") for c in reversed(adapter.calls) if c.get("ok")), None
        ),
        "prompt_tokens": sum(
            int(c.get("prompt_tokens", 0) or 0) for c in adapter.calls if c.get("ok")
        ),
        "output_tokens": sum(
            int(c.get("output_tokens", 0) or 0) for c in adapter.calls if c.get("ok")
        ),
        "thinking_tokens": sum(
            int(c.get("thinking_tokens", 0) or 0) for c in adapter.calls if c.get("ok")
        ),
        "tasks_count": tasks_count,
        "total_estimated_minutes": total_estimated_minutes,
        "soft_warnings_count": soft_warnings_count,
        "retry_history": retry_history,
        "gate_violations": gate_violations,
        "error": error,
        "precomputed_schedule_budget": budget_info if include_budget_context else None,
    }


def _summarize_arm_group(rows: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for arm_name in ("before_no_budget", "after_with_budget"):
        subset = [r for r in rows if r["arm"] == arm_name]
        n = len(subset)
        a1_pass = sum(1 for r in subset if r["attempt_1_passed"])
        final_pass = sum(1 for r in subset if r["final_passed"])
        retries = sum(1 for r in subset if r["retried"])
        rule_counts = Counter(
            code for r in subset for code in r.get("attempt_1_failure_rule_codes", [])
        )
        latencies = [float(r["wall_ms"]) for r in subset]
        out[arm_name] = {
            "count": n,
            "attempt_1_pass_count": a1_pass,
            "attempt_1_pass_at_1_rate": round(a1_pass / max(1, n), 4),
            "final_pass_count": final_pass,
            "final_pass_rate": round(final_pass / max(1, n), 4),
            "retry_count": retries,
            "retry_rate": round(retries / max(1, n), 4),
            "attempt_1_failure_rule_codes": dict(rule_counts),
            "latency_ms": summarize_numeric(latencies),
            "prompt_tokens_total": sum(int(r["prompt_tokens"]) for r in subset),
            "output_tokens_total": sum(int(r["output_tokens"]) for r in subset),
            "thinking_tokens_total": sum(int(r["thinking_tokens"]) for r in subset),
        }
    return out


async def run_g4_g5_isolation(base_url: str, api_key: str) -> dict[str, Any]:
    print("\n=== [Part 1] G4 & G5 (120s Isolation, LOW thinking) ===", flush=True)
    _configure_env(
        base_url, api_key, decomposer_timeout_seconds=120.0, skip_critics=True
    )
    cases = _load_g4_g5_from_exp09()
    rows: list[dict[str, Any]] = []

    for case in cases:
        goal_def = case["goal"]
        milestones: list[Milestone] = case["milestones"]
        base_prompt = _build_decomposer_user_prompt(
            goal=goal_def, milestones=milestones
        )
        ms_summary_json = json.dumps(
            [
                {
                    "milestone_id": str(m.id),
                    "sequence_order": m.sequence_order,
                    "title": m.title,
                    "learning_outcomes": list(m.learning_outcomes),
                    "completion_criteria": m.completion_criteria or "",
                    "estimated_effort_minutes": m.estimated_effort_minutes,
                    "required_concepts": list(m.required_concepts),
                }
                for m in milestones
            ],
            ensure_ascii=False,
        )
        for arm_name, include_budget in (
            ("before_no_budget", False),
            ("after_with_budget", True),
        ):
            print(f"  [{case['case_id']}] arm={arm_name}...", flush=True)
            res = await _run_decomposer_arm(
                case_id=case["case_id"],
                arm_name=arm_name,
                include_budget_context=include_budget,
                goal_title=goal_def["goal_title"],
                learner_level=goal_def["learner_level"],
                availability=goal_def["availability"],
                start_date=date.fromisoformat(goal_def["start_date"]),
                target_date=date.fromisoformat(goal_def["target_date"]),
                opt_session_minutes=int(goal_def["opt_session_minutes"]),
                milestones=milestones,
                base_user_prompt=base_prompt,
                milestone_summary_json=ms_summary_json,
                max_retries=1,
                roadmap_id=case["roadmap_id"],
                thinking_level="LOW",
                enable_tools=True,
                max_tool_calls=2,
            )
            rows.append(res)
            print(
                f"    -> a1_pass={res['attempt_1_passed']} final_pass={res['final_passed']} "
                f"att={res['attempts_used']} wall={res['wall_ms']}ms rules={res['attempt_1_failure_rule_codes']}",
                flush=True,
            )

    return {
        "decomposer_timeout_seconds": 120.0,
        "thinking_level": "LOW",
        "summary": _summarize_arm_group(rows),
        "runs": rows,
    }


async def run_hard_6_goals(
    base_url: str,
    api_key: str,
    *,
    decomposer_timeout_seconds: float,
) -> dict[str, Any]:
    print(
        f"\n=== [Part 2] Hard 6 Goals (decomposer_timeout={decomposer_timeout_seconds}s) ===",
        flush=True,
    )
    _configure_env(
        base_url,
        api_key,
        decomposer_timeout_seconds=decomposer_timeout_seconds,
        skip_critics=True,
    )
    scenarios = _load_hard_scenarios()
    rows: list[dict[str, Any]] = []

    for scenario in scenarios:
        sid = str(scenario["scenario_id"])
        user_id = generate_uuid7()
        availability = _build_availability(scenario["availability"])
        start_d = date.fromisoformat(str(scenario["start_date"]))
        target_d = date.fromisoformat(str(scenario["target_date"]))

        goal = Goal(
            id=generate_uuid7(),
            user_id=user_id,
            title=str(scenario["goal"].get("title", "")),
            raw_description=str(scenario["goal"].get("raw_description", "")),
            target_date=target_d,
            prior_knowledge_level=str(scenario.get("learner_level", "INTERMEDIATE")),
        )
        clar_summary = _merge_clarification_answers_into_goal(
            goal,
            scenario,
            ClarificationQuestionsLLMOutput(questions=[]),
        )
        milestones_raw = list(scenario.get("milestones", []))
        milestone_entities, _, milestone_json, raw_prompt_before = (
            _build_decomposer_inputs(
                scenario,
                milestones_raw,
                effective_parallel=True,
                clarification_summary=clar_summary,
                include_budget_context=False,
            )
        )
        base_prompt_before = build_task_decomposer_prompt(raw_prompt_before)

        for arm_name, include_budget in (
            ("before_no_budget", False),
            ("after_with_budget", True),
        ):
            print(
                f"  [{sid}] arm={arm_name} (timeout={decomposer_timeout_seconds}s)...",
                flush=True,
            )
            res = await _run_decomposer_arm(
                case_id=sid,
                arm_name=arm_name,
                include_budget_context=include_budget,
                goal_title=goal.title,
                learner_level=goal.prior_knowledge_level,
                availability=availability,
                start_date=start_d,
                target_date=target_d,
                opt_session_minutes=60,
                milestones=milestone_entities,
                base_user_prompt=base_prompt_before,
                milestone_summary_json=milestone_json,
                max_retries=2,
                roadmap_id=generate_uuid7(),
                thinking_level=TASK_DECOMPOSER_SKILL.thinking_level,
                enable_tools=False,
                max_tool_calls=0,
            )
            rows.append(res)
            print(
                f"    -> a1_pass={res['attempt_1_passed']} final_pass={res['final_passed']} "
                f"att={res['attempts_used']} wall={res['wall_ms']}ms rules={res['attempt_1_failure_rule_codes']}",
                flush=True,
            )

    return {
        "decomposer_timeout_seconds": decomposer_timeout_seconds,
        "thinking_level": TASK_DECOMPOSER_SKILL.thinking_level,
        "summary": _summarize_arm_group(rows),
        "runs": rows,
    }


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Exp 11: Task Decomposer Precomputed Schedule Budget A/B",
    )
    parser.add_argument(
        "--decomposer-timeout",
        "--timeout-seconds",
        type=float,
        default=40.0,
        dest="decomposer_timeout",
        help="Decomposer timeout budget in seconds for hard_6_goals (default: 40.0).",
    )
    parser.add_argument(
        "--both-timeouts",
        action="store_true",
        help="Run hard_6_goals at both 25.0s (production) and 40.0s budgets.",
    )
    parser.add_argument(
        "--skip-g4-g5",
        action="store_true",
        help="Skip Part 1 (G4 & G5 120s isolation).",
    )
    parser.add_argument(
        "--skip-hard-6",
        action="store_true",
        help="Skip Part 2 (hard_planning_6_goals).",
    )
    args = parser.parse_args()

    base_url, api_key = get_cobhub_config()
    report: dict[str, Any] = {
        "schema_version": "1.0",
        "experiment": "exp_11_decomposer_budget_ab",
        "timestamp": utc_timestamp(),
        "gateway_base_url": base_url,
    }

    if not args.skip_g4_g5:
        report["part_1_g4_g5_120s"] = await run_g4_g5_isolation(base_url, api_key)

    if not args.skip_hard_6:
        timeouts = (
            [25.0, 40.0] if args.both_timeouts else [float(args.decomposer_timeout)]
        )
        hard_runs: dict[str, Any] = {}
        for t_sec in timeouts:
            key = f"timeout_{int(t_sec)}s"
            hard_runs[key] = await run_hard_6_goals(
                base_url,
                api_key,
                decomposer_timeout_seconds=t_sec,
            )
        report["part_2_hard_6_goals"] = hard_runs

    out_path = write_experiment_json(OUTPUT_FILENAME, report)
    print(f"\nSaved Exp 11 report to {out_path}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
