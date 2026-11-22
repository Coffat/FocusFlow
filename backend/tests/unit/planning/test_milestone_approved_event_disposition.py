"""Unit tests for Phase 4 (`MilestoneApprovedEvent` outbox disposition) and
read-transaction release before LLM inference in `ExecuteMilestoneGenerationUseCase`.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

import pytest

from src.account.public_api import AvailabilitySnapshotDTO
from src.execution.public_api import ExistingScheduledTaskDTO
from src.planning.application.use_cases.milestone_use_cases import (
    ApproveMilestonesUseCase,
    ExecuteMilestoneGenerationUseCase,
)
from src.planning.application.use_cases.proposal_management_use_cases import (
    SaveManualRoadmapPlanUseCase,
)
from src.planning.domain.events import MilestoneApprovedEvent as ReexportedMilestoneApprovedEvent
from src.planning.domain.events.planning_events import MilestoneApprovedEvent
from src.planning.domain.models.goal import Goal
from src.planning.domain.models.milestone import Milestone, MilestoneStatus
from src.planning.domain.models.roadmap import Roadmap, RoadmapStatus
from src.planning.domain.models.schedule import ScheduleProposal, ScheduleProposalStatus
from src.planning.domain.services.milestone_effort_allocator import MilestoneEffortAllocator
from src.shared_kernel.application.llm_port import LLMGenerationResult
from src.shared_kernel.domain.base import AggregateRoot, generate_uuid7
from src.shared_kernel.domain.events import DomainEvent


class _SpyUnitOfWork:
    """In-memory UoW spy tracking collected domain events, commits, and rollbacks."""

    def __init__(self, call_log: list[str] | None = None) -> None:
        self.collected_events: list[DomainEvent] = []
        self.commit_count: int = 0
        self.rollback_count: int = 0
        self._call_log = call_log

    async def __aenter__(self) -> _SpyUnitOfWork:
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_type is not None:
            await self.rollback()

    def collect_events_from(self, aggregate: AggregateRoot) -> None:
        self.collected_events.extend(aggregate.pull_domain_events())

    async def commit(self) -> None:
        self.commit_count += 1
        if self._call_log is not None:
            self._call_log.append("commit")

    async def rollback(self) -> None:
        self.rollback_count += 1
        if self._call_log is not None:
            self._call_log.append("rollback")


class _InMemoryGoalRepo:
    def __init__(self, goals: list[Goal] | None = None) -> None:
        self._store: dict[UUID, Goal] = {g.id: g for g in (goals or [])}

    async def get_by_id(self, goal_id: UUID) -> Goal | None:
        return self._store.get(goal_id)


class _InMemoryRoadmapRepo:
    def __init__(self, roadmaps: list[Roadmap] | None = None) -> None:
        self._store: dict[UUID, Roadmap] = {r.id: r for r in (roadmaps or [])}

    async def get_by_id_for_user(
        self, roadmap_id: UUID, user_id: UUID, *, for_update: bool = False
    ) -> Roadmap | None:
        del for_update
        rm = self._store.get(roadmap_id)
        if rm is None or rm.user_id != user_id:
            return None
        return rm

    async def list_by_user_id(
        self,
        user_id: UUID,
        status: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> Sequence[Roadmap]:
        items = [r for r in self._store.values() if r.user_id == user_id]
        if status is not None:
            items = [r for r in items if r.status.value == status]
        return items[offset : offset + limit]

    async def save(self, roadmap: Roadmap) -> Roadmap:
        self._store[roadmap.id] = roadmap
        return roadmap


class _InMemoryMilestoneRepo:
    def __init__(self, milestones: list[Milestone] | None = None) -> None:
        self._by_roadmap: dict[UUID, list[Milestone]] = {}
        for m in milestones or []:
            self._by_roadmap.setdefault(m.roadmap_id, []).append(m)

    async def list_by_roadmap_id(self, roadmap_id: UUID) -> list[Milestone]:
        return sorted(
            list(self._by_roadmap.get(roadmap_id, [])),
            key=lambda m: m.sequence_order,
        )

    async def save_many(self, roadmap_id: UUID, milestones: Sequence[Milestone]) -> list[Milestone]:
        saved = list(milestones)
        self._by_roadmap[roadmap_id] = saved
        return saved

    async def approve_all_for_roadmap(self, roadmap_id: UUID, now: datetime) -> list[Milestone]:
        items = list(self._by_roadmap.get(roadmap_id, []))
        for m in items:
            m.approve(now)
        self._by_roadmap[roadmap_id] = items
        return items


class _InMemoryProposalRepo:
    def __init__(self) -> None:
        self.proposals: dict[UUID, ScheduleProposal] = {}
        self.discarded_roadmaps: list[UUID] = []

    async def discard_existing_drafts(self, roadmap_id: UUID, now: datetime) -> int:
        del now
        self.discarded_roadmaps.append(roadmap_id)
        return 0

    async def save(self, proposal: ScheduleProposal) -> ScheduleProposal:
        self.proposals[proposal.id] = proposal
        return proposal


class _FakeAvailabilityPort:
    def __init__(self, snapshot: AvailabilitySnapshotDTO) -> None:
        self._snapshot = snapshot

    async def get_active_availability(self, user_id: UUID) -> AvailabilitySnapshotDTO:
        del user_id
        return self._snapshot


class _FakeExecutionSyncPort:
    async def get_tasks_for_roadmaps(
        self,
        roadmap_ids: Sequence[UUID],
        *,
        roadmap_target_dates: dict[UUID, date | None] | None = None,
    ) -> Sequence[ExistingScheduledTaskDTO]:
        del roadmap_ids, roadmap_target_dates
        return ()


class _FakeQuotaFacade:
    def __init__(self) -> None:
        self.committed: list[UUID] = []
        self.released: list[UUID] = []

    async def commit_reservation(
        self,
        reservation_id: UUID,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        model_name: str = "",
        thinking_tokens: int = 0,
    ) -> None:
        del prompt_tokens, completion_tokens, model_name, thinking_tokens
        self.committed.append(reservation_id)

    async def release_reservation(self, reservation_id: UUID, reason: str = "RELEASED") -> None:
        del reason
        self.released.append(reservation_id)

    async def record_attempt_usage(self, **kwargs: Any) -> None:
        del kwargs


class _FakeSseJobStore:
    def __init__(self) -> None:
        self.events: list[tuple[UUID, str, str, dict[str, Any]]] = []

    async def append_event(
        self,
        *,
        job_id: UUID,
        event: str,
        status: str,
        data: dict[str, Any],
    ) -> None:
        self.events.append((job_id, event, status, data))


class _SpyLLMProvider:
    model_identifier = "gemini-3.8-flash-stub"

    def __init__(self, payload: dict[str, Any], call_log: list[str]) -> None:
        self._payload = payload
        self._call_log = call_log

    async def generate_structured(self, **kwargs: Any) -> LLMGenerationResult:
        del kwargs
        self._call_log.append("llm_call")
        return LLMGenerationResult(
            payload=self._payload,
            prompt_tokens=100,
            output_tokens=150,
            thinking_tokens=0,
            model_id=self.model_identifier,
        )


def _make_milestone(
    roadmap_id: UUID,
    seq: int,
    *,
    now: datetime,
    status: MilestoneStatus = MilestoneStatus.PENDING,
) -> Milestone:
    return Milestone(
        id=generate_uuid7(),
        roadmap_id=roadmap_id,
        sequence_order=seq,
        title=f"Chặng {seq}: Nội dung học tập {seq}",
        description=f"Mô tả chặng {seq}",
        learning_outcomes=(f"Hoàn thành mục tiêu chặng {seq}",),
        completion_criteria=f"Đạt bài kiểm tra chặng {seq}",
        estimated_effort_minutes=120,
        status=status,
        created_at=now,
        updated_at=now,
    )


def test_milestone_approved_event_preserved_for_import_compatibility() -> None:
    assert MilestoneApprovedEvent is ReexportedMilestoneApprovedEvent
    assert MilestoneApprovedEvent.__doc__ is not None
    assert "DEPRECATED" in MilestoneApprovedEvent.__doc__


@pytest.mark.asyncio
async def test_standard_milestone_approval_emits_zero_milestone_approved_events() -> None:
    now = datetime(2026, 6, 1, 10, 0, tzinfo=UTC)
    user_id = generate_uuid7()
    roadmap = Roadmap(
        id=generate_uuid7(),
        goal_id=generate_uuid7(),
        user_id=user_id,
        title="Backend Architecture",
        description="Learn backend systems",
        status=RoadmapStatus.ACTIVE,
        start_date=date(2026, 6, 1),
        target_date=date(2026, 7, 15),
        created_at=now,
        updated_at=now,
    )
    milestones = [
        _make_milestone(roadmap.id, 1, now=now),
        _make_milestone(roadmap.id, 2, now=now),
        _make_milestone(roadmap.id, 3, now=now),
    ]
    uow = _SpyUnitOfWork()
    uc = ApproveMilestonesUseCase(
        roadmap_repo=_InMemoryRoadmapRepo([roadmap]),  # type: ignore[arg-type]
        milestone_repo=_InMemoryMilestoneRepo(milestones),  # type: ignore[arg-type]
        uow=uow,  # type: ignore[arg-type]
    )

    approved = await uc.execute(user_id=user_id, roadmap_id=roadmap.id, now=now)

    assert len(approved) == 3
    assert all(m.status == MilestoneStatus.APPROVED for m in approved)
    assert uow.commit_count == 1
    assert uow.collected_events == []
    assert roadmap.pull_domain_events() == []


@pytest.mark.asyncio
async def test_fit_capacity_milestone_approval_emits_zero_milestone_approved_events() -> None:
    now = datetime(2026, 6, 1, 10, 0, tzinfo=UTC)
    user_id = generate_uuid7()
    roadmap_id = generate_uuid7()
    milestones = [
        _make_milestone(roadmap_id, 1, now=now),
        _make_milestone(roadmap_id, 2, now=now),
        _make_milestone(roadmap_id, 3, now=now),
    ]
    kept_scope = [
        {
            "sequence_order": m.sequence_order,
            "milestone_id": str(m.id),
            "title": m.title,
            "completion_criteria": m.completion_criteria or "",
            "normalized_planned_effort_minutes": m.estimated_effort_minutes,
            "expected_outcomes": list(m.learning_outcomes),
            "dependencies": [],
            "prerequisite_milestone_ids": [],
        }
        for m in milestones[:2]
    ]
    deferred_scope = [
        {
            "sequence_order": milestones[2].sequence_order,
            "milestone_id": str(milestones[2].id),
            "title": milestones[2].title,
            "completion_criteria": milestones[2].completion_criteria or "",
            "dependencies": [],
            "prerequisite_milestone_ids": [],
        }
    ]
    proposal_hash = MilestoneEffortAllocator._compute_proposal_hash(
        version=2,
        status="FIT_CAPACITY_REQUIRES_APPROVAL",
        kept_scope=kept_scope,
        deferred_scope=deferred_scope,
        hard_packable_capacity_minutes=240,
        target_date=date(2026, 6, 20),
    )
    roadmap = Roadmap(
        id=roadmap_id,
        goal_id=generate_uuid7(),
        user_id=user_id,
        title="System Design Intensive",
        description="Fit capacity scope approval",
        status=RoadmapStatus.ACTIVE,
        start_date=date(2026, 6, 1),
        target_date=date(2026, 6, 20),
        planning_metadata={
            "preliminary_feasibility": {
                "status": "FIT_CAPACITY_REQUIRES_APPROVAL",
                "requires_learner_approval": True,
                "scope_proposal_version": 2,
                "scope_proposal_hash": proposal_hash,
                "scope_approval_status": "PENDING_LEARNER_APPROVAL",
                "hard_packable_capacity_minutes": 240,
                "target_date": "2026-06-20",
                "kept_scope": kept_scope,
                "deferred_scope": deferred_scope,
            }
        },
        created_at=now,
        updated_at=now,
    )
    roadmap_repo = _InMemoryRoadmapRepo([roadmap])
    uow = _SpyUnitOfWork()
    uc = ApproveMilestonesUseCase(
        roadmap_repo=roadmap_repo,  # type: ignore[arg-type]
        milestone_repo=_InMemoryMilestoneRepo(milestones),  # type: ignore[arg-type]
        uow=uow,  # type: ignore[arg-type]
    )

    saved = await uc.execute(
        user_id=user_id,
        roadmap_id=roadmap.id,
        confirmed_scope_proposal_version=2,
        accept_fit_capacity=True,
        now=now,
    )

    assert [m.status for m in saved] == [
        MilestoneStatus.APPROVED,
        MilestoneStatus.APPROVED,
        MilestoneStatus.PENDING,
    ]
    stored_rm = await roadmap_repo.get_by_id_for_user(roadmap.id, user_id)
    assert stored_rm is not None
    prelim = stored_rm.planning_metadata["preliminary_feasibility"]
    assert prelim["scope_approval_status"] == "APPROVED_BY_LEARNER"
    assert prelim["approved_scope_version"] == 2
    assert uow.commit_count == 1
    assert uow.collected_events == []
    assert stored_rm.pull_domain_events() == []


@pytest.mark.asyncio
async def test_manual_proposal_save_emits_zero_milestone_approved_events() -> None:
    now = datetime(2026, 6, 1, 9, 0, tzinfo=UTC)  # Monday
    user_id = generate_uuid7()
    goal = Goal(
        id=generate_uuid7(),
        user_id=user_id,
        title="Manual Plan Goal",
        raw_description="Build a manual study plan",
        prior_knowledge_level="INTERMEDIATE",
        created_at=now,
        updated_at=now,
    )
    roadmap = Roadmap(
        id=generate_uuid7(),
        goal_id=goal.id,
        user_id=user_id,
        title="Manual Roadmap",
        description="Learner-authored plan",
        status=RoadmapStatus.ACTIVE,
        start_date=date(2026, 6, 1),
        target_date=date(2026, 6, 30),
        created_at=now,
        updated_at=now,
    )
    m1 = _make_milestone(roadmap.id, 1, now=now)
    availability = AvailabilitySnapshotDTO(
        user_id=user_id,
        mode="MODE_B",
        daily_cap_minutes=120,
        weekly_capacity_minutes=120,
        daily_quota_minutes={"monday": 120},
        availability_slots=(
            {
                "day_of_week": 0,
                "slot_type": "FIXED",
                "start_time": "19:00",
                "end_time": "21:00",
                "end_day_offset": 0,
                "is_active": True,
            },
        ),
        calendar_integration_mode="NONE",
        min_session_minutes=30,
    )
    milestone_repo = _InMemoryMilestoneRepo([m1])
    proposal_repo = _InMemoryProposalRepo()
    uow = _SpyUnitOfWork()
    uc = SaveManualRoadmapPlanUseCase(
        goal_repo=_InMemoryGoalRepo([goal]),  # type: ignore[arg-type]
        roadmap_repo=_InMemoryRoadmapRepo([roadmap]),  # type: ignore[arg-type]
        milestone_repo=milestone_repo,  # type: ignore[arg-type]
        proposal_repo=proposal_repo,  # type: ignore[arg-type]
        availability_query_port=_FakeAvailabilityPort(availability),  # type: ignore[arg-type]
        execution_sync_port=_FakeExecutionSyncPort(),  # type: ignore[arg-type]
        uow=uow,  # type: ignore[arg-type]
    )

    result = await uc.execute(
        user_id=user_id,
        roadmap_id=roadmap.id,
        tasks=[
            {
                "task_id": str(generate_uuid7()),
                "milestone_id": str(m1.id),
                "title": "Đọc tài liệu kiến trúc",
                "description": "Đọc chương 1 và ghi chú",
                "estimated_minutes": 60,
                "scheduled_date": "2026-06-08",
                "start_time": "19:00",
                "end_time": "20:00",
            }
        ],
        now=now,
    )

    assert result.is_valid is True
    assert result.proposal.status == ScheduleProposalStatus.DRAFT
    saved_ms = await milestone_repo.list_by_roadmap_id(roadmap.id)
    assert all(m.status == MilestoneStatus.APPROVED for m in saved_ms)
    assert uow.commit_count == 1
    assert uow.collected_events == []
    assert roadmap.pull_domain_events() == []


@pytest.mark.asyncio
async def test_generate_milestones_releases_read_tx_before_llm_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime(2026, 6, 1, 10, 0, tzinfo=UTC)
    user_id = generate_uuid7()
    goal = Goal(
        id=generate_uuid7(),
        user_id=user_id,
        title="Distributed Systems",
        raw_description="Learn consensus and replication",
        prior_knowledge_level="INTERMEDIATE",
        created_at=now,
        updated_at=now,
    )
    roadmap = Roadmap(
        id=generate_uuid7(),
        goal_id=goal.id,
        user_id=user_id,
        title="Distributed Systems Roadmap",
        description="Consensus & replication",
        status=RoadmapStatus.ACTIVE,
        start_date=date(2026, 6, 1),
        target_date=date(2026, 7, 15),
        created_at=now,
        updated_at=now,
    )
    llm_payload = {
        "milestones": [
            {
                "sequence_order": 1,
                "title": "Chặng 1: Logical Clocks và Ordering",
                "description": "Hiểu Lamport clocks và Vector clocks trong hệ phân tán.",
                "learning_outcomes": ["Phân biệt được Lamport và Vector clock"],
                "completion_criteria": "Cài đặt thành công Vector clock demo",
                "estimated_effort_minutes": 180,
                "required_concepts": ["logical_clocks"],
            },
            {
                "sequence_order": 2,
                "title": "Chặng 2: Raft Consensus & Replication",
                "description": "Leader election, log replication và safety invariants.",
                "learning_outcomes": ["Giải thích được cơ chế bầu leader trong Raft"],
                "completion_criteria": "Mô phỏng leader election khi node crash",
                "estimated_effort_minutes": 240,
                "required_concepts": ["raft_consensus"],
            },
            {
                "sequence_order": 3,
                "title": "Chặng 3: Transactional Outbox & Idempotency",
                "description": "Đảm bảo at-least-once delivery và consumer idempotent.",
                "learning_outcomes": ["Thiết kế bảng outbox và processed_events"],
                "completion_criteria": "Hoàn thành bài lab outbox relay",
                "estimated_effort_minutes": 180,
                "required_concepts": ["transactional_outbox"],
            },
        ],
        "scope_summary": "FULL_SCOPE",
        "deferred_scope": [],
    }

    # Skip dual quality critic LLM calls so only the primary planner call is asserted.
    async def _fake_critics(
        *args: Any, **kwargs: Any
    ) -> tuple[list[Any], list[dict[str, Any]], int, int]:
        del args, kwargs
        return [], [], 0, 0

    monkeypatch.setattr(
        "src.planning.application.use_cases.milestone_use_cases.run_dual_quality_critics",
        _fake_critics,
    )

    call_log: list[str] = []
    uow = _SpyUnitOfWork(call_log=call_log)
    sse_store = _FakeSseJobStore()
    job_id = generate_uuid7()
    res_id = generate_uuid7()

    uc = ExecuteMilestoneGenerationUseCase(
        goal_repo=_InMemoryGoalRepo([goal]),  # type: ignore[arg-type]
        roadmap_repo=_InMemoryRoadmapRepo([roadmap]),  # type: ignore[arg-type]
        milestone_repo=_InMemoryMilestoneRepo(),  # type: ignore[arg-type]
        quota_facade=_FakeQuotaFacade(),  # type: ignore[arg-type]
        llm_provider=_SpyLLMProvider(llm_payload, call_log),  # type: ignore[arg-type]
        sse_job_store=sse_store,  # type: ignore[arg-type]
        uow=uow,  # type: ignore[arg-type]
    )

    saved = await uc.execute(
        job_id=job_id,
        user_id=user_id,
        roadmap_id=roadmap.id,
        reservation_id=res_id,
        now=now,
    )

    assert len(saved) == 3
    assert "rollback" in call_log
    assert "llm_call" in call_log
    assert call_log.index("rollback") < call_log.index("llm_call")
    assert uow.rollback_count >= 1
    assert uow.commit_count >= 1
