from __future__ import annotations

import asyncio
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import patch
from uuid import UUID

import pytest
import redis.asyncio as aioredis
from sqlalchemy import delete, select, text
from taskiq_redis import RedisStreamBroker
from uuid6 import uuid7

from src.shared_kernel.infrastructure.database.session import async_session_factory
from src.shared_kernel.infrastructure.outbox.models import OutboxEventORM, ProcessedEventORM
from src.shared_kernel.infrastructure.outbox.relay import (
    clear_outbox_handlers,
    collect_outbox_metrics,
    compute_retry_backoff_seconds,
    get_registered_outbox_handlers,
    register_outbox_handler,
    relay_pending_outbox_events,
    reset_outbox_relay_metrics,
)
from src.shared_kernel.infrastructure.outbox.repository import SqlAlchemyOutboxRepository

REDIS_URL = "redis://localhost:6379"


@pytest.fixture
def isolated_outbox_handlers() -> Generator[None, None, None]:
    snapshot = {et: list(handlers) for et, handlers in get_registered_outbox_handlers().items()}
    clear_outbox_handlers()
    reset_outbox_relay_metrics()
    try:
        yield
    finally:
        clear_outbox_handlers()
        for et, handlers in snapshot.items():
            for name, fn in handlers:
                register_outbox_handler(et, name, fn)


async def _seed_outbox_event(
    *,
    event_type: str,
    payload: dict[str, Any],
    aggregate_type: str = "ReliabilityTestAggregate",
    aggregate_id: UUID | None = None,
    created_at: datetime | None = None,
    status: str = "PENDING",
    retry_count: int = 0,
) -> UUID:
    event_id = uuid7()
    async with async_session_factory() as session:
        session.add(
            OutboxEventORM(
                id=event_id,
                aggregate_type=aggregate_type,
                aggregate_id=aggregate_id or uuid7(),
                event_type=event_type,
                payload=payload,
                status=status,
                retry_count=retry_count,
                created_at=created_at or datetime.now(UTC),
                published_at=datetime.now(UTC) if status == "PUBLISHED" else None,
            )
        )
        await session.commit()
    return event_id


async def _cleanup_outbox_events(event_ids: list[UUID]) -> None:
    if not event_ids:
        return
    async with async_session_factory() as session:
        await session.execute(delete(OutboxEventORM).where(OutboxEventORM.id.in_(event_ids)))
        await session.commit()


