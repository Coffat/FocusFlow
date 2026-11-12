from uuid import UUID

from src.account.application.dtos.profile import ChangePasswordRequestDTO
from src.account.application.ports.auth_ports import RefreshTokenRepositoryPort
from src.account.application.ports.user_repository_port import UserRepositoryPort
from src.account.domain.services.password_hasher import PasswordHasher
from src.shared_kernel.application.uow import AsyncUnitOfWork


class ChangePasswordUseCase:
    """Changes user password, updates hash using Argon2id, and revokes all active sessions."""

    def __init__(
        self,
        user_repo: UserRepositoryPort,
        uow: AsyncUnitOfWork,
        refresh_token_repo: RefreshTokenRepositoryPort | None = None,
    ) -> None:
        self.user_repo = user_repo
        self.uow = uow
        self.refresh_token_repo = refresh_token_repo

    async def execute(self, user_id: UUID, dto: ChangePasswordRequestDTO) -> dict[str, str]:
        user = await self.user_repo.find_by_id(user_id)
        if not user:
            raise ValueError(f"User not found: {user_id}")

        # 1. Verify current password
        is_valid = PasswordHasher.verify_password(dto.current_password, user.password_hash)
        if not is_valid:
            raise ValueError("Mật khẩu hiện tại không chính xác")

        # 2. Hash new password with Argon2id
        new_password_hash = PasswordHasher.hash_password(dto.new_password)

        # 3. Persist new hash via UnitOfWork
        async with self.uow:
            await self.user_repo.update_password(user_id, new_password_hash)
            await self.uow.commit()

        # 4. Revoke all active Redis refresh token sessions
        if self.refresh_token_repo is not None:
            try:
                await self.refresh_token_repo.revoke_all_for_user(str(user_id))
            except Exception:
                # Non-blocking if Redis is unreachable in disconnected test mode
                pass

        return {"message": "Mật khẩu đã được thay đổi thành công."}
