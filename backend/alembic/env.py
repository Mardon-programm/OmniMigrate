from __future__ import annotations

import sys
print("DEBUG: alembic/env.py starting", file=sys.stderr, flush=True)

import asyncio
from logging.config import fileConfig

from alembic import context
from app.core.config import settings
from app.models import Base
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

print(f"DEBUG: settings imported, database_url = {settings.database_url}", file=sys.stderr, flush=True)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override the sqlalchemy.url from the runtime settings for async drivers.
print(f"DEBUG: settings.database_url = {settings.database_url}", file=sys.stderr, flush=True)
print(f"DEBUG: settings.postgres_url_for_alembic = {settings.postgres_url_for_alembic}", file=sys.stderr, flush=True)
config.set_main_option("sqlalchemy.url", settings.database_url)
print(f"DEBUG: config sqlalchemy.url = {config.get_main_option('sqlalchemy.url')}", file=sys.stderr, flush=True)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.postgres_url_for_alembic,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
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
