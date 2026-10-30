from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from src.account.public_api import QuotaFacadePort
from src.planning.application.dtos.planning_dtos import (
    MilestoneInputItemDTO,
    SseJobTicketDTO,
)
from src.planning.application.ports.planning_repository_ports import (
    GoalRepositoryPort,
    MilestoneRepositoryPort,
    RoadmapRepositoryPort,
)
from src.planning.application.ports.sse_job_port import SseJobPort
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
    AI_MILESTONE_MAX_COUNT,
    AI_MILESTONE_MIN_COUNT,
    Milestone,
    MilestoneStatus,
    validate_milestone_sequence,
)
from src.shared_kernel.application.llm_port import LLMProviderPort
from src.shared_kernel.application.uow import AsyncUnitOfWork
from src.shared_kernel.domain.base import generate_uuid7
from src.shared_kernel.infrastructure.external_ai.prompt_sanitizer import (
    PromptSanitizer,
)

MILESTONE_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "milestones": {
            "type": "array",
            "minItems": AI_MILESTONE_MIN_COUNT,
            "maxItems": AI_MILESTONE_MAX_COUNT,
            "items": {
                "type": "object",
                "properties": {
                    "sequence_order": {"type": "integer", "minimum": 1},
                    "title": {"type": "string", "minLength": 1},
                    "description": {"type": "string"},
                },
                "required": ["sequence_order", "title"],
            },
        }
    },
    "required": ["milestones"],
}


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
    ) -> None:
        self._goal_repo = goal_repo
        self._roadmap_repo = roadmap_repo
        self._milestone_repo = milestone_repo
        self._quota_facade = quota_facade
        self._llm = llm_provider
        self._sse = sse_job_store
        self._uow = uow

    async def execute(
        self,
        *,
        job_id: UUID,
        user_id: UUID,
        roadmap_id: UUID,
        reservation_id: UUID,
        max_retries: int = DEFAULT_MAX_RETRIES,
        now: datetime | None = None,
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

            sanitized_title = PromptSanitizer.sanitize(raw_title, wrap_xml=True)
            sanitized_desc = PromptSanitizer.sanitize(raw_desc, wrap_xml=True)

            await self._sse.append_event(
                job_id=job_id,
                event="stage",
                status="STREAMING",
                data={
                    "stage": "STREAMING",
                    "progress": 35,
                    "delta_text": "Đang phân tích mục tiêu học tập và phân rã cột mốc (3-7 chặng)...",
                    "deltaText": "Đang phân tích mục tiêu học tập và phân rã cột mốc (3-7 chặng)...",
                },
            )

            system_prompt = (
                "Bạn là kiến trúc sư lộ trình học tập tự điều chỉnh theo mô hình Zimmerman SRL. "
                "Hãy phân rã mục tiêu học tập trong thẻ <user_input> thành từ 3 đến 7 cột mốc "
                "(Milestones) tuần tự có sequence_order liên tục từ 1..N."
            )
            base_user_prompt = (
                f"Tiêu đề mục tiêu: {sanitized_title}\n"
                f"Mô tả chi tiết: {sanitized_desc}\n"
                f"Ngày bắt đầu: {roadmap.start_date.isoformat() if roadmap.start_date else 'N/A'}\n"
                f"Ngày đích: {roadmap.target_date.isoformat() if roadmap.target_date else 'N/A'}"
            )

            current_prompt = base_user_prompt
            total_prompt_tokens = 0
            total_completion_tokens = 0
            max_attempts = max(1, int(max_retries) + 1)
            validated_items: list[dict[str, Any]] = []
            last_violations = []

            for attempt in range(1, max_attempts + 1):
                raw_result, p_tok, c_tok = await self._llm.generate_structured(
                    prompt=current_prompt,
                    system_prompt=system_prompt,
                    response_schema=MILESTONE_RESPONSE_SCHEMA,
                    user_prompt=current_prompt,
                    temperature=0.2,
                )
                total_prompt_tokens += int(p_tok or 0)
                total_completion_tokens += int(c_tok or 0)

                raw_milestones = raw_result.get("milestones", [])
                if not isinstance(raw_milestones, list):
                    raw_milestones = []

                violations = ProposalValidationGateOrchestrator.validate_ai_milestones_tier1(
                    raw_milestones
                )
                if not violations:
                    validated_items = list(raw_milestones)
                    break

                last_violations = violations
                if attempt < max_attempts:
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

            if not validated_items:
                raise ProposalValidationGateError(
                    message="AI không thể sinh danh sách cột mốc hợp lệ (3..7 chặng tuần tự) sau khi tự sửa lỗi.",
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
                    status=MilestoneStatus.PENDING,
                    created_at=effective_now,
                    updated_at=effective_now,
                )
                for idx, item in enumerate(sorted_items, start=1)
            ]
            validate_milestone_sequence(new_milestones, enforce_ai_bounds=True)

            async with self._uow:
                saved_milestones = await self._milestone_repo.save_many(roadmap_id, new_milestones)
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
            try:
                async with self._uow:
                    await self._quota_facade.release_reservation(
                        reservation_id,
                        reason=getattr(exc, "code", "MILESTONE_GEN_FAILED"),
                    )
                    await self._uow.commit()
            except Exception:
                pass

            await self._sse.append_event(
                job_id=job_id,
                event="failed",
                status="FAILED",
                data={
                    "stage": "FAILED",
                    "progress": 100,
                    "error": str(exc),
                    "error_code": getattr(exc, "code", "MILESTONE_GEN_FAILED"),
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
    ) -> SseJobTicketDTO:
        roadmap = await self._roadmap_repo.get_by_id_for_user(roadmap_id, user_id)
        if roadmap is None:
            raise RoadmapNotFoundError()

        operation = f"MILESTONE_GEN:{roadmap_id}"
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
                job_type="MILESTONE_GEN",
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
                )
            except Exception:
                # Error is already recorded in the SSE job stream and quota is released
                pass

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
