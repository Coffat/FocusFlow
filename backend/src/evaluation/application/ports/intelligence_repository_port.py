from datetime import date
from typing import Any, Protocol
from uuid import UUID

from src.evaluation.domain.models.intelligence import MilestoneProof, WeeklyReview


class EvaluationIntelligenceRepositoryPort(Protocol):
    async def create_proof(
        self, *, milestone_id: UUID, user_id: UUID, questions: list[dict[str, Any]]
    ) -> MilestoneProof: ...

    async def get_owned_proof(self, proof_id: UUID, user_id: UUID) -> MilestoneProof | None: ...

    async def save_proof(self, proof: MilestoneProof) -> None: ...

    async def get_user_proof_metrics(self, user_id: UUID) -> dict[str, Any]: ...

    async def create_weekly_review(
        self,
        *,
        roadmap_id: UUID,
        user_id: UUID,
        period_start: date,
        period_end: date,
        reflection: dict[str, Any],
        quantitative_summary: dict[str, Any] | None = None,
        strengths_feedback: str | None = None,
        bottlenecks_feedback: str | None = None,
        action_recommendations: str | None = None,
        model_used: str = "deterministic-fallback",
    ) -> WeeklyReview: ...

    async def save_weekly_review(
        self,
        review: WeeklyReview,
        *,
        model_used: str = "deterministic-fallback",
    ) -> None: ...

    async def latest_weekly_review(self, user_id: UUID) -> WeeklyReview | None: ...
