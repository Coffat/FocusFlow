from datetime import UTC, date, datetime
from uuid import UUID

import pytest
from uuid6 import uuid7

from src.execution.domain.services.dag_cycle_validator import (
    DagCycleValidator,
    DagDependencyEdge,
    DagTaskNode,
    DagValidationError,
)


def test_dag_cycle_validator_valid_acyclic_graph_and_temporal_order() -> None:
    t1_id = uuid7()
    t2_id = uuid7()
    t3_id = uuid7()

    tasks = [
        DagTaskNode(
            task_id=t1_id,
            title="Task 1",
            scheduled_date=date(2026, 11, 2),
            scheduled_start=datetime(2026, 11, 2, 19, 0, tzinfo=UTC),
            scheduled_end=datetime(2026, 11, 2, 20, 0, tzinfo=UTC),
        ),
        DagTaskNode(
            task_id=t2_id,
            title="Task 2",
            scheduled_date=date(2026, 11, 2),
            scheduled_start=datetime(2026, 11, 2, 20, 0, tzinfo=UTC),
            scheduled_end=datetime(2026, 11, 2, 21, 0, tzinfo=UTC),
        ),
        DagTaskNode(
            task_id=t3_id,
            title="Task 3",
            scheduled_date=date(2026, 11, 3),
            scheduled_start=datetime(2026, 11, 3, 19, 0, tzinfo=UTC),
            scheduled_end=datetime(2026, 11, 3, 20, 30, tzinfo=UTC),
        ),
    ]
    edges = [
        DagDependencyEdge(predecessor_id=t1_id, successor_id=t2_id, is_mandatory=True),
        DagDependencyEdge(predecessor_id=t2_id, successor_id=t3_id, is_mandatory=True),
        DagDependencyEdge(predecessor_id=t1_id, successor_id=t3_id, is_mandatory=True),
    ]

    result = DagCycleValidator.assert_valid(tasks, edges)
    assert result.is_valid is True
    assert result.has_self_dependency is False
    assert result.cycle_path == ()
    assert result.temporal_violations == ()


def test_dag_cycle_validator_detects_self_dependency() -> None:
    t1_id = uuid7()
    tasks = [DagTaskNode(task_id=t1_id, title="Self Dependent Task")]
    edges = [DagDependencyEdge(predecessor_id=t1_id, successor_id=t1_id, is_mandatory=True)]

    result = DagCycleValidator.validate(tasks, edges)
    assert result.is_valid is False
    assert result.has_self_dependency is True
    assert result.cycle_path == (t1_id, t1_id)

    with pytest.raises(DagValidationError) as exc_info:
        DagCycleValidator.assert_valid(tasks, edges)
    assert exc_info.value.code == "DEPENDENCY_CYCLE_DETECTED"


def test_dag_cycle_validator_detects_2_node_and_3_node_cycles() -> None:
    a, b, c = "task_a", "task_b", "task_c"
    tasks = [
        DagTaskNode(task_id=a, title="A"),
        DagTaskNode(task_id=b, title="B"),
        DagTaskNode(task_id=c, title="C"),
    ]

    # 2-node cycle A -> B -> A
    edges_2 = [
        DagDependencyEdge(predecessor_id=a, successor_id=b),
        DagDependencyEdge(predecessor_id=b, successor_id=a),
    ]
    res_2 = DagCycleValidator.validate(tasks, edges_2)
    assert res_2.is_valid is False
    assert res_2.cycle_path == (a, b, a)

    # 3-node cycle A -> B -> C -> A
    edges_3 = [
        DagDependencyEdge(predecessor_id=a, successor_id=b),
        DagDependencyEdge(predecessor_id=b, successor_id=c),
        DagDependencyEdge(predecessor_id=c, successor_id=a),
    ]
    res_3 = DagCycleValidator.validate(tasks, edges_3)
    assert res_3.is_valid is False
    assert res_3.cycle_path == (a, b, c, a)


def test_dag_cycle_validator_detects_mandatory_temporal_violation() -> None:
    pred_id: UUID = uuid7()
    succ_id: UUID = uuid7()
    tasks = [
        DagTaskNode(
            task_id=pred_id,
            title="Predecessor",
            scheduled_date=date(2026, 11, 5),
            scheduled_start=datetime(2026, 11, 5, 20, 0, tzinfo=UTC),
            scheduled_end=datetime(2026, 11, 5, 21, 0, tzinfo=UTC),
        ),
        DagTaskNode(
            task_id=succ_id,
            title="Successor",
            scheduled_date=date(2026, 11, 5),
            scheduled_start=datetime(2026, 11, 5, 19, 0, tzinfo=UTC),
            scheduled_end=datetime(2026, 11, 5, 20, 0, tzinfo=UTC),
        ),
    ]
    edges = [DagDependencyEdge(predecessor_id=pred_id, successor_id=succ_id, is_mandatory=True)]

    res = DagCycleValidator.validate(tasks, edges)
    assert res.is_valid is False
    assert len(res.temporal_violations) == 1
    assert res.temporal_violations[0].predecessor_id == pred_id
    assert res.temporal_violations[0].successor_id == succ_id

    # Non-mandatory edge does not fail temporal order
    non_mandatory_edges = [
        DagDependencyEdge(predecessor_id=pred_id, successor_id=succ_id, is_mandatory=False)
    ]
    res_opt = DagCycleValidator.validate(tasks, non_mandatory_edges)
    assert res_opt.is_valid is True
