from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

import pytest
from uuid6 import uuid7

import src.execution.public_api as execution_public_api
from src.account.public_api import (
    AvailabilitySnapshotDTO,
    LearnerProfileDTO,
    UserSnapshotDTO,
)
from src.execution.public_api import (
    ExistingScheduledTaskDTO,
    ProposedDependencySyncItemDTO,
    ProposedTaskSyncItemDTO,
    ScheduleSyncResultDTO,
)
from src.planning.application.use_cases.proposal_management_use_cases import (
    ApplyScheduleProposalUseCase,
    InitiateOverdueRecoveryUseCase,
    ReoptimizeScheduleProposalUseCase,
    UpdateScheduleProposalUseCase,
)
from src.planning.domain.exceptions.planning_exceptions import (
    PlanInfeasibleError,
)
from src.planning.domain.models.milestone import Milestone, MilestoneStatus
from src.planning.domain.models.roadmap import Roadmap, RoadmapStatus
from src.planning.domain.models.schedule import (
    OfficialSchedule,
    ScheduleProposal,
    ScheduleProposalStatus,
    ScheduleProposalType,
)
from src.planning.domain.models.schedule_block import ScheduleBlock


class _FakeUow:
    def __init__(self) -> None:
        self.committed = False
        self.events: list[Any] = []

    async def __aenter__(self) -> _FakeUow:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        return None

    def collect_events_from(self, agg: object) -> None:
        self.events.append(agg)


class _FakeRoadmapRepo:
    def __init__(self, roadmap: Roadmap) -> None:
        self._roadmap = roadmap

    async def get_by_id(self, roadmap_id: UUID) -> Roadmap | None:
        return self._roadmap if self._roadmap.id == roadmap_id else None

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

    async def count_active_by_user_id(
        self, user_id: UUID, exclude_roadmap_id: UUID | None = None
    ) -> int:
        if self._roadmap.user_id == user_id and self._roadmap.status == RoadmapStatus.ACTIVE:
            if exclude_roadmap_id is not None and self._roadmap.id == exclude_roadmap_id:
                return 0
            return 1
        return 0

    async def save(self, roadmap: Roadmap) -> Roadmap:
        self._roadmap = roadmap
        return roadmap


class _FakeMilestoneRepo:
    def __init__(self, milestones: list[Milestone]) -> None:
        self._milestones = list(milestones)

    async def list_by_roadmap_id(self, roadmap_id: UUID) -> list[Milestone]:
        return [m for m in self._milestones if m.roadmap_id == roadmap_id]

    async def save_many(self, roadmap_id: UUID, milestones: Sequence[Milestone]) -> list[Milestone]:
        self._milestones = list(milestones)
        return self._milestones

    async def approve_all_for_roadmap(self, roadmap_id: UUID, now: datetime) -> list[Milestone]:
        return self._milestones


class _FakeProposalRepo:
    def __init__(self, initial_proposals: Sequence[ScheduleProposal] = ()) -> None:
        self.proposals: dict[UUID, ScheduleProposal] = {p.id: p for p in initial_proposals}

    async def save(self, proposal: ScheduleProposal) -> ScheduleProposal:
        self.proposals[proposal.id] = proposal
        return proposal

    async def get_by_id(self, proposal_id: UUID) -> ScheduleProposal | None:
        return self.proposals.get(proposal_id)

    async def get_current_draft(self, roadmap_id: UUID) -> ScheduleProposal | None:
        for p in self.proposals.values():
            if p.roadmap_id == roadmap_id and p.status == ScheduleProposalStatus.DRAFT:
                return p
        return None

    async def list_by_roadmap_id(self, roadmap_id: UUID) -> list[ScheduleProposal]:
        rows = [p for p in self.proposals.values() if p.roadmap_id == roadmap_id]
        rows.sort(
            key=lambda p: (
                p.applied_at or datetime.min.replace(tzinfo=UTC),
                p.updated_at,
                p.created_at,
            ),
            reverse=True,
        )
        return rows

    async def discard_existing_drafts(self, roadmap_id: UUID, now: datetime) -> int:
        count = 0
        for p in self.proposals.values():
            if p.roadmap_id == roadmap_id and p.status == ScheduleProposalStatus.DRAFT:
                p.status = ScheduleProposalStatus.DISCARDED
                p.updated_at = now
                count += 1
        return count


class _FakeScheduleRepo:
    def __init__(self, schedule: OfficialSchedule | None = None) -> None:
        self._schedule = schedule

    async def get_by_roadmap_id(self, roadmap_id: UUID) -> OfficialSchedule | None:
        if self._schedule is not None and self._schedule.roadmap_id == roadmap_id:
            return self._schedule
        return None

    async def save(self, schedule: OfficialSchedule) -> OfficialSchedule:
        self._schedule = schedule
        return schedule


class _FakeBlockRepo:
    def __init__(self, blocks: Sequence[ScheduleBlock] = ()) -> None:
        self.blocks: dict[UUID, ScheduleBlock] = {b.id: b for b in blocks}

    async def get_by_id(self, block_id: UUID) -> ScheduleBlock | None:
        return self.blocks.get(block_id)

    async def get_by_schedule_id(
        self,
        official_schedule_id: UUID,
        sync_status_in: list[str] | None = None,
    ) -> list[ScheduleBlock]:
        rows = [
            b
            for b in self.blocks.values()
            if b.official_schedule_id == official_schedule_id
            and (sync_status_in is None or b.sync_status in sync_status_in)
        ]
        rows.sort(key=lambda b: (b.start_time, b.sequence_in_task))
        return rows

    async def list_by_roadmap_ids(self, roadmap_ids: Sequence[UUID]) -> list[ScheduleBlock]:
        rset = set(roadmap_ids)
        rows = [b for b in self.blocks.values() if b.roadmap_id in rset]
        rows.sort(key=lambda b: (b.start_time, b.sequence_in_task))
        return rows

    async def get_by_external_event_id(self, external_event_id: str) -> ScheduleBlock | None:
        return None

    async def save(self, block: ScheduleBlock) -> ScheduleBlock:
        self.blocks[block.id] = block
        return block

    async def save_all(self, blocks: list[ScheduleBlock]) -> list[ScheduleBlock]:
        for b in blocks:
            self.blocks[b.id] = b
        return blocks


