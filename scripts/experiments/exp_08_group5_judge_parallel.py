"""Live cobhub experiment for Group 5: Parallel Tier 3 Judge (8.0s) + Dual Critics & 55s Pipeline Budget.

Runs all 18 scenarios from `golden_planning_18_goals.jsonl` through the production
`ProposalValidationGateOrchestrator` with `gemini-3.8-flash-low`, `tier3_judge_timeout_seconds=8.0`,
and `ai_sse_pipeline_timeout_seconds=55.0`, measuring:
1. Real Judge verdict rate (`PASSED` + `NEEDS_REVIEW`) over valid Tier 1/2 proposals (target >= 80%).
2. Per-stage and end-to-end `p50`/`p95` latency budget table (proving Schedule Generation p95 <= 55.0s).

Saves PII-free results to `docs/experiments/group5_judge_and_pipeline_budget.json`.
"""

from __future__ import annotations

import asyncio
import json
import math
import os
import statistics
import time
from pathlib import Path
from typing import Any
from uuid import UUID

from common import EXPERIMENTS_OUT_DIR, REPO_ROOT, get_cobhub_config, utc_timestamp
from src.planning.application.dtos.planning_dtos import TaskProposalLLMOutput
from src.planning.application.services.roadmap_skills import (
    TASK_DECOMPOSER_SKILL,
    build_planning_prompt_registry,
)
from src.planning.application.services.validation_gate import (
    ProposalValidationGateOrchestrator,
)
from src.planning.domain.exceptions.planning_exceptions import (
    ProposalValidationGateError,
)
from src.shared_kernel.application.llm_port import LLMGenerationResult
from src.shared_kernel.config import get_settings
from src.shared_kernel.infrastructure.external_ai.litellm_adapter import LiteLLMAdapter
from src.shared_kernel.infrastructure.external_ai.prompt_sanitizer import (
    PromptSanitizer,
)
from tests.ai_evals.eval_runner import (
    _build_availability,
    _build_milestone_entities,
    load_18_goal_dataset,
)

OUTPUT_PATH: Path = EXPERIMENTS_OUT_DIR / "group5_judge_and_pipeline_budget.json"
GROUP2_PATH: Path = EXPERIMENTS_OUT_DIR / "group2_measurements.json"


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return round(ordered[0], 2)
    rank = (len(ordered) - 1) * (pct / 100.0)
    lo = math.floor(rank)
    hi = math.ceil(rank)
    if lo == hi:
        return round(ordered[lo], 2)
    w = rank - lo
    return round(ordered[lo] * (1.0 - w) + ordered[hi] * w, 2)


def _summarize_ms(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"count": 0, "min_ms": 0.0, "p50_ms": 0.0, "p95_ms": 0.0, "max_ms": 0.0, "mean_ms": 0.0}
    return {
        "count": len(values),
        "min_ms": round(min(values), 2),
        "p50_ms": _percentile(values, 50.0),
        "p95_ms": _percentile(values, 95.0),
        "max_ms": round(max(values), 2),
        "mean_ms": round(statistics.mean(values), 2),
    }


def _configure_env(base_url: str) -> None:
    os.environ["LLM_PROVIDER"] = "gemini"
    os.environ["LLM_BASE_URL"] = base_url
    os.environ["LLM_THINKING_CONTROL"] = "model_suffix"
    os.environ["LLM_MODEL"] = "gemini-3.8-flash-low"
    os.environ["LLM_MODEL_LOW"] = "gemini-3.8-flash-low"
    os.environ["LLM_MODEL_MEDIUM"] = "gemini-3.8-flash-medium"
    os.environ["LLM_MODEL_HIGH"] = "gemini-3.8-flash-high"
    os.environ["TIER3_JUDGE_TIMEOUT_SECONDS"] = "8.0"
    os.environ["AI_MIN_JUDGE_REMAINING_SECONDS"] = "3.0"
    os.environ["AI_MIN_CRITIC_REMAINING_SECONDS"] = "6.0"
    os.environ["AI_SSE_PIPELINE_TIMEOUT_SECONDS"] = "55.0"
    os.environ["AI_HARD_TIMEOUT_SECONDS"] = "55.0"
    get_settings.cache_clear()


