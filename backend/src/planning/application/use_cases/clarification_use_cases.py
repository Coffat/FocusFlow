from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

from src.account.public_api import (
    AvailabilityQueryPort,
    LearnerMemoryQueryPort,
    QuotaExceededError,
    QuotaFacadePort,
)
from src.planning.application.dtos.planning_dtos import (
    ClarificationAnswerItem,
    ClarificationContextPayload,
    ClarificationFollowupLLMOutput,
    ClarificationOption,
    ClarificationQuestion,
    ClarificationQuestionLLMOutput,
    ClarificationQuestionsLLMOutput,
    ClarificationQuestionsResponse,
    ClarificationTurnResultDTO,
    normalize_diagnostic_dimension,
    parse_clarification_context,
)
from src.planning.application.ports.knowledge_source_repository_port import (
    KnowledgeSourceRepositoryPort,
)
from src.planning.application.ports.planning_repository_ports import GoalRepositoryPort
from src.planning.application.services.clarification_gap_analysis import (
    ClarificationSessionStatus,
    FactProvenance,
    GapStatus,
    GoalFactProvenance,
    InformationGap,
    InformationGapAnalyzer,
)
from src.planning.application.services.harness_support import (
    compact_context_snapshot,
    load_planning_harness_context_inputs,
)
from src.planning.application.services.roadmap_context_builder import (
    RoadmapContextBuilder,
)
from src.planning.application.services.roadmap_skills import (
    GOAL_CLARIFIER_FOLLOWUP_PROMPT,
    GOAL_CLARIFIER_SKILL,
    build_goal_clarifier_followup_prompt,
    build_goal_clarifier_prompt,
    build_planning_prompt_registry,
)
from src.planning.domain.exceptions.planning_exceptions import (
    AIExecutionError,
    GoalNotFoundError,
    InvalidClarificationSessionError,
)
from src.planning.domain.models.goal import Goal
from src.shared_kernel.application.embedding_port import EmbeddingProviderPort
from src.shared_kernel.application.harness.execution_manager import (
    AIExecutionManager,
    default_ai_retry_predicate,
)
from src.shared_kernel.application.harness.models import (
    WorkflowRun,
    WorkflowStatus,
    WorkflowStepExecution,
    WorkflowStepStatus,
    WorkflowType,
)
from src.shared_kernel.application.harness.workflow_port import WorkflowRepositoryPort
from src.shared_kernel.application.llm_port import (
    AIErrorCategory,
    LLMProviderPort,
    classify_ai_error,
)
from src.shared_kernel.application.uow import AsyncUnitOfWork
from src.shared_kernel.config import get_settings
from src.shared_kernel.domain.base import generate_uuid7

logger = logging.getLogger(__name__)

_FALLBACK_DIAGNOSTIC_QUESTIONS: tuple[dict[str, Any], ...] = (
    {
        "id": "q1",
        "question_id": "q1",
        "question": "Bạn đã từng làm việc với những ngôn ngữ hoặc công cụ liên quan nào trước đây?",
        "text": "Bạn đã từng làm việc với những ngôn ngữ hoặc công cụ liên quan nào trước đây?",
        "placeholder": "Chọn mức độ tiếp xúc trước đây của bạn...",
        "question_type": "single_choice",
        "options": [
            "Chưa từng tiếp xúc, bắt đầu hoàn toàn từ con số 0",
            "Đã tự học cú pháp cơ bản qua tài liệu hoặc video",
            "Đã từng làm bài tập nhỏ hoặc mini-project",
            "Đã có kinh nghiệm thực tế / đi làm với công nghệ tương tự",
            "Khác / Mục tiêu tự định nghĩa",
        ],
        "question_purpose": "Xác định điểm xuất phát thực tế để tránh lặp lại kiến thức đã vững.",
        "expected_answer_format": "Chọn 1 phương án phù hợp nhất.",
        "diagnostic_dimension": "PRIOR_KNOWLEDGE",
    },
    {
        "id": "q2",
        "question_id": "q2",
        "question": "Sản phẩm đầu ra hoặc kết quả cụ thể bạn muốn đạt được sau lộ trình này là gì?",
        "text": "Sản phẩm đầu ra hoặc kết quả cụ thể bạn muốn đạt được sau lộ trình này là gì?",
        "placeholder": "VD: Tự xây dựng được REST API hoàn chỉnh, vượt qua phỏng vấn...",
        "question_type": "text",
        "options": [],
        "question_purpose": "Định hướng bài tập thực hành và tiêu chí hoàn thành cột mốc.",
        "expected_answer_format": "Nêu mục tiêu đầu ra cụ thể (dự án, kỳ thi hoặc vị trí công việc).",
        "diagnostic_dimension": "TARGET_OUTCOME",
    },
    {
        "id": "q3",
        "question_id": "q3",
        "question": "Bạn ưu tiên phong cách học qua dự án thực hành ngay hay nắm chắc lý thuyết nền tảng trước?",
        "text": "Bạn ưu tiên phong cách học qua dự án thực hành ngay hay nắm chắc lý thuyết nền tảng trước?",
        "placeholder": "Chọn phong cách học tập ưa thích...",
        "question_type": "single_choice",
        "options": [
            "70% thực hành làm dự án nhỏ, 30% lý thuyết cốt lõi",
            "Cân bằng đồng đều: 50% lý thuyết - 50% thực hành kiểm chứng",
            "Nắm chắc lý thuyết chuyên sâu và nguyên lý trước khi làm bài tập",
            "Khác / Tùy chỉnh theo tuần",
        ],
        "question_purpose": "Cân bằng tỷ lệ nhiệm vụ THEORY, PRACTICE và REVIEW khi phân rã lịch.",
        "expected_answer_format": "Chọn 1 phương án phù hợp nhất.",
        "diagnostic_dimension": "LEARNING_PREFERENCE",
    },
    {
        "id": "q4",
        "question_id": "q4",
        "question": "Bạn muốn đi sâu đến mức độ nào về mặt kiến trúc, kiểm thử và triển khai thực tế?",
        "text": "Bạn muốn đi sâu đến mức độ nào về mặt kiến trúc, kiểm thử và triển khai thực tế?",
        "placeholder": "Chọn mức độ đào sâu kỹ thuật...",
        "question_type": "single_choice",
        "options": [
            "Mức cơ bản: Hiểu cú pháp, chạy được ứng dụng mẫu",
            "Mức chuẩn production: Unit test, clean code, Docker hóa",
            "Mức chuyên sâu: Tối ưu hiệu năng, kiến trúc mở rộng và bảo mật",
            "Khác / Mục tiêu tự định nghĩa",
        ],
        "question_purpose": "Xác định độ sâu kỹ thuật cho các cột mốc giai đoạn cuối.",
        "expected_answer_format": "Chọn 1 phương án phù hợp nhất.",
        "diagnostic_dimension": "DESIRED_DEPTH",
    },
    {
        "id": "q5",
        "question_id": "q5",
        "question": "Những mảng nội dung hoặc kỹ năng cụ thể nào bạn muốn tập trung rèn luyện nhiều nhất?",
        "text": "Những mảng nội dung hoặc kỹ năng cụ thể nào bạn muốn tập trung rèn luyện nhiều nhất?",
        "placeholder": "Chọn các mảng trọng tâm mong muốn...",
        "question_type": "multiple_choice",
        "options": [
            "Kiến trúc hệ thống & tư duy thiết kế giải pháp",
            "Thực hành viết code bài tập & dự án thực tế",
            "Luyện đề thi chứng chỉ & kỹ thuật phỏng vấn",
            "Tối ưu hiệu năng, bảo mật & CI/CD",
            "Khác / Mục tiêu tự định nghĩa",
        ],
        "question_purpose": "Xác định các trọng tâm chuyên môn để ưu tiên số lượng bài tập và thời lượng.",
        "expected_answer_format": "Có thể chọn nhiều phương án phù hợp.",
        "diagnostic_dimension": "PRACTICAL_EXPERIENCE",
    },
)

