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
    CalendarConnectionQueryPort,
    CalendarSyncFacadePort,
    LearnerMemoryQueryPort,
    LearnerProfileQueryPort,
    QuotaFacadePort,
    UserQueryPort,
    create_availability_query_port,
    create_calendar_connection_query_port,
    create_calendar_sync_facade,
    create_learner_memory_query_port,
    create_learner_profile_query_port,
    create_quota_facade,
    create_user_query_port,
)
from src.evaluation.public_api import (
    PauseRecordPort,
    ScheduleChangeLogPort,
    create_pause_record_port,
    create_schedule_change_log_port,
)
from src.execution.public_api import (
    ExecutionScheduleSyncPort,
    create_execution_schedule_sync_port,
)
from src.planning.application.knowledge import DocumentExtractor, SafeUrlFetcher, SemanticChunker
from src.planning.application.ports.knowledge_base_port import KnowledgeBasePort
from src.planning.application.ports.knowledge_source_repository_port import (
    KnowledgeSourceRepositoryPort,
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
    HandleAvailabilityUpdatedEventUseCase,
    InitiateMilestoneGenerationUseCase,
    InitiateOverdueRecoveryUseCase,
    InitiateScheduleProposalGenerationUseCase,
    ListRoadmapsUseCase,
    PauseRoadmapUseCase,
    ReoptimizeScheduleProposalUseCase,
    ResumeRoadmapUseCase,
    SaveManualRoadmapPlanUseCase,
    SubmitClarificationAnswersUseCase,
    UpdateMilestonesUseCase,
    UpdateRoadmapUseCase,
    UpdateScheduleProposalUseCase,
)
from src.planning.application.use_cases.knowledge_source_use_cases import (
    CreateKnowledgeSourceUseCase,
    IngestKnowledgeSourceUseCase,
)
from src.planning.infrastructure.knowledge import LocalKnowledgeFileStore
from src.planning.infrastructure.repositories.knowledge_source_repository import (
    SqlAlchemyKnowledgeSourceRepository,
)
from src.planning.infrastructure.repositories.planning_repositories import (
    SqlAlchemyGoalRepository,
    SqlAlchemyMilestoneRepository,
    SqlAlchemyOfficialScheduleRepository,
    SqlAlchemyRoadmapRepository,
    SqlAlchemyScheduleProposalRepository,
)
from src.planning.infrastructure.repositories.schedule_block_repository import (
    SqlAlchemyScheduleBlockRepository,
)
from src.planning.infrastructure.repositories.sqlalchemy_knowledge_base_repository import (
    SqlAlchemyKnowledgeBaseRepository,
)
from src.planning.infrastructure.sse import default_redis_sse_job_store
from src.shared_kernel.application.embedding_port import EmbeddingProviderPort
from src.shared_kernel.application.event_bus import OutboxRepositoryPort
from src.shared_kernel.application.harness.workflow_port import WorkflowRepositoryPort
from src.shared_kernel.application.llm_port import LLMProviderPort
from src.shared_kernel.application.uow import AsyncUnitOfWork
from src.shared_kernel.config import get_settings
from src.shared_kernel.infrastructure.database.session import get_async_session
from src.shared_kernel.infrastructure.database.sqlalchemy_uow import (
    SqlAlchemyUnitOfWork,
)
from src.shared_kernel.infrastructure.external_ai.circuit_breaker import (
    wrap_with_circuit_breaker,
)
from src.shared_kernel.infrastructure.external_ai.embedding_adapter import LiteLLMEmbeddingAdapter
from src.shared_kernel.infrastructure.external_ai.litellm_adapter import (
    LiteLLMAdapter,
)
from src.shared_kernel.infrastructure.outbox.repository import SqlAlchemyOutboxRepository
from src.shared_kernel.infrastructure.workflow.repository import SqlAlchemyWorkflowRepository

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


def get_schedule_block_repository(
    session: AsyncSession = Depends(get_planning_db_session),
) -> ScheduleBlockRepositoryPort:
    return SqlAlchemyScheduleBlockRepository(session)


def get_knowledge_base_repository(
    session: AsyncSession = Depends(get_planning_db_session),
) -> KnowledgeBasePort:
    return SqlAlchemyKnowledgeBaseRepository(session)


