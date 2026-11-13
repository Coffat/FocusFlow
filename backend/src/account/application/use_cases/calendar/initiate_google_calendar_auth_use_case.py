import base64
import json
import secrets
from urllib.parse import urlencode
from uuid import UUID

from src.account.application.dtos.calendar import (
    InitiateCalendarAuthRequestDTO,
    InitiateCalendarAuthResponseDTO,
)
from src.shared_kernel.config import Settings, get_settings

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
INBOUND_SCOPES = [
    "https://www.googleapis.com/auth/calendar.calendarlist.readonly",
    "https://www.googleapis.com/auth/calendar.events.freebusy",
]
TWO_WAY_SCOPES = [
    *INBOUND_SCOPES,
    "https://www.googleapis.com/auth/calendar.app.created",
]


class InitiateGoogleCalendarAuthUseCase:
    """Generate OAuth2 authorization URL with progressive consent scopes (UC-17)."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    async def execute(
        self,
        user_id: UUID,
        request: InitiateCalendarAuthRequestDTO,
    ) -> InitiateCalendarAuthResponseDTO:
        sync_type = request.sync_type.lower()
        scopes = TWO_WAY_SCOPES if sync_type == "two_way" else INBOUND_SCOPES

        redirect_uri = request.redirect_uri or self._settings.google_redirect_uri

        # CSRF state encoding user_id, sync_type, random nonce, and redirect_uri
        csrf_token = secrets.token_urlsafe(16)
        state_payload = {
            "user_id": str(user_id),
            "sync_type": sync_type,
            "nonce": csrf_token,
            "redirect_uri": redirect_uri,
            "return_to": request.return_to or "/settings",
        }
        state_str = base64.urlsafe_b64encode(json.dumps(state_payload).encode("utf-8")).decode(
            "utf-8"
        )

        params = {
            "client_id": self._settings.google_client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes),
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
            "state": state_str,
        }

        auth_url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
        return InitiateCalendarAuthResponseDTO(authorization_url=auth_url, state=state_str)
