from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import RedirectResponse

from src.account.application.dtos.calendar import (
    CalendarConnectionResponseDTO,
    CalendarOAuthCallbackRequestDTO,
    InitiateCalendarAuthRequestDTO,
    InitiateCalendarAuthResponseDTO,
    WebcalRevokeResponseDTO,
    WebcalRotateResponseDTO,
    WebcalStatusResponseDTO,
)
from src.account.application.use_cases.calendar import (
    DisconnectGoogleCalendarUseCase,
    GetCalendarConnectionStatusUseCase,
    GetWebcalIcsFeedUseCase,
    GetWebcalStatusUseCase,
    HandleGoogleCalendarOAuthCallbackUseCase,
    InitiateGoogleCalendarAuthUseCase,
    RevokeWebcalTokenUseCase,
    RotateWebcalTokenUseCase,
    WebcalTokenInvalidError,
)
from src.account.domain.ports.calendar_provider_port import (
    CalendarAuthError,
    CalendarProviderError,
)
from src.account.domain.services.oauth_state import (
    DEFAULT_RETURN_TO,
    sanitize_return_to,
    verify_signed_oauth_state,
)
from src.account.presentation.deps import (
    get_current_learner_id,
    get_disconnect_google_calendar_use_case,
    get_get_calendar_connection_status_use_case,
    get_handle_google_calendar_oauth_callback_use_case,
    get_initiate_google_calendar_auth_use_case,
    get_revoke_webcal_token_use_case,
    get_rotate_webcal_token_use_case,
    get_webcal_ics_feed_use_case,
    get_webcal_status_use_case,
)
from src.shared_kernel.config import get_settings
from src.shared_kernel.infrastructure.security.rate_limiter import (
    enforce_rate_limit,
    hash_token,
)

router = APIRouter(prefix="/api/v1/account/calendar", tags=["Calendar Integration (UC-17)"])
feeds_router = APIRouter(prefix="/api/v1/feeds", tags=["WebCal Feeds (UC-17)"])


@router.post(
    "/google/authorize",
    response_model=InitiateCalendarAuthResponseDTO,
    status_code=status.HTTP_200_OK,
    summary="Generate Google Calendar OAuth consent URL",
)
async def initiate_google_calendar_auth(
    http_request: Request,
    request: InitiateCalendarAuthRequestDTO,
    user_id: UUID = Depends(get_current_learner_id),
    use_case: InitiateGoogleCalendarAuthUseCase = Depends(
        get_initiate_google_calendar_auth_use_case
    ),
) -> InitiateCalendarAuthResponseDTO:
    await enforce_rate_limit(http_request, "calendar_oauth_init_user", identifier=str(user_id))
    return await use_case.execute(user_id=user_id, request=request)


@router.get(
    "/google/callback",
    summary="Handle Google OAuth redirection callback (GET)",
)
async def handle_google_calendar_callback_get(
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
    user_id: UUID = Depends(get_current_learner_id),
    use_case: HandleGoogleCalendarOAuthCallbackUseCase = Depends(
        get_handle_google_calendar_oauth_callback_use_case
    ),
) -> Response:
    del request
    settings = get_settings()
    frontend_url = (settings.frontend_url or "http://localhost:3000").rstrip("/")
    return_to = DEFAULT_RETURN_TO

    # Extract safe return_to only after verifying the HMAC-signed state and user binding.
    try:
        verified_state = verify_signed_oauth_state(
            state=state,
            secret_key=settings.secret_key,
            now=datetime.now(UTC),
        )
        if verified_state.user_id == user_id:
            return_to = sanitize_return_to(verified_state.return_to)
    except CalendarAuthError:
        return_to = DEFAULT_RETURN_TO

    try:
        dto = CalendarOAuthCallbackRequestDTO(code=code, state=state)
        await use_case.execute(user_id=user_id, request=dto)

        separator = "&" if "?" in return_to else "?"
        redirect_url = f"{frontend_url}{return_to}{separator}calendar_connected=success"
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)
    except CalendarAuthError:
        separator = "&" if "?" in return_to else "?"
        redirect_url = f"{frontend_url}{return_to}{separator}calendar_connected=error&error_detail=oauth_auth_failed"
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)
    except CalendarProviderError:
        separator = "&" if "?" in return_to else "?"
        redirect_url = (
            f"{frontend_url}{return_to}{separator}calendar_connected=error"
            "&error_detail=calendar_provider_error"
        )
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)
    except Exception:
        separator = "&" if "?" in return_to else "?"
        redirect_url = (
            f"{frontend_url}{return_to}{separator}calendar_connected=error"
            "&error_detail=calendar_connection_failed"
        )
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)


