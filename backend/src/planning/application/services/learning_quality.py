import asyncio
import json
import logging
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from src.planning.application.dtos.planning_dtos import CriticQualityLLMOutput
from src.planning.application.services.roadmap_skills import (
    COVERAGE_PREREQUISITE_CRITIC_PROMPT,
    LEARNER_FIT_CRITIC_PROMPT,
    QUALITY_ARBITER_PROMPT,
    build_planning_prompt_registry,
)
from src.planning.domain.models.milestone import Milestone
from src.planning.domain.services.validation_types import ConstraintViolationDTO
from src.shared_kernel.application.harness.execution_manager import AIExecutionManager
from src.shared_kernel.application.harness.models import (
    WorkflowRun,
    WorkflowStatus,
    WorkflowStepExecution,
    WorkflowStepStatus,
    WorkflowType,
)
from src.shared_kernel.application.harness.prompt_registry import build_prompt_audit_metadata
from src.shared_kernel.application.harness.untrusted_context import (
    UntrustedBlockKind,
    format_untrusted_block,
    sanitize_untrusted_text,
    sanitize_untrusted_value,
)
from src.shared_kernel.application.harness.workflow_port import (
    BufferedWorkflowRepo,
    WorkflowRepositoryPort,
)
from src.shared_kernel.application.llm_port import LLMProviderPort
from src.shared_kernel.domain.base import generate_uuid7

logger = logging.getLogger(__name__)


class GenerationStrategy(StrEnum):
    FULL_SCOPE = "FULL_SCOPE"
    FIT_CAPACITY = "FIT_CAPACITY"


class FeasibilityStatus(StrEnum):
    FEASIBLE = "FEASIBLE"
    PARTIAL = "PARTIAL"
    INFEASIBLE = "INFEASIBLE"


@dataclass(frozen=True, slots=True)
class FeasibilityAssessment:
    status: FeasibilityStatus
    required_minutes: int
    available_minutes: int
    scheduled_minutes: int
    schedulable_ratio: float
    unscheduled_minutes: int
    reason_codes: tuple[str, ...]
    recommended_actions: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "required_minutes": self.required_minutes,
            "available_minutes": self.available_minutes,
            "scheduled_minutes": self.scheduled_minutes,
            "schedulable_ratio": self.schedulable_ratio,
            "unscheduled_minutes": self.unscheduled_minutes,
            "reason_codes": list(self.reason_codes),
            "recommended_actions": list(self.recommended_actions),
        }


def assess_schedule_feasibility(
    tasks: Sequence[dict[str, Any]],
    *,
    available_minutes: int,
) -> FeasibilityAssessment:
    required = sum(max(0, int(task.get("estimated_minutes", 0) or 0)) for task in tasks)
    scheduled_from_proposal = sum(
        max(0, int(task.get("estimated_minutes", 0) or 0))
        for task in tasks
        if task.get("scheduled_date") is not None
    )
    scheduled = min(scheduled_from_proposal, max(0, available_minutes))
    ratio = 1.0 if required == 0 else min(1.0, scheduled / required)
    no_capacity = available_minutes <= 0 or scheduled <= 0
    reasons: tuple[str, ...]
    actions: tuple[str, ...]
    if no_capacity or ratio < 0.25:
        status = FeasibilityStatus.INFEASIBLE
        reasons = ("NO_VALID_CAPACITY",) if no_capacity else ("SCHEDULABLE_RATIO_BELOW_25_PERCENT",)
        actions = ("CHANGE_DEADLINE", "INCREASE_AVAILABILITY", "REDUCE_GOAL_SCOPE")
    elif scheduled < required:
        status = FeasibilityStatus.PARTIAL
        reasons = ("DEADLINE_CAPACITY_EXCEEDED",)
        actions = ("KEEP_BACKLOG", "EDIT_SCOPE_MANUALLY", "REGENERATE_ROADMAP_FIT_CAPACITY")
    else:
        status = FeasibilityStatus.FEASIBLE
        reasons = ()
        actions = ("APPLY",)
    return FeasibilityAssessment(
        status=status,
        required_minutes=required,
        available_minutes=max(0, available_minutes),
        scheduled_minutes=scheduled,
        schedulable_ratio=round(ratio, 4),
        unscheduled_minutes=max(0, required - scheduled),
        reason_codes=reasons,
        recommended_actions=actions,
    )


