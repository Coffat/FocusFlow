import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from src.application.use_cases.auth.login_use_case import AuthResultDTO, UserDTO
from src.domain.exceptions.auth_exceptions import UserAlreadyExistsError
from src.domain.services.password_hasher import PasswordHasher
from src.infrastructure.caching.redis_client import RefreshTokenRepository
from src.infrastructure.database.models.user_orm import AIQuotaORM, UserORM
from src.infrastructure.database.repositories.user_repository import SqlUserRepository
from src.infrastructure.security.jwt_token_provider import JwtTokenProvider


@dataclass
class RegisterCommand:
    full_name: str
    email: str
    password: str


class RegisterUseCase:
    """Realizes User Registration (UC-AUTH-01)."""

    def __init__(self, user_repo: SqlUserRepository):
        self.user_repo = user_repo

    async def execute(self, cmd: RegisterCommand) -> AuthResultDTO:
        clean_email = cmd.email.lower().strip()
        existing = await self.user_repo.find_by_email(clean_email)
        if existing is not None:
            raise UserAlreadyExistsError("An account with this email address already exists.")

        # Hash password with Argon2id
        hashed_password = PasswordHasher.hash_password(cmd.password)

        new_user = UserORM(
            id=uuid.uuid4(),
            email=clean_email,
            password_hash=hashed_password,
            full_name=cmd.full_name.strip(),
            timezone="Asia/Ho_Chi_Minh",
            role="LEARNER",
            tier="FREE"
        )

        now = datetime.now(UTC)
        cycle_end = now + timedelta(days=30)
        default_quota = AIQuotaORM(
            id=uuid.uuid4(),
            user_id=new_user.id,
            monthly_limit=30,
            used_calls=0,
            reserved_calls=0,
            tokens_consumed=0,
            cycle_start=now,
            cycle_end=cycle_end
        )

        saved_user = await self.user_repo.create_user_with_quota(new_user, default_quota)

        # Issue JWT Access Token & Refresh Token
        access_token = JwtTokenProvider.create_access_token(
            user_id=saved_user.id,
            email=saved_user.email,
            role=saved_user.role,
            tier=saved_user.tier
        )

        raw_refresh_token = JwtTokenProvider.create_refresh_token()
        refresh_token_hash = JwtTokenProvider.hash_token(raw_refresh_token)
        family_id = str(uuid.uuid4())

        try:
            await RefreshTokenRepository.save_refresh_token(
                token_hash=refresh_token_hash,
                user_id=str(saved_user.id),
                family_id=family_id
            )
        except Exception:
            pass

        user_dto = UserDTO(
            id=str(saved_user.id),
            email=saved_user.email,
            full_name=saved_user.full_name,
            role=saved_user.role,
            tier=saved_user.tier,
            created_at=saved_user.created_at.isoformat()
        )

        return AuthResultDTO(
            access_token=access_token,
            refresh_token=raw_refresh_token,
            token_type="bearer",
            expires_in=15 * 60,
            user=user_dto
        )