class _FakeAvailabilityPort:
    def __init__(
        self,
        *,
        mode: str = "MODE_B",
        slots: Sequence[dict[str, Any]] | None = None,
        daily_quota_minutes: dict[str, int] | None = None,
        disabled_weekdays: tuple[str, ...] = (),
    ) -> None:
        self._snapshot = AvailabilitySnapshotDTO(
            user_id=uuid7(),
            mode=mode,
            weekly_capacity_minutes=len(slots or ()) * 120,
            daily_cap_minutes=120,
            daily_quota_minutes=daily_quota_minutes or {},
            availability_slots=tuple(slots or ()),
            disabled_weekdays=disabled_weekdays,
        )

    async def get_active_availability(self, user_id: UUID) -> AvailabilitySnapshotDTO:
        return self._snapshot

    async def get_user_availability(self, user_id: UUID) -> AvailabilitySnapshotDTO:
        return self._snapshot


class _FakeUserQueryPort:
    def __init__(self, timezone: str = "Asia/Ho_Chi_Minh", tier: str = "FREE") -> None:
        self._tz = timezone
        self._tier = tier

    async def get_user_by_id(self, user_id: UUID) -> UserSnapshotDTO:
        return UserSnapshotDTO(
            id=user_id,
            email="learner@focusflow.vn",
            full_name="PR-C Learner",
            timezone=self._tz,
            tier=self._tier,
            role="LEARNER",
            is_locked=False,
        )


class _FakeLearnerProfilePort:
    def __init__(self, *, opt_session_minutes: int = 60, estimation_bias_beta: float = 1.5) -> None:
        self._profile = LearnerProfileDTO(
            user_id=uuid7(),
            opt_session_minutes=opt_session_minutes,
            estimation_bias_beta=estimation_bias_beta,
            is_cold_start=False,
        )

    async def get_learner_profile(self, user_id: UUID) -> LearnerProfileDTO:
        return self._profile


class _FakeExecutionSyncPort:
    def __init__(
        self,
        tasks: Sequence[ExistingScheduledTaskDTO],
        dependencies: Sequence[Any] = (),
        *,
        tasks_with_sessions: set[UUID] | None = None,
    ) -> None:
        self.tasks = list(tasks)
        self.dependencies = list(dependencies)
        self.tasks_with_sessions = set(tasks_with_sessions or ())
        self.synced_tasks: list[ProposedTaskSyncItemDTO] = []
        self.synced_dependencies: list[ProposedDependencySyncItemDTO] = []

    async def get_tasks_for_roadmaps(
        self,
        roadmap_ids: Sequence[UUID],
        *,
        roadmap_target_dates: Mapping[UUID, date | None] | None = None,
    ) -> list[ExistingScheduledTaskDTO]:
        rset = set(roadmap_ids)
        return [t for t in self.tasks if t.roadmap_id in rset]

    async def get_active_roadmaps_tasks(
        self,
        user_id: UUID,
        exclude_roadmap_id: UUID | None = None,
        *,
        active_roadmap_ids: Sequence[UUID] | None = None,
        roadmap_target_dates: Mapping[UUID, date | None] | None = None,
    ) -> list[ExistingScheduledTaskDTO]:
        return []

    async def get_task_dependencies_for_roadmap(
        self,
        roadmap_id: UUID,
    ) -> list[Any]:
        return list(self.dependencies)

    async def sync_official_schedule_tasks(
        self,
        *,
        roadmap_id: UUID,
        official_schedule_id: UUID,
        proposed_tasks: Sequence[ProposedTaskSyncItemDTO],
        proposed_dependencies: Sequence[ProposedDependencySyncItemDTO],
        now: datetime,
        protected_task_ids: Sequence[UUID] = (),
    ) -> ScheduleSyncResultDTO:
        self.synced_tasks = list(proposed_tasks)
        self.synced_dependencies = list(proposed_dependencies)
        completed = [t for t in self.tasks if t.status == "COMPLETED"]
        protected = [t for t in self.tasks if t.task_id in set(protected_task_ids)]
        id_remap: dict[UUID, UUID] = {}
        for item in proposed_tasks:
            if item.task_id in self.tasks_with_sessions:
                id_remap[item.task_id] = uuid7()
        return ScheduleSyncResultDTO(
            roadmap_id=roadmap_id,
            official_schedule_id=official_schedule_id,
            preserved_completed_tasks_count=len(completed),
            replaced_tasks_count=0,
            inserted_tasks_count=len(proposed_tasks),
            affected_tasks_count=len(proposed_tasks),
            total_shifted_minutes=0,
            total_active_sessions=len(completed) + len(protected) + len(proposed_tasks),
            total_planned_minutes=sum(t.estimated_minutes for t in proposed_tasks),
        )

    async def shift_incomplete_tasks_for_domino(
        self, *, roadmap_id: UUID, shift_days: int, now: datetime
    ) -> int:
        return 0


class _FakeChangeLogPort:
    def __init__(self) -> None:
        self.logs: list[dict[str, Any]] = []

    async def record_change_log(self, **kwargs: Any) -> None:
        self.logs.append(kwargs)


class _FakeSseStore:
    def __init__(self) -> None:
        self.jobs: list[Any] = []
        self.events: list[dict[str, Any]] = []

    async def create_job(self, **kwargs: Any) -> Any:
        from src.planning.application.dtos.planning_dtos import SseJobTicketDTO

        t = SseJobTicketDTO(
            job_id=kwargs["job_id"],
            reservation_id=kwargs["reservation_id"],
            roadmap_id=kwargs["roadmap_id"],
            job_type=kwargs["job_type"],
            status="QUEUED",
            stream_url=f"/api/v1/planning/jobs/{kwargs['job_id']}/stream",
        )
        self.jobs.append(t)
        return t

    async def append_event(self, **kwargs: Any) -> None:
        self.events.append(kwargs)


def _slots_mon_wed_fri() -> list[dict[str, Any]]:
    return [
        {
            "day_of_week": d,
            "start_time": "19:00",
            "end_time": "21:00",
            "end_day_offset": 0,
            "is_active": True,
        }
        for d in ("monday", "wednesday", "friday")
    ]


