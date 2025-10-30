"""Alembic environment configuration for Sophia's Supabase Postgres schema."""

from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Ensure the application package is importable when running via the Alembic CLI.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import get_settings
from app.db import Base  # noqa: E402
from app import db  # noqa: E402  # ensures models are imported for metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    """Resolve the database URL from settings or Alembic configuration."""
    settings = get_settings()
    configured_url = config.get_main_option("sqlalchemy.url")
    url = settings.SUPABASE_DB_DSN or configured_url
    if not url:
        raise RuntimeError(
            "Database URL is not configured. Set SUPABASE_DB_DSN in the environment "
            "or provide sqlalchemy.url in alembic.ini."
        )
    return url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode without establishing a DB connection."""
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode using a live connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        url=get_url(),
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
