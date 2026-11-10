from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import delete, select, text
from uuid6 import uuid7

from src.account.infrastructure.adapters import (
    LearnerProfileQueryAdapter,
    QuotaFacadeAdapter,
)
from src.account.infrastructure.orm import (
    AiQuotaModel,
    AiQuotaReservationModel,
    AiUsageLogModel,
    LearnerProfileModel,
    UserORM,
)
from src.account.public_api import (
    QuotaExceededException,
    QuotaReservationNotFoundError,
)
from src.shared_kernel.infrastructure.database.session import async_session_factory


def test_migration_0002_structure_and_18_tables_verification() -> None:
    """Verify migration 0002 defines all 18 remaining tables, constraints, and clean downgrade."""
    migration_path = (
        Path(__file__).resolve().parents[3]
        / "alembic"
        / "versions"
        / "0002_complete_24_tables_schema.py"
    )
    assert migration_path.exists(), "0002_complete_24_tables_schema.py must exist"
    content = migration_path.read_text(encoding="utf-8")

    assert 'revision: str = "0002_complete_24_tables"' in content
    assert 'down_revision: str | None = "0001_account_avail"' in content

    expected_18_tables = (
        "learner_profiles",
        "webcal_tokens",
        "ai_quota_reservations",
        "ai_usage_logs",
        "payment_transactions",
        "goals",
        "roadmaps",
        "milestones",
        "official_schedules",
        "schedule_proposals",
        "tasks",
        "task_dependencies",
        "study_sessions",
        "session_tasks",
        "study_notes",
        "pause_records",
        "ai_reviews",
        "schedule_change_logs",
    )
    for table_name in expected_18_tables:
        assert f'"{table_name}"' in content, f"Table {table_name} missing in migration 0002"
        assert f'op.drop_table("{table_name}"' in content, (
            f"Table {table_name} missing in migration 0002 downgrade()"
        )

    # Check deferrable unique constraint on milestones and partial unique index on schedule_proposals
    assert "uq_milestones_roadmap_seq" in content
    assert "deferrable=True" in content
    assert 'initially="DEFERRED"' in content
    assert "uq_schedule_proposals_roadmap_draft" in content


@pytest.mark.asyncio
async def test_postgres_24_tables_present_after_migration() -> None:
    """Verify all 24 physical tables from schema.sql exist in PostgreSQL 16."""
    expected_24_tables = {
        "users",
        "learner_profiles",
        "webcal_tokens",
        "availabilities",
        "availability_slots",
        "ai_quotas",
        "ai_quota_reservations",
        "ai_usage_logs",
        "payment_transactions",
        "goals",
        "roadmaps",
        "milestones",
        "official_schedules",
        "schedule_proposals",
        "tasks",
        "task_dependencies",
        "study_sessions",
        "session_tasks",
        "study_notes",
        "pause_records",
        "ai_reviews",
        "schedule_change_logs",
        "outbox_events",
        "processed_events",
    }
    async with async_session_factory() as session:
        res = await session.execute(
            text(
                "SELECT tablename FROM pg_tables "
                "WHERE schemaname = 'public' AND tablename != 'alembic_version'"
            )
        )
        actual_tables = {row[0] for row in res.fetchall()}

    assert expected_24_tables.issubset(actual_tables)
    assert len(expected_24_tables) == 24