def get_knowledge_source_repository(
    session: AsyncSession = Depends(get_planning_db_session),
) -> KnowledgeSourceRepositoryPort:
    return SqlAlchemyKnowledgeSourceRepository(session)


def get_knowledge_file_store() -> LocalKnowledgeFileStore:
    return LocalKnowledgeFileStore(get_settings().knowledge_upload_dir)


def get_create_knowledge_source_use_case(
    goal_repository: GoalRepositoryPort = Depends(get_goal_repository),
    source_repository: KnowledgeSourceRepositoryPort = Depends(get_knowledge_source_repository),
    file_store: LocalKnowledgeFileStore = Depends(get_knowledge_file_store),
    uow: AsyncUnitOfWork = Depends(get_planning_uow),
) -> CreateKnowledgeSourceUseCase:
    settings = get_settings()
    return CreateKnowledgeSourceUseCase(
        goal_repository=goal_repository,
        source_repository=source_repository,
        file_store=file_store,
        uow=uow,
        max_file_bytes=settings.knowledge_file_max_bytes,
        docx_max_entries=settings.knowledge_docx_max_entries,
        docx_max_uncompressed_bytes=settings.knowledge_docx_max_uncompressed_bytes,
        docx_max_compression_ratio=settings.knowledge_docx_max_compression_ratio,
    )


def get_planning_embedding_provider() -> EmbeddingProviderPort:
    return LiteLLMEmbeddingAdapter()


def get_ingest_knowledge_source_use_case(
    source_repository: KnowledgeSourceRepositoryPort = Depends(get_knowledge_source_repository),
    file_store: LocalKnowledgeFileStore = Depends(get_knowledge_file_store),
    embedding_provider: EmbeddingProviderPort = Depends(get_planning_embedding_provider),
    uow: AsyncUnitOfWork = Depends(get_planning_uow),
) -> IngestKnowledgeSourceUseCase:
    settings = get_settings()
    return IngestKnowledgeSourceUseCase(
        source_repository=source_repository,
        file_store=file_store,
        embedding_provider=embedding_provider,
        url_fetcher=SafeUrlFetcher(
            max_bytes=settings.knowledge_url_max_bytes,
            timeout_seconds=settings.knowledge_url_timeout_seconds,
        ),
        extractor=DocumentExtractor(
            max_file_bytes=settings.knowledge_file_max_bytes,
            max_extracted_chars=settings.knowledge_max_extracted_chars,
            pdf_max_pages=settings.knowledge_pdf_max_pages,
            docx_max_entries=settings.knowledge_docx_max_entries,
            docx_max_uncompressed_bytes=settings.knowledge_docx_max_uncompressed_bytes,
            docx_max_compression_ratio=settings.knowledge_docx_max_compression_ratio,
        ),
        chunker=SemanticChunker(),
        uow=uow,
    )


# --- Cross-Context & Shared Kernel Port Dependencies ---
def get_planning_quota_facade(
    session: AsyncSession = Depends(get_planning_db_session),
) -> QuotaFacadePort:
    return create_quota_facade(session)


def get_planning_availability_query_port(
    session: AsyncSession = Depends(get_planning_db_session),
) -> AvailabilityQueryPort:
    return create_availability_query_port(session)


def get_planning_calendar_connection_query_port(
    session: AsyncSession = Depends(get_planning_db_session),
) -> CalendarConnectionQueryPort:
    return create_calendar_connection_query_port(session)


def get_planning_calendar_sync_facade(
    session: AsyncSession = Depends(get_planning_db_session),
) -> CalendarSyncFacadePort:
    return create_calendar_sync_facade(session)


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


def get_planning_pause_record_port(
    session: AsyncSession = Depends(get_planning_db_session),
) -> PauseRecordPort:
    return create_pause_record_port(session)


def get_planning_learner_memory_port(
    session: AsyncSession = Depends(get_planning_db_session),
) -> LearnerMemoryQueryPort:
    return create_learner_memory_query_port(session)


def get_planning_workflow_repository(
    session: AsyncSession = Depends(get_planning_db_session),
) -> WorkflowRepositoryPort:
    return SqlAlchemyWorkflowRepository(session)


def get_planning_outbox_repository(
    session: AsyncSession = Depends(get_planning_db_session),
) -> OutboxRepositoryPort:
    return SqlAlchemyOutboxRepository(session)


