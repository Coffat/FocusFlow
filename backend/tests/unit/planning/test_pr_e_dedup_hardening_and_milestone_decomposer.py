from __future__ import annotations

import asyncio
import json
from collections.abc import Sequence
from datetime import UTC, date, datetime
from types import SimpleNamespace
from typing import Any
from uuid import UUID

import pytest
from uuid6 import uuid7

from src.account.public_api import (
    AvailabilitySnapshotDTO,
    LearnerMemoryItemSnapshotDTO,
    LearnerProfileDTO,
)
from src.execution.public_api import ExistingScheduledTaskDTO, ScheduleSyncResultDTO
from src.planning.application.services.milestone_scoped_decomposer import (
    MilestoneDecompositionOutcome,
    reconcile_milestone_proposals,
)
from src.planning.application.services.roadmap_context_builder import RoadmapContextBuilder
from src.planning.application.use_cases.clarification_use_cases import (
    GenerateClarificationQuestionsUseCase,
)
from src.planning.application.use_cases.milestone_use_cases import (
    ExecuteMilestoneGenerationUseCase,
)
from src.planning.application.use_cases.proposal_generation_use_cases import (
    ExecuteScheduleProposalGenerationUseCase,
)
from src.planning.application.use_cases.proposal_management_use_cases import (
    ApplyScheduleProposalUseCase,
)
from src.planning.domain.models.goal import Goal, GoalStatus
from src.planning.domain.models.knowledge_concept import (
    ConceptPrerequisiteGraph,
    LearningConcept,
    LearningResource,
    compute_deterministic_resource_id,
)
from src.planning.domain.models.milestone import Milestone, MilestoneStatus
from src.planning.domain.models.roadmap import Roadmap, RoadmapStatus
from src.planning.domain.models.schedule import (
    OfficialSchedule,
    ScheduleProposal,
    ScheduleProposalStatus,
)
from src.planning.domain.models.schedule_block import ScheduleBlock
from src.planning.presentation.routers import build_sse_event_generator
from src.shared_kernel.application.llm_port import (
    LLMGenerationResult,
    LLMToolDeclarationDTO,
    LLMToolExecutor,
)
from src.shared_kernel.config import Settings
from src.shared_kernel.infrastructure.external_ai.litellm_adapter import (
    _GENAI_CLIENT_CACHE,
    _OUTBOUND_SEMAPHORES,
    LiteLLMAdapter,
    clear_google_genai_client_cache,
)
from src.shared_kernel.infrastructure.sse.job_store import InMemorySseJobStore
from tests.helpers.llm_stubs import StubLLMAdapter


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
        self.committed: list[tuple[UUID, int, int, str]] = []
        self.released: list[tuple[UUID, str]] = []
        self.reserved: list[UUID] = []

    async def reserve_quota(
        self,
        user_id: UUID,
        operation_type: str = "ROADMAP_GENERATION",
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
        *,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        model_name: str = "",
    ) -> None:
        self.committed.append((reservation_id, prompt_tokens, completion_tokens, model_name))

    async def release_reservation(self, reservation_id: UUID, *, reason: str = "") -> None:
        self.released.append((reservation_id, reason))


class _FakeGoalRepo:
    def __init__(self, goal: Goal) -> None:
        self.goal = goal

    async def get_by_id(self, gid: UUID) -> Goal | None:
        return self.goal if gid == self.goal.id else None

    async def get_by_id_for_user(self, goal_id: UUID, user_id: UUID) -> Goal | None:
        return self.goal if goal_id == self.goal.id and user_id == self.goal.user_id else None

    async def save(self, goal: Goal) -> Goal:
        self.goal = goal
        return goal


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
        self.milestones = list(milestones)

    async def list_by_roadmap_id(self, rid: UUID) -> list[Milestone]:
        del rid
        return list(self.milestones)

    async def save_many(self, rid: UUID, milestones: Sequence[Milestone]) -> list[Milestone]:
        del rid
        self.milestones = list(milestones)
        return list(self.milestones)


class _FakeProposalRepo:
    def __init__(self) -> None:
        self.proposals: dict[UUID, ScheduleProposal] = {}

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
    def __init__(self) -> None:
        self.synced_tasks: list[Any] = []

    async def get_tasks_for_roadmaps(
        self, *args: Any, **kwargs: Any
    ) -> list[ExistingScheduledTaskDTO]:
        del args, kwargs
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


class _FakeAvailabilityPort:
    def __init__(self, snap: AvailabilitySnapshotDTO) -> None:
        self.snap = snap

    async def get_active_availability(self, uid: UUID) -> AvailabilitySnapshotDTO | None:
        del uid
        return self.snap


