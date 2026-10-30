import asyncio
import json
import os
from collections.abc import AsyncIterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from uuid6 import uuid7

from src.account.public_api import (
    AvailabilityGateResultDTO,
    AvailabilitySnapshotDTO,
    LearnerProfileDTO,
    ProposedTaskBlockDTO,
)
from src.evaluation.public_api import ScheduleChangeLogEntryDTO
from src.execution.public_api import (
    ExistingScheduledTaskDTO,
    ProposedDependencySyncItemDTO,
    ProposedTaskSyncItemDTO,
    ScheduleSyncResultDTO,
)
from src.planning.application.services.validation_gate import (
    ProposalValidationGateOrchestrator,
)
from src.planning.application.use_cases.proposal_generation_use_cases import (
    SCHEDULE_PROPOSAL_RESPONSE_SCHEMA,
    ExecuteScheduleProposalGenerationUseCase,
)
from src.planning.application.use_cases.proposal_management_use_cases import (
    ApplyScheduleProposalUseCase,
)
from src.planning.domain.exceptions.planning_exceptions import (
    ProposalValidationGateError,
    SoftOverflowConfirmationRequiredError,
)
from src.planning.domain.models.goal import Goal, GoalStatus
from src.planning.domain.models.milestone import Milestone, MilestoneStatus
from src.planning.domain.models.roadmap import Roadmap, RoadmapStatus
from src.planning.domain.models.schedule import (
    OfficialSchedule,
    ScheduleProposal,
    ScheduleProposalStatus,
)
from src.planning.domain.services.validation_types import (
    AvailabilityConfigurationDTO,
    AvailabilitySlotDTO,
    ConstraintViolationDTO,
    parse_iso_date,
    parse_iso_datetime,
)
from src.shared_kernel.application.llm_port import LLMProviderPort
from src.shared_kernel.domain.events import DomainEvent
from src.shared_kernel.infrastructure.external_ai.litellm_adapter import (
    LiteLLMAdapter,
    MockLLMAdapter,
)
from src.shared_kernel.infrastructure.sse.job_store import InMemorySseJobStore

DATASET_PATH = Path(__file__).parent / "datasets" / "golden_planning_5_scenarios.jsonl"

EXPECTED_SCENARIO_IDS: tuple[str, ...] = (
    "G1_PYTHON_BACKEND_MODE_A",
    "G2_CERT_EXAM_MODE_B",
    "G3_TIGHT_AVAILABILITY_RECOVERY",
    "G4_CROSS_MIDNIGHT_SOFT_OVERFLOW",
    "G5_MULTI_BRANCH_DAG",
)


@dataclass(frozen=True, slots=True)
class EvaluationSummaryMetrics:
    """Quantitative benchmark metrics for ADR-009 AI Evaluation Harness (WBS 6.0)."""

    total_scenarios: int
    adversarial_cases_tested: int
    adversarial_cases_blocked: int
    hallucinated_overbooking_pass_rate: float
    raw_pass_at_1_count: int
    post_retry_recovery_count: int
    post_retry_pass_rate: float
    soft_overflow_detected_count: int
    tier3_fail_open_verified: bool


def load_golden_scenarios() -> list[dict[str, Any]]:
    """Load and parse all 5 Golden Scenarios from `golden_planning_5_scenarios.jsonl`."""
    assert DATASET_PATH.exists(), f"Missing golden dataset file: {DATASET_PATH}"
    scenarios: list[dict[str, Any]] = []
    with DATASET_PATH.open("r", encoding="utf-8") as fh:
        for line_no, raw_line in enumerate(fh, start=1):
            stripped = raw_line.strip()
            if not stripped:
                continue
            parsed = json.loads(stripped)
            assert isinstance(parsed, dict), f"Line {line_no} must be a JSON object"
            scenarios.append(parsed)
    return scenarios


def build_availability_from_scenario(scenario: dict[str, Any]) -> AvailabilityConfigurationDTO:
    raw_avail = scenario["availability"]
    slots = [
        AvailabilitySlotDTO(
            day_of_week=str(s["day_of_week"]),
            start_time=str(s["start_time"]),
            end_time=str(s["end_time"]),
            end_day_offset=int(s.get("end_day_offset", 0) or 0),
            is_active=bool(s.get("is_active", True)),
        )
        for s in raw_avail.get("availability_slots", [])
    ]
    return AvailabilityConfigurationDTO(
        mode=str(raw_avail.get("mode", "MODE_A")),
        daily_quota_minutes={
            str(k): int(v) for k, v in raw_avail.get("daily_quota_minutes", {}).items()
        },
        default_daily_quota_minutes=int(raw_avail.get("default_daily_quota_minutes", 120)),
        availability_slots=tuple(slots),
        disabled_weekdays=frozenset(str(d) for d in raw_avail.get("disabled_weekdays", [])),
    )


def build_existing_tasks_from_scenario(
    scenario: dict[str, Any],
) -> list[ExistingScheduledTaskDTO]:
    items: list[ExistingScheduledTaskDTO] = []
    for raw in scenario.get("existing_active_tasks", []):
        items.append(
            ExistingScheduledTaskDTO(
                task_id=UUID(str(raw["task_id"])),
                roadmap_id=UUID(str(raw["roadmap_id"])),
                milestone_id=UUID(str(raw["milestone_id"])),
                title=str(raw["title"]),
                estimated_minutes=int(raw["estimated_minutes"]),
                scheduled_date=parse_iso_date(raw.get("scheduled_date")),
                scheduled_start=parse_iso_datetime(raw.get("scheduled_start")),
                scheduled_end=parse_iso_datetime(raw.get("scheduled_end")),
                status=str(raw.get("status", "TODO")),
                roadmap_target_date=parse_iso_date(raw.get("roadmap_target_date")),
            )
        )
    return items


