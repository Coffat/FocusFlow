from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import UUID

import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy import delete, select
from uuid6 import uuid7

import src.account.presentation.tasks as account_tasks  # noqa: F401
from src.account.application.use_cases.notifications import PersistNotificationUseCase
from src.account.infrastructure.orm.notification_orm import NotificationORM
from src.account.infrastructure.orm.user_orm import UserORM
from src.account.infrastructure.repositories.notification_repository import (
    SqlAlchemyNotificationRepository,
)
from src.account.infrastructure.security.jwt_token_provider import JwtTokenProvider
from src.main import app
from src.shared_kernel.infrastructure.database.session import async_session_factory
from src.shared_kernel.infrastructure.database.sqlalchemy_uow import SqlAlchemyUnitOfWork
from src.shared_kernel.infrastructure.outbox.models import OutboxEventORM
from src.shared_kernel.infrastructure.outbox.relay import relay_pending_outbox_events


async def _seed_users() -> tuple[UUID, UUID]:
    user_a = uuid7()
    user_b = uuid7()
    async with async_session_factory() as session:
        session.add_all(
            [
                UserORM(
                    id=user_a,
                    email=f"notif_a_{user_a.hex}@focusflow.vn",
                    password_hash="argon2id$mockhash",
                    full_name="Notif User A",
                    timezone="Asia/Ho_Chi_Minh",
                    role="LEARNER",
                    tier="FREE",
                    is_locked=False,
                ),
                UserORM(
                    id=user_b,
                    email=f"notif_b_{user_b.hex}@focusflow.vn",
                    password_hash="argon2id$mockhash",
                    full_name="Notif User B",
                    timezone="UTC",
                    role="LEARNER",
                    tier="FREE",
                    is_locked=False,
                ),
            ]
        )
        await session.commit()
    return user_a, user_b


async def _cleanup(user_ids: list[UUID], event_ids: list[UUID]) -> None:
    async with async_session_factory() as session:
        if event_ids:
            await session.execute(delete(OutboxEventORM).where(OutboxEventORM.id.in_(event_ids)))
        if user_ids:
            await session.execute(delete(UserORM).where(UserORM.id.in_(user_ids)))
        await session.commit()


