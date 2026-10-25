from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/evaluation", tags=["Evaluation & Analytics"])


@router.get("/status")
async def get_evaluation_context_status() -> dict[str, str]:
    """Bounded Context 4 health/status endpoint (UC-14..UC-17, UC-19)."""
    return {"context": "evaluation", "status": "ready"}