class _FakeLearnerProfilePort:
    def __init__(self, user_id: UUID) -> None:
        self.profile = LearnerProfileDTO(
            user_id=user_id,
            opt_session_minutes=60,
            estimation_bias_beta=1.0,
            peak_productivity_slots=("EVENING",),
        )

    async def get_learner_profile(self, uid: UUID) -> LearnerProfileDTO:
        del uid
        return self.profile


class _FakeLearnerMemoryPort:
    def __init__(self, user_id: UUID) -> None:
        self._items = [
            LearnerMemoryItemSnapshotDTO(
                id=uuid7(),
                user_id=user_id,
                category="PREFERENCE",
                memory_key="study_style",
                memory_value={"prefers": "hands-on"},
                confidence=0.9,
                source_workflow="PLAN_CREATION",
            )
        ]

    async def list_active_memory_items(
        self, user_id: UUID, *, limit: int = 10
    ) -> list[LearnerMemoryItemSnapshotDTO]:
        del user_id, limit
        return list(self._items)

    async def list_concept_masteries(self, user_id: UUID) -> list[Any]:
        del user_id
        return []


class _FakeChangeLogPort:
    def __init__(self) -> None:
        self.logs: list[dict[str, Any]] = []

    async def record_change_log(self, **kwargs: Any) -> None:
        self.logs.append(kwargs)


class _FakeUserQueryPort:
    def __init__(self, user_id: UUID, timezone: str = "UTC", tier: str = "FREE") -> None:
        self._snapshot = SimpleNamespace(id=user_id, timezone=timezone, tier=tier)

    async def get_user_by_id(self, user_id: UUID) -> Any:
        return self._snapshot if user_id == self._snapshot.id else None


class _FakeKnowledgeBasePort:
    def __init__(self, resources: Sequence[LearningResource]) -> None:
        self.resources = list(resources)
        self.resource_calls: list[dict[str, Any]] = []

    async def search_concepts(
        self,
        query: str,
        *,
        domain: str | None = None,
        learner_level: str | None = None,
        limit: int = 10,
    ) -> list[LearningConcept]:
        del query, domain, learner_level, limit
        return []

    async def get_prerequisite_graph(
        self,
        concept_ids: Sequence[str],
        *,
        max_depth: int = 3,
    ) -> ConceptPrerequisiteGraph:
        del concept_ids, max_depth
        return ConceptPrerequisiteGraph(nodes=(), edges=(), unresolved_ids=())

    async def get_learning_resources_and_guidance(
        self,
        *,
        query: str | None = None,
        domain: str | None = None,
        concept_ids: Sequence[str] = (),
        task_type: str | None = None,
        limit: int = 10,
    ) -> list[LearningResource]:
        self.resource_calls.append(
            {
                "query": query,
                "domain": domain,
                "concept_ids": list(concept_ids),
                "task_type": task_type,
                "limit": limit,
            }
        )
        return list(self.resources[:limit])


class _PromptCapturingStubLLM(StubLLMAdapter):
    def __init__(self, canned_responses: list[dict[str, Any]] | None = None) -> None:
        super().__init__(canned_responses=canned_responses)
        self.recorded_calls: list[dict[str, Any]] = []

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
        self.recorded_calls.append(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "tools": tools,
                "max_tool_calls": max_tool_calls,
                "thinking_level": thinking_level,
            }
        )
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


