from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from src.account.application.dtos.auth import (
    ConfirmPasswordResetCommand,
    ConfirmPasswordResetSchema,
    GoogleAuthCommand,
    GoogleAuthRequestSchema,
    LoginCommand,
    LoginRequestSchema,
    LoginResponseSchema,
    MessageResponseSchema,
    RefreshTokenCommand,
    RefreshTokenRequestSchema,
    RegisterCommand,
    RegisterRequestSchema,
    RequestPasswordResetOtpCommand,
    RequestPasswordResetOtpSchema,
    RequestRegisterOtpCommand,
    ResendRegisterOtpCommand,
    ResendRegisterOtpSchema,
    UserProfileSchema,
    VerifyPasswordResetOtpCommand,
    VerifyPasswordResetOtpResponseSchema,
    VerifyPasswordResetOtpSchema,
    VerifyRegisterOtpCommand,
    VerifyRegisterOtpSchema,
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
from src.account.domain.exceptions.auth_exceptions import (
    AccountLockedError,
    InvalidCredentialsError,
    InvalidOtpError,
    InvalidTokenError,
    RateLimitError,
    UserAlreadyExistsError,
)
from src.account.infrastructure.orm.user_orm import UserORM
from src.account.presentation.deps import (
    get_confirm_password_reset_use_case,
    get_current_user,
    get_google_auth_use_case,
    get_login_use_case,
    get_refresh_token_use_case,
    get_register_use_case,
    get_request_password_reset_otp_use_case,
    get_request_register_otp_use_case,
    get_resend_register_otp_use_case,
    get_verify_password_reset_otp_use_case,
    get_verify_register_otp_use_case,
)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post(
    "/login",
    response_model=LoginResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="User Login (UC-AUTH-02)",
)
async def login(
    payload: LoginRequestSchema,
    response: Response,
    use_case: LoginUseCase = Depends(get_login_use_case),
) -> LoginResponseSchema:
    """Authenticates credentials using Argon2id, generates HS256 JWT & 7-day Refresh Token."""
    try:
        cmd = LoginCommand(
            email=payload.email, password=payload.password, remember_me=payload.remember_me
        )
        result = await use_case.execute(cmd)

        response.set_cookie(
            key="access_token",
            value=result.access_token,
            httponly=True,
            samesite="lax",
            max_age=result.expires_in,
            path="/",
        )
        response.set_cookie(
            key="refresh_token",
            value=result.refresh_token,
            httponly=True,
            samesite="lax",
            max_age=7 * 24 * 3600,
            path="/",
        )

        return LoginResponseSchema(
            access_token=result.access_token,
            token_type=result.token_type,
            expires_in=result.expires_in,
            user=UserProfileSchema(
                id=result.user.id,
                email=result.user.email,
                full_name=result.user.full_name,
                role=result.user.role,
                tier=result.user.tier,
                created_at=result.user.created_at,
            ),
        )
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except AccountLockedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.post(
    "/google",
    response_model=LoginResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Google OAuth 2.0 Single Sign-On (SSO)",
)
async def google_auth(
    payload: GoogleAuthRequestSchema,
    response: Response,
    use_case: GoogleAuthUseCase = Depends(get_google_auth_use_case),
) -> LoginResponseSchema:
    """Verifies Google ID Token or Access Token, auto-provisions user if new, issues JWT pair."""
    token = payload.id_token or payload.credential

    if not token and not payload.access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google token is required (id_token, credential, or access_token).",
        )

    try:
        cmd = GoogleAuthCommand(id_token=token, access_token=payload.access_token)
        result = await use_case.execute(cmd)

        response.set_cookie(
            key="access_token",
            value=result.access_token,
            httponly=True,
            samesite="lax",
            max_age=result.expires_in,
            path="/",
        )
        response.set_cookie(
            key="refresh_token",
            value=result.refresh_token,
            httponly=True,
            samesite="lax",
            max_age=7 * 24 * 3600,
            path="/",
        )

        return LoginResponseSchema(
            access_token=result.access_token,
            token_type=result.token_type,
            expires_in=result.expires_in,
            user=UserProfileSchema(
                id=result.user.id,
                email=result.user.email,
                full_name=result.user.full_name,
                role=result.user.role,
                tier=result.user.tier,
                created_at=result.user.created_at,
            ),
        )
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except AccountLockedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.post(
    "/register",
    response_model=LoginResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="User Registration (Direct fallback)",
)
async def register(
    payload: RegisterRequestSchema,
    response: Response,
    use_case: RegisterUseCase = Depends(get_register_use_case),
) -> LoginResponseSchema:
    """Direct registration fallback without OTP (UC-AUTH-01)."""
    try:
        cmd = RegisterCommand(
            full_name=payload.full_name, email=payload.email, password=payload.password
        )
        result = await use_case.execute(cmd)

        response.set_cookie(
            key="access_token",
            value=result.access_token,
            httponly=True,
            samesite="lax",
            max_age=result.expires_in,
            path="/",
        )
        response.set_cookie(
            key="refresh_token",
            value=result.refresh_token,
            httponly=True,
            samesite="lax",
            max_age=7 * 24 * 3600,
            path="/",
        )

        return LoginResponseSchema(
            access_token=result.access_token,
            token_type=result.token_type,
            expires_in=result.expires_in,
            user=UserProfileSchema(
                id=result.user.id,
                email=result.user.email,
                full_name=result.user.full_name,
                role=result.user.role,
                tier=result.user.tier,
                created_at=result.user.created_at,
            ),
        )
    except UserAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


