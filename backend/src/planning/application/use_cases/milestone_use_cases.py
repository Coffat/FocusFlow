import asyncio
import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from src.account.public_api import LearnerMemoryQueryPort, QuotaFacadePort
from src.planning.application.dtos.planning_dtos import (
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
)
from src.planning.application.ports.sse_job_port import SseJobPort
from src.planning.application.services.harness_support import (
    compact_context_snapshot,
    load_planning_harness_context_inputs,
)
from src.planning.application.services.knowledge_tool_dispatcher import (
    KnowledgeToolDispatcher,
    RoadmapPipelineStage,
)
from src.planning.application.services.learning_quality import (
    GenerationStrategy,
    has_operational_quality_review_failure,
    run_dual_quality_critics,
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
    DEFAULT_MAX_RETRIES,
    ProposalValidationGateOrchestrator,
)
from src.planning.domain.events.planning_events import MilestoneApprovedEvent
from src.planning.domain.exceptions.planning_exceptions import (
    ProposalValidationGateError,
    RoadmapNotFoundError,
)
from src.planning.domain.models.milestone import (
    Milestone,
    MilestoneStatus,
    validate_milestone_sequence,
)
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
from src.shared_kernel.domain.base import generate_uuid7


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
                context_block = RoadmapContextBuilder.build_milestone_planning_context(
                    goal=goal,
                    roadmap=roadmap,
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

            dispatcher: KnowledgeToolDispatcher | None = None
            if self._kb is not None:
                dispatcher = KnowledgeToolDispatcher(
                    self._kb,
                    stage=RoadmapPipelineStage.MILESTONE_PLANNING,
                    max_tool_calls=MILESTONE_PLANNER_SKILL.max_tool_calls,
                    timeout_seconds=5.0,
                )

            current_prompt = base_user_prompt
            total_prompt_tokens = 0
            total_completion_tokens = 0
            max_attempts = max(1, int(max_retries) + 1)
            pipeline_deadline = asyncio.get_running_loop().time() + 55.0
            validated_items: list[dict[str, Any]] = []
            last_violations = []

            for attempt in range(1, max_attempts + 1):
                remaining_seconds = pipeline_deadline - asyncio.get_running_loop().time()
                if remaining_seconds <= 0:
                    raise TimeoutError("Milestone generation exceeded 55 seconds")

                exec_mgr = AIExecutionManager(
                    provider=self._llm,
                    quota=self._quota_facade,
                    manage_quota=False,
                    max_retries=0,
                    workflow_repo=self._workflow_repo,
                    timeout_seconds=min(35.0, remaining_seconds),
                )
                exec_res = await exec_mgr.execute(
                    user_id=user_id,
                    operation_type="MILESTONE_GEN",
                    system_prompt=system_prompt,
                    user_prompt=current_prompt,
                    response_schema=MILESTONE_RESPONSE_SCHEMA,
                    model_name=getattr(self._llm, "model_identifier", "gemini-3.8-flash"),
                    tools=(
                        dispatcher.get_allowed_tool_declarations()
                        if dispatcher is not None and attempt == 1
                        else None
                    ),
                    tool_executor=(
                        dispatcher.dispatch if dispatcher is not None and attempt == 1 else None
                    ),
                    max_tool_calls=(
                        MILESTONE_PLANNER_SKILL.max_tool_calls
                        if dispatcher is not None and attempt == 1
                        else 0
                    ),
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
                total_prompt_tokens += int(p_tok or 0)
                total_completion_tokens += int(c_tok or 0)

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
                if not violations:
                    remaining_seconds = pipeline_deadline - asyncio.get_running_loop().time()
                    if remaining_seconds <= 0:
                        raise TimeoutError("Milestone quality review exceeded 55 seconds")
                    critic_timeout = min(8.0, remaining_seconds)
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
                            arbiter_timeout_seconds=critic_timeout,
                            workflow_repo=self._workflow_repo,
                            user_id=user_id,
                            goal_id=roadmap.goal_id,
                            roadmap_id=roadmap_id,
                            workflow_type=WorkflowType.PLAN_CREATION,
                        ),
                        timeout=remaining_seconds,
                    )
                    total_prompt_tokens += critic_p
                    total_completion_tokens += critic_c
                    if has_operational_quality_review_failure(critic_violations):
                        raise TimeoutError(
                            "Milestone quality review did not complete within its time budget"
                        )
                    violations.extend(critic_violations)
                if not violations:
                    validated_items = list(raw_milestones)
                    roadmap.planning_metadata = {
                        **roadmap.planning_metadata,
                        "generation_strategy": strategy.value,
                        "quality_reviews": critic_reports,
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
                if attempt < max_attempts and remaining_for_retry >= 12.0:
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
            new_milestones = [
                Milestone(
                    id=generate_uuid7(),
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
                    estimated_effort_minutes=int(item.get("estimated_effort_minutes", 60) or 60),
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
                await self._quota_facade.commit_reservation(
                    reservation_id,
                    prompt_tokens=total_prompt_tokens,
                    completion_tokens=total_completion_tokens,
                )
                await self._uow.commit()

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
            await self._sse.append_event(
                job_id=job_id,
                event="completed",
                status="COMPLETED",
                data={
                    "stage": "COMPLETED",
                    "progress": 100,
                    "delta_text": "Hoàn tất phân rã cột mốc học tập!",
                    "deltaText": "Hoàn tất phân rã cột mốc học tập!",
                    "payload": {
                        "roadmap_id": str(roadmap_id),
                        "milestones": milestones_payload,
                    },
                },
            )
            return saved_milestones

        except Exception as exc:
            error_code, error_message = _milestone_generation_error_details(exc)
            try:
                async with self._uow:
                    await self._quota_facade.release_reservation(
                        reservation_id,
                        reason=error_code,
                    )
                    await self._uow.commit()
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
                idempotency_key=idempotency_key,
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
    ) -> None:
        self._roadmap_repo = roadmap_repo
        self._milestone_repo = milestone_repo
        self._uow = uow

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

        async with self._uow:
            saved = await self._milestone_repo.save_many(roadmap_id, milestones)
            await self._uow.commit()

        return saved


class ApproveMilestonesUseCase:
    """Approve all Level-1 Milestones of a Roadmap and emit MilestoneApprovedEvent to Outbox (UC-07)."""

    def __init__(
        self,
        *,
        roadmap_repo: RoadmapRepositoryPort,
        milestone_repo: MilestoneRepositoryPort,
        uow: AsyncUnitOfWork,
    ) -> None:
        self._roadmap_repo = roadmap_repo
        self._milestone_repo = milestone_repo
        self._uow = uow

    async def execute(
        self,
        *,
        user_id: UUID,
        roadmap_id: UUID,
        now: datetime | None = None,
    ) -> list[Milestone]:
        effective_now = now or datetime.now(UTC)
        roadmap = await self._roadmap_repo.get_by_id_for_user(roadmap_id, user_id)
        if roadmap is None:
            raise RoadmapNotFoundError()

        current_milestones = await self._milestone_repo.list_by_roadmap_id(roadmap_id)
        validate_milestone_sequence(current_milestones, enforce_ai_bounds=False)

        async with self._uow:
            approved = await self._milestone_repo.approve_all_for_roadmap(roadmap_id, effective_now)
            roadmap.add_domain_event(
                MilestoneApprovedEvent(
                    aggregate_id=roadmap.id,
                    user_id=user_id,
                    roadmap_id=roadmap.id,
                    milestone_count=len(approved),
                    occurred_at=effective_now,
                )
            )
            self._uow.collect_events_from(roadmap)
            await self._uow.commit()

        return approved
