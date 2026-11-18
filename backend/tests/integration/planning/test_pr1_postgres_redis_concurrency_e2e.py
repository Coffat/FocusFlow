from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from unittest.mock import patch
from uuid import UUID

import pytest
import redis.asyncio as aioredis
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, func, select, text
from uuid6 import uuid7

from src.account.infrastructure.adapters.quota_facade_adapter import QuotaFacadeAdapter
from src.account.infrastructure.orm.availability_orm import (
    AvailabilityORM,
    AvailabilitySlotORM,
)
from src.account.infrastructure.orm.user_orm import (
    AIQuotaORM,
    AIQuotaReservationORM,
    LearnerProfileORM,
    UserORM,
)
from src.account.presentation.deps import get_current_learner_id
from src.account.public_api import QuotaExceededException
from src.evaluation.application.dtos.intelligence import GenerateWeeklyReviewRequestDTO
from src.evaluation.application.use_cases.intelligence import (
    GenerateWeeklyReviewUseCase,
    WeeklyReviewWriteScope,
)
from src.evaluation.infrastructure.orm.ai_review_orm import AIReviewORM
from src.evaluation.infrastructure.repositories.intelligence_repository import (
    SqlAlchemyEvaluationIntelligenceRepository,
)
from src.evaluation.presentation.deps import get_current_evaluation_learner_id
from src.main import app
from src.planning.application.ports.sse_job_port import (
    DEFAULT_SSE_TIMEOUT_MESSAGE,
    claim_idempotency_slot_with_wait,
)
from src.planning.application.use_cases.milestone_use_cases import (
    ExecuteMilestoneGenerationUseCase,
    InitiateMilestoneGenerationUseCase,
)
from src.planning.application.use_cases.proposal_generation_use_cases import (
    InitiateScheduleProposalGenerationUseCase,
)
from src.planning.domain.models.milestone import Milestone, MilestoneStatus
from src.planning.infrastructure.repositories.planning_repositories import (
    SqlAlchemyGoalRepository,
    SqlAlchemyMilestoneRepository,
    SqlAlchemyRoadmapRepository,
    SqlAlchemyScheduleProposalRepository,
)
from src.planning.presentation.deps import get_llm_provider, get_sse_job_store
from src.planning.public_api import create_milestone_ownership_port
from src.shared_kernel.infrastructure.database.session import async_session_factory
from src.shared_kernel.infrastructure.database.sqlalchemy_uow import SqlAlchemyUnitOfWork
from src.shared_kernel.infrastructure.outbox.models import OutboxEventORM
from src.shared_kernel.infrastructure.sse.job_store import InMemorySseJobStore, RedisSseJobStore
from tests.helpers.llm_stubs import StubLLMAdapter

_REDIS_URL = "redis://localhost:6379/0"


