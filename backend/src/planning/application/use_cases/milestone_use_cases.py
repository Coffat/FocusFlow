import asyncio
import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from src.account.public_api import (
    AvailabilityQueryPort,
    CalendarConnectionQueryPort,
    LearnerMemoryQueryPort,
    QuotaFacadePort,
    UserQueryPort,
)
from src.execution.public_api import ExecutionScheduleSyncPort
from src.planning.application.dtos.planning_dtos import (
    ApproveMilestonesRequestDTO,
    MilestoneGenerationLLMOutput,
    MilestoneInputItemDTO,
    SseJobTicketDTO,
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
from src.planning.application.ports.sse_job_port import (
    IdempotencySlotClaim,
    SseJobPort,
    claim_idempotency_slot_with_wait,
    sanitize_sse_error_details,
)
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
from src.planning.application.services.learning_quality import (
    GenerationStrategy,
    has_operational_quality_review_failure,
    run_dual_quality_critics,
)
from src.planning.application.services.preliminary_feasibility_service import (
    _verify_preliminary_hash_matches,
    refresh_roadmap_preliminary_feasibility,
    verify_or_refresh_preliminary_feasibility_for_gate,
)
from src.planning.application.services.repo_lock import call_for_update
from src.planning.application.services.roadmap_context_builder import (
    RoadmapContextBuilder,
)
from src.planning.application.services.roadmap_skills import (
    MILESTONE_PLANNER_SKILL,
    build_milestone_planner_prompt,
    build_planning_prompt_registry,
)
from src.planning.application.services.validation_gate import (
    DEFAULT_MAX_RETRIES,
    ProposalValidationGateOrchestrator,
)
from src.planning.domain.exceptions.planning_exceptions import (
    InsufficientCapacityError,
    ProposalValidationGateError,
    RoadmapNotFoundError,
    ScopeApprovalRequiredError,
)
from src.planning.domain.models.milestone import (
    Milestone,
    MilestoneStatus,
    validate_milestone_sequence,
)
from src.planning.domain.services.milestone_effort_allocator import MilestoneEffortAllocator
from src.planning.domain.services.spatio_temporal_engine import SpatioTemporalRuleEngine
from src.planning.domain.services.validation_types import AvailabilityConfigurationDTO
from src.shared_kernel.application.embedding_port import EmbeddingProviderPort
from src.shared_kernel.application.harness.execution_manager import AIExecutionManager
from src.shared_kernel.application.harness.models import WorkflowType
from src.shared_kernel.application.harness.untrusted_context import (
    UntrustedBlockKind,
    format_untrusted_block,
)
from src.shared_kernel.application.harness.workflow_port import WorkflowRepositoryPort
from src.shared_kernel.application.llm_port import LLMProviderPort
from src.shared_kernel.application.uow import AsyncUnitOfWork
from src.shared_kernel.config import get_settings
from src.shared_kernel.domain.base import generate_uuid7

logger = logging.getLogger(__name__)


def _milestone_generation_error_details(exc: Exception) -> tuple[str, str]:
    """Return a stable user-facing error without exposing provider details."""

    if isinstance(exc, (TimeoutError, asyncio.TimeoutError)):
        return (
            "AI_GATEWAY_TIMEOUT",
            "AI mất quá nhiều thời gian phản hồi. Vui lòng thử lại.",
        )
    return (
        str(getattr(exc, "code", "MILESTONE_GEN_FAILED")),
        str(exc).strip() or "Không thể sinh cột mốc học tập bằng AI. Vui lòng thử lại.",
    )


MILESTONE_RESPONSE_SCHEMA: dict[str, Any] = MilestoneGenerationLLMOutput.model_json_schema()


class ExecuteMilestoneGenerationUseCase:
    """Stage 2 Worker / Inline executor for Level-1 AI Milestone Generation (UC-07)."""

    def __init__(
        self,
        *,
        goal_repo: GoalRepositoryPort,
        roadmap_repo: RoadmapRepositoryPort,
        milestone_repo: MilestoneRepositoryPort,
        quota_facade: QuotaFacadePort,
        llm_provider: LLMProviderPort,
        sse_job_store: SseJobPort,
        uow: AsyncUnitOfWork,
        knowledge_base: KnowledgeBasePort | None = None,
        learner_memory_port: LearnerMemoryQueryPort | None = None,
        knowledge_source_repo: KnowledgeSourceRepositoryPort | None = None,
        embedding_provider: EmbeddingProviderPort | None = None,
        workflow_repo: WorkflowRepositoryPort | None = None,
        availability_query_port: AvailabilityQueryPort | None = None,
        execution_sync_port: ExecutionScheduleSyncPort | None = None,
        block_repo: ScheduleBlockRepositoryPort | None = None,
        user_query_port: UserQueryPort | None = None,
        calendar_connection_query_port: CalendarConnectionQueryPort | None = None,
        proposal_repo: ScheduleProposalRepositoryPort | None = None,
    ) -> None:
        self._goal_repo = goal_repo
        self._roadmap_repo = roadmap_repo
        self._milestone_repo = milestone_repo
        self._quota_facade = quota_facade
        self._llm = llm_provider
        self._sse = sse_job_store
        self._uow = uow
        self._kb = knowledge_base
        self._learner_memory_port = learner_memory_port
        self._knowledge_source_repo = knowledge_source_repo
        self._embedding_provider = embedding_provider
        self._workflow_repo = workflow_repo
        self._availability_port = availability_query_port
        self._execution_sync_port = execution_sync_port
        self._block_repo = block_repo
        self._user_query_port = user_query_port
        self._calendar_connection_port = calendar_connection_query_port
        self._proposal_repo = proposal_repo

    async def execute(
        self,
        *,
        job_id: UUID,
        user_id: UUID,
        roadmap_id: UUID,
        reservation_id: UUID,
        max_retries: int = DEFAULT_MAX_RETRIES,
        now: datetime | None = None,
        generation_strategy: str = "FULL_SCOPE",
    ) -> list[Milestone]:
        effective_now = now or datetime.now(UTC)
        reservation_finalized = False

        async def _release_once(reason: str) -> None:
            nonlocal reservation_finalized
            if reservation_finalized:
                return
            reservation_finalized = True
            async with self._uow:
                try:
                    await self._quota_facade.release_reservation(
                        reservation_id,
                        reason=reason,
                    )
                except Exception as rel_exc:
                    if getattr(rel_exc, "code", None) == "QUOTA_RESERVATION_NOT_FOUND" or (
                        type(rel_exc).__name__ == "QuotaReservationNotFoundError"
                    ):
                        return
                    raise
                await self._uow.commit()

        try:
            roadmap = await self._roadmap_repo.get_by_id_for_user(roadmap_id, user_id)
            if roadmap is None:
                raise RoadmapNotFoundError()

            goal = await self._goal_repo.get_by_id(roadmap.goal_id)
            raw_title = goal.title if goal is not None else roadmap.title
            raw_desc = (
                (goal.raw_description or "") if goal is not None else (roadmap.description or "")
            )
            prior_knowledge = goal.prior_knowledge_level if goal is not None else "BEGINNER"
            clarification_ctx = (goal.clarification_context or "") if goal is not None else ""

            sanitized_title = format_untrusted_block(UntrustedBlockKind.GOAL_TITLE, raw_title)
            sanitized_desc = format_untrusted_block(
                UntrustedBlockKind.GOAL_RAW_DESCRIPTION, raw_desc
            )
            sanitized_clarification = (
                format_untrusted_block(UntrustedBlockKind.CLARIFICATION_DATA, clarification_ctx)
                if clarification_ctx
                else ""
            )

            await self._sse.append_event(
                job_id=job_id,
                event="stage",
                status="STREAMING",
                data={
                    "stage": "STREAMING",
                    "progress": 35,
                    "delta_text": "Đang phân tích phạm vi mục tiêu và lập coverage blueprint...",
                    "deltaText": "Đang phân tích phạm vi mục tiêu và lập coverage blueprint...",
                },
            )

            planner_tpl = build_planning_prompt_registry().latest(MILESTONE_PLANNER_SKILL.skill_id)
            system_prompt = planner_tpl.system_template
            if goal is not None:
                (
                    prefetched_concepts,
                    prefetched_graphs,
                ) = await RoadmapContextBuilder.prefetch_milestone_kb_evidence(
                    self._kb,
                    query_text=f"{raw_title} {raw_desc}",
                    learner_level=prior_knowledge,
                )
                context_block = RoadmapContextBuilder.build_milestone_planning_context(
                    goal=goal,
                    roadmap=roadmap,
                    kb_concepts=prefetched_concepts,
                    kb_graphs=prefetched_graphs,
                )
            else:
                prompt_lines = [
                    f"Tiêu đề mục tiêu: {sanitized_title}",
                    f"Mô tả chi tiết: {sanitized_desc}",
                    f"Trình độ đầu vào: {prior_knowledge}",
                ]
                if sanitized_clarification:
                    prompt_lines.append(
                        f"Kết quả phỏng vấn chẩn đoán / Làm rõ nhu cầu:\n{sanitized_clarification}"
                    )
                prompt_lines.extend(
                    [
                        f"Ngày bắt đầu: {roadmap.start_date.isoformat() if roadmap.start_date else 'N/A'}",
                        f"Ngày đích: {roadmap.target_date.isoformat() if roadmap.target_date else 'N/A'}",
                    ]
                )
                context_block = "\n".join(prompt_lines)

            harness_inputs = await load_planning_harness_context_inputs(
                user_id=user_id,
                goal_id=roadmap.goal_id,
                query_text=f"{raw_title} {raw_desc}",
                learner_memory_port=self._learner_memory_port,
                knowledge_source_repo=self._knowledge_source_repo,
                embedding_provider=self._embedding_provider,
            )
            assembled = RoadmapContextBuilder.assemble_harness_context(
                system_instruction=system_prompt,
                workflow_stage="MILESTONE_PLANNING",
                base_context_text=context_block,
                learner_diagnostic={"prior_knowledge_level": prior_knowledge},
                workflow_constraints={
                    "start_date": roadmap.start_date.isoformat() if roadmap.start_date else None,
                    "target_date": roadmap.target_date.isoformat() if roadmap.target_date else None,
                },
                memory_items=harness_inputs.memory_items,
                concept_masteries=harness_inputs.concept_masteries,
                knowledge_chunks=harness_inputs.knowledge_chunks,
                include_planning_context=False,
            )
            effective_context = (
                f"{context_block}\n\n{assembled.text}"
                if (
                    harness_inputs.memory_items
                    or harness_inputs.concept_masteries
                    or harness_inputs.knowledge_chunks
                )
                else context_block
            )

            strategy = GenerationStrategy(generation_strategy)
            base_user_prompt = build_milestone_planner_prompt(
                effective_context,
                generation_strategy=strategy.value,
            )

            settings = get_settings()

            current_prompt = base_user_prompt
            total_prompt_tokens = 0
            total_completion_tokens = 0
            total_thinking_tokens = 0
            last_model_id = str(getattr(self._llm, "model_identifier", "gemini-3.8-flash-medium"))
            max_attempts = max(1, int(max_retries) + 1)
            pipeline_deadline = asyncio.get_running_loop().time() + float(
                settings.ai_sse_pipeline_timeout_seconds
            )
            validated_items: list[dict[str, Any]] = []
            last_violations = []

            # End the pure read-only DB transaction before entering external LLM calls
            # so connections are not held IDLE IN TRANSACTION during inference.
            if hasattr(self._uow, "rollback"):
                await self._uow.rollback()

            for attempt in range(1, max_attempts + 1):
                remaining_seconds = pipeline_deadline - asyncio.get_running_loop().time()
                if remaining_seconds <= 0:
                    raise TimeoutError("Milestone generation exceeded pipeline timeout budget")

                exec_mgr = AIExecutionManager(
                    provider=self._llm,
                    quota=self._quota_facade,
                    manage_quota=False,
                    max_retries=0,
                    workflow_repo=self._workflow_repo,
                    timeout_seconds=min(
                        float(settings.ai_milestone_planner_timeout_seconds), remaining_seconds
                    ),
                    tool_call_timeout_seconds=float(settings.ai_tool_call_timeout_seconds),
                )
                exec_res = await exec_mgr.execute(
                    user_id=user_id,
                    operation_type="MILESTONE_GEN",
                    system_prompt=system_prompt,
                    user_prompt=current_prompt,
                    response_schema=MILESTONE_RESPONSE_SCHEMA,
                    model_name=getattr(self._llm, "model_identifier", "gemini-3.8-flash"),
                    tools=None,
                    tool_executor=None,
                    max_tool_calls=0,
                    thinking_level=MILESTONE_PLANNER_SKILL.thinking_level,
                    existing_reservation_id=reservation_id,
                    commit_on_success=False,
                    release_on_failure=False,
                    workflow_type=WorkflowType.PLAN_CREATION,
                    step_name="CURRICULUM_ARCHITECT",
                    step_order=attempt,
                    goal_id=roadmap.goal_id,
                    roadmap_id=roadmap_id,
                    context_snapshot=compact_context_snapshot(
                        goal_id=roadmap.goal_id,
                        roadmap_id=roadmap_id,
                        stage="MILESTONE_PLANNING",
                        inputs=harness_inputs,
                        layer_tokens=assembled.layer_tokens,
                        prompt_template=planner_tpl,
                    ),
                    prompt_template=planner_tpl,
                )
                raw_result = exec_res.value
                p_tok = exec_res.prompt_tokens
                c_tok = exec_res.completion_tokens
                t_tok = exec_res.thinking_tokens
                if exec_res.model_id:
                    last_model_id = exec_res.model_id
                total_prompt_tokens += int(p_tok or 0)
                total_completion_tokens += int(c_tok or 0)
                total_thinking_tokens += int(t_tok or 0)

                if isinstance(raw_result, list):
                    raw_milestones = raw_result
                elif isinstance(raw_result, dict):
                    raw_milestones = raw_result.get("milestones", [])
                else:
                    raw_milestones = []
                if not isinstance(raw_milestones, list):
                    raw_milestones = []

                violations = ProposalValidationGateOrchestrator.validate_ai_milestones_tier1(
                    raw_milestones
                )
                critic_reports: list[dict[str, Any]] = []
                critic_warnings: list[str] = []
                if not violations:
                    remaining_seconds = pipeline_deadline - asyncio.get_running_loop().time()
                    if remaining_seconds < float(settings.ai_min_critic_remaining_seconds):
                        logger.warning(
                            "milestone_quality_critic_skipped_low_budget",
                            extra={
                                "roadmap_id": str(roadmap_id),
                                "remaining_seconds": round(remaining_seconds, 2),
                                "min_required_seconds": float(
                                    settings.ai_min_critic_remaining_seconds
                                ),
                            },
                        )
                        critic_warnings.append(
                            "Ngân sách thời gian còn lại không đủ cho AI Critic — đã bỏ qua bước Critic và giữ kết quả hợp lệ Tier 1."
                        )
                        critic_reports = [
                            {
                                "critic": "QUALITY_CRITIC",
                                "status": "SKIPPED_LOW_BUDGET",
                                "issues": [],
                            }
                        ]
                    else:
                        critic_timeout = min(
                            float(settings.ai_quality_critic_timeout_seconds), remaining_seconds
                        )
                        arbiter_timeout = min(
                            float(settings.ai_quality_arbiter_timeout_seconds), remaining_seconds
                        )
                        critic_tokens: dict[str, int] = {}
                        try:
                            (
                                critic_violations,
                                critic_reports,
                                critic_p,
                                critic_c,
                            ) = await asyncio.wait_for(
                                run_dual_quality_critics(
                                    self._llm,
                                    stage="MILESTONE_PLANNING",
                                    payload={"milestones": raw_milestones},
                                    context=context_block,
                                    learner_level=prior_knowledge,
                                    timeout_seconds=critic_timeout,
                                    arbiter_timeout_seconds=arbiter_timeout,
                                    workflow_repo=self._workflow_repo,
                                    user_id=user_id,
                                    goal_id=roadmap.goal_id,
                                    roadmap_id=roadmap_id,
                                    workflow_type=WorkflowType.PLAN_CREATION,
                                    token_accumulator=critic_tokens,
                                    quota=self._quota_facade,
                                ),
                                timeout=remaining_seconds,
                            )
                            total_prompt_tokens += critic_p
                            total_completion_tokens += critic_c
                            total_thinking_tokens += int(critic_tokens.get("thinking_tokens", 0))
                            if has_operational_quality_review_failure(critic_violations):
                                logger.warning(
                                    "milestone_quality_critic_degraded",
                                    extra={"roadmap_id": str(roadmap_id)},
                                )
                                critic_warnings.append(
                                    "AI Critic tạm thời quá thời gian chờ — đã tiếp tục với kết quả hợp lệ Tier 1."
                                )
                                critic_violations = [
                                    v
                                    for v in critic_violations
                                    if v.rule_code
                                    not in {
                                        "QUALITY_CRITIC_UNAVAILABLE",
                                        "QUALITY_ARBITER_UNAVAILABLE",
                                    }
                                ]
                            violations.extend(critic_violations)
                        except TimeoutError:
                            logger.warning(
                                "milestone_quality_critic_timeout_skipped",
                                extra={"roadmap_id": str(roadmap_id)},
                            )
                            critic_warnings.append(
                                "AI Critic hết ngân sách thời gian — đã bỏ qua bước Critic và giữ kết quả hợp lệ Tier 1."
                            )
                            critic_reports = [
                                {
                                    "critic": "QUALITY_CRITIC",
                                    "status": "SKIPPED_LOW_BUDGET",
                                    "issues": [],
                                }
                            ]
                if not violations:
                    validated_items = list(raw_milestones)
                    roadmap.planning_metadata = {
                        **roadmap.planning_metadata,
                        "generation_strategy": strategy.value,
                        "quality_reviews": critic_reports,
                        **({"advisory_warnings": critic_warnings} if critic_warnings else {}),
                        "scope_summary": raw_result.get("scope_summary", "")
                        if isinstance(raw_result, dict)
                        else "",
                        "deferred_scope": raw_result.get("deferred_scope", [])
                        if isinstance(raw_result, dict)
                        else [],
                    }
                    break

                last_violations = violations
                remaining_for_retry = pipeline_deadline - asyncio.get_running_loop().time()
                if attempt < max_attempts and remaining_for_retry >= float(
                    settings.ai_min_retry_remaining_seconds
                ):
                    await self._sse.append_event(
                        job_id=job_id,
                        event="validation_retry",
                        status="STREAMING",
                        data={
                            "stage": "VALIDATING_TIER_1_2_3",
                            "progress": min(85, 50 + attempt * 15),
                            "retry_attempt": attempt,
                            "violations": [v.to_dict() for v in violations],
                            "delta_text": f"Tự động điều chỉnh cấu trúc cột mốc (vòng thử #{attempt})...",
                            "deltaText": f"Tự động điều chỉnh cấu trúc cột mốc (vòng thử #{attempt})...",
                        },
                    )
                    current_prompt = (
                        ProposalValidationGateOrchestrator.build_self_correction_prompt(
                            base_user_prompt,
                            violations,
                            attempt_number=attempt,
                        )
                    )
                else:
                    break

            if not validated_items:
                raise ProposalValidationGateError(
                    message="AI không thể sinh danh sách cột mốc thích ứng, đầy đủ và tuần tự sau khi tự sửa lỗi.",
                    code="AI_SCHEMA_VALIDATION_ERROR",
                    violations=[v.to_dict() for v in last_violations],
                )

            await self._sse.append_event(
                job_id=job_id,
                event="chunk",
                status="STREAMING",
                data={
                    "stage": "VALIDATING_TIER_1_2_3",
                    "progress": 80,
                    "delta_text": f"Đã kiểm định {len(validated_items)} cột mốc học tập. Đang lưu bản nháp...",
                    "deltaText": f"Đã kiểm định {len(validated_items)} cột mốc học tập. Đang lưu bản nháp...",
                },
            )

            sorted_items = sorted(
                validated_items,
                key=lambda item: int(item.get("sequence_order", 0) or 0),
            )
            generated_ids = [generate_uuid7() for _ in sorted_items]
            seq_to_id = {idx: generated_ids[idx - 1] for idx in range(1, len(sorted_items) + 1)}
            raw_seq_to_normalized_seq = {
                int(item.get("sequence_order", idx) or idx): idx
                for idx, item in enumerate(sorted_items, start=1)
            }

            prelim_dict: dict[str, Any] | None = None
            efforts_by_seq: dict[int, int] = {}
            if getattr(settings, "milestone_effort_allocator_enabled", True):
                p_hard: int | None = None
                avail_cfg: AvailabilityConfigurationDTO | None = None
                effective_existing: Sequence[Any] = ()
                effective_start = roadmap.start_date or effective_now.date()
                if roadmap.target_date is not None and self._availability_port is not None:
                    user_tz = "Asia/Ho_Chi_Minh"
                    if self._user_query_port is not None:
                        user_snap = await self._user_query_port.get_user_by_id(user_id)
                        if user_snap is not None and user_snap.timezone:
                            user_tz = user_snap.timezone
                    existing_tasks: list[Any] = []
                    if self._execution_sync_port is not None:
                        active_roadmaps = await self._roadmap_repo.list_by_user_id(
                            user_id, status="ACTIVE"
                        )
                        other_roadmaps = [r for r in active_roadmaps if r.id != roadmap_id]
                        other_ids = [r.id for r in other_roadmaps]
                        target_dates_map = {r.id: r.target_date for r in other_roadmaps}
                        existing_tasks = list(
                            await self._execution_sync_port.get_tasks_for_roadmaps(
                                other_ids,
                                roadmap_target_dates=target_dates_map,
                            )
                        )
                        if self._block_repo is not None:
                            existing_tasks = expand_existing_schedule_occupancy(
                                existing_tasks,
                                await self._block_repo.list_by_roadmap_ids(other_ids),
                            )
                    effective_avail = await GetEffectiveAvailabilityUseCase(
                        availability_query_port=self._availability_port,
                        calendar_connection_query_port=self._calendar_connection_port,
                        execution_sync_port=self._execution_sync_port,
                    ).execute(
                        user_id=user_id,
                        start_date=effective_start,
                        target_date=roadmap.target_date,
                        timezone=user_tz,
                        existing_tasks=existing_tasks,
                        exclude_roadmap_id=roadmap_id,
                    )
                    avail_cfg = effective_avail.availability_config
                    effective_existing = effective_avail.effective_existing_tasks
                    p_hard, _ = SpatioTemporalRuleEngine.calculate_hard_packable_capacity(
                        avail_cfg,
                        start_date=effective_start,
                        target_date=roadmap.target_date,
                        existing_tasks=effective_existing,
                    )

                prev_prelim = (
                    roadmap.planning_metadata.get("preliminary_feasibility")
                    if isinstance(roadmap.planning_metadata, dict)
                    else None
                )
                prev_version = (
                    int(prev_prelim.get("scope_proposal_version") or 0)
                    if isinstance(prev_prelim, dict)
                    else 0
                )
                allocator_inputs = [
                    {
                        **item,
                        "sequence_order": idx,
                        "milestone_id": str(generated_ids[idx - 1]),
                        "dependencies": [
                            raw_seq_to_normalized_seq[int(dep)]
                            for dep in (item.get("dependencies") or [])
                            if isinstance(dep, (int, str))
                            and str(dep).isdigit()
                            and int(dep) in raw_seq_to_normalized_seq
                        ],
                        "prerequisite_milestone_ids": [
                            str(seq_to_id[raw_seq_to_normalized_seq[int(dep)]])
                            for dep in (item.get("dependencies") or [])
                            if isinstance(dep, (int, str))
                            and str(dep).isdigit()
                            and int(dep) in raw_seq_to_normalized_seq
                            and raw_seq_to_normalized_seq[int(dep)] != idx
                        ],
                    }
                    for idx, item in enumerate(sorted_items, start=1)
                ]
                prelim_res = MilestoneEffortAllocator.allocate(
                    allocator_inputs,
                    hard_packable_capacity_minutes=p_hard,
                    prior_knowledge_level=prior_knowledge,
                    target_utilization=float(
                        getattr(settings, "ai_milestone_target_utilization", 0.85)
                    ),
                    gamma_min=float(getattr(settings, "ai_milestone_min_effort_ratio", 0.65)),
                    alpha_by_level={
                        "BEGINNER": float(getattr(settings, "ai_milestone_alpha_beginner", 1.15)),
                        "INTERMEDIATE": float(
                            getattr(settings, "ai_milestone_alpha_intermediate", 1.00)
                        ),
                        "ADVANCED": float(getattr(settings, "ai_milestone_alpha_advanced", 0.85)),
                    },
                    previous_scope_proposal_version=prev_version,
                    start_date=effective_start,
                    target_date=roadmap.target_date,
                    availability=avail_cfg,
                    existing_tasks=effective_existing,
                )
                prelim_dict = prelim_res.to_metadata_dict()
                for bd in prelim_res.breakdowns:
                    efforts_by_seq[bd.sequence_order] = (
                        bd.normalized_planned_effort_minutes
                        if bd.kept_in_scope and bd.normalized_planned_effort_minutes > 0
                        else bd.estimated_effort_minutes
                    )
                updated_meta = {
                    **roadmap.planning_metadata,
                    "preliminary_feasibility": prelim_dict,
                }
                if prelim_res.status == "FIT_CAPACITY_REQUIRES_APPROVAL":
                    updated_meta["deferred_scope"] = [
                        str(item.get("title", "")) for item in prelim_res.deferred_scope
                    ]
                    if not str(updated_meta.get("scope_summary", "")).startswith("FIT_CAPACITY"):
                        updated_meta["scope_summary"] = (
                            f"FIT_CAPACITY (chờ xác nhận v{prelim_res.scope_proposal_version}): "
                            + str(updated_meta.get("scope_summary") or "")
                        ).strip()
                roadmap.planning_metadata = updated_meta
            else:
                if (
                    isinstance(roadmap.planning_metadata, dict)
                    and "preliminary_feasibility" in roadmap.planning_metadata
                ):
                    cleaned_meta = dict(roadmap.planning_metadata)
                    cleaned_meta.pop("preliminary_feasibility", None)
                    roadmap.planning_metadata = cleaned_meta

            new_milestones = [
                Milestone(
                    id=generated_ids[idx - 1],
                    roadmap_id=roadmap_id,
                    sequence_order=idx,
                    title=str(item.get("title", "")).strip(),
                    description=(
                        str(item.get("description")).strip()
                        if item.get("description") is not None
                        else None
                    ),
                    learning_outcomes=tuple(
                        str(value).strip()
                        for value in item.get("learning_outcomes", [])
                        if str(value).strip()
                    ),
                    completion_criteria=str(item.get("completion_criteria", "")).strip() or None,
                    estimated_effort_minutes=efforts_by_seq.get(
                        idx,
                        int(item.get("estimated_effort_minutes", 60) or 60),
                    ),
                    required_concepts=tuple(
                        str(value).strip()
                        for value in item.get("required_concepts", [])
                        if str(value).strip()
                    ),
                    unverified_concepts=tuple(
                        str(value).strip()
                        for value in item.get("unverified_concepts", [])
                        if str(value).strip()
                    ),
                    prerequisite_milestone_ids=tuple(
                        seq_to_id[raw_seq_to_normalized_seq[int(dep)]]
                        for dep in (item.get("dependencies") or [])
                        if isinstance(dep, (int, str))
                        and str(dep).isdigit()
                        and int(dep) in raw_seq_to_normalized_seq
                        and raw_seq_to_normalized_seq[int(dep)] != idx
                    ),
                    status=MilestoneStatus.PENDING,
                    created_at=effective_now,
                    updated_at=effective_now,
                )
                for idx, item in enumerate(sorted_items, start=1)
            ]
            validate_milestone_sequence(new_milestones, enforce_ai_bounds=True)

            async with self._uow:
                saved_milestones = await self._milestone_repo.save_many(roadmap_id, new_milestones)
                await self._roadmap_repo.save(roadmap)
                if self._proposal_repo is not None:
                    await self._proposal_repo.discard_existing_drafts(roadmap_id, effective_now)
                billable_completion_tokens = max(total_completion_tokens, total_thinking_tokens)
                await self._quota_facade.commit_reservation(
                    reservation_id,
                    prompt_tokens=total_prompt_tokens,
                    completion_tokens=billable_completion_tokens,
                    model_name=last_model_id,
                )
                await self._uow.commit()
            reservation_finalized = True
            logger.info(
                "milestone_generation_completed",
                extra={
                    "roadmap_id": str(roadmap_id),
                    "model_id": last_model_id,
                    "prompt_tokens": total_prompt_tokens,
                    "output_tokens": billable_completion_tokens,
                    "completion_tokens": billable_completion_tokens,
                    "thinking_tokens": total_thinking_tokens,
                    "milestones_count": len(saved_milestones),
                },
            )

            milestones_payload = [
                {
                    "id": str(m.id),
                    "roadmap_id": str(m.roadmap_id),
                    "sequence_order": m.sequence_order,
                    "title": m.title,
                    "description": m.description,
                    "learning_outcomes": list(m.learning_outcomes),
                    "completion_criteria": m.completion_criteria,
                    "estimated_effort_minutes": m.estimated_effort_minutes,
                    "required_concepts": list(m.required_concepts),
                    "unverified_concepts": list(m.unverified_concepts),
                    "status": m.status.value,
                }
                for m in saved_milestones
            ]
            completed_payload: dict[str, Any] = {
                "roadmap_id": str(roadmap_id),
                "milestones": milestones_payload,
            }
            if prelim_dict is not None:
                completed_payload["preliminary_feasibility"] = prelim_dict
            await self._sse.append_event(
                job_id=job_id,
                event="completed",
                status="COMPLETED",
                data={
                    "stage": "COMPLETED",
                    "progress": 100,
                    "delta_text": "Hoàn tất phân rã cột mốc học tập!",
                    "deltaText": "Hoàn tất phân rã cột mốc học tập!",
                    "payload": completed_payload,
                },
            )
            return saved_milestones

        except asyncio.CancelledError:

            async def _cancel_cleanup() -> None:
                await _release_once("CANCELLED")
                await self._sse.append_event(
                    job_id=job_id,
                    event="failed",
                    status="FAILED",
                    data={
                        "stage": "FAILED",
                        "progress": 100,
                        "error": "Yêu cầu tạo cột mốc học tập đã bị hủy.",
                        "error_code": "CANCELLED",
                    },
                )

            try:
                await asyncio.shield(_cancel_cleanup())
            except Exception as release_exc:
                logging.getLogger(__name__).warning(
                    "milestone_generation_cancel_release_failed",
                    extra={
                        "job_id": str(job_id),
                        "roadmap_id": str(roadmap_id),
                        "error_type": type(release_exc).__name__,
                    },
                )
            raise

        except Exception as exc:
            error_code, error_message = sanitize_sse_error_details(
                exc,
                default_code="MILESTONE_GEN_FAILED",
                default_message="Không thể sinh cột mốc học tập bằng AI. Vui lòng thử lại.",
            )
            try:
                await _release_once(error_code)
            except Exception as release_exc:
                logging.getLogger(__name__).warning(
                    "milestone_generation_quota_release_failed",
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
                    "error": error_message,
                    "error_code": error_code,
                },
            )
            raise


