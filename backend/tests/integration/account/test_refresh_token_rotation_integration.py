"""Real-Redis integration tests for atomic Refresh Token Rotation & Reuse Detection (AUD-HIGH-02)."""

from __future__ import annotations

import asyncio
import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import redis.asyncio as aioredis

from src.account.application.dtos.auth import (
    ConfirmPasswordResetCommand,
    RefreshTokenCommand,
)
from src.account.application.use_cases.auth.password_reset_otp_use_case import (
    ConfirmPasswordResetUseCase,
)
from src.account.application.use_cases.auth.refresh_token_use_case import (
    RefreshTokenUseCase,
)
from src.account.domain.exceptions.auth_exceptions import (
    InvalidTokenError,
    SessionStoreUnavailableError,
)
from src.account.infrastructure.caching.redis_client import (
    RefreshTokenRepository,
    get_redis_client,
)


@dataclass
class _DummyUser:
    id: uuid.UUID
    email: str = "rtr-integration@focusflow.vn"
    full_name: str = "RTR Learner"
    role: str = "LEARNER"
    tier: str = "FREE"
    is_locked: bool = False
    created_at: datetime = datetime.now(UTC)


class _DummyUoW:
    async def __aenter__(self) -> _DummyUoW:
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        pass

    async def commit(self) -> None:
        pass

    async def rollback(self) -> None:
        pass


def _make_token_provider() -> MagicMock:
    counter = 0
    provider = MagicMock()
    provider.hash_token.side_effect = lambda raw: hashlib.sha256(raw.encode()).hexdigest()
    provider.create_access_token.return_value = "jwt-access-token"

    def _next_refresh() -> str:
        nonlocal counter
        counter += 1
        return f"rtr-int-{uuid.uuid4().hex}-{counter}"

    provider.create_refresh_token.side_effect = _next_refresh
    return provider


@pytest.fixture
async def clean_redis_keys() -> Any:
    """Track created keys/users/families and clean them up after each integration test."""
    client = get_redis_client()
    try:
        await client.ping()
    except Exception as exc:
        pytest.skip(f"Redis is not reachable for integration tests: {exc}")

    tracked_keys: set[str] = set()
    yield client, tracked_keys

    if tracked_keys:
        await client.delete(*tracked_keys)


@pytest.mark.asyncio
async def test_real_redis_normal_rotation_preserves_family_and_bounded_ttl(
    clean_redis_keys: tuple[aioredis.Redis, set[str]],
) -> None:
    client, tracked = clean_redis_keys
    user = _DummyUser(id=uuid.uuid4())
    user_repo = AsyncMock()
    user_repo.find_by_id.return_value = user
    provider = _make_token_provider()
    repo = RefreshTokenRepository()

    fam_id = f"fam-{uuid.uuid4().hex}"
    t1_raw = f"raw-t1-{uuid.uuid4().hex}"
    t1_hash = provider.hash_token(t1_raw)

    await repo.save_refresh_token(t1_hash, str(user.id), fam_id, expires_days=7)
    # Artificially shorten remaining TTL to 120s to prove rotation NEVER extends session lifetime
    await client.expire(f"refresh_token:{t1_hash}", 120)
    await client.expire(f"token_family:{fam_id}", 120)

    uc = RefreshTokenUseCase(user_repo, provider, repo)
    result = await uc.execute(RefreshTokenCommand(raw_refresh_token=t1_raw))
    t2_hash = provider.hash_token(result.refresh_token)

    tracked.update(
        {
            f"refresh_token:{t1_hash}",
            f"used_refresh_token:{t1_hash}",
            f"refresh_token:{t2_hash}",
            f"token_family:{fam_id}",
            f"user_families:{user.id}",
        }
    )

    # Old token deleted, used marker recorded with bounded TTL <= 120s
    assert await client.get(f"refresh_token:{t1_hash}") is None
    used_raw = await client.get(f"used_refresh_token:{t1_hash}")
    assert used_raw is not None
    used_data = json.loads(used_raw)
    assert used_data["family_id"] == fam_id
    assert used_data["user_id"] == str(user.id)
    assert used_data["replacement_hash"] == t2_hash
    assert "rotated_at" in used_data

    used_ttl = await client.ttl(f"used_refresh_token:{t1_hash}")
    new_ttl = await client.ttl(f"refresh_token:{t2_hash}")
    fam_ttl = await client.ttl(f"token_family:{fam_id}")
    assert 0 < used_ttl <= 120
    assert 0 < new_ttl <= 120
    assert 0 < fam_ttl <= 120

    # New token is valid in the same family
    new_raw = await client.get(f"refresh_token:{t2_hash}")
    assert new_raw is not None
    assert json.loads(new_raw) == {"user_id": str(user.id), "family_id": fam_id}


