"""Generated examples exercise hard constraints independently of fixed fixtures."""

from datetime import time

from hypothesis import given, settings
from hypothesis import strategies as st

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


@settings(max_examples=100, derandomize=True)
@given(quota=st.integers(min_value=1, max_value=28), allocated=st.integers(0, 1000))
def test_mode_a_ceiling_and_remaining_capacity(quota: int, allocated: int) -> None:
    ceiling = quota * 30
    profile = AvailabilityProfile(
        mode=AvailabilityMode.MODE_A,
        weekly_schedule=WeeklySchedule(
            days={"monday": DaySchedule(enabled=True, quota_hours=quota / 2)}
        ),
    )
    result = HybridAvailabilityRuleEngine.validate_daily_ceiling(profile, "monday", allocated)
    remaining = HybridAvailabilityRuleEngine.calculate_remaining_capacity(
        profile, "monday", allocated_minutes=allocated
    )
    assert result.is_valid == (allocated <= ceiling)
    assert result.overflow_minutes == max(0, allocated - ceiling)
    assert remaining == max(0, ceiling - allocated)


@settings(max_examples=100, derandomize=True)
@given(overflow=st.integers(min_value=0, max_value=60))
def test_mode_b_soft_overflow_boundary(overflow: int) -> None:
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
    end = 21 * 60 + overflow
    task = ProposedTaskSlot(
        task_id=None,
        title="Generated task",
        day_of_week="monday",
        start_time=time(19),
        end_time=time(end // 60, end % 60),
        duration_minutes=120 + overflow,
    )
    result = HybridAvailabilityRuleEngine.validate_proposal_against_slots(profile, "monday", [task])
    assert result.is_valid == (overflow <= 30)
    assert result.has_soft_overflow == (0 < overflow <= 30)


@settings(max_examples=100, derandomize=True)
@given(size=st.integers(min_value=2, max_value=35), cycle=st.booleans())
def test_dag_cycle_is_always_rejected(size: int, cycle: bool) -> None:
    nodes = [DagTaskNode(task_id=f"n{i}", title=f"Task {i}") for i in range(size)]
    edges = [
        DagDependencyEdge(predecessor_id=f"n{i}", successor_id=f"n{i + 1}") for i in range(size - 1)
    ]
    if cycle:
        edges.append(DagDependencyEdge(predecessor_id=f"n{size - 1}", successor_id="n0"))
    result = DagCycleValidator.validate(nodes, edges)
    assert result.is_valid == (not cycle)
    if cycle:
        assert result.cycle_path[0] == result.cycle_path[-1]
