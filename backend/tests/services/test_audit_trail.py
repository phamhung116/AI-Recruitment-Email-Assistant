from __future__ import annotations

from collections.abc import Iterator

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.adapters.resend_adapter import ResendEmailAdapter
from app.db.database import Base, build_engine
from app.models import (
    AttemptStatus,
    AuditLog,
    Candidate,
    DraftRevision,
    DraftStatus,
    LogicalSendOperation,
    OperationStatus,
    ProviderAttempt,
)
from app.services.audit_service import AuditEvent, append_audit_event
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
            application_id="APP-AUDIT-001",
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


def accepted_adapter() -> ResendEmailAdapter:
    return ResendEmailAdapter(
        api_key="re_test_secret",
        sender_address="onboarding@resend.dev",
        sender_name="Recruitment Team",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={"id": "email_audit_123"})
        ),
    )


def test_draft_and_send_events_are_structured_and_exclude_candidate_pii(
    session_factory: sessionmaker[Session],
) -> None:
    draft = seed_ready_draft(session_factory)
    result = execute_initial_send(
        session_factory,
        adapter=accepted_adapter(),
        draft_revision_id=draft.id,
        actor="hr.sender",
    )

    with session_factory() as db:
        events = db.execute(select(AuditLog).order_by(AuditLog.id)).scalars().all()

    assert [event.event_name for event in events] == [
        AuditEvent.DRAFT_GENERATED.value,
        AuditEvent.SEND_PREPARED.value,
        AuditEvent.SEND_OUTCOME_FINALIZED.value,
    ]
    assert events[1].entity_id == str(result.operation_id)
    assert events[2].actor == "hr.sender"
    assert events[2].payload_json["operation_status"] == OperationStatus.PROVIDER_ACCEPTED.value
    serialized_payloads = str([event.payload_json for event in events])
    assert "candidate@example.com" not in serialized_payloads
    assert "Nguyen Van A" not in serialized_payloads


def test_audit_payload_rejects_known_pii_and_message_content(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as db:
        with pytest.raises(ValueError, match="prohibited PII/content"):
            append_audit_event(
                db,
                event=AuditEvent.DRAFT_GENERATED,
                entity_type="DRAFT_REVISION",
                entity_id="draft-1",
                actor="hr.author",
                payload={"rendered_body": "private message"},
            )


def test_phase_c_audit_failure_rolls_back_provider_outcome_atomically(
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    draft = seed_ready_draft(session_factory)
    from app.services import send_orchestrator

    original_append = send_orchestrator.append_audit_event

    def fail_final_event(*args, **kwargs):
        if kwargs.get("event") == AuditEvent.SEND_OUTCOME_FINALIZED:
            raise RuntimeError("audit insert failed")
        return original_append(*args, **kwargs)

    monkeypatch.setattr(send_orchestrator, "append_audit_event", fail_final_event)

    with pytest.raises(RuntimeError, match="audit insert failed"):
        execute_initial_send(
            session_factory,
            adapter=accepted_adapter(),
            draft_revision_id=draft.id,
            actor="hr.sender",
        )

    with session_factory() as db:
        operation = db.execute(select(LogicalSendOperation)).scalar_one()
        attempt = db.execute(select(ProviderAttempt)).scalar_one()
        candidate = db.get(Candidate, draft.candidate_id)
        persisted_draft = db.get(DraftRevision, draft.id)

        assert operation.operation_status == OperationStatus.SENDING_UNCONFIRMED.value
        assert attempt.attempt_status == AttemptStatus.PREPARED.value
        assert candidate is not None and candidate.communicated_decision is None
        assert persisted_draft is not None
        assert persisted_draft.status == DraftStatus.FROZEN_IN_FLIGHT.value


def test_event_is_rolled_back_with_the_business_transaction(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as db:
        append_audit_event(
            db,
            event=AuditEvent.CANDIDATE_IMPORTED,
            entity_type="CANDIDATE",
            entity_id=1,
            application_id="APP-ROLLBACK-001",
            actor="hr.importer",
        )
        db.rollback()

    with session_factory() as db:
        assert db.execute(select(AuditLog)).scalars().all() == []
