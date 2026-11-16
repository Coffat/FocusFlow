"""Offline/Live AI Planning Evaluation Runner (T0.2).

Measures pass@1, post-retry recovery, average retries, prompt/output/thinking tokens,
latency p50/p95, judge timeout rate, weekly review fallback rate, faithfulness, and
prompt-injection isolation across the 18-goal evaluation dataset without persisting PII.
"""

from __future__ import annotations

import asyncio
import json
import math
import os
import time
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from src.evaluation.application.dtos.intelligence import GenerateWeeklyReviewRequestDTO
from src.evaluation.application.use_cases.intelligence import GenerateWeeklyReviewUseCase
from src.evaluation.domain.models.intelligence import WeeklyReview
from src.evaluation.domain.services import QuantitativeFaithfulnessValidator
from src.planning.application.dtos.planning_dtos import TaskProposalLLMOutput
from src.planning.application.services.roadmap_skills import (
    TASK_DECOMPOSER_SKILL,
    build_planning_prompt_registry,
)
from src.planning.application.services.validation_gate import ProposalValidationGateOrchestrator
from src.planning.domain.exceptions.planning_exceptions import ProposalValidationGateError
from src.planning.domain.services.validation_types import (
    AvailabilityConfigurationDTO,
    AvailabilitySlotDTO,
)
from src.shared_kernel.application.llm_port import LLMGenerationResult, LLMProviderPort
from src.shared_kernel.infrastructure.external_ai.litellm_adapter import LiteLLMAdapter
from src.shared_kernel.infrastructure.external_ai.prompt_sanitizer import PromptSanitizer
from tests.helpers.llm_stubs import StubLLMAdapter

DEFAULT_18_GOALS_DATASET_PATH = (
    Path(__file__).resolve().parent / "datasets" / "golden_planning_18_goals.jsonl"
)


