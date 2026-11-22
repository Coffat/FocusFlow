"""Add persistent notifications table (#36) for Notification Center (FE-MOCK-08).

Revision ID: 0015_add_notifications_table
Revises: 0014_add_updated_at_triggers
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0015_add_notifications_table"
down_revision: str | None = "0014_add_updated_at_triggers"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE", name="fk_notifications_user"),
            nullable=False,
        ),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("notification_type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("resource_url", sa.String(length=255), nullable=True),
        sa.Column(
            "is_read",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema="public",
    )

    op.create_index(
        "uq_notifications_user_event_type",
        "notifications",
        ["user_id", "event_id", "notification_type"],
        unique=True,
        schema="public",
        postgresql_where=sa.text("event_id IS NOT NULL"),
    )

    op.create_index(
        "idx_notifications_user_unread",
        "notifications",
        ["user_id", "is_read", sa.text("created_at DESC")],
        unique=False,
        schema="public",
    )

    op.execute(
        "CREATE TRIGGER trg_notifications_updated_at "
        "BEFORE UPDATE ON public.notifications "
        "FOR EACH ROW EXECUTE FUNCTION public.fn_set_updated_at();"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_notifications_updated_at ON public.notifications;")
    op.drop_index("idx_notifications_user_unread", table_name="notifications", schema="public")
    op.drop_index("uq_notifications_user_event_type", table_name="notifications", schema="public")
    op.drop_table("notifications", schema="public")
