"""Unit & DB tests for idempotent release_reservation and outer CancelledError asyncio.shield cleanup."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime
from types import SimpleNamespace
from typing import Any
from uuid import UUID

import pytest
from sqlalchemy import delete, select
from uuid6 import uuid7

from src.account.domain.exceptions.quota_exceptions import QuotaReservationNotFoundError
from src.account.infrastructure.adapters.quota_facade_adapter import QuotaFacadeAdapter
from src.account.infrastructure.orm import UserORM
from src.account.infrastructure.orm.user_orm import AIQuotaORM, AIQuotaReservationORM
from src.account.public_api import AvailabilitySnapshotDTO, LearnerProfileDTO
from src.planning.application.use_cases.clarification_use_cases import (
    GenerateClarificationQuestionsUseCase,
    SubmitClarificationAnswersUseCase,
)
from src.planning.application.use_cases.milestone_use_cases import (
    ExecuteMilestoneGenerationUseCase,
)
from src.planning.application.use_cases.proposal_generation_use_cases import (
    ExecuteScheduleProposalGenerationUseCase,
)
from src.planning.domain.models.goal import Goal, GoalStatus
from src.planning.domain.models.milestone import Milestone, MilestoneStatus
from src.planning.domain.models.roadmap import Roadmap, RoadmapStatus
from src.shared_kernel.application.harness.execution_manager import AIExecutionManager
from src.shared_kernel.infrastructure.database.session import async_session_factory


class _DummyUoW:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    async def __aenter__(self) -> _DummyUoW:
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if exc_type is not None:
            self.rollbacks += 1

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


class _RecordingQuotaFacade:
    def __init__(self, *, raise_not_found_on_release: bool = False) -> None:
        self.reserved: list[UUID] = []
        self.released: list[tuple[UUID, str]] = []
        self.release_completed: list[UUID] = []
        self.committed: list[UUID] = []
        self._raise_not_found_on_release = raise_not_found_on_release

    async def check_quota_available(self, user_id: UUID, min_credits: int = 1) -> bool:
        del user_id, min_credits
        return True

    async def reserve_quota(
        self,
        user_id: UUID,
        operation_type: str = "ROADMAP_GEN",
        cost: int = 1,
        ttl_seconds: int = 120,
    ) -> UUID:
        del user_id, operation_type, cost, ttl_seconds
        rid = uuid7()
        self.reserved.append(rid)
        return rid

    async def commit_reservation(
        self,
        reservation_id: UUID,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        model_name: str = "gemini-3.8-flash",
    ) -> None:
        del prompt_tokens, completion_tokens, model_name
        self.committed.append(reservation_id)

    async def release_reservation(
        self,
        reservation_id: UUID,
        reason: str = "RELEASED",
    ) -> None:
        self.released.append((reservation_id, reason))
        # Yield control so unshielded cancellation would abort here
        await asyncio.sleep(0.01)
        if self._raise_not_found_on_release:
            raise QuotaReservationNotFoundError("not found")
        self.release_completed.append(reservation_id)


class _CancellingLLM:
    async def generate_structured(self, **kwargs: Any) -> Any:
        del kwargs
        raise asyncio.CancelledError

    async def stream_structured(self, **kwargs: Any) -> AsyncIterator[str]:
        del kwargs
        yield "{}"


class _DummySSE:
    def __init__(self) -> None:
        self.events: list[tuple[str, str]] = []

    async def append_event(
        self,
        *,
        job_id: UUID,
        event: str,
        status: str,
        data: dict[str, Any],
    ) -> None:
        del job_id, data
        self.events.append((event, status))


@pytest.mark.asyncio
async def test_quota_facade_release_reservation_is_idempotent_on_double_committed_and_missing() -> (
    None
):
    """QuotaFacadeAdapter.release_reservation is safe on double-release, COMMITTED, and missing IDs."""
    user_id = uuid7()
    async with async_session_factory() as session:
        session.add(
            UserORM(
                id=user_id,
                email=f"quota_idem_{user_id.hex[:8]}@focusflow.vn",
                password_hash="argon2id$mockhash",
                full_name="Quota Idem",
                timezone="Asia/Ho_Chi_Minh",
                role="LEARNER",
                tier="FREE",
                is_locked=False,
            )
        )
        await session.commit()

    try:
        async with async_session_factory() as session:
            facade = QuotaFacadeAdapter(session=session)
            res_1 = await facade.reserve_quota(user_id=user_id, operation_type="ROADMAP_GEN")
            await session.commit()

            # Double release does not crash or double-decrement reserved_calls
            await facade.release_reservation(res_1, reason="FIRST")
            await session.commit()
            await facade.release_reservation(res_1, reason="SECOND")
            await session.commit()

            quota = (
                await session.execute(select(AIQuotaORM).where(AIQuotaORM.user_id == user_id))
            ).scalar_one()
            assert quota.reserved_calls == 0

            # Releasing a COMMITTED reservation is a safe no-op
            res_2 = await facade.reserve_quota(user_id=user_id, operation_type="ROADMAP_GEN")
            await facade.commit_reservation(res_2, prompt_tokens=10, completion_tokens=5)
            await facade.release_reservation(res_2, reason="LATE_CANCEL")
            await session.commit()

            res_2_row = (
                await session.execute(
                    select(AIQuotaReservationORM).where(AIQuotaReservationORM.id == res_2)
                )
            ).scalar_one()
            assert res_2_row.status == "COMMITTED"

            # Releasing a non-existent reservation does not raise
            await facade.release_reservation(uuid7(), reason="MISSING")
    finally:
        AIQuotaORM._credit_ledger_by_user.pop(user_id, None)
        async with async_session_factory() as session:
            await session.execute(delete(UserORM).where(UserORM.id == user_id))
            await session.commit()


@pytest.mark.asyncio
async def test_ai_execution_manager_ignores_not_found_on_release() -> None:
    """AIExecutionManager._release_once swallows QuotaReservationNotFoundError safely."""
    quota = _RecordingQuotaFacade(raise_not_found_on_release=True)
    mgr = AIExecutionManager(provider=_CancellingLLM(), quota=quota, max_retries=0)  # type: ignore[arg-type]

    with pytest.raises(asyncio.CancelledError):
        await mgr.execute(
            user_id=uuid7(),
            operation_type="TEST_OP",
            system_prompt="sys",
            user_prompt="usr",
            response_schema={"type": "object"},
        )
    assert len(quota.released) == 1


@pytest.mark.asyncio
async def test_clarification_questions_cancelled_error_shields_release() -> None:
    """CancelledError during GenerateClarificationQuestionsUseCase shields release_reservation."""
    user_id = uuid7()
    goal_id = uuid7()
    now = datetime(2026, 11, 16, 8, 0, tzinfo=UTC)
    goal = Goal(
        id=goal_id,
        user_id=user_id,
        title="Học Rust Systems",
        raw_description="Xây dựng CLI tool",
        target_date=date(2026, 12, 30),
        prior_knowledge_level="BEGINNER",
        status=GoalStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
    goal_repo = SimpleNamespace(
        get_by_id_for_user=lambda **kw: asyncio.sleep(0, result=goal),
        save=lambda g: asyncio.sleep(0, result=g),
    )
    quota = _RecordingQuotaFacade()
    uc = GenerateClarificationQuestionsUseCase(
        goal_repo=goal_repo,  # type: ignore[arg-type]
        quota_facade=quota,  # type: ignore[arg-type]
        llm_provider=_CancellingLLM(),  # type: ignore[arg-type]
        uow=_DummyUoW(),  # type: ignore[arg-type]
    )

    with pytest.raises(asyncio.CancelledError):
        await uc.execute(user_id=user_id, goal_id=goal_id, now=now)

    assert len(quota.reserved) == 1
    assert quota.release_completed == [quota.reserved[0]]


@pytest.mark.asyncio
async def test_clarification_followup_cancelled_error_shields_release() -> None:
    """CancelledError during _try_generate_follow_up shields release_reservation."""
    user_id = uuid7()
    goal_id = uuid7()
    session_id = uuid7()
    quota = _RecordingQuotaFacade()
    uc = SubmitClarificationAnswersUseCase(
        goal_repo=SimpleNamespace(),  # type: ignore[arg-type]
        uow=_DummyUoW(),  # type: ignore[arg-type]
        quota_facade=quota,  # type: ignore[arg-type]
        llm_provider=_CancellingLLM(),  # type: ignore[arg-type]
    )

    with pytest.raises(asyncio.CancelledError):
        await uc._try_generate_follow_up(
            user_id=user_id,
            goal_id=goal_id,
            session_id=session_id,
            gap={"dimension": "PRIOR_KNOWLEDGE", "status": "PARTIAL"},
            prior_answers=[],
        )

    assert len(quota.reserved) == 1
    assert quota.released == [(quota.reserved[0], "CANCELLED")]
    assert quota.release_completed == [quota.reserved[0]]


@pytest.mark.asyncio
async def test_milestone_generation_cancelled_error_shields_release() -> None:
    """CancelledError during ExecuteMilestoneGenerationUseCase shields release_reservation."""
    user_id = uuid7()
    goal_id = uuid7()
    roadmap_id = uuid7()
    reservation_id = uuid7()
    now = datetime(2026, 11, 16, 8, 0, tzinfo=UTC)
    goal = Goal(
        id=goal_id,
        user_id=user_id,
        title="Học FastAPI",
        raw_description="Build APIs",
        target_date=date(2026, 12, 30),
        prior_knowledge_level="BEGINNER",
        status=GoalStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
    roadmap = Roadmap(
        id=roadmap_id,
        user_id=user_id,
        goal_id=goal_id,
        title="FastAPI Roadmap",
        start_date=date(2026, 11, 16),
        target_date=date(2026, 12, 30),
        status=RoadmapStatus.INITIALIZED,
        created_at=now,
        updated_at=now,
    )
    quota = _RecordingQuotaFacade()
    sse = _DummySSE()
    uc = ExecuteMilestoneGenerationUseCase(
        goal_repo=SimpleNamespace(get_by_id=lambda gid: asyncio.sleep(0, result=goal)),  # type: ignore[arg-type]
        roadmap_repo=SimpleNamespace(
            get_by_id_for_user=lambda rid, uid: asyncio.sleep(0, result=roadmap)
        ),  # type: ignore[arg-type]
        milestone_repo=SimpleNamespace(),  # type: ignore[arg-type]
        quota_facade=quota,  # type: ignore[arg-type]
        llm_provider=_CancellingLLM(),  # type: ignore[arg-type]
        sse_job_store=sse,  # type: ignore[arg-type]
        uow=_DummyUoW(),  # type: ignore[arg-type]
    )

    with pytest.raises(asyncio.CancelledError):
        await uc.execute(
            job_id=uuid7(),
            user_id=user_id,
            roadmap_id=roadmap_id,
            reservation_id=reservation_id,
            now=now,
        )

    assert quota.released == [(reservation_id, "CANCELLED")]
    assert quota.release_completed == [reservation_id]
    assert ("failed", "FAILED") in sse.events


@pytest.mark.asyncio
async def test_proposal_generation_cancelled_error_shields_release() -> None:
    """CancelledError during ExecuteScheduleProposalGenerationUseCase shields release_reservation."""
    user_id = uuid7()
    goal_id = uuid7()
    roadmap_id = uuid7()
    reservation_id = uuid7()
    now = datetime(2026, 11, 16, 8, 0, tzinfo=UTC)
    goal = Goal(
        id=goal_id,
        user_id=user_id,
        title="Học FastAPI",
        raw_description="Build APIs",
        target_date=date(2026, 12, 30),
        prior_knowledge_level="BEGINNER",
        status=GoalStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
    roadmap = Roadmap(
        id=roadmap_id,
        user_id=user_id,
        goal_id=goal_id,
        title="FastAPI Roadmap",
        start_date=date(2026, 11, 16),
        target_date=date(2026, 12, 30),
        status=RoadmapStatus.INITIALIZED,
        created_at=now,
        updated_at=now,
    )
    milestone = Milestone(
        id=uuid7(),
        roadmap_id=roadmap_id,
        sequence_order=1,
        title="M1",
        status=MilestoneStatus.APPROVED,
        estimated_effort_minutes=120,
        created_at=now,
        updated_at=now,
    )
    avail = AvailabilitySnapshotDTO(
        user_id=user_id,
        mode="MODE_A",
        daily_cap_minutes=120,
        weekly_capacity_minutes=600,
    )
    quota = _RecordingQuotaFacade()
    sse = _DummySSE()
    uc = ExecuteScheduleProposalGenerationUseCase(
        goal_repo=SimpleNamespace(get_by_id=lambda gid: asyncio.sleep(0, result=goal)),  # type: ignore[arg-type]
        roadmap_repo=SimpleNamespace(
            get_by_id_for_user=lambda rid, uid: asyncio.sleep(0, result=roadmap),
            list_by_user_id=lambda uid, status=None: asyncio.sleep(0, result=[]),
        ),  # type: ignore[arg-type]
        milestone_repo=SimpleNamespace(
            list_by_roadmap_id=lambda rid: asyncio.sleep(0, result=[milestone]),
        ),  # type: ignore[arg-type]
        proposal_repo=SimpleNamespace(),  # type: ignore[arg-type]
        availability_query_port=SimpleNamespace(
            get_active_availability=lambda uid: asyncio.sleep(0, result=avail),
        ),  # type: ignore[arg-type]
        learner_profile_port=SimpleNamespace(
            get_learner_profile=lambda uid: asyncio.sleep(
                0, result=LearnerProfileDTO(user_id=user_id)
            ),
        ),  # type: ignore[arg-type]
        execution_sync_port=SimpleNamespace(
            get_tasks_for_roadmaps=lambda rids, roadmap_target_dates=None: asyncio.sleep(
                0, result=[]
            ),
        ),  # type: ignore[arg-type]
        quota_facade=quota,  # type: ignore[arg-type]
        llm_provider=_CancellingLLM(),  # type: ignore[arg-type]
        sse_job_store=sse,  # type: ignore[arg-type]
        uow=_DummyUoW(),  # type: ignore[arg-type]
        enable_tier3_judge=False,
    )

    with pytest.raises(asyncio.CancelledError):
        await uc.execute(
            job_id=uuid7(),
            user_id=user_id,
            roadmap_id=roadmap_id,
            reservation_id=reservation_id,
            now=now,
        )

    assert quota.released == [(reservation_id, "CANCELLED")]
    assert quota.release_completed == [reservation_id]
    assert ("failed", "FAILED") in sse.events