def get_llm_provider() -> LLMProviderPort:
    provider: LLMProviderPort = LiteLLMAdapter()
    settings = get_settings()
    if not settings.ai_circuit_breaker_enabled:
        return provider
    return wrap_with_circuit_breaker(provider, provider_name="litellm")


def get_sse_job_store() -> SseJobPort:
    return default_redis_sse_job_store


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
    uow: AsyncUnitOfWork = Depends(get_planning_uow),
    learner_memory_port: LearnerMemoryQueryPort = Depends(get_planning_learner_memory_port),
    knowledge_source_repo: KnowledgeSourceRepositoryPort = Depends(get_knowledge_source_repository),
    embedding_provider: EmbeddingProviderPort = Depends(get_planning_embedding_provider),
    workflow_repo: WorkflowRepositoryPort = Depends(get_planning_workflow_repository),
    availability_query_port: AvailabilityQueryPort = Depends(get_planning_availability_query_port),
) -> GenerateClarificationQuestionsUseCase:
    return GenerateClarificationQuestionsUseCase(
        goal_repo=goal_repo,
        quota_facade=quota_facade,
        llm_provider=llm_provider,
        uow=uow,
        learner_memory_port=learner_memory_port,
        knowledge_source_repo=knowledge_source_repo,
        embedding_provider=embedding_provider,
        workflow_repo=workflow_repo,
        availability_query_port=availability_query_port,
        v2_enabled=get_settings().clarification_engine_v2_enabled,
    )


def get_submit_clarification_answers_use_case(
    goal_repo: GoalRepositoryPort = Depends(get_goal_repository),
    uow: AsyncUnitOfWork = Depends(get_planning_uow),
    workflow_repo: WorkflowRepositoryPort = Depends(get_planning_workflow_repository),
    quota_facade: QuotaFacadePort = Depends(get_planning_quota_facade),
    llm_provider: LLMProviderPort = Depends(get_llm_provider),
) -> SubmitClarificationAnswersUseCase:
    return SubmitClarificationAnswersUseCase(
        goal_repo=goal_repo,
        uow=uow,
        workflow_repo=workflow_repo,
        quota_facade=quota_facade,
        llm_provider=llm_provider,
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
    learner_memory_port: LearnerMemoryQueryPort | None = Depends(get_planning_learner_memory_port),
    knowledge_source_repo: KnowledgeSourceRepositoryPort | None = Depends(
        get_knowledge_source_repository
    ),
    embedding_provider: EmbeddingProviderPort | None = Depends(get_planning_embedding_provider),
    workflow_repo: WorkflowRepositoryPort | None = Depends(get_planning_workflow_repository),
    availability_query_port: AvailabilityQueryPort | None = Depends(
        get_planning_availability_query_port
    ),
    execution_sync_port: ExecutionScheduleSyncPort | None = Depends(
        get_planning_execution_sync_port
    ),
    block_repo: ScheduleBlockRepositoryPort | None = Depends(get_schedule_block_repository),
    user_query_port: UserQueryPort | None = Depends(get_planning_user_query_port),
    calendar_connection_query_port: CalendarConnectionQueryPort | None = Depends(
        get_planning_calendar_connection_query_port
    ),
    proposal_repo: ScheduleProposalRepositoryPort | None = Depends(
        get_schedule_proposal_repository
    ),
) -> ExecuteMilestoneGenerationUseCase:
    effective_kb = knowledge_base if isinstance(knowledge_base, KnowledgeBasePort) else None
    effective_cal = (
        calendar_connection_query_port
        if isinstance(calendar_connection_query_port, CalendarConnectionQueryPort)
        else None
    )
    effective_prop_repo = (
        proposal_repo if hasattr(proposal_repo, "discard_existing_drafts") else None
    )
    return ExecuteMilestoneGenerationUseCase(
        goal_repo=goal_repo,
        roadmap_repo=roadmap_repo,
        milestone_repo=milestone_repo,
        quota_facade=quota_facade,
        llm_provider=llm_provider,
        sse_job_store=sse_job_store,
        uow=uow,
        knowledge_base=effective_kb,
        learner_memory_port=learner_memory_port,
        knowledge_source_repo=knowledge_source_repo,
        embedding_provider=embedding_provider,
        workflow_repo=workflow_repo,
        availability_query_port=availability_query_port,
        execution_sync_port=execution_sync_port,
        block_repo=block_repo,
        user_query_port=user_query_port,
        calendar_connection_query_port=effective_cal,
        proposal_repo=effective_prop_repo,
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
    goal_repo: GoalRepositoryPort = Depends(get_goal_repository),
    proposal_repo: ScheduleProposalRepositoryPort = Depends(get_schedule_proposal_repository),
    availability_query_port: AvailabilityQueryPort = Depends(get_planning_availability_query_port),
    execution_sync_port: ExecutionScheduleSyncPort = Depends(get_planning_execution_sync_port),
    user_query_port: UserQueryPort = Depends(get_planning_user_query_port),
    block_repo: ScheduleBlockRepositoryPort = Depends(get_schedule_block_repository),
    calendar_connection_query_port: CalendarConnectionQueryPort | None = Depends(
        get_planning_calendar_connection_query_port
    ),
) -> UpdateMilestonesUseCase:
    effective_cal = (
        calendar_connection_query_port
        if isinstance(calendar_connection_query_port, CalendarConnectionQueryPort)
        else None
    )
    return UpdateMilestonesUseCase(
        roadmap_repo=roadmap_repo,
        milestone_repo=milestone_repo,
        uow=uow,
        goal_repo=goal_repo,
        proposal_repo=proposal_repo,
        availability_query_port=availability_query_port,
        execution_sync_port=execution_sync_port,
        user_query_port=user_query_port,
        block_repo=block_repo,
        calendar_connection_query_port=effective_cal,
    )


