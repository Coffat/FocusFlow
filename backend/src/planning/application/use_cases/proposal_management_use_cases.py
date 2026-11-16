from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from src.account.public_api import (
    AvailabilityQueryPort,
    CalendarConnectionQueryPort,
    CalendarSyncFacadePort,
    LearnerProfileQueryPort,
    UserQueryPort,
)
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
    SseJobTicketDTO,
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
from src.planning.application.ports.sse_job_port import SseJobPort
from src.planning.application.services.effective_availability_service import (
    GetEffectiveAvailabilityUseCase,
)
from src.planning.application.services.existing_schedule_occupancy import (
    expand_existing_schedule_occupancy,
)
from src.planning.application.services.learning_quality import (
    FeasibilityStatus,
    assess_schedule_feasibility,
    validate_task_coverage,
)
from src.planning.application.services.validation_gate import (
    ProposalValidationGateOrchestrator,
)
from src.planning.application.use_cases.proposal_generation_use_cases import (
    normalize_proposal_task_ids_and_dependencies,
)
from src.planning.domain.events.planning_events import MilestoneApprovedEvent
from src.planning.domain.exceptions.planning_exceptions import (
    FreshCalendarConflictDetectedError,
    JudgeReviewConfirmationRequiredError,
    PartialScheduleConfirmationRequiredError,
    PlanInfeasibleError,
    PlanningDomainError,
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
    ScheduleProposalType,
)
from src.planning.domain.models.schedule_block import ScheduleBlock
from src.planning.domain.services.spatio_temporal_engine import SpatioTemporalRuleEngine
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
        user_query_port: UserQueryPort | None = None,
        block_repo: ScheduleBlockRepositoryPort | None = None,
        calendar_connection_query_port: CalendarConnectionQueryPort | None = None,
    ) -> None:
        self._roadmap_repo = roadmap_repo
        self._milestone_repo = milestone_repo
        self._proposal_repo = proposal_repo
        self._availability_port = availability_query_port
        self._execution_sync_port = execution_sync_port
        self._uow = uow
        self._user_query_port = user_query_port
        self._block_repo = block_repo
        self._calendar_connection_port = calendar_connection_query_port

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

        user_tz = "UTC"
        if self._user_query_port is not None:
            user_snapshot = await self._user_query_port.get_user_by_id(user_id)
            user_tz = (
                user_snapshot.timezone
                if user_snapshot is not None and user_snapshot.timezone
                else "Asia/Ho_Chi_Minh"
            )

        active_roadmaps = await self._roadmap_repo.list_by_user_id(user_id, status="ACTIVE")
        other_roadmaps = [r for r in active_roadmaps if r.id != roadmap_id]
        other_ids = [r.id for r in other_roadmaps]
        target_dates = {r.id: r.target_date for r in other_roadmaps}
        existing_tasks = await self._execution_sync_port.get_tasks_for_roadmaps(
            other_ids,
            roadmap_target_dates=target_dates,
        )
        if self._block_repo is not None:
            existing_tasks = expand_existing_schedule_occupancy(
                existing_tasks, await self._block_repo.list_by_roadmap_ids(other_ids)
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

        normalized_payload = _serialize_task_inputs(tasks, dependencies)
        original_tasks = {
            str(task.get("task_id")): task
            for task in proposal.proposal_data.get("tasks", [])
            if isinstance(task, dict)
        }
        unchanged_schedule = len(normalized_payload["tasks"]) == len(original_tasks) and all(
            str(task.get("task_id")) in original_tasks
            and int(task.get("estimated_minutes", 0))
            == int(original_tasks[str(task["task_id"])].get("estimated_minutes", 0))
            and parse_iso_date(task.get("scheduled_date"))
            == parse_iso_date(original_tasks[str(task["task_id"])].get("scheduled_date"))
            and parse_iso_datetime(task.get("scheduled_start"))
            == parse_iso_datetime(original_tasks[str(task["task_id"])].get("scheduled_start"))
            and parse_iso_datetime(task.get("scheduled_end"))
            == parse_iso_datetime(original_tasks[str(task["task_id"])].get("scheduled_end"))
            for task in normalized_payload["tasks"]
        )
        if unchanged_schedule and isinstance(proposal.proposal_data.get("schedule_blocks"), list):
            normalized_payload["schedule_blocks"] = proposal.proposal_data["schedule_blocks"]
        orchestrator = ProposalValidationGateOrchestrator(enable_tier3_judge=False)
        gate_result = await orchestrator.validate_proposal(
            normalized_payload,
            availability=avail_config,
            valid_milestone_ids=valid_mids if valid_mids else None,
            existing_tasks=existing_tasks,
            current_roadmap_target_date=roadmap.target_date,
            is_ai_generated=False,
            allow_unscheduled_tasks=any(
                isinstance(task, dict) and task.get("scheduled_date") is None
                for task in normalized_payload["tasks"]
            ),
        )
        coverage_violations = validate_task_coverage(normalized_payload["tasks"], milestones)
        combined_violations = [*gate_result.violations, *coverage_violations]
        proposal_is_valid = gate_result.is_valid and not coverage_violations

        if reject_invalid and not proposal_is_valid:
            raise ProposalValidationGateError(
                message="Bản chỉnh sửa đề xuất lịch học vi phạm các ràng buộc kiểm định UC-12.",
                code="PROPOSAL_VALIDATION_FAILED",
                violations=[v.to_dict() for v in combined_violations],
            )

        updated_data = dict(proposal.proposal_data)
        updated_data["tasks"] = normalized_payload["tasks"]
        updated_data["dependencies"] = normalized_payload["dependencies"]
        if "schedule_blocks" in normalized_payload:
            updated_data["schedule_blocks"] = normalized_payload["schedule_blocks"]
        else:
            updated_data.pop("schedule_blocks", None)
        updated_data["soft_overflow_warnings"] = [
            w.to_dict() for w in gate_result.soft_overflow_warnings
        ]
        updated_data["validation_violations"] = [v.to_dict() for v in combined_violations]
        updated_data["is_valid"] = proposal_is_valid
        updated_data["availability_mode"] = avail_config.mode
        updated_data["availability_source_metadata"] = effective_avail.source_metadata
        available_minutes = SpatioTemporalRuleEngine.calculate_available_capacity_minutes(
            avail_config,
            start_date=roadmap.start_date or effective_now.date(),
            target_date=roadmap.target_date,
            existing_tasks=existing_tasks,
        )
        feasibility = assess_schedule_feasibility(
            [task for task in normalized_payload["tasks"] if isinstance(task, dict)],
            available_minutes=available_minutes,
        )
        updated_data["feasibility"] = feasibility.to_dict()
        updated_data["is_partial_schedule"] = feasibility.status is FeasibilityStatus.PARTIAL

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
        advisories = list(gate_result.advisory_warnings)
        for w in effective_avail.warnings:
            if w not in advisories:
                advisories.append(w)
        return ScheduleProposalViewDTO(
            proposal=saved_proposal,
            is_valid=proposal_is_valid,
            violations=[v.to_dict() for v in combined_violations],
            soft_overflow_warnings=[w.to_dict() for w in gate_result.soft_overflow_warnings],
            advisory_warnings=advisories,
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
        block_repo: ScheduleBlockRepositoryPort,
        availability_query_port: AvailabilityQueryPort,
        execution_sync_port: ExecutionScheduleSyncPort,
        schedule_change_log_port: ScheduleChangeLogPort,
        uow: AsyncUnitOfWork,
        user_query_port: UserQueryPort | None = None,
        calendar_connection_query_port: CalendarConnectionQueryPort | None = None,
        calendar_sync_facade: CalendarSyncFacadePort | None = None,
    ) -> None:
        self._roadmap_repo = roadmap_repo
        self._milestone_repo = milestone_repo
        self._proposal_repo = proposal_repo
        self._schedule_repo = schedule_repo
        self._block_repo = block_repo
        self._availability_port = availability_query_port
        self._execution_sync_port = execution_sync_port
        self._change_log_port = schedule_change_log_port
        self._uow = uow
        self._user_query_port = user_query_port
        self._calendar_connection_port = calendar_connection_query_port
        self._calendar_sync_facade = calendar_sync_facade

    @staticmethod
    def _detect_fresh_calendar_conflicts(
        proposal_data: dict[str, Any],
        blocked_intervals: Sequence[dict[str, Any]],
    ) -> list[dict[str, object]]:
        conflicts: list[dict[str, object]] = []
        raw_blocks = proposal_data.get("schedule_blocks")
        raw_tasks = proposal_data.get("tasks", [])

        candidate_sessions: list[dict[str, Any]] = []
        if isinstance(raw_blocks, list) and raw_blocks:
            for b in raw_blocks:
                if isinstance(b, dict):
                    candidate_sessions.append(
                        {
                            "task_id": str(b.get("task_id", "")),
                            "scheduled_start": b.get("scheduled_start"),
                            "scheduled_end": b.get("scheduled_end"),
                        }
                    )
        elif isinstance(raw_tasks, list):
            for t in raw_tasks:
                if isinstance(t, dict) and t.get("scheduled_start") and t.get("scheduled_end"):
                    candidate_sessions.append(
                        {
                            "task_id": str(t.get("task_id") or t.get("id") or ""),
                            "title": str(t.get("title", "")),
                            "scheduled_start": t.get("scheduled_start"),
                            "scheduled_end": t.get("scheduled_end"),
                        }
                    )

        for sess in candidate_sessions:
            s_dt = parse_iso_datetime(sess.get("scheduled_start"))
            e_dt = parse_iso_datetime(sess.get("scheduled_end"))
            if s_dt is None or e_dt is None:
                continue
            for blocked in blocked_intervals:
                b_start = parse_iso_datetime(blocked.get("start_time"))
                b_end = parse_iso_datetime(blocked.get("end_time"))
                if b_start is None or b_end is None:
                    continue
                if s_dt < b_end and b_start < e_dt:
                    conflicts.append(
                        {
                            "task_id": sess.get("task_id"),
                            "scheduled_start": s_dt.isoformat(),
                            "scheduled_end": e_dt.isoformat(),
                            "conflict_source": blocked.get("source", "GOOGLE_CALENDAR_BUSY"),
                            "conflict_start": b_start.isoformat(),
                            "conflict_end": b_end.isoformat(),
                        }
                    )
        return conflicts

    async def execute(
        self,
        *,
        user_id: UUID,
        roadmap_id: UUID,
        proposal_id: UUID,
        confirm_soft_overflow: bool = False,
        confirm_warnings: bool = False,
        confirm_partial_schedule: bool = False,
        idempotency_key: str | None = None,
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

        existing_schedule = await self._schedule_repo.get_by_roadmap_id(roadmap_id)

        # AC-10 Idempotency: If this exact proposal was already APPLIED, return idempotently
        if proposal.status == ScheduleProposalStatus.APPLIED and existing_schedule is not None:
            cached = proposal.proposal_data.get("last_apply_result", {})
            if not isinstance(cached, dict):
                cached = {}
            return ApplyScheduleProposalResultDTO(
                roadmap=roadmap,
                official_schedule=existing_schedule,
                proposal=proposal,
                preserved_completed_tasks_count=int(
                    cached.get("preserved_completed_tasks_count", 0)
                ),
                replaced_tasks_count=int(cached.get("replaced_tasks_count", 0)),
                inserted_tasks_count=int(cached.get("inserted_tasks_count", 0)),
                affected_tasks_count=int(cached.get("affected_tasks_count", 0)),
                total_shifted_minutes=int(cached.get("total_shifted_minutes", 0)),
                trigger_type=str(cached.get("trigger_type", "INITIAL_APPLY")),
                calendar_sync_status=str(cached.get("calendar_sync_status", "NOT_CONNECTED")),
                backlog_unscheduled_tasks_count=int(
                    cached.get("backlog_unscheduled_tasks_count", 0)
                ),
            )

        milestones = await self._milestone_repo.list_by_roadmap_id(roadmap_id)
        valid_mids: set[UUID | str] = {m.id for m in milestones}

        user_tz = "UTC"
        if self._user_query_port is not None:
            user_snapshot = await self._user_query_port.get_user_by_id(user_id)
            user_tz = (
                user_snapshot.timezone
                if user_snapshot is not None and user_snapshot.timezone
                else "Asia/Ho_Chi_Minh"
            )

        active_roadmaps = await self._roadmap_repo.list_by_user_id(user_id, status="ACTIVE")
        other_roadmaps = [r for r in active_roadmaps if r.id != roadmap_id]
        other_ids = [r.id for r in other_roadmaps]
        target_dates = {r.id: r.target_date for r in other_roadmaps}
        existing_tasks = await self._execution_sync_port.get_tasks_for_roadmaps(
            other_ids,
            roadmap_target_dates=target_dates,
        )
        existing_tasks = expand_existing_schedule_occupancy(
            existing_tasks, await self._block_repo.list_by_roadmap_ids(other_ids)
        )

        # AC-09 Fresh Availability & Conflict Revalidation before commit
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

        protected_blocks = (
            [
                block
                for block in await self._block_repo.get_by_schedule_id(existing_schedule.id)
                if block.is_protected and block.status == "PLANNED" and block.task_id is not None
            ]
            if existing_schedule is not None
            else []
        )
        protected_task_ids = {block.task_id for block in protected_blocks if block.task_id}
        current_roadmap_tasks = await self._execution_sync_port.get_tasks_for_roadmaps([roadmap_id])
        protected_tasks = {
            task.task_id: task
            for task in current_roadmap_tasks
            if task.task_id in protected_task_ids
        }
        proposal_tasks_by_id = {
            str(task.get("task_id")): task
            for task in proposal.proposal_data.get("tasks", [])
            if isinstance(task, dict)
        }
        proposed_blocks_by_key = {
            (str(block.get("task_id")), int(block.get("sequence_in_task", 0))): block
            for block in proposal.proposal_data.get("schedule_blocks", [])
            if isinstance(block, dict)
        }
        for task_id, existing_task in protected_tasks.items():
            proposed = proposal_tasks_by_id.get(str(task_id))
            if proposed is None:
                existing_tasks.append(existing_task)
                continue
            if (
                parse_iso_datetime(proposed.get("scheduled_start")) != existing_task.scheduled_start
                or parse_iso_datetime(proposed.get("scheduled_end")) != existing_task.scheduled_end
            ):
                raise ProposalValidationGateError(
                    message="Phiên học được bảo vệ không thể thay đổi khi áp dụng lịch mới.",
                    code="PROTECTED_SESSION_CHANGED",
                )
        for block in protected_blocks:
            if str(block.task_id) not in proposal_tasks_by_id:
                continue
            proposed_block = proposed_blocks_by_key.get(
                (str(block.task_id), block.sequence_in_task)
            )
            if (
                proposed_block is None
                or parse_iso_datetime(proposed_block.get("scheduled_start")) != block.start_time
                or parse_iso_datetime(proposed_block.get("scheduled_end")) != block.end_time
            ):
                raise ProposalValidationGateError(
                    message="Phiên học được bảo vệ không thể thay đổi khi áp dụng lịch mới.",
                    code="PROTECTED_SESSION_CHANGED",
                )

        normalized_data = normalize_proposal_task_ids_and_dependencies(proposal.proposal_data)

        raw_normalized_tasks = [
            task for task in normalized_data.get("tasks", []) if isinstance(task, dict)
        ]
        fresh_capacity_minutes = SpatioTemporalRuleEngine.calculate_available_capacity_minutes(
            avail_config,
            start_date=roadmap.start_date or effective_now.date(),
            target_date=roadmap.target_date,
            existing_tasks=existing_tasks,
        )
        feasibility = assess_schedule_feasibility(
            raw_normalized_tasks,
            available_minutes=fresh_capacity_minutes,
        )
        normalized_data["feasibility"] = feasibility.to_dict()
        normalized_data["is_partial_schedule"] = feasibility.status is FeasibilityStatus.PARTIAL
        if feasibility.status is FeasibilityStatus.INFEASIBLE:
            raise PlanInfeasibleError(feasibility.schedulable_ratio)
        if feasibility.status is FeasibilityStatus.PARTIAL and not confirm_partial_schedule:
            raise PartialScheduleConfirmationRequiredError()

        # AC-09: Check fresh Google Calendar busy intervals for direct time collisions
        google_busy_blocks = [
            b
            for b in effective_avail.blocked_intervals
            if b.get("source") == "GOOGLE_CALENDAR_BUSY"
        ]
        if google_busy_blocks:
            fresh_conflicts = self._detect_fresh_calendar_conflicts(
                normalized_data,
                google_busy_blocks,
            )
            if fresh_conflicts:
                raise FreshCalendarConflictDetectedError(conflicts=fresh_conflicts)

        is_partial_proposal = bool(normalized_data.get("is_partial_schedule", False)) or any(
            isinstance(t, dict) and bool(t.get("unscheduled_reason"))
            for t in normalized_data.get("tasks", [])
        )

        orchestrator = ProposalValidationGateOrchestrator(enable_tier3_judge=False)
        gate_result = await orchestrator.validate_proposal(
            normalized_data,
            availability=avail_config,
            valid_milestone_ids=valid_mids if valid_mids else None,
            existing_tasks=existing_tasks,
            current_roadmap_target_date=roadmap.target_date,
            is_ai_generated=False,
            allow_unscheduled_tasks=is_partial_proposal,
        )
        coverage_violations = validate_task_coverage(
            [task for task in normalized_data.get("tasks", []) if isinstance(task, dict)],
            milestones,
        )

        if not gate_result.is_valid or coverage_violations:
            raise ProposalValidationGateError(
                message="Không thể áp dụng lịch học: phát hiện vi phạm ràng buộc tại cổng kiểm định UC-12.",
                code="PROPOSAL_VALIDATION_FAILED",
                violations=[v.to_dict() for v in [*gate_result.violations, *coverage_violations]],
            )

        user_confirmed = bool(confirm_soft_overflow or confirm_warnings)
        if gate_result.soft_overflow_warnings and not user_confirmed:
            total_overflow = sum(w.overflow_minutes for w in gate_result.soft_overflow_warnings)
            err = SoftOverflowConfirmationRequiredError(overflow_minutes=total_overflow)
            err.warnings = [w.to_dict() for w in gate_result.soft_overflow_warnings]  # type: ignore[attr-defined]
            raise err

        proposal_judge_status = str(normalized_data.get("judge_status", "PASSED")).upper()
        if proposal_judge_status in ("NEEDS_REVIEW", "REVIEW_PENDING") and not user_confirmed:
            raise JudgeReviewConfirmationRequiredError(
                judge_status=proposal_judge_status,
                advisory_warnings=[str(w) for w in normalized_data.get("advisory_warnings", [])],
            )

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
        backlog_unscheduled_count = 0
        for t in raw_tasks:
            if not isinstance(t, dict):
                continue
            tid = UUID(str(t["task_id"]))
            mid_raw = t.get("milestone_id")
            try:
                mid = UUID(str(mid_raw)) if mid_raw else default_mid
            except ValueError:
                mid = default_mid
            s_date = parse_iso_date(t.get("scheduled_date"))
            s_start = parse_iso_datetime(t.get("scheduled_start"))
            s_end = parse_iso_datetime(t.get("scheduled_end"))
            if s_date is None and is_partial_proposal:
                backlog_unscheduled_count += 1
            sync_tasks.append(
                ProposedTaskSyncItemDTO(
                    task_id=tid,
                    milestone_id=mid,
                    title=str(t.get("title", "")).strip(),
                    description=(
                        str(t["description"]).strip() if t.get("description") is not None else None
                    ),
                    estimated_minutes=int(t.get("estimated_minutes", 30) or 30),
                    scheduled_date=s_date,
                    scheduled_start=s_start,
                    scheduled_end=s_end,
                )
            )

        missing_block_times = [
            str(task.task_id)
            for task in sync_tasks
            if (
                not is_partial_proposal
                and (
                    task.scheduled_date is None
                    or task.scheduled_start is None
                    or task.scheduled_end is None
                )
            )
            or (
                is_partial_proposal
                and task.scheduled_date is not None
                and (task.scheduled_start is None or task.scheduled_end is None)
            )
        ]
        if missing_block_times:
            raise ProposalValidationGateError(
                message="Không thể áp dụng lịch học khi nhiệm vụ chưa có ngày và giờ học cụ thể.",
                code="PROPOSAL_VALIDATION_FAILED",
                violations=[
                    {
                        "field": "scheduled_start",
                        "rule_code": "MISSING_SCHEDULE_BLOCK_TIME",
                        "task_id": task_id,
                    }
                    for task_id in missing_block_times
                ],
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
                protected_task_ids=tuple(protected_task_ids),
            )

            current_tasks = await self._execution_sync_port.get_tasks_for_roadmaps([roadmap_id])
            completed_task_ids = {
                task.task_id for task in current_tasks if task.status == "COMPLETED"
            }
            previous_blocks = await self._block_repo.get_by_schedule_id(saved_schedule.id)
            for block in previous_blocks:
                if block.status == "PLANNED" and not block.is_protected:
                    block.status = (
                        "COMPLETED" if block.task_id in completed_task_ids else "CANCELLED"
                    )
                    block.updated_at = effective_now
            await self._block_repo.save_all(previous_blocks)
            blocks: list[ScheduleBlock] = []
            proposed_blocks = normalized_data.get("schedule_blocks")
            if isinstance(proposed_blocks, list):
                for raw_block in proposed_blocks:
                    if not isinstance(raw_block, dict):
                        continue
                    if UUID(str(raw_block["task_id"])) in protected_task_ids:
                        continue
                    block_start = parse_iso_datetime(raw_block.get("scheduled_start"))
                    block_end = parse_iso_datetime(raw_block.get("scheduled_end"))
                    block_date = parse_iso_date(raw_block.get("block_date"))
                    if block_start is None or block_end is None or block_date is None:
                        continue
                    blocks.append(
                        ScheduleBlock(
                            id=generate_uuid7(),
                            roadmap_id=roadmap_id,
                            official_schedule_id=saved_schedule.id,
                            task_id=UUID(str(raw_block["task_id"])),
                            sequence_in_task=int(raw_block["sequence_in_task"]),
                            block_date=block_date,
                            start_time=block_start,
                            end_time=block_end,
                            scheduled_duration_minutes=int(raw_block["scheduled_duration_minutes"]),
                            sync_status="PENDING_SYNC",
                            created_at=effective_now,
                            updated_at=effective_now,
                        )
                    )
            else:
                for task in sync_tasks:
                    if task.task_id in protected_task_ids:
                        continue
                    if task.scheduled_start is None or task.scheduled_end is None:
                        continue
                    duration = int(
                        (task.scheduled_end - task.scheduled_start).total_seconds() // 60
                    )
                    if duration <= 0:
                        continue
                    # Keep session durations bounded independently of task effort.
                    block_count = (duration + 59) // 60
                    base_minutes, extra_minutes = divmod(duration, block_count)
                    cursor = task.scheduled_start
                    for sequence in range(1, block_count + 1):
                        block_minutes = base_minutes + (1 if sequence <= extra_minutes else 0)
                        block_end = cursor + timedelta(minutes=block_minutes)
                        blocks.append(
                            ScheduleBlock(
                                id=generate_uuid7(),
                                roadmap_id=roadmap_id,
                                official_schedule_id=saved_schedule.id,
                                task_id=task.task_id,
                                sequence_in_task=sequence,
                                block_date=cursor.date(),
                                start_time=cursor,
                                end_time=block_end,
                                scheduled_duration_minutes=block_minutes,
                                sync_status="PENDING_SYNC",
                                created_at=effective_now,
                                updated_at=effective_now,
                            )
                        )
                        cursor = block_end
            await self._block_repo.save_all(blocks)
            current_blocks = await self._block_repo.get_by_schedule_id(saved_schedule.id)

            official_schedule.id = saved_schedule.id
            official_schedule.apply_metrics(
                user_id=user_id,
                total_sessions=sum(1 for block in current_blocks if block.status != "CANCELLED"),
                total_planned_minutes=sync_result.total_planned_minutes,
                now=effective_now,
                proposal_id=proposal.id,
            )
            saved_schedule = await self._schedule_repo.save(official_schedule)
            self._uow.collect_events_from(official_schedule)

            if idempotency_key:
                normalized_data["applied_idempotency_key"] = idempotency_key
            normalized_data["last_apply_result"] = {
                "preserved_completed_tasks_count": sync_result.preserved_completed_tasks_count,
                "replaced_tasks_count": sync_result.replaced_tasks_count,
                "inserted_tasks_count": sync_result.inserted_tasks_count,
                "affected_tasks_count": sync_result.affected_tasks_count,
                "total_shifted_minutes": sync_result.total_shifted_minutes,
                "trigger_type": trigger_type,
                "calendar_sync_status": "NOT_CONNECTED",
                "backlog_unscheduled_tasks_count": backlog_unscheduled_count,
            }
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
                    "confirm_warnings": confirm_warnings,
                    "backlog_unscheduled_tasks_count": backlog_unscheduled_count,
                },
                now=effective_now,
            )

            await self._uow.commit()

        # AC-11: Honest Google Calendar Sync after commit
        calendar_sync_status = "NOT_CONNECTED"
        google_meta_status = str(
            effective_avail.source_metadata.get("google_sync_status", "NOT_CONNECTED")
        )
        is_cal_connected = bool(effective_avail.source_metadata.get("calendar_connected", False))
        if google_meta_status == "FAILED_OR_EXPIRED":
            calendar_sync_status = "SYNC_FAILED"
            async with self._uow:
                failed_blocks = await self._block_repo.get_by_schedule_id(saved_schedule.id)
                for b in failed_blocks:
                    if b.status != "CANCELLED":
                        b.sync_status = "SYNC_FAILED"
                        b.updated_at = effective_now
                await self._block_repo.save_all(failed_blocks)
                await self._uow.commit()
        elif is_cal_connected:
            if self._calendar_sync_facade is not None:
                try:
                    facade_status = await self._calendar_sync_facade.sync_schedule_blocks_to_google(
                        schedule_id=saved_schedule.id,
                        user_id=user_id,
                    )
                    refreshed_blocks = [
                        b
                        for b in await self._block_repo.get_by_schedule_id(saved_schedule.id)
                        if b.status != "CANCELLED"
                    ]
                    if any(b.sync_status == "SYNC_FAILED" for b in refreshed_blocks) or (
                        facade_status == "SYNC_FAILED"
                    ):
                        calendar_sync_status = "SYNC_FAILED"
                    elif (
                        not refreshed_blocks
                        or all(b.sync_status == "SYNCED" for b in refreshed_blocks)
                        or facade_status == "SYNCED"
                    ):
                        calendar_sync_status = "SYNCED"
                    elif facade_status in ("NOT_CONNECTED", "PENDING_SYNC"):
                        calendar_sync_status = facade_status
                    else:
                        calendar_sync_status = "PENDING_SYNC"
                except Exception:
                    calendar_sync_status = "SYNC_FAILED"
                    async with self._uow:
                        failed_blocks = await self._block_repo.get_by_schedule_id(saved_schedule.id)
                        for b in failed_blocks:
                            if b.status != "CANCELLED":
                                b.sync_status = "SYNC_FAILED"
                                b.updated_at = effective_now
                        await self._block_repo.save_all(failed_blocks)
                        await self._uow.commit()
            else:
                calendar_sync_status = "PENDING_SYNC"

        if calendar_sync_status != "NOT_CONNECTED":
            async with self._uow:
                updated_prop_data = dict(saved_proposal.proposal_data)
                last_res = dict(updated_prop_data.get("last_apply_result", {}))
                last_res["calendar_sync_status"] = calendar_sync_status
                updated_prop_data["last_apply_result"] = last_res
                saved_proposal.proposal_data = updated_prop_data
                saved_proposal = await self._proposal_repo.save(saved_proposal)
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
            calendar_sync_status=calendar_sync_status,
            backlog_unscheduled_tasks_count=backlog_unscheduled_count,
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
        user_query_port: UserQueryPort | None = None,
        block_repo: ScheduleBlockRepositoryPort | None = None,
        calendar_connection_query_port: CalendarConnectionQueryPort | None = None,
    ) -> None:
        self._goal_repo = goal_repo
        self._roadmap_repo = roadmap_repo
        self._milestone_repo = milestone_repo
        self._proposal_repo = proposal_repo
        self._availability_port = availability_query_port
        self._execution_sync_port = execution_sync_port
        self._uow = uow
        self._user_query_port = user_query_port
        self._block_repo = block_repo
        self._calendar_connection_port = calendar_connection_query_port

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

        user_tz = "UTC"
        if self._user_query_port is not None:
            user_snapshot = await self._user_query_port.get_user_by_id(user_id)
            user_tz = (
                user_snapshot.timezone
                if user_snapshot is not None and user_snapshot.timezone
                else "Asia/Ho_Chi_Minh"
            )

        active_roadmaps = await self._roadmap_repo.list_by_user_id(user_id, status="ACTIVE")
        other_roadmaps = [r for r in active_roadmaps if r.id != roadmap_id]
        other_ids = [r.id for r in other_roadmaps]
        target_dates = {r.id: r.target_date for r in other_roadmaps}
        existing_tasks = await self._execution_sync_port.get_tasks_for_roadmaps(
            other_ids,
            roadmap_target_dates=target_dates,
        )
        if self._block_repo is not None:
            existing_tasks = expand_existing_schedule_occupancy(
                existing_tasks, await self._block_repo.list_by_roadmap_ids(other_ids)
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
        proposal_data["availability_source_metadata"] = effective_avail.source_metadata
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
        advisories = list(gate_result.advisory_warnings)
        for w in effective_avail.warnings:
            if w not in advisories:
                advisories.append(w)
        return ScheduleProposalViewDTO(
            proposal=saved_proposal,
            is_valid=True,
            violations=[],
            soft_overflow_warnings=[w.to_dict() for w in gate_result.soft_overflow_warnings],
            advisory_warnings=advisories,
            diff_summary={
                "proposed_tasks_count": len(proposal_data.get("tasks", [])),
                "proposed_total_minutes": proposed_minutes,
            },
        )


async def _build_reoptimized_draft_proposal(
    *,
    user_id: UUID,
    roadmap_id: UUID,
    proposal_type: ScheduleProposalType,
    start_date_anchor: Any,
    roadmap_repo: RoadmapRepositoryPort,
    milestone_repo: MilestoneRepositoryPort,
    proposal_repo: ScheduleProposalRepositoryPort,
    availability_port: AvailabilityQueryPort,
    execution_sync_port: ExecutionScheduleSyncPort,
    uow: AsyncUnitOfWork,
    learner_profile_port: LearnerProfileQueryPort | None = None,
    user_query_port: UserQueryPort | None = None,
    block_repo: ScheduleBlockRepositoryPort | None = None,
    calendar_connection_query_port: CalendarConnectionQueryPort | None = None,
    effective_now: datetime,
    only_overdue_and_incomplete: bool = False,
) -> ScheduleProposalViewDTO:
    """Shared deterministic schedule re-allocation for Reoptimize (0 credit) & Overdue Recovery (UC-23)."""
    roadmap = await roadmap_repo.get_by_id_for_user(roadmap_id, user_id)
    if roadmap is None:
        raise RoadmapNotFoundError()

    roadmap_tasks = await execution_sync_port.get_tasks_for_roadmaps(
        [roadmap_id],
        roadmap_target_dates={roadmap_id: roadmap.target_date},
    )
    incomplete_tasks = [t for t in roadmap_tasks if t.status in ("TODO", "IN_PROGRESS")]
    if only_overdue_and_incomplete:
        overdue = [
            t
            for t in incomplete_tasks
            if t.scheduled_date is not None and t.scheduled_date < effective_now.date()
        ]
        # Keep existing dependency/order across overdue + remaining incomplete tasks
        target_tasks = incomplete_tasks if overdue else incomplete_tasks
    else:
        target_tasks = incomplete_tasks

    if not target_tasks:
        raise PlanningDomainError(
            message="Không có nhiệm vụ chưa hoàn thành nào để tái tối ưu lịch học.",
            code="NO_TASKS_TO_REOPTIMIZE",
        )

    milestones = await milestone_repo.list_by_roadmap_id(roadmap_id)
    milestone_order_map = {str(m.id): m.sequence_order for m in milestones}
    valid_mids: set[UUID | str] = {m.id for m in milestones}

    user_tz = "Asia/Ho_Chi_Minh"
    if user_query_port is not None:
        user_snapshot = await user_query_port.get_user_by_id(user_id)
        if user_snapshot is not None and user_snapshot.timezone:
            user_tz = user_snapshot.timezone

    pref_minutes = 60
    est_beta = 1.0
    if learner_profile_port is not None:
        profile = await learner_profile_port.get_learner_profile(user_id)
        pref_minutes = int(profile.opt_session_minutes)
        est_beta = float(profile.estimation_bias_beta)

    active_roadmaps = await roadmap_repo.list_by_user_id(user_id, status="ACTIVE")
    other_roadmaps = [r for r in active_roadmaps if r.id != roadmap_id]
    other_ids = [r.id for r in other_roadmaps]
    other_targets = {r.id: r.target_date for r in other_roadmaps}
    other_existing = await execution_sync_port.get_tasks_for_roadmaps(
        other_ids,
        roadmap_target_dates=other_targets,
    )
    if block_repo is not None:
        other_existing = expand_existing_schedule_occupancy(
            other_existing,
            await block_repo.list_by_roadmap_ids(other_ids),
        )

    effective_avail_uc = GetEffectiveAvailabilityUseCase(
        availability_query_port=availability_port,
        calendar_connection_query_port=calendar_connection_query_port,
        execution_sync_port=execution_sync_port,
    )
    effective_avail = await effective_avail_uc.execute(
        user_id=user_id,
        start_date=start_date_anchor,
        target_date=roadmap.target_date,
        timezone=user_tz,
        existing_tasks=other_existing,
        exclude_roadmap_id=roadmap_id,
    )
    avail_config = effective_avail.availability_config
    other_existing = list(effective_avail.effective_existing_tasks)

    unscheduled_items = [
        {
            "task_id": str(t.task_id),
            "milestone_id": str(t.milestone_id),
            "title": t.title,
            "estimated_minutes": int(t.estimated_minutes),
        }
        for t in target_tasks
    ]
    allocated_tasks, schedule_blocks = SpatioTemporalRuleEngine.allocate_task_sessions(
        unscheduled_items,
        avail_config,
        start_date=start_date_anchor,
        target_date=roadmap.target_date,
        existing_tasks=other_existing,
        milestone_order_map=milestone_order_map,
        preferred_session_minutes=pref_minutes,
        estimation_bias_beta=est_beta,
    )
    candidate_payload = {
        "tasks": allocated_tasks,
        "schedule_blocks": schedule_blocks,
        "dependencies": [],
    }
    orchestrator = ProposalValidationGateOrchestrator(enable_tier3_judge=False)
    gate_result = await orchestrator.validate_proposal(
        candidate_payload,
        availability=avail_config,
        valid_milestone_ids=valid_mids if valid_mids else None,
        existing_tasks=other_existing,
        current_roadmap_target_date=roadmap.target_date,
        is_ai_generated=False,
    )
    if not gate_result.is_valid:
        raise ProposalValidationGateError(
            message="Không thể tái tối ưu lịch học với cấu hình thời gian rảnh hiện tại.",
            code="SCHEDULE_REOPTIMIZE_FAILED",
            violations=[v.to_dict() for v in gate_result.violations],
        )

    proposal_data = normalize_proposal_task_ids_and_dependencies(
        gate_result.validated_proposal_data
    )
    proposal_data["source"] = proposal_type.value
    proposal_data["availability_mode"] = avail_config.mode
    proposal_data["availability_source_metadata"] = effective_avail.source_metadata
    proposal = ScheduleProposal(
        id=generate_uuid7(),
        roadmap_id=roadmap_id,
        user_id=user_id,
        proposal_data=proposal_data,
        proposal_type=proposal_type,
        status=ScheduleProposalStatus.DRAFT,
        applied_at=None,
        created_at=effective_now,
        updated_at=effective_now,
    )

    async with uow:
        await proposal_repo.discard_existing_drafts(roadmap_id, effective_now)
        saved_proposal = await proposal_repo.save(proposal)
        await uow.commit()

    proposed_minutes = sum(
        int(t.get("estimated_minutes", 0) or 0)
        for t in proposal_data.get("tasks", [])
        if isinstance(t, dict)
    )
    advisories = list(gate_result.advisory_warnings)
    for w in effective_avail.warnings:
        if w not in advisories:
            advisories.append(w)
    return ScheduleProposalViewDTO(
        proposal=saved_proposal,
        is_valid=True,
        violations=[],
        soft_overflow_warnings=[w.to_dict() for w in gate_result.soft_overflow_warnings],
        advisory_warnings=advisories,
        diff_summary={
            "proposed_tasks_count": len(proposal_data.get("tasks", [])),
            "proposed_total_minutes": proposed_minutes,
            "proposal_type": proposal_type.value,
        },
    )


class ReoptimizeScheduleProposalUseCase:
    """Schedule-only deterministic re-optimization (`0 AI credit`) creating a DRAFT proposal."""

    def __init__(
        self,
        *,
        roadmap_repo: RoadmapRepositoryPort,
        milestone_repo: MilestoneRepositoryPort,
        proposal_repo: ScheduleProposalRepositoryPort,
        availability_query_port: AvailabilityQueryPort,
        execution_sync_port: ExecutionScheduleSyncPort,
        uow: AsyncUnitOfWork,
        learner_profile_port: LearnerProfileQueryPort | None = None,
        user_query_port: UserQueryPort | None = None,
        block_repo: ScheduleBlockRepositoryPort | None = None,
        calendar_connection_query_port: CalendarConnectionQueryPort | None = None,
    ) -> None:
        self._roadmap_repo = roadmap_repo
        self._milestone_repo = milestone_repo
        self._proposal_repo = proposal_repo
        self._availability_port = availability_query_port
        self._execution_sync_port = execution_sync_port
        self._uow = uow
        self._learner_profile_port = learner_profile_port
        self._user_query_port = user_query_port
        self._block_repo = block_repo
        self._calendar_connection_port = calendar_connection_query_port

    async def execute(
        self,
        *,
        user_id: UUID,
        roadmap_id: UUID,
        now: datetime | None = None,
    ) -> ScheduleProposalViewDTO:
        effective_now = now or datetime.now(UTC)
        roadmap = await self._roadmap_repo.get_by_id_for_user(roadmap_id, user_id)
        if roadmap is None:
            raise RoadmapNotFoundError()
        anchor_date = max(effective_now.date(), roadmap.start_date or effective_now.date())
        return await _build_reoptimized_draft_proposal(
            user_id=user_id,
            roadmap_id=roadmap_id,
            proposal_type=ScheduleProposalType.SCHEDULE_ONLY_REOPTIMIZE,
            start_date_anchor=anchor_date,
            roadmap_repo=self._roadmap_repo,
            milestone_repo=self._milestone_repo,
            proposal_repo=self._proposal_repo,
            availability_port=self._availability_port,
            execution_sync_port=self._execution_sync_port,
            uow=self._uow,
            learner_profile_port=self._learner_profile_port,
            user_query_port=self._user_query_port,
            block_repo=self._block_repo,
            calendar_connection_query_port=self._calendar_connection_port,
            effective_now=effective_now,
        )


class InitiateOverdueRecoveryUseCase:
    """UC-23: Generate DRAFT overdue-recovery ScheduleProposal without auto-mutating OfficialSchedule."""

    def __init__(
        self,
        *,
        roadmap_repo: RoadmapRepositoryPort,
        milestone_repo: MilestoneRepositoryPort,
        proposal_repo: ScheduleProposalRepositoryPort,
        availability_query_port: AvailabilityQueryPort,
        execution_sync_port: ExecutionScheduleSyncPort,
        sse_job_store: SseJobPort,
        uow: AsyncUnitOfWork,
        learner_profile_port: LearnerProfileQueryPort | None = None,
        user_query_port: UserQueryPort | None = None,
        block_repo: ScheduleBlockRepositoryPort | None = None,
        calendar_connection_query_port: CalendarConnectionQueryPort | None = None,
    ) -> None:
        self._roadmap_repo = roadmap_repo
        self._milestone_repo = milestone_repo
        self._proposal_repo = proposal_repo
        self._availability_port = availability_query_port
        self._execution_sync_port = execution_sync_port
        self._sse = sse_job_store
        self._uow = uow
        self._learner_profile_port = learner_profile_port
        self._user_query_port = user_query_port
        self._block_repo = block_repo
        self._calendar_connection_port = calendar_connection_query_port

    async def execute(
        self,
        *,
        user_id: UUID,
        roadmap_id: UUID,
        now: datetime | None = None,
    ) -> SseJobTicketDTO:
        effective_now = now or datetime.now(UTC)
        view = await _build_reoptimized_draft_proposal(
            user_id=user_id,
            roadmap_id=roadmap_id,
            proposal_type=ScheduleProposalType.AI_RECOVERY,
            start_date_anchor=effective_now.date(),
            roadmap_repo=self._roadmap_repo,
            milestone_repo=self._milestone_repo,
            proposal_repo=self._proposal_repo,
            availability_port=self._availability_port,
            execution_sync_port=self._execution_sync_port,
            uow=self._uow,
            learner_profile_port=self._learner_profile_port,
            user_query_port=self._user_query_port,
            block_repo=self._block_repo,
            calendar_connection_query_port=self._calendar_connection_port,
            effective_now=effective_now,
            only_overdue_and_incomplete=True,
        )

        job_id = generate_uuid7()
        reservation_id = generate_uuid7()
        await self._sse.create_job(
            job_id=job_id,
            user_id=user_id,
            roadmap_id=roadmap_id,
            reservation_id=reservation_id,
            job_type="OVERDUE_RECOVERY",
            operation=f"OVERDUE_RECOVERY:{roadmap_id}",
        )
        await self._sse.append_event(
            job_id=job_id,
            event="completed",
            status="COMPLETED",
            data={
                "stage": "COMPLETED",
                "progress": 100,
                "delta_text": "Đã tạo bản nháp khôi phục nhiệm vụ quá hạn (DRAFT).",
                "deltaText": "Đã tạo bản nháp khôi phục nhiệm vụ quá hạn (DRAFT).",
                "payload": {
                    "proposal_id": str(view.proposal.id),
                    "roadmap_id": str(roadmap_id),
                    "status": view.proposal.status.value,
                    "proposal_type": ScheduleProposalType.AI_RECOVERY.value,
                },
            },
        )
        return SseJobTicketDTO(
            job_id=job_id,
            reservation_id=reservation_id,
            roadmap_id=roadmap_id,
            job_type="OVERDUE_RECOVERY",
            status="COMPLETED",
            stream_url=f"/api/v1/roadmaps/jobs/{job_id}/stream",
        )
