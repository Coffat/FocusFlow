import asyncio
import contextlib
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
import structlog
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from uuid6 import uuid7

from src.account.presentation.auth_router import router as auth_router
from src.account.presentation.billing_router import router as billing_router
from src.account.presentation.calendar_router import (
    feeds_router,
)
from src.account.presentation.calendar_router import (
    router as calendar_router,
)
from src.account.presentation.routers import (
    availabilities_router,
)
from src.account.presentation.routers import (
    router as account_router,
)
from src.account.presentation.webhook_router import router as webhook_router
from src.evaluation.presentation.routers import (
    analytics_router,
)
from src.evaluation.presentation.routers import (
    router as evaluation_router,
)
from src.execution.presentation.routers import (
    router as execution_router,
)
from src.execution.presentation.routers import (
    sessions_router,
    tasks_router,
)
from src.planning.presentation.routers import (
    roadmaps_router,
)
from src.planning.presentation.routers import (
    router as planning_router,
)
from src.shared_kernel.config import get_settings
from src.shared_kernel.infrastructure.database.session import engine
from src.shared_kernel.infrastructure.external_ai.circuit_breaker import (
    AIServiceUnavailableError,
)
from src.shared_kernel.infrastructure.external_ai.litellm_adapter import (
    CobhubCapabilityProbeResult,
    probe_cobhub_capabilities,
)
from src.shared_kernel.infrastructure.security.csrf_middleware import (
    CSRFProtectionMiddleware,
)
from src.shared_kernel.infrastructure.security.rate_limiter import (
    RateLimiterUnavailableError,
    RateLimitExceededError,
)
from src.shared_kernel.infrastructure.worker.broker import broker
from src.shared_kernel.logging import configure_logging, correlation_id_ctx

_logger = structlog.get_logger(__name__)

_HEALTH_CHECK_TIMEOUT_SECONDS = 2.0


async def check_database_health(timeout_seconds: float = _HEALTH_CHECK_TIMEOUT_SECONDS) -> bool:
    """Perform a lightweight SELECT 1 connectivity check against PostgreSQL."""

    async def _ping_db() -> None:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))

    try:
        await asyncio.wait_for(_ping_db(), timeout=timeout_seconds)
        return True
    except Exception:
        return False


async def check_redis_health(timeout_seconds: float = _HEALTH_CHECK_TIMEOUT_SECONDS) -> bool:
    """Perform a lightweight PING connectivity check against Redis."""
    settings = get_settings()
    client = aioredis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_connect_timeout=timeout_seconds,
        socket_timeout=timeout_seconds,
    )
    try:
        res = await asyncio.wait_for(client.ping(), timeout=timeout_seconds)
        return bool(res)
    except Exception:
        return False
    finally:
        with contextlib.suppress(Exception):
            await client.aclose()


async def run_startup_ai_probe(app: FastAPI | None = None) -> CobhubCapabilityProbeResult | None:
    """Probe cobhub gateway capabilities on startup when configured outside test mode."""
    settings = get_settings()
    if settings.environment == "test":
        return None
    if (settings.llm_provider or "").strip().lower() != "gemini":
        return None
    if not (settings.llm_base_url or "").strip():
        return None
    try:
        probe_res = await probe_cobhub_capabilities(settings)
    except Exception as exc:  # pragma: no cover - defensive startup guard
        _logger.warning("startup_ai_probe_failed", error=str(exc))
        return None
    if app is not None:
        app.state.ai_gateway_probe = probe_res
    return probe_res


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    configure_logging()
    if not broker.is_worker_process:
        await broker.startup()
    await run_startup_ai_probe(app)
    yield
    if not broker.is_worker_process:
        await broker.shutdown()
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="FocusFlow API",
        description=(
            "AI-Powered Personalized Study Planning & Execution System "
            "(Context-First Modular Monolith + Hexagonal Architecture)"
        ),
        version="2.0.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
    )

    origins = settings.cors_origins

    # Middleware stack (outermost to innermost):
    # correlation_id_middleware -> CORSMiddleware -> CSRFProtectionMiddleware -> Router
    app.add_middleware(CSRFProtectionMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
        allow_headers=[
            "Accept",
            "Accept-Language",
            "Authorization",
            "Cache-Control",
            "Content-Language",
            "Content-Type",
            "Last-Event-ID",
            "X-Correlation-ID",
            "X-Requested-With",
        ],
        expose_headers=["X-Correlation-ID", "Content-Disposition"],
    )

    @app.middleware("http")
    async def correlation_id_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        corr_id = request.headers.get("X-Correlation-ID", str(uuid7()))
        token = correlation_id_ctx.set(corr_id)
        try:
            response = await call_next(request)
            response.headers["X-Correlation-ID"] = corr_id
            return response
        finally:
            correlation_id_ctx.reset(token)

    @app.exception_handler(RateLimitExceededError)
    async def rate_limit_exceeded_handler(
        _request: Request, exc: RateLimitExceededError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "code": "RATE_LIMIT_EXCEEDED",
                "detail": "Quá nhiều yêu cầu. Vui lòng thử lại sau.",
            },
            headers=exc.decision.to_headers(),
        )

    @app.exception_handler(RateLimiterUnavailableError)
    async def rate_limiter_unavailable_handler(
        _request: Request, _exc: RateLimiterUnavailableError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "code": "RATE_LIMITER_UNAVAILABLE",
                "detail": "Dịch vụ kiểm soát lưu lượng tạm thời không khả dụng.",
            },
        )

    @app.exception_handler(AIServiceUnavailableError)
    async def ai_service_unavailable_handler(
        _request: Request, exc: AIServiceUnavailableError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "code": "AI_SERVICE_UNAVAILABLE",
                "detail": (
                    str(exc)
                    or "Dịch vụ AI đang tạm bảo trì. Vui lòng thử lại hoặc lập kế hoạch thủ công."
                ),
            },
        )

    app.include_router(account_router)
    app.include_router(availabilities_router)
    app.include_router(auth_router)
    app.include_router(billing_router)
    app.include_router(calendar_router)
    app.include_router(feeds_router)
    app.include_router(webhook_router)
    app.include_router(planning_router)
    app.include_router(roadmaps_router)
    app.include_router(execution_router)
    app.include_router(tasks_router)
    app.include_router(sessions_router)
    app.include_router(evaluation_router)
    app.include_router(analytics_router)

    @app.get("/api/health", tags=["System"])
    async def health_check() -> JSONResponse:
        db_ok, redis_ok = await asyncio.gather(
            check_database_health(),
            check_redis_health(),
        )
        all_ok = db_ok and redis_ok
        payload = {
            "status": "healthy" if all_ok else "degraded",
            "database": "ok" if db_ok else "error",
            "redis": "ok" if redis_ok else "error",
        }
        return JSONResponse(
            status_code=status.HTTP_200_OK if all_ok else status.HTTP_503_SERVICE_UNAVAILABLE,
            content=payload,
        )

    return app


app = create_app()

from src.shared_kernel.infrastructure.worker.broker import (  # noqa: E402
    register_dependency_overrides_provider,
)

register_dependency_overrides_provider(lambda: app.dependency_overrides)

try:
    import taskiq_fastapi

    taskiq_fastapi.init(broker, "src.main:app")
except ImportError:  # pragma: no cover
    pass