def get_approve_milestones_use_case(
    roadmap_repo: RoadmapRepositoryPort = Depends(get_roadmap_repository),
    milestone_repo: MilestoneRepositoryPort = Depends(get_milestone_repository),
    uow: AsyncUnitOfWork = Depends(get_planning_uow),
    goal_repo: GoalRepositoryPort = Depends(get_goal_repository),
    proposal_repo: ScheduleProposalRepositoryPort = Depends(get_schedule_proposal_repository),
    availability_query_port: AvailabilityQueryPort = Depends(get_planning_availability_query_port),
    execution_sync_port: ExecutionScheduleSyncPort = Depends(get_planning_execution_sync_port),
    user_query_port: UserQueryPort = Depends(get_planning_user_query_port),
    block_repo: ScheduleBlockRepositoryPort = Depends(get_schedule_block_repository),
    calendar_connection_query_port: CalendarConnectionQueryPort | None = Depends(
        get_planning_calendar_connection_query_port
    ),
) -> ApproveMilestonesUseCase:
    effective_cal = (
        calendar_connection_query_port
        if isinstance(calendar_connection_query_port, CalendarConnectionQueryPort)
        else None
    )
    return ApproveMilestonesUseCase(
        roadmap_repo=roadmap_repo,
        milestone_repo=milestone_repo,
        uow=uow,
        goal_repo=goal_repo,
        proposal_repo=proposal_repo,
        availability_query_port=availability_query_port,
        execution_sync_port=execution_sync_port,
        user_query_port=user_query_port,
        block_repo=block_repo,
        calendar_connection_query_port=effective_cal,
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
    user_query_port: UserQueryPort = Depends(get_planning_user_query_port),
    block_repo: ScheduleBlockRepositoryPort = Depends(get_schedule_block_repository),
    learner_memory_port: LearnerMemoryQueryPort | None = Depends(get_planning_learner_memory_port),
    knowledge_source_repo: KnowledgeSourceRepositoryPort | None = Depends(
        get_knowledge_source_repository
    ),
    embedding_provider: EmbeddingProviderPort | None = Depends(get_planning_embedding_provider),
    workflow_repo: WorkflowRepositoryPort | None = Depends(get_planning_workflow_repository),
    calendar_connection_query_port: CalendarConnectionQueryPort | None = Depends(
        get_planning_calendar_connection_query_port
    ),
) -> ExecuteScheduleProposalGenerationUseCase:
    effective_kb = knowledge_base if isinstance(knowledge_base, KnowledgeBasePort) else None
    effective_cal = (
        calendar_connection_query_port
        if isinstance(calendar_connection_query_port, CalendarConnectionQueryPort)
        else None
    )
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
        user_query_port=user_query_port,
        block_repo=block_repo,
        learner_memory_port=learner_memory_port,
        knowledge_source_repo=knowledge_source_repo,
        embedding_provider=embedding_provider,
        workflow_repo=workflow_repo,
        calendar_connection_query_port=effective_cal,
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
    goal_repo: GoalRepositoryPort = Depends(get_goal_repository),
    proposal_repo: ScheduleProposalRepositoryPort = Depends(get_schedule_proposal_repository),
    availability_query_port: AvailabilityQueryPort = Depends(get_planning_availability_query_port),
    execution_sync_port: ExecutionScheduleSyncPort = Depends(get_planning_execution_sync_port),
    user_query_port: UserQueryPort = Depends(get_planning_user_query_port),
    block_repo: ScheduleBlockRepositoryPort = Depends(get_schedule_block_repository),
    calendar_connection_query_port: CalendarConnectionQueryPort | None = Depends(
        get_planning_calendar_connection_query_port
    ),
) -> InitiateScheduleProposalGenerationUseCase:
    effective_cal = (
        calendar_connection_query_port
        if isinstance(calendar_connection_query_port, CalendarConnectionQueryPort)
        else None
    )
    return InitiateScheduleProposalGenerationUseCase(
        roadmap_repo=roadmap_repo,
        milestone_repo=milestone_repo,
        quota_facade=quota_facade,
        sse_job_store=sse_job_store,
        uow=uow,
        executor=executor,
        goal_repo=goal_repo,
        proposal_repo=proposal_repo,
        availability_query_port=availability_query_port,
        execution_sync_port=execution_sync_port,
        user_query_port=user_query_port,
        block_repo=block_repo,
        calendar_connection_query_port=effective_cal,
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
    user_query_port: UserQueryPort = Depends(get_planning_user_query_port),
    block_repo: ScheduleBlockRepositoryPort = Depends(get_schedule_block_repository),
    calendar_connection_query_port: CalendarConnectionQueryPort | None = Depends(
        get_planning_calendar_connection_query_port
    ),
    goal_repo: GoalRepositoryPort = Depends(get_goal_repository),
) -> UpdateScheduleProposalUseCase:
    effective_cal = (
        calendar_connection_query_port
        if isinstance(calendar_connection_query_port, CalendarConnectionQueryPort)
        else None
    )
    return UpdateScheduleProposalUseCase(
        roadmap_repo=roadmap_repo,
        milestone_repo=milestone_repo,
        proposal_repo=proposal_repo,
        availability_query_port=availability_query_port,
        execution_sync_port=execution_sync_port,
        uow=uow,
        user_query_port=user_query_port,
        block_repo=block_repo,
        calendar_connection_query_port=effective_cal,
        goal_repo=goal_repo,
    )


