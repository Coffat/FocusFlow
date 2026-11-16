"""Tests covering Phases 1–3 hardening requirements (T1.4, T2.1–T2.4, T2.4 DB audit helper)."""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from scripts.audit_clarification_dimensions import audit_clarification_json_rows
from src.evaluation.application.dtos.intelligence import (
    GenerateWeeklyReviewRequestDTO,
    SubmitProofRequestDTO,
)
from src.evaluation.application.use_cases.intelligence import (
    GenerateMilestoneProofUseCase,
    GenerateWeeklyReviewUseCase,
    SubmitMilestoneProofUseCase,
)
from src.evaluation.domain.models.intelligence import MilestoneProof, WeeklyReview
from src.planning.application.dtos.planning_dtos import (
    ClarificationQuestionsLLMOutput,
    CriticQualityLLMOutput,
    DiagnosticDimension,
    PedagogicalJudgeLLMOutput,
)
from src.planning.application.services.validation_gate import ProposalValidationGateOrchestrator
from src.planning.application.use_cases.clarification_use_cases import (
    normalize_choice_options_with_other_last,
)
from src.planning.application.use_cases.proposal_generation_use_cases import (
    resolve_task_resources_from_tool_results,
)
from src.planning.domain.models.knowledge_concept import (
    LearningResource,
    compute_deterministic_resource_id,
)


class _QuotaDouble:
    def __init__(self) -> None:
        self.reserved: list[str] = []
        self.committed: int = 0
        self.released: list[str] = []

    async def reserve_quota(
        self,
        user_id: UUID,
        operation_type: str = "AI_CALL",
        cost: int = 1,
        ttl_seconds: int = 120,
    ) -> UUID:
        del user_id, cost, ttl_seconds
        self.reserved.append(operation_type)
        return uuid4()

    async def commit_reservation(
        self,
        reservation_id: UUID,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        model_name: str = "",
    ) -> None:
        del reservation_id, prompt_tokens, completion_tokens, model_name
        self.committed += 1

    async def release_reservation(self, reservation_id: UUID, reason: str = "RELEASED") -> None:
        del reservation_id
        self.released.append(reason)


class _EvalRepoDouble:
    def __init__(self) -> None:
        self.proofs: dict[UUID, MilestoneProof] = {}
        self.saved_model_used: str | None = None

    async def create_proof(
        self, *, milestone_id: UUID, user_id: UUID, questions: list[dict[str, Any]]
    ) -> MilestoneProof:
        p = MilestoneProof(
            milestone_id=milestone_id,
            user_id=user_id,
            status="PENDING",
            questions=questions,
        )
        self.proofs[p.id] = p
        return p

    async def get_owned_proof(self, proof_id: UUID, user_id: UUID) -> MilestoneProof | None:
        p = self.proofs.get(proof_id)
        if p and p.user_id == user_id:
            return p
        return None

    async def save_proof(self, proof: MilestoneProof) -> None:
        self.proofs[proof.id] = proof

    async def create_weekly_review(
        self,
        *,
        roadmap_id: UUID,
        user_id: UUID,
        period_start: date,
        period_end: date,
        reflection: dict[str, Any],
    ) -> WeeklyReview:
        return WeeklyReview(
            roadmap_id=roadmap_id,
            user_id=user_id,
            period_start=period_start,
            period_end=period_end,
            quantitative_summary={"completed_sessions": 5},
            strengths_feedback="Hoàn thành 5 phiên học.",
            bottlenecks_feedback="Chú ý ôn lại phần lý thuyết.",
            action_recommendations="Làm thêm bài tập.",
            user_reflection_payload=reflection,
        )

    async def save_weekly_review(self, review: WeeklyReview, *, model_used: str = "") -> None:
        del review
        self.saved_model_used = model_used


class _OwnershipDouble:
    def __init__(self, user_id: UUID) -> None:
        self._user_id = user_id

    async def get_milestone(self, milestone_id: UUID) -> Any:
        from types import SimpleNamespace

        return SimpleNamespace(id=milestone_id, user_id=self._user_id, title="FastAPI Async")

    async def roadmap_belongs_to(self, roadmap_id: UUID, user_id: UUID) -> bool:
        del roadmap_id
        return user_id == self._user_id


class _UoWDouble:
    async def commit(self) -> None:
        return None


