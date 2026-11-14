import asyncio
import inspect
import logging
import time
from collections.abc import Callable
from typing import Any, cast
from uuid import UUID

from src.planning.presentation.deps import (
    get_execute_milestone_generation_use_case,
    get_execute_schedule_proposal_generation_use_case,
    get_goal_repository,
    get_ingest_knowledge_source_use_case,
    get_knowledge_base_repository,
    get_knowledge_file_store,
    get_knowledge_source_repository,
    get_llm_provider,
    get_milestone_repository,
    get_planning_availability_query_port,
    get_planning_embedding_provider,
    get_planning_execution_sync_port,
    get_planning_learner_memory_port,
    get_planning_learner_profile_port,
    get_planning_quota_facade,
    get_planning_uow,
    get_planning_user_query_port,
    get_planning_workflow_repository,
    get_roadmap_repository,
    get_schedule_block_repository,
    get_schedule_proposal_repository,
    get_sse_job_store,
)
from src.shared_kernel.infrastructure.database.session import async_session_factory
from src.shared_kernel.infrastructure.worker.broker import (
    broker,
    get_registered_dependency_overrides,
)

logger = logging.getLogger(__name__)
_broker_retry_after: float = 0.0


async def _resolve_dep[T](dep_fn: Callable[..., Any], default_factory: Callable[[], T]) -> T:
    override = get_registered_dependency_overrides().get(dep_fn)
    if override is not None:
        value = override()
        if inspect.isawaitable(value):
            return cast("T", await value)
        return cast("T", value)
    return default_factory()


@broker.task
async def execute_ai_roadmap_generation(
    job_id: str,
    reservation_id: str,
    user_id: str | None = None,
    roadmap_id: str | None = None,
    job_type: str = "SCHEDULE_PROPOSAL_GEN",
) -> None:
    """Taskiq background task calling the same Planning Use Case as inline execution (ADR-004/005)."""
    if not user_id or not roadmap_id:
        return

    async with async_session_factory() as session:
        uow = get_planning_uow(session)
        goal_repo = get_goal_repository(session)
        roadmap_repo = get_roadmap_repository(session)
        milestone_repo = get_milestone_repository(session)
        quota_facade = get_planning_quota_facade(session)
        llm_provider = await _resolve_dep(get_llm_provider, get_llm_provider)
        sse_store = await _resolve_dep(get_sse_job_store, get_sse_job_store)
        knowledge_base = get_knowledge_base_repository(session)
        learner_memory_port = get_planning_learner_memory_port(session)
        knowledge_source_repo = get_knowledge_source_repository(session)
        embedding_provider = await _resolve_dep(
            get_planning_embedding_provider,
            get_planning_embedding_provider,
        )
        workflow_repo = get_planning_workflow_repository(session)

        try:
            if job_type.upper() == "MILESTONE_GEN":
                ms_uc = get_execute_milestone_generation_use_case(
                    goal_repo=goal_repo,
                    roadmap_repo=roadmap_repo,
                    milestone_repo=milestone_repo,
                    quota_facade=quota_facade,
                    llm_provider=llm_provider,
                    sse_job_store=sse_store,
                    uow=uow,
                    knowledge_base=knowledge_base,
                    learner_memory_port=learner_memory_port,
                    knowledge_source_repo=knowledge_source_repo,
                    embedding_provider=embedding_provider,
                    workflow_repo=workflow_repo,
                )
                await ms_uc.execute(
                    job_id=UUID(job_id),
                    user_id=UUID(user_id),
                    roadmap_id=UUID(roadmap_id),
                    reservation_id=UUID(reservation_id),
                )
            else:
                proposal_repo = get_schedule_proposal_repository(session)
                avail_port = get_planning_availability_query_port(session)
                profile_port = get_planning_learner_profile_port(session)
                exec_sync_port = get_planning_execution_sync_port(session)
                user_query_port = get_planning_user_query_port(session)
                block_repo = get_schedule_block_repository(session)
                prop_uc = get_execute_schedule_proposal_generation_use_case(
                    goal_repo=goal_repo,
                    roadmap_repo=roadmap_repo,
                    milestone_repo=milestone_repo,
                    proposal_repo=proposal_repo,
                    availability_query_port=avail_port,
                    learner_profile_port=profile_port,
                    execution_sync_port=exec_sync_port,
                    quota_facade=quota_facade,
                    llm_provider=llm_provider,
                    sse_job_store=sse_store,
                    uow=uow,
                    knowledge_base=knowledge_base,
                    user_query_port=user_query_port,
                    block_repo=block_repo,
                    learner_memory_port=learner_memory_port,
                    knowledge_source_repo=knowledge_source_repo,
                    embedding_provider=embedding_provider,
                    workflow_repo=workflow_repo,
                )
                await prop_uc.execute(
                    job_id=UUID(job_id),
                    user_id=UUID(user_id),
                    roadmap_id=UUID(roadmap_id),
                    reservation_id=UUID(reservation_id),
                )
        except Exception as exc:
            logger.exception("Background AI roadmap generation failed for job %s", job_id)
            try:
                await sse_store.append_event(
                    job_id=UUID(job_id),
                    event="failed",
                    status="FAILED",
                    data={
                        "stage": "FAILED",
                        "progress": 0,
                        "code": "AI_GENERATION_FAILED",
                        "message": str(exc) or "AI generation background failure",
                    },
                )
            except Exception:
                pass