def get_apply_schedule_proposal_use_case(
    roadmap_repo: RoadmapRepositoryPort = Depends(get_roadmap_repository),
    milestone_repo: MilestoneRepositoryPort = Depends(get_milestone_repository),
    proposal_repo: ScheduleProposalRepositoryPort = Depends(get_schedule_proposal_repository),
    schedule_repo: OfficialScheduleRepositoryPort = Depends(get_official_schedule_repository),
    block_repo: ScheduleBlockRepositoryPort = Depends(get_schedule_block_repository),
    availability_query_port: AvailabilityQueryPort = Depends(get_planning_availability_query_port),
    execution_sync_port: ExecutionScheduleSyncPort = Depends(get_planning_execution_sync_port),
    schedule_change_log_port: ScheduleChangeLogPort = Depends(
        get_planning_schedule_change_log_port
    ),
    uow: AsyncUnitOfWork = Depends(get_planning_uow),
    user_query_port: UserQueryPort = Depends(get_planning_user_query_port),
    calendar_connection_query_port: CalendarConnectionQueryPort | None = Depends(
        get_planning_calendar_connection_query_port
    ),
    calendar_sync_facade: CalendarSyncFacadePort | None = Depends(
        get_planning_calendar_sync_facade
    ),
    goal_repo: GoalRepositoryPort = Depends(get_goal_repository),
) -> ApplyScheduleProposalUseCase:
    effective_cal = (
        calendar_connection_query_port
        if isinstance(calendar_connection_query_port, CalendarConnectionQueryPort)
        else None
    )
    effective_sync = (
        calendar_sync_facade if isinstance(calendar_sync_facade, CalendarSyncFacadePort) else None
    )
    return ApplyScheduleProposalUseCase(
        roadmap_repo=roadmap_repo,
        milestone_repo=milestone_repo,
        proposal_repo=proposal_repo,
        schedule_repo=schedule_repo,
        block_repo=block_repo,
        availability_query_port=availability_query_port,
        execution_sync_port=execution_sync_port,
        schedule_change_log_port=schedule_change_log_port,
        uow=uow,
        user_query_port=user_query_port,
        calendar_connection_query_port=effective_cal,
        calendar_sync_facade=effective_sync,
        goal_repo=goal_repo,
    )


