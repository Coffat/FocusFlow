import uuid
from dataclasses import dataclass
from uuid import UUID

from src.application.use_cases.auth.login_use_case import AuthResultDTO, UserDTO
from src.domain.exceptions.auth_exceptions import (
    AccountLockedError,
    InvalidTokenError,
)
from src.infrastructure.caching.redis_client import RefreshTokenRepository
from src.infrastructure.database.repositories.user_repository import SqlUserRepository
from src.infrastructure.security.jwt_token_provider import JwtTokenProvider


@dataclass
class RefreshTokenCommand:
    raw_refresh_token: str


class RefreshTokenUseCase:
    """
    Implements Refresh Token Rotation (RTR) per ADR-008.
    Validates token hash against Redis, invalidates consumed token, issues a fresh JWT and refresh token within the same token family.
    """

    def __init__(self, user_repo: SqlUserRepository):
        self.user_repo = user_repo

    async def execute(self, cmd: RefreshTokenCommand) -> AuthResultDTO:
        if not cmd.raw_refresh_token:
            raise InvalidTokenError("Refresh token is required.")

        token_hash = JwtTokenProvider.hash_token(cmd.raw_refresh_token)

        # 1. Fetch token session from Redis
        token_data = await RefreshTokenRepository.get_refresh_token(token_hash)
        if not token_data:
            raise InvalidTokenError("Refresh token has expired or has already been used.")

        user_id_str = token_data.get("user_id")
        family_id = token_data.get("family_id")

        if not user_id_str or not family_id:
            raise InvalidTokenError("Corrupted token session metadata.")

        # 2. Consume existing token (Rotation)
        await RefreshTokenRepository.revoke_refresh_token(token_hash)

        # 3. Verify user in database
        try:
            user_uuid = UUID(user_id_str)
        except ValueError as exc:
            raise InvalidTokenError("Invalid user identifier in token.") from exc

        user_record = await self.user_repo.find_by_id(user_uuid)
        if user_record is None:
            raise InvalidTokenError("User associated with this token no longer exists.")

        if user_record.role == "LOCKED":
            # If user locked, revoke entire token family
            await RefreshTokenRepository.revoke_family(family_id)
            raise AccountLockedError("Your account has been locked or suspended.")

        # 4. Issue new Access Token (15m)
        access_token = JwtTokenProvider.create_access_token(
            user_id=user_record.id,
            email=user_record.email,
            role=user_record.role,
            tier=user_record.tier
        )

        # 5. Issue new Refresh Token (7 days) and save in Redis with same family_id
        new_raw_refresh = JwtTokenProvider.create_refresh_token()
        new_token_hash = JwtTokenProvider.hash_token(new_raw_refresh)

        try:
            await RefreshTokenRepository.save_refresh_token(
                token_hash=new_token_hash,
                user_id=str(user_record.id),
                family_id=family_id
            )
        except Exception:
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
            refresh_token=new_raw_refresh,
            token_type="bearer",
            expires_in=15 * 60,
            user=user_dto
        )
