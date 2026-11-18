import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from sqlalchemy import delete, func, select
from uuid6 import uuid7

from src.account.domain.services.ai_cost_accounting_service import summarize_cost_accounting_logs
from src.account.infrastructure.adapters.quota_facade_adapter import QuotaFacadeAdapter
from src.account.infrastructure.orm.user_orm import (
    AIQuotaORM,
    AIQuotaReservationORM,
    AIUsageLogORM,
    UserORM,
)
from src.shared_kernel.application.harness.execution_manager import AIExecutionManager
from src.shared_kernel.application.llm_port import LLMGenerationResult, LLMProviderPort
from src.shared_kernel.infrastructure.database.session import async_session_factory
from src.shared_kernel.infrastructure.database.sqlalchemy_uow import SqlAlchemyUnitOfWork


async def _seed_user(user_id: UUID) -> None:
    now = datetime.now(UTC)
    async with async_session_factory() as session:
        user = UserORM(
            id=user_id,
            email=f"def17_pg_{user_id.hex}@focusflow.vn",
            password_hash="argon2id$mockhash",
            full_name="DEF-17 Postgres Verification Learner",
            timezone="Asia/Ho_Chi_Minh",
            role="LEARNER",
            tier="FREE",
            is_locked=False,
        )
        quota = AIQuotaORM(
            id=uuid7(),
            user_id=user_id,
            free_credits_remaining=3,
            paid_credits_remaining=0,
            used_calls=0,
            reserved_calls=0,
            tokens_consumed=0,
            cycle_start=now,
            cycle_end=now + timedelta(days=30),
        )
        session.add(user)
        await session.flush()
        session.add(quota)
        await session.commit()


async def _cleanup_user(user_id: UUID) -> None:
    async with async_session_factory() as session:
        await session.execute(delete(AIUsageLogORM).where(AIUsageLogORM.user_id == user_id))
        await session.execute(
            delete(AIQuotaReservationORM).where(AIQuotaReservationORM.user_id == user_id)
        )
        await session.execute(delete(AIQuotaORM).where(AIQuotaORM.user_id == user_id))
        await session.execute(delete(UserORM).where(UserORM.id == user_id))
        await session.commit()


