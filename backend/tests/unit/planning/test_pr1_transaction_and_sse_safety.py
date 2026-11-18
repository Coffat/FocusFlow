from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from uuid6 import uuid7

from src.account.domain.exceptions.quota_exceptions import QuotaExceededException
from src.account.infrastructure.adapters.quota_facade_adapter import QuotaFacadeAdapter
from src.account.infrastructure.orm.user_orm import AIQuotaORM
from src.account.public_api import AvailabilitySnapshotDTO, LearnerProfileDTO
from src.evaluation.application.dtos.intelligence import GenerateWeeklyReviewRequestDTO
from src.evaluation.application.ports.intelligence_repository_port import (
    DuplicateWeeklyReviewConflictError,
)
from src.evaluation.application.use_cases.intelligence import (
    GenerateWeeklyReviewUseCase,
    WeeklyReviewWriteScope,
)
from src.evaluation.domain.models.intelligence import WeeklyReview
from src.execution.public_api import WeeklyExecutionMetricsDTO
from src.planning.application.ports.sse_job_port import (
    DEFAULT_SSE_TIMEOUT_MESSAGE,
    IdempotencyInProgressError,
    sanitize_sse_error_details,
)
from src.planning.application.use_cases.milestone_use_cases import (
    InitiateMilestoneGenerationUseCase,
)
from src.planning.application.use_cases.proposal_generation_use_cases import (
    ExecuteScheduleProposalGenerationUseCase,
    InitiateScheduleProposalGenerationUseCase,
)
from src.planning.application.use_cases.proposal_management_use_cases import (
    ApplyScheduleProposalUseCase,
)
from src.planning.domain.exceptions.planning_exceptions import (
    ProposalSupersededError,
    RoadmapNotFoundError,
)
from src.planning.domain.models.milestone import Milestone, MilestoneStatus
from src.planning.domain.models.roadmap import Roadmap, RoadmapStatus
from src.planning.domain.models.schedule import (
    OfficialSchedule,
    ScheduleProposal,
    ScheduleProposalStatus,
)
from src.planning.presentation import tasks as planning_tasks
from src.shared_kernel.application.llm_port import LLMGenerationResult
from src.shared_kernel.infrastructure.sse.job_store import InMemorySseJobStore


class _FakeUoW:
    def __init__(self, *, fail_on_commit: bool = False) -> None:
        self.commits = 0
        self.rollbacks = 0
        self._fail_on_commit = fail_on_commit

    async def __aenter__(self) -> _FakeUoW:
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if exc_type is not None:
            self.rollbacks += 1

    async def commit(self) -> None:
        if self._fail_on_commit:
            raise RuntimeError("simulated commit failure")
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1

    async def close(self) -> None:
        pass

    def collect_events_from(self, agg: Any) -> None:
        del agg


class _SlowQuotaFacade:
    def __init__(self, *, delay_seconds: float = 0.05, fail_reserve: bool = False) -> None:
        self.reserve_calls = 0
        self.release_calls: list[tuple[UUID, str]] = []
        self._delay = delay_seconds
        self._fail_reserve = fail_reserve

    async def check_quota_available(self, user_id: UUID, min_credits: int = 1) -> bool:
        del user_id, min_credits
        return not self._fail_reserve

    async def reserve_quota(
        self,
        user_id: UUID,
        operation_type: str = "ROADMAP_GEN",
        cost: int = 1,
        ttl_seconds: int = 120,
    ) -> UUID:
        del user_id, operation_type, cost, ttl_seconds
        if self._delay > 0:
            await asyncio.sleep(self._delay)
        self.reserve_calls += 1
        if self._fail_reserve:
            raise QuotaExceededException("Không đủ hạn ngạch AI: cần 1 credit, hiện còn 0 credit.")
        return uuid7()

    async def commit_reservation(self, *args: Any, **kwargs: Any) -> None:
        del args, kwargs

    async def release_reservation(self, reservation_id: UUID, reason: str = "RELEASED") -> None:
        self.release_calls.append((reservation_id, reason))


# =============================================================================
# BUG-03: Atomic Idempotency Slot Tests (InMemorySseJobStore & Use Cases)
# =============================================================================


