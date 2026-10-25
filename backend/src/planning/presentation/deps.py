from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from src.shared_kernel.infrastructure.database.session import get_async_session


async def get_planning_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Composition root dependency for Planning Bounded Context."""
    async for session in get_async_session():
        yield session
