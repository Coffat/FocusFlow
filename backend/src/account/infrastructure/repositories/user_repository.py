import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.account.domain.models.user import User
from src.account.infrastructure.orm.user_orm import AIQuotaORM, UserORM


class SqlAlchemyUserRepository:
    """SQLAlchemy 2.0 Async Repository implementation for User and AI Quota persistence.

    Adheres strictly to the architectural rule: Repository only performs add/flush,
    NEVER commits transactions. Transactions are managed by AsyncUnitOfWork.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find_by_email(self, email: str) -> UserORM | None:
        """Query user record by email address."""
        stmt = select(UserORM).where(UserORM.email == email.lower().strip())
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_id(self, user_id: uuid.UUID) -> UserORM | None:
        """Query user record by unique identifier."""
        stmt = select(UserORM).where(UserORM.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_user_with_quota(
        self, user: UserORM | User | Any, quota: AIQuotaORM | Any = None
    ) -> UserORM:
        """Persist a new user entity and their default AI quota allocation without committing."""
        if isinstance(user, User):
            user_orm = UserORM(
                id=user.id or uuid.uuid4(),
                email=user.email,
                password_hash=user.password_hash,
                full_name=user.full_name,
                timezone=user.timezone,
                role=user.role,
                tier=user.tier,
                is_locked=user.is_locked,
            )
        else:
            user_orm = user

        self.session.add(user_orm)
        await self.session.flush()

        now = datetime.now(UTC)
        if quota is None:
            quota = AIQuotaORM(
                id=uuid.uuid4(),
                user_id=user_orm.id,
                monthly_limit=30,
                used_calls=0,
                reserved_calls=0,
                tokens_consumed=0,
                cycle_start=now,
                cycle_end=now + timedelta(days=30),
            )
        else:
            quota.user_id = user_orm.id

        self.session.add(quota)
        await self.session.flush()
        await self.session.refresh(user_orm)
        return user_orm

    async def update_password(self, user_id: uuid.UUID, password_hash: str) -> None:
        """Update password hash of an existing user record."""
        user = await self.find_by_id(user_id)
        if user is not None:
            user.password_hash = password_hash
            await self.session.flush()


# Legacy alias for backward compatibility
SqlUserRepository = SqlAlchemyUserRepository
