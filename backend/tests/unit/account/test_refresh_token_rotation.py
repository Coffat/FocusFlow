"""Unit tests for Refresh Token Rotation (AUD-HIGH-02) with atomic reuse detection."""

from __future__ import annotations

import asyncio
import hashlib
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.account.application.dtos.auth import RefreshTokenCommand
from src.account.application.ports.auth_ports import (
    RefreshTokenInspectResult,
    RefreshTokenRotateResult,
)
from src.account.application.use_cases.auth.refresh_token_use_case import (
    RefreshTokenUseCase,
)
from src.account.domain.exceptions.auth_exceptions import (
    AccountLockedError,
    InvalidTokenError,
    SessionStoreUnavailableError,
)


@dataclass
class _DummyUser:
    id: uuid.UUID
    email: str = "learner@focusflow.vn"
    full_name: str = "FocusFlow Learner"
    role: str = "LEARNER"
    tier: str = "FREE"
    is_locked: bool = False
    created_at: datetime = datetime.now(UTC)


class _AtomicInMemoryRefreshRepo:
    """In-memory state machine mirroring the Redis Lua scripts for fast unit testing."""

    def __init__(self, default_ttl: int = 7 * 86400) -> None:
        self.default_ttl = default_ttl
        self.active: dict[str, dict[str, Any]] = {}
        self.used: dict[str, dict[str, Any]] = {}
        self.families: dict[str, set[str]] = {}
        self.family_ttls: dict[str, int] = {}
        self.user_families: dict[str, set[str]] = {}

    async def save_refresh_token(
        self,
        token_hash: str,
        user_id: str,
        family_id: str,
        expires_days: int | None = None,
    ) -> None:
        ttl = (expires_days * 86400) if expires_days is not None else self.default_ttl
        self.active[token_hash] = {"user_id": user_id, "family_id": family_id, "ttl": ttl}
        self.families.setdefault(family_id, set()).add(token_hash)
        self.family_ttls[family_id] = ttl
        self.user_families.setdefault(user_id, set()).add(family_id)

    async def save_rotated_refresh_token(
        self,
        token_hash: str,
        user_id: str,
        family_id: str,
        expires_days: int | None = None,
    ) -> bool:
        if family_id not in self.user_families.get(user_id, set()):
            return False
        ttl = (expires_days * 86400) if expires_days is not None else self.default_ttl
        self.active[token_hash] = {"user_id": user_id, "family_id": family_id, "ttl": ttl}
        self.families.setdefault(family_id, set()).add(token_hash)
        return True

    def _revoke_family_sync(self, family_id: str, user_id: str | None = None) -> None:
        members = self.families.pop(family_id, set())
        self.family_ttls.pop(family_id, None)
        for member in members:
            entry = self.active.pop(member, None)
            if entry and user_id is None:
                user_id = str(entry["user_id"])
        if user_id:
            self.user_families.get(user_id, set()).discard(family_id)

    async def inspect_refresh_token_atomic(self, token_hash: str) -> RefreshTokenInspectResult:
        active = self.active.get(token_hash)
        if active is not None:
            user_id = str(active["user_id"])
            family_id = str(active["family_id"])
            if family_id not in self.user_families.get(user_id, set()):
                self.active.pop(token_hash, None)
                return RefreshTokenInspectResult(
                    status="FAMILY_REVOKED", user_id=user_id, family_id=family_id
                )
            rem = min(int(active["ttl"]), self.family_ttls.get(family_id, int(active["ttl"])))
            if rem <= 0:
                self.active.pop(token_hash, None)
                return RefreshTokenInspectResult(status="NOT_FOUND")
            return RefreshTokenInspectResult(
                status="ACTIVE", user_id=user_id, family_id=family_id, remaining_ttl=rem
            )

        used = self.used.get(token_hash)
        if used is not None:
            user_id = str(used["user_id"])
            family_id = str(used["family_id"])
            self._revoke_family_sync(family_id, user_id)
            return RefreshTokenInspectResult(
                status="REUSE_DETECTED", user_id=user_id, family_id=family_id
            )

        return RefreshTokenInspectResult(status="NOT_FOUND")

    async def rotate_refresh_token_atomic(
        self,
        old_token_hash: str,
        new_token_hash: str,
        user_id: str,
        family_id: str,
        rotated_at: str | None = None,
        max_ttl_seconds: int | None = None,
    ) -> RefreshTokenRotateResult:
        active = self.active.get(old_token_hash)
        if active is None:
            used = self.used.get(old_token_hash)
            if used is not None:
                self._revoke_family_sync(str(used["family_id"]), str(used["user_id"]))
                return RefreshTokenRotateResult(status="REUSE_DETECTED")
            if family_id not in self.user_families.get(user_id, set()):
                return RefreshTokenRotateResult(status="FAMILY_REVOKED")
            return RefreshTokenRotateResult(status="NOT_FOUND")

        if family_id not in self.user_families.get(user_id, set()):
            self.active.pop(old_token_hash, None)
            return RefreshTokenRotateResult(status="FAMILY_REVOKED")

        rem = min(int(active["ttl"]), self.family_ttls.get(family_id, int(active["ttl"])))
        if max_ttl_seconds is not None and rem > max_ttl_seconds:
            rem = max_ttl_seconds
        if rem <= 0:
            self.active.pop(old_token_hash, None)
            return RefreshTokenRotateResult(status="EXPIRED")

        self.active.pop(old_token_hash, None)
        self.used[old_token_hash] = {
            "family_id": family_id,
            "user_id": user_id,
            "rotated_at": rotated_at or datetime.now(UTC).isoformat(),
            "replacement_hash": new_token_hash,
            "ttl": rem,
        }
        self.active[new_token_hash] = {"user_id": user_id, "family_id": family_id, "ttl": rem}
        self.families.setdefault(family_id, set()).add(new_token_hash)
        self.family_ttls[family_id] = rem
        return RefreshTokenRotateResult(status="ROTATED", remaining_ttl=rem)

    async def get_refresh_token(self, token_hash: str) -> dict[str, Any] | None:
        return self.active.get(token_hash)

    async def revoke_refresh_token(self, token_hash: str) -> None:
        entry = self.active.pop(token_hash, None) or self.used.get(token_hash)
        if entry:
            self._revoke_family_sync(str(entry["family_id"]), str(entry["user_id"]))

    async def revoke_family(self, family_id: str) -> None:
        self._revoke_family_sync(family_id)

    async def revoke_all_for_user(self, user_id: str) -> None:
        for fam in list(self.user_families.pop(user_id, set())):
            self._revoke_family_sync(fam, user_id)