_DIMENSION_DEFAULT_OPTIONS: dict[str, list[str]] = {
    "PRIOR_KNOWLEDGE": [
        "Mới bắt đầu hoàn toàn, chưa có kinh nghiệm",
        "Đã tự học cú pháp hoặc khái niệm cơ bản",
        "Đã làm bài tập nhỏ hoặc mini-project",
        "Đã có kinh nghiệm thực tế với chủ đề tương đương",
    ],
    "KNOWLEDGE_BASELINE": [
        "Mới bắt đầu hoàn toàn, chưa có kinh nghiệm",
        "Đã tự học cú pháp cơ bản qua sách/video",
        "Đã từng làm bài tập nhỏ hoặc mini-project",
        "Đã có kinh nghiệm thực tế với công nghệ tương đương",
    ],
    "PRIOR_EXPOSURE": [
        "Chưa từng tiếp xúc, bắt đầu hoàn toàn từ con số 0",
        "Đã tự học cú pháp cơ bản qua tài liệu hoặc video",
        "Đã từng làm bài tập nhỏ hoặc mini-project",
        "Đã có kinh nghiệm thực tế / đi làm với công nghệ tương tự",
    ],
    "PRACTICAL_EXPERIENCE": [
        "Chỉ đọc lý thuyết, chưa viết code thực tế",
        "Viết code theo tutorial hướng dẫn từng bước",
        "Đã tự code bài tập và giải quyết lỗi độc lập",
        "Đã xây dựng sản phẩm hoàn chỉnh độc lập",
    ],
    "TECH_STACK_DEPTH": [
        "Mức cơ bản: Hiểu cú pháp, chạy được ứng dụng mẫu",
        "Mức chuẩn production: Unit test, clean code, Docker hóa",
        "Mức chuyên sâu: Tối ưu hiệu năng, kiến trúc mở rộng và bảo mật",
    ],
    "DESIRED_DEPTH": [
        "Mức cơ bản: Hiểu khái niệm và làm được bài mẫu",
        "Mức ứng dụng: Tự hoàn thành dự án hoặc bài thi mục tiêu",
        "Mức chuyên sâu: Tối ưu, giải thích và xử lý tình huống phức tạp",
    ],
    "LEARNING_STYLE": [
        "70% thực hành làm dự án nhỏ, 30% lý thuyết cốt lõi",
        "Cân bằng đồng đều: 50% lý thuyết - 50% thực hành kiểm chứng",
        "Nắm chắc lý thuyết chuyên sâu và nguyên lý trước khi làm bài tập",
    ],
    "LEARNING_PREFERENCE": [
        "Ưu tiên thực hành và dự án nhỏ",
        "Cân bằng lý thuyết với thực hành kiểm chứng",
        "Nắm chắc nguyên lý trước khi làm bài tập",
    ],
    "LEARNING_CONSTRAINTS": [
        "Chỉ học được vào buổi tối các ngày trong tuần (1-2h/ngày)",
        "Tập trung học dồn vào thứ Bảy và Chủ Nhật (3-4h/ngày)",
        "Linh hoạt sắp xếp theo tiến độ công việc hàng ngày",
    ],
    "TIME_COMMITMENT": [
        "Dưới 5 giờ/tuần (mỗi ngày 30-45 phút)",
        "5 - 10 giờ/tuần (mỗi ngày 1 - 1.5 giờ)",
        "10 - 20 giờ/tuần (cường độ cao)",
        "Linh hoạt dồn vào cuối tuần",
    ],
}

_DIMENSION_ALIASES: dict[str, str] = {
    "KNOWLEDGE_BASELINE": "PRIOR_KNOWLEDGE",
    "PRIOR_EXPOSURE": "PRIOR_KNOWLEDGE",
    "TECH_STACK_DEPTH": "DESIRED_DEPTH",
    "LEARNING_STYLE": "LEARNING_PREFERENCE",
    "LEARNING_CONSTRAINTS": "TIME_COMMITMENT",
    "TIMELINE_URGENCY": "TIMELINE",
}

_DEFAULT_SINGLE_CHOICE_OPTIONS: list[str] = [
    "Mới bắt đầu / Cần hướng dẫn chi tiết từ căn bản",
    "Đã có nền tảng / Cần bài tập thực hành nâng cao",
    "Muốn tập trung trọng tâm vào dự án thực tế",
]
_OTHER_OPTION_LABEL = "Khác / Mục tiêu tự định nghĩa"


def normalize_choice_options_with_other_last(
    raw_options: list[str],
    dimension: str,
) -> list[str]:
    """Take up to 4 unique domain options and always append 'Khác / Mục tiêu tự định nghĩa' at the end (3..5 total)."""
    domain_options: list[str] = []
    for opt in raw_options:
        cleaned = str(opt or "").strip()
        if not cleaned:
            continue
        if cleaned.lower().startswith("khác"):
            continue
        if cleaned not in domain_options:
            domain_options.append(cleaned)
        if len(domain_options) >= 4:
            break

    if len(domain_options) < 2:
        fallback_pool = _DIMENSION_DEFAULT_OPTIONS.get(dimension, _DEFAULT_SINGLE_CHOICE_OPTIONS)
        for fallback in fallback_pool:
            if fallback not in domain_options and not fallback.lower().startswith("khác"):
                domain_options.append(fallback)
            if len(domain_options) >= 3:
                break

    domain_options = domain_options[:4]
    return [*domain_options, _OTHER_OPTION_LABEL]


def _is_retryable_clarification_error(exc: Exception) -> bool:
    """Retry only transient provider/timeout failures (never schema mismatches)."""
    return default_ai_retry_predicate(exc)


