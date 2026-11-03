from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from src.account.public_api import AvailabilityQueryPort, UserQueryPort
from src.evaluation.public_api import ScheduleChangeLogPort
from src.execution.public_api import (
    ExecutionScheduleSyncPort,
    ProposedDependencySyncItemDTO,
    ProposedTaskSyncItemDTO,
)
from src.planning.application.dtos.planning_dtos import (
    ApplyScheduleProposalResultDTO,
    MilestoneInputItemDTO,
    ProposedDependencyInputItemDTO,
    ProposedTaskInputItemDTO,
    ScheduleProposalViewDTO,
)
from src.planning.application.ports.planning_repository_ports import (
    GoalRepositoryPort,
    MilestoneRepositoryPort,
    OfficialScheduleRepositoryPort,
    RoadmapRepositoryPort,
    ScheduleProposalRepositoryPort,
)
from src.planning.application.services.validation_gate import (
    ProposalValidationGateOrchestrator,
)
from src.planning.application.use_cases.proposal_generation_use_cases import (
    build_availability_config_from_snapshot,
    normalize_proposal_task_ids_and_dependencies,
)
from src.planning.domain.events.planning_events import MilestoneApprovedEvent
from src.planning.domain.exceptions.planning_exceptions import (
    ProposalValidationGateError,
    RoadmapNotFoundError,
    ScheduleProposalNotFoundError,
    SoftOverflowConfirmationRequiredError,
)
from src.planning.domain.models.milestone import (
    Milestone,
    MilestoneStatus,
    validate_milestone_sequence,
)
from src.planning.domain.models.schedule import (
    OfficialSchedule,
    ScheduleProposal,
    ScheduleProposalStatus,
)
from src.planning.domain.services.validation_types import (
    parse_iso_date,
    parse_iso_datetime,
)
from src.shared_kernel.application.uow import AsyncUnitOfWork
from src.shared_kernel.domain.base import generate_uuid7


def _serialize_task_inputs(
    tasks: Sequence[ProposedTaskInputItemDTO | dict[str, Any]],
    dependencies: Sequence[ProposedDependencyInputItemDTO | dict[str, Any]] | None = None,
) -> dict[str, Any]:
    task_dicts: list[dict[str, Any]] = []
    for idx, t in enumerate(tasks):
        if isinstance(t, dict):
            item = dict(t)
            if "task_id" not in item:
                item["task_id"] = str(item.get("id") or generate_uuid7())
            else:
                item["task_id"] = str(item["task_id"])
            if "milestone_id" in item and item["milestone_id"] is not None:
                item["milestone_id"] = str(item["milestone_id"])
            if isinstance(item.get("scheduled_date"), datetime):
                item["scheduled_date"] = item["scheduled_date"].date().isoformat()
            elif hasattr(item.get("scheduled_date"), "isoformat"):
                item["scheduled_date"] = item["scheduled_date"].isoformat()
            if hasattr(item.get("scheduled_start"), "isoformat"):
                item["scheduled_start"] = item["scheduled_start"].isoformat()
            if hasattr(item.get("scheduled_end"), "isoformat"):
                item["scheduled_end"] = item["scheduled_end"].isoformat()
            task_dicts.append(item)
        else:
            s_date = (
                t.scheduled_date.isoformat()
                if hasattr(t.scheduled_date, "isoformat") and t.scheduled_date is not None
                else (str(t.scheduled_date) if t.scheduled_date is not None else None)
            )
            s_start = (
                t.scheduled_start.isoformat()
                if hasattr(t.scheduled_start, "isoformat") and t.scheduled_start is not None
                else (str(t.scheduled_start) if t.scheduled_start is not None else None)
            )
            s_end = (
                t.scheduled_end.isoformat()
                if hasattr(t.scheduled_end, "isoformat") and t.scheduled_end is not None
                else (str(t.scheduled_end) if t.scheduled_end is not None else None)
            )
            task_dicts.append(
                {
                    "task_id": str(t.task_id or generate_uuid7()),
                    "milestone_id": str(t.milestone_id),
                    "title": t.title,
                    "description": t.description,
                    "estimated_minutes": int(t.estimated_minutes),
                    "scheduled_date": s_date,
                    "scheduled_start": s_start,
                    "scheduled_end": s_end,
                    "prerequisite_ids": [str(p) for p in t.prerequisite_ids],
                }
            )

    dep_dicts: list[dict[str, Any]] = []
    for d in dependencies or []:
        if isinstance(d, dict):
            dep_dicts.append(
                {
                    "predecessor_id": str(d.get("predecessor_id", "")),
                    "successor_id": str(d.get("successor_id", "")),
                    "is_mandatory": bool(d.get("is_mandatory", True)),
                }
            )
        else:
            dep_dicts.append(
                {
                    "predecessor_id": str(d.predecessor_id),
                    "successor_id": str(d.successor_id),
                    "is_mandatory": bool(d.is_mandatory),
                }
            )

    return normalize_proposal_task_ids_and_dependencies(
        {
            "tasks": task_dicts,
            "dependencies": dep_dicts,
        }
    )


