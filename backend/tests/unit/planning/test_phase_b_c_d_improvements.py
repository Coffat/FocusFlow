from datetime import UTC, date, datetime
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import pytest

from src.account.public_api import (
    AvailabilitySnapshotDTO,
    CalendarBusyIntervalDTO,
    CalendarConnectionSnapshotDTO,
)
from src.evaluation.application.dtos.intelligence import (
    GenerateWeeklyReviewRequestDTO,
    SubmitProofRequestDTO,
)
from src.evaluation.application.use_cases.intelligence import (
    GenerateMilestoneProofUseCase,
    GenerateWeeklyReviewUseCase,
    SubmitMilestoneProofUseCase,
)
from src.evaluation.domain.models.intelligence import MilestoneProof, WeeklyReview
from src.execution.public_api import ScheduleSyncResultDTO
from src.planning.application.services.effective_availability_service import (
    GetEffectiveAvailabilityUseCase,
    subtract_intervals_and_filter_fragments,
)
from src.planning.application.services.validation_gate import (
    ProposalValidationGateOrchestrator,
)
from src.planning.application.use_cases.proposal_management_use_cases import (
    ApplyScheduleProposalUseCase,
)
from src.planning.domain.exceptions.planning_exceptions import (
    FreshCalendarConflictDetectedError,
    JudgeReviewConfirmationRequiredError,
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
from src.shared_kernel.config import Settings
from src.shared_kernel.domain.base import uuid7
from src.shared_kernel.infrastructure.external_ai.embedding_adapter import (
    LiteLLMEmbeddingAdapter,
)
from src.shared_kernel.infrastructure.external_ai.litellm_adapter import LiteLLMAdapter
from tests.helpers.llm_stubs import StubLLMAdapter

# =============================================================================
# Phase C Tests: Proxy HttpOptions, 3-Tier Routing, & Embedding 768-d Fallback
# =============================================================================


@pytest.mark.asyncio
async def test_phase_c_google_genai_proxy_and_three_tier_routing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import os

    from google import genai

    orig_exists = os.path.exists
    monkeypatch.delenv("RUNNING_IN_DOCKER", raising=False)
    monkeypatch.setattr(
        os.path,
        "exists",
        lambda path: False if path == "/.dockerenv" else orig_exists(path),
    )

    client_init_kwargs: list[dict[str, Any]] = []
    called_models: list[str] = []

    class FakeModels:
        async def generate_content(
            self,
            *,
            model: str,
            contents: Any,
            config: Any,
        ) -> Any:
            del contents, config
            called_models.append(model)
            return SimpleNamespace(
                usage_metadata=SimpleNamespace(prompt_token_count=12, candidates_token_count=18),
                text='{"ok": true}',
            )

    class FakeClient:
        def __init__(self, **kwargs: Any) -> None:
            client_init_kwargs.append(kwargs)
            self.aio = SimpleNamespace(models=FakeModels())

    monkeypatch.setattr(genai, "Client", FakeClient)

    adapter = LiteLLMAdapter()
    adapter._settings = Settings(
        llm_provider="gemini",
        llm_api_key="proxy-test-key",
        llm_base_url="http://127.0.0.1:8045",
        llm_model="gemini-3.8-flash",
        llm_model_low="gemini-3.8-flash",
        llm_model_medium="gemini-3.8-flash",
        llm_model_high="gemini-3.8-flash",
    )

    assert adapter._should_use_google_genai_sdk() is True

    for level, expected_model in (
        ("LOW", "gemini-3.8-flash"),
        ("MEDIUM", "gemini-3.8-flash"),
        ("HIGH", "gemini-3.8-flash"),
    ):
        res, _, _ = await adapter.generate_structured(
            system_prompt="sys",
            user_prompt="usr",
            response_schema={"type": "object", "properties": {"ok": {"type": "boolean"}}},
            thinking_level=level,
        )
        assert res["ok"] is True
        assert adapter.last_model_used == expected_model
        assert adapter.last_degraded_model_used is False

    assert called_models == [
        "gemini-3.8-flash",
        "gemini-3.8-flash",
        "gemini-3.8-flash",
    ]
    assert len(client_init_kwargs) == 1
    http_opts = client_init_kwargs[0].get("http_options")
    assert http_opts is not None
    assert getattr(http_opts, "base_url", None) == "http://127.0.0.1:8045"

    # Inside Docker (RUNNING_IN_DOCKER=1 or /.dockerenv present), 127.0.0.1 is rewritten to host.docker.internal
    monkeypatch.setenv("RUNNING_IN_DOCKER", "1")
    assert adapter._resolve_base_url() == "http://host.docker.internal:8045"

    monkeypatch.delenv("RUNNING_IN_DOCKER", raising=False)
    monkeypatch.setattr(
        os.path,
        "exists",
        lambda path: True if path == "/.dockerenv" else orig_exists(path),
    )
    assert adapter._resolve_base_url() == "http://host.docker.internal:8045"


@pytest.mark.asyncio
async def test_phase_c_high_tier_does_not_downgrade_to_lite_until_flash_exhausted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from google import genai

    called_models: list[str] = []

    class FakeModels:
        async def generate_content(
            self,
            *,
            model: str,
            contents: Any,
            config: Any,
        ) -> Any:
            del contents, config
            called_models.append(model)
            if model != "gemini-3.8-flash":
                raise RuntimeError("503 UNAVAILABLE")
            return SimpleNamespace(
                usage_metadata=SimpleNamespace(prompt_token_count=10, candidates_token_count=10),
                text='{"ok": true}',
            )

    class FakeClient:
        def __init__(self, **kwargs: Any) -> None:
            del kwargs
            self.aio = SimpleNamespace(models=FakeModels())

    monkeypatch.setattr(genai, "Client", FakeClient)

    adapter = LiteLLMAdapter()
    adapter._settings = Settings(
        llm_provider="gemini",
        llm_api_key="real-key",
        llm_base_url="http://127.0.0.1:8045",
        llm_model="gemini-3.8-flash",
        llm_model_low="gemini-3.8-flash",
        llm_model_medium="gemini-3.8-flash",
        llm_model_high="custom-high-tier",
        llm_fallback_models="",
    )

    # Without explicit llm_fallback_models, failing tier model does NOT silently fall back to llm_model
    with pytest.raises(RuntimeError, match="503 UNAVAILABLE"):
        await adapter.generate_structured(
            system_prompt="sys",
            user_prompt="usr",
            response_schema={"type": "object", "properties": {"ok": {"type": "boolean"}}},
            thinking_level="HIGH",
        )
    assert called_models == ["custom-high-tier"]

    # With explicit llm_fallback_models, falls back strictly along configured list
    called_models.clear()
    adapter._settings.llm_fallback_models = "gemini-3.8-flash"
    res, _, _ = await adapter.generate_structured(
        system_prompt="sys",
        user_prompt="usr",
        response_schema={"type": "object", "properties": {"ok": {"type": "boolean"}}},
        thinking_level="HIGH",
    )
    assert res["ok"] is True
    assert adapter.last_model_used == "gemini-3.8-flash"
    assert adapter.last_degraded_model_used is False
    assert called_models == ["custom-high-tier", "gemini-3.8-flash"]


@pytest.mark.asyncio
async def test_phase_c_embedding_adapter_never_uses_deprecated_004(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import litellm

    attempted_calls: list[tuple[str, str | None, int | None]] = []

    async def fake_aembedding(**kwargs: Any) -> Any:
        model = str(kwargs.get("model", ""))
        api_base = kwargs.get("api_base")
        dimensions = kwargs.get("dimensions")
        attempted_calls.append((model, api_base, dimensions))
        return SimpleNamespace(data=[{"embedding": [0.25] * 768}])

    monkeypatch.setattr(litellm, "aembedding", fake_aembedding)

    emb = LiteLLMEmbeddingAdapter()
    emb._settings = Settings(
        llm_provider="gemini",
        llm_api_key="cobhub-proxy-key",
        llm_base_url="http://127.0.0.1:8045",
        embedding_provider="google_ai_studio",
        embedding_api_key="real-studio-key",
        embedding_base_url="",
        embedding_model="gemini/gemini-embedding-2",
        embedding_dimensions=768,
    )
    vectors = await emb.embed(["Kiến trúc Hexagonal"])
    assert len(vectors) == 1
    assert len(vectors[0]) == 768
    assert attempted_calls == [("gemini/gemini-embedding-2", None, 768)]

    # Fail closed when embedding_provider is invalid/mock
    emb._settings = Settings(
        embedding_provider="mock",
        embedding_api_key="real-studio-key",
        embedding_base_url="",
    )
    with pytest.raises(RuntimeError, match="AI_EMBEDDING_PROVIDER_NOT_CONFIGURED"):
        await emb.embed(["Kiến trúc Hexagonal"])

    # Fail closed when embedding API key is missing or mock
    emb._settings = Settings(
        embedding_provider="google_ai_studio",
        embedding_api_key="",
        embedding_base_url="",
    )
    with pytest.raises(RuntimeError, match="AI_EMBEDDING_PROVIDER_NOT_CONFIGURED"):
        await emb.embed(["Kiến trúc Hexagonal"])

    # Fail closed when configured embedding model fails (no fallback to legacy embedding models)
    failed_models: list[str] = []

    async def failing_aembedding(**kwargs: Any) -> Any:
        failed_models.append(str(kwargs.get("model", "")))
        raise RuntimeError("Upstream 503")

    monkeypatch.setattr(litellm, "aembedding", failing_aembedding)
    emb._settings = Settings(
        embedding_provider="google_ai_studio",
        embedding_api_key="real-studio-key",
        embedding_base_url="",
        embedding_model="gemini/gemini-embedding-2",
    )
    with pytest.raises(RuntimeError, match="AI_EMBEDDING_FAILED"):
        await emb.embed(["Kiến trúc Hexagonal"])
    assert failed_models == ["gemini/gemini-embedding-2"]


# =============================================================================
# Phase C.2 Tests: AC-07 Partial Schedule & Tier 3 Judge Status
# =============================================================================


@pytest.mark.asyncio
async def test_phase_c2_partial_schedule_triggers_one_condense_retry_then_returns_partial() -> None:
    milestone_id = uuid7()
    attempt_1 = {
        "tasks": [
            {
                "task_id": "t1",
                "milestone_id": str(milestone_id),
                "title": "Bài 1",
                "estimated_minutes": 90,
            },
            {
                "task_id": "t2",
                "milestone_id": str(milestone_id),
                "title": "Bài 2",
                "estimated_minutes": 60,
            },
        ],
        "dependencies": [],
    }
    # 150 minutes requested vs 120 minutes available (125% <= 130%) -> triggers 1 retry!
    # Attempt 2 still returns 150 minutes -> returns valid partial schedule draft (AC-07)
    llm = StubLLMAdapter(canned_responses=[attempt_1, attempt_1])
    gate = ProposalValidationGateOrchestrator(llm_provider=llm, enable_tier3_judge=False)

    res = await gate.generate_and_validate_proposal_with_retry(
        system_prompt="sys",
        user_prompt="usr",
        response_schema=None,
        availability=AvailabilityConfigurationDTO(mode="MODE_A", default_daily_quota_minutes=120),
        valid_milestone_ids={milestone_id},
        start_date=date(2026, 11, 16),
        current_roadmap_target_date=date(2026, 11, 16),
        deterministic_allocation=True,
        max_retries=2,
    )
    assert res.attempts_used == 2
    assert res.is_valid is True
    assert res.is_partial_schedule is True
    assert res.scheduled_tasks_count == 1
    assert res.unscheduled_tasks_count == 1
    assert len(res.unscheduled_tasks) == 1
    assert "DEADLINE_CAPACITY_EXCEEDED" in str(res.unscheduled_tasks[0].get("unscheduled_reason"))


@pytest.mark.asyncio
async def test_phase_c2_tier3_judge_fail_triggers_retry_and_marks_needs_review_or_review_pending() -> (
    None
):
    milestone_id = uuid7()
    valid_task_payload = {
        "tasks": [
            {
                "task_id": str(uuid7()),
                "milestone_id": str(milestone_id),
                "title": "Nền tảng FastAPI",
                "estimated_minutes": 60,
                "scheduled_date": "2026-11-16",
                "scheduled_start": "2026-11-16T19:00:00+00:00",
                "scheduled_end": "2026-11-16T20:00:00+00:00",
            }
        ],
        "dependencies": [],
    }
    judge_fail_payload = {
        "overall_status": "FAIL",
        "score": 0.45,
        "issues": [
            {
                "category": "THEORY_PRACTICE_BALANCE",
                "severity": "ERROR",
                "message": "Thiếu bài tập thực hành cho cột mốc.",
            }
        ],
        "warnings": ["Thiếu bài tập thực hành cho cột mốc."],
    }

    # Attempt 1: task decomposer -> judge FAIL (triggers pedagogical retry)
    # Attempt 2: task decomposer -> judge FAIL (exhausted -> judge_status = NEEDS_REVIEW)
    llm = StubLLMAdapter(
        canned_responses=[
            valid_task_payload,
            judge_fail_payload,
            valid_task_payload,
            judge_fail_payload,
        ]
    )
    gate = ProposalValidationGateOrchestrator(llm_provider=llm, enable_tier3_judge=True)
    res = await gate.generate_and_validate_proposal_with_retry(
        system_prompt="sys",
        user_prompt="usr",
        response_schema=None,
        availability=AvailabilityConfigurationDTO(mode="MODE_A", default_daily_quota_minutes=120),
        valid_milestone_ids={milestone_id},
        start_date=date(2026, 11, 16),
        current_roadmap_target_date=date(2026, 11, 20),
        deterministic_allocation=False,
        max_retries=2,
    )
    assert res.attempts_used == 2
    assert res.judge_status == "NEEDS_REVIEW"
    assert len(res.advisory_warnings) >= 1
    assert any("Thiếu bài tập thực hành" in w for w in res.advisory_warnings)

    # Judge timeout -> retries once and returns REVIEW_PENDING (never PASSED)
    class TimeoutJudgeLLM(StubLLMAdapter):
        async def generate_structured(
            self, *args: Any, **kwargs: Any
        ) -> tuple[dict[str, Any], int, int]:
            del args, kwargs
            raise TimeoutError("Judge timed out")

    timeout_gate = ProposalValidationGateOrchestrator(
        llm_provider=TimeoutJudgeLLM(),
        enable_tier3_judge=True,
        tier3_timeout_seconds=0.05,
    )
    skipped, score, advisories, j_status = await timeout_gate.run_tier3_pedagogical_judge(
        valid_task_payload,
        goal_title="FastAPI",
    )
    assert skipped is True
    assert score is None
    assert j_status == "REVIEW_PENDING"
    assert any("REVIEW_PENDING" in w for w in advisories)


# =============================================================================
# Phase B.1 Tests: GetEffectiveAvailabilityUseCase (Manual vs Google Calendar)
# =============================================================================


def test_subtract_intervals_and_filter_fragments_eliminates_short_fragments() -> None:
    # Base window 07:00 (420) to 10:00 (600)
    # Busy 07:00-07:40 (420..460), 08:00-09:40 (480..580)
    # Remaining: 07:40-08:00 (20m < 30m) and 09:40-10:00 (20m < 30m) -> both discarded!
    remaining = subtract_intervals_and_filter_fragments(
        base_intervals=[(420, 600)],
        busy_intervals=[(420, 460), (480, 580)],
        min_session_minutes=30,
    )
    assert remaining == []

    # Busy 07:00-08:00 (420..480) -> Remaining 08:00-10:00 (480..600 = 120m >= 30m)
    remaining_valid = subtract_intervals_and_filter_fragments(
        base_intervals=[(420, 600)],
        busy_intervals=[(420, 480)],
        min_session_minutes=30,
    )
    assert remaining_valid == [(480, 600)]


@pytest.mark.asyncio
async def test_phase_b1_get_effective_availability_google_calendar_and_fallback() -> None:
    user_id = uuid4()

    class FakeAvailPort:
        def __init__(self, snapshot: AvailabilitySnapshotDTO | None) -> None:
            self._snapshot = snapshot

        async def get_active_availability(self, uid: UUID) -> AvailabilitySnapshotDTO | None:
            del uid
            return self._snapshot

    class FakeCalendarPort:
        def __init__(self, fail: bool = False) -> None:
            self.fail = fail

        async def get_connection_snapshot(
            self, user_id: UUID, provider: str = "GOOGLE"
        ) -> CalendarConnectionSnapshotDTO | None:
            del provider
            return CalendarConnectionSnapshotDTO(
                user_id=user_id,
                provider="GOOGLE",
                sync_status="ACTIVE",
                external_calendar_id="primary",
                source_calendars=("primary",),
                last_synced_at="2026-11-16T00:00:00+00:00",
                is_active=True,
            )

        async def get_free_busy_intervals(
            self,
            user_id: UUID,
            time_min: datetime,
            time_max: datetime,
            provider: str = "GOOGLE",
        ) -> list[CalendarBusyIntervalDTO]:
            del user_id, time_min, time_max, provider
            if self.fail:
                raise RuntimeError("OAuth token expired")
            return [
                CalendarBusyIntervalDTO(
                    start_time=datetime(2026, 11, 16, 7, 0, tzinfo=UTC),
                    end_time=datetime(2026, 11, 16, 19, 0, tzinfo=UTC),
                )
            ]

    avail_snap = AvailabilitySnapshotDTO(
        user_id=user_id,
        mode="MODE_A",
        daily_cap_minutes=120,
        weekly_capacity_minutes=840,
        calendar_integration_mode="CONNECTED",
        allowed_window_start="07:00",
        allowed_window_end="23:00",
        min_session_minutes=30,
    )

    # Case 2: Connected Google Calendar -> converts to MODE_B slots subtracting busy 07:00..19:00 -> leaves 19:00..23:00
    uc = GetEffectiveAvailabilityUseCase(
        availability_query_port=FakeAvailPort(avail_snap),  # type: ignore[arg-type]
        calendar_connection_query_port=FakeCalendarPort(fail=False),  # type: ignore[arg-type]
    )
    eff = await uc.execute(
        user_id=user_id,
        start_date=date(2026, 11, 16),
        target_date=date(2026, 11, 16),
        timezone="UTC",
    )
    assert eff.availability_config.mode == "MODE_B"
    assert eff.source_metadata["source_type"] == "GOOGLE_CALENDAR"
    monday_slots = [
        s for s in eff.availability_config.availability_slots if s.day_of_week == "monday"
    ]
    assert len(monday_slots) == 1
    assert monday_slots[0].start_time == "19:00"
    assert monday_slots[0].end_time == "23:00"

    # Case 2 Fallback: Google Calendar FreeBusy raises -> safe fallback with FAILED_OR_EXPIRED
    uc_fail = GetEffectiveAvailabilityUseCase(
        availability_query_port=FakeAvailPort(avail_snap),  # type: ignore[arg-type]
        calendar_connection_query_port=FakeCalendarPort(fail=True),  # type: ignore[arg-type]
    )
    eff_fail = await uc_fail.execute(
        user_id=user_id,
        start_date=date(2026, 11, 16),
        target_date=date(2026, 11, 16),
        timezone="UTC",
    )
    assert eff_fail.source_metadata["google_sync_status"] == "FAILED_OR_EXPIRED"
    assert len(eff_fail.warnings) >= 1


# =============================================================================
# Phase B.4 Tests: ApplyScheduleProposal Fresh Conflict, Idempotency & Sync
# =============================================================================


@pytest.mark.asyncio
async def test_phase_b4_apply_schedule_fresh_conflict_idempotency_and_honest_sync() -> None:
    now = datetime(2026, 11, 16, 8, 0, tzinfo=UTC)
    user_id = uuid7()
    roadmap_id = uuid7()
    milestone_id = uuid7()
    proposal_id = uuid7()
    task_1_id = uuid7()
    unscheduled_task_id = uuid7()

    roadmap = Roadmap(
        id=roadmap_id,
        user_id=user_id,
        goal_id=uuid7(),
        title="Học FastAPI",
        start_date=date(2026, 11, 16),
        target_date=date(2026, 11, 20),
        status=RoadmapStatus.INITIALIZED,
        created_at=now,
        updated_at=now,
    )
    milestone = Milestone(
        id=milestone_id,
        roadmap_id=roadmap_id,
        sequence_order=1,
        title="Milestone 1",
        status=MilestoneStatus.APPROVED,
        created_at=now,
        updated_at=now,
    )
    proposal = ScheduleProposal(
        id=proposal_id,
        roadmap_id=roadmap_id,
        user_id=user_id,
        proposal_data={
            "judge_status": "NEEDS_REVIEW",
            "advisory_warnings": ["Cảnh báo sư phạm cần xác nhận."],
            "is_partial_schedule": True,
            "tasks": [
                {
                    "task_id": str(task_1_id),
                    "milestone_id": str(milestone_id),
                    "title": "Bài 1 đã xếp lịch",
                    "learning_objective": "Hoàn thành nội dung học đã xếp lịch.",
                    "completion_criteria": "Nộp bài thực hành đạt yêu cầu.",
                    "estimated_minutes": 60,
                    "scheduled_date": "2026-11-16",
                    "scheduled_start": "2026-11-16T19:00:00+00:00",
                    "scheduled_end": "2026-11-16T20:00:00+00:00",
                },
                {
                    "task_id": str(unscheduled_task_id),
                    "milestone_id": str(milestone_id),
                    "title": "Bài 2 trong Backlog",
                    "learning_objective": "Hoàn thành nội dung học trong Backlog.",
                    "completion_criteria": "Nộp bài thực hành đạt yêu cầu.",
                    "estimated_minutes": 60,
                    "scheduled_date": None,
                    "scheduled_start": None,
                    "scheduled_end": None,
                    "unscheduled_reason": "DEADLINE_CAPACITY_EXCEEDED: Không đủ thời gian rảnh",
                },
            ],
            "dependencies": [],
        },
        status=ScheduleProposalStatus.DRAFT,
        created_at=now,
        updated_at=now,
    )

    class SimpleRoadmapRepo:
        def __init__(self) -> None:
            self.roadmap = roadmap

        async def get_by_id(self, rid: UUID) -> Roadmap | None:
            return self.roadmap if rid == roadmap_id else None

        async def get_by_id_for_user(self, rid: UUID, uid: UUID) -> Roadmap | None:
            return self.roadmap if rid == roadmap_id and uid == user_id else None

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

    class SimpleMilestoneRepo:
        async def list_by_roadmap_id(self, rid: UUID) -> list[Milestone]:
            del rid
            return [milestone]

    class SimpleProposalRepo:
        def __init__(self) -> None:
            self.proposal = proposal

        async def get_by_id(self, pid: UUID) -> ScheduleProposal | None:
            return self.proposal if pid == proposal_id else None

        async def get_by_id_for_user(self, pid: UUID, uid: UUID) -> ScheduleProposal | None:
            return self.proposal if pid == proposal_id and uid == user_id else None

        async def save(self, p: ScheduleProposal) -> ScheduleProposal:
            self.proposal = p
            return p

        async def discard_other_drafts(
            self, roadmap_id: UUID, keep_proposal_id: UUID, now: datetime
        ) -> int:
            del roadmap_id, keep_proposal_id, now
            return 0

    class SimpleScheduleRepo:
        def __init__(self) -> None:
            self.sched: OfficialSchedule | None = None

        async def get_by_roadmap_id(self, rid: UUID) -> OfficialSchedule | None:
            del rid
            return self.sched

        async def save(self, s: OfficialSchedule) -> OfficialSchedule:
            self.sched = s
            return s

    class SimpleBlockRepo:
        def __init__(self) -> None:
            self.blocks: list[ScheduleBlock] = []

        async def get_by_schedule_id(self, sid: UUID) -> list[ScheduleBlock]:
            del sid
            return list(self.blocks)

        async def list_by_roadmap_ids(self, rids: list[UUID]) -> list[ScheduleBlock]:
            del rids
            return []

        async def delete_unprotected_by_schedule_id(self, sid: UUID) -> int:
            del sid
            return 0

        async def save_all(self, blocks: list[ScheduleBlock]) -> list[ScheduleBlock]:
            self.blocks = list(blocks)
            return self.blocks

    class SimpleExecSyncPort:
        async def get_tasks_for_roadmaps(self, *args: Any, **kwargs: Any) -> list[Any]:
            del args, kwargs
            return []

        async def get_active_roadmaps_tasks(self, *args: Any, **kwargs: Any) -> list[Any]:
            del args, kwargs
            return []

        async def sync_official_schedule_tasks(self, **kwargs: Any) -> ScheduleSyncResultDTO:
            tasks = kwargs["proposed_tasks"]
            return ScheduleSyncResultDTO(
                roadmap_id=roadmap_id,
                official_schedule_id=kwargs["official_schedule_id"],
                preserved_completed_tasks_count=0,
                replaced_tasks_count=0,
                inserted_tasks_count=len(tasks),
                affected_tasks_count=len(tasks),
                total_shifted_minutes=60,
                total_active_sessions=1,
                total_planned_minutes=60,
            )

    class SimpleChangeLogPort:
        async def record_change_log(self, **kwargs: Any) -> None:
            del kwargs

    class SimpleUoW:
        async def __aenter__(self) -> "SimpleUoW":
            return self

        async def __aexit__(self, *args: Any) -> None:
            del args

        async def commit(self) -> None:
            pass

        async def rollback(self) -> None:
            pass

        def collect_events_from(self, *args: Any) -> None:
            del args

    class MutableCalendarPort:
        def __init__(self, busy_list: list[CalendarBusyIntervalDTO]) -> None:
            self.busy_list = busy_list

        async def get_connection_snapshot(
            self, user_id: UUID, provider: str = "GOOGLE"
        ) -> CalendarConnectionSnapshotDTO | None:
            del provider
            return CalendarConnectionSnapshotDTO(
                user_id=user_id,
                provider="GOOGLE",
                sync_status="ACTIVE",
                external_calendar_id="primary",
                source_calendars=("primary",),
                is_active=True,
            )

        async def get_free_busy_intervals(
            self, *args: Any, **kwargs: Any
        ) -> list[CalendarBusyIntervalDTO]:
            del args, kwargs
            return list(self.busy_list)

    class FakeSyncFacade:
        def __init__(self) -> None:
            self.calls = 0

        async def sync_schedule_blocks_to_google(self, schedule_id: UUID, user_id: UUID) -> str:
            del schedule_id, user_id
            self.calls += 1
            return "SYNCED"

    avail_snap = AvailabilitySnapshotDTO(
        user_id=user_id,
        mode="MODE_A",
        daily_cap_minutes=120,
        weekly_capacity_minutes=840,
        calendar_integration_mode="CONNECTED",
        allowed_window_start="07:00",
        allowed_window_end="23:00",
        min_session_minutes=30,
    )

    class SimpleAvailPort:
        async def get_active_availability(self, uid: UUID) -> AvailabilitySnapshotDTO | None:
            del uid
            return avail_snap

    # 1. Judge review confirmation gate: without confirm_warnings -> JudgeReviewConfirmationRequiredError
    cal_port = MutableCalendarPort(
        busy_list=[
            CalendarBusyIntervalDTO(
                start_time=datetime(2026, 11, 16, 19, 30, tzinfo=UTC),
                end_time=datetime(2026, 11, 16, 20, 30, tzinfo=UTC),
            )
        ]
    )
    sync_facade = FakeSyncFacade()
    block_repo = SimpleBlockRepo()
    uc = ApplyScheduleProposalUseCase(
        roadmap_repo=SimpleRoadmapRepo(),  # type: ignore[arg-type]
        milestone_repo=SimpleMilestoneRepo(),  # type: ignore[arg-type]
        proposal_repo=SimpleProposalRepo(),  # type: ignore[arg-type]
        schedule_repo=SimpleScheduleRepo(),  # type: ignore[arg-type]
        block_repo=block_repo,  # type: ignore[arg-type]
        availability_query_port=SimpleAvailPort(),  # type: ignore[arg-type]
        execution_sync_port=SimpleExecSyncPort(),  # type: ignore[arg-type]
        schedule_change_log_port=SimpleChangeLogPort(),  # type: ignore[arg-type]
        uow=SimpleUoW(),  # type: ignore[arg-type]
        calendar_connection_query_port=cal_port,  # type: ignore[arg-type]
        calendar_sync_facade=sync_facade,  # type: ignore[arg-type]
    )

    # 1. AC-09: Detects fresh Google Calendar conflict at 19:30-20:30 before commit
    with pytest.raises(FreshCalendarConflictDetectedError) as conflict_exc:
        await uc.execute(
            user_id=user_id,
            roadmap_id=roadmap_id,
            proposal_id=proposal_id,
            confirm_warnings=True,
            confirm_partial_schedule=True,
            now=now,
        )
    assert conflict_exc.value.code == "FRESH_CALENDAR_CONFLICT_DETECTED"
    assert len(conflict_exc.value.conflicts) == 1

    # 2. Clear conflict -> Judge review confirmation gate: without confirm_warnings -> JudgeReviewConfirmationRequiredError
    cal_port.busy_list = []
    with pytest.raises(JudgeReviewConfirmationRequiredError):
        await uc.execute(
            user_id=user_id,
            roadmap_id=roadmap_id,
            proposal_id=proposal_id,
            confirm_warnings=False,
            confirm_partial_schedule=True,
            now=now,
        )

    # 3. With confirm_warnings=True -> Apply succeeds, syncs to Google Calendar, and preserves Backlog task
    res1 = await uc.execute(
        user_id=user_id,
        roadmap_id=roadmap_id,
        proposal_id=proposal_id,
        confirm_warnings=True,
        confirm_partial_schedule=True,
        now=now,
    )
    assert res1.calendar_sync_status == "SYNCED"
    assert res1.backlog_unscheduled_tasks_count == 1
    assert len(block_repo.blocks) == 1
    assert sync_facade.calls == 1

    # 4. AC-10 Idempotency: calling execute again on APPLIED proposal returns idempotently
    res2 = await uc.execute(
        user_id=user_id,
        roadmap_id=roadmap_id,
        proposal_id=proposal_id,
        confirm_warnings=True,
        confirm_partial_schedule=True,
        now=now,
    )
    assert res2.official_schedule.id == res1.official_schedule.id
    assert res2.calendar_sync_status == "SYNCED"
    assert len(block_repo.blocks) == 1
    assert sync_facade.calls == 1


# =============================================================================
# Phase D Tests: Prove Mode (UC-20) & Weekly Review (UC-21) with LLM & Validator
# =============================================================================


@pytest.mark.asyncio
async def test_phase_d_prove_mode_and_weekly_review_llm_and_faithfulness_guard() -> None:
    user_id = uuid4()
    roadmap_id = uuid4()
    milestone_id = uuid4()

    class FakeEvalRepo:
        def __init__(self) -> None:
            self.proofs: dict[UUID, MilestoneProof] = {}
            self.reviews: dict[UUID, WeeklyReview] = {}
            self.saved_model_used: str = ""

        async def create_proof(
            self, *, milestone_id: UUID, user_id: UUID, questions: list[dict[str, Any]]
        ) -> MilestoneProof:
            proof = MilestoneProof(
                milestone_id=milestone_id,
                user_id=user_id,
                status="READY",
                questions=questions,
            )
            self.proofs[proof.id] = proof
            return proof

        async def get_owned_proof(self, proof_id: UUID, uid: UUID) -> MilestoneProof | None:
            p = self.proofs.get(proof_id)
            return p if p and p.user_id == uid else None

        async def save_proof(self, proof: MilestoneProof) -> None:
            self.proofs[proof.id] = proof

        async def create_weekly_review(
            self,
            *,
            roadmap_id: UUID,
            user_id: UUID,
            period_start: date,
            period_end: date,
            reflection: dict[str, Any],
        ) -> WeeklyReview:
            rev = WeeklyReview(
                roadmap_id=roadmap_id,
                user_id=user_id,
                period_start=period_start,
                period_end=period_end,
                quantitative_summary={"period_days": 7, "completed_sessions": 5},
                strengths_feedback="Hoàn thành 5 phiên học trong 7 ngày.",
                bottlenecks_feedback="Cần duy trì nhịp độ ổn định.",
                action_recommendations="Tiếp tục thực hành trong 7 ngày tới.",
                user_reflection_payload=reflection,
            )
            self.reviews[rev.id] = rev
            return rev

        async def save_weekly_review(
            self, review: WeeklyReview, *, model_used: str = "mock-deterministic"
        ) -> None:
            self.reviews[review.id] = review
            self.saved_model_used = model_used

        async def latest_weekly_review(self, uid: UUID) -> WeeklyReview | None:
            del uid
            return None

    class FakeOwnership:
        async def get_milestone(self, mid: UUID) -> Any:
            return SimpleNamespace(id=mid, user_id=user_id, title="Hexagonal Architecture")

        async def roadmap_belongs_to(self, rid: UUID, uid: UUID) -> bool:
            return rid == roadmap_id and uid == user_id

    class FakeUoW:
        async def commit(self) -> None:
            pass

        async def rollback(self) -> None:
            pass

        def collect_events_from(self, *args: Any) -> None:
            del args

        async def __aenter__(self) -> "FakeUoW":
            return self

        async def __aexit__(self, *args: Any) -> None:
            del args

    repo = FakeEvalRepo()
    ownership = FakeOwnership()
    uow = FakeUoW()

    llm = StubLLMAdapter(
        canned_responses=[
            {
                "questions": [
                    {"id": "q1", "prompt": "Tại sao Domain không được phụ thuộc Infrastructure?"},
                    {"id": "q2", "prompt": "Phân biệt Port và Adapter bằng ví dụ thực tế."},
                    {"id": "q3", "prompt": "Cách kiểm thử Use Case độc lập với Database?"},
                ]
            },
            {
                "conceptual_understanding_score": 35,
                "example_grounding_score": 27,
                "practical_application_score": 26,
                "answer_evidence": [
                    {
                        "question_id": "q1",
                        "evidence": "Giải thích đúng nguyên lý tách biệt Domain khỏi Infrastructure.",
                        "is_addressed": True,
                    }
                ],
                "corrective_action": None,
            },
            {
                # Strengths cites faithful numbers (5, 7); bottlenecks hallucinates 999 -> sanitized!
                "strengths_feedback": "Bạn đã hoàn thành tốt 5 phiên học trong chu kỳ 7 ngày.",
                "bottlenecks_feedback": "Bạn đã bỏ lỡ 999 giờ học trong tuần qua.",
                "action_recommendations": "Duy trì 5 phiên học chất lượng cao cho tuần tiếp theo.",
            },
        ]
    )
    llm.last_model_used = "gemini-3.8-flash"

    gen_proof_uc = GenerateMilestoneProofUseCase(
        repository=repo,
        ownership=ownership,  # type: ignore[arg-type]
        uow=uow,  # type: ignore[arg-type]
        llm_provider=llm,
    )
    proof_dto = await gen_proof_uc.execute(user_id=user_id, milestone_id=milestone_id)
    assert len(proof_dto.questions) == 3
    assert "Domain" in proof_dto.questions[0]["prompt"]

    sub_proof_uc = SubmitMilestoneProofUseCase(
        repository=repo,
        uow=uow,  # type: ignore[arg-type]
        llm_provider=llm,
    )
    graded_dto = await sub_proof_uc.execute(
        user_id=user_id,
        milestone_id=milestone_id,
        proof_id=proof_dto.proof_id,
        request=SubmitProofRequestDTO(
            answers=[{"id": "q1", "answer": "Để bảo toàn tính thuần khiết của nghiệp vụ."}],
            confidence=0.8,
        ),
    )
    assert graded_dto.score == 88
    assert graded_dto.status == "PASSED"

    class FakeExecMetrics:
        async def get_roadmap_period_metrics(self, **kwargs: Any) -> Any:
            del kwargs
            from src.execution.public_api import WeeklyExecutionMetricsDTO

            return WeeklyExecutionMetricsDTO(
                completed_minutes=250,
                planned_minutes=300,
                completed_sessions_count=5,
                completed_tasks_count=4,
                planned_tasks_count=5,
                overdue_tasks_count=0,
                adherence_rate_pct=80.0,
            )

    weekly_uc = GenerateWeeklyReviewUseCase(
        repository=repo,
        ownership=ownership,  # type: ignore[arg-type]
        uow=uow,  # type: ignore[arg-type]
        execution_metrics_port=FakeExecMetrics(),
        llm_provider=llm,
    )
    review_dto = await weekly_uc.execute(
        user_id=user_id,
        request=GenerateWeeklyReviewRequestDTO(
            roadmap_id=roadmap_id,
            period_start=date(2026, 11, 10),
            period_end=date(2026, 11, 16),
            reflection={"note": "Tuần này học hiệu quả."},
        ),
    )
    assert "5 phiên học" in review_dto.strengths_feedback
    # Hallucinated 999 was caught by QuantitativeFaithfulnessValidator and replaced with safe fallback!
    assert "999" not in review_dto.bottlenecks_feedback
    assert repo.saved_model_used == "gemini-3.8-flash"