@pytest.mark.asyncio
async def test_intelligence_use_cases_route_through_execution_manager_and_handle_grader_failure() -> (
    None
):
    """T1.4 & T0.3(E5): Prove generation/grading & Weekly Review use AIExecutionManager + quota & fail-safe fallback."""
    user_id = uuid4()
    milestone_id = uuid4()
    roadmap_id = uuid4()
    repo = _EvalRepoDouble()
    ownership = _OwnershipDouble(user_id)
    uow = _UoWDouble()
    quota = _QuotaDouble()

    class _RecordingLLM:
        def __init__(self) -> None:
            self.calls: list[str | None] = []
            self.fail_next = False

        async def generate_structured(self, **kwargs: Any) -> tuple[dict[str, Any], int, int]:
            self.calls.append(kwargs.get("thinking_level"))
            if self.fail_next:
                raise PermissionError("403 Forbidden")
            schema = kwargs.get("response_schema")
            name = getattr(schema, "__name__", "")
            if name == "ProveQuestionsLLMOutput":
                return (
                    {
                        "questions": [
                            {"id": "q1", "prompt": "Giải thích FastAPI async event loop?"},
                            {"id": "q2", "prompt": "Nêu một lỗi block loop hay gặp?"},
                            {"id": "q3", "prompt": "Cách xử lý concurrency an toàn?"},
                        ]
                    },
                    20,
                    10,
                )
            return (
                {
                    "strengths_feedback": "Hoàn thành 5 phiên học chất lượng.",
                    "bottlenecks_feedback": "Cần thêm 5 phút tổng kết cuối buổi.",
                    "action_recommendations": "Duy trì 5 phiên đều đặn.",
                },
                30,
                15,
            )

        async def stream_structured(self, **kwargs: Any) -> Any:
            del kwargs
            yield "{}"

    llm = _RecordingLLM()
    gen_uc = GenerateMilestoneProofUseCase(
        repository=repo,  # type: ignore[arg-type]
        ownership=ownership,  # type: ignore[arg-type]
        uow=uow,  # type: ignore[arg-type]
        llm_provider=llm,  # type: ignore[arg-type]
        quota_port=quota,
    )
    proof_dto = await gen_uc.execute(user_id, milestone_id)
    assert len(proof_dto.questions) == 3
    assert quota.committed == 1
    assert llm.calls == ["MEDIUM"]

    # E5: Prove grader fails with non-retryable 403 -> releases quota, does NOT retry, falls back safely
    llm.fail_next = True
    submit_uc = SubmitMilestoneProofUseCase(
        repository=repo,  # type: ignore[arg-type]
        uow=uow,  # type: ignore[arg-type]
        llm_provider=llm,  # type: ignore[arg-type]
        quota_port=quota,
    )
    graded = await submit_uc.execute(
        user_id,
        milestone_id,
        proof_dto.proof_id,
        SubmitProofRequestDTO(
            answers=[{"id": "q1", "answer": "Tránh I/O đồng bộ."}], confidence=0.8
        ),
    )
    assert graded.status in ("PASSED", "NEEDS_REVIEW")
    assert len(quota.released) == 1
    assert len(llm.calls) == 2

    class _ExecMetricsDouble:
        async def get_roadmap_period_metrics(self, **kwargs: Any) -> Any:
            del kwargs
            from src.execution.public_api import WeeklyExecutionMetricsDTO

            return WeeklyExecutionMetricsDTO(
                completed_minutes=225,
                planned_minutes=300,
                completed_sessions_count=5,
                completed_tasks_count=3,
                planned_tasks_count=4,
                overdue_tasks_count=0,
                adherence_rate_pct=75.0,
            )

    llm.fail_next = False
    weekly_uc = GenerateWeeklyReviewUseCase(
        repository=repo,  # type: ignore[arg-type]
        ownership=ownership,  # type: ignore[arg-type]
        uow=uow,  # type: ignore[arg-type]
        execution_metrics_port=_ExecMetricsDouble(),
        llm_provider=llm,  # type: ignore[arg-type]
        quota_port=quota,
    )
    weekly = await weekly_uc.execute(
        user_id,
        GenerateWeeklyReviewRequestDTO(
            roadmap_id=roadmap_id,
            period_start=date(2026, 11, 2),
            period_end=date(2026, 11, 9),
            reflection={"note": "Ổn"},
        ),
    )
    assert "5 phiên học" in weekly.strengths_feedback
    assert quota.committed == 2
    assert llm.calls == ["MEDIUM", "MEDIUM", "MEDIUM"]


