from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

from app.db.database import Base


BACKEND_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = (
    BACKEND_ROOT / "alembic" / "versions" / "001_initial_core_schema.py"
)
TARGET_TABLES = {
    "candidates",
    "draft_revisions",
    "logical_send_operations",
    "provider_attempts",
    "audit_logs",
}
LEGACY_TABLES = {
    "email_templates",
    "email_queue",
    "email_history",
    "outbox_events",
}


def _load_migration_module():
    spec = importlib.util.spec_from_file_location("initial_core_schema", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _operation_table_names(operation_name: str) -> list[str]:
    tree = ast.parse(MIGRATION_PATH.read_text(encoding="utf-8"))
    table_names: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != operation_name or not node.args:
            continue
        first_argument = node.args[0]
        if isinstance(first_argument, ast.Constant) and isinstance(first_argument.value, str):
            table_names.append(first_argument.value)
    return table_names


def test_initial_revision_is_a_single_clean_schema_baseline() -> None:
    migration = _load_migration_module()

    assert migration.revision == "001_initial_core_schema"
    assert migration.down_revision is None
    assert set(migration.TARGET_TABLE_NAMES) == TARGET_TABLES


def test_upgrade_creates_exactly_the_five_approved_tables() -> None:
    created_tables = _operation_table_names("create_table")

    assert len(created_tables) == len(TARGET_TABLES)
    assert set(created_tables) == TARGET_TABLES
    assert set(created_tables).isdisjoint(LEGACY_TABLES)


def test_downgrade_drops_exactly_the_five_approved_tables() -> None:
    dropped_tables = _operation_table_names("drop_table")

    assert len(dropped_tables) == len(TARGET_TABLES)
    assert set(dropped_tables) == TARGET_TABLES
    assert set(dropped_tables).isdisjoint(LEGACY_TABLES)


def test_autogenerate_metadata_contains_target_and_legacy_tables() -> None:
    # The migration environment filters this metadata to TARGET_TABLES. Keeping
    # legacy models registered preserves runtime compatibility until SLICE-019.
    assert TARGET_TABLES <= set(Base.metadata.tables)
    assert LEGACY_TABLES <= set(Base.metadata.tables)
