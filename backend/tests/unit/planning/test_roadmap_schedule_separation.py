from datetime import UTC, date, datetime

import pytest
from uuid6 import uuid7

from src.execution.public_api import ExistingScheduledTaskDTO
from src.planning.application.services.existing_schedule_occupancy import (
    expand_existing_schedule_occupancy,
)
from src.planning.application.services.validation_gate import ProposalValidationGateOrchestrator
from src.planning.domain.exceptions.planning_exceptions import ProposalValidationGateError
from src.planning.domain.models.schedule_block import ScheduleBlock
from src.planning.domain.services.validation_types import AvailabilityConfigurationDTO
from src.shared_kernel.infrastructure.external_ai.litellm_adapter import MockLLMAdapter


@pytest.mark.asyncio
async def test_ai_dates_are_discarded_and_allocated_by_availability() -> None:
    milestone_id = uuid7()
    llm = MockLLMAdapter(
        canned_responses=[
            {
                "tasks": [
                    {
                        "task_id": "task-1",
                        "milestone_id": str(milestone_id),
                        "title": "Học Python",
                        "estimated_minutes": 60,
                        "scheduled_date": "2020-01-01",
                        "scheduled_start": "2020-01-01T01:00:00Z",
                        "scheduled_end": "2020-01-01T02:00:00Z",
                    }
                ],
                "dependencies": [],
            }
        ]
    )
    result = await ProposalValidationGateOrchestrator(
        llm_provider=llm,
        enable_tier3_judge=False,
    ).generate_and_validate_proposal_with_retry(
        system_prompt="planner",
        user_prompt="python",
        response_schema=None,
        availability=AvailabilityConfigurationDTO(mode="MODE_A", default_daily_quota_minutes=120),
        valid_milestone_ids={milestone_id},
        start_date=date(2026, 11, 12),
        deterministic_allocation=True,
    )
    assert result.is_valid
    assert result.validated_proposal_data["tasks"][0]["scheduled_date"] == "2026-11-12"


def test_no_slot_does_not_invent_a_fallback_time() -> None:
    from src.planning.domain.services.spatio_temporal_engine import SpatioTemporalRuleEngine

    tasks = SpatioTemporalRuleEngine.allocate_tasks_to_availability(
        [{"task_id": "one", "estimated_minutes": 60}],
        AvailabilityConfigurationDTO(mode="MODE_B", availability_slots=()),
        start_date=date(2026, 11, 12),
    )
    assert tasks[0]["scheduled_date"] is None
    assert tasks[0]["scheduled_start"] is None


def test_allocation_stops_at_roadmap_target_date() -> None:
    from src.planning.domain.services.spatio_temporal_engine import SpatioTemporalRuleEngine

    tasks = SpatioTemporalRuleEngine.allocate_tasks_to_availability(
        [
            {"task_id": "one", "estimated_minutes": 120},
            {"task_id": "two", "estimated_minutes": 120},
        ],
        AvailabilityConfigurationDTO(mode="MODE_A", default_daily_quota_minutes=120),
        start_date=date(2026, 11, 12),
        target_date=date(2026, 11, 12),
    )
    assert tasks[0]["scheduled_date"] == "2026-11-12"
    assert tasks[1]["scheduled_date"] is None


def test_task_effort_is_split_across_available_days() -> None:
    from src.planning.domain.services.spatio_temporal_engine import SpatioTemporalRuleEngine
    from src.planning.domain.services.validation_types import AvailabilitySlotDTO

    tasks, blocks = SpatioTemporalRuleEngine.allocate_task_sessions(
        [{"task_id": "one", "estimated_minutes": 120, "milestone_id": "m1"}],
        AvailabilityConfigurationDTO(
            mode="MODE_B",
            availability_slots=(
                AvailabilitySlotDTO("monday", "19:00", "20:00"),
                AvailabilitySlotDTO("tuesday", "19:00", "20:00"),
            ),
        ),
        start_date=date(2026, 11, 2),
        target_date=date(2026, 11, 3),
    )
    assert tasks[0]["estimated_minutes"] == 120
    assert [block["scheduled_duration_minutes"] for block in blocks] == [60, 60]
    assert [block["block_date"] for block in blocks] == ["2026-11-02", "2026-11-03"]
    assert tasks[0]["scheduled_start"] == blocks[0]["scheduled_start"]
    assert tasks[0]["scheduled_end"] == blocks[1]["scheduled_end"]


def test_mode_a_uses_configured_daily_capacity_for_session_size() -> None:
    from src.planning.domain.services.spatio_temporal_engine import SpatioTemporalRuleEngine

    quotas = {
        day: 30
        for day in ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
    }
    tasks, blocks = SpatioTemporalRuleEngine.allocate_task_sessions(
        [{"task_id": "one", "estimated_minutes": 60}],
        AvailabilityConfigurationDTO(
            mode="MODE_A", daily_quota_minutes=quotas, default_daily_quota_minutes=120
        ),
        start_date=date(2026, 11, 2),
        target_date=date(2026, 11, 3),
    )
    assert tasks[0]["scheduled_date"] == "2026-11-02"
    assert [block["scheduled_duration_minutes"] for block in blocks] == [30, 30]
    assert [block["block_date"] for block in blocks] == ["2026-11-02", "2026-11-03"]


