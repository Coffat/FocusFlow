from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select
from uuid6 import uuid7

import src.account.presentation.tasks as account_tasks
from src.account.infrastructure.orm.user_orm import LearnerProfileORM, UserORM
from src.account.infrastructure.security.jwt_token_provider import JwtTokenProvider
from src.execution.application.use_cases.session_use_cases import FinalizeStudySessionUseCase
from src.execution.domain.models.study_session import StudySession
from src.execution.infrastructure.orm.session_orm import StudySessionORM
from src.execution.infrastructure.repositories.sqlalchemy_study_session_repository import (
    SqlAlchemyStudySessionRepository,
)
from src.execution.infrastructure.repositories.sqlalchemy_task_repository import (
    SqlAlchemyTaskRepository,
)
from src.main import app
from src.planning.infrastructure.orm.planning_orm import GoalORM, RoadmapORM
from src.planning.public_api import create_planning_execution_bridge
from src.shared_kernel.infrastructure.database.session import async_session_factory
from src.shared_kernel.infrastructure.database.sqlalchemy_uow import SqlAlchemyUnitOfWork
from src.shared_kernel.infrastructure.outbox.models import OutboxEventORM, ProcessedEventORM
from src.shared_kernel.infrastructure.outbox.relay import (
    clear_outbox_handlers,
    get_registered_outbox_handlers,
    register_outbox_handler,
    relay_pending_outbox_events,
)


@pytest.fixture
def preserved_outbox_handlers() -> Generator[None, None, None]:
    snapshot = {et: list(handlers) for et, handlers in get_registered_outbox_handlers().items()}
    try:
        yield
    finally:
        clear_outbox_handlers()
        for et, handlers in snapshot.items():
            for name, fn in handlers:
                register_outbox_handler(et, name, fn)


async def _seed_user_and_roadmap(
    *,
    timezone: str = "Asia/Ho_Chi_Minh",
) -> tuple[UUID, UUID]:
    user_id = uuid7()
    goal_id = uuid7()
    roadmap_id = uuid7()
    now = datetime.now(UTC)

    async with async_session_factory() as session:
        session.add(
            UserORM(
                id=user_id,
                email=f"srl_test_{user_id.hex}@focusflow.vn",
                password_hash="argon2id$mockhash",
                full_name="SRL Learner",
                timezone=timezone,
                role="LEARNER",
                tier="FREE",
                is_locked=False,
            )
        )
        await session.flush()
        session.add(
            GoalORM(
                id=goal_id,
                user_id=user_id,
                title="SRL Mastery Goal",
                status="ACTIVE",
                created_at=now,
                updated_at=now,
            )
        )
        await session.flush()
        session.add(
            RoadmapORM(
                id=roadmap_id,
                user_id=user_id,
                goal_id=goal_id,
                title="SRL Roadmap",
                status="ACTIVE",
                start_date=now.date(),
                target_date=now.date() + timedelta(days=30),
                created_at=now,
                updated_at=now,
            )
        )
        await session.commit()

    return user_id, roadmap_id


async def _seed_completed_session(
    *,
    user_id: UUID,
    roadmap_id: UUID,
    started_at_utc: datetime,
    planned_minutes: int,
    actual_minutes: int,
    status: str = "COMPLETED",
) -> UUID:
    sess_id = uuid7()
    async with async_session_factory() as session:
        session.add(
            StudySessionORM(
                id=sess_id,
                user_id=user_id,
                roadmap_id=roadmap_id,
                started_at=started_at_utc,
                ended_at=started_at_utc + timedelta(minutes=actual_minutes),
                planned_minutes=planned_minutes,
                actual_minutes=actual_minutes,
                status=status,
                last_heartbeat_at=started_at_utc + timedelta(minutes=actual_minutes),
                session_mode="STANDARD",
                pending_takeaway=False,
                created_at=started_at_utc,
                updated_at=started_at_utc,
            )
        )
        await session.commit()
    return sess_id


async def _cleanup_user(user_id: UUID, outbox_ids: list[UUID] | None = None) -> None:
    async with async_session_factory() as session:
        if outbox_ids:
            await session.execute(
                delete(ProcessedEventORM).where(ProcessedEventORM.event_id.in_(outbox_ids))
            )
            await session.execute(delete(OutboxEventORM).where(OutboxEventORM.id.in_(outbox_ids)))
        await session.execute(delete(UserORM).where(UserORM.id == user_id))
        await session.commit()


