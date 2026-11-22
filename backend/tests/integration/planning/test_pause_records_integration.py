from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy import delete, select
from uuid6 import uuid7

import src.account.infrastructure.orm  # noqa: F401
import src.evaluation.infrastructure.orm  # noqa: F401
import src.execution.infrastructure.orm  # noqa: F401
import src.planning.infrastructure.orm  # noqa: F401
import src.shared_kernel.infrastructure.outbox.models  # noqa: F401
import src.shared_kernel.infrastructure.workflow.models  # noqa: F401
from src.account.infrastructure.orm.user_orm import UserORM
from src.evaluation.infrastructure.adapters.pause_record_adapter import PauseRecordAdapter
from src.evaluation.infrastructure.orm.pause_record_orm import PauseRecordORM
from src.evaluation.public_api import PauseRecordDTO, PauseRecordPort, create_pause_record_port
from src.planning.application.use_cases.roadmap_management_use_cases import (
    PauseRoadmapUseCase,
    ResumeRoadmapUseCase,
)
from src.planning.infrastructure.orm.planning_orm import GoalORM, RoadmapORM
from src.planning.infrastructure.repositories.planning_repositories import (
    SqlAlchemyGoalRepository,
    SqlAlchemyOfficialScheduleRepository,
    SqlAlchemyRoadmapRepository,
)
from src.shared_kernel.infrastructure.database.session import Base, async_session_factory
from src.shared_kernel.infrastructure.database.sqlalchemy_uow import SqlAlchemyUnitOfWork


async def _seed_active_roadmap() -> tuple[UUID, UUID, UUID]:
    user_id = uuid7()
    goal_id = uuid7()
    roadmap_id = uuid7()
    now = datetime.now(UTC)
    start_d = now.date()
    target_d = start_d + timedelta(days=30)

    async with async_session_factory() as session:
        session.add(
            UserORM(
                id=user_id,
                email=f"pause_test_{user_id.hex}@focusflow.vn",
                password_hash="argon2id$mockhash",
                full_name="Pause Test Learner",
                timezone="Asia/Ho_Chi_Minh",
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
                title="Master System Design",
                target_date=target_d,
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
                title="System Design Roadmap",
                status="ACTIVE",
                start_date=start_d,
                target_date=target_d,
                created_at=now,
                updated_at=now,
            )
        )
        await session.commit()

    return user_id, goal_id, roadmap_id


async def _cleanup_user(user_id: UUID) -> None:
    async with async_session_factory() as session:
        await session.execute(delete(UserORM).where(UserORM.id == user_id))
        await session.commit()


def test_base_metadata_registers_all_36_application_tables() -> None:
    """Base.metadata must contain pause_records, notifications, and all 36 FocusFlow application tables."""
    tables = set(Base.metadata.tables.keys())
    assert "pause_records" in tables
    assert "notifications" in tables
    assert len(tables) == 36, f"Expected 36 application tables in Base.metadata, got {len(tables)}"


@pytest.mark.asyncio
async def test_pause_and_resume_lifecycle_writes_and_completes_pause_record() -> None:
    user_id, _, roadmap_id = await _seed_active_roadmap()
    pause_time = datetime(2026, 5, 1, 9, 0, tzinfo=UTC)
    resume_time = datetime(2026, 5, 4, 10, 0, tzinfo=UTC)

    try:
        async with async_session_factory() as session:
            pause_uc = PauseRoadmapUseCase(
                roadmap_repo=SqlAlchemyRoadmapRepository(session),
                schedule_repo=SqlAlchemyOfficialScheduleRepository(session),
                uow=SqlAlchemyUnitOfWork(session),
                pause_record_port=create_pause_record_port(session),
            )
            paused = await pause_uc.execute(
                user_id=user_id,
                roadmap_id=roadmap_id,
                now=pause_time,
            )
            assert paused.status.value == "PAUSED"

        async with async_session_factory() as session:
            rows = list(
                (
                    await session.execute(
                        select(PauseRecordORM).where(PauseRecordORM.roadmap_id == roadmap_id)
                    )
                )
                .scalars()
                .all()
            )
            assert len(rows) == 1
            assert rows[0].status == "ACTIVE"
            assert rows[0].pause_start_date == date(2026, 5, 1)
            assert rows[0].pause_end_date == date(2026, 5, 1)
            assert rows[0].shifted_days == 1

        async with async_session_factory() as session:
            resume_uc = ResumeRoadmapUseCase(
                goal_repo=SqlAlchemyGoalRepository(session),
                roadmap_repo=SqlAlchemyRoadmapRepository(session),
                schedule_repo=SqlAlchemyOfficialScheduleRepository(session),
                uow=SqlAlchemyUnitOfWork(session),
                pause_record_port=create_pause_record_port(session),
            )
            resumed = await resume_uc.execute(
                user_id=user_id,
                roadmap_id=roadmap_id,
                now=resume_time,
            )
            assert resumed.status.value == "ACTIVE"

        async with async_session_factory() as session:
            rows = list(
                (
                    await session.execute(
                        select(PauseRecordORM).where(PauseRecordORM.roadmap_id == roadmap_id)
                    )
                )
                .scalars()
                .all()
            )
            assert len(rows) == 1
            assert rows[0].status == "COMPLETED"
            assert rows[0].pause_start_date == date(2026, 5, 1)
            assert rows[0].shifted_days == 3
            assert rows[0].pause_end_date == date(2026, 5, 3)
    finally:
        await _cleanup_user(user_id)