@pytest.mark.asyncio
async def test_in_memory_idempotency_slot_claim_finalize_and_release_cas() -> None:
    store = InMemorySseJobStore()
    uid = uuid7()
    op = f"MILESTONE_GEN:FULL_SCOPE:{uuid7()}"

    c1, c2 = await asyncio.gather(
        store.claim_idempotency_slot(user_id=uid, operation=op, idempotency_key="k1"),
        store.claim_idempotency_slot(user_id=uid, operation=op, idempotency_key="k1"),
    )
    winners = [c for c in (c1, c2) if c.acquired]
    losers = [c for c in (c1, c2) if not c.acquired]
    assert len(winners) == 1
    assert len(losers) == 1
    assert losers[0].in_progress is True
    assert winners[0].token is not None

    # Wrong token cannot release or finalize
    assert (
        await store.release_idempotency_slot(
            user_id=uid, operation=op, idempotency_key="k1", token="wrong-token"
        )
        is False
    )
    assert (
        await store.finalize_idempotency_slot(
            user_id=uid,
            operation=op,
            idempotency_key="k1",
            token="wrong-token",
            job_id=uuid7(),
        )
        is False
    )

    # Correct token releases slot cleanly
    assert (
        await store.release_idempotency_slot(
            user_id=uid, operation=op, idempotency_key="k1", token=winners[0].token
        )
        is True
    )

    # Re-claim succeeds after release
    c3 = await store.claim_idempotency_slot(user_id=uid, operation=op, idempotency_key="k1")
    assert c3.acquired is True and c3.token is not None
    job_id = uuid7()
    await store.create_job(
        job_id=job_id,
        user_id=uid,
        roadmap_id=uuid7(),
        reservation_id=uuid7(),
        job_type="MILESTONE_GEN",
        operation=op,
        idempotency_key="k1",
        register_idempotency=False,
    )
    assert (
        await store.finalize_idempotency_slot(
            user_id=uid,
            operation=op,
            idempotency_key="k1",
            token=c3.token,
            job_id=job_id,
        )
        is True
    )

    c4 = await store.claim_idempotency_slot(user_id=uid, operation=op, idempotency_key="k1")
    assert c4.acquired is False
    assert c4.in_progress is False
    assert c4.existing_job is not None and c4.existing_job.job_id == job_id


@pytest.mark.asyncio
async def test_concurrent_initiate_milestone_gen_single_reservation_and_cleanup_on_failure() -> (
    None
):
    uid = uuid7()
    rid = uuid7()
    now = datetime(2026, 11, 18, 8, 0, tzinfo=UTC)
    roadmap = Roadmap(
        id=rid,
        user_id=uid,
        goal_id=uuid7(),
        title="R",
        start_date=date(2026, 11, 18),
        target_date=date(2026, 11, 30),
        status=RoadmapStatus.INITIALIZED,
        created_at=now,
        updated_at=now,
    )
    sse = InMemorySseJobStore()
    quota = _SlowQuotaFacade(delay_seconds=0.05)
    uow = _FakeUoW()
    uc = InitiateMilestoneGenerationUseCase(
        roadmap_repo=SimpleNamespace(get_by_id_for_user=AsyncMock(return_value=roadmap)),  # type: ignore[arg-type]
        quota_facade=quota,  # type: ignore[arg-type]
        sse_job_store=sse,
        uow=uow,  # type: ignore[arg-type]
        executor=None,
    )

    t1, t2, t3 = await asyncio.gather(
        uc.execute(user_id=uid, roadmap_id=rid, idempotency_key="idem-ms-race", run_inline=False),
        uc.execute(user_id=uid, roadmap_id=rid, idempotency_key="idem-ms-race", run_inline=False),
        uc.execute(user_id=uid, roadmap_id=rid, idempotency_key="idem-ms-race", run_inline=False),
    )

    assert quota.reserve_calls == 1
    assert uow.commits == 1
    assert t1.job_id == t2.job_id == t3.job_id
    existing_flags = sorted([t1.is_existing, t2.is_existing, t3.is_existing])
    assert existing_flags == [False, True, True]

    # Failure before commit releases slot so a retry can acquire and succeed
    failing_uow = _FakeUoW(fail_on_commit=True)
    uc_fail = InitiateMilestoneGenerationUseCase(
        roadmap_repo=SimpleNamespace(get_by_id_for_user=AsyncMock(return_value=roadmap)),  # type: ignore[arg-type]
        quota_facade=_SlowQuotaFacade(delay_seconds=0.0),  # type: ignore[arg-type]
        sse_job_store=sse,
        uow=failing_uow,  # type: ignore[arg-type]
        executor=None,
    )
    with pytest.raises(RuntimeError, match="simulated commit failure"):
        await uc_fail.execute(
            user_id=uid, roadmap_id=rid, idempotency_key="idem-ms-fail", run_inline=False
        )

    retry_ticket = await uc.execute(
        user_id=uid, roadmap_id=rid, idempotency_key="idem-ms-fail", run_inline=False
    )
    assert retry_ticket.is_existing is False
    assert quota.reserve_calls == 2


