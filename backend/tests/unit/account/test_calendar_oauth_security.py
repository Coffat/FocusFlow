import base64
import json
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from starlette.requests import Request

from src.account.application.dtos.calendar import (
    CalendarOAuthCallbackRequestDTO,
    InitiateCalendarAuthRequestDTO,
)
from src.account.application.use_cases.calendar import (
    HandleGoogleCalendarOAuthCallbackUseCase,
    InitiateGoogleCalendarAuthUseCase,
)
from src.account.domain.ports.calendar_provider_port import CalendarAuthError
from src.account.domain.services.oauth_state import (
    create_signed_oauth_state,
    sanitize_return_to,
)
from src.account.presentation.calendar_router import handle_google_calendar_callback_get
from src.main import app
from src.shared_kernel.config import Settings
from src.shared_kernel.infrastructure.security.encryption import generate_fernet_key
from tests.helpers.calendar_stubs import InMemoryCalendarAdapter
from tests.unit.account.test_calendar_sync import InMemoryCalendarConnectionRepository


class InMemoryOAuthStateStore:
    """In-memory implementation of OAuthStateStorePort for unit testing."""

    def __init__(self) -> None:
        self._nonces: dict[str, tuple[UUID, datetime]] = {}

    async def store_nonce(self, nonce: str, user_id: UUID, ttl_seconds: int = 300) -> None:
        self._nonces[nonce] = (user_id, datetime.now(UTC) + timedelta(seconds=ttl_seconds))

    async def consume_nonce(self, nonce: str) -> UUID | None:
        entry = self._nonces.pop(nonce, None)
        if entry is None:
            return None
        user_id, expires_at = entry
        if datetime.now(UTC) >= expires_at:
            return None
        return user_id


def _fake_google_oauth_client(
    refresh_token: str = "google_refresh_token_test",
) -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(
            200,
            json={"access_token": "ya29.test", "refresh_token": refresh_token},
        )

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _make_settings(secret_key: str = "test-secret-key-for-oauth-state-hmac-32bytes") -> Settings:
    return Settings(
        calendar_provider="google",
        google_client_id="test_client_id",
        google_client_secret="test_client_secret",
        calendar_encryption_key=generate_fernet_key(),
        google_redirect_uri="http://localhost:8000/api/v1/account/calendar/google/callback",
        frontend_url="http://localhost:3000",
        secret_key=secret_key,
    )


@pytest.mark.asyncio
async def test_unsigned_raw_base64_state_rejected() -> None:
    settings = _make_settings()
    state_store = InMemoryOAuthStateStore()
    use_case = HandleGoogleCalendarOAuthCallbackUseCase(
        repository=InMemoryCalendarConnectionRepository(),
        calendar_provider=InMemoryCalendarAdapter(),
        state_store=state_store,
        secret_key=settings.secret_key,
        settings=settings,
        http_client=_fake_google_oauth_client(),
    )

    user_id = uuid4()
    raw_state = base64.urlsafe_b64encode(
        json.dumps({"user_id": str(user_id), "sync_type": "two_way"}).encode("utf-8")
    ).decode("utf-8")

    with pytest.raises(CalendarAuthError):
        await use_case.execute(
            user_id, CalendarOAuthCallbackRequestDTO(code="code", state=raw_state)
        )


@pytest.mark.asyncio
async def test_tampered_state_payload_and_signature_rejected() -> None:
    settings = _make_settings()
    state_store = InMemoryOAuthStateStore()
    init_uc = InitiateGoogleCalendarAuthUseCase(
        state_store=state_store,
        secret_key=settings.secret_key,
        settings=settings,
    )
    callback_uc = HandleGoogleCalendarOAuthCallbackUseCase(
        repository=InMemoryCalendarConnectionRepository(),
        calendar_provider=InMemoryCalendarAdapter(),
        state_store=state_store,
        secret_key=settings.secret_key,
        settings=settings,
        http_client=_fake_google_oauth_client(),
    )

    user_id = uuid4()
    init_resp = await init_uc.execute(
        user_id, InitiateCalendarAuthRequestDTO(sync_type="two_way", return_to="/schedule")
    )
    payload_b64, sig = init_resp.state.split(".")

    # Tamper signature
    bad_sig_state = f"{payload_b64}.{'0' * len(sig)}"
    with pytest.raises(CalendarAuthError):
        await callback_uc.execute(
            user_id, CalendarOAuthCallbackRequestDTO(code="code", state=bad_sig_state)
        )

    # Tamper payload while keeping original signature
    decoded = json.loads(base64.urlsafe_b64decode(payload_b64.encode("utf-8")).decode("utf-8"))
    decoded["return_to"] = "/evil"
    tampered_b64 = base64.urlsafe_b64encode(json.dumps(decoded).encode("utf-8")).decode("utf-8")
    tampered_state = f"{tampered_b64}.{sig}"
    with pytest.raises(CalendarAuthError):
        await callback_uc.execute(
            user_id, CalendarOAuthCallbackRequestDTO(code="code", state=tampered_state)
        )


