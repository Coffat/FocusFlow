import json
import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from src.account.public_api import (
    AvailabilityQueryPort,
    AvailabilitySnapshotDTO,
    CalendarConnectionQueryPort,
    LearnerMemoryQueryPort,
    LearnerProfileQueryPort,
    QuotaFacadePort,
    UserQueryPort,
)
from src.execution.public_api import ExecutionScheduleSyncPort
from src.planning.application.dtos.planning_dtos import (
    SseJobTicketDTO,
    TaskProposalLLMOutput,
)
from src.planning.application.ports.knowledge_base_port import KnowledgeBasePort
from src.planning.application.ports.knowledge_source_repository_port import (
    KnowledgeSourceRepositoryPort,
)
from src.planning.application.ports.planning_repository_ports import (
    GoalRepositoryPort,
    MilestoneRepositoryPort,
    RoadmapRepositoryPort,
    ScheduleProposalRepositoryPort,
)
from src.planning.application.ports.schedule_block_repository_port import (
    ScheduleBlockRepositoryPort,
)
from src.planning.application.ports.sse_job_port import SseJobPort
from src.planning.application.services.effective_availability_service import (
    GetEffectiveAvailabilityUseCase,
)
from src.planning.application.services.existing_schedule_occupancy import (
    expand_existing_schedule_occupancy,
)
from src.planning.application.services.harness_support import (
    compact_context_snapshot,
    load_planning_harness_context_inputs,
)
from src.planning.application.services.knowledge_tool_dispatcher import (
    KnowledgeToolDispatcher,
    RoadmapPipelineStage,
)
from src.planning.application.services.learning_quality import assess_schedule_feasibility
from src.planning.application.services.roadmap_context_builder import (
    RoadmapContextBuilder,
)
from src.planning.application.services.roadmap_skills import (
    TASK_DECOMPOSER_SKILL,
    build_planning_prompt_registry,
    build_task_decomposer_prompt,
)
from src.planning.application.services.validation_gate import (
    DEFAULT_MAX_RETRIES,
    ProposalValidationGateOrchestrator,
)
from src.planning.domain.exceptions.planning_exceptions import (
    RoadmapNotFoundError,
    UnapprovedMilestonesError,
)
from src.planning.domain.models.knowledge_concept import LearningResource
from src.planning.domain.models.milestone import MilestoneStatus
from src.planning.domain.models.schedule import (
    ScheduleProposal,
    ScheduleProposalStatus,
)
from src.planning.domain.services.spatio_temporal_engine import SpatioTemporalRuleEngine
from src.planning.domain.services.validation_types import (
    AvailabilityConfigurationDTO,
    AvailabilitySlotDTO,
    ConstraintViolationDTO,
)
from src.shared_kernel.application.embedding_port import EmbeddingProviderPort
from src.shared_kernel.application.harness.models import (
    WorkflowRun,
    WorkflowStatus,
    WorkflowStepExecution,
    WorkflowStepStatus,
    WorkflowType,
)
from src.shared_kernel.application.harness.untrusted_context import (
    UntrustedBlockKind,
    format_untrusted_block,
    sanitize_untrusted_text,
)
from src.shared_kernel.application.harness.workflow_port import WorkflowRepositoryPort
from src.shared_kernel.application.llm_port import LLMProviderPort
from src.shared_kernel.application.uow import AsyncUnitOfWork
from src.shared_kernel.config import get_settings
from src.shared_kernel.domain.base import generate_uuid7

logger = logging.getLogger(__name__)

SCHEDULE_PROPOSAL_RESPONSE_SCHEMA: dict[str, Any] = TaskProposalLLMOutput.model_json_schema()


