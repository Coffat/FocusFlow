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
from src.planning.domain.exceptions.planning_exceptions import (
    AIExecutionError,
    GoalNotFoundError,
    InvalidClarificationSessionError,
)
from src.planning.domain.models.goal import Goal, GoalStatus
from src.planning.domain.models.roadmap import Roadmap
from src.shared_kernel.application.harness.models import WorkflowRun, WorkflowStepExecution
from src.shared_kernel.application.llm_port import LLMProviderPort
from tests.helpers.llm_stubs import StubLLMAdapter


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
        self.released_reservations: list[UUID] = []
        self.committed_reservations: list[UUID] = []

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
        model_name: str = "gemini-3.8-flash",
    ) -> None:
        _ = (prompt_tokens, completion_tokens, model_name)
        self.committed_reservations.append(reservation_id)

    async def release_reservation(self, reservation_id: UUID, reason: str = "RELEASED") -> None:
        _ = reason
        self.released_reservations.append(reservation_id)

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


class FakeWorkflowRepository:
    def __init__(self) -> None:
        self.runs: dict[UUID, WorkflowRun] = {}
        self.steps: list[WorkflowStepExecution] = []

    async def add_run(self, run: WorkflowRun) -> None:
        self.runs[run.id] = run

    async def get_run(self, run_id: UUID, *, user_id: UUID | None = None) -> WorkflowRun | None:
        run = self.runs.get(run_id)
        return run if run is not None and (user_id is None or run.user_id == user_id) else None

    async def get_active_run_for_goal(
        self, goal_id: UUID, user_id: UUID, workflow_type: Any
    ) -> WorkflowRun | None:
        return next(
            (
                run
                for run in self.runs.values()
                if run.goal_id == goal_id
                and run.user_id == user_id
                and run.status.value in {"RUNNING", "PAUSED_WAITING_USER"}
            ),
            None,
        )

    async def save_run(self, run: WorkflowRun) -> None:
        self.runs[run.id] = run

    async def add_step(self, step: WorkflowStepExecution) -> None:
        self.steps.append(step)

    async def get_steps(self, run_id: UUID) -> list[WorkflowStepExecution]:
        return [step for step in self.steps if step.workflow_run_id == run_id]


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
    llm = StubLLMAdapter()

    use_case = GenerateClarificationQuestionsUseCase(
        goal_repo=goal_repo,
        quota_facade=quota_facade,
        llm_provider=llm,
    )

    res = await use_case.execute(goal_id=goal.id, user_id=user_id)
    assert isinstance(res, ClarificationQuestionsResponse)
    assert len(res.questions) >= 2
    assert res.questions[0].question_id.endswith("-r1-q1")
    single_choices = [q for q in res.questions if q.question_type == "single_choice"]
    assert len(single_choices) >= 1
    for sc in single_choices:
        assert 3 <= len(sc.options) <= 5
        assert all(option.id and option.label for option in sc.options)


@pytest.mark.asyncio
async def test_generate_clarification_questions_heals_empty_options() -> None:
    class MockEmptyOptionsLLM(LLMProviderPort):
        async def generate_text(
            self, prompt: str, system_prompt: str | None = None, **kwargs: Any
        ) -> tuple[str, int, int]:
            return "{}", 10, 10

        async def generate_structured(
            self,
            *,
            system_prompt: str,
            user_prompt: str,
            response_schema: Any = None,
            tools: Any = None,
            tool_executor: Any = None,
            max_tool_calls: int = 2,
            thinking_level: str | None = None,
            timeout_seconds: float | None = None,
            tool_call_timeout_seconds: float | None = None,
        ) -> tuple[dict[str, Any], int, int]:
            _ = (
                system_prompt,
                user_prompt,
                response_schema,
                tools,
                tool_executor,
                max_tool_calls,
                thinking_level,
                timeout_seconds,
                tool_call_timeout_seconds,
            )
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
    # Options must be healed automatically to 3-5 options
    assert 3 <= len(q1.options) <= 5
    assert q1.options[0].label != ""
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
        llm_provider=StubLLMAdapter(),
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
        llm_provider=StubLLMAdapter(),
    )

    with pytest.raises(QuotaExceededError):
        await use_case.execute(goal_id=goal.id, user_id=user_id)