@pytest.mark.asyncio
async def test_real_redis_reuse_detection_revokes_entire_family_and_blocks_new_token(
    clean_redis_keys: tuple[aioredis.Redis, set[str]],
) -> None:
    client, tracked = clean_redis_keys
    user = _DummyUser(id=uuid.uuid4())
    user_repo = AsyncMock()
    user_repo.find_by_id.return_value = user
    provider = _make_token_provider()
    repo = RefreshTokenRepository()

    fam_id = f"fam-reuse-{uuid.uuid4().hex}"
    t1_raw = f"raw-t1-{uuid.uuid4().hex}"
    t1_hash = provider.hash_token(t1_raw)
    await repo.save_refresh_token(t1_hash, str(user.id), fam_id, expires_days=1)

    uc = RefreshTokenUseCase(user_repo, provider, repo)
    res1 = await uc.execute(RefreshTokenCommand(raw_refresh_token=t1_raw))
    t2_raw = res1.refresh_token
    t2_hash = provider.hash_token(t2_raw)

    tracked.update(
        {
            f"refresh_token:{t1_hash}",
            f"used_refresh_token:{t1_hash}",
            f"refresh_token:{t2_hash}",
            f"token_family:{fam_id}",
            f"user_families:{user.id}",
        }
    )

    # Attacker replays old t1 -> triggers atomic family revocation
    with pytest.raises(InvalidTokenError, match="reuse"):
        await uc.execute(RefreshTokenCommand(raw_refresh_token=t1_raw))

    # Entire family is revoked in Redis
    assert await client.get(f"refresh_token:{t2_hash}") is None
    assert await client.exists(f"token_family:{fam_id}") == 0
    assert await client.sismember(f"user_families:{user.id}", fam_id) == 0

    # Victim's legitimate t2 now ALSO fails with 401
    with pytest.raises(InvalidTokenError):
        await uc.execute(RefreshTokenCommand(raw_refresh_token=t2_raw))


@pytest.mark.asyncio
async def test_real_redis_parallel_refresh_same_token_no_dual_tokens_minted(
    clean_redis_keys: tuple[aioredis.Redis, set[str]],
) -> None:
    client, tracked = clean_redis_keys
    user = _DummyUser(id=uuid.uuid4())
    user_repo = AsyncMock()

    async def slow_find(_uid: uuid.UUID) -> _DummyUser:
        await asyncio.sleep(0.02)
        return user

    user_repo.find_by_id.side_effect = slow_find
    provider = _make_token_provider()
    repo = RefreshTokenRepository()

    fam_id = f"fam-par-{uuid.uuid4().hex}"
    t1_raw = f"raw-par-{uuid.uuid4().hex}"
    t1_hash = provider.hash_token(t1_raw)
    await repo.save_refresh_token(t1_hash, str(user.id), fam_id, expires_days=1)

    uc = RefreshTokenUseCase(user_repo, provider, repo)
    results = await asyncio.gather(
        uc.execute(RefreshTokenCommand(raw_refresh_token=t1_raw)),
        uc.execute(RefreshTokenCommand(raw_refresh_token=t1_raw)),
        return_exceptions=True,
    )

    successes = [r for r in results if not isinstance(r, BaseException)]
    errors = [r for r in results if isinstance(r, InvalidTokenError)]

    tracked.update(
        {
            f"refresh_token:{t1_hash}",
            f"used_refresh_token:{t1_hash}",
            f"token_family:{fam_id}",
            f"user_families:{user.id}",
        }
    )
    for s in successes:
        tracked.add(f"refresh_token:{provider.hash_token(s.refresh_token)}")

    assert len(successes) == 1
    assert len(errors) == 1
    # Replay invalidated the family so no dual valid tokens survive in Redis
    assert await client.exists(f"token_family:{fam_id}") == 0
    assert await client.sismember(f"user_families:{user.id}", fam_id) == 0