def _make_planning_fixture(
    *,
    with_prerequisites: bool = False,
) -> tuple[UUID, Goal, Roadmap, list[Milestone], AvailabilitySnapshotDTO]:
    now = datetime(2026, 11, 1, 9, 0, tzinfo=UTC)
    user_id = uuid7()
    goal_id = uuid7()
    roadmap_id = uuid7()
    goal = Goal(
        id=goal_id,
        user_id=user_id,
        title="Làm chủ Python & FastAPI Backend",
        raw_description="Xây dựng API chuẩn sản xuất với FastAPI, SQLAlchemy async và pytest.",
        prior_knowledge_level="BEGINNER",
        target_date=date(2026, 12, 10),
        clarification_context=json.dumps(
            {
                "status": "ANSWERED",
                "information_gaps": [
                    {
                        "dimension": "TIMELINE",
                        "status": "UNKNOWN",
                        "roadmap_decision": "Xác định mật độ giờ học mỗi tuần",
                    }
                ],
            }
        ),
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
        target_date=date(2026, 12, 10),
        status=RoadmapStatus.INITIALIZED,
        created_at=now,
        updated_at=now,
    )

    m1_id, m2_id, m3_id = uuid7(), uuid7(), uuid7()
    m1 = Milestone(
        id=m1_id,
        roadmap_id=roadmap_id,
        sequence_order=1,
        title="Nền tảng Python & Typing",
        description="Cú pháp Python 3.12 và kiểu dữ liệu",
        learning_outcomes=("Viết hàm Python có type hint",),
        completion_criteria="Hoàn thành bài tập Python cơ bản",
        estimated_effort_minutes=60,
        required_concepts=("py-syntax-variables",),
        status=MilestoneStatus.APPROVED,
        created_at=now,
        updated_at=now,
    )
    m2 = Milestone(
        id=m2_id,
        roadmap_id=roadmap_id,
        sequence_order=2,
        title="Xây dựng API với FastAPI",
        description="Routing, Pydantic v2 và validation",
        learning_outcomes=("Thiết kế endpoint FastAPI với Pydantic",),
        completion_criteria="Pass unit test cho router",
        estimated_effort_minutes=60,
        required_concepts=("fastapi-routing-pydantic",),
        prerequisite_milestone_ids=(m1_id,) if with_prerequisites else (),
        status=MilestoneStatus.APPROVED,
        created_at=now,
        updated_at=now,
    )
    m3 = Milestone(
        id=m3_id,
        roadmap_id=roadmap_id,
        sequence_order=3,
        title="Kiểm thử & Hoàn thiện hệ thống",
        description="Viết pytest async và tích hợp",
        learning_outcomes=("Viết bộ test pytest async",),
        completion_criteria="Đạt 100% test pass",
        estimated_effort_minutes=60,
        required_concepts=("py-control-flow-functions",),
        prerequisite_milestone_ids=(m2_id,) if with_prerequisites else (),
        status=MilestoneStatus.APPROVED,
        created_at=now,
        updated_at=now,
    )
    avail = AvailabilitySnapshotDTO(
        user_id=user_id,
        mode="MODE_B",
        daily_cap_minutes=120,
        weekly_capacity_minutes=420,
        availability_slots=(
            {
                "day_of_week": "monday",
                "start_time": "19:00",
                "end_time": "21:00",
                "is_active": True,
            },
            {
                "day_of_week": "tuesday",
                "start_time": "19:00",
                "end_time": "21:00",
                "is_active": True,
            },
            {
                "day_of_week": "wednesday",
                "start_time": "19:00",
                "end_time": "21:00",
                "is_active": True,
            },
            {
                "day_of_week": "thursday",
                "start_time": "19:00",
                "end_time": "21:00",
                "is_active": True,
            },
            {
                "day_of_week": "friday",
                "start_time": "19:00",
                "end_time": "21:00",
                "is_active": True,
            },
        ),
    )
    return user_id, goal, roadmap, [m1, m2, m3], avail


def test_production_default_decomposer_architecture_mode_is_milestone_scoped() -> None:
    cfg = Settings(_env_file=None)
    assert cfg.decomposer_architecture_mode == "milestone_scoped"
    assert cfg.ai_max_concurrent_llm_requests == 4
    assert cfg.ai_decomposer_max_concurrency == 2