def resolve_task_resources_from_tool_results(
    proposal_data: dict[str, Any],
    collected_resources: Sequence[LearningResource | dict[str, Any]],
    *,
    strict: bool = True,
) -> dict[str, Any]:
    """Resolve `resource_ids` on each task against verified tool results; drop hallucinated IDs."""
    if not isinstance(proposal_data, dict):
        return proposal_data
    raw_tasks = proposal_data.get("tasks")
    if not isinstance(raw_tasks, list):
        return proposal_data

    resource_lookup: dict[str, dict[str, str]] = {}
    for item in collected_resources:
        if isinstance(item, LearningResource):
            r_dict = item.to_dict()
            rid = item.resource_id
        elif isinstance(item, dict):
            rid = str(item.get("resource_id") or "").strip()
            r_dict = {
                "resource_id": rid,
                "title": str(item.get("title") or "").strip(),
                "url": str(item.get("url") or "").strip(),
                "type": str(item.get("type") or item.get("resource_type") or "DOCS").strip(),
                "resource_type": str(
                    item.get("resource_type") or item.get("type") or "DOCS"
                ).strip(),
                "description": str(item.get("description") or "").strip(),
            }
        else:
            continue
        if rid:
            resource_lookup[rid] = r_dict

    resolved_tasks: list[Any] = []
    for task in raw_tasks:
        if not isinstance(task, dict):
            resolved_tasks.append(task)
            continue
        t_copy = dict(task)
        has_resource_ids_field = "resource_ids" in t_copy
        raw_rids = t_copy.get("resource_ids")
        if isinstance(raw_rids, list):
            clean_rids: list[str] = []
            for raw_id in raw_rids:
                rid_str = str(raw_id or "").strip()
                if rid_str and rid_str not in clean_rids:
                    clean_rids.append(rid_str)
                if len(clean_rids) >= 3:
                    break
            t_copy["resource_ids"] = clean_rids
            if not resource_lookup:
                t_copy["learning_resources"] = []
            else:
                t_copy["learning_resources"] = [
                    dict(resource_lookup[rid]) for rid in clean_rids if rid in resource_lookup
                ]
        elif strict or has_resource_ids_field:
            t_copy["resource_ids"] = []
            t_copy["learning_resources"] = []
        resolved_tasks.append(t_copy)

    return {**proposal_data, "tasks": resolved_tasks}


def build_availability_config_from_snapshot(
    snapshot: AvailabilitySnapshotDTO | None,
) -> AvailabilityConfigurationDTO:
    """Convert cross-context AvailabilitySnapshotDTO into Planning's AvailabilityConfigurationDTO."""
    if snapshot is None:
        return AvailabilityConfigurationDTO(
            mode="MODE_A",
            daily_quota_minutes={
                "monday": 120,
                "tuesday": 120,
                "wednesday": 120,
                "thursday": 120,
                "friday": 120,
                "saturday": 180,
                "sunday": 180,
            },
            default_daily_quota_minutes=120,
        )

    slots: list[AvailabilitySlotDTO] = []
    for raw_slot in snapshot.availability_slots:
        slots.append(
            AvailabilitySlotDTO(
                day_of_week=str(raw_slot.get("day_of_week", "monday")),
                start_time=str(raw_slot.get("start_time", "19:30")),
                end_time=str(raw_slot.get("end_time", "21:30")),
                end_day_offset=int(raw_slot.get("end_day_offset", 0) or 0),
                is_active=bool(raw_slot.get("is_active", True)),
            )
        )

    default_cap = int(snapshot.daily_cap_minutes) if snapshot.daily_cap_minutes > 0 else 120
    quotas_map: dict[str | int, int] = (
        {str(k): int(v) for k, v in snapshot.daily_quota_minutes.items()}
        if snapshot.daily_quota_minutes
        else {}
    )
    return AvailabilityConfigurationDTO(
        mode=snapshot.mode,
        daily_quota_minutes=quotas_map,
        default_daily_quota_minutes=default_cap,
        availability_slots=tuple(slots),
        disabled_weekdays=frozenset(snapshot.disabled_weekdays),
    )


