import re
from pathlib import Path

EXECUTION_SRC_DIR = Path(__file__).resolve().parents[2] / "src" / "execution"
EXECUTION_TASKS_FILE = EXECUTION_SRC_DIR / "presentation" / "tasks.py"

PLANNING_TABLES: tuple[str, ...] = (
    "learning_concepts",
    "schedule_proposals",
    "learning_goals",
    "goals",
    "milestones",
    "roadmaps",
    "knowledge_sources",
    "knowledge_chunks",
    "official_schedules",
    "schedule_blocks",
)
ACCOUNT_TABLES: tuple[str, ...] = ("users",)

FORBIDDEN_CROSS_CONTEXT_SQL_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (
        f"raw SQL referencing {table}",
        re.compile(
            rf"\b(?:FROM|JOIN|UPDATE|INTO|DELETE\s+FROM)\s+{table}\b",
            re.IGNORECASE,
        ),
    )
    for table in (*PLANNING_TABLES, *ACCOUNT_TABLES)
)


def test_execution_context_has_no_raw_sql_touching_planning_or_account_tables() -> None:
    """BE-ARCH-01: Execution bounded context must access Planning/Account only via public_api ports."""
    assert EXECUTION_SRC_DIR.is_dir(), f"Expected directory: {EXECUTION_SRC_DIR}"
    py_files = sorted(EXECUTION_SRC_DIR.rglob("*.py"))
    assert py_files, "No Python files found under src/execution"

    violations: list[str] = []
    for file_path in py_files:
        source = file_path.read_text(encoding="utf-8")
        rel_path = file_path.relative_to(EXECUTION_SRC_DIR.parents[1])
        for label, pattern in FORBIDDEN_CROSS_CONTEXT_SQL_PATTERNS:
            for match in pattern.finditer(source):
                line_no = source.count("\n", 0, match.start()) + 1
                violations.append(f"{rel_path}:{line_no} matched {label}")

    assert not violations, (
        "Bounded context boundary violation(s) found in src/execution:\n" + "\n".join(violations)
    )


def test_execution_worker_tasks_has_no_raw_sql_text_calls() -> None:
    """BE-ARCH-01: Execution worker tasks must use ORM/ports exclusively without raw SQL text(...)."""
    source = EXECUTION_TASKS_FILE.read_text(encoding="utf-8")
    matches = list(re.finditer(r"\btext\s*\(", source))
    assert not matches, (
        "src/execution/presentation/tasks.py must not contain raw SQL text(...) calls"
    )
