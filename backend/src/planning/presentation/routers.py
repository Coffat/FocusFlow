from collections.abc import AsyncGenerator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, Query, status
from fastapi.responses import JSONResponse, StreamingResponse

from src.account.public_api import QuotaExceededError
from src.planning.application.dtos.planning_dtos import (
    MilestoneInputItemDTO,
    ScheduleProposalViewDTO,
    SseJobTicketDTO,
)
from src.planning.application.ports.sse_job_port import SseJobNotFoundError
from src.planning.domain.exceptions.planning_exceptions import (
    PlanningDomainError,
    ProposalValidationGateError,
    RoadmapNotFoundError,
    ScheduleProposalNotFoundError,
    SoftOverflowConfirmationRequiredError,
    UnapprovedMilestonesError,
)
from src.planning.domain.models.goal import Goal
from src.planning.domain.models.milestone import Milestone
from src.planning.domain.models.roadmap import Roadmap
from src.planning.domain.models.schedule import OfficialSchedule, ScheduleProposal
from src.planning.presentation.deps import (
    ApplyProposalUseCaseDep,
    ApproveMilestonesUseCaseDep,
    ArchiveRoadmapUseCaseDep,
    CreateGoalAndRoadmapUseCaseDep,
    CurrentLearnerIdDep,
    GetCurrentProposalUseCaseDep,
    GetRoadmapDetailUseCaseDep,
    InitiateMilestoneGenUseCaseDep,
    InitiateProposalGenUseCaseDep,
    ListRoadmapsUseCaseDep,
    SaveManualPlanUseCaseDep,
    SseJobStoreDep,
    UpdateMilestonesUseCaseDep,
    UpdateProposalUseCaseDep,
    UpdateRoadmapUseCaseDep,
)
from src.planning.presentation.schemas.planning_schemas import (
    ApplyScheduleProposalRequest,
    ApplyScheduleProposalResponse,
    ConstraintViolationSchema,
    CreateManualRoadmapPlanRequest,
    CreateRoadmapRequest,
    GoalResponse,
    MilestoneListResponse,
    MilestoneResponse,
    OfficialScheduleResponse,
    RoadmapDetailResponse,
    RoadmapResponse,
    ScheduledTaskResponse,
    ScheduleProposalResponse,
    SoftOverflowWarningSchema,
    SseJobTicketResponse,
    UpdateMilestonesRequest,
    UpdateRoadmapRequest,
    UpdateScheduleProposalRequest,
)
from src.shared_kernel.domain.exceptions import DomainError

router = APIRouter(prefix="/api/v1/planning", tags=["Planning & Roadmaps"])
roadmaps_router = APIRouter(prefix="/api/v1/roadmaps", tags=["Roadmaps & AI Planning"])


def _handle_planning_error(exc: DomainError) -> JSONResponse:
    if isinstance(
        exc,
        (RoadmapNotFoundError, ScheduleProposalNotFoundError, SseJobNotFoundError),
    ):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"code": exc.code, "message": exc.message, "detail": exc.message},
        )
    if isinstance(exc, UnapprovedMilestonesError):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"code": exc.code, "message": exc.message, "detail": exc.message},
        )
    if isinstance(exc, SoftOverflowConfirmationRequiredError):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "code": exc.code,
                "message": exc.message,
                "detail": exc.message,
                "overflow_minutes": exc.overflow_minutes,
                "soft_overflow_warnings": getattr(exc, "warnings", []),
            },
        )
    if isinstance(exc, QuotaExceededError):
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"code": exc.code, "message": exc.message, "detail": exc.message},
        )
    if isinstance(exc, ProposalValidationGateError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={
                "code": exc.code,
                "message": exc.message,
                "detail": exc.message,
                "violations": exc.violations,
            },
        )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"code": exc.code, "message": exc.message, "detail": exc.message},
    )


def _to_goal_response(goal: Goal) -> GoalResponse:
    return GoalResponse(
        id=goal.id,
        user_id=goal.user_id,
        title=goal.title,
        raw_description=goal.raw_description,
        target_date=goal.target_date,
        status=goal.status.value,
        created_at=goal.created_at,
        updated_at=goal.updated_at,
    )


def _to_roadmap_response(roadmap: Roadmap, goal: Goal | None = None) -> RoadmapResponse:
    return RoadmapResponse(
        id=roadmap.id,
        user_id=roadmap.user_id,
        goal_id=roadmap.goal_id,
        title=roadmap.title,
        description=roadmap.description,
        status=roadmap.status.value,
        start_date=roadmap.start_date,
        target_date=roadmap.target_date,
        created_at=roadmap.created_at,
        updated_at=roadmap.updated_at,
        goal=_to_goal_response(goal) if goal is not None else None,
    )


