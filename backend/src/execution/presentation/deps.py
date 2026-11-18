import inspect
from collections.abc import AsyncGenerator
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import ExpiredSignatureError, PyJWTError
from sqlalchemy.ext.asyncio import AsyncSession

from src.account.public_api import UserQueryPort, create_user_query_port
from src.evaluation.public_api import (
    ScheduleChangeLogPort,
    create_schedule_change_log_port,
)
from src.execution.application.ports.study_session_repository_port import (
    StudySessionRepositoryPort,
)
from src.execution.application.ports.task_repository_port import TaskRepositoryPort
from src.execution.application.use_cases.session_use_cases import (
    FinalizeStudySessionUseCase,
    GetActiveSessionUseCase,
    GetTodayFocusUseCase,
    HeartbeatStudySessionUseCase,
    ResolvePendingTakeawayUseCase,
    StartStudySessionUseCase,
)
from src.execution.application.use_cases.task_use_cases import (
    AddTaskDependencyUseCase,
    CompleteTaskUseCase,
    CreateManualTaskUseCase,
    DeleteTaskDependencyUseCase,
    DeleteTaskUseCase,
    GetBacklogTasksUseCase,
    GetWeeklyScheduleUseCase,
    ListTasksUseCase,
    ReopenTaskUseCase,
    RescheduleTaskUseCase,
    UpdateTaskUseCase,
)
from src.execution.infrastructure.repositories.sqlalchemy_study_session_repository import (
    SqlAlchemyStudySessionRepository,
)
from src.execution.infrastructure.repositories.sqlalchemy_task_repository import (
    SqlAlchemyTaskRepository,
)
from src.planning.public_api import (
    PlanningExecutionBridgePort,
    create_planning_execution_bridge,
)
from src.shared_kernel.application.uow import AsyncUnitOfWork
from src.shared_kernel.config import get_settings
from src.shared_kernel.infrastructure.database.session import get_async_session
from src.shared_kernel.infrastructure.database.sqlalchemy_uow import SqlAlchemyUnitOfWork

security_bearer = HTTPBearer(auto_error=False)


