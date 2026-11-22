from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

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
    ExistingScheduledTaskDTO,
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
from src.planning.application.services.preliminary_feasibility_service import (
    resolve_effective_milestones_for_proposal,
    verify_or_refresh_preliminary_feasibility_for_gate,
)
from src.planning.application.services.repo_lock import call_for_update
from src.planning.application.services.validation_gate import (
    ProposalValidationGateOrchestrator,
)
from src.planning.application.use_cases.proposal_generation_use_cases import (
    normalize_proposal_task_ids_and_dependencies,
)
from src.planning.domain.exceptions.planning_exceptions import (
    FreshCalendarConflictDetectedError,
    JudgeReviewConfirmationRequiredError,
    PartialScheduleConfirmationRequiredError,
    PlanInfeasibleError,
    PlanningDomainError,
    ProposalSupersededError,
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
from src.planning.domain.models.roadmap import Roadmap, RoadmapStatus
from src.planning.domain.models.schedule import (
    OfficialSchedule,
    ScheduleProposal,
    ScheduleProposalStatus,
    ScheduleProposalType,
)
from src.planning.domain.models.schedule_block import ScheduleBlock
from src.planning.domain.services.spatio_temporal_engine import (
    NonSplittableTaskClassifier,
    SpatioTemporalRuleEngine,
)
from src.planning.domain.services.validation_types import (
    ScheduleCompletenessStatus,
    classify_schedule_completeness,
    parse_iso_date,
    parse_iso_datetime,
    safe_parse_iso_date,
    safe_parse_iso_datetime,
)
from src.shared_kernel.application.uow import AsyncUnitOfWork
from src.shared_kernel.config import get_settings
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


_REOPTIMIZE_OR_RECOVERY_SOURCES = frozenset(
    {
        "SCHEDULE_ONLY_REOPTIMIZE",
        "AI_RECOVERY",
        "POST_FAILURE_RESET",
        "REOPTIMIZE_SCHEDULE",
        "OVERDUE_RECOVERY",
    }
)


def _is_reoptimize_or_recovery_proposal(proposal: ScheduleProposal) -> bool:
    return (
        proposal.proposal_type
        in {
            ScheduleProposalType.SCHEDULE_ONLY_REOPTIMIZE,
            ScheduleProposalType.AI_RECOVERY,
            ScheduleProposalType.POST_FAILURE_RESET,
        }
        or str(proposal.proposal_data.get("source") or "") in _REOPTIMIZE_OR_RECOVERY_SOURCES
    )


async def _load_historical_task_lookup(
    proposal_repo: ScheduleProposalRepositoryPort,
    roadmap_id: UUID,
) -> tuple[dict[str, dict[str, Any]], dict[tuple[str, str], dict[str, Any]]]:
    by_task_id: dict[str, dict[str, Any]] = {}
    by_mid_title: dict[tuple[str, str], dict[str, Any]] = {}
    list_fn = getattr(proposal_repo, "list_by_roadmap_id", None)
    if not callable(list_fn):
        return by_task_id, by_mid_title

    proposals = list(await list_fn(roadmap_id))
    proposals.sort(
        key=lambda p: (
            1 if p.status == ScheduleProposalStatus.APPLIED else 0,
            p.applied_at or datetime.min.replace(tzinfo=UTC),
            p.updated_at,
            p.created_at,
        ),
        reverse=True,
    )
    for prop in proposals:
        raw_tasks = prop.proposal_data.get("tasks", [])
        if not isinstance(raw_tasks, list):
            continue
        for t in raw_tasks:
            if not isinstance(t, dict):
                continue
            tid = str(t.get("task_id") or t.get("id") or "").strip()
            if tid and tid not in by_task_id:
                by_task_id[tid] = t
            mid = str(t.get("milestone_id") or "").strip()
            norm_title = " ".join(str(t.get("title") or "").lower().split())
            if mid and norm_title and (mid, norm_title) not in by_mid_title:
                by_mid_title[(mid, norm_title)] = t
    return by_task_id, by_mid_title


def _recover_task_metadata(
    task_dto: ExistingScheduledTaskDTO,
    *,
    hist_by_id: dict[str, dict[str, Any]],
    hist_by_mid_title: dict[tuple[str, str], dict[str, Any]],
    milestone_by_id: dict[str, Milestone],
    task_order: int = 0,
) -> dict[str, Any]:
    tid_str = str(task_dto.task_id)
    mid_str = str(task_dto.milestone_id)
    norm_title = " ".join(task_dto.title.lower().split())
    hist = hist_by_id.get(tid_str) or hist_by_mid_title.get((mid_str, norm_title))
    ms = milestone_by_id.get(mid_str)

    description = (
        hist.get("description")
        if hist is not None and hist.get("description") is not None
        else task_dto.description
    )
    learning_objective = (
        str(hist.get("learning_objective") or "").strip() if hist is not None else ""
    )
    if not learning_objective:
        learning_objective = (
            (task_dto.description or "").strip()
            or (ms.description.strip() if ms is not None and ms.description else "")
            or f"Hoàn thành nhiệm vụ: {task_dto.title}"
        )

    completion_criteria = (
        str(hist.get("completion_criteria") or "").strip() if hist is not None else ""
    )
    if not completion_criteria:
        completion_criteria = (
            ms.completion_criteria.strip() if ms is not None and ms.completion_criteria else ""
        ) or f"Hoàn thành đầy đủ nội dung '{task_dto.title}'"

    if hist is not None and isinstance(hist.get("covered_outcome_ids"), list):
        covered_outcome_ids = [str(o) for o in hist["covered_outcome_ids"] if str(o).strip()]
    elif hist is None and ms is not None and ms.learning_outcomes:
        covered_outcome_ids = [
            f"M{ms.sequence_order}-O{i}" for i in range(1, len(ms.learning_outcomes) + 1)
        ]
    else:
        covered_outcome_ids = []

    if hist is not None and isinstance(hist.get("concept_ids"), list) and hist.get("concept_ids"):
        concept_ids = [str(c).strip() for c in hist["concept_ids"] if str(c).strip()]
    elif task_dto.concept_id:
        concept_ids = [task_dto.concept_id]
    elif hist is None and ms is not None and ms.required_concepts:
        concept_ids = list(ms.required_concepts)
    else:
        concept_ids = []

    if (
        hist is not None
        and isinstance(hist.get("learning_resources"), list)
        and hist.get("learning_resources")
    ):
        learning_resources = [dict(r) for r in hist["learning_resources"] if isinstance(r, dict)]
    else:
        learning_resources = [dict(r) for r in task_dto.learning_resources]

    payload: dict[str, Any] = {
        "task_id": tid_str,
        "milestone_id": mid_str,
        "title": task_dto.title,
        "description": description,
        "estimated_minutes": int(task_dto.estimated_minutes),
        "learning_objective": learning_objective,
        "completion_criteria": completion_criteria,
        "covered_outcome_ids": covered_outcome_ids,
        "concept_ids": concept_ids,
        "learning_resources": learning_resources,
        "task_order": (
            int(hist["task_order"])
            if hist is not None and hist.get("task_order") is not None
            else task_order
        ),
    }
    if hist is not None:
        for opt_key in (
            "task_type",
            "is_non_splittable",
            "non_splittable_source",
            "resource_ids",
        ):
            if opt_key in hist and hist[opt_key] is not None:
                payload[opt_key] = hist[opt_key]
    return payload


async def _build_completed_coverage_tasks(
    *,
    proposal_repo: ScheduleProposalRepositoryPort,
    roadmap_id: UUID,
    current_roadmap_tasks: Sequence[ExistingScheduledTaskDTO],
    milestones: Sequence[Milestone],
    proposal_task_ids: set[str],
) -> list[dict[str, Any]]:
    completed = [
        t
        for t in current_roadmap_tasks
        if t.status == "COMPLETED" and str(t.task_id) not in proposal_task_ids
    ]
    if not completed:
        return []
    hist_by_id, hist_by_mid_title = await _load_historical_task_lookup(proposal_repo, roadmap_id)
    milestone_by_id = {str(m.id): m for m in milestones}
    return [
        _recover_task_metadata(
            t,
            hist_by_id=hist_by_id,
            hist_by_mid_title=hist_by_mid_title,
            milestone_by_id=milestone_by_id,
        )
        for t in completed
    ]


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
        goal_repo: GoalRepositoryPort | None = None,
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
        self._goal_repo = goal_repo

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
        if proposal.status != ScheduleProposalStatus.DRAFT:
            raise PlanningDomainError(
                message=(
                    "Chỉ có thể chỉnh sửa đề xuất ở trạng thái DRAFT "
                    f"(hiện tại: {proposal.status.value})."
                ),
                code="INVALID_PROPOSAL_STATE_TRANSITION",
            )

        milestones = await self._milestone_repo.list_by_roadmap_id(roadmap_id)
        kept_milestones = resolve_effective_milestones_for_proposal(
            roadmap,
            milestones,
            require_all_approved_without_prelim=False,
        )

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

        await verify_or_refresh_preliminary_feasibility_for_gate(
            user_id=user_id,
            roadmap=roadmap,
            milestones=milestones,
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
            preloaded_avail=avail_config,
            preloaded_existing_tasks=existing_tasks,
            raise_on_stale_fit_capacity=True,
            now=effective_now,
        )
        kept_milestones = resolve_effective_milestones_for_proposal(
            roadmap,
            milestones,
            require_all_approved_without_prelim=False,
        )
        valid_mids: set[UUID | str] = {m.id for m in kept_milestones}

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
        completed_coverage_tasks: list[dict[str, Any]] = []
        if _is_reoptimize_or_recovery_proposal(proposal):
            current_roadmap_tasks = await self._execution_sync_port.get_tasks_for_roadmaps(
                [roadmap_id]
            )
            proposal_tids = {
                str(t.get("task_id")) for t in normalized_payload["tasks"] if isinstance(t, dict)
            }
            completed_coverage_tasks = await _build_completed_coverage_tasks(
                proposal_repo=self._proposal_repo,
                roadmap_id=roadmap_id,
                current_roadmap_tasks=current_roadmap_tasks,
                milestones=kept_milestones,
                proposal_task_ids=proposal_tids,
            )
        coverage_violations = validate_task_coverage(
            normalized_payload["tasks"],
            kept_milestones,
            completed_tasks=completed_coverage_tasks,
        )
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
        normalized_tasks = [task for task in normalized_payload["tasks"] if isinstance(task, dict)]
        feasibility = assess_schedule_feasibility(
            normalized_tasks,
            available_minutes=available_minutes,
        )
        scheduled_tasks_count = sum(
            1
            for task in normalized_tasks
            if safe_parse_iso_date(task.get("scheduled_date")) is not None
        )
        unscheduled_tasks = [
            dict(task)
            for task in normalized_tasks
            if safe_parse_iso_date(task.get("scheduled_date")) is None
        ]
        unscheduled_tasks_count = len(unscheduled_tasks)
        raw_blocks = updated_data.get("schedule_blocks")
        has_blocks = isinstance(raw_blocks, list) and any(isinstance(b, dict) for b in raw_blocks)
        all_scheduled_have_times = scheduled_tasks_count > 0 and all(
            safe_parse_iso_datetime(t.get("scheduled_start")) is not None
            and safe_parse_iso_datetime(t.get("scheduled_end")) is not None
            for t in normalized_tasks
            if safe_parse_iso_date(t.get("scheduled_date")) is not None
        )
        if proposal_is_valid:
            if unscheduled_tasks_count == 0:
                refreshed_verdict = "VERIFIED_FEASIBLE"
            elif unchanged_schedule and proposal.proposal_data.get("feasibility_verdict") in (
                "EXPLICIT_UNSCHEDULABLE",
                "HEURISTIC_ALLOCATION_INCOMPLETE",
            ):
                refreshed_verdict = str(proposal.proposal_data["feasibility_verdict"])
            else:
                refreshed_verdict = "EXPLICIT_UNSCHEDULABLE"
        else:
            refreshed_verdict = (
                "EXPLICIT_UNSCHEDULABLE"
                if feasibility.status is FeasibilityStatus.INFEASIBLE
                else "UNDETERMINED"
            )
        completeness_status: ScheduleCompletenessStatus = classify_schedule_completeness(
            total_tasks=len(normalized_tasks),
            scheduled_tasks_count=scheduled_tasks_count,
            unscheduled_tasks_count=unscheduled_tasks_count,
            available_minutes=available_minutes,
            schedulable_ratio=feasibility.schedulable_ratio,
            feasibility_verdict=refreshed_verdict,
            has_schedule_blocks=has_blocks,
            all_scheduled_have_block_times=all_scheduled_have_times,
            allow_partial_schedule=True,
        )
        updated_data["feasibility"] = feasibility.to_dict()
        updated_data["feasibility_verdict"] = refreshed_verdict
        updated_data["schedule_completeness_status"] = completeness_status
        updated_data["scheduled_tasks_count"] = scheduled_tasks_count
        updated_data["unscheduled_tasks_count"] = unscheduled_tasks_count
        updated_data["unscheduled_tasks"] = unscheduled_tasks
        updated_data["is_partial_schedule"] = completeness_status == "PARTIAL"

        async with self._uow:
            locked_roadmap = await call_for_update(
                self._roadmap_repo.get_by_id_for_user, roadmap_id, user_id
            )
            if locked_roadmap is None:
                raise RoadmapNotFoundError()
            locked_proposal = await call_for_update(self._proposal_repo.get_by_id, proposal_id)
            if (
                locked_proposal is None
                or locked_proposal.roadmap_id != roadmap_id
                or locked_proposal.user_id != user_id
            ):
                raise ScheduleProposalNotFoundError()
            if locked_proposal.status != ScheduleProposalStatus.DRAFT:
                raise PlanningDomainError(
                    message=(
                        "Chỉ có thể chỉnh sửa đề xuất ở trạng thái DRAFT "
                        f"(hiện tại: {locked_proposal.status.value})."
                    ),
                    code="INVALID_PROPOSAL_STATE_TRANSITION",
                )
            locked_proposal.proposal_data = updated_data
            locked_proposal.updated_at = effective_now
            saved_proposal = await self._proposal_repo.save(locked_proposal)
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
        goal_repo: GoalRepositoryPort | None = None,
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
        self._goal_repo = goal_repo

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

    @staticmethod
    def _build_idempotent_apply_result(
        roadmap: Roadmap,
        schedule: OfficialSchedule,
        proposal: ScheduleProposal,
    ) -> ApplyScheduleProposalResultDTO:
        cached = proposal.proposal_data.get("last_apply_result", {})
        if not isinstance(cached, dict):
            cached = {}
        return ApplyScheduleProposalResultDTO(
            roadmap=roadmap,
            official_schedule=schedule,
            proposal=proposal,
            preserved_completed_tasks_count=int(cached.get("preserved_completed_tasks_count", 0)),
            replaced_tasks_count=int(cached.get("replaced_tasks_count", 0)),
            inserted_tasks_count=int(cached.get("inserted_tasks_count", 0)),
            affected_tasks_count=int(cached.get("affected_tasks_count", 0)),
            total_shifted_minutes=int(cached.get("total_shifted_minutes", 0)),
            trigger_type=str(cached.get("trigger_type", "INITIAL_APPLY")),
            calendar_sync_status=str(cached.get("calendar_sync_status", "NOT_CONNECTED")),
            backlog_unscheduled_tasks_count=int(cached.get("backlog_unscheduled_tasks_count", 0)),
        )

    @staticmethod
    def _normalize_idempotency_key(value: object) -> str | None:
        if not isinstance(value, str):
            return None
        cleaned = value.strip()
        return cleaned if cleaned else None

    async def _resolve_applied_proposal_idempotency(
        self,
        *,
        roadmap: Roadmap,
        proposal: ScheduleProposal,
        existing_schedule: OfficialSchedule | None,
        idempotency_key: str | None,
    ) -> ApplyScheduleProposalResultDTO:
        if existing_schedule is None:
            raise ProposalSupersededError(
                message="Không thể áp dụng lại đề xuất vì lịch học chính thức không tồn tại.",
            )

        proposal_ts = proposal.applied_at or proposal.created_at
        proposal_updated_ts = proposal.applied_at or proposal.updated_at
        if existing_schedule.activated_at > proposal_updated_ts:
            raise ProposalSupersededError()

        list_fn = getattr(self._proposal_repo, "list_by_roadmap_id", None)
        if callable(list_fn):
            roadmap_proposals = list(await list_fn(roadmap.id))
            for other in roadmap_proposals:
                if other.id == proposal.id:
                    continue
                if other.status == ScheduleProposalStatus.APPLIED:
                    other_ts = other.applied_at or other.created_at
                    if (other_ts, other.id) > (proposal_ts, proposal.id):
                        raise ProposalSupersededError()
                elif other.status == ScheduleProposalStatus.DRAFT:
                    if other.created_at > proposal_ts:
                        raise ProposalSupersededError()

        req_key = self._normalize_idempotency_key(idempotency_key)
        raw_applied_key = (
            proposal.proposal_data.get("applied_idempotency_key")
            if isinstance(proposal.proposal_data, dict)
            else None
        )
        applied_key = self._normalize_idempotency_key(raw_applied_key)
        if req_key != applied_key:
            raise ProposalSupersededError(
                message="Đề xuất này đã được áp dụng với khóa lũy đẳng khác.",
            )

        return self._build_idempotent_apply_result(roadmap, existing_schedule, proposal)

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

        # AC-10 Idempotency: Only return cached result if APPLIED proposal is NOT superseded
        # and Idempotency-Key strictly matches applied_idempotency_key.
        if proposal.status == ScheduleProposalStatus.APPLIED:
            return await self._resolve_applied_proposal_idempotency(
                roadmap=roadmap,
                proposal=proposal,
                existing_schedule=existing_schedule,
                idempotency_key=idempotency_key,
            )

        if proposal.status != ScheduleProposalStatus.DRAFT:
            raise PlanningDomainError(
                message=(
                    "Chỉ có thể áp dụng đề xuất ở trạng thái DRAFT "
                    f"(hiện tại: {proposal.status.value})."
                ),
                code="INVALID_PROPOSAL_STATE_TRANSITION",
            )

        milestones = await self._milestone_repo.list_by_roadmap_id(roadmap_id)
        kept_milestones = resolve_effective_milestones_for_proposal(
            roadmap,
            milestones,
            require_all_approved_without_prelim=False,
        )

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

        await verify_or_refresh_preliminary_feasibility_for_gate(
            user_id=user_id,
            roadmap=roadmap,
            milestones=milestones,
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
            preloaded_avail=avail_config,
            preloaded_existing_tasks=existing_tasks,
            raise_on_stale_fit_capacity=True,
            now=effective_now,
        )
        kept_milestones = resolve_effective_milestones_for_proposal(
            roadmap,
            milestones,
            require_all_approved_without_prelim=False,
        )
        valid_mids: set[UUID | str] = {m.id for m in kept_milestones}

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
        inconsistent_tasks = [
            (idx, str(task.get("task_id") or ""))
            for idx, task in enumerate(raw_normalized_tasks)
            if safe_parse_iso_date(task.get("scheduled_date")) is not None
            and bool(str(task.get("unscheduled_reason") or "").strip())
        ]
        if inconsistent_tasks:
            raise ProposalValidationGateError(
                message=(
                    "Không thể áp dụng lịch học: có nhiệm vụ vừa có ngày xếp lịch vừa có "
                    "lý do chưa xếp lịch."
                ),
                code="PROPOSAL_VALIDATION_FAILED",
                violations=[
                    {
                        "task_index": idx,
                        "task_id": tid,
                        "field": "unscheduled_reason",
                        "rule_code": "INCONSISTENT_TASK_SCHEDULE_STATE",
                    }
                    for idx, tid in inconsistent_tasks
                ],
            )

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
        scheduled_tasks_count = sum(
            1
            for task in raw_normalized_tasks
            if safe_parse_iso_date(task.get("scheduled_date")) is not None
        )
        unscheduled_tasks_count = len(raw_normalized_tasks) - scheduled_tasks_count
        raw_blocks = normalized_data.get("schedule_blocks")
        has_blocks = isinstance(raw_blocks, list) and any(isinstance(b, dict) for b in raw_blocks)
        all_scheduled_have_times = scheduled_tasks_count > 0 and all(
            safe_parse_iso_datetime(t.get("scheduled_start")) is not None
            and safe_parse_iso_datetime(t.get("scheduled_end")) is not None
            for t in raw_normalized_tasks
            if safe_parse_iso_date(t.get("scheduled_date")) is not None
        )
        raw_verdict = normalized_data.get("feasibility_verdict")
        completeness_status = classify_schedule_completeness(
            total_tasks=len(raw_normalized_tasks),
            scheduled_tasks_count=scheduled_tasks_count,
            unscheduled_tasks_count=unscheduled_tasks_count,
            available_minutes=fresh_capacity_minutes,
            schedulable_ratio=feasibility.schedulable_ratio,
            feasibility_verdict=str(raw_verdict) if raw_verdict is not None else None,
            has_schedule_blocks=has_blocks,
            all_scheduled_have_block_times=all_scheduled_have_times,
            allow_partial_schedule=True,
        )
        normalized_data["feasibility"] = feasibility.to_dict()
        normalized_data["schedule_completeness_status"] = completeness_status
        normalized_data["is_partial_schedule"] = completeness_status == "PARTIAL"
        if (
            completeness_status == "INFEASIBLE"
            or feasibility.status is FeasibilityStatus.INFEASIBLE
        ):
            raise PlanInfeasibleError(feasibility.schedulable_ratio)
        if completeness_status == "UNDETERMINED":
            raise ProposalValidationGateError(
                message=(
                    "Không thể áp dụng lịch học khi trạng thái hoàn thiện lịch chưa được "
                    "xác định tất định (UNDETERMINED)."
                ),
                code="PROPOSAL_VALIDATION_FAILED",
                violations=[
                    {
                        "field": "schedule_completeness_status",
                        "rule_code": "SCHEDULE_COMPLETENESS_UNDETERMINED",
                    }
                ],
            )

        has_unscheduled_or_reason = any(
            safe_parse_iso_date(t.get("scheduled_date")) is None
            or bool(str(t.get("unscheduled_reason") or "").strip())
            for t in raw_normalized_tasks
        )
        if (
            completeness_status == "PARTIAL" or has_unscheduled_or_reason
        ) and not confirm_partial_schedule:
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

        is_partial_proposal = completeness_status == "PARTIAL" or has_unscheduled_or_reason

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
        proposal_tasks_list = [
            task for task in normalized_data.get("tasks", []) if isinstance(task, dict)
        ]
        completed_coverage_tasks: list[dict[str, Any]] = []
        if existing_schedule is not None or _is_reoptimize_or_recovery_proposal(proposal):
            completed_coverage_tasks = await _build_completed_coverage_tasks(
                proposal_repo=self._proposal_repo,
                roadmap_id=roadmap_id,
                current_roadmap_tasks=current_roadmap_tasks,
                milestones=kept_milestones,
                proposal_task_ids=set(proposal_tasks_by_id),
            )
        coverage_violations = validate_task_coverage(
            proposal_tasks_list,
            kept_milestones,
            completed_tasks=completed_coverage_tasks,
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
        if (
            proposal_judge_status in ("NEEDS_REVIEW", "REVIEW_PENDING", "FAILED", "ERROR")
            and not user_confirmed
        ):
            raise JudgeReviewConfirmationRequiredError(
                judge_status=proposal_judge_status,
                advisory_warnings=[str(w) for w in normalized_data.get("advisory_warnings", [])],
            )

        effective_tier = tier or "FREE"
        if tier is None and self._user_query_port is not None:
            user_snap = await self._user_query_port.get_user_by_id(user_id)
            if user_snap is not None:
                effective_tier = user_snap.tier

        raw_tasks = normalized_data.get("tasks", [])
        raw_deps = normalized_data.get("dependencies", [])

        sync_tasks: list[ProposedTaskSyncItemDTO] = []
        default_mid = kept_milestones[0].id if kept_milestones else generate_uuid7()
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
            raw_concept_ids = t.get("concept_ids")
            primary_concept_id: str | None = None
            raw_single_cid = t.get("concept_id")
            if isinstance(raw_single_cid, str) and raw_single_cid.strip():
                primary_concept_id = raw_single_cid.strip()
            elif isinstance(raw_concept_ids, list):
                for cid in raw_concept_ids:
                    if isinstance(cid, str) and cid.strip():
                        primary_concept_id = cid.strip()
                        break
            raw_resources = t.get("learning_resources")
            resources_tuple = (
                tuple(dict(r) for r in raw_resources if isinstance(r, dict))
                if isinstance(raw_resources, list)
                else ()
            )
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
                    concept_id=primary_concept_id,
                    learning_resources=resources_tuple,
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

        async with self._uow:
            # DEF-11: Acquire deterministic row locks across all user roadmaps (`ORDER BY id ASC`)
            # plus target proposal and official schedule to serialize concurrent Apply calls.
            locked_roadmaps = await call_for_update(self._roadmap_repo.list_by_user_id, user_id)
            locked_roadmap = next((r for r in locked_roadmaps if r.id == roadmap_id), None)
            if locked_roadmap is None:
                locked_roadmap = await call_for_update(
                    self._roadmap_repo.get_by_id_for_user, roadmap_id, user_id
                )
            if locked_roadmap is None:
                raise RoadmapNotFoundError()

            locked_proposal = await call_for_update(self._proposal_repo.get_by_id, proposal_id)
            if (
                locked_proposal is None
                or locked_proposal.roadmap_id != roadmap_id
                or locked_proposal.user_id != user_id
            ):
                raise ScheduleProposalNotFoundError()

            locked_schedule = await call_for_update(
                self._schedule_repo.get_by_roadmap_id, roadmap_id
            )

            if locked_proposal.status == ScheduleProposalStatus.APPLIED:
                return await self._resolve_applied_proposal_idempotency(
                    roadmap=locked_roadmap,
                    proposal=locked_proposal,
                    existing_schedule=locked_schedule,
                    idempotency_key=idempotency_key,
                )
            if locked_proposal.status != ScheduleProposalStatus.DRAFT:
                raise PlanningDomainError(
                    message=(
                        "Chỉ có thể áp dụng đề xuất ở trạng thái DRAFT "
                        f"(hiện tại: {locked_proposal.status.value})."
                    ),
                    code="INVALID_PROPOSAL_STATE_TRANSITION",
                )

            if locked_roadmaps:
                fresh_other_roadmaps = [
                    r
                    for r in locked_roadmaps
                    if r.id != roadmap_id and r.status == RoadmapStatus.ACTIVE
                ]
                fresh_active_count = len(fresh_other_roadmaps)
            else:
                fresh_active_count = await self._roadmap_repo.count_active_by_user_id(
                    user_id,
                    exclude_roadmap_id=roadmap_id,
                )
                fresh_active_roadmaps = await self._roadmap_repo.list_by_user_id(
                    user_id, status="ACTIVE"
                )
                fresh_other_roadmaps = [r for r in fresh_active_roadmaps if r.id != roadmap_id]

            if fresh_other_roadmaps:
                fresh_other_ids = [r.id for r in fresh_other_roadmaps]
                fresh_target_dates = {r.id: r.target_date for r in fresh_other_roadmaps}
                fresh_other_tasks = await self._execution_sync_port.get_tasks_for_roadmaps(
                    fresh_other_ids,
                    roadmap_target_dates=fresh_target_dates,
                )
                fresh_other_tasks = expand_existing_schedule_occupancy(
                    fresh_other_tasks,
                    await self._block_repo.list_by_roadmap_ids(fresh_other_ids),
                )
                other_busy_blocks = [
                    {
                        "source": "ACTIVE_ROADMAP_SLOT_CONFLICT",
                        "start_time": t.scheduled_start.isoformat(),
                        "end_time": t.scheduled_end.isoformat(),
                    }
                    for t in fresh_other_tasks
                    if t.scheduled_start is not None and t.scheduled_end is not None
                ]
                if other_busy_blocks:
                    concurrent_conflicts = self._detect_fresh_calendar_conflicts(
                        normalized_data,
                        other_busy_blocks,
                    )
                    if concurrent_conflicts:
                        raise FreshCalendarConflictDetectedError(conflicts=concurrent_conflicts)
                non_other_existing = [
                    t
                    for t in existing_tasks
                    if t.roadmap_id == UUID(int=0) or t.roadmap_id == roadmap_id
                ]
                locked_existing_tasks = [*fresh_other_tasks, *non_other_existing]
                locked_gate = await orchestrator.validate_proposal(
                    normalized_data,
                    availability=avail_config,
                    valid_milestone_ids=valid_mids if valid_mids else None,
                    existing_tasks=locked_existing_tasks,
                    current_roadmap_target_date=locked_roadmap.target_date,
                    is_ai_generated=False,
                    allow_unscheduled_tasks=is_partial_proposal,
                )
                if not locked_gate.is_valid:
                    raise ProposalValidationGateError(
                        message=(
                            "Không thể áp dụng lịch học: phát hiện xung đột đồng thời với lộ trình đang hoạt động."
                        ),
                        code="PROPOSAL_VALIDATION_FAILED",
                        violations=[v.to_dict() for v in locked_gate.violations],
                    )

            is_replan = locked_schedule is not None
            trigger_type = "REPLAN_MERGE" if is_replan else "INITIAL_APPLY"

            official_schedule = locked_schedule or OfficialSchedule(
                id=generate_uuid7(),
                roadmap_id=roadmap_id,
                total_sessions=len(sync_tasks),
                total_planned_minutes=sum(t.estimated_minutes for t in sync_tasks),
                activated_at=effective_now,
                created_at=effective_now,
                updated_at=effective_now,
            )

            locked_roadmap.activate(
                effective_now,
                tier=effective_tier,
                current_active_count=fresh_active_count,
            )
            saved_roadmap = await self._roadmap_repo.save(locked_roadmap)

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
                if (
                    block.status == "PLANNED"
                    and not block.is_protected
                    and block.task_id not in protected_task_ids
                ):
                    block.status = (
                        "COMPLETED" if block.task_id in completed_task_ids else "CANCELLED"
                    )
                    block.updated_at = effective_now
            await self._block_repo.save_all(previous_blocks)
            blocks: list[ScheduleBlock] = []
            task_id_remap = getattr(sync_result, "task_id_remap", {}) or {}
            proposed_blocks = normalized_data.get("schedule_blocks")
            if isinstance(proposed_blocks, list):
                for raw_block in proposed_blocks:
                    if not isinstance(raw_block, dict):
                        continue
                    raw_tid = UUID(str(raw_block["task_id"]))
                    if raw_tid in protected_task_ids:
                        continue
                    effective_tid = task_id_remap.get(raw_tid, raw_tid)
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
                            task_id=effective_tid,
                            sequence_in_task=int(raw_block["sequence_in_task"]),
                            block_type=str(raw_block.get("block_type") or "STUDY"),
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
                raw_tasks_by_id = {
                    str(rt.get("task_id")): rt
                    for rt in raw_tasks
                    if isinstance(rt, dict) and rt.get("task_id") is not None
                }
                is_manual_proposal = str(normalized_data.get("source") or "").upper() == "MANUAL"
                for task in sync_tasks:
                    if task.task_id in protected_task_ids:
                        continue
                    effective_tid = task_id_remap.get(task.task_id, task.task_id)
                    if task.scheduled_start is None or task.scheduled_end is None:
                        continue
                    duration = int(
                        (task.scheduled_end - task.scheduled_start).total_seconds() // 60
                    )
                    if duration <= 0:
                        continue
                    raw_t = raw_tasks_by_id.get(str(task.task_id), {"title": task.title})
                    is_non_splittable = NonSplittableTaskClassifier.is_non_splittable(raw_t)
                    is_manual_contiguous = (
                        is_manual_proposal and abs(duration - int(task.estimated_minutes)) <= 1
                    )
                    if duration <= 240 and (is_non_splittable or is_manual_contiguous):
                        block_count = 1
                    else:
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
                                task_id=effective_tid,
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
                proposal_id=locked_proposal.id,
            )
            saved_schedule = await self._schedule_repo.save(official_schedule)
            self._uow.collect_events_from(official_schedule)

            clean_idem_key = self._normalize_idempotency_key(idempotency_key)
            if clean_idem_key is not None:
                normalized_data["applied_idempotency_key"] = clean_idem_key
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
            locked_proposal.proposal_data = normalized_data
            locked_proposal.mark_applied(effective_now)
            saved_proposal = await self._proposal_repo.save(locked_proposal)

            await self._change_log_port.record_change_log(
                roadmap_id=roadmap_id,
                schedule_id=saved_schedule.id,
                trigger_type=trigger_type,
                reason=f"Áp dụng lịch học chính thức ({trigger_type}) từ đề xuất {locked_proposal.id}",
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

        raw_tasks_sum_by_mid: dict[str, int] = {}
        raw_tasks_sum_by_seq: dict[int, int] = {}
        total_raw_task_minutes = 0
        for raw_t in tasks:
            if isinstance(raw_t, dict):
                est = max(0, int(raw_t.get("estimated_minutes", 45) or 0))
                t_mid = str(raw_t.get("milestone_id") or "").strip()
                t_seq = int(raw_t.get("milestone_sequence_order") or 0)
            else:
                est = max(0, int(getattr(raw_t, "estimated_minutes", 45) or 0))
                t_mid = str(getattr(raw_t, "milestone_id", "") or "").strip()
                t_seq = int(getattr(raw_t, "milestone_sequence_order", 0) or 0)
            total_raw_task_minutes += est
            if t_mid:
                raw_tasks_sum_by_mid[t_mid] = raw_tasks_sum_by_mid.get(t_mid, 0) + est
            if t_seq >= 1:
                raw_tasks_sum_by_seq[t_seq] = raw_tasks_sum_by_seq.get(t_seq, 0) + est

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
                    raw_effort = m_in.get("estimated_effort_minutes")
                    raw_outcomes = m_in.get("learning_outcomes")
                    raw_criteria = m_in.get("completion_criteria")
                    raw_req_concepts = m_in.get("required_concepts")
                    raw_unver_concepts = m_in.get("unverified_concepts")
                    raw_prereqs = m_in.get("prerequisite_milestone_ids")
                else:
                    mid_uuid = m_in.milestone_id or generate_uuid7()
                    seq = m_in.sequence_order if m_in.sequence_order >= 1 else idx
                    title = m_in.title
                    desc = m_in.description
                    raw_effort = m_in.estimated_effort_minutes
                    raw_outcomes = m_in.learning_outcomes
                    raw_criteria = m_in.completion_criteria
                    raw_req_concepts = m_in.required_concepts
                    raw_unver_concepts = m_in.unverified_concepts
                    raw_prereqs = m_in.prerequisite_milestone_ids

                prev = existing_by_id.get(mid_uuid)
                sum_task_minutes = (
                    raw_tasks_sum_by_mid.get(str(mid_uuid), 0)
                    or raw_tasks_sum_by_seq.get(seq, 0)
                    or (total_raw_task_minutes if len(milestones) == 1 else 0)
                )
                if raw_effort is not None and int(raw_effort) > 0:
                    effective_effort = int(raw_effort)
                elif prev is not None and prev.estimated_effort_minutes > 0:
                    effective_effort = prev.estimated_effort_minutes
                else:
                    effective_effort = max(60, sum_task_minutes)

                parsed_outcomes = tuple(
                    str(o).strip() for o in (raw_outcomes or ()) if str(o).strip()
                )
                effective_outcomes = (
                    parsed_outcomes
                    if parsed_outcomes
                    else (prev.learning_outcomes if prev is not None else ())
                )
                effective_criteria = (
                    str(raw_criteria).strip() or None
                    if raw_criteria is not None
                    else (prev.completion_criteria if prev is not None else None)
                )
                parsed_req = tuple(
                    str(c).strip() for c in (raw_req_concepts or ()) if str(c).strip()
                )
                effective_req = (
                    parsed_req
                    if parsed_req
                    else (prev.required_concepts if prev is not None else ())
                )
                parsed_unver = tuple(
                    str(c).strip() for c in (raw_unver_concepts or ()) if str(c).strip()
                )
                effective_unver = (
                    parsed_unver
                    if parsed_unver
                    else (prev.unverified_concepts if prev is not None else ())
                )
                parsed_prereqs = tuple(
                    pid if isinstance(pid, UUID) else UUID(str(pid))
                    for pid in (raw_prereqs or ())
                    if pid
                )
                effective_prereqs = (
                    parsed_prereqs
                    if parsed_prereqs
                    else (prev.prerequisite_milestone_ids if prev is not None else ())
                )

                built_milestones.append(
                    Milestone(
                        id=mid_uuid,
                        roadmap_id=roadmap_id,
                        sequence_order=seq,
                        title=title,
                        description=desc,
                        learning_outcomes=effective_outcomes,
                        completion_criteria=effective_criteria,
                        estimated_effort_minutes=effective_effort,
                        required_concepts=effective_req,
                        unverified_concepts=effective_unver,
                        prerequisite_milestone_ids=effective_prereqs,
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
                    estimated_effort_minutes=max(60, total_raw_task_minutes),
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
            await self._milestone_repo.approve_all_for_roadmap(roadmap_id, effective_now)
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


async def _resolve_planned_blocks_and_protected(
    *,
    roadmap_id: UUID,
    schedule_repo: OfficialScheduleRepositoryPort | None,
    block_repo: ScheduleBlockRepositoryPort | None,
) -> tuple[set[UUID], dict[UUID, list[ScheduleBlock]]]:
    if block_repo is None:
        return set(), {}
    existing_schedule = (
        await schedule_repo.get_by_roadmap_id(roadmap_id) if schedule_repo is not None else None
    )
    if existing_schedule is not None:
        raw_blocks = await block_repo.get_by_schedule_id(existing_schedule.id)
    else:
        raw_blocks = await block_repo.list_by_roadmap_ids([roadmap_id])
    planned = [b for b in raw_blocks if b.status == "PLANNED" and b.task_id is not None]
    protected_ids = {b.task_id for b in planned if b.is_protected and b.task_id is not None}
    by_task: dict[UUID, list[ScheduleBlock]] = {}
    for b in planned:
        if b.task_id is not None:
            by_task.setdefault(b.task_id, []).append(b)
    for task_blocks in by_task.values():
        task_blocks.sort(key=lambda blk: (blk.sequence_in_task, blk.start_time))
    return protected_ids, by_task


def _compute_overdue_descendants(
    overdue_ids: set[UUID],
    deps: Sequence[dict[str, Any]],
) -> set[UUID]:
    adj: dict[str, list[str]] = {}
    for dep in deps:
        pred = str(dep.get("predecessor_id") or "")
        succ = str(dep.get("successor_id") or "")
        if pred and succ:
            adj.setdefault(pred, []).append(succ)
    descendants: set[UUID] = set()
    queue: list[str] = [str(oid) for oid in overdue_ids]
    visited: set[str] = set(queue)
    while queue:
        cur = queue.pop(0)
        for nxt in adj.get(cur, ()):
            if nxt not in visited:
                visited.add(nxt)
                try:
                    descendants.add(UUID(nxt))
                except ValueError:
                    continue
                queue.append(nxt)
    return descendants


def _drop_overlapping_non_protected_pins(
    pinned_ids: set[UUID],
    *,
    protected_ids: set[UUID],
    tasks_by_id: dict[UUID, ExistingScheduledTaskDTO],
    planned_blocks_by_task: dict[UUID, list[ScheduleBlock]],
) -> set[UUID]:
    def _intervals_for(tid: UUID) -> list[tuple[datetime, datetime]]:
        blks = planned_blocks_by_task.get(tid)
        if blks:
            return [(b.start_time, b.end_time) for b in blks]
        t = tasks_by_id.get(tid)
        if t is not None and t.scheduled_start is not None and t.scheduled_end is not None:
            return [(t.scheduled_start, t.scheduled_end)]
        return []

    accepted_intervals: list[tuple[datetime, datetime]] = []
    kept: set[UUID] = set()
    for pid in sorted(protected_ids & pinned_ids, key=str):
        kept.add(pid)
        accepted_intervals.extend(_intervals_for(pid))

    non_protected = sorted(
        pinned_ids - protected_ids,
        key=lambda tid: (
            tasks_by_id[tid].scheduled_start or datetime.max.replace(tzinfo=UTC),
            str(tid),
        ),
    )
    for tid in non_protected:
        ivs = _intervals_for(tid)
        overlaps = any(s1 < e2 and s2 < e1 for s1, e1 in ivs for s2, e2 in accepted_intervals)
        if not overlaps:
            kept.add(tid)
            accepted_intervals.extend(ivs)
    return kept


def _build_reopt_solver_items(
    *,
    incomplete_tasks: Sequence[ExistingScheduledTaskDTO],
    pinned_ids: set[UUID],
    planned_blocks_by_task: dict[UUID, list[ScheduleBlock]],
    recovered_meta_by_id: dict[str, dict[str, Any]],
    user_tz: str,
) -> list[dict[str, Any]]:
    tz = ZoneInfo(user_tz)
    items: list[dict[str, Any]] = []
    for t in incomplete_tasks:
        item = dict(recovered_meta_by_id[str(t.task_id)])
        if t.task_id in pinned_ids:
            blks = planned_blocks_by_task.get(t.task_id, [])
            if blks:
                pinned_blocks_payload = []
                for blk in blks:
                    st_local = blk.start_time.astimezone(tz)
                    en_local = blk.end_time.astimezone(tz)
                    pinned_blocks_payload.append(
                        {
                            "task_id": str(t.task_id),
                            "sequence_in_task": blk.sequence_in_task,
                            "block_date": st_local.date().isoformat(),
                            "scheduled_start": st_local.isoformat(),
                            "scheduled_end": en_local.isoformat(),
                            "scheduled_duration_minutes": int(blk.scheduled_duration_minutes),
                            "is_protected": bool(blk.is_protected),
                        }
                    )
                item["pinned_schedule_blocks"] = pinned_blocks_payload
                if t.scheduled_start is not None and t.scheduled_end is not None:
                    st_t = t.scheduled_start.astimezone(tz)
                    en_t = t.scheduled_end.astimezone(tz)
                    item["scheduled_date"] = (
                        t.scheduled_date.isoformat()
                        if t.scheduled_date is not None
                        else st_t.date().isoformat()
                    )
                    item["scheduled_start"] = st_t.isoformat()
                    item["scheduled_end"] = en_t.isoformat()
                else:
                    item["scheduled_date"] = pinned_blocks_payload[0]["block_date"]
                    item["scheduled_start"] = pinned_blocks_payload[0]["scheduled_start"]
                    item["scheduled_end"] = pinned_blocks_payload[-1]["scheduled_end"]
            elif t.scheduled_date is not None:
                item["scheduled_date"] = t.scheduled_date.isoformat()
                item["scheduled_start"] = (
                    t.scheduled_start.astimezone(tz).isoformat()
                    if t.scheduled_start is not None
                    else None
                )
                item["scheduled_end"] = (
                    t.scheduled_end.astimezone(tz).isoformat()
                    if t.scheduled_end is not None
                    else None
                )
            else:
                item["scheduled_date"] = None
                item["scheduled_start"] = None
                item["scheduled_end"] = None
        else:
            item["scheduled_date"] = None
            item["scheduled_start"] = None
            item["scheduled_end"] = None
        items.append(item)
    return items


def _needs_overdue_cascade(
    *,
    allocated_tasks: Sequence[dict[str, Any]],
    solver_deps: Sequence[dict[str, Any]],
    pinned_ids: set[UUID],
    protected_ids: set[UUID],
    overdue_descendant_ids: set[UUID],
) -> bool:
    cascadable = (pinned_ids & overdue_descendant_ids) - protected_ids
    if not cascadable:
        return False
    by_id = {str(t.get("task_id")): t for t in allocated_tasks if isinstance(t, dict)}
    for t in allocated_tasks:
        if safe_parse_iso_date(t.get("scheduled_date")) is None:
            return True
    for dep in solver_deps:
        if dep.get("is_mandatory", True) is False:
            continue
        p = by_id.get(str(dep.get("predecessor_id") or ""))
        s = by_id.get(str(dep.get("successor_id") or ""))
        if p is None or s is None:
            continue
        p_end = safe_parse_iso_datetime(p.get("scheduled_end"))
        s_start = safe_parse_iso_datetime(s.get("scheduled_start"))
        if p_end is None or s_start is None or p_end > s_start:
            return True
    return False


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
    schedule_repo: OfficialScheduleRepositoryPort | None = None,
    effective_now: datetime,
    only_overdue_and_incomplete: bool = False,
) -> ScheduleProposalViewDTO:
    """Shared deterministic schedule re-allocation for Reoptimize (0 credit) & Overdue Recovery (UC-23)."""
    roadmap = await roadmap_repo.get_by_id_for_user(roadmap_id, user_id)
    if roadmap is None:
        raise RoadmapNotFoundError()

    user_tz = "Asia/Ho_Chi_Minh"
    if user_query_port is not None:
        user_snapshot = await user_query_port.get_user_by_id(user_id)
        if user_snapshot is not None and user_snapshot.timezone:
            user_tz = user_snapshot.timezone

    effective_today = effective_now.astimezone(ZoneInfo(user_tz)).date()
    effective_anchor = max(start_date_anchor, effective_today)

    roadmap_tasks = await execution_sync_port.get_tasks_for_roadmaps(
        [roadmap_id],
        roadmap_target_dates={roadmap_id: roadmap.target_date},
    )
    incomplete_tasks = [t for t in roadmap_tasks if t.status in ("TODO", "IN_PROGRESS")]
    if not incomplete_tasks:
        raise PlanningDomainError(
            message="Không có nhiệm vụ chưa hoàn thành nào để tái tối ưu lịch học.",
            code="NO_TASKS_TO_REOPTIMIZE",
        )

    milestones = await milestone_repo.list_by_roadmap_id(roadmap_id)
    kept_milestones = resolve_effective_milestones_for_proposal(
        roadmap,
        milestones,
        require_all_approved_without_prelim=False,
    )
    milestone_order_map = {str(m.id): m.sequence_order for m in milestones}
    milestone_by_id = {str(m.id): m for m in milestones}
    valid_mids: set[UUID | str] = {m.id for m in (kept_milestones or milestones)}

    pref_minutes = 60
    if learner_profile_port is not None:
        profile = await learner_profile_port.get_learner_profile(user_id)
        pref_minutes = int(profile.opt_session_minutes)

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
        start_date=effective_anchor,
        target_date=roadmap.target_date,
        timezone=user_tz,
        existing_tasks=other_existing,
        exclude_roadmap_id=roadmap_id,
    )
    avail_config = effective_avail.availability_config
    other_existing = list(effective_avail.effective_existing_tasks)

    # Recover task metadata from historical proposals (APPLIED first), fallback to ExistingScheduledTaskDTO & milestone
    hist_by_id, hist_by_mid_title = await _load_historical_task_lookup(proposal_repo, roadmap_id)
    recovered_meta_by_id: dict[str, dict[str, Any]] = {
        str(t.task_id): _recover_task_metadata(
            t,
            hist_by_id=hist_by_id,
            hist_by_mid_title=hist_by_mid_title,
            milestone_by_id=milestone_by_id,
            task_order=idx,
        )
        for idx, t in enumerate(incomplete_tasks)
    }

    # Fetch persisted TaskDependencyORM edges via ExecutionScheduleSyncPort
    dep_fn = getattr(execution_sync_port, "get_task_dependencies_for_roadmap", None)
    raw_existing_deps = list(await dep_fn(roadmap_id)) if callable(dep_fn) else []
    active_task_ids = {t.task_id for t in incomplete_tasks}
    completed_task_ids = {t.task_id for t in roadmap_tasks if t.status == "COMPLETED"}
    all_roadmap_task_ids = active_task_ids | completed_task_ids

    solver_deps: list[dict[str, Any]] = []
    preserved_deps: list[dict[str, Any]] = []
    seen_solver_edges: set[tuple[str, str]] = set()
    seen_preserved_edges: set[tuple[str, str]] = set()
    for dep in raw_existing_deps:
        pred_uuid = dep.predecessor_id
        succ_uuid = dep.successor_id
        if pred_uuid == succ_uuid:
            continue
        edge_dict = {
            "predecessor_id": str(pred_uuid),
            "successor_id": str(succ_uuid),
            "is_mandatory": bool(dep.is_mandatory),
        }
        pair = (str(pred_uuid), str(succ_uuid))
        if pred_uuid in all_roadmap_task_ids and succ_uuid in all_roadmap_task_ids:
            if pair not in seen_preserved_edges:
                seen_preserved_edges.add(pair)
                preserved_deps.append(edge_dict)
        if pred_uuid in active_task_ids and succ_uuid in active_task_ids:
            if pair not in seen_solver_edges:
                seen_solver_edges.add(pair)
                solver_deps.append(edge_dict)

    protected_task_ids, planned_blocks_by_task = await _resolve_planned_blocks_and_protected(
        roadmap_id=roadmap_id,
        schedule_repo=schedule_repo,
        block_repo=block_repo,
    )
    tasks_by_id = {t.task_id: t for t in incomplete_tasks}

    overdue_ids = {
        t.task_id
        for t in incomplete_tasks
        if t.task_id not in protected_task_ids
        and (t.scheduled_date is None or t.scheduled_date < effective_today)
    }
    future_non_overdue_ids = {
        t.task_id
        for t in incomplete_tasks
        if t.task_id not in protected_task_ids and t.task_id not in overdue_ids
    }
    if only_overdue_and_incomplete:
        pinned_ids = _drop_overlapping_non_protected_pins(
            set(protected_task_ids) | future_non_overdue_ids,
            protected_ids=protected_task_ids,
            tasks_by_id=tasks_by_id,
            planned_blocks_by_task=planned_blocks_by_task,
        )
    else:
        pinned_ids = set(protected_task_ids)

    overdue_descendant_ids = (
        _compute_overdue_descendants(overdue_ids, solver_deps)
        if only_overdue_and_incomplete and overdue_ids
        else set()
    )

    settings = get_settings()
    hard_solver_v2_enabled = bool(getattr(settings, "spatio_temporal_v2_hard_solver_enabled", True))
    soft_pacing_v2_enabled = bool(getattr(settings, "spatio_temporal_v2_soft_pacing_enabled", True))
    soft_end_buffer_ratio = float(getattr(settings, "spatio_temporal_soft_end_buffer_ratio", 0.12))
    soft_max_consecutive_days = int(
        getattr(settings, "spatio_temporal_soft_max_consecutive_days", 5)
    )

    def _run_solver(
        cur_pinned_ids: set[UUID],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], Any]:
        solver_items = _build_reopt_solver_items(
            incomplete_tasks=incomplete_tasks,
            pinned_ids=cur_pinned_ids,
            planned_blocks_by_task=planned_blocks_by_task,
            recovered_meta_by_id=recovered_meta_by_id,
            user_tz=user_tz,
        )
        # Never re-apply estimation_bias_beta here: TaskORM.estimated_minutes was already scaled on initial generation.
        alloc = (
            SpatioTemporalRuleEngine.allocate_task_sessions_with_diagnostics(
                solver_items,
                avail_config,
                start_date=effective_anchor,
                target_date=roadmap.target_date,
                dependencies=solver_deps,
                existing_tasks=other_existing,
                milestone_order_map=milestone_order_map,
                preferred_session_minutes=pref_minutes,
                estimation_bias_beta=1.0,
                soft_pacing_v2_enabled=soft_pacing_v2_enabled,
                end_buffer_ratio=soft_end_buffer_ratio,
                max_consecutive_study_days=soft_max_consecutive_days,
            )
            if hard_solver_v2_enabled
            else None
        )
        if alloc is not None:
            return alloc.tasks, alloc.schedule_blocks, alloc
        tasks_out, blocks_out = SpatioTemporalRuleEngine.allocate_task_sessions(
            solver_items,
            avail_config,
            start_date=effective_anchor,
            target_date=roadmap.target_date,
            dependencies=solver_deps,
            existing_tasks=other_existing,
            milestone_order_map=milestone_order_map,
            preferred_session_minutes=pref_minutes,
            estimation_bias_beta=1.0,
            hard_solver_v2_enabled=False,
        )
        return tasks_out, blocks_out, None

    allocated_tasks, schedule_blocks, alloc_res = _run_solver(pinned_ids)
    if only_overdue_and_incomplete and _needs_overdue_cascade(
        allocated_tasks=allocated_tasks,
        solver_deps=solver_deps,
        pinned_ids=pinned_ids,
        protected_ids=protected_task_ids,
        overdue_descendant_ids=overdue_descendant_ids,
    ):
        cascaded_pins = pinned_ids - (overdue_descendant_ids - protected_task_ids)
        allocated_tasks, schedule_blocks, alloc_res = _run_solver(cascaded_pins)

    # Restore full recovered metadata on allocated tasks (preserving solver timestamps)
    for t_out in allocated_tasks:
        if not isinstance(t_out, dict):
            continue
        t_out.pop("pinned_schedule_blocks", None)
        meta = recovered_meta_by_id.get(str(t_out.get("task_id")))
        if meta is not None:
            for k, v in meta.items():
                if k not in ("scheduled_date", "scheduled_start", "scheduled_end"):
                    t_out.setdefault(k, v)

    has_unscheduled_tasks = any(
        safe_parse_iso_date(t.get("scheduled_date")) is None
        for t in allocated_tasks
        if isinstance(t, dict)
    )

    candidate_payload: dict[str, Any] = {
        "tasks": allocated_tasks,
        "schedule_blocks": schedule_blocks,
        "dependencies": preserved_deps,
    }
    if alloc_res is not None:
        candidate_payload["feasibility_verdict"] = alloc_res.feasibility_verdict
        candidate_payload["unscheduled_diagnostics"] = [
            d.to_dict() for d in alloc_res.unscheduled_diagnostics
        ]

    scheduled_dates = [
        d
        for t in allocated_tasks
        if isinstance(t, dict) and (d := safe_parse_iso_date(t.get("scheduled_date"))) is not None
    ]
    capacity_start = (
        min([effective_anchor, *scheduled_dates]) if scheduled_dates else effective_anchor
    )
    available_minutes = SpatioTemporalRuleEngine.calculate_available_capacity_minutes(
        avail_config,
        start_date=capacity_start,
        target_date=roadmap.target_date,
        existing_tasks=other_existing,
    )
    feasibility = assess_schedule_feasibility(
        allocated_tasks,
        available_minutes=available_minutes,
    )

    orchestrator = ProposalValidationGateOrchestrator(enable_tier3_judge=False)
    gate_result = await orchestrator.validate_proposal(
        candidate_payload,
        availability=avail_config,
        valid_milestone_ids=valid_mids if valid_mids else None,
        existing_tasks=other_existing,
        current_roadmap_target_date=roadmap.target_date,
        is_ai_generated=False,
        allow_unscheduled_tasks=has_unscheduled_tasks,
    )
    if (
        gate_result.schedule_completeness_status == "INFEASIBLE"
        or feasibility.status is FeasibilityStatus.INFEASIBLE
        or any(v.rule_code == "PLAN_INFEASIBLE" for v in gate_result.violations)
    ):
        raise PlanInfeasibleError(feasibility.schedulable_ratio)

    if not gate_result.is_valid:
        raise ProposalValidationGateError(
            message="Không thể tái tối ưu lịch học với cấu hình thời gian rảnh hiện tại.",
            code="SCHEDULE_REOPTIMIZE_FAILED",
            violations=[v.to_dict() for v in gate_result.violations],
        )

    proposal_data = normalize_proposal_task_ids_and_dependencies(
        gate_result.validated_proposal_data
    )
    proposal_data["feasibility"] = feasibility.to_dict()
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
        schedule_repo: OfficialScheduleRepositoryPort | None = None,
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
        self._schedule_repo = schedule_repo

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
            schedule_repo=self._schedule_repo,
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
        schedule_repo: OfficialScheduleRepositoryPort | None = None,
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
        self._schedule_repo = schedule_repo

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
            schedule_repo=self._schedule_repo,
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
