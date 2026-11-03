import asyncio
from datetime import UTC, date, datetime
from typing import Any

import pytest
from uuid6 import uuid7

from src.execution.public_api import ExistingScheduledTaskDTO
from src.planning.application.services import (
    AI_BLOCK_MAX_MINUTES,
    AI_BLOCK_MIN_MINUTES,
    MANUAL_BLOCK_MAX_MINUTES,
    MANUAL_BLOCK_MIN_MINUTES,
    AvailabilityConfigurationDTO,
    AvailabilitySlotDTO,
    ProposalValidationGateOrchestrator,
)
from src.planning.domain.exceptions import (
    ActiveRoadmapLimitExceededError,
    InvalidRoadmapStateTransitionError,
    ProposalValidationGateError,
    SoftOverflowConfirmationRequiredError,
)
from src.planning.domain.models import (
    Goal,
    GoalStatus,
    Milestone,
    MilestoneStatus,
    OfficialSchedule,
    Roadmap,
    RoadmapStatus,
    ScheduleProposal,
    ScheduleProposalStatus,
    validate_milestone_sequence,
)
from src.shared_kernel.application.llm_port import LLMProviderPort
from src.shared_kernel.infrastructure.external_ai.litellm_adapter import MockLLMAdapter


def test_planning_domain_models_and_roadmap_state_machine() -> None:
    now = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)
    user_id = uuid7()
    goal = Goal(
        user_id=user_id,
        title="Chinh phục FastAPI & Hexagonal Architecture",
        raw_description="Học chuyên sâu trong 6 tuần",
        target_date=date(2026, 12, 15),
        created_at=now,
        updated_at=now,
    )
    assert goal.status == GoalStatus.ACTIVE

    roadmap = Roadmap(
        user_id=user_id,
        goal_id=goal.id,
        title="Lộ trình FastAPI 6 tuần",
        start_date=date(2026, 11, 1),
        target_date=date(2026, 12, 15),
        created_at=now,
        updated_at=now,
    )
    assert roadmap.status == RoadmapStatus.INITIALIZED

    # Cannot pause before activating
    with pytest.raises(InvalidRoadmapStateTransitionError):
        roadmap.pause(now)

    # Free tier limit OS-02: max 3 active roadmaps
    with pytest.raises(ActiveRoadmapLimitExceededError):
        roadmap.activate(now, tier="FREE", current_active_count=3)

    # Activate within limit
    roadmap.activate(now, tier="FREE", current_active_count=2)
    assert roadmap.status == RoadmapStatus.ACTIVE

    # Pause and re-activate
    roadmap.pause(now)
    assert roadmap.status == RoadmapStatus.PAUSED
    roadmap.activate(now, tier="PREMIUM", current_active_count=14)
    assert roadmap.status == RoadmapStatus.ACTIVE

    # Complete -> terminal state (cannot archive after completed)
    roadmap.complete(now)
    assert roadmap.status == RoadmapStatus.COMPLETED
    with pytest.raises(InvalidRoadmapStateTransitionError):
        roadmap.archive(now)

    # Milestones sequence validation
    milestones = [
        Milestone(
            roadmap_id=roadmap.id,
            sequence_order=i,
            title=f"Chặng {i}",
            created_at=now,
            updated_at=now,
        )
        for i in range(1, 4)
    ]
    validate_milestone_sequence(milestones, enforce_ai_bounds=True)
    milestones[0].approve(now)
    assert milestones[0].status == MilestoneStatus.APPROVED

    # OfficialSchedule & ScheduleProposal domain events and transitions
    schedule = OfficialSchedule(roadmap_id=roadmap.id, activated_at=now, updated_at=now)
    proposal = ScheduleProposal(
        roadmap_id=roadmap.id,
        user_id=user_id,
        proposal_data={"tasks": []},
        created_at=now,
    )
    assert proposal.status == ScheduleProposalStatus.DRAFT
    proposal.mark_applied(now)
    assert proposal.status == ScheduleProposalStatus.APPLIED
    schedule.apply_metrics(
        user_id=user_id,
        total_sessions=5,
        total_planned_minutes=300,
        now=now,
        proposal_id=proposal.id,
    )
    events = schedule.pull_domain_events()
    assert len(events) == 1
    assert events[0].event_type == "OfficialScheduleAppliedEvent"