def normalize_proposal_task_ids_and_dependencies(
    proposal_data: dict[str, Any],
) -> dict[str, Any]:
    """Ensure every task in proposal_data has a valid UUID string `task_id` and remap dependency IDs."""
    normalized = dict(proposal_data)
    raw_tasks = normalized.get("tasks", [])
    if not isinstance(raw_tasks, list):
        return normalized

    id_remap: dict[str, str] = {}
    cleaned_tasks: list[dict[str, Any]] = []

    for idx, raw_t in enumerate(raw_tasks):
        if not isinstance(raw_t, dict):
            continue
        t_copy = dict(raw_t)
        raw_tid = str(t_copy.get("task_id") or t_copy.get("id") or f"task_{idx}").strip()
        try:
            valid_uuid = str(UUID(raw_tid))
        except ValueError:
            valid_uuid = str(generate_uuid7())
        id_remap[raw_tid] = valid_uuid
        id_remap[f"task_{idx}"] = valid_uuid
        t_copy["task_id"] = valid_uuid
        cleaned_tasks.append(t_copy)

    raw_deps = normalized.get("dependencies", [])
    cleaned_deps: list[dict[str, Any]] = []
    if isinstance(raw_deps, list):
        for dep in raw_deps:
            if not isinstance(dep, dict):
                continue
            pred_raw = str(dep.get("predecessor_id", "")).strip()
            succ_raw = str(dep.get("successor_id", "")).strip()
            if not pred_raw or not succ_raw:
                continue
            cleaned_deps.append(
                {
                    "predecessor_id": id_remap.get(pred_raw, pred_raw),
                    "successor_id": id_remap.get(succ_raw, succ_raw),
                    "is_mandatory": bool(dep.get("is_mandatory", True)),
                }
            )

    # Also convert any inline `prerequisite_ids` / `depends_on` on tasks into explicit dependencies
    seen_edges = {(d["predecessor_id"], d["successor_id"]) for d in cleaned_deps}
    for t_copy in cleaned_tasks:
        succ_id = str(t_copy["task_id"])
        prereqs = t_copy.get("prerequisite_ids") or t_copy.get("depends_on") or []
        if isinstance(prereqs, list):
            remapped_prereqs: list[str] = []
            for p in prereqs:
                p_str = id_remap.get(str(p).strip(), str(p).strip())
                remapped_prereqs.append(p_str)
                if (p_str, succ_id) not in seen_edges:
                    seen_edges.add((p_str, succ_id))
                    cleaned_deps.append(
                        {
                            "predecessor_id": p_str,
                            "successor_id": succ_id,
                            "is_mandatory": True,
                        }
                    )
            t_copy["prerequisite_ids"] = remapped_prereqs

    normalized["tasks"] = cleaned_tasks
    normalized["dependencies"] = cleaned_deps
    raw_blocks = normalized.get("schedule_blocks")
    if isinstance(raw_blocks, list):
        normalized["schedule_blocks"] = [
            {**block, "task_id": id_remap.get(str(block.get("task_id")), str(block.get("task_id")))}
            for block in raw_blocks
            if isinstance(block, dict)
        ]
    raw_unscheduled = normalized.get("unscheduled_tasks")
    if isinstance(raw_unscheduled, list):
        normalized["unscheduled_tasks"] = [
            {
                **t_item,
                "task_id": id_remap.get(str(t_item.get("task_id")), str(t_item.get("task_id"))),
            }
            for t_item in raw_unscheduled
            if isinstance(t_item, dict)
        ]
    return normalized