@pytest.mark.asyncio
async def test_context_deduplication_across_builder_and_planning_use_cases() -> None:
    user_id, goal, roadmap, milestones, avail = _make_planning_fixture(with_prerequisites=True)
    mem_port = _FakeLearnerMemoryPort(user_id)

    base_ctx = RoadmapContextBuilder.build_task_decomposition_context(
        goal=goal,
        roadmap=roadmap,
        milestones=milestones,
        availability=avail,
        learner_profile=_FakeLearnerProfilePort(user_id).profile,
    )
    assert "prerequisite_milestone_ids" in base_ctx
    assert str(milestones[0].id) in base_ctx

    legacy_assembled = RoadmapContextBuilder.assemble_harness_context(
        workflow_stage="TASK_DECOMPOSITION",
        base_context_text=base_ctx,
        memory_items=await mem_port.list_active_memory_items(user_id),
        include_planning_context=True,
    )
    dedup_assembled = RoadmapContextBuilder.assemble_harness_context(
        workflow_stage="TASK_DECOMPOSITION",
        base_context_text=base_ctx,
        memory_items=await mem_port.list_active_memory_items(user_id),
        include_planning_context=False,
    )
    assert "planning_context" in legacy_assembled.text
    assert "planning_context" not in dedup_assembled.text
    assert len(dedup_assembled.text) < len(legacy_assembled.text)
    reduction_ratio = 1.0 - (len(dedup_assembled.text) / len(legacy_assembled.text))
    assert reduction_ratio > 0.50

    # 1) Proposal generation use case deduplicates structured_ctx + header_markers
    llm_prop = _PromptCapturingStubLLM()
    sse_prop = InMemorySseJobStore()
    job_prop = uuid7()
    res_prop = uuid7()
    await sse_prop.create_job(
        job_id=job_prop,
        user_id=user_id,
        roadmap_id=roadmap.id,
        reservation_id=res_prop,
        job_type="SCHEDULE_PROPOSAL_GEN",
        operation=f"SCHEDULE_PROPOSAL_GEN:{roadmap.id}",
    )
    prop_uc = ExecuteScheduleProposalGenerationUseCase(
        goal_repo=_FakeGoalRepo(goal),
        roadmap_repo=_FakeRoadmapRepo(roadmap),
        milestone_repo=_FakeMilestoneRepo(milestones),
        proposal_repo=_FakeProposalRepo(),
        availability_query_port=_FakeAvailabilityPort(avail),
        learner_profile_port=_FakeLearnerProfilePort(user_id),
        execution_sync_port=_FakeExecSyncPort(),
        quota_facade=_RecordingQuotaFacade(),
        llm_provider=llm_prop,
        sse_job_store=sse_prop,
        uow=_FakeUoW(),
        enable_tier3_judge=False,
        learner_memory_port=mem_port,
    )
    await prop_uc.execute(
        job_id=job_prop,
        user_id=user_id,
        roadmap_id=roadmap.id,
        reservation_id=res_prop,
        decomposer_architecture_mode="monolithic",
    )
    decomp_prompt = llm_prop.recorded_calls[0]["user_prompt"]
    assert "MILESTONE_IDS:" not in decomp_prompt
    assert "AVAILABILITY_SLOTS:" not in decomp_prompt
    assert "planning_context" not in decomp_prompt
    assert decomp_prompt.count("[USER_PROVIDED_FACTS]") == 1

    # 2) Milestone generation use case deduplicates context_block
    llm_ms = _PromptCapturingStubLLM()
    sse_ms = InMemorySseJobStore()
    job_ms = uuid7()
    res_ms = uuid7()
    await sse_ms.create_job(
        job_id=job_ms,
        user_id=user_id,
        roadmap_id=roadmap.id,
        reservation_id=res_ms,
        job_type="MILESTONE_GEN",
        operation=f"MILESTONE_GEN:{roadmap.id}",
    )
    ms_uc = ExecuteMilestoneGenerationUseCase(
        goal_repo=_FakeGoalRepo(goal),
        roadmap_repo=_FakeRoadmapRepo(roadmap),
        milestone_repo=_FakeMilestoneRepo([]),
        quota_facade=_RecordingQuotaFacade(),
        llm_provider=llm_ms,
        sse_job_store=sse_ms,
        uow=_FakeUoW(),
        learner_memory_port=mem_port,
        availability_query_port=_FakeAvailabilityPort(avail),
        execution_sync_port=_FakeExecSyncPort(),
        proposal_repo=_FakeProposalRepo(),
    )
    await ms_uc.execute(
        job_id=job_ms,
        user_id=user_id,
        roadmap_id=roadmap.id,
        reservation_id=res_ms,
        generation_strategy="FULL_SCOPE",
    )
    ms_prompt = llm_ms.recorded_calls[0]["user_prompt"]
    assert "planning_context" not in ms_prompt
    assert ms_prompt.count("[USER_PROVIDED_FACTS]") == 1

    # 3) Clarification questions use case avoids duplicating information_gaps & context_block
    llm_clar = _PromptCapturingStubLLM()
    clar_uc = GenerateClarificationQuestionsUseCase(
        goal_repo=_FakeGoalRepo(goal),
        quota_facade=_RecordingQuotaFacade(),
        llm_provider=llm_clar,
        uow=_FakeUoW(),
        learner_memory_port=mem_port,
        availability_query_port=_FakeAvailabilityPort(avail),
    )
    await clar_uc.execute(goal_id=goal.id, user_id=user_id)
    clar_prompt = llm_clar.recorded_calls[0]["user_prompt"]
    assert "planning_context" not in clar_prompt
    assert clar_prompt.count("[INFORMATION_GAPS_TO_CLARIFY]") == 1
    assert '"information_gaps":' not in clar_prompt
    assert "\ninformation_gaps:\n" not in clar_prompt


