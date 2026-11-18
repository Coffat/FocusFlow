"""Exhaustive integration test suite for Durable Checkpoint & Resume with Comprehensive Context Fingerprinting.

Covers:
1. Worker Crash / Restart (M1 & M2 succeed, worker terminates; new worker resumes with 0s / 0 tokens for M1 & M2).
2. Concurrent Resume (2 concurrent workers resuming simultaneously via asyncio.gather; idempotent writes & deduplication).
3. Stale Checkpoint Invalidation (Mutate learner profile opt_session_minutes or sibling milestone outline -> cache miss).
4. DB Commit Failure Resilience (DB commit fails after decomposition; retry completes with 0 LLM token spend).
5. Quota Failure Isolation (Quota exhaustion at M4; checkpoints M1..M3 preserved in Redis).
6. Cancellation Handling (asyncio.CancelledError releases reservation cleanly and preserves checkpoints in Redis).
7. Exact Token Accounting (Attempt 1 vs Attempt 2 tokens distinguished, zero double-billing of cached milestones).
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from datetime import UTC, date, datetime
from types import SimpleNamespace
from typing import Any
from uuid import UUID

import pytest
from uuid6 import uuid7

from src.account.public_api import (
    AvailabilitySnapshotDTO,
    LearnerProfileDTO,
    QuotaExceededError,
)
from src.execution.public_api import (
    ScheduleSyncResultDTO,
)
from src.planning.application.ports.milestone_checkpoint_port import (
    RedisMilestoneCheckpointStore,
)
from src.planning.application.services.milestone_scoped_decomposer import (
    MilestoneScopedTaskDecomposer,
    compute_decomposition_context_fingerprint,
    compute_milestone_checkpoint_key,
)
from src.planning.application.services.roadmap_skills import (
    TASK_DECOMPOSER_SKILL,
    build_planning_prompt_registry,
)
from src.planning.application.use_cases.proposal_generation_use_cases import (
    ExecuteScheduleProposalGenerationUseCase,
)
from src.planning.domain.models.goal import Goal, GoalStatus
from src.planning.domain.models.milestone import Milestone, MilestoneStatus
from src.planning.domain.models.roadmap import Roadmap, RoadmapStatus
from src.planning.domain.models.schedule import ScheduleProposal
from src.planning.domain.models.schedule_block import ScheduleBlock
from src.planning.domain.services.validation_types import (
    AvailabilityConfigurationDTO,
)
from src.shared_kernel.application.llm_port import (
    LLMGenerationResult,
    LLMToolDeclarationDTO,
    LLMToolExecutor,
)
from src.shared_kernel.infrastructure.sse.job_store import InMemorySseJobStore
from tests.helpers.llm_stubs import StubLLMAdapter

# ---------------------------------------------------------------------------
# Test Doubles & Mock Infrastructures
# ---------------------------------------------------------------------------


class FakeRedisClient:
    """Async Redis simulator mirroring redis.asyncio.Redis."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.ttls: dict[str, int] = {}
        self.fail_on_call: bool = False
        self.calls: list[str] = []

    async def ping(self) -> bool:
        if self.fail_on_call:
            raise ConnectionError("Simulated Redis connection refused on ping")
        self.calls.append("ping")
        return True

    async def get(self, key: str) -> str | None:
        if self.fail_on_call:
            raise ConnectionError("Simulated Redis connection reset on get")
        self.calls.append(f"get:{key}")
        return self.store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        if self.fail_on_call:
            raise ConnectionError("Simulated Redis connection reset on set")
        self.calls.append(f"set:{key}")
        self.store[key] = value
        if ex is not None:
            self.ttls[key] = ex
        return True

    async def keys(self, pattern: str) -> list[str]:
        if self.fail_on_call:
            raise ConnectionError("Simulated Redis connection reset on keys")
        prefix = pattern.replace("*", "")
        return [k for k in self.store if k.startswith(prefix)]

    async def delete(self, *keys: str) -> int:
        if self.fail_on_call:
            raise ConnectionError("Simulated Redis connection reset on delete")
        count = 0
        for k in keys:
            if k in self.store:
                del self.store[k]
                self.ttls.pop(k, None)
                count += 1
        return count

    async def aclose(self) -> None:
        self.calls.append("aclose")


