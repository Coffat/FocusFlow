import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from src.application.use_cases.auth.login_use_case import AuthResultDTO, UserDTO
from src.domain.exceptions.auth_exceptions import (
    InvalidOtpError,
    RateLimitError,
    UserAlreadyExistsError,
)
from src.domain.services.password_hasher import PasswordHasher
from src.infrastructure.caching.otp_repository import OtpRepository
from src.infrastructure.caching.redis_client import RefreshTokenRepository, get_redis_client
from src.infrastructure.database.models.user_orm import AIQuotaORM, UserORM
from src.infrastructure.database.repositories.user_repository import SqlUserRepository
from src.infrastructure.email.email_service import EmailService
from src.infrastructure.security.jwt_token_provider import JwtTokenProvider


@dataclass
class RequestRegisterOtpCommand:
    full_name: str
    email: str
    password: str


@dataclass
class ResendRegisterOtpCommand:
    email: str


@dataclass
class VerifyRegisterOtpCommand:
    email: str
    otp_code: str


class RequestRegisterOtpUseCase:
    """Step 1 of OTP Registration: Validates input, hashes password, saves OTP in Redis, and dispatches email."""

    def __init__(self, user_repo: SqlUserRepository):
        self.user_repo = user_repo

    async def execute(self, cmd: RequestRegisterOtpCommand) -> str:
        clean_email = cmd.email.lower().strip()

        # 1. Verify email uniqueness
        existing_user = await self.user_repo.find_by_email(clean_email)
        if existing_user is not None:
            raise UserAlreadyExistsError("An account with this email address already exists.")

        # 2. Check rate limit cooldown (60s)
        cooldown = await OtpRepository.get_cooldown_remaining("register", clean_email)
        if cooldown and cooldown > 0:
            raise RateLimitError(f"Vui lòng đợi {cooldown} giây trước khi yêu cầu gửi lại mã OTP.")

        # 3. Hash password with Argon2id for temporary Redis storage
        password_hash = PasswordHasher.hash_password(cmd.password)

        # 4. Generate 6-digit CSPRNG OTP
        otp_code = OtpRepository.generate_otp()

        # 5. Save in Redis with 3-minute TTL
        payload = {
            "full_name": cmd.full_name.strip(),
            "email": clean_email,
            "password_hash": password_hash
        }
        await OtpRepository.save_otp("register", clean_email, otp_code, payload)

        # 6. Send verification email via Gmail SMTP
        await EmailService.send_otp_email(clean_email, otp_code, "register")

        return "Mã xác thực OTP đã được gửi đến email của bạn."


class ResendRegisterOtpUseCase:
    """Resends a new OTP for an active registration session in Redis."""

    def __init__(self, user_repo: SqlUserRepository):
        self.user_repo = user_repo

    async def execute(self, cmd: ResendRegisterOtpCommand) -> str:
        clean_email = cmd.email.lower().strip()

        # 1. Verify email uniqueness
        existing_user = await self.user_repo.find_by_email(clean_email)
        if existing_user is not None:
            raise UserAlreadyExistsError("An account with this email address already exists.")

        # 2. Check rate limit cooldown (60s)
        cooldown = await OtpRepository.get_cooldown_remaining("register", clean_email)
        if cooldown and cooldown > 0:
            raise RateLimitError(f"Vui lòng đợi {cooldown} giây trước khi yêu cầu gửi lại mã OTP.")

        # 3. Retrieve existing registration session from Redis
        client = get_redis_client()
        raw_data = await client.get(f"otp:register:{clean_email}")
        if not raw_data:
            raise InvalidOtpError("Phiên đăng ký đã hết hạn. Vui lòng quay lại trang Đăng ký.")

        data = json.loads(raw_data)
        payload = data.get("payload", {})

        # 4. Generate new 6-digit OTP
        otp_code = OtpRepository.generate_otp()

        # 5. Save in Redis with fresh TTL (3 minutes) and restart cooldown (60s)
        await OtpRepository.save_otp("register", clean_email, otp_code, payload)

        # 6. Send verification email via Gmail SMTP
        await EmailService.send_otp_email(clean_email, otp_code, "register")

        return "Mã xác thực mới đã được gửi đến email của bạn."


class VerifyRegisterOtpUseCase:
    """Step 2 of OTP Registration: Verifies OTP, persists user in PostgreSQL, and issues JWT tokens."""

    def __init__(self, user_repo: SqlUserRepository):
        self.user_repo = user_repo

    async def execute(self, cmd: VerifyRegisterOtpCommand) -> AuthResultDTO:
        clean_email = cmd.email.lower().strip()

        # 1. Verify and consume OTP from Redis (Anti-Replay)
        is_valid, message, payload = await OtpRepository.verify_and_consume_otp(
            purpose="register",
            identifier=clean_email,
            user_otp=cmd.otp_code
        )
        if not is_valid:
            raise InvalidOtpError(message)

        # 2. Check duplicate again
        existing_user = await self.user_repo.find_by_email(clean_email)
        if existing_user is not None:
            raise UserAlreadyExistsError("An account with this email address already exists.")

        # 3. Create persistent User in PostgreSQL
        new_user = UserORM(
            id=uuid.uuid4(),
            email=clean_email,
            password_hash=payload["password_hash"],
            full_name=payload["full_name"],
            timezone="Asia/Ho_Chi_Minh",
            role="LEARNER",
            tier="FREE"
        )

        now = datetime.now(UTC)
        cycle_end = now + timedelta(days=30)
        default_quota = AIQuotaORM(
            id=uuid.uuid4(),
            user_id=new_user.id,
            monthly_limit=30,
            used_calls=0,
            reserved_calls=0,
            tokens_consumed=0,
            cycle_start=now,
            cycle_end=cycle_end
        )

        saved_user = await self.user_repo.create_user_with_quota(new_user, default_quota)

        # 4. Issue JWT Access Token & Refresh Token
        access_token = JwtTokenProvider.create_access_token(
            user_id=saved_user.id,
            email=saved_user.email,
            role=saved_user.role,
            tier=saved_user.tier
        )

        raw_refresh_token = JwtTokenProvider.create_refresh_token()
        refresh_token_hash = JwtTokenProvider.hash_token(raw_refresh_token)
        family_id = str(uuid.uuid4())

        try:
            await RefreshTokenRepository.save_refresh_token(
                token_hash=refresh_token_hash,
                user_id=str(saved_user.id),
                family_id=family_id
            )
        except Exception:
            pass

        user_dto = UserDTO(
            id=str(saved_user.id),
            email=saved_user.email,
            full_name=saved_user.full_name,
            role=saved_user.role,
            tier=saved_user.tier,
            created_at=saved_user.created_at.isoformat()
        )

        return AuthResultDTO(
            access_token=access_token,
            refresh_token=raw_refresh_token,
            token_type="bearer",
            expires_in=15 * 60,
            user=user_dto
        )
