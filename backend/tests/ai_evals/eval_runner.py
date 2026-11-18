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
import re
import time
from collections import Counter, defaultdict
from collections.abc import AsyncIterator, Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from pydantic import ValidationError

from src.evaluation.application.dtos.intelligence import GenerateWeeklyReviewRequestDTO
from src.evaluation.application.use_cases.intelligence import GenerateWeeklyReviewUseCase
from src.evaluation.domain.models.intelligence import WeeklyReview
from src.evaluation.domain.services import QuantitativeFaithfulnessValidator
from src.planning.application.dtos.planning_dtos import (
    ClarificationContextPayload,
    ClarificationQuestionsLLMOutput,
    MilestoneGenerationLLMOutput,
    TaskProposalLLMOutput,
)
from src.planning.application.services.clarification_gap_analysis import (
    GapStatus,
    GoalFactProvenance,
    InformationGapAnalyzer,
)
from src.planning.application.services.roadmap_context_builder import (
    RoadmapContextBuilder,
)
from src.planning.application.services.roadmap_skills import (
    GOAL_CLARIFIER_SKILL,
    MILESTONE_PLANNER_SKILL,
    TASK_DECOMPOSER_SKILL,
    build_goal_clarifier_prompt,
    build_milestone_planner_prompt,
    build_planning_prompt_registry,
)
from src.planning.application.services.validation_gate import ProposalValidationGateOrchestrator
from src.planning.domain.exceptions.planning_exceptions import ProposalValidationGateError
from src.planning.domain.models.goal import Goal
from src.planning.domain.models.milestone import Milestone, MilestoneStatus
from src.planning.domain.models.roadmap import Roadmap
from src.planning.domain.services.milestone_effort_allocator import MilestoneEffortAllocator
from src.planning.domain.services.spatio_temporal_engine import SpatioTemporalRuleEngine
from src.planning.domain.services.validation_types import (
    AvailabilityConfigurationDTO,
    AvailabilitySlotDTO,
)
from src.planning.infrastructure.repositories.sqlalchemy_knowledge_base_repository import (
    InMemoryKnowledgeBaseRepository,
)
from src.shared_kernel.application.harness.execution_manager import (
    AIExecutionManager,
    default_ai_retry_predicate,
)
from src.shared_kernel.application.harness.models import (
    PromptTemplate,
    WorkflowRun,
    WorkflowStepExecution,
    WorkflowStepStatus,
    WorkflowType,
)
from src.shared_kernel.application.llm_port import (
    LLMGenerationResult,
    LLMProviderPort,
    LLMToolDeclarationDTO,
    LLMToolExecutor,
)
from src.shared_kernel.config import get_settings
from src.shared_kernel.domain.base import generate_uuid7
from src.shared_kernel.infrastructure.external_ai.litellm_adapter import LiteLLMAdapter
from src.shared_kernel.infrastructure.external_ai.prompt_sanitizer import PromptSanitizer
from tests.helpers.llm_stubs import StubLLMAdapter