@pytest.mark.asyncio
async def test_srl_profile_cold_start_hides_fake_defaults_on_profile_api() -> None:
    user_id, roadmap_id = await _seed_user_and_roadmap(timezone="Asia/Ho_Chi_Minh")
    now = datetime(2026, 5, 10, 2, 0, tzinfo=UTC)  # 09:00 Asia/Ho_Chi_Minh (MORNING)

    try:
        # Only 2 sessions (< 3 required for non-cold-start)
        await _seed_completed_session(
            user_id=user_id,
            roadmap_id=roadmap_id,
            started_at_utc=now - timedelta(days=2),
            planned_minutes=30,
            actual_minutes=35,
        )
        await _seed_completed_session(
            user_id=user_id,
            roadmap_id=roadmap_id,
            started_at_utc=now - timedelta(days=1),
            planned_minutes=45,
            actual_minutes=50,
        )

        executed = await account_tasks.aggregate_learner_srl_profile(
            user_id=str(user_id),
            session_factory=async_session_factory,
        )
        assert executed is True

        async with async_session_factory() as session:
            row = (
                await session.execute(
                    select(LearnerProfileORM).where(LearnerProfileORM.user_id == user_id)
                )
            ).scalar_one_or_none()
            assert row is not None
            assert row.is_cold_start is True
            assert row.total_completed_sessions == 2
            assert row.optimal_focus_duration_mins == 25
            assert row.estimation_bias_factor == Decimal("1.00")

        token = JwtTokenProvider().create_access_token(
            user_id=user_id,
            email=f"srl_test_{user_id.hex}@focusflow.vn",
            role="LEARNER",
            tier="FREE",
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/api/v1/account/profile",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["srl_profile"] is not None
            assert body["srl_profile"]["is_cold_start"] is True
            assert body["srl_profile"]["total_completed_sessions"] == 2
            assert body["srl_profile"]["min_sessions_required"] == 3
            assert body["srl_profile"]["optimal_focus_duration_mins"] is None
            assert body["srl_profile"]["estimation_bias_factor"] is None
            assert body["srl_profile"]["peak_productivity_slots"] == []
    finally:
        await _cleanup_user(user_id)


@pytest.mark.asyncio
async def test_srl_full_pipeline_outbox_relay_to_profile_api(
    preserved_outbox_handlers: None,
) -> None:
    user_id, roadmap_id = await _seed_user_and_roadmap(timezone="Asia/Ho_Chi_Minh")
    outbox_ids: list[UUID] = []

    try:
        # Seed 2 historical completed sessions in MORNING (09:00 ICT = 02:00 UTC) and EVENING (20:00 ICT = 13:00 UTC)
        await _seed_completed_session(
            user_id=user_id,
            roadmap_id=roadmap_id,
            started_at_utc=datetime(2026, 5, 1, 2, 0, tzinfo=UTC),  # 09:00 ICT -> MORNING
            planned_minutes=30,
            actual_minutes=30,  # ratio = 1.00
        )
        await _seed_completed_session(
            user_id=user_id,
            roadmap_id=roadmap_id,
            started_at_utc=datetime(2026, 5, 2, 2, 30, tzinfo=UTC),  # 09:30 ICT -> MORNING
            planned_minutes=40,
            actual_minutes=50,  # ratio = 1.25
        )

        # 3rd session finalized through FinalizeStudySessionUseCase -> emits StudySessionCompletedEvent to outbox
        sess3_start = datetime(2026, 5, 3, 13, 0, tzinfo=UTC)  # 20:00 ICT -> EVENING
        sess3_end = sess3_start + timedelta(minutes=60)  # actual 60, planned 40 -> ratio 1.50
        sess3_id = uuid7()
        async with async_session_factory() as session:
            session.add(
                StudySessionORM(
                    id=sess3_id,
                    user_id=user_id,
                    roadmap_id=roadmap_id,
                    started_at=sess3_start,
                    ended_at=None,
                    planned_minutes=40,
                    actual_minutes=60,
                    status="IN_PROGRESS",
                    last_heartbeat_at=sess3_end,
                    session_mode="STANDARD",
                    pending_takeaway=False,
                    created_at=sess3_start,
                    updated_at=sess3_start,
                )
            )
            await session.commit()

        async with async_session_factory() as session:
            finalize_uc = FinalizeStudySessionUseCase(
                session_repo=SqlAlchemyStudySessionRepository(session),
                task_repo=SqlAlchemyTaskRepository(session),
                planning_bridge=create_planning_execution_bridge(session),
                uow=SqlAlchemyUnitOfWork(session),
            )
            await finalize_uc.execute(
                user_id=user_id,
                session_id=sess3_id,
                actual_minutes=60,
                takeaway="Learned distributed consensus and Raft leader election.",
                now=sess3_end,
            )

        # Verify StudySessionCompletedEvent is in outbox_events
        async with async_session_factory() as session:
            ev = (
                await session.execute(
                    select(OutboxEventORM).where(
                        OutboxEventORM.aggregate_id == sess3_id,
                        OutboxEventORM.event_type == "StudySessionCompletedEvent",
                    )
                )
            ).scalar_one_or_none()
            assert ev is not None
            assert ev.status == "PENDING"
            outbox_ids.append(ev.id)

        # Relay outbox -> dispatches aggregate_learner_srl_profile.kiq(...)
        dispatched: list[dict[str, Any]] = []

        async def _capture_kiq(**kwargs: Any) -> None:
            dispatched.append(dict(kwargs))

        with patch.object(
            account_tasks.aggregate_learner_srl_profile,
            "kiq",
            new=AsyncMock(side_effect=_capture_kiq),
        ):
            await relay_pending_outbox_events(batch_size=100, session_factory=async_session_factory)

        matching = [d for d in dispatched if d.get("user_id") == str(user_id)]
        assert len(matching) == 1
        event_id_str = matching[0]["event_id"]
        assert event_id_str == str(outbox_ids[0])

        # Execute the worker directly
        first_run = await account_tasks.aggregate_learner_srl_profile(
            user_id=str(user_id),
            event_id=event_id_str,
            session_factory=async_session_factory,
        )
        assert first_run is True

        # Duplicate delivery with same event_id must be skipped via processed_events
        duplicate_run = await account_tasks.aggregate_learner_srl_profile(
            user_id=str(user_id),
            event_id=event_id_str,
            session_factory=async_session_factory,
        )
        assert duplicate_run is False

        # Verify persisted learner_profiles & GET /api/v1/account/profile
        # Durations: [30, 50, 60] -> median = 50
        # Ratios: [1.00, 1.25, 1.50] -> mean = 1.25
        # Slots: MORNING (2), EVENING (1) -> ["MORNING", "EVENING"]
        token = JwtTokenProvider().create_access_token(
            user_id=user_id,
            email=f"srl_test_{user_id.hex}@focusflow.vn",
            role="LEARNER",
            tier="FREE",
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/api/v1/account/profile",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200
            srl = resp.json()["srl_profile"]
            assert srl["is_cold_start"] is False
            assert srl["total_completed_sessions"] == 3
            assert srl["optimal_focus_duration_mins"] == 50
            assert srl["estimation_bias_factor"] == pytest.approx(1.25)
            assert srl["peak_productivity_slots"] == ["MORNING", "EVENING"]
            assert srl["last_aggregated_at"] is not None
    finally:
        await _cleanup_user(user_id, outbox_ids=outbox_ids)


@pytest.mark.asyncio
async def test_srl_worker_failure_does_not_mark_processed_events_and_recovers_on_retry() -> None:
    user_id, roadmap_id = await _seed_user_and_roadmap(timezone="UTC")
    fake_event_id = uuid7()

    async with async_session_factory() as session:
        session.add(
            OutboxEventORM(
                id=fake_event_id,
                aggregate_type="StudySession",
                aggregate_id=uuid7(),
                event_type="StudySessionCompletedEvent",
                payload={"user_id": str(user_id)},
                status="PUBLISHED",
                retry_count=0,
                created_at=datetime.now(UTC),
                published_at=datetime.now(UTC),
            )
        )
        await session.commit()

    try:
        for i in range(3):
            await _seed_completed_session(
                user_id=user_id,
                roadmap_id=roadmap_id,
                started_at_utc=datetime(2026, 5, 1 + i, 10, 0, tzinfo=UTC),
                planned_minutes=45,
                actual_minutes=45,
            )

        with patch(
            "src.account.application.use_cases.profile.aggregate_srl_profile_use_case.AggregateSrlProfileUseCase.execute",
            new=AsyncMock(side_effect=RuntimeError("transient db error")),
        ):
            with pytest.raises(RuntimeError, match="transient db error"):
                await account_tasks.aggregate_learner_srl_profile(
                    user_id=str(user_id),
                    event_id=str(fake_event_id),
                    session_factory=async_session_factory,
                )

        # Ensure processed_events was NOT marked on failure
        async with async_session_factory() as session:
            pe = (
                await session.execute(
                    select(ProcessedEventORM).where(
                        ProcessedEventORM.event_id == fake_event_id,
                        ProcessedEventORM.handler_name
                        == "account.aggregate_learner_srl_profile_worker",
                    )
                )
            ).scalar_one_or_none()
            assert pe is None

        # Retry succeeds and persists learner_profiles
        recovered = await account_tasks.aggregate_learner_srl_profile(
            user_id=str(user_id),
            event_id=str(fake_event_id),
            session_factory=async_session_factory,
        )
        assert recovered is True

        async with async_session_factory() as session:
            profile_row = (
                await session.execute(
                    select(LearnerProfileORM).where(LearnerProfileORM.user_id == user_id)
                )
            ).scalar_one_or_none()
            assert profile_row is not None
            assert profile_row.is_cold_start is False
            assert profile_row.optimal_focus_duration_mins == 45
            assert profile_row.estimation_bias_factor == Decimal("1.00")
    finally:
        await _cleanup_user(user_id, outbox_ids=[fake_event_id])
        # Keep unused import clean
        assert StudySession is not None