class _StageTelemetryAdapter(LiteLLMAdapter):
    """Thin wrapper over production LiteLLMAdapter recording per-stage wall timings."""

    def __init__(self) -> None:
        super().__init__()
        self.events: list[dict[str, Any]] = []

    async def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: dict[str, Any] | type[Any] | None = None,
        tools: list[Any] | None = None,
        tool_executor: Any = None,
        max_tool_calls: int = 2,
        thinking_level: str | None = None,
        timeout_seconds: float | None = None,
        tool_call_timeout_seconds: float | None = None,
    ) -> LLMGenerationResult:
        if "[INDEPENDENT_CRITIC:" in user_prompt:
            stage = "CRITIC"
        elif "[QUALITY_ARBITER]" in user_prompt:
            stage = "ARBITER"
        elif "pedagogical-quality-judge" in system_prompt or "pedagogical-quality-judge" in user_prompt:
            stage = "JUDGE"
        else:
            stage = "DECOMPOSER"

        t_start = time.perf_counter()
        try:
            res = await super().generate_structured(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_schema=response_schema,
                tools=tools,
                tool_executor=tool_executor,
                max_tool_calls=max_tool_calls,
                thinking_level=thinking_level,
                timeout_seconds=timeout_seconds,
                tool_call_timeout_seconds=tool_call_timeout_seconds,
            )
            elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            self.events.append(
                {
                    "stage": stage,
                    "ok": True,
                    "start_perf": t_start,
                    "end_perf": time.perf_counter(),
                    "elapsed_ms": round(elapsed_ms, 2),
                    "timeout_seconds": timeout_seconds,
                    "model_id": res.model_id,
                    "prompt_tokens": res.prompt_tokens,
                    "output_tokens": res.output_tokens,
                    "thinking_tokens": res.thinking_tokens,
                }
            )
            return res
        except BaseException as exc:
            elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            self.events.append(
                {
                    "stage": stage,
                    "ok": False,
                    "start_perf": t_start,
                    "end_perf": time.perf_counter(),
                    "elapsed_ms": round(elapsed_ms, 2),
                    "timeout_seconds": timeout_seconds,
                    "error_type": type(exc).__name__,
                }
            )
            raise