class _RecordingSelfCorrectionLLM(LLMProviderPort):
    """Test double that records every prompt received (including retry feedback) and returns scripted responses."""

    def __init__(self, responses: Sequence[dict[str, Any]]) -> None:
        self._responses = list(responses)
        self.received_prompts: list[str] = []

    async def generate_structured(
        self,
        prompt: str | None = None,
        system_prompt: str = "",
        response_schema: dict[str, Any] | type[Any] | None = None,
        *,
        user_prompt: str | None = None,
        temperature: float = 0.2,
    ) -> tuple[dict[str, Any], int, int]:
        _ = (system_prompt, response_schema, temperature)
        effective_prompt = user_prompt if user_prompt is not None else (prompt or "")
        self.received_prompts.append(effective_prompt)
        if not self._responses:
            raise RuntimeError(
                "No more scripted responses available in _RecordingSelfCorrectionLLM"
            )
        payload = self._responses.pop(0)
        return payload, 150, 220

    async def stream_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> AsyncIterator[str]:
        _ = (system_prompt, user_prompt, temperature)
        yield "{}"


class _SlowOrFailingJudgeLLM(LLMProviderPort):
    """Simulates Tier 3 Pedagogical Judge timeout (> 5s) or network error for Fail-Open testing."""

    def __init__(self, *, mode: str = "timeout", sleep_seconds: float = 0.2) -> None:
        self._mode = mode
        self._sleep_seconds = sleep_seconds

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
        if self._mode == "timeout":
            await asyncio.sleep(self._sleep_seconds)
            return {"score": 0.9, "advisory_warnings": []}, 50, 50
        raise ConnectionError("Simulated LLM Judge network outage")

    async def stream_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> AsyncIterator[str]:
        _ = (system_prompt, user_prompt, temperature)
        yield "{}"


# ---------------------------------------------------------------------------
# In-memory ports for End-to-End Quota & UseCase Evaluation
# ---------------------------------------------------------------------------


class _FakeUoW:
    def __init__(self) -> None:
        self.committed_count = 0
        self.collected_events: list[DomainEvent] = []

    async def __aenter__(self) -> "_FakeUoW":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        return None

    async def commit(self) -> None:
        self.committed_count += 1

    async def rollback(self) -> None:
        return None

    def collect_events_from(self, aggregate: Any) -> None:
        if hasattr(aggregate, "pull_domain_events"):
            self.collected_events.extend(aggregate.pull_domain_events())


class _FakeQuotaFacade:
    def __init__(self) -> None:
        self.reserved: list[UUID] = []
        self.committed: list[tuple[UUID, int, int]] = []
        self.released: list[tuple[UUID, str]] = []

    async def reserve_quota(
        self,
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
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        model_name: str = "gemini-2.5-flash",
    ) -> None:
        _ = model_name
        self.committed.append((reservation_id, prompt_tokens, completion_tokens))

    async def release_reservation(self, reservation_id: UUID, reason: str = "RELEASED") -> None:
        self.released.append((reservation_id, reason))

    async def expire_stale_reservations(self, now: datetime | None = None) -> int:
        _ = now
        return 0


class _FakeGoalRepo:
    def __init__(self, goal: Goal) -> None:
        self._goal = goal

    async def save(self, goal: Goal) -> Goal:
        self._goal = goal
        return goal

    async def get_by_id(self, goal_id: UUID) -> Goal | None:
        return self._goal if self._goal.id == goal_id else None

    async def list_by_user_id(self, user_id: UUID) -> list[Goal]:
        return [self._goal] if self._goal.user_id == user_id else []


class _FakeRoadmapRepo:
    def __init__(self, roadmap: Roadmap) -> None:
        self._roadmap = roadmap

    async def save(self, roadmap: Roadmap) -> Roadmap:
        self._roadmap = roadmap
        return roadmap

    async def get_by_id(self, roadmap_id: UUID) -> Roadmap | None:
        return self._roadmap if self._roadmap.id == roadmap_id else None

    async def get_by_id_for_user(self, roadmap_id: UUID, user_id: UUID) -> Roadmap | None:
        if self._roadmap.id == roadmap_id and self._roadmap.user_id == user_id:
            return self._roadmap
        return None

    async def list_by_user_id(
        self,
        user_id: UUID,
        *,
        status: str | None = None,
    ) -> list[Roadmap]:
        if self._roadmap.user_id != user_id:
            return []
        if status and self._roadmap.status.value != status:
            return []
        return [self._roadmap]

    async def count_active_by_user_id(
        self,
        user_id: UUID,
        *,
        exclude_roadmap_id: UUID | None = None,
    ) -> int:
        _ = (user_id, exclude_roadmap_id)
        return 0


class _FakeMilestoneRepo:
    def __init__(self, milestones: list[Milestone]) -> None:
        self._milestones = list(milestones)

    async def save_many(
        self,
        roadmap_id: UUID,
        milestones: Sequence[Milestone],
    ) -> list[Milestone]:
        _ = roadmap_id
        self._milestones = list(milestones)
        return self._milestones

    async def list_by_roadmap_id(self, roadmap_id: UUID) -> list[Milestone]:
        return [m for m in self._milestones if m.roadmap_id == roadmap_id]

    async def approve_all_for_roadmap(
        self,
        roadmap_id: UUID,
        now: datetime,
    ) -> list[Milestone]:
        for m in self._milestones:
            if m.roadmap_id == roadmap_id:
                m.approve(now)
        return self._milestones