@pytest.mark.asyncio
async def test_concurrent_initiate_proposal_gen_single_reservation_and_409_in_progress() -> None:
    uid = uuid7()
    rid = uuid7()
    now = datetime(2026, 11, 18, 8, 0, tzinfo=UTC)
    roadmap = Roadmap(
        id=rid,
        user_id=uid,
        goal_id=uuid7(),
        title="R",
        start_date=date(2026, 11, 18),
        target_date=date(2026, 12, 10),
        status=RoadmapStatus.INITIALIZED,
        created_at=now,
        updated_at=now,
    )
    ms = Milestone(
        id=uuid7(),
        roadmap_id=rid,
        sequence_order=1,
        title="M1",
        estimated_effort_minutes=60,
        status=MilestoneStatus.APPROVED,
        created_at=now,
        updated_at=now,
    )
    avail = AvailabilitySnapshotDTO(
        user_id=uid, mode="MODE_A", daily_cap_minutes=120, weekly_capacity_minutes=600
    )
    sse = InMemorySseJobStore()
    quota = _SlowQuotaFacade(delay_seconds=0.05)
    uow = _FakeUoW()
    uc = InitiateScheduleProposalGenerationUseCase(
        roadmap_repo=SimpleNamespace(
            get_by_id_for_user=AsyncMock(return_value=roadmap),
            list_by_user_id=AsyncMock(return_value=[]),
        ),  # type: ignore[arg-type]
        milestone_repo=SimpleNamespace(list_by_roadmap_id=AsyncMock(return_value=[ms])),  # type: ignore[arg-type]
        quota_facade=quota,  # type: ignore[arg-type]
        sse_job_store=sse,
        uow=uow,  # type: ignore[arg-type]
        availability_query_port=SimpleNamespace(
            get_active_availability=AsyncMock(return_value=avail)
        ),  # type: ignore[arg-type]
        execution_sync_port=SimpleNamespace(get_tasks_for_roadmaps=AsyncMock(return_value=[])),  # type: ignore[arg-type]
    )

    p1, p2 = await asyncio.gather(
        uc.execute(user_id=uid, roadmap_id=rid, idempotency_key="idem-prop-race", run_inline=False),
        uc.execute(user_id=uid, roadmap_id=rid, idempotency_key="idem-prop-race", run_inline=False),
    )
    assert quota.reserve_calls == 1
    assert p1.job_id == p2.job_id
    assert sorted([p1.is_existing, p2.is_existing]) == [False, True]

    # When a winner holds PENDING beyond max_wait_seconds, loser raises IdempotencyInProgressError (409)
    op = f"SCHEDULE_PROPOSAL_GEN:{rid}"
    held = await sse.claim_idempotency_slot(
        user_id=uid, operation=op, idempotency_key="idem-prop-stuck", pending_ttl_seconds=30
    )
    assert held.acquired is True
    with pytest.raises(IdempotencyInProgressError) as exc_info:
        from src.planning.application.ports.sse_job_port import claim_idempotency_slot_with_wait

        await claim_idempotency_slot_with_wait(
            sse,
            user_id=uid,
            operation=op,
            idempotency_key="idem-prop-stuck",
            max_wait_seconds=0.06,
        )
    assert exc_info.value.code == "IDEMPOTENCY_REQUEST_IN_PROGRESS"


