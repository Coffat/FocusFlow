import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup actions: e.g., connect database, warm up caches
    yield
    # Shutdown actions: e.g., close connection pools


def create_app() -> FastAPI:
    app = FastAPI(
        title="FocusFlow API",
        description="Adaptive Self-Directed Learning Operating System with AI Integration",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # Configure CORS
    allowed_origins = os.getenv(
        "BACKEND_CORS_ORIGINS",
        '["http://localhost:3000", "http://127.0.0.1:3000"]',
    )
    if isinstance(allowed_origins, str) and allowed_origins.startswith("["):
        import json

        origins = json.loads(allowed_origins)
    else:
        origins = ["http://localhost:3000", "http://127.0.0.1:3000"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health Check Endpoint
    @app.get("/api/health", tags=["System"])
    async def health_check() -> dict[str, str]:
        return {
            "status": "healthy",
            "service": "FocusFlow Backend API",
            "version": "1.0.0",
            "architecture": "Hexagonal (Ports & Adapters)",
        }

    return app


app = create_app()