def test_existing_roadmap_task_occupies_its_actual_time_window() -> None:
    from src.planning.domain.services.spatio_temporal_engine import SpatioTemporalRuleEngine
    from src.planning.domain.services.validation_types import AvailabilitySlotDTO

    existing = ExistingScheduledTaskDTO(
        task_id=uuid7(),
        roadmap_id=uuid7(),
        milestone_id=uuid7(),
        title="Phiên học đã có",
        estimated_minutes=60,
        scheduled_date=date(2026, 11, 2),
        scheduled_start=datetime(2026, 11, 2, 19, 0, tzinfo=UTC),
        scheduled_end=datetime(2026, 11, 2, 20, 0, tzinfo=UTC),
        status="TODO",
    )
    tasks, blocks = SpatioTemporalRuleEngine.allocate_task_sessions(
        [{"task_id": "new", "estimated_minutes": 60}],
        AvailabilityConfigurationDTO(
            mode="MODE_B",
            availability_slots=(AvailabilitySlotDTO("monday", "19:00", "21:00"),),
        ),
        start_date=date(2026, 11, 2),
        target_date=date(2026, 11, 2),
        existing_tasks=[existing],
    )
    assert tasks[0]["scheduled_start"] == "2026-11-02T20:00:00+00:00"
    assert blocks[0]["scheduled_end"] == "2026-11-02T21:00:00+00:00"


def test_allocator_converts_existing_utc_session_to_learner_timezone() -> None:
    from src.planning.domain.services.spatio_temporal_engine import SpatioTemporalRuleEngine
    from src.planning.domain.services.validation_types import AvailabilitySlotDTO

    existing = ExistingScheduledTaskDTO(
        task_id=uuid7(),
        roadmap_id=uuid7(),
        milestone_id=uuid7(),
        title="Phiên học đã có",
        estimated_minutes=60,
        scheduled_date=date(2026, 11, 2),
        scheduled_start=datetime(2026, 11, 2, 12, 0, tzinfo=UTC),
        scheduled_end=datetime(2026, 11, 2, 13, 0, tzinfo=UTC),
        status="TODO",
    )
    tasks, _ = SpatioTemporalRuleEngine.allocate_task_sessions(
        [{"task_id": "new", "estimated_minutes": 60}],
        AvailabilityConfigurationDTO(
            mode="MODE_B",
            availability_slots=(AvailabilitySlotDTO("monday", "19:00", "21:00"),),
            timezone="Asia/Ho_Chi_Minh",
        ),
        start_date=date(2026, 11, 2),
        target_date=date(2026, 11, 2),
        existing_tasks=[existing],
    )
    assert tasks[0]["scheduled_start"] == "2026-11-02T20:00:00+07:00"


def test_mode_b_validates_utc_timestamp_in_learner_timezone() -> None:
    from src.planning.domain.services.spatio_temporal_engine import SpatioTemporalRuleEngine
    from src.planning.domain.services.validation_types import AvailabilitySlotDTO

    violations, warnings = SpatioTemporalRuleEngine.validate_mode_b_slots(
        tasks=[
            {
                "task_id": "one",
                "estimated_minutes": 60,
                "scheduled_date": "2026-11-02",
                "scheduled_start": "2026-11-02T12:00:00+00:00",
                "scheduled_end": "2026-11-02T13:00:00+00:00",
            }
        ],
        availability=AvailabilityConfigurationDTO(
            mode="MODE_B",
            availability_slots=(AvailabilitySlotDTO("monday", "19:00", "20:00"),),
            timezone="Asia/Ho_Chi_Minh",
        ),
    )
    assert violations == []
    assert warnings == []


def test_completed_task_does_not_consume_future_capacity() -> None:
    from src.planning.domain.services.spatio_temporal_engine import SpatioTemporalRuleEngine
    from src.planning.domain.services.validation_types import AvailabilitySlotDTO

    existing = ExistingScheduledTaskDTO(
        task_id=uuid7(),
        roadmap_id=uuid7(),
        milestone_id=uuid7(),
        title="Đã học xong",
        estimated_minutes=60,
        scheduled_date=date(2026, 11, 2),
        scheduled_start=datetime(2026, 11, 2, 19, 0, tzinfo=UTC),
        scheduled_end=datetime(2026, 11, 2, 20, 0, tzinfo=UTC),
        status="COMPLETED",
    )
    tasks, _ = SpatioTemporalRuleEngine.allocate_task_sessions(
        [{"task_id": "new", "estimated_minutes": 60}],
        AvailabilityConfigurationDTO(
            mode="MODE_B",
            availability_slots=(AvailabilitySlotDTO("monday", "19:00", "20:00"),),
        ),
        start_date=date(2026, 11, 2),
        target_date=date(2026, 11, 2),
        existing_tasks=[existing],
    )
    assert tasks[0]["scheduled_start"] == "2026-11-02T19:00:00+00:00"