@pytest.mark.asyncio
async def test_def02_reoptimize_preserves_metadata_dependencies_completed_coverage_and_no_beta_double_scale() -> (
    None
):
    """DEF-02: Reoptimize MUST preserve metadata, DAG dependencies, avoid beta^2, and Apply MUST count COMPLETED coverage."""
    uid = uuid7()
    gid = uuid7()
    rid = uuid7()
    m1_id = uuid7()
    m2_id = uuid7()
    t0_id = uuid7()  # COMPLETED in M1
    t1_id = uuid7()  # TODO in M2
    t2_id = uuid7()  # TODO in M2, depends on T1
    now = datetime(2026, 11, 10, 3, 0, tzinfo=UTC)  # 10:00 +07:00

    roadmap = Roadmap(
        id=rid,
        user_id=uid,
        goal_id=gid,
        title="PR-C Reoptimize Roadmap",
        status=RoadmapStatus.ACTIVE,
        start_date=date(2026, 11, 2),
        target_date=date(2026, 11, 30),
        created_at=now,
        updated_at=now,
    )
    m1 = Milestone(
        id=m1_id,
        roadmap_id=rid,
        sequence_order=1,
        title="Chặng 1: Nền tảng Python",
        learning_outcomes=["Nắm biến và kiểu dữ liệu"],
        completion_criteria="Pass quiz Python",
        estimated_effort_minutes=90,
        required_concepts=["py-syntax-variables"],
        status=MilestoneStatus.APPROVED,
        created_at=now,
        updated_at=now,
    )
    m2 = Milestone(
        id=m2_id,
        roadmap_id=rid,
        sequence_order=2,
        title="Chặng 2: Luồng điều khiển",
        learning_outcomes=["Viết hàm và vòng lặp", "Kiểm thử đơn vị"],
        completion_criteria="Pass 5 bài tập hàm",
        estimated_effort_minutes=180,
        required_concepts=["py-control-flow-functions"],
        status=MilestoneStatus.APPROVED,
        created_at=now,
        updated_at=now,
    )
    schedule = OfficialSchedule(
        id=uuid7(),
        roadmap_id=rid,
        total_sessions=3,
        total_planned_minutes=270,
        activated_at=now,
        created_at=now,
        updated_at=now,
    )
    sample_res_1 = {
        "resource_id": "res-py-1",
        "title": "Python Docs: Variables",
        "url": "https://docs.python.org/3/",
        "type": "DOCS",
        "resource_type": "DOCS",
        "description": "Tài liệu biến Python",
    }
    sample_res_2 = {
        "resource_id": "res-py-2",
        "title": "Python Docs: Functions",
        "url": "https://docs.python.org/3/tutorial/controlflow.html",
        "type": "DOCS",
        "resource_type": "DOCS",
        "description": "Tài liệu hàm Python",
    }
    hist_applied = ScheduleProposal(
        id=uuid7(),
        roadmap_id=rid,
        user_id=uid,
        proposal_type=ScheduleProposalType.INITIAL_SCHEDULE,
        status=ScheduleProposalStatus.APPLIED,
        applied_at=now - timedelta(days=5),
        created_at=now - timedelta(days=5),
        updated_at=now - timedelta(days=5),
        proposal_data={
            "tasks": [
                {
                    "task_id": str(t0_id),
                    "milestone_id": str(m1_id),
                    "title": "Bài 0: Biến và kiểu dữ liệu",
                    "description": "Học cú pháp biến cơ bản",
                    "learning_objective": "Hiểu biến và kiểu cơ bản",
                    "completion_criteria": "Hoàn thành bài quiz 10 câu",
                    "covered_outcome_ids": ["M1-O1"],
                    "concept_ids": ["py-syntax-variables"],
                    "learning_resources": [sample_res_1],
                    "task_type": "CONCEPT",
                    "is_non_splittable": False,
                    "estimated_minutes": 90,
                },
                {
                    "task_id": str(t1_id),
                    "milestone_id": str(m2_id),
                    "title": "Bài 1: Vòng lặp & Điều kiện",
                    "description": "Luyện viết vòng lặp",
                    "learning_objective": "Thành thạo for/while/if",
                    "completion_criteria": "Pass 3 bài tập",
                    "covered_outcome_ids": ["M2-O1"],
                    "concept_ids": ["py-control-flow-functions"],
                    "learning_resources": [sample_res_2],
                    "task_type": "PRACTICE",
                    "is_non_splittable": False,
                    "estimated_minutes": 90,
                },
                {
                    "task_id": str(t2_id),
                    "milestone_id": str(m2_id),
                    "title": "Bài 2: Kiểm thử hàm",
                    "description": "Viết unit test cho hàm",
                    "learning_objective": "Viết unit test đầy đủ",
                    "completion_criteria": "Đạt 100% pass pytest",
                    "covered_outcome_ids": ["M2-O2"],
                    "concept_ids": ["py-control-flow-functions"],
                    "learning_resources": [sample_res_2],
                    "task_type": "PRACTICE",
                    "is_non_splittable": True,
                    "estimated_minutes": 90,
                },
            ],
            "dependencies": [
                {"predecessor_id": str(t0_id), "successor_id": str(t1_id), "is_mandatory": True},
                {"predecessor_id": str(t1_id), "successor_id": str(t2_id), "is_mandatory": True},
            ],
        },
    )

    existing_tasks = [
        ExistingScheduledTaskDTO(
            task_id=t0_id,
            roadmap_id=rid,
            milestone_id=m1_id,
            title="Bài 0: Biến và kiểu dữ liệu",
            description="Học cú pháp biến cơ bản",
            concept_id="py-syntax-variables",
            learning_resources=(sample_res_1,),
            estimated_minutes=90,
            scheduled_date=date(2026, 11, 2),
            scheduled_start=datetime(2026, 11, 2, 12, 0, tzinfo=UTC),
            scheduled_end=datetime(2026, 11, 2, 13, 30, tzinfo=UTC),
            status="COMPLETED",
        ),
        ExistingScheduledTaskDTO(
            task_id=t1_id,
            roadmap_id=rid,
            milestone_id=m2_id,
            title="Bài 1: Vòng lặp & Điều kiện",
            description="Luyện viết vòng lặp",
            concept_id="py-control-flow-functions",
            learning_resources=(sample_res_2,),
            estimated_minutes=90,
            scheduled_date=date(2026, 11, 4),
            scheduled_start=datetime(2026, 11, 4, 12, 0, tzinfo=UTC),
            scheduled_end=datetime(2026, 11, 4, 13, 30, tzinfo=UTC),
            status="TODO",
        ),
        ExistingScheduledTaskDTO(
            task_id=t2_id,
            roadmap_id=rid,
            milestone_id=m2_id,
            title="Bài 2: Kiểm thử hàm",
            description="Viết unit test cho hàm",
            concept_id="py-control-flow-functions",
            learning_resources=(sample_res_2,),
            estimated_minutes=90,
            scheduled_date=date(2026, 11, 6),
            scheduled_start=datetime(2026, 11, 6, 12, 0, tzinfo=UTC),
            scheduled_end=datetime(2026, 11, 6, 13, 30, tzinfo=UTC),
            status="TODO",
        ),
    ]
    dep_cls = getattr(execution_public_api, "ExistingTaskDependencyDTO")
    existing_deps = [
        dep_cls(predecessor_id=t0_id, successor_id=t1_id, is_mandatory=True),
        dep_cls(predecessor_id=t1_id, successor_id=t2_id, is_mandatory=True),
    ]

    exec_port = _FakeExecutionSyncPort(existing_tasks, existing_deps)
    proposal_repo = _FakeProposalRepo([hist_applied])
    roadmap_repo = _FakeRoadmapRepo(roadmap)
    milestone_repo = _FakeMilestoneRepo([m1, m2])
    schedule_repo = _FakeScheduleRepo(schedule)
    block_repo = _FakeBlockRepo()
    avail_port = _FakeAvailabilityPort(mode="MODE_B", slots=_slots_mon_wed_fri())
    user_port = _FakeUserQueryPort()
    profile_port = _FakeLearnerProfilePort(opt_session_minutes=60, estimation_bias_beta=1.5)
    uow = _FakeUow()

    reopt_view = await ReoptimizeScheduleProposalUseCase(
        roadmap_repo=roadmap_repo,  # type: ignore[arg-type]
        milestone_repo=milestone_repo,  # type: ignore[arg-type]
        proposal_repo=proposal_repo,  # type: ignore[arg-type]
        availability_query_port=avail_port,  # type: ignore[arg-type]
        execution_sync_port=exec_port,  # type: ignore[arg-type]
        uow=uow,  # type: ignore[arg-type]
        learner_profile_port=profile_port,  # type: ignore[arg-type]
        user_query_port=user_port,  # type: ignore[arg-type]
        block_repo=block_repo,  # type: ignore[arg-type]
        schedule_repo=schedule_repo,  # type: ignore[arg-type]
    ).execute(user_id=uid, roadmap_id=rid, now=now)

    pdata = reopt_view.proposal.proposal_data
    tasks_out = pdata["tasks"]
    # T0 (COMPLETED) MUST NOT be recreated as TODO in proposal_data["tasks"]
    assert [t["task_id"] for t in tasks_out] == [str(t1_id), str(t2_id)]
    # No double-scaling of estimation_bias_beta (remains 90, NOT 135)
    assert all(t["estimated_minutes"] == 90 for t in tasks_out)
    # Metadata preserved
    t1_out = tasks_out[0]
    assert t1_out["learning_objective"] == "Thành thạo for/while/if"
    assert t1_out["completion_criteria"] == "Pass 3 bài tập"
    assert t1_out["covered_outcome_ids"] == ["M2-O1"]
    assert t1_out["concept_ids"] == ["py-control-flow-functions"]
    assert t1_out["learning_resources"] == [sample_res_2]
    assert t1_out["task_type"] == "PRACTICE"
    assert tasks_out[1]["is_non_splittable"] is True
    # Dependencies preserved (NEVER hardcoded [])
    dep_pairs = {(d["predecessor_id"], d["successor_id"]) for d in pdata["dependencies"]}
    assert (str(t1_id), str(t2_id)) in dep_pairs
    assert (str(t0_id), str(t1_id)) in dep_pairs
    # Feasibility & completeness set
    assert "feasibility" in pdata
    assert pdata["schedule_completeness_status"] == "FULL"

    # UpdateScheduleProposalUseCase MUST succeed even though M1 only has COMPLETED T0
    updated_view = await UpdateScheduleProposalUseCase(
        roadmap_repo=roadmap_repo,  # type: ignore[arg-type]
        milestone_repo=milestone_repo,  # type: ignore[arg-type]
        proposal_repo=proposal_repo,  # type: ignore[arg-type]
        availability_query_port=avail_port,  # type: ignore[arg-type]
        execution_sync_port=exec_port,  # type: ignore[arg-type]
        uow=uow,  # type: ignore[arg-type]
        user_query_port=user_port,  # type: ignore[arg-type]
        block_repo=block_repo,  # type: ignore[arg-type]
    ).execute(
        user_id=uid,
        roadmap_id=rid,
        proposal_id=reopt_view.proposal.id,
        tasks=tasks_out,
        dependencies=pdata["dependencies"],
        reject_invalid=True,
        now=now,
    )
    assert updated_view.is_valid

    # ApplyScheduleProposalUseCase MUST succeed without 422 MILESTONE_WITHOUT_TASKS on M1
    apply_res = await ApplyScheduleProposalUseCase(
        roadmap_repo=roadmap_repo,  # type: ignore[arg-type]
        milestone_repo=milestone_repo,  # type: ignore[arg-type]
        proposal_repo=proposal_repo,  # type: ignore[arg-type]
        schedule_repo=schedule_repo,  # type: ignore[arg-type]
        block_repo=block_repo,  # type: ignore[arg-type]
        availability_query_port=avail_port,  # type: ignore[arg-type]
        execution_sync_port=exec_port,  # type: ignore[arg-type]
        schedule_change_log_port=_FakeChangeLogPort(),  # type: ignore[arg-type]
        uow=uow,  # type: ignore[arg-type]
        user_query_port=user_port,  # type: ignore[arg-type]
    ).execute(user_id=uid, roadmap_id=rid, proposal_id=reopt_view.proposal.id, now=now)
    assert apply_res.proposal.status == ScheduleProposalStatus.APPLIED
    # Concept & learning_resources propagated onto ProposedTaskSyncItemDTO
    synced_by_id = {item.task_id: item for item in exec_port.synced_tasks}
    assert synced_by_id[t1_id].concept_id == "py-control-flow-functions"
    assert len(synced_by_id[t1_id].learning_resources) == 1
    assert synced_by_id[t1_id].learning_resources[0]["resource_id"] == "res-py-2"