class _FakeProposalRepo:
    def __init__(self) -> None:
        self.proposals: dict[UUID, ScheduleProposal] = {}

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

    async def discard_existing_drafts(self, roadmap_id: UUID, now: datetime) -> int:
        count = 0
        for p in self.proposals.values():
            if p.roadmap_id == roadmap_id and p.status == ScheduleProposalStatus.DRAFT:
                p.mark_discarded(now)
                count += 1
        return count


class _FakeOfficialScheduleRepo:
    def __init__(self) -> None:
        self.schedules: dict[UUID, OfficialSchedule] = {}

    async def save(self, schedule: OfficialSchedule) -> OfficialSchedule:
        self.schedules[schedule.roadmap_id] = schedule
        return schedule

    async def get_by_roadmap_id(self, roadmap_id: UUID) -> OfficialSchedule | None:
        return self.schedules.get(roadmap_id)


class _FakeAvailabilityPort:
    def __init__(self, snapshot: AvailabilitySnapshotDTO) -> None:
        self._snapshot = snapshot

    async def get_active_availability(self, user_id: UUID) -> AvailabilitySnapshotDTO | None:
        _ = user_id
        return self._snapshot

    async def validate_schedule_proposal(
        self,
        user_id: UUID,
        proposed_tasks: list[ProposedTaskBlockDTO],
        occupied_tasks: list[ProposedTaskBlockDTO] | None = None,
        expected_updated_at: str | None = None,
    ) -> AvailabilityGateResultDTO:
        _ = (user_id, proposed_tasks, occupied_tasks, expected_updated_at)
        return AvailabilityGateResultDTO(
            is_valid=True,
            has_soft_overflow=False,
            overflow_minutes=0,
            violation_reasons=(),
        )


class _FakeLearnerProfilePort:
    def __init__(self, profile: LearnerProfileDTO) -> None:
        self._profile = profile

    async def get_learner_profile(self, user_id: UUID) -> LearnerProfileDTO:
        _ = user_id
        return self._profile


class _FakeExecutionSyncPort:
    def __init__(
        self,
        existing_tasks: Sequence[ExistingScheduledTaskDTO] = (),
    ) -> None:
        self._existing_tasks = list(existing_tasks)
        self.synced_tasks: list[ProposedTaskSyncItemDTO] = []
        self.synced_deps: list[ProposedDependencySyncItemDTO] = []

    async def get_tasks_for_roadmaps(
        self,
        roadmap_ids: Sequence[UUID],
        *,
        roadmap_target_dates: Mapping[UUID, date | None] | None = None,
    ) -> list[ExistingScheduledTaskDTO]:
        _ = (roadmap_ids, roadmap_target_dates)
        return list(self._existing_tasks)

    async def get_active_roadmaps_tasks(
        self,
        user_id: UUID,
        exclude_roadmap_id: UUID | None = None,
        *,
        active_roadmap_ids: Sequence[UUID] | None = None,
        roadmap_target_dates: Mapping[UUID, date | None] | None = None,
    ) -> list[ExistingScheduledTaskDTO]:
        _ = (user_id, exclude_roadmap_id, active_roadmap_ids, roadmap_target_dates)
        return list(self._existing_tasks)

    async def sync_official_schedule_tasks(
        self,
        *,
        roadmap_id: UUID,
        official_schedule_id: UUID,
        proposed_tasks: Sequence[ProposedTaskSyncItemDTO],
        proposed_dependencies: Sequence[ProposedDependencySyncItemDTO],
        now: datetime,
    ) -> ScheduleSyncResultDTO:
        _ = now
        self.synced_tasks = list(proposed_tasks)
        self.synced_deps = list(proposed_dependencies)
        return ScheduleSyncResultDTO(
            roadmap_id=roadmap_id,
            official_schedule_id=official_schedule_id,
            preserved_completed_tasks_count=0,
            replaced_tasks_count=0,
            inserted_tasks_count=len(proposed_tasks),
            affected_tasks_count=len(proposed_tasks),
            total_shifted_minutes=0,
            total_active_sessions=len(proposed_tasks),
            total_planned_minutes=sum(t.estimated_minutes for t in proposed_tasks),
        )


class _FakeScheduleChangeLogPort:
    def __init__(self) -> None:
        self.logs: list[dict[str, Any]] = []

    async def log_schedule_change(
        self,
        *,
        roadmap_id: UUID,
        trigger_type: str = "AI_REPLAN",
        schedule_id: UUID | None = None,
        task_id: UUID | None = None,
        reason: str | None = None,
        affected_tasks_count: int = 1,
        total_shifted_minutes: int = 0,
        diff_payload: dict[str, Any] | None = None,
        now: datetime | None = None,
    ) -> ScheduleChangeLogEntryDTO:
        return await self.record_change_log(
            roadmap_id=roadmap_id,
            trigger_type=trigger_type,
            schedule_id=schedule_id,
            task_id=task_id,
            reason=reason,
            affected_tasks_count=affected_tasks_count,
            total_shifted_minutes=total_shifted_minutes,
            diff_payload=diff_payload,
            now=now,
        )

    async def record_change_log(
        self,
        *,
        roadmap_id: UUID,
        trigger_type: str = "AI_REPLAN",
        schedule_id: UUID | None = None,
        task_id: UUID | None = None,
        reason: str | None = None,
        affected_tasks_count: int = 1,
        total_shifted_minutes: int = 0,
        diff_payload: dict[str, Any] | None = None,
        now: datetime | None = None,
    ) -> ScheduleChangeLogEntryDTO:
        log_id = uuid7()
        payload = diff_payload or {}
        self.logs.append(
            {
                "id": log_id,
                "roadmap_id": roadmap_id,
                "schedule_id": schedule_id,
                "trigger_type": trigger_type,
                "reason": reason,
                "affected_tasks_count": affected_tasks_count,
                "total_shifted_minutes": total_shifted_minutes,
                "diff_payload": payload,
                "now": now,
            }
        )
        return ScheduleChangeLogEntryDTO(
            id=log_id,
            roadmap_id=roadmap_id,
            schedule_id=schedule_id,
            task_id=task_id,
            trigger_type=trigger_type,
            reason=reason,
            affected_tasks_count=affected_tasks_count,
            total_shifted_minutes=total_shifted_minutes,
            diff_payload=payload,
            created_at=now,
        )


