"""Experiment 0.1: Cobhub gateway baseline latency (10 sequential minimal calls)."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from common import (
    build_cobhub_client,
    build_genai_config,
    extract_response_telemetry,
    get_cobhub_config,
    parse_json_text,
    sanitize_error_message,
    summarize_numeric,
    utc_timestamp,
    write_experiment_json,
)


async def main() -> None:
    base_url, _ = get_cobhub_config()
    client = build_cobhub_client()
    model = "gemini-3.8-flash"
    thinking_level = "MEDIUM"
    prompt = 'Trả về JSON {"ok":true}'

    cfg = build_genai_config(
        response_mime_type="application/json",
        max_output_tokens=32768,
        thinking_level=thinking_level,
    )

    runs: list[dict[str, Any]] = []
    latencies_ms: list[float] = []

    for idx in range(1, 11):
        t0 = time.perf_counter()
        ok = False
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
        parsed_ok = False
        try:
            resp = await asyncio.wait_for(
                client.aio.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=cfg,
                ),
                timeout=35.0,
            )
            telemetry = extract_response_telemetry(resp, model)
            parsed = parse_json_text(getattr(resp, "text", None))
            parsed_ok = isinstance(parsed, dict) and parsed.get("ok") is True
            ok = parsed_ok
            if not ok:
                error_type = "SchemaMismatch"
                error_message = f"Unexpected JSON payload: {parsed!r}"
        except Exception as exc:
            error_type = type(exc).__name__
            error_message = sanitize_error_message(exc)
        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 3)
        latencies_ms.append(elapsed_ms)

        record = {
            "call_index": idx,
            "requested_model": model,
            "thinking_level_sent": thinking_level,
            "latency_ms": elapsed_ms,
            "ok": ok,
            "parsed_ok": parsed_ok,
            **telemetry,
            "error_type": error_type,
            "error_message": error_message,
        }
        runs.append(record)
        print(
            f"[0.1] call={idx:02d}/10 ok={ok} latency_ms={elapsed_ms:.1f} "
            f"actual_model={telemetry['actual_model_id']} "
            f"p_tok={telemetry['prompt_tokens']} c_tok={telemetry['candidate_tokens']} "
            f"t_tok={telemetry['thinking_tokens']}",
            flush=True,
        )

    ok_latencies = [r["latency_ms"] for r in runs if r["ok"]]
    report = {
        "experiment": "0.1_cobhub_baseline",
        "timestamp": utc_timestamp(),
        "base_url": base_url,
        "requested_model": model,
        "thinking_level_sent": thinking_level,
        "total_calls": len(runs),
        "success_count": sum(1 for r in runs if r["ok"]),
        "latency_ms_all": summarize_numeric(latencies_ms),
        "latency_ms_ok": summarize_numeric(ok_latencies),
        "prompt_tokens_stats": summarize_numeric([float(r["prompt_tokens"]) for r in runs]),
        "candidate_tokens_stats": summarize_numeric([float(r["candidate_tokens"]) for r in runs]),
        "thinking_tokens_stats": summarize_numeric([float(r["thinking_tokens"]) for r in runs]),
        "total_tokens_stats": summarize_numeric([float(r["total_tokens"]) for r in runs]),
        "runs": runs,
    }
    out = write_experiment_json("exp_01_cobhub_baseline.json", report)
    print(f"Saved: {out}")
    print("Summary latency_ms_all:", report["latency_ms_all"])


if __name__ == "__main__":
    asyncio.run(main())
