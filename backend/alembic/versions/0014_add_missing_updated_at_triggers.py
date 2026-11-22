"""Add missing BEFORE UPDATE updated_at triggers for 5 tables (DB-CONSIST-02).

Revision ID: 0014_add_updated_at_triggers
Revises: 0013_ai_usage_audit_jsonb
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0014_add_updated_at_triggers"
down_revision: str | None = "0013_ai_usage_audit_jsonb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TRIGGER_TABLES: tuple[str, ...] = (
    "knowledge_sources",
    "learner_concept_masteries",
    "learner_memory_items",
    "learning_concepts",
    "workflow_runs",
)


def upgrade() -> None:
    for table in _TRIGGER_TABLES:
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_updated_at ON public.{table};")
        op.execute(
            f"CREATE TRIGGER trg_{table}_updated_at "
            f"BEFORE UPDATE ON public.{table} "
            "FOR EACH ROW EXECUTE FUNCTION public.fn_set_updated_at();"
        )


def downgrade() -> None:
    for table in _TRIGGER_TABLES:
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_updated_at ON public.{table};")
