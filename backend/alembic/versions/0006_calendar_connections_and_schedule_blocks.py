"""Add calendar_connections and schedule_blocks tables for 2-way Google Calendar sync

Revision ID: 0006_calendar_connections_and_schedule_blocks
Revises: 0005_add_missing_fk_indexes
Create Date: 2026-05-15 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006_calendar_and_blocks"
down_revision: str | None = "0005_add_missing_fk_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    # 1. Bảng calendar_connections (account context)
    if "calendar_connections" not in existing_tables:
        op.create_table(
            "calendar_connections",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("provider", sa.String(length=30), nullable=False, server_default="GOOGLE"),
            sa.Column(
                "external_calendar_id",
                sa.String(length=255),
                nullable=False,
                server_default="primary",
            ),
            sa.Column("oauth_refresh_token_encrypted", sa.Text(), nullable=False),
            sa.Column("sync_status", sa.String(length=20), nullable=False, server_default="ACTIVE"),
            sa.Column("sync_token", sa.Text(), nullable=True),
            sa.Column("channel_id", sa.String(length=255), nullable=True),
            sa.Column("resource_id", sa.String(length=255), nullable=True),
            sa.Column("channel_token_hash", sa.String(length=64), nullable=True),
            sa.Column("channel_expiration", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "source_calendars_json",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'[\"primary\"]'::jsonb"),
            ),
            sa.Column(
                "sync_metadata_json",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
            sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("error_detail", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("NOW()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("NOW()"),
            ),
            sa.ForeignKeyConstraint(
                ["user_id"],
                ["users.id"],
                name="fk_calendar_connections_user",
                ondelete="CASCADE",
            ),
            sa.UniqueConstraint(
                "user_id", "provider", name="uq_calendar_connections_user_provider"
            ),
            sa.CheckConstraint(
                "provider IN ('GOOGLE', 'OUTLOOK', 'LOCAL_MOCK')",
                name="chk_calendar_connections_provider",
            ),
            sa.CheckConstraint(
                "sync_status IN ('ACTIVE', 'REVOKED', 'ERROR')",
                name="chk_calendar_connections_status",
            ),
        )

        op.create_index(
            "idx_calendar_connections_user_status",
            "calendar_connections",
            ["user_id", "sync_status"],
        )
        op.create_index(
            "idx_calendar_connections_channel",
            "calendar_connections",
            ["channel_id"],
            postgresql_where=sa.text("channel_id IS NOT NULL"),
        )
        op.execute(
            "DROP TRIGGER IF EXISTS trg_calendar_connections_updated_at ON calendar_connections;"
        )
        op.execute(
            "CREATE TRIGGER trg_calendar_connections_updated_at BEFORE UPDATE ON calendar_connections "
            "FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();"
        )

    # 2. Bảng schedule_blocks (planning context)
    if "schedule_blocks" not in existing_tables:
        op.create_table(
            "schedule_blocks",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column("roadmap_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("official_schedule_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("sequence_in_task", sa.SmallInteger(), nullable=False, server_default="1"),
            sa.Column("block_type", sa.String(length=20), nullable=False, server_default="STUDY"),
            sa.Column("block_date", sa.Date(), nullable=False),
            sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
            sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
            sa.Column("scheduled_duration_minutes", sa.Integer(), nullable=False),
            sa.Column("is_protected", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="PLANNED"),
            sa.Column("external_calendar_event_id", sa.String(length=255), nullable=True),
            sa.Column("etag", sa.String(length=255), nullable=True),
            sa.Column("sync_status", sa.String(length=30), nullable=False, server_default="SYNCED"),
            sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("placement_rationale", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("NOW()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("NOW()"),
            ),
            sa.ForeignKeyConstraint(
                ["roadmap_id"],
                ["roadmaps.id"],
                name="fk_schedule_blocks_roadmap",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["official_schedule_id"],
                ["official_schedules.id"],
                name="fk_schedule_blocks_schedule",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["task_id"],
                ["tasks.id"],
                name="fk_schedule_blocks_task",
                ondelete="CASCADE",
            ),
            sa.CheckConstraint("sequence_in_task >= 1", name="chk_schedule_blocks_seq"),
            sa.CheckConstraint(
                "block_type IN ('STUDY', 'BUFFER', 'REVISION', 'RECOVERY')",
                name="chk_schedule_blocks_type",
            ),
            sa.CheckConstraint(
                "scheduled_duration_minutes BETWEEN 10 AND 240",
                name="chk_schedule_blocks_duration",
            ),
            sa.CheckConstraint(
                "status IN ('PLANNED', 'COMPLETED', 'MISSED', 'RESCHEDULED', 'CANCELLED')",
                name="chk_schedule_blocks_status",
            ),
            sa.CheckConstraint("end_time > start_time", name="chk_schedule_blocks_time_order"),
        )

        op.create_index(
            "idx_schedule_blocks_roadmap_date",
            "schedule_blocks",
            ["roadmap_id", "block_date", "start_time"],
        )
        op.create_index(
            "idx_schedule_blocks_schedule_id",
            "schedule_blocks",
            ["official_schedule_id"],
        )
        op.create_index(
            "idx_schedule_blocks_task_id",
            "schedule_blocks",
            ["task_id"],
            postgresql_where=sa.text("task_id IS NOT NULL"),
        )
        op.create_index(
            "idx_schedule_blocks_external_event",
            "schedule_blocks",
            ["external_calendar_event_id"],
            postgresql_where=sa.text("external_calendar_event_id IS NOT NULL"),
        )
        op.execute("DROP TRIGGER IF EXISTS trg_schedule_blocks_updated_at ON schedule_blocks;")
        op.execute(
            "CREATE TRIGGER trg_schedule_blocks_updated_at BEFORE UPDATE ON schedule_blocks "
            "FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();"
        )
    else:
        # Table exists: ensure new columns are present
        existing_cols = {col["name"] for col in inspector.get_columns("schedule_blocks")}
        if "etag" not in existing_cols:
            op.add_column(
                "schedule_blocks", sa.Column("etag", sa.String(length=255), nullable=True)
            )
        if "sync_status" not in existing_cols:
            op.add_column(
                "schedule_blocks",
                sa.Column(
                    "sync_status",
                    sa.String(length=30),
                    nullable=False,
                    server_default="SYNCED",
                ),
            )
        if "last_synced_at" not in existing_cols:
            op.add_column(
                "schedule_blocks",
                sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
            )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if "schedule_blocks" in existing_tables:
        op.execute("DROP TRIGGER IF EXISTS trg_schedule_blocks_updated_at ON schedule_blocks;")
        op.drop_index("idx_schedule_blocks_external_event", table_name="schedule_blocks")
        op.drop_index("idx_schedule_blocks_task_id", table_name="schedule_blocks")
        op.drop_index("idx_schedule_blocks_schedule_id", table_name="schedule_blocks")
        op.drop_index("idx_schedule_blocks_roadmap_date", table_name="schedule_blocks")
        op.drop_table("schedule_blocks")

    if "calendar_connections" in existing_tables:
        op.execute(
            "DROP TRIGGER IF EXISTS trg_calendar_connections_updated_at ON calendar_connections;"
        )
        op.drop_index("idx_calendar_connections_channel", table_name="calendar_connections")
        op.drop_index("idx_calendar_connections_user_status", table_name="calendar_connections")
        op.drop_table("calendar_connections")