def validate_adaptive_milestones(
    milestones: Sequence[dict[str, Any]],
) -> list[ConstraintViolationDTO]:
    violations: list[ConstraintViolationDTO] = []
    if not milestones:
        return [
            ConstraintViolationDTO(
                task_index=None,
                field="milestones",
                rule_code="EMPTY_MILESTONE_LIST",
                expected_bound="At least one milestone",
                actual_value="0 milestones",
                suggested_fix="Sinh danh sách Milestone thích ứng nhưng không được rỗng.",
            )
        ]
    orders: list[int] = []
    normalized_titles: Counter[str] = Counter()
    for idx, item in enumerate(milestones):
        orders.append(int(item.get("sequence_order", 0) or 0))
        title = str(item.get("title", "")).strip()
        normalized_titles[" ".join(title.lower().split())] += 1
        outcomes = item.get("learning_outcomes")
        criteria = str(item.get("completion_criteria", "")).strip()
        effort = int(item.get("estimated_effort_minutes", 0) or 0)
        if not title:
            violations.append(_violation(idx, "title", "EMPTY_MILESTONE_TITLE", "Non-empty"))
        if not isinstance(outcomes, list) or not [o for o in outcomes if str(o).strip()]:
            violations.append(
                _violation(
                    idx, "learning_outcomes", "MISSING_LEARNING_OUTCOMES", "At least one outcome"
                )
            )
        if not criteria:
            violations.append(
                _violation(
                    idx, "completion_criteria", "MISSING_COMPLETION_CRITERIA", "Measurable criteria"
                )
            )
        if effort <= 0:
            violations.append(
                _violation(
                    idx, "estimated_effort_minutes", "INVALID_MILESTONE_EFFORT", "> 0 minutes"
                )
            )
    expected = list(range(1, len(milestones) + 1))
    if sorted(orders) != expected:
        violations.append(
            _violation(
                None, "sequence_order", "INVALID_MILESTONE_SEQUENCE_ORDER", f"1..{len(milestones)}"
            )
        )
    for title, count in normalized_titles.items():
        if title and count > 1:
            violations.append(
                _violation(
                    None, "title", "DUPLICATE_MILESTONE", f"Unique titles; duplicate={title}"
                )
            )
    return violations