# =============================================================================
# BUG-04: Stale/Superseded Proposal Apply Checks
# =============================================================================


@pytest.mark.asyncio
async def test_apply_rejects_superseded_applied_proposal_and_mismatched_idempotency() -> None:
    t1 = datetime(2026, 11, 16, 8, 0, tzinfo=UTC)
    t2 = datetime(2026, 11, 16, 9, 0, tzinfo=UTC)
    t3 = datetime(2026, 11, 16, 10, 0, tzinfo=UTC)
    uid = uuid7()
    rid = uuid7()
    ms = Milestone(
        id=uuid7(),
        roadmap_id=rid,
        sequence_order=1,
        title="M1",
        status=MilestoneStatus.APPROVED,
        created_at=t1,
        updated_at=t1,
    )
    roadmap = Roadmap(
        id=rid,
        user_id=uid,
        goal_id=uuid7(),
        title="R",
        start_date=date(2026, 11, 16),
        target_date=date(2026, 11, 20),
        status=RoadmapStatus.ACTIVE,
        created_at=t1,
        updated_at=t3,
    )
    p1 = ScheduleProposal(
        id=uuid7(),
        roadmap_id=rid,
        user_id=uid,
        proposal_data={"applied_idempotency_key": "k1", "tasks": []},
        status=ScheduleProposalStatus.APPLIED,
        applied_at=t1,
        created_at=t1,
        updated_at=t1,
    )
    p2 = ScheduleProposal(
        id=uuid7(),
        roadmap_id=rid,
        user_id=uid,
        proposal_data={"applied_idempotency_key": "k2", "tasks": []},
        status=ScheduleProposalStatus.APPLIED,
        applied_at=t2,
        created_at=t2,
        updated_at=t2,
    )
    sched = OfficialSchedule(
        id=uuid7(),
        roadmap_id=rid,
        total_sessions=1,
        total_planned_minutes=60,
        activated_at=t2,
        created_at=t1,
        updated_at=t2,
    )
    avail = AvailabilitySnapshotDTO(
        user_id=uid, mode="MODE_A", daily_cap_minutes=120, weekly_capacity_minutes=600
    )

    all_props = [p2, p1]
    prop_repo = SimpleNamespace(
        get_by_id=lambda pid: asyncio.sleep(
            0, result=next((p for p in all_props if p.id == pid), None)
        ),
        list_by_roadmap_id=lambda roadmap_id: asyncio.sleep(0, result=list(all_props)),
    )
    uc = ApplyScheduleProposalUseCase(
        roadmap_repo=SimpleNamespace(get_by_id_for_user=AsyncMock(return_value=roadmap)),  # type: ignore[arg-type]
        milestone_repo=SimpleNamespace(list_by_roadmap_id=AsyncMock(return_value=[ms])),  # type: ignore[arg-type]
        proposal_repo=prop_repo,  # type: ignore[arg-type]
        schedule_repo=SimpleNamespace(get_by_roadmap_id=AsyncMock(return_value=sched)),  # type: ignore[arg-type]
        block_repo=SimpleNamespace(),  # type: ignore[arg-type]
        availability_query_port=SimpleNamespace(
            get_active_availability=AsyncMock(return_value=avail)
        ),  # type: ignore[arg-type]
        execution_sync_port=SimpleNamespace(),  # type: ignore[arg-type]
        schedule_change_log_port=SimpleNamespace(),  # type: ignore[arg-type]
        uow=_FakeUoW(),  # type: ignore[arg-type]
    )

    # 1. Re-applying superseded P1 (even with its original key k1) must raise 409 ProposalSupersededError
    with pytest.raises(ProposalSupersededError) as exc1:
        await uc.execute(user_id=uid, roadmap_id=rid, proposal_id=p1.id, idempotency_key="k1")
    assert exc1.value.code == "PROPOSAL_SUPERSEDED"

    # 2. Re-applying latest P2 with matching key k2 returns 200 idempotently
    res_ok = await uc.execute(user_id=uid, roadmap_id=rid, proposal_id=p2.id, idempotency_key="k2")
    assert res_ok.proposal.id == p2.id

    # 3. Re-applying latest P2 with mismatched key k3 or missing key raises ProposalSupersededError
    with pytest.raises(ProposalSupersededError):
        await uc.execute(user_id=uid, roadmap_id=rid, proposal_id=p2.id, idempotency_key="k3")
    with pytest.raises(ProposalSupersededError):
        await uc.execute(user_id=uid, roadmap_id=rid, proposal_id=p2.id, idempotency_key=None)

    # 4. If P2 was applied WITHOUT idempotency key (applied_key=None), replaying WITH key k9 raises 409
    p2.proposal_data = {"tasks": []}
    with pytest.raises(ProposalSupersededError):
        await uc.execute(user_id=uid, roadmap_id=rid, proposal_id=p2.id, idempotency_key="k9")

    # 5. If a newer DRAFT exists after P2 was applied, re-applying P2 raises ProposalSupersededError
    p3_draft = ScheduleProposal(
        id=uuid7(),
        roadmap_id=rid,
        user_id=uid,
        proposal_data={"tasks": []},
        status=ScheduleProposalStatus.DRAFT,
        created_at=t3,
        updated_at=t3,
    )
    all_props.append(p3_draft)
    with pytest.raises(ProposalSupersededError):
        await uc.execute(user_id=uid, roadmap_id=rid, proposal_id=p2.id, idempotency_key=None)


