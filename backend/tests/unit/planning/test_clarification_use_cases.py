from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import pytest
from uuid6 import uuid7

from src.account.public_api import QuotaExceededError
from src.planning.application.dtos.planning_dtos import (
    ClarificationAnswerItem,
    ClarificationQuestionsResponse,
)
from src.planning.application.use_cases.clarification_use_cases import (
    GenerateClarificationQuestionsUseCase,
    SubmitClarificationAnswersUseCase,
)
from src.planning.application.use_cases.create_goal_and_roadmap import (
    CreateGoalAndRoadmapUseCase,
)
from src.planning.domain.exceptions.planning_exceptions import GoalNotFoundError
from src.planning.domain.models.goal import Goal, GoalStatus
from src.planning.domain.models.roadmap import Roadmap
from src.shared_kernel.application.llm_port import LLMProviderPort
from src.shared_kernel.infrastructure.external_ai.litellm_adapter import MockLLMAdapter


class FakeGoalRepository:
    def __init__(self) -> None:
        self.goals: dict[UUID, Goal] = {}

    async def save(self, goal: Goal) -> Goal:
        self.goals[goal.id] = goal
        return goal

    async def get_by_id(self, goal_id: UUID) -> Goal | None:
        return self.goals.get(goal_id)

    async def get_by_id_for_user(self, goal_id: UUID, user_id: UUID) -> Goal | None:
        goal = self.goals.get(goal_id)
        if goal is not None and goal.user_id == user_id:
            return goal
        return None

    async def list_by_user_id(self, user_id: UUID) -> list[Goal]:
        return [g for g in self.goals.values() if g.user_id == user_id]


class FakeRoadmapRepository:
    def __init__(self) -> None:
        self.roadmaps: dict[UUID, Roadmap] = {}

    async def save(self, roadmap: Roadmap) -> Roadmap:
        self.roadmaps[roadmap.id] = roadmap
        return roadmap

    async def get_by_id(self, roadmap_id: UUID) -> Roadmap | None:
        return self.roadmaps.get(roadmap_id)

    async def get_by_id_for_user(self, roadmap_id: UUID, user_id: UUID) -> Roadmap | None:
        r = self.roadmaps.get(roadmap_id)
        if r is not None and r.user_id == user_id:
            return r
        return None

    async def list_by_user_id(self, user_id: UUID, *, status: str | None = None) -> list[Roadmap]:
        res = [r for r in self.roadmaps.values() if r.user_id == user_id]
        if status:
            res = [r for r in res if r.status.value == status]
        return res

    async def count_active_by_user_id(
        self, user_id: UUID, *, exclude_roadmap_id: UUID | None = None
    ) -> int:
        return len(
            [
                r
                for r in self.roadmaps.values()
                if r.user_id == user_id
                and r.status.value == "ACTIVE"
                and r.id != exclude_roadmap_id
            ]
        )


class FakeQuotaFacade:
    def __init__(self, available: bool = True) -> None:
        self.available = available

    async def check_quota_available(self, user_id: UUID, min_credits: int = 1) -> bool:
        _ = (user_id, min_credits)
        return self.available

    async def reserve_quota(
        self,
        user_id: UUID,
        operation_type: str = "ROADMAP_GEN",
        cost: int = 1,
        ttl_seconds: int = 120,
    ) -> UUID:
        _ = (user_id, operation_type, cost, ttl_seconds)
        return uuid7()

    async def commit_reservation(
        self,
        reservation_id: UUID,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        model_name: str = "gemini-2.5-flash",
    ) -> None:
        _ = (reservation_id, prompt_tokens, completion_tokens, model_name)

    async def release_reservation(self, reservation_id: UUID, reason: str = "RELEASED") -> None:
        _ = (reservation_id, reason)

    async def expire_stale_reservations(self, now: datetime | None = None) -> int:
        _ = now
        return 0


class FakeUnitOfWork:
    def __init__(self) -> None:
        self.committed = False

    async def __aenter__(self) -> "FakeUnitOfWork":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        pass

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.committed = False


@pytest.mark.asyncio
async def test_goal_domain_model_clarification_and_level() -> None:
    now = datetime(2026, 11, 2, 10, 0, tzinfo=UTC)
    goal = Goal(
        title="Lập trình Python cơ bản",
        prior_knowledge_level="intermediate",
        created_at=now,
        updated_at=now,
    )
    assert goal.prior_knowledge_level == "INTERMEDIATE"
    assert goal.clarification_context is None

    goal.update_clarification_context("Đã học xong syntax", now)
    assert goal.clarification_context == "Đã học xong syntax"
    assert goal.updated_at == now


@pytest.mark.asyncio
async def test_create_goal_and_roadmap_with_prior_knowledge() -> None:
    goal_repo = FakeGoalRepository()
    roadmap_repo = FakeRoadmapRepository()
    uow = FakeUnitOfWork()
    user_id = uuid7()

    use_case = CreateGoalAndRoadmapUseCase(
        goal_repo=goal_repo,
        roadmap_repo=roadmap_repo,
        uow=uow,
    )

    result = await use_case.execute(
        user_id=user_id,
        title="Python Mastery",
        prior_knowledge_level="ADVANCED",
    )

    assert result.goal.prior_knowledge_level == "ADVANCED"
    assert result.goal.status == GoalStatus.ACTIVE
    assert uow.committed is True