def get_save_manual_roadmap_plan_use_case(
    goal_repo: GoalRepositoryPort = Depends(get_goal_repository),
    roadmap_repo: RoadmapRepositoryPort = Depends(get_roadmap_repository),
    milestone_repo: MilestoneRepositoryPort = Depends(get_milestone_repository),
    proposal_repo: ScheduleProposalRepositoryPort = Depends(get_schedule_proposal_repository),
    availability_query_port: AvailabilityQueryPort = Depends(get_planning_availability_query_port),
    execution_sync_port: ExecutionScheduleSyncPort = Depends(get_planning_execution_sync_port),
    uow: AsyncUnitOfWork = Depends(get_planning_uow),
    user_query_port: UserQueryPort = Depends(get_planning_user_query_port),
    block_repo: ScheduleBlockRepositoryPort = Depends(get_schedule_block_repository),
    calendar_connection_query_port: CalendarConnectionQueryPort | None = Depends(
        get_planning_calendar_connection_query_port
    ),
) -> SaveManualRoadmapPlanUseCase:
    effective_cal = (
        calendar_connection_query_port
        if isinstance(calendar_connection_query_port, CalendarConnectionQueryPort)
        else None
    )
    return SaveManualRoadmapPlanUseCase(
        goal_repo=goal_repo,
        roadmap_repo=roadmap_repo,
        milestone_repo=milestone_repo,
        proposal_repo=proposal_repo,
        availability_query_port=availability_query_port,
        execution_sync_port=execution_sync_port,
        uow=uow,
        user_query_port=user_query_port,
        block_repo=block_repo,
        calendar_connection_query_port=effective_cal,
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
    milestone_repo: MilestoneRepositoryPort = Depends(get_milestone_repository),
    proposal_repo: ScheduleProposalRepositoryPort = Depends(get_schedule_proposal_repository),
    availability_query_port: AvailabilityQueryPort = Depends(get_planning_availability_query_port),
    execution_sync_port: ExecutionScheduleSyncPort = Depends(get_planning_execution_sync_port),
    block_repo: ScheduleBlockRepositoryPort = Depends(get_schedule_block_repository),
    calendar_connection_query_port: CalendarConnectionQueryPort | None = Depends(
        get_planning_calendar_connection_query_port
    ),
) -> UpdateRoadmapUseCase:
    effective_cal = (
        calendar_connection_query_port
        if isinstance(calendar_connection_query_port, CalendarConnectionQueryPort)
        else None
    )
    return UpdateRoadmapUseCase(
        goal_repo=goal_repo,
        roadmap_repo=roadmap_repo,
        uow=uow,
        user_query_port=user_query_port,
        milestone_repo=milestone_repo,
        proposal_repo=proposal_repo,
        availability_query_port=availability_query_port,
        execution_sync_port=execution_sync_port,
        block_repo=block_repo,
        calendar_connection_query_port=effective_cal,
    )


