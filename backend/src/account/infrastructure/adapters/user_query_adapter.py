from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.account.infrastructure.orm.user_orm import UserORM
from src.account.public_api import UserQueryPort, UserSnapshotDTO


class SqlAlchemyUserQueryAdapter(UserQueryPort):
    """Cross-context read-only adapter for UserQueryPort."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_dto(row: UserORM) -> UserSnapshotDTO:
        return UserSnapshotDTO(
            id=row.id,
            email=row.email,
            full_name=row.full_name,
            role=row.role,
            tier=row.tier,
            is_locked=bool(row.is_locked),
            timezone=row.timezone or "Asia/Ho_Chi_Minh",
        )

    async def get_user_by_id(self, user_id: UUID) -> UserSnapshotDTO | None:
        row = await self._session.get(UserORM, user_id)
        if row is None:
            return None
        return self._to_dto(row)

    async def get_user_by_email(self, email: str) -> UserSnapshotDTO | None:
        stmt = select(UserORM).where(UserORM.email == email.lower().strip())
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return None
        return self._to_dto(row)


UserQueryAdapter = SqlAlchemyUserQueryAdapter
