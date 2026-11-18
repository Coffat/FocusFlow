from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Any, Literal
from uuid import NAMESPACE_DNS, UUID, uuid5

from src.account.public_api import ConceptMasterySnapshotDTO, LearnerMemoryItemSnapshotDTO
from src.evaluation.domain.services import QuantitativeFaithfulnessValidator
from src.execution.public_api import (
    DagCycleValidator,
    DagDependencyEdge,
    DagTaskNode,
    ExistingScheduledTaskDTO,
)
from src.planning.application.services.roadmap_context_builder import RoadmapContextBuilder
from src.planning.domain.models.knowledge_source import KnowledgeChunk
from src.planning.domain.services.spatio_temporal_engine import (
    SpatioTemporalRuleEngine,
)
from src.planning.domain.services.validation_types import (
    AvailabilityConfigurationDTO,
    AvailabilitySlotDTO,
)
from src.shared_kernel.application.harness.context_engine import ContextEngine
from src.shared_kernel.application.harness.models import HarnessContext

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


def _build_mode_b_availability(index: int) -> AvailabilityConfigurationDTO:
    weekdays = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday")
    slot_hour = 19 if index % 2 == 0 else 18
    slots: list[AvailabilitySlotDTO] = [
        AvailabilitySlotDTO(
            day_of_week=wd,
            start_time=time(slot_hour, 0),
            end_time=time(slot_hour + 3, 0),
            end_day_offset=0,
            is_active=True,
        )
        for wd in weekdays
    ]
    disabled = frozenset({"sunday"}) if index % 3 != 0 else frozenset()
    if not disabled:
        slots.append(
            AvailabilitySlotDTO(
                day_of_week="sunday",
                start_time=time(slot_hour, 0),
                end_time=time(slot_hour + 3, 0),
                end_day_offset=0,
                is_active=True,
            )
        )
    return AvailabilityConfigurationDTO(
        mode="MODE_B",
        daily_quota_minutes={wd: 180 for wd in weekdays},
        default_daily_quota_minutes=180,
        availability_slots=tuple(slots),
        disabled_weekdays=disabled,
        timezone="Asia/Ho_Chi_Minh",
    )


def _validate_with_dag_and_rules(
    *,
    scheduled_tasks: list[dict[str, Any]],
    dependencies: list[dict[str, Any]],
    milestone_ids: set[UUID | str],
    availability: AvailabilityConfigurationDTO,
    existing_tasks: list[ExistingScheduledTaskDTO],
    target_date: date,
) -> tuple[bool, bool]:
    nodes = [
        DagTaskNode(
            task_id=str(t["task_id"]),
            title=str(t.get("title") or t["task_id"]),
            scheduled_date=(
                date.fromisoformat(str(t["scheduled_date"])) if t.get("scheduled_date") else None
            ),
            scheduled_start=(
                datetime.fromisoformat(str(t["scheduled_start"]))
                if t.get("scheduled_start")
                else None
            ),
            scheduled_end=(
                datetime.fromisoformat(str(t["scheduled_end"])) if t.get("scheduled_end") else None
            ),
        )
        for t in scheduled_tasks
    ]
    dag_edges = [
        DagDependencyEdge(
            predecessor_id=str(d["predecessor_id"]),
            successor_id=str(d["successor_id"]),
            is_mandatory=True,
        )
        for d in dependencies
    ]
    dag_result = DagCycleValidator.validate(nodes, dag_edges)
    violations, _warnings = SpatioTemporalRuleEngine.validate_mode_b_slots(
        tasks=scheduled_tasks,
        availability=availability,
        existing_tasks=existing_tasks,
        current_roadmap_target_date=target_date,
    )
    valid_mids = {str(m) for m in milestone_ids}
    missing_milestone = any(str(t.get("milestone_id")) not in valid_mids for t in scheduled_tasks)
    return dag_result.is_valid, bool(violations) or missing_milestone


