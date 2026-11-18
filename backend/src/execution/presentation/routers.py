from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Query, status
from fastapi.responses import JSONResponse

from src.execution.application.dtos.execution_dtos import (
    StickyNoteViewDTO,
    StudioConfigViewDTO,
    StudySessionViewDTO,
    TaskViewDTO,
)
from src.execution.domain.exceptions.execution_exceptions import ExecutionDomainError
from src.execution.domain.services.dag_cycle_validator import DagValidationError
from src.execution.presentation.deps import (
    AddTaskDependencyUseCaseDep,
    CompleteTaskUseCaseDep,
    CreateManualTaskUseCaseDep,
    CreateStickyNoteUseCaseDep,
    CurrentExecutionLearnerIdDep,
    DeleteStickyNoteUseCaseDep,
    DeleteTaskDependencyUseCaseDep,
    DeleteTaskUseCaseDep,
    FinalizeStudySessionUseCaseDep,
    GetActiveSessionUseCaseDep,
    GetBacklogTasksUseCaseDep,
    GetStudioConfigUseCaseDep,
    GetTodayFocusUseCaseDep,
    GetWeeklyScheduleUseCaseDep,
    HeartbeatStudySessionUseCaseDep,
    ListStickyNotesUseCaseDep,
    ListTasksUseCaseDep,
    ReopenTaskUseCaseDep,
    RescheduleTaskUseCaseDep,
    ResolvePendingTakeawayUseCaseDep,
    StartStudySessionUseCaseDep,
    UpdateStickyNoteUseCaseDep,
    UpdateTaskUseCaseDep,
    UpsertStudioConfigUseCaseDep,
)
from src.execution.presentation.schemas.execution_schemas import (
    AddTaskDependencyRequest,
    CompleteTaskRequest,
    CreateStickyNoteRequest,
    CreateTaskRequest,
    FinalizeSessionRequest,
    HeartbeatSessionRequest,
    ParkingThoughtSchema,
    RescheduleTaskRequest,
    ResolveTakeawayRequest,
    SessionTaskResponse,
    StartSessionRequest,
    StickyNoteResponse,
    StudyNoteResponse,
    StudySessionResponse,
    TaskDependencyResponse,
    TaskResponse,
    TodayFocusResponse,
    UpdateStickyNoteRequest,
    UpdateTaskRequest,
    UpdateWorkspaceStudioConfigRequest,
    WeeklyScheduleItemResponse,
    WeeklyScheduleResponse,
    WorkspaceStudioConfigResponse,
)
from src.shared_kernel.domain.exceptions import DomainError

router = APIRouter(prefix="/api/v1/execution", tags=["Execution & Workspace"])
tasks_router = APIRouter(prefix="/api/v1/tasks", tags=["Execution Tasks"])
sessions_router = APIRouter(prefix="/api/v1/sessions", tags=["Study Sessions"])

_NOT_FOUND_CODES = frozenset(
    {"TASK_NOT_FOUND", "SESSION_NOT_FOUND", "ROADMAP_NOT_FOUND", "NOTE_NOT_FOUND"}
)
_CONFLICT_CODES = frozenset(
    {
        "TASK_BLOCKED",
        "TASK_STALLED_INTERVENTION_REQUIRED",
        "TASK_HAS_ACTIVE_SUCCESSORS",
        "INVALID_TASK_STATE",
        "ACTIVE_SESSION_EXISTS",
        "PENDING_TAKEAWAY_REQUIRED",
        "INVALID_SESSION_STATE",
        "SCHEDULE_SLOT_CONFLICT",
        "ROADMAP_READ_ONLY",
        "RESCHEDULE_BUDGET_EXHAUSTED",
    }
)