@pytest.fixture
async def pr1_pg_redis_user() -> AsyncGenerator[tuple[UUID, RedisSseJobStore], None]:
    user_id = uuid7()
    now = datetime.now(UTC)
    redis_client = aioredis.from_url(_REDIS_URL, decode_responses=True)
    await redis_client.ping()
    sse_store = RedisSseJobStore(redis_url=_REDIS_URL, fallback_store=InMemorySseJobStore())

    async with async_session_factory() as session:
        user = UserORM(
            id=user_id,
            email=f"pr1_pg_redis_{user_id.hex}@focusflow.vn",
            password_hash="argon2id$mockhash",
            full_name="PR-1 Postgres Redis Concurrency",
            timezone="Asia/Ho_Chi_Minh",
            role="LEARNER",
            tier="FREE",
            is_locked=False,
        )
        quota = AIQuotaORM(
            id=uuid7(),
            user_id=user_id,
            monthly_limit=5,
            used_calls=0,
            reserved_calls=0,
            tokens_consumed=0,
            cycle_start=now,
            cycle_end=now + timedelta(days=30),
        )
        profile = LearnerProfileORM(
            id=uuid7(),
            user_id=user_id,
            opt_session_minutes=60,
            estimation_bias_beta=1.0,
            is_cold_start=False,
        )
        avail_id = uuid7()
        avail = AvailabilityORM(
            id=avail_id,
            user_id=user_id,
            mode="MODE_A",
            calendar_integration_mode="NONE",
            min_session_minutes=30,
            daily_quotas={
                "monday": {"enabled": True, "quota_hours": 2.0},
                "tuesday": {"enabled": True, "quota_hours": 2.0},
                "wednesday": {"enabled": True, "quota_hours": 2.0},
            },
        )
        slots = [
            AvailabilitySlotORM(
                id=uuid7(),
                availability_id=avail_id,
                day_of_week=dow,
                slot_type="FIXED",
                start_time=time(19, 0),
                end_time=time(21, 0),
                end_day_offset=0,
                is_active=True,
            )
            for dow in (0, 1, 2)
        ]
        session.add(user)
        await session.flush()
        session.add_all([quota, profile, avail])
        await session.flush()
        session.add_all(slots)
        await session.commit()

    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_learner_id] = lambda: user_id
    app.dependency_overrides[get_current_evaluation_learner_id] = lambda: user_id
    app.dependency_overrides[get_llm_provider] = lambda: StubLLMAdapter()
    app.dependency_overrides[get_sse_job_store] = lambda: sse_store

    try:
        yield user_id, sse_store
    finally:
        app.dependency_overrides.clear()
        AIQuotaORM._credit_ledger_by_user.pop(user_id, None)
        keys = await redis_client.keys(f"sse:idem:{user_id}:*")
        if keys:
            await redis_client.delete(*keys)
        await redis_client.aclose()
        async with async_session_factory() as session:
            await session.execute(
                text(
                    "DELETE FROM session_tasks WHERE session_id IN "
                    "(SELECT id FROM study_sessions WHERE user_id = :uid)"
                ),
                {"uid": user_id},
            )
            await session.execute(delete(AIReviewORM).where(AIReviewORM.user_id == user_id))
            await session.execute(
                delete(OutboxEventORM).where(OutboxEventORM.aggregate_id == user_id)
            )
            await session.execute(delete(UserORM).where(UserORM.id == user_id))
            await session.commit()