def _to_milestone_response(m: Milestone) -> MilestoneResponse:
    return MilestoneResponse(
        id=m.id,
        roadmap_id=m.roadmap_id,
        sequence_order=m.sequence_order,
        title=m.title,
        description=m.description,
        status=m.status.value,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


def _to_ticket_response(ticket: SseJobTicketDTO) -> SseJobTicketResponse:
    return SseJobTicketResponse(
        job_id=ticket.job_id,
        reservation_id=ticket.reservation_id,
        roadmap_id=ticket.roadmap_id,
        job_type=ticket.job_type,
        status=ticket.status,
        stream_url=ticket.stream_url,
        jobId=str(ticket.job_id),
        reservationId=str(ticket.reservation_id),
        streamUrl=ticket.stream_url,
    )


def _to_official_schedule_response(sched: OfficialSchedule) -> OfficialScheduleResponse:
    return OfficialScheduleResponse(
        id=sched.id,
        roadmap_id=sched.roadmap_id,
        total_sessions=sched.total_sessions,
        total_planned_minutes=sched.total_planned_minutes,
        activated_at=sched.activated_at,
        created_at=sched.created_at,
        updated_at=sched.updated_at,
    )


def _to_proposal_response_from_domain(proposal: ScheduleProposal) -> ScheduleProposalResponse:
    raw_tasks = list(proposal.proposal_data.get("tasks", []))
    raw_deps = list(proposal.proposal_data.get("dependencies", []))
    raw_violations = list(proposal.proposal_data.get("validation_violations", []))
    raw_warnings = list(proposal.proposal_data.get("soft_overflow_warnings", []))
    raw_advisories = [str(w) for w in proposal.proposal_data.get("advisory_warnings", [])]

    violations = [ConstraintViolationSchema.model_validate(v) for v in raw_violations]
    warnings = [SoftOverflowWarningSchema.model_validate(w) for w in raw_warnings]

    return ScheduleProposalResponse(
        id=proposal.id,
        roadmap_id=proposal.roadmap_id,
        user_id=proposal.user_id,
        status=proposal.status.value,
        is_valid=len(violations) == 0,
        has_soft_overflow=len(warnings) > 0,
        tasks=raw_tasks,
        dependencies=raw_deps,
        violations=violations,
        soft_overflow_warnings=warnings,
        advisory_warnings=raw_advisories,
        diff_summary={},
        proposal_data=dict(proposal.proposal_data),
        applied_at=proposal.applied_at,
        created_at=proposal.created_at,
        updated_at=proposal.updated_at,
    )


def _to_proposal_response(view: ScheduleProposalViewDTO) -> ScheduleProposalResponse:
    resp = _to_proposal_response_from_domain(view.proposal)
    resp.is_valid = view.is_valid
    resp.violations = [ConstraintViolationSchema.model_validate(v) for v in view.violations]
    resp.soft_overflow_warnings = [
        SoftOverflowWarningSchema.model_validate(w) for w in view.soft_overflow_warnings
    ]
    resp.has_soft_overflow = len(resp.soft_overflow_warnings) > 0
    resp.advisory_warnings = list(view.advisory_warnings)
    resp.diff_summary = dict(view.diff_summary)
    return resp


@router.get("/status")
async def get_planning_context_status() -> dict[str, str]:
    """Bounded Context 2 health/status endpoint (UC-07..UC-10, UC-12)."""
    return {"context": "planning", "status": "ready"}


# =============================================================================
# 2-Stage SSE Stream Endpoint (Stage 2)
# =============================================================================


@roadmaps_router.get(
    "/jobs/{job_id}/stream",
    response_model=None,
    summary="Stream 2-Stage SSE AI generation events with Last-Event-ID replay (ADR-005)",
)
async def stream_ai_generation_job(
    job_id: UUID,
    user_id: CurrentLearnerIdDep,
    sse_store: SseJobStoreDep,
    last_event_id_header: Annotated[str | None, Header(alias="Last-Event-ID")] = None,
    last_event_id_query: Annotated[int | None, Query(alias="last_event_id")] = None,
) -> StreamingResponse | JSONResponse:
    try:
        await sse_store.get_job_for_user(job_id=job_id, user_id=user_id)
    except DomainError as exc:
        return _handle_planning_error(exc)

    effective_last_id: int | None = last_event_id_query
    if effective_last_id is None and last_event_id_header is not None:
        try:
            effective_last_id = int(last_event_id_header.strip())
        except ValueError:
            effective_last_id = None

    async def _event_generator() -> AsyncGenerator[str, None]:
        async for ev in sse_store.stream_events(
            job_id=job_id,
            user_id=user_id,
            last_event_id=effective_last_id,
        ):
            yield ev.format_sse()

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# =============================================================================
# Roadmap Portfolio CRUD & Lifecycle (UC-07, UC-10)
# =============================================================================


@roadmaps_router.post(
    "",
    response_model=RoadmapResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a Learner Goal and an INITIALIZED Roadmap (UC-07 / OS-02)",
)
async def create_roadmap(
    request: CreateRoadmapRequest,
    user_id: CurrentLearnerIdDep,
    use_case: CreateGoalAndRoadmapUseCaseDep,
) -> RoadmapResponse | JSONResponse:
    try:
        res = await use_case.execute(
            user_id=user_id,
            title=request.title,
            description=request.description,
            goal_title=request.goal_title,
            goal_description=request.goal_description,
            start_date=request.start_date,
            target_date=request.target_date,
        )
        return _to_roadmap_response(res.roadmap, res.goal)
    except DomainError as exc:
        return _handle_planning_error(exc)


@roadmaps_router.get(
    "",
    response_model=list[RoadmapResponse],
    status_code=status.HTTP_200_OK,
    summary="List learner's roadmaps with optional status filter (UC-10)",
)
async def list_roadmaps(
    user_id: CurrentLearnerIdDep,
    use_case: ListRoadmapsUseCaseDep,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
) -> list[RoadmapResponse]:
    roadmaps = await use_case.execute(user_id=user_id, status=status_filter)
    return [_to_roadmap_response(r) for r in roadmaps]


@roadmaps_router.get(
    "/{roadmap_id}",
    response_model=RoadmapDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get full Roadmap detail including Goal, Milestones, OfficialSchedule, Tasks & Draft Proposal (UC-10)",
)
async def get_roadmap_detail(
    roadmap_id: UUID,
    user_id: CurrentLearnerIdDep,
    use_case: GetRoadmapDetailUseCaseDep,
) -> RoadmapDetailResponse | JSONResponse:
    try:
        detail = await use_case.execute(user_id=user_id, roadmap_id=roadmap_id)
        return RoadmapDetailResponse(
            id=detail.roadmap.id,
            user_id=detail.roadmap.user_id,
            goal_id=detail.roadmap.goal_id,
            title=detail.roadmap.title,
            description=detail.roadmap.description,
            status=detail.roadmap.status.value,
            start_date=detail.roadmap.start_date,
            target_date=detail.roadmap.target_date,
            created_at=detail.roadmap.created_at,
            updated_at=detail.roadmap.updated_at,
            goal=_to_goal_response(detail.goal) if detail.goal is not None else None,
            milestones=[_to_milestone_response(m) for m in detail.milestones],
            official_schedule=(
                _to_official_schedule_response(detail.official_schedule)
                if detail.official_schedule is not None
                else None
            ),
            scheduled_tasks=[
                ScheduledTaskResponse(
                    task_id=t.task_id,
                    roadmap_id=t.roadmap_id,
                    milestone_id=t.milestone_id,
                    title=t.title,
                    estimated_minutes=t.estimated_minutes,
                    scheduled_date=t.scheduled_date,
                    scheduled_start=t.scheduled_start,
                    scheduled_end=t.scheduled_end,
                    status=t.status,
                    roadmap_target_date=t.roadmap_target_date,
                )
                for t in detail.scheduled_tasks
            ],
            current_draft_proposal=(
                _to_proposal_response_from_domain(detail.current_draft_proposal)
                if detail.current_draft_proposal is not None
                else None
            ),
        )
    except DomainError as exc:
        return _handle_planning_error(exc)


@roadmaps_router.patch(
    "/{roadmap_id}",
    response_model=RoadmapResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Roadmap metadata or status (UC-10)",
)
async def update_roadmap(
    roadmap_id: UUID,
    request: UpdateRoadmapRequest,
    user_id: CurrentLearnerIdDep,
    use_case: UpdateRoadmapUseCaseDep,
) -> RoadmapResponse | JSONResponse:
    try:
        updated = await use_case.execute(
            user_id=user_id,
            roadmap_id=roadmap_id,
            title=request.title,
            description=request.description,
            start_date=request.start_date,
            target_date=request.target_date,
            status=request.status,
        )
        return _to_roadmap_response(updated)
    except DomainError as exc:
        return _handle_planning_error(exc)


@roadmaps_router.post(
    "/{roadmap_id}/archive",
    response_model=RoadmapResponse,
    status_code=status.HTTP_200_OK,
    summary="Archive a Roadmap into immutable ARCHIVED state (UC-10)",
)
async def archive_roadmap(
    roadmap_id: UUID,
    user_id: CurrentLearnerIdDep,
    use_case: ArchiveRoadmapUseCaseDep,
) -> RoadmapResponse | JSONResponse:
    try:
        archived = await use_case.execute(user_id=user_id, roadmap_id=roadmap_id)
        return _to_roadmap_response(archived)
    except DomainError as exc:
        return _handle_planning_error(exc)


# =============================================================================
# Level 1 — AI Milestone Generation, Editing & Approval (UC-07 / FR-PLAN-001)
# =============================================================================


@roadmaps_router.post(
    "/{roadmap_id}/milestones/generate-jobs",
    response_model=SseJobTicketResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Stage 1: Reserve AI Quota & initiate Level-1 Milestone Generation SSE job (UC-07)",
)
async def initiate_milestone_generation_job(
    roadmap_id: UUID,
    user_id: CurrentLearnerIdDep,
    use_case: InitiateMilestoneGenUseCaseDep,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> SseJobTicketResponse | JSONResponse:
    try:
        ticket = await use_case.execute(
            user_id=user_id,
            roadmap_id=roadmap_id,
            idempotency_key=idempotency_key,
        )
        return _to_ticket_response(ticket)
    except DomainError as exc:
        return _handle_planning_error(exc)


@roadmaps_router.put(
    "/{roadmap_id}/milestones",
    response_model=MilestoneListResponse,
    status_code=status.HTTP_200_OK,
    summary="Add, edit, delete, and reorder Milestones (1..N) for a Roadmap (UC-07)",
)
async def update_milestones(
    roadmap_id: UUID,
    request: UpdateMilestonesRequest,
    user_id: CurrentLearnerIdDep,
    use_case: UpdateMilestonesUseCaseDep,
) -> MilestoneListResponse | JSONResponse:
    try:
        items = [
            MilestoneInputItemDTO(
                milestone_id=m.milestone_id or m.id,
                sequence_order=m.sequence_order,
                title=m.title,
                description=m.description,
            )
            for m in request.milestones
        ]
        saved = await use_case.execute(
            user_id=user_id,
            roadmap_id=roadmap_id,
            items=items,
        )
        return MilestoneListResponse(
            roadmap_id=roadmap_id,
            milestones=[_to_milestone_response(m) for m in saved],
        )
    except DomainError as exc:
        return _handle_planning_error(exc)


@roadmaps_router.post(
    "/{roadmap_id}/milestones/approve",
    response_model=MilestoneListResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve Level-1 Milestones & unlock Level-2 Schedule Proposal generation (UC-07 / FR-PLAN-001)",
)
async def approve_milestones(
    roadmap_id: UUID,
    user_id: CurrentLearnerIdDep,
    use_case: ApproveMilestonesUseCaseDep,
) -> MilestoneListResponse | JSONResponse:
    try:
        approved = await use_case.execute(user_id=user_id, roadmap_id=roadmap_id)
        return MilestoneListResponse(
            roadmap_id=roadmap_id,
            milestones=[_to_milestone_response(m) for m in approved],
        )
    except DomainError as exc:
        return _handle_planning_error(exc)


# =============================================================================
# Level 2 — AI Schedule Proposal Generation, Preview, Edit, Manual & Apply (UC-08, UC-09, UC-12)
# =============================================================================


@roadmaps_router.post(
    "/{roadmap_id}/proposals/generate-jobs",
    response_model=SseJobTicketResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Stage 1: Reserve AI Quota & initiate Level-2 ScheduleProposal SSE job (UC-08)",
)
async def initiate_schedule_proposal_generation_job(
    roadmap_id: UUID,
    user_id: CurrentLearnerIdDep,
    use_case: InitiateProposalGenUseCaseDep,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> SseJobTicketResponse | JSONResponse:
    try:
        ticket = await use_case.execute(
            user_id=user_id,
            roadmap_id=roadmap_id,
            idempotency_key=idempotency_key,
        )
        return _to_ticket_response(ticket)
    except DomainError as exc:
        return _handle_planning_error(exc)


@roadmaps_router.get(
    "/{roadmap_id}/proposals/current",
    response_model=ScheduleProposalResponse,
    status_code=status.HTTP_200_OK,
    summary="Get active DRAFT ScheduleProposal with warnings and diff metadata (UC-08)",
)
async def get_current_schedule_proposal(
    roadmap_id: UUID,
    user_id: CurrentLearnerIdDep,
    use_case: GetCurrentProposalUseCaseDep,
) -> ScheduleProposalResponse | JSONResponse:
    try:
        view = await use_case.execute(user_id=user_id, roadmap_id=roadmap_id)
        return _to_proposal_response(view)
    except DomainError as exc:
        return _handle_planning_error(exc)


@roadmaps_router.put(
    "/{roadmap_id}/proposals/{proposal_id}",
    response_model=ScheduleProposalResponse,
    status_code=status.HTTP_200_OK,
    summary="Edit tasks & dependencies on a DRAFT ScheduleProposal and run UC-12 validation ([15, 240]m)",
)
async def update_schedule_proposal(
    roadmap_id: UUID,
    proposal_id: UUID,
    request: UpdateScheduleProposalRequest,
    user_id: CurrentLearnerIdDep,
    use_case: UpdateProposalUseCaseDep,
) -> ScheduleProposalResponse | JSONResponse:
    try:
        task_dicts = [t.model_dump(mode="json") for t in request.tasks]
        dep_dicts = [d.model_dump(mode="json") for d in request.dependencies]
        view = await use_case.execute(
            user_id=user_id,
            roadmap_id=roadmap_id,
            proposal_id=proposal_id,
            tasks=task_dicts,
            dependencies=dep_dicts,
            reject_invalid=request.reject_invalid,
        )
        return _to_proposal_response(view)
    except DomainError as exc:
        return _handle_planning_error(exc)


@roadmaps_router.post(
    "/{roadmap_id}/proposals/manual",
    response_model=ScheduleProposalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save manual roadmap milestones & ScheduleProposal(DRAFT) without AI quota (UC-09)",
)
async def save_manual_roadmap_plan(
    roadmap_id: UUID,
    request: CreateManualRoadmapPlanRequest,
    user_id: CurrentLearnerIdDep,
    use_case: SaveManualPlanUseCaseDep,
) -> ScheduleProposalResponse | JSONResponse:
    try:
        milestone_dicts = (
            [m.model_dump(mode="json") for m in request.milestones]
            if request.milestones is not None
            else None
        )
        task_dicts = [t.model_dump(mode="json") for t in request.tasks]
        dep_dicts = [d.model_dump(mode="json") for d in request.dependencies]
        view = await use_case.execute(
            user_id=user_id,
            roadmap_id=roadmap_id,
            milestones=milestone_dicts,
            tasks=task_dicts,
            dependencies=dep_dicts,
        )
        return _to_proposal_response(view)
    except DomainError as exc:
        return _handle_planning_error(exc)


@roadmaps_router.post(
    "/{roadmap_id}/proposals/{proposal_id}/apply",
    response_model=ApplyScheduleProposalResponse,
    status_code=status.HTTP_200_OK,
    summary="Apply verified ScheduleProposal as OfficialSchedule with OS-03 Merge & Soft Overflow gate (UC-12)",
)
async def apply_schedule_proposal(
    roadmap_id: UUID,
    proposal_id: UUID,
    user_id: CurrentLearnerIdDep,
    use_case: ApplyProposalUseCaseDep,
    request: ApplyScheduleProposalRequest | None = None,
) -> ApplyScheduleProposalResponse | JSONResponse:
    confirm_overflow = request.confirm_soft_overflow if request is not None else False
    try:
        res = await use_case.execute(
            user_id=user_id,
            roadmap_id=roadmap_id,
            proposal_id=proposal_id,
            confirm_soft_overflow=confirm_overflow,
        )
        return ApplyScheduleProposalResponse(
            roadmap_id=res.roadmap.id,
            roadmap_status=res.roadmap.status.value,
            official_schedule_id=res.official_schedule.id,
            proposal_id=res.proposal.id,
            proposal_status=res.proposal.status.value,
            total_sessions=res.official_schedule.total_sessions,
            total_planned_minutes=res.official_schedule.total_planned_minutes,
            preserved_completed_tasks_count=res.preserved_completed_tasks_count,
            replaced_tasks_count=res.replaced_tasks_count,
            inserted_tasks_count=res.inserted_tasks_count,
            affected_tasks_count=res.affected_tasks_count,
            total_shifted_minutes=res.total_shifted_minutes,
            trigger_type=res.trigger_type,
            official_schedule=_to_official_schedule_response(res.official_schedule),
        )
    except (PlanningDomainError, DomainError) as exc:
        return _handle_planning_error(exc)
