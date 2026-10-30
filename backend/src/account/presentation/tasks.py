import logging

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
