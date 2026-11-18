"""Unit tests for Group 5: Parallel Tier 3 Judge + Dual Critics, Compact Payload, and Pipeline Budget."""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID, uuid4

import pytest

from src.planning.application.services.validation_gate import (
    TIER3_JUDGE_TIMEOUT_SECONDS,
    ProposalValidationGateOrchestrator,
    build_compact_judge_payload,
    execute_tier3_pedagogical_judge,
)
from src.planning.domain.models.milestone import Milestone, MilestoneStatus
from src.planning.domain.services.validation_types import AvailabilityConfigurationDTO
from src.shared_kernel.application.harness.models import (
    WorkflowRun,
    WorkflowStepExecution,
    WorkflowType,
)
from src.shared_kernel.application.llm_port import LLMGenerationResult
from src.shared_kernel.config import Settings


class _ConcurrencySafeWorkflowRepo:
    """Fake WorkflowRepositoryPort asserting no concurrent writes happen during asyncio.gather."""

    def __init__(self) -> None:
        self.runs: list[WorkflowRun] = []
        self.steps: list[WorkflowStepExecution] = []
        self._active_writes = 0
        self.max_concurrent_writes = 0

    async def add_run(self, run: WorkflowRun) -> None:
        self._active_writes += 1
        self.max_concurrent_writes = max(self.max_concurrent_writes, self._active_writes)
        try:
            await asyncio.sleep(0.002)
            self.runs.append(run)
        finally:
            self._active_writes -= 1

    async def get_run(self, run_id: UUID, *, user_id: UUID | None = None) -> WorkflowRun | None:
        del user_id
        return next((r for r in self.runs if r.id == run_id), None)

    async def get_run_for_update(
        self, run_id: UUID, *, user_id: UUID | None = None
    ) -> WorkflowRun | None:
        return await self.get_run(run_id, user_id=user_id)

    async def get_active_run_for_goal(
        self,
        goal_id: UUID,
        user_id: UUID,
        workflow_type: WorkflowType = WorkflowType.PLAN_CREATION,
    ) -> WorkflowRun | None:
        del goal_id, user_id, workflow_type
        return None

    async def acquire_goal_clarification_lock(self, goal_id: UUID, user_id: UUID) -> None:
        del goal_id, user_id

    async def get_run_by_idempotency_key(
        self, goal_id: UUID, user_id: UUID, idempotency_key: str
    ) -> WorkflowRun | None:
        del goal_id, user_id, idempotency_key
        return None

    async def save_run(self, run: WorkflowRun) -> None:
        self.runs.append(run)

    async def add_step(self, step: WorkflowStepExecution) -> None:
        self._active_writes += 1
        self.max_concurrent_writes = max(self.max_concurrent_writes, self._active_writes)
        try:
            await asyncio.sleep(0.002)
            self.steps.append(step)
        finally:
            self._active_writes -= 1

    async def get_steps(self, run_id: UUID) -> list[WorkflowStepExecution]:
        return [s for s in self.steps if s.workflow_run_id == run_id]


def test_group5_default_judge_timeout_and_min_remaining_settings() -> None:
    """Requirement #3: tier3_judge_timeout_seconds must default to 12.0 and min remaining to 3.0."""
    settings = Settings()
    assert settings.tier3_judge_timeout_seconds == 12.0
    assert settings.ai_min_judge_remaining_seconds == 3.0
    assert TIER3_JUDGE_TIMEOUT_SECONDS == 12.0


