import json
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from src.infrastructure.caching.redis_client import get_redis_client
from src.presentation.main import app


@pytest.mark.asyncio
async def test_otp_registration_and_password_reset_workflow() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        redis = get_redis_client()
        random_str = uuid.uuid4().hex[:8]
        email = f"learner_{random_str}@focusflow.vn"
        password = "InitialPassword123!"
        new_password = "UpdatedPassword456!"
        full_name = "Duẩn Phan"

        # 1. Request Register OTP
        req_resp = await client.post(
            "/api/v1/auth/register/request-otp",
            json={
                "full_name": full_name,
                "email": email,
                "password": password
            }
        )
        assert req_resp.status_code == 200, req_resp.text
        assert "Mã xác thực" in req_resp.json()["message"]

        # 2. Verify cooldown rate limiting
        cooldown_resp = await client.post(
            "/api/v1/auth/register/request-otp",
            json={
                "full_name": full_name,
                "email": email,
                "password": password
            }
        )
        assert cooldown_resp.status_code == 429

        # 3. Retrieve OTP data from Redis to test verification
        raw_otp = await redis.get(f"otp:register:{email}")
        assert raw_otp is not None
        otp_data = json.loads(raw_otp)
        assert "otp_hash" in otp_data

        # 4. Try verifying with wrong OTP code -> 400
        bad_verify = await client.post(
            "/api/v1/auth/register/verify-otp",
            json={
                "email": email,
                "otp_code": "000000"
            }
        )
        assert bad_verify.status_code == 400

        # We can extract the actual OTP by injecting or reading from test context
        # Let's set a known OTP hash for testing
        test_code = "123456"
        from src.infrastructure.caching.otp_repository import OtpRepository
        otp_data["otp_hash"] = OtpRepository.hash_otp(test_code)
        await redis.set(f"otp:register:{email}", json.dumps(otp_data), ex=180)

        # 5. Verify with correct OTP code -> 201 Created + JWT Token
        good_verify = await client.post(
            "/api/v1/auth/register/verify-otp",
            json={
                "email": email,
                "otp_code": test_code
            }
        )
        assert good_verify.status_code == 201, good_verify.text
        verify_data = good_verify.json()
        assert "access_token" in verify_data
        assert verify_data["user"]["email"] == email

        # Ensure OTP key was deleted from Redis (Anti-Replay)
        deleted_key = await redis.get(f"otp:register:{email}")
        assert deleted_key is None

        # 6. Request Password Reset OTP
        reset_req = await client.post(
            "/api/v1/auth/password-reset/request-otp",
            json={"email": email}
        )
        assert reset_req.status_code == 200

        # Inject known reset OTP code
        raw_reset_otp = await redis.get(f"otp:reset_password:{email}")
        assert raw_reset_otp is not None
        reset_otp_data = json.loads(raw_reset_otp)
        reset_test_code = "654321"
        reset_otp_data["otp_hash"] = OtpRepository.hash_otp(reset_test_code)
        await redis.set(f"otp:reset_password:{email}", json.dumps(reset_otp_data), ex=180)

        # 7. Step 2 of 3-step Password Reset: Verify OTP -> returns reset_token
        verify_otp_resp = await client.post(
            "/api/v1/auth/password-reset/verify-otp",
            json={
                "email": email,
                "otp_code": reset_test_code
            }
        )
        assert verify_otp_resp.status_code == 200, verify_otp_resp.text
        reset_token = verify_otp_resp.json()["reset_token"]
        assert len(reset_token) > 0

        # 7b. Step 3 of 3-step Password Reset: Confirm with reset_token
        confirm_resp = await client.post(
            "/api/v1/auth/password-reset/confirm",
            json={
                "email": email,
                "reset_token": reset_token,
                "new_password": new_password
            }
        )
        assert confirm_resp.status_code == 200

        # 8. Login with old password -> 401
        old_login = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password, "remember_me": True}
        )
        assert old_login.status_code == 401

        # 9. Login with new password -> 200 OK + new JWT
        new_login = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": new_password, "remember_me": True}
        )
        assert new_login.status_code == 200
        assert "access_token" in new_login.json()
