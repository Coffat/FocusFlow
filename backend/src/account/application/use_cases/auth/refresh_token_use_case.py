from uuid import UUID

import structlog

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
    SessionStoreUnavailableError,
)

_logger = structlog.get_logger(__name__)


class RefreshTokenUseCase:
    """
    Implements Refresh Token Rotation (RTR) with atomic reuse detection per ADR-008.
    Validates token hash against Redis via atomic Lua scripts, detects replay of
    already-rotated tokens (revoking the entire compromised session family),
    preserves bounded family TTL, and issues a fresh JWT + refresh token pair.
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
        token_hash_prefix = token_hash[:12]

        use_atomic = hasattr(self.refresh_token_repo, "inspect_refresh_token_atomic") and hasattr(
            self.refresh_token_repo, "rotate_refresh_token_atomic"
        )

        # 1. Inspect token session in Redis (atomically revoking family on reuse)
        if use_atomic:
            try:
                inspect_res = await self.refresh_token_repo.inspect_refresh_token_atomic(token_hash)
            except SessionStoreUnavailableError:
                raise
            except (ConnectionError, TimeoutError, OSError) as exc:
                raise SessionStoreUnavailableError() from exc
            if inspect_res.status == "REUSE_DETECTED":
                _logger.warning(
                    "refresh_token_reuse_detected",
                    stage="inspect",
                    token_hash_prefix=token_hash_prefix,
                    family_id=inspect_res.family_id,
                    user_id=inspect_res.user_id,
                )
                raise InvalidTokenError(
                    "Refresh token reuse detected. Session family has been revoked."
                )
            if inspect_res.status == "FAMILY_REVOKED":
                raise InvalidTokenError("Session has been revoked. Please log in again.")
            if inspect_res.status == "CORRUPTED":
                raise InvalidTokenError("Corrupted token session metadata.")
            if inspect_res.status != "ACTIVE":
                raise InvalidTokenError("Refresh token has expired or has already been used.")

            user_id_str = inspect_res.user_id
            family_id = inspect_res.family_id
        else:
            # Compatibility path for legacy in-memory test doubles lacking atomic methods
            token_data = await self.refresh_token_repo.get_refresh_token(token_hash)
            if not token_data:
                raise InvalidTokenError("Refresh token has expired or has already been used.")
            user_id_str = token_data.get("user_id")
            family_id = token_data.get("family_id")
            await self.refresh_token_repo.revoke_refresh_token(token_hash)

        if not user_id_str or not family_id:
            raise InvalidTokenError("Corrupted token session metadata.")

        # 2. Verify user in database
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

        # 3. Issue new Access Token (15m) & replacement Refresh Token
        access_token = self.token_provider.create_access_token(
            user_id=user_record.id,
            email=user_record.email,
            role=user_record.role,
            tier=user_record.tier,
        )

        new_raw_refresh = self.token_provider.create_refresh_token()
        new_token_hash = self.token_provider.hash_token(new_raw_refresh)

        # 4. Atomically rotate in Redis (never swallow Redis failures!)
        if use_atomic:
            try:
                rotate_res = await self.refresh_token_repo.rotate_refresh_token_atomic(
                    old_token_hash=token_hash,
                    new_token_hash=new_token_hash,
                    user_id=str(user_record.id),
                    family_id=family_id,
                )
            except SessionStoreUnavailableError:
                raise
            except (ConnectionError, TimeoutError, OSError) as exc:
                raise SessionStoreUnavailableError() from exc

            if rotate_res.status == "REUSE_DETECTED":
                _logger.warning(
                    "refresh_token_reuse_detected",
                    stage="rotate",
                    token_hash_prefix=token_hash_prefix,
                    family_id=family_id,
                    user_id=str(user_record.id),
                )
                raise InvalidTokenError(
                    "Refresh token reuse detected. Session family has been revoked."
                )
            if rotate_res.status != "ROTATED":
                raise InvalidTokenError("Session has been revoked. Please log in again.")
        else:
            try:
                rotated = await self.refresh_token_repo.save_rotated_refresh_token(
                    token_hash=new_token_hash,
                    user_id=str(user_record.id),
                    family_id=family_id,
                )
            except SessionStoreUnavailableError:
                raise
            except (ConnectionError, TimeoutError, OSError) as exc:
                raise SessionStoreUnavailableError() from exc

            if not rotated:
                raise InvalidTokenError("Session has been revoked. Please log in again.")

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
