from __future__ import annotations

from collections.abc import Iterator
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.database import Base, build_engine
from app.models import Candidate, DraftRevision, DraftStatus, LogicalSendOperation, OperationStatus
from app.services.draft_service import generate_draft
from app.services.send_orchestrator import (
    SendOrchestratorError,
    prepare_logical_send_operation,
)


@pytest.fixture
def db() -> Iterator[Session]:
    engine = build_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def add_ready_draft(db: Session) -> DraftRevision:
    candidate = Candidate(
        application_id="APP-SEND-001",
        full_name="Nguyen Van A",
        email="candidate@example.com",
        stage="CV_SCREENING",
        status="PASS_CV",
    )
    db.add(candidate)
    db.flush()
    draft = generate_draft(db, application_id=candidate.application_id, actor="hr.owner")
    assert draft.status == DraftStatus.READY_TO_SEND.value
    return draft


def operation_count(db: Session) -> int:
    return db.execute(
        select(func.count()).select_from(LogicalSendOperation)
    ).scalar_one()


def test_prepare_creates_one_operation_and_freezes_ready_draft(db: Session) -> None:
    draft = add_ready_draft(db)

    operation = prepare_logical_send_operation(
        db,
        draft_revision_id=draft.id,
        actor="hr.sender",
    )

    assert operation.draft_revision_id == draft.id
    assert operation.operation_status == OperationStatus.SENDING_UNCONFIRMED.value
    assert operation.provider_name == "RESEND"
    assert operation.created_by == "hr.sender"
    assert draft.status == DraftStatus.FROZEN_IN_FLIGHT.value
    assert operation_count(db) == 1


def test_repeated_prepare_reuses_existing_operation(db: Session) -> None:
    draft = add_ready_draft(db)
    first = prepare_logical_send_operation(db, draft_revision_id=draft.id)

    second = prepare_logical_send_operation(db, draft_revision_id=draft.id)

    assert second.id == first.id
    assert operation_count(db) == 1


@pytest.mark.parametrize(
    "status",
    [
        DraftStatus.DRAFT_PENDING_CHECK.value,
        DraftStatus.BLOCKED_DETERMINISTIC.value,
        DraftStatus.SUPERSEDED.value,
        DraftStatus.DISCARDED.value,
        DraftStatus.FINALIZED.value,
    ],
)
def test_non_sendable_draft_cannot_create_operation(
    db: Session,
    status: str,
) -> None:
    draft = add_ready_draft(db)
    draft.status = status

    with pytest.raises(SendOrchestratorError) as error:
        prepare_logical_send_operation(db, draft_revision_id=draft.id)

    assert error.value.error_code == "DRAFT_NOT_READY_TO_SEND"
    assert operation_count(db) == 0


def test_send_requires_positive_deterministic_result(db: Session) -> None:
    draft = add_ready_draft(db)
    draft.risk_check_result = {"passed": False, "issues": []}

    with pytest.raises(SendOrchestratorError) as error:
        prepare_logical_send_operation(db, draft_revision_id=draft.id)

    assert error.value.error_code == "DETERMINISTIC_CHECK_REQUIRED"
    assert draft.status == DraftStatus.READY_TO_SEND.value
    assert operation_count(db) == 0


def test_missing_draft_returns_stable_error(db: Session) -> None:
    with pytest.raises(SendOrchestratorError) as error:
        prepare_logical_send_operation(db, draft_revision_id=uuid4())

    assert error.value.error_code == "DRAFT_REVISION_NOT_FOUND"


def test_prepare_does_not_commit_callers_transaction(db: Session) -> None:
    draft = add_ready_draft(db)
    prepare_logical_send_operation(db, draft_revision_id=draft.id)

    db.rollback()

    assert operation_count(db) == 0