@pytest.mark.asyncio
async def test_pr1_concurrent_generation_idempotency_postgres_and_redis(
    pr1_pg_redis_user: tuple[UUID, RedisSseJobStore],
) -> None:
    """(a) Concurrent generation requests with identical Idempotency-Key -> 1 job, 1 reservation, 1 dispatch."""
    user_id, sse_store = pr1_pg_redis_user
    transport = ASGITransport(app=app)
    mon = date(2026, 11, 16)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        rm_res = await client.post(
            "/api/v1/roadmaps",
            json={
                "title": "PR1 Concurrency Roadmap",
                "description": "Idempotency test",
                "start_date": mon.isoformat(),
                "target_date": (mon + timedelta(days=14)).isoformat(),
            },
        )
        assert rm_res.status_code == 201, rm_res.text
        roadmap_id = UUID(rm_res.json()["id"])

        dispatches: list[str] = []

        async def _fake_dispatch(**kwargs: str) -> None:
            dispatches.append(kwargs["job_id"])

        with patch(
            "src.planning.presentation.routers.dispatch_ai_roadmap_generation",
            side_effect=_fake_dispatch,
        ):
            r1, r2, r3 = await asyncio.gather(
                client.post(
                    f"/api/v1/roadmaps/{roadmap_id}/milestones/generate-jobs",
                    headers={"Idempotency-Key": "pr1-idem-key-001"},
                ),
                client.post(
                    f"/api/v1/roadmaps/{roadmap_id}/milestones/generate-jobs",
                    headers={"Idempotency-Key": "pr1-idem-key-001"},
                ),
                client.post(
                    f"/api/v1/roadmaps/{roadmap_id}/milestones/generate-jobs",
                    headers={"Idempotency-Key": "pr1-idem-key-001"},
                ),
            )

        assert r1.status_code == 202, r1.text
        assert r2.status_code == 202, r2.text
        assert r3.status_code == 202, r3.text
        assert r1.json()["job_id"] == r2.json()["job_id"] == r3.json()["job_id"]
        assert (
            r1.json()["reservation_id"]
            == r2.json()["reservation_id"]
            == r3.json()["reservation_id"]
        )
        assert len(dispatches) == 1

        # Verify strictly 1 reservation in PostgreSQL and reserved_calls == 1
        async with async_session_factory() as session:
            res_count = (
                await session.execute(
                    select(func.count())
                    .select_from(AIQuotaReservationORM)
                    .where(AIQuotaReservationORM.user_id == user_id)
                )
            ).scalar_one()
            quota_row = (
                await session.execute(select(AIQuotaORM).where(AIQuotaORM.user_id == user_id))
            ).scalar_one()
            assert res_count == 1
            assert quota_row.reserved_calls == 1
            assert quota_row.monthly_limit == 5

        # Also test direct RedisSseJobStore cross-instance concurrency (two separate stores sharing Redis)
        store_a = RedisSseJobStore(redis_url=_REDIS_URL, fallback_store=InMemorySseJobStore())
        store_b = RedisSseJobStore(redis_url=_REDIS_URL, fallback_store=InMemorySseJobStore())

        async def _run_init(store: RedisSseJobStore) -> UUID:
            async with async_session_factory() as session:
                uc = InitiateMilestoneGenerationUseCase(
                    roadmap_repo=SqlAlchemyRoadmapRepository(session),
                    quota_facade=QuotaFacadeAdapter(session),
                    sse_job_store=store,
                    uow=SqlAlchemyUnitOfWork(session),
                )
                ticket = await uc.execute(
                    user_id=user_id,
                    roadmap_id=roadmap_id,
                    idempotency_key="pr1-cross-store-key",
                    run_inline=False,
                )
                return ticket.job_id

        j_a, j_b = await asyncio.gather(_run_init(store_a), _run_init(store_b))
        assert j_a == j_b

        async with async_session_factory() as session:
            res_count_2 = (
                await session.execute(
                    select(func.count())
                    .select_from(AIQuotaReservationORM)
                    .where(AIQuotaReservationORM.user_id == user_id)
                )
            ).scalar_one()
            assert res_count_2 == 2  # 1 from first key + 1 from second key

        # Also verify concurrent InitiateScheduleProposalGenerationUseCase across two Postgres+Redis sessions
        async with async_session_factory() as seed_session:
            ms_repo = SqlAlchemyMilestoneRepository(seed_session)
            ms_id = uuid7()
            await ms_repo.save_many(
                roadmap_id,
                [
                    Milestone(
                        id=ms_id,
                        roadmap_id=roadmap_id,
                        sequence_order=1,
                        title="Approved M1",
                        estimated_effort_minutes=60,
                        status=MilestoneStatus.APPROVED,
                        created_at=datetime.now(UTC),
                        updated_at=datetime.now(UTC),
                    )
                ],
            )
            await seed_session.commit()

        from src.account.public_api import create_availability_query_port
        from src.execution.public_api import create_execution_schedule_sync_port

        async def _run_prop_init(store: RedisSseJobStore) -> UUID:
            async with async_session_factory() as session:
                uc = InitiateScheduleProposalGenerationUseCase(
                    roadmap_repo=SqlAlchemyRoadmapRepository(session),
                    milestone_repo=SqlAlchemyMilestoneRepository(session),
                    quota_facade=QuotaFacadeAdapter(session),
                    sse_job_store=store,
                    uow=SqlAlchemyUnitOfWork(session),
                    goal_repo=SqlAlchemyGoalRepository(session),
                    proposal_repo=SqlAlchemyScheduleProposalRepository(session),
                    availability_query_port=create_availability_query_port(session),
                    execution_sync_port=create_execution_schedule_sync_port(session),
                )
                ticket = await uc.execute(
                    user_id=user_id,
                    roadmap_id=roadmap_id,
                    idempotency_key="pr1-prop-cross-store-key",
                    run_inline=False,
                )
                return ticket.job_id

        pj_a, pj_b = await asyncio.gather(_run_prop_init(store_a), _run_prop_init(store_b))
        assert pj_a == pj_b

        async with async_session_factory() as session:
            res_count_3 = (
                await session.execute(
                    select(func.count())
                    .select_from(AIQuotaReservationORM)
                    .where(AIQuotaReservationORM.user_id == user_id)
                )
            ).scalar_one()
            assert res_count_3 == 3

        # Also verify 409 IDEMPOTENCY_REQUEST_IN_PROGRESS when slot stays PENDING in Redis
        op = f"MILESTONE_GEN:FULL_SCOPE:{roadmap_id}"
        held = await sse_store.claim_idempotency_slot(
            user_id=user_id,
            operation=op,
            idempotency_key="pr1-stuck-key",
            pending_ttl_seconds=30,
        )
        assert held.acquired is True

        async def _short_wait(*args: object, **kwargs: object) -> object:
            kwargs["max_wait_seconds"] = 0.06
            return await claim_idempotency_slot_with_wait(*args, **kwargs)  # type: ignore[arg-type]

        with patch(
            "src.planning.application.use_cases.milestone_use_cases.claim_idempotency_slot_with_wait",
            side_effect=_short_wait,
        ):
            stuck_res = await client.post(
                f"/api/v1/roadmaps/{roadmap_id}/milestones/generate-jobs",
                headers={"Idempotency-Key": "pr1-stuck-key"},
            )
            assert stuck_res.status_code == 409
            assert stuck_res.json()["code"] == "IDEMPOTENCY_REQUEST_IN_PROGRESS"


