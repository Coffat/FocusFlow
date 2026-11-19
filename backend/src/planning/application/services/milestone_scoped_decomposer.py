"""Milestone-Scoped Task Decomposer Prototype (PR-E Step 1)."""

from __future__ import annotations

import asyncio
import hashlib
import heapq
import json
import logging
import math
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID, uuid4

from src.planning.application.dtos.planning_dtos import TaskProposalLLMOutput
from src.planning.application.ports.knowledge_base_port import KnowledgeBasePort
from src.planning.application.ports.knowledge_source_repository_port import (
    KnowledgeSourceRepositoryPort,
)
from src.planning.application.ports.milestone_checkpoint_port import (
    InMemoryMilestoneCheckpointStore,
    MilestoneCheckpointStorePort,
    MilestoneDecompositionOutcome,
)
from src.planning.application.services.learning_quality import (
    assess_schedule_feasibility,
    has_operational_quality_review_failure,
    resolve_task_resources_from_tool_results,
    run_dual_quality_critics,
    validate_task_coverage,
)
from src.planning.application.services.learning_resource_discovery import (
    discover_curated_official_resources,
    knowledge_source_to_learning_resource,
    tokenize_meaningful_terms,
    verify_official_url_live,
)
from src.planning.application.services.roadmap_context_builder import (
    RoadmapContextBuilder,
)
from src.planning.application.services.roadmap_skills import (
    TASK_DECOMPOSER_SKILL,
    build_planning_prompt_registry,
    build_task_decomposer_prompt,
)
from src.planning.application.services.validation_gate.orchestrator import (
    ProposalValidationGateOrchestrator,
    ValidationGateResultDTO,
)
from src.planning.application.services.validation_gate.tier1_schema import (
    _safe_minutes,
    run_tier1_gate,
)
from src.planning.application.services.validation_gate.tier3_judge import (
    Tier3JudgeOutcome,
    execute_tier3_pedagogical_judge,
)
from src.planning.domain.exceptions.planning_exceptions import (
    PlanInfeasibleError,
    ProposalValidationGateError,
)
from src.planning.domain.models.goal import Goal
from src.planning.domain.models.knowledge_concept import LearningResource
from src.planning.domain.models.knowledge_source import (
    KnowledgeIngestionStatus,
    KnowledgeSource,
)
from src.planning.domain.models.milestone import Milestone
from src.planning.domain.models.roadmap import Roadmap
from src.planning.domain.services.spatio_temporal_engine import SpatioTemporalRuleEngine
from src.planning.domain.services.validation_types import (
    AvailabilityConfigurationDTO,
    ConstraintViolationDTO,
    ScheduleCompletenessStatus,
    classify_schedule_completeness,
    safe_parse_iso_date,
    safe_parse_iso_datetime,
)
from src.shared_kernel.application.harness.execution_manager import AIExecutionManager
from src.shared_kernel.application.harness.models import (
    WorkflowRun,
    WorkflowStepExecution,
    WorkflowType,
)
from src.shared_kernel.application.harness.untrusted_context import (
    UntrustedBlockKind,
    format_untrusted_block,
    sanitize_untrusted_text,
)
from src.shared_kernel.application.harness.workflow_port import (
    BufferedWorkflowRepo,
    WorkflowRepositoryPort,
)
from src.shared_kernel.application.llm_port import LLMProviderPort
from src.shared_kernel.config import get_settings

logger = logging.getLogger(__name__)

_SCHEDULE_FIELDS = frozenset(
    {"scheduled_date", "scheduled_start", "scheduled_end", "start_time", "end_time"}
)


