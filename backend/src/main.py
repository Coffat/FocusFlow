import json
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from uuid6 import uuid7

from src.account.presentation.auth_router import router as auth_router
from src.account.presentation.routers import (
    availabilities_router,
)
from src.account.presentation.routers import (
    router as account_router,
)
from src.evaluation.presentation.routers import router as evaluation_router
from src.execution.presentation.routers import router as execution_router
from src.planning.presentation.routers import router as planning_router
from src.shared_kernel.config import get_settings
from src.shared_kernel.infrastructure.worker.broker import broker
from src.shared_kernel.logging import configure_logging, correlation_id_ctx


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    configure_logging()
    if not broker.is_worker_process:
        await broker.startup()
    yield
    if not broker.is_worker_process:
        await broker.shutdown()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="FocusFlow API",
        description=(
            "AI-Powered Personalized Study Planning & Execution System "
            "(Context-First Modular Monolith + Hexagonal Architecture)"
        ),
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    if settings.backend_cors_origins.startswith("["):
        origins = json.loads(settings.backend_cors_origins)
    else:
        origins = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:4200",
            "http://127.0.0.1:4200",
        ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
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

    app.include_router(account_router)
    app.include_router(availabilities_router)
    app.include_router(auth_router)
    app.include_router(planning_router)
    app.include_router(execution_router)
    app.include_router(evaluation_router)

    @app.get("/api/health", tags=["System"])
    async def health_check() -> dict[str, str]:
        return {
            "status": "healthy",
            "service": "FocusFlow Backend API",
            "version": "2.0.0",
            "architecture": "Context-First Modular Monolith + Hexagonal (Ports & Adapters)",
        }

    return app


app = create_app()

try:
    import taskiq_fastapi

    taskiq_fastapi.init(broker, "src.main:app")
except ImportError:  # pragma: no cover
    pass
