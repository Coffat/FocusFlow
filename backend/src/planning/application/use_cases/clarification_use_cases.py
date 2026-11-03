from datetime import datetime
from typing import Any
from uuid import UUID

from src.account.public_api import QuotaExceededError, QuotaFacadePort
from src.planning.application.dtos.planning_dtos import (
    ClarificationAnswerItem,
    ClarificationContextPayload,
    ClarificationQuestion,
    ClarificationQuestionsResponse,
)
from src.planning.application.ports.planning_repository_ports import GoalRepositoryPort
from src.planning.application.services.roadmap_context_builder import (
    RoadmapContextBuilder,
)
from src.planning.application.services.roadmap_skills import (
    GOAL_CLARIFIER_SKILL,
    build_goal_clarifier_prompt,
)
from src.planning.domain.exceptions.planning_exceptions import GoalNotFoundError
from src.planning.domain.models.goal import Goal
from src.shared_kernel.application.llm_port import LLMProviderPort
from src.shared_kernel.application.uow import AsyncUnitOfWork

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
        ],
        "question_purpose": "Xác định điểm xuất phát thực tế để tránh lặp lại kiến thức đã vững.",
        "expected_answer_format": "Chọn 1 phương án phù hợp nhất.",
        "diagnostic_dimension": "PRIOR_EXPOSURE",
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
        ],
        "question_purpose": "Cân bằng tỷ lệ nhiệm vụ THEORY, PRACTICE và REVIEW khi phân rã lịch.",
        "expected_answer_format": "Chọn 1 phương án phù hợp nhất.",
        "diagnostic_dimension": "LEARNING_STYLE",
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
        ],
        "question_purpose": "Xác định độ sâu kỹ thuật cho các cột mốc giai đoạn cuối.",
        "expected_answer_format": "Chọn 1 phương án phù hợp nhất.",
        "diagnostic_dimension": "TECH_STACK_DEPTH",
    },
)