@pytest.mark.asyncio
async def test_tier1_ai_vs_manual_duration_bounds_and_milestone_reference() -> None:
    assert AI_BLOCK_MIN_MINUTES == 30
    assert AI_BLOCK_MAX_MINUTES == 120
    assert MANUAL_BLOCK_MIN_MINUTES == 15
    assert MANUAL_BLOCK_MAX_MINUTES == 240

    m1 = uuid7()
    avail = AvailabilityConfigurationDTO(mode="MODE_A", default_daily_quota_minutes=240)
    gate = ProposalValidationGateOrchestrator()

    # 20m task: rejected for AI ([30, 120]), accepted for Manual ([15, 240])
    proposal_20m = {
        "tasks": [
            {
                "task_id": str(uuid7()),
                "milestone_id": str(m1),
                "title": "Ôn tập ngắn 20 phút",
                "estimated_minutes": 20,
                "scheduled_date": "2026-11-02",
            }
        ]
    }
    res_ai = await gate.validate_proposal(
        proposal_20m,
        availability=avail,
        valid_milestone_ids={m1},
        is_ai_generated=True,
    )
    assert res_ai.is_valid is False
    assert any(v.rule_code == "AI_TASK_DURATION_OUT_OF_BOUNDS" for v in res_ai.violations)

    res_manual = await gate.validate_proposal(
        proposal_20m,
        availability=avail,
        valid_milestone_ids={m1},
        is_ai_generated=False,
    )
    assert res_manual.is_valid is True

    # Invalid milestone reference
    res_bad_milestone = await gate.validate_proposal(
        proposal_20m,
        availability=avail,
        valid_milestone_ids={uuid7()},
        is_ai_generated=False,
    )
    assert res_bad_milestone.is_valid is False
    assert any(v.rule_code == "INVALID_MILESTONE_REFERENCE" for v in res_bad_milestone.violations)


@pytest.mark.asyncio
async def test_tier2_mode_a_quota_and_cross_roadmap_edf_conflict() -> None:
    m1 = uuid7()
    avail = AvailabilityConfigurationDTO(
        mode="MODE_A",
        daily_quota_minutes={"monday": 120},
        default_daily_quota_minutes=120,
    )
    gate = ProposalValidationGateOrchestrator()

    # Existing task from higher-priority EDF roadmap takes 60m on Monday 2026-11-02
    existing = [
        ExistingScheduledTaskDTO(
            task_id=uuid7(),
            roadmap_id=uuid7(),
            milestone_id=uuid7(),
            title="Lộ trình ưu tiên EDF",
            estimated_minutes=60,
            scheduled_date=date(2026, 11, 2),
            scheduled_start=None,
            scheduled_end=None,
            status="TODO",
            roadmap_target_date=date(2026, 11, 10),
        )
    ]

    # Proposed 90m + existing 60m = 150m > 120m quota -> EDF conflict
    proposal = {
        "tasks": [
            {
                "task_id": str(uuid7()),
                "milestone_id": str(m1),
                "title": "Học SQL nâng cao",
                "estimated_minutes": 90,
                "scheduled_date": "2026-11-02",
            }
        ]
    }
    res = await gate.validate_proposal(
        proposal,
        availability=avail,
        valid_milestone_ids={m1},
        existing_tasks=existing,
        current_roadmap_target_date=date(2026, 12, 1),
    )
    assert res.is_valid is False
    assert any(v.rule_code == "CROSS_ROADMAP_EDF_QUOTA_CONFLICT" for v in res.violations)