@pytest.mark.asyncio
async def test_postgres_concurrent_workers_idempotent_record_attempt_usage() -> None:
    """Verify atomic PostgreSQL uniqueness across two independent sessions/workers."""
    user_id = uuid7()
    await _seed_user(user_id)
    shared_key = f"concurrent-worker-key:{uuid7()}:M1:1"

    try:

        async def _worker_call(resolved_model: str) -> AIUsageLogORM | None:
            # Completely independent AsyncSession and QuotaFacadeAdapter (no shared in-memory set)
            async with async_session_factory() as worker_session:
                adapter = QuotaFacadeAdapter(session=worker_session)
                return await adapter.record_attempt_usage(
                    user_id=user_id,
                    action_type="MILESTONE_BREAKDOWN",
                    requested_model="gemini-3.8-flash",
                    resolved_model=resolved_model,
                    prompt_tokens=1200,
                    completion_tokens=600,
                    thinking_tokens=100,
                    latency_ms=420,
                    status="SUCCESS",
                    usage_completeness="COMPLETE",
                    usage_source="GATEWAY_TELEMETRY",
                    attempt_no=1,
                    idempotency_key=shared_key,
                )

        # Race two independent sessions concurrently
        res_a, res_b = await asyncio.gather(
            _worker_call("gemini-3.8-flash-high"),
            _worker_call("gemini-3.8-flash-high"),
        )

        # Exactly one worker inserted the row; the other saw ON CONFLICT DO NOTHING -> None
        winners = [r for r in (res_a, res_b) if r is not None]
        losers = [r for r in (res_a, res_b) if r is None]
        assert len(winners) == 1
        assert len(losers) == 1

        # Sequential third worker call with same key also deduplicates atomically via Postgres index
        res_c = await _worker_call("gemini-3.8-flash-high")
        assert res_c is None

        # Verify physical PostgreSQL row count == 1 and JSONB audit_metadata stored cleanly
        async with async_session_factory() as verify_session:
            count_res = await verify_session.execute(
                select(func.count())
                .select_from(AIUsageLogORM)
                .where(AIUsageLogORM.idempotency_key == shared_key)
            )
            assert count_res.scalar_one() == 1

            row = (
                await verify_session.execute(
                    select(AIUsageLogORM).where(AIUsageLogORM.idempotency_key == shared_key)
                )
            ).scalar_one()
            assert row.idempotency_key == shared_key
            assert isinstance(row.audit_metadata, dict)
            assert row.audit_metadata["requested_model"] == "gemini-3.8-flash"
            assert row.audit_metadata["resolved_model"] == "gemini-3.8-flash-high"
            assert row.audit_metadata["pricing_version"] == "2026-Q1-STANDARD"
            assert row.audit_metadata["usage_completeness"] == "COMPLETE"
            assert row.audit_metadata["cost_verification_status"] == "UNVERIFIED"
            assert row.audit_metadata["thinking_tokens"] == 100

            # Also verify legacy compatibility: multiple rows with idempotency_key=NULL allowed
            legacy_1 = AIUsageLogORM(
                user_id=user_id, action_type="CHAT_ASSISTANT", idempotency_key=None
            )
            legacy_2 = AIUsageLogORM(
                user_id=user_id, action_type="CHAT_ASSISTANT", idempotency_key=None
            )
            verify_session.add_all([legacy_1, legacy_2])
            await verify_session.commit()

            null_count = (
                await verify_session.execute(
                    select(func.count())
                    .select_from(AIUsageLogORM)
                    .where(
                        AIUsageLogORM.user_id == user_id,
                        AIUsageLogORM.idempotency_key.is_(None),
                    )
                )
            ).scalar_one()
            assert null_count == 2
    finally:
        await _cleanup_user(user_id)


