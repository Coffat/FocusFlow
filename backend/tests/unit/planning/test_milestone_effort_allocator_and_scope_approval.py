from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path
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
)
from src.execution.public_api import (
    ExecutionScheduleSyncPort,
    ExistingScheduledTaskDTO,
)
from src.planning.application.ports.planning_repository_ports import (
    GoalRepositoryPort,
    MilestoneRepositoryPort,
    RoadmapRepositoryPort,
    ScheduleProposalRepositoryPort,
)
from src.planning.application.services.roadmap_context_builder import (
    RoadmapContextBuilder,
)
from src.planning.application.use_cases.milestone_use_cases import (
    ApproveMilestonesUseCase,
    ExecuteMilestoneGenerationUseCase,
)
from src.planning.application.use_cases.proposal_generation_use_cases import (
    ExecuteScheduleProposalGenerationUseCase,
    InitiateScheduleProposalGenerationUseCase,
)
from src.planning.domain.exceptions.planning_exceptions import (
    InsufficientCapacityError,
    ScopeApprovalRequiredError,
)
from src.planning.domain.models.goal import Goal, GoalStatus
from src.planning.domain.models.milestone import Milestone, MilestoneStatus
from src.planning.domain.models.roadmap import Roadmap, RoadmapStatus
from src.planning.domain.models.schedule import ScheduleProposal, ScheduleProposalStatus
from src.planning.domain.services.milestone_effort_allocator import (
    MilestoneEffortAllocator,
)
from src.planning.domain.services.spatio_temporal_engine import SpatioTemporalRuleEngine
from src.planning.domain.services.validation_types import (
    AvailabilityConfigurationDTO,
    AvailabilitySlotDTO,
)
from src.shared_kernel.application.uow import AsyncUnitOfWork
from src.shared_kernel.config import get_settings
from src.shared_kernel.infrastructure.sse.job_store import InMemorySseJobStore
from tests.helpers.llm_stubs import StubLLMAdapter

REPO_ROOT = Path(__file__).resolve().parents[4]
EXP09_PATH = REPO_ROOT / "docs" / "experiments" / "exp_09_judge_and_quality_ab.json"
KEY10_PATH = REPO_ROOT / "docs" / "experiments" / "blind_review_10_roadmaps_key.json"
EXP10_PATH = REPO_ROOT / "docs" / "experiments" / "exp_10_planner_tool_rounds_ab.json"
KEY12_PATH = REPO_ROOT / "docs" / "experiments" / "blind_review_hard_6_milestones_key.json"
HARD_DATASET_PATH = (
    REPO_ROOT / "backend" / "tests" / "ai_evals" / "datasets" / "hard_planning_6_goals.jsonl"
)


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

    async def save_many(
        self,
        roadmap_id: UUID,
        milestones: Any,
    ) -> list[Milestone]:
        self.by_roadmap[roadmap_id] = list(milestones)
        return sorted(self.by_roadmap[roadmap_id], key=lambda m: m.sequence_order)

    async def list_by_roadmap_id(self, roadmap_id: UUID) -> list[Milestone]:
        return sorted(self.by_roadmap.get(roadmap_id, []), key=lambda m: m.sequence_order)

    async def approve_all_for_roadmap(
        self,
        roadmap_id: UUID,
        now: datetime,
    ) -> list[Milestone]:
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
        _ = now
        cnt = 0
        for p in self.items.values():
            if p.roadmap_id == roadmap_id and p.status == ScheduleProposalStatus.DRAFT:
                p.discard(now)
                cnt += 1
        return cnt


class _FakeQuotaFacade(QuotaFacadePort):
    def __init__(self) -> None:
        self.reserved: list[UUID] = []
        self.committed: list[UUID] = []
        self.released: list[UUID] = []

    async def reserve_quota(
        self,
        *,
        user_id: UUID,
        operation_type: str,
        cost: int = 1,
    ) -> UUID:
        _ = (user_id, operation_type, cost)
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


class _FakeAvailabilityPort(AvailabilityQueryPort):
    def __init__(self, snapshot: AvailabilitySnapshotDTO) -> None:
        self._snapshot = snapshot

    async def get_active_availability(self, user_id: UUID) -> AvailabilitySnapshotDTO | None:
        _ = user_id
        return self._snapshot


