import pytest

from tests.ai_evals.constraints_eval import build_report, evaluate_scenario, load_scenarios


@pytest.mark.parametrize("scenario", load_scenarios(), ids=lambda item: item["scenario_id"])
def test_golden_constraint_scenario(scenario: dict[str, object]) -> None:
    assert evaluate_scenario(scenario) == scenario["expected_valid"]


def test_golden_constraint_report_is_complete() -> None:
    report = build_report()
    assert report["total"] >= 100
    assert report["passed"] == report["total"]
    assert report["hard_constraint_violation_rate"] == 0.0