def _handle_execution_error(exc: DomainError) -> JSONResponse:
    if exc.code in _NOT_FOUND_CODES:
        http_status = status.HTTP_404_NOT_FOUND
    elif exc.code in _CONFLICT_CODES:
        http_status = status.HTTP_409_CONFLICT
    else:
        http_status = status.HTTP_422_UNPROCESSABLE_CONTENT

    payload: dict[str, object] = {
        "code": exc.code,
        "message": exc.message,
        "detail": exc.message,
    }
    if isinstance(exc, ExecutionDomainError) and exc.details:
        payload["details"] = exc.details
    elif isinstance(exc, DagValidationError) and exc.cycle_path:
        payload["details"] = {"cycle_path": [str(x) for x in exc.cycle_path]}
    return JSONResponse(status_code=http_status, content=payload)


def _to_task_response(view: TaskViewDTO) -> TaskResponse:
    t = view.task
    return TaskResponse(
        id=t.id,
        roadmap_id=t.roadmap_id,
        milestone_id=t.milestone_id,
        official_schedule_id=t.official_schedule_id,
        parent_task_id=t.parent_task_id,
        concept_id=t.concept_id,
        title=t.title,
        description=t.description,
        estimated_minutes=t.estimated_minutes,
        learning_resources=list(t.learning_resources),
        scheduled_date=t.scheduled_date,
        scheduled_start=t.scheduled_start,
        scheduled_end=t.scheduled_end,
        status=t.status.value,
        completed_at=t.completed_at,
        reschedule_count=t.reschedule_count,
        is_overdue=view.is_overdue,
        is_blocked=view.is_blocked,
        is_stalled=view.is_stalled,
        predecessor_ids=list(view.predecessor_ids),
        roadmap_title=view.roadmap_title,
        priority_rank=view.priority_rank,
        out_degree=view.out_degree,
        milestone_sequence=view.milestone_sequence,
        milestone_title=view.milestone_title,
        learning_outcomes=list(view.learning_outcomes),
        completion_criteria=view.completion_criteria,
        created_at=t.created_at,
        updated_at=t.updated_at,
    )


def _to_session_response(view: StudySessionViewDTO) -> StudySessionResponse:
    s = view.session
    return StudySessionResponse(
        id=s.id,
        user_id=s.user_id,
        roadmap_id=s.roadmap_id,
        started_at=s.started_at,
        ended_at=s.ended_at,
        planned_minutes=s.planned_minutes,
        actual_minutes=s.actual_minutes,
        status=s.status.value,
        last_heartbeat_at=s.last_heartbeat_at,
        session_mode=s.session_mode.value,
        pending_takeaway=s.pending_takeaway,
        checkin_time_sufficiency=(
            s.checkin_time_sufficiency.value if s.checkin_time_sufficiency is not None else None
        ),
        checkin_perceived_difficulty=s.checkin_perceived_difficulty,
        checkin_focus_level=s.checkin_focus_level,
        scratchpad_content=view.scratchpad_content,
        takeaway_content=view.takeaway_content,
        takeaway_self_confidence=view.takeaway_self_confidence,
        session_tasks=[
            SessionTaskResponse(
                id=st.id,
                session_id=st.session_id,
                task_id=st.task_id,
                allocated_minutes=st.allocated_minutes,
                actual_minutes=st.actual_minutes,
                status_after_session=st.status_after_session,
                notes=st.notes,
            )
            for st in view.session_tasks
        ],
        notes=[
            StudyNoteResponse(
                id=n.id,
                note_type=n.note_type.value,
                content=n.content,
                self_confidence=n.self_confidence,
                alignment_flag=n.alignment_flag.value,
                verification_status=n.verification_status.value,
                created_at=n.created_at,
                updated_at=n.updated_at,
            )
            for n in view.notes
        ],
        created_at=s.created_at,
        updated_at=s.updated_at,
    )


@router.get("/status")
async def get_execution_context_status() -> dict[str, str]:
    """Bounded Context 3 health/status endpoint (UC-10..UC-13)."""
    return {"context": "execution", "status": "ready"}


# =============================================================================
# Tasks & Backlog & Weekly Schedule Endpoints (`/api/v1/tasks`)
# =============================================================================