@pytest.mark.asyncio
async def test_tier2_mode_b_cross_midnight_and_soft_overflow_rules() -> None:
    m1 = uuid7()
    # Cross-midnight slot on Monday: 23:00 -> 01:00 (+1 day)
    avail = AvailabilityConfigurationDTO(
        mode="MODE_B",
        availability_slots=[
            AvailabilitySlotDTO(
                day_of_week="monday",
                start_time="23:00",
                end_time="01:00",
                end_day_offset=1,
            )
        ],
    )
    gate = ProposalValidationGateOrchestrator()

    # 1. Exact fit inside cross-midnight slot (23:00 -> 00:30 = 90m)
    fit_proposal = {
        "tasks": [
            {
                "task_id": str(uuid7()),
                "milestone_id": str(m1),
                "title": "Ca học đêm Cross-Midnight",
                "estimated_minutes": 90,
                "scheduled_date": "2026-11-02",
                "scheduled_start": "2026-11-02T23:00:00+00:00",
                "scheduled_end": "2026-11-03T00:30:00+00:00",
            }
        ]
    }
    res_fit = await gate.validate_proposal(
        fit_proposal,
        availability=avail,
        valid_milestone_ids={m1},
    )
    assert res_fit.is_valid is True
    assert len(res_fit.soft_overflow_warnings) == 0

    # 2. Soft overflow <= 30m on last task of day (23:30 -> 01:20 = 110m, overflows 01:00 by 20m)
    soft_overflow_proposal = {
        "tasks": [
            {
                "task_id": str(uuid7()),
                "milestone_id": str(m1),
                "title": "Ca học đêm tràn nhẹ 20p",
                "estimated_minutes": 110,
                "scheduled_date": "2026-11-02",
                "scheduled_start": "2026-11-02T23:30:00+00:00",
                "scheduled_end": "2026-11-03T01:20:00+00:00",
            }
        ]
    }
    res_soft = await gate.validate_proposal(
        soft_overflow_proposal,
        availability=avail,
        valid_milestone_ids={m1},
    )
    assert res_soft.is_valid is True
    assert len(res_soft.soft_overflow_warnings) == 1
    assert res_soft.soft_overflow_warnings[0].overflow_minutes == 20

    # Require confirmation on Apply when soft overflow exists
    with pytest.raises(SoftOverflowConfirmationRequiredError):
        await gate.validate_proposal(
            soft_overflow_proposal,
            availability=avail,
            valid_milestone_ids={m1},
            require_soft_overflow_confirmation=True,
            confirm_soft_overflow=False,
        )

    res_confirmed = await gate.validate_proposal(
        soft_overflow_proposal,
        availability=avail,
        valid_milestone_ids={m1},
        require_soft_overflow_confirmation=True,
        confirm_soft_overflow=True,
    )
    assert res_confirmed.is_valid is True

    # 3. Hard overflow > 30m (23:50 -> 01:40 = 110m, overflows 01:00 by 40m -> OVERFLOW_EXCEEDS_30M)
    hard_overflow_proposal = {
        "tasks": [
            {
                "task_id": str(uuid7()),
                "milestone_id": str(m1),
                "title": "Ca học đêm tràn 40p",
                "estimated_minutes": 110,
                "scheduled_date": "2026-11-02",
                "scheduled_start": "2026-11-02T23:50:00+00:00",
                "scheduled_end": "2026-11-03T01:40:00+00:00",
            }
        ]
    }
    res_hard = await gate.validate_proposal(
        hard_overflow_proposal,
        availability=avail,
        valid_milestone_ids={m1},
    )
    assert res_hard.is_valid is False
    assert any(v.rule_code == "OVERFLOW_EXCEEDS_30M" for v in res_hard.violations)


class _SlowTimeoutLLM(LLMProviderPort):
    async def generate_structured(
        self,
        prompt: str | None = None,
        system_prompt: str = "",
        response_schema: dict[str, Any] | type[Any] | None = None,
        *,
        user_prompt: str | None = None,
        temperature: float = 0.2,
    ) -> tuple[dict[str, Any], int, int]:
        _ = (prompt, system_prompt, response_schema, user_prompt, temperature)
        await asyncio.sleep(0.25)
        return {"score": 0.9, "advisory_warnings": []}, 10, 10

    async def stream_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ):  # type: ignore[override]
        _ = (system_prompt, user_prompt, temperature)
        yield "{}"


