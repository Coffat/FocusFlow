import secrets
from dataclasses import dataclass

from src.domain.exceptions.auth_exceptions import InvalidOtpError, RateLimitError
from src.domain.services.password_hasher import PasswordHasher
from src.infrastructure.caching.otp_repository import OtpRepository
from src.infrastructure.caching.redis_client import get_redis_client
from src.infrastructure.database.repositories.user_repository import SqlUserRepository
from src.infrastructure.email.email_service import EmailService


@dataclass
class RequestPasswordResetOtpCommand:
    email: str


@dataclass
class VerifyPasswordResetOtpCommand:
    email: str
    otp_code: str


@dataclass
class VerifyPasswordResetOtpResult:
    message: str
    reset_token: str


@dataclass
class ConfirmPasswordResetCommand:
    email: str
    new_password: str
    reset_token: str | None = None
    otp_code: str | None = None


class RequestPasswordResetOtpUseCase:
    """Step 1: Request Password Reset OTP with Anti-Enumeration and Cooldown."""

    def __init__(self, user_repo: SqlUserRepository):
        self.user_repo = user_repo

    async def execute(self, cmd: RequestPasswordResetOtpCommand) -> str:
        clean_email = cmd.email.lower().strip()

        # 1. Look up user (Anti-Enumeration: do not leak whether account exists)
        user = await self.user_repo.find_by_email(clean_email)
        if user is None:
            return "Nếu email tồn tại trong hệ thống, mã xác thực OTP đã được gửi đến hòm thư của bạn."

        # 2. Check 60s rate limit cooldown
        cooldown = await OtpRepository.get_cooldown_remaining("reset_password", clean_email)
        if cooldown and cooldown > 0:
            raise RateLimitError(f"Vui lòng đợi {cooldown} giây trước khi yêu cầu gửi lại mã OTP.")

        # 3. Generate 6-digit CSPRNG OTP
        otp_code = OtpRepository.generate_otp()

        # 4. Save in Redis with 3-minute TTL
        await OtpRepository.save_otp("reset_password", clean_email, otp_code)

        # 5. Dispatch email via Gmail SMTP
        await EmailService.send_otp_email(clean_email, otp_code, "reset_password")

        return "Mã xác thực đặt lại mật khẩu đã được gửi đến email của bạn."


class VerifyPasswordResetOtpUseCase:
    """Step 2: Verifies reset OTP from Redis, consumes it, and generates a single-use reset token."""

    def __init__(self, user_repo: SqlUserRepository):
        self.user_repo = user_repo

    async def execute(self, cmd: VerifyPasswordResetOtpCommand) -> VerifyPasswordResetOtpResult:
        clean_email = cmd.email.lower().strip()

        # 1. Verify and consume OTP from Redis (Anti-Replay)
        is_valid, message, _ = await OtpRepository.verify_and_consume_otp(
            purpose="reset_password",
            identifier=clean_email,
            user_otp=cmd.otp_code
        )
        if not is_valid:
            raise InvalidOtpError(message)

        # 2. Verify user exists
        user = await self.user_repo.find_by_email(clean_email)
        if user is None:
            raise InvalidOtpError("Tài khoản người dùng không còn tồn tại.")

        # 3. Generate single-use reset token valid for 10 minutes (600s)
        reset_token = secrets.token_urlsafe(32)
        client = get_redis_client()
        await client.set(f"password_reset_token:{reset_token}", clean_email, ex=600)

        return VerifyPasswordResetOtpResult(
            message="Xác thực mã OTP thành công. Vui lòng thiết lập mật khẩu mới.",
            reset_token=reset_token
        )


class ConfirmPasswordResetUseCase:
    """Step 3: Verifies reset_token (or legacy otp_code), hashes new password with Argon2id, and updates PostgreSQL."""

    def __init__(self, user_repo: SqlUserRepository):
        self.user_repo = user_repo

    async def execute(self, cmd: ConfirmPasswordResetCommand) -> str:
        clean_email = cmd.email.lower().strip()
        client = get_redis_client()

        # Method A: Validate reset_token (Preferred multi-step flow)
        if cmd.reset_token:
            token_key = f"password_reset_token:{cmd.reset_token}"
            saved_email = await client.get(token_key)
            if not saved_email or saved_email != clean_email:
                raise InvalidOtpError("Phiên đặt lại mật khẩu đã hết hạn hoặc không hợp lệ. Vui lòng thử lại từ đầu.")
            # Consume reset token immediately
            await client.delete(token_key)

        # Method B: Validate direct otp_code (Backward compatibility with single-step / tests)
        elif cmd.otp_code:
            is_valid, message, _ = await OtpRepository.verify_and_consume_otp(
                purpose="reset_password",
                identifier=clean_email,
                user_otp=cmd.otp_code
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
        user.password_hash = PasswordHasher.hash_password(cmd.new_password)
        await self.user_repo.session.commit()

        return "Mật khẩu đã được cập nhật thành công. Vui lòng đăng nhập lại."
