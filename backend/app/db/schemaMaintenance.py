from sqlalchemy import inspect, text

from app.db.database import engine


def ensure_candidate_status_metadata_columns() -> None:
    """Keep local MVP databases compatible until Alembic migrations are added."""
    inspector = inspect(engine)
    column_names = {column["name"] for column in inspector.get_columns("candidates")}
    statements: list[str] = []

    if "status_updated_at" not in column_names:
        statements.append("ALTER TABLE candidates ADD COLUMN status_updated_at TIMESTAMP WITH TIME ZONE")

    if "status_updated_by" not in column_names:
        statements.append("ALTER TABLE candidates ADD COLUMN status_updated_by VARCHAR(255)")

    if not statements:
        return

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
