from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager, nullcontext
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog
from pydantic import BaseModel, ValidationError

from src.account.public_api import LearnerMemoryQueryPort
from src.evaluation.application.dtos.intelligence import (
    GenerateProofResponseDTO,
    GenerateWeeklyReviewRequestDTO,
    LatestMilestoneProofResponseDTO,
    MilestoneProofResponseDTO,
    ProveAnswerFeedbackSchema,
    ProveGradingLLMOutput,
    ProveQuestionItemSchema,
    ProveQuestionsLLMOutput,
    SubmitProofRequestDTO,
    WeeklyReviewLLMOutput,
    WeeklyReviewResponseDTO,
)
from src.evaluation.application.ports.intelligence_repository_port import (
    DuplicateWeeklyReviewConflictError,
    EvaluationIntelligenceRepositoryPort,
)
from src.evaluation.application.prompts import (
    PROVE_MODE_GRADER_PROMPT,
    PROVE_QUESTION_GENERATOR_PROMPT,
    WEEKLY_REVIEW_ADVISOR_PROMPT,
    build_evaluation_prompt_registry,
    build_prove_grader_prompt,
    build_prove_question_prompt,
    build_weekly_review_prompt,
)
from src.evaluation.domain.exceptions import (
    ProofAlreadyGradedError,
    ProveGradingUnavailableError,
)
from src.evaluation.domain.models.intelligence import WeeklyReview
from src.evaluation.domain.services import QuantitativeFaithfulnessValidator
from src.execution.public_api import WeeklyExecutionMetricsDTO, WeeklyExecutionMetricsQueryPort
from src.planning.public_api import MilestoneOwnershipQueryPort
from src.shared_kernel.application.harness.execution_manager import (
    AIExecutionManager,
    AIQuotaPort,
)
from src.shared_kernel.application.harness.models import (
    WorkflowRun,
    WorkflowStatus,
    WorkflowStepExecution,
    WorkflowStepStatus,
    WorkflowType,
)
from src.shared_kernel.application.harness.prompt_registry import build_prompt_audit_metadata
from src.shared_kernel.application.harness.workflow_port import WorkflowRepositoryPort
from src.shared_kernel.application.llm_port import LLMProviderPort, SchemaMismatchError
from src.shared_kernel.application.uow import AsyncUnitOfWork
from src.shared_kernel.config import get_settings
from src.shared_kernel.domain.base import generate_uuid7

logger = structlog.get_logger(__name__)

_PROVE_PASS_THRESHOLD = 70

__all__ = [
    "EvaluationResourceNotFoundError",
    "GenerateMilestoneProofUseCase",
    "GenerateWeeklyReviewUseCase",
    "GetLatestMilestoneProofUseCase",
    "GetLatestWeeklyReviewUseCase",
    "ProofAlreadyGradedError",
    "ProveAnswerFeedbackSchema",
    "ProveGradingLLMOutput",
    "ProveGradingUnavailableError",
    "ProveQuestionItemSchema",
    "ProveQuestionsLLMOutput",
    "SubmitMilestoneProofUseCase",
    "WeeklyReviewLLMOutput",
    "WeeklyReviewWriteScope",
    "WeeklyReviewWriteScopeFactory",
]


class EvaluationResourceNotFoundError(LookupError):
    pass


@dataclass(frozen=True, slots=True)
class WeeklyReviewWriteScope:
    """Fresh write-phase dependencies opened strictly after external LLM execution."""

    uow: AsyncUnitOfWork
    repository: EvaluationIntelligenceRepositoryPort
    learner_memory_port: LearnerMemoryQueryPort | None = None
    workflow_repo: WorkflowRepositoryPort | None = None


WeeklyReviewWriteScopeFactory = Callable[[], AbstractAsyncContextManager[WeeklyReviewWriteScope]]


def _classify_ai_failure_reason(exc: Exception, prefix: str) -> str:
    if isinstance(exc, (TimeoutError, asyncio.TimeoutError)):
        return f"{prefix}_TIMEOUT"
    if isinstance(exc, (ValidationError, json.JSONDecodeError, SchemaMismatchError)):
        return f"{prefix}_SCHEMA_ERROR"
    if isinstance(exc, PermissionError):
        return f"{prefix}_PERMISSION_ERROR"
    return f"{prefix}_EXECUTION_ERROR"


async def _close_read_transaction(uow: AsyncUnitOfWork) -> None:
    close_fn = getattr(uow, "close", None)
    if callable(close_fn):
        await close_fn()
        return
    rollback_fn = getattr(uow, "rollback", None)
    if callable(rollback_fn):
        await rollback_fn()


