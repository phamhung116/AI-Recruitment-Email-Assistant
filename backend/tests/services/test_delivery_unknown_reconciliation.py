from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.adapters.resend_adapter import ResendEmailAdapter
from app.db.database import Base, build_engine
from app.models import Candidate, LogicalSendOperation, OperationStatus, ProviderAttempt, ResolutionMode
from app.services.draft_service import generate_draft
from app.services.send_orchestrator import (
    DeliveryUnknownResolution,
    SendOrchestratorError,
    execute_initial_send,
    reconcile_delivery_unknown_via_provider,
    resolve_delivery_unknown,
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


def seed_unknown_operation(
    factory: sessionmaker[Session],
) -> tuple[LogicalSendOperation, list[int]]:
    with factory() as db:
        candidate = Candidate(
            application_id="APP-UNKNOWN-001",
            full_name="Nguyen Van A",
            email="candidate@example.com",
            stage="INTERVIEW",
            status="REJECT_INTERVIEW",
        )
        db.add(candidate)
        db.flush()
        draft = generate_draft(db, application_id=candidate.application_id)
        db.commit()

    calls: list[int] = []

    def timeout(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        raise httpx.ReadTimeout("timeout", request=request)

    unknown = execute_initial_send(
        factory,
        adapter=make_adapter(timeout),
        draft_revision_id=draft.id,
    )
    with factory() as db:
        operation = db.get(LogicalSendOperation, unknown.operation_id)
        assert operation is not None
        return operation, calls


def make_adapter(handler) -> ResendEmailAdapter:
    return ResendEmailAdapter(
        api_key="re_test_secret",
        sender_address="onboarding@resend.dev",
        sender_name="Recruitment Team",
        transport=httpx.MockTransport(handler),
    )


def test_provider_replay_within_24_hours_reuses_operation(
    session_factory: sessionmaker[Session],
) -> None:
    operation, initial_calls = seed_unknown_operation(session_factory)

    result = reconcile_delivery_unknown_via_provider(
        session_factory,
        adapter=make_adapter(lambda request: httpx.Response(200, json={"id": "email_replayed"})),
        operation_id=operation.id,
        current_time=_aware(operation.created_at) + timedelta(hours=23),
    )

    with session_factory() as db:
        refreshed = db.get(LogicalSendOperation, operation.id)
        attempts = db.execute(
            select(ProviderAttempt)
            .where(ProviderAttempt.operation_id == operation.id)
            .order_by(ProviderAttempt.attempt_number)
        ).scalars().all()

    assert initial_calls == [1]
    assert result.operation_id == operation.id
    assert result.operation_status == OperationStatus.PROVIDER_ACCEPTED.value
    assert refreshed is not None
    assert refreshed.resolution_mode == ResolutionMode.PROVIDER_IDEMPOTENT_REPLAY.value
    assert [attempt.attempt_number for attempt in attempts] == [1, 2]


def test_provider_replay_after_24_hours_is_blocked(
    session_factory: sessionmaker[Session],
) -> None:
    operation, _ = seed_unknown_operation(session_factory)
    provider_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal provider_calls
        provider_calls += 1
        return httpx.Response(200, json={"id": "must_not_send"})

    with pytest.raises(SendOrchestratorError) as error:
        reconcile_delivery_unknown_via_provider(
            session_factory,
            adapter=make_adapter(handler),
            operation_id=operation.id,
            current_time=_aware(operation.created_at) + timedelta(hours=24, seconds=1),
        )

    assert error.value.error_code == "IDEMPOTENCY_WINDOW_EXPIRED"
    assert provider_calls == 0


@pytest.mark.parametrize(
    ("rationale", "resolved_by", "acknowledged", "error_code"),
    [
        ("Verified in provider dashboard", "hr.owner", False, "RESOLUTION_WARNING_ACKNOWLEDGEMENT_REQUIRED"),
        ("no", "hr.owner", True, "RESOLUTION_RATIONALE_REQUIRED"),
        ("Verified in provider dashboard", "", True, "RESOLVED_BY_REQUIRED"),
    ],
)
def test_manual_resolution_requires_governance_fields(
    session_factory: sessionmaker[Session],
    rationale: str,
    resolved_by: str,
    acknowledged: bool,
    error_code: str,
) -> None:
    operation, _ = seed_unknown_operation(session_factory)
    with session_factory() as db:
        with pytest.raises(SendOrchestratorError) as error:
            resolve_delivery_unknown(
                db,
                operation_id=operation.id,
                resolution=DeliveryUnknownResolution.PROVIDER_ACCEPTED,
                rationale=rationale,
                resolved_by=resolved_by,
                warning_acknowledged=acknowledged,
            )

    assert error.value.error_code == error_code


def test_manual_provider_accepted_updates_communicated_outcome(
    session_factory: sessionmaker[Session],
) -> None:
    operation, _ = seed_unknown_operation(session_factory)
    with session_factory() as db:
        resolved = resolve_delivery_unknown(
            db,
            operation_id=operation.id,
            resolution=DeliveryUnknownResolution.PROVIDER_ACCEPTED,
            rationale="Verified in provider dashboard",
            resolved_by="hr.owner",
            warning_acknowledged=True,
        )
        db.commit()
        candidate_id = resolved.draft_revision.candidate_id

    with session_factory() as db:
        refreshed = db.get(LogicalSendOperation, operation.id)
        candidate = db.get(Candidate, candidate_id)

    assert refreshed is not None
    assert candidate is not None
    assert refreshed.operation_status == OperationStatus.PROVIDER_ACCEPTED.value
    assert refreshed.resolution_mode == ResolutionMode.HR_MANUAL_OVERRIDE.value
    assert refreshed.resolved_by == "hr.owner"
    assert candidate.communicated_decision == "REJECT_INTERVIEW"


def test_manual_not_received_unlocks_retry_on_same_operation(
    session_factory: sessionmaker[Session],
) -> None:
    operation, _ = seed_unknown_operation(session_factory)
    with session_factory() as db:
        resolved = resolve_delivery_unknown(
            db,
            operation_id=operation.id,
            resolution=DeliveryUnknownResolution.PROVIDER_NOT_RECEIVED,
            rationale="Confirmed no email in provider logs",
            resolved_by="hr.owner",
            warning_acknowledged=True,
        )
        db.commit()

    result = retry_definitive_failure(
        session_factory,
        adapter=make_adapter(lambda request: httpx.Response(200, json={"id": "email_after_check"})),
        operation_id=resolved.id,
    )

    assert result.operation_id == operation.id
    assert result.operation_status == OperationStatus.PROVIDER_ACCEPTED.value


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