@tasks_router.get(
    "",
    response_model=list[TaskResponse],
    status_code=status.HTTP_200_OK,
    summary="List learner tasks with derived OVERDUE/BLOCKED/STALLED flags",
)
async def list_tasks(
    user_id: CurrentExecutionLearnerIdDep,
    use_case: ListTasksUseCaseDep,
    roadmap_id: Annotated[UUID | None, Query()] = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
) -> list[TaskResponse] | JSONResponse:
    try:
        views = await use_case.execute(
            user_id=user_id,
            roadmap_id=roadmap_id,
            status=status_filter,
        )
        return [_to_task_response(v) for v in views]
    except DomainError as exc:
        return _handle_execution_error(exc)


@tasks_router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a manual task (15..240 min) with optional UC-12 slot validation",
)
async def create_manual_task(
    request: CreateTaskRequest,
    user_id: CurrentExecutionLearnerIdDep,
    use_case: CreateManualTaskUseCaseDep,
) -> TaskResponse | JSONResponse:
    try:
        view = await use_case.execute(
            user_id=user_id,
            roadmap_id=request.roadmap_id,
            milestone_id=request.milestone_id,
            title=request.title,
            description=request.description,
            estimated_minutes=request.estimated_minutes,
            scheduled_date=request.scheduled_date,
            scheduled_start=request.scheduled_start,
            scheduled_end=request.scheduled_end,
            concept_id=request.concept_id,
            learning_resources=request.learning_resources,
            confirm_soft_overflow=request.confirm_soft_overflow,
        )
        return _to_task_response(view)
    except DomainError as exc:
        return _handle_execution_error(exc)


@tasks_router.get(
    "/backlog",
    response_model=list[TaskResponse],
    status_code=status.HTTP_200_OK,
    summary="List Backlog Recovery Queue ranked by BacklogPriorityRanker",
)
async def list_backlog_tasks(
    user_id: CurrentExecutionLearnerIdDep,
    use_case: GetBacklogTasksUseCaseDep,
    roadmap_id: Annotated[UUID | None, Query()] = None,
) -> list[TaskResponse] | JSONResponse:
    try:
        views = await use_case.execute(user_id=user_id, roadmap_id=roadmap_id)
        return [_to_task_response(v) for v in views]
    except DomainError as exc:
        return _handle_execution_error(exc)


@tasks_router.get(
    "/schedule/week",
    response_model=WeeklyScheduleResponse,
    status_code=status.HTTP_200_OK,
    summary="Weekly schedule view combining Planning schedule_blocks and Execution tasks",
)
async def get_weekly_schedule(
    user_id: CurrentExecutionLearnerIdDep,
    use_case: GetWeeklyScheduleUseCaseDep,
    week_start: Annotated[date | None, Query()] = None,
) -> WeeklyScheduleResponse | JSONResponse:
    try:
        dto = await use_case.execute(user_id=user_id, week_start=week_start)
        return WeeklyScheduleResponse(
            week_start=dto.week_start,
            week_end=dto.week_end,
            items=[
                WeeklyScheduleItemResponse(
                    block_id=item.block_id,
                    roadmap_id=item.roadmap_id,
                    roadmap_title=item.roadmap_title,
                    roadmap_status=item.roadmap_status,
                    official_schedule_id=item.official_schedule_id,
                    task_id=item.task_id,
                    sequence_in_task=item.sequence_in_task,
                    block_type=item.block_type,
                    block_date=item.block_date,
                    start_time=item.start_time,
                    end_time=item.end_time,
                    scheduled_duration_minutes=item.scheduled_duration_minutes,
                    block_status=item.block_status,
                    sync_status=item.sync_status,
                    is_protected=item.is_protected,
                    placement_rationale=item.placement_rationale,
                    task=_to_task_response(item.task) if item.task is not None else None,
                )
                for item in dto.items
            ],
        )
    except DomainError as exc:
        return _handle_execution_error(exc)


