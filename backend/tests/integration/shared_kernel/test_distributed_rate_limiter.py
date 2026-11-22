"""Real-Redis integration tests for distributed RedisRateLimiter (AUD-HIGH-05)."""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
import redis.asyncio as aioredis

from src.shared_kernel.config import get_settings
from src.shared_kernel.infrastructure.security.rate_limiter import (
    RateLimitExceededError,
    RateLimitPolicy,
    RedisRateLimiter,
    hash_email,
)


@pytest_asyncio.fixture
async def redis_client() -> AsyncIterator[aioredis.Redis]:
    settings = get_settings()
    client = aioredis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_connect_timeout=1.0,
        socket_timeout=2.0,
    )
    try:
        await client.ping()
    except Exception as exc:  # pragma: no cover - skip only if Redis unavailable
        await client.aclose()
        pytest.skip(f"Local Redis unavailable for integration test: {exc}")

    try:
        yield client
    finally:
        await client.aclose()


@pytest_asyncio.fixture
async def key_prefix(redis_client: aioredis.Redis) -> AsyncIterator[str]:
    prefix = f"ff:rl:it:{uuid.uuid4().hex[:12]}"
    try:
        yield prefix
    finally:
        keys = [k async for k in redis_client.scan_iter(match=f"{prefix}:*")]
        if keys:
            await redis_client.delete(*keys)


@pytest.mark.asyncio
async def test_below_threshold_allowed_with_accurate_remaining(
    redis_client: aioredis.Redis,
    key_prefix: str,
) -> None:
    limiter = RedisRateLimiter(redis_client=redis_client, key_prefix=key_prefix)
    policy = RateLimitPolicy(name="it_basic", limit=4, window_seconds=30, fail_closed=True)

    d1 = await limiter.check(policy, "203.0.113.1")
    d2 = await limiter.check(policy, "203.0.113.1")
    d3 = await limiter.check(policy, "203.0.113.1")
    d4 = await limiter.check(policy, "203.0.113.1")

    assert (d1.allowed, d1.limit, d1.remaining, d1.retry_after_seconds, d1.degraded) == (
        True,
        4,
        3,
        0,
        False,
    )
    assert (d2.allowed, d2.remaining) == (True, 2)
    assert (d3.allowed, d3.remaining) == (True, 1)
    assert (d4.allowed, d4.remaining) == (True, 0)

    # Key must have a bounded positive TTL (never -1 / unbounded)
    pttl = await redis_client.pttl(limiter.build_key(policy.name, "203.0.113.1"))
    assert 0 < pttl <= 30_000


@pytest.mark.asyncio
async def test_exceeding_threshold_denied_with_retry_after(
    redis_client: aioredis.Redis,
    key_prefix: str,
) -> None:
    limiter = RedisRateLimiter(redis_client=redis_client, key_prefix=key_prefix)
    policy = RateLimitPolicy(name="it_exceed", limit=2, window_seconds=20, fail_closed=True)

    assert (await limiter.check(policy, "198.51.100.10")).allowed is True
    assert (await limiter.check(policy, "198.51.100.10")).allowed is True

    denied = await limiter.check(policy, "198.51.100.10")
    assert denied.allowed is False
    assert denied.limit == 2
    assert denied.remaining == 0
    assert 1 <= denied.retry_after_seconds <= 20
    assert denied.degraded is False

    with pytest.raises(RateLimitExceededError) as exc_info:
        await limiter.enforce(policy, "198.51.100.10")
    assert exc_info.value.status_code == 429
    assert int(exc_info.value.headers["Retry-After"]) >= 1
    assert exc_info.value.headers["X-RateLimit-Limit"] == "2"
    assert exc_info.value.headers["X-RateLimit-Remaining"] == "0"