class _FakeLearnerProfilePort(LearnerProfileQueryPort):
    def __init__(self, opt_session_minutes: int = 60) -> None:
        self._opt = opt_session_minutes

    async def get_learner_profile(self, user_id: UUID) -> LearnerProfileDTO:
        return LearnerProfileDTO(
            user_id=user_id,
            opt_session_minutes=self._opt,
            estimation_bias_beta=1.0,
        )


class _FakeExecutionSyncPort(ExecutionScheduleSyncPort):
    async def get_tasks_for_roadmaps(
        self,
        roadmap_ids: Any,
        *,
        roadmap_target_dates: dict[UUID, date | None] | None = None,
    ) -> list[ExistingScheduledTaskDTO]:
        _ = (roadmap_ids, roadmap_target_dates)
        return []


def _to_avail_cfg(avail_dict: dict[str, Any]) -> AvailabilityConfigurationDTO:
    return AvailabilityConfigurationDTO(
        mode=avail_dict["mode"],
        default_daily_quota_minutes=int(avail_dict["default_daily_quota_minutes"]),
        daily_quota_minutes=dict(avail_dict.get("daily_quota_minutes") or {}),
        availability_slots=tuple(
            AvailabilitySlotDTO(**s) for s in (avail_dict.get("availability_slots") or [])
        ),
        disabled_weekdays=frozenset(avail_dict.get("disabled_weekdays") or []),
    )