async def _record_eval_workflow(
    workflow_repo: WorkflowRepositoryPort | None,
    *,
    user_id: UUID,
    workflow_type: WorkflowType,
    step_name: str,
    roadmap_id: UUID | None = None,
    input_summary: dict[str, Any] | None = None,
    output_payload: dict[str, Any] | None = None,
    step_status: WorkflowStepStatus = WorkflowStepStatus.COMPLETED,
    error_detail: str | None = None,
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
        status=(
            WorkflowStatus.FAILED
            if step_status is WorkflowStepStatus.FAILED
            else WorkflowStatus.COMPLETED
        ),
        context_snapshot=dict(input_summary or {}),
        error_detail=error_detail,
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
            status=step_status,
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
        llm_provider: LLMProviderPort | None = None,
        quota_port: AIQuotaPort | None = None,
    ) -> None:
        self._repository = repository
        self._ownership = ownership
        self._uow = uow
        self._learner_memory_port = learner_memory_port
        self._workflow_repo = workflow_repo
        self._llm_provider = llm_provider
        self._quota_port = quota_port

    async def execute(self, user_id: UUID, milestone_id: UUID) -> GenerateProofResponseDTO:
        milestone = await self._ownership.get_milestone(milestone_id)
        if milestone is None or milestone.user_id != user_id:
            await _close_read_transaction(self._uow)
            raise EvaluationResourceNotFoundError
        milestone_title = milestone.title
        milestone_description = getattr(milestone, "description", None)
        milestone_learning_outcomes = getattr(milestone, "learning_outcomes", ()) or ()
        milestone_completion_criteria = getattr(milestone, "completion_criteria", None)
        milestone_required_concepts = getattr(milestone, "required_concepts", ()) or ()
        milestone_unverified_concepts = getattr(milestone, "unverified_concepts", ()) or ()
        milestone_task_titles = getattr(milestone, "task_titles", ()) or ()

        # Close read transaction / release DB pool connection strictly BEFORE external LLM call.
        await _close_read_transaction(self._uow)

        default_questions = [
            {"id": "q1", "prompt": f"Giải thích ý chính của {milestone_title} bằng ví dụ của bạn."},
            {"id": "q2", "prompt": "Nêu một lỗi thường gặp và cách bạn phát hiện lỗi đó."},
            {"id": "q3", "prompt": "Áp dụng kiến thức này vào một tình huống mới."},
        ]
        questions = default_questions
        model_used = "deterministic-rule-v1"
        llm_recorded = False
        fallback_reason_code: str | None = None
        prompt_tpl = build_evaluation_prompt_registry().latest(
            PROVE_QUESTION_GENERATOR_PROMPT.prompt_id
        )
        prompt_audit = build_prompt_audit_metadata(prompt_tpl)
        if self._llm_provider is not None:
            user_prompt = build_prove_question_prompt(
                milestone_title=milestone_title,
                description=milestone_description,
                learning_outcomes=milestone_learning_outcomes,
                completion_criteria=milestone_completion_criteria,
                required_concepts=milestone_required_concepts,
                unverified_concepts=milestone_unverified_concepts,
                task_titles=milestone_task_titles,
            )
            try:
                manager = AIExecutionManager(
                    provider=self._llm_provider,
                    quota=self._quota_port,
                    manage_quota=self._quota_port is not None,
                    max_retries=1,
                    timeout_seconds=float(get_settings().ai_prove_question_timeout_seconds),
                    workflow_repo=self._workflow_repo,
                )
                exec_res = await manager.execute(
                    user_id=user_id,
                    operation_type="PROVE_MODE_GENERATION",
                    system_prompt=prompt_tpl.system_template,
                    user_prompt=user_prompt,
                    response_schema=ProveQuestionsLLMOutput,
                    thinking_level=PROVE_QUESTION_GENERATOR_PROMPT.thinking_level,
                    workflow_type=WorkflowType.CONTINUOUS_LEARNING,
                    step_name="PROVE_MODE_GENERATION",
                    context_snapshot={"milestone_id": str(milestone_id)},
                    prompt_template=prompt_tpl,
                )
                raw_resp = (
                    exec_res.value.model_dump()
                    if isinstance(exec_res.value, BaseModel)
                    else exec_res.value
                )
                raw_q_list = raw_resp.get("questions") if isinstance(raw_resp, dict) else None
                parsed_questions: list[dict[str, Any]] = []
                if isinstance(raw_q_list, list) and len(raw_q_list) == 3:
                    for idx, q_item in enumerate(raw_q_list):
                        if isinstance(q_item, dict):
                            prompt_str = str(q_item.get("prompt") or "").strip()
                            if prompt_str:
                                parsed_questions.append(
                                    {
                                        "id": str(q_item.get("id") or f"q{idx + 1}"),
                                        "prompt": prompt_str,
                                    }
                                )
                if len(parsed_questions) == 3:
                    questions = parsed_questions
                    model_used = str(exec_res.model_id or "gemini-3.8-flash")
                    llm_recorded = True
                else:
                    fallback_reason_code = "PROVE_QUESTION_GEN_INVALID_PAYLOAD"
            except (
                TimeoutError,
                ValidationError,
                json.JSONDecodeError,
                PermissionError,
                ValueError,
                RuntimeError,
                OSError,
            ) as exc:
                fallback_reason_code = _classify_ai_failure_reason(exc, "PROVE_QUESTION_GEN")
                logger.warning(
                    "prove_question_generation_fallback",
                    milestone_id=str(milestone_id),
                    reason_code=fallback_reason_code,
                    error_type=type(exc).__name__,
                )
                questions = default_questions
        else:
            fallback_reason_code = "PROVE_QUESTION_GEN_NO_PROVIDER"

        proof = await self._repository.create_proof(
            milestone_id=milestone_id, user_id=user_id, questions=questions
        )
        if not llm_recorded:
            await _record_eval_workflow(
                self._workflow_repo,
                user_id=user_id,
                workflow_type=WorkflowType.CONTINUOUS_LEARNING,
                step_name="PROVE_MODE_GENERATION",
                input_summary={"milestone_id": str(milestone_id), **prompt_audit},
                output_payload={
                    "proof_id": str(proof.id),
                    "question_count": len(questions),
                    "model_used": model_used,
                    "fallback_reason_code": fallback_reason_code,
                    "prompt_tokens": 0,
                    "output_tokens": 0,
                    "completion_tokens": 0,
                    "thinking_tokens": 0,
                },
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
        llm_provider: LLMProviderPort | None = None,
        quota_port: AIQuotaPort | None = None,
    ) -> None:
        self._repository = repository
        self._uow = uow
        self._learner_memory_port = learner_memory_port
        self._workflow_repo = workflow_repo
        self._llm_provider = llm_provider
        self._quota_port = quota_port

    async def execute(
        self,
        user_id: UUID,
        milestone_id: UUID,
        proof_id: UUID,
        request: SubmitProofRequestDTO,
    ) -> MilestoneProofResponseDTO:
        proof = await self._repository.get_owned_proof(proof_id, user_id)
        if proof is None or proof.milestone_id != milestone_id:
            await _close_read_transaction(self._uow)
            raise EvaluationResourceNotFoundError

        # Idempotency / status guard: never overwrite an already-graded proof or double-charge quota.
        if (proof.submitted_at is not None and proof.score is not None) or proof.status == "PASSED":
            await _close_read_transaction(self._uow)
            raise ProofAlreadyGradedError

        answered = sum(bool(str(item.get("answer", "")).strip()) for item in request.answers)
        if answered == 0:
            await _close_read_transaction(self._uow)
            raise ValueError("Vui lòng trả lời ít nhất một câu hỏi trước khi nộp bài.")

        questions_snapshot = list(proof.questions)
        # Close read transaction / release DB pool connection strictly BEFORE external LLM call.
        await _close_read_transaction(self._uow)

        grader_tpl = build_evaluation_prompt_registry().latest(PROVE_MODE_GRADER_PROMPT.prompt_id)
        grader_audit = build_prompt_audit_metadata(grader_tpl)

        if self._llm_provider is None:
            await _record_eval_workflow(
                self._workflow_repo,
                user_id=user_id,
                workflow_type=WorkflowType.CONTINUOUS_LEARNING,
                step_name="PROVE_MODE_ASSESSMENT",
                input_summary={
                    "milestone_id": str(milestone_id),
                    "proof_id": str(proof.id),
                    **grader_audit,
                },
                output_payload={
                    "status": proof.status,
                    "score": None,
                    "is_verified": False,
                    "calibration_error": None,
                    "model_used": "unavailable",
                    "fallback_reason_code": "PROVE_GRADER_UNAVAILABLE",
                    "prompt_tokens": 0,
                    "output_tokens": 0,
                    "completion_tokens": 0,
                    "thinking_tokens": 0,
                },
                step_status=WorkflowStepStatus.FAILED,
                error_detail="PROVE_GRADER_UNAVAILABLE",
            )
            await self._uow.commit()
            raise ProveGradingUnavailableError(reason_code="PROVE_GRADER_UNAVAILABLE")

        q_map = {
            str(q.get("id", f"q{i + 1}")): str(q.get("prompt", ""))
            for i, q in enumerate(questions_snapshot)
        }
        qa_pairs: list[tuple[str, str, str]] = []
        for idx, ans in enumerate(request.answers):
            raw_qid = str(ans.get("question_id") or ans.get("id") or f"q{idx + 1}")
            raw_ans = str(ans.get("answer") or "")
            qa_pairs.append((raw_qid, q_map.get(raw_qid, ""), raw_ans))

        try:
            manager = AIExecutionManager(
                provider=self._llm_provider,
                quota=self._quota_port,
                manage_quota=self._quota_port is not None,
                max_retries=1,
                timeout_seconds=float(get_settings().ai_prove_grader_timeout_seconds),
                workflow_repo=self._workflow_repo,
            )
            exec_res = await manager.execute(
                user_id=user_id,
                operation_type="PROVE_MODE_ASSESSMENT",
                system_prompt=grader_tpl.system_template,
                user_prompt=build_prove_grader_prompt(qa_pairs),
                response_schema=ProveGradingLLMOutput,
                thinking_level=PROVE_MODE_GRADER_PROMPT.thinking_level,
                workflow_type=WorkflowType.CONTINUOUS_LEARNING,
                step_name="PROVE_MODE_ASSESSMENT",
                context_snapshot={"milestone_id": str(milestone_id), "proof_id": str(proof.id)},
                prompt_template=grader_tpl,
            )
            raw_grade = (
                exec_res.value.model_dump()
                if isinstance(exec_res.value, BaseModel)
                else exec_res.value
            )
            if not isinstance(raw_grade, dict):
                raise ValueError("PROVE_GRADER_INVALID_PAYLOAD")
            graded = ProveGradingLLMOutput.model_validate(raw_grade)
        except (
            TimeoutError,
            ValidationError,
            json.JSONDecodeError,
            PermissionError,
            ValueError,
            RuntimeError,
            OSError,
        ) as exc:
            # Never conflate technical AI grading failure with score=0 / NEEDS_REVIEW.
            # Leave MilestoneProof untouched (READY, score=None, submitted_at=None) and never touch mastery.
            # Quota reservation is already released by AIExecutionManager._cleanup_on_failure().
            fallback_reason_code = _classify_ai_failure_reason(exc, "PROVE_GRADER")
            logger.warning(
                "prove_grader_unavailable",
                proof_id=str(proof_id),
                milestone_id=str(milestone_id),
                reason_code=fallback_reason_code,
                error_type=type(exc).__name__,
            )
            await _record_eval_workflow(
                self._workflow_repo,
                user_id=user_id,
                workflow_type=WorkflowType.CONTINUOUS_LEARNING,
                step_name="PROVE_MODE_ASSESSMENT",
                input_summary={
                    "milestone_id": str(milestone_id),
                    "proof_id": str(proof.id),
                    **grader_audit,
                },
                output_payload={
                    "status": proof.status,
                    "score": None,
                    "is_verified": False,
                    "calibration_error": None,
                    "model_used": "unavailable",
                    "fallback_reason_code": fallback_reason_code,
                    "prompt_tokens": 0,
                    "output_tokens": 0,
                    "completion_tokens": 0,
                    "thinking_tokens": 0,
                },
                step_status=WorkflowStepStatus.FAILED,
                error_detail=fallback_reason_code,
            )
            await self._uow.commit()
            raise ProveGradingUnavailableError(reason_code=fallback_reason_code) from exc

        total_score = max(
            0,
            min(
                100,
                int(graded.conceptual_understanding_score)
                + int(graded.example_grounding_score)
                + int(graded.practical_application_score),
            ),
        )
        proof.answers = request.answers
        proof.confidence = request.confidence
        proof.score = total_score
        proof.status = "PASSED" if total_score >= _PROVE_PASS_THRESHOLD else "NEEDS_REVIEW"
        proof.corrective_action = (
            None
            if proof.status == "PASSED"
            else (
                graded.corrective_action.strip()
                if graded.corrective_action
                else "Ôn lại takeaway và thử Prove Mode với ví dụ cụ thể hơn."
            )
        )
        proof.submitted_at = datetime.now(UTC)
        answer_evidence = [item.model_dump() for item in graded.answer_evidence]
        is_verified = True
        calibration_error = round(float(request.confidence) - (float(total_score) / 100.0), 4)
        model_used = str(exec_res.model_id or "gemini-3.8-flash")

        await self._repository.save_proof(proof)

        # Strictly upsert mastery & memory evidence inside the verified grading branch.
        if self._learner_memory_port is not None:
            mastery_score = round(float(total_score) / 100.0, 4)
            confidence_pct = round(float(request.confidence) * 100)
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
                                f"(score {total_score}%, confidence {confidence_pct}%)."
                            ),
                            "source_workflow": "PROVE_MODE",
                            "proof_id": str(proof.id),
                            "score": total_score,
                            "confidence": round(float(request.confidence), 4),
                            "confidence_pct": confidence_pct,
                            "calibration_error": calibration_error,
                            "model_used": model_used,
                        },
                        "evidence": [{"proof_id": str(proof.id), "score": total_score}],
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

        await self._uow.commit()
        return MilestoneProofResponseDTO(
            id=proof.id,
            milestone_id=proof.milestone_id,
            status=proof.status,
            score=total_score,
            confidence=request.confidence,
            corrective_action=proof.corrective_action,
            is_verified=is_verified,
            calibration_error=calibration_error,
            answer_evidence=answer_evidence,
        )