async def run_scenario(idx: int, scenario: dict[str, Any]) -> dict[str, Any]:
    from datetime import date

    decomposer_tpl = build_planning_prompt_registry().latest(TASK_DECOMPOSER_SKILL.skill_id)
    availability = _build_availability(scenario["availability"])
    milestones = list(scenario["milestones"])
    milestone_entities = _build_milestone_entities(milestones)
    valid_milestone_ids = {UUID(str(m["milestone_id"])) for m in milestones}
    milestone_json = json.dumps(
        [
            {
                "milestone_id": m["milestone_id"],
                "sequence_order": m["sequence_order"],
                "title": m["title"],
                "required_concepts": m.get("required_concepts", []),
                "learning_outcomes": m.get("learning_outcomes", []),
                "completion_criteria": m.get("completion_criteria")
                or "; ".join(
                    str(o.get("description") or o.get("id") or o)
                    if isinstance(o, dict)
                    else str(o)
                    for o in (m.get("learning_outcomes") or [])
                ),
                "estimated_effort_minutes": m.get("estimated_effort_minutes", 120),
            }
            for m in milestones
        ],
        ensure_ascii=False,
    )
    all_required_concepts = list(
        dict.fromkeys(
            str(c).strip()
            for m in milestones
            for c in (m.get("required_concepts") or [])
            if str(c).strip()
        )
    )
    sanitized_goal = PromptSanitizer.sanitize(
        str(scenario["goal"].get("raw_description", "")), wrap_xml=True
    )
    user_prompt = (
        f"GENERATE_PROPOSAL_TASKS\n"
        f"GOAL: {PromptSanitizer.sanitize(str(scenario['goal'].get('title', '')), wrap_xml=True)}\n"
        f"DESCRIPTION: {sanitized_goal}\n"
        f"PLANNING_WINDOW: {scenario['start_date']}..{scenario['target_date']}\n"
        f"MILESTONE_IDS: {','.join(str(m['milestone_id']) for m in milestones)}\n"
        f"required_concepts={','.join(all_required_concepts)}\n"
        f"approved_milestones={milestone_json}\n"
        f"skill=learning-task-decomposer"
    )

    adapter = _StageTelemetryAdapter()
    orchestrator = ProposalValidationGateOrchestrator(
        llm_provider=adapter,
        enable_tier3_judge=True,
        tier3_timeout_seconds=8.0,
    )

    t0 = time.perf_counter()
    valid_proposal = False
    attempts_used = 1
    judge_status = "SKIPPED_NO_PROPOSAL"
    judge_skipped = True
    pedagogical_score: float | None = None
    tasks_count = 0
    error_code: str | None = None
    prompt_tokens = 0
    completion_tokens = 0
    thinking_tokens = 0

    try:
        res = await orchestrator.generate_and_validate_proposal_with_retry(
            system_prompt=decomposer_tpl.system_template,
            user_prompt=user_prompt,
            response_schema=TaskProposalLLMOutput.model_json_schema(),
            availability=availability,
            valid_milestone_ids=valid_milestone_ids,
            start_date=date.fromisoformat(str(scenario["start_date"])),
            current_roadmap_target_date=date.fromisoformat(str(scenario["target_date"])),
            goal_title=str(scenario["goal"].get("title", "")),
            learner_level=str(scenario.get("learner_level", "")),
            milestone_summary=milestone_json,
            milestones=milestone_entities,
            thinking_level="LOW",
            deterministic_allocation=True,
            max_retries=2,
            prompt_template=decomposer_tpl,
        )
        valid_proposal = res.is_valid
        attempts_used = res.attempts_used
        judge_status = res.judge_status
        judge_skipped = res.judge_skipped
        pedagogical_score = res.pedagogical_score
        tasks_count = len((res.validated_proposal_data or {}).get("tasks", []))
        prompt_tokens = res.total_prompt_tokens
        completion_tokens = res.total_completion_tokens
        thinking_tokens = res.total_thinking_tokens
    except ProposalValidationGateError as exc:
        error_code = exc.code
        attempts_used = 3
    except Exception as exc:
        error_code = type(exc).__name__

    total_ms = round((time.perf_counter() - t0) * 1000.0, 2)

    decomposer_events = [e for e in adapter.events if e["stage"] == "DECOMPOSER"]
    eval_events = [e for e in adapter.events if e["stage"] in {"CRITIC", "ARBITER", "JUDGE"}]
    critic_events = [e for e in adapter.events if e["stage"] == "CRITIC"]
    judge_events = [e for e in adapter.events if e["stage"] == "JUDGE"]

    decomposer_ms = round(sum(e["elapsed_ms"] for e in decomposer_events), 2)
    parallel_eval_ms = (
        round((max(e["end_perf"] for e in eval_events) - min(e["start_perf"] for e in eval_events)) * 1000.0, 2)
        if eval_events
        else 0.0
    )
    critics_wall_ms = (
        round((max(e["end_perf"] for e in critic_events) - min(e["start_perf"] for e in critic_events)) * 1000.0, 2)
        if critic_events
        else 0.0
    )
    judge_ms = judge_events[-1]["elapsed_ms"] if judge_events else 0.0
    judge_timeout_budget_s = judge_events[-1]["timeout_seconds"] if judge_events else None

    case_out = {
        "index": idx + 1,
        "scenario_id": scenario["scenario_id"],
        "domain": scenario["domain"],
        "learner_level": scenario["learner_level"],
        "valid_proposal": valid_proposal,
        "attempts_used": attempts_used,
        "tasks_count": tasks_count,
        "judge_status": judge_status,
        "judge_skipped": judge_skipped,
        "pedagogical_score": pedagogical_score,
        "judge_timeout_budget_s": judge_timeout_budget_s,
        "decomposer_ms": decomposer_ms,
        "critics_wall_ms": critics_wall_ms,
        "judge_ms": judge_ms,
        "parallel_critics_judge_ms": parallel_eval_ms,
        "total_pipeline_ms": total_ms,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "thinking_tokens": thinking_tokens,
        "error_code": error_code,
    }
    print(
        f"[{idx + 1:02d}/18] {scenario['scenario_id']}: valid={valid_proposal} "
        f"decomp={decomposer_ms/1000:.2f}s parallel={parallel_eval_ms/1000:.2f}s "
        f"(judge={judge_ms/1000:.2f}s/{judge_status}) total={total_ms/1000:.2f}s",
        flush=True,
    )
    return case_out


def _load_group2_milestone_planner_reference() -> dict[str, Any]:
    if not GROUP2_PATH.exists():
        return {"source": "unavailable"}
    data = json.loads(GROUP2_PATH.read_text(encoding="utf-8"))
    low_ab = (data.get("planner_low_vs_medium") or {}).get("low", {}).get("latency_ms", {})
    verify = (data.get("part_c_verify_0_of_3") or {}).get("learning-milestone-planner", {}).get("summary", {}).get("latency_ms", {})
    return {
        "source": str(GROUP2_PATH.relative_to(REPO_ROOT)),
        "planner_low_ab_p50_ms": low_ab.get("p50"),
        "planner_low_ab_p95_ms": low_ab.get("p95"),
        "planner_verify_p50_ms": verify.get("p50"),
        "planner_verify_p95_ms": verify.get("p95"),
    }