@pytest.mark.asyncio
async def test_generate_clarification_questions_ai_error_releases_quota_and_raises_ai_execution_error() -> (
    None
):
    class FailingLLMAdapter(LLMProviderPort):
        @property
        def model_identifier(self) -> str:
            return "gemini-3.8-flash"

        async def generate_text(
            self, prompt: str, system_prompt: str = "", **kwargs: Any
        ) -> tuple[str, int, int]:
            raise RuntimeError("503 Service Unavailable: High demand on Gemini model")

        async def generate_structured(
            self, *args: Any, **kwargs: Any
        ) -> tuple[dict[str, Any], int, int]:
            raise RuntimeError("503 Service Unavailable: High demand on Gemini model")

        async def generate_stream(self, *args: Any, **kwargs: Any) -> Any:
            raise NotImplementedError

    goal_repo = FakeGoalRepository()
    user_id = uuid7()
    goal = Goal(
        id=uuid7(),
        user_id=user_id,
        title="Học Kubernetes",
    )
    await goal_repo.save(goal)

    quota_facade = FakeQuotaFacade(available=True)
    use_case = GenerateClarificationQuestionsUseCase(
        goal_repo=goal_repo,
        quota_facade=quota_facade,
        llm_provider=FailingLLMAdapter(),
    )

    with pytest.raises(AIExecutionError) as exc_info:
        await use_case.execute(goal_id=goal.id, user_id=user_id)

    assert (
        "Hệ thống AI hiện đang bận hoặc gặp sự cố kết nối. Vui lòng bấm 'Thử lại' sau giây lát."
        in str(exc_info.value)
    )
    # Check that reservation was released so learner's credits are not deducted
    assert len(quota_facade.released_reservations) == 1


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


@pytest.mark.asyncio
async def test_clarification_answer_item_handles_multiple_choice_list_and_json() -> None:
    # 1. Test raw list of selections
    item_from_list = ClarificationAnswerItem(
        question_id="q1",
        question_text="Công nghệ mong muốn",
        answer=["FastAPI", "Docker", "PostgreSQL"],  # type: ignore[arg-type]
    )
    assert item_from_list.answer == "FastAPI, Docker, PostgreSQL"

    # 2. Test JSON array string
    item_from_json = ClarificationAnswerItem(
        question_id="q2",
        question_text="Chứng chỉ quan tâm",
        answer='["AWS SAA-C03", "Terraform Associate"]',
    )
    assert item_from_json.answer == "AWS SAA-C03, Terraform Associate"

    # 3. Test comma-separated string
    item_from_csv = ClarificationAnswerItem(
        question_id="q3",
        question_text="Nhịp học",
        answer="Buổi tối 20:00 - 22:00, Cuối tuần",
    )
    assert item_from_csv.answer == "Buổi tối 20:00 - 22:00, Cuối tuần"