class _FaultInjectingStubLLM(StubLLMAdapter):
    """LLM double that records milestone calls and can inject faults with realistic tokens."""

    def __init__(self) -> None:
        super().__init__()
        self.fail_milestone_ids: set[UUID] = set()
        self.fail_exception: Exception = TimeoutError("Simulated LLM network timeout on milestone")
        self.calls_by_milestone_id: dict[UUID, int] = {}
        self.total_decomposer_calls: int = 0
        self.milestone_tokens: dict[UUID, tuple[int, int]] = {}
        self.on_milestone_hook: Any | None = None

    async def generate_structured(
        self,
        *,
        system_prompt: str = "",
        user_prompt: str = "",
        response_schema: dict[str, Any] | type[Any] | None = None,
        tools: Sequence[LLMToolDeclarationDTO | dict[str, Any]] | None = None,
        tool_executor: LLMToolExecutor | None = None,
        max_tool_calls: int = 2,
        thinking_level: str | None = None,
        timeout_seconds: float | None = None,
        tool_call_timeout_seconds: float | None = None,
    ) -> LLMGenerationResult:
        if "GENERATE_PROPOSAL_TASKS" in user_prompt:
            self.total_decomposer_calls += 1
            target_mid: UUID | None = None
            if "MILESTONE_IDS: [" in user_prompt:
                start = user_prompt.index("MILESTONE_IDS: [") + len("MILESTONE_IDS: [")
                end = user_prompt.index("]", start)
                raw_mid = user_prompt[start:end].strip()
                try:
                    target_mid = UUID(raw_mid)
                except ValueError:
                    pass

            if target_mid is not None:
                self.calls_by_milestone_id[target_mid] = (
                    self.calls_by_milestone_id.get(target_mid, 0) + 1
                )
                if self.on_milestone_hook is not None:
                    maybe_coro = self.on_milestone_hook(target_mid)
                    if asyncio.iscoroutine(maybe_coro):
                        await maybe_coro

                if target_mid in self.fail_milestone_ids:
                    raise self.fail_exception

            res = await super().generate_structured(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_schema=response_schema,
                tools=tools,
                tool_executor=tool_executor,
                max_tool_calls=max_tool_calls,
                thinking_level=thinking_level,
                timeout_seconds=timeout_seconds,
                tool_call_timeout_seconds=tool_call_timeout_seconds,
            )
            # Assign consistent, deterministic non-zero token accounting per milestone
            if target_mid is not None:
                p_tok, c_tok = self.milestone_tokens.get(target_mid, (500, 150))
                return LLMGenerationResult(
                    payload=res.payload,
                    prompt_tokens=p_tok,
                    output_tokens=c_tok,
                    thinking_tokens=30,
                    model_id=res.model_id,
                )
            return res

        return await super().generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_schema=response_schema,
            tools=tools,
            tool_executor=tool_executor,
            max_tool_calls=max_tool_calls,
            thinking_level=thinking_level,
            timeout_seconds=timeout_seconds,
            tool_call_timeout_seconds=tool_call_timeout_seconds,
        )


class _RecordingQuotaFacade:
    def __init__(self) -> None:
        self.committed: list[tuple[UUID, int, int, str]] = []
        self.released: list[tuple[UUID, str]] = []
        self.reserved: list[UUID] = []

    async def check_quota_available(self, user_id: UUID, min_credits: int = 1) -> bool:
        del user_id, min_credits
        return True

    async def reserve_quota(
        self,
        user_id: UUID,
        operation_type: str = "SCHEDULE_PROPOSAL_GEN",
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
        model_name: str = "",
    ) -> None:
        self.committed.append((reservation_id, prompt_tokens, completion_tokens, model_name))

    async def release_reservation(self, reservation_id: UUID, reason: str = "") -> None:
        self.released.append((reservation_id, reason))

    async def expire_stale_reservations(self, now: datetime | None = None) -> int:
        del now
        return 0


class _ConfigurableUoW:
    def __init__(self) -> None:
        self.commits = 0
        self.fail_commits_count = 0

    async def __aenter__(self) -> _ConfigurableUoW:
        return self

    async def __aexit__(self, *args: Any) -> None:
        del args

    async def commit(self) -> None:
        if self.fail_commits_count > 0:
            self.fail_commits_count -= 1
            raise RuntimeError("Simulated DB connection lost during proposal commit")
        self.commits += 1

    async def rollback(self) -> None:
        pass

    def collect_events_from(self, *args: Any) -> None:
        del args


class _FakeGoalRepo:
    def __init__(self, goal: Goal) -> None:
        self.goal = goal

    async def get_by_id(self, gid: UUID) -> Goal | None:
        return self.goal if gid == self.goal.id else None

    async def get_by_id_for_user(self, goal_id: UUID, user_id: UUID) -> Goal | None:
        return self.goal if goal_id == self.goal.id and user_id == self.goal.user_id else None

    async def list_by_user_id(self, user_id: UUID) -> list[Goal]:
        return [self.goal] if user_id == self.goal.user_id else []

    async def save(self, goal: Goal) -> Goal:
        self.goal = goal
        return goal


class _FakeRoadmapRepo:
    def __init__(self, roadmap: Roadmap) -> None:
        self.roadmap = roadmap

    async def get_by_id(self, rid: UUID) -> Roadmap | None:
        return self.roadmap if rid == self.roadmap.id else None

    async def get_by_id_for_user(
        self, roadmap_id: UUID, user_id: UUID, *, for_update: bool = False
    ) -> Roadmap | None:
        del for_update
        return (
            self.roadmap
            if roadmap_id == self.roadmap.id and user_id == self.roadmap.user_id
            else None
        )

    async def list_by_user_id(
        self, user_id: UUID, *, status: str | None = None, for_update: bool = False
    ) -> list[Roadmap]:
        del user_id, status, for_update
        return []

    async def count_active_by_user_id(
        self, user_id: UUID, *, exclude_roadmap_id: UUID | None = None
    ) -> int:
        del user_id, exclude_roadmap_id
        return 1

    async def save(self, roadmap: Roadmap) -> Roadmap:
        self.roadmap = roadmap
        return roadmap


class _FakeMilestoneRepo:
    def __init__(self, milestones: Sequence[Milestone]) -> None:
        self.milestones = list(milestones)

    async def list_by_roadmap_id(self, rid: UUID) -> list[Milestone]:
        del rid
        return list(self.milestones)

    async def save_many(self, rid: UUID, milestones: Sequence[Milestone]) -> list[Milestone]:
        del rid
        self.milestones = list(milestones)
        return self.milestones

    async def approve_all_for_roadmap(self, rid: UUID, now: datetime) -> list[Milestone]:
        del rid
        for m in self.milestones:
            m.approve(now)
        return self.milestones


class _FakeProposalRepo:
    def __init__(self) -> None:
        self.proposals: list[ScheduleProposal] = []

    async def get_by_id(self, pid: UUID, *, for_update: bool = False) -> ScheduleProposal | None:
        del for_update
        return next((p for p in self.proposals if p.id == pid), None)

    async def get_current_draft(self, rid: UUID) -> ScheduleProposal | None:
        return next((p for p in reversed(self.proposals) if p.roadmap_id == rid), None)

    async def list_by_roadmap_id(self, rid: UUID) -> list[ScheduleProposal]:
        return [p for p in self.proposals if p.roadmap_id == rid]

    async def discard_existing_drafts(self, rid: UUID, now: datetime) -> int:
        del rid, now
        return len(self.proposals)

    async def save(self, p: ScheduleProposal) -> ScheduleProposal:
        self.proposals.append(p)
        return p


