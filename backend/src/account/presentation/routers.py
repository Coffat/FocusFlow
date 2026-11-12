from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from src.account.application.dtos.availability import (
    AvailabilityResponseDTO,
    UpdateAvailabilityRequestDTO,
)
from src.account.application.dtos.learner_memory import (
    LearnerMemoryResponseDTO,
    ResetLearnerMemoryRequestDTO,
    UpdateLearnerMemoryRequestDTO,
)
from src.account.application.use_cases.availability.get_availability_use_case import (
    GetAvailabilityUseCase,
)
from src.account.application.use_cases.availability.update_availability_use_case import (
    UpdateAvailabilityUseCase,
)
from src.account.application.use_cases.learner_memory import (
    LearnerMemoryNotFoundError,
    ListLearnerMemoryUseCase,
    ResetLearnerMemoryUseCase,
    UpdateLearnerMemoryUseCase,
)
from src.account.domain.exceptions.availability import AvailabilityDomainException
from src.account.presentation.calendar_router import router as calendar_router
from src.account.presentation.deps import (
    get_current_learner_id,
    get_get_availability_use_case,
    get_list_learner_memory_use_case,
    get_reset_learner_memory_use_case,
    get_update_availability_use_case,
    get_update_learner_memory_use_case,
)

router = APIRouter(prefix="/api/v1/account", tags=["Account & Quota"])
account_router = router
availabilities_router = APIRouter(prefix="/api/v1/availabilities", tags=["Availabilities"])

__all__ = ["account_router", "availabilities_router", "calendar_router", "router"]


@router.get("/status")
async def get_account_context_status() -> dict[str, str]:
    """Bounded Context 1 health/status endpoint (UC-01..UC-05, UC-18)."""
    return {"context": "account", "status": "ready"}


@router.get("/learner-memory", response_model=list[LearnerMemoryResponseDTO])
async def list_learner_memory(
    user_id: UUID = Depends(get_current_learner_id),
    use_case: ListLearnerMemoryUseCase = Depends(get_list_learner_memory_use_case),
) -> list[LearnerMemoryResponseDTO]:
    return await use_case.execute(user_id)


@router.patch("/learner-memory/{memory_id}", response_model=LearnerMemoryResponseDTO)
async def update_learner_memory(
    memory_id: UUID,
    request: UpdateLearnerMemoryRequestDTO,
    user_id: UUID = Depends(get_current_learner_id),
    use_case: UpdateLearnerMemoryUseCase = Depends(get_update_learner_memory_use_case),
) -> LearnerMemoryResponseDTO:
    try:
        return await use_case.execute(user_id, memory_id, request)
    except LearnerMemoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found"
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc


@router.post("/learner-memory/reset", status_code=status.HTTP_204_NO_CONTENT)
async def reset_learner_memory(
    request: ResetLearnerMemoryRequestDTO,
    user_id: UUID = Depends(get_current_learner_id),
    use_case: ResetLearnerMemoryUseCase = Depends(get_reset_learner_memory_use_case),
) -> None:
    try:
        await use_case.execute(user_id, confirmed=request.confirm)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc


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
