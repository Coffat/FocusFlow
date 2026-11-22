"""Unit tests for distributed Redis rate limiter core (AUD-HIGH-05)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock

import pytest
import redis.exceptions

from src.shared_kernel.infrastructure.security.rate_limiter import (
    DEFAULT_RATE_LIMIT_POLICIES,
    RateLimitDecision,
    RateLimiterUnavailableError,
    RateLimitExceededError,
    RateLimitPolicy,
    RedisRateLimiter,
    extract_client_ip,
    hash_email,
    hash_identifier,
    hash_token,
    load_rate_limit_policies,
)


@dataclass
class _FakeAddress:
    host: str
    port: int = 12345


class _FakeHeaders(dict[str, str]):
    """Case-insensitive header mapping mimicking Starlette Headers."""

    def __init__(self, initial: dict[str, str] | None = None) -> None:
        super().__init__({k.lower(): v for k, v in (initial or {}).items()})

    def get(self, key: str, default: Any = None) -> Any:  # type: ignore[override]
        return super().get(key.lower(), default)


@dataclass
class _FakeRequest:
    client: _FakeAddress | None
    headers: _FakeHeaders


class TestExtractClientIp:
    def test_untrusted_peer_ignores_spoofed_xff_and_x_real_ip(self) -> None:
        request = _FakeRequest(
            client=_FakeAddress(host="203.0.113.42"),
            headers=_FakeHeaders(
                {
                    "X-Forwarded-For": "1.2.3.4, 5.6.7.8",
                    "X-Real-IP": "9.9.9.9",
                }
            ),
        )
        assert (
            extract_client_ip(request, trusted_proxies=["127.0.0.1/32", "::1/128"])
            == "203.0.113.42"
        )

    def test_trusted_proxy_uses_rightmost_untrusted_xff_hop(self) -> None:
        # Attacker sends X-Forwarded-For: 1.1.1.1; edge proxy appends real client 198.51.100.77;
        # internal proxy 10.0.0.5 forwards to backend peer 127.0.0.1.
        request = _FakeRequest(
            client=_FakeAddress(host="127.0.0.1"),
            headers=_FakeHeaders(
                {
                    "X-Forwarded-For": "1.1.1.1, 198.51.100.77, 10.0.0.5",
                }
            ),
        )
        ip = extract_client_ip(
            request,
            trusted_proxies=["127.0.0.1/32", "10.0.0.0/8"],
        )
        assert ip == "198.51.100.77"

    def test_trusted_proxy_accepts_comma_separated_cidr_string(self) -> None:
        request = _FakeRequest(
            client=_FakeAddress(host="172.18.0.2"),
            headers=_FakeHeaders({"X-Forwarded-For": "198.51.100.12"}),
        )
        ip = extract_client_ip(request, trusted_proxies="127.0.0.1/32, 172.16.0.0/12")
        assert ip == "198.51.100.12"

    def test_trusted_proxy_falls_back_to_x_real_ip_when_no_xff(self) -> None:
        request = _FakeRequest(
            client=_FakeAddress(host="127.0.0.1"),
            headers=_FakeHeaders({"X-Real-IP": "198.51.100.88"}),
        )
        assert extract_client_ip(request, trusted_proxies=["127.0.0.1/32"]) == "198.51.100.88"

    def test_trusted_proxy_malformed_xff_falls_back_to_peer_ip(self) -> None:
        request = _FakeRequest(
            client=_FakeAddress(host="127.0.0.1"),
            headers=_FakeHeaders({"X-Forwarded-For": "not-an-ip, definitely-bad"}),
        )
        assert extract_client_ip(request, trusted_proxies=["127.0.0.1/32"]) == "127.0.0.1"

    def test_missing_client_returns_unknown(self) -> None:
        request = _FakeRequest(client=None, headers=_FakeHeaders({}))
        assert extract_client_ip(request) == "unknown"


class TestIdentifierHashing:
    def test_hash_email_normalizes_and_hides_plaintext(self) -> None:
        raw_email = "  Alice.Example+tag@FocusFlow.IO  "
        h1 = hash_email(raw_email)
        h2 = hash_email("alice.example+tag@focusflow.io")
        assert h1 == h2
        assert len(h1) == 32
        assert "alice" not in h1.lower()
        assert "focusflow" not in h1.lower()

    def test_hash_token_hides_raw_secret(self) -> None:
        raw_token = "wc_live_super_secret_token_987654321"
        hashed = hash_token(raw_token)
        assert len(hashed) == 32
        assert raw_token not in hashed
        assert hashed == hash_token(f"  {raw_token}  ")

    def test_hash_identifier_is_deterministic_hex(self) -> None:
        digest = hash_identifier("user-123")
        assert len(digest) == 32
        int(digest, 16)  # valid hex


class TestPolicyMatrixAndOverrides:
    def test_default_policy_matrix_contains_all_required_policies(self) -> None:
        expected = {
            "auth_login_ip",
            "auth_login_account",
            "auth_register_otp_ip",
            "auth_verify_otp_ip",
            "auth_verify_otp_account",
            "auth_password_reset_ip",
            "auth_password_reset_account",
            "auth_refresh_ip",
            "auth_google_ip",
            "account_export_user",
            "webcal_feed_token",
            "calendar_oauth_init_user",
            "knowledge_upload_user",
            "billing_webhook_ip",
            "calendar_webhook_ip",
        }
        assert expected.issubset(set(DEFAULT_RATE_LIMIT_POLICIES.keys()))

    def test_high_risk_policies_fail_closed_and_webhooks_fail_open(self) -> None:
        assert DEFAULT_RATE_LIMIT_POLICIES["auth_verify_otp_ip"].fail_closed is True
        assert DEFAULT_RATE_LIMIT_POLICIES["auth_verify_otp_account"].fail_closed is True
        assert DEFAULT_RATE_LIMIT_POLICIES["auth_password_reset_account"].fail_closed is True
        assert DEFAULT_RATE_LIMIT_POLICIES["billing_webhook_ip"].fail_closed is False
        assert DEFAULT_RATE_LIMIT_POLICIES["calendar_webhook_ip"].fail_closed is False
        assert DEFAULT_RATE_LIMIT_POLICIES["webcal_feed_token"].fail_closed is False

    def test_policy_overrides_from_json_and_mapping(self) -> None:
        original_limit = DEFAULT_RATE_LIMIT_POLICIES["auth_login_ip"].limit
        env_json = json.dumps(
            {
                "auth_login_ip": {"limit": 99, "window_seconds": 120, "fail_closed": True},
                "custom_policy": {"limit": 5, "window_seconds": 30, "fail_closed": False},
            }
        )
        policies = load_rate_limit_policies(
            overrides={
                "billing_webhook_ip": RateLimitPolicy(
                    name="billing_webhook_ip",
                    limit=250,
                    window_seconds=60,
                    fail_closed=False,
                )
            },
            env_overrides_json=env_json,
        )
        assert policies["auth_login_ip"].limit == 99
        assert policies["auth_login_ip"].window_seconds == 120
        assert policies["auth_login_ip"].fail_closed is True
        assert policies["custom_policy"].limit == 5
        assert policies["billing_webhook_ip"].limit == 250
        # Ensure defaults were not mutated
        assert DEFAULT_RATE_LIMIT_POLICIES["auth_login_ip"].limit == original_limit

    def test_invalid_policy_raises_value_error(self) -> None:
        with pytest.raises(ValueError):
            RateLimitPolicy(name="bad", limit=0, window_seconds=60)
        with pytest.raises(ValueError):
            RateLimitPolicy(name="bad", limit=10, window_seconds=0)


class TestFailureSemanticsAndEnforcement:
    @pytest.mark.asyncio
    async def test_fail_closed_raises_503_on_redis_connection_error(self) -> None:
        fake_redis = AsyncMock()
        fake_redis.eval = AsyncMock(side_effect=redis.exceptions.ConnectionError("redis down"))
        limiter = RedisRateLimiter(redis_client=fake_redis)

        with pytest.raises(RateLimiterUnavailableError) as exc_info:
            await limiter.check("auth_verify_otp_account", hash_email("victim@example.com"))

        assert exc_info.value.status_code == 503
        assert exc_info.value.policy_name == "auth_verify_otp_account"

    @pytest.mark.asyncio
    async def test_fail_open_returns_degraded_allowed_on_redis_connection_error(self) -> None:
        fake_redis = AsyncMock()
        fake_redis.eval = AsyncMock(side_effect=redis.exceptions.ConnectionError("redis down"))
        limiter = RedisRateLimiter(redis_client=fake_redis)

        decision = await limiter.check("billing_webhook_ip", "203.0.113.10")
        assert decision.allowed is True
        assert decision.degraded is True
        assert decision.limit == DEFAULT_RATE_LIMIT_POLICIES["billing_webhook_ip"].limit
        assert decision.remaining == decision.limit
        assert decision.retry_after_seconds == 0

    @pytest.mark.asyncio
    async def test_enforce_raises_429_with_rate_limit_headers_when_denied(self) -> None:
        fake_redis = AsyncMock()
        # Lua return tuple: [allowed=0, current=6, remaining=0, pttl_ms=42100]
        fake_redis.eval = AsyncMock(return_value=[0, 6, 0, 42100])
        limiter = RedisRateLimiter(redis_client=fake_redis)

        policy = RateLimitPolicy(name="test_policy", limit=5, window_seconds=60, fail_closed=True)
        with pytest.raises(RateLimitExceededError) as exc_info:
            await limiter.enforce(policy, "203.0.113.55")

        err = exc_info.value
        assert err.status_code == 429
        assert err.decision == RateLimitDecision(
            allowed=False,
            limit=5,
            remaining=0,
            retry_after_seconds=43,
            degraded=False,
        )
        assert err.headers["Retry-After"] == "43"
        assert err.headers["X-RateLimit-Limit"] == "5"
        assert err.headers["X-RateLimit-Remaining"] == "0"

    @pytest.mark.asyncio
    async def test_unknown_policy_raises_key_error(self) -> None:
        fake_redis = AsyncMock()
        limiter = RedisRateLimiter(redis_client=fake_redis)
        with pytest.raises(KeyError):
            await limiter.check("nonexistent_policy", "127.0.0.1")

    @pytest.mark.asyncio
    async def test_redis_key_never_contains_raw_token_or_email(self) -> None:
        fake_redis = AsyncMock()
        fake_redis.eval = AsyncMock(return_value=[1, 1, 59, 300000])
        limiter = RedisRateLimiter(redis_client=fake_redis, key_prefix="ff:rl:unit")

        raw_token = "secret_webcal_token_xyz"
        await limiter.check("webcal_feed_token", hash_token(raw_token))

        call_args = fake_redis.eval.call_args
        assert call_args is not None
        redis_key = call_args.args[2]
        assert isinstance(redis_key, str)
        assert raw_token not in redis_key
        assert redis_key.startswith("ff:rl:unit:webcal_feed_token:")