class GetCurrentScheduleProposalUseCase:
    """Retrieve the active DRAFT ScheduleProposal for a Roadmap with diff & warning metadata (UC-08)."""

    def __init__(
        self,
        *,
        roadmap_repo: RoadmapRepositoryPort,
        proposal_repo: ScheduleProposalRepositoryPort,
        execution_sync_port: ExecutionScheduleSyncPort | None = None,
    ) -> None:
        self._roadmap_repo = roadmap_repo
        self._proposal_repo = proposal_repo
        self._execution_sync_port = execution_sync_port

    async def execute(
        self,
        *,
        user_id: UUID,
        roadmap_id: UUID,
    ) -> ScheduleProposalViewDTO:
        roadmap = await self._roadmap_repo.get_by_id_for_user(roadmap_id, user_id)
        if roadmap is None:
            raise RoadmapNotFoundError()

        proposal = await self._proposal_repo.get_current_draft(roadmap_id)
        if proposal is None or proposal.user_id != user_id:
            raise ScheduleProposalNotFoundError()

        raw_tasks = proposal.proposal_data.get("tasks", [])
        proposed_minutes = sum(
            int(t.get("estimated_minutes", 0) or 0) for t in raw_tasks if isinstance(t, dict)
        )

        preserved_completed = 0
        replaceable_pending = 0
        if self._execution_sync_port is not None:
            current_tasks = await self._execution_sync_port.get_tasks_for_roadmaps([roadmap_id])
            preserved_completed = sum(1 for t in current_tasks if t.status == "COMPLETED")
            replaceable_pending = sum(
                1 for t in current_tasks if t.status in ("TODO", "IN_PROGRESS")
            )

        violations = list(proposal.proposal_data.get("validation_violations", []))
        soft_warnings = list(proposal.proposal_data.get("soft_overflow_warnings", []))
        advisories = [str(w) for w in proposal.proposal_data.get("advisory_warnings", [])]

        return ScheduleProposalViewDTO(
            proposal=proposal,
            is_valid=len(violations) == 0,
            violations=violations,
            soft_overflow_warnings=soft_warnings,
            advisory_warnings=advisories,
            diff_summary={
                "preserved_completed_tasks_count": preserved_completed,
                "replaceable_pending_tasks_count": replaceable_pending,
                "proposed_tasks_count": len(raw_tasks),
                "proposed_total_minutes": proposed_minutes,
            },
        )