class _ClarificationSessionMixin:
    """Shared v2 session transitions used by the generate and submit use cases."""

    _goal_repo: GoalRepositoryPort
    _uow: AsyncUnitOfWork
    _workflow_repo: WorkflowRepositoryPort | None
    _quota: QuotaFacadePort | None
    _llm: LLMProviderPort | None

    async def _persist_answers(
        self,
        *,
        user_id: UUID,
        goal_id: UUID,
        answers: list[ClarificationAnswerItem],
        skipped: bool,
        skipped_question_ids: list[str],
        total_questions_count: int | None = None,
        now: datetime | None = None,
        commit: bool = True,
    ) -> Goal:
        raise NotImplementedError

    async def execute_turn(
        self,
        *,
        user_id: UUID,
        goal_id: UUID,
        session_id: UUID,
        round_number: int,
        answers: list[ClarificationAnswerItem],
        skipped_question_ids: list[str],
        total_questions_count: int | None,
        now: datetime | None = None,
    ) -> ClarificationTurnResultDTO:
        if self._workflow_repo is None:
            raise InvalidClarificationSessionError()
        effective_now = now or datetime.now(UTC)
        locking_getter = getattr(self._workflow_repo, "get_run_for_update", None)
        run = (
            await locking_getter(session_id, user_id=user_id)
            if callable(locking_getter)
            else await self._workflow_repo.get_run(session_id, user_id=user_id)
        )
        if run is None or run.goal_id != goal_id:
            raise InvalidClarificationSessionError()
        if run.status is not WorkflowStatus.PAUSED_WAITING_USER:
            raise InvalidClarificationSessionError("Phiên làm rõ đã kết thúc.")
        snapshot = dict(run.context_snapshot)
        expected_round = int(snapshot.get("round", 1))
        if round_number != expected_round:
            raise InvalidClarificationSessionError("Lượt trả lời không khớp trạng thái máy chủ.")

        questions = [
            ClarificationQuestion.model_validate(item) for item in snapshot.get("questions", [])
        ]
        by_id = {question.question_id: question for question in questions}
        if any(question_id not in by_id for question_id in skipped_question_ids):
            raise InvalidClarificationSessionError(
                "Câu hỏi bỏ qua không thuộc phiên làm rõ hiện tại."
            )
        submitted_question_ids = [answer.question_id for answer in answers]
        if len(submitted_question_ids) != len(set(submitted_question_ids)):
            raise InvalidClarificationSessionError("Không được gửi trùng câu trả lời.")
        normalized_answers: list[ClarificationAnswerItem] = []
        for answer in answers:
            question = by_id.get(answer.question_id)
            if question is None:
                raise InvalidClarificationSessionError("Câu hỏi không thuộc phiên làm rõ hiện tại.")
            options_by_id = {option.id: option.label for option in question.options}
            if any(option_id not in options_by_id for option_id in answer.selected_option_ids):
                raise InvalidClarificationSessionError("Phương án trả lời không hợp lệ.")
            selected_labels = [options_by_id[item] for item in answer.selected_option_ids]
            answer_parts = [*selected_labels]
            free_text = (answer.free_text or answer.answer or "").strip()
            if free_text:
                answer_parts.append(free_text)
            normalized = ", ".join(dict.fromkeys(answer_parts)).strip()
            if normalized:
                normalized_answers.append(
                    ClarificationAnswerItem(
                        question_id=answer.question_id,
                        question_text=question.question,
                        answer=normalized,
                        selected_option_ids=list(answer.selected_option_ids),
                        free_text=answer.free_text,
                    )
                )

        all_skipped = list(
            dict.fromkeys(
                [
                    *skipped_question_ids,
                    *(
                        question_id
                        for question_id in by_id
                        if question_id not in {a.question_id for a in normalized_answers}
                    ),
                ]
            )
        )
        updated_goal = await self._persist_answers(
            user_id=user_id,
            goal_id=goal_id,
            answers=normalized_answers,
            skipped=False,
            skipped_question_ids=all_skipped,
            total_questions_count=len(questions),
            now=effective_now,
            commit=False,
        )

        gaps = [dict(item) for item in snapshot.get("information_gaps", [])]
        answered_dimensions = {
            by_id[item.question_id].diagnostic_dimension for item in normalized_answers
        }
        for gap in gaps:
            if str(gap.get("dimension")) in answered_dimensions:
                gap["status"] = GapStatus.KNOWN.value
                gap["provenance"] = FactProvenance.USER_CONFIRMED.value

        accumulated_answers = [*snapshot.get("answers", [])]
        accumulated_answers.extend(
            {
                "question_id": answer.question_id,
                "question_text": answer.question_text or "",
                "answer": answer.answer,
                "selected_option_ids": list(answer.selected_option_ids),
                "free_text": answer.free_text,
                "round": round_number,
            }
            for answer in normalized_answers
        )
        await self._workflow_repo.add_step(
            WorkflowStepExecution(
                id=generate_uuid7(),
                workflow_run_id=session_id,
                step_name=f"CLARIFICATION_ANSWER_ROUND_{round_number}",
                step_order=round_number * 2,
                status=WorkflowStepStatus.COMPLETED,
                input_summary={
                    "answered_count": len(normalized_answers),
                    "skipped_count": len(all_skipped),
                },
                output_payload={
                    "answered_dimensions": sorted(answered_dimensions),
                },
                retry_count=0,
                started_at=effective_now,
                completed_at=effective_now,
            )
        )

        follow_up_gap = next(
            (
                gap
                for gap in sorted(gaps, key=lambda item: int(item.get("priority", 0)), reverse=True)
                if str(gap.get("status"))
                in (GapStatus.PARTIAL.value, GapStatus.CONTRADICTORY.value)
                and int(gap.get("priority", 0)) >= 80
            ),
            None,
        )
        if round_number == 1 and follow_up_gap is not None:
            follow_up_tokens: dict[str, int] = {}
            follow_up = await self._try_generate_follow_up(
                user_id=user_id,
                goal_id=goal_id,
                session_id=session_id,
                gap=follow_up_gap,
                prior_answers=accumulated_answers,
                token_accumulator=follow_up_tokens,
            )
            if follow_up is not None:
                resumed = run.resume(
                    next_step="CLARIFICATION_FOLLOW_UP",
                    context_snapshot={
                        **snapshot,
                        "round": 2,
                        "questions": [follow_up.model_dump(mode="json")],
                        "answers": accumulated_answers,
                        "information_gaps": gaps,
                    },
                ).pause(now=effective_now, waiting_step="CLARIFICATION_FOLLOW_UP")
                await self._workflow_repo.save_run(resumed)
                await self._workflow_repo.add_step(
                    WorkflowStepExecution(
                        id=generate_uuid7(),
                        workflow_run_id=session_id,
                        step_name="CLARIFICATION_FOLLOW_UP",
                        step_order=3,
                        status=WorkflowStepStatus.WAITING_USER,
                        input_summary={"dimension": str(follow_up_gap.get("dimension"))},
                        output_payload={
                            "question_id": follow_up.question_id,
                            "prompt_tokens": int(follow_up_tokens.get("prompt_tokens", 0)),
                            "output_tokens": int(follow_up_tokens.get("output_tokens", 0)),
                            "completion_tokens": int(follow_up_tokens.get("completion_tokens", 0)),
                            "thinking_tokens": int(follow_up_tokens.get("thinking_tokens", 0)),
                        },
                        retry_count=0,
                        started_at=effective_now,
                    )
                )
                await self._persist_v2_context(
                    goal=updated_goal,
                    session_id=session_id,
                    status="PARTIAL",
                    answers=accumulated_answers,
                    skipped_questions=all_skipped,
                    gaps=gaps,
                    rounds_completed=1,
                    now=effective_now,
                )
                await self._uow.commit()
                return ClarificationTurnResultDTO(
                    goal=updated_goal,
                    session_id=session_id,
                    round=2,
                    status=ClarificationSessionStatus.WAITING_FOLLOW_UP.value,
                    questions=(follow_up,),
                    information_gaps=tuple(gaps),
                    next_turn_quota_cost=1,
                )

        final_status: Literal["ANSWERED", "PARTIAL"] = (
            "PARTIAL" if all_skipped or follow_up_gap is not None else "ANSWERED"
        )
        await self._persist_v2_context(
            goal=updated_goal,
            session_id=session_id,
            status=final_status,
            answers=accumulated_answers,
            skipped_questions=all_skipped,
            gaps=gaps,
            rounds_completed=round_number,
            now=effective_now,
        )
        completed = run.resume(
            next_step="CLARIFICATION_COMPLETE",
            context_snapshot={
                **snapshot,
                "round": round_number,
                "questions": [],
                "answers": accumulated_answers,
                "information_gaps": gaps,
            },
        ).complete(now=effective_now)
        await self._workflow_repo.save_run(completed)
        await self._uow.commit()
        return ClarificationTurnResultDTO(
            goal=updated_goal,
            session_id=session_id,
            round=round_number,
            status=ClarificationSessionStatus.READY_TO_PLAN.value,
            information_gaps=tuple(gaps),
            next_turn_quota_cost=0,
        )

    async def _try_generate_follow_up(
        self,
        *,
        user_id: UUID,
        goal_id: UUID,
        session_id: UUID,
        gap: dict[str, Any],
        prior_answers: list[dict[str, Any]],
        token_accumulator: dict[str, int] | None = None,
    ) -> ClarificationQuestion | None:
        if self._quota is None or self._llm is None:
            return None
        has_quota = await self._quota.check_quota_available(user_id=user_id, min_credits=1)
        if not has_quota:
            return None
        reservation_id = await self._quota.reserve_quota(
            user_id=user_id,
            operation_type="GOAL_CLARIFICATION",
            cost=1,
        )
        reservation_finalized = False

        async def _release_once(reason: str) -> None:
            nonlocal reservation_finalized
            if reservation_finalized or self._quota is None:
                return
            reservation_finalized = True
            try:
                await self._quota.release_reservation(reservation_id, reason=reason)
            except Exception as rel_exc:
                if getattr(rel_exc, "code", None) == "QUOTA_RESERVATION_NOT_FOUND" or (
                    type(rel_exc).__name__ == "QuotaReservationNotFoundError"
                ):
                    return
                raise

        async def _commit_once(
            *,
            prompt_tokens: int,
            completion_tokens: int,
            model_name: str,
        ) -> None:
            nonlocal reservation_finalized
            if reservation_finalized or self._quota is None:
                return
            reservation_finalized = True
            await self._quota.commit_reservation(
                reservation_id,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                model_name=model_name,
            )

        async def _record_followup_fallback(
            *,
            error_category: AIErrorCategory,
            error_type: str,
        ) -> None:
            logger.warning(
                "clarification_followup_generation_failed",
                extra={
                    "goal_id": str(goal_id),
                    "session_id": str(session_id),
                    "reason_code": "FOLLOWUP_GENERATION_FAILED",
                    "error_category": error_category.value,
                    "error_type": error_type,
                },
            )
            if self._workflow_repo is not None:
                await self._workflow_repo.add_step(
                    WorkflowStepExecution(
                        id=generate_uuid7(),
                        workflow_run_id=session_id,
                        step_name="CLARIFICATION_FOLLOW_UP_FALLBACK",
                        step_order=3,
                        status=WorkflowStepStatus.FAILED,
                        input_summary={"dimension": str(gap.get("dimension", ""))},
                        output_payload={
                            "fallback_reason_code": "FOLLOWUP_GENERATION_FAILED",
                            "error_category": error_category.value,
                            "error_type": error_type,
                            "prompt_tokens": 0,
                            "output_tokens": 0,
                            "completion_tokens": 0,
                            "thinking_tokens": 0,
                        },
                        retry_count=0,
                        started_at=datetime.now(UTC),
                        completed_at=datetime.now(UTC),
                    )
                )

        followup_tpl = build_planning_prompt_registry().latest(
            GOAL_CLARIFIER_FOLLOWUP_PROMPT.prompt_id
        )
        prompt = build_goal_clarifier_followup_prompt(gap=gap, prior_answers=prior_answers)
        try:
            settings = get_settings()
            result = await AIExecutionManager(
                provider=self._llm,
                quota=self._quota,
                timeout_seconds=float(settings.ai_clarifier_followup_timeout_seconds),
                max_retries=2,
                retry_predicate=_is_retryable_clarification_error,
            ).execute(
                user_id=user_id,
                operation_type="GOAL_CLARIFICATION",
                system_prompt=followup_tpl.system_template,
                user_prompt=prompt,
                response_schema=ClarificationFollowupLLMOutput,
                model_name=getattr(self._llm, "model_identifier", "gemini-3.8-flash"),
                thinking_level=GOAL_CLARIFIER_FOLLOWUP_PROMPT.thinking_level,
                existing_reservation_id=reservation_id,
                commit_on_success=False,
                release_on_failure=False,
                prompt_template=followup_tpl,
            )
        except asyncio.CancelledError:
            try:
                await asyncio.shield(_release_once("CANCELLED"))
            except Exception as release_exc:
                logger.warning(
                    "clarification_followup_cancel_release_failed",
                    extra={
                        "goal_id": str(goal_id),
                        "session_id": str(session_id),
                        "error_type": type(release_exc).__name__,
                    },
                )
            raise
        except Exception as exc:
            category = classify_ai_error(exc)
            await _release_once(type(exc).__name__)
            await _record_followup_fallback(error_category=category, error_type=type(exc).__name__)
            return None

        raw_questions = (
            result.value.questions
            if isinstance(
                result.value,
                (
                    ClarificationFollowupLLMOutput,
                    ClarificationQuestionsLLMOutput,
                    ClarificationQuestionsResponse,
                ),
            )
            else []
        )
        if len(raw_questions) != 1:
            await _release_once("INVALID_FOLLOWUP_COUNT")
            await _record_followup_fallback(
                error_category=AIErrorCategory.SCHEMA_MISMATCH,
                error_type="InvalidFollowupQuestionCount",
            )
            return None

        raw = raw_questions[0]
        q_text = str(getattr(raw, "text", "") or getattr(raw, "question", "")).strip()
        if not q_text:
            await _release_once("EMPTY_FOLLOWUP_QUESTION")
            await _record_followup_fallback(
                error_category=AIErrorCategory.SCHEMA_MISMATCH,
                error_type="EmptyFollowupQuestionText",
            )
            return None

        dimension = normalize_diagnostic_dimension(str(gap.get("dimension", "PRIOR_KNOWLEDGE")))
        raw_labels = [
            opt.label if hasattr(opt, "label") else str(opt) for opt in getattr(raw, "options", [])
        ]
        if raw.question_type in ("single_choice", "multiple_choice"):
            final_labels = normalize_choice_options_with_other_last(raw_labels, dimension)
            options = [
                ClarificationOption(
                    id=f"{session_id}-r2-q1-o{idx + 1}",
                    label=label,
                )
                for idx, label in enumerate(final_labels)
            ]
        else:
            options = []
        question = ClarificationQuestion(
            id=f"{session_id}-r2-q1",
            question_id=f"{session_id}-r2-q1",
            question=q_text,
            text=q_text,
            question_type=raw.question_type,
            options=options,
            question_purpose=str(getattr(raw, "question_purpose", "") or ""),
            expected_answer_format=str(getattr(raw, "expected_answer_format", "") or ""),
            diagnostic_dimension=dimension,
        )
        if token_accumulator is not None:
            billable_c = max(int(result.completion_tokens or 0), int(result.thinking_tokens or 0))
            token_accumulator["prompt_tokens"] = int(result.prompt_tokens or 0)
            token_accumulator["output_tokens"] = billable_c
            token_accumulator["completion_tokens"] = billable_c
            token_accumulator["thinking_tokens"] = int(result.thinking_tokens or 0)
        await _commit_once(
            prompt_tokens=result.prompt_tokens,
            completion_tokens=max(
                int(result.completion_tokens or 0), int(result.thinking_tokens or 0)
            ),
            model_name=result.model_id
            or getattr(self._llm, "model_identifier", "gemini-3.8-flash-low"),
        )
        return question

    async def skip_session(
        self,
        *,
        user_id: UUID,
        goal_id: UUID,
        session_id: UUID,
        skipped_question_ids: list[str],
        now: datetime | None = None,
    ) -> ClarificationTurnResultDTO:
        if self._workflow_repo is None:
            raise InvalidClarificationSessionError()
        effective_now = now or datetime.now(UTC)
        run = await self._workflow_repo.get_run(session_id, user_id=user_id)
        if run is None or run.goal_id != goal_id:
            raise InvalidClarificationSessionError()
        goal = await self._persist_answers(
            user_id=user_id,
            goal_id=goal_id,
            answers=[],
            skipped=True,
            skipped_question_ids=skipped_question_ids,
            now=effective_now,
            commit=False,
        )
        snapshot = dict(run.context_snapshot)
        gaps = [dict(item) for item in snapshot.get("information_gaps", [])]
        await self._persist_v2_context(
            goal=goal,
            session_id=session_id,
            status="SKIPPED",
            answers=list(snapshot.get("answers", [])),
            skipped_questions=skipped_question_ids,
            gaps=gaps,
            rounds_completed=max(0, int(snapshot.get("round", 1)) - 1),
            now=effective_now,
        )
        if run.status is WorkflowStatus.PAUSED_WAITING_USER:
            completed = run.resume(
                next_step="CLARIFICATION_SKIPPED",
                context_snapshot={**snapshot, "questions": []},
            ).complete(now=effective_now)
            await self._workflow_repo.save_run(completed)
            await self._workflow_repo.add_step(
                WorkflowStepExecution(
                    id=generate_uuid7(),
                    workflow_run_id=session_id,
                    step_name="CLARIFICATION_SKIPPED",
                    step_order=max(2, int(snapshot.get("round", 1)) * 2),
                    status=WorkflowStepStatus.COMPLETED,
                    input_summary={"skipped_question_count": len(skipped_question_ids)},
                    output_payload={"status": "SKIPPED"},
                    retry_count=0,
                    started_at=effective_now,
                    completed_at=effective_now,
                )
            )
        await self._uow.commit()
        return ClarificationTurnResultDTO(
            goal=goal,
            session_id=session_id,
            round=int(snapshot.get("round", 1)),
            status=ClarificationSessionStatus.SKIPPED.value,
            information_gaps=tuple(gaps),
        )

    async def _persist_v2_context(
        self,
        *,
        goal: Goal,
        session_id: UUID,
        status: Literal["NOT_REQUIRED", "ANSWERED", "PARTIAL", "SKIPPED"],
        answers: list[dict[str, Any]],
        skipped_questions: list[str],
        gaps: list[dict[str, Any]],
        rounds_completed: int,
        now: datetime,
    ) -> None:
        previous = parse_clarification_context(goal.clarification_context)
        contradictions = [
            gap for gap in gaps if str(gap.get("status")) == GapStatus.CONTRADICTORY.value
        ]
        assumptions = [
            f"Chưa xác nhận {gap.get('dimension')}."
            for gap in gaps
            if str(gap.get("status"))
            in (
                GapStatus.ASSUMED.value,
                GapStatus.UNKNOWN.value,
                GapStatus.PARTIAL.value,
                GapStatus.CONTRADICTORY.value,
            )
        ]
        payload = ClarificationContextPayload(
            session_id=str(session_id),
            status=status,
            questions_version="v2.0",
            answers=answers,
            skipped_questions=skipped_questions,
            unresolved_assumptions=assumptions,
            facts=[gap for gap in gaps if str(gap.get("status")) == GapStatus.KNOWN.value],
            information_gaps=gaps,
            contradictions=contradictions,
            input_provenance=previous.input_provenance,
            weekly_commitment_hours=previous.weekly_commitment_hours,
            rounds_completed=rounds_completed,
            updated_at=now.isoformat(),
        )
        goal.update_clarification(payload.to_json_str(), now=now)
        await self._goal_repo.save(goal)


