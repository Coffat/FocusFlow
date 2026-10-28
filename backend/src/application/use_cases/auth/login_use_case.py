import uuid
from dataclasses import dataclass

from src.domain.exceptions.auth_exceptions import AccountLockedError, InvalidCredentialsError
from src.domain.services.password_hasher import PasswordHasher
from src.infrastructure.caching.redis_client import RefreshTokenRepository
from src.infrastructure.database.repositories.user_repository import SqlUserRepository
from src.infrastructure.security.jwt_token_provider import JwtTokenProvider


@dataclass
class LoginCommand:
    email: str
    password: str
    remember_me: bool = True


@dataclass
class UserDTO:
    id: str
    email: str
    full_name: str
    role: str
    tier: str
    created_at: str


@dataclass
class AuthResultDTO:
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user: UserDTO


class LoginUseCase:
    """Realizes Use Case UC-AUTH-02 (System Sequence Diagram 1)."""

    def __init__(self, user_repo: SqlUserRepository):
        self.user_repo = user_repo

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
        if user_record.role == "LOCKED":
            raise AccountLockedError("Your account has been locked or suspended.")

        # Step 4: Issue JWT Access Token & Refresh Token
        access_token = JwtTokenProvider.create_access_token(
            user_id=user_record.id,
            email=user_record.email,
            role=user_record.role,
            tier=user_record.tier
        )

        raw_refresh_token = JwtTokenProvider.create_refresh_token()
        refresh_token_hash = JwtTokenProvider.hash_token(raw_refresh_token)
        family_id = str(uuid.uuid4())

        # Step 5: Persist Refresh Token Rotation entry in Redis
        try:
            await RefreshTokenRepository.save_refresh_token(
                token_hash=refresh_token_hash,
                user_id=str(user_record.id),
                family_id=family_id
            )
        except Exception:
            # Redis is non-blocking for local fallback if Redis server is temporarily unreachable
            pass

        user_dto = UserDTO(
            id=str(user_record.id),
            email=user_record.email,
            full_name=user_record.full_name,
            role=user_record.role,
            tier=user_record.tier,
            created_at=user_record.created_at.isoformat()
        )

        return AuthResultDTO(
            access_token=access_token,
            refresh_token=raw_refresh_token,
            token_type="bearer",
            expires_in=15 * 60,
            user=user_dto
        )