def _make_token_provider() -> MagicMock:
    counter = 0
    provider = MagicMock()
    provider.hash_token.side_effect = lambda raw: hashlib.sha256(raw.encode()).hexdigest()
    provider.create_access_token.return_value = "jwt-access-token"

    def _next_refresh() -> str:
        nonlocal counter
        counter += 1
        return f"raw-refresh-token-{counter}"

    provider.create_refresh_token.side_effect = _next_refresh
    return provider


@pytest.mark.asyncio
async def test_normal_rotation_invalidates_old_and_preserves_bounded_ttl() -> None:
    user = _DummyUser(id=uuid.uuid4())
    user_repo = AsyncMock()
    user_repo.find_by_id.return_value = user
    token_provider = _make_token_provider()
    repo = _AtomicInMemoryRefreshRepo(default_ttl=3600)

    old_raw = "initial-raw-refresh-token"
    old_hash = token_provider.hash_token(old_raw)
    await repo.save_refresh_token(old_hash, str(user.id), "fam-1")
    # Simulate 1000s elapsed
    repo.active[old_hash]["ttl"] = 2600
    repo.family_ttls["fam-1"] = 2600

    uc = RefreshTokenUseCase(user_repo, token_provider, repo)
    res = await uc.execute(RefreshTokenCommand(raw_refresh_token=old_raw))

    new_hash = token_provider.hash_token(res.refresh_token)
    assert res.refresh_token != old_raw
    assert old_hash not in repo.active
    assert old_hash in repo.used
    assert repo.used[old_hash]["replacement_hash"] == new_hash
    assert repo.used[old_hash]["ttl"] == 2600
    assert repo.active[new_hash]["family_id"] == "fam-1"
    assert repo.active[new_hash]["ttl"] == 2600


@pytest.mark.asyncio
async def test_reuse_of_rotated_token_revokes_entire_family_and_invalidates_new_token() -> None:
    user = _DummyUser(id=uuid.uuid4())
    user_repo = AsyncMock()
    user_repo.find_by_id.return_value = user
    token_provider = _make_token_provider()
    repo = _AtomicInMemoryRefreshRepo()

    t1_raw = "token-1"
    await repo.save_refresh_token(
        token_provider.hash_token(t1_raw), str(user.id), "fam-compromised"
    )

    uc = RefreshTokenUseCase(user_repo, token_provider, repo)
    res = await uc.execute(RefreshTokenCommand(raw_refresh_token=t1_raw))
    t2_raw = res.refresh_token

    # Replay t1 -> reuse detected, entire family revoked!
    with pytest.raises(InvalidTokenError, match="reuse"):
        await uc.execute(RefreshTokenCommand(raw_refresh_token=t1_raw))

    # Subsequent use of legitimate t2 MUST also fail with InvalidTokenError (401)
    with pytest.raises(InvalidTokenError):
        await uc.execute(RefreshTokenCommand(raw_refresh_token=t2_raw))

    assert "fam-compromised" not in repo.user_families.get(str(user.id), set())
    assert repo.active == {}