class UpdateScheduleProposalUseCase:
    """Edit tasks/dependencies in a DRAFT ScheduleProposal & run UC-12 validation ([15, 240] min)."""

    def __init__(
        self,
        *,
        roadmap_repo: RoadmapRepositoryPort,
        milestone_repo: MilestoneRepositoryPort,
        proposal_repo: ScheduleProposalRepositoryPort,
        availability_query_port: AvailabilityQueryPort,
        execution_sync_port: ExecutionScheduleSyncPort,
        uow: AsyncUnitOfWork,
    ) -> None:
        self._roadmap_repo = roadmap_repo
        self._milestone_repo = milestone_repo
        self._proposal_repo = proposal_repo
        self._availability_port = availability_query_port
        self._execution_sync_port = execution_sync_port
        self._uow = uow

    async def execute(
        self,
        *,
        user_id: UUID,
        roadmap_id: UUID,
        proposal_id: UUID,
        tasks: Sequence[ProposedTaskInputItemDTO | dict[str, Any]],
        dependencies: Sequence[ProposedDependencyInputItemDTO | dict[str, Any]] | None = None,
        reject_invalid: bool = False,
        now: datetime | None = None,
    ) -> ScheduleProposalViewDTO:
        effective_now = now or datetime.now(UTC)
        roadmap = await self._roadmap_repo.get_by_id_for_user(roadmap_id, user_id)
        if roadmap is None:
            raise RoadmapNotFoundError()

        proposal = await self._proposal_repo.get_by_id(proposal_id)
        if proposal is None or proposal.roadmap_id != roadmap_id or proposal.user_id != user_id:
            raise ScheduleProposalNotFoundError()

        milestones = await self._milestone_repo.list_by_roadmap_id(roadmap_id)
        valid_mids: set[UUID | str] = {m.id for m in milestones}

        avail_snapshot = await self._availability_port.get_active_availability(user_id)
        avail_config = build_availability_config_from_snapshot(avail_snapshot)

        active_roadmaps = await self._roadmap_repo.list_by_user_id(user_id, status="ACTIVE")
        other_roadmaps = [r for r in active_roadmaps if r.id != roadmap_id]
        other_ids = [r.id for r in other_roadmaps]
        target_dates = {r.id: r.target_date for r in other_roadmaps}
        existing_tasks = await self._execution_sync_port.get_tasks_for_roadmaps(
            other_ids,
            roadmap_target_dates=target_dates,
        )

        normalized_payload = _serialize_task_inputs(tasks, dependencies)
        orchestrator = ProposalValidationGateOrchestrator(enable_tier3_judge=False)
        gate_result = await orchestrator.validate_proposal(
            normalized_payload,
            availability=avail_config,
            valid_milestone_ids=valid_mids if valid_mids else None,
            existing_tasks=existing_tasks,
            current_roadmap_target_date=roadmap.target_date,
            is_ai_generated=False,
        )

        if reject_invalid and not gate_result.is_valid:
            raise ProposalValidationGateError(
                message="Bản chỉnh sửa đề xuất lịch học vi phạm các ràng buộc kiểm định UC-12.",
                code="PROPOSAL_VALIDATION_FAILED",
                violations=[v.to_dict() for v in gate_result.violations],
            )

        updated_data = dict(proposal.proposal_data)
        updated_data["tasks"] = normalized_payload["tasks"]
        updated_data["dependencies"] = normalized_payload["dependencies"]
        updated_data["soft_overflow_warnings"] = [
            w.to_dict() for w in gate_result.soft_overflow_warnings
        ]
        updated_data["validation_violations"] = [v.to_dict() for v in gate_result.violations]
        updated_data["is_valid"] = gate_result.is_valid
        updated_data["availability_mode"] = avail_config.mode

        proposal.proposal_data = updated_data
        proposal.updated_at = effective_now

        async with self._uow:
            saved_proposal = await self._proposal_repo.save(proposal)
            await self._uow.commit()

        proposed_minutes = sum(
            int(t.get("estimated_minutes", 0) or 0)
            for t in normalized_payload["tasks"]
            if isinstance(t, dict)
        )
        return ScheduleProposalViewDTO(
            proposal=saved_proposal,
            is_valid=gate_result.is_valid,
            violations=[v.to_dict() for v in gate_result.violations],
            soft_overflow_warnings=[w.to_dict() for w in gate_result.soft_overflow_warnings],
            advisory_warnings=list(gate_result.advisory_warnings),
            diff_summary={
                "proposed_tasks_count": len(normalized_payload["tasks"]),
                "proposed_total_minutes": proposed_minutes,
            },
        )


