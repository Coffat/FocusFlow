from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.user_orm import AIQuotaORM, UserORM


class SqlUserRepository:
    """SQLAlchemy 2.0 Async Repository implementation for User persistence."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_email(self, email: str) -> UserORM | None:
        """Query user record by email address."""
        stmt = select(UserORM).where(UserORM.email == email.lower().strip())
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_id(self, user_id: UUID) -> UserORM | None:
        """Query user record by unique identifier."""
        stmt = select(UserORM).where(UserORM.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_user_with_quota(
        self,
        user: UserORM,
        quota: AIQuotaORM
    ) -> UserORM:
        """Atomically persist a new user entity and their default AI quota allocation."""
        self.session.add(user)
        await self.session.flush()  # Ensures user.id is generated and accessible
        quota.user_id = user.id
        self.session.add(quota)
        await self.session.commit()
        await self.session.refresh(user)
        return user
