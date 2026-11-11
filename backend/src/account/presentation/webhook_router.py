import hashlib
import hmac
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, status

from src.account.application.ports.calendar_connection_repository_port import (
    CalendarConnectionRepositoryPort,
)
from src.account.presentation.deps import get_calendar_connection_repository
from src.account.presentation.tasks import process_google_calendar_webhook

logger = logging.getLogger("focusflow.account.webhook")

router = APIRouter(prefix="/api/v1/calendar/webhooks", tags=["Calendar Webhooks (UC-17)"])


@router.post(
    "/google",
    status_code=status.HTTP_200_OK,
    summary="Receive Google Calendar push notifications via webhook",
)
async def handle_google_calendar_webhook(
    x_goog_channel_id: str | None = Header(None, alias="X-Goog-Channel-ID"),
    x_goog_resource_id: str | None = Header(None, alias="X-Goog-Resource-ID"),
    x_goog_channel_token: str | None = Header(None, alias="X-Goog-Channel-Token"),
    x_goog_resource_state: str | None = Header(None, alias="X-Goog-Resource-State"),
    repository: CalendarConnectionRepositoryPort = Depends(get_calendar_connection_repository),
) -> dict[str, str]:
    """Handle incoming Google Calendar push notifications with strict 3-header verification."""
    if not x_goog_channel_id or not x_goog_resource_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing required Google webhook headers (X-Goog-Channel-ID, X-Goog-Resource-ID).",
        )

    conn = await repository.get_by_channel_id(x_goog_channel_id)
    if conn is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unrecognized X-Goog-Channel-ID.",
        )

    if conn.resource_id != x_goog_resource_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="X-Goog-Resource-ID mismatch.",
        )

    if conn.channel_token_hash:
        if not x_goog_channel_token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Missing X-Goog-Channel-Token header.",
            )
        token_hash = hashlib.sha256(x_goog_channel_token.encode("utf-8")).hexdigest()
        if not hmac.compare_digest(token_hash, conn.channel_token_hash):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid X-Goog-Channel-Token verification hash.",
            )

    # Initial sync ping from Google
    if x_goog_resource_state == "sync":
        logger.info("Verified Google Calendar webhook channel: %s", x_goog_channel_id)
        return {"status": "ok", "message": "Channel verified."}

    # Enqueue background task
    try:
        await process_google_calendar_webhook.kiq(channel_id=x_goog_channel_id)
    except Exception as exc:
        logger.warning(
            "Taskiq dispatch failed (%s); running inline fallback for channel %s",
            exc,
            x_goog_channel_id,
        )
        try:
            await process_google_calendar_webhook(channel_id=x_goog_channel_id)
        except Exception as fallback_exc:
            logger.error("Inline webhook fallback also failed: %s", fallback_exc)

    return {"status": "accepted", "channel_id": x_goog_channel_id}