@pytest.mark.asyncio
async def test_pr1_multi_session_quota_no_double_subtraction_or_limit_shrink(
    pr1_pg_redis_user: tuple[UUID, RedisSseJobStore],
) -> None:
    """(b) Multi-session QuotaFacadeAdapter reserve/commit/release never shrinks monthly_limit or double-subtracts."""
    user_id, _ = pr1_pg_redis_user

    # Poison class-level cache with stale entry to prove DB-backed QuotaFacadeAdapter ignores it
    AIQuotaORM._credit_ledger_by_user[user_id] = (1, 0)

    # Session 1: set monthly_limit=3, reserve cost=1
    async with async_session_factory() as s1:
        q = (await s1.execute(select(AIQuotaORM).where(AIQuotaORM.user_id == user_id))).scalar_one()
        q.monthly_limit = 3
        await s1.commit()

    async with async_session_factory() as s1:
        f1 = QuotaFacadeAdapter(session=s1)
        res_1 = await f1.reserve_quota(user_id=user_id, operation_type="MILESTONE_GEN", cost=1)
        await s1.commit()

    # Session 2: available MUST be 3 - 0 - 1 = 2 (NOT 1 and NOT stale cache 0!)
    async with async_session_factory() as s2:
        f2 = QuotaFacadeAdapter(session=s2)
        assert await f2.check_quota_available(user_id, min_credits=2) is True
        res_2 = await f2.reserve_quota(user_id=user_id, operation_type="SCHEDULE_PROPOSAL", cost=2)
        await s2.commit()

    # Session 3: available is 0 -> QuotaExceededException shows 0 (never negative)
    async with async_session_factory() as s3:
        f3 = QuotaFacadeAdapter(session=s3)
        with pytest.raises(QuotaExceededException) as exc_info:
            await f3.reserve_quota(user_id=user_id, operation_type="MILESTONE_GEN", cost=1)
        assert "hiện còn 0 credit" in exc_info.value.message

        # Release res_1 and commit res_2 in fresh session -> monthly_limit MUST stay 3
        await f3.release_reservation(res_1, reason="TEST_RELEASE")
        await f3.commit_reservation(res_2, prompt_tokens=100, completion_tokens=50)
        await s3.commit()

    async with async_session_factory() as verify:
        q_final = (
            await verify.execute(select(AIQuotaORM).where(AIQuotaORM.user_id == user_id))
        ).scalar_one()
        assert q_final.monthly_limit == 3
        assert q_final.used_calls == 2
        assert q_final.reserved_calls == 0


