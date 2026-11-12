from datetime import UTC, datetime
from uuid import UUID

from src.evaluation.application.dtos.intelligence import (
    GenerateProofResponseDTO,
    GenerateWeeklyReviewRequestDTO,
    MilestoneProofResponseDTO,
    SubmitProofRequestDTO,
    WeeklyReviewResponseDTO,
)
from src.evaluation.application.ports.intelligence_repository_port import (
    EvaluationIntelligenceRepositoryPort,
)
from src.evaluation.domain.models.intelligence import WeeklyReview
from src.planning.public_api import MilestoneOwnershipQueryPort
from src.shared_kernel.application.uow import AsyncUnitOfWork


class EvaluationResourceNotFoundError(LookupError):
    pass


def _weekly_dto(review: WeeklyReview) -> WeeklyReviewResponseDTO:
    return WeeklyReviewResponseDTO(
        id=review.id,
        roadmap_id=review.roadmap_id,
        period_start=review.period_start,
        period_end=review.period_end,
        quantitative_summary=review.quantitative_summary,
        strengths_feedback=review.strengths_feedback,
        bottlenecks_feedback=review.bottlenecks_feedback,
        action_recommendations=review.action_recommendations,
        user_reflection_payload=review.user_reflection_payload,
        generated_at=review.generated_at,
    )


class GenerateMilestoneProofUseCase:
    def __init__(
        self,
        repository: EvaluationIntelligenceRepositoryPort,
        ownership: MilestoneOwnershipQueryPort,
        uow: AsyncUnitOfWork,
    ) -> None:
        self._repository = repository
        self._ownership = ownership
        self._uow = uow

    async def execute(self, user_id: UUID, milestone_id: UUID) -> GenerateProofResponseDTO:
        milestone = await self._ownership.get_milestone(milestone_id)
        if milestone is None or milestone.user_id != user_id:
            raise EvaluationResourceNotFoundError
        questions = [
            {"id": "q1", "prompt": f"Giải thích ý chính của {milestone.title} bằng ví dụ của bạn."},
            {"id": "q2", "prompt": "Nêu một lỗi thường gặp và cách bạn phát hiện lỗi đó."},
            {"id": "q3", "prompt": "Áp dụng kiến thức này vào một tình huống mới."},
        ]
        proof = await self._repository.create_proof(
            milestone_id=milestone_id, user_id=user_id, questions=questions
        )
        await self._uow.commit()
        return GenerateProofResponseDTO(proof_id=proof.id, status=proof.status, questions=questions)


class SubmitMilestoneProofUseCase:
    def __init__(
        self, repository: EvaluationIntelligenceRepositoryPort, uow: AsyncUnitOfWork
    ) -> None:
        self._repository = repository
        self._uow = uow

    async def execute(
        self,
        user_id: UUID,
        milestone_id: UUID,
        proof_id: UUID,
        request: SubmitProofRequestDTO,
    ) -> MilestoneProofResponseDTO:
        proof = await self._repository.get_owned_proof(proof_id, user_id)
        if proof is None or proof.milestone_id != milestone_id:
            raise EvaluationResourceNotFoundError
        answered = sum(bool(str(item.get("answer", "")).strip()) for item in request.answers)
        proof.answers = request.answers
        proof.confidence = request.confidence
        proof.score = round(100 * answered / max(1, len(proof.questions)))
        proof.status = "PASSED" if proof.score >= 70 else "NEEDS_REVIEW"
        proof.corrective_action = (
            None
            if proof.status == "PASSED"
            else "Ôn lại takeaway và thử Prove Mode với ví dụ khác."
        )
        proof.submitted_at = datetime.now(UTC)
        await self._repository.save_proof(proof)
        await self._uow.commit()
        return MilestoneProofResponseDTO(
            id=proof.id,
            milestone_id=proof.milestone_id,
            status=proof.status,
            score=proof.score,
            confidence=request.confidence,
            corrective_action=proof.corrective_action,
        )


class GenerateWeeklyReviewUseCase:
    def __init__(
        self,
        repository: EvaluationIntelligenceRepositoryPort,
        ownership: MilestoneOwnershipQueryPort,
        uow: AsyncUnitOfWork,
    ) -> None:
        self._repository = repository
        self._ownership = ownership
        self._uow = uow

    async def execute(
        self, user_id: UUID, request: GenerateWeeklyReviewRequestDTO
    ) -> WeeklyReviewResponseDTO:
        if request.period_end < request.period_start:
            raise ValueError("period_end must not precede period_start")
        if not await self._ownership.roadmap_belongs_to(request.roadmap_id, user_id):
            raise EvaluationResourceNotFoundError
        review = await self._repository.create_weekly_review(
            roadmap_id=request.roadmap_id,
            user_id=user_id,
            period_start=request.period_start,
            period_end=request.period_end,
            reflection=request.reflection,
        )
        await self._uow.commit()
        return _weekly_dto(review)


class GetLatestWeeklyReviewUseCase:
    def __init__(self, repository: EvaluationIntelligenceRepositoryPort) -> None:
        self._repository = repository

    async def execute(self, user_id: UUID) -> WeeklyReviewResponseDTO:
        review = await self._repository.latest_weekly_review(user_id)
        if review is None:
            raise EvaluationResourceNotFoundError
        return _weekly_dto(review)
