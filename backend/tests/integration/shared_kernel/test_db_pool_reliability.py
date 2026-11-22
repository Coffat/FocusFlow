from __future__ import annotations

import asyncio
import math
import time
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.exc import TimeoutError as SQLAlchemyTimeoutError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import AsyncAdaptedQueuePool, NullPool

from src.shared_kernel.config import Settings, get_settings
from src.shared_kernel.infrastructure.database.session import build_async_engine


def _make_settings(**overrides: Any) -> Settings:
    base = get_settings()
    return base.model_copy(update=overrides)


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, math.ceil((pct / 100.0) * len(ordered)) - 1))
    return ordered[idx]


def test_build_async_engine_selects_pool_by_environment() -> None:
    test_engine = build_async_engine(_make_settings(environment="test"))
    dev_engine = build_async_engine(
        _make_settings(
            environment="development",
            db_pool_size=6,
            db_max_overflow=4,
            db_pool_timeout=15.0,
            db_pool_recycle=900,
            db_pool_pre_ping=True,
        )
    )
    assert isinstance(test_engine.pool, NullPool)
    assert isinstance(dev_engine.pool, AsyncAdaptedQueuePool)
    assert dev_engine.pool.size() == 6
    assert dev_engine.pool._max_overflow == 4


@pytest.mark.asyncio
async def test_pooled_engine_concurrent_queries_and_zero_leak() -> None:
    engine: AsyncEngine = build_async_engine(
        _make_settings(
            environment="development",
            db_pool_size=10,
            db_max_overflow=10,
            db_pool_timeout=10.0,
        )
    )
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async def _run_select_one() -> int:
        async with session_factory() as session:
            result = await session.execute(text("SELECT 1"))
            return int(result.scalar_one())

    try:
        results = await asyncio.gather(*(_run_select_one() for _ in range(20)))
        assert results == [1] * 20
        assert isinstance(engine.pool, AsyncAdaptedQueuePool)
        assert engine.pool.checkedout() == 0
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_statement_timeout_aborts_slow_query_cleanly() -> None:
    engine: AsyncEngine = build_async_engine(
        _make_settings(
            environment="development",
            db_pool_size=4,
            db_max_overflow=0,
            db_statement_timeout_ms=200,
            db_command_timeout=10.0,
        )
    )
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    try:
        with pytest.raises((DBAPIError, TimeoutError)) as exc_info:
            async with session_factory() as session:
                await session.execute(text("SELECT pg_sleep(1.5)"))
        err_text = str(exc_info.value).lower()
        assert (
            "statement timeout" in err_text or "querycanceled" in err_text or "timeout" in err_text
        )

        # Pool remains healthy and usable after timeout
        async with session_factory() as session:
            val = await session.execute(text("SELECT 1"))
            assert int(val.scalar_one()) == 1
        assert isinstance(engine.pool, AsyncAdaptedQueuePool)
        assert engine.pool.checkedout() == 0
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_transaction_rollback_and_session_cleanup() -> None:
    engine: AsyncEngine = build_async_engine(
        _make_settings(
            environment="development",
            db_pool_size=4,
            db_max_overflow=0,
        )
    )
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with session_factory() as session:
            await session.execute(
                text("CREATE TEMP TABLE _ff_pool_tx_test (id INT) ON COMMIT DROP")
            )
            await session.execute(text("INSERT INTO _ff_pool_tx_test (id) VALUES (42)"))
            await session.rollback()
            # After rollback, the transaction is clean and a fresh query succeeds
            val = await session.execute(text("SELECT 1"))
            assert int(val.scalar_one()) == 1

        assert isinstance(engine.pool, AsyncAdaptedQueuePool)
        assert engine.pool.checkedout() == 0
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_task_cancellation_does_not_leak_pool_connections() -> None:
    engine: AsyncEngine = build_async_engine(
        _make_settings(
            environment="development",
            db_pool_size=2,
            db_max_overflow=0,
            db_statement_timeout_ms=10000,
            db_command_timeout=10.0,
        )
    )
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    started = asyncio.Event()

    async def _slow_query() -> None:
        async with session_factory() as session:
            started.set()
            await session.execute(text("SELECT pg_sleep(5)"))

    try:
        task = asyncio.create_task(_slow_query())
        await started.wait()
        await asyncio.sleep(0.05)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        # Give asyncpg transport cancellation a brief tick to finalize cleanup
        await asyncio.sleep(0.05)
        assert isinstance(engine.pool, AsyncAdaptedQueuePool)
        assert engine.pool.checkedout() == 0

        # Pool still serves fresh queries cleanly
        async with session_factory() as session:
            res = await session.execute(text("SELECT 1"))
            assert int(res.scalar_one()) == 1
        assert engine.pool.checkedout() == 0
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_pool_exhaustion_raises_timeout_cleanly() -> None:
    engine: AsyncEngine = build_async_engine(
        _make_settings(
            environment="development",
            db_pool_size=1,
            db_max_overflow=0,
            db_pool_timeout=0.2,
        )
    )
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    holder_ready = asyncio.Event()
    release_holder = asyncio.Event()

    async def _hold_single_connection() -> None:
        async with session_factory() as session:
            await session.execute(text("SELECT 1"))
            holder_ready.set()
            await release_holder.wait()

    try:
        holder_task = asyncio.create_task(_hold_single_connection())
        await holder_ready.wait()

        with pytest.raises((SQLAlchemyTimeoutError, TimeoutError)):
            async with session_factory() as session:
                await session.execute(text("SELECT 1"))

        release_holder.set()
        await holder_task
        assert isinstance(engine.pool, AsyncAdaptedQueuePool)
        assert engine.pool.checkedout() == 0
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_benchmark_nullpool_vs_queuepool_40_concurrent_queries() -> None:
    async def _measure(engine: AsyncEngine) -> tuple[float, float, float, float]:
        session_factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        # Warm up 1 query for QueuePool connection establishment
        async with session_factory() as warm_session:
            await warm_session.execute(text("SELECT 1"))

        async def _timed_query() -> float:
            t0 = time.perf_counter()
            async with session_factory() as session:
                res = await session.execute(text("SELECT 1"))
                assert int(res.scalar_one()) == 1
            return (time.perf_counter() - t0) * 1000.0

        wall_start = time.perf_counter()
        latencies = await asyncio.gather(*(_timed_query() for _ in range(40)))
        wall_ms = (time.perf_counter() - wall_start) * 1000.0
        return (
            _percentile(list(latencies), 50),
            _percentile(list(latencies), 95),
            _percentile(list(latencies), 99),
            wall_ms,
        )

    null_engine = build_async_engine(_make_settings(environment="test"))
    pooled_engine = build_async_engine(
        _make_settings(
            environment="development",
            db_pool_size=10,
            db_max_overflow=10,
            db_pool_timeout=30.0,
        )
    )
    try:
        null_p50, null_p95, null_p99, null_wall = await _measure(null_engine)
        pool_p50, pool_p95, pool_p99, pool_wall = await _measure(pooled_engine)
        print(
            f"\n[DB POOL BENCHMARK - 40 concurrent SELECT 1]\n"
            f"  NullPool:              p50={null_p50:.2f}ms p95={null_p95:.2f}ms p99={null_p99:.2f}ms wall={null_wall:.2f}ms\n"
            f"  AsyncAdaptedQueuePool: p50={pool_p50:.2f}ms p95={pool_p95:.2f}ms p99={pool_p99:.2f}ms wall={pool_wall:.2f}ms"
        )
        assert isinstance(pooled_engine.pool, AsyncAdaptedQueuePool)
        assert pooled_engine.pool.checkedout() == 0
        assert pool_p50 > 0.0 and null_p50 > 0.0
    finally:
        await null_engine.dispose()
        await pooled_engine.dispose()