def load_18_goal_dataset(
    dataset_path: Path = DEFAULT_18_GOALS_DATASET_PATH,
) -> list[dict[str, Any]]:
    """Load the 18-goal deterministic evaluation JSONL dataset."""
    lines = [
        line.strip()
        for line in dataset_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return [json.loads(line) for line in lines]


def _percentile(sorted_values: list[float], pct: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return round(sorted_values[0], 3)
    rank = (len(sorted_values) - 1) * (pct / 100.0)
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return round(sorted_values[low], 3)
    weight = rank - low
    interpolated = sorted_values[low] * (1.0 - weight) + sorted_values[high] * weight
    return round(interpolated, 3)


def _build_availability(raw: dict[str, Any]) -> AvailabilityConfigurationDTO:
    mode_str = str(raw.get("mode", "MODE_A")).upper()
    slots = tuple(
        AvailabilitySlotDTO(
            day_of_week=str(slot.get("day_of_week", "monday")).lower(),
            start_time=str(slot.get("start_time", "19:00")),
            end_time=str(slot.get("end_time", "21:00")),
            end_day_offset=int(slot.get("end_day_offset", 0) or 0),
            is_active=bool(slot.get("is_active", True)),
        )
        for slot in raw.get("availability_slots", [])
        if isinstance(slot, dict)
    )
    return AvailabilityConfigurationDTO(
        mode=mode_str,
        daily_quota_minutes={
            str(k).lower(): int(v) for k, v in dict(raw.get("daily_quota_minutes", {})).items()
        },
        default_daily_quota_minutes=int(raw.get("default_daily_quota_minutes", 90)),
        availability_slots=slots,
        disabled_weekdays=frozenset(str(d).lower() for d in raw.get("disabled_weekdays", [])),
    )


class _SlowJudgeStub(LLMProviderPort):
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
    ) -> LLMGenerationResult:
        del (
            system_prompt,
            user_prompt,
            response_schema,
            tools,
            tool_executor,
            max_tool_calls,
            thinking_level,
        )
        await asyncio.sleep(0.05)
        return LLMGenerationResult(payload={"score": 90, "issues": []})

    async def stream_structured(
        self, *, system_prompt: str, user_prompt: str
    ) -> AsyncIterator[str]:
        del system_prompt, user_prompt
        yield "{}"


class _EvalWeeklyRepo:
    def __init__(self, roadmap_id: UUID) -> None:
        self._roadmap_id = roadmap_id
        self.last_model_used: str = ""

    async def create_weekly_review(
        self,
        *,
        roadmap_id: UUID,
        user_id: UUID,
        period_start: date,
        period_end: date,
        reflection: dict[str, Any],
    ) -> WeeklyReview:
        return WeeklyReview(
            id=uuid4(),
            user_id=user_id,
            roadmap_id=roadmap_id,
            period_start=period_start,
            period_end=period_end,
            quantitative_summary={"completed_sessions": 4, "total_days": 7},
            user_reflection_payload=reflection,
            strengths_feedback="Hoàn thành 4 phiên học trong chu kỳ 7 ngày.",
            bottlenecks_feedback="Cần duy trì nhịp ổn định vào cuối tuần.",
            action_recommendations="Ưu tiên 1 phiên Prove Mode cho cột mốc hiện tại.",
            generated_at=datetime.now(UTC),
        )

    async def save_weekly_review(
        self,
        review: WeeklyReview,
        *,
        model_used: str = "deterministic-fallback",
    ) -> None:
        del review
        self.last_model_used = model_used


class _EvalWeeklyMetricsPort:
    async def get_roadmap_period_metrics(self, **kwargs: Any) -> Any:
        del kwargs
        from src.execution.public_api import WeeklyExecutionMetricsDTO

        return WeeklyExecutionMetricsDTO(
            completed_minutes=180,
            planned_minutes=240,
            completed_sessions_count=4,
            completed_tasks_count=3,
            planned_tasks_count=4,
            overdue_tasks_count=0,
            adherence_rate_pct=75.0,
        )


class _EvalOwnership:
    async def roadmap_belongs_to(self, roadmap_id: UUID, user_id: UUID) -> bool:
        del roadmap_id, user_id
        return True


class _EvalUoW:
    async def commit(self) -> None:
        return None

    async def close(self) -> None:
        return None


class _FailingWeeklyLLM(LLMProviderPort):
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
    ) -> LLMGenerationResult:
        del (
            system_prompt,
            user_prompt,
            response_schema,
            tools,
            tool_executor,
            max_tool_calls,
            thinking_level,
        )
        raise TimeoutError("Simulated weekly review timeout")

    async def stream_structured(
        self, *, system_prompt: str, user_prompt: str
    ) -> AsyncIterator[str]:
        del system_prompt, user_prompt
        yield "{}"


