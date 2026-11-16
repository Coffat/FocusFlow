"""Part B & Part C live cobhub experiments for Group 2.

Measures:
1. All unmeasured stages (`goal-clarifier`, `goal-clarifier-followup`,
   `coverage-prerequisite-critic`, `learner-fit-actionability-critic`,
   `quality-arbiter`, `weekly-review-advisor`, `prove-question-generator` LOW vs MEDIUM,
   `prove-mode-grader` LOW vs MEDIUM).
2. Requirement #2 A/B comparison (-low vs -medium x 3 runs):
   - Milestone Planner across multi-level sample goals (x 3 rounds).
   - Task Decomposer via `eval_runner` (18 goals sequential, trials_per_goal=1, x 3 runs per arm)
     with Tier 3 Judge enabled on `gemini-3.8-flash-low`.
3. Part C live verification: 3 consecutive runs per stage verifying 0/3 timeouts under final
   configured `Settings` budgets.

Results are written incrementally to `docs/experiments/group2_measurements.json` without PII/secrets.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import statistics
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

from common import EXPERIMENTS_OUT_DIR, get_cobhub_config, sanitize_error_message, utc_timestamp

from src.evaluation.application.dtos.intelligence import (
    ProveGradingLLMOutput,
    ProveQuestionsLLMOutput,
    WeeklyReviewLLMOutput,
)
from src.evaluation.application.prompts import (
    PROVE_MODE_GRADER_PROMPT,
    PROVE_QUESTION_GENERATOR_PROMPT,
    WEEKLY_REVIEW_ADVISOR_PROMPT,
    build_evaluation_prompt_registry,
    build_prove_grader_prompt,
    build_prove_question_prompt,
    build_weekly_review_prompt,
)
from src.planning.application.dtos.planning_dtos import (
    ClarificationFollowupLLMOutput,
    ClarificationQuestionsLLMOutput,
    MilestoneGenerationLLMOutput,
    TaskProposalLLMOutput,
)
from src.planning.application.services.learning_quality import CRITIC_RESPONSE_SCHEMA
from src.planning.application.services.roadmap_skills import (
    COVERAGE_PREREQUISITE_CRITIC_PROMPT,
    GOAL_CLARIFIER_FOLLOWUP_PROMPT,
    GOAL_CLARIFIER_SKILL,
    LEARNER_FIT_CRITIC_PROMPT,
    MILESTONE_PLANNER_SKILL,
    PEDAGOGICAL_JUDGE_SKILL,
    QUALITY_ARBITER_PROMPT,
    TASK_DECOMPOSER_SKILL,
    build_goal_clarifier_followup_prompt,
    build_goal_clarifier_prompt,
    build_milestone_planner_prompt,
    build_pedagogical_judge_prompt,
    build_planning_prompt_registry,
    build_task_decomposer_prompt,
)
from src.planning.application.services.validation_gate.tier1_schema import (
    validate_ai_milestones_tier1,
)
from src.planning.application.services.validation_gate.tier3_judge import (
    PEDAGOGICAL_JUDGE_RESPONSE_SCHEMA,
)
from src.shared_kernel.application.harness.execution_manager import AIExecutionManager
from src.shared_kernel.application.llm_port import LLMToolDeclarationDTO, classify_ai_error
from src.shared_kernel.config import get_settings
from src.shared_kernel.infrastructure.external_ai.litellm_adapter import LiteLLMAdapter
from tests.ai_evals.eval_runner import run_planning_eval_suite

OUTPUT_PATH: Path = EXPERIMENTS_OUT_DIR / "group2_measurements.json"


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return round(ordered[0], 2)
    rank = (len(ordered) - 1) * (pct / 100.0)
    lo = math.floor(rank)
    hi = math.ceil(rank)
    if lo == hi:
        return round(ordered[lo], 2)
    w = rank - lo
    return round(ordered[lo] * (1.0 - w) + ordered[hi] * w, 2)


def _summarize_runs(runs: list[dict[str, Any]]) -> dict[str, Any]:
    ok_runs = [r for r in runs if r.get("ok")]
    latencies = [float(r["latency_ms"]) for r in ok_runs]
    p_toks = [int(r["prompt_tokens"]) for r in ok_runs]
    o_toks = [int(r["output_tokens"]) for r in ok_runs]
    t_toks = [int(r["thinking_tokens"]) for r in ok_runs]
    total_o = sum(o_toks)
    total_t = sum(t_toks)
    p95_ms = _percentile(latencies, 95.0)
    return {
        "trials": len(runs),
        "success_count": len(ok_runs),
        "success_rate": round(len(ok_runs) / max(1, len(runs)), 4),
        "latency_ms": {
            "min": round(min(latencies), 2) if latencies else 0.0,
            "p50": _percentile(latencies, 50.0),
            "p95": p95_ms,
            "max": round(max(latencies), 2) if latencies else 0.0,
            "mean": round(statistics.mean(latencies), 2) if latencies else 0.0,
        },
        "recommended_timeout_1_4x_p95_s": round((p95_ms / 1000.0) * 1.4, 2) if p95_ms else 0.0,
        "recommended_timeout_1_5x_p95_s": round((p95_ms / 1000.0) * 1.5, 2) if p95_ms else 0.0,
        "prompt_tokens_total": sum(p_toks),
        "output_tokens_total": total_o,
        "thinking_tokens_total": total_t,
        "thinking_pct_of_output": round((total_t / total_o) * 100.0, 2) if total_o > 0 else 0.0,
        "thinking_tokens": {
            "min": min(t_toks) if t_toks else 0,
            "p50": _percentile([float(x) for x in t_toks], 50.0),
            "p95": _percentile([float(x) for x in t_toks], 95.0),
            "max": max(t_toks) if t_toks else 0,
        },
        "models_used": sorted({str(r.get("model_id", "")) for r in ok_runs if r.get("model_id")}),
        "errors": [r["error"] for r in runs if not r.get("ok")],
    }


def _configure_env(base_url: str) -> None:
    os.environ["LLM_PROVIDER"] = "gemini"
    os.environ["LLM_BASE_URL"] = base_url
    os.environ["LLM_THINKING_CONTROL"] = "model_suffix"
    os.environ["LLM_MODEL"] = "gemini-3.8-flash-medium"
    os.environ["LLM_MODEL_LOW"] = "gemini-3.8-flash-low"
    os.environ["LLM_MODEL_MEDIUM"] = "gemini-3.8-flash-medium"
    os.environ["LLM_MODEL_HIGH"] = "gemini-3.8-flash-high"
    get_settings.cache_clear()


def _load_existing() -> dict[str, Any]:
    if OUTPUT_PATH.exists():
        try:
            data = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return {
        "schema_version": "1.0",
        "branch": "feat/cobhub-hardening",
        "gateway_base_url": "http://127.0.0.1:8045",
        "thinking_control": "model_suffix",
    }


def _save_report(report: dict[str, Any]) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    report["updated_at"] = utc_timestamp()
    OUTPUT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


async def _run_stage_trials(
    *,
    stage_name: str,
    system_prompt: str,
    user_prompt: str,
    response_schema: Any,
    thinking_level: str,
    trials: int,
    timeout_seconds: float,
    max_retries: int = 1,
    tools: list[LLMToolDeclarationDTO] | None = None,
    tool_executor: Any = None,
    max_tool_calls: int = 0,
) -> dict[str, Any]:
    runs: list[dict[str, Any]] = []
    for idx in range(1, trials + 1):
        adapter = LiteLLMAdapter()
        mgr = AIExecutionManager(
            provider=adapter,
            manage_quota=False,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )
        t0 = time.perf_counter()
        try:
            res = await mgr.execute(
                user_id=uuid4(),
                operation_type=f"MEASURE_{stage_name.upper()}",
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_schema=response_schema,
                tools=tools,
                tool_executor=tool_executor,
                max_tool_calls=max_tool_calls,
                thinking_level=thinking_level,
            )
            elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            runs.append(
                {
                    "trial": idx,
                    "ok": True,
                    "latency_ms": elapsed_ms,
                    "prompt_tokens": res.prompt_tokens,
                    "output_tokens": res.completion_tokens,
                    "thinking_tokens": res.thinking_tokens,
                    "model_id": res.model_id,
                    "attempts": res.attempts,
                    "repair_attempts": res.repair_attempts,
                }
            )
            print(
                f"  [{stage_name}][{thinking_level}] #{idx}/{trials} OK "
                f"{elapsed_ms:.0f}ms model={res.model_id} t_tok={res.thinking_tokens} o_tok={res.completion_tokens}",
                flush=True,
            )
        except Exception as exc:
            elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            cat = classify_ai_error(exc).value
            err_msg = f"{cat}: {sanitize_error_message(exc)}"
            runs.append(
                {
                    "trial": idx,
                    "ok": False,
                    "latency_ms": elapsed_ms,
                    "error": err_msg,
                    "error_category": cat,
                }
            )
            print(
                f"  [{stage_name}][{thinking_level}] #{idx}/{trials} FAIL "
                f"{elapsed_ms:.0f}ms {err_msg[:120]}",
                flush=True,
            )
    return {
        "stage": stage_name,
        "thinking_level": thinking_level,
        "timeout_budget_s": timeout_seconds,
        "summary": _summarize_runs(runs),
        "runs": runs,
    }


def _sample_planner_goals() -> list[dict[str, Any]]:
    return [
        {
            "id": "G1_BEGINNER_PYTHON",
            "learner_level": "BEGINNER",
            "strategy": "FULL_SCOPE",
            "context": (
                "Goal: Tự học Python Backend với FastAPI và PostgreSQL trong 45 ngày.\n"
                "Trình độ hiện tại: BEGINNER (mới biết cú pháp cơ bản, chưa từng làm REST API).\n"
                "Quỹ thời gian: 90 phút/ngày, tổng 67 giờ.\n"
                "Sản phẩm đầu ra: Xây dựng được API quản lý công việc có JWT và unit test."
            ),
        },
        {
            "id": "G2_INTERMEDIATE_AWS",
            "learner_level": "INTERMEDIATE",
            "strategy": "FULL_SCOPE",
            "context": (
                "Goal: Luyện thi chứng chỉ AWS Solutions Architect Associate (SAA-C03) trong 60 ngày.\n"
                "Trình độ hiện tại: INTERMEDIATE (đã biết Linux, Docker, mạng cơ bản).\n"
                "Quỹ thời gian: 120 phút/ngày.\n"
                "Trọng tâm: IAM, VPC, EC2, S3, RDS, Serverless, High Availability & Cost Optimization."
            ),
        },
        {
            "id": "G3_ADVANCED_SYS_DESIGN",
            "learner_level": "ADVANCED",
            "strategy": "FULL_SCOPE",
            "context": (
                "Goal: Thiết kế Hệ thống Phân tán & Event-Driven Architecture chịu tải cao trong 30 ngày.\n"
                "Trình độ hiện tại: ADVANCED (4 năm kinh nghiệm backend, muốn lên Staff Engineer).\n"
                "Quỹ thời gian: 90 phút/ngày.\n"
                "Trọng tâm: Consensus (Raft), Partitioning, Outbox/CDC, Saga, Backpressure & Observability."
            ),
        },
        {
            "id": "G4_TIGHT_FIT_CAPACITY",
            "learner_level": "BEGINNER",
            "strategy": "FIT_CAPACITY",
            "context": (
                "Goal: Học React 19, TypeScript và Next.js Fullstack trong 14 ngày.\n"
                "Trình độ hiện tại: BEGINNER (biết HTML/CSS cơ bản).\n"
                "Quỹ thời gian: 60 phút/ngày (tổng chỉ 14 giờ -> cần FIT_CAPACITY, hoãn phần nâng cao).\n"
                "Trọng tâm: Thành thạo component cơ bản và 1 trang dashboard kết nối API."
            ),
        },
    ]


async def _mock_planner_tool_executor(name: str, args: dict[str, Any]) -> dict[str, Any]:
    del args
    if name == "search_learning_concepts":
        return {
            "status": "success",
            "concepts": [
                {"concept_id": "py-control-flow-functions", "title": "Python Control Flow & Functions"},
                {"concept_id": "fastapi-routing-pydantic", "title": "FastAPI Routing & Pydantic v2"},
                {"concept_id": "sql-postgres-indexing", "title": "PostgreSQL & Indexing"},
                {"concept_id": "system-design-distributed", "title": "Distributed Systems Foundations"},
            ],
        }
    if name == "get_concept_prerequisite_graph":
        return {
            "status": "success",
            "prerequisites": [
                {"from": "py-control-flow-functions", "to": "fastapi-routing-pydantic"},
                {"from": "fastapi-routing-pydantic", "to": "sql-postgres-indexing"},
            ],
        }
    return {"status": "success", "items": []}


async def run_stages_phase(trials: int = 8) -> dict[str, Any]:
    planning_reg = build_planning_prompt_registry()
    eval_reg = build_evaluation_prompt_registry()

    clarifier_tpl = planning_reg.latest(GOAL_CLARIFIER_SKILL.skill_id)
    followup_tpl = planning_reg.latest(GOAL_CLARIFIER_FOLLOWUP_PROMPT.prompt_id)
    cov_critic_tpl = planning_reg.latest(COVERAGE_PREREQUISITE_CRITIC_PROMPT.prompt_id)
    fit_critic_tpl = planning_reg.latest(LEARNER_FIT_CRITIC_PROMPT.prompt_id)
    arbiter_tpl = planning_reg.latest(QUALITY_ARBITER_PROMPT.prompt_id)
    weekly_tpl = eval_reg.latest(WEEKLY_REVIEW_ADVISOR_PROMPT.prompt_id)
    prove_q_tpl = eval_reg.latest(PROVE_QUESTION_GENERATOR_PROMPT.prompt_id)
    prove_g_tpl = eval_reg.latest(PROVE_MODE_GRADER_PROMPT.prompt_id)

    clarifier_user = build_goal_clarifier_prompt(
        goal_title="Học FastAPI, PostgreSQL & Hexagonal Architecture trong 45 ngày",
        raw_description=(
            "Tôi muốn làm backend API chuẩn production bằng Python, biết cơ bản vòng lặp và hàm, "
            "chưa rõ cách tổ chức dự án và viết test bất đồng bộ."
        ),
        prior_knowledge_level="BEGINNER",
        target_date_iso="2026-12-31",
        known_dimensions=["TIMELINE"],
        gap_count=3,
    )
    followup_user = build_goal_clarifier_followup_prompt(
        gap={
            "dimension": "TIME_COMMITMENT",
            "status": "PARTIAL",
            "priority": 90,
            "reason": "Người học chưa nêu rõ số giờ rảnh mỗi ngày trong tuần vs cuối tuần.",
        },
        prior_answers=[
            {
                "question_id": "q1",
                "answer": "Tôi đã biết Python cơ bản và muốn làm backend FastAPI.",
            }
        ],
    )
    sample_proposal_payload = {
        "tasks": [
            {
                "task_id": "T1",
                "title": "Nắm vững Pydantic v2 BaseModel & Validation",
                "task_type": "THEORY",
                "estimated_minutes": 45,
                "covered_outcome_ids": ["M1-O1"],
                "concept_ids": ["fastapi-routing-pydantic"],
                "learning_objective": "Phân biệt Pydantic schema và domain entity.",
                "completion_criteria": "Viết được 3 schema request/response có validator.",
            },
            {
                "task_id": "T2",
                "title": "Thực hành xây dựng FastAPI Router & Dependency Injection",
                "task_type": "PRACTICE",
                "estimated_minutes": 60,
                "covered_outcome_ids": ["M1-O2"],
                "concept_ids": ["fastapi-routing-pydantic"],
                "learning_objective": "Tổ chức router tách biệt use case qua Depends.",
                "completion_criteria": "Chạy thành công 3 endpoint CRUD qua TestClient.",
            },
            {
                "task_id": "T3",
                "title": "Ôn tập kiến trúc 4 lớp và viết pytest async",
                "task_type": "REVIEW",
                "estimated_minutes": 45,
                "covered_outcome_ids": ["M1-O1", "M1-O2"],
                "concept_ids": ["fastapi-routing-pydantic"],
                "learning_objective": "Kiểm chứng bất biến tầng application bằng fake port.",
                "completion_criteria": "Pass 100% 4 unit tests async.",
            },
        ],
        "dependencies": [
            {"predecessor_id": "T1", "successor_id": "T2", "is_mandatory": True},
            {"predecessor_id": "T2", "successor_id": "T3", "is_mandatory": True},
        ],
    }
    critic_user = (
        "[INDEPENDENT_CRITIC]\nStage=TASK_DECOMPOSITION\n"
        "learner_level: BEGINNER\n"
        "[CONTEXT]\n<user_input>Goal: Học FastAPI Backend</user_input>\n"
        "[MILESTONES]\n<milestone_data>M1 (FastAPI Core): effort=150m | outcomes=[M1-O1, M1-O2]</milestone_data>\n"
        f"[PAYLOAD]\n{json.dumps(sample_proposal_payload, ensure_ascii=False)}"
    )
    arbiter_reports = [
        {
            "critic": "COVERAGE_PREREQUISITE_CRITIC",
            "status": "PASS",
            "score": 88,
            "issues": [],
        },
        {
            "critic": "LEARNER_FIT_ACTIONABILITY_CRITIC",
            "status": "FAIL",
            "score": 52,
            "issues": [
                {
                    "code": "MISSING_PROJECT",
                    "severity": "ERROR",
                    "task_ref": "T3",
                    "evidence": "Chỉ có THEORY, PRACTICE, REVIEW, thiếu task PROJECT.",
                    "message": "Thiếu bài tập tổng hợp nhỏ cuối chặng.",
                }
            ],
        },
    ]
    arbiter_user = (
        "[QUALITY_ARBITER]\nStage=TASK_DECOMPOSITION\n"
        "learner_level: BEGINNER\n"
        f"[CRITIC_REPORTS]\n{json.dumps(arbiter_reports, ensure_ascii=False)}\n"
        f"[PAYLOAD]\n{json.dumps(sample_proposal_payload, ensure_ascii=False)}"
    )
    weekly_user = build_weekly_review_prompt(
        quantitative_summary={
            "completed_minutes": 240,
            "planned_minutes": 300,
            "completed_sessions_count": 5,
            "completed_tasks_count": 4,
            "planned_tasks_count": 5,
            "overdue_tasks_count": 1,
            "adherence_rate_pct": 80.0,
        },
        reflection={
            "summary": "Tuần này mình học tốt Pydantic và FastAPI, hơi đuối vào thứ Năm do tăng ca."
        },
    )
    prove_q_user = build_prove_question_prompt(
        milestone_title="Cột mốc 1: FastAPI & Pydantic Validation",
        description="Thiết kế REST API chuẩn Pydantic v2 và Dependency Injection.",
        learning_outcomes=[
            "M1-O1: Phân biệt schema request/response với domain model",
            "M1-O2: Xử lý validation error và HTTP status code chuẩn",
        ],
        completion_criteria="Xây dựng được 3 endpoint CRUD có unit test.",
        required_concepts=["fastapi-routing-pydantic"],
        task_titles=["T1: Pydantic v2 Schema", "T2: FastAPI Router & Depends"],
    )
    prove_g_user = build_prove_grader_prompt(
        [
            (
                "q1",
                "Giải thích sự khác nhau giữa Pydantic schema ở tầng presentation và Domain Model ở tầng domain.",
                "Pydantic schema dùng để validate JSON input/output ở HTTP boundary, còn Domain Model chứa logic nghiệp vụ và bất biến thuần Python.",
            ),
            (
                "q2",
                "Nêu một lỗi thường gặp khi đặt session.commit() trong repository và cách khắc phục.",
                "Nếu repository tự commit thì khi use case cập nhật 2 bảng hoặc outbox sẽ mất tính nguyên tử; cần dùng AsyncUnitOfWork để commit ở cuối use case.",
            ),
            (
                "q3",
                "Trong tình huống user A gọi GET /goals/{id_cua_B}, API nên xử lý như thế nào để chống IDOR?",
                "Kiểm tra resource.user_id == current_user.id ở use case và trả về 404 Not Found thay vì 403 để tránh lộ sự tồn tại tài nguyên.",
            ),
        ]
    )

    stage_specs = [
        ("goal-clarifier", clarifier_tpl.system_template, clarifier_user, ClarificationQuestionsLLMOutput, "LOW", trials),
        ("goal-clarifier-followup", followup_tpl.system_template, followup_user, ClarificationFollowupLLMOutput, "LOW", trials),
        ("coverage-prerequisite-critic", cov_critic_tpl.system_template, critic_user, CRITIC_RESPONSE_SCHEMA, "LOW", trials),
        ("learner-fit-actionability-critic", fit_critic_tpl.system_template, critic_user, CRITIC_RESPONSE_SCHEMA, "LOW", trials),
        ("quality-arbiter", arbiter_tpl.system_template, arbiter_user, CRITIC_RESPONSE_SCHEMA, "LOW", trials),
        ("weekly-review-advisor", weekly_tpl.system_template, weekly_user, WeeklyReviewLLMOutput, "LOW", trials),
        ("prove-question-generator", prove_q_tpl.system_template, prove_q_user, ProveQuestionsLLMOutput, "LOW", max(6, trials)),
        ("prove-question-generator", prove_q_tpl.system_template, prove_q_user, ProveQuestionsLLMOutput, "MEDIUM", max(6, trials)),
        ("prove-mode-grader", prove_g_tpl.system_template, prove_g_user, ProveGradingLLMOutput, "LOW", max(6, trials)),
        ("prove-mode-grader", prove_g_tpl.system_template, prove_g_user, ProveGradingLLMOutput, "MEDIUM", max(6, trials)),
    ]

    results: dict[str, Any] = {}
    for stage_name, sys_p, usr_p, schema, tier, n_trials in stage_specs:
        key = f"{stage_name}__{tier.lower()}"
        print(f"\n[Stage Measure] {key} ({n_trials} trials)...", flush=True)
        results[key] = await _run_stage_trials(
            stage_name=stage_name,
            system_prompt=sys_p,
            user_prompt=usr_p,
            response_schema=schema,
            thinking_level=tier,
            trials=n_trials,
            timeout_seconds=55.0,
            max_retries=1,
        )
    return results


async def run_planner_ab_phase(rounds: int = 3) -> dict[str, Any]:
    planning_reg = build_planning_prompt_registry()
    planner_tpl = planning_reg.latest(MILESTONE_PLANNER_SKILL.skill_id)
    goals = _sample_planner_goals()
    tools = [
        LLMToolDeclarationDTO(
            name="search_learning_concepts",
            description="Search verified learning concepts in FocusFlow catalog.",
            parameters_schema={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        ),
        LLMToolDeclarationDTO(
            name="get_concept_prerequisite_graph",
            description="Inspect prerequisite edges among learning concepts.",
            parameters_schema={
                "type": "object",
                "properties": {"concept_ids": {"type": "array", "items": {"type": "string"}}},
            },
        ),
    ]

    arms: dict[str, Any] = {}
    for tier in ("LOW", "MEDIUM"):
        arm_key = tier.lower()
        print(f"\n[Planner A/B] Arm={arm_key} ({rounds} rounds x {len(goals)} goals)...", flush=True)
        runs: list[dict[str, Any]] = []
        for r_idx in range(1, rounds + 1):
            for g in goals:
                prompt = build_milestone_planner_prompt(
                    g["context"],
                    generation_strategy=g["strategy"],
                )
                adapter = LiteLLMAdapter()
                mgr = AIExecutionManager(
                    provider=adapter,
                    manage_quota=False,
                    timeout_seconds=55.0,
                    max_retries=1,
                )
                t0 = time.perf_counter()
                try:
                    res = await mgr.execute(
                        user_id=uuid4(),
                        operation_type="MILESTONE_PLANNER_AB",
                        system_prompt=planner_tpl.system_template,
                        user_prompt=prompt,
                        response_schema=MilestoneGenerationLLMOutput,
                        tools=tools,
                        tool_executor=_mock_planner_tool_executor,
                        max_tool_calls=MILESTONE_PLANNER_SKILL.max_tool_calls,
                        thinking_level=tier,
                    )
                    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
                    val_dict = (
                        res.value.model_dump()
                        if hasattr(res.value, "model_dump")
                        else dict(res.value)
                    )
                    raw_ms = val_dict.get("milestones", [])
                    violations = validate_ai_milestones_tier1(raw_ms)
                    is_valid = len(violations) == 0 and len(raw_ms) >= 1
                    concepts_count = sum(
                        len(m.get("required_concepts", [])) + len(m.get("unverified_concepts", []))
                        for m in raw_ms
                        if isinstance(m, dict)
                    )
                    outcomes_count = sum(
                        len(m.get("learning_outcomes", []))
                        for m in raw_ms
                        if isinstance(m, dict)
                    )
                    criteria_met = sum(
                        1
                        for m in raw_ms
                        if isinstance(m, dict) and bool(str(m.get("completion_criteria", "")).strip())
                    )
                    runs.append(
                        {
                            "round": r_idx,
                            "goal_id": g["id"],
                            "learner_level": g["learner_level"],
                            "ok": True,
                            "is_valid": is_valid,
                            "violations": [v.rule_code for v in violations],
                            "milestones_count": len(raw_ms),
                            "concepts_count": concepts_count,
                            "outcomes_count": outcomes_count,
                            "criteria_met_count": criteria_met,
                            "latency_ms": elapsed_ms,
                            "prompt_tokens": res.prompt_tokens,
                            "output_tokens": res.completion_tokens,
                            "thinking_tokens": res.thinking_tokens,
                            "model_id": res.model_id,
                        }
                    )
                    print(
                        f"  [planner][{arm_key}] R{r_idx} {g['id']}: valid={is_valid} ms={len(raw_ms)} "
                        f"concepts={concepts_count} {elapsed_ms:.0f}ms t_tok={res.thinking_tokens}",
                        flush=True,
                    )
                except Exception as exc:
                    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
                    cat = classify_ai_error(exc).value
                    err_msg = f"{cat}: {sanitize_error_message(exc)}"
                    runs.append(
                        {
                            "round": r_idx,
                            "goal_id": g["id"],
                            "learner_level": g["learner_level"],
                            "ok": False,
                            "is_valid": False,
                            "latency_ms": elapsed_ms,
                            "error": err_msg,
                        }
                    )
                    print(
                        f"  [planner][{arm_key}] R{r_idx} {g['id']}: FAIL {elapsed_ms:.0f}ms {err_msg[:120]}",
                        flush=True,
                    )

        base_summary = _summarize_runs(runs)
        valid_runs = [r for r in runs if r.get("is_valid")]
        ok_runs = [r for r in runs if r.get("ok")]
        ms_total = sum(int(r.get("milestones_count", 0)) for r in ok_runs)
        arms[arm_key] = {
            "summary": {
                **base_summary,
                "gate_valid_count": len(valid_runs),
                "gate_valid_rate": round(len(valid_runs) / max(1, len(runs)), 4),
                "milestones_avg": round(ms_total / max(1, len(ok_runs)), 2),
                "concepts_avg": round(
                    sum(int(r.get("concepts_count", 0)) for r in ok_runs) / max(1, len(ok_runs)), 2
                ),
                "outcomes_avg": round(
                    sum(int(r.get("outcomes_count", 0)) for r in ok_runs) / max(1, len(ok_runs)), 2
                ),
                "criteria_coverage_rate": round(
                    sum(int(r.get("criteria_met_count", 0)) for r in ok_runs) / max(1, ms_total), 4
                ),
            },
            "runs": runs,
        }
    return arms


async def run_decomposer_ab_phase(
    rounds: int = 3,
    *,
    report_container: dict[str, Any] | None = None,
) -> dict[str, Any]:
    # Ensure Judge uses `gemini-3.8-flash-low` (decided in 0.5) with generous 15s budget for A/B eval.
    # Weekly Review is excluded here (already measured standalone) to isolate Decomposer + Judge.
    arms: dict[str, Any] = {}
    for tier in ("LOW", "MEDIUM"):
        arm_key = tier.lower()
        arm_runs: list[dict[str, Any]] = []
        for r_idx in range(1, rounds + 1):
            print(
                f"\n[Decomposer A/B] Arm={arm_key} Run {r_idx}/{rounds} (18 goals sequential, include_weekly=False)...",
                flush=True,
            )
            t0 = time.perf_counter()
            rep = await run_planning_eval_suite(
                trials_per_goal=1,
                live=True,
                concurrency=1,
                decomposer_thinking_level=tier,
                judge_thinking_level="LOW",
                judge_timeout_seconds=15.0,
                include_weekly=False,
            )
            wall_s = round(time.perf_counter() - t0, 2)
            summary = {k: v for k, v in rep.items() if k != "per_case_outcomes"}
            summary["run_index"] = r_idx
            summary["wall_seconds"] = wall_s
            arm_runs.append(
                {
                    "run_index": r_idx,
                    "wall_seconds": wall_s,
                    "summary": summary,
                    "per_case_outcomes": rep["per_case_outcomes"],
                }
            )
            print(
                f"  [decomposer][{arm_key}] Run {r_idx}/{rounds} done in {wall_s}s: "
                f"pass@1={summary['pass_at_1']} post_retry={summary['post_retry_recovery_rate']} "
                f"judge_pass={summary['judge_passed_rate']} score_avg={summary['pedagogical_score_avg']} "
                f"p50={summary['latency_p50_ms']}ms p95={summary['latency_p95_ms']}ms "
                f"d_t_tok={summary['decomposer_thinking_tokens_total']} ({summary['decomposer_thinking_pct']*100:.1f}%)",
                flush=True,
            )
            if report_container is not None:
                arms[arm_key] = {"runs": list(arm_runs)}
                report_container["decomposer_low_vs_medium"] = arms
                _save_report(report_container)

        # Aggregate across the 3 runs
        summaries = [r["summary"] for r in arm_runs]
        scores = [s["pedagogical_score_avg"] for s in summaries if s["pedagogical_score_avg"] is not None]
        d_out_total = sum(int(s["decomposer_output_tokens_total"]) for s in summaries)
        d_think_total = sum(int(s["decomposer_thinking_tokens_total"]) for s in summaries)
        all_out_total = sum(int(s["output_tokens_total"]) for s in summaries)
        all_think_total = sum(int(s["thinking_tokens_total"]) for s in summaries)
        arms[arm_key] = {
            "aggregate": {
                "runs_count": len(arm_runs),
                "total_scenarios": sum(int(s["total_runs"]) for s in summaries),
                "pass_at_1_mean": round(statistics.mean(s["pass_at_1"] for s in summaries), 4),
                "post_retry_recovery_rate_mean": round(
                    statistics.mean(s["post_retry_recovery_rate"] for s in summaries), 4
                ),
                "judge_passed_rate_mean": round(
                    statistics.mean(s["judge_passed_rate"] for s in summaries), 4
                ),
                "judge_needs_review_rate_mean": round(
                    statistics.mean(s["judge_needs_review_rate"] for s in summaries), 4
                ),
                "judge_timeout_rate_mean": round(
                    statistics.mean(s["judge_timeout_rate"] for s in summaries), 4
                ),
                "pedagogical_score_avg_mean": round(statistics.mean(scores), 2) if scores else None,
                "avg_tasks_per_goal_mean": round(
                    statistics.mean(s["avg_tasks_per_goal"] for s in summaries), 2
                ),
                "min_tasks_met_rate_mean": round(
                    statistics.mean(s["min_tasks_met_rate"] for s in summaries), 4
                ),
                "latency_p50_ms_mean": round(
                    statistics.mean(s["latency_p50_ms"] for s in summaries), 2
                ),
                "latency_p95_ms_mean": round(
                    statistics.mean(s["latency_p95_ms"] for s in summaries), 2
                ),
                "latency_p95_ms_max": round(max(s["latency_p95_ms"] for s in summaries), 2),
                "decomposer_output_tokens_total": d_out_total,
                "decomposer_thinking_tokens_total": d_think_total,
                "decomposer_thinking_pct": (
                    round((d_think_total / d_out_total) * 100.0, 2) if d_out_total > 0 else 0.0
                ),
                "all_output_tokens_total": all_out_total,
                "all_thinking_tokens_total": all_think_total,
                "all_thinking_pct": (
                    round((all_think_total / all_out_total) * 100.0, 2)
                    if all_out_total > 0
                    else 0.0
                ),
                "weekly_fallback_rate_mean": round(
                    statistics.mean(s["weekly_fallback_rate"] for s in summaries), 4
                ),
            },
            "runs": arm_runs,
        }
    return arms


async def run_verify_phase() -> dict[str, Any]:
    """Part C: 3 consecutive live runs per stage verifying 0/3 timeout under locked Settings."""
    settings = get_settings()
    planning_reg = build_planning_prompt_registry()
    eval_reg = build_evaluation_prompt_registry()

    clarifier_tpl = planning_reg.latest(GOAL_CLARIFIER_SKILL.skill_id)
    followup_tpl = planning_reg.latest(GOAL_CLARIFIER_FOLLOWUP_PROMPT.prompt_id)
    planner_tpl = planning_reg.latest(MILESTONE_PLANNER_SKILL.skill_id)
    decomposer_tpl = planning_reg.latest(TASK_DECOMPOSER_SKILL.skill_id)
    cov_critic_tpl = planning_reg.latest(COVERAGE_PREREQUISITE_CRITIC_PROMPT.prompt_id)
    fit_critic_tpl = planning_reg.latest(LEARNER_FIT_CRITIC_PROMPT.prompt_id)
    arbiter_tpl = planning_reg.latest(QUALITY_ARBITER_PROMPT.prompt_id)
    judge_tpl = planning_reg.latest(PEDAGOGICAL_JUDGE_SKILL.skill_id)
    weekly_tpl = eval_reg.latest(WEEKLY_REVIEW_ADVISOR_PROMPT.prompt_id)
    prove_q_tpl = eval_reg.latest(PROVE_QUESTION_GENERATOR_PROMPT.prompt_id)
    prove_g_tpl = eval_reg.latest(PROVE_MODE_GRADER_PROMPT.prompt_id)

    sample_proposal = {
        "tasks": [
            {
                "task_id": "T1",
                "title": "Đọc tài liệu Pydantic v2 & Type Hints",
                "task_type": "THEORY",
                "estimated_minutes": 45,
                "covered_outcome_ids": ["M1-O1"],
                "learning_objective": "Hiểu cơ chế validate dữ liệu bằng Pydantic v2.",
                "completion_criteria": "Viết được 2 schema mẫu.",
            },
            {
                "task_id": "T2",
                "title": "Thực hành FastAPI Router & AsyncUnitOfWork",
                "task_type": "PRACTICE",
                "estimated_minutes": 60,
                "covered_outcome_ids": ["M1-O2"],
                "learning_objective": "Kết nối endpoint với use case qua Depends.",
                "completion_criteria": "Pass 3 test endpoint.",
            },
            {
                "task_id": "T3",
                "title": "Ôn tập và làm mini project CRUD",
                "task_type": "PROJECT",
                "estimated_minutes": 60,
                "covered_outcome_ids": ["M1-O1", "M1-O2"],
                "learning_objective": "Hoàn thiện module API độc lập.",
                "completion_criteria": "Chạy toàn bộ pytest xanh.",
            },
        ],
        "dependencies": [
            {"predecessor_id": "T1", "successor_id": "T2", "is_mandatory": True},
            {"predecessor_id": "T2", "successor_id": "T3", "is_mandatory": True},
        ],
    }

    planner_tools = [
        LLMToolDeclarationDTO(
            name="search_learning_concepts",
            description="Search verified learning concepts in FocusFlow catalog.",
            parameters_schema={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        ),
    ]

    verify_specs = [
        (
            "goal-clarifier",
            clarifier_tpl.system_template,
            build_goal_clarifier_prompt(
                goal_title="Học FastAPI trong 30 ngày",
                raw_description="Muốn làm REST API có auth và pytest.",
                prior_knowledge_level="BEGINNER",
                gap_count=2,
            ),
            ClarificationQuestionsLLMOutput,
            GOAL_CLARIFIER_SKILL.thinking_level,
            settings.ai_clarifier_timeout_seconds,
            None,
            None,
            0,
        ),
        (
            "goal-clarifier-followup",
            followup_tpl.system_template,
            build_goal_clarifier_followup_prompt(
                gap={"dimension": "TIME_COMMITMENT", "status": "PARTIAL", "priority": 85, "reason": "Chưa rõ số giờ mỗi tuần"},
                prior_answers=[{"question_id": "q1", "answer": "Đã biết Python cơ bản"}],
            ),
            ClarificationFollowupLLMOutput,
            GOAL_CLARIFIER_FOLLOWUP_PROMPT.thinking_level,
            settings.ai_clarifier_followup_timeout_seconds,
            None,
            None,
            0,
        ),
        (
            "learning-milestone-planner",
            planner_tpl.system_template,
            build_milestone_planner_prompt(
                "Goal: Tự học FastAPI & PostgreSQL trong 45 ngày.\nTrình độ: BEGINNER.\nQuỹ: 90p/ngày.",
                generation_strategy="FULL_SCOPE",
            ),
            MilestoneGenerationLLMOutput,
            MILESTONE_PLANNER_SKILL.thinking_level,
            settings.ai_milestone_planner_timeout_seconds,
            planner_tools,
            _mock_planner_tool_executor,
            2,
        ),
        (
            "learning-task-decomposer",
            decomposer_tpl.system_template,
            build_task_decomposer_prompt(
                "[USER_PROVIDED_FACTS]\nGoal: Tự học FastAPI & PostgreSQL trong 30 ngày.\n"
                "[SYSTEM_DERIVED_FACTS]\navailability: MODE_A 90m/day, window=2026-11-02..2026-12-01\n"
                "[MILESTONES]\nM1 (id=11111111-1111-1111-1111-111111111111): Pydantic v2 & Routing, effort=180m",
            ),
            TaskProposalLLMOutput,
            TASK_DECOMPOSER_SKILL.thinking_level,
            settings.ai_task_decomposer_timeout_seconds,
            None,
            None,
            0,
        ),
        (
            "coverage-prerequisite-critic",
            cov_critic_tpl.system_template,
            f"learner_level: BEGINNER\n[PAYLOAD]\n{json.dumps(sample_proposal, ensure_ascii=False)}",
            CRITIC_RESPONSE_SCHEMA,
            COVERAGE_PREREQUISITE_CRITIC_PROMPT.thinking_level,
            settings.ai_quality_critic_timeout_seconds,
            None,
            None,
            0,
        ),
        (
            "learner-fit-actionability-critic",
            fit_critic_tpl.system_template,
            f"learner_level: BEGINNER\n[PAYLOAD]\n{json.dumps(sample_proposal, ensure_ascii=False)}",
            CRITIC_RESPONSE_SCHEMA,
            LEARNER_FIT_CRITIC_PROMPT.thinking_level,
            settings.ai_quality_critic_timeout_seconds,
            None,
            None,
            0,
        ),
        (
            "quality-arbiter",
            arbiter_tpl.system_template,
            f"learner_level: BEGINNER\n[CRITIC_REPORTS]\n[]\n[PAYLOAD]\n{json.dumps(sample_proposal, ensure_ascii=False)}",
            CRITIC_RESPONSE_SCHEMA,
            QUALITY_ARBITER_PROMPT.thinking_level,
            settings.ai_quality_arbiter_timeout_seconds,
            None,
            None,
            0,
        ),
        (
            "pedagogical-quality-judge",
            judge_tpl.system_template,
            build_pedagogical_judge_prompt(
                sample_proposal,
                context_block="Mục tiêu: FastAPI Backend\nSố nhiệm vụ: 3",
                milestones_summary="M1: FastAPI Core",
                learner_level="BEGINNER",
            ),
            PEDAGOGICAL_JUDGE_RESPONSE_SCHEMA,
            PEDAGOGICAL_JUDGE_SKILL.thinking_level,
            settings.tier3_judge_timeout_seconds,
            None,
            None,
            0,
        ),
        (
            "weekly-review-advisor",
            weekly_tpl.system_template,
            build_weekly_review_prompt(
                quantitative_summary={
                    "completed_minutes": 180,
                    "planned_minutes": 240,
                    "completed_sessions_count": 4,
                    "completed_tasks_count": 3,
                    "planned_tasks_count": 4,
                    "overdue_tasks_count": 0,
                    "adherence_rate_pct": 75.0,
                },
                reflection={"summary": "Tuần này học ổn định."},
            ),
            WeeklyReviewLLMOutput,
            WEEKLY_REVIEW_ADVISOR_PROMPT.thinking_level,
            settings.ai_weekly_review_timeout_seconds,
            None,
            None,
            0,
        ),
        (
            "prove-question-generator",
            prove_q_tpl.system_template,
            build_prove_question_prompt(
                milestone_title="Cột mốc 1: FastAPI & Pydantic",
                learning_outcomes=["M1-O1: Phân biệt schema và domain"],
                required_concepts=["fastapi-routing-pydantic"],
            ),
            ProveQuestionsLLMOutput,
            PROVE_QUESTION_GENERATOR_PROMPT.thinking_level,
            settings.ai_prove_question_timeout_seconds,
            None,
            None,
            0,
        ),
        (
            "prove-mode-grader",
            prove_g_tpl.system_template,
            build_prove_grader_prompt(
                [
                    ("q1", "Phân biệt schema và domain model?", "Schema validate JSON HTTP, domain model giữ bất biến."),
                    ("q2", "Lỗi commit trong repo?", "Làm mất tính nguyên tử giao dịch, cần dùng UoW."),
                    ("q3", "Chống IDOR?", "Kiểm user_id và trả 404."),
                ]
            ),
            ProveGradingLLMOutput,
            PROVE_MODE_GRADER_PROMPT.thinking_level,
            settings.ai_prove_grader_timeout_seconds,
            None,
            None,
            0,
        ),
    ]

    out: dict[str, Any] = {}
    for stage_name, sys_p, usr_p, schema, tier, budget_s, tools, tool_exec, max_tc in verify_specs:
        print(f"\n[Verify 0/3] {stage_name} tier={tier} budget={budget_s}s...", flush=True)
        res = await _run_stage_trials(
            stage_name=stage_name,
            system_prompt=sys_p,
            user_prompt=usr_p,
            response_schema=schema,
            thinking_level=tier,
            trials=3,
            timeout_seconds=budget_s,
            max_retries=0,
            tools=tools,
            tool_executor=tool_exec,
            max_tool_calls=max_tc,
        )
        timeouts = sum(1 for r in res["runs"] if r.get("error_category") == "TIMEOUT")
        res["timeouts_count"] = timeouts
        res["zero_of_three_timeout"] = timeouts == 0 and res["summary"]["success_count"] == 3
        out[stage_name] = res
    return out


async def async_main() -> None:
    parser = argparse.ArgumentParser(description="Group 2 cobhub stage measurements & A/B suite.")
    parser.add_argument(
        "--phase",
        choices=("stages", "planner_ab", "decomposer_ab", "verify", "all"),
        default="stages",
    )
    parser.add_argument("--stage-trials", type=int, default=8)
    parser.add_argument("--ab-rounds", type=int, default=3)
    args = parser.parse_args()

    base_url, _ = get_cobhub_config()
    _configure_env(base_url)

    report = _load_existing()

    if args.phase in ("stages", "all"):
        report["stage_measurements"] = await run_stages_phase(trials=args.stage_trials)
        _save_report(report)

    if args.phase in ("planner_ab", "all"):
        report["planner_low_vs_medium"] = await run_planner_ab_phase(rounds=args.ab_rounds)
        _save_report(report)

    if args.phase in ("decomposer_ab", "all"):
        report["decomposer_low_vs_medium"] = await run_decomposer_ab_phase(
            rounds=args.ab_rounds,
            report_container=report,
        )
        _save_report(report)

    if args.phase in ("verify", "all"):
        report["part_c_verify_0_of_3"] = await run_verify_phase()
        _save_report(report)

    print(f"\nSaved measurements to {OUTPUT_PATH}", flush=True)


if __name__ == "__main__":
    asyncio.run(async_main())