@pytest.mark.asyncio
async def test_expired_state_rejected() -> None:
    settings = _make_settings()
    state_store = InMemoryOAuthStateStore()
    callback_uc = HandleGoogleCalendarOAuthCallbackUseCase(
        repository=InMemoryCalendarConnectionRepository(),
        calendar_provider=InMemoryCalendarAdapter(),
        state_store=state_store,
        secret_key=settings.secret_key,
        settings=settings,
        http_client=_fake_google_oauth_client(),
    )

    user_id = uuid4()
    nonce = "nonce-expired-test"
    await state_store.store_nonce(nonce=nonce, user_id=user_id, ttl_seconds=300)
    expired_state = create_signed_oauth_state(
        user_id=user_id,
        sync_type="two_way",
        redirect_uri=settings.google_redirect_uri,
        return_to="/settings",
        nonce=nonce,
        secret_key=settings.secret_key,
        now=datetime.now(UTC) - timedelta(seconds=600),
        ttl_seconds=300,
    )

    with pytest.raises(CalendarAuthError, match="expired"):
        await callback_uc.execute(
            user_id, CalendarOAuthCallbackRequestDTO(code="code", state=expired_state)
        )


@pytest.mark.asyncio
async def test_replayed_state_rejected() -> None:
    settings = _make_settings()
    state_store = InMemoryOAuthStateStore()
    init_uc = InitiateGoogleCalendarAuthUseCase(
        state_store=state_store,
        secret_key=settings.secret_key,
        settings=settings,
    )
    callback_uc = HandleGoogleCalendarOAuthCallbackUseCase(
        repository=InMemoryCalendarConnectionRepository(),
        calendar_provider=InMemoryCalendarAdapter(),
        state_store=state_store,
        secret_key=settings.secret_key,
        settings=settings,
        http_client=_fake_google_oauth_client(),
    )

    user_id = uuid4()
    init_resp = await init_uc.execute(user_id, InitiateCalendarAuthRequestDTO(sync_type="two_way"))
    dto = CalendarOAuthCallbackRequestDTO(code="code", state=init_resp.state)

    # First use succeeds
    first = await callback_uc.execute(user_id, dto)
    assert first.connected is True

    # Second use (replay) fails closed
    with pytest.raises(CalendarAuthError):
        await callback_uc.execute(user_id, dto)


@pytest.mark.asyncio
async def test_cross_user_state_rejected() -> None:
    settings = _make_settings()
    state_store = InMemoryOAuthStateStore()
    init_uc = InitiateGoogleCalendarAuthUseCase(
        state_store=state_store,
        secret_key=settings.secret_key,
        settings=settings,
    )
    callback_uc = HandleGoogleCalendarOAuthCallbackUseCase(
        repository=InMemoryCalendarConnectionRepository(),
        calendar_provider=InMemoryCalendarAdapter(),
        state_store=state_store,
        secret_key=settings.secret_key,
        settings=settings,
        http_client=_fake_google_oauth_client(),
    )

    victim_id = uuid4()
    attacker_id = uuid4()
    init_resp = await init_uc.execute(
        victim_id, InitiateCalendarAuthRequestDTO(sync_type="two_way")
    )

    with pytest.raises(CalendarAuthError):
        await callback_uc.execute(
            attacker_id, CalendarOAuthCallbackRequestDTO(code="code", state=init_resp.state)
        )


@pytest.mark.asyncio
async def test_unauthenticated_get_callback_returns_401() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/account/calendar/google/callback",
            params={"code": "fake_code", "state": "fake_state"},
            follow_redirects=False,
        )
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_open_redirect_return_to_sanitized() -> None:
    assert sanitize_return_to("//evil.com") == "/settings"
    assert sanitize_return_to("https://evil.com/phish") == "/settings"
    assert sanitize_return_to("/\\evil.com") == "/settings"
    assert sanitize_return_to("/ok\r\nSet-Cookie: x=1") == "/settings"
    assert sanitize_return_to("/schedule?tab=calendar") == "/schedule?tab=calendar"

    settings = _make_settings()
    state_store = InMemoryOAuthStateStore()
    init_uc = InitiateGoogleCalendarAuthUseCase(
        state_store=state_store,
        secret_key=settings.secret_key,
        settings=settings,
    )
    callback_uc = HandleGoogleCalendarOAuthCallbackUseCase(
        repository=InMemoryCalendarConnectionRepository(),
        calendar_provider=InMemoryCalendarAdapter(),
        state_store=state_store,
        secret_key=settings.secret_key,
        settings=settings,
        http_client=_fake_google_oauth_client(),
    )

    user_id = uuid4()
    init_resp = await init_uc.execute(
        user_id, InitiateCalendarAuthRequestDTO(sync_type="two_way", return_to="//evil.com")
    )
    payload_b64, _ = init_resp.state.split(".")
    decoded = json.loads(base64.urlsafe_b64decode(payload_b64.encode("utf-8")).decode("utf-8"))
    assert decoded["return_to"] == "/settings"

    scope = {"type": "http", "method": "GET", "headers": []}
    req = Request(scope)
    response = await handle_google_calendar_callback_get(
        request=req,
        code="valid_code",
        state=init_resp.state,
        user_id=user_id,
        use_case=callback_uc,
    )
    assert response.status_code == 302
    assert (
        response.headers["location"] == "http://localhost:3000/settings?calendar_connected=success"
    )
