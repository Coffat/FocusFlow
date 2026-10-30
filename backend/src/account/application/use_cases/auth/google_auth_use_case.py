import secrets
import uuid

from src.account.application.dtos.auth import (
    AuthResultDTO,
    GoogleAuthCommand,
    UserDTO,
)
from src.account.application.ports.auth_ports import (
    GoogleAuthPort,
    RefreshTokenRepositoryPort,
    TokenProviderPort,
)
from src.account.application.ports.user_repository_port import UserRepositoryPort
from src.account.domain.exceptions.auth_exceptions import (
    AccountLockedError,
    InvalidCredentialsError,
)
from src.account.domain.models.user import User
from src.account.domain.services.password_hasher import PasswordHasher
from src.shared_kernel.application.uow import AsyncUnitOfWork


class GoogleAuthUseCase:
    """Realizes Google OAuth SSO authentication (Sign In / Auto-registration)."""

    def __init__(
        self,
        user_repo: UserRepositoryPort,
        auth_service: GoogleAuthPort,
        token_provider: TokenProviderPort,
        refresh_token_repo: RefreshTokenRepositoryPort,
        uow: AsyncUnitOfWork,
    ) -> None:
        self.user_repo = user_repo
        self.auth_service = auth_service
        self.token_provider = token_provider
        self.refresh_token_repo = refresh_token_repo
        self.uow = uow

    async def execute(self, cmd: GoogleAuthCommand) -> AuthResultDTO:
        """Verifies Google credential, provisions new account if absent, and returns JWT tokens."""
        if not cmd.id_token and not cmd.access_token:
            raise InvalidCredentialsError(
                "Either Google id_token or access_token must be provided."
            )

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

        if user_record is not None:
            # Check account status
            is_locked = getattr(user_record, "is_locked", False)
            if user_record.role == "LOCKED" or is_locked is True:
                raise AccountLockedError("Your account has been locked or suspended.")
        else:
            # Step 3: Auto-provision new learner entity and default AI quota allocation
            random_secret = secrets.token_urlsafe(32)
            password_hash = PasswordHasher.hash_password(random_secret)

            new_user = User(
                id=uuid.uuid4(),
                email=email,
                password_hash=password_hash,
                full_name=name,
                timezone="Asia/Ho_Chi_Minh",
                role="LEARNER",
                tier="FREE",
            )

            async with self.uow:
                user_record = await self.user_repo.create_user_with_quota(new_user)
                await self.uow.commit()

        # Step 4: Issue FocusFlow JWT Access Token (15m) & Refresh Token (7d)
        access_token = self.token_provider.create_access_token(
            user_id=user_record.id,
            email=user_record.email,
            role=user_record.role,
            tier=user_record.tier,
        )

        raw_refresh_token = self.token_provider.create_refresh_token()
        refresh_token_hash = self.token_provider.hash_token(raw_refresh_token)
        family_id = str(uuid.uuid4())

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
