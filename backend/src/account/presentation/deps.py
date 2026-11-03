from collections.abc import AsyncGenerator
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.account.application.ports.auth_ports import (
    EmailServicePort,
    GoogleAuthPort,
    OtpRepositoryPort,
    RefreshTokenRepositoryPort,
    TokenProviderPort,
)
from src.account.application.ports.availability_repository_port import (
    AvailabilityRepositoryPort,
)
from src.account.application.ports.user_repository_port import (
    UserRepositoryPort,
)
from src.account.application.use_cases.auth.google_auth_use_case import (
    GoogleAuthUseCase,
)
from src.account.application.use_cases.auth.login_use_case import (
    LoginUseCase,
)
from src.account.application.use_cases.auth.password_reset_otp_use_case import (
    ConfirmPasswordResetUseCase,
    RequestPasswordResetOtpUseCase,
    VerifyPasswordResetOtpUseCase,
)
from src.account.application.use_cases.auth.refresh_token_use_case import (
    RefreshTokenUseCase,
)
from src.account.application.use_cases.auth.register_otp_use_case import (
    RequestRegisterOtpUseCase,
    ResendRegisterOtpUseCase,
    VerifyRegisterOtpUseCase,
)
from src.account.application.use_cases.auth.register_use_case import (
    RegisterUseCase,
)
from src.account.application.use_cases.availability.get_availability_use_case import (
    GetAvailabilityUseCase,
)
from src.account.application.use_cases.availability.update_availability_use_case import (
    UpdateAvailabilityUseCase,
)
from src.account.domain.exceptions.auth_exceptions import (
    InvalidTokenError,
    TokenExpiredError,
)
from src.account.infrastructure.adapters.learner_profile_query_adapter import (
    LearnerProfileQueryAdapter,
)
from src.account.infrastructure.adapters.quota_facade_adapter import (
    QuotaFacadeAdapter,
)
from src.account.infrastructure.caching.otp_repository import OtpRepository
from src.account.infrastructure.caching.redis_client import RefreshTokenRepository
from src.account.infrastructure.orm.user_orm import UserORM
from src.account.infrastructure.repositories.availability_repository import (
    SqlAlchemyAvailabilityRepository,
)
from src.account.infrastructure.repositories.user_repository import (
    SqlAlchemyUserRepository,
)
from src.account.infrastructure.security.google_auth_service import (
    google_auth_service,
)
from src.account.infrastructure.security.jwt_token_provider import (
    JwtTokenProvider,
)
from src.account.presentation.tasks import dispatch_otp_email
from src.account.public_api import LearnerProfileQueryPort, QuotaFacadePort
from src.shared_kernel.application.uow import AsyncUnitOfWork
from src.shared_kernel.infrastructure.database.session import get_async_session
from src.shared_kernel.infrastructure.database.sqlalchemy_uow import (
    SqlAlchemyUnitOfWork,
)

security_bearer = HTTPBearer(auto_error=False)


class TaskiqEmailServiceAdapter:
    """Adapts email dispatch with Taskiq worker + immediate inline fallback."""

    async def send_otp_email(self, to_email: str, otp_code: str, purpose: str) -> None:
        await dispatch_otp_email(to_email=to_email, otp_code=otp_code, purpose=purpose)