@pytest.mark.asyncio
async def test_quota_facade_reserve_commit_release_idempotency_and_free_first_deduction() -> None:
    """Verify 2-Phase Quota Reservation lifecycle on PostgreSQL 16:
    - Auto-initializes default ai_quotas (free_credits_remaining=3) when missing.
    - Deducts from free_credits_remaining first, then paid_credits_remaining on commit (BUSR-10).
    - Writes ai_usage_logs on commit; idempotent on repeated commit.
    - Release keeps credits intact; idempotent on repeated release.
    - Insufficient quota raises QuotaExceededException.
    - Expire stale reservations releases held credits.
    """
    user_id: UUID = uuid7()
    async with async_session_factory() as session:
        user = UserORM(
            id=user_id,
            email=f"quota_test_{user_id.hex[:8]}@focusflow.vn",
            password_hash="argon2id$mockhash",
            full_name="Quota Test Learner",
            timezone="Asia/Ho_Chi_Minh",
            role="LEARNER",
            tier="FREE",
            is_locked=False,
        )
        session.add(user)
        await session.commit()

    try:
        async with async_session_factory() as session:
            facade = QuotaFacadeAdapter(session=session, default_free_credits=3)

            # 1. Auto-initialize quota (free=3, paid=0) and reserve cost=2
            res_id_1 = await facade.reserve_quota(
                user_id=user_id,
                cost=2,
                operation_type="ROADMAP_GEN",
                ttl_seconds=120,
            )
            await session.commit()

            quota_row = (
                await session.execute(select(AiQuotaModel).where(AiQuotaModel.user_id == user_id))
            ).scalar_one()
            assert quota_row.free_credits_remaining == 3
            assert quota_row.paid_credits_remaining == 0
            assert quota_row.reserved_calls == 2

            # Add 2 paid credits so pool has free=3, paid=2
            quota_row.paid_credits_remaining = 2
            await session.commit()

            # 2. Commit reservation 1 (cost=2) -> deducts 2 from free_credits_remaining first (free=1, paid=2)
            await facade.commit_reservation(
                reservation_id=res_id_1,
                prompt_tokens=150,
                completion_tokens=350,
                model_name="gemini-2.5-flash",
            )
            await session.commit()

            assert quota_row.free_credits_remaining == 1
            assert quota_row.paid_credits_remaining == 2
            assert quota_row.used_calls == 2
            assert quota_row.reserved_calls == 0
            assert quota_row.tokens_consumed == 500

            # Idempotent second commit call must not deduct again or duplicate usage log
            await facade.commit_reservation(
                reservation_id=res_id_1,
                prompt_tokens=150,
                completion_tokens=350,
                model_name="gemini-2.5-flash",
            )
            await session.commit()
            assert quota_row.free_credits_remaining == 1
            assert quota_row.paid_credits_remaining == 2

            logs = list(
                (
                    await session.execute(
                        select(AiUsageLogModel).where(AiUsageLogModel.user_id == user_id)
                    )
                )
                .scalars()
                .all()
            )
            assert len(logs) == 1
            assert logs[0].action_type == "ROADMAP_GENERATION"
            assert logs[0].total_tokens == 500
            assert logs[0].model_name == "gemini-2.5-flash"

            # 3. Reserve cost=2 and commit -> deducts remaining 1 free credit + 1 paid credit (free=0, paid=1)
            res_id_2 = await facade.reserve_quota(
                user_id=user_id,
                cost=2,
                operation_type="SCHEDULE_PROPOSAL",
                ttl_seconds=120,
            )
            await facade.commit_reservation(
                reservation_id=res_id_2,
                prompt_tokens=200,
                completion_tokens=400,
            )
            await session.commit()
            assert quota_row.free_credits_remaining == 0
            assert quota_row.paid_credits_remaining == 1
            assert quota_row.used_calls == 4

            # 4. Reserve cost=1 then release -> credits stay intact (free=0, paid=1)
            res_id_3 = await facade.reserve_quota(
                user_id=user_id,
                cost=1,
                operation_type="ROADMAP_GEN",
                ttl_seconds=120,
            )
            await facade.release_reservation(res_id_3, reason="Validation failed after retries")
            # Idempotent second release
            await facade.release_reservation(res_id_3, reason="Duplicate release")
            await session.commit()

            res_3_row = (
                await session.execute(
                    select(AiQuotaReservationModel).where(AiQuotaReservationModel.id == res_id_3)
                )
            ).scalar_one()
            assert res_3_row.status == "RELEASED"
            assert res_3_row.resolved_at is not None
            assert quota_row.free_credits_remaining == 0
            assert quota_row.paid_credits_remaining == 1
            assert quota_row.reserved_calls == 0

            # 5. Insufficient quota (available=1, requested cost=2) -> raises QuotaExceededException
            with pytest.raises(QuotaExceededException) as exc_info:
                await facade.reserve_quota(user_id=user_id, cost=2, operation_type="ROADMAP_GEN")
            assert exc_info.value.code == "QUOTA_EXHAUSTED"

            # 6. Stale reservation expiration sweeper
            res_id_4 = await facade.reserve_quota(
                user_id=user_id,
                cost=1,
                operation_type="ROADMAP_GEN",
                ttl_seconds=10,
            )
            await session.commit()
            expired_count = await facade.expire_stale_reservations(
                now=datetime.now(UTC) + timedelta(seconds=30)
            )
            await session.commit()
            assert expired_count >= 1

            res_4_row = (
                await session.execute(
                    select(AiQuotaReservationModel).where(AiQuotaReservationModel.id == res_id_4)
                )
            ).scalar_one()
            assert res_4_row.status == "EXPIRED"
            assert quota_row.reserved_calls == 0

            # Non-existent reservation raises QuotaReservationNotFoundError
            with pytest.raises(QuotaReservationNotFoundError):
                await facade.commit_reservation(uuid7(), 10, 10)
    finally:
        AiQuotaModel._credit_ledger_by_user.pop(user_id, None)
        async with async_session_factory() as session:
            await session.execute(delete(UserORM).where(UserORM.id == user_id))
            await session.commit()


@pytest.mark.asyncio
async def test_learner_profile_query_adapter_cold_start_and_persisted() -> None:
    """Verify LearnerProfileQueryAdapter returns cold-start defaults when missing and persisted values when present."""
    user_id: UUID = uuid7()
    async with async_session_factory() as session:
        user = UserORM(
            id=user_id,
            email=f"profile_test_{user_id.hex[:8]}@focusflow.vn",
            password_hash="argon2id$mockhash",
            full_name="Profile Test Learner",
            timezone="Asia/Ho_Chi_Minh",
            role="LEARNER",
            tier="FREE",
            is_locked=False,
        )
        session.add(user)
        await session.commit()

    try:
        async with async_session_factory() as session:
            adapter = LearnerProfileQueryAdapter(session=session)

            # 1. Cold-start default when no learner_profiles row exists
            cold_dto = await adapter.get_learner_profile(user_id)
            assert cold_dto.user_id == user_id
            assert cold_dto.opt_session_minutes == 45
            assert cold_dto.estimation_bias_beta == 1.0
            assert cold_dto.peak_productivity_slots == {}
            assert cold_dto.is_cold_start is True

            # 2. Persist custom learner profile and query again
            profile = LearnerProfileModel(
                user_id=user_id,
                optimal_focus_duration_mins=60,
                estimation_bias_factor=Decimal("1.25"),
                peak_productivity_slots={"monday": ["19:00-21:00"], "preferred": "EVENING"},
                is_cold_start=False,
            )
            session.add(profile)
            await session.commit()

            persisted_dto = await adapter.get_learner_profile(user_id)
            assert persisted_dto.user_id == user_id
            assert persisted_dto.opt_session_minutes == 60
            assert persisted_dto.estimation_bias_beta == 1.25
            assert persisted_dto.peak_productivity_slots == {
                "monday": ["19:00-21:00"],
                "preferred": "EVENING",
            }
            assert persisted_dto.is_cold_start is False
    finally:
        async with async_session_factory() as session:
            await session.execute(delete(UserORM).where(UserORM.id == user_id))
            await session.commit()
