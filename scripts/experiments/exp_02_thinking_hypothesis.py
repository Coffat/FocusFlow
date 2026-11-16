"""Experiment 0.2: Thinking hypothesis test on cobhub (A..F interleaved round-robin x 10 rounds = 60 calls)."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from common import (
    build_cobhub_client,
    build_genai_config,
    extract_response_telemetry,
    get_cobhub_config,
    get_prompt_template,
    parse_json_text,
    sanitize_error_message,
    summarize_numeric,
    utc_timestamp,
    write_experiment_json,
)

from src.planning.application.dtos.planning_dtos import ClarificationQuestionsLLMOutput
from src.planning.application.services.roadmap_skills import (
    GOAL_CLARIFIER_SKILL,
    build_goal_clarifier_prompt,
)

ARMS: list[dict[str, Any]] = [
    {"arm": "A", "model": "gemini-3.8-flash", "thinking_level": "LOW"},
    {"arm": "B", "model": "gemini-3.8-flash-low", "thinking_level": None},
    {"arm": "C", "model": "gemini-3.8-flash", "thinking_level": "HIGH"},
    {"arm": "D", "model": "gemini-3.8-flash-high", "thinking_level": None},
    {"arm": "E", "model": "gemini-3.8-flash", "thinking_level": None},
    {"arm": "F", "model": "gemini-3.8-flash-tiered", "thinking_level": None},
]


async def main() -> None:
    base_url, _ = get_cobhub_config()
    client = build_cobhub_client()
    tpl = get_prompt_template(GOAL_CLARIFIER_SKILL.skill_id)
    user_prompt = build_goal_clarifier_prompt(
        goal_title="Làm chủ Python Asyncio & FastAPI Production",
        raw_description=(
            "Mình đã biết Python cơ bản và viết script đơn giản, muốn học sâu asyncio, "
            "SQLAlchemy 2.0 async, thiết kế API chuẩn production trong 6 tuần."
        ),
        prior_knowledge_level="BEGINNER",
        target_date_iso="2026-12-28",
        known_dimensions=(),
        gap_count=3,
    )
    schema_dict = ClarificationQuestionsLLMOutput.model_json_schema()

    runs: list[dict[str, Any]] = []
    rounds = 10

    for round_idx in range(1, rounds + 1):
        for arm_spec in ARMS:
            arm = arm_spec["arm"]
            model = arm_spec["model"]
            thinking_level = arm_spec["thinking_level"]
            cfg = build_genai_config(
                system_instruction=tpl.system_template,
                response_mime_type="application/json",
                response_json_schema=schema_dict,
                max_output_tokens=32768,
                thinking_level=thinking_level,
            )

            t0 = time.perf_counter()
            ok = False
            schema_valid = False
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
                    timeout=60.0,
                )
                telemetry = extract_response_telemetry(resp, model)
                parsed = parse_json_text(getattr(resp, "text", None))
                ok = True
                try:
                    ClarificationQuestionsLLMOutput.model_validate(parsed)
                    schema_valid = True
                except Exception:
                    schema_valid = False
            except Exception as exc:
                error_type = type(exc).__name__
                error_message = sanitize_error_message(exc)
            elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 3)

            record = {
                "round": round_idx,
                "arm": arm,
                "requested_model": model,
                "thinking_level_sent": thinking_level,
                "latency_ms": elapsed_ms,
                "ok": ok,
                "schema_valid": schema_valid,
                **telemetry,
                "error_type": error_type,
                "error_message": error_message,
            }
            runs.append(record)
            print(
                f"[0.2] r={round_idx:02d}/10 arm={arm} model={model} level={thinking_level} "
                f"ok={ok} valid={schema_valid} ms={elapsed_ms:.1f} "
                f"t_tok={telemetry['thinking_tokens']} tot_tok={telemetry['total_tokens']} "
                f"actual={telemetry['actual_model_id']}",
                flush=True,
            )

    summary_by_arm: dict[str, Any] = {}
    for arm_spec in ARMS:
        arm = arm_spec["arm"]
        arm_runs = [r for r in runs if r["arm"] == arm]
        ok_runs = [r for r in arm_runs if r["ok"]]
        summary_by_arm[arm] = {
            "requested_model": arm_spec["model"],
            "thinking_level_sent": arm_spec["thinking_level"],
            "total_calls": len(arm_runs),
            "success_count": len(ok_runs),
            "schema_valid_count": sum(1 for r in arm_runs if r["schema_valid"]),
            "actual_model_ids": sorted({r["actual_model_id"] for r in ok_runs}),
            "latency_ms": summarize_numeric([r["latency_ms"] for r in ok_runs]),
            "thinking_tokens": summarize_numeric([float(r["thinking_tokens"]) for r in ok_runs]),
            "candidate_tokens": summarize_numeric([float(r["candidate_tokens"]) for r in ok_runs]),
            "total_tokens": summarize_numeric([float(r["total_tokens"]) for r in ok_runs]),
        }

    report = {
        "experiment": "0.2_thinking_hypothesis",
        "timestamp": utc_timestamp(),
        "base_url": base_url,
        "prompt_id": GOAL_CLARIFIER_SKILL.skill_id,
        "rounds": rounds,
        "total_calls": len(runs),
        "summary_by_arm": summary_by_arm,
        "runs": runs,
    }
    out = write_experiment_json("exp_02_thinking_hypothesis.json", report)
    print(f"Saved: {out}")


if __name__ == "__main__":
    asyncio.run(main())