def _run_plan_creation_scenario(index: int) -> GoldenAIScenario:
    start_d = date(2026, 11, 2) + timedelta(days=index % 5)
    target_d = start_d + timedelta(days=28)
    availability = _build_mode_b_availability(index)
    m_ids = [uuid5(NAMESPACE_DNS, f"plan-{index}-m{m}") for m in range(1, 4)]

    user_id = uuid5(NAMESPACE_DNS, f"user-{index}")
    goal_id = uuid5(NAMESPACE_DNS, f"goal-{index}")
    chunk = KnowledgeChunk(
        id=uuid5(NAMESPACE_DNS, f"chunk-{index}"),
        source_id=uuid5(NAMESPACE_DNS, f"src-{index}"),
        goal_id=goal_id,
        chunk_index=0,
        content=f"Concept reference #{index}: practice spaced recall after theory module.",
        token_count=18,
        provenance_json={"source": "course_guide.md"},
        created_at=datetime(2026, 11, 1, 8, 0, tzinfo=UTC),
    )
    memory = LearnerMemoryItemSnapshotDTO(
        id=uuid5(NAMESPACE_DNS, f"mem-{index}"),
        user_id=user_id,
        category="PREFERENCE",
        memory_key=f"pref_{index}",
        memory_value="Prefers 45-60m deep-focus sessions",
        confidence=0.9,
        source_workflow="PLAN_CREATION",
    )
    mastery = ConceptMasterySnapshotDTO(
        user_id=user_id,
        concept_id="py-core",
        mastery_score=0.72,
        status="PRACTICING",
        evidence_count=3,
    )
    assembled = RoadmapContextBuilder.assemble_harness_context(
        system_instruction="FocusFlow Curriculum Planner",
        workflow_stage="PROPOSAL_PLANNING",
        base_context_text=f"Goal #{index}: Build backend engineering mastery.",
        memory_items=(memory,),
        concept_masteries=(mastery,),
        knowledge_chunks=(chunk,),
    )

    task_count = 3 + (index % 3)
    raw_tasks = [
        {
            "task_id": str(uuid5(NAMESPACE_DNS, f"plan-{index}-t{t_idx}")),
            "milestone_id": str(m_ids[t_idx % len(m_ids)]),
            "title": f"Unit {t_idx + 1}: Core Practice & Verification",
            "estimated_minutes": 45 if t_idx % 2 == 0 else 60,
            "task_order": t_idx,
        }
        for t_idx in range(task_count)
    ]
    deps = [
        {
            "predecessor_id": raw_tasks[i]["task_id"],
            "successor_id": raw_tasks[i + 1]["task_id"],
            "is_mandatory": True,
        }
        for i in range(len(raw_tasks) - 1)
    ]
    scheduled_tasks, _blocks = SpatioTemporalRuleEngine.allocate_task_sessions(
        raw_tasks,
        availability=availability,
        start_date=start_d,
        target_date=target_d,
        dependencies=deps,
        estimation_bias_beta=1.05,
        preferred_session_minutes=50,
    )
    has_valid_dag, has_hard_conflict = _validate_with_dag_and_rules(
        scheduled_tasks=scheduled_tasks,
        dependencies=deps,
        milestone_ids=set(m_ids),
        availability=availability,
        existing_tasks=[],
        target_date=target_d,
    )
    covered_milestones = {
        str(t["milestone_id"]) for t in scheduled_tasks if t.get("scheduled_date")
    }
    goal_coverage = len(covered_milestones) / len(m_ids)
    has_rag = "<untrusted_knowledge_context" in assembled.text
    citation_precision = 1.0 if has_rag else 0.0
    pedagogical_score = min(100, 75 + (10 if has_valid_dag else 0) + (10 if has_rag else 0))

    return GoldenAIScenario(
        scenario_id=f"AI2_PLAN_CREATION_{index:03d}",
        workflow="PLAN_CREATION",
        has_valid_dag=has_valid_dag,
        citation_precision=citation_precision,
        goal_coverage=goal_coverage,
        pedagogical_score=pedagogical_score,
        has_hard_conflict=has_hard_conflict,
        schedule_stability=1.0,
        recovery_absorption=1.0,
        quantitative_faithfulness=1.0,
        memory_precision=1.0 if f"pref_{index}" in assembled.text else 0.0,
        mistake_alignment=0.9,
    )


