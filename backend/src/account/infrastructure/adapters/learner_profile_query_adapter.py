from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.account.infrastructure.orm.user_orm import LearnerProfileORM
from src.account.public_api import LearnerProfileDTO, LearnerProfileQueryPort


class LearnerProfileQueryAdapter(LearnerProfileQueryPort):
    """Cross-context read-only adapter for Zimmerman SRL Learner Profile (ADR-010).

    Returns persisted profile or cold-start defaults (opt_session_minutes=45,
    estimation_bias_beta=1.0, peak_productivity_slots={}) when no record exists.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_learner_profile(self, user_id: UUID) -> LearnerProfileDTO:
        stmt = select(LearnerProfileORM).where(LearnerProfileORM.user_id == user_id)
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return LearnerProfileDTO(
                user_id=user_id,
                opt_session_minutes=45,
                estimation_bias_beta=1.0,
                peak_productivity_slots={},
                is_cold_start=True,
            )

        raw_slots = row.peak_productivity_slots
        if isinstance(raw_slots, dict):
            slots_dict: dict[str, Any] = dict(raw_slots)
        elif isinstance(raw_slots, list):
            slots_dict = {"preferred_periods": list(raw_slots)}
        else:
            slots_dict = {}

        return LearnerProfileDTO(
            user_id=row.user_id,
            opt_session_minutes=int(row.optimal_focus_duration_mins),
            estimation_bias_beta=float(row.estimation_bias_factor),
            peak_productivity_slots=slots_dict,
            is_cold_start=bool(row.is_cold_start),
        )

    async def get_by_user_id(self, user_id: UUID) -> LearnerProfileDTO:
        """Alias for get_learner_profile."""
        return await self.get_learner_profile(user_id)

    async def get_profile(self, user_id: UUID) -> LearnerProfileDTO:
        """Alias for get_learner_profile."""
        return await self.get_learner_profile(user_id)


SqlAlchemyLearnerProfileQueryAdapter = LearnerProfileQueryAdapter