class GenerateClarificationQuestionsUseCase:
    """Start or resume a provenance-aware clarification session (`UC-07`)."""

    def __init__(
        self,
        goal_repo: GoalRepositoryPort,
        quota_facade: QuotaFacadePort,
        llm_provider: LLMProviderPort,
        uow: AsyncUnitOfWork | None = None,
        learner_memory_port: LearnerMemoryQueryPort | None = None,
        knowledge_source_repo: KnowledgeSourceRepositoryPort | None = None,
        embedding_provider: EmbeddingProviderPort | None = None,
        workflow_repo: WorkflowRepositoryPort | None = None,
        availability_query_port: AvailabilityQueryPort | None = None,
        v2_enabled: bool = True,
    ) -> None:
        self._goal_repo = goal_repo
        self._quota = quota_facade
        self._llm = llm_provider
        self._uow = uow
        self._learner_memory_port = learner_memory_port
        self._knowledge_source_repo = knowledge_source_repo
        self._embedding_provider = embedding_provider
        self._workflow_repo = workflow_repo
        self._availability_port = availability_query_port
        self._gap_analyzer = InformationGapAnalyzer()
        self._v2_enabled = v2_enabled

    async def execute(
        self,
        user_id: UUID,
        goal_id: UUID,
        idempotency_key: str | None = None,
        now: datetime | None = None,
    ) -> ClarificationQuestionsResponse:
        effective_now = now or datetime.now(UTC)
        goal = await self._goal_repo.get_by_id_for_user(goal_id=goal_id, user_id=user_id)
        if goal is None:
            raise GoalNotFoundError(goal_id)

        if self._workflow_repo is not None:
            locker = getattr(self._workflow_repo, "acquire_goal_clarification_lock", None)
            if callable(locker):
                await locker(goal_id, user_id)
            if idempotency_key:
                idempotency_lookup = getattr(
                    self._workflow_repo, "get_run_by_idempotency_key", None
                )
                if callable(idempotency_lookup):
                    previous_run = await idempotency_lookup(goal_id, user_id, idempotency_key)
                    if isinstance(previous_run, WorkflowRun):
                        if previous_run.status in (
                            WorkflowStatus.RUNNING,
                            WorkflowStatus.PAUSED_WAITING_USER,
                        ):
                            return self._response_from_snapshot(previous_run)
                        return await self.get_state(user_id=user_id, goal_id=goal_id)

        active_run = await self._get_active_run(goal_id=goal_id, user_id=user_id)
        if active_run is not None:
            return self._response_from_snapshot(active_run)

        parsed_context = parse_clarification_context(
            goal.clarification_context,
            prior_knowledge_level=goal.prior_knowledge_level,
        )
        provenance = GoalFactProvenance.from_mapping(parsed_context.input_provenance)
        observed_dimensions: set[str] = set()
        if self._learner_memory_port is not None:
            memories = await self._learner_memory_port.list_active_memory_items(user_id, limit=8)
            masteries = await self._learner_memory_port.list_concept_masteries(user_id)
            for memory in memories:
                if memory.status != "CONFIRMED" or memory.confidence < 0.7:
                    continue
                memory_key = f"{memory.category}:{memory.memory_key}".lower()
                if "preference" in memory_key or "learning_style" in memory_key:
                    observed_dimensions.add("LEARNING_PREFERENCE")
                if "experience" in memory_key or "project" in memory_key:
                    observed_dimensions.add("PRACTICAL_EXPERIENCE")
                if "depth" in memory_key:
                    observed_dimensions.add("DESIRED_DEPTH")
            if any(item.evidence_count > 0 for item in masteries):
                observed_dimensions.update({"PRIOR_KNOWLEDGE", "PRACTICAL_EXPERIENCE"})
        availability_minutes: int | None = None
        if self._availability_port is not None:
            availability = await self._availability_port.get_active_availability(user_id)
            if availability is not None:
                availability_minutes = availability.weekly_capacity_minutes
        information_gaps = self._gap_analyzer.analyze(
            goal=goal,
            provenance=provenance,
            weekly_commitment_hours=parsed_context.weekly_commitment_hours,
            availability_weekly_minutes=availability_minutes,
            observed_dimensions=observed_dimensions,
        )
        question_gaps = self._gap_analyzer.select_question_gaps(information_gaps, limit=3)
        session_id = generate_uuid7()

        if not question_gaps:
            await self._persist_not_required(
                goal=goal,
                session_id=session_id,
                gaps=information_gaps,
                now=effective_now,
            )
            return ClarificationQuestionsResponse(
                session_id=session_id,
                round=1,
                status=ClarificationSessionStatus.READY_TO_PLAN.value,
                questions=[],
                questions_version="v2.0",
                information_gaps=[gap.as_dict() for gap in information_gaps],
                next_turn_quota_cost=0,
            )

        operation = f"GOAL_CLARIFICATION:{goal_id}"
        check_fn = getattr(self._quota, "check_quota_available", None)
        if callable(check_fn):
            has_quota = await self._quota.check_quota_available(user_id=user_id, min_credits=1)
            if has_quota is False:
                raise QuotaExceededError()

        reserve_slot_fn = getattr(self._quota, "reserve_slot", None)
        if callable(reserve_slot_fn):
            reservation_id: UUID = await reserve_slot_fn(
                user_id=user_id,
                operation=operation,
                now=effective_now,
            )
        else:
            reservation_id = await self._quota.reserve_quota(
                user_id=user_id,
                operation_type="GOAL_CLARIFICATION",
                cost=1,
            )

        clarifier_tpl = build_planning_prompt_registry().latest(GOAL_CLARIFIER_SKILL.skill_id)
        reservation_finalized = False

        async def _release_questions_reservation(reason: str) -> None:
            nonlocal reservation_finalized
            if reservation_finalized or self._quota is None:
                return
            reservation_finalized = True
            try:
                await self._quota.release_reservation(
                    reservation_id=reservation_id,
                    reason=reason,
                )
            except Exception as rel_exc:
                if getattr(rel_exc, "code", None) == "QUOTA_RESERVATION_NOT_FOUND" or (
                    type(rel_exc).__name__ == "QuotaReservationNotFoundError"
                ):
                    return
                raise

        try:
            context_block = RoadmapContextBuilder.build_clarification_context(goal)
            harness_inputs = await load_planning_harness_context_inputs(
                user_id=user_id,
                goal_id=goal_id,
                query_text=f"{goal.title} {goal.raw_description or ''}",
                learner_memory_port=self._learner_memory_port,
                knowledge_source_repo=self._knowledge_source_repo,
                embedding_provider=self._embedding_provider,
            )
            assembled = RoadmapContextBuilder.assemble_harness_context(
                system_instruction=clarifier_tpl.system_template,
                workflow_stage="GOAL_CLARIFICATION",
                base_context_text=context_block,
                learner_diagnostic={
                    "information_gaps": [gap.as_dict() for gap in information_gaps]
                },
                memory_items=harness_inputs.memory_items,
                concept_masteries=harness_inputs.concept_masteries,
                knowledge_chunks=harness_inputs.knowledge_chunks,
            )
            effective_context = (
                f"{context_block}\n\n{assembled.text}"
                if (
                    harness_inputs.memory_items
                    or harness_inputs.concept_masteries
                    or harness_inputs.knowledge_chunks
                )
                else context_block
            )
            user_prompt = build_goal_clarifier_prompt(
                (
                    f"{effective_context}\n\n[INFORMATION_GAPS_TO_CLARIFY]\n"
                    + "\n".join(
                        f"- {gap.dimension}: {gap.status.value}; ảnh hưởng={gap.roadmap_decision}"
                        for gap in question_gaps
                    )
                ),
                known_dimensions=[
                    gap.dimension for gap in information_gaps if gap.status is GapStatus.KNOWN
                ],
                gap_count=len(question_gaps),
            )

            try:
                settings = get_settings()
                exec_mgr = AIExecutionManager(
                    provider=self._llm,
                    quota=self._quota,
                    timeout_seconds=float(settings.ai_clarifier_timeout_seconds),
                    max_retries=2,
                    retry_predicate=_is_retryable_clarification_error,
                )
                exec_res = await exec_mgr.execute(
                    user_id=user_id,
                    operation_type="GOAL_CLARIFICATION",
                    system_prompt=clarifier_tpl.system_template,
                    user_prompt=user_prompt,
                    response_schema=ClarificationQuestionsLLMOutput,
                    model_name=getattr(self._llm, "model_identifier", "gemini-3.8-flash"),
                    thinking_level=GOAL_CLARIFIER_SKILL.thinking_level,
                    existing_reservation_id=reservation_id,
                    commit_on_success=False,
                    release_on_failure=False,
                    prompt_template=clarifier_tpl,
                )
                raw_result = exec_res.value
                p_tok = exec_res.prompt_tokens
                c_tok = max(
                    int(exec_res.completion_tokens or 0), int(exec_res.thinking_tokens or 0)
                )
                t_tok = int(exec_res.thinking_tokens or 0)
                resolved_clarifier_model = (
                    exec_res.model_id
                    or getattr(self._llm, "last_model_used", "")
                    or getattr(self._llm, "model_identifier", "gemini-3.8-flash-low")
                )
            except Exception as exc:
                logger.warning(
                    "AI execution failed during clarification questions generation for goal %s: %s",
                    goal_id,
                    exc,
                    exc_info=True,
                )
                await _release_questions_reservation(type(exc).__name__)
                raise AIExecutionError(
                    "Hệ thống AI hiện đang bận hoặc gặp sự cố kết nối. Vui lòng bấm 'Thử lại' sau giây lát."
                ) from exc

            raw_questions: list[Any] = []
            if isinstance(
                raw_result, (ClarificationQuestionsLLMOutput, ClarificationQuestionsResponse)
            ):
                raw_questions = list(raw_result.questions)
            elif isinstance(raw_result, dict) and isinstance(raw_result.get("questions"), list):
                raw_questions = raw_result["questions"]

            normalized_items: list[ClarificationQuestion] = []
            for idx, item in enumerate(raw_questions):
                item_dict: dict[str, Any] = {}
                if isinstance(item, (ClarificationQuestion, ClarificationQuestionLLMOutput)):
                    item_dict = item.model_dump()
                elif isinstance(item, dict):
                    item_dict = item
                else:
                    continue

                q_id = f"q{idx + 1}"
                q_text = str(item_dict.get("text") or item_dict.get("question") or "").strip()
                if not q_text:
                    continue

                raw_q_type = (
                    str(item_dict.get("question_type") or item_dict.get("type") or "")
                    .strip()
                    .lower()
                )
                raw_opts = item_dict.get("options")
                extracted_opts: list[str] = (
                    [
                        str(opt.get("label", "")).strip()
                        if isinstance(opt, dict)
                        else str(getattr(opt, "label", opt)).strip()
                        for opt in raw_opts
                        if (
                            str(opt.get("label", "")).strip()
                            if isinstance(opt, dict)
                            else str(getattr(opt, "label", opt)).strip()
                        )
                    ]
                    if isinstance(raw_opts, list)
                    else []
                )

                raw_dim = str(item_dict.get("diagnostic_dimension") or "PRIOR_KNOWLEDGE").strip()
                dim = normalize_diagnostic_dimension(_DIMENSION_ALIASES.get(raw_dim, raw_dim))

                if raw_q_type == "multiple_choice":
                    q_type = "multiple_choice"
                elif raw_q_type == "single_choice":
                    q_type = "single_choice"
                elif raw_q_type == "text":
                    q_type = "text"
                else:
                    q_type = "single_choice" if len(extracted_opts) >= 2 else "text"

                if q_type in ("single_choice", "multiple_choice"):
                    if not extracted_opts and ("TARGET_OUTCOME" in dim or "OUTCOME" in dim):
                        q_type = "text"
                        extracted_opts = []
                    else:
                        extracted_opts = normalize_choice_options_with_other_last(
                            extracted_opts, dim
                        )
                else:
                    extracted_opts = []

                placeholder = str(item_dict.get("placeholder") or "").strip()
                if not placeholder:
                    if q_type == "multiple_choice":
                        placeholder = "Chọn các phương án phù hợp..."
                    elif q_type == "single_choice":
                        placeholder = "Chọn phương án phù hợp nhất..."
                    else:
                        placeholder = "Nhập câu trả lời ngắn gọn của bạn..."

                purpose = str(
                    item_dict.get("question_purpose")
                    or "Làm rõ bối cảnh và nhu cầu cá nhân hóa lộ trình học tập."
                ).strip()

                expected_format = str(item_dict.get("expected_answer_format") or "").strip()
                if not expected_format:
                    if q_type == "multiple_choice":
                        expected_format = "Có thể chọn nhiều phương án phù hợp."
                    elif q_type == "single_choice":
                        expected_format = "Chọn 1 đáp án phù hợp nhất."
                    else:
                        expected_format = "Câu trả lời tự do ngắn gọn (1-2 câu)."

                q_obj = ClarificationQuestion(
                    id=q_id,
                    question_id=q_id,
                    question=q_text,
                    text=q_text,
                    placeholder=placeholder,
                    question_type=q_type,
                    options=[
                        ClarificationOption(id=f"{q_id}-o{index + 1}", label=label)
                        for index, label in enumerate(extracted_opts)
                    ],
                    question_purpose=purpose,
                    expected_answer_format=expected_format,
                    diagnostic_dimension=dim,
                )
                normalized_items.append(q_obj)

            allowed_dimensions = {gap.dimension for gap in question_gaps}
            non_redundant = [
                q for q in normalized_items if q.diagnostic_dimension in allowed_dimensions
            ]
            if len(non_redundant) >= len(question_gaps):
                selected = non_redundant[: len(question_gaps)]
            else:
                selected = list(non_redundant)
                used_questions = {q.question for q in selected}
                for fb in _FALLBACK_DIAGNOSTIC_QUESTIONS:
                    if len(selected) >= len(question_gaps):
                        break
                    if (
                        fb["diagnostic_dimension"] in allowed_dimensions
                        and fb["question"] not in used_questions
                    ):
                        selected.append(ClarificationQuestion.model_validate(fb))
                        used_questions.add(fb["question"])
                for q in normalized_items:
                    if len(selected) >= len(question_gaps):
                        break
                    if (
                        q.diagnostic_dimension in allowed_dimensions
                        and q.question not in used_questions
                    ):
                        selected.append(q)
                        used_questions.add(q.question)

            text_question_seen = False
            policy_validated: list[ClarificationQuestion] = []
            for question in selected:
                if question.question_type == "text":
                    if text_question_seen:
                        continue
                    text_question_seen = True
                policy_validated.append(question)

            reindexed: list[ClarificationQuestion] = [
                ClarificationQuestion(
                    id=f"{session_id}-r1-q{i + 1}",
                    question_id=f"{session_id}-r1-q{i + 1}",
                    question=q.question,
                    text=q.text or q.question,
                    placeholder=q.placeholder,
                    question_type=q.question_type,
                    options=[
                        ClarificationOption(
                            id=f"{session_id}-r1-q{i + 1}-o{option_index + 1}",
                            label=option.label,
                        )
                        for option_index, option in enumerate(q.options)
                    ],
                    question_purpose=q.question_purpose,
                    expected_answer_format=q.expected_answer_format,
                    diagnostic_dimension=q.diagnostic_dimension,
                )
                for i, q in enumerate(policy_validated[:3])
            ]

            # Ensure at least one choice question exists with options for fast 1-click UX
            has_choice = any(
                q.question_type in ("single_choice", "multiple_choice") and len(q.options) >= 2
                for q in reindexed
            )
            if not has_choice and reindexed:
                target_q = next(
                    (q for q in reindexed if "OUTCOME" not in q.diagnostic_dimension),
                    reindexed[0],
                )
                dim_key = target_q.diagnostic_dimension
                target_q.question_type = "single_choice"
                target_q.options = [
                    ClarificationOption(
                        id=f"{target_q.question_id}-o{option_index + 1}",
                        label=label,
                    )
                    for option_index, label in enumerate(
                        normalize_choice_options_with_other_last(
                            _DIMENSION_DEFAULT_OPTIONS.get(dim_key, _DEFAULT_SINGLE_CHOICE_OPTIONS),
                            dim_key,
                        )
                    )
                ]
                target_q.expected_answer_format = "Chọn 1 đáp án phù hợp nhất."
            ClarificationQuestionsResponse(questions=reindexed)

            await self._quota.commit_reservation(
                reservation_id=reservation_id,
                prompt_tokens=p_tok,
                completion_tokens=c_tok,
                model_name=resolved_clarifier_model,
            )
            reservation_finalized = True
            if not self._v2_enabled:
                return ClarificationQuestionsResponse(
                    questions=reindexed,
                    questions_version="v2.0",
                    status=ClarificationSessionStatus.WAITING_ANSWER.value,
                    information_gaps=[gap.as_dict() for gap in information_gaps],
                )
            snapshot = {
                **compact_context_snapshot(
                    goal_id=goal_id,
                    roadmap_id=None,
                    stage="GOAL_CLARIFICATION",
                    inputs=harness_inputs,
                    layer_tokens=assembled.layer_tokens,
                    prompt_template=clarifier_tpl,
                ),
                "schema_version": 2,
                "session_id": str(session_id),
                "round": 1,
                "idempotency_key": idempotency_key,
                "questions_version": "v2.0",
                "questions": [q.model_dump(mode="json") for q in reindexed],
                "information_gaps": [gap.as_dict() for gap in information_gaps],
                "answers": [],
                "model_name": resolved_clarifier_model,
                "prompt_tokens": p_tok,
                "output_tokens": c_tok,
                "completion_tokens": c_tok,
                "thinking_tokens": t_tok,
            }
            await self._store_waiting_session(
                session_id=session_id,
                user_id=user_id,
                goal_id=goal_id,
                snapshot=snapshot,
                now=effective_now,
            )
            if self._uow is not None:
                await self._uow.commit()
            return ClarificationQuestionsResponse(
                session_id=session_id,
                round=1,
                status=ClarificationSessionStatus.WAITING_ANSWER.value,
                questions=reindexed,
                questions_version="v2.0",
                information_gaps=[gap.as_dict() for gap in information_gaps],
                next_turn_quota_cost=1,
            )

        except asyncio.CancelledError:
            try:
                await asyncio.shield(_release_questions_reservation("CANCELLED"))
            except Exception as release_exc:
                logger.warning(
                    "clarification_questions_cancel_release_failed",
                    extra={
                        "goal_id": str(goal_id),
                        "session_id": str(session_id),
                        "error_type": type(release_exc).__name__,
                    },
                )
            raise
        except (QuotaExceededError, AIExecutionError):
            raise
        except Exception as exc:
            await _release_questions_reservation(type(exc).__name__)
            raise

    async def _get_active_run(self, *, goal_id: UUID, user_id: UUID) -> WorkflowRun | None:
        if self._workflow_repo is None:
            return None
        getter = getattr(self._workflow_repo, "get_active_run_for_goal", None)
        if not callable(getter):
            return None
        run = await getter(goal_id, user_id, WorkflowType.PLAN_CREATION)
        return run if isinstance(run, WorkflowRun) else None

    async def get_state(self, *, user_id: UUID, goal_id: UUID) -> ClarificationQuestionsResponse:
        goal = await self._goal_repo.get_by_id_for_user(goal_id=goal_id, user_id=user_id)
        if goal is None:
            raise GoalNotFoundError(goal_id)
        active_run = await self._get_active_run(goal_id=goal_id, user_id=user_id)
        if active_run is not None:
            return self._response_from_snapshot(active_run)
        parsed = parse_clarification_context(goal.clarification_context)
        return ClarificationQuestionsResponse(
            session_id=UUID(parsed.session_id) if parsed.session_id else None,
            round=max(1, parsed.rounds_completed),
            status=(
                ClarificationSessionStatus.SKIPPED.value
                if parsed.status == "SKIPPED"
                else ClarificationSessionStatus.READY_TO_PLAN.value
            ),
            questions=[],
            questions_version=parsed.questions_version,
            information_gaps=list(parsed.information_gaps),
            next_turn_quota_cost=0,
        )

    @staticmethod
    def _response_from_snapshot(run: WorkflowRun) -> ClarificationQuestionsResponse:
        snapshot = run.context_snapshot
        return ClarificationQuestionsResponse(
            session_id=run.id,
            round=int(snapshot.get("round", 1)),
            status=(
                ClarificationSessionStatus.WAITING_FOLLOW_UP.value
                if int(snapshot.get("round", 1)) == 2
                else ClarificationSessionStatus.WAITING_ANSWER.value
            ),
            questions=list(snapshot.get("questions", [])),
            questions_version=str(snapshot.get("questions_version", "v2.0")),
            information_gaps=list(snapshot.get("information_gaps", [])),
            next_turn_quota_cost=1,
        )

    async def _store_waiting_session(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
        goal_id: UUID,
        snapshot: dict[str, Any],
        now: datetime,
    ) -> None:
        if self._workflow_repo is None:
            return
        run = WorkflowRun(
            id=session_id,
            user_id=user_id,
            goal_id=goal_id,
            roadmap_id=None,
            workflow_type=WorkflowType.PLAN_CREATION,
            current_step="CLARIFICATION_ROUND_1",
            status=WorkflowStatus.RUNNING,
            context_snapshot=snapshot,
            started_at=now,
        ).pause(now=now, waiting_step="CLARIFICATION_ROUND_1")
        await self._workflow_repo.add_run(run)
        await self._workflow_repo.add_step(
            WorkflowStepExecution(
                id=generate_uuid7(),
                workflow_run_id=session_id,
                step_name="CLARIFICATION_ROUND_1",
                step_order=1,
                status=WorkflowStepStatus.WAITING_USER,
                input_summary={"question_count": len(snapshot.get("questions", []))},
                output_payload={
                    "questions_version": "v2.0",
                    "prompt_tokens": int(snapshot.get("prompt_tokens", 0)),
                    "output_tokens": int(snapshot.get("output_tokens", 0)),
                    "completion_tokens": int(snapshot.get("completion_tokens", 0)),
                    "thinking_tokens": int(snapshot.get("thinking_tokens", 0)),
                },
                retry_count=0,
                started_at=now,
            )
        )

    async def _persist_not_required(
        self,
        *,
        goal: Goal,
        session_id: UUID,
        gaps: list[InformationGap],
        now: datetime,
    ) -> None:
        previous = parse_clarification_context(goal.clarification_context)
        payload = ClarificationContextPayload(
            session_id=str(session_id),
            status="NOT_REQUIRED",
            questions_version="v2.0",
            facts=[gap.as_dict() for gap in gaps if gap.status is GapStatus.KNOWN],
            information_gaps=[gap.as_dict() for gap in gaps],
            input_provenance=previous.input_provenance,
            weekly_commitment_hours=previous.weekly_commitment_hours,
            rounds_completed=0,
            updated_at=now.isoformat(),
        )
        goal.update_clarification(payload.to_json_str(), now=now)
        await self._goal_repo.save(goal)
        if self._workflow_repo is not None:
            await self._workflow_repo.add_run(
                WorkflowRun(
                    id=session_id,
                    user_id=goal.user_id,
                    goal_id=goal.id,
                    roadmap_id=None,
                    workflow_type=WorkflowType.PLAN_CREATION,
                    current_step="CLARIFICATION_COMPLETE",
                    status=WorkflowStatus.RUNNING,
                    context_snapshot={
                        "schema_version": 2,
                        "session_id": str(session_id),
                        "round": 0,
                        "questions": [],
                        "information_gaps": [gap.as_dict() for gap in gaps],
                    },
                    started_at=now,
                ).complete(now=now)
            )
        if self._uow is not None:
            await self._uow.commit()