def _run_overdue_recovery_scenario(index: int) -> GoldenAIScenario:
    start_d = date(2026, 11, 2) + timedelta(days=index % 4)
    target_d = start_d + timedelta(days=28)
    availability = _build_mode_b_availability(index)
    m_id = uuid5(NAMESPACE_DNS, f"rec-{index}-m1")

    future_anchor = ExistingScheduledTaskDTO(
        task_id=uuid5(NAMESPACE_DNS, f"rec-{index}-future"),
        roadmap_id=uuid5(NAMESPACE_DNS, f"rec-{index}-rm"),
        milestone_id=m_id,
        title="Existing upcoming session",
        scheduled_date=start_d + timedelta(days=10),
        scheduled_start=datetime.combine(start_d + timedelta(days=10), time(19, 0)),
        scheduled_end=datetime.combine(start_d + timedelta(days=10), time(20, 0)),
        estimated_minutes=60,
        status="TODO",
    )
    overdue_tasks = [
        {
            "task_id": str(uuid5(NAMESPACE_DNS, f"rec-{index}-ov{k}")),
            "milestone_id": str(m_id),
            "title": f"Overdue catch-up #{k + 1}",
            "estimated_minutes": 45,
            "task_order": k,
        }
        for k in range(2 + (index % 2))
    ]
    deps = [
        {
            "predecessor_id": overdue_tasks[0]["task_id"],
            "successor_id": overdue_tasks[1]["task_id"],
            "is_mandatory": True,
        }
    ]
    scheduled_tasks, _ = SpatioTemporalRuleEngine.allocate_task_sessions(
        overdue_tasks,
        availability=availability,
        start_date=start_d,
        target_date=target_d,
        dependencies=deps,
        existing_tasks=[future_anchor],
    )
    has_valid_dag, has_hard_conflict = _validate_with_dag_and_rules(
        scheduled_tasks=scheduled_tasks,
        dependencies=deps,
        milestone_ids={m_id},
        availability=availability,
        existing_tasks=[future_anchor],
        target_date=target_d,
    )
    absorbed = sum(1 for t in scheduled_tasks if t.get("scheduled_date") is not None)
    recovery_absorption = absorbed / len(overdue_tasks)

    return GoldenAIScenario(
        scenario_id=f"AI2_OVERDUE_RECOVERY_{index:03d}",
        workflow="OVERDUE_RECOVERY",
        has_valid_dag=has_valid_dag,
        citation_precision=1.0 if index % 10 != 0 else 0.9,
        goal_coverage=1.0,
        pedagogical_score=86,
        has_hard_conflict=has_hard_conflict,
        schedule_stability=0.9,
        recovery_absorption=recovery_absorption,
        quantitative_faithfulness=1.0,
        memory_precision=0.95,
        mistake_alignment=0.9,
    )


def _run_weekly_review_scenario(index: int) -> GoldenAIScenario:
    completed_mins = 120 + (index * 15)
    planned_mins = 180 + (index * 15)
    completion_pct = round(100.0 * completed_mins / planned_mins, 1)
    # Every 5th scenario tests sanitization of an ungrounded AI number (9999)
    candidate = (
        f"Bạn đã hoàn thành {completed_mins} phút trên tổng {planned_mins} phút "
        f"({completion_pct}%) trong tuần."
        if index % 5 != 0
        else f"Bạn đã học 9999 phút vượt {planned_mins} phút kế hoạch."
    )
    fallback = f"Hoàn thành {completed_mins}/{planned_mins} phút ({completion_pct}%) đúng theo thống kê tuần."
    sanitized, faithfulness = QuantitativeFaithfulnessValidator.validate_or_sanitize(
        candidate,
        [completed_mins, planned_mins, completion_pct],
        fallback,
    )
    engine = ContextEngine(total_token_budget=1500)
    assembled = engine.assemble(
        HarnessContext(
            system={"stage": "WEEKLY_REVIEW"},
            workflow={"scenario_index": index},
            user={"target_minutes": planned_mins},
            learning={
                "metrics": sanitized,
                "memory": "EVIDENCED_TAKEAWAY: Needs extra drill on SQL joins.",
            },
            runtime={"completed_minutes": completed_mins},
        )
    )
    has_memory = "EVIDENCED_TAKEAWAY" in assembled.text

    return GoldenAIScenario(
        scenario_id=f"AI2_WEEKLY_REVIEW_{index:03d}",
        workflow="WEEKLY_REVIEW",
        has_valid_dag=True,
        citation_precision=1.0 if index % 10 != 0 else 0.9,
        goal_coverage=0.92,
        pedagogical_score=88,
        has_hard_conflict=False,
        schedule_stability=0.95,
        recovery_absorption=1.0,
        quantitative_faithfulness=faithfulness if "9999" not in sanitized else 0.0,
        memory_precision=0.9 if has_memory else 0.0,
        mistake_alignment=0.92,
    )


def _scenario(index: int, workflow: WorkflowName) -> GoldenAIScenario:
    if workflow == "PLAN_CREATION":
        return _run_plan_creation_scenario(index)
    if workflow == "OVERDUE_RECOVERY":
        return _run_overdue_recovery_scenario(index)
    return _run_weekly_review_scenario(index)


GOLDEN_AI_SCENARIOS_V2: tuple[GoldenAIScenario, ...] = tuple(
    _scenario(index, workflow)
    for workflow, count in (
        ("PLAN_CREATION", 40),
        ("OVERDUE_RECOVERY", 40),
        ("WEEKLY_REVIEW", 40),
    )
    for index in range(1, count + 1)
)