@pytest.mark.asyncio
async def test_def02_multi_block_protected_task_preserved_verbatim_and_blocks_respected() -> None:
    """Multi-block protected task MUST keep exact scheduled_start/end & multi-block schedule_blocks verbatim."""
    uid = uuid7()
    gid = uuid7()
    rid = uuid7()
    m1_id = uuid7()
    sched_id = uuid7()
    t_prot_id = uuid7()  # Protected task split into 2 blocks (Mon 60m + Wed 30m)
    t_move_id = uuid7()  # Overdue task depending on t_prot_id
    now = datetime(2026, 11, 10, 3, 0, tzinfo=UTC)  # Tue 10:00 +07:00

    roadmap = Roadmap(
        id=rid,
        user_id=uid,
        goal_id=gid,
        title="Protected Multi-Block Roadmap",
        status=RoadmapStatus.ACTIVE,
        start_date=date(2026, 11, 2),
        target_date=date(2026, 11, 25),
        created_at=now,
        updated_at=now,
    )
    m1 = Milestone(
        id=m1_id,
        roadmap_id=rid,
        sequence_order=1,
        title="Chặng 1",
        learning_outcomes=["Outcome 1"],
        completion_criteria="Done",
        estimated_effort_minutes=150,
        status=MilestoneStatus.APPROVED,
        created_at=now,
        updated_at=now,
    )
    schedule = OfficialSchedule(
        id=sched_id,
        roadmap_id=rid,
        total_sessions=3,
        total_planned_minutes=150,
        activated_at=now,
        created_at=now,
        updated_at=now,
    )

    b1_start = datetime(2026, 11, 11, 19, 0, tzinfo=UTC)  # Wed Nov 11
    b1_end = datetime(2026, 11, 11, 20, 0, tzinfo=UTC)
    b2_start = datetime(2026, 11, 13, 19, 0, tzinfo=UTC)  # Fri Nov 13
    b2_end = datetime(2026, 11, 13, 19, 30, tzinfo=UTC)
    # Note: use Asia/Ho_Chi_Minh local times matching 19:00+07:00 = 12:00 UTC
    b1_start = datetime(2026, 11, 11, 12, 0, tzinfo=UTC)
    b1_end = datetime(2026, 11, 11, 13, 0, tzinfo=UTC)
    b2_start = datetime(2026, 11, 13, 12, 0, tzinfo=UTC)
    b2_end = datetime(2026, 11, 13, 12, 30, tzinfo=UTC)

    prot_b1 = ScheduleBlock(
        id=uuid7(),
        roadmap_id=rid,
        official_schedule_id=sched_id,
        task_id=t_prot_id,
        sequence_in_task=1,
        block_date=date(2026, 11, 11),
        start_time=b1_start,
        end_time=b1_end,
        scheduled_duration_minutes=60,
        is_protected=True,
        status="PLANNED",
        created_at=now,
        updated_at=now,
    )
    prot_b2 = ScheduleBlock(
        id=uuid7(),
        roadmap_id=rid,
        official_schedule_id=sched_id,
        task_id=t_prot_id,
        sequence_in_task=2,
        block_date=date(2026, 11, 13),
        start_time=b2_start,
        end_time=b2_end,
        scheduled_duration_minutes=30,
        is_protected=True,
        status="PLANNED",
        created_at=now,
        updated_at=now,
    )

    existing_tasks = [
        ExistingScheduledTaskDTO(
            task_id=t_prot_id,
            roadmap_id=rid,
            milestone_id=m1_id,
            title="Nhiệm vụ bảo vệ 2 phiên",
            description="Phiên học cố định",
            estimated_minutes=90,
            scheduled_date=date(2026, 11, 11),
            scheduled_start=b1_start,
            scheduled_end=b2_end,
            status="TODO",
        ),
        ExistingScheduledTaskDTO(
            task_id=t_move_id,
            roadmap_id=rid,
            milestone_id=m1_id,
            title="Nhiệm vụ cần xếp sau protected",
            description="Xếp sau khi protected kết thúc",
            estimated_minutes=60,
            scheduled_date=date(2026, 11, 4),  # overdue
            scheduled_start=datetime(2026, 11, 4, 12, 0, tzinfo=UTC),
            scheduled_end=datetime(2026, 11, 4, 13, 0, tzinfo=UTC),
            status="TODO",
        ),
    ]
    dep_cls = getattr(execution_public_api, "ExistingTaskDependencyDTO")
    existing_deps = [
        dep_cls(predecessor_id=t_prot_id, successor_id=t_move_id, is_mandatory=True),
    ]

    exec_port = _FakeExecutionSyncPort(existing_tasks, existing_deps)
    proposal_repo = _FakeProposalRepo()
    roadmap_repo = _FakeRoadmapRepo(roadmap)
    milestone_repo = _FakeMilestoneRepo([m1])
    schedule_repo = _FakeScheduleRepo(schedule)
    block_repo = _FakeBlockRepo([prot_b1, prot_b2])
    avail_port = _FakeAvailabilityPort(mode="MODE_B", slots=_slots_mon_wed_fri())
    user_port = _FakeUserQueryPort()
    uow = _FakeUow()

    reopt_view = await ReoptimizeScheduleProposalUseCase(
        roadmap_repo=roadmap_repo,  # type: ignore[arg-type]
        milestone_repo=milestone_repo,  # type: ignore[arg-type]
        proposal_repo=proposal_repo,  # type: ignore[arg-type]
        availability_query_port=avail_port,  # type: ignore[arg-type]
        execution_sync_port=exec_port,  # type: ignore[arg-type]
        uow=uow,  # type: ignore[arg-type]
        user_query_port=user_port,  # type: ignore[arg-type]
        block_repo=block_repo,  # type: ignore[arg-type]
        schedule_repo=schedule_repo,  # type: ignore[arg-type]
    ).execute(user_id=uid, roadmap_id=rid, now=now)

    pdata = reopt_view.proposal.proposal_data
    prot_blocks_out = [b for b in pdata["schedule_blocks"] if b["task_id"] == str(t_prot_id)]
    assert len(prot_blocks_out) == 2
    assert [b["sequence_in_task"] for b in prot_blocks_out] == [1, 2]
    assert prot_blocks_out[0]["is_protected"] is True
    assert prot_blocks_out[1]["is_protected"] is True

    move_task_out = next(t for t in pdata["tasks"] if t["task_id"] == str(t_move_id))
    # Must start on or after b2_end (2026-11-13 19:30+07:00), never overlap b1 or b2
    assert datetime.fromisoformat(move_task_out["scheduled_start"]) >= b2_end

    # Apply MUST succeed without PROTECTED_SESSION_CHANGED
    apply_res = await ApplyScheduleProposalUseCase(
        roadmap_repo=roadmap_repo,  # type: ignore[arg-type]
        milestone_repo=milestone_repo,  # type: ignore[arg-type]
        proposal_repo=proposal_repo,  # type: ignore[arg-type]
        schedule_repo=schedule_repo,  # type: ignore[arg-type]
        block_repo=block_repo,  # type: ignore[arg-type]
        availability_query_port=avail_port,  # type: ignore[arg-type]
        execution_sync_port=exec_port,  # type: ignore[arg-type]
        schedule_change_log_port=_FakeChangeLogPort(),  # type: ignore[arg-type]
        uow=uow,  # type: ignore[arg-type]
        user_query_port=user_port,  # type: ignore[arg-type]
    ).execute(user_id=uid, roadmap_id=rid, proposal_id=reopt_view.proposal.id, now=now)
    assert apply_res.proposal.status == ScheduleProposalStatus.APPLIED


