"""CI Drift & Inventory checks for `prompts.lock` and registry-backed production prompts (T7.1, T7.2)."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from scripts.update_prompts_lock import (
    DEFAULT_LOCK_PATH,
    build_combined_production_registry,
    check_prompts_lock,
    render_prompts_lock_payload,
)
from src.evaluation.application.prompts import (
    EVALUATION_PROMPT_SPECS,
    build_evaluation_prompt_registry,
)
from src.planning.application.services.roadmap_skills import (
    AUXILIARY_PLANNING_PROMPTS,
    ROADMAP_SKILL_REGISTRY,
    build_planning_prompt_registry,
)

EXPECTED_PRODUCTION_PROMPT_IDS: frozenset[str] = frozenset(
    {
        # Planning (9)
        "goal-clarifier",
        "goal-clarifier-followup",
        "learning-milestone-planner",
        "learning-task-decomposer",
        "proposal-self-correction",
        "pedagogical-quality-judge",
        "coverage-prerequisite-critic",
        "learner-fit-actionability-critic",
        "quality-arbiter",
        # Evaluation (3)
        "prove-question-generator",
        "prove-mode-grader",
        "weekly-review-advisor",
    }
)


def test_production_prompt_inventory_is_one_to_one_with_registries() -> None:
    """T7.1: Every production prompt is registered 1-to-1 across planning and evaluation registries."""
    planning_ids = {tpl.prompt_id for tpl in build_planning_prompt_registry().list_templates()}
    eval_ids = {tpl.prompt_id for tpl in build_evaluation_prompt_registry().list_templates()}
    assert planning_ids.isdisjoint(eval_ids)

    declared_planning = set(ROADMAP_SKILL_REGISTRY.keys()) | set(AUXILIARY_PLANNING_PROMPTS.keys())
    declared_eval = set(EVALUATION_PROMPT_SPECS.keys())
    assert planning_ids == declared_planning
    assert eval_ids == declared_eval

    combined = build_combined_production_registry()
    combined_ids = {tpl.prompt_id for tpl in combined.list_templates()}
    assert combined_ids == EXPECTED_PRODUCTION_PROMPT_IDS
    assert len(combined.list_templates()) == 12


def test_prompts_lock_matches_live_registry_and_detects_drift(tmp_path: Path) -> None:
    """T7.2: `backend/prompts.lock` matches live PromptRegistry 100%; any drift fails check."""
    ok, msg = check_prompts_lock(DEFAULT_LOCK_PATH)
    assert ok is True, msg

    lock_data = json.loads(DEFAULT_LOCK_PATH.read_text(encoding="utf-8"))
    assert lock_data["prompt_count"] == 12
    assert {item["prompt_id"] for item in lock_data["prompts"]} == EXPECTED_PRODUCTION_PROMPT_IDS

    # Simulate drift: prompt checksum changes without updating lockfile -> check MUST fail
    drifted = render_prompts_lock_payload()
    drifted["prompts"][0]["prompt_checksum"] = "0" * 64
    drifted_path = tmp_path / "prompts.lock"
    drifted_path.write_text(json.dumps(drifted, indent=2, sort_keys=True), encoding="utf-8")

    ok_drift, _ = check_prompts_lock(drifted_path)
    assert ok_drift is False


def test_no_inline_system_prompts_or_runtime_markdown_reads_in_src() -> None:
    """T7.1 & T7.4: No direct inline system_prompt string literals outside adapters and no `.md` runtime reads."""
    src_root = Path(__file__).resolve().parents[3] / "src"
    allowed_inline_files = {
        str(src_root / "shared_kernel" / "infrastructure" / "external_ai" / "litellm_adapter.py"),
    }

    inline_violations: list[str] = []
    md_runtime_reads: list[str] = []

    for py_file in sorted(src_root.rglob("*.py")):
        source = py_file.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(py_file))

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                for kw in node.keywords:
                    if kw.arg == "system_prompt" and isinstance(
                        kw.value, (ast.Constant, ast.JoinedStr)
                    ):
                        if (
                            isinstance(kw.value, ast.Constant)
                            and isinstance(kw.value.value, str)
                            and kw.value.value.strip() == ""
                        ):
                            continue
                        if str(py_file) not in allowed_inline_files:
                            inline_violations.append(f"{py_file.name}:{node.lineno}")
                    if kw.arg == "system_prompt" and isinstance(kw.value, ast.BinOp):
                        if str(py_file) not in allowed_inline_files:
                            inline_violations.append(f"{py_file.name}:{node.lineno}")

            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and ".md" in node.value.lower()
                and any(tok in source for tok in ("read_text", "open("))
            ):
                # Ignore benign docstrings/comments; flag actual file-path literals ending in .md
                if node.value.lower().endswith(".md"):
                    md_runtime_reads.append(f"{py_file.name}:{node.lineno}")

    assert inline_violations == [], f"Found inline system_prompt(s): {inline_violations}"
    assert md_runtime_reads == [], f"Found runtime .md path literal(s): {md_runtime_reads}"
