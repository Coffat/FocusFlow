import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from pydantic import ValidationError

from src.account.application.dtos.profile import (
    AIQuotaResponseDTO,
    ChangePasswordRequestDTO,
    ProfileResponseDTO,
    UpdateProfileRequestDTO,
)
from src.account.application.ports.user_repository_port import UserRepositoryPort
from src.account.application.use_cases.profile import (
    ChangePasswordUseCase,
    GetProfileUseCase,
    GetQuotaUseCase,
    UpdateProfileUseCase,
)
from src.account.domain.services.password_hasher import PasswordHasher


class DummyUser:
    def __init__(
        self,
        user_id: uuid.UUID,
        email: str,
        password_hash: str,
        full_name: str,
        timezone: str = "Asia/Ho_Chi_Minh",
        role: str = "LEARNER",
        tier: str = "FREE",
    ) -> None:
        self.id = user_id
        self.email = email
        self.password_hash = password_hash
        self.full_name = full_name
        self.timezone = timezone
        self.role = role
        self.tier = tier
        self.created_at = datetime.now(UTC)


class DummyQuota:
    def __init__(
        self,
        quota_id: uuid.UUID,
        user_id: uuid.UUID,
        monthly_limit: int = 30,
        used_calls: int = 0,
        reserved_calls: int = 0,
        tokens_consumed: int = 0,
    ) -> None:
        self.id = quota_id
        self.user_id = user_id
        self.monthly_limit = monthly_limit
        self.used_calls = used_calls
        self.reserved_calls = reserved_calls
        self.tokens_consumed = tokens_consumed
        self.cycle_start = datetime.now(UTC)
        self.cycle_end = datetime.now(UTC) + timedelta(days=30)


class InMemoryUserRepository(UserRepositoryPort):
    def __init__(self) -> None:
        self.users: dict[uuid.UUID, DummyUser] = {}
        self.quotas: dict[uuid.UUID, DummyQuota] = {}

    async def find_by_email(self, email: str) -> DummyUser | None:
        for u in self.users.values():
            if u.email.lower() == email.lower():
                return u
        return None

    async def find_by_id(self, user_id: uuid.UUID) -> DummyUser | None:
        return self.users.get(user_id)

    async def create_user_with_quota(self, user: Any, quota: Any = None) -> DummyUser:
        self.users[user.id] = user
        if quota:
            self.quotas[user.id] = quota
        return user

    async def update_password(self, user_id: uuid.UUID, password_hash: str) -> None:
        if user_id in self.users:
            self.users[user_id].password_hash = password_hash

    async def update_profile(
        self, user_id: uuid.UUID, full_name: str, timezone: str
    ) -> DummyUser | None:
        user = self.users.get(user_id)
        if user:
            user.full_name = full_name
            user.timezone = timezone
        return user

    async def get_quota_by_user_id(self, user_id: uuid.UUID) -> DummyQuota | None:
        return self.quotas.get(user_id)

    async def create_or_init_quota(self, user_id: uuid.UUID, tier: str = "FREE") -> DummyQuota:
        monthly_limit = 100 if tier == "PREMIUM" else 30
        quota = DummyQuota(
            quota_id=uuid.uuid4(),
            user_id=user_id,
            monthly_limit=monthly_limit,
            used_calls=0,
            reserved_calls=0,
            tokens_consumed=0,
        )
        self.quotas[user_id] = quota
        return quota


class MockUoW:
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False

    async def __aenter__(self) -> "MockUoW":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_type is not None:
            self.rolled_back = True

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


class MockRefreshTokenRepository:
    def __init__(self) -> None:
        self.revoked_users: list[str] = []

    async def save_refresh_token(
        self, token_hash: str, user_id: str, family_id: str, expires_days: int | None = None
    ) -> None:
        pass

    async def get_refresh_token(self, token_hash: str) -> dict[str, Any] | None:
        return None

    async def revoke_refresh_token(self, token_hash: str) -> None:
        pass

    async def revoke_family(self, family_id: str) -> None:
        pass

    async def revoke_all_for_user(self, user_id: str) -> None:
        self.revoked_users.append(user_id)


# --- Unit Tests ---


@pytest.mark.asyncio
async def test_update_profile_successfully() -> None:
    repo = InMemoryUserRepository()
    uow = MockUoW()
    user_id = uuid.uuid4()
    user = DummyUser(
        user_id=user_id,
        email="test@focusflow.vn",
        password_hash="argon2_hash",
        full_name="Nguyễn Văn A",
        timezone="Asia/Ho_Chi_Minh",
    )
    repo.users[user_id] = user

    use_case = UpdateProfileUseCase(user_repo=repo, uow=uow)
    dto = UpdateProfileRequestDTO(full_name="Trần Thị B", timezone="Asia/Tokyo")

    result = await use_case.execute(user_id=user_id, dto=dto)

    assert isinstance(result, ProfileResponseDTO)
    assert result.id == str(user_id)
    assert result.email == "test@focusflow.vn"
    assert result.full_name == "Trần Thị B"
    assert result.timezone == "Asia/Tokyo"
    assert user.full_name == "Trần Thị B"
    assert user.timezone == "Asia/Tokyo"
    assert uow.committed is True

    # Test GetProfileUseCase
    get_uc = GetProfileUseCase(user_repo=repo)
    fetched = await get_uc.execute(user_id=user_id)
    assert fetched.full_name == "Trần Thị B"
    assert fetched.timezone == "Asia/Tokyo"