@tasks_router.patch(
    "/{task_id}",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Update task title, description, or estimated_minutes",
)
async def update_task(
    task_id: UUID,
    request: UpdateTaskRequest,
    user_id: CurrentExecutionLearnerIdDep,
    use_case: UpdateTaskUseCaseDep,
) -> TaskResponse | JSONResponse:
    try:
        view = await use_case.execute(
            user_id=user_id,
            task_id=task_id,
            title=request.title,
            description=request.description,
            estimated_minutes=request.estimated_minutes,
        )
        return _to_task_response(view)
    except DomainError as exc:
        return _handle_execution_error(exc)


@tasks_router.post(
    "/{task_id}/complete",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark a task COMPLETED (verifies mandatory predecessors & optional TakeawayGuard)",
)
async def complete_task(
    task_id: UUID,
    user_id: CurrentExecutionLearnerIdDep,
    use_case: CompleteTaskUseCaseDep,
    request: Annotated[CompleteTaskRequest | None, Body()] = None,
) -> TaskResponse | JSONResponse:
    try:
        view = await use_case.execute(
            user_id=user_id,
            task_id=task_id,
            takeaway=request.takeaway if request is not None else None,
            self_confidence=request.self_confidence if request is not None else None,
        )
        return _to_task_response(view)
    except DomainError as exc:
        return _handle_execution_error(exc)


@tasks_router.post(
    "/{task_id}/reopen",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Reopen a COMPLETED task back to TODO",
)
async def reopen_task(
    task_id: UUID,
    user_id: CurrentExecutionLearnerIdDep,
    use_case: ReopenTaskUseCaseDep,
) -> TaskResponse | JSONResponse:
    try:
        view = await use_case.execute(user_id=user_id, task_id=task_id)
        return _to_task_response(view)
    except DomainError as exc:
        return _handle_execution_error(exc)


@tasks_router.post(
    "/{task_id}/reschedule",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Reschedule task to new date/time or move to backlog (UC-12 + DAG + STALLED checks)",
)
async def reschedule_task(
    task_id: UUID,
    request: RescheduleTaskRequest,
    user_id: CurrentExecutionLearnerIdDep,
    use_case: RescheduleTaskUseCaseDep,
) -> TaskResponse | JSONResponse:
    try:
        view = await use_case.execute(
            user_id=user_id,
            task_id=task_id,
            scheduled_date=request.scheduled_date,
            scheduled_start=request.scheduled_start,
            scheduled_end=request.scheduled_end,
            reason=request.reason,
            allow_stalled_commitment=request.allow_stalled_commitment,
            confirm_soft_overflow=request.confirm_soft_overflow,
        )
        return _to_task_response(view)
    except DomainError as exc:
        return _handle_execution_error(exc)


@tasks_router.delete(
    "/{task_id}",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel a task (CANCELLED) and free its schedule blocks",
)
async def delete_task(
    task_id: UUID,
    user_id: CurrentExecutionLearnerIdDep,
    use_case: DeleteTaskUseCaseDep,
) -> TaskResponse | JSONResponse:
    try:
        view = await use_case.execute(user_id=user_id, task_id=task_id)
        return _to_task_response(view)
    except DomainError as exc:
        return _handle_execution_error(exc)


@tasks_router.post(
    "/{task_id}/dependencies",
    response_model=TaskDependencyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a DAG-validated prerequisite dependency to a task",
)
async def add_task_dependency(
    task_id: UUID,
    request: AddTaskDependencyRequest,
    user_id: CurrentExecutionLearnerIdDep,
    use_case: AddTaskDependencyUseCaseDep,
) -> TaskDependencyResponse | JSONResponse:
    try:
        dep = await use_case.execute(
            user_id=user_id,
            successor_id=task_id,
            predecessor_id=request.predecessor_id,
            is_mandatory=request.is_mandatory,
        )
        return TaskDependencyResponse(
            id=dep.id,
            predecessor_id=dep.predecessor_id,
            successor_id=dep.successor_id,
            roadmap_id=dep.roadmap_id,
            is_mandatory=dep.is_mandatory,
            created_at=dep.created_at,
        )
    except DomainError as exc:
        return _handle_execution_error(exc)


