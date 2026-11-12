from dataclasses import dataclass
from typing import Literal

DATASET_VERSION = "2.0.0"

WorkflowName = Literal["PLAN_CREATION", "OVERDUE_RECOVERY", "WEEKLY_REVIEW"]


@dataclass(frozen=True, slots=True)
class GoldenAIScenario:
    scenario_id: str
    workflow: WorkflowName
    has_valid_dag: bool
    citation_precision: float
    goal_coverage: float
    pedagogical_score: int
    has_hard_conflict: bool
    schedule_stability: float
    recovery_absorption: float
    quantitative_faithfulness: float
    memory_precision: float
    mistake_alignment: float


def _scenario(index: int, workflow: WorkflowName) -> GoldenAIScenario:
    has_citations = workflow == "PLAN_CREATION" or index % 10 != 0
    return GoldenAIScenario(
        scenario_id=f"AI2_{workflow}_{index:03d}",
        workflow=workflow,
        has_valid_dag=True,
        citation_precision=1.0 if has_citations else 0.9,
        goal_coverage=0.9,
        pedagogical_score=85,
        has_hard_conflict=False,
        schedule_stability=0.9 if workflow != "OVERDUE_RECOVERY" else 0.86,
        recovery_absorption=0.85 if workflow == "OVERDUE_RECOVERY" else 1.0,
        quantitative_faithfulness=1.0,
        memory_precision=0.85 if workflow == "WEEKLY_REVIEW" else 1.0,
        mistake_alignment=0.9,
    )


GOLDEN_AI_SCENARIOS_V2: tuple[GoldenAIScenario, ...] = tuple(
    _scenario(index, workflow)
    for workflow, count in (
        ("PLAN_CREATION", 40),
        ("OVERDUE_RECOVERY", 40),
        ("WEEKLY_REVIEW", 40),
    )
    for index in range(1, count + 1)
)
