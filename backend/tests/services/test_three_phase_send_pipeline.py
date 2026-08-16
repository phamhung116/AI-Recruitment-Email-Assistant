from __future__ import annotations

from collections.abc import Callable, Iterator

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.adapters.resend_adapter import ResendEmailAdapter
from app.db.database import Base, build_engine
from app.models import (
    AttemptStatus,
    Candidate,
    DraftRevision,
    DraftStatus,
    FailureCategory,
    LogicalSendOperation,
    OperationStatus,
    ProviderAttempt,
)
from app.services.draft_service import generate_draft
from app.services.send_orchestrator import execute_initial_send


@pytest.fixture
def session_factory() -> Iterator[sessionmaker[Session]]:
    engine = build_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        yield factory
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def seed_ready_draft(factory: sessionmaker[Session]) -> DraftRevision:
    with factory() as db:
        candidate = Candidate(
            application_id="APP-PIPELINE-001",
            full_name="Nguyen Van A",
            email="candidate@example.com",
            stage="INTERVIEW",
            status="PASS_INTERVIEW",
        )
        db.add(candidate)
        db.flush()
        draft = generate_draft(db, application_id=candidate.application_id, actor="hr.author")
        db.commit()
        return draft


def make_adapter(handler: Callable[[httpx.Request], httpx.Response]) -> ResendEmailAdapter:
    return ResendEmailAdapter(
        api_key="re_test_secret",
        sender_address="onboarding@resend.dev",
        sender_name="Recruitment Team",
        transport=httpx.MockTransport(handler),
    )


def test_provider_call_runs_after_phase_a_transaction_is_closed(
    session_factory: sessionmaker[Session],
) -> None:
    draft = seed_ready_draft(session_factory)
    opened_sessions: list[Session] = []

    def tracked_factory() -> Session:
        session = session_factory()
        opened_sessions.append(session)
        return session

    def handler(request: httpx.Request) -> httpx.Response:
        assert opened_sessions
        assert all(not session.in_transaction() for session in opened_sessions)
        return httpx.Response(200, json={"id": "email_phase_123"})

    result = execute_initial_send(
        tracked_factory,
        adapter=make_adapter(handler),
        draft_revision_id=draft.id,
        actor="hr.sender",
    )

    assert result.operation_status == OperationStatus.PROVIDER_ACCEPTED.value
    assert result.provider_call_performed is True


def test_accepted_result_finalizes_operation_and_communicated_outcome(
    session_factory: sessionmaker[Session],
) -> None:
    draft = seed_ready_draft(session_factory)
    adapter = make_adapter(lambda request: httpx.Response(201, json={"id": "email_accepted"}))

    result = execute_initial_send(
        session_factory,
        adapter=adapter,
        draft_revision_id=draft.id,
        actor="hr.sender",
    )

    with session_factory() as db:
        operation = db.get(LogicalSendOperation, result.operation_id)
        attempt = db.get(ProviderAttempt, result.attempt_id)
        refreshed_draft = db.get(DraftRevision, draft.id)
        candidate = db.get(Candidate, draft.candidate_id)

        assert operation is not None
        assert attempt is not None
        assert refreshed_draft is not None
        assert candidate is not None
        assert operation.operation_status == OperationStatus.PROVIDER_ACCEPTED.value
        assert operation.provider_message_id == "email_accepted"
        assert attempt.attempt_status == AttemptStatus.ACCEPTED.value
        assert refreshed_draft.status == DraftStatus.FINALIZED.value
        assert candidate.communicated_decision == draft.decision
        assert candidate.communicated_stage == draft.stage
        assert candidate.communicated_at is not None


@pytest.mark.parametrize(
    ("status_code", "expected_operation_status", "expected_category"),
    [
        (422, OperationStatus.FAILED_TERMINAL.value, FailureCategory.VALIDATION_TERMINAL.value),
        (503, OperationStatus.DEFINITIVE_FAILURE.value, FailureCategory.TRANSIENT_RETRYABLE.value),
        (429, OperationStatus.DEFINITIVE_FAILURE.value, FailureCategory.QUOTA_EXCEEDED.value),
    ],
)
def test_provider_failures_do_not_update_communicated_outcome(
    session_factory: sessionmaker[Session],
    status_code: int,
    expected_operation_status: str,
    expected_category: str,
) -> None:
    draft = seed_ready_draft(session_factory)
    adapter = make_adapter(
        lambda request: httpx.Response(
            status_code,
            json={"name": "provider_error", "message": "Provider rejected request"},
        )
    )

    result = execute_initial_send(
        session_factory,
        adapter=adapter,
        draft_revision_id=draft.id,
    )

    with session_factory() as db:
        operation = db.get(LogicalSendOperation, result.operation_id)
        attempt = db.get(ProviderAttempt, result.attempt_id)
        candidate = db.get(Candidate, draft.candidate_id)

        assert operation is not None
        assert attempt is not None
        assert candidate is not None
        assert operation.operation_status == expected_operation_status
        assert operation.failure_category == expected_category
        assert attempt.attempt_status == AttemptStatus.DEFINITIVE_FAILURE.value
        assert candidate.communicated_decision is None
        assert candidate.communicated_stage is None


def test_timeout_becomes_delivery_unknown_without_outcome_update(
    session_factory: sessionmaker[Session],
) -> None:
    draft = seed_ready_draft(session_factory)

    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timeout", request=request)

    result = execute_initial_send(
        session_factory,
        adapter=make_adapter(timeout),
        draft_revision_id=draft.id,
    )

    with session_factory() as db:
        operation = db.get(LogicalSendOperation, result.operation_id)
        attempt = db.get(ProviderAttempt, result.attempt_id)
        candidate = db.get(Candidate, draft.candidate_id)

        assert operation is not None
        assert attempt is not None
        assert candidate is not None
        assert operation.operation_status == OperationStatus.DELIVERY_UNKNOWN.value
        assert attempt.attempt_status == AttemptStatus.UNCONFIRMED_TIMEOUT.value
        assert candidate.communicated_decision is None


def test_repeated_execution_does_not_call_provider_or_create_attempt_twice(
    session_factory: sessionmaker[Session],
) -> None:
    draft = seed_ready_draft(session_factory)
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"id": "email_once"})

    adapter = make_adapter(handler)
    first = execute_initial_send(
        session_factory,
        adapter=adapter,
        draft_revision_id=draft.id,
    )
    second = execute_initial_send(
        session_factory,
        adapter=adapter,
        draft_revision_id=draft.id,
    )

    with session_factory() as db:
        attempt_count = db.execute(
            select(func.count()).select_from(ProviderAttempt)
        ).scalar_one()

    assert first.operation_id == second.operation_id
    assert second.provider_call_performed is False
    assert calls == 1
    assert attempt_count == 1
