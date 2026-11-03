from uuid import UUID

from src.account.application.dtos.auth import (
    AuthResultDTO,
    RefreshTokenCommand,
    UserDTO,
)
from src.account.application.ports.auth_ports import (
    RefreshTokenRepositoryPort,
    TokenProviderPort,
)
from src.account.application.ports.user_repository_port import UserRepositoryPort
from src.account.domain.exceptions.auth_exceptions import (
    AccountLockedError,
    InvalidTokenError,
)


class RefreshTokenUseCase:
    """
    Implements Refresh Token Rotation (RTR) per ADR-008.
    Validates token hash against Redis, invalidates consumed token,
    issues a fresh JWT and refresh token within the same token family.
    """

    def __init__(
        self,
        user_repo: UserRepositoryPort,
        token_provider: TokenProviderPort,
        refresh_token_repo: RefreshTokenRepositoryPort,
    ) -> None:
        self.user_repo = user_repo
        self.token_provider = token_provider
        self.refresh_token_repo = refresh_token_repo

    async def execute(self, cmd: RefreshTokenCommand) -> AuthResultDTO:
        if not cmd.raw_refresh_token:
            raise InvalidTokenError("Refresh token is required.")

        token_hash = self.token_provider.hash_token(cmd.raw_refresh_token)

        # 1. Fetch token session from Redis
        token_data = await self.refresh_token_repo.get_refresh_token(token_hash)
        if not token_data:
            raise InvalidTokenError("Refresh token has expired or has already been used.")

        user_id_str = token_data.get("user_id")
        family_id = token_data.get("family_id")

        if not user_id_str or not family_id:
            raise InvalidTokenError("Corrupted token session metadata.")

        # 2. Consume existing token (Rotation)
        await self.refresh_token_repo.revoke_refresh_token(token_hash)

        # 3. Verify user in database
        try:
            user_uuid = UUID(user_id_str)
        except ValueError as exc:
            raise InvalidTokenError("Invalid user identifier in token.") from exc

        user_record = await self.user_repo.find_by_id(user_uuid)
        if user_record is None:
            raise InvalidTokenError("User associated with this token no longer exists.")

        is_locked = getattr(user_record, "is_locked", False)
        if user_record.role == "LOCKED" or is_locked is True:
            # If user locked, revoke entire token family
            await self.refresh_token_repo.revoke_family(family_id)
            raise AccountLockedError("Your account has been locked or suspended.")

        # 4. Issue new Access Token (15m)
        access_token = self.token_provider.create_access_token(
            user_id=user_record.id,
            email=user_record.email,
            role=user_record.role,
            tier=user_record.tier,
        )

        # 5. Issue new Refresh Token (7 days) and save in Redis with same family_id
        new_raw_refresh = self.token_provider.create_refresh_token()
        new_token_hash = self.token_provider.hash_token(new_raw_refresh)

        try:
            await self.refresh_token_repo.save_refresh_token(
                token_hash=new_token_hash, user_id=str(user_record.id), family_id=family_id
            )
        except Exception:
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
            refresh_token=new_raw_refresh,
            token_type="bearer",
            expires_in=15 * 60,
            user=user_dto,
        )