def validate_task_coverage(
    tasks: Sequence[dict[str, Any]], milestones: Sequence[Milestone]
) -> list[ConstraintViolationDTO]:
    violations: list[ConstraintViolationDTO] = []
    tasks_by_mid: dict[str, list[tuple[int, dict[str, Any]]]] = defaultdict(list)
    normalized_titles: Counter[str] = Counter()
    for idx, task in enumerate(tasks):
        tasks_by_mid[str(task.get("milestone_id"))].append((idx, task))
        normalized_titles[" ".join(str(task.get("title", "")).lower().split())] += 1
        for field_name in ("learning_objective", "completion_criteria"):
            if not str(task.get(field_name, "")).strip():
                violations.append(
                    _violation(
                        idx,
                        field_name,
                        f"MISSING_TASK_{field_name.upper()}",
                        "Non-empty measurable text",
                    )
                )

    for milestone in milestones:
        grouped = tasks_by_mid.get(str(milestone.id), [])
        if not grouped:
            violations.append(
                _violation(None, "milestone_id", "MILESTONE_WITHOUT_TASKS", str(milestone.id))
            )
            continue
        covered_outcomes = {
            str(outcome_id)
            for _, task in grouped
            for outcome_id in task.get("covered_outcome_ids", [])
        }
        expected_outcomes = {
            f"M{milestone.sequence_order}-O{i}"
            for i in range(1, len(milestone.learning_outcomes) + 1)
        }
        missing_outcomes = sorted(expected_outcomes - covered_outcomes)
        if missing_outcomes:
            violations.append(
                _violation(
                    None,
                    "covered_outcome_ids",
                    "MILESTONE_OUTCOMES_NOT_COVERED",
                    ",".join(missing_outcomes),
                )
            )
        covered_concepts = {
            str(concept).strip().lower()
            for _, task in grouped
            for concept in task.get("concept_ids", [])
        }
        missing_concepts = sorted(
            concept
            for concept in milestone.required_concepts
            if concept.lower() not in covered_concepts
        )
        if missing_concepts:
            violations.append(
                _violation(
                    None, "concept_ids", "REQUIRED_CONCEPTS_NOT_COVERED", ",".join(missing_concepts)
                )
            )
        task_effort = sum(max(0, int(task.get("estimated_minutes", 0) or 0)) for _, task in grouped)
        milestone_effort = milestone.estimated_effort_minutes
        if milestone_effort > 0 and (
            task_effort < milestone_effort * 0.25 or task_effort > milestone_effort * 2
        ):
            violations.append(
                _violation(
                    None,
                    "estimated_minutes",
                    "MILESTONE_TASK_EFFORT_MISMATCH",
                    f"25%..200% of milestone effort ({milestone_effort} minutes)",
                )
            )

    for title, count in normalized_titles.items():
        if title and count > 1:
            violations.append(_violation(None, "title", "DUPLICATE_TASK", title))
    return violations


CRITIC_RESPONSE_SCHEMA: dict[str, Any] = CriticQualityLLMOutput.model_json_schema()

QUALITY_CRITIC_THINKING_LEVEL = "LOW"
QUALITY_ARBITER_THINKING_LEVEL = "LOW"
DEFAULT_QUALITY_CRITIC_TIMEOUT_SECONDS = 15.0
DEFAULT_QUALITY_ARBITER_TIMEOUT_SECONDS = 14.5
_OPERATIONAL_QUALITY_REVIEW_CODES = frozenset(
    {"QUALITY_CRITIC_UNAVAILABLE", "QUALITY_ARBITER_UNAVAILABLE"}
)


def has_operational_quality_review_failure(
    violations: Sequence[ConstraintViolationDTO],
) -> bool:
    """Return whether quality review failed operationally rather than on plan content."""
    return any(violation.rule_code in _OPERATIONAL_QUALITY_REVIEW_CODES for violation in violations)


def _extract_valid_task_refs(payload: dict[str, Any]) -> set[str]:
    raw_tasks = payload.get("tasks")
    if not isinstance(raw_tasks, list):
        return set()
    refs: set[str] = set()
    for task in raw_tasks:
        if not isinstance(task, dict):
            continue
        for key in ("task_id", "id"):
            val = task.get(key)
            if val is not None and str(val).strip():
                refs.add(str(val).strip())
    return refs


def _filter_unsupported_critic_issues(
    issues: Any,
    *,
    valid_task_refs: set[str],
) -> tuple[list[dict[str, Any]], int]:
    if not isinstance(issues, list):
        return [], 0
    kept: list[dict[str, Any]] = []
    dropped = 0
    for issue in issues:
        if not isinstance(issue, dict):
            continue
        raw_ref = issue.get("task_ref")
        ref_str = str(raw_ref).strip() if raw_ref is not None else ""
        if ref_str and valid_task_refs and ref_str not in valid_task_refs:
            dropped += 1
            continue
        kept.append(issue)
    return kept, dropped