# =============================================================================
# BUG-05: Quota Unit Compatibility & Non-Negative Error Display
# =============================================================================


@pytest.mark.asyncio
async def test_quota_in_memory_compatibility_and_non_negative_error_message() -> None:
    uid = uuid7()
    quota = AIQuotaORM(
        id=uuid7(),
        user_id=uid,
        free_credits_remaining=1,
        paid_credits_remaining=0,
        reserved_calls=2,
        used_calls=0,
    )
    assert quota.monthly_limit >= 2

    class _MockSession:
        def add(self, item: Any) -> None:
            del item

        async def flush(self) -> None:
            pass

        async def execute(self, stmt: Any, params: Any = None) -> Any:
            del stmt, params
            return SimpleNamespace(scalar_one_or_none=lambda: quota)

    adapter = QuotaFacadeAdapter(session=_MockSession())  # type: ignore[arg-type]
    with pytest.raises(QuotaExceededException) as exc:
        await adapter.reserve_quota(user_id=uid, operation_type="MILESTONE_GEN", cost=1)
    assert "hiện còn -" not in exc.value.message
    assert "hiện còn 0 credit" in exc.value.message
    AIQuotaORM._credit_ledger_by_user.pop(uid, None)


# =============================================================================
# BUG-07: Weekly Review Duplicate Period Pre-Check & Conflict Fallback
# =============================================================================