@router.post(
    "/google/callback",
    response_model=CalendarConnectionResponseDTO,
    status_code=status.HTTP_200_OK,
    summary="Handle Google OAuth redirection callback (POST from SPA)",
)
async def handle_google_calendar_callback_post(
    dto: CalendarOAuthCallbackRequestDTO,
    user_id: UUID = Depends(get_current_learner_id),
    use_case: HandleGoogleCalendarOAuthCallbackUseCase = Depends(
        get_handle_google_calendar_oauth_callback_use_case
    ),
) -> CalendarConnectionResponseDTO:
    try:
        return await use_case.execute(user_id=user_id, request=dto)
    except CalendarAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=exc.message,
        ) from exc
    except CalendarProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=exc.message,
        ) from exc


@router.get(
    "/status",
    response_model=CalendarConnectionResponseDTO,
    status_code=status.HTTP_200_OK,
    summary="Get current external calendar integration status",
)
async def get_calendar_status(
    provider: str = Query(default="GOOGLE"),
    user_id: UUID = Depends(get_current_learner_id),
    use_case: GetCalendarConnectionStatusUseCase = Depends(
        get_get_calendar_connection_status_use_case
    ),
) -> CalendarConnectionResponseDTO:
    return await use_case.execute(user_id=user_id, provider=provider)


@router.post(
    "/disconnect",
    response_model=CalendarConnectionResponseDTO,
    status_code=status.HTTP_200_OK,
    summary="Disconnect external calendar and stop push notifications",
)
async def disconnect_calendar(
    provider: str = Query(default="GOOGLE"),
    user_id: UUID = Depends(get_current_learner_id),
    use_case: DisconnectGoogleCalendarUseCase = Depends(get_disconnect_google_calendar_use_case),
) -> CalendarConnectionResponseDTO:
    return await use_case.execute(user_id=user_id, provider=provider)


@router.get(
    "/webcal",
    response_model=WebcalStatusResponseDTO,
    status_code=status.HTTP_200_OK,
    summary="Get current WebCal subscription status",
)
async def get_webcal_status(
    user_id: UUID = Depends(get_current_learner_id),
    use_case: GetWebcalStatusUseCase = Depends(get_webcal_status_use_case),
) -> WebcalStatusResponseDTO:
    return await use_case.execute(user_id=user_id)


@router.post(
    "/webcal/rotate",
    response_model=WebcalRotateResponseDTO,
    status_code=status.HTTP_200_OK,
    summary="Create or rotate personal WebCal feed token",
)
async def rotate_webcal_token(
    user_id: UUID = Depends(get_current_learner_id),
    use_case: RotateWebcalTokenUseCase = Depends(get_rotate_webcal_token_use_case),
) -> WebcalRotateResponseDTO:
    return await use_case.execute(user_id=user_id)


@router.delete(
    "/webcal",
    response_model=WebcalRevokeResponseDTO,
    status_code=status.HTTP_200_OK,
    summary="Revoke personal WebCal feed token",
)
async def revoke_webcal_token(
    user_id: UUID = Depends(get_current_learner_id),
    use_case: RevokeWebcalTokenUseCase = Depends(get_revoke_webcal_token_use_case),
) -> WebcalRevokeResponseDTO:
    return await use_case.execute(user_id=user_id)


@feeds_router.get(
    "/{token}.ics",
    status_code=status.HTTP_200_OK,
    summary="Download read-only RFC 5545 ICS calendar feed",
)
async def get_webcal_ics_feed(
    request: Request,
    token: str,
    use_case: GetWebcalIcsFeedUseCase = Depends(get_webcal_ics_feed_use_case),
) -> Response:
    await enforce_rate_limit(request, "webcal_feed_token", identifier=hash_token(token))
    try:
        ics_text = await use_case.execute(raw_token=token)
    except WebcalTokenInvalidError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Calendar feed not found",
        ) from exc
    return Response(
        content=ics_text,
        media_type="text/calendar; charset=utf-8",
        headers={
            "Cache-Control": "no-store, private",
            "Referrer-Policy": "no-referrer",
            "X-Content-Type-Options": "nosniff",
        },
    )
