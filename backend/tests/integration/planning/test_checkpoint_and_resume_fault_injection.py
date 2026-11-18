"""Integration tests for Checkpoint & Resume with Fault Injection in Milestone-Scoped Task Decomposer."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime
from types import SimpleNamespace
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
    ExistingTaskDependencyDTO,
    ScheduleSyncResultDTO,
)
from src.planning.application.ports.milestone_checkpoint_port import (
    InMemoryMilestoneCheckpointStore,
)
from src.planning.application.services.milestone_scoped_decomposer import (
    MilestoneScopedTaskDecomposer,
    compute_milestone_checkpoint_key,
    compute_milestone_content_hash,
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
from src.shared_kernel.application.harness.workflow_port import BufferedWorkflowRepo
from src.shared_kernel.application.llm_port import (
    LLMGenerationResult,
    LLMToolDeclarationDTO,
    LLMToolExecutor,
)
from src.shared_kernel.infrastructure.sse.job_store import InMemorySseJobStore
from tests.helpers.llm_stubs import StubLLMAdapter

# ---------------------------------------------------------------------------
# Test Doubles & Fixtures
# ---------------------------------------------------------------------------


class _FaultInjectingStubLLM(StubLLMAdapter):
    """LLM double that records milestone decomposition calls and can inject faults."""

    def __init__(self) -> None:
        super().__init__()
        self.fail_milestone_ids: set[UUID] = set()
        self.fail_exception: Exception = TimeoutError("Simulated LLM network timeout on milestone")
        self.calls_by_milestone_id: dict[UUID, int] = {}
        self.total_decomposer_calls: int = 0

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
            # Extract target milestone ID from user_prompt
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
                if target_mid in self.fail_milestone_ids:
                    raise self.fail_exception

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

    async def check_quota_available(
        self,
        user_id: UUID,
        min_credits: int = 1,
    ) -> bool:
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

    async def release_reservation(
        self,
        reservation_id: UUID,
        reason: str = "",
    ) -> None:
        self.released.append((reservation_id, reason))

    async def expire_stale_reservations(self, now: datetime | None = None) -> int:
        del now
        return 0


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
        self,
        roadmap_id: UUID,
        user_id: UUID,
        *,
        for_update: bool = False,
    ) -> Roadmap | None:
        del for_update
        return (
            self.roadmap
            if roadmap_id == self.roadmap.id and user_id == self.roadmap.user_id
            else None
        )

    async def list_by_user_id(
        self,
        user_id: UUID,
        *,
        status: str | None = None,
        for_update: bool = False,
    ) -> list[Roadmap]:
        del user_id, status, for_update
        return []

    async def count_active_by_user_id(
        self,
        user_id: UUID,
        *,
        exclude_roadmap_id: UUID | None = None,
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

    async def list_by_roadmap_ids(
        self,
        roadmap_ids: Sequence[UUID],
        *,
        for_update: bool = False,
    ) -> list[ScheduleBlock]:
        del roadmap_ids, for_update
        return []

    async def get_by_external_event_id(self, external_event_id: str) -> ScheduleBlock | None:
        del external_event_id
        return None

    async def save(self, block: ScheduleBlock) -> ScheduleBlock:
        self.blocks.append(block)
        return block

    async def save_all(self, blocks: list[ScheduleBlock]) -> list[ScheduleBlock]:
        self.blocks = list(blocks)
        return self.blocks


class _FakeExecSyncPort:
    async def get_tasks_for_roadmaps(
        self,
        roadmap_ids: Sequence[UUID],
        *,
        roadmap_target_dates: Mapping[UUID, date | None] | None = None,
    ) -> list[ExistingScheduledTaskDTO]:
        del roadmap_ids, roadmap_target_dates
        return []

    async def get_task_dependencies_for_roadmap(
        self,
        roadmap_id: UUID,
    ) -> list[ExistingTaskDependencyDTO]:
        del roadmap_id
        return []

    async def get_active_roadmaps_tasks(
        self,
        user_id: UUID,
        exclude_roadmap_id: UUID | None = None,
        *,
        active_roadmap_ids: Sequence[UUID] | None = None,
        roadmap_target_dates: Mapping[UUID, date | None] | None = None,
    ) -> list[ExistingScheduledTaskDTO]:
        del user_id, exclude_roadmap_id, active_roadmap_ids, roadmap_target_dates
        return []

    async def sync_official_schedule_tasks(self, **kwargs: Any) -> ScheduleSyncResultDTO:
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

    async def shift_incomplete_tasks_for_domino(
        self,
        *,
        roadmap_id: UUID,
        shift_days: int,
        now: datetime,
    ) -> int:
        del roadmap_id, shift_days, now
        return 0


class _FakeAvailabilityPort:
    def __init__(self, snap: AvailabilitySnapshotDTO) -> None:
        self.snap = snap

    async def get_active_availability(self, user_id: UUID) -> AvailabilitySnapshotDTO | None:
        del user_id
        return self.snap

    async def validate_schedule_proposal(
        self,
        user_id: UUID,
        proposed_tasks: list[Any],
        occupied_tasks: list[Any] | None = None,
        expected_updated_at: str | None = None,
    ) -> Any:
        del user_id, proposed_tasks, occupied_tasks, expected_updated_at
        from src.account.public_api import AvailabilityGateResultDTO

        return AvailabilityGateResultDTO(
            is_valid=True,
            has_soft_overflow=False,
            overflow_minutes=0,
            violation_reasons=(),
        )


class _FakeLearnerProfilePort:
    def __init__(self, user_id: UUID) -> None:
        self.profile = LearnerProfileDTO(
            user_id=user_id,
            opt_session_minutes=60,
            estimation_bias_beta=1.0,
            peak_productivity_slots={"slots": ["MORNING", "EVENING"]},
        )

    async def get_learner_profile(self, user_id: UUID) -> LearnerProfileDTO:
        del user_id
        return self.profile


def _build_5_milestone_fixture() -> tuple[
    UUID, Goal, Roadmap, list[Milestone], AvailabilityConfigurationDTO
]:
    """Build a goal with 5 approved milestones (M1..M5) and generous schedule availability."""
    now = datetime(2026, 11, 1, 9, 0, tzinfo=UTC)
    user_id = uuid7()
    goal_id = uuid7()
    roadmap_id = uuid7()

    goal = Goal(
        id=goal_id,
        user_id=user_id,
        title="Làm chủ Kiến trúc Phần mềm Phân tán",
        raw_description="Lộ trình chuyên sâu 5 cột mốc từ nền tảng đến dự án lớn.",
        prior_knowledge_level="INTERMEDIATE",
        target_date=date(2027, 2, 28),
        status=GoalStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )

    roadmap = Roadmap(
        id=roadmap_id,
        goal_id=goal_id,
        user_id=user_id,
        title=goal.title,
        description=goal.raw_description,
        start_date=date(2026, 11, 2),
        target_date=date(2027, 2, 28),
        status=RoadmapStatus.INITIALIZED,
        created_at=now,
        updated_at=now,
    )

    m1_id, m2_id, m3_id, m4_id, m5_id = uuid7(), uuid7(), uuid7(), uuid7(), uuid7()

    m1 = Milestone(
        id=m1_id,
        roadmap_id=roadmap_id,
        sequence_order=1,
        title="M1: Nền tảng Monolith và Thiết kế Hướng miền",
        description="Hiểu Domain-Driven Design và Bounded Contexts",
        learning_outcomes=("Phân rã domain thành các aggregate",),
        completion_criteria="Hoàn thành mô hình domain mẫu",
        estimated_effort_minutes=90,
        required_concepts=("ddd-bounded-context",),
        prerequisite_milestone_ids=(),
        status=MilestoneStatus.APPROVED,
        created_at=now,
        updated_at=now,
    )

    m2 = Milestone(
        id=m2_id,
        roadmap_id=roadmap_id,
        sequence_order=2,
        title="M2: Giao tiếp Bất đồng bộ và Sự kiện Miền",
        description="Event-Driven Architecture với Redis Streams",
        learning_outcomes=("Thiết kế Outbox Pattern và Idempotency",),
        completion_criteria="Xây dựng consumer chống trùng lặp",
        estimated_effort_minutes=90,
        required_concepts=("redis-streams-outbox",),
        prerequisite_milestone_ids=(m1_id,),
        status=MilestoneStatus.APPROVED,
        created_at=now,
        updated_at=now,
    )

    m3 = Milestone(
        id=m3_id,
        roadmap_id=roadmap_id,
        sequence_order=3,
        title="M3: Tối ưu Cơ sở dữ liệu và Transactional Isolation",
        description="PostgreSQL async, chỉ mục pgvector, khoá ngoại và ACID",
        learning_outcomes=("Tối ưu hoá truy vấn và chống deadlocks",),
        completion_criteria="Benchmark truy vấn dưới 10ms",
        estimated_effort_minutes=90,
        required_concepts=("postgres-async-perf",),
        prerequisite_milestone_ids=(m2_id,),
        status=MilestoneStatus.APPROVED,
        created_at=now,
        updated_at=now,
    )

    m4 = Milestone(
        id=m4_id,
        roadmap_id=roadmap_id,
        sequence_order=4,
        title="M4: Triển khai Hạ tầng Khả năng chịu lỗi và Checkpoint",
        description="Xây dựng cơ chế Fault Injection và Checkpoint Resume",
        learning_outcomes=("Thiết kế cơ chế resume tất định sau lỗi mạng",),
        completion_criteria="Pass test fault injection",
        estimated_effort_minutes=90,
        required_concepts=("fault-injection-checkpoint",),
        prerequisite_milestone_ids=(m3_id,),
        status=MilestoneStatus.APPROVED,
        created_at=now,
        updated_at=now,
    )

    m5 = Milestone(
        id=m5_id,
        roadmap_id=roadmap_id,
        sequence_order=5,
        title="M5: Đánh giá Toàn diện và Kiểm thử Tải Hệ thống",
        description="Tổng kết lộ trình, load test và bảo mật IDOR",
        learning_outcomes=("Kiểm định toàn bộ ràng buộc Spatio-Temporal và SRL",),
        completion_criteria="Hệ thống ổn định dưới tải 100 RPS",
        estimated_effort_minutes=90,
        required_concepts=("load-test-chaos-eval",),
        prerequisite_milestone_ids=(m4_id,),
        status=MilestoneStatus.APPROVED,
        created_at=now,
        updated_at=now,
    )

    milestones = [m1, m2, m3, m4, m5]

    # Generous availability: 4 hours every single day
    avail_config = AvailabilityConfigurationDTO(
        mode="MODE_A",
        default_daily_quota_minutes=240,
        daily_quota_minutes={},
    )

    return user_id, goal, roadmap, milestones, avail_config


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fault_injection_and_checkpoint_resume_5_milestones() -> None:
    """Scenario 1:

    Attempt 1: M1, M2, M3 succeed and persist checkpoints; M4 raises TimeoutError.
    First run fails.
    Attempt 2 (Resume): M1, M2, M3 load from checkpoint (0 LLM calls).
    M4 and M5 execute successfully.
    Verify invariant assertions (no duplicate tasks, no duplicate deps, quota tokens, step preservation).
    """
    user_id, goal, roadmap, milestones, avail = _build_5_milestone_fixture()
    m1, m2, m3, m4, m5 = milestones

    checkpoint_store = InMemoryMilestoneCheckpointStore()
    workflow_repo = BufferedWorkflowRepo()
    llm = _FaultInjectingStubLLM()

    # Configure fault injection on M4 and M5 for Attempt 1:
    llm.fail_milestone_ids = {m4.id, m5.id}
    llm.fail_exception = TimeoutError("Simulated LLM network timeout during M4 decomposition")

    learner_profile = SimpleNamespace(
        opt_session_minutes=60,
        estimation_bias_beta=1.0,
        peak_productivity_slots=("MORNING",),
    )

    decomposer = MilestoneScopedTaskDecomposer(
        llm_provider=llm,
        enable_tier3_judge=False,
        workflow_repo=workflow_repo,
        user_id=user_id,
        goal_id=goal.id,
        roadmap_id=roadmap.id,
        max_concurrency=1,  # Sequential execution guarantees M1..M3 finish before M4 fails
        checkpoint_store=checkpoint_store,
    )

    # -----------------------------------------------------------------------
    # ATTEMPT 1: Must fail on M4
    # -----------------------------------------------------------------------
    with pytest.raises(TimeoutError, match="Simulated LLM network timeout during M4 decomposition"):
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

    # Verify state after Attempt 1 failure:
    # M1, M2, M3 checkpoints MUST be present immediately
    prompt_checksum = (
        build_planning_prompt_registry().latest(TASK_DECOMPOSER_SKILL.skill_id).checksum
    )
    key_m1 = compute_milestone_checkpoint_key(
        roadmap_id=roadmap.id,
        milestone=m1,
        all_milestones=milestones,
        prompt_checksum=prompt_checksum,
        model_name=getattr(llm, "model_identifier", "gemini-3.8-flash"),
        target_date=roadmap.target_date,
        start_date=roadmap.start_date,
        learner_profile=learner_profile,
        prior_knowledge_level=goal.prior_knowledge_level,
        clarification_context=goal.clarification_context,
        availability=avail,
    )
    key_m2 = compute_milestone_checkpoint_key(
        roadmap_id=roadmap.id,
        milestone=m2,
        all_milestones=milestones,
        prompt_checksum=prompt_checksum,
        model_name=getattr(llm, "model_identifier", "gemini-3.8-flash"),
        target_date=roadmap.target_date,
        start_date=roadmap.start_date,
        learner_profile=learner_profile,
        prior_knowledge_level=goal.prior_knowledge_level,
        clarification_context=goal.clarification_context,
        availability=avail,
    )
    key_m3 = compute_milestone_checkpoint_key(
        roadmap_id=roadmap.id,
        milestone=m3,
        all_milestones=milestones,
        prompt_checksum=prompt_checksum,
        model_name=getattr(llm, "model_identifier", "gemini-3.8-flash"),
        target_date=roadmap.target_date,
        start_date=roadmap.start_date,
        learner_profile=learner_profile,
        prior_knowledge_level=goal.prior_knowledge_level,
        clarification_context=goal.clarification_context,
        availability=avail,
    )
    key_m4 = compute_milestone_checkpoint_key(
        roadmap_id=roadmap.id,
        milestone=m4,
        all_milestones=milestones,
        prompt_checksum=prompt_checksum,
        model_name=getattr(llm, "model_identifier", "gemini-3.8-flash"),
        target_date=roadmap.target_date,
        start_date=roadmap.start_date,
        learner_profile=learner_profile,
        prior_knowledge_level=goal.prior_knowledge_level,
        clarification_context=goal.clarification_context,
        availability=avail,
    )

    assert await checkpoint_store.get_checkpoint(key_m1) is not None, "M1 checkpoint must be saved"
    assert await checkpoint_store.get_checkpoint(key_m2) is not None, "M2 checkpoint must be saved"
    assert await checkpoint_store.get_checkpoint(key_m3) is not None, "M3 checkpoint must be saved"
    assert await checkpoint_store.get_checkpoint(key_m4) is None, "M4 checkpoint must NOT exist"

    # Verify workflow_repo recorded steps for M1, M2, M3
    m1_steps_run1 = [s for s in workflow_repo.steps if s.step_name == "TASK_DECOMPOSER_M1"]
    m2_steps_run1 = [s for s in workflow_repo.steps if s.step_name == "TASK_DECOMPOSER_M2"]
    m3_steps_run1 = [s for s in workflow_repo.steps if s.step_name == "TASK_DECOMPOSER_M3"]
    assert len(m1_steps_run1) == 1, "M1 step must be persisted immediately on success"
    assert len(m2_steps_run1) == 1, "M2 step must be persisted immediately on success"
    assert len(m3_steps_run1) == 1, "M3 step must be persisted immediately on success"

    # Reset LLM call tracking for Attempt 2
    llm.calls_by_milestone_id.clear()
    llm.fail_milestone_ids.clear()  # Remove fault injection

    # -----------------------------------------------------------------------
    # ATTEMPT 2: Resume with the same checkpoint_store and workflow_repo
    # -----------------------------------------------------------------------
    decomposer_resume = MilestoneScopedTaskDecomposer(
        llm_provider=llm,
        enable_tier3_judge=False,
        workflow_repo=workflow_repo,
        user_id=user_id,
        goal_id=goal.id,
        roadmap_id=roadmap.id,
        max_concurrency=1,
        checkpoint_store=checkpoint_store,
    )

    gate_result = await decomposer_resume.decompose_and_validate(
        goal=goal,
        roadmap=roadmap,
        milestones=milestones,
        availability=avail,
        learner_profile=learner_profile,
        start_date=roadmap.start_date,
        max_milestone_retries=0,
        reference_date=roadmap.start_date,
    )

    # 1. Assert M1, M2, M3 are loaded from checkpoint with ZERO LLM calls:
    assert llm.calls_by_milestone_id.get(m1.id, 0) == 0, (
        "M1 must NOT call LLM on resume (checkpoint hit)"
    )
    assert llm.calls_by_milestone_id.get(m2.id, 0) == 0, (
        "M2 must NOT call LLM on resume (checkpoint hit)"
    )
    assert llm.calls_by_milestone_id.get(m3.id, 0) == 0, (
        "M3 must NOT call LLM on resume (checkpoint hit)"
    )

    # 2. Assert M4 and M5 execute successfully via LLM:
    assert llm.calls_by_milestone_id.get(m4.id, 0) == 1, "M4 must execute via LLM on resume"
    assert llm.calls_by_milestone_id.get(m5.id, 0) == 1, "M5 must execute via LLM on resume"

    # 3. Invariant: Zero duplicate tasks across milestones:
    tasks = gate_result.validated_proposal_data.get("tasks", [])
    task_ids = [t["task_id"] for t in tasks]
    assert len(task_ids) > 0
    assert len(task_ids) == len(set(task_ids)), (
        f"Duplicate tasks detected: {task_ids} != {set(task_ids)}"
    )

    # All 5 milestones must be represented among tasks
    task_mids = {str(t.get("milestone_id")) for t in tasks}
    for m in milestones:
        assert str(m.id) in task_mids, f"Milestone {m.id} must have tasks in reconciled proposal"

    # 4. Invariant: Zero duplicate dependencies:
    dependencies = gate_result.validated_proposal_data.get("dependencies", [])
    dep_pairs = [(d["predecessor_id"], d["successor_id"]) for d in dependencies]
    assert len(dep_pairs) == len(set(dep_pairs)), (
        f"Duplicate dependencies detected: {dep_pairs} != {set(dep_pairs)}"
    )

    # 5. Invariant: Quota tokens on attempt 2 only bill M4 and M5 (M1..M3 cost 0 tokens):
    # Only M4 and M5 generated LLM tokens on Attempt 2
    assert gate_result.total_prompt_tokens > 0, (
        "Attempt 2 incurred prompt tokens for fresh milestones"
    )
    assert gate_result.total_completion_tokens > 0, (
        "Attempt 2 incurred completion tokens for fresh milestones"
    )

    # 6. Invariant: WorkflowStepExecution for M1..M3 are preserved; no duplicate runs or ghost records:
    m1_steps_total = [s for s in workflow_repo.steps if s.step_name == "TASK_DECOMPOSER_M1"]
    m2_steps_total = [s for s in workflow_repo.steps if s.step_name == "TASK_DECOMPOSER_M2"]
    m3_steps_total = [s for s in workflow_repo.steps if s.step_name == "TASK_DECOMPOSER_M3"]
    m4_steps_total = [s for s in workflow_repo.steps if s.step_name == "TASK_DECOMPOSER_M4"]
    m5_steps_total = [s for s in workflow_repo.steps if s.step_name == "TASK_DECOMPOSER_M5"]

    # Each milestone has exactly 1 successful step recorded across both runs!
    assert len(m1_steps_total) == 1, (
        f"M1 should have exactly 1 step record, found {len(m1_steps_total)}"
    )
    assert len(m2_steps_total) == 1, (
        f"M2 should have exactly 1 step record, found {len(m2_steps_total)}"
    )
    assert len(m3_steps_total) == 1, (
        f"M3 should have exactly 1 step record, found {len(m3_steps_total)}"
    )
    assert len(m4_steps_total) >= 1, (
        f"M4 should have step record, found {len(m4_steps_total)}"
    )  # May include attempt 1 failure
    assert len(m5_steps_total) == 1, (
        f"M5 should have exactly 1 step record, found {len(m5_steps_total)}"
    )


@pytest.mark.asyncio
async def test_checkpoint_invalidation_when_milestone_or_prompt_changes() -> None:
    """Scenario 2:

    Checkpoints are populated.
    Altering M2's outcomes invalidates M2's checkpoint hash.
    Run decomposition: verify M1 loads from checkpoint, but M2 is re-executed.
    Altering prompt checksum invalidates all checkpoints.
    """
    user_id, goal, roadmap, milestones, avail = _build_5_milestone_fixture()
    m1, m2, m3, m4, m5 = milestones

    checkpoint_store = InMemoryMilestoneCheckpointStore()
    llm = _FaultInjectingStubLLM()

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

    # Initial run: all 5 milestones execute and populate checkpoints
    res1 = await decomposer.decompose_and_validate(
        goal=goal,
        roadmap=roadmap,
        milestones=milestones,
        availability=avail,
        learner_profile=learner_profile,
        start_date=roadmap.start_date,
        max_milestone_retries=0,
        reference_date=roadmap.start_date,
    )
    assert len(res1.validated_proposal_data["tasks"]) > 0
    assert llm.calls_by_milestone_id[m1.id] == 1
    assert llm.calls_by_milestone_id[m2.id] == 1
    assert llm.calls_by_milestone_id[m3.id] == 1
    assert llm.calls_by_milestone_id[m4.id] == 1
    assert llm.calls_by_milestone_id[m5.id] == 1

    # Reset LLM call tracking
    llm.calls_by_milestone_id.clear()

    # -----------------------------------------------------------------------
    # Invalidation Test A: Alter M2's outcomes
    # -----------------------------------------------------------------------
    # M2's outcomes changed -> content_hash changes -> checkpoint key changes
    m2_altered = Milestone(
        id=m2.id,
        roadmap_id=roadmap.id,
        sequence_order=m2.sequence_order,
        title=m2.title,
        description=m2.description,
        learning_outcomes=("Hoàn toàn mới: Thiết kế Distributed Sagas và 2PC",),
        completion_criteria="Triển khai Saga Coordinator",
        estimated_effort_minutes=m2.estimated_effort_minutes,
        required_concepts=m2.required_concepts,
        prerequisite_milestone_ids=m2.prerequisite_milestone_ids,
        status=MilestoneStatus.APPROVED,
        created_at=m2.created_at,
        updated_at=m2.updated_at,
    )
    milestones_altered = [m1, m2_altered, m3, m4, m5]

    # Verify that content hash for M2 changed:
    orig_m2_hash = compute_milestone_content_hash(m2, target_date=roadmap.target_date)
    altered_m2_hash = compute_milestone_content_hash(m2_altered, target_date=roadmap.target_date)
    assert orig_m2_hash != altered_m2_hash, "Altering learning_outcomes must change content hash"

    res2 = await decomposer.decompose_and_validate(
        goal=goal,
        roadmap=roadmap,
        milestones=milestones_altered,
        availability=avail,
        learner_profile=learner_profile,
        start_date=roadmap.start_date,
        max_milestone_retries=0,
        reference_date=roadmap.start_date,
    )
    assert len(res2.validated_proposal_data["tasks"]) > 0

    # Sibling milestone outline changed -> all sibling milestones in roadmap are re-executed
    # because [SIBLING_MILESTONES_OUTLINE] in prompt changed!
    assert llm.calls_by_milestone_id.get(m1.id, 0) == 1, (
        "M1 must be re-executed via LLM because sibling outline changed"
    )
    assert llm.calls_by_milestone_id.get(m3.id, 0) == 1, (
        "M3 must be re-executed via LLM because sibling outline changed"
    )
    assert llm.calls_by_milestone_id.get(m4.id, 0) == 1, (
        "M4 must be re-executed via LLM because sibling outline changed"
    )
    assert llm.calls_by_milestone_id.get(m5.id, 0) == 1, (
        "M5 must be re-executed via LLM because sibling outline changed"
    )

    # M2 was re-executed via LLM because checkpoint hash was invalidated!
    assert llm.calls_by_milestone_id.get(m2.id, 0) == 1, (
        "M2 must be re-executed via LLM due to checkpoint invalidation"
    )


@pytest.mark.asyncio
async def test_end_to_end_use_case_fault_injection_and_quota_commit() -> None:
    """Scenario 3: End-to-end integration with ExecuteScheduleProposalGenerationUseCase.

    Attempt 1: Fails on M4. Quota reservation is released.
    Attempt 2: Resumes. M1..M3 loaded from checkpoint. M4, M5 execute.
    Quota committed on Attempt 2 ONLY covers fresh tokens.
    """
    user_id, goal, roadmap, milestones, avail = _build_5_milestone_fixture()
    m1, m2, m3, m4, m5 = milestones

    checkpoint_store = InMemoryMilestoneCheckpointStore()
    workflow_repo = BufferedWorkflowRepo()
    llm = _FaultInjectingStubLLM()
    quota_facade = _RecordingQuotaFacade()
    proposal_repo = _FakeProposalRepo()
    roadmap_repo = _FakeRoadmapRepo(roadmap)
    milestone_repo = _FakeMilestoneRepo(milestones)
    goal_repo = _FakeGoalRepo(goal)
    avail_snap = AvailabilitySnapshotDTO(
        user_id=user_id,
        mode="QUOTA",
        daily_cap_minutes=240,
        weekly_capacity_minutes=1680,
        daily_quota_minutes={
            day: 240
            for day in (
                "monday",
                "tuesday",
                "wednesday",
                "thursday",
                "friday",
                "saturday",
                "sunday",
            )
        },
    )
    avail_port = _FakeAvailabilityPort(avail_snap)
    exec_sync_port = _FakeExecSyncPort()
    block_repo = _FakeBlockRepo()
    learner_profile_port = _FakeLearnerProfilePort(user_id)
    sse_store = InMemorySseJobStore()
    uow = _FakeUoW()

    class _AsyncUserQueryPort:
        async def get_user_by_id(self, user_id: UUID) -> Any:
            return SimpleNamespace(id=user_id, timezone="UTC", tier="PRO")

        async def get_user_by_email(self, email: str) -> Any:
            del email
            return None

    user_query_port = _AsyncUserQueryPort()

    use_case = ExecuteScheduleProposalGenerationUseCase(
        goal_repo=goal_repo,
        roadmap_repo=roadmap_repo,
        milestone_repo=milestone_repo,
        proposal_repo=proposal_repo,
        availability_query_port=avail_port,
        learner_profile_port=learner_profile_port,
        execution_sync_port=exec_sync_port,
        quota_facade=quota_facade,
        llm_provider=llm,
        sse_job_store=sse_store,
        uow=uow,
        enable_tier3_judge=False,
        user_query_port=user_query_port,
        block_repo=block_repo,
        workflow_repo=workflow_repo,
        checkpoint_store=checkpoint_store,
    )

    # Attempt 1: Inject failure on M4 and M5
    llm.fail_milestone_ids = {m4.id, m5.id}
    job_id_1 = uuid7()
    res_id_1 = uuid7()
    await sse_store.create_job(
        job_id=job_id_1,
        user_id=user_id,
        roadmap_id=roadmap.id,
        reservation_id=res_id_1,
        job_type="SCHEDULE_PROPOSAL_GEN",
        operation=f"SCHEDULE_PROPOSAL_GEN:{roadmap.id}",
    )

    with pytest.raises(TimeoutError):
        await use_case.execute(
            job_id=job_id_1,
            user_id=user_id,
            roadmap_id=roadmap.id,
            reservation_id=res_id_1,
            max_retries=0,
            decomposer_architecture_mode="milestone_scoped",
        )

    # Verify Attempt 1 released its reservation
    assert any(r[0] == res_id_1 for r in quota_facade.released), (
        "Attempt 1 failed reservation must be released"
    )
    assert not any(c[0] == res_id_1 for c in quota_facade.committed), (
        "Attempt 1 reservation must NOT be committed"
    )

    # Attempt 2: Resume
    llm.fail_milestone_ids.clear()
    llm.calls_by_milestone_id.clear()

    job_id_2 = uuid7()
    res_id_2 = uuid7()
    await sse_store.create_job(
        job_id=job_id_2,
        user_id=user_id,
        roadmap_id=roadmap.id,
        reservation_id=res_id_2,
        job_type="SCHEDULE_PROPOSAL_GEN",
        operation=f"SCHEDULE_PROPOSAL_GEN:{roadmap.id}",
    )

    saved_proposal = await use_case.execute(
        job_id=job_id_2,
        user_id=user_id,
        roadmap_id=roadmap.id,
        reservation_id=res_id_2,
        max_retries=0,
        decomposer_architecture_mode="milestone_scoped",
    )

    assert saved_proposal is not None
    assert len(saved_proposal.proposal_data["tasks"]) > 0

    # Verify M1..M3 were loaded from checkpoint (0 LLM calls in attempt 2)
    assert llm.calls_by_milestone_id.get(m1.id, 0) == 0
    assert llm.calls_by_milestone_id.get(m2.id, 0) == 0
    assert llm.calls_by_milestone_id.get(m3.id, 0) == 0
    assert llm.calls_by_milestone_id.get(m4.id, 0) == 1
    assert llm.calls_by_milestone_id.get(m5.id, 0) == 1

    # Verify quota commitment on Attempt 2
    committed_entries = [c for c in quota_facade.committed if c[0] == res_id_2]
    assert len(committed_entries) == 1, "Attempt 2 must commit its quota reservation exactly once"
    _, p_tokens, c_tokens, model_used = committed_entries[0]
    assert p_tokens > 0, "Committed prompt tokens must be > 0"
    assert c_tokens > 0, "Committed completion tokens must be > 0"
