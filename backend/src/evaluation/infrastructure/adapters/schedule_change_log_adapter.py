from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from uuid6 import uuid7

from src.evaluation.infrastructure.orm.schedule_change_log_orm import (
    ScheduleChangeLogORM,
)
from src.evaluation.public_api import (
    ScheduleChangeLogEntryDTO,
    ScheduleChangeLogPort,
)

_VALID_TRIGGER_TYPES: frozenset[str] = frozenset(
    {
        "DOMINO_SHIFT",
        "MANUAL_EDIT",
        "AI_REPLAN",
        "CALENDAR_SYNC",
    }
)

_TRIGGER_ALIASES: dict[str, str] = {
    "INITIAL_APPLY": "AI_REPLAN",
    "REPLAN_MERGE": "AI_REPLAN",
    "PROPOSAL_APPLY": "AI_REPLAN",
    "MANUAL_APPLY": "MANUAL_EDIT",
    "MANUAL": "MANUAL_EDIT",
}


def normalize_trigger_type(trigger_type: str) -> str:
    """Normalize trigger_type to match DB CHECK constraint `chk_sched_change_logs_trigger`."""
    upper = (trigger_type or "AI_REPLAN").strip().upper()
    if upper in _VALID_TRIGGER_TYPES:
        return upper
    return _TRIGGER_ALIASES.get(upper, "AI_REPLAN")


class ScheduleChangeLogAdapter(ScheduleChangeLogPort):
    """SQLAlchemy adapter for ScheduleChangeLogPort.

    Inserts into `schedule_change_logs` within the active AsyncSession / UnitOfWork
    (only `add`/`flush`, never `commit`).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def log_schedule_change(
        self,
        *,
        roadmap_id: UUID,
        trigger_type: str = "AI_REPLAN",
        schedule_id: UUID | None = None,
        task_id: UUID | None = None,
        reason: str | None = None,
        affected_tasks_count: int = 1,
        total_shifted_minutes: int = 0,
        diff_payload: dict[str, Any] | None = None,
        now: datetime | None = None,
    ) -> ScheduleChangeLogEntryDTO:
        normalized_trigger = normalize_trigger_type(trigger_type)
        effective_now = now or datetime.now(UTC)
        payload = dict(diff_payload) if isinstance(diff_payload, dict) else {}
        if trigger_type != normalized_trigger and "original_trigger_type" not in payload:
            payload["original_trigger_type"] = trigger_type

        row = ScheduleChangeLogORM(
            id=uuid7(),
            roadmap_id=roadmap_id,
            schedule_id=schedule_id,
            task_id=task_id,
            trigger_type=normalized_trigger,
            reason=reason,
            affected_tasks_count=max(0, int(affected_tasks_count)),
            total_shifted_minutes=max(0, int(total_shifted_minutes)),
            diff_payload=payload,
            created_at=effective_now,
        )
        self._session.add(row)
        await self._session.flush()

        return ScheduleChangeLogEntryDTO(
            id=row.id,
            roadmap_id=row.roadmap_id,
            schedule_id=row.schedule_id,
            task_id=row.task_id,
            trigger_type=row.trigger_type,
            reason=row.reason,
            affected_tasks_count=row.affected_tasks_count,
            total_shifted_minutes=row.total_shifted_minutes,
            diff_payload=row.diff_payload,
            created_at=row.created_at,
        )


SqlAlchemyScheduleChangeLogAdapter = ScheduleChangeLogAdapter
