from collections.abc import AsyncGenerator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, Form, Header, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import JSONResponse, StreamingResponse

from src.account.public_api import QuotaExceededError
from src.planning.application.dtos.planning_dtos import (
    MilestoneInputItemDTO,
    ScheduleProposalViewDTO,
    SseJobTicketDTO,
    parse_clarification_context,
)
from src.planning.application.knowledge.safe_url_fetcher import UnsafeUrlError
from src.planning.application.ports.sse_job_port import SseJobNotFoundError, SseJobPort
from src.planning.application.use_cases.knowledge_source_use_cases import (
    InvalidKnowledgeSourceError,
)
from src.planning.domain.exceptions.planning_exceptions import (
    AIExecutionError,
    FreshCalendarConflictDetectedError,
    GoalNotFoundError,
    IdempotencyInProgressError,
    InsufficientCapacityError,
    InvalidClarificationSessionError,
    JudgeReviewConfirmationRequiredError,
    PartialScheduleConfirmationRequiredError,
    PlanInfeasibleError,
    PlanningDomainError,
    ProposalSupersededError,
    ProposalValidationGateError,
    RoadmapNotFoundError,
    ScheduleProposalNotFoundError,
    ScopeApprovalRequiredError,
    SoftOverflowConfirmationRequiredError,
    UnapprovedMilestonesError,
)
from src.planning.domain.models.goal import Goal
from src.planning.domain.models.knowledge_source import KnowledgeSource
from src.planning.domain.models.milestone import Milestone
from src.planning.domain.models.roadmap import Roadmap
from src.planning.domain.models.schedule import OfficialSchedule, ScheduleProposal
from src.planning.domain.services.validation_types import (
    ScheduleCompletenessStatus,
    classify_schedule_completeness,
    safe_parse_iso_date,
    safe_parse_iso_datetime,
)
from src.planning.presentation.deps import (
    ApplyProposalUseCaseDep,
    ApproveMilestonesUseCaseDep,
    ArchiveRoadmapUseCaseDep,
    CreateGoalAndRoadmapUseCaseDep,
    CreateKnowledgeSourceUseCaseDep,
    CurrentLearnerIdDep,
    GenerateClarificationQuestionsUseCaseDep,
    GetCurrentProposalUseCaseDep,
    GetRoadmapDetailUseCaseDep,
    GoalRepositoryDep,
    InitiateMilestoneGenUseCaseDep,
    InitiateOverdueRecoveryUseCaseDep,
    InitiateProposalGenUseCaseDep,
    KnowledgeSourceRepositoryDep,
    ListRoadmapsUseCaseDep,
    PauseRoadmapUseCaseDep,
    ReoptimizeScheduleProposalUseCaseDep,
    ResumeRoadmapUseCaseDep,
    RoadmapRepositoryDep,
    SaveManualPlanUseCaseDep,
    SseJobStoreDep,
    SubmitClarificationAnswersUseCaseDep,
    UpdateMilestonesUseCaseDep,
    UpdateProposalUseCaseDep,
    UpdateRoadmapUseCaseDep,
)
from src.planning.presentation.schemas.planning_schemas import (
    ApplyScheduleProposalRequest,
    ApplyScheduleProposalResponse,
    ApproveMilestonesRequest,
    ClarificationQuestionsResponse,
    ConstraintViolationSchema,
    CreateKnowledgeUrlRequest,
    CreateManualRoadmapPlanRequest,
    CreateRoadmapRequest,
    GoalResponse,
    KnowledgeSourceResponse,
    MilestoneGenerationRequest,
    MilestoneListResponse,
    MilestoneResponse,
    OfficialScheduleResponse,
    PlanningConflictResponse,
    RoadmapDetailResponse,
    RoadmapResponse,
    ScheduledTaskResponse,
    ScheduleFeasibilitySchema,
    ScheduleProposalResponse,
    SkipClarificationRequest,
    SoftOverflowWarningSchema,
    SseJobTicketResponse,
    SubmitClarificationAnswersRequest,
    SubmitClarificationAnswersResponse,
    UpdateMilestonesRequest,
    UpdateRoadmapRequest,
    UpdateScheduleProposalRequest,
)
from src.planning.presentation.tasks import (
    dispatch_ai_roadmap_generation,
    dispatch_ingest_knowledge_source,
)
from src.shared_kernel.config import get_settings
from src.shared_kernel.domain.exceptions import DomainError
from src.shared_kernel.infrastructure.security.rate_limiter import enforce_rate_limit
from src.shared_kernel.infrastructure.sse.job_store import (
    DEFAULT_SSE_KEEPALIVE_INTERVAL_SECONDS,
    stream_sse_wire_with_keepalive,
)

