from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import ExpiredSignatureError, PyJWTError
from sqlalchemy.ext.asyncio import AsyncSession

from src.account.public_api import (
    LearnerMemoryQueryPort,
    UserQueryPort,
    create_learner_memory_query_port,
    create_user_query_port,
)
from src.evaluation.application.ports.intelligence_repository_port import (
    EvaluationIntelligenceRepositoryPort,
)
from src.evaluation.application.use_cases.dashboard_summary import (
    GetDashboardSummaryUseCase,
)
from src.evaluation.application.use_cases.intelligence import (
    GenerateMilestoneProofUseCase,
    GenerateWeeklyReviewUseCase,
    GetLatestWeeklyReviewUseCase,
    SubmitMilestoneProofUseCase,
    WeeklyReviewWriteScope,
)
from src.evaluation.infrastructure.repositories.intelligence_repository import (
    SqlAlchemyEvaluationIntelligenceRepository,
)
from src.execution.public_api import (
    ExecutionDashboardQueryPort,
    WeeklyExecutionMetricsQueryPort,
    create_execution_dashboard_query_port,
    create_weekly_execution_metrics_port,
)
from src.planning.public_api import (
    MilestoneOwnershipQueryPort,
    PlanningDashboardQueryPort,
    create_milestone_ownership_port,
    create_planning_dashboard_query_port,
)
from src.shared_kernel.application.harness.workflow_port import WorkflowRepositoryPort
from src.shared_kernel.application.llm_port import LLMProviderPort
from src.shared_kernel.application.uow import AsyncUnitOfWork
from src.shared_kernel.config import get_settings
from src.shared_kernel.infrastructure.database.session import (
    async_session_factory,
    get_async_session,
)
from src.shared_kernel.infrastructure.database.sqlalchemy_uow import SqlAlchemyUnitOfWork
from src.shared_kernel.infrastructure.external_ai.litellm_adapter import LiteLLMAdapter
from src.shared_kernel.infrastructure.workflow.repository import SqlAlchemyWorkflowRepository

security_bearer = HTTPBearer(auto_error=False)