def test_other_roadmap_capacity_uses_each_schedule_block_date() -> None:
    task_id, roadmap_id, milestone_id = uuid7(), uuid7(), uuid7()
    task = ExistingScheduledTaskDTO(
        task_id=task_id,
        roadmap_id=roadmap_id,
        milestone_id=milestone_id,
        title="Bài dài",
        estimated_minutes=120,
        scheduled_date=date(2026, 11, 2),
        scheduled_start=datetime(2026, 11, 2, 19, 0, tzinfo=UTC),
        scheduled_end=datetime(2026, 11, 3, 20, 0, tzinfo=UTC),
        status="TODO",
    )
    blocks = [
        ScheduleBlock(
            roadmap_id=roadmap_id,
            task_id=task_id,
            sequence_in_task=index,
            block_date=day,
            start_time=start,
            end_time=start.replace(hour=20),
            scheduled_duration_minutes=60,
        )
        for index, day, start in (
            (1, date(2026, 11, 2), datetime(2026, 11, 2, 19, 0, tzinfo=UTC)),
            (2, date(2026, 11, 3), datetime(2026, 11, 3, 19, 0, tzinfo=UTC)),
        )
    ]
    occupied = expand_existing_schedule_occupancy([task], blocks)
    assert [(item.scheduled_date, item.estimated_minutes) for item in occupied] == [
        (date(2026, 11, 2), 60),
        (date(2026, 11, 3), 60),
    ]
    blocks[0].status = "COMPLETED"
    occupied = expand_existing_schedule_occupancy([task], blocks)
    assert [(item.scheduled_date, item.estimated_minutes) for item in occupied] == [
        (date(2026, 11, 3), 60)
    ]


def test_gate_rejects_overlapping_sessions_even_in_quota_mode() -> None:
    milestone_id = str(uuid7())
    proposal = {
        "tasks": [
            {
                "task_id": "one",
                "milestone_id": milestone_id,
                "title": "Bài một",
                "estimated_minutes": 60,
                "scheduled_date": "2026-11-02",
                "scheduled_start": "2026-11-02T19:00:00+00:00",
                "scheduled_end": "2026-11-02T20:00:00+00:00",
            },
            {
                "task_id": "two",
                "milestone_id": milestone_id,
                "title": "Bài hai",
                "estimated_minutes": 60,
                "scheduled_date": "2026-11-02",
                "scheduled_start": "2026-11-02T19:30:00+00:00",
                "scheduled_end": "2026-11-02T20:30:00+00:00",
            },
        ],
        "schedule_blocks": [
            {
                "task_id": task_id,
                "sequence_in_task": 1,
                "block_date": "2026-11-02",
                "scheduled_start": start,
                "scheduled_end": end,
                "scheduled_duration_minutes": 60,
            }
            for task_id, start, end in (
                ("one", "2026-11-02T19:00:00+00:00", "2026-11-02T20:00:00+00:00"),
                ("two", "2026-11-02T19:30:00+00:00", "2026-11-02T20:30:00+00:00"),
            )
        ],
    }
    violations = ProposalValidationGateOrchestrator.run_tier1_gate(proposal, is_ai_generated=False)
    assert "SCHEDULE_BLOCK_OVERLAP" in {item.rule_code for item in violations}


@pytest.mark.asyncio
async def test_ai_proposal_is_rejected_when_target_date_has_no_capacity() -> None:
    milestone_id = uuid7()
    llm = MockLLMAdapter(
        canned_responses=[
            {
                "tasks": [
                    {
                        "task_id": f"task-{index}",
                        "milestone_id": str(milestone_id),
                        "title": f"Nhiệm vụ {index}",
                        "estimated_minutes": 120,
                    }
                    for index in range(2)
                ],
                "dependencies": [],
            }
        ]
    )
    with pytest.raises(ProposalValidationGateError):
        await ProposalValidationGateOrchestrator(
            llm_provider=llm,
            enable_tier3_judge=False,
        ).generate_and_validate_proposal_with_retry(
            system_prompt="planner",
            user_prompt="python",
            response_schema=None,
            availability=AvailabilityConfigurationDTO(
                mode="MODE_A", default_daily_quota_minutes=120
            ),
            valid_milestone_ids={milestone_id},
            start_date=date(2026, 11, 12),
            current_roadmap_target_date=date(2026, 11, 12),
            deterministic_allocation=True,
            max_retries=0,
        )