async def main() -> None:
    base_url, _ = get_cobhub_config()
    _configure_env(base_url)

    scenarios = load_18_goal_dataset()
    outcomes: list[dict[str, Any]] = []
    for idx, scenario in enumerate(scenarios):
        outcomes.append(await run_scenario(idx, scenario))

    valid_cases = [o for o in outcomes if o["valid_proposal"]]
    judge_real_verdicts = [
        o for o in valid_cases if o["judge_status"] in {"PASSED", "NEEDS_REVIEW"}
    ]
    judge_real_verdict_rate = (
        round(len(judge_real_verdicts) / len(valid_cases), 4) if valid_cases else 0.0
    )

    decomposer_latencies = [o["decomposer_ms"] for o in outcomes if o["decomposer_ms"] > 0]
    critics_latencies = [o["critics_wall_ms"] for o in outcomes if o["critics_wall_ms"] > 0]
    judge_latencies = [o["judge_ms"] for o in outcomes if o["judge_ms"] > 0]
    parallel_latencies = [
        o["parallel_critics_judge_ms"] for o in outcomes if o["parallel_critics_judge_ms"] > 0
    ]
    total_latencies = [o["total_pipeline_ms"] for o in outcomes]

    decomposer_stats = _summarize_ms(decomposer_latencies)
    critics_stats = _summarize_ms(critics_latencies)
    judge_stats = _summarize_ms(judge_latencies)
    parallel_stats = _summarize_ms(parallel_latencies)
    total_stats = _summarize_ms(total_latencies)

    milestone_ref = _load_group2_milestone_planner_reference()
    schedule_gen_p50_s = round(total_stats["p50_ms"] / 1000.0, 2)
    schedule_gen_p95_s = round(total_stats["p95_ms"] / 1000.0, 2)

    report = {
        "schema_version": "1.0",
        "experiment": "group5_judge_parallel_and_pipeline_budget",
        "timestamp": utc_timestamp(),
        "gateway_base_url": base_url,
        "model": "gemini-3.8-flash-low",
        "config": {
            "tier3_judge_timeout_seconds": 8.0,
            "ai_min_judge_remaining_seconds": 3.0,
            "ai_min_critic_remaining_seconds": 6.0,
            "ai_sse_pipeline_timeout_seconds": 55.0,
            "parallel_critics_and_judge": True,
        },
        "dataset_size": len(scenarios),
        "valid_proposals_count": len(valid_cases),
        "judge_verdicts": {
            "PASSED": sum(1 for o in valid_cases if o["judge_status"] == "PASSED"),
            "NEEDS_REVIEW": sum(1 for o in valid_cases if o["judge_status"] == "NEEDS_REVIEW"),
            "REVIEW_PENDING": sum(1 for o in valid_cases if o["judge_status"] == "REVIEW_PENDING"),
            "SKIPPED": sum(1 for o in valid_cases if o["judge_status"] in {"SKIPPED", "SKIPPED_NO_PROPOSAL"}),
            "real_verdict_count": len(judge_real_verdicts),
            "real_verdict_rate": judge_real_verdict_rate,
            "target_rate": 0.80,
            "target_met": judge_real_verdict_rate >= 0.80,
        },
        "pipeline_budget_table": {
            "sse_hard_cap_seconds": 55.0,
            "schedule_generation_total_p50_s": schedule_gen_p50_s,
            "schedule_generation_total_p95_s": schedule_gen_p95_s,
            "schedule_generation_within_55s_budget": schedule_gen_p95_s <= 55.0,
            "stages": {
                "milestone_planner_group2_ref": milestone_ref,
                "task_decomposer": decomposer_stats,
                "dual_critics_wall": critics_stats,
                "tier3_judge": judge_stats,
                "parallel_critics_plus_judge": parallel_stats,
                "schedule_generation_pipeline_total": total_stats,
            },
        },
        "per_case_outcomes": outcomes,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"\nSaved Group 5 report to {OUTPUT_PATH}", flush=True)
    print(
        f"Real Judge verdict rate: {len(judge_real_verdicts)}/{len(valid_cases)} "
        f"({judge_real_verdict_rate * 100:.1f}%), Schedule Gen p50={schedule_gen_p50_s}s, p95={schedule_gen_p95_s}s",
        flush=True,
    )


if __name__ == "__main__":
    asyncio.run(main())
