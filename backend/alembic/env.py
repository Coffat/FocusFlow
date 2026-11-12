"""Async Alembic environment for FocusFlow (ADR-007).

Alembic is the runtime source of truth for the PostgreSQL 16 schema.
`docs/database/schema.sql` is a generated documentation artifact
(see `scripts/dump_schema.sh`).
"""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Import every Bounded Context's ORM package so that all models register on
# Base.metadata before autogenerate compares it against the database.
import src.account.infrastructure.orm  # noqa: F401
import src.evaluation.infrastructure.orm  # noqa: F401
import src.execution.infrastructure.orm  # noqa: F401
import src.planning.infrastructure.orm  # noqa: F401
import src.shared_kernel.infrastructure.outbox.models  # noqa: F401
import src.shared_kernel.infrastructure.workflow.models  # noqa: F401
from alembic import context
from src.shared_kernel.config import get_settings
from src.shared_kernel.infrastructure.database.session import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Single source for the connection string: application Settings (DATABASE_URL).
config.set_main_option("sqlalchemy.url", get_settings().database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Emit SQL to stdout without a DB connection (`alembic upgrade head --sql`)."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine (asyncpg) and run migrations on a sync bridge."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