@broker.task
async def ingest_knowledge_source(source_id: str, user_id: str) -> None:
    """Run the same secure ingestion use case outside the request lifecycle."""
    async with async_session_factory() as session:
        embedding_provider = await _resolve_dep(
            get_planning_embedding_provider,
            get_planning_embedding_provider,
        )
        use_case = get_ingest_knowledge_source_use_case(
            source_repository=get_knowledge_source_repository(session),
            file_store=get_knowledge_file_store(),
            embedding_provider=embedding_provider,
            uow=get_planning_uow(session),
        )
        await use_case.execute(source_id=UUID(source_id), user_id=UUID(user_id))


async def dispatch_ai_roadmap_generation(
    *,
    job_id: str,
    reservation_id: str,
    user_id: str,
    roadmap_id: str,
    job_type: str,
) -> None:
    """Enqueue Taskiq job with bounded broker probe and direct fallback when broker unreachable."""
    global _broker_retry_after
    if time.monotonic() >= _broker_retry_after:
        try:
            await asyncio.wait_for(
                execute_ai_roadmap_generation.kiq(
                    job_id=job_id,
                    reservation_id=reservation_id,
                    user_id=user_id,
                    roadmap_id=roadmap_id,
                    job_type=job_type,
                ),
                timeout=0.5,
            )
            return
        except Exception as exc:
            _broker_retry_after = time.monotonic() + 30.0
            logger.warning(
                "Taskiq dispatch failed for roadmap job %s (%s); running direct execution fallback",
                job_id,
                exc,
            )
    await execute_ai_roadmap_generation(
        job_id=job_id,
        reservation_id=reservation_id,
        user_id=user_id,
        roadmap_id=roadmap_id,
        job_type=job_type,
    )


async def dispatch_ingest_knowledge_source(*, source_id: str, user_id: str) -> None:
    """Enqueue knowledge ingestion Taskiq job with direct fallback when broker unreachable."""
    global _broker_retry_after
    if time.monotonic() >= _broker_retry_after:
        try:
            await asyncio.wait_for(
                ingest_knowledge_source.kiq(source_id, user_id),
                timeout=0.5,
            )
            return
        except Exception as exc:
            _broker_retry_after = time.monotonic() + 30.0
            logger.warning(
                "Taskiq dispatch failed for knowledge source %s (%s); running inline ingestion",
                source_id,
                exc,
            )
    await ingest_knowledge_source(source_id=source_id, user_id=user_id)
