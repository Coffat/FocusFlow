from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from src.account.public_api import LearnerMemoryQueryPort
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
from src.evaluation.domain.services import QuantitativeFaithfulnessValidator
from src.planning.public_api import MilestoneOwnershipQueryPort
from src.shared_kernel.application.harness.models import (
    WorkflowRun,
    WorkflowStatus,
    WorkflowStepExecution,
    WorkflowStepStatus,
    WorkflowType,
)
from src.shared_kernel.application.harness.workflow_port import WorkflowRepositoryPort
from src.shared_kernel.application.uow import AsyncUnitOfWork
from src.shared_kernel.domain.base import generate_uuid7


class EvaluationResourceNotFoundError(LookupError):
    pass


async def _record_eval_workflow(
    workflow_repo: WorkflowRepositoryPort | None,
    *,
    user_id: UUID,
    workflow_type: WorkflowType,
    step_name: str,
    roadmap_id: UUID | None = None,
    input_summary: dict[str, Any] | None = None,
    output_payload: dict[str, Any] | None = None,
) -> None:
    if workflow_repo is None:
        return
    now = datetime.now(UTC)
    run = WorkflowRun(
        id=generate_uuid7(),
        user_id=user_id,
        roadmap_id=roadmap_id,
        workflow_type=workflow_type,
        current_step=step_name,
        status=WorkflowStatus.COMPLETED,
        context_snapshot=dict(input_summary or {}),
        started_at=now,
        completed_at=now,
    )
    await workflow_repo.add_run(run)
    await workflow_repo.add_step(
        WorkflowStepExecution(
            id=generate_uuid7(),
            workflow_run_id=run.id,
            step_name=step_name,
            step_order=1,
            status=WorkflowStepStatus.COMPLETED,
            input_summary=dict(input_summary or {}),
            output_payload=dict(output_payload or {}),
            retry_count=0,
            started_at=now,
            completed_at=now,
        )
    )


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
        *,
        learner_memory_port: LearnerMemoryQueryPort | None = None,
        workflow_repo: WorkflowRepositoryPort | None = None,
    ) -> None:
        self._repository = repository
        self._ownership = ownership
        self._uow = uow
        self._learner_memory_port = learner_memory_port
        self._workflow_repo = workflow_repo

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
        await _record_eval_workflow(
            self._workflow_repo,
            user_id=user_id,
            workflow_type=WorkflowType.CONTINUOUS_LEARNING,
            step_name="PROVE_MODE_GENERATION",
            input_summary={"milestone_id": str(milestone_id)},
            output_payload={"proof_id": str(proof.id), "question_count": len(questions)},
        )
        await self._uow.commit()
        return GenerateProofResponseDTO(proof_id=proof.id, status=proof.status, questions=questions)


class SubmitMilestoneProofUseCase:
    def __init__(
        self,
        repository: EvaluationIntelligenceRepositoryPort,
        uow: AsyncUnitOfWork,
        *,
        learner_memory_port: LearnerMemoryQueryPort | None = None,
        workflow_repo: WorkflowRepositoryPort | None = None,
    ) -> None:
        self._repository = repository
        self._uow = uow
        self._learner_memory_port = learner_memory_port
        self._workflow_repo = workflow_repo

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

        if self._learner_memory_port is not None:
            mastery_score = round(float(proof.score) / 100.0, 4)
            await self._learner_memory_port.upsert_memory_and_mastery_feedback(
                user_id,
                memories=[
                    {
                        "memory_key": f"prove_mode:milestone:{milestone_id}",
                        "category": "KNOWLEDGE",
                        "epistemic_level": "OBSERVED",
                        "confidence": 0.9,
                        "value": {
                            "summary": (
                                f"Prove Mode milestone {milestone_id}: {proof.status} "
                                f"(score {proof.score}%, confidence {request.confidence}/5)."
                            ),
                            "source_workflow": "PROVE_MODE",
                            "proof_id": str(proof.id),
                            "score": proof.score,
                            "confidence": request.confidence,
                        },
                        "evidence": [{"proof_id": str(proof.id), "score": proof.score}],
                    }
                ],
                masteries=[
                    {
                        "concept_key": f"milestone:{milestone_id}",
                        "mastery_score": mastery_score,
                        "last_evidence_type": "PROVE_MODE",
                    }
                ],
            )
        await _record_eval_workflow(
            self._workflow_repo,
            user_id=user_id,
            workflow_type=WorkflowType.CONTINUOUS_LEARNING,
            step_name="PROVE_MODE_ASSESSMENT",
            input_summary={"milestone_id": str(milestone_id), "proof_id": str(proof.id)},
            output_payload={"status": proof.status, "score": proof.score},
        )
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
        *,
        learner_memory_port: LearnerMemoryQueryPort | None = None,
        workflow_repo: WorkflowRepositoryPort | None = None,
    ) -> None:
        self._repository = repository
        self._ownership = ownership
        self._uow = uow
        self._learner_memory_port = learner_memory_port
        self._workflow_repo = workflow_repo

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

        allowed_numbers = [
            float(val)
            for val in review.quantitative_summary.values()
            if isinstance(val, (int, float)) and not isinstance(val, bool)
        ]
        safe_strengths, _ = QuantitativeFaithfulnessValidator.validate_or_sanitize(
            review.strengths_feedback,
            allowed_numbers,
            "Hoàn thành các phiên học theo đúng dữ liệu thống kê tuần.",
        )
        safe_bottlenecks, _ = QuantitativeFaithfulnessValidator.validate_or_sanitize(
            review.bottlenecks_feedback,
            allowed_numbers,
            "Cần rà soát lại các khối học còn tồn đọng theo số liệu tuần.",
        )
        review.strengths_feedback = safe_strengths
        review.bottlenecks_feedback = safe_bottlenecks

        if self._learner_memory_port is not None:
            await self._learner_memory_port.upsert_memory_and_mastery_feedback(
                user_id,
                memories=[
                    {
                        "memory_key": f"weekly_review:{request.roadmap_id}:{request.period_end.isoformat()}",
                        "category": "BEHAVIOR",
                        "epistemic_level": "OBSERVED",
                        "confidence": 0.85,
                        "value": {
                            "summary": review.strengths_feedback,
                            "bottleneck": review.bottlenecks_feedback,
                            "source_workflow": "EVIDENCED_TAKEAWAY",
                            "quantitative_summary": dict(review.quantitative_summary),
                        },
                        "evidence": [
                            {
                                "review_id": str(review.id),
                                "period_start": request.period_start.isoformat(),
                                "period_end": request.period_end.isoformat(),
                            }
                        ],
                    }
                ],
            )
        await _record_eval_workflow(
            self._workflow_repo,
            user_id=user_id,
            workflow_type=WorkflowType.WEEKLY_REVIEW,
            roadmap_id=request.roadmap_id,
            step_name="WEEKLY_REVIEW_SRL",
            input_summary={
                "roadmap_id": str(request.roadmap_id),
                "period_start": request.period_start.isoformat(),
                "period_end": request.period_end.isoformat(),
            },
            output_payload={"review_id": str(review.id), "quantitative_faithfulness": 1.0},
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