@pytest.mark.asyncio
async def test_litellm_adapter_reuses_genai_client_and_enforces_outbound_semaphore(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from google import genai

    clear_google_genai_client_cache()
    created_clients: list[str] = []
    active_calls = 0
    max_observed_concurrency = 0

    class FakeModels:
        async def generate_content(
            self,
            *,
            model: str,
            contents: Any,
            config: Any,
        ) -> Any:
            del model, contents, config
            nonlocal active_calls, max_observed_concurrency
            active_calls += 1
            max_observed_concurrency = max(max_observed_concurrency, active_calls)
            await asyncio.sleep(0.03)
            active_calls -= 1
            return SimpleNamespace(
                usage_metadata=SimpleNamespace(prompt_token_count=5, candidates_token_count=5),
                text='{"ok": true}',
            )

    class FakeClient:
        def __init__(self, **kwargs: Any) -> None:
            created_clients.append(str(kwargs.get("api_key", "")))
            self.aio = SimpleNamespace(models=FakeModels())

    monkeypatch.setattr(genai, "Client", FakeClient)

    secret_key = "super-secret-api-key-should-not-leak"
    adapter = LiteLLMAdapter()
    adapter._settings = SimpleNamespace(  # type: ignore[assignment]
        llm_provider="gemini",
        llm_thinking_control="model_suffix",
        llm_model="gemini-3.8-flash",
        llm_model_low="gemini-3.8-flash",
        llm_model_medium="gemini-3.8-flash",
        llm_model_high="gemini-3.8-flash",
        llm_fallback_models="",
        llm_api_key=secret_key,
        llm_base_url="http://127.0.0.1:8045",
        llm_thinking_level="LOW",
        ai_max_concurrent_llm_requests=2,
        ai_hard_timeout_seconds=10.0,
    )

    await asyncio.gather(
        *(
            adapter.generate_structured(
                system_prompt="sys",
                user_prompt=f"usr-{i}",
                response_schema={"type": "object", "properties": {"ok": {"type": "boolean"}}},
                thinking_level="LOW",
            )
            for i in range(5)
        )
    )

    # Shared client created only once for the 5 concurrent calls
    assert len(created_clients) == 1
    # Outbound semaphore capped concurrent calls at 2
    assert max_observed_concurrency == 2
    # Cache key must hash the API key, never storing raw secret in cache keys
    assert all(
        secret_key not in key_part for cache_k in _GENAI_CLIENT_CACHE for key_part in cache_k
    )
    assert asyncio.get_running_loop() in _OUTBOUND_SEMAPHORES

    # Distinct API key creates a second cached client
    adapter._settings.llm_api_key = "different-secret-key"
    await adapter.generate_structured(
        system_prompt="sys",
        user_prompt="usr-other",
        response_schema={"type": "object", "properties": {"ok": {"type": "boolean"}}},
        thinking_level="LOW",
    )
    assert len(created_clients) == 2


@pytest.mark.asyncio
async def test_sse_streaming_emits_keepalive_without_corrupting_completed_event() -> None:
    store = InMemorySseJobStore()
    user_id = uuid7()
    roadmap_id = uuid7()
    job_id = uuid7()
    await store.create_job(
        job_id=job_id,
        user_id=user_id,
        roadmap_id=roadmap_id,
        reservation_id=uuid7(),
        job_type="SCHEDULE_PROPOSAL_GEN",
        operation=f"SCHEDULE_PROPOSAL_GEN:{roadmap_id}",
    )

    async def _produce() -> None:
        await store.append_event(
            job_id=job_id,
            event="stage",
            status="STREAMING",
            data={"stage": "STREAMING", "progress": 30},
        )
        await asyncio.sleep(0.08)
        await store.append_event(
            job_id=job_id,
            event="completed",
            status="COMPLETED",
            data={"stage": "COMPLETED", "progress": 100, "payload": {"ok": True}},
        )

    producer = asyncio.create_task(_produce())
    frames: list[str] = []
    async for chunk in build_sse_event_generator(
        store,
        job_id=job_id,
        user_id=user_id,
        keepalive_interval_seconds=0.025,
    ):
        frames.append(chunk)
    await producer

    assert any(frame == ": keepalive\n\n" for frame in frames)
    event_frames = [f for f in frames if f != ": keepalive\n\n"]
    assert len(event_frames) == 2
    assert event_frames[0].startswith("id: 1\nevent: stage\ndata: ")
    assert event_frames[1].startswith("id: 2\nevent: completed\ndata: ")
    completed_payload = json.loads(event_frames[1].split("data: ", 1)[1])
    assert completed_payload["payload"] == {"ok": True}


def test_reconcile_milestone_proposals_dag_strictly_respects_prerequisite_milestone_ids() -> None:
    now = datetime(2026, 11, 1, 9, 0, tzinfo=UTC)
    rid = uuid7()
    m1 = Milestone(
        id=uuid7(),
        roadmap_id=rid,
        sequence_order=1,
        title="M1",
        learning_outcomes=("O1",),
        estimated_effort_minutes=60,
        status=MilestoneStatus.APPROVED,
        created_at=now,
        updated_at=now,
    )
    m2 = Milestone(
        id=uuid7(),
        roadmap_id=rid,
        sequence_order=2,
        title="M2",
        learning_outcomes=("O2",),
        estimated_effort_minutes=60,
        prerequisite_milestone_ids=(),
        status=MilestoneStatus.APPROVED,
        created_at=now,
        updated_at=now,
    )
    m3 = Milestone(
        id=uuid7(),
        roadmap_id=rid,
        sequence_order=3,
        title="M3",
        learning_outcomes=("O3",),
        estimated_effort_minutes=60,
        prerequisite_milestone_ids=(m1.id,),  # Only depends on M1, NOT M2
        status=MilestoneStatus.APPROVED,
        created_at=now,
        updated_at=now,
    )

    outcomes_no_cross = {
        m1.id: MilestoneDecompositionOutcome(
            milestone=m1,
            tasks=(
                {
                    "task_id": "T1",
                    "title": "M1 Theory",
                    "task_type": "THEORY",
                    "estimated_minutes": 45,
                },
                {
                    "task_id": "T2",
                    "title": "M1 Project",
                    "task_type": "PROJECT",
                    "estimated_minutes": 60,
                },
            ),
            dependencies=({"predecessor_id": "T1", "successor_id": "T2", "is_mandatory": True},),
            prompt_tokens=10,
            completion_tokens=10,
            thinking_tokens=0,
            attempts_used=1,
        ),
        m2.id: MilestoneDecompositionOutcome(
            milestone=m2,
            tasks=(
                {
                    "task_id": "T1",
                    "title": "M2 Theory",
                    "task_type": "THEORY",
                    "estimated_minutes": 45,
                },
            ),
            dependencies=(),
            prompt_tokens=10,
            completion_tokens=10,
            thinking_tokens=0,
            attempts_used=1,
        ),
        m3.id: MilestoneDecompositionOutcome(
            milestone=m3,
            tasks=(
                {
                    "task_id": "T1",
                    "title": "M3 Theory",
                    "task_type": "THEORY",
                    "estimated_minutes": 45,
                },
                {
                    "task_id": "T2",
                    "title": "M3 Review",
                    "task_type": "REVIEW",
                    "estimated_minutes": 45,
                },
            ),
            dependencies=({"predecessor_id": "T1", "successor_id": "T2", "is_mandatory": True},),
            prompt_tokens=10,
            completion_tokens=10,
            thinking_tokens=0,
            attempts_used=1,
        ),
    }

    # Case 1: With M3.prerequisite_milestone_ids == (M1.id,) and M2.prerequisite_milestone_ids == ()
    reconciled = reconcile_milestone_proposals([m1, m2, m3], outcomes_no_cross)
    assert [t["task_id"] for t in reconciled.tasks] == ["T1", "T2", "T3", "T4", "T5"]
    edges = {(d["predecessor_id"], d["successor_id"]) for d in reconciled.dependencies}
    # Internal M1 (T1->T2), internal M3 (T4->T5), and explicit M1->M3 (T2->T4); NO M1->M2 or M2->M3!
    assert edges == {("T1", "T2"), ("T4", "T5"), ("T2", "T4")}

    # Case 2: All prerequisite_milestone_ids empty -> ZERO cross-milestone edges even with sequence_order 1,2,3
    m3_unlinked = Milestone(
        id=m3.id,
        roadmap_id=rid,
        sequence_order=3,
        title="M3",
        learning_outcomes=("O3",),
        estimated_effort_minutes=60,
        prerequisite_milestone_ids=(),
        status=MilestoneStatus.APPROVED,
        created_at=now,
        updated_at=now,
    )
    reconciled_unlinked = reconcile_milestone_proposals([m1, m2, m3_unlinked], outcomes_no_cross)
    unlinked_edges = {
        (d["predecessor_id"], d["successor_id"]) for d in reconciled_unlinked.dependencies
    }
    assert unlinked_edges == {("T1", "T2"), ("T4", "T5")}


@pytest.mark.asyncio
async def test_milestone_scoped_decomposer_prefetch_isolated_retry_and_apply_roundtrip() -> None:
    user_id, goal, roadmap, milestones, avail = _make_planning_fixture(with_prerequisites=True)
    res_m1 = LearningResource(
        resource_id=compute_deterministic_resource_id(
            url="https://docs.python.org/3/", title="Python Official Docs"
        ),
        title="Python Official Docs",
        url="https://docs.python.org/3/",
        type="DOCS",
        description="Official Python documentation",
    )
    kb = _FakeKnowledgeBasePort([res_m1])

    class _MilestoneSelectiveRetryLLM(_PromptCapturingStubLLM):
        def __init__(self) -> None:
            super().__init__()
            self.m2_calls = 0
            self.decomposer_calls = 0

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
            if (
                "[INDEPENDENT_CRITIC:" not in system_prompt
                and "[INDEPENDENT_CRITIC:" not in user_prompt
            ):
                if "GENERATE_PROPOSAL_TASKS" in user_prompt:
                    self.decomposer_calls += 1
                    assert tools is None
                    assert tool_executor is None
                    if f"MILESTONE_IDS: [{milestones[1].id}]" in user_prompt:
                        self.m2_calls += 1
                        if self.m2_calls == 1:
                            # Fail local Tier 1 check on M2 attempt 1 (15m < 30m)
                            self.recorded_calls.append(
                                {
                                    "system_prompt": system_prompt,
                                    "user_prompt": user_prompt,
                                    "tools": tools,
                                    "max_tool_calls": max_tool_calls,
                                }
                            )
                            return LLMGenerationResult(
                                payload={
                                    "tasks": [
                                        {
                                            "task_id": "T1",
                                            "milestone_id": str(milestones[1].id),
                                            "title": "Quá ngắn M2",
                                            "description": "Task cố tình vi phạm biên thời lượng",
                                            "task_type": "THEORY",
                                            "learning_objective": "Học nhanh FastAPI",
                                            "completion_criteria": "Xong bài tập",
                                            "concept_ids": ["fastapi-routing-pydantic"],
                                            "covered_outcome_ids": ["M2-O1"],
                                            "resource_ids": [res_m1.resource_id, "res-fake-999"],
                                            "estimated_minutes": 15,
                                        }
                                    ],
                                    "dependencies": [],
                                },
                                prompt_tokens=100,
                                output_tokens=50,
                                thinking_tokens=0,
                                model_id="stub-deterministic",
                            )
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

    llm = _MilestoneSelectiveRetryLLM()
    quota_facade = _RecordingQuotaFacade()
    proposal_repo = _FakeProposalRepo()
    roadmap_repo = _FakeRoadmapRepo(roadmap)
    milestone_repo = _FakeMilestoneRepo(milestones)
    goal_repo = _FakeGoalRepo(goal)
    avail_port = _FakeAvailabilityPort(avail)
    exec_sync_port = _FakeExecSyncPort()
    sse_store = InMemorySseJobStore()
    uow = _FakeUoW()

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

    user_query_port = _FakeUserQueryPort(user_id, timezone="UTC")
    gen_uc = ExecuteScheduleProposalGenerationUseCase(
        goal_repo=goal_repo,
        roadmap_repo=roadmap_repo,
        milestone_repo=milestone_repo,
        proposal_repo=proposal_repo,
        availability_query_port=avail_port,
        learner_profile_port=_FakeLearnerProfilePort(user_id),
        execution_sync_port=exec_sync_port,
        quota_facade=quota_facade,
        llm_provider=llm,
        sse_job_store=sse_store,
        uow=uow,
        enable_tier3_judge=False,
        knowledge_base=kb,
        user_query_port=user_query_port,
    )
    saved_proposal = await gen_uc.execute(
        job_id=job_id,
        user_id=user_id,
        roadmap_id=roadmap.id,
        reservation_id=reservation_id,
        decomposer_architecture_mode="milestone_scoped",
    )

    job = await sse_store.get_job_for_user(job_id=job_id, user_id=user_id)
    milestone_progress_events = [
        event
        for event in job.events
        if isinstance(event.data.get("milestone_sequence"), int)
    ]
    assert len(milestone_progress_events) == 3
    assert {event.data["milestone_sequence"] for event in milestone_progress_events} == {1, 2, 3}
    assert [event.data["completed_count"] for event in milestone_progress_events] == [1, 2, 3]
    assert all(event.data["total_count"] == 3 for event in milestone_progress_events)
    assert all(event.data["from_checkpoint"] is False for event in milestone_progress_events)

    # Prefetched on server (3 milestones), zero LLM tool calls, and ONLY M2 retried (3 + 1 = 4 calls)
    assert len(kb.resource_calls) == 3
    assert llm.m2_calls == 2
    assert llm.decomposer_calls == 4
    # Quota committed exactly ONCE
    assert len(quota_facade.committed) == 1
    assert quota_facade.committed[0][0] == reservation_id
    assert quota_facade.released == []

    assert saved_proposal.status == ScheduleProposalStatus.DRAFT
    tasks = saved_proposal.proposal_data["tasks"]
    assert len(tasks) == 3
    # Every task has unique UUID and resolved verified resource (hallucinated IDs excluded)
    assert len({t["task_id"] for t in tasks}) == 3
    for task in tasks:
        assert [r["resource_id"] for r in task["learning_resources"]] == [res_m1.resource_id]

    # Cross-milestone prerequisite edges M1->M2 and M2->M3 preserved after UUID normalization
    deps = saved_proposal.proposal_data["dependencies"]
    task_id_by_mid = {t["milestone_id"]: t["task_id"] for t in tasks}
    edge_pairs = {(d["predecessor_id"], d["successor_id"]) for d in deps}
    assert (
        task_id_by_mid[str(milestones[0].id)],
        task_id_by_mid[str(milestones[1].id)],
    ) in edge_pairs
    assert (
        task_id_by_mid[str(milestones[1].id)],
        task_id_by_mid[str(milestones[2].id)],
    ) in edge_pairs

    # Roundtrip through ApplyScheduleProposalUseCase
    apply_uc = ApplyScheduleProposalUseCase(
        roadmap_repo=roadmap_repo,
        milestone_repo=milestone_repo,
        proposal_repo=proposal_repo,
        schedule_repo=_FakeScheduleRepo(),
        block_repo=_FakeBlockRepo(),
        availability_query_port=avail_port,
        execution_sync_port=exec_sync_port,
        schedule_change_log_port=_FakeChangeLogPort(),
        uow=uow,
        user_query_port=user_query_port,
        goal_repo=goal_repo,
    )
    apply_result = await apply_uc.execute(
        user_id=user_id,
        roadmap_id=roadmap.id,
        proposal_id=saved_proposal.id,
    )
    assert apply_result.inserted_tasks_count == 3
    assert apply_result.proposal.status == ScheduleProposalStatus.APPLIED


def test_reconcile_milestone_proposals_prioritizes_project_review_sinks_and_theory_sources() -> (
    None
):
    now = datetime(2026, 11, 1, 9, 0, tzinfo=UTC)
    rid = uuid7()
    m1 = Milestone(
        id=uuid7(),
        roadmap_id=rid,
        sequence_order=1,
        title="M1",
        learning_outcomes=("O1",),
        estimated_effort_minutes=60,
        status=MilestoneStatus.APPROVED,
        created_at=now,
        updated_at=now,
    )
    m2 = Milestone(
        id=uuid7(),
        roadmap_id=rid,
        sequence_order=2,
        title="M2",
        learning_outcomes=("O2",),
        estimated_effort_minutes=60,
        prerequisite_milestone_ids=(m1.id,),
        status=MilestoneStatus.APPROVED,
        created_at=now,
        updated_at=now,
    )
    outcomes = {
        m1.id: MilestoneDecompositionOutcome(
            milestone=m1,
            tasks=(
                {
                    "task_id": "T1",
                    "title": "M1 Review",
                    "task_type": "REVIEW",
                    "estimated_minutes": 30,
                },
                {
                    "task_id": "T2",
                    "title": "M1 Project",
                    "task_type": "PROJECT",
                    "estimated_minutes": 60,
                },
            ),
            dependencies=(),
            prompt_tokens=10,
            completion_tokens=10,
            thinking_tokens=0,
            attempts_used=1,
        ),
        m2.id: MilestoneDecompositionOutcome(
            milestone=m2,
            tasks=(
                {
                    "task_id": "T1",
                    "title": "M2 Practice",
                    "task_type": "PRACTICE",
                    "estimated_minutes": 45,
                },
                {
                    "task_id": "T2",
                    "title": "M2 Theory",
                    "task_type": "THEORY",
                    "estimated_minutes": 45,
                },
            ),
            dependencies=(),
            prompt_tokens=10,
            completion_tokens=10,
            thinking_tokens=0,
            attempts_used=1,
        ),
    }
    reconciled = reconcile_milestone_proposals([m1, m2], outcomes)
    # M1 PROJECT sink is T2; M2 THEORY source is T4
    assert reconciled.dependencies == [
        {"predecessor_id": "T2", "successor_id": "T4", "is_mandatory": True}
    ]