@pytest.mark.asyncio
async def test_def02_overdue_recovery_pins_unaffected_future_tasks_and_cascades_blocked_dependents() -> (
    None
):
    """InitiateOverdueRecoveryUseCase MUST pin unaffected future tasks & cascade only impacted dependents."""
    uid = uuid7()
    gid = uuid7()
    rid = uuid7()
    m1_id = uuid7()
    sched_id = uuid7()
    t_overdue_id = uuid7()
    t_dep_future_id = uuid7()
    t_indep_future_id = uuid7()
    # Today: Wednesday 2026-11-11 10:00+07:00 (03:00 UTC)
    now = datetime(2026, 11, 11, 3, 0, tzinfo=UTC)

    roadmap = Roadmap(
        id=rid,
        user_id=uid,
        goal_id=gid,
        title="Overdue Recovery Selective Pinning",
        status=RoadmapStatus.ACTIVE,
        start_date=date(2026, 11, 2),
        target_date=date(2026, 11, 25),
        created_at=now,
        updated_at=now,
    )
    m1 = Milestone(
        id=m1_id,
        roadmap_id=rid,
        sequence_order=1,
        title="Chặng 1",
        learning_outcomes=["Outcome 1"],
        completion_criteria="Done",
        estimated_effort_minutes=180,
        status=MilestoneStatus.APPROVED,
        created_at=now,
        updated_at=now,
    )
    schedule = OfficialSchedule(
        id=sched_id,
        roadmap_id=rid,
        total_sessions=3,
        total_planned_minutes=180,
        activated_at=now,
        created_at=now,
        updated_at=now,
    )

    # T_dep_future was scheduled TODAY (Wed Nov 11 19:00-20:00+07:00), BEFORE T_overdue can run + finish?
    # Actually T_overdue is 60m and T_dep_future is at Wed Nov 11 19:00-20:00+07:00!
    # Because Wed Nov 11 19:00-20:00 is occupied by T_dep_future (and say Wed only has 19:00-20:00? No, Mon/Wed/Fri 19:00-21:00 -> T_overdue can't fit BEFORE 19:00 Wed!),
    # so T_overdue -> T_dep_future forces T_dep_future to cascade!
    # Meanwhile T_indep_future is pinned at Fri Nov 13 19:00-20:00+07:00 and MUST NOT move!
    dep_start = datetime(2026, 11, 11, 12, 0, tzinfo=UTC)  # Wed Nov 11 19:00+07:00
    dep_end = datetime(2026, 11, 11, 13, 0, tzinfo=UTC)
    indep_start = datetime(2026, 11, 13, 12, 0, tzinfo=UTC)  # Fri Nov 13 19:00+07:00
    indep_end = datetime(2026, 11, 13, 13, 0, tzinfo=UTC)

    existing_tasks = [
        ExistingScheduledTaskDTO(
            task_id=t_overdue_id,
            roadmap_id=rid,
            milestone_id=m1_id,
            title="Quá hạn từ thứ Hai",
            estimated_minutes=60,
            scheduled_date=date(2026, 11, 9),
            scheduled_start=datetime(2026, 11, 9, 12, 0, tzinfo=UTC),
            scheduled_end=datetime(2026, 11, 9, 13, 0, tzinfo=UTC),
            status="TODO",
        ),
        ExistingScheduledTaskDTO(
            task_id=t_dep_future_id,
            roadmap_id=rid,
            milestone_id=m1_id,
            title="Phụ thuộc nhiệm vụ quá hạn",
            estimated_minutes=60,
            scheduled_date=date(2026, 11, 11),
            scheduled_start=dep_start,
            scheduled_end=dep_end,
            status="TODO",
        ),
        ExistingScheduledTaskDTO(
            task_id=t_indep_future_id,
            roadmap_id=rid,
            milestone_id=m1_id,
            title="Tương lai độc lập giữ nguyên",
            estimated_minutes=60,
            scheduled_date=date(2026, 11, 13),
            scheduled_start=indep_start,
            scheduled_end=indep_end,
            status="TODO",
        ),
    ]
    dep_cls = getattr(execution_public_api, "ExistingTaskDependencyDTO")
    existing_deps = [
        dep_cls(predecessor_id=t_overdue_id, successor_id=t_dep_future_id, is_mandatory=True),
    ]
    blocks = [
        ScheduleBlock(
            id=uuid7(),
            roadmap_id=rid,
            official_schedule_id=sched_id,
            task_id=t_dep_future_id,
            sequence_in_task=1,
            block_date=date(2026, 11, 11),
            start_time=dep_start,
            end_time=dep_end,
            scheduled_duration_minutes=60,
            is_protected=False,
            status="PLANNED",
            created_at=now,
            updated_at=now,
        ),
        ScheduleBlock(
            id=uuid7(),
            roadmap_id=rid,
            official_schedule_id=sched_id,
            task_id=t_indep_future_id,
            sequence_in_task=1,
            block_date=date(2026, 11, 13),
            start_time=indep_start,
            end_time=indep_end,
            scheduled_duration_minutes=60,
            is_protected=False,
            status="PLANNED",
            created_at=now,
            updated_at=now,
        ),
    ]

    exec_port = _FakeExecutionSyncPort(existing_tasks, existing_deps)
    proposal_repo = _FakeProposalRepo()
    sse_store = _FakeSseStore()
    ticket = await InitiateOverdueRecoveryUseCase(
        roadmap_repo=_FakeRoadmapRepo(roadmap),  # type: ignore[arg-type]
        milestone_repo=_FakeMilestoneRepo([m1]),  # type: ignore[arg-type]
        proposal_repo=proposal_repo,  # type: ignore[arg-type]
        availability_query_port=_FakeAvailabilityPort(mode="MODE_B", slots=_slots_mon_wed_fri()),  # type: ignore[arg-type]
        execution_sync_port=exec_port,  # type: ignore[arg-type]
        sse_job_store=sse_store,  # type: ignore[arg-type]
        uow=_FakeUow(),  # type: ignore[arg-type]
        user_query_port=_FakeUserQueryPort(),  # type: ignore[arg-type]
        block_repo=_FakeBlockRepo(blocks),  # type: ignore[arg-type]
        schedule_repo=_FakeScheduleRepo(schedule),  # type: ignore[arg-type]
    ).execute(user_id=uid, roadmap_id=rid, now=now)

    assert ticket.status == "COMPLETED"
    draft = await proposal_repo.get_current_draft(rid)
    assert draft is not None
    by_id = {t["task_id"]: t for t in draft.proposal_data["tasks"]}

    # Independent future task MUST stay pinned at its exact original slot
    assert by_id[str(t_indep_future_id)]["scheduled_date"] == "2026-11-13"
    assert datetime.fromisoformat(by_id[str(t_indep_future_id)]["scheduled_start"]) == indep_start
    assert datetime.fromisoformat(by_id[str(t_indep_future_id)]["scheduled_end"]) == indep_end

    # Overdue task moved to >= today, and dependent cascaded so pred.end <= succ.start
    overdue_start = datetime.fromisoformat(by_id[str(t_overdue_id)]["scheduled_start"])
    overdue_end = datetime.fromisoformat(by_id[str(t_overdue_id)]["scheduled_end"])
    dep_new_start = datetime.fromisoformat(by_id[str(t_dep_future_id)]["scheduled_start"])
    assert overdue_start.date() >= date(2026, 11, 11)
    assert overdue_end <= dep_new_start