# --- OTP REGISTRATION ENDPOINTS ---


@router.post(
    "/register/request-otp",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Request OTP for User Registration",
)
async def request_register_otp(
    payload: RegisterRequestSchema,
    use_case: RequestRegisterOtpUseCase = Depends(get_request_register_otp_use_case),
) -> MessageResponseSchema:
    """Step 1: Check duplicate, generate OTP, store in Redis, dispatch email."""
    try:
        cmd = RequestRegisterOtpCommand(
            full_name=payload.full_name, email=payload.email, password=payload.password
        )
        message = await use_case.execute(cmd)
        return MessageResponseSchema(message=message)
    except UserAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except RateLimitError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc


@router.post(
    "/register/resend-otp",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Resend OTP for User Registration",
)
async def resend_register_otp(
    payload: ResendRegisterOtpSchema,
    use_case: ResendRegisterOtpUseCase = Depends(get_resend_register_otp_use_case),
) -> MessageResponseSchema:
    """Step 1b: Resend fresh OTP using existing Redis registration session."""
    try:
        cmd = ResendRegisterOtpCommand(email=payload.email)
        message = await use_case.execute(cmd)
        return MessageResponseSchema(message=message)
    except RateLimitError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc
    except InvalidOtpError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except UserAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post(
    "/register/verify-otp",
    response_model=LoginResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Verify OTP and Complete Registration",
)
async def verify_register_otp(
    payload: VerifyRegisterOtpSchema,
    response: Response,
    use_case: VerifyRegisterOtpUseCase = Depends(get_verify_register_otp_use_case),
) -> LoginResponseSchema:
    """Step 2: Verify OTP from Redis, write to PostgreSQL, and return JWT tokens."""
    try:
        cmd = VerifyRegisterOtpCommand(email=payload.email, otp_code=payload.otp_code)
        result = await use_case.execute(cmd)

        response.set_cookie(
            key="access_token",
            value=result.access_token,
            httponly=True,
            samesite="lax",
            max_age=result.expires_in,
            path="/",
        )
        response.set_cookie(
            key="refresh_token",
            value=result.refresh_token,
            httponly=True,
            samesite="lax",
            max_age=7 * 24 * 3600,
            path="/",
        )

        return LoginResponseSchema(
            access_token=result.access_token,
            token_type=result.token_type,
            expires_in=result.expires_in,
            user=UserProfileSchema(
                id=result.user.id,
                email=result.user.email,
                full_name=result.user.full_name,
                role=result.user.role,
                tier=result.user.tier,
                created_at=result.user.created_at,
            ),
        )
    except InvalidOtpError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except UserAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


# --- OTP PASSWORD RESET ENDPOINTS ---


