import asyncio
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

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
from src.account.domain.exceptions.auth_exceptions import InvalidTokenError


@dataclass
class DummyUserRecord:
    id: uuid.UUID
    email: str
    full_name: str = "Test Learner"
    role: str = "LEARNER"
    tier: str = "FREE"
    is_locked: bool = False
    created_at: datetime = datetime.now(UTC)


class InMemoryRefreshTokenRepository:
    """In-memory model of RefreshTokenRepository matching Redis family semantics."""

    def __init__(self) -> None:
        self.tokens: dict[str, dict[str, Any]] = {}
        self.families: dict[str, set[str]] = {}
        self.user_families: dict[str, set[str]] = {}
        self.revoked_users: list[str] = []

    async def save_refresh_token(
        self,
        token_hash: str,
        user_id: str,
        family_id: str,
        expires_days: int | None = None,
    ) -> None:
        self.tokens[token_hash] = {"user_id": user_id, "family_id": family_id}
        self.families.setdefault(family_id, set()).add(token_hash)
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
        self.tokens[token_hash] = {"user_id": user_id, "family_id": family_id}
        self.families.setdefault(family_id, set()).add(token_hash)
        return True

    async def get_refresh_token(self, token_hash: str) -> dict[str, Any] | None:
        return self.tokens.get(token_hash)

    async def revoke_refresh_token(self, token_hash: str) -> None:
        self.tokens.pop(token_hash, None)

    async def revoke_family(self, family_id: str) -> None:
        for t_hash in self.families.pop(family_id, set()):
            self.tokens.pop(t_hash, None)

    async def revoke_all_for_user(self, user_id: str) -> None:
        self.revoked_users.append(user_id)
        for fam in self.user_families.pop(user_id, set()):
            await self.revoke_family(fam)


class DummyUoW:
    def __init__(self) -> None:
        self.committed = False

    async def __aenter__(self) -> "DummyUoW":
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        pass

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        pass


@pytest.mark.asyncio
async def test_confirm_password_reset_revokes_all_refresh_tokens() -> None:
    user = DummyUserRecord(id=uuid.uuid4(), email="learner@focusflow.vn")
    user_repo = AsyncMock()
    user_repo.find_by_email.return_value = user
    user_repo.update_password.return_value = None

    otp_repo = AsyncMock()
    otp_repo.consume_reset_token.return_value = user.email

    refresh_repo = InMemoryRefreshTokenRepository()
    await refresh_repo.save_refresh_token(
        token_hash="old_hash_1", user_id=str(user.id), family_id="fam_1"
    )
    await refresh_repo.save_refresh_token(
        token_hash="old_hash_2", user_id=str(user.id), family_id="fam_2"
    )

    uow = DummyUoW()
    use_case = ConfirmPasswordResetUseCase(
        user_repo=user_repo,
        otp_repo=otp_repo,
        uow=uow,
        refresh_token_repo=refresh_repo,
    )

    await use_case.execute(
        ConfirmPasswordResetCommand(
            email=user.email,
            new_password="NewSecurePassword123!",
            reset_token="valid_reset_token",
        )
    )

    assert uow.committed is True
    assert str(user.id) in refresh_repo.revoked_users
    assert await refresh_repo.get_refresh_token("old_hash_1") is None
    assert await refresh_repo.get_refresh_token("old_hash_2") is None


@pytest.mark.asyncio
async def test_concurrent_refresh_and_password_reset_does_not_revive_session() -> None:
    """
    Reproduces the race condition where RefreshTokenUseCase reads the old refresh
    token BEFORE ConfirmPasswordResetUseCase revokes all sessions, and then tries
    to rotate/persist a new refresh token AFTER the reset completes.
    """
    user = DummyUserRecord(id=uuid.uuid4(), email="race@focusflow.vn")
    refresh_repo = InMemoryRefreshTokenRepository()
    await refresh_repo.save_refresh_token(
        token_hash="hash_old_rt", user_id=str(user.id), family_id="fam_race"
    )

    reset_done = asyncio.Event()
    refresh_entered_db = asyncio.Event()

    user_repo = AsyncMock()
    user_repo.find_by_email.return_value = user
    user_repo.update_password.return_value = None

    async def slow_find_by_id(_uid: uuid.UUID) -> DummyUserRecord:
        # Signal that RefreshTokenUseCase already read the old token and is mid-flight
        refresh_entered_db.set()
        # Wait until password reset has committed and revoked all sessions
        await reset_done.wait()
        return user

    user_repo.find_by_id.side_effect = slow_find_by_id

    otp_repo = AsyncMock()
    otp_repo.consume_reset_token.return_value = user.email

    token_provider = MagicMock()
    token_provider.hash_token.side_effect = lambda raw: f"hash_{raw}"
    token_provider.create_access_token.return_value = "new_access_jwt"
    token_provider.create_refresh_token.return_value = "new_rt"

    refresh_uc = RefreshTokenUseCase(
        user_repo=user_repo,
        token_provider=token_provider,
        refresh_token_repo=refresh_repo,
    )
    reset_uc = ConfirmPasswordResetUseCase(
        user_repo=user_repo,
        otp_repo=otp_repo,
        uow=DummyUoW(),
        refresh_token_repo=refresh_repo,
    )

    async def run_reset() -> None:
        await refresh_entered_db.wait()
        await reset_uc.execute(
            ConfirmPasswordResetCommand(
                email=user.email,
                new_password="BrandNewPassword123!",
                reset_token="valid_reset_token",
            )
        )
        reset_done.set()

    refresh_task = asyncio.create_task(
        refresh_uc.execute(RefreshTokenCommand(raw_refresh_token="old_rt"))
    )
    reset_task = asyncio.create_task(run_reset())

    await reset_task
    with pytest.raises(InvalidTokenError):
        await refresh_task

    # Ensure NO new refresh token was saved in the revoked family
    assert await refresh_repo.get_refresh_token("hash_new_rt") is None
    assert refresh_repo.tokens == {}
