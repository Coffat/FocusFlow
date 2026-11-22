"""Unit tests for Phase 5: AI Generation Timeout & Checkpoint Recovery (AI_GATEWAY_TIMEOUT)."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Sequence
from datetime import UTC, date, datetime
from types import TracebackType
from typing import Any
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest

from src.account.public_api import LearnerProfileDTO, UserSnapshotDTO
from src.planning.application.ports.milestone_checkpoint_port import (
    InMemoryMilestoneCheckpointStore,
    RedisMilestoneCheckpointStore,
)
from src.planning.application.services.milestone_scoped_decomposer import (
    MilestoneDecompositionTimeoutError,
    MilestoneScopedTaskDecomposer,
    calculate_dynamic_subjob_concurrency,
)
from src.planning.application.use_cases.proposal_generation_use_cases import (
    ExecuteScheduleProposalGenerationUseCase,
    InitiateScheduleProposalGenerationUseCase,
)
from src.planning.domain.models.goal import Goal
from src.planning.domain.models.knowledge_concept import (
    LearningResource,
    compute_deterministic_resource_id,
)
from src.planning.domain.models.milestone import Milestone, MilestoneStatus
from src.planning.domain.models.roadmap import Roadmap, RoadmapStatus
from src.planning.domain.models.schedule import ScheduleProposal, ScheduleProposalStatus
from src.planning.domain.services.validation_types import AvailabilityConfigurationDTO
from src.shared_kernel.application.llm_port import (
    LLMGenerationResult,
    LLMToolDeclarationDTO,
    LLMToolExecutor,
)
from src.shared_kernel.domain.base import generate_uuid7
from src.shared_kernel.infrastructure.sse.job_store import InMemorySseJobStore

# ---------------------------------------------------------------------------
# Minimal deterministic fakes for Planning Use Cases
# ---------------------------------------------------------------------------


class _FakeUoW:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    async def __aenter__(self) -> _FakeUoW:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            self.rollbacks += 1

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


class _FakeGoalRepo:
    def __init__(self, goal: Goal) -> None:
        self._goal = goal

    async def get_by_id(self, goal_id: UUID) -> Goal | None:
        return self._goal if self._goal.id == goal_id else None

    async def get_by_id_for_user(self, goal_id: UUID, user_id: UUID) -> Goal | None:
        if self._goal.id == goal_id and self._goal.user_id == user_id:
            return self._goal
        return None


class _FakeRoadmapRepo:
    def __init__(self, roadmap: Roadmap) -> None:
        self._roadmap = roadmap

    async def get_by_id_for_user(self, roadmap_id: UUID, user_id: UUID) -> Roadmap | None:
        if self._roadmap.id == roadmap_id and self._roadmap.user_id == user_id:
            return self._roadmap
        return None

    async def list_by_user_id(self, user_id: UUID, status: str | None = None) -> list[Roadmap]:
        if self._roadmap.user_id != user_id:
            return []
        if status is not None and self._roadmap.status.value != status:
            return []
        return [self._roadmap]

    async def save(self, roadmap: Roadmap) -> Roadmap:
        self._roadmap = roadmap
        return roadmap


class _FakeMilestoneRepo:
    def __init__(self, milestones: list[Milestone]) -> None:
        self._milestones = list(milestones)

    async def list_by_roadmap_id(self, roadmap_id: UUID) -> list[Milestone]:
        return [m for m in self._milestones if m.roadmap_id == roadmap_id]


class _FakeProposalRepo:
    def __init__(self) -> None:
        self.saved: list[ScheduleProposal] = []
        self.discarded_calls = 0

    async def discard_existing_drafts(self, roadmap_id: UUID, now: datetime) -> int:
        self.discarded_calls += 1
        return 0

    async def save(self, proposal: ScheduleProposal) -> ScheduleProposal:
        self.saved.append(proposal)
        return proposal

    async def get_latest_for_roadmap(self, roadmap_id: UUID) -> ScheduleProposal | None:
        return self.saved[-1] if self.saved else None


class _FakeAvailabilityPort:
    def __init__(self, config: AvailabilityConfigurationDTO) -> None:
        self._config = config

    async def get_availability_config(self, user_id: UUID) -> AvailabilityConfigurationDTO:
        return self._config


class _FakeLearnerProfilePort:
    def __init__(self, user_id: UUID) -> None:
        self._user_id = user_id

    async def get_learner_profile(self, user_id: UUID) -> LearnerProfileDTO:
        return LearnerProfileDTO(
            user_id=user_id,
            opt_session_minutes=60,
            estimation_bias_beta=1.0,
            peak_productivity_slots={},
        )


class _FakeUserQueryPort:
    def __init__(self, user_id: UUID, timezone: str = "UTC") -> None:
        self._user_id = user_id
        self._timezone = timezone

    async def get_user_by_id(self, user_id: UUID) -> UserSnapshotDTO | None:
        if user_id != self._user_id:
            return None
        return UserSnapshotDTO(
            id=user_id,
            email="learner@focusflow.dev",
            full_name="Test Learner",
            role="LEARNER",
            tier="FREE",
            is_locked=False,
            timezone=self._timezone,
        )


class _FakeExecSyncPort:
    async def get_tasks_for_roadmaps(
        self,
        roadmap_ids: Sequence[UUID],
        *,
        roadmap_target_dates: dict[UUID, date | None] | None = None,
    ) -> list[dict[str, Any]]:
        return []


class _RecordingQuotaFacade:
    def __init__(self) -> None:
        self.reserved: list[tuple[UUID, str]] = []
        self.committed: list[tuple[UUID, int, int, str]] = []
        self.released: list[tuple[UUID, str]] = []

    async def reserve_quota(
        self,
        user_id: UUID,
        operation_type: str = "ROADMAP_GEN",
        cost: int = 1,
        ttl_seconds: int = 120,
    ) -> UUID:
        res_id = generate_uuid7()
        self.reserved.append((res_id, operation_type))
        return res_id

    async def commit_reservation(
        self,
        reservation_id: UUID,
        *,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        model_name: str = "stub",
    ) -> None:
        self.committed.append((reservation_id, prompt_tokens, completion_tokens, model_name))

    async def release_reservation(self, reservation_id: UUID, *, reason: str = "") -> None:
        self.released.append((reservation_id, reason))


class _FakeKnowledgeBasePort:
    def __init__(self, resources: list[LearningResource] | None = None) -> None:
        self._resources = resources or []

    async def get_learning_resources_and_guidance(
        self,
        *,
        query: str | None = None,
        concept_ids: list[str] | None = None,
        limit: int = 6,
    ) -> list[LearningResource]:
        return list(self._resources[:limit])


def _make_four_milestone_fixture() -> tuple[
    UUID, Goal, Roadmap, list[Milestone], AvailabilityConfigurationDTO
]:
    now = datetime(2026, 6, 1, 8, 0, tzinfo=UTC)
    user_id = uuid4()
    goal_id = uuid4()
    roadmap_id = uuid4()

    goal = Goal(
        id=goal_id,
        user_id=user_id,
        title="Master Distributed Systems with Python",
        raw_description="Build resilient async backends with PostgreSQL and Redis.",
        target_date=date(2026, 9, 1),
        prior_knowledge_level="INTERMEDIATE",
        clarification_context=None,
        created_at=now,
        updated_at=now,
    )
    roadmap = Roadmap(
        id=roadmap_id,
        goal_id=goal_id,
        user_id=user_id,
        title="Distributed Python Roadmap",
        description="4-milestone learning path",
        start_date=date(2026, 6, 2),
        target_date=date(2026, 9, 1),
        status=RoadmapStatus.INITIALIZED,
        created_at=now,
        updated_at=now,
    )

    milestones: list[Milestone] = []
    for seq in range(1, 5):
        milestones.append(
            Milestone(
                id=uuid4(),
                roadmap_id=roadmap_id,
                title=f"Milestone {seq}: Core Module {seq}",
                description=f"Deep dive into module {seq}",
                sequence_order=seq,
                learning_outcomes=(f"M{seq}-O1: Master topic {seq}",),
                completion_criteria=f"Complete project {seq}",
                estimated_effort_minutes=120,
                required_concepts=(f"concept-{seq}",),
                unverified_concepts=(),
                status=MilestoneStatus.APPROVED,
                created_at=now,
                updated_at=now,
            )
        )

    avail = AvailabilityConfigurationDTO(
        mode="MODE_A",
        default_daily_quota_minutes=120,
        disabled_weekdays=(),
    )
    return user_id, goal, roadmap, milestones, avail


def _make_valid_milestone_payload(milestone: Milestone, resource_id: str) -> dict[str, Any]:
    seq = milestone.sequence_order
    return {
        "tasks": [
            {
                "task_id": f"M{seq}_T1",
                "milestone_id": str(milestone.id),
                "title": f"Lý thuyết cốt lõi cột mốc {seq}",
                "description": f"Đọc tài liệu và nắm vững khái niệm cột mốc {seq}",
                "task_type": "THEORY",
                "learning_objective": f"Hiểu rõ nền tảng cột mốc {seq}",
                "completion_criteria": f"Tóm tắt được nguyên lý cột mốc {seq}",
                "concept_ids": [f"concept-{seq}"],
                "covered_outcome_ids": [f"M{seq}-O1"],
                "resource_ids": [resource_id],
                "estimated_minutes": 60,
            },
            {
                "task_id": f"M{seq}_T2",
                "milestone_id": str(milestone.id),
                "title": f"Thực hành bài tập cột mốc {seq}",
                "description": f"Xây dựng bài tập thực tế áp dụng cột mốc {seq}",
                "task_type": "PRACTICE",
                "learning_objective": f"Vận dụng thành thạo cột mốc {seq}",
                "completion_criteria": f"Chạy xanh toàn bộ unit test cột mốc {seq}",
                "concept_ids": [f"concept-{seq}"],
                "covered_outcome_ids": [f"M{seq}-O1"],
                "resource_ids": [resource_id],
                "estimated_minutes": 60,
            },
        ],
        "dependencies": [
            {
                "predecessor_id": f"M{seq}_T1",
                "successor_id": f"M{seq}_T2",
                "is_mandatory": True,
            }
        ],
    }


def _extract_target_milestone(
    user_prompt: str, milestones: Sequence[Milestone]
) -> Milestone | None:
    for m in milestones:
        if f"MILESTONE_IDS: [{m.id}]" in user_prompt:
            return m
    return None


class _DeterministicMilestoneLLM:
    """Stub LLM that simulates latency, tracks peak concurrency, and can fail specific milestones."""

    model_identifier = "stub-deterministic-phase5"

    def __init__(
        self,
        *,
        milestones: Sequence[Milestone],
        resource_id: str,
        delay_seconds: float = 0.0,
        timeout_milestone_sequences: set[int] | None = None,
    ) -> None:
        self._milestones = list(milestones)
        self._resource_id = resource_id
        self._delay_seconds = delay_seconds
        self.timeout_milestone_sequences: set[int] = set(timeout_milestone_sequences or ())
        self.active_calls = 0
        self.peak_concurrent_calls = 0
        self.called_sequences: list[int] = []

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
        # Handle quality critic calls immediately as PASS
        if (
            "[INDEPENDENT_CRITIC:" in system_prompt
            or "[INDEPENDENT_CRITIC:" in user_prompt
            or "QUALITY_CRITIC" in system_prompt
        ):
            return LLMGenerationResult(
                payload={"verdict": "PASS", "issues": []},
                prompt_tokens=10,
                output_tokens=10,
                thinking_tokens=0,
                model_id=self.model_identifier,
            )

        milestone = _extract_target_milestone(user_prompt, self._milestones)
        assert milestone is not None, "Could not identify target milestone from prompt"

        self.active_calls += 1
        self.peak_concurrent_calls = max(self.peak_concurrent_calls, self.active_calls)
        self.called_sequences.append(milestone.sequence_order)
        try:
            if self._delay_seconds > 0:
                await asyncio.sleep(self._delay_seconds)
            if milestone.sequence_order in self.timeout_milestone_sequences:
                raise TimeoutError(f"Simulated gateway timeout on M{milestone.sequence_order}")
            return LLMGenerationResult(
                payload=_make_valid_milestone_payload(milestone, self._resource_id),
                prompt_tokens=100,
                output_tokens=80,
                thinking_tokens=0,
                model_id=self.model_identifier,
            )
        finally:
            self.active_calls -= 1


# ---------------------------------------------------------------------------
# 1. True 1-Wave Concurrency Tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("milestone_count", "ceiling", "expected"),
    [
        (0, 4, 0),
        (1, 4, 1),
        (2, 4, 2),
        (3, 4, 3),
        (4, 4, 4),
        (6, 4, 4),
        (4, 2, 2),
    ],
)
def test_calculate_dynamic_subjob_concurrency_runs_1_to_4_milestones_in_single_wave(
    milestone_count: int,
    ceiling: int,
    expected: int,
) -> None:
    assert calculate_dynamic_subjob_concurrency(milestone_count, ceiling=ceiling) == expected


@pytest.mark.asyncio
async def test_four_milestones_execute_in_single_parallel_wave() -> None:
    user_id, goal, roadmap, milestones, avail = _make_four_milestone_fixture()
    res = LearningResource(
        resource_id=compute_deterministic_resource_id(
            url="https://docs.python.org/3/", title="Python Docs"
        ),
        title="Python Docs",
        url="https://docs.python.org/3/",
        type="DOCS",
        description="Official docs",
    )
    single_delay = 0.15
    llm = _DeterministicMilestoneLLM(
        milestones=milestones,
        resource_id=res.resource_id,
        delay_seconds=single_delay,
    )
    decomposer = MilestoneScopedTaskDecomposer(
        llm_provider=llm,
        knowledge_base=_FakeKnowledgeBasePort([res]),
        enable_tier3_judge=False,
        user_id=user_id,
        goal_id=goal.id,
        roadmap_id=roadmap.id,
        max_concurrency=4,
    )

    t0 = time.monotonic()
    result = await decomposer.decompose_and_validate(
        goal=goal,
        roadmap=roadmap,
        milestones=milestones,
        availability=avail,
        learner_profile=LearnerProfileDTO(
            user_id=user_id,
            opt_session_minutes=60,
            estimation_bias_beta=1.0,
            peak_productivity_slots={},
        ),
        reference_date=date(2026, 6, 1),
    )
    elapsed = time.monotonic() - t0

    assert llm.peak_concurrent_calls == 4
    # Must complete in ~1x single-milestone latency (not 2x wave starvation = 0.30s+)
    assert elapsed < single_delay * 1.8, (
        f"Expected 1-wave execution (< {single_delay * 1.8:.2f}s), took {elapsed:.2f}s"
    )
    assert len(result.validated_proposal_data["tasks"]) == 8


# ---------------------------------------------------------------------------
# 2. Bounded External Prefetch Latency Test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_prefetch_url_verification_runs_concurrently_and_caps_slow_probes() -> None:
    user_id, goal, roadmap, milestones, _ = _make_four_milestone_fixture()
    m1 = milestones[0]
    candidates = [
        LearningResource(
            resource_id=f"res-{i}",
            title=f"Resource {i}",
            url=f"https://example.org/doc-{i}",
            type="DOCS",
            description=f"Doc {i}",
        )
        for i in range(6)
    ]

    async def _slow_or_fast_probe(url: str) -> bool:
        if url.endswith("doc-0") or url.endswith("doc-1"):
            await asyncio.sleep(0.01)
            return True
        # Remaining 4 probes hang for 2.0s each (8s if sequential!)
        await asyncio.sleep(2.0)
        return True

    decomposer = MilestoneScopedTaskDecomposer(
        llm_provider=_DeterministicMilestoneLLM(milestones=[m1], resource_id="res-0"),
        knowledge_base=_FakeKnowledgeBasePort([]),
        enable_tier3_judge=False,
        user_id=user_id,
        goal_id=goal.id,
        roadmap_id=roadmap.id,
        max_concurrency=4,
        url_verify_timeout_seconds=0.15,
    )

    with (
        patch(
            "src.planning.application.services.milestone_scoped_decomposer.discover_curated_official_resources",
            return_value=candidates,
        ),
        patch(
            "src.planning.application.services.milestone_scoped_decomposer.verify_official_url_live",
            side_effect=_slow_or_fast_probe,
        ),
    ):
        t0 = time.monotonic()
        prefetched = await decomposer._prefetch_resources_for_milestones([m1])
        elapsed = time.monotonic() - t0

    assert elapsed < 0.45, f"Prefetch should be bounded by timeout, took {elapsed:.2f}s"
    returned_ids = {r.resource_id for r in prefetched[m1.id]}
    assert returned_ids == {"res-0", "res-1"}


# ---------------------------------------------------------------------------
# 3. Timeout Before First Response -> Releases Quota & Emits resumable=False
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_timeout_before_first_response_releases_quota_and_emits_non_resumable() -> None:
    user_id, goal, roadmap, milestones, avail = _make_four_milestone_fixture()
    res = LearningResource(
        resource_id=compute_deterministic_resource_id(
            url="https://docs.python.org/3/", title="Python Docs"
        ),
        title="Python Docs",
        url="https://docs.python.org/3/",
        type="DOCS",
        description="Official docs",
    )
    llm = _DeterministicMilestoneLLM(
        milestones=milestones,
        resource_id=res.resource_id,
        timeout_milestone_sequences={1, 2, 3, 4},
    )
    quota_facade = _RecordingQuotaFacade()
    sse_store = InMemorySseJobStore()
    checkpoint_store = InMemoryMilestoneCheckpointStore(durable=True)
    job_id = generate_uuid7()
    reservation_id = generate_uuid7()
    await sse_store.create_job(
        job_id=job_id,
        user_id=user_id,
        roadmap_id=roadmap.id,
        reservation_id=reservation_id,
        job_type="SCHEDULE_PROPOSAL_GEN",
        operation=f"SCHEDULE_PROPOSAL_GEN:{roadmap.id}",
    )

    uc = ExecuteScheduleProposalGenerationUseCase(
        goal_repo=_FakeGoalRepo(goal),
        roadmap_repo=_FakeRoadmapRepo(roadmap),
        milestone_repo=_FakeMilestoneRepo(milestones),
        proposal_repo=_FakeProposalRepo(),
        availability_query_port=_FakeAvailabilityPort(avail),
        learner_profile_port=_FakeLearnerProfilePort(user_id),
        execution_sync_port=_FakeExecSyncPort(),
        quota_facade=quota_facade,
        llm_provider=llm,
        sse_job_store=sse_store,
        uow=_FakeUoW(),
        enable_tier3_judge=False,
        knowledge_base=_FakeKnowledgeBasePort([res]),
        user_query_port=_FakeUserQueryPort(user_id),
        checkpoint_store=checkpoint_store,
    )

    with pytest.raises(MilestoneDecompositionTimeoutError) as exc_info:
        await uc.execute(
            job_id=job_id,
            user_id=user_id,
            roadmap_id=roadmap.id,
            reservation_id=reservation_id,
            decomposer_architecture_mode="milestone_scoped",
        )

    assert exc_info.value.completed_milestones == 0
    assert exc_info.value.total_milestones == 4
    assert exc_info.value.resumable is False

    # Quota cleanly released, never committed
    assert quota_facade.committed == []
    assert quota_facade.released == [(reservation_id, "AI_GATEWAY_TIMEOUT")]

    job = await sse_store.get_job_for_user(job_id=job_id, user_id=user_id)
    assert job is not None
    failed_events = [e for e in job.events if e.event == "failed"]
    assert len(failed_events) == 1
    data = failed_events[0].data
    assert data["error_code"] == "AI_GATEWAY_TIMEOUT"
    assert data["completed_milestones"] == 0
    assert data["total_milestones"] == 4
    assert data["resumable"] is False


# ---------------------------------------------------------------------------
# 4. Partial Progress Timeout (M1-M3 cached, M4 timeout) & Seamless Retry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_partial_timeout_caches_m1_m3_and_retry_resumes_only_m4_with_zero_duplicates() -> (
    None
):
    user_id, goal, roadmap, milestones, avail = _make_four_milestone_fixture()
    res = LearningResource(
        resource_id=compute_deterministic_resource_id(
            url="https://docs.python.org/3/", title="Python Docs"
        ),
        title="Python Docs",
        url="https://docs.python.org/3/",
        type="DOCS",
        description="Official docs",
    )
    llm = _DeterministicMilestoneLLM(
        milestones=milestones,
        resource_id=res.resource_id,
        timeout_milestone_sequences={4},
    )
    quota_facade = _RecordingQuotaFacade()
    proposal_repo = _FakeProposalRepo()
    sse_store = InMemorySseJobStore()
    checkpoint_store = InMemoryMilestoneCheckpointStore(durable=True)

    # --- Run 1: M1-M3 succeed and are saved to checkpoint_store, M4 times out ---
    job_id_1 = generate_uuid7()
    reservation_id_1 = generate_uuid7()
    await sse_store.create_job(
        job_id=job_id_1,
        user_id=user_id,
        roadmap_id=roadmap.id,
        reservation_id=reservation_id_1,
        job_type="SCHEDULE_PROPOSAL_GEN",
        operation=f"SCHEDULE_PROPOSAL_GEN:{roadmap.id}",
    )

    uc = ExecuteScheduleProposalGenerationUseCase(
        goal_repo=_FakeGoalRepo(goal),
        roadmap_repo=_FakeRoadmapRepo(roadmap),
        milestone_repo=_FakeMilestoneRepo(milestones),
        proposal_repo=proposal_repo,
        availability_query_port=_FakeAvailabilityPort(avail),
        learner_profile_port=_FakeLearnerProfilePort(user_id),
        execution_sync_port=_FakeExecSyncPort(),
        quota_facade=quota_facade,
        llm_provider=llm,
        sse_job_store=sse_store,
        uow=_FakeUoW(),
        enable_tier3_judge=False,
        knowledge_base=_FakeKnowledgeBasePort([res]),
        user_query_port=_FakeUserQueryPort(user_id),
        checkpoint_store=checkpoint_store,
    )

    with pytest.raises(MilestoneDecompositionTimeoutError) as exc_info:
        await uc.execute(
            job_id=job_id_1,
            user_id=user_id,
            roadmap_id=roadmap.id,
            reservation_id=reservation_id_1,
            decomposer_architecture_mode="milestone_scoped",
        )

    assert exc_info.value.completed_milestones == 3
    assert exc_info.value.total_milestones == 4
    assert exc_info.value.resumable is True
    assert exc_info.value.failed_milestone_sequence == 4

    # Quota released cleanly for Run 1, never committed
    assert quota_facade.committed == []
    assert quota_facade.released == [(reservation_id_1, "AI_GATEWAY_TIMEOUT")]

    job_1 = await sse_store.get_job_for_user(job_id=job_id_1, user_id=user_id)
    assert job_1 is not None
    failed_events = [e for e in job_1.events if e.event == "failed"]
    assert len(failed_events) == 1
    assert failed_events[0].data["error_code"] == "AI_GATEWAY_TIMEOUT"
    assert failed_events[0].data["completed_milestones"] == 3
    assert failed_events[0].data["total_milestones"] == 4
    assert failed_events[0].data["resumable"] is True

    # --- Run 2 (Retry): M4 succeeds, M1-M3 served from checkpoint store ---
    llm.called_sequences.clear()
    llm.timeout_milestone_sequences.clear()

    job_id_2 = generate_uuid7()
    reservation_id_2 = generate_uuid7()
    await sse_store.create_job(
        job_id=job_id_2,
        user_id=user_id,
        roadmap_id=roadmap.id,
        reservation_id=reservation_id_2,
        job_type="SCHEDULE_PROPOSAL_GEN",
        operation=f"SCHEDULE_PROPOSAL_GEN:{roadmap.id}",
    )

    saved_proposal = await uc.execute(
        job_id=job_id_2,
        user_id=user_id,
        roadmap_id=roadmap.id,
        reservation_id=reservation_id_2,
        decomposer_architecture_mode="milestone_scoped",
    )

    # ONLY M4 invoked LLM on retry! M1-M3 hit Redis/in-memory checkpoint store
    assert llm.called_sequences == [4]

    # Quota committed ONCE (for Run 2 only); Run 1 remained released
    assert len(quota_facade.committed) == 1
    assert quota_facade.committed[0][0] == reservation_id_2
    assert quota_facade.released == [(reservation_id_1, "AI_GATEWAY_TIMEOUT")]

    # Proposal has exact 4 milestones' tasks (2 tasks each = 8 tasks), zero duplicates
    assert saved_proposal.status == ScheduleProposalStatus.DRAFT
    tasks = saved_proposal.proposal_data["tasks"]
    assert len(tasks) == 8
    milestone_counts: dict[str, int] = {}
    for task in tasks:
        mid = str(task["milestone_id"])
        milestone_counts[mid] = milestone_counts.get(mid, 0) + 1
    assert set(milestone_counts.keys()) == {str(m.id) for m in milestones}
    assert all(count == 2 for count in milestone_counts.values())

    # Progress events on Run 2 confirm 3 checkpoint hits + 1 fresh AI completion
    job_2 = await sse_store.get_job_for_user(job_id=job_id_2, user_id=user_id)
    assert job_2 is not None
    progress_events = [e for e in job_2.events if isinstance(e.data.get("milestone_sequence"), int)]
    assert len(progress_events) == 4
    checkpoint_seqs = {
        e.data["milestone_sequence"] for e in progress_events if e.data["from_checkpoint"] is True
    }
    fresh_seqs = {
        e.data["milestone_sequence"] for e in progress_events if e.data["from_checkpoint"] is False
    }
    assert checkpoint_seqs == {1, 2, 3}
    assert fresh_seqs == {4}


# ---------------------------------------------------------------------------
# 5. Duplicate Job Submission / Idempotency Verification
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_duplicate_job_submission_is_idempotent_and_reserves_quota_once() -> None:
    user_id, goal, roadmap, milestones, avail = _make_four_milestone_fixture()
    quota_facade = _RecordingQuotaFacade()
    sse_store = InMemorySseJobStore()

    initiator = InitiateScheduleProposalGenerationUseCase(
        roadmap_repo=_FakeRoadmapRepo(roadmap),
        milestone_repo=_FakeMilestoneRepo(milestones),
        quota_facade=quota_facade,
        sse_job_store=sse_store,
        uow=_FakeUoW(),
        goal_repo=_FakeGoalRepo(goal),
        proposal_repo=_FakeProposalRepo(),
        availability_query_port=_FakeAvailabilityPort(avail),
        execution_sync_port=_FakeExecSyncPort(),
        user_query_port=_FakeUserQueryPort(user_id),
    )

    ticket_1 = await initiator.execute(
        user_id=user_id,
        roadmap_id=roadmap.id,
        idempotency_key="retry-proposal-key-001",
        run_inline=False,
    )
    ticket_2 = await initiator.execute(
        user_id=user_id,
        roadmap_id=roadmap.id,
        idempotency_key="retry-proposal-key-001",
        run_inline=False,
    )

    assert ticket_1.is_existing is False
    assert ticket_2.is_existing is True
    assert ticket_2.job_id == ticket_1.job_id
    assert ticket_2.reservation_id == ticket_1.reservation_id
    assert len(quota_facade.reserved) == 1


# ---------------------------------------------------------------------------
# 6. Phase 0 P1B Follow-up Regression Tests:
#    - Durable vs. Degraded Redis Checkpoint resumable accuracy
#    - Read-TX rollback before long LLM decomposition
# ---------------------------------------------------------------------------


class _FailingRedisClient:
    """Fake Redis client that raises ConnectionError on every get/set."""

    async def get(self, key: str) -> str | None:
        raise ConnectionError("Redis unavailable (get)")

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        raise ConnectionError("Redis unavailable (set)")

    async def aclose(self) -> None:
        return None


class _HealthyFakeRedisClient:
    """Fake healthy Redis client backed by an in-process dict for testing durable writes."""

    def __init__(self) -> None:
        self.data: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.data.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.data[key] = value

    async def aclose(self) -> None:
        return None


@pytest.mark.asyncio
async def test_redis_checkpoint_degraded_to_memory_fallback_emits_resumable_false() -> None:
    user_id, goal, roadmap, milestones, avail = _make_four_milestone_fixture()
    res = LearningResource(
        resource_id=compute_deterministic_resource_id(
            url="https://docs.python.org/3/", title="Python Docs"
        ),
        title="Python Docs",
        url="https://docs.python.org/3/",
        type="DOCS",
        description="Official docs",
    )
    llm = _DeterministicMilestoneLLM(
        milestones=milestones,
        resource_id=res.resource_id,
        timeout_milestone_sequences={4},
    )
    quota_facade = _RecordingQuotaFacade()
    sse_store = InMemorySseJobStore()
    checkpoint_store = RedisMilestoneCheckpointStore(redis_client=_FailingRedisClient())

    job_id = generate_uuid7()
    reservation_id = generate_uuid7()
    await sse_store.create_job(
        job_id=job_id,
        user_id=user_id,
        roadmap_id=roadmap.id,
        reservation_id=reservation_id,
        job_type="SCHEDULE_PROPOSAL_GEN",
        operation=f"SCHEDULE_PROPOSAL_GEN:{roadmap.id}",
    )

    uc = ExecuteScheduleProposalGenerationUseCase(
        goal_repo=_FakeGoalRepo(goal),
        roadmap_repo=_FakeRoadmapRepo(roadmap),
        milestone_repo=_FakeMilestoneRepo(milestones),
        proposal_repo=_FakeProposalRepo(),
        availability_query_port=_FakeAvailabilityPort(avail),
        learner_profile_port=_FakeLearnerProfilePort(user_id),
        execution_sync_port=_FakeExecSyncPort(),
        quota_facade=quota_facade,
        llm_provider=llm,
        sse_job_store=sse_store,
        uow=_FakeUoW(),
        enable_tier3_judge=False,
        knowledge_base=_FakeKnowledgeBasePort([res]),
        user_query_port=_FakeUserQueryPort(user_id),
        checkpoint_store=checkpoint_store,
    )

    with pytest.raises(MilestoneDecompositionTimeoutError) as exc_info:
        await uc.execute(
            job_id=job_id,
            user_id=user_id,
            roadmap_id=roadmap.id,
            reservation_id=reservation_id,
            decomposer_architecture_mode="milestone_scoped",
        )

    assert exc_info.value.completed_milestones == 3
    assert exc_info.value.total_milestones == 4
    assert checkpoint_store.is_durable is False
    assert exc_info.value.resumable is False

    job = await sse_store.get_job_for_user(job_id=job_id, user_id=user_id)
    assert job is not None
    failed_events = [e for e in job.events if e.event == "failed"]
    assert len(failed_events) == 1
    assert failed_events[0].data["error_code"] == "AI_GATEWAY_TIMEOUT"
    assert failed_events[0].data["completed_milestones"] == 3
    assert failed_events[0].data["total_milestones"] == 4
    assert failed_events[0].data["resumable"] is False


@pytest.mark.asyncio
async def test_redis_checkpoint_healthy_emits_resumable_true() -> None:
    user_id, goal, roadmap, milestones, avail = _make_four_milestone_fixture()
    res = LearningResource(
        resource_id=compute_deterministic_resource_id(
            url="https://docs.python.org/3/", title="Python Docs"
        ),
        title="Python Docs",
        url="https://docs.python.org/3/",
        type="DOCS",
        description="Official docs",
    )
    llm = _DeterministicMilestoneLLM(
        milestones=milestones,
        resource_id=res.resource_id,
        timeout_milestone_sequences={4},
    )
    quota_facade = _RecordingQuotaFacade()
    sse_store = InMemorySseJobStore()
    fake_redis = _HealthyFakeRedisClient()
    checkpoint_store = RedisMilestoneCheckpointStore(redis_client=fake_redis)

    job_id = generate_uuid7()
    reservation_id = generate_uuid7()
    await sse_store.create_job(
        job_id=job_id,
        user_id=user_id,
        roadmap_id=roadmap.id,
        reservation_id=reservation_id,
        job_type="SCHEDULE_PROPOSAL_GEN",
        operation=f"SCHEDULE_PROPOSAL_GEN:{roadmap.id}",
    )

    uc = ExecuteScheduleProposalGenerationUseCase(
        goal_repo=_FakeGoalRepo(goal),
        roadmap_repo=_FakeRoadmapRepo(roadmap),
        milestone_repo=_FakeMilestoneRepo(milestones),
        proposal_repo=_FakeProposalRepo(),
        availability_query_port=_FakeAvailabilityPort(avail),
        learner_profile_port=_FakeLearnerProfilePort(user_id),
        execution_sync_port=_FakeExecSyncPort(),
        quota_facade=quota_facade,
        llm_provider=llm,
        sse_job_store=sse_store,
        uow=_FakeUoW(),
        enable_tier3_judge=False,
        knowledge_base=_FakeKnowledgeBasePort([res]),
        user_query_port=_FakeUserQueryPort(user_id),
        checkpoint_store=checkpoint_store,
    )

    with pytest.raises(MilestoneDecompositionTimeoutError) as exc_info:
        await uc.execute(
            job_id=job_id,
            user_id=user_id,
            roadmap_id=roadmap.id,
            reservation_id=reservation_id,
            decomposer_architecture_mode="milestone_scoped",
        )

    assert exc_info.value.completed_milestones == 3
    assert exc_info.value.total_milestones == 4
    assert len(fake_redis.data) == 3
    assert checkpoint_store.is_durable is True
    assert exc_info.value.resumable is True

    job = await sse_store.get_job_for_user(job_id=job_id, user_id=user_id)
    assert job is not None
    failed_events = [e for e in job.events if e.event == "failed"]
    assert len(failed_events) == 1
    assert failed_events[0].data["resumable"] is True


@pytest.mark.asyncio
async def test_ephemeral_in_memory_checkpoint_store_emits_resumable_false() -> None:
    user_id, goal, roadmap, milestones, avail = _make_four_milestone_fixture()
    res = LearningResource(
        resource_id=compute_deterministic_resource_id(
            url="https://docs.python.org/3/", title="Python Docs"
        ),
        title="Python Docs",
        url="https://docs.python.org/3/",
        type="DOCS",
        description="Official docs",
    )
    llm = _DeterministicMilestoneLLM(
        milestones=milestones,
        resource_id=res.resource_id,
        timeout_milestone_sequences={4},
    )
    sse_store = InMemorySseJobStore()
    checkpoint_store = InMemoryMilestoneCheckpointStore()
    assert checkpoint_store.is_durable is False

    job_id = generate_uuid7()
    reservation_id = generate_uuid7()
    await sse_store.create_job(
        job_id=job_id,
        user_id=user_id,
        roadmap_id=roadmap.id,
        reservation_id=reservation_id,
        job_type="SCHEDULE_PROPOSAL_GEN",
        operation=f"SCHEDULE_PROPOSAL_GEN:{roadmap.id}",
    )

    uc = ExecuteScheduleProposalGenerationUseCase(
        goal_repo=_FakeGoalRepo(goal),
        roadmap_repo=_FakeRoadmapRepo(roadmap),
        milestone_repo=_FakeMilestoneRepo(milestones),
        proposal_repo=_FakeProposalRepo(),
        availability_query_port=_FakeAvailabilityPort(avail),
        learner_profile_port=_FakeLearnerProfilePort(user_id),
        execution_sync_port=_FakeExecSyncPort(),
        quota_facade=_RecordingQuotaFacade(),
        llm_provider=llm,
        sse_job_store=sse_store,
        uow=_FakeUoW(),
        enable_tier3_judge=False,
        knowledge_base=_FakeKnowledgeBasePort([res]),
        user_query_port=_FakeUserQueryPort(user_id),
        checkpoint_store=checkpoint_store,
    )

    with pytest.raises(MilestoneDecompositionTimeoutError) as exc_info:
        await uc.execute(
            job_id=job_id,
            user_id=user_id,
            roadmap_id=roadmap.id,
            reservation_id=reservation_id,
            decomposer_architecture_mode="milestone_scoped",
        )

    assert exc_info.value.completed_milestones == 3
    assert exc_info.value.resumable is False
    job = await sse_store.get_job_for_user(job_id=job_id, user_id=user_id)
    assert job is not None
    failed_events = [e for e in job.events if e.event == "failed"]
    assert len(failed_events) == 1
    assert failed_events[0].data["resumable"] is False


@pytest.mark.asyncio
async def test_execute_proposal_generation_releases_read_tx_before_llm_decomposition() -> None:
    user_id, goal, roadmap, milestones, avail = _make_four_milestone_fixture()
    res = LearningResource(
        resource_id=compute_deterministic_resource_id(
            url="https://docs.python.org/3/", title="Python Docs"
        ),
        title="Python Docs",
        url="https://docs.python.org/3/",
        type="DOCS",
        description="Official docs",
    )
    events_log: list[str] = []

    class _TracingUoW(_FakeUoW):
        async def rollback(self) -> None:
            events_log.append("uow_rollback")
            await super().rollback()

        async def commit(self) -> None:
            events_log.append("uow_commit")
            await super().commit()

    class _TracingLLM(_DeterministicMilestoneLLM):
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
            events_log.append("llm_call")
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

    uow = _TracingUoW()
    llm = _TracingLLM(milestones=milestones, resource_id=res.resource_id)
    sse_store = InMemorySseJobStore()
    job_id = generate_uuid7()
    reservation_id = generate_uuid7()
    await sse_store.create_job(
        job_id=job_id,
        user_id=user_id,
        roadmap_id=roadmap.id,
        reservation_id=reservation_id,
        job_type="SCHEDULE_PROPOSAL_GEN",
        operation=f"SCHEDULE_PROPOSAL_GEN:{roadmap.id}",
    )

    uc = ExecuteScheduleProposalGenerationUseCase(
        goal_repo=_FakeGoalRepo(goal),
        roadmap_repo=_FakeRoadmapRepo(roadmap),
        milestone_repo=_FakeMilestoneRepo(milestones),
        proposal_repo=_FakeProposalRepo(),
        availability_query_port=_FakeAvailabilityPort(avail),
        learner_profile_port=_FakeLearnerProfilePort(user_id),
        execution_sync_port=_FakeExecSyncPort(),
        quota_facade=_RecordingQuotaFacade(),
        llm_provider=llm,
        sse_job_store=sse_store,
        uow=uow,
        enable_tier3_judge=False,
        knowledge_base=_FakeKnowledgeBasePort([res]),
        user_query_port=_FakeUserQueryPort(user_id),
        checkpoint_store=InMemoryMilestoneCheckpointStore(),
    )

    await uc.execute(
        job_id=job_id,
        user_id=user_id,
        roadmap_id=roadmap.id,
        reservation_id=reservation_id,
        decomposer_architecture_mode="milestone_scoped",
    )

    assert "uow_rollback" in events_log
    assert "llm_call" in events_log
    assert events_log.index("uow_rollback") < events_log.index("llm_call")
    assert events_log[-1] == "uow_commit"
