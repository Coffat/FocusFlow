from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/planning", tags=["Planning & Roadmaps"])


@router.get("/status")
async def get_planning_context_status() -> dict[str, str]:
    """Bounded Context 2 health/status endpoint (UC-06..UC-09)."""
    return {"context": "planning", "status": "ready"}
