import inspect
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import ExpiredSignatureError, PyJWTError
from sqlalchemy.ext.asyncio import AsyncSession

from src.account.public_api import (
    LearnerMemoryQueryPort,
    QuotaFacadePort,
    UserQueryPort,
    create_learner_memory_query_port,
    create_quota_facade,
    create_user_query_port,
)
from src.evaluation.application.ports.intelligence_repository_port import (
    EvaluationIntelligenceRepositoryPort,
)
from src.evaluation.application.use_cases.analytics import (
    GetAnalyticsSummaryUseCase,
    GetWeeklyAnalyticsUseCase,
)
from src.evaluation.application.use_cases.dashboard_summary import (
    GetDashboardSummaryUseCase,
)
from src.evaluation.application.use_cases.intelligence import (
    GenerateMilestoneProofUseCase,
    GenerateWeeklyReviewUseCase,
    GetLatestMilestoneProofUseCase,
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
from src.shared_kernel.infrastructure.external_ai.circuit_breaker import (
    wrap_with_circuit_breaker,
)
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
    provider: LLMProviderPort = LiteLLMAdapter()
    settings = get_settings()
    if not settings.ai_circuit_breaker_enabled:
        return provider
    return wrap_with_circuit_breaker(provider, provider_name="litellm")


class _AutonomousEvaluationQuotaFacade(QuotaFacadePort):
    """Wraps canonical Account QuotaFacadeAdapter in short-lived autonomous DB transactions.

    Ensures 2-phase quota reservations (RESERVE -> COMMIT | RELEASE) commit immediately
    without holding row locks across external LLM calls and survive multi-phase use cases
    (e.g., GenerateWeeklyReviewUseCase) that close their read session before LLM execution.
    """

    async def check_quota_available(
        self,
        user_id: UUID,
        min_credits: int = 1,
    ) -> bool:
        async with async_session_factory() as session:
            facade = create_quota_facade(session)
            available = await facade.check_quota_available(user_id, min_credits=min_credits)
            await session.commit()
            return available

    async def reserve_quota(
        self,
        user_id: UUID,
        operation_type: str = "ROADMAP_GEN",
        cost: int = 1,
        ttl_seconds: int = 120,
    ) -> UUID:
        async with async_session_factory() as session:
            facade = create_quota_facade(session)
            reservation_id = await facade.reserve_quota(
                user_id,
                operation_type=operation_type,
                cost=cost,
                ttl_seconds=ttl_seconds,
            )
            await session.commit()
            return reservation_id

    async def commit_reservation(
        self,
        reservation_id: UUID,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        model_name: str = "gemini-3.8-flash",
    ) -> None:
        async with async_session_factory() as session:
            facade = create_quota_facade(session)
            await facade.commit_reservation(
                reservation_id,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                model_name=model_name,
            )
            await session.commit()

    async def release_reservation(
        self,
        reservation_id: UUID,
        reason: str = "RELEASED",
    ) -> None:
        async with async_session_factory() as session:
            facade = create_quota_facade(session)
            await facade.release_reservation(reservation_id, reason=reason)
            await session.commit()

    async def expire_stale_reservations(self, now: datetime | None = None) -> int:
        async with async_session_factory() as session:
            facade = create_quota_facade(session)
            count = await facade.expire_stale_reservations(now=now)
            await session.commit()
            return count

    async def record_attempt_usage(
        self,
        *,
        user_id: UUID,
        action_type: str,
        requested_model: str = "gemini-3.8-flash",
        resolved_model: str | None = None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        thinking_tokens: int = 0,
        latency_ms: int = 0,
        status: Literal["SUCCESS", "FAILED", "RATE_LIMITED", "TIMEOUT"] = "SUCCESS",
        usage_completeness: Literal["COMPLETE", "PARTIAL", "UNKNOWN"] = "COMPLETE",
        usage_source: Literal[
            "GATEWAY_TELEMETRY", "CACHE", "ESTIMATED", "UNKNOWN"
        ] = "GATEWAY_TELEMETRY",
        error_code: str | None = None,
        error_message: str | None = None,
        attempt_no: int = 1,
        idempotency_key: str | None = None,
        reservation_id: UUID | None = None,
    ) -> Any:
        async with async_session_factory() as session:
            facade = create_quota_facade(session)
            res = await facade.record_attempt_usage(
                user_id=user_id,
                action_type=action_type,
                requested_model=requested_model,
                resolved_model=resolved_model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                thinking_tokens=thinking_tokens,
                latency_ms=latency_ms,
                status=status,
                usage_completeness=usage_completeness,
                usage_source=usage_source,
                error_code=error_code,
                error_message=error_message,
                attempt_no=attempt_no,
                idempotency_key=idempotency_key,
                reservation_id=reservation_id,
            )
            await session.commit()
            return res


def get_evaluation_quota_port() -> QuotaFacadePort:
    return _AutonomousEvaluationQuotaFacade()


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
    overrides = getattr(request.app, "dependency_overrides", {})
    for dep_fn, override_fn in overrides.items():
        if getattr(dep_fn, "__name__", "") in (
            "get_current_learner_id",
            "get_current_evaluation_learner_id",
        ):
            res = override_fn()
            if inspect.isawaitable(res):
                res = await res
            if isinstance(res, UUID):
                return res
            return UUID(str(res))

    token = bearer.credentials if bearer else request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )
    try:
        settings = get_settings()
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token")
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
    quota_port: QuotaFacadePort = Depends(get_evaluation_quota_port),
) -> GenerateMilestoneProofUseCase:
    return GenerateMilestoneProofUseCase(
        repository,
        ownership,
        uow,
        learner_memory_port=learner_memory_port,
        workflow_repo=workflow_repo,
        llm_provider=llm_provider,
        quota_port=quota_port,
    )


