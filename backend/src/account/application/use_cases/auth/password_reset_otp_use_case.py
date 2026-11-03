import secrets

from src.account.application.dtos.auth import (
    ConfirmPasswordResetCommand,
    RequestPasswordResetOtpCommand,
    VerifyPasswordResetOtpCommand,
    VerifyPasswordResetOtpResult,
)
from src.account.application.ports.auth_ports import (
    EmailServicePort,
    OtpRepositoryPort,
)
from src.account.application.ports.user_repository_port import UserRepositoryPort
from src.account.domain.exceptions.auth_exceptions import (
    InvalidOtpError,
    RateLimitError,
)
from src.account.domain.services.password_hasher import PasswordHasher
from src.shared_kernel.application.uow import AsyncUnitOfWork


class RequestPasswordResetOtpUseCase:
    """Step 1: Request Password Reset OTP with Anti-Enumeration and Cooldown."""

    def __init__(
        self,
        user_repo: UserRepositoryPort,
        otp_repo: OtpRepositoryPort,
        email_service: EmailServicePort,
    ) -> None:
        self.user_repo = user_repo
        self.otp_repo = otp_repo
        self.email_service = email_service

    async def execute(self, cmd: RequestPasswordResetOtpCommand) -> str:
        clean_email = cmd.email.lower().strip()

        # 1. Look up user (Anti-Enumeration: do not leak whether account exists)
        user = await self.user_repo.find_by_email(clean_email)
        if user is None:
            return (
                "Nếu email tồn tại trong hệ thống, mã xác thực OTP đã được gửi đến hòm thư của bạn."
            )

        # 2. Check rate limit cooldown (60s)
        cooldown = await self.otp_repo.get_cooldown_remaining("reset_password", clean_email)
        if cooldown and cooldown > 0:
            raise RateLimitError(f"Vui lòng đợi {cooldown} giây trước khi yêu cầu gửi lại mã OTP.")

        # 3. Generate 6-digit CSPRNG OTP
        otp_code = self.otp_repo.generate_otp()

        # 4. Save in Redis with TTL
        await self.otp_repo.save_otp("reset_password", clean_email, otp_code)

        # 5. Dispatch email via SMTP/Console
        await self.email_service.send_otp_email(clean_email, otp_code, "reset_password")

        return "Mã xác thực đặt lại mật khẩu đã được gửi đến email của bạn."


class VerifyPasswordResetOtpUseCase:
    """Step 2: Verifies reset OTP from Redis, consumes it, and generates a single-use reset token."""

    def __init__(
        self,
        user_repo: UserRepositoryPort,
        otp_repo: OtpRepositoryPort,
    ) -> None:
        self.user_repo = user_repo
        self.otp_repo = otp_repo

    async def execute(self, cmd: VerifyPasswordResetOtpCommand) -> VerifyPasswordResetOtpResult:
        clean_email = cmd.email.lower().strip()

        # 1. Verify and consume OTP from Redis (Anti-Replay)
        is_valid, message, _ = await self.otp_repo.verify_and_consume_otp(
            purpose="reset_password", identifier=clean_email, user_otp=cmd.otp_code
        )
        if not is_valid:
            raise InvalidOtpError(message)

        # 2. Verify user exists
        user = await self.user_repo.find_by_email(clean_email)
        if user is None:
            raise InvalidOtpError("Tài khoản người dùng không còn tồn tại.")

        # 3. Generate single-use reset token valid for 10 minutes (600s)
        reset_token = secrets.token_urlsafe(32)
        await self.otp_repo.save_reset_token(reset_token, clean_email, ttl_seconds=600)

        return VerifyPasswordResetOtpResult(
            message="Xác thực mã OTP thành công. Vui lòng thiết lập mật khẩu mới.",
            reset_token=reset_token,
        )


class ConfirmPasswordResetUseCase:
    """Step 3: Verifies reset_token (or direct otp_code), hashes new password, updates PostgreSQL."""

    def __init__(
        self,
        user_repo: UserRepositoryPort,
        otp_repo: OtpRepositoryPort,
        uow: AsyncUnitOfWork,
    ) -> None:
        self.user_repo = user_repo
        self.otp_repo = otp_repo
        self.uow = uow

    async def execute(self, cmd: ConfirmPasswordResetCommand) -> str:
        clean_email = cmd.email.lower().strip()

        # Method A: Validate reset_token (Preferred multi-step flow)
        if cmd.reset_token:
            saved_email = await self.otp_repo.consume_reset_token(cmd.reset_token)
            if not saved_email or saved_email != clean_email:
                raise InvalidOtpError(
                    "Phiên đặt lại mật khẩu đã hết hạn hoặc không hợp lệ. Vui lòng thử lại từ đầu."
                )

        # Method B: Validate direct otp_code (Backward compatibility with single-step / tests)
        elif cmd.otp_code:
            is_valid, message, _ = await self.otp_repo.verify_and_consume_otp(
                purpose="reset_password", identifier=clean_email, user_otp=cmd.otp_code
            )
            if not is_valid:
                raise InvalidOtpError(message)
        else:
            raise InvalidOtpError("Mã xác thực hoặc token đặt lại mật khẩu là bắt buộc.")

        # Find user in PostgreSQL
        user = await self.user_repo.find_by_email(clean_email)
        if user is None:
            raise InvalidOtpError("Tài khoản người dùng không còn tồn tại.")

        # Hash new password with Argon2id
        new_password_hash = PasswordHasher.hash_password(cmd.new_password)

        async with self.uow:
            await self.user_repo.update_password(user.id, new_password_hash)
            await self.uow.commit()

        return "Mật khẩu đã được cập nhật thành công. Vui lòng đăng nhập lại."