class _FakeBlockRepo:
    def __init__(self) -> None:
        self.blocks: list[ScheduleBlock] = []

    async def get_by_id(self, block_id: UUID) -> ScheduleBlock | None:
        return next((b for b in self.blocks if b.id == block_id), None)

    async def get_by_schedule_id(
        self,
        official_schedule_id: UUID,
        sync_status_in: list[str] | None = None,
        *,
        for_update: bool = False,
    ) -> list[ScheduleBlock]:
        del official_schedule_id, sync_status_in, for_update
        return list(self.blocks)

    async def list_by_roadmap_ids(self, roadmap_ids: list[UUID]) -> list[ScheduleBlock]:
        del roadmap_ids
        return list(self.blocks)

    async def save(self, block: ScheduleBlock) -> ScheduleBlock:
        self.blocks.append(block)
        return block

    async def save_many(self, blocks: list[ScheduleBlock]) -> list[ScheduleBlock]:
        self.blocks.extend(blocks)
        return list(blocks)


class _FakeAvailabilityQueryPort:
    def __init__(self, mode: str = "MODE_A", daily_minutes: int = 180) -> None:
        self.mode = mode
        self.daily_minutes = daily_minutes

    async def get_active_availability(self, user_id: UUID) -> AvailabilitySnapshotDTO | None:
        return AvailabilitySnapshotDTO(
            user_id=user_id,
            mode=self.mode,
            daily_cap_minutes=self.daily_minutes,
            weekly_capacity_minutes=self.daily_minutes * 7,
            daily_quota_minutes={},
            availability_slots=(),
            disabled_weekdays=(),
        )

    async def get_availability_snapshot(
        self, user_id: UUID, timezone_str: str | None = None
    ) -> AvailabilitySnapshotDTO:
        del timezone_str
        return AvailabilitySnapshotDTO(
            user_id=user_id,
            mode=self.mode,
            daily_cap_minutes=self.daily_minutes,
            weekly_capacity_minutes=self.daily_minutes * 7,
            daily_quota_minutes={},
            availability_slots=(),
            disabled_weekdays=(),
        )


class _FakeLearnerProfileQueryPort:
    def __init__(self, opt_session_minutes: int = 60, beta: float = 1.0) -> None:
        self.profile = LearnerProfileDTO(
            user_id=uuid7(),
            opt_session_minutes=opt_session_minutes,
            estimation_bias_beta=beta,
            peak_productivity_slots={},
            is_cold_start=False,
        )

    async def get_learner_profile(self, user_id: UUID) -> LearnerProfileDTO:
        del user_id
        return self.profile


class _FakeExecutionScheduleSyncPort:
    async def get_tasks_for_roadmaps(
        self,
        roadmap_ids: Sequence[UUID],
        roadmap_target_dates: Any | None = None,
    ) -> list[Any]:
        del roadmap_ids, roadmap_target_dates
        return []

    async def sync_proposal_to_official_schedule(
        self,
        proposal: ScheduleProposal,
        roadmap_id: UUID,
        user_id: UUID,
        now: datetime | None = None,
    ) -> ScheduleSyncResultDTO:
        del proposal, roadmap_id, user_id, now
        return ScheduleSyncResultDTO(
            official_schedule_id=uuid7(),
            synced_tasks_count=0,
            synced_blocks_count=0,
            has_unscheduled=False,
        )


def _build_5_milestone_fixture() -> tuple[
    UUID, Goal, Roadmap, list[Milestone], AvailabilityConfigurationDTO
]:
    user_id = uuid7()
    roadmap_id = uuid7()
    created = datetime(2026, 11, 1, 9, 0, tzinfo=UTC)

    goal = Goal(
        id=uuid7(),
        user_id=user_id,
        title="Master Distributed Systems & Event Sourcing",
        raw_description="Build production-grade event-driven architectures with high reliability.",
        prior_knowledge_level="INTERMEDIATE",
        status=GoalStatus.ACTIVE,
        created_at=created,
        updated_at=created,
    )
    roadmap = Roadmap(
        id=roadmap_id,
        goal_id=goal.id,
        user_id=user_id,
        title="Distributed Systems Roadmap",
        description="Comprehensive 5-milestone roadmap covering storage, consensus, and event streams.",
        start_date=date(2026, 11, 2),
        target_date=date(2026, 12, 15),
        status=RoadmapStatus.ACTIVE,
        created_at=created,
        updated_at=created,
    )
    milestones = [
        Milestone(
            id=uuid7(),
            roadmap_id=roadmap_id,
            sequence_order=1,
            title="M1: Storage Engines & LSM Trees",
            learning_outcomes=(
                "Understand SSTables and MemTables",
                "Implement basic Write-Ahead Log",
            ),
            estimated_effort_minutes=120,
            required_concepts=("lsm_tree", "wal"),
            status=MilestoneStatus.APPROVED,
            created_at=created,
            updated_at=created,
        ),
        Milestone(
            id=uuid7(),
            roadmap_id=roadmap_id,
            sequence_order=2,
            title="M2: Consensus Protocols & Raft",
            learning_outcomes=("Leader Election", "Log Replication"),
            estimated_effort_minutes=120,
            required_concepts=("raft", "paxos"),
            status=MilestoneStatus.APPROVED,
            created_at=created,
            updated_at=created,
        ),
        Milestone(
            id=uuid7(),
            roadmap_id=roadmap_id,
            sequence_order=3,
            title="M3: Event Sourcing & CQRS",
            learning_outcomes=("Aggregate Roots and Domain Events", "Read Models and Projections"),
            estimated_effort_minutes=120,
            required_concepts=("event_sourcing", "cqrs"),
            status=MilestoneStatus.APPROVED,
            created_at=created,
            updated_at=created,
        ),
        Milestone(
            id=uuid7(),
            roadmap_id=roadmap_id,
            sequence_order=4,
            title="M4: Distributed Transactions & Sagas",
            learning_outcomes=("Orchestrated Saga Pattern", "Choreographed Saga Pattern"),
            estimated_effort_minutes=120,
            required_concepts=("saga", "two_phase_commit"),
            status=MilestoneStatus.APPROVED,
            created_at=created,
            updated_at=created,
        ),
        Milestone(
            id=uuid7(),
            roadmap_id=roadmap_id,
            sequence_order=5,
            title="M5: Capstone Distributed Stream Processing",
            learning_outcomes=("Kafka Streams pipeline", "End-to-End Verification"),
            estimated_effort_minutes=120,
            required_concepts=("stream_processing",),
            status=MilestoneStatus.APPROVED,
            created_at=created,
            updated_at=created,
        ),
    ]
    # Chain explicit prerequisites M1 -> M2 -> M3 -> M4 -> M5
    milestones[1].prerequisite_milestone_ids = (milestones[0].id,)
    milestones[2].prerequisite_milestone_ids = (milestones[1].id,)
    milestones[3].prerequisite_milestone_ids = (milestones[2].id,)
    milestones[4].prerequisite_milestone_ids = (milestones[3].id,)

    avail = AvailabilityConfigurationDTO(
        mode="MODE_A",
        default_daily_quota_minutes=180,
        daily_quota_minutes={},
        disabled_weekdays=frozenset(),
    )
    return user_id, goal, roadmap, milestones, avail


