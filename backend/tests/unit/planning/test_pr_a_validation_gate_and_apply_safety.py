from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

import pytest
from uuid6 import uuid7

from src.account.public_api import (
    AvailabilitySnapshotDTO,
    LearnerProfileDTO,
)
from src.execution.public_api import (
    ExistingScheduledTaskDTO,
    ScheduleSyncResultDTO,
)
from src.planning.application.services import (
    AvailabilityConfigurationDTO,
    AvailabilitySlotDTO,
    ProposalValidationGateOrchestrator,
)
from src.planning.application.services.learning_quality import (
    FeasibilityStatus,
    assess_schedule_feasibility,
)
from src.planning.application.services.validation_gate.tier2_deterministic import (
    run_tier2_gate,
)
from src.planning.application.use_cases.proposal_generation_use_cases import (
    ExecuteScheduleProposalGenerationUseCase,
)
from src.planning.application.use_cases.proposal_management_use_cases import (
    ApplyScheduleProposalUseCase,
    UpdateScheduleProposalUseCase,
)
from src.planning.domain.exceptions.planning_exceptions import (
    JudgeReviewConfirmationRequiredError,
    PartialScheduleConfirmationRequiredError,
    PlanInfeasibleError,
    PlanningDomainError,
    ProposalValidationGateError,
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
from src.shared_kernel.infrastructure.sse import InMemorySseJobStore
from tests.helpers.llm_stubs import StubLLMAdapter


class _CountingLLM(StubLLMAdapter):
    def __init__(self, canned_responses: list[dict[str, Any]]) -> None:
        super().__init__(canned_responses=canned_responses)
        self.calls = 0

    async def generate_structured(
        self, *args: Any, **kwargs: Any
    ) -> tuple[dict[str, Any], int, int]:
        self.calls += 1
        return await super().generate_structured(*args, **kwargs)


class _RecordingQuotaFacade:
    def __init__(self) -> None:
        self.committed: list[tuple[UUID, int, int, str]] = []
        self.released: list[tuple[UUID, str]] = []

    async def commit_reservation(
        self,
        reservation_id: UUID,
        *,
        prompt_tokens: int,
        completion_tokens: int,
        model_name: str,
    ) -> None:
        self.committed.append((reservation_id, prompt_tokens, completion_tokens, model_name))

    async def release_reservation(self, reservation_id: UUID, *, reason: str = "") -> None:
        self.released.append((reservation_id, reason))


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


class _FakeGoalRepo:
    def __init__(self, goal: Goal) -> None:
        self.goal = goal

    async def get_by_id(self, gid: UUID) -> Goal | None:
        return self.goal if gid == self.goal.id else None


class _FakeRoadmapRepo:
    def __init__(self, roadmap: Roadmap) -> None:
        self.roadmap = roadmap

    async def get_by_id(self, rid: UUID) -> Roadmap | None:
        return self.roadmap if rid == self.roadmap.id else None

    async def get_by_id_for_user(self, rid: UUID, uid: UUID) -> Roadmap | None:
        return self.roadmap if rid == self.roadmap.id and uid == self.roadmap.user_id else None

    async def list_by_user_id(self, uid: UUID, status: str | None = None) -> list[Roadmap]:
        del uid, status
        return []

    async def count_active_by_user_id(
        self, uid: UUID, exclude_roadmap_id: UUID | None = None
    ) -> int:
        del uid, exclude_roadmap_id
        return 0

    async def save(self, r: Roadmap) -> Roadmap:
        self.roadmap = r
        return r


class _FakeMilestoneRepo:
    def __init__(self, milestones: list[Milestone]) -> None:
        self.milestones = milestones

    async def list_by_roadmap_id(self, rid: UUID) -> list[Milestone]:
        del rid
        return list(self.milestones)


class _FakeProposalRepo:
    def __init__(self, initial: ScheduleProposal | None = None) -> None:
        self.proposals: dict[UUID, ScheduleProposal] = {}
        if initial is not None:
            self.proposals[initial.id] = initial

    async def get_by_id(self, pid: UUID) -> ScheduleProposal | None:
        return self.proposals.get(pid)

    async def get_current_draft(self, rid: UUID) -> ScheduleProposal | None:
        for p in self.proposals.values():
            if p.roadmap_id == rid and p.status == ScheduleProposalStatus.DRAFT:
                return p
        return None

    async def discard_existing_drafts(self, rid: UUID, now: datetime) -> int:
        count = 0
        for p in self.proposals.values():
            if p.roadmap_id == rid and p.status == ScheduleProposalStatus.DRAFT:
                p.mark_discarded(now)
                count += 1
        return count

    async def save(self, p: ScheduleProposal) -> ScheduleProposal:
        self.proposals[p.id] = p
        return p


class _FakeScheduleRepo:
    def __init__(self) -> None:
        self.schedule: OfficialSchedule | None = None

    async def get_by_roadmap_id(self, rid: UUID) -> OfficialSchedule | None:
        del rid
        return self.schedule

    async def save(self, s: OfficialSchedule) -> OfficialSchedule:
        self.schedule = s
        return s


class _FakeBlockRepo:
    def __init__(self) -> None:
        self.blocks: list[ScheduleBlock] = []

    async def get_by_schedule_id(self, sid: UUID) -> list[ScheduleBlock]:
        del sid
        return list(self.blocks)

    async def list_by_roadmap_ids(self, rids: list[UUID]) -> list[ScheduleBlock]:
        del rids
        return []

    async def save_all(self, blocks: list[ScheduleBlock]) -> list[ScheduleBlock]:
        self.blocks = list(blocks)
        return self.blocks


class _FakeExecSyncPort:
    def __init__(self, existing: list[ExistingScheduledTaskDTO] | None = None) -> None:
        self.existing = existing or []
        self.get_tasks_calls = 0
        self.sync_calls = 0

    async def get_tasks_for_roadmaps(
        self, *args: Any, **kwargs: Any
    ) -> list[ExistingScheduledTaskDTO]:
        del args, kwargs
        self.get_tasks_calls += 1
        return list(self.existing)

    async def sync_official_schedule_tasks(self, **kwargs: Any) -> ScheduleSyncResultDTO:
        self.sync_calls += 1
        tasks = kwargs["proposed_tasks"]
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


class _FakeAvailabilityPort:
    def __init__(self, snap: AvailabilitySnapshotDTO | None) -> None:
        self.snap = snap
        self.calls = 0

    async def get_active_availability(self, uid: UUID) -> AvailabilitySnapshotDTO | None:
        del uid
        self.calls += 1
        return self.snap


class _FakeChangeLogPort:
    def __init__(self) -> None:
        self.logs: list[dict[str, Any]] = []

    async def record_change_log(self, **kwargs: Any) -> None:
        self.logs.append(kwargs)


def _valid_task(
    milestone_id: UUID,
    *,
    task_id: str | None = None,
    title: str = "Học Python cơ bản",
    minutes: int = 60,
    scheduled_date: str | None = "2026-11-16",
    scheduled_start: str | None = "2026-11-16T19:00:00+00:00",
    scheduled_end: str | None = "2026-11-16T20:00:00+00:00",
    is_non_splittable: bool | None = None,
    unscheduled_reason: str | None = None,
) -> dict[str, Any]:
    task: dict[str, Any] = {
        "task_id": task_id or str(uuid7()),
        "milestone_id": str(milestone_id),
        "title": title,
        "learning_objective": "Nắm vững kiến thức cốt lõi của bài học.",
        "completion_criteria": "Hoàn thành bài tập kiểm chứng đạt yêu cầu.",
        "covered_outcome_ids": ["M1-O1"],
        "concept_ids": ["python"],
        "estimated_minutes": minutes,
        "scheduled_date": scheduled_date,
        "scheduled_start": scheduled_start,
        "scheduled_end": scheduled_end,
    }
    if is_non_splittable is not None:
        task["is_non_splittable"] = is_non_splittable
    if unscheduled_reason is not None:
        task["unscheduled_reason"] = unscheduled_reason
    return task


def _milestone(roadmap_id: UUID, *, effort: int = 120) -> Milestone:
    now = datetime(2026, 11, 1, 9, 0, tzinfo=UTC)
    return Milestone(
        id=uuid7(),
        roadmap_id=roadmap_id,
        sequence_order=1,
        title="M1: Python",
        learning_outcomes=("Viết hàm",),
        completion_criteria="Pass pytest",
        estimated_effort_minutes=effort,
        required_concepts=("python",),
        status=MilestoneStatus.APPROVED,
        created_at=now,
        updated_at=now,
    )


# =============================================================================
# 1. ScheduleCompletenessStatus (4 states)
# =============================================================================


def test_classify_schedule_completeness_separates_all_four_states() -> None:
    from src.planning.domain.services.validation_types import (
        classify_schedule_completeness,
    )

    assert (
        classify_schedule_completeness(
            total_tasks=2,
            scheduled_tasks_count=2,
            unscheduled_tasks_count=0,
            available_minutes=120,
            schedulable_ratio=1.0,
            feasibility_verdict="VERIFIED_FEASIBLE",
        )
        == "FULL"
    )
    assert (
        classify_schedule_completeness(
            total_tasks=2,
            scheduled_tasks_count=2,
            unscheduled_tasks_count=0,
            available_minutes=120,
            schedulable_ratio=1.0,
            feasibility_verdict=None,
            all_scheduled_have_block_times=True,
        )
        == "FULL"
    )
    assert (
        classify_schedule_completeness(
            total_tasks=2,
            scheduled_tasks_count=1,
            unscheduled_tasks_count=1,
            available_minutes=120,
            schedulable_ratio=0.5,
            feasibility_verdict="EXPLICIT_UNSCHEDULABLE",
            allow_partial_schedule=True,
        )
        == "PARTIAL"
    )
    assert (
        classify_schedule_completeness(
            total_tasks=0,
            scheduled_tasks_count=0,
            unscheduled_tasks_count=0,
            available_minutes=120,
            schedulable_ratio=1.0,
        )
        == "UNDETERMINED"
    )
    assert (
        classify_schedule_completeness(
            total_tasks=2,
            scheduled_tasks_count=1,
            unscheduled_tasks_count=1,
            available_minutes=120,
            schedulable_ratio=0.5,
            feasibility_verdict=None,
            has_schedule_blocks=False,
            all_scheduled_have_block_times=False,
        )
        == "UNDETERMINED"
    )
    assert (
        classify_schedule_completeness(
            total_tasks=2,
            scheduled_tasks_count=1,
            unscheduled_tasks_count=1,
            available_minutes=120,
            schedulable_ratio=0.5,
            feasibility_verdict="UNDETERMINED",
        )
        == "UNDETERMINED"
    )
    assert (
        classify_schedule_completeness(
            total_tasks=2,
            scheduled_tasks_count=0,
            unscheduled_tasks_count=2,
            available_minutes=0,
            schedulable_ratio=0.0,
            feasibility_verdict="EXPLICIT_UNSCHEDULABLE",
        )
        == "INFEASIBLE"
    )
    assert (
        classify_schedule_completeness(
            total_tasks=4,
            scheduled_tasks_count=1,
            unscheduled_tasks_count=3,
            available_minutes=120,
            schedulable_ratio=0.2,
            feasibility_verdict="EXPLICIT_UNSCHEDULABLE",
        )
        == "INFEASIBLE"
    )
    assert (
        classify_schedule_completeness(
            total_tasks=2,
            scheduled_tasks_count=1,
            unscheduled_tasks_count=1,
            available_minutes=120,
            schedulable_ratio=0.5,
            feasibility_verdict="EXPLICIT_UNSCHEDULABLE",
            allow_partial_schedule=False,
        )
        == "INFEASIBLE"
    )


# =============================================================================
# 2. DEF-03: Fail-closed on infeasible/empty schedule + Quota Release
# =============================================================================


@pytest.mark.asyncio
async def test_def03_zero_availability_fails_closed_without_retry_or_valid_result() -> None:
    mid = uuid7()
    canned = {
        "tasks": [
            _valid_task(
                mid, minutes=60, scheduled_date=None, scheduled_start=None, scheduled_end=None
            )
        ],
        "dependencies": [],
    }
    llm = _CountingLLM([canned, canned, canned])
    gate = ProposalValidationGateOrchestrator(llm_provider=llm, enable_tier3_judge=False)
    avail_zero = AvailabilityConfigurationDTO(
        mode="MODE_A",
        default_daily_quota_minutes=0,
        disabled_weekdays=frozenset(
            {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}
        ),
    )

    with pytest.raises(PlanInfeasibleError):
        await gate.generate_and_validate_proposal_with_retry(
            system_prompt="sys",
            user_prompt="usr",
            response_schema=None,
            availability=avail_zero,
            valid_milestone_ids={mid},
            start_date=date(2026, 11, 16),
            current_roadmap_target_date=date(2026, 11, 20),
            deterministic_allocation=True,
            allow_partial_schedule=True,
            max_retries=2,
        )
    assert llm.calls == 1


@pytest.mark.asyncio
async def test_def03_ratio_below_25_percent_fails_closed_even_with_allow_partial() -> None:
    mid = uuid7()
    # 5 tasks x 60m = 300m required; 60m available -> only 1 task scheduled (ratio = 0.20 < 0.25)
    canned = {
        "tasks": [
            _valid_task(
                mid,
                task_id=f"t-{i}",
                title=f"Bài {i}",
                minutes=60,
                scheduled_date=None,
                scheduled_start=None,
                scheduled_end=None,
            )
            for i in range(5)
        ],
        "dependencies": [],
    }
    llm = _CountingLLM([canned, canned, canned])
    gate = ProposalValidationGateOrchestrator(llm_provider=llm, enable_tier3_judge=False)
    avail = AvailabilityConfigurationDTO(mode="MODE_A", default_daily_quota_minutes=60)

    with pytest.raises(PlanInfeasibleError) as exc_info:
        await gate.generate_and_validate_proposal_with_retry(
            system_prompt="sys",
            user_prompt="usr",
            response_schema=None,
            availability=avail,
            valid_milestone_ids={mid},
            start_date=date(2026, 11, 16),
            current_roadmap_target_date=date(2026, 11, 16),
            deterministic_allocation=True,
            allow_partial_schedule=True,
            max_retries=2,
        )
    assert exc_info.value.schedulable_ratio < 0.25
    assert llm.calls == 1


@pytest.mark.asyncio
async def test_def03_execute_generation_use_case_releases_quota_and_saves_no_draft_on_zero_capacity() -> (
    None
):
    now = datetime(2026, 11, 16, 8, 0, tzinfo=UTC)
    user_id = uuid7()
    goal_id = uuid7()
    roadmap_id = uuid7()
    job_id = uuid7()
    reservation_id = uuid7()
    ms = _milestone(roadmap_id, effort=60)
    goal = Goal(
        id=goal_id,
        user_id=user_id,
        title="Học Python",
        raw_description="Python basics",
        target_date=date(2026, 11, 20),
        status=GoalStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
    roadmap = Roadmap(
        id=roadmap_id,
        user_id=user_id,
        goal_id=goal_id,
        title="Python Roadmap",
        start_date=date(2026, 11, 16),
        target_date=date(2026, 11, 20),
        status=RoadmapStatus.INITIALIZED,
        created_at=now,
        updated_at=now,
    )
    avail = AvailabilitySnapshotDTO(
        user_id=user_id,
        mode="MODE_B",
        daily_cap_minutes=0,
        weekly_capacity_minutes=0,
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
    llm_payload = {
        "tasks": [
            _valid_task(
                ms.id,
                task_id="t1",
                minutes=60,
                scheduled_date=None,
                scheduled_start=None,
                scheduled_end=None,
            )
        ],
        "dependencies": [],
    }
    quota = _RecordingQuotaFacade()
    sse = InMemorySseJobStore()
    await sse.create_job(
        job_id=job_id,
        user_id=user_id,
        roadmap_id=roadmap_id,
        reservation_id=reservation_id,
        job_type="SCHEDULE_PROPOSAL_GEN",
        operation=f"SCHEDULE_PROPOSAL_GEN:{roadmap_id}",
    )
    proposal_repo = _FakeProposalRepo()
    uc = ExecuteScheduleProposalGenerationUseCase(
        goal_repo=_FakeGoalRepo(goal),  # type: ignore[arg-type]
        roadmap_repo=_FakeRoadmapRepo(roadmap),  # type: ignore[arg-type]
        milestone_repo=_FakeMilestoneRepo([ms]),  # type: ignore[arg-type]
        proposal_repo=proposal_repo,  # type: ignore[arg-type]
        availability_query_port=_FakeAvailabilityPort(avail),  # type: ignore[arg-type]
        learner_profile_port=type(
            "LP",
            (),
            {
                "get_learner_profile": staticmethod(
                    lambda uid: _async_val(LearnerProfileDTO(user_id=uid))
                )
            },
        )(),  # type: ignore[arg-type]
        execution_sync_port=_FakeExecSyncPort(),  # type: ignore[arg-type]
        quota_facade=quota,  # type: ignore[arg-type]
        llm_provider=_CountingLLM([llm_payload]),
        sse_job_store=sse,
        uow=_FakeUoW(),  # type: ignore[arg-type]
        enable_tier3_judge=False,
    )

    with pytest.raises(PlanInfeasibleError):
        await uc.execute(
            job_id=job_id,
            user_id=user_id,
            roadmap_id=roadmap_id,
            reservation_id=reservation_id,
            now=now,
        )

    assert len(quota.committed) == 0
    assert len(quota.released) == 1
    assert quota.released[0][0] == reservation_id
    assert len(proposal_repo.proposals) == 0


async def _async_val(val: Any) -> Any:
    return val


# =============================================================================
# 3. Useless LLM Retry Suppression on Hard Impossibility
# =============================================================================


@pytest.mark.asyncio
async def test_suppresses_llm_retry_on_task_exceeds_continuous_slot() -> None:
    mid = uuid7()
    # Non-splittable 120m task vs 90m max slot -> TASK_EXCEEDS_CONTINUOUS_SLOT, 0 scheduled
    canned = {
        "tasks": [
            _valid_task(
                mid,
                task_id="t1",
                minutes=120,
                is_non_splittable=True,
                scheduled_date=None,
                scheduled_start=None,
                scheduled_end=None,
            )
        ],
        "dependencies": [],
    }
    llm = _CountingLLM([canned, canned, canned])
    gate = ProposalValidationGateOrchestrator(llm_provider=llm, enable_tier3_judge=False)
    avail = AvailabilityConfigurationDTO(
        mode="MODE_B",
        availability_slots=[
            AvailabilitySlotDTO(day_of_week="monday", start_time="19:00", end_time="20:30")
        ],
    )

    with pytest.raises(PlanInfeasibleError):
        await gate.generate_and_validate_proposal_with_retry(
            system_prompt="sys",
            user_prompt="usr",
            response_schema=None,
            availability=avail,
            valid_milestone_ids={mid},
            start_date=date(2026, 11, 16),
            current_roadmap_target_date=date(2026, 11, 20),
            deterministic_allocation=True,
            max_retries=2,
        )
    assert llm.calls == 1


@pytest.mark.asyncio
async def test_suppresses_llm_retry_on_critical_path_exceeded_window() -> None:
    mid = uuid7()
    # 2 tasks with mandatory dependency: 90m + 90m = 180m critical path across only 1 day of 90m slot
    canned = {
        "tasks": [
            _valid_task(
                mid,
                task_id="t1",
                title="Bước 1",
                minutes=90,
                scheduled_date=None,
                scheduled_start=None,
                scheduled_end=None,
            ),
            _valid_task(
                mid,
                task_id="t2",
                title="Bước 2",
                minutes=90,
                scheduled_date=None,
                scheduled_start=None,
                scheduled_end=None,
            ),
        ],
        "dependencies": [{"predecessor_id": "t1", "successor_id": "t2", "is_mandatory": True}],
    }
    llm = _CountingLLM([canned, canned, canned])
    gate = ProposalValidationGateOrchestrator(llm_provider=llm, enable_tier3_judge=False)
    avail = AvailabilityConfigurationDTO(
        mode="MODE_B",
        availability_slots=[
            AvailabilitySlotDTO(day_of_week="monday", start_time="19:00", end_time="20:30")
        ],
    )

    res = await gate.generate_and_validate_proposal_with_retry(
        system_prompt="sys",
        user_prompt="usr",
        response_schema=None,
        availability=avail,
        valid_milestone_ids={mid},
        start_date=date(2026, 11, 16),
        current_roadmap_target_date=date(2026, 11, 16),
        deterministic_allocation=True,
        max_retries=2,
    )
    # t1 (90m) fits Monday -> 50% scheduled (PARTIAL), t2 fails CRITICAL_PATH_EXCEEDED_WINDOW
    # Must NOT waste an LLM retry even though req_mins (180) vs avail_mins (90)
    assert llm.calls == 1
    assert res.attempts_used == 1
    assert res.schedule_completeness_status == "PARTIAL"


@pytest.mark.asyncio
async def test_suppresses_llm_retry_on_calendar_conflict_saturation() -> None:
    mid = uuid7()
    canned = {
        "tasks": [
            _valid_task(
                mid,
                task_id="t1",
                title="Bài 1",
                minutes=90,
                scheduled_date=None,
                scheduled_start=None,
                scheduled_end=None,
            )
        ],
        "dependencies": [],
    }
    existing = [
        ExistingScheduledTaskDTO(
            task_id=uuid7(),
            roadmap_id=uuid7(),
            milestone_id=uuid7(),
            title="Lịch đã chiếm chỗ",
            estimated_minutes=120,
            scheduled_date=date(2026, 11, 16),
            scheduled_start=datetime(2026, 11, 16, 19, 0, tzinfo=UTC),
            scheduled_end=datetime(2026, 11, 16, 21, 0, tzinfo=UTC),
            status="TODO",
            roadmap_target_date=date(2026, 11, 16),
        )
    ]
    llm = _CountingLLM([canned, canned, canned])
    gate = ProposalValidationGateOrchestrator(llm_provider=llm, enable_tier3_judge=False)
    avail = AvailabilityConfigurationDTO(
        mode="MODE_B",
        availability_slots=[
            AvailabilitySlotDTO(day_of_week="monday", start_time="19:00", end_time="21:00")
        ],
    )

    with pytest.raises(PlanInfeasibleError):
        await gate.generate_and_validate_proposal_with_retry(
            system_prompt="sys",
            user_prompt="usr",
            response_schema=None,
            availability=avail,
            existing_tasks=existing,
            valid_milestone_ids={mid},
            start_date=date(2026, 11, 16),
            current_roadmap_target_date=date(2026, 11, 16),
            deterministic_allocation=True,
            max_retries=2,
        )
    assert llm.calls == 1


# =============================================================================
# 4. Empty schedule_blocks: [] must NOT bypass Tier 2 Mode A / Mode B checks
# =============================================================================


def test_empty_schedule_blocks_does_not_bypass_tier2_mode_a_and_mode_b() -> None:
    mid = uuid7()
    # Mode A: 180m scheduled on Monday vs 120m quota, with schedule_blocks: []
    mode_a_proposal = {
        "tasks": [
            _valid_task(
                mid,
                minutes=180,
                scheduled_date="2026-11-16",
                scheduled_start=None,
                scheduled_end=None,
            )
        ],
        "schedule_blocks": [],
        "dependencies": [],
    }
    mode_a_avail = AvailabilityConfigurationDTO(
        mode="MODE_A",
        daily_quota_minutes={"monday": 120},
        default_daily_quota_minutes=120,
    )
    a_violations, _ = run_tier2_gate(mode_a_proposal, availability=mode_a_avail)
    assert len(a_violations) >= 1

    # Mode B: task outside fixed slot (10:00-11:00 vs 19:00-21:00), with schedule_blocks: []
    mode_b_proposal = {
        "tasks": [
            _valid_task(
                mid,
                minutes=60,
                scheduled_date="2026-11-16",
                scheduled_start="2026-11-16T10:00:00+00:00",
                scheduled_end="2026-11-16T11:00:00+00:00",
            )
        ],
        "schedule_blocks": [],
        "dependencies": [],
    }
    mode_b_avail = AvailabilityConfigurationDTO(
        mode="MODE_B",
        availability_slots=[
            AvailabilitySlotDTO(day_of_week="monday", start_time="19:00", end_time="21:00")
        ],
    )
    b_violations, _ = run_tier2_gate(mode_b_proposal, availability=mode_b_avail)
    assert len(b_violations) >= 1


def test_assess_schedule_feasibility_ignores_empty_or_invalid_scheduled_date_strings() -> None:
    res = assess_schedule_feasibility(
        [
            {"estimated_minutes": 60, "scheduled_date": ""},
            {"estimated_minutes": 60, "scheduled_date": "not-a-date"},
        ],
        available_minutes=120,
    )
    assert res.scheduled_minutes == 0
    assert res.status is FeasibilityStatus.INFEASIBLE


# =============================================================================
# 5. ApplyScheduleProposalUseCase Independent Safety & UpdateScheduleProposalUseCase
# =============================================================================


def _build_apply_uc(
    *,
    roadmap: Roadmap,
    milestone: Milestone,
    proposal: ScheduleProposal,
    avail_snap: AvailabilitySnapshotDTO,
) -> tuple[ApplyScheduleProposalUseCase, _FakeAvailabilityPort, _FakeExecSyncPort, _FakeUoW]:
    avail_port = _FakeAvailabilityPort(avail_snap)
    sync_port = _FakeExecSyncPort()
    uow = _FakeUoW()
    uc = ApplyScheduleProposalUseCase(
        roadmap_repo=_FakeRoadmapRepo(roadmap),  # type: ignore[arg-type]
        milestone_repo=_FakeMilestoneRepo([milestone]),  # type: ignore[arg-type]
        proposal_repo=_FakeProposalRepo(proposal),  # type: ignore[arg-type]
        schedule_repo=_FakeScheduleRepo(),  # type: ignore[arg-type]
        block_repo=_FakeBlockRepo(),  # type: ignore[arg-type]
        availability_query_port=avail_port,  # type: ignore[arg-type]
        execution_sync_port=sync_port,  # type: ignore[arg-type]
        schedule_change_log_port=_FakeChangeLogPort(),  # type: ignore[arg-type]
        uow=uow,  # type: ignore[arg-type]
    )
    return uc, avail_port, sync_port, uow


@pytest.mark.asyncio
async def test_apply_rejects_discarded_proposal_before_any_side_effects() -> None:
    now = datetime(2026, 11, 16, 8, 0, tzinfo=UTC)
    user_id = uuid7()
    roadmap_id = uuid7()
    ms = _milestone(roadmap_id)
    roadmap = Roadmap(
        id=roadmap_id,
        user_id=user_id,
        goal_id=uuid7(),
        title="Roadmap",
        start_date=date(2026, 11, 16),
        target_date=date(2026, 11, 20),
        status=RoadmapStatus.INITIALIZED,
        created_at=now,
        updated_at=now,
    )
    proposal = ScheduleProposal(
        id=uuid7(),
        roadmap_id=roadmap_id,
        user_id=user_id,
        proposal_data={"tasks": [_valid_task(ms.id)], "feasibility_verdict": "VERIFIED_FEASIBLE"},
        status=ScheduleProposalStatus.DISCARDED,
        created_at=now,
        updated_at=now,
    )
    avail = AvailabilitySnapshotDTO(
        user_id=user_id, mode="MODE_A", daily_cap_minutes=120, weekly_capacity_minutes=600
    )
    uc, avail_port, sync_port, uow = _build_apply_uc(
        roadmap=roadmap, milestone=ms, proposal=proposal, avail_snap=avail
    )

    with pytest.raises(PlanningDomainError):
        await uc.execute(user_id=user_id, roadmap_id=roadmap_id, proposal_id=proposal.id, now=now)

    assert avail_port.calls == 0
    assert sync_port.get_tasks_calls == 0
    assert sync_port.sync_calls == 0
    assert uow.commits == 0


@pytest.mark.asyncio
async def test_apply_rejects_inconsistent_task_and_unscheduled_reason_bypass() -> None:
    now = datetime(2026, 11, 16, 8, 0, tzinfo=UTC)
    user_id = uuid7()
    roadmap_id = uuid7()
    ms = _milestone(roadmap_id, effort=60)
    roadmap = Roadmap(
        id=roadmap_id,
        user_id=user_id,
        goal_id=uuid7(),
        title="Roadmap",
        start_date=date(2026, 11, 16),
        target_date=date(2026, 11, 20),
        status=RoadmapStatus.INITIALIZED,
        created_at=now,
        updated_at=now,
    )
    avail = AvailabilitySnapshotDTO(
        user_id=user_id, mode="MODE_A", daily_cap_minutes=120, weekly_capacity_minutes=600
    )

    # Case A: Both valid scheduled_date AND non-empty unscheduled_reason -> INCONSISTENT_TASK_SCHEDULE_STATE
    inconsistent_prop = ScheduleProposal(
        id=uuid7(),
        roadmap_id=roadmap_id,
        user_id=user_id,
        proposal_data={
            "feasibility_verdict": "VERIFIED_FEASIBLE",
            "tasks": [_valid_task(ms.id, unscheduled_reason="DEADLINE_CAPACITY_EXCEEDED")],
        },
        status=ScheduleProposalStatus.DRAFT,
        created_at=now,
        updated_at=now,
    )
    uc_a, _, _, _ = _build_apply_uc(
        roadmap=roadmap, milestone=ms, proposal=inconsistent_prop, avail_snap=avail
    )
    with pytest.raises(ProposalValidationGateError) as exc_a:
        await uc_a.execute(
            user_id=user_id,
            roadmap_id=roadmap_id,
            proposal_id=inconsistent_prop.id,
            confirm_partial_schedule=True,
            now=now,
        )
    assert any(
        v.get("rule_code") == "INCONSISTENT_TASK_SCHEDULE_STATE" for v in exc_a.value.violations
    )

    # Case B: unscheduled_reason set on 0-min/unscheduled task when feasibility might look FEASIBLE
    # -> MUST require confirm_partial_schedule=True
    bypass_prop = ScheduleProposal(
        id=uuid7(),
        roadmap_id=roadmap_id,
        user_id=user_id,
        proposal_data={
            "feasibility_verdict": "EXPLICIT_UNSCHEDULABLE",
            "tasks": [
                _valid_task(ms.id, task_id="t1", title="Bài 1", minutes=60),
                _valid_task(
                    ms.id,
                    task_id="t2",
                    title="Bài 2",
                    minutes=0,
                    scheduled_date=None,
                    scheduled_start=None,
                    scheduled_end=None,
                    unscheduled_reason="BACKLOG",
                ),
            ],
        },
        status=ScheduleProposalStatus.DRAFT,
        created_at=now,
        updated_at=now,
    )
    uc_b, _, _, _ = _build_apply_uc(
        roadmap=roadmap, milestone=ms, proposal=bypass_prop, avail_snap=avail
    )
    with pytest.raises(PartialScheduleConfirmationRequiredError):
        await uc_b.execute(
            user_id=user_id,
            roadmap_id=roadmap_id,
            proposal_id=bypass_prop.id,
            confirm_partial_schedule=False,
            now=now,
        )


@pytest.mark.asyncio
async def test_apply_rejects_undetermined_and_judge_failed_or_error_statuses() -> None:
    now = datetime(2026, 11, 16, 8, 0, tzinfo=UTC)
    user_id = uuid7()
    roadmap_id = uuid7()
    ms = _milestone(roadmap_id, effort=60)
    roadmap = Roadmap(
        id=roadmap_id,
        user_id=user_id,
        goal_id=uuid7(),
        title="Roadmap",
        start_date=date(2026, 11, 16),
        target_date=date(2026, 11, 20),
        status=RoadmapStatus.INITIALIZED,
        created_at=now,
        updated_at=now,
    )
    avail = AvailabilitySnapshotDTO(
        user_id=user_id, mode="MODE_A", daily_cap_minutes=120, weekly_capacity_minutes=600
    )

    # UNDETERMINED proposal (empty tasks or feasibility_verdict="UNDETERMINED") -> ProposalValidationGateError
    undetermined_prop = ScheduleProposal(
        id=uuid7(),
        roadmap_id=roadmap_id,
        user_id=user_id,
        proposal_data={"feasibility_verdict": "UNDETERMINED", "tasks": [_valid_task(ms.id)]},
        status=ScheduleProposalStatus.DRAFT,
        created_at=now,
        updated_at=now,
    )
    uc_u, _, _, _ = _build_apply_uc(
        roadmap=roadmap, milestone=ms, proposal=undetermined_prop, avail_snap=avail
    )
    with pytest.raises(ProposalValidationGateError):
        await uc_u.execute(
            user_id=user_id, roadmap_id=roadmap_id, proposal_id=undetermined_prop.id, now=now
        )

    # Judge status FAILED and ERROR require confirmation
    for j_status in ("FAILED", "ERROR"):
        judge_prop = ScheduleProposal(
            id=uuid7(),
            roadmap_id=roadmap_id,
            user_id=user_id,
            proposal_data={
                "feasibility_verdict": "VERIFIED_FEASIBLE",
                "judge_status": j_status,
                "tasks": [_valid_task(ms.id, minutes=60)],
            },
            status=ScheduleProposalStatus.DRAFT,
            created_at=now,
            updated_at=now,
        )
        uc_j, _, _, _ = _build_apply_uc(
            roadmap=roadmap, milestone=ms, proposal=judge_prop, avail_snap=avail
        )
        with pytest.raises(JudgeReviewConfirmationRequiredError):
            await uc_j.execute(
                user_id=user_id,
                roadmap_id=roadmap_id,
                proposal_id=judge_prop.id,
                confirm_warnings=False,
                now=now,
            )


@pytest.mark.asyncio
async def test_update_schedule_proposal_refreshes_counts_and_completeness_status() -> None:
    now = datetime(2026, 11, 16, 8, 0, tzinfo=UTC)
    user_id = uuid7()
    roadmap_id = uuid7()
    ms = _milestone(roadmap_id, effort=120)
    roadmap = Roadmap(
        id=roadmap_id,
        user_id=user_id,
        goal_id=uuid7(),
        title="Roadmap",
        start_date=date(2026, 11, 16),
        target_date=date(2026, 11, 16),
        status=RoadmapStatus.INITIALIZED,
        created_at=now,
        updated_at=now,
    )
    proposal = ScheduleProposal(
        id=uuid7(),
        roadmap_id=roadmap_id,
        user_id=user_id,
        proposal_data={
            "tasks": [_valid_task(ms.id, task_id="t1", minutes=60)],
            "scheduled_tasks_count": 99,
            "unscheduled_tasks_count": 99,
            "unscheduled_tasks": [{"task_id": "stale"}],
            "feasibility_verdict": "STALE",
            "schedule_completeness_status": "PARTIAL",
        },
        status=ScheduleProposalStatus.DRAFT,
        created_at=now,
        updated_at=now,
    )
    avail = AvailabilitySnapshotDTO(
        user_id=user_id, mode="MODE_A", daily_cap_minutes=120, weekly_capacity_minutes=600
    )
    uc = UpdateScheduleProposalUseCase(
        roadmap_repo=_FakeRoadmapRepo(roadmap),  # type: ignore[arg-type]
        milestone_repo=_FakeMilestoneRepo([ms]),  # type: ignore[arg-type]
        proposal_repo=_FakeProposalRepo(proposal),  # type: ignore[arg-type]
        availability_query_port=_FakeAvailabilityPort(avail),  # type: ignore[arg-type]
        execution_sync_port=_FakeExecSyncPort(),  # type: ignore[arg-type]
        uow=_FakeUoW(),  # type: ignore[arg-type]
    )

    view = await uc.execute(
        user_id=user_id,
        roadmap_id=roadmap_id,
        proposal_id=proposal.id,
        tasks=[_valid_task(ms.id, task_id="t1", minutes=60)],
        dependencies=[],
        now=now,
    )
    pdata = view.proposal.proposal_data
    assert pdata["scheduled_tasks_count"] == 1
    assert pdata["unscheduled_tasks_count"] == 0
    assert pdata["unscheduled_tasks"] == []
    assert pdata["feasibility_verdict"] == "VERIFIED_FEASIBLE"
    assert pdata["schedule_completeness_status"] == "FULL"