def get_latest_milestone_proof_use_case(
    repository: EvaluationIntelligenceRepositoryPort = Depends(get_intelligence_repository),
    ownership: MilestoneOwnershipQueryPort = Depends(get_milestone_ownership_port),
) -> GetLatestMilestoneProofUseCase:
    return GetLatestMilestoneProofUseCase(repository, ownership)


def get_submit_proof_use_case(
    repository: EvaluationIntelligenceRepositoryPort = Depends(get_intelligence_repository),
    uow: AsyncUnitOfWork = Depends(get_evaluation_uow),
    learner_memory_port: LearnerMemoryQueryPort = Depends(get_evaluation_learner_memory_port),
    workflow_repo: WorkflowRepositoryPort = Depends(get_evaluation_workflow_repository),
    llm_provider: LLMProviderPort = Depends(get_evaluation_llm_provider),
    quota_port: QuotaFacadePort = Depends(get_evaluation_quota_port),
) -> SubmitMilestoneProofUseCase:
    return SubmitMilestoneProofUseCase(
        repository,
        uow,
        learner_memory_port=learner_memory_port,
        workflow_repo=workflow_repo,
        llm_provider=llm_provider,
        quota_port=quota_port,
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
    quota_port: QuotaFacadePort = Depends(get_evaluation_quota_port),
) -> GenerateWeeklyReviewUseCase:
    return GenerateWeeklyReviewUseCase(
        repository,
        ownership,
        uow,
        learner_memory_port=learner_memory_port,
        execution_metrics_port=execution_metrics_port,
        workflow_repo=workflow_repo,
        llm_provider=llm_provider,
        quota_port=quota_port,
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


def get_analytics_summary_use_case(
    execution_port: ExecutionDashboardQueryPort = Depends(get_execution_dashboard_port),
    user_query_port: UserQueryPort = Depends(get_evaluation_user_query_port),
    weekly_metrics_port: WeeklyExecutionMetricsQueryPort = Depends(
        get_weekly_execution_metrics_port
    ),
) -> GetAnalyticsSummaryUseCase:
    return GetAnalyticsSummaryUseCase(
        execution_dashboard_port=execution_port,
        user_query_port=user_query_port,
        weekly_metrics_port=weekly_metrics_port,
    )


def get_weekly_analytics_use_case(
    execution_port: ExecutionDashboardQueryPort = Depends(get_execution_dashboard_port),
    user_query_port: UserQueryPort = Depends(get_evaluation_user_query_port),
    weekly_metrics_port: WeeklyExecutionMetricsQueryPort = Depends(
        get_weekly_execution_metrics_port
    ),
) -> GetWeeklyAnalyticsUseCase:
    return GetWeeklyAnalyticsUseCase(
        execution_dashboard_port=execution_port,
        user_query_port=user_query_port,
        weekly_metrics_port=weekly_metrics_port,
    )
