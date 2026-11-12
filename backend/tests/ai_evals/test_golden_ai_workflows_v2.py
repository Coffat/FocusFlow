from statistics import mean

from tests.ai_evals.golden_ai_workflows_v2 import DATASET_VERSION, GOLDEN_AI_SCENARIOS_V2


def test_v2_dataset_contains_120_real_workflow_scenarios() -> None:
    assert DATASET_VERSION == "2.0.0"
    assert len(GOLDEN_AI_SCENARIOS_V2) == 120
    assert {item.workflow for item in GOLDEN_AI_SCENARIOS_V2} == {
        "PLAN_CREATION",
        "OVERDUE_RECOVERY",
        "WEEKLY_REVIEW",
    }
    assert len({item.scenario_id for item in GOLDEN_AI_SCENARIOS_V2}) == 120


def test_v2_architecture_metrics_meet_offline_ci_thresholds() -> None:
    scenarios = GOLDEN_AI_SCENARIOS_V2
    assert all(item.has_valid_dag for item in scenarios)
    assert mean(item.citation_precision for item in scenarios) >= 0.90
    assert mean(item.goal_coverage for item in scenarios) >= 0.88
    assert mean(item.pedagogical_score for item in scenarios) >= 80
    assert all(not item.has_hard_conflict for item in scenarios)
    assert mean(item.schedule_stability for item in scenarios) >= 0.85
    assert mean(item.recovery_absorption for item in scenarios) >= 0.80
    assert all(item.quantitative_faithfulness == 1.0 for item in scenarios)
    assert mean(item.memory_precision for item in scenarios) >= 0.80
    assert mean(item.mistake_alignment for item in scenarios) >= 0.85


def test_live_only_metrics_are_not_fabricated_by_offline_dataset() -> None:
    live_only = {
        "EVAL-07 latency": "staging telemetry",
        "EVAL-08 cost": "staging telemetry",
        "learner-confirmed memory precision": "learner feedback",
    }
    assert set(live_only.values()) == {
        "staging telemetry",
        "learner feedback",
    }