@pytest.mark.asyncio
async def test_judge_skipped_and_review_pending_status_contracts() -> None:
    """T1.4: Judge disabled returns (judge_skipped=True, 'SKIPPED'); missing score returns 'REVIEW_PENDING'."""
    orch_disabled = ProposalValidationGateOrchestrator(llm_provider=None, enable_tier3_judge=False)
    skipped, score, _, status = await orch_disabled.run_tier3_pedagogical_judge({"tasks": []})
    assert skipped is True
    assert score is None
    assert status == "SKIPPED"

    class _BrokenJudgeLLM:
        async def generate_structured(self, **kwargs: Any) -> tuple[dict[str, Any], int, int]:
            del kwargs
            return {"issues": []}, 5, 5  # Missing required `score`

        async def stream_structured(self, **kwargs: Any) -> Any:
            del kwargs
            yield "{}"

    orch_bad = ProposalValidationGateOrchestrator(
        llm_provider=_BrokenJudgeLLM(),  # type: ignore[arg-type]
        enable_tier3_judge=True,
    )
    skipped2, score2, warnings2, status2 = await orch_bad.run_tier3_pedagogical_judge({"tasks": []})
    assert skipped2 is True
    assert score2 is None
    assert status2 == "REVIEW_PENDING"
    assert warnings2


def test_llm_output_schemas_resource_grounding_clarification_choice_and_audit() -> None:
    """T2.1–T2.4: Judge/Critic schemas, resource_id grounding, clarification bounds, and read-only audit."""
    # T2.1: Judge derives PASS/FAIL deterministically
    j_pass = PedagogicalJudgeLLMOutput(score=85, issues=[])
    assert j_pass.derive_status() == "PASS"
    j_fail = PedagogicalJudgeLLMOutput.model_validate(
        {
            "score": 85,
            "issues": [{"severity": "CRITICAL", "category": "SEQUENCE", "message": "Sai thứ tự"}],
        }
    )
    assert j_fail.derive_status() == "FAIL"
    CriticQualityLLMOutput.model_validate({"status": "PASS", "score": 95, "issues": []})
    with pytest.raises(ValidationError):
        PedagogicalJudgeLLMOutput.model_validate({"issues": []})

    # T2.2: Server resolves curated resource_id and strips unknown/hallucinated IDs
    curated = LearningResource(
        resource_id=compute_deterministic_resource_id(
            url="https://fastapi.tiangolo.com/", title="FastAPI Docs"
        ),
        title="FastAPI Docs",
        url="https://fastapi.tiangolo.com/",
        type="DOCS",
        description="Official FastAPI guide",
    )
    grounded = resolve_task_resources_from_tool_results(
        {
            "tasks": [
                {
                    "task_id": "T1",
                    "resource_ids": [curated.resource_id, "res-invented-999"],
                }
            ]
        },
        (curated,),
    )
    res_list = grounded["tasks"][0]["learning_resources"]
    assert len(res_list) == 1
    assert res_list[0]["url"] == "https://fastapi.tiangolo.com/"

    # T2.3: ClarificationQuestionsLLMOutput excludes server fields & enforces choice options 3..5 + 'Khác' last
    schema_props = ClarificationQuestionsLLMOutput.model_json_schema()["properties"]
    for forbidden_prop in ("session_id", "round", "status", "quota"):
        assert forbidden_prop not in schema_props
    opts = normalize_choice_options_with_other_last(
        ["A", "Khác (mô tả)", "B", "C", "D", "E"],
        "single_choice",
    )
    assert 3 <= len(opts) <= 5
    assert opts[-1].startswith("Khác")

    # T2.4: Read-only audit counts canonical vs legacy vs unknown without mutation
    audit_report = audit_clarification_json_rows(
        goal_contexts=[
            {
                "answered_dimensions": [
                    DiagnosticDimension.TARGET_OUTCOME.value,
                    "PRIOR_EXPOSURE",
                ],
                "missing_dimensions": ["WEIRD_DIM"],
            },
            "not-a-dict",  # type: ignore[list-item]
        ],
        workflow_snapshots=[
            {"questions": [{"diagnostic_dimension": "TIME_BUDGET"}]},
        ],
    )
    assert (
        audit_report["goals_clarification_context"]["canonical_counts"][
            DiagnosticDimension.TARGET_OUTCOME.value
        ]
        == 1
    )
    assert audit_report["goals_clarification_context"]["legacy_alias_counts"]["PRIOR_EXPOSURE"] == 1
    assert audit_report["goals_clarification_context"]["unknown_counts"]["WEIRD_DIM"] == 1
    assert audit_report["goals_clarification_context"]["is_clean"] is False
    assert audit_report["goals_clarification_context"]["invalid_container_rows"] == 1
    assert audit_report["workflow_runs_context_snapshot"]["legacy_alias_counts"]["TIME_BUDGET"] == 1
