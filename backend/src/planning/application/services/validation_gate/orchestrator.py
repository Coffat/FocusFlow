"""3-Tier Hybrid Validation Gate Orchestrator & Self-Correction Retry Loop (ADR-009 / T6.1 / T7.3)."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import date
from typing import Any
from uuid import UUID, uuid4

from src.planning.application.services.learning_quality import (
    assess_schedule_feasibility,
    has_operational_quality_review_failure,
    run_dual_quality_critics,
    validate_task_coverage,
)
from src.planning.application.services.roadmap_skills import (
    PROPOSAL_SELF_CORRECTION_PROMPT,
    TASK_DECOMPOSER_SKILL,
    build_planning_prompt_registry,
)
from src.planning.application.services.validation_gate.tier1_schema import (
    _safe_minutes,
    run_tier1_gate,
    validate_ai_milestones_tier1,
)
from src.planning.application.services.validation_gate.tier2_deterministic import (
    run_tier2_gate,
)
from src.planning.application.services.validation_gate.tier3_judge import (
    Tier3JudgeOutcome,
    execute_tier3_pedagogical_judge,
)
from src.planning.domain.exceptions.planning_exceptions import (
    PlanInfeasibleError,
    ProposalValidationGateError,
    SoftOverflowConfirmationRequiredError,
)
from src.planning.domain.models.milestone import Milestone
from src.planning.domain.services.spatio_temporal_engine import (
    SpatioTemporalRuleEngine,
)
from src.planning.domain.services.validation_types import (
    AvailabilityConfigurationDTO,
    ConstraintViolationDTO,
    ScheduleCompletenessStatus,
    SoftOverflowWarningDTO,
    classify_schedule_completeness,
    parse_iso_date,
    safe_parse_iso_date,
    safe_parse_iso_datetime,
)
from src.shared_kernel.application.harness.execution_manager import AIExecutionManager
from src.shared_kernel.application.harness.models import (
    PromptTemplate,
    WorkflowRun,
    WorkflowStepExecution,
    WorkflowType,
)
from src.shared_kernel.application.harness.prompt_registry import build_prompt_audit_metadata
from src.shared_kernel.application.harness.untrusted_context import sanitize_untrusted_text
from src.shared_kernel.application.harness.workflow_port import WorkflowRepositoryPort
from src.shared_kernel.application.llm_port import LLMProviderPort
from src.shared_kernel.config import get_settings

logger = logging.getLogger(__name__)

DECOMPOSER_CALL_TIMEOUT_SECONDS: float = 36.0
PIPELINE_DEADLINE_SECONDS: float = 55.0
MIN_RETRY_REMAINING_SECONDS: float = 12.0
DEFAULT_MAX_RETRIES: int = 2


@dataclass(frozen=True, slots=True)
class ValidationGateResultDTO:
    """Comprehensive validation output from the 3-Tier Hybrid Validation Gate (ADR-009)."""

    is_valid: bool
    violations: tuple[ConstraintViolationDTO, ...] = ()
    soft_overflow_warnings: tuple[SoftOverflowWarningDTO, ...] = ()
    advisory_warnings: tuple[str, ...] = ()
    judge_skipped: bool = False
    judge_status: str = "PASSED"
    pedagogical_score: float | None = None
    is_partial_schedule: bool = False
    scheduled_tasks_count: int = 0
    unscheduled_tasks_count: int = 0
    unscheduled_tasks: tuple[dict[str, Any], ...] = ()
    attempts_used: int = 1
    retry_history: tuple[dict[str, Any], ...] = ()
    validated_proposal_data: dict[str, Any] = field(default_factory=dict)
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_thinking_tokens: int = 0
    feasibility_verdict: str = "VERIFIED_FEASIBLE"
    schedule_completeness_status: ScheduleCompletenessStatus = "FULL"
    unscheduled_diagnostics: tuple[dict[str, Any], ...] = ()

    @property
    def has_soft_overflow(self) -> bool:
        return len(self.soft_overflow_warnings) > 0


def _summarize_milestones(milestones: Sequence[Milestone]) -> str:
    if not milestones:
        return ""
    items = [
        {
            "milestone_id": str(m.id),
            "sequence_order": m.sequence_order,
            "title": m.title,
            "learning_outcomes": list(m.learning_outcomes),
            "completion_criteria": m.completion_criteria or "",
            "estimated_effort_minutes": m.estimated_effort_minutes,
            "required_concepts": list(m.required_concepts),
        }
        for m in sorted(milestones, key=lambda item: item.sequence_order)
    ]
    return json.dumps(items, ensure_ascii=False)


class ProposalValidationGateOrchestrator:
    """3-Tier Hybrid Validation Gate & Self-Correction Retry Loop Orchestrator (UC-12 / ADR-009)."""

    def __init__(
        self,
        llm_provider: LLMProviderPort | None = None,
        *,
        enable_tier3_judge: bool = True,
        tier3_timeout_seconds: float | None = None,
        workflow_repo: WorkflowRepositoryPort | None = None,
        user_id: UUID | None = None,
        goal_id: UUID | None = None,
        roadmap_id: UUID | None = None,
        quota: Any = None,
        reservation_id: UUID | None = None,
    ) -> None:
        self._llm = llm_provider
        self._enable_tier3_judge = enable_tier3_judge
        self._tier3_timeout_seconds = tier3_timeout_seconds
        self._workflow_repo = workflow_repo
        self._user_id = user_id
        self._goal_id = goal_id
        self._roadmap_id = roadmap_id
        self._quota = quota
        self._reservation_id = reservation_id
        self._last_judge_prompt_tokens = 0
        self._last_judge_completion_tokens = 0
        self._last_judge_thinking_tokens = 0

    @staticmethod
    def validate_ai_milestones_tier1(
        milestones_data: Sequence[dict[str, Any]],
    ) -> list[ConstraintViolationDTO]:
        """Validate adaptive Milestone structure and pedagogical minimum fields."""
        return validate_ai_milestones_tier1(milestones_data)

    @classmethod
    def run_tier1_gate(
        cls,
        proposal_data: dict[str, Any],
        *,
        valid_milestone_ids: set[UUID | str] | None = None,
        is_ai_generated: bool = True,
        allow_unscheduled_tasks: bool = False,
    ) -> list[ConstraintViolationDTO]:
        """Execute Tier 1 Syntactic & Bound checks on a ScheduleProposal payload."""
        return run_tier1_gate(
            proposal_data,
            valid_milestone_ids=valid_milestone_ids,
            is_ai_generated=is_ai_generated,
            allow_unscheduled_tasks=allow_unscheduled_tasks,
        )

    @classmethod
    def run_tier2_gate(
        cls,
        proposal_data: dict[str, Any],
        *,
        availability: AvailabilityConfigurationDTO,
        existing_tasks: Sequence[object] = (),
        current_roadmap_target_date: date | None = None,
        allow_unscheduled_tasks: bool = False,
    ) -> tuple[list[ConstraintViolationDTO], list[SoftOverflowWarningDTO]]:
        """Execute Tier 2 Deterministic Spatio-Temporal, Cross-Roadmap EDF & DAG checks."""
        return run_tier2_gate(
            proposal_data,
            availability=availability,
            existing_tasks=existing_tasks,
            current_roadmap_target_date=current_roadmap_target_date,
            allow_unscheduled_tasks=allow_unscheduled_tasks,
        )

    async def run_tier3_pedagogical_judge(
        self,
        proposal_data: dict[str, Any],
        *,
        goal_title: str = "",
        learner_level: str = "",
        milestone_summary: str = "",
        milestones_metadata: Sequence[Any] | None = None,
        remaining_budget_seconds: float | None = None,
        min_judge_remaining_seconds: float | None = None,
        workflow_repo: WorkflowRepositoryPort | None = None,
        step_records_out: list[tuple[WorkflowRun, WorkflowStepExecution]] | None = None,
        thinking_level: str | None = None,
    ) -> tuple[bool, float | None, list[str], str]:
        """Execute Tier 3 Pedagogical LLM-as-a-Judge with configurable timeout & honest status."""
        effective_wf_repo = (
            None
            if step_records_out is not None
            else (workflow_repo if workflow_repo is not None else self._workflow_repo)
        )
        outcome = await execute_tier3_pedagogical_judge(
            self._llm,
            proposal_data,
            enable_tier3_judge=self._enable_tier3_judge,
            tier3_timeout_seconds=self._tier3_timeout_seconds,
            min_judge_remaining_seconds=min_judge_remaining_seconds,
            thinking_level=thinking_level,
            goal_title=goal_title,
            learner_level=learner_level,
            milestone_summary=milestone_summary,
            milestones_metadata=milestones_metadata,
            remaining_budget_seconds=remaining_budget_seconds,
            workflow_repo=effective_wf_repo,
            step_records_out=step_records_out,
            user_id=self._user_id,
            goal_id=self._goal_id,
            roadmap_id=self._roadmap_id,
            quota=self._quota,
        )
        self._last_judge_prompt_tokens = outcome.prompt_tokens
        self._last_judge_completion_tokens = outcome.completion_tokens
        self._last_judge_thinking_tokens = outcome.thinking_tokens
        return (
            outcome.judge_skipped,
            outcome.pedagogical_score,
            outcome.advisory_warnings,
            outcome.judge_status,
        )

    def _build_valid_gate_result(
        self,
        proposal_data: dict[str, Any],
        *,
        soft_warnings: Sequence[SoftOverflowWarningDTO],
        judge_skipped: bool,
        score: float | None,
        advisories: list[str],
        judge_status: str,
        prompt_tokens: int,
        completion_tokens: int,
        thinking_tokens: int,
        attempts_used: int = 1,
        retry_history: tuple[dict[str, Any], ...] = (),
        available_minutes: int | None = None,
        schedule_completeness_status: ScheduleCompletenessStatus | None = None,
        allow_partial_schedule: bool = True,
    ) -> ValidationGateResultDTO:
        raw_tasks_obj = proposal_data.get("tasks")
        raw_tasks = raw_tasks_obj if isinstance(raw_tasks_obj, list) else []
        capacity_overflow = proposal_data.get("_capacity_overflow")
        if available_minutes is not None:
            avail_mins = available_minutes
        elif isinstance(capacity_overflow, dict):
            avail_mins = int(capacity_overflow.get("available_minutes", 0) or 0)
        else:
            avail_mins = max(
                1,
                sum(
                    max(0, _safe_minutes(t.get("estimated_minutes")))
                    for t in raw_tasks
                    if isinstance(t, dict)
                ),
            )
        default_unscheduled_reason = (
            "NO_AVAILABILITY_CONFIGURED: Chưa có khung giờ rảnh khả dụng"
            if avail_mins <= 0
            else "DEADLINE_CAPACITY_EXCEEDED: Không đủ thời gian rảnh trước ngày mục tiêu"
        )

        updated_tasks: list[dict[str, Any]] = []
        scheduled_tasks_count = 0
        unscheduled_list: list[dict[str, Any]] = []
        for task in raw_tasks:
            if not isinstance(task, dict):
                continue
            t_copy = dict(task)
            if safe_parse_iso_date(t_copy.get("scheduled_date")) is not None:
                scheduled_tasks_count += 1
            else:
                if not t_copy.get("unscheduled_reason"):
                    t_copy["unscheduled_reason"] = default_unscheduled_reason
                unscheduled_list.append(t_copy)
            updated_tasks.append(t_copy)

        is_partial = len(unscheduled_list) > 0
        merged_advisories = list(advisories)
        if is_partial:
            partial_msg = (
                f"Lịch học khả thi một phần: Đã xếp lịch {scheduled_tasks_count}/{len(updated_tasks)} nhiệm vụ; "
                f"còn {len(unscheduled_list)} nhiệm vụ trong danh sách chờ ({default_unscheduled_reason})."
            )
            if partial_msg not in merged_advisories:
                merged_advisories.append(partial_msg)
        merged_advisories = list(dict.fromkeys(merged_advisories))

        enriched_data = dict(proposal_data)
        enriched_data["tasks"] = updated_tasks
        enriched_data["soft_overflow_warnings"] = [w.to_dict() for w in soft_warnings]
        enriched_data["judge_status"] = judge_status
        enriched_data["is_partial_schedule"] = is_partial
        enriched_data["scheduled_tasks_count"] = scheduled_tasks_count
        enriched_data["unscheduled_tasks_count"] = len(unscheduled_list)
        enriched_data["unscheduled_tasks"] = unscheduled_list
        feasibility_verdict = str(
            enriched_data.get("feasibility_verdict")
            or ("EXPLICIT_UNSCHEDULABLE" if is_partial else "VERIFIED_FEASIBLE")
        )
        raw_diags = enriched_data.get("unscheduled_diagnostics")
        unscheduled_diags: list[dict[str, Any]] = (
            [dict(d) for d in raw_diags if isinstance(d, dict)]
            if isinstance(raw_diags, list)
            else []
        )
        resolved_completeness = schedule_completeness_status
        if resolved_completeness is None:
            feasibility_assessment = assess_schedule_feasibility(
                updated_tasks,
                available_minutes=avail_mins,
            )
            raw_blocks = enriched_data.get("schedule_blocks")
            has_blocks = isinstance(raw_blocks, list) and any(
                isinstance(b, dict) for b in raw_blocks
            )
            all_scheduled_have_times = scheduled_tasks_count > 0 and all(
                safe_parse_iso_datetime(t.get("scheduled_start")) is not None
                and safe_parse_iso_datetime(t.get("scheduled_end")) is not None
                for t in updated_tasks
                if safe_parse_iso_date(t.get("scheduled_date")) is not None
            )
            resolved_completeness = classify_schedule_completeness(
                total_tasks=len(updated_tasks),
                scheduled_tasks_count=scheduled_tasks_count,
                unscheduled_tasks_count=len(unscheduled_list),
                available_minutes=avail_mins,
                schedulable_ratio=feasibility_assessment.schedulable_ratio,
                feasibility_verdict=feasibility_verdict,
                has_schedule_blocks=has_blocks,
                all_scheduled_have_block_times=all_scheduled_have_times,
                allow_partial_schedule=allow_partial_schedule,
            )
        enriched_data["feasibility_verdict"] = feasibility_verdict
        enriched_data["schedule_completeness_status"] = resolved_completeness
        enriched_data["unscheduled_diagnostics"] = unscheduled_diags
        if merged_advisories:
            enriched_data["advisory_warnings"] = merged_advisories
        if judge_skipped:
            enriched_data["judge_skipped"] = True

        return ValidationGateResultDTO(
            is_valid=True,
            violations=(),
            soft_overflow_warnings=tuple(soft_warnings),
            advisory_warnings=tuple(merged_advisories),
            judge_skipped=judge_skipped,
            judge_status=judge_status,
            pedagogical_score=score,
            is_partial_schedule=is_partial,
            scheduled_tasks_count=scheduled_tasks_count,
            unscheduled_tasks_count=len(unscheduled_list),
            unscheduled_tasks=tuple(unscheduled_list),
            attempts_used=attempts_used,
            retry_history=retry_history,
            validated_proposal_data=enriched_data,
            total_prompt_tokens=prompt_tokens,
            total_completion_tokens=completion_tokens,
            total_thinking_tokens=thinking_tokens,
            feasibility_verdict=feasibility_verdict,
            schedule_completeness_status=resolved_completeness,
            unscheduled_diagnostics=tuple(unscheduled_diags),
        )

    async def validate_proposal(
        self,
        proposal_data: dict[str, Any],
        *,
        availability: AvailabilityConfigurationDTO,
        valid_milestone_ids: set[UUID | str] | None = None,
        existing_tasks: Sequence[object] = (),
        current_roadmap_target_date: date | None = None,
        is_ai_generated: bool = True,
        require_soft_overflow_confirmation: bool = False,
        confirm_soft_overflow: bool = False,
        goal_title: str = "",
        learner_level: str = "",
        milestone_summary: str = "",
        milestones_metadata: Sequence[Any] | None = None,
        allow_unscheduled_tasks: bool = False,
        remaining_budget_seconds: float | None = None,
        precomputed_judge_outcome: Tier3JudgeOutcome | None = None,
    ) -> ValidationGateResultDTO:
        """Run all 3 Tiers on a single proposal payload."""
        self._last_judge_prompt_tokens = 0
        self._last_judge_completion_tokens = 0
        self._last_judge_thinking_tokens = 0
        tier1_violations = self.run_tier1_gate(
            proposal_data,
            valid_milestone_ids=valid_milestone_ids,
            is_ai_generated=is_ai_generated,
            allow_unscheduled_tasks=allow_unscheduled_tasks,
        )
        tier2_violations, soft_warnings = self.run_tier2_gate(
            proposal_data,
            availability=availability,
            existing_tasks=existing_tasks,
            current_roadmap_target_date=current_roadmap_target_date,
            allow_unscheduled_tasks=allow_unscheduled_tasks,
        )

        all_violations = [*tier1_violations, *tier2_violations]
        if all_violations:
            return ValidationGateResultDTO(
                is_valid=False,
                violations=tuple(all_violations),
                soft_overflow_warnings=tuple(soft_warnings),
                validated_proposal_data=proposal_data,
                schedule_completeness_status="UNDETERMINED",
            )

        raw_tasks_obj = proposal_data.get("tasks")
        dict_tasks = (
            [t for t in raw_tasks_obj if isinstance(t, dict)]
            if isinstance(raw_tasks_obj, list)
            else []
        )
        scheduled_dates = [
            d for t in dict_tasks if (d := safe_parse_iso_date(t.get("scheduled_date"))) is not None
        ]
        if allow_unscheduled_tasks and not scheduled_dates:
            return ValidationGateResultDTO(
                is_valid=False,
                violations=(
                    ConstraintViolationDTO(
                        task_index=None,
                        field="tasks",
                        rule_code="NO_SCHEDULED_TASKS",
                        expected_bound="At least 1 scheduled task",
                        actual_value="0 scheduled tasks",
                        suggested_fix="Cần ít nhất một nhiệm vụ được xếp lịch trước khi lưu đề xuất.",
                    ),
                ),
                soft_overflow_warnings=tuple(soft_warnings),
                validated_proposal_data=proposal_data,
                schedule_completeness_status="INFEASIBLE",
            )

        avail_mins_for_result: int | None = None
        if allow_unscheduled_tasks:
            effective_start = (
                min(scheduled_dates)
                if scheduled_dates
                else (current_roadmap_target_date or date.today())
            )
            avail_mins_for_result = SpatioTemporalRuleEngine.calculate_available_capacity_minutes(
                availability,
                start_date=effective_start,
                target_date=current_roadmap_target_date,
                existing_tasks=existing_tasks,
            )
            feasibility_assessment = assess_schedule_feasibility(
                dict_tasks,
                available_minutes=avail_mins_for_result,
            )
            if avail_mins_for_result <= 0 or feasibility_assessment.schedulable_ratio < 0.25:
                return ValidationGateResultDTO(
                    is_valid=False,
                    violations=(
                        ConstraintViolationDTO(
                            task_index=None,
                            field="tasks",
                            rule_code="PLAN_INFEASIBLE",
                            expected_bound="available_minutes > 0 and schedulable_ratio >= 0.25",
                            actual_value=(
                                f"avail={avail_mins_for_result}, "
                                f"ratio={feasibility_assessment.schedulable_ratio}"
                            ),
                            suggested_fix="Gia hạn ngày mục tiêu hoặc tăng thời gian rảnh.",
                        ),
                    ),
                    soft_overflow_warnings=tuple(soft_warnings),
                    validated_proposal_data=proposal_data,
                    schedule_completeness_status="INFEASIBLE",
                )

        if require_soft_overflow_confirmation and soft_warnings and not confirm_soft_overflow:
            total_overflow = sum(w.overflow_minutes for w in soft_warnings)
            raise SoftOverflowConfirmationRequiredError(overflow_minutes=total_overflow)

        if precomputed_judge_outcome is not None:
            judge_skipped = precomputed_judge_outcome.judge_skipped
            score = precomputed_judge_outcome.pedagogical_score
            advisories = list(precomputed_judge_outcome.advisory_warnings)
            judge_status = precomputed_judge_outcome.judge_status
            self._last_judge_prompt_tokens = precomputed_judge_outcome.prompt_tokens
            self._last_judge_completion_tokens = precomputed_judge_outcome.completion_tokens
            self._last_judge_thinking_tokens = precomputed_judge_outcome.thinking_tokens
        else:
            judge_skipped, score, advisories, judge_status = await self.run_tier3_pedagogical_judge(
                proposal_data,
                goal_title=goal_title,
                learner_level=learner_level,
                milestone_summary=milestone_summary,
                milestones_metadata=milestones_metadata,
                remaining_budget_seconds=remaining_budget_seconds,
            )

        return self._build_valid_gate_result(
            proposal_data,
            soft_warnings=soft_warnings,
            judge_skipped=judge_skipped,
            score=score,
            advisories=advisories,
            judge_status=judge_status,
            prompt_tokens=self._last_judge_prompt_tokens,
            completion_tokens=self._last_judge_completion_tokens,
            thinking_tokens=self._last_judge_thinking_tokens,
            available_minutes=avail_mins_for_result,
            allow_partial_schedule=allow_unscheduled_tasks
            or len(scheduled_dates) == len(dict_tasks),
        )

    @staticmethod
    def build_self_correction_prompt(
        original_user_prompt: str,
        violations: Sequence[ConstraintViolationDTO],
        attempt_number: int,
    ) -> str:
        """Build full-regeneration self-correction prompt listing all constraint violations (T6.1)."""
        retry_tpl = build_planning_prompt_registry().latest(
            PROPOSAL_SELF_CORRECTION_PROMPT.prompt_id
        )
        lines = [
            original_user_prompt,
            "",
            f"[SELF-CORRECTION RETRY ATTEMPT #{attempt_number}]",
            retry_tpl.system_template,
            "Danh sách toàn bộ vi phạm cần khắc phục triệt để khi sinh lại toàn bộ danh sách:",
        ]
        for idx, v in enumerate(violations, start=1):
            task_ref = f"task_index={v.task_index}" if v.task_index is not None else "toàn cục"
            lines.append(
                f"{idx}. [{v.rule_code}] ({task_ref}, trường '{v.field}'): "
                f"Giá trị hiện tại = {v.actual_value} | Yêu cầu = {v.expected_bound} | "
                f"Cách sửa = {v.suggested_fix}"
            )
        lines.append(
            "Yêu cầu hành động: Sinh lại TOÀN BỘ danh sách hợp lệ theo đúng schema và khắc phục tất cả các lỗi đã liệt kê ở trên."
        )
        return "\n".join(lines)

    async def generate_and_validate_proposal_with_retry(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: dict[str, Any] | type[Any] | None,
        availability: AvailabilityConfigurationDTO,
        valid_milestone_ids: set[UUID | str] | None = None,
        existing_tasks: Sequence[object] = (),
        current_roadmap_target_date: date | None = None,
        goal_title: str = "",
        learner_level: str = "",
        milestone_summary: str = "",
        max_retries: int = DEFAULT_MAX_RETRIES,
        on_retry_callback: Callable[[int, Sequence[ConstraintViolationDTO]], Any] | None = None,
        start_date: date | None = None,
        milestone_order_map: dict[str, int] | None = None,
        tools: list[Any] | None = None,
        tool_executor: Any | None = None,
        max_tool_calls: int = 4,
        thinking_level: str | None = None,
        deterministic_allocation: bool = False,
        preferred_session_minutes: int = 60,
        estimation_bias_beta: float = 1.0,
        peak_productivity_slots: Sequence[str] = (),
        daily_workload_cap_minutes: int | None = None,
        buffer_minutes_per_week: int = 0,
        allow_partial_schedule: bool = True,
        milestones: Sequence[Milestone] = (),
        resource_resolver: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
        prompt_template: PromptTemplate | None = None,
    ) -> ValidationGateResultDTO:
        """Invoke LLMProviderPort via AIExecutionManager and run the 3-Tier Validation Gate with up to `max_retries` (2) self-correction loops."""
        if self._llm is None:
            raise ValueError(
                "LLMProviderPort is required for generate_and_validate_proposal_with_retry."
            )
        llm_provider: LLMProviderPort = self._llm

        registry = build_planning_prompt_registry()
        effective_tpl = prompt_template or registry.latest(TASK_DECOMPOSER_SKILL.skill_id)
        retry_tpl = registry.latest(PROPOSAL_SELF_CORRECTION_PROMPT.prompt_id)
        effective_milestone_summary = milestone_summary or _summarize_milestones(milestones)

        current_prompt = user_prompt
        total_prompt_tokens = 0
        total_completion_tokens = 0
        total_thinking_tokens = 0
        retry_history: list[dict[str, Any]] = []
        last_violations: list[ConstraintViolationDTO] = []
        last_infeasible_ratio: float | None = None
        pedagogical_retry_used = False

        settings = get_settings()
        min_retry_remaining = float(settings.ai_min_retry_remaining_seconds)
        max_attempts = max(1, int(max_retries) + 1)
        pipeline_deadline = asyncio.get_running_loop().time() + float(
            settings.ai_sse_pipeline_timeout_seconds
        )
        effective_schema: dict[str, Any] | type[Any] = (
            response_schema if response_schema is not None else {"type": "object"}
        )

        for attempt in range(1, max_attempts + 1):
            remaining_seconds = pipeline_deadline - asyncio.get_running_loop().time()
            if remaining_seconds <= 0:
                raise TimeoutError("Task decomposition exceeded pipeline timeout budget")

            decomposer_timeout = min(
                float(settings.ai_task_decomposer_timeout_seconds), remaining_seconds
            )
            exec_mgr = AIExecutionManager(
                provider=self._llm,
                quota=self._quota,
                manage_quota=False,
                max_retries=0,
                timeout_seconds=decomposer_timeout,
                tool_call_timeout_seconds=float(settings.ai_tool_call_timeout_seconds),
                workflow_repo=self._workflow_repo,
            )
            step_snapshot = (
                {"retry_prompt_ref": retry_tpl.prompt_ref, **build_prompt_audit_metadata(retry_tpl)}
                if attempt > 1
                else {}
            )
            effective_thinking_level = (
                thinking_level or ""
            ).strip() or TASK_DECOMPOSER_SKILL.thinking_level
            exec_res = await exec_mgr.execute(
                user_id=self._user_id or uuid4(),
                operation_type="TASK_DECOMPOSITION",
                system_prompt=system_prompt,
                user_prompt=current_prompt,
                response_schema=effective_schema,
                model_name=getattr(self._llm, "model_identifier", "gemini-3.8-flash"),
                tools=tools if attempt == 1 else None,
                tool_executor=tool_executor if attempt == 1 else None,
                max_tool_calls=max_tool_calls if (tools is not None and attempt == 1) else 0,
                thinking_level=effective_thinking_level,
                workflow_type=WorkflowType.SCHEDULE_GENERATION,
                step_name="TASK_DECOMPOSER",
                step_order=attempt,
                goal_id=self._goal_id,
                roadmap_id=self._roadmap_id,
                context_snapshot=step_snapshot,
                prompt_template=effective_tpl,
                existing_reservation_id=self._reservation_id,
                commit_on_success=False,
                release_on_failure=False,
            )
            raw_proposal = exec_res.value if isinstance(exec_res.value, dict) else {}
            total_prompt_tokens += int(exec_res.prompt_tokens or 0)
            total_completion_tokens += int(exec_res.completion_tokens or 0)
            total_thinking_tokens += int(exec_res.thinking_tokens or 0)

            if resource_resolver is not None and isinstance(raw_proposal, dict):
                raw_proposal = resource_resolver(raw_proposal)

            raw_tasks = raw_proposal.get("tasks") if isinstance(raw_proposal, dict) else None
            if isinstance(raw_proposal, dict) and isinstance(raw_tasks, list) and milestones:
                coverage_violations = validate_task_coverage(raw_tasks, milestones)
                if coverage_violations:
                    last_violations = coverage_violations
                    retry_history.append(
                        {
                            "attempt": attempt,
                            "violations": [v.to_dict() for v in coverage_violations],
                        }
                    )
                    remaining_for_retry = pipeline_deadline - asyncio.get_running_loop().time()
                    if attempt < max_attempts and remaining_for_retry >= min_retry_remaining:
                        if on_retry_callback is not None:
                            maybe_coro = on_retry_callback(attempt, last_violations)
                            if asyncio.iscoroutine(maybe_coro):
                                await maybe_coro
                        current_prompt = self.build_self_correction_prompt(
                            user_prompt,
                            last_violations,
                            attempt_number=attempt,
                        )
                        continue
                    break

            hard_solver_v2_enabled = bool(
                getattr(settings, "spatio_temporal_v2_hard_solver_enabled", True)
            )
            soft_pacing_v2_enabled = bool(
                getattr(settings, "spatio_temporal_v2_soft_pacing_enabled", True)
            )
            soft_end_buffer_ratio = float(
                getattr(settings, "spatio_temporal_soft_end_buffer_ratio", 0.12)
            )
            soft_max_consecutive_days = int(
                getattr(settings, "spatio_temporal_soft_max_consecutive_days", 5)
            )
            if deterministic_allocation and isinstance(raw_tasks, list):
                unscheduled_tasks = [
                    {
                        k: v
                        for k, v in task.items()
                        if k
                        not in {
                            "scheduled_date",
                            "scheduled_start",
                            "scheduled_end",
                            "start_time",
                            "end_time",
                        }
                    }
                    if isinstance(task, dict)
                    else task
                    for task in raw_tasks
                ]
                raw_deps = (
                    raw_proposal.get("dependencies")
                    if isinstance(raw_proposal.get("dependencies"), list)
                    else []
                )
                if hard_solver_v2_enabled:
                    alloc_res = SpatioTemporalRuleEngine.allocate_task_sessions_with_diagnostics(
                        unscheduled_tasks,
                        availability,
                        start_date=start_date or date.today(),
                        target_date=current_roadmap_target_date,
                        dependencies=raw_deps,
                        existing_tasks=existing_tasks,
                        milestone_order_map=milestone_order_map,
                        preferred_session_minutes=preferred_session_minutes,
                        estimation_bias_beta=estimation_bias_beta,
                        peak_productivity_slots=peak_productivity_slots,
                        daily_workload_cap_minutes=daily_workload_cap_minutes,
                        buffer_minutes_per_week=buffer_minutes_per_week,
                        soft_pacing_v2_enabled=soft_pacing_v2_enabled,
                        end_buffer_ratio=soft_end_buffer_ratio,
                        max_consecutive_study_days=soft_max_consecutive_days,
                    )
                    allocated_tasks = alloc_res.tasks
                    schedule_blocks = alloc_res.schedule_blocks
                    raw_proposal = {
                        **raw_proposal,
                        "tasks": allocated_tasks,
                        "schedule_blocks": schedule_blocks,
                        "feasibility_verdict": alloc_res.feasibility_verdict,
                        "unscheduled_diagnostics": [
                            d.to_dict() for d in alloc_res.unscheduled_diagnostics
                        ],
                    }
                else:
                    allocated_tasks, schedule_blocks = (
                        SpatioTemporalRuleEngine.allocate_task_sessions(
                            unscheduled_tasks,
                            availability,
                            start_date=start_date or date.today(),
                            target_date=current_roadmap_target_date,
                            dependencies=raw_deps,
                            existing_tasks=existing_tasks,
                            milestone_order_map=milestone_order_map,
                            preferred_session_minutes=preferred_session_minutes,
                            estimation_bias_beta=estimation_bias_beta,
                            peak_productivity_slots=peak_productivity_slots,
                            daily_workload_cap_minutes=daily_workload_cap_minutes,
                            buffer_minutes_per_week=buffer_minutes_per_week,
                            hard_solver_v2_enabled=False,
                        )
                    )
                    raw_proposal = {
                        **raw_proposal,
                        "tasks": allocated_tasks,
                        "schedule_blocks": schedule_blocks,
                    }
            elif isinstance(raw_tasks, list) and any(
                isinstance(t, dict) and parse_iso_date(t.get("scheduled_date")) is None
                for t in raw_tasks
            ):
                raw_deps = raw_proposal.get("dependencies", [])
                allocated_tasks = SpatioTemporalRuleEngine.allocate_tasks_to_availability(
                    raw_tasks,
                    availability,
                    start_date=start_date or date.today(),
                    target_date=current_roadmap_target_date,
                    dependencies=raw_deps if isinstance(raw_deps, list) else [],
                    existing_tasks=existing_tasks,
                    milestone_order_map=milestone_order_map,
                    daily_workload_cap_minutes=daily_workload_cap_minutes,
                    hard_solver_v2_enabled=hard_solver_v2_enabled,
                )
                raw_proposal = {**raw_proposal, "tasks": allocated_tasks}
            else:
                allocated_tasks = raw_tasks if isinstance(raw_tasks, list) else []

            has_unscheduled = any(
                isinstance(t, dict) and safe_parse_iso_date(t.get("scheduled_date")) is None
                for t in allocated_tasks
            )
            allow_unscheduled_in_attempt = False
            attempt_avail_mins: int | None = None
            attempt_completeness: ScheduleCompletenessStatus | None = None
            if has_unscheduled and isinstance(raw_proposal, dict):
                avail_mins = SpatioTemporalRuleEngine.calculate_available_capacity_minutes(
                    availability,
                    start_date=start_date or date.today(),
                    target_date=current_roadmap_target_date,
                    existing_tasks=existing_tasks,
                    daily_workload_cap_minutes=daily_workload_cap_minutes,
                )
                attempt_avail_mins = avail_mins
                req_mins = sum(
                    _safe_minutes(t.get("estimated_minutes"))
                    for t in allocated_tasks
                    if isinstance(t, dict)
                )
                raw_proposal = {
                    **raw_proposal,
                    "_capacity_overflow": {
                        "available_minutes": avail_mins,
                        "required_minutes": req_mins,
                        "target_date": (
                            current_roadmap_target_date.isoformat()
                            if current_roadmap_target_date is not None
                            else "N/A"
                        ),
                    },
                }
                dict_tasks = [t for t in allocated_tasks if isinstance(t, dict)]
                scheduled_count = sum(
                    1
                    for t in dict_tasks
                    if safe_parse_iso_date(t.get("scheduled_date")) is not None
                )
                unscheduled_count = len(dict_tasks) - scheduled_count
                feasibility_assessment = assess_schedule_feasibility(
                    dict_tasks,
                    available_minutes=avail_mins,
                )
                raw_diags = raw_proposal.get("unscheduled_diagnostics")
                unscheduled_reason_codes = {
                    str(d.get("reason_code"))
                    for d in (raw_diags if isinstance(raw_diags, list) else [])
                    if isinstance(d, dict) and d.get("reason_code")
                }
                raw_verdict = raw_proposal.get("feasibility_verdict")
                raw_blocks = raw_proposal.get("schedule_blocks")
                has_blocks = isinstance(raw_blocks, list) and any(
                    isinstance(b, dict) for b in raw_blocks
                )
                all_scheduled_have_times = scheduled_count > 0 and all(
                    safe_parse_iso_datetime(t.get("scheduled_start")) is not None
                    and safe_parse_iso_datetime(t.get("scheduled_end")) is not None
                    for t in dict_tasks
                    if safe_parse_iso_date(t.get("scheduled_date")) is not None
                )
                attempt_completeness = classify_schedule_completeness(
                    total_tasks=len(dict_tasks),
                    scheduled_tasks_count=scheduled_count,
                    unscheduled_tasks_count=unscheduled_count,
                    available_minutes=avail_mins,
                    schedulable_ratio=feasibility_assessment.schedulable_ratio,
                    feasibility_verdict=str(raw_verdict) if raw_verdict is not None else None,
                    has_schedule_blocks=has_blocks,
                    all_scheduled_have_block_times=all_scheduled_have_times,
                    allow_partial_schedule=allow_partial_schedule,
                )

                hard_impossibility_codes = {
                    "TASK_EXCEEDS_CONTINUOUS_SLOT",
                    "CRITICAL_PATH_EXCEEDED_WINDOW",
                    "CALENDAR_CONFLICT_SATURATION",
                }
                has_hard_impossibility_code = bool(
                    unscheduled_reason_codes & hard_impossibility_codes
                )
                is_hard_deterministic_impossibility = avail_mins <= 0 or (
                    raw_verdict == "EXPLICIT_UNSCHEDULABLE"
                    and (has_hard_impossibility_code or scheduled_count == 0)
                )

                remaining_for_retry = pipeline_deadline - asyncio.get_running_loop().time()
                can_condense_retry = (
                    not is_hard_deterministic_impossibility
                    and attempt == 1
                    and attempt < max_attempts
                    and remaining_for_retry >= min_retry_remaining
                    and avail_mins > 0
                    and req_mins <= int(avail_mins * 1.30)
                )

                if attempt_completeness == "INFEASIBLE":
                    allow_unscheduled_in_attempt = False
                    last_infeasible_ratio = feasibility_assessment.schedulable_ratio
                    if not can_condense_retry:
                        if allow_partial_schedule:
                            raise PlanInfeasibleError(feasibility_assessment.schedulable_ratio)
                        raise ProposalValidationGateError(
                            message=(
                                "Đề xuất lịch học không khả thi với quỹ thời gian rảnh hiện tại "
                                f"(tỉ lệ xếp lịch {feasibility_assessment.schedulable_ratio:.0%})."
                            ),
                            code="AI_SCHEMA_VALIDATION_ERROR",
                            violations=[
                                {
                                    "task_index": None,
                                    "field": "tasks",
                                    "rule_code": "PLAN_INFEASIBLE",
                                    "expected_bound": "schedulable_ratio >= 0.25 and available_minutes > 0",
                                    "actual_value": (
                                        f"ratio={feasibility_assessment.schedulable_ratio}, "
                                        f"avail={avail_mins}"
                                    ),
                                    "suggested_fix": "Gia hạn ngày mục tiêu hoặc tăng thời gian rảnh.",
                                }
                            ],
                        )
                elif attempt_completeness == "UNDETERMINED":
                    allow_unscheduled_in_attempt = False
                    last_infeasible_ratio = None
                elif attempt_completeness == "PARTIAL":
                    last_infeasible_ratio = None
                    if can_condense_retry:
                        allow_unscheduled_in_attempt = False
                    else:
                        allow_unscheduled_in_attempt = True
            else:
                last_infeasible_ratio = None

            # Tier 1 & Tier 2 deterministic gates run BEFORE parallel Critic + Tier 3 Judge.
            tier1_violations = self.run_tier1_gate(
                raw_proposal,
                valid_milestone_ids=valid_milestone_ids,
                is_ai_generated=True,
                allow_unscheduled_tasks=allow_unscheduled_in_attempt,
            )
            tier2_violations, soft_warnings = self.run_tier2_gate(
                raw_proposal,
                availability=availability,
                existing_tasks=existing_tasks,
                current_roadmap_target_date=current_roadmap_target_date,
                allow_unscheduled_tasks=allow_unscheduled_in_attempt,
            )
            deterministic_violations = [*tier1_violations, *tier2_violations]
            if deterministic_violations:
                last_violations = deterministic_violations
                retry_history.append(
                    {
                        "attempt": attempt,
                        "violations": [v.to_dict() for v in last_violations],
                    }
                )
                remaining_for_retry = pipeline_deadline - asyncio.get_running_loop().time()
                if attempt < max_attempts and remaining_for_retry >= min_retry_remaining:
                    if on_retry_callback is not None:
                        maybe_coro = on_retry_callback(attempt, last_violations)
                        if asyncio.iscoroutine(maybe_coro):
                            await maybe_coro
                    current_prompt = self.build_self_correction_prompt(
                        user_prompt,
                        last_violations,
                        attempt_number=attempt,
                    )
                    continue
                break

            # Proposal passed Tier 1 & Tier 2: run Dual Critics + Tier 3 Judge in parallel with remaining budget.
            remaining_budget = max(0.0, pipeline_deadline - asyncio.get_running_loop().time())
            should_run_critics = bool(
                isinstance(raw_proposal, dict) and isinstance(raw_tasks, list) and milestones
            )
            min_critic_remaining = float(getattr(settings, "ai_min_critic_remaining_seconds", 6.0))
            min_judge_remaining = float(getattr(settings, "ai_min_judge_remaining_seconds", 3.0))
            critics_budget_ok = should_run_critics and remaining_budget >= min_critic_remaining

            critic_advisory_warnings: list[str] = []
            quality_violations: list[ConstraintViolationDTO] = []
            quality_reports: list[dict[str, Any]] = []
            critic_step_records: list[tuple[WorkflowRun, WorkflowStepExecution]] = []
            judge_step_records: list[tuple[WorkflowRun, WorkflowStepExecution]] = []

            if should_run_critics and not critics_budget_ok:
                logger.warning(
                    "proposal_quality_critic_skipped_low_budget",
                    extra={
                        "roadmap_id": str(self._roadmap_id) if self._roadmap_id else None,
                        "remaining_seconds": round(remaining_budget, 2),
                        "min_required_seconds": min_critic_remaining,
                    },
                )
                critic_advisory_warnings.append(
                    "Ngân sách thời gian còn lại không đủ cho AI Critic — đã bỏ qua bước Critic và giữ kiểm định Tier 1/2."
                )
                quality_reports = [
                    {
                        "critic": "QUALITY_CRITIC",
                        "status": "SKIPPED_LOW_BUDGET",
                        "issues": [],
                    }
                ]

            async def _run_critics_coro() -> tuple[
                list[ConstraintViolationDTO], list[dict[str, Any]], int, int, int, bool
            ]:
                critic_timeout = min(
                    float(settings.ai_quality_critic_timeout_seconds), remaining_budget
                )
                arbiter_timeout = min(
                    float(settings.ai_quality_arbiter_timeout_seconds), remaining_budget
                )
                critic_tokens: dict[str, int] = {}
                try:
                    c_violations, c_reports, c_p, c_c = await asyncio.wait_for(
                        run_dual_quality_critics(
                            llm_provider,
                            stage="TASK_DECOMPOSITION",
                            payload=raw_proposal,
                            context=f"Goal: {sanitize_untrusted_text(goal_title)}",
                            learner_level=learner_level,
                            milestone_summary=effective_milestone_summary,
                            timeout_seconds=critic_timeout,
                            arbiter_timeout_seconds=arbiter_timeout,
                            remaining_budget_seconds=remaining_budget,
                            workflow_repo=None,
                            step_records_out=critic_step_records,
                            user_id=self._user_id,
                            goal_id=self._goal_id,
                            roadmap_id=self._roadmap_id,
                            workflow_type=WorkflowType.SCHEDULE_GENERATION,
                            token_accumulator=critic_tokens,
                            quota=self._quota,
                        ),
                        timeout=remaining_budget,
                    )
                    return (
                        c_violations,
                        c_reports,
                        c_p,
                        c_c,
                        int(critic_tokens.get("thinking_tokens", 0)),
                        False,
                    )
                except TimeoutError:
                    return (
                        [],
                        [
                            {
                                "critic": "QUALITY_CRITIC",
                                "status": "SKIPPED_LOW_BUDGET",
                                "issues": [],
                            }
                        ],
                        0,
                        0,
                        0,
                        True,
                    )

            async def _run_judge_coro() -> Tier3JudgeOutcome:
                dynamic_judge_cap = min(
                    float(
                        self._tier3_timeout_seconds
                        if self._tier3_timeout_seconds is not None
                        else getattr(settings, "tier3_judge_timeout_seconds", 12.0)
                    ),
                    remaining_budget,
                )
                return await execute_tier3_pedagogical_judge(
                    self._llm,
                    raw_proposal,
                    enable_tier3_judge=self._enable_tier3_judge,
                    tier3_timeout_seconds=dynamic_judge_cap,
                    min_judge_remaining_seconds=min_judge_remaining,
                    goal_title=goal_title,
                    learner_level=learner_level,
                    milestone_summary=effective_milestone_summary,
                    milestones_metadata=milestones,
                    remaining_budget_seconds=remaining_budget,
                    workflow_repo=None,
                    step_records_out=judge_step_records,
                    user_id=self._user_id,
                    goal_id=self._goal_id,
                    roadmap_id=self._roadmap_id,
                    quota=self._quota,
                )

            critic_result: (
                tuple[list[ConstraintViolationDTO], list[dict[str, Any]], int, int, int, bool]
                | None
            ) = None
            if critics_budget_ok and self._enable_tier3_judge:
                # Run Dual Critics + Tier 3 Judge concurrently with workflow_repo=None to prevent
                # concurrent AsyncSession flushes; records are persisted sequentially below.
                critic_result, judge_outcome = await asyncio.gather(
                    _run_critics_coro(),
                    _run_judge_coro(),
                )
            elif critics_budget_ok:
                critic_result = await _run_critics_coro()
                judge_outcome = await _run_judge_coro()
            else:
                judge_outcome = await _run_judge_coro()

            if self._workflow_repo is not None:
                persisted_runs: set[UUID] = set()
                for run, step in [*critic_step_records, *judge_step_records]:
                    if run.id not in persisted_runs:
                        await self._workflow_repo.add_run(run)
                        persisted_runs.add(run.id)
                    await self._workflow_repo.add_step(step)

            if critic_result is not None:
                (
                    critic_violations,
                    quality_reports,
                    critic_p,
                    critic_c,
                    critic_t,
                    critic_timed_out,
                ) = critic_result
                total_prompt_tokens += critic_p
                total_completion_tokens += critic_c
                total_thinking_tokens += critic_t
                if critic_timed_out:
                    logger.warning(
                        "proposal_quality_critic_timeout_skipped",
                        extra={"roadmap_id": str(self._roadmap_id) if self._roadmap_id else None},
                    )
                    critic_advisory_warnings.append(
                        "AI Critic hết ngân sách thời gian — đã bỏ qua bước Critic và giữ kiểm định Tier 1/2."
                    )
                else:
                    if has_operational_quality_review_failure(critic_violations):
                        logger.warning(
                            "proposal_quality_critic_degraded",
                            extra={
                                "roadmap_id": str(self._roadmap_id) if self._roadmap_id else None
                            },
                        )
                        critic_advisory_warnings.append(
                            "AI Critic tạm thời quá thời gian chờ — đã tiếp tục kiểm định Tier 1/2."
                        )
                        critic_violations = [
                            v
                            for v in critic_violations
                            if v.rule_code
                            not in {
                                "QUALITY_CRITIC_UNAVAILABLE",
                                "QUALITY_ARBITER_UNAVAILABLE",
                            }
                        ]
                    quality_violations.extend(critic_violations)

            if should_run_critics and isinstance(raw_proposal, dict):
                raw_proposal = {**raw_proposal, "quality_reviews": quality_reports}

            self._last_judge_prompt_tokens = judge_outcome.prompt_tokens
            self._last_judge_completion_tokens = judge_outcome.completion_tokens
            self._last_judge_thinking_tokens = judge_outcome.thinking_tokens
            total_prompt_tokens += judge_outcome.prompt_tokens
            total_completion_tokens += judge_outcome.completion_tokens
            total_thinking_tokens += judge_outcome.thinking_tokens

            if quality_violations:
                last_violations = quality_violations
                retry_history.append(
                    {
                        "attempt": attempt,
                        "violations": [v.to_dict() for v in quality_violations],
                    }
                )
                remaining_for_retry = pipeline_deadline - asyncio.get_running_loop().time()
                if attempt < max_attempts and remaining_for_retry >= min_retry_remaining:
                    if on_retry_callback is not None:
                        maybe_coro = on_retry_callback(attempt, last_violations)
                        if asyncio.iscoroutine(maybe_coro):
                            await maybe_coro
                    current_prompt = self.build_self_correction_prompt(
                        user_prompt,
                        last_violations,
                        attempt_number=attempt,
                    )
                    continue
                break

            remaining_for_retry = pipeline_deadline - asyncio.get_running_loop().time()
            if (
                judge_outcome.judge_status == "NEEDS_REVIEW"
                and attempt < max_attempts
                and not pedagogical_retry_used
                and remaining_for_retry >= min_retry_remaining
            ):
                pedagogical_retry_used = True
                judge_violation = ConstraintViolationDTO(
                    task_index=None,
                    field="tasks",
                    rule_code="PEDAGOGICAL_QUALITY_ISSUE",
                    expected_bound="Pedagogical score >= 60% & overall_status != FAIL",
                    actual_value=f"score={judge_outcome.pedagogical_score}",
                    suggested_fix=(
                        "; ".join(judge_outcome.advisory_warnings)
                        if judge_outcome.advisory_warnings
                        else "Cải thiện trình tự sư phạm, độ rõ ràng và tính thực hành của các nhiệm vụ học tập."
                    ),
                )
                last_violations = [judge_violation]
                retry_history.append(
                    {
                        "attempt": attempt,
                        "violations": [judge_violation.to_dict()],
                    }
                )
                if on_retry_callback is not None:
                    maybe_coro = on_retry_callback(attempt, last_violations)
                    if asyncio.iscoroutine(maybe_coro):
                        await maybe_coro
                current_prompt = self.build_self_correction_prompt(
                    user_prompt,
                    last_violations,
                    attempt_number=attempt,
                )
                continue

            return self._build_valid_gate_result(
                raw_proposal,
                soft_warnings=soft_warnings,
                judge_skipped=judge_outcome.judge_skipped,
                score=judge_outcome.pedagogical_score,
                advisories=[*critic_advisory_warnings, *judge_outcome.advisory_warnings],
                judge_status=judge_outcome.judge_status,
                prompt_tokens=total_prompt_tokens,
                completion_tokens=total_completion_tokens,
                thinking_tokens=total_thinking_tokens,
                attempts_used=attempt,
                retry_history=tuple(retry_history),
                available_minutes=attempt_avail_mins,
                schedule_completeness_status=attempt_completeness,
                allow_partial_schedule=allow_partial_schedule,
            )

        if last_infeasible_ratio is not None and allow_partial_schedule:
            raise PlanInfeasibleError(last_infeasible_ratio)

        raise ProposalValidationGateError(
            message=(
                f"Đề xuất lịch học của AI vẫn vi phạm ràng buộc sau {max_attempts} lần thử "
                f"(tối đa {max_retries} vòng tự sửa lỗi): "
                + ", ".join(v.rule_code for v in last_violations)
            ),
            code="AI_SCHEMA_VALIDATION_ERROR",
            violations=[v.to_dict() for v in last_violations],
        )
