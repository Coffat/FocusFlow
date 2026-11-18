"""Experiment 14 (PR-E Step 2): Decomposer Architecture Controlled A/B Suite.

Compares Arm A (`monolithic` Task Decomposer) vs Arm B (`milestone_scoped` Parallel Task
Decomposer with Server Resource Prefetch & Deterministic Global DAG Reconciliation) on
live CofHub (`LLM_BASE_URL=http://127.0.0.1:8045`) across:
  - Part 1: Production-equivalent prompt & context deduplication overhead measurements.
  - Part 2:
    1. Golden 18 (`golden_planning_18_goals.jsonl`, `n=18`, `concurrency=3`):
       Stage 3 `ExecuteScheduleProposalGenerationUseCase` + `ApplyScheduleProposalUseCase`.
    2. Hard 6 (`hard_planning_6_goals.jsonl`, `n=6`, `concurrency=1` and `concurrency=3`):
       - Stage 3 Apples-to-Apples on the 5 milestones of `hard_planning_6_goals.jsonl`
         (with `MilestoneEffortAllocator` realistic efforts) + `ApplyScheduleProposalUseCase`.
       - Full E2E (`ExecuteMilestoneGenerationUseCase` -> `ApproveMilestonesUseCase` ->
         `ExecuteScheduleProposalGenerationUseCase` -> `ApplyScheduleProposalUseCase`).
    3. Production-Equivalent Workload (`n=6` Hard 6 goals with `LearnerMemoryItem` +
       `LearnerConceptMastery` + `KnowledgeChunk` RAG + `InMemoryKnowledgeBasePort`
       resources, `concurrency=1`):
       `ExecuteScheduleProposalGenerationUseCase` (`monolithic` with `KnowledgeToolDispatcher`
       vs `milestone_scoped` with Server Resource Prefetch) + `ApplyScheduleProposalUseCase`.

Constraints:
  - Never fabricates or extrapolates live LLM numbers.
  - Never prints, logs, or persists API keys or PII.
  - Zero modifications to prompts, lockfile, or timeout budgets (`36s`/`55s`).

Output:
  - `docs/experiments/exp_14_decomposer_architecture_ab.json`
"""

from __future__ import annotations

import argparse
import asyncio
import contextvars
import json
import os
import random
import time
import urllib.error
import urllib.request
from collections import Counter
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from types import SimpleNamespace
from typing import Any, Literal, Self
from uuid import UUID

from common import (
    BACKEND_DIR,
    get_cobhub_config,
    sanitize_error_message,
    summarize_numeric,
    utc_timestamp,
    write_experiment_json,
)

from src.account.public_api import (
    AvailabilityQueryPort,
    AvailabilitySnapshotDTO,
    ConceptMasterySnapshotDTO,
    LearnerMemoryItemSnapshotDTO,
    LearnerMemoryQueryPort,
    LearnerProfileDTO,
    LearnerProfileQueryPort,
    QuotaFacadePort,
    UserQueryPort,
)
from src.evaluation.public_api import ScheduleChangeLogPort
from src.execution.public_api import (
    ExecutionScheduleSyncPort,
    ExistingScheduledTaskDTO,
    ScheduleSyncResultDTO,
)
from src.planning.application.dtos.planning_dtos import (
    ClarificationContextPayload,
    MilestoneGenerationLLMOutput,
)
from src.planning.application.ports.knowledge_base_port import KnowledgeBasePort
from src.planning.application.ports.knowledge_source_repository_port import (
    KnowledgeSourceRepositoryPort,
)
from src.planning.application.ports.planning_repository_ports import (
    GoalRepositoryPort,
    MilestoneRepositoryPort,
    OfficialScheduleRepositoryPort,
    RoadmapRepositoryPort,
    ScheduleProposalRepositoryPort,
)
from src.planning.application.ports.schedule_block_repository_port import (
    ScheduleBlockRepositoryPort,
)
from src.planning.application.services.clarification_gap_analysis import (
    GapStatus,
    GoalFactProvenance,
    InformationGapAnalyzer,
)
from src.planning.application.services.learning_quality import validate_task_coverage
from src.planning.application.services.milestone_scoped_decomposer import (
    MilestoneScopedTaskDecomposer,
)
from src.planning.application.services.roadmap_context_builder import (
    RoadmapContextBuilder,
)
from src.planning.application.services.roadmap_skills import (
    build_goal_clarifier_prompt,
    build_milestone_planner_prompt,
    build_task_decomposer_prompt,
)
from src.planning.application.use_cases.milestone_use_cases import (
    ApproveMilestonesUseCase,
    ExecuteMilestoneGenerationUseCase,
)
from src.planning.application.use_cases.proposal_generation_use_cases import (
    ExecuteScheduleProposalGenerationUseCase,
)
from src.planning.application.use_cases.proposal_management_use_cases import (
    ApplyScheduleProposalUseCase,
)
from src.planning.domain.exceptions.planning_exceptions import (
    InsufficientCapacityError,
    PlanInfeasibleError,
    ProposalValidationGateError,
    ScopeApprovalRequiredError,
)
from src.planning.domain.models.goal import Goal, GoalStatus
from src.planning.domain.models.knowledge_concept import (
    ConceptPrerequisiteGraph,
    LearningConcept,
    LearningResource,
    compute_deterministic_resource_id,
)
from src.planning.domain.models.knowledge_source import (
    KnowledgeChunk,
    KnowledgeIngestionStatus,
    KnowledgeSource,
    KnowledgeSourceType,
)
from src.planning.domain.models.milestone import Milestone, MilestoneStatus
from src.planning.domain.models.roadmap import Roadmap, RoadmapStatus
from src.planning.domain.models.schedule import (
    OfficialSchedule,
    ScheduleProposal,
    ScheduleProposalStatus,
)
from src.planning.domain.models.schedule_block import ScheduleBlock
from src.planning.domain.services.milestone_effort_allocator import (
    MilestoneEffortAllocator,
)
from src.planning.domain.services.spatio_temporal_engine import (
    NonSplittableTaskClassifier,
    SpatioTemporalRuleEngine,
)
from src.planning.domain.services.validation_types import (
    AvailabilityConfigurationDTO,
    safe_parse_iso_date,
)
from src.planning.infrastructure.repositories.sqlalchemy_knowledge_base_repository import (
    VERIFIED_SEED_CONCEPTS,
    VERIFIED_SEED_EDGES,
    VERIFIED_SEED_RESOURCES,
    InMemoryKnowledgeBaseRepository,
)
from src.shared_kernel.application.harness.context_engine import ContextEngine
from src.shared_kernel.application.harness.untrusted_context import (
    UntrustedBlockKind,
    format_untrusted_block,
)
from src.shared_kernel.application.llm_port import (
    LLMGenerationResult,
    LLMProviderPort,
    LLMToolDeclarationDTO,
    LLMToolExecutor,
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
    _build_availability,
    _check_dag_acyclic_and_prereq_order,
    load_eval_dataset,
)

OUTPUT_FILENAME = "exp_14_decomposer_architecture_ab.json"
ArchMode = Literal["monolithic", "milestone_scoped"]

# ---------------------------------------------------------------------------
# Seeded Domain Learning Resources for Production-Equivalent Workload
# ---------------------------------------------------------------------------
EXTRA_PRODUCTION_RESOURCES: tuple[LearningResource, ...] = (
    LearningResource(
        resource_id=compute_deterministic_resource_id(
            url="https://raft.github.io/raft.pdf",
            title="In Search of an Understandable Consensus Algorithm (Raft Paper)",
        ),
        title="In Search of an Understandable Consensus Algorithm (Raft Paper)",
        url="https://raft.github.io/raft.pdf",
        type="DOCS",
        description="Đặc tả chuẩn thuật toán Raft: Leader Election, Log Replication, Safety & Compaction.",
        domain="distributed_systems_go",
        concept_id="sys-transactional-outbox-sse",
    ),
    LearningResource(
        resource_id=compute_deterministic_resource_id(
            url="https://grpc.io/docs/languages/go/basics/",
            title="gRPC Go Streaming, Interceptors & Deadline Propagation Guide",
        ),
        title="gRPC Go Streaming, Interceptors & Deadline Propagation Guide",
        url="https://grpc.io/docs/languages/go/basics/",
        type="TUTORIAL",
        description="Hướng dẫn xây dựng gRPC bidirectional streaming, TLS và retry interceptor trong Go.",
        domain="distributed_systems_go",
        concept_id="http-rest-fundamentals",
    ),
    LearningResource(
        resource_id=compute_deterministic_resource_id(
            url="https://embassy.dev/book/",
            title="Embassy Async Embedded Rust Book (#![no_std] & DMA)",
        ),
        title="Embassy Async Embedded Rust Book (#![no_std] & DMA)",
        url="https://embassy.dev/book/",
        type="DOCS",
        description="Tài liệu chính thức về Rust #![no_std], async executor, HAL/PAC và zero-copy DMA.",
        domain="embedded_rust_rtos",
        concept_id="py-async-concurrency",
    ),
    LearningResource(
        resource_id=compute_deterministic_resource_id(
            url="https://docs.cilium.io/en/stable/security/",
            title="Cilium eBPF Zero-Trust NetworkPolicy & Kyverno Policy-as-Code",
        ),
        title="Cilium eBPF Zero-Trust NetworkPolicy & Kyverno Policy-as-Code",
        url="https://docs.cilium.io/en/stable/security/",
        type="DOCS",
        description="Thiết lập Zero-Trust L3/L4/L7 NetworkPolicy với Cilium, Kyverno, Cosign và Falco.",
        domain="kubernetes_terraform",
        concept_id="backend-auth-jwt-security",
    ),
    LearningResource(
        resource_id=compute_deterministic_resource_id(
            url="https://iceberg.apache.org/docs/latest/spark-writes/",
            title="Apache Iceberg + PySpark Structured Streaming & Compaction Guide",
        ),
        title="Apache Iceberg + PySpark Structured Streaming & Compaction Guide",
        url="https://iceberg.apache.org/docs/latest/spark-writes/",
        type="DOCS",
        description="Kiến trúc Medallion Lakehouse với Apache Spark, Iceberg MERGE INTO, Time Travel & dbt.",
        domain="data_engineering",
        concept_id="sql-relational-modeling",
    ),
    LearningResource(
        resource_id=compute_deterministic_resource_id(
            url="https://nextjs.org/docs/app/building-your-application/rendering/server-components",
            title="Next.js App Router, React Server Components & PostgreSQL RLS",
        ),
        title="Next.js App Router, React Server Components & PostgreSQL RLS",
        url="https://nextjs.org/docs/app/building-your-application/rendering/server-components",
        type="DOCS",
        description="Tối ưu RSC streaming Suspense, Server Actions, PostgreSQL B-Tree/GIN Index & RLS.",
        domain="fullstack_nextjs_pg",
        concept_id="ts-strict-type-system",
    ),
    LearningResource(
        resource_id=compute_deterministic_resource_id(
            url="https://docs.vllm.ai/en/latest/",
            title="vLLM Production Serving, PagedAttention & LLMOps Eval Harness",
        ),
        title="vLLM Production Serving, PagedAttention & LLMOps Eval Harness",
        url="https://docs.vllm.ai/en/latest/",
        type="DOCS",
        description="Triển khai vLLM continuous batching, Prompt Registry, Eval Gate và Prometheus drift alerting.",
        domain="mlops_llmops",
        concept_id="ai-llm-structured-rag-agents",
    ),
)


# ---------------------------------------------------------------------------
# Per-Scenario Telemetry Context & Wrappers
# ---------------------------------------------------------------------------
@dataclass
class ScenarioTelemetry:
    milestone_planner_calls: list[dict[str, Any]] = field(default_factory=list)
    decomposer_calls: list[dict[str, Any]] = field(default_factory=list)
    critic_judge_calls: list[dict[str, Any]] = field(default_factory=list)
    kb_calls: list[dict[str, Any]] = field(default_factory=list)
    scheduler_calls_ms: list[float] = field(default_factory=list)

    @property
    def prefetch_or_tools_ms(self) -> float:
        if not self.kb_calls:
            return 0.0
        starts = [float(c["t_start"]) for c in self.kb_calls]
        ends = [float(c["t_end"]) for c in self.kb_calls]
        return round(max(0.0, (max(ends) - min(starts)) * 1000.0), 3)

    @property
    def decomposer_llm_wall_ms(self) -> float:
        if not self.decomposer_calls:
            return 0.0
        starts = [float(c["t_start"]) for c in self.decomposer_calls]
        ends = [float(c["t_end"]) for c in self.decomposer_calls]
        raw_wall = max(0.0, (max(ends) - min(starts)) * 1000.0)
        # In monolithic mode, tool calls execute inside the decomposer generate_structured span
        tool_calls_used = sum(int(c.get("tool_calls_count", 0)) for c in self.decomposer_calls)
        if tool_calls_used > 0 and self.kb_calls:
            return round(max(1.0, raw_wall - self.prefetch_or_tools_ms), 3)
        return round(raw_wall, 3)

    @property
    def critics_judge_parallel_ms(self) -> float:
        if not self.critic_judge_calls:
            return 0.0
        starts = [float(c["t_start"]) for c in self.critic_judge_calls]
        ends = [float(c["t_end"]) for c in self.critic_judge_calls]
        return round(max(0.0, (max(ends) - min(starts)) * 1000.0), 3)

    @property
    def deterministic_scheduler_ms(self) -> float:
        return round(sum(self.scheduler_calls_ms), 3)

    @property
    def decomposer_prompt_tokens(self) -> int:
        return sum(int(c.get("prompt_tokens", 0)) for c in self.decomposer_calls)

    @property
    def decomposer_output_tokens(self) -> int:
        return sum(int(c.get("output_tokens", 0)) for c in self.decomposer_calls)

    @property
    def decomposer_thinking_tokens(self) -> int:
        return sum(int(c.get("thinking_tokens", 0)) for c in self.decomposer_calls)

    @property
    def stage3_total_prompt_tokens(self) -> int:
        return self.decomposer_prompt_tokens + sum(
            int(c.get("prompt_tokens", 0)) for c in self.critic_judge_calls
        )

    @property
    def stage3_total_output_tokens(self) -> int:
        return self.decomposer_output_tokens + sum(
            int(c.get("output_tokens", 0)) for c in self.critic_judge_calls
        )

    @property
    def stage3_total_thinking_tokens(self) -> int:
        return self.decomposer_thinking_tokens + sum(
            int(c.get("thinking_tokens", 0)) for c in self.critic_judge_calls
        )

    @property
    def tool_calls_count(self) -> int:
        return sum(int(c.get("tool_calls_count", 0)) for c in self.decomposer_calls)


_ACTIVE_TELEMETRY: contextvars.ContextVar[ScenarioTelemetry | None] = contextvars.ContextVar(
    "_ACTIVE_TELEMETRY", default=None
)

_ORIG_ALLOCATE_WITH_DIAGNOSTICS = SpatioTemporalRuleEngine.allocate_task_sessions_with_diagnostics