class ExecuteScheduleProposalGenerationUseCase:
    """Stage 2 Worker / Inline executor for Level-2 AI ScheduleProposal Generation (UC-08 / ADR-009)."""

    def __init__(
        self,
        *,
        goal_repo: GoalRepositoryPort,
        roadmap_repo: RoadmapRepositoryPort,
        milestone_repo: MilestoneRepositoryPort,
        proposal_repo: ScheduleProposalRepositoryPort,
        availability_query_port: AvailabilityQueryPort,
        learner_profile_port: LearnerProfileQueryPort,
        execution_sync_port: ExecutionScheduleSyncPort,
        quota_facade: QuotaFacadePort,
        llm_provider: LLMProviderPort,
        sse_job_store: SseJobPort,
        uow: AsyncUnitOfWork,
        enable_tier3_judge: bool = True,
        knowledge_base: KnowledgeBasePort | None = None,
        user_query_port: UserQueryPort | None = None,
        block_repo: ScheduleBlockRepositoryPort | None = None,
        learner_memory_port: LearnerMemoryQueryPort | None = None,
        knowledge_source_repo: KnowledgeSourceRepositoryPort | None = None,
        embedding_provider: EmbeddingProviderPort | None = None,
        workflow_repo: WorkflowRepositoryPort | None = None,
        calendar_connection_query_port: CalendarConnectionQueryPort | None = None,
    ) -> None:
        self._goal_repo = goal_repo
        self._roadmap_repo = roadmap_repo
        self._milestone_repo = milestone_repo
        self._proposal_repo = proposal_repo
        self._availability_port = availability_query_port
        self._learner_profile_port = learner_profile_port
        self._execution_sync_port = execution_sync_port
        self._quota_facade = quota_facade
        self._llm = llm_provider
        self._sse = sse_job_store
        self._uow = uow
        self._enable_tier3_judge = enable_tier3_judge
        self._kb = knowledge_base
        self._user_query_port = user_query_port
        self._block_repo = block_repo
        self._learner_memory_port = learner_memory_port
        self._knowledge_source_repo = knowledge_source_repo
        self._embedding_provider = embedding_provider
        self._workflow_repo = workflow_repo
        self._calendar_connection_port = calendar_connection_query_port

    async def execute(
        self,
        *,
        job_id: UUID,
        user_id: UUID,
        roadmap_id: UUID,
        reservation_id: UUID,
        max_retries: int = DEFAULT_MAX_RETRIES,
        now: datetime | None = None,
    ) -> ScheduleProposal:
        effective_now = now or datetime.now(UTC)

        try:
            roadmap = await self._roadmap_repo.get_by_id_for_user(roadmap_id, user_id)
            if roadmap is None:
                raise RoadmapNotFoundError()

            milestones = await self._milestone_repo.list_by_roadmap_id(roadmap_id)
            if not milestones or any(m.status == MilestoneStatus.PENDING for m in milestones):
                raise UnapprovedMilestonesError()

            goal = await self._goal_repo.get_by_id(roadmap.goal_id)
            user_tz = "Asia/Ho_Chi_Minh"
            if self._user_query_port is not None:
                user_snapshot = await self._user_query_port.get_user_by_id(user_id)
                if user_snapshot is not None and user_snapshot.timezone:
                    user_tz = user_snapshot.timezone

            learner_profile = await self._learner_profile_port.get_learner_profile(user_id)
            prior_knowledge = goal.prior_knowledge_level if goal is not None else "BEGINNER"
            clarification_ctx = (goal.clarification_context or "") if goal is not None else ""

            active_roadmaps = await self._roadmap_repo.list_by_user_id(user_id, status="ACTIVE")
            other_roadmaps = [r for r in active_roadmaps if r.id != roadmap_id]
            other_roadmap_ids = [r.id for r in other_roadmaps]
            roadmap_target_dates = {r.id: r.target_date for r in other_roadmaps}
            existing_tasks = await self._execution_sync_port.get_tasks_for_roadmaps(
                other_roadmap_ids,
                roadmap_target_dates=roadmap_target_dates,
            )
            if self._block_repo is not None:
                existing_tasks = expand_existing_schedule_occupancy(
                    existing_tasks,
                    await self._block_repo.list_by_roadmap_ids(other_roadmap_ids),
                )

            effective_avail_uc = GetEffectiveAvailabilityUseCase(
                availability_query_port=self._availability_port,
                calendar_connection_query_port=self._calendar_connection_port,
                execution_sync_port=self._execution_sync_port,
            )
            effective_avail = await effective_avail_uc.execute(
                user_id=user_id,
                start_date=roadmap.start_date or effective_now.date(),
                target_date=roadmap.target_date,
                timezone=user_tz,
                existing_tasks=existing_tasks,
                exclude_roadmap_id=roadmap_id,
            )
            avail_config = effective_avail.availability_config
            existing_tasks = list(effective_avail.effective_existing_tasks)

            await self._sse.append_event(
                job_id=job_id,
                event="stage",
                status="STREAMING",
                data={
                    "stage": "STREAMING",
                    "progress": 35,
                    "delta_text": "Đang tổng hợp hồ sơ năng lực SRL, lịch rảnh và phân bổ nhiệm vụ...",
                    "deltaText": "Đang tổng hợp hồ sơ năng lực SRL, lịch rảnh và phân bổ nhiệm vụ...",
                },
            )

            sanitized_title = format_untrusted_block(UntrustedBlockKind.GOAL_TITLE, roadmap.title)
            sanitized_desc = format_untrusted_block(
                UntrustedBlockKind.GOAL_RAW_DESCRIPTION, roadmap.description or ""
            )
            milestone_lines = [
                (
                    f"- id={m.id} | seq={m.sequence_order} | "
                    f"title={format_untrusted_block(UntrustedBlockKind.MILESTONE_DATA, m.title)} | "
                    f"outcome_ids={','.join(f'M{m.sequence_order}-O{i}' for i in range(1, len(m.learning_outcomes) + 1))} | "
                    f"required_concepts={','.join(m.required_concepts)} | "
                    f"estimated_effort_minutes={m.estimated_effort_minutes}"
                )
                for m in milestones
            ]
            slot_lines = [
                f"{slot.day_of_week}: {slot.start_time}-{slot.end_time}"
                for slot in avail_config.availability_slots
                if slot.is_active
            ]
            start_date_str = (roadmap.start_date or effective_now.date()).isoformat()

            decomposer_tpl = build_planning_prompt_registry().latest(TASK_DECOMPOSER_SKILL.skill_id)
            system_prompt = decomposer_tpl.system_template
            # Structured machine-readable header markers paired with unified context builder
            # without duplicating Goal/Milestone/Availability prose.
            header_markers = (
                "GENERATE_PROPOSAL_TASKS\n"
                f"Start Date: {start_date_str}\n"
                f"Target Date: {roadmap.target_date.isoformat() if roadmap.target_date else 'N/A'}\n"
                "MILESTONE_IDS:\n"
                + "\n".join(milestone_lines)
                + "\nAVAILABILITY_SLOTS:\n"
                + ("\n".join(slot_lines) if slot_lines else "monday: 19:30-21:30")
            )
            harness_inputs = await load_planning_harness_context_inputs(
                user_id=user_id,
                goal_id=roadmap.goal_id,
                query_text=f"{roadmap.title} {roadmap.description or ''}",
                learner_memory_port=self._learner_memory_port,
                knowledge_source_repo=self._knowledge_source_repo,
                embedding_provider=self._embedding_provider,
            )
            if goal is not None:
                structured_ctx = RoadmapContextBuilder.build_task_decomposition_context(
                    goal=goal,
                    roadmap=roadmap,
                    milestones=milestones,
                    availability=avail_config,
                    learner_profile=learner_profile,
                    existing_tasks=existing_tasks,
                )
            else:
                structured_ctx = (
                    f"Roadmap: {sanitized_title}\n"
                    f"Description: {sanitized_desc}\n"
                    f"Prior Knowledge Level: {sanitize_untrusted_text(prior_knowledge)}\n"
                    + (
                        "Clarification Context:\n"
                        + format_untrusted_block(
                            UntrustedBlockKind.CLARIFICATION_DATA, clarification_ctx
                        )
                        + "\n"
                        if clarification_ctx
                        else ""
                    )
                    + f"Availability Mode: {avail_config.mode}\n"
                    f"Learner Optimal Session Minutes: {learner_profile.opt_session_minutes}"
                )

            assembled = RoadmapContextBuilder.assemble_harness_context(
                workflow_stage="TASK_DECOMPOSITION",
                base_context_text=structured_ctx,
                learner_diagnostic={
                    "prior_knowledge_level": prior_knowledge,
                    "opt_session_minutes": learner_profile.opt_session_minutes,
                },
                workflow_constraints={
                    "start_date": start_date_str,
                    "target_date": roadmap.target_date.isoformat() if roadmap.target_date else None,
                    "availability_mode": avail_config.mode,
                },
                memory_items=harness_inputs.memory_items,
                concept_masteries=harness_inputs.concept_masteries,
                knowledge_chunks=harness_inputs.knowledge_chunks,
            )
            harness_suffix = (
                f"\n\n{assembled.text}"
                if (
                    harness_inputs.memory_items
                    or harness_inputs.concept_masteries
                    or harness_inputs.knowledge_chunks
                )
                else ""
            )
            user_prompt = build_task_decomposer_prompt(
                f"{header_markers}\n\n{structured_ctx}{harness_suffix}"
            )

            dispatcher: KnowledgeToolDispatcher | None = None
            if self._kb is not None:
                dispatcher = KnowledgeToolDispatcher(
                    self._kb,
                    stage=RoadmapPipelineStage.TASK_DECOMPOSITION,
                    max_tool_calls=TASK_DECOMPOSER_SKILL.max_tool_calls,
                    timeout_seconds=float(get_settings().llm_tool_timeout_seconds),
                )

            await self._sse.append_event(
                job_id=job_id,
                event="chunk",
                status="STREAMING",
                data={
                    "stage": "VALIDATING_TIER_1_2_3",
                    "progress": 60,
                    "delta_text": "Đang phân rã nhiệm vụ bằng AI và chạy cổng kiểm định 3 tầng (Schema, DAG & Sư phạm)...",
                    "deltaText": "Đang phân rã nhiệm vụ bằng AI và chạy cổng kiểm định 3 tầng (Schema, DAG & Sư phạm)...",
                },
            )

            async def _on_retry(
                attempt: int,
                violations: Sequence[ConstraintViolationDTO],
            ) -> None:
                await self._sse.append_event(
                    job_id=job_id,
                    event="validation_retry",
                    status="STREAMING",
                    data={
                        "stage": "VALIDATING_TIER_1_2_3",
                        "progress": min(90, 60 + attempt * 12),
                        "retry_attempt": attempt,
                        "violations": [v.to_dict() for v in violations],
                        "delta_text": (
                            f"Phát hiện {len(violations)} xung đột ràng buộc ở vòng #{attempt}. "
                            "Đang tự động điều chỉnh lịch học..."
                        ),
                        "deltaText": (
                            f"Phát hiện {len(violations)} xung đột ràng buộc ở vòng #{attempt}. "
                            "Đang tự động điều chỉnh lịch học..."
                        ),
                    },
                )

            orchestrator = ProposalValidationGateOrchestrator(
                llm_provider=self._llm,
                enable_tier3_judge=self._enable_tier3_judge,
                workflow_repo=self._workflow_repo,
                user_id=user_id,
                goal_id=roadmap.goal_id,
                roadmap_id=roadmap_id,
            )
            valid_mids: set[UUID | str] = {m.id for m in milestones}
            milestone_order_map = {str(m.id): m.sequence_order for m in milestones}
            milestone_summary_for_gate = json.dumps(
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
                    for m in sorted(milestones, key=lambda item: item.sequence_order)
                ],
                ensure_ascii=False,
            )
            gate_result = await orchestrator.generate_and_validate_proposal_with_retry(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_schema=SCHEDULE_PROPOSAL_RESPONSE_SCHEMA,
                availability=avail_config,
                valid_milestone_ids=valid_mids,
                existing_tasks=existing_tasks,
                current_roadmap_target_date=roadmap.target_date,
                goal_title=goal.title if goal is not None else roadmap.title,
                learner_level=prior_knowledge,
                milestone_summary=milestone_summary_for_gate,
                max_retries=max_retries,
                on_retry_callback=_on_retry,
                start_date=roadmap.start_date or effective_now.date(),
                milestone_order_map=milestone_order_map,
                tools=(
                    dispatcher.get_allowed_tool_declarations() if dispatcher is not None else None
                ),
                tool_executor=dispatcher.dispatch if dispatcher is not None else None,
                max_tool_calls=TASK_DECOMPOSER_SKILL.max_tool_calls,
                thinking_level=TASK_DECOMPOSER_SKILL.thinking_level,
                deterministic_allocation=True,
                preferred_session_minutes=learner_profile.opt_session_minutes,
                estimation_bias_beta=float(learner_profile.estimation_bias_beta),
                peak_productivity_slots=getattr(learner_profile, "peak_productivity_slots", ()),
                milestones=milestones,
                resource_resolver=lambda raw_prop: resolve_task_resources_from_tool_results(
                    raw_prop,
                    dispatcher.collected_resources if dispatcher is not None else (),
                    strict=dispatcher is not None,
                ),
                prompt_template=decomposer_tpl,
            )

            await self._sse.append_event(
                job_id=job_id,
                event="chunk",
                status="STREAMING",
                data={
                    "stage": "VALIDATING_TIER_1_2_3",
                    "progress": 85,
                    "delta_text": "Đã hoàn tất phân rã, kiểm định 3 tầng và xếp thời gian biểu tất định. Đang lưu bản đề xuất...",
                    "deltaText": "Đã hoàn tất phân rã, kiểm định 3 tầng và xếp thời gian biểu tất định. Đang lưu bản đề xuất...",
                },
            )

            normalized_data = normalize_proposal_task_ids_and_dependencies(
                gate_result.validated_proposal_data
            )
            normalized_data["availability_mode"] = avail_config.mode
            available_minutes = SpatioTemporalRuleEngine.calculate_available_capacity_minutes(
                avail_config,
                start_date=roadmap.start_date or effective_now.date(),
                target_date=roadmap.target_date,
                existing_tasks=existing_tasks,
            )
            normalized_data["feasibility"] = assess_schedule_feasibility(
                [task for task in normalized_data.get("tasks", []) if isinstance(task, dict)],
                available_minutes=available_minutes,
            ).to_dict()
            normalized_data["availability_source_metadata"] = effective_avail.source_metadata
            if effective_avail.warnings:
                existing_adv = list(normalized_data.get("advisory_warnings", []) or [])
                for w in effective_avail.warnings:
                    if w not in existing_adv:
                        existing_adv.append(w)
                normalized_data["advisory_warnings"] = existing_adv
            normalized_data["attempts_used"] = gate_result.attempts_used
            normalized_data["retry_history"] = list(gate_result.retry_history)
            normalized_data["judge_skipped"] = gate_result.judge_skipped
            normalized_data["judge_status"] = gate_result.judge_status
            normalized_data["is_partial_schedule"] = gate_result.is_partial_schedule
            normalized_data["scheduled_tasks_count"] = gate_result.scheduled_tasks_count
            normalized_data["unscheduled_tasks_count"] = gate_result.unscheduled_tasks_count
            if gate_result.pedagogical_score is not None:
                normalized_data["pedagogical_score"] = gate_result.pedagogical_score
            model_used = getattr(self._llm, "last_model_used", None)
            if model_used:
                normalized_data["model_used"] = model_used
            normalized_data["degraded_model_used"] = bool(
                getattr(self._llm, "last_degraded_model_used", False)
            )

            proposal = ScheduleProposal(
                id=generate_uuid7(),
                roadmap_id=roadmap_id,
                user_id=user_id,
                proposal_data=normalized_data,
                status=ScheduleProposalStatus.DRAFT,
                applied_at=None,
                created_at=effective_now,
                updated_at=effective_now,
            )

            async with self._uow:
                await self._proposal_repo.discard_existing_drafts(roadmap_id, effective_now)
                saved_proposal = await self._proposal_repo.save(proposal)
                billable_completion_tokens = max(
                    int(gate_result.total_completion_tokens or 0),
                    int(gate_result.total_thinking_tokens or 0),
                )
                resolved_model_name = str(
                    model_used or getattr(self._llm, "model_identifier", "gemini-3.8-flash-medium")
                )
                await self._quota_facade.commit_reservation(
                    reservation_id,
                    prompt_tokens=gate_result.total_prompt_tokens,
                    completion_tokens=billable_completion_tokens,
                    model_name=resolved_model_name,
                )
                logger.info(
                    "task_decomposer_completed",
                    extra={
                        "roadmap_id": str(roadmap_id),
                        "proposal_id": str(saved_proposal.id),
                        "model_id": resolved_model_name,
                        "prompt_tokens": gate_result.total_prompt_tokens,
                        "output_tokens": billable_completion_tokens,
                        "completion_tokens": billable_completion_tokens,
                        "thinking_tokens": gate_result.total_thinking_tokens,
                        "attempts_used": gate_result.attempts_used,
                    },
                )
                if self._workflow_repo is not None:
                    wf_run_id = generate_uuid7()
                    await self._workflow_repo.add_run(
                        WorkflowRun(
                            id=wf_run_id,
                            user_id=user_id,
                            workflow_type=WorkflowType.SCHEDULE_GENERATION,
                            current_step="TASK_DECOMPOSER",
                            status=WorkflowStatus.COMPLETED,
                            context_snapshot=compact_context_snapshot(
                                goal_id=roadmap.goal_id,
                                roadmap_id=roadmap_id,
                                stage="TASK_DECOMPOSITION",
                                inputs=harness_inputs,
                                layer_tokens=assembled.layer_tokens,
                                prompt_template=decomposer_tpl,
                            ),
                            started_at=effective_now,
                            goal_id=roadmap.goal_id,
                            roadmap_id=roadmap_id,
                            completed_at=effective_now,
                        )
                    )
                    await self._workflow_repo.add_step(
                        WorkflowStepExecution(
                            id=generate_uuid7(),
                            workflow_run_id=wf_run_id,
                            step_name="TASK_DECOMPOSER",
                            step_order=1,
                            status=WorkflowStepStatus.COMPLETED,
                            input_summary={
                                "milestones_count": len(milestones),
                                "availability_mode": avail_config.mode,
                            },
                            output_payload={
                                "proposal_id": str(saved_proposal.id),
                                "attempts_used": gate_result.attempts_used,
                                "pedagogical_score": gate_result.pedagogical_score,
                                "model_id": resolved_model_name,
                                "prompt_tokens": gate_result.total_prompt_tokens,
                                "output_tokens": billable_completion_tokens,
                                "completion_tokens": billable_completion_tokens,
                                "thinking_tokens": gate_result.total_thinking_tokens,
                            },
                            retry_count=max(0, int(gate_result.attempts_used) - 1),
                            started_at=effective_now,
                            completed_at=effective_now,
                        )
                    )
                await self._uow.commit()

            tasks_list = saved_proposal.proposal_data.get("tasks", [])
            total_minutes = sum(
                int(t.get("estimated_minutes", 0) or 0) for t in tasks_list if isinstance(t, dict)
            )
            await self._sse.append_event(
                job_id=job_id,
                event="completed",
                status="COMPLETED",
                data={
                    "stage": "COMPLETED",
                    "progress": 100,
                    "delta_text": "Hoàn tất sinh đề xuất lịch học chi tiết (DRAFT)!",
                    "deltaText": "Hoàn tất sinh đề xuất lịch học chi tiết (DRAFT)!",
                    "payload": {
                        "proposal_id": str(saved_proposal.id),
                        "roadmap_id": str(roadmap_id),
                        "status": saved_proposal.status.value,
                        "total_tasks": len(tasks_list),
                        "total_planned_minutes": total_minutes,
                        "has_soft_overflow": gate_result.has_soft_overflow,
                        "soft_overflow_warnings": [
                            w.to_dict() for w in gate_result.soft_overflow_warnings
                        ],
                        "judge_status": gate_result.judge_status,
                        "is_partial_schedule": gate_result.is_partial_schedule,
                        "scheduled_tasks_count": gate_result.scheduled_tasks_count,
                        "unscheduled_tasks_count": gate_result.unscheduled_tasks_count,
                        "unscheduled_tasks": normalized_data.get("unscheduled_tasks", []),
                        "attempts_used": gate_result.attempts_used,
                    },
                },
            )
            return saved_proposal

        except Exception as exc:
            try:
                async with self._uow:
                    await self._quota_facade.release_reservation(
                        reservation_id,
                        reason=getattr(exc, "code", "SCHEDULE_PROPOSAL_GEN_FAILED"),
                    )
                    await self._uow.commit()
            except Exception as release_exc:
                logging.getLogger(__name__).warning(
                    "proposal_generation_quota_release_failed",
                    extra={
                        "job_id": str(job_id),
                        "roadmap_id": str(roadmap_id),
                        "error_type": type(release_exc).__name__,
                    },
                )

            await self._sse.append_event(
                job_id=job_id,
                event="failed",
                status="FAILED",
                data={
                    "stage": "FAILED",
                    "progress": 100,
                    "error": str(exc),
                    "error_code": getattr(exc, "code", "SCHEDULE_PROPOSAL_GEN_FAILED"),
                    "violations": getattr(exc, "violations", []),
                },
            )
            raise


