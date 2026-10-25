from src.shared_kernel.infrastructure.worker.broker import broker


@broker.task(schedule=[{"cron": "* * * * *"}])
async def sweep_expired_ai_quota_reservations() -> int:
    """Sweep RESERVED AI quota locks older than expires_at and refund credits (ADR-003)."""
    return 0


@broker.task
async def aggregate_learner_srl_profile(user_id: str) -> None:
    """Recalculate LearnerProfile SRL metrics upon StudySessionCompletedEvent."""
    return None
