from __future__ import annotations

import asyncio
from collections.abc import Generator
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
from sqlalchemy import delete, select
from uuid6 import uuid7

import src.account.presentation.tasks as account_tasks
import src.planning.presentation.tasks as planning_tasks
from src.shared_kernel.infrastructure.database.session import async_session_factory
from src.shared_kernel.infrastructure.outbox.models import OutboxEventORM, ProcessedEventORM
from src.shared_kernel.infrastructure.outbox.relay import (
    clear_outbox_handlers,
    get_registered_outbox_handlers,
    register_outbox_handler,
    relay_pending_outbox_events,
)


@pytest.fixture
def isolated_outbox_handlers() -> Generator[None, None, None]:
    snapshot = {et: list(handlers) for et, handlers in get_registered_outbox_handlers().items()}
    clear_outbox_handlers()
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
    aggregate_type: str = "TestAggregate",
    aggregate_id: UUID | None = None,
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
                status="PENDING",
                retry_count=0,
                created_at=datetime.now(UTC),
                published_at=None,
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
async def test_outbox_relay_handler_failure_keeps_pending_and_increments_retry(
    isolated_outbox_handlers: None,
) -> None:
    event_type = f"TestFailEvent_{uuid7().hex}"

    async def failing_handler(event_id: UUID, payload: dict[str, Any]) -> None:
        raise RuntimeError("broker temporarily unreachable")

    register_outbox_handler(event_type, "test.failing_handler", failing_handler)
    event_id = await _seed_outbox_event(event_type=event_type, payload={"key": "val"})

    try:
        await relay_pending_outbox_events(batch_size=100, max_retries=5)

        async with async_session_factory() as session:
            row = await session.get(OutboxEventORM, event_id)
            assert row is not None
            assert row.status == "PENDING"
            assert row.published_at is None
            assert row.retry_count == 1
    finally:
        await _cleanup_outbox_events([event_id])


@pytest.mark.asyncio
async def test_outbox_relay_retry_succeeds_after_recovery(
    isolated_outbox_handlers: None,
) -> None:
    event_type = f"TestRecoverEvent_{uuid7().hex}"
    should_fail = True
    received: list[tuple[UUID, dict[str, Any]]] = []

    async def flaky_handler(event_id: UUID, payload: dict[str, Any]) -> None:
        if should_fail:
            raise ConnectionError("redis down")
        received.append((event_id, payload))

    register_outbox_handler(event_type, "test.flaky_handler", flaky_handler)
    event_id = await _seed_outbox_event(event_type=event_type, payload={"step": 1})

    try:
        await relay_pending_outbox_events(batch_size=100, max_retries=5, base_backoff_seconds=0.0)

        async with async_session_factory() as session:
            row = await session.get(OutboxEventORM, event_id)
            assert row is not None
            assert row.status == "PENDING"
            assert row.retry_count == 1
            assert row.published_at is None

        should_fail = False
        published = await relay_pending_outbox_events(
            batch_size=100, max_retries=5, base_backoff_seconds=0.0
        )
        assert published >= 1
        assert received == [(event_id, {"step": 1})]

        async with async_session_factory() as session:
            row = await session.get(OutboxEventORM, event_id)
            assert row is not None
            assert row.status == "PUBLISHED"
            assert row.published_at is not None

            pe = (
                await session.execute(
                    select(ProcessedEventORM).where(
                        ProcessedEventORM.event_id == event_id,
                        ProcessedEventORM.handler_name == "test.flaky_handler",
                    )
                )
            ).scalar_one_or_none()
            assert pe is not None
    finally:
        await _cleanup_outbox_events([event_id])


