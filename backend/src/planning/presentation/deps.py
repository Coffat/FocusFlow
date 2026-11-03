import inspect
from collections.abc import AsyncGenerator
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import ExpiredSignatureError, PyJWTError
from sqlalchemy.ext.asyncio import AsyncSession

from src.account.public_api import (
    AvailabilityQueryPort,
    LearnerProfileQueryPort,
    QuotaFacadePort,
    UserQueryPort,
    create_availability_query_port,
    create_learner_profile_query_port,
    create_quota_facade,
    create_user_query_port,
)
from src.evaluation.public_api import (
    ScheduleChangeLogPort,
    create_schedule_change_log_port,
)
from src.execution.public_api import (
    ExecutionScheduleSyncPort,
    create_execution_schedule_sync_port,
)
from src.planning.application.ports.knowledge_base_port import KnowledgeBasePort
from src.planning.application.ports.planning_repository_ports import (
    GoalRepositoryPort,
    MilestoneRepositoryPort,
    OfficialScheduleRepositoryPort,
    RoadmapRepositoryPort,
    ScheduleProposalRepositoryPort,
)
from src.planning.application.ports.sse_job_port import SseJobPort
from src.planning.application.use_cases import (
    ApplyScheduleProposalUseCase,
    ApproveMilestonesUseCase,
    ArchiveRoadmapUseCase,
    CreateGoalAndRoadmapUseCase,
    ExecuteMilestoneGenerationUseCase,
    ExecuteScheduleProposalGenerationUseCase,
    GenerateClarificationQuestionsUseCase,
    GetCurrentScheduleProposalUseCase,
    GetRoadmapDetailUseCase,
    InitiateMilestoneGenerationUseCase,
    InitiateScheduleProposalGenerationUseCase,
    ListRoadmapsUseCase,
    SaveManualRoadmapPlanUseCase,
    SubmitClarificationAnswersUseCase,
    UpdateMilestonesUseCase,
    UpdateRoadmapUseCase,
    UpdateScheduleProposalUseCase,
)
from src.planning.infrastructure.repositories.planning_repositories import (
    SqlAlchemyGoalRepository,
    SqlAlchemyMilestoneRepository,
    SqlAlchemyOfficialScheduleRepository,
    SqlAlchemyRoadmapRepository,
    SqlAlchemyScheduleProposalRepository,
)
from src.planning.infrastructure.repositories.sqlalchemy_knowledge_base_repository import (
    SqlAlchemyKnowledgeBaseRepository,
)
from src.planning.infrastructure.sse import default_in_memory_sse_job_store
from src.shared_kernel.application.llm_port import LLMProviderPort
from src.shared_kernel.application.uow import AsyncUnitOfWork
from src.shared_kernel.config import get_settings
from src.shared_kernel.infrastructure.database.session import get_async_session
from src.shared_kernel.infrastructure.database.sqlalchemy_uow import (
    SqlAlchemyUnitOfWork,
)
from src.shared_kernel.infrastructure.external_ai.litellm_adapter import (
    LiteLLMAdapter,
)

security_bearer = HTTPBearer(auto_error=False)


