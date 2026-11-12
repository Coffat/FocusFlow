import base64
import json
import urllib.parse
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import RedirectResponse

from src.account.application.dtos.calendar import (
    CalendarConnectionResponseDTO,
    CalendarOAuthCallbackRequestDTO,
    InitiateCalendarAuthRequestDTO,
    InitiateCalendarAuthResponseDTO,
)
from src.account.application.use_cases.calendar import (
    DisconnectGoogleCalendarUseCase,
    GetCalendarConnectionStatusUseCase,
    HandleGoogleCalendarOAuthCallbackUseCase,
    InitiateGoogleCalendarAuthUseCase,
)
from src.account.domain.ports.calendar_provider_port import (
    CalendarAuthError,
    CalendarProviderError,
)
from src.account.presentation.deps import (
    get_current_learner_id,
    get_disconnect_google_calendar_use_case,
    get_get_calendar_connection_status_use_case,
    get_handle_google_calendar_oauth_callback_use_case,
    get_initiate_google_calendar_auth_use_case,
)
from src.shared_kernel.config import get_settings

router = APIRouter(prefix="/api/v1/account/calendar", tags=["Calendar Integration (UC-17)"])


@router.post(
    "/google/authorize",
    response_model=InitiateCalendarAuthResponseDTO,
    status_code=status.HTTP_200_OK,
    summary="Generate Google Calendar OAuth consent URL",
)
async def initiate_google_calendar_auth(
    request: InitiateCalendarAuthRequestDTO,
    user_id: UUID = Depends(get_current_learner_id),
    use_case: InitiateGoogleCalendarAuthUseCase = Depends(
        get_initiate_google_calendar_auth_use_case
    ),
) -> InitiateCalendarAuthResponseDTO:
    return await use_case.execute(user_id=user_id, request=request)


@router.get(
    "/google/callback",
    summary="Handle Google OAuth redirection callback (GET)",
)
async def handle_google_calendar_callback_get(
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
    use_case: HandleGoogleCalendarOAuthCallbackUseCase = Depends(
        get_handle_google_calendar_oauth_callback_use_case
    ),
) -> Response:
    settings = get_settings()
    frontend_url = (settings.frontend_url or "http://localhost:4200").rstrip("/")
    return_to = "/settings"

    # Extract user_id and return_to from state
    try:
        decoded_bytes = base64.urlsafe_b64decode(state.encode("utf-8"))
        state_data = json.loads(decoded_bytes.decode("utf-8"))
        user_id = UUID(state_data["user_id"])
        return_to = str(state_data.get("return_to") or "/settings")
        if not return_to.startswith("/"):
            return_to = f"/{return_to}"
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OAuth state parameter.",
        ) from exc

    try:
        dto = CalendarOAuthCallbackRequestDTO(code=code, state=state)
        await use_case.execute(user_id=user_id, request=dto)

        redirect_url = f"{frontend_url}{return_to}?calendar_connected=success"
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)
    except (CalendarAuthError, CalendarProviderError, Exception) as exc:
        error_msg = getattr(exc, "message", str(exc))
        redirect_url = f"{frontend_url}{return_to}?calendar_connected=error&error_detail={urllib.parse.quote(str(error_msg))}"
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
