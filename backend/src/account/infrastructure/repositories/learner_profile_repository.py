from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid6 import uuid7

from src.account.application.ports.learner_profile_repository_port import (
    LearnerProfileRecordDTO,
    LearnerProfileRepositoryPort,
)
from src.account.infrastructure.orm.user_orm import LearnerProfileORM


def _extract_slot_list(raw_slots: Any) -> tuple[str, ...]:
    if isinstance(raw_slots, list):
        return tuple(str(item) for item in raw_slots if isinstance(item, str) and item.strip())
    if isinstance(raw_slots, dict):
        preferred = raw_slots.get("preferred_periods")
        if isinstance(preferred, list):
            return tuple(str(item) for item in preferred if isinstance(item, str) and item.strip())
    return ()


def _to_record_dto(row: LearnerProfileORM) -> LearnerProfileRecordDTO:
    return LearnerProfileRecordDTO(
        user_id=row.user_id,
        optimal_focus_duration_mins=int(row.optimal_focus_duration_mins),
        peak_productivity_slots=_extract_slot_list(row.peak_productivity_slots),
        estimation_bias_factor=Decimal(str(row.estimation_bias_factor)),
        weekly_completion_rate=Decimal(str(row.weekly_completion_rate)),
        total_completed_sessions=int(row.total_completed_sessions),
        is_cold_start=bool(row.is_cold_start),
        last_aggregated_at=row.last_aggregated_at,
    )


class SqlAlchemyLearnerProfileRepository(LearnerProfileRepositoryPort):
    """SQLAlchemy repository for `learner_profiles` (only add/flush, never commit)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_user_id(self, user_id: UUID) -> LearnerProfileRecordDTO | None:
        stmt = select(LearnerProfileORM).where(LearnerProfileORM.user_id == user_id)
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _to_record_dto(row) if row is not None else None

    async def upsert(
        self,
        record: LearnerProfileRecordDTO,
        *,
        now: datetime | None = None,
    ) -> LearnerProfileRecordDTO:
        effective_now = now or datetime.now(UTC)
        stmt = (
            select(LearnerProfileORM)
            .where(LearnerProfileORM.user_id == record.user_id)
            .with_for_update()
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()

        slots_payload = list(record.peak_productivity_slots)
        if row is None:
            row = LearnerProfileORM(
                id=uuid7(),
                user_id=record.user_id,
                optimal_focus_duration_mins=record.optimal_focus_duration_mins,
                peak_productivity_slots=slots_payload,
                estimation_bias_factor=record.estimation_bias_factor,
                weekly_completion_rate=record.weekly_completion_rate,
                total_completed_sessions=record.total_completed_sessions,
                is_cold_start=record.is_cold_start,
                last_aggregated_at=record.last_aggregated_at or effective_now,
                created_at=effective_now,
                updated_at=effective_now,
            )
            self._session.add(row)
        else:
            row.optimal_focus_duration_mins = record.optimal_focus_duration_mins
            row.peak_productivity_slots = slots_payload
            row.estimation_bias_factor = record.estimation_bias_factor
            row.weekly_completion_rate = record.weekly_completion_rate
            row.total_completed_sessions = record.total_completed_sessions
            row.is_cold_start = record.is_cold_start
            row.last_aggregated_at = record.last_aggregated_at or effective_now
            row.updated_at = effective_now

        await self._session.flush()
        return _to_record_dto(row)