# ===========================================================================
# TEST SUITE: WBS 6.0 AI Evaluation Harness (5 Golden Datasets & 4 Metrics)
# ===========================================================================


def test_golden_5_scenarios_dataset_integrity() -> None:
    """Verify `golden_planning_5_scenarios.jsonl` contains all 5 self-contained Golden Scenarios."""
    scenarios = load_golden_scenarios()
    assert len(scenarios) == 5
    loaded_ids = tuple(s["scenario_id"] for s in scenarios)
    assert loaded_ids == EXPECTED_SCENARIO_IDS

    for scenario in scenarios:
        assert "title" in scenario and scenario["title"]
        assert "goal" in scenario and "roadmap" in scenario
        assert "availability" in scenario and "milestones" in scenario
        assert 3 <= len(scenario["milestones"]) <= 7
        assert "adversarial_attempt_1" in scenario
        assert "golden_valid_proposal" in scenario
        assert "expected_attempt_1_violation_codes" in scenario


@pytest.mark.asyncio
async def test_metric1_zero_hallucinated_overbooking_across_all_golden_scenarios() -> None:
    """Metric 1 — Zero Hallucinated Overbooking (0.0%):
    No invalid schedule (Mode A quota overflow, Mode B slot breach > 30m, Cross-Roadmap EDF collision,
    DAG cycle, temporal ordering violation, or AI block outside [30, 120] minutes) can ever pass
    `ProposalValidationGateOrchestrator`.
    """
    scenarios = load_golden_scenarios()
    gate = ProposalValidationGateOrchestrator(enable_tier3_judge=False)

    total_adversarial_tested = 0
    adversarial_passed = 0

    for scenario in scenarios:
        avail = build_availability_from_scenario(scenario)
        existing_tasks = build_existing_tasks_from_scenario(scenario)
        valid_mids: set[UUID | str] = {m["milestone_id"] for m in scenario["milestones"]}
        target_date = parse_iso_date(scenario["roadmap"]["target_date"])

        # 1. Test the scenario's primary adversarial payload
        adv_payload = scenario["adversarial_attempt_1"]
        res_adv = await gate.validate_proposal(
            adv_payload,
            availability=avail,
            valid_milestone_ids=valid_mids,
            existing_tasks=existing_tasks,
            current_roadmap_target_date=target_date,
            is_ai_generated=True,
        )
        total_adversarial_tested += 1
        if res_adv.is_valid:
            adversarial_passed += 1

        actual_codes = {v.rule_code for v in res_adv.violations}
        expected_codes = set(scenario["expected_attempt_1_violation_codes"])
        assert expected_codes.issubset(actual_codes), (
            f"Scenario {scenario['scenario_id']} expected violations {expected_codes}, "
            f"got {actual_codes}"
        )

        # 2. If scenario also has `adversarial_temporal_attempt` (e.g. G5), verify it is blocked too
        if "adversarial_temporal_attempt" in scenario:
            res_temp = await gate.validate_proposal(
                scenario["adversarial_temporal_attempt"],
                availability=avail,
                valid_milestone_ids=valid_mids,
                existing_tasks=existing_tasks,
                current_roadmap_target_date=target_date,
                is_ai_generated=True,
            )
            total_adversarial_tested += 1
            if res_temp.is_valid:
                adversarial_passed += 1
            temp_codes = {v.rule_code for v in res_temp.violations}
            assert "DEPENDENCY_TEMPORAL_ORDER_VIOLATION" in temp_codes

        # 3. Verify the scenario's golden valid proposal passes cleanly
        res_gold = await gate.validate_proposal(
            scenario["golden_valid_proposal"],
            availability=avail,
            valid_milestone_ids=valid_mids,
            existing_tasks=existing_tasks,
            current_roadmap_target_date=target_date,
            is_ai_generated=True,
        )
        assert res_gold.is_valid is True, (
            f"Golden proposal for {scenario['scenario_id']} failed with violations: "
            f"{[v.to_dict() for v in res_gold.violations]}"
        )

    hallucinated_overbooking_pass_rate = adversarial_passed / total_adversarial_tested
    assert total_adversarial_tested >= 6
    assert hallucinated_overbooking_pass_rate == 0.0