@pytest.mark.asyncio
async def test_def02_reoptimize_partial_allowed_and_infeasible_blocked() -> None:
    """Reoptimize MUST set feasibility/completeness, allow PARTIAL (>=25%), and block INFEASIBLE."""
    uid = uuid7()
    gid = uuid7()
    rid = uuid7()
    m1_id = uuid7()
    t1_id = uuid7()
    t2_id = uuid7()
    now = datetime(2026, 11, 10, 3, 0, tzinfo=UTC)

    roadmap = Roadmap(
        id=rid,
        user_id=uid,
        goal_id=gid,
        title="Partial vs Infeasible Reoptimize",
        status=RoadmapStatus.ACTIVE,
        start_date=date(2026, 11, 2),
        target_date=date(2026, 11, 12),  # Only 1 Wednesday (Nov 11) -> 60m capacity
        created_at=now,
        updated_at=now,
    )
    m1 = Milestone(
        id=m1_id,
        roadmap_id=rid,
        sequence_order=1,
        title="Chặng 1",
        learning_outcomes=["O1"],
        completion_criteria="Done",
        estimated_effort_minutes=120,
        status=MilestoneStatus.APPROVED,
        created_at=now,
        updated_at=now,
    )
    tasks = [
        ExistingScheduledTaskDTO(
            task_id=t1_id,
            roadmap_id=rid,
            milestone_id=m1_id,
            title="Task A",
            estimated_minutes=60,
            scheduled_date=date(2026, 11, 4),
            scheduled_start=datetime(2026, 11, 4, 12, 0, tzinfo=UTC),
            scheduled_end=datetime(2026, 11, 4, 13, 0, tzinfo=UTC),
            status="TODO",
        ),
        ExistingScheduledTaskDTO(
            task_id=t2_id,
            roadmap_id=rid,
            milestone_id=m1_id,
            title="Task B",
            estimated_minutes=60,
            scheduled_date=date(2026, 11, 4),
            scheduled_start=datetime(2026, 11, 4, 13, 0, tzinfo=UTC),
            scheduled_end=datetime(2026, 11, 4, 14, 0, tzinfo=UTC),
            status="TODO",
        ),
    ]
    partial_slot = [
        {
            "day_of_week": "wednesday",
            "start_time": "19:00",
            "end_time": "20:00",
            "end_day_offset": 0,
            "is_active": True,
        }
    ]
    proposal_repo = _FakeProposalRepo()
    view = await ReoptimizeScheduleProposalUseCase(
        roadmap_repo=_FakeRoadmapRepo(roadmap),  # type: ignore[arg-type]
        milestone_repo=_FakeMilestoneRepo([m1]),  # type: ignore[arg-type]
        proposal_repo=proposal_repo,  # type: ignore[arg-type]
        availability_query_port=_FakeAvailabilityPort(mode="MODE_B", slots=partial_slot),  # type: ignore[arg-type]
        execution_sync_port=_FakeExecutionSyncPort(tasks),  # type: ignore[arg-type]
        uow=_FakeUow(),  # type: ignore[arg-type]
        user_query_port=_FakeUserQueryPort(),  # type: ignore[arg-type]
    ).execute(user_id=uid, roadmap_id=rid, now=now)

    assert view.proposal.proposal_data["schedule_completeness_status"] == "PARTIAL"
    assert view.proposal.proposal_data["feasibility"]["status"] == "PARTIAL"
    assert view.proposal.proposal_data["scheduled_tasks_count"] == 1
    assert view.proposal.proposal_data["unscheduled_tasks_count"] == 1

    # Zero capacity -> MUST block with PlanInfeasibleError
    with pytest.raises(PlanInfeasibleError):
        await ReoptimizeScheduleProposalUseCase(
            roadmap_repo=_FakeRoadmapRepo(roadmap),  # type: ignore[arg-type]
            milestone_repo=_FakeMilestoneRepo([m1]),  # type: ignore[arg-type]
            proposal_repo=proposal_repo,  # type: ignore[arg-type]
            availability_query_port=_FakeAvailabilityPort(
                mode="MODE_B",
                slots=[],
                disabled_weekdays=(
                    "monday",
                    "tuesday",
                    "wednesday",
                    "thursday",
                    "friday",
                    "saturday",
                    "sunday",
                ),
            ),  # type: ignore[arg-type]
            execution_sync_port=_FakeExecutionSyncPort(tasks),  # type: ignore[arg-type]
            uow=_FakeUow(),  # type: ignore[arg-type]
            user_query_port=_FakeUserQueryPort(),  # type: ignore[arg-type]
        ).execute(user_id=uid, roadmap_id=rid, now=now)


