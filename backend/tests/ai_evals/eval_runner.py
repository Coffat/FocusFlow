"""Offline/Live AI Planning Evaluation Runner (T0.2 + Group 4 normalized metrics).

Measures pass@1, post-retry recovery, average retries, prompt/output/thinking tokens,
latency p50/p95, separated judge status rates, separated weekly LLM vs fallback
faithfulness, valid-output-only prompt-injection isolation, standardized 6-category
error breakdown, and bounded concurrency across the 18-goal evaluation dataset
without persisting PII.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import time
from collections import Counter
from collections.abc import AsyncIterator, Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from pydantic import ValidationError

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
from src.planning.domain.models.milestone import Milestone, MilestoneStatus
from src.planning.domain.services.validation_types import (
    AvailabilityConfigurationDTO,
    AvailabilitySlotDTO,
)
from src.shared_kernel.application.harness.models import (
    PromptTemplate,
    WorkflowRun,
    WorkflowStepExecution,
    WorkflowStepStatus,
    WorkflowType,
)
from src.shared_kernel.application.llm_port import LLMGenerationResult, LLMProviderPort
from src.shared_kernel.config import get_settings
from src.shared_kernel.infrastructure.external_ai.litellm_adapter import LiteLLMAdapter
from src.shared_kernel.infrastructure.external_ai.prompt_sanitizer import PromptSanitizer
from tests.helpers.llm_stubs import StubLLMAdapter

DEFAULT_18_GOALS_DATASET_PATH = (
    Path(__file__).resolve().parent / "datasets" / "golden_planning_18_goals.jsonl"
)

ERROR_TAXONOMY_CATEGORIES: tuple[str, ...] = (
    "SCHEMA_MISMATCH",
    "TIMEOUT",
    "GATEWAY_ERROR",
    "VALIDATION_GATE",
    "QUOTA",
    "OTHER",
)

ProviderFactory = Callable[[int, dict[str, Any]], LLMProviderPort]


def _empty_error_bucket() -> dict[str, int]:
    return {category: 0 for category in ERROR_TAXONOMY_CATEGORIES}


def classify_eval_error(
    exc: Exception | None = None,
    *,
    error_code: str | None = None,
    error_message: str | None = None,
) -> str:
    """Classify an evaluation error into the canonical 6-category error taxonomy."""
    code_upper = (error_code or "").strip().upper()
    exc_type_name = type(exc).__name__ if exc is not None else ""
    exc_type_upper = exc_type_name.upper()
    msg_parts = [
        error_message or "",
        str(exc) if exc is not None else "",
        error_code or "",
    ]
    msg_lower = " ".join(part for part in msg_parts if part).lower()

    if "QUOTAEXCEEDED" in exc_type_upper or code_upper in {
        "QUOTA",
        "QUOTA_EXCEEDED",
        "INSUFFICIENT_QUOTA",
        "AI_QUOTA_EXCEEDED",
    }:
        return "QUOTA"

    if isinstance(exc, ProposalValidationGateError) or code_upper in {
        "VALIDATION_GATE",
        "INSUFFICIENT_TASKS",
    }:
        return "VALIDATION_GATE"

    if (
        isinstance(exc, (TimeoutError, asyncio.TimeoutError))
        or "TIMEOUT" in code_upper
        or "TIMEOUT" in exc_type_upper
    ):
        return "TIMEOUT"

    if isinstance(exc, (ValidationError, json.JSONDecodeError)) or code_upper in {
        "SCHEMA_MISMATCH",
        "WEEKLY_REVIEW_SCHEMA_ERROR",
        "WEEKLY_REVIEW_INVALID_PAYLOAD",
        "PROVE_QUESTION_GEN_INVALID_PAYLOAD",
    }:
        return "SCHEMA_MISMATCH"

    if exc_type_upper in {"VALIDATIONERROR", "JSONDECODEERROR"}:
        return "SCHEMA_MISMATCH"

    if isinstance(exc, ValueError) and any(
        marker in msg_lower
        for marker in ("json", "schema", "validation", "empty", "malformed", "parse")
    ):
        return "SCHEMA_MISMATCH"

    if any(
        marker in msg_lower
        for marker in (
            "ai_schema_validation_error",
            "missing required keys",
            "expected json object payload",
            "thiếu điểm số",
            "validationerror",
            "jsondecodeerror",
            "schema mismatch",
            "empty json response",
        )
    ):
        return "SCHEMA_MISMATCH"

    if any(
        marker in msg_lower
        for marker in (
            "timed out",
            "quá thời gian chờ",
            "không còn thời gian",
            "exceeded 55 seconds",
            "time budget",
        )
    ):
        return "TIMEOUT"

    if (
        isinstance(exc, (ConnectionError, OSError))
        or code_upper
        in {
            "GATEWAY_ERROR",
            "WEEKLY_REVIEW_EXECUTION_ERROR",
            "WEEKLY_REVIEW_PERMISSION_ERROR",
        }
        or exc_type_name
        in {
            "ServerError",
            "APIError",
            "ClientError",
            "APIConnectionError",
            "ServiceUnavailableError",
            "InternalServerError",
            "BadGatewayError",
            "GatewayTimeoutError",
            "RateLimitError",
        }
        or any(
            marker in msg_lower
            for marker in (
                "500",
                "502",
                "503",
                "504",
                "429",
                "401",
                "403",
                "404",
                "stream interrupted",
                "servererror",
                "unavailable",
                "resource_exhausted",
                "high demand",
                "tạm thời không phản hồi",
                "connection",
                "gateway",
            )
        )
    ):
        return "GATEWAY_ERROR"

    if "timeout" in msg_lower:
        return "TIMEOUT"

    return "OTHER"


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
        timeout_seconds: float | None = None,
        tool_call_timeout_seconds: float | None = None,
    ) -> LLMGenerationResult:
        del (
            system_prompt,
            user_prompt,
            response_schema,
            tools,
            tool_executor,
            max_tool_calls,
            thinking_level,
            timeout_seconds,
            tool_call_timeout_seconds,
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


class _EvalWorkflowRepo:
    """In-memory WorkflowRepositoryPort capturing step errors for taxonomy classification."""

    def __init__(self) -> None:
        self.runs: list[WorkflowRun] = []
        self.steps: list[WorkflowStepExecution] = []

    async def add_run(self, run: WorkflowRun) -> None:
        self.runs.append(run)

    async def get_run(self, run_id: UUID, *, user_id: UUID | None = None) -> WorkflowRun | None:
        del user_id
        for run in self.runs:
            if run.id == run_id:
                return run
        return None

    async def get_run_for_update(
        self,
        run_id: UUID,
        *,
        user_id: UUID | None = None,
    ) -> WorkflowRun | None:
        return await self.get_run(run_id, user_id=user_id)

    async def get_active_run_for_goal(
        self,
        goal_id: UUID,
        user_id: UUID,
        workflow_type: WorkflowType = WorkflowType.PLAN_CREATION,
    ) -> WorkflowRun | None:
        del goal_id, user_id, workflow_type
        return None

    async def acquire_goal_clarification_lock(self, goal_id: UUID, user_id: UUID) -> None:
        del goal_id, user_id

    async def get_run_by_idempotency_key(
        self,
        goal_id: UUID,
        user_id: UUID,
        idempotency_key: str,
    ) -> WorkflowRun | None:
        del goal_id, user_id, idempotency_key
        return None

    async def save_run(self, run: WorkflowRun) -> None:
        self.runs.append(run)

    async def add_step(self, step: WorkflowStepExecution) -> None:
        self.steps.append(step)

    async def get_steps(self, run_id: UUID) -> list[WorkflowStepExecution]:
        return [step for step in self.steps if step.workflow_run_id == run_id]


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
        timeout_seconds: float | None = None,
        tool_call_timeout_seconds: float | None = None,
    ) -> LLMGenerationResult:
        del (
            system_prompt,
            user_prompt,
            response_schema,
            tools,
            tool_executor,
            max_tool_calls,
            thinking_level,
            timeout_seconds,
            tool_call_timeout_seconds,
        )
        raise TimeoutError("Simulated weekly review timeout")

    async def stream_structured(
        self, *, system_prompt: str, user_prompt: str
    ) -> AsyncIterator[str]:
        del system_prompt, user_prompt
        yield "{}"


@dataclass(slots=True)
class _ScenarioEvalResult:
    outcome: dict[str, Any]
    latencies_ms: list[float] = field(default_factory=list)
    total_runs: int = 0
    pass_at_1_count: int = 0
    passed_runs: int = 0
    failed_runs: int = 0
    total_retries: int = 0
    prompt_tokens_total: int = 0
    output_tokens_total: int = 0
    thinking_tokens_total: int = 0
    decomposer_output_tokens: int = 0
    decomposer_thinking_tokens: int = 0
    tasks_count: int = 0
    min_tasks_met: bool = False
    pedagogical_score: float | None = None
    judge_status: str = "SKIPPED"
    judge_error_category: str | None = None
    weekly_skipped: bool = False
    weekly_fallback: bool = False
    weekly_faithfulness: float = 0.0
    weekly_error_category: str | None = None
    is_injection_case: bool = False
    injection_has_valid_output: bool = False
    injection_isolated: bool = False
    decomposer_error_categories: list[str] = field(default_factory=list)
    schema_check_calls: int = 0
    critic_schema_mismatch_count: int = 0
    schema_repair_attempts: int = 0


def _build_milestone_entities(milestones: Sequence[dict[str, Any]]) -> list[Milestone]:
    roadmap_uuid = uuid4()
    entities: list[Milestone] = []
    for m in milestones:
        raw_outcomes = m.get("learning_outcomes") or []
        outcomes_tuple = tuple(
            str(o.get("description") or o.get("id") or o) if isinstance(o, dict) else str(o)
            for o in raw_outcomes
        )
        completion_criteria = str(
            m.get("completion_criteria")
            or "; ".join(outcomes_tuple)
            or f"Hoàn thành cột mốc {m.get('title', '')}"
        )
        entities.append(
            Milestone(
                id=UUID(str(m["milestone_id"])),
                roadmap_id=roadmap_uuid,
                sequence_order=int(m.get("sequence_order", len(entities) + 1)),
                title=str(m.get("title", "Milestone")),
                learning_outcomes=outcomes_tuple,
                completion_criteria=completion_criteria,
                estimated_effort_minutes=int(m.get("estimated_effort_minutes", 120)),
                required_concepts=tuple(str(c) for c in (m.get("required_concepts") or [])),
                status=MilestoneStatus.APPROVED,
            )
        )
    return entities


async def _evaluate_scenario(
    idx: int,
    scenario: dict[str, Any],
    *,
    use_live: bool,
    effective_trials: int,
    decomposer_tpl: PromptTemplate,
    decomposer_thinking_level: str | None = None,
    judge_thinking_level: str | None = None,
    judge_timeout_seconds: float | None = None,
    include_weekly: bool = True,
    parallel_critics_and_judge: bool | None = None,
    decomposer_provider_factory: ProviderFactory | None = None,
    judge_provider_factory: ProviderFactory | None = None,
    weekly_provider_factory: ProviderFactory | None = None,
) -> _ScenarioEvalResult:
    effective_parallel = (
        (use_live and judge_provider_factory is None)
        if parallel_critics_and_judge is None
        else bool(parallel_critics_and_judge)
    )
    availability = _build_availability(scenario["availability"])
    milestones = list(scenario["milestones"])
    milestone_entities = _build_milestone_entities(milestones) if effective_parallel else []
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
                    str(o.get("description") or o.get("id") or o) if isinstance(o, dict) else str(o)
                    for o in (m.get("learning_outcomes") or [])
                ),
                "estimated_effort_minutes": m.get("estimated_effort_minutes", 120),
            }
            for m in milestones
        ],
        ensure_ascii=False,
    )
    sanitized_goal = PromptSanitizer.sanitize(
        str(scenario["goal"].get("raw_description", "")), wrap_xml=True
    )
    all_required_concepts = list(
        dict.fromkeys(
            str(c).strip()
            for m in milestones
            for c in (m.get("required_concepts") or [])
            if str(c).strip()
        )
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

    result = _ScenarioEvalResult(
        outcome={},
        is_injection_case=bool(scenario.get("is_injection_case", False)),
    )
    case_passed = False
    case_attempts = 1
    case_p_tok = 0
    case_o_tok = 0
    case_t_tok = 0
    case_error: str | None = None
    case_passed_trials = 0
    case_failed_trials = 0
    case_injection_ok = True
    case_has_valid_output = False
    last_valid_proposal: dict[str, Any] = {}

    case_judge_status = "SKIPPED_NO_PROPOSAL"
    case_pedagogical_score: float | None = None
    judge_error_category: str | None = None
    parallel_wf_repo = _EvalWorkflowRepo()

    for trial in range(effective_trials):
        result.total_runs += 1
        if decomposer_provider_factory is not None:
            provider = decomposer_provider_factory(idx, scenario)
        else:
            provider = LiteLLMAdapter() if use_live else StubLLMAdapter()

        effective_judge_timeout = (
            judge_timeout_seconds
            if judge_timeout_seconds is not None
            else float(get_settings().tier3_judge_timeout_seconds)
        )
        orchestrator = ProposalValidationGateOrchestrator(
            llm_provider=provider,
            enable_tier3_judge=effective_parallel,
            tier3_timeout_seconds=effective_judge_timeout if effective_parallel else None,
            workflow_repo=parallel_wf_repo if effective_parallel else None,
        )
        t0 = time.perf_counter()
        step_start_idx = len(parallel_wf_repo.steps)
        proposal: dict[str, Any] = {}
        attempts_used = 1
        retries_used = 0
        p_tok = 0
        o_tok = 0
        t_tok = 0
        passed = False
        trial_error: str | None = None
        trial_exc: Exception | None = None

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
                learner_level=str(scenario.get("learner_level", "")),
                milestone_summary=milestone_json if effective_parallel else "",
                milestones=milestone_entities if effective_parallel else (),
                thinking_level=decomposer_thinking_level or TASK_DECOMPOSER_SKILL.thinking_level,
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
            if effective_parallel and gate_result.is_valid:
                case_judge_status = gate_result.judge_status
                case_pedagogical_score = gate_result.pedagogical_score
                result.pedagogical_score = gate_result.pedagogical_score
                if gate_result.judge_status == "REVIEW_PENDING":
                    failed_judge_steps = [
                        step
                        for step in parallel_wf_repo.steps[step_start_idx:]
                        if step.step_name == "PEDAGOGICAL_JUDGE"
                        and step.status == WorkflowStepStatus.FAILED
                    ]
                    if failed_judge_steps:
                        last_j = failed_judge_steps[-1]
                        judge_error_category = classify_eval_error(
                            error_code=str(last_j.output_payload.get("error_category") or "")
                            or None,
                            error_message=str(last_j.output_payload.get("error", "")),
                        )
                    else:
                        judge_error_category = classify_eval_error(
                            error_message=" ".join(gate_result.advisory_warnings)
                        )
            if not passed:
                trial_error = "INSUFFICIENT_TASKS"
        except ProposalValidationGateError as exc:
            attempts_used = 3
            retries_used = 2
            trial_error = exc.code
            trial_exc = exc
        except Exception as exc:
            attempts_used = 1
            retries_used = 0
            trial_error = type(exc).__name__
            trial_exc = exc

        trial_steps = parallel_wf_repo.steps[step_start_idx:]
        if trial_exc is not None and effective_parallel and p_tok == 0 and trial_steps:
            p_tok = sum(int(s.output_payload.get("prompt_tokens", 0) or 0) for s in trial_steps)
            o_tok = sum(
                int(
                    s.output_payload.get(
                        "output_tokens", s.output_payload.get("completion_tokens", 0)
                    )
                    or 0
                )
                for s in trial_steps
            )
            t_tok = sum(int(s.output_payload.get("thinking_tokens", 0) or 0) for s in trial_steps)

        if effective_parallel:
            decomposer_steps = [s for s in trial_steps if s.step_name == "TASK_DECOMPOSER"]
            critic_steps = [
                s
                for s in trial_steps
                if s.step_name
                in {
                    "COVERAGE_PREREQUISITE_CRITIC",
                    "LEARNER_FIT_ACTIONABILITY_CRITIC",
                    "QUALITY_ARBITER",
                }
            ]
            judge_steps = [s for s in trial_steps if s.step_name == "PEDAGOGICAL_JUDGE"]
            result.schema_check_calls += (
                max(1, len(decomposer_steps)) + len(critic_steps) + len(judge_steps)
            )
            for c_step in critic_steps:
                if c_step.status == WorkflowStepStatus.FAILED:
                    c_cat = classify_eval_error(
                        error_code=str(c_step.output_payload.get("error_category") or "") or None,
                        error_message=str(c_step.output_payload.get("error", "")),
                    )
                    if c_cat == "SCHEMA_MISMATCH":
                        result.critic_schema_mismatch_count += 1
            result.schema_repair_attempts += sum(
                int(s.output_payload.get("repair_attempts", 0) or 0) for s in trial_steps
            )
        else:
            result.schema_check_calls += attempts_used if trial_exc is None else 1

        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 3)
        result.latencies_ms.append(elapsed_ms)

        result.total_retries += retries_used
        result.prompt_tokens_total += p_tok
        result.output_tokens_total += o_tok
        result.thinking_tokens_total += t_tok
        result.decomposer_output_tokens += o_tok
        result.decomposer_thinking_tokens += t_tok

        if passed and retries_used == 0:
            result.pass_at_1_count += 1
        if passed:
            result.passed_runs += 1
            case_passed_trials += 1
        else:
            result.failed_runs += 1
            case_failed_trials += 1
            err_cat = classify_eval_error(
                trial_exc,
                error_code=trial_error,
                error_message=str(trial_exc) if trial_exc is not None else None,
            )
            result.decomposer_error_categories.append(err_cat)

        has_valid_trial_output = (
            trial_exc is None
            and isinstance(proposal.get("tasks"), list)
            and len(proposal.get("tasks", [])) > 0
        )
        if has_valid_trial_output:
            case_has_valid_output = True
            last_valid_proposal = proposal
            # Check prompt injection containment strictly on valid generated proposals
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

    # Tier 3 Pedagogical Judge (skipped here when already evaluated in parallel inside orchestrator)
    min_tasks_required = int(scenario["expected_invariants"].get("min_tasks", 1))
    last_tasks_count = len(last_valid_proposal.get("tasks", []))
    result.tasks_count = last_tasks_count
    result.min_tasks_met = last_tasks_count >= min_tasks_required
    if not effective_parallel and last_valid_proposal.get("tasks"):
        result.schema_check_calls += 1
        judge_workflow_repo = _EvalWorkflowRepo()
        if judge_provider_factory is not None:
            judge_provider = judge_provider_factory(idx, scenario)
            judge_timeout = judge_timeout_seconds if judge_timeout_seconds is not None else 5.0
        elif use_live:
            judge_provider = LiteLLMAdapter()
            judge_timeout = (
                judge_timeout_seconds
                if judge_timeout_seconds is not None
                else float(get_settings().tier3_judge_timeout_seconds)
            )
        elif idx % 6 == 0:
            judge_provider = _SlowJudgeStub()
            judge_timeout = 0.01
        else:
            judge_provider = StubLLMAdapter()
            judge_timeout = 5.0

        judge_orch = ProposalValidationGateOrchestrator(
            llm_provider=judge_provider,
            enable_tier3_judge=True,
            tier3_timeout_seconds=judge_timeout,
            workflow_repo=judge_workflow_repo,
        )
        try:
            (
                _skipped,
                judge_score,
                advisory_warnings,
                judge_status,
            ) = await judge_orch.run_tier3_pedagogical_judge(
                last_valid_proposal,
                goal_title=str(scenario["goal"].get("title", "")),
                learner_level=str(scenario.get("learner_level", "")),
                milestone_summary=milestone_json,
                milestones_metadata=milestones,
                thinking_level=judge_thinking_level,
            )
            case_judge_status = judge_status
            case_pedagogical_score = judge_score
            result.pedagogical_score = judge_score
            result.prompt_tokens_total += judge_orch._last_judge_prompt_tokens
            result.output_tokens_total += judge_orch._last_judge_completion_tokens
            result.thinking_tokens_total += judge_orch._last_judge_thinking_tokens
            case_p_tok += judge_orch._last_judge_prompt_tokens
            case_o_tok += judge_orch._last_judge_completion_tokens
            case_t_tok += judge_orch._last_judge_thinking_tokens

            if judge_status == "REVIEW_PENDING":
                failed_steps = [
                    step
                    for step in judge_workflow_repo.steps
                    if step.status == WorkflowStepStatus.FAILED
                ]
                failed_runs = [
                    run for run in judge_workflow_repo.runs if run.error_detail is not None
                ]
                step_err_msg = (
                    str(failed_steps[-1].output_payload.get("error", "")).strip()
                    if failed_steps
                    else ""
                )
                run_err_code = failed_runs[-1].error_detail if failed_runs else None
                warn_text = " ".join(advisory_warnings)
                judge_error_category = classify_eval_error(
                    error_code=run_err_code,
                    error_message=step_err_msg or warn_text,
                )
            result.schema_repair_attempts += sum(
                int(step.output_payload.get("repair_attempts", 0) or 0)
                for step in judge_workflow_repo.steps
            )
        except Exception as exc:
            case_judge_status = "REVIEW_PENDING"
            judge_error_category = classify_eval_error(exc)

    result.judge_status = case_judge_status
    result.judge_error_category = judge_error_category

    # Weekly Review evaluation (real LiteLLMAdapter in live mode + quantitative faithfulness)
    case_weekly_fallback = False
    case_weekly_faithfulness = 0.0
    weekly_error_category: str | None = None
    if not include_weekly:
        result.weekly_skipped = True
    else:
        result.schema_check_calls += 1
        roadmap_uuid = uuid4()
        weekly_repo = _EvalWeeklyRepo(roadmap_uuid)
        weekly_workflow_repo = _EvalWorkflowRepo()
        if weekly_provider_factory is not None:
            weekly_llm = weekly_provider_factory(idx, scenario)
        elif use_live:
            weekly_llm = LiteLLMAdapter()
        else:
            weekly_llm = _FailingWeeklyLLM() if idx % 5 == 0 else StubLLMAdapter()

        weekly_uc = GenerateWeeklyReviewUseCase(
            repository=weekly_repo,  # type: ignore[arg-type]
            ownership=_EvalOwnership(),  # type: ignore[arg-type]
            uow=_EvalUoW(),  # type: ignore[arg-type]
            execution_metrics_port=_EvalWeeklyMetricsPort(),
            workflow_repo=weekly_workflow_repo,  # type: ignore[arg-type]
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
            case_weekly_fallback = weekly_repo.last_model_used in (
                "deterministic-fallback",
                "deterministic-insufficient-data",
            )
            raw_logged_faithfulness = (
                weekly_workflow_repo.steps[-1].output_payload.get("quantitative_faithfulness")
                if weekly_workflow_repo.steps
                else None
            )
            if isinstance(raw_logged_faithfulness, (int, float)) and not isinstance(
                raw_logged_faithfulness, bool
            ):
                case_weekly_faithfulness = float(raw_logged_faithfulness)
            else:
                allowed_numbers = [
                    float(val)
                    for val in weekly_res.quantitative_summary.values()
                    if isinstance(val, (int, float)) and not isinstance(val, bool)
                ]
                case_weekly_faithfulness = (
                    QuantitativeFaithfulnessValidator.compute_raw_faithfulness(
                        (
                            weekly_res.strengths_feedback,
                            weekly_res.bottlenecks_feedback,
                            weekly_res.action_recommendations,
                        ),
                        allowed_numbers,
                    )
                )
            if case_weekly_fallback:
                fallback_code = None
                if weekly_workflow_repo.steps:
                    raw_code = weekly_workflow_repo.steps[-1].output_payload.get(
                        "fallback_reason_code"
                    )
                    if raw_code is not None:
                        fallback_code = str(raw_code)
                if fallback_code is None and weekly_workflow_repo.runs:
                    fallback_code = weekly_workflow_repo.runs[-1].error_detail
                weekly_error_category = classify_eval_error(error_code=fallback_code)
        except Exception as exc:
            case_weekly_fallback = True
            case_weekly_faithfulness = 0.0
            weekly_error_category = classify_eval_error(exc)

    result.weekly_fallback = case_weekly_fallback
    result.weekly_faithfulness = case_weekly_faithfulness
    result.weekly_error_category = weekly_error_category

    result.injection_has_valid_output = case_has_valid_output
    result.injection_isolated = case_has_valid_output and case_injection_ok
    if result.is_injection_case:
        if not case_has_valid_output:
            injection_status = "EXCLUDED_NO_OUTPUT"
            outcome_injection_isolated: bool | None = None
        elif case_injection_ok:
            injection_status = "ISOLATED"
            outcome_injection_isolated = True
        else:
            injection_status = "LEAKED"
            outcome_injection_isolated = False
    else:
        injection_status = "NOT_APPLICABLE"
        outcome_injection_isolated = case_injection_ok if case_has_valid_output else None

    outcome: dict[str, Any] = {
        "case_id": str(scenario["scenario_id"]),
        "domain": str(scenario["domain"]),
        "learner_level": str(scenario["learner_level"]),
        "deadline_regime": str(scenario["deadline_regime"]),
        "planning_mode": str(scenario["planning_mode"]),
        "is_injection_case": result.is_injection_case,
        "passed_tier1": case_passed,
        "decomposer_passed_trials": case_passed_trials,
        "decomposer_failed_trials": case_failed_trials,
        "decomposer_error_categories": list(result.decomposer_error_categories),
        "attempts": case_attempts,
        "prompt_tokens": case_p_tok,
        "output_tokens": case_o_tok,
        "thinking_tokens": case_t_tok,
        "tasks_count": last_tasks_count,
        "min_tasks": min_tasks_required,
        "min_tasks_met": last_tasks_count >= min_tasks_required,
        "pedagogical_score": case_pedagogical_score,
        "median_latency_ms": _percentile(sorted(result.latencies_ms), 50.0),
        "judge_status": case_judge_status,
        "judge_error_category": judge_error_category,
        "weekly_fallback": case_weekly_fallback,
        "weekly_source": "skipped"
        if not include_weekly
        else ("fallback" if case_weekly_fallback else "llm"),
        "weekly_faithfulness": round(case_weekly_faithfulness, 4),
        "weekly_error_category": weekly_error_category,
        "injection_status": injection_status,
        "injection_isolated": outcome_injection_isolated,
    }
    if case_error is not None:
        outcome["error"] = case_error
    result.outcome = outcome
    return result


def validate_eval_report_totals(report: dict[str, Any]) -> None:
    """Self-check that all summary counts and error_breakdown totals match per-case details 100%."""
    per_case_outcomes = report["per_case_outcomes"]
    dataset_size = int(report["dataset_size"])
    trials_per_goal = int(report["trials_per_goal"])

    assert len(per_case_outcomes) == dataset_size, (
        f"dataset_size={dataset_size} != len(per_case_outcomes)={len(per_case_outcomes)}"
    )
    assert report["total_runs"] == dataset_size * trials_per_goal, (
        f"total_runs={report['total_runs']} != {dataset_size * trials_per_goal}"
    )
    assert report["passed_runs"] + report["failed_runs"] == report["total_runs"], (
        "passed_runs + failed_runs must equal total_runs"
    )
    assert sum(o["decomposer_passed_trials"] for o in per_case_outcomes) == report["passed_runs"], (
        "sum(decomposer_passed_trials) must match passed_runs"
    )
    assert sum(o["decomposer_failed_trials"] for o in per_case_outcomes) == report["failed_runs"], (
        "sum(decomposer_failed_trials) must match failed_runs"
    )

    judge_total = (
        report["judge_passed_count"]
        + report["judge_needs_review_count"]
        + report["judge_review_pending_count"]
        + report["judge_skipped_count"]
    )
    assert judge_total == report["judge_checks"] == dataset_size, (
        f"judge status counts sum ({judge_total}) must equal judge_checks ({report['judge_checks']}) and dataset_size ({dataset_size})"
    )
    assert report["judge_attempted_cases"] == (
        report["judge_passed_count"]
        + report["judge_needs_review_count"]
        + report["judge_review_pending_count"]
    )
    assert (
        sum(1 for o in per_case_outcomes if o["judge_status"] == "PASSED")
        == (report["judge_passed_count"])
    )
    assert (
        sum(1 for o in per_case_outcomes if o["judge_status"] == "NEEDS_REVIEW")
        == (report["judge_needs_review_count"])
    )
    assert (
        sum(1 for o in per_case_outcomes if o["judge_status"] == "REVIEW_PENDING")
        == (report["judge_review_pending_count"])
    )
    assert (
        sum(1 for o in per_case_outcomes if o["judge_status"] in {"SKIPPED", "SKIPPED_NO_PROPOSAL"})
        == (report["judge_skipped_count"])
    )

    assert (
        report["weekly_llm_success_count"] + report["weekly_fallbacks"] == report["weekly_checks"]
    ), "weekly_llm_success_count + weekly_fallbacks must equal weekly_checks"
    if report["weekly_checks"] > 0:
        assert report["weekly_checks"] == dataset_size
        assert (
            sum(1 for o in per_case_outcomes if not o["weekly_fallback"])
            == (report["weekly_llm_success_count"])
        )
    assert sum(1 for o in per_case_outcomes if o["weekly_fallback"]) == report["weekly_fallbacks"]

    injection_outcomes = [o for o in per_case_outcomes if o["is_injection_case"]]
    assert len(injection_outcomes) == report["injection_cases"]
    assert (
        report["injection_valid_output_cases"] + report["injection_excluded_cases"]
        == report["injection_cases"]
    )
    assert 0 <= report["injection_isolated_count"] <= report["injection_valid_output_cases"]
    assert (
        sum(1 for o in injection_outcomes if o["injection_status"] == "EXCLUDED_NO_OUTPUT")
        == (report["injection_excluded_cases"])
    )
    assert (
        sum(1 for o in injection_outcomes if o["injection_status"] in {"ISOLATED", "LEAKED"})
        == (report["injection_valid_output_cases"])
    )
    assert (
        sum(1 for o in injection_outcomes if o["injection_status"] == "ISOLATED")
        == (report["injection_isolated_count"])
    )

    eb = report["error_breakdown"]
    assert set(eb.keys()) == {"decomposer", "judge", "weekly", "total"}
    for step in ("decomposer", "judge", "weekly", "total"):
        assert set(eb[step].keys()) == set(ERROR_TAXONOMY_CATEGORIES)
        assert all(isinstance(v, int) and v >= 0 for v in eb[step].values())

    assert sum(eb["decomposer"].values()) == report["failed_runs"], (
        "sum(error_breakdown.decomposer) must equal failed_runs"
    )
    assert sum(eb["judge"].values()) == report["judge_review_pending_count"], (
        "sum(error_breakdown.judge) must equal judge_review_pending_count"
    )
    assert sum(eb["weekly"].values()) == report["weekly_fallbacks"], (
        "sum(error_breakdown.weekly) must equal weekly_fallbacks"
    )

    decomposer_counter = Counter(
        cat for o in per_case_outcomes for cat in o["decomposer_error_categories"]
    )
    judge_counter = Counter(
        o["judge_error_category"] for o in per_case_outcomes if o.get("judge_error_category")
    )
    weekly_counter = Counter(
        o["weekly_error_category"] for o in per_case_outcomes if o.get("weekly_error_category")
    )
    for category in ERROR_TAXONOMY_CATEGORIES:
        assert eb["decomposer"][category] == decomposer_counter[category]
        assert eb["judge"][category] == judge_counter[category]
        assert eb["weekly"][category] == weekly_counter[category]
        assert eb["total"][category] == (
            eb["decomposer"][category] + eb["judge"][category] + eb["weekly"][category]
        )

    assert report["post_repair_schema_mismatch_count"] >= eb["total"]["SCHEMA_MISMATCH"]
    assert 0 <= report["post_repair_schema_mismatch_count"] <= report["schema_check_calls"]
    expected_mismatch_rate = round(
        report["post_repair_schema_mismatch_count"] / max(1, report["schema_check_calls"]), 4
    )
    assert report["post_repair_schema_mismatch_rate"] == expected_mismatch_rate


async def run_planning_eval_suite(
    dataset_path: Path = DEFAULT_18_GOALS_DATASET_PATH,
    *,
    trials_per_goal: int = 3,
    output_path: Path | None = None,
    live: bool | None = None,
    concurrency: int = 1,
    decomposer_thinking_level: str | None = None,
    judge_thinking_level: str | None = None,
    judge_timeout_seconds: float | None = None,
    include_weekly: bool = True,
    parallel_critics_and_judge: bool | None = None,
    decomposer_provider_factory: ProviderFactory | None = None,
    judge_provider_factory: ProviderFactory | None = None,
    weekly_provider_factory: ProviderFactory | None = None,
) -> dict[str, Any]:
    """Run the 18-goal evaluation benchmark and return a PII-free metrics artifact."""
    scenarios = load_18_goal_dataset(dataset_path)
    use_live = bool(os.getenv("RUN_LIVE_AI_EVALS") == "1") if live is None else live
    effective_trials = max(1, trials_per_goal)
    effective_concurrency = max(1, int(concurrency))

    decomposer_tpl = build_planning_prompt_registry().latest(TASK_DECOMPOSER_SKILL.skill_id)

    if effective_concurrency == 1:
        scenario_results = [
            await _evaluate_scenario(
                idx,
                scenario,
                use_live=use_live,
                effective_trials=effective_trials,
                decomposer_tpl=decomposer_tpl,
                decomposer_thinking_level=decomposer_thinking_level,
                judge_thinking_level=judge_thinking_level,
                judge_timeout_seconds=judge_timeout_seconds,
                include_weekly=include_weekly,
                parallel_critics_and_judge=parallel_critics_and_judge,
                decomposer_provider_factory=decomposer_provider_factory,
                judge_provider_factory=judge_provider_factory,
                weekly_provider_factory=weekly_provider_factory,
            )
            for idx, scenario in enumerate(scenarios)
        ]
    else:
        semaphore = asyncio.Semaphore(effective_concurrency)

        async def _bounded_eval(idx: int, scenario: dict[str, Any]) -> _ScenarioEvalResult:
            async with semaphore:
                return await _evaluate_scenario(
                    idx,
                    scenario,
                    use_live=use_live,
                    effective_trials=effective_trials,
                    decomposer_tpl=decomposer_tpl,
                    decomposer_thinking_level=decomposer_thinking_level,
                    judge_thinking_level=judge_thinking_level,
                    judge_timeout_seconds=judge_timeout_seconds,
                    include_weekly=include_weekly,
                    parallel_critics_and_judge=parallel_critics_and_judge,
                    decomposer_provider_factory=decomposer_provider_factory,
                    judge_provider_factory=judge_provider_factory,
                    weekly_provider_factory=weekly_provider_factory,
                )

        scenario_results = list(
            await asyncio.gather(
                *(_bounded_eval(idx, scenario) for idx, scenario in enumerate(scenarios))
            )
        )

    latencies_ms: list[float] = []
    per_case_outcomes: list[dict[str, Any]] = []
    weekly_llm_faithfulness_scores: list[float] = []
    weekly_fallback_faithfulness_scores: list[float] = []

    total_runs = 0
    pass_at_1_count = 0
    passed_runs = 0
    failed_runs = 0
    total_retries = 0
    prompt_tokens_total = 0
    output_tokens_total = 0
    thinking_tokens_total = 0

    judge_checks = len(scenario_results)
    judge_passed_count = 0
    judge_needs_review_count = 0
    judge_review_pending_count = 0
    judge_skipped_count = 0

    weekly_checks = len(scenario_results) if include_weekly else 0
    weekly_llm_success_count = 0
    weekly_fallbacks = 0

    injection_cases = 0
    injection_valid_output_cases = 0
    injection_excluded_cases = 0
    injection_isolated_count = 0

    decomposer_errors = _empty_error_bucket()
    judge_errors = _empty_error_bucket()
    weekly_errors = _empty_error_bucket()

    for item in scenario_results:
        latencies_ms.extend(item.latencies_ms)
        per_case_outcomes.append(item.outcome)
        total_runs += item.total_runs
        pass_at_1_count += item.pass_at_1_count
        passed_runs += item.passed_runs
        failed_runs += item.failed_runs
        total_retries += item.total_retries
        prompt_tokens_total += item.prompt_tokens_total
        output_tokens_total += item.output_tokens_total
        thinking_tokens_total += item.thinking_tokens_total

        for cat in item.decomposer_error_categories:
            decomposer_errors[cat] += 1

        if item.judge_status == "PASSED":
            judge_passed_count += 1
        elif item.judge_status == "NEEDS_REVIEW":
            judge_needs_review_count += 1
        elif item.judge_status == "REVIEW_PENDING":
            judge_review_pending_count += 1
            j_cat = item.judge_error_category or "OTHER"
            judge_errors[j_cat] += 1
        else:
            judge_skipped_count += 1

        if not item.weekly_skipped:
            if item.weekly_fallback:
                weekly_fallbacks += 1
                weekly_fallback_faithfulness_scores.append(item.weekly_faithfulness)
                w_cat = item.weekly_error_category or "OTHER"
                weekly_errors[w_cat] += 1
            else:
                weekly_llm_success_count += 1
                weekly_llm_faithfulness_scores.append(item.weekly_faithfulness)

        if item.is_injection_case:
            injection_cases += 1
            if item.injection_has_valid_output:
                injection_valid_output_cases += 1
                if item.injection_isolated:
                    injection_isolated_count += 1
            else:
                injection_excluded_cases += 1

    judge_attempted_cases = (
        judge_passed_count + judge_needs_review_count + judge_review_pending_count
    )
    total_errors = {
        cat: decomposer_errors[cat] + judge_errors[cat] + weekly_errors[cat]
        for cat in ERROR_TAXONOMY_CATEGORIES
    }

    pedagogical_scores = [
        item.pedagogical_score for item in scenario_results if item.pedagogical_score is not None
    ]
    tasks_counts = [item.tasks_count for item in scenario_results if item.tasks_count > 0]
    min_tasks_met_count = sum(1 for item in scenario_results if item.min_tasks_met)
    decomposer_output_tokens_total = sum(item.decomposer_output_tokens for item in scenario_results)
    decomposer_thinking_tokens_total = sum(
        item.decomposer_thinking_tokens for item in scenario_results
    )
    schema_check_calls = sum(item.schema_check_calls for item in scenario_results)
    critic_schema_mismatch_count = sum(
        item.critic_schema_mismatch_count for item in scenario_results
    )
    post_repair_schema_mismatch_count = (
        total_errors["SCHEMA_MISMATCH"] + critic_schema_mismatch_count
    )
    schema_repair_attempts_total = sum(item.schema_repair_attempts for item in scenario_results)

    sorted_latencies = sorted(latencies_ms)
    report: dict[str, Any] = {
        "schema_version": "1.0",
        "mode": "live" if use_live else "mock",
        "dataset_size": len(scenarios),
        "trials_per_goal": effective_trials,
        "concurrency": effective_concurrency,
        "total_runs": total_runs,
        "passed_runs": passed_runs,
        "failed_runs": failed_runs,
        "pass_at_1": round(pass_at_1_count / max(1, total_runs), 4),
        "post_retry_recovery_rate": round(passed_runs / max(1, total_runs), 4),
        "avg_retries": round(total_retries / max(1, total_runs), 4),
        "schema_check_calls": schema_check_calls,
        "schema_repair_attempts_total": schema_repair_attempts_total,
        "post_repair_schema_mismatch_count": post_repair_schema_mismatch_count,
        "post_repair_schema_mismatch_rate": round(
            post_repair_schema_mismatch_count / max(1, schema_check_calls), 4
        ),
        "prompt_tokens_total": prompt_tokens_total,
        "output_tokens_total": output_tokens_total,
        "thinking_tokens_total": thinking_tokens_total,
        "thinking_pct_of_output": (
            round(thinking_tokens_total / output_tokens_total, 4)
            if output_tokens_total > 0
            else 0.0
        ),
        "decomposer_output_tokens_total": decomposer_output_tokens_total,
        "decomposer_thinking_tokens_total": decomposer_thinking_tokens_total,
        "decomposer_thinking_pct": (
            round(decomposer_thinking_tokens_total / decomposer_output_tokens_total, 4)
            if decomposer_output_tokens_total > 0
            else 0.0
        ),
        "avg_tasks_per_goal": (
            round(sum(tasks_counts) / len(tasks_counts), 2) if tasks_counts else 0.0
        ),
        "min_tasks_met_rate": round(min_tasks_met_count / max(1, len(scenario_results)), 4),
        "pedagogical_score_avg": (
            round(sum(pedagogical_scores) / len(pedagogical_scores), 2)
            if pedagogical_scores
            else None
        ),
        "latency_p50_ms": _percentile(sorted_latencies, 50.0),
        "latency_p95_ms": _percentile(sorted_latencies, 95.0),
        "judge_checks": judge_checks,
        "judge_attempted_cases": judge_attempted_cases,
        "judge_passed_count": judge_passed_count,
        "judge_needs_review_count": judge_needs_review_count,
        "judge_review_pending_count": judge_review_pending_count,
        "judge_skipped_count": judge_skipped_count,
        "judge_passed_rate": round(judge_passed_count / max(1, judge_checks), 4),
        "judge_needs_review_rate": round(judge_needs_review_count / max(1, judge_checks), 4),
        "judge_review_pending_rate": round(judge_review_pending_count / max(1, judge_checks), 4),
        "judge_skipped_rate": round(judge_skipped_count / max(1, judge_checks), 4),
        "judge_timeout_rate": (
            round(judge_review_pending_count / judge_attempted_cases, 4)
            if judge_attempted_cases > 0
            else 0.0
        ),
        "weekly_checks": weekly_checks,
        "weekly_llm_success_count": weekly_llm_success_count,
        "weekly_fallbacks": weekly_fallbacks,
        "weekly_llm_success_rate": round(weekly_llm_success_count / max(1, weekly_checks), 4),
        "weekly_fallback_rate": round(weekly_fallbacks / max(1, weekly_checks), 4),
        "weekly_llm_faithfulness_avg": (
            round(
                sum(weekly_llm_faithfulness_scores) / len(weekly_llm_faithfulness_scores),
                4,
            )
            if weekly_llm_faithfulness_scores
            else None
        ),
        "weekly_fallback_faithfulness_avg": (
            round(
                sum(weekly_fallback_faithfulness_scores) / len(weekly_fallback_faithfulness_scores),
                4,
            )
            if weekly_fallback_faithfulness_scores
            else None
        ),
        "injection_cases": injection_cases,
        "injection_valid_output_cases": injection_valid_output_cases,
        "injection_excluded_cases": injection_excluded_cases,
        "injection_isolated_count": injection_isolated_count,
        "injection_isolation_rate": (
            round(injection_isolated_count / injection_valid_output_cases, 4)
            if injection_valid_output_cases > 0
            else None
        ),
        "injection_isolation_summary": (
            f"{injection_isolated_count}/{injection_valid_output_cases} valid outputs "
            f"({injection_excluded_cases} excluded)"
        ),
        "error_breakdown": {
            "decomposer": decomposer_errors,
            "judge": judge_errors,
            "weekly": weekly_errors,
            "total": total_errors,
        },
        "per_case_outcomes": per_case_outcomes,
    }
    validate_eval_report_totals(report)

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return report


def parse_cli_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run FocusFlow 18-goal AI planning evaluation suite.",
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_18_GOALS_DATASET_PATH,
        help="Path to the evaluation JSONL dataset.",
    )
    parser.add_argument(
        "--trials-per-goal",
        type=int,
        default=int(os.getenv("EVAL_TRIALS_PER_GOAL", "3")),
        help="Number of trials per goal scenario (default: 3).",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=int(os.getenv("EVAL_CONCURRENCY", "1")),
        help="Maximum concurrent scenarios (default: 1 sequential).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(out) if (out := os.getenv("EVAL_REPORT_OUTPUT_PATH")) else None,
        help="Optional output JSON report file path.",
    )
    parser.add_argument(
        "--parallel-critics-judge",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Run Dual Critics and Tier 3 Judge in parallel inside orchestrator (default: enabled in live mode).",
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--live",
        dest="live",
        action="store_true",
        help="Force live LLM execution mode.",
    )
    mode_group.add_argument(
        "--mock",
        dest="live",
        action="store_false",
        help="Force offline mock LLM execution mode.",
    )
    parser.set_defaults(live=None)
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_cli_args(argv)
    res = asyncio.run(
        run_planning_eval_suite(
            dataset_path=args.dataset,
            trials_per_goal=args.trials_per_goal,
            output_path=args.output,
            live=args.live,
            concurrency=args.concurrency,
            parallel_critics_and_judge=args.parallel_critics_judge,
        )
    )
    print(json.dumps({k: v for k, v in res.items() if k != "per_case_outcomes"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
