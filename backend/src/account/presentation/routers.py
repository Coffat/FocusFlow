from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/account", tags=["Account & Quota"])


@router.get("/status")
async def get_account_context_status() -> dict[str, str]:
    """Bounded Context 1 health/status endpoint (UC-01..UC-05, UC-18)."""
    return {"context": "account", "status": "ready"}