def test_replay_12_exp10_milestones_and_r01_concise_beginner_goal() -> None:
    exp10 = json.loads(EXP10_PATH.read_text(encoding="utf-8"))
    key12 = json.loads(KEY12_PATH.read_text(encoding="utf-8"))["mapping"]
    dataset = {
        obj["scenario_id"]: obj
        for line in HARD_DATASET_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
        for obj in [json.loads(line)]
    }
    scenarios = {s["scenario_id"]: s for s in exp10["scenarios"]}

    # M-01..M-11 (82.8%..100.0% raw) MUST retain FULL_SCOPE_FEASIBLE with differentiated efforts
    for label in [f"M-{idx:02d}" for idx in range(1, 12)]:
        meta = key12[label]
        sid = meta["scenario_id"]
        arm = meta["arm"]
        ds_item = dataset[sid]
        cfg = _to_avail_cfg(ds_item["availability"])
        s_date = date.fromisoformat(ds_item["start_date"])
        t_date = date.fromisoformat(ds_item["target_date"])
        p_hard, _ = SpatioTemporalRuleEngine.calculate_hard_packable_capacity(
            cfg, start_date=s_date, target_date=t_date
        )

        res = MilestoneEffortAllocator.allocate(
            scenarios[sid][arm]["milestones"],
            hard_packable_capacity_minutes=p_hard,
            prior_knowledge_level=ds_item["learner_level"],
            start_date=s_date,
            target_date=t_date,
            availability=cfg,
        )
        assert res.status == "FULL_SCOPE_FEASIBLE", f"{label} expected FULL_SCOPE_FEASIBLE"
        assert res.requires_learner_approval is False
        assert res.scope_approval_status == "NOT_REQUIRED"
        assert len(res.kept_scope) == len(scenarios[sid][arm]["milestones"])
        assert len(res.deferred_scope) == 0

        efforts = [b.normalized_planned_effort_minutes for b in res.breakdowns]
        assert len(set(efforts)) > 1, f"{label} must break uniform effort equality: {efforts}"
        assert all(e % 30 == 0 and e >= 60 for e in efforts)
        assert sum(efforts) <= p_hard
        for bd in res.breakdowns:
            assert bd.estimated_effort_minutes % 30 == 0
            assert bd.minimum_defensible_effort_minutes % 30 == 0
            assert bd.normalized_planned_effort_minutes >= bd.minimum_defensible_effort_minutes

    # M-12 at 3480m: sum(E_llm)=3960 > 3480, yet sum(E_min)=1050 <= 3480 -> Decision 1 keeps FULL_SCOPE_FEASIBLE
    m12_meta = key12["M-12"]
    m12_ds = dataset[m12_meta["scenario_id"]]
    m12_cfg = _to_avail_cfg(m12_ds["availability"])
    m12_s = date.fromisoformat(m12_ds["start_date"])
    m12_t = date.fromisoformat(m12_ds["target_date"])
    m12_p_hard, _ = SpatioTemporalRuleEngine.calculate_hard_packable_capacity(
        m12_cfg, start_date=m12_s, target_date=m12_t
    )
    m12_milestones = scenarios[m12_meta["scenario_id"]][m12_meta["arm"]]["milestones"]
    res_m12_full = MilestoneEffortAllocator.allocate(
        m12_milestones,
        hard_packable_capacity_minutes=m12_p_hard,
        prior_knowledge_level=m12_ds["learner_level"],
        start_date=m12_s,
        target_date=m12_t,
        availability=m12_cfg,
    )
    assert m12_p_hard == 3480
    assert res_m12_full.llm_estimated_total_minutes == 3960
    assert res_m12_full.minimum_defensible_total_minutes <= m12_p_hard
    assert res_m12_full.status == "FULL_SCOPE_FEASIBLE"
    assert res_m12_full.normalized_planned_total_minutes <= m12_p_hard

    # M-12 under constrained window where BOTH sum(E_llm) > P_hard AND sum(E_min) > P_hard -> FIT_CAPACITY_REQUIRES_APPROVAL
    tight_p_hard = 780
    res_m12_fit = MilestoneEffortAllocator.allocate(
        m12_milestones,
        hard_packable_capacity_minutes=tight_p_hard,
        prior_knowledge_level=m12_ds["learner_level"],
        start_date=m12_s,
        target_date=m12_s + (m12_t - m12_s) // 4,
        availability=m12_cfg,
    )
    assert res_m12_fit.llm_estimated_total_minutes > tight_p_hard
    assert res_m12_fit.minimum_defensible_total_minutes > tight_p_hard
    assert res_m12_fit.status == "FIT_CAPACITY_REQUIRES_APPROVAL"
    assert res_m12_fit.scope_proposal_version == 1
    assert res_m12_fit.scope_proposal_hash.startswith("sha256:")
    assert res_m12_fit.requires_learner_approval is True
    assert res_m12_fit.scope_approval_status == "PENDING_LEARNER_APPROVAL"
    assert len(res_m12_fit.kept_scope) >= 1
    assert len(res_m12_fit.deferred_scope) >= 1
    assert len(res_m12_fit.expected_outcomes) >= 1
    assert res_m12_fit.feasibility_reasons[0]["code"] == "FIT_CAPACITY_REQUIRED"
    assert res_m12_fit.adjustment_options["is_approximate"] is True
    assert res_m12_fit.adjustment_options["estimated_earliest_target_date_range"] is not None
    assert res_m12_fit.adjustment_options["recommended_additional_weekly_minutes"] > 0

    # R-01 concise beginner goal (810m / 3030m) MUST keep 810m (NOT inflated to 85%)
    exp09 = json.loads(EXP09_PATH.read_text(encoding="utf-8"))
    r01_meta = json.loads(KEY10_PATH.read_text(encoding="utf-8"))["mapping"]["R-01"]
    r01_data = next(
        r
        for r in exp09["part_3_quality_ab_low_vs_medium"]["roadmaps"]
        if r["goal_key"] == r01_meta["goal_id"] and r["arm"] == r01_meta["arm"]
    )
    res_r01 = MilestoneEffortAllocator.allocate(
        r01_data["planner"]["milestones"],
        hard_packable_capacity_minutes=3030,
        prior_knowledge_level="BEGINNER",
    )
    assert res_r01.status == "FULL_SCOPE_FEASIBLE"
    assert res_r01.normalized_planned_total_minutes == 810
    assert [b.normalized_planned_effort_minutes for b in res_r01.breakdowns] == [
        210,
        180,
        240,
        180,
    ]


