"""Endpoint-level integration tests for distributed Redis rate limiting (AUD-HIGH-05)
and session store failure semantics (AUD-HIGH-02).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import redis.asyncio as aioredis
import redis.exceptions
from httpx import ASGITransport
from sqlalchemy import delete

from src.account.domain.exceptions.auth_exceptions import SessionStoreUnavailableError
from src.account.infrastructure.orm.user_orm import UserORM
from src.account.infrastructure.security.jwt_token_provider import JwtTokenProvider
from src.main import app
from src.shared_kernel.config import get_settings
from src.shared_kernel.infrastructure.database.session import async_session_factory
from src.shared_kernel.infrastructure.security.rate_limiter import (
    DEFAULT_RATE_LIMIT_POLICIES,
    RateLimitPolicy,
    RedisRateLimiter,
    hash_email,
    hash_token,
    reset_rate_limiter_cache,
)

ORIGIN_HEADER = "http://localhost:3000"


def _unique_client_ip() -> str:
    """Return a unique TEST-NET-3 IPv4 address for per-test IP bucket isolation."""
    raw = uuid.uuid4().bytes
    return f"203.0.113.{1 + (raw[0] % 250)}"


async def _delete_redis_keys(*keys: str) -> None:
    if not keys:
        return
    client = aioredis.from_url(get_settings().redis_url, decode_responses=True)
    try:
        await client.delete(*keys)
    finally:
        await client.aclose()


async def _cleanup_users(*user_ids: uuid.UUID) -> None:
    if not user_ids:
        return
    async with async_session_factory() as session:
        await session.execute(delete(UserORM).where(UserORM.id.in_(list(user_ids))))
        await session.commit()


def _sign_billing_webhook(raw_body: bytes, timestamp: str, secret: str) -> str:
    signed_payload = f"{timestamp}.".encode() + raw_body
    return hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()


@pytest.mark.asyncio
async def test_login_rate_limit_429_with_retry_after_and_account_isolation() -> None:
    """Exceeding auth_login_account blocks Account A with 429 + Retry-After while Account B still succeeds."""
    reset_rate_limiter_cache()
    client_ip = _unique_client_ip()
    suffix = uuid.uuid4().hex[:8]
    email_a = f"rl_login_a_{suffix}@focusflow.vn"
    email_b = f"rl_login_b_{suffix}@focusflow.vn"
    password = "SecurePassword123!"
    account_limit = DEFAULT_RATE_LIMIT_POLICIES["auth_login_account"].limit

    headers = {"Origin": ORIGIN_HEADER, "X-Forwarded-For": client_ip}
    user_ids: list[uuid.UUID] = []

    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=headers,
        ) as client:
            reg_b = await client.post(
                "/api/v1/auth/register",
                json={"full_name": "Account B", "email": email_b, "password": password},
            )
            assert reg_b.status_code == 201, reg_b.text
            user_ids.append(uuid.UUID(reg_b.json()["user"]["id"]))

            # Exhaust Account A's per-account login quota
            for _ in range(account_limit):
                resp = await client.post(
                    "/api/v1/auth/login",
                    json={"email": email_a, "password": "WrongPassword!", "remember_me": False},
                )
                assert resp.status_code == 401

            # Next attempt on Account A MUST return 429 with standard headers
            limited = await client.post(
                "/api/v1/auth/login",
                json={"email": email_a, "password": "WrongPassword!", "remember_me": False},
            )
            assert limited.status_code == 429, limited.text
            body = limited.json()
            assert body["code"] == "RATE_LIMIT_EXCEEDED"
            assert "retry-after" in limited.headers
            assert int(limited.headers["retry-after"]) >= 1
            assert limited.headers["x-ratelimit-limit"] == str(account_limit)
            assert limited.headers["x-ratelimit-remaining"] == "0"

            # Account B from the same shared NAT IP must NOT be locked out
            resp_b = await client.post(
                "/api/v1/auth/login",
                json={"email": email_b, "password": password, "remember_me": True},
            )
            assert resp_b.status_code == 200, resp_b.text
    finally:
        await _cleanup_users(*user_ids)
        await _delete_redis_keys(
            f"ff:rl:auth_login_ip:{client_ip}",
            f"ff:rl:auth_register_otp_ip:{client_ip}",
            f"ff:rl:auth_login_account:{hash_email(email_a)}",
            f"ff:rl:auth_login_account:{hash_email(email_b)}",
        )


@pytest.mark.asyncio
async def test_verify_otp_rate_limit_429_and_fail_closed_503_on_redis_error() -> None:
    """Verify OTP returns 429 when exceeded and 503 when Redis is unavailable (fail-closed)."""
    reset_rate_limiter_cache()
    client_ip = _unique_client_ip()
    email = f"rl_otp_{uuid.uuid4().hex[:8]}@focusflow.vn"
    account_limit = DEFAULT_RATE_LIMIT_POLICIES["auth_verify_otp_account"].limit
    headers = {"Origin": ORIGIN_HEADER, "X-Forwarded-For": client_ip}

    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=headers,
        ) as client:
            for _ in range(account_limit):
                resp = await client.post(
                    "/api/v1/auth/register/verify-otp",
                    json={"email": email, "otp_code": "000000"},
                )
                assert resp.status_code == 400, resp.text

            limited = await client.post(
                "/api/v1/auth/register/verify-otp",
                json={"email": email, "otp_code": "000000"},
            )
            assert limited.status_code == 429, limited.text
            assert limited.json()["code"] == "RATE_LIMIT_EXCEEDED"
            assert "retry-after" in limited.headers

            # Simulate Redis outage -> fail-closed policy MUST return 503
            failing_redis = AsyncMock()
            failing_redis.eval = AsyncMock(
                side_effect=redis.exceptions.ConnectionError("redis down")
            )
            failing_limiter = RedisRateLimiter(redis_client=failing_redis)

            with patch(
                "src.shared_kernel.infrastructure.security.rate_limiter.get_rate_limiter",
                return_value=failing_limiter,
            ):
                outage_resp = await client.post(
                    "/api/v1/auth/register/verify-otp",
                    json={"email": email, "otp_code": "123456"},
                )
            assert outage_resp.status_code == 503, outage_resp.text
            assert outage_resp.json()["code"] == "RATE_LIMITER_UNAVAILABLE"
    finally:
        await _delete_redis_keys(
            f"ff:rl:auth_verify_otp_ip:{client_ip}",
            f"ff:rl:auth_verify_otp_account:{hash_email(email)}",
        )


@pytest.mark.asyncio
async def test_webcal_feed_redis_rate_limit_and_fresh_bucket_on_rotation() -> None:
    """WebCal .ics feed enforces distributed Redis limit per token hash; rotating token yields a fresh bucket."""
    reset_rate_limiter_cache()
    suffix = uuid.uuid4().hex[:8]
    user_id = uuid.uuid4()
    email = f"rl_webcal_{suffix}@focusflow.vn"

    async with async_session_factory() as session:
        session.add(
            UserORM(
                id=user_id,
                email=email,
                password_hash="not-used-in-jwt-test",
                full_name="WebCal RL Tester",
                role="LEARNER",
                tier="FREE",
            )
        )
        await session.commit()

    jwt_token = JwtTokenProvider.create_access_token(
        user_id=user_id,
        email=email,
        role="LEARNER",
        tier="FREE",
    )
    auth_headers = {"Authorization": f"Bearer {jwt_token}", "Origin": ORIGIN_HEADER}

    # Use a small Redis-backed policy limit (3 req / 300s) for fast integration verification
    custom_policies = dict(DEFAULT_RATE_LIMIT_POLICIES)
    custom_policies["webcal_feed_token"] = RateLimitPolicy(
        name="webcal_feed_token",
        limit=3,
        window_seconds=300,
        fail_closed=False,
    )
    test_prefix = f"ff:rl:test:{suffix}"
    test_limiter = RedisRateLimiter(
        redis_url=get_settings().redis_url,
        policies=custom_policies,
        key_prefix=test_prefix,
    )
    token_1: str | None = None
    token_2: str | None = None

    try:
        with patch(
            "src.shared_kernel.infrastructure.security.rate_limiter.get_rate_limiter",
            return_value=test_limiter,
        ):
            async with httpx.AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                rot1 = await client.post(
                    "/api/v1/account/calendar/webcal/rotate",
                    headers=auth_headers,
                )
                assert rot1.status_code == 200, rot1.text
                token_1 = rot1.json()["feed_url"].rsplit("/", 1)[-1].removesuffix(".ics")

                for _ in range(3):
                    resp = await client.get(f"/api/v1/feeds/{token_1}.ics")
                    assert resp.status_code == 200

                limited = await client.get(f"/api/v1/feeds/{token_1}.ics")
                assert limited.status_code == 429, limited.text
                assert limited.json()["code"] == "RATE_LIMIT_EXCEEDED"
                assert "retry-after" in limited.headers

                # Rotating WebCal token produces a new token hash -> fresh Redis bucket
                rot2 = await client.post(
                    "/api/v1/account/calendar/webcal/rotate",
                    headers=auth_headers,
                )
                assert rot2.status_code == 200, rot2.text
                token_2 = rot2.json()["feed_url"].rsplit("/", 1)[-1].removesuffix(".ics")
                assert token_2 != token_1

                fresh_resp = await client.get(f"/api/v1/feeds/{token_2}.ics")
                assert fresh_resp.status_code == 200
    finally:
        await test_limiter.aclose()
        await _cleanup_users(user_id)
        keys_to_delete: list[str] = []
        if token_1:
            keys_to_delete.append(f"{test_prefix}:webcal_feed_token:{hash_token(token_1)}")
        if token_2:
            keys_to_delete.append(f"{test_prefix}:webcal_feed_token:{hash_token(token_2)}")
        await _delete_redis_keys(*keys_to_delete)


@pytest.mark.asyncio
async def test_account_export_rate_limit_returns_429() -> None:
    """GET /api/v1/account/export enforces per-user limit (5/hour) and returns 429 on 6th call."""
    reset_rate_limiter_cache()
    suffix = uuid.uuid4().hex[:8]
    user_id = uuid.uuid4()
    email = f"rl_export_{suffix}@focusflow.vn"
    export_limit = DEFAULT_RATE_LIMIT_POLICIES["account_export_user"].limit

    async with async_session_factory() as session:
        session.add(
            UserORM(
                id=user_id,
                email=email,
                password_hash="not-used-in-jwt-test",
                full_name="Export RL Tester",
                role="LEARNER",
                tier="FREE",
            )
        )
        await session.commit()

    jwt_token = JwtTokenProvider.create_access_token(
        user_id=user_id,
        email=email,
        role="LEARNER",
        tier="FREE",
    )
    auth_headers = {"Authorization": f"Bearer {jwt_token}"}

    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=auth_headers,
        ) as client:
            for _ in range(export_limit):
                resp = await client.get("/api/v1/account/export")
                assert resp.status_code == 200, resp.text

            limited = await client.get("/api/v1/account/export")
            assert limited.status_code == 429, limited.text
            assert limited.json()["code"] == "RATE_LIMIT_EXCEEDED"
            assert "retry-after" in limited.headers
            assert limited.headers["x-ratelimit-limit"] == str(export_limit)
    finally:
        await _cleanup_users(user_id)
        await _delete_redis_keys(f"ff:rl:account_export_user:{user_id}")


@pytest.mark.asyncio
async def test_billing_webhook_allows_normal_traffic_and_fails_open_on_redis_error() -> None:
    """POST /api/v1/account/billing/webhook allows normal traffic and fails open on Redis error."""
    reset_rate_limiter_cache()
    client_ip = _unique_client_ip()
    webhook_secret = "test_webhook_secret_for_rate_limit_123456"
    payload_bytes = json.dumps(
        {
            "transaction_ref": f"missing_txn_{uuid.uuid4().hex[:8]}",
            "event_type": "payment.succeeded",
            "status": "PAID",
            "amount_vnd": 99000,
            "currency": "VND",
        }
    ).encode("utf-8")
    now_ts = str(int(time.time()))
    sig = _sign_billing_webhook(payload_bytes, now_ts, webhook_secret)
    headers = {
        "Content-Type": "application/json",
        "X-Forwarded-For": client_ip,
        "X-Webhook-Timestamp": now_ts,
        "X-Webhook-Signature": sig,
    }

    settings_obj = get_settings().model_copy(update={"payment_webhook_secret": webhook_secret})

    try:
        with patch(
            "src.account.presentation.billing_router.get_settings", return_value=settings_obj
        ):
            async with httpx.AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                # Normal traffic: rate limiter passes, HMAC verifies, missing txn -> 404 (not 429/503)
                normal_resp = await client.post(
                    "/api/v1/account/billing/webhook",
                    content=payload_bytes,
                    headers=headers,
                )
                assert normal_resp.status_code == 404, normal_resp.text

                # Redis outage -> fail-open policy MUST NOT return 503 or 429
                failing_redis = AsyncMock()
                failing_redis.eval = AsyncMock(
                    side_effect=redis.exceptions.ConnectionError("redis down")
                )
                failing_limiter = RedisRateLimiter(redis_client=failing_redis)

                with patch(
                    "src.shared_kernel.infrastructure.security.rate_limiter.get_rate_limiter",
                    return_value=failing_limiter,
                ):
                    outage_resp = await client.post(
                        "/api/v1/account/billing/webhook",
                        content=payload_bytes,
                        headers=headers,
                    )
                assert outage_resp.status_code == 404, outage_resp.text
    finally:
        await _delete_redis_keys(f"ff:rl:billing_webhook_ip:{client_ip}")


@pytest.mark.asyncio
async def test_refresh_returns_503_when_session_store_unavailable() -> None:
    """POST /api/v1/auth/refresh maps SessionStoreUnavailableError to 503 (distinct from 401)."""
    reset_rate_limiter_cache()
    client_ip = _unique_client_ip()
    failing_uc = AsyncMock()
    failing_uc.execute.side_effect = SessionStoreUnavailableError()

    from src.account.presentation.deps import get_refresh_token_use_case

    app.dependency_overrides[get_refresh_token_use_case] = lambda: failing_uc
    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"Origin": ORIGIN_HEADER, "X-Forwarded-For": client_ip},
        ) as client:
            resp = await client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": "some_opaque_refresh_token"},
            )
        assert resp.status_code == 503, resp.text
        assert resp.json()["code"] == "SESSION_STORE_UNAVAILABLE"
    finally:
        app.dependency_overrides.pop(get_refresh_token_use_case, None)
        await _delete_redis_keys(f"ff:rl:auth_refresh_ip:{client_ip}")