DEFAULT_18_GOALS_DATASET_PATH = (
    Path(__file__).resolve().parent / "datasets" / "golden_planning_18_goals.jsonl"
)
HARD_6_GOALS_DATASET_PATH = (
    Path(__file__).resolve().parent / "datasets" / "hard_planning_6_goals.jsonl"
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


def load_eval_dataset(
    dataset_path: Path = DEFAULT_18_GOALS_DATASET_PATH,
) -> list[dict[str, Any]]:
    """Load an evaluation JSONL dataset (18-goal, holdout, or 6-goal hard E2E)."""
    lines = [
        line.strip()
        for line in dataset_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return [json.loads(line) for line in lines]


def load_18_goal_dataset(
    dataset_path: Path = DEFAULT_18_GOALS_DATASET_PATH,
) -> list[dict[str, Any]]:
    """Load the 18-goal deterministic evaluation JSONL dataset."""
    return load_eval_dataset(dataset_path)


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


def _summarize_latency_stats(values: Sequence[float]) -> dict[str, float | int]:
    if not values:
        return {"count": 0, "min_ms": 0.0, "p50_ms": 0.0, "p95_ms": 0.0, "max_ms": 0.0}
    ordered = sorted(float(v) for v in values)
    return {
        "count": len(ordered),
        "min_ms": round(ordered[0], 3),
        "p50_ms": _percentile(ordered, 50.0),
        "p95_ms": _percentile(ordered, 95.0),
        "max_ms": round(ordered[-1], 3),
    }


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


class _E2EStubLLMAdapter(StubLLMAdapter):
    """Offline stub supporting 3-stage E2E (Clarifier, 5-milestone Planner, >=10-task Decomposer)."""

    _GOAL_TITLE_RE = re.compile(r"<goal_title>\s*(.*?)\s*</goal_title>", re.DOTALL | re.IGNORECASE)

    @staticmethod
    def _extract_approved_milestones(prompt_text: str) -> list[dict[str, Any]]:
        marker = "approved_milestones="
        if marker not in prompt_text:
            return []
        after = prompt_text.split(marker, 1)[1]
        json_line = after.splitlines()[0].strip()
        try:
            parsed = json.loads(json_line)
        except json.JSONDecodeError:
            return []
        return (
            [item for item in parsed if isinstance(item, dict)] if isinstance(parsed, list) else []
        )

    async def generate_structured(
        self,
        *,
        system_prompt: str = "",
        user_prompt: str = "",
        response_schema: dict[str, Any] | type[Any] | None = None,
        tools: Sequence[LLMToolDeclarationDTO | dict[str, Any]] | None = None,
        tool_executor: LLMToolExecutor | None = None,
        max_tool_calls: int = 2,
        thinking_level: str | None = None,
        timeout_seconds: float | None = None,
        tool_call_timeout_seconds: float | None = None,
    ) -> LLMGenerationResult:
        effective_prompt = f"{system_prompt}\n{user_prompt}"

        # Critics & Judge delegate straight to StubLLMAdapter
        if "[INDEPENDENT_CRITIC:" in effective_prompt or "[PROPOSAL_PAYLOAD]" in effective_prompt:
            return await super().generate_structured(
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

        is_milestone_schema = isinstance(response_schema, type) and issubclass(
            response_schema, MilestoneGenerationLLMOutput
        )
        if is_milestone_schema:
            base_res = await super().generate_structured(
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
            discovered_ids: list[str] = []
            for rec in base_res.raw_tool_results:
                if isinstance(rec.output, dict):
                    for c in rec.output.get("concepts", []):
                        if isinstance(c, dict) and c.get("concept_id"):
                            cid = str(c["concept_id"])
                            if cid not in discovered_ids:
                                discovered_ids.append(cid)

            title_match = self._GOAL_TITLE_RE.search(effective_prompt)
            goal_snippet = (title_match.group(1).strip() if title_match else "Lộ trình chuyên sâu")[
                :45
            ]
            phase_names = (
                "Nền tảng & Kiến trúc lõi",
                "Thành phần chính & Giao thức",
                "Độ tin cậy & Xử lý lỗi",
                "Bảo mật, Hiệu năng & Tối ưu",
                "Kiểm thử toàn diện & Production",
            )
            milestones_payload = []
            mock_efforts = (90, 120, 150, 120, 180)
            for seq, phase in enumerate(phase_names, start=1):
                req_concepts = (
                    [discovered_ids[(seq - 1) % len(discovered_ids)]] if discovered_ids else []
                )
                unverified = [] if req_concepts else [f"advanced-topic-{seq}"]
                milestones_payload.append(
                    {
                        "sequence_order": seq,
                        "title": f"Cột mốc {seq}: {phase} ({goal_snippet})",
                        "description": f"Học và thực hành {phase.lower()} cho {goal_snippet}.",
                        "learning_outcomes": [
                            f"Nắm vững nguyên lý và mô hình thiết kế {phase.lower()} (giai đoạn {seq})",
                            f"Triển khai và kiểm chứng thực tế bài tập Cột mốc {seq}",
                        ],
                        "completion_criteria": (
                            f"Hoàn thành bài kiểm tra thực hành và đạt chuẩn đầu ra Cột mốc {seq}"
                        ),
                        "estimated_effort_minutes": mock_efforts[(seq - 1) % len(mock_efforts)],
                        "required_concepts": req_concepts,
                        "unverified_concepts": unverified,
                        "dependencies": [] if seq == 1 else [seq - 1],
                    }
                )
            validated = MilestoneGenerationLLMOutput.model_validate(
                {
                    "milestones": milestones_payload,
                    "scope_summary": (
                        "Bao phủ đầy đủ 5 cột mốc thích ứng từ nền tảng đến triển khai production."
                    ),
                    "deferred_scope": [],
                }
            )
            return LLMGenerationResult(
                payload=validated.model_dump(mode="json"),
                prompt_tokens=base_res.prompt_tokens,
                output_tokens=base_res.output_tokens,
                thinking_tokens=base_res.thinking_tokens,
                model_id=base_res.model_id,
                raw_tool_results=base_res.raw_tool_results,
            )

        schema_props = (
            response_schema.get("properties", {}) if isinstance(response_schema, dict) else {}
        )
        approved_milestones = self._extract_approved_milestones(effective_prompt)
        if "tasks" in schema_props and approved_milestones:
            tasks: list[dict[str, Any]] = []
            dependencies: list[dict[str, Any]] = []
            total_ms = len(approved_milestones)
            for m_idx, m in enumerate(approved_milestones):
                mid = str(m["milestone_id"])
                seq = int(m.get("sequence_order", m_idx + 1))
                m_title = str(m.get("title", f"Cột mốc {seq}"))[:40]
                raw_outcomes = m.get("learning_outcomes") or []
                outcome_ids = [f"M{seq}-O{o_i}" for o_i in range(1, max(1, len(raw_outcomes)) + 1)]
                req_concepts = [
                    str(c).strip() for c in (m.get("required_concepts") or []) if str(c).strip()
                ]
                effort = int(m.get("estimated_effort_minutes", 120) or 120)
                n_tasks = max(2, min(4, math.ceil(effort / 120)))
                est_min = max(30, min(120, round(effort / n_tasks)))

                for t_i in range(n_tasks):
                    task_id = f"T{len(tasks) + 1}"
                    if t_i == 0:
                        t_type = "THEORY"
                    elif m_idx == total_ms - 1 and t_i == n_tasks - 1:
                        t_type = "PROJECT"
                    elif m_idx == total_ms - 2 and t_i == n_tasks - 1:
                        t_type = "REVIEW"
                    else:
                        t_type = "PRACTICE"
                    tasks.append(
                        {
                            "task_id": task_id,
                            "milestone_id": mid,
                            "title": f"[{task_id}] {t_type} Cột mốc {seq}: {m_title} (Phần {t_i + 1})",
                            "description": (
                                f"Thực hiện phiên {t_type} phần {t_i + 1} thuộc {m_title}."
                            ),
                            "task_type": t_type,
                            "learning_objective": (
                                f"Nắm vững và vận dụng nội dung {m_title} (phần {t_i + 1})"
                            ),
                            "completion_criteria": (
                                f"Hoàn thành bài kiểm tra đầu ra {task_id} của Cột mốc {seq}"
                            ),
                            "concept_ids": req_concepts,
                            "covered_outcome_ids": outcome_ids,
                            "resource_ids": [],
                            "estimated_minutes": est_min,
                        }
                    )
                    if len(tasks) > 1:
                        dependencies.append(
                            {
                                "predecessor_id": tasks[-2]["task_id"],
                                "successor_id": task_id,
                                "is_mandatory": True,
                            }
                        )
            validated_tasks = TaskProposalLLMOutput.model_validate(
                {"tasks": tasks, "dependencies": dependencies}
            )
            return LLMGenerationResult(
                payload=validated_tasks.model_dump(mode="json"),
                prompt_tokens=160,
                output_tokens=384,
                thinking_tokens=0,
                model_id=self.last_model_used or self.model_used,
            )

        return await super().generate_structured(
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


@dataclass(slots=True)
class _ScenarioEvalResult:
    outcome: dict[str, Any]
    latencies_ms: list[float] = field(default_factory=list)
    clarifier_latencies_ms: list[float] = field(default_factory=list)
    milestone_planner_latencies_ms: list[float] = field(default_factory=list)
    decomposer_latencies_ms: list[float] = field(default_factory=list)
    critics_judge_latencies_ms: list[float] = field(default_factory=list)
    weekly_latencies_ms: list[float] = field(default_factory=list)
    e2e_total_latencies_ms: list[float] = field(default_factory=list)
    total_runs: int = 0
    pass_at_1_count: int = 0
    pass_with_judge_verdict_count: int = 0
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
    clarifier_error_categories: list[str] = field(default_factory=list)
    milestone_planner_error_categories: list[str] = field(default_factory=list)
    decomposer_error_categories: list[str] = field(default_factory=list)
    generated_milestones_count: int = 0
    simulated_scope_approval_used: bool = False
    schema_check_calls: int = 0
    critic_schema_mismatch_count: int = 0
    schema_repair_attempts: int = 0
    structural_audit: dict[str, Any] = field(default_factory=dict)


_SENSITIVE_SPLIT_RE = re.compile(
    r"(?:thi\s*thử|mock\s*test|load\s*test|stress\s*test|kiểm\s*thử\s*(?:chịu\s*)?tải|tải\s*cao|benchmark|đối\s*chuẩn|đánh\s*giá\s*tổng\s*hợp|kiểm\s*tra\s*cuối)",
    re.IGNORECASE,
)

_SCHEDULING_ONLY_RULE_CODES: frozenset[str] = frozenset(
    {
        "FULL_SCOPE_CAPACITY_EXCEEDED",
        "CONDITIONAL_MAX_UTILIZATION_EXCEEDED",
        "FIT_CAPACITY_APPROVAL_REQUIRED",
        "CAPACITY_EXCEEDED_BEFORE_TARGET_DATE",
        "SCHEDULE_BLOCK_EFFORT_MISMATCH",
        "DAILY_QUOTA_EXCEEDED",
        "SLOT_BOUNDARY_VIOLATION",
        "DISABLED_WEEKDAY_VIOLATION",
        "PREDECESSOR_ORDER_VIOLATION",
        "NON_SPLITTABLE_TASK_SPLIT_ACROSS_DAYS",
    }
)


def _is_simulated_fit_capacity_accepted(scenario: dict[str, Any]) -> bool:
    """Return True only when the fixture explicitly declares simulated learner FIT_CAPACITY approval."""
    decision = scenario.get("simulated_learner_scope_decision")
    if isinstance(decision, dict):
        action = str(decision.get("action", "")).strip().upper()
        if action in {"ACCEPT_FIT_CAPACITY", "APPROVE_FIT_CAPACITY", "ACCEPT"}:
            return True
        if decision.get("accept_fit_capacity") is True:
            return True
    elif isinstance(decision, str):
        if decision.strip().upper() in {"ACCEPT_FIT_CAPACITY", "APPROVE_FIT_CAPACITY", "ACCEPT"}:
            return True
    return False


def _parse_iso_dt_safe(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.strip())
    except ValueError:
        return None


def _check_dag_acyclic_and_prereq_order(
    tasks: Sequence[dict[str, Any]],
    dependencies: Sequence[dict[str, Any]],
    blocks_by_task: dict[str, list[dict[str, Any]]],
) -> tuple[bool, bool]:
    """Return (dag_acyclic, prereq_ordered) for task list and dependencies."""
    task_ids = {
        str(t.get("task_id", "")).strip() for t in tasks if str(t.get("task_id", "")).strip()
    }
    adj: dict[str, list[str]] = defaultdict(list)
    indegree: dict[str, int] = {tid: 0 for tid in task_ids}
    valid_refs = True
    edges: list[tuple[str, str, bool]] = []
    for dep in dependencies:
        pred = str(dep.get("predecessor_id", "")).strip()
        succ = str(dep.get("successor_id", "")).strip()
        is_mand = bool(dep.get("is_mandatory", True))
        if not pred or not succ:
            continue
        if pred not in task_ids or succ not in task_ids or pred == succ:
            valid_refs = False
            continue
        adj[pred].append(succ)
        indegree[succ] = indegree.get(succ, 0) + 1
        edges.append((pred, succ, is_mand))

    queue = [tid for tid, deg in indegree.items() if deg == 0]
    visited = 0
    while queue:
        curr = queue.pop()
        visited += 1
        for nxt in adj.get(curr, []):
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                queue.append(nxt)
    dag_acyclic = valid_refs and (visited == len(task_ids))

    # Check temporal prerequisite ordering: predecessor end <= successor start
    earliest_start: dict[str, tuple[date, datetime | None]] = {}
    latest_end: dict[str, tuple[date, datetime | None]] = {}
    for t in tasks:
        tid = str(t.get("task_id", "")).strip()
        blks = blocks_by_task.get(tid, [])
        if blks:
            b_dates: list[date] = []
            b_starts: list[datetime] = []
            b_ends: list[datetime] = []
            for b in blks:
                raw_bd = b.get("block_date")
                if isinstance(raw_bd, str) and raw_bd.strip():
                    try:
                        b_dates.append(date.fromisoformat(raw_bd.strip()[:10]))
                    except ValueError:
                        pass
                st = _parse_iso_dt_safe(b.get("scheduled_start"))
                en = _parse_iso_dt_safe(b.get("scheduled_end"))
                if st is not None:
                    b_starts.append(st)
                if en is not None:
                    b_ends.append(en)
            if b_dates:
                earliest_start[tid] = (min(b_dates), min(b_starts) if b_starts else None)
                latest_end[tid] = (max(b_dates), max(b_ends) if b_ends else None)
        else:
            raw_sd = t.get("scheduled_date")
            if isinstance(raw_sd, str) and raw_sd.strip():
                try:
                    sd = date.fromisoformat(raw_sd.strip()[:10])
                    earliest_start[tid] = (sd, None)
                    latest_end[tid] = (sd, None)
                except ValueError:
                    pass

    prereq_ordered = True
    for pred, succ, is_mand in edges:
        if not is_mand:
            continue
        if pred in latest_end and succ in earliest_start:
            pred_d, pred_dt = latest_end[pred]
            succ_d, succ_dt = earliest_start[succ]
            if pred_d > succ_d:
                prereq_ordered = False
                break
            if (
                pred_d == succ_d
                and pred_dt is not None
                and succ_dt is not None
                and pred_dt > succ_dt
            ):
                prereq_ordered = False
                break

    return dag_acyclic, prereq_ordered


def _compute_case_structural_audit(
    *,
    milestones: Sequence[dict[str, Any]],
    proposal: dict[str, Any],
    availability: AvailabilityConfigurationDTO,
    start_date: date,
    target_date: date,
    scenario: dict[str, Any] | None = None,
    case_passed: bool | None = None,
    case_error: str | None = None,
    stage2_violations: Sequence[dict[str, Any]] | None = None,
    decomposer_violations: Sequence[dict[str, Any]] | None = None,
    scope_summary: str | None = None,
    deferred_scope: Sequence[str] | None = None,
    judge_status: str = "SKIPPED",
    pedagogical_score: float | None = None,
    injection_status: str = "NOT_APPLICABLE",
    audited_milestones_source: str = "fixture",
    require_proposal: bool = False,
    latency_ms: float | None = None,
    prompt_tokens: int = 0,
    output_tokens: int = 0,
    thinking_tokens: int = 0,
) -> dict[str, Any]:
    """Compute 4-category structural/pedagogical audit metrics and 3-layer verdicts."""
    ordered_ms = sorted(milestones, key=lambda m: int(m.get("sequence_order", 0) or 0))
    efforts = [int(m.get("estimated_effort_minutes", 0) or 0) for m in ordered_ms]
    total_ms_effort = sum(efforts)
    avail_minutes = SpatioTemporalRuleEngine.calculate_available_capacity_minutes(
        availability, start_date=start_date, target_date=target_date
    )
    cap_util = round(total_ms_effort / avail_minutes, 4) if avail_minutes > 0 else None
    modal_freq = max(Counter(efforts).values()) if efforts else 0
    effort_equal_ratio = round(modal_freq / len(efforts), 4) if efforts else 0.0
    all_efforts_equal = len(set(efforts)) <= 1 and len(efforts) > 1
    effort_balance_score = round(1.0 - effort_equal_ratio, 4) if len(efforts) > 1 else 1.0

    invariants_cfg = (scenario or {}).get("expected_invariants") or {}
    cond_cfg = (scenario or {}).get("conditional_constraints") or {}
    soft_cfg = (scenario or {}).get("soft_quality_targets") or {}
    enforce_cond_hard = bool(cond_cfg.get("enforce_hard", False))

    min_ms_target = int(
        cond_cfg.get("min_milestones", invariants_cfg.get("min_milestones", 4)) or 4
    )
    max_ms_target = int(cond_cfg.get("max_milestones", 6) or 6)
    proj_min_target = int(cond_cfg.get("project_min_minutes", 90) or 90)
    band_raw = soft_cfg.get("target_utilization_band", [0.70, 0.90])
    band_low = (
        float(band_raw[0]) if isinstance(band_raw, (list, tuple)) and len(band_raw) >= 2 else 0.70
    )
    band_high = (
        float(band_raw[1]) if isinstance(band_raw, (list, tuple)) and len(band_raw) >= 2 else 0.90
    )

    is_full_scope = not bool(deferred_scope) and (
        "FIT_CAPACITY" not in str(scope_summary or "").upper()
    )
    ms_orders = [int(m.get("sequence_order", 0) or 0) for m in ordered_ms]
    ms_contiguous = bool(ordered_ms) and ms_orders == list(range(1, len(ordered_ms) + 1))
    ms_fields_valid = bool(ordered_ms) and all(
        bool(str(m.get("title", "")).strip())
        and bool(m.get("learning_outcomes"))
        and int(m.get("estimated_effort_minutes", 0) or 0) > 0
        for m in ordered_ms
    )

    tasks = list(proposal.get("tasks") or []) if isinstance(proposal, dict) else []
    dependencies = list(proposal.get("dependencies") or []) if isinstance(proposal, dict) else []
    blocks = list(proposal.get("schedule_blocks") or []) if isinstance(proposal, dict) else []
    has_proposal = len(tasks) > 0

    total_task_minutes = sum(int(t.get("estimated_minutes", 0) or 0) for t in tasks)
    task_cap_util = (
        round(total_task_minutes / avail_minutes, 4)
        if (avail_minutes > 0 and has_proposal)
        else None
    )
    ms_vs_tasks_gap = (
        round(abs(total_task_minutes - total_ms_effort) / total_ms_effort, 4)
        if (has_proposal and total_ms_effort > 0)
        else None
    )

    linear_dep_ratio: float | None = None
    max_consec: int | None = None
    days_idle: int | None = None
    split_cross_day = 0
    sensitive_split_cross_day = 0
    adjacent_same_day_split_count = 0
    short_projects = 0
    dag_acyclic_ok = True
    prereq_ordered_ok = True
    task_and_outcome_conservation_ok = True
    slot_and_quota_compliance_ok = True
    unplaced_tasks_count = 0

    if has_proposal:
        task_ids = [str(t.get("task_id", "")).strip() for t in tasks]
        preds_by_task: dict[str, list[str]] = defaultdict(list)
        for dep in dependencies:
            pred = str(dep.get("predecessor_id", "")).strip()
            succ = str(dep.get("successor_id", "")).strip()
            if pred and succ:
                preds_by_task[succ].append(pred)
        non_initial = max(0, len(task_ids) - 1)
        linear_tasks = sum(
            1
            for i in range(1, len(task_ids))
            if preds_by_task.get(task_ids[i], []) == [task_ids[i - 1]]
        )
        linear_dep_ratio = round(linear_tasks / non_initial, 4) if non_initial > 0 else 0.0

        blocks_by_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
        active_dates_set: set[date] = set()
        minutes_by_date: dict[date, int] = defaultdict(int)
        for blk in blocks:
            tid = str(blk.get("task_id", "")).strip()
            if tid:
                blocks_by_task[tid].append(blk)
            raw_d = blk.get("block_date")
            if isinstance(raw_d, str) and raw_d.strip():
                try:
                    bd = date.fromisoformat(raw_d.strip()[:10])
                    active_dates_set.add(bd)
                    minutes_by_date[bd] += int(blk.get("scheduled_duration_minutes", 0) or 0)
                except ValueError:
                    pass
        if not active_dates_set:
            for t in tasks:
                raw_sd = t.get("scheduled_date")
                if isinstance(raw_sd, str) and raw_sd.strip():
                    try:
                        sd = date.fromisoformat(raw_sd.strip()[:10])
                        active_dates_set.add(sd)
                        minutes_by_date[sd] += int(t.get("estimated_minutes", 0) or 0)
                    except ValueError:
                        pass

        sorted_dates = sorted(active_dates_set)
        max_consec = 0
        streak = 0
        prev_d: date | None = None
        for d in sorted_dates:
            streak = streak + 1 if (prev_d is not None and d == prev_d + timedelta(days=1)) else 1
            max_consec = max(max_consec, streak)
            prev_d = d
        days_idle = (target_date - sorted_dates[-1]).days if sorted_dates else None

        for t in tasks:
            tid = str(t.get("task_id", "")).strip()
            est_m = int(t.get("estimated_minutes", 0) or 0)
            blks = blocks_by_task.get(tid, [])
            if blks:
                blk_sum = sum(int(b.get("scheduled_duration_minutes", 0) or 0) for b in blks)
                if blk_sum != est_m:
                    unplaced_tasks_count += 1
            elif not str(t.get("scheduled_date") or "").strip():
                unplaced_tasks_count += 1

            distinct_dates = {
                str(b.get("block_date", ""))[:10]
                for b in blks
                if str(b.get("block_date", "")).strip()
            }
            if len(distinct_dates) > 1:
                split_cross_day += 1
                if bool(t.get("is_non_splittable")) or _SENSITIVE_SPLIT_RE.search(
                    str(t.get("title", ""))
                ):
                    sensitive_split_cross_day += 1

            by_day: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for b in blks:
                day_str = str(b.get("block_date", ""))[:10]
                if day_str:
                    by_day[day_str].append(b)
            for day_blks in by_day.values():
                if len(day_blks) <= 1:
                    continue
                day_sorted = sorted(day_blks, key=lambda b: str(b.get("scheduled_start") or ""))
                for idx_b in range(len(day_sorted) - 1):
                    end_cur = _parse_iso_dt_safe(day_sorted[idx_b].get("scheduled_end"))
                    start_nxt = _parse_iso_dt_safe(day_sorted[idx_b + 1].get("scheduled_start"))
                    if end_cur is not None and start_nxt is not None and end_cur == start_nxt:
                        adjacent_same_day_split_count += 1
                        break

        short_projects = sum(
            1
            for t in tasks
            if str(t.get("task_type", "")).upper() == "PROJECT"
            and int(t.get("estimated_minutes", 0) or 0) < proj_min_target
        )

        dag_acyclic_ok, prereq_ordered_ok = _check_dag_acyclic_and_prereq_order(
            tasks, dependencies, blocks_by_task
        )

        ms_ids = {
            str(m.get("milestone_id", "")).strip()
            for m in ordered_ms
            if str(m.get("milestone_id", "")).strip()
        }
        covered_ms_ids = {
            str(t.get("milestone_id", "")).strip()
            for t in tasks
            if str(t.get("milestone_id", "")).strip()
        }
        required_outcome_ids = {
            str(o.get("id", "")).strip()
            for m in ordered_ms
            for o in (m.get("learning_outcomes") or [])
            if isinstance(o, dict) and str(o.get("id", "")).strip()
        }
        covered_outcome_ids = {
            str(oid).strip()
            for t in tasks
            for oid in (t.get("covered_outcome_ids") or [])
            if str(oid).strip()
        }
        outcomes_ok = required_outcome_ids.issubset(covered_outcome_ids)
        ms_covered_ok = ms_ids.issubset(covered_ms_ids) if ms_ids else True
        task_and_outcome_conservation_ok = (
            unplaced_tasks_count == 0 and outcomes_ok and ms_covered_ok
        )

        disabled_days = {str(d).lower() for d in availability.disabled_weekdays}
        active_slot_days = {
            str(s.day_of_week).lower() for s in availability.availability_slots if s.is_active
        }
        for d, mins in minutes_by_date.items():
            weekday_name = d.strftime("%A").lower()
            if weekday_name in disabled_days:
                slot_and_quota_compliance_ok = False
                break
            if str(availability.mode).upper() == "MODE_A":
                quota = int(
                    availability.daily_quota_minutes.get(
                        weekday_name, availability.default_daily_quota_minutes
                    )
                )
                if mins > quota:
                    slot_and_quota_compliance_ok = False
                    break
            elif str(availability.mode).upper() == "MODE_B" and active_slot_days:
                if weekday_name not in active_slot_days:
                    slot_and_quota_compliance_ok = False
                    break
    elif require_proposal:
        task_and_outcome_conservation_ok = False

    # Category 1: Hard Constraints
    hard_cap_limit = float(
        invariants_cfg.get(
            "full_scope_max_capacity_utilization",
            invariants_cfg.get("max_capacity_utilization", 1.0),
        )
        or 1.0
    )
    if is_full_scope:
        hard_cap_limit = min(1.0, hard_cap_limit)
    ms_cap_ok = cap_util is not None and cap_util <= (1.0 if is_full_scope else hard_cap_limit)
    task_cap_ok = task_cap_util is None or task_cap_util <= 1.0
    full_scope_hard_capacity_ok = bool(ms_cap_ok and task_cap_ok)
    non_splittable_integrity_ok = sensitive_split_cross_day == 0

    s2_codes = [
        str(v.get("rule_code", "")).strip()
        for v in (stage2_violations or [])
        if isinstance(v, dict) and str(v.get("rule_code", "")).strip()
    ]
    dec_codes = [
        str(v.get("rule_code", "")).strip()
        for v in (decomposer_violations or [])
        if isinstance(v, dict) and str(v.get("rule_code", "")).strip()
    ]

    if case_passed is not None:
        must_pass_tier1_ok = bool(case_passed)
    elif require_proposal:
        must_pass_tier1_ok = bool(has_proposal and ms_contiguous and ms_fields_valid)
    else:
        must_pass_tier1_ok = bool(ms_contiguous and ms_fields_valid)

    hard_constraints: dict[str, Any] = {
        "must_pass_tier1": must_pass_tier1_ok,
        "dag_acyclic_and_prereq_ordered": bool(dag_acyclic_ok and prereq_ordered_ok),
        "task_and_outcome_conservation": bool(task_and_outcome_conservation_ok),
        "slot_and_quota_compliance": bool(slot_and_quota_compliance_ok),
        "non_splittable_integrity": bool(non_splittable_integrity_ok),
        "full_scope_hard_capacity": bool(full_scope_hard_capacity_ok),
    }

    # Category 2: Conditional Constraints
    min_milestones_met = len(ordered_ms) >= min_ms_target
    max_milestones_met = len(ordered_ms) <= max_ms_target
    project_min_minutes_met = short_projects == 0
    conditional_violations: list[str] = []
    if not min_milestones_met:
        conditional_violations.append("MIN_MILESTONES_BELOW_TARGET")
    if not max_milestones_met:
        conditional_violations.append("MAX_MILESTONES_EXCEEDED")
    if has_proposal and not project_min_minutes_met:
        conditional_violations.append("PROJECT_UNDER_90_MIN")
    if cond_cfg.get("require_non_equal_milestone_effort") and all_efforts_equal:
        conditional_violations.append("UNIFORM_MILESTONE_EFFORT")
    if (
        cond_cfg.get("max_capacity_utilization") is not None
        and cap_util is not None
        and cap_util > float(cond_cfg["max_capacity_utilization"])
    ):
        conditional_violations.append("CONDITIONAL_MAX_UTILIZATION_EXCEEDED")

    conditional_constraints_report: dict[str, Any] = {
        "enforce_hard": enforce_cond_hard,
        "min_milestones_target": min_ms_target,
        "min_milestones_met": min_milestones_met,
        "max_milestones_target": max_ms_target,
        "max_milestones_met": max_milestones_met,
        "project_min_minutes_target": proj_min_target,
        "project_min_minutes_met": project_min_minutes_met if has_proposal else None,
        "violations": conditional_violations,
    }

    # Category 3: Soft Quality Metrics
    target_utilization_band_met = bool(cap_util is not None and band_low <= cap_util <= band_high)
    pacing_rest_day_compliance = (max_consec <= 6) if max_consec is not None else None
    end_buffer_present = (days_idle >= 1) if days_idle is not None else None

    soft_quality_warnings: list[str] = []
    if cap_util is not None and not target_utilization_band_met:
        soft_quality_warnings.append("UTILIZATION_OUTSIDE_TARGET_BAND")
    if all_efforts_equal:
        soft_quality_warnings.append("UNIFORM_MILESTONE_EFFORT")
    elif effort_equal_ratio >= 0.75 and len(efforts) >= 4:
        soft_quality_warnings.append("HIGH_MILESTONE_EFFORT_UNIFORMITY")
    if pacing_rest_day_compliance is False:
        soft_quality_warnings.append("CONSECUTIVE_STUDY_DAYS_GT_6")
    if end_buffer_present is False:
        soft_quality_warnings.append("NO_END_BUFFER_BEFORE_DEADLINE")
    if has_proposal and adjacent_same_day_split_count > 0:
        soft_quality_warnings.append("ADJACENT_SAME_DAY_TASK_SPLITS")

    util_band_score = (
        1.0
        if target_utilization_band_met
        else (
            0.0
            if (cap_util is None or cap_util > 1.0)
            else round(max(0.0, 1.0 - abs(cap_util - ((band_low + band_high) / 2.0)) / 0.30), 4)
        )
    )
    if has_proposal:
        pacing_score = 1.0 if pacing_rest_day_compliance else 0.0
        buffer_score = 1.0 if end_buffer_present else 0.0
        soft_quality_score = round(
            (util_band_score + effort_balance_score + pacing_score + buffer_score) / 4.0, 4
        )
    else:
        soft_quality_score = round((util_band_score + effort_balance_score) / 2.0, 4)

    soft_quality_metrics: dict[str, Any] = {
        "target_utilization_band": [band_low, band_high],
        "target_utilization_band_met": target_utilization_band_met,
        "target_utilization_band_score": util_band_score,
        "effort_balance_score": effort_balance_score,
        "pacing_rest_day_compliance": pacing_rest_day_compliance,
        "end_buffer_present": end_buffer_present,
        "adjacent_same_day_split_free": (adjacent_same_day_split_count == 0)
        if has_proposal
        else None,
        "soft_quality_score": soft_quality_score,
    }

    # Category 4: Diagnostic Metrics Only
    diagnostic_metrics: dict[str, Any] = {
        "all_efforts_equal": all_efforts_equal,
        "effort_equal_ratio": effort_equal_ratio,
        "linear_dependency_ratio": linear_dep_ratio,
        "milestone_vs_tasks_gap": ms_vs_tasks_gap,
        "capacity_utilization": cap_util,
        "task_capacity_utilization": task_cap_util,
        "latency_ms": latency_ms,
        "tokens": {
            "prompt_tokens": prompt_tokens,
            "output_tokens": output_tokens,
            "thinking_tokens": thinking_tokens,
        },
    }

    # 3 Separate Layer Verdicts: structural_validity, scheduling_feasibility, pedagogical_quality
    structural_failure_reasons: list[str] = []
    scheduling_failure_reasons: list[str] = []

    if not ms_contiguous or not ms_fields_valid:
        structural_failure_reasons.append("MILESTONE_TIER1_STRUCTURAL_INVALID")
    if invariants_cfg.get("min_milestones") is not None and len(ordered_ms) < int(
        invariants_cfg["min_milestones"]
    ):
        structural_failure_reasons.append("MIN_MILESTONES_BELOW_TARGET")

    if not full_scope_hard_capacity_ok:
        scheduling_failure_reasons.append("FULL_SCOPE_CAPACITY_EXCEEDED")
    if not non_splittable_integrity_ok:
        scheduling_failure_reasons.append("NON_SPLITTABLE_TASK_SPLIT_ACROSS_DAYS")

    if has_proposal:
        if not dag_acyclic_ok:
            structural_failure_reasons.append("DAG_CYCLE_OR_INVALID_DEPENDENCY_REF")
        if not prereq_ordered_ok:
            scheduling_failure_reasons.append("PREREQUISITE_ORDER_VIOLATION")
        if unplaced_tasks_count > 0:
            scheduling_failure_reasons.append("UNSCHEDULED_TASKS_DROPPED")
        if not task_and_outcome_conservation_ok and unplaced_tasks_count == 0:
            structural_failure_reasons.append("TASK_OR_OUTCOME_CONSERVATION_VIOLATION")
        if not slot_and_quota_compliance_ok:
            scheduling_failure_reasons.append("SLOT_OR_QUOTA_COMPLIANCE_VIOLATION")
        min_tasks_req = int(invariants_cfg.get("min_tasks", 1) or 1)
        if len(tasks) < min_tasks_req:
            structural_failure_reasons.append("INSUFFICIENT_TASKS")

    if injection_status == "LEAKED":
        structural_failure_reasons.append("PROMPT_INJECTION_LEAKED")

    for code in s2_codes:
        if code in _SCHEDULING_ONLY_RULE_CODES:
            if code not in scheduling_failure_reasons:
                scheduling_failure_reasons.append(code)
        else:
            if code not in structural_failure_reasons:
                structural_failure_reasons.append(code)

    for code in dec_codes:
        if code in _SCHEDULING_ONLY_RULE_CODES:
            if code not in scheduling_failure_reasons:
                scheduling_failure_reasons.append(code)
        else:
            if code not in structural_failure_reasons:
                structural_failure_reasons.append(code)

    if enforce_cond_hard and conditional_violations:
        for cv in conditional_violations:
            if cv == "CONDITIONAL_MAX_UTILIZATION_EXCEEDED":
                if cv not in scheduling_failure_reasons:
                    scheduling_failure_reasons.append(cv)
            else:
                tag = f"CONDITIONAL_CONSTRAINT_ENFORCED:{cv}"
                if tag not in structural_failure_reasons:
                    structural_failure_reasons.append(tag)

    if case_passed is False and not has_proposal:
        # Determine whether the failure was purely scheduling/feasibility at Stage 2/3 or structural/upstream
        only_scheduling_s2 = bool(s2_codes) and all(
            c in _SCHEDULING_ONLY_RULE_CODES for c in s2_codes
        )
        only_scheduling_dec = bool(dec_codes) and all(
            c in _SCHEDULING_ONLY_RULE_CODES for c in dec_codes
        )
        if only_scheduling_s2 or only_scheduling_dec:
            if not scheduling_failure_reasons:
                scheduling_failure_reasons.append(case_error or "SCHEDULING_FEASIBILITY_FAILED")
        else:
            err_tag = case_error or "PROPOSAL_GENERATION_FAILED"
            if err_tag not in structural_failure_reasons:
                structural_failure_reasons.append(err_tag)
            if not scheduling_failure_reasons:
                scheduling_failure_reasons.append("NO_VALID_SCHEDULE_PRODUCED")

    structural_validity = len(structural_failure_reasons) == 0
    scheduling_feasibility = len(scheduling_failure_reasons) == 0
    failure_reasons_by_layer: dict[str, list[str]] = {
        "structural_validity": structural_failure_reasons,
        "scheduling_feasibility": scheduling_failure_reasons,
        "conditional_constraints": conditional_violations,
        "soft_quality_warnings": soft_quality_warnings,
    }
    pedagogical_quality: dict[str, Any] = {
        "soft_quality_score": soft_quality_score,
        "soft_quality_warnings": soft_quality_warnings,
        "soft_quality_metrics": soft_quality_metrics,
        "judge_status": judge_status,
        "judge_score": pedagogical_score,
    }

    return {
        "has_proposal": has_proposal,
        "audited_milestones_source": audited_milestones_source,
        "audited_milestones_count": len(ordered_ms),
        "capacity_utilization": cap_util,
        "task_capacity_utilization": task_cap_util,
        "effort_equal_ratio": effort_equal_ratio,
        "all_efforts_equal": all_efforts_equal,
        "milestone_vs_tasks_gap": ms_vs_tasks_gap,
        "linear_dependency_ratio": linear_dep_ratio,
        "max_consecutive_study_days": max_consec,
        "days_idle_before_deadline": days_idle,
        "tasks_split_across_days_count": split_cross_day,
        "sensitive_tasks_split_across_days_count": sensitive_split_cross_day,
        "adjacent_same_day_split_count": adjacent_same_day_split_count,
        "short_project_under_90_count": short_projects,
        "structural_validity": structural_validity,
        "scheduling_feasibility": scheduling_feasibility,
        "pedagogical_quality": pedagogical_quality,
        "failure_reasons_by_layer": failure_reasons_by_layer,
        "invariant_categories": {
            "hard_constraints": hard_constraints,
            "conditional_constraints": conditional_constraints_report,
            "soft_quality_metrics": soft_quality_metrics,
            "diagnostic_metrics": diagnostic_metrics,
        },
    }


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


def _build_decomposer_inputs(
    scenario: dict[str, Any],
    milestones: Sequence[dict[str, Any]],
    *,
    effective_parallel: bool,
    clarification_summary: str = "",
    include_budget_context: bool = True,
) -> tuple[list[Milestone], set[UUID], str, str]:
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
    clar_line = (
        f"CLARIFICATION_CONTEXT: {PromptSanitizer.sanitize(clarification_summary, wrap_xml=True)}\n"
        if clarification_summary.strip()
        else ""
    )
    budget_suffix = ""
    if include_budget_context:
        availability_dto = _build_availability(scenario.get("availability", {}))
        start_d = date.fromisoformat(str(scenario["start_date"]))
        raw_target = scenario.get("target_date") or scenario.get("goal", {}).get("target_date")
        target_d = date.fromisoformat(str(raw_target)) if raw_target else None
        raw_cap = scenario.get("daily_workload_cap_minutes")
        budget = RoadmapContextBuilder.compute_schedule_budget(
            availability=availability_dto,
            milestones=milestones,
            start_date=start_d,
            target_date=target_d,
            learner_profile=scenario.get("learner_profile"),
            existing_tasks=scenario.get("existing_active_tasks")
            or scenario.get("existing_tasks")
            or (),
            daily_workload_cap_minutes=int(raw_cap) if raw_cap is not None else None,
            default_milestone_effort_minutes=120,
        )
        budget_suffix = f"\nprecomputed_schedule_budget: {json.dumps(budget, ensure_ascii=False)}"
    user_prompt = (
        f"GENERATE_PROPOSAL_TASKS\n"
        f"GOAL: {PromptSanitizer.sanitize(str(scenario['goal'].get('title', '')), wrap_xml=True)}\n"
        f"DESCRIPTION: {sanitized_goal}\n"
        f"{clar_line}"
        f"PLANNING_WINDOW: {scenario['start_date']}..{scenario['target_date']}\n"
        f"MILESTONE_IDS: {','.join(str(m['milestone_id']) for m in milestones)}\n"
        f"required_concepts={','.join(all_required_concepts)}\n"
        f"approved_milestones={milestone_json}\n"
        f"skill=learning-task-decomposer"
        f"{budget_suffix}"
    )
    return milestone_entities, valid_milestone_ids, milestone_json, user_prompt


def _merge_clarification_answers_into_goal(
    goal: Goal,
    scenario: dict[str, Any],
    clarifier_output: ClarificationQuestionsLLMOutput,
) -> str:
    raw_answers = scenario.get("clarification_answers")
    dim_answers: dict[str, str] = {}
    if isinstance(raw_answers, dict):
        for k, v in raw_answers.items():
            key_str = str(k).strip().upper()
            val_str = str(v).strip()
            if key_str and val_str:
                dim_answers[key_str] = val_str
    elif isinstance(raw_answers, list):
        for item in raw_answers:
            if isinstance(item, dict):
                key_str = (
                    str(item.get("diagnostic_dimension") or item.get("dimension") or "")
                    .strip()
                    .upper()
                )
                val_str = str(item.get("answer") or "").strip()
                if key_str and val_str:
                    dim_answers[key_str] = val_str

    answers_list: list[dict[str, Any]] = []
    covered_dims: set[str] = set()
    for q_idx, q in enumerate(clarifier_output.questions, start=1):
        dim = str(getattr(q, "diagnostic_dimension", "") or "PRIOR_KNOWLEDGE").strip().upper()
        q_text = str(getattr(q, "text", "") or getattr(q, "question", "")).strip()
        ans_text = dim_answers.get(dim)
        if not ans_text and getattr(q, "options", None):
            ans_text = str(q.options[0])
        if ans_text:
            covered_dims.add(dim)
            answers_list.append(
                {
                    "question_id": f"q{q_idx}",
                    "question_text": q_text,
                    "diagnostic_dimension": dim,
                    "answer": ans_text,
                }
            )

    facts_list: list[dict[str, Any]] = []
    for dim, ans_text in dim_answers.items():
        facts_list.append(
            {
                "dimension": dim,
                "status": GapStatus.KNOWN.value,
                "provenance": "USER_CONFIRMED",
                "value": ans_text,
            }
        )
        if dim not in covered_dims:
            answers_list.append(
                {
                    "question_id": f"dim_{dim.lower()}",
                    "question_text": f"Thông tin bổ sung cho chiều {dim}",
                    "diagnostic_dimension": dim,
                    "answer": ans_text,
                }
            )

    payload = ClarificationContextPayload(
        session_id=str(generate_uuid7()),
        status="ANSWERED" if answers_list or facts_list else "NOT_REQUIRED",
        answers=answers_list,
        facts=facts_list,
        rounds_completed=1,
    )
    goal.update_clarification(payload.to_json_str(), now=datetime.now(UTC))
    return "; ".join(f"{a['diagnostic_dimension']}: {a['answer']}" for a in answers_list)


async def _run_e2e_stage1_clarifier(
    *,
    scenario: dict[str, Any],
    availability: AvailabilityConfigurationDTO,
    provider: LLMProviderPort,
    clarifier_tpl: PromptTemplate,
    user_id: UUID,
) -> tuple[Goal, str, int, int, int, int]:
    settings = get_settings()
    start_d = date.fromisoformat(str(scenario["start_date"]))
    target_d = date.fromisoformat(str(scenario["target_date"]))
    weekly_avail_minutes = SpatioTemporalRuleEngine.calculate_available_capacity_minutes(
        availability,
        start_date=start_d,
        target_date=start_d + timedelta(days=6),
    )
    goal = Goal(
        id=generate_uuid7(),
        user_id=user_id,
        title=str(scenario["goal"].get("title", "")),
        raw_description=str(scenario["goal"].get("raw_description", "")),
        target_date=target_d,
        prior_knowledge_level=str(scenario.get("learner_level", "INTERMEDIATE")),
    )
    information_gaps = InformationGapAnalyzer().analyze(
        goal=goal,
        provenance=GoalFactProvenance(),
        weekly_commitment_hours=None,
        availability_weekly_minutes=weekly_avail_minutes,
    )
    question_gaps = InformationGapAnalyzer().select_question_gaps(information_gaps, limit=3)
    context_block = RoadmapContextBuilder.build_clarification_context(goal)
    gaps_block = "\n".join(
        f"- {gap.dimension}: {gap.status.value}; ảnh hưởng={gap.roadmap_decision}"
        for gap in question_gaps
    )
    effective_ctx = (
        f"{context_block}\n\n[INFORMATION_GAPS_TO_CLARIFY]\n{gaps_block}"
        if gaps_block
        else context_block
    )
    known_dims = [gap.dimension for gap in information_gaps if gap.status is GapStatus.KNOWN]
    user_prompt = build_goal_clarifier_prompt(
        effective_ctx,
        known_dimensions=known_dims,
        gap_count=max(1, len(question_gaps)),
    )

    exec_res = await AIExecutionManager(
        provider=provider,
        manage_quota=False,
        timeout_seconds=float(settings.ai_clarifier_timeout_seconds),
        tool_call_timeout_seconds=float(settings.ai_tool_call_timeout_seconds),
        max_retries=1,
        retry_predicate=default_ai_retry_predicate,
    ).execute(
        user_id=user_id,
        operation_type="GOAL_CLARIFICATION",
        system_prompt=clarifier_tpl.system_template,
        user_prompt=user_prompt,
        response_schema=ClarificationQuestionsLLMOutput,
        model_name=getattr(provider, "model_identifier", "gemini-3.8-flash"),
        thinking_level=GOAL_CLARIFIER_SKILL.thinking_level,
        prompt_template=clarifier_tpl,
    )
    clarifier_out = (
        exec_res.value
        if isinstance(exec_res.value, ClarificationQuestionsLLMOutput)
        else ClarificationQuestionsLLMOutput.model_validate(exec_res.value)
    )
    clarification_summary = _merge_clarification_answers_into_goal(goal, scenario, clarifier_out)
    p_tok = int(exec_res.prompt_tokens or 0)
    t_tok = int(exec_res.thinking_tokens or 0)
    o_tok = max(int(exec_res.completion_tokens or 0), t_tok)
    return goal, clarification_summary, p_tok, o_tok, t_tok, int(exec_res.repair_attempts or 0)


async def _run_e2e_stage2_milestone_planner(
    *,
    scenario: dict[str, Any],
    goal: Goal,
    provider: LLMProviderPort,
    planner_tpl: PromptTemplate,
    user_id: UUID,
    apply_milestone_effort_allocator: bool = False,
) -> tuple[list[dict[str, Any]], int, int, int, int]:
    settings = get_settings()
    start_d = date.fromisoformat(str(scenario["start_date"]))
    target_d = date.fromisoformat(str(scenario["target_date"]))
    roadmap = Roadmap(
        id=generate_uuid7(),
        user_id=user_id,
        goal_id=goal.id,
        title=goal.title,
        description=goal.raw_description,
        start_date=start_d,
        target_date=target_d,
    )
    kb_repo = InMemoryKnowledgeBaseRepository()
    kb_concepts, kb_graphs = await RoadmapContextBuilder.prefetch_milestone_kb_evidence(
        kb_repo,
        query_text=f"{goal.title} {goal.raw_description or ''}",
        learner_level=goal.prior_knowledge_level,
        domain=str(scenario.get("domain") or "").strip() or None,
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
    exec_res = await AIExecutionManager(
        provider=provider,
        manage_quota=False,
        timeout_seconds=float(settings.ai_milestone_planner_timeout_seconds),
        tool_call_timeout_seconds=float(settings.ai_tool_call_timeout_seconds),
        max_retries=0,
    ).execute(
        user_id=user_id,
        operation_type="MILESTONE_GEN",
        system_prompt=planner_tpl.system_template,
        user_prompt=user_prompt,
        response_schema=MilestoneGenerationLLMOutput,
        model_name=getattr(provider, "model_identifier", "gemini-3.8-flash"),
        tools=None,
        tool_executor=None,
        max_tool_calls=0,
        thinking_level=MILESTONE_PLANNER_SKILL.thinking_level,
        prompt_template=planner_tpl,
    )
    parsed = (
        exec_res.value
        if isinstance(exec_res.value, MilestoneGenerationLLMOutput)
        else MilestoneGenerationLLMOutput.model_validate(exec_res.value)
    )
    sorted_items = sorted(parsed.milestones, key=lambda item: int(item.sequence_order))
    raw_dicts = [item.model_dump(mode="json") for item in sorted_items]
    p_tok = int(exec_res.prompt_tokens or 0)
    t_tok = int(exec_res.thinking_tokens or 0)
    o_tok = max(int(exec_res.completion_tokens or 0), t_tok)
    repairs_count = int(exec_res.repair_attempts or 0)

    scope_summary_str = str(parsed.scope_summary or "").strip()
    deferred_list = [str(x).strip() for x in (parsed.deferred_scope or []) if str(x).strip()]
    is_fit_capacity = bool(deferred_list) or ("FIT_CAPACITY" in scope_summary_str.upper())
    simulated_approval_used = bool(
        is_fit_capacity and _is_simulated_fit_capacity_accepted(scenario)
    )

    normalized_milestones: list[dict[str, Any]] = []
    for seq_idx, item in enumerate(sorted_items, start=1):
        outcomes = [
            {"id": f"M{seq_idx}-O{o_idx}", "description": str(o_text).strip()}
            for o_idx, o_text in enumerate(item.learning_outcomes, start=1)
            if str(o_text).strip()
        ]
        normalized_milestones.append(
            {
                "milestone_id": str(generate_uuid7()),
                "sequence_order": seq_idx,
                "title": str(item.title).strip(),
                "description": str(item.description).strip(),
                "learning_outcomes": outcomes,
                "completion_criteria": str(item.completion_criteria).strip(),
                "estimated_effort_minutes": int(item.estimated_effort_minutes),
                "required_concepts": [
                    str(c).strip() for c in item.required_concepts if str(c).strip()
                ],
                "unverified_concepts": [
                    str(c).strip() for c in item.unverified_concepts if str(c).strip()
                ],
                "scope_summary": scope_summary_str,
                "deferred_scope": deferred_list,
                "simulated_scope_approval_used": simulated_approval_used,
            }
        )

    def _raise_stage2_gate_error(
        message: str,
        violations_payload: list[dict[str, object]],
    ) -> None:
        gate_exc = ProposalValidationGateError(
            message=message,
            code="VALIDATION_GATE",
            violations=violations_payload,
        )
        setattr(gate_exc, "generated_milestones", normalized_milestones)
        setattr(gate_exc, "scope_summary", scope_summary_str)
        setattr(gate_exc, "deferred_scope", deferred_list)
        setattr(gate_exc, "simulated_scope_approval_used", simulated_approval_used)
        setattr(gate_exc, "prompt_tokens", p_tok)
        setattr(gate_exc, "output_tokens", o_tok)
        setattr(gate_exc, "thinking_tokens", t_tok)
        setattr(gate_exc, "repair_attempts", repairs_count)
        raise gate_exc

    violations = ProposalValidationGateOrchestrator.validate_ai_milestones_tier1(raw_dicts)
    if violations:
        _raise_stage2_gate_error(
            "Milestone Planner output failed Tier 1 validation",
            [v.to_dict() for v in violations],
        )

    invariants = scenario.get("expected_invariants", {})
    cond_constraints = scenario.get("conditional_constraints", {})
    enforce_cond_hard = bool(cond_constraints.get("enforce_hard", False))

    min_ms = (
        cond_constraints.get("min_milestones")
        if (enforce_cond_hard and cond_constraints.get("min_milestones") is not None)
        else invariants.get("min_milestones")
    )
    if min_ms is not None and len(sorted_items) < int(min_ms):
        _raise_stage2_gate_error(
            f"Expected at least {min_ms} milestones, got {len(sorted_items)}",
            [
                {
                    "rule_code": "MIN_MILESTONES_BELOW_TARGET",
                    "field": "milestones",
                    "expected_bound": f">= {min_ms}",
                    "actual_value": str(len(sorted_items)),
                }
            ],
        )

    if enforce_cond_hard and cond_constraints.get("max_milestones") is not None:
        max_ms = int(cond_constraints["max_milestones"])
        if len(sorted_items) > max_ms:
            _raise_stage2_gate_error(
                f"Expected at most {max_ms} milestones (conditional enforce_hard=True), got {len(sorted_items)}",
                [
                    {
                        "rule_code": "MAX_MILESTONES_EXCEEDED",
                        "field": "milestones",
                        "expected_bound": f"<= {max_ms}",
                        "actual_value": str(len(sorted_items)),
                    }
                ],
            )

    if (
        apply_milestone_effort_allocator
        and getattr(settings, "milestone_effort_allocator_enabled", True)
        and scenario.get("availability")
    ):
        avail_dto_alloc = _build_availability(scenario["availability"])
        p_hard, _ = SpatioTemporalRuleEngine.calculate_hard_packable_capacity(
            avail_dto_alloc,
            start_date=start_d,
            target_date=target_d,
        )
        allocator_inputs = [
            {
                "sequence_order": nm["sequence_order"],
                "milestone_id": nm["milestone_id"],
                "title": nm["title"],
                "description": nm["description"],
                "learning_outcomes": [o["description"] for o in nm["learning_outcomes"]],
                "completion_criteria": nm["completion_criteria"],
                "estimated_effort_minutes": nm["estimated_effort_minutes"],
                "required_concepts": nm["required_concepts"],
                "unverified_concepts": nm["unverified_concepts"],
                "dependencies": [
                    int(d)
                    for d in (sorted_items[seq_idx - 1].dependencies or [])
                    if isinstance(d, int)
                ],
            }
            for seq_idx, nm in enumerate(normalized_milestones, start=1)
        ]
        prelim_res = MilestoneEffortAllocator.allocate(
            allocator_inputs,
            hard_packable_capacity_minutes=p_hard,
            prior_knowledge_level=goal.prior_knowledge_level,
            target_utilization=float(getattr(settings, "ai_milestone_target_utilization", 0.85)),
            gamma_min=float(getattr(settings, "ai_milestone_min_effort_ratio", 0.65)),
            alpha_by_level={
                "BEGINNER": float(getattr(settings, "ai_milestone_alpha_beginner", 1.15)),
                "INTERMEDIATE": float(getattr(settings, "ai_milestone_alpha_intermediate", 1.00)),
                "ADVANCED": float(getattr(settings, "ai_milestone_alpha_advanced", 1.10)),
            },
            start_date=start_d,
            target_date=target_d,
            availability=avail_dto_alloc,
        )
        efforts_by_seq = {
            bd.sequence_order: (
                bd.normalized_planned_effort_minutes
                if bd.kept_in_scope and bd.normalized_planned_effort_minutes > 0
                else bd.estimated_effort_minutes
            )
            for bd in prelim_res.breakdowns
        }
        for nm in normalized_milestones:
            nm["estimated_effort_minutes"] = efforts_by_seq.get(
                nm["sequence_order"], nm["estimated_effort_minutes"]
            )
            nm["preliminary_feasibility_status"] = prelim_res.status
        if prelim_res.status == "FIT_CAPACITY_REQUIRES_APPROVAL":
            is_fit_capacity = True
            deferred_list = [str(item.get("title", "")) for item in prelim_res.deferred_scope]
            scope_summary_str = (
                f"FIT_CAPACITY (v{prelim_res.scope_proposal_version}): {scope_summary_str}"
            ).strip()
            simulated_approval_used = _is_simulated_fit_capacity_accepted(scenario)
            for nm in normalized_milestones:
                nm["scope_summary"] = scope_summary_str
                nm["deferred_scope"] = deferred_list
                nm["simulated_scope_approval_used"] = simulated_approval_used
            if simulated_approval_used:
                kept_seqs = {int(item["sequence_order"]) for item in prelim_res.kept_scope}
                normalized_milestones = [
                    nm for nm in normalized_milestones if nm["sequence_order"] in kept_seqs
                ]
        elif prelim_res.status == "PRELIMINARY_UNSCHEDULABLE":
            _raise_stage2_gate_error(
                "MilestoneEffortAllocator flagged PRELIMINARY_UNSCHEDULABLE",
                [
                    {
                        "rule_code": "FULL_SCOPE_CAPACITY_EXCEEDED",
                        "field": "estimated_effort_minutes",
                        "expected_bound": f"<= {p_hard}",
                        "actual_value": str(prelim_res.minimum_defensible_total_minutes),
                    }
                ],
            )

    if is_fit_capacity and not simulated_approval_used:
        _raise_stage2_gate_error(
            "FIT_CAPACITY scope proposal requires explicit simulated_learner_scope_decision approval",
            [
                {
                    "rule_code": "FIT_CAPACITY_APPROVAL_REQUIRED",
                    "field": "deferred_scope",
                    "expected_bound": "simulated_learner_scope_decision=ACCEPT_FIT_CAPACITY",
                    "actual_value": "None",
                }
            ],
        )

    efforts = [int(nm["estimated_effort_minutes"]) for nm in normalized_milestones]
    if scenario.get("availability"):
        avail_dto = _build_availability(scenario["availability"])
        avail_minutes = SpatioTemporalRuleEngine.calculate_available_capacity_minutes(
            avail_dto,
            start_date=start_d,
            target_date=target_d,
        )
        if avail_minutes > 0:
            actual_util = sum(efforts) / avail_minutes
            if enforce_cond_hard and cond_constraints.get("max_capacity_utilization") is not None:
                hard_max_util = float(cond_constraints["max_capacity_utilization"])
            else:
                configured_max = float(
                    invariants.get(
                        "full_scope_max_capacity_utilization",
                        invariants.get("max_capacity_utilization", 1.0),
                    )
                    or 1.0
                )
                hard_max_util = min(1.0, configured_max) if not is_fit_capacity else 1.0
            if actual_util > hard_max_util:
                rule_code = (
                    "FULL_SCOPE_CAPACITY_EXCEEDED"
                    if actual_util > 1.0
                    else "CONDITIONAL_MAX_UTILIZATION_EXCEEDED"
                )
                _raise_stage2_gate_error(
                    (
                        f"Milestone capacity_utilization={actual_util:.4f} exceeds "
                        f"hard_max_capacity_utilization={hard_max_util:.4f} "
                        f"({sum(efforts)}m / {avail_minutes}m)"
                    ),
                    [
                        {
                            "rule_code": rule_code,
                            "field": "estimated_effort_minutes",
                            "expected_bound": f"<= {hard_max_util:.4f}",
                            "actual_value": f"{actual_util:.4f}",
                        }
                    ],
                )

    if (
        enforce_cond_hard
        and bool(cond_constraints.get("require_non_equal_milestone_effort"))
        and len(efforts) > 1
        and len(set(efforts)) <= 1
    ):
        _raise_stage2_gate_error(
            (
                f"All {len(efforts)} milestones have identical effort={efforts[0]}m "
                "(conditional require_non_equal_milestone_effort=True)"
            ),
            [
                {
                    "rule_code": "UNIFORM_MILESTONE_EFFORT",
                    "field": "estimated_effort_minutes",
                    "expected_bound": "non-uniform efforts",
                    "actual_value": str(efforts),
                }
            ],
        )

    return normalized_milestones, p_tok, o_tok, t_tok, repairs_count


async def _evaluate_scenario(
    idx: int,
    scenario: dict[str, Any],
    *,
    use_live: bool,
    e2e: bool = False,
    effective_trials: int,
    decomposer_tpl: PromptTemplate,
    clarifier_tpl: PromptTemplate | None = None,
    milestone_planner_tpl: PromptTemplate | None = None,
    decomposer_thinking_level: str | None = None,
    judge_thinking_level: str | None = None,
    judge_timeout_seconds: float | None = None,
    include_weekly: bool = True,
    include_budget_context: bool = True,
    parallel_critics_and_judge: bool | None = None,
    apply_milestone_effort_allocator: bool = False,
    clarifier_provider_factory: ProviderFactory | None = None,
    milestone_planner_provider_factory: ProviderFactory | None = None,
    decomposer_provider_factory: ProviderFactory | None = None,
    judge_provider_factory: ProviderFactory | None = None,
    weekly_provider_factory: ProviderFactory | None = None,
) -> _ScenarioEvalResult:
    effective_parallel = (
        ((use_live or e2e) and judge_provider_factory is None)
        if parallel_critics_and_judge is None
        else bool(parallel_critics_and_judge)
    )
    availability = _build_availability(scenario["availability"])
    milestones = list(scenario.get("milestones", []))
    milestone_entities, valid_milestone_ids, milestone_json, user_prompt = _build_decomposer_inputs(
        scenario,
        milestones,
        effective_parallel=effective_parallel,
        include_budget_context=include_budget_context,
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
    trial_pass_at_1_flags: list[bool] = []
    trial_judge_statuses: list[str] = []
    audited_milestones_source = "fixture" if milestones else "none"
    case_stage2_violations: list[dict[str, Any]] = []
    case_decomposer_violations: list[dict[str, Any]] = []
    case_scope_summary: str | None = None
    case_deferred_scope: list[str] = []

    case_judge_status = "SKIPPED_NO_PROPOSAL"
    case_pedagogical_score: float | None = None
    judge_error_category: str | None = None
    parallel_wf_repo = _EvalWorkflowRepo()

    for trial in range(effective_trials):
        result.total_runs += 1
        trial_p_tok = 0
        trial_o_tok = 0
        trial_t_tok = 0
        e2e_t0 = time.perf_counter()

        trial_milestones = list(milestones)
        trial_milestone_entities = milestone_entities
        trial_valid_milestone_ids = valid_milestone_ids
        trial_milestone_json = milestone_json
        trial_user_prompt = user_prompt

        if e2e:
            eval_user_id = generate_uuid7()
            effective_clarifier_tpl = clarifier_tpl or build_planning_prompt_registry().latest(
                GOAL_CLARIFIER_SKILL.skill_id
            )
            effective_planner_tpl = (
                milestone_planner_tpl
                or build_planning_prompt_registry().latest(MILESTONE_PLANNER_SKILL.skill_id)
            )
            clarifier_provider = (
                clarifier_provider_factory(idx, scenario)
                if clarifier_provider_factory is not None
                else (LiteLLMAdapter() if use_live else _E2EStubLLMAdapter())
            )
            c_t0 = time.perf_counter()
            result.schema_check_calls += 1
            try:
                (
                    clarified_goal,
                    clarification_summary,
                    c_p_tok,
                    c_o_tok,
                    c_t_tok,
                    c_repairs,
                ) = await _run_e2e_stage1_clarifier(
                    scenario=scenario,
                    availability=availability,
                    provider=clarifier_provider,
                    clarifier_tpl=effective_clarifier_tpl,
                    user_id=eval_user_id,
                )
                result.clarifier_latencies_ms.append(
                    round((time.perf_counter() - c_t0) * 1000.0, 3)
                )
                result.schema_repair_attempts += c_repairs
                trial_p_tok += c_p_tok
                trial_o_tok += c_o_tok
                trial_t_tok += c_t_tok
                result.prompt_tokens_total += c_p_tok
                result.output_tokens_total += c_o_tok
                result.thinking_tokens_total += c_t_tok
            except Exception as exc:
                result.clarifier_latencies_ms.append(
                    round((time.perf_counter() - c_t0) * 1000.0, 3)
                )
                result.e2e_total_latencies_ms.append(
                    round((time.perf_counter() - e2e_t0) * 1000.0, 3)
                )
                result.failed_runs += 1
                result.clarifier_error_categories.append(classify_eval_error(exc))
                trial_pass_at_1_flags.append(False)
                trial_judge_statuses.append("SKIPPED_NO_PROPOSAL")
                if trial == 0:
                    case_passed = False
                    detail = getattr(exc, "message", "") or str(exc)
                    case_error = f"CLARIFIER:{type(exc).__name__}:{detail[:200]}"
                continue

            planner_provider = (
                milestone_planner_provider_factory(idx, scenario)
                if milestone_planner_provider_factory is not None
                else (LiteLLMAdapter() if use_live else _E2EStubLLMAdapter())
            )
            mp_t0 = time.perf_counter()
            result.schema_check_calls += 1
            try:
                (
                    generated_milestones,
                    mp_p_tok,
                    mp_o_tok,
                    mp_t_tok,
                    mp_repairs,
                ) = await _run_e2e_stage2_milestone_planner(
                    scenario=scenario,
                    goal=clarified_goal,
                    provider=planner_provider,
                    planner_tpl=effective_planner_tpl,
                    user_id=eval_user_id,
                    apply_milestone_effort_allocator=apply_milestone_effort_allocator,
                )
                result.milestone_planner_latencies_ms.append(
                    round((time.perf_counter() - mp_t0) * 1000.0, 3)
                )
                result.schema_repair_attempts += mp_repairs
                trial_p_tok += mp_p_tok
                trial_o_tok += mp_o_tok
                trial_t_tok += mp_t_tok
                result.prompt_tokens_total += mp_p_tok
                result.output_tokens_total += mp_o_tok
                result.thinking_tokens_total += mp_t_tok
                trial_milestones = generated_milestones
                result.generated_milestones_count = len(generated_milestones)
                if trial == 0:
                    audited_milestones_source = "generated_milestones"
                    if generated_milestones:
                        case_scope_summary = generated_milestones[0].get("scope_summary")
                        case_deferred_scope = list(
                            generated_milestones[0].get("deferred_scope") or []
                        )
                        result.simulated_scope_approval_used = any(
                            bool(m.get("simulated_scope_approval_used"))
                            for m in generated_milestones
                        )
                (
                    trial_milestone_entities,
                    trial_valid_milestone_ids,
                    trial_milestone_json,
                    trial_user_prompt,
                ) = _build_decomposer_inputs(
                    scenario,
                    trial_milestones,
                    effective_parallel=effective_parallel,
                    clarification_summary=clarification_summary,
                    include_budget_context=include_budget_context,
                )
            except Exception as exc:
                result.milestone_planner_latencies_ms.append(
                    round((time.perf_counter() - mp_t0) * 1000.0, 3)
                )
                result.e2e_total_latencies_ms.append(
                    round((time.perf_counter() - e2e_t0) * 1000.0, 3)
                )
                result.failed_runs += 1
                result.milestone_planner_error_categories.append(classify_eval_error(exc))
                trial_pass_at_1_flags.append(False)
                trial_judge_statuses.append("SKIPPED_NO_PROPOSAL")
                if trial == 0:
                    case_passed = False
                    gen_ms = getattr(exc, "generated_milestones", None)
                    if isinstance(gen_ms, list) and gen_ms:
                        milestones = list(gen_ms)
                        result.generated_milestones_count = len(gen_ms)
                        audited_milestones_source = "generated_milestones_on_stage2_failure"
                        case_scope_summary = getattr(exc, "scope_summary", None)
                        case_deferred_scope = list(getattr(exc, "deferred_scope", []) or [])
                        result.simulated_scope_approval_used = bool(
                            getattr(exc, "simulated_scope_approval_used", False)
                        )
                    else:
                        milestones = []
                        result.generated_milestones_count = 0
                        audited_milestones_source = "none"
                    trial_p_tok += int(getattr(exc, "prompt_tokens", 0) or 0)
                    trial_o_tok += int(getattr(exc, "output_tokens", 0) or 0)
                    trial_t_tok += int(getattr(exc, "thinking_tokens", 0) or 0)
                    case_p_tok = trial_p_tok
                    case_o_tok = trial_o_tok
                    case_t_tok = trial_t_tok
                    detail = getattr(exc, "message", "") or str(exc)
                    v_list = getattr(exc, "violations", None)
                    if isinstance(v_list, list):
                        case_stage2_violations = [dict(v) for v in v_list if isinstance(v, dict)]
                    v_codes = (
                        ",".join(str(v.get("rule_code", "")) for v in v_list if isinstance(v, dict))
                        if isinstance(v_list, list) and v_list
                        else ""
                    )
                    suffix = f"[{v_codes}]" if v_codes else ""
                    case_error = f"MILESTONE_PLANNER:{type(exc).__name__}{suffix}:{detail[:200]}"
                continue

        if decomposer_provider_factory is not None:
            provider = decomposer_provider_factory(idx, scenario)
        elif use_live:
            provider = LiteLLMAdapter()
        elif e2e:
            provider = _E2EStubLLMAdapter()
        else:
            provider = StubLLMAdapter()

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
        trial_judge_status = "SKIPPED_NO_PROPOSAL"

        try:
            gate_result = await orchestrator.generate_and_validate_proposal_with_retry(
                system_prompt=decomposer_tpl.system_template,
                user_prompt=trial_user_prompt,
                response_schema=TaskProposalLLMOutput.model_json_schema(),
                availability=availability,
                valid_milestone_ids=trial_valid_milestone_ids,
                start_date=date.fromisoformat(str(scenario["start_date"])),
                current_roadmap_target_date=date.fromisoformat(str(scenario["target_date"])),
                goal_title=str(scenario["goal"].get("title", "")),
                learner_level=str(scenario.get("learner_level", "")),
                milestone_summary=trial_milestone_json if effective_parallel else "",
                milestones=trial_milestone_entities if effective_parallel else (),
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
                trial_judge_status = gate_result.judge_status
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
        if e2e:
            result.e2e_total_latencies_ms.append(round((time.perf_counter() - e2e_t0) * 1000.0, 3))

        if effective_parallel:
            decomposer_step_ms = [
                max(0.0, (s.completed_at - s.started_at).total_seconds() * 1000.0)
                for s in decomposer_steps
                if s.started_at is not None and s.completed_at is not None
            ]
            result.decomposer_latencies_ms.append(
                round(sum(decomposer_step_ms), 3) if decomposer_step_ms else elapsed_ms
            )
            cj_steps = [*critic_steps, *judge_steps]
            cj_starts = [s.started_at for s in cj_steps if s.started_at is not None]
            cj_ends = [s.completed_at for s in cj_steps if s.completed_at is not None]
            if cj_starts and cj_ends:
                cj_wall_ms = max(0.0, (max(cj_ends) - min(cj_starts)).total_seconds() * 1000.0)
                result.critics_judge_latencies_ms.append(round(cj_wall_ms, 3))
        else:
            result.decomposer_latencies_ms.append(elapsed_ms)

        result.total_retries += retries_used
        result.prompt_tokens_total += p_tok
        result.output_tokens_total += o_tok
        result.thinking_tokens_total += t_tok
        result.decomposer_output_tokens += o_tok
        result.decomposer_thinking_tokens += t_tok

        trial_pass_at_1 = bool(passed and retries_used == 0)
        trial_pass_at_1_flags.append(trial_pass_at_1)
        trial_judge_statuses.append(trial_judge_status)

        if trial_pass_at_1:
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
            case_p_tok = trial_p_tok + p_tok
            case_o_tok = trial_o_tok + o_tok
            case_t_tok = trial_t_tok + t_tok
            case_error = trial_error
            dec_v = getattr(trial_exc, "violations", None)
            if isinstance(dec_v, list):
                case_decomposer_violations = [dict(v) for v in dec_v if isinstance(v, dict)]

        if e2e:
            milestones = trial_milestones
            milestone_json = trial_milestone_json

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
        j_t0 = time.perf_counter()
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
        finally:
            result.critics_judge_latencies_ms.append(
                round((time.perf_counter() - j_t0) * 1000.0, 3)
            )

    result.judge_status = case_judge_status
    result.judge_error_category = judge_error_category

    trial_pwj_flags = [
        bool(
            trial_pass_at_1_flags[t_idx]
            and (trial_judge_statuses[t_idx] if effective_parallel else case_judge_status)
            == "PASSED"
        )
        for t_idx in range(len(trial_pass_at_1_flags))
    ]
    result.pass_with_judge_verdict_count = sum(1 for flag in trial_pwj_flags if flag)
    case_pass_with_judge_verdict = trial_pwj_flags[0] if trial_pwj_flags else False

    # Weekly Review evaluation (real LiteLLMAdapter in live mode + quantitative faithfulness)
    case_weekly_fallback = False
    case_weekly_faithfulness = 0.0
    weekly_error_category: str | None = None
    weekly_p_tok = 0
    weekly_o_tok = 0
    weekly_t_tok = 0
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
        w_t0 = time.perf_counter()
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
            if weekly_workflow_repo.steps:
                w_out = weekly_workflow_repo.steps[-1].output_payload
                weekly_p_tok = int(w_out.get("prompt_tokens", 0) or 0)
                weekly_t_tok = int(w_out.get("thinking_tokens", 0) or 0)
                weekly_o_tok = max(
                    int(w_out.get("output_tokens", w_out.get("completion_tokens", 0)) or 0),
                    weekly_t_tok,
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
        finally:
            result.weekly_latencies_ms.append(round((time.perf_counter() - w_t0) * 1000.0, 3))
            result.prompt_tokens_total += weekly_p_tok
            result.output_tokens_total += weekly_o_tok
            result.thinking_tokens_total += weekly_t_tok
            case_p_tok += weekly_p_tok
            case_o_tok += weekly_o_tok
            case_t_tok += weekly_t_tok

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

    case_structural_audit = _compute_case_structural_audit(
        milestones=milestones,
        proposal=last_valid_proposal,
        availability=availability,
        start_date=date.fromisoformat(str(scenario["start_date"])),
        target_date=date.fromisoformat(str(scenario["target_date"])),
        scenario=scenario,
        case_passed=case_passed,
        case_error=case_error,
        stage2_violations=case_stage2_violations,
        decomposer_violations=case_decomposer_violations,
        scope_summary=case_scope_summary,
        deferred_scope=case_deferred_scope,
        judge_status=case_judge_status,
        pedagogical_score=case_pedagogical_score,
        injection_status=injection_status,
        audited_milestones_source=audited_milestones_source,
        require_proposal=True,
        latency_ms=_percentile(sorted(result.latencies_ms), 50.0),
        prompt_tokens=case_p_tok,
        output_tokens=case_o_tok,
        thinking_tokens=case_t_tok,
    )
    result.structural_audit = case_structural_audit

    outcome: dict[str, Any] = {
        "case_id": str(scenario["scenario_id"]),
        "domain": str(scenario["domain"]),
        "learner_level": str(scenario["learner_level"]),
        "deadline_regime": str(scenario["deadline_regime"]),
        "planning_mode": str(scenario["planning_mode"]),
        "is_injection_case": result.is_injection_case,
        "passed_tier1": case_passed,
        "pass_with_judge_verdict": case_pass_with_judge_verdict,
        "pass_with_judge_verdict_trials": result.pass_with_judge_verdict_count,
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
        "decomposer_latency_ms": _percentile(sorted(result.decomposer_latencies_ms), 50.0),
        "critics_judge_parallel_latency_ms": _percentile(
            sorted(result.critics_judge_latencies_ms), 50.0
        ),
        "weekly_latency_ms": _percentile(sorted(result.weekly_latencies_ms), 50.0),
        "weekly_prompt_tokens": weekly_p_tok,
        "weekly_output_tokens": weekly_o_tok,
        "weekly_thinking_tokens": weekly_t_tok,
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
        "structural_audit": case_structural_audit,
    }
    if e2e:
        outcome["clarifier_latency_ms"] = _percentile(sorted(result.clarifier_latencies_ms), 50.0)
        outcome["milestone_planner_latency_ms"] = _percentile(
            sorted(result.milestone_planner_latencies_ms), 50.0
        )
        outcome["e2e_total_latency_ms"] = _percentile(sorted(result.e2e_total_latencies_ms), 50.0)
        outcome["generated_milestones_count"] = result.generated_milestones_count
        outcome["clarifier_error_categories"] = list(result.clarifier_error_categories)
        outcome["milestone_planner_error_categories"] = list(
            result.milestone_planner_error_categories
        )
    if case_error is not None:
        outcome["error"] = case_error
    result.outcome = outcome
    return result


def validate_eval_report_totals(report: dict[str, Any]) -> None:
    """Self-check that all summary counts and error_breakdown totals match per-case details 100%."""
    per_case_outcomes = report["per_case_outcomes"]
    dataset_size = int(report["dataset_size"])
    trials_per_goal = int(report["trials_per_goal"])
    is_e2e = bool(report.get("e2e", False))

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
    assert 0 <= report["pass_with_judge_verdict_count"] <= report["passed_runs"], (
        "pass_with_judge_verdict_count must be between 0 and passed_runs"
    )
    assert report["pass_with_judge_verdict"] == round(
        report["pass_with_judge_verdict_count"] / max(1, report["total_runs"]), 4
    )
    assert (
        sum(o["pass_with_judge_verdict_trials"] for o in per_case_outcomes)
        == report["pass_with_judge_verdict_count"]
    ), "sum(pass_with_judge_verdict_trials) must equal pass_with_judge_verdict_count"
    if trials_per_goal == 1:
        assert (
            sum(1 for o in per_case_outcomes if o["pass_with_judge_verdict"])
            == report["pass_with_judge_verdict_count"]
        )
        for o in per_case_outcomes:
            assert isinstance(o["pass_with_judge_verdict"], bool)
            if o["pass_with_judge_verdict"]:
                assert o["passed_tier1"] and o["attempts"] == 1 and o["judge_status"] == "PASSED"
            if o["judge_status"] != "PASSED":
                assert not o["pass_with_judge_verdict"]

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
    expected_eb_keys = (
        {"clarifier", "milestone_planner", "decomposer", "judge", "weekly", "total"}
        if is_e2e
        else {"decomposer", "judge", "weekly", "total"}
    )
    assert set(eb.keys()) == expected_eb_keys
    for step in expected_eb_keys:
        assert set(eb[step].keys()) == set(ERROR_TAXONOMY_CATEGORIES)
        assert all(isinstance(v, int) and v >= 0 for v in eb[step].values())

    decomposer_failed_sum = sum(o["decomposer_failed_trials"] for o in per_case_outcomes)
    assert sum(eb["decomposer"].values()) == decomposer_failed_sum, (
        "sum(error_breakdown.decomposer) must equal sum(decomposer_failed_trials)"
    )
    if is_e2e:
        assert (
            sum(eb["clarifier"].values())
            + sum(eb["milestone_planner"].values())
            + decomposer_failed_sum
            == report["failed_runs"]
        ), "e2e stage failure counts must equal failed_runs"
    else:
        assert decomposer_failed_sum == report["failed_runs"], (
            "sum(decomposer_failed_trials) must match failed_runs"
        )
    assert sum(eb["judge"].values()) == report["judge_review_pending_count"], (
        "sum(error_breakdown.judge) must equal judge_review_pending_count"
    )
    assert sum(eb["weekly"].values()) == report["weekly_fallbacks"], (
        "sum(error_breakdown.weekly) must equal weekly_fallbacks"
    )

    clarifier_counter = Counter(
        cat for o in per_case_outcomes for cat in o.get("clarifier_error_categories", [])
    )
    milestone_planner_counter = Counter(
        cat for o in per_case_outcomes for cat in o.get("milestone_planner_error_categories", [])
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
        if is_e2e:
            assert eb["clarifier"][category] == clarifier_counter[category]
            assert eb["milestone_planner"][category] == milestone_planner_counter[category]
        assert eb["decomposer"][category] == decomposer_counter[category]
        assert eb["judge"][category] == judge_counter[category]
        assert eb["weekly"][category] == weekly_counter[category]
        expected_total_cat = (
            eb["decomposer"][category] + eb["judge"][category] + eb["weekly"][category]
        )
        if is_e2e:
            expected_total_cat += eb["clarifier"][category] + eb["milestone_planner"][category]
        assert eb["total"][category] == expected_total_cat

    assert report["post_repair_schema_mismatch_count"] >= eb["total"]["SCHEMA_MISMATCH"]
    assert 0 <= report["post_repair_schema_mismatch_count"] <= report["schema_check_calls"]
    expected_mismatch_rate = round(
        report["post_repair_schema_mismatch_count"] / max(1, report["schema_check_calls"]), 4
    )
    assert report["post_repair_schema_mismatch_rate"] == expected_mismatch_rate

    stage_stats = report["stage_latency_stats"]
    expected_stage_keys = (
        {
            "clarifier",
            "milestone_planner",
            "decomposer",
            "critics_judge_parallel",
            "weekly",
            "e2e_total",
        }
        if is_e2e
        else {"decomposer", "critics_judge_parallel", "weekly"}
    )
    assert set(stage_stats.keys()) == expected_stage_keys
    for stage_key, stats in stage_stats.items():
        assert set(stats.keys()) == {"count", "min_ms", "p50_ms", "p95_ms", "max_ms"}
        assert isinstance(stats["count"], int) and stats["count"] >= 0
        if stats["count"] > 0:
            assert (
                0.0 <= stats["min_ms"] <= stats["p50_ms"] <= stats["p95_ms"] <= stats["max_ms"]
            ), f"Invalid latency ordering for {stage_key}: {stats}"

    rates = report["error_category_rates"]
    assert set(rates.keys()) == {"by_stage_rate", "share_of_total_errors"}
    assert set(rates["by_stage_rate"].keys()) == expected_eb_keys
    for step in expected_eb_keys:
        assert set(rates["by_stage_rate"][step].keys()) == set(ERROR_TAXONOMY_CATEGORIES)
        assert all(0.0 <= v <= 1.0 for v in rates["by_stage_rate"][step].values())
    assert set(rates["share_of_total_errors"].keys()) == set(ERROR_TAXONOMY_CATEGORIES)


async def run_planning_eval_suite(
    dataset_path: Path = DEFAULT_18_GOALS_DATASET_PATH,
    *,
    trials_per_goal: int = 3,
    output_path: Path | None = None,
    live: bool | None = None,
    e2e: bool = False,
    concurrency: int = 1,
    decomposer_thinking_level: str | None = None,
    judge_thinking_level: str | None = None,
    judge_timeout_seconds: float | None = None,
    include_weekly: bool = True,
    include_budget_context: bool = True,
    parallel_critics_and_judge: bool | None = None,
    apply_milestone_effort_allocator: bool = False,
    clarifier_provider_factory: ProviderFactory | None = None,
    milestone_planner_provider_factory: ProviderFactory | None = None,
    decomposer_provider_factory: ProviderFactory | None = None,
    judge_provider_factory: ProviderFactory | None = None,
    weekly_provider_factory: ProviderFactory | None = None,
) -> dict[str, Any]:
    """Run the AI planning evaluation benchmark and return a PII-free metrics artifact."""
    scenarios = load_eval_dataset(dataset_path)
    use_live = bool(os.getenv("RUN_LIVE_AI_EVALS") == "1") if live is None else live
    effective_trials = max(1, trials_per_goal)
    effective_concurrency = max(1, int(concurrency))

    registry = build_planning_prompt_registry()
    decomposer_tpl = registry.latest(TASK_DECOMPOSER_SKILL.skill_id)
    clarifier_tpl = registry.latest(GOAL_CLARIFIER_SKILL.skill_id) if e2e else None
    milestone_planner_tpl = registry.latest(MILESTONE_PLANNER_SKILL.skill_id) if e2e else None

    if effective_concurrency == 1:
        scenario_results = [
            await _evaluate_scenario(
                idx,
                scenario,
                use_live=use_live,
                e2e=e2e,
                effective_trials=effective_trials,
                decomposer_tpl=decomposer_tpl,
                clarifier_tpl=clarifier_tpl,
                milestone_planner_tpl=milestone_planner_tpl,
                decomposer_thinking_level=decomposer_thinking_level,
                judge_thinking_level=judge_thinking_level,
                judge_timeout_seconds=judge_timeout_seconds,
                include_weekly=include_weekly,
                include_budget_context=include_budget_context,
                parallel_critics_and_judge=parallel_critics_and_judge,
                apply_milestone_effort_allocator=apply_milestone_effort_allocator,
                clarifier_provider_factory=clarifier_provider_factory,
                milestone_planner_provider_factory=milestone_planner_provider_factory,
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
                    e2e=e2e,
                    effective_trials=effective_trials,
                    decomposer_tpl=decomposer_tpl,
                    clarifier_tpl=clarifier_tpl,
                    milestone_planner_tpl=milestone_planner_tpl,
                    decomposer_thinking_level=decomposer_thinking_level,
                    judge_thinking_level=judge_thinking_level,
                    judge_timeout_seconds=judge_timeout_seconds,
                    include_weekly=include_weekly,
                    include_budget_context=include_budget_context,
                    parallel_critics_and_judge=parallel_critics_and_judge,
                    apply_milestone_effort_allocator=apply_milestone_effort_allocator,
                    clarifier_provider_factory=clarifier_provider_factory,
                    milestone_planner_provider_factory=milestone_planner_provider_factory,
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
    clarifier_latencies_ms: list[float] = []
    milestone_planner_latencies_ms: list[float] = []
    decomposer_latencies_ms: list[float] = []
    critics_judge_latencies_ms: list[float] = []
    weekly_latencies_ms: list[float] = []
    e2e_total_latencies_ms: list[float] = []
    per_case_outcomes: list[dict[str, Any]] = []
    weekly_llm_faithfulness_scores: list[float] = []
    weekly_fallback_faithfulness_scores: list[float] = []

    total_runs = 0
    pass_at_1_count = 0
    pass_with_judge_verdict_count = 0
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

    clarifier_errors = _empty_error_bucket()
    milestone_planner_errors = _empty_error_bucket()
    decomposer_errors = _empty_error_bucket()
    judge_errors = _empty_error_bucket()
    weekly_errors = _empty_error_bucket()

    for item in scenario_results:
        latencies_ms.extend(item.latencies_ms)
        clarifier_latencies_ms.extend(item.clarifier_latencies_ms)
        milestone_planner_latencies_ms.extend(item.milestone_planner_latencies_ms)
        decomposer_latencies_ms.extend(item.decomposer_latencies_ms)
        critics_judge_latencies_ms.extend(item.critics_judge_latencies_ms)
        weekly_latencies_ms.extend(item.weekly_latencies_ms)
        e2e_total_latencies_ms.extend(item.e2e_total_latencies_ms)
        per_case_outcomes.append(item.outcome)
        total_runs += item.total_runs
        pass_at_1_count += item.pass_at_1_count
        pass_with_judge_verdict_count += item.pass_with_judge_verdict_count
        passed_runs += item.passed_runs
        failed_runs += item.failed_runs
        total_retries += item.total_retries
        prompt_tokens_total += item.prompt_tokens_total
        output_tokens_total += item.output_tokens_total
        thinking_tokens_total += item.thinking_tokens_total

        for cat in item.clarifier_error_categories:
            clarifier_errors[cat] += 1
        for cat in item.milestone_planner_error_categories:
            milestone_planner_errors[cat] += 1
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
        cat: (
            (clarifier_errors[cat] + milestone_planner_errors[cat] if e2e else 0)
            + decomposer_errors[cat]
            + judge_errors[cat]
            + weekly_errors[cat]
        )
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
    clarifier_checks = total_runs if e2e else 0
    milestone_planner_checks = max(0, total_runs - sum(clarifier_errors.values())) if e2e else 0
    decomposer_checks = (
        max(0, milestone_planner_checks - sum(milestone_planner_errors.values()))
        if e2e
        else total_runs
    )
    total_stage_checks = (
        clarifier_checks
        + milestone_planner_checks
        + decomposer_checks
        + judge_attempted_cases
        + weekly_checks
    )
    total_error_events = sum(total_errors.values())

    stage_latency_stats: dict[str, dict[str, float | int]] = (
        {
            "clarifier": _summarize_latency_stats(clarifier_latencies_ms),
            "milestone_planner": _summarize_latency_stats(milestone_planner_latencies_ms),
            "decomposer": _summarize_latency_stats(decomposer_latencies_ms),
            "critics_judge_parallel": _summarize_latency_stats(critics_judge_latencies_ms),
            "weekly": _summarize_latency_stats(weekly_latencies_ms),
            "e2e_total": _summarize_latency_stats(e2e_total_latencies_ms),
        }
        if e2e
        else {
            "decomposer": _summarize_latency_stats(decomposer_latencies_ms),
            "critics_judge_parallel": _summarize_latency_stats(critics_judge_latencies_ms),
            "weekly": _summarize_latency_stats(weekly_latencies_ms),
        }
    )

    error_breakdown: dict[str, dict[str, int]] = (
        {
            "clarifier": clarifier_errors,
            "milestone_planner": milestone_planner_errors,
            "decomposer": decomposer_errors,
            "judge": judge_errors,
            "weekly": weekly_errors,
            "total": total_errors,
        }
        if e2e
        else {
            "decomposer": decomposer_errors,
            "judge": judge_errors,
            "weekly": weekly_errors,
            "total": total_errors,
        }
    )

    by_stage_rate: dict[str, dict[str, float]] = {}
    if e2e:
        by_stage_rate["clarifier"] = {
            cat: (
                round(clarifier_errors[cat] / clarifier_checks, 4) if clarifier_checks > 0 else 0.0
            )
            for cat in ERROR_TAXONOMY_CATEGORIES
        }
        by_stage_rate["milestone_planner"] = {
            cat: (
                round(milestone_planner_errors[cat] / milestone_planner_checks, 4)
                if milestone_planner_checks > 0
                else 0.0
            )
            for cat in ERROR_TAXONOMY_CATEGORIES
        }
    by_stage_rate["decomposer"] = {
        cat: (
            round(decomposer_errors[cat] / decomposer_checks, 4) if decomposer_checks > 0 else 0.0
        )
        for cat in ERROR_TAXONOMY_CATEGORIES
    }
    by_stage_rate["judge"] = {
        cat: (
            round(judge_errors[cat] / judge_attempted_cases, 4)
            if judge_attempted_cases > 0
            else 0.0
        )
        for cat in ERROR_TAXONOMY_CATEGORIES
    }
    by_stage_rate["weekly"] = {
        cat: (round(weekly_errors[cat] / weekly_checks, 4) if weekly_checks > 0 else 0.0)
        for cat in ERROR_TAXONOMY_CATEGORIES
    }
    by_stage_rate["total"] = {
        cat: round(total_errors[cat] / max(1, total_stage_checks), 4)
        for cat in ERROR_TAXONOMY_CATEGORIES
    }

    struct_rows = [item.structural_audit for item in scenario_results if item.structural_audit]
    prop_struct_rows = [r for r in struct_rows if r.get("has_proposal")]
    util_vals = [
        float(r["capacity_utilization"])
        for r in struct_rows
        if r.get("capacity_utilization") is not None
    ]
    eq_vals = [
        float(r["effort_equal_ratio"])
        for r in struct_rows
        if r.get("effort_equal_ratio") is not None
    ]
    gap_vals = [
        float(r["milestone_vs_tasks_gap"])
        for r in prop_struct_rows
        if r.get("milestone_vs_tasks_gap") is not None
    ]
    lin_vals = [
        float(r["linear_dependency_ratio"])
        for r in prop_struct_rows
        if r.get("linear_dependency_ratio") is not None
    ]
    consec_vals = [
        int(r["max_consecutive_study_days"])
        for r in prop_struct_rows
        if r.get("max_consecutive_study_days") is not None
    ]
    idle_vals = [
        int(r["days_idle_before_deadline"])
        for r in prop_struct_rows
        if r.get("days_idle_before_deadline") is not None
    ]
    structural_audit_summary: dict[str, Any] = {
        "evaluated_cases": len(struct_rows),
        "cases_with_proposal": len(prop_struct_rows),
        "capacity_utilization_avg": round(sum(util_vals) / len(util_vals), 4)
        if util_vals
        else None,
        "capacity_utilization_max": round(max(util_vals), 4) if util_vals else None,
        "effort_equal_ratio_avg": round(sum(eq_vals) / len(eq_vals), 4) if eq_vals else None,
        "all_efforts_equal_cases": sum(1 for r in struct_rows if r.get("all_efforts_equal")),
        "milestone_vs_tasks_gap_avg": round(sum(gap_vals) / len(gap_vals), 4) if gap_vals else None,
        "linear_dependency_ratio_avg": round(sum(lin_vals) / len(lin_vals), 4)
        if lin_vals
        else None,
        "max_consecutive_study_days_max": max(consec_vals) if consec_vals else None,
        "days_idle_before_deadline_avg": round(sum(idle_vals) / len(idle_vals), 2)
        if idle_vals
        else None,
        "tasks_split_across_days_total": sum(
            int(r.get("tasks_split_across_days_count", 0)) for r in prop_struct_rows
        ),
        "sensitive_tasks_split_across_days_total": sum(
            int(r.get("sensitive_tasks_split_across_days_count", 0)) for r in prop_struct_rows
        ),
        "short_project_under_90_total": sum(
            int(r.get("short_project_under_90_count", 0)) for r in prop_struct_rows
        ),
    }

    report: dict[str, Any] = {
        "schema_version": "1.0",
        "mode": "live" if use_live else "mock",
        "e2e": bool(e2e),
        "dataset_size": len(scenarios),
        "trials_per_goal": effective_trials,
        "concurrency": effective_concurrency,
        "total_runs": total_runs,
        "passed_runs": passed_runs,
        "failed_runs": failed_runs,
        "pass_at_1_count": pass_at_1_count,
        "pass_at_1": round(pass_at_1_count / max(1, total_runs), 4),
        "pass_with_judge_verdict_count": pass_with_judge_verdict_count,
        "pass_with_judge_verdict": round(pass_with_judge_verdict_count / max(1, total_runs), 4),
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
        "stage_latency_stats": stage_latency_stats,
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
        "error_breakdown": error_breakdown,
        "error_category_rates": {
            "by_stage_rate": by_stage_rate,
            "share_of_total_errors": {
                cat: (
                    round(total_errors[cat] / total_error_events, 4)
                    if total_error_events > 0
                    else 0.0
                )
                for cat in ERROR_TAXONOMY_CATEGORIES
            },
        },
        "structural_audit_summary": structural_audit_summary,
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
        description="Run FocusFlow AI planning evaluation suite.",
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
        help="Run Dual Critics and Tier 3 Judge in parallel inside orchestrator (default: enabled in live/e2e mode).",
    )
    parser.add_argument(
        "--e2e",
        action="store_true",
        default=False,
        help="Execute full 3-stage E2E pipeline (Clarifier -> Milestone Planner -> Decomposer + Critics + Judge).",
    )
    parser.add_argument(
        "--no-budget-context",
        dest="include_budget_context",
        action="store_false",
        default=True,
        help="Omit precomputed_schedule_budget from Task Decomposer prompts (for A/B evaluation).",
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
            e2e=args.e2e,
            concurrency=args.concurrency,
            include_budget_context=args.include_budget_context,
            parallel_critics_and_judge=args.parallel_critics_judge,
        )
    )
    print(json.dumps({k: v for k, v in res.items() if k != "per_case_outcomes"}, indent=2))
    print(
        f"\n[Summary] mode={res['mode']} e2e={res['e2e']} "
        f"pass_at_1={res['pass_at_1']} ({res['pass_at_1_count']}/{res['total_runs']}) | "
        f"pass_with_judge_verdict={res['pass_with_judge_verdict']} "
        f"({res['pass_with_judge_verdict_count']}/{res['total_runs']})"
    )
    for stage_name, stats in res.get("stage_latency_stats", {}).items():
        print(
            f"  stage={stage_name}: count={stats['count']} "
            f"p50={stats['p50_ms']}ms p95={stats['p95_ms']}ms"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
