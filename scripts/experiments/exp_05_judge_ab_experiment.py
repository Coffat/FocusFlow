"""Experiment 0.5: Tier 3 Pedagogical Judge A/B test with compact payload (LOW vs MEDIUM suffix vs Base)."""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from common import (
    build_cobhub_client,
    build_genai_config,
    extract_response_telemetry,
    get_cobhub_config,
    get_prompt_template,
    parse_json_text,
    render_compact_schema_spec,
    sanitize_error_message,
    summarize_numeric,
    utc_timestamp,
    write_experiment_json,
)

from src.planning.application.dtos.planning_dtos import PedagogicalJudgeLLMOutput
from src.planning.application.services.roadmap_skills import (
    PEDAGOGICAL_JUDGE_SKILL,
    build_pedagogical_judge_prompt,
)

ARMS: list[dict[str, Any]] = [
    {"arm": "LOW_SUFFIX", "model": "gemini-3.8-flash-low", "thinking_level": "LOW"},
    {"arm": "MEDIUM_SUFFIX", "model": "gemini-3.8-flash-medium", "thinking_level": "MEDIUM"},
    {"arm": "BASE_MEDIUM", "model": "gemini-3.8-flash", "thinking_level": "MEDIUM"},
]


def _compact_proposal_for_judge(full_proposal: dict[str, Any]) -> dict[str, Any]:
    """Strip internal/redundant fields while keeping deps, outcomes, criteria, milestones summary."""
    raw_deps = [
        {
            "predecessor_id": str(d.get("predecessor_id", "")),
            "successor_id": str(d.get("successor_id", "")),
            "is_mandatory": bool(d.get("is_mandatory", True)),
        }
        for d in (full_proposal.get("dependencies") or [])
        if isinstance(d, dict)
    ]
    preds_by_task: dict[str, list[str]] = {}
    for dep in raw_deps:
        succ = dep["successor_id"]
        pred = dep["predecessor_id"]
        if succ and pred:
            preds_by_task.setdefault(succ, []).append(pred)

    compact_tasks: list[dict[str, Any]] = []
    for t in full_proposal.get("tasks") or []:
        if not isinstance(t, dict):
            continue
        tid = str(t.get("task_id", ""))
        compact_tasks.append(
            {
                "task_id": tid,
                "milestone_id": str(t.get("milestone_id", "")),
                "title": str(t.get("title", "")),
                "task_type": str(t.get("task_type", "")),
                "estimated_minutes": t.get("estimated_minutes"),
                "scheduled_date": t.get("scheduled_date"),
                "learning_objective": str(t.get("learning_objective", "")),
                "completion_criteria": str(t.get("completion_criteria", "")),
                "covered_outcome_ids": list(t.get("covered_outcome_ids") or []),
                "depends_on_task_ids": list(
                    t.get("depends_on_task_ids") or preds_by_task.get(tid, [])
                ),
            }
        )

    return {
        "tasks": compact_tasks,
        "dependencies": raw_deps,
    }


