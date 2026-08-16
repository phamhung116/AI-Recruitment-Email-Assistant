from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timezone

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.constants.templates import DECISION_CORRECTION
from app.db.database import Base, build_engine
from app.models import (
    Candidate,
    DraftRevision,
    DraftStatus,
    LogicalSendOperation,
    OperationStatus,
)
from app.services.draft_service import (
    DraftServiceError,
    create_decision_correction,
    discard_decision_correction,
    generate_draft,
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


def establish_communicated_outcome(
    db: Session,
    *,
    stage: str = "INTERVIEW",
    decision: str = "REJECT_INTERVIEW",
) -> tuple[Candidate, DraftRevision, LogicalSendOperation]:
    candidate = Candidate(
        id=1,
        application_id="APP-2026-001",
        full_name="Nguyen Van A",
        email="candidate@example.com",
        stage=stage,
        status=decision,
        communicated_stage=stage,
        communicated_decision=decision,
        communicated_at=datetime(2026, 8, 16, 8, 0, tzinfo=timezone.utc),
    )
    db.add(candidate)
    db.flush()
    prior_draft = generate_draft(db, application_id=candidate.application_id)
    prior_draft.status = DraftStatus.FINALIZED.value
    prior_operation = LogicalSendOperation(
        draft_revision_id=prior_draft.id,
        operation_status=OperationStatus.PROVIDER_ACCEPTED.value,
        final_outcome=OperationStatus.PROVIDER_ACCEPTED.value,
        provider_message_id="resend-prior-message",
    )
    db.add(prior_operation)
    db.commit()
    return candidate, prior_draft, prior_operation


def correction_count(db: Session) -> int:
    return db.execute(
        select(func.count())
        .select_from(DraftRevision)
        .where(DraftRevision.is_correction.is_(True))
    ).scalar_one()


def test_create_correction_links_prior_operation_and_preserves_communicated_outcome(
    db: Session,
) -> None:
    candidate, _, prior_operation = establish_communicated_outcome(db)
    communicated_at = candidate.communicated_at

    correction = create_decision_correction(
        db,
        application_id=candidate.application_id,
        new_decision="PASS_INTERVIEW",
        rationale="  Interview assessment was revised.  ",
        actor="hr.owner",
    )

    assert correction.revision_number == 2
    assert correction.template_code == DECISION_CORRECTION
    assert correction.status == DraftStatus.CORRECTION_DRAFT.value
    assert correction.is_correction is True
    assert correction.correction_rationale == "Interview assessment was revised."
    assert correction.prior_operation_id == prior_operation.id
    assert correction.risk_check_result["passed"] is True
    assert "corrects the outcome previously communicated" in correction.rendered_body
    assert candidate.status == "PASS_INTERVIEW"
    assert candidate.status_updated_by == "hr.owner"
    assert candidate.communicated_stage == "INTERVIEW"
    assert candidate.communicated_decision == "REJECT_INTERVIEW"
    assert candidate.communicated_at == communicated_at


@pytest.mark.parametrize("rationale", [None, "", "   ", "abcd"])
def test_correction_requires_meaningful_rationale(
    db: Session,
    rationale: str | None,
) -> None:
    candidate, _, _ = establish_communicated_outcome(db)

    with pytest.raises(DraftServiceError) as error:
        create_decision_correction(
            db,
            application_id=candidate.application_id,
            new_decision="PASS_INTERVIEW",
            rationale=rationale,
        )

    assert error.value.error_code == "CORRECTION_RATIONALE_REQUIRED"
    assert correction_count(db) == 0


def test_correction_requires_prior_provider_accepted_operation(db: Session) -> None:
    candidate, _, operation = establish_communicated_outcome(db)
    operation.operation_status = OperationStatus.DEFINITIVE_FAILURE.value
    operation.final_outcome = OperationStatus.DEFINITIVE_FAILURE.value
    db.commit()

    with pytest.raises(DraftServiceError) as error:
        create_decision_correction(
            db,
            application_id=candidate.application_id,
            new_decision="PASS_INTERVIEW",
            rationale="Decision changed after review",
        )

    assert error.value.error_code == "PRIOR_ACCEPTED_OPERATION_NOT_FOUND"


def test_prior_operation_must_match_communicated_stage_and_decision(db: Session) -> None:
    candidate, prior_draft, _ = establish_communicated_outcome(db)
    prior_draft.decision = "PASS_INTERVIEW"
    db.commit()

    with pytest.raises(DraftServiceError) as error:
        create_decision_correction(
            db,
            application_id=candidate.application_id,
            new_decision="PASS_INTERVIEW",
            rationale="Decision changed after review",
        )

    assert error.value.error_code == "PRIOR_ACCEPTED_OPERATION_NOT_FOUND"


def test_correction_links_latest_matching_accepted_operation(db: Session) -> None:
    candidate, _, first_operation = establish_communicated_outcome(db)
    first_operation.updated_at = datetime(2026, 8, 16, 8, 0, tzinfo=timezone.utc)
    newer_draft = generate_draft(db, application_id=candidate.application_id)
    newer_draft.status = DraftStatus.FINALIZED.value
    newer_operation = LogicalSendOperation(
        draft_revision_id=newer_draft.id,
        operation_status=OperationStatus.PROVIDER_ACCEPTED.value,
        final_outcome=OperationStatus.PROVIDER_ACCEPTED.value,
        provider_message_id="resend-newer-message",
        updated_at=datetime(2026, 8, 16, 9, 0, tzinfo=timezone.utc),
    )
    db.add(newer_operation)
    db.commit()

    correction = create_decision_correction(
        db,
        application_id=candidate.application_id,
        new_decision="PASS_INTERVIEW",
        rationale="Decision changed after review",
    )

    assert correction.prior_operation_id == newer_operation.id


def test_missing_communicated_outcome_is_rejected(db: Session) -> None:
    candidate, _, _ = establish_communicated_outcome(db)
    candidate.communicated_stage = None
    candidate.communicated_decision = None
    db.commit()

    with pytest.raises(DraftServiceError) as error:
        create_decision_correction(
            db,
            application_id=candidate.application_id,
            new_decision="PASS_INTERVIEW",
            rationale="Decision changed after review",
        )

    assert error.value.error_code == "COMMUNICATED_OUTCOME_REQUIRED"


def test_correction_stage_must_match_current_communicated_stage(db: Session) -> None:
    candidate, _, _ = establish_communicated_outcome(db)
    candidate.stage = "CV_SCREENING"
    candidate.status = "PASS_CV"
    db.commit()

    with pytest.raises(DraftServiceError) as error:
        create_decision_correction(
            db,
            application_id=candidate.application_id,
            new_decision="REJECT_CV",
            rationale="Decision changed after review",
        )

    assert error.value.error_code == "CORRECTION_STAGE_MISMATCH"


@pytest.mark.parametrize(
    ("decision", "expected_code"),
    [
        ("REJECT_INTERVIEW", "CORRECTION_NOT_REQUIRED"),
        ("PASS_CV", "STATUS_UNSUPPORTED"),
        ("PENDING", "STATUS_UNSUPPORTED"),
    ],
)
def test_correction_requires_opposing_policy_valid_decision(
    db: Session,
    decision: str,
    expected_code: str,
) -> None:
    candidate, _, _ = establish_communicated_outcome(db)

    with pytest.raises(DraftServiceError) as error:
        create_decision_correction(
            db,
            application_id=candidate.application_id,
            new_decision=decision,
            rationale="Decision changed after review",
        )

    assert error.value.error_code == expected_code


def test_second_active_correction_is_rejected(db: Session) -> None:
    candidate, _, _ = establish_communicated_outcome(db)
    first = create_decision_correction(
        db,
        application_id=candidate.application_id,
        new_decision="PASS_INTERVIEW",
        rationale="Decision changed after review",
    )

    with pytest.raises(DraftServiceError) as error:
        create_decision_correction(
            db,
            application_id=candidate.application_id,
            new_decision="PASS_INTERVIEW",
            rationale="Another correction attempt",
        )

    assert first.status == DraftStatus.CORRECTION_DRAFT.value
    assert error.value.error_code == "ACTIVE_CORRECTION_EXISTS"
    assert correction_count(db) == 1


@pytest.mark.parametrize(
    "operation_status",
    [
        OperationStatus.SENDING_UNCONFIRMED.value,
        OperationStatus.DEFINITIVE_FAILURE.value,
        OperationStatus.DELIVERY_UNKNOWN.value,
    ],
)
def test_retryable_or_in_flight_correction_operation_remains_active(
    db: Session,
    operation_status: str,
) -> None:
    candidate, _, _ = establish_communicated_outcome(db)
    correction = create_decision_correction(
        db,
        application_id=candidate.application_id,
        new_decision="PASS_INTERVIEW",
        rationale="Decision changed after review",
    )
    correction.status = DraftStatus.FINALIZED.value
    db.add(
        LogicalSendOperation(
            draft_revision_id=correction.id,
            operation_status=operation_status,
            final_outcome=(
                None
                if operation_status == OperationStatus.SENDING_UNCONFIRMED.value
                else operation_status
            ),
        )
    )
    db.commit()

    with pytest.raises(DraftServiceError) as error:
        create_decision_correction(
            db,
            application_id=candidate.application_id,
            new_decision="PASS_INTERVIEW",
            rationale="Another correction attempt",
        )

    assert error.value.error_code == "ACTIVE_CORRECTION_EXISTS"


def test_discard_unsent_correction_preserves_outcome_and_allows_replacement(
    db: Session,
) -> None:
    candidate, _, _ = establish_communicated_outcome(db)
    correction = create_decision_correction(
        db,
        application_id=candidate.application_id,
        new_decision="PASS_INTERVIEW",
        rationale="Decision changed after review",
    )

    discarded = discard_decision_correction(
        db,
        draft_revision_id=correction.id,
    )
    replacement = create_decision_correction(
        db,
        application_id=candidate.application_id,
        new_decision="PASS_INTERVIEW",
        rationale="Updated correction rationale",
    )

    assert discarded.status == DraftStatus.DISCARDED.value
    assert discarded.discarded_at is not None
    assert replacement.revision_number == 3
    assert candidate.communicated_decision == "REJECT_INTERVIEW"


def test_only_unsent_correction_draft_can_be_discarded(db: Session) -> None:
    candidate, prior_draft, _ = establish_communicated_outcome(db)
    correction = create_decision_correction(
        db,
        application_id=candidate.application_id,
        new_decision="PASS_INTERVIEW",
        rationale="Decision changed after review",
    )
    db.add(
        LogicalSendOperation(
            draft_revision_id=correction.id,
            operation_status=OperationStatus.SENDING_UNCONFIRMED.value,
        )
    )
    db.flush()

    with pytest.raises(DraftServiceError) as sent_error:
        discard_decision_correction(db, draft_revision_id=correction.id)
    with pytest.raises(DraftServiceError) as normal_error:
        discard_decision_correction(db, draft_revision_id=prior_draft.id)

    assert sent_error.value.error_code == "CORRECTION_NOT_DISCARDABLE"
    assert normal_error.value.error_code == "CORRECTION_DRAFT_REQUIRED"


def test_correction_service_does_not_commit_callers_transaction(db: Session) -> None:
    candidate, _, _ = establish_communicated_outcome(db)

    correction = create_decision_correction(
        db,
        application_id=candidate.application_id,
        new_decision="PASS_INTERVIEW",
        rationale="Decision changed after review",
    )
    db.rollback()
    refreshed = db.execute(
        select(Candidate).where(Candidate.id == candidate.id)
    ).scalar_one()

    assert correction.revision_number == 2
    assert refreshed.status == "REJECT_INTERVIEW"
    assert refreshed.communicated_decision == "REJECT_INTERVIEW"
    assert correction_count(db) == 0
