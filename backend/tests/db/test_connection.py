from unittest.mock import MagicMock

import pytest
from sqlalchemy import Column, Integer, MetaData, Table, func, insert, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.db import database


def make_sqlite_session_factory() -> tuple[sessionmaker[Session], Table]:
    test_engine = database.build_engine("sqlite+pysqlite:///:memory:")
    metadata = MetaData()
    records = Table(
        "records",
        metadata,
        Column("id", Integer, primary_key=True),
    )
    metadata.create_all(test_engine)
    return sessionmaker(bind=test_engine, expire_on_commit=False), records


def test_build_engine_supports_disposable_sqlite() -> None:
    test_engine = database.build_engine("sqlite+pysqlite:///:memory:")

    with test_engine.connect() as connection:
        assert connection.execute(text("SELECT 1")).scalar_one() == 1

    test_engine.dispose()


def test_session_scope_commits_successful_unit_of_work() -> None:
    session_factory, records = make_sqlite_session_factory()

    with database.session_scope(session_factory) as db:
        db.execute(insert(records).values(id=1))

    with session_factory() as verification_db:
        count = verification_db.execute(select(func.count()).select_from(records)).scalar_one()

    assert count == 1


def test_session_scope_rolls_back_failed_unit_of_work() -> None:
    session_factory, records = make_sqlite_session_factory()

    with pytest.raises(RuntimeError, match="force rollback"):
        with database.session_scope(session_factory) as db:
            db.execute(insert(records).values(id=1))
            raise RuntimeError("force rollback")

    with session_factory() as verification_db:
        count = verification_db.execute(select(func.count()).select_from(records)).scalar_one()

    assert count == 0


def test_get_db_rolls_back_and_closes_after_request_error(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_session = MagicMock(spec=Session)
    monkeypatch.setattr(database, "SessionLocal", lambda: fake_session)
    dependency = database.get_db()

    assert next(dependency) is fake_session
    with pytest.raises(RuntimeError, match="request failed"):
        dependency.throw(RuntimeError("request failed"))

    fake_session.rollback.assert_called_once_with()
    fake_session.close.assert_called_once_with()
