import base64
import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import HTMLResponse

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
    # Extract user_id from state
    try:
        decoded_bytes = base64.urlsafe_b64decode(state.encode("utf-8"))
        state_data = json.loads(decoded_bytes.decode("utf-8"))
        user_id = UUID(state_data["user_id"])
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OAuth state parameter.",
        ) from exc

    try:
        dto = CalendarOAuthCallbackRequestDTO(code=code, state=state)
        result = await use_case.execute(user_id=user_id, request=dto)

        accept_header = request.headers.get("accept", "")
        if "text/html" in accept_header:
            html_content = """
            <!DOCTYPE html>
            <html lang="vi">
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <title>FocusFlow — Kết nối Google Calendar thành công</title>
                <style>
                    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; background: #0f172a; color: #f8fafc; }
                    .card { background: #1e293b; padding: 2.5rem; border-radius: 1.25rem; box-shadow: 0 20px 40px rgba(0,0,0,0.5); text-align: center; max-width: 480px; width: 90%; border: 1px solid #334155; }
                    .icon { font-size: 3.5rem; margin-bottom: 1rem; }
                    h1 { font-size: 1.5rem; margin-bottom: 0.75rem; color: #38bdf8; }
                    p { color: #94a3b8; font-size: 0.95rem; line-height: 1.6; margin-bottom: 1.75rem; }
                    .badge { display: inline-block; background: #0369a1; color: #e0f2fe; padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.85rem; font-weight: 500; margin-bottom: 1rem; }
                    .btn { display: inline-block; background: #0284c7; color: white; text-decoration: none; padding: 0.85rem 1.75rem; border-radius: 0.625rem; font-weight: 600; font-size: 0.95rem; transition: background 0.2s, transform 0.1s; }
                    .btn:hover { background: #0369a1; transform: translateY(-1px); }
                </style>
            </head>
            <body>
                <div class="card">
                    <div class="icon">🎉</div>
                    <div class="badge">Trạng thái: ACTIVE</div>
                    <h1>Kết nối Google Calendar thành công!</h1>
                    <p>Lịch <strong>FocusFlow (Lịch học thông minh)</strong> đã được liên kết với tài khoản của bạn. Mọi khối lịch học sẽ được đồng bộ tự động hai chiều.</p>
                    <a href="http://localhost:3000" class="btn">Quay lại FocusFlow Dashboard</a>
                </div>
            </body>
            </html>
            """
            return HTMLResponse(content=html_content, status_code=status.HTTP_200_OK)

        from fastapi.responses import JSONResponse
        return JSONResponse(content=result.__dict__, status_code=status.HTTP_200_OK)
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