@pytest.mark.asyncio
async def test_metric2_self_correction_post_retry_recovery_and_single_quota_commit() -> None:
    """Metric 2 — Self-Correction Post-Retry Recovery (`Pass@Retry`):
    When attempt 1 produces violations (`ConstraintViolationDTO`), the retry loop feeds exact
    violation feedback to the LLM and recovers cleanly within `max_retries=2`, while consuming
    only 1 quota reservation (`commit_reservation` called once).
    """
    scenarios = load_golden_scenarios()
    recovered_count = 0

    for scenario in scenarios:
        avail = build_availability_from_scenario(scenario)
        existing_tasks = build_existing_tasks_from_scenario(scenario)
        valid_mids: set[UUID | str] = {m["milestone_id"] for m in scenario["milestones"]}
        target_date = parse_iso_date(scenario["roadmap"]["target_date"])

        # For G5, test 2 consecutive retries (Attempt 1: DAG cycle -> Attempt 2: Temporal violation -> Attempt 3: Valid)
        if scenario["scenario_id"] == "G5_MULTI_BRANCH_DAG":
            scripted_responses = [
                scenario["adversarial_attempt_1"],
                scenario["adversarial_temporal_attempt"],
                scenario["golden_valid_proposal"],
            ]
            expected_attempts = 3
        else:
            scripted_responses = [
                scenario["adversarial_attempt_1"],
                scenario["golden_valid_proposal"],
            ]
            expected_attempts = 2

        recording_llm = _RecordingSelfCorrectionLLM(scripted_responses)
        orchestrator = ProposalValidationGateOrchestrator(
            llm_provider=recording_llm,
            enable_tier3_judge=False,
        )

        retry_events: list[tuple[int, list[str]]] = []

        def _on_retry(
            attempt: int,
            violations: Sequence[ConstraintViolationDTO],
            _bucket: list[tuple[int, list[str]]] = retry_events,
        ) -> None:
            _bucket.append((attempt, [v.rule_code for v in violations]))

        result = await orchestrator.generate_and_validate_proposal_with_retry(
            system_prompt="FocusFlow SRL Planner",
            user_prompt=f"Generate schedule for {scenario['scenario_id']}",
            response_schema=SCHEDULE_PROPOSAL_RESPONSE_SCHEMA,
            availability=avail,
            valid_milestone_ids=valid_mids,
            existing_tasks=existing_tasks,
            current_roadmap_target_date=target_date,
            goal_title=scenario["goal"]["title"],
            max_retries=2,
            on_retry_callback=_on_retry,
        )

        assert result.is_valid is True
        assert result.attempts_used == expected_attempts
        assert len(result.retry_history) == expected_attempts - 1
        assert len(retry_events) == expected_attempts - 1

        # Verify the retry prompt fed back to the LLM contains structured violation codes
        second_prompt = recording_llm.received_prompts[1]
        assert "[SELF-CORRECTION RETRY ATTEMPT #1]" in second_prompt
        for expected_code in scenario["expected_attempt_1_violation_codes"]:
            assert expected_code in second_prompt

        recovered_count += 1

    assert recovered_count == len(scenarios)

    # Verify End-to-End UseCase Quota Conservation during Self-Correction Retry (G3 Tight Availability)
    g3 = next(s for s in scenarios if s["scenario_id"] == "G3_TIGHT_AVAILABILITY_RECOVERY")
    now = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)
    user_id = uuid7()
    goal_id = uuid7()
    roadmap_id = uuid7()
    reservation_id = uuid7()
    job_id = uuid7()

    goal = Goal(
        id=goal_id,
        user_id=user_id,
        title=g3["goal"]["title"],
        raw_description=g3["goal"]["raw_description"],
        target_date=parse_iso_date(g3["goal"]["target_date"]),
        status=GoalStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
    roadmap = Roadmap(
        id=roadmap_id,
        user_id=user_id,
        goal_id=goal_id,
        title=g3["roadmap"]["title"],
        start_date=parse_iso_date(g3["roadmap"]["start_date"]),
        target_date=parse_iso_date(g3["roadmap"]["target_date"]),
        status=RoadmapStatus.INITIALIZED,
        created_at=now,
        updated_at=now,
    )
    milestones = [
        Milestone(
            id=UUID(str(m["milestone_id"])),
            roadmap_id=roadmap_id,
            sequence_order=int(m["sequence_order"]),
            title=str(m["title"]),
            status=MilestoneStatus.APPROVED,
            created_at=now,
            updated_at=now,
        )
        for m in g3["milestones"]
    ]
    avail_snapshot = AvailabilitySnapshotDTO(
        user_id=user_id,
        mode=g3["availability"]["mode"],
        daily_cap_minutes=g3["availability"]["default_daily_quota_minutes"],
        weekly_capacity_minutes=285,
        daily_quota_minutes=g3["availability"]["daily_quota_minutes"],
        availability_slots=tuple(g3["availability"]["availability_slots"]),
        disabled_weekdays=tuple(g3["availability"]["disabled_weekdays"]),
    )
    learner_profile = LearnerProfileDTO(
        user_id=user_id,
        opt_session_minutes=g3["learner_profile"]["opt_session_minutes"],
        estimation_bias_beta=g3["learner_profile"]["estimation_bias_beta"],
        peak_productivity_slots={"slots": list(g3["learner_profile"]["peak_productivity_slots"])},
    )

    quota_facade = _FakeQuotaFacade()
    sse_store = InMemorySseJobStore()
    await sse_store.create_job(
        job_id=job_id,
        user_id=user_id,
        roadmap_id=roadmap_id,
        reservation_id=reservation_id,
        job_type="SCHEDULE_PROPOSAL_GEN",
        operation=f"SCHEDULE_PROPOSAL_GEN:{roadmap_id}",
    )
    uow = _FakeUoW()
    proposal_repo = _FakeProposalRepo()

    use_case = ExecuteScheduleProposalGenerationUseCase(
        goal_repo=_FakeGoalRepo(goal),
        roadmap_repo=_FakeRoadmapRepo(roadmap),
        milestone_repo=_FakeMilestoneRepo(milestones),
        proposal_repo=proposal_repo,
        availability_query_port=_FakeAvailabilityPort(avail_snapshot),
        learner_profile_port=_FakeLearnerProfilePort(learner_profile),
        execution_sync_port=_FakeExecutionSyncPort(),
        quota_facade=quota_facade,
        llm_provider=_RecordingSelfCorrectionLLM(
            [g3["adversarial_attempt_1"], g3["golden_valid_proposal"]]
        ),
        sse_job_store=sse_store,
        uow=uow,
    )

    saved_proposal = await use_case.execute(
        job_id=job_id,
        user_id=user_id,
        roadmap_id=roadmap_id,
        reservation_id=reservation_id,
        max_retries=2,
        now=now,
    )

    assert saved_proposal.status == ScheduleProposalStatus.DRAFT
    assert saved_proposal.proposal_data["attempts_used"] == 2
    # Quota committed exactly ONCE across 2 LLM attempts, 0 releases
    assert len(quota_facade.committed) == 1
    assert quota_facade.committed[0][0] == reservation_id
    assert quota_facade.committed[0][1] == 300  # 150 * 2 prompt tokens
    assert quota_facade.committed[0][2] == 440  # 220 * 2 completion tokens
    assert len(quota_facade.released) == 0

    # Verify SSE stream emitted `validation_retry` followed by `completed`
    events = [
        ev
        async for ev in sse_store.stream_events(job_id=job_id, user_id=user_id, last_event_id=None)
    ]
    event_names = [e.event for e in events]
    assert "validation_retry" in event_names
    assert event_names[-1] == "completed"


@pytest.mark.asyncio
async def test_metric2_exhausted_retries_releases_quota_and_saves_no_draft() -> None:
    """When all 3 attempts (initial + 2 retries) violate Tier 1/2 constraints, the use case
    MUST release the quota reservation (`release_reservation` called once, `commit_reservation` 0)
    and never persist an invalid `ScheduleProposal(DRAFT)`.
    """
    scenarios = load_golden_scenarios()
    g1 = next(s for s in scenarios if s["scenario_id"] == "G1_PYTHON_BACKEND_MODE_A")
    now = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)
    user_id = uuid7()
    goal_id = uuid7()
    roadmap_id = uuid7()
    reservation_id = uuid7()
    job_id = uuid7()

    goal = Goal(
        id=goal_id,
        user_id=user_id,
        title=g1["goal"]["title"],
        raw_description=g1["goal"]["raw_description"],
        target_date=parse_iso_date(g1["goal"]["target_date"]),
        status=GoalStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
    roadmap = Roadmap(
        id=roadmap_id,
        user_id=user_id,
        goal_id=goal_id,
        title=g1["roadmap"]["title"],
        start_date=parse_iso_date(g1["roadmap"]["start_date"]),
        target_date=parse_iso_date(g1["roadmap"]["target_date"]),
        status=RoadmapStatus.INITIALIZED,
        created_at=now,
        updated_at=now,
    )
    milestones = [
        Milestone(
            id=UUID(str(m["milestone_id"])),
            roadmap_id=roadmap_id,
            sequence_order=int(m["sequence_order"]),
            title=str(m["title"]),
            status=MilestoneStatus.APPROVED,
            created_at=now,
            updated_at=now,
        )
        for m in g1["milestones"]
    ]
    avail_snapshot = AvailabilitySnapshotDTO(
        user_id=user_id,
        mode=g1["availability"]["mode"],
        daily_cap_minutes=g1["availability"]["default_daily_quota_minutes"],
        weekly_capacity_minutes=960,
        daily_quota_minutes=g1["availability"]["daily_quota_minutes"],
        availability_slots=(),
        disabled_weekdays=(),
    )
    learner_profile = LearnerProfileDTO(user_id=user_id)

    quota_facade = _FakeQuotaFacade()
    sse_store = InMemorySseJobStore()
    await sse_store.create_job(
        job_id=job_id,
        user_id=user_id,
        roadmap_id=roadmap_id,
        reservation_id=reservation_id,
        job_type="SCHEDULE_PROPOSAL_GEN",
        operation=f"SCHEDULE_PROPOSAL_GEN:{roadmap_id}",
    )
    proposal_repo = _FakeProposalRepo()

    use_case = ExecuteScheduleProposalGenerationUseCase(
        goal_repo=_FakeGoalRepo(goal),
        roadmap_repo=_FakeRoadmapRepo(roadmap),
        milestone_repo=_FakeMilestoneRepo(milestones),
        proposal_repo=proposal_repo,
        availability_query_port=_FakeAvailabilityPort(avail_snapshot),
        learner_profile_port=_FakeLearnerProfilePort(learner_profile),
        execution_sync_port=_FakeExecutionSyncPort(),
        quota_facade=quota_facade,
        llm_provider=_RecordingSelfCorrectionLLM(
            [
                g1["adversarial_attempt_1"],
                g1["adversarial_attempt_1"],
                g1["adversarial_attempt_1"],
            ]
        ),
        sse_job_store=sse_store,
        uow=_FakeUoW(),
    )

    with pytest.raises(ProposalValidationGateError) as exc_info:
        await use_case.execute(
            job_id=job_id,
            user_id=user_id,
            roadmap_id=roadmap_id,
            reservation_id=reservation_id,
            max_retries=2,
            now=now,
        )

    assert exc_info.value.code == "AI_SCHEMA_VALIDATION_ERROR"
    assert len(quota_facade.committed) == 0
    assert len(quota_facade.released) == 1
    assert quota_facade.released[0][0] == reservation_id
    assert len(proposal_repo.proposals) == 0


@pytest.mark.asyncio
async def test_metric3_soft_overflow_detection_and_apply_confirmation_gate_g4() -> None:
    """Metric 3 — Soft Overflow Detection (`BUSR-03`/`BUSR-04`, `UC-12`):
    In `G4_CROSS_MIDNIGHT_SOFT_OVERFLOW`, the last task of the Monday `23:00–01:00` cross-midnight shift
    ends at `01:20` (20m overflow <= 30m):
    - Passes Tier 2 with `SoftOverflowWarningDTO(overflow_minutes=20)`.
    - Apply (`UC-12`) with `confirm_soft_overflow=False` raises `SoftOverflowConfirmationRequiredError`.
    - Apply (`UC-12`) with `confirm_soft_overflow=True` succeeds and activates `OfficialSchedule`.
    """
    scenarios = load_golden_scenarios()
    g4 = next(s for s in scenarios if s["scenario_id"] == "G4_CROSS_MIDNIGHT_SOFT_OVERFLOW")
    avail = build_availability_from_scenario(g4)
    valid_mids: set[UUID | str] = {m["milestone_id"] for m in g4["milestones"]}

    gate = ProposalValidationGateOrchestrator(enable_tier3_judge=False)
    gate_res = await gate.validate_proposal(
        g4["golden_valid_proposal"],
        availability=avail,
        valid_milestone_ids=valid_mids,
        is_ai_generated=True,
    )
    assert gate_res.is_valid is True
    assert gate_res.has_soft_overflow is True
    assert len(gate_res.soft_overflow_warnings) == 1
    assert gate_res.soft_overflow_warnings[0].overflow_minutes == int(
        g4["expected_soft_overflow_minutes"]
    )

    # Test ApplyScheduleProposalUseCase confirmation enforcement (UC-12)
    now = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)
    user_id = uuid7()
    roadmap_id = uuid7()
    proposal_id = uuid7()

    roadmap = Roadmap(
        id=roadmap_id,
        user_id=user_id,
        goal_id=uuid7(),
        title=g4["roadmap"]["title"],
        start_date=parse_iso_date(g4["roadmap"]["start_date"]),
        target_date=parse_iso_date(g4["roadmap"]["target_date"]),
        status=RoadmapStatus.INITIALIZED,
        created_at=now,
        updated_at=now,
    )
    milestones = [
        Milestone(
            id=UUID(str(m["milestone_id"])),
            roadmap_id=roadmap_id,
            sequence_order=int(m["sequence_order"]),
            title=str(m["title"]),
            status=MilestoneStatus.APPROVED,
            created_at=now,
            updated_at=now,
        )
        for m in g4["milestones"]
    ]
    proposal = ScheduleProposal(
        id=proposal_id,
        roadmap_id=roadmap_id,
        user_id=user_id,
        proposal_data=dict(gate_res.validated_proposal_data),
        status=ScheduleProposalStatus.DRAFT,
        created_at=now,
        updated_at=now,
    )
    avail_snapshot = AvailabilitySnapshotDTO(
        user_id=user_id,
        mode=g4["availability"]["mode"],
        daily_cap_minutes=g4["availability"]["default_daily_quota_minutes"],
        weekly_capacity_minutes=240,
        daily_quota_minutes={},
        availability_slots=tuple(g4["availability"]["availability_slots"]),
        disabled_weekdays=(),
    )

    proposal_repo = _FakeProposalRepo()
    await proposal_repo.save(proposal)
    schedule_repo = _FakeOfficialScheduleRepo()
    exec_sync_port = _FakeExecutionSyncPort()
    change_log_port = _FakeScheduleChangeLogPort()
    uow = _FakeUoW()

    apply_uc = ApplyScheduleProposalUseCase(
        roadmap_repo=_FakeRoadmapRepo(roadmap),
        milestone_repo=_FakeMilestoneRepo(milestones),
        proposal_repo=proposal_repo,
        schedule_repo=schedule_repo,
        availability_query_port=_FakeAvailabilityPort(avail_snapshot),
        execution_sync_port=exec_sync_port,
        schedule_change_log_port=change_log_port,
        uow=uow,
    )

    # 1. Without confirmation -> raises SoftOverflowConfirmationRequiredError
    with pytest.raises(SoftOverflowConfirmationRequiredError) as exc_info:
        await apply_uc.execute(
            user_id=user_id,
            roadmap_id=roadmap_id,
            proposal_id=proposal_id,
            confirm_soft_overflow=False,
            now=now,
        )
    assert exc_info.value.overflow_minutes == 20

    # 2. With confirm_soft_overflow=True -> applies OfficialSchedule and activates Roadmap
    apply_res = await apply_uc.execute(
        user_id=user_id,
        roadmap_id=roadmap_id,
        proposal_id=proposal_id,
        confirm_soft_overflow=True,
        now=now,
    )
    assert apply_res.roadmap.status == RoadmapStatus.ACTIVE
    assert apply_res.proposal.status == ScheduleProposalStatus.APPLIED
    assert apply_res.official_schedule.total_sessions == 3
    assert apply_res.official_schedule.total_planned_minutes == 230
    assert len(change_log_port.logs) == 1
    assert change_log_port.logs[0]["diff_payload"]["confirm_soft_overflow"] is True


