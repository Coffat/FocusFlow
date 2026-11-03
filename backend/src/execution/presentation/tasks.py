from src.shared_kernel.infrastructure.worker.broker import broker


@broker.task(schedule=[{"cron": "* * * * *"}])
async def sweep_abandoned_study_sessions() -> int:
    """Sweep IN_PROGRESS study sessions without heartbeat for >5 minutes (ASR-05)."""
    return 0


@broker.task
async def sync_external_google_calendar(user_id: str) -> None:
    """Synchronize OfficialSchedule with Google Calendar OAuth2 (UC-13)."""
    return None