def test_decision1_safeguard_and_prerequisite_closure_and_case3_unschedulable() -> None:
    # 1. Decision 1 safeguard: huge outcome/concept counts pushing H_est high NEVER triggers
    # FIT_CAPACITY or PRELIMINARY_UNSCHEDULABLE when sum(E_llm) <= P_hard or sum(E_min) <= P_hard.
    rich_milestones = [
        {
            "sequence_order": 1,
            "title": "Xây dựng nền tảng hệ thống",
            "description": "Cài đặt và kiểm thử đầy đủ pipeline Docker",
            "learning_outcomes": [
                f"M1-O{i}: Triển khai thành phần {i} với benchmark và kiểm thử toàn diện trên cụm Docker"
                for i in range(1, 7)
            ],
            "completion_criteria": "Đồ án tích hợp hoàn chỉnh đạt 100% benchmark",
            "estimated_effort_minutes": 180,
            "required_concepts": [f"c-{i}" for i in range(6)],
            "dependencies": [],
        },
        {
            "sequence_order": 2,
            "title": "Tối ưu hiệu năng và triển khai",
            "description": "Profile và benchmark tải cao",
            "learning_outcomes": [
                f"M2-O{i}: Tối ưu dịch vụ {i} với Prometheus và Grafana" for i in range(1, 7)
            ],
            "completion_criteria": "Kiểm thử chịu tải đạt ngưỡng p99",
            "estimated_effort_minutes": 240,
            "required_concepts": [f"d-{i}" for i in range(6)],
            "dependencies": [1],
        },
    ]
    res_safeguard = MilestoneEffortAllocator.allocate(
        rich_milestones,
        hard_packable_capacity_minutes=450,  # sum(E_llm) = 420 <= 450, even though H_est >> 450
        prior_knowledge_level="BEGINNER",
    )
    assert res_safeguard.status == "FULL_SCOPE_FEASIBLE"
    assert res_safeguard.normalized_planned_total_minutes <= 450

    # 2. Prerequisite closure on branching DAG: M4 depends on [2, 3]; M1=120, M2=120, M3=120, M4=120.
    # With P_hard=300 and gamma_min=0.90 (so E_min ~ [120, 120, 120, 120]), kept_scope must be {1, 2}
    # and never keep M4 without both M2 and M3.
    branching_milestones = [
        {
            "sequence_order": idx,
            "title": f"Cột mốc {idx}",
            "learning_outcomes": [f"M{idx}-O1", f"M{idx}-O2"],
            "completion_criteria": "Hoàn thành bài lab",
            "estimated_effort_minutes": 240,
            "required_concepts": ["c1", "c2"],
            "dependencies": deps,
        }
        for idx, deps in [(1, []), (2, [1]), (3, [1]), (4, [2, 3])]
    ]
    res_fit = MilestoneEffortAllocator.allocate(
        branching_milestones,
        hard_packable_capacity_minutes=300,
        prior_knowledge_level="INTERMEDIATE",
        gamma_min=0.90,
    )
    assert res_fit.status == "FIT_CAPACITY_REQUIRES_APPROVAL"
    kept_seqs = {item["sequence_order"] for item in res_fit.kept_scope}
    for item in res_fit.kept_scope:
        assert set(item["dependencies"]).issubset(kept_seqs)
    assert 4 not in kept_seqs

    # 3. Case 3: PRELIMINARY_UNSCHEDULABLE when P_hard < 30m or M1 exceeds P_hard
    res_unsched = MilestoneEffortAllocator.allocate(
        branching_milestones,
        hard_packable_capacity_minutes=20,
        prior_knowledge_level="INTERMEDIATE",
    )
    assert res_unsched.status == "PRELIMINARY_UNSCHEDULABLE"
    assert res_unsched.adjustment_options["is_approximate"] is True
    assert res_unsched.kept_scope == ()

    res_m1_too_big = MilestoneEffortAllocator.allocate(
        [
            {
                "sequence_order": 1,
                "title": "Cột mốc nền tảng",
                "learning_outcomes": ["O1", "O2", "O3"],
                "completion_criteria": "Đồ án tốt nghiệp",
                "estimated_effort_minutes": 300,
                "required_concepts": ["a", "b", "c"],
                "dependencies": [],
            }
        ],
        hard_packable_capacity_minutes=60,
        prior_knowledge_level="BEGINNER",
    )
    assert res_m1_too_big.status == "PRELIMINARY_UNSCHEDULABLE"
    assert res_m1_too_big.adjustment_options["is_approximate"] is True


