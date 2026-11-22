from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from uuid6 import uuid7

from src.account.application.ports.notification_repository_port import (
    NotificationRecordDTO,
    NotificationRepositoryPort,
)
from src.account.infrastructure.orm.notification_orm import NotificationORM


def _to_dto(row: NotificationORM) -> NotificationRecordDTO:
    return NotificationRecordDTO(
        id=row.id,
        user_id=row.user_id,
        event_id=row.event_id,
        notification_type=row.notification_type,
        title=row.title,
        content=row.content,
        resource_url=row.resource_url,
        is_read=row.is_read,
        read_at=row.read_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlAlchemyNotificationRepository(NotificationRepositoryPort):
    """SQLAlchemy 2.0 Async Repository for persistent notifications (`notifications`).

    Adheres to UoW rules: only add/flush/execute, NEVER commits transactions.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_idempotent(
        self,
        *,
        user_id: UUID,
        notification_type: str,
        title: str,
        content: str,
        event_id: UUID | None = None,
        resource_url: str | None = None,
    ) -> NotificationRecordDTO | None:
        now = datetime.now(UTC)
        new_id = uuid7()
        if event_id is not None:
            stmt = (
                pg_insert(NotificationORM)
                .values(
                    id=new_id,
                    user_id=user_id,
                    event_id=event_id,
                    notification_type=notification_type,
                    title=title,
                    content=content,
                    resource_url=resource_url,
                    is_read=False,
                    read_at=None,
                    created_at=now,
                    updated_at=now,
                )
                .on_conflict_do_nothing(
                    index_elements=["user_id", "event_id", "notification_type"],
                    index_where=NotificationORM.event_id.is_not(None),
                )
                .returning(NotificationORM)
            )
            result = await self._session.execute(stmt)
            inserted = result.scalar_one_or_none()
            await self._session.flush()
            return _to_dto(inserted) if inserted is not None else None

        orm_obj = NotificationORM(
            id=new_id,
            user_id=user_id,
            event_id=None,
            notification_type=notification_type,
            title=title,
            content=content,
            resource_url=resource_url,
            is_read=False,
            read_at=None,
            created_at=now,
            updated_at=now,
        )
        self._session.add(orm_obj)
        await self._session.flush()
        return _to_dto(orm_obj)

    async def list_for_user(
        self,
        user_id: UUID,
        *,
        limit: int = 20,
        offset: int = 0,
        unread_only: bool = False,
    ) -> tuple[list[NotificationRecordDTO], int, int]:
        base_filter = [NotificationORM.user_id == user_id]
        if unread_only:
            base_filter.append(NotificationORM.is_read.is_(False))

        total_stmt = select(func.count(NotificationORM.id)).where(*base_filter)
        total = int((await self._session.execute(total_stmt)).scalar_one() or 0)

        unread_stmt = select(func.count(NotificationORM.id)).where(
            NotificationORM.user_id == user_id,
            NotificationORM.is_read.is_(False),
        )
        unread_count = int((await self._session.execute(unread_stmt)).scalar_one() or 0)

        items_stmt = (
            select(NotificationORM)
            .where(*base_filter)
            .order_by(NotificationORM.created_at.desc(), NotificationORM.id.desc())
            .offset(max(0, offset))
            .limit(max(1, min(limit, 100)))
        )
        rows = (await self._session.execute(items_stmt)).scalars().all()
        return [_to_dto(r) for r in rows], total, unread_count

    async def mark_read(
        self,
        notification_id: UUID,
        user_id: UUID,
        *,
        now: datetime,
    ) -> NotificationRecordDTO | None:
        stmt = select(NotificationORM).where(
            NotificationORM.id == notification_id,
            NotificationORM.user_id == user_id,
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return None

        if not row.is_read:
            row.is_read = True
            row.read_at = now
            await self._session.flush()
            await self._session.refresh(row)
        return _to_dto(row)

    async def mark_all_read(
        self,
        user_id: UUID,
        *,
        now: datetime,
    ) -> int:
        stmt = (
            update(NotificationORM)
            .where(
                NotificationORM.user_id == user_id,
                NotificationORM.is_read.is_(False),
            )
            .values(is_read=True, read_at=now)
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        rowcount: int = getattr(result, "rowcount", 0) or 0
        return rowcount
