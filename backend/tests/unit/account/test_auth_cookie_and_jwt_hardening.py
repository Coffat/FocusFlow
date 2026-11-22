from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import jwt
import pytest
from fastapi import HTTPException, Response
from fastapi.security import HTTPAuthorizationCredentials
from starlette.requests import Request

from src.account.presentation.auth_router import _is_secure_cookie, logout
from src.evaluation.presentation.deps import get_current_evaluation_learner_id
from src.shared_kernel.config import Settings, get_settings


def test_is_secure_cookie_per_environment() -> None:
    for env in ("development", "dev", "test", "local", "DEVELOPMENT"):
        with patch(
            "src.account.presentation.auth_router.get_settings",
            return_value=Settings(environment=env, debug=True),
        ):
            assert _is_secure_cookie() is False

    for env in ("staging", "production"):
        with patch(
            "src.account.presentation.auth_router.get_settings",
            return_value=Settings(
                environment=env,
                debug=False,
                secret_key="a-very-strong-non-default-secret-key-for-prod-testing-12345",
            ),
        ):
            assert _is_secure_cookie() is True


@pytest.mark.asyncio
async def test_logout_revokes_refresh_token_and_deletes_cookies() -> None:
    raw_refresh = "sample_raw_refresh_token_123"
    token_provider = MagicMock()
    token_provider.hash_token.return_value = "hashed_refresh_token_abc"
    refresh_repo = AsyncMock()

    scope = {
        "type": "http",
        "method": "POST",
        "headers": [(b"cookie", f"refresh_token={raw_refresh}".encode())],
    }
    req = Request(scope)
    resp = Response()

    with patch(
        "src.account.presentation.auth_router.get_settings",
        return_value=Settings(
            environment="production",
            debug=False,
            secret_key="a-very-strong-non-default-secret-key-for-prod-testing-12345",
        ),
    ):
        result = await logout(
            request=req,
            response=resp,
            token_provider=token_provider,
            refresh_token_repo=refresh_repo,
        )

    assert result == {"message": "Logged out successfully."}
    token_provider.hash_token.assert_called_once_with(raw_refresh)
    refresh_repo.revoke_refresh_token.assert_awaited_once_with("hashed_refresh_token_abc")

    set_cookie_headers = resp.headers.getlist("set-cookie")
    assert len(set_cookie_headers) == 3
    assert all("Secure" in h for h in set_cookie_headers)
    assert any("access_token=" in h and "Path=/" in h for h in set_cookie_headers)
    assert any("refresh_token=" in h and "Path=/api/v1/auth" in h for h in set_cookie_headers)
    assert any("refresh_token=" in h and "Path=/;" in h for h in set_cookie_headers)


@pytest.mark.asyncio
async def test_logout_succeeds_even_when_redis_unavailable() -> None:
    token_provider = MagicMock()
    token_provider.hash_token.return_value = "hashed_refresh_token_abc"
    refresh_repo = AsyncMock()
    refresh_repo.revoke_refresh_token.side_effect = RuntimeError("Redis down")

    scope = {
        "type": "http",
        "method": "POST",
        "headers": [(b"cookie", b"refresh_token=some_token")],
    }
    req = Request(scope)
    resp = Response()

    result = await logout(
        request=req,
        response=resp,
        token_provider=token_provider,
        refresh_token_repo=refresh_repo,
    )
    assert result == {"message": "Logged out successfully."}
    set_cookie_headers = resp.headers.getlist("set-cookie")
    assert len(set_cookie_headers) == 3
    assert any("access_token=" in h and "Path=/" in h for h in set_cookie_headers)
    assert any("refresh_token=" in h and "Path=/api/v1/auth" in h for h in set_cookie_headers)
    assert any("refresh_token=" in h and "Path=/;" in h for h in set_cookie_headers)


@pytest.mark.asyncio
async def test_evaluation_deps_rejects_non_access_jwt_type() -> None:
    settings = get_settings()
    user_id = uuid4()
    now = datetime.now(UTC)

    refresh_typed_token = jwt.encode(
        {
            "sub": str(user_id),
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=15)).timestamp()),
            "type": "refresh",
        },
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )
    missing_type_token = jwt.encode(
        {
            "sub": str(user_id),
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=15)).timestamp()),
        },
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )
    valid_access_token = jwt.encode(
        {
            "sub": str(user_id),
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=15)).timestamp()),
            "type": "access",
        },
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )

    dummy_app = MagicMock()
    dummy_app.dependency_overrides = {}
    scope = {"type": "http", "method": "GET", "headers": [], "app": dummy_app}
    req = Request(scope)

    users_port = AsyncMock()
    users_port.get_user_by_id.return_value = MagicMock(id=user_id)

    for bad_token in (refresh_typed_token, missing_type_token):
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=bad_token)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_evaluation_learner_id(
                request=req,
                bearer=creds,
                users=users_port,
            )
        assert exc_info.value.status_code == 401

    good_creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=valid_access_token)
    resolved: UUID = await get_current_evaluation_learner_id(
        request=req,
        bearer=good_creds,
        users=users_port,
    )
    assert resolved == user_id