def _build_sample_cases() -> list[dict[str, Any]]:
    milestones_summary = json.dumps(
        [
            {
                "milestone_id": "m1",
                "sequence_order": 1,
                "title": "Chặng 1: Nền tảng Python & FastAPI",
                "learning_outcomes": [
                    "M1-O1: Nắm vững kiểu dữ liệu, hàm và type hints Python",
                    "M1-O2: Xây dựng REST API CRUD với FastAPI và Pydantic v2",
                ],
                "completion_criteria": "Hoàn thành API CRUD có kiểm thử validation và tài liệu OpenAPI.",
            }
        ],
        ensure_ascii=False,
    )

    good_raw = {
        "tasks": [
            {
                "task_id": "T1",
                "milestone_id": "m1",
                "title": "Học cú pháp Python, type hints và Pydantic BaseModel",
                "description": "Internal long description stripped...",
                "task_type": "THEORY",
                "estimated_minutes": 60,
                "scheduled_date": "2026-11-18",
                "learning_objective": "Hiểu rõ kiểu dữ liệu Python và cơ chế validate của Pydantic v2.",
                "completion_criteria": "Viết được 3 model Pydantic có validator và pass ví dụ mẫu.",
                "covered_outcome_ids": ["M1-O1"],
                "resource_ids": ["res-1"],
            },
            {
                "task_id": "T2",
                "milestone_id": "m1",
                "title": "Thực hành viết endpoint FastAPI CRUD kết hợp Pydantic",
                "description": "Internal long description stripped...",
                "task_type": "PRACTICE",
                "estimated_minutes": 90,
                "scheduled_date": "2026-11-19",
                "learning_objective": "Xây dựng các route GET/POST/PUT/DELETE có schema request/response.",
                "completion_criteria": "Chạy thành công 4 endpoint trên Swagger UI với HTTP status chuẩn.",
                "covered_outcome_ids": ["M1-O2"],
            },
            {
                "task_id": "T3",
                "milestone_id": "m1",
                "title": "Ôn tập kiến thức HTTP status và kiểm thử API",
                "task_type": "REVIEW",
                "estimated_minutes": 45,
                "scheduled_date": "2026-11-20",
                "learning_objective": "Củng cố xử lý lỗi validation 422 và 404 trong FastAPI.",
                "completion_criteria": "Tự giải thích được sự khác nhau giữa 400, 404 và 422 kèm test case.",
                "covered_outcome_ids": ["M1-O1", "M1-O2"],
            },
            {
                "task_id": "T4",
                "milestone_id": "m1",
                "title": "Dự án mini: API quản lý ghi chú học tập hoàn chỉnh",
                "task_type": "PROJECT",
                "estimated_minutes": 90,
                "scheduled_date": "2026-11-21",
                "learning_objective": "Tổng hợp kiến thức Python, Pydantic và FastAPI vào ứng dụng hoàn chỉnh.",
                "completion_criteria": "Hoàn thành CRUD ghi chú, kiểm thử pytest đạt >= 90% pass.",
                "covered_outcome_ids": ["M1-O1", "M1-O2"],
            },
        ],
        "dependencies": [
            {"predecessor_id": "T1", "successor_id": "T2", "is_mandatory": True},
            {"predecessor_id": "T2", "successor_id": "T3", "is_mandatory": True},
            {"predecessor_id": "T3", "successor_id": "T4", "is_mandatory": True},
        ],
        "quality_reviews": [{"critic": "internal", "status": "PASS"}],
        "schedule_blocks": [{"block": "internal-noise"}],
        "_capacity_overflow": {"available_minutes": 600},
    }

    flawed_raw = {
        "tasks": [
            {
                "task_id": "T1",
                "milestone_id": "m1",
                "title": "Xây dựng dự án API FastAPI production hoàn chỉnh",
                "task_type": "PROJECT",
                "estimated_minutes": 90,
                "scheduled_date": "2026-11-18",
                "learning_objective": "Làm quen.",
                "completion_criteria": "Xong.",
                "covered_outcome_ids": ["M1-O2"],
            },
            {
                "task_id": "T2",
                "milestone_id": "m1",
                "title": "Đọc lý thuyết biến và kiểu dữ liệu Python cơ bản",
                "task_type": "THEORY",
                "estimated_minutes": 60,
                "scheduled_date": "2026-11-19",
                "learning_objective": "Xem qua biến Python.",
                "completion_criteria": "Đọc hết bài.",
                "covered_outcome_ids": ["M1-O1"],
            },
            {
                "task_id": "T3",
                "milestone_id": "m1",
                "title": "Đọc thêm tài liệu nâng cao về FastAPI",
                "task_type": "THEORY",
                "estimated_minutes": 60,
                "scheduled_date": "2026-11-20",
                "learning_objective": "Biết thêm.",
                "completion_criteria": "Đọc xong.",
                "covered_outcome_ids": ["M1-O2"],
            },
        ],
        # Inverted dependency: PROJECT T1 comes BEFORE THEORY T2! And no PRACTICE/REVIEW at all.
        "dependencies": [
            {"predecessor_id": "T1", "successor_id": "T2", "is_mandatory": True},
            {"predecessor_id": "T2", "successor_id": "T3", "is_mandatory": True},
        ],
        "quality_reviews": [{"critic": "internal"}],
    }

    return [
        {
            "proposal_kind": "good_proposal",
            "expected_verdict": "PASS",
            "learner_level": "BEGINNER",
            "milestones_summary": milestones_summary,
            "compact_payload": _compact_proposal_for_judge(good_raw),
            "goal_title": "Nền tảng Python & FastAPI cho người mới bắt đầu",
        },
        {
            "proposal_kind": "flawed_proposal",
            "expected_verdict": "FAIL",
            "learner_level": "BEGINNER",
            "milestones_summary": milestones_summary,
            "compact_payload": _compact_proposal_for_judge(flawed_raw),
            "goal_title": "Nền tảng Python & FastAPI cho người mới bắt đầu",
        },
    ]


