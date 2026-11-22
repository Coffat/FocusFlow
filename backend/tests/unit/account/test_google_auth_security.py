import time
import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.account.application.dtos.auth import GoogleAuthCommand
from src.account.application.use_cases.auth.google_auth_use_case import GoogleAuthUseCase
from src.account.domain.exceptions.auth_exceptions import InvalidCredentialsError
from src.account.infrastructure.security.google_auth_service import GoogleAuthService

VALID_CLIENT_ID = "test-focusflow-client.apps.googleusercontent.com"


def _valid_id_token_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "iss": "https://accounts.google.com",
        "aud": VALID_CLIENT_ID,
        "azp": VALID_CLIENT_ID,
        "sub": "google-sub-123456",
        "email": "learner@gmail.com",
        "email_verified": True,
        "name": "FocusFlow Learner",
        "exp": int(time.time()) + 3600,
    }
    payload.update(overrides)
    return payload


# --- GoogleAuthService.verify_id_token security tests ---


def test_verify_id_token_fails_closed_when_client_id_empty() -> None:
    with patch(
        "src.account.infrastructure.security.google_auth_service.get_settings",
        return_value=MagicMock(google_client_id=""),
    ):
        svc = GoogleAuthService(client_id="")
        with pytest.raises(InvalidCredentialsError, match="client_id"):
            svc.verify_id_token("some.jwt.token")


def test_verify_id_token_rejects_wrong_audience() -> None:
    svc = GoogleAuthService(client_id=VALID_CLIENT_ID)
    with patch(
        "src.account.infrastructure.security.google_auth_service.id_token.verify_oauth2_token",
        return_value=_valid_id_token_payload(aud="other-app.apps.googleusercontent.com"),
    ):
        with pytest.raises(InvalidCredentialsError, match="audience"):
            svc.verify_id_token("some.jwt.token")


def test_verify_id_token_rejects_invalid_issuer() -> None:
    svc = GoogleAuthService(client_id=VALID_CLIENT_ID)
    with patch(
        "src.account.infrastructure.security.google_auth_service.id_token.verify_oauth2_token",
        return_value=_valid_id_token_payload(iss="https://evil.example.com"),
    ):
        with pytest.raises(InvalidCredentialsError, match="issuer"):
            svc.verify_id_token("some.jwt.token")


def test_verify_id_token_rejects_expired_token() -> None:
    svc = GoogleAuthService(client_id=VALID_CLIENT_ID)
    with patch(
        "src.account.infrastructure.security.google_auth_service.id_token.verify_oauth2_token",
        return_value=_valid_id_token_payload(exp=int(time.time()) - 60),
    ):
        with pytest.raises(InvalidCredentialsError, match="expired"):
            svc.verify_id_token("some.jwt.token")


def test_verify_id_token_rejects_invalid_signature() -> None:
    svc = GoogleAuthService(client_id=VALID_CLIENT_ID)
    with patch(
        "src.account.infrastructure.security.google_auth_service.id_token.verify_oauth2_token",
        side_effect=ValueError("Wrong signature"),
    ):
        with pytest.raises(InvalidCredentialsError, match="Wrong signature"):
            svc.verify_id_token("forged.jwt.token")


@pytest.mark.parametrize("email_verified_val", [None, False, "true", "false", 1, 0])
def test_verify_id_token_rejects_missing_or_non_true_email_verified(
    email_verified_val: Any,
) -> None:
    svc = GoogleAuthService(client_id=VALID_CLIENT_ID)
    payload = _valid_id_token_payload()
    if email_verified_val is None:
        payload.pop("email_verified", None)
    else:
        payload["email_verified"] = email_verified_val

    with patch(
        "src.account.infrastructure.security.google_auth_service.id_token.verify_oauth2_token",
        return_value=payload,
    ):
        with pytest.raises(InvalidCredentialsError, match="verified"):
            svc.verify_id_token("some.jwt.token")


def test_verify_id_token_rejects_invalid_azp() -> None:
    svc = GoogleAuthService(client_id=VALID_CLIENT_ID)
    with patch(
        "src.account.infrastructure.security.google_auth_service.id_token.verify_oauth2_token",
        return_value=_valid_id_token_payload(azp="other-app.apps.googleusercontent.com"),
    ):
        with pytest.raises(InvalidCredentialsError, match="azp"):
            svc.verify_id_token("some.jwt.token")


