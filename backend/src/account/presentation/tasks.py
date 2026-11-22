import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from src.shared_kernel.infrastructure.database.session import async_session_factory
from src.shared_kernel.infrastructure.outbox.relay import register_outbox_handler
from src.shared_kernel.infrastructure.worker.broker import broker

logger = logging.getLogger("focusflow.account.tasks")


@broker.task(schedule=[{"cron": "* * * * *"}])
async def sweep_expired_ai_quota_reservations(
    session_factory: Any = None,
    now: datetime | None = None,
) -> int:
    """Sweep RESERVED AI quota locks older than expires_at and refund credits (ADR-003)."""
    from src.account.infrastructure.adapters.quota_facade_adapter import QuotaFacadeAdapter

    session_maker = session_factory or async_session_factory
    async with session_maker() as session:
        try:
            adapter = QuotaFacadeAdapter(session=session)
            expired_count = await adapter.expire_stale_reservations(now=now)
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    if expired_count > 0:
        logger.info("Swept %d expired AI quota reservation(s)", expired_count)
    return expired_count


@broker.task
async def aggregate_learner_srl_profile(
    user_id: str,
    event_id: str | None = None,
    session_factory: Any = None,
) -> bool:
    """Recalculate LearnerProfile SRL metrics upon StudySessionCompletedEvent (BE-MOCK-02)."""
    from src.account.application.use_cases.profile.aggregate_srl_profile_use_case import (
        AggregateSrlProfileUseCase,
    )
    from src.account.infrastructure.repositories.learner_profile_repository import (
        SqlAlchemyLearnerProfileRepository,
    )
    from src.account.infrastructure.repositories.user_repository import (
        SqlAlchemyUserRepository,
    )
    from src.execution.public_api import create_execution_dashboard_query_port
    from src.shared_kernel.infrastructure.database.sqlalchemy_uow import SqlAlchemyUnitOfWork
    from src.shared_kernel.infrastructure.outbox.repository import SqlAlchemyOutboxRepository

    handler_name = "account.aggregate_learner_srl_profile_worker"
    parsed_user_id = UUID(user_id)
    parsed_event_id = UUID(event_id) if event_id else None
    session_maker = session_factory or async_session_factory

    if parsed_event_id is not None:
        async with session_maker() as session:
            outbox_repo = SqlAlchemyOutboxRepository(session)
            if await outbox_repo.is_event_processed(parsed_event_id, handler_name):
                logger.info(
                    "SRL profile aggregation already processed for event_id=%s; skipping duplicate",
                    parsed_event_id,
                )
                return False

    async with session_maker() as session:
        use_case = AggregateSrlProfileUseCase(
            user_repo=SqlAlchemyUserRepository(session),
            learner_profile_repo=SqlAlchemyLearnerProfileRepository(session),
            execution_dashboard_port=create_execution_dashboard_query_port(session),
            uow=SqlAlchemyUnitOfWork(session),
        )
        await use_case.execute(parsed_user_id)

    if parsed_event_id is not None:
        async with session_maker() as session:
            outbox_repo = SqlAlchemyOutboxRepository(session)
            await outbox_repo.mark_event_processed(parsed_event_id, handler_name)
            await session.commit()

    return True


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


@broker.task
async def send_overdue_task_alert_email_task(
    email: str,
    overdue_task_titles: list[str],
    remaining_reschedule_budget: int,
    event_id: str | None = None,
    session_factory: Any = None,
) -> None:
    """Dispatches overdue tasks warning email asynchronously via Taskiq worker (UC-25, BUSR-23)."""
    from src.account.infrastructure.email.email_service import EmailService
    from src.shared_kernel.infrastructure.outbox.repository import SqlAlchemyOutboxRepository

    handler_name = "account.overdue_task_alert_email_worker"
    parsed_event_id = UUID(event_id) if event_id else None
    session_maker = session_factory or async_session_factory

    if parsed_event_id is not None:
        async with session_maker() as session:
            outbox_repo = SqlAlchemyOutboxRepository(session)
            if await outbox_repo.is_event_processed(parsed_event_id, handler_name):
                logger.info(
                    "Overdue alert email already processed for event_id=%s; skipping duplicate",
                    parsed_event_id,
                )
                return

    await EmailService.send_overdue_alert_email(
        to_email=email,
        overdue_task_titles=overdue_task_titles,
        remaining_reschedule_budget=remaining_reschedule_budget,
        raise_on_error=True,
    )

    if parsed_event_id is not None:
        async with session_maker() as session:
            outbox_repo = SqlAlchemyOutboxRepository(session)
            await outbox_repo.mark_event_processed(parsed_event_id, handler_name)
            await session.commit()


async def _handle_overdue_task_alert_event(event_id: UUID, payload: dict[str, Any]) -> None:
    email = str(payload.get("email") or "").strip()
    if not email:
        return
    raw_titles = payload.get("overdue_task_titles")
    titles = [str(t) for t in raw_titles] if isinstance(raw_titles, list) else []
    budget = int(payload.get("remaining_reschedule_budget", 0))
    await send_overdue_task_alert_email_task.kiq(
        email=email,
        overdue_task_titles=titles,
        remaining_reschedule_budget=budget,
        event_id=str(event_id),
    )


