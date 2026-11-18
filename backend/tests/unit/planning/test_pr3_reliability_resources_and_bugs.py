"""PR-3 tests: CofHub Step 3 Reliability, Learning Resources Discovery, BUG-06 & BUG-08."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from datetime import UTC, date, datetime
from types import SimpleNamespace
from typing import Any
from uuid import UUID

import httpx
import pytest
from uuid6 import uuid7

from src.account.public_api import (
    AvailabilitySnapshotDTO,
    LearnerProfileDTO,
)
from src.execution.infrastructure.adapters.execution_dashboard_adapter import (
    ExecutionDashboardAdapter,
)
from src.execution.public_api import ScheduleSyncResultDTO
from src.planning.application.ports.milestone_checkpoint_port import (
    RedisMilestoneCheckpointStore,
)
from src.planning.application.services.learning_quality import (
    resolve_task_resources_from_tool_results,
)
from src.planning.application.services.learning_resource_discovery import (
    clear_url_health_cache,
    discover_curated_official_resources,
    knowledge_source_to_learning_resource,
    validate_official_resource_url,
    verify_official_url_live,
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
from src.planning.application.use_cases.proposal_management_use_cases import (
    ApplyScheduleProposalUseCase,
    SaveManualRoadmapPlanUseCase,
)
from src.planning.domain.models.goal import Goal, GoalStatus
from src.planning.domain.models.knowledge_source import (
    KnowledgeChunk,
    KnowledgeIngestionStatus,
    KnowledgeSource,
    KnowledgeSourceType,
)
from src.planning.domain.models.milestone import Milestone, MilestoneStatus
from src.planning.domain.models.roadmap import Roadmap, RoadmapStatus
from src.planning.domain.models.schedule import (
    OfficialSchedule,
    ScheduleProposal,
    ScheduleProposalStatus,
)
from src.planning.domain.models.schedule_block import ScheduleBlock
from src.planning.domain.services.validation_types import AvailabilityConfigurationDTO
from src.planning.infrastructure.repositories.sqlalchemy_knowledge_base_repository import (
    VERIFIED_SEED_CONCEPTS,
    VERIFIED_SEED_RESOURCES,
    InMemoryKnowledgeBaseRepository,
)
from src.shared_kernel.application.llm_port import LLMGenerationResult
from src.shared_kernel.config import Settings
from src.shared_kernel.infrastructure.external_ai.litellm_adapter import (
    LiteLLMAdapter,
    aclose_google_genai_clients,
    clear_google_genai_client_cache,
)
from src.shared_kernel.infrastructure.sse.job_store import InMemorySseJobStore
from tests.helpers.llm_stubs import StubLLMAdapter


class _FakeRedisClient:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.calls: list[str] = []
        self.closed_count = 0

    async def ping(self) -> bool:
        return True

    async def get(self, key: str) -> str | None:
        self.calls.append(f"get:{key}")
        return self.store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        del ex
        self.calls.append(f"set:{key}")
        self.store[key] = value
        return True

    async def keys(self, pattern: str) -> list[str]:
        prefix = pattern.replace("*", "")
        return [k for k in self.store if k.startswith(prefix)]

    async def delete(self, *keys: str) -> int:
        deleted = 0
        for k in keys:
            if k in self.store:
                del self.store[k]
                deleted += 1
        return deleted

    async def aclose(self) -> None:
        self.closed_count += 1
        self.calls.append("aclose")


class _FakeUoW:
    def __init__(self) -> None:
        self.commits = 0

    async def __aenter__(self) -> _FakeUoW:
        return self

    async def __aexit__(self, *args: Any) -> None:
        del args

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        pass

    def collect_events_from(self, *args: Any) -> None:
        del args


class _RecordingQuotaFacade:
    def __init__(self) -> None:
        self.reserved: list[UUID] = []
        self.committed: list[tuple[UUID, int, int, str]] = []
        self.released: list[tuple[UUID, str]] = []
        self.attempt_usage_rows: list[dict[str, Any]] = []

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

    async def record_attempt_usage(self, **kwargs: Any) -> None:
        self.attempt_usage_rows.append(kwargs)


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

    async def list_by_user_id(self, user_id: UUID, status: str | None = None) -> list[Roadmap]:
        if user_id != self.roadmap.user_id:
            return []
        if status is not None and self.roadmap.status.value != status:
            return []
        return [self.roadmap]

    async def count_active_by_user_id(
        self, user_id: UUID, exclude_roadmap_id: UUID | None = None
    ) -> int:
        del user_id, exclude_roadmap_id
        return 0

    async def save(self, roadmap: Roadmap) -> Roadmap:
        self.roadmap = roadmap
        return roadmap


class _FakeMilestoneRepo:
    def __init__(self, milestones: list[Milestone]) -> None:
        self.milestones = list(milestones)

    async def list_by_roadmap_id(self, roadmap_id: UUID) -> list[Milestone]:
        return [m for m in self.milestones if m.roadmap_id == roadmap_id]

    async def save_many(self, roadmap_id: UUID, milestones: Sequence[Milestone]) -> list[Milestone]:
        del roadmap_id
        self.milestones = list(milestones)
        return list(milestones)

    async def approve_all_for_roadmap(self, roadmap_id: UUID, now: datetime) -> list[Milestone]:
        updated = [
            Milestone(
                id=m.id,
                roadmap_id=m.roadmap_id,
                sequence_order=m.sequence_order,
                title=m.title,
                description=m.description,
                learning_outcomes=m.learning_outcomes,
                completion_criteria=m.completion_criteria,
                estimated_effort_minutes=m.estimated_effort_minutes,
                required_concepts=m.required_concepts,
                unverified_concepts=m.unverified_concepts,
                prerequisite_milestone_ids=m.prerequisite_milestone_ids,
                status=MilestoneStatus.APPROVED,
                created_at=m.created_at,
                updated_at=now,
            )
            for m in self.milestones
            if m.roadmap_id == roadmap_id
        ]
        self.milestones = updated
        return updated


class _FakeProposalRepo:
    def __init__(self) -> None:
        self.proposals: dict[UUID, ScheduleProposal] = {}

    async def save(self, proposal: ScheduleProposal) -> ScheduleProposal:
        self.proposals[proposal.id] = proposal
        return proposal

    async def get_by_id(self, pid: UUID) -> ScheduleProposal | None:
        return self.proposals.get(pid)

    async def get_by_id_for_user(self, pid: UUID, uid: UUID) -> ScheduleProposal | None:
        p = self.proposals.get(pid)
        return p if p and p.user_id == uid else None

    async def get_current_draft(self, roadmap_id: UUID) -> ScheduleProposal | None:
        drafts = [
            p
            for p in self.proposals.values()
            if p.roadmap_id == roadmap_id and p.status == ScheduleProposalStatus.DRAFT
        ]
        return drafts[-1] if drafts else None

    async def discard_existing_drafts(self, roadmap_id: UUID, now: datetime) -> int:
        del now
        count = 0
        for pid, p in list(self.proposals.items()):
            if p.roadmap_id == roadmap_id and p.status == ScheduleProposalStatus.DRAFT:
                p.status = ScheduleProposalStatus.DISCARDED
                self.proposals[pid] = p
                count += 1
        return count


class _FakeScheduleRepo:
    def __init__(self) -> None:
        self.schedules: dict[UUID, OfficialSchedule] = {}

    async def get_by_roadmap_id(self, roadmap_id: UUID) -> OfficialSchedule | None:
        for s in self.schedules.values():
            if s.roadmap_id == roadmap_id:
                return s
        return None

    async def save(self, schedule: OfficialSchedule) -> OfficialSchedule:
        self.schedules[schedule.id] = schedule
        return schedule


class _FakeBlockRepo:
    def __init__(self) -> None:
        self.blocks: list[ScheduleBlock] = []

    async def list_by_roadmap_ids(self, roadmap_ids: Sequence[UUID]) -> list[ScheduleBlock]:
        return [b for b in self.blocks if b.roadmap_id in set(roadmap_ids)]

    async def get_by_schedule_id(self, official_schedule_id: UUID) -> list[ScheduleBlock]:
        return [b for b in self.blocks if b.official_schedule_id == official_schedule_id]

    async def save_all(self, blocks: Sequence[ScheduleBlock]) -> list[ScheduleBlock]:
        self.blocks = list(blocks)
        return self.blocks

    async def replace_for_official_schedule(
        self,
        *,
        official_schedule_id: UUID,
        blocks: Sequence[ScheduleBlock],
        preserved_task_ids: set[UUID] = frozenset(),
    ) -> list[ScheduleBlock]:
        self.blocks = [
            b
            for b in self.blocks
            if not (
                b.official_schedule_id == official_schedule_id
                and b.task_id not in preserved_task_ids
            )
        ] + list(blocks)
        return list(blocks)


class _FakeAvailabilityPort:
    def __init__(self, snapshot: AvailabilitySnapshotDTO) -> None:
        self.snapshot = snapshot

    async def get_user_availability(self, user_id: UUID) -> AvailabilitySnapshotDTO:
        del user_id
        return self.snapshot

    async def get_active_availability(self, user_id: UUID) -> AvailabilitySnapshotDTO:
        del user_id
        return self.snapshot


class _FakeLearnerProfilePort:
    def __init__(self, user_id: UUID) -> None:
        self.profile = LearnerProfileDTO(
            user_id=user_id,
            opt_session_minutes=60,
            estimation_bias_beta=1.0,
            peak_productivity_slots={},
        )

    async def get_learner_profile(self, user_id: UUID) -> LearnerProfileDTO:
        del user_id
        return self.profile


class _FakeUserQueryPort:
    def __init__(self, user_id: UUID, timezone: str = "Asia/Ho_Chi_Minh") -> None:
        self.snap = SimpleNamespace(
            id=user_id,
            timezone=timezone,
            role="LEARNER",
            tier="FREE",
            is_locked=False,
        )

    async def get_user_by_id(self, user_id: UUID) -> Any:
        return self.snap if user_id == self.snap.id else None


class _FakeExecutionSyncPort:
    def __init__(self) -> None:
        self.synced_proposals: list[ScheduleProposal] = []
        self.synced_tasks: list[Any] = []

    async def get_tasks_for_roadmaps(
        self,
        roadmap_ids: Sequence[UUID],
        roadmap_target_dates: Any | None = None,
    ) -> list[Any]:
        del roadmap_ids, roadmap_target_dates
        return []

    async def sync_official_schedule_tasks(self, **kwargs: Any) -> ScheduleSyncResultDTO:
        tasks = kwargs["proposed_tasks"]
        self.synced_tasks = list(tasks)
        return ScheduleSyncResultDTO(
            roadmap_id=kwargs["roadmap_id"],
            official_schedule_id=kwargs["official_schedule_id"],
            preserved_completed_tasks_count=0,
            replaced_tasks_count=0,
            inserted_tasks_count=len(tasks),
            affected_tasks_count=len(tasks),
            total_shifted_minutes=0,
            total_active_sessions=len(tasks),
            total_planned_minutes=sum(t.estimated_minutes for t in tasks),
        )


class _FakeChangeLogPort:
    async def record_change_log(self, **kwargs: Any) -> None:
        del kwargs

    async def append_change_log(self, **kwargs: Any) -> None:
        del kwargs


class _FakeKnowledgeSourceRepo:
    def __init__(self, sources: list[KnowledgeSource]) -> None:
        self._sources = sources

    async def save_source(self, source: KnowledgeSource) -> KnowledgeSource:
        return source

    async def get_source_for_user(self, source_id: UUID, user_id: UUID) -> KnowledgeSource | None:
        for s in self._sources:
            if s.id == source_id and s.user_id == user_id:
                return s
        return None

    async def list_sources_for_goal(self, goal_id: UUID, user_id: UUID) -> list[KnowledgeSource]:
        return [s for s in self._sources if s.goal_id == goal_id and s.user_id == user_id]

    async def replace_chunks(self, source_id: UUID, chunks: list[KnowledgeChunk]) -> None:
        del source_id, chunks

    async def hybrid_search(
        self,
        *,
        goal_id: UUID,
        query: str,
        query_embedding: list[float],
        limit: int,
    ) -> list[KnowledgeChunk]:
        del goal_id, query, query_embedding, limit
        return []


def _make_3_milestone_fixture() -> tuple[
    UUID, Goal, Roadmap, list[Milestone], AvailabilitySnapshotDTO
]:
    now = datetime(2026, 11, 1, 9, 0, tzinfo=UTC)
    uid = uuid7()
    gid = uuid7()
    rid = uuid7()
    goal = Goal(
        id=gid,
        user_id=uid,
        title="System Design & Kubernetes Observability",
        raw_description="Xây dựng hệ thống phân tán và giám sát Kubernetes với eBPF.",
        prior_knowledge_level="INTERMEDIATE",
        clarification_context="Đã biết Linux cơ bản, học 2h mỗi tối.",
        target_date=date(2026, 12, 20),
        status=GoalStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
    roadmap = Roadmap(
        id=rid,
        goal_id=gid,
        user_id=uid,
        title=goal.title,
        description=goal.raw_description,
        start_date=date(2026, 11, 2),
        target_date=date(2026, 12, 20),
        status=RoadmapStatus.INITIALIZED,
        created_at=now,
        updated_at=now,
    )
    m1_id, m2_id, m3_id = uuid7(), uuid7(), uuid7()
    m1 = Milestone(
        id=m1_id,
        roadmap_id=rid,
        sequence_order=1,
        title="M1: Kubernetes Workloads & Networking",
        learning_outcomes=("Triển khai Pods, Deployments và Services",),
        completion_criteria="Chạy cụm Kubernetes mẫu",
        estimated_effort_minutes=90,
        required_concepts=("k8s-architecture-workloads",),
        status=MilestoneStatus.APPROVED,
        created_at=now,
        updated_at=now,
    )
    m2 = Milestone(
        id=m2_id,
        roadmap_id=rid,
        sequence_order=2,
        title="M2: Apache Kafka Event Streaming",
        learning_outcomes=("Thiết kế Topic/Partition và Consumer Group",),
        completion_criteria="Chạy pipeline producer/consumer",
        estimated_effort_minutes=90,
        required_concepts=("dist-kafka-event-streaming",),
        prerequisite_milestone_ids=(m1_id,),
        status=MilestoneStatus.APPROVED,
        created_at=now,
        updated_at=now,
    )
    m3 = Milestone(
        id=m3_id,
        roadmap_id=rid,
        sequence_order=3,
        title="M3: eBPF Kernel Observability",
        learning_outcomes=("Theo dõi syscall và network latency bằng eBPF",),
        completion_criteria="Hoàn thành probe XDP/kprobe",
        estimated_effort_minutes=90,
        required_concepts=("ebpf-kernel-observability",),
        prerequisite_milestone_ids=(m2_id,),
        status=MilestoneStatus.APPROVED,
        created_at=now,
        updated_at=now,
    )
    avail = AvailabilitySnapshotDTO(
        user_id=uid,
        mode="MODE_A",
        daily_cap_minutes=180,
        weekly_capacity_minutes=1260,
        daily_quota_minutes={
            "monday": 180,
            "tuesday": 180,
            "wednesday": 180,
            "thursday": 180,
            "friday": 180,
            "saturday": 180,
            "sunday": 180,
        },
        availability_slots=(),
        disabled_weekdays=(),
    )
    return uid, goal, roadmap, [m1, m2, m3], avail


# ---------------------------------------------------------------------------
# PR-3A Tests: HTTP Transport, AFC Disabled, Concurrency, Timeout Budget,
# Sibling Checkpoint Preservation & Safe Retry/Resume, Hardened Fingerprint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_litellm_adapter_uses_bounded_httpx_http11_pool_and_disables_afc() -> None:
    clear_google_genai_client_cache()
    try:
        client = LiteLLMAdapter.get_shared_google_genai_client(
            "test-api-key",
            "http://127.0.0.1:8045",
        )
        api_client = client._api_client
        assert api_client._use_aiohttp() is False
        hc = api_client._async_httpx_client
        assert isinstance(hc, httpx.AsyncClient)
        limits = hc._transport._pool._max_connections  # type: ignore[attr-defined]
        keepalive = hc._transport._pool._max_keepalive_connections  # type: ignore[attr-defined]
        assert limits == 12
        assert keepalive == 6
        assert hc.is_closed is False

        cfg = LiteLLMAdapter.build_generate_content_config(
            system_instruction="Sys",
            response_mime_type="application/json",
            thinking_level="LOW",
        )
        assert cfg.automatic_function_calling is not None
        assert cfg.automatic_function_calling.disable is True
    finally:
        await aclose_google_genai_clients()
        assert hc.is_closed is True


def test_concurrency_pacing_and_decomposer_defaults() -> None:
    cfg = Settings(_env_file=None)
    assert cfg.ai_max_concurrent_llm_requests == 4
    assert cfg.ai_decomposer_max_concurrency == 2
    decomposer = MilestoneScopedTaskDecomposer(llm_provider=StubLLMAdapter())
    assert decomposer._max_concurrency == 2


@pytest.mark.asyncio
async def test_decomposer_does_not_truncate_timeout_at_26s() -> None:
    uid, goal, roadmap, milestones, avail_snap = _make_3_milestone_fixture()
    avail = AvailabilityConfigurationDTO(mode="MODE_A", default_daily_quota_minutes=180)
    recorded_timeouts: list[float | None] = []

    class _TimeoutSpyLLM(StubLLMAdapter):
        async def generate_structured(self, **kwargs: Any) -> LLMGenerationResult:
            if "GENERATE_PROPOSAL_TASKS" in str(kwargs.get("user_prompt") or ""):
                recorded_timeouts.append(kwargs.get("timeout_seconds"))
            return await super().generate_structured(**kwargs)

    decomposer = MilestoneScopedTaskDecomposer(
        llm_provider=_TimeoutSpyLLM(),
        enable_tier3_judge=False,
        user_id=uid,
        goal_id=goal.id,
        roadmap_id=roadmap.id,
    )
    await decomposer.decompose_and_validate(
        goal=goal,
        roadmap=roadmap,
        milestones=[milestones[0]],
        availability=avail,
        learner_profile=_FakeLearnerProfilePort(uid).profile,
        start_date=roadmap.start_date,
        max_milestone_retries=1,
        reference_date=roadmap.start_date,
    )
    assert len(recorded_timeouts) == 1
    assert recorded_timeouts[0] is not None
    # Previously capped prematurely at 26.0s when attempt==1 and max_milestone_retries>=1
    assert recorded_timeouts[0] > 30.0
    assert recorded_timeouts[0] <= 36.0


@pytest.mark.asyncio
async def test_sibling_checkpoints_preserved_before_timeout_and_retry_charges_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    uid, goal, roadmap, milestones, avail_snap = _make_3_milestone_fixture()
    m1, m2, m3 = milestones
    fake_redis = _FakeRedisClient()

    # Patch RedisMilestoneCheckpointStore created internally by Job 1 and Job 2
    created_stores: list[RedisMilestoneCheckpointStore] = []

    class _TrackedRedisStore(RedisMilestoneCheckpointStore):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            kwargs["redis_client"] = fake_redis
            super().__init__(*args, **kwargs)
            created_stores.append(self)

    monkeypatch.setattr(
        "src.planning.application.use_cases.proposal_generation_use_cases.RedisMilestoneCheckpointStore",
        _TrackedRedisStore,
    )

    class _ConcurrentFaultLLM(StubLLMAdapter):
        def __init__(self) -> None:
            super().__init__()
            self.fail_mids: set[UUID] = {m3.id}
            self.calls_by_mid: dict[UUID, int] = {}

        async def generate_structured(self, **kwargs: Any) -> LLMGenerationResult:
            prompt = str(kwargs.get("user_prompt") or "")
            if "GENERATE_PROPOSAL_TASKS" in prompt and "MILESTONE_IDS: [" in prompt:
                start = prompt.index("MILESTONE_IDS: [") + len("MILESTONE_IDS: [")
                mid = UUID(prompt[start : prompt.index("]", start)].strip())
                self.calls_by_mid[mid] = self.calls_by_mid.get(mid, 0) + 1
                if mid in self.fail_mids:
                    # Delay slightly while siblings complete, then raise empty TimeoutError()
                    await asyncio.sleep(0.02)
                    raise TimeoutError()
                await asyncio.sleep(0.05)
            return await super().generate_structured(**kwargs)

    llm_job1 = _ConcurrentFaultLLM()
    quota = _RecordingQuotaFacade()
    sse_store = InMemorySseJobStore()
    proposal_repo = _FakeProposalRepo()
    roadmap_repo = _FakeRoadmapRepo(roadmap)
    milestone_repo = _FakeMilestoneRepo(milestones)
    goal_repo = _FakeGoalRepo(goal)
    avail_port = _FakeAvailabilityPort(avail_snap)
    exec_sync = _FakeExecutionSyncPort()

    job1_id = uuid7()
    res1_id = await quota.reserve_quota(uid, "SCHEDULE_PROPOSAL_GEN", cost=1)
    await sse_store.create_job(
        job_id=job1_id,
        user_id=uid,
        roadmap_id=roadmap.id,
        reservation_id=res1_id,
        job_type="SCHEDULE_PROPOSAL_GEN",
        operation=f"SCHEDULE_PROPOSAL_GEN:{roadmap.id}",
    )

    uc1 = ExecuteScheduleProposalGenerationUseCase(
        goal_repo=goal_repo,
        roadmap_repo=roadmap_repo,
        milestone_repo=milestone_repo,
        proposal_repo=proposal_repo,
        availability_query_port=avail_port,
        learner_profile_port=_FakeLearnerProfilePort(uid),
        execution_sync_port=exec_sync,
        quota_facade=quota,
        llm_provider=llm_job1,
        sse_job_store=sse_store,
        uow=_FakeUoW(),
        enable_tier3_judge=False,
        user_query_port=_FakeUserQueryPort(uid),
    )

    with pytest.raises(TimeoutError) as exc_info:
        await uc1.execute(
            job_id=job1_id,
            user_id=uid,
            roadmap_id=roadmap.id,
            reservation_id=res1_id,
            max_retries=0,
            decomposer_architecture_mode="milestone_scoped",
        )
    # Must have non-empty descriptive message even when underlying TimeoutError had ""
    assert str(exc_info.value).strip() != ""
    # Quota released cleanly on failure
    assert len(quota.released) == 1
    assert quota.released[0][0] == res1_id
    assert quota.committed == []
    # Internal Redis store closed cleanly in finally (no connection leak)
    assert fake_redis.closed_count == 1
    # Sibling milestones M1 & M2 persisted checkpoints in Redis before Job 1 failed!
    saved_cp_keys = [k for k in fake_redis.store if k.startswith("ff:checkpoint:milestone:")]
    assert len(saved_cp_keys) == 2

    # Job 2: Retry with M3 healed -> M1 & M2 load from Redis (0 LLM calls), only M3 calls LLM
    llm_job2 = _ConcurrentFaultLLM()
    llm_job2.fail_mids = set()
    job2_id = uuid7()
    res2_id = await quota.reserve_quota(uid, "SCHEDULE_PROPOSAL_GEN", cost=1)
    await sse_store.create_job(
        job_id=job2_id,
        user_id=uid,
        roadmap_id=roadmap.id,
        reservation_id=res2_id,
        job_type="SCHEDULE_PROPOSAL_GEN",
        operation=f"SCHEDULE_PROPOSAL_GEN:{roadmap.id}",
    )
    uc2 = ExecuteScheduleProposalGenerationUseCase(
        goal_repo=goal_repo,
        roadmap_repo=roadmap_repo,
        milestone_repo=milestone_repo,
        proposal_repo=proposal_repo,
        availability_query_port=avail_port,
        learner_profile_port=_FakeLearnerProfilePort(uid),
        execution_sync_port=exec_sync,
        quota_facade=quota,
        llm_provider=llm_job2,
        sse_job_store=sse_store,
        uow=_FakeUoW(),
        enable_tier3_judge=False,
        user_query_port=_FakeUserQueryPort(uid),
    )
    proposal = await uc2.execute(
        job_id=job2_id,
        user_id=uid,
        roadmap_id=roadmap.id,
        reservation_id=res2_id,
        max_retries=0,
        decomposer_architecture_mode="milestone_scoped",
    )
    assert proposal.status == ScheduleProposalStatus.DRAFT
    assert llm_job2.calls_by_mid.get(m1.id, 0) == 0
    assert llm_job2.calls_by_mid.get(m2.id, 0) == 0
    assert llm_job2.calls_by_mid.get(m3.id, 0) == 1
    # Checkpoint audit rows recorded for the 2 cached milestones
    checkpoint_audits = [
        row
        for row in quota.attempt_usage_rows
        if str(row.get("idempotency_key", "")).startswith("checkpoint:")
    ]
    assert len(checkpoint_audits) == 2
    assert all(row["usage_source"] == "CACHE" for row in checkpoint_audits)
    # Exactly 1 credit committed upon final success
    assert len(quota.committed) == 1
    assert quota.committed[0][0] == res2_id
    assert fake_redis.closed_count == 2


def test_fingerprint_invalidation_on_clarification_start_date_and_stage_model() -> None:
    uid, goal, roadmap, milestones, _ = _make_3_milestone_fixture()
    m1 = milestones[0]
    avail = AvailabilityConfigurationDTO(mode="MODE_A", default_daily_quota_minutes=120)
    profile = _FakeLearnerProfilePort(uid).profile
    prompt_checksum = (
        build_planning_prompt_registry().latest(TASK_DECOMPOSER_SKILL.skill_id).checksum
    )

    base_fp = compute_decomposition_context_fingerprint(
        milestone=m1,
        all_milestones=milestones,
        target_date=roadmap.target_date,
        start_date=roadmap.start_date,
        learner_profile=profile,
        prior_knowledge_level=goal.prior_knowledge_level,
        clarification_context=goal.clarification_context,
        availability=avail,
        prompt_checksum=prompt_checksum,
        model_name="gemini-3.8-flash-low",
    )
    diff_clar = compute_decomposition_context_fingerprint(
        milestone=m1,
        all_milestones=milestones,
        target_date=roadmap.target_date,
        start_date=roadmap.start_date,
        learner_profile=profile,
        prior_knowledge_level=goal.prior_knowledge_level,
        clarification_context="Đã từng vận hành production EKS cluster 2 năm.",
        availability=avail,
        prompt_checksum=prompt_checksum,
        model_name="gemini-3.8-flash-low",
    )
    diff_start = compute_decomposition_context_fingerprint(
        milestone=m1,
        all_milestones=milestones,
        target_date=roadmap.target_date,
        start_date=date(2026, 11, 10),
        learner_profile=profile,
        prior_knowledge_level=goal.prior_knowledge_level,
        clarification_context=goal.clarification_context,
        availability=avail,
        prompt_checksum=prompt_checksum,
        model_name="gemini-3.8-flash-low",
    )
    diff_model = compute_decomposition_context_fingerprint(
        milestone=m1,
        all_milestones=milestones,
        target_date=roadmap.target_date,
        start_date=roadmap.start_date,
        learner_profile=profile,
        prior_knowledge_level=goal.prior_knowledge_level,
        clarification_context=goal.clarification_context,
        availability=avail,
        prompt_checksum=prompt_checksum,
        model_name="gemini-3.8-flash-medium",
    )
    assert base_fp != diff_clar
    assert base_fp != diff_start
    assert base_fp != diff_model
    assert compute_milestone_checkpoint_key(
        roadmap_id=roadmap.id, milestone=m1, context_fingerprint=base_fp
    ) != compute_milestone_checkpoint_key(
        roadmap_id=roadmap.id, milestone=m1, context_fingerprint=diff_clar
    )


# ---------------------------------------------------------------------------
# PR-3B Tests: Learning Resources Discovery, Non-Leakage, Source Grounding
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_learning_resource_seed_fixes_expansion_and_non_leakage() -> None:
    repo = InMemoryKnowledgeBaseRepository()

    # 1. Fixed mismatched Angular concept_ids
    ang_signals = await repo.get_learning_resources_and_guidance(
        concept_ids=["angular-standalone-signals"], limit=5
    )
    assert any("angular.dev/guide/signals" in r.url for r in ang_signals)
    ang_forms = await repo.get_learning_resources_and_guidance(
        concept_ids=["angular-routing-reactive-forms"], limit=5
    )
    assert ang_forms

    # 2. Out-of-seed domains now present and discoverable with HTTPS official docs
    k8s = await repo.get_learning_resources_and_guidance(
        query="Kubernetes eBPF observability", limit=5
    )
    assert any(
        "kubernetes.io" in r.url or "ebpf.io" in r.url or "docs.kernel.org" in r.url for r in k8s
    )

    kafka = await repo.get_learning_resources_and_guidance(
        query="Apache Kafka event streaming", limit=5
    )
    assert any("kafka.apache.org" in r.url for r in kafka)

    rust = await repo.get_learning_resources_and_guidance(query="Rust ownership borrowing", limit=5)
    assert any("doc.rust-lang.org" in r.url for r in rust)

    # 3. Unrelated query must return [] (NEVER fall back to Python resources!)
    unrelated = await repo.get_learning_resources_and_guidance(
        query="Quantum Underwater Basketweaving",
        task_type="PRACTICE",
        limit=5,
    )
    assert unrelated == []

    # 4. All seeded resources use strict HTTPS URLs
    assert all(r.url.startswith("https://") for r in VERIFIED_SEED_RESOURCES)
    seed_cids = {c.concept_id for c in VERIFIED_SEED_CONCEPTS}
    assert all(r.concept_id in seed_cids for r in VERIFIED_SEED_RESOURCES)


@pytest.mark.asyncio
async def test_curated_discovery_url_validation_and_live_404_stripping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clear_url_health_cache()

    # SSRF / non-HTTPS / unallowlisted URLs rejected
    assert validate_official_resource_url("http://kubernetes.io/docs/") is False
    assert validate_official_resource_url("https://127.0.0.1/admin") is False
    assert validate_official_resource_url("https://localhost:8000/docs") is False
    assert validate_official_resource_url("https://evil-phishing.example.com/k8s") is False
    assert validate_official_resource_url("https://kubernetes.io/docs/concepts/overview/") is True

    # Verify fallback discovery covers out-of-seed unverified_concepts
    discovered = discover_curated_official_resources(
        query="Triển khai giám sát mạng kernel",
        unverified_concepts=["eBPF XDP", "Kubernetes CNI"],
        limit=4,
    )
    urls = [r.url for r in discovered]
    assert any("ebpf.io" in u or "docs.kernel.org" in u for u in urls)
    assert any("kubernetes.io" in u for u in urls)

    # Verify live HEAD check strips 404 URLs outside test/mock mode
    monkeypatch.setattr(
        "src.planning.application.services.learning_resource_discovery.get_settings",
        lambda: SimpleNamespace(environment="production", llm_provider="gemini"),
    )

    async def _fake_public_dns(url: str) -> None:
        del url

    monkeypatch.setattr(
        "src.planning.application.knowledge.safe_url_fetcher.SafeUrlFetcher._validate_public_destination",
        _fake_public_dns,
    )

    class _FakeHeadClient:
        def __init__(self, **kwargs: Any) -> None:
            del kwargs

        async def __aenter__(self) -> _FakeHeadClient:
            return self

        async def __aexit__(self, *args: Any) -> None:
            del args

        async def head(self, url: str, headers: dict[str, str] | None = None) -> Any:
            del headers
            status_code = 404 if "broken" in url else 200
            return SimpleNamespace(status_code=status_code, headers={})

    monkeypatch.setattr(httpx, "AsyncClient", _FakeHeadClient)
    assert await verify_official_url_live("https://kubernetes.io/docs/broken-page") is False
    assert await verify_official_url_live("https://kubernetes.io/docs/concepts/overview/") is True


@pytest.mark.asyncio
async def test_milestone_decomposer_grounds_indexed_sources_and_strips_hallucinated_urls() -> None:
    uid, goal, roadmap, milestones, avail_snap = _make_3_milestone_fixture()
    now = datetime(2026, 11, 1, 9, 0, tzinfo=UTC)
    avail = AvailabilityConfigurationDTO(mode="MODE_A", default_daily_quota_minutes=180)

    indexed_url_source = KnowledgeSource(
        id=uuid7(),
        user_id=uid,
        goal_id=goal.id,
        source_type=KnowledgeSourceType.URL,
        title="Cilium eBPF Networking Guide",
        source_uri="https://ebpf.io/what-is-ebpf/",
        content_hash="abc123",
        ingestion_status=KnowledgeIngestionStatus.INDEXED,
        chunk_count=3,
        provenance_metadata={"final_url": "https://ebpf.io/what-is-ebpf/"},
        error_detail=None,
        created_at=now,
        updated_at=now,
    )
    indexed_pdf_source = KnowledgeSource(
        id=uuid7(),
        user_id=uid,
        goal_id=goal.id,
        source_type=KnowledgeSourceType.PDF,
        title="Internal Kernel Notes PDF",
        source_uri="/tmp/focusflow-knowledge/secret-local-path.pdf",
        content_hash="def456",
        ingestion_status=KnowledgeIngestionStatus.INDEXED,
        chunk_count=2,
        provenance_metadata={"original_filename": "kernel-notes.pdf"},
        error_detail=None,
        created_at=now,
        updated_at=now,
    )
    pending_source = KnowledgeSource(
        id=uuid7(),
        user_id=uid,
        goal_id=goal.id,
        source_type=KnowledgeSourceType.URL,
        title="Unindexed Pending URL",
        source_uri="https://example.com/pending",
        content_hash="pend",
        ingestion_status=KnowledgeIngestionStatus.PENDING,
        chunk_count=0,
        provenance_metadata={},
        error_detail=None,
        created_at=now,
        updated_at=now,
    )
    assert knowledge_source_to_learning_resource(pending_source) is None

    # Stub LLM deliberately emits a hallucinated resource_id + hallucinated learning_resources URL
    class _HallucinatingLLM(StubLLMAdapter):
        async def generate_structured(self, **kwargs: Any) -> LLMGenerationResult:
            res = await super().generate_structured(**kwargs)
            prompt = str(kwargs.get("user_prompt") or "")
            if "GENERATE_PROPOSAL_TASKS" in prompt and isinstance(res.payload, dict):
                tasks = list(res.payload.get("tasks", []))
                for t in tasks:
                    t["resource_ids"] = ["res-hallucinated-999"]
                    t["learning_resources"] = [
                        {
                            "title": "Fake 404 Blog",
                            "url": "https://hallucinated.bad/404",
                            "type": "DOCS",
                        }
                    ]
                return LLMGenerationResult(
                    payload={**res.payload, "tasks": tasks},
                    prompt_tokens=res.prompt_tokens,
                    output_tokens=res.output_tokens,
                    thinking_tokens=0,
                    model_id=res.model_id,
                )
            return res

    # Strict unit test: resolve_task_resources_from_tool_results strips hallucinated IDs & URLs
    stripped = resolve_task_resources_from_tool_results(
        {
            "tasks": [
                {
                    "task_id": "T1",
                    "resource_ids": ["res-fake"],
                    "learning_resources": [
                        {"title": "Fake", "url": "https://fake.tld/404", "type": "DOCS"}
                    ],
                }
            ]
        },
        (),
        strict=True,
    )
    assert stripped["tasks"][0]["learning_resources"] == []

    # Out-of-seed milestone with unverified_concepts + uploaded INDEXED sources
    out_of_seed_milestone = Milestone(
        id=milestones[2].id,
        roadmap_id=roadmap.id,
        sequence_order=1,
        title="M1: eBPF & Cilium Kernel Tracing",
        learning_outcomes=("Viết chương trình eBPF theo dõi syscall",),
        completion_criteria="Chạy được eBPF tracer",
        estimated_effort_minutes=90,
        required_concepts=(),
        unverified_concepts=("eBPF", "Cilium"),
        status=MilestoneStatus.APPROVED,
        created_at=now,
        updated_at=now,
    )
    # Empty KB returns [] -> curated official-docs discovery + learner INDEXED sources must ground tasks!
    empty_kb = InMemoryKnowledgeBaseRepository(concepts=(), edges=(), resources=())
    ks_repo = _FakeKnowledgeSourceRepo([indexed_url_source, indexed_pdf_source, pending_source])
    decomposer = MilestoneScopedTaskDecomposer(
        llm_provider=_HallucinatingLLM(),
        knowledge_base=empty_kb,
        knowledge_source_repo=ks_repo,
        enable_tier3_judge=False,
        user_id=uid,
        goal_id=goal.id,
        roadmap_id=roadmap.id,
    )
    gate_res = await decomposer.decompose_and_validate(
        goal=goal,
        roadmap=roadmap,
        milestones=[out_of_seed_milestone],
        availability=avail,
        learner_profile=_FakeLearnerProfilePort(uid).profile,
        start_date=roadmap.start_date,
        max_milestone_retries=0,
        reference_date=roadmap.start_date,
    )
    all_attached_urls = [
        r["url"]
        for t in gate_res.validated_proposal_data["tasks"]
        for r in t.get("learning_resources", [])
    ]
    assert all_attached_urls, "Out-of-seed milestone must receive verified resources"
    assert "https://hallucinated.bad/404" not in all_attached_urls
    assert all("/tmp/focusflow-knowledge/" not in u for u in all_attached_urls)
    assert any("ebpf.io" in u or "docs.kernel.org" in u for u in all_attached_urls)
    assert any(u.startswith("#knowledge-source-") for u in all_attached_urls)


# ---------------------------------------------------------------------------
# PR-3C Tests: BUG-06 (Manual Estimated Effort) & BUG-08 (Learner Timezone)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bug06_save_manual_roadmap_plan_preserves_effort_and_applies() -> None:
    now = datetime(2026, 11, 1, 9, 0, tzinfo=UTC)
    uid = uuid7()
    gid = uuid7()
    rid = uuid7()
    mid = uuid7()

    goal = Goal(
        id=gid,
        user_id=uid,
        title="Manual Kubernetes Roadmap",
        raw_description="Tự lập lộ trình học Kubernetes.",
        prior_knowledge_level="BEGINNER",
        target_date=date(2026, 12, 15),
        status=GoalStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
    roadmap = Roadmap(
        id=rid,
        goal_id=gid,
        user_id=uid,
        title=goal.title,
        description=goal.raw_description,
        start_date=date(2026, 11, 2),
        target_date=date(2026, 12, 15),
        status=RoadmapStatus.INITIALIZED,
        created_at=now,
        updated_at=now,
    )
    avail = AvailabilitySnapshotDTO(
        user_id=uid,
        mode="MODE_A",
        daily_cap_minutes=240,
        weekly_capacity_minutes=1680,
        daily_quota_minutes={
            "monday": 240,
            "tuesday": 240,
            "wednesday": 240,
            "thursday": 240,
            "friday": 240,
            "saturday": 240,
            "sunday": 240,
        },
        availability_slots=(),
        disabled_weekdays=(),
    )

    milestone_repo = _FakeMilestoneRepo([])
    roadmap_repo = _FakeRoadmapRepo(roadmap)
    proposal_repo = _FakeProposalRepo()
    avail_port = _FakeAvailabilityPort(avail)
    exec_sync = _FakeExecutionSyncPort()
    uow = _FakeUoW()

    manual_uc = SaveManualRoadmapPlanUseCase(
        goal_repo=_FakeGoalRepo(goal),
        roadmap_repo=roadmap_repo,
        milestone_repo=milestone_repo,
        proposal_repo=proposal_repo,
        availability_query_port=avail_port,
        execution_sync_port=exec_sync,
        uow=uow,
        user_query_port=_FakeUserQueryPort(uid),
    )

    view = await manual_uc.execute(
        user_id=uid,
        roadmap_id=rid,
        milestones=[
            {
                "id": str(mid),
                "milestone_id": str(mid),
                "sequence_order": 1,
                "title": "Chặng 1: Core K8s",
                "description": "Pods & Deployments",
                "estimated_effort_minutes": 360,
                "learning_outcomes": ["Triển khai Deployment"],
                "completion_criteria": "Chạy pod healthy",
                "required_concepts": ["k8s-architecture-workloads"],
                "unverified_concepts": ["kubectl"],
            }
        ],
        tasks=[
            {
                "milestone_id": str(mid),
                "title": "Học Pods & Services",
                "learning_objective": "Triển khai được Deployment trên Kubernetes",
                "completion_criteria": "Chạy được Deployment healthy với 2 replicas",
                "concept_ids": ["k8s-architecture-workloads"],
                "covered_outcome_ids": ["M1-O1"],
                "estimated_minutes": 90,
                "scheduled_date": "2026-11-02",
                "scheduled_start": "2026-11-02T12:00:00Z",
                "scheduled_end": "2026-11-02T13:30:00Z",
            }
        ],
    )
    saved_ms = await milestone_repo.list_by_roadmap_id(rid)
    assert len(saved_ms) == 1
    assert saved_ms[0].estimated_effort_minutes == 360
    assert saved_ms[0].learning_outcomes == ("Triển khai Deployment",)
    assert saved_ms[0].completion_criteria == "Chạy pod healthy"
    assert saved_ms[0].required_concepts == ("k8s-architecture-workloads",)
    assert saved_ms[0].unverified_concepts == ("kubectl",)

    # Roundtrip Apply on the 360-minute manual plan
    apply_uc = ApplyScheduleProposalUseCase(
        roadmap_repo=roadmap_repo,
        milestone_repo=milestone_repo,
        proposal_repo=proposal_repo,
        schedule_repo=_FakeScheduleRepo(),
        block_repo=_FakeBlockRepo(),
        availability_query_port=avail_port,
        execution_sync_port=exec_sync,
        schedule_change_log_port=_FakeChangeLogPort(),
        uow=uow,
        user_query_port=_FakeUserQueryPort(uid),
        goal_repo=_FakeGoalRepo(goal),
    )
    apply_res = await apply_uc.execute(
        user_id=uid,
        roadmap_id=rid,
        proposal_id=view.proposal.id,
    )
    assert apply_res.proposal.status == ScheduleProposalStatus.APPLIED
    assert apply_res.inserted_tasks_count == 1

    # Also verify fallback when estimated_effort_minutes is omitted -> sum of tasks
    await manual_uc.execute(
        user_id=uid,
        roadmap_id=rid,
        milestones=[
            {
                "id": str(uuid7()),
                "sequence_order": 1,
                "title": "Chặng mới không truyền effort",
            }
        ],
        tasks=[
            {
                "milestone_sequence_order": 1,
                "title": "Nhiệm vụ 120p",
                "learning_objective": "Hiểu nền tảng",
                "completion_criteria": "Hoàn thành bài tập 1",
                "estimated_minutes": 120,
                "scheduled_date": "2026-11-03",
                "scheduled_start": "2026-11-03T12:00:00Z",
                "scheduled_end": "2026-11-03T14:00:00Z",
            },
            {
                "milestone_sequence_order": 1,
                "title": "Nhiệm vụ 90p",
                "learning_objective": "Thực hành nâng cao",
                "completion_criteria": "Hoàn thành bài tập 2",
                "estimated_minutes": 90,
                "scheduled_date": "2026-11-04",
                "scheduled_start": "2026-11-04T12:00:00Z",
                "scheduled_end": "2026-11-04T13:30:00Z",
            },
        ],
    )
    summed_ms = await milestone_repo.list_by_roadmap_id(rid)
    assert summed_ms[0].estimated_effort_minutes == 210


@pytest.mark.asyncio
async def test_bug08_execution_dashboard_formats_today_queue_in_learner_timezone() -> None:
    uid = uuid7()
    rid = uuid7()
    tid = uuid7()

    fake_task = SimpleNamespace(
        id=tid,
        roadmap_id=rid,
        title="Học tối theo giờ Việt Nam",
        estimated_minutes=90,
        status="TODO",
        scheduled_start=datetime(2026, 11, 2, 12, 0, tzinfo=UTC),
        scheduled_end=datetime(2026, 11, 2, 13, 30, tzinfo=UTC),
    )

    class _FakeScalarResult:
        def scalars(self) -> _FakeScalarResult:
            return self

        def all(self) -> list[Any]:
            return [fake_task]

    class _FakeSession:
        async def execute(self, stmt: Any, params: Any = None) -> Any:
            del stmt, params
            return _FakeScalarResult()

    adapter = ExecutionDashboardAdapter(_FakeSession())  # type: ignore[arg-type]

    async def _fake_active_roadmaps(user_id: UUID) -> dict[UUID, str]:
        del user_id
        return {rid: "Lộ trình K8s"}

    adapter._get_active_roadmaps = _fake_active_roadmaps  # type: ignore[method-assign]

    queue = await adapter.get_today_queue(
        uid,
        today=date(2026, 11, 2),
        user_timezone="Asia/Ho_Chi_Minh",
    )
    assert len(queue) == 1
    assert queue[0].scheduled_time == "19:00 - 20:30"


@pytest.mark.asyncio
async def test_bug08_planning_dashboard_adapter_week_blocks_convert_to_local_timezone() -> None:
    """BUG-08: Dashboard weekly calendar grid must render start_time/end_time in user's local timezone."""
    from src.planning.infrastructure.adapters.planning_dashboard_adapter import (
        PlanningDashboardAdapter,
    )

    uid = uuid7()
    rid = uuid7()
    bid = uuid7()
    fake_block = SimpleNamespace(
        id=bid,
        roadmap_id=rid,
        task_id=None,
        block_date=date(2026, 11, 2),
        start_time=datetime(2026, 11, 2, 12, 0, tzinfo=UTC),
        end_time=datetime(2026, 11, 2, 13, 30, tzinfo=UTC),
        block_type="STUDY",
        status="PLANNED",
        scheduled_duration_minutes=90,
        placement_rationale=None,
    )

    class _FakeExecRes:
        def all(self) -> list[Any]:
            return [(fake_block, "Lộ trình FastAPI")]

    class _FakeSession:
        async def execute(self, stmt: Any, params: Any = None) -> Any:
            del stmt, params
            return _FakeExecRes()

    adapter = PlanningDashboardAdapter(_FakeSession())  # type: ignore[arg-type]
    blocks = await adapter.get_week_schedule_blocks(
        uid,
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 8),
        user_timezone="Asia/Ho_Chi_Minh",
    )
    assert len(blocks) == 1
    assert blocks[0].start_time == "19:00"
    assert blocks[0].end_time == "20:30"