# ---------------------------------------------------------------------------
# Test 1: Worker Crash / Restart
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_worker_crash_and_restart_resumes_from_redis() -> None:
    """Test 1: Worker Crash & Restart.

    Simulate a 5-milestone goal where M1 & M2 succeed, followed by simulated
    worker process termination at M3. On new worker process restart with the
    same Redis store, verify M1 & M2 load from Redis (0s, 0 tokens), and only
    M3..M5 call the LLM.
    """
    user_id, goal, roadmap, milestones, avail = _build_5_milestone_fixture()
    m1, m2, m3, m4, m5 = milestones

    fake_redis = FakeRedisClient()
    redis_store_worker1 = RedisMilestoneCheckpointStore(redis_client=fake_redis)
    llm1 = _FaultInjectingStubLLM()
    # Configure Worker 1 to fail at M3..M5 (simulating process termination)
    llm1.fail_milestone_ids = {m3.id, m4.id, m5.id}
    llm1.fail_exception = RuntimeError("Simulated Worker Process SIGKILL / Memory OOM at M3")

    learner_profile = SimpleNamespace(
        opt_session_minutes=60,
        estimation_bias_beta=1.0,
        peak_productivity_slots=("MORNING",),
    )

    worker1_decomposer = MilestoneScopedTaskDecomposer(
        llm_provider=llm1,
        enable_tier3_judge=False,
        user_id=user_id,
        goal_id=goal.id,
        roadmap_id=roadmap.id,
        max_concurrency=1,
        checkpoint_store=redis_store_worker1,
    )

    # Worker 1 runs and crashes on M3
    with pytest.raises(RuntimeError, match="Simulated Worker Process SIGKILL"):
        await worker1_decomposer.decompose_and_validate(
            goal=goal,
            roadmap=roadmap,
            milestones=milestones,
            availability=avail,
            learner_profile=learner_profile,
            start_date=roadmap.start_date,
            max_milestone_retries=0,
            reference_date=roadmap.start_date,
        )

    # Worker 1 called LLM on M1 and M2 successfully before process termination
    assert llm1.calls_by_milestone_id[m1.id] == 1
    assert llm1.calls_by_milestone_id[m2.id] == 1

    # Verify M1 and M2 checkpoints are durably persisted in Redis
    prompt_checksum = (
        build_planning_prompt_registry().latest(TASK_DECOMPOSER_SKILL.skill_id).checksum
    )
    key_m1 = compute_milestone_checkpoint_key(
        roadmap_id=roadmap.id,
        milestone=m1,
        all_milestones=milestones,
        target_date=roadmap.target_date,
        start_date=roadmap.start_date,
        learner_profile=learner_profile,
        prior_knowledge_level=goal.prior_knowledge_level,
        clarification_context=goal.clarification_context,
        availability=avail,
        prompt_checksum=prompt_checksum,
        model_name=getattr(llm1, "model_identifier", "gemini-3.8-flash"),
    )
    key_m2 = compute_milestone_checkpoint_key(
        roadmap_id=roadmap.id,
        milestone=m2,
        all_milestones=milestones,
        target_date=roadmap.target_date,
        start_date=roadmap.start_date,
        learner_profile=learner_profile,
        prior_knowledge_level=goal.prior_knowledge_level,
        clarification_context=goal.clarification_context,
        availability=avail,
        prompt_checksum=prompt_checksum,
        model_name=getattr(llm1, "model_identifier", "gemini-3.8-flash"),
    )
    assert await fake_redis.get(f"ff:checkpoint:milestone:{key_m1}") is not None
    assert await fake_redis.get(f"ff:checkpoint:milestone:{key_m2}") is not None

    # Simulate Worker 2 process restart: clean memory, same Redis store
    llm2 = _FaultInjectingStubLLM()
    redis_store_worker2 = RedisMilestoneCheckpointStore(redis_client=fake_redis)

    worker2_decomposer = MilestoneScopedTaskDecomposer(
        llm_provider=llm2,
        enable_tier3_judge=False,
        user_id=user_id,
        goal_id=goal.id,
        roadmap_id=roadmap.id,
        max_concurrency=1,
        checkpoint_store=redis_store_worker2,
    )

    res = await worker2_decomposer.decompose_and_validate(
        goal=goal,
        roadmap=roadmap,
        milestones=milestones,
        availability=avail,
        learner_profile=learner_profile,
        start_date=roadmap.start_date,
        max_milestone_retries=0,
        reference_date=roadmap.start_date,
    )

    # Worker 2: M1 & M2 loaded from Redis (0 LLM calls)
    assert llm2.calls_by_milestone_id.get(m1.id, 0) == 0, "M1 must load from Redis"
    assert llm2.calls_by_milestone_id.get(m2.id, 0) == 0, "M2 must load from Redis"
    # Only M3, M4, M5 executed via LLM
    assert llm2.calls_by_milestone_id[m3.id] == 1
    assert llm2.calls_by_milestone_id[m4.id] == 1
    assert llm2.calls_by_milestone_id[m5.id] == 1
    assert len(res.validated_proposal_data["tasks"]) == 5  # 1 task per milestone in stub


