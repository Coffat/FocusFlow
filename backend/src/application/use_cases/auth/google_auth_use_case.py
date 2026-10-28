import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from src.application.use_cases.auth.login_use_case import AuthResultDTO, UserDTO
from src.domain.exceptions.auth_exceptions import AccountLockedError, InvalidCredentialsError
from src.domain.services.password_hasher import PasswordHasher
from src.infrastructure.caching.redis_client import RefreshTokenRepository
from src.infrastructure.database.models.user_orm import AIQuotaORM, UserORM
from src.infrastructure.database.repositories.user_repository import SqlUserRepository
from src.infrastructure.security.google_auth_service import GoogleAuthService, google_auth_service
from src.infrastructure.security.jwt_token_provider import JwtTokenProvider


@dataclass
class GoogleAuthCommand:
    """Command carrying Google ID Token or Access Token."""
    id_token: str | None = None
    access_token: str | None = None


class GoogleAuthUseCase:
    """Realizes Google OAuth SSO authentication (Sign In / Auto-registration)."""

    def __init__(
        self,
        user_repo: SqlUserRepository,
        auth_service: GoogleAuthService | None = None
    ):
        self.user_repo = user_repo
        self.auth_service = auth_service or google_auth_service

    async def execute(self, cmd: GoogleAuthCommand) -> AuthResultDTO:
        """Verifies Google credential, provisions new account if absent, and returns JWT tokens."""
        if not cmd.id_token and not cmd.access_token:
            raise InvalidCredentialsError("Either Google id_token or access_token must be provided.")

        # Step 1: Validate Google token
        if cmd.id_token:
            payload = self.auth_service.verify_id_token(cmd.id_token)
        else:
            payload = await self.auth_service.verify_access_token(cmd.access_token)  # type: ignore[arg-type]

        email = payload.get("email", "").strip().lower()
        if not email:
            raise InvalidCredentialsError("Google account does not provide an email address.")

        email_verified = payload.get("email_verified", True)
        if not email_verified:
            raise InvalidCredentialsError("Google email has not been verified.")

        name = payload.get("name", "").strip() or email.split("@")[0]

        # Step 2: Query user in database
        user_record = await self.user_repo.find_by_email(email)

        now = datetime.now(UTC)

        if user_record is not None:
            # Check account status
            if user_record.role == "LOCKED":
                raise AccountLockedError("Your account has been locked or suspended.")
        else:
            # Step 3: Auto-provision new learner entity and default AI quota allocation
            random_secret = secrets.token_urlsafe(32)
            password_hash = PasswordHasher.hash_password(random_secret)

            new_user = UserORM(
                email=email,
                password_hash=password_hash,
                full_name=name,
                timezone="Asia/Ho_Chi_Minh",
                role="LEARNER",
                tier="FREE",
                created_at=now,
                updated_at=now
            )

            quota = AIQuotaORM(
                monthly_limit=30,
                used_calls=0,
                reserved_calls=0,
                tokens_consumed=0,
                cycle_start=now,
                cycle_end=now + timedelta(days=30),
                updated_at=now
            )

            user_record = await self.user_repo.create_user_with_quota(new_user, quota)

        # Step 4: Issue FocusFlow JWT Access Token (15m) & Refresh Token (7d)
        access_token = JwtTokenProvider.create_access_token(
            user_id=user_record.id,
            email=user_record.email,
            role=user_record.role,
            tier=user_record.tier
        )

        raw_refresh_token = JwtTokenProvider.create_refresh_token()
        refresh_token_hash = JwtTokenProvider.hash_token(raw_refresh_token)
        family_id = str(uuid.uuid4())

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