async def run_planning_eval_suite(
    dataset_path: Path = DEFAULT_18_GOALS_DATASET_PATH,
    *,
    trials_per_goal: int = 3,
    output_path: Path | None = None,
    live: bool | None = None,
) -> dict[str, Any]:
    """Run the 18-goal evaluation benchmark and return a PII-free metrics artifact."""
    scenarios = load_18_goal_dataset(dataset_path)
    use_live = bool(os.getenv("RUN_LIVE_AI_EVALS") == "1") if live is None else live
    effective_trials = max(1, trials_per_goal)

    decomposer_tpl = build_planning_prompt_registry().latest(TASK_DECOMPOSER_SKILL.skill_id)

    latencies_ms: list[float] = []
    per_case_outcomes: list[dict[str, Any]] = []
    weekly_faithfulness_scores: list[float] = []

    total_runs = 0
    pass_at_1_count = 0
    recovered_count = 0
    total_retries = 0
    prompt_tokens_total = 0
    output_tokens_total = 0
    thinking_tokens_total = 0
    judge_checks = 0
    judge_timeouts = 0
    weekly_checks = 0
    weekly_fallbacks = 0
    injection_cases = 0
    injection_isolated = 0

    for idx, scenario in enumerate(scenarios):
        availability = _build_availability(scenario["availability"])
        milestones = list(scenario["milestones"])
        valid_milestone_ids = {UUID(str(m["milestone_id"])) for m in milestones}
        milestone_json = json.dumps(
            [
                {
                    "milestone_id": m["milestone_id"],
                    "sequence_order": m["sequence_order"],
                    "title": m["title"],
                    "required_concepts": m.get("required_concepts", []),
                    "learning_outcomes": m.get("learning_outcomes", []),
                    "estimated_effort_minutes": m.get("estimated_effort_minutes", 120),
                }
                for m in milestones
            ],
            ensure_ascii=False,
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
            f"approved_milestones={milestone_json}\n"
            f"skill=learning-task-decomposer"
        )

        case_latencies: list[float] = []
        case_passed = False
        case_attempts = 1
        case_p_tok = 0
        case_o_tok = 0
        case_t_tok = 0
        case_error: str | None = None
        case_judge_status = "PASS"
        case_weekly_fallback = False
        case_weekly_faithfulness = 1.0
        case_injection_ok = True
        last_valid_proposal: dict[str, Any] = {}

        for trial in range(effective_trials):
            total_runs += 1
            provider: LLMProviderPort = LiteLLMAdapter() if use_live else StubLLMAdapter()
            orchestrator = ProposalValidationGateOrchestrator(
                llm_provider=provider,
                enable_tier3_judge=False,
            )
            t0 = time.perf_counter()
            proposal: dict[str, Any] = {}
            attempts_used = 1
            retries_used = 0
            p_tok = 0
            o_tok = 0
            t_tok = 0
            passed = False
            trial_error: str | None = None

            try:
                gate_result = await orchestrator.generate_and_validate_proposal_with_retry(
                    system_prompt=decomposer_tpl.system_template,
                    user_prompt=user_prompt,
                    response_schema=TaskProposalLLMOutput.model_json_schema(),
                    availability=availability,
                    valid_milestone_ids=valid_milestone_ids,
                    start_date=date.fromisoformat(str(scenario["start_date"])),
                    current_roadmap_target_date=date.fromisoformat(str(scenario["target_date"])),
                    goal_title=str(scenario["goal"].get("title", "")),
                    thinking_level=TASK_DECOMPOSER_SKILL.thinking_level,
                    deterministic_allocation=True,
                    max_retries=2,
                    prompt_template=decomposer_tpl,
                )
                attempts_used = max(1, int(gate_result.attempts_used))
                retries_used = max(0, attempts_used - 1)
                p_tok = int(gate_result.total_prompt_tokens or 0)
                o_tok = int(gate_result.total_completion_tokens or 0)
                t_tok = int(gate_result.total_thinking_tokens or 0)
                proposal = gate_result.validated_proposal_data or {}
                passed = (
                    gate_result.is_valid
                    and len(gate_result.violations) == 0
                    and len(proposal.get("tasks", []))
                    >= int(scenario["expected_invariants"].get("min_tasks", 1))
                )
            except ProposalValidationGateError as exc:
                attempts_used = 3
                retries_used = 2
                trial_error = exc.code
            except Exception as exc:
                attempts_used = 1
                retries_used = 0
                trial_error = type(exc).__name__

            elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 3)
            latencies_ms.append(elapsed_ms)
            case_latencies.append(elapsed_ms)

            total_retries += retries_used
            prompt_tokens_total += p_tok
            output_tokens_total += o_tok
            thinking_tokens_total += t_tok

            if passed and retries_used == 0:
                pass_at_1_count += 1
            if passed:
                recovered_count += 1
            if proposal.get("tasks"):
                last_valid_proposal = proposal

            # Check prompt injection containment: forbidden strings never leak into generated proposal tasks
            serialized_proposal = json.dumps(proposal, ensure_ascii=False)
            for forbidden in scenario["expected_invariants"].get("forbidden_substrings", []):
                if forbidden.lower() in serialized_proposal.lower():
                    case_injection_ok = False

            if trial == 0:
                case_passed = passed
                case_attempts = attempts_used
                case_p_tok = p_tok
                case_o_tok = o_tok
                case_t_tok = t_tok
                case_error = trial_error

        # Tier 3 Pedagogical Judge (PEDAGOGICAL_JUDGE_SKILL via execute_tier3_pedagogical_judge)
        if use_live:
            if last_valid_proposal.get("tasks"):
                judge_checks += 1
                judge_orch = ProposalValidationGateOrchestrator(
                    llm_provider=LiteLLMAdapter(),
                    enable_tier3_judge=True,
                    tier3_timeout_seconds=8.0,
                )
                try:
                    (
                        _skipped,
                        _score,
                        _warn,
                        judge_status,
                    ) = await judge_orch.run_tier3_pedagogical_judge(
                        last_valid_proposal,
                        goal_title=str(scenario["goal"].get("title", "")),
                    )
                    case_judge_status = judge_status
                    if judge_status == "REVIEW_PENDING":
                        judge_timeouts += 1
                    prompt_tokens_total += judge_orch._last_judge_prompt_tokens
                    output_tokens_total += judge_orch._last_judge_completion_tokens
                    thinking_tokens_total += judge_orch._last_judge_thinking_tokens
                    case_p_tok += judge_orch._last_judge_prompt_tokens
                    case_o_tok += judge_orch._last_judge_completion_tokens
                    case_t_tok += judge_orch._last_judge_thinking_tokens
                except Exception:
                    case_judge_status = "REVIEW_PENDING"
                    judge_timeouts += 1
            else:
                case_judge_status = "SKIPPED_NO_PROPOSAL"
        else:
            judge_checks += 1
            if idx % 6 == 0:
                judge_orch = ProposalValidationGateOrchestrator(
                    llm_provider=_SlowJudgeStub(),
                    enable_tier3_judge=True,
                    tier3_timeout_seconds=0.01,
                )
            else:
                judge_orch = ProposalValidationGateOrchestrator(
                    llm_provider=StubLLMAdapter(),
                    enable_tier3_judge=True,
                    tier3_timeout_seconds=5.0,
                )
            _skipped, _score, _warn, judge_status = await judge_orch.run_tier3_pedagogical_judge(
                last_valid_proposal or {"tasks": []},
                goal_title=str(scenario["goal"].get("title", "")),
            )
            case_judge_status = judge_status
            if judge_status == "REVIEW_PENDING":
                judge_timeouts += 1

        # Weekly Review evaluation (real LiteLLMAdapter in live mode + quantitative faithfulness)
        weekly_checks += 1
        roadmap_uuid = uuid4()
        weekly_repo = _EvalWeeklyRepo(roadmap_uuid)
        weekly_llm: LLMProviderPort = (
            LiteLLMAdapter()
            if use_live
            else (_FailingWeeklyLLM() if idx % 5 == 0 else StubLLMAdapter())
        )
        weekly_uc = GenerateWeeklyReviewUseCase(
            repository=weekly_repo,  # type: ignore[arg-type]
            ownership=_EvalOwnership(),  # type: ignore[arg-type]
            uow=_EvalUoW(),  # type: ignore[arg-type]
            execution_metrics_port=_EvalWeeklyMetricsPort(),
            llm_provider=weekly_llm,
        )
        try:
            weekly_res = await weekly_uc.execute(
                user_id=uuid4(),
                request=GenerateWeeklyReviewRequestDTO(
                    roadmap_id=roadmap_uuid,
                    period_start=date(2026, 11, 2),
                    period_end=date(2026, 11, 9),
                    reflection={"summary": "eval"},
                ),
            )
            if use_live:
                case_weekly_fallback = weekly_repo.last_model_used in (
                    "deterministic-fallback",
                    "deterministic-insufficient-data",
                )
            else:
                case_weekly_fallback = (
                    idx % 5 == 0 and "4 phiên học" in weekly_res.strengths_feedback
                )
            if case_weekly_fallback:
                weekly_fallbacks += 1

            allowed_numbers = [
                float(val)
                for val in weekly_res.quantitative_summary.values()
                if isinstance(val, (int, float)) and not isinstance(val, bool)
            ]
            case_weekly_faithfulness = QuantitativeFaithfulnessValidator.compute_raw_faithfulness(
                (
                    weekly_res.strengths_feedback,
                    weekly_res.bottlenecks_feedback,
                    weekly_res.action_recommendations,
                ),
                allowed_numbers,
            )
            weekly_faithfulness_scores.append(case_weekly_faithfulness)
        except Exception:
            case_weekly_fallback = True
            weekly_fallbacks += 1
            case_weekly_faithfulness = 0.0
            weekly_faithfulness_scores.append(0.0)

        if scenario.get("is_injection_case"):
            injection_cases += 1
            if case_injection_ok:
                injection_isolated += 1

        outcome: dict[str, Any] = {
            "case_id": str(scenario["scenario_id"]),
            "domain": str(scenario["domain"]),
            "learner_level": str(scenario["learner_level"]),
            "deadline_regime": str(scenario["deadline_regime"]),
            "planning_mode": str(scenario["planning_mode"]),
            "is_injection_case": bool(scenario.get("is_injection_case", False)),
            "passed_tier1": case_passed,
            "attempts": case_attempts,
            "prompt_tokens": case_p_tok,
            "output_tokens": case_o_tok,
            "thinking_tokens": case_t_tok,
            "median_latency_ms": _percentile(sorted(case_latencies), 50.0),
            "judge_status": case_judge_status,
            "weekly_fallback": case_weekly_fallback,
            "weekly_faithfulness": round(case_weekly_faithfulness, 4),
            "injection_isolated": case_injection_ok,
        }
        if case_error is not None:
            outcome["error"] = case_error
        per_case_outcomes.append(outcome)

    sorted_latencies = sorted(latencies_ms)
    report: dict[str, Any] = {
        "schema_version": "1.0",
        "mode": "live" if use_live else "mock",
        "dataset_size": len(scenarios),
        "trials_per_goal": effective_trials,
        "total_runs": total_runs,
        "pass_at_1": round(pass_at_1_count / max(1, total_runs), 4),
        "post_retry_recovery_rate": round(recovered_count / max(1, total_runs), 4),
        "avg_retries": round(total_retries / max(1, total_runs), 4),
        "prompt_tokens_total": prompt_tokens_total,
        "output_tokens_total": output_tokens_total,
        "thinking_tokens_total": thinking_tokens_total,
        "latency_p50_ms": _percentile(sorted_latencies, 50.0),
        "latency_p95_ms": _percentile(sorted_latencies, 95.0),
        "judge_timeout_rate": round(judge_timeouts / max(1, judge_checks), 4),
        "weekly_fallback_rate": round(weekly_fallbacks / max(1, weekly_checks), 4),
        "weekly_faithfulness_avg": round(
            sum(weekly_faithfulness_scores) / max(1, len(weekly_faithfulness_scores)), 4
        ),
        "injection_isolation_rate": round(injection_isolated / max(1, injection_cases), 4),
        "per_case_outcomes": per_case_outcomes,
    }
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return report


if __name__ == "__main__":
    out = os.getenv("EVAL_REPORT_OUTPUT_PATH")
    res = asyncio.run(run_planning_eval_suite(output_path=Path(out) if out else None))
    print(json.dumps({k: v for k, v in res.items() if k != "per_case_outcomes"}, indent=2))
