from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy import delete
from taskiq.schedule_sources import LabelScheduleSource
from uuid6 import uuid7

import src.account.presentation.tasks as account_tasks  # noqa: F401
import src.shared_kernel.infrastructure.outbox.relay as outbox_relay  # noqa: F401
from src.account.infrastructure.orm.user_orm import (
    AIQuotaORM,
    AIQuotaReservationORM,
    UserORM,
)
from src.account.presentation.tasks import sweep_expired_ai_quota_reservations
from src.shared_kernel.infrastructure.database.session import async_session_factory
from src.shared_kernel.infrastructure.worker.broker import broker


async def _create_user_and_quota(
    *,
    reserved_calls: int,
    used_calls: int = 0,
) -> tuple[UUID, UUID]:
    user_id = uuid7()
    quota_id = uuid7()
    now = datetime.now(UTC)
    async with async_session_factory() as session:
        session.add(
            UserORM(
                id=user_id,
                email=f"sweeper_{user_id.hex}@focusflow.vn",
                password_hash="argon2id$mockhash",
                full_name="Sweeper Test Learner",
                timezone="Asia/Ho_Chi_Minh",
                role="LEARNER",
                tier="FREE",
                is_locked=False,
            )
        )
        await session.flush()
        session.add(
            AIQuotaORM(
                id=quota_id,
                user_id=user_id,
                free_credits_remaining=30,
                paid_credits_remaining=0,
                used_calls=used_calls,
                reserved_calls=reserved_calls,
                tokens_consumed=0,
                cycle_start=now,
                cycle_end=now + timedelta(days=30),
            )
        )
        await session.commit()
    return user_id, quota_id


async def _cleanup_user(user_id: UUID) -> None:
    async with async_session_factory() as session:
        await session.execute(delete(UserORM).where(UserORM.id == user_id))
        await session.commit()


@pytest.mark.asyncio
async def test_sweeper_expires_stale_reservation_and_refunds_once() -> None:
    now = datetime.now(UTC)
    user_id, quota_id = await _create_user_and_quota(reserved_calls=2)
    stale_id = uuid7()
    fresh_id = uuid7()

    async with async_session_factory() as session:
        session.add_all(
            [
                AIQuotaReservationORM(
                    id=stale_id,
                    quota_id=quota_id,
                    user_id=user_id,
                    operation_type="ROADMAP_GEN",
                    status="RESERVED",
                    tokens_reserved=1,
                    expires_at=now - timedelta(seconds=30),
                    created_at=now - timedelta(minutes=3),
                    resolved_at=None,
                ),
                AIQuotaReservationORM(
                    id=fresh_id,
                    quota_id=quota_id,
                    user_id=user_id,
                    operation_type="ROADMAP_GEN",
                    status="RESERVED",
                    tokens_reserved=1,
                    expires_at=now + timedelta(minutes=5),
                    created_at=now,
                    resolved_at=None,
                ),
            ]
        )
        await session.commit()

    try:
        expired_count = await sweep_expired_ai_quota_reservations(now=now)
        assert expired_count >= 1

        async with async_session_factory() as session:
            stale_row = await session.get(AIQuotaReservationORM, stale_id)
            fresh_row = await session.get(AIQuotaReservationORM, fresh_id)
            quota_row = await session.get(AIQuotaORM, quota_id)

            assert stale_row is not None
            assert stale_row.status == "EXPIRED"
            assert stale_row.resolved_at is not None

            assert fresh_row is not None
            assert fresh_row.status == "RESERVED"
            assert fresh_row.resolved_at is None

            assert quota_row is not None
            assert quota_row.reserved_calls == 1

        # Second sweep must be a no-op for the already-expired row
        await sweep_expired_ai_quota_reservations(now=now)
        async with async_session_factory() as session:
            quota_row = await session.get(AIQuotaORM, quota_id)
            assert quota_row is not None
            assert quota_row.reserved_calls == 1
    finally:
        await _cleanup_user(user_id)