@pytest.mark.asyncio
async def test_parallel_refresh_requests_allow_at_most_one_and_revoke_on_replay() -> None:
    user = _DummyUser(id=uuid.uuid4())
    user_repo = AsyncMock()

    async def delayed_find(_uid: uuid.UUID) -> _DummyUser:
        await asyncio.sleep(0.01)
        return user

    user_repo.find_by_id.side_effect = delayed_find
    token_provider = _make_token_provider()
    repo = _AtomicInMemoryRefreshRepo()

    t1_raw = "concurrent-token"
    await repo.save_refresh_token(token_provider.hash_token(t1_raw), str(user.id), "fam-race")

    uc = RefreshTokenUseCase(user_repo, token_provider, repo)
    results = await asyncio.gather(
        uc.execute(RefreshTokenCommand(raw_refresh_token=t1_raw)),
        uc.execute(RefreshTokenCommand(raw_refresh_token=t1_raw)),
        return_exceptions=True,
    )

    successes = [r for r in results if not isinstance(r, BaseException)]
    errors = [r for r in results if isinstance(r, InvalidTokenError)]

    assert len(successes) == 1
    assert len(errors) == 1
    # Because the second concurrent caller replayed t1, the family is now revoked
    assert "fam-race" not in repo.user_families.get(str(user.id), set())
    assert repo.active == {}


@pytest.mark.asyncio
async def test_family_revocation_isolates_other_user_sessions() -> None:
    user = _DummyUser(id=uuid.uuid4())
    user_repo = AsyncMock()
    user_repo.find_by_id.return_value = user
    token_provider = _make_token_provider()
    repo = _AtomicInMemoryRefreshRepo()

    await repo.save_refresh_token(token_provider.hash_token("famA-t1"), str(user.id), "fam-A")
    await repo.save_refresh_token(token_provider.hash_token("famB-t1"), str(user.id), "fam-B")

    uc = RefreshTokenUseCase(user_repo, token_provider, repo)
    # Rotate fam-A, then replay famA-t1
    await uc.execute(RefreshTokenCommand(raw_refresh_token="famA-t1"))
    with pytest.raises(InvalidTokenError):
        await uc.execute(RefreshTokenCommand(raw_refresh_token="famA-t1"))

    # Family B MUST remain completely healthy and rotatable!
    res_b = await uc.execute(RefreshTokenCommand(raw_refresh_token="famB-t1"))
    assert res_b.refresh_token
    assert "fam-B" in repo.user_families[str(user.id)]
    assert "fam-A" not in repo.user_families[str(user.id)]


@pytest.mark.asyncio
async def test_expired_or_unknown_token_raises_401_without_revoking_other_sessions() -> None:
    user = _DummyUser(id=uuid.uuid4())
    user_repo = AsyncMock()
    user_repo.find_by_id.return_value = user
    token_provider = _make_token_provider()
    repo = _AtomicInMemoryRefreshRepo()

    await repo.save_refresh_token(token_provider.hash_token("active-t1"), str(user.id), "fam-ok")

    uc = RefreshTokenUseCase(user_repo, token_provider, repo)
    with pytest.raises(InvalidTokenError):
        await uc.execute(RefreshTokenCommand(raw_refresh_token="expired-unknown-token"))

    assert "fam-ok" in repo.user_families[str(user.id)]
    assert token_provider.hash_token("active-t1") in repo.active


@pytest.mark.asyncio
async def test_locked_user_revokes_family_and_raises_account_locked() -> None:
    user = _DummyUser(id=uuid.uuid4(), is_locked=True)
    user_repo = AsyncMock()
    user_repo.find_by_id.return_value = user
    token_provider = _make_token_provider()
    repo = _AtomicInMemoryRefreshRepo()

    await repo.save_refresh_token(token_provider.hash_token("locked-t1"), str(user.id), "fam-lock")

    uc = RefreshTokenUseCase(user_repo, token_provider, repo)
    with pytest.raises(AccountLockedError):
        await uc.execute(RefreshTokenCommand(raw_refresh_token="locked-t1"))

    assert "fam-lock" not in repo.user_families.get(str(user.id), set())
    assert repo.active == {}


@pytest.mark.asyncio
async def test_redis_failure_on_inspect_or_rotate_raises_unavailable_never_swallowed() -> None:
    user = _DummyUser(id=uuid.uuid4())
    user_repo = AsyncMock()
    user_repo.find_by_id.return_value = user
    token_provider = _make_token_provider()

    failing_inspect_repo = AsyncMock()
    failing_inspect_repo.inspect_refresh_token_atomic.side_effect = SessionStoreUnavailableError()
    uc1 = RefreshTokenUseCase(user_repo, token_provider, failing_inspect_repo)
    with pytest.raises(SessionStoreUnavailableError):
        await uc1.execute(RefreshTokenCommand(raw_refresh_token="raw-token"))

    failing_rotate_repo = AsyncMock()
    failing_rotate_repo.inspect_refresh_token_atomic.return_value = RefreshTokenInspectResult(
        status="ACTIVE",
        user_id=str(user.id),
        family_id="fam-1",
        remaining_ttl=3600,
    )
    failing_rotate_repo.rotate_refresh_token_atomic.side_effect = ConnectionError("Redis down")
    uc2 = RefreshTokenUseCase(user_repo, token_provider, failing_rotate_repo)
    with pytest.raises(SessionStoreUnavailableError):
        await uc2.execute(RefreshTokenCommand(raw_refresh_token="raw-token"))