@pytest.mark.asyncio
async def test_judge_and_dual_critics_run_in_parallel_via_gather_and_persist_sequentially() -> None:
    """Critics (0.25s) + Judge (0.25s) must finish in < 0.45s total and never flush repo concurrently."""
    m_id = uuid4()
    roadmap_id = uuid4()
    milestone = Milestone(
        id=m_id,
        roadmap_id=roadmap_id,
        sequence_order=1,
        title="Cột mốc 1: Python & FastAPI",
        learning_outcomes=("M1-O1: Tạo REST API CRUD",),
        completion_criteria="Pass 100% unit test API",
        estimated_effort_minutes=120,
        required_concepts=("fastapi-routing",),
        status=MilestoneStatus.APPROVED,
    )

    recorded_judge_prompts: list[str] = []

    class _ParallelTimingLLM:
        model_identifier = "gemini-3.8-flash-low"

        async def generate_structured(
            self,
            *,
            system_prompt: str,
            user_prompt: str,
            **kwargs: Any,
        ) -> LLMGenerationResult:
            del kwargs
            if "[INDEPENDENT_CRITIC:" in user_prompt:
                await asyncio.sleep(0.25)
                return LLMGenerationResult(
                    payload={"status": "PASS", "score": 92, "issues": []},
                    prompt_tokens=40,
                    output_tokens=20,
                    thinking_tokens=0,
                    model_id="gemini-3.8-flash-low",
                )
            if (
                "pedagogical-quality-judge" in system_prompt
                or "pedagogical-quality-judge" in user_prompt
            ):
                recorded_judge_prompts.append(user_prompt)
                await asyncio.sleep(0.25)
                return LLMGenerationResult(
                    payload={"score": 90, "overall_status": "PASS", "issues": []},
                    prompt_tokens=50,
                    output_tokens=25,
                    thinking_tokens=0,
                    model_id="gemini-3.8-flash-low",
                )
            return LLMGenerationResult(
                payload={
                    "tasks": [
                        {
                            "task_id": "T1",
                            "milestone_id": str(m_id),
                            "title": "Học Pydantic v2",
                            "task_type": "THEORY",
                            "estimated_minutes": 60,
                            "scheduled_date": "2026-11-18",
                            "learning_objective": "Hiểu schema Pydantic",
                            "completion_criteria": "Tạo 2 model hợp lệ",
                            "covered_outcome_ids": ["M1-O1"],
                            "concept_ids": ["fastapi-routing"],
                        },
                        {
                            "task_id": "T2",
                            "milestone_id": str(m_id),
                            "title": "Xây dựng endpoint CRUD",
                            "task_type": "PRACTICE",
                            "estimated_minutes": 60,
                            "scheduled_date": "2026-11-19",
                            "learning_objective": "Viết router FastAPI",
                            "completion_criteria": "TestClient trả 200 OK",
                            "covered_outcome_ids": ["M1-O1"],
                            "concept_ids": ["fastapi-routing"],
                        },
                    ],
                    "dependencies": [
                        {"predecessor_id": "T1", "successor_id": "T2", "is_mandatory": True}
                    ],
                },
                prompt_tokens=80,
                output_tokens=60,
                thinking_tokens=0,
                model_id="gemini-3.8-flash-low",
            )

        async def stream_structured(self, **kwargs: Any) -> AsyncIterator[str]:
            del kwargs
            yield "{}"

    wf_repo = _ConcurrencySafeWorkflowRepo()
    orch = ProposalValidationGateOrchestrator(
        llm_provider=_ParallelTimingLLM(),  # type: ignore[arg-type]
        enable_tier3_judge=True,
        workflow_repo=wf_repo,
        user_id=uuid4(),
        goal_id=uuid4(),
        roadmap_id=roadmap_id,
    )
    avail = AvailabilityConfigurationDTO(mode="MODE_A", default_daily_quota_minutes=120)

    t0 = time.perf_counter()
    res = await orch.generate_and_validate_proposal_with_retry(
        system_prompt="Task Decomposer",
        user_prompt="Sinh tasks",
        response_schema={"type": "object"},
        availability=avail,
        valid_milestone_ids={m_id},
        start_date=None,
        goal_title="FastAPI Backend",
        learner_level="BEGINNER",
        milestones=[milestone],
        deterministic_allocation=True,
    )
    elapsed = time.perf_counter() - t0

    assert res.is_valid is True
    assert res.judge_status == "PASSED"
    assert res.judge_skipped is False
    assert res.pedagogical_score == 90.0
    assert res.total_prompt_tokens == 210
    assert res.total_completion_tokens == 125
    # 0.25s critics + 0.25s judge run concurrently -> total must be well below 0.45s (sequential would be >= 0.50s)
    assert elapsed < 0.45, f"Expected parallel Critic+Judge < 0.45s, got {elapsed:.3f}s"
    assert wf_repo.max_concurrent_writes == 1
    recorded_steps = {s.step_name for s in wf_repo.steps}
    assert {
        "TASK_DECOMPOSER",
        "COVERAGE_PREREQUISITE_CRITIC",
        "LEARNER_FIT_ACTIONABILITY_CRITIC",
        "PEDAGOGICAL_JUDGE",
    }.issubset(recorded_steps)
    assert len(recorded_judge_prompts) == 1
    assert "Pass 100% unit test API" in recorded_judge_prompts[0]
    assert "depends_on_task_ids" in recorded_judge_prompts[0]