def get_handle_availability_updated_event_use_case(
    roadmap_repo: RoadmapRepositoryPort = Depends(get_roadmap_repository),
    milestone_repo: MilestoneRepositoryPort = Depends(get_milestone_repository),
    proposal_repo: ScheduleProposalRepositoryPort = Depends(get_schedule_proposal_repository),
    availability_query_port: AvailabilityQueryPort = Depends(get_planning_availability_query_port),
    outbox_repo: OutboxRepositoryPort = Depends(get_planning_outbox_repository),
    uow: AsyncUnitOfWork = Depends(get_planning_uow),
    goal_repo: GoalRepositoryPort = Depends(get_goal_repository),
    execution_sync_port: ExecutionScheduleSyncPort = Depends(get_planning_execution_sync_port),
    block_repo: ScheduleBlockRepositoryPort = Depends(get_schedule_block_repository),
    user_query_port: UserQueryPort = Depends(get_planning_user_query_port),
    calendar_connection_query_port: CalendarConnectionQueryPort | None = Depends(
        get_planning_calendar_connection_query_port
    ),
) -> HandleAvailabilityUpdatedEventUseCase:
    effective_cal = (
        calendar_connection_query_port
        if isinstance(calendar_connection_query_port, CalendarConnectionQueryPort)
        else None
    )
    return HandleAvailabilityUpdatedEventUseCase(
        roadmap_repo=roadmap_repo,
        milestone_repo=milestone_repo,
        proposal_repo=proposal_repo,
        availability_query_port=availability_query_port,
        outbox_repo=outbox_repo,
        uow=uow,
        goal_repo=goal_repo,
        execution_sync_port=execution_sync_port,
        block_repo=block_repo,
        user_query_port=user_query_port,
        calendar_connection_query_port=effective_cal,
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


def get_pause_roadmap_use_case(
    roadmap_repo: RoadmapRepositoryPort = Depends(get_roadmap_repository),
    schedule_repo: OfficialScheduleRepositoryPort = Depends(get_official_schedule_repository),
    uow: AsyncUnitOfWork = Depends(get_planning_uow),
    schedule_change_log_port: ScheduleChangeLogPort = Depends(
        get_planning_schedule_change_log_port
    ),
    pause_record_port: PauseRecordPort = Depends(get_planning_pause_record_port),
) -> PauseRoadmapUseCase:
    return PauseRoadmapUseCase(
        roadmap_repo=roadmap_repo,
        schedule_repo=schedule_repo,
        uow=uow,
        schedule_change_log_port=schedule_change_log_port,
        pause_record_port=pause_record_port,
    )


def get_resume_roadmap_use_case(
    goal_repo: GoalRepositoryPort = Depends(get_goal_repository),
    roadmap_repo: RoadmapRepositoryPort = Depends(get_roadmap_repository),
    schedule_repo: OfficialScheduleRepositoryPort = Depends(get_official_schedule_repository),
    uow: AsyncUnitOfWork = Depends(get_planning_uow),
    execution_sync_port: ExecutionScheduleSyncPort = Depends(get_planning_execution_sync_port),
    block_repo: ScheduleBlockRepositoryPort = Depends(get_schedule_block_repository),
    user_query_port: UserQueryPort = Depends(get_planning_user_query_port),
    schedule_change_log_port: ScheduleChangeLogPort = Depends(
        get_planning_schedule_change_log_port
    ),
    pause_record_port: PauseRecordPort = Depends(get_planning_pause_record_port),
) -> ResumeRoadmapUseCase:
    return ResumeRoadmapUseCase(
        goal_repo=goal_repo,
        roadmap_repo=roadmap_repo,
        schedule_repo=schedule_repo,
        uow=uow,
        execution_sync_port=execution_sync_port,
        block_repo=block_repo,
        user_query_port=user_query_port,
        schedule_change_log_port=schedule_change_log_port,
        pause_record_port=pause_record_port,
    )


def get_reoptimize_schedule_proposal_use_case(
    roadmap_repo: RoadmapRepositoryPort = Depends(get_roadmap_repository),
    milestone_repo: MilestoneRepositoryPort = Depends(get_milestone_repository),
    proposal_repo: ScheduleProposalRepositoryPort = Depends(get_schedule_proposal_repository),
    availability_query_port: AvailabilityQueryPort = Depends(get_planning_availability_query_port),
    execution_sync_port: ExecutionScheduleSyncPort = Depends(get_planning_execution_sync_port),
    uow: AsyncUnitOfWork = Depends(get_planning_uow),
    learner_profile_port: LearnerProfileQueryPort = Depends(get_planning_learner_profile_port),
    user_query_port: UserQueryPort = Depends(get_planning_user_query_port),
    block_repo: ScheduleBlockRepositoryPort = Depends(get_schedule_block_repository),
    schedule_repo: OfficialScheduleRepositoryPort = Depends(get_official_schedule_repository),
    calendar_connection_query_port: CalendarConnectionQueryPort | None = Depends(
        get_planning_calendar_connection_query_port
    ),
) -> ReoptimizeScheduleProposalUseCase:
    effective_cal = (
        calendar_connection_query_port
        if isinstance(calendar_connection_query_port, CalendarConnectionQueryPort)
        else None
    )
    return ReoptimizeScheduleProposalUseCase(
        roadmap_repo=roadmap_repo,
        milestone_repo=milestone_repo,
        proposal_repo=proposal_repo,
        availability_query_port=availability_query_port,
        execution_sync_port=execution_sync_port,
        uow=uow,
        learner_profile_port=learner_profile_port,
        user_query_port=user_query_port,
        block_repo=block_repo,
        calendar_connection_query_port=effective_cal,
        schedule_repo=schedule_repo,
    )


def get_initiate_overdue_recovery_use_case(
    roadmap_repo: RoadmapRepositoryPort = Depends(get_roadmap_repository),
    milestone_repo: MilestoneRepositoryPort = Depends(get_milestone_repository),
    proposal_repo: ScheduleProposalRepositoryPort = Depends(get_schedule_proposal_repository),
    availability_query_port: AvailabilityQueryPort = Depends(get_planning_availability_query_port),
    execution_sync_port: ExecutionScheduleSyncPort = Depends(get_planning_execution_sync_port),
    sse_job_store: SseJobPort = Depends(get_sse_job_store),
    uow: AsyncUnitOfWork = Depends(get_planning_uow),
    learner_profile_port: LearnerProfileQueryPort = Depends(get_planning_learner_profile_port),
    user_query_port: UserQueryPort = Depends(get_planning_user_query_port),
    block_repo: ScheduleBlockRepositoryPort = Depends(get_schedule_block_repository),
    schedule_repo: OfficialScheduleRepositoryPort = Depends(get_official_schedule_repository),
    calendar_connection_query_port: CalendarConnectionQueryPort | None = Depends(
        get_planning_calendar_connection_query_port
    ),
) -> InitiateOverdueRecoveryUseCase:
    effective_cal = (
        calendar_connection_query_port
        if isinstance(calendar_connection_query_port, CalendarConnectionQueryPort)
        else None
    )
    return InitiateOverdueRecoveryUseCase(
        roadmap_repo=roadmap_repo,
        milestone_repo=milestone_repo,
        proposal_repo=proposal_repo,
        availability_query_port=availability_query_port,
        execution_sync_port=execution_sync_port,
        sse_job_store=sse_job_store,
        uow=uow,
        learner_profile_port=learner_profile_port,
        user_query_port=user_query_port,
        block_repo=block_repo,
        calendar_connection_query_port=effective_cal,
        schedule_repo=schedule_repo,
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
PauseRoadmapUseCaseDep = Annotated[PauseRoadmapUseCase, Depends(get_pause_roadmap_use_case)]
ResumeRoadmapUseCaseDep = Annotated[ResumeRoadmapUseCase, Depends(get_resume_roadmap_use_case)]
ReoptimizeScheduleProposalUseCaseDep = Annotated[
    ReoptimizeScheduleProposalUseCase, Depends(get_reoptimize_schedule_proposal_use_case)
]
InitiateOverdueRecoveryUseCaseDep = Annotated[
    InitiateOverdueRecoveryUseCase, Depends(get_initiate_overdue_recovery_use_case)
]
GenerateClarificationQuestionsUseCaseDep = Annotated[
    GenerateClarificationQuestionsUseCase,
    Depends(get_generate_clarification_questions_use_case),
]
SubmitClarificationAnswersUseCaseDep = Annotated[
    SubmitClarificationAnswersUseCase,
    Depends(get_submit_clarification_answers_use_case),
]
CreateKnowledgeSourceUseCaseDep = Annotated[
    CreateKnowledgeSourceUseCase, Depends(get_create_knowledge_source_use_case)
]
KnowledgeSourceRepositoryDep = Annotated[
    KnowledgeSourceRepositoryPort, Depends(get_knowledge_source_repository)
]
GoalRepositoryDep = Annotated[GoalRepositoryPort, Depends(get_goal_repository)]
RoadmapRepositoryDep = Annotated[RoadmapRepositoryPort, Depends(get_roadmap_repository)]