async def _handle_official_schedule_applied_event(event_id: UUID, payload: dict[str, Any]) -> None:
    _ = event_id
    schedule_id = payload.get("schedule_id")
    user_id = payload.get("user_id")
    if schedule_id and user_id:
        await sync_schedule_blocks_to_google.kiq(
            schedule_id=str(schedule_id),
            user_id=str(user_id),
        )


async def _handle_study_session_completed_event(event_id: UUID, payload: dict[str, Any]) -> None:
    user_id = payload.get("user_id")
    if user_id:
        await aggregate_learner_srl_profile.kiq(
            user_id=str(user_id),
            event_id=str(event_id),
        )


async def _persist_notification_from_outbox(
    *,
    user_id: UUID,
    event_id: UUID,
    notification_type: str,
    title: str,
    content: str,
    resource_url: str | None = None,
    session_factory: Any = None,
) -> None:
    from src.account.application.use_cases.notifications import PersistNotificationUseCase
    from src.account.infrastructure.repositories.notification_repository import (
        SqlAlchemyNotificationRepository,
    )
    from src.account.infrastructure.repositories.user_repository import (
        SqlAlchemyUserRepository,
    )
    from src.shared_kernel.infrastructure.database.sqlalchemy_uow import SqlAlchemyUnitOfWork

    session_maker = session_factory or async_session_factory
    async with session_maker() as session:
        if await SqlAlchemyUserRepository(session).find_by_id(user_id) is None:
            logger.info(
                "Skipping notification persistence for non-existent user_id=%s event_id=%s",
                user_id,
                event_id,
            )
            return
        use_case = PersistNotificationUseCase(
            notification_repo=SqlAlchemyNotificationRepository(session),
            uow=SqlAlchemyUnitOfWork(session),
        )
        await use_case.execute(
            user_id=user_id,
            event_id=event_id,
            notification_type=notification_type,
            title=title,
            content=content,
            resource_url=resource_url,
        )


async def _handle_persist_overdue_task_notification(
    event_id: UUID, payload: dict[str, Any]
) -> None:
    raw_user_id = payload.get("user_id")
    if not raw_user_id:
        return
    raw_titles = payload.get("overdue_task_titles")
    titles = [str(t) for t in raw_titles] if isinstance(raw_titles, list) else []
    if titles:
        preview = ", ".join(titles[:3])
        extra = f" và {len(titles) - 3} nhiệm vụ khác" if len(titles) > 3 else ""
        content = f"Bạn có {len(titles)} nhiệm vụ quá hạn cần xử lý: {preview}{extra}."
    else:
        content = "Bạn có nhiệm vụ học tập đã quá hạn cần xem xét và điều chỉnh."
    await _persist_notification_from_outbox(
        user_id=UUID(str(raw_user_id)),
        event_id=event_id,
        notification_type="OVERDUE_TASK",
        title="Nhiệm vụ quá hạn cần xử lý",
        content=content,
        resource_url="/tasks",
    )


async def _handle_persist_schedule_applied_notification(
    event_id: UUID, payload: dict[str, Any]
) -> None:
    raw_user_id = payload.get("user_id")
    if not raw_user_id:
        return
    await _persist_notification_from_outbox(
        user_id=UUID(str(raw_user_id)),
        event_id=event_id,
        notification_type="SCHEDULE_APPLIED",
        title="Lịch học chính thức đã được kích hoạt",
        content="Lịch học chính thức mới của bạn đã được áp dụng và sẵn sàng thực thi.",
        resource_url="/schedule",
    )


async def _handle_persist_session_completed_notification(
    event_id: UUID, payload: dict[str, Any]
) -> None:
    raw_user_id = payload.get("user_id")
    if not raw_user_id:
        return
    raw_secs = payload.get("actual_duration_seconds")
    minutes = max(1, int(raw_secs) // 60) if isinstance(raw_secs, (int, float)) else 0
    content = (
        f"Chúc mừng! Bạn vừa hoàn thành phiên học tập kéo dài {minutes} phút."
        if minutes > 0
        else "Chúc mừng! Bạn vừa hoàn thành một phiên học tập mới."
    )
    await _persist_notification_from_outbox(
        user_id=UUID(str(raw_user_id)),
        event_id=event_id,
        notification_type="SESSION_COMPLETED",
        title="Hoàn thành phiên học tập",
        content=content,
        resource_url="/analytics",
    )


register_outbox_handler(
    "OverdueTaskAlertEvent",
    "account.overdue_task_alert_email",
    _handle_overdue_task_alert_event,
)
register_outbox_handler(
    "OverdueTaskAlertEvent",
    "account.persist_overdue_task_notification",
    _handle_persist_overdue_task_notification,
)
register_outbox_handler(
    "OfficialScheduleAppliedEvent",
    "account.sync_schedule_blocks_to_google",
    _handle_official_schedule_applied_event,
)
register_outbox_handler(
    "OfficialScheduleAppliedEvent",
    "account.persist_schedule_applied_notification",
    _handle_persist_schedule_applied_notification,
)
register_outbox_handler(
    "StudySessionCompletedEvent",
    "account.aggregate_learner_srl_profile",
    _handle_study_session_completed_event,
)
register_outbox_handler(
    "StudySessionCompletedEvent",
    "account.persist_session_completed_notification",
    _handle_persist_session_completed_notification,
)
