from __future__ import annotations

from collections.abc import Iterator

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.adapters.resend_adapter import ResendEmailAdapter
from app.db.database import Base, build_engine
from app.models import Candidate, FailureCategory, LogicalSendOperation, OperationStatus, ProviderAttempt
from app.services.draft_service import generate_draft
from app.services.send_orchestrator import (
    SendOrchestratorError,
    execute_initial_send,
    retry_definitive_failure,
)


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


def seed_draft(factory: sessionmaker[Session]):
    with factory() as db:
        candidate = Candidate(
            application_id="APP-RETRY-001",
            full_name="Nguyen Van A",
            email="candidate@example.com",
            stage="CV_SCREENING",
            status="PASS_CV",
        )
        db.add(candidate)
        db.flush()
        draft = generate_draft(db, application_id=candidate.application_id)
        db.commit()
        return draft


def adapter_with_sequence(status_codes: list[int]) -> tuple[ResendEmailAdapter, list[int]]:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        status_code = status_codes[len(calls)]
        calls.append(status_code)
        if status_code in {200, 201}:
            return httpx.Response(status_code, json={"id": f"email_{len(calls)}"})
        return httpx.Response(status_code, json={"name": "provider_error"})

    return (
        ResendEmailAdapter(
            api_key="re_test_secret",
            sender_address="onboarding@resend.dev",
            sender_name="Recruitment Team",
            transport=httpx.MockTransport(handler),
        ),
        calls,
    )


def test_transient_retry_reuses_operation_and_creates_next_attempt(
    session_factory: sessionmaker[Session],
) -> None:
    draft = seed_draft(session_factory)
    adapter, calls = adapter_with_sequence([503, 200])
    failed = execute_initial_send(
        session_factory,
        adapter=adapter,
        draft_revision_id=draft.id,
    )

    accepted = retry_definitive_failure(
        session_factory,
        adapter=adapter,
        operation_id=failed.operation_id,
    )

    with session_factory() as db:
        attempts = db.execute(
            select(ProviderAttempt)
            .where(ProviderAttempt.operation_id == failed.operation_id)
            .order_by(ProviderAttempt.attempt_number)
        ).scalars().all()
        candidate = db.get(Candidate, draft.candidate_id)

    assert accepted.operation_id == failed.operation_id
    assert accepted.operation_status == OperationStatus.PROVIDER_ACCEPTED.value
    assert [attempt.attempt_number for attempt in attempts] == [1, 2]
    assert calls == [503, 200]
    assert candidate is not None
    assert candidate.communicated_decision == draft.decision


def test_validation_terminal_failure_cannot_retry(
    session_factory: sessionmaker[Session],
) -> None:
    draft = seed_draft(session_factory)
    adapter, calls = adapter_with_sequence([422])
    failed = execute_initial_send(
        session_factory,
        adapter=adapter,
        draft_revision_id=draft.id,
    )

    with pytest.raises(SendOrchestratorError) as error:
        retry_definitive_failure(
            session_factory,
            adapter=adapter,
            operation_id=failed.operation_id,
        )

    assert error.value.error_code == "SEND_OPERATION_NOT_RETRYABLE"
    assert calls == [422]


@pytest.mark.parametrize("first_status", [503, 429])
def test_retryable_categories_can_create_another_failed_attempt(
    session_factory: sessionmaker[Session],
    first_status: int,
) -> None:
    draft = seed_draft(session_factory)
    adapter, _ = adapter_with_sequence([first_status, 503])
    first = execute_initial_send(
        session_factory,
        adapter=adapter,
        draft_revision_id=draft.id,
    )

    second = retry_definitive_failure(
        session_factory,
        adapter=adapter,
        operation_id=first.operation_id,
    )

    with session_factory() as db:
        operation = db.get(LogicalSendOperation, second.operation_id)
        attempts = db.execute(
            select(ProviderAttempt).where(ProviderAttempt.operation_id == second.operation_id)
        ).scalars().all()

    assert operation is not None
    assert operation.operation_status == OperationStatus.DEFINITIVE_FAILURE.value
    assert operation.failure_category == FailureCategory.TRANSIENT_RETRYABLE.value
    assert len(attempts) == 2


def test_delivery_unknown_cannot_use_definitive_failure_retry(
    session_factory: sessionmaker[Session],
) -> None:
    draft = seed_draft(session_factory)

    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout", request=request)

    adapter = ResendEmailAdapter(
        api_key="re_test_secret",
        sender_address="onboarding@resend.dev",
        sender_name="Recruitment Team",
        transport=httpx.MockTransport(timeout),
    )
    unknown = execute_initial_send(
        session_factory,
        adapter=adapter,
        draft_revision_id=draft.id,
    )

    with pytest.raises(SendOrchestratorError) as error:
        retry_definitive_failure(
            session_factory,
            adapter=adapter,
            operation_id=unknown.operation_id,
        )

    assert error.value.error_code == "SEND_OPERATION_NOT_RETRYABLE"
