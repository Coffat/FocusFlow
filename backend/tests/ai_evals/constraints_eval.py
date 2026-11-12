"""Versioned, offline evaluation of deterministic ADR-009 hard constraints."""

import json
from datetime import time
from pathlib import Path
from typing import Any

from src.account.domain.models.availability import (
    AvailabilityMode,
    AvailabilityProfile,
    DaySchedule,
    ProposedTaskSlot,
    TimeSlot,
    WeeklySchedule,
)
from src.account.domain.services.hybrid_availability_rule_engine import (
    HybridAvailabilityRuleEngine,
)
from src.execution.public_api import DagCycleValidator, DagDependencyEdge, DagTaskNode
from src.shared_kernel.infrastructure.external_ai.prompt_sanitizer import PromptSanitizer

DATASET = Path(__file__).parent / "datasets" / "golden_constraints_v1.jsonl"


def load_scenarios() -> list[dict[str, Any]]:
    scenarios = [json.loads(line) for line in DATASET.read_text().splitlines() if line.strip()]
    ids = [item["scenario_id"] for item in scenarios]
    if (
        len(scenarios) < 100
        or len(ids) != len(set(ids))
        or any(s["version"] != 1 for s in scenarios)
    ):
        raise ValueError("Golden dataset must contain 100+ unique version 1 scenarios")
    return scenarios


def evaluate_scenario(scenario: dict[str, Any]) -> bool:
    kind = scenario["kind"]
    if kind == "mode_a_ceiling":
        profile = AvailabilityProfile(
            mode=AvailabilityMode.MODE_A,
            weekly_schedule=WeeklySchedule(
                days={
                    "monday": DaySchedule(enabled=True, quota_hours=scenario["quota_minutes"] / 60)
                }
            ),
        )
        return HybridAvailabilityRuleEngine.validate_daily_ceiling(
            profile, "monday", scenario["allocated_minutes"]
        ).is_valid
    if kind == "mode_b_overflow":
        overflow = scenario["overflow_minutes"]
        end = 21 * 60 + overflow
        profile = AvailabilityProfile(
            mode=AvailabilityMode.MODE_B,
            weekly_schedule=WeeklySchedule(
                days={
                    "monday": DaySchedule(
                        enabled=True,
                        quota_hours=2.0,
                        time_slots=(TimeSlot.from_str("19:00", "21:00"),),
                    )
                }
            ),
        )
        task = ProposedTaskSlot(
            task_id=None,
            title="Golden task",
            day_of_week="monday",
            start_time=time(19),
            end_time=time(end // 60, end % 60),
            duration_minutes=120 + overflow,
        )
        return HybridAvailabilityRuleEngine.validate_proposal_against_slots(
            profile, "monday", [task]
        ).is_valid
    if kind == "dag_cycle":
        size = scenario["nodes"]
        nodes = [DagTaskNode(task_id=f"n{i}", title=f"Task {i}") for i in range(size)]
        edges = [
            DagDependencyEdge(predecessor_id=f"n{i}", successor_id=f"n{i + 1}")
            for i in range(size - 1)
        ]
        edges.append(DagDependencyEdge(predecessor_id=f"n{size - 1}", successor_id="n0"))
        return DagCycleValidator.validate(nodes, edges).is_valid
    if kind == "prompt_isolation":
        wrapped = PromptSanitizer.sanitize_and_wrap(
            "untrusted_knowledge_context", scenario["payload"]
        )
        return (
            wrapped.startswith("<untrusted_knowledge_context>")
            and wrapped.endswith("</untrusted_knowledge_context>")
            and wrapped.count("<untrusted_knowledge_context>") == 1
            and wrapped.count("</untrusted_knowledge_context>") == 1
            and scenario["forbidden_text"] not in wrapped
        )
    raise ValueError(f"Unknown scenario kind: {kind}")


def build_report() -> dict[str, Any]:
    cases = []
    for scenario in load_scenarios():
        actual = evaluate_scenario(scenario)
        cases.append(
            {
                "scenario_id": scenario["scenario_id"],
                "kind": scenario["kind"],
                "passed": actual == scenario["expected_valid"],
            }
        )
    failures = sum(not case["passed"] for case in cases)
    return {
        "dataset": DATASET.name,
        "version": 1,
        "total": len(cases),
        "passed": len(cases) - failures,
        "hard_constraint_violation_rate": failures / len(cases),
        "cases": cases,
    }


if __name__ == "__main__":
    print(json.dumps(build_report(), ensure_ascii=False, indent=2))
