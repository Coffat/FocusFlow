"""Tests for T0.1 (18-goal eval dataset), T0.2 (offline eval metrics), and Group 4 (4.1-4.5)."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Sequence
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

from src.account.public_api import QuotaExceededError
from src.planning.domain.exceptions.planning_exceptions import ProposalValidationGateError
from src.planning.domain.services.spatio_temporal_engine import SpatioTemporalRuleEngine
from src.shared_kernel.application.llm_port import (
    LLMGenerationResult,
    LLMProviderPort,
    LLMToolDeclarationDTO,
    LLMToolExecutor,
)
from tests.ai_evals.eval_runner import (
    ERROR_TAXONOMY_CATEGORIES,
    HARD_6_GOALS_DATASET_PATH,
    _build_availability,
    _build_decomposer_inputs,
    _E2EStubLLMAdapter,
    load_18_goal_dataset,
    load_eval_dataset,
    main,
    parse_cli_args,
    run_planning_eval_suite,
    validate_eval_report_totals,
)
from tests.helpers.llm_stubs import StubLLMAdapter


class _ScriptedErrorLLM(LLMProviderPort):
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    async def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: dict[str, Any] | type[Any] | None = None,
        tools: list[Any] | None = None,
        tool_executor: Any = None,
        max_tool_calls: int = 2,
        thinking_level: str | None = None,
        timeout_seconds: float | None = None,
        tool_call_timeout_seconds: float | None = None,
    ) -> LLMGenerationResult:
        del (
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
        raise self._exc

    async def stream_structured(
        self, *, system_prompt: str, user_prompt: str
    ) -> AsyncIterator[str]:
        del system_prompt, user_prompt
        yield "{}"


class _ScriptedPayloadLLM(LLMProviderPort):
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    async def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: dict[str, Any] | type[Any] | None = None,
        tools: list[Any] | None = None,
        tool_executor: Any = None,
        max_tool_calls: int = 2,
        thinking_level: str | None = None,
        timeout_seconds: float | None = None,
        tool_call_timeout_seconds: float | None = None,
    ) -> LLMGenerationResult:
        del (
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
        return LLMGenerationResult(
            payload=self._payload,
            prompt_tokens=10,
            output_tokens=20,
            thinking_tokens=0,
            model_id="stub-scripted",
        )

    async def stream_structured(
        self, *, system_prompt: str, user_prompt: str
    ) -> AsyncIterator[str]:
        del system_prompt, user_prompt
        yield "{}"


class _LeakingInjectionStub(StubLLMAdapter):
    def __init__(self, leak_token: str) -> None:
        super().__init__()
        self._leak_token = leak_token

    async def generate_structured(
        self,
        *,
        system_prompt: str = "",
        user_prompt: str = "",
        response_schema: dict[str, Any] | type[Any] | None = None,
        tools: Any = None,
        tool_executor: Any = None,
        max_tool_calls: int = 2,
        thinking_level: str | None = None,
        timeout_seconds: float | None = None,
        tool_call_timeout_seconds: float | None = None,
    ) -> LLMGenerationResult:
        res = await super().generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_schema=response_schema,
            tools=tools,
            tool_executor=tool_executor,
            max_tool_calls=max_tool_calls,
            thinking_level=thinking_level,
            timeout_seconds=timeout_seconds,
            tool_call_timeout_seconds=tool_call_timeout_seconds,
        )
        payload = dict(res.payload)
        tasks = [dict(t) for t in payload.get("tasks", [])]
        if tasks:
            tasks[0]["title"] = f"{tasks[0].get('title', 'Task')} {self._leak_token}"
            payload["tasks"] = tasks
        return LLMGenerationResult(
            payload=payload,
            prompt_tokens=res.prompt_tokens,
            output_tokens=res.output_tokens,
            thinking_tokens=res.thinking_tokens,
            model_id=res.model_id,
            raw_tool_results=res.raw_tool_results,
        )


class _ConcurrencyTrackingStub(StubLLMAdapter):
    def __init__(self, state: dict[str, int]) -> None:
        super().__init__()
        self._state = state

    async def generate_structured(
        self,
        *,
        system_prompt: str = "",
        user_prompt: str = "",
        response_schema: dict[str, Any] | type[Any] | None = None,
        tools: Any = None,
        tool_executor: Any = None,
        max_tool_calls: int = 2,
        thinking_level: str | None = None,
        timeout_seconds: float | None = None,
        tool_call_timeout_seconds: float | None = None,
    ) -> LLMGenerationResult:
        self._state["active"] += 1
        self._state["max_seen"] = max(self._state["max_seen"], self._state["active"])
        try:
            await asyncio.sleep(0.01)
            return await super().generate_structured(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_schema=response_schema,
                tools=tools,
                tool_executor=tool_executor,
                max_tool_calls=max_tool_calls,
                thinking_level=thinking_level,
                timeout_seconds=timeout_seconds,
                tool_call_timeout_seconds=tool_call_timeout_seconds,
            )
        finally:
            self._state["active"] -= 1


class _SampleSchema(BaseModel):
    required_field: int


def _make_validation_error() -> ValidationError:
    try:
        _SampleSchema.model_validate({})
    except ValidationError as exc:
        return exc
    raise AssertionError("Expected ValidationError")


def test_18_goal_dataset_covers_domains_levels_modes_deadlines_and_injections() -> None:
    scenarios = load_18_goal_dataset()
    assert len(scenarios) == 18

    domains = {s["domain"] for s in scenarios}
    assert domains == {
        "backend",
        "dsa",
        "frontend",
        "system_design",
        "machine_learning",
        "database_devops",
    }
    levels = {s["learner_level"] for s in scenarios}
    assert levels == {"BEGINNER", "INTERMEDIATE", "ADVANCED"}
    regimes = {s["deadline_regime"] for s in scenarios}
    assert regimes == {"WIDE", "TIGHT"}
    modes = {s["planning_mode"] for s in scenarios}
    assert modes == {"MODE_A", "MODE_B"}
    injection_cases = [s for s in scenarios if s.get("is_injection_case")]
    assert len(injection_cases) == 4


@pytest.mark.asyncio
async def test_eval_runner_produces_deterministic_pii_free_json_report(tmp_path: Path) -> None:
    report_path = tmp_path / "eval-report.json"
    report = await run_planning_eval_suite(
        trials_per_goal=3,
        output_path=report_path,
        live=False,
    )

    assert report_path.exists()
    persisted = json.loads(report_path.read_text(encoding="utf-8"))
    assert persisted == report
    assert report["schema_version"] == "1.0"
    assert report["mode"] == "mock"
    assert report["dataset_size"] == 18
    assert report["trials_per_goal"] == 3
    assert report["concurrency"] == 1
    assert report["total_runs"] == 54
    assert report["passed_runs"] == 54
    assert report["failed_runs"] == 0
    assert report["pass_at_1"] == 1.0
    assert report["post_retry_recovery_rate"] == 1.0
    assert report["avg_retries"] == 0.0
    assert report["prompt_tokens_total"] > 0
    assert report["output_tokens_total"] > 0
    assert report["latency_p50_ms"] >= 0.0
    assert report["latency_p95_ms"] >= report["latency_p50_ms"]
    assert report["judge_checks"] == 18
    assert report["judge_passed_rate"] == round(15 / 18, 4)
    assert report["judge_review_pending_rate"] == round(3 / 18, 4)
    assert report["judge_needs_review_rate"] == 0.0
    assert report["judge_skipped_rate"] == 0.0
    assert report["judge_timeout_rate"] == round(3 / 18, 4)
    assert report["weekly_fallback_rate"] == round(4 / 18, 4)
    assert report["weekly_llm_success_rate"] == round(14 / 18, 4)
    assert report["weekly_llm_faithfulness_avg"] is not None
    assert report["weekly_fallback_faithfulness_avg"] is not None
    assert report["injection_isolation_rate"] == 1.0
    assert report["injection_isolation_summary"] == "4/4 valid outputs (0 excluded)"
    assert len(report["per_case_outcomes"]) == 18
    validate_eval_report_totals(report)

    serialized = json.dumps(report, ensure_ascii=False)
    for forbidden in (
        "raw_description",
        "user_prompt",
        "system_prompt",
        "api_key",
        "Ignore all previous instructions",
        "EXFILTRATE_ENV",
    ):
        assert forbidden not in serialized


@pytest.mark.asyncio
async def test_4_1_judge_status_separation_never_counts_pending_or_skipped_as_passed() -> None:
    def decomposer_factory(idx: int, _scenario: dict[str, Any]) -> LLMProviderPort:
        if idx in (0, 1):
            return _ScriptedErrorLLM(TimeoutError("Decomposer timed out"))
        return StubLLMAdapter()

    def judge_factory(idx: int, _scenario: dict[str, Any]) -> LLMProviderPort:
        if idx in (2, 3):
            return _ScriptedPayloadLLM(
                {
                    "score": 45,
                    "overall_status": "FAIL",
                    "issues": [{"severity": "CRITICAL", "category": "ORDER", "message": "Bad"}],
                }
            )
        if idx in (4, 5, 6):
            return _ScriptedErrorLLM(TimeoutError("Judge timed out"))
        return StubLLMAdapter()

    report = await run_planning_eval_suite(
        trials_per_goal=1,
        live=False,
        decomposer_provider_factory=decomposer_factory,
        judge_provider_factory=judge_factory,
    )

    # 2 skipped (no proposal), 2 NEEDS_REVIEW, 3 REVIEW_PENDING, 11 PASSED -> total 18, attempted 16
    assert report["judge_checks"] == 18
    assert report["judge_attempted_cases"] == 16
    assert report["judge_passed_count"] == 11
    assert report["judge_needs_review_count"] == 2
    assert report["judge_review_pending_count"] == 3
    assert report["judge_skipped_count"] == 2

    assert report["judge_passed_rate"] == round(11 / 18, 4)
    assert report["judge_needs_review_rate"] == round(2 / 18, 4)
    assert report["judge_review_pending_rate"] == round(3 / 18, 4)
    assert report["judge_skipped_rate"] == round(2 / 18, 4)
    assert report["judge_timeout_rate"] == round(3 / 16, 4)
    validate_eval_report_totals(report)


@pytest.mark.asyncio
async def test_4_2_injection_isolation_denominator_excludes_timeouts_and_empty_outputs() -> None:
    scenarios = load_18_goal_dataset()
    injection_ids = [s["scenario_id"] for s in scenarios if s.get("is_injection_case")]
    assert len(injection_ids) == 4

    def partial_decomposer_factory(_idx: int, scenario: dict[str, Any]) -> LLMProviderPort:
        sid = scenario["scenario_id"]
        if sid == injection_ids[0]:
            return _ScriptedErrorLLM(TimeoutError("Injection timeout before proposal"))
        if sid == injection_ids[1]:
            return _ScriptedPayloadLLM({"tasks": [], "dependencies": []})
        if sid == injection_ids[2]:
            forbidden_word = scenario["expected_invariants"]["forbidden_substrings"][0]
            return _LeakingInjectionStub(forbidden_word)
        return StubLLMAdapter()

    report_partial = await run_planning_eval_suite(
        trials_per_goal=1,
        live=False,
        decomposer_provider_factory=partial_decomposer_factory,
    )
    assert report_partial["injection_cases"] == 4
    assert report_partial["injection_valid_output_cases"] == 2
    assert report_partial["injection_excluded_cases"] == 2
    assert report_partial["injection_isolated_count"] == 1
    assert report_partial["injection_isolation_rate"] == 0.5
    assert report_partial["injection_isolation_summary"] == "1/2 valid outputs (2 excluded)"
    validate_eval_report_totals(report_partial)

    def all_excluded_factory(_idx: int, scenario: dict[str, Any]) -> LLMProviderPort:
        if scenario.get("is_injection_case"):
            return _ScriptedErrorLLM(TimeoutError("All injection timeouts"))
        return StubLLMAdapter()

    report_none = await run_planning_eval_suite(
        trials_per_goal=1,
        live=False,
        decomposer_provider_factory=all_excluded_factory,
    )
    assert report_none["injection_cases"] == 4
    assert report_none["injection_valid_output_cases"] == 0
    assert report_none["injection_excluded_cases"] == 4
    assert report_none["injection_isolated_count"] == 0
    assert report_none["injection_isolation_rate"] is None
    assert report_none["injection_isolation_summary"] == "0/0 valid outputs (4 excluded)"
    validate_eval_report_totals(report_none)


@pytest.mark.asyncio
async def test_4_3_weekly_faithfulness_separates_llm_vs_deterministic_fallback() -> None:
    report_all_fallback = await run_planning_eval_suite(
        trials_per_goal=1,
        live=False,
        weekly_provider_factory=lambda _idx, _s: _ScriptedErrorLLM(TimeoutError("Weekly timeout")),
    )
    assert report_all_fallback["weekly_checks"] == 18
    assert report_all_fallback["weekly_llm_success_count"] == 0
    assert report_all_fallback["weekly_fallbacks"] == 18
    assert report_all_fallback["weekly_llm_success_rate"] == 0.0
    assert report_all_fallback["weekly_fallback_rate"] == 1.0
    assert report_all_fallback["weekly_llm_faithfulness_avg"] is None
    assert report_all_fallback["weekly_fallback_faithfulness_avg"] == 1.0
    validate_eval_report_totals(report_all_fallback)

    def mixed_weekly_factory(idx: int, _scenario: dict[str, Any]) -> LLMProviderPort:
        if idx < 6:
            return _ScriptedErrorLLM(TimeoutError("Weekly timeout"))
        # Return ungrounded numbers (999) so LLM raw faithfulness < 1.0
        return _ScriptedPayloadLLM(
            {
                "strengths_feedback": "Bạn đã học 999 giờ và vượt 888 bài kiểm tra.",
                "bottlenecks_feedback": "Còn 777 nhiệm vụ chưa xong.",
                "action_recommendations": "Thực hiện 666 phiên Prove Mode.",
            }
        )

    report_mixed = await run_planning_eval_suite(
        trials_per_goal=1,
        live=False,
        weekly_provider_factory=mixed_weekly_factory,
    )
    assert report_mixed["weekly_llm_success_count"] == 12
    assert report_mixed["weekly_fallbacks"] == 6
    assert report_mixed["weekly_llm_success_rate"] == round(12 / 18, 4)
    assert report_mixed["weekly_fallback_rate"] == round(6 / 18, 4)
    assert report_mixed["weekly_llm_faithfulness_avg"] == 0.0
    assert report_mixed["weekly_fallback_faithfulness_avg"] == 1.0
    validate_eval_report_totals(report_mixed)


@pytest.mark.asyncio
async def test_4_4_error_breakdown_taxonomy_and_self_check_totals() -> None:
    def decomposer_factory(idx: int, _s: dict[str, Any]) -> LLMProviderPort:
        mapping: dict[int, Exception] = {
            0: _make_validation_error(),
            1: TimeoutError("Decomposer timeout"),
            2: ConnectionError("503 Service Unavailable"),
            3: ProposalValidationGateError("Gate failed"),
            4: QuotaExceededError("Quota exhausted"),
            5: RuntimeError("Unexpected decomposer crash"),
        }
        if idx in mapping:
            return _ScriptedErrorLLM(mapping[idx])
        return StubLLMAdapter()

    def judge_factory(idx: int, _s: dict[str, Any]) -> LLMProviderPort:
        if idx == 6:
            return _ScriptedErrorLLM(TimeoutError("Judge timeout"))
        if idx == 7:
            return _ScriptedErrorLLM(ConnectionError("502 Bad Gateway"))
        if idx == 8:
            return _ScriptedPayloadLLM({"unexpected": "missing score"})
        return StubLLMAdapter()

    def weekly_factory(idx: int, _s: dict[str, Any]) -> LLMProviderPort:
        if idx == 9:
            return _ScriptedErrorLLM(TimeoutError("Weekly timeout"))
        if idx == 10:
            return _ScriptedErrorLLM(_make_validation_error())
        if idx == 11:
            return _ScriptedErrorLLM(RuntimeError("500 Stream interrupted"))
        return StubLLMAdapter()

    report = await run_planning_eval_suite(
        trials_per_goal=1,
        live=False,
        decomposer_provider_factory=decomposer_factory,
        judge_provider_factory=judge_factory,
        weekly_provider_factory=weekly_factory,
    )

    assert report["total_runs"] == 18
    assert report["passed_runs"] == 12
    assert report["failed_runs"] == 6

    eb = report["error_breakdown"]
    assert set(eb["decomposer"].keys()) == set(ERROR_TAXONOMY_CATEGORIES)
    assert eb["decomposer"] == {
        "SCHEMA_MISMATCH": 1,
        "TIMEOUT": 1,
        "GATEWAY_ERROR": 1,
        "VALIDATION_GATE": 1,
        "QUOTA": 1,
        "OTHER": 1,
    }
    assert eb["judge"] == {
        "SCHEMA_MISMATCH": 1,
        "TIMEOUT": 1,
        "GATEWAY_ERROR": 1,
        "VALIDATION_GATE": 0,
        "QUOTA": 0,
        "OTHER": 0,
    }
    assert eb["weekly"] == {
        "SCHEMA_MISMATCH": 1,
        "TIMEOUT": 1,
        "GATEWAY_ERROR": 1,
        "VALIDATION_GATE": 0,
        "QUOTA": 0,
        "OTHER": 0,
    }
    assert eb["total"] == {
        "SCHEMA_MISMATCH": 3,
        "TIMEOUT": 3,
        "GATEWAY_ERROR": 3,
        "VALIDATION_GATE": 1,
        "QUOTA": 1,
        "OTHER": 1,
    }
    assert report["schema_check_calls"] == 48
    assert report["post_repair_schema_mismatch_count"] == 3
    assert report["post_repair_schema_mismatch_rate"] == round(3 / 48, 4)
    validate_eval_report_totals(report)

    # Verify self-check fails if any summary total disagrees with details
    broken = json.loads(json.dumps(report))
    broken["error_breakdown"]["decomposer"]["TIMEOUT"] += 1
    with pytest.raises(AssertionError):
        validate_eval_report_totals(broken)


@pytest.mark.asyncio
async def test_4_5_concurrency_1_and_4_produce_consistent_grouped_results() -> None:
    cli_args = parse_cli_args(["--concurrency", "4", "--trials-per-goal", "1", "--mock"])
    assert cli_args.concurrency == 4
    assert cli_args.trials_per_goal == 1
    assert cli_args.live is False

    seq_state = {"active": 0, "max_seen": 0}
    par_state = {"active": 0, "max_seen": 0}

    seq_report = await run_planning_eval_suite(
        trials_per_goal=1,
        live=False,
        concurrency=1,
        decomposer_provider_factory=lambda _i, _s: _ConcurrencyTrackingStub(seq_state),
    )
    par_report = await run_planning_eval_suite(
        trials_per_goal=1,
        live=False,
        concurrency=4,
        decomposer_provider_factory=lambda _i, _s: _ConcurrencyTrackingStub(par_state),
    )

    assert seq_report["concurrency"] == 1
    assert par_report["concurrency"] == 4
    assert seq_state["max_seen"] == 1
    assert 2 <= par_state["max_seen"] <= 4

    assert [o["case_id"] for o in seq_report["per_case_outcomes"]] == [
        o["case_id"] for o in par_report["per_case_outcomes"]
    ]
    for metric_key in (
        "total_runs",
        "passed_runs",
        "failed_runs",
        "pass_at_1",
        "post_retry_recovery_rate",
        "judge_passed_rate",
        "judge_review_pending_rate",
        "judge_timeout_rate",
        "weekly_fallback_rate",
        "weekly_llm_success_rate",
        "weekly_llm_faithfulness_avg",
        "weekly_fallback_faithfulness_avg",
        "injection_isolation_rate",
        "injection_isolation_summary",
        "error_breakdown",
    ):
        assert seq_report[metric_key] == par_report[metric_key]


@pytest.mark.asyncio
async def test_include_weekly_false_skips_weekly_review_cleanly() -> None:
    report = await run_planning_eval_suite(
        trials_per_goal=1,
        live=False,
        include_weekly=False,
    )
    assert report["weekly_checks"] == 0
    assert report["weekly_llm_success_count"] == 0
    assert report["weekly_fallbacks"] == 0
    assert all(o["weekly_source"] == "skipped" for o in report["per_case_outcomes"])
    validate_eval_report_totals(report)


@pytest.mark.asyncio
async def test_live_mode_defaults_to_parallel_critics_and_judge() -> None:
    cli_args = parse_cli_args(["--live", "--trials-per-goal", "1"])
    assert cli_args.live is True
    assert cli_args.parallel_critics_judge is None

    report = await run_planning_eval_suite(
        trials_per_goal=1,
        live=True,
        include_weekly=False,
        decomposer_provider_factory=lambda _i, _s: StubLLMAdapter(),
    )
    assert report["mode"] == "live"
    assert report["passed_runs"] == 18
    assert report["judge_passed_count"] == 18
    # 18 * (1 decomposer + 2 parallel critics + 1 parallel judge) = 72 calls
    assert report["schema_check_calls"] == 72
    assert report["post_repair_schema_mismatch_count"] == 0
    assert report["post_repair_schema_mismatch_rate"] == 0.0
    assert set(report["stage_latency_stats"].keys()) == {
        "decomposer",
        "critics_judge_parallel",
        "weekly",
    }
    assert report["stage_latency_stats"]["decomposer"]["count"] == 18
    assert report["stage_latency_stats"]["critics_judge_parallel"]["count"] == 18
    assert report["stage_latency_stats"]["weekly"]["count"] == 0
    validate_eval_report_totals(report)


@pytest.mark.asyncio
async def test_eval_runner_accumulates_weekly_thinking_tokens_and_error_rates() -> None:
    """Verify WeeklyReview thinking_tokens are included in totals and error_category_rates/stage_latency_stats match."""

    class _ThinkingWeeklyLLM(StubLLMAdapter):
        async def generate_structured(
            self,
            *,
            system_prompt: str = "",
            user_prompt: str = "",
            response_schema: Any = None,
            tools: Any = None,
            tool_executor: Any = None,
            max_tool_calls: int = 2,
            thinking_level: str | None = None,
            timeout_seconds: float | None = None,
            tool_call_timeout_seconds: float | None = None,
        ) -> LLMGenerationResult:
            res = await super().generate_structured(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_schema=response_schema,
                tools=tools,
                tool_executor=tool_executor,
                max_tool_calls=max_tool_calls,
                thinking_level=thinking_level,
                timeout_seconds=timeout_seconds,
                tool_call_timeout_seconds=tool_call_timeout_seconds,
            )
            return LLMGenerationResult(
                payload=res.payload,
                prompt_tokens=111,
                output_tokens=77,
                thinking_tokens=33,
                model_id="gemini-3.8-flash-low",
            )

    def weekly_factory(idx: int, _s: dict[str, Any]) -> LLMProviderPort:
        if idx == 0:
            return _ScriptedErrorLLM(TimeoutError("Weekly timeout"))
        return _ThinkingWeeklyLLM()

    report = await run_planning_eval_suite(
        trials_per_goal=1,
        live=False,
        include_weekly=True,
        weekly_provider_factory=weekly_factory,
    )
    # 17 weekly LLM successes * 33 thinking_tokens = 561
    assert report["thinking_tokens_total"] >= 17 * 33
    assert report["per_case_outcomes"][0]["weekly_thinking_tokens"] == 0
    assert report["per_case_outcomes"][1]["weekly_thinking_tokens"] == 33
    assert report["per_case_outcomes"][1]["weekly_output_tokens"] == 77
    assert report["per_case_outcomes"][1]["weekly_prompt_tokens"] == 111
    assert report["stage_latency_stats"]["weekly"]["count"] == 18
    assert report["error_category_rates"]["by_stage_rate"]["weekly"]["TIMEOUT"] == round(1 / 18, 4)
    validate_eval_report_totals(report)


@pytest.mark.asyncio
async def test_pass_with_judge_verdict_metric_and_exclusions() -> None:
    """pass_with_judge_verdict is True iff attempt-1 passed AND judge_status == 'PASSED'."""

    class _RetryOnceDecomposer(StubLLMAdapter):
        def __init__(self) -> None:
            super().__init__()
            self._calls = 0

        async def generate_structured(
            self,
            *,
            system_prompt: str = "",
            user_prompt: str = "",
            response_schema: Any = None,
            tools: Any = None,
            tool_executor: Any = None,
            max_tool_calls: int = 2,
            thinking_level: str | None = None,
            timeout_seconds: float | None = None,
            tool_call_timeout_seconds: float | None = None,
        ) -> LLMGenerationResult:
            self._calls += 1
            if self._calls == 1:
                # Fail Tier 1 on attempt 1 (empty tasks) so attempt 2 recovers with retries_used == 1
                return LLMGenerationResult(
                    payload={"tasks": [], "dependencies": []},
                    prompt_tokens=10,
                    output_tokens=10,
                    thinking_tokens=0,
                    model_id="stub-retry",
                )
            return await super().generate_structured(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_schema=response_schema,
                tools=tools,
                tool_executor=tool_executor,
                max_tool_calls=max_tool_calls,
                thinking_level=thinking_level,
                timeout_seconds=timeout_seconds,
                tool_call_timeout_seconds=tool_call_timeout_seconds,
            )

    def decomposer_factory(idx: int, _s: dict[str, Any]) -> LLMProviderPort:
        if idx == 0:
            return _ScriptedErrorLLM(TimeoutError("Decomposer timeout"))
        if idx == 1:
            return _RetryOnceDecomposer()
        return StubLLMAdapter()

    def judge_factory(idx: int, _s: dict[str, Any]) -> LLMProviderPort:
        if idx == 2:
            return _ScriptedPayloadLLM(
                {
                    "score": 45,
                    "overall_status": "FAIL",
                    "issues": [{"severity": "CRITICAL", "category": "ORDER", "message": "Bad"}],
                }
            )
        if idx == 3:
            return _ScriptedErrorLLM(TimeoutError("Judge timeout"))
        return StubLLMAdapter()

    report = await run_planning_eval_suite(
        trials_per_goal=1,
        live=False,
        include_weekly=False,
        decomposer_provider_factory=decomposer_factory,
        judge_provider_factory=judge_factory,
    )

    # idx=0 failed decomposer (SKIPPED_NO_PROPOSAL)
    # idx=1 passed after retry (attempts=2, pass_at_1=False, judge=PASSED) -> pass_with_judge_verdict=False
    # idx=2 passed attempt 1, judge=NEEDS_REVIEW -> pass_with_judge_verdict=False
    # idx=3 passed attempt 1, judge=REVIEW_PENDING -> pass_with_judge_verdict=False
    # idx=4..17 (14 cases) passed attempt 1 AND judge=PASSED -> pass_with_judge_verdict=True
    assert report["total_runs"] == 18
    assert report["passed_runs"] == 17
    assert report["pass_at_1_count"] == 16
    assert report["pass_at_1"] == round(16 / 18, 4)
    assert report["pass_with_judge_verdict_count"] == 14
    assert report["pass_with_judge_verdict"] == round(14 / 18, 4)

    outcomes = report["per_case_outcomes"]
    assert outcomes[0]["pass_with_judge_verdict"] is False
    assert outcomes[1]["passed_tier1"] is True
    assert outcomes[1]["attempts"] == 2
    assert outcomes[1]["judge_status"] == "PASSED"
    assert outcomes[1]["pass_with_judge_verdict"] is False
    assert outcomes[2]["judge_status"] == "NEEDS_REVIEW"
    assert outcomes[2]["pass_with_judge_verdict"] is False
    assert outcomes[3]["judge_status"] == "REVIEW_PENDING"
    assert outcomes[3]["pass_with_judge_verdict"] is False
    assert all(o["pass_with_judge_verdict"] is True for o in outcomes[4:])
    validate_eval_report_totals(report)

    broken = json.loads(json.dumps(report))
    broken["pass_with_judge_verdict_count"] += 1
    with pytest.raises(AssertionError):
        validate_eval_report_totals(broken)


def test_hard_planning_6_goals_dataset_schema_and_constraints() -> None:
    scenarios = load_eval_dataset(HARD_6_GOALS_DATASET_PATH)
    assert len(scenarios) == 6
    assert len({s["domain"] for s in scenarios}) == 6

    for scenario in scenarios:
        assert scenario["planning_mode"] == "MODE_B"
        avail_raw = scenario["availability"]
        assert avail_raw["mode"] == "MODE_B"
        assert len(avail_raw["availability_slots"]) >= 3
        disabled = {d.lower() for d in avail_raw["disabled_weekdays"]}
        assert len(disabled) >= 1
        slot_days = {slot["day_of_week"].lower() for slot in avail_raw["availability_slots"]}
        assert slot_days.isdisjoint(disabled)

        invariants = scenario["expected_invariants"]
        assert int(invariants["min_milestones"]) == 4
        assert float(invariants["full_scope_max_capacity_utilization"]) == 1.0
        assert invariants["task_and_outcome_conservation"] is True
        assert invariants["non_splittable_integrity"] is True
        assert int(invariants["min_tasks"]) >= 10
        assert invariants["must_pass_tier1"] is True
        assert isinstance(invariants["forbidden_substrings"], list)

        cond_constraints = scenario["conditional_constraints"]
        assert int(cond_constraints["max_milestones"]) == 6
        assert cond_constraints["enforce_hard"] is False

        soft_targets = scenario["soft_quality_targets"]
        assert soft_targets["target_utilization_band"] == [0.7, 0.9]
        assert soft_targets["require_non_equal_milestone_effort"] is True

        assert scenario["simulated_learner_scope_decision"] is None

        clar_answers = scenario.get("clarification_answers")
        assert isinstance(clar_answers, dict) and len(clar_answers) >= 5

        avail_dto = _build_availability(avail_raw)
        cap_mins = SpatioTemporalRuleEngine.calculate_available_capacity_minutes(
            avail_dto,
            start_date=date.fromisoformat(scenario["start_date"]),
            target_date=date.fromisoformat(scenario["target_date"]),
        )
        assert cap_mins >= int(invariants["min_tasks"]) * 60


@pytest.mark.asyncio
async def test_e2e_mock_mode_executes_3_stage_pipeline_and_reports_stage_latencies() -> None:
    cli_args = parse_cli_args(
        [
            "--mock",
            "--e2e",
            "--dataset",
            str(HARD_6_GOALS_DATASET_PATH),
            "--trials-per-goal",
            "1",
        ]
    )
    assert cli_args.e2e is True
    assert cli_args.live is False

    report = await run_planning_eval_suite(
        dataset_path=HARD_6_GOALS_DATASET_PATH,
        trials_per_goal=1,
        live=False,
        e2e=True,
        include_weekly=False,
    )
    assert report["mode"] == "mock"
    assert report["e2e"] is True
    assert report["dataset_size"] == 6
    assert report["total_runs"] == 6
    assert report["passed_runs"] == 6
    assert report["failed_runs"] == 0
    assert report["pass_at_1"] == 1.0
    assert report["pass_with_judge_verdict_count"] == 6
    assert report["pass_with_judge_verdict"] == 1.0
    assert report["min_tasks_met_rate"] == 1.0

    stats = report["stage_latency_stats"]
    assert set(stats.keys()) == {
        "clarifier",
        "milestone_planner",
        "decomposer",
        "critics_judge_parallel",
        "weekly",
        "e2e_total",
    }
    for stage_key in (
        "clarifier",
        "milestone_planner",
        "decomposer",
        "critics_judge_parallel",
        "e2e_total",
    ):
        assert stats[stage_key]["count"] == 6
        assert 0.0 <= stats[stage_key]["p50_ms"] <= stats[stage_key]["p95_ms"]

    for outcome in report["per_case_outcomes"]:
        assert outcome["generated_milestones_count"] == 5
        assert outcome["tasks_count"] >= 10
        assert outcome["pass_with_judge_verdict"] is True
    validate_eval_report_totals(report)


@pytest.mark.asyncio
async def test_e2e_milestone_planner_failure_records_error_breakdown_and_skips_decomposer() -> None:
    from tests.ai_evals.eval_runner import _E2EStubLLMAdapter

    def planner_factory(idx: int, _s: dict[str, Any]) -> LLMProviderPort:
        if idx == 0:
            return _ScriptedErrorLLM(TimeoutError("Milestone planner timeout"))
        if idx == 1:
            # Only 2 milestones -> violates min_milestones=5
            return _ScriptedPayloadLLM(
                {
                    "milestones": [
                        {
                            "sequence_order": 1,
                            "title": "M1",
                            "description": "",
                            "learning_outcomes": ["O1"],
                            "completion_criteria": "Done 1",
                            "estimated_effort_minutes": 120,
                        },
                        {
                            "sequence_order": 2,
                            "title": "M2",
                            "description": "",
                            "learning_outcomes": ["O2"],
                            "completion_criteria": "Done 2",
                            "estimated_effort_minutes": 120,
                        },
                    ],
                    "scope_summary": "Partial",
                    "deferred_scope": [],
                }
            )
        return _E2EStubLLMAdapter()

    report = await run_planning_eval_suite(
        dataset_path=HARD_6_GOALS_DATASET_PATH,
        trials_per_goal=1,
        live=False,
        e2e=True,
        include_weekly=False,
        milestone_planner_provider_factory=planner_factory,
    )

    assert report["total_runs"] == 6
    assert report["passed_runs"] == 4
    assert report["failed_runs"] == 2
    assert report["error_breakdown"]["milestone_planner"]["TIMEOUT"] == 1
    assert report["error_breakdown"]["milestone_planner"]["VALIDATION_GATE"] == 1
    assert sum(report["error_breakdown"]["decomposer"].values()) == 0
    assert report["stage_latency_stats"]["clarifier"]["count"] == 6
    assert report["stage_latency_stats"]["milestone_planner"]["count"] == 6
    assert report["stage_latency_stats"]["decomposer"]["count"] == 4
    assert report["stage_latency_stats"]["critics_judge_parallel"]["count"] == 4
    assert report["judge_skipped_count"] == 2
    assert report["judge_passed_count"] == 4
    assert report["pass_with_judge_verdict_count"] == 4
    assert report["pass_with_judge_verdict"] == round(4 / 6, 4)
    validate_eval_report_totals(report)


def test_cli_main_stdout_includes_pass_at_1_pass_with_judge_verdict_and_stage_p50_p95(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = main(
        [
            "--mock",
            "--e2e",
            "--dataset",
            str(HARD_6_GOALS_DATASET_PATH),
            "--trials-per-goal",
            "1",
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "pass_at_1=" in out
    assert "pass_with_judge_verdict=" in out
    assert "stage=clarifier:" in out
    assert "stage=milestone_planner:" in out
    assert "stage=decomposer:" in out
    assert "p50=" in out
    assert "p95=" in out


def test_build_decomposer_inputs_injects_precomputed_schedule_budget_and_supports_opt_out() -> None:
    scenarios = load_18_goal_dataset()
    tight_mode_b = next(
        s for s in scenarios if s["scenario_id"] == "E02_BACKEND_INTERMEDIATE_TIGHT_B"
    )
    milestones = list(tight_mode_b["milestones"])

    _, _, _, prompt_with_budget = _build_decomposer_inputs(
        tight_mode_b,
        milestones,
        effective_parallel=False,
    )
    assert "precomputed_schedule_budget:" in prompt_with_budget
    budget_line = next(
        line
        for line in prompt_with_budget.splitlines()
        if line.startswith("precomputed_schedule_budget:")
    )
    budget = json.loads(budget_line.split("precomputed_schedule_budget:", 1)[1].strip())

    expected_capacity = SpatioTemporalRuleEngine.calculate_available_capacity_minutes(
        _build_availability(tight_mode_b["availability"]),
        start_date=date.fromisoformat(tight_mode_b["start_date"]),
        target_date=date.fromisoformat(tight_mode_b["target_date"]),
    )
    expected_effort = sum(int(m["estimated_effort_minutes"]) for m in milestones)
    expected_rec_minutes = 45
    expected_max_tasks = expected_capacity // expected_rec_minutes
    expected_min_tasks = min(
        expected_max_tasks, max(len(milestones), (expected_effort + 119) // 120)
    )

    assert budget["max_available_minutes_until_target_date"] == expected_capacity
    assert budget["total_milestone_effort_minutes"] == expected_effort
    assert budget["recommended_minutes_per_task"] == expected_rec_minutes
    assert budget["recommended_task_count_range"] == {
        "min_tasks": expected_min_tasks,
        "max_tasks": expected_max_tasks,
    }
    assert (
        budget["recommended_task_count_range"]["max_tasks"] * budget["recommended_minutes_per_task"]
        <= budget["max_available_minutes_until_target_date"]
    )
    assert budget["fits_milestone_effort"] is True
    assert budget["capacity_fit_ratio"] == round(expected_capacity / expected_effort, 4)

    _, _, _, prompt_without_budget = _build_decomposer_inputs(
        tight_mode_b,
        milestones,
        effective_parallel=False,
        include_budget_context=False,
    )
    assert "precomputed_schedule_budget:" not in prompt_without_budget

    default_args = parse_cli_args([])
    assert default_args.include_budget_context is True
    ab_args = parse_cli_args(["--no-budget-context"])
    assert ab_args.include_budget_context is False


@pytest.mark.asyncio
async def test_e2e_milestone_planner_uses_server_prefetch_and_enforces_structural_invariants() -> (
    None
):
    seen_planner_calls: list[dict[str, Any]] = []

    class _RecordingPrefetchPlannerLLM(_E2EStubLLMAdapter):
        def __init__(self, *, mode: str) -> None:
            super().__init__()
            self._mode = mode

        async def generate_structured(
            self,
            *,
            system_prompt: str = "",
            user_prompt: str = "",
            response_schema: dict[str, Any] | type[Any] | None = None,
            tools: Sequence[LLMToolDeclarationDTO | dict[str, Any]] | None = None,
            tool_executor: LLMToolExecutor | None = None,
            max_tool_calls: int | None = None,
            thinking_level: str | None = None,
            timeout_seconds: float | None = None,
            tool_call_timeout_seconds: float | None = None,
        ) -> LLMGenerationResult:
            seen_planner_calls.append(
                {
                    "tools": tools,
                    "tool_executor": tool_executor,
                    "max_tool_calls": max_tool_calls,
                    "has_kb_evidence": "[KNOWLEDGE_BASE_EVIDENCE]" in user_prompt,
                }
            )
            if self._mode == "equal_effort":
                efforts = [480, 480, 480, 480]
            elif self._mode == "over_100_utilization":
                # 3960m > 100% hard capacity of H_E2E_02 (3480m)
                efforts = [900, 960, 1020, 1080]
            else:
                efforts = [360, 420, 480, 540]
            return LLMGenerationResult(
                payload={
                    "milestones": [
                        {
                            "sequence_order": i + 1,
                            "title": f"Milestone {i + 1}",
                            "description": f"Desc {i + 1}",
                            "learning_outcomes": [f"Outcome {i + 1}"],
                            "completion_criteria": f"Done {i + 1}",
                            "estimated_effort_minutes": effort,
                            "required_concepts": [],
                            "unverified_concepts": [f"topic-{i + 1}"],
                            "dependencies": [] if i == 0 else [i],
                        }
                        for i, effort in enumerate(efforts)
                    ],
                    "scope_summary": "FULL_SCOPE",
                    "deferred_scope": [],
                },
                prompt_tokens=100,
                output_tokens=100,
                thinking_tokens=0,
                model_id="gemini-3.8-flash-low",
            )

    def planner_factory(idx: int, _s: dict[str, Any]) -> LLMProviderPort:
        if idx == 0:
            return _RecordingPrefetchPlannerLLM(mode="equal_effort")
        if idx == 1:
            return _RecordingPrefetchPlannerLLM(mode="over_100_utilization")
        if idx == 2:
            return _RecordingPrefetchPlannerLLM(mode="valid_4_ms")
        return _E2EStubLLMAdapter()

    report = await run_planning_eval_suite(
        dataset_path=HARD_6_GOALS_DATASET_PATH,
        trials_per_goal=1,
        live=False,
        e2e=True,
        include_weekly=False,
        milestone_planner_provider_factory=planner_factory,
    )
    assert len(seen_planner_calls) == 3
    for call in seen_planner_calls:
        assert call["tools"] is None
        assert call["tool_executor"] is None
        assert call["max_tool_calls"] is None
        assert call["has_kb_evidence"] is True

    # idx=0 (equal effort -> Soft Quality Warning only) passes; idx=1 (>100% hard cap) fails VALIDATION_GATE
    assert report["passed_runs"] == 5
    assert report["failed_runs"] == 1
    assert report["error_breakdown"]["milestone_planner"]["VALIDATION_GATE"] == 1
    assert "structural_audit_summary" in report
    summary = report["structural_audit_summary"]
    assert summary["evaluated_cases"] == 6
    assert summary["cases_with_proposal"] == 5
    assert summary["capacity_utilization_avg"] is not None
    assert summary["effort_equal_ratio_avg"] is not None
    assert summary["linear_dependency_ratio_avg"] is not None

    idx0_audit = report["per_case_outcomes"][0]["structural_audit"]
    assert idx0_audit["structural_validity"] is True
    assert idx0_audit["scheduling_feasibility"] is True
    assert "UNIFORM_MILESTONE_EFFORT" in idx0_audit["pedagogical_quality"]["soft_quality_warnings"]

    idx1_audit = report["per_case_outcomes"][1]["structural_audit"]
    assert idx1_audit["audited_milestones_source"] == "generated_milestones_on_stage2_failure"
    assert idx1_audit["audited_milestones_count"] == 4
    assert idx1_audit["scheduling_feasibility"] is False
    assert (
        "FULL_SCOPE_CAPACITY_EXCEEDED"
        in idx1_audit["failure_reasons_by_layer"]["scheduling_feasibility"]
    )
    validate_eval_report_totals(report)


@pytest.mark.asyncio
async def test_e2e_failed_stage2_audits_generated_milestones_not_static_fixture(
    tmp_path: Path,
) -> None:
    scenarios = load_eval_dataset(HARD_6_GOALS_DATASET_PATH)[:1]
    scenario = json.loads(json.dumps(scenarios[0]))
    dataset_file = tmp_path / "single_goal_stage2_fail.jsonl"
    dataset_file.write_text(json.dumps(scenario, ensure_ascii=False) + "\n", encoding="utf-8")

    class _UnderMinMilestonesLLM(_E2EStubLLMAdapter):
        async def generate_structured(
            self,
            *,
            system_prompt: str = "",
            user_prompt: str = "",
            response_schema: dict[str, Any] | type[Any] | None = None,
            tools: Sequence[LLMToolDeclarationDTO | dict[str, Any]] | None = None,
            tool_executor: LLMToolExecutor | None = None,
            max_tool_calls: int | None = None,
            thinking_level: str | None = None,
            timeout_seconds: float | None = None,
            tool_call_timeout_seconds: float | None = None,
        ) -> LLMGenerationResult:
            del (
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
            return LLMGenerationResult(
                payload={
                    "milestones": [
                        {
                            "sequence_order": 1,
                            "title": "Only Milestone 1",
                            "description": "Desc 1",
                            "learning_outcomes": ["Outcome 1"],
                            "completion_criteria": "Done 1",
                            "estimated_effort_minutes": 300,
                            "required_concepts": [],
                            "unverified_concepts": ["c1"],
                            "dependencies": [],
                        },
                        {
                            "sequence_order": 2,
                            "title": "Only Milestone 2",
                            "description": "Desc 2",
                            "learning_outcomes": ["Outcome 2"],
                            "completion_criteria": "Done 2",
                            "estimated_effort_minutes": 420,
                            "required_concepts": [],
                            "unverified_concepts": ["c2"],
                            "dependencies": [1],
                        },
                    ],
                    "scope_summary": "FULL_SCOPE",
                    "deferred_scope": [],
                },
                prompt_tokens=80,
                output_tokens=90,
                thinking_tokens=0,
                model_id="gemini-3.8-flash-low",
            )

    report = await run_planning_eval_suite(
        dataset_path=dataset_file,
        trials_per_goal=1,
        live=False,
        e2e=True,
        include_weekly=False,
        milestone_planner_provider_factory=lambda _i, _s: _UnderMinMilestonesLLM(),
    )
    assert report["failed_runs"] == 1
    assert report["error_breakdown"]["milestone_planner"]["VALIDATION_GATE"] == 1
    case_out = report["per_case_outcomes"][0]
    assert case_out["generated_milestones_count"] == 2
    audit = case_out["structural_audit"]
    assert audit["has_proposal"] is False
    assert audit["audited_milestones_source"] == "generated_milestones_on_stage2_failure"
    assert audit["audited_milestones_count"] == 2
    assert audit["structural_validity"] is False
    assert "MIN_MILESTONES_BELOW_TARGET" in audit["failure_reasons_by_layer"]["structural_validity"]


@pytest.mark.asyncio
async def test_four_category_invariant_classification_and_three_layer_verdicts(
    tmp_path: Path,
) -> None:
    scenarios = load_eval_dataset(HARD_6_GOALS_DATASET_PATH)[:1]
    scenario = json.loads(json.dumps(scenarios[0]))
    scenario["conditional_constraints"] = {
        "max_milestones": 6,
        "max_capacity_utilization": 0.90,
        "require_non_equal_milestone_effort": True,
        "enforce_hard": False,
    }
    dataset_file = tmp_path / "four_cat.jsonl"
    dataset_file.write_text(json.dumps(scenario, ensure_ascii=False) + "\n", encoding="utf-8")

    # H_E2E_01 capacity in 21 days (4d * 60m + 2d * 90m per week => check exact cap via >85% but <=100%)
    avail_dto = _build_availability(scenario["availability"])
    cap_mins = SpatioTemporalRuleEngine.calculate_available_capacity_minutes(
        avail_dto,
        start_date=date.fromisoformat(scenario["start_date"]),
        target_date=date.fromisoformat(scenario["target_date"]),
    )
    equal_92_effort = max(120, int(cap_mins * 0.92 // 4 // 30 * 30))

    class _SoftAndCondWarningPlanner(_E2EStubLLMAdapter):
        async def generate_structured(
            self,
            *,
            system_prompt: str = "",
            user_prompt: str = "",
            response_schema: dict[str, Any] | type[Any] | None = None,
            tools: Sequence[LLMToolDeclarationDTO | dict[str, Any]] | None = None,
            tool_executor: LLMToolExecutor | None = None,
            max_tool_calls: int | None = None,
            thinking_level: str | None = None,
            timeout_seconds: float | None = None,
            tool_call_timeout_seconds: float | None = None,
        ) -> LLMGenerationResult:
            del (
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
            return LLMGenerationResult(
                payload={
                    "milestones": [
                        {
                            "sequence_order": i + 1,
                            "title": f"Milestone {i + 1}",
                            "description": f"Desc {i + 1}",
                            "learning_outcomes": [f"Outcome {i + 1}"],
                            "completion_criteria": f"Done {i + 1}",
                            "estimated_effort_minutes": equal_92_effort,
                            "required_concepts": [],
                            "unverified_concepts": [f"c{i + 1}"],
                            "dependencies": [] if i == 0 else [i],
                        }
                        for i in range(4)
                    ],
                    "scope_summary": "FULL_SCOPE",
                    "deferred_scope": [],
                },
                prompt_tokens=90,
                output_tokens=110,
                thinking_tokens=0,
                model_id="gemini-3.8-flash-low",
            )

    report = await run_planning_eval_suite(
        dataset_path=dataset_file,
        trials_per_goal=1,
        live=False,
        e2e=True,
        include_weekly=False,
        milestone_planner_provider_factory=lambda _i, _s: _SoftAndCondWarningPlanner(),
    )
    audit = report["per_case_outcomes"][0]["structural_audit"]
    assert "invariant_categories" in audit
    cats = audit["invariant_categories"]
    assert "hard_constraints" in cats
    assert "conditional_constraints" in cats
    assert "soft_quality_metrics" in cats
    assert "diagnostic_metrics" in cats
    assert audit["structural_validity"] is True
    assert "UNIFORM_MILESTONE_EFFORT" in audit["pedagogical_quality"]["soft_quality_warnings"]
    assert audit["pedagogical_quality"]["soft_quality_score"] < 1.0


@pytest.mark.asyncio
async def test_fit_capacity_eval_requires_explicit_fixture_simulated_decision(
    tmp_path: Path,
) -> None:
    scenarios = load_eval_dataset(HARD_6_GOALS_DATASET_PATH)[:1]
    base_no_approval = json.loads(json.dumps(scenarios[0]))
    base_no_approval["case_id"] = "FIT_NO_APPROVAL"
    base_no_approval["simulated_learner_scope_decision"] = None

    base_with_approval = json.loads(json.dumps(scenarios[0]))
    base_with_approval["case_id"] = "FIT_WITH_APPROVAL"
    base_with_approval["simulated_learner_scope_decision"] = "ACCEPT_FIT_CAPACITY"

    dataset_file = tmp_path / "fit_capacity_decision.jsonl"
    dataset_file.write_text(
        json.dumps(base_no_approval, ensure_ascii=False)
        + "\n"
        + json.dumps(base_with_approval, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )

    class _FitCapacityPlannerLLM(_E2EStubLLMAdapter):
        async def generate_structured(
            self,
            *,
            system_prompt: str = "",
            user_prompt: str = "",
            response_schema: dict[str, Any] | type[Any] | None = None,
            tools: Sequence[LLMToolDeclarationDTO | dict[str, Any]] | None = None,
            tool_executor: LLMToolExecutor | None = None,
            max_tool_calls: int | None = None,
            thinking_level: str | None = None,
            timeout_seconds: float | None = None,
            tool_call_timeout_seconds: float | None = None,
        ) -> LLMGenerationResult:
            del (
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
            efforts = [240, 300, 360, 420]
            return LLMGenerationResult(
                payload={
                    "milestones": [
                        {
                            "sequence_order": i + 1,
                            "title": f"Milestone {i + 1}",
                            "description": f"Desc {i + 1}",
                            "learning_outcomes": [f"Outcome {i + 1}"],
                            "completion_criteria": f"Done {i + 1}",
                            "estimated_effort_minutes": effort,
                            "required_concepts": [],
                            "unverified_concepts": [f"c{i + 1}"],
                            "dependencies": [] if i == 0 else [i],
                        }
                        for i, effort in enumerate(efforts)
                    ],
                    "scope_summary": "FIT_CAPACITY: scope trimmed to 1320 minutes",
                    "deferred_scope": ["Capstone multi-cluster failover"],
                },
                prompt_tokens=90,
                output_tokens=110,
                thinking_tokens=0,
                model_id="gemini-3.8-flash-low",
            )

    report = await run_planning_eval_suite(
        dataset_path=dataset_file,
        trials_per_goal=1,
        live=False,
        e2e=True,
        include_weekly=False,
        milestone_planner_provider_factory=lambda _i, _s: _FitCapacityPlannerLLM(),
    )
    assert report["passed_runs"] == 1
    assert report["failed_runs"] == 1
    assert report["error_breakdown"]["milestone_planner"]["VALIDATION_GATE"] == 1
    out_no, out_yes = report["per_case_outcomes"]
    assert out_no["passed_tier1"] is False
    assert out_no["structural_audit"]["structural_validity"] is True
    assert out_no["structural_audit"]["scheduling_feasibility"] is False
    assert (
        "FIT_CAPACITY_APPROVAL_REQUIRED"
        in out_no["structural_audit"]["failure_reasons_by_layer"]["scheduling_feasibility"]
    )
    assert out_yes["passed_tier1"] is True
    assert out_yes["structural_audit"]["structural_validity"] is True
    assert out_yes["structural_audit"]["scheduling_feasibility"] is True
    validate_eval_report_totals(report)