@pytest.mark.asyncio
async def test_postgres_fault_injection_rollback_preserves_provider_usage() -> None:
    """Fault injection: outer UoW rolls back after LLM completes & user quota is released,
    proving provider usage telemetry in ai_usage_logs survives independently in PostgreSQL.
    """
    user_id = uuid7()
    await _seed_user(user_id)

    try:
        # Step 1: Reserve quota in transaction 1 (realistic pre-AI reservation)
        async with async_session_factory() as reserve_session:
            facade_res = QuotaFacadeAdapter(session=reserve_session)
            reservation_id = await facade_res.reserve_quota(
                user_id=user_id,
                operation_type="ROADMAP_GEN",
                cost=1,
            )
            await reserve_session.commit()

        # Step 2: Run LLM via AIExecutionManager inside an outer UoW that FAILS and ROLLS BACK
        mock_provider = MagicMock(spec=LLMProviderPort)
        mock_provider.generate_structured = AsyncMock(
            return_value=LLMGenerationResult(
                payload={"milestones": [{"title": "M1"}]},
                prompt_tokens=2000,
                output_tokens=1000,  # includes 300 thinking tokens
                thinking_tokens=300,
                model_id="gemini-3.8-flash-high",
                resolved_model="gemini-3.8-flash-high",
            )
        )

        class _InjectedDownstreamDBError(RuntimeError):
            pass

        with pytest.raises(_InjectedDownstreamDBError):
            async with async_session_factory() as biz_session:
                uow = SqlAlchemyUnitOfWork(biz_session)
                async with uow:
                    quota_adapter = QuotaFacadeAdapter(session=biz_session)
                    exec_mgr = AIExecutionManager(
                        provider=mock_provider,
                        quota=quota_adapter,
                        manage_quota=False,
                        timeout_seconds=10.0,
                        max_retries=0,
                    )
                    # Upstream LLM succeeds and records provider attempt usage
                    await exec_mgr.execute(
                        user_id=user_id,
                        operation_type="ROADMAP_GENERATION",
                        system_prompt="sys",
                        user_prompt="user",
                        response_schema={"type": "object"},
                        thinking_level="HIGH",
                        existing_reservation_id=reservation_id,
                        step_name="TASK_DECOMPOSER_FAULT_TEST",
                    )

                    # Even if commit_reservation was staged in biz_session before injected crash,
                    # rolling back biz_session must rollback quota deduction while preserving usage log!
                    await quota_adapter.commit_reservation(
                        reservation_id=reservation_id,
                        prompt_tokens=2000,
                        completion_tokens=1000,
                        model_name="gemini-3.8-flash-high",
                    )

                    # Inject catastrophic downstream DB failure BEFORE uow.commit()
                    raise _InjectedDownstreamDBError(
                        "Simulated DB commit failure after LLM completed"
                    )

        # Step 3: Release user's reservation (since workflow failed) in a clean recovery transaction
        async with async_session_factory() as release_session:
            facade_rel = QuotaFacadeAdapter(session=release_session)
            await facade_rel.release_reservation(reservation_id, reason="DOWNSTREAM_DB_ROLLBACK")
            await release_session.commit()

        # Step 4: Verify in an independent PostgreSQL session
        async with async_session_factory() as verify_session:
            quota_row = (
                await verify_session.execute(
                    select(AIQuotaORM).where(AIQuotaORM.user_id == user_id)
                )
            ).scalar_one()
            res_row = (
                await verify_session.execute(
                    select(AIQuotaReservationORM).where(AIQuotaReservationORM.id == reservation_id)
                )
            ).scalar_one()
            logs = list(
                (
                    await verify_session.execute(
                        select(AIUsageLogORM).where(AIUsageLogORM.user_id == user_id)
                    )
                )
                .scalars()
                .all()
            )

            # User quota was NOT charged (Postgres columns rolled back & reservation settled RELEASED)
            assert quota_row.monthly_limit == 3
            assert quota_row.used_calls == 0
            assert quota_row.reserved_calls == 0
            assert quota_row.tokens_consumed == 0
            assert res_row.status == "RELEASED"

            # Provider usage WAS preserved in PostgreSQL independently of rollback & quota refund!
            assert len(logs) == 1
            log = logs[0]
            assert log.prompt_tokens == 2000
            assert log.completion_tokens == 1000
            assert log.total_tokens == 3000
            # (2000 * 0.75 + 1000 * 3.75) / 1,000,000 = (1500 + 3750) / 1,000,000 = 0.005250 USD
            assert log.estimated_cost_usd == Decimal("0.005250")
            assert log.audit_metadata is not None
            assert log.audit_metadata["reservation_id"] == str(reservation_id)
            assert log.audit_metadata["resolved_model"] == "gemini-3.8-flash-high"
            assert log.audit_metadata["usage_completeness"] == "COMPLETE"
    finally:
        await _cleanup_user(user_id)