@pytest.mark.asyncio
async def test_weekly_review_precheck_and_conflict_skips_llm_and_returns_existing() -> None:
    uid = uuid7()
    rid = uuid7()
    p_start = date(2026, 11, 2)
    p_end = date(2026, 11, 8)
    existing = WeeklyReview(
        id=uuid7(),
        roadmap_id=rid,
        user_id=uid,
        period_start=p_start,
        period_end=p_end,
        quantitative_summary={"completed_minutes": 120},
        strengths_feedback="Existing strengths",
        bottlenecks_feedback="Existing bottlenecks",
        action_recommendations="Existing actions",
        user_reflection_payload={},
        generated_at=datetime(2026, 11, 8, 12, 0, tzinfo=UTC),
    )

    llm_calls = 0

    class _SpyLLM:
        async def generate_structured(self, **kwargs: Any) -> LLMGenerationResult:
            nonlocal llm_calls
            del kwargs
            llm_calls += 1
            return LLMGenerationResult(
                payload={
                    "strengths_feedback": "S",
                    "bottlenecks_feedback": "B",
                    "action_recommendations": "A",
                },
                prompt_tokens=10,
                output_tokens=10,
            )

        async def stream_structured(self, **kwargs: Any) -> AsyncIterator[str]:
            del kwargs
            yield "{}"

    ownership = SimpleNamespace(
        get_milestone=AsyncMock(return_value=None),
        roadmap_belongs_to=AsyncMock(return_value=True),
    )
    repo_precheck = SimpleNamespace(
        get_weekly_review_for_period=AsyncMock(return_value=existing),
    )
    uow = _FakeUoW()
    uc_pre = GenerateWeeklyReviewUseCase(
        repository=repo_precheck,  # type: ignore[arg-type]
        ownership=ownership,  # type: ignore[arg-type]
        uow=uow,  # type: ignore[arg-type]
        llm_provider=_SpyLLM(),  # type: ignore[arg-type]
    )
    res = await uc_pre.execute(
        uid,
        GenerateWeeklyReviewRequestDTO(
            roadmap_id=rid, period_start=p_start, period_end=p_end, reflection={}
        ),
    )
    assert res.id == existing.id
    assert llm_calls == 0

    # Race conflict in Phase 3 returns existing review cleanly
    repo_race = SimpleNamespace(
        get_weekly_review_for_period=AsyncMock(return_value=None),
        get_user_proof_metrics=AsyncMock(
            return_value={"proofs_count": 0, "avg_proof_score": None, "avg_proof_confidence": None}
        ),
        create_weekly_review=AsyncMock(
            side_effect=DuplicateWeeklyReviewConflictError(existing_review=existing)
        ),
    )

    @asynccontextmanager
    async def _write_scope() -> Any:
        yield WeeklyReviewWriteScope(uow=_FakeUoW(), repository=repo_race)  # type: ignore[arg-type]

    uc_race = GenerateWeeklyReviewUseCase(
        repository=repo_race,  # type: ignore[arg-type]
        ownership=ownership,  # type: ignore[arg-type]
        uow=_FakeUoW(),  # type: ignore[arg-type]
        execution_metrics_port=SimpleNamespace(
            get_roadmap_period_metrics=AsyncMock(return_value=WeeklyExecutionMetricsDTO())
        ),
        write_scope_factory=_write_scope,
    )
    res_race = await uc_race.execute(
        uid,
        GenerateWeeklyReviewRequestDTO(
            roadmap_id=rid, period_start=p_start, period_end=p_end, reflection={}
        ),
    )
    assert res_race.id == existing.id


# =============================================================================
# BUG-02: SSE Error Reporting Sanitizer & Taskiq Failure Handling
# =============================================================================


