import uuid
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.domain.exceptions.auth_exceptions import InvalidCredentialsError
from src.presentation.main import app


@pytest.mark.asyncio
async def test_google_auth_new_user_provisioning() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        unique_suffix = uuid.uuid4().hex[:8]
        test_email = f"google_user_{unique_suffix}@gmail.com"
        mock_payload = {
            "sub": f"google_sub_{unique_suffix}",
            "email": test_email,
            "name": "Google User Test",
            "email_verified": True,
            "picture": "https://lh3.googleusercontent.com/a/mock-pic"
        }

        with patch("src.infrastructure.security.google_auth_service.google_auth_service.verify_id_token") as mock_verify:
            mock_verify.return_value = mock_payload

            # 1. First-time login -> auto-provisions user + quota + tokens
            response = await client.post(
                "/api/v1/auth/google",
                json={"credential": "mock_valid_google_id_token"}
            )
            assert response.status_code == 200, response.text
            data = response.json()

            assert "access_token" in data
            assert data["token_type"] == "bearer"
            assert data["user"]["email"] == test_email
            assert data["user"]["full_name"] == "Google User Test"
            assert data["user"]["role"] == "LEARNER"
            assert data["user"]["tier"] == "FREE"

            # Check cookies
            assert "access_token" in response.cookies
            assert "refresh_token" in response.cookies

            # 2. Second-time login -> logs in without duplicate error
            repeat_response = await client.post(
                "/api/v1/auth/google",
                json={"id_token": "mock_valid_google_id_token"}
            )
            assert repeat_response.status_code == 200
            repeat_data = repeat_response.json()
            assert repeat_data["user"]["id"] == data["user"]["id"]


@pytest.mark.asyncio
async def test_google_auth_with_access_token() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        unique_suffix = uuid.uuid4().hex[:8]
        test_email = f"oauth_user_{unique_suffix}@gmail.com"
        mock_payload = {
            "sub": f"oauth_sub_{unique_suffix}",
            "email": test_email,
            "name": "OAuth User",
            "email_verified": True
        }

        with patch(
            "src.infrastructure.security.google_auth_service.google_auth_service.verify_access_token"
        ) as mock_verify_access:
            mock_verify_access.return_value = mock_payload

            response = await client.post(
                "/api/v1/auth/google",
                json={"access_token": "ya29.mock_access_token"}
            )
            assert response.status_code == 200, response.text
            data = response.json()
            assert data["user"]["email"] == test_email


@pytest.mark.asyncio
async def test_google_auth_missing_token() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/google",
            json={}
        )
        assert response.status_code == 400
        assert "Google token is required" in response.json()["detail"]


@pytest.mark.asyncio
async def test_google_auth_invalid_token() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch("src.infrastructure.security.google_auth_service.google_auth_service.verify_id_token") as mock_verify:
            mock_verify.side_effect = InvalidCredentialsError("Invalid Google ID token signature.")

            response = await client.post(
                "/api/v1/auth/google",
                json={"credential": "invalid_jwt_token"}
            )
            assert response.status_code == 401
            assert "Invalid Google ID token signature" in response.json()["detail"]