@router.post(
    "/password-reset/request-otp",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Request Password Reset OTP",
)
async def request_password_reset_otp(
    payload: RequestPasswordResetOtpSchema,
    use_case: RequestPasswordResetOtpUseCase = Depends(get_request_password_reset_otp_use_case),
) -> MessageResponseSchema:
    """Step 1: Check user, generate OTP, store in Redis, dispatch email."""
    try:
        cmd = RequestPasswordResetOtpCommand(email=payload.email)
        message = await use_case.execute(cmd)
        return MessageResponseSchema(message=message)
    except RateLimitError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc


@router.post(
    "/password-reset/verify-otp",
    response_model=VerifyPasswordResetOtpResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Verify OTP for Password Reset (Step 2)",
)
async def verify_password_reset_otp(
    payload: VerifyPasswordResetOtpSchema,
    use_case: VerifyPasswordResetOtpUseCase = Depends(get_verify_password_reset_otp_use_case),
) -> VerifyPasswordResetOtpResponseSchema:
    """Step 2: Verify reset OTP from Redis, consume it, and issue temporary reset_token."""
    try:
        cmd = VerifyPasswordResetOtpCommand(email=payload.email, otp_code=payload.otp_code)
        result = await use_case.execute(cmd)
        return VerifyPasswordResetOtpResponseSchema(
            message=result.message, reset_token=result.reset_token
        )
    except InvalidOtpError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post(
    "/password-reset/confirm",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Confirm Password Reset (Step 3)",
)
async def confirm_password_reset(
    payload: ConfirmPasswordResetSchema,
    use_case: ConfirmPasswordResetUseCase = Depends(get_confirm_password_reset_use_case),
) -> MessageResponseSchema:
    """Step 3: Verify reset_token (or direct OTP), update password_hash in PostgreSQL with Argon2id."""
    try:
        cmd = ConfirmPasswordResetCommand(
            email=payload.email,
            new_password=payload.new_password,
            reset_token=payload.reset_token,
            otp_code=payload.otp_code,
        )
        message = await use_case.execute(cmd)
        return MessageResponseSchema(message=message)
    except InvalidOtpError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post(
    "/refresh",
    response_model=LoginResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Refresh Access Token (ADR-008 RTR)",
)
async def refresh_token(
    request: Request,
    response: Response,
    payload: RefreshTokenRequestSchema | None = None,
    use_case: RefreshTokenUseCase = Depends(get_refresh_token_use_case),
) -> LoginResponseSchema:
    """Consumes existing refresh token, rotates session, and issues fresh JWT access/refresh token pair."""
    token = (
        payload.refresh_token if payload and payload.refresh_token else None
    ) or request.cookies.get("refresh_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required in request body or cookie.",
        )

    try:
        cmd = RefreshTokenCommand(raw_refresh_token=token)
        result = await use_case.execute(cmd)

        response.set_cookie(
            key="access_token",
            value=result.access_token,
            httponly=True,
            samesite="lax",
            max_age=result.expires_in,
            path="/",
        )
        response.set_cookie(
            key="refresh_token",
            value=result.refresh_token,
            httponly=True,
            samesite="lax",
            max_age=7 * 24 * 3600,
            path="/",
        )

        return LoginResponseSchema(
            access_token=result.access_token,
            token_type=result.token_type,
            expires_in=result.expires_in,
            user=UserProfileSchema(
                id=result.user.id,
                email=result.user.email,
                full_name=result.user.full_name,
                role=result.user.role,
                tier=result.user.tier,
                created_at=result.user.created_at,
            ),
        )
    except InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except AccountLockedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get(
    "/me",
    response_model=UserProfileSchema,
    status_code=status.HTTP_200_OK,
    summary="Get Current Authenticated User",
)
async def get_current_user_profile(
    current_user: UserORM = Depends(get_current_user),
) -> UserProfileSchema:
    """Retrieves profile information for currently authenticated learner."""
    return UserProfileSchema(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        tier=current_user.tier,
        created_at=current_user.created_at.isoformat(),
    )


@router.post("/logout", status_code=status.HTTP_200_OK, summary="User Logout")
async def logout(response: Response) -> dict[str, str]:
    """Clears authentication cookies and invalidates session."""
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/")
    return {"message": "Logged out successfully."}