class InitiateScheduleProposalGenerationUseCase:
    """Stage 1 Initiator for Level-2 AI ScheduleProposal Generation (`202 Accepted`, UC-08 / FR-PLAN-001)."""

    def __init__(
        self,
        *,
        roadmap_repo: RoadmapRepositoryPort,
        milestone_repo: MilestoneRepositoryPort,
        quota_facade: QuotaFacadePort,
        sse_job_store: SseJobPort,
        uow: AsyncUnitOfWork,
        executor: ExecuteScheduleProposalGenerationUseCase | None = None,
    ) -> None:
        self._roadmap_repo = roadmap_repo
        self._milestone_repo = milestone_repo
        self._quota_facade = quota_facade
        self._sse = sse_job_store
        self._uow = uow
        self._executor = executor

    async def execute(
        self,
        *,
        user_id: UUID,
        roadmap_id: UUID,
        idempotency_key: str | None = None,
        run_inline: bool = True,
    ) -> SseJobTicketDTO:
        roadmap = await self._roadmap_repo.get_by_id_for_user(roadmap_id, user_id)
        if roadmap is None:
            raise RoadmapNotFoundError()

        operation = f"SCHEDULE_PROPOSAL_GEN:{roadmap_id}"
        if idempotency_key and idempotency_key.strip():
            existing_job = await self._sse.get_by_idempotency_key(
                user_id=user_id,
                operation=operation,
                idempotency_key=idempotency_key,
            )
            if existing_job is not None:
                return SseJobTicketDTO(
                    job_id=existing_job.job_id,
                    reservation_id=existing_job.reservation_id,
                    roadmap_id=existing_job.roadmap_id,
                    job_type=existing_job.job_type,
                    status=existing_job.status,
                    stream_url=f"/api/v1/roadmaps/jobs/{existing_job.job_id}/stream",
                    is_existing=True,
                )

        # Enforce FR-PLAN-001 guard BEFORE reserving AI quota
        milestones = await self._milestone_repo.list_by_roadmap_id(roadmap_id)
        if not milestones or any(m.status == MilestoneStatus.PENDING for m in milestones):
            raise UnapprovedMilestonesError()

        async with self._uow:
            reservation_id = await self._quota_facade.reserve_quota(
                user_id=user_id,
                operation_type="SCHEDULE_PROPOSAL_GEN",
                cost=1,
            )
            job_id = generate_uuid7()
            job_record = await self._sse.create_job(
                job_id=job_id,
                user_id=user_id,
                roadmap_id=roadmap_id,
                reservation_id=reservation_id,
                job_type="SCHEDULE_PROPOSAL_GEN",
                operation=operation,
                idempotency_key=idempotency_key,
            )
            await self._sse.append_event(
                job_id=job_id,
                event="stage",
                status="RESERVED",
                data={
                    "stage": "RESERVED",
                    "progress": 10,
                    "delta_text": "Đã giữ chỗ hạn ngạch AI. Đang khởi tạo đề xuất lịch học Cấp 2...",
                    "deltaText": "Đã giữ chỗ hạn ngạch AI. Đang khởi tạo đề xuất lịch học Cấp 2...",
                },
            )
            await self._uow.commit()

        if run_inline and self._executor is not None:
            try:
                await self._executor.execute(
                    job_id=job_id,
                    user_id=user_id,
                    roadmap_id=roadmap_id,
                    reservation_id=reservation_id,
                )
            except Exception as exec_exc:
                logging.getLogger(__name__).warning(
                    "proposal_generation_inline_failed",
                    extra={
                        "job_id": str(job_id),
                        "roadmap_id": str(roadmap_id),
                        "error_type": type(exec_exc).__name__,
                    },
                )

        updated_job = await self._sse.get_job_for_user(job_id=job_id, user_id=user_id)
        return SseJobTicketDTO(
            job_id=job_record.job_id,
            reservation_id=job_record.reservation_id,
            roadmap_id=job_record.roadmap_id,
            job_type=job_record.job_type,
            status=updated_job.status,
            stream_url=f"/api/v1/roadmaps/jobs/{job_record.job_id}/stream",
        )
