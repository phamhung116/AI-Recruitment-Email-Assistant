"""Validate Alembic on a disposable local PostgreSQL database.

This script deliberately refuses non-local database hosts and only creates or
drops a database whose name starts with the dedicated validation prefix.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import psycopg2
from psycopg2 import sql
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import make_url

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import get_settings


DATABASE_PREFIX = "recruitment_mail_guard_migration_test_"
DATABASE_NAME = f"{DATABASE_PREFIX}{os.getpid()}"
TARGET_TABLES = {
    "candidates",
    "draft_revisions",
    "logical_send_operations",
    "provider_attempts",
    "audit_logs",
}


def _run_alembic(database_url: str, *arguments: str) -> None:
    environment = os.environ.copy()
    environment["DATABASE_URL"] = database_url
    subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "alembic.ini", *arguments],
        cwd=BACKEND_ROOT,
        env=environment,
        check=True,
    )


def _schema_tables(database_url: str) -> set[str]:
    engine = create_engine(database_url)
    try:
        return set(inspect(engine).get_table_names(schema="public"))
    finally:
        engine.dispose()


def main() -> int:
    source_url = make_url(get_settings().database_url)
    if source_url.host not in {"localhost", "127.0.0.1", "::1"}:
        raise RuntimeError("Migration round-trip is restricted to local PostgreSQL hosts.")
    if not DATABASE_NAME.startswith(DATABASE_PREFIX):
        raise RuntimeError("Refusing unsafe validation database name.")

    maintenance_url = source_url.set(drivername="postgresql", database="postgres")
    test_url = source_url.set(database=DATABASE_NAME)
    connection = psycopg2.connect(maintenance_url.render_as_string(hide_password=False))
    connection.autocommit = True

    try:
        with connection.cursor() as cursor:
            cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(DATABASE_NAME)))

        rendered_test_url = test_url.render_as_string(hide_password=False)
        _run_alembic(rendered_test_url, "upgrade", "head")
        upgraded_tables = _schema_tables(rendered_test_url)
        assert upgraded_tables == TARGET_TABLES | {"alembic_version"}, upgraded_tables

        _run_alembic(rendered_test_url, "downgrade", "base")
        downgraded_tables = _schema_tables(rendered_test_url)
        assert downgraded_tables == {"alembic_version"}, downgraded_tables

        _run_alembic(rendered_test_url, "upgrade", "head")
        reupgraded_tables = _schema_tables(rendered_test_url)
        assert reupgraded_tables == TARGET_TABLES | {"alembic_version"}, reupgraded_tables
        print("Migration round-trip passed: upgrade -> downgrade -> upgrade (5 core tables).")
        return 0
    finally:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = %s AND pid <> pg_backend_pid()",
                (DATABASE_NAME,),
            )
            cursor.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(DATABASE_NAME)))
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