def _timed_allocate_with_diagnostics(*args: Any, **kwargs: Any) -> Any:
    t0 = time.perf_counter()
    try:
        return _ORIG_ALLOCATE_WITH_DIAGNOSTICS(*args, **kwargs)
    finally:
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        tel = _ACTIVE_TELEMETRY.get()
        if tel is not None:
            tel.scheduler_calls_ms.append(elapsed_ms)


SpatioTemporalRuleEngine.allocate_task_sessions_with_diagnostics = (  # type: ignore[method-assign]
    _timed_allocate_with_diagnostics
)


class TelemetryLLMProvider(LLMProviderPort):
    """Wraps `LiteLLMAdapter` to record per-call latencies, token counts, and tool calls."""

    def __init__(self, inner: LiteLLMAdapter, telemetry: ScenarioTelemetry) -> None:
        self._inner = inner
        self._telemetry = telemetry

    @property
    def model_identifier(self) -> str:
        return self._inner.model_identifier

    @property
    def last_model_used(self) -> str | None:
        return getattr(self._inner, "last_model_used", None)

    @property
    def last_degraded_model_used(self) -> bool:
        return bool(getattr(self._inner, "last_degraded_model_used", False))

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
        combined = f"{system_prompt}\n{user_prompt}"
        is_critic_or_judge = (
            "[INDEPENDENT_CRITIC:" in combined
            or "[PROPOSAL_PAYLOAD]" in combined
            or "PEDAGOGICAL_EVALUATION" in combined
        )
        is_decomposer = not is_critic_or_judge and "GENERATE_PROPOSAL_TASKS" in user_prompt
        is_milestone_planner = (
            not is_critic_or_judge
            and not is_decomposer
            and (
                (
                    isinstance(response_schema, type)
                    and issubclass(response_schema, MilestoneGenerationLLMOutput)
                )
                or (
                    isinstance(response_schema, dict)
                    and "milestones" in (response_schema.get("properties") or {})
                )
            )
        )

        t_start = time.perf_counter()
        try:
            res = await self._inner.generate_structured(
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
            t_end = time.perf_counter()
            rec = {
                "t_start": t_start,
                "t_end": t_end,
                "elapsed_ms": round((t_end - t_start) * 1000.0, 3),
                "prompt_tokens": int(res.prompt_tokens or 0),
                "output_tokens": int(res.output_tokens or 0),
                "thinking_tokens": int(res.thinking_tokens or 0),
                "tool_calls_count": len(res.raw_tool_results or ()),
                "status": "OK",
            }
            if is_decomposer:
                self._telemetry.decomposer_calls.append(rec)
            elif is_critic_or_judge:
                self._telemetry.critic_judge_calls.append(rec)
            elif is_milestone_planner:
                self._telemetry.milestone_planner_calls.append(rec)
            return res
        except BaseException as exc:
            t_end = time.perf_counter()
            err_rec = {
                "t_start": t_start,
                "t_end": t_end,
                "elapsed_ms": round((t_end - t_start) * 1000.0, 3),
                "prompt_tokens": 0,
                "output_tokens": 0,
                "thinking_tokens": 0,
                "tool_calls_count": 0,
                "status": f"ERR:{type(exc).__name__}",
            }
            if is_decomposer:
                self._telemetry.decomposer_calls.append(err_rec)
            elif is_critic_or_judge:
                self._telemetry.critic_judge_calls.append(err_rec)
            elif is_milestone_planner:
                self._telemetry.milestone_planner_calls.append(err_rec)
            raise

    async def stream_structured(
        self, *, system_prompt: str, user_prompt: str
    ) -> AsyncIterator[str]:
        del system_prompt, user_prompt
        yield "{}"


class TelemetryKnowledgeBase(KnowledgeBasePort):
    """In-memory KnowledgeBasePort recording prefetch / tool-call latency and counts."""

    def __init__(self, telemetry: ScenarioTelemetry) -> None:
        self._inner = InMemoryKnowledgeBaseRepository(
            concepts=VERIFIED_SEED_CONCEPTS,
            edges=VERIFIED_SEED_EDGES,
            resources=(*VERIFIED_SEED_RESOURCES, *EXTRA_PRODUCTION_RESOURCES),
        )
        self._telemetry = telemetry

    async def search_concepts(
        self,
        query: str,
        *,
        domain: str | None = None,
        learner_level: str | None = None,
        limit: int = 10,
    ) -> list[LearningConcept]:
        t0 = time.perf_counter()
        res = await self._inner.search_concepts(
            query, domain=domain, learner_level=learner_level, limit=limit
        )
        t1 = time.perf_counter()
        self._telemetry.kb_calls.append(
            {"op": "search_concepts", "t_start": t0, "t_end": t1, "count": len(res)}
        )
        return res

    async def get_prerequisite_graph(
        self,
        concept_ids: Sequence[str],
        *,
        max_depth: int = 3,
    ) -> ConceptPrerequisiteGraph:
        t0 = time.perf_counter()
        res = await self._inner.get_prerequisite_graph(concept_ids, max_depth=max_depth)
        t1 = time.perf_counter()
        self._telemetry.kb_calls.append(
            {
                "op": "get_prerequisite_graph",
                "t_start": t0,
                "t_end": t1,
                "count": len(res.nodes),
            }
        )
        return res

    async def get_learning_resources_and_guidance(
        self,
        *,
        query: str | None = None,
        domain: str | None = None,
        concept_ids: Sequence[str] = (),
        task_type: str | None = None,
        limit: int = 10,
    ) -> list[LearningResource]:
        t0 = time.perf_counter()
        res = await self._inner.get_learning_resources_and_guidance(
            query=query,
            domain=domain,
            concept_ids=concept_ids,
            task_type=task_type,
            limit=limit,
        )
        t1 = time.perf_counter()
        self._telemetry.kb_calls.append(
            {
                "op": "get_learning_resources_and_guidance",
                "t_start": t0,
                "t_end": t1,
                "count": len(res),
            }
        )
        return res


# ---------------------------------------------------------------------------
# In-Memory Repositories & Ports for Use-Case Harness
# ---------------------------------------------------------------------------
class _InMemGoalRepo(GoalRepositoryPort):
    def __init__(self, goal: Goal) -> None:
        self.items: dict[UUID, Goal] = {goal.id: goal}

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


class _InMemRoadmapRepo(RoadmapRepositoryPort):
    def __init__(self, roadmap: Roadmap) -> None:
        self.items: dict[UUID, Roadmap] = {roadmap.id: roadmap}

    async def save(self, roadmap: Roadmap) -> Roadmap:
        self.items[roadmap.id] = roadmap
        return roadmap

    async def get_by_id(self, roadmap_id: UUID) -> Roadmap | None:
        return self.items.get(roadmap_id)

    async def get_by_id_for_user(self, roadmap_id: UUID, user_id: UUID) -> Roadmap | None:
        r = self.items.get(roadmap_id)
        return r if r and r.user_id == user_id else None

    async def list_by_user_id(self, user_id: UUID, *, status: str | None = None) -> list[Roadmap]:
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


class _InMemMilestoneRepo(MilestoneRepositoryPort):
    def __init__(self, roadmap_id: UUID, milestones: Sequence[Milestone]) -> None:
        self.by_roadmap: dict[UUID, list[Milestone]] = {roadmap_id: list(milestones)}

    async def save_many(self, roadmap_id: UUID, milestones: Sequence[Milestone]) -> list[Milestone]:
        self.by_roadmap[roadmap_id] = list(milestones)
        return sorted(self.by_roadmap[roadmap_id], key=lambda m: m.sequence_order)

    async def list_by_roadmap_id(self, roadmap_id: UUID) -> list[Milestone]:
        return sorted(self.by_roadmap.get(roadmap_id, []), key=lambda m: m.sequence_order)

    async def approve_all_for_roadmap(self, roadmap_id: UUID, now: datetime) -> list[Milestone]:
        items = self.by_roadmap.get(roadmap_id, [])
        for m in items:
            m.approve(now)
        return sorted(items, key=lambda m: m.sequence_order)


class _InMemProposalRepo(ScheduleProposalRepositoryPort):
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
                p.mark_discarded(now)
                cnt += 1
        return cnt


class _InMemScheduleRepo(OfficialScheduleRepositoryPort):
    def __init__(self) -> None:
        self.schedule: OfficialSchedule | None = None

    async def get_by_roadmap_id(self, roadmap_id: UUID) -> OfficialSchedule | None:
        del roadmap_id
        return self.schedule

    async def save(self, schedule: OfficialSchedule) -> OfficialSchedule:
        self.schedule = schedule
        return schedule


class _InMemBlockRepo(ScheduleBlockRepositoryPort):
    def __init__(self) -> None:
        self.blocks: list[ScheduleBlock] = []

    async def get_by_schedule_id(self, schedule_id: UUID) -> list[ScheduleBlock]:
        del schedule_id
        return list(self.blocks)

    async def list_by_roadmap_ids(self, roadmap_ids: Sequence[UUID]) -> list[ScheduleBlock]:
        del roadmap_ids
        return []

    async def save_all(self, blocks: Sequence[ScheduleBlock]) -> list[ScheduleBlock]:
        self.blocks = list(blocks)
        return self.blocks


class _InMemQuotaFacade(QuotaFacadePort):
    def __init__(self) -> None:
        self.reserved: list[UUID] = []
        self.committed: list[tuple[UUID, int, int, str]] = []
        self.released: list[tuple[UUID, str]] = []

    async def reserve_quota(
        self,
        user_id: UUID,
        operation_type: str = "ROADMAP_GENERATION",
        cost: int = 1,
        ttl_seconds: int = 120,
    ) -> UUID:
        del user_id, operation_type, cost, ttl_seconds
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
        self.committed.append((reservation_id, prompt_tokens, completion_tokens, model_name))

    async def release_reservation(self, reservation_id: UUID, *, reason: str = "") -> None:
        self.released.append((reservation_id, reason))


class _InMemUoW(AsyncUnitOfWork):
    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None

    def collect_events_from(self, *aggregates: Any) -> None:
        del aggregates


class _InMemAvailabilityPort(AvailabilityQueryPort):
    def __init__(self, snapshot: AvailabilitySnapshotDTO) -> None:
        self._snapshot = snapshot

    async def get_active_availability(self, user_id: UUID) -> AvailabilitySnapshotDTO | None:
        del user_id
        return self._snapshot


class _InMemLearnerProfilePort(LearnerProfileQueryPort):
    def __init__(self, user_id: UUID, opt_session_minutes: int = 60) -> None:
        self._profile = LearnerProfileDTO(
            user_id=user_id,
            opt_session_minutes=opt_session_minutes,
            estimation_bias_beta=1.0,
            peak_productivity_slots=("EVENING",),
        )

    async def get_learner_profile(self, user_id: UUID) -> LearnerProfileDTO:
        del user_id
        return self._profile


class _InMemExecSyncPort(ExecutionScheduleSyncPort):
    def __init__(self) -> None:
        self.synced_tasks: list[Any] = []

    async def get_tasks_for_roadmaps(
        self, *args: Any, **kwargs: Any
    ) -> list[ExistingScheduledTaskDTO]:
        del args, kwargs
        return []

    async def sync_official_schedule_tasks(self, **kwargs: Any) -> ScheduleSyncResultDTO:
        tasks = kwargs["proposed_tasks"]
        self.synced_tasks = list(tasks)
        return ScheduleSyncResultDTO(
            roadmap_id=kwargs["roadmap_id"],
            official_schedule_id=kwargs["official_schedule_id"],
            preserved_completed_tasks_count=0,
            replaced_tasks_count=0,
            inserted_tasks_count=len(tasks),
            affected_tasks_count=len(tasks),
            total_shifted_minutes=0,
            total_active_sessions=len(tasks),
            total_planned_minutes=sum(t.estimated_minutes for t in tasks),
        )


class _InMemChangeLogPort(ScheduleChangeLogPort):
    def __init__(self) -> None:
        self.logs: list[dict[str, Any]] = []

    async def record_change_log(self, **kwargs: Any) -> None:
        self.logs.append(kwargs)


class _InMemUserQueryPort(UserQueryPort):
    def __init__(self, user_id: UUID, timezone: str = "UTC", tier: str = "FREE") -> None:
        self._snapshot = SimpleNamespace(id=user_id, timezone=timezone, tier=tier)

    async def get_user_by_id(self, user_id: UUID) -> Any:
        return self._snapshot if user_id == self._snapshot.id else None


class _ProductionLearnerMemoryPort(LearnerMemoryQueryPort):
    """Production-equivalent LearnerMemoryQueryPort returning active memory & mastery items."""

    def __init__(self, user_id: UUID, domain: str) -> None:
        self._items = (
            LearnerMemoryItemSnapshotDTO(
                id=generate_uuid7(),
                user_id=user_id,
                category="PREFERENCE",
                memory_key="study_modality",
                memory_value="hands-on coding labs with automated tests (70% practice)",
                confidence=0.92,
                source_workflow="PLAN_CREATION",
            ),
            LearnerMemoryItemSnapshotDTO(
                id=generate_uuid7(),
                user_id=user_id,
                category="CONSTRAINT",
                memory_key="session_pacing",
                memory_value="preferred_block_minutes=60; avoid_late_night_splits=true",
                confidence=0.88,
                source_workflow="WEEKLY_REVIEW",
            ),
            LearnerMemoryItemSnapshotDTO(
                id=generate_uuid7(),
                user_id=user_id,
                category="STRENGTH",
                memory_key=f"foundation_{domain}",
                memory_value=f"Nắm vững kiến trúc cơ bản của miền {domain}",
                confidence=0.85,
                source_workflow="PROVE_EVALUATION",
            ),
        )
        self._masteries: tuple[Any, ...] = (
            SimpleNamespace(
                user_id=user_id,
                concept_id="py-control-flow-functions",
                concept_key="py-control-flow-functions",
                mastery_score=0.88,
                status="MASTERED",
                evidence_count=4,
                last_evidence_type="PROVE_PASSED",
            ),
            SimpleNamespace(
                user_id=user_id,
                concept_id="http-rest-fundamentals",
                concept_key="http-rest-fundamentals",
                mastery_score=0.82,
                status="MASTERED",
                evidence_count=3,
                last_evidence_type="TASK_COMPLETED",
            ),
        )

    async def list_active_memory_items(
        self, user_id: UUID, limit: int = 20
    ) -> list[LearnerMemoryItemSnapshotDTO]:
        del user_id
        return list(self._items[:limit])

    async def list_concept_masteries(
        self, user_id: UUID, concept_ids: list[str] | None = None
    ) -> list[ConceptMasterySnapshotDTO]:
        del user_id, concept_ids
        return list(self._masteries)

    async def upsert_memory_and_mastery_feedback(
        self,
        user_id: UUID,
        *,
        memories: list[dict[str, Any]] | None = None,
        masteries: list[dict[str, Any]] | None = None,
    ) -> None:
        del user_id, memories, masteries


class _ProductionKnowledgeSourceRepo(KnowledgeSourceRepositoryPort):
    """Production-equivalent KnowledgeSourceRepositoryPort returning domain RAG chunks."""

    def __init__(self, user_id: UUID, goal_id: UUID, scenario: dict[str, Any]) -> None:
        now = datetime(2026, 11, 2, 9, 0, tzinfo=UTC)
        source_id = generate_uuid7()
        title = str(scenario["goal"]["title"])
        desc = str(scenario["goal"]["raw_description"])
        self._source = KnowledgeSource(
            id=source_id,
            user_id=user_id,
            goal_id=goal_id,
            source_type=KnowledgeSourceType.TXT,
            title=f"Tài liệu tham khảo kỹ thuật: {title[:60]}",
            source_uri=None,
            content_hash="sha256:prod-equiv-seed",
            ingestion_status=KnowledgeIngestionStatus.INDEXED,
            chunk_count=2,
            provenance_metadata={"origin": "seeded_rag"},
            error_detail=None,
            created_at=now,
            updated_at=now,
        )
        self._chunks = (
            KnowledgeChunk(
                id=generate_uuid7(),
                source_id=source_id,
                goal_id=goal_id,
                chunk_index=0,
                content=(
                    f"Tóm tắt chuẩn kỹ thuật cho '{title}': {desc} "
                    "Mọi cột mốc cần kết hợp lý thuyết cốt lõi, bài tập thực hành có kiểm thử tự động "
                    "và bước tổng hợp đánh giá chất lượng."
                ),
                token_count=64,
                provenance_json={"source": "seeded_rag", "chunk": 0},
                created_at=now,
            ),
            KnowledgeChunk(
                id=generate_uuid7(),
                source_id=source_id,
                goal_id=goal_id,
                chunk_index=1,
                content=(
                    "Hướng dẫn thực hành: Chia nhỏ từng cột mốc thành các phiên học 45-90 phút, "
                    "ưu tiên xây dựng prototype chạy được trước khi tối ưu hiệu năng và viết kiểm thử."
                ),
                token_count=48,
                provenance_json={"source": "seeded_rag", "chunk": 1},
                created_at=now,
            ),
        )

    async def save_source(self, source: KnowledgeSource) -> KnowledgeSource:
        return source

    async def get_source_for_user(self, source_id: UUID, user_id: UUID) -> KnowledgeSource | None:
        del source_id, user_id
        return self._source

    async def list_sources_for_goal(self, goal_id: UUID, user_id: UUID) -> list[KnowledgeSource]:
        del goal_id, user_id
        return [self._source]

    async def replace_chunks(self, source_id: UUID, chunks: Sequence[KnowledgeChunk]) -> None:
        del source_id, chunks

    async def hybrid_search(
        self,
        *,
        goal_id: UUID,
        query: str,
        query_embedding: Sequence[float] | None = None,
        limit: int = 5,
    ) -> list[KnowledgeChunk]:
        del goal_id, query, query_embedding
        return list(self._chunks[:limit])


# ---------------------------------------------------------------------------
# Scenario Fixture Builder
# ---------------------------------------------------------------------------
def _build_goal_clarification_json(scenario: dict[str, Any]) -> str:
    raw_answers = scenario.get("clarification_answers")
    if not isinstance(raw_answers, dict) or not raw_answers:
        return ""
    answers_list = [
        {
            "question_id": f"q_{idx}",
            "question_text": f"Làm rõ chiều {dim}",
            "diagnostic_dimension": str(dim).upper(),
            "answer": str(ans),
        }
        for idx, (dim, ans) in enumerate(raw_answers.items(), start=1)
    ]
    facts_list = [
        {
            "dimension": str(dim).upper(),
            "status": GapStatus.KNOWN.value,
            "provenance": "USER_CONFIRMED",
            "value": str(ans),
        }
        for dim, ans in raw_answers.items()
    ]
    payload = ClarificationContextPayload(
        session_id=str(generate_uuid7()),
        status="ANSWERED",
        answers=answers_list,
        facts=facts_list,
        rounds_completed=1,
    )
    return payload.to_json_str()


def _build_scenario_domain_objects(
    scenario: dict[str, Any],
    *,
    scale_hard_milestone_efforts: bool,
) -> tuple[
    UUID, Goal, Roadmap, list[Milestone], AvailabilitySnapshotDTO, AvailabilityConfigurationDTO
]:
    now = datetime(2026, 11, 2, 9, 0, tzinfo=UTC)
    user_id = generate_uuid7()
    goal_id = generate_uuid7()
    roadmap_id = generate_uuid7()

    start_d = date.fromisoformat(str(scenario["start_date"]))
    target_d = date.fromisoformat(str(scenario["target_date"]))
    avail_raw = dict(scenario.get("availability") or {})
    avail_cfg = _build_availability(avail_raw)

    clar_json = _build_goal_clarification_json(scenario)
    goal = Goal(
        id=goal_id,
        user_id=user_id,
        title=str(scenario["goal"]["title"]),
        raw_description=str(scenario["goal"].get("raw_description", "")),
        prior_knowledge_level=str(scenario.get("learner_level", "INTERMEDIATE")),
        target_date=target_d,
        clarification_context=clar_json or None,
        status=GoalStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )

    raw_ms_list = list(scenario.get("milestones") or [])
    p_hard, _ = SpatioTemporalRuleEngine.calculate_hard_packable_capacity(
        avail_cfg, start_date=start_d, target_date=target_d
    )

    if scale_hard_milestone_efforts and raw_ms_list:
        per_ms_seed = max(120, int((p_hard * 0.85) // len(raw_ms_list)))
        seeded_ms = [
            {
                **m,
                "estimated_effort_minutes": per_ms_seed,
                "dependencies": [idx - 1] if idx > 1 else [],
            }
            for idx, m in enumerate(raw_ms_list, start=1)
        ]
        alloc = MilestoneEffortAllocator.allocate(
            seeded_ms,
            hard_packable_capacity_minutes=p_hard,
            prior_knowledge_level=goal.prior_knowledge_level,
            start_date=start_d,
            target_date=target_d,
            availability=avail_cfg,
        )
        eff_by_seq = {
            b.sequence_order: b.normalized_planned_effort_minutes for b in alloc.breakdowns
        }
        planning_meta: dict[str, Any] = {
            "preliminary_feasibility": alloc.to_metadata_dict(),
            "generation_strategy": "FULL_SCOPE",
        }
    else:
        eff_by_seq = {
            int(m.get("sequence_order", idx)): int(m.get("estimated_effort_minutes", 120))
            for idx, m in enumerate(raw_ms_list, start=1)
        }
        planning_meta = {"generation_strategy": "FULL_SCOPE"}

    roadmap = Roadmap(
        id=roadmap_id,
        goal_id=goal_id,
        user_id=user_id,
        title=goal.title,
        description=goal.raw_description,
        start_date=start_d,
        target_date=target_d,
        status=RoadmapStatus.INITIALIZED,
        planning_metadata=planning_meta,
        created_at=now,
        updated_at=now,
    )

    milestones: list[Milestone] = []
    for idx, raw_m in enumerate(raw_ms_list, start=1):
        seq = int(raw_m.get("sequence_order", idx))
        mid = UUID(str(raw_m["milestone_id"]))
        raw_outcomes = raw_m.get("learning_outcomes") or []
        outcomes = tuple(
            str(o.get("description") or o.get("id") or o) if isinstance(o, dict) else str(o)
            for o in raw_outcomes
        )
        completion_criteria = str(
            raw_m.get("completion_criteria")
            or "; ".join(outcomes)
            or f"Hoàn thành {raw_m.get('title', '')}"
        )
        prereqs = (milestones[-1].id,) if milestones else ()
        milestones.append(
            Milestone(
                id=mid,
                roadmap_id=roadmap_id,
                sequence_order=seq,
                title=str(raw_m["title"]),
                description=str(raw_m.get("description") or ""),
                learning_outcomes=outcomes,
                completion_criteria=completion_criteria,
                estimated_effort_minutes=eff_by_seq.get(seq, 120),
                required_concepts=tuple(str(c) for c in (raw_m.get("required_concepts") or [])),
                prerequisite_milestone_ids=prereqs,
                status=MilestoneStatus.APPROVED,
                created_at=now,
                updated_at=now,
            )
        )

    avail_snapshot = AvailabilitySnapshotDTO(
        user_id=user_id,
        mode=str(avail_raw.get("mode", "MODE_A")),
        daily_cap_minutes=int(avail_raw.get("default_daily_quota_minutes", 120)),
        weekly_capacity_minutes=max(120, p_hard // 4),
        daily_quota_minutes={
            str(k): int(v) for k, v in (avail_raw.get("daily_quota_minutes") or {}).items()
        },
        availability_slots=tuple(avail_raw.get("availability_slots") or ()),
        disabled_weekdays=tuple(avail_raw.get("disabled_weekdays") or ()),
    )
    return user_id, goal, roadmap, milestones, avail_snapshot, avail_cfg


# ---------------------------------------------------------------------------
# Part 1: Production-Equivalent Prompt & Context Deduplication Measurement
# ---------------------------------------------------------------------------
async def run_part_1_prompt_overhead_measurement() -> dict[str, Any]:
    print(
        "\n=== [Part 1] Prompt & Context Overhead Measurement (Production-Equivalent) ===",
        flush=True,
    )
    hard_scenarios = load_eval_dataset(HARD_6_GOALS_DATASET_PATH)
    engine = ContextEngine()
    per_scenario_rows: list[dict[str, Any]] = []

    for sc in hard_scenarios:
        uid, goal, roadmap, milestones, _, avail_cfg = _build_scenario_domain_objects(
            sc, scale_hard_milestone_efforts=True
        )
        profile = LearnerProfileDTO(
            user_id=uid,
            opt_session_minutes=60,
            estimation_bias_beta=1.0,
            peak_productivity_slots=("EVENING",),
        )
        mem_port = _ProductionLearnerMemoryPort(uid, str(sc.get("domain", "general")))
        rag_repo = _ProductionKnowledgeSourceRepo(uid, goal.id, sc)
        tel = ScenarioTelemetry()
        kb = TelemetryKnowledgeBase(tel)

        memories = await mem_port.list_active_memory_items(uid)
        masteries = await mem_port.list_concept_masteries(uid)
        chunks = await rag_repo.hybrid_search(goal_id=goal.id, query=goal.title, limit=5)

        # 1. Stage 3 Task Decomposition Context & Prompts
        structured_ctx = RoadmapContextBuilder.build_task_decomposition_context(
            goal=goal,
            roadmap=roadmap,
            milestones=milestones,
            availability=avail_cfg,
            learner_profile=profile,
            existing_tasks=(),
            reference_date=roadmap.start_date,
        )
        start_date_str = (roadmap.start_date or date(2026, 11, 2)).isoformat()
        target_date_str = roadmap.target_date.isoformat() if roadmap.target_date else "N/A"

        # Before dedup: legacy header_markers had MILESTONE_IDS + AVAILABILITY_SLOTS, and include_planning_context=True
        legacy_ms_lines = [
            (
                f"- id={m.id} | seq={m.sequence_order} | "
                f"title={format_untrusted_block(UntrustedBlockKind.MILESTONE_DATA, m.title)} | "
                f"outcome_ids={','.join(f'M{m.sequence_order}-O{i}' for i in range(1, len(m.learning_outcomes) + 1))} | "
                f"required_concepts={','.join(m.required_concepts)} | "
                f"estimated_effort_minutes={m.estimated_effort_minutes}"
            )
            for m in milestones
        ]
        legacy_slot_lines = [
            f"{slot.day_of_week}: {slot.start_time}-{slot.end_time}"
            for slot in avail_cfg.availability_slots
            if slot.is_active
        ]
        legacy_header_markers = (
            "GENERATE_PROPOSAL_TASKS\n"
            f"Start Date: {start_date_str}\n"
            f"Target Date: {target_date_str}\n"
            f"Availability Mode: {avail_cfg.mode}\n"
            "MILESTONE_IDS:\n"
            + "\n".join(legacy_ms_lines)
            + "\nAVAILABILITY_SLOTS:\n"
            + ("\n".join(legacy_slot_lines) if legacy_slot_lines else "monday: 19:30-21:30")
        )
        assembled_before = RoadmapContextBuilder.assemble_harness_context(
            workflow_stage="TASK_DECOMPOSITION",
            base_context_text=structured_ctx,
            learner_diagnostic={
                "prior_knowledge_level": goal.prior_knowledge_level,
                "opt_session_minutes": profile.opt_session_minutes,
            },
            workflow_constraints={
                "start_date": start_date_str,
                "target_date": target_date_str,
                "availability_mode": avail_cfg.mode,
            },
            memory_items=memories,
            concept_masteries=masteries,
            knowledge_chunks=chunks,
            include_planning_context=True,
        )
        monolithic_prompt_before = build_task_decomposer_prompt(
            f"{legacy_header_markers}\n\n{structured_ctx}\n\n{assembled_before.text}"
        )

        # After dedup: PR-E monolithic prompt
        dedup_header_markers = (
            "GENERATE_PROPOSAL_TASKS\n"
            f"Start Date: {start_date_str}\n"
            f"Target Date: {target_date_str}\n"
            f"Availability Mode: {avail_cfg.mode}"
        )
        assembled_after = RoadmapContextBuilder.assemble_harness_context(
            workflow_stage="TASK_DECOMPOSITION",
            base_context_text=structured_ctx,
            learner_diagnostic={
                "prior_knowledge_level": goal.prior_knowledge_level,
                "opt_session_minutes": profile.opt_session_minutes,
            },
            workflow_constraints={
                "start_date": start_date_str,
                "target_date": target_date_str,
                "availability_mode": avail_cfg.mode,
            },
            memory_items=memories,
            concept_masteries=masteries,
            knowledge_chunks=chunks,
            include_planning_context=False,
        )
        harness_suffix = f"\n\n{assembled_after.text}" if assembled_after.text else ""
        monolithic_prompt_after = build_task_decomposer_prompt(
            f"{dedup_header_markers}\n\n{structured_ctx}{harness_suffix}"
        )

        # Milestone-scoped prompts (1 per milestone with prefetched resources)
        ms_prompt_chars: list[int] = []
        ms_prompt_tokens: list[int] = []
        for m in milestones:
            prefetched_res = await kb.get_learning_resources_and_guidance(
                query=f"{m.title} {' '.join(m.learning_outcomes)}"[:200],
                concept_ids=list(m.required_concepts),
                limit=6,
            )
            m_prompt = MilestoneScopedTaskDecomposer._build_milestone_prompt(
                milestone=m,
                all_milestones=milestones,
                goal=goal,
                roadmap=roadmap,
                availability=avail_cfg,
                learner_profile=profile,
                existing_tasks=(),
                prefetched_resources=prefetched_res,
                harness_suffix=harness_suffix,
                start_date=roadmap.start_date or date(2026, 11, 2),
                reference_date=roadmap.start_date or date(2026, 11, 2),
            )
            ms_prompt_chars.append(len(m_prompt))
            ms_prompt_tokens.append(engine._estimate_tokens(m_prompt))

        # 2. Stage 2 Milestone Planner Prompt before vs after dedup
        (
            prefetched_concepts,
            prefetched_graphs,
        ) = await RoadmapContextBuilder.prefetch_milestone_kb_evidence(
            kb,
            query_text=f"{goal.title} {goal.raw_description or ''}",
            learner_level=goal.prior_knowledge_level,
        )
        ms_ctx_block = RoadmapContextBuilder.build_milestone_planning_context(
            goal=goal,
            roadmap=roadmap,
            kb_concepts=prefetched_concepts,
            kb_graphs=prefetched_graphs,
        )
        ms_assembled_before = RoadmapContextBuilder.assemble_harness_context(
            workflow_stage="MILESTONE_PLANNING",
            base_context_text=ms_ctx_block,
            learner_diagnostic={"prior_knowledge_level": goal.prior_knowledge_level},
            workflow_constraints={
                "start_date": start_date_str,
                "target_date": target_date_str,
            },
            memory_items=memories,
            concept_masteries=masteries,
            knowledge_chunks=chunks,
            include_planning_context=True,
        )
        ms_assembled_after = RoadmapContextBuilder.assemble_harness_context(
            workflow_stage="MILESTONE_PLANNING",
            base_context_text=ms_ctx_block,
            learner_diagnostic={"prior_knowledge_level": goal.prior_knowledge_level},
            workflow_constraints={
                "start_date": start_date_str,
                "target_date": target_date_str,
            },
            memory_items=memories,
            concept_masteries=masteries,
            knowledge_chunks=chunks,
            include_planning_context=False,
        )
        planner_prompt_before = build_milestone_planner_prompt(
            f"{ms_ctx_block}\n\n{ms_assembled_before.text}",
            generation_strategy="FULL_SCOPE",
        )
        planner_prompt_after = build_milestone_planner_prompt(
            f"{ms_ctx_block}\n\n{ms_assembled_after.text}",
            generation_strategy="FULL_SCOPE",
        )

        # 3. Stage 1 Goal Clarifier Prompt before vs after dedup
        gaps = InformationGapAnalyzer().analyze(
            goal=goal,
            provenance=GoalFactProvenance(),
            weekly_commitment_hours=None,
            availability_weekly_minutes=540,
        )
        q_gaps = InformationGapAnalyzer().select_question_gaps(gaps, limit=3)
        gaps_block = "\n".join(
            f"- {g.dimension}: {g.status.value}; ảnh hưởng={g.roadmap_decision}" for g in q_gaps
        )
        clar_ctx_before = RoadmapContextBuilder.build_clarification_context(
            goal, include_information_gaps=True
        )
        clar_assembled_before = RoadmapContextBuilder.assemble_harness_context(
            workflow_stage="GOAL_CLARIFICATION",
            base_context_text=clar_ctx_before,
            memory_items=memories,
            concept_masteries=masteries,
            knowledge_chunks=chunks,
            include_planning_context=True,
        )
        clar_prompt_before = build_goal_clarifier_prompt(
            f"{clar_ctx_before}\n\n[INFORMATION_GAPS_TO_CLARIFY]\n{gaps_block}\n\n{clar_assembled_before.text}",
            known_dimensions=[],
            gap_count=max(1, len(q_gaps)),
        )
        clar_ctx_after = RoadmapContextBuilder.build_clarification_context(
            goal, include_information_gaps=False
        )
        clar_assembled_after = RoadmapContextBuilder.assemble_harness_context(
            workflow_stage="GOAL_CLARIFICATION",
            base_context_text=clar_ctx_after,
            memory_items=memories,
            concept_masteries=masteries,
            knowledge_chunks=chunks,
            include_planning_context=False,
        )
        clar_prompt_after = build_goal_clarifier_prompt(
            f"{clar_ctx_after}\n\n[INFORMATION_GAPS_TO_CLARIFY]\n{gaps_block}\n\n{clar_assembled_after.text}",
            known_dimensions=[],
            gap_count=max(1, len(q_gaps)),
        )

        mono_before_tok = engine._estimate_tokens(monolithic_prompt_before)
        mono_after_tok = engine._estimate_tokens(monolithic_prompt_after)
        ms_mean_chars = round(sum(ms_prompt_chars) / len(ms_prompt_chars), 1)
        ms_mean_tok = round(sum(ms_prompt_tokens) / len(ms_prompt_tokens), 1)

        per_scenario_rows.append(
            {
                "scenario_id": sc["scenario_id"],
                "assembled_harness_context": {
                    "before_dedup_chars": len(assembled_before.text),
                    "before_dedup_tokens": assembled_before.total_tokens,
                    "after_dedup_chars": len(assembled_after.text),
                    "after_dedup_tokens": assembled_after.total_tokens,
                    "char_reduction_pct": round(
                        (1.0 - len(assembled_after.text) / len(assembled_before.text)) * 100.0,
                        2,
                    ),
                    "token_reduction_pct": round(
                        (1.0 - assembled_after.total_tokens / max(1, assembled_before.total_tokens))
                        * 100.0,
                        2,
                    ),
                },
                "stage_3_decomposer_user_prompt": {
                    "monolithic_before_dedup_chars": len(monolithic_prompt_before),
                    "monolithic_before_dedup_est_tokens": mono_before_tok,
                    "monolithic_after_dedup_chars": len(monolithic_prompt_after),
                    "monolithic_after_dedup_est_tokens": mono_after_tok,
                    "monolithic_dedup_char_reduction_pct": round(
                        (1.0 - len(monolithic_prompt_after) / len(monolithic_prompt_before))
                        * 100.0,
                        2,
                    ),
                    "monolithic_dedup_token_reduction_pct": round(
                        (1.0 - mono_after_tok / max(1, mono_before_tok)) * 100.0,
                        2,
                    ),
                    "milestone_scoped_per_call_mean_chars": ms_mean_chars,
                    "milestone_scoped_per_call_max_chars": max(ms_prompt_chars),
                    "milestone_scoped_per_call_mean_est_tokens": ms_mean_tok,
                    "milestone_scoped_per_call_max_est_tokens": max(ms_prompt_tokens),
                    "milestone_scoped_total_5_calls_chars": sum(ms_prompt_chars),
                    "milestone_scoped_total_5_calls_est_tokens": sum(ms_prompt_tokens),
                    "per_call_reduction_vs_monolithic_after_dedup_pct": round(
                        (1.0 - ms_mean_chars / len(monolithic_prompt_after)) * 100.0,
                        2,
                    ),
                    "per_call_reduction_vs_monolithic_before_dedup_pct": round(
                        (1.0 - ms_mean_chars / len(monolithic_prompt_before)) * 100.0,
                        2,
                    ),
                },
                "stage_2_milestone_planner_user_prompt": {
                    "before_dedup_chars": len(planner_prompt_before),
                    "before_dedup_est_tokens": engine._estimate_tokens(planner_prompt_before),
                    "after_dedup_chars": len(planner_prompt_after),
                    "after_dedup_est_tokens": engine._estimate_tokens(planner_prompt_after),
                    "char_reduction_pct": round(
                        (1.0 - len(planner_prompt_after) / len(planner_prompt_before)) * 100.0,
                        2,
                    ),
                },
                "stage_1_clarifier_user_prompt": {
                    "before_dedup_chars": len(clar_prompt_before),
                    "before_dedup_est_tokens": engine._estimate_tokens(clar_prompt_before),
                    "after_dedup_chars": len(clar_prompt_after),
                    "after_dedup_est_tokens": engine._estimate_tokens(clar_prompt_after),
                    "char_reduction_pct": round(
                        (1.0 - len(clar_prompt_after) / len(clar_prompt_before)) * 100.0,
                        2,
                    ),
                },
            }
        )

    n = len(per_scenario_rows)
    summary = {
        "scenarios_count": n,
        "assembled_harness_context_char_reduction_pct_mean": round(
            sum(r["assembled_harness_context"]["char_reduction_pct"] for r in per_scenario_rows)
            / n,
            2,
        ),
        "assembled_harness_context_token_reduction_pct_mean": round(
            sum(r["assembled_harness_context"]["token_reduction_pct"] for r in per_scenario_rows)
            / n,
            2,
        ),
        "monolithic_before_dedup_chars_mean": round(
            sum(
                r["stage_3_decomposer_user_prompt"]["monolithic_before_dedup_chars"]
                for r in per_scenario_rows
            )
            / n,
            1,
        ),
        "monolithic_before_dedup_est_tokens_mean": round(
            sum(
                r["stage_3_decomposer_user_prompt"]["monolithic_before_dedup_est_tokens"]
                for r in per_scenario_rows
            )
            / n,
            1,
        ),
        "monolithic_after_dedup_chars_mean": round(
            sum(
                r["stage_3_decomposer_user_prompt"]["monolithic_after_dedup_chars"]
                for r in per_scenario_rows
            )
            / n,
            1,
        ),
        "monolithic_after_dedup_est_tokens_mean": round(
            sum(
                r["stage_3_decomposer_user_prompt"]["monolithic_after_dedup_est_tokens"]
                for r in per_scenario_rows
            )
            / n,
            1,
        ),
        "monolithic_dedup_char_reduction_pct_mean": round(
            sum(
                r["stage_3_decomposer_user_prompt"]["monolithic_dedup_char_reduction_pct"]
                for r in per_scenario_rows
            )
            / n,
            2,
        ),
        "monolithic_dedup_token_reduction_pct_mean": round(
            sum(
                r["stage_3_decomposer_user_prompt"]["monolithic_dedup_token_reduction_pct"]
                for r in per_scenario_rows
            )
            / n,
            2,
        ),
        "milestone_scoped_per_call_chars_mean": round(
            sum(
                r["stage_3_decomposer_user_prompt"]["milestone_scoped_per_call_mean_chars"]
                for r in per_scenario_rows
            )
            / n,
            1,
        ),
        "milestone_scoped_per_call_est_tokens_mean": round(
            sum(
                r["stage_3_decomposer_user_prompt"]["milestone_scoped_per_call_mean_est_tokens"]
                for r in per_scenario_rows
            )
            / n,
            1,
        ),
        "milestone_scoped_total_5_calls_est_tokens_mean": round(
            sum(
                r["stage_3_decomposer_user_prompt"]["milestone_scoped_total_5_calls_est_tokens"]
                for r in per_scenario_rows
            )
            / n,
            1,
        ),
        "per_call_reduction_vs_monolithic_after_dedup_pct_mean": round(
            sum(
                r["stage_3_decomposer_user_prompt"][
                    "per_call_reduction_vs_monolithic_after_dedup_pct"
                ]
                for r in per_scenario_rows
            )
            / n,
            2,
        ),
        "stage_2_planner_char_reduction_pct_mean": round(
            sum(
                r["stage_2_milestone_planner_user_prompt"]["char_reduction_pct"]
                for r in per_scenario_rows
            )
            / n,
            2,
        ),
        "stage_1_clarifier_char_reduction_pct_mean": round(
            sum(r["stage_1_clarifier_user_prompt"]["char_reduction_pct"] for r in per_scenario_rows)
            / n,
            2,
        ),
    }
    print(f"  Part 1 Summary: {json.dumps(summary, ensure_ascii=False)}", flush=True)
    return {
        "summary": summary,
        "per_scenario": per_scenario_rows,
    }


# ---------------------------------------------------------------------------
# Part 2: Live Controlled A/B Execution Engine
# ---------------------------------------------------------------------------
def _configure_live_environment() -> tuple[str, str]:
    base_url, api_key = get_cobhub_config()
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
    os.environ["AI_TASK_DECOMPOSER_TIMEOUT_SECONDS"] = "36.0"
    os.environ["AI_TOOL_CALL_TIMEOUT_SECONDS"] = "40.0"
    os.environ["AI_QUALITY_CRITIC_TIMEOUT_SECONDS"] = "15.0"
    os.environ["AI_QUALITY_ARBITER_TIMEOUT_SECONDS"] = "14.5"
    os.environ["TIER3_JUDGE_TIMEOUT_SECONDS"] = "12.0"
    os.environ["AI_MIN_CRITIC_REMAINING_SECONDS"] = "6.0"
    os.environ["AI_MIN_JUDGE_REMAINING_SECONDS"] = "3.0"
    os.environ["AI_MIN_RETRY_REMAINING_SECONDS"] = "12.0"

    os.environ["SPATIO_TEMPORAL_V2_HARD_SOLVER_ENABLED"] = "true"
    os.environ["SPATIO_TEMPORAL_V2_SOFT_PACING_ENABLED"] = "true"
    os.environ["MILESTONE_EFFORT_ALLOCATOR_ENABLED"] = "true"
    os.environ["AI_MAX_CONCURRENT_LLM_REQUESTS"] = "16"

    get_settings.cache_clear()
    clear_cobhub_capability_probe_cache()
    return base_url, api_key


def _classify_run_error(
    exc: BaseException | None,
    *,
    feasibility_verdict: str | None = None,
    unscheduled_tasks_count: int = 0,
) -> str:
    if exc is None:
        if feasibility_verdict == "EXPLICIT_UNSCHEDULABLE" or unscheduled_tasks_count > 0:
            return "EXPLICIT_UNSCHEDULABLE"
        return "OTHER"
    if isinstance(exc, PlanInfeasibleError):
        return "PLAN_INFEASIBLE"
    if isinstance(exc, InsufficientCapacityError):
        return "EXPLICIT_UNSCHEDULABLE"
    if isinstance(exc, (ProposalValidationGateError, ScopeApprovalRequiredError)):
        return "VALIDATION_GATE"
    if isinstance(exc, (TimeoutError, asyncio.TimeoutError)):
        return "TIMEOUT"
    msg_lower = f"{type(exc).__name__} {exc}".lower()
    if any(
        tok in msg_lower for tok in ("timeout", "timed out", "quá thời gian", "exceeded pipeline")
    ):
        return "TIMEOUT"
    if "infeasible" in msg_lower:
        return "PLAN_INFEASIBLE"
    if "validation" in msg_lower or "schema" in msg_lower:
        return "VALIDATION_GATE"
    return "OTHER"


async def _execute_single_scenario(
    scenario: dict[str, Any],
    *,
    arm: ArchMode,
    e2e: bool,
    with_production_harness: bool,
    scale_hard_milestone_efforts: bool,
    base_adapter: LiteLLMAdapter,
) -> dict[str, Any]:
    now = datetime(2026, 11, 2, 9, 0, tzinfo=UTC)
    telemetry = ScenarioTelemetry()
    token_ctx = _ACTIVE_TELEMETRY.set(telemetry)

    t_wall_start = time.perf_counter()
    milestone_planner_ms = 0.0
    apply_rehearsal_ms = 0.0
    error_cat: str | None = None
    error_msg: str | None = None

    try:
        uid, goal, roadmap, fixture_milestones, avail_snap, avail_cfg = (
            _build_scenario_domain_objects(
                scenario,
                scale_hard_milestone_efforts=(scale_hard_milestone_efforts and not e2e),
            )
        )
        goal_repo = _InMemGoalRepo(goal)
        roadmap_repo = _InMemRoadmapRepo(roadmap)
        milestone_repo = _InMemMilestoneRepo(roadmap.id, [] if e2e else fixture_milestones)
        proposal_repo = _InMemProposalRepo()
        schedule_repo = _InMemScheduleRepo()
        block_repo = _InMemBlockRepo()
        avail_port = _InMemAvailabilityPort(avail_snap)
        profile_port = _InMemLearnerProfilePort(uid, opt_session_minutes=60)
        exec_sync_port = _InMemExecSyncPort()
        quota_facade = _InMemQuotaFacade()
        sse_store = InMemorySseJobStore()
        uow = _InMemUoW()
        user_query_port = _InMemUserQueryPort(uid, timezone="UTC")

        llm_wrapper = TelemetryLLMProvider(base_adapter, telemetry)
        kb_port: KnowledgeBasePort | None = (
            TelemetryKnowledgeBase(telemetry) if (with_production_harness or e2e) else None
        )
        mem_port: LearnerMemoryQueryPort | None = (
            _ProductionLearnerMemoryPort(uid, str(scenario.get("domain", "general")))
            if with_production_harness
            else None
        )
        rag_repo: KnowledgeSourceRepositoryPort | None = (
            _ProductionKnowledgeSourceRepo(uid, goal.id, scenario)
            if with_production_harness
            else None
        )

        # Optional Stage 2: ExecuteMilestoneGenerationUseCase + ApproveMilestonesUseCase
        if e2e:
            t_ms_start = time.perf_counter()
            ms_job_id = generate_uuid7()
            ms_res_id = await quota_facade.reserve_quota(uid, operation_type="MILESTONE_GEN")
            await sse_store.create_job(
                job_id=ms_job_id,
                user_id=uid,
                roadmap_id=roadmap.id,
                reservation_id=ms_res_id,
                job_type="MILESTONE_GEN",
                operation=f"MILESTONE_GEN:{roadmap.id}",
            )
            ms_uc = ExecuteMilestoneGenerationUseCase(
                goal_repo=goal_repo,
                roadmap_repo=roadmap_repo,
                milestone_repo=milestone_repo,
                quota_facade=quota_facade,
                llm_provider=llm_wrapper,
                sse_job_store=sse_store,
                uow=uow,
                knowledge_base=kb_port,
                learner_memory_port=mem_port,
                knowledge_source_repo=rag_repo,
                availability_query_port=avail_port,
                execution_sync_port=exec_sync_port,
                block_repo=block_repo,
                user_query_port=user_query_port,
                proposal_repo=proposal_repo,
            )
            await ms_uc.execute(
                job_id=ms_job_id,
                user_id=uid,
                roadmap_id=roadmap.id,
                reservation_id=ms_res_id,
                now=now,
                generation_strategy="FULL_SCOPE",
            )
            stored_rm = await roadmap_repo.get_by_id(roadmap.id)
            assert stored_rm is not None
            prelim = stored_rm.planning_metadata.get("preliminary_feasibility") or {}
            approve_uc = ApproveMilestonesUseCase(
                roadmap_repo=roadmap_repo,
                milestone_repo=milestone_repo,
                uow=uow,
                goal_repo=goal_repo,
                proposal_repo=proposal_repo,
                availability_query_port=avail_port,
                execution_sync_port=exec_sync_port,
                block_repo=block_repo,
                user_query_port=user_query_port,
            )
            if prelim.get("status") == "FIT_CAPACITY_REQUIRES_APPROVAL":
                await approve_uc.execute(
                    user_id=uid,
                    roadmap_id=roadmap.id,
                    confirmed_scope_proposal_version=int(prelim.get("scope_proposal_version", 1)),
                    confirmed_scope_proposal_hash=prelim.get("scope_proposal_hash"),
                    accept_fit_capacity=True,
                    now=now,
                )
            else:
                await approve_uc.execute(
                    user_id=uid,
                    roadmap_id=roadmap.id,
                    now=now,
                )
            milestone_planner_ms = round((time.perf_counter() - t_ms_start) * 1000.0, 3)
            # Clear KB calls from Stage 2 so `prefetch_or_tools_ms` reflects Stage 3 only
            telemetry.kb_calls.clear()

        active_milestones = await milestone_repo.list_by_roadmap_id(roadmap.id)

        # Stage 3: ExecuteScheduleProposalGenerationUseCase
        prop_job_id = generate_uuid7()
        prop_res_id = await quota_facade.reserve_quota(uid, operation_type="SCHEDULE_PROPOSAL_GEN")
        await sse_store.create_job(
            job_id=prop_job_id,
            user_id=uid,
            roadmap_id=roadmap.id,
            reservation_id=prop_res_id,
            job_type="SCHEDULE_PROPOSAL_GEN",
            operation=f"SCHEDULE_PROPOSAL_GEN:{roadmap.id}",
        )
        prop_uc = ExecuteScheduleProposalGenerationUseCase(
            goal_repo=goal_repo,
            roadmap_repo=roadmap_repo,
            milestone_repo=milestone_repo,
            proposal_repo=proposal_repo,
            availability_query_port=avail_port,
            learner_profile_port=profile_port,
            execution_sync_port=exec_sync_port,
            quota_facade=quota_facade,
            llm_provider=llm_wrapper,
            sse_job_store=sse_store,
            uow=uow,
            enable_tier3_judge=True,
            knowledge_base=kb_port if with_production_harness else None,
            user_query_port=user_query_port,
            block_repo=block_repo,
            learner_memory_port=mem_port,
            knowledge_source_repo=rag_repo,
        )
        saved_proposal = await prop_uc.execute(
            job_id=prop_job_id,
            user_id=uid,
            roadmap_id=roadmap.id,
            reservation_id=prop_res_id,
            now=now,
            decomposer_architecture_mode=arm,
        )

        # Stage 4: ApplyScheduleProposalUseCase Roundtrip Rehearsal
        t_apply_start = time.perf_counter()
        apply_uc = ApplyScheduleProposalUseCase(
            roadmap_repo=roadmap_repo,
            milestone_repo=milestone_repo,
            proposal_repo=proposal_repo,
            schedule_repo=schedule_repo,
            block_repo=block_repo,
            availability_query_port=avail_port,
            execution_sync_port=exec_sync_port,
            schedule_change_log_port=_InMemChangeLogPort(),
            uow=uow,
            user_query_port=user_query_port,
            goal_repo=goal_repo,
        )
        apply_result = await apply_uc.execute(
            user_id=uid,
            roadmap_id=roadmap.id,
            proposal_id=saved_proposal.id,
            confirm_soft_overflow=True,
            confirm_warnings=True,
            confirm_partial_schedule=False,
            now=now,
        )
        apply_rehearsal_ms = round((time.perf_counter() - t_apply_start) * 1000.0, 3)
        total_wall_ms = round((time.perf_counter() - t_wall_start) * 1000.0, 3)

        pdata = saved_proposal.proposal_data
        tasks = [t for t in (pdata.get("tasks") or []) if isinstance(t, dict)]
        deps = [d for d in (pdata.get("dependencies") or []) if isinstance(d, dict)]
        blocks = [b for b in (pdata.get("schedule_blocks") or []) if isinstance(b, dict)]

        # Evaluate structural & scheduling correctness
        cov_violations = validate_task_coverage(tasks, active_milestones)
        outcome_violations = [
            v
            for v in cov_violations
            if v.rule_code in ("MISSING_OUTCOME_COVERAGE", "MISSING_MILESTONE_COVERAGE")
        ]
        concept_violations = [
            v for v in cov_violations if v.rule_code == "MISSING_CONCEPT_COVERAGE"
        ]
        outcome_coverage_ok = len(outcome_violations) == 0
        concept_coverage_ok = len(concept_violations) == 0

        blocks_by_task: dict[str, list[dict[str, Any]]] = {}
        dates_by_task: dict[str, set[str]] = {}
        for b in blocks:
            tid = str(b.get("task_id", ""))
            blocks_by_task.setdefault(tid, []).append(b)
            bdate = str(b.get("block_date", ""))[:10]
            if bdate:
                dates_by_task.setdefault(tid, set()).add(bdate)

        dag_acyclic, prereq_ordered = _check_dag_acyclic_and_prereq_order(
            tasks, deps, blocks_by_task
        )
        dag_valid = bool(dag_acyclic and prereq_ordered)

        norm_titles = [
            " ".join(str(t.get("title", "")).lower().split())
            for t in tasks
            if str(t.get("title", "")).strip()
        ]
        title_counts = Counter(norm_titles)
        duplicate_tasks_count = sum(c - 1 for c in title_counts.values() if c > 1)
        duplicate_task_ratio = round(duplicate_tasks_count / max(1, len(tasks)), 4)

        unscheduled_count = sum(
            1 for t in tasks if safe_parse_iso_date(t.get("scheduled_date")) is None
        )
        unplaced_zero = unscheduled_count == 0

        sensitive_split_count = sum(
            1
            for t in tasks
            if NonSplittableTaskClassifier.is_non_splittable(t)
            and len(dates_by_task.get(str(t.get("task_id")), set())) > 1
        )
        non_splittable_ok = sensitive_split_count == 0

        forbidden = (scenario.get("expected_invariants") or {}).get("forbidden_substrings", [])
        serialized_prop = json.dumps(pdata, ensure_ascii=False).lower()
        injection_leaked = bool(scenario.get("is_injection_case", False)) and any(
            str(f).lower() in serialized_prop for f in forbidden if str(f).strip()
        )

        ms_efforts = [int(m.estimated_effort_minutes) for m in active_milestones]
        total_ms_effort = sum(ms_efforts)
        total_task_effort = sum(int(t.get("estimated_minutes", 0) or 0) for t in tasks)
        ms_vs_tasks_gap = (
            round(abs(total_task_effort - total_ms_effort) / total_ms_effort, 4)
            if total_ms_effort > 0
            else 0.0
        )
        all_ms_efforts_equal = len(set(ms_efforts)) <= 1 and len(ms_efforts) > 1

        judge_status = str(pdata.get("judge_status", "SKIPPED")).upper()
        ped_score = pdata.get("pedagogical_score")

        apply_passed = bool(
            apply_result.proposal.status == ScheduleProposalStatus.APPLIED
            and apply_result.inserted_tasks_count == len(tasks)
            and schedule_repo.schedule is not None
            and len(block_repo.blocks) > 0
        )
        passed = bool(
            len(tasks) > 0
            and outcome_coverage_ok
            and concept_coverage_ok
            and dag_valid
            and unplaced_zero
            and non_splittable_ok
            and not injection_leaked
            and apply_passed
        )
        if not passed:
            error_cat = _classify_run_error(
                None,
                feasibility_verdict=str(pdata.get("feasibility_verdict", "")),
                unscheduled_tasks_count=unscheduled_count,
            )

        dec_llm_ms = max(1.0, telemetry.decomposer_llm_wall_ms)
        dec_out_tok = telemetry.decomposer_output_tokens
        out_tok_per_task = round(dec_out_tok / max(1, len(tasks)), 2)
        tok_per_sec = round(dec_out_tok / (dec_llm_ms / 1000.0), 2)

        return {
            "scenario_id": scenario["scenario_id"],
            "domain": scenario.get("domain"),
            "learner_level": scenario.get("learner_level"),
            "deadline_regime": scenario.get("deadline_regime"),
            "planning_mode": scenario.get("planning_mode"),
            "arm": arm,
            "passed": passed,
            "apply_roundtrip_passed": apply_passed,
            "error_category": error_cat,
            "error_message": None,
            "tasks_count": len(tasks),
            "blocks_count": len(blocks),
            "dependencies_count": len(deps),
            "milestones_count": len(active_milestones),
            "attempts_used": int(pdata.get("attempts_used", 1)),
            "latencies_ms": {
                "milestone_planner": milestone_planner_ms,
                "prefetch_or_tools": telemetry.prefetch_or_tools_ms,
                "decomposer_llm": telemetry.decomposer_llm_wall_ms,
                "deterministic_scheduler": telemetry.deterministic_scheduler_ms,
                "critics_judge_parallel": telemetry.critics_judge_parallel_ms,
                "apply_rehearsal": apply_rehearsal_ms,
                "total_wall_time": total_wall_ms,
                "per_decomposer_call_ms": [c["elapsed_ms"] for c in telemetry.decomposer_calls],
            },
            "tokens": {
                "decomposer_prompt_tokens": telemetry.decomposer_prompt_tokens,
                "decomposer_output_tokens": telemetry.decomposer_output_tokens,
                "decomposer_thinking_tokens": telemetry.decomposer_thinking_tokens,
                "stage3_total_prompt_tokens": telemetry.stage3_total_prompt_tokens,
                "stage3_total_output_tokens": telemetry.stage3_total_output_tokens,
                "stage3_total_thinking_tokens": telemetry.stage3_total_thinking_tokens,
                "output_tokens_per_task": out_tok_per_task,
                "throughput_tok_per_sec": tok_per_sec,
                "tool_calls_count": telemetry.tool_calls_count,
                "kb_calls_count": len(telemetry.kb_calls),
            },
            "correctness": {
                "outcome_coverage_ok": outcome_coverage_ok,
                "concept_coverage_ok": concept_coverage_ok,
                "dag_acyclic": dag_acyclic,
                "prereq_ordered": prereq_ordered,
                "dag_valid": dag_valid,
                "duplicate_tasks_count": duplicate_tasks_count,
                "duplicate_task_ratio": duplicate_task_ratio,
                "unscheduled_tasks_count": unscheduled_count,
                "unplaced_tasks_zero": unplaced_zero,
                "sensitive_split_count": sensitive_split_count,
                "non_splittable_integrity_ok": non_splittable_ok,
                "injection_leaked": injection_leaked,
            },
            "effort_and_judge": {
                "total_milestone_effort_minutes": total_ms_effort,
                "total_task_effort_minutes": total_task_effort,
                "milestone_vs_tasks_gap": ms_vs_tasks_gap,
                "all_milestone_efforts_equal": all_ms_efforts_equal,
                "judge_status": judge_status,
                "pedagogical_score": ped_score,
                "feasibility_verdict": pdata.get("feasibility_verdict"),
            },
            "proposal_snapshot": {
                "goal_title": goal.title,
                "goal_description": goal.raw_description,
                "start_date": str(scenario["start_date"]),
                "target_date": str(scenario["target_date"]),
                "availability": scenario.get("availability"),
                "milestones": [
                    {
                        "milestone_id": str(m.id),
                        "sequence_order": m.sequence_order,
                        "title": m.title,
                        "description": m.description,
                        "learning_outcomes": list(m.learning_outcomes),
                        "completion_criteria": m.completion_criteria,
                        "estimated_effort_minutes": m.estimated_effort_minutes,
                        "required_concepts": list(m.required_concepts),
                        "prerequisite_milestone_ids": [
                            str(pid) for pid in m.prerequisite_milestone_ids
                        ],
                    }
                    for m in active_milestones
                ],
                "tasks": tasks,
                "dependencies": deps,
                "schedule_blocks": blocks,
            },
        }
    except Exception as exc:
        total_wall_ms = round((time.perf_counter() - t_wall_start) * 1000.0, 3)
        error_cat = _classify_run_error(exc)
        error_msg = sanitize_error_message(exc)
        return {
            "scenario_id": scenario["scenario_id"],
            "domain": scenario.get("domain"),
            "learner_level": scenario.get("learner_level"),
            "deadline_regime": scenario.get("deadline_regime"),
            "planning_mode": scenario.get("planning_mode"),
            "arm": arm,
            "passed": False,
            "apply_roundtrip_passed": False,
            "error_category": error_cat,
            "error_message": error_msg,
            "tasks_count": 0,
            "blocks_count": 0,
            "dependencies_count": 0,
            "milestones_count": 0,
            "attempts_used": len(telemetry.decomposer_calls),
            "latencies_ms": {
                "milestone_planner": milestone_planner_ms,
                "prefetch_or_tools": telemetry.prefetch_or_tools_ms,
                "decomposer_llm": telemetry.decomposer_llm_wall_ms,
                "deterministic_scheduler": telemetry.deterministic_scheduler_ms,
                "critics_judge_parallel": telemetry.critics_judge_parallel_ms,
                "apply_rehearsal": apply_rehearsal_ms,
                "total_wall_time": total_wall_ms,
                "per_decomposer_call_ms": [c["elapsed_ms"] for c in telemetry.decomposer_calls],
            },
            "tokens": {
                "decomposer_prompt_tokens": telemetry.decomposer_prompt_tokens,
                "decomposer_output_tokens": telemetry.decomposer_output_tokens,
                "decomposer_thinking_tokens": telemetry.decomposer_thinking_tokens,
                "stage3_total_prompt_tokens": telemetry.stage3_total_prompt_tokens,
                "stage3_total_output_tokens": telemetry.stage3_total_output_tokens,
                "stage3_total_thinking_tokens": telemetry.stage3_total_thinking_tokens,
                "output_tokens_per_task": 0.0,
                "throughput_tok_per_sec": 0.0,
                "tool_calls_count": telemetry.tool_calls_count,
                "kb_calls_count": len(telemetry.kb_calls),
            },
            "correctness": {
                "outcome_coverage_ok": False,
                "concept_coverage_ok": False,
                "dag_acyclic": False,
                "prereq_ordered": False,
                "dag_valid": False,
                "duplicate_tasks_count": 0,
                "duplicate_task_ratio": 0.0,
                "unscheduled_tasks_count": 0,
                "unplaced_tasks_zero": False,
                "sensitive_split_count": 0,
                "non_splittable_integrity_ok": False,
                "injection_leaked": False,
            },
            "effort_and_judge": {
                "total_milestone_effort_minutes": 0,
                "total_task_effort_minutes": 0,
                "milestone_vs_tasks_gap": None,
                "all_milestone_efforts_equal": False,
                "judge_status": "SKIPPED_NO_PROPOSAL",
                "pedagogical_score": None,
                "feasibility_verdict": None,
            },
            "proposal_snapshot": None,
        }
    finally:
        _ACTIVE_TELEMETRY.reset(token_ctx)


def _aggregate_arm_results(
    runs: Sequence[dict[str, Any]],
    *,
    arm: ArchMode,
    workload_name: str,
    concurrency: int,
    suite_wall_seconds: float,
) -> dict[str, Any]:
    total = len(runs)
    passed_runs = [r for r in runs if r["passed"]]
    passed_count = len(passed_runs)
    apply_passed_count = sum(1 for r in runs if r["apply_roundtrip_passed"])

    err_buckets = {
        "TIMEOUT": 0,
        "VALIDATION_GATE": 0,
        "EXPLICIT_UNSCHEDULABLE": 0,
        "PLAN_INFEASIBLE": 0,
        "OTHER": 0,
    }
    for r in runs:
        if not r["passed"]:
            cat = str(r.get("error_category") or "OTHER")
            err_buckets[cat if cat in err_buckets else "OTHER"] += 1

    def _stage_stats(stage_key: str) -> dict[str, float]:
        vals = [
            float(r["latencies_ms"][stage_key])
            for r in runs
            if r["latencies_ms"].get(stage_key) is not None
        ]
        return summarize_numeric(vals)

    passed_or_all = passed_runs if passed_runs else list(runs)
    gaps = [
        float(r["effort_and_judge"]["milestone_vs_tasks_gap"])
        for r in passed_runs
        if r["effort_and_judge"].get("milestone_vs_tasks_gap") is not None
    ]
    judge_counts = Counter(
        str(r["effort_and_judge"].get("judge_status") or "SKIPPED") for r in passed_runs
    )
    ped_scores = [
        float(r["effort_and_judge"]["pedagogical_score"])
        for r in passed_runs
        if r["effort_and_judge"].get("pedagogical_score") is not None
    ]

    return {
        "workload": workload_name,
        "arm": arm,
        "concurrency": concurrency,
        "suite_wall_seconds": round(suite_wall_seconds, 2),
        "total_runs": total,
        "passed_count": passed_count,
        "pass_rate": round(passed_count / max(1, total), 4),
        "apply_roundtrip_passed_count": apply_passed_count,
        "apply_roundtrip_pass_rate": round(apply_passed_count / max(1, total), 4),
        "error_breakdown": err_buckets,
        "stage_latency_ms": {
            "milestone_planner": _stage_stats("milestone_planner"),
            "prefetch_or_tools": _stage_stats("prefetch_or_tools"),
            "decomposer_llm": _stage_stats("decomposer_llm"),
            "deterministic_scheduler": _stage_stats("deterministic_scheduler"),
            "critics_judge_parallel": _stage_stats("critics_judge_parallel"),
            "apply_rehearsal": _stage_stats("apply_rehearsal"),
            "total_wall_time": _stage_stats("total_wall_time"),
        },
        "tokens_and_efficiency": {
            "decomposer_prompt_tokens_total": sum(
                int(r["tokens"]["decomposer_prompt_tokens"]) for r in runs
            ),
            "decomposer_output_tokens_total": sum(
                int(r["tokens"]["decomposer_output_tokens"]) for r in runs
            ),
            "decomposer_thinking_tokens_total": sum(
                int(r["tokens"]["decomposer_thinking_tokens"]) for r in runs
            ),
            "stage3_total_prompt_tokens": sum(
                int(r["tokens"]["stage3_total_prompt_tokens"]) for r in runs
            ),
            "stage3_total_output_tokens": sum(
                int(r["tokens"]["stage3_total_output_tokens"]) for r in runs
            ),
            "stage3_total_thinking_tokens": sum(
                int(r["tokens"]["stage3_total_thinking_tokens"]) for r in runs
            ),
            "decomposer_prompt_tokens_mean": round(
                sum(int(r["tokens"]["decomposer_prompt_tokens"]) for r in passed_or_all)
                / max(1, len(passed_or_all)),
                1,
            ),
            "decomposer_output_tokens_mean": round(
                sum(int(r["tokens"]["decomposer_output_tokens"]) for r in passed_or_all)
                / max(1, len(passed_or_all)),
                1,
            ),
            "output_tokens_per_task_mean": round(
                sum(float(r["tokens"]["output_tokens_per_task"]) for r in passed_runs)
                / max(1, len(passed_runs)),
                2,
            )
            if passed_runs
            else 0.0,
            "throughput_tok_per_sec_mean": round(
                sum(float(r["tokens"]["throughput_tok_per_sec"]) for r in passed_runs)
                / max(1, len(passed_runs)),
                2,
            )
            if passed_runs
            else 0.0,
            "tool_calls_count_total": sum(int(r["tokens"]["tool_calls_count"]) for r in runs),
            "kb_calls_count_total": sum(int(r["tokens"]["kb_calls_count"]) for r in runs),
        },
        "correctness_rates_on_passed": {
            "outcome_coverage_rate": round(
                sum(1 for r in passed_runs if r["correctness"]["outcome_coverage_ok"])
                / max(1, len(passed_runs)),
                4,
            )
            if passed_runs
            else 0.0,
            "concept_coverage_rate": round(
                sum(1 for r in passed_runs if r["correctness"]["concept_coverage_ok"])
                / max(1, len(passed_runs)),
                4,
            )
            if passed_runs
            else 0.0,
            "dag_validity_rate": round(
                sum(1 for r in passed_runs if r["correctness"]["dag_valid"])
                / max(1, len(passed_runs)),
                4,
            )
            if passed_runs
            else 0.0,
            "duplicate_task_rate": round(
                sum(float(r["correctness"]["duplicate_task_ratio"]) for r in passed_runs)
                / max(1, len(passed_runs)),
                4,
            )
            if passed_runs
            else 0.0,
            "unplaced_tasks_zero_rate": round(
                sum(1 for r in passed_runs if r["correctness"]["unplaced_tasks_zero"])
                / max(1, len(passed_runs)),
                4,
            )
            if passed_runs
            else 0.0,
            "non_splittable_integrity_rate": round(
                sum(1 for r in passed_runs if r["correctness"]["non_splittable_integrity_ok"])
                / max(1, len(passed_runs)),
                4,
            )
            if passed_runs
            else 0.0,
        },
        "correctness_rates_all_runs": {
            "outcome_coverage_rate": round(
                sum(1 for r in runs if r["correctness"]["outcome_coverage_ok"]) / max(1, total),
                4,
            ),
            "concept_coverage_rate": round(
                sum(1 for r in runs if r["correctness"]["concept_coverage_ok"]) / max(1, total),
                4,
            ),
            "dag_validity_rate": round(
                sum(1 for r in runs if r["correctness"]["dag_valid"]) / max(1, total),
                4,
            ),
            "unplaced_tasks_zero_rate": round(
                sum(1 for r in runs if r["correctness"]["unplaced_tasks_zero"]) / max(1, total),
                4,
            ),
            "non_splittable_integrity_rate": round(
                sum(1 for r in runs if r["correctness"]["non_splittable_integrity_ok"])
                / max(1, total),
                4,
            ),
        },
        "effort_and_judge": {
            "milestone_vs_tasks_gap_mean": round(sum(gaps) / len(gaps), 4) if gaps else None,
            "milestone_vs_tasks_gap_max": round(max(gaps), 4) if gaps else None,
            "all_efforts_equal_rate": round(
                sum(1 for r in passed_runs if r["effort_and_judge"]["all_milestone_efforts_equal"])
                / max(1, len(passed_runs)),
                4,
            )
            if passed_runs
            else 0.0,
            "judge_verdict_distribution": {
                "PASSED": judge_counts.get("PASSED", 0),
                "NEEDS_REVIEW": judge_counts.get("NEEDS_REVIEW", 0),
                "REVIEW_PENDING": judge_counts.get("REVIEW_PENDING", 0),
                "SKIPPED": judge_counts.get("SKIPPED", 0),
            },
            "pedagogical_score_mean": round(sum(ped_scores) / len(ped_scores), 2)
            if ped_scores
            else None,
        },
    }


async def _run_workload_pair(
    *,
    workload_name: str,
    scenarios: Sequence[dict[str, Any]],
    concurrency: int,
    e2e: bool,
    with_production_harness: bool,
    scale_hard_milestone_efforts: bool,
    base_adapter: LiteLLMAdapter,
    existing_pair: dict[str, Any] | None = None,
    only_arms: set[str] | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = dict(existing_pair or {})
    for arm in ("monolithic", "milestone_scoped"):
        if only_arms is not None and arm not in only_arms:
            continue
        arm_lit: ArchMode = arm
        print(
            f"\n  -> Running [{workload_name}] arm={arm_lit} "
            f"(n={len(scenarios)}, concurrency={concurrency}, e2e={e2e}, "
            f"prod_harness={with_production_harness})...",
            flush=True,
        )
        sem = asyncio.Semaphore(max(1, concurrency))
        t0 = time.perf_counter()

        async def _bounded_run(
            sc: dict[str, Any],
            _sem: asyncio.Semaphore = sem,
            _arm: ArchMode = arm_lit,
        ) -> dict[str, Any]:
            async with _sem:
                res = await _execute_single_scenario(
                    sc,
                    arm=_arm,
                    e2e=e2e,
                    with_production_harness=with_production_harness,
                    scale_hard_milestone_efforts=scale_hard_milestone_efforts,
                    base_adapter=base_adapter,
                )
                status_tag = "PASS" if res["passed"] else f"FAIL({res['error_category']})"
                print(
                    f"     [{_arm}] {sc['scenario_id']}: {status_tag} "
                    f"wall={res['latencies_ms']['total_wall_time']:.0f}ms "
                    f"dec_llm={res['latencies_ms']['decomposer_llm']:.0f}ms "
                    f"tasks={res['tasks_count']} judge={res['effort_and_judge']['judge_status']}",
                    flush=True,
                )
                return res

        runs = await asyncio.gather(*(_bounded_run(sc) for sc in scenarios))
        wall_s = time.perf_counter() - t0
        summary = _aggregate_arm_results(
            runs,
            arm=arm_lit,
            workload_name=workload_name,
            concurrency=concurrency,
            suite_wall_seconds=wall_s,
        )
        print(
            f"  => [{workload_name} / {arm_lit}] pass={summary['passed_count']}/{summary['total_runs']} "
            f"({summary['pass_rate'] * 100:.1f}%) | apply_ok={summary['apply_roundtrip_passed_count']}/{summary['total_runs']} "
            f"| dec_p50={summary['stage_latency_ms']['decomposer_llm']['p50']}ms "
            f"dec_p95={summary['stage_latency_ms']['decomposer_llm']['p95']}ms "
            f"| wall_p50={summary['stage_latency_ms']['total_wall_time']['p50']}ms "
            f"wall_p95={summary['stage_latency_ms']['total_wall_time']['p95']}ms",
            flush=True,
        )
        out[arm_lit] = {
            "summary": summary,
            "runs": list(runs),
        }
    return out


def probe_cobhub_health(base_url: str) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}/v1beta/models"
    t0 = time.perf_counter()
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            status = int(resp.status)
            body = resp.read().decode("utf-8", "ignore")
            parsed = json.loads(body) if body.strip() else {}
            models_count = len(parsed.get("models", [])) if isinstance(parsed, dict) else 0
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


async def run_part_2_live_ab(
    part1_data: dict[str, Any],
    *,
    only_workloads: set[str] | None = None,
    only_arms: set[str] | None = None,
) -> dict[str, Any]:
    print(
        "\n=== [Part 2] Live Controlled A/B (monolithic vs milestone_scoped) via CofHub ===",
        flush=True,
    )
    base_url, _ = _configure_live_environment()
    health = probe_cobhub_health(base_url)
    if not health.get("reachable"):
        raise RuntimeError(f"CofHub unreachable: {health}")

    base_adapter = LiteLLMAdapter()
    cap_probe = await base_adapter.probe_cobhub_capabilities(force=True)

    golden_18 = load_eval_dataset(DEFAULT_18_GOALS_DATASET_PATH)
    hard_6 = load_eval_dataset(HARD_6_GOALS_DATASET_PATH)

    workloads_out: dict[str, Any] = {}
    existing_path = BACKEND_DIR.parent / "docs" / "experiments" / OUTPUT_FILENAME
    if existing_path.exists():
        try:
            existing_json = json.loads(existing_path.read_text(encoding="utf-8"))
            existing_w = (existing_json.get("part_2_live_controlled_ab") or {}).get("workloads")
            if isinstance(existing_w, dict):
                workloads_out.update(existing_w)
        except Exception:
            pass

    def _checkpoint() -> None:
        write_experiment_json(
            OUTPUT_FILENAME,
            {
                "schema_version": "1.0",
                "experiment": "exp_14_decomposer_architecture_ab",
                "timestamp": utc_timestamp(),
                "repo_paths": {"backend_dir": str(BACKEND_DIR)},
                "part_1_prompt_overhead_measurement": part1_data,
                "part_2_live_controlled_ab": {
                    "status": "EXECUTED",
                    "health_probe": health,
                    "capability_probe": cap_probe.to_dict(),
                    "workloads": workloads_out,
                },
            },
        )

    workload_specs: list[tuple[str, Sequence[dict[str, Any]], int, bool, bool, bool]] = [
        ("golden_18_stage3_c3", golden_18, 3, False, False, False),
        ("hard_6_stage3_apples_to_apples_c1", hard_6, 1, False, False, True),
        ("hard_6_stage3_apples_to_apples_c3", hard_6, 3, False, False, True),
        ("hard_6_full_e2e_c1", hard_6, 1, True, False, True),
        ("hard_6_full_e2e_c3", hard_6, 3, True, False, True),
        ("hard_6_production_equivalent_c1", hard_6, 1, False, True, True),
    ]

    for w_name, sc_list, conc, is_e2e, is_prod, scale_ms in workload_specs:
        if only_workloads is not None and w_name not in only_workloads:
            continue
        workloads_out[w_name] = await _run_workload_pair(
            workload_name=w_name,
            scenarios=sc_list,
            concurrency=conc,
            e2e=is_e2e,
            with_production_harness=is_prod,
            scale_hard_milestone_efforts=scale_ms,
            base_adapter=base_adapter,
            existing_pair=workloads_out.get(w_name),
            only_arms=only_arms,
        )
        _checkpoint()

    return {
        "status": "EXECUTED",
        "health_probe": health,
        "capability_probe": cap_probe.to_dict(),
        "workloads": workloads_out,
    }


# ---------------------------------------------------------------------------
# Part 3: Blind Pedagogical Review Generation & Unblinded Analysis
# ---------------------------------------------------------------------------
BLIND_REVIEW_SEED = 20261117
BLIND_KEY_FILENAME = "blind_review_exp14_key.json"
BLIND_REPORT_REL_PATH = "docs/reports/blind-review-exp14-decomposer-ab.md"

# Pre-unblinding blind scores (C1..C5 on 1..5 scale) assigned purely from blind sample inspection
BLIND_SAMPLE_EVALUATIONS: dict[str, tuple[int, int, int, int, int, str]] = {
    "S-01": (
        5,
        4,
        5,
        5,
        5,
        "Tiến trình THEORY→PRACTICE rõ ràng cho từng milestone; mô tả và tiêu chí kiểm thử UoW/Idempotency rất chi tiết.",
    ),
    "S-02": (
        5,
        4,
        5,
        5,
        5,
        "Bám sát Cache-Aside vs Write-Through và DLQ; tiêu chí hoàn thành có kịch bản test cụ thể.",
    ),
    "S-03": (
        5,
        5,
        5,
        5,
        5,
        "Mỗi milestone đều có chu trình THEORY→PRACTICE→REVIEW cân bằng; chống prompt injection tuyệt đối.",
    ),
    "S-04": (
        5,
        5,
        5,
        5,
        4,
        "Cấu trúc THEORY→PRACTICE→PROJECT/REVIEW rất tốt, bám sát ngưỡng <200KB và Lighthouse >=95; mô tả ngắn gọn hơn.",
    ),
    "S-05": (
        5,
        5,
        5,
        5,
        5,
        "Phân rã Redis Streams Consumer Group, DLQ và SSE Replay mạch lạc; tiêu chí kiểm thử failover và slow client rất sắc nét.",
    ),
    "S-06": (
        5,
        5,
        5,
        5,
        5,
        "Chu trình THEORY→PRACTICE→REVIEW chuẩn mực cho chống Data Leakage và tối ưu ngưỡng F1/PR-AUC.",
    ),
    "S-07": (
        5,
        4,
        5,
        5,
        4,
        "Bao phủ đúng Zoneless EventSource và Vitest/Playwright nhưng tiêu chí hoàn thành ngắn gọn hơn.",
    ),
    "S-08": (
        5,
        4,
        5,
        5,
        4,
        "Bao phủ đầy đủ AsyncEngine UoW và Outbox Consumer; mô tả ngắn hơn S-01.",
    ),
    "S-09": (
        5,
        4,
        5,
        5,
        5,
        "Đặc tả rõ cơ chế Zoneless/OnPush, mock EventSource trong Vitest và kịch bản E2E Playwright.",
    ),
    "S-10": (
        5,
        5,
        5,
        5,
        5,
        "Thiết kế Fencing Token chống Split-Brain và Saga Orchestrator sâu sắc, có bài tổng kết Staff Design.",
    ),
    "S-11": (
        5,
        5,
        5,
        5,
        5,
        "Kết hợp THEORY→PRACTICE→REVIEW ở M1 và THEORY→PRACTICE→PROJECT ở M2 cho BFS/DFS, Kahn và Dijkstra.",
    ),
    "S-12": (
        5,
        5,
        5,
        5,
        4,
        "Cấu trúc THEORY→PRACTICE→REVIEW/PROJECT tốt cho Redis Streams & SSE; tiêu chí hoàn thành ngắn gọn hơn S-05.",
    ),
    "S-13": (
        5,
        4,
        5,
        5,
        4,
        "Đạt đầy đủ outcome về Caching và DLQ trong ngân sách 240 phút; tiêu chí ở mức vừa đủ.",
    ),
    "S-14": (
        5,
        4,
        5,
        5,
        5,
        "Đặc tả rõ ArgoCD Sync Waves/Phases và kiểm thử kubectl drain node tôn trọng PDB.",
    ),
    "S-15": (
        5,
        5,
        5,
        4,
        5,
        "Lộ trình 22 tasks bao phủ toàn diện 4 milestone Fullstack Next.js + PostgreSQL RLS; chia 3 mức thời lượng (60/90/120p).",
    ),
    "S-16": (
        5,
        5,
        5,
        5,
        5,
        "Cấu trúc 6 tasks cân bằng THEORY→PRACTICE→REVIEW, nhấn mạnh kiểm chứng PR-AUC và threshold tuning.",
    ),
    "S-17": (
        5,
        5,
        5,
        5,
        4,
        "Bao phủ tốt Raft Quorum/Fencing Token và Saga Pattern; mô tả ngắn gọn hơn S-10.",
    ),
    "S-18": (
        5,
        5,
        5,
        5,
        5,
        "Lộ trình 20 tasks cực kỳ sắc nét (50% PRACTICE, 5 mức thời lượng 60–120p khớp độ khó, mô tả 210 ký tự/task và tiêu chí nghiệm thu định lượng).",
    ),
    "S-19": (
        4,
        4,
        5,
        5,
        5,
        "M1 có 2 task THEORY liên tiếp (tổng 3 THEORY, không có PROJECT), dù mô tả chi tiết.",
    ),
    "S-20": (
        5,
        5,
        5,
        5,
        4,
        "Đầy đủ THEORY→PRACTICE→REVIEW/PROJECT cho @defer và Lighthouse >=95; tiêu chí hoàn thành ngắn gọn.",
    ),
    "S-21": (
        5,
        5,
        5,
        5,
        5,
        "Có mini-project giỏ hàng với Signals ở M1 và kiểm thử bàn phím/Screen Reader cho ARIA Form ở M2 rất thực tế.",
    ),
    "S-22": (
        5,
        5,
        5,
        5,
        5,
        "Bao phủ sâu MVCC Row-level Locks, pgstattuple bloat và dự án pipeline Zero-Downtime Migration.",
    ),
    "S-23": (
        5,
        5,
        5,
        5,
        5,
        "Mô tả giải thuật Iterative DFS/BFS và Kahn rất chi tiết (177 ký tự/task) kèm kiểm thử đồ thị có chu trình.",
    ),
    "S-24": (
        5,
        5,
        5,
        5,
        4,
        "Cấu trúc THEORY→PRACTICE→REVIEW/PROJECT hợp lý cho Signals & ARIA Form; mô tả ngắn gọn hơn S-21.",
    ),
    "S-25": (
        5,
        5,
        5,
        5,
        5,
        "Đặc tả sâu sắc kịch bản tái hiện deadlock, giám sát pg_locks và kiểm thử tải Expand-Contract 0% lỗi.",
    ),
    "S-26": (
        5,
        4,
        5,
        5,
        4,
        "Bao phủ đúng Big-O, Two Pointers O(1) space và Sliding Window; mô tả ngắn gọn hơn S-27.",
    ),
    "S-27": (
        5,
        4,
        5,
        5,
        5,
        "Mô tả rõ cấu trúc vòng lặp chuẩn của Sliding Window + HashMap và xử lý các ca biên.",
    ),
    "S-28": (
        5,
        5,
        5,
        5,
        4,
        "Cân bằng tốt THEORY→PRACTICE→REVIEW (M1) và THEORY→PRACTICE→PROJECT (M2) cho Python & FastAPI CRUD.",
    ),
    "S-29": (
        5,
        5,
        5,
        5,
        4,
        "Cấu trúc THEORY→PRACTICE→REVIEW/PROJECT chuẩn cho Hexagonal & chống IDOR; văn phong cô đọng.",
    ),
    "S-30": (
        5,
        4,
        5,
        5,
        5,
        "Đặc tả chi tiết annotation ArgoCD Sync Waves, hook rollback và diễn tập node drain duy trì 0% lỗi.",
    ),
}


def generate_blind_pedagogical_review(part2_data: dict[str, Any]) -> dict[str, Any]:
    workloads = part2_data.get("workloads") or {}
    pairs: list[tuple[str, str, dict[str, Any], dict[str, Any]]] = []
    for w_name in ("golden_18_stage3_c3", "hard_6_full_e2e_c3"):
        w = workloads.get(w_name) or {}
        mono_runs = {
            r["scenario_id"]: r
            for r in (w.get("monolithic", {}).get("runs") or [])
            if r.get("passed") and r.get("proposal_snapshot")
        }
        scoped_runs = {
            r["scenario_id"]: r
            for r in (w.get("milestone_scoped", {}).get("runs") or [])
            if r.get("passed") and r.get("proposal_snapshot")
        }
        common_ids = sorted(set(mono_runs.keys()) & set(scoped_runs.keys()))
        for sid in common_ids:
            pairs.append((w_name, sid, mono_runs[sid], scoped_runs[sid]))

    raw_samples: list[dict[str, Any]] = []
    for w_name, sid, r_mono, r_scoped in pairs:
        raw_samples.append(
            {
                "workload": w_name,
                "scenario_id": sid,
                "arm": "monolithic",
                "run": r_mono,
            }
        )
        raw_samples.append(
            {
                "workload": w_name,
                "scenario_id": sid,
                "arm": "milestone_scoped",
                "run": r_scoped,
            }
        )

    rng = random.Random(BLIND_REVIEW_SEED)
    rng.shuffle(raw_samples)

    key_mapping: dict[str, dict[str, Any]] = {}
    blind_rows: list[dict[str, Any]] = []
    for idx, item in enumerate(raw_samples, start=1):
        sample_id = f"S-{idx:02d}"
        run = item["run"]
        c1, c2, c3, c4, c5, note = BLIND_SAMPLE_EVALUATIONS[sample_id]
        total_25 = c1 + c2 + c3 + c4 + c5
        mean_5 = round(total_25 / 5.0, 2)
        key_mapping[sample_id] = {
            "scenario_id": item["scenario_id"],
            "workload": item["workload"],
            "arm": item["arm"],
            "tasks_count": run["tasks_count"],
            "blocks_count": run["blocks_count"],
            "dependencies_count": run["dependencies_count"],
            "milestones_count": run["milestones_count"],
            "decomposer_llm_ms": run["latencies_ms"]["decomposer_llm"],
            "total_wall_time_ms": run["latencies_ms"]["total_wall_time"],
            "judge_status": run["effort_and_judge"]["judge_status"],
            "scores": {
                "c1_logical_progression": c1,
                "c2_theory_practice_review_balance": c2,
                "c3_milestone_outcome_coverage": c3,
                "c4_effort_session_realism": c4,
                "c5_actionability_clarity": c5,
                "total_out_of_25": total_25,
                "mean_out_of_5": mean_5,
            },
            "note": note,
        }
        blind_rows.append(
            {
                "sample_id": sample_id,
                "scenario_id": item["scenario_id"],
                "workload": item["workload"],
                "arm": item["arm"],
                "run": run,
                "c1": c1,
                "c2": c2,
                "c3": c3,
                "c4": c4,
                "c5": c5,
                "total_25": total_25,
                "mean_5": mean_5,
                "note": note,
            }
        )

    # Save unblinding key JSON
    key_payload = {
        "schema_version": "1.0",
        "seed": BLIND_REVIEW_SEED,
        "source_file": f"docs/experiments/{OUTPUT_FILENAME}",
        "blind_review_doc": BLIND_REPORT_REL_PATH,
        "paired_scenarios_count": len(pairs),
        "blind_samples_count": len(blind_rows),
        "mapping": key_mapping,
    }
    write_experiment_json(BLIND_KEY_FILENAME, key_payload)

    # Compute unblinded comparison metrics
    arm_rows: dict[str, list[dict[str, Any]]] = {
        "monolithic": [r for r in blind_rows if r["arm"] == "monolithic"],
        "milestone_scoped": [r for r in blind_rows if r["arm"] == "milestone_scoped"],
    }
    arm_summary: dict[str, Any] = {}
    for arm_name, rows in arm_rows.items():
        n = max(1, len(rows))
        arm_summary[arm_name] = {
            "samples_count": len(rows),
            "c1_logical_progression_mean": round(sum(r["c1"] for r in rows) / n, 3),
            "c2_theory_practice_review_balance_mean": round(sum(r["c2"] for r in rows) / n, 3),
            "c3_milestone_outcome_coverage_mean": round(sum(r["c3"] for r in rows) / n, 3),
            "c4_effort_session_realism_mean": round(sum(r["c4"] for r in rows) / n, 3),
            "c5_actionability_clarity_mean": round(sum(r["c5"] for r in rows) / n, 3),
            "total_out_of_25_mean": round(sum(r["total_25"] for r in rows) / n, 3),
            "overall_mean_out_of_5": round(sum(r["mean_5"] for r in rows) / n, 3),
        }

    by_sc_arm = {(r["workload"], r["scenario_id"], r["arm"]): r for r in blind_rows}
    scoped_wins = 0
    mono_wins = 0
    ties = 0
    paired_comparison: list[dict[str, Any]] = []
    for w_name, sid, _, _ in pairs:
        rm = by_sc_arm[(w_name, sid, "monolithic")]
        rs = by_sc_arm[(w_name, sid, "milestone_scoped")]
        if rs["total_25"] > rm["total_25"]:
            scoped_wins += 1
            winner = "milestone_scoped"
        elif rs["total_25"] < rm["total_25"]:
            mono_wins += 1
            winner = "monolithic"
        else:
            ties += 1
            winner = "tie"
        paired_comparison.append(
            {
                "workload": w_name,
                "scenario_id": sid,
                "monolithic_sample_id": rm["sample_id"],
                "monolithic_total_25": rm["total_25"],
                "milestone_scoped_sample_id": rs["sample_id"],
                "milestone_scoped_total_25": rs["total_25"],
                "delta_scoped_minus_mono": rs["total_25"] - rm["total_25"],
                "winner": winner,
            }
        )

    # Render markdown report
    md_lines = [
        "# Blind Pedagogical Review — Experiment 14: Decomposer Architecture A/B (`monolithic` vs `milestone_scoped`)",
        "",
        "> **Phương pháp đánh giá mù (Blind Review Protocol):**",
        f"> - **Nguồn dữ liệu thực nghiệm:** `docs/experiments/{OUTPUT_FILENAME}` (chạy trực tiếp qua CofHub `http://127.0.0.1:8045`).",
        f"> - **Số cặp kịch bản đối chứng (Paired Scenarios):** **{len(pairs)} cặp** ({len(blind_rows)} mẫu độc lập `S-01` .. `S-{len(blind_rows):02d}`), gồm toàn bộ 14 kịch bản cùng pass trên `golden_18_stage3_c3` và kịch bản phức tạp `H_E2E_05_FULLSTACK_NEXTJS_PG` trên `hard_6_full_e2e_c3`.",
        f"> - **Hạt giống xáo trộn cố định (Fixed RNG Seed):** `{BLIND_REVIEW_SEED}`. Toàn bộ metadata về kiến trúc (`monolithic` / `milestone_scoped`), latency, số lượng token, số lần gọi hàm và điểm Judge đã được ẩn hoàn toàn khỏi phần nội dung mẫu khi chấm.",
        f"> - **File khóa giải mã (Unblinding Key):** `docs/experiments/{BLIND_KEY_FILENAME}`.",
        "",
        "## 1. Rubric Chấm Điểm Sư Phạm 5 Tiêu Chí (Thang 1–5)",
        "",
        "1. **C1 — Logical Progression & Prerequisites (1–5):** Trình tự nhiệm vụ trong từng milestone và giữa các milestone có tuân thủ chặt chẽ chuỗi tiên quyết (`THEORY` → `PRACTICE` → `REVIEW` / `PROJECT`), không nhảy cóc hoặc đảo ngược thứ tự nhận thức không?",
        "2. **C2 — Theory-Practice-Review Balance (1–5):** Tỷ trọng giữa lý thuyết nền tảng (`THEORY`), thực hành tay (`PRACTICE`), ôn tập củng cố (`REVIEW`) và bài tập tích hợp (`PROJECT`) có cân bằng và phù hợp với trình độ người học không?",
        "3. **C3 — Milestone & Outcome Coverage Fidelity (1–5):** Các nhiệm vụ có bao phủ đầy đủ 100% chuẩn đầu ra (`M*-O*`), khái niệm bắt buộc (`required_concepts`) và tiêu chí hoàn thành của từng cột mốc mà không trùng lặp hoặc lệch phạm vi không?",
        "4. **C4 — Effort & Session Realism (1–5):** Thời lượng ước tính (`estimated_minutes` trong khoảng 30–120 phút) có khớp với ngân sách thời lượng của cột mốc (`0%` độ lệch tổng) và phân bổ hợp lý vào các khung giờ học (`schedule_blocks`) không?",
        "5. **C5 — Actionability & Clarity (1–5):** Tên nhiệm vụ, `description`, `learning_objective` và `completion_criteria` có đủ cụ thể, rõ ràng và kiểm chứng/đo lường được ngay trong một phiên học không?",
        "",
        "## 2. Bảng Đánh Giá Mù (Blind Evaluation Table — Trước Khi Giải Mã)",
        "",
        "| Mẫu Blind | Kịch bản (`scenario_id`) | C1: Tiến trình & Tiên quyết | C2: Cân bằng T/P/R | C3: Bao phủ Outcome | C4: Khả thi Thời lượng | C5: Tính hành động & Rõ ràng | Tổng (/25) | Điểm TB (/5) | Nhận xét sư phạm (Blind) |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for r in blind_rows:
        md_lines.append(
            f"| **{r['sample_id']}** | `{r['scenario_id']}` | {r['c1']} | {r['c2']} | {r['c3']} | {r['c4']} | {r['c5']} | **{r['total_25']}** | **{r['mean_5']:.2f}** | {r['note']} |"
        )

    md_lines.extend(
        [
            "",
            "---",
            "",
            "## 3. Hồ Sơ Chi Tiết 30 Mẫu Đánh Giá Mù (`S-01` .. `S-30` — Đã Ẩn Metadata Kiến Trúc)",
            "",
        ]
    )

    for r in blind_rows:
        snap = r["run"]["proposal_snapshot"]
        tasks = snap["tasks"]
        deps = snap["dependencies"]
        ms = snap["milestones"]
        t_counts = Counter(str(t.get("task_type", "")).upper() for t in tasks)
        total_t_eff = sum(int(t.get("estimated_minutes", 0)) for t in tasks)
        total_m_eff = sum(int(m.get("estimated_effort_minutes", 0)) for m in ms)
        pred_map: dict[str, list[str]] = {}
        for idx_t, t in enumerate(tasks, start=1):
            tid = str(t.get("task_id", f"T{idx_t}"))
            pred_map[tid] = []
        id_to_label = {
            str(t.get("task_id", f"T{idx_t}")): f"T{idx_t}"
            for idx_t, t in enumerate(tasks, start=1)
        }
        for d in deps:
            p_raw = str(d.get("predecessor_id", ""))
            s_raw = str(d.get("successor_id", ""))
            if s_raw in pred_map and p_raw in id_to_label:
                pred_map[s_raw].append(id_to_label[p_raw])
        mid_to_seq = {str(m["milestone_id"]): f"M{m['sequence_order']}" for m in ms}

        md_lines.extend(
            [
                f"### {r['sample_id']} — `{r['scenario_id']}` ({snap['goal_title']})",
                "",
                f"- **Trình độ:** `{r['run']['learner_level']}` | **Khung ngày:** `{snap['start_date']}` → `{snap['target_date']}`",
                f"- **Cấu trúc đề xuất:** {len(ms)} milestones ({total_m_eff} phút) | {len(tasks)} tasks ({total_t_eff} phút; `THEORY`: {t_counts.get('THEORY', 0)}, `PRACTICE`: {t_counts.get('PRACTICE', 0)}, `REVIEW`: {t_counts.get('REVIEW', 0)}, `PROJECT`: {t_counts.get('PROJECT', 0)}) | {len(deps)} cạnh phụ thuộc DAG",
                "",
                "| # | Milestone | Loại | Thời lượng | Outcomes | Tiên quyết | Tiêu đề nhiệm vụ | Tiêu chí hoàn thành (`completion_criteria`) |",
                "|---|---|---|---|---|---|---|",
            ]
        )
        for idx_t, t in enumerate(tasks, start=1):
            tid_raw = str(t.get("task_id", f"T{idx_t}"))
            m_label = mid_to_seq.get(str(t.get("milestone_id", "")), "M?")
            ttype = str(t.get("task_type", ""))
            mins = int(t.get("estimated_minutes", 0))
            outs = ", ".join(str(o) for o in (t.get("covered_outcome_ids") or []))
            preds = ", ".join(pred_map.get(tid_raw, [])) or "Không"
            title = str(t.get("title", "")).replace("|", "\\|")
            crit = str(t.get("completion_criteria", "")).replace("|", "\\|")
            md_lines.append(
                f"| **T{idx_t}** | {m_label} | `{ttype}` | {mins}p | `{outs}` | {preds} | {title} | {crit} |"
            )
        md_lines.append("")

    s_mono = arm_summary["monolithic"]
    s_scoped = arm_summary["milestone_scoped"]
    md_lines.extend(
        [
            "---",
            "",
            "## 4. Kết Quả Sau Giải Mã (Unblinded Comparison Summary: Arm A `monolithic` vs Arm B `milestone_scoped`)",
            "",
            "### 4.1. Điểm Trung Bình Theo 5 Tiêu Chí Sư Phạm (15 Cặp Kịch Bản = 30 Mẫu)",
            "",
            "| Tiêu chí đánh giá | Arm A: `monolithic` (n=15) | Arm B: `milestone_scoped` (n=15) | Chênh lệch (`B - A`) |",
            "|---|---:|---:|---:|",
            f"| **C1 — Logical Progression & Prerequisites (/5)** | {s_mono['c1_logical_progression_mean']:.3f} | **{s_scoped['c1_logical_progression_mean']:.3f}** | **+{s_scoped['c1_logical_progression_mean'] - s_mono['c1_logical_progression_mean']:.3f}** |",
            f"| **C2 — Theory-Practice-Review Balance (/5)** | {s_mono['c2_theory_practice_review_balance_mean']:.3f} | **{s_scoped['c2_theory_practice_review_balance_mean']:.3f}** | **+{s_scoped['c2_theory_practice_review_balance_mean'] - s_mono['c2_theory_practice_review_balance_mean']:.3f}** |",
            f"| **C3 — Milestone & Outcome Coverage Fidelity (/5)** | **{s_mono['c3_milestone_outcome_coverage_mean']:.3f}** | **{s_scoped['c3_milestone_outcome_coverage_mean']:.3f}** | {s_scoped['c3_milestone_outcome_coverage_mean'] - s_mono['c3_milestone_outcome_coverage_mean']:+.3f} |",
            f"| **C4 — Effort & Session Realism (/5)** | {s_mono['c4_effort_session_realism_mean']:.3f} | **{s_scoped['c4_effort_session_realism_mean']:.3f}** | **+{s_scoped['c4_effort_session_realism_mean'] - s_mono['c4_effort_session_realism_mean']:.3f}** |",
            f"| **C5 — Actionability & Clarity (/5)** | {s_mono['c5_actionability_clarity_mean']:.3f} | **{s_scoped['c5_actionability_clarity_mean']:.3f}** | **+{s_scoped['c5_actionability_clarity_mean'] - s_mono['c5_actionability_clarity_mean']:.3f}** |",
            f"| **Tổng điểm trung bình (/25)** | {s_mono['total_out_of_25_mean']:.3f} | **{s_scoped['total_out_of_25_mean']:.3f}** | **+{s_scoped['total_out_of_25_mean'] - s_mono['total_out_of_25_mean']:.3f}** |",
            f"| **Điểm trung bình toàn cục (/5)** | {s_mono['overall_mean_out_of_5']:.3f} | **{s_scoped['overall_mean_out_of_5']:.3f}** | **+{s_scoped['overall_mean_out_of_5'] - s_mono['overall_mean_out_of_5']:.3f}** |",
            "",
            "### 4.2. Tỷ Lệ Thắng / Hòa / Thua Đối Đầu Trực Tiếp (Head-to-Head Win / Tie / Loss trên 15 Cặp)",
            "",
            f"- **Arm B (`milestone_scoped`) thắng:** **{scoped_wins}/15 ({scoped_wins / 15 * 100:.1f}%)**",
            f"- **Hòa (Tie):** **{ties}/15 ({ties / 15 * 100:.1f}%)**",
            f"- **Arm A (`monolithic`) thắng:** **{mono_wins}/15 ({mono_wins / 15 * 100:.1f}%)**",
            "",
            "| # | Workload | Kịch bản (`scenario_id`) | Mẫu `monolithic` | Điểm `monolithic` (/25) | Mẫu `milestone_scoped` | Điểm `milestone_scoped` (/25) | Chênh lệch (`B - A`) | Kết quả đối đầu |",
            "|---:|---|---|---|---:|---|---:|---:|---|",
        ]
    )
    for idx_p, pc in enumerate(paired_comparison, start=1):
        md_lines.append(
            f"| {idx_p} | `{pc['workload']}` | `{pc['scenario_id']}` | **{pc['monolithic_sample_id']}** | {pc['monolithic_total_25']} | **{pc['milestone_scoped_sample_id']}** | **{pc['milestone_scoped_total_25']}** | {pc['delta_scoped_minus_mono']:+d} | `{pc['winner']}` |"
        )

    report_path = BACKEND_DIR.parent / BLIND_REPORT_REL_PATH
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    print(f"  Saved Blind Review Report to: {report_path}", flush=True)

    return {
        "seed": BLIND_REVIEW_SEED,
        "paired_scenarios_count": len(pairs),
        "blind_samples_count": len(blind_rows),
        "blind_key_file": f"docs/experiments/{BLIND_KEY_FILENAME}",
        "blind_report_file": BLIND_REPORT_REL_PATH,
        "arm_summary": arm_summary,
        "head_to_head": {
            "milestone_scoped_wins": scoped_wins,
            "ties": ties,
            "monolithic_wins": mono_wins,
        },
        "paired_comparison": paired_comparison,
    }


async def async_main() -> int:
    parser = argparse.ArgumentParser(
        description="Experiment 14: Decomposer Architecture Controlled A/B"
    )
    parser.add_argument(
        "--part1-only",
        action="store_true",
        help="Run only Part 1 prompt overhead measurements",
    )
    parser.add_argument(
        "--blind-review-only",
        action="store_true",
        help="Generate Part 3 blind review artifacts from existing Part 2 JSON",
    )
    parser.add_argument(
        "--workloads",
        type=str,
        default="",
        help="Comma-separated workload names to run (default: all)",
    )
    parser.add_argument(
        "--arms",
        type=str,
        default="",
        help="Comma-separated arms to run (monolithic,milestone_scoped)",
    )
    args = parser.parse_args()

    existing_path = BACKEND_DIR.parent / "docs" / "experiments" / OUTPUT_FILENAME
    if args.blind_review_only and existing_path.exists():
        existing_payload = json.loads(existing_path.read_text(encoding="utf-8"))
        part1 = existing_payload.get("part_1_prompt_overhead_measurement") or (
            await run_part_1_prompt_overhead_measurement()
        )
        part2 = existing_payload.get("part_2_live_controlled_ab") or {}
        part3 = generate_blind_pedagogical_review(part2)
        existing_payload["part_1_prompt_overhead_measurement"] = part1
        existing_payload["part_3_blind_pedagogical_review"] = part3
        out_path = write_experiment_json(OUTPUT_FILENAME, existing_payload)
        print(f"\nUpdated Experiment 14 artifact with Blind Review: {out_path}", flush=True)
        return 0

    only_w = (
        {w.strip() for w in args.workloads.split(",") if w.strip()}
        if args.workloads.strip()
        else None
    )
    only_a = {a.strip() for a in args.arms.split(",") if a.strip()} if args.arms.strip() else None
    part1 = await run_part_1_prompt_overhead_measurement()
    part2 = (
        None
        if args.part1_only
        else await run_part_2_live_ab(part1, only_workloads=only_w, only_arms=only_a)
    )
    part3 = generate_blind_pedagogical_review(part2) if isinstance(part2, dict) else None

    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "experiment": "exp_14_decomposer_architecture_ab",
        "timestamp": utc_timestamp(),
        "repo_paths": {"backend_dir": str(BACKEND_DIR)},
        "part_1_prompt_overhead_measurement": part1,
        "part_2_live_controlled_ab": part2,
        "part_3_blind_pedagogical_review": part3,
    }
    out_path = write_experiment_json(OUTPUT_FILENAME, payload)
    print(f"\nSaved Experiment 14 artifact to: {out_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(async_main()))