class ApplyScheduleProposalUseCase:
    """Final deterministic UC-12 validation gate, Soft Overflow confirmation & OS-03 Merge into OfficialSchedule."""

    def __init__(
        self,
        *,
        roadmap_repo: RoadmapRepositoryPort,
        milestone_repo: MilestoneRepositoryPort,
        proposal_repo: ScheduleProposalRepositoryPort,
        schedule_repo: OfficialScheduleRepositoryPort,
        availability_query_port: AvailabilityQueryPort,
        execution_sync_port: ExecutionScheduleSyncPort,
        schedule_change_log_port: ScheduleChangeLogPort,
        uow: AsyncUnitOfWork,
        user_query_port: UserQueryPort | None = None,
    ) -> None:
        self._roadmap_repo = roadmap_repo
        self._milestone_repo = milestone_repo
        self._proposal_repo = proposal_repo
        self._schedule_repo = schedule_repo
        self._availability_port = availability_query_port
        self._execution_sync_port = execution_sync_port
        self._change_log_port = schedule_change_log_port
        self._uow = uow
        self._user_query_port = user_query_port

    async def execute(
        self,
        *,
        user_id: UUID,
        roadmap_id: UUID,
        proposal_id: UUID,
        confirm_soft_overflow: bool = False,
        tier: str | None = None,
        now: datetime | None = None,
    ) -> ApplyScheduleProposalResultDTO:
        effective_now = now or datetime.now(UTC)

        roadmap = await self._roadmap_repo.get_by_id_for_user(roadmap_id, user_id)
        if roadmap is None:
            raise RoadmapNotFoundError()

        proposal = await self._proposal_repo.get_by_id(proposal_id)
        if proposal is None or proposal.roadmap_id != roadmap_id or proposal.user_id != user_id:
            raise ScheduleProposalNotFoundError()

        milestones = await self._milestone_repo.list_by_roadmap_id(roadmap_id)
        valid_mids: set[UUID | str] = {m.id for m in milestones}

        avail_snapshot = await self._availability_port.get_active_availability(user_id)
        avail_config = build_availability_config_from_snapshot(avail_snapshot)

        active_roadmaps = await self._roadmap_repo.list_by_user_id(user_id, status="ACTIVE")
        other_roadmaps = [r for r in active_roadmaps if r.id != roadmap_id]
        other_ids = [r.id for r in other_roadmaps]
        target_dates = {r.id: r.target_date for r in other_roadmaps}
        existing_tasks = await self._execution_sync_port.get_tasks_for_roadmaps(
            other_ids,
            roadmap_target_dates=target_dates,
        )

        normalized_data = normalize_proposal_task_ids_and_dependencies(proposal.proposal_data)
        orchestrator = ProposalValidationGateOrchestrator(enable_tier3_judge=False)
        gate_result = await orchestrator.validate_proposal(
            normalized_data,
            availability=avail_config,
            valid_milestone_ids=valid_mids if valid_mids else None,
            existing_tasks=existing_tasks,
            current_roadmap_target_date=roadmap.target_date,
            is_ai_generated=False,
        )

        if not gate_result.is_valid:
            raise ProposalValidationGateError(
                message="Không thể áp dụng lịch học: phát hiện vi phạm ràng buộc tại cổng kiểm định UC-12.",
                code="PROPOSAL_VALIDATION_FAILED",
                violations=[v.to_dict() for v in gate_result.violations],
            )

        if gate_result.soft_overflow_warnings and not confirm_soft_overflow:
            total_overflow = sum(w.overflow_minutes for w in gate_result.soft_overflow_warnings)
            err = SoftOverflowConfirmationRequiredError(overflow_minutes=total_overflow)
            err.warnings = [w.to_dict() for w in gate_result.soft_overflow_warnings]  # type: ignore[attr-defined]
            raise err

        effective_tier = tier or "FREE"
        if tier is None and self._user_query_port is not None:
            user_snap = await self._user_query_port.get_user_by_id(user_id)
            if user_snap is not None:
                effective_tier = user_snap.tier

        active_count = await self._roadmap_repo.count_active_by_user_id(
            user_id,
            exclude_roadmap_id=roadmap_id,
        )

        raw_tasks = normalized_data.get("tasks", [])
        raw_deps = normalized_data.get("dependencies", [])

        sync_tasks: list[ProposedTaskSyncItemDTO] = []
        default_mid = milestones[0].id if milestones else generate_uuid7()
        for t in raw_tasks:
            if not isinstance(t, dict):
                continue
            tid = UUID(str(t["task_id"]))
            mid_raw = t.get("milestone_id")
            try:
                mid = UUID(str(mid_raw)) if mid_raw else default_mid
            except ValueError:
                mid = default_mid
            sync_tasks.append(
                ProposedTaskSyncItemDTO(
                    task_id=tid,
                    milestone_id=mid,
                    title=str(t.get("title", "")).strip(),
                    description=(
                        str(t["description"]).strip() if t.get("description") is not None else None
                    ),
                    estimated_minutes=int(t.get("estimated_minutes", 30) or 30),
                    scheduled_date=parse_iso_date(t.get("scheduled_date")),
                    scheduled_start=parse_iso_datetime(t.get("scheduled_start")),
                    scheduled_end=parse_iso_datetime(t.get("scheduled_end")),
                )
            )

        sync_deps: list[ProposedDependencySyncItemDTO] = []
        for dep in raw_deps:
            if not isinstance(dep, dict):
                continue
            try:
                pred_uuid = UUID(str(dep["predecessor_id"]))
                succ_uuid = UUID(str(dep["successor_id"]))
            except (KeyError, ValueError):
                continue
            sync_deps.append(
                ProposedDependencySyncItemDTO(
                    predecessor_id=pred_uuid,
                    successor_id=succ_uuid,
                    is_mandatory=bool(dep.get("is_mandatory", True)),
                )
            )

        existing_schedule = await self._schedule_repo.get_by_roadmap_id(roadmap_id)
        is_replan = existing_schedule is not None
        trigger_type = "REPLAN_MERGE" if is_replan else "INITIAL_APPLY"

        official_schedule = existing_schedule or OfficialSchedule(
            id=generate_uuid7(),
            roadmap_id=roadmap_id,
            total_sessions=len(sync_tasks),
            total_planned_minutes=sum(t.estimated_minutes for t in sync_tasks),
            activated_at=effective_now,
            created_at=effective_now,
            updated_at=effective_now,
        )

        async with self._uow:
            roadmap.activate(
                effective_now,
                tier=effective_tier,
                current_active_count=active_count,
            )
            saved_roadmap = await self._roadmap_repo.save(roadmap)

            # Save OfficialSchedule first so FK `tasks.official_schedule_id` is satisfied
            saved_schedule = await self._schedule_repo.save(official_schedule)

            sync_result = await self._execution_sync_port.sync_official_schedule_tasks(
                roadmap_id=roadmap_id,
                official_schedule_id=saved_schedule.id,
                proposed_tasks=sync_tasks,
                proposed_dependencies=sync_deps,
                now=effective_now,
            )

            official_schedule.id = saved_schedule.id
            official_schedule.apply_metrics(
                user_id=user_id,
                total_sessions=sync_result.total_active_sessions,
                total_planned_minutes=sync_result.total_planned_minutes,
                now=effective_now,
                proposal_id=proposal.id,
            )
            saved_schedule = await self._schedule_repo.save(official_schedule)
            self._uow.collect_events_from(official_schedule)

            proposal.proposal_data = normalized_data
            proposal.mark_applied(effective_now)
            saved_proposal = await self._proposal_repo.save(proposal)

            await self._change_log_port.record_change_log(
                roadmap_id=roadmap_id,
                schedule_id=saved_schedule.id,
                trigger_type=trigger_type,
                reason=f"Áp dụng lịch học chính thức ({trigger_type}) từ đề xuất {proposal.id}",
                affected_tasks_count=sync_result.affected_tasks_count,
                total_shifted_minutes=sync_result.total_shifted_minutes,
                diff_payload={
                    "proposal_id": str(proposal.id),
                    "preserved_completed_tasks_count": sync_result.preserved_completed_tasks_count,
                    "replaced_tasks_count": sync_result.replaced_tasks_count,
                    "inserted_tasks_count": sync_result.inserted_tasks_count,
                    "confirm_soft_overflow": confirm_soft_overflow,
                },
                now=effective_now,
            )

            await self._uow.commit()

        return ApplyScheduleProposalResultDTO(
            roadmap=saved_roadmap,
            official_schedule=saved_schedule,
            proposal=saved_proposal,
            preserved_completed_tasks_count=sync_result.preserved_completed_tasks_count,
            replaced_tasks_count=sync_result.replaced_tasks_count,
            inserted_tasks_count=sync_result.inserted_tasks_count,
            affected_tasks_count=sync_result.affected_tasks_count,
            total_shifted_minutes=sync_result.total_shifted_minutes,
            trigger_type=trigger_type,
        )


