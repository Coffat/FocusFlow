import asyncio
from datetime import UTC, datetime
from typing import Any

import pytest
from uuid6 import uuid7

from src.planning.application.services.learning_quality import (
    FeasibilityStatus,
    assess_schedule_feasibility,
    has_operational_quality_review_failure,
    run_dual_quality_critics,
    validate_adaptive_milestones,
    validate_task_coverage,
)
from src.planning.domain.models.milestone import Milestone, validate_milestone_sequence


def test_adaptive_milestones_accept_one_and_more_than_seven() -> None:
    now = datetime.now(UTC)
    roadmap_id = uuid7()
    one = [Milestone(roadmap_id=roadmap_id, title="M1", created_at=now, updated_at=now)]
    many = [
        Milestone(
            roadmap_id=roadmap_id,
            sequence_order=index,
            title=f"M{index}",
            created_at=now,
            updated_at=now,
        )
        for index in range(1, 13)
    ]
    validate_milestone_sequence(one, enforce_ai_bounds=True)
    validate_milestone_sequence(many, enforce_ai_bounds=True)


def test_adaptive_milestone_gate_requires_quality_fields_not_fixed_count() -> None:
    valid = [
        {
            "sequence_order": index,
            "title": f"Chặng {index}",
            "learning_outcomes": [f"M{index}-O1"],
            "completion_criteria": "Hoàn thành bài thực hành đạt yêu cầu.",
            "estimated_effort_minutes": 120,
        }
        for index in range(1, 10)
    ]
    assert validate_adaptive_milestones(valid) == []
    codes = {
        v.rule_code for v in validate_adaptive_milestones([{**valid[0], "learning_outcomes": []}])
    }
    assert "MISSING_LEARNING_OUTCOMES" in codes


def test_task_coverage_detects_missing_outcome_and_concept() -> None:
    milestone = Milestone(
        roadmap_id=uuid7(),
        title="Python nền tảng",
        learning_outcomes=("Viết chương trình", "Kiểm thử chương trình"),
        required_concepts=("pytest",),
    )
    tasks = [
        {
            "milestone_id": str(milestone.id),
            "title": "Viết chương trình đầu tiên",
            "learning_objective": "Viết chương trình CLI.",
            "completion_criteria": "CLI chạy đúng.",
            "covered_outcome_ids": ["M1-O1"],
            "concept_ids": ["python"],
            "estimated_minutes": 60,
        }
    ]
    codes = {v.rule_code for v in validate_task_coverage(tasks, [milestone])}
    assert codes == {"MILESTONE_OUTCOMES_NOT_COVERED", "REQUIRED_CONCEPTS_NOT_COVERED"}


def test_feasibility_boundaries() -> None:
    tasks_24 = [
        {"estimated_minutes": 24, "scheduled_date": "2026-11-15"},
        {"estimated_minutes": 76, "scheduled_date": None},
    ]
    tasks_25 = [
        {"estimated_minutes": 25, "scheduled_date": "2026-11-15"},
        {"estimated_minutes": 75, "scheduled_date": None},
    ]
    tasks_100 = [{"estimated_minutes": 100, "scheduled_date": "2026-11-15"}]
    assert (
        assess_schedule_feasibility(tasks_24, available_minutes=24).status
        is FeasibilityStatus.INFEASIBLE
    )
    assert (
        assess_schedule_feasibility(tasks_25, available_minutes=25).status
        is FeasibilityStatus.PARTIAL
    )
    assert (
        assess_schedule_feasibility(tasks_100, available_minutes=100).status
        is FeasibilityStatus.FEASIBLE
    )


def test_master_python_beginner_blueprint_covers_full_scope_without_count_cap() -> None:
    concepts = (
        "syntax",
        "data-structures",
        "oop",
        "typing",
        "standard-library",
        "testing",
        "packaging",
        "concurrency",
        "database",
        "web",
        "capstone",
    )
    blueprint = [
        {
            "sequence_order": index,
            "title": concept,
            "learning_outcomes": [f"M{index}-O1"],
            "completion_criteria": f"Hoàn thành sản phẩm kiểm chứng {concept}",
            "estimated_effort_minutes": 180,
            "required_concepts": [concept],
        }
        for index, concept in enumerate(concepts, start=1)
    ]
    assert len(blueprint) > 7
    assert validate_adaptive_milestones(blueprint) == []
    assert {item["required_concepts"][0] for item in blueprint} == set(concepts)