@tasks_router.delete(
    "/{task_id}/dependencies/{predecessor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Remove a prerequisite dependency from a task",
)
async def delete_task_dependency(
    task_id: UUID,
    predecessor_id: UUID,
    user_id: CurrentExecutionLearnerIdDep,
    use_case: DeleteTaskDependencyUseCaseDep,
) -> JSONResponse | None:
    try:
        await use_case.execute(
            user_id=user_id,
            successor_id=task_id,
            predecessor_id=predecessor_id,
        )
        return None
    except DomainError as exc:
        return _handle_execution_error(exc)


# =============================================================================
# Study Sessions Endpoints (`/api/v1/sessions`)
# =============================================================================


@sessions_router.get(
    "/today-focus",
    response_model=TodayFocusResponse,
    status_code=status.HTTP_200_OK,
    summary="Today Focus View: active session, pending takeaway, focus task & today queue",
)
async def get_today_focus(
    user_id: CurrentExecutionLearnerIdDep,
    use_case: GetTodayFocusUseCaseDep,
) -> TodayFocusResponse | JSONResponse:
    try:
        dto = await use_case.execute(user_id=user_id)
        return TodayFocusResponse(
            local_date=dto.local_date,
            active_session=(
                _to_session_response(dto.active_session) if dto.active_session is not None else None
            ),
            pending_takeaway_session=(
                _to_session_response(dto.pending_takeaway_session)
                if dto.pending_takeaway_session is not None
                else None
            ),
            focus_task=_to_task_response(dto.focus_task) if dto.focus_task is not None else None,
            today_queue=[_to_task_response(v) for v in dto.today_queue],
            overdue_tasks_count=dto.overdue_tasks_count,
            completed_sessions_today=dto.completed_sessions_today,
            studied_minutes_today=dto.studied_minutes_today,
        )
    except DomainError as exc:
        return _handle_execution_error(exc)


def _to_sticky_note_response(dto: StickyNoteViewDTO) -> StickyNoteResponse:
    return StickyNoteResponse(
        id=dto.id,
        task_id=dto.task_id,
        title=dto.title,
        body=dto.body,
        color=dto.color,
        pinned=dto.pinned,
        pos_x=dto.pos_x,
        pos_y=dto.pos_y,
        z_index=dto.z_index,
        origin_session_id=dto.origin_session_id,
        created_at=dto.created_at,
        updated_at=dto.updated_at,
    )


def _to_studio_config_response(dto: StudioConfigViewDTO) -> WorkspaceStudioConfigResponse:
    parking_items: list[ParkingThoughtSchema] = []
    for item in dto.parking_lot:
        raw_text = str(item.get("text", "")).strip()
        if not raw_text:
            continue
        parking_items.append(
            ParkingThoughtSchema(
                id=str(item.get("id", "")),
                text=raw_text[:500],
                created_at=(
                    str(item["created_at"]) if item.get("created_at") is not None else None
                ),
            )
        )
    return WorkspaceStudioConfigResponse(
        scene=dto.scene,
        clock_style=dto.clock_style,
        clock_size=dto.clock_size,
        show_seconds=dto.show_seconds,
        show_in_tab_title=dto.show_in_tab_title,
        tab_guard_enabled=dto.tab_guard_enabled,
        zen_lock_enabled=dto.zen_lock_enabled,
        blocklist=list(dto.blocklist),
        parking_lot=parking_items,
        updated_at=dto.updated_at,
    )


