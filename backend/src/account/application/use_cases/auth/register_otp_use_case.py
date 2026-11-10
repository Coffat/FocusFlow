import uuid

from src.account.application.dtos.auth import (
    AuthResultDTO,
    RequestRegisterOtpCommand,
    ResendRegisterOtpCommand,
    UserDTO,
    VerifyRegisterOtpCommand,
)
from src.account.application.ports.auth_ports import (
    EmailServicePort,
    OtpRepositoryPort,
    RefreshTokenRepositoryPort,
    TokenProviderPort,
)
from src.account.application.ports.user_repository_port import UserRepositoryPort
from src.account.domain.exceptions.auth_exceptions import (
    InvalidOtpError,
    RateLimitError,
    UserAlreadyExistsError,
)
from src.account.domain.models.user import User
from src.account.domain.services.password_hasher import PasswordHasher
from src.shared_kernel.application.uow import AsyncUnitOfWork


class RequestRegisterOtpUseCase:
    """Step 1 of OTP Registration: Validates input, hashes password, saves OTP in Redis, and dispatches email."""

    def __init__(
        self,
        user_repo: UserRepositoryPort,
        otp_repo: OtpRepositoryPort,
        email_service: EmailServicePort,
    ) -> None:
        self.user_repo = user_repo
        self.otp_repo = otp_repo
        self.email_service = email_service

    async def execute(self, cmd: RequestRegisterOtpCommand) -> str:
        clean_email = cmd.email.lower().strip()

        # 1. Verify email uniqueness
        existing_user = await self.user_repo.find_by_email(clean_email)
        if existing_user is not None:
            raise UserAlreadyExistsError("An account with this email address already exists.")

        # 2. Check rate limit cooldown (60s)
        cooldown = await self.otp_repo.get_cooldown_remaining("register", clean_email)
        if cooldown and cooldown > 0:
            raise RateLimitError(f"Vui lòng đợi {cooldown} giây trước khi yêu cầu gửi lại mã OTP.")

        # 3. Hash password with Argon2id for temporary Redis storage
        password_hash = PasswordHasher.hash_password(cmd.password)

        # 4. Generate 6-digit CSPRNG OTP
        otp_code = self.otp_repo.generate_otp()

        # 5. Save in Redis with TTL
        payload = {
            "full_name": cmd.full_name.strip(),
            "email": clean_email,
            "password_hash": password_hash,
        }
        await self.otp_repo.save_otp("register", clean_email, otp_code, payload)

        # 6. Send verification email via SMTP/Console
        await self.email_service.send_otp_email(clean_email, otp_code, "register")

        return "Mã xác thực OTP đã được gửi đến email của bạn."


class ResendRegisterOtpUseCase:
    """Resends a new OTP for an active registration session in Redis."""

    def __init__(
        self,
        user_repo: UserRepositoryPort,
        otp_repo: OtpRepositoryPort,
        email_service: EmailServicePort,
    ) -> None:
        self.user_repo = user_repo
        self.otp_repo = otp_repo
        self.email_service = email_service

    async def execute(self, cmd: ResendRegisterOtpCommand) -> str:
        clean_email = cmd.email.lower().strip()

        # 1. Verify email uniqueness
        existing_user = await self.user_repo.find_by_email(clean_email)
        if existing_user is not None:
            raise UserAlreadyExistsError("An account with this email address already exists.")

        # 2. Check rate limit cooldown (60s)
        cooldown = await self.otp_repo.get_cooldown_remaining("register", clean_email)
        if cooldown and cooldown > 0:
            raise RateLimitError(f"Vui lòng đợi {cooldown} giây trước khi yêu cầu gửi lại mã OTP.")

        # 3. Retrieve existing registration session from Redis
        raw_session = await self.otp_repo.get_raw_session("register", clean_email)
        if not raw_session:
            raise InvalidOtpError("Phiên đăng ký đã hết hạn. Vui lòng quay lại trang Đăng ký.")

        payload = raw_session.get("payload", {})

        # 4. Generate new 6-digit OTP
        otp_code = self.otp_repo.generate_otp()

        # 5. Save in Redis with fresh TTL and restart cooldown
        await self.otp_repo.save_otp("register", clean_email, otp_code, payload)

        # 6. Send verification email
        await self.email_service.send_otp_email(clean_email, otp_code, "register")

        return "Mã xác thực mới đã được gửi đến email của bạn."


class VerifyRegisterOtpUseCase:
    """Step 2 of OTP Registration: Verifies OTP, persists user in PostgreSQL, and issues JWT tokens."""

    def __init__(
        self,
        user_repo: UserRepositoryPort,
        otp_repo: OtpRepositoryPort,
        token_provider: TokenProviderPort,
        refresh_token_repo: RefreshTokenRepositoryPort,
        uow: AsyncUnitOfWork,
    ) -> None:
        self.user_repo = user_repo
        self.otp_repo = otp_repo
        self.token_provider = token_provider
        self.refresh_token_repo = refresh_token_repo
        self.uow = uow

    async def execute(self, cmd: VerifyRegisterOtpCommand) -> AuthResultDTO:
        clean_email = cmd.email.lower().strip()

        # 1. Verify and consume OTP from Redis (Anti-Replay)
        is_valid, message, payload = await self.otp_repo.verify_and_consume_otp(
            purpose="register", identifier=clean_email, user_otp=cmd.otp_code
        )
        if not is_valid:
            raise InvalidOtpError(message)

        # 2. Check duplicate again
        existing_user = await self.user_repo.find_by_email(clean_email)
        if existing_user is not None:
            raise UserAlreadyExistsError("An account with this email address already exists.")

        # 3. Create persistent User in PostgreSQL
        new_user = User(
            id=uuid.uuid4(),
            email=clean_email,
            password_hash=payload["password_hash"],
            full_name=payload["full_name"],
            timezone="Asia/Ho_Chi_Minh",
            role="LEARNER",
            tier="FREE",
        )

        async with self.uow:
            saved_user = await self.user_repo.create_user_with_quota(new_user)
            await self.uow.commit()

        # 4. Issue JWT Access Token & Refresh Token
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
