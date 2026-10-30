"""Account availability and outbox tables

Revision ID: 0001_account_avail
Revises:
Create Date: 2026-10-28 09:45:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_account_avail"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. users
    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(100), nullable=False),
        sa.Column("timezone", sa.String(50), nullable=False, server_default="Asia/Ho_Chi_Minh"),
        sa.Column("role", sa.String(20), nullable=False, server_default="LEARNER"),
        sa.Column("tier", sa.String(20), nullable=False, server_default="FREE"),
        sa.Column(
            "is_locked",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("FALSE"),
        ),
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
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.CheckConstraint("role IN ('LEARNER', 'ADMIN')", name="chk_users_role"),
        sa.CheckConstraint("tier IN ('FREE', 'PREMIUM')", name="chk_users_tier"),
        if_not_exists=True,
    )
    op.create_index(
        "uq_users_lower_email",
        "users",
        [sa.text("LOWER(email)")],
        unique=True,
        if_not_exists=True,
    )

    # 2. ai_quotas
    op.create_table(
        "ai_quotas",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("monthly_limit", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("used_calls", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reserved_calls", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tokens_consumed", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("cycle_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cycle_end", sa.DateTime(timezone=True), nullable=False),
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
        sa.UniqueConstraint("user_id", name="uq_ai_quotas_user_id"),
        sa.CheckConstraint("monthly_limit > 0", name="chk_ai_quotas_monthly_limit"),
        sa.CheckConstraint("used_calls >= 0", name="chk_ai_quotas_used_calls"),
        sa.CheckConstraint("reserved_calls >= 0", name="chk_ai_quotas_reserved_calls"),
        sa.CheckConstraint("tokens_consumed >= 0", name="chk_ai_quotas_tokens"),
        sa.CheckConstraint(
            "used_calls + reserved_calls <= monthly_limit", name="chk_ai_quotas_limit"
        ),
        sa.CheckConstraint("cycle_end > cycle_start", name="chk_ai_quotas_cycle"),
        if_not_exists=True,
    )

    # 3. availabilities
    op.create_table(
        "availabilities",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("mode", sa.String(20), nullable=False, server_default="MODE_A"),
        sa.Column(
            "calendar_integration_mode", sa.String(20), nullable=False, server_default="NONE"
        ),
        sa.Column(
            "daily_quotas",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("min_session_minutes", sa.Integer(), nullable=False, server_default="30"),
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
        sa.UniqueConstraint("user_id", name="uq_availabilities_user_id"),
        sa.CheckConstraint("mode IN ('MODE_A', 'MODE_B')", name="chk_availabilities_mode"),
        sa.CheckConstraint(
            "calendar_integration_mode IN ('NONE', 'EXPORT_ICS', 'CONNECTED')",
            name="chk_availabilities_cal_mode",
        ),
        sa.CheckConstraint(
            "min_session_minutes BETWEEN 15 AND 120", name="chk_availabilities_min_session"
        ),
        if_not_exists=True,
    )

    # 4. availability_slots
    op.create_table(
        "availability_slots",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "availability_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("availabilities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("day_of_week", sa.SmallInteger(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("end_day_offset", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("slot_type", sa.String(20), nullable=False, server_default="ALLOWED"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
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
        sa.CheckConstraint("day_of_week BETWEEN 0 AND 6", name="chk_avail_slots_day"),
        sa.CheckConstraint("end_day_offset IN (0, 1)", name="chk_avail_slots_offset"),
        sa.CheckConstraint("slot_type IN ('ALLOWED', 'FIXED')", name="chk_avail_slots_type"),
        sa.CheckConstraint(
            "end_day_offset = 1 OR end_time > start_time", name="chk_avail_slots_time"
        ),
        if_not_exists=True,
    )
    op.create_index(
        "idx_avail_slots_availability_day",
        "availability_slots",
        ["availability_id", "day_of_week"],
        if_not_exists=True,
    )

    # 5. outbox_events
    op.create_table(
        "outbox_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("aggregate_type", sa.String(100), nullable=False),
        sa.Column("aggregate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(120), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("correlation_id", sa.String(64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('PENDING', 'PUBLISHED', 'FAILED')", name="chk_outbox_events_status"
        ),
        sa.CheckConstraint("retry_count >= 0", name="chk_outbox_events_retry"),
        sa.CheckConstraint("jsonb_typeof(payload) = 'object'", name="chk_outbox_events_payload"),
        sa.CheckConstraint(
            "(status = 'PUBLISHED' AND published_at IS NOT NULL) OR (status != 'PUBLISHED' AND published_at IS NULL)",
            name="chk_outbox_events_published",
        ),
        if_not_exists=True,
    )
    op.create_index(
        "idx_outbox_events_pending",
        "outbox_events",
        ["created_at"],
        postgresql_where=sa.text("status = 'PENDING'"),
        if_not_exists=True,
    )
    op.create_index(
        "idx_outbox_events_aggregate",
        "outbox_events",
        ["aggregate_type", "aggregate_id"],
        if_not_exists=True,
    )

    # 6. processed_events
    op.create_table(
        "processed_events",
        sa.Column(
            "event_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("outbox_events.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("handler_name", sa.String(120), primary_key=True, nullable=False),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_table("processed_events", if_exists=True)
    op.drop_index("idx_outbox_events_aggregate", table_name="outbox_events", if_exists=True)
    op.drop_index("idx_outbox_events_pending", table_name="outbox_events", if_exists=True)
    op.drop_table("outbox_events", if_exists=True)
    op.drop_index(
        "idx_avail_slots_availability_day", table_name="availability_slots", if_exists=True
    )
    op.drop_table("availability_slots", if_exists=True)
    op.drop_table("availabilities", if_exists=True)
    op.drop_table("ai_quotas", if_exists=True)
    op.drop_index("uq_users_lower_email", table_name="users", if_exists=True)
    op.drop_table("users", if_exists=True)
