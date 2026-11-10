from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from src.account.application.dtos.availability import (
    AvailabilityResponseDTO,
    UpdateAvailabilityRequestDTO,
)
from src.account.application.use_cases.availability.get_availability_use_case import (
    GetAvailabilityUseCase,
)
from src.account.application.use_cases.availability.update_availability_use_case import (
    UpdateAvailabilityUseCase,
)
from src.account.domain.exceptions.availability import AvailabilityDomainException
from src.account.presentation.deps import (
    get_current_learner_id,
    get_get_availability_use_case,
    get_update_availability_use_case,
)

router = APIRouter(prefix="/api/v1/account", tags=["Account & Quota"])
availabilities_router = APIRouter(prefix="/api/v1/availabilities", tags=["Availabilities"])


@router.get("/status")
async def get_account_context_status() -> dict[str, str]:
    """Bounded Context 1 health/status endpoint (UC-01..UC-05, UC-18)."""
    return {"context": "account", "status": "ready"}


@availabilities_router.get(
    "/me",
    response_model=AvailabilityResponseDTO,
    status_code=status.HTTP_200_OK,
    summary="Get current learner's availability profile",
)
async def get_my_availability(
    user_id: UUID = Depends(get_current_learner_id),
    use_case: GetAvailabilityUseCase = Depends(get_get_availability_use_case),
) -> AvailabilityResponseDTO | JSONResponse:
    try:
        return await use_case.execute(user_id=user_id)
    except AvailabilityDomainException as exc:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            },
        )


@availabilities_router.put(
    "/me",
    response_model=AvailabilityResponseDTO,
    status_code=status.HTTP_200_OK,
    summary="Update current learner's availability profile",
)
async def update_my_availability(
    request: UpdateAvailabilityRequestDTO,
    user_id: UUID = Depends(get_current_learner_id),
    use_case: UpdateAvailabilityUseCase = Depends(get_update_availability_use_case),
) -> AvailabilityResponseDTO | JSONResponse:
    try:
        return await use_case.execute(user_id=user_id, request=request)
    except AvailabilityDomainException as exc:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            },
        )