@pytest.mark.asyncio
async def test_pr1_stale_applied_proposal_returns_409_postgres(
    pr1_pg_redis_user: tuple[UUID, RedisSseJobStore],
) -> None:
    """(c) Applying a stale/superseded APPLIED proposal returns 409 PROPOSAL_SUPERSEDED instead of false 200."""
    del pr1_pg_redis_user
    transport = ASGITransport(app=app)
    mon = date(2026, 11, 16)
    tue = date(2026, 11, 17)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        rm_res = await client.post(
            "/api/v1/roadmaps",
            json={
                "title": "Stale Applied Roadmap",
                "description": "BUG-04 test",
                "start_date": mon.isoformat(),
                "target_date": (mon + timedelta(days=14)).isoformat(),
            },
        )
        assert rm_res.status_code == 201
        roadmap_id = rm_res.json()["id"]

        ms_id = str(uuid7())
        t1_id = str(uuid7())
        p1_res = await client.post(
            f"/api/v1/roadmaps/{roadmap_id}/proposals/manual",
            json={
                "milestones": [
                    {
                        "milestone_id": ms_id,
                        "sequence_order": 1,
                        "title": "M1",
                        "description": "M1",
                    }
                ],
                "tasks": [
                    {
                        "task_id": t1_id,
                        "milestone_id": ms_id,
                        "title": "Task 1",
                        "estimated_minutes": 60,
                        "scheduled_date": mon.isoformat(),
                        "scheduled_start": f"{mon.isoformat()}T19:00:00+07:00",
                        "scheduled_end": f"{mon.isoformat()}T20:00:00+07:00",
                    }
                ],
                "dependencies": [],
            },
        )
        assert p1_res.status_code == 201
        p1_id = p1_res.json()["id"]

        # Apply P1 with Idempotency-Key k1 -> 200
        a1 = await client.post(
            f"/api/v1/roadmaps/{roadmap_id}/proposals/{p1_id}/apply",
            json={"confirm_soft_overflow": False},
            headers={"Idempotency-Key": "p1-apply-k1"},
        )
        assert a1.status_code == 200, a1.text

        # Create P2 and apply P2 -> 200
        t2_id = str(uuid7())
        p2_res = await client.post(
            f"/api/v1/roadmaps/{roadmap_id}/proposals/manual",
            json={
                "tasks": [
                    {
                        "task_id": t2_id,
                        "milestone_id": ms_id,
                        "title": "Task 2",
                        "estimated_minutes": 60,
                        "scheduled_date": tue.isoformat(),
                        "scheduled_start": f"{tue.isoformat()}T19:00:00+07:00",
                        "scheduled_end": f"{tue.isoformat()}T20:00:00+07:00",
                    }
                ],
                "dependencies": [],
            },
        )
        assert p2_res.status_code == 201, p2_res.text
        p2_id = p2_res.json()["id"]

        # Apply P2 WITHOUT Idempotency-Key -> 200
        a2 = await client.post(
            f"/api/v1/roadmaps/{roadmap_id}/proposals/{p2_id}/apply",
            json={"confirm_soft_overflow": False},
        )
        assert a2.status_code == 200, a2.text

        # Re-applying superseded P1 (even with its original key) -> 409 PROPOSAL_SUPERSEDED
        stale_p1 = await client.post(
            f"/api/v1/roadmaps/{roadmap_id}/proposals/{p1_id}/apply",
            json={"confirm_soft_overflow": False},
            headers={"Idempotency-Key": "p1-apply-k1"},
        )
        assert stale_p1.status_code == 409, stale_p1.text
        assert stale_p1.json()["code"] == "PROPOSAL_SUPERSEDED"

        # Re-applying P2 (which had applied_key=None) WITH an Idempotency-Key -> 409
        mismatched_p2 = await client.post(
            f"/api/v1/roadmaps/{roadmap_id}/proposals/{p2_id}/apply",
            json={"confirm_soft_overflow": False},
            headers={"Idempotency-Key": "unexpected-key"},
        )
        assert mismatched_p2.status_code == 409, mismatched_p2.text
        assert mismatched_p2.json()["code"] == "PROPOSAL_SUPERSEDED"


@pytest.mark.asyncio
async def test_pr1_concurrent_weekly_review_same_period_race_safe_postgres(
    pr1_pg_redis_user: tuple[UUID, RedisSseJobStore],
) -> None:
    """(d) Concurrent GenerateWeeklyReviewUseCase for same period succeeds without IntegrityError."""
    user_id, _ = pr1_pg_redis_user
    transport = ASGITransport(app=app)
    p_start = date(2026, 11, 9)
    p_end = date(2026, 11, 15)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        rm_res = await client.post(
            "/api/v1/roadmaps",
            json={
                "title": "Weekly Review Race Roadmap",
                "description": "BUG-07 test",
                "start_date": p_start.isoformat(),
                "target_date": (p_end + timedelta(days=7)).isoformat(),
            },
        )
        assert rm_res.status_code == 201
        roadmap_id = UUID(rm_res.json()["id"])

    from contextlib import asynccontextmanager

    async def _run_weekly_uc() -> UUID:
        async with async_session_factory() as read_session:

            @asynccontextmanager
            async def _write_scope_factory() -> AsyncGenerator[WeeklyReviewWriteScope, None]:
                async with async_session_factory() as write_session:
                    yield WeeklyReviewWriteScope(
                        uow=SqlAlchemyUnitOfWork(write_session),
                        repository=SqlAlchemyEvaluationIntelligenceRepository(write_session),
                    )

            uc = GenerateWeeklyReviewUseCase(
                repository=SqlAlchemyEvaluationIntelligenceRepository(read_session),
                ownership=create_milestone_ownership_port(read_session),
                uow=SqlAlchemyUnitOfWork(read_session),
                write_scope_factory=_write_scope_factory,
            )
            dto = await uc.execute(
                user_id,
                GenerateWeeklyReviewRequestDTO(
                    roadmap_id=roadmap_id,
                    period_start=p_start,
                    period_end=p_end,
                    reflection={"note": "Concurrent test"},
                ),
            )
            return dto.id

    id1, id2, id3 = await asyncio.gather(_run_weekly_uc(), _run_weekly_uc(), _run_weekly_uc())
    assert id1 == id2 == id3

    async with async_session_factory() as verify:
        count = (
            await verify.execute(
                select(func.count())
                .select_from(AIReviewORM)
                .where(
                    AIReviewORM.roadmap_id == roadmap_id,
                    AIReviewORM.period_start == p_start,
                    AIReviewORM.period_end == p_end,
                )
            )
        ).scalar_one()
        assert count == 1

    # Sequential HTTP call for same period also returns 202 with same review ID (never 500)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        http_res = await client.post(
            "/api/v1/evaluation/weekly-reviews/generate-jobs",
            json={
                "roadmap_id": str(roadmap_id),
                "period_start": p_start.isoformat(),
                "period_end": p_end.isoformat(),
                "reflection": {},
            },
        )
        assert http_res.status_code == 202, http_res.text
        assert UUID(http_res.json()["id"]) == id1


