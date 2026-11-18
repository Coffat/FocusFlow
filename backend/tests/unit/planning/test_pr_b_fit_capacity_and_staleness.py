from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

import pytest
from uuid6 import uuid7

from src.account.public_api import (
    AvailabilityQueryPort,
    AvailabilitySnapshotDTO,
    LearnerProfileDTO,
    LearnerProfileQueryPort,
    QuotaFacadePort,
    UserQueryPort,
    UserSnapshotDTO,
)
from src.evaluation.public_api import ScheduleChangeLogPort
from src.execution.public_api import (
    ExecutionScheduleSyncPort,
    ExistingScheduledTaskDTO,
    ScheduleSyncResultDTO,
)
from src.planning.application.dtos.planning_dtos import MilestoneInputItemDTO
from src.planning.application.ports.planning_repository_ports import (
    GoalRepositoryPort,
    MilestoneRepositoryPort,
    OfficialScheduleRepositoryPort,
    RoadmapRepositoryPort,
    ScheduleProposalRepositoryPort,
)
from src.planning.application.ports.schedule_block_repository_port import (
    ScheduleBlockRepositoryPort,
)
from src.planning.application.use_cases.availability_outbox_consumer import (
    HandleAvailabilityUpdatedEventUseCase,
)
from src.planning.application.use_cases.milestone_use_cases import (
    ApproveMilestonesUseCase,
    ExecuteMilestoneGenerationUseCase,
    UpdateMilestonesUseCase,
)
from src.planning.application.use_cases.proposal_generation_use_cases import (
    ExecuteScheduleProposalGenerationUseCase,
    InitiateScheduleProposalGenerationUseCase,
)
from src.planning.application.use_cases.proposal_management_use_cases import (
    ApplyScheduleProposalUseCase,
    UpdateScheduleProposalUseCase,
)
from src.planning.application.use_cases.roadmap_management_use_cases import (
    UpdateRoadmapUseCase,
)
from src.planning.domain.exceptions.planning_exceptions import (
    InsufficientCapacityError,
    ScopeApprovalRequiredError,
)
from src.planning.domain.models.goal import Goal, GoalStatus
from src.planning.domain.models.milestone import Milestone, MilestoneStatus
from src.planning.domain.models.roadmap import Roadmap, RoadmapStatus
from src.planning.domain.models.schedule import (
    OfficialSchedule,
    ScheduleProposal,
    ScheduleProposalStatus,
)
from src.planning.domain.models.schedule_block import ScheduleBlock
from src.planning.domain.services.milestone_effort_allocator import (
    MilestoneEffortAllocator,
)
from src.shared_kernel.application.uow import AsyncUnitOfWork
from src.shared_kernel.config import get_settings
from src.shared_kernel.infrastructure.sse.job_store import InMemorySseJobStore
from tests.helpers.llm_stubs import StubLLMAdapter


class _FakeGoalRepo(GoalRepositoryPort):
    def __init__(self) -> None:
        self.items: dict[UUID, Goal] = {}

    async def save(self, goal: Goal) -> Goal:
        self.items[goal.id] = goal
        return goal

    async def get_by_id(self, goal_id: UUID) -> Goal | None:
        return self.items.get(goal_id)

    async def get_by_id_for_user(self, goal_id: UUID, user_id: UUID) -> Goal | None:
        g = self.items.get(goal_id)
        return g if g and g.user_id == user_id else None

    async def list_by_user_id(self, user_id: UUID) -> list[Goal]:
        return [g for g in self.items.values() if g.user_id == user_id]


class _FakeRoadmapRepo(RoadmapRepositoryPort):
    def __init__(self) -> None:
        self.items: dict[UUID, Roadmap] = {}

    async def save(self, roadmap: Roadmap) -> Roadmap:
        self.items[roadmap.id] = roadmap
        return roadmap

    async def get_by_id(self, roadmap_id: UUID) -> Roadmap | None:
        return self.items.get(roadmap_id)

    async def get_by_id_for_user(self, roadmap_id: UUID, user_id: UUID) -> Roadmap | None:
        r = self.items.get(roadmap_id)
        return r if r and r.user_id == user_id else None

    async def list_by_user_id(
        self,
        user_id: UUID,
        *,
        status: str | None = None,
    ) -> list[Roadmap]:
        return [
            r
            for r in self.items.values()
            if r.user_id == user_id and (status is None or r.status.value == status)
        ]

    async def count_active_by_user_id(
        self,
        user_id: UUID,
        *,
        exclude_roadmap_id: UUID | None = None,
    ) -> int:
        return sum(
            1
            for r in self.items.values()
            if r.user_id == user_id
            and r.status == RoadmapStatus.ACTIVE
            and r.id != exclude_roadmap_id
        )


class _FakeMilestoneRepo(MilestoneRepositoryPort):
    def __init__(self) -> None:
        self.by_roadmap: dict[UUID, list[Milestone]] = {}

    async def save_many(self, roadmap_id: UUID, milestones: Any) -> list[Milestone]:
        self.by_roadmap[roadmap_id] = list(milestones)
        return sorted(self.by_roadmap[roadmap_id], key=lambda m: m.sequence_order)

    async def list_by_roadmap_id(self, roadmap_id: UUID) -> list[Milestone]:
        return sorted(self.by_roadmap.get(roadmap_id, []), key=lambda m: m.sequence_order)

    async def approve_all_for_roadmap(self, roadmap_id: UUID, now: datetime) -> list[Milestone]:
        items = self.by_roadmap.get(roadmap_id, [])
        for m in items:
            m.approve(now)
        return sorted(items, key=lambda m: m.sequence_order)


