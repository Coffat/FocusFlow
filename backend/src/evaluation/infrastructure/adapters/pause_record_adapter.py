from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid6 import uuid7

from src.evaluation.infrastructure.orm.pause_record_orm import PauseRecordORM
from src.evaluation.public_api import PauseRecordDTO, PauseRecordPort


def _to_dto(row: PauseRecordORM) -> PauseRecordDTO:
    return PauseRecordDTO(
        id=row.id,
        roadmap_id=row.roadmap_id,
        pause_start_date=row.pause_start_date,
        pause_end_date=row.pause_end_date,
        shifted_days=int(row.shifted_days),
        reason=row.reason,
        status=row.status,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class PauseRecordAdapter(PauseRecordPort):
    """SQLAlchemy adapter for PauseRecordPort sharing the caller's AsyncSession.

    Only performs add/flush; NEVER commits (transactions owned by AsyncUnitOfWork).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_active_pause(self, roadmap_id: UUID) -> PauseRecordDTO | None:
        stmt = (
            select(PauseRecordORM)
            .where(
                PauseRecordORM.roadmap_id == roadmap_id,
                PauseRecordORM.status == "ACTIVE",
            )
            .order_by(PauseRecordORM.created_at.desc())
            .limit(1)
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _to_dto(row) if row is not None else None

    async def create_active_pause(
        self,
        *,
        roadmap_id: UUID,
        pause_start_date: date,
        pause_end_date: date | None = None,
        reason: str | None = None,
        now: datetime | None = None,
    ) -> PauseRecordDTO:
        effective_now = now or datetime.now(UTC)

        # Lock existing ACTIVE pause rows to prevent duplicate active records under concurrency
        lock_stmt = (
            select(PauseRecordORM)
            .where(
                PauseRecordORM.roadmap_id == roadmap_id,
                PauseRecordORM.status == "ACTIVE",
            )
            .with_for_update()
        )
        stale_rows = list((await self._session.execute(lock_stmt)).scalars().all())
        for stale in stale_rows:
            stale.status = "CANCELLED"
            stale.updated_at = effective_now

        eff_end = (
            pause_end_date
            if (pause_end_date is not None and pause_end_date >= pause_start_date)
            else pause_start_date
        )
        shifted_days = (eff_end - pause_start_date).days + 1

        row = PauseRecordORM(
            id=uuid7(),
            roadmap_id=roadmap_id,
            pause_start_date=pause_start_date,
            pause_end_date=eff_end,
            shifted_days=shifted_days,
            reason=reason,
            status="ACTIVE",
            created_at=effective_now,
            updated_at=effective_now,
        )
        self._session.add(row)
        await self._session.flush()
        return _to_dto(row)

    async def complete_active_pause(
        self,
        *,
        roadmap_id: UUID,
        actual_end_date: date,
        shifted_days: int | None = None,
        now: datetime | None = None,
    ) -> PauseRecordDTO | None:
        effective_now = now or datetime.now(UTC)

        lock_stmt = (
            select(PauseRecordORM)
            .where(
                PauseRecordORM.roadmap_id == roadmap_id,
                PauseRecordORM.status == "ACTIVE",
            )
            .order_by(PauseRecordORM.created_at.desc())
            .with_for_update()
        )
        active_rows = list((await self._session.execute(lock_stmt)).scalars().all())
        if not active_rows:
            return None

        row = active_rows[0]
        for extra in active_rows[1:]:
            extra.status = "CANCELLED"
            extra.updated_at = effective_now

        if shifted_days == 0:
            # Preserve chk_pause_records_shifted (shifted_days > 0) by cancelling
            row.status = "CANCELLED"
            row.updated_at = effective_now
        elif shifted_days is not None and shifted_days >= 1:
            row.pause_end_date = row.pause_start_date + timedelta(days=shifted_days - 1)
            row.shifted_days = shifted_days
            row.status = "COMPLETED"
            row.updated_at = effective_now
        else:
            eff_end = max(row.pause_start_date, actual_end_date)
            row.pause_end_date = eff_end
            row.shifted_days = (eff_end - row.pause_start_date).days + 1
            row.status = "COMPLETED"
            row.updated_at = effective_now

        await self._session.flush()
        return _to_dto(row)


SqlAlchemyPauseRecordAdapter = PauseRecordAdapter
