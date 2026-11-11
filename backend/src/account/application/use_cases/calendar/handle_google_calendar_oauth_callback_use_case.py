import base64
import json
from uuid import UUID

import httpx

from src.account.application.dtos.calendar import (
    CalendarConnectionResponseDTO,
    CalendarOAuthCallbackRequestDTO,
)
from src.account.application.ports.calendar_connection_repository_port import (
    CalendarConnectionRepositoryPort,
)
from src.account.domain.models.calendar_connection import CalendarConnection
from src.account.domain.ports.calendar_provider_port import (
    CalendarAuthError,
    CalendarProviderPort,
)
from src.shared_kernel.application.uow import AsyncUnitOfWork
from src.shared_kernel.config import Settings, get_settings
from src.shared_kernel.infrastructure.security.encryption import (
    decrypt_token,
    encrypt_token,
)

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"


class HandleGoogleCalendarOAuthCallbackUseCase:
    """Exchange authorization code, encrypt refresh token via Fernet, and initialize CalendarConnection."""

    def __init__(
        self,
        repository: CalendarConnectionRepositoryPort,
        calendar_provider: CalendarProviderPort,
        settings: Settings | None = None,
        http_client: httpx.AsyncClient | None = None,
        uow: AsyncUnitOfWork | None = None,
    ) -> None:
        self._repository = repository
        self._calendar_provider = calendar_provider
        self._settings = settings or get_settings()
        self._http_client = http_client
        self._uow = uow

    async def execute(
        self,
        user_id: UUID,
        request: CalendarOAuthCallbackRequestDTO,
    ) -> CalendarConnectionResponseDTO:
        # Decode and verify CSRF state
        sync_type = "two_way"
        effective_redirect_uri = self._settings.google_redirect_uri
        if request.state:
            try:
                decoded_bytes = base64.urlsafe_b64decode(request.state.encode("utf-8"))
                state_data = json.loads(decoded_bytes.decode("utf-8"))
                state_user_id = state_data.get("user_id")
                if state_user_id and str(user_id) != state_user_id:
                    raise CalendarAuthError("State mismatch: CSRF or user discrepancy detected.")
                sync_type = state_data.get("sync_type", "two_way")
                effective_redirect_uri = state_data.get("redirect_uri") or effective_redirect_uri
            except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
                pass

        # Exchange authorization code for refresh token
        provider_name = self._settings.calendar_provider.strip().lower()
        if provider_name in ("mock", "local_mock"):
            refresh_token = f"mock_refresh_token_{user_id.hex[:8]}"
        else:
            client = self._http_client or httpx.AsyncClient(timeout=15.0)
            token_payload = {
                "client_id": self._settings.google_client_id,
                "client_secret": self._settings.google_client_secret,
                "code": request.code,
                "grant_type": "authorization_code",
                "redirect_uri": effective_redirect_uri,
            }
            try:
                resp = await client.post(GOOGLE_TOKEN_URL, data=token_payload)
                if resp.is_error:
                    raise CalendarAuthError(
                        f"OAuth code exchange failed ({resp.status_code}): {resp.text}"
                    )
                data = resp.json()
                refresh_token_opt = data.get("refresh_token")
                if not refresh_token_opt:
                    existing = await self._repository.get_by_user_id_and_provider(user_id, "GOOGLE")
                    if existing and existing.oauth_refresh_token_encrypted:
                        refresh_token = decrypt_token(
                            existing.oauth_refresh_token_encrypted,
                            key=self._settings.calendar_encryption_key or None,
                        )
                    else:
                        raise CalendarAuthError(
                            "Google OAuth did not return a refresh token. Re-consent required."
                        )
                else:
                    refresh_token = refresh_token_opt
            except httpx.HTTPError as exc:
                raise CalendarAuthError(f"HTTP network error exchanging OAuth code: {exc}") from exc

        encrypted_refresh_token = encrypt_token(
            refresh_token,
            key=self._settings.calendar_encryption_key or None,
        )

        # External calendar setup
        external_cal_id = "primary"
        if sync_type == "two_way":
            try:
                external_cal_id = await self._calendar_provider.create_secondary_calendar(
                    refresh_token=refresh_token,
                    title="FocusFlow",
                )
            except Exception:
                external_cal_id = "primary"

        connection = await self._repository.get_by_user_id_and_provider(user_id, "GOOGLE")
        if connection is None:
            source_cals = (
                ["primary", external_cal_id] if external_cal_id != "primary" else ["primary"]
            )
            connection = CalendarConnection(
                user_id=user_id,
                provider="GOOGLE",
                external_calendar_id=external_cal_id,
                oauth_refresh_token_encrypted=encrypted_refresh_token,
                sync_status="ACTIVE",
                source_calendars_json=source_cals,
            )
        else:
            connection.oauth_refresh_token_encrypted = encrypted_refresh_token
            connection.external_calendar_id = external_cal_id
            connection.mark_active()
            if external_cal_id not in connection.source_calendars_json:
                connection.source_calendars_json.append(external_cal_id)

        if self._uow is not None:
            async with self._uow as uow:
                saved = await self._repository.save(connection)
                await uow.commit()
        else:
            saved = await self._repository.save(connection)

        return CalendarConnectionResponseDTO(
            connected=saved.is_active,
            provider=saved.provider,
            sync_status=saved.sync_status,
            external_calendar_id=saved.external_calendar_id,
            source_calendars=saved.source_calendars_json,
            last_synced_at=saved.last_synced_at,
            error_detail=saved.error_detail,
        )