@dataclass(frozen=True, slots=True)
class ReconciledGlobalProposal:
    """Merged global tasks, deterministic T1..TN IDs, and cross-milestone prerequisite DAG."""

    tasks: list[dict[str, Any]]
    dependencies: list[dict[str, Any]]
    namespace_map: dict[tuple[int, str], str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class MilestoneSubjobProgress:
    """Progress emitted after one logical milestone subjob completes successfully."""

    milestone_sequence: int
    completed_count: int
    total_count: int
    from_checkpoint: bool


def calculate_dynamic_subjob_concurrency(milestone_count: int, *, ceiling: int) -> int:
    """Return a bounded worker count that keeps milestone fan-out to at most two waves."""
    if milestone_count <= 0:
        return 0
    dynamic_target = 1 if milestone_count == 1 else max(2, math.ceil(milestone_count / 2))
    return min(milestone_count, dynamic_target, max(1, int(ceiling)))


def calculate_milestone_subjob_timeout(
    *,
    pipeline_remaining_seconds: float,
    attempt_cap_seconds: float,
    finalization_reserve_seconds: float,
) -> float:
    """Protect merge and global validation time from milestone LLM calls."""
    available = pipeline_remaining_seconds - finalization_reserve_seconds
    if available <= 0:
        raise TimeoutError(
            "Milestone subjob cannot start without consuming the proposal finalization budget"
        )
    return min(attempt_cap_seconds, available)


async def run_dynamic_subjob_pool[T, R](
    *,
    items: Sequence[T],
    worker_count: int,
    run_one: Callable[[T], Awaitable[R]],
) -> list[R | BaseException]:
    """Run every item once with work-stealing semantics and ordered results."""
    if not items:
        return []

    queue: asyncio.Queue[tuple[int, T]] = asyncio.Queue()
    for index, item in enumerate(items):
        queue.put_nowait((index, item))

    results: dict[int, R | BaseException] = {}

    async def _worker() -> None:
        while True:
            try:
                index, item = queue.get_nowait()
            except asyncio.QueueEmpty:
                return
            try:
                results[index] = await run_one(item)
            except asyncio.CancelledError:
                raise
            except BaseException as exc:
                results[index] = exc
            finally:
                queue.task_done()

    workers = [
        asyncio.create_task(_worker()) for _ in range(min(len(items), max(1, int(worker_count))))
    ]
    try:
        await asyncio.gather(*workers)
    finally:
        for worker in workers:
            if not worker.done():
                worker.cancel()

    return [results[index] for index in range(len(items))]


def compute_milestone_content_hash(
    milestone: Milestone,
    target_date: date | datetime | str | None = None,
) -> str:
    """Compute deterministic sha256 hash of milestone content.

    Incorporates milestone title, description, estimated_effort_minutes, target_date,
    outcomes (id, description, criteria), and concepts.
    """
    target_date_str = ""
    if isinstance(target_date, (date, datetime)):
        target_date_str = target_date.isoformat()
    elif target_date is not None:
        target_date_str = str(target_date).strip()
    elif getattr(milestone, "target_date", None) is not None:
        m_td = getattr(milestone, "target_date")
        target_date_str = (
            m_td.isoformat() if isinstance(m_td, (date, datetime)) else str(m_td).strip()
        )

    outcomes_canonical: list[dict[str, str]] = []
    for idx, out in enumerate(getattr(milestone, "learning_outcomes", ()) or ()):
        if isinstance(out, dict):
            outcomes_canonical.append(
                {
                    "id": str(out.get("id") or out.get("outcome_id") or f"out_{idx}").strip(),
                    "description": str(
                        out.get("description") or out.get("text") or out.get("title") or ""
                    ).strip(),
                    "criteria": str(
                        out.get("criteria") or out.get("completion_criteria") or ""
                    ).strip(),
                }
            )
        else:
            outcomes_canonical.append(
                {
                    "id": f"out_{idx}",
                    "description": str(out).strip(),
                    "criteria": "",
                }
            )

    req_concepts = sorted(
        str(c).strip()
        for c in (getattr(milestone, "required_concepts", ()) or ())
        if str(c).strip()
    )
    unver_concepts = sorted(
        str(c).strip()
        for c in (getattr(milestone, "unverified_concepts", ()) or ())
        if str(c).strip()
    )
    prereq_ids = sorted(
        str(pid).strip()
        for pid in (getattr(milestone, "prerequisite_milestone_ids", ()) or ())
        if str(pid).strip()
    )

    content_dict = {
        "title": (milestone.title or "").strip(),
        "description": (milestone.description or "").strip(),
        "estimated_effort_minutes": int(milestone.estimated_effort_minutes or 0),
        "target_date": target_date_str,
        "outcomes": outcomes_canonical,
        "completion_criteria": (milestone.completion_criteria or "").strip(),
        "required_concepts": req_concepts,
        "unverified_concepts": unver_concepts,
        "prerequisite_milestone_ids": prereq_ids,
    }
    canonical_json = json.dumps(
        content_dict, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def compute_decomposition_context_fingerprint(
    *,
    milestone: Milestone,
    all_milestones: Sequence[Milestone] = (),
    target_date: date | datetime | str | None = None,
    start_date: date | datetime | str | None = None,
    learner_profile: Any = None,
    prior_knowledge_level: str | None = None,
    clarification_context: str | None = None,
    availability: AvailabilityConfigurationDTO | Any = None,
    prefetched_resources: Sequence[LearningResource | Any] = (),
    knowledge_chunks: Sequence[Any] = (),
    memory_items: Sequence[Any] = (),
    concept_masteries: Sequence[Any] = (),
    prompt_checksum: str = "",
    schema_checksum: str = "",
    model_name: str = "",
) -> str:
    """Compute canonical 7-dimensional SHA-256 fingerprint for milestone task decomposition.

    Dimensions captured:
    1. Milestone Core: milestone.id, title, description, estimated_effort_minutes, target_date,
       outcomes (id, description, criteria), concepts (required/unverified), prerequisite_milestone_ids.
    2. Learner Profile & Goal Clarification: prior_knowledge_level, opt_session_minutes,
       estimation_bias_beta, clarification_context.
    3. Availability & Capacity & Timeline: mode, default_daily_quota_minutes, disabled weekdays, start_date.
    4. RAG / Knowledge Evidence: hash of chunk IDs, text, and prefetched resources.
    5. Learner Memory Items & Concept Masteries: hash of memory IDs & mastery IDs.
    6. Sibling Milestones Outline: hash of all sibling milestones (sequence_order, title, outcomes)
       to capture the [SIBLING_MILESTONES_OUTLINE] block.
    7. Prompt Schema & Model: prompt_checksum, schema_checksum, and stage-resolved model_name.
    """
    target_date_str = ""
    if isinstance(target_date, (date, datetime)):
        target_date_str = target_date.isoformat()
    elif target_date is not None:
        target_date_str = str(target_date).strip()
    elif getattr(milestone, "target_date", None) is not None:
        m_td = getattr(milestone, "target_date")
        target_date_str = (
            m_td.isoformat() if isinstance(m_td, (date, datetime)) else str(m_td).strip()
        )

    start_date_str = ""
    if isinstance(start_date, (date, datetime)):
        start_date_str = start_date.isoformat()
    elif start_date is not None:
        start_date_str = str(start_date).strip()

    outcomes_canonical: list[dict[str, str]] = []
    for idx, out in enumerate(getattr(milestone, "learning_outcomes", ()) or ()):
        if isinstance(out, dict):
            outcomes_canonical.append(
                {
                    "id": str(out.get("id") or out.get("outcome_id") or f"out_{idx}").strip(),
                    "description": str(
                        out.get("description") or out.get("text") or out.get("title") or ""
                    ).strip(),
                    "criteria": str(
                        out.get("criteria") or out.get("completion_criteria") or ""
                    ).strip(),
                }
            )
        else:
            outcomes_canonical.append(
                {
                    "id": f"out_{idx}",
                    "description": str(out).strip(),
                    "criteria": "",
                }
            )

    req_concepts = sorted(
        str(c).strip()
        for c in (getattr(milestone, "required_concepts", ()) or ())
        if str(c).strip()
    )
    unver_concepts = sorted(
        str(c).strip()
        for c in (getattr(milestone, "unverified_concepts", ()) or ())
        if str(c).strip()
    )
    prereq_ids = sorted(
        str(pid).strip()
        for pid in (getattr(milestone, "prerequisite_milestone_ids", ()) or ())
        if str(pid).strip()
    )

    milestone_core = {
        "id": str(milestone.id).strip(),
        "title": (milestone.title or "").strip(),
        "description": (milestone.description or "").strip(),
        "estimated_effort_minutes": int(milestone.estimated_effort_minutes or 0),
        "target_date": target_date_str,
        "outcomes": outcomes_canonical,
        "completion_criteria": (milestone.completion_criteria or "").strip(),
        "required_concepts": req_concepts,
        "unverified_concepts": unver_concepts,
        "prerequisite_milestone_ids": prereq_ids,
    }

    prior_level = (
        str(prior_knowledge_level).strip()
        if prior_knowledge_level is not None
        else str(
            getattr(learner_profile, "prior_knowledge_level", "BEGINNER") or "BEGINNER"
        ).strip()
    )
    opt_session = int(getattr(learner_profile, "opt_session_minutes", 45) or 45)
    bias_beta = float(getattr(learner_profile, "estimation_bias_beta", 1.0) or 1.0)

    clarification_ctx_str = str(clarification_context or "").strip()
    learner_profile_data = {
        "prior_knowledge_level": prior_level,
        "opt_session_minutes": opt_session,
        "estimation_bias_beta": round(bias_beta, 4),
        "clarification_context": clarification_ctx_str,
    }

    avail_mode = str(getattr(availability, "mode", "MODE_A") or "MODE_A").strip()
    default_daily_quota = int(getattr(availability, "default_daily_quota_minutes", 120) or 120)
    raw_disabled = getattr(availability, "disabled_weekdays", ()) or ()
    disabled_weekdays = sorted(str(w).strip().lower() for w in raw_disabled if str(w).strip())

    availability_data = {
        "mode": avail_mode,
        "default_daily_quota_minutes": default_daily_quota,
        "disabled_weekdays": disabled_weekdays,
        "start_date": start_date_str,
    }

    chunks_data: list[dict[str, str]] = []
    for c in knowledge_chunks or ():
        c_id = str(
            getattr(c, "id", None)
            or getattr(c, "chunk_id", None)
            or (c.get("id") if isinstance(c, dict) else "")
            or (c.get("chunk_id") if isinstance(c, dict) else "")
            or ""
        ).strip()
        c_text = str(
            getattr(c, "content", None)
            or getattr(c, "text", None)
            or (c.get("content") if isinstance(c, dict) else "")
            or (c.get("text") if isinstance(c, dict) else "")
            or ""
        ).strip()
        chunks_data.append({"id": c_id, "text": c_text})
    chunks_data.sort(key=lambda x: (x["id"], x["text"]))

    resources_data: list[dict[str, str]] = []
    for r in prefetched_resources or ():
        r_id = str(
            getattr(r, "resource_id", None)
            or (r.get("resource_id") if isinstance(r, dict) else "")
            or ""
        ).strip()
        r_title = str(
            getattr(r, "title", None) or (r.get("title") if isinstance(r, dict) else "") or ""
        ).strip()
        r_url = str(
            getattr(r, "url", None) or (r.get("url") if isinstance(r, dict) else "") or ""
        ).strip()
        r_type = str(
            getattr(r, "type", None) or (r.get("type") if isinstance(r, dict) else "") or ""
        ).strip()
        resources_data.append({"id": r_id, "title": r_title, "url": r_url, "type": r_type})
    resources_data.sort(key=lambda x: (x["id"], x["title"]))

    rag_evidence = {
        "chunks": chunks_data,
        "resources": resources_data,
    }

    memory_ids = sorted(
        str(
            getattr(m, "id", None)
            or getattr(m, "memory_id", None)
            or (m.get("id") if isinstance(m, dict) else "")
            or (m.get("memory_id") if isinstance(m, dict) else "")
            or ""
        ).strip()
        for m in (memory_items or ())
        if str(
            getattr(m, "id", None)
            or getattr(m, "memory_id", None)
            or (m.get("id") if isinstance(m, dict) else "")
            or (m.get("memory_id") if isinstance(m, dict) else "")
            or ""
        ).strip()
    )
    mastery_ids = sorted(
        str(
            getattr(cm, "id", None)
            or getattr(cm, "mastery_id", None)
            or getattr(cm, "concept_id", None)
            or (cm.get("id") if isinstance(cm, dict) else "")
            or (cm.get("mastery_id") if isinstance(cm, dict) else "")
            or (cm.get("concept_id") if isinstance(cm, dict) else "")
            or ""
        ).strip()
        for cm in (concept_masteries or ())
        if str(
            getattr(cm, "id", None)
            or getattr(cm, "mastery_id", None)
            or getattr(cm, "concept_id", None)
            or (cm.get("id") if isinstance(cm, dict) else "")
            or (cm.get("mastery_id") if isinstance(cm, dict) else "")
            or (cm.get("concept_id") if isinstance(cm, dict) else "")
            or ""
        ).strip()
    )

    learner_memory_data = {
        "memory_ids": memory_ids,
        "mastery_ids": mastery_ids,
    }

    siblings_data: list[dict[str, Any]] = []
    for sib in sorted(all_milestones or (), key=lambda x: getattr(x, "sequence_order", 0)):
        if getattr(sib, "id", None) == getattr(milestone, "id", None):
            continue
        outcomes_list = [
            str(out.get("description") or out.get("title") or out).strip()
            if isinstance(out, dict)
            else str(out).strip()
            for out in (getattr(sib, "learning_outcomes", ()) or ())
        ]
        siblings_data.append(
            {
                "sequence_order": int(getattr(sib, "sequence_order", 0)),
                "title": str(getattr(sib, "title", "") or "").strip(),
                "learning_outcomes": outcomes_list,
            }
        )

    effective_schema_checksum = str(schema_checksum or "").strip()
    if not effective_schema_checksum:
        schema_dict = TaskProposalLLMOutput.model_json_schema()
        effective_schema_checksum = hashlib.sha256(
            json.dumps(schema_dict, sort_keys=True).encode("utf-8")
        ).hexdigest()

    prompt_schema_model = {
        "prompt_checksum": str(prompt_checksum or "").strip(),
        "schema_checksum": effective_schema_checksum,
        "model_name": str(model_name or "").strip(),
    }

    fingerprint_dict = {
        "1_milestone_core": milestone_core,
        "2_learner_profile": learner_profile_data,
        "3_availability_capacity": availability_data,
        "4_rag_knowledge_evidence": rag_evidence,
        "5_learner_memory_and_masteries": learner_memory_data,
        "6_sibling_milestones_outline": siblings_data,
        "7_prompt_schema_model": prompt_schema_model,
    }
    canonical_json = json.dumps(
        fingerprint_dict,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def compute_milestone_checkpoint_key(
    *,
    roadmap_id: UUID | str | None = None,
    milestone: Milestone,
    prompt_checksum: str = "",
    model_name: str = "",
    target_date: date | datetime | str | None = None,
    start_date: date | datetime | str | None = None,
    all_milestones: Sequence[Milestone] = (),
    learner_profile: Any = None,
    prior_knowledge_level: str | None = None,
    clarification_context: str | None = None,
    availability: AvailabilityConfigurationDTO | Any = None,
    prefetched_resources: Sequence[LearningResource | Any] = (),
    knowledge_chunks: Sequence[Any] = (),
    memory_items: Sequence[Any] = (),
    concept_masteries: Sequence[Any] = (),
    schema_checksum: str = "",
    context_fingerprint: str | None = None,
) -> str:
    """Construct deterministic SHA-256 checkpoint key for a milestone decomposition.

    Incorporates the roadmap ID, milestone ID, and the 7-dimensional decomposition context fingerprint.
    """
    r_id_str = str(roadmap_id or getattr(milestone, "roadmap_id", "") or "").strip()
    m_id_str = str(milestone.id).strip()
    effective_fingerprint = (
        context_fingerprint
        if context_fingerprint is not None
        else compute_decomposition_context_fingerprint(
            milestone=milestone,
            all_milestones=all_milestones,
            target_date=target_date,
            start_date=start_date,
            learner_profile=learner_profile,
            prior_knowledge_level=prior_knowledge_level,
            clarification_context=clarification_context,
            availability=availability,
            prefetched_resources=prefetched_resources,
            knowledge_chunks=knowledge_chunks,
            memory_items=memory_items,
            concept_masteries=concept_masteries,
            prompt_checksum=prompt_checksum,
            schema_checksum=schema_checksum,
            model_name=model_name,
        )
    )
    raw_key = f"{r_id_str}:{m_id_str}:{effective_fingerprint}"
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def topological_sort_milestones(milestones: Sequence[Milestone]) -> list[Milestone]:
    """Sort milestones topologically by `prerequisite_milestone_ids`, breaking ties by `sequence_order`."""
    if not milestones:
        return []

    by_id: dict[UUID, Milestone] = {m.id: m for m in milestones}
    in_degree: dict[UUID, int] = {m.id: 0 for m in milestones}
    dependents: dict[UUID, list[UUID]] = {m.id: [] for m in milestones}

    for m in milestones:
        seen_preds: set[UUID] = set()
        for raw_pid in getattr(m, "prerequisite_milestone_ids", ()) or ():
            pid = raw_pid if isinstance(raw_pid, UUID) else UUID(str(raw_pid))
            if pid in by_id and pid != m.id and pid not in seen_preds:
                seen_preds.add(pid)
                dependents[pid].append(m.id)
                in_degree[m.id] += 1

    heap: list[tuple[int, str, UUID]] = []
    for m in milestones:
        if in_degree[m.id] == 0:
            heapq.heappush(heap, (m.sequence_order, str(m.id), m.id))

    ordered: list[Milestone] = []
    while heap:
        _, _, mid = heapq.heappop(heap)
        ordered.append(by_id[mid])
        for succ_id in dependents[mid]:
            in_degree[succ_id] -= 1
            if in_degree[succ_id] == 0:
                succ = by_id[succ_id]
                heapq.heappush(heap, (succ.sequence_order, str(succ.id), succ.id))

    if len(ordered) != len(milestones):
        raise ProposalValidationGateError(
            message="Phát hiện chu trình trong prerequisite_milestone_ids của các cột mốc.",
            code="DEPENDENCY_CYCLE_DETECTED",
            violations=[
                {
                    "task_index": None,
                    "field": "prerequisite_milestone_ids",
                    "rule_code": "DEPENDENCY_CYCLE_DETECTED",
                    "expected_bound": "Acyclic milestone prerequisite graph",
                    "actual_value": "Cycle detected",
                    "suggested_fix": "Loại bỏ phụ thuộc vòng giữa các cột mốc.",
                }
            ],
        )
    return ordered


def _select_milestone_sinks(
    tasks: Sequence[dict[str, Any]],
    internal_edges: Sequence[tuple[str, str]],
) -> list[dict[str, Any]]:
    """Select out-degree-0 sink tasks within a milestone, prioritizing PROJECT then REVIEW when unlinked."""
    out_degree: dict[str, int] = {str(t["task_id"]): 0 for t in tasks}
    for pred_id, _ in internal_edges:
        if pred_id in out_degree:
            out_degree[pred_id] += 1
    sinks = [t for t in tasks if out_degree.get(str(t["task_id"]), 0) == 0]
    if not sinks:
        sinks = [tasks[-1]]
    if internal_edges:
        return sinks
    project_sinks = [t for t in sinks if str(t.get("task_type", "")).upper() == "PROJECT"]
    if project_sinks:
        return project_sinks
    review_sinks = [t for t in sinks if str(t.get("task_type", "")).upper() == "REVIEW"]
    if review_sinks:
        return review_sinks
    return sinks


def _select_milestone_sources(
    tasks: Sequence[dict[str, Any]],
    internal_edges: Sequence[tuple[str, str]],
) -> list[dict[str, Any]]:
    """Select in-degree-0 source tasks within a milestone, prioritizing THEORY when unlinked."""
    in_degree: dict[str, int] = {str(t["task_id"]): 0 for t in tasks}
    for _, succ_id in internal_edges:
        if succ_id in in_degree:
            in_degree[succ_id] += 1
    sources = [t for t in tasks if in_degree.get(str(t["task_id"]), 0) == 0]
    if not sources:
        sources = [tasks[0]]
    if internal_edges:
        return sources
    theory_sources = [t for t in sources if str(t.get("task_type", "")).upper() == "THEORY"]
    if theory_sources:
        return theory_sources
    return sources


def reconcile_milestone_proposals(
    sorted_milestones: Sequence[Milestone],
    outcomes_by_milestone_id: dict[UUID, MilestoneDecompositionOutcome],
) -> ReconciledGlobalProposal:
    """Remap per-milestone local IDs to deterministic T1..TN and connect explicit prerequisites."""
    all_tasks: list[dict[str, Any]] = []
    all_deps: list[dict[str, Any]] = []
    seen_edges: set[tuple[str, str]] = set()
    namespace_map: dict[tuple[int, str], str] = {}

    tasks_by_mid: dict[UUID, list[dict[str, Any]]] = {}
    internal_edges_by_mid: dict[UUID, list[tuple[str, str]]] = {}

    global_idx = 1
    for milestone in sorted_milestones:
        outcome = outcomes_by_milestone_id[milestone.id]
        local_to_global: dict[str, str] = {}
        milestone_tasks: list[dict[str, Any]] = []

        for local_idx, raw_task in enumerate(outcome.tasks):
            t_copy = {k: v for k, v in raw_task.items() if k not in _SCHEDULE_FIELDS}
            raw_tid = str(t_copy.get("task_id") or t_copy.get("id") or f"task_{local_idx}").strip()
            global_tid = f"T{global_idx}"
            global_idx += 1

            local_to_global[raw_tid] = global_tid
            local_to_global.setdefault(f"task_{local_idx}", global_tid)
            namespace_map[(milestone.sequence_order, raw_tid)] = global_tid

            t_copy["task_id"] = global_tid
            t_copy["milestone_id"] = str(milestone.id)
            milestone_tasks.append(t_copy)

        internal_edges: list[tuple[str, str]] = []
        for dep in outcome.dependencies:
            pred_raw = str(dep.get("predecessor_id", "")).strip()
            succ_raw = str(dep.get("successor_id", "")).strip()
            pred_global = local_to_global.get(pred_raw)
            succ_global = local_to_global.get(succ_raw)
            if pred_global is None or succ_global is None or pred_global == succ_global:
                continue
            edge = (pred_global, succ_global)
            internal_edges.append(edge)
            if edge not in seen_edges:
                seen_edges.add(edge)
                all_deps.append(
                    {
                        "predecessor_id": pred_global,
                        "successor_id": succ_global,
                        "is_mandatory": bool(dep.get("is_mandatory", True)),
                    }
                )

        for t_copy in milestone_tasks:
            succ_global = str(t_copy["task_id"])
            raw_prereqs = t_copy.get("prerequisite_ids") or t_copy.get("depends_on") or []
            if isinstance(raw_prereqs, list):
                remapped_prereqs: list[str] = []
                for p in raw_prereqs:
                    pred_global = local_to_global.get(str(p).strip())
                    if pred_global is None or pred_global == succ_global:
                        continue
                    remapped_prereqs.append(pred_global)
                    edge = (pred_global, succ_global)
                    internal_edges.append(edge)
                    if edge not in seen_edges:
                        seen_edges.add(edge)
                        all_deps.append(
                            {
                                "predecessor_id": pred_global,
                                "successor_id": succ_global,
                                "is_mandatory": True,
                            }
                        )
                t_copy["prerequisite_ids"] = remapped_prereqs

        tasks_by_mid[milestone.id] = milestone_tasks
        internal_edges_by_mid[milestone.id] = internal_edges
        all_tasks.extend(milestone_tasks)

    # Cross-milestone DAG edges: ONLY from explicit Milestone.prerequisite_milestone_ids.
    milestone_by_id = {m.id: m for m in sorted_milestones}
    for m_succ in sorted_milestones:
        succ_tasks = tasks_by_mid.get(m_succ.id, [])
        if not succ_tasks:
            continue
        succ_sources = _select_milestone_sources(
            succ_tasks, internal_edges_by_mid.get(m_succ.id, [])
        )
        for raw_pid in getattr(m_succ, "prerequisite_milestone_ids", ()) or ():
            pred_id = raw_pid if isinstance(raw_pid, UUID) else UUID(str(raw_pid))
            if pred_id == m_succ.id or pred_id not in milestone_by_id:
                continue
            pred_tasks = tasks_by_mid.get(pred_id, [])
            if not pred_tasks:
                continue
            pred_sinks = _select_milestone_sinks(pred_tasks, internal_edges_by_mid.get(pred_id, []))
            for sink_task in pred_sinks:
                for source_task in succ_sources:
                    edge = (str(sink_task["task_id"]), str(source_task["task_id"]))
                    if edge[0] != edge[1] and edge not in seen_edges:
                        seen_edges.add(edge)
                        all_deps.append(
                            {
                                "predecessor_id": edge[0],
                                "successor_id": edge[1],
                                "is_mandatory": True,
                            }
                        )

    return ReconciledGlobalProposal(
        tasks=all_tasks,
        dependencies=all_deps,
        namespace_map=namespace_map,
    )


class MilestoneScopedTaskDecomposer:
    """Milestone-scoped parallel Task Decomposer with server prefetch & global DAG reconciliation."""

    def __init__(
        self,
        *,
        llm_provider: LLMProviderPort,
        knowledge_base: KnowledgeBasePort | None = None,
        knowledge_source_repo: KnowledgeSourceRepositoryPort | None = None,
        enable_tier3_judge: bool = True,
        tier3_timeout_seconds: float | None = None,
        workflow_repo: WorkflowRepositoryPort | None = None,
        user_id: UUID | None = None,
        goal_id: UUID | None = None,
        roadmap_id: UUID | None = None,
        max_concurrency: int = 4,
        checkpoint_store: MilestoneCheckpointStorePort | None = None,
        quota: Any = None,
        reservation_id: UUID | None = None,
    ) -> None:
        self._llm = llm_provider
        self._kb = knowledge_base
        self._knowledge_source_repo = knowledge_source_repo
        self._enable_tier3_judge = enable_tier3_judge
        self._tier3_timeout_seconds = tier3_timeout_seconds
        self._workflow_repo = workflow_repo
        self._user_id = user_id
        self._goal_id = goal_id
        self._roadmap_id = roadmap_id
        self._max_concurrency = max(1, int(max_concurrency))
        self._checkpoint_store = (
            checkpoint_store if checkpoint_store is not None else InMemoryMilestoneCheckpointStore()
        )
        self._quota = quota
        self._reservation_id = reservation_id
        self._wf_lock = asyncio.Lock()

    async def _prefetch_resources_for_milestones(
        self,
        milestones: Sequence[Milestone],
        *,
        indexed_sources: Sequence[KnowledgeSource] = (),
    ) -> dict[UUID, list[LearningResource]]:
        learner_resources: list[LearningResource] = []
        for src in indexed_sources:
            lr = knowledge_source_to_learning_resource(src)
            if lr is not None:
                learner_resources.append(lr)

        if self._kb is None and not learner_resources:
            return {m.id: [] for m in milestones}

        kb = self._kb
        sem = asyncio.Semaphore(self._max_concurrency)

        async def _fetch_one(milestone: Milestone) -> tuple[UUID, list[LearningResource]]:
            query = " ".join(
                part
                for part in (milestone.title, *milestone.learning_outcomes)
                if isinstance(part, str) and part.strip()
            ).strip()[:200]
            raw: list[LearningResource] = []
            if kb is not None:
                async with sem:
                    try:
                        raw = await kb.get_learning_resources_and_guidance(
                            query=query or None,
                            concept_ids=list(milestone.required_concepts),
                            limit=6,
                        )
                    except asyncio.CancelledError:
                        raise
                    except Exception as exc:
                        logger.warning(
                            "milestone_resource_prefetch_failed",
                            extra={
                                "milestone_id": str(milestone.id),
                                "error_type": type(exc).__name__,
                            },
                        )
                        raw = []

            unverified = tuple(getattr(milestone, "unverified_concepts", ()) or ())
            discovered: list[LearningResource] = []
            if kb is not None and (not raw or bool(unverified)):
                candidates = discover_curated_official_resources(
                    query=query,
                    concept_ids=list(milestone.required_concepts),
                    unverified_concepts=unverified,
                    limit=6,
                )
                for cand in candidates:
                    if await verify_official_url_live(cand.url):
                        discovered.append(cand)

            # Rank learner INDEXED KnowledgeSource materials for this milestone
            m_terms = set(
                tokenize_meaningful_terms(
                    " ".join(
                        [
                            milestone.title or "",
                            *(str(o) for o in (milestone.learning_outcomes or ())),
                            *milestone.required_concepts,
                            *unverified,
                        ]
                    )
                )
            )
            ranked_learner = sorted(
                learner_resources,
                key=lambda lr: (
                    -len(m_terms & set(tokenize_meaningful_terms(f"{lr.title} {lr.description}"))),
                    lr.title,
                ),
            )

            deduped: list[LearningResource] = []
            seen_ids: set[str] = set()
            seen_urls: set[str] = set()
            for item in (*ranked_learner, *raw, *discovered):
                if not item.resource_id or item.resource_id in seen_ids:
                    continue
                if item.url and item.url in seen_urls:
                    continue
                seen_ids.add(item.resource_id)
                if item.url:
                    seen_urls.add(item.url)
                deduped.append(item)
                if len(deduped) >= 8:
                    break
            return milestone.id, deduped

        pairs = await asyncio.gather(*(_fetch_one(m) for m in milestones))
        return dict(pairs)

    @staticmethod
    def _build_milestone_prompt(
        *,
        milestone: Milestone,
        all_milestones: Sequence[Milestone],
        goal: Goal | None,
        roadmap: Roadmap,
        availability: AvailabilityConfigurationDTO,
        learner_profile: Any,
        existing_tasks: Sequence[object],
        prefetched_resources: Sequence[LearningResource],
        harness_suffix: str,
        start_date: date,
        reference_date: date,
    ) -> str:
        target_date_str = roadmap.target_date.isoformat() if roadmap.target_date else "N/A"
        header_markers = (
            "GENERATE_PROPOSAL_TASKS\n"
            f"Start Date: {start_date.isoformat()}\n"
            f"Target Date: {target_date_str}\n"
            f"Availability Mode: {availability.mode}\n"
            f"MILESTONE_IDS: [{milestone.id}]"
        )

        sibling_outline = [
            {
                "sequence_order": sib.sequence_order,
                "title": sanitize_untrusted_text(sib.title),
                "learning_outcomes": [
                    sanitize_untrusted_text(out) for out in sib.learning_outcomes
                ],
            }
            for sib in sorted(all_milestones, key=lambda item: item.sequence_order)
            if sib.id != milestone.id
        ]
        sibling_block = (
            "[SIBLING_MILESTONES_OUTLINE]\n"
            "Chỉ phân rã milestone mục tiêu; tránh lặp lại chủ đề của các cột mốc anh em:\n"
            + json.dumps(sibling_outline, ensure_ascii=False)
        )

        milestone_effort = max(30, int(getattr(milestone, "estimated_effort_minutes", 60) or 60))
        raw_opt = getattr(learner_profile, "opt_session_minutes", 60)
        opt_session_minutes = min(120, max(30, int(raw_opt if raw_opt is not None else 60)))
        min_m_tasks = max(2, math.ceil(milestone_effort / 120))
        max_m_tasks = max(min_m_tasks, math.ceil(milestone_effort / max(90, opt_session_minutes)))
        rec_per_task = min(
            120,
            max(30, int(round(milestone_effort / max(1, max_m_tasks) / 15.0)) * 15),
        )
        scoped_budget = {
            "milestone_sequence_order": milestone.sequence_order,
            "total_milestone_effort_minutes": milestone_effort,
            "recommended_minutes_per_task": rec_per_task,
            "hard_task_duration_bounds_minutes": {"min": 30, "max": 120},
            "recommended_task_count_range": {
                "min_tasks": min_m_tasks,
                "max_tasks": max_m_tasks,
            },
            "fits_milestone_effort": True,
        }

        if goal is not None:
            base_ctx = RoadmapContextBuilder.build_task_decomposition_context(
                goal=goal,
                roadmap=roadmap,
                milestones=[milestone],
                availability=availability,
                learner_profile=learner_profile,
                existing_tasks=existing_tasks,
                include_precomputed_budget=False,
                reference_date=reference_date,
            )
            structured_ctx = (
                f"{base_ctx}\n"
                f"precomputed_schedule_budget: {json.dumps(scoped_budget, ensure_ascii=False)}"
            )
        else:
            sanitized_title = format_untrusted_block(UntrustedBlockKind.GOAL_TITLE, roadmap.title)
            sanitized_desc = format_untrusted_block(
                UntrustedBlockKind.GOAL_RAW_DESCRIPTION,
                roadmap.description or "",
            )
            milestone_json = [
                {
                    "milestone_id": str(milestone.id),
                    "sequence_order": milestone.sequence_order,
                    "title": sanitize_untrusted_text(milestone.title),
                    "description": sanitize_untrusted_text(milestone.description or ""),
                    "learning_outcomes": [
                        sanitize_untrusted_text(out) for out in milestone.learning_outcomes
                    ],
                    "completion_criteria": sanitize_untrusted_text(
                        milestone.completion_criteria or ""
                    ),
                    "estimated_effort_minutes": milestone.estimated_effort_minutes,
                    "required_concepts": [
                        sanitize_untrusted_text(c) for c in milestone.required_concepts
                    ],
                    "unverified_concepts": [
                        sanitize_untrusted_text(c) for c in milestone.unverified_concepts
                    ],
                    "prerequisite_milestone_ids": [
                        str(pid)
                        for pid in (getattr(milestone, "prerequisite_milestone_ids", ()) or ())
                    ],
                }
            ]
            structured_ctx = (
                f"Roadmap: {sanitized_title}\n"
                f"Description: {sanitized_desc}\n"
                f"Availability Mode: {availability.mode}\n"
                f"Learner Optimal Session Minutes: {getattr(learner_profile, 'opt_session_minutes', 45)}\n"
                f"approved_milestones: {json.dumps(milestone_json, ensure_ascii=False)}"
            )

        prefetched_payload = [
            {
                "resource_id": res.resource_id,
                "title": sanitize_untrusted_text(res.title),
                "type": res.type,
                "url": res.url,
                "description": sanitize_untrusted_text(res.description),
            }
            for res in prefetched_resources
        ]
        resources_block = "[PREFETCHED_LEARNING_RESOURCES]\n" + json.dumps(
            prefetched_payload, ensure_ascii=False
        )

        body = f"{header_markers}\n\n{sibling_block}\n\n{structured_ctx}\n\n{resources_block}{harness_suffix}"
        return build_task_decomposer_prompt(body)

    async def decompose_and_validate(
        self,
        *,
        goal: Goal | None,
        roadmap: Roadmap,
        milestones: Sequence[Milestone],
        availability: AvailabilityConfigurationDTO,
        learner_profile: Any,
        existing_tasks: Sequence[object] = (),
        harness_inputs: Any | None = None,
        start_date: date | None = None,
        max_milestone_retries: int = 1,
        on_retry_callback: Callable[[int, Sequence[ConstraintViolationDTO]], Any] | None = None,
        on_progress_callback: Callable[[MilestoneSubjobProgress], Any] | None = None,
        daily_workload_cap_minutes: int | None = None,
        buffer_minutes_per_week: int = 0,
        allow_partial_schedule: bool = True,
        reference_date: date | None = None,
        checkpoint_store: MilestoneCheckpointStorePort | None = None,
    ) -> ValidationGateResultDTO:
        if not milestones:
            raise ProposalValidationGateError(
                message="Không có cột mốc hợp lệ để phân rã nhiệm vụ.",
                code="AI_SCHEMA_VALIDATION_ERROR",
            )

        sorted_milestones = topological_sort_milestones(milestones)
        effective_ref_date = reference_date or datetime.now(UTC).date()
        effective_start_date = start_date or roadmap.start_date or effective_ref_date

        settings = get_settings()
        pipeline_deadline = asyncio.get_running_loop().time() + float(
            settings.ai_sse_pipeline_timeout_seconds
        )
        min_retry_remaining = float(settings.ai_min_retry_remaining_seconds)
        finalization_reserve = float(settings.ai_proposal_finalize_reserve_seconds)

        registry = build_planning_prompt_registry()
        decomposer_tpl = registry.latest(TASK_DECOMPOSER_SKILL.skill_id)
        system_prompt = decomposer_tpl.system_template
        response_schema: dict[str, Any] = TaskProposalLLMOutput.model_json_schema()

        prior_knowledge = goal.prior_knowledge_level if goal is not None else "BEGINNER"
        opt_session_minutes = int(getattr(learner_profile, "opt_session_minutes", 45) or 45)
        harness_suffix = ""
        mem_items: Sequence[Any] = ()
        concept_masteries: Sequence[Any] = ()
        knowledge_chunks: Sequence[Any] = ()
        if harness_inputs is not None:
            mem_items = getattr(harness_inputs, "memory_items", ()) or ()
            concept_masteries = getattr(harness_inputs, "concept_masteries", ()) or ()
            knowledge_chunks = getattr(harness_inputs, "knowledge_chunks", ()) or ()
            if mem_items or concept_masteries or knowledge_chunks:
                assembled = RoadmapContextBuilder.assemble_harness_context(
                    workflow_stage="TASK_DECOMPOSITION",
                    base_context_text="",
                    learner_diagnostic={
                        "prior_knowledge_level": prior_knowledge,
                        "opt_session_minutes": opt_session_minutes,
                    },
                    workflow_constraints={
                        "start_date": effective_start_date.isoformat(),
                        "target_date": roadmap.target_date.isoformat()
                        if roadmap.target_date
                        else None,
                        "availability_mode": availability.mode,
                    },
                    memory_items=mem_items,
                    concept_masteries=concept_masteries,
                    knowledge_chunks=knowledge_chunks,
                    include_planning_context=False,
                )
                if assembled.text:
                    harness_suffix = f"\n\n{assembled.text}"

        indexed_sources: list[KnowledgeSource] = [
            src
            for src in (getattr(harness_inputs, "knowledge_sources", ()) or ())
            if getattr(src, "ingestion_status", None) == KnowledgeIngestionStatus.INDEXED
        ]
        eff_goal_id = self._goal_id or (goal.id if goal is not None else roadmap.goal_id)
        if (
            not indexed_sources
            and self._knowledge_source_repo is not None
            and eff_goal_id is not None
            and self._user_id is not None
        ):
            try:
                loaded_sources = await self._knowledge_source_repo.list_sources_for_goal(
                    eff_goal_id,
                    self._user_id,
                )
                indexed_sources = [
                    src
                    for src in loaded_sources
                    if getattr(src, "ingestion_status", None) == KnowledgeIngestionStatus.INDEXED
                ]
            except Exception as exc:
                logger.warning(
                    "milestone_decomposer_knowledge_sources_load_failed",
                    extra={"goal_id": str(eff_goal_id), "error_type": type(exc).__name__},
                )

        prefetched_map = await self._prefetch_resources_for_milestones(
            sorted_milestones,
            indexed_sources=indexed_sources,
        )
        subjob_concurrency = calculate_dynamic_subjob_concurrency(
            len(sorted_milestones),
            ceiling=self._max_concurrency,
        )
        llm_semaphore = asyncio.Semaphore(subjob_concurrency)
        max_attempts_per_milestone = 1 + max(0, min(1, int(max_milestone_retries)))
        effective_cp_store = (
            checkpoint_store if checkpoint_store is not None else self._checkpoint_store
        )

        resolve_stage_model_fn = getattr(self._llm, "resolve_model_for_thinking_level", None)
        if callable(resolve_stage_model_fn):
            try:
                resolved_stage_model = str(
                    resolve_stage_model_fn(TASK_DECOMPOSER_SKILL.thinking_level)
                )
            except Exception:
                resolved_stage_model = str(
                    getattr(self._llm, "model_identifier", "gemini-3.8-flash")
                )
        else:
            resolved_stage_model = str(getattr(self._llm, "model_identifier", "gemini-3.8-flash"))

        clarification_ctx = (goal.clarification_context or None) if goal is not None else None

        async def _run_single_milestone(
            milestone: Milestone,
        ) -> tuple[MilestoneDecompositionOutcome, BufferedWorkflowRepo]:
            prompt_checksum = decomposer_tpl.checksum if decomposer_tpl is not None else ""
            model_name = resolved_stage_model
            schema_checksum = hashlib.sha256(
                json.dumps(response_schema, sort_keys=True).encode("utf-8")
            ).hexdigest()
            prefetched_resources = prefetched_map.get(milestone.id, [])
            cp_key = compute_milestone_checkpoint_key(
                roadmap_id=self._roadmap_id or roadmap.id,
                milestone=milestone,
                prompt_checksum=prompt_checksum,
                model_name=model_name,
                target_date=roadmap.target_date,
                start_date=effective_start_date,
                all_milestones=sorted_milestones,
                learner_profile=learner_profile,
                prior_knowledge_level=prior_knowledge,
                clarification_context=clarification_ctx,
                availability=availability,
                prefetched_resources=prefetched_resources,
                knowledge_chunks=knowledge_chunks,
                memory_items=mem_items,
                concept_masteries=concept_masteries,
                schema_checksum=schema_checksum,
            )

            if effective_cp_store is not None:
                cached_payload = await effective_cp_store.get_checkpoint(cp_key)
                if cached_payload is not None:
                    logger.info(
                        "milestone_decomposition_checkpoint_hit",
                        extra={
                            "milestone_id": str(milestone.id),
                            "sequence_order": milestone.sequence_order,
                            "checkpoint_key": cp_key,
                        },
                    )
                    cached_tasks = tuple(cached_payload.get("tasks", ()))
                    cached_deps = tuple(cached_payload.get("dependencies", ()))
                    outcome = MilestoneDecompositionOutcome(
                        milestone=milestone,
                        tasks=cached_tasks,
                        dependencies=cached_deps,
                        prompt_tokens=0,
                        completion_tokens=0,
                        thinking_tokens=0,
                        attempts_used=0,
                        retry_history=(),
                        from_checkpoint=True,
                    )
                    if (
                        self._quota is not None
                        and getattr(self._quota, "record_attempt_usage", None) is not None
                    ):
                        try:
                            await self._quota.record_attempt_usage(
                                user_id=self._user_id
                                or getattr(milestone, "roadmap_id", None)
                                or uuid4(),
                                action_type="MILESTONE_BREAKDOWN",
                                requested_model=model_name,
                                prompt_tokens=0,
                                completion_tokens=0,
                                thinking_tokens=0,
                                status="SUCCESS",
                                usage_completeness="COMPLETE",
                                usage_source="CACHE",
                                attempt_no=1,
                                idempotency_key=f"checkpoint:{cp_key}",
                                reservation_id=self._reservation_id,
                            )
                        except Exception:
                            pass
                    return outcome, BufferedWorkflowRepo()
            base_prompt = self._build_milestone_prompt(
                milestone=milestone,
                all_milestones=sorted_milestones,
                goal=goal,
                roadmap=roadmap,
                availability=availability,
                learner_profile=learner_profile,
                existing_tasks=existing_tasks,
                prefetched_resources=prefetched_resources,
                harness_suffix=harness_suffix,
                start_date=effective_start_date,
                reference_date=effective_ref_date,
            )
            current_prompt = base_prompt
            m_prompt_tokens = 0
            m_completion_tokens = 0
            m_thinking_tokens = 0
            m_retry_history: list[dict[str, Any]] = []
            last_local_violations: list[ConstraintViolationDTO] = []
            buffered_wf = BufferedWorkflowRepo()

            async with llm_semaphore:
                for attempt in range(1, max_attempts_per_milestone + 1):
                    remaining_seconds = pipeline_deadline - asyncio.get_running_loop().time()
                    attempt_cap = float(settings.ai_task_decomposer_timeout_seconds)
                    decomposer_timeout = calculate_milestone_subjob_timeout(
                        pipeline_remaining_seconds=remaining_seconds,
                        attempt_cap_seconds=attempt_cap,
                        finalization_reserve_seconds=finalization_reserve,
                    )
                    exec_mgr = AIExecutionManager(
                        provider=self._llm,
                        quota=self._quota,
                        manage_quota=False,
                        max_retries=0,
                        timeout_seconds=decomposer_timeout,
                        tool_call_timeout_seconds=float(settings.ai_tool_call_timeout_seconds),
                        workflow_repo=buffered_wf if self._workflow_repo is not None else None,
                    )
                    try:
                        exec_res = await exec_mgr.execute(
                            user_id=self._user_id or uuid4(),
                            operation_type="TASK_DECOMPOSITION",
                            system_prompt=system_prompt,
                            user_prompt=current_prompt,
                            response_schema=response_schema,
                            model_name=model_name,
                            tools=None,
                            tool_executor=None,
                            max_tool_calls=0,
                            thinking_level=TASK_DECOMPOSER_SKILL.thinking_level,
                            workflow_type=WorkflowType.SCHEDULE_GENERATION,
                            step_name=f"TASK_DECOMPOSER_M{milestone.sequence_order}",
                            step_order=attempt,
                            goal_id=self._goal_id,
                            roadmap_id=self._roadmap_id,
                            context_snapshot={"checkpoint_key": cp_key},
                            prompt_template=decomposer_tpl,
                            existing_reservation_id=self._reservation_id,
                            commit_on_success=False,
                            release_on_failure=False,
                        )
                    except TimeoutError:
                        raise
                    m_prompt_tokens += int(exec_res.prompt_tokens or 0)
                    m_completion_tokens += int(exec_res.completion_tokens or 0)
                    m_thinking_tokens += int(exec_res.thinking_tokens or 0)

                    raw_proposal = exec_res.value if isinstance(exec_res.value, dict) else {}
                    resolved_proposal = resolve_task_resources_from_tool_results(
                        raw_proposal,
                        prefetched_resources,
                        strict=True,
                        fallback_on_empty=bool(prefetched_resources),
                    )
                    raw_tasks = resolved_proposal.get("tasks")
                    m_tasks = (
                        [t for t in raw_tasks if isinstance(t, dict)]
                        if isinstance(raw_tasks, list)
                        else []
                    )
                    raw_deps = resolved_proposal.get("dependencies")
                    m_deps = (
                        [d for d in raw_deps if isinstance(d, dict)]
                        if isinstance(raw_deps, list)
                        else []
                    )

                    stripped_tasks = [
                        {k: v for k, v in t.items() if k not in _SCHEDULE_FIELDS} for t in m_tasks
                    ]
                    stripped_proposal = {"tasks": stripped_tasks, "dependencies": m_deps}

                    local_coverage = validate_task_coverage(stripped_tasks, [milestone])
                    local_tier1 = run_tier1_gate(
                        stripped_proposal,
                        valid_milestone_ids={milestone.id},
                        is_ai_generated=True,
                        allow_unscheduled_tasks=True,
                    )
                    local_violations = [*local_coverage, *local_tier1]
                    if not local_violations:
                        outcome = MilestoneDecompositionOutcome(
                            milestone=milestone,
                            tasks=tuple(stripped_tasks),
                            dependencies=tuple(m_deps),
                            prompt_tokens=m_prompt_tokens,
                            completion_tokens=m_completion_tokens,
                            thinking_tokens=m_thinking_tokens,
                            attempts_used=attempt,
                            retry_history=tuple(m_retry_history),
                            from_checkpoint=False,
                        )
                        if effective_cp_store is not None:
                            await effective_cp_store.set_checkpoint(cp_key, outcome)

                        if self._workflow_repo is not None:
                            async with self._wf_lock:
                                for r in buffered_wf.runs:
                                    await self._workflow_repo.add_run(r)
                                for s in buffered_wf.steps:
                                    await self._workflow_repo.add_step(s)
                                buffered_wf.runs.clear()
                                buffered_wf.steps.clear()

                        return (
                            outcome,
                            buffered_wf,
                        )

                    last_local_violations = local_violations
                    m_retry_history.append(
                        {
                            "milestone_id": str(milestone.id),
                            "sequence_order": milestone.sequence_order,
                            "attempt": attempt,
                            "violations": [v.to_dict() for v in local_violations],
                        }
                    )
                    remaining_for_retry = (
                        pipeline_deadline - asyncio.get_running_loop().time() - finalization_reserve
                    )
                    if (
                        attempt < max_attempts_per_milestone
                        and remaining_for_retry >= min_retry_remaining
                    ):
                        if on_retry_callback is not None:
                            maybe_coro = on_retry_callback(attempt, local_violations)
                            if asyncio.iscoroutine(maybe_coro):
                                await maybe_coro
                        current_prompt = (
                            ProposalValidationGateOrchestrator.build_self_correction_prompt(
                                base_prompt,
                                local_violations,
                                attempt_number=attempt,
                            )
                        )
                        continue
                    break

            raise ProposalValidationGateError(
                message=(
                    f"Phân rã nhiệm vụ cho cột mốc #{milestone.sequence_order} "
                    f"('{milestone.title}') vi phạm ràng buộc cục bộ: "
                    + ", ".join(v.rule_code for v in last_local_violations)
                ),
                code="AI_SCHEMA_VALIDATION_ERROR",
                violations=[v.to_dict() for v in last_local_violations],
            )

        completed_count = 0
        progress_lock = asyncio.Lock()

        async def _run_and_report(
            milestone: Milestone,
        ) -> tuple[MilestoneDecompositionOutcome, BufferedWorkflowRepo]:
            nonlocal completed_count
            result = await _run_single_milestone(milestone)
            async with progress_lock:
                completed_count += 1
                if on_progress_callback is not None:
                    progress = MilestoneSubjobProgress(
                        milestone_sequence=milestone.sequence_order,
                        completed_count=completed_count,
                        total_count=len(sorted_milestones),
                        from_checkpoint=result[0].from_checkpoint,
                    )
                    maybe_coro = on_progress_callback(progress)
                    if asyncio.iscoroutine(maybe_coro):
                        await maybe_coro
            return result

        raw_milestone_results = await run_dynamic_subjob_pool(
            items=sorted_milestones,
            worker_count=subjob_concurrency,
            run_one=_run_and_report,
        )

        milestone_results: list[tuple[MilestoneDecompositionOutcome, BufferedWorkflowRepo]] = []
        first_failure: BaseException | None = None
        for milestone, res in zip(sorted_milestones, raw_milestone_results, strict=True):
            if isinstance(res, asyncio.CancelledError):
                raise res
            if isinstance(res, BaseException):
                if first_failure is None:
                    if isinstance(res, TimeoutError) and not str(res).strip():
                        first_failure = TimeoutError(
                            f"Milestone-scoped decomposition timed out for milestone #{milestone.sequence_order} ({milestone.id})"
                        )
                    else:
                        first_failure = res
            else:
                milestone_results.append(res)

        if first_failure is not None:
            raise first_failure

        if self._workflow_repo is not None:
            persisted_m_runs: set[UUID] = set()
            for _, buffered_wf in milestone_results:
                for run in buffered_wf.runs:
                    if run.id not in persisted_m_runs:
                        await self._workflow_repo.add_run(run)
                        persisted_m_runs.add(run.id)
                for step in buffered_wf.steps:
                    await self._workflow_repo.add_step(step)

        outcomes_by_mid: dict[UUID, MilestoneDecompositionOutcome] = {}
        total_prompt_tokens = 0
        total_completion_tokens = 0
        total_thinking_tokens = 0
        all_retry_history: list[dict[str, Any]] = []
        max_attempts_used = 1

        for outcome, _ in milestone_results:
            outcomes_by_mid[outcome.milestone.id] = outcome
            total_prompt_tokens += outcome.prompt_tokens
            total_completion_tokens += outcome.completion_tokens
            total_thinking_tokens += outcome.thinking_tokens
            all_retry_history.extend(outcome.retry_history)
            max_attempts_used = max(max_attempts_used, outcome.attempts_used)

        reconciled = reconcile_milestone_proposals(sorted_milestones, outcomes_by_mid)
        global_coverage_violations = validate_task_coverage(reconciled.tasks, sorted_milestones)
        if global_coverage_violations:
            raise ProposalValidationGateError(
                message=(
                    "Đề xuất hợp nhất từ các cột mốc vi phạm bao phủ toàn cục: "
                    + ", ".join(v.rule_code for v in global_coverage_violations)
                ),
                code="AI_SCHEMA_VALIDATION_ERROR",
                violations=[v.to_dict() for v in global_coverage_violations],
            )

        milestone_order_map = {str(m.id): m.sequence_order for m in sorted_milestones}
        soft_pacing_v2_enabled = bool(
            getattr(settings, "spatio_temporal_v2_soft_pacing_enabled", True)
        )
        soft_end_buffer_ratio = float(
            getattr(settings, "spatio_temporal_soft_end_buffer_ratio", 0.12)
        )
        soft_max_consecutive_days = int(
            getattr(settings, "spatio_temporal_soft_max_consecutive_days", 5)
        )

        alloc_res = SpatioTemporalRuleEngine.allocate_task_sessions_with_diagnostics(
            reconciled.tasks,
            availability,
            start_date=effective_start_date,
            target_date=roadmap.target_date,
            dependencies=reconciled.dependencies,
            existing_tasks=existing_tasks,
            milestone_order_map=milestone_order_map,
            preferred_session_minutes=opt_session_minutes,
            estimation_bias_beta=float(
                getattr(learner_profile, "estimation_bias_beta", 1.0) or 1.0
            ),
            peak_productivity_slots=getattr(learner_profile, "peak_productivity_slots", ()),
            daily_workload_cap_minutes=daily_workload_cap_minutes,
            buffer_minutes_per_week=buffer_minutes_per_week,
            soft_pacing_v2_enabled=soft_pacing_v2_enabled,
            end_buffer_ratio=soft_end_buffer_ratio,
            max_consecutive_study_days=soft_max_consecutive_days,
        )

        merged_proposal: dict[str, Any] = {
            "tasks": alloc_res.tasks,
            "dependencies": reconciled.dependencies,
            "schedule_blocks": alloc_res.schedule_blocks,
            "feasibility_verdict": alloc_res.feasibility_verdict,
            "unscheduled_diagnostics": [d.to_dict() for d in alloc_res.unscheduled_diagnostics],
        }

        has_unscheduled = any(
            isinstance(t, dict) and safe_parse_iso_date(t.get("scheduled_date")) is None
            for t in alloc_res.tasks
        )
        allow_unscheduled_in_gate = False
        attempt_avail_mins: int | None = None
        attempt_completeness: ScheduleCompletenessStatus | None = None
        if has_unscheduled:
            avail_mins = SpatioTemporalRuleEngine.calculate_available_capacity_minutes(
                availability,
                start_date=effective_start_date,
                target_date=roadmap.target_date,
                existing_tasks=existing_tasks,
                daily_workload_cap_minutes=daily_workload_cap_minutes,
            )
            attempt_avail_mins = avail_mins
            req_mins = sum(
                _safe_minutes(t.get("estimated_minutes"))
                for t in alloc_res.tasks
                if isinstance(t, dict)
            )
            merged_proposal["_capacity_overflow"] = {
                "available_minutes": avail_mins,
                "required_minutes": req_mins,
                "target_date": roadmap.target_date.isoformat() if roadmap.target_date else "N/A",
            }
            dict_tasks = [t for t in alloc_res.tasks if isinstance(t, dict)]
            scheduled_count = sum(
                1 for t in dict_tasks if safe_parse_iso_date(t.get("scheduled_date")) is not None
            )
            unscheduled_count = len(dict_tasks) - scheduled_count
            feasibility_assessment = assess_schedule_feasibility(
                dict_tasks,
                available_minutes=avail_mins,
            )
            has_blocks = isinstance(alloc_res.schedule_blocks, list) and any(
                isinstance(b, dict) for b in alloc_res.schedule_blocks
            )
            all_scheduled_have_times = scheduled_count > 0 and all(
                safe_parse_iso_datetime(t.get("scheduled_start")) is not None
                and safe_parse_iso_datetime(t.get("scheduled_end")) is not None
                for t in dict_tasks
                if safe_parse_iso_date(t.get("scheduled_date")) is not None
            )
            attempt_completeness = classify_schedule_completeness(
                total_tasks=len(dict_tasks),
                scheduled_tasks_count=scheduled_count,
                unscheduled_tasks_count=unscheduled_count,
                available_minutes=avail_mins,
                schedulable_ratio=feasibility_assessment.schedulable_ratio,
                feasibility_verdict=alloc_res.feasibility_verdict,
                has_schedule_blocks=has_blocks,
                all_scheduled_have_block_times=all_scheduled_have_times,
                allow_partial_schedule=allow_partial_schedule,
            )
            if attempt_completeness == "INFEASIBLE":
                if allow_partial_schedule:
                    raise PlanInfeasibleError(feasibility_assessment.schedulable_ratio)
                raise ProposalValidationGateError(
                    message=(
                        "Đề xuất lịch học không khả thi với quỹ thời gian rảnh hiện tại "
                        f"(tỉ lệ xếp lịch {feasibility_assessment.schedulable_ratio:.0%})."
                    ),
                    code="AI_SCHEMA_VALIDATION_ERROR",
                )
            if attempt_completeness == "UNDETERMINED":
                raise ProposalValidationGateError(
                    message=(
                        "Đề xuất lịch học chưa hoàn tất kiểm định tất định (UNDETERMINED) "
                        "nên không thể lưu bản nháp."
                    ),
                    code="AI_SCHEMA_VALIDATION_ERROR",
                )
            if attempt_completeness == "PARTIAL":
                allow_unscheduled_in_gate = True

        orchestrator = ProposalValidationGateOrchestrator(
            llm_provider=self._llm,
            enable_tier3_judge=self._enable_tier3_judge,
            tier3_timeout_seconds=self._tier3_timeout_seconds,
            workflow_repo=self._workflow_repo,
            user_id=self._user_id,
            goal_id=self._goal_id,
            roadmap_id=self._roadmap_id,
        )
        valid_mids: set[UUID | str] = {m.id for m in sorted_milestones}
        tier1_violations = orchestrator.run_tier1_gate(
            merged_proposal,
            valid_milestone_ids=valid_mids,
            is_ai_generated=True,
            allow_unscheduled_tasks=allow_unscheduled_in_gate,
        )
        tier2_violations, soft_warnings = orchestrator.run_tier2_gate(
            merged_proposal,
            availability=availability,
            existing_tasks=existing_tasks,
            current_roadmap_target_date=roadmap.target_date,
            allow_unscheduled_tasks=allow_unscheduled_in_gate,
        )
        deterministic_violations = [*tier1_violations, *tier2_violations]
        if deterministic_violations:
            raise ProposalValidationGateError(
                message=(
                    "Đề xuất lịch học hợp nhất vi phạm kiểm định Tier 1/2: "
                    + ", ".join(v.rule_code for v in deterministic_violations)
                ),
                code="AI_SCHEMA_VALIDATION_ERROR",
                violations=[v.to_dict() for v in deterministic_violations],
            )

        remaining_budget = max(0.0, pipeline_deadline - asyncio.get_running_loop().time())
        min_critic_remaining = float(getattr(settings, "ai_min_critic_remaining_seconds", 6.0))
        min_judge_remaining = float(getattr(settings, "ai_min_judge_remaining_seconds", 3.0))
        critics_budget_ok = remaining_budget >= min_critic_remaining

        goal_title = goal.title if goal is not None else roadmap.title
        milestone_summary = json.dumps(
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
                for m in sorted_milestones
            ],
            ensure_ascii=False,
        )

        critic_advisory_warnings: list[str] = []
        quality_violations: list[ConstraintViolationDTO] = []
        quality_reports: list[dict[str, Any]] = []
        critic_step_records: list[tuple[WorkflowRun, WorkflowStepExecution]] = []
        judge_step_records: list[tuple[WorkflowRun, WorkflowStepExecution]] = []

        if not critics_budget_ok:
            critic_advisory_warnings.append(
                "Ngân sách thời gian còn lại không đủ cho AI Critic — đã bỏ qua bước Critic và giữ kiểm định Tier 1/2."
            )
            quality_reports = [
                {"critic": "QUALITY_CRITIC", "status": "SKIPPED_LOW_BUDGET", "issues": []}
            ]

        async def _run_critics_coro() -> tuple[
            list[ConstraintViolationDTO], list[dict[str, Any]], int, int, int, bool
        ]:
            critic_timeout = min(
                float(settings.ai_quality_critic_timeout_seconds), remaining_budget
            )
            arbiter_timeout = min(
                float(settings.ai_quality_arbiter_timeout_seconds), remaining_budget
            )
            critic_tokens: dict[str, int] = {}
            try:
                c_violations, c_reports, c_p, c_c = await asyncio.wait_for(
                    run_dual_quality_critics(
                        self._llm,
                        stage="TASK_DECOMPOSITION",
                        payload={
                            "tasks": merged_proposal["tasks"],
                            "dependencies": merged_proposal["dependencies"],
                        },
                        context=f"Goal: {sanitize_untrusted_text(goal_title)}",
                        learner_level=prior_knowledge,
                        milestone_summary=milestone_summary,
                        timeout_seconds=critic_timeout,
                        arbiter_timeout_seconds=arbiter_timeout,
                        remaining_budget_seconds=remaining_budget,
                        workflow_repo=None,
                        step_records_out=critic_step_records,
                        user_id=self._user_id,
                        goal_id=self._goal_id,
                        roadmap_id=self._roadmap_id,
                        workflow_type=WorkflowType.SCHEDULE_GENERATION,
                        token_accumulator=critic_tokens,
                        quota=self._quota,
                    ),
                    timeout=remaining_budget,
                )
                return (
                    c_violations,
                    c_reports,
                    c_p,
                    c_c,
                    int(critic_tokens.get("thinking_tokens", 0)),
                    False,
                )
            except TimeoutError:
                return (
                    [],
                    [{"critic": "QUALITY_CRITIC", "status": "SKIPPED_LOW_BUDGET", "issues": []}],
                    0,
                    0,
                    0,
                    True,
                )

        async def _run_judge_coro() -> Tier3JudgeOutcome:
            dynamic_judge_cap = min(
                float(
                    self._tier3_timeout_seconds
                    if self._tier3_timeout_seconds is not None
                    else getattr(settings, "tier3_judge_timeout_seconds", 12.0)
                ),
                remaining_budget,
            )
            return await execute_tier3_pedagogical_judge(
                self._llm,
                merged_proposal,
                enable_tier3_judge=self._enable_tier3_judge,
                tier3_timeout_seconds=dynamic_judge_cap,
                min_judge_remaining_seconds=min_judge_remaining,
                goal_title=goal_title,
                learner_level=prior_knowledge,
                milestone_summary=milestone_summary,
                milestones_metadata=sorted_milestones,
                remaining_budget_seconds=remaining_budget,
                workflow_repo=None,
                step_records_out=judge_step_records,
                user_id=self._user_id,
                goal_id=self._goal_id,
                roadmap_id=self._roadmap_id,
                quota=self._quota,
            )

        critic_result: (
            tuple[list[ConstraintViolationDTO], list[dict[str, Any]], int, int, int, bool] | None
        ) = None
        if critics_budget_ok and self._enable_tier3_judge:
            critic_result, judge_outcome = await asyncio.gather(
                _run_critics_coro(),
                _run_judge_coro(),
            )
        elif critics_budget_ok:
            critic_result = await _run_critics_coro()
            judge_outcome = await _run_judge_coro()
        else:
            judge_outcome = await _run_judge_coro()

        if self._workflow_repo is not None:
            persisted_runs: set[UUID] = set()
            for run, step in [*critic_step_records, *judge_step_records]:
                if run.id not in persisted_runs:
                    await self._workflow_repo.add_run(run)
                    persisted_runs.add(run.id)
                await self._workflow_repo.add_step(step)

        if critic_result is not None:
            (
                critic_violations,
                quality_reports,
                critic_p,
                critic_c,
                critic_t,
                critic_timed_out,
            ) = critic_result
            total_prompt_tokens += critic_p
            total_completion_tokens += critic_c
            total_thinking_tokens += critic_t
            if critic_timed_out:
                critic_advisory_warnings.append(
                    "AI Critic hết ngân sách thời gian — đã bỏ qua bước Critic và giữ kiểm định Tier 1/2."
                )
            else:
                if has_operational_quality_review_failure(critic_violations):
                    critic_advisory_warnings.append(
                        "AI Critic tạm thời quá thời gian chờ — đã tiếp tục kiểm định Tier 1/2."
                    )
                    critic_violations = [
                        v
                        for v in critic_violations
                        if v.rule_code
                        not in {"QUALITY_CRITIC_UNAVAILABLE", "QUALITY_ARBITER_UNAVAILABLE"}
                    ]
                quality_violations.extend(critic_violations)

        merged_proposal["quality_reviews"] = quality_reports

        total_prompt_tokens += judge_outcome.prompt_tokens
        total_completion_tokens += judge_outcome.completion_tokens
        total_thinking_tokens += judge_outcome.thinking_tokens

        if quality_violations:
            raise ProposalValidationGateError(
                message=(
                    "Đề xuất lịch học hợp nhất vi phạm thẩm định chất lượng AI Critic: "
                    + ", ".join(qv.rule_code for qv in quality_violations)
                ),
                code="AI_SCHEMA_VALIDATION_ERROR",
                violations=[qv.to_dict() for qv in quality_violations],
            )

        return orchestrator._build_valid_gate_result(
            merged_proposal,
            soft_warnings=soft_warnings,
            judge_skipped=judge_outcome.judge_skipped,
            score=judge_outcome.pedagogical_score,
            advisories=[*critic_advisory_warnings, *judge_outcome.advisory_warnings],
            judge_status=judge_outcome.judge_status,
            prompt_tokens=total_prompt_tokens,
            completion_tokens=total_completion_tokens,
            thinking_tokens=total_thinking_tokens,
            attempts_used=max_attempts_used,
            retry_history=tuple(all_retry_history),
            available_minutes=attempt_avail_mins,
            schedule_completeness_status=attempt_completeness,
            allow_partial_schedule=allow_partial_schedule,
        )