def test_update_profile_with_invalid_timezone_raises_validation_error() -> None:
    with pytest.raises(ValidationError) as exc_info:
        UpdateProfileRequestDTO(
            full_name="Nguyễn Văn A",
            timezone="Mars/Olympus_Mons",
        )
    assert "not a valid IANA timezone" in str(exc_info.value)


def test_update_profile_with_invalid_name_length_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        UpdateProfileRequestDTO(
            full_name="A",  # Less than min_length=2
            timezone="Asia/Ho_Chi_Minh",
        )


@pytest.mark.asyncio
async def test_get_ai_quota_calculates_remaining_calls_correctly() -> None:
    repo = InMemoryUserRepository()
    uow = MockUoW()
    user_id = uuid.uuid4()
    user = DummyUser(
        user_id=user_id,
        email="learner@focusflow.vn",
        password_hash="hash",
        full_name="Learner One",
        tier="FREE",
    )
    repo.users[user_id] = user

    # 1. Quota doesn't exist yet -> Initializes default with monthly_limit=30
    use_case = GetQuotaUseCase(user_repo=repo, uow=uow)
    res_init = await use_case.execute(user_id=user_id)
    assert isinstance(res_init, AIQuotaResponseDTO)
    assert res_init.monthly_limit == 30
    assert res_init.used_calls == 0
    assert res_init.reserved_calls == 0
    assert res_init.remaining_calls == 30

    # 2. Quota with usage and reservation
    quota = repo.quotas[user_id]
    quota.used_calls = 12
    quota.reserved_calls = 3
    quota.tokens_consumed = 45000

    res_used = await use_case.execute(user_id=user_id)
    # Remaining: 30 - 12 - 3 = 15
    assert res_used.remaining_calls == 15
    assert res_used.tokens_consumed == 45000

    # 3. Quota exhausted/over-reserved -> Remaining calls cannot be negative (floor at 0)
    quota.used_calls = 28
    quota.reserved_calls = 5
    res_exhausted = await use_case.execute(user_id=user_id)
    assert res_exhausted.remaining_calls == 0


@pytest.mark.asyncio
async def test_change_password_successfully_and_rejects_incorrect_password() -> None:
    repo = InMemoryUserRepository()
    uow = MockUoW()
    refresh_repo = MockRefreshTokenRepository()
    user_id = uuid.uuid4()

    old_pw = "CurrentSecret123!"
    old_hash = PasswordHasher.hash_password(old_pw)

    user = DummyUser(
        user_id=user_id,
        email="learner@focusflow.vn",
        password_hash=old_hash,
        full_name="Password Changer",
    )
    repo.users[user_id] = user

    use_case = ChangePasswordUseCase(
        user_repo=repo,
        uow=uow,
        refresh_token_repo=refresh_repo,
    )

    # 1. Reject incorrect current password
    bad_dto = ChangePasswordRequestDTO(
        current_password="WrongOldPassword!",
        new_password="NewSecurePass456@",
    )
    with pytest.raises(ValueError, match="Mật khẩu hiện tại không chính xác"):
        await use_case.execute(user_id=user_id, dto=bad_dto)

    # Ensure password remained unchanged
    assert user.password_hash == old_hash
    assert str(user_id) not in refresh_repo.revoked_users

    # 2. Successfully change password
    good_dto = ChangePasswordRequestDTO(
        current_password="CurrentSecret123!",
        new_password="NewSecurePass456@",
    )
    result = await use_case.execute(user_id=user_id, dto=good_dto)

    assert "message" in result
    assert uow.committed is True
    # Verify that new hash matches new password and does NOT match old password
    assert PasswordHasher.verify_password("NewSecurePass456@", user.password_hash) is True
    assert PasswordHasher.verify_password("CurrentSecret123!", user.password_hash) is False
    # Verify user sessions were revoked
    assert str(user_id) in refresh_repo.revoked_users


def test_change_password_dto_validation() -> None:
    # Too short (< 8 chars)
    with pytest.raises(ValidationError):
        ChangePasswordRequestDTO(
            current_password="any",
            new_password="Short1!",
        )

    # Missing uppercase
    with pytest.raises(ValidationError, match="in hoa"):
        ChangePasswordRequestDTO(
            current_password="any",
            new_password="alllowercase123!",
        )

    # Missing lowercase
    with pytest.raises(ValidationError, match="in thường"):
        ChangePasswordRequestDTO(
            current_password="any",
            new_password="ALLLUPPERCASE123!",
        )

    # Missing digit
    with pytest.raises(ValidationError, match="chữ số"):
        ChangePasswordRequestDTO(
            current_password="any",
            new_password="OnlyLettersNoDigits!",
        )

    # Missing special character
    with pytest.raises(ValidationError, match="ký tự đặc biệt"):
        ChangePasswordRequestDTO(
            current_password="any",
            new_password="NoSpecialChars1234",
        )
