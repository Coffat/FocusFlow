from uuid import UUID

from src.account.public_api import create_calendar_sync_facade
from src.shared_kernel.infrastructure.database.session import async_session_factory
from src.shared_kernel.infrastructure.worker.broker import broker


@broker.task(schedule=[{"cron": "* * * * *"}])
async def sweep_abandoned_study_sessions() -> int:
    """Sweep IN_PROGRESS study sessions without heartbeat for >5 minutes (ASR-05)."""
    return 0


@broker.task
async def sync_external_google_calendar(user_id: str) -> None:
    """Synchronize OfficialSchedule with Google Calendar OAuth2 (UC-13)."""
    return None


@broker.task
async def sync_schedule_blocks_to_google(schedule_id: str, user_id: str) -> None:
    """Outbound sync worker: syncs ScheduleBlock entities to Google Calendar (UC-17)."""
    async with async_session_factory() as session:
        facade = create_calendar_sync_facade(session)
        await facade.sync_schedule_blocks_to_google(
            schedule_id=UUID(schedule_id),
            user_id=UUID(user_id),
        )
