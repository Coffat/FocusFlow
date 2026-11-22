import secrets
from datetime import UTC, datetime
from urllib.parse import urlencode
from uuid import UUID

from src.account.application.dtos.calendar import (
    InitiateCalendarAuthRequestDTO,
    InitiateCalendarAuthResponseDTO,
)
from src.account.application.ports.oauth_state_store_port import OAuthStateStorePort
from src.account.domain.ports.calendar_provider_port import CalendarAuthError
from src.account.domain.services.oauth_state import (
    OAUTH_STATE_TTL_SECONDS,
    create_signed_oauth_state,
    sanitize_return_to,
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

    def __init__(
        self,
        state_store: OAuthStateStorePort,
        secret_key: str | None = None,
        settings: Settings | None = None,
        state_ttl_seconds: int = OAUTH_STATE_TTL_SECONDS,
    ) -> None:
        self._settings = settings or get_settings()
        self._state_store = state_store
        self._secret_key = secret_key if secret_key is not None else self._settings.secret_key
        self._state_ttl_seconds = state_ttl_seconds

    async def execute(
        self,
        user_id: UUID,
        request: InitiateCalendarAuthRequestDTO,
    ) -> InitiateCalendarAuthResponseDTO:
        provider_name = self._settings.calendar_provider.strip().lower()
        if provider_name not in ("google", "google_calendar"):
            raise CalendarAuthError(
                f"CALENDAR_PROVIDER_NOT_CONFIGURED: Unsupported calendar_provider={self._settings.calendar_provider!r}."
            )
        if not self._settings.google_client_id.strip():
            raise CalendarAuthError("CALENDAR_OAUTH_NOT_CONFIGURED: Missing GOOGLE_CLIENT_ID.")

        sync_type = request.sync_type.lower()
        scopes = TWO_WAY_SCOPES if sync_type == "two_way" else INBOUND_SCOPES

        redirect_uri = request.redirect_uri or self._settings.google_redirect_uri
        safe_return_to = sanitize_return_to(request.return_to)

        nonce = secrets.token_urlsafe(24)
        state_str = create_signed_oauth_state(
            user_id=user_id,
            sync_type=sync_type,
            redirect_uri=redirect_uri,
            return_to=safe_return_to,
            nonce=nonce,
            secret_key=self._secret_key,
            now=datetime.now(UTC),
            ttl_seconds=self._state_ttl_seconds,
        )
        await self._state_store.store_nonce(
            nonce=nonce,
            user_id=user_id,
            ttl_seconds=self._state_ttl_seconds,
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