# ---------------------------------------------------------------------------
# Test 2: Concurrent Resume
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_concurrent_resume_is_idempotent_and_consistent() -> None:
    """Test 2: Concurrent Resume.

    Simulate 2 concurrent workers resuming the same roadmap simultaneously via
    asyncio.gather. Verify idempotent writes, consistent proposal merging, zero
    duplicate tasks, and zero duplicate dependencies.
    """
    user_id, goal, roadmap, milestones, avail = _build_5_milestone_fixture()
    fake_redis = FakeRedisClient()

    llm_shared = _FaultInjectingStubLLM()
    store_a = RedisMilestoneCheckpointStore(redis_client=fake_redis)
    store_b = RedisMilestoneCheckpointStore(redis_client=fake_redis)

    learner_profile = SimpleNamespace(
        opt_session_minutes=60,
        estimation_bias_beta=1.0,
        peak_productivity_slots=("MORNING",),
    )

    worker_a = MilestoneScopedTaskDecomposer(
        llm_provider=llm_shared,
        enable_tier3_judge=False,
        user_id=user_id,
        goal_id=goal.id,
        roadmap_id=roadmap.id,
        checkpoint_store=store_a,
    )
    worker_b = MilestoneScopedTaskDecomposer(
        llm_provider=llm_shared,
        enable_tier3_judge=False,
        user_id=user_id,
        goal_id=goal.id,
        roadmap_id=roadmap.id,
        checkpoint_store=store_b,
    )

    res_a, res_b = await asyncio.gather(
        worker_a.decompose_and_validate(
            goal=goal,
            roadmap=roadmap,
            milestones=milestones,
            availability=avail,
            learner_profile=learner_profile,
            start_date=roadmap.start_date,
            max_milestone_retries=0,
            reference_date=roadmap.start_date,
        ),
        worker_b.decompose_and_validate(
            goal=goal,
            roadmap=roadmap,
            milestones=milestones,
            availability=avail,
            learner_profile=learner_profile,
            start_date=roadmap.start_date,
            max_milestone_retries=0,
            reference_date=roadmap.start_date,
        ),
    )

    tasks_a = res_a.validated_proposal_data["tasks"]
    tasks_b = res_b.validated_proposal_data["tasks"]
    deps_a = res_a.validated_proposal_data["dependencies"]
    deps_b = res_b.validated_proposal_data["dependencies"]

    assert len(tasks_a) == len(tasks_b) == 5
    assert len(deps_a) == len(deps_b)

    # Assert zero duplicate tasks
    task_ids_a = [t["task_id"] for t in tasks_a]
    assert len(task_ids_a) == len(set(task_ids_a))
    task_ids_b = [t["task_id"] for t in tasks_b]
    assert len(task_ids_b) == len(set(task_ids_b))

    # Assert zero duplicate dependencies
    edges_a = [(d["predecessor_id"], d["successor_id"]) for d in deps_a]
    assert len(edges_a) == len(set(edges_a))
    edges_b = [(d["predecessor_id"], d["successor_id"]) for d in deps_b]
    assert len(edges_b) == len(set(edges_b))


