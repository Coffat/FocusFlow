from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from src.shared_kernel.config import Settings, get_settings


class Base(DeclarativeBase):
    """Declarative base for all 24 SQLAlchemy 2.0 ORM models across Bounded Contexts."""


def build_async_engine(settings: Settings | None = None) -> AsyncEngine:
    """Build the canonical SQLAlchemy async engine with environment-aware pooling & DB timeouts."""
    resolved = settings if settings is not None else get_settings()
    connect_args: dict[str, Any] = {
        "timeout": resolved.db_connect_timeout,
        "command_timeout": resolved.db_command_timeout,
        "server_settings": {
            "statement_timeout": str(resolved.db_statement_timeout_ms),
            "lock_timeout": str(resolved.db_lock_timeout_ms),
        },
    }
    env = (resolved.environment or "").strip().lower()
    if env == "test":
        return create_async_engine(
            resolved.database_url,
            echo=False,
            poolclass=NullPool,
            connect_args=connect_args,
            future=True,
        )
    return create_async_engine(
        resolved.database_url,
        echo=False,
        pool_size=resolved.db_pool_size,
        max_overflow=resolved.db_max_overflow,
        pool_timeout=resolved.db_pool_timeout,
        pool_recycle=resolved.db_pool_recycle,
        pool_pre_ping=resolved.db_pool_pre_ping,
        connect_args=connect_args,
        future=True,
    )


settings = get_settings()

engine: AsyncEngine = build_async_engine(settings)

async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI & Taskiq dependency providing a scoped AsyncSession."""
    async with async_session_factory() as session:
        yield session