class InitiateMilestoneGenerationUseCase:
    """Stage 1 Initiator for Level-1 AI Milestone Generation (`202 Accepted`, ADR-005 / UC-07)."""

    def __init__(
        self,
        *,
        roadmap_repo: RoadmapRepositoryPort,
        quota_facade: QuotaFacadePort,
        sse_job_store: SseJobPort,
        uow: AsyncUnitOfWork,
        executor: ExecuteMilestoneGenerationUseCase | None = None,
    ) -> None:
        self._roadmap_repo = roadmap_repo
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
        generation_strategy: str = "FULL_SCOPE",
    ) -> SseJobTicketDTO:
        roadmap = await self._roadmap_repo.get_by_id_for_user(roadmap_id, user_id)
        if roadmap is None:
            raise RoadmapNotFoundError()

        strategy = GenerationStrategy(generation_strategy)
        operation = f"MILESTONE_GEN:{strategy.value}:{roadmap_id}"
        cleaned_key = (
            idempotency_key.strip() if idempotency_key and idempotency_key.strip() else None
        )
        claim: IdempotencySlotClaim | None = None
        if cleaned_key is not None:
            claim, existing_job = await claim_idempotency_slot_with_wait(
                self._sse,
                user_id=user_id,
                operation=operation,
                idempotency_key=cleaned_key,
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

        committed = False
        try:
            async with self._uow:
                reservation_id = await self._quota_facade.reserve_quota(
                    user_id=user_id,
                    operation_type="MILESTONE_GEN",
                    cost=1,
                )
                job_id = generate_uuid7()
                job_record = await self._sse.create_job(
                    job_id=job_id,
                    user_id=user_id,
                    roadmap_id=roadmap_id,
                    reservation_id=reservation_id,
                    job_type=f"MILESTONE_GEN:{strategy.value}",
                    operation=operation,
                    idempotency_key=cleaned_key,
                    register_idempotency=False,
                )
                await self._sse.append_event(
                    job_id=job_id,
                    event="stage",
                    status="RESERVED",
                    data={
                        "stage": "RESERVED",
                        "progress": 10,
                        "delta_text": "Đã giữ chỗ hạn ngạch AI. Bắt đầu phân rã cột mốc...",
                        "deltaText": "Đã giữ chỗ hạn ngạch AI. Bắt đầu phân rã cột mốc...",
                    },
                )
                await self._uow.commit()
                committed = True
            if cleaned_key is not None and claim is not None and claim.token is not None:
                await self._sse.finalize_idempotency_slot(
                    user_id=user_id,
                    operation=operation,
                    idempotency_key=cleaned_key,
                    token=claim.token,
                    job_id=job_id,
                )
        except BaseException:
            if (
                not committed
                and cleaned_key is not None
                and claim is not None
                and claim.token is not None
            ):
                try:
                    await self._sse.release_idempotency_slot(
                        user_id=user_id,
                        operation=operation,
                        idempotency_key=cleaned_key,
                        token=claim.token,
                    )
                except Exception:
                    pass
            raise

        if run_inline and self._executor is not None:
            try:
                await self._executor.execute(
                    job_id=job_id,
                    user_id=user_id,
                    roadmap_id=roadmap_id,
                    reservation_id=reservation_id,
                    generation_strategy=strategy.value,
                )
            except Exception as exec_exc:
                # Error is already recorded in the SSE job stream and quota is released
                logging.getLogger(__name__).warning(
                    "milestone_generation_inline_failed",
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


class UpdateMilestonesUseCase:
    """Add, edit, delete, and reorder Milestones for a Roadmap (UC-07 / FR-PLAN-001)."""

    def __init__(
        self,
        *,
        roadmap_repo: RoadmapRepositoryPort,
        milestone_repo: MilestoneRepositoryPort,
        uow: AsyncUnitOfWork,
        goal_repo: GoalRepositoryPort | None = None,
        proposal_repo: ScheduleProposalRepositoryPort | None = None,
        availability_query_port: AvailabilityQueryPort | None = None,
        execution_sync_port: ExecutionScheduleSyncPort | None = None,
        user_query_port: UserQueryPort | None = None,
        block_repo: ScheduleBlockRepositoryPort | None = None,
        calendar_connection_query_port: CalendarConnectionQueryPort | None = None,
    ) -> None:
        self._roadmap_repo = roadmap_repo
        self._milestone_repo = milestone_repo
        self._uow = uow
        self._goal_repo = goal_repo
        self._proposal_repo = proposal_repo
        self._availability_port = availability_query_port
        self._execution_sync_port = execution_sync_port
        self._user_query_port = user_query_port
        self._block_repo = block_repo
        self._calendar_connection_port = calendar_connection_query_port

    async def execute(
        self,
        *,
        user_id: UUID,
        roadmap_id: UUID,
        items: Sequence[MilestoneInputItemDTO],
        now: datetime | None = None,
    ) -> list[Milestone]:
        effective_now = now or datetime.now(UTC)
        roadmap = await self._roadmap_repo.get_by_id_for_user(roadmap_id, user_id)
        if roadmap is None:
            raise RoadmapNotFoundError()

        existing = await self._milestone_repo.list_by_roadmap_id(roadmap_id)
        existing_by_id = {m.id: m for m in existing}

        milestones: list[Milestone] = []
        for idx, item in enumerate(items, start=1):
            seq = item.sequence_order if item.sequence_order >= 1 else idx
            prev = existing_by_id.get(item.milestone_id) if item.milestone_id else None
            milestones.append(
                Milestone(
                    id=prev.id if prev is not None else (item.milestone_id or generate_uuid7()),
                    roadmap_id=roadmap_id,
                    sequence_order=seq,
                    title=item.title,
                    description=item.description,
                    learning_outcomes=(
                        item.learning_outcomes
                        if item.learning_outcomes
                        else (prev.learning_outcomes if prev is not None else ())
                    ),
                    completion_criteria=(
                        item.completion_criteria
                        if item.completion_criteria is not None
                        else (prev.completion_criteria if prev is not None else None)
                    ),
                    estimated_effort_minutes=(
                        item.estimated_effort_minutes
                        if item.estimated_effort_minutes is not None
                        else (prev.estimated_effort_minutes if prev is not None else 60)
                    ),
                    required_concepts=(
                        item.required_concepts
                        if item.required_concepts
                        else (prev.required_concepts if prev is not None else ())
                    ),
                    unverified_concepts=(
                        item.unverified_concepts
                        if item.unverified_concepts
                        else (prev.unverified_concepts if prev is not None else ())
                    ),
                    prerequisite_milestone_ids=item.prerequisite_milestone_ids,
                    status=prev.status if prev is not None else MilestoneStatus.PENDING,
                    created_at=prev.created_at if prev is not None else effective_now,
                    updated_at=effective_now,
                )
            )

        validate_milestone_sequence(milestones, enforce_ai_bounds=False)

        milestones_changed = len(milestones) != len(existing) or any(
            (
                m.id != e.id
                or m.sequence_order != e.sequence_order
                or m.title != e.title
                or m.learning_outcomes != e.learning_outcomes
                or m.completion_criteria != e.completion_criteria
                or m.estimated_effort_minutes != e.estimated_effort_minutes
                or m.required_concepts != e.required_concepts
                or m.unverified_concepts != e.unverified_concepts
                or m.prerequisite_milestone_ids != e.prerequisite_milestone_ids
            )
            for m, e in zip(milestones, existing, strict=True)
        )

        refresh_res = await refresh_roadmap_preliminary_feasibility(
            user_id=user_id,
            roadmap=roadmap,
            milestones=milestones,
            goal_repo=self._goal_repo,
            roadmap_repo=self._roadmap_repo,
            proposal_repo=None,
            availability_query_port=self._availability_port,
            execution_sync_port=self._execution_sync_port,
            block_repo=self._block_repo,
            user_query_port=self._user_query_port,
            calendar_connection_query_port=self._calendar_connection_port,
            force_recompute=True,
            discard_drafts_on_change=False,
            now=effective_now,
        )
        roadmap_dirty = refresh_res.roadmap_dirty

        # Fallback invalidation when allocator disabled / no availability & no prior prelim
        if not roadmap_dirty:
            raw_prelim = (
                roadmap.planning_metadata.get("preliminary_feasibility")
                if (
                    getattr(get_settings(), "milestone_effort_allocator_enabled", True)
                    and isinstance(roadmap.planning_metadata, dict)
                )
                else None
            )
            if isinstance(raw_prelim, dict) and bool(raw_prelim.get("requires_learner_approval")):
                updated_prelim = {
                    **raw_prelim,
                    "scope_approval_status": "PENDING_LEARNER_APPROVAL",
                    "approved_scope_version": None,
                }
                roadmap.planning_metadata = {
                    **roadmap.planning_metadata,
                    "preliminary_feasibility": updated_prelim,
                }
                roadmap.updated_at = effective_now
                roadmap_dirty = True
                for m in milestones:
                    m.reset_to_pending(effective_now)

        async with self._uow:
            locked_roadmap = await call_for_update(
                self._roadmap_repo.get_by_id_for_user, roadmap_id, user_id
            )
            if locked_roadmap is None:
                raise RoadmapNotFoundError()
            if roadmap_dirty:
                locked_roadmap.planning_metadata = roadmap.planning_metadata
                locked_roadmap.updated_at = roadmap.updated_at
            saved = await self._milestone_repo.save_many(roadmap_id, milestones)
            if roadmap_dirty:
                await self._roadmap_repo.save(locked_roadmap)
            if self._proposal_repo is not None and (milestones_changed or refresh_res.drifted):
                await self._proposal_repo.discard_existing_drafts(roadmap_id, effective_now)
            await self._uow.commit()

        return saved


class ApproveMilestonesUseCase:
    """Approve Level-1 Milestones of a Roadmap (enforcing versioned FIT_CAPACITY approval)."""

    def __init__(
        self,
        *,
        roadmap_repo: RoadmapRepositoryPort,
        milestone_repo: MilestoneRepositoryPort,
        uow: AsyncUnitOfWork,
        goal_repo: GoalRepositoryPort | None = None,
        proposal_repo: ScheduleProposalRepositoryPort | None = None,
        availability_query_port: AvailabilityQueryPort | None = None,
        execution_sync_port: ExecutionScheduleSyncPort | None = None,
        user_query_port: UserQueryPort | None = None,
        block_repo: ScheduleBlockRepositoryPort | None = None,
        calendar_connection_query_port: CalendarConnectionQueryPort | None = None,
    ) -> None:
        self._roadmap_repo = roadmap_repo
        self._milestone_repo = milestone_repo
        self._uow = uow
        self._goal_repo = goal_repo
        self._proposal_repo = proposal_repo
        self._availability_port = availability_query_port
        self._execution_sync_port = execution_sync_port
        self._user_query_port = user_query_port
        self._block_repo = block_repo
        self._calendar_connection_port = calendar_connection_query_port

    async def execute(
        self,
        *,
        user_id: UUID,
        roadmap_id: UUID,
        request: ApproveMilestonesRequestDTO | None = None,
        confirmed_scope_proposal_version: int | None = None,
        accept_fit_capacity: bool = False,
        now: datetime | None = None,
    ) -> list[Milestone]:
        effective_now = now or datetime.now(UTC)
        roadmap = await self._roadmap_repo.get_by_id_for_user(roadmap_id, user_id)
        if roadmap is None:
            raise RoadmapNotFoundError()

        current_milestones = await self._milestone_repo.list_by_roadmap_id(roadmap_id)
        validate_milestone_sequence(current_milestones, enforce_ai_bounds=False)

        eff_accept = request.accept_fit_capacity if request is not None else accept_fit_capacity
        eff_version = (
            request.confirmed_scope_proposal_version
            if request is not None
            else confirmed_scope_proposal_version
        )

        # Synchronous drift verification (checks live availability, target_date, milestones & hash)
        await verify_or_refresh_preliminary_feasibility_for_gate(
            user_id=user_id,
            roadmap=roadmap,
            milestones=current_milestones,
            goal_repo=self._goal_repo,
            roadmap_repo=self._roadmap_repo,
            milestone_repo=self._milestone_repo,
            proposal_repo=self._proposal_repo,
            availability_query_port=self._availability_port,
            execution_sync_port=self._execution_sync_port,
            block_repo=self._block_repo,
            user_query_port=self._user_query_port,
            calendar_connection_query_port=self._calendar_connection_port,
            uow=self._uow,
            raise_on_stale_fit_capacity=True,
            now=effective_now,
        )

        raw_prelim = (
            roadmap.planning_metadata.get("preliminary_feasibility")
            if (
                getattr(get_settings(), "milestone_effort_allocator_enabled", True)
                and isinstance(roadmap.planning_metadata, dict)
            )
            else None
        )
        if isinstance(raw_prelim, dict):
            prelim_status = str(raw_prelim.get("status") or "")
            if prelim_status == "PRELIMINARY_UNSCHEDULABLE":
                raise InsufficientCapacityError(
                    preliminary_feasibility=raw_prelim,
                    hard_packable_capacity_minutes=int(
                        raw_prelim.get("hard_packable_capacity_minutes") or 0
                    ),
                )

            requires_approval = bool(raw_prelim.get("requires_learner_approval", False))
            approval_status = str(raw_prelim.get("scope_approval_status") or "NOT_REQUIRED")
            raw_ver = raw_prelim.get("scope_proposal_version")
            current_version = int(raw_ver) if isinstance(raw_ver, int) else None
            raw_hash = raw_prelim.get("scope_proposal_hash")
            proposal_hash = str(raw_hash) if raw_hash is not None else None

            if requires_approval or prelim_status == "FIT_CAPACITY_REQUIRES_APPROVAL":
                kept_scope_items = [
                    item
                    for item in (raw_prelim.get("kept_scope") or [])
                    if isinstance(item, dict) and "sequence_order" in item
                ]
                deferred_scope_items = [
                    item
                    for item in (raw_prelim.get("deferred_scope") or [])
                    if isinstance(item, dict) and "sequence_order" in item
                ]
                if current_version is not None and proposal_hash:
                    if not _verify_preliminary_hash_matches(
                        raw_prelim,
                        version=current_version,
                        status="FIT_CAPACITY_REQUIRES_APPROVAL",
                        kept_scope_items=kept_scope_items,
                        deferred_scope_items=deferred_scope_items,
                    ):
                        raise ScopeApprovalRequiredError(
                            preliminary_feasibility=raw_prelim,
                            scope_proposal_version=current_version,
                            scope_proposal_hash=proposal_hash,
                            message="Đề xuất phạm vi FIT_CAPACITY đã thay đổi (hash không khớp). Vui lòng xác nhận lại phiên bản mới nhất.",
                        )

                if approval_status == "APPROVED_BY_LEARNER":
                    approved_ver = raw_prelim.get("approved_scope_version")
                    if (
                        approved_ver is not None
                        and current_version is not None
                        and int(approved_ver) == current_version
                        and (eff_version is None or eff_version == current_version)
                    ):
                        # Idempotent re-approval of already-approved fresh FIT_CAPACITY scope
                        return current_milestones
                    raise ScopeApprovalRequiredError(
                        preliminary_feasibility=raw_prelim,
                        scope_proposal_version=current_version,
                        scope_proposal_hash=proposal_hash,
                    )

                if (
                    not eff_accept
                    or eff_version is None
                    or current_version is None
                    or eff_version != current_version
                ):
                    raise ScopeApprovalRequiredError(
                        preliminary_feasibility=raw_prelim,
                        scope_proposal_version=current_version,
                        scope_proposal_hash=proposal_hash,
                    )

                kept_orders = {int(item["sequence_order"]) for item in kept_scope_items}
                if not kept_orders:
                    raise InsufficientCapacityError(
                        preliminary_feasibility=raw_prelim,
                        hard_packable_capacity_minutes=int(
                            raw_prelim.get("hard_packable_capacity_minutes") or 0
                        ),
                    )

                updated_prelim = {
                    **raw_prelim,
                    "scope_approval_status": "APPROVED_BY_LEARNER",
                    "approved_scope_version": current_version,
                }
                roadmap.planning_metadata = {
                    **roadmap.planning_metadata,
                    "preliminary_feasibility": updated_prelim,
                }
                roadmap.updated_at = effective_now

                for milestone in current_milestones:
                    if milestone.sequence_order in kept_orders:
                        milestone.approve(effective_now)
                    else:
                        milestone.reset_to_pending(effective_now)

                async with self._uow:
                    locked_roadmap = await call_for_update(
                        self._roadmap_repo.get_by_id_for_user, roadmap_id, user_id
                    )
                    if locked_roadmap is None:
                        raise RoadmapNotFoundError()
                    locked_prelim = (
                        locked_roadmap.planning_metadata.get("preliminary_feasibility")
                        if isinstance(locked_roadmap.planning_metadata, dict)
                        else None
                    )
                    if isinstance(locked_prelim, dict) and current_version is not None:
                        locked_ver = locked_prelim.get("scope_proposal_version")
                        locked_hash = (
                            str(locked_prelim.get("scope_proposal_hash"))
                            if locked_prelim.get("scope_proposal_hash") is not None
                            else None
                        )
                        if locked_ver != current_version or (
                            proposal_hash and locked_hash != proposal_hash
                        ):
                            raise ScopeApprovalRequiredError(
                                preliminary_feasibility=locked_prelim,
                                scope_proposal_version=(
                                    int(locked_ver)
                                    if isinstance(locked_ver, int)
                                    else current_version
                                ),
                                scope_proposal_hash=locked_hash or proposal_hash or "",
                            )
                    locked_roadmap.planning_metadata = {
                        **(
                            locked_roadmap.planning_metadata
                            if isinstance(locked_roadmap.planning_metadata, dict)
                            else {}
                        ),
                        "preliminary_feasibility": updated_prelim,
                    }
                    locked_roadmap.updated_at = effective_now

                    saved_milestones = await self._milestone_repo.save_many(
                        roadmap_id, current_milestones
                    )
                    await self._roadmap_repo.save(locked_roadmap)
                    await self._uow.commit()
                return saved_milestones

        async with self._uow:
            locked_roadmap = await call_for_update(
                self._roadmap_repo.get_by_id_for_user, roadmap_id, user_id
            )
            if locked_roadmap is None:
                raise RoadmapNotFoundError()
            locked_prelim = (
                locked_roadmap.planning_metadata.get("preliminary_feasibility")
                if isinstance(locked_roadmap.planning_metadata, dict)
                else None
            )
            if isinstance(locked_prelim, dict):
                locked_status = str(locked_prelim.get("status") or "")
                if locked_status == "PRELIMINARY_UNSCHEDULABLE":
                    raise InsufficientCapacityError(
                        preliminary_feasibility=locked_prelim,
                        hard_packable_capacity_minutes=int(
                            locked_prelim.get("hard_packable_capacity_minutes") or 0
                        ),
                    )
                if (
                    bool(locked_prelim.get("requires_learner_approval", False))
                    or locked_status == "FIT_CAPACITY_REQUIRES_APPROVAL"
                ):
                    raw_l_ver = locked_prelim.get("scope_proposal_version")
                    raise ScopeApprovalRequiredError(
                        preliminary_feasibility=locked_prelim,
                        scope_proposal_version=(
                            int(raw_l_ver) if isinstance(raw_l_ver, int) else 1
                        ),
                        scope_proposal_hash=str(locked_prelim.get("scope_proposal_hash") or ""),
                    )
            approved = await self._milestone_repo.approve_all_for_roadmap(roadmap_id, effective_now)
            if locked_roadmap.planning_metadata:
                await self._roadmap_repo.save(locked_roadmap)
            await self._uow.commit()

        return approved