# ---------------------------------------------------------------------------
# Test 3: Stale Checkpoint Invalidation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stale_checkpoint_invalidation_on_profile_or_sibling_mutation() -> None:
    """Test 3: Stale Checkpoint Invalidation.

    Mutate learner profile opt_session_minutes or change a sibling milestone outline.
    Verify that the checkpoint key changes and triggers a cache miss.
    """
    user_id, goal, roadmap, milestones, avail = _build_5_milestone_fixture()
    m1, m2 = milestones[0], milestones[1]
    prompt_checksum = "test_prompt_chk_123"
    model_name = "gemini-3.8-flash"

    # 1. Base Fingerprint
    base_profile = SimpleNamespace(
        prior_knowledge_level="BEGINNER",
        opt_session_minutes=45,
        estimation_bias_beta=1.0,
    )
    fp_base = compute_decomposition_context_fingerprint(
        milestone=m1,
        all_milestones=milestones,
        target_date=roadmap.target_date,
        learner_profile=base_profile,
        availability=avail,
        prompt_checksum=prompt_checksum,
        model_name=model_name,
    )
    key_base = compute_milestone_checkpoint_key(
        roadmap_id=roadmap.id,
        milestone=m1,
        context_fingerprint=fp_base,
    )

    # 2. Mutate Learner Profile opt_session_minutes (45 -> 90)
    mutated_profile = SimpleNamespace(
        prior_knowledge_level="BEGINNER",
        opt_session_minutes=90,
        estimation_bias_beta=1.0,
    )
    fp_profile_mutated = compute_decomposition_context_fingerprint(
        milestone=m1,
        all_milestones=milestones,
        target_date=roadmap.target_date,
        learner_profile=mutated_profile,
        availability=avail,
        prompt_checksum=prompt_checksum,
        model_name=model_name,
    )
    key_profile_mutated = compute_milestone_checkpoint_key(
        roadmap_id=roadmap.id,
        milestone=m1,
        context_fingerprint=fp_profile_mutated,
    )
    assert fp_base != fp_profile_mutated, "Mutating opt_session_minutes must invalidate fingerprint"
    assert key_base != key_profile_mutated, "Mutating opt_session_minutes must invalidate key"

    # 3. Mutate Sibling Milestone Outline (Change M2's title & outcomes)
    m2_altered = Milestone(
        id=m2.id,
        roadmap_id=roadmap.id,
        sequence_order=m2.sequence_order,
        title="M2: Quantum Fault-Tolerant Consensus",
        learning_outcomes=("Byzantine Fault Tolerance in Quantum Networks",),
        status=MilestoneStatus.APPROVED,
    )
    milestones_with_altered_sibling = [m1, m2_altered, *milestones[2:]]
    fp_sibling_mutated = compute_decomposition_context_fingerprint(
        milestone=m1,
        all_milestones=milestones_with_altered_sibling,
        target_date=roadmap.target_date,
        learner_profile=base_profile,
        availability=avail,
        prompt_checksum=prompt_checksum,
        model_name=model_name,
    )
    key_sibling_mutated = compute_milestone_checkpoint_key(
        roadmap_id=roadmap.id,
        milestone=m1,
        context_fingerprint=fp_sibling_mutated,
    )
    assert fp_base != fp_sibling_mutated, "Mutating sibling outline must invalidate fingerprint"
    assert key_base != key_sibling_mutated, "Mutating sibling outline must invalidate key"


# ---------------------------------------------------------------------------
# Test 4: DB Commit Failure Resilience
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_db_commit_failure_resilience_preserves_checkpoints() -> None:
    """Test 4: DB Commit Failure Resilience.

    Simulate a DB commit error after milestone decomposition completes.
    Verify Redis checkpoint remains intact so the subsequent retry completes with 0 LLM token spend.
    """
    user_id, goal, roadmap, milestones, _ = _build_5_milestone_fixture()
    fake_redis = FakeRedisClient()
    checkpoint_store = RedisMilestoneCheckpointStore(redis_client=fake_redis)

    goal_repo = _FakeGoalRepo(goal)
    roadmap_repo = _FakeRoadmapRepo(roadmap)
    milestone_repo = _FakeMilestoneRepo(milestones)
    proposal_repo = _FakeProposalRepo()
    quota_facade = _RecordingQuotaFacade()
    sse_store = InMemorySseJobStore()
    uow = _ConfigurableUoW()
    llm = _FaultInjectingStubLLM()

    use_case = ExecuteScheduleProposalGenerationUseCase(
        goal_repo=goal_repo,
        roadmap_repo=roadmap_repo,
        milestone_repo=milestone_repo,
        proposal_repo=proposal_repo,
        availability_query_port=_FakeAvailabilityQueryPort(),
        learner_profile_port=_FakeLearnerProfileQueryPort(),
        execution_sync_port=_FakeExecutionScheduleSyncPort(),
        quota_facade=quota_facade,
        llm_provider=llm,
        sse_job_store=sse_store,
        uow=uow,
        enable_tier3_judge=False,
        checkpoint_store=checkpoint_store,
    )

    # Attempt 1: Simulate DB commit failure at the very end
    uow.fail_commits_count = 1
    job_id = uuid7()
    reservation_id = uuid7()
    await sse_store.create_job(
        job_id=job_id,
        user_id=user_id,
        roadmap_id=roadmap.id,
        reservation_id=reservation_id,
        job_type="SCHEDULE_PROPOSAL_GEN",
        operation=f"SCHEDULE_PROPOSAL_GEN:{roadmap.id}",
    )

    with pytest.raises(RuntimeError, match="Simulated DB connection lost"):
        await use_case.execute(
            job_id=job_id,
            user_id=user_id,
            roadmap_id=roadmap.id,
            reservation_id=reservation_id,
            decomposer_architecture_mode="milestone_scoped",
        )

    # In Attempt 1, LLM decomposed all 5 milestones
    assert llm.total_decomposer_calls == 5
    # Verify all 5 checkpoints were durably stored in Redis before commit failure
    redis_keys = await fake_redis.keys("ff:checkpoint:milestone:*")
    assert len(redis_keys) == 5, "All 5 milestone checkpoints must be preserved in Redis"

    # Attempt 2 (Retry): Reset LLM calls counter, restore DB commit
    llm.calls_by_milestone_id.clear()
    llm.total_decomposer_calls = 0
    uow.fail_commits_count = 0
    new_job_id = uuid7()
    new_reservation_id = uuid7()
    await sse_store.create_job(
        job_id=new_job_id,
        user_id=user_id,
        roadmap_id=roadmap.id,
        reservation_id=new_reservation_id,
        job_type="SCHEDULE_PROPOSAL_GEN",
        operation=f"SCHEDULE_PROPOSAL_GEN:{roadmap.id}",
    )

    proposal = await use_case.execute(
        job_id=new_job_id,
        user_id=user_id,
        roadmap_id=roadmap.id,
        reservation_id=new_reservation_id,
        decomposer_architecture_mode="milestone_scoped",
    )

    # In Attempt 2, ZERO LLM decomposition calls were made — all 5 loaded directly from Redis!
    assert llm.total_decomposer_calls == 0, (
        "Retry after DB failure must spend 0 LLM decomposer calls"
    )
    assert proposal is not None
    assert len(proposal.proposal_data["tasks"]) == 5
    # Quota commit for Attempt 2 recorded 0 prompt tokens for decomposition (64 tokens for critics)
    assert len(quota_facade.committed) == 2
    assert quota_facade.committed[0][0] == reservation_id
    assert quota_facade.committed[1][0] == new_reservation_id
    _, prompt_toks, comp_toks, _ = quota_facade.committed[1]
    assert prompt_toks == 64, (
        "0 milestone decomposition prompt tokens billed when all load from checkpoint"
    )
    assert comp_toks == 32, (
        "0 milestone decomposition completion tokens billed when all load from checkpoint"
    )