def test_verify_id_token_accepts_valid_payload() -> None:
    svc = GoogleAuthService(client_id=VALID_CLIENT_ID)
    expected = _valid_id_token_payload()
    with patch(
        "src.account.infrastructure.security.google_auth_service.id_token.verify_oauth2_token",
        return_value=expected,
    ) as mock_verify:
        result = svc.verify_id_token("valid.jwt.token")
        assert result["email"] == "learner@gmail.com"
        assert result["email_verified"] is True
        mock_verify.assert_called_once()
        assert mock_verify.call_args.args[2] == VALID_CLIENT_ID


# --- GoogleAuthService.verify_access_token security tests ---


def _mock_httpx_responses(responses_by_url_prefix: dict[str, tuple[int, dict[str, Any]]]) -> Any:
    mock_client = AsyncMock()

    async def fake_get(url: str, **kwargs: Any) -> MagicMock:
        for prefix, (status_code, body) in responses_by_url_prefix.items():
            if url.startswith(prefix):
                resp = MagicMock()
                resp.status_code = status_code
                resp.json.return_value = body
                return resp
        raise AssertionError(f"Unexpected URL called: {url}")

    mock_client.get.side_effect = fake_get
    mock_cm = AsyncMock()
    mock_cm.__aenter__.return_value = mock_client
    mock_cm.__aexit__.return_value = None
    return mock_cm


@pytest.mark.asyncio
async def test_verify_access_token_fails_closed_when_client_id_empty() -> None:
    with patch(
        "src.account.infrastructure.security.google_auth_service.get_settings",
        return_value=MagicMock(google_client_id=""),
    ):
        svc = GoogleAuthService(client_id="")
        with pytest.raises(InvalidCredentialsError, match="client_id"):
            await svc.verify_access_token("ya29.some_token")


@pytest.mark.asyncio
async def test_verify_access_token_rejects_wrong_app_audience() -> None:
    """Confused deputy test: access token from another Google OAuth app must be rejected."""
    svc = GoogleAuthService(client_id=VALID_CLIENT_ID)
    mock_cm = _mock_httpx_responses(
        {
            "https://oauth2.googleapis.com/tokeninfo": (
                200,
                {
                    "aud": "attacker-app.apps.googleusercontent.com",
                    "azp": "attacker-app.apps.googleusercontent.com",
                    "sub": "google-sub-123",
                    "email": "victim@gmail.com",
                    "email_verified": "true",
                    "exp": str(int(time.time()) + 3600),
                },
            ),
            "https://www.googleapis.com/oauth2/v3/userinfo": (
                200,
                {
                    "sub": "google-sub-123",
                    "email": "victim@gmail.com",
                    "email_verified": True,
                    "name": "Victim",
                },
            ),
        }
    )

    with patch(
        "src.account.infrastructure.security.google_auth_service.httpx.AsyncClient",
        return_value=mock_cm,
    ):
        with pytest.raises(InvalidCredentialsError, match="audience"):
            await svc.verify_access_token("ya29.other_app_token")


@pytest.mark.asyncio
async def test_verify_access_token_rejects_invalid_azp() -> None:
    svc = GoogleAuthService(client_id=VALID_CLIENT_ID)
    mock_cm = _mock_httpx_responses(
        {
            "https://oauth2.googleapis.com/tokeninfo": (
                200,
                {
                    "aud": VALID_CLIENT_ID,
                    "azp": "other-app.apps.googleusercontent.com",
                    "sub": "google-sub-123",
                    "email": "learner@gmail.com",
                    "email_verified": "true",
                    "exp": str(int(time.time()) + 3600),
                },
            ),
        }
    )
    with patch(
        "src.account.infrastructure.security.google_auth_service.httpx.AsyncClient",
        return_value=mock_cm,
    ):
        with pytest.raises(InvalidCredentialsError, match="azp"):
            await svc.verify_access_token("ya29.bad_azp")