# --- Database & Unit of Work Dependencies ---
async def get_planning_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Composition root dependency for Planning Bounded Context."""
    async for session in get_async_session():
        yield session


def get_planning_uow(
    session: AsyncSession = Depends(get_planning_db_session),
) -> AsyncUnitOfWork:
    return SqlAlchemyUnitOfWork(session)


# --- Planning Repository Dependencies ---
def get_goal_repository(
    session: AsyncSession = Depends(get_planning_db_session),
) -> GoalRepositoryPort:
    return SqlAlchemyGoalRepository(session)


def get_roadmap_repository(
    session: AsyncSession = Depends(get_planning_db_session),
) -> RoadmapRepositoryPort:
    return SqlAlchemyRoadmapRepository(session)


def get_milestone_repository(
    session: AsyncSession = Depends(get_planning_db_session),
) -> MilestoneRepositoryPort:
    return SqlAlchemyMilestoneRepository(session)


def get_schedule_proposal_repository(
    session: AsyncSession = Depends(get_planning_db_session),
) -> ScheduleProposalRepositoryPort:
    return SqlAlchemyScheduleProposalRepository(session)


def get_official_schedule_repository(
    session: AsyncSession = Depends(get_planning_db_session),
) -> OfficialScheduleRepositoryPort:
    return SqlAlchemyOfficialScheduleRepository(session)


def get_knowledge_base_repository(
    session: AsyncSession = Depends(get_planning_db_session),
) -> KnowledgeBasePort:
    return SqlAlchemyKnowledgeBaseRepository(session)


# --- Cross-Context & Shared Kernel Port Dependencies ---
def get_planning_quota_facade(
    session: AsyncSession = Depends(get_planning_db_session),
) -> QuotaFacadePort:
    return create_quota_facade(session)


def get_planning_availability_query_port(
    session: AsyncSession = Depends(get_planning_db_session),
) -> AvailabilityQueryPort:
    return create_availability_query_port(session)


def get_planning_learner_profile_port(
    session: AsyncSession = Depends(get_planning_db_session),
) -> LearnerProfileQueryPort:
    return create_learner_profile_query_port(session)


def get_planning_user_query_port(
    session: AsyncSession = Depends(get_planning_db_session),
) -> UserQueryPort:
    return create_user_query_port(session)


def get_planning_execution_sync_port(
    session: AsyncSession = Depends(get_planning_db_session),
) -> ExecutionScheduleSyncPort:
    return create_execution_schedule_sync_port(session)


def get_planning_schedule_change_log_port(
    session: AsyncSession = Depends(get_planning_db_session),
) -> ScheduleChangeLogPort:
    return create_schedule_change_log_port(session)


def get_llm_provider() -> LLMProviderPort:
    return LiteLLMAdapter()


def get_sse_job_store() -> SseJobPort:
    return default_in_memory_sse_job_store


# --- Authentication Dependency ---
async def get_current_learner_id(
    request: Request,
    bearer: HTTPAuthorizationCredentials | None = Depends(security_bearer),
    user_query_port: UserQueryPort = Depends(get_planning_user_query_port),
) -> UUID:
    """Extract authenticated learner UUID from JWT Bearer header or HttpOnly cookie (ADR-008)."""
    # Support tests that override `get_current_learner_id` from `account.presentation.deps`
    overrides = getattr(request.app, "dependency_overrides", {})
    for dep_fn, override_fn in overrides.items():
        if getattr(dep_fn, "__name__", "") == "get_current_learner_id":
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


# --- Use Case Factories ---
def get_create_goal_and_roadmap_use_case(
    goal_repo: GoalRepositoryPort = Depends(get_goal_repository),
    roadmap_repo: RoadmapRepositoryPort = Depends(get_roadmap_repository),
    uow: AsyncUnitOfWork = Depends(get_planning_uow),
    user_query_port: UserQueryPort = Depends(get_planning_user_query_port),
) -> CreateGoalAndRoadmapUseCase:
    return CreateGoalAndRoadmapUseCase(
        goal_repo=goal_repo,
        roadmap_repo=roadmap_repo,
        uow=uow,
        user_query_port=user_query_port,
    )


def get_generate_clarification_questions_use_case(
    goal_repo: GoalRepositoryPort = Depends(get_goal_repository),
    quota_facade: QuotaFacadePort = Depends(get_planning_quota_facade),
    llm_provider: LLMProviderPort = Depends(get_llm_provider),
) -> GenerateClarificationQuestionsUseCase:
    return GenerateClarificationQuestionsUseCase(
        goal_repo=goal_repo,
        quota_facade=quota_facade,
        llm_provider=llm_provider,
    )


def get_submit_clarification_answers_use_case(
    goal_repo: GoalRepositoryPort = Depends(get_goal_repository),
    uow: AsyncUnitOfWork = Depends(get_planning_uow),
) -> SubmitClarificationAnswersUseCase:
    return SubmitClarificationAnswersUseCase(
        goal_repo=goal_repo,
        uow=uow,
    )


def get_execute_milestone_generation_use_case(
    goal_repo: GoalRepositoryPort = Depends(get_goal_repository),
    roadmap_repo: RoadmapRepositoryPort = Depends(get_roadmap_repository),
    milestone_repo: MilestoneRepositoryPort = Depends(get_milestone_repository),
    quota_facade: QuotaFacadePort = Depends(get_planning_quota_facade),
    llm_provider: LLMProviderPort = Depends(get_llm_provider),
    sse_job_store: SseJobPort = Depends(get_sse_job_store),
    uow: AsyncUnitOfWork = Depends(get_planning_uow),
    knowledge_base: KnowledgeBasePort | None = Depends(get_knowledge_base_repository),
) -> ExecuteMilestoneGenerationUseCase:
    effective_kb = knowledge_base if isinstance(knowledge_base, KnowledgeBasePort) else None
    return ExecuteMilestoneGenerationUseCase(
        goal_repo=goal_repo,
        roadmap_repo=roadmap_repo,
        milestone_repo=milestone_repo,
        quota_facade=quota_facade,
        llm_provider=llm_provider,
        sse_job_store=sse_job_store,
        uow=uow,
        knowledge_base=effective_kb,
    )


def get_initiate_milestone_generation_use_case(
    roadmap_repo: RoadmapRepositoryPort = Depends(get_roadmap_repository),
    quota_facade: QuotaFacadePort = Depends(get_planning_quota_facade),
    sse_job_store: SseJobPort = Depends(get_sse_job_store),
    uow: AsyncUnitOfWork = Depends(get_planning_uow),
    executor: ExecuteMilestoneGenerationUseCase = Depends(
        get_execute_milestone_generation_use_case
    ),
) -> InitiateMilestoneGenerationUseCase:
    return InitiateMilestoneGenerationUseCase(
        roadmap_repo=roadmap_repo,
        quota_facade=quota_facade,
        sse_job_store=sse_job_store,
        uow=uow,
        executor=executor,
    )


def get_update_milestones_use_case(
    roadmap_repo: RoadmapRepositoryPort = Depends(get_roadmap_repository),
    milestone_repo: MilestoneRepositoryPort = Depends(get_milestone_repository),
    uow: AsyncUnitOfWork = Depends(get_planning_uow),
) -> UpdateMilestonesUseCase:
    return UpdateMilestonesUseCase(
        roadmap_repo=roadmap_repo,
        milestone_repo=milestone_repo,
        uow=uow,
    )


def get_approve_milestones_use_case(
    roadmap_repo: RoadmapRepositoryPort = Depends(get_roadmap_repository),
    milestone_repo: MilestoneRepositoryPort = Depends(get_milestone_repository),
    uow: AsyncUnitOfWork = Depends(get_planning_uow),
) -> ApproveMilestonesUseCase:
    return ApproveMilestonesUseCase(
        roadmap_repo=roadmap_repo,
        milestone_repo=milestone_repo,
        uow=uow,
    )


def get_execute_schedule_proposal_generation_use_case(
    goal_repo: GoalRepositoryPort = Depends(get_goal_repository),
    roadmap_repo: RoadmapRepositoryPort = Depends(get_roadmap_repository),
    milestone_repo: MilestoneRepositoryPort = Depends(get_milestone_repository),
    proposal_repo: ScheduleProposalRepositoryPort = Depends(get_schedule_proposal_repository),
    availability_query_port: AvailabilityQueryPort = Depends(get_planning_availability_query_port),
    learner_profile_port: LearnerProfileQueryPort = Depends(get_planning_learner_profile_port),
    execution_sync_port: ExecutionScheduleSyncPort = Depends(get_planning_execution_sync_port),
    quota_facade: QuotaFacadePort = Depends(get_planning_quota_facade),
    llm_provider: LLMProviderPort = Depends(get_llm_provider),
    sse_job_store: SseJobPort = Depends(get_sse_job_store),
    uow: AsyncUnitOfWork = Depends(get_planning_uow),
    knowledge_base: KnowledgeBasePort | None = Depends(get_knowledge_base_repository),
) -> ExecuteScheduleProposalGenerationUseCase:
    effective_kb = knowledge_base if isinstance(knowledge_base, KnowledgeBasePort) else None
    return ExecuteScheduleProposalGenerationUseCase(
        goal_repo=goal_repo,
        roadmap_repo=roadmap_repo,
        milestone_repo=milestone_repo,
        proposal_repo=proposal_repo,
        availability_query_port=availability_query_port,
        learner_profile_port=learner_profile_port,
        execution_sync_port=execution_sync_port,
        quota_facade=quota_facade,
        llm_provider=llm_provider,
        sse_job_store=sse_job_store,
        uow=uow,
        enable_tier3_judge=get_settings().enable_tier3_judge,
        knowledge_base=effective_kb,
    )


def get_initiate_schedule_proposal_generation_use_case(
    roadmap_repo: RoadmapRepositoryPort = Depends(get_roadmap_repository),
    milestone_repo: MilestoneRepositoryPort = Depends(get_milestone_repository),
    quota_facade: QuotaFacadePort = Depends(get_planning_quota_facade),
    sse_job_store: SseJobPort = Depends(get_sse_job_store),
    uow: AsyncUnitOfWork = Depends(get_planning_uow),
    executor: ExecuteScheduleProposalGenerationUseCase = Depends(
        get_execute_schedule_proposal_generation_use_case
    ),
) -> InitiateScheduleProposalGenerationUseCase:
    return InitiateScheduleProposalGenerationUseCase(
        roadmap_repo=roadmap_repo,
        milestone_repo=milestone_repo,
        quota_facade=quota_facade,
        sse_job_store=sse_job_store,
        uow=uow,
        executor=executor,
    )


def get_get_current_schedule_proposal_use_case(
    roadmap_repo: RoadmapRepositoryPort = Depends(get_roadmap_repository),
    proposal_repo: ScheduleProposalRepositoryPort = Depends(get_schedule_proposal_repository),
    execution_sync_port: ExecutionScheduleSyncPort = Depends(get_planning_execution_sync_port),
) -> GetCurrentScheduleProposalUseCase:
    return GetCurrentScheduleProposalUseCase(
        roadmap_repo=roadmap_repo,
        proposal_repo=proposal_repo,
        execution_sync_port=execution_sync_port,
    )


def get_update_schedule_proposal_use_case(
    roadmap_repo: RoadmapRepositoryPort = Depends(get_roadmap_repository),
    milestone_repo: MilestoneRepositoryPort = Depends(get_milestone_repository),
    proposal_repo: ScheduleProposalRepositoryPort = Depends(get_schedule_proposal_repository),
    availability_query_port: AvailabilityQueryPort = Depends(get_planning_availability_query_port),
    execution_sync_port: ExecutionScheduleSyncPort = Depends(get_planning_execution_sync_port),
    uow: AsyncUnitOfWork = Depends(get_planning_uow),
) -> UpdateScheduleProposalUseCase:
    return UpdateScheduleProposalUseCase(
        roadmap_repo=roadmap_repo,
        milestone_repo=milestone_repo,
        proposal_repo=proposal_repo,
        availability_query_port=availability_query_port,
        execution_sync_port=execution_sync_port,
        uow=uow,
    )


def get_apply_schedule_proposal_use_case(
    roadmap_repo: RoadmapRepositoryPort = Depends(get_roadmap_repository),
    milestone_repo: MilestoneRepositoryPort = Depends(get_milestone_repository),
    proposal_repo: ScheduleProposalRepositoryPort = Depends(get_schedule_proposal_repository),
    schedule_repo: OfficialScheduleRepositoryPort = Depends(get_official_schedule_repository),
    availability_query_port: AvailabilityQueryPort = Depends(get_planning_availability_query_port),
    execution_sync_port: ExecutionScheduleSyncPort = Depends(get_planning_execution_sync_port),
    schedule_change_log_port: ScheduleChangeLogPort = Depends(
        get_planning_schedule_change_log_port
    ),
    uow: AsyncUnitOfWork = Depends(get_planning_uow),
    user_query_port: UserQueryPort = Depends(get_planning_user_query_port),
) -> ApplyScheduleProposalUseCase:
    return ApplyScheduleProposalUseCase(
        roadmap_repo=roadmap_repo,
        milestone_repo=milestone_repo,
        proposal_repo=proposal_repo,
        schedule_repo=schedule_repo,
        availability_query_port=availability_query_port,
        execution_sync_port=execution_sync_port,
        schedule_change_log_port=schedule_change_log_port,
        uow=uow,
        user_query_port=user_query_port,
    )


def get_save_manual_roadmap_plan_use_case(
    goal_repo: GoalRepositoryPort = Depends(get_goal_repository),
    roadmap_repo: RoadmapRepositoryPort = Depends(get_roadmap_repository),
    milestone_repo: MilestoneRepositoryPort = Depends(get_milestone_repository),
    proposal_repo: ScheduleProposalRepositoryPort = Depends(get_schedule_proposal_repository),
    availability_query_port: AvailabilityQueryPort = Depends(get_planning_availability_query_port),
    execution_sync_port: ExecutionScheduleSyncPort = Depends(get_planning_execution_sync_port),
    uow: AsyncUnitOfWork = Depends(get_planning_uow),
) -> SaveManualRoadmapPlanUseCase:
    return SaveManualRoadmapPlanUseCase(
        goal_repo=goal_repo,
        roadmap_repo=roadmap_repo,
        milestone_repo=milestone_repo,
        proposal_repo=proposal_repo,
        availability_query_port=availability_query_port,
        execution_sync_port=execution_sync_port,
        uow=uow,
    )


def get_list_roadmaps_use_case(
    roadmap_repo: RoadmapRepositoryPort = Depends(get_roadmap_repository),
) -> ListRoadmapsUseCase:
    return ListRoadmapsUseCase(roadmap_repo=roadmap_repo)


def get_get_roadmap_detail_use_case(
    goal_repo: GoalRepositoryPort = Depends(get_goal_repository),
    roadmap_repo: RoadmapRepositoryPort = Depends(get_roadmap_repository),
    milestone_repo: MilestoneRepositoryPort = Depends(get_milestone_repository),
    schedule_repo: OfficialScheduleRepositoryPort = Depends(get_official_schedule_repository),
    proposal_repo: ScheduleProposalRepositoryPort = Depends(get_schedule_proposal_repository),
    execution_sync_port: ExecutionScheduleSyncPort = Depends(get_planning_execution_sync_port),
) -> GetRoadmapDetailUseCase:
    return GetRoadmapDetailUseCase(
        goal_repo=goal_repo,
        roadmap_repo=roadmap_repo,
        milestone_repo=milestone_repo,
        schedule_repo=schedule_repo,
        proposal_repo=proposal_repo,
        execution_sync_port=execution_sync_port,
    )


def get_update_roadmap_use_case(
    goal_repo: GoalRepositoryPort = Depends(get_goal_repository),
    roadmap_repo: RoadmapRepositoryPort = Depends(get_roadmap_repository),
    uow: AsyncUnitOfWork = Depends(get_planning_uow),
    user_query_port: UserQueryPort = Depends(get_planning_user_query_port),
) -> UpdateRoadmapUseCase:
    return UpdateRoadmapUseCase(
        goal_repo=goal_repo,
        roadmap_repo=roadmap_repo,
        uow=uow,
        user_query_port=user_query_port,
    )


def get_archive_roadmap_use_case(
    goal_repo: GoalRepositoryPort = Depends(get_goal_repository),
    roadmap_repo: RoadmapRepositoryPort = Depends(get_roadmap_repository),
    uow: AsyncUnitOfWork = Depends(get_planning_uow),
) -> ArchiveRoadmapUseCase:
    return ArchiveRoadmapUseCase(
        goal_repo=goal_repo,
        roadmap_repo=roadmap_repo,
        uow=uow,
    )


# --- Annotated Dependencies for Routers (Depends stays 100% in deps.py) ---
CurrentLearnerIdDep = Annotated[UUID, Depends(get_current_learner_id)]
SseJobStoreDep = Annotated[SseJobPort, Depends(get_sse_job_store)]
CreateGoalAndRoadmapUseCaseDep = Annotated[
    CreateGoalAndRoadmapUseCase, Depends(get_create_goal_and_roadmap_use_case)
]
InitiateMilestoneGenUseCaseDep = Annotated[
    InitiateMilestoneGenerationUseCase,
    Depends(get_initiate_milestone_generation_use_case),
]
UpdateMilestonesUseCaseDep = Annotated[
    UpdateMilestonesUseCase, Depends(get_update_milestones_use_case)
]
ApproveMilestonesUseCaseDep = Annotated[
    ApproveMilestonesUseCase, Depends(get_approve_milestones_use_case)
]
InitiateProposalGenUseCaseDep = Annotated[
    InitiateScheduleProposalGenerationUseCase,
    Depends(get_initiate_schedule_proposal_generation_use_case),
]
GetCurrentProposalUseCaseDep = Annotated[
    GetCurrentScheduleProposalUseCase,
    Depends(get_get_current_schedule_proposal_use_case),
]
UpdateProposalUseCaseDep = Annotated[
    UpdateScheduleProposalUseCase, Depends(get_update_schedule_proposal_use_case)
]
ApplyProposalUseCaseDep = Annotated[
    ApplyScheduleProposalUseCase, Depends(get_apply_schedule_proposal_use_case)
]
SaveManualPlanUseCaseDep = Annotated[
    SaveManualRoadmapPlanUseCase, Depends(get_save_manual_roadmap_plan_use_case)
]
ListRoadmapsUseCaseDep = Annotated[ListRoadmapsUseCase, Depends(get_list_roadmaps_use_case)]
GetRoadmapDetailUseCaseDep = Annotated[
    GetRoadmapDetailUseCase, Depends(get_get_roadmap_detail_use_case)
]
UpdateRoadmapUseCaseDep = Annotated[UpdateRoadmapUseCase, Depends(get_update_roadmap_use_case)]
ArchiveRoadmapUseCaseDep = Annotated[ArchiveRoadmapUseCase, Depends(get_archive_roadmap_use_case)]
GenerateClarificationQuestionsUseCaseDep = Annotated[
    GenerateClarificationQuestionsUseCase,
    Depends(get_generate_clarification_questions_use_case),
]
SubmitClarificationAnswersUseCaseDep = Annotated[
    SubmitClarificationAnswersUseCase,
    Depends(get_submit_clarification_answers_use_case),
]