@pytest.mark.asyncio
async def test_outbox_relay_marks_failed_after_max_retries(
    isolated_outbox_handlers: None,
) -> None:
    event_type = f"TestMaxRetryEvent_{uuid7().hex}"

    async def always_fail(event_id: UUID, payload: dict[str, Any]) -> None:
        raise RuntimeError("permanent broker failure")

    register_outbox_handler(event_type, "test.always_fail", always_fail)
    event_id = await _seed_outbox_event(event_type=event_type, payload={"x": 1})

    try:
        for attempt in range(1, 4):
            await relay_pending_outbox_events(
                batch_size=100, max_retries=3, base_backoff_seconds=0.0
            )
            async with async_session_factory() as session:
                row = await session.get(OutboxEventORM, event_id)
                assert row is not None
                assert row.retry_count == attempt
                assert row.published_at is None
                if attempt < 3:
                    assert row.status == "PENDING"
                else:
                    assert row.status == "FAILED"
    finally:
        await _cleanup_outbox_events([event_id])


@pytest.mark.asyncio
async def test_outbox_relay_multi_handler_partial_failure_is_idempotent_on_retry(
    isolated_outbox_handlers: None,
) -> None:
    event_type = f"TestPartialFailEvent_{uuid7().hex}"
    handler_a_calls = 0
    handler_b_calls = 0
    fail_b = True

    async def handler_a(event_id: UUID, payload: dict[str, Any]) -> None:
        nonlocal handler_a_calls
        handler_a_calls += 1

    async def handler_b(event_id: UUID, payload: dict[str, Any]) -> None:
        nonlocal handler_b_calls
        handler_b_calls += 1
        if fail_b:
            raise RuntimeError("handler B failed on attempt 1")

    register_outbox_handler(event_type, "test.handler_a", handler_a)
    register_outbox_handler(event_type, "test.handler_b", handler_b)
    event_id = await _seed_outbox_event(event_type=event_type, payload={"multi": True})

    try:
        await relay_pending_outbox_events(batch_size=100, max_retries=5, base_backoff_seconds=0.0)
        assert handler_a_calls == 1
        assert handler_b_calls == 1

        async with async_session_factory() as session:
            row = await session.get(OutboxEventORM, event_id)
            assert row is not None
            assert row.status == "PENDING"
            assert row.retry_count == 1
            assert row.published_at is None

        fail_b = False
        await relay_pending_outbox_events(batch_size=100, max_retries=5, base_backoff_seconds=0.0)
        assert handler_a_calls == 1, "Handler A must not be re-executed on retry"
        assert handler_b_calls == 2

        async with async_session_factory() as session:
            row = await session.get(OutboxEventORM, event_id)
            assert row is not None
            assert row.status == "PUBLISHED"
            assert row.published_at is not None
    finally:
        await _cleanup_outbox_events([event_id])


@pytest.mark.asyncio
async def test_outbox_relay_concurrent_sessions_dispatch_strictly_once(
    isolated_outbox_handlers: None,
) -> None:
    event_type = f"TestConcurrentEvent_{uuid7().hex}"
    dispatched_ids: list[UUID] = []

    async def slow_handler(event_id: UUID, payload: dict[str, Any]) -> None:
        await asyncio.sleep(0.15)
        dispatched_ids.append(event_id)

    register_outbox_handler(event_type, "test.slow_handler", slow_handler)
    event_id = await _seed_outbox_event(event_type=event_type, payload={"concurrent": True})

    try:
        results = await asyncio.gather(
            relay_pending_outbox_events(batch_size=100, max_retries=5),
            relay_pending_outbox_events(batch_size=100, max_retries=5),
        )
        assert dispatched_ids == [event_id]
        assert sum(results) >= 1

        async with async_session_factory() as session:
            row = await session.get(OutboxEventORM, event_id)
            assert row is not None
            assert row.status == "PUBLISHED"
            assert row.published_at is not None
    finally:
        await _cleanup_outbox_events([event_id])