@pytest.mark.asyncio
async def test_pr1_timeout_sse_emission_in_redis_store(
    pr1_pg_redis_user: tuple[UUID, RedisSseJobStore],
) -> None:
    """(e) TimeoutError SSE emission produces non-empty AI_GATEWAY_TIMEOUT in RedisSseJobStore."""
    user_id, sse_store = pr1_pg_redis_user
    now = datetime.now(UTC)
    mon = date(2026, 11, 16)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        rm_res = await client.post(
            "/api/v1/roadmaps",
            json={
                "title": "SSE Timeout Roadmap",
                "description": "BUG-02 test",
                "start_date": mon.isoformat(),
                "target_date": (mon + timedelta(days=14)).isoformat(),
            },
        )
        assert rm_res.status_code == 201
        roadmap_id = UUID(rm_res.json()["id"])

    class _TimeoutLLM:
        async def generate_structured(self, **kwargs: Any) -> Any:
            del kwargs
            raise TimeoutError()

        async def stream_structured(self, **kwargs: Any) -> AsyncGenerator[str, None]:
            del kwargs
            yield "{}"

    async with async_session_factory() as session:
        quota = QuotaFacadeAdapter(session)
        res_id = await quota.reserve_quota(user_id=user_id, operation_type="MILESTONE_GEN", cost=1)
        await session.commit()

    job_id = uuid7()
    await sse_store.create_job(
        job_id=job_id,
        user_id=user_id,
        roadmap_id=roadmap_id,
        reservation_id=res_id,
        job_type="MILESTONE_GEN:FULL_SCOPE",
        operation=f"MILESTONE_GEN:FULL_SCOPE:{roadmap_id}",
    )

    async with async_session_factory() as session:
        exec_uc = ExecuteMilestoneGenerationUseCase(
            goal_repo=SqlAlchemyGoalRepository(session),
            roadmap_repo=SqlAlchemyRoadmapRepository(session),
            milestone_repo=SqlAlchemyMilestoneRepository(session),
            quota_facade=QuotaFacadeAdapter(session),
            llm_provider=_TimeoutLLM(),  # type: ignore[arg-type]
            sse_job_store=sse_store,
            uow=SqlAlchemyUnitOfWork(session),
        )
        with pytest.raises(TimeoutError):
            await exec_uc.execute(
                job_id=job_id,
                user_id=user_id,
                roadmap_id=roadmap_id,
                reservation_id=res_id,
                max_retries=0,
                now=now,
            )

    # Read from a fresh RedisSseJobStore instance to confirm Redis persistence
    reader_store = RedisSseJobStore(redis_url=_REDIS_URL, fallback_store=InMemorySseJobStore())
    job = await reader_store.get_job_for_user(job_id=job_id, user_id=user_id)
    assert job.status == "FAILED"
    failed_events = [ev for ev in job.events if ev.event == "failed"]
    assert len(failed_events) == 1
    assert failed_events[0].data["error_code"] == "AI_GATEWAY_TIMEOUT"
    assert failed_events[0].data["error"] == DEFAULT_SSE_TIMEOUT_MESSAGE
