from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import get_settings
from app.db.database import Base
import app.models  # noqa: F401 - registers model metadata


TARGET_TABLES = {
    "candidates",
    "draft_revisions",
    "logical_send_operations",
    "provider_attempts",
    "audit_logs",
}

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option(
    "sqlalchemy.url",
    get_settings().database_url.replace("%", "%%"),
)
target_metadata = Base.metadata


def include_object(object_, name: str | None, type_: str, reflected: bool, compare_to) -> bool:
    if type_ == "table":
        return name in TARGET_TABLES

    table = getattr(object_, "table", None)
    return table is None or table.name in TARGET_TABLES


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