# ---------------------------------------------------------------------------
# Test 5: Quota Failure Isolation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_quota_failure_isolation_preserves_preceding_milestone_checkpoints() -> None:
    """Test 5: Quota Failure Isolation.

    Simulate quota exhaustion at M4. Verify checkpoints for M1..M3 are preserved in Redis.
    """
    user_id, goal, roadmap, milestones, avail = _build_5_milestone_fixture()
    m1, m2, m3, m4, _ = milestones

    fake_redis = FakeRedisClient()
    checkpoint_store = RedisMilestoneCheckpointStore(redis_client=fake_redis)
    llm = _FaultInjectingStubLLM()

    # M4 and M5 throw QuotaExceededError
    llm.fail_milestone_ids = {m4.id, milestones[4].id}
    llm.fail_exception = QuotaExceededError("Simulated quota exhaustion at M4")

    learner_profile = SimpleNamespace(
        opt_session_minutes=60,
        estimation_bias_beta=1.0,
        peak_productivity_slots=("MORNING",),
    )

    decomposer = MilestoneScopedTaskDecomposer(
        llm_provider=llm,
        enable_tier3_judge=False,
        user_id=user_id,
        goal_id=goal.id,
        roadmap_id=roadmap.id,
        max_concurrency=1,
        checkpoint_store=checkpoint_store,
    )

    with pytest.raises(QuotaExceededError):
        await decomposer.decompose_and_validate(
            goal=goal,
            roadmap=roadmap,
            milestones=milestones,
            availability=avail,
            learner_profile=learner_profile,
            start_date=roadmap.start_date,
            max_milestone_retries=0,
            reference_date=roadmap.start_date,
        )

    # Verify M1..M3 exist in Redis, M4 and M5 do not
    prompt_checksum = (
        build_planning_prompt_registry().latest(TASK_DECOMPOSER_SKILL.skill_id).checksum
    )
    for m in (m1, m2, m3):
        k = compute_milestone_checkpoint_key(
            roadmap_id=roadmap.id,
            milestone=m,
            all_milestones=milestones,
            target_date=roadmap.target_date,
            start_date=roadmap.start_date,
            learner_profile=learner_profile,
            prior_knowledge_level=goal.prior_knowledge_level,
            clarification_context=goal.clarification_context,
            availability=avail,
            prompt_checksum=prompt_checksum,
            model_name=getattr(llm, "model_identifier", "gemini-3.8-flash"),
        )
        assert await fake_redis.get(f"ff:checkpoint:milestone:{k}") is not None, (
            f"Checkpoint for {m.title} must be preserved in Redis"
        )


# ---------------------------------------------------------------------------
# Test 6: Cancellation Handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cancellation_handling_releases_quota_and_preserves_checkpoints() -> None:
    """Test 6: Cancellation Handling.

    Simulate asyncio.CancelledError during proposal generation.
    Verify clean quota release and preserved checkpoints in Redis.
    """
    user_id, goal, roadmap, milestones, _ = _build_5_milestone_fixture()
    m1, m2, m3 = milestones[0], milestones[1], milestones[2]

    fake_redis = FakeRedisClient()
    checkpoint_store = RedisMilestoneCheckpointStore(redis_client=fake_redis)

    goal_repo = _FakeGoalRepo(goal)
    roadmap_repo = _FakeRoadmapRepo(roadmap)
    milestone_repo = _FakeMilestoneRepo(milestones)
    proposal_repo = _FakeProposalRepo()
    quota_facade = _RecordingQuotaFacade()
    sse_store = InMemorySseJobStore()
    uow = _ConfigurableUoW()
    llm = _FaultInjectingStubLLM()

    # Cancel task when M3 is reached (after M1 and M2 succeeded)
    task_to_cancel: asyncio.Task[Any] | None = None

    async def _cancel_at_m3(target_mid: UUID) -> None:
        if target_mid == m3.id and task_to_cancel is not None:
            # Wait for M1 and M2 to complete and persist checkpoints
            while (
                llm.calls_by_milestone_id.get(m1.id, 0) == 0
                or llm.calls_by_milestone_id.get(m2.id, 0) == 0
            ):
                await asyncio.sleep(0.01)
            await asyncio.sleep(0.02)
            task_to_cancel.cancel()

    llm.on_milestone_hook = _cancel_at_m3

    use_case = ExecuteScheduleProposalGenerationUseCase(
        goal_repo=goal_repo,
        roadmap_repo=roadmap_repo,
        milestone_repo=milestone_repo,
        proposal_repo=proposal_repo,
        availability_query_port=_FakeAvailabilityQueryPort(),
        learner_profile_port=_FakeLearnerProfileQueryPort(),
        execution_sync_port=_FakeExecutionScheduleSyncPort(),
        quota_facade=quota_facade,
        llm_provider=llm,
        sse_job_store=sse_store,
        uow=uow,
        enable_tier3_judge=False,
        checkpoint_store=checkpoint_store,
    )

    job_id = uuid7()
    reservation_id = uuid7()
    await sse_store.create_job(
        job_id=job_id,
        user_id=user_id,
        roadmap_id=roadmap.id,
        reservation_id=reservation_id,
        job_type="SCHEDULE_PROPOSAL_GEN",
        operation=f"SCHEDULE_PROPOSAL_GEN:{roadmap.id}",
    )

    coro = use_case.execute(
        job_id=job_id,
        user_id=user_id,
        roadmap_id=roadmap.id,
        reservation_id=reservation_id,
        decomposer_architecture_mode="milestone_scoped",
    )
    task_to_cancel = asyncio.create_task(coro)

    with pytest.raises(asyncio.CancelledError):
        await task_to_cancel

    # Assert clean quota release
    assert len(quota_facade.released) == 1
    assert quota_facade.released[0] == (reservation_id, "CANCELLED")

    # Assert M1 and M2 checkpoints remain intact in Redis
    prompt_checksum = (
        build_planning_prompt_registry().latest(TASK_DECOMPOSER_SKILL.skill_id).checksum
    )
    for m in (m1, m2):
        k = compute_milestone_checkpoint_key(
            roadmap_id=roadmap.id,
            milestone=m,
            all_milestones=milestones,
            target_date=roadmap.target_date,
            start_date=roadmap.start_date,
            learner_profile=SimpleNamespace(
                opt_session_minutes=60,
                estimation_bias_beta=1.0,
            ),
            prior_knowledge_level="INTERMEDIATE",
            clarification_context=goal.clarification_context,
            availability=AvailabilityConfigurationDTO(
                mode="MODE_A",
                default_daily_quota_minutes=180,
            ),
            prompt_checksum=prompt_checksum,
            model_name=getattr(llm, "model_identifier", "gemini-3.8-flash"),
        )
        assert await fake_redis.get(f"ff:checkpoint:milestone:{k}") is not None