class SubmitClarificationAnswersUseCase(_ClarificationSessionMixin):
    """Use case to persist full, partial, or skipped clarification state into Goal (`UC-07`)."""

    def __init__(
        self,
        goal_repo: GoalRepositoryPort,
        uow: AsyncUnitOfWork,
        workflow_repo: WorkflowRepositoryPort | None = None,
        quota_facade: QuotaFacadePort | None = None,
        llm_provider: LLMProviderPort | None = None,
    ) -> None:
        self._goal_repo = goal_repo
        self._uow = uow
        self._workflow_repo = workflow_repo
        self._quota = quota_facade
        self._llm = llm_provider

    async def _persist_answers(
        self,
        *,
        user_id: UUID,
        goal_id: UUID,
        answers: list[ClarificationAnswerItem],
        skipped: bool,
        skipped_question_ids: list[str],
        total_questions_count: int | None = None,
        now: datetime | None = None,
        commit: bool = True,
    ) -> Goal:
        return await self.execute(
            user_id=user_id,
            goal_id=goal_id,
            answers=answers,
            skipped=skipped,
            skipped_question_ids=skipped_question_ids,
            total_questions_count=total_questions_count,
            now=now,
            commit=commit,
        )

    async def execute(
        self,
        user_id: UUID,
        goal_id: UUID,
        answers: list[ClarificationAnswerItem] | None = None,
        *,
        skipped: bool = False,
        skipped_question_ids: list[str] | None = None,
        total_questions_count: int | None = None,
        now: datetime | None = None,
        commit: bool = True,
    ) -> Goal:
        async with self._uow:
            goal = await self._goal_repo.get_by_id_for_user(goal_id=goal_id, user_id=user_id)
            if goal is None:
                raise GoalNotFoundError(goal_id)

            raw_answers = answers or []
            valid_answers: list[ClarificationAnswerItem] = []
            inferred_skipped_ids: list[str] = list(skipped_question_ids or [])

            for item in raw_answers:
                if item.answer and item.answer.strip():
                    valid_answers.append(item)
                elif item.question_id and item.question_id not in inferred_skipped_ids:
                    inferred_skipped_ids.append(item.question_id)

            unresolved_assumptions: list[str] = []

            status_val: Literal["ANSWERED", "PARTIAL", "SKIPPED"]
            if skipped:
                status_val = "SKIPPED"
                unresolved_assumptions.append(
                    f"Người học đã bỏ qua bước khảo sát; hệ thống giả định điểm xuất phát theo trình độ '{goal.prior_knowledge_level}'."
                )
                unresolved_assumptions.append(
                    "Giả định phân bổ cân bằng chuẩn SRL: 40% Lý thuyết (THEORY) - 45% Thực hành (PRACTICE) - 15% Ôn tập (REVIEW)."
                )
                if goal.target_date is None:
                    unresolved_assumptions.append(
                        "Chưa có hạn chót cụ thể; giả định nhịp độ học tập bền vững theo quỹ thời gian rảnh hàng tuần."
                    )
                synthesized_text = (
                    "Người học đã bỏ qua phỏng vấn làm rõ mục tiêu (SKIPPED).\n"
                    + "\n".join(f"- Giả định: {a}" for a in unresolved_assumptions)
                )
            else:
                expected_total = total_questions_count or len(raw_answers)
                is_partial = (
                    not valid_answers
                    or bool(inferred_skipped_ids)
                    or (expected_total > len(valid_answers))
                )
                status_val = "PARTIAL" if is_partial else "ANSWERED"

                lines: list[str] = []
                for idx, ans in enumerate(valid_answers, 1):
                    lines.append(
                        f"Câu hỏi {idx} ({ans.question_text}):\n- Trả lời: {ans.answer.strip()}"
                    )

                if status_val == "PARTIAL":
                    skipped_label = (
                        ", ".join(inferred_skipped_ids)
                        if inferred_skipped_ids
                        else "một số câu hỏi khảo sát"
                    )
                    unresolved_assumptions.append(
                        f"Người học chưa trả lời ({skipped_label}); hệ thống giả định cấu hình tiêu chuẩn phù hợp với trình độ '{goal.prior_knowledge_level}'."
                    )
                    lines.append(f"Ghi chú hệ thống (PARTIAL): {unresolved_assumptions[0]}")

                synthesized_text = "\n\n".join(lines)

            previous = parse_clarification_context(goal.clarification_context)
            payload = ClarificationContextPayload(
                status=status_val,
                questions_version="v2.0",
                answers=[
                    {
                        "question_id": a.question_id,
                        "question_text": a.question_text or "",
                        "answer": a.answer.strip(),
                    }
                    for a in valid_answers
                ],
                skipped_questions=inferred_skipped_ids,
                unresolved_assumptions=unresolved_assumptions,
                facts=previous.facts,
                information_gaps=previous.information_gaps,
                contradictions=previous.contradictions,
                input_provenance=previous.input_provenance,
                weekly_commitment_hours=previous.weekly_commitment_hours,
                synthesized_text=synthesized_text,
                updated_at=now.isoformat() if now is not None else "",
            )

            goal.update_clarification(
                clarification_context=payload.to_json_str(),
                now=now,
            )
            await self._goal_repo.save(goal)
            if commit:
                await self._uow.commit()
            return goal

    async def skip(
        self,
        user_id: UUID,
        goal_id: UUID,
        *,
        skipped_question_ids: list[str] | None = None,
        now: datetime | None = None,
    ) -> Goal:
        return await self.execute(
            user_id=user_id,
            goal_id=goal_id,
            answers=[],
            skipped=True,
            skipped_question_ids=skipped_question_ids,
            now=now,
        )