@sessions_router.get(
    "/notes",
    response_model=list[StickyNoteResponse],
    status_code=status.HTTP_200_OK,
    summary="List learner workspace sticky notes",
)
async def list_sticky_notes(
    user_id: CurrentExecutionLearnerIdDep,
    use_case: ListStickyNotesUseCaseDep,
) -> list[StickyNoteResponse] | JSONResponse:
    try:
        items = await use_case.execute(user_id=user_id)
        return [_to_sticky_note_response(item) for item in items]
    except DomainError as exc:
        return _handle_execution_error(exc)


@sessions_router.post(
    "/notes",
    response_model=StickyNoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a workspace sticky note",
)
async def create_sticky_note(
    request: CreateStickyNoteRequest,
    user_id: CurrentExecutionLearnerIdDep,
    use_case: CreateStickyNoteUseCaseDep,
) -> StickyNoteResponse | JSONResponse:
    try:
        item = await use_case.execute(
            user_id=user_id,
            title=request.title,
            body=request.body,
            color=request.color,
            pinned=request.pinned,
            pos_x=request.pos_x,
            pos_y=request.pos_y,
            z_index=request.z_index,
            origin_session_id=request.origin_session_id,
            task_id=request.task_id,
        )
        return _to_sticky_note_response(item)
    except DomainError as exc:
        return _handle_execution_error(exc)


@sessions_router.patch(
    "/notes/{note_id}",
    response_model=StickyNoteResponse,
    status_code=status.HTTP_200_OK,
    summary="Update an owned workspace sticky note",
)
async def update_sticky_note(
    note_id: UUID,
    request: UpdateStickyNoteRequest,
    user_id: CurrentExecutionLearnerIdDep,
    use_case: UpdateStickyNoteUseCaseDep,
) -> StickyNoteResponse | JSONResponse:
    try:
        item = await use_case.execute(
            user_id=user_id,
            note_id=note_id,
            title=request.title,
            body=request.body,
            color=request.color,
            pinned=request.pinned,
            pos_x=request.pos_x,
            pos_y=request.pos_y,
            z_index=request.z_index,
        )
        return _to_sticky_note_response(item)
    except DomainError as exc:
        return _handle_execution_error(exc)


@sessions_router.delete(
    "/notes/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Delete an owned workspace sticky note",
)
async def delete_sticky_note(
    note_id: UUID,
    user_id: CurrentExecutionLearnerIdDep,
    use_case: DeleteStickyNoteUseCaseDep,
) -> JSONResponse | None:
    try:
        await use_case.execute(user_id=user_id, note_id=note_id)
        return None
    except DomainError as exc:
        return _handle_execution_error(exc)


@sessions_router.get(
    "/studio-config",
    response_model=WorkspaceStudioConfigResponse,
    status_code=status.HTTP_200_OK,
    summary="Get learner workspace studio configuration",
)
async def get_studio_config(
    user_id: CurrentExecutionLearnerIdDep,
    use_case: GetStudioConfigUseCaseDep,
) -> WorkspaceStudioConfigResponse | JSONResponse:
    try:
        dto = await use_case.execute(user_id=user_id)
        return _to_studio_config_response(dto)
    except DomainError as exc:
        return _handle_execution_error(exc)


@sessions_router.put(
    "/studio-config",
    response_model=WorkspaceStudioConfigResponse,
    status_code=status.HTTP_200_OK,
    summary="Create or update learner workspace studio configuration",
)
async def upsert_studio_config(
    request: UpdateWorkspaceStudioConfigRequest,
    user_id: CurrentExecutionLearnerIdDep,
    use_case: UpsertStudioConfigUseCaseDep,
) -> WorkspaceStudioConfigResponse | JSONResponse:
    try:
        dto = await use_case.execute(
            user_id=user_id,
            scene=request.scene,
            clock_style=request.clock_style,
            clock_size=request.clock_size,
            show_seconds=request.show_seconds,
            show_in_tab_title=request.show_in_tab_title,
            tab_guard_enabled=request.tab_guard_enabled,
            zen_lock_enabled=request.zen_lock_enabled,
            blocklist=request.blocklist,
            parking_lot=[item.model_dump() for item in request.parking_lot],
        )
        return _to_studio_config_response(dto)
    except DomainError as exc:
        return _handle_execution_error(exc)