@pytest.mark.asyncio
async def test_postgres_commit_reservation_no_double_counting_when_attempt_logged() -> None:
    """Verify commit_reservation skips aggregate row insertion when attempt ledger already recorded for reservation."""
    user_id = uuid7()
    await _seed_user(user_id)

    try:
        async with async_session_factory() as session:
            adapter = QuotaFacadeAdapter(session=session)
            res_id = await adapter.reserve_quota(
                user_id=user_id, operation_type="ROADMAP_GEN", cost=1
            )
            await session.commit()

        async with async_session_factory() as worker_session:
            adapter = QuotaFacadeAdapter(session=worker_session)
            await adapter.record_attempt_usage(
                user_id=user_id,
                action_type="ROADMAP_GENERATION",
                requested_model="gemini-3.8-flash",
                resolved_model="gemini-3.8-flash-high",
                prompt_tokens=1000,
                completion_tokens=1000,
                thinking_tokens=200,
                status="SUCCESS",
                idempotency_key=f"{res_id}:DECOMPOSER:1",
                reservation_id=res_id,
            )

        # Call commit_reservation from a SECOND independent session (fresh adapter instance)
        async with async_session_factory() as commit_session:
            commit_adapter = QuotaFacadeAdapter(session=commit_session)
            await commit_adapter.commit_reservation(
                reservation_id=res_id,
                prompt_tokens=1000,
                completion_tokens=1000,
                model_name="gemini-3.8-flash-high",
            )
            await commit_session.commit()

        async with async_session_factory() as verify_session:
            logs = list(
                (
                    await verify_session.execute(
                        select(AIUsageLogORM).where(AIUsageLogORM.user_id == user_id)
                    )
                )
                .scalars()
                .all()
            )
            # Strictly 1 row (no double-counting!)
            assert len(logs) == 1
            assert logs[0].idempotency_key == f"{res_id}:DECOMPOSER:1"
    finally:
        await _cleanup_user(user_id)


@pytest.mark.asyncio
async def test_cost_summary_excludes_or_flags_unknown_telemetry_postgres() -> None:
    """Verify cost aggregation from real Postgres rows flags UNKNOWN attempts and never reports them as complete $0 compute."""
    user_id = uuid7()
    await _seed_user(user_id)

    try:
        async with async_session_factory() as session:
            adapter = QuotaFacadeAdapter(session=session)
            await adapter.record_attempt_usage(
                user_id=user_id,
                action_type="ROADMAP_GENERATION",
                requested_model="gemini-3.8-flash",
                resolved_model="gemini-3.8-flash-high",
                prompt_tokens=4000,
                completion_tokens=2000,
                thinking_tokens=400,
                status="SUCCESS",
                usage_completeness="COMPLETE",
                idempotency_key=f"summary:{uuid7()}:1",
            )
            await adapter.record_attempt_usage(
                user_id=user_id,
                action_type="MILESTONE_BREAKDOWN",
                requested_model="gemini-3.8-flash",
                prompt_tokens=0,
                completion_tokens=0,
                status="TIMEOUT",
                usage_completeness="UNKNOWN",
                usage_source="UNKNOWN",
                error_code="TimeoutError",
                error_message="Socket timed out at 36s before headers",
                idempotency_key=f"summary:{uuid7()}:2",
            )
            await adapter.record_attempt_usage(
                user_id=user_id,
                action_type="MILESTONE_BREAKDOWN",
                requested_model="gemini-3.8-flash",
                prompt_tokens=0,
                completion_tokens=0,
                status="SUCCESS",
                usage_completeness="COMPLETE",
                usage_source="CACHE",
                idempotency_key=f"summary:{uuid7()}:3",
            )

        async with async_session_factory() as verify_session:
            logs = list(
                (
                    await verify_session.execute(
                        select(AIUsageLogORM)
                        .where(AIUsageLogORM.user_id == user_id)
                        .order_by(AIUsageLogORM.created_at.asc())
                    )
                )
                .scalars()
                .all()
            )
            summary = summarize_cost_accounting_logs(logs, successful_runs_count=1)
            assert summary.total_attempts == 3
            assert summary.complete_attempts == 2  # SUCCESS + CACHE
            assert summary.unknown_usage_attempts == 1
            assert summary.cached_attempts == 1
            assert summary.observed_prompt_tokens == 4000
            assert summary.observed_completion_tokens == 2000
            assert summary.observed_thinking_tokens == 400
            # (4000 * 0.75 + 2000 * 3.75) / 1M = (3000 + 7500) / 1M = $0.010500
            assert summary.observed_estimated_provider_cost_usd == Decimal("0.010500")
            assert summary.cost_completeness_status == "INCOMPLETE_LOWER_BOUND"
            assert summary.gateway_cost_status == "UNVERIFIED"
            assert summary.actual_gateway_cost_usd is None
    finally:
        await _cleanup_user(user_id)
