from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from src.account.public_api import (
    AvailabilityQueryPort,
    AvailabilitySnapshotDTO,
    LearnerProfileQueryPort,
    QuotaFacadePort,
)
from src.execution.public_api import ExecutionScheduleSyncPort
from src.planning.application.dtos.planning_dtos import SseJobTicketDTO
from src.planning.application.ports.planning_repository_ports import (
    GoalRepositoryPort,
    MilestoneRepositoryPort,
    RoadmapRepositoryPort,
    ScheduleProposalRepositoryPort,
)
from src.planning.application.ports.sse_job_port import SseJobPort
from src.planning.application.services.validation_gate import (
    DEFAULT_MAX_RETRIES,
    ProposalValidationGateOrchestrator,
)
from src.planning.domain.exceptions.planning_exceptions import (
    RoadmapNotFoundError,
    UnapprovedMilestonesError,
)
from src.planning.domain.models.milestone import MilestoneStatus
from src.planning.domain.models.schedule import (
    ScheduleProposal,
    ScheduleProposalStatus,
)
from src.planning.domain.services.validation_types import (
    AI_BLOCK_MAX_MINUTES,
    AI_BLOCK_MIN_MINUTES,
    AvailabilityConfigurationDTO,
    AvailabilitySlotDTO,
    ConstraintViolationDTO,
)
from src.shared_kernel.application.llm_port import LLMProviderPort
from src.shared_kernel.application.uow import AsyncUnitOfWork
from src.shared_kernel.domain.base import generate_uuid7
from src.shared_kernel.infrastructure.external_ai.prompt_sanitizer import (
    PromptSanitizer,
)

SCHEDULE_PROPOSAL_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "tasks": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string"},
                    "milestone_id": {"type": "string"},
                    "title": {"type": "string", "minLength": 1},
                    "description": {"type": "string"},
                    "estimated_minutes": {
                        "type": "integer",
                        "minimum": AI_BLOCK_MIN_MINUTES,
                        "maximum": AI_BLOCK_MAX_MINUTES,
                    },
                    "scheduled_date": {"type": "string"},
                    "scheduled_start": {"type": "string"},
                    "scheduled_end": {"type": "string"},
                },
                "required": [
                    "milestone_id",
                    "title",
                    "estimated_minutes",
                    "scheduled_date",
                ],
            },
        },
        "dependencies": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "predecessor_id": {"type": "string"},
                    "successor_id": {"type": "string"},
                    "is_mandatory": {"type": "boolean"},
                },
                "required": ["predecessor_id", "successor_id"],
            },
        },
    },
    "required": ["tasks"],
}


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
        enable_tier3_judge: bool = False,
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
            avail_snapshot = await self._availability_port.get_active_availability(user_id)
            avail_config = build_availability_config_from_snapshot(avail_snapshot)
            learner_profile = await self._learner_profile_port.get_learner_profile(user_id)

            active_roadmaps = await self._roadmap_repo.list_by_user_id(user_id, status="ACTIVE")
            other_roadmaps = [r for r in active_roadmaps if r.id != roadmap_id]
            other_roadmap_ids = [r.id for r in other_roadmaps]
            roadmap_target_dates = {r.id: r.target_date for r in other_roadmaps}
            existing_tasks = await self._execution_sync_port.get_tasks_for_roadmaps(
                other_roadmap_ids,
                roadmap_target_dates=roadmap_target_dates,
            )

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

            sanitized_title = PromptSanitizer.sanitize(roadmap.title, wrap_xml=True)
            sanitized_desc = PromptSanitizer.sanitize(roadmap.description or "", wrap_xml=True)
            milestone_lines = [
                f"- id={m.id} | seq={m.sequence_order} | title={PromptSanitizer.sanitize(m.title, wrap_xml=True)}"
                for m in milestones
            ]
            slot_lines = [
                f"{slot.day_of_week}: {slot.start_time}-{slot.end_time}"
                for slot in avail_config.availability_slots
                if slot.is_active
            ]
            start_date_str = (
                roadmap.start_date.isoformat() if roadmap.start_date is not None else "2026-11-02"
            )

            system_prompt = (
                "Bạn là hệ thống lập kế hoạch học tập thích ứng FocusFlow (Zimmerman SRL). "
                "Hãy sinh đề xuất lịch học chi tiết (tasks & dependencies) bám sát các cột mốc "
                "đã duyệt, thời lượng mỗi nhiệm vụ từ 30 đến 120 phút, tuyệt đối tuân thủ lịch rảnh."
            )
            user_prompt = (
                f"GENERATE_PROPOSAL_TASKS\n"
                f"Roadmap: {sanitized_title}\n"
                f"Description: {sanitized_desc}\n"
                f"Start Date: {start_date_str}\n"
                f"Target Date: {roadmap.target_date.isoformat() if roadmap.target_date else 'N/A'}\n"
                f"Availability Mode: {avail_config.mode}\n"
                f"Learner Optimal Session Minutes: {learner_profile.opt_session_minutes} (beta={learner_profile.estimation_bias_beta})\n"
                f"MILESTONE_IDS:\n" + "\n".join(milestone_lines) + "\n"
                "AVAILABILITY_SLOTS:\n"
                + ("\n".join(slot_lines) if slot_lines else "monday: 19:30-21:30")
            )

            await self._sse.append_event(
                job_id=job_id,
                event="chunk",
                status="STREAMING",
                data={
                    "stage": "VALIDATING_TIER_1_2_3",
                    "progress": 60,
                    "delta_text": "Đang chạy cổng kiểm định 3 tầng (Tier 1 Schema, Tier 2 Spatio-Temporal/DAG, Tier 3 Judge)...",
                    "deltaText": "Đang chạy cổng kiểm định 3 tầng (Tier 1 Schema, Tier 2 Spatio-Temporal/DAG, Tier 3 Judge)...",
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
            )
            valid_mids: set[UUID | str] = {m.id for m in milestones}
            gate_result = await orchestrator.generate_and_validate_proposal_with_retry(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_schema=SCHEDULE_PROPOSAL_RESPONSE_SCHEMA,
                availability=avail_config,
                valid_milestone_ids=valid_mids,
                existing_tasks=existing_tasks,
                current_roadmap_target_date=roadmap.target_date,
                goal_title=goal.title if goal is not None else roadmap.title,
                max_retries=max_retries,
                on_retry_callback=_on_retry,
            )

            normalized_data = normalize_proposal_task_ids_and_dependencies(
                gate_result.validated_proposal_data
            )
            normalized_data["availability_mode"] = avail_config.mode
            normalized_data["attempts_used"] = gate_result.attempts_used
            normalized_data["retry_history"] = list(gate_result.retry_history)
            normalized_data["judge_skipped"] = gate_result.judge_skipped
            if gate_result.pedagogical_score is not None:
                normalized_data["pedagogical_score"] = gate_result.pedagogical_score

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
                await self._quota_facade.commit_reservation(
                    reservation_id,
                    prompt_tokens=gate_result.total_prompt_tokens,
                    completion_tokens=gate_result.total_completion_tokens,
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
            except Exception:
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