@sessions_router.get(
    "/active",
    response_model=StudySessionResponse | None,
    status_code=status.HTTP_200_OK,
    summary="Get active IN_PROGRESS study session for learner",
)
async def get_active_session(
    user_id: CurrentExecutionLearnerIdDep,
    use_case: GetActiveSessionUseCaseDep,
) -> StudySessionResponse | None | JSONResponse:
    try:
        view = await use_case.execute(user_id=user_id)
        return _to_session_response(view) if view is not None else None
    except DomainError as exc:
        return _handle_execution_error(exc)


@sessions_router.post(
    "/start",
    response_model=StudySessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a STANDARD or MVS study session",
)
async def start_study_session(
    request: StartSessionRequest,
    user_id: CurrentExecutionLearnerIdDep,
    use_case: StartStudySessionUseCaseDep,
) -> StudySessionResponse | JSONResponse:
    try:
        view = await use_case.execute(
            user_id=user_id,
            task_ids=request.task_ids,
            session_mode=request.session_mode,
            planned_minutes=request.planned_minutes,
        )
        return _to_session_response(view)
    except DomainError as exc:
        return _handle_execution_error(exc)


@sessions_router.post(
    "/{session_id}/heartbeat",
    response_model=StudySessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Record 60s study session heartbeat and optional scratchpad note",
)
async def heartbeat_study_session(
    session_id: UUID,
    user_id: CurrentExecutionLearnerIdDep,
    use_case: HeartbeatStudySessionUseCaseDep,
    request: Annotated[HeartbeatSessionRequest | None, Body()] = None,
) -> StudySessionResponse | JSONResponse:
    try:
        view = await use_case.execute(
            user_id=user_id,
            session_id=session_id,
            actual_minutes=request.actual_minutes if request is not None else None,
            scratchpad_content=request.scratchpad_content if request is not None else None,
        )
        return _to_session_response(view)
    except DomainError as exc:
        return _handle_execution_error(exc)


@sessions_router.post(
    "/{session_id}/finalize",
    response_model=StudySessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Finalize a study session with TakeawayGuard, OS-01, DailyCheckin & Outbox event",
)
async def finalize_study_session(
    session_id: UUID,
    request: FinalizeSessionRequest,
    user_id: CurrentExecutionLearnerIdDep,
    use_case: FinalizeStudySessionUseCaseDep,
) -> StudySessionResponse | JSONResponse:
    try:
        view = await use_case.execute(
            user_id=user_id,
            session_id=session_id,
            early_stop=request.early_stop,
            completed_task_ids=request.completed_task_ids,
            takeaway=request.takeaway,
            self_confidence=request.self_confidence,
            scratchpad_content=request.scratchpad_content,
            actual_minutes=request.actual_minutes,
            checkin_time_sufficiency=request.checkin_time_sufficiency,
            checkin_perceived_difficulty=request.checkin_perceived_difficulty,
            checkin_focus_level=request.checkin_focus_level,
        )
        return _to_session_response(view)
    except DomainError as exc:
        return _handle_execution_error(exc)


@sessions_router.post(
    "/{session_id}/resolve-takeaway",
    response_model=StudySessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Resolve pending_takeaway debt for an auto-closed session",
)
async def resolve_pending_takeaway(
    session_id: UUID,
    request: ResolveTakeawayRequest,
    user_id: CurrentExecutionLearnerIdDep,
    use_case: ResolvePendingTakeawayUseCaseDep,
) -> StudySessionResponse | JSONResponse:
    try:
        view = await use_case.execute(
            user_id=user_id,
            session_id=session_id,
            takeaway=request.takeaway,
            self_confidence=request.self_confidence,
        )
        return _to_session_response(view)
    except DomainError as exc:
        return _handle_execution_error(exc)
