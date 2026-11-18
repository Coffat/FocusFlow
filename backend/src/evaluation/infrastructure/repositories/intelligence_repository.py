from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from uuid6 import uuid7

from src.evaluation.application.ports.intelligence_repository_port import (
    DuplicateWeeklyReviewConflictError,
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

    async def get_user_proof_metrics(self, user_id: UUID) -> dict[str, Any]:
        stmt = select(
            func.count(MilestoneProofORM.id),
            func.avg(MilestoneProofORM.score),
            func.avg(MilestoneProofORM.confidence),
        ).where(
            MilestoneProofORM.user_id == user_id,
            MilestoneProofORM.submitted_at.is_not(None),
        )
        row = (await self._session.execute(stmt)).one()
        count = int(row[0] or 0)
        avg_score = round(float(row[1]), 1) if row[1] is not None else None
        avg_conf = round(float(row[2]), 4) if row[2] is not None else None
        return {
            "proofs_count": count,
            "avg_proof_score": avg_score,
            "avg_proof_confidence": avg_conf,
        }

    @staticmethod
    def _to_weekly_review(row: AIReviewORM) -> WeeklyReview:
        assert row.period_start is not None and row.period_end is not None
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

    async def get_weekly_review_for_period(
        self,
        roadmap_id: UUID,
        period_start: date,
        period_end: date,
    ) -> WeeklyReview | None:
        result = await self._session.execute(
            select(AIReviewORM)
            .where(
                AIReviewORM.roadmap_id == roadmap_id,
                AIReviewORM.review_cycle == "WEEKLY",
                AIReviewORM.period_start == period_start,
                AIReviewORM.period_end == period_end,
            )
            .order_by(AIReviewORM.generated_at.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        if row is None or row.period_start is None or row.period_end is None:
            return None
        return self._to_weekly_review(row)

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
    ) -> WeeklyReview:
        summary_payload = (
            dict(quantitative_summary)
            if quantitative_summary is not None
            else {
                "source": "deterministic_features",
                "period_days": (period_end - period_start).days + 1,
            }
        )
        default_strengths = (
            strengths_feedback or "Duy trì nhịp học đều và tiếp tục ghi lại takeaway có bằng chứng."
        )
        default_bottlenecks = (
            bottlenecks_feedback
            or "Chưa đủ dữ liệu phiên học hoặc nhiệm vụ trong kỳ để xác định nút thắt định lượng."
        )
        default_actions = (
            action_recommendations
            or "Ưu tiên một phiên Prove Mode cho khái niệm có confidence thấp nhất."
        )
        bind = self._session.get_bind() if hasattr(self._session, "get_bind") else None
        dialect_name = getattr(getattr(bind, "dialect", None), "name", None)
        if dialect_name == "postgresql":
            review_id = uuid7()
            now = datetime.now(UTC)
            stmt = (
                pg_insert(AIReviewORM)
                .values(
                    id=review_id,
                    roadmap_id=roadmap_id,
                    user_id=user_id,
                    review_cycle="WEEKLY",
                    period_start=period_start,
                    period_end=period_end,
                    quantitative_summary=summary_payload,
                    strengths_feedback=default_strengths,
                    bottlenecks_feedback=default_bottlenecks,
                    action_recommendations=default_actions,
                    user_reflection_payload=reflection,
                    model_used=model_used[:100],
                    generated_at=now,
                    created_at=now,
                    updated_at=now,
                )
                .on_conflict_do_nothing(
                    index_elements=["roadmap_id", "period_start", "period_end"],
                    index_where=text("review_cycle = 'WEEKLY'"),
                )
                .returning(AIReviewORM.id)
            )
            inserted_id = (await self._session.execute(stmt)).scalar_one_or_none()
            if inserted_id is None:
                existing = await self.get_weekly_review_for_period(
                    roadmap_id, period_start, period_end
                )
                raise DuplicateWeeklyReviewConflictError(existing_review=existing)
            row = await self._session.get(AIReviewORM, inserted_id)
            if row is None:
                existing = await self.get_weekly_review_for_period(
                    roadmap_id, period_start, period_end
                )
                if existing is not None:
                    raise DuplicateWeeklyReviewConflictError(existing_review=existing)
                raise RuntimeError("Inserted weekly review could not be reloaded")
            return self._to_weekly_review(row)

        review = AIReviewORM(
            roadmap_id=roadmap_id,
            user_id=user_id,
            review_cycle="WEEKLY",
            period_start=period_start,
            period_end=period_end,
            quantitative_summary=summary_payload,
            strengths_feedback=default_strengths,
            bottlenecks_feedback=default_bottlenecks,
            action_recommendations=default_actions,
            user_reflection_payload=reflection,
            model_used=model_used[:100],
        )
        try:
            async with self._session.begin_nested():
                self._session.add(review)
                await self._session.flush()
        except IntegrityError as exc:
            existing = await self.get_weekly_review_for_period(roadmap_id, period_start, period_end)
            raise DuplicateWeeklyReviewConflictError(existing_review=existing) from exc
        return self._to_weekly_review(review)

    async def save_weekly_review(
        self,
        review: WeeklyReview,
        *,
        model_used: str = "deterministic-fallback",
    ) -> None:
        row = await self._session.get(AIReviewORM, review.id)
        if row is None:
            return
        row.strengths_feedback = review.strengths_feedback
        row.bottlenecks_feedback = review.bottlenecks_feedback
        row.action_recommendations = review.action_recommendations
        row.quantitative_summary = dict(review.quantitative_summary)
        row.model_used = model_used[:100]
        await self._session.flush()

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
        return self._to_weekly_review(row)
