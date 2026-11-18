"""Experiment 10: Milestone Planner Tool-Calling Rounds Instrumentation vs Server Prefetch A/B.

Compares on the 6 hard goals (`hard_planning_6_goals.jsonl`, clarified with
`clarification_answers` via `_merge_clarification_answers_into_goal`):
  - Arm (a): Current Tool-Calling Planner (`tools=allowed`, `max_tool_calls=4`)
    with per-round GenAI & tool-execution instrumentation.
  - Arm (b): Server Prefetch (`tools=None`, `max_tool_calls=0`), pre-querying
    `InMemoryKnowledgeBaseRepository` (`search_concepts` + `get_prerequisite_graph`)
    and injecting `kb_concepts` + `kb_graphs` via `RoadmapContextBuilder`.

Constraints:
- NEVER modifies production prompts (`roadmap_skills.py`, `prompts.py`, `prompts.lock`).
- NEVER reads/prints secrets, API keys, or PII.
- Executes all cobhub calls (`http://127.0.0.1:8045`) strictly sequentially.

Output:
- `docs/experiments/exp_10_planner_tool_rounds_ab.json`
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any
from uuid import UUID

from common import (
    BACKEND_DIR,
    extract_response_telemetry,
    get_cobhub_config,
    sanitize_error_message,
    summarize_numeric,
    utc_timestamp,
    write_experiment_json,
)
from src.planning.application.dtos.planning_dtos import (
    ClarificationQuestionsLLMOutput,
    MilestoneGenerationLLMOutput,
)
from src.planning.application.services.knowledge_tool_dispatcher import (
    KnowledgeToolDispatcher,
    RoadmapPipelineStage,
)
from src.planning.application.services.roadmap_context_builder import (
    RoadmapContextBuilder,
)
from src.planning.application.services.roadmap_skills import (
    MILESTONE_PLANNER_SKILL,
    build_milestone_planner_prompt,
    build_planning_prompt_registry,
)
from src.planning.application.services.validation_gate import (
    ProposalValidationGateOrchestrator,
)
from src.planning.domain.models.goal import Goal
from src.planning.domain.models.knowledge_concept import (
    ConceptPrerequisiteGraph,
    LearningConcept,
)
from src.planning.domain.models.roadmap import Roadmap
from src.planning.infrastructure.repositories.sqlalchemy_knowledge_base_repository import (
    InMemoryKnowledgeBaseRepository,
)
from src.shared_kernel.application.harness.execution_manager import AIExecutionManager
from src.shared_kernel.config import get_settings
from src.shared_kernel.domain.base import generate_uuid7
from src.shared_kernel.infrastructure.external_ai.litellm_adapter import LiteLLMAdapter
from tests.ai_evals.eval_runner import _merge_clarification_answers_into_goal

OUTPUT_FILENAME = "exp_10_planner_tool_rounds_ab.json"
HARD_DATASET_PATH = BACKEND_DIR / "tests" / "ai_evals" / "datasets" / "hard_planning_6_goals.jsonl"


def _configure_env(base_url: str, api_key: str, *, timeout_seconds: float) -> None:
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
    hard_cap = max(120.0, timeout_seconds + 30.0)
    os.environ["AI_HARD_TIMEOUT_SECONDS"] = str(hard_cap)
    os.environ["AI_SSE_PIPELINE_TIMEOUT_SECONDS"] = str(hard_cap)
    os.environ["AI_MILESTONE_PLANNER_TIMEOUT_SECONDS"] = str(timeout_seconds)
    os.environ["AI_TOOL_CALL_TIMEOUT_SECONDS"] = "45.0"
    get_settings.cache_clear()


def _load_hard_scenarios(
    dataset_path: Path = HARD_DATASET_PATH,
) -> list[dict[str, Any]]:
    scenarios: list[dict[str, Any]] = []
    for raw_line in dataset_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line:
            scenarios.append(json.loads(line))
    return scenarios


def _build_clarified_goal_and_roadmap(
    scenario: dict[str, Any],
    *,
    user_id: UUID,
) -> tuple[Goal, Roadmap, str]:
    start_d = date.fromisoformat(str(scenario["start_date"]))
    target_d = date.fromisoformat(str(scenario["target_date"]))
    goal_data = scenario["goal"]
    goal = Goal(
        id=generate_uuid7(),
        user_id=user_id,
        title=str(goal_data.get("title", "")),
        raw_description=str(goal_data.get("raw_description", "")),
        target_date=target_d,
        prior_knowledge_level=str(scenario.get("learner_level", "INTERMEDIATE")),
    )
    clar_summary = _merge_clarification_answers_into_goal(
        goal,
        scenario,
        ClarificationQuestionsLLMOutput(questions=[]),
    )
    roadmap = Roadmap(
        id=generate_uuid7(),
        user_id=user_id,
        goal_id=goal.id,
        title=goal.title,
        description=goal.raw_description,
        start_date=start_d,
        target_date=target_d,
    )
    return goal, roadmap, clar_summary


def _extract_fc_requests(resp: Any) -> list[dict[str, Any]]:
    fn_calls = list(getattr(resp, "function_calls", None) or [])
    if not fn_calls:
        candidates = getattr(resp, "candidates", None) or []
        model_content = getattr(candidates[0], "content", None) if candidates else None
        for part in getattr(model_content, "parts", None) or []:
            part_fc = getattr(part, "function_call", None)
            if part_fc is not None:
                fn_calls.append(part_fc)
    extracted: list[dict[str, Any]] = []
    for fc in fn_calls:
        raw_args = getattr(fc, "args", None) or {}
        extracted.append(
            {
                "name": str(getattr(fc, "name", "") or ""),
                "args": dict(raw_args) if isinstance(raw_args, dict) else {},
            }
        )
    return extracted


class _InstrumentedPlannerAdapter(LiteLLMAdapter):
    """Subclass capturing exact per-round GenAI telemetry without altering production code."""

    def __init__(self) -> None:
        super().__init__()
        self.rounds: list[dict[str, Any]] = []
        self._non_tool_turns = 0

    def build_google_genai_client(self, api_key: str, base_url: str) -> Any:  # type: ignore[override]
        client = super().build_google_genai_client(api_key, base_url)
        models_obj = client.aio.models
        orig_generate_content = models_obj.generate_content
        adapter_self = self

        async def _wrapped_generate_content(*, model: str, contents: Any, config: Any) -> Any:
            has_tools = bool(getattr(config, "tools", None))
            if has_tools:
                turn_type = "tool_round"
            else:
                adapter_self._non_tool_turns += 1
                turn_type = "final_json" if adapter_self._non_tool_turns == 1 else "schema_repair"

            t0 = time.perf_counter()
            resp = await orig_generate_content(model=model, contents=contents, config=config)
            llm_latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            telemetry = extract_response_telemetry(resp, model)
            fc_requests = _extract_fc_requests(resp)
            adapter_self.rounds.append(
                {
                    "round_index": len(adapter_self.rounds) + 1,
                    "turn_type": turn_type,
                    "requested_model": model,
                    "actual_model_id": telemetry["actual_model_id"],
                    "llm_latency_ms": llm_latency_ms,
                    "function_calls_requested": fc_requests,
                    "tool_exec_latencies": [],
                    "prompt_tokens": telemetry["prompt_tokens"],
                    "output_tokens": telemetry["candidate_tokens"],
                    "thinking_tokens": telemetry["thinking_tokens"],
                    "finish_reason": telemetry["finish_reason"],
                }
            )
            return resp

        models_obj.generate_content = _wrapped_generate_content  # type: ignore[method-assign]
        return client


def _count_tool_results(tool_name: str, output: dict[str, Any]) -> int:
    if tool_name == "search_learning_concepts":
        return int(output.get("count", len(output.get("concepts", []) or [])))
    if tool_name == "get_concept_prerequisite_graph":
        return len(output.get("nodes", []) or [])
    if tool_name == "get_learning_resources_and_guidance":
        return int(output.get("count", len(output.get("resources", []) or [])))
    return int(output.get("count", 0) or 0)


def _validate_milestones_output(
    raw_value: Any,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    parsed = (
        raw_value
        if isinstance(raw_value, MilestoneGenerationLLMOutput)
        else MilestoneGenerationLLMOutput.model_validate(raw_value)
    )
    sorted_items = sorted(parsed.milestones, key=lambda item: int(item.sequence_order))
    raw_dicts = [item.model_dump(mode="json") for item in sorted_items]
    violations = ProposalValidationGateOrchestrator.validate_ai_milestones_tier1(raw_dicts)
    serialized = [v.to_dict() for v in violations]
    payload = parsed.model_dump(mode="json")
    return raw_dicts, serialized, payload


async def _run_arm_a_tool_calling(
    *,
    scenario: dict[str, Any],
    planner_tpl: Any,
    kb_repo: InMemoryKnowledgeBaseRepository,
    timeout_seconds: float,
) -> dict[str, Any]:
    user_id = generate_uuid7()
    goal, roadmap, _ = _build_clarified_goal_and_roadmap(scenario, user_id=user_id)
    context_block = RoadmapContextBuilder.build_milestone_planning_context(
        goal=goal,
        roadmap=roadmap,
    )
    user_prompt = build_milestone_planner_prompt(
        context_block,
        generation_strategy="FULL_SCOPE",
    )

    dispatcher = KnowledgeToolDispatcher(
        kb_repo,
        stage=RoadmapPipelineStage.MILESTONE_PLANNING,
        max_tool_calls=MILESTONE_PLANNER_SKILL.max_tool_calls,
        timeout_seconds=10.0,
    )
    adapter = _InstrumentedPlannerAdapter()

    async def _instrumented_tool_executor(
        tool_name: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        t0 = time.perf_counter()
        out = await dispatcher.dispatch(tool_name, arguments)
        exec_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        entry = {
            "tool_name": tool_name,
            "latency_ms": exec_ms,
            "result_count": _count_tool_results(tool_name, out),
        }
        if adapter.rounds:
            adapter.rounds[-1]["tool_exec_latencies"].append(entry)
        return out

    mgr = AIExecutionManager(
        provider=adapter,
        manage_quota=False,
        max_retries=0,
        timeout_seconds=timeout_seconds,
        tool_call_timeout_seconds=45.0,
    )

    t0 = time.perf_counter()
    ok = False
    error: str | None = None
    milestones_dicts: list[dict[str, Any]] = []
    tier1_violations: list[dict[str, Any]] = []
    payload: dict[str, Any] = {}
    prompt_tokens = 0
    output_tokens = 0
    thinking_tokens = 0
    model_id = ""
    repair_attempts = 0

    try:
        exec_res = await mgr.execute(
            user_id=user_id,
            operation_type="MILESTONE_GEN_TOOL_AB",
            system_prompt=planner_tpl.system_template,
            user_prompt=user_prompt,
            response_schema=MilestoneGenerationLLMOutput,
            model_name=getattr(adapter, "model_identifier", "gemini-3.8-flash"),
            tools=dispatcher.get_allowed_tool_declarations(),
            tool_executor=_instrumented_tool_executor,
            max_tool_calls=MILESTONE_PLANNER_SKILL.max_tool_calls,
            thinking_level=MILESTONE_PLANNER_SKILL.thinking_level,
            prompt_template=planner_tpl,
        )
        prompt_tokens = int(exec_res.prompt_tokens or 0)
        output_tokens = int(exec_res.completion_tokens or 0)
        thinking_tokens = int(exec_res.thinking_tokens or 0)
        model_id = str(exec_res.model_id or "")
        repair_attempts = int(exec_res.repair_attempts or 0)
        milestones_dicts, tier1_violations, payload = _validate_milestones_output(exec_res.value)
        ok = len(milestones_dicts) > 0 and len(tier1_violations) == 0
    except Exception as exc:  # noqa: BLE001
        error = sanitize_error_message(exc)
        prompt_tokens = sum(r.get("prompt_tokens", 0) for r in adapter.rounds)
        output_tokens = sum(
            r.get("output_tokens", 0) + r.get("thinking_tokens", 0) for r in adapter.rounds
        )
        thinking_tokens = sum(r.get("thinking_tokens", 0) for r in adapter.rounds)

    wall_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    tool_rounds_count = sum(1 for r in adapter.rounds if r["turn_type"] == "tool_round")
    return {
        "arm": "a_tool_calling",
        "ok": ok,
        "error": error,
        "wall_ms": wall_ms,
        "model_id": model_id,
        "thinking_level": MILESTONE_PLANNER_SKILL.thinking_level,
        "max_tool_calls": MILESTONE_PLANNER_SKILL.max_tool_calls,
        "total_rounds": len(adapter.rounds),
        "tool_rounds_count": tool_rounds_count,
        "tool_calls_executed": dispatcher.call_count,
        "repair_attempts": repair_attempts,
        "prompt_tokens": prompt_tokens,
        "output_tokens": output_tokens,
        "thinking_tokens": thinking_tokens,
        "milestones_count": len(milestones_dicts),
        "tier1_valid": len(tier1_violations) == 0 and len(milestones_dicts) > 0,
        "tier1_violations": tier1_violations,
        "rounds": adapter.rounds,
        "milestones": milestones_dicts,
        "scope_summary": payload.get("scope_summary", ""),
        "deferred_scope": payload.get("deferred_scope", []),
    }


async def _prefetch_kb_evidence(
    kb_repo: InMemoryKnowledgeBaseRepository,
    *,
    goal: Goal,
    domain: str | None,
) -> tuple[list[LearningConcept], list[ConceptPrerequisiteGraph], float]:
    t0 = time.perf_counter()
    query_text = f"{goal.title} {goal.raw_description or ''}".strip()[:200]
    concepts = await kb_repo.search_concepts(
        query=query_text,
        domain=domain,
        learner_level=goal.prior_knowledge_level,
        limit=10,
    )
    if not concepts and domain:
        concepts = await kb_repo.search_concepts(
            query=query_text,
            domain=None,
            learner_level=goal.prior_knowledge_level,
            limit=10,
        )
    graphs: list[ConceptPrerequisiteGraph] = []
    if concepts:
        graph = await kb_repo.get_prerequisite_graph(
            concept_ids=[c.concept_id for c in concepts],
            max_depth=3,
        )
        graphs.append(graph)
    prefetch_latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    return concepts, graphs, prefetch_latency_ms


async def _run_arm_b_server_prefetch(
    *,
    scenario: dict[str, Any],
    planner_tpl: Any,
    kb_repo: InMemoryKnowledgeBaseRepository,
    timeout_seconds: float,
) -> dict[str, Any]:
    user_id = generate_uuid7()
    goal, roadmap, _ = _build_clarified_goal_and_roadmap(scenario, user_id=user_id)
    domain = str(scenario.get("domain") or "").strip() or None

    total_t0 = time.perf_counter()
    kb_concepts, kb_graphs, prefetch_latency_ms = await _prefetch_kb_evidence(
        kb_repo,
        goal=goal,
        domain=domain,
    )

    context_block = RoadmapContextBuilder.build_milestone_planning_context(
        goal=goal,
        roadmap=roadmap,
        kb_concepts=kb_concepts,
        kb_graphs=kb_graphs,
    )
    user_prompt = build_milestone_planner_prompt(
        context_block,
        generation_strategy="FULL_SCOPE",
    )

    adapter = _InstrumentedPlannerAdapter()
    mgr = AIExecutionManager(
        provider=adapter,
        manage_quota=False,
        max_retries=0,
        timeout_seconds=timeout_seconds,
        tool_call_timeout_seconds=45.0,
    )

    llm_t0 = time.perf_counter()
    ok = False
    error: str | None = None
    milestones_dicts: list[dict[str, Any]] = []
    tier1_violations: list[dict[str, Any]] = []
    payload: dict[str, Any] = {}
    prompt_tokens = 0
    output_tokens = 0
    thinking_tokens = 0
    model_id = ""
    repair_attempts = 0

    try:
        exec_res = await mgr.execute(
            user_id=user_id,
            operation_type="MILESTONE_GEN_PREFETCH_AB",
            system_prompt=planner_tpl.system_template,
            user_prompt=user_prompt,
            response_schema=MilestoneGenerationLLMOutput,
            model_name=getattr(adapter, "model_identifier", "gemini-3.8-flash"),
            tools=None,
            tool_executor=None,
            max_tool_calls=0,
            thinking_level=MILESTONE_PLANNER_SKILL.thinking_level,
            prompt_template=planner_tpl,
        )
        prompt_tokens = int(exec_res.prompt_tokens or 0)
        output_tokens = int(exec_res.completion_tokens or 0)
        thinking_tokens = int(exec_res.thinking_tokens or 0)
        model_id = str(exec_res.model_id or "")
        repair_attempts = int(exec_res.repair_attempts or 0)
        milestones_dicts, tier1_violations, payload = _validate_milestones_output(exec_res.value)
        ok = len(milestones_dicts) > 0 and len(tier1_violations) == 0
    except Exception as exc:  # noqa: BLE001
        error = sanitize_error_message(exc)
        prompt_tokens = sum(r.get("prompt_tokens", 0) for r in adapter.rounds)
        output_tokens = sum(
            r.get("output_tokens", 0) + r.get("thinking_tokens", 0) for r in adapter.rounds
        )
        thinking_tokens = sum(r.get("thinking_tokens", 0) for r in adapter.rounds)

    llm_latency_ms = round((time.perf_counter() - llm_t0) * 1000.0, 2)
    total_ms = round((time.perf_counter() - total_t0) * 1000.0, 2)
    return {
        "arm": "b_server_prefetch",
        "ok": ok,
        "error": error,
        "prefetch_latency_ms": prefetch_latency_ms,
        "llm_latency_ms": llm_latency_ms,
        "total_ms": total_ms,
        "prefetched_concept_ids": [c.concept_id for c in kb_concepts],
        "prefetched_edges_count": sum(len(g.edges) for g in kb_graphs),
        "model_id": model_id,
        "thinking_level": MILESTONE_PLANNER_SKILL.thinking_level,
        "max_tool_calls": 0,
        "repair_attempts": repair_attempts,
        "prompt_tokens": prompt_tokens,
        "output_tokens": output_tokens,
        "thinking_tokens": thinking_tokens,
        "milestones_count": len(milestones_dicts),
        "tier1_valid": len(tier1_violations) == 0 and len(milestones_dicts) > 0,
        "tier1_violations": tier1_violations,
        "rounds": adapter.rounds,
        "milestones": milestones_dicts,
        "scope_summary": payload.get("scope_summary", ""),
        "deferred_scope": payload.get("deferred_scope", []),
    }


def _summarize_results(rows: list[dict[str, Any]]) -> dict[str, Any]:
    arm_a = [r["arm_a_tool_calling"] for r in rows]
    arm_b = [r["arm_b_server_prefetch"] for r in rows]

    a_walls = [float(x["wall_ms"]) for x in arm_a]
    b_totals = [float(x["total_ms"]) for x in arm_b]
    b_prefetch = [float(x["prefetch_latency_ms"]) for x in arm_b]
    a_rounds = [float(x["total_rounds"]) for x in arm_a]
    a_tool_calls = [float(x["tool_calls_executed"]) for x in arm_a]
    tool_round_latencies = [
        float(rnd["llm_latency_ms"])
        for x in arm_a
        for rnd in x.get("rounds", [])
        if rnd.get("turn_type") == "tool_round"
    ]
    final_round_latencies = [
        float(rnd["llm_latency_ms"])
        for x in arm_a
        for rnd in x.get("rounds", [])
        if rnd.get("turn_type") == "final_json"
    ]
    tool_name_counts = Counter(
        tc["tool_name"]
        for x in arm_a
        for rnd in x.get("rounds", [])
        for tc in rnd.get("tool_exec_latencies", [])
    )

    a_p50 = summarize_numeric(a_walls)["p50"]
    b_p50 = summarize_numeric(b_totals)["p50"]
    speedup_p50 = round(a_p50 / b_p50, 3) if b_p50 > 0 else 0.0

    return {
        "goals_count": len(rows),
        "arm_a_tool_calling": {
            "ok_count": sum(1 for x in arm_a if x["ok"]),
            "tier1_valid_count": sum(1 for x in arm_a if x["tier1_valid"]),
            "wall_ms": summarize_numeric(a_walls),
            "rounds_per_goal": summarize_numeric(a_rounds),
            "tool_calls_per_goal": summarize_numeric(a_tool_calls),
            "tool_round_llm_ms": summarize_numeric(tool_round_latencies),
            "final_json_llm_ms": summarize_numeric(final_round_latencies),
            "tool_exec_counts": dict(tool_name_counts),
            "prompt_tokens_total": sum(int(x["prompt_tokens"]) for x in arm_a),
            "output_tokens_total": sum(int(x["output_tokens"]) for x in arm_a),
            "thinking_tokens_total": sum(int(x["thinking_tokens"]) for x in arm_a),
        },
        "arm_b_server_prefetch": {
            "ok_count": sum(1 for x in arm_b if x["ok"]),
            "tier1_valid_count": sum(1 for x in arm_b if x["tier1_valid"]),
            "prefetch_latency_ms": summarize_numeric(b_prefetch),
            "total_ms": summarize_numeric(b_totals),
            "llm_latency_ms": summarize_numeric([float(x["llm_latency_ms"]) for x in arm_b]),
            "prompt_tokens_total": sum(int(x["prompt_tokens"]) for x in arm_b),
            "output_tokens_total": sum(int(x["output_tokens"]) for x in arm_b),
            "thinking_tokens_total": sum(int(x["thinking_tokens"]) for x in arm_b),
        },
        "p50_speedup_a_over_b": speedup_p50,
    }


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Exp 10: Milestone Planner Tool-Calling Rounds vs Server Prefetch A/B",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=120.0,
        help="Planner call timeout budget in seconds (default: 120.0).",
    )
    args = parser.parse_args()

    base_url, api_key = get_cobhub_config()
    _configure_env(base_url, api_key, timeout_seconds=args.timeout_seconds)

    scenarios = _load_hard_scenarios()
    planner_tpl = build_planning_prompt_registry().latest(MILESTONE_PLANNER_SKILL.skill_id)
    kb_repo = InMemoryKnowledgeBaseRepository()

    results: list[dict[str, Any]] = []
    for idx, scenario in enumerate(scenarios, start=1):
        sid = str(scenario["scenario_id"])
        print(f"\n=== [{idx}/{len(scenarios)}] {sid} ===", flush=True)

        arm_a = await _run_arm_a_tool_calling(
            scenario=scenario,
            planner_tpl=planner_tpl,
            kb_repo=kb_repo,
            timeout_seconds=args.timeout_seconds,
        )
        print(
            f"  Arm (a) tool-calling: ok={arm_a['ok']} wall={arm_a['wall_ms']}ms "
            f"rounds={arm_a['total_rounds']} tools={arm_a['tool_calls_executed']} "
            f"ms={arm_a['milestones_count']}",
            flush=True,
        )

        arm_b = await _run_arm_b_server_prefetch(
            scenario=scenario,
            planner_tpl=planner_tpl,
            kb_repo=kb_repo,
            timeout_seconds=args.timeout_seconds,
        )
        print(
            f"  Arm (b) server-prefetch: ok={arm_b['ok']} prefetch={arm_b['prefetch_latency_ms']}ms "
            f"llm={arm_b['llm_latency_ms']}ms total={arm_b['total_ms']}ms "
            f"ms={arm_b['milestones_count']}",
            flush=True,
        )

        results.append(
            {
                "scenario_id": sid,
                "domain": scenario.get("domain"),
                "learner_level": scenario.get("learner_level"),
                "arm_a_tool_calling": arm_a,
                "arm_b_server_prefetch": arm_b,
            }
        )

    report = {
        "schema_version": "1.0",
        "experiment": "exp_10_planner_tool_rounds_ab",
        "timestamp": utc_timestamp(),
        "gateway_base_url": base_url,
        "thinking_level": MILESTONE_PLANNER_SKILL.thinking_level,
        "timeout_seconds": args.timeout_seconds,
        "summary": _summarize_results(results),
        "scenarios": results,
    }
    out_path = write_experiment_json(OUTPUT_FILENAME, report)
    print(f"\nSaved Exp 10 report to {out_path}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