@pytest.mark.asyncio
async def test_judge_skips_cleanly_on_exhausted_or_low_remaining_budget() -> None:
    """When remaining_budget_seconds <= 0 or < min_judge_remaining_seconds, Judge must not call LLM."""
    llm_calls = 0
    seen_timeouts: list[float | None] = []

    class _TrackingJudgeLLM:
        model_identifier = "gemini-3.8-flash-low"

        async def generate_structured(
            self, *, timeout_seconds: float | None = None, **kwargs: Any
        ) -> LLMGenerationResult:
            nonlocal llm_calls
            del kwargs
            llm_calls += 1
            seen_timeouts.append(timeout_seconds)
            return LLMGenerationResult(
                payload={"score": 88, "overall_status": "PASS", "issues": []},
                prompt_tokens=20,
                output_tokens=10,
                thinking_tokens=0,
                model_id="gemini-3.8-flash-low",
            )

        async def stream_structured(self, **kwargs: Any) -> AsyncIterator[str]:
            del kwargs
            yield "{}"

    llm = _TrackingJudgeLLM()
    proposal = {"tasks": [{"task_id": "T1", "title": "Task 1"}], "dependencies": []}

    # 1. remaining_budget_seconds <= 0 -> REVIEW_PENDING, 0 LLM calls
    out_zero = await execute_tier3_pedagogical_judge(
        llm,  # type: ignore[arg-type]
        proposal,
        remaining_budget_seconds=0.0,
    )
    assert out_zero.judge_skipped is True
    assert out_zero.judge_status == "REVIEW_PENDING"
    assert out_zero.pedagogical_score is None
    assert llm_calls == 0

    # 2. 0 < remaining_budget_seconds < ai_min_judge_remaining_seconds (3.0) -> REVIEW_PENDING, 0 LLM calls
    out_low = await execute_tier3_pedagogical_judge(
        llm,  # type: ignore[arg-type]
        proposal,
        remaining_budget_seconds=2.5,
        min_judge_remaining_seconds=3.0,
    )
    assert out_low.judge_skipped is True
    assert out_low.judge_status == "REVIEW_PENDING"
    assert out_low.pedagogical_score is None
    assert llm_calls == 0

    # 3. remaining_budget_seconds >= 3.0 -> calls LLM with min(tier3_timeout, remaining_budget)
    out_ok = await execute_tier3_pedagogical_judge(
        llm,  # type: ignore[arg-type]
        proposal,
        tier3_timeout_seconds=8.0,
        remaining_budget_seconds=5.2,
        min_judge_remaining_seconds=3.0,
    )
    assert out_ok.judge_skipped is False
    assert out_ok.judge_status == "PASSED"
    assert out_ok.pedagogical_score == 88.0
    assert llm_calls == 1
    assert seen_timeouts[-1] == pytest.approx(5.2, abs=0.05)

    # 4. Config override > 12.0 (e.g., 15.0) is NOT clamped to 12.0
    out_override = await execute_tier3_pedagogical_judge(
        llm,  # type: ignore[arg-type]
        proposal,
        tier3_timeout_seconds=15.0,
        remaining_budget_seconds=20.0,
    )
    assert out_override.judge_status == "PASSED"
    assert seen_timeouts[-1] == pytest.approx(15.0, abs=0.05)