@pytest.mark.asyncio
async def test_verify_access_token_rejects_expired_tokeninfo() -> None:
    svc = GoogleAuthService(client_id=VALID_CLIENT_ID)
    mock_cm = _mock_httpx_responses(
        {
            "https://oauth2.googleapis.com/tokeninfo": (
                200,
                {
                    "aud": VALID_CLIENT_ID,
                    "azp": VALID_CLIENT_ID,
                    "sub": "google-sub-123",
                    "email": "learner@gmail.com",
                    "email_verified": "true",
                    "exp": str(int(time.time()) - 10),
                },
            ),
        }
    )
    with patch(
        "src.account.infrastructure.security.google_auth_service.httpx.AsyncClient",
        return_value=mock_cm,
    ):
        with pytest.raises(InvalidCredentialsError, match="expired"):
            await svc.verify_access_token("ya29.expired")


@pytest.mark.asyncio
@pytest.mark.parametrize("email_verified_val", [None, False, "false", ""])
async def test_verify_access_token_rejects_unverified_email(email_verified_val: Any) -> None:
    svc = GoogleAuthService(client_id=VALID_CLIENT_ID)
    body: dict[str, Any] = {
        "aud": VALID_CLIENT_ID,
        "azp": VALID_CLIENT_ID,
        "sub": "google-sub-123",
        "email": "learner@gmail.com",
        "exp": str(int(time.time()) + 3600),
    }
    if email_verified_val is not None:
        body["email_verified"] = email_verified_val

    mock_cm = _mock_httpx_responses({"https://oauth2.googleapis.com/tokeninfo": (200, body)})
    with patch(
        "src.account.infrastructure.security.google_auth_service.httpx.AsyncClient",
        return_value=mock_cm,
    ):
        with pytest.raises(InvalidCredentialsError, match="verified"):
            await svc.verify_access_token("ya29.unverified")


@pytest.mark.asyncio
async def test_verify_access_token_accepts_valid_tokeninfo_and_userinfo() -> None:
    svc = GoogleAuthService(client_id=VALID_CLIENT_ID)
    mock_cm = _mock_httpx_responses(
        {
            "https://oauth2.googleapis.com/tokeninfo": (
                200,
                {
                    "aud": VALID_CLIENT_ID,
                    "azp": VALID_CLIENT_ID,
                    "sub": "google-sub-999",
                    "email": "learner@gmail.com",
                    "email_verified": "true",
                    "exp": str(int(time.time()) + 3600),
                },
            ),
            "https://www.googleapis.com/oauth2/v3/userinfo": (
                200,
                {
                    "sub": "google-sub-999",
                    "email": "learner@gmail.com",
                    "email_verified": True,
                    "name": "Verified Learner",
                    "picture": "https://example.com/avatar.png",
                },
            ),
        }
    )
    with patch(
        "src.account.infrastructure.security.google_auth_service.httpx.AsyncClient",
        return_value=mock_cm,
    ):
        payload = await svc.verify_access_token("ya29.valid_token")
        assert payload["email"] == "learner@gmail.com"
        assert payload["email_verified"] is True
        assert payload["name"] == "Verified Learner"
        assert payload["sub"] == "google-sub-999"


# --- GoogleAuthUseCase email_verified strictness test ---


@pytest.mark.asyncio
@pytest.mark.parametrize("email_verified_val", [None, False, "false", "true", 1])
async def test_google_auth_use_case_rejects_missing_or_non_bool_true_email_verified(
    email_verified_val: Any,
) -> None:
    payload: dict[str, Any] = {
        "sub": "google-sub-123",
        "email": f"user_{uuid.uuid4().hex[:6]}@gmail.com",
        "name": "Test User",
    }
    if email_verified_val is not None:
        payload["email_verified"] = email_verified_val

    auth_service = MagicMock()
    auth_service.verify_id_token.return_value = payload

    user_repo = AsyncMock()
    token_provider = MagicMock()
    refresh_repo = AsyncMock()
    uow = AsyncMock()

    use_case = GoogleAuthUseCase(
        user_repo=user_repo,
        auth_service=auth_service,
        token_provider=token_provider,
        refresh_token_repo=refresh_repo,
        uow=uow,
    )

    with pytest.raises(InvalidCredentialsError, match="verified"):
        await use_case.execute(GoogleAuthCommand(id_token="mock_id_token"))

    user_repo.find_by_email.assert_not_awaited()
    user_repo.create_user_with_quota.assert_not_awaited()