@pytest.mark.asyncio
async def test_real_redis_cross_session_family_isolation(
    clean_redis_keys: tuple[aioredis.Redis, set[str]],
) -> None:
    client, tracked = clean_redis_keys
    user = _DummyUser(id=uuid.uuid4())
    user_repo = AsyncMock()
    user_repo.find_by_id.return_value = user
    provider = _make_token_provider()
    repo = RefreshTokenRepository()

    fam_a = f"fam-A-{uuid.uuid4().hex}"
    fam_b = f"fam-B-{uuid.uuid4().hex}"
    t_a1 = f"raw-a1-{uuid.uuid4().hex}"
    t_b1 = f"raw-b1-{uuid.uuid4().hex}"
    await repo.save_refresh_token(provider.hash_token(t_a1), str(user.id), fam_a, expires_days=1)
    await repo.save_refresh_token(provider.hash_token(t_b1), str(user.id), fam_b, expires_days=1)

    uc = RefreshTokenUseCase(user_repo, provider, repo)
    res_a = await uc.execute(RefreshTokenCommand(raw_refresh_token=t_a1))

    # Compromise Family A by replaying t_a1
    with pytest.raises(InvalidTokenError):
        await uc.execute(RefreshTokenCommand(raw_refresh_token=t_a1))

    # Family B MUST remain active and usable!
    res_b = await uc.execute(RefreshTokenCommand(raw_refresh_token=t_b1))

    tracked.update(
        {
            f"used_refresh_token:{provider.hash_token(t_a1)}",
            f"refresh_token:{provider.hash_token(res_a.refresh_token)}",
            f"used_refresh_token:{provider.hash_token(t_b1)}",
            f"refresh_token:{provider.hash_token(res_b.refresh_token)}",
            f"token_family:{fam_a}",
            f"token_family:{fam_b}",
            f"user_families:{user.id}",
        }
    )

    assert await client.sismember(f"user_families:{user.id}", fam_a) == 0
    assert await client.sismember(f"user_families:{user.id}", fam_b) == 1
    assert await client.get(f"refresh_token:{provider.hash_token(res_b.refresh_token)}") is not None


@pytest.mark.asyncio
async def test_real_redis_expired_token_returns_401_without_revoking_other_sessions(
    clean_redis_keys: tuple[aioredis.Redis, set[str]],
) -> None:
    client, tracked = clean_redis_keys
    user = _DummyUser(id=uuid.uuid4())
    user_repo = AsyncMock()
    user_repo.find_by_id.return_value = user
    provider = _make_token_provider()
    repo = RefreshTokenRepository()

    fam_ok = f"fam-ok-{uuid.uuid4().hex}"
    ok_raw = f"raw-ok-{uuid.uuid4().hex}"
    ok_hash = provider.hash_token(ok_raw)
    await repo.save_refresh_token(ok_hash, str(user.id), fam_ok, expires_days=1)

    tracked.update(
        {f"refresh_token:{ok_hash}", f"token_family:{fam_ok}", f"user_families:{user.id}"}
    )

    uc = RefreshTokenUseCase(user_repo, provider, repo)
    with pytest.raises(InvalidTokenError):
        await uc.execute(RefreshTokenCommand(raw_refresh_token=f"expired-{uuid.uuid4().hex}"))

    assert await client.sismember(f"user_families:{user.id}", fam_ok) == 1
    assert await client.get(f"refresh_token:{ok_hash}") is not None


@pytest.mark.asyncio
async def test_real_redis_logout_revokes_family_and_blocks_subsequent_refresh(
    clean_redis_keys: tuple[aioredis.Redis, set[str]],
) -> None:
    client, tracked = clean_redis_keys
    user = _DummyUser(id=uuid.uuid4())
    user_repo = AsyncMock()
    user_repo.find_by_id.return_value = user
    provider = _make_token_provider()
    repo = RefreshTokenRepository()

    fam_logout = f"fam-logout-{uuid.uuid4().hex}"
    fam_other = f"fam-other-{uuid.uuid4().hex}"
    t_logout = f"raw-logout-{uuid.uuid4().hex}"
    t_other = f"raw-other-{uuid.uuid4().hex}"

    await repo.save_refresh_token(provider.hash_token(t_logout), str(user.id), fam_logout, 1)
    await repo.save_refresh_token(provider.hash_token(t_other), str(user.id), fam_other, 1)

    tracked.update(
        {
            f"refresh_token:{provider.hash_token(t_logout)}",
            f"refresh_token:{provider.hash_token(t_other)}",
            f"token_family:{fam_logout}",
            f"token_family:{fam_other}",
            f"user_families:{user.id}",
        }
    )

    # Logout calls revoke_refresh_token(token_hash)
    await repo.revoke_refresh_token(provider.hash_token(t_logout))

    assert await client.exists(f"token_family:{fam_logout}") == 0
    assert await client.sismember(f"user_families:{user.id}", fam_logout) == 0
    assert await client.sismember(f"user_families:{user.id}", fam_other) == 1

    uc = RefreshTokenUseCase(user_repo, provider, repo)
    with pytest.raises(InvalidTokenError):
        await uc.execute(RefreshTokenCommand(raw_refresh_token=t_logout))