router = APIRouter(prefix="/api/v1/planning", tags=["Planning & Roadmaps"])
roadmaps_router = APIRouter(prefix="/api/v1/roadmaps", tags=["Roadmaps & AI Planning"])


def _handle_planning_error(exc: DomainError) -> JSONResponse:
    if isinstance(
        exc,
        (
            GoalNotFoundError,
            RoadmapNotFoundError,
            ScheduleProposalNotFoundError,
            SseJobNotFoundError,
        ),
    ):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"code": exc.code, "message": exc.message, "detail": exc.message},
        )
    if isinstance(exc, ScopeApprovalRequiredError):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "code": exc.code,
                "message": exc.message,
                "detail": exc.message,
                "scope_proposal_version": exc.scope_proposal_version,
                "scope_proposal_hash": exc.scope_proposal_hash,
                "preliminary_feasibility": exc.preliminary_feasibility,
            },
        )
    if isinstance(exc, InsufficientCapacityError):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "code": exc.code,
                "message": exc.message,
                "detail": exc.message,
                "hard_packable_capacity_minutes": exc.hard_packable_capacity_minutes,
                "preliminary_feasibility": exc.preliminary_feasibility,
            },
        )
    if isinstance(exc, UnapprovedMilestonesError):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"code": exc.code, "message": exc.message, "detail": exc.message},
        )
    if isinstance(exc, InvalidClarificationSessionError):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"code": exc.code, "message": exc.message, "detail": exc.message},
        )
    if isinstance(exc, (IdempotencyInProgressError, ProposalSupersededError)):
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
    if isinstance(exc, JudgeReviewConfirmationRequiredError):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "code": exc.code,
                "message": exc.message,
                "detail": exc.message,
                "judge_status": exc.judge_status,
                "advisory_warnings": exc.advisory_warnings,
            },
        )
    if isinstance(exc, PartialScheduleConfirmationRequiredError):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"code": exc.code, "message": exc.message, "detail": exc.message},
        )
    if isinstance(exc, PlanInfeasibleError):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "code": exc.code,
                "message": exc.message,
                "detail": exc.message,
                "schedulable_ratio": exc.schedulable_ratio,
            },
        )
    if isinstance(exc, FreshCalendarConflictDetectedError):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "code": exc.code,
                "message": exc.message,
                "detail": exc.message,
                "conflicts": exc.conflicts,
            },
        )
    if isinstance(exc, QuotaExceededError):
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"code": exc.code, "message": exc.message, "detail": exc.message},
        )
    if isinstance(exc, AIExecutionError):
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
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
        prior_knowledge_level=goal.prior_knowledge_level,
        clarification_context=goal.clarification_context,
        created_at=goal.created_at,
        updated_at=goal.updated_at,
    )


def _to_knowledge_source_response(source: KnowledgeSource) -> KnowledgeSourceResponse:
    return KnowledgeSourceResponse(
        id=source.id,
        goal_id=source.goal_id,
        source_type=source.source_type.value,
        title=source.title,
        ingestion_status=source.ingestion_status.value,
        chunk_count=source.chunk_count,
        provenance_metadata=dict(source.provenance_metadata),
        error_detail=source.error_detail,
        created_at=source.created_at,
        updated_at=source.updated_at,
    )


