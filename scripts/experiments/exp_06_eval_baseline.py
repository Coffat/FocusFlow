"""Experiment 0.6: Run 18-goal planning eval suite sequentially against cobhub (BEFORE baseline)."""

from __future__ import annotations

import asyncio
import json
import os
import time
from typing import Any

from common import EXPERIMENTS_OUT_DIR, get_cobhub_config, utc_timestamp

from src.planning.application.services.validation_gate import ProposalValidationGateOrchestrator
from src.shared_kernel.config import get_settings
from tests.ai_evals.eval_runner import run_planning_eval_suite


async def main() -> None:
    base_url, _ = get_cobhub_config()
    os.environ["LLM_PROVIDER"] = "gemini"
    os.environ["LLM_MODEL"] = os.getenv("LLM_MODEL_OVERRIDE") or "gemini-3.8-flash"
    os.environ["LLM_BASE_URL"] = base_url
    get_settings.cache_clear()

    # Non-intrusive progress logger around orchestrator calls (does not alter behavior or inputs)
    orig_gen = ProposalValidationGateOrchestrator.generate_and_validate_proposal_with_retry
    counter = {"idx": 0}

    async def _logged_gen(self: Any, *args: Any, **kwargs: Any) -> Any:
        counter["idx"] += 1
        cur = counter["idx"]
        goal_title = str(kwargs.get("goal_title", ""))[:60]
        t0 = time.perf_counter()
        print(f"[0.6] Scenario {cur:02d}/18 START: {goal_title}", flush=True)
        try:
            res = await orig_gen(self, *args, **kwargs)
            elapsed = time.perf_counter() - t0
            print(
                f"[0.6] Scenario {cur:02d}/18 DONE in {elapsed:.1f}s: "
                f"is_valid={res.is_valid} attempts={res.attempts_used} "
                f"p_tok={res.total_prompt_tokens} c_tok={res.total_completion_tokens} "
                f"t_tok={res.total_thinking_tokens}",
                flush=True,
            )
            return res
        except Exception as exc:
            elapsed = time.perf_counter() - t0
            print(
                f"[0.6] Scenario {cur:02d}/18 FAIL in {elapsed:.1f}s: "
                f"{type(exc).__name__}: {str(exc)[:120]}",
                flush=True,
            )
            raise

    ProposalValidationGateOrchestrator.generate_and_validate_proposal_with_retry = _logged_gen  # type: ignore[method-assign]

    settings = get_settings()
    out_path = EXPERIMENTS_OUT_DIR / "exp_06_eval_baseline.json"
    print(
        f"[0.6] Starting live sequential 18-goal eval baseline: "
        f"provider={settings.llm_provider} model={settings.llm_model} "
        f"base_url={settings.llm_base_url}",
        flush=True,
    )
    t0 = time.perf_counter()
    report = await run_planning_eval_suite(
        trials_per_goal=1,
        output_path=out_path,
        live=True,
    )
    elapsed_s = round(time.perf_counter() - t0, 2)
    report["timestamp"] = utc_timestamp()
    report["total_wall_seconds"] = elapsed_s
    report["requested_model"] = settings.llm_model
    report["base_url"] = settings.llm_base_url
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summary = {k: v for k, v in report.items() if k != "per_case_outcomes"}
    print(f"[0.6] Completed in {elapsed_s}s. Saved: {out_path}", flush=True)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
