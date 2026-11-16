"""Tests for T0.1 (18-goal eval dataset) and T0.2 (offline eval metrics & PII-free artifact)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.ai_evals.eval_runner import load_18_goal_dataset, run_planning_eval_suite


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
    assert report["total_runs"] == 54
    assert report["pass_at_1"] == 1.0
    assert report["post_retry_recovery_rate"] == 1.0
    assert report["avg_retries"] == 0.0
    assert report["prompt_tokens_total"] > 0
    assert report["output_tokens_total"] > 0
    assert report["latency_p50_ms"] >= 0.0
    assert report["latency_p95_ms"] >= report["latency_p50_ms"]
    assert report["judge_timeout_rate"] > 0.0
    assert report["weekly_fallback_rate"] > 0.0
    assert report["injection_isolation_rate"] == 1.0
    assert len(report["per_case_outcomes"]) == 18

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
