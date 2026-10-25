import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from src.presentation.main import app


@pytest.mark.asyncio
async def test_auth_workflow() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Unique email per test run
        random_str = uuid.uuid4().hex[:8]
        email = f"learner_{random_str}@focusflow.vn"
        password = "SecurePassword123!"
        full_name = "Thang Vu"

        # 2. Register
        reg_response = await client.post(
            "/api/v1/auth/register",
            json={
                "full_name": full_name,
                "email": email,
                "password": password
            }
        )
        assert reg_response.status_code == 201, reg_response.text
        reg_data = reg_response.json()
        assert "access_token" in reg_data
        assert reg_data["user"]["email"] == email
        assert reg_data["user"]["full_name"] == full_name
        assert reg_data["token_type"] == "bearer"
        assert len(reg_data["access_token"]) > 0

        # 3. Duplicate registration should return 409 Conflict
        dup_response = await client.post(
            "/api/v1/auth/register",
            json={
                "full_name": full_name,
                "email": email,
                "password": password
            }
        )
        assert dup_response.status_code == 409

        # 4. Login with invalid password -> 401
        bad_login = await client.post(
            "/api/v1/auth/login",
            json={
                "email": email,
                "password": "WrongPassword!",
                "remember_me": True
            }
        )
        assert bad_login.status_code == 401

        # 5. Login with valid credentials -> 200 OK + JWT Token
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": email,
                "password": password,
                "remember_me": True
            }
        )
        assert login_response.status_code == 200
        login_data = login_response.json()
        assert "access_token" in login_data
        assert login_data["user"]["email"] == email
        auth_header = {"Authorization": f"Bearer {login_data['access_token']}"}

        # 6. Access protected route /me with Bearer token
        me_response = await client.get("/api/v1/auth/me", headers=auth_header)
        assert me_response.status_code == 200
        me_data = me_response.json()
        assert me_data["email"] == email
        assert me_data["full_name"] == full_name

        # 7. Refresh token rotation (ADR-008 RTR)
        refresh_cookie = login_response.cookies.get("refresh_token")
        assert refresh_cookie is not None

        # 7a. Refresh using cookie
        refresh_resp = await client.post("/api/v1/auth/refresh")
        assert refresh_resp.status_code == 200, refresh_resp.text
        refresh_data = refresh_resp.json()
        assert "access_token" in refresh_data
        assert refresh_data["user"]["email"] == email

        # 7b. Access /me with rotated access token
        new_header = {"Authorization": f"Bearer {refresh_data['access_token']}"}
        me_rotated_resp = await client.get("/api/v1/auth/me", headers=new_header)
        assert me_rotated_resp.status_code == 200

        # 7c. Replay old refresh token -> 401 (Consumed in rotation)
        replay_resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_cookie}
        )
        assert replay_resp.status_code == 401

        # 8. Logout clears cookies
        logout_response = await client.post("/api/v1/auth/logout")
        assert logout_response.status_code == 200

        # 9. Access protected route without token or cookie -> 401
        unauth_response = await client.get("/api/v1/auth/me")
        assert unauth_response.status_code == 401
