from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.evaluation.application.ports.intelligence_repository_port import (
    EvaluationIntelligenceRepositoryPort,
)
from src.evaluation.domain.models.intelligence import MilestoneProof, WeeklyReview
from src.evaluation.infrastructure.orm.ai_review_orm import AIReviewORM
from src.evaluation.infrastructure.orm.milestone_proof_orm import MilestoneProofORM


class SqlAlchemyEvaluationIntelligenceRepository(EvaluationIntelligenceRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_proof(
        self, *, milestone_id: UUID, user_id: UUID, questions: list[dict[str, Any]]
    ) -> MilestoneProof:
        proof = MilestoneProofORM(
            milestone_id=milestone_id,
            user_id=user_id,
            status="READY",
            questions=questions,
        )
        self._session.add(proof)
        await self._session.flush()
        return MilestoneProof(
            id=proof.id,
            milestone_id=proof.milestone_id,
            user_id=proof.user_id,
            status=proof.status,
            questions=proof.questions,
            created_at=proof.created_at,
        )

    async def get_owned_proof(self, proof_id: UUID, user_id: UUID) -> MilestoneProof | None:
        result = await self._session.execute(
            select(MilestoneProofORM).where(
                MilestoneProofORM.id == proof_id,
                MilestoneProofORM.user_id == user_id,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return MilestoneProof(
            id=row.id,
            milestone_id=row.milestone_id,
            user_id=row.user_id,
            status=row.status,
            questions=row.questions,
            answers=row.answers,
            score=row.score,
            confidence=float(row.confidence) if row.confidence is not None else None,
            corrective_action=row.corrective_action,
            created_at=row.created_at,
            submitted_at=row.submitted_at,
        )

    async def save_proof(self, proof: MilestoneProof) -> None:
        row = await self._session.get(MilestoneProofORM, proof.id)
        if row is None:
            raise LookupError("proof not found")
        row.status = proof.status
        row.answers = proof.answers
        row.score = proof.score
        row.confidence = Decimal(str(proof.confidence)) if proof.confidence is not None else None
        row.corrective_action = proof.corrective_action
        row.submitted_at = proof.submitted_at
        await self._session.flush()

    async def create_weekly_review(
        self,
        *,
        roadmap_id: UUID,
        user_id: UUID,
        period_start: date,
        period_end: date,
        reflection: dict[str, Any],
    ) -> WeeklyReview:
        review = AIReviewORM(
            roadmap_id=roadmap_id,
            user_id=user_id,
            review_cycle="WEEKLY",
            period_start=period_start,
            period_end=period_end,
            quantitative_summary={
                "source": "deterministic_features",
                "period_days": (period_end - period_start).days + 1,
            },
            strengths_feedback="Duy trì nhịp học đều và tiếp tục ghi lại takeaway có bằng chứng.",
            bottlenecks_feedback="Cần thêm dữ liệu phiên học để xác định nút thắt ổn định.",
            action_recommendations="Ưu tiên một phiên Prove Mode cho khái niệm có confidence thấp nhất.",
            user_reflection_payload=reflection,
            model_used="mock-deterministic",
        )
        self._session.add(review)
        await self._session.flush()
        return WeeklyReview(
            id=review.id,
            roadmap_id=review.roadmap_id,
            user_id=review.user_id,
            period_start=period_start,
            period_end=period_end,
            quantitative_summary=review.quantitative_summary,
            strengths_feedback=review.strengths_feedback,
            bottlenecks_feedback=review.bottlenecks_feedback,
            action_recommendations=review.action_recommendations,
            user_reflection_payload=reflection,
            generated_at=review.generated_at,
        )

    async def latest_weekly_review(self, user_id: UUID) -> WeeklyReview | None:
        result = await self._session.execute(
            select(AIReviewORM)
            .where(AIReviewORM.user_id == user_id, AIReviewORM.review_cycle == "WEEKLY")
            .order_by(AIReviewORM.generated_at.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        if row is None or row.period_start is None or row.period_end is None:
            return None
        return WeeklyReview(
            id=row.id,
            roadmap_id=row.roadmap_id,
            user_id=row.user_id,
            period_start=row.period_start,
            period_end=row.period_end,
            quantitative_summary=row.quantitative_summary,
            strengths_feedback=row.strengths_feedback,
            bottlenecks_feedback=row.bottlenecks_feedback,
            action_recommendations=row.action_recommendations,
            user_reflection_payload=row.user_reflection_payload,
            generated_at=row.generated_at,
        )