class _FakeProposalRepo(ScheduleProposalRepositoryPort):
    def __init__(self) -> None:
        self.items: dict[UUID, ScheduleProposal] = {}

    async def save(self, proposal: ScheduleProposal) -> ScheduleProposal:
        self.items[proposal.id] = proposal
        return proposal

    async def get_by_id(self, proposal_id: UUID) -> ScheduleProposal | None:
        return self.items.get(proposal_id)

    async def get_current_draft(self, roadmap_id: UUID) -> ScheduleProposal | None:
        for p in self.items.values():
            if p.roadmap_id == roadmap_id and p.status == ScheduleProposalStatus.DRAFT:
                return p
        return None

    async def discard_existing_drafts(self, roadmap_id: UUID, now: datetime) -> int:
        cnt = 0
        for p in self.items.values():
            if p.roadmap_id == roadmap_id and p.status == ScheduleProposalStatus.DRAFT:
                p.mark_discarded(now)
                cnt += 1
        return cnt


class _FakeOfficialScheduleRepo(OfficialScheduleRepositoryPort):
    def __init__(self) -> None:
        self.by_roadmap: dict[UUID, OfficialSchedule] = {}

    async def save(self, schedule: OfficialSchedule) -> OfficialSchedule:
        self.by_roadmap[schedule.roadmap_id] = schedule
        return schedule

    async def get_by_roadmap_id(self, roadmap_id: UUID) -> OfficialSchedule | None:
        return self.by_roadmap.get(roadmap_id)


class _FakeBlockRepo(ScheduleBlockRepositoryPort):
    def __init__(self) -> None:
        self.blocks: list[ScheduleBlock] = []

    async def get_by_schedule_id(self, official_schedule_id: UUID) -> list[ScheduleBlock]:
        return [b for b in self.blocks if b.official_schedule_id == official_schedule_id]

    async def list_by_roadmap_ids(self, roadmap_ids: Any) -> list[ScheduleBlock]:
        rset = set(roadmap_ids)
        return [b for b in self.blocks if b.roadmap_id in rset]

    async def save_all(self, blocks: Any) -> list[ScheduleBlock]:
        self.blocks.extend(blocks)
        return list(blocks)


class _FakeQuotaFacade(QuotaFacadePort):
    def __init__(self) -> None:
        self.reserved: list[UUID] = []
        self.committed: list[UUID] = []
        self.released: list[UUID] = []

    async def reserve_quota(
        self,
        *,
        user_id: UUID,
        operation_type: str = "ROADMAP_GEN",
        cost: int = 1,
        ttl_seconds: int = 120,
    ) -> UUID:
        _ = (user_id, operation_type, cost, ttl_seconds)
        rid = uuid7()
        self.reserved.append(rid)
        return rid

    async def commit_reservation(
        self,
        reservation_id: UUID,
        *,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        model_name: str = "",
    ) -> None:
        _ = (prompt_tokens, completion_tokens, model_name)
        self.committed.append(reservation_id)

    async def release_reservation(self, reservation_id: UUID, *, reason: str = "") -> None:
        _ = reason
        self.released.append(reservation_id)

    async def check_quota_available(self, user_id: UUID, min_credits: int = 1) -> bool:
        _ = (user_id, min_credits)
        return True

    async def expire_stale_reservations(self, now: datetime | None = None) -> int:
        _ = now
        return 0


class _FakeUoW(AsyncUnitOfWork):
    def __init__(self) -> None:
        self.commits = 0
        self.events: list[Any] = []

    async def __aenter__(self) -> _FakeUoW:
        return self

    async def __aexit__(self, *args: Any) -> None:
        return None

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        return None

    def collect_events_from(self, aggregate: Any) -> None:
        if hasattr(aggregate, "pull_domain_events"):
            self.events.extend(aggregate.pull_domain_events())


