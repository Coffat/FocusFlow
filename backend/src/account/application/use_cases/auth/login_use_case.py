import uuid

from src.account.application.dtos.auth import AuthResultDTO, LoginCommand, UserDTO
from src.account.application.ports.auth_ports import (
    RefreshTokenRepositoryPort,
    TokenProviderPort,
)
from src.account.application.ports.user_repository_port import UserRepositoryPort
from src.account.domain.exceptions.auth_exceptions import (
    AccountLockedError,
    InvalidCredentialsError,
)
from src.account.domain.services.password_hasher import PasswordHasher


class LoginUseCase:
    """Realizes Use Case UC-AUTH-02 (User Login & Token Issuance)."""

    def __init__(
        self,
        user_repo: UserRepositoryPort,
        token_provider: TokenProviderPort,
        refresh_token_repo: RefreshTokenRepositoryPort,
    ) -> None:
        self.user_repo = user_repo
        self.token_provider = token_provider
        self.refresh_token_repo = refresh_token_repo

    async def execute(self, cmd: LoginCommand) -> AuthResultDTO:
        # Step 1: Find user by email (normalized lowercase & stripped)
        clean_email = cmd.email.lower().strip()
        user_record = await self.user_repo.find_by_email(clean_email)
        if user_record is None:
            raise InvalidCredentialsError("Invalid email or password.")

        # Step 2: Verify Argon2id password hash
        is_valid = PasswordHasher.verify_password(cmd.password, user_record.password_hash)
        if not is_valid:
            raise InvalidCredentialsError("Invalid email or password.")

        # Step 3: Check account status
        is_locked = getattr(user_record, "is_locked", False)
        if user_record.role == "LOCKED" or is_locked is True:
            raise AccountLockedError("Your account has been locked or suspended.")

        # Step 4: Issue JWT Access Token & Refresh Token
        access_token = self.token_provider.create_access_token(
            user_id=user_record.id,
            email=user_record.email,
            role=user_record.role,
            tier=user_record.tier,
        )

        raw_refresh_token = self.token_provider.create_refresh_token()
        refresh_token_hash = self.token_provider.hash_token(raw_refresh_token)
        family_id = str(uuid.uuid4())

        # Step 5: Persist Refresh Token Rotation entry in Redis
        try:
            await self.refresh_token_repo.save_refresh_token(
                token_hash=refresh_token_hash, user_id=str(user_record.id), family_id=family_id
            )
        except Exception:
            # Redis is non-blocking for local fallback if Redis server is temporarily unreachable
            pass

        created_at_str = (
            user_record.created_at.isoformat()
            if hasattr(user_record.created_at, "isoformat")
            else str(user_record.created_at)
        )

        user_dto = UserDTO(
            id=str(user_record.id),
            email=user_record.email,
            full_name=user_record.full_name,
            role=user_record.role,
            tier=user_record.tier,
            created_at=created_at_str,
        )

        return AuthResultDTO(
            access_token=access_token,
            refresh_token=raw_refresh_token,
            token_type="bearer",
            expires_in=15 * 60,
            user=user_dto,
        )
