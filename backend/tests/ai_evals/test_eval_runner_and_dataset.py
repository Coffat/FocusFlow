"""Tests for T0.1 (18-goal eval dataset), T0.2 (offline eval metrics), and Group 4 (4.1-4.5)."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

from src.account.public_api import QuotaExceededError
from src.planning.domain.exceptions.planning_exceptions import ProposalValidationGateError
from src.shared_kernel.application.llm_port import LLMGenerationResult, LLMProviderPort
from tests.ai_evals.eval_runner import (
    ERROR_TAXONOMY_CATEGORIES,
    load_18_goal_dataset,
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