@pytest.mark.asyncio
async def test_generate_clarification_questions_success() -> None:
    goal_repo = FakeGoalRepository()
    user_id = uuid7()
    goal = Goal(
        id=uuid7(),
        user_id=user_id,
        title="Học Spring Boot",
        raw_description="Muốn làm backend Java",
        prior_knowledge_level="BEGINNER",
    )
    await goal_repo.save(goal)

    quota_facade = FakeQuotaFacade(available=True)
    llm = MockLLMAdapter()

    use_case = GenerateClarificationQuestionsUseCase(
        goal_repo=goal_repo,
        quota_facade=quota_facade,
        llm_provider=llm,
    )

    res = await use_case.execute(goal_id=goal.id, user_id=user_id)
    assert isinstance(res, ClarificationQuestionsResponse)
    assert len(res.questions) >= 2
    assert res.questions[0].question_id == "q1"
    single_choices = [q for q in res.questions if q.question_type == "single_choice"]
    assert len(single_choices) >= 1
    for sc in single_choices:
        assert 3 <= len(sc.options) <= 4


@pytest.mark.asyncio
async def test_generate_clarification_questions_heals_empty_options() -> None:
    class MockEmptyOptionsLLM(LLMProviderPort):
        async def generate_text(
            self, prompt: str, system_prompt: str | None = None, **kwargs: Any
        ) -> tuple[str, int, int]:
            return "{}", 10, 10

        async def generate_structured(
            self,
            prompt: str,
            system_prompt: str | None = None,
            response_schema: Any = None,
            **kwargs: Any,
        ) -> tuple[dict[str, Any], int, int]:
            # Simulate LLM returning single_choice questions with empty options array
            return (
                {
                    "questions": [
                        {
                            "id": "q1",
                            "question": "Bạn đã có kinh nghiệm lập trình nào trước đây chưa?",
                            "question_type": "single_choice",
                            "options": [],
                            "diagnostic_dimension": "PRIOR_EXPOSURE",
                        },
                        {
                            "id": "q2",
                            "question": "Sản phẩm đầu ra bạn mong muốn là gì?",
                            "question_type": "text",
                            "options": [],
                            "diagnostic_dimension": "TARGET_OUTCOME",
                        },
                    ]
                },
                50,
                50,
            )

    goal_repo = FakeGoalRepository()
    user_id = uuid7()
    goal = Goal(
        id=uuid7(),
        user_id=user_id,
        title="Lập trình C++",
    )
    await goal_repo.save(goal)

    use_case = GenerateClarificationQuestionsUseCase(
        goal_repo=goal_repo,
        quota_facade=FakeQuotaFacade(available=True),
        llm_provider=MockEmptyOptionsLLM(),
    )

    res = await use_case.execute(goal_id=goal.id, user_id=user_id)
    assert len(res.questions) >= 2
    q1 = res.questions[0]
    assert q1.question_type == "single_choice"
    # Options must be healed automatically to 3-4 options
    assert 3 <= len(q1.options) <= 4
    assert q1.options[0] != ""
    q2 = res.questions[1]
    assert q2.question_type == "text"
    assert len(q2.options) == 0


@pytest.mark.asyncio
async def test_generate_clarification_questions_idor_protection() -> None:
    goal_repo = FakeGoalRepository()
    user_a = uuid7()
    user_b = uuid7()
    goal = Goal(
        id=uuid7(),
        user_id=user_a,
        title="Học Go",
    )
    await goal_repo.save(goal)

    use_case = GenerateClarificationQuestionsUseCase(
        goal_repo=goal_repo,
        quota_facade=FakeQuotaFacade(available=True),
        llm_provider=MockLLMAdapter(),
    )

    with pytest.raises(GoalNotFoundError):
        await use_case.execute(goal_id=goal.id, user_id=user_b)


@pytest.mark.asyncio
async def test_generate_clarification_questions_quota_exhausted() -> None:
    goal_repo = FakeGoalRepository()
    user_id = uuid7()
    goal = Goal(
        id=uuid7(),
        user_id=user_id,
        title="Học Rust",
    )
    await goal_repo.save(goal)

    use_case = GenerateClarificationQuestionsUseCase(
        goal_repo=goal_repo,
        quota_facade=FakeQuotaFacade(available=False),
        llm_provider=MockLLMAdapter(),
    )

    with pytest.raises(QuotaExceededError):
        await use_case.execute(goal_id=goal.id, user_id=user_id)


@pytest.mark.asyncio
async def test_submit_clarification_answers_success() -> None:
    goal_repo = FakeGoalRepository()
    uow = FakeUnitOfWork()
    user_id = uuid7()
    goal = Goal(
        id=uuid7(),
        user_id=user_id,
        title="Học Machine Learning",
    )
    await goal_repo.save(goal)

    use_case = SubmitClarificationAnswersUseCase(
        goal_repo=goal_repo,
        uow=uow,
    )

    answers = [
        ClarificationAnswerItem(
            question_id="q1",
            question_text="Kinh nghiệm toán và python?",
            answer="Đã biết Python cơ bản và giải tích 1-2",
        ),
        ClarificationAnswerItem(
            question_id="q2",
            question_text="Thời gian học?",
            answer="2 giờ mỗi tối",
        ),
    ]

    updated_goal = await use_case.execute(
        goal_id=goal.id,
        user_id=user_id,
        answers=answers,
    )

    assert updated_goal.clarification_context is not None
    assert "Đã biết Python cơ bản và giải tích 1-2" in updated_goal.clarification_context
    assert "2 giờ mỗi tối" in updated_goal.clarification_context
    assert uow.committed is True