@pytest.mark.asyncio
async def test_sanitize_sse_error_details_and_proposal_timeout_sse_emission() -> None:
    assert sanitize_sse_error_details(TimeoutError()) == (
        "AI_GATEWAY_TIMEOUT",
        DEFAULT_SSE_TIMEOUT_MESSAGE,
    )
    assert sanitize_sse_error_details(RoadmapNotFoundError()) == (
        "ROADMAP_NOT_FOUND",
        "Không tìm thấy lộ trình học tập.",
    )
    code, msg = sanitize_sse_error_details(RuntimeError("sensitive db dsn=postgres://secret"))
    assert code == "AI_GENERATION_FAILED"
    assert "secret" not in msg
    assert len(msg) > 0

    # ExecuteScheduleProposalGenerationUseCase emits AI_GATEWAY_TIMEOUT on TimeoutError
    uid = uuid7()
    rid = uuid7()
    job_id = uuid7()
    res_id = uuid7()
    now = datetime(2026, 11, 18, 8, 0, tzinfo=UTC)
    roadmap = Roadmap(
        id=rid,
        user_id=uid,
        goal_id=uuid7(),
        title="R",
        start_date=date(2026, 11, 18),
        target_date=date(2026, 12, 10),
        status=RoadmapStatus.INITIALIZED,
        created_at=now,
        updated_at=now,
    )
    ms = Milestone(
        id=uuid7(),
        roadmap_id=rid,
        sequence_order=1,
        title="M1",
        estimated_effort_minutes=60,
        status=MilestoneStatus.APPROVED,
        created_at=now,
        updated_at=now,
    )
    avail = AvailabilitySnapshotDTO(
        user_id=uid, mode="MODE_A", daily_cap_minutes=120, weekly_capacity_minutes=600
    )
    sse = InMemorySseJobStore()
    await sse.create_job(
        job_id=job_id,
        user_id=uid,
        roadmap_id=rid,
        reservation_id=res_id,
        job_type="SCHEDULE_PROPOSAL_GEN",
        operation=f"SCHEDULE_PROPOSAL_GEN:{rid}",
    )
    quota = _SlowQuotaFacade(delay_seconds=0.0)

    class _TimeoutLLM:
        async def generate_structured(self, **kwargs: Any) -> Any:
            del kwargs
            raise TimeoutError()

        async def stream_structured(self, **kwargs: Any) -> AsyncIterator[str]:
            del kwargs
            yield "{}"

    exec_uc = ExecuteScheduleProposalGenerationUseCase(
        goal_repo=SimpleNamespace(get_by_id=AsyncMock(return_value=None)),  # type: ignore[arg-type]
        roadmap_repo=SimpleNamespace(
            get_by_id_for_user=AsyncMock(return_value=roadmap),
            list_by_user_id=AsyncMock(return_value=[]),
        ),  # type: ignore[arg-type]
        milestone_repo=SimpleNamespace(list_by_roadmap_id=AsyncMock(return_value=[ms])),  # type: ignore[arg-type]
        proposal_repo=SimpleNamespace(),  # type: ignore[arg-type]
        availability_query_port=SimpleNamespace(
            get_active_availability=AsyncMock(return_value=avail)
        ),  # type: ignore[arg-type]
        learner_profile_port=SimpleNamespace(
            get_learner_profile=AsyncMock(return_value=LearnerProfileDTO(user_id=uid))
        ),  # type: ignore[arg-type]
        execution_sync_port=SimpleNamespace(get_tasks_for_roadmaps=AsyncMock(return_value=[])),  # type: ignore[arg-type]
        quota_facade=quota,  # type: ignore[arg-type]
        llm_provider=_TimeoutLLM(),  # type: ignore[arg-type]
        sse_job_store=sse,
        uow=_FakeUoW(),  # type: ignore[arg-type]
        enable_tier3_judge=False,
    )

    with pytest.raises(TimeoutError):
        await exec_uc.execute(
            job_id=job_id,
            user_id=uid,
            roadmap_id=rid,
            reservation_id=res_id,
            max_retries=0,
            now=now,
            decomposer_architecture_mode="monolithic",
        )

    assert quota.release_calls == [(res_id, "AI_GATEWAY_TIMEOUT")]
    job = await sse.get_job_for_user(job_id=job_id, user_id=uid)
    failed_events = [ev for ev in job.events if ev.event == "failed"]
    assert len(failed_events) == 1
    assert failed_events[0].data["error_code"] == "AI_GATEWAY_TIMEOUT"
    assert failed_events[0].data["error"] == DEFAULT_SSE_TIMEOUT_MESSAGE


