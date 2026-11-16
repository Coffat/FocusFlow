"""Tier 2 Deterministic Spatio-Temporal, Cross-Roadmap EDF & DAG Gate (ADR-009 / T7.3)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Any

from src.execution.public_api import (
    DagCycleValidator,
    DagDependencyEdge,
    DagTaskNode,
)
from src.planning.domain.services.spatio_temporal_engine import (
    SpatioTemporalRuleEngine,
)
from src.planning.domain.services.validation_types import (
    AvailabilityConfigurationDTO,
    ConstraintViolationDTO,
    SoftOverflowWarningDTO,
    parse_iso_date,
    parse_iso_datetime,
)


def run_tier2_gate(
    proposal_data: dict[str, Any],
    *,
    availability: AvailabilityConfigurationDTO,
    existing_tasks: Sequence[object] = (),
    current_roadmap_target_date: date | None = None,
    allow_unscheduled_tasks: bool = False,
) -> tuple[list[ConstraintViolationDTO], list[SoftOverflowWarningDTO]]:
    """Execute Tier 2 Deterministic Spatio-Temporal, Cross-Roadmap EDF & DAG checks."""
    violations: list[ConstraintViolationDTO] = []
    warnings: list[SoftOverflowWarningDTO] = []

    raw_tasks = proposal_data.get("tasks")
    if not isinstance(raw_tasks, list) or not raw_tasks:
        return violations, warnings

    mode_upper = (availability.mode or "MODE_A").strip().upper()
    is_mode_b = mode_upper in ("MODE_B", "FIXED_SLOTS", "SLOTS")

    raw_blocks = proposal_data.get("schedule_blocks")
    scheduling_items = raw_tasks
    if isinstance(raw_blocks, list):
        scheduling_items = [
            {
                "task_id": block.get("task_id"),
                "estimated_minutes": block.get("scheduled_duration_minutes"),
                "scheduled_date": block.get("block_date"),
                "scheduled_start": block.get("scheduled_start"),
                "scheduled_end": block.get("scheduled_end"),
            }
            for block in raw_blocks
            if isinstance(block, dict)
        ]
    elif allow_unscheduled_tasks:
        scheduling_items = [
            task
            for task in raw_tasks
            if isinstance(task, dict) and parse_iso_date(task.get("scheduled_date")) is not None
        ]

    if is_mode_b:
        b_violations, b_warnings = SpatioTemporalRuleEngine.validate_mode_b_slots(
            tasks=scheduling_items,
            availability=availability,
            existing_tasks=existing_tasks,
            current_roadmap_target_date=current_roadmap_target_date,
        )
        violations.extend(b_violations)
        warnings.extend(b_warnings)
    else:
        a_violations = SpatioTemporalRuleEngine.validate_mode_a_quota(
            tasks=scheduling_items,
            availability=availability,
            existing_tasks=existing_tasks,
            current_roadmap_target_date=current_roadmap_target_date,
        )
        violations.extend(a_violations)

    dag_nodes: list[DagTaskNode] = []
    index_by_id: dict[str, int] = {}

    for idx, t in enumerate(raw_tasks):
        if not isinstance(t, dict):
            continue
        tid = t.get("task_id") or t.get("id") or f"task_{idx}"
        tid_key = str(tid)
        index_by_id[tid_key] = idx
        dag_nodes.append(
            DagTaskNode(
                task_id=tid_key,
                title=str(t.get("title", f"Task #{idx}")),
                scheduled_date=parse_iso_date(t.get("scheduled_date")),
                scheduled_start=parse_iso_datetime(t.get("scheduled_start")),
                scheduled_end=parse_iso_datetime(t.get("scheduled_end")),
                task_index=idx,
            )
        )

    dag_edges: list[DagDependencyEdge] = []
    raw_deps = proposal_data.get("dependencies", [])
    if isinstance(raw_deps, list):
        for dep in raw_deps:
            if not isinstance(dep, dict):
                continue
            pred_id = dep.get("predecessor_id")
            succ_id = dep.get("successor_id")
            if pred_id is None or succ_id is None:
                continue
            is_mand = bool(dep.get("is_mandatory", True))
            dag_edges.append(
                DagDependencyEdge(
                    predecessor_id=str(pred_id),
                    successor_id=str(succ_id),
                    is_mandatory=is_mand,
                )
            )

    for idx, t in enumerate(raw_tasks):
        if not isinstance(t, dict):
            continue
        tid = str(t.get("task_id") or t.get("id") or f"task_{idx}")
        prereqs = t.get("prerequisite_ids") or t.get("depends_on") or []
        if isinstance(prereqs, list):
            for p in prereqs:
                dag_edges.append(
                    DagDependencyEdge(
                        predecessor_id=str(p),
                        successor_id=tid,
                        is_mandatory=True,
                    )
                )

    if dag_edges:
        dag_res = DagCycleValidator.validate(dag_nodes, dag_edges)
        if not dag_res.is_valid:
            if dag_res.has_self_dependency:
                node_str = str(dag_res.cycle_path[0]) if dag_res.cycle_path else ""
                violations.append(
                    ConstraintViolationDTO(
                        task_index=index_by_id.get(node_str),
                        field="dependencies",
                        rule_code="DAG_SELF_DEPENDENCY",
                        expected_bound="predecessor_id != successor_id",
                        actual_value=f"{node_str} -> {node_str}",
                        suggested_fix=f"Loại bỏ cạnh phụ thuộc tự thân tại nhiệm vụ '{node_str}'.",
                    )
                )
            elif dag_res.cycle_path:
                cycle_str = " -> ".join(str(x) for x in dag_res.cycle_path)
                first_node = str(dag_res.cycle_path[0])
                violations.append(
                    ConstraintViolationDTO(
                        task_index=index_by_id.get(first_node),
                        field="dependencies",
                        rule_code="DEPENDENCY_CYCLE_DETECTED",
                        expected_bound="Acyclic directed graph (DAG)",
                        actual_value=cycle_str,
                        suggested_fix=f"Phá vỡ chu trình phụ thuộc bằng cách gỡ ít nhất một cạnh trong: {cycle_str}.",
                    )
                )
            for tv in dag_res.temporal_violations:
                succ_idx = index_by_id.get(str(tv.successor_id))
                violations.append(
                    ConstraintViolationDTO(
                        task_index=succ_idx,
                        field="scheduled_start",
                        rule_code="DEPENDENCY_TEMPORAL_ORDER_VIOLATION",
                        expected_bound=(
                            f"Bắt đầu sau khi nhiệm vụ tiền đề '{tv.predecessor_title}' kết thúc "
                            f"({tv.predecessor_end_str})"
                        ),
                        actual_value=f"'{tv.successor_title}' bắt đầu lúc {tv.successor_start_str}",
                        suggested_fix=(
                            f"Dời lịch nhiệm vụ '{tv.successor_title}' sang sau mốc {tv.predecessor_end_str}."
                        ),
                    )
                )
        if allow_unscheduled_tasks:
            node_by_id = {n.task_id: n for n in dag_nodes}
            for edge in dag_edges:
                if not edge.is_mandatory:
                    continue
                pred_node = node_by_id.get(edge.predecessor_id)
                succ_node = node_by_id.get(edge.successor_id)
                if (
                    pred_node is not None
                    and succ_node is not None
                    and pred_node.scheduled_date is None
                    and succ_node.scheduled_date is not None
                ):
                    violations.append(
                        ConstraintViolationDTO(
                            task_index=index_by_id.get(str(edge.successor_id)),
                            field="scheduled_date",
                            rule_code="DEPENDENCY_TEMPORAL_ORDER_VIOLATION",
                            expected_bound=(
                                f"Nhiệm vụ tiền đề '{pred_node.title}' phải được xếp lịch trước "
                                f"nhiệm vụ kế tiếp '{succ_node.title}'"
                            ),
                            actual_value=(
                                f"'{pred_node.title}' chưa xếp lịch nhưng '{succ_node.title}' "
                                f"được xếp vào {succ_node.scheduled_date.isoformat()}"
                            ),
                            suggested_fix=(
                                f"Xếp lịch cho nhiệm vụ tiền đề '{pred_node.title}' trước hoặc đưa "
                                f"'{succ_node.title}' vào danh sách chờ."
                            ),
                        )
                    )

    return violations, warnings