@pytest.mark.asyncio
async def test_registered_context_handlers_dispatch_cleanly() -> None:
    handlers = get_registered_outbox_handlers()
    assert any(
        name == "account.overdue_task_alert_email"
        for name, _ in handlers.get("OverdueTaskAlertEvent", [])
    )
    assert any(
        name == "account.sync_schedule_blocks_to_google"
        for name, _ in handlers.get("OfficialScheduleAppliedEvent", [])
    )
    assert any(
        name == "planning.availability_updated_dispatch"
        for name, _ in handlers.get("AvailabilityUpdatedEvent", [])
    )

    user_id = uuid7()
    overdue_event_id = await _seed_outbox_event(
        event_type="OverdueTaskAlertEvent",
        aggregate_type="User",
        aggregate_id=user_id,
        payload={
            "user_id": str(user_id),
            "email": "learner@example.com",
            "overdue_task_titles": ["Task 1", "Task 2"],
            "remaining_reschedule_budget": 2,
        },
    )
    avail_event_id = await _seed_outbox_event(
        event_type="AvailabilityUpdatedEvent",
        aggregate_type="AvailabilityProfile",
        aggregate_id=user_id,
        payload={
            "user_id": str(user_id),
            "availability_mode": "MODE_B",
        },
    )

    try:
        overdue_kiq = AsyncMock()
        avail_kiq = AsyncMock()
        with (
            patch.object(account_tasks.send_overdue_task_alert_email_task, "kiq", overdue_kiq),
            patch.object(planning_tasks.consume_availability_updated_event, "kiq", avail_kiq),
        ):
            published = await relay_pending_outbox_events(batch_size=100, max_retries=5)
            assert published >= 2

        overdue_kiq.assert_awaited_once_with(
            email="learner@example.com",
            overdue_task_titles=["Task 1", "Task 2"],
            remaining_reschedule_budget=2,
            event_id=str(overdue_event_id),
        )
        avail_kiq.assert_awaited_once_with(
            event_id=str(avail_event_id),
            user_id=str(user_id),
            availability_mode="MODE_B",
        )

        async with async_session_factory() as session:
            ev1 = await session.get(OutboxEventORM, overdue_event_id)
            ev2 = await session.get(OutboxEventORM, avail_event_id)
            assert ev1 is not None and ev1.status == "PUBLISHED" and ev1.published_at is not None
            assert ev2 is not None and ev2.status == "PUBLISHED" and ev2.published_at is not None
    finally:
        await _cleanup_outbox_events([overdue_event_id, avail_event_id])


@pytest.mark.asyncio
async def test_overdue_alert_email_worker_duplicate_delivery_sends_strictly_once() -> None:
    from src.account.infrastructure.email.email_service import EmailService

    event_id = await _seed_outbox_event(
        event_type="OverdueTaskAlertEvent",
        aggregate_type="User",
        aggregate_id=uuid7(),
        payload={"email": "dedup@focusflow.test"},
    )
    send_mock = AsyncMock()
    try:
        with patch.object(EmailService, "send_overdue_alert_email", send_mock):
            await account_tasks.send_overdue_task_alert_email_task(
                email="dedup@focusflow.test",
                overdue_task_titles=["Task A"],
                remaining_reschedule_budget=2,
                event_id=str(event_id),
            )
            # Duplicate broker delivery with the exact same event_id must be ignored.
            await account_tasks.send_overdue_task_alert_email_task(
                email="dedup@focusflow.test",
                overdue_task_titles=["Task A"],
                remaining_reschedule_budget=2,
                event_id=str(event_id),
            )

        send_mock.assert_awaited_once_with(
            to_email="dedup@focusflow.test",
            overdue_task_titles=["Task A"],
            remaining_reschedule_budget=2,
            raise_on_error=True,
        )

        async with async_session_factory() as session:
            pe = (
                await session.execute(
                    select(ProcessedEventORM).where(
                        ProcessedEventORM.event_id == event_id,
                        ProcessedEventORM.handler_name == "account.overdue_task_alert_email_worker",
                    )
                )
            ).scalar_one_or_none()
            assert pe is not None
    finally:
        await _cleanup_outbox_events([event_id])
