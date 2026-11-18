"""Tier 3 Pedagogical LLM-as-a-Judge Gate with Unsupported-Issue Filtering (ADR-009 / T6.2 / T7.3)."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

import structlog

from src.planning.application.dtos.planning_dtos import PedagogicalJudgeLLMOutput
from src.planning.application.services.roadmap_skills import (
    PEDAGOGICAL_JUDGE_SKILL,
    build_pedagogical_judge_prompt,
    build_planning_prompt_registry,
)
from src.planning.application.services.roadmap_skills import (
    build_compact_judge_payload as build_compact_judge_payload,
)
from src.shared_kernel.application.harness.execution_manager import AIExecutionManager
from src.shared_kernel.application.harness.models import (
    WorkflowRun,
    WorkflowStepExecution,
    WorkflowType,
)
from src.shared_kernel.application.harness.untrusted_context import sanitize_untrusted_text
from src.shared_kernel.application.harness.workflow_port import (
    BufferedWorkflowRepo,
    WorkflowRepositoryPort,
)
from src.shared_kernel.application.llm_port import LLMProviderPort
from src.shared_kernel.config import get_settings

logger = structlog.get_logger(__name__)

TIER3_JUDGE_TIMEOUT_SECONDS: float = 12.0
DEFAULT_MIN_JUDGE_REMAINING_SECONDS: float = 3.0
PEDAGOGICAL_JUDGE_RESPONSE_SCHEMA: dict[str, Any] = PedagogicalJudgeLLMOutput.model_json_schema()


@dataclass(frozen=True, slots=True)
class Tier3JudgeOutcome:
    judge_skipped: bool
    pedagogical_score: float | None
    advisory_warnings: list[str]
    judge_status: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    thinking_tokens: int = 0
    unsupported_issues_filtered: int = 0


def _extract_valid_task_refs(proposal_data: dict[str, Any]) -> set[str]:
    raw_tasks = proposal_data.get("tasks")
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


def _filter_unsupported_judge_issues(
    raw_issues: Any,
    *,
    valid_task_refs: set[str],
) -> tuple[list[dict[str, Any]], int]:
    """Filter out judge issues referencing nonexistent task_refs (`unsupported_issue`)."""
    if not isinstance(raw_issues, list):
        return [], 0
    kept: list[dict[str, Any]] = []
    dropped = 0
    for issue in raw_issues:
        if not isinstance(issue, dict):
            continue
        raw_ref = issue.get("task_ref")
        ref_str = str(raw_ref).strip() if raw_ref is not None else ""
        if ref_str and ref_str not in valid_task_refs:
            dropped += 1
            continue
        kept.append(issue)
    return kept, dropped


async def execute_tier3_pedagogical_judge(
    llm_provider: LLMProviderPort | None,
    proposal_data: dict[str, Any],
    *,
    enable_tier3_judge: bool = True,
    tier3_timeout_seconds: float | None = None,
    min_judge_remaining_seconds: float | None = None,
    thinking_level: str | None = None,
    goal_title: str = "",
    learner_level: str = "",
    milestone_summary: str = "",
    milestones_metadata: Sequence[Any] | None = None,
    remaining_budget_seconds: float | None = None,
    workflow_repo: WorkflowRepositoryPort | None = None,
    step_records_out: list[tuple[WorkflowRun, WorkflowStepExecution]] | None = None,
    user_id: UUID | None = None,
    goal_id: UUID | None = None,
    roadmap_id: UUID | None = None,
    quota: Any = None,
) -> Tier3JudgeOutcome:
    """Execute Tier 3 Pedagogical Judge with configurable single-attempt timeout & honest status."""
    if not enable_tier3_judge or llm_provider is None:
        return Tier3JudgeOutcome(
            judge_skipped=True,
            pedagogical_score=None,
            advisory_warnings=[],
            judge_status="SKIPPED",
        )

    settings = get_settings()
    effective_min_remaining = (
        float(min_judge_remaining_seconds)
        if min_judge_remaining_seconds is not None
        else float(
            getattr(settings, "ai_min_judge_remaining_seconds", DEFAULT_MIN_JUDGE_REMAINING_SECONDS)
        )
    )
    if remaining_budget_seconds is not None and (
        remaining_budget_seconds <= 0 or remaining_budget_seconds < effective_min_remaining
    ):
        return Tier3JudgeOutcome(
            judge_skipped=True,
            pedagogical_score=None,
            advisory_warnings=[
                "Tier 3 Pedagogical Judge không còn đủ thời gian trong ngân sách pipeline — trạng thái REVIEW_PENDING."
            ],
            judge_status="REVIEW_PENDING",
        )

    configured_timeout = (
        float(tier3_timeout_seconds)
        if tier3_timeout_seconds is not None
        else float(getattr(settings, "tier3_judge_timeout_seconds", TIER3_JUDGE_TIMEOUT_SECONDS))
    )
    attempt_timeout = min(
        configured_timeout,
        float(getattr(settings, "ai_hard_timeout_seconds", 55.0)),
    )
    if remaining_budget_seconds is not None:
        attempt_timeout = min(attempt_timeout, float(remaining_budget_seconds))
    if attempt_timeout <= 0:
        return Tier3JudgeOutcome(
            judge_skipped=True,
            pedagogical_score=None,
            advisory_warnings=[
                "Tier 3 Pedagogical Judge không còn thời gian trong ngân sách pipeline — trạng thái REVIEW_PENDING."
            ],
            judge_status="REVIEW_PENDING",
        )

    compact_payload = build_compact_judge_payload(
        proposal_data,
        milestones_metadata=milestones_metadata,
    )
    effective_milestone_summary = milestone_summary
    if not effective_milestone_summary.strip() and compact_payload.get("milestones"):
        effective_milestone_summary = json.dumps(compact_payload["milestones"], ensure_ascii=False)

    judge_tpl = build_planning_prompt_registry().latest(PEDAGOGICAL_JUDGE_SKILL.skill_id)
    judge_user_prompt = build_pedagogical_judge_prompt(
        compact_payload,
        context_block=(
            f"Mục tiêu: {sanitize_untrusted_text(goal_title)}\n"
            f"Số nhiệm vụ: {len(compact_payload.get('tasks', []))}"
        ),
        milestones_summary=effective_milestone_summary,
        learner_level=learner_level,
    )

    judge_dict: dict[str, Any] | None = None
    last_exc: Exception | None = None
    prompt_tokens = 0
    completion_tokens = 0
    thinking_tokens = 0
    effective_thinking_level = thinking_level or PEDAGOGICAL_JUDGE_SKILL.thinking_level
    buffered_repo = (
        BufferedWorkflowRepo() if (workflow_repo is None and step_records_out is not None) else None
    )
    effective_wf_repo: WorkflowRepositoryPort | None = (
        workflow_repo if workflow_repo is not None else buffered_repo
    )
    try:
        exec_mgr = AIExecutionManager(
            provider=llm_provider,
            quota=quota,
            manage_quota=False,
            max_retries=0,
            timeout_seconds=attempt_timeout,
            workflow_repo=effective_wf_repo,
        )
        exec_res = await exec_mgr.execute(
            user_id=user_id or uuid4(),
            operation_type="PEDAGOGICAL_JUDGE",
            system_prompt=judge_tpl.system_template,
            user_prompt=judge_user_prompt,
            response_schema=PEDAGOGICAL_JUDGE_RESPONSE_SCHEMA,
            model_name=getattr(llm_provider, "model_identifier", "gemini-3.8-flash-low"),
            thinking_level=effective_thinking_level,
            workflow_type=WorkflowType.SCHEDULE_GENERATION,
            step_name="PEDAGOGICAL_JUDGE",
            goal_id=goal_id,
            roadmap_id=roadmap_id,
            prompt_template=judge_tpl,
        )
        judge_dict = exec_res.value if isinstance(exec_res.value, dict) else None
        prompt_tokens = exec_res.prompt_tokens
        completion_tokens = exec_res.completion_tokens
        thinking_tokens = exec_res.thinking_tokens
    except TimeoutError as exc:
        last_exc = exc
        logger.warning(
            "tier3_pedagogical_judge_timeout",
            attempt=1,
            timeout_seconds=attempt_timeout,
        )
    except Exception as exc:
        last_exc = exc
        logger.warning(
            "tier3_pedagogical_judge_error",
            attempt=1,
            error=str(exc),
        )
    finally:
        if buffered_repo is not None and step_records_out is not None:
            step_records_out.extend(buffered_repo.drain_pairs())

    if judge_dict is None or last_exc is not None:
        if isinstance(last_exc, (TimeoutError, asyncio.TimeoutError)):
            return Tier3JudgeOutcome(
                judge_skipped=True,
                pedagogical_score=None,
                advisory_warnings=[
                    f"Tier 3 Pedagogical Judge quá thời gian chờ ({attempt_timeout:.0f}s) — đã bỏ qua theo cơ chế Fail-Open (ADR-009), trạng thái REVIEW_PENDING."
                ],
                judge_status="REVIEW_PENDING",
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                thinking_tokens=thinking_tokens,
            )
        return Tier3JudgeOutcome(
            judge_skipped=True,
            pedagogical_score=None,
            advisory_warnings=[
                "Tier 3 Pedagogical Judge tạm thời không phản hồi — đã bỏ qua theo cơ chế Fail-Open (ADR-009), trạng thái REVIEW_PENDING."
            ],
            judge_status="REVIEW_PENDING",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            thinking_tokens=thinking_tokens,
        )

    score_raw = judge_dict.get("score")
    if isinstance(score_raw, bool) or not isinstance(score_raw, (int, float)):
        score_raw = judge_dict.get("pedagogical_score")
    if isinstance(score_raw, bool) or not isinstance(score_raw, (int, float)):
        return Tier3JudgeOutcome(
            judge_skipped=True,
            pedagogical_score=None,
            advisory_warnings=[
                "Tier 3 Pedagogical Judge thiếu điểm số hợp lệ (score) — đã chuyển sang trạng thái REVIEW_PENDING."
            ],
            judge_status="REVIEW_PENDING",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            thinking_tokens=thinking_tokens,
        )

    raw_float = float(score_raw)
    if 0.0 < raw_float <= 1.0 and not isinstance(score_raw, int):
        score_int = int(round(raw_float * 100))
    else:
        score_int = int(round(raw_float))
    score_int = max(0, min(100, score_int))
    score = float(score_int)

    raw_overall_status = judge_dict.get("overall_status")
    overall_status = str(raw_overall_status).strip().upper() if raw_overall_status else ""

    collected_warnings: list[str] = []
    for key in ("advisory_warnings", "warnings"):
        raw_list = judge_dict.get(key, [])
        if isinstance(raw_list, list):
            for w in raw_list:
                w_str = str(w).strip()
                if w_str and w_str not in collected_warnings:
                    collected_warnings.append(w_str)

    valid_task_refs = _extract_valid_task_refs(proposal_data)
    filtered_issues, dropped_unsupported = _filter_unsupported_judge_issues(
        judge_dict.get("issues", []),
        valid_task_refs=valid_task_refs,
    )
    if dropped_unsupported:
        logger.warning(
            "tier3_judge_unsupported_issues_filtered",
            dropped_count=dropped_unsupported,
        )

    has_critical_issue = False
    for issue in filtered_issues:
        sev = str(issue.get("severity") or "").strip().upper()
        if sev in {"CRITICAL", "ERROR", "FAIL"}:
            has_critical_issue = True
        cat = str(issue.get("category") or "").strip()
        msg = str(issue.get("message") or "").strip()
        if msg:
            formatted_msg = f"[{cat}] {msg}" if cat and cat not in msg else msg
            if formatted_msg not in collected_warnings:
                collected_warnings.append(formatted_msg)

    if overall_status == "FAIL" or has_critical_issue or score_int < 60:
        if not collected_warnings:
            collected_warnings.append(
                f"Điểm thẩm định sư phạm đạt {score_int}/100 (< 60) — cần kiểm tra lại trình tự và độ khó của các bài học."
            )
        return Tier3JudgeOutcome(
            judge_skipped=False,
            pedagogical_score=score,
            advisory_warnings=collected_warnings,
            judge_status="NEEDS_REVIEW",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            thinking_tokens=thinking_tokens,
            unsupported_issues_filtered=dropped_unsupported,
        )

    return Tier3JudgeOutcome(
        judge_skipped=False,
        pedagogical_score=score,
        advisory_warnings=collected_warnings,
        judge_status="PASSED",
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        thinking_tokens=thinking_tokens,
        unsupported_issues_filtered=dropped_unsupported,
    )