@pytest.mark.asyncio
async def test_concurrent_burst_enforces_exact_atomic_limit(
    redis_client: aioredis.Redis,
    key_prefix: str,
) -> None:
    limiter = RedisRateLimiter(redis_client=redis_client, key_prefix=key_prefix)
    policy = RateLimitPolicy(name="it_burst", limit=7, window_seconds=30, fail_closed=True)

    decisions = await asyncio.gather(*(limiter.check(policy, "198.51.100.99") for _ in range(25)))

    allowed = [d for d in decisions if d.allowed]
    denied = [d for d in decisions if not d.allowed]

    assert len(allowed) == 7
    assert len(denied) == 18
    assert sorted(d.remaining for d in allowed) == [0, 1, 2, 3, 4, 5, 6]
    assert all(d.remaining == 0 and d.retry_after_seconds >= 1 for d in denied)


@pytest.mark.asyncio
async def test_multiple_backend_replicas_share_exact_counter(
    key_prefix: str,
) -> None:
    settings = get_settings()
    replica_a = RedisRateLimiter(redis_url=settings.redis_url, key_prefix=key_prefix)
    replica_b = RedisRateLimiter(redis_url=settings.redis_url, key_prefix=key_prefix)
    policy = RateLimitPolicy(name="it_replicas", limit=5, window_seconds=30, fail_closed=True)
    subject = hash_email("shared-user@example.com")

    try:
        results = [
            await replica_a.check(policy, subject),
            await replica_b.check(policy, subject),
            await replica_a.check(policy, subject),
            await replica_b.check(policy, subject),
            await replica_a.check(policy, subject),
            await replica_b.check(policy, subject),  # 6th -> must be denied across replicas
            await replica_a.check(policy, subject),  # 7th -> must be denied across replicas
        ]
        assert [r.allowed for r in results] == [True, True, True, True, True, False, False]
        assert [r.remaining for r in results[:5]] == [4, 3, 2, 1, 0]
        assert results[5].retry_after_seconds >= 1
    finally:
        await replica_a.aclose()
        await replica_b.aclose()


@pytest.mark.asyncio
async def test_ttl_expiry_resets_window_cleanly(
    redis_client: aioredis.Redis,
    key_prefix: str,
) -> None:
    limiter = RedisRateLimiter(redis_client=redis_client, key_prefix=key_prefix)
    policy = RateLimitPolicy(name="it_ttl", limit=2, window_seconds=1, fail_closed=True)

    assert (await limiter.check(policy, "203.0.113.77")).allowed is True
    assert (await limiter.check(policy, "203.0.113.77")).allowed is True
    assert (await limiter.check(policy, "203.0.113.77")).allowed is False

    await asyncio.sleep(1.15)

    reset_decision = await limiter.check(policy, "203.0.113.77")
    assert reset_decision.allowed is True
    assert reset_decision.remaining == 1


@pytest.mark.asyncio
async def test_user_and_ip_isolation(
    redis_client: aioredis.Redis,
    key_prefix: str,
) -> None:
    limiter = RedisRateLimiter(redis_client=redis_client, key_prefix=key_prefix)
    ip_policy = RateLimitPolicy(name="it_iso_ip", limit=2, window_seconds=30, fail_closed=True)
    acct_policy = RateLimitPolicy(name="it_iso_acct", limit=2, window_seconds=30, fail_closed=True)

    # Exhaust IP A
    assert (await limiter.check(ip_policy, "203.0.113.10")).allowed is True
    assert (await limiter.check(ip_policy, "203.0.113.10")).allowed is True
    assert (await limiter.check(ip_policy, "203.0.113.10")).allowed is False

    # IP B must remain unaffected
    ip_b = await limiter.check(ip_policy, "203.0.113.20")
    assert ip_b.allowed is True
    assert ip_b.remaining == 1

    # Exhaust Account A
    acct_a = hash_email("alice@example.com")
    acct_b = hash_email("bob@example.com")
    assert (await limiter.check(acct_policy, acct_a)).allowed is True
    assert (await limiter.check(acct_policy, acct_a)).allowed is True
    assert (await limiter.check(acct_policy, acct_a)).allowed is False

    # Account B must remain unaffected
    bob = await limiter.check(acct_policy, acct_b)
    assert bob.allowed is True
    assert bob.remaining == 1