@pytest.mark.asyncio
async def test_dual_critics_run_in_parallel_at_medium_without_unneeded_arbiter() -> None:
    class AgreeingCriticProvider:
        active_calls = 0
        max_active_calls = 0
        thinking_levels: list[str | None] = []

        async def generate_structured(self, **kwargs: Any) -> tuple[dict[str, Any], int, int]:
            self.thinking_levels.append(kwargs.get("thinking_level"))
            self.active_calls += 1
            self.max_active_calls = max(self.max_active_calls, self.active_calls)
            await asyncio.sleep(0)
            self.active_calls -= 1
            return {"status": "PASS", "issues": []}, 10, 5

    provider = AgreeingCriticProvider()
    violations, reports, prompt_tokens, completion_tokens = await run_dual_quality_critics(  # type: ignore[arg-type]
        provider,
        stage="MILESTONE_PLANNING",
        payload={"milestones": []},
        context="test",
    )

    assert violations == []
    assert provider.max_active_calls == 2
    assert provider.thinking_levels == ["LOW", "LOW"]
    assert len(reports) == 2
    assert (prompt_tokens, completion_tokens) == (20, 10)


@pytest.mark.asyncio
async def test_dual_critics_escalate_to_high_arbiter_only_on_disagreement() -> None:
    class FakeCriticProvider:
        active_calls = 0
        max_active_calls = 0
        thinking_levels: list[str | None] = []

        async def generate_structured(self, **kwargs: Any) -> tuple[dict[str, Any], int, int]:
            self.thinking_levels.append(kwargs.get("thinking_level"))
            self.active_calls += 1
            self.max_active_calls = max(self.max_active_calls, self.active_calls)
            await asyncio.sleep(0)
            self.active_calls -= 1
            prompt = str(kwargs.get("user_prompt") or kwargs.get("prompt") or "")
            if "[QUALITY_ARBITER]" in prompt:
                return {"status": "PASS", "issues": []}, 10, 5
            if "COVERAGE_PREREQUISITE_CRITIC" in prompt:
                return {"status": "FAIL", "issues": []}, 10, 5
            return {"status": "PASS", "issues": []}, 10, 5

    provider = FakeCriticProvider()
    violations, reports, prompt_tokens, completion_tokens = await run_dual_quality_critics(  # type: ignore[arg-type]
        provider,
        stage="TASK_DECOMPOSITION",
        payload={"tasks": []},
        context="test",
    )
    assert provider.max_active_calls == 2
    assert provider.thinking_levels[:2] == ["LOW", "LOW"]
    assert provider.thinking_levels[2:] == ["LOW"]
    assert [report["critic"] for report in reports] == [
        "COVERAGE_PREREQUISITE_CRITIC",
        "LEARNER_FIT_ACTIONABILITY_CRITIC",
        "QUALITY_ARBITER",
    ]
    assert violations == []
    assert (prompt_tokens, completion_tokens) == (30, 15)


@pytest.mark.asyncio
async def test_operational_critic_timeout_is_not_a_content_repair_violation() -> None:
    class SlowCriticProvider:
        async def generate_structured(self, **kwargs: Any) -> tuple[dict[str, Any], int, int]:
            prompt = str(kwargs.get("user_prompt") or kwargs.get("prompt") or "")
            if "COVERAGE_PREREQUISITE_CRITIC" in prompt:
                await asyncio.sleep(0.05)
            return {"status": "PASS", "issues": []}, 10, 5

    violations, reports, _, _ = await run_dual_quality_critics(  # type: ignore[arg-type]
        SlowCriticProvider(),
        stage="MILESTONE_PLANNING",
        payload={"milestones": []},
        context="test",
        timeout_seconds=0.01,
    )

    assert [violation.rule_code for violation in violations] == ["QUALITY_CRITIC_UNAVAILABLE"]
    assert has_operational_quality_review_failure(violations)
    assert {report["status"] for report in reports} == {"PASS", "ERROR"}