def _extract_preliminary_feasibility(roadmap: Roadmap) -> dict[str, object] | None:
    if isinstance(getattr(roadmap, "planning_metadata", None), dict):
        raw = roadmap.planning_metadata.get("preliminary_feasibility")
        if isinstance(raw, dict):
            return dict(raw)
    return None


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
        preliminary_feasibility=_extract_preliminary_feasibility(roadmap),
    )


def _to_milestone_response(m: Milestone) -> MilestoneResponse:
    return MilestoneResponse(
        id=m.id,
        roadmap_id=m.roadmap_id,
        sequence_order=m.sequence_order,
        title=m.title,
        description=m.description,
        learning_outcomes=list(m.learning_outcomes),
        completion_criteria=m.completion_criteria,
        estimated_effort_minutes=m.estimated_effort_minutes,
        required_concepts=list(m.required_concepts),
        unverified_concepts=list(m.unverified_concepts),
        prerequisite_milestone_ids=list(m.prerequisite_milestone_ids),
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
    raw_unscheduled = list(proposal.proposal_data.get("unscheduled_tasks", []))

    violations = [ConstraintViolationSchema.model_validate(v) for v in raw_violations]
    warnings = [SoftOverflowWarningSchema.model_validate(w) for w in raw_warnings]

    default_scheduled_count = len(
        [
            t
            for t in raw_tasks
            if isinstance(t, dict) and safe_parse_iso_date(t.get("scheduled_date")) is not None
        ]
    )
    default_unscheduled_count = len(
        [
            t
            for t in raw_tasks
            if isinstance(t, dict) and safe_parse_iso_date(t.get("scheduled_date")) is None
        ]
    )
    feasibility_raw = proposal.proposal_data.get("feasibility", {})
    feasibility_dict = feasibility_raw if isinstance(feasibility_raw, dict) else {}
    raw_completeness = proposal.proposal_data.get("schedule_completeness_status")
    resolved_verdict = str(
        proposal.proposal_data.get("feasibility_verdict")
        or ("EXPLICIT_UNSCHEDULABLE" if default_unscheduled_count > 0 else "VERIFIED_FEASIBLE")
    )
    if raw_completeness in ("FULL", "PARTIAL", "UNDETERMINED", "INFEASIBLE"):
        resolved_completeness: ScheduleCompletenessStatus = raw_completeness
    elif len(violations) > 0:
        resolved_completeness = (
            "INFEASIBLE" if feasibility_dict.get("status") == "INFEASIBLE" else "UNDETERMINED"
        )
    else:
        raw_blocks = proposal.proposal_data.get("schedule_blocks")
        has_blocks = isinstance(raw_blocks, list) and any(isinstance(b, dict) for b in raw_blocks)
        all_scheduled_have_times = default_scheduled_count > 0 and all(
            safe_parse_iso_datetime(t.get("scheduled_start")) is not None
            and safe_parse_iso_datetime(t.get("scheduled_end")) is not None
            for t in raw_tasks
            if isinstance(t, dict) and safe_parse_iso_date(t.get("scheduled_date")) is not None
        )
        avail_from_feasibility = int(feasibility_dict.get("available_minutes", 1) or 0)
        ratio_from_feasibility = float(feasibility_dict.get("schedulable_ratio", 1.0) or 0.0)
        resolved_completeness = classify_schedule_completeness(
            total_tasks=len([t for t in raw_tasks if isinstance(t, dict)]),
            scheduled_tasks_count=default_scheduled_count,
            unscheduled_tasks_count=default_unscheduled_count,
            available_minutes=avail_from_feasibility
            if "available_minutes" in feasibility_dict
            else 1,
            schedulable_ratio=ratio_from_feasibility
            if "schedulable_ratio" in feasibility_dict
            else 1.0,
            feasibility_verdict=resolved_verdict,
            has_schedule_blocks=has_blocks,
            all_scheduled_have_block_times=all_scheduled_have_times,
            allow_partial_schedule=True,
        )

    return ScheduleProposalResponse(
        id=proposal.id,
        roadmap_id=proposal.roadmap_id,
        user_id=proposal.user_id,
        status=proposal.status.value,
        is_valid=len(violations) == 0,
        has_soft_overflow=len(warnings) > 0,
        judge_status=str(proposal.proposal_data.get("judge_status") or "PASSED"),
        is_partial_schedule=bool(
            proposal.proposal_data.get("is_partial_schedule", default_unscheduled_count > 0)
        ),
        scheduled_tasks_count=int(
            proposal.proposal_data.get("scheduled_tasks_count", default_scheduled_count)
        ),
        unscheduled_tasks_count=int(
            proposal.proposal_data.get("unscheduled_tasks_count", default_unscheduled_count)
        ),
        unscheduled_tasks=raw_unscheduled,
        feasibility=ScheduleFeasibilitySchema.model_validate(feasibility_dict),
        feasibility_verdict=resolved_verdict,
        schedule_completeness_status=resolved_completeness,
        availability_source_metadata=dict(
            proposal.proposal_data.get("availability_source_metadata", {})
        ),
        tasks=raw_tasks,
        schedule_blocks=list(proposal.proposal_data.get("schedule_blocks", [])),
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


@router.post(
    "/goals/{goal_id}/knowledge-sources/files",
    response_model=KnowledgeSourceResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_knowledge_source_file(
    http_request: Request,
    goal_id: UUID,
    current_user_id: CurrentLearnerIdDep,
    use_case: CreateKnowledgeSourceUseCaseDep,
    file: UploadFile = File(...),
    title: str = Form(default=""),
) -> KnowledgeSourceResponse:
    await enforce_rate_limit(http_request, "knowledge_upload_user", identifier=str(current_user_id))
    if not get_settings().knowledge_rag_enabled:
        raise HTTPException(status_code=404, detail="Knowledge RAG is not enabled")
    content = await file.read(get_settings().knowledge_file_max_bytes + 1)
    try:
        source = await use_case.create_file(
            user_id=current_user_id,
            goal_id=goal_id,
            title=title,
            filename=file.filename or "knowledge.txt",
            content=content,
            content_type=file.content_type,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Goal not found") from exc
    except InvalidKnowledgeSourceError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    await dispatch_ingest_knowledge_source(source_id=str(source.id), user_id=str(current_user_id))
    return _to_knowledge_source_response(source)


@router.post(
    "/goals/{goal_id}/knowledge-sources/urls",
    response_model=KnowledgeSourceResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def add_knowledge_source_url(
    http_request: Request,
    goal_id: UUID,
    request: CreateKnowledgeUrlRequest,
    current_user_id: CurrentLearnerIdDep,
    use_case: CreateKnowledgeSourceUseCaseDep,
) -> KnowledgeSourceResponse:
    await enforce_rate_limit(http_request, "knowledge_upload_user", identifier=str(current_user_id))
    if not get_settings().knowledge_rag_enabled:
        raise HTTPException(status_code=404, detail="Knowledge RAG is not enabled")
    try:
        source = await use_case.create_url(
            user_id=current_user_id,
            goal_id=goal_id,
            title=request.title,
            url=request.url,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Goal not found") from exc
    except (InvalidKnowledgeSourceError, UnsafeUrlError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    await dispatch_ingest_knowledge_source(source_id=str(source.id), user_id=str(current_user_id))
    return _to_knowledge_source_response(source)


@router.get(
    "/goals/{goal_id}/knowledge-sources",
    response_model=list[KnowledgeSourceResponse],
)
async def list_knowledge_sources(
    goal_id: UUID,
    current_user_id: CurrentLearnerIdDep,
    goal_repository: GoalRepositoryDep,
    repository: KnowledgeSourceRepositoryDep,
) -> list[KnowledgeSourceResponse]:
    goal = await goal_repository.get_by_id_for_user(goal_id, current_user_id)
    if goal is None:
        raise HTTPException(status_code=404, detail="Goal not found")
    sources = await repository.list_sources_for_goal(goal_id, current_user_id)
    return [_to_knowledge_source_response(source) for source in sources]


@router.get(
    "/knowledge-sources/{source_id}",
    response_model=KnowledgeSourceResponse,
)
async def get_knowledge_source(
    source_id: UUID,
    current_user_id: CurrentLearnerIdDep,
    goal_repository: GoalRepositoryDep,
    repository: KnowledgeSourceRepositoryDep,
) -> KnowledgeSourceResponse:
    source = await repository.get_source_for_user(source_id, current_user_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Knowledge source not found")
    goal = await goal_repository.get_by_id_for_user(source.goal_id, current_user_id)
    if goal is None:
        raise HTTPException(status_code=404, detail="Knowledge source not found")
    return _to_knowledge_source_response(source)


# =============================================================================
# 2-Stage SSE Stream Endpoint (Stage 2)
# =============================================================================


def build_sse_event_generator(
    sse_store: SseJobPort,
    *,
    job_id: UUID,
    user_id: UUID,
    last_event_id: int | None = None,
    keepalive_interval_seconds: float = DEFAULT_SSE_KEEPALIVE_INTERVAL_SECONDS,
) -> AsyncGenerator[str, None]:
    """Build SSE wire generator emitting `: keepalive` comments on idle intervals."""
    return stream_sse_wire_with_keepalive(
        sse_store.stream_events(
            job_id=job_id,
            user_id=user_id,
            last_event_id=last_event_id,
        ),
        keepalive_interval_seconds=keepalive_interval_seconds,
    )


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

    return StreamingResponse(
        build_sse_event_generator(
            sse_store,
            job_id=job_id,
            user_id=user_id,
            last_event_id=effective_last_id,
        ),
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
            prior_knowledge_level=request.prior_knowledge_level,
            start_date=request.start_date,
            target_date=request.target_date,
            weekly_commitment_hours=request.weekly_commitment_hours,
            input_provenance=request.input_provenance.model_dump(mode="json"),
        )
        return _to_roadmap_response(res.roadmap, res.goal)
    except DomainError as exc:
        return _handle_planning_error(exc)


@roadmaps_router.post(
    "/goals/{goal_id}/clarify-questions",
    response_model=ClarificationQuestionsResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate 0-3 gap-aware clarification questions for a goal (FR-GOAL-002)",
)
async def generate_clarification_questions(
    goal_id: UUID,
    user_id: CurrentLearnerIdDep,
    use_case: GenerateClarificationQuestionsUseCaseDep,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> ClarificationQuestionsResponse | JSONResponse:
    try:
        return await use_case.execute(
            goal_id=goal_id,
            user_id=user_id,
            idempotency_key=idempotency_key,
        )
    except DomainError as exc:
        return _handle_planning_error(exc)


@roadmaps_router.post(
    "/goals/{goal_id}/clarify-answers",
    response_model=SubmitClarificationAnswersResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit answers to clarification questions and update goal context (FR-GOAL-002)",
)
async def submit_clarification_answers(
    goal_id: UUID,
    request: SubmitClarificationAnswersRequest,
    user_id: CurrentLearnerIdDep,
    use_case: SubmitClarificationAnswersUseCaseDep,
) -> SubmitClarificationAnswersResponse | JSONResponse:
    try:
        if request.session_id is not None:
            turn = await use_case.execute_turn(
                goal_id=goal_id,
                user_id=user_id,
                session_id=request.session_id,
                round_number=request.round,
                answers=request.answers,
                skipped_question_ids=request.skipped_question_ids,
                total_questions_count=request.total_questions_count,
            )
            goal = turn.goal
        else:
            turn = None
            goal = await use_case.execute(
                goal_id=goal_id,
                user_id=user_id,
                answers=request.answers,
                skipped=request.skipped,
                skipped_question_ids=request.skipped_question_ids,
                total_questions_count=request.total_questions_count,
            )
        parsed = parse_clarification_context(goal.clarification_context)
        return SubmitClarificationAnswersResponse(
            goal_id=goal.id,
            status=turn.status if turn is not None else parsed.status,
            clarification_context=goal.clarification_context or "",
            unresolved_assumptions=list(parsed.unresolved_assumptions),
            session_id=turn.session_id if turn is not None else None,
            round=turn.round if turn is not None else request.round,
            questions=list(turn.questions) if turn is not None else [],
            information_gaps=list(turn.information_gaps) if turn is not None else [],
            next_turn_quota_cost=turn.next_turn_quota_cost if turn is not None else 0,
            message="Clarification context updated successfully",
        )
    except DomainError as exc:
        return _handle_planning_error(exc)


@roadmaps_router.post(
    "/goals/{goal_id}/clarify-skip",
    response_model=SubmitClarificationAnswersResponse,
    status_code=status.HTTP_200_OK,
    summary="Explicitly skip goal clarification survey and record unresolved assumptions (FR-GOAL-002)",
)
async def skip_clarification_questions(
    goal_id: UUID,
    user_id: CurrentLearnerIdDep,
    use_case: SubmitClarificationAnswersUseCaseDep,
    request: SkipClarificationRequest | None = None,
) -> SubmitClarificationAnswersResponse | JSONResponse:
    try:
        skipped_ids = request.skipped_question_ids if request else None
        if request is not None and request.session_id is not None:
            turn = await use_case.skip_session(
                user_id=user_id,
                goal_id=goal_id,
                session_id=request.session_id,
                skipped_question_ids=skipped_ids or [],
            )
            goal = turn.goal
        else:
            turn = None
            goal = await use_case.skip(
                user_id=user_id,
                goal_id=goal_id,
                skipped_question_ids=skipped_ids,
            )
        parsed = parse_clarification_context(goal.clarification_context)
        return SubmitClarificationAnswersResponse(
            goal_id=goal.id,
            status=turn.status if turn is not None else parsed.status,
            clarification_context=goal.clarification_context or "",
            unresolved_assumptions=list(parsed.unresolved_assumptions),
            session_id=turn.session_id if turn is not None else None,
            round=turn.round if turn is not None else 1,
            information_gaps=list(turn.information_gaps) if turn is not None else [],
            message="Clarification survey skipped and assumptions recorded",
        )
    except DomainError as exc:
        return _handle_planning_error(exc)


@roadmaps_router.get(
    "/goals/{goal_id}/clarification-state",
    response_model=ClarificationQuestionsResponse,
    status_code=status.HTTP_200_OK,
    summary="Resume clarification session without creating a new AI call",
)
async def get_clarification_state(
    goal_id: UUID,
    user_id: CurrentLearnerIdDep,
    use_case: GenerateClarificationQuestionsUseCaseDep,
) -> ClarificationQuestionsResponse | JSONResponse:
    try:
        return await use_case.get_state(goal_id=goal_id, user_id=user_id)
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
    limit: Annotated[int | None, Query(ge=1, le=100)] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[RoadmapResponse]:
    roadmaps = await use_case.execute(user_id=user_id, status=status_filter)
    sliced = roadmaps[offset : offset + limit] if limit is not None else roadmaps[offset:]
    return [_to_roadmap_response(r) for r in sliced]


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
            preliminary_feasibility=_extract_preliminary_feasibility(detail.roadmap),
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


@roadmaps_router.post(
    "/{roadmap_id}/pause",
    response_model=RoadmapResponse,
    status_code=status.HTTP_200_OK,
    summary="Pause an ACTIVE Roadmap (`ACTIVE -> PAUSED`, UC-22)",
)
async def pause_roadmap(
    roadmap_id: UUID,
    user_id: CurrentLearnerIdDep,
    use_case: PauseRoadmapUseCaseDep,
) -> RoadmapResponse | JSONResponse:
    try:
        paused = await use_case.execute(user_id=user_id, roadmap_id=roadmap_id)
        return _to_roadmap_response(paused)
    except DomainError as exc:
        return _handle_planning_error(exc)


@roadmaps_router.post(
    "/{roadmap_id}/resume",
    response_model=RoadmapResponse,
    status_code=status.HTTP_200_OK,
    summary="Resume a PAUSED Roadmap (`PAUSED -> ACTIVE`) applying Domino Shift (UC-22)",
)
async def resume_roadmap(
    roadmap_id: UUID,
    user_id: CurrentLearnerIdDep,
    use_case: ResumeRoadmapUseCaseDep,
    shift_days: int | None = Query(default=None, ge=0, le=365),
) -> RoadmapResponse | JSONResponse:
    try:
        resumed = await use_case.execute(
            user_id=user_id,
            roadmap_id=roadmap_id,
            shift_days=shift_days,
        )
        return _to_roadmap_response(resumed)
    except DomainError as exc:
        return _handle_planning_error(exc)


@roadmaps_router.post(
    "/{roadmap_id}/reoptimize-schedule",
    response_model=ScheduleProposalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Deterministic schedule-only re-optimization (0 AI credit) creating a DRAFT proposal",
)
async def reoptimize_schedule_proposal(
    roadmap_id: UUID,
    user_id: CurrentLearnerIdDep,
    use_case: ReoptimizeScheduleProposalUseCaseDep,
) -> ScheduleProposalResponse | JSONResponse:
    try:
        view = await use_case.execute(user_id=user_id, roadmap_id=roadmap_id)
        return _to_proposal_response(view)
    except DomainError as exc:
        return _handle_planning_error(exc)


@roadmaps_router.post(
    "/{roadmap_id}/overdue-revise-jobs",
    response_model=SseJobTicketResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Initiate deterministic overdue-recovery DRAFT proposal job (UC-23)",
)
async def initiate_overdue_recovery_job(
    roadmap_id: UUID,
    user_id: CurrentLearnerIdDep,
    use_case: InitiateOverdueRecoveryUseCaseDep,
) -> SseJobTicketResponse | JSONResponse:
    try:
        ticket = await use_case.execute(user_id=user_id, roadmap_id=roadmap_id)
        if not ticket.is_existing and ticket.status != "COMPLETED":
            await dispatch_ai_roadmap_generation(
                job_id=str(ticket.job_id),
                reservation_id=str(ticket.reservation_id),
                user_id=str(user_id),
                roadmap_id=str(roadmap_id),
                job_type=ticket.job_type,
            )
        return _to_ticket_response(ticket)
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
    request: MilestoneGenerationRequest | None = None,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> SseJobTicketResponse | JSONResponse:
    try:
        ticket = await use_case.execute(
            user_id=user_id,
            roadmap_id=roadmap_id,
            idempotency_key=idempotency_key,
            run_inline=False,
            generation_strategy=(
                request.generation_strategy if request is not None else "FULL_SCOPE"
            ),
        )
        if not ticket.is_existing:
            await dispatch_ai_roadmap_generation(
                job_id=str(ticket.job_id),
                reservation_id=str(ticket.reservation_id),
                user_id=str(user_id),
                roadmap_id=str(roadmap_id),
                job_type=ticket.job_type,
            )
        return _to_ticket_response(ticket)
    except DomainError as exc:
        return _handle_planning_error(exc)


@roadmaps_router.put(
    "/{roadmap_id}/milestones",
    response_model=MilestoneListResponse,
    responses={409: {"model": PlanningConflictResponse}},
    status_code=status.HTTP_200_OK,
    summary="Add, edit, delete, and reorder Milestones (1..N) for a Roadmap (UC-07)",
)
async def update_milestones(
    roadmap_id: UUID,
    request: UpdateMilestonesRequest,
    user_id: CurrentLearnerIdDep,
    use_case: UpdateMilestonesUseCaseDep,
    roadmap_repo: RoadmapRepositoryDep,
) -> MilestoneListResponse | JSONResponse:
    try:
        items = [
            MilestoneInputItemDTO(
                milestone_id=m.milestone_id or m.id,
                sequence_order=m.sequence_order,
                title=m.title,
                description=m.description,
                learning_outcomes=tuple(m.learning_outcomes),
                completion_criteria=m.completion_criteria,
                estimated_effort_minutes=m.estimated_effort_minutes,
                required_concepts=tuple(m.required_concepts),
                unverified_concepts=tuple(m.unverified_concepts),
                prerequisite_milestone_ids=tuple(m.prerequisite_milestone_ids),
            )
            for m in request.milestones
        ]
        saved = await use_case.execute(
            user_id=user_id,
            roadmap_id=roadmap_id,
            items=items,
        )
        roadmap = await roadmap_repo.get_by_id_for_user(roadmap_id, user_id)
        return MilestoneListResponse(
            roadmap_id=roadmap_id,
            milestones=[_to_milestone_response(m) for m in saved],
            preliminary_feasibility=(
                _extract_preliminary_feasibility(roadmap) if roadmap is not None else None
            ),
        )
    except DomainError as exc:
        return _handle_planning_error(exc)


@roadmaps_router.post(
    "/{roadmap_id}/milestones/approve",
    response_model=MilestoneListResponse,
    responses={409: {"model": PlanningConflictResponse}},
    status_code=status.HTTP_200_OK,
    summary="Approve Level-1 Milestones & unlock Level-2 Schedule Proposal generation (UC-07 / FR-PLAN-001)",
)
async def approve_milestones(
    roadmap_id: UUID,
    user_id: CurrentLearnerIdDep,
    use_case: ApproveMilestonesUseCaseDep,
    roadmap_repo: RoadmapRepositoryDep,
    request: ApproveMilestonesRequest | None = None,
) -> MilestoneListResponse | JSONResponse:
    try:
        approved = await use_case.execute(
            user_id=user_id,
            roadmap_id=roadmap_id,
            confirmed_scope_proposal_version=(
                request.confirmed_scope_proposal_version if request is not None else None
            ),
            accept_fit_capacity=(request.accept_fit_capacity if request is not None else False),
        )
        roadmap = await roadmap_repo.get_by_id_for_user(roadmap_id, user_id)
        return MilestoneListResponse(
            roadmap_id=roadmap_id,
            milestones=[_to_milestone_response(m) for m in approved],
            preliminary_feasibility=(
                _extract_preliminary_feasibility(roadmap) if roadmap is not None else None
            ),
        )
    except DomainError as exc:
        return _handle_planning_error(exc)


# =============================================================================
# Level 2 — AI Schedule Proposal Generation, Preview, Edit, Manual & Apply (UC-08, UC-09, UC-12)
# =============================================================================


@roadmaps_router.post(
    "/{roadmap_id}/proposals/generate-jobs",
    response_model=SseJobTicketResponse,
    responses={409: {"model": PlanningConflictResponse}},
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
            run_inline=False,
        )
        if not ticket.is_existing:
            await dispatch_ai_roadmap_generation(
                job_id=str(ticket.job_id),
                reservation_id=str(ticket.reservation_id),
                user_id=str(user_id),
                roadmap_id=str(roadmap_id),
                job_type=ticket.job_type,
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
    responses={409: {"model": PlanningConflictResponse}},
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
    responses={409: {"model": PlanningConflictResponse}},
    status_code=status.HTTP_200_OK,
    summary="Apply verified ScheduleProposal as OfficialSchedule with OS-03 Merge & Soft Overflow gate (UC-12)",
)
async def apply_schedule_proposal(
    roadmap_id: UUID,
    proposal_id: UUID,
    user_id: CurrentLearnerIdDep,
    use_case: ApplyProposalUseCaseDep,
    request: ApplyScheduleProposalRequest | None = None,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> ApplyScheduleProposalResponse | JSONResponse:
    confirm_overflow = request.confirm_soft_overflow if request is not None else False
    confirm_warnings = request.confirm_warnings if request is not None else False
    confirm_partial = request.confirm_partial_schedule if request is not None else False
    try:
        res = await use_case.execute(
            user_id=user_id,
            roadmap_id=roadmap_id,
            proposal_id=proposal_id,
            confirm_soft_overflow=confirm_overflow,
            confirm_warnings=confirm_warnings,
            confirm_partial_schedule=confirm_partial,
            idempotency_key=idempotency_key,
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
            calendar_sync_status=res.calendar_sync_status,
            backlog_unscheduled_tasks_count=res.backlog_unscheduled_tasks_count,
            official_schedule=_to_official_schedule_response(res.official_schedule),
        )
    except (PlanningDomainError, DomainError) as exc:
        return _handle_planning_error(exc)
