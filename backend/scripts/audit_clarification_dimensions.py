"""Read-only audit for `DiagnosticDimension` JSON fields in existing database rows (T2.4 / B5).

Does NOT mutate any row. Checks `goals.clarification_context` and
`workflow_runs.context_snapshot` for canonical vs legacy vs unknown dimension keys/values.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Iterable
from typing import Any

from src.planning.application.dtos.planning_dtos import audit_clarification_dimensions


def audit_clarification_json_rows(
    *,
    goal_contexts: Iterable[dict[str, Any]],
    workflow_snapshots: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Audit raw JSON payloads from `goals.clarification_context` and `workflow_runs.context_snapshot`."""
    goal_items: list[dict[str, Any]] = []
    invalid_goal_rows = 0
    for ctx in goal_contexts:
        if not isinstance(ctx, dict):
            invalid_goal_rows += 1
            continue
        goal_items.append(ctx)
        for key in ("answered_dimensions", "missing_dimensions"):
            if isinstance(ctx.get(key), list):
                goal_items.append(
                    {"questions": [{"diagnostic_dimension": val} for val in ctx[key]]}
                )
        if isinstance(ctx.get("asked_questions"), list):
            goal_items.append(
                {
                    "questions": [
                        item
                        for item in ctx["asked_questions"]
                        if isinstance(item, dict) and "diagnostic_dimension" in item
                    ]
                }
            )

    workflow_items: list[dict[str, Any]] = []
    invalid_workflow_rows = 0
    for snap in workflow_snapshots:
        if not isinstance(snap, dict):
            invalid_workflow_rows += 1
            continue
        workflow_items.append(snap)
        if "diagnostic_dimension" in snap:
            workflow_items.append(
                {"questions": [{"diagnostic_dimension": snap["diagnostic_dimension"]}]}
            )
        if isinstance(snap.get("missing_dimensions"), list):
            workflow_items.append(
                {"questions": [{"diagnostic_dimension": val} for val in snap["missing_dimensions"]]}
            )

    goal_report = audit_clarification_dimensions(goal_items)
    workflow_report = audit_clarification_dimensions(workflow_items)
    return {
        "goals_clarification_context": {
            **goal_report,
            "invalid_container_rows": invalid_goal_rows,
        },
        "workflow_runs_context_snapshot": {
            **workflow_report,
            "invalid_container_rows": invalid_workflow_rows,
        },
    }


async def run_readonly_db_audit() -> dict[str, Any]:
    """Connect to the configured database in read-only mode and print JSON audit counts."""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    from src.shared_kernel.config import Settings

    settings = Settings()
    engine = create_async_engine(settings.database_url, echo=False)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SET TRANSACTION READ ONLY"))
            goal_rows = (
                (
                    await conn.execute(
                        text(
                            "SELECT clarification_context FROM goals "
                            "WHERE clarification_context IS NOT NULL"
                        )
                    )
                )
                .scalars()
                .all()
            )
            workflow_rows = (
                (
                    await conn.execute(
                        text(
                            "SELECT context_snapshot FROM workflow_runs "
                            "WHERE context_snapshot IS NOT NULL"
                        )
                    )
                )
                .scalars()
                .all()
            )
        return audit_clarification_json_rows(
            goal_contexts=list(goal_rows),
            workflow_snapshots=list(workflow_rows),
        )
    finally:
        await engine.dispose()


if __name__ == "__main__":
    print(json.dumps(asyncio.run(run_readonly_db_audit()), ensure_ascii=False, indent=2))