@pytest.mark.asyncio
async def test_real_redis_password_reset_revokes_all_families_and_blocks_concurrent_refresh(
    clean_redis_keys: tuple[aioredis.Redis, set[str]],
) -> None:
    client, tracked = clean_redis_keys
    user = _DummyUser(id=uuid.uuid4())
    provider = _make_token_provider()
    repo = RefreshTokenRepository()

    fam_1 = f"fam-pr1-{uuid.uuid4().hex}"
    fam_2 = f"fam-pr2-{uuid.uuid4().hex}"
    t1_raw = f"raw-pr1-{uuid.uuid4().hex}"
    t2_raw = f"raw-pr2-{uuid.uuid4().hex}"
    await repo.save_refresh_token(provider.hash_token(t1_raw), str(user.id), fam_1, 1)
    await repo.save_refresh_token(provider.hash_token(t2_raw), str(user.id), fam_2, 1)

    refresh_entered_db = asyncio.Event()
    reset_done = asyncio.Event()

    user_repo = AsyncMock()
    user_repo.find_by_email.return_value = user
    user_repo.update_password.return_value = None

    async def paused_find_by_id(_uid: uuid.UUID) -> _DummyUser:
        refresh_entered_db.set()
        await reset_done.wait()
        return user

    user_repo.find_by_id.side_effect = paused_find_by_id

    otp_repo = AsyncMock()
    otp_repo.consume_reset_token.return_value = user.email

    refresh_uc = RefreshTokenUseCase(user_repo, provider, repo)
    reset_uc = ConfirmPasswordResetUseCase(user_repo, otp_repo, _DummyUoW(), repo)

    async def run_reset() -> None:
        await refresh_entered_db.wait()
        await reset_uc.execute(
            ConfirmPasswordResetCommand(
                email=user.email,
                new_password="BrandNewPassword123!",
                reset_token="valid-reset-token",
            )
        )
        reset_done.set()

    refresh_task = asyncio.create_task(
        refresh_uc.execute(RefreshTokenCommand(raw_refresh_token=t1_raw))
    )
    reset_task = asyncio.create_task(run_reset())

    await reset_task
    with pytest.raises(InvalidTokenError):
        await refresh_task

    tracked.update(
        {
            f"refresh_token:{provider.hash_token(t1_raw)}",
            f"refresh_token:{provider.hash_token(t2_raw)}",
            f"token_family:{fam_1}",
            f"token_family:{fam_2}",
            f"user_families:{user.id}",
        }
    )

    assert await client.exists(f"user_families:{user.id}") == 0
    assert await client.exists(f"token_family:{fam_1}") == 0
    assert await client.exists(f"token_family:{fam_2}") == 0


@pytest.mark.asyncio
async def test_real_redis_outage_raises_session_store_unavailable_error() -> None:
    user = _DummyUser(id=uuid.uuid4())
    user_repo = AsyncMock()
    user_repo.find_by_id.return_value = user
    provider = _make_token_provider()
    repo = RefreshTokenRepository()

    broken_client = AsyncMock()
    broken_client.eval.side_effect = aioredis.ConnectionError("Connection refused")

    uc = RefreshTokenUseCase(user_repo, provider, repo)
    with patch(
        "src.account.infrastructure.caching.redis_client.get_redis_client",
        return_value=broken_client,
    ):
        with pytest.raises(SessionStoreUnavailableError):
            await uc.execute(RefreshTokenCommand(raw_refresh_token="any-token"))