async def main() -> None:
    base_url, _ = get_cobhub_config()
    client = build_cobhub_client()
    judge_tpl = get_prompt_template(PEDAGOGICAL_JUDGE_SKILL.skill_id)
    compact_schema_spec = render_compact_schema_spec(PedagogicalJudgeLLMOutput)
    system_instruction = (
        f"{judge_tpl.system_template}\n\n"
        "[OUTPUT_JSON_SCHEMA]: Chỉ trả về DUY NHẤT JSON khớp chính xác các trường sau:\n"
        f"{compact_schema_spec}"
    )
    schema_dict = PedagogicalJudgeLLMOutput.model_json_schema()
    cases = _build_sample_cases()

    rounds = 5  # 5 rounds x 2 proposals = 10 calls per arm (30 total)
    runs: list[dict[str, Any]] = []

    for round_idx in range(1, rounds + 1):
        for case in cases:
            user_prompt = build_pedagogical_judge_prompt(
                case["compact_payload"],
                context_block=(
                    f"Mục tiêu: {case['goal_title']}\n"
                    f"Số nhiệm vụ: {len(case['compact_payload']['tasks'])}"
                ),
                milestones_summary=case["milestones_summary"],
                learner_level=case["learner_level"],
            )
            for arm_spec in ARMS:
                arm = arm_spec["arm"]
                model = arm_spec["model"]
                thinking_level = arm_spec["thinking_level"]
                cfg = build_genai_config(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_json_schema=schema_dict,
                    max_output_tokens=32768,
                    thinking_level=thinking_level,
                )

                t0 = time.perf_counter()
                ok = False
                schema_valid = False
                verdict: str | None = None
                score: int | None = None
                issues_count = 0
                verdict_matches_expected = False
                error_type: str | None = None
                error_message: str | None = None
                telemetry: dict[str, Any] = {
                    "actual_model_id": model,
                    "prompt_tokens": 0,
                    "candidate_tokens": 0,
                    "thinking_tokens": 0,
                    "total_tokens": 0,
                    "finish_reason": None,
                }
                try:
                    resp = await asyncio.wait_for(
                        client.aio.models.generate_content(
                            model=model,
                            contents=user_prompt,
                            config=cfg,
                        ),
                        timeout=45.0,
                    )
                    telemetry = extract_response_telemetry(resp, model)
                    parsed = parse_json_text(getattr(resp, "text", None))
                    validated = PedagogicalJudgeLLMOutput.model_validate(parsed)
                    ok = True
                    schema_valid = True
                    score = validated.score
                    issues_count = len(validated.issues)
                    verdict = validated.derive_status()
                    verdict_matches_expected = verdict == case["expected_verdict"]
                except Exception as exc:
                    error_type = type(exc).__name__
                    error_message = sanitize_error_message(exc)
                elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 3)

                rec = {
                    "round": round_idx,
                    "proposal_kind": case["proposal_kind"],
                    "expected_verdict": case["expected_verdict"],
                    "arm": arm,
                    "requested_model": model,
                    "thinking_level_sent": thinking_level,
                    "latency_ms": elapsed_ms,
                    "ok": ok,
                    "schema_valid": schema_valid,
                    "score": score,
                    "verdict": verdict,
                    "issues_count": issues_count,
                    "verdict_matches_expected": verdict_matches_expected,
                    **telemetry,
                    "error_type": error_type,
                    "error_message": error_message,
                }
                runs.append(rec)
                print(
                    f"[0.5] r={round_idx}/{rounds} case={case['proposal_kind']} arm={arm} "
                    f"ok={ok} score={score} verdict={verdict} match={verdict_matches_expected} "
                    f"ms={elapsed_ms:.1f} t_tok={telemetry['thinking_tokens']}",
                    flush=True,
                )

    summary_by_arm: dict[str, Any] = {}
    for arm_spec in ARMS:
        arm = arm_spec["arm"]
        arm_runs = [r for r in runs if r["arm"] == arm]
        ok_runs = [r for r in arm_runs if r["ok"]]
        good_runs = [r for r in ok_runs if r["proposal_kind"] == "good_proposal"]
        flawed_runs = [r for r in ok_runs if r["proposal_kind"] == "flawed_proposal"]
        summary_by_arm[arm] = {
            "requested_model": arm_spec["model"],
            "thinking_level_sent": arm_spec["thinking_level"],
            "total_calls": len(arm_runs),
            "success_count": len(ok_runs),
            "verdict_accuracy_overall": round(
                sum(1 for r in ok_runs if r["verdict_matches_expected"]) / max(1, len(arm_runs)),
                3,
            ),
            "good_proposal_pass_count": sum(1 for r in good_runs if r["verdict"] == "PASS"),
            "good_proposal_total": len([r for r in arm_runs if r["proposal_kind"] == "good_proposal"]),
            "flawed_proposal_fail_count": sum(1 for r in flawed_runs if r["verdict"] == "FAIL"),
            "flawed_proposal_total": len(
                [r for r in arm_runs if r["proposal_kind"] == "flawed_proposal"]
            ),
            "under_8s_rate": round(
                sum(1 for r in ok_runs if r["latency_ms"] <= 8000.0) / max(1, len(arm_runs)),
                3,
            ),
            "latency_ms": summarize_numeric([r["latency_ms"] for r in ok_runs]),
            "thinking_tokens": summarize_numeric([float(r["thinking_tokens"]) for r in ok_runs]),
            "total_tokens": summarize_numeric([float(r["total_tokens"]) for r in ok_runs]),
        }

    report = {
        "experiment": "0.5_judge_ab_experiment",
        "timestamp": utc_timestamp(),
        "base_url": base_url,
        "rounds": rounds,
        "total_calls": len(runs),
        "summary_by_arm": summary_by_arm,
        "runs": runs,
    }
    out = write_experiment_json("exp_05_judge_ab_experiment.json", report)
    print(f"Saved: {out}")


if __name__ == "__main__":
    asyncio.run(main())