@pytest.mark.asyncio
async def test_fit_capacity_versioned_approval_and_decomposer_guard_e2e(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime(2026, 11, 2, 10, 0, tzinfo=UTC)
    user_id = uuid7()
    goal = Goal(
        id=uuid7(),
        user_id=user_id,
        title="Hệ thống Distributed Rust",
        raw_description="Xây dựng hệ phân tán",
        target_date=date(2026, 11, 15),
        prior_knowledge_level="INTERMEDIATE",
        status=GoalStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
    # 14 days (Nov 2..15) * 60m = 840m hard capacity (set via Mode A 60m/day)
    roadmap = Roadmap(
        id=uuid7(),
        user_id=user_id,
        goal_id=goal.id,
        title="Distributed Rust 2 tuần",
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
    quota = _FakeQuotaFacade()
    sse_store = InMemorySseJobStore()
    uow = _FakeUoW()

    await goal_repo.save(goal)
    await roadmap_repo.save(roadmap)

    # Tight availability: only Monday 19:00-21:00 (120m/wk * 2 Mondays = 240m P_hard)
    avail_snapshot = AvailabilitySnapshotDTO(
        user_id=user_id,
        mode="MODE_B",
        daily_cap_minutes=120,
        weekly_capacity_minutes=120,
        daily_quota_minutes={},
        availability_slots=(
            {
                "day_of_week": "monday",
                "start_time": "19:00",
                "end_time": "21:00",
                "end_day_offset": 0,
                "is_active": True,
            },
        ),
        disabled_weekdays=(),
    )

    llm_milestones_payload = {
        "milestones": [
            {
                "sequence_order": 1,
                "title": "Nền tảng Rust Ownership & Async",
                "description": "Cài đặt async executor cơ bản",
                "learning_outcomes": [
                    "Thiết lập async runtime và xử lý channel concurrency",
                    "Kiểm thử unit cho trạng thái bất đồng bộ",
                ],
                "completion_criteria": "Pass toàn bộ unit test async",
                "estimated_effort_minutes": 240,
                "required_concepts": [],
                "unverified_concepts": ["rust-async", "tokio-channel"],
                "dependencies": [],
            },
            {
                "sequence_order": 2,
                "title": "Giao thức gRPC & RPC Framing",
                "description": "Xây dựng server gRPC streaming",
                "learning_outcomes": [
                    "Cài đặt bidirectional streaming RPC",
                    "Kiểm thử tích hợp client-server",
                ],
                "completion_criteria": "gRPC server chạy ổn định",
                "estimated_effort_minutes": 240,
                "required_concepts": [],
                "unverified_concepts": ["tonic-grpc", "protobuf"],
                "dependencies": [1],
            },
            {
                "sequence_order": 3,
                "title": "Đồ án Raft Consensus Cluster",
                "description": "Xây dựng cụm Raft 3-node chịu lỗi",
                "learning_outcomes": [
                    "Triển khai leader election và log replication",
                    "Chạy benchmark và chaos test",
                ],
                "completion_criteria": "Đồ án cụm 3-node vượt qua chaos test",
                "estimated_effort_minutes": 360,
                "required_concepts": [],
                "unverified_concepts": ["raft", "wal-snapshot"],
                "dependencies": [2],
            },
        ],
        "scope_summary": "FULL_SCOPE",
        "deferred_scope": [],
    }
    monkeypatch.setattr(get_settings(), "milestone_effort_allocator_enabled", True)

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
        llm_provider=StubLLMAdapter(canned_responses=[llm_milestones_payload]),
        sse_job_store=sse_store,
        uow=uow,
        availability_query_port=_FakeAvailabilityPort(avail_snapshot),
        execution_sync_port=_FakeExecutionSyncPort(),
    )
    saved_ms = await gen_ms_uc.execute(
        job_id=ms_job_id,
        user_id=user_id,
        roadmap_id=roadmap.id,
        reservation_id=ms_res_id,
        now=now,
    )
    assert len(saved_ms) == 3

    stored_roadmap = await roadmap_repo.get_by_id(roadmap.id)
    assert stored_roadmap is not None
    prelim = stored_roadmap.planning_metadata["preliminary_feasibility"]
    assert isinstance(prelim, dict)
    assert prelim["status"] == "FIT_CAPACITY_REQUIRES_APPROVAL"
    assert prelim["scope_proposal_version"] == 1
    assert prelim["requires_learner_approval"] is True
    assert prelim["scope_approval_status"] == "PENDING_LEARNER_APPROVAL"
    assert len(prelim["kept_scope"]) < 3

    approve_uc = ApproveMilestonesUseCase(
        roadmap_repo=roadmap_repo,
        milestone_repo=milestone_repo,
        uow=uow,
    )
    # 1. Unconfirmed approval fails with ScopeApprovalRequiredError
    with pytest.raises(ScopeApprovalRequiredError) as exc_info:
        await approve_uc.execute(user_id=user_id, roadmap_id=roadmap.id, now=now)
    assert exc_info.value.scope_proposal_version == 1

    # 2. Stale/mismatched version fails with ScopeApprovalRequiredError
    with pytest.raises(ScopeApprovalRequiredError):
        await approve_uc.execute(
            user_id=user_id,
            roadmap_id=roadmap.id,
            confirmed_scope_proposal_version=99,
            accept_fit_capacity=True,
            now=now,
        )

    # 3. Initiating Task Decomposer before approval raises ScopeApprovalRequiredError & reserves 0 quota
    reserved_before = len(quota.reserved)
    init_prop_uc = InitiateScheduleProposalGenerationUseCase(
        roadmap_repo=roadmap_repo,
        milestone_repo=milestone_repo,
        quota_facade=quota,
        sse_job_store=sse_store,
        uow=uow,
    )
    with pytest.raises(ScopeApprovalRequiredError):
        await init_prop_uc.execute(user_id=user_id, roadmap_id=roadmap.id, run_inline=False)
    assert len(quota.reserved) == reserved_before

    # 4. Confirm matching version -> approves ONLY kept_scope milestones
    approved_ms = await approve_uc.execute(
        user_id=user_id,
        roadmap_id=roadmap.id,
        confirmed_scope_proposal_version=1,
        accept_fit_capacity=True,
        now=now,
    )
    kept_orders = {int(item["sequence_order"]) for item in prelim["kept_scope"]}
    for m in approved_ms:
        if m.sequence_order in kept_orders:
            assert m.status == MilestoneStatus.APPROVED
        else:
            assert m.status == MilestoneStatus.PENDING

    stored_after_approve = await roadmap_repo.get_by_id(roadmap.id)
    assert stored_after_approve is not None
    prelim_after = stored_after_approve.planning_metadata["preliminary_feasibility"]
    assert isinstance(prelim_after, dict)
    assert prelim_after["scope_approval_status"] == "APPROVED_BY_LEARNER"
    assert prelim_after["approved_scope_version"] == 1

    # 5. Task Decomposer now passes guard and decomposes ONLY kept_scope milestones
    kept_ms = [m for m in approved_ms if m.sequence_order in kept_orders]
    decomposer_payload = {
        "tasks": [
            {
                "task_id": f"T{idx}",
                "milestone_id": str(m.id),
                "title": f"Thực hành {m.title}",
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
        ],
        "dependencies": [],
    }
    exec_prop_uc = ExecuteScheduleProposalGenerationUseCase(
        goal_repo=goal_repo,
        roadmap_repo=roadmap_repo,
        milestone_repo=milestone_repo,
        proposal_repo=proposal_repo,
        availability_query_port=_FakeAvailabilityPort(avail_snapshot),
        learner_profile_port=_FakeLearnerProfilePort(),
        execution_sync_port=_FakeExecutionSyncPort(),
        quota_facade=quota,
        llm_provider=StubLLMAdapter(canned_responses=[decomposer_payload]),
        sse_job_store=sse_store,
        uow=uow,
        enable_tier3_judge=False,
    )
    prop_ticket = await init_prop_uc.execute(
        user_id=user_id, roadmap_id=roadmap.id, run_inline=False
    )
    proposal = await exec_prop_uc.execute(
        job_id=prop_ticket.job_id,
        user_id=user_id,
        roadmap_id=roadmap.id,
        reservation_id=prop_ticket.reservation_id,
        now=now,
    )
    assert proposal.status == ScheduleProposalStatus.DRAFT
    decomposed_mids = {str(t["milestone_id"]) for t in proposal.proposal_data["tasks"]}
    assert decomposed_mids == {str(m.id) for m in kept_ms}

    # Verify RoadmapContextBuilder includes preliminary_feasibility_summary safely
    ctx = RoadmapContextBuilder.build_task_decomposition_context(
        goal=goal,
        roadmap=stored_after_approve,
        milestones=kept_ms,
        availability=_to_avail_cfg(
            {
                "mode": "MODE_B",
                "default_daily_quota_minutes": 120,
                "availability_slots": avail_snapshot.availability_slots,
            }
        ),
        learner_profile=LearnerProfileDTO(user_id=user_id, opt_session_minutes=60),
    )
    assert "preliminary_feasibility_summary:" in ctx

    # 6. Rollback flag milestone_effort_allocator_enabled=False restores legacy bypass cleanly
    monkeypatch.setattr(get_settings(), "milestone_effort_allocator_enabled", False)
    roadmap_legacy = Roadmap(
        id=uuid7(),
        user_id=user_id,
        goal_id=goal.id,
        title="Legacy mode",
        start_date=date(2026, 11, 2),
        target_date=date(2026, 11, 15),
        status=RoadmapStatus.INITIALIZED,
        created_at=now,
        updated_at=now,
    )
    await roadmap_repo.save(roadmap_legacy)
    ms_job_legacy = uuid7()
    ms_res_legacy = await quota.reserve_quota(user_id=user_id, operation_type="MILESTONE_GEN")
    await sse_store.create_job(
        job_id=ms_job_legacy,
        user_id=user_id,
        roadmap_id=roadmap_legacy.id,
        reservation_id=ms_res_legacy,
        job_type="MILESTONE_GEN",
        operation=f"MILESTONE_GEN:{roadmap_legacy.id}",
    )
    gen_ms_uc_legacy = ExecuteMilestoneGenerationUseCase(
        goal_repo=goal_repo,
        roadmap_repo=roadmap_repo,
        milestone_repo=milestone_repo,
        quota_facade=quota,
        llm_provider=StubLLMAdapter(canned_responses=[llm_milestones_payload]),
        sse_job_store=sse_store,
        uow=uow,
        availability_query_port=_FakeAvailabilityPort(avail_snapshot),
        execution_sync_port=_FakeExecutionSyncPort(),
    )
    legacy_ms = await gen_ms_uc_legacy.execute(
        job_id=ms_job_legacy,
        user_id=user_id,
        roadmap_id=roadmap_legacy.id,
        reservation_id=ms_res_legacy,
        now=now,
    )
    assert [m.estimated_effort_minutes for m in legacy_ms] == [240, 240, 360]
    legacy_rm = await roadmap_repo.get_by_id(roadmap_legacy.id)
    assert legacy_rm is not None
    assert "preliminary_feasibility" not in legacy_rm.planning_metadata
    approved_legacy = await approve_uc.execute(
        user_id=user_id, roadmap_id=roadmap_legacy.id, now=now
    )
    assert all(m.status == MilestoneStatus.APPROVED for m in approved_legacy)


@pytest.mark.asyncio
async def test_preliminary_unschedulable_blocks_approval_and_decomposer() -> None:
    now = datetime(2026, 11, 2, 10, 0, tzinfo=UTC)
    user_id = uuid7()
    roadmap = Roadmap(
        id=uuid7(),
        user_id=user_id,
        goal_id=uuid7(),
        title="Impossible 1-day window",
        start_date=date(2026, 11, 2),
        target_date=date(2026, 11, 2),
        status=RoadmapStatus.INITIALIZED,
        planning_metadata={
            "preliminary_feasibility": {
                "status": "PRELIMINARY_UNSCHEDULABLE",
                "hard_packable_capacity_minutes": 15,
                "requires_learner_approval": False,
                "scope_approval_status": "NOT_REQUIRED",
                "adjustment_options": {"is_approximate": True},
            }
        },
        created_at=now,
        updated_at=now,
    )
    roadmap_repo = _FakeRoadmapRepo()
    milestone_repo = _FakeMilestoneRepo()
    quota = _FakeQuotaFacade()
    sse_store = InMemorySseJobStore()
    uow = _FakeUoW()
    await roadmap_repo.save(roadmap)
    await milestone_repo.save_many(
        roadmap.id,
        [
            Milestone(
                id=uuid7(),
                roadmap_id=roadmap.id,
                sequence_order=1,
                title="M1",
                estimated_effort_minutes=120,
                status=MilestoneStatus.PENDING,
                created_at=now,
                updated_at=now,
            )
        ],
    )

    approve_uc = ApproveMilestonesUseCase(
        roadmap_repo=roadmap_repo, milestone_repo=milestone_repo, uow=uow
    )
    with pytest.raises(InsufficientCapacityError):
        await approve_uc.execute(user_id=user_id, roadmap_id=roadmap.id, now=now)

    init_prop_uc = InitiateScheduleProposalGenerationUseCase(
        roadmap_repo=roadmap_repo,
        milestone_repo=milestone_repo,
        quota_facade=quota,
        sse_job_store=sse_store,
        uow=uow,
    )
    with pytest.raises(InsufficientCapacityError):
        await init_prop_uc.execute(user_id=user_id, roadmap_id=roadmap.id, run_inline=False)