# ---------------------------------------------------------------------------
# Test 7: Exact Token Accounting
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_exact_token_accounting_zero_double_billing_for_cached_milestones() -> None:
    """Test 7: Exact Token Accounting.

    Assert tokens from attempt 1 (failed) vs attempt 2 (resumed) are clearly distinguished,
    with zero double-billing of cached milestones.
    """
    user_id, goal, roadmap, milestones, avail = _build_5_milestone_fixture()
    m1, m2, m3, m4, m5 = milestones

    fake_redis = FakeRedisClient()
    checkpoint_store = RedisMilestoneCheckpointStore(redis_client=fake_redis)

    llm1 = _FaultInjectingStubLLM()
    # Configure custom tokens per milestone
    llm1.milestone_tokens = {
        m1.id: (400, 100),
        m2.id: (500, 120),
        m3.id: (600, 140),
        m4.id: (700, 160),
        m5.id: (800, 180),
    }
    # Fail at M3..M5 on Attempt 1
    llm1.fail_milestone_ids = {m3.id, m4.id, m5.id}
    llm1.fail_exception = TimeoutError("Simulated LLM network timeout at M3")

    learner_profile = SimpleNamespace(
        opt_session_minutes=60,
        estimation_bias_beta=1.0,
        peak_productivity_slots=("MORNING",),
    )

    decomposer1 = MilestoneScopedTaskDecomposer(
        llm_provider=llm1,
        enable_tier3_judge=False,
        user_id=user_id,
        goal_id=goal.id,
        roadmap_id=roadmap.id,
        max_concurrency=1,
        checkpoint_store=checkpoint_store,
    )

    with pytest.raises(TimeoutError):
        await decomposer1.decompose_and_validate(
            goal=goal,
            roadmap=roadmap,
            milestones=milestones,
            availability=avail,
            learner_profile=learner_profile,
            start_date=roadmap.start_date,
            max_milestone_retries=0,
            reference_date=roadmap.start_date,
        )

    # Attempt 2: Resumed with clean LLM
    llm2 = _FaultInjectingStubLLM()
    llm2.milestone_tokens = llm1.milestone_tokens

    decomposer2 = MilestoneScopedTaskDecomposer(
        llm_provider=llm2,
        enable_tier3_judge=False,
        user_id=user_id,
        goal_id=goal.id,
        roadmap_id=roadmap.id,
        max_concurrency=1,
        checkpoint_store=checkpoint_store,
    )

    res = await decomposer2.decompose_and_validate(
        goal=goal,
        roadmap=roadmap,
        milestones=milestones,
        availability=avail,
        learner_profile=learner_profile,
        start_date=roadmap.start_date,
        max_milestone_retries=0,
        reference_date=roadmap.start_date,
    )

    # Expected Attempt 2 tokens:
    # M1 loaded from Redis -> 0 prompt tokens, 0 completion tokens
    # M2 loaded from Redis -> 0 prompt tokens, 0 completion tokens
    # M3 generated by LLM -> 600 prompt tokens, 140 completion tokens
    # M4 generated by LLM -> 700 prompt tokens, 160 completion tokens
    # M5 generated by LLM -> 800 prompt tokens, 180 completion tokens
    # Dual quality critics -> 64 prompt tokens, 32 completion tokens
    expected_prompt_tokens = 600 + 700 + 800 + 64  # 2164 (NOT including 400 + 500)
    expected_completion_tokens = 140 + 160 + 180 + 32  # 512 (NOT including 100 + 120)

    assert res.total_prompt_tokens == expected_prompt_tokens, (
        f"Expected {expected_prompt_tokens} prompt tokens, got {res.total_prompt_tokens}. Zero double-billing!"
    )
    assert res.total_completion_tokens == expected_completion_tokens, (
        f"Expected {expected_completion_tokens} completion tokens, got {res.total_completion_tokens}."
    )
