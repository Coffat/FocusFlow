"""Generate or verify `backend/prompts.lock` against the live production PromptRegistries (T7.2).

Usage:
    python scripts/update_prompts_lock.py          # Update backend/prompts.lock
    python scripts/update_prompts_lock.py --check  # Fail non-zero on drift (for CI)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from src.evaluation.application.prompts import build_evaluation_prompt_registry  # noqa: E402
from src.planning.application.services.roadmap_skills import (  # noqa: E402
    build_planning_prompt_registry,
)
from src.shared_kernel.application.harness.prompt_registry import PromptRegistry  # noqa: E402

DEFAULT_LOCK_PATH = BACKEND_ROOT / "prompts.lock"


def build_combined_production_registry() -> PromptRegistry:
    """Combine all bounded-context PromptRegistries without cross-context imports in `src/`."""
    return PromptRegistry.merge(
        build_planning_prompt_registry(),
        build_evaluation_prompt_registry(),
    )


def render_prompts_lock_payload(registry: PromptRegistry | None = None) -> dict[str, Any]:
    """Build canonical, sorted JSON payload for `prompts.lock`."""
    reg = registry or build_combined_production_registry()
    entries = [
        {
            "prompt_id": tpl.prompt_id,
            "version": tpl.version,
            "workflow_type": tpl.workflow_type,
            "skill_id": tpl.skill_id,
            "prompt_checksum": tpl.checksum,
            "schema_checksum": tpl.schema_checksum,
        }
        for tpl in reg.list_templates()
    ]
    return {
        "schema_version": 1,
        "prompt_count": len(entries),
        "prompts": entries,
    }


def serialize_prompts_lock(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def check_prompts_lock(lock_path: Path = DEFAULT_LOCK_PATH) -> tuple[bool, str]:
    """Return `(is_in_sync, message)` comparing `prompts.lock` against live registries."""
    expected_text = serialize_prompts_lock(render_prompts_lock_payload())
    if not lock_path.exists():
        return False, f"Missing lockfile: {lock_path}"
    actual_text = lock_path.read_text(encoding="utf-8")
    if actual_text != expected_text:
        return (
            False,
            "prompts.lock is out of sync with live PromptRegistry. "
            "Bump prompt version if intended and run `python scripts/update_prompts_lock.py`.",
        )
    return (
        True,
        f"prompts.lock matches live PromptRegistry ({len(render_prompts_lock_payload()['prompts'])} prompts).",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate or verify FocusFlow prompts.lock.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify prompts.lock matches live PromptRegistry without modifying disk.",
    )
    parser.add_argument(
        "--lock-path",
        type=Path,
        default=DEFAULT_LOCK_PATH,
        help="Path to prompts.lock (default: backend/prompts.lock).",
    )
    args = parser.parse_args(argv)

    if args.check:
        ok, msg = check_prompts_lock(args.lock_path)
        print(msg)
        return 0 if ok else 1

    payload = render_prompts_lock_payload()
    args.lock_path.write_text(serialize_prompts_lock(payload), encoding="utf-8")
    print(f"Updated {args.lock_path} with {payload['prompt_count']} production prompts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
