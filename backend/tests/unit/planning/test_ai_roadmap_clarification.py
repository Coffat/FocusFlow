from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

import pytest
from uuid6 import uuid7

from src.account.public_api import QuotaFacadePort
from src.planning.application.dtos.planning_dtos import (
    ClarificationAnswerItem,
    ClarificationQuestionsResponse,
    parse_clarification_context,
)
from src.planning.application.ports.planning_repository_ports import GoalRepositoryPort
from src.planning.application.use_cases.clarification_use_cases import (
    GenerateClarificationQuestionsUseCase,
    SubmitClarificationAnswersUseCase,
)
from src.planning.domain.models.goal import Goal, GoalStatus
from src.shared_kernel.application.uow import AsyncUnitOfWork
from src.shared_kernel.infrastructure.external_ai.litellm_adapter import MockLLMAdapter


class _InMemoryGoalRepo(GoalRepositoryPort):
    def __init__(self, initial: Goal | None = None) -> None:
        self.items: dict[UUID, Goal] = {}
        if initial is not None:
            self.items[initial.id] = initial

    async def get_by_id(self, goal_id: UUID) -> Goal | None:
        return self.items.get(goal_id)

    async def get_by_id_for_user(self, goal_id: UUID, user_id: UUID) -> Goal | None:
        g = self.items.get(goal_id)
        if g is not None and g.user_id == user_id:
            return g
        return None

    async def save(self, goal: Goal) -> Goal:
        self.items[goal.id] = goal
        return goal


class _DummyUoW(AsyncUnitOfWork):
    def __init__(self) -> None:
        self.committed = False

    async def __aenter__(self) -> "_DummyUoW":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        pass

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        pass


class _DummyQuotaFacade(QuotaFacadePort):
    def __init__(self) -> None:
        self.reserved: list[tuple[UUID, str]] = []
        self.committed: list[tuple[UUID, int, int]] = []
        self.released: list[UUID] = []

    async def reserve_slot(
        self,
        user_id: UUID,
        operation: str,
        *,
        cost: int = 1,
        ttl_seconds: int = 300,
        now: datetime | None = None,
    ) -> UUID:
        _ = (cost, ttl_seconds, now)
        rid = uuid7()
        self.reserved.append((user_id, operation))
        return rid

    async def commit_reservation(
        self,
        reservation_id: UUID,
        *,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        model_name: str = "gemini-3.8-flash",
        now: datetime | None = None,
    ) -> None:
        _ = (model_name, now)
        self.committed.append((reservation_id, prompt_tokens, completion_tokens))

    async def release_reservation(
        self,
        reservation_id: UUID,
        *,
        now: datetime | None = None,
    ) -> None:
        _ = now
        self.released.append(reservation_id)

    async def expire_stale_reservations(self, *, now: datetime | None = None) -> int:
        _ = now
        return 0