async def get_execution_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Composition root dependency for Execution Bounded Context."""
    async for session in get_async_session():
        yield session


def get_execution_uow(
    session: AsyncSession = Depends(get_execution_db_session),
) -> AsyncUnitOfWork:
    return SqlAlchemyUnitOfWork(session)


def get_task_repository(
    session: AsyncSession = Depends(get_execution_db_session),
) -> TaskRepositoryPort:
    return SqlAlchemyTaskRepository(session)


def get_study_session_repository(
    session: AsyncSession = Depends(get_execution_db_session),
) -> StudySessionRepositoryPort:
    return SqlAlchemyStudySessionRepository(session)


def get_execution_planning_bridge(
    session: AsyncSession = Depends(get_execution_db_session),
) -> PlanningExecutionBridgePort:
    return create_planning_execution_bridge(session)


def get_execution_user_query_port(
    session: AsyncSession = Depends(get_execution_db_session),
) -> UserQueryPort:
    return create_user_query_port(session)


def get_execution_schedule_change_log_port(
    session: AsyncSession = Depends(get_execution_db_session),
) -> ScheduleChangeLogPort:
    return create_schedule_change_log_port(session)


async def get_current_execution_learner_id(
    request: Request,
    bearer: HTTPAuthorizationCredentials | None = Depends(security_bearer),
    user_query_port: UserQueryPort = Depends(get_execution_user_query_port),
) -> UUID:
    """Extract authenticated learner UUID from JWT Bearer header or HttpOnly cookie (ADR-008)."""
    overrides = getattr(request.app, "dependency_overrides", {})
    for dep_fn, override_fn in overrides.items():
        if getattr(dep_fn, "__name__", "") in (
            "get_current_learner_id",
            "get_current_execution_learner_id",
        ):
            res = override_fn()
            if inspect.isawaitable(res):
                res = await res
            if isinstance(res, UUID):
                return res
            return UUID(str(res))

    token: str | None = None
    if bearer and bearer.credentials:
        token = bearer.credentials
    elif "access_token" in request.cookies:
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        sub = payload.get("sub")
        if not sub:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user_id = UUID(str(sub))
    except ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please refresh your session.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except (PyJWTError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user_snap = await user_query_port.get_user_by_id(user_id)
    if user_snap is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User associated with this token no longer exists.",
        )
    if user_snap.role == "LOCKED" or user_snap.is_locked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been locked or suspended.",
        )
    return user_snap.id


# --- Task Use Case Factories ---
def get_list_tasks_use_case(
    task_repo: TaskRepositoryPort = Depends(get_task_repository),
    planning_bridge: PlanningExecutionBridgePort = Depends(get_execution_planning_bridge),
    user_query_port: UserQueryPort = Depends(get_execution_user_query_port),
) -> ListTasksUseCase:
    return ListTasksUseCase(
        task_repo=task_repo,
        planning_bridge=planning_bridge,
        user_query_port=user_query_port,
    )


def get_create_manual_task_use_case(
    task_repo: TaskRepositoryPort = Depends(get_task_repository),
    planning_bridge: PlanningExecutionBridgePort = Depends(get_execution_planning_bridge),
    uow: AsyncUnitOfWork = Depends(get_execution_uow),
    user_query_port: UserQueryPort = Depends(get_execution_user_query_port),
) -> CreateManualTaskUseCase:
    return CreateManualTaskUseCase(
        task_repo=task_repo,
        planning_bridge=planning_bridge,
        uow=uow,
        user_query_port=user_query_port,
    )


def get_backlog_tasks_use_case(
    task_repo: TaskRepositoryPort = Depends(get_task_repository),
    planning_bridge: PlanningExecutionBridgePort = Depends(get_execution_planning_bridge),
    user_query_port: UserQueryPort = Depends(get_execution_user_query_port),
) -> GetBacklogTasksUseCase:
    return GetBacklogTasksUseCase(
        task_repo=task_repo,
        planning_bridge=planning_bridge,
        user_query_port=user_query_port,
    )


def get_weekly_schedule_use_case(
    task_repo: TaskRepositoryPort = Depends(get_task_repository),
    planning_bridge: PlanningExecutionBridgePort = Depends(get_execution_planning_bridge),
    user_query_port: UserQueryPort = Depends(get_execution_user_query_port),
) -> GetWeeklyScheduleUseCase:
    return GetWeeklyScheduleUseCase(
        task_repo=task_repo,
        planning_bridge=planning_bridge,
        user_query_port=user_query_port,
    )


def get_update_task_use_case(
    task_repo: TaskRepositoryPort = Depends(get_task_repository),
    planning_bridge: PlanningExecutionBridgePort = Depends(get_execution_planning_bridge),
    uow: AsyncUnitOfWork = Depends(get_execution_uow),
    user_query_port: UserQueryPort = Depends(get_execution_user_query_port),
) -> UpdateTaskUseCase:
    return UpdateTaskUseCase(
        task_repo=task_repo,
        planning_bridge=planning_bridge,
        uow=uow,
        user_query_port=user_query_port,
    )


def get_complete_task_use_case(
    task_repo: TaskRepositoryPort = Depends(get_task_repository),
    session_repo: StudySessionRepositoryPort = Depends(get_study_session_repository),
    planning_bridge: PlanningExecutionBridgePort = Depends(get_execution_planning_bridge),
    uow: AsyncUnitOfWork = Depends(get_execution_uow),
    user_query_port: UserQueryPort = Depends(get_execution_user_query_port),
) -> CompleteTaskUseCase:
    return CompleteTaskUseCase(
        task_repo=task_repo,
        planning_bridge=planning_bridge,
        uow=uow,
        note_saver=session_repo.upsert_study_note,
        user_query_port=user_query_port,
    )


def get_reopen_task_use_case(
    task_repo: TaskRepositoryPort = Depends(get_task_repository),
    planning_bridge: PlanningExecutionBridgePort = Depends(get_execution_planning_bridge),
    uow: AsyncUnitOfWork = Depends(get_execution_uow),
    user_query_port: UserQueryPort = Depends(get_execution_user_query_port),
) -> ReopenTaskUseCase:
    return ReopenTaskUseCase(
        task_repo=task_repo,
        planning_bridge=planning_bridge,
        uow=uow,
        user_query_port=user_query_port,
    )


def get_reschedule_task_use_case(
    task_repo: TaskRepositoryPort = Depends(get_task_repository),
    planning_bridge: PlanningExecutionBridgePort = Depends(get_execution_planning_bridge),
    schedule_change_log_port: ScheduleChangeLogPort = Depends(
        get_execution_schedule_change_log_port
    ),
    uow: AsyncUnitOfWork = Depends(get_execution_uow),
    user_query_port: UserQueryPort = Depends(get_execution_user_query_port),
) -> RescheduleTaskUseCase:
    return RescheduleTaskUseCase(
        task_repo=task_repo,
        planning_bridge=planning_bridge,
        schedule_change_log_port=schedule_change_log_port,
        uow=uow,
        user_query_port=user_query_port,
    )


def get_delete_task_use_case(
    task_repo: TaskRepositoryPort = Depends(get_task_repository),
    planning_bridge: PlanningExecutionBridgePort = Depends(get_execution_planning_bridge),
    uow: AsyncUnitOfWork = Depends(get_execution_uow),
    user_query_port: UserQueryPort = Depends(get_execution_user_query_port),
) -> DeleteTaskUseCase:
    return DeleteTaskUseCase(
        task_repo=task_repo,
        planning_bridge=planning_bridge,
        uow=uow,
        user_query_port=user_query_port,
    )


def get_add_task_dependency_use_case(
    task_repo: TaskRepositoryPort = Depends(get_task_repository),
    planning_bridge: PlanningExecutionBridgePort = Depends(get_execution_planning_bridge),
    uow: AsyncUnitOfWork = Depends(get_execution_uow),
) -> AddTaskDependencyUseCase:
    return AddTaskDependencyUseCase(
        task_repo=task_repo,
        planning_bridge=planning_bridge,
        uow=uow,
    )


def get_delete_task_dependency_use_case(
    task_repo: TaskRepositoryPort = Depends(get_task_repository),
    planning_bridge: PlanningExecutionBridgePort = Depends(get_execution_planning_bridge),
    uow: AsyncUnitOfWork = Depends(get_execution_uow),
) -> DeleteTaskDependencyUseCase:
    return DeleteTaskDependencyUseCase(
        task_repo=task_repo,
        planning_bridge=planning_bridge,
        uow=uow,
    )


# --- Session Use Case Factories ---
def get_today_focus_use_case(
    session_repo: StudySessionRepositoryPort = Depends(get_study_session_repository),
    task_repo: TaskRepositoryPort = Depends(get_task_repository),
    planning_bridge: PlanningExecutionBridgePort = Depends(get_execution_planning_bridge),
    user_query_port: UserQueryPort = Depends(get_execution_user_query_port),
) -> GetTodayFocusUseCase:
    return GetTodayFocusUseCase(
        session_repo=session_repo,
        task_repo=task_repo,
        planning_bridge=planning_bridge,
        user_query_port=user_query_port,
    )


def get_active_session_use_case(
    session_repo: StudySessionRepositoryPort = Depends(get_study_session_repository),
) -> GetActiveSessionUseCase:
    return GetActiveSessionUseCase(session_repo=session_repo)


def get_start_study_session_use_case(
    session_repo: StudySessionRepositoryPort = Depends(get_study_session_repository),
    task_repo: TaskRepositoryPort = Depends(get_task_repository),
    planning_bridge: PlanningExecutionBridgePort = Depends(get_execution_planning_bridge),
    uow: AsyncUnitOfWork = Depends(get_execution_uow),
) -> StartStudySessionUseCase:
    return StartStudySessionUseCase(
        session_repo=session_repo,
        task_repo=task_repo,
        planning_bridge=planning_bridge,
        uow=uow,
    )


def get_heartbeat_study_session_use_case(
    session_repo: StudySessionRepositoryPort = Depends(get_study_session_repository),
    uow: AsyncUnitOfWork = Depends(get_execution_uow),
) -> HeartbeatStudySessionUseCase:
    return HeartbeatStudySessionUseCase(
        session_repo=session_repo,
        uow=uow,
    )


def get_finalize_study_session_use_case(
    session_repo: StudySessionRepositoryPort = Depends(get_study_session_repository),
    task_repo: TaskRepositoryPort = Depends(get_task_repository),
    planning_bridge: PlanningExecutionBridgePort = Depends(get_execution_planning_bridge),
    uow: AsyncUnitOfWork = Depends(get_execution_uow),
) -> FinalizeStudySessionUseCase:
    return FinalizeStudySessionUseCase(
        session_repo=session_repo,
        task_repo=task_repo,
        planning_bridge=planning_bridge,
        uow=uow,
    )


def get_resolve_pending_takeaway_use_case(
    session_repo: StudySessionRepositoryPort = Depends(get_study_session_repository),
    task_repo: TaskRepositoryPort = Depends(get_task_repository),
    uow: AsyncUnitOfWork = Depends(get_execution_uow),
) -> ResolvePendingTakeawayUseCase:
    return ResolvePendingTakeawayUseCase(
        session_repo=session_repo,
        task_repo=task_repo,
        uow=uow,
    )


CurrentExecutionLearnerIdDep = Annotated[UUID, Depends(get_current_execution_learner_id)]
ListTasksUseCaseDep = Annotated[ListTasksUseCase, Depends(get_list_tasks_use_case)]
CreateManualTaskUseCaseDep = Annotated[
    CreateManualTaskUseCase, Depends(get_create_manual_task_use_case)
]
GetBacklogTasksUseCaseDep = Annotated[GetBacklogTasksUseCase, Depends(get_backlog_tasks_use_case)]
GetWeeklyScheduleUseCaseDep = Annotated[
    GetWeeklyScheduleUseCase, Depends(get_weekly_schedule_use_case)
]
UpdateTaskUseCaseDep = Annotated[UpdateTaskUseCase, Depends(get_update_task_use_case)]
CompleteTaskUseCaseDep = Annotated[CompleteTaskUseCase, Depends(get_complete_task_use_case)]
ReopenTaskUseCaseDep = Annotated[ReopenTaskUseCase, Depends(get_reopen_task_use_case)]
RescheduleTaskUseCaseDep = Annotated[RescheduleTaskUseCase, Depends(get_reschedule_task_use_case)]
DeleteTaskUseCaseDep = Annotated[DeleteTaskUseCase, Depends(get_delete_task_use_case)]
AddTaskDependencyUseCaseDep = Annotated[
    AddTaskDependencyUseCase, Depends(get_add_task_dependency_use_case)
]
DeleteTaskDependencyUseCaseDep = Annotated[
    DeleteTaskDependencyUseCase, Depends(get_delete_task_dependency_use_case)
]
GetTodayFocusUseCaseDep = Annotated[GetTodayFocusUseCase, Depends(get_today_focus_use_case)]
GetActiveSessionUseCaseDep = Annotated[
    GetActiveSessionUseCase, Depends(get_active_session_use_case)
]
StartStudySessionUseCaseDep = Annotated[
    StartStudySessionUseCase, Depends(get_start_study_session_use_case)
]
HeartbeatStudySessionUseCaseDep = Annotated[
    HeartbeatStudySessionUseCase, Depends(get_heartbeat_study_session_use_case)
]
FinalizeStudySessionUseCaseDep = Annotated[
    FinalizeStudySessionUseCase, Depends(get_finalize_study_session_use_case)
]
ResolvePendingTakeawayUseCaseDep = Annotated[
    ResolvePendingTakeawayUseCase, Depends(get_resolve_pending_takeaway_use_case)
]
