import uuid

from src.account.application.dtos.auth import AuthResultDTO, RegisterCommand, UserDTO
from src.account.application.ports.auth_ports import (
    RefreshTokenRepositoryPort,
    TokenProviderPort,
)
from src.account.application.ports.user_repository_port import UserRepositoryPort
from src.account.domain.exceptions.auth_exceptions import UserAlreadyExistsError
from src.account.domain.models.user import User
from src.account.domain.services.password_hasher import PasswordHasher
from src.shared_kernel.application.uow import AsyncUnitOfWork


class RegisterUseCase:
    """Realizes User Registration (UC-AUTH-01)."""

    def __init__(
        self,
        user_repo: UserRepositoryPort,
        token_provider: TokenProviderPort,
        refresh_token_repo: RefreshTokenRepositoryPort,
        uow: AsyncUnitOfWork,
    ) -> None:
        self.user_repo = user_repo
        self.token_provider = token_provider
        self.refresh_token_repo = refresh_token_repo
        self.uow = uow

    async def execute(self, cmd: RegisterCommand) -> AuthResultDTO:
        clean_email = cmd.email.lower().strip()
        existing = await self.user_repo.find_by_email(clean_email)
        if existing is not None:
            raise UserAlreadyExistsError("An account with this email address already exists.")

        # Hash password with Argon2id
        hashed_password = PasswordHasher.hash_password(cmd.password)

        new_user = User(
            id=uuid.uuid4(),
            email=clean_email,
            password_hash=hashed_password,
            full_name=cmd.full_name.strip(),
            timezone="Asia/Ho_Chi_Minh",
            role="LEARNER",
            tier="FREE",
        )

        async with self.uow:
            saved_user = await self.user_repo.create_user_with_quota(new_user)
            await self.uow.commit()

        # Issue JWT Access Token & Refresh Token
        access_token = self.token_provider.create_access_token(
            user_id=saved_user.id,
            email=saved_user.email,
            role=saved_user.role,
            tier=saved_user.tier,
        )

        raw_refresh_token = self.token_provider.create_refresh_token()
        refresh_token_hash = self.token_provider.hash_token(raw_refresh_token)
        family_id = str(uuid.uuid4())

        try:
            await self.refresh_token_repo.save_refresh_token(
                token_hash=refresh_token_hash, user_id=str(saved_user.id), family_id=family_id
            )
        except Exception:
            pass

        created_at_str = (
            saved_user.created_at.isoformat()
            if hasattr(saved_user.created_at, "isoformat")
            else str(saved_user.created_at)
        )

        user_dto = UserDTO(
            id=str(saved_user.id),
            email=saved_user.email,
            full_name=saved_user.full_name,
            role=saved_user.role,
            tier=saved_user.tier,
            created_at=created_at_str,
        )

        return AuthResultDTO(
            access_token=access_token,
            refresh_token=raw_refresh_token,
            token_type="bearer",
            expires_in=15 * 60,
            user=user_dto,
        )