class _MutableAvailabilityPort(AvailabilityQueryPort):
    def __init__(self, snapshot: AvailabilitySnapshotDTO) -> None:
        self.snapshot = snapshot

    async def get_active_availability(self, user_id: UUID) -> AvailabilitySnapshotDTO | None:
        _ = user_id
        return self.snapshot

    async def validate_schedule_proposal(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError


class _FakeLearnerProfilePort(LearnerProfileQueryPort):
    async def get_learner_profile(self, user_id: UUID) -> LearnerProfileDTO:
        return LearnerProfileDTO(
            user_id=user_id,
            opt_session_minutes=60,
            estimation_bias_beta=1.0,
        )


class _FakeExecutionSyncPort(ExecutionScheduleSyncPort):
    def __init__(self) -> None:
        self.tasks: list[ExistingScheduledTaskDTO] = []

    async def get_tasks_for_roadmaps(
        self,
        roadmap_ids: Any,
        *,
        roadmap_target_dates: dict[UUID, date | None] | None = None,
    ) -> list[ExistingScheduledTaskDTO]:
        _ = (roadmap_ids, roadmap_target_dates)
        return list(self.tasks)

    async def sync_official_schedule_tasks(self, **kwargs: Any) -> ScheduleSyncResultDTO:
        proposed = kwargs.get("proposed_tasks", [])
        return ScheduleSyncResultDTO(
            roadmap_id=kwargs["roadmap_id"],
            official_schedule_id=kwargs["official_schedule_id"],
            preserved_completed_tasks_count=0,
            replaced_tasks_count=0,
            inserted_tasks_count=len(proposed),
            affected_tasks_count=len(proposed),
            total_shifted_minutes=0,
            total_planned_minutes=sum(t.estimated_minutes for t in proposed),
            total_active_sessions=len(proposed),
        )


class _FakeUserQueryPort(UserQueryPort):
    async def get_user_by_id(self, user_id: UUID) -> UserSnapshotDTO | None:
        return UserSnapshotDTO(
            id=user_id,
            email="learner@focusflow.vn",
            full_name="Learner",
            timezone="Asia/Ho_Chi_Minh",
            role="LEARNER",
            tier="FREE",
            is_locked=False,
        )


class _FakeOutboxRepo:
    def __init__(self) -> None:
        self.processed: set[tuple[UUID, str]] = set()

    async def add_events(self, events: Any) -> None:
        _ = events

    async def is_event_processed(self, event_id: UUID, consumer_name: str) -> bool:
        return (event_id, consumer_name) in self.processed

    async def mark_event_processed(self, event_id: UUID, consumer_name: str) -> None:
        self.processed.add((event_id, consumer_name))


class _FakeChangeLogPort(ScheduleChangeLogPort):
    async def record_change_log(self, **kwargs: Any) -> None:
        _ = kwargs


def _tight_availability(user_id: UUID, *, monday_hours: int = 2) -> AvailabilitySnapshotDTO:
    end_hour = 19 + monday_hours
    return AvailabilitySnapshotDTO(
        user_id=user_id,
        mode="MODE_B",
        daily_cap_minutes=monday_hours * 60,
        weekly_capacity_minutes=monday_hours * 60,
        daily_quota_minutes={},
        availability_slots=(
            {
                "day_of_week": "monday",
                "start_time": "19:00",
                "end_time": f"{end_hour:02d}:00",
                "end_day_offset": 0,
                "is_active": True,
            },
        ),
        disabled_weekdays=(),
    )


def _three_tight_milestones_payload() -> dict[str, Any]:
    return {
        "milestones": [
            {
                "sequence_order": 1,
                "title": "Nền tảng Rust Ownership",
                "description": "Cài đặt và kiểm thử ownership",
                "learning_outcomes": ["Hiểu ownership", "Kiểm thử unit"],
                "completion_criteria": "Pass unit test",
                "estimated_effort_minutes": 180,
                "required_concepts": [],
                "unverified_concepts": ["rust-ownership"],
                "dependencies": [],
            },
            {
                "sequence_order": 2,
                "title": "Async Tokio & Channels",
                "description": "Xây dựng server async",
                "learning_outcomes": ["Triển khai channel", "Kiểm thử tích hợp"],
                "completion_criteria": "Server async chạy ổn định",
                "estimated_effort_minutes": 240,
                "required_concepts": [],
                "unverified_concepts": ["tokio"],
                "dependencies": [1],
            },
            {
                "sequence_order": 3,
                "title": "Đồ án Raft Cluster",
                "description": "Xây dựng cụm Raft 3-node",
                "learning_outcomes": ["Triển khai leader election", "Chạy chaos test"],
                "completion_criteria": "Đồ án cụm 3-node vượt qua chaos test",
                "estimated_effort_minutes": 360,
                "required_concepts": [],
                "unverified_concepts": ["raft"],
                "dependencies": [2],
            },
        ],
        "scope_summary": "FULL_SCOPE",
        "deferred_scope": [],
    }


async def _setup_fit_capacity_roadmap(
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, Any]:
    monkeypatch.setattr(get_settings(), "milestone_effort_allocator_enabled", True)
    now = datetime(2026, 11, 2, 10, 0, tzinfo=UTC)
    user_id = uuid7()
    goal = Goal(
        id=uuid7(),
        user_id=user_id,
        title="Rust Distributed Systems",
        raw_description="Xây dựng hệ phân tán",
        target_date=date(2026, 11, 15),
        prior_knowledge_level="INTERMEDIATE",
        status=GoalStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
    roadmap = Roadmap(
        id=uuid7(),
        user_id=user_id,
        goal_id=goal.id,
        title="Rust 2 tuần",
        start_date=date(2026, 11, 2),
        target_date=date(2026, 11, 15),
        status=RoadmapStatus.INITIALIZED,
        created_at=now,
        updated_at=now,
    )
    goal_repo = _FakeGoalRepo()
    roadmap_repo = _FakeRoadmapRepo()
    milestone_repo = _FakeMilestoneRepo()
    proposal_repo = _FakeProposalRepo()
    schedule_repo = _FakeOfficialScheduleRepo()
    block_repo = _FakeBlockRepo()
    quota = _FakeQuotaFacade()
    sse_store = InMemorySseJobStore()
    uow = _FakeUoW()
    avail_port = _MutableAvailabilityPort(_tight_availability(user_id, monday_hours=2))
    exec_sync = _FakeExecutionSyncPort()
    profile_port = _FakeLearnerProfilePort()
    change_log = _FakeChangeLogPort()

    await goal_repo.save(goal)
    await roadmap_repo.save(roadmap)

    ms_job_id = uuid7()
    ms_res_id = await quota.reserve_quota(user_id=user_id, operation_type="MILESTONE_GEN")
    await sse_store.create_job(
        job_id=ms_job_id,
        user_id=user_id,
        roadmap_id=roadmap.id,
        reservation_id=ms_res_id,
        job_type="MILESTONE_GEN",
        operation=f"MILESTONE_GEN:{roadmap.id}",
    )
    gen_ms_uc = ExecuteMilestoneGenerationUseCase(
        goal_repo=goal_repo,
        roadmap_repo=roadmap_repo,
        milestone_repo=milestone_repo,
        quota_facade=quota,
        llm_provider=StubLLMAdapter(canned_responses=[_three_tight_milestones_payload()]),
        sse_job_store=sse_store,
        uow=uow,
        availability_query_port=avail_port,
        execution_sync_port=exec_sync,
    )
    milestones = await gen_ms_uc.execute(
        job_id=ms_job_id,
        user_id=user_id,
        roadmap_id=roadmap.id,
        reservation_id=ms_res_id,
        now=now,
    )
    stored_rm = await roadmap_repo.get_by_id(roadmap.id)
    assert stored_rm is not None
    prelim = stored_rm.planning_metadata["preliminary_feasibility"]
    assert prelim["status"] == "FIT_CAPACITY_REQUIRES_APPROVAL"
    assert len(prelim["kept_scope"]) < 3
    assert len(prelim["deferred_scope"]) >= 1

    return {
        "now": now,
        "user_id": user_id,
        "goal": goal,
        "roadmap": stored_rm,
        "milestones": milestones,
        "goal_repo": goal_repo,
        "roadmap_repo": roadmap_repo,
        "milestone_repo": milestone_repo,
        "proposal_repo": proposal_repo,
        "schedule_repo": schedule_repo,
        "block_repo": block_repo,
        "quota": quota,
        "sse_store": sse_store,
        "uow": uow,
        "avail_port": avail_port,
        "exec_sync": exec_sync,
        "profile_port": profile_port,
        "change_log": change_log,
    }


@pytest.mark.asyncio
async def test_def01_fit_capacity_update_and_apply_preserve_deferred_pending_milestones(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env = await _setup_fit_capacity_roadmap(monkeypatch)
    now: datetime = env["now"]
    user_id: UUID = env["user_id"]
    roadmap: Roadmap = env["roadmap"]
    roadmap_repo: _FakeRoadmapRepo = env["roadmap_repo"]
    milestone_repo: _FakeMilestoneRepo = env["milestone_repo"]
    proposal_repo: _FakeProposalRepo = env["proposal_repo"]
    schedule_repo: _FakeOfficialScheduleRepo = env["schedule_repo"]
    block_repo: _FakeBlockRepo = env["block_repo"]
    quota: _FakeQuotaFacade = env["quota"]
    sse_store: InMemorySseJobStore = env["sse_store"]
    uow: _FakeUoW = env["uow"]
    avail_port: _MutableAvailabilityPort = env["avail_port"]
    exec_sync: _FakeExecutionSyncPort = env["exec_sync"]
    profile_port: _FakeLearnerProfilePort = env["profile_port"]
    change_log: _FakeChangeLogPort = env["change_log"]

    prelim = roadmap.planning_metadata["preliminary_feasibility"]
    approve_uc = ApproveMilestonesUseCase(
        roadmap_repo=roadmap_repo,
        milestone_repo=milestone_repo,
        uow=uow,
    )
    approved = await approve_uc.execute(
        user_id=user_id,
        roadmap_id=roadmap.id,
        confirmed_scope_proposal_version=int(prelim["scope_proposal_version"]),
        accept_fit_capacity=True,
        now=now,
    )
    kept_ms = [m for m in approved if m.status != MilestoneStatus.PENDING]
    deferred_ms = [m for m in approved if m.status == MilestoneStatus.PENDING]
    assert len(kept_ms) >= 1
    assert len(deferred_ms) >= 1

    # Generate proposal covering ONLY kept milestones
    init_prop_uc = InitiateScheduleProposalGenerationUseCase(
        roadmap_repo=roadmap_repo,
        milestone_repo=milestone_repo,
        quota_facade=quota,
        sse_job_store=sse_store,
        uow=uow,
    )
    decomposer_tasks = [
        {
            "task_id": f"T{idx}",
            "milestone_id": str(m.id),
            "title": f"Bài {idx}: {m.title}",
            "description": "Thực hành chuyên sâu",
            "task_type": "PRACTICE",
            "learning_objective": f"Nắm vững {m.title}",
            "completion_criteria": "Pass unit test",
            "resource_ids": [],
            "concept_ids": [],
            "covered_outcome_ids": [
                f"M{m.sequence_order}-O{oi}" for oi in range(1, len(m.learning_outcomes) + 1)
            ],
            "estimated_minutes": 60,
        }
        for idx, m in enumerate(kept_ms, start=1)
    ]
    exec_prop_uc = ExecuteScheduleProposalGenerationUseCase(
        goal_repo=env["goal_repo"],
        roadmap_repo=roadmap_repo,
        milestone_repo=milestone_repo,
        proposal_repo=proposal_repo,
        availability_query_port=avail_port,
        learner_profile_port=profile_port,
        execution_sync_port=exec_sync,
        quota_facade=quota,
        llm_provider=StubLLMAdapter(
            canned_responses=[{"tasks": decomposer_tasks, "dependencies": []}]
        ),
        sse_job_store=sse_store,
        uow=uow,
        enable_tier3_judge=False,
    )
    ticket = await init_prop_uc.execute(user_id=user_id, roadmap_id=roadmap.id, run_inline=False)
    proposal = await exec_prop_uc.execute(
        job_id=ticket.job_id,
        user_id=user_id,
        roadmap_id=roadmap.id,
        reservation_id=ticket.reservation_id,
        now=now,
    )

    # UpdateScheduleProposalUseCase MUST succeed without MILESTONE_WITHOUT_TASKS on deferred PENDING milestones
    update_prop_uc = UpdateScheduleProposalUseCase(
        roadmap_repo=roadmap_repo,
        milestone_repo=milestone_repo,
        proposal_repo=proposal_repo,
        availability_query_port=avail_port,
        execution_sync_port=exec_sync,
        uow=uow,
        user_query_port=_FakeUserQueryPort(),
        block_repo=block_repo,
        goal_repo=env["goal_repo"],
    )
    edited_tasks = [dict(t) for t in proposal.proposal_data["tasks"]]
    edited_tasks[0]["title"] = "Bài 1 (đã chỉnh sửa): Nền tảng Rust"
    updated_view = await update_prop_uc.execute(
        user_id=user_id,
        roadmap_id=roadmap.id,
        proposal_id=proposal.id,
        tasks=edited_tasks,
        dependencies=[],
        reject_invalid=True,
        now=now,
    )
    assert updated_view.is_valid is True
    assert updated_view.violations == []

    # ApplyScheduleProposalUseCase MUST succeed without MILESTONE_WITHOUT_TASKS on deferred PENDING milestones
    apply_uc = ApplyScheduleProposalUseCase(
        roadmap_repo=roadmap_repo,
        milestone_repo=milestone_repo,
        proposal_repo=proposal_repo,
        schedule_repo=schedule_repo,
        block_repo=block_repo,
        availability_query_port=avail_port,
        execution_sync_port=exec_sync,
        schedule_change_log_port=change_log,
        uow=uow,
        user_query_port=_FakeUserQueryPort(),
        goal_repo=env["goal_repo"],
    )
    applied = await apply_uc.execute(
        user_id=user_id,
        roadmap_id=roadmap.id,
        proposal_id=proposal.id,
        confirm_warnings=True,
        confirm_partial_schedule=True,
        now=now,
    )
    assert applied.proposal.status == ScheduleProposalStatus.APPLIED
    # Deferred milestones must stay PENDING in repository
    all_ms_after = await milestone_repo.list_by_roadmap_id(roadmap.id)
    for m in all_ms_after:
        if m.id in {dm.id for dm in deferred_ms}:
            assert m.status == MilestoneStatus.PENDING


@pytest.mark.asyncio
async def test_def01_update_and_apply_block_unapproved_or_hash_tampered_fit_capacity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env = await _setup_fit_capacity_roadmap(monkeypatch)
    now: datetime = env["now"]
    user_id: UUID = env["user_id"]
    roadmap: Roadmap = env["roadmap"]
    roadmap_repo: _FakeRoadmapRepo = env["roadmap_repo"]
    milestone_repo: _FakeMilestoneRepo = env["milestone_repo"]
    proposal_repo: _FakeProposalRepo = env["proposal_repo"]
    schedule_repo: _FakeOfficialScheduleRepo = env["schedule_repo"]
    block_repo: _FakeBlockRepo = env["block_repo"]
    uow: _FakeUoW = env["uow"]
    avail_port: _MutableAvailabilityPort = env["avail_port"]
    exec_sync: _FakeExecutionSyncPort = env["exec_sync"]
    change_log: _FakeChangeLogPort = env["change_log"]

    kept_m = env["milestones"][0]
    draft = ScheduleProposal(
        id=uuid7(),
        roadmap_id=roadmap.id,
        user_id=user_id,
        proposal_data={
            "tasks": [
                {
                    "task_id": str(uuid7()),
                    "milestone_id": str(kept_m.id),
                    "title": "Task 1",
                    "learning_objective": "Obj",
                    "completion_criteria": "Crit",
                    "covered_outcome_ids": ["M1-O1", "M1-O2"],
                    "estimated_minutes": 60,
                    "scheduled_date": "2026-11-02",
                    "scheduled_start": "2026-11-02T19:00:00+00:00",
                    "scheduled_end": "2026-11-02T20:00:00+00:00",
                }
            ],
            "dependencies": [],
            "feasibility_verdict": "VERIFIED_FEASIBLE",
        },
        status=ScheduleProposalStatus.DRAFT,
        created_at=now,
        updated_at=now,
    )
    await proposal_repo.save(draft)

    apply_uc = ApplyScheduleProposalUseCase(
        roadmap_repo=roadmap_repo,
        milestone_repo=milestone_repo,
        proposal_repo=proposal_repo,
        schedule_repo=schedule_repo,
        block_repo=block_repo,
        availability_query_port=avail_port,
        execution_sync_port=exec_sync,
        schedule_change_log_port=change_log,
        uow=uow,
    )
    with pytest.raises(ScopeApprovalRequiredError):
        await apply_uc.execute(
            user_id=user_id,
            roadmap_id=roadmap.id,
            proposal_id=draft.id,
            now=now,
        )

    update_prop_uc = UpdateScheduleProposalUseCase(
        roadmap_repo=roadmap_repo,
        milestone_repo=milestone_repo,
        proposal_repo=proposal_repo,
        availability_query_port=avail_port,
        execution_sync_port=exec_sync,
        uow=uow,
        block_repo=block_repo,
    )
    with pytest.raises(ScopeApprovalRequiredError):
        await update_prop_uc.execute(
            user_id=user_id,
            roadmap_id=roadmap.id,
            proposal_id=draft.id,
            tasks=draft.proposal_data["tasks"],
            dependencies=[],
            now=now,
        )


def test_def06_proposal_hash_covers_target_date_availability_existing_tasks_and_metadata() -> None:
    kept = [
        {
            "sequence_order": 1,
            "milestone_id": str(uuid7()),
            "title": "M1",
            "completion_criteria": "Pass quiz",
            "normalized_planned_effort_minutes": 120,
            "expected_outcomes": ["M1-O1: Basics"],
            "dependencies": [],
            "prerequisite_milestone_ids": [],
        }
    ]
    deferred = [
        {
            "sequence_order": 2,
            "milestone_id": str(uuid7()),
            "title": "M2",
            "completion_criteria": "Build app",
            "dependencies": [1],
            "prerequisite_milestone_ids": [kept[0]["milestone_id"]],
        }
    ]
    # Backward-compatible legacy call still works
    legacy_h = MilestoneEffortAllocator._compute_proposal_hash(
        version=1,
        status="FIT_CAPACITY_REQUIRES_APPROVAL",
        kept_scope=kept,
        deferred_scope=deferred,
        hard_packable_capacity_minutes=120,
    )
    assert legacy_h.startswith("sha256:")

    base_h = MilestoneEffortAllocator._compute_proposal_hash(
        version=1,
        status="FIT_CAPACITY_REQUIRES_APPROVAL",
        kept_scope=kept,
        deferred_scope=deferred,
        hard_packable_capacity_minutes=120,
        target_date=date(2026, 11, 15),
        availability_fingerprint="sha256:avail_a",
        existing_tasks_fingerprint="sha256:tasks_a",
    )
    # Changing target_date MUST change hash
    assert base_h != MilestoneEffortAllocator._compute_proposal_hash(
        version=1,
        status="FIT_CAPACITY_REQUIRES_APPROVAL",
        kept_scope=kept,
        deferred_scope=deferred,
        hard_packable_capacity_minutes=120,
        target_date=date(2026, 11, 20),
        availability_fingerprint="sha256:avail_a",
        existing_tasks_fingerprint="sha256:tasks_a",
    )
    # Changing availability_fingerprint MUST change hash
    assert base_h != MilestoneEffortAllocator._compute_proposal_hash(
        version=1,
        status="FIT_CAPACITY_REQUIRES_APPROVAL",
        kept_scope=kept,
        deferred_scope=deferred,
        hard_packable_capacity_minutes=120,
        target_date=date(2026, 11, 15),
        availability_fingerprint="sha256:avail_b",
        existing_tasks_fingerprint="sha256:tasks_a",
    )
    # Changing existing_tasks_fingerprint MUST change hash
    assert base_h != MilestoneEffortAllocator._compute_proposal_hash(
        version=1,
        status="FIT_CAPACITY_REQUIRES_APPROVAL",
        kept_scope=kept,
        deferred_scope=deferred,
        hard_packable_capacity_minutes=120,
        target_date=date(2026, 11, 15),
        availability_fingerprint="sha256:avail_a",
        existing_tasks_fingerprint="sha256:tasks_b",
    )
    # Changing completion_criteria MUST change hash
    kept_crit = [{**kept[0], "completion_criteria": "Pass exam"}]
    assert base_h != MilestoneEffortAllocator._compute_proposal_hash(
        version=1,
        status="FIT_CAPACITY_REQUIRES_APPROVAL",
        kept_scope=kept_crit,
        deferred_scope=deferred,
        hard_packable_capacity_minutes=120,
        target_date=date(2026, 11, 15),
        availability_fingerprint="sha256:avail_a",
        existing_tasks_fingerprint="sha256:tasks_a",
    )
    # Changing dependencies MUST change hash
    deferred_dep = [{**deferred[0], "dependencies": []}]
    assert base_h != MilestoneEffortAllocator._compute_proposal_hash(
        version=1,
        status="FIT_CAPACITY_REQUIRES_APPROVAL",
        kept_scope=kept,
        deferred_scope=deferred_dep,
        hard_packable_capacity_minutes=120,
        target_date=date(2026, 11, 15),
        availability_fingerprint="sha256:avail_a",
        existing_tasks_fingerprint="sha256:tasks_a",
    )


@pytest.mark.asyncio
async def test_def06_milestone_edit_and_roadmap_target_date_invalidate_and_discard_drafts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env = await _setup_fit_capacity_roadmap(monkeypatch)
    now: datetime = env["now"]
    user_id: UUID = env["user_id"]
    roadmap: Roadmap = env["roadmap"]
    goal_repo: _FakeGoalRepo = env["goal_repo"]
    roadmap_repo: _FakeRoadmapRepo = env["roadmap_repo"]
    milestone_repo: _FakeMilestoneRepo = env["milestone_repo"]
    proposal_repo: _FakeProposalRepo = env["proposal_repo"]
    uow: _FakeUoW = env["uow"]
    avail_port: _MutableAvailabilityPort = env["avail_port"]
    exec_sync: _FakeExecutionSyncPort = env["exec_sync"]

    approve_uc = ApproveMilestonesUseCase(
        roadmap_repo=roadmap_repo,
        milestone_repo=milestone_repo,
        uow=uow,
        goal_repo=goal_repo,
        availability_query_port=avail_port,
        execution_sync_port=exec_sync,
        proposal_repo=proposal_repo,
    )
    prelim_v1 = roadmap.planning_metadata["preliminary_feasibility"]
    await approve_uc.execute(
        user_id=user_id,
        roadmap_id=roadmap.id,
        confirmed_scope_proposal_version=int(prelim_v1["scope_proposal_version"]),
        accept_fit_capacity=True,
        now=now,
    )
    draft = ScheduleProposal(
        id=uuid7(),
        roadmap_id=roadmap.id,
        user_id=user_id,
        proposal_data={"tasks": []},
        status=ScheduleProposalStatus.DRAFT,
        created_at=now,
        updated_at=now,
    )
    await proposal_repo.save(draft)

    # 1. UpdateMilestonesUseCase recomputes feasibility, bumps version, resets approval & discards DRAFT
    update_ms_uc = UpdateMilestonesUseCase(
        roadmap_repo=roadmap_repo,
        milestone_repo=milestone_repo,
        uow=uow,
        goal_repo=goal_repo,
        proposal_repo=proposal_repo,
        availability_query_port=avail_port,
        execution_sync_port=exec_sync,
    )
    current_ms = await milestone_repo.list_by_roadmap_id(roadmap.id)
    updated_items = [
        MilestoneInputItemDTO(
            milestone_id=m.id,
            sequence_order=m.sequence_order,
            title=m.title,
            description=m.description,
            learning_outcomes=m.learning_outcomes,
            completion_criteria="New strict completion criteria"
            if idx == 0
            else m.completion_criteria,
            estimated_effort_minutes=300 if idx == 0 else m.estimated_effort_minutes,
            required_concepts=m.required_concepts,
            unverified_concepts=m.unverified_concepts,
            prerequisite_milestone_ids=m.prerequisite_milestone_ids,
        )
        for idx, m in enumerate(current_ms)
    ]
    saved_ms = await update_ms_uc.execute(
        user_id=user_id,
        roadmap_id=roadmap.id,
        items=updated_items,
        now=now,
    )
    assert all(m.status == MilestoneStatus.PENDING for m in saved_ms)
    rm_after_ms_edit = await roadmap_repo.get_by_id(roadmap.id)
    assert rm_after_ms_edit is not None
    prelim_v2 = rm_after_ms_edit.planning_metadata["preliminary_feasibility"]
    assert prelim_v2["scope_approval_status"] == "PENDING_LEARNER_APPROVAL"
    assert prelim_v2["approved_scope_version"] is None
    assert prelim_v2["scope_proposal_version"] > prelim_v1["scope_proposal_version"]
    assert prelim_v2["scope_proposal_hash"] != prelim_v1["scope_proposal_hash"]
    assert await proposal_repo.get_current_draft(roadmap.id) is None

    # 2. Re-approve v2, create new DRAFT, then UpdateRoadmapUseCase shrinking target_date
    await approve_uc.execute(
        user_id=user_id,
        roadmap_id=roadmap.id,
        confirmed_scope_proposal_version=int(prelim_v2["scope_proposal_version"]),
        accept_fit_capacity=True,
        now=now,
    )
    draft2 = ScheduleProposal(
        id=uuid7(),
        roadmap_id=roadmap.id,
        user_id=user_id,
        proposal_data={"tasks": []},
        status=ScheduleProposalStatus.DRAFT,
        created_at=now,
        updated_at=now,
    )
    await proposal_repo.save(draft2)

    update_rm_uc = UpdateRoadmapUseCase(
        goal_repo=goal_repo,
        roadmap_repo=roadmap_repo,
        uow=uow,
        milestone_repo=milestone_repo,
        proposal_repo=proposal_repo,
        availability_query_port=avail_port,
        execution_sync_port=exec_sync,
    )
    await update_rm_uc.execute(
        user_id=user_id,
        roadmap_id=roadmap.id,
        target_date=date(2026, 11, 10),
        now=now,
    )
    rm_after_date = await roadmap_repo.get_by_id(roadmap.id)
    assert rm_after_date is not None
    prelim_v3 = rm_after_date.planning_metadata["preliminary_feasibility"]
    assert prelim_v3["scope_approval_status"] == "PENDING_LEARNER_APPROVAL"
    assert prelim_v3["approved_scope_version"] is None
    assert prelim_v3["scope_proposal_hash"] != prelim_v2["scope_proposal_hash"]
    assert await proposal_repo.get_current_draft(roadmap.id) is None


@pytest.mark.asyncio
async def test_def06_sync_drift_detection_catches_availability_shrink_on_approve_initiate_apply(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env = await _setup_fit_capacity_roadmap(monkeypatch)
    now: datetime = env["now"]
    user_id: UUID = env["user_id"]
    roadmap: Roadmap = env["roadmap"]
    goal_repo: _FakeGoalRepo = env["goal_repo"]
    roadmap_repo: _FakeRoadmapRepo = env["roadmap_repo"]
    milestone_repo: _FakeMilestoneRepo = env["milestone_repo"]
    proposal_repo: _FakeProposalRepo = env["proposal_repo"]
    schedule_repo: _FakeOfficialScheduleRepo = env["schedule_repo"]
    block_repo: _FakeBlockRepo = env["block_repo"]
    quota: _FakeQuotaFacade = env["quota"]
    sse_store: InMemorySseJobStore = env["sse_store"]
    uow: _FakeUoW = env["uow"]
    avail_port: _MutableAvailabilityPort = env["avail_port"]
    exec_sync: _FakeExecutionSyncPort = env["exec_sync"]
    change_log: _FakeChangeLogPort = env["change_log"]

    prelim_v1 = roadmap.planning_metadata["preliminary_feasibility"]
    approve_uc = ApproveMilestonesUseCase(
        roadmap_repo=roadmap_repo,
        milestone_repo=milestone_repo,
        uow=uow,
        goal_repo=goal_repo,
        proposal_repo=proposal_repo,
        availability_query_port=avail_port,
        execution_sync_port=exec_sync,
    )
    # Approve v1 while fresh
    await approve_uc.execute(
        user_id=user_id,
        roadmap_id=roadmap.id,
        confirmed_scope_proposal_version=int(prelim_v1["scope_proposal_version"]),
        accept_fit_capacity=True,
        now=now,
    )
    # Double-submit while fresh -> idempotent success
    res_double = await approve_uc.execute(
        user_id=user_id,
        roadmap_id=roadmap.id,
        confirmed_scope_proposal_version=int(prelim_v1["scope_proposal_version"]),
        accept_fit_capacity=True,
        now=now,
    )
    assert any(m.status == MilestoneStatus.APPROVED for m in res_double)

    # Create DRAFT proposal for M1
    kept_m = env["milestones"][0]
    draft = ScheduleProposal(
        id=uuid7(),
        roadmap_id=roadmap.id,
        user_id=user_id,
        proposal_data={
            "tasks": [
                {
                    "task_id": str(uuid7()),
                    "milestone_id": str(kept_m.id),
                    "title": "Task 1",
                    "learning_objective": "Obj",
                    "completion_criteria": "Crit",
                    "covered_outcome_ids": ["M1-O1", "M1-O2"],
                    "estimated_minutes": 60,
                    "scheduled_date": "2026-11-02",
                    "scheduled_start": "2026-11-02T19:00:00+00:00",
                    "scheduled_end": "2026-11-02T20:00:00+00:00",
                }
            ],
            "dependencies": [],
            "feasibility_verdict": "VERIFIED_FEASIBLE",
        },
        status=ScheduleProposalStatus.DRAFT,
        created_at=now,
        updated_at=now,
    )
    await proposal_repo.save(draft)

    # Shrink availability to 0 -> becomes PRELIMINARY_UNSCHEDULABLE!
    avail_port.snapshot = AvailabilitySnapshotDTO(
        user_id=user_id,
        mode="MODE_B",
        daily_cap_minutes=0,
        weekly_capacity_minutes=0,
        daily_quota_minutes={},
        availability_slots=(),
        disabled_weekdays=(
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ),
    )

    # ApproveMilestonesUseCase MUST detect drift & raise InsufficientCapacityError (even though already APPROVED_BY_LEARNER!)
    with pytest.raises(InsufficientCapacityError):
        await approve_uc.execute(
            user_id=user_id,
            roadmap_id=roadmap.id,
            confirmed_scope_proposal_version=int(prelim_v1["scope_proposal_version"]),
            accept_fit_capacity=True,
            now=now,
        )

    # InitiateScheduleProposalGenerationUseCase MUST detect drift & raise 409 without reserving quota
    init_prop_uc = InitiateScheduleProposalGenerationUseCase(
        roadmap_repo=roadmap_repo,
        milestone_repo=milestone_repo,
        quota_facade=quota,
        sse_job_store=sse_store,
        uow=uow,
        goal_repo=goal_repo,
        proposal_repo=proposal_repo,
        availability_query_port=avail_port,
        execution_sync_port=exec_sync,
    )
    reserved_before = len(quota.reserved)
    with pytest.raises(InsufficientCapacityError):
        await init_prop_uc.execute(user_id=user_id, roadmap_id=roadmap.id, run_inline=False)
    assert len(quota.reserved) == reserved_before

    # ApplyScheduleProposalUseCase MUST detect drift & raise InsufficientCapacityError
    apply_uc = ApplyScheduleProposalUseCase(
        roadmap_repo=roadmap_repo,
        milestone_repo=milestone_repo,
        proposal_repo=proposal_repo,
        schedule_repo=schedule_repo,
        block_repo=block_repo,
        availability_query_port=avail_port,
        execution_sync_port=exec_sync,
        schedule_change_log_port=change_log,
        uow=uow,
        goal_repo=goal_repo,
    )
    with pytest.raises(InsufficientCapacityError):
        await apply_uc.execute(
            user_id=user_id,
            roadmap_id=roadmap.id,
            proposal_id=draft.id,
            now=now,
        )


@pytest.mark.asyncio
async def test_def06_outbox_availability_consumer_is_idempotent_and_skips_completed_archived(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env = await _setup_fit_capacity_roadmap(monkeypatch)
    now: datetime = env["now"]
    user_id: UUID = env["user_id"]
    roadmap: Roadmap = env["roadmap"]
    goal_repo: _FakeGoalRepo = env["goal_repo"]
    roadmap_repo: _FakeRoadmapRepo = env["roadmap_repo"]
    milestone_repo: _FakeMilestoneRepo = env["milestone_repo"]
    proposal_repo: _FakeProposalRepo = env["proposal_repo"]
    uow: _FakeUoW = env["uow"]
    avail_port: _MutableAvailabilityPort = env["avail_port"]
    exec_sync: _FakeExecutionSyncPort = env["exec_sync"]

    # Approve v1 and attach a DRAFT proposal
    prelim_v1 = roadmap.planning_metadata["preliminary_feasibility"]
    approve_uc = ApproveMilestonesUseCase(
        roadmap_repo=roadmap_repo,
        milestone_repo=milestone_repo,
        uow=uow,
        goal_repo=goal_repo,
        availability_query_port=avail_port,
        execution_sync_port=exec_sync,
    )
    await approve_uc.execute(
        user_id=user_id,
        roadmap_id=roadmap.id,
        confirmed_scope_proposal_version=int(prelim_v1["scope_proposal_version"]),
        accept_fit_capacity=True,
        now=now,
    )
    draft = ScheduleProposal(
        id=uuid7(),
        roadmap_id=roadmap.id,
        user_id=user_id,
        proposal_data={"tasks": []},
        status=ScheduleProposalStatus.DRAFT,
        created_at=now,
        updated_at=now,
    )
    await proposal_repo.save(draft)

    # Also add an ARCHIVED roadmap that MUST NOT be refreshed
    archived_rm = Roadmap(
        id=uuid7(),
        user_id=user_id,
        goal_id=roadmap.goal_id,
        title="Archived Roadmap",
        start_date=date(2026, 11, 2),
        target_date=date(2026, 11, 15),
        status=RoadmapStatus.ARCHIVED,
        planning_metadata={"preliminary_feasibility": dict(prelim_v1)},
        created_at=now,
        updated_at=now,
    )
    await roadmap_repo.save(archived_rm)

    # Shrink availability from 2h -> 1h Monday
    avail_port.snapshot = _tight_availability(user_id, monday_hours=1)
    outbox_repo = _FakeOutboxRepo()
    consumer = HandleAvailabilityUpdatedEventUseCase(
        roadmap_repo=roadmap_repo,
        milestone_repo=milestone_repo,
        proposal_repo=proposal_repo,
        availability_query_port=avail_port,
        outbox_repo=outbox_repo,  # type: ignore[arg-type]
        uow=uow,
        goal_repo=goal_repo,
        execution_sync_port=exec_sync,
        user_query_port=_FakeUserQueryPort(),
    )

    event_id = uuid7()
    refreshed_1 = await consumer.execute(event_id=event_id, user_id=user_id, now=now)
    assert refreshed_1 == 1
    assert await proposal_repo.get_current_draft(roadmap.id) is None

    updated_rm = await roadmap_repo.get_by_id(roadmap.id)
    assert updated_rm is not None
    assert (
        updated_rm.planning_metadata["preliminary_feasibility"]["scope_proposal_hash"]
        != prelim_v1["scope_proposal_hash"]
    )
    assert updated_rm.planning_metadata["preliminary_feasibility"]["approved_scope_version"] is None

    # Archived roadmap stayed untouched
    arch_after = await roadmap_repo.get_by_id(archived_rm.id)
    assert arch_after is not None
    assert (
        arch_after.planning_metadata["preliminary_feasibility"]["scope_proposal_hash"]
        == prelim_v1["scope_proposal_hash"]
    )

    # Re-delivering the exact same event_id MUST be idempotent (0 refreshed)
    refreshed_2 = await consumer.execute(event_id=event_id, user_id=user_id, now=now)
    assert refreshed_2 == 0