_DIMENSION_DEFAULT_OPTIONS: dict[str, list[str]] = {
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
    "LEARNING_STYLE": [
        "70% thực hành làm dự án nhỏ, 30% lý thuyết cốt lõi",
        "Cân bằng đồng đều: 50% lý thuyết - 50% thực hành kiểm chứng",
        "Nắm chắc lý thuyết chuyên sâu và nguyên lý trước khi làm bài tập",
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

_DEFAULT_SINGLE_CHOICE_OPTIONS: list[str] = [
    "Mới bắt đầu / Cần hướng dẫn chi tiết từ căn bản",
    "Đã có nền tảng / Cần bài tập thực hành nâng cao",
    "Muốn tập trung trọng tâm vào dự án thực tế",
]


class GenerateClarificationQuestionsUseCase:
    """Use case to generate 2-3 non-redundant clarification questions for a Goal via AI (`UC-07`)."""

    def __init__(
        self,
        goal_repo: GoalRepositoryPort,
        quota_facade: QuotaFacadePort,
        llm_provider: LLMProviderPort,
        uow: AsyncUnitOfWork | None = None,
    ) -> None:
        self._goal_repo = goal_repo
        self._quota = quota_facade
        self._llm = llm_provider
        self._uow = uow

    async def execute(
        self,
        user_id: UUID,
        goal_id: UUID,
        now: datetime | None = None,
    ) -> ClarificationQuestionsResponse:
        goal = await self._goal_repo.get_by_id_for_user(goal_id=goal_id, user_id=user_id)
        if goal is None:
            raise GoalNotFoundError(goal_id)

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
                now=now,
            )
        else:
            reservation_id = await self._quota.reserve_quota(
                user_id=user_id,
                operation_type="GOAL_CLARIFICATION",
                cost=1,
            )

        try:
            known_dims = RoadmapContextBuilder.extract_known_diagnostic_dimensions(goal)
            context_block = RoadmapContextBuilder.build_clarification_context(goal)
            user_prompt = build_goal_clarifier_prompt(
                context_block,
                goal_title=goal.title,
                raw_description=goal.raw_description or "",
                prior_knowledge_level=goal.prior_knowledge_level,
                target_date_iso=goal.target_date.isoformat() if goal.target_date else None,
                known_dimensions=known_dims,
            )

            raw_result, p_tok, c_tok = await self._llm.generate_structured(
                prompt=user_prompt,
                system_prompt=GOAL_CLARIFIER_SKILL.system_instruction,
                response_schema=ClarificationQuestionsResponse,
                user_prompt=user_prompt,
            )

            raw_questions: list[Any] = []
            if isinstance(raw_result, dict) and isinstance(raw_result.get("questions"), list):
                raw_questions = raw_result["questions"]

            normalized_items: list[ClarificationQuestion] = []
            for idx, item in enumerate(raw_questions):
                item_dict: dict[str, Any] = {}
                if isinstance(item, ClarificationQuestion):
                    item_dict = item.model_dump()
                elif isinstance(item, dict):
                    item_dict = item
                else:
                    continue

                q_id = str(item_dict.get("id") or item_dict.get("question_id") or f"q{idx + 1}")
                q_text = str(item_dict.get("question") or item_dict.get("text") or "").strip()
                if not q_text:
                    continue

                raw_q_type = str(item_dict.get("question_type") or "").strip().lower()
                raw_opts = item_dict.get("options")
                extracted_opts: list[str] = (
                    [str(opt).strip() for opt in raw_opts if str(opt).strip()]
                    if isinstance(raw_opts, list)
                    else []
                )

                dim = str(item_dict.get("diagnostic_dimension") or "GENERAL").strip()

                if raw_q_type in ("single_choice", "multiple_choice"):
                    q_type = "single_choice"
                elif raw_q_type == "text":
                    q_type = "text"
                else:
                    q_type = "single_choice" if len(extracted_opts) >= 2 else "text"

                if q_type == "single_choice":
                    if not extracted_opts:
                        fallback_opts = _DIMENSION_DEFAULT_OPTIONS.get(dim)
                        if fallback_opts:
                            extracted_opts = list(fallback_opts)
                        elif "TARGET_OUTCOME" in dim or "OUTCOME" in dim:
                            q_type = "text"
                            extracted_opts = []
                        else:
                            extracted_opts = list(_DEFAULT_SINGLE_CHOICE_OPTIONS)
                else:
                    extracted_opts = []

                placeholder = str(item_dict.get("placeholder") or "").strip()
                if not placeholder:
                    placeholder = (
                        "Chọn phương án phù hợp nhất..."
                        if q_type == "single_choice"
                        else "Nhập câu trả lời ngắn gọn của bạn..."
                    )

                purpose = str(
                    item_dict.get("question_purpose")
                    or "Làm rõ bối cảnh và nhu cầu cá nhân hóa lộ trình học tập."
                ).strip()

                expected_format = str(item_dict.get("expected_answer_format") or "").strip()
                if not expected_format:
                    expected_format = (
                        "Chọn 1 đáp án phù hợp nhất."
                        if q_type == "single_choice"
                        else "Câu trả lời tự do ngắn gọn (1-2 câu)."
                    )

                q_obj = ClarificationQuestion(
                    id=q_id,
                    question_id=q_id,
                    question=q_text,
                    text=q_text,
                    placeholder=placeholder,
                    question_type=q_type,
                    options=extracted_opts,
                    question_purpose=purpose,
                    expected_answer_format=expected_format,
                    diagnostic_dimension=dim,
                )
                normalized_items.append(q_obj)

            # Filter out questions whose diagnostic_dimension is already known if we have enough
            known_set = set(known_dims)
            non_redundant = [q for q in normalized_items if q.diagnostic_dimension not in known_set]
            if len(non_redundant) >= 2:
                selected = non_redundant[:3]
            else:
                selected = list(non_redundant)
                used_questions = {q.question for q in selected}
                for fb in _FALLBACK_DIAGNOSTIC_QUESTIONS:
                    if len(selected) >= 3:
                        break
                    if (
                        fb["diagnostic_dimension"] not in known_set
                        and fb["question"] not in used_questions
                    ):
                        selected.append(ClarificationQuestion.model_validate(fb))
                        used_questions.add(fb["question"])
                for q in normalized_items:
                    if len(selected) >= 2:
                        break
                    if q.question not in used_questions:
                        selected.append(q)
                        used_questions.add(q.question)

            reindexed: list[ClarificationQuestion] = [
                ClarificationQuestion(
                    id=f"q{i + 1}",
                    question_id=f"q{i + 1}",
                    question=q.question,
                    text=q.text or q.question,
                    placeholder=q.placeholder,
                    question_type=q.question_type,
                    options=list(q.options),
                    question_purpose=q.question_purpose,
                    expected_answer_format=q.expected_answer_format,
                    diagnostic_dimension=q.diagnostic_dimension,
                )
                for i, q in enumerate(selected[:3])
            ]

            # Ensure at least one single_choice question exists with options for fast 1-click UX
            has_single_choice = any(
                q.question_type == "single_choice" and len(q.options) >= 2 for q in reindexed
            )
            if not has_single_choice and reindexed:
                target_q = next(
                    (q for q in reindexed if "OUTCOME" not in q.diagnostic_dimension),
                    reindexed[0],
                )
                dim_key = target_q.diagnostic_dimension
                target_q.question_type = "single_choice"
                target_q.options = list(
                    _DIMENSION_DEFAULT_OPTIONS.get(dim_key, _DEFAULT_SINGLE_CHOICE_OPTIONS)
                )
                target_q.expected_answer_format = "Chọn 1 đáp án phù hợp nhất."
            validated_response = ClarificationQuestionsResponse(questions=reindexed)

            await self._quota.commit_reservation(
                reservation_id=reservation_id,
                prompt_tokens=p_tok,
                completion_tokens=c_tok,
            )
            return validated_response

        except QuotaExceededError:
            raise
        except Exception:
            await self._quota.release_reservation(
                reservation_id=reservation_id,
            )
            raise


class SubmitClarificationAnswersUseCase:
    """Use case to persist full, partial, or skipped clarification state into Goal (`UC-07`)."""

    def __init__(
        self,
        goal_repo: GoalRepositoryPort,
        uow: AsyncUnitOfWork,
    ) -> None:
        self._goal_repo = goal_repo
        self._uow = uow

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

            if skipped or len(valid_answers) == 0:
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
                is_partial = bool(inferred_skipped_ids) or (expected_total > len(valid_answers))
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

            payload = ClarificationContextPayload(
                status=status_val,
                questions_version=GOAL_CLARIFIER_SKILL.version,
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
                synthesized_text=synthesized_text,
                updated_at=now.isoformat() if now is not None else "",
            )

            goal.update_clarification(
                clarification_context=payload.to_json_str(),
                now=now,
            )
            await self._goal_repo.save(goal)
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
