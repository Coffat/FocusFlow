from uuid import UUID

from src.planning.presentation.deps import (
    get_execute_milestone_generation_use_case,
    get_execute_schedule_proposal_generation_use_case,
    get_goal_repository,
    get_knowledge_base_repository,
    get_llm_provider,
    get_milestone_repository,
    get_planning_availability_query_port,
    get_planning_execution_sync_port,
    get_planning_learner_profile_port,
    get_planning_quota_facade,
    get_planning_uow,
    get_roadmap_repository,
    get_schedule_proposal_repository,
    get_sse_job_store,
)
from src.shared_kernel.infrastructure.database.session import async_session_factory
from src.shared_kernel.infrastructure.worker.broker import broker


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
        llm_provider = get_llm_provider()
        sse_store = get_sse_job_store()
        knowledge_base = get_knowledge_base_repository(session)

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
            )
            await prop_uc.execute(
                job_id=UUID(job_id),
                user_id=UUID(user_id),
                roadmap_id=UUID(roadmap_id),
                reservation_id=UUID(reservation_id),
            )
