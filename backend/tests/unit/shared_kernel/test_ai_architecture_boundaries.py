"""AST architecture boundary tests ensuring LLM calls route exclusively through AIExecutionManager."""

from __future__ import annotations

import ast
from pathlib import Path

_SRC_ROOT = Path(__file__).resolve().parents[3] / "src"

_ALLOWED_GENERATE_STRUCTURED_CALLERS: frozenset[str] = frozenset(
    {
        "shared_kernel/application/harness/execution_manager.py",
        "shared_kernel/infrastructure/external_ai/circuit_breaker.py",
        "shared_kernel/infrastructure/external_ai/litellm_adapter.py",
    }
)


def find_generate_structured_calls(source: str, filename: str = "<string>") -> list[int]:
    """Return 1-based line numbers of all `.generate_structured(...)` calls in `source`."""
    tree = ast.parse(source, filename=filename)
    lines: list[int] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "generate_structured"
        ):
            lines.append(node.lineno)
    return sorted(lines)


def test_generate_structured_only_called_inside_allowed_harness_files() -> None:
    """Forbid calling `.generate_structured(...)` anywhere in `backend/src/` outside the harness."""
    assert _SRC_ROOT.is_dir()

    violations: list[str] = []
    execution_manager_calls = 0

    for py_file in sorted(_SRC_ROOT.rglob("*.py")):
        rel_path = py_file.relative_to(_SRC_ROOT).as_posix()
        source = py_file.read_text(encoding="utf-8")
        call_lines = find_generate_structured_calls(source, filename=rel_path)
        if not call_lines:
            continue
        if rel_path == "shared_kernel/application/harness/execution_manager.py":
            execution_manager_calls += len(call_lines)
        if rel_path not in _ALLOWED_GENERATE_STRUCTURED_CALLERS:
            for lineno in call_lines:
                violations.append(f"{rel_path}:{lineno}")

    assert execution_manager_calls >= 1
    assert violations == [], (
        "Direct `.generate_structured(...)` calls found outside AIExecutionManager / harness: "
        + ", ".join(violations)
    )


def test_generate_structured_ast_detector_catches_violations() -> None:
    """Ensure the AST detector does not silently pass when an unauthorized call exists."""
    sample = """
async def bad_use_case(llm):
    return await llm.generate_structured(system_prompt="s", user_prompt="u")
"""
    assert find_generate_structured_calls(sample, "planning/bad.py") == [3]