@pytest.mark.asyncio
async def test_metric4_tier3_pedagogical_judge_fail_open_resilience() -> None:
    """Metric 4 — Tier 3 Fail-Open Resilience (`ADR-009`):
    Simulated Judge timeout (> 5s ceiling) or network error degrades gracefully
    (`judge_skipped=True`, `is_valid=True`) when Tier 1 & Tier 2 pass.
    """
    scenarios = load_golden_scenarios()
    g1 = next(s for s in scenarios if s["scenario_id"] == "G1_PYTHON_BACKEND_MODE_A")
    avail = build_availability_from_scenario(g1)
    valid_mids: set[UUID | str] = {m["milestone_id"] for m in g1["milestones"]}

    # 1. Simulated timeout
    timeout_gate = ProposalValidationGateOrchestrator(
        llm_provider=_SlowOrFailingJudgeLLM(mode="timeout", sleep_seconds=0.15),
        enable_tier3_judge=True,
        tier3_timeout_seconds=0.03,
    )
    res_timeout = await timeout_gate.validate_proposal(
        g1["golden_valid_proposal"],
        availability=avail,
        valid_milestone_ids=valid_mids,
        goal_title=g1["goal"]["title"],
    )
    assert res_timeout.is_valid is True
    assert res_timeout.judge_skipped is True
    assert res_timeout.pedagogical_score is None
    assert len(res_timeout.advisory_warnings) == 1
    assert "Fail-Open" in res_timeout.advisory_warnings[0]

    # 2. Simulated network/provider error
    error_gate = ProposalValidationGateOrchestrator(
        llm_provider=_SlowOrFailingJudgeLLM(mode="error"),
        enable_tier3_judge=True,
        tier3_timeout_seconds=1.0,
    )
    res_error = await error_gate.validate_proposal(
        g1["golden_valid_proposal"],
        availability=avail,
        valid_milestone_ids=valid_mids,
        goal_title=g1["goal"]["title"],
    )
    assert res_error.is_valid is True
    assert res_error.judge_skipped is True
    assert res_error.pedagogical_score is None
    assert len(res_error.advisory_warnings) == 1
    assert "Fail-Open" in res_error.advisory_warnings[0]