@pytest.mark.asyncio
async def test_concurrent_pause_calls_never_create_duplicate_active_pause_records() -> None:
    user_id, _, roadmap_id = await _seed_active_roadmap()
    now = datetime(2026, 5, 10, 8, 0, tzinfo=UTC)

    async def _attempt_pause() -> str:
        async with async_session_factory() as session:
            uc = PauseRoadmapUseCase(
                roadmap_repo=SqlAlchemyRoadmapRepository(session),
                schedule_repo=SqlAlchemyOfficialScheduleRepository(session),
                uow=SqlAlchemyUnitOfWork(session),
                pause_record_port=PauseRecordAdapter(session),
            )
            try:
                await uc.execute(user_id=user_id, roadmap_id=roadmap_id, now=now)
                return "ok"
            except Exception as exc:
                return f"err:{type(exc).__name__}"

    try:
        outcomes = await asyncio.gather(_attempt_pause(), _attempt_pause(), _attempt_pause())
        assert outcomes.count("ok") == 1

        async with async_session_factory() as session:
            active_rows = list(
                (
                    await session.execute(
                        select(PauseRecordORM).where(
                            PauseRecordORM.roadmap_id == roadmap_id,
                            PauseRecordORM.status == "ACTIVE",
                        )
                    )
                )
                .scalars()
                .all()
            )
            assert len(active_rows) == 1
    finally:
        await _cleanup_user(user_id)


@pytest.mark.asyncio
async def test_pause_transaction_rollback_leaves_zero_orphan_pause_records() -> None:
    user_id, _, roadmap_id = await _seed_active_roadmap()
    now = datetime(2026, 5, 12, 8, 0, tzinfo=UTC)

    class _FailingChangeLogPort:
        async def log_schedule_change(self, **kwargs: object) -> object:
            raise RuntimeError("simulated change log failure")

        async def record_change_log(self, **kwargs: object) -> object:
            raise RuntimeError("simulated change log failure")

    try:
        async with async_session_factory() as session:
            pause_port: PauseRecordPort = create_pause_record_port(session)
            uc = PauseRoadmapUseCase(
                roadmap_repo=SqlAlchemyRoadmapRepository(session),
                schedule_repo=SqlAlchemyOfficialScheduleRepository(session),
                uow=SqlAlchemyUnitOfWork(session),
                schedule_change_log_port=_FailingChangeLogPort(),  # type: ignore[arg-type]
                pause_record_port=pause_port,
            )
            with pytest.raises(RuntimeError, match="simulated change log failure"):
                await uc.execute(user_id=user_id, roadmap_id=roadmap_id, now=now)

        async with async_session_factory() as session:
            rows = list(
                (
                    await session.execute(
                        select(PauseRecordORM).where(PauseRecordORM.roadmap_id == roadmap_id)
                    )
                )
                .scalars()
                .all()
            )
            assert rows == []
            roadmap_row = await session.get(RoadmapORM, roadmap_id)
            assert roadmap_row is not None
            assert roadmap_row.status == "ACTIVE"
            assert isinstance(
                PauseRecordDTO(
                    id=uuid7(),
                    roadmap_id=roadmap_id,
                    pause_start_date=now.date(),
                    pause_end_date=now.date(),
                    shifted_days=1,
                    reason=None,
                    status="ACTIVE",
                ),
                PauseRecordDTO,
            )
    finally:
        await _cleanup_user(user_id)
