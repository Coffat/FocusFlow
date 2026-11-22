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
from src.account.application.ports.calendar_connection_repository_port import (
    CalendarConnectionRepositoryPort,
)
from src.account.application.ports.learner_memory_repository_port import (
    LearnerMemoryRepositoryPort,
)
from src.account.application.ports.learner_profile_repository_port import (
    LearnerProfileRepositoryPort,
)
from src.account.application.ports.notification_repository_port import (
    NotificationRepositoryPort,
)
from src.account.application.ports.oauth_state_store_port import (
    OAuthStateStorePort,
)
from src.account.application.ports.payment_ports import (
    PaymentProviderPort,
    PaymentTransactionRepositoryPort,
)
from src.account.application.ports.user_repository_port import (
    UserRepositoryPort,
)
from src.account.application.ports.webcal_token_repository_port import (
    WebcalTokenRepositoryPort,
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
from src.account.application.use_cases.billing import (
    CreateBillingCheckoutUseCase,
    ListBillingTransactionsUseCase,
    SettlePaymentTransactionUseCase,
)
from src.account.application.use_cases.calendar import (
    DisconnectGoogleCalendarUseCase,
    GetCalendarConnectionStatusUseCase,
    GetWebcalIcsFeedUseCase,
    GetWebcalStatusUseCase,
    HandleGoogleCalendarOAuthCallbackUseCase,
    InitiateGoogleCalendarAuthUseCase,
    ProcessGoogleCalendarWebhookUseCase,
    ReconcileCalendarConnectionsUseCase,
    RenewExpiringCalendarWebhooksUseCase,
    RevokeWebcalTokenUseCase,
    RotateWebcalTokenUseCase,
    SyncScheduleBlocksToGoogleUseCase,
)
from src.account.application.use_cases.learner_memory import (
    ListLearnerMemoryUseCase,
    ResetLearnerMemoryUseCase,
    UpdateLearnerMemoryUseCase,
)
from src.account.application.use_cases.notifications import (
    ListNotificationsUseCase,
    MarkAllNotificationsReadUseCase,
    MarkNotificationReadUseCase,
)
from src.account.application.use_cases.profile import (
    ChangePasswordUseCase,
    ExportAccountDataUseCase,
    GetProfileUseCase,
    GetQuotaUseCase,
    UpdateProfileUseCase,
)
from src.account.domain.exceptions.auth_exceptions import (
    InvalidTokenError,
    TokenExpiredError,
)
from src.account.domain.ports.calendar_provider_port import (
    CalendarProviderError,
    CalendarProviderPort,
)
from src.account.infrastructure.adapters.google_calendar_adapter import (
    GoogleCalendarAdapter,
)
from src.account.infrastructure.adapters.learner_profile_query_adapter import (
    LearnerProfileQueryAdapter,
)
from src.account.infrastructure.adapters.payment_provider_adapter import (
    LocalMockPaymentAdapter,
)
from src.account.infrastructure.adapters.quota_facade_adapter import (
    QuotaFacadeAdapter,
)
from src.account.infrastructure.caching.oauth_state_store import RedisOAuthStateStore
from src.account.infrastructure.caching.otp_repository import OtpRepository
from src.account.infrastructure.caching.redis_client import RefreshTokenRepository
from src.account.infrastructure.orm.user_orm import UserORM
from src.account.infrastructure.repositories.availability_repository import (
    SqlAlchemyAvailabilityRepository,
)
from src.account.infrastructure.repositories.calendar_connection_repository import (
    SqlAlchemyCalendarConnectionRepository,
)
from src.account.infrastructure.repositories.learner_memory_repository import (
    SqlAlchemyLearnerMemoryRepository,
)
from src.account.infrastructure.repositories.learner_profile_repository import (
    SqlAlchemyLearnerProfileRepository,
)
from src.account.infrastructure.repositories.notification_repository import (
    SqlAlchemyNotificationRepository,
)
from src.account.infrastructure.repositories.payment_transaction_repository import (
    SqlAlchemyPaymentTransactionRepository,
)
from src.account.infrastructure.repositories.user_repository import (
    SqlAlchemyUserRepository,
)
from src.account.infrastructure.repositories.webcal_token_repository import (
    SqlAlchemyWebcalTokenRepository,
)
from src.account.infrastructure.security.google_auth_service import (
    google_auth_service,
)
from src.account.infrastructure.security.jwt_token_provider import (
    JwtTokenProvider,
)
from src.account.presentation.tasks import dispatch_otp_email
from src.account.public_api import LearnerProfileQueryPort, QuotaFacadePort
from src.execution.public_api import (
    ExecutionDashboardQueryPort,
    create_execution_dashboard_query_port,
)
from src.planning.public_api import (
    PlanningExecutionBridgePort,
    ScheduleBlockSyncPort,
    create_planning_execution_bridge,
    create_schedule_block_sync_port,
)
from src.shared_kernel.application.uow import AsyncUnitOfWork
from src.shared_kernel.config import get_settings
from src.shared_kernel.infrastructure.database.session import get_async_session
from src.shared_kernel.infrastructure.database.sqlalchemy_uow import (
    SqlAlchemyUnitOfWork,
)

security_bearer = HTTPBearer(auto_error=False)


class TaskiqEmailServiceAdapter:
    """Adapts email dispatch with Taskiq worker + immediate inline fallback."""

    async def send_otp_email(self, to_email: str, otp_code: str, purpose: str) -> None:
        await dispatch_otp_email(to_email=to_email, otp_code=otp_code, purpose=purpose)

    async def send_overdue_alert_email(
        self,
        to_email: str,
        overdue_task_titles: list[str],
        remaining_reschedule_budget: int,
    ) -> None:
        from src.account.infrastructure.email.email_service import EmailService

        await EmailService.send_overdue_alert_email(
            to_email=to_email,
            overdue_task_titles=overdue_task_titles,
            remaining_reschedule_budget=remaining_reschedule_budget,
        )


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


async def get_current_admin_user(
    current_user: UserORM = Depends(get_current_user),
) -> UserORM:
    """Require authenticated user with ADMIN role (ADR-008)."""
    if not current_user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user


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
    refresh_token_repo: RefreshTokenRepositoryPort = Depends(get_refresh_token_repository),
) -> ConfirmPasswordResetUseCase:
    return ConfirmPasswordResetUseCase(
        user_repo=user_repo,
        otp_repo=otp_repo,
        uow=uow,
        refresh_token_repo=refresh_token_repo,
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


def get_learner_memory_repository(
    session: AsyncSession = Depends(get_account_db_session),
) -> LearnerMemoryRepositoryPort:
    return SqlAlchemyLearnerMemoryRepository(session)


def get_list_learner_memory_use_case(
    repository: LearnerMemoryRepositoryPort = Depends(get_learner_memory_repository),
) -> ListLearnerMemoryUseCase:
    return ListLearnerMemoryUseCase(repository)


def get_update_learner_memory_use_case(
    repository: LearnerMemoryRepositoryPort = Depends(get_learner_memory_repository),
    uow: AsyncUnitOfWork = Depends(get_account_uow),
) -> UpdateLearnerMemoryUseCase:
    return UpdateLearnerMemoryUseCase(repository, uow)


def get_reset_learner_memory_use_case(
    repository: LearnerMemoryRepositoryPort = Depends(get_learner_memory_repository),
    uow: AsyncUnitOfWork = Depends(get_account_uow),
) -> ResetLearnerMemoryUseCase:
    return ResetLearnerMemoryUseCase(repository, uow)


# --- Cross-Context Port Providers (Quota & Learner Profile) ---
def get_quota_facade(
    session: AsyncSession = Depends(get_account_db_session),
) -> QuotaFacadePort:
    return QuotaFacadeAdapter(session=session)


def get_learner_profile_query_port(
    session: AsyncSession = Depends(get_account_db_session),
) -> LearnerProfileQueryPort:
    return LearnerProfileQueryAdapter(session=session)


# --- Calendar Integration Dependencies (UC-17) ---
def get_calendar_connection_repository(
    session: AsyncSession = Depends(get_account_db_session),
) -> CalendarConnectionRepositoryPort:
    return SqlAlchemyCalendarConnectionRepository(session)


def get_calendar_provider() -> CalendarProviderPort:
    settings = get_settings()
    provider_name = settings.calendar_provider.strip().lower()
    if provider_name not in ("google", "google_calendar"):
        raise CalendarProviderError(
            f"CALENDAR_PROVIDER_NOT_CONFIGURED: Unsupported calendar_provider={settings.calendar_provider!r}. Only 'google' is supported.",
            code="CALENDAR_PROVIDER_NOT_CONFIGURED",
        )
    if not settings.google_client_id.strip() or not settings.google_client_secret.strip():
        raise CalendarProviderError(
            "CALENDAR_OAUTH_NOT_CONFIGURED: Missing GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET.",
            code="CALENDAR_OAUTH_NOT_CONFIGURED",
        )
    return GoogleCalendarAdapter(settings=settings)


def get_oauth_state_store() -> OAuthStateStorePort:
    return RedisOAuthStateStore()


def get_initiate_google_calendar_auth_use_case(
    state_store: OAuthStateStorePort = Depends(get_oauth_state_store),
) -> InitiateGoogleCalendarAuthUseCase:
    settings = get_settings()
    return InitiateGoogleCalendarAuthUseCase(
        state_store=state_store,
        secret_key=settings.secret_key,
        settings=settings,
    )


def get_handle_google_calendar_oauth_callback_use_case(
    repo: CalendarConnectionRepositoryPort = Depends(get_calendar_connection_repository),
    provider: CalendarProviderPort = Depends(get_calendar_provider),
    state_store: OAuthStateStorePort = Depends(get_oauth_state_store),
    uow: AsyncUnitOfWork = Depends(get_account_uow),
) -> HandleGoogleCalendarOAuthCallbackUseCase:
    settings = get_settings()
    return HandleGoogleCalendarOAuthCallbackUseCase(
        repository=repo,
        calendar_provider=provider,
        state_store=state_store,
        secret_key=settings.secret_key,
        settings=settings,
        uow=uow,
    )


def get_get_calendar_connection_status_use_case(
    repo: CalendarConnectionRepositoryPort = Depends(get_calendar_connection_repository),
) -> GetCalendarConnectionStatusUseCase:
    return GetCalendarConnectionStatusUseCase(repository=repo)


def get_disconnect_google_calendar_use_case(
    repo: CalendarConnectionRepositoryPort = Depends(get_calendar_connection_repository),
    provider: CalendarProviderPort = Depends(get_calendar_provider),
    uow: AsyncUnitOfWork = Depends(get_account_uow),
) -> DisconnectGoogleCalendarUseCase:
    return DisconnectGoogleCalendarUseCase(
        repository=repo,
        calendar_provider=provider,
        uow=uow,
    )


def get_schedule_block_sync_port_dep(
    session: AsyncSession = Depends(get_async_session),
) -> ScheduleBlockSyncPort:
    return create_schedule_block_sync_port(session)


def get_sync_schedule_blocks_use_case(
    repo: CalendarConnectionRepositoryPort = Depends(get_calendar_connection_repository),
    provider: CalendarProviderPort = Depends(get_calendar_provider),
    block_port: ScheduleBlockSyncPort = Depends(get_schedule_block_sync_port_dep),
    uow: AsyncUnitOfWork = Depends(get_account_uow),
) -> SyncScheduleBlocksToGoogleUseCase:
    return SyncScheduleBlocksToGoogleUseCase(
        repository=repo,
        calendar_provider=provider,
        schedule_block_port=block_port,
        uow=uow,
    )


def get_process_google_calendar_webhook_use_case(
    repo: CalendarConnectionRepositoryPort = Depends(get_calendar_connection_repository),
    provider: CalendarProviderPort = Depends(get_calendar_provider),
    block_port: ScheduleBlockSyncPort = Depends(get_schedule_block_sync_port_dep),
    uow: AsyncUnitOfWork = Depends(get_account_uow),
) -> ProcessGoogleCalendarWebhookUseCase:
    return ProcessGoogleCalendarWebhookUseCase(
        repository=repo,
        calendar_provider=provider,
        schedule_block_port=block_port,
        uow=uow,
    )


def get_renew_expiring_calendar_webhooks_use_case(
    repo: CalendarConnectionRepositoryPort = Depends(get_calendar_connection_repository),
    provider: CalendarProviderPort = Depends(get_calendar_provider),
    uow: AsyncUnitOfWork = Depends(get_account_uow),
) -> RenewExpiringCalendarWebhooksUseCase:
    return RenewExpiringCalendarWebhooksUseCase(
        repository=repo,
        calendar_provider=provider,
        uow=uow,
    )


def get_reconcile_calendar_connections_use_case(
    repo: CalendarConnectionRepositoryPort = Depends(get_calendar_connection_repository),
    process_webhook_uc: ProcessGoogleCalendarWebhookUseCase = Depends(
        get_process_google_calendar_webhook_use_case
    ),
    renew_webhooks_uc: RenewExpiringCalendarWebhooksUseCase = Depends(
        get_renew_expiring_calendar_webhooks_use_case
    ),
    uow: AsyncUnitOfWork = Depends(get_account_uow),
) -> ReconcileCalendarConnectionsUseCase:
    return ReconcileCalendarConnectionsUseCase(
        repository=repo,
        process_webhook_use_case=process_webhook_uc,
        renew_webhooks_use_case=renew_webhooks_uc,
        uow=uow,
    )


# --- Profile, Quota & Password Dependencies ---
def get_learner_profile_repository(
    session: AsyncSession = Depends(get_account_db_session),
) -> LearnerProfileRepositoryPort:
    return SqlAlchemyLearnerProfileRepository(session)


def get_update_profile_use_case(
    user_repo: UserRepositoryPort = Depends(get_user_repository),
    uow: AsyncUnitOfWork = Depends(get_account_uow),
    learner_profile_repo: LearnerProfileRepositoryPort = Depends(get_learner_profile_repository),
) -> UpdateProfileUseCase:
    return UpdateProfileUseCase(
        user_repo=user_repo,
        uow=uow,
        learner_profile_repo=learner_profile_repo,
    )


def get_get_profile_use_case(
    user_repo: UserRepositoryPort = Depends(get_user_repository),
    learner_profile_repo: LearnerProfileRepositoryPort = Depends(get_learner_profile_repository),
) -> GetProfileUseCase:
    return GetProfileUseCase(
        user_repo=user_repo,
        learner_profile_repo=learner_profile_repo,
    )


def get_get_quota_use_case(
    user_repo: UserRepositoryPort = Depends(get_user_repository),
    uow: AsyncUnitOfWork = Depends(get_account_uow),
) -> GetQuotaUseCase:
    return GetQuotaUseCase(user_repo=user_repo, uow=uow)


def get_change_password_use_case(
    user_repo: UserRepositoryPort = Depends(get_user_repository),
    uow: AsyncUnitOfWork = Depends(get_account_uow),
    refresh_token_repo: RefreshTokenRepositoryPort = Depends(get_refresh_token_repository),
) -> ChangePasswordUseCase:
    return ChangePasswordUseCase(
        user_repo=user_repo,
        uow=uow,
        refresh_token_repo=refresh_token_repo,
    )


# --- WebCal Dependencies ---
def get_webcal_token_repository(
    session: AsyncSession = Depends(get_account_db_session),
) -> WebcalTokenRepositoryPort:
    return SqlAlchemyWebcalTokenRepository(session)


def get_account_planning_execution_bridge(
    session: AsyncSession = Depends(get_account_db_session),
) -> PlanningExecutionBridgePort:
    return create_planning_execution_bridge(session)


def get_webcal_status_use_case(
    repo: WebcalTokenRepositoryPort = Depends(get_webcal_token_repository),
) -> GetWebcalStatusUseCase:
    return GetWebcalStatusUseCase(repository=repo)


def get_rotate_webcal_token_use_case(
    repo: WebcalTokenRepositoryPort = Depends(get_webcal_token_repository),
    uow: AsyncUnitOfWork = Depends(get_account_uow),
) -> RotateWebcalTokenUseCase:
    settings = get_settings()
    return RotateWebcalTokenUseCase(
        repository=repo,
        uow=uow,
        public_base_url=settings.frontend_url,
    )


def get_revoke_webcal_token_use_case(
    repo: WebcalTokenRepositoryPort = Depends(get_webcal_token_repository),
    uow: AsyncUnitOfWork = Depends(get_account_uow),
) -> RevokeWebcalTokenUseCase:
    return RevokeWebcalTokenUseCase(repository=repo, uow=uow)


def get_webcal_ics_feed_use_case(
    repo: WebcalTokenRepositoryPort = Depends(get_webcal_token_repository),
    user_repo: UserRepositoryPort = Depends(get_user_repository),
    planning_bridge: PlanningExecutionBridgePort = Depends(get_account_planning_execution_bridge),
    uow: AsyncUnitOfWork = Depends(get_account_uow),
) -> GetWebcalIcsFeedUseCase:
    return GetWebcalIcsFeedUseCase(
        repository=repo,
        user_repo=user_repo,
        planning_bridge=planning_bridge,
        uow=uow,
    )


def get_account_execution_dashboard_port(
    session: AsyncSession = Depends(get_account_db_session),
) -> ExecutionDashboardQueryPort:
    return create_execution_dashboard_query_port(session)


def get_export_account_data_use_case(
    user_repo: UserRepositoryPort = Depends(get_user_repository),
    learner_profile_repo: LearnerProfileRepositoryPort = Depends(get_learner_profile_repository),
    learner_memory_repo: LearnerMemoryRepositoryPort = Depends(get_learner_memory_repository),
    availability_repo: AvailabilityRepositoryPort = Depends(get_availability_repository),
    planning_bridge: PlanningExecutionBridgePort = Depends(get_account_planning_execution_bridge),
    execution_dashboard_port: ExecutionDashboardQueryPort = Depends(
        get_account_execution_dashboard_port
    ),
) -> ExportAccountDataUseCase:
    return ExportAccountDataUseCase(
        user_repo=user_repo,
        learner_profile_repo=learner_profile_repo,
        learner_memory_repo=learner_memory_repo,
        availability_repo=availability_repo,
        planning_bridge=planning_bridge,
        execution_dashboard_port=execution_dashboard_port,
    )


# --- Notification Center Dependencies ---
def get_notification_repository(
    session: AsyncSession = Depends(get_account_db_session),
) -> NotificationRepositoryPort:
    return SqlAlchemyNotificationRepository(session)


def get_list_notifications_use_case(
    repo: NotificationRepositoryPort = Depends(get_notification_repository),
) -> ListNotificationsUseCase:
    return ListNotificationsUseCase(notification_repo=repo)


def get_mark_notification_read_use_case(
    repo: NotificationRepositoryPort = Depends(get_notification_repository),
    uow: AsyncUnitOfWork = Depends(get_account_uow),
) -> MarkNotificationReadUseCase:
    return MarkNotificationReadUseCase(notification_repo=repo, uow=uow)


def get_mark_all_notifications_read_use_case(
    repo: NotificationRepositoryPort = Depends(get_notification_repository),
    uow: AsyncUnitOfWork = Depends(get_account_uow),
) -> MarkAllNotificationsReadUseCase:
    return MarkAllNotificationsReadUseCase(notification_repo=repo, uow=uow)


# --- Billing & Subscription Dependencies ---
def get_payment_transaction_repository(
    session: AsyncSession = Depends(get_account_db_session),
) -> PaymentTransactionRepositoryPort:
    return SqlAlchemyPaymentTransactionRepository(session)


def get_payment_provider() -> PaymentProviderPort:
    return LocalMockPaymentAdapter(settings=get_settings())


def get_create_billing_checkout_use_case(
    payment_repo: PaymentTransactionRepositoryPort = Depends(get_payment_transaction_repository),
    payment_provider: PaymentProviderPort = Depends(get_payment_provider),
    uow: AsyncUnitOfWork = Depends(get_account_uow),
) -> CreateBillingCheckoutUseCase:
    return CreateBillingCheckoutUseCase(
        payment_repo=payment_repo,
        payment_provider=payment_provider,
        uow=uow,
    )


def get_list_billing_transactions_use_case(
    payment_repo: PaymentTransactionRepositoryPort = Depends(get_payment_transaction_repository),
) -> ListBillingTransactionsUseCase:
    return ListBillingTransactionsUseCase(payment_repo=payment_repo)


def get_settle_payment_transaction_use_case(
    payment_repo: PaymentTransactionRepositoryPort = Depends(get_payment_transaction_repository),
    user_repo: UserRepositoryPort = Depends(get_user_repository),
    uow: AsyncUnitOfWork = Depends(get_account_uow),
) -> SettlePaymentTransactionUseCase:
    return SettlePaymentTransactionUseCase(
        payment_repo=payment_repo,
        user_repo=user_repo,
        uow=uow,
    )
