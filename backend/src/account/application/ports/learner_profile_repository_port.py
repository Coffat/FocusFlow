from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class LearnerProfileRecordDTO:
    """Persisted Zimmerman SRL LearnerProfile snapshot owned by Account context."""

    user_id: UUID
    optimal_focus_duration_mins: int
    peak_productivity_slots: tuple[str, ...]
    estimation_bias_factor: Decimal
    weekly_completion_rate: Decimal
    total_completed_sessions: int
    is_cold_start: bool
    last_aggregated_at: datetime | None = None


class LearnerProfileRepositoryPort(Protocol):
    """Repository port for reading and upserting `learner_profiles` in Account context."""

    async def get_by_user_id(self, user_id: UUID) -> LearnerProfileRecordDTO | None: ...

    async def upsert(
        self,
        record: LearnerProfileRecordDTO,
        *,
        now: datetime | None = None,
    ) -> LearnerProfileRecordDTO: ...