def _extract_allowed_numbers(value: Any) -> list[float]:
    """Recursively collect numeric metrics from quantitative_summary for faithfulness checks."""
    nums: list[float] = []
    if isinstance(value, bool):
        return nums
    if isinstance(value, (int, float)):
        nums.append(float(value))
    elif isinstance(value, dict):
        for item in value.values():
            nums.extend(_extract_allowed_numbers(item))
    elif isinstance(value, (list, tuple)):
        for item in value:
            nums.extend(_extract_allowed_numbers(item))
    return nums


class GenerateWeeklyReviewUseCase:
    def __init__(
        self,
        repository: EvaluationIntelligenceRepositoryPort,
        ownership: MilestoneOwnershipQueryPort,
        uow: AsyncUnitOfWork,
        *,
        learner_memory_port: LearnerMemoryQueryPort | None = None,
        execution_metrics_port: WeeklyExecutionMetricsQueryPort | None = None,
        workflow_repo: WorkflowRepositoryPort | None = None,
        llm_provider: LLMProviderPort | None = None,
        quota_port: AIQuotaPort | None = None,
        write_scope_factory: WeeklyReviewWriteScopeFactory | None = None,
    ) -> None:
        self._repository = repository
        self._ownership = ownership
        self._uow = uow
        self._learner_memory_port = learner_memory_port
        self._execution_metrics_port = execution_metrics_port
        self._workflow_repo = workflow_repo
        self._llm_provider = llm_provider
        self._quota_port = quota_port
        self._write_scope_factory = write_scope_factory

    @staticmethod
    def _build_quantitative_summary(
        *,
        period_days: int,
        exec_metrics: WeeklyExecutionMetricsDTO,
        masteries: list[Any],
        proof_metrics: dict[str, Any],
    ) -> tuple[dict[str, Any], bool]:
        avg_mastery_score: float | None = None
        lowest_concept: str | None = None
        if masteries:
            avg_mastery_score = round(
                sum(float(getattr(m, "mastery_score", 0.0)) for m in masteries) / len(masteries),
                4,
            )
            lowest = min(masteries, key=lambda m: float(getattr(m, "mastery_score", 0.0)))
            lowest_concept = str(getattr(lowest, "concept_id", "") or "") or None

        proofs_count = int(proof_metrics.get("proofs_count", 0) or 0)
        has_sufficient_data = any(
            (
                exec_metrics.completed_minutes > 0,
                exec_metrics.planned_minutes > 0,
                exec_metrics.completed_sessions_count > 0,
                exec_metrics.planned_tasks_count > 0,
                exec_metrics.overdue_tasks_count > 0,
                len(masteries) > 0,
                proofs_count > 0,
            )
        )
        summary: dict[str, Any] = {
            "source": "deterministic_features",
            "period_days": period_days,
            "completed_minutes": exec_metrics.completed_minutes,
            "planned_minutes": exec_metrics.planned_minutes,
            "completed_sessions_count": exec_metrics.completed_sessions_count,
            "completed_tasks_count": exec_metrics.completed_tasks_count,
            "planned_tasks_count": exec_metrics.planned_tasks_count,
            "overdue_tasks_count": exec_metrics.overdue_tasks_count,
            "adherence_rate_pct": exec_metrics.adherence_rate_pct,
            "task_type_breakdown": dict(exec_metrics.task_type_breakdown),
            "previous_week_completed_minutes": exec_metrics.previous_week_completed_minutes,
            "week_over_week_delta_pct": exec_metrics.week_over_week_delta_pct,
            "mastery_count": len(masteries),
            "avg_mastery_score": avg_mastery_score,
            "lowest_mastery_concept": lowest_concept,
            "proofs_count": proofs_count,
            "avg_proof_score": proof_metrics.get("avg_proof_score"),
            "avg_proof_confidence": proof_metrics.get("avg_proof_confidence"),
            "has_sufficient_data": has_sufficient_data,
        }
        return summary, has_sufficient_data

    @staticmethod
    def _build_deterministic_fallback(
        quantitative_summary: dict[str, Any],
        *,
        has_sufficient_data: bool,
    ) -> tuple[str, str, str]:
        if not has_sufficient_data:
            return (
                "Hiện chưa có đủ dữ liệu phiên học hoặc nhiệm vụ trong kỳ để đánh giá định lượng.",
                "Thiếu dữ liệu thời lượng học, độ tuân thủ lịch hoặc kết quả kiểm tra để chỉ ra nút thắt cụ thể.",
                "Hãy hoàn thành ít nhất một phiên học hoặc nộp một bài Prove Mode để hệ thống tổng hợp số liệu tuần tới.",
            )
        completed_sessions = int(quantitative_summary.get("completed_sessions_count", 0) or 0)
        completed_minutes = int(quantitative_summary.get("completed_minutes", 0) or 0)
        planned_minutes = int(quantitative_summary.get("planned_minutes", 0) or 0)
        adherence = quantitative_summary.get("adherence_rate_pct")
        overdue = int(quantitative_summary.get("overdue_tasks_count", 0) or 0)

        strengths = (
            f"Bạn đã hoàn thành {completed_sessions} phiên học ({completed_minutes} phút"
            + (f" / {planned_minutes} phút kế hoạch" if planned_minutes > 0 else "")
            + ")."
        )
        if overdue > 0:
            bottlenecks = f"Hiện còn {overdue} nhiệm vụ quá hạn cần rà soát và sắp xếp lại."
        elif adherence is not None:
            bottlenecks = f"Tỷ lệ tuân thủ kế hoạch tuần đạt {adherence}%."
        else:
            bottlenecks = "Cần theo dõi thêm tiến độ hoàn thành các nhiệm vụ tiếp theo."

        actions = (
            "Ưu tiên xử lý các nhiệm vụ tồn đọng và thực hiện 1 phiên Prove Mode cho khái niệm có mức độ thành thạo thấp nhất."
            if overdue > 0
            else "Duy trì nhịp học hiện tại và thực hiện 1 phiên Prove Mode để củng cố kiến thức trọng tâm."
        )
        return strengths, bottlenecks, actions

    async def execute(
        self, user_id: UUID, request: GenerateWeeklyReviewRequestDTO
    ) -> WeeklyReviewResponseDTO:
        if request.period_end < request.period_start:
            raise ValueError("period_end must not precede period_start")
        if not await self._ownership.roadmap_belongs_to(request.roadmap_id, user_id):
            raise EvaluationResourceNotFoundError

        get_for_period = getattr(self._repository, "get_weekly_review_for_period", None)
        if callable(get_for_period):
            existing_review = await get_for_period(
                request.roadmap_id,
                request.period_start,
                request.period_end,
            )
            if existing_review is not None:
                await _close_read_transaction(self._uow)
                return _weekly_dto(existing_review)

        # Phase 1: Read-only deterministic metrics via Bounded Context Query Ports.
        exec_metrics = WeeklyExecutionMetricsDTO()
        if self._execution_metrics_port is not None:
            exec_metrics = await self._execution_metrics_port.get_roadmap_period_metrics(
                user_id=user_id,
                roadmap_id=request.roadmap_id,
                period_start=request.period_start,
                period_end=request.period_end,
            )

        masteries: list[Any] = []
        if self._learner_memory_port is not None:
            masteries = await self._learner_memory_port.list_concept_masteries(user_id)

        proof_metrics: dict[str, Any] = {}
        get_proof_metrics = getattr(self._repository, "get_user_proof_metrics", None)
        if callable(get_proof_metrics):
            proof_metrics = await get_proof_metrics(user_id)

        period_days = (request.period_end - request.period_start).days + 1
        quantitative_summary, has_sufficient_data = self._build_quantitative_summary(
            period_days=period_days,
            exec_metrics=exec_metrics,
            masteries=masteries,
            proof_metrics=proof_metrics,
        )

        # Close read transaction / session strictly BEFORE external LLM call.
        await _close_read_transaction(self._uow)

        default_strengths, default_bottlenecks, default_actions = (
            self._build_deterministic_fallback(
                quantitative_summary,
                has_sufficient_data=has_sufficient_data,
            )
        )
        final_strengths = default_strengths
        final_bottlenecks = default_bottlenecks
        final_actions = default_actions
        model_used = (
            "deterministic-insufficient-data"
            if not has_sufficient_data
            else "deterministic-fallback"
        )
        fallback_reason_code: str | None = (
            None if has_sufficient_data else "INSUFFICIENT_QUANTITATIVE_DATA"
        )

        allowed_numbers = _extract_allowed_numbers(quantitative_summary)
        raw_faithfulness = QuantitativeFaithfulnessValidator.compute_raw_faithfulness(
            (final_strengths, final_bottlenecks, final_actions),
            allowed_numbers,
        )
        prompt_tokens = 0
        completion_tokens = 0
        thinking_tokens = 0
        llm_attempts = 0

        weekly_tpl = build_evaluation_prompt_registry().latest(
            WEEKLY_REVIEW_ADVISOR_PROMPT.prompt_id
        )
        weekly_audit = build_prompt_audit_metadata(weekly_tpl)

        # Phase 2: External LLM call (no DB session or transaction held open).
        if has_sufficient_data and self._llm_provider is not None:
            try:
                manager = AIExecutionManager(
                    provider=self._llm_provider,
                    quota=self._quota_port,
                    manage_quota=self._quota_port is not None,
                    max_retries=1,
                    timeout_seconds=float(get_settings().ai_weekly_review_timeout_seconds),
                    workflow_repo=None,
                )
                exec_res = await manager.execute(
                    user_id=user_id,
                    operation_type="WEEKLY_REVIEW_SRL",
                    system_prompt=weekly_tpl.system_template,
                    user_prompt=build_weekly_review_prompt(
                        quantitative_summary=quantitative_summary,
                        reflection=request.reflection,
                    ),
                    response_schema=WeeklyReviewLLMOutput,
                    thinking_level=WEEKLY_REVIEW_ADVISOR_PROMPT.thinking_level,
                    workflow_type=WorkflowType.WEEKLY_REVIEW,
                    step_name="WEEKLY_REVIEW_SRL",
                    roadmap_id=request.roadmap_id,
                    prompt_template=weekly_tpl,
                )
                prompt_tokens = int(exec_res.prompt_tokens or 0)
                completion_tokens = int(exec_res.completion_tokens or 0)
                thinking_tokens = int(exec_res.thinking_tokens or 0)
                llm_attempts = int(exec_res.attempts or 1)
                raw_review = (
                    exec_res.value.model_dump()
                    if isinstance(exec_res.value, BaseModel)
                    else exec_res.value
                )
                if isinstance(raw_review, dict):
                    s_fb = str(raw_review.get("strengths_feedback") or "").strip()
                    b_fb = str(raw_review.get("bottlenecks_feedback") or "").strip()
                    a_rec = str(raw_review.get("action_recommendations") or "").strip()
                    if s_fb and b_fb and a_rec:
                        raw_faithfulness = (
                            QuantitativeFaithfulnessValidator.compute_raw_faithfulness(
                                (s_fb, b_fb, a_rec),
                                allowed_numbers,
                            )
                        )
                        safe_strengths, _ = QuantitativeFaithfulnessValidator.validate_or_sanitize(
                            s_fb, allowed_numbers, default_strengths
                        )
                        safe_bottlenecks, _ = (
                            QuantitativeFaithfulnessValidator.validate_or_sanitize(
                                b_fb, allowed_numbers, default_bottlenecks
                            )
                        )
                        safe_actions, _ = QuantitativeFaithfulnessValidator.validate_or_sanitize(
                            a_rec, allowed_numbers, default_actions
                        )
                        final_strengths = safe_strengths
                        final_bottlenecks = safe_bottlenecks
                        final_actions = safe_actions
                        model_used = str(exec_res.model_id or "gemini-3.8-flash")
                    else:
                        fallback_reason_code = "WEEKLY_REVIEW_INVALID_PAYLOAD"
                else:
                    fallback_reason_code = "WEEKLY_REVIEW_INVALID_PAYLOAD"
            except (
                TimeoutError,
                ValidationError,
                json.JSONDecodeError,
                PermissionError,
                ValueError,
                RuntimeError,
                OSError,
            ) as exc:
                fallback_reason_code = _classify_ai_failure_reason(exc, "WEEKLY_REVIEW")
                logger.warning(
                    "weekly_review_llm_fallback",
                    roadmap_id=str(request.roadmap_id),
                    reason_code=fallback_reason_code,
                    error_type=type(exc).__name__,
                )
        elif has_sufficient_data and self._llm_provider is None:
            fallback_reason_code = "WEEKLY_REVIEW_NO_PROVIDER"

        # Phase 3: Open a fresh AsyncUnitOfWork exclusively for persisting the review.
        scope_cm: AbstractAsyncContextManager[WeeklyReviewWriteScope] = (
            self._write_scope_factory()
            if self._write_scope_factory is not None
            else nullcontext(
                WeeklyReviewWriteScope(
                    uow=self._uow,
                    repository=self._repository,
                    learner_memory_port=self._learner_memory_port,
                    workflow_repo=self._workflow_repo,
                )
            )
        )
        async with scope_cm as write_scope:
            uow_cm: AbstractAsyncContextManager[Any] = (
                write_scope.uow
                if hasattr(write_scope.uow, "__aenter__") and hasattr(write_scope.uow, "__aexit__")
                else nullcontext(write_scope.uow)
            )
            try:
                async with uow_cm:
                    review = await write_scope.repository.create_weekly_review(
                        roadmap_id=request.roadmap_id,
                        user_id=user_id,
                        period_start=request.period_start,
                        period_end=request.period_end,
                        reflection=request.reflection,
                    )
                    review.quantitative_summary = dict(quantitative_summary)
                    review.strengths_feedback = final_strengths
                    review.bottlenecks_feedback = final_bottlenecks
                    review.action_recommendations = final_actions
                    await write_scope.repository.save_weekly_review(review, model_used=model_used)

                    if write_scope.learner_memory_port is not None:
                        await write_scope.learner_memory_port.upsert_memory_and_mastery_feedback(
                            user_id,
                            memories=[
                                {
                                    "memory_key": (
                                        f"weekly_review:{request.roadmap_id}:{request.period_end.isoformat()}"
                                    ),
                                    "category": "BEHAVIOR",
                                    "epistemic_level": "OBSERVED",
                                    "confidence": 0.85,
                                    "value": {
                                        "summary": review.strengths_feedback,
                                        "bottleneck": review.bottlenecks_feedback,
                                        "source_workflow": "WEEKLY_REVIEW",
                                        "quantitative_summary": dict(review.quantitative_summary),
                                        "model_used": model_used,
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
                        write_scope.workflow_repo,
                        user_id=user_id,
                        workflow_type=WorkflowType.WEEKLY_REVIEW,
                        roadmap_id=request.roadmap_id,
                        step_name="WEEKLY_REVIEW_SRL",
                        input_summary={
                            "roadmap_id": str(request.roadmap_id),
                            "period_start": request.period_start.isoformat(),
                            "period_end": request.period_end.isoformat(),
                            "has_sufficient_data": has_sufficient_data,
                            **weekly_audit,
                        },
                        output_payload={
                            "review_id": str(review.id),
                            "quantitative_faithfulness": raw_faithfulness,
                            "model_used": model_used,
                            "prompt_tokens": prompt_tokens,
                            "output_tokens": completion_tokens,
                            "completion_tokens": completion_tokens,
                            "thinking_tokens": thinking_tokens,
                            "attempts": llm_attempts,
                            "fallback_reason_code": fallback_reason_code,
                        },
                        step_status=(
                            WorkflowStepStatus.COMPLETED
                            if fallback_reason_code in (None, "INSUFFICIENT_QUANTITATIVE_DATA")
                            else WorkflowStepStatus.FAILED
                        ),
                        error_detail=fallback_reason_code,
                    )
                    await write_scope.uow.commit()
            except DuplicateWeeklyReviewConflictError as dup_exc:
                if dup_exc.existing_review is not None:
                    return _weekly_dto(dup_exc.existing_review)
                raise
        return _weekly_dto(review)


class GetLatestMilestoneProofUseCase:
    def __init__(
        self,
        repository: EvaluationIntelligenceRepositoryPort,
        ownership: MilestoneOwnershipQueryPort,
    ) -> None:
        self._repository = repository
        self._ownership = ownership

    async def execute(
        self, user_id: UUID, milestone_id: UUID
    ) -> LatestMilestoneProofResponseDTO | None:
        milestone = await self._ownership.get_milestone(milestone_id)
        if milestone is None or milestone.user_id != user_id:
            raise EvaluationResourceNotFoundError
        proof = await self._repository.get_latest_milestone_proof(milestone_id, user_id)
        if proof is None:
            return None
        is_verified = proof.submitted_at is not None and proof.score is not None
        calibration_error: float | None = None
        if is_verified and proof.confidence is not None and proof.score is not None:
            calibration_error = round(float(proof.confidence) - (float(proof.score) / 100.0), 4)
        return LatestMilestoneProofResponseDTO(
            id=proof.id,
            milestone_id=proof.milestone_id,
            status=proof.status,
            score=proof.score,
            confidence=proof.confidence,
            corrective_action=proof.corrective_action,
            is_verified=is_verified,
            calibration_error=calibration_error,
            questions=list(proof.questions),
            answer_evidence=[],
            created_at=proof.created_at,
            updated_at=proof.submitted_at or proof.created_at,
        )


class GetLatestWeeklyReviewUseCase:
    def __init__(self, repository: EvaluationIntelligenceRepositoryPort) -> None:
        self._repository = repository

    async def execute(self, user_id: UUID) -> WeeklyReviewResponseDTO:
        review = await self._repository.latest_weekly_review(user_id)
        if review is None:
            raise EvaluationResourceNotFoundError
        return _weekly_dto(review)
