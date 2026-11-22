"""Unit tests for dynamic milestone logical-subjob orchestration."""

from __future__ import annotations

import asyncio

import pytest

from src.planning.application.services.milestone_scoped_decomposer import (
    calculate_dynamic_subjob_concurrency,
    calculate_milestone_subjob_timeout,
    run_dynamic_subjob_pool,
)


@pytest.mark.parametrize(
    ("milestone_count", "expected_workers"),
    [(1, 1), (3, 3), (4, 4), (6, 4), (7, 4)],
)
def test_dynamic_subjob_concurrency_scales_with_milestone_count(
    milestone_count: int,
    expected_workers: int,
) -> None:
    assert calculate_dynamic_subjob_concurrency(milestone_count, ceiling=4) == expected_workers


def test_dynamic_subjob_concurrency_respects_configured_ceiling() -> None:
    assert calculate_dynamic_subjob_concurrency(7, ceiling=2) == 2


def test_milestone_subjob_timeout_reserves_finalization_budget() -> None:
    assert (
        calculate_milestone_subjob_timeout(
            pipeline_remaining_seconds=55.0,
            attempt_cap_seconds=36.0,
            finalization_reserve_seconds=14.0,
        )
        == 36.0
    )
    assert (
        calculate_milestone_subjob_timeout(
            pipeline_remaining_seconds=30.0,
            attempt_cap_seconds=36.0,
            finalization_reserve_seconds=14.0,
        )
        == 16.0
    )


def test_milestone_subjob_timeout_fails_before_consuming_finalization_budget() -> None:
    with pytest.raises(TimeoutError, match="finalization budget"):
        calculate_milestone_subjob_timeout(
            pipeline_remaining_seconds=14.0,
            attempt_cap_seconds=36.0,
            finalization_reserve_seconds=14.0,
        )


@pytest.mark.asyncio
async def test_dynamic_subjob_pool_work_steals_without_duplicates_and_preserves_order() -> None:
    active = 0
    peak_active = 0
    executed: list[int] = []

    async def run_one(item: int) -> int:
        nonlocal active, peak_active
        active += 1
        peak_active = max(peak_active, active)
        executed.append(item)
        await asyncio.sleep(0)
        active -= 1
        return item * 10

    results = await run_dynamic_subjob_pool(
        items=list(range(7)),
        worker_count=4,
        run_one=run_one,
    )

    assert peak_active == 4
    assert sorted(executed) == list(range(7))
    assert results == [0, 10, 20, 30, 40, 50, 60]


@pytest.mark.asyncio
async def test_dynamic_subjob_pool_keeps_processing_siblings_after_one_failure() -> None:
    executed: list[int] = []

    async def run_one(item: int) -> int:
        executed.append(item)
        if item == 2:
            raise TimeoutError("milestone 2 timed out")
        await asyncio.sleep(0)
        return item

    results = await run_dynamic_subjob_pool(
        items=list(range(5)),
        worker_count=3,
        run_one=run_one,
    )

    assert sorted(executed) == list(range(5))
    assert isinstance(results[2], TimeoutError)
    assert [result for result in results if not isinstance(result, BaseException)] == [0, 1, 3, 4]
