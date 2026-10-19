from __future__ import annotations

import os
from alembic import context
from sqlalchemy import pool
from backend.db import Base, make_database_engine, normalize_database_url
from backend import models  # noqa: F401 - register metadata

config = context.config
raw_url = os.getenv("DATABASE_URL", "").strip() or config.get_main_option("sqlalchemy.url")
normalized_url, _ = normalize_database_url(raw_url)
config.set_main_option("sqlalchemy.url", normalized_url.replace("%", "%%"))
target_metadata = Base.metadata


def run_migrations_offline():
    context.configure(url=normalized_url, target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"}, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = make_database_engine(raw_url, poolclass=pool.NullPool, pool_pre_ping=True)
    try:
        with connectable.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        connectable.dispose()


run_migrations_offline() if context.is_offline_mode() else run_migrations_online()
