from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

from src.account.public_api import (
    AvailabilityQueryPort,
    CalendarConnectionQueryPort,
    UserQueryPort,
)
from src.execution.public_api import ExecutionScheduleSyncPort
from src.planning.application.ports.planning_repository_ports import (
    GoalRepositoryPort,
    MilestoneRepositoryPort,
    RoadmapRepositoryPort,
    ScheduleProposalRepositoryPort,
)
from src.planning.application.ports.schedule_block_repository_port import (
    ScheduleBlockRepositoryPort,
)
from src.planning.application.services.effective_availability_service import (
    GetEffectiveAvailabilityUseCase,
)
from src.planning.application.services.existing_schedule_occupancy import (
    expand_existing_schedule_occupancy,
)
from src.planning.domain.exceptions.planning_exceptions import (
    InsufficientCapacityError,
    ScopeApprovalRequiredError,
    UnapprovedMilestonesError,
)
from src.planning.domain.models.goal import Goal
from src.planning.domain.models.milestone import Milestone, MilestoneStatus
from src.planning.domain.models.roadmap import Roadmap
from src.planning.domain.services.milestone_effort_allocator import (
    MilestoneEffortAllocator,
    PreliminaryFeasibilityStatus,
    compute_availability_fingerprint,
    compute_existing_tasks_fingerprint,
)
from src.planning.domain.services.spatio_temporal_engine import SpatioTemporalRuleEngine
from src.planning.domain.services.validation_types import (
    AvailabilityConfigurationDTO,
    safe_parse_iso_date,
)
from src.shared_kernel.application.uow import AsyncUnitOfWork
from src.shared_kernel.config import get_settings


