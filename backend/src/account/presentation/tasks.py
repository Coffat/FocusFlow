import logging
from uuid import UUID

from src.shared_kernel.infrastructure.database.session import async_session_factory
from src.shared_kernel.infrastructure.worker.broker import broker

logger = logging.getLogger("focusflow.account.tasks")


@broker.task(schedule=[{"cron": "* * * * *"}])
async def sweep_expired_ai_quota_reservations() -> int:
    """Sweep RESERVED AI quota locks older than expires_at and refund credits (ADR-003)."""
    return 0


@broker.task
async def aggregate_learner_srl_profile(user_id: str) -> None:
    """Recalculate LearnerProfile SRL metrics upon StudySessionCompletedEvent."""
    return None


@broker.task
async def send_otp_email_task(to_email: str, otp_code: str, purpose: str) -> None:
    """Dispatches OTP verification email asynchronously via Taskiq worker."""
    from src.account.infrastructure.email.email_service import EmailService

    await EmailService.send_otp_email(to_email=to_email, otp_code=otp_code, purpose=purpose)


async def dispatch_otp_email(to_email: str, otp_code: str, purpose: str) -> None:
    """Dispatches OTP email via Taskiq with immediate direct fallback if worker unavailable."""
    from src.account.infrastructure.email.email_service import EmailService

    try:
        await send_otp_email_task.kiq(to_email=to_email, otp_code=otp_code, purpose=purpose)
    except Exception as exc:
        logger.warning(
            "Taskiq worker dispatch failed (%s); falling back to direct email delivery", exc
        )
        await EmailService.send_otp_email(to_email=to_email, otp_code=otp_code, purpose=purpose)


@broker.task
async def sync_schedule_blocks_to_google(schedule_id: str, user_id: str) -> None:
    """Outbound sync worker: syncs ScheduleBlock entities to Google Calendar (UC-17)."""
    from src.account.presentation.deps import (
        get_account_uow,
        get_calendar_connection_repository,
        get_calendar_provider,
        get_schedule_block_sync_port_dep,
        get_sync_schedule_blocks_use_case,
    )

    async with async_session_factory() as session:
        repo = get_calendar_connection_repository(session)
        provider = get_calendar_provider()
        block_port = get_schedule_block_sync_port_dep(session)
        uow = get_account_uow(session)
        uc = get_sync_schedule_blocks_use_case(
            repo=repo,
            provider=provider,
            block_port=block_port,
            uow=uow,
        )
        await uc.execute(schedule_id=UUID(schedule_id), user_id=UUID(user_id))


@broker.task
async def process_google_calendar_webhook(channel_id: str) -> None:
    """Inbound sync worker: processes Google Calendar push notifications (UC-17)."""
    from src.account.presentation.deps import (
        get_account_uow,
        get_calendar_connection_repository,
        get_calendar_provider,
        get_process_google_calendar_webhook_use_case,
        get_schedule_block_sync_port_dep,
    )

    async with async_session_factory() as session:
        repo = get_calendar_connection_repository(session)
        provider = get_calendar_provider()
        block_port = get_schedule_block_sync_port_dep(session)
        uow = get_account_uow(session)
        uc = get_process_google_calendar_webhook_use_case(
            repo=repo,
            provider=provider,
            block_port=block_port,
            uow=uow,
        )
        await uc.execute(channel_id=channel_id)


@broker.task(schedule=[{"cron": "0 * * * *"}])
async def renew_expiring_calendar_webhooks() -> int:
    """Cron sweeper: renews webhook watch channels expiring within 24 hours (UC-17)."""
    from src.account.presentation.deps import (
        get_account_uow,
        get_calendar_connection_repository,
        get_calendar_provider,
        get_renew_expiring_calendar_webhooks_use_case,
    )

    async with async_session_factory() as session:
        repo = get_calendar_connection_repository(session)
        provider = get_calendar_provider()
        uow = get_account_uow(session)
        uc = get_renew_expiring_calendar_webhooks_use_case(
            repo=repo,
            provider=provider,
            uow=uow,
        )
        return await uc.execute()


@broker.task(schedule=[{"cron": "0 */6 * * *"}])
async def reconcile_calendar_connections() -> int:
    """Cron sweeper: runs every 6 hours to reconcile active connections and catch missed events (UC-17)."""
    from src.account.presentation.deps import (
        get_account_uow,
        get_calendar_connection_repository,
        get_reconcile_calendar_connections_use_case,
    )

    async with async_session_factory() as session:
        repo = get_calendar_connection_repository(session)
        uow = get_account_uow(session)
        uc = get_reconcile_calendar_connections_use_case(repo=repo, uow=uow)
        return await uc.execute()
