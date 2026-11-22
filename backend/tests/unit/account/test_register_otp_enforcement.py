from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app
from src.shared_kernel.config import Settings


@pytest.mark.asyncio
@pytest.mark.parametrize("env", ["production", "staging", "PRODUCTION", "STAGING"])
async def test_direct_register_blocked_in_production_and_staging(env: str) -> None:
    transport = ASGITransport(app=app)
    prod_settings = Settings(
        environment=env,
        debug=False,
        secret_key="a-very-strong-non-default-secret-key-for-prod-testing-12345",
    )

    with (
        patch(
            "src.account.presentation.auth_router.get_settings",
            return_value=prod_settings,
        ),
        patch(
            "src.account.application.use_cases.auth.register_use_case.RegisterUseCase.execute",
            new_callable=AsyncMock,
        ) as mock_register_exec,
    ):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/register",
                json={
                    "full_name": "Bypass Tester",
                    "email": "bypass@focusflow.vn",
                    "password": "SecurePassword123!",
                },
            )

    assert resp.status_code == 403, resp.text
    assert "REGISTRATION_OTP_REQUIRED" in str(resp.json()["detail"])
    mock_register_exec.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("env", ["development", "dev", "test", "local"])
async def test_direct_register_allowed_in_dev_and_test(env: str) -> None:
    import uuid

    transport = ASGITransport(app=app)
    dev_settings = Settings(environment=env, debug=True)

    with patch(
        "src.account.presentation.auth_router.get_settings",
        return_value=dev_settings,
    ):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            email = f"dev_reg_{env}_{uuid.uuid4().hex[:8]}@focusflow.vn"
            resp = await client.post(
                "/api/v1/auth/register",
                json={
                    "full_name": "Dev Tester",
                    "email": email,
                    "password": "SecurePassword123!",
                },
            )

    assert resp.status_code == 201, resp.text
    assert resp.json()["user"]["email"] == email