@pytest.mark.asyncio
async def test_tier3_pedagogical_judge_fail_open_on_timeout() -> None:
    m1 = uuid7()
    avail = AvailabilityConfigurationDTO(mode="MODE_A", default_daily_quota_minutes=120)
    gate = ProposalValidationGateOrchestrator(
        llm_provider=_SlowTimeoutLLM(),
        enable_tier3_judge=True,
        tier3_timeout_seconds=0.05,
    )
    proposal = {
        "tasks": [
            {
                "task_id": str(uuid7()),
                "milestone_id": str(m1),
                "title": "Nhiệm vụ hợp lệ Tier 1 & 2",
                "estimated_minutes": 60,
                "scheduled_date": "2026-11-02",
            }
        ]
    }
    res = await gate.validate_proposal(
        proposal,
        availability=avail,
        valid_milestone_ids={m1},
        goal_title="Học Python",
    )
    assert res.is_valid is True
    assert res.judge_skipped is True
    assert res.validated_proposal_data.get("judge_skipped") is True


@pytest.mark.asyncio
async def test_self_correction_retry_loop_recovers_on_attempt_2() -> None:
    m1 = uuid7()
    avail = AvailabilityConfigurationDTO(mode="MODE_A", default_daily_quota_minutes=120)

    # Attempt 1 violates AI duration (15m < 30m) and DAG cycle; Attempt 2 fixes both
    bad_attempt_1 = {
        "tasks": [
            {
                "task_id": "t1",
                "milestone_id": str(m1),
                "title": "Task 1 quá ngắn",
                "estimated_minutes": 15,
                "scheduled_date": "2026-11-02",
            },
            {
                "task_id": "t2",
                "milestone_id": str(m1),
                "title": "Task 2",
                "estimated_minutes": 60,
                "scheduled_date": "2026-11-02",
            },
        ],
        "dependencies": [
            {"predecessor_id": "t1", "successor_id": "t2"},
            {"predecessor_id": "t2", "successor_id": "t1"},
        ],
    }
    good_attempt_2 = {
        "tasks": [
            {
                "task_id": "t1",
                "milestone_id": str(m1),
                "title": "Task 1 đã sửa 45p",
                "estimated_minutes": 45,
                "scheduled_date": "2026-11-02",
            },
            {
                "task_id": "t2",
                "milestone_id": str(m1),
                "title": "Task 2 60p",
                "estimated_minutes": 60,
                "scheduled_date": "2026-11-03",
            },
        ],
        "dependencies": [
            {"predecessor_id": "t1", "successor_id": "t2"},
        ],
    }

    mock_llm = MockLLMAdapter(canned_responses=[bad_attempt_1, good_attempt_2])
    gate = ProposalValidationGateOrchestrator(llm_provider=mock_llm)

    retry_callbacks: list[tuple[int, int]] = []

    def on_retry(attempt: int, violations: Any) -> None:
        retry_callbacks.append((attempt, len(violations)))

    result = await gate.generate_and_validate_proposal_with_retry(
        system_prompt="System prompt",
        user_prompt="User prompt",
        response_schema=None,
        availability=avail,
        valid_milestone_ids={m1},
        max_retries=2,
        on_retry_callback=on_retry,
    )
    assert result.is_valid is True
    assert result.attempts_used == 2
    assert len(result.retry_history) == 1
    assert retry_callbacks == [(1, 2)]

    # When all 3 attempts fail, raises ProposalValidationGateError
    failing_llm = MockLLMAdapter(canned_responses=[bad_attempt_1, bad_attempt_1, bad_attempt_1])
    failing_gate = ProposalValidationGateOrchestrator(llm_provider=failing_llm)
    with pytest.raises(ProposalValidationGateError) as exc_info:
        await failing_gate.generate_and_validate_proposal_with_retry(
            system_prompt="System prompt",
            user_prompt="User prompt",
            response_schema=None,
            availability=avail,
            valid_milestone_ids={m1},
            max_retries=2,
        )
    assert exc_info.value.code == "AI_SCHEMA_VALIDATION_ERROR"
    assert len(exc_info.value.violations) >= 2