@pytest.mark.asyncio
async def test_judge_method_a_dynamic_timeout_in_gather(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Method A: inside asyncio.gather with Dual Critics, Judge timeout = min(tier3_judge_timeout_seconds, remaining_budget)."""
    import src.planning.application.services.validation_gate.orchestrator as orch_mod

    m_id = uuid4()
    roadmap_id = uuid4()
    milestone = Milestone(
        id=m_id,
        roadmap_id=roadmap_id,
        sequence_order=1,
        title="Cột mốc 1: Python & FastAPI",
        learning_outcomes=("M1-O1: Tạo REST API CRUD",),
        completion_criteria="Pass 100% unit test API",
        estimated_effort_minutes=120,
        required_concepts=("fastapi-routing",),
        status=MilestoneStatus.APPROVED,
    )

    recorded_judge_timeouts: list[float | None] = []
    recorded_judge_call_args: list[tuple[float | None, float | None]] = []
    critic_calls = 0

    real_execute_judge = orch_mod.execute_tier3_pedagogical_judge

    async def spy_execute_judge(*args: Any, **kwargs: Any) -> Any:
        recorded_judge_call_args.append(
            (kwargs.get("tier3_timeout_seconds"), kwargs.get("remaining_budget_seconds"))
        )
        return await real_execute_judge(*args, **kwargs)

    monkeypatch.setattr(orch_mod, "execute_tier3_pedagogical_judge", spy_execute_judge)

    class _DynamicTimeoutLLM:
        model_identifier = "gemini-3.8-flash-low"

        async def generate_structured(
            self,
            *,
            system_prompt: str,
            user_prompt: str,
            timeout_seconds: float | None = None,
            **kwargs: Any,
        ) -> LLMGenerationResult:
            nonlocal critic_calls
            del kwargs
            if "[INDEPENDENT_CRITIC:" in user_prompt:
                critic_calls += 1
                return LLMGenerationResult(
                    payload={"status": "PASS", "score": 92, "issues": []},
                    prompt_tokens=20,
                    output_tokens=10,
                    thinking_tokens=0,
                    model_id="gemini-3.8-flash-low",
                )
            if (
                "pedagogical-quality-judge" in system_prompt
                or "pedagogical-quality-judge" in user_prompt
            ):
                recorded_judge_timeouts.append(timeout_seconds)
                return LLMGenerationResult(
                    payload={"score": 90, "overall_status": "PASS", "issues": []},
                    prompt_tokens=30,
                    output_tokens=15,
                    thinking_tokens=0,
                    model_id="gemini-3.8-flash-low",
                )
            return LLMGenerationResult(
                payload={
                    "tasks": [
                        {
                            "task_id": "T1",
                            "milestone_id": str(m_id),
                            "title": "Học Pydantic v2",
                            "task_type": "THEORY",
                            "estimated_minutes": 60,
                            "scheduled_date": "2026-11-18",
                            "learning_objective": "Hiểu schema Pydantic",
                            "completion_criteria": "Tạo 2 model hợp lệ",
                            "covered_outcome_ids": ["M1-O1"],
                            "concept_ids": ["fastapi-routing"],
                        },
                        {
                            "task_id": "T2",
                            "milestone_id": str(m_id),
                            "title": "Xây dựng endpoint CRUD",
                            "task_type": "PRACTICE",
                            "estimated_minutes": 60,
                            "scheduled_date": "2026-11-19",
                            "learning_objective": "Viết router FastAPI",
                            "completion_criteria": "TestClient trả 200 OK",
                            "covered_outcome_ids": ["M1-O1"],
                            "concept_ids": ["fastapi-routing"],
                        },
                    ],
                    "dependencies": [
                        {"predecessor_id": "T1", "successor_id": "T2", "is_mandatory": True}
                    ],
                },
                prompt_tokens=50,
                output_tokens=40,
                thinking_tokens=0,
                model_id="gemini-3.8-flash-low",
            )

        async def stream_structured(self, **kwargs: Any) -> AsyncIterator[str]:
            del kwargs
            yield "{}"

    avail = AvailabilityConfigurationDTO(mode="MODE_A", default_daily_quota_minutes=120)

    # Case 1: remaining_budget ~ 9.0s (< 12.0s default cap) -> Judge receives <= 9.0s
    base_settings = Settings()
    monkeypatch.setattr(
        orch_mod,
        "get_settings",
        lambda: base_settings.model_copy(update={"ai_sse_pipeline_timeout_seconds": 9.0}),
    )
    orch = ProposalValidationGateOrchestrator(
        llm_provider=_DynamicTimeoutLLM(),  # type: ignore[arg-type]
        enable_tier3_judge=True,
        user_id=uuid4(),
        goal_id=uuid4(),
        roadmap_id=roadmap_id,
    )
    res_9s = await orch.generate_and_validate_proposal_with_retry(
        system_prompt="Task Decomposer",
        user_prompt="Sinh tasks",
        response_schema={"type": "object"},
        availability=avail,
        valid_milestone_ids={m_id},
        goal_title="FastAPI Backend",
        learner_level="BEGINNER",
        milestones=[milestone],
        deterministic_allocation=True,
    )
    assert res_9s.judge_status == "PASSED"
    assert critic_calls == 2
    assert len(recorded_judge_call_args) == 1
    cap_9s, rem_9s = recorded_judge_call_args[0]
    assert cap_9s is not None and rem_9s is not None
    assert 8.0 < cap_9s <= 9.0
    assert cap_9s == pytest.approx(rem_9s, abs=1e-6)
    assert recorded_judge_timeouts[0] is not None
    assert 8.0 < recorded_judge_timeouts[0] <= 9.0

    # Case 2: remaining_budget ~ 40.0s (> 12.0s default cap) -> Judge receives 12.0s
    monkeypatch.setattr(
        orch_mod,
        "get_settings",
        lambda: base_settings.model_copy(update={"ai_sse_pipeline_timeout_seconds": 40.0}),
    )
    res_40s = await orch.generate_and_validate_proposal_with_retry(
        system_prompt="Task Decomposer",
        user_prompt="Sinh tasks",
        response_schema={"type": "object"},
        availability=avail,
        valid_milestone_ids={m_id},
        goal_title="FastAPI Backend",
        learner_level="BEGINNER",
        milestones=[milestone],
        deterministic_allocation=True,
    )
    assert res_40s.judge_status == "PASSED"
    assert critic_calls == 4
    assert len(recorded_judge_call_args) == 2
    cap_40s, rem_40s = recorded_judge_call_args[1]
    assert cap_40s == pytest.approx(12.0, abs=0.01)
    assert rem_40s is not None and rem_40s > 35.0
    assert recorded_judge_timeouts[1] == pytest.approx(12.0, abs=0.01)


def test_build_compact_judge_payload_strips_noise_but_preserves_deps_objectives_criteria() -> None:
    """Compact payload must strip noisy fields while preserving 100% of dependencies, objectives, and criteria."""
    m1_id = str(uuid4())
    milestone_entity = Milestone(
        id=UUID(m1_id),
        roadmap_id=uuid4(),
        sequence_order=1,
        title="Chặng 1: Python Nền tảng",
        learning_outcomes=(
            "M1-O1: Thành thạo hàm và type hints",
            "M1-O2: Xử lý ngoại lệ đúng chuẩn",
        ),
        completion_criteria="Hoàn thành 5 bài tập pytest pass 100%",
        estimated_effort_minutes=180,
        required_concepts=("py-functions",),
        status=MilestoneStatus.APPROVED,
    )
    full_proposal: dict[str, Any] = {
        "tasks": [
            {
                "task_id": "T1",
                "milestone_id": m1_id,
                "title": "Học cú pháp hàm Python",
                "description": "Mô tả rất dài cần loại bỏ khỏi payload judge...",
                "task_type": "THEORY",
                "estimated_minutes": 45,
                "scheduled_date": "2026-11-18",
                "scheduled_start": "2026-11-18T19:00:00+00:00",
                "scheduled_end": "2026-11-18T19:45:00+00:00",
                "learning_objective": "Viết được hàm Python kèm type annotations đầy đủ.",
                "completion_criteria": "Tạo 3 hàm có docstring và mypy clean.",
                "covered_outcome_ids": ["M1-O1"],
                "resource_ids": ["res-001"],
                "learning_resources": [
                    {
                        "resource_id": "res-001",
                        "title": "Python Docs",
                        "url": "https://docs.python.org/3/tutorial/controlflow.html#very-long-url",
                        "description": "Extremely verbose resource description...",
                    }
                ],
                "resources": [
                    {"url": "https://example.com/noisy-resource", "description": "Noisy text"}
                ],
            },
            {
                "task_id": "T2",
                "milestone_id": m1_id,
                "title": "Thực hành xử lý ngoại lệ",
                "description": "Mô tả thừa thứ 2...",
                "task_type": "PRACTICE",
                "estimated_minutes": 60,
                "scheduled_date": "2026-11-19",
                "learning_objective": "Áp dụng try/except/raise tùy chỉnh theo domain.",
                "completion_criteria": "Viết unit test kiểm tra 3 ca lỗi biên.",
                "covered_outcome_ids": ["M1-O2"],
                "depends_on_task_ids": ["T1"],
                "dependencies": ["T1"],
            },
        ],
        "dependencies": [{"predecessor_id": "T1", "successor_id": "T2", "is_mandatory": True}],
        "quality_reviews": [{"critic": "COVERAGE", "status": "PASS", "issues": []}],
        "_capacity_overflow": {"available_minutes": 600, "required_minutes": 105},
        "schedule_blocks": [
            {"block_id": "b1", "start": "19:00", "end": "20:00"} for _ in range(10)
        ],
        "resources": [{"url": "https://example.com/top-level-noisy-resource"}],
        "learning_resources": [{"url": "https://example.com/top-level-learning-resource"}],
    }

    compact = build_compact_judge_payload(full_proposal, milestones_metadata=[milestone_entity])
    serialized = json.dumps(compact, ensure_ascii=False)

    # Noisy fields stripped completely
    for stripped_marker in (
        "quality_reviews",
        "_capacity_overflow",
        "schedule_blocks",
        "learning_resources",
        "https://docs.python.org",
        "https://example.com/noisy-resource",
        "Mô tả rất dài",
    ):
        assert stripped_marker not in serialized

    assert "resources" not in compact
    assert len(compact["tasks"]) == 2
    t1, t2 = compact["tasks"]
    assert t1["task_id"] == "T1"
    assert t1["milestone_id"] == m1_id
    assert t1["task_type"] == "THEORY"
    assert t1["estimated_minutes"] == 45
    assert t1["scheduled_date"] == "2026-11-18"
    assert t1["learning_objective"] == "Viết được hàm Python kèm type annotations đầy đủ."
    assert t1["completion_criteria"] == "Tạo 3 hàm có docstring và mypy clean."
    assert t1["depends_on_task_ids"] == []

    assert t2["depends_on_task_ids"] == ["T1"]
    assert t2["dependencies"] == ["T1"]
    assert t2["learning_objective"] == "Áp dụng try/except/raise tùy chỉnh theo domain."
    assert t2["completion_criteria"] == "Viết unit test kiểm tra 3 ca lỗi biên."

    assert compact["dependencies"] == [
        {"predecessor_id": "T1", "successor_id": "T2", "is_mandatory": True}
    ]

    assert len(compact["milestones"]) == 1
    m_out = compact["milestones"][0]
    assert m_out["milestone_id"] == m1_id
    assert m_out["sequence_order"] == 1
    assert m_out["title"] == "Chặng 1: Python Nền tảng"
    assert m_out["learning_outcomes"] == [
        "M1-O1: Thành thạo hàm và type hints",
        "M1-O2: Xử lý ngoại lệ đúng chuẩn",
    ]
    assert m_out["completion_criteria"] == "Hoàn thành 5 bài tập pytest pass 100%"


@pytest.mark.asyncio
async def test_judge_status_and_skipped_invariant_across_all_four_states() -> None:
    """Verify exact (judge_skipped, pedagogical_score, judge_status) invariant for all 4 statuses."""
    proposal = {"tasks": [{"task_id": "T1", "title": "Task 1"}], "dependencies": []}

    # 1. SKIPPED (disabled)
    skipped_out = await execute_tier3_pedagogical_judge(
        None,
        proposal,
        enable_tier3_judge=False,
    )
    assert skipped_out.judge_status == "SKIPPED"
    assert skipped_out.judge_skipped is True
    assert skipped_out.pedagogical_score is None

    # 2. REVIEW_PENDING (missing score / error / timeout — never 0.85/PASS default)
    class _MalformedScoreLLM:
        model_identifier = "gemini-3.8-flash-low"

        async def generate_structured(self, **kwargs: Any) -> LLMGenerationResult:
            del kwargs
            return LLMGenerationResult(
                payload={"issues": []},
                prompt_tokens=10,
                output_tokens=5,
                model_id="gemini-3.8-flash-low",
            )

        async def stream_structured(self, **kwargs: Any) -> AsyncIterator[str]:
            del kwargs
            yield "{}"

    pending_out = await execute_tier3_pedagogical_judge(
        _MalformedScoreLLM(),  # type: ignore[arg-type]
        proposal,
    )
    assert pending_out.judge_status == "REVIEW_PENDING"
    assert pending_out.judge_skipped is True
    assert pending_out.pedagogical_score is None

    # 3. PASSED
    class _PassLLM:
        model_identifier = "gemini-3.8-flash-low"

        async def generate_structured(self, **kwargs: Any) -> LLMGenerationResult:
            del kwargs
            return LLMGenerationResult(
                payload={"score": 84, "overall_status": "PASS", "issues": []},
                prompt_tokens=10,
                output_tokens=5,
                model_id="gemini-3.8-flash-low",
            )

        async def stream_structured(self, **kwargs: Any) -> AsyncIterator[str]:
            del kwargs
            yield "{}"

    passed_out = await execute_tier3_pedagogical_judge(_PassLLM(), proposal)  # type: ignore[arg-type]
    assert passed_out.judge_status == "PASSED"
    assert passed_out.judge_skipped is False
    assert passed_out.pedagogical_score == 84.0

    # 4. NEEDS_REVIEW
    class _FailLLM:
        model_identifier = "gemini-3.8-flash-low"

        async def generate_structured(self, **kwargs: Any) -> LLMGenerationResult:
            del kwargs
            return LLMGenerationResult(
                payload={
                    "score": 45,
                    "overall_status": "FAIL",
                    "issues": [
                        {
                            "severity": "CRITICAL",
                            "category": "PREREQUISITE_ORDER",
                            "message": "PROJECT trước THEORY",
                            "evidence": "T1 là PROJECT",
                            "task_ref": "T1",
                        }
                    ],
                },
                prompt_tokens=10,
                output_tokens=5,
                model_id="gemini-3.8-flash-low",
            )

        async def stream_structured(self, **kwargs: Any) -> AsyncIterator[str]:
            del kwargs
            yield "{}"

    needs_review_out = await execute_tier3_pedagogical_judge(_FailLLM(), proposal)  # type: ignore[arg-type]
    assert needs_review_out.judge_status == "NEEDS_REVIEW"
    assert needs_review_out.judge_skipped is False
    assert needs_review_out.pedagogical_score == 45.0


@pytest.mark.asyncio
async def test_eval_runner_supports_parallel_critics_and_judge_mode() -> None:
    """eval_runner.run_planning_eval_suite(parallel_critics_and_judge=True) passes totals self-check."""
    from tests.ai_evals.eval_runner import run_planning_eval_suite

    report = await run_planning_eval_suite(
        trials_per_goal=1,
        live=False,
        concurrency=2,
        include_weekly=False,
        parallel_critics_and_judge=True,
        judge_timeout_seconds=8.0,
    )
    assert report["dataset_size"] == 18
    assert report["passed_runs"] == 18
    assert report["judge_passed_count"] == 18
    assert report["judge_review_pending_count"] == 0