@pytest.mark.asyncio
async def test_generate_clarification_questions_preserves_multiple_choice() -> None:
    class MockMultipleChoiceLLM(LLMProviderPort):
        async def generate_text(self, *args: Any, **kwargs: Any) -> tuple[str, int, int]:
            return "{}", 10, 10

        async def generate_structured(
            self, *args: Any, **kwargs: Any
        ) -> tuple[dict[str, Any], int, int]:
            return (
                {
                    "questions": [
                        {
                            "id": "q1",
                            "question": "Những mảng nào bạn muốn tập trung rèn luyện?",
                            "question_type": "multiple_choice",
                            "options": [
                                "Kiến trúc hệ thống",
                                "Thực hành bài tập",
                                "Luyện đề thi",
                                "Khác / Mục tiêu tự định nghĩa",
                            ],
                            "diagnostic_dimension": "PRIOR_EXPOSURE",
                        },
                        {
                            "id": "q2",
                            "question": "Mục tiêu cụ thể là gì?",
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
    goal = Goal(id=uuid7(), user_id=user_id, title="Luyện thi AWS")
    await goal_repo.save(goal)

    use_case = GenerateClarificationQuestionsUseCase(
        goal_repo=goal_repo,
        quota_facade=FakeQuotaFacade(available=True),
        llm_provider=MockMultipleChoiceLLM(),
    )
    res = await use_case.execute(goal_id=goal.id, user_id=user_id)
    mc_questions = [q for q in res.questions if q.question_type == "multiple_choice"]
    assert len(mc_questions) >= 1
    assert mc_questions[0].options[0].label == "Kiến trúc hệ thống"
    assert "Khác / Mục tiêu tự định nghĩa" in [option.label for option in mc_questions[0].options]


@pytest.mark.asyncio
async def test_v2_session_validates_answers_and_is_idempotently_resumable() -> None:
    goal_repo = FakeGoalRepository()
    workflow_repo = FakeWorkflowRepository()
    quota = FakeQuotaFacade(available=True)
    uow = FakeUnitOfWork()
    user_id = uuid7()
    goal = Goal(id=uuid7(), user_id=user_id, title="Học AI", raw_description="")
    await goal_repo.save(goal)

    generator = GenerateClarificationQuestionsUseCase(
        goal_repo=goal_repo,
        quota_facade=quota,
        llm_provider=StubLLMAdapter(),
        uow=uow,
        workflow_repo=workflow_repo,
    )
    first = await generator.execute(
        goal_id=goal.id,
        user_id=user_id,
        idempotency_key="idem-clarification-1",
    )
    resumed = await generator.execute(
        goal_id=goal.id,
        user_id=user_id,
        idempotency_key="idem-clarification-1",
    )

    assert first.session_id is not None
    assert resumed.session_id == first.session_id
    assert [q.question_id for q in resumed.questions] == [q.question_id for q in first.questions]

    question = first.questions[0]
    answer = ClarificationAnswerItem(
        question_id=question.question_id,
        selected_option_ids=[question.options[0].id] if question.options else [],
        free_text="Chi tiết do người học xác nhận" if not question.options else None,
    )
    submitter = SubmitClarificationAnswersUseCase(
        goal_repo=goal_repo,
        uow=uow,
        workflow_repo=workflow_repo,
        quota_facade=quota,
        llm_provider=StubLLMAdapter(),
    )
    with pytest.raises(InvalidClarificationSessionError):
        await submitter.execute_turn(
            user_id=user_id,
            goal_id=goal.id,
            session_id=first.session_id,
            round_number=1,
            answers=[answer],
            skipped_question_ids=["forged-question-id"],
            total_questions_count=len(first.questions),
        )
    result = await submitter.execute_turn(
        user_id=user_id,
        goal_id=goal.id,
        session_id=first.session_id,
        round_number=1,
        answers=[answer],
        skipped_question_ids=[q.question_id for q in first.questions[1:]],
        total_questions_count=len(first.questions),
    )

    assert result.status in {"WAITING_FOLLOW_UP", "READY_TO_PLAN"}
    assert result.round in {1, 2}


@pytest.mark.asyncio
async def test_followup_clarification_empty_list_repairs_once_and_fails_safe_releasing_quota() -> (
    None
):
    """Mục 4.6: Follow-up returning [] triggers 1-shot repair; persistent failure releases quota (0 commit) and returns READY_TO_PLAN."""
    from collections.abc import AsyncIterator

    from src.shared_kernel.application.llm_port import LLMGenerationResult

    async def _run_followup_scenario(
        *, recover_on_repair: bool
    ) -> tuple[Any, FakeQuotaFacade, FakeWorkflowRepository, int]:
        goal_repo = FakeGoalRepository()
        workflow_repo = FakeWorkflowRepository()
        quota = FakeQuotaFacade(available=True)
        uow = FakeUnitOfWork()
        user_id = uuid7()
        goal = Goal(id=uuid7(), user_id=user_id, title="Học FastAPI nâng cao", raw_description="")
        await goal_repo.save(goal)

        generator = GenerateClarificationQuestionsUseCase(
            goal_repo=goal_repo,
            quota_facade=quota,
            llm_provider=StubLLMAdapter(),
            uow=uow,
            workflow_repo=workflow_repo,
        )
        round1 = await generator.execute(goal_id=goal.id, user_id=user_id)
        # Clear round 1 commit/release counts so we isolate round 2 follow-up quota behavior.
        quota.committed_reservations.clear()
        quota.released_reservations.clear()

        # Ensure at least one high-priority PARTIAL gap exists so round 2 follow-up triggers.
        assert round1.session_id is not None
        run = workflow_repo.runs[round1.session_id]
        run.context_snapshot["information_gaps"] = [
            {"dimension": "TIMELINE", "status": "PARTIAL", "priority": 95},
        ]

        followup_calls = 0

        class _FollowupProvider(LLMProviderPort):
            async def generate_structured(self, **kwargs: Any) -> LLMGenerationResult:
                nonlocal followup_calls
                del kwargs
                followup_calls += 1
                if followup_calls == 1 or not recover_on_repair:
                    return LLMGenerationResult(
                        payload={"questions": []},
                        prompt_tokens=15,
                        output_tokens=5,
                        model_id="gemini-3.8-flash",
                    )
                return LLMGenerationResult(
                    payload={
                        "questions": [
                            {
                                "text": "Bạn dự kiến hoàn thành mục tiêu này trong bao nhiêu tuần?",
                                "question_type": "single_choice",
                                "options": ["2 - 4 tuần", "1 - 2 tháng", "3 tháng"],
                                "question_purpose": "Chốt deadline lập lịch.",
                                "expected_answer_format": "Chọn 1 phương án.",
                                "diagnostic_dimension": "TIMELINE",
                            }
                        ]
                    },
                    prompt_tokens=20,
                    output_tokens=15,
                    model_id="gemini-3.8-flash",
                )

            async def stream_structured(self, **kwargs: Any) -> AsyncIterator[str]:
                del kwargs
                yield "{}"

        q0 = round1.questions[0]
        ans = ClarificationAnswerItem(
            question_id=q0.question_id,
            selected_option_ids=[q0.options[0].id] if q0.options else [],
            free_text="Xác nhận" if not q0.options else None,
        )
        submitter = SubmitClarificationAnswersUseCase(
            goal_repo=goal_repo,
            uow=uow,
            workflow_repo=workflow_repo,
            quota_facade=quota,
            llm_provider=_FollowupProvider(),
        )
        turn_res = await submitter.execute_turn(
            user_id=user_id,
            goal_id=goal.id,
            session_id=round1.session_id,
            round_number=1,
            answers=[ans],
            skipped_question_ids=[q.question_id for q in round1.questions[1:]],
            total_questions_count=len(round1.questions),
        )
        return turn_res, quota, workflow_repo, followup_calls

    # Scenario A: Follow-up returns [] -> 1-shot repair recovers -> commits 1 reservation.
    ok_res, ok_quota, _, ok_calls = await _run_followup_scenario(recover_on_repair=True)
    assert ok_calls == 2
    assert ok_res.status == "WAITING_FOLLOW_UP"
    assert len(ok_res.questions) == 1
    assert len(ok_quota.committed_reservations) == 1
    assert ok_quota.released_reservations == []

    # Scenario B: Follow-up returns [] on initial + repair -> releases quota (0 commit), returns READY_TO_PLAN safely.
    fail_res, fail_quota, fail_wf, fail_calls = await _run_followup_scenario(
        recover_on_repair=False
    )
    assert fail_calls == 2
    assert fail_res.status == "READY_TO_PLAN"
    assert fail_res.questions == ()
    assert fail_quota.committed_reservations == []
    assert len(fail_quota.released_reservations) == 1
    fallback_step = next(
        s for s in fail_wf.steps if s.step_name == "CLARIFICATION_FOLLOW_UP_FALLBACK"
    )
    assert fallback_step.output_payload["error_category"] == "SCHEMA_MISMATCH"