@pytest.mark.asyncio
async def test_tasks_does_not_duplicate_failed_event_and_releases_on_setup_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    uid = uuid7()
    rid = uuid7()
    job_id = uuid7()
    res_id = uuid7()
    sse = InMemorySseJobStore()
    await sse.create_job(
        job_id=job_id,
        user_id=uid,
        roadmap_id=rid,
        reservation_id=res_id,
        job_type="MILESTONE_GEN",
        operation=f"MILESTONE_GEN:{rid}",
    )

    class _FakeSessionCM:
        async def __aenter__(self) -> Any:
            return SimpleNamespace(rollback=AsyncMock())

        async def __aexit__(self, *args: Any) -> None:
            del args

    quota = _SlowQuotaFacade(delay_seconds=0.0)
    monkeypatch.setattr(planning_tasks, "async_session_factory", lambda: _FakeSessionCM())
    monkeypatch.setattr(planning_tasks, "get_planning_uow", lambda s: _FakeUoW())
    monkeypatch.setattr(planning_tasks, "get_planning_quota_facade", lambda s: quota)
    monkeypatch.setattr(planning_tasks, "get_goal_repository", lambda s: SimpleNamespace())
    monkeypatch.setattr(planning_tasks, "get_roadmap_repository", lambda s: SimpleNamespace())
    monkeypatch.setattr(planning_tasks, "get_milestone_repository", lambda s: SimpleNamespace())
    monkeypatch.setattr(planning_tasks, "get_knowledge_base_repository", lambda s: None)
    monkeypatch.setattr(planning_tasks, "get_planning_learner_memory_port", lambda s: None)
    monkeypatch.setattr(planning_tasks, "get_knowledge_source_repository", lambda s: None)
    monkeypatch.setattr(planning_tasks, "get_planning_workflow_repository", lambda s: None)
    monkeypatch.setattr(
        planning_tasks,
        "_resolve_dep",
        AsyncMock(
            side_effect=lambda fn, df: (
                sse if fn is planning_tasks.get_sse_job_store else MagicMock()
            )
        ),
    )

    # Case 1: execute() records terminal FAILED -> tasks.py must NOT append a second failed event
    class _FailingUC:
        async def execute(self, **kwargs: Any) -> None:
            del kwargs
            await sse.append_event(
                job_id=job_id,
                event="failed",
                status="FAILED",
                data={
                    "stage": "FAILED",
                    "progress": 100,
                    "error": DEFAULT_SSE_TIMEOUT_MESSAGE,
                    "error_code": "AI_GATEWAY_TIMEOUT",
                },
            )
            raise TimeoutError()

    monkeypatch.setattr(
        planning_tasks, "get_execute_milestone_generation_use_case", lambda **kw: _FailingUC()
    )
    monkeypatch.setattr(planning_tasks, "get_planning_availability_query_port", lambda s: None)
    monkeypatch.setattr(planning_tasks, "get_planning_execution_sync_port", lambda s: None)
    monkeypatch.setattr(planning_tasks, "get_schedule_block_repository", lambda s: None)
    monkeypatch.setattr(planning_tasks, "get_planning_user_query_port", lambda s: None)
    monkeypatch.setattr(
        planning_tasks, "get_planning_calendar_connection_query_port", lambda s: None
    )
    monkeypatch.setattr(planning_tasks, "get_schedule_proposal_repository", lambda s: None)

    await planning_tasks.execute_ai_roadmap_generation(
        job_id=str(job_id),
        reservation_id=str(res_id),
        user_id=str(uid),
        roadmap_id=str(rid),
        job_type="MILESTONE_GEN",
    )
    job = await sse.get_job_for_user(job_id=job_id, user_id=uid)
    assert len([ev for ev in job.events if ev.event == "failed"]) == 1
    assert quota.release_calls == []

    # Case 2: setup fails BEFORE execute() -> tasks.py releases reservation_id & emits sanitized failed event
    job_id_2 = uuid7()
    res_id_2 = uuid7()
    await sse.create_job(
        job_id=job_id_2,
        user_id=uid,
        roadmap_id=rid,
        reservation_id=res_id_2,
        job_type="MILESTONE_GEN",
        operation=f"MILESTONE_GEN:{rid}",
    )

    async def _broken_resolve(fn: Any, df: Any) -> Any:
        if fn is planning_tasks.get_sse_job_store:
            return sse
        raise RuntimeError("dependency setup exploded")

    monkeypatch.setattr(planning_tasks, "_resolve_dep", _broken_resolve)
    await planning_tasks.execute_ai_roadmap_generation(
        job_id=str(job_id_2),
        reservation_id=str(res_id_2),
        user_id=str(uid),
        roadmap_id=str(rid),
        job_type="MILESTONE_GEN",
    )
    assert quota.release_calls == [(res_id_2, "AI_GENERATION_FAILED")]
    job_2 = await sse.get_job_for_user(job_id=job_id_2, user_id=uid)
    failed_2 = [ev for ev in job_2.events if ev.event == "failed"]
    assert len(failed_2) == 1
    assert failed_2[0].data["error_code"] == "AI_GENERATION_FAILED"
    assert "error" in failed_2[0].data and "code" not in failed_2[0].data