@pytest.mark.asyncio
async def test_sweeper_leaves_committed_and_released_reservations_untouched() -> None:
    now = datetime.now(UTC)
    user_id, quota_id = await _create_user_and_quota(reserved_calls=0, used_calls=1)
    committed_id = uuid7()
    released_id = uuid7()
    resolved_at = now - timedelta(minutes=1)

    async with async_session_factory() as session:
        session.add_all(
            [
                AIQuotaReservationORM(
                    id=committed_id,
                    quota_id=quota_id,
                    user_id=user_id,
                    operation_type="ROADMAP_GEN",
                    status="COMMITTED",
                    tokens_reserved=1,
                    expires_at=now - timedelta(minutes=5),
                    created_at=now - timedelta(minutes=10),
                    resolved_at=resolved_at,
                ),
                AIQuotaReservationORM(
                    id=released_id,
                    quota_id=quota_id,
                    user_id=user_id,
                    operation_type="ROADMAP_GEN",
                    status="RELEASED",
                    tokens_reserved=1,
                    expires_at=now - timedelta(minutes=5),
                    created_at=now - timedelta(minutes=10),
                    resolved_at=resolved_at,
                ),
            ]
        )
        await session.commit()

    try:
        await sweep_expired_ai_quota_reservations(now=now)

        async with async_session_factory() as session:
            committed_row = await session.get(AIQuotaReservationORM, committed_id)
            released_row = await session.get(AIQuotaReservationORM, released_id)
            quota_row = await session.get(AIQuotaORM, quota_id)

            assert committed_row is not None and committed_row.status == "COMMITTED"
            assert released_row is not None and released_row.status == "RELEASED"
            assert quota_row is not None
            assert quota_row.reserved_calls == 0
            assert quota_row.used_calls == 1
    finally:
        await _cleanup_user(user_id)


@pytest.mark.asyncio
async def test_sweeper_concurrent_executions_refund_strictly_once() -> None:
    now = datetime.now(UTC)
    stale_count = 3
    user_id, quota_id = await _create_user_and_quota(reserved_calls=stale_count)
    res_ids = [uuid7() for _ in range(stale_count)]

    async with async_session_factory() as session:
        for res_id in res_ids:
            session.add(
                AIQuotaReservationORM(
                    id=res_id,
                    quota_id=quota_id,
                    user_id=user_id,
                    operation_type="ROADMAP_GEN",
                    status="RESERVED",
                    tokens_reserved=1,
                    expires_at=now - timedelta(seconds=60),
                    created_at=now - timedelta(minutes=5),
                    resolved_at=None,
                )
            )
        await session.commit()

    try:
        results = await asyncio.gather(
            sweep_expired_ai_quota_reservations(now=now),
            sweep_expired_ai_quota_reservations(now=now),
            sweep_expired_ai_quota_reservations(now=now),
        )
        assert sum(results) == stale_count

        async with async_session_factory() as session:
            quota_row = await session.get(AIQuotaORM, quota_id)
            assert quota_row is not None
            assert quota_row.reserved_calls == 0

            for res_id in res_ids:
                row = await session.get(AIQuotaReservationORM, res_id)
                assert row is not None
                assert row.status == "EXPIRED"
                assert row.resolved_at is not None
    finally:
        await _cleanup_user(user_id)


@pytest.mark.asyncio
async def test_runtime_scheduler_registers_quota_sweeper_and_outbox_relay() -> None:
    source = LabelScheduleSource(broker)
    await source.startup()
    schedules = await source.get_schedules()
    by_task = {s.task_name: s.cron for s in schedules}

    sweeper_matches = [
        cron
        for task_name, cron in by_task.items()
        if "sweep_expired_ai_quota_reservations" in task_name
    ]
    relay_matches = [
        cron for task_name, cron in by_task.items() if "relay_pending_outbox_events" in task_name
    ]

    assert "* * * * *" in sweeper_matches
    assert "* * * * *" in relay_matches
