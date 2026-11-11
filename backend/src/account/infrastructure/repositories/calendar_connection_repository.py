from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.account.application.ports.calendar_connection_repository_port import (
    CalendarConnectionRepositoryPort,
)
from src.account.domain.models.calendar_connection import CalendarConnection
from src.account.infrastructure.orm.calendar_connection_orm import CalendarConnectionORM


class SqlAlchemyCalendarConnectionRepository(CalendarConnectionRepositoryPort):
    """SQLAlchemy repository for CalendarConnection Aggregate Root (UC-17)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _to_domain(self, orm: CalendarConnectionORM) -> CalendarConnection:
        return CalendarConnection(
            id=orm.id,
            user_id=orm.user_id,
            provider=orm.provider,
            external_calendar_id=orm.external_calendar_id,
            oauth_refresh_token_encrypted=orm.oauth_refresh_token_encrypted,
            sync_status=orm.sync_status,
            sync_token=orm.sync_token,
            channel_id=orm.channel_id,
            resource_id=orm.resource_id,
            channel_token_hash=orm.channel_token_hash,
            channel_expiration=orm.channel_expiration,
            source_calendars_json=list(orm.source_calendars_json or ["primary"]),
            sync_metadata_json=dict(orm.sync_metadata_json or {}),
            last_synced_at=orm.last_synced_at,
            error_detail=orm.error_detail,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    async def get_by_user_id_and_provider(
        self,
        user_id: UUID,
        provider: str = "GOOGLE",
    ) -> CalendarConnection | None:
        stmt = select(CalendarConnectionORM).where(
            CalendarConnectionORM.user_id == user_id,
            CalendarConnectionORM.provider == provider,
        )
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm is not None else None

    async def get_by_user_id(self, user_id: UUID) -> list[CalendarConnection]:
        stmt = (
            select(CalendarConnectionORM)
            .where(CalendarConnectionORM.user_id == user_id)
            .order_by(CalendarConnectionORM.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def get_by_channel_id(self, channel_id: str) -> CalendarConnection | None:
        stmt = select(CalendarConnectionORM).where(CalendarConnectionORM.channel_id == channel_id)
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm is not None else None

    async def get_expiring_active_connections(
        self,
        expiration_before: datetime,
    ) -> list[CalendarConnection]:
        stmt = (
            select(CalendarConnectionORM)
            .where(
                CalendarConnectionORM.sync_status == "ACTIVE",
                CalendarConnectionORM.channel_expiration.is_not(None),
                CalendarConnectionORM.channel_expiration <= expiration_before,
            )
            .order_by(CalendarConnectionORM.channel_expiration.asc())
        )
        result = await self.session.execute(stmt)
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def get_active_connections(self) -> list[CalendarConnection]:
        stmt = (
            select(CalendarConnectionORM)
            .where(CalendarConnectionORM.sync_status == "ACTIVE")
            .order_by(CalendarConnectionORM.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def save(self, connection: CalendarConnection) -> CalendarConnection:
        stmt = select(CalendarConnectionORM).where(CalendarConnectionORM.id == connection.id)
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()

        if orm is None:
            orm = CalendarConnectionORM(
                id=connection.id,
                user_id=connection.user_id,
                provider=connection.provider,
                external_calendar_id=connection.external_calendar_id,
                oauth_refresh_token_encrypted=connection.oauth_refresh_token_encrypted,
                sync_status=connection.sync_status,
                sync_token=connection.sync_token,
                channel_id=connection.channel_id,
                resource_id=connection.resource_id,
                channel_token_hash=connection.channel_token_hash,
                channel_expiration=connection.channel_expiration,
                source_calendars_json=connection.source_calendars_json,
                sync_metadata_json=connection.sync_metadata_json,
                last_synced_at=connection.last_synced_at,
                error_detail=connection.error_detail,
                created_at=connection.created_at,
                updated_at=connection.updated_at,
            )
            self.session.add(orm)
        else:
            orm.user_id = connection.user_id
            orm.provider = connection.provider
            orm.external_calendar_id = connection.external_calendar_id
            orm.oauth_refresh_token_encrypted = connection.oauth_refresh_token_encrypted
            orm.sync_status = connection.sync_status
            orm.sync_token = connection.sync_token
            orm.channel_id = connection.channel_id
            orm.resource_id = connection.resource_id
            orm.channel_token_hash = connection.channel_token_hash
            orm.channel_expiration = connection.channel_expiration
            orm.source_calendars_json = connection.source_calendars_json
            orm.sync_metadata_json = connection.sync_metadata_json
            orm.last_synced_at = connection.last_synced_at
            orm.error_detail = connection.error_detail
            orm.updated_at = connection.updated_at

        await self.session.flush()
        return self._to_domain(orm)

    async def delete(self, connection_id: UUID) -> bool:
        stmt = delete(CalendarConnectionORM).where(CalendarConnectionORM.id == connection_id)
        result = await self.session.execute(stmt)
        await self.session.flush()
        rowcount = getattr(result, "rowcount", 0)
        return bool(rowcount and rowcount > 0)