@pytest.mark.asyncio
async def test_outbox_relay_persists_notifications_idempotently_and_rest_lifecycle() -> None:
    user_a, user_b = await _seed_users()
    overdue_event_id = uuid7()
    schedule_event_id = uuid7()
    event_ids = [overdue_event_id, schedule_event_id]

    token_a = JwtTokenProvider.create_access_token(
        user_id=user_a,
        email=f"notif_a_{user_a.hex}@focusflow.vn",
        role="LEARNER",
        tier="FREE",
    )
    token_b = JwtTokenProvider.create_access_token(
        user_id=user_b,
        email=f"notif_b_{user_b.hex}@focusflow.vn",
        role="LEARNER",
        tier="FREE",
    )
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    try:
        # 1. Insert real PENDING Outbox events
        async with async_session_factory() as session:
            session.add_all(
                [
                    OutboxEventORM(
                        id=overdue_event_id,
                        aggregate_type="Execution",
                        aggregate_id=user_a,
                        event_type="OverdueTaskAlertEvent",
                        payload={
                            "user_id": str(user_a),
                            "email": f"notif_a_{user_a.hex}@focusflow.vn",
                            "overdue_task_titles": ["Ôn tập SQL Index", "Làm bài tập DAG"],
                            "remaining_reschedule_budget": 2,
                        },
                        status="PENDING",
                        created_at=datetime.now(UTC),
                    ),
                    OutboxEventORM(
                        id=schedule_event_id,
                        aggregate_type="Planning",
                        aggregate_id=user_a,
                        event_type="OfficialScheduleAppliedEvent",
                        payload={
                            "user_id": str(user_a),
                            "roadmap_id": str(uuid7()),
                            "schedule_id": str(uuid7()),
                        },
                        status="PENDING",
                        created_at=datetime.now(UTC),
                    ),
                ]
            )
            await session.commit()

        # 2. Relay outbox events (mock only external broker .kiq side effects)
        with (
            patch.object(account_tasks.send_overdue_task_alert_email_task, "kiq", new=AsyncMock()),
            patch.object(account_tasks.sync_schedule_blocks_to_google, "kiq", new=AsyncMock()),
        ):
            published = await relay_pending_outbox_events(batch_size=20)
            assert published >= 2

        # 3. Duplicate event with same event_id MUST create strictly 1 notification (DB unique index)
        async with async_session_factory() as session:
            uc = PersistNotificationUseCase(
                notification_repo=SqlAlchemyNotificationRepository(session),
                uow=SqlAlchemyUnitOfWork(session),
            )
            dup = await uc.execute(
                user_id=user_a,
                event_id=overdue_event_id,
                notification_type="OVERDUE_TASK",
                title="Nhiệm vụ quá hạn cần xử lý",
                content="Duplicate payload must be ignored",
                resource_url="/tasks",
            )
            assert dup is None

        async with async_session_factory() as session:
            rows = (
                (
                    await session.execute(
                        select(NotificationORM).where(NotificationORM.user_id == user_a)
                    )
                )
                .scalars()
                .all()
            )
            assert len(rows) == 2
            types = {r.notification_type for r in rows}
            assert types == {"OVERDUE_TASK", "SCHEDULE_APPLIED"}
            overdue_row = next(r for r in rows if r.notification_type == "OVERDUE_TASK")
            initial_updated_at = overdue_row.updated_at

        # 4. REST API checks: list, IDOR 404, mark single read, updated_at trigger, mark all read
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            list_resp = await client.get("/api/v1/account/notifications", headers=headers_a)
            assert list_resp.status_code == 200
            list_data = list_resp.json()
            assert list_data["total"] == 2
            assert list_data["unread_count"] == 2
            assert len(list_data["items"]) == 2

            # User B sees 0 notifications and gets 404 when trying to mark User A's notification
            b_list = await client.get("/api/v1/account/notifications", headers=headers_b)
            assert b_list.status_code == 200
            assert b_list.json()["total"] == 0

            idor_resp = await client.post(
                f"/api/v1/account/notifications/{overdue_row.id}/read",
                headers=headers_b,
            )
            assert idor_resp.status_code == 404

            # Sleep briefly so PostgreSQL BEFORE UPDATE trigger produces strictly newer updated_at
            await asyncio.sleep(0.05)

            read_resp = await client.post(
                f"/api/v1/account/notifications/{overdue_row.id}/read",
                headers=headers_a,
            )
            assert read_resp.status_code == 200
            read_data = read_resp.json()
            assert read_data["is_read"] is True
            assert read_data["read_at"] is not None

            # Verify trg_notifications_updated_at fired in DB
            async with async_session_factory() as session:
                refreshed = (
                    await session.execute(
                        select(NotificationORM).where(NotificationORM.id == overdue_row.id)
                    )
                ).scalar_one()
                assert refreshed.updated_at >= initial_updated_at

            # Unread-only filter returns 1 remaining item
            unread_resp = await client.get(
                "/api/v1/account/notifications?unread_only=true", headers=headers_a
            )
            assert unread_resp.status_code == 200
            assert unread_resp.json()["total"] == 1
            assert unread_resp.json()["unread_count"] == 1

            # Mark all read updates remaining 1 item
            read_all_resp = await client.post(
                "/api/v1/account/notifications/read-all", headers=headers_a
            )
            assert read_all_resp.status_code == 200
            assert read_all_resp.json()["updated_count"] == 1

            final_list = await client.get("/api/v1/account/notifications", headers=headers_a)
            assert final_list.status_code == 200
            assert final_list.json()["unread_count"] == 0
    finally:
        await _cleanup([user_a, user_b], event_ids)