async def run_dual_quality_critics(
    llm: LLMProviderPort,
    *,
    stage: str,
    payload: dict[str, Any],
    context: str,
    learner_level: str = "",
    milestone_summary: str = "",
    timeout_seconds: float = DEFAULT_QUALITY_CRITIC_TIMEOUT_SECONDS,
    arbiter_timeout_seconds: float = DEFAULT_QUALITY_ARBITER_TIMEOUT_SECONDS,
    remaining_budget_seconds: float | None = None,
    workflow_repo: WorkflowRepositoryPort | None = None,
    step_records_out: list[tuple[WorkflowRun, WorkflowStepExecution]] | None = None,
    user_id: UUID | None = None,
    goal_id: UUID | None = None,
    roadmap_id: UUID | None = None,
    workflow_type: WorkflowType | None = None,
    token_accumulator: dict[str, int] | None = None,
) -> tuple[list[ConstraintViolationDTO], list[dict[str, Any]], int, int]:
    if remaining_budget_seconds is not None and remaining_budget_seconds <= 0:
        if token_accumulator is not None:
            token_accumulator["prompt_tokens"] = 0
            token_accumulator["completion_tokens"] = 0
            token_accumulator["thinking_tokens"] = 0
        return (
            [],
            [{"critic": "QUALITY_CRITIC", "status": "SKIPPED_LOW_BUDGET", "issues": []}],
            0,
            0,
        )

    registry = build_planning_prompt_registry()
    serialized = json.dumps(sanitize_untrusted_value(payload), ensure_ascii=False, default=str)
    safe_level = sanitize_untrusted_text(learner_level) or "UNSPECIFIED"
    safe_context_block = format_untrusted_block(
        UntrustedBlockKind.USER_INPUT, context, multiline=True
    )
    safe_milestone_block = (
        format_untrusted_block(UntrustedBlockKind.MILESTONE_DATA, milestone_summary, multiline=True)
        if milestone_summary.strip()
        else ""
    )
    effective_user_id = user_id or uuid4()
    effective_critic_timeout = max(0.01, float(timeout_seconds))
    effective_arbiter_timeout = max(0.01, float(arbiter_timeout_seconds))
    if remaining_budget_seconds is not None:
        effective_critic_timeout = min(effective_critic_timeout, float(remaining_budget_seconds))
        effective_arbiter_timeout = min(effective_arbiter_timeout, float(remaining_budget_seconds))
    roles = (
        (
            "COVERAGE_PREREQUISITE_CRITIC",
            COVERAGE_PREREQUISITE_CRITIC_PROMPT.prompt_id,
            "Kiểm tra độ bao phủ, khoảng trống, trùng lặp và thứ tự tiên quyết.",
        ),
        (
            "LEARNER_FIT_ACTIONABILITY_CRITIC",
            LEARNER_FIT_CRITIC_PROMPT.prompt_id,
            "Kiểm tra độ phù hợp người học, cognitive load, tính hành động và khả năng đo lường.",
        ),
    )

    async def _run(
        role: str, prompt_id: str, instruction: str
    ) -> tuple[dict[str, Any], int, int, int, str, dict[str, str]]:
        tpl = registry.latest(prompt_id)
        audit_meta = build_prompt_audit_metadata(tpl)
        context_parts = [f"learner_level: {safe_level}", f"[CONTEXT]\n{safe_context_block}"]
        if safe_milestone_block:
            context_parts.append(f"[MILESTONES]\n{safe_milestone_block}")
        prompt = (
            f"[INDEPENDENT_CRITIC:{role}]\nStage={stage}\n{instruction}\n"
            "Không sửa payload và không dựa vào kết luận của critic khác; mọi issue phải nêu evidence/task_ref.\n"
            + "\n".join(context_parts)
            + f"\n[PAYLOAD]\n{serialized}"
        )
        # Keep `workflow_repo=None` inside concurrent gather so parallel critics never
        # flush the same SQLAlchemy AsyncSession simultaneously; steps are persisted sequentially below.
        manager = AIExecutionManager(
            provider=llm,
            manage_quota=False,
            max_retries=0,
            timeout_seconds=effective_critic_timeout,
            workflow_repo=None,
        )
        exec_res = await manager.execute(
            user_id=effective_user_id,
            operation_type=f"QUALITY_CRITIC:{role}",
            system_prompt=tpl.system_template,
            user_prompt=prompt,
            response_schema=CRITIC_RESPONSE_SCHEMA,
            model_name=getattr(llm, "model_identifier", "gemini-3.8-flash"),
            thinking_level=QUALITY_CRITIC_THINKING_LEVEL,
            workflow_type=workflow_type,
            step_name=role,
            goal_id=goal_id,
            roadmap_id=roadmap_id,
            prompt_template=tpl,
        )
        raw_val = exec_res.value if isinstance(exec_res.value, dict) else {}
        return (
            raw_val,
            exec_res.prompt_tokens,
            exec_res.completion_tokens,
            exec_res.thinking_tokens,
            exec_res.model_id,
            audit_meta,
        )

    async def _persist_or_buffer(run: WorkflowRun, step: WorkflowStepExecution) -> None:
        if workflow_repo is not None:
            await workflow_repo.add_run(run)
            await workflow_repo.add_step(step)
        elif step_records_out is not None:
            step_records_out.append((run, step))

    critic_loop_start = asyncio.get_running_loop().time()
    started_at = datetime.now(UTC)
    results = await asyncio.gather(*(_run(*role) for role in roles), return_exceptions=True)
    finished_at = datetime.now(UTC)
    violations: list[ConstraintViolationDTO] = []
    reports: list[dict[str, Any]] = []
    prompt_tokens = 0
    completion_tokens = 0
    thinking_tokens = 0
    valid_task_refs = _extract_valid_task_refs(payload)
    for (role, prompt_id, _), result in zip(roles, results, strict=True):
        tpl = registry.latest(prompt_id)
        audit_meta = build_prompt_audit_metadata(tpl)
        if isinstance(result, BaseException):
            if (
                workflow_repo is not None or step_records_out is not None
            ) and workflow_type is not None:
                run = WorkflowRun(
                    id=generate_uuid7(),
                    user_id=effective_user_id,
                    goal_id=goal_id,
                    roadmap_id=roadmap_id,
                    workflow_type=workflow_type,
                    current_step=role,
                    status=WorkflowStatus.FAILED,
                    context_snapshot=audit_meta,
                    error_detail=type(result).__name__,
                    started_at=started_at,
                    completed_at=finished_at,
                )
                step = WorkflowStepExecution(
                    id=generate_uuid7(),
                    workflow_run_id=run.id,
                    step_name=role,
                    step_order=1,
                    status=WorkflowStepStatus.FAILED,
                    input_summary={"operation_type": f"QUALITY_CRITIC:{role}", **audit_meta},
                    output_payload={
                        "error": str(result),
                        "prompt_tokens": 0,
                        "output_tokens": 0,
                        "completion_tokens": 0,
                        "thinking_tokens": 0,
                    },
                    retry_count=0,
                    started_at=started_at,
                    completed_at=finished_at,
                )
                await _persist_or_buffer(run, step)
            violations.append(
                _violation(None, "quality_review", "QUALITY_CRITIC_UNAVAILABLE", role)
            )
            reports.append({"critic": role, "status": "ERROR", "issues": []})
            continue
        report, p_tokens, c_tokens, t_tokens, model_id, run_audit = result
        filtered_issues, dropped_count = _filter_unsupported_critic_issues(
            report.get("issues"), valid_task_refs=valid_task_refs
        )
        if dropped_count:
            logger.warning(
                "critic_unsupported_issues_filtered",
                extra={"critic": role, "dropped_count": dropped_count},
            )
            report = {
                **report,
                "issues": filtered_issues,
                "unsupported_issues_filtered": dropped_count,
            }
        if (
            workflow_repo is not None or step_records_out is not None
        ) and workflow_type is not None:
            run = WorkflowRun(
                id=generate_uuid7(),
                user_id=effective_user_id,
                goal_id=goal_id,
                roadmap_id=roadmap_id,
                workflow_type=workflow_type,
                current_step=role,
                status=WorkflowStatus.COMPLETED,
                context_snapshot=run_audit,
                started_at=started_at,
                completed_at=finished_at,
            )
            step = WorkflowStepExecution(
                id=generate_uuid7(),
                workflow_run_id=run.id,
                step_name=role,
                step_order=1,
                status=WorkflowStepStatus.COMPLETED,
                input_summary={
                    "operation_type": f"QUALITY_CRITIC:{role}",
                    "model": model_id,
                    **run_audit,
                },
                output_payload={
                    "status": str(report.get("status", "")),
                    "prompt_tokens": p_tokens,
                    "output_tokens": c_tokens,
                    "completion_tokens": c_tokens,
                    "thinking_tokens": t_tokens,
                    "model_id": model_id,
                },
                retry_count=0,
                started_at=started_at,
                completed_at=finished_at,
            )
            await _persist_or_buffer(run, step)
        report = {**report, "critic": role}
        reports.append(report)
        prompt_tokens += int(p_tokens or 0)
        completion_tokens += int(c_tokens or 0)
        thinking_tokens += int(t_tokens or 0)

    critic_statuses = {
        str(report.get("status", "")).upper()
        for report in reports
        if str(report.get("status", "")).upper() in {"PASS", "WARN", "FAIL"}
    }
    decisive_reports = reports
    if not violations and "FAIL" in critic_statuses and critic_statuses & {"PASS", "WARN"}:
        if remaining_budget_seconds is not None:
            arbiter_remaining = float(remaining_budget_seconds) - (
                asyncio.get_running_loop().time() - critic_loop_start
            )
            if arbiter_remaining < 1.5:
                logger.warning(
                    "quality_arbiter_skipped_low_budget",
                    extra={
                        "stage": stage,
                        "remaining_seconds": round(arbiter_remaining, 2),
                    },
                )
                violations.append(
                    _violation(
                        None,
                        "quality_review",
                        "QUALITY_ARBITER_UNAVAILABLE",
                        "QUALITY_ARBITER",
                    )
                )
                reports.append({"critic": "QUALITY_ARBITER", "status": "ERROR", "issues": []})
                if token_accumulator is not None:
                    token_accumulator["prompt_tokens"] = prompt_tokens
                    token_accumulator["completion_tokens"] = completion_tokens
                    token_accumulator["thinking_tokens"] = thinking_tokens
                return violations, reports, prompt_tokens, completion_tokens
            effective_arbiter_timeout = min(effective_arbiter_timeout, arbiter_remaining)

        arbiter_tpl = registry.latest(QUALITY_ARBITER_PROMPT.prompt_id)
        arbiter_context_parts = [
            f"learner_level: {safe_level}",
            f"[CONTEXT]\n{safe_context_block}",
        ]
        if safe_milestone_block:
            arbiter_context_parts.append(f"[MILESTONES]\n{safe_milestone_block}")
        arbiter_prompt = (
            f"[QUALITY_ARBITER]\nStage={stage}\n"
            "Hai Critic độc lập đang bất đồng. Hãy phân xử dựa trên bằng chứng trong payload; "
            "không sửa payload và mọi issue phải dẫn evidence/task_ref.\n"
            + "\n".join(arbiter_context_parts)
            + "\n[CRITIC_REPORTS]\n"
            f"{json.dumps(sanitize_untrusted_value(reports), ensure_ascii=False, default=str)}\n"
            f"[PAYLOAD]\n{serialized}"
        )
        arbiter_buffered = (
            BufferedWorkflowRepo()
            if (workflow_repo is None and step_records_out is not None)
            else None
        )
        arbiter_wf_repo: WorkflowRepositoryPort | None = (
            workflow_repo if workflow_repo is not None else arbiter_buffered
        )
        try:
            arbiter_mgr = AIExecutionManager(
                provider=llm,
                manage_quota=False,
                max_retries=0,
                timeout_seconds=effective_arbiter_timeout,
                workflow_repo=arbiter_wf_repo,
            )
            arbiter_res = await arbiter_mgr.execute(
                user_id=effective_user_id,
                operation_type="QUALITY_ARBITER",
                system_prompt=arbiter_tpl.system_template,
                user_prompt=arbiter_prompt,
                response_schema=CRITIC_RESPONSE_SCHEMA,
                model_name=getattr(llm, "model_identifier", "gemini-3.8-flash"),
                thinking_level=QUALITY_ARBITER_THINKING_LEVEL,
                workflow_type=workflow_type,
                step_name="QUALITY_ARBITER",
                goal_id=goal_id,
                roadmap_id=roadmap_id,
                prompt_template=arbiter_tpl,
            )
            arbiter_report = arbiter_res.value if isinstance(arbiter_res.value, dict) else {}
            filtered_arb_issues, arb_dropped = _filter_unsupported_critic_issues(
                arbiter_report.get("issues"), valid_task_refs=valid_task_refs
            )
            if arb_dropped:
                arbiter_report = {
                    **arbiter_report,
                    "issues": filtered_arb_issues,
                    "unsupported_issues_filtered": arb_dropped,
                }
            arbiter_p = arbiter_res.prompt_tokens
            arbiter_c = arbiter_res.completion_tokens
            arbiter_t = arbiter_res.thinking_tokens
        except (TimeoutError, ValueError, RuntimeError, OSError) as exc:
            logger.warning(
                "quality_arbiter_unavailable",
                extra={
                    "stage": stage,
                    "reason_code": "QUALITY_ARBITER_UNAVAILABLE",
                    "error_type": type(exc).__name__,
                },
            )
            violations.append(
                _violation(
                    None,
                    "quality_review",
                    "QUALITY_ARBITER_UNAVAILABLE",
                    "QUALITY_ARBITER",
                )
            )
            reports.append({"critic": "QUALITY_ARBITER", "status": "ERROR", "issues": []})
            if token_accumulator is not None:
                token_accumulator["prompt_tokens"] = prompt_tokens
                token_accumulator["completion_tokens"] = completion_tokens
                token_accumulator["thinking_tokens"] = thinking_tokens
            return violations, reports, prompt_tokens, completion_tokens
        finally:
            if arbiter_buffered is not None and step_records_out is not None:
                step_records_out.extend(arbiter_buffered.drain_pairs())

        arbiter_report = {**arbiter_report, "critic": "QUALITY_ARBITER"}
        reports.append(arbiter_report)
        prompt_tokens += int(arbiter_p or 0)
        completion_tokens += int(arbiter_c or 0)
        thinking_tokens += int(arbiter_t or 0)
        decisive_reports = [arbiter_report]

    for report in decisive_reports:
        role = str(report.get("critic", "QUALITY_CRITIC"))
        error_count_before = len(violations)
        for issue in report.get("issues", []):
            if not isinstance(issue, dict) or str(issue.get("severity", "")).upper() != "ERROR":
                continue
            violations.append(
                _violation(
                    None,
                    "quality_review",
                    str(issue.get("code") or "CRITIC_QUALITY_ISSUE"),
                    str(issue.get("message") or issue.get("suggested_fix") or role),
                )
            )
        if (
            str(report.get("status", "")).upper() == "FAIL"
            and len(violations) == error_count_before
        ):
            violations.append(_violation(None, "quality_review", "CRITIC_REJECTED_PLAN", role))
    if token_accumulator is not None:
        token_accumulator["prompt_tokens"] = prompt_tokens
        token_accumulator["completion_tokens"] = completion_tokens
        token_accumulator["thinking_tokens"] = thinking_tokens
    return violations, reports, prompt_tokens, completion_tokens


def _violation(
    task_index: int | None, field: str, code: str, expected: str
) -> ConstraintViolationDTO:
    return ConstraintViolationDTO(
        task_index=task_index,
        field=field,
        rule_code=code,
        expected_bound=expected,
        actual_value="Invalid or missing",
        suggested_fix=f"Khắc phục {code}: {expected}.",
    )