async def get_evaluation_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Composition root dependency for Evaluation Bounded Context."""
    async for session in get_async_session():
        yield session


def get_evaluation_uow(
    session: AsyncSession = Depends(get_evaluation_db_session),
) -> AsyncUnitOfWork:
    return SqlAlchemyUnitOfWork(session)


def get_intelligence_repository(
    session: AsyncSession = Depends(get_evaluation_db_session),
) -> EvaluationIntelligenceRepositoryPort:
    return SqlAlchemyEvaluationIntelligenceRepository(session)


def get_milestone_ownership_port(
    session: AsyncSession = Depends(get_evaluation_db_session),
) -> MilestoneOwnershipQueryPort:
    return create_milestone_ownership_port(session)


def get_evaluation_user_query_port(
    session: AsyncSession = Depends(get_evaluation_db_session),
) -> UserQueryPort:
    return create_user_query_port(session)


def get_evaluation_learner_memory_port(
    session: AsyncSession = Depends(get_evaluation_db_session),
) -> LearnerMemoryQueryPort:
    return create_learner_memory_query_port(session)


def get_weekly_execution_metrics_port(
    session: AsyncSession = Depends(get_evaluation_db_session),
) -> WeeklyExecutionMetricsQueryPort:
    return create_weekly_execution_metrics_port(session)


def get_evaluation_workflow_repository(
    session: AsyncSession = Depends(get_evaluation_db_session),
) -> WorkflowRepositoryPort:
    return SqlAlchemyWorkflowRepository(session)


def get_evaluation_llm_provider() -> LLMProviderPort:
    return LiteLLMAdapter()


@asynccontextmanager
async def _open_weekly_review_write_scope() -> AsyncGenerator[WeeklyReviewWriteScope, None]:
    async with async_session_factory() as write_session:
        yield WeeklyReviewWriteScope(
            uow=SqlAlchemyUnitOfWork(write_session),
            repository=SqlAlchemyEvaluationIntelligenceRepository(write_session),
            learner_memory_port=create_learner_memory_query_port(write_session),
            workflow_repo=SqlAlchemyWorkflowRepository(write_session),
        )


async def get_current_evaluation_learner_id(
    request: Request,
    bearer: HTTPAuthorizationCredentials | None = Depends(security_bearer),
    users: UserQueryPort = Depends(get_evaluation_user_query_port),
) -> UUID:
    token = bearer.credentials if bearer else request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )
    try:
        settings = get_settings()
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        user_id = UUID(str(payload["sub"]))
    except ExpiredSignatureError as exc:
        raise HTTPException(status_code=401, detail="Token expired") from exc
    except (PyJWTError, KeyError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc
    user = await users.get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user_id


def get_generate_proof_use_case(
    repository: EvaluationIntelligenceRepositoryPort = Depends(get_intelligence_repository),
    ownership: MilestoneOwnershipQueryPort = Depends(get_milestone_ownership_port),
    uow: AsyncUnitOfWork = Depends(get_evaluation_uow),
    learner_memory_port: LearnerMemoryQueryPort = Depends(get_evaluation_learner_memory_port),
    workflow_repo: WorkflowRepositoryPort = Depends(get_evaluation_workflow_repository),
    llm_provider: LLMProviderPort = Depends(get_evaluation_llm_provider),
) -> GenerateMilestoneProofUseCase:
    return GenerateMilestoneProofUseCase(
        repository,
        ownership,
        uow,
        learner_memory_port=learner_memory_port,
        workflow_repo=workflow_repo,
        llm_provider=llm_provider,
    )


def get_submit_proof_use_case(
    repository: EvaluationIntelligenceRepositoryPort = Depends(get_intelligence_repository),
    uow: AsyncUnitOfWork = Depends(get_evaluation_uow),
    learner_memory_port: LearnerMemoryQueryPort = Depends(get_evaluation_learner_memory_port),
    workflow_repo: WorkflowRepositoryPort = Depends(get_evaluation_workflow_repository),
    llm_provider: LLMProviderPort = Depends(get_evaluation_llm_provider),
) -> SubmitMilestoneProofUseCase:
    return SubmitMilestoneProofUseCase(
        repository,
        uow,
        learner_memory_port=learner_memory_port,
        workflow_repo=workflow_repo,
        llm_provider=llm_provider,
    )


def get_generate_weekly_review_use_case(
    repository: EvaluationIntelligenceRepositoryPort = Depends(get_intelligence_repository),
    ownership: MilestoneOwnershipQueryPort = Depends(get_milestone_ownership_port),
    uow: AsyncUnitOfWork = Depends(get_evaluation_uow),
    learner_memory_port: LearnerMemoryQueryPort = Depends(get_evaluation_learner_memory_port),
    execution_metrics_port: WeeklyExecutionMetricsQueryPort = Depends(
        get_weekly_execution_metrics_port
    ),
    workflow_repo: WorkflowRepositoryPort = Depends(get_evaluation_workflow_repository),
    llm_provider: LLMProviderPort = Depends(get_evaluation_llm_provider),
) -> GenerateWeeklyReviewUseCase:
    return GenerateWeeklyReviewUseCase(
        repository,
        ownership,
        uow,
        learner_memory_port=learner_memory_port,
        execution_metrics_port=execution_metrics_port,
        workflow_repo=workflow_repo,
        llm_provider=llm_provider,
        write_scope_factory=_open_weekly_review_write_scope,
    )


def get_latest_weekly_review_use_case(
    repository: EvaluationIntelligenceRepositoryPort = Depends(get_intelligence_repository),
) -> GetLatestWeeklyReviewUseCase:
    return GetLatestWeeklyReviewUseCase(repository)


def get_planning_dashboard_port(
    session: AsyncSession = Depends(get_evaluation_db_session),
) -> PlanningDashboardQueryPort:
    return create_planning_dashboard_query_port(session)


def get_execution_dashboard_port(
    session: AsyncSession = Depends(get_evaluation_db_session),
) -> ExecutionDashboardQueryPort:
    return create_execution_dashboard_query_port(session)


def get_dashboard_summary_use_case(
    planning_port: PlanningDashboardQueryPort = Depends(get_planning_dashboard_port),
    execution_port: ExecutionDashboardQueryPort = Depends(get_execution_dashboard_port),
    intelligence_repo: EvaluationIntelligenceRepositoryPort = Depends(get_intelligence_repository),
    user_query_port: UserQueryPort = Depends(get_evaluation_user_query_port),
) -> GetDashboardSummaryUseCase:
    return GetDashboardSummaryUseCase(
        planning_port,
        execution_port,
        intelligence_repo,
        user_query_port=user_query_port,
    )