@pytest.mark.asyncio
async def test_unknown_event_type_is_quarantined_and_never_marked_published(
    isolated_outbox_handlers: None,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """AUD-HIGH-07: Unknown event types must NEVER be silently marked PUBLISHED."""
    event_type = f"UnknownOrphanEvent_{uuid7().hex}"
    event_id = await _seed_outbox_event(event_type=event_type, payload={"hello": "world"})

    try:
        with caplog.at_level("WARNING", logger="focusflow.shared_kernel.outbox.relay"):
            published = await relay_pending_outbox_events(batch_size=100, max_retries=5)

        assert published == 0

        async with async_session_factory() as session:
            row = await session.get(OutboxEventORM, event_id)
            assert row is not None
            assert row.status == "FAILED"
            assert row.published_at is None
            meta = row.payload.get("_outbox_meta", {})
            assert meta.get("failure_code") == "NO_HANDLER_REGISTERED"
            assert "NO_HANDLER_REGISTERED" in str(meta.get("last_error", ""))
            assert row.payload.get("hello") == "world"

            metrics = await collect_outbox_metrics(session)
            assert metrics.unknown_handler_events >= 1
            assert metrics.failed_count >= 1

        assert any("NO_HANDLER_REGISTERED" in rec.message for rec in caplog.records)
    finally:
        await _cleanup_outbox_events([event_id])


@pytest.mark.asyncio
async def test_transient_failure_uses_exponential_backoff_and_recovers(
    isolated_outbox_handlers: None,
) -> None:
    """Transient handler failures must back off exponentially before retrying and recovering."""
    assert (
        compute_retry_backoff_seconds(1, base_backoff_seconds=10.0, max_backoff_seconds=60.0)
        == 10.0
    )
    assert (
        compute_retry_backoff_seconds(2, base_backoff_seconds=10.0, max_backoff_seconds=60.0)
        == 20.0
    )
    assert (
        compute_retry_backoff_seconds(3, base_backoff_seconds=10.0, max_backoff_seconds=60.0)
        == 40.0
    )
    assert (
        compute_retry_backoff_seconds(4, base_backoff_seconds=10.0, max_backoff_seconds=60.0)
        == 60.0
    )

    event_type = f"BackoffRecoverEvent_{uuid7().hex}"
    attempts = 0
    received_payloads: list[dict[str, Any]] = []

    async def flaky_handler(event_id: UUID, payload: dict[str, Any]) -> None:
        nonlocal attempts
        attempts += 1
        if attempts <= 2:
            raise ConnectionError(f"transient broker outage attempt={attempts}")
        received_payloads.append(payload)

    register_outbox_handler(event_type, "test.backoff_handler", flaky_handler)
    t0 = datetime.now(UTC)
    event_id = await _seed_outbox_event(
        event_type=event_type,
        payload={"order_id": "abc-123"},
        created_at=t0 - timedelta(seconds=5),
    )

    try:
        # Attempt 1 at t0 -> fails, schedules next_retry_at = t0 + 10s
        published = await relay_pending_outbox_events(
            batch_size=100,
            max_retries=5,
            base_backoff_seconds=10.0,
            max_backoff_seconds=60.0,
            now=t0,
        )
        assert published == 0
        assert attempts == 1

        async with async_session_factory() as session:
            row = await session.get(OutboxEventORM, event_id)
            assert row is not None
            assert row.status == "PENDING"
            assert row.retry_count == 1
            assert row.published_at is None
            meta = row.payload.get("_outbox_meta", {})
            assert meta.get("next_retry_at") is not None
            assert "ConnectionError" in str(meta.get("last_error", ""))

        # Poll at t0 + 5s (before 10s backoff elapses) -> must be skipped
        published = await relay_pending_outbox_events(
            batch_size=100,
            max_retries=5,
            base_backoff_seconds=10.0,
            max_backoff_seconds=60.0,
            now=t0 + timedelta(seconds=5),
        )
        assert published == 0
        assert attempts == 1

        # Poll at t0 + 11s -> attempt 2 runs and fails -> schedules 20s backoff (t0 + 31s)
        t1 = t0 + timedelta(seconds=11)
        published = await relay_pending_outbox_events(
            batch_size=100,
            max_retries=5,
            base_backoff_seconds=10.0,
            max_backoff_seconds=60.0,
            now=t1,
        )
        assert published == 0
        assert attempts == 2

        # Poll at t1 + 15s (before 20s backoff elapses) -> must be skipped
        published = await relay_pending_outbox_events(
            batch_size=100,
            max_retries=5,
            base_backoff_seconds=10.0,
            max_backoff_seconds=60.0,
            now=t1 + timedelta(seconds=15),
        )
        assert published == 0
        assert attempts == 2

        # Poll at t1 + 21s -> attempt 3 runs and succeeds -> PUBLISHED
        t2 = t1 + timedelta(seconds=21)
        published = await relay_pending_outbox_events(
            batch_size=100,
            max_retries=5,
            base_backoff_seconds=10.0,
            max_backoff_seconds=60.0,
            now=t2,
        )
        assert published >= 1
        assert attempts == 3
        assert received_payloads == [{"order_id": "abc-123"}]

        async with async_session_factory() as session:
            row = await session.get(OutboxEventORM, event_id)
            assert row is not None
            assert row.status == "PUBLISHED"
            assert row.published_at is not None
            assert "_outbox_meta" not in row.payload
    finally:
        await _cleanup_outbox_events([event_id])


@pytest.mark.asyncio
async def test_exhausted_retries_transitions_to_terminal_failed_and_stops_retrying(
    isolated_outbox_handlers: None,
) -> None:
    """Once retry_count >= max_retries, event enters terminal FAILED state and stops retrying."""
    event_type = f"ExhaustedEvent_{uuid7().hex}"
    call_count = 0

    async def always_failing(event_id: UUID, payload: dict[str, Any]) -> None:
        nonlocal call_count
        call_count += 1
        raise RuntimeError(
            "permanent downstream error with secret redis://user:secretpass@host:6379"
        )

    register_outbox_handler(event_type, "test.always_failing", always_failing)
    event_id = await _seed_outbox_event(event_type=event_type, payload={"job": 42})

    try:
        for _ in range(5):
            await relay_pending_outbox_events(
                batch_size=100,
                max_retries=3,
                base_backoff_seconds=0.0,
            )

        assert call_count == 3

        async with async_session_factory() as session:
            row = await session.get(OutboxEventORM, event_id)
            assert row is not None
            assert row.status == "FAILED"
            assert row.retry_count == 3
            assert row.published_at is None
            meta = row.payload.get("_outbox_meta", {})
            assert meta.get("failure_code") == "MAX_RETRIES_EXCEEDED"
            assert "secretpass" not in str(meta.get("last_error", ""))
    finally:
        await _cleanup_outbox_events([event_id])


@pytest.mark.asyncio
async def test_aborted_pg_transaction_rolls_back_and_persists_retry_in_fresh_session(
    isolated_outbox_handlers: None,
) -> None:
    """An aborted PostgreSQL transaction must NEVER roll back retry_count or cause infinite retries."""
    event_type = f"AbortedTxEvent_{uuid7().hex}"
    handler_calls = 0

    async def ok_handler(event_id: UUID, payload: dict[str, Any]) -> None:
        nonlocal handler_calls
        handler_calls += 1

    register_outbox_handler(event_type, "test.ok_handler", ok_handler)
    event_id = await _seed_outbox_event(event_type=event_type, payload={"tx": "abort"})

    async def poison_session_mark_processed(
        self: SqlAlchemyOutboxRepository, event_id_arg: UUID, consumer_name: str
    ) -> None:
        # Execute invalid SQL directly on the relay's PostgreSQL session to genuinely abort the TX.
        await self._session.execute(text("SELECT 1 / 0"))

    try:
        with patch.object(
            SqlAlchemyOutboxRepository,
            "mark_event_processed",
            new=poison_session_mark_processed,
        ):
            # Attempt 1: PG aborts transaction -> relay rolls back & increments retry_count in fresh session
            await relay_pending_outbox_events(
                batch_size=100,
                max_retries=2,
                base_backoff_seconds=0.0,
            )
            async with async_session_factory() as session:
                row = await session.get(OutboxEventORM, event_id)
                assert row is not None
                assert row.retry_count == 1
                assert row.status == "PENDING"
                assert row.published_at is None

            # Attempt 2: PG aborts again -> relay transitions deterministically to FAILED
            await relay_pending_outbox_events(
                batch_size=100,
                max_retries=2,
                base_backoff_seconds=0.0,
            )
            async with async_session_factory() as session:
                row = await session.get(OutboxEventORM, event_id)
                assert row is not None
                assert row.retry_count == 2
                assert row.status == "FAILED"
                assert row.published_at is None
                meta = row.payload.get("_outbox_meta", {})
                assert meta.get("failure_code") == "MAX_RETRIES_EXCEEDED"

            # Attempt 3: must NOT be retried again (no infinite loop!)
            await relay_pending_outbox_events(
                batch_size=100,
                max_retries=2,
                base_backoff_seconds=0.0,
            )
            assert handler_calls == 2
    finally:
        await _cleanup_outbox_events([event_id])


@pytest.mark.asyncio
async def test_concurrent_relays_use_skip_locked_to_prevent_double_claiming(
    isolated_outbox_handlers: None,
) -> None:
    """Two concurrent relay workers with separate PG sessions must never double-claim pending rows."""
    event_type = f"ConcurrentMultiEvent_{uuid7().hex}"
    dispatched: list[UUID] = []

    async def slow_handler(event_id: UUID, payload: dict[str, Any]) -> None:
        await asyncio.sleep(0.12)
        dispatched.append(event_id)

    register_outbox_handler(event_type, "test.slow_multi", slow_handler)
    event_ids = [
        await _seed_outbox_event(event_type=event_type, payload={"idx": idx}) for idx in range(4)
    ]

    try:
        counts = await asyncio.gather(
            relay_pending_outbox_events(batch_size=10, max_retries=3),
            relay_pending_outbox_events(batch_size=10, max_retries=3),
        )
        assert len(dispatched) == 4
        assert set(dispatched) == set(event_ids)
        assert sum(counts) >= 4

        async with async_session_factory() as session:
            rows = (
                (
                    await session.execute(
                        select(OutboxEventORM).where(OutboxEventORM.id.in_(event_ids))
                    )
                )
                .scalars()
                .all()
            )
            assert len(rows) == 4
            assert all(r.status == "PUBLISHED" and r.published_at is not None for r in rows)
    finally:
        await _cleanup_outbox_events(event_ids)


@pytest.mark.asyncio
async def test_crash_window_redelivery_guarded_by_consumer_idempotency(
    isolated_outbox_handlers: None,
) -> None:
    """At-least-once crash window: if relay commit fails after dispatch, consumer processed_events
    prevents duplicate business side effects on redelivery."""
    event_type = f"CrashWindowEvent_{uuid7().hex}"
    consumer_name = "test.idempotent_downstream_consumer"
    business_side_effects: list[UUID] = []
    dispatch_count = 0

    async def idempotent_downstream_consumer(event_id: UUID) -> None:
        async with async_session_factory() as c_session:
            repo = SqlAlchemyOutboxRepository(c_session)
            if await repo.is_event_processed(event_id, consumer_name):
                return
            business_side_effects.append(event_id)
            await repo.mark_event_processed(event_id, consumer_name)
            await c_session.commit()

    async def dispatch_handler(event_id: UUID, payload: dict[str, Any]) -> None:
        nonlocal dispatch_count
        dispatch_count += 1
        await idempotent_downstream_consumer(event_id)

    register_outbox_handler(event_type, "test.dispatch_to_consumer", dispatch_handler)
    event_id = await _seed_outbox_event(event_type=event_type, payload={"amount": 100})

    try:
        # Simulate crash after handler ran by failing relay session.commit() once.
        commit_calls = 0
        orig_session_factory = async_session_factory

        class _CrashOnceSessionWrapper:
            def __init__(self, inner: Any) -> None:
                self._inner = inner

            async def __aenter__(self) -> Any:
                self._sess = await self._inner.__aenter__()
                orig_commit = self._sess.commit

                async def flaky_commit() -> None:
                    nonlocal commit_calls
                    commit_calls += 1
                    if commit_calls == 1:
                        raise RuntimeError("simulated crash before outbox PUBLISHED commit")
                    await orig_commit()

                self._sess.commit = flaky_commit
                return self._sess

            async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> Any:
                return await self._inner.__aexit__(exc_type, exc, tb)

        def flaky_factory() -> Any:
            return _CrashOnceSessionWrapper(orig_session_factory())

        # Run 1: handler executes (consumer runs side effect + records processed_events),
        # then relay commit crashes -> event stays PENDING with retry_count=1.
        await relay_pending_outbox_events(
            batch_size=10,
            max_retries=5,
            session_factory=flaky_factory,
            base_backoff_seconds=0.0,
        )
        assert dispatch_count == 1
        assert business_side_effects == [event_id]

        # Run 2: relay redelivers -> consumer sees processed_events and skips duplicate side effect.
        published = await relay_pending_outbox_events(
            batch_size=10,
            max_retries=5,
            base_backoff_seconds=0.0,
        )
        assert published >= 1
        assert dispatch_count == 2
        assert business_side_effects == [event_id]

        async with async_session_factory() as session:
            row = await session.get(OutboxEventORM, event_id)
            assert row is not None
            assert row.status == "PUBLISHED"
            pe = (
                await session.execute(
                    select(ProcessedEventORM).where(
                        ProcessedEventORM.event_id == event_id,
                        ProcessedEventORM.handler_name == consumer_name,
                    )
                )
            ).scalar_one_or_none()
            assert pe is not None
    finally:
        await _cleanup_outbox_events([event_id])


@pytest.mark.asyncio
async def test_real_redis_streams_broker_dispatch_and_unavailable_handling(
    isolated_outbox_handlers: None,
) -> None:
    """Real Redis 7 RedisStreamBroker integration: verifies real XADD push + broker-down retry."""
    stream_name = f"test:outbox_stream:{uuid7().hex}"
    group_name = f"test_group_{uuid7().hex}"
    real_broker = RedisStreamBroker(
        url=REDIS_URL,
        queue_name=stream_name,
        consumer_group_name=group_name,
    )

    @real_broker.task
    async def sample_redis_consumer(event_id: str, marker: str) -> str:
        return f"{event_id}:{marker}"

    ok_event_type = f"RealRedisOkEvent_{uuid7().hex}"
    down_event_type = f"RealRedisDownEvent_{uuid7().hex}"

    async def real_redis_handler(event_id: UUID, payload: dict[str, Any]) -> None:
        await sample_redis_consumer.kiq(event_id=str(event_id), marker=str(payload["marker"]))

    unreachable_broker = RedisStreamBroker(
        url="redis://127.0.0.1:6399",
        queue_name=f"test:unreachable:{uuid7().hex}",
        socket_connect_timeout=0.3,
        socket_timeout=0.3,
    )

    @unreachable_broker.task
    async def unreachable_consumer(event_id: str) -> None:
        return None

    async def unreachable_redis_handler(event_id: UUID, payload: dict[str, Any]) -> None:
        await unreachable_consumer.kiq(event_id=str(event_id))

    register_outbox_handler(ok_event_type, "test.real_redis_push", real_redis_handler)
    register_outbox_handler(
        down_event_type, "test.unreachable_redis_push", unreachable_redis_handler
    )

    ok_event_id = await _seed_outbox_event(
        event_type=ok_event_type,
        payload={"marker": "redis-streams-ok"},
    )
    down_event_id = await _seed_outbox_event(
        event_type=down_event_type,
        payload={"marker": "redis-down"},
    )

    redis_client = aioredis.from_url(REDIS_URL)
    try:
        await real_broker.startup()
        published = await relay_pending_outbox_events(
            batch_size=100,
            max_retries=5,
            base_backoff_seconds=10.0,
        )
        assert published >= 1

        # Verify message actually landed in Redis Stream!
        stream_len = await redis_client.xlen(stream_name)
        assert stream_len >= 1
        entries = await redis_client.xrange(stream_name, count=10)
        raw_blob = str(entries)
        assert str(ok_event_id) in raw_blob
        assert "redis-streams-ok" in raw_blob

        async with async_session_factory() as session:
            ok_row = await session.get(OutboxEventORM, ok_event_id)
            assert ok_row is not None
            assert ok_row.status == "PUBLISHED"
            assert ok_row.published_at is not None

            down_row = await session.get(OutboxEventORM, down_event_id)
            assert down_row is not None
            assert down_row.status == "PENDING"
            assert down_row.published_at is None
            assert down_row.retry_count == 1
            meta = down_row.payload.get("_outbox_meta", {})
            assert meta.get("next_retry_at") is not None
            assert meta.get("last_error")
    finally:
        await real_broker.shutdown()
        await unreachable_broker.shutdown()
        await redis_client.delete(stream_name)
        await redis_client.aclose()
        await _cleanup_outbox_events([ok_event_id, down_event_id])


@pytest.mark.asyncio
async def test_outbox_observability_metrics_snapshot(
    isolated_outbox_handlers: None,
) -> None:
    """collect_outbox_metrics must report pending, failed, oldest age, retries, and unknown handlers."""
    ok_type = f"MetricOkEvent_{uuid7().hex}"
    fail_type = f"MetricFailEvent_{uuid7().hex}"
    unknown_type = f"MetricUnknownEvent_{uuid7().hex}"

    async def ok_handler(event_id: UUID, payload: dict[str, Any]) -> None:
        return None

    async def fail_handler(event_id: UUID, payload: dict[str, Any]) -> None:
        raise RuntimeError("metric failure")

    register_outbox_handler(ok_type, "test.metric_ok", ok_handler)
    register_outbox_handler(fail_type, "test.metric_fail", fail_handler)

    now = datetime.now(UTC)
    ev_ok = await _seed_outbox_event(event_type=ok_type, payload={"a": 1}, created_at=now)
    ev_fail = await _seed_outbox_event(
        event_type=fail_type,
        payload={"b": 2},
        created_at=now - timedelta(seconds=120),
    )
    ev_unknown = await _seed_outbox_event(event_type=unknown_type, payload={"c": 3}, created_at=now)

    try:
        published = await relay_pending_outbox_events(
            batch_size=100,
            max_retries=5,
            base_backoff_seconds=30.0,
            now=now,
        )
        assert published >= 1

        async with async_session_factory() as session:
            metrics = await collect_outbox_metrics(session, now=now)
            assert metrics.pending_count >= 1
            assert metrics.failed_count >= 1
            assert metrics.oldest_pending_age_seconds is not None
            assert metrics.oldest_pending_age_seconds >= 115.0
            assert metrics.published_count >= 1
            assert metrics.dispatch_failures >= 1
            assert metrics.retry_attempts >= 1
            assert metrics.unknown_handler_events >= 1
    finally:
        await _cleanup_outbox_events([ev_ok, ev_fail, ev_unknown])