def _build_allocator_inputs_from_milestones(
    milestones: Sequence[Milestone],
    prev_prelim: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Build allocator records preserving raw `llm_effort_minutes` when effort wasn't manually edited."""
    bd_by_id: dict[str, dict[str, Any]] = {}
    bd_by_seq: dict[int, dict[str, Any]] = {}
    if isinstance(prev_prelim, dict):
        for raw_bd in prev_prelim.get("three_effort_breakdown") or []:
            if not isinstance(raw_bd, dict):
                continue
            if raw_bd.get("milestone_id"):
                bd_by_id[str(raw_bd["milestone_id"])] = raw_bd
            if "sequence_order" in raw_bd:
                bd_by_seq[int(raw_bd["sequence_order"])] = raw_bd

    records: list[dict[str, Any]] = []
    for m in milestones:
        bd = bd_by_id.get(str(m.id)) or bd_by_seq.get(int(m.sequence_order))
        effort_for_alloc = int(m.estimated_effort_minutes)
        if isinstance(bd, dict) and bd.get("llm_effort_minutes"):
            kept = bool(bd.get("kept_in_scope", True))
            planned = int(bd.get("normalized_planned_effort_minutes") or 0)
            est = int(bd.get("estimated_effort_minutes") or 0)
            saved_effort = planned if (kept and planned > 0) else est
            if effort_for_alloc == saved_effort:
                effort_for_alloc = int(bd["llm_effort_minutes"])

        records.append(
            {
                "sequence_order": int(m.sequence_order),
                "milestone_id": str(m.id),
                "title": m.title,
                "description": m.description or "",
                "learning_outcomes": list(m.learning_outcomes),
                "completion_criteria": m.completion_criteria or "",
                "estimated_effort_minutes": effort_for_alloc,
                "required_concepts": list(m.required_concepts),
                "unverified_concepts": list(m.unverified_concepts),
                "prerequisite_milestone_ids": [str(pid) for pid in m.prerequisite_milestone_ids],
                "dependencies": [],
            }
        )
    return records


def _verify_preliminary_hash_matches(
    raw_prelim: dict[str, Any],
    *,
    version: int,
    status: PreliminaryFeasibilityStatus,
    kept_scope_items: Sequence[dict[str, Any]],
    deferred_scope_items: Sequence[dict[str, Any]],
) -> bool:
    raw_hash = raw_prelim.get("scope_proposal_hash")
    if not raw_hash:
        return False
    p_hard_raw = raw_prelim.get("hard_packable_capacity_minutes")
    p_hard = int(p_hard_raw) if p_hard_raw is not None else None
    recomputed = MilestoneEffortAllocator._compute_proposal_hash(
        version=version,
        status=status,
        kept_scope=kept_scope_items,
        deferred_scope=deferred_scope_items,
        hard_packable_capacity_minutes=p_hard,
        target_date=raw_prelim.get("target_date"),
        availability_fingerprint=raw_prelim.get("availability_fingerprint"),
        existing_tasks_fingerprint=raw_prelim.get("existing_tasks_fingerprint"),
    )
    return str(raw_hash) == recomputed


def resolve_effective_milestones_for_proposal(
    roadmap: Roadmap,
    milestones: Sequence[Milestone],
    *,
    require_all_approved_without_prelim: bool = True,
) -> list[Milestone]:
    """Resolve effective milestones for proposal generation, update, and apply.

    - Enforces `PRELIMINARY_UNSCHEDULABLE` (409) and versioned/hashed `FIT_CAPACITY`
      approval (`APPROVED_BY_LEARNER`, matching version & hash) (409).
    - Filters to ONLY `kept_scope` milestones (`status != PENDING` and `sequence_order in kept_orders`),
      leaving `deferred_scope` (`PENDING`) milestones untouched.
    - Remains backward-compatible for manual roadmaps without `preliminary_feasibility`.
    """
    if not milestones:
        if require_all_approved_without_prelim:
            raise UnapprovedMilestonesError()
        return []

    if getattr(get_settings(), "milestone_effort_allocator_enabled", True) and isinstance(
        getattr(roadmap, "planning_metadata", None), dict
    ):
        raw_prelim = roadmap.planning_metadata.get("preliminary_feasibility")
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
            if requires_approval or prelim_status == "FIT_CAPACITY_REQUIRES_APPROVAL":
                raw_ver = raw_prelim.get("scope_proposal_version")
                proposal_ver = int(raw_ver) if isinstance(raw_ver, int) else None
                raw_hash = raw_prelim.get("scope_proposal_hash")
                proposal_hash = str(raw_hash) if raw_hash is not None else None
                approved_ver = raw_prelim.get("approved_scope_version")

                if (
                    approval_status != "APPROVED_BY_LEARNER"
                    or approved_ver is None
                    or proposal_ver is None
                    or int(approved_ver) != int(proposal_ver)
                ):
                    raise ScopeApprovalRequiredError(
                        preliminary_feasibility=raw_prelim,
                        scope_proposal_version=proposal_ver,
                        scope_proposal_hash=proposal_hash,
                    )

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
                if not _verify_preliminary_hash_matches(
                    raw_prelim,
                    version=proposal_ver,
                    status="FIT_CAPACITY_REQUIRES_APPROVAL",
                    kept_scope_items=kept_scope_items,
                    deferred_scope_items=deferred_scope_items,
                ):
                    raise ScopeApprovalRequiredError(
                        preliminary_feasibility=raw_prelim,
                        scope_proposal_version=proposal_ver,
                        scope_proposal_hash=proposal_hash,
                        message=(
                            "Đề xuất phạm vi FIT_CAPACITY đã thay đổi (hash không khớp). "
                            "Vui lòng xác nhận lại phiên bản mới nhất."
                        ),
                    )

                if "target_date" in raw_prelim:
                    current_target_iso = (
                        roadmap.target_date.isoformat() if roadmap.target_date else None
                    )
                    if raw_prelim.get("target_date") != current_target_iso:
                        raise ScopeApprovalRequiredError(
                            preliminary_feasibility=raw_prelim,
                            scope_proposal_version=proposal_ver,
                            scope_proposal_hash=proposal_hash,
                            message=(
                                "Ngày mục tiêu lộ trình đã thay đổi sau khi xác nhận phạm vi. "
                                "Vui lòng xác nhận lại."
                            ),
                        )

                kept_orders = {int(item["sequence_order"]) for item in kept_scope_items}
                kept_milestones = [
                    m
                    for m in milestones
                    if m.status != MilestoneStatus.PENDING
                    and (not kept_orders or m.sequence_order in kept_orders)
                ]
                if not kept_milestones:
                    raise UnapprovedMilestonesError()
                if kept_orders and {m.sequence_order for m in kept_milestones} != kept_orders:
                    raise ScopeApprovalRequiredError(
                        preliminary_feasibility=raw_prelim,
                        scope_proposal_version=proposal_ver,
                        scope_proposal_hash=proposal_hash,
                        message=(
                            "Trạng thái cột mốc trong phạm vi giữ lại chưa đồng bộ với phiên bản "
                            "đã xác nhận. Vui lòng phê duyệt lại."
                        ),
                    )
                return kept_milestones

    if require_all_approved_without_prelim and any(
        m.status == MilestoneStatus.PENDING for m in milestones
    ):
        raise UnapprovedMilestonesError()
    return list(milestones)


@dataclass(frozen=True, slots=True)
class PreliminaryFeasibilityRefreshResult:
    preliminary_feasibility: dict[str, Any] | None
    drifted: bool
    status_changed: bool
    roadmap_dirty: bool
    milestones_dirty: bool
    drafts_discarded: int


async def _resolve_live_capacity_inputs(
    *,
    user_id: UUID,
    roadmap: Roadmap,
    effective_start: date,
    availability_query_port: AvailabilityQueryPort,
    execution_sync_port: ExecutionScheduleSyncPort | None = None,
    roadmap_repo: RoadmapRepositoryPort | None = None,
    block_repo: ScheduleBlockRepositoryPort | None = None,
    user_query_port: UserQueryPort | None = None,
    calendar_connection_query_port: CalendarConnectionQueryPort | None = None,
    preloaded_avail: AvailabilityConfigurationDTO | None = None,
    preloaded_existing_tasks: Sequence[Any] | None = None,
) -> tuple[int | None, AvailabilityConfigurationDTO, list[Any]]:
    if preloaded_avail is not None and preloaded_existing_tasks is not None:
        avail_cfg = preloaded_avail
        effective_existing = list(preloaded_existing_tasks)
    else:
        user_tz = "Asia/Ho_Chi_Minh"
        if user_query_port is not None:
            user_snap = await user_query_port.get_user_by_id(user_id)
            if user_snap is not None and user_snap.timezone:
                user_tz = user_snap.timezone
        existing_tasks: list[Any] = []
        if execution_sync_port is not None and roadmap_repo is not None:
            active_roadmaps = await roadmap_repo.list_by_user_id(user_id, status="ACTIVE")
            other_roadmaps = [r for r in active_roadmaps if r.id != roadmap.id]
            other_ids = [r.id for r in other_roadmaps]
            target_dates_map = {r.id: r.target_date for r in other_roadmaps}
            existing_tasks = list(
                await execution_sync_port.get_tasks_for_roadmaps(
                    other_ids,
                    roadmap_target_dates=target_dates_map,
                )
            )
            if block_repo is not None:
                existing_tasks = expand_existing_schedule_occupancy(
                    existing_tasks,
                    await block_repo.list_by_roadmap_ids(other_ids),
                )
        effective_avail = await GetEffectiveAvailabilityUseCase(
            availability_query_port=availability_query_port,
            calendar_connection_query_port=calendar_connection_query_port,
            execution_sync_port=execution_sync_port,
        ).execute(
            user_id=user_id,
            start_date=effective_start,
            target_date=roadmap.target_date,
            timezone=user_tz,
            existing_tasks=existing_tasks,
            exclude_roadmap_id=roadmap.id,
        )
        avail_cfg = effective_avail.availability_config
        effective_existing = list(effective_avail.effective_existing_tasks)

    p_hard: int | None = None
    if roadmap.target_date is not None:
        p_hard, _ = SpatioTemporalRuleEngine.calculate_hard_packable_capacity(
            avail_cfg,
            start_date=effective_start,
            target_date=roadmap.target_date,
            existing_tasks=effective_existing,
        )
    return p_hard, avail_cfg, effective_existing


def _apply_preliminary_result_to_roadmap(
    roadmap: Roadmap,
    prelim_dict: dict[str, Any],
    *,
    milestones: Sequence[Milestone],
    now: datetime,
) -> bool:
    updated_meta = {
        **roadmap.planning_metadata,
        "preliminary_feasibility": prelim_dict,
    }
    status_val = str(prelim_dict.get("status") or "")
    if status_val == "FIT_CAPACITY_REQUIRES_APPROVAL":
        deferred_list = prelim_dict.get("deferred_scope") or []
        updated_meta["deferred_scope"] = [
            str(item.get("title", "")) for item in deferred_list if isinstance(item, dict)
        ]
        base_summary = str(updated_meta.get("scope_summary") or "")
        if base_summary.startswith("FIT_CAPACITY") and ":" in base_summary:
            base_summary = base_summary.split(":", 1)[1].strip()
        ver = prelim_dict.get("scope_proposal_version")
        updated_meta["scope_summary"] = (
            f"FIT_CAPACITY (chờ xác nhận v{ver}): {base_summary}"
        ).strip()
    else:
        updated_meta.pop("deferred_scope", None)
    roadmap.planning_metadata = updated_meta
    roadmap.updated_at = now

    milestones_dirty = False
    requires_approval = bool(prelim_dict.get("requires_learner_approval", False))
    if requires_approval or status_val == "PRELIMINARY_UNSCHEDULABLE":
        for m in milestones:
            if m.status == MilestoneStatus.APPROVED:
                m.reset_to_pending(now)
                milestones_dirty = True
    return milestones_dirty


async def refresh_roadmap_preliminary_feasibility(
    *,
    user_id: UUID,
    roadmap: Roadmap,
    milestones: Sequence[Milestone],
    goal: Goal | None = None,
    goal_repo: GoalRepositoryPort | None = None,
    roadmap_repo: RoadmapRepositoryPort | None = None,
    proposal_repo: ScheduleProposalRepositoryPort | None = None,
    availability_query_port: AvailabilityQueryPort | None = None,
    execution_sync_port: ExecutionScheduleSyncPort | None = None,
    block_repo: ScheduleBlockRepositoryPort | None = None,
    user_query_port: UserQueryPort | None = None,
    calendar_connection_query_port: CalendarConnectionQueryPort | None = None,
    preloaded_avail: AvailabilityConfigurationDTO | None = None,
    preloaded_existing_tasks: Sequence[Any] | None = None,
    force_recompute: bool = False,
    discard_drafts_on_change: bool = True,
    now: datetime | None = None,
) -> PreliminaryFeasibilityRefreshResult:
    """Idempotently verify/recompute `preliminary_feasibility` for a roadmap & its milestones."""
    effective_now = now or datetime.now(UTC)
    if not milestones or not getattr(get_settings(), "milestone_effort_allocator_enabled", True):
        return PreliminaryFeasibilityRefreshResult(
            preliminary_feasibility=None,
            drifted=False,
            status_changed=False,
            roadmap_dirty=False,
            milestones_dirty=False,
            drafts_discarded=0,
        )

    prev_prelim = (
        roadmap.planning_metadata.get("preliminary_feasibility")
        if isinstance(getattr(roadmap, "planning_metadata", None), dict)
        else None
    )
    if (
        not isinstance(prev_prelim, dict)
        and availability_query_port is None
        and preloaded_avail is None
    ):
        return PreliminaryFeasibilityRefreshResult(
            preliminary_feasibility=None,
            drifted=False,
            status_changed=False,
            roadmap_dirty=False,
            milestones_dirty=False,
            drafts_discarded=0,
        )

    prev_status = str(prev_prelim.get("status") or "") if isinstance(prev_prelim, dict) else ""
    prev_version = (
        int(prev_prelim.get("scope_proposal_version") or 0) if isinstance(prev_prelim, dict) else 0
    )
    prev_hash = (
        str(prev_prelim.get("scope_proposal_hash") or "") if isinstance(prev_prelim, dict) else ""
    )
    prev_target_date = prev_prelim.get("target_date") if isinstance(prev_prelim, dict) else None
    prev_has_target_key = isinstance(prev_prelim, dict) and "target_date" in prev_prelim

    effective_start = roadmap.start_date
    if effective_start is None and isinstance(prev_prelim, dict):
        effective_start = safe_parse_iso_date(prev_prelim.get("effective_start_date"))
    if effective_start is None:
        effective_start = effective_now.date()

    prior_knowledge = "BEGINNER"
    if goal is not None:
        prior_knowledge = goal.prior_knowledge_level
    elif goal_repo is not None:
        loaded_goal = await goal_repo.get_by_id(roadmap.goal_id)
        if loaded_goal is not None:
            prior_knowledge = loaded_goal.prior_knowledge_level
    elif isinstance(prev_prelim, dict) and prev_prelim.get("prior_knowledge_level"):
        prior_knowledge = str(prev_prelim["prior_knowledge_level"])

    settings = get_settings()
    target_util = float(getattr(settings, "ai_milestone_target_utilization", 0.85))
    gamma_min = float(getattr(settings, "ai_milestone_min_effort_ratio", 0.65))
    alphas = {
        "BEGINNER": float(getattr(settings, "ai_milestone_alpha_beginner", 1.15)),
        "INTERMEDIATE": float(getattr(settings, "ai_milestone_alpha_intermediate", 1.00)),
        "ADVANCED": float(getattr(settings, "ai_milestone_alpha_advanced", 0.85)),
    }

    avail_cfg: AvailabilityConfigurationDTO | None = None
    effective_existing: list[Any] = []
    p_hard: int | None = None
    has_live_avail = availability_query_port is not None or preloaded_avail is not None

    if has_live_avail and availability_query_port is not None:
        p_hard, avail_cfg, effective_existing = await _resolve_live_capacity_inputs(
            user_id=user_id,
            roadmap=roadmap,
            effective_start=effective_start,
            availability_query_port=availability_query_port,
            execution_sync_port=execution_sync_port,
            roadmap_repo=roadmap_repo,
            block_repo=block_repo,
            user_query_port=user_query_port,
            calendar_connection_query_port=calendar_connection_query_port,
            preloaded_avail=preloaded_avail,
            preloaded_existing_tasks=preloaded_existing_tasks,
        )
    elif preloaded_avail is not None:
        avail_cfg = preloaded_avail
        effective_existing = list(preloaded_existing_tasks or ())
        if roadmap.target_date is not None:
            p_hard, _ = SpatioTemporalRuleEngine.calculate_hard_packable_capacity(
                avail_cfg,
                start_date=effective_start,
                target_date=roadmap.target_date,
                existing_tasks=effective_existing,
            )
    elif isinstance(prev_prelim, dict):
        raw_ph = prev_prelim.get("hard_packable_capacity_minutes")
        p_hard = int(raw_ph) if raw_ph is not None else None

    if not force_recompute and isinstance(prev_prelim, dict) and not has_live_avail:
        # Without live availability port, check stored hash + target_date + milestone metadata
        target_matches = (not prev_has_target_key) or (
            prev_target_date == (roadmap.target_date.isoformat() if roadmap.target_date else None)
        )
        kept_items = [
            item
            for item in (prev_prelim.get("kept_scope") or [])
            if isinstance(item, dict) and "sequence_order" in item
        ]
        deferred_items = [
            item
            for item in (prev_prelim.get("deferred_scope") or [])
            if isinstance(item, dict) and "sequence_order" in item
        ]
        hash_ok = prev_status in (
            "FULL_SCOPE_FEASIBLE",
            "FIT_CAPACITY_REQUIRES_APPROVAL",
            "PRELIMINARY_UNSCHEDULABLE",
        ) and _verify_preliminary_hash_matches(
            prev_prelim,
            version=prev_version,
            status=prev_status,  # type: ignore[arg-type]
            kept_scope_items=kept_items,
            deferred_scope_items=deferred_items,
        )
        if target_matches and (hash_ok or not prev_hash):
            # Also check if milestones themselves were altered vs kept+deferred metadata
            scope_by_seq = {
                int(item["sequence_order"]): item for item in [*kept_items, *deferred_items]
            }
            milestones_match = not scope_by_seq or (
                len(scope_by_seq) == len(milestones)
                and all(
                    m.sequence_order in scope_by_seq
                    and scope_by_seq[m.sequence_order].get("title") == m.title
                    and (
                        scope_by_seq[m.sequence_order].get("milestone_id") is None
                        or str(scope_by_seq[m.sequence_order].get("milestone_id")) == str(m.id)
                    )
                    for m in milestones
                )
            )
            if milestones_match:
                return PreliminaryFeasibilityRefreshResult(
                    preliminary_feasibility=dict(prev_prelim),
                    drifted=False,
                    status_changed=False,
                    roadmap_dirty=False,
                    milestones_dirty=False,
                    drafts_discarded=0,
                )

    probe_prev_version = (
        max(0, prev_version - 1)
        if (prev_status == "FIT_CAPACITY_REQUIRES_APPROVAL" and prev_version >= 1)
        else prev_version
    )
    allocator_records = _build_allocator_inputs_from_milestones(
        milestones,
        prev_prelim if isinstance(prev_prelim, dict) else None,
    )
    probe_res = MilestoneEffortAllocator.allocate(
        allocator_records,
        hard_packable_capacity_minutes=p_hard,
        prior_knowledge_level=prior_knowledge,
        target_utilization=target_util,
        gamma_min=gamma_min,
        alpha_by_level=alphas,
        previous_scope_proposal_version=probe_prev_version,
        start_date=effective_start,
        target_date=roadmap.target_date,
        availability=avail_cfg,
        existing_tasks=effective_existing,
    )

    if not force_recompute and isinstance(prev_prelim, dict):
        target_matches = (not prev_has_target_key) or (
            prev_target_date == (roadmap.target_date.isoformat() if roadmap.target_date else None)
        )
        hash_matches = bool(prev_hash) and probe_res.scope_proposal_hash == prev_hash
        status_matches = probe_res.status == prev_status
        if hash_matches and status_matches and target_matches:
            return PreliminaryFeasibilityRefreshResult(
                preliminary_feasibility=dict(prev_prelim),
                drifted=False,
                status_changed=False,
                roadmap_dirty=False,
                milestones_dirty=False,
                drafts_discarded=0,
            )

    # Recompute with monotonic version bump on FIT_CAPACITY
    if prev_version == probe_prev_version:
        final_res = probe_res
    else:
        final_res = MilestoneEffortAllocator.allocate(
            allocator_records,
            hard_packable_capacity_minutes=p_hard,
            prior_knowledge_level=prior_knowledge,
            target_utilization=target_util,
            gamma_min=gamma_min,
            alpha_by_level=alphas,
            previous_scope_proposal_version=prev_version,
            start_date=effective_start,
            target_date=roadmap.target_date,
            availability=avail_cfg,
            existing_tasks=effective_existing,
        )

    prelim_dict = final_res.to_metadata_dict()
    if (
        not has_live_avail
        and isinstance(prev_prelim, dict)
        and prev_prelim.get("availability_fingerprint") is not None
    ):
        # Preserve stored availability fingerprint when recomputing without live availability port
        prelim_dict["availability_fingerprint"] = prev_prelim.get("availability_fingerprint")
        prelim_dict["existing_tasks_fingerprint"] = prev_prelim.get("existing_tasks_fingerprint")
        prelim_dict["scope_proposal_hash"] = MilestoneEffortAllocator._compute_proposal_hash(
            version=int(prelim_dict["scope_proposal_version"]),
            status=final_res.status,
            kept_scope=prelim_dict["kept_scope"],
            deferred_scope=prelim_dict["deferred_scope"],
            hard_packable_capacity_minutes=final_res.hard_packable_capacity_minutes,
            target_date=prelim_dict.get("target_date"),
            availability_fingerprint=prelim_dict.get("availability_fingerprint"),
            existing_tasks_fingerprint=prelim_dict.get("existing_tasks_fingerprint"),
        )

    status_changed = bool(prev_status) and (final_res.status != prev_status)
    milestones_dirty = _apply_preliminary_result_to_roadmap(
        roadmap,
        prelim_dict,
        milestones=milestones,
        now=effective_now,
    )
    drafts_discarded = 0
    if discard_drafts_on_change and proposal_repo is not None:
        drafts_discarded = await proposal_repo.discard_existing_drafts(roadmap.id, effective_now)

    return PreliminaryFeasibilityRefreshResult(
        preliminary_feasibility=prelim_dict,
        drifted=True,
        status_changed=status_changed,
        roadmap_dirty=True,
        milestones_dirty=milestones_dirty,
        drafts_discarded=drafts_discarded,
    )


async def verify_or_refresh_preliminary_feasibility_for_gate(
    *,
    user_id: UUID,
    roadmap: Roadmap,
    milestones: Sequence[Milestone],
    goal_repo: GoalRepositoryPort | None = None,
    roadmap_repo: RoadmapRepositoryPort | None = None,
    milestone_repo: MilestoneRepositoryPort | None = None,
    proposal_repo: ScheduleProposalRepositoryPort | None = None,
    availability_query_port: AvailabilityQueryPort | None = None,
    execution_sync_port: ExecutionScheduleSyncPort | None = None,
    block_repo: ScheduleBlockRepositoryPort | None = None,
    user_query_port: UserQueryPort | None = None,
    calendar_connection_query_port: CalendarConnectionQueryPort | None = None,
    uow: AsyncUnitOfWork | None = None,
    preloaded_avail: AvailabilityConfigurationDTO | None = None,
    preloaded_existing_tasks: Sequence[Any] | None = None,
    raise_on_stale_fit_capacity: bool = True,
    now: datetime | None = None,
) -> PreliminaryFeasibilityRefreshResult:
    """Synchronous drift check used before Approval / Proposal Gen / Proposal Edit / Apply."""
    effective_now = now or datetime.now(UTC)
    if not milestones or not getattr(get_settings(), "milestone_effort_allocator_enabled", True):
        return PreliminaryFeasibilityRefreshResult(
            preliminary_feasibility=None,
            drifted=False,
            status_changed=False,
            roadmap_dirty=False,
            milestones_dirty=False,
            drafts_discarded=0,
        )

    raw_prelim = (
        roadmap.planning_metadata.get("preliminary_feasibility")
        if isinstance(getattr(roadmap, "planning_metadata", None), dict)
        else None
    )
    if not isinstance(raw_prelim, dict):
        return PreliminaryFeasibilityRefreshResult(
            preliminary_feasibility=None,
            drifted=False,
            status_changed=False,
            roadmap_dirty=False,
            milestones_dirty=False,
            drafts_discarded=0,
        )

    prev_status = str(raw_prelim.get("status") or "")
    prev_requires_approval = bool(raw_prelim.get("requires_learner_approval", False))
    prev_approval_status = str(raw_prelim.get("scope_approval_status") or "NOT_REQUIRED")

    refresh_res = await refresh_roadmap_preliminary_feasibility(
        user_id=user_id,
        roadmap=roadmap,
        milestones=milestones,
        goal_repo=goal_repo,
        roadmap_repo=roadmap_repo,
        proposal_repo=proposal_repo,
        availability_query_port=availability_query_port,
        execution_sync_port=execution_sync_port,
        block_repo=block_repo,
        user_query_port=user_query_port,
        calendar_connection_query_port=calendar_connection_query_port,
        preloaded_avail=preloaded_avail,
        preloaded_existing_tasks=preloaded_existing_tasks,
        force_recompute=False,
        discard_drafts_on_change=False,
        now=effective_now,
    )
    if not refresh_res.drifted:
        return refresh_res

    new_prelim = refresh_res.preliminary_feasibility or {}
    new_status = str(new_prelim.get("status") or "")
    new_ver_raw = new_prelim.get("scope_proposal_version")
    new_ver = int(new_ver_raw) if isinstance(new_ver_raw, int) else None
    new_hash = (
        str(new_prelim.get("scope_proposal_hash"))
        if new_prelim.get("scope_proposal_hash")
        else None
    )

    if uow is not None and roadmap_repo is not None:
        async with uow:
            await roadmap_repo.save(roadmap)
            if refresh_res.milestones_dirty and milestone_repo is not None:
                await milestone_repo.save_many(roadmap.id, milestones)
            await uow.commit()

    if new_status == "PRELIMINARY_UNSCHEDULABLE":
        raise InsufficientCapacityError(
            preliminary_feasibility=new_prelim,
            hard_packable_capacity_minutes=int(
                new_prelim.get("hard_packable_capacity_minutes") or 0
            ),
        )

    if new_status == "FIT_CAPACITY_REQUIRES_APPROVAL" and raise_on_stale_fit_capacity:
        raise ScopeApprovalRequiredError(
            preliminary_feasibility=new_prelim,
            scope_proposal_version=new_ver,
            scope_proposal_hash=new_hash,
            message=(
                "Ngữ cảnh lộ trình hoặc quỹ thời gian rảnh đã thay đổi. "
                "Vui lòng xác nhận lại phạm vi FIT_CAPACITY phiên bản mới nhất."
            ),
        )

    # Even if transitioned from FIT_CAPACITY (already approved) -> FULL_SCOPE_FEASIBLE,
    # deferred milestones are still PENDING, or caller had a stale approval.
    if (
        prev_requires_approval
        and prev_approval_status == "APPROVED_BY_LEARNER"
        and new_status != prev_status
    ):
        if any(m.status == MilestoneStatus.PENDING for m in milestones):
            raise UnapprovedMilestonesError(
                message="Phạm vi lộ trình đã thay đổi sau khi phê duyệt. Vui lòng phê duyệt lại các cột mốc."
            )

    return refresh_res


__all__ = [
    "PreliminaryFeasibilityRefreshResult",
    "compute_availability_fingerprint",
    "compute_existing_tasks_fingerprint",
    "refresh_roadmap_preliminary_feasibility",
    "resolve_effective_milestones_for_proposal",
    "verify_or_refresh_preliminary_feasibility_for_gate",
]