# --- Database & Unit of Work Dependencies ---
async def get_account_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Composition root dependency for Account Bounded Context."""
    async for session in get_async_session():
        yield session


def get_account_uow(
    session: AsyncSession = Depends(get_account_db_session),
) -> AsyncUnitOfWork:
    return SqlAlchemyUnitOfWork(session)


# --- Port Adapter Providers ---
def get_user_repository(
    session: AsyncSession = Depends(get_account_db_session),
) -> UserRepositoryPort:
    return SqlAlchemyUserRepository(session)


def get_token_provider() -> TokenProviderPort:
    return JwtTokenProvider()


def get_refresh_token_repository() -> RefreshTokenRepositoryPort:
    return RefreshTokenRepository()


def get_otp_repository() -> OtpRepositoryPort:
    return OtpRepository()


def get_email_service() -> EmailServicePort:
    return TaskiqEmailServiceAdapter()


def get_google_auth_service() -> GoogleAuthPort:
    return google_auth_service


# --- Current User & Auth Dependency ---
async def get_current_user(
    request: Request,
    bearer: HTTPAuthorizationCredentials | None = Depends(security_bearer),
    session: AsyncSession = Depends(get_account_db_session),
) -> UserORM:
    """Extract and validate current authenticated user via JWT header or HttpOnly cookie."""
    token: str | None = None

    # Priority 1: Authorization Header (Bearer token)
    if bearer and bearer.credentials:
        token = bearer.credentials
    # Priority 2: Cookie fallback (ADR-008 SameSite Cookie)
    elif "access_token" in request.cookies:
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = JwtTokenProvider.decode_access_token(token)
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise InvalidTokenError("Missing subject in token.")
        user_id = UUID(user_id_str)
    except TokenExpiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please refresh your session.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except (InvalidTokenError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user_repo = SqlAlchemyUserRepository(session)
    user = await user_repo.find_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User associated with this token no longer exists.",
        )

    if user.role == "LOCKED" or user.is_locked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been locked or suspended.",
        )

    return user


def get_current_learner_id(
    current_user: UserORM = Depends(get_current_user),
) -> UUID:
    """Extract authenticated learner UUID from JWT session."""
    return current_user.id


# --- Use Case Dependencies ---
def get_login_use_case(
    user_repo: UserRepositoryPort = Depends(get_user_repository),
    token_provider: TokenProviderPort = Depends(get_token_provider),
    refresh_token_repo: RefreshTokenRepositoryPort = Depends(get_refresh_token_repository),
) -> LoginUseCase:
    return LoginUseCase(
        user_repo=user_repo,
        token_provider=token_provider,
        refresh_token_repo=refresh_token_repo,
    )


def get_google_auth_use_case(
    user_repo: UserRepositoryPort = Depends(get_user_repository),
    auth_service: GoogleAuthPort = Depends(get_google_auth_service),
    token_provider: TokenProviderPort = Depends(get_token_provider),
    refresh_token_repo: RefreshTokenRepositoryPort = Depends(get_refresh_token_repository),
    uow: AsyncUnitOfWork = Depends(get_account_uow),
) -> GoogleAuthUseCase:
    return GoogleAuthUseCase(
        user_repo=user_repo,
        auth_service=auth_service,
        token_provider=token_provider,
        refresh_token_repo=refresh_token_repo,
        uow=uow,
    )


def get_register_use_case(
    user_repo: UserRepositoryPort = Depends(get_user_repository),
    token_provider: TokenProviderPort = Depends(get_token_provider),
    refresh_token_repo: RefreshTokenRepositoryPort = Depends(get_refresh_token_repository),
    uow: AsyncUnitOfWork = Depends(get_account_uow),
) -> RegisterUseCase:
    return RegisterUseCase(
        user_repo=user_repo,
        token_provider=token_provider,
        refresh_token_repo=refresh_token_repo,
        uow=uow,
    )


def get_request_register_otp_use_case(
    user_repo: UserRepositoryPort = Depends(get_user_repository),
    otp_repo: OtpRepositoryPort = Depends(get_otp_repository),
    email_service: EmailServicePort = Depends(get_email_service),
) -> RequestRegisterOtpUseCase:
    return RequestRegisterOtpUseCase(
        user_repo=user_repo,
        otp_repo=otp_repo,
        email_service=email_service,
    )


def get_resend_register_otp_use_case(
    user_repo: UserRepositoryPort = Depends(get_user_repository),
    otp_repo: OtpRepositoryPort = Depends(get_otp_repository),
    email_service: EmailServicePort = Depends(get_email_service),
) -> ResendRegisterOtpUseCase:
    return ResendRegisterOtpUseCase(
        user_repo=user_repo,
        otp_repo=otp_repo,
        email_service=email_service,
    )


def get_verify_register_otp_use_case(
    user_repo: UserRepositoryPort = Depends(get_user_repository),
    otp_repo: OtpRepositoryPort = Depends(get_otp_repository),
    token_provider: TokenProviderPort = Depends(get_token_provider),
    refresh_token_repo: RefreshTokenRepositoryPort = Depends(get_refresh_token_repository),
    uow: AsyncUnitOfWork = Depends(get_account_uow),
) -> VerifyRegisterOtpUseCase:
    return VerifyRegisterOtpUseCase(
        user_repo=user_repo,
        otp_repo=otp_repo,
        token_provider=token_provider,
        refresh_token_repo=refresh_token_repo,
        uow=uow,
    )


def get_request_password_reset_otp_use_case(
    user_repo: UserRepositoryPort = Depends(get_user_repository),
    otp_repo: OtpRepositoryPort = Depends(get_otp_repository),
    email_service: EmailServicePort = Depends(get_email_service),
) -> RequestPasswordResetOtpUseCase:
    return RequestPasswordResetOtpUseCase(
        user_repo=user_repo,
        otp_repo=otp_repo,
        email_service=email_service,
    )


def get_verify_password_reset_otp_use_case(
    user_repo: UserRepositoryPort = Depends(get_user_repository),
    otp_repo: OtpRepositoryPort = Depends(get_otp_repository),
) -> VerifyPasswordResetOtpUseCase:
    return VerifyPasswordResetOtpUseCase(
        user_repo=user_repo,
        otp_repo=otp_repo,
    )


def get_confirm_password_reset_use_case(
    user_repo: UserRepositoryPort = Depends(get_user_repository),
    otp_repo: OtpRepositoryPort = Depends(get_otp_repository),
    uow: AsyncUnitOfWork = Depends(get_account_uow),
) -> ConfirmPasswordResetUseCase:
    return ConfirmPasswordResetUseCase(
        user_repo=user_repo,
        otp_repo=otp_repo,
        uow=uow,
    )


def get_refresh_token_use_case(
    user_repo: UserRepositoryPort = Depends(get_user_repository),
    token_provider: TokenProviderPort = Depends(get_token_provider),
    refresh_token_repo: RefreshTokenRepositoryPort = Depends(get_refresh_token_repository),
) -> RefreshTokenUseCase:
    return RefreshTokenUseCase(
        user_repo=user_repo,
        token_provider=token_provider,
        refresh_token_repo=refresh_token_repo,
    )


# --- Availability Dependencies ---
def get_availability_repository(
    session: AsyncSession = Depends(get_account_db_session),
) -> AvailabilityRepositoryPort:
    return SqlAlchemyAvailabilityRepository(session)


def get_get_availability_use_case(
    repository: AvailabilityRepositoryPort = Depends(get_availability_repository),
) -> GetAvailabilityUseCase:
    return GetAvailabilityUseCase(repository=repository)


def get_update_availability_use_case(
    repository: AvailabilityRepositoryPort = Depends(get_availability_repository),
    uow: AsyncUnitOfWork = Depends(get_account_uow),
) -> UpdateAvailabilityUseCase:
    return UpdateAvailabilityUseCase(repository=repository, uow=uow)


# --- Cross-Context Port Providers (Quota & Learner Profile) ---
def get_quota_facade(
    session: AsyncSession = Depends(get_account_db_session),
) -> QuotaFacadePort:
    return QuotaFacadeAdapter(session=session)


def get_learner_profile_query_port(
    session: AsyncSession = Depends(get_account_db_session),
) -> LearnerProfileQueryPort:
    return LearnerProfileQueryAdapter(session=session)
