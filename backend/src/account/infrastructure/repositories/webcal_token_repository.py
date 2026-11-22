from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.account.application.ports.webcal_token_repository_port import (
    WebcalTokenRecord,
    WebcalTokenRepositoryPort,
)
from src.account.infrastructure.orm.user_orm import WebCalTokenORM


class SqlAlchemyWebcalTokenRepository(WebcalTokenRepositoryPort):
    """SQLAlchemy 2.0 async repository for `webcal_tokens` (add/flush only, never commit)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_record(row: WebCalTokenORM) -> WebcalTokenRecord:
        return WebcalTokenRecord(
            id=row.id,
            user_id=row.user_id,
            token_hash=row.token_hash,
            is_active=row.is_active,
            rotated_at=row.rotated_at,
            last_used_at=row.last_used_at,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def get_by_user_id(self, user_id: UUID) -> WebcalTokenRecord | None:
        stmt = select(WebCalTokenORM).where(WebCalTokenORM.user_id == user_id)
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return self._to_record(row) if row is not None else None

    async def get_active_by_token_hash(self, token_hash: str) -> WebcalTokenRecord | None:
        stmt = select(WebCalTokenORM).where(
            WebCalTokenORM.token_hash == token_hash,
            WebCalTokenORM.is_active.is_(True),
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return self._to_record(row) if row is not None else None

    async def upsert_token(
        self, user_id: UUID, token_hash: str, now: datetime
    ) -> WebcalTokenRecord:
        stmt = select(WebCalTokenORM).where(WebCalTokenORM.user_id == user_id)
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is not None:
            row.token_hash = token_hash
            row.is_active = True
            row.rotated_at = now
            row.updated_at = now
        else:
            row = WebCalTokenORM(
                user_id=user_id,
                token_hash=token_hash,
                is_active=True,
                rotated_at=now,
                created_at=now,
                updated_at=now,
            )
            self._session.add(row)
        await self._session.flush()
        return self._to_record(row)

    async def revoke_for_user(self, user_id: UUID, now: datetime) -> bool:
        stmt = select(WebCalTokenORM).where(WebCalTokenORM.user_id == user_id)
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return False
        row.is_active = False
        row.updated_at = now
        await self._session.flush()
        return True

    async def touch_last_used(self, token_id: UUID, now: datetime) -> None:
        stmt = (
            update(WebCalTokenORM)
            .where(WebCalTokenORM.id == token_id)
            .values(last_used_at=now, updated_at=now)
        )
        await self._session.execute(stmt)
        await self._session.flush()