class SaveManualRoadmapPlanUseCase:
    """Manual fallback planning (`UC-09`, `FR-PLAN-004`) without consuming AI quota."""

    def __init__(
        self,
        *,
        goal_repo: GoalRepositoryPort,
        roadmap_repo: RoadmapRepositoryPort,
        milestone_repo: MilestoneRepositoryPort,
        proposal_repo: ScheduleProposalRepositoryPort,
        availability_query_port: AvailabilityQueryPort,
        execution_sync_port: ExecutionScheduleSyncPort,
        uow: AsyncUnitOfWork,
    ) -> None:
        self._goal_repo = goal_repo
        self._roadmap_repo = roadmap_repo
        self._milestone_repo = milestone_repo
        self._proposal_repo = proposal_repo
        self._availability_port = availability_query_port
        self._execution_sync_port = execution_sync_port
        self._uow = uow

    async def execute(
        self,
        *,
        user_id: UUID,
        roadmap_id: UUID,
        tasks: Sequence[ProposedTaskInputItemDTO | dict[str, Any]],
        dependencies: Sequence[ProposedDependencyInputItemDTO | dict[str, Any]] | None = None,
        milestones: Sequence[MilestoneInputItemDTO | dict[str, Any]] | None = None,
        now: datetime | None = None,
    ) -> ScheduleProposalViewDTO:
        effective_now = now or datetime.now(UTC)

        roadmap = await self._roadmap_repo.get_by_id_for_user(roadmap_id, user_id)
        if roadmap is None:
            raise RoadmapNotFoundError()

        existing_milestones = await self._milestone_repo.list_by_roadmap_id(roadmap_id)
        existing_by_id = {m.id: m for m in existing_milestones}

        if milestones is not None and len(milestones) > 0:
            built_milestones: list[Milestone] = []
            for idx, m_in in enumerate(milestones, start=1):
                if isinstance(m_in, dict):
                    raw_mid = m_in.get("milestone_id") or m_in.get("id")
                    mid_uuid = UUID(str(raw_mid)) if raw_mid else generate_uuid7()
                    seq = int(m_in.get("sequence_order", idx) or idx)
                    title = str(m_in.get("title", "")).strip()
                    desc = (
                        str(m_in["description"]).strip()
                        if m_in.get("description") is not None
                        else None
                    )
                else:
                    mid_uuid = m_in.milestone_id or generate_uuid7()
                    seq = m_in.sequence_order if m_in.sequence_order >= 1 else idx
                    title = m_in.title
                    desc = m_in.description

                prev = existing_by_id.get(mid_uuid)
                built_milestones.append(
                    Milestone(
                        id=mid_uuid,
                        roadmap_id=roadmap_id,
                        sequence_order=seq,
                        title=title,
                        description=desc,
                        status=MilestoneStatus.APPROVED,
                        created_at=prev.created_at if prev is not None else effective_now,
                        updated_at=effective_now,
                    )
                )
            validate_milestone_sequence(built_milestones, enforce_ai_bounds=False)
            active_milestones = built_milestones
        elif existing_milestones:
            active_milestones = existing_milestones
        else:
            active_milestones = [
                Milestone(
                    id=generate_uuid7(),
                    roadmap_id=roadmap_id,
                    sequence_order=1,
                    title="Chặng 1: Kế hoạch tự học thủ công",
                    description="Cột mốc mặc định cho lộ trình lập thủ công.",
                    status=MilestoneStatus.APPROVED,
                    created_at=effective_now,
                    updated_at=effective_now,
                )
            ]

        seq_to_mid: dict[int, UUID] = {m.sequence_order: m.id for m in active_milestones}
        default_mid = active_milestones[0].id
        valid_mid_strs = {str(m.id) for m in active_milestones}

        normalized_payload = _serialize_task_inputs(tasks, dependencies)
        for t_dict in normalized_payload.get("tasks", []):
            if not isinstance(t_dict, dict):
                continue
            raw_m = str(t_dict.get("milestone_id", "")).strip()
            if raw_m not in valid_mid_strs:
                seq_hint = int(t_dict.get("milestone_sequence_order", 1) or 1)
                t_dict["milestone_id"] = str(seq_to_mid.get(seq_hint, default_mid))

        avail_snapshot = await self._availability_port.get_active_availability(user_id)
        avail_config = build_availability_config_from_snapshot(avail_snapshot)

        active_roadmaps = await self._roadmap_repo.list_by_user_id(user_id, status="ACTIVE")
        other_roadmaps = [r for r in active_roadmaps if r.id != roadmap_id]
        other_ids = [r.id for r in other_roadmaps]
        target_dates = {r.id: r.target_date for r in other_roadmaps}
        existing_tasks = await self._execution_sync_port.get_tasks_for_roadmaps(
            other_ids,
            roadmap_target_dates=target_dates,
        )

        orchestrator = ProposalValidationGateOrchestrator(enable_tier3_judge=False)
        gate_result = await orchestrator.validate_proposal(
            normalized_payload,
            availability=avail_config,
            valid_milestone_ids={m.id for m in active_milestones},
            existing_tasks=existing_tasks,
            current_roadmap_target_date=roadmap.target_date,
            is_ai_generated=False,
        )

        if not gate_result.is_valid:
            raise ProposalValidationGateError(
                message="Kế hoạch học tập thủ công vi phạm các ràng buộc kiểm định UC-12.",
                code="MANUAL_PLAN_VALIDATION_FAILED",
                violations=[v.to_dict() for v in gate_result.violations],
            )

        proposal_data = dict(gate_result.validated_proposal_data)
        proposal_data["source"] = "MANUAL"
        proposal_data["availability_mode"] = avail_config.mode
        proposal_data["is_valid"] = True
        proposal_data["validation_violations"] = []

        proposal = ScheduleProposal(
            id=generate_uuid7(),
            roadmap_id=roadmap_id,
            user_id=user_id,
            proposal_data=proposal_data,
            status=ScheduleProposalStatus.DRAFT,
            applied_at=None,
            created_at=effective_now,
            updated_at=effective_now,
        )

        async with self._uow:
            await self._milestone_repo.save_many(roadmap_id, active_milestones)
            approved_ms = await self._milestone_repo.approve_all_for_roadmap(
                roadmap_id, effective_now
            )
            roadmap.add_domain_event(
                MilestoneApprovedEvent(
                    aggregate_id=roadmap.id,
                    user_id=user_id,
                    roadmap_id=roadmap.id,
                    milestone_count=len(approved_ms),
                    occurred_at=effective_now,
                )
            )
            self._uow.collect_events_from(roadmap)
            await self._proposal_repo.discard_existing_drafts(roadmap_id, effective_now)
            saved_proposal = await self._proposal_repo.save(proposal)
            await self._uow.commit()

        proposed_minutes = sum(
            int(t.get("estimated_minutes", 0) or 0)
            for t in proposal_data.get("tasks", [])
            if isinstance(t, dict)
        )
        return ScheduleProposalViewDTO(
            proposal=saved_proposal,
            is_valid=True,
            violations=[],
            soft_overflow_warnings=[w.to_dict() for w in gate_result.soft_overflow_warnings],
            advisory_warnings=list(gate_result.advisory_warnings),
            diff_summary={
                "proposed_tasks_count": len(proposal_data.get("tasks", [])),
                "proposed_total_minutes": proposed_minutes,
            },
        )