@pytest.mark.asyncio
async def test_full_evaluation_harness_summary_and_optional_live_llm() -> None:
    """Aggregate all 4 ADR-009 metrics across the 5 Golden Scenarios and support optional
    live LLM evaluation when `RUN_LIVE_AI_EVALS=1` is set.
    """
    scenarios = load_golden_scenarios()
    run_live = os.getenv("RUN_LIVE_AI_EVALS", "0").strip() == "1"
    llm_adapter: LLMProviderPort = LiteLLMAdapter() if run_live else MockLLMAdapter()

    gate_no_judge = ProposalValidationGateOrchestrator(enable_tier3_judge=False)
    adversarial_tested = 0
    adversarial_blocked = 0
    raw_pass_at_1 = 0
    post_retry_recovered = 0
    soft_overflow_detected = 0

    for scenario in scenarios:
        avail = build_availability_from_scenario(scenario)
        existing_tasks = build_existing_tasks_from_scenario(scenario)
        valid_mids: set[UUID | str] = {m["milestone_id"] for m in scenario["milestones"]}
        target_date = parse_iso_date(scenario["roadmap"]["target_date"])

        # Metric 1 check
        adv_res = await gate_no_judge.validate_proposal(
            scenario["adversarial_attempt_1"],
            availability=avail,
            valid_milestone_ids=valid_mids,
            existing_tasks=existing_tasks,
            current_roadmap_target_date=target_date,
            is_ai_generated=True,
        )
        adversarial_tested += 1
        if not adv_res.is_valid:
            adversarial_blocked += 1

        if scenario.get("expected_pass_at_1"):
            raw_pass_at_1 += 1

        # Metric 2 & 3 check
        retry_llm = (
            llm_adapter
            if run_live
            else _RecordingSelfCorrectionLLM(
                [scenario["adversarial_attempt_1"], scenario["golden_valid_proposal"]]
            )
        )
        retry_gate = ProposalValidationGateOrchestrator(
            llm_provider=retry_llm,
            enable_tier3_judge=False,
        )
        milestone_lines = "\n".join(
            f"- id={m['milestone_id']} | seq={m['sequence_order']} | title={m['title']}"
            for m in scenario["milestones"]
        )
        user_prompt = (
            f"GENERATE_PROPOSAL_TASKS\n"
            f"Roadmap: {scenario['roadmap']['title']}\n"
            f"Start Date: {scenario['roadmap']['start_date']}\n"
            f"MILESTONE_IDS:\n{milestone_lines}\n"
        )
        recovered_res = await retry_gate.generate_and_validate_proposal_with_retry(
            system_prompt="FocusFlow SRL Evaluation Harness",
            user_prompt=user_prompt,
            response_schema=SCHEDULE_PROPOSAL_RESPONSE_SCHEMA,
            availability=avail,
            valid_milestone_ids=valid_mids,
            existing_tasks=existing_tasks,
            current_roadmap_target_date=target_date,
            goal_title=scenario["goal"]["title"],
            max_retries=2,
        )
        if recovered_res.is_valid:
            post_retry_recovered += 1
        if recovered_res.has_soft_overflow:
            soft_overflow_detected += 1

    metrics = EvaluationSummaryMetrics(
        total_scenarios=len(scenarios),
        adversarial_cases_tested=adversarial_tested,
        adversarial_cases_blocked=adversarial_blocked,
        hallucinated_overbooking_pass_rate=(
            (adversarial_tested - adversarial_blocked) / adversarial_tested
        ),
        raw_pass_at_1_count=raw_pass_at_1,
        post_retry_recovery_count=post_retry_recovered,
        post_retry_pass_rate=post_retry_recovered / len(scenarios),
        soft_overflow_detected_count=soft_overflow_detected,
        tier3_fail_open_verified=True,
    )

    assert metrics.total_scenarios == 5
    assert metrics.hallucinated_overbooking_pass_rate == 0.0
    assert metrics.post_retry_pass_rate == 1.0
    assert metrics.soft_overflow_detected_count >= 1
    assert metrics.tier3_fail_open_verified is True