@pytest.mark.asyncio
async def test_def02_reoptimize_falls_back_by_title_and_existing_task_dto_without_history() -> None:
    """When task_id was rotated (no id match) or no historical proposal exists, recover metadata cleanly."""
    uid = uuid7()
    gid = uuid7()
    rid = uuid7()
    m1_id = uuid7()
    m2_id = uuid7()
    old_t1_id = uuid7()
    rotated_t1_id = uuid7()
    t2_id = uuid7()
    now = datetime(2026, 11, 10, 3, 0, tzinfo=UTC)

    roadmap = Roadmap(
        id=rid,
        user_id=uid,
        goal_id=gid,
        title="Fallback Metadata Roadmap",
        status=RoadmapStatus.ACTIVE,
        start_date=date(2026, 11, 2),
        target_date=date(2026, 11, 30),
        created_at=now,
        updated_at=now,
    )
    m1 = Milestone(
        id=m1_id,
        roadmap_id=rid,
        sequence_order=1,
        title="Chặng 1",
        learning_outcomes=["O1"],
        completion_criteria="Done M1",
        estimated_effort_minutes=60,
        required_concepts=["py-syntax-variables"],
        status=MilestoneStatus.APPROVED,
        created_at=now,
        updated_at=now,
    )
    m2 = Milestone(
        id=m2_id,
        roadmap_id=rid,
        sequence_order=2,
        title="Chặng 2",
        learning_outcomes=["O2"],
        completion_criteria="Done M2",
        estimated_effort_minutes=60,
        required_concepts=["py-control-flow-functions"],
        status=MilestoneStatus.APPROVED,
        created_at=now,
        updated_at=now,
    )
    hist_applied = ScheduleProposal(
        id=uuid7(),
        roadmap_id=rid,
        user_id=uid,
        proposal_type=ScheduleProposalType.INITIAL_SCHEDULE,
        status=ScheduleProposalStatus.APPLIED,
        applied_at=now - timedelta(days=3),
        created_at=now - timedelta(days=3),
        updated_at=now - timedelta(days=3),
        proposal_data={
            "tasks": [
                {
                    "task_id": str(old_t1_id),
                    "milestone_id": str(m1_id),
                    "title": "Bài   xoay UUID",
                    "learning_objective": "Mục tiêu khôi phục qua tiêu đề",
                    "completion_criteria": "Tiêu chí khôi phục qua tiêu đề",
                    "covered_outcome_ids": ["M1-O1"],
                    "concept_ids": ["py-syntax-variables"],
                    "estimated_minutes": 60,
                }
            ]
        },
    )
    dto_res = {
        "resource_id": "res-dto-1",
        "title": "Python Control Flow",
        "url": "https://docs.python.org/3/",
        "type": "DOCS",
    }
    tasks = [
        ExistingScheduledTaskDTO(
            task_id=rotated_t1_id,
            roadmap_id=rid,
            milestone_id=m1_id,
            title="Bài xoay UUID",
            estimated_minutes=60,
            scheduled_date=date(2026, 11, 4),
            scheduled_start=datetime(2026, 11, 4, 12, 0, tzinfo=UTC),
            scheduled_end=datetime(2026, 11, 4, 13, 0, tzinfo=UTC),
            status="TODO",
        ),
        ExistingScheduledTaskDTO(
            task_id=t2_id,
            roadmap_id=rid,
            milestone_id=m2_id,
            title="Bài không có lịch sử proposal",
            description="Mô tả từ TaskORM",
            concept_id="py-control-flow-functions",
            learning_resources=(dto_res,),
            estimated_minutes=60,
            scheduled_date=date(2026, 11, 6),
            scheduled_start=datetime(2026, 11, 6, 12, 0, tzinfo=UTC),
            scheduled_end=datetime(2026, 11, 6, 13, 0, tzinfo=UTC),
            status="TODO",
        ),
    ]
    view = await ReoptimizeScheduleProposalUseCase(
        roadmap_repo=_FakeRoadmapRepo(roadmap),  # type: ignore[arg-type]
        milestone_repo=_FakeMilestoneRepo([m1, m2]),  # type: ignore[arg-type]
        proposal_repo=_FakeProposalRepo([hist_applied]),  # type: ignore[arg-type]
        availability_query_port=_FakeAvailabilityPort(mode="MODE_B", slots=_slots_mon_wed_fri()),  # type: ignore[arg-type]
        execution_sync_port=_FakeExecutionSyncPort(tasks),  # type: ignore[arg-type]
        uow=_FakeUow(),  # type: ignore[arg-type]
        user_query_port=_FakeUserQueryPort(),  # type: ignore[arg-type]
    ).execute(user_id=uid, roadmap_id=rid, now=now)

    by_id = {t["task_id"]: t for t in view.proposal.proposal_data["tasks"]}
    # Matched via (milestone_id, normalized_title)
    assert by_id[str(rotated_t1_id)]["learning_objective"] == "Mục tiêu khôi phục qua tiêu đề"
    assert by_id[str(rotated_t1_id)]["covered_outcome_ids"] == ["M1-O1"]
    # Fallback via ExistingScheduledTaskDTO + Milestone
    assert by_id[str(t2_id)]["learning_objective"] == "Mô tả từ TaskORM"
    assert by_id[str(t2_id)]["completion_criteria"] == "Done M2"
    assert by_id[str(t2_id)]["covered_outcome_ids"] == ["M2-O1"]
    assert by_id[str(t2_id)]["concept_ids"] == ["py-control-flow-functions"]
    assert by_id[str(t2_id)]["learning_resources"] == [dto_res]