@pytest.mark.asyncio
async def test_generate_clarification_questions_avoids_known_dimensions_and_populates_metadata() -> (
    None
):
    now = datetime(2026, 11, 2, 10, 0, tzinfo=UTC)
    user_id = uuid7()
    goal = Goal(
        id=uuid7(),
        user_id=user_id,
        title="Học FastAPI và SQLAlchemy 2.0",
        raw_description=(
            "Tôi đã biết Python cơ bản 1 năm kinh nghiệm, muốn làm dự án REST API thực tế "
            "trong 6 tuần với lịch học 2 giờ/ngày."
        ),
        target_date=date(2026, 12, 15),
        prior_knowledge_level="INTERMEDIATE",
        status=GoalStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
    repo = _InMemoryGoalRepo(goal)
    quota = _DummyQuotaFacade()
    uow = _DummyUoW()
    llm = MockLLMAdapter()

    uc = GenerateClarificationQuestionsUseCase(
        goal_repo=repo,
        quota_facade=quota,
        llm_provider=llm,
        uow=uow,
    )
    res: ClarificationQuestionsResponse = await uc.execute(
        user_id=user_id,
        goal_id=goal.id,
        now=now,
    )

    assert 2 <= len(res.questions) <= 3
    for q in res.questions:
        assert q.id.startswith("q")
        assert q.question_id == q.id
        assert len(q.question) > 10
        assert q.text == q.question
        assert len(q.question_purpose) > 5
        assert len(q.expected_answer_format) > 5
        assert len(q.diagnostic_dimension) > 2
        # Learner already provided PRIOR_EXPOSURE, TARGET_OUTCOME, TIMELINE_URGENCY, TIME_COMMITMENT
        assert q.diagnostic_dimension not in {
            "PRIOR_EXPOSURE",
            "TARGET_OUTCOME",
            "TIMELINE_URGENCY",
            "TIME_COMMITMENT",
        }
        if q.question_type == "single_choice":
            assert len(q.options) >= 3
        elif q.question_type == "text":
            assert len(q.options) == 0

    assert any(q.question_type == "single_choice" and len(q.options) >= 3 for q in res.questions)
    assert len(quota.reserved) == 1
    assert len(quota.committed) == 1
    assert len(quota.released) == 0


@pytest.mark.asyncio
async def test_submit_clarification_answers_full_partial_and_skipped_states() -> None:
    now = datetime(2026, 11, 2, 10, 0, tzinfo=UTC)
    user_id = uuid7()
    goal = Goal(
        id=uuid7(),
        user_id=user_id,
        title="Chinh phục Cấu trúc dữ liệu & Giải thuật",
        raw_description="Chuẩn bị phỏng vấn thuật toán.",
        target_date=date(2026, 12, 20),
        prior_knowledge_level="BEGINNER",
        status=GoalStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
    repo = _InMemoryGoalRepo(goal)
    uow = _DummyUoW()
    submit_uc = SubmitClarificationAnswersUseCase(goal_repo=repo, uow=uow)

    # 1. Full ANSWERED
    updated_full = await submit_uc.execute(
        user_id=user_id,
        goal_id=goal.id,
        answers=[
            ClarificationAnswerItem(
                question_id="q1",
                question_text="Ngôn ngữ ưu tiên?",
                answer="Python 3.12",
            ),
            ClarificationAnswerItem(
                question_id="q2",
                question_text="Mục tiêu đầu ra?",
                answer="Giải được 75 bài LeetCode Medium",
            ),
        ],
        total_questions_count=2,
        now=now,
    )
    assert updated_full.clarification_context is not None
    assert "Python 3.12" in updated_full.clarification_context
    parsed_full = parse_clarification_context(updated_full.clarification_context)
    assert parsed_full is not None
    assert parsed_full.status == "ANSWERED"
    assert len(parsed_full.answers) == 2
    assert parsed_full.unresolved_assumptions == []

    # 2. PARTIAL (1 answered, 1 empty/skipped)
    updated_partial = await submit_uc.execute(
        user_id=user_id,
        goal_id=goal.id,
        answers=[
            ClarificationAnswerItem(
                question_id="q1",
                question_text="Ngôn ngữ ưu tiên?",
                answer="Python 3.12",
            ),
            ClarificationAnswerItem(
                question_id="q2",
                question_text="Phong cách học?",
                answer="   ",
            ),
        ],
        total_questions_count=2,
        now=now,
    )
    parsed_partial = parse_clarification_context(updated_partial.clarification_context)
    assert parsed_partial is not None
    assert parsed_partial.status == "PARTIAL"
    assert "q2" in parsed_partial.skipped_questions
    assert len(parsed_partial.unresolved_assumptions) >= 1

    # 3. SKIPPED via .skip()
    updated_skipped = await submit_uc.skip(
        user_id=user_id,
        goal_id=goal.id,
        skipped_question_ids=["q1", "q2", "q3"],
        now=now,
    )
    parsed_skipped = parse_clarification_context(updated_skipped.clarification_context)
    assert parsed_skipped is not None
    assert parsed_skipped.status == "SKIPPED"
    assert parsed_skipped.answers == []
    assert parsed_skipped.skipped_questions == ["q1", "q2", "q3"]
    assert len(parsed_skipped.unresolved_assumptions) >= 2


def test_parse_clarification_context_backward_compatibility_with_legacy_text() -> None:
    legacy = "Câu hỏi 1: Kinh nghiệm? - Trả lời: Đã học C++ cơ bản."
    parsed = parse_clarification_context(legacy)
    assert parsed is not None
    assert parsed.status == "ANSWERED"
    assert "Đã học C++ cơ bản" in parsed.synthesized_text

    parsed_empty = parse_clarification_context(None)
    assert parsed_empty is not None
    assert parsed_empty.status == "SKIPPED"
    assert len(parsed_empty.unresolved_assumptions) >= 1
